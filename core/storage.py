"""
Hypergraph Storage Engine with Provenance Tracking

SQLiteDict-based storage with efficient indexes for legal hypergraph operations.
Implements the storage layer for the provenance-first legal ontology system.
"""

from __future__ import annotations
from typing import List, Dict, Any, Optional, Set
from collections import defaultdict
import json
from sqlitedict import SqliteDict
from .model import Node, Hyperedge, Provenance


class GraphStore:
    """
    Optimized hypergraph storage with provenance enforcement and efficient querying.
    
    Uses SQLiteDict for persistent storage with custom indexes for fast lookups.
    All entities require provenance for explainable legal reasoning.
    """
    
    def __init__(self, path: str = ":memory:"):
        """
        Initialize the graph store with SQLite backend
        
        Args:
            path: SQLite database path, ":memory:" for in-memory storage
        """
        self.path = path
        
        # Core tables for nodes and edges
        self._nodes = SqliteDict(path, tablename="nodes", autocommit=True)
        self._edges = SqliteDict(path, tablename="edges", autocommit=True)
        
        # Indexes for efficient querying
        self._node_by_type = SqliteDict(path, tablename="node_type_idx", autocommit=True)
        self._edge_by_relation = SqliteDict(path, tablename="edge_rel_idx", autocommit=True)
        self._edge_by_tail = SqliteDict(path, tablename="edge_tail_idx", autocommit=True)
        self._edge_by_head = SqliteDict(path, tablename="edge_head_idx", autocommit=True)
        
        # Provenance indexes for explainability
        self._node_by_source = SqliteDict(path, tablename="node_source_idx", autocommit=True)
        
    def add_node(self, node: Node) -> None:
        """
        Add a node to the graph store with automatic indexing
        
        Args:
            node: Node with required provenance
        """
        # Store the node
        self._nodes[node.id] = node.model_dump()
        
        # Update type index
        if node.type not in self._node_by_type:
            self._node_by_type[node.type] = []
        type_list = self._node_by_type[node.type]
        if node.id not in type_list:
            type_list.append(node.id)
            self._node_by_type[node.type] = type_list
            
        # Update provenance indexes
        for source in node.prov.source:
            if "type" in source:
                source_type = source["type"]
                if source_type not in self._node_by_source:
                    self._node_by_source[source_type] = []
                source_list = self._node_by_source[source_type]
                if node.id not in source_list:
                    source_list.append(node.id)
                    self._node_by_source[source_type] = source_list
                    
    def get_node(self, node_id: str) -> Optional[Node]:
        """
        Retrieve a node by ID
        
        Args:
            node_id: Unique node identifier
            
        Returns:
            Node object or None if not found
        """
        if node_id not in self._nodes:
            return None
            
        node_data = self._nodes[node_id]
        return Node.model_validate(node_data)
        
    def add_edge(self, edge: Hyperedge) -> None:
        """
        Add a hyperedge to the graph store with automatic indexing
        
        Args:
            edge: Hyperedge with required provenance
        """
        # Store the edge
        self._edges[edge.id] = edge.model_dump()
        
        # Update relation index
        if edge.relation not in self._edge_by_relation:
            self._edge_by_relation[edge.relation] = []
        rel_list = self._edge_by_relation[edge.relation]
        if edge.id not in rel_list:
            rel_list.append(edge.id)
            self._edge_by_relation[edge.relation] = rel_list
            
        # Update tail indexes (outgoing edges)
        for tail_id in edge.tails:
            if tail_id not in self._edge_by_tail:
                self._edge_by_tail[tail_id] = []
            tail_list = self._edge_by_tail[tail_id]
            if edge.id not in tail_list:
                tail_list.append(edge.id)
                self._edge_by_tail[tail_id] = tail_list
                
        # Update head indexes (incoming edges)
        for head_id in edge.heads:
            if head_id not in self._edge_by_head:
                self._edge_by_head[head_id] = []
            head_list = self._edge_by_head[head_id]
            if edge.id not in head_list:
                head_list.append(edge.id)
                self._edge_by_head[head_id] = head_list
                
    def get_edge(self, edge_id: str) -> Optional[Hyperedge]:
        """
        Retrieve a hyperedge by ID
        
        Args:
            edge_id: Unique edge identifier
            
        Returns:
            Hyperedge object or None if not found
        """
        if edge_id not in self._edges:
            return None
            
        edge_data = self._edges[edge_id]
        return Hyperedge.model_validate(edge_data)
        
    def get_nodes_by_type(self, node_type: str) -> List[Node]:
        """
        Get all nodes of a specific type
        
        Args:
            node_type: Type of nodes to retrieve
            
        Returns:
            List of nodes of the specified type
        """
        if node_type not in self._node_by_type:
            return []
            
        node_ids = self._node_by_type[node_type]
        nodes = []
        for node_id in node_ids:
            node = self.get_node(node_id)
            if node:
                nodes.append(node)
        return nodes
        
    def get_edges_by_relation(self, relation: str) -> List[Hyperedge]:
        """
        Get all edges with a specific relation type
        
        Args:
            relation: Relation type to query
            
        Returns:
            List of edges with the specified relation
        """
        if relation not in self._edge_by_relation:
            return []
            
        edge_ids = self._edge_by_relation[relation]
        edges = []
        for edge_id in edge_ids:
            edge = self.get_edge(edge_id)
            if edge:
                edges.append(edge)
        return edges
        
    def get_incoming_edges(self, node_id: str) -> List[Hyperedge]:
        """
        Get all edges that have the given node as a head (incoming)
        
        Args:
            node_id: Node to find incoming edges for
            
        Returns:
            List of edges pointing to this node
        """
        if node_id not in self._edge_by_head:
            return []
            
        edge_ids = self._edge_by_head[node_id]
        edges = []
        for edge_id in edge_ids:
            edge = self.get_edge(edge_id)
            if edge:
                edges.append(edge)
        return edges
        
    def get_outgoing_edges(self, node_id: str) -> List[Hyperedge]:
        """
        Get all edges that have the given node as a tail (outgoing)
        
        Args:
            node_id: Node to find outgoing edges for
            
        Returns:
            List of edges originating from this node
        """
        if node_id not in self._edge_by_tail:
            return []
            
        edge_ids = self._edge_by_tail[node_id]
        edges = []
        for edge_id in edge_ids:
            edge = self.get_edge(edge_id)
            if edge:
                edges.append(edge)
        return edges
        
    def get_nodes_by_source_type(self, source_type: str) -> List[Node]:
        """
        Get all nodes that have a specific provenance source type
        
        Args:
            source_type: Type of provenance source to query
            
        Returns:
            List of nodes with the specified source type in their provenance
        """
        if source_type not in self._node_by_source:
            return []
            
        node_ids = self._node_by_source[source_type]
        nodes = []
        for node_id in node_ids:
            node = self.get_node(node_id)
            if node:
                nodes.append(node)
        return nodes