"""
Basic pytest configuration for TDD development

This is a simplified version that will be expanded as we implement more components.
"""

import pytest
from datetime import datetime
from typing import Dict, Any


@pytest.fixture
def sample_provenance_data():
    """Basic provenance data for testing"""
    return {
        "source": [{"type": "test", "id": "test-source"}],
        "method": "test.method",
        "agent": "test.agent",
        "time": datetime.utcnow(),
        "confidence": 0.9
    }


@pytest.fixture
def sample_node_data():
    """Basic node data for testing"""
    return {
        "type": "Employee",
        "data": {"name": "John Doe"},
        "labels": ["qualified"]
    }


@pytest.fixture
def sample_edge_data():
    """Basic edge data for testing"""
    return {
        "relation": "employs",
        "tails": ["employer1"],
        "heads": ["employee1"]
    }