"""
Pytest configuration and shared fixtures for legal hypergraph system testing.

This file contains shared fixtures, configuration, and utilities used across
all test modules to support test-driven development and comprehensive testing.
"""

import pytest
import asyncio
import tempfile
import os
from pathlib import Path
from typing import Dict, Any, Generator
from unittest.mock import Mock, patch

# Import core system components
from core.system import LegalHypergraphSystem
from core.storage import GraphStore
from core.loader import PluginLoader
from core.model import Context, Provenance
from sdk.plugin import RawDoc
from tests.fixtures.legal_documents import TestDocuments, TestDocumentMetadata
from tests.helpers.legal_assertions import (
    LegalAssertions, PerformanceAssertions, SecurityAssertions, ComplianceAssertions
)


# Pytest configuration hooks
def pytest_configure(config):
    """Configure pytest with custom markers and settings"""
    config.addinivalue_line(
        "markers", "unit: Unit tests for individual components"
    )
    config.addinivalue_line(
        "markers", "integration: Integration tests for component interaction"
    )
    config.addinivalue_line(
        "markers", "e2e: End-to-end tests for complete workflows"
    )
    config.addinivalue_line(
        "markers", "performance: Performance and scalability tests"
    )
    config.addinivalue_line(
        "markers", "security: Security and compliance tests"
    )
    config.addinivalue_line(
        "markers", "slow: Tests that take more than 30 seconds"
    )


def pytest_collection_modifyitems(config, items):
    """Modify test collection to add markers based on test paths"""
    for item in items:
        # Add markers based on test file path
        if "e2e" in str(item.fspath):
            item.add_marker(pytest.mark.e2e)
        if "unit" in str(item.fspath):
            item.add_marker(pytest.mark.unit)
        if "integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)
            
        # Add markers based on test function names
        if "performance" in item.name:
            item.add_marker(pytest.mark.performance)
        if "security" in item.name:
            item.add_marker(pytest.mark.security)
        if "ada" in item.name.lower():
            item.add_marker(pytest.mark.ada)
        if "flsa" in item.name.lower():
            item.add_marker(pytest.mark.flsa)
        if "workers_comp" in item.name:
            item.add_marker(pytest.mark.workers_comp)
        if "multi_domain" in item.name:
            item.add_marker(pytest.mark.multi_domain)


# Event loop fixture for async testing
@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# Core system fixtures
@pytest.fixture(scope="session")
async def legal_system():
    """Session-scoped legal hypergraph system for testing"""
    system = LegalHypergraphSystem(
        storage_config={'path': ':memory:'},
        plugin_dirs=['tests/fixtures/plugins', 'plugins'],
        test_mode=True
    )
    
    try:
        await system.initialize()
        # Load employment plugin if available
        try:
            await system.load_plugin('employment-us')
        except Exception:
            pass  # Plugin might not exist in all test environments
        
        yield system
    finally:
        await system.shutdown()


@pytest.fixture
async def fresh_system():
    """Function-scoped fresh system instance for isolated testing"""
    system = LegalHypergraphSystem(
        storage_config={'path': ':memory:'},
        plugin_dirs=['tests/fixtures/plugins'],
        test_mode=True
    )
    
    try:
        await system.initialize()
        yield system
    finally:
        await system.shutdown()


@pytest.fixture
def memory_graph_store():
    """In-memory graph store for testing"""
    return GraphStore(':memory:')


@pytest.fixture
def temp_graph_store():
    """Temporary file-based graph store for testing"""
    with tempfile.NamedTemporaryFile(delete=False) as temp_file:
        store = GraphStore(temp_file.name)
        yield store
        # Cleanup
        try:
            os.unlink(temp_file.name)
        except OSError:
            pass


# Context and document fixtures
@pytest.fixture
def us_legal_context():
    """Standard US legal context for testing"""
    return Context(
        jurisdiction="US",
        law_type="statute",
        authority_level="federal"
    )


@pytest.fixture
def state_legal_context():
    """State-level legal context for testing"""
    return Context(
        jurisdiction="US-CA",
        law_type="statute",
        authority_level="state"
    )


@pytest.fixture
def test_documents():
    """Access to all test legal documents"""
    return TestDocuments


@pytest.fixture
def document_metadata():
    """Access to test document metadata"""
    return TestDocumentMetadata


