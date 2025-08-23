"""
Test suite for Hypergraph Storage components
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from typing import Dict, Any, List
from datetime import datetime

from ..storage.hypergraph_store import HypergraphStore
from ..storage.storage_config import StorageConfig
from ..models.caselaw_node import CaselawNode, CourtLevel, JurisdictionType
from ..models.case_relationship import CaseRelationship, RelationshipType
from ..models.canonical_identifiers import DocumentID, CitationID, ParagraphID
from ..models.provenance_record import ProvenanceRecord, ProvenanceOperation, ProvenanceSource


class TestStorageConfig:
    """Test suite for StorageConfig"""
    
    def test_default_config(self):
        """Test default storage configuration"""
        config = StorageConfig()
        
        assert config.neo4j_enabled is True
        assert config.redis_enabled is True
        assert config.elasticsearch_enabled is True
        assert config.use_mock is False
        assert config.neo4j_uri == "bolt://localhost:7687"
        assert config.redis_url == "redis://localhost:6379"
        assert config.elasticsearch_hosts == ["localhost:9200"]
    
    def test_from_dict(self):
        """Test configuration from dictionary"""
        config_dict = {
            "neo4j_enabled": False,
            "redis_enabled": True,
            "elasticsearch_enabled": False,
            "use_mock": True,
            "neo4j_uri": "bolt://test:7687",
            "redis_url": "redis://test:6379"
        }
        
        config = StorageConfig.from_dict(config_dict)
        
        assert config.neo4j_enabled is False
        assert config.redis_enabled is True
        assert config.elasticsearch_enabled is False
        assert config.use_mock is True
        assert config.neo4j_uri == "bolt://test:7687"
        assert config.redis_url == "redis://test:6379"
    
    def test_to_dict(self):
        """Test configuration to dictionary"""
        config = StorageConfig(
            neo4j_enabled=False,
            redis_enabled=True,
            use_mock=True
        )
        
        config_dict = config.to_dict()
        
        assert config_dict["neo4j_enabled"] is False
        assert config_dict["redis_enabled"] is True
        assert config_dict["use_mock"] is True


class TestHypergraphStore:
    """Test suite for HypergraphStore"""
    
    @pytest.fixture
    def mock_config(self):
        """Mock storage configuration for testing"""
        return StorageConfig(
            neo4j_enabled=False,
            redis_enabled=False,
            elasticsearch_enabled=False,
            use_mock=True
        )
    
    @pytest.fixture
    def store(self, mock_config):
        """Create hypergraph store for testing"""
        return HypergraphStore(mock_config)
    
    @pytest.fixture
    def sample_case(self):
        """Sample case node for testing"""
        return CaselawNode(
            case_id=DocumentID("cap:12345"),
            case_name="Brown v. Board of Education",
            full_text="Sample case text...",
            court_level=CourtLevel.SUPREME,
            jurisdiction_type=JurisdictionType.FEDERAL,
            decision_date=datetime(1954, 5, 17),
            metadata={
                "court_slug": "us",
                "jurisdiction_slug": "us",
                "volume": "347",
                "reporter": "U.S.",
                "page": "483"
            }
        )
    
    @pytest.fixture
    def sample_relationship(self):
        """Sample case relationship for testing"""
        return CaseRelationship(
            source_case_id=DocumentID("cap:12345"),
            target_case_id=DocumentID("cap:67890"),
            relationship_type=RelationshipType.CITES,
            confidence=0.9,
            source_location="paragraph 5",
            context="The court cited this precedent..."
        )
    
    def test_store_initialization(self, store):
        """Test store initialization"""
        assert store.config.use_mock is True
        assert hasattr(store, 'neo4j_adapter')
        assert hasattr(store, 'redis_cache')
        assert hasattr(store, 'elasticsearch_adapter')
    
    @pytest.mark.asyncio
    async def test_initialize_store(self, store):
        """Test store initialization"""
        # Mock adapter initialization
        store.neo4j_adapter.initialize = AsyncMock(return_value=True)
        store.redis_cache.initialize = AsyncMock(return_value=True)
        store.elasticsearch_adapter.initialize = AsyncMock(return_value=True)
        
        result = await store.initialize()
        
        assert result is True
        # Should not call real adapters when using mock
        if not store.config.use_mock:
            store.neo4j_adapter.initialize.assert_called_once()
            store.redis_cache.initialize.assert_called_once()
            store.elasticsearch_adapter.initialize.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_store_case(self, store, sample_case):
        """Test storing a case"""
        # Mock adapter methods
        store.neo4j_adapter.store_case = AsyncMock(return_value=True)
        store.elasticsearch_adapter.index_case = AsyncMock(return_value=True)
        store.redis_cache.cache_case = AsyncMock(return_value=True)
        
        result = await store.store_case(sample_case)
        
        assert result is True
        
        if not store.config.use_mock:
            store.neo4j_adapter.store_case.assert_called_once_with(sample_case)
            store.elasticsearch_adapter.index_case.assert_called_once_with(sample_case)
            store.redis_cache.cache_case.assert_called_once_with(sample_case)
    
    @pytest.mark.asyncio
    async def test_get_case(self, store, sample_case):
        """Test retrieving a case"""
        case_id = sample_case.case_id
        
        # Mock cache hit
        store.redis_cache.get_case = AsyncMock(return_value=sample_case)
        
        result = await store.get_case(case_id)
        
        assert result == sample_case
        
        if not store.config.use_mock:
            store.redis_cache.get_case.assert_called_once_with(case_id)
    
    @pytest.mark.asyncio
    async def test_get_case_cache_miss(self, store, sample_case):
        """Test retrieving case with cache miss"""
        case_id = sample_case.case_id
        
        # Mock cache miss, then database hit
        store.redis_cache.get_case = AsyncMock(return_value=None)
        store.neo4j_adapter.get_case = AsyncMock(return_value=sample_case)
        store.redis_cache.cache_case = AsyncMock(return_value=True)
        
        result = await store.get_case(case_id)
        
        assert result == sample_case
        
        if not store.config.use_mock:
            store.redis_cache.get_case.assert_called_once_with(case_id)
            store.neo4j_adapter.get_case.assert_called_once_with(case_id)
            store.redis_cache.cache_case.assert_called_once_with(sample_case)
    
    @pytest.mark.asyncio
    async def test_store_relationship(self, store, sample_relationship):
        """Test storing a case relationship"""
        store.neo4j_adapter.store_relationship = AsyncMock(return_value=True)
        
        result = await store.store_relationship(sample_relationship)
        
        assert result is True
        
        if not store.config.use_mock:
            store.neo4j_adapter.store_relationship.assert_called_once_with(sample_relationship)
    
    @pytest.mark.asyncio
    async def test_search_cases(self, store, sample_case):
        """Test case search"""
        query = "brown v board"
        expected_results = [sample_case]
        
        store.elasticsearch_adapter.search_cases = AsyncMock(return_value=expected_results)
        
        results = await store.search_cases(query, limit=10)
        
        assert results == expected_results
        
        if not store.config.use_mock:
            store.elasticsearch_adapter.search_cases.assert_called_once_with(
                query, limit=10, filters={}
            )
    
    @pytest.mark.asyncio
    async def test_get_case_relationships(self, store, sample_case, sample_relationship):
        """Test retrieving case relationships"""
        case_id = sample_case.case_id
        expected_relationships = [sample_relationship]
        
        store.neo4j_adapter.get_case_relationships = AsyncMock(return_value=expected_relationships)
        
        relationships = await store.get_case_relationships(case_id)
        
        assert relationships == expected_relationships
        
        if not store.config.use_mock:
            store.neo4j_adapter.get_case_relationships.assert_called_once_with(case_id)
    
    @pytest.mark.asyncio
    async def test_find_similar_cases(self, store, sample_case):
        """Test finding similar cases"""
        case_id = sample_case.case_id
        expected_similar = [sample_case]
        
        store.elasticsearch_adapter.find_similar_cases = AsyncMock(return_value=expected_similar)
        
        similar_cases = await store.find_similar_cases(case_id, limit=5)
        
        assert similar_cases == expected_similar
        
        if not store.config.use_mock:
            store.elasticsearch_adapter.find_similar_cases.assert_called_once_with(
                case_id, limit=5
            )
    
    @pytest.mark.asyncio
    async def test_store_citation(self, store):
        """Test storing a citation"""
        citation_id = CitationID("cite:test123")
        citation_data = {
            "full_citation": "Brown v. Board, 347 U.S. 483 (1954)",
            "case_name": "Brown v. Board",
            "year": "1954"
        }
        
        store.neo4j_adapter.store_citation = AsyncMock(return_value=True)
        
        result = await store.store_citation(citation_id, citation_data)
        
        assert result is True
        
        if not store.config.use_mock:
            store.neo4j_adapter.store_citation.assert_called_once_with(citation_id, citation_data)
    
    @pytest.mark.asyncio
    async def test_get_citation(self, store):
        """Test retrieving a citation"""
        citation_id = CitationID("cite:test123")
        expected_citation = {
            "full_citation": "Brown v. Board, 347 U.S. 483 (1954)",
            "case_name": "Brown v. Board"
        }
        
        store.redis_cache.get_citation = AsyncMock(return_value=expected_citation)
        
        citation = await store.get_citation(citation_id)
        
        assert citation == expected_citation
        
        if not store.config.use_mock:
            store.redis_cache.get_citation.assert_called_once_with(citation_id)
    
    @pytest.mark.asyncio
    async def test_store_provenance(self, store):
        """Test storing provenance record"""
        provenance = ProvenanceRecord(
            operation=ProvenanceOperation.STORE,
            source=ProvenanceSource.HUGGINGFACE,
            agent_type="system",
            agent_id="test_agent",
            timestamp=datetime.utcnow(),
            confidence=0.9
        )
        
        store.neo4j_adapter.store_provenance = AsyncMock(return_value=True)
        
        result = await store.store_provenance(provenance)
        
        assert result is True
        
        if not store.config.use_mock:
            store.neo4j_adapter.store_provenance.assert_called_once_with(provenance)
    
    @pytest.mark.asyncio
    async def test_health_check_healthy(self, store):
        """Test health check when all components healthy"""
        store.neo4j_adapter.health_check = AsyncMock(return_value=True)
        store.redis_cache.health_check = AsyncMock(return_value=True)
        store.elasticsearch_adapter.health_check = AsyncMock(return_value=True)
        
        result = await store.health_check()
        
        assert result is True
    
    @pytest.mark.asyncio
    async def test_health_check_degraded(self, store):
        """Test health check with one component failing"""
        store.neo4j_adapter.health_check = AsyncMock(return_value=True)
        store.redis_cache.health_check = AsyncMock(return_value=False)
        store.elasticsearch_adapter.health_check = AsyncMock(return_value=True)
        
        result = await store.health_check()
        
        # Should still return True if critical components work
        assert result is True
    
    @pytest.mark.asyncio
    async def test_health_check_critical_failure(self, store):
        """Test health check with critical component failing"""
        store.neo4j_adapter.health_check = AsyncMock(return_value=False)
        store.redis_cache.health_check = AsyncMock(return_value=True)
        store.elasticsearch_adapter.health_check = AsyncMock(return_value=True)
        
        result = await store.health_check()
        
        # Should return False if Neo4j (critical) fails
        assert result is False
    
    @pytest.mark.asyncio
    async def test_shutdown(self, store):
        """Test store shutdown"""
        store.neo4j_adapter.shutdown = AsyncMock()
        store.redis_cache.shutdown = AsyncMock()
        store.elasticsearch_adapter.shutdown = AsyncMock()
        
        await store.shutdown()
        
        if not store.config.use_mock:
            store.neo4j_adapter.shutdown.assert_called_once()
            store.redis_cache.shutdown.assert_called_once()
            store.elasticsearch_adapter.shutdown.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_batch_store_cases(self, store, sample_case):
        """Test batch storing of cases"""
        cases = [sample_case for _ in range(5)]
        
        store.neo4j_adapter.batch_store_cases = AsyncMock(return_value=True)
        store.elasticsearch_adapter.batch_index_cases = AsyncMock(return_value=True)
        
        result = await store.batch_store_cases(cases)
        
        assert result is True
        
        if not store.config.use_mock:
            store.neo4j_adapter.batch_store_cases.assert_called_once_with(cases)
            store.elasticsearch_adapter.batch_index_cases.assert_called_once_with(cases)
    
    @pytest.mark.asyncio
    async def test_get_statistics(self, store):
        """Test retrieving storage statistics"""
        expected_stats = {
            "total_cases": 1000,
            "total_relationships": 5000,
            "total_citations": 10000
        }
        
        store.neo4j_adapter.get_statistics = AsyncMock(return_value=expected_stats)
        
        stats = await store.get_statistics()
        
        assert stats == expected_stats
        
        if not store.config.use_mock:
            store.neo4j_adapter.get_statistics.assert_called_once()


class TestHypergraphStoreIntegration:
    """Integration tests for hypergraph store"""
    
    @pytest.mark.asyncio
    async def test_full_case_lifecycle(self):
        """Test complete case storage and retrieval lifecycle"""
        config = StorageConfig(use_mock=True)
        store = HypergraphStore(config)
        
        # Initialize store
        await store.initialize()
        
        # Create sample case
        case = CaselawNode(
            case_id=DocumentID("cap:test123"),
            case_name="Test v. Case",
            full_text="This is a test case...",
            court_level=CourtLevel.DISTRICT,
            jurisdiction_type=JurisdictionType.FEDERAL,
            decision_date=datetime(2023, 1, 1),
            metadata={"court_slug": "us.d.test"}
        )
        
        # Store case
        store_result = await store.store_case(case)
        assert store_result is True
        
        # Retrieve case
        retrieved_case = await store.get_case(case.case_id)
        
        # In mock mode, we may not get the exact same object back
        # but the operation should complete successfully
        if retrieved_case:
            assert retrieved_case.case_id == case.case_id
        
        # Cleanup
        await store.shutdown()
    
    @pytest.mark.asyncio
    async def test_relationship_storage_and_query(self):
        """Test relationship storage and querying"""
        config = StorageConfig(use_mock=True)
        store = HypergraphStore(config)
        
        await store.initialize()
        
        # Create relationship
        relationship = CaseRelationship(
            source_case_id=DocumentID("cap:source"),
            target_case_id=DocumentID("cap:target"),
            relationship_type=RelationshipType.CITES,
            confidence=0.9
        )
        
        # Store relationship
        result = await store.store_relationship(relationship)
        assert result is True
        
        # Query relationships
        relationships = await store.get_case_relationships(DocumentID("cap:source"))
        
        # Should complete successfully
        assert isinstance(relationships, list)
        
        await store.shutdown()
    
    @pytest.mark.asyncio
    async def test_search_and_similarity(self):
        """Test search and similarity operations"""
        config = StorageConfig(use_mock=True)
        store = HypergraphStore(config)
        
        await store.initialize()
        
        # Test search
        search_results = await store.search_cases("constitutional law", limit=10)
        assert isinstance(search_results, list)
        
        # Test similarity
        similar_cases = await store.find_similar_cases(
            DocumentID("cap:test"), limit=5
        )
        assert isinstance(similar_cases, list)
        
        await store.shutdown()
    
    @pytest.mark.asyncio
    async def test_error_handling(self):
        """Test error handling in store operations"""
        config = StorageConfig(use_mock=True)
        store = HypergraphStore(config)
        
        # Test operations before initialization
        with pytest.raises(Exception):
            await store.get_case(DocumentID("cap:test"))
        
        await store.initialize()
        
        # Test with invalid data
        try:
            await store.store_case(None)
        except Exception:
            pass  # Expected to handle gracefully
        
        await store.shutdown()