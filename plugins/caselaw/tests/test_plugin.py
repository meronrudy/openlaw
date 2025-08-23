"""
Test suite for CAP Caselaw Plugin core functionality
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from typing import Dict, Any
from datetime import datetime

from core.model import Context, mk_node, Provenance

from ..plugin import CaselawPlugin
from ..models.canonical_identifiers import DocumentID
from ..models.provenance_record import ProvenanceRecord, ProvenanceOperation


class TestCaselawPlugin:
    """Test suite for CaselawPlugin class"""
    
    @pytest.fixture
    def plugin_config(self):
        """Plugin configuration for testing"""
        return {
            "storage": {
                "use_mock": True,
                "neo4j_enabled": False,
                "redis_enabled": False,
                "elasticsearch_enabled": False
            },
            "ingestion_batch_size": 10,
            "ingestion_max_workers": 2,
            "auto_start_ingestion": False,
            "enable_background_ingestion": False
        }
    
    @pytest.fixture
    def plugin(self, plugin_config):
        """Create plugin instance for testing"""
        return CaselawPlugin(config=plugin_config)
    
    @pytest.fixture
    def sample_legal_text(self):
        """Sample legal text for testing"""
        return """
        In Smith v. Jones, 410 U.S. 113 (1973), the Supreme Court held that 
        procedural due process requires notice and an opportunity to be heard.
        This precedent was followed in Brown v. Board, 347 U.S. 483 (1954),
        which established the principle that separate educational facilities 
        are inherently unequal. The Court of Appeals distinguished this case
        from earlier precedents and overruled the district court's decision.
        """
    
    @pytest.fixture
    def sample_context(self):
        """Sample context for testing"""
        return Context(
            domain="constitutional_law",
            jurisdiction="federal",
            user_id="test_user",
            session_id="test_session"
        )
    
    def test_plugin_initialization(self, plugin):
        """Test plugin initialization"""
        assert plugin.name == "Case Law Access Project"
        assert plugin.version == "1.0.0"
        assert plugin.description is not None
        assert hasattr(plugin, 'config')
        assert hasattr(plugin, 'identifier_factory')
        assert hasattr(plugin, 'id_generator')
        assert hasattr(plugin, 'hypergraph_store')
        assert hasattr(plugin, 'citation_extractor')
        assert hasattr(plugin, 'relationship_extractor')
        assert hasattr(plugin, 'temporal_reasoner')
        assert hasattr(plugin, 'jurisdictional_reasoner')
        assert hasattr(plugin, 'query_api')
        assert hasattr(plugin, 'provenance_api')
        assert hasattr(plugin, 'ingestion_pipeline')
        assert not plugin._initialized
    
    @pytest.mark.asyncio
    async def test_plugin_async_initialization(self, plugin):
        """Test async initialization"""
        # Mock storage initialization
        plugin.hypergraph_store.initialize = AsyncMock(return_value=True)
        
        result = await plugin.initialize()
        
        assert result is True
        assert plugin._initialized is True
        plugin.hypergraph_store.initialize.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_plugin_shutdown(self, plugin):
        """Test plugin shutdown"""
        # Initialize first
        plugin._initialized = True
        plugin._background_tasks = [Mock()]
        plugin._background_tasks[0].cancel = Mock()
        
        # Mock shutdown methods
        plugin.hypergraph_store.shutdown = AsyncMock()
        plugin.ingestion_pipeline.stop_processing = Mock()
        
        await plugin.shutdown()
        
        plugin._background_tasks[0].cancel.assert_called_once()
        plugin.hypergraph_store.shutdown.assert_called_once()
        plugin.ingestion_pipeline.stop_processing.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_analyze_document(self, plugin, sample_legal_text, sample_context):
        """Test document analysis functionality"""
        # Mock initialization
        plugin._initialized = True
        
        # Mock extraction components
        mock_citations = [Mock()]
        mock_citations[0].to_dict = Mock(return_value={"citation": "test"})
        mock_citations[0].confidence = 0.9
        mock_citations[0].citation_type = "federal_case"
        
        mock_relationships = [Mock()]
        mock_relationships[0].to_dict = Mock(return_value={"relationship": "test"})
        mock_relationships[0].confidence = 0.8
        mock_relationships[0].relationship_type = Mock()
        mock_relationships[0].relationship_type.value = "cites"
        
        plugin.citation_extractor.extract_citations = Mock(return_value=mock_citations)
        plugin.relationship_extractor.extract_relationships = Mock(return_value=mock_relationships)
        
        result = await plugin.analyze_document(sample_legal_text, sample_context)
        
        # Verify result structure
        assert "document_id" in result
        assert "citations" in result
        assert "relationships" in result
        assert "provenance" in result
        assert "entities" in result
        assert "conclusions" in result
        assert "analysis_timestamp" in result
        assert "plugin_version" in result
        
        # Verify data
        assert len(result["citations"]) == 1
        assert len(result["relationships"]) == 1
        assert result["plugin_version"] == plugin.version
        
        # Verify method calls
        plugin.citation_extractor.extract_citations.assert_called_once()
        plugin.relationship_extractor.extract_relationships.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_analyze_document_error_handling(self, plugin, sample_legal_text, sample_context):
        """Test error handling in document analysis"""
        # Force an error
        plugin.citation_extractor.extract_citations = Mock(side_effect=Exception("Test error"))
        
        result = await plugin.analyze_document(sample_legal_text, sample_context)
        
        assert "error" in result
        assert result["error"] == "Test error"
        assert result["entities"] == []
        assert result["citations"] == []
        assert result["relationships"] == []
        assert result["conclusions"] == []
    
    @pytest.mark.asyncio
    async def test_query_precedents(self, plugin):
        """Test precedent querying"""
        plugin._initialized = True
        plugin.query_api.find_precedents = AsyncMock(return_value={"precedents": []})
        
        result = await plugin.query_precedents(
            legal_issue="constitutional due process",
            jurisdiction="federal",
            date_range={"start": "2000-01-01", "end": "2023-12-31"}
        )
        
        assert result == {"precedents": []}
        plugin.query_api.find_precedents.assert_called_once_with(
            legal_issue="constitutional due process",
            jurisdiction="federal",
            date_range={"start": "2000-01-01", "end": "2023-12-31"}
        )
    
    @pytest.mark.asyncio
    async def test_trace_provenance(self, plugin):
        """Test provenance tracing"""
        plugin._initialized = True
        
        mock_chain = Mock()
        mock_chain.to_dict = Mock(return_value={"provenance": "chain"})
        plugin.provenance_api.trace_legal_conclusion = AsyncMock(return_value=mock_chain)
        
        result = await plugin.trace_provenance("test conclusion", {"context": "test"})
        
        assert result == {"provenance": "chain"}
        plugin.provenance_api.trace_legal_conclusion.assert_called_once_with(
            "test conclusion", {"context": "test"}
        )
    
    @pytest.mark.asyncio
    async def test_answer_why_question(self, plugin):
        """Test why question answering"""
        plugin._initialized = True
        
        mock_answer = Mock()
        mock_answer.to_dict = Mock(return_value={"answer": "test"})
        plugin.provenance_api.answer_why_question = AsyncMock(return_value=mock_answer)
        
        result = await plugin.answer_why_question("Why is this legal?", {"context": "test"})
        
        assert result == {"answer": "test"}
        plugin.provenance_api.answer_why_question.assert_called_once_with(
            "Why is this legal?", {"context": "test"}
        )
    
    @pytest.mark.asyncio
    async def test_answer_from_where_question(self, plugin):
        """Test from where question answering"""
        plugin._initialized = True
        
        mock_answer = Mock()
        mock_answer.to_dict = Mock(return_value={"source": "test"})
        plugin.provenance_api.answer_from_where_question = AsyncMock(return_value=mock_answer)
        
        result = await plugin.answer_from_where_question(
            "From where does this come?", "test claim", {"context": "test"}
        )
        
        assert result == {"source": "test"}
        plugin.provenance_api.answer_from_where_question.assert_called_once_with(
            "From where does this come?", "test claim", {"context": "test"}
        )
    
    @pytest.mark.asyncio
    async def test_verify_legal_claim(self, plugin):
        """Test legal claim verification"""
        plugin._initialized = True
        plugin.provenance_api.verify_legal_claim = AsyncMock(return_value={"verified": True})
        
        result = await plugin.verify_legal_claim(
            "test claim", ["source1", "source2"], {"context": "test"}
        )
        
        assert result == {"verified": True}
        plugin.provenance_api.verify_legal_claim.assert_called_once_with(
            "test claim", ["source1", "source2"], {"context": "test"}
        )
    
    def test_get_supported_domains(self, plugin):
        """Test supported domains"""
        domains = plugin.get_supported_domains()
        
        expected_domains = [
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
        
        assert domains == expected_domains
    
    def test_validate_canonical_identifiers(self, plugin):
        """Test canonical identifier validation"""
        result = plugin.validate_canonical_identifiers()
        
        assert "all_valid" in result
        assert "test_results" in result
        
        test_results = result["test_results"]
        assert "document_id" in test_results
        assert "citation_id" in test_results
        assert "paragraph_id" in test_results
        assert "identifier_validation" in test_results
    
    @pytest.mark.asyncio
    async def test_health_check_not_initialized(self, plugin):
        """Test health check when not initialized"""
        result = await plugin.health_check()
        
        assert result["plugin_name"] == plugin.name
        assert result["version"] == plugin.version
        assert result["status"] == "not_initialized"
        assert result["initialized"] is False
    
    @pytest.mark.asyncio
    async def test_health_check_initialized(self, plugin):
        """Test health check when initialized"""
        plugin._initialized = True
        plugin._check_storage_health = AsyncMock(return_value=True)
        
        result = await plugin.health_check()
        
        assert result["status"] == "healthy"
        assert result["initialized"] is True
        assert result["storage_health"] is True
        assert result["query_api_available"] is True
        assert result["provenance_api_available"] is True
    
    @pytest.mark.asyncio
    async def test_health_check_degraded(self, plugin):
        """Test health check with some components failing"""
        plugin._initialized = True
        plugin._check_storage_health = AsyncMock(return_value=False)
        
        result = await plugin.health_check()
        
        assert result["status"] == "degraded"
        assert result["storage_health"] is False
    
    @pytest.mark.asyncio
    async def test_health_check_error(self, plugin):
        """Test health check with error"""
        plugin._initialized = True
        plugin._check_storage_health = AsyncMock(side_effect=Exception("Test error"))
        
        result = await plugin.health_check()
        
        assert result["status"] == "error"
        assert "error" in result
    
    def test_get_plugin_info(self, plugin):
        """Test plugin info retrieval"""
        info = plugin.get_plugin_info()
        
        assert info["name"] == plugin.name
        assert info["version"] == plugin.version
        assert info["description"] == plugin.description
        assert "supported_domains" in info
        assert "capabilities" in info
        assert "configuration_options" in info
        assert "api_endpoints" in info
        
        # Verify capabilities
        capabilities = info["capabilities"]
        assert capabilities["ml_citation_extraction"] is True
        assert capabilities["case_relationship_mapping"] is True
        assert capabilities["temporal_reasoning"] is True
        assert capabilities["jurisdictional_analysis"] is True
        assert capabilities["provenance_tracking"] is True
        assert capabilities["hf_dataset_ingestion"] is True
        assert capabilities["hypergraph_storage"] is True
        assert capabilities["audit_trails"] is True
        assert capabilities["why_from_where_answers"] is True
    
    def test_extract_legal_citations_basic(self, plugin, sample_legal_text):
        """Test basic citation extraction"""
        citations = plugin._extract_legal_citations(sample_legal_text)
        
        # Should find at least the federal citations
        assert len(citations) >= 2
        
        # Check for expected citations
        citation_texts = [c["text"] for c in citations]
        assert any("410 U.S. 113" in text for text in citation_texts)
        assert any("347 U.S. 483" in text for text in citation_texts)
    
    def test_extract_caselaw_entities(self, plugin, sample_legal_text):
        """Test caselaw entity extraction"""
        entities = plugin._extract_caselaw_entities(sample_legal_text)
        
        # Should find case names, courts, and precedent terms
        entity_types = [e["type"] for e in entities]
        assert "CASE_NAME" in entity_types
        assert "COURT" in entity_types
        assert "PRECEDENT_TERM" in entity_types
        
        # Check for specific entities
        case_names = [e["text"] for e in entities if e["type"] == "CASE_NAME"]
        assert any("Smith v. Jones" in name for name in case_names)
        assert any("Brown v. Board" in name for name in case_names)
    
    def test_entities_to_facts(self, plugin):
        """Test entity to fact conversion"""
        entities = [
            {
                "type": "CASE_NAME",
                "text": "Smith v. Jones",
                "plaintiff": "Smith",
                "defendant": "Jones",
                "confidence": 0.8
            },
            {
                "type": "COURT", 
                "text": "Supreme Court",
                "confidence": 0.9
            }
        ]
        
        prov = Provenance(
            source=[{"type": "test"}],
            method="test",
            agent="test",
            time=datetime.utcnow(),
            confidence=0.8
        )
        
        facts = plugin._entities_to_facts(entities, prov)
        
        assert len(facts) == 2
        assert facts[0].data["statement"] == "case_cited"
        assert facts[1].data["statement"] == "court_referenced"
    
    def test_extract_conclusions(self, plugin):
        """Test conclusion extraction"""
        # Create mock facts
        fact1 = mk_node("Fact", {
            "statement": "case_cited",
            "case_name": "Smith v. Jones"
        }, Provenance(
            source=[{"type": "test"}],
            method="test", 
            agent="test",
            time=datetime.utcnow(),
            confidence=0.8
        ))
        
        fact2 = mk_node("Fact", {
            "statement": "precedential_analysis_present", 
            "precedent_terms": "stare decisis"
        }, Provenance(
            source=[{"type": "test"}],
            method="test",
            agent="test", 
            time=datetime.utcnow(),
            confidence=0.7
        ))
        
        conclusions = plugin._extract_conclusions([fact1, fact2])
        
        assert len(conclusions) == 2
        assert conclusions[0]["type"] == "CASE_LAW_ANALYSIS"
        assert conclusions[1]["type"] == "PRECEDENTIAL_REASONING"
        assert conclusions[0]["confidence"] == 0.8
        assert conclusions[1]["confidence"] == 0.7


class TestPluginIntegration:
    """Integration tests for the plugin"""
    
    @pytest.mark.asyncio
    async def test_full_document_analysis_workflow(self):
        """Test complete document analysis workflow"""
        config = {
            "storage": {"use_mock": True},
            "auto_start_ingestion": False,
            "enable_background_ingestion": False
        }
        
        plugin = CaselawPlugin(config=config)
        
        # Mock storage
        plugin.hypergraph_store.initialize = AsyncMock(return_value=True)
        
        # Initialize plugin
        await plugin.initialize()
        
        # Sample text
        text = "In Miranda v. Arizona, 384 U.S. 436 (1966), the Court held..."
        context = Context(domain="criminal_law", jurisdiction="federal")
        
        # Analyze document
        result = await plugin.analyze_document(text, context)
        
        # Verify comprehensive result
        assert "document_id" in result
        assert "citations" in result
        assert "relationships" in result
        assert "provenance" in result
        assert "entities" in result
        assert "conclusions" in result
        
        # Cleanup
        await plugin.shutdown()
    
    @pytest.mark.asyncio
    async def test_plugin_lifecycle(self):
        """Test complete plugin lifecycle"""
        config = {
            "storage": {"use_mock": True},
            "auto_start_ingestion": False
        }
        
        plugin = CaselawPlugin(config=config)
        
        # Mock dependencies
        plugin.hypergraph_store.initialize = AsyncMock(return_value=True)
        plugin.hypergraph_store.shutdown = AsyncMock()
        
        # Test lifecycle
        assert not plugin._initialized
        
        # Initialize
        result = await plugin.initialize()
        assert result is True
        assert plugin._initialized
        
        # Health check
        health = await plugin.health_check()
        assert health["status"] in ["healthy", "degraded"]  # Allow for mock limitations
        
        # Shutdown
        await plugin.shutdown()
        
        # Verify cleanup
        assert len(plugin._background_tasks) == 0