@pytest.fixture
def sample_ada_document():
    """Sample ADA accommodation request document"""
    return RawDoc(
        id="test-ada-001",
        text=TestDocuments.ADA_ACCOMMODATION_REQUEST,
        meta={'domain': 'ada', 'test': True}
    )


@pytest.fixture
def sample_flsa_document():
    """Sample FLSA overtime scenario document"""
    return RawDoc(
        id="test-flsa-001", 
        text=TestDocuments.FLSA_OVERTIME_SCENARIO,
        meta={'domain': 'flsa', 'test': True}
    )


@pytest.fixture
def sample_multi_domain_document():
    """Sample multi-domain legal scenario document"""
    return RawDoc(
        id="test-multi-001",
        text=TestDocuments.MULTI_DOMAIN_SCENARIO,
        meta={'domain': 'multi', 'test': True}
    )


# Plugin testing fixtures
@pytest.fixture
def temp_plugin_directory():
    """Temporary directory for plugin testing"""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)


@pytest.fixture
def plugin_loader(temp_plugin_directory):
    """Plugin loader for testing"""
    return PluginLoader(str(temp_plugin_directory))


@pytest.fixture
def mock_plugin():
    """Mock plugin for testing plugin interfaces"""
    plugin = Mock()
    plugin.manifest.id = "test.mock"
    plugin.manifest.version = "1.0.0"
    plugin.provides_ontology = True
    plugin.provides_mapping = True
    plugin.provides_rules = True
    plugin.provides_explanation = True
    return plugin


# Assertion helper fixtures
@pytest.fixture
def legal_assertions():
    """Legal-specific assertion helpers"""
    return LegalAssertions()


@pytest.fixture
def performance_assertions():
    """Performance assertion helpers"""
    return PerformanceAssertions()


@pytest.fixture
def security_assertions():
    """Security assertion helpers"""
    return SecurityAssertions()


@pytest.fixture
def compliance_assertions():
    """Compliance assertion helpers"""
    return ComplianceAssertions()


# Utility fixtures
@pytest.fixture
def sample_provenance():
    """Sample provenance for testing"""
    from datetime import datetime
    return Provenance(
        source=[{"type": "test", "id": "test-source"}],
        method="test.method",
        agent="test.agent",
        time=datetime.utcnow(),
        confidence=0.9
    )


@pytest.fixture
def mock_nlp_pipeline():
    """Mock NLP pipeline for testing without heavy ML dependencies"""
    with patch('nlp.legal_ner.LegalNERPipeline') as mock_ner:
        mock_instance = Mock()
        mock_instance.extract_legal_entities.return_value = [
            {
                'entity_group': 'PERSON',
                'word': 'John Doe',
                'start': 0,
                'end': 8,
                'score': 0.99
            }
        ]
        mock_ner.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def performance_monitor():
    """Performance monitoring context manager for testing"""
    class PerformanceMonitor:
        def __init__(self):
            self.start_time = None
            self.end_time = None
            self.duration = None
            
        def __enter__(self):
            import time
            self.start_time = time.time()
            return self
            
        def __exit__(self, exc_type, exc_val, exc_tb):
            import time
            self.end_time = time.time()
            self.duration = self.end_time - self.start_time
            
        def assert_duration_under(self, max_seconds: float, operation: str = "operation"):
            assert self.duration is not None, "Monitor was not used as context manager"
            assert self.duration < max_seconds, \
                f"{operation} took {self.duration:.2f}s, should be under {max_seconds}s"
    
    return PerformanceMonitor


@pytest.fixture
def test_data_factory():
    """Factory for creating test data objects"""
    class TestDataFactory:
        @staticmethod
        def create_document(doc_type: str = "ada", custom_text: str = None) -> RawDoc:
            """Create test document of specified type"""
            if custom_text:
                text = custom_text
            elif doc_type == "ada":
                text = TestDocuments.ADA_ACCOMMODATION_REQUEST
            elif doc_type == "flsa":
                text = TestDocuments.FLSA_OVERTIME_SCENARIO
            elif doc_type == "workers_comp":
                text = TestDocuments.WORKERS_COMP_SCENARIO
            elif doc_type == "at_will":
                text = TestDocuments.AT_WILL_RETALIATION_SCENARIO
            else:
                text = "Sample legal document for testing"
                
            return RawDoc(
                id=f"test-{doc_type}-{hash(text) % 1000}",
                text=text,
                meta={'type': doc_type, 'test': True}
            )
        
        @staticmethod
        def create_context(jurisdiction: str = "US", **kwargs) -> Context:
            """Create test legal context"""
            return Context(jurisdiction=jurisdiction, **kwargs)
            
        @staticmethod
        def create_provenance(confidence: float = 0.9, **kwargs) -> Provenance:
            """Create test provenance"""
            from datetime import datetime
            defaults = {
                'source': [{"type": "test", "id": "test-source"}],
                'method': "test.method",
                'agent': "test.agent", 
                'time': datetime.utcnow(),
                'confidence': confidence
            }
            defaults.update(kwargs)
            return Provenance(**defaults)
    
    return TestDataFactory


