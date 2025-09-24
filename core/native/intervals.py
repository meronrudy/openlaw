"""
Native Interval Algebra
- Replicates PyReason interval semantics for probabilistic bounds
- Provides immutable-style Interval object with helper operations
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Tuple


def _clamp_01(x: float) -> float:
    if x < 0.0:
        return 0.0
    if x > 1.0:
        return 1.0
    return x


def _check_bound(lower: float, upper: float) -> Tuple[float, float]:
    """
    PyReason compatibility:
      - if lower > upper, return [0, 1]
      - otherwise clamp both to [0, 1]
    """
    if lower > upper:
        return 0.0, 1.0
    return _clamp_01(lower), _clamp_01(upper)


@dataclass
class Interval:
    """
    Closed probability interval [l, u], with prior snapshot and static flag.

    Semantics modeled after pyreason.scripts.interval.interval.Interval:
      - reset(): set prev_l/u to current and current to [0, 1]
      - intersection(): [max(l, l2), min(u, u2)] or [0,1] if invalid
      - has_changed(): True iff current != previous snapshot
    """
    l: float
    u: float
    s: bool = False
    prev_l: float = field(default=None)
    prev_u: float = field(default=None)

    def __post_init__(self) -> None:
        # Enforce bounds and default previous snapshot
        nl, nu = _check_bound(float(self.l), float(self.u))
        self.l, self.u = nl, nu
        if self.prev_l is None:
            self.prev_l = self.l
        if self.prev_u is None:
            self.prev_u = self.u

    # Properties for parity with PyReason proxy API
    @property
    def lower(self) -> float:
        return self.l

    @property
    def upper(self) -> float:
        return self.u

    @property
    def static(self) -> bool:
        return self.s

    @property
    def prev_lower(self) -> float:
        return self.prev_l

    @property
    def prev_upper(self) -> float:
        return self.prev_u

    # Mutators with explicit naming to mirror PyReason
    def set_lower_upper(self, l: float, u: float) -> None:
        nl, nu = _check_bound(float(l), float(u))
        self.l, self.u = nl, nu

    def reset(self) -> None:
        self.prev_l = self.l
        self.prev_u = self.u
        self.l = 0.0
        self.u = 1.0

    def set_static(self, static: bool) -> None:
        self.s = bool(static)

    def is_static(self) -> bool:
        return self.s

    def has_changed(self) -> bool:
        return not (self.lower == self.prev_lower and self.upper == self.prev_upper)

    # Interval algebra
    def intersection(self, other: Interval) -> Interval:
        nl = max(self.lower, other.lower)
        nu = min(self.upper, other.upper)
        if nl > nu:
            nl, nu = 0.0, 1.0
        return Interval(nl, nu, False, self.lower, self.upper)

    def to_tuple(self) -> Tuple[float, float]:
        return (self.lower, self.upper)

    # Python protocol helpers
    def __contains__(self, item: Interval) -> bool:
        return self.lower <= item.lower and self.upper >= item.upper

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Interval):
            return NotImplemented
        return self.lower == other.lower and self.upper == other.upper

    def __hash__(self) -> int:
        return hash((self.lower, self.upper))

    def __repr__(self) -> str:
        return f"[{self.lower},{self.upper}]"


# Convenience constructor (parity with interval.closed in PyReason)
def closed(lower: float, upper: float, static: bool = False) -> Interval:
    return Interval(lower, upper, static)


# Functional intersection helper
def intersect(a: Interval, b: Interval) -> Interval:
    return a.intersection(b)