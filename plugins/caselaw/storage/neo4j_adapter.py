"""
Neo4j Adapter for CAP Caselaw Plugin
Primary graph storage for hypergraph relationships and complex traversals
"""

import logging
from typing import Dict, List, Any, Optional, Union
from datetime import datetime
import asyncio
from contextlib import asynccontextmanager

from neo4j import AsyncGraphDatabase, AsyncDriver, AsyncSession
from neo4j.exceptions import Neo4jError, ServiceUnavailable

from ..models.caselaw_node import CaselawNode, CaseNode, CitationNode, CourtNode, JudgeNode, LegalConceptNode, ParagraphNode
from ..models.case_relationship import CaseRelationship
from ..models.canonical_identifiers import CanonicalID

logger = logging.getLogger(__name__)


class Neo4jAdapter:
    """
    Neo4j adapter for storing and querying legal hypergraph data.
    Optimized for complex case relationship traversals and precedent analysis.
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.uri = config.get("uri", "bolt://localhost:7687")
        self.username = config.get("username", "neo4j")
        self.password = config.get("password", "password")
        self.database = config.get("database", "caselaw")
        
        # Connection settings
        self.max_connection_pool_size = config.get("max_connection_pool_size", 50)
        self.max_transaction_retry_time = config.get("max_transaction_retry_time", 30)
        self.connection_timeout = config.get("connection_timeout", 30)
        
        self._driver: Optional[AsyncDriver] = None
        self._initialized = False
        
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    async def initialize(self):
        """Initialize Neo4j connection"""
        try:
            self._driver = AsyncGraphDatabase.driver(
                self.uri,
                auth=(self.username, self.password),
                max_connection_pool_size=self.max_connection_pool_size,
                max_transaction_retry_time=self.max_transaction_retry_time,
                connection_timeout=self.connection_timeout
            )
            
            # Test connection
            await self._driver.verify_connectivity()
            
            self._initialized = True
            self.logger.info(f"Neo4j adapter initialized: {self.uri}")
            
        except ServiceUnavailable as e:
            self.logger.error(f"Neo4j service unavailable: {e}")
            raise
        except Exception as e:
            self.logger.error(f"Failed to initialize Neo4j adapter: {e}")
            raise
    
    async def close(self):
        """Close Neo4j connection"""
        if self._driver:
            await self._driver.close()
            self._initialized = False
            self.logger.info("Neo4j adapter closed")
    
    def is_healthy(self) -> bool:
        """Check if Neo4j connection is healthy"""
        return self._initialized and self._driver is not None
    
    @asynccontextmanager
    async def _session(self, database: Optional[str] = None) -> AsyncSession:
        """Get Neo4j session with proper error handling"""
        if not self._driver:
            raise RuntimeError("Neo4j adapter not initialized")
        
        session = self._driver.session(database=database or self.database)
        try:
            yield session
        finally:
            await session.close()
    
    # Schema management
    async def create_constraints(self, constraints: List[str]):
        """Create database constraints"""
        async with self._session() as session:
            for constraint in constraints:
                try:
                    await session.run(constraint)
                    self.logger.debug(f"Created constraint: {constraint}")
                except Neo4jError as e:
                    if "already exists" not in str(e):
                        self.logger.warning(f"Failed to create constraint: {e}")
    
    async def create_indices(self, indices: List[str]):
        """Create database indices"""
        async with self._session() as session:
            for index in indices:
                try:
                    await session.run(index)
                    self.logger.debug(f"Created index: {index}")
                except Neo4jError as e:
                    if "already exists" not in str(e):
                        self.logger.warning(f"Failed to create index: {e}")
    
    # Node operations
    async def create_node(self, node: CaselawNode) -> bool:
        """Create a node in Neo4j"""
        try:
            cypher_query, params = self._build_create_node_query(node)
            
            async with self._session() as session:
                result = await session.run(cypher_query, params)
                summary = await result.consume()
                
                return summary.counters.nodes_created > 0
                
        except Neo4jError as e:
            self.logger.error(f"Failed to create node {node.id}: {e}")
            return False
    
    def _build_create_node_query(self, node: CaselawNode) -> tuple[str, Dict[str, Any]]:
        """Build Cypher query for creating a node"""
        node_label = self._get_node_label(node)
        
        # Prepare properties
        properties = {
            "id": node.id,
            "canonical_id": str(node.canonical_id),
            "created_at": node.created_at.isoformat(),
            "updated_at": node.updated_at.isoformat(),
            "provenance_id": node.provenance_id,
            **node.properties
        }
        
        # Convert datetime objects to ISO strings
        for key, value in properties.items():
            if isinstance(value, datetime):
                properties[key] = value.isoformat()
        
        cypher_query = f"""
        CREATE (n:{node_label} $properties)
        RETURN n.id as created_id
        """
        
        return cypher_query, {"properties": properties}
    
    def _get_node_label(self, node: CaselawNode) -> str:
        """Get Neo4j label for a node type"""
        label_mapping = {
            "case": "Case",
            "citation": "Citation", 
            "court": "Court",
            "judge": "Judge",
            "legal_concept": "LegalConcept",
            "paragraph": "Paragraph"
        }
        return label_mapping.get(node.node_type, "Unknown")
    
    async def get_node(self, node_id: str) -> Optional[CaselawNode]:
        """Retrieve a node from Neo4j"""
        try:
            cypher_query = """
            MATCH (n {id: $node_id})
            RETURN n, labels(n) as labels
            """
            
            async with self._session() as session:
                result = await session.run(cypher_query, {"node_id": node_id})
                record = await result.single()
                
                if record:
                    return self._build_node_from_record(record)
                
                return None
                
        except Neo4jError as e:
            self.logger.error(f"Failed to get node {node_id}: {e}")
            return None
    
    def _build_node_from_record(self, record) -> Optional[CaselawNode]:
        """Build CaselawNode from Neo4j record"""
        try:
            node_data = dict(record["n"])
            labels = record["labels"]
            
            # Determine node type from labels
            node_type = None
            for label in labels:
                if label in ["Case", "Citation", "Court", "Judge", "LegalConcept", "Paragraph"]:
                    node_type = label.lower().replace("legalconcept", "legal_concept")
                    break
            
            if not node_type:
                return None
            
            # Extract canonical ID and other metadata
            canonical_id_str = node_data.pop("canonical_id")
            provenance_id = node_data.pop("provenance_id", None)
            created_at = datetime.fromisoformat(node_data.pop("created_at"))
            updated_at = datetime.fromisoformat(node_data.pop("updated_at", created_at.isoformat()))
            
            # Create appropriate node type
            from ..models.canonical_identifiers import IdentifierFactory
            canonical_id = IdentifierFactory.create_from_string(canonical_id_str)
            
            # Mock provenance record (would be fetched separately in production)
            from ..models.provenance_record import ProvenanceRecord, ProvenanceAgent, ProvenanceActivity, ProvenanceMetadata, ProvenanceOperation
            mock_provenance = ProvenanceRecord(
                entity_id=canonical_id_str,
                entity_type=node_type,
                operation=ProvenanceOperation.CREATE,
                agent=ProvenanceAgent("system", "neo4j_adapter"),
                activity=ProvenanceActivity(ProvenanceOperation.CREATE, "Retrieved from Neo4j", "database_query"),
                metadata=ProvenanceMetadata("neo4j", "1.0", "1.0.0")
            )
            
            # Build the appropriate node type
            node_classes = {
                "case": CaseNode,
                "citation": CitationNode,
                "court": CourtNode,
                "judge": JudgeNode,
                "legal_concept": LegalConceptNode,
                "paragraph": ParagraphNode
            }
            
            node_class = node_classes.get(node_type)
            if node_class:
                return node_class(
                    canonical_id,
                    node_data,
                    mock_provenance,
                    created_at
                )
            
            return None
            
        except Exception as e:
            self.logger.error(f"Failed to build node from record: {e}")
            return None
    
    async def update_node(self, node: CaselawNode) -> bool:
        """Update a node in Neo4j"""
        try:
            properties = {
                "updated_at": datetime.utcnow().isoformat(),
                **node.properties
            }
            
            # Convert datetime objects
            for key, value in properties.items():
                if isinstance(value, datetime):
                    properties[key] = value.isoformat()
            
            cypher_query = """
            MATCH (n {id: $node_id})
            SET n += $properties
            RETURN n.id as updated_id
            """
            
            async with self._session() as session:
                result = await session.run(cypher_query, {
                    "node_id": node.id,
                    "properties": properties
                })
                summary = await result.consume()
                
                return summary.counters.properties_set > 0
                
        except Neo4jError as e:
            self.logger.error(f"Failed to update node {node.id}: {e}")
            return False
    
    async def delete_node(self, node_id: str) -> bool:
        """Delete a node and its relationships"""
        try:
            cypher_query = """
            MATCH (n {id: $node_id})
            DETACH DELETE n
            """
            
            async with self._session() as session:
                result = await session.run(cypher_query, {"node_id": node_id})
                summary = await result.consume()
                
                return summary.counters.nodes_deleted > 0
                
        except Neo4jError as e:
            self.logger.error(f"Failed to delete node {node_id}: {e}")
            return False
    
    # Relationship operations
    async def create_relationship(self, relationship: CaseRelationship) -> bool:
        """Create a relationship in Neo4j"""
        try:
            # Prepare relationship properties
            properties = {
                "id": relationship.id,
                "relationship_type": relationship.relationship_type.value,
                "confidence": relationship.confidence,
                "extraction_method": relationship.extraction_method,
                "precedential_strength": relationship.precedential_strength,
                "created_at": relationship.created_at.isoformat(),
                "provenance_id": relationship.provenance_record.id,
                "evidence_spans": [span.to_dict() for span in relationship.evidence_spans]
            }
            
            # Add temporal and jurisdictional evaluations
            if relationship.temporal_evaluation:
                properties["temporal_evaluation"] = relationship.temporal_evaluation.to_dict()
            
            if relationship.jurisdictional_evaluation:
                properties["jurisdictional_evaluation"] = relationship.jurisdictional_evaluation.to_dict()
            
            # Create relationship with proper direction
            cypher_query = f"""
            MATCH (source {{id: $source_id}})
            MATCH (target {{id: $target_id}})
            CREATE (source)-[r:{relationship.relationship_type.value.upper()} $properties]->(target)
            RETURN r.id as created_id
            """
            
            async with self._session() as session:
                result = await session.run(cypher_query, {
                    "source_id": relationship.source_case_id,
                    "target_id": relationship.target_case_id,
                    "properties": properties
                })
                summary = await result.consume()
                
                return summary.counters.relationships_created > 0
                
        except Neo4jError as e:
            self.logger.error(f"Failed to create relationship {relationship.id}: {e}")
            return False
    
    async def get_relationships(self,
                              node_id: str,
                              relationship_types: Optional[List[str]] = None,
                              direction: str = "BOTH") -> List[CaseRelationship]:
        """Get relationships for a node"""
        try:
            # Build relationship type filter
            rel_type_filter = ""
            if relationship_types:
                formatted_types = [f":{rel_type.upper()}" for rel_type in relationship_types]
                rel_type_filter = "|".join(formatted_types)
            
            # Build direction pattern
            if direction.upper() == "OUTGOING":
                pattern = f"(n)-[r{rel_type_filter}]->()"
            elif direction.upper() == "INCOMING":
                pattern = f"()-[r{rel_type_filter}]->(n)"
            else:  # BOTH
                pattern = f"(n)-[r{rel_type_filter}]-()"
            
            cypher_query = f"""
            MATCH {pattern}
            WHERE n.id = $node_id
            RETURN r, startNode(r).id as source_id, endNode(r).id as target_id
            """
            
            async with self._session() as session:
                result = await session.run(cypher_query, {"node_id": node_id})
                
                relationships = []
                async for record in result:
                    rel = self._build_relationship_from_record(record)
                    if rel:
                        relationships.append(rel)
                
                return relationships
                
        except Neo4jError as e:
            self.logger.error(f"Failed to get relationships for {node_id}: {e}")
            return []
    
    def _build_relationship_from_record(self, record) -> Optional[CaseRelationship]:
        """Build CaseRelationship from Neo4j record"""
        try:
            rel_data = dict(record["r"])
            source_id = record["source_id"]
            target_id = record["target_id"]
            
            # Extract relationship properties
            rel_id = rel_data.get("id")
            relationship_type_str = rel_data.get("relationship_type")
            confidence = rel_data.get("confidence", 0.0)
            extraction_method = rel_data.get("extraction_method", "unknown")
            evidence_spans_data = rel_data.get("evidence_spans", [])
            
            # Build evidence spans
            from ..models.case_relationship import EvidenceSpan
            evidence_spans = [EvidenceSpan.from_dict(span_data) for span_data in evidence_spans_data]
            
            # Build temporal evaluation
            temporal_eval = None
            if rel_data.get("temporal_evaluation"):
                from ..models.case_relationship import TemporalEvaluation
                temporal_eval = TemporalEvaluation.from_dict(rel_data["temporal_evaluation"])
            
            # Build jurisdictional evaluation
            jurisdictional_eval = None
            if rel_data.get("jurisdictional_evaluation"):
                from ..models.case_relationship import JurisdictionalEvaluation
                jurisdictional_eval = JurisdictionalEvaluation.from_dict(rel_data["jurisdictional_evaluation"])
            
            # Mock provenance record
            from ..models.provenance_record import ProvenanceRecord, ProvenanceAgent, ProvenanceActivity, ProvenanceMetadata, ProvenanceOperation
            mock_provenance = ProvenanceRecord(
                entity_id=rel_id,
                entity_type="case_relationship",
                operation=ProvenanceOperation.CREATE,
                agent=ProvenanceAgent("system", "neo4j_adapter"),
                activity=ProvenanceActivity(ProvenanceOperation.CREATE, "Retrieved from Neo4j", "database_query"),
                metadata=ProvenanceMetadata("neo4j", "1.0", "1.0.0")
            )
            
            # Create relationship
            from ..models.case_relationship import RelationshipType
            relationship_type = RelationshipType(relationship_type_str)
            
            relationship = CaseRelationship(
                source_case_id=source_id,
                target_case_id=target_id,
                relationship_type=relationship_type,
                confidence=confidence,
                evidence_spans=evidence_spans,
                extraction_method=extraction_method,
                provenance_record=mock_provenance,
                temporal_evaluation=temporal_eval,
                jurisdictional_evaluation=jurisdictional_eval
            )
            
            # Override generated ID with stored ID
            relationship._id = rel_id
            
            return relationship
            
        except Exception as e:
            self.logger.error(f"Failed to build relationship from record: {e}")
            return None
    
    # Batch operations
    async def create_nodes_batch(self, nodes: List[CaselawNode]) -> Dict[str, Any]:
        """Create multiple nodes in a single transaction"""
        try:
            success_count = 0
            errors = []
            
            async with self._session() as session:
                async with session.begin_transaction() as tx:
                    for node in nodes:
                        try:
                            cypher_query, params = self._build_create_node_query(node)
                            await tx.run(cypher_query, params)
                            success_count += 1
                        except Exception as e:
                            errors.append(f"Node {node.id}: {str(e)}")
                    
                    # Commit transaction if no errors
                    if not errors:
                        await tx.commit()
                    else:
                        await tx.rollback()
            
            return {
                "success_count": success_count if not errors else 0,
                "total_count": len(nodes),
                "errors": errors
            }
            
        except Neo4jError as e:
            self.logger.error(f"Failed to create nodes batch: {e}")
            return {"success_count": 0, "total_count": len(nodes), "errors": [str(e)]}
    
    # Complex queries
    async def execute_cypher(self, query: str, parameters: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """Execute a custom Cypher query"""
        try:
            async with self._session() as session:
                result = await session.run(query, parameters or {})
                
                records = []
                async for record in result:
                    records.append(dict(record))
                
                return records
                
        except Neo4jError as e:
            self.logger.error(f"Failed to execute Cypher query: {e}")
            return []
    
    async def get_precedent_chain(self, case_id: str, max_depth: int = 5) -> List[Dict[str, Any]]:
        """Get the precedent chain for a case"""
        cypher_query = """
        MATCH path = (case:Case {id: $case_id})-[:CITES_CASE*1..{max_depth}]->(precedent:Case)
        WHERE precedent.precedential_value > 0.5
        WITH path, precedent, 
             reduce(strength = 1.0, rel in relationships(path) | strength * rel.precedential_strength) as chain_strength
        RETURN precedent.id as precedent_id,
               precedent.name as precedent_name,
               precedent.decision_date as decision_date,
               precedent.precedential_value as precedential_value,
               chain_strength,
               length(path) as depth
        ORDER BY chain_strength DESC, precedent.decision_date DESC
        """.format(max_depth=max_depth)
        
        return await self.execute_cypher(cypher_query, {"case_id": case_id})
    
    async def analyze_citation_network(self, jurisdiction: str, limit: int = 100) -> Dict[str, Any]:
        """Analyze citation network for a jurisdiction"""
        cypher_query = """
        MATCH (case:Case {jurisdiction: $jurisdiction})
        OPTIONAL MATCH (case)-[cites:CITES_CASE]->(cited:Case)
        OPTIONAL MATCH (citing:Case)-[cited_by:CITES_CASE]->(case)
        WITH case, 
             count(cites) as outgoing_citations,
             count(cited_by) as incoming_citations,
             avg(cites.precedential_strength) as avg_citation_strength
        RETURN case.id as case_id,
               case.name as case_name,
               case.decision_date as decision_date,
               outgoing_citations,
               incoming_citations,
               avg_citation_strength,
               (incoming_citations * avg_citation_strength) as influence_score
        ORDER BY influence_score DESC
        LIMIT $limit
        """
        
        results = await self.execute_cypher(cypher_query, {
            "jurisdiction": jurisdiction,
            "limit": limit
        })
        
        return {
            "jurisdiction": jurisdiction,
            "analysis_date": datetime.utcnow().isoformat(),
            "top_cases": results,
            "total_analyzed": len(results)
        }
    
    # Maintenance operations
    async def update_statistics(self):
        """Update Neo4j database statistics"""
        try:
            async with self._session() as session:
                await session.run("CALL db.stats.retrieve('GRAPH COUNTS')")
                self.logger.info("Neo4j statistics updated")
        except Neo4jError as e:
            self.logger.warning(f"Failed to update Neo4j statistics: {e}")
    
    async def get_database_info(self) -> Dict[str, Any]:
        """Get database information and statistics"""
        try:
            async with self._session() as session:
                # Get node counts
                node_result = await session.run("""
                MATCH (n)
                RETURN labels(n) as labels, count(n) as count
                """)
                
                node_counts = {}
                async for record in node_result:
                    labels = record["labels"]
                    count = record["count"]
                    for label in labels:
                        node_counts[label] = node_counts.get(label, 0) + count
                
                # Get relationship counts
                rel_result = await session.run("""
                MATCH ()-[r]->()
                RETURN type(r) as relationship_type, count(r) as count
                """)
                
                relationship_counts = {}
                async for record in rel_result:
                    rel_type = record["relationship_type"]
                    count = record["count"]
                    relationship_counts[rel_type] = count
                
                return {
                    "database": self.database,
                    "node_counts": node_counts,
                    "relationship_counts": relationship_counts,
                    "total_nodes": sum(node_counts.values()),
                    "total_relationships": sum(relationship_counts.values())
                }
                
        except Neo4jError as e:
            self.logger.error(f"Failed to get database info: {e}")
            return {}