# Test environment configuration
@pytest.fixture(scope="session", autouse=True)
def configure_test_environment():
    """Configure test environment settings"""
    # Set environment variables for testing
    os.environ['LEGAL_HYPERGRAPH_ENV'] = 'test'
    os.environ['LEGAL_HYPERGRAPH_LOG_LEVEL'] = 'WARNING'
    os.environ['LEGAL_HYPERGRAPH_DISABLE_TELEMETRY'] = 'true'
    
    # Mock external dependencies if needed
    with patch.dict(os.environ, {
        'HUGGINGFACE_HUB_DISABLE_PROGRESS_BARS': 'true',
        'TRANSFORMERS_VERBOSITY': 'error'
    }):
        yield


# Cleanup fixtures
@pytest.fixture(autouse=True)
def cleanup_after_test():
    """Cleanup after each test"""
    yield
    # Cleanup operations if needed
    # This runs after each test function


# Parametrized fixtures for comprehensive testing
@pytest.fixture(params=[
    TestDocuments.ADA_ACCOMMODATION_REQUEST,
    TestDocuments.FLSA_OVERTIME_SCENARIO,
    TestDocuments.WORKERS_COMP_SCENARIO,
    TestDocuments.AT_WILL_RETALIATION_SCENARIO
])
def employment_law_document(request):
    """Parametrized fixture for all employment law document types"""
    doc_text = request.param
    doc_type = None
    
    if doc_text == TestDocuments.ADA_ACCOMMODATION_REQUEST:
        doc_type = "ada"
    elif doc_text == TestDocuments.FLSA_OVERTIME_SCENARIO:
        doc_type = "flsa"
    elif doc_text == TestDocuments.WORKERS_COMP_SCENARIO:
        doc_type = "workers_comp"
    elif doc_text == TestDocuments.AT_WILL_RETALIATION_SCENARIO:
        doc_type = "at_will"
    
    return RawDoc(
        id=f"param-test-{doc_type}",
        text=doc_text,
        meta={'type': doc_type, 'parametrized': True}
    )


@pytest.fixture(params=["US", "US-CA", "US-NY", "US-TX"])
def us_jurisdiction_context(request):
    """Parametrized fixture for different US jurisdictions"""
    return Context(
        jurisdiction=request.param,
        law_type="statute",
        authority_level="state" if "-" in request.param else "federal"
    )


# Test skip conditions
def pytest_runtest_setup(item):
    """Setup function to skip tests based on conditions"""
    # Skip slow tests unless explicitly requested
    if "slow" in item.keywords and not item.config.getoption("--runslow", default=False):
        pytest.skip("need --runslow option to run slow tests")
    
    # Skip tests requiring specific plugins if not available
    if "requires_plugin" in item.keywords:
        required_plugin = item.get_closest_marker("requires_plugin").args[0]
        # Check if plugin is available
        # This would be implemented based on your plugin availability checking


def pytest_addoption(parser):
    """Add custom command line options"""
    parser.addoption(
        "--runslow", action="store_true", default=False,
        help="run slow tests"
    )
    parser.addoption(
        "--runintegration", action="store_true", default=False,
        help="run integration tests"
    )
    parser.addoption(
        "--rune2e", action="store_true", default=False,
        help="run end-to-end tests"
    )


# Test result collection
@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """Collect test results for reporting"""
    outcome = yield
    report = outcome.get_result()
    
    # Add custom attributes to test reports
    if report.when == "call":
        # Add test metadata
        report.legal_domain = getattr(item, 'legal_domain', None)
        report.test_type = 'e2e' if 'e2e' in str(item.fspath) else 'unit'