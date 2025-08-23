"""
Unit Tests: Core Data Models

Test-driven development for the core data models (Node, Hyperedge, Provenance).
Following TDD red-green-refactor cycle.
"""

import pytest
from datetime import datetime
from typing import List, Dict, Any

# This will fail initially - we'll implement these as we go
from core.model import Node, Hyperedge, Provenance, Context, mk_node, mk_edge


class TestProvenance:
    """Test the Provenance model - foundation of the system"""
    
    def test_provenance_creation_with_required_fields(self):
        """
        TDD: First test - Provenance must have required fields
        RED: This will fail because Provenance doesn't exist yet
        """
        # Given: Required provenance fields
        source = [{"type": "document", "id": "test-doc", "snippet": "test content"}]
        method = "test.extraction"
        agent = "test.user"
        time = datetime.utcnow()
        confidence = 0.9
        
        # When: Creating provenance
        prov = Provenance(
            source=source,
            method=method,
            agent=agent,
            time=time,
            confidence=confidence
        )
        
        # Then: Should have all required fields
        assert prov.source == source
        assert prov.method == method
        assert prov.agent == agent
        assert prov.time == time
        assert prov.confidence == confidence
    
    def test_provenance_validation_empty_source(self):
        """
        TDD: Provenance must validate that source is not empty
        """
        with pytest.raises(ValueError, match="Source cannot be empty"):
            Provenance(
                source=[],  # Empty source should fail
                method="test.method",
                agent="test.agent",
                time=datetime.utcnow(),
                confidence=0.9
            )
    
    def test_provenance_confidence_bounds(self):
        """
        TDD: Confidence must be between 0.0 and 1.0
        """
        # Test confidence too high
        with pytest.raises(ValueError, match="Confidence must be between 0.0 and 1.0"):
            Provenance(
                source=[{"type": "test"}],
                method="test.method",
                agent="test.agent", 
                time=datetime.utcnow(),
                confidence=1.5  # Invalid confidence
            )
        
        # Test confidence too low
        with pytest.raises(ValueError, match="Confidence must be between 0.0 and 1.0"):
            Provenance(
                source=[{"type": "test"}],
                method="test.method",
                agent="test.agent",
                time=datetime.utcnow(),
                confidence=-0.1  # Invalid confidence
            )


class TestNode:
    """Test the Node model"""
    
    def test_node_creation_with_provenance(self):
        """
        TDD: Node must have provenance
        """
        # Given: Valid provenance
        prov = Provenance(
            source=[{"type": "document", "id": "test"}],
            method="test.method",
            agent="test.agent",
            time=datetime.utcnow(),
            confidence=0.9
        )
        
        # When: Creating node
        node = Node(
            id="test-node-001",
            type="Employee",
            data={"name": "John Doe"},
            prov=prov
        )
        
        # Then: Should have correct properties
        assert node.id == "test-node-001"
        assert node.type == "Employee"
        assert node.data == {"name": "John Doe"}
        assert node.prov == prov
        assert node.labels == []  # Default empty
        assert node.context is None  # Default None
    
    def test_node_auto_id_generation(self):
        """
        TDD: Node should auto-generate ID if not provided
        """
        prov = Provenance(
            source=[{"type": "test"}],
            method="test.method",
            agent="test.agent",
            time=datetime.utcnow(),
            confidence=0.9
        )
        
        node = Node(
            type="Employee",
            data={},
            prov=prov
        )
        
        # Should have auto-generated ID starting with "node:"
        assert node.id.startswith("node:")
        assert len(node.id) > 5  # Should be more than just "node:"


class TestHyperedge:
    """Test the Hyperedge model"""
    
    def test_hyperedge_creation(self):
        """
        TDD: Hyperedge must connect multiple nodes
        """
        prov = Provenance(
            source=[{"type": "rule", "id": "test-rule"}],
            method="test.rule",
            agent="test.system",
            time=datetime.utcnow(),
            confidence=1.0
        )
        
        edge = Hyperedge(
            id="test-edge-001",
            relation="implies",
            tails=["node1", "node2"],  # Multiple premises
            heads=["node3"],           # Single conclusion
            prov=prov
        )
        
        assert edge.id == "test-edge-001"
        assert edge.relation == "implies"
        assert edge.tails == ["node1", "node2"]
        assert edge.heads == ["node3"]
        assert edge.prov == prov
    
    def test_hyperedge_requires_tails_and_heads(self):
        """
        TDD: Hyperedge must have at least one tail and one head
        """
        prov = Provenance(
            source=[{"type": "test"}],
            method="test.method",
            agent="test.agent",
            time=datetime.utcnow(),
            confidence=0.9
        )
        
        # Empty tails should fail
        with pytest.raises(ValueError, match="must have at least one tail"):
            Hyperedge(
                relation="implies",
                tails=[],
                heads=["node1"],
                prov=prov
            )
        
        # Empty heads should fail
        with pytest.raises(ValueError, match="must have at least one head"):
            Hyperedge(
                relation="implies",
                tails=["node1"],
                heads=[],
                prov=prov
            )


class TestContext:
    """Test the Context model"""
    
    def test_context_creation(self):
        """
        TDD: Context for legal jurisdiction and temporal scope
        """
        context = Context(
            jurisdiction="US",
            law_type="statute",
            authority_level="federal"
        )
        
        assert context.jurisdiction == "US"
        assert context.law_type == "statute"
        assert context.authority_level == "federal"
    
    def test_context_applicability_check(self):
        """
        TDD: Context should check if it applies within another context
        """
        federal_context = Context(jurisdiction="US", authority_level="federal")
        state_context = Context(jurisdiction="US-CA", authority_level="state")
        
        # Federal context should apply to state context
        assert federal_context.is_applicable_in(state_context)
        
        # State context should not apply to different state
        other_state = Context(jurisdiction="US-NY", authority_level="state")
        assert not state_context.is_applicable_in(other_state)


class TestHelperFunctions:
    """Test helper functions for creating nodes and edges"""
    
    def test_mk_node_helper(self):
        """
        TDD: mk_node helper should create valid nodes
        """
        prov = Provenance(
            source=[{"type": "test"}],
            method="test.method",
            agent="test.agent",
            time=datetime.utcnow(),
            confidence=0.9
        )
        
        node = mk_node(
            type="Employee",
            data={"name": "Jane"},
            prov=prov,
            labels=["qualified", "disabled"]
        )
        
        assert node.type == "Employee"
        assert node.data == {"name": "Jane"}
        assert node.labels == ["qualified", "disabled"]
        assert node.prov == prov
    
    def test_mk_edge_helper(self):
        """
        TDD: mk_edge helper should create valid hyperedges
        """
        prov = Provenance(
            source=[{"type": "test"}],
            method="test.method",
            agent="test.agent",
            time=datetime.utcnow(),
            confidence=0.9
        )
        
        edge = mk_edge(
            relation="employs",
            tails=["employer1"],
            heads=["employee1"],
            prov=prov
        )
        
        assert edge.relation == "employs"
        assert edge.tails == ["employer1"]
        assert edge.heads == ["employee1"]
        assert edge.prov == prov
    
    def test_mk_edge_validation(self):
        """
        TDD: mk_edge should validate inputs
        """
        prov = Provenance(
            source=[{"type": "test"}],
            method="test.method",
            agent="test.agent",
            time=datetime.utcnow(),
            confidence=0.9
        )
        
        # Should fail with empty tails
        with pytest.raises(ValueError):
            mk_edge(
                relation="test",
                tails=[],
                heads=["node1"],
                prov=prov
            )