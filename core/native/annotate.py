"""
Native Annotation Functions
- Replicates PyReason's probabilistic aggregation semantics
- Provides legal-specific burden and conservative aggregators

All functions accept:
  annotations: List[List[Interval]]  # clauses -> list of supporting intervals
  weights: List[float]               # per-clause weights aligned by index

Return:
  Interval (closed probability interval [l, u])
"""

from __future__ import annotations
from typing import List, Sequence, Tuple
import math

from core.native.intervals import Interval, closed


# Lightweight numba shim (optional JIT)
try:
    import numba  # type: ignore  # pylint: disable=import-error

    def njit_sig(fn):
        try:
            return numba.njit(fn)  # type: ignore
        except Exception:
            return fn
except Exception:  # pragma: no cover
    def njit_sig(fn):
        return fn


@njit_sig
def _check_bound(lower: float, upper: float) -> Tuple[float, float]:
    """
    PyReason compatibility:
      - if lower > upper, return [0, 1]
      - otherwise clamp both to [0, 1]
    """
    if lower > upper:
        return 0.0, 1.0
    # clamp to [0, 1]
    if lower < 0.0:
        lower = 0.0
    if upper < 0.0:
        upper = 0.0
    if lower > 1.0:
        lower = 1.0
    if upper > 1.0:
        upper = 1.0
    return lower, upper


@njit_sig
def _get_weighted_sum(
    annotations: Sequence[Sequence[Interval]],
    weights: Sequence[float],
    mode: str = "lower",
) -> Tuple[List[float], int]:
    """
    Returns (weighted_sum_per_clause, total_annotation_count)
    weighted_sum_per_clause holds per-clause sum over its member intervals using the provided weight
    """
    out: List[float] = []
    cnt = 0
    # Defensive: if no clauses, return zeros
    if annotations is None:
        return out, 0

    for i in range(len(annotations)):
        clause = annotations[i]
        w = float(weights[i]) if i < len(weights) else 1.0
        s = 0.0
        for j in range(len(clause)):
            ann = clause[j]
            cnt += 1
            if mode == "lower":
                s += float(ann.lower) * w
            else:
                s += float(ann.upper) * w
        out.append(s)
    return out, cnt


# -------------------------------
# Core aggregators (PyReason parity)
# -------------------------------

@njit_sig
def average(annotations: Sequence[Sequence[Interval]], weights: Sequence[float]) -> Interval:
    """
    Average lower bounds for L; average upper bounds for U.
    """
    weighted_sum_lower, n = _get_weighted_sum(annotations, weights, mode="lower")
    weighted_sum_upper, n2 = _get_weighted_sum(annotations, weights, mode="upper")
    # n cannot be zero otherwise rule would not have fired
    n_total = n if n > 0 else 1
    l = (sum(weighted_sum_lower) / n_total) if len(weighted_sum_lower) > 0 else 0.0
    u = (sum(weighted_sum_upper) / n_total) if len(weighted_sum_upper) > 0 else 1.0
    l, u = _check_bound(l, u)
    return closed(l, u)


@njit_sig
def average_lower(annotations: Sequence[Sequence[Interval]], weights: Sequence[float]) -> Interval:
    """
    Average lower bounds for L; take max of upper bounds across all intervals for U.
    """
    weighted_sum_lower, n = _get_weighted_sum(annotations, weights, mode="lower")
    n_total = n if n > 0 else 1
    l = (sum(weighted_sum_lower) / n_total) if len(weighted_sum_lower) > 0 else 0.0

    max_upper = 0.0
    for i in range(len(annotations)):
        clause = annotations[i]
        for j in range(len(clause)):
            ann = clause[j]
            if float(ann.upper) > max_upper:
                max_upper = float(ann.upper)

    l, u = _check_bound(l, max_upper)
    return closed(l, u)


@njit_sig
def maximum(annotations: Sequence[Sequence[Interval]], weights: Sequence[float]) -> Interval:
    """
    Take max of clause-weighted sums for lower and upper.
    """
    weighted_sum_lower, _ = _get_weighted_sum(annotations, weights, mode="lower")
    weighted_sum_upper, _ = _get_weighted_sum(annotations, weights, mode="upper")

    max_lower = max(weighted_sum_lower) if weighted_sum_lower else 0.0
    max_upper = max(weighted_sum_upper) if weighted_sum_upper else 1.0

    l, u = _check_bound(max_lower, max_upper)
    return closed(l, u)


@njit_sig
def minimum(annotations: Sequence[Sequence[Interval]], weights: Sequence[float]) -> Interval:
    """
    Take min of clause-weighted sums for lower and upper.
    """
    weighted_sum_lower, _ = _get_weighted_sum(annotations, weights, mode="lower")
    weighted_sum_upper, _ = _get_weighted_sum(annotations, weights, mode="upper")

    min_lower = min(weighted_sum_lower) if weighted_sum_lower else 0.0
    min_upper = min(weighted_sum_upper) if weighted_sum_upper else 1.0

    l, u = _check_bound(min_lower, min_upper)
    return closed(l, u)


# -------------------------------
# Legal-specific aggregators
# -------------------------------

@njit_sig
def _weighted_average_bounds(
    annotations: Sequence[Sequence[Interval]], weights: Sequence[float]
) -> Tuple[float, float]:
    weighted_sum_lower, n = _get_weighted_sum(annotations, weights, mode="lower")
    weighted_sum_upper, n2 = _get_weighted_sum(annotations, weights, mode="upper")

    n_total = n if n > 0 else 1
    avg_lower = (sum(weighted_sum_lower) / n_total) if len(weighted_sum_lower) > 0 else 0.0
    avg_upper = (sum(weighted_sum_upper) / n_total) if len(weighted_sum_upper) > 0 else 1.0
    return avg_lower, avg_upper


