"""
Variable grounding and join strategies for native rules.

This module provides:
- ground_rule(rule, label_index): produce consistent variable assignments that satisfy
  the structural constraints of rule clauses (node/edge) via index-aware joins.
- eval_clause_on_assignment(clause, assignment, label_index): check clause satisfaction
  for a given assignment and return a probability interval for annotation.

Notes:
- Comparison clauses are currently treated as non-blocking placeholders and return
  [0,1] intervals. Extend as needed for numeric/text comparisons.
- Threshold evaluation is performed in the engine using satisfied counts across
  assignments and evaluate_threshold from thresholds.py.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, List, Tuple, Iterable

from .intervals import Interval, closed
from .rules import Clause
from .labels import LabelIndex


Assignment = Dict[str, str]


def _bound_satisfied(itv: Interval, bound: Tuple[float, float]) -> bool:
    l, u = float(bound[0]), float(bound[1])
    return (l <= itv.lower) and (u >= itv.upper)


def _node_presence_interval(present: bool) -> Interval:
    return closed(1.0, 1.0) if present else closed(0.0, 0.0)


def _eval_node_clause(
    clause: Clause,
    asg: Assignment,
    labels: LabelIndex,
) -> Tuple[bool, Interval]:
    """
    Evaluate a node clause 'label(v)' against an assignment mapping v -> node_id.
    Returns (satisfied, interval).
    """
    if not clause.variables:
        # No variable specified; cannot evaluate meaningfully
        return False, closed(0.0, 0.0)
    v = clause.variables[0]
    if v not in asg:
        # Variable not bound; cannot evaluate
        return False, closed(0.0, 0.0)
    nid = asg[v]
    itv = _node_presence_interval(labels.nodes.has(nid, clause.label))
    return _bound_satisfied(itv, clause.bound), itv


def _eval_edge_clause(
    clause: Clause,
    asg: Assignment,
    labels: LabelIndex,
) -> Tuple[bool, Interval]:
    """
    Evaluate an edge clause 'label(u,v)' against an assignment mapping u/v -> node_id.
    Returns (satisfied, interval).
    """
    if len(clause.variables) < 2:
        return False, closed(0.0, 0.0)
    uvar, vvar = clause.variables[0], clause.variables[1]
    if uvar not in asg or vvar not in asg:
        return False, closed(0.0, 0.0)
    u, v = asg[uvar], asg[vvar]
    itv = _node_presence_interval(labels.edges.has(u, v, clause.label))
    return _bound_satisfied(itv, clause.bound), itv


def eval_clause_on_assignment(
    clause: Clause,
    asg: Assignment,
    labels: LabelIndex,
) -> Tuple[bool, Interval]:
    """
    Evaluate a single clause under a given assignment.
    """
    if clause.ctype == "node":
        return _eval_node_clause(clause, asg, labels)
    elif clause.ctype == "edge":
        return _eval_edge_clause(clause, asg, labels)
    else:
        # comparison clause placeholder (extend as needed)
        return True, closed(0.0, 1.0)


def _extend_with_node(
    assignments: List[Assignment],
    var: str,
    label: str,
    labels: LabelIndex,
) -> List[Assignment]:
    """
    Join assignments with node candidates for var based on presence of label(var).
    - If var already bound, filter by presence.
    - Else, produce new assignments for each candidate node.
    """
    out: List[Assignment] = []
    if var in assignments[0] if assignments else False:
        # Filter path
        for asg in assignments:
            nid = asg[var]
            if labels.nodes.has(nid, label):
                out.append(asg)
        return out

    # Extend path
    candidates = labels.nodes.nodes(label)
    for asg in assignments:
        for nid in candidates:
            new_asg = dict(asg)
            new_asg[var] = nid
            out.append(new_asg)
    return out


def _extend_with_edge(
    assignments: List[Assignment],
    uvar: str,
    vvar: str,
    label: str,
    labels: LabelIndex,
) -> List[Assignment]:
    """
    Join assignments with edge candidates for (uvar,vvar) based on presence of label(u,v).
    - If both bound, filter by presence.
    - If one bound, extend the other by neighbors under the label (uses adjacency maps).
    - If neither bound, expand by all labeled edges.
    """
    out: List[Assignment] = []
    labeled_edges = labels.edges.edges(label)
    if not assignments:
        # Seed from edges
        for (u, v) in labeled_edges:
            out.append({uvar: u, vvar: v})
        return out

    for asg in assignments:
        u_bound = uvar in asg
        v_bound = vvar in asg
        if u_bound and v_bound:
            u, v = asg[uvar], asg[vvar]
            if labels.edges.has(u, v, label):
                out.append(asg)
            continue

        if u_bound and not v_bound:
            u = asg[uvar]
            for vv in labels.edges.out_neighbors(label, u):
                new_asg = dict(asg)
                new_asg[vvar] = vv
                out.append(new_asg)
            continue

        if v_bound and not u_bound:
            v = asg[vvar]
            for uu in labels.edges.in_neighbors(label, v):
                new_asg = dict(asg)
                new_asg[uvar] = uu
                out.append(new_asg)
            continue

        # Neither bound
        for (uu, vv) in labeled_edges:
            new_asg = dict(asg)
            new_asg[uvar] = uu
            new_asg[vvar] = vv
            out.append(new_asg)

    return out


def ground_rule(rule, labels: LabelIndex) -> List[Assignment]:
    """
    Produce consistent variable assignments that satisfy the structural part of the rule
    (node/edge label membership joins). Bound checks are performed later on the produced
    assignments during evaluation.

    Strategy:
      - Initialize with a single empty assignment.
      - For each clause in order, join/extend the assignment set according to clause type.
      - Deterministically preserve ordering by sorting lexicographically at the end.
    """
    assignments: List[Assignment] = [dict()]

    # Join-order optimization: process more selective clauses first to reduce intermediate assignment explosion.
    indexed_clauses = list(enumerate(rule.clauses))

    def _cardinality(ic):
        _, cl = ic
        if cl.ctype == "node":
            return labels.nodes.count(cl.label)
        elif cl.ctype == "edge":
            return labels.edges.count(cl.label)
        else:
            # comparison clauses do not bind variables; push to end
            return 10**9

    for idx, cl in sorted(indexed_clauses, key=lambda ic: (_cardinality(ic), ic[0])):
        if cl.ctype == "node":
            var = cl.variables[0] if cl.variables else None
            if not var:
                # No variable to bind; skip
                continue
            assignments = _extend_with_node(assignments, var, cl.label, labels)
        elif cl.ctype == "edge":
            if len(cl.variables) < 2:
                # Malformed clause; skip
                continue
            uvar, vvar = cl.variables[0], cl.variables[1]
            assignments = _extend_with_edge(assignments, uvar, vvar, cl.label, labels)
        else:
            # comparison clause does not bind variables here
            continue

        if not assignments:
            # Early exit if no consistent assignment remains
            return []

    # Deterministic sort of assignments by variable tuple
    def _asg_key(a: Assignment):
        # Sort by variable name then value to ensure stable order
        return tuple(sorted(a.items(), key=lambda kv: (kv[0], kv[1])))

    assignments.sort(key=_asg_key)
    return assignments