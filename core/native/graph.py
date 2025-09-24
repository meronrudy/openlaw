"""
Native Graph Ingestion Utilities

This module provides GraphML loading and helpers to work with NetworkX graphs
without relying on PyReason. It is intended to be used by the native engine and
tooling during the migration away from PyReason.

Capabilities:
- Load GraphML into a directed NetworkX graph, with optional edge reversal.
- Load an existing NetworkX graph and normalize to DiGraph.
- Extract simple "specific label" indices from node/edge attributes for fast lookup.

Notes:
- This module does NOT mutate or depend on core.storage.GraphStore. The native
  engine can choose to ingest into GraphStore or operate on NetworkX directly.
- Label extraction is heuristic: any node/edge attribute with a truthy value
  (True, "true", "1", non-empty string) is treated as a label present on that
  node/edge. Downstream code can refine this mapping or provide explicit label
  sets as needed.
"""

from __future__ import annotations
from typing import Any, Dict, List, Tuple
import networkx as nx


def load_graphml(graphml_path: str, reverse: bool = False) -> nx.DiGraph:
    """
    Load a GraphML file into a directed graph.

    Args:
        graphml_path: Path to GraphML file
        reverse: If True, reverse edge direction

    Returns:
        Directed graph (nx.DiGraph)
    """
    g = nx.read_graphml(graphml_path)
    if not isinstance(g, (nx.DiGraph, nx.MultiDiGraph)):
        g = g.to_directed()  # ensure directed
    if reverse:
        g = g.reverse(copy=True)
    # Normalize to DiGraph (merge parallel edges if MultiDiGraph)
    if isinstance(g, nx.MultiDiGraph):
        dg = nx.DiGraph()
        dg.add_nodes_from(g.nodes(data=True))
        # Collapse parallel edges, merging attributes (last-wins semantics)
        for u, v, data in g.edges(data=True):
            if dg.has_edge(u, v):
                # Update existing attributes; MultiDiGraph may keep multiple sets
                dg[u][v].update(data or {})
            else:
                dg.add_edge(u, v, **(data or {}))
        g = dg
    return g


def load_graph(graph: nx.Graph, reverse: bool = False) -> nx.DiGraph:
    """
    Load a pre-constructed NetworkX graph and normalize to a DiGraph.

    Args:
        graph: NetworkX graph (directed or undirected)
        reverse: If True, reverse edge direction

    Returns:
        Directed graph (nx.DiGraph)
    """
    g = graph
    if not isinstance(g, (nx.DiGraph, nx.MultiDiGraph)):
        g = g.to_directed()
    if reverse:
        g = g.reverse(copy=True)
    if isinstance(g, nx.MultiDiGraph):
        dg = nx.DiGraph()
        dg.add_nodes_from(g.nodes(data=True))
        for u, v, data in g.edges(data=True):
            if dg.has_edge(u, v):
                dg[u][v].update(data or {})
            else:
                dg.add_edge(u, v, **(data or {}))
        g = dg
    return g


def _is_truthy(val: Any) -> bool:
    if val is True:
        return True
    if isinstance(val, (int, float)) and val != 0:
        return True
    if isinstance(val, str):
        s = val.strip().lower()
        if s in ("true", "yes", "y", "1"):
            return True
        # Non-empty strings can be treated as present labels in some graphs
        if len(s) > 0 and s not in ("false", "no", "n", "0", "none", "null"):
            return True
    return False


def extract_specific_labels(
    graph: nx.DiGraph,
) -> Tuple[Dict[str, List[str]], Dict[str, List[Tuple[str, str]]]]:
    """
    Build "specific label" indices similar to PyReason's specific_node_labels and
    specific_edge_labels, but without specialized types.

    Heuristic:
      - For nodes: each attribute key whose value is truthy marks the node as
        belonging to that label.
      - For edges: same for edge attributes.

    Returns:
        (specific_node_labels, specific_edge_labels)
        where:
          specific_node_labels: {label: [node_id, ...]}
          specific_edge_labels: {label: [(u, v), ...]}
    """
    node_labels: Dict[str, List[str]] = {}
    edge_labels: Dict[str, List[Tuple[str, str]]] = {}

    # Node attributes
    for n, attrs in graph.nodes(data=True):
        for key, val in (attrs or {}).items():
            if _is_truthy(val):
                node_labels.setdefault(str(key), []).append(str(n))

    # Edge attributes
    for u, v, attrs in graph.edges(data=True):
        for key, val in (attrs or {}).items():
            if _is_truthy(val):
                edge_labels.setdefault(str(key), []).append((str(u), str(v)))

    return node_labels, edge_labels