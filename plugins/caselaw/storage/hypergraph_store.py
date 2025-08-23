"""
Hybrid Hypergraph Store for CAP Caselaw Plugin
Coordinates Neo4j core + Redis Graph caching + Elasticsearch search
"""

import logging
from typing import Dict, List, Any, Optional, Iterator, Union
from datetime import datetime
import asyncio
from contextlib import asynccontextmanager

from ..models.caselaw_node import CaselawNode, CaseNode, CitationNode
from ..models.case_relationship import CaseRelationship
from ..models.canonical_identifiers import CanonicalID, DocumentID
from ..models.provenance_record import ProvenanceRecord

from .neo4j_adapter import Neo4jAdapter
from .redis_cache import RedisGraphCache
from .elasticsearch_adapter import ElasticsearchAdapter
from .storage_config import StorageConfig

logger = logging.getLogger(__name__)


class CaselawHypergraphStore:
    """
    Hybrid hypergraph store coordinating multiple storage backends:
    - Neo4j: Primary graph storage for relationships and traversals
    - Redis Graph: High-speed caching for hot queries
    - Elasticsearch: Full-text search and document retrieval
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = StorageConfig(config)
        self.plugin_id = "caselaw_access_project"
        
        # Storage adapters
        self._neo4j: Optional[Neo4jAdapter] = None
        self._redis_cache: Optional[RedisGraphCache] = None
        self._elasticsearch: Optional[ElasticsearchAdapter] = None
        
        # Connection pools
        self._initialized = False
        self._write_locks: Dict[str, asyncio.Lock] = {}
        
        # Performance metrics
        self._query_stats = {
            "cache_hits": 0,
            "cache_misses": 0,
            "neo4j_queries": 0,
            "elasticsearch_queries": 0
        }
        
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    async def initialize(self):
        """Initialize all storage backends"""
        if self._initialized:
            return
        
        try:
            self.logger.info("Initializing hybrid hypergraph store...")
            
            # Initialize Neo4j primary graph store
            self._neo4j = Neo4jAdapter(self.config.neo4j_config)
            await self._neo4j.initialize()
            
            # Initialize Redis cache
            self._redis_cache = RedisGraphCache(self.config.redis_config)
            await self._redis_cache.initialize()
            
            # Initialize Elasticsearch
            self._elasticsearch = ElasticsearchAdapter(self.config.elasticsearch_config)
            await self._elasticsearch.initialize()
            
            # Create indices and constraints
            await self._setup_database_schema()
            
            self._initialized = True
            self.logger.info("Hybrid hypergraph store initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize hypergraph store: {e}")
            raise
    
    async def _setup_database_schema(self):
        """Setup database schema and indices across all backends"""
        
        # Neo4j constraints and indices
        await self._neo4j.create_constraints([
            "CREATE CONSTRAINT case_id_unique IF NOT EXISTS FOR (c:Case) REQUIRE c.id IS UNIQUE",
            "CREATE CONSTRAINT citation_id_unique IF NOT EXISTS FOR (c:Citation) REQUIRE c.id IS UNIQUE",
            "CREATE CONSTRAINT court_id_unique IF NOT EXISTS FOR (c:Court) REQUIRE c.id IS UNIQUE",
            "CREATE CONSTRAINT judge_id_unique IF NOT EXISTS FOR (j:Judge) REQUIRE j.id IS UNIQUE",
            "CREATE CONSTRAINT concept_id_unique IF NOT EXISTS FOR (c:LegalConcept) REQUIRE c.id IS UNIQUE",
            "CREATE CONSTRAINT paragraph_id_unique IF NOT EXISTS FOR (p:Paragraph) REQUIRE p.id IS UNIQUE"
        ])
        
        await self._neo4j.create_indices([
            "CREATE INDEX case_jurisdiction IF NOT EXISTS FOR (c:Case) ON (c.jurisdiction)",
            "CREATE INDEX case_decision_date IF NOT EXISTS FOR (c:Case) ON (c.decision_date)",
            "CREATE INDEX case_precedential_value IF NOT EXISTS FOR (c:Case) ON (c.precedential_value)",
            "CREATE INDEX citation_normalized IF NOT EXISTS FOR (c:Citation) ON (c.normalized_cite)",
            "CREATE INDEX court_authority_level IF NOT EXISTS FOR (c:Court) ON (c.authority_level)"
        ])
        
        # Elasticsearch indices
        await self._elasticsearch.create_index("legal_cases", {
            "mappings": {
                "properties": {
                    "case_id": {"type": "keyword"},
                    "name": {
                        "type": "text",
                        "analyzer": "legal_text_analyzer",
                        "fields": {"keyword": {"type": "keyword"}}
                    },
                    "jurisdiction": {"type": "keyword"},
                    "decision_date": {"type": "date"},
                    "court": {"type": "keyword"},
                    "full_text": {
                        "type": "text",
                        "analyzer": "legal_text_analyzer"
                    },
                    "legal_concepts": {"type": "keyword"},
                    "precedential_value": {"type": "float"},
                    "citations": {"type": "text", "analyzer": "citation_analyzer"}
                }
            },
            "settings": {
                "analysis": {
                    "analyzer": {
                        "legal_text_analyzer": {
                            "type": "custom",
                            "tokenizer": "standard",
                            "filter": ["lowercase", "legal_synonyms", "legal_stemmer"]
                        },
                        "citation_analyzer": {
                            "type": "custom",
                            "tokenizer": "keyword",
                            "filter": ["lowercase", "trim"]
                        }
                    },
                    "filter": {
                        "legal_synonyms": {
                            "type": "synonym",
                            "synonyms": [
                                "discrimination,bias",
                                "precedent,authority",
                                "jurisdiction,venue"
                            ]
                        },
                        "legal_stemmer": {
                            "type": "stemmer",
                            "language": "english"
                        }
                    }
                }
            }
        })
    
    async def close(self):
        """Close all storage connections"""
        self.logger.info("Closing hypergraph store connections...")
        
        if self._neo4j:
            await self._neo4j.close()
        
        if self._redis_cache:
            await self._redis_cache.close()
        
        if self._elasticsearch:
            await self._elasticsearch.close()
        
        self._initialized = False
        self.logger.info("Hypergraph store closed")
    
    def is_healthy(self) -> bool:
        """Check if all storage backends are healthy"""
        if not self._initialized:
            return False
        
        return (self._neo4j.is_healthy() and 
                self._redis_cache.is_healthy() and 
                self._elasticsearch.is_healthy())
    
    # Node operations
    async def add_node(self, node: CaselawNode) -> bool:
        """Add a node to the hypergraph"""
        async with self._get_write_lock(node.id):
            try:
                # Store in Neo4j primary store
                success = await self._neo4j.create_node(node)
                
                if success:
                    # Index in Elasticsearch for search
                    await self._elasticsearch.index_node(node)
                    
                    # Invalidate cache to ensure consistency
                    await self._redis_cache.invalidate_node(node.id)
                    
                    self.logger.debug(f"Added node {node.id} to hypergraph")
                    return True
                
                return False
                
            except Exception as e:
                self.logger.error(f"Failed to add node {node.id}: {e}")
                return False
    
    async def get_node(self, node_id: str, use_cache: bool = True) -> Optional[CaselawNode]:
        """Retrieve a node from the hypergraph"""
        try:
            # Try cache first if enabled
            if use_cache:
                cached_node = await self._redis_cache.get_node(node_id)
                if cached_node:
                    self._query_stats["cache_hits"] += 1
                    return cached_node
                
                self._query_stats["cache_misses"] += 1
            
            # Fetch from Neo4j
            node = await self._neo4j.get_node(node_id)
            self._query_stats["neo4j_queries"] += 1
            
            # Cache for future queries
            if node and use_cache:
                await self._redis_cache.cache_node(node)
            
            return node
            
        except Exception as e:
            self.logger.error(f"Failed to get node {node_id}: {e}")
            return None
    
    async def update_node(self, node: CaselawNode) -> bool:
        """Update a node in the hypergraph"""
        async with self._get_write_lock(node.id):
            try:
                # Update in Neo4j
                success = await self._neo4j.update_node(node)
                
                if success:
                    # Update search index
                    await self._elasticsearch.update_node(node)
                    
                    # Update cache
                    await self._redis_cache.cache_node(node)
                    
                    return True
                
                return False
                
            except Exception as e:
                self.logger.error(f"Failed to update node {node.id}: {e}")
                return False
    
    async def delete_node(self, node_id: str) -> bool:
        """Delete a node from the hypergraph"""
        async with self._get_write_lock(node_id):
            try:
                # Delete from Neo4j (cascades to relationships)
                success = await self._neo4j.delete_node(node_id)
                
                if success:
                    # Remove from search index
                    await self._elasticsearch.delete_node(node_id)
                    
                    # Remove from cache
                    await self._redis_cache.invalidate_node(node_id)
                    
                    return True
                
                return False
                
            except Exception as e:
                self.logger.error(f"Failed to delete node {node_id}: {e}")
                return False
    
    # Relationship operations
    async def add_relationship(self, relationship: CaseRelationship) -> bool:
        """Add a relationship to the hypergraph"""
        async with self._get_write_lock(f"rel_{relationship.id}"):
            try:
                # Store in Neo4j
                success = await self._neo4j.create_relationship(relationship)
                
                if success:
                    # Invalidate related caches
                    await self._redis_cache.invalidate_node_relationships(
                        relationship.source_case_id
                    )
                    await self._redis_cache.invalidate_node_relationships(
                        relationship.target_case_id
                    )
                    
                    return True
                
                return False
                
            except Exception as e:
                self.logger.error(f"Failed to add relationship {relationship.id}: {e}")
                return False
    
    async def get_relationships(self, 
                              node_id: str,
                              relationship_types: Optional[List[str]] = None,
                              direction: str = "BOTH") -> List[CaseRelationship]:
        """Get relationships for a node"""
        try:
            cache_key = f"rels_{node_id}_{relationship_types}_{direction}"
            
            # Try cache first
            cached_rels = await self._redis_cache.get_relationships(cache_key)
            if cached_rels:
                self._query_stats["cache_hits"] += 1
                return cached_rels
            
            self._query_stats["cache_misses"] += 1
            
            # Fetch from Neo4j
            relationships = await self._neo4j.get_relationships(
                node_id, relationship_types, direction
            )
            self._query_stats["neo4j_queries"] += 1
            
            # Cache results
            await self._redis_cache.cache_relationships(cache_key, relationships)
            
            return relationships
            
        except Exception as e:
            self.logger.error(f"Failed to get relationships for {node_id}: {e}")
            return []
    
    # Complex queries
    async def query_precedents(self,
                             legal_concept: str,
                             jurisdiction: str,
                             date_range: Optional[tuple] = None,
                             limit: int = 100) -> List[CaseNode]:
        """Query precedent cases for a legal concept"""
        try:
            cache_key = f"precedents_{legal_concept}_{jurisdiction}_{date_range}_{limit}"
            
            # Try cache first
            cached_results = await self._redis_cache.get_query_results(cache_key)
            if cached_results:
                self._query_stats["cache_hits"] += 1
                return cached_results
            
            self._query_stats["cache_misses"] += 1
            
            # Complex Cypher query for precedent analysis
            cypher_query = """
            MATCH (concept:LegalConcept {name: $legal_concept})
            MATCH (case:Case)-[:REFERENCES_CONCEPT]->(concept)
            WHERE case.jurisdiction = $jurisdiction
            AND ($start_date IS NULL OR case.decision_date >= $start_date)
            AND ($end_date IS NULL OR case.decision_date <= $end_date)
            WITH case, case.precedential_value as strength
            ORDER BY strength DESC, case.decision_date DESC
            LIMIT $limit
            RETURN case
            """
            
            params = {
                "legal_concept": legal_concept,
                "jurisdiction": jurisdiction,
                "start_date": date_range[0] if date_range else None,
                "end_date": date_range[1] if date_range else None,
                "limit": limit
            }
            
            cases = await self._neo4j.execute_cypher(cypher_query, params)
            self._query_stats["neo4j_queries"] += 1
            
            # Cache results
            await self._redis_cache.cache_query_results(cache_key, cases, ttl=3600)
            
            return cases
            
        except Exception as e:
            self.logger.error(f"Failed to query precedents: {e}")
            return []
    
    async def full_text_search(self,
                             query: str,
                             jurisdiction: Optional[str] = None,
                             limit: int = 100) -> List[Dict[str, Any]]:
        """Full-text search across case documents"""
        try:
            search_params = {
                "index": "legal_cases",
                "body": {
                    "query": {
                        "bool": {
                            "must": [
                                {
                                    "multi_match": {
                                        "query": query,
                                        "fields": ["name^3", "full_text", "legal_concepts^2"],
                                        "fuzziness": "AUTO"
                                    }
                                }
                            ],
                            "filter": []
                        }
                    },
                    "highlight": {
                        "fields": {
                            "full_text": {},
                            "name": {}
                        }
                    },
                    "size": limit
                }
            }
            
            if jurisdiction:
                search_params["body"]["query"]["bool"]["filter"].append({
                    "term": {"jurisdiction": jurisdiction}
                })
            
            results = await self._elasticsearch.search(search_params)
            self._query_stats["elasticsearch_queries"] += 1
            
            return results
            
        except Exception as e:
            self.logger.error(f"Failed to perform full-text search: {e}")
            return []
    
    async def find_citation_path(self, 
                                source_case_id: str,
                                target_case_id: str,
                                max_depth: int = 5) -> Optional[List[Dict[str, Any]]]:
        """Find citation path between two cases"""
        try:
            cache_key = f"citation_path_{source_case_id}_{target_case_id}_{max_depth}"
            
            # Try cache first
            cached_path = await self._redis_cache.get_query_results(cache_key)
            if cached_path:
                self._query_stats["cache_hits"] += 1
                return cached_path
            
            self._query_stats["cache_misses"] += 1
            
            # Cypher query for shortest path
            cypher_query = """
            MATCH path = shortestPath(
                (source:Case {id: $source_id})-[:CITES_CASE*1..5]-(target:Case {id: $target_id})
            )
            WITH path, relationships(path) as rels, nodes(path) as path_nodes
            RETURN [node in path_nodes | {
                id: node.id,
                name: node.name,
                decision_date: node.decision_date
            }] as nodes,
            [rel in rels | {
                type: type(rel),
                confidence: rel.confidence,
                precedential_strength: rel.precedential_strength
            }] as relationships
            """
            
            params = {
                "source_id": source_case_id,
                "target_id": target_case_id
            }
            
            path_result = await self._neo4j.execute_cypher(cypher_query, params)
            self._query_stats["neo4j_queries"] += 1
            
            # Cache result
            if path_result:
                await self._redis_cache.cache_query_results(cache_key, path_result, ttl=7200)
            
            return path_result
            
        except Exception as e:
            self.logger.error(f"Failed to find citation path: {e}")
            return None
    
    # Batch operations
    async def add_case_batch(self, cases: List[CaseNode]) -> Dict[str, Any]:
        """Add multiple cases in batch"""
        try:
            # Use Neo4j transaction for atomicity
            results = await self._neo4j.create_nodes_batch(cases)
            
            # Index in Elasticsearch
            es_results = await self._elasticsearch.index_nodes_batch(cases)
            
            # Clear related caches
            for case in cases:
                await self._redis_cache.invalidate_node(case.id)
            
            return {
                "total_cases": len(cases),
                "neo4j_success": results.get("success_count", 0),
                "elasticsearch_success": es_results.get("success_count", 0),
                "errors": results.get("errors", []) + es_results.get("errors", [])
            }
            
        except Exception as e:
            self.logger.error(f"Failed to add case batch: {e}")
            return {"error": str(e)}
    
    # Utility methods
    @asynccontextmanager
    async def _get_write_lock(self, resource_id: str):
        """Get write lock for a resource"""
        if resource_id not in self._write_locks:
            self._write_locks[resource_id] = asyncio.Lock()
        
        async with self._write_locks[resource_id]:
            yield
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics"""
        total_queries = sum(self._query_stats.values())
        cache_hit_rate = (self._query_stats["cache_hits"] / total_queries * 100) if total_queries > 0 else 0
        
        return {
            "cache_hit_rate": f"{cache_hit_rate:.2f}%",
            "total_queries": total_queries,
            **self._query_stats,
            "backends_healthy": {
                "neo4j": self._neo4j.is_healthy() if self._neo4j else False,
                "redis": self._redis_cache.is_healthy() if self._redis_cache else False,
                "elasticsearch": self._elasticsearch.is_healthy() if self._elasticsearch else False
            }
        }
    
    async def optimize_performance(self):
        """Run performance optimization tasks"""
        try:
            # Clean expired cache entries
            await self._redis_cache.cleanup_expired_entries()
            
            # Optimize Elasticsearch indices
            await self._elasticsearch.optimize_indices()
            
            # Update Neo4j statistics
            await self._neo4j.update_statistics()
            
            self.logger.info("Performance optimization completed")
            
        except Exception as e:
            self.logger.error(f"Performance optimization failed: {e}")