@njit_sig
def legal_burden_civil_051(annotations: Sequence[Sequence[Interval]], weights: Sequence[float]) -> Interval:
    """
    Civil burden of proof (preponderance): clamp lower bound to at least 0.51.
    Aggregation: weighted average of clause bounds, then clamp.
    """
    avg_lower, avg_upper = _weighted_average_bounds(annotations, weights)
    lower = avg_lower if avg_lower >= 0.51 else 0.51
    l, u = _check_bound(lower, avg_upper)
    return closed(l, u)


@njit_sig
def legal_burden_clear_075(annotations: Sequence[Sequence[Interval]], weights: Sequence[float]) -> Interval:
    """
    Clear and convincing: clamp lower bound to at least 0.75.
    """
    avg_lower, avg_upper = _weighted_average_bounds(annotations, weights)
    lower = avg_lower if avg_lower >= 0.75 else 0.75
    l, u = _check_bound(lower, avg_upper)
    return closed(l, u)


@njit_sig
def legal_burden_criminal_090(annotations: Sequence[Sequence[Interval]], weights: Sequence[float]) -> Interval:
    """
    Criminal burden (beyond a reasonable doubt): clamp lower bound to at least 0.90.
    """
    avg_lower, avg_upper = _weighted_average_bounds(annotations, weights)
    lower = avg_lower if avg_lower >= 0.90 else 0.90
    l, u = _check_bound(lower, avg_upper)
    return closed(l, u)


@njit_sig
def legal_conservative_min(annotations: Sequence[Sequence[Interval]], weights: Sequence[float]) -> Interval:
    """
    Conservative aggregator:
      - Lower = min of clause-weighted sums (conservative wrt conflicts)
      - Upper = average of clause-weighted sums
    """
    weighted_sum_lower, n = _get_weighted_sum(annotations, weights, mode="lower")
    weighted_sum_upper, n2 = _get_weighted_sum(annotations, weights, mode="upper")

    min_lower = min(weighted_sum_lower) if weighted_sum_lower else 0.0
    n_total = n if n > 0 else 1
    avg_upper = (sum(weighted_sum_upper) / n_total) if len(weighted_sum_upper) > 0 else 1.0

    l, u = _check_bound(min_lower, avg_upper)
    return closed(l, u)


@njit_sig
def precedent_weighted(annotations: Sequence[Sequence[Interval]], weights: Sequence[float]) -> Interval:
    """
    Precedent-weighted aggregator:
      - weights correspond to clause classes (e.g., controlling, persuasive, contrary)
      - computes weighted average of lower/upper bounds across all annotations
      - enforces PyReason-compatible bound checks and [0,1] clamp
    """
    weighted_sum_lower, n = _get_weighted_sum(annotations, weights, mode="lower")
    weighted_sum_upper, _ = _get_weighted_sum(annotations, weights, mode="upper")
    n_total = n if n > 0 else 1
    l = (sum(weighted_sum_lower) / n_total) if len(weighted_sum_lower) > 0 else 0.0
    u = (sum(weighted_sum_upper) / n_total) if len(weighted_sum_upper) > 0 else 1.0
    l, u = _check_bound(l, u)
    return closed(l, u)


# -------------------------------
# Statutory interpretation operators (legal-specific)
# -------------------------------

@njit_sig
def textualism_alpha(annotations: Sequence[Sequence[Interval]], weights: Sequence[float]) -> Interval:
    """
    Textualism-style bias: emphasize plain meaning by slightly tightening the upper bound.
    Neutral placeholder with mild effect to remain backward compatible.
    """
    avg_lower, avg_upper = _weighted_average_bounds(annotations, weights)
    span = avg_upper - avg_lower
    adj_upper = avg_lower + span * 0.95  # shrink upper bound by 5%
    l, u = _check_bound(avg_lower, adj_upper)
    return closed(l, u)


@njit_sig
def purposivism_alpha(annotations: Sequence[Sequence[Interval]], weights: Sequence[float]) -> Interval:
    """
    Purposivism-style bias: modestly allow broader purposive evidence by expanding the upper bound.
    Neutral placeholder with mild effect to remain backward compatible.
    """
    avg_lower, avg_upper = _weighted_average_bounds(annotations, weights)
    span = avg_upper - avg_lower
    adj_upper = avg_lower + span * 1.05  # expand upper bound by 5%, clamped later
    l, u = _check_bound(avg_lower, adj_upper)
    return closed(l, u)


@njit_sig
def lenity_alpha(annotations: Sequence[Sequence[Interval]], weights: Sequence[float]) -> Interval:
    """
    Rule-of-lenity-style bias: in penal ambiguity, lean toward defendant by slightly reducing lower bound.
    Neutral placeholder with mild effect to remain backward compatible.
    """
    avg_lower, avg_upper = _weighted_average_bounds(annotations, weights)
    adj_lower = avg_lower * 0.95  # reduce lower bound by 5%
    l, u = _check_bound(adj_lower, avg_upper)
    return closed(l, u)


# Optional registry for name-based lookup
ANNOTATION_REGISTRY = {
    "average": average,
    "average_lower": average_lower,
    "maximum": maximum,
    "minimum": minimum,
    "legal_burden_civil_051": legal_burden_civil_051,
    "legal_burden_clear_075": legal_burden_clear_075,
    "legal_burden_criminal_090": legal_burden_criminal_090,
    "legal_conservative_min": legal_conservative_min,
    "precedent_weighted": precedent_weighted,
    "textualism_alpha": textualism_alpha,
    "purposivism_alpha": purposivism_alpha,
    "lenity_alpha": lenity_alpha,
}