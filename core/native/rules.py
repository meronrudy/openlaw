"""
Native Rule Model

Defines data structures for native rules, clauses, and thresholds that mirror
PyReason rule capabilities without depending on PyReason internals.

This model is used by the native compiler and engine to represent rules,
thresholds, clause bounds, and optional inference directives.
"""

from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import List, Tuple, Literal, Optional, Dict, Any


ClauseType = Literal["node", "edge", "comparison"]
Quantifier = Literal["greater_equal", "greater", "less_equal", "less", "equal"]
QuantifierMode = Literal["number", "percent"]
QuantifierBase = Literal["total", "available"]


Bound = Tuple[float, float]  # closed interval [l, u]
QuantifierType = Tuple[QuantifierMode, QuantifierBase]


@dataclass(frozen=True)
class ThresholdSpec:
    """
    Threshold specification for a single clause, compatible with PyReason semantics.

    Example: ThresholdSpec("greater_equal", ("number", "total"), 1.0)
    """
    quantifier: Quantifier
    quantifier_type: QuantifierType
    thresh: float

    def to_tuple(self) -> Tuple[str, Tuple[str, str], float]:
        return (self.quantifier, self.quantifier_type, float(self.thresh))


@dataclass
class Clause:
    """
    A single body clause of a rule.

    Attributes:
      ctype: 'node', 'edge', or 'comparison'
      label: predicate label name (e.g., 'cites', 'same_issue')
      variables: list of variable names (['x'] for node, ['x','y'] for edge)
      bound: closed probability interval for satisfaction (l, u)
      operator: comparison operator (for 'comparison' ctype), else ''
    """
    ctype: ClauseType
    label: str
    variables: List[str]
    bound: Bound
    operator: str = ""


@dataclass
class NativeRule:
    """
    Native rule representation.

    Attributes:
      id: unique rule identifier / name
      rule_type: 'node' or 'edge' (determined by head arity)
      target_label: label for the rule head (e.g., 'support_for_breach_of_contract')
      head_variables: variables appearing in the head (['x'] or ['x','y'])
      delta: integer time offset (delta_t)
      clauses: list of Clause objects forming the body
      thresholds: list of ThresholdSpec, one per clause (default: number/total >= 1.0)
      head_bound: optional fixed head bound [l,u] when no annotation function is used
      ann_fn: name of annotation function to apply at head ('' if fixed head bound)
      weights: list of per-clause weights for the annotation function (aligned with clauses)
      infer_edges: whether to add edges between head variables (only for edge rules)
      infer_edge_label: optional label for inferred edges ('' means unlabeled)
      set_static: if True, resulting head atom is marked static (bounds no longer change)
      qualifiers: optional metadata (authority, text, priority, etc.)
    """
    id: str
    rule_type: Literal["node", "edge"]
    target_label: str
    head_variables: List[str]
    delta: int = 0
    clauses: List[Clause] = field(default_factory=list)
    thresholds: List[ThresholdSpec] = field(default_factory=list)
    head_bound: Optional[Bound] = None  # used when ann_fn == ''
    ann_fn: str = ""  # used when head_bound is None
    weights: List[float] = field(default_factory=list)
    infer_edges: bool = False
    infer_edge_label: str = ""
    set_static: bool = False
    qualifiers: Dict[str, Any] = field(default_factory=dict)

    def validate(self) -> None:
        """
        Basic validation for rule consistency.
        """
        if self.rule_type not in ("node", "edge"):
            raise ValueError(f"rule_type must be 'node' or 'edge', got {self.rule_type}")
        if self.rule_type == "node" and len(self.head_variables) != 1:
            raise ValueError("node rule must have exactly one head variable")
        if self.rule_type == "edge" and len(self.head_variables) != 2:
            raise ValueError("edge rule must have exactly two head variables")
        if self.ann_fn and self.head_bound is not None:
            raise ValueError("ann_fn and head_bound are mutually exclusive")
        if not self.ann_fn and self.head_bound is None:
            # Default to [1,1] if no annotation provided and no bound provided
            self.head_bound = (1.0, 1.0)  # type: ignore[assignment]
        if len(self.thresholds) not in (0, len(self.clauses)):
            raise ValueError("thresholds length must be 0 or equal to number of clauses")
        if self.ann_fn and self.weights and len(self.weights) != len(self.clauses):
            raise ValueError("weights length must match number of clauses")

    def to_dict(self) -> Dict[str, Any]:
        """
        Serialize rule to a plain dict for logging/testing.
        """
        return {
            "id": self.id,
            "rule_type": self.rule_type,
            "target_label": self.target_label,
            "head_variables": list(self.head_variables),
            "delta": int(self.delta),
            "clauses": [asdict(c) for c in self.clauses],
            "thresholds": [t.to_tuple() for t in self.thresholds],
            "head_bound": tuple(self.head_bound) if self.head_bound is not None else None,
            "ann_fn": self.ann_fn,
            "weights": list(self.weights),
            "infer_edges": bool(self.infer_edges),
            "infer_edge_label": str(self.infer_edge_label or ""),
            "set_static": bool(self.set_static),
            "qualifiers": dict(self.qualifiers or {}),
        }


# Defaults ---------------------------------------------------------------------

DEFAULT_THRESHOLD: ThresholdSpec = ThresholdSpec(
    "greater_equal", ("number", "total"), 1.0
)


def default_thresholds_for(clauses: List[Clause]) -> List[ThresholdSpec]:
    """
    Produce default thresholds (number/total >= 1.0) for each clause.
    """
    return [DEFAULT_THRESHOLD for _ in clauses]