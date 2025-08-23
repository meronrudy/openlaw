"""
TDD Tests for Hypergraph Storage Engine

Following Test-Driven Development methodology:
1. RED: Write failing tests first
2. GREEN: Implement minimal code to pass
3. REFACTOR: Clean up and optimize

Tests cover SQLiteDict-based storage with indexes and provenance tracking.
"""

import pytest
import tempfile
import os
from datetime import datetime
from core.model import Node, Hyperedge, Provenance, Context, mk_node, mk_edge
from core.storage import GraphStore


class TestGraphStore:
    """Test the core hypergraph storage engine"""
    
    def test_graphstore_initialization(self):
        """
        TDD: GraphStore should initialize with in-memory SQLite
        """
        store = GraphStore()
        assert store is not None
        assert store.path == ":memory:"
        
    def test_graphstore_file_initialization(self):
        """
        TDD: GraphStore should support file-based storage
        """
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            store = GraphStore(tmp.name)
            assert store.path == tmp.name
        os.unlink(tmp.name)
        
    def test_add_node_to_store(self):
        """
        TDD: Should be able to add nodes to the store
        """
        store = GraphStore()
        prov = Provenance(
            source=[{"type": "test"}],
            method="test.method",
            agent="test.agent",
            time=datetime.utcnow(),
            confidence=0.9
        )
        
        node = mk_node("Person", {"name": "John"}, prov)
        store.add_node(node)
        
        # Should be able to retrieve it
        retrieved = store.get_node(node.id)
        assert retrieved is not None
        assert retrieved.id == node.id
        assert retrieved.type == "Person"
        assert retrieved.data["name"] == "John"
        
    def test_add_edge_to_store(self):
        """
        TDD: Should be able to add hyperedges to the store
        """
        store = GraphStore()
        prov = Provenance(
            source=[{"type": "test"}],
            method="test.method",
            agent="test.agent",
            time=datetime.utcnow(),
            confidence=0.9
        )
        
        # Create nodes first
        node1 = mk_node("Person", {"name": "Alice"}, prov)
        node2 = mk_node("Obligation", {"type": "employment"}, prov)
        store.add_node(node1)
        store.add_node(node2)
        
        # Create edge
        edge = mk_edge("has", [node1.id], [node2.id], prov)
        store.add_edge(edge)
        
        # Should be able to retrieve it
        retrieved = store.get_edge(edge.id)
        assert retrieved is not None
        assert retrieved.id == edge.id
        assert retrieved.relation == "has"
        assert retrieved.tails == [node1.id]
        assert retrieved.heads == [node2.id]
        
    def test_query_nodes_by_type(self):
        """
        TDD: Should be able to query nodes by type
        """
        store = GraphStore()
        prov = Provenance(
            source=[{"type": "test"}],
            method="test.method",
            agent="test.agent",
            time=datetime.utcnow(),
            confidence=0.9
        )
        
        # Add nodes of different types
        person1 = mk_node("Person", {"name": "Alice"}, prov)
        person2 = mk_node("Person", {"name": "Bob"}, prov)
        obligation = mk_node("Obligation", {"type": "employment"}, prov)
        
        store.add_node(person1)
        store.add_node(person2)
        store.add_node(obligation)
        
        # Query by type
        people = store.get_nodes_by_type("Person")
        assert len(people) == 2
        person_ids = {p.id for p in people}
        assert person1.id in person_ids
        assert person2.id in person_ids
        
        obligations = store.get_nodes_by_type("Obligation")
        assert len(obligations) == 1
        assert obligations[0].id == obligation.id
        
    def test_query_edges_by_relation(self):
        """
        TDD: Should be able to query edges by relation type
        """
        store = GraphStore()
        prov = Provenance(
            source=[{"type": "test"}],
            method="test.method",
            agent="test.agent",
            time=datetime.utcnow(),
            confidence=0.9
        )
        
        # Create nodes
        node1 = mk_node("Person", {"name": "Alice"}, prov)
        node2 = mk_node("Person", {"name": "Bob"}, prov)
        node3 = mk_node("Obligation", {"type": "employment"}, prov)
        
        store.add_node(node1)
        store.add_node(node2)
        store.add_node(node3)
        
        # Create edges with different relations
        edge1 = mk_edge("knows", [node1.id], [node2.id], prov)
        edge2 = mk_edge("has", [node1.id], [node3.id], prov)
        edge3 = mk_edge("has", [node2.id], [node3.id], prov)
        
        store.add_edge(edge1)
        store.add_edge(edge2)
        store.add_edge(edge3)
        
        # Query by relation
        knows_edges = store.get_edges_by_relation("knows")
        assert len(knows_edges) == 1
        assert knows_edges[0].id == edge1.id
        
        has_edges = store.get_edges_by_relation("has")
        assert len(has_edges) == 2
        has_edge_ids = {e.id for e in has_edges}
        assert edge2.id in has_edge_ids
        assert edge3.id in has_edge_ids
        
    def test_incoming_edges(self):
        """
        TDD: Should be able to find incoming edges to a node
        """
        store = GraphStore()
        prov = Provenance(
            source=[{"type": "test"}],
            method="test.method",
            agent="test.agent",
            time=datetime.utcnow(),
            confidence=0.9
        )
        
        # Create nodes
        node1 = mk_node("Person", {"name": "Alice"}, prov)
        node2 = mk_node("Person", {"name": "Bob"}, prov)
        node3 = mk_node("Obligation", {"type": "employment"}, prov)
        
        store.add_node(node1)
        store.add_node(node2)
        store.add_node(node3)
        
        # Create edges pointing TO node3
        edge1 = mk_edge("has", [node1.id], [node3.id], prov)
        edge2 = mk_edge("has", [node2.id], [node3.id], prov)
        edge3 = mk_edge("knows", [node1.id], [node2.id], prov)  # Doesn't point to node3
        
        store.add_edge(edge1)
        store.add_edge(edge2)
        store.add_edge(edge3)
        
        # Get incoming edges to node3
        incoming = store.get_incoming_edges(node3.id)
        assert len(incoming) == 2
        incoming_ids = {e.id for e in incoming}
        assert edge1.id in incoming_ids
        assert edge2.id in incoming_ids
        assert edge3.id not in incoming_ids
        
    def test_outgoing_edges(self):
        """
        TDD: Should be able to find outgoing edges from a node
        """
        store = GraphStore()
        prov = Provenance(
            source=[{"type": "test"}],
            method="test.method",
            agent="test.agent",
            time=datetime.utcnow(),
            confidence=0.9
        )
        
        # Create nodes
        node1 = mk_node("Person", {"name": "Alice"}, prov)
        node2 = mk_node("Person", {"name": "Bob"}, prov)
        node3 = mk_node("Obligation", {"type": "employment"}, prov)
        
        store.add_node(node1)
        store.add_node(node2)
        store.add_node(node3)
        
        # Create edges FROM node1
        edge1 = mk_edge("knows", [node1.id], [node2.id], prov)
        edge2 = mk_edge("has", [node1.id], [node3.id], prov)
        edge3 = mk_edge("has", [node2.id], [node3.id], prov)  # Doesn't come from node1
        
        store.add_edge(edge1)
        store.add_edge(edge2)
        store.add_edge(edge3)
        
        # Get outgoing edges from node1
        outgoing = store.get_outgoing_edges(node1.id)
        assert len(outgoing) == 2
        outgoing_ids = {e.id for e in outgoing}
        assert edge1.id in outgoing_ids
        assert edge2.id in outgoing_ids
        assert edge3.id not in outgoing_ids
        
    def test_provenance_tracking(self):
        """
        TDD: Should track provenance for all stored entities
        """
        store = GraphStore()
        prov1 = Provenance(
            source=[{"type": "statute", "cite": "42 USC 1981"}],
            method="manual.entry",
            agent="legal.expert",
            time=datetime.utcnow(),
            confidence=1.0
        )
        prov2 = Provenance(
            source=[{"type": "case", "cite": "Brown v. Board"}],
            method="nlp.extraction",
            agent="legal.nlp.v1",
            time=datetime.utcnow(),
            confidence=0.85
        )
        
        # Add nodes with different provenance
        node1 = mk_node("Rule", {"text": "Civil rights law"}, prov1)
        node2 = mk_node("Case", {"holding": "Separate is not equal"}, prov2)
        
        store.add_node(node1)
        store.add_node(node2)
        
        # Should be able to query by provenance source
        statute_nodes = store.get_nodes_by_source_type("statute")
        assert len(statute_nodes) == 1
        assert statute_nodes[0].id == node1.id
        
        case_nodes = store.get_nodes_by_source_type("case")
        assert len(case_nodes) == 1
        assert case_nodes[0].id == node2.id
        
    def test_store_persistence(self):
        """
        TDD: File-based storage should persist across sessions
        """
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            # Create store and add data
            store1 = GraphStore(tmp.name)
            prov = Provenance(
                source=[{"type": "test"}],
                method="test.method",
                agent="test.agent",
                time=datetime.utcnow(),
                confidence=0.9
            )
            
            node = mk_node("Person", {"name": "Persistent"}, prov)
            store1.add_node(node)
            
            # Close and reopen
            del store1
            store2 = GraphStore(tmp.name)
            
            # Data should still be there
            retrieved = store2.get_node(node.id)
            assert retrieved is not None
            assert retrieved.data["name"] == "Persistent"
            
        os.unlink(tmp.name)