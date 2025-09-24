"""
Temporal scheduling utilities for the native reasoning engine.

Provides:
- ScheduledUpdate: a scheduled write to a statement at a given timestep.
- TemporalScheduler: queue and flush scheduled updates into an Interpretation
  with support for intersection/override modes and set_static semantics.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional, Set
from collections import defaultdict

from .intervals import Interval, closed
from .interpretation import Interpretation


@dataclass
class ScheduledUpdate:
    statement: str
    interval: Interval
    mode: str  # "intersection" or "override"
    set_static: bool = False
    source: Optional[str] = None  # rule id or origin identifier


class TemporalScheduler:
    """
    Queue of timed updates to be applied to an Interpretation at specific timesteps.
    """

    def __init__(self) -> None:
        self._queue: Dict[int, List[ScheduledUpdate]] = defaultdict(list)
        self._static: Set[str] = set()

    def clear(self) -> None:
        self._queue.clear()
        self._static.clear()

    def schedule(
        self,
        t_effect: int,
        statement: str,
        interval: Interval,
        mode: str = "intersection",
        set_static: bool = False,
        source: Optional[str] = None,
    ) -> None:
        self._queue[int(t_effect)].append(
            ScheduledUpdate(str(statement), interval, mode, bool(set_static), str(source) if source is not None else None)
        )

    def has_pending_after(self, t: int) -> bool:
        for k in self._queue.keys():
            if k > t:
                return True
        return False

    def flush(
        self,
        t: int,
        interpretation: Interpretation,
        default_update_mode: str = "intersection",
        emit_facts: bool = True,
    ) -> Tuple[int, float]:
        """
        Apply all updates scheduled for timestep t, grouping by statement.
        For intersection mode: intersect all candidate intervals for a statement.
        For override mode: choose the most specific (narrowest) interval; tie-break on source, then bounds.
        Returns:
            (changed_count, max_bound_delta)
        """
        updates = self._queue.pop(int(t), [])
        if not updates or not emit_facts:
            return 0, 0.0

        changed_count = 0
        max_bound_delta = 0.0

        def _delta(prev: Interval, cur: Interval) -> float:
            return max(abs(prev.lower - cur.lower), abs(prev.upper - cur.upper))

        # Group by statement
        grouped: Dict[str, List[ScheduledUpdate]] = defaultdict(list)
        for upd in updates:
            grouped[upd.statement].append(upd)
            if upd.set_static:
                self._static.add(upd.statement)

        # Apply per statement
        for stmt, upds in grouped.items():
            # If already static and present, skip
            if stmt in self._static and interpretation.has_fact(stmt):
                continue

            # Resolve combined interval per update_mode
            mode = (default_update_mode or "intersection").lower()
            if mode == "intersection":
                # Intersect all candidate intervals
                combined = None
                for u in upds:
                    combined = u.interval if combined is None else combined.intersection(u.interval)
                if combined is None:
                    combined = closed(0.0, 1.0)
            else:
                # Override: choose narrowest interval; tie-breakers: source id, then lower/upper
                def _key(u: ScheduledUpdate):
                    width = float(u.interval.upper) - float(u.interval.lower)
                    src = u.source or ""
                    return (width, src, float(u.interval.lower), float(u.interval.upper))
                chosen = sorted(upds, key=_key)[0]
                combined = chosen.interval

            # Apply update
            prev = interpretation.get_fact(stmt) or closed(0.0, 1.0)
            if mode == "intersection":
                interpretation.upsert_fact_intersection(stmt, combined)
                cur = interpretation.get_fact(stmt) or combined
            else:
                interpretation.set_fact(stmt, combined)
                cur = combined

            d = _delta(prev, cur)
            if d > 0:
                changed_count += 1
                if d > max_bound_delta:
                    max_bound_delta = d

        return changed_count, max_bound_delta