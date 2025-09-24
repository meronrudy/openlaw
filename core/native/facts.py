"""
Dense fact models for nodes and edges with deterministic ordering and dense id mapping.
Used by the native reasoning engine to ingest initial facts and to provide fast lookups.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional, Iterable, Any
import re

from .intervals import Interval, closed

_STMT_RE = re.compile(r"^\s*([A-Za-z0-9_]+)\s*\(\s*([^)]+)\s*\)\s*$")


def parse_statement(stmt: str) -> Tuple[str, List[str]]:
    """
    Parse a statement key like 'LABEL(node)' or 'LABEL(u,v)' into (label, [args]).
    Whitespace is ignored; args are returned as string ids without quotes.
    """
    m = _STMT_RE.match(str(stmt))
    if not m:
        raise ValueError(f"Invalid statement format: {stmt!r}")
    label = m.group(1)
    args = [a.strip() for a in m.group(2).split(",")]
    return label, args


def format_node_statement(label: str, node_id: str) -> str:
    return f"{str(label)}({str(node_id)})"


def format_edge_statement(label: str, u: str, v: str) -> str:
    return f"{str(label)}({str(u)},{str(v)})"


@dataclass
class NodeFacts:
    """
    Node facts stored as label -> node_id -> Interval.
    Deterministic ordering and dense indices are maintained for stable iteration.
    """
    facts_by_label: Dict[str, Dict[str, Interval]] = field(default_factory=dict)
    node_ids: List[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        # Normalize keys and sort for determinism
        norm: Dict[str, Dict[str, Interval]] = {}
        nid_set: set[str] = set(self.node_ids)
        for lbl, inner in (self.facts_by_label or {}).items():
            l2: Dict[str, Interval] = {}
            for nid, itv in (inner or {}).items():
                sn = str(nid)
                l2[sn] = itv
                nid_set.add(sn)
            norm[str(lbl)] = dict(sorted(l2.items(), key=lambda kv: kv[0]))
        self.facts_by_label = dict(sorted(norm.items(), key=lambda kv: kv[0]))
        self.node_ids = sorted(nid_set)

        # Dense mappings
        self.node_to_idx: Dict[str, int] = {nid: i for i, nid in enumerate(self.node_ids)}
        self.idx_to_node: List[str] = list(self.node_ids)

    def set(self, node_id: str, label: str, interval: Interval) -> None:
        self.facts_by_label.setdefault(str(label), {})[str(node_id)] = interval
        if str(node_id) not in self.node_to_idx:
            self.node_ids.append(str(node_id))
            self.node_ids.sort()
            self.node_to_idx = {nid: i for i, nid in enumerate(self.node_ids)}
            self.idx_to_node = list(self.node_ids)

    def get(self, node_id: str, label: str) -> Optional[Interval]:
        return self.facts_by_label.get(str(label), {}).get(str(node_id))

    def has(self, node_id: str, label: str) -> bool:
        return str(node_id) in self.facts_by_label.get(str(label), {})

    def nodes(self, label: str) -> List[str]:
        return list(self.facts_by_label.get(str(label), {}).keys())

    def labels(self, node_id: str) -> List[str]:
        out: List[str] = []
        nid = str(node_id)
        for lbl, inn in self.facts_by_label.items():
            if nid in inn:
                out.append(lbl)
        return out

    def all_nodes(self) -> List[str]:
        return list(self.node_ids)

    @staticmethod
    def from_node_map(label_node_map: Dict[str, Dict[str, Tuple[float, float]]]) -> "NodeFacts":
        """
        Build from a mapping: {label: {node_id: (l,u)}}.
        """
        fb: Dict[str, Dict[str, Interval]] = {}
        for lbl, inner in (label_node_map or {}).items():
            fb[str(lbl)] = {
                str(nid): closed(float(lu[0]), float(lu[1]))
                for nid, lu in (inner or {}).items()
            }
        return NodeFacts(fb, [])

    @staticmethod
    def from_statements(facts: Dict[str, Tuple[float, float]] | List[Tuple[str, Tuple[float, float]]]) -> "NodeFacts":
        """
        Build from statements like 'Label(node)' -> (l,u).
        Non-node-arity statements are ignored.
        """
        items = facts.items() if isinstance(facts, dict) else facts
        fb: Dict[str, Dict[str, Interval]] = {}
        for stmt, (l, u) in items:
            try:
                label, args = parse_statement(stmt)
            except Exception:
                continue
            if len(args) != 1:
                continue
            nid = args[0]
            fb.setdefault(label, {})[nid] = closed(float(l), float(u))
        return NodeFacts(fb, [])

    def to_statements(self) -> Dict[str, Tuple[float, float]]:
        out: Dict[str, Tuple[float, float]] = {}
        for lbl, inner in self.facts_by_label.items():
            for nid, iv in inner.items():
                out[format_node_statement(lbl, nid)] = (float(iv.lower), float(iv.upper))
        return out


@dataclass
class EdgeFacts:
    """
    Edge facts stored as label -> (u,v) -> Interval.
    Deterministic ordering and dense indices are maintained for stable iteration.
    """
    facts_by_label: Dict[str, Dict[Tuple[str, str], Interval]] = field(default_factory=dict)
    edge_keys: List[Tuple[str, str]] = field(default_factory=list)

    def __post_init__(self) -> None:
        # Normalize keys and sort for determinism
        norm: Dict[str, Dict[Tuple[str, str], Interval]] = {}
        ekey_set: set[Tuple[str, str]] = set(self.edge_keys)
        for lbl, inner in (self.facts_by_label or {}).items():
            l2: Dict[Tuple[str, str], Interval] = {}
            for key, itv in (inner or {}).items():
                u, v = (str(key[0]), str(key[1]))
                l2[(u, v)] = itv
                ekey_set.add((u, v))
            norm[str(lbl)] = dict(sorted(l2.items(), key=lambda kv: (kv[0][0], kv[0][1])))
        self.facts_by_label = dict(sorted(norm.items(), key=lambda kv: kv[0]))
        self.edge_keys = sorted(ekey_set)

        # Dense mappings
        self.edge_to_idx: Dict[Tuple[str, str], int] = {e: i for i, e in enumerate(self.edge_keys)}
        self.idx_to_edge: List[Tuple[str, str]] = list(self.edge_keys)

    def set(self, u: str, v: str, label: str, interval: Interval) -> None:
        self.facts_by_label.setdefault(str(label), {})[(str(u), str(v))] = interval
        k = (str(u), str(v))
        if k not in self.edge_to_idx:
            self.edge_keys.append(k)
            self.edge_keys.sort()
            self.edge_to_idx = {e: i for i, e in enumerate(self.edge_keys)}
            self.idx_to_edge = list(self.edge_keys)

    def get(self, u: str, v: str, label: str) -> Optional[Interval]:
        return self.facts_by_label.get(str(label), {}).get((str(u), str(v)))

    def has(self, u: str, v: str, label: str) -> bool:
        return (str(u), str(v)) in self.facts_by_label.get(str(label), {})

    def edges(self, label: str) -> List[Tuple[str, str]]:
        return list(self.facts_by_label.get(str(label), {}).keys())

    def labels(self, u: str, v: str) -> List[str]:
        out: List[str] = []
        key = (str(u), str(v))
        for lbl, inn in self.facts_by_label.items():
            if key in inn:
                out.append(lbl)
        return out

    def all_edges(self) -> List[Tuple[str, str]]:
        return list(self.edge_keys)

    @staticmethod
    def from_edge_map(label_edge_map: Dict[str, Dict[Tuple[str, str], Tuple[float, float]]]) -> "EdgeFacts":
        """
        Build from a mapping: {label: {(u,v): (l,u)}}.
        """
        fb: Dict[str, Dict[Tuple[str, str], Interval]] = {}
        for lbl, inner in (label_edge_map or {}).items():
            fb[str(lbl)] = {
                (str(u), str(v)): closed(float(lu[0]), float(lu[1]))
                for (u, v), lu in (inner or {}).items()
            }
        return EdgeFacts(fb, [])

    @staticmethod
    def from_statements(facts: Dict[str, Tuple[float, float]] | List[Tuple[str, Tuple[float, float]]]) -> "EdgeFacts":
        """
        Build from statements like 'Label(u,v)' -> (l,u).
        Non-edge-arity statements are ignored.
        """
        items = facts.items() if isinstance(facts, dict) else facts
        fb: Dict[str, Dict[Tuple[str, str], Interval]] = {}
        for stmt, (l, u) in items:
            try:
                label, args = parse_statement(stmt)
            except Exception:
                continue
            if len(args) != 2:
                continue
            u_id, v_id = args[0], args[1]
            fb.setdefault(label, {})[(u_id, v_id)] = closed(float(l), float(u))
        return EdgeFacts(fb, [])

    def to_statements(self) -> Dict[str, Tuple[float, float]]:
        out: Dict[str, Tuple[float, float]] = {}
        for lbl, inner in self.facts_by_label.items():
            for (u, v), iv in inner.items():
                out[format_edge_statement(lbl, u, v)] = (float(iv.lower), float(iv.upper))
        return out


@dataclass
class FactsIndex:
    """
    Combined facts index containing NodeFacts and EdgeFacts with convenience APIs.
    """
    nodes: NodeFacts = field(default_factory=NodeFacts)
    edges: EdgeFacts = field(default_factory=EdgeFacts)

    def get_node_fact(self, node_id: str, label: str) -> Optional[Interval]:
        return self.nodes.get(node_id, label)

    def get_edge_fact(self, u: str, v: str, label: str) -> Optional[Interval]:
        return self.edges.get(u, v, label)

    def set_node_fact(self, node_id: str, label: str, interval: Interval) -> None:
        self.nodes.set(node_id, label, interval)

    def set_edge_fact(self, u: str, v: str, label: str, interval: Interval) -> None:
        self.edges.set(u, v, label, interval)

    def to_statements(self) -> Dict[str, Tuple[float, float]]:
        out = {}
        out.update(self.nodes.to_statements())
        out.update(self.edges.to_statements())
        return out

    @staticmethod
    def from_statements(facts: Dict[str, Tuple[float, float]] | List[Tuple[str, Tuple[float, float]]]) -> "FactsIndex":
        """
        Build a combined index from mixed statements of both node and edge arity.
        """
        items = facts.items() if isinstance(facts, dict) else facts
        node_items: List[Tuple[str, Tuple[float, float]]] = []
        edge_items: List[Tuple[str, Tuple[float, float]]] = []
        for stmt, lu in items:
            try:
                _, args = parse_statement(stmt)
            except Exception:
                continue
            if len(args) == 1:
                node_items.append((stmt, lu))
            elif len(args) == 2:
                edge_items.append((stmt, lu))
            else:
                # ignore higher-arity for now
                pass
        return FactsIndex(NodeFacts.from_statements(node_items), EdgeFacts.from_statements(edge_items))


__all__ = [
    "NodeFacts",
    "EdgeFacts",
    "FactsIndex",
    "parse_statement",
    "format_node_statement",
    "format_edge_statement",
]