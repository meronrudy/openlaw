"""
Dense label indices for nodes and edges with deterministic ordering and dense id mapping.
Provides fast membership and enumeration for native reasoning without PyReason.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, List, Tuple, Iterable, Optional, Set
import networkx as nx
from .graph import extract_specific_labels

@dataclass
class NodeLabelIndex:
    label_to_nodes: Dict[str, List[str]]
    node_ids: List[str]

    def __post_init__(self) -> None:
        # Normalize and sort for determinism
        self.node_ids = sorted(str(n) for n in self.node_ids)
        norm: Dict[str, List[str]] = {}
        for lbl, arr in (self.label_to_nodes or {}).items():
            norm[str(lbl)] = sorted(str(x) for x in (arr or []))
        self.label_to_nodes = norm
        # Dense mappings
        self.node_to_idx: Dict[str, int] = {nid: i for i, nid in enumerate(self.node_ids)}
        self.idx_to_node: List[str] = list(self.node_ids)
        # Set-based membership for O(1) has() checks
        self._label_to_node_set: Dict[str, Set[str]] = {lbl: set(arr) for lbl, arr in self.label_to_nodes.items()}

    @staticmethod
    def from_specific(node_labels: Dict[str, List[str]], node_ids: Optional[Iterable[str]] = None) -> "NodeLabelIndex":
        if node_ids is None:
            ns = set()
            for arr in node_labels.values():
                ns.update(str(x) for x in arr)
            node_ids = sorted(ns)
        return NodeLabelIndex(dict(node_labels), list(node_ids))

    @staticmethod
    def from_graph(graph: nx.DiGraph) -> "NodeLabelIndex":
        node_labels, _ = extract_specific_labels(graph)
        node_ids = [str(n) for n in graph.nodes]
        return NodeLabelIndex.from_specific(node_labels, node_ids)

    def has(self, node_id: str, label: str) -> bool:
        s = self._label_to_node_set.get(str(label))
        if s is None:
            return False
        return str(node_id) in s

    def nodes(self, label: str) -> List[str]:
        return list(self.label_to_nodes.get(str(label), []))

    def count(self, label: str) -> int:
        return len(self.label_to_nodes.get(str(label), []))

    def all_nodes(self) -> List[str]:
        return list(self.node_ids)

@dataclass
class EdgeLabelIndex:
    label_to_edges: Dict[str, List[Tuple[str, str]]]
    edge_keys: List[Tuple[str, str]]

    def __post_init__(self) -> None:
        # Normalize and sort for determinism
        norm: Dict[str, List[Tuple[str, str]]] = {}
        for lbl, pairs in (self.label_to_edges or {}).items():
            norm[str(lbl)] = sorted((str(u), str(v)) for (u, v) in (pairs or []))
        self.label_to_edges = norm
        self.edge_keys = sorted((str(u), str(v)) for (u, v) in self.edge_keys)
        # Dense mappings
        self.edge_to_idx: Dict[Tuple[str, str], int] = {e: i for i, e in enumerate(self.edge_keys)}
        self.idx_to_edge: List[Tuple[str, str]] = list(self.edge_keys)
        # Set-based membership for O(1) has() checks
        self._label_to_edge_set: Dict[str, Set[Tuple[str, str]]] = {lbl: set(pairs) for lbl, pairs in self.label_to_edges.items()}
        # Adjacency maps for fast neighbor expansion
        self._label_src_to_dst_map: Dict[str, Dict[str, List[str]]] = {}
        self._label_dst_to_src_map: Dict[str, Dict[str, List[str]]] = {}
        for lbl, pairs in self.label_to_edges.items():
            s2d: Dict[str, List[str]] = {}
            d2s: Dict[str, List[str]] = {}
            for (u, v) in pairs:
                s2d.setdefault(u, []).append(v)
                d2s.setdefault(v, []).append(u)
            # Ensure deterministic neighbor ordering
            for u in s2d:
                s2d[u].sort()
            for v in d2s:
                d2s[v].sort()
            self._label_src_to_dst_map[lbl] = s2d
            self._label_dst_to_src_map[lbl] = d2s

    @staticmethod
    def from_specific(edge_labels: Dict[str, List[Tuple[str, str]]], edges: Optional[Iterable[Tuple[str, str]]] = None) -> "EdgeLabelIndex":
        if edges is None:
            es: set[Tuple[str, str]] = set()
            for arr in edge_labels.values():
                for u, v in arr:
                    es.add((str(u), str(v)))
            edges = sorted(es)
        return EdgeLabelIndex(dict(edge_labels), list(edges))

    @staticmethod
    def from_graph(graph: nx.DiGraph) -> "EdgeLabelIndex":
        _, edge_labels = extract_specific_labels(graph)
        edges = [(str(u), str(v)) for u, v in graph.edges()]
        return EdgeLabelIndex.from_specific(edge_labels, edges)

    def has(self, u: str, v: str, label: str) -> bool:
        s = self._label_to_edge_set.get(str(label))
        if s is None:
            return False
        return (str(u), str(v)) in s

    def edges(self, label: str) -> List[Tuple[str, str]]:
        return list(self.label_to_edges.get(str(label), []))

    def count(self, label: str) -> int:
        return len(self.label_to_edges.get(str(label), []))

    def all_edges(self) -> List[Tuple[str, str]]:
        return list(self.edge_keys)

    def out_neighbors(self, label: str, u: str) -> List[str]:
        s2d = self._label_src_to_dst_map.get(str(label), {})
        return list(s2d.get(str(u), []))

    def in_neighbors(self, label: str, v: str) -> List[str]:
        d2s = self._label_dst_to_src_map.get(str(label), {})
        return list(d2s.get(str(v), []))

@dataclass
class LabelIndex:
    nodes: NodeLabelIndex
    edges: EdgeLabelIndex

    @staticmethod
    def from_graph(graph: nx.DiGraph) -> "LabelIndex":
        return LabelIndex(NodeLabelIndex.from_graph(graph), EdgeLabelIndex.from_graph(graph))

    @staticmethod
    def from_specific(
        node_labels: Dict[str, List[str]],
        edge_labels: Dict[str, List[Tuple[str, str]]],
        node_ids: Optional[Iterable[str]] = None,
        edges: Optional[Iterable[Tuple[str, str]]] = None,
    ) -> "LabelIndex":
        return LabelIndex(
            NodeLabelIndex.from_specific(node_labels, node_ids),
            EdgeLabelIndex.from_specific(edge_labels, edges),
        )

__all__ = ["LabelIndex", "NodeLabelIndex", "EdgeLabelIndex"]