"""
Native Threshold Semantics
- Replicates PyReason threshold behavior for clause satisfaction
- Supports ('number'|'percent', 'total'|'available') quantifier types
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Literal, Tuple


Quantifier = Literal["greater_equal", "greater", "less_equal", "less", "equal"]
QuantifierMode = Literal["number", "percent"]
QuantifierBase = Literal["total", "available"]


@dataclass(frozen=True)
class Threshold:
    """
    Clause threshold compatible with PyReason semantics.

    Attributes:
        quantifier: comparison operator
        quantifier_type: (mode, base) where mode in {'number','percent'}, base in {'total','available'}
        thresh: numeric threshold value

    Methods:
        to_tuple(): stable tuple form for serialization
    """
    quantifier: Quantifier
    quantifier_type: Tuple[QuantifierMode, QuantifierBase]
    thresh: float

    def __post_init__(self) -> None:
        if self.quantifier not in ("greater_equal", "greater", "less_equal", "less", "equal"):
            raise ValueError("Invalid quantifier")
        m, b = self.quantifier_type
        if m not in ("number", "percent") or b not in ("total", "available"):
            raise ValueError("Invalid quantifier type")

    def to_tuple(self) -> Tuple[str, Tuple[str, str], float]:
        return (self.quantifier, self.quantifier_type, self.thresh)


def evaluate_threshold(
    threshold: Threshold,
    satisfied_count: int,
    total_count: int,
    available_count: int | None = None,
) -> bool:
    """
    Evaluate whether a clause passes its threshold.

    Args:
        threshold: Threshold definition
        satisfied_count: number of satisfied atoms in the clause
        total_count: total number of atoms in the clause
        available_count: size of the 'available' set for percent/number over available (defaults to total_count)

    PyReason parity rules:
      - 'percent' compares against 100 * (satisfied / base)
      - 'number' compares satisfied vs numeric thresh
      - base is total or available; available defaults to total_count when not provided
      - Empty bases are treated as zero to avoid division by zero
    """
    m, b = threshold.quantifier_type
    base = (available_count if (available_count is not None) else total_count) if b == "available" else total_count
    base = max(int(base), 0)
    sat = max(int(satisfied_count), 0)

    if m == "percent":
        # Convert satisfied/base into a percentage in [0, 100]
        pct = 0.0 if base == 0 else (100.0 * (float(sat) / float(base)))
        value = pct
        rhs = float(threshold.thresh)
    else:
        # 'number' mode compares counts directly
        value = float(sat)
        rhs = float(threshold.thresh)

    q = threshold.quantifier
    if q == "greater_equal":
        return value >= rhs
    if q == "greater":
        return value > rhs
    if q == "less_equal":
        return value <= rhs
    if q == "less":
        return value < rhs
    if q == "equal":
        return value == rhs

    # Defensive fallback (should not reach)
    return False