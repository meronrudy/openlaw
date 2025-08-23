"""
CAP Caselaw Plugin Implementation

Provides comprehensive caselaw analysis using Harvard Law's CAP dataset for
provenance-first legal reasoning with complete audit trails. Integrates 37M+
legal documents into the OpenLaw hypergraph system.

Follows the proven employment law plugin pattern for seamless integration.
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from pathlib import Path

from core.model import Node, Hyperedge, Context, mk_node, mk_edge, Provenance
from core.storage import GraphStore
from core.reasoning import RuleEngine
from core.rules import LegalRule

from .models.canonical_identifiers import IdentifierFactory, IDGenerator
from .models.provenance_record import ProvenanceRecord, ProvenanceOperation, ProvenanceSource
from .models.caselaw_node import CaselawNode
from .storage.hypergraph_store import HypergraphStore
from .storage.storage_config import StorageConfig
from .extraction.citation_extractor import MLCitationExtractor
from .extraction.relationship_extractor import CaseRelationshipExtractor
from .reasoning.temporal_reasoner import TemporalReasoner
from .reasoning.jurisdictional_reasoner import JurisdictionalReasoner
from .api.query_api import CaselawQueryAPI
from .api.caselaw_provenance_api import CaselawProvenanceAPI
from .ingestion.hf_ingestion_pipeline import HuggingFaceIngestionPipeline

logger = logging.getLogger(__name__)


class CaselawPlugin:
    """
    CAP Caselaw Plugin - Provides provenance-first access to case law documents
    
    Provides comprehensive caselaw analysis capabilities including:
    - Citation extraction and resolution
    - Case relationship mapping (cites, distinguishes, overrules, etc.)
    - Temporal and jurisdictional authority analysis
    - Integration with hypergraph reasoning system
    - HuggingFace dataset ingestion for 37M+ documents
    - Complete audit trails and provenance tracking
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize caselaw plugin with advanced components"""
        self.name = "Case Law Access Project"
        self.version = "1.0.0"
        self.description = "Comprehensive caselaw analysis with CAP dataset integration and provenance tracking"
        
        # Configuration
        self.config = config or {}
        
        # Initialize core components
        self.identifier_factory = IdentifierFactory()
        self.id_generator = IDGenerator()
        
        # Initialize storage
        storage_config = StorageConfig.from_dict(self.config.get("storage", {}))
        self.hypergraph_store = HypergraphStore(storage_config)
        
        # Initialize extraction components
        self.citation_extractor = MLCitationExtractor()
        self.relationship_extractor = CaseRelationshipExtractor()
        
        # Initialize reasoning engines
        self.temporal_reasoner = TemporalReasoner()
        self.jurisdictional_reasoner = JurisdictionalReasoner()
        
        # Initialize APIs
        self.query_api = CaselawQueryAPI(self.hypergraph_store,
                                       self.temporal_reasoner,
                                       self.jurisdictional_reasoner)
        self.provenance_api = CaselawProvenanceAPI(self.hypergraph_store,
                                                  self.temporal_reasoner,
                                                  self.jurisdictional_reasoner)
        
        # Initialize ingestion pipeline
        self.ingestion_pipeline = HuggingFaceIngestionPipeline(
            store=self.hypergraph_store,
            citation_extractor=self.citation_extractor,
            relationship_extractor=self.relationship_extractor,
            batch_size=self.config.get("ingestion_batch_size", 1000),
            max_workers=self.config.get("ingestion_max_workers", 10)
        )
        
        # Plugin state
        self._initialized = False
        self._background_tasks = []
        
        logger.info(f"Initialized {self.name} v{self.version}")
    
    async def initialize(self) -> bool:
        """Initialize plugin components asynchronously"""
        try:
            if self._initialized:
                return True
            
            logger.info("Initializing CAP Caselaw Plugin components...")
            
            # Initialize storage backends
            await self.hypergraph_store.initialize()
            
            # Start background ingestion if enabled
            if self.config.get("auto_start_ingestion", False):
                await self.start_background_ingestion()
            
            self._initialized = True
            logger.info("CAP Caselaw Plugin initialization completed")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize CAP Caselaw Plugin: {e}")
            return False
    
    async def shutdown(self):
        """Shutdown plugin and cleanup resources"""
        logger.info("Shutting down CAP Caselaw Plugin...")
        
        # Stop background tasks
        for task in self._background_tasks:
            task.cancel()
        
        if self._background_tasks:
            await asyncio.gather(*self._background_tasks, return_exceptions=True)
        
        # Stop ingestion
        if hasattr(self.ingestion_pipeline, 'stop_processing'):
            self.ingestion_pipeline.stop_processing()
        
        # Shutdown storage
        if hasattr(self.hypergraph_store, 'shutdown'):
            await self.hypergraph_store.shutdown()
        
        logger.info("CAP Caselaw Plugin shutdown completed")
    
    async def start_background_ingestion(self):
        """Start background HuggingFace ingestion"""
        if not self.config.get("enable_background_ingestion", True):
            logger.info("Background ingestion disabled by configuration")
            return
        
        logger.info("Starting background CAP dataset ingestion...")
        task = asyncio.create_task(self.ingestion_pipeline.start_background_processing())
        self._background_tasks.append(task)
        
    async def analyze_document(self, text: str, context: Context) -> Dict[str, Any]:
        """
        Enhanced document analysis using advanced caselaw components
        
        Args:
            text: Document text to analyze
            context: Legal context for analysis
            
        Returns:
            Comprehensive analysis with citations, relationships, and provenance
        """
        if not self._initialized:
            await self.initialize()
        
        try:
            # Generate document ID for tracking
            doc_id = self.id_generator.generate_document_id(hash(text))
            
            # Enhanced citation extraction using ML components
            citations = self.citation_extractor.extract_citations(text, str(doc_id))
            
            # Extract case relationships
            relationships = self.relationship_extractor.extract_relationships(
                text, citations, str(doc_id)
            )
            
            # Basic entity extraction (legacy compatibility)
            entities = self._extract_caselaw_entities(text)
            
            # Create provenance record
            analysis_provenance = ProvenanceRecord(
                operation=ProvenanceOperation.ANALYZE,
                source=ProvenanceSource.USER_INPUT,
                agent_type="plugin",
                agent_id="caselaw_plugin",
                timestamp=datetime.utcnow(),
                confidence=0.9,
                metadata={
                    "text_length": len(text),
                    "citations_found": len(citations),
                    "relationships_found": len(relationships),
                    "document_id": str(doc_id)
                }
            )
            
            # Create graph for traditional reasoning
            graph = GraphStore(":memory:")
            
            # Convert to legacy format for compatibility
            document_prov = Provenance(
                source=[{
                    "type": "enhanced_analysis",
                    "method": "ml_caselaw_extraction",
                    "text_length": len(text),
                    "document_id": str(doc_id)
                }],
                method="nlp.enhanced_caselaw_extraction",
                agent="caselaw.plugin.v2",
                time=datetime.utcnow(),
                confidence=0.9
            )
            
            facts = self._entities_to_facts(entities, document_prov)
            
            # Add facts to graph
            for fact in facts:
                graph.add_node(fact)
                
            # Run enhanced reasoning
            engine = RuleEngine(graph, context)
            derived_facts = engine.forward_chain()
            
            # Enhanced conclusions using advanced components
            conclusions = await self._extract_enhanced_conclusions(
                derived_facts, citations, relationships, context
            )
            
            return {
                # Enhanced results
                "document_id": str(doc_id),
                "citations": [c.to_dict() for c in citations],
                "relationships": [r.to_dict() for r in relationships],
                "provenance": analysis_provenance.to_dict(),
                
                # Legacy compatibility
                "entities": entities,
                "original_facts": [f.data for f in facts],
                "derived_facts": [f.data for f in derived_facts],
                "conclusions": conclusions,
                "context": context.model_dump() if context else None,
                
                # Analysis metadata
                "analysis_timestamp": datetime.utcnow().isoformat(),
                "plugin_version": self.version
            }
            
        except Exception as e:
            logger.error(f"Error in document analysis: {e}")
            return {
                "error": str(e),
                "entities": [],
                "citations": [],
                "relationships": [],
                "conclusions": [],
                "analysis_timestamp": datetime.utcnow().isoformat()
            }
    
    async def query_precedents(self, legal_issue: str,
                             jurisdiction: Optional[str] = None,
                             date_range: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """
        Query for legal precedents using advanced reasoning
        
        Args:
            legal_issue: Description of the legal issue
            jurisdiction: Target jurisdiction (optional)
            date_range: Date range for temporal analysis (optional)
            
        Returns:
            Precedent analysis with authority and temporal relevance
        """
        if not self._initialized:
            await self.initialize()
        
        return await self.query_api.find_precedents(
            legal_issue=legal_issue,
            jurisdiction=jurisdiction,
            date_range=date_range
        )
    
    async def trace_provenance(self, conclusion: str,
                             context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Trace complete provenance chain for a legal conclusion
        
        Args:
            conclusion: Legal conclusion to trace
            context: Additional context for analysis
            
        Returns:
            Complete provenance chain with audit trail
        """
        if not self._initialized:
            await self.initialize()
        
        provenance_chain = await self.provenance_api.trace_legal_conclusion(
            conclusion, context
        )
        
        return provenance_chain.to_dict()
    
    async def answer_why_question(self, question: str,
                                context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Answer "why" questions with complete legal reasoning
        
        Args:
            question: The "why" question to answer
            context: Additional context for analysis
            
        Returns:
            Complete answer with reasoning and sources
        """
        if not self._initialized:
            await self.initialize()
        
        why_answer = await self.provenance_api.answer_why_question(question, context)
        return why_answer.to_dict()
    
    async def answer_from_where_question(self, question: str,
                                       target_claim: str,
                                       context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Answer "from where" questions by tracing source origins
        
        Args:
            question: The "from where" question to answer
            target_claim: The claim/statement to trace
            context: Additional context for analysis
            
        Returns:
            Complete source tracing with verification
        """
        if not self._initialized:
            await self.initialize()
        
        from_where_answer = await self.provenance_api.answer_from_where_question(
            question, target_claim, context
        )
        return from_where_answer.to_dict()
    
    async def verify_legal_claim(self, claim: str,
                               sources: List[str],
                               context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Verify a legal claim against authoritative sources
        
        Args:
            claim: The legal claim to verify
            sources: List of source identifiers
            context: Additional context for verification
            
        Returns:
            Verification result with confidence and evidence
        """
        if not self._initialized:
            await self.initialize()
        
        return await self.provenance_api.verify_legal_claim(claim, sources, context)
    
    async def _extract_enhanced_conclusions(self, derived_facts: List[Node],
                                          citations: List[Any],
                                          relationships: List[Any],
                                          context: Context) -> List[Dict[str, Any]]:
        """Extract enhanced conclusions using all available components"""
        conclusions = []
        
        # Legacy conclusions
        legacy_conclusions = self._extract_conclusions(derived_facts)
        conclusions.extend(legacy_conclusions)
        
        # Citation-based conclusions
        if citations:
            conclusions.append({
                "type": "ENHANCED_CITATION_ANALYSIS",
                "conclusion": f"Document contains {len(citations)} legal citations with ML-enhanced extraction",
                "legal_basis": "Advanced citation extraction with confidence scoring",
                "confidence": sum(c.confidence for c in citations) / len(citations) if citations else 0.0,
                "citation_count": len(citations),
                "citation_types": list(set(c.citation_type for c in citations))
            })
        
        # Relationship-based conclusions
        if relationships:
            relationship_types = [r.relationship_type.value for r in relationships]
            conclusions.append({
                "type": "CASE_RELATIONSHIP_ANALYSIS",
                "conclusion": f"Document shows {len(relationships)} case relationships",
                "legal_basis": "Case relationship extraction with precedential analysis",
                "confidence": sum(r.confidence for r in relationships) / len(relationships) if relationships else 0.0,
                "relationship_count": len(relationships),
                "relationship_types": list(set(relationship_types))
            })
        
        # Jurisdictional conclusions (if context available)
        if context and hasattr(context, 'jurisdiction'):
            conclusions.append({
                "type": "JURISDICTIONAL_ANALYSIS",
                "conclusion": f"Analysis performed in {context.jurisdiction} jurisdiction context",
                "legal_basis": "Jurisdictional reasoning with authority analysis",
                "confidence": 0.8,
                "jurisdiction": context.jurisdiction
            })
        
        return conclusions
    
    def _extract_legal_citations(self, text: str) -> List[Dict[str, Any]]:
        """Extract legal citations from text"""
        citations = []
        
        # Basic citation patterns (to be enhanced with ML)
        import re
        
        # Federal court citation patterns
        fed_pattern = r'\b(\d+)\s+F\.\s*(?:2d|3d)?\s+(\d+)\b'
        fed_matches = re.finditer(fed_pattern, text, re.IGNORECASE)
        
        for match in fed_matches:
            volume = match.group(1)
            page = match.group(2)
            citation_text = match.group(0)
            
            citations.append({
                "text": citation_text,
                "type": "federal_case",
                "volume": volume,
                "page": page,
                "confidence": 0.8,
                "start_pos": match.start(),
                "end_pos": match.end(),
                "metadata": {
                    "citation_type": "federal_reporter",
                    "pattern_matched": "federal_court"
                }
            })
        
        # U.S. Supreme Court citations
        scotus_pattern = r'\b(\d+)\s+U\.S\.\s+(\d+)\b'
        scotus_matches = re.finditer(scotus_pattern, text, re.IGNORECASE)
        
        for match in scotus_matches:
            volume = match.group(1)
            page = match.group(2)
            citation_text = match.group(0)
            
            citations.append({
                "text": citation_text,
                "type": "supreme_court",
                "volume": volume,
                "page": page, 
                "confidence": 0.9,
                "start_pos": match.start(),
                "end_pos": match.end(),
                "metadata": {
                    "citation_type": "us_reports",
                    "pattern_matched": "supreme_court"
                }
            })
        
        return citations
    
    def _extract_caselaw_entities(self, text: str) -> List[Dict[str, Any]]:
        """Extract case law related entities from text"""
        entities = []
        
        # Basic entity extraction patterns
        import re
        
        # Case names (basic pattern)
        case_pattern = r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+v\.\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)'
        case_matches = re.finditer(case_pattern, text)
        
        for match in case_matches:
            plaintiff = match.group(1)
            defendant = match.group(2)
            case_name = match.group(0)
            
            entities.append({
                "type": "CASE_NAME",
                "text": case_name,
                "plaintiff": plaintiff,
                "defendant": defendant,
                "confidence": 0.75,
                "metadata": {
                    "category": "caselaw",
                    "entity_type": "case_reference"
                }
            })
        
        # Court references
        court_pattern = r'\b(Supreme Court|Court of Appeals|District Court|Circuit Court)\b'
        court_matches = re.finditer(court_pattern, text, re.IGNORECASE)
        
        for match in court_matches:
            court_name = match.group(0)
            
            entities.append({
                "type": "COURT",
                "text": court_name,
                "confidence": 0.8,
                "metadata": {
                    "category": "caselaw",
                    "entity_type": "court_reference"
                }
            })
        
        # Legal precedent terms
        precedent_pattern = r'\b(precedent|stare decisis|binding|persuasive|overrule[ds]?|distinguish(?:ed|ing)?|follow(?:ed|ing)?)\b'
        precedent_matches = re.finditer(precedent_pattern, text, re.IGNORECASE)
        
        for match in precedent_matches:
            precedent_term = match.group(0)
            
            entities.append({
                "type": "PRECEDENT_TERM",
                "text": precedent_term,
                "confidence": 0.7,
                "metadata": {
                    "category": "caselaw",
                    "entity_type": "precedent_reference"
                }
            })
        
        return entities
    
    def _entities_to_facts(self, entities: List[Dict[str, Any]], prov: Provenance) -> List[Node]:
        """Convert extracted entities to graph facts"""
        facts = []
        
        # Group entities by type to create meaningful facts
        entity_groups = {}
        for entity in entities:
            entity_type = entity["type"]
            if entity_type not in entity_groups:
                entity_groups[entity_type] = []
            entity_groups[entity_type].append(entity)
        
        # Convert entity groups to facts based on caselaw patterns
        for entity_type, group_entities in entity_groups.items():
            if entity_type == "CASE_NAME":
                # Create case reference facts
                for entity in group_entities:
                    fact = mk_node("Fact", {
                        "statement": "case_cited",
                        "case_name": entity["text"],
                        "plaintiff": entity.get("plaintiff", ""),
                        "defendant": entity.get("defendant", ""),
                        "entity_type": entity_type
                    }, prov)
                    facts.append(fact)
                    
            elif entity_type == "COURT":
                # Create court authority facts
                court_text = " ".join([e["text"] for e in group_entities])
                fact = mk_node("Fact", {
                    "statement": "court_referenced",
                    "court_details": court_text,
                    "entity_type": entity_type
                }, prov)
                facts.append(fact)
                
            elif entity_type == "PRECEDENT_TERM":
                # Create precedential relationship facts
                precedent_text = " ".join([e["text"] for e in group_entities])
                fact = mk_node("Fact", {
                    "statement": "precedential_analysis_present",
                    "precedent_terms": precedent_text,
                    "entity_type": entity_type
                }, prov)
                facts.append(fact)
        
        return facts
    
    def _extract_conclusions(self, derived_facts: List[Node]) -> List[Dict[str, Any]]:
        """Extract high-level conclusions from derived facts"""
        conclusions = []
        
        # Look for key conclusion patterns
        for fact in derived_facts:
            statement = fact.data.get("statement", "")
            
            if statement == "case_cited":
                conclusions.append({
                    "type": "CASE_LAW_ANALYSIS",
                    "conclusion": "Legal precedent cited in document",
                    "legal_basis": "Case law citation identified",
                    "confidence": fact.prov.confidence,
                    "fact_id": fact.id
                })
                
            elif statement == "precedential_analysis_present":
                conclusions.append({
                    "type": "PRECEDENTIAL_REASONING",
                    "conclusion": "Document contains precedential legal analysis",
                    "legal_basis": "Precedential terms and reasoning identified",
                    "confidence": fact.prov.confidence,
                    "fact_id": fact.id
                })
        
        return conclusions
    
    def get_supported_domains(self) -> List[str]:
        """Get list of supported legal domains"""
        return [
            "case_law",
            "precedent_analysis",
            "citation_resolution",
            "case_relationships",
            "temporal_reasoning",
            "jurisdictional_analysis",
            "provenance_tracking",
            "hf_dataset_ingestion",
            "legal_claim_verification",
            "precedent_queries"
        ]
    
    def validate_canonical_identifiers(self) -> Dict[str, Any]:
        """Enhanced validation of canonical identifier system"""
        test_results = {}
        
        # Test document ID creation
        try:
            doc_id = self.id_generator.generate_document_id(12345)
            test_results["document_id"] = {"valid": True, "example": str(doc_id)}
        except Exception as e:
            test_results["document_id"] = {"valid": False, "error": str(e)}
            
        # Test citation ID creation
        try:
            citation_id = self.id_generator.generate_citation_id_from_citation("410 U.S. 113")
            test_results["citation_id"] = {"valid": True, "example": str(citation_id) if citation_id else "None"}
        except Exception as e:
            test_results["citation_id"] = {"valid": False, "error": str(e)}
            
        # Test paragraph ID creation
        try:
            para_id = self.id_generator.generate_paragraph_id("cap:12345", 1)
            test_results["paragraph_id"] = {"valid": True, "example": str(para_id)}
        except Exception as e:
            test_results["paragraph_id"] = {"valid": False, "error": str(e)}
            
        # Test identifier validation
        test_results["identifier_validation"] = {
            "valid_doc_id": self.identifier_factory.validate_identifier("cap:12345"),
            "invalid_id": self.identifier_factory.validate_identifier("invalid_format")
        }
        
        return {
            "all_valid": all(result.get("valid", False) for result in test_results.values() if isinstance(result, dict) and "valid" in result),
            "test_results": test_results
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """Enhanced plugin health check"""
        health_status = {
            "plugin_name": self.name,
            "version": self.version,
            "status": "healthy",
            "initialized": self._initialized,
            "canonical_ids_valid": self.validate_canonical_identifiers()["all_valid"],
            "supported_domains": self.get_supported_domains(),
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Check component health if initialized
        if self._initialized:
            try:
                # Test storage connection
                storage_healthy = await self._check_storage_health()
                health_status["storage_health"] = storage_healthy
                
                # Test API components
                health_status["query_api_available"] = self.query_api is not None
                health_status["provenance_api_available"] = self.provenance_api is not None
                
                # Test extraction components
                health_status["citation_extractor_available"] = self.citation_extractor is not None
                health_status["relationship_extractor_available"] = self.relationship_extractor is not None
                
                # Test reasoning engines
                health_status["temporal_reasoner_available"] = self.temporal_reasoner is not None
                health_status["jurisdictional_reasoner_available"] = self.jurisdictional_reasoner is not None
                
                # Test ingestion pipeline
                health_status["ingestion_pipeline_available"] = self.ingestion_pipeline is not None
                
                # Background tasks status
                health_status["background_tasks_count"] = len(self._background_tasks)
                
                # Overall health
                component_checks = [
                    storage_healthy,
                    health_status["query_api_available"],
                    health_status["provenance_api_available"],
                    health_status["citation_extractor_available"],
                    health_status["relationship_extractor_available"]
                ]
                
                if all(component_checks):
                    health_status["status"] = "healthy"
                elif any(component_checks):
                    health_status["status"] = "degraded"
                else:
                    health_status["status"] = "unhealthy"
                    
            except Exception as e:
                health_status["status"] = "error"
                health_status["error"] = str(e)
        else:
            health_status["status"] = "not_initialized"
            
        return health_status
    
    async def _check_storage_health(self) -> bool:
        """Check storage backend health"""
        try:
            if hasattr(self.hypergraph_store, 'health_check'):
                return await self.hypergraph_store.health_check()
            return True
        except Exception as e:
            logger.warning(f"Storage health check failed: {e}")
            return False
    
    def get_plugin_info(self) -> Dict[str, Any]:
        """Get comprehensive plugin information"""
        return {
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "supported_domains": self.get_supported_domains(),
            "capabilities": {
                "ml_citation_extraction": True,
                "case_relationship_mapping": True,
                "temporal_reasoning": True,
                "jurisdictional_analysis": True,
                "provenance_tracking": True,
                "hf_dataset_ingestion": True,
                "hypergraph_storage": True,
                "audit_trails": True,
                "why_from_where_answers": True
            },
            "configuration_options": {
                "storage": "Storage backend configuration",
                "ingestion_batch_size": "HuggingFace ingestion batch size",
                "ingestion_max_workers": "Maximum ingestion workers",
                "auto_start_ingestion": "Auto-start background ingestion",
                "enable_background_ingestion": "Enable background processing"
            },
            "api_endpoints": {
                "analyze_document": "Enhanced document analysis",
                "query_precedents": "Legal precedent queries",
                "trace_provenance": "Complete provenance tracing",
                "answer_why_question": "Answer 'why' questions",
                "answer_from_where_question": "Answer 'from where' questions",
                "verify_legal_claim": "Legal claim verification"
            }
        }