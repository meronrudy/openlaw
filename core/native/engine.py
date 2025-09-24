"""
Native Fixed-Point Reasoning Engine

Implements:
  - Variable grounding and clause evaluation for node- and edge-head rules
  - Deterministic agenda with intersection/override update modes
  - Temporal windows (tmax loop) with delta-t scheduling and convergence checks
  - Integration with annotation and threshold semantics
  - Optional JIT hooks (no-ops unless enabled)
  - Config flag emit_facts to gate emission during parity bring-up

Notes:
  - This implementation supports both node and edge head rules.
  - Grounding and clause evaluation use LabelIndex and Grounder for index-aware joins.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple, DefaultDict
from collections import defaultdict

import networkx as nx
import logging

from .interpretation import Interpretation
from .jit import get_njit
from .annotate import ANNOTATION_REGISTRY
from .thresholds import Threshold, evaluate_threshold
from .intervals import Interval, closed
from .rules import NativeRule, Clause, DEFAULT_THRESHOLD
from .labels import LabelIndex
from .grounder import ground_rule, eval_clause_on_assignment
from .temporal import TemporalScheduler

logger = logging.getLogger(__name__)


@dataclass
class EngineConfig:
    aggregator: str = "min"
    alpha: float = 0.8
    enable_jit: bool = False
    deterministic: bool = True
    update_mode: str = "intersection"  # "intersection" or "override"
    inconsistency_check: bool = True
    persistent: bool = True
    atom_trace: bool = False
    save_graph_attrs_to_rule_trace: bool = False
    emit_facts: bool = False  # gate native fact emission for strict parity bring-up


class FixedPointEngine:
    """
    Native fixed-point engine. Invoked by the facade.
    """

    def __init__(self, config: Optional[EngineConfig] = None):
        self.config = config or EngineConfig()
        self._nj = get_njit(self.config.enable_jit)
        self._aggregators = dict(ANNOTATION_REGISTRY)

    def run(
        self,
        graph: nx.DiGraph,
        facts_node: Any,   # accepted for API compatibility (unused here)
        facts_edge: Any,   # accepted for API compatibility (unused here)
        rules: List[NativeRule],
        tmax: int = 1,
        convergence_threshold: float = -1,
        convergence_bound_threshold: float = -1,
        verbose: bool = False,
    ) -> Interpretation:
        """
        Execute native reasoning and return an Interpretation.
        """
        interp = Interpretation()

        # Build label indices from graph attributes (heuristic parity)
        label_index: LabelIndex = LabelIndex.from_graph(graph)

        # Prepare deterministic rule ordering
        native_rules: List[NativeRule] = list(rules)
        if self.config.deterministic:
            native_rules = sorted(native_rules, key=lambda r: (r.rule_type, r.id))

        # Temporal scheduler buffers updates per timestep (t + delta)
        scheduler = TemporalScheduler()

        # Timestep loop
        t = 0
        converged = False
        while tmax == -1 or t < tmax:
            # Schedule derivations for rules at this timestep
            for r in native_rules:
                try:
                    r.validate()
                except Exception:
                    continue

                ann_fn = self._aggregators.get(r.ann_fn) if r.ann_fn else None

                # Ground structural variables via index-aware joins
                assignments = ground_rule(r, label_index)
                if not assignments:
                    continue

                # Group assignments by head key (node-id or (u,v))
                grouped: DefaultDict[Any, List[Dict[str, str]]] = defaultdict(list)
                if r.rule_type == "node":
                    head_var = r.head_variables[0] if r.head_variables else "x"
                    for asg in assignments:
                        if head_var in asg:
                            grouped[asg[head_var]].append(asg)
                else:  # "edge"
                    hu, hv = r.head_variables[0], r.head_variables[1]
                    for asg in assignments:
                        if hu in asg and hv in asg:
                            grouped[(asg[hu], asg[hv])].append(asg)

                # For each head group, evaluate thresholds and aggregate clause intervals
                for head_key, group_asgs in grouped.items():
                    if not group_asgs:
                        continue

                    annotations: List[List[Interval]] = []
                    thresholds_ok = True

                    for idx, cl in enumerate(r.clauses):
                        clause_intervals: List[Interval] = []
                        satisfied = 0
                        total = 0

                        for asg in group_asgs:
                            ok, itv = eval_clause_on_assignment(cl, asg, label_index)
                            total += 1
                            if ok:
                                satisfied += 1
                                clause_intervals.append(itv)

                        # Evaluate threshold (default to number/total >= 1.0 if unspecified)
                        thr_spec = r.thresholds[idx] if (idx < len(r.thresholds) and len(r.thresholds) > 0) else DEFAULT_THRESHOLD
                        thr = Threshold(thr_spec.quantifier, thr_spec.quantifier_type, thr_spec.thresh)
                        if not evaluate_threshold(
                            thr,
                            satisfied_count=satisfied,
                            total_count=total,
                            available_count=total,
                        ):
                            thresholds_ok = False
                            break

                        # Ensure at least one interval for aggregator stability
                        if not clause_intervals:
                            clause_intervals = [closed(0.0, 1.0)]
                        annotations.append(clause_intervals)

                    if not thresholds_ok:
                        continue

                    # Determine head bound
                    if ann_fn:
                        weights = r.weights if (r.weights and len(r.weights) == len(annotations)) else [1.0] * len(annotations)
                        try:
                            head_itv = ann_fn(annotations, weights)
                            head_itv = _clamp01(head_itv)
                        except Exception:
                            head_itv = closed(0.0, 1.0)
                    else:
                        l, u = r.head_bound if r.head_bound is not None else (1.0, 1.0)
                        head_itv = closed(float(l), float(u))

                    # Build statement key and schedule update at t + delta
                    if r.rule_type == "node":
                        nid = str(head_key)
                        stmt = f"{r.target_label}({nid})"
                    else:
                        u, v = str(head_key[0]), str(head_key[1])
                        stmt = f"{r.target_label}({u},{v})"

                    t_effect = (t + int(r.delta)) if r.delta else t
                    scheduler.schedule(
                        t_effect=t_effect,
                        statement=stmt,
                        interval=head_itv,
                        mode=self.config.update_mode,
                        set_static=r.set_static,
                        source=str(r.id),
                    )

                    # If this is an edge rule that infers edges with a label, also schedule that label
                    if r.rule_type == "edge" and r.infer_edges and (r.infer_edge_label or "").strip():
                        u2, v2 = (str(head_key[0]), str(head_key[1]))
                        infer_stmt = f"{r.infer_edge_label}({u2},{v2})"
                        scheduler.schedule(
                            t_effect=t_effect,
                            statement=infer_stmt,
                            interval=head_itv,
                            mode=self.config.update_mode,
                            set_static=r.set_static,
                            source=str(r.id),
                        )

                    # Optional lightweight trace for debugging (no PII by default)
                    if self.config.atom_trace or self.config.save_graph_attrs_to_rule_trace:
                        try:
                            interp.add_trace_event(
                                {
                                    "t": int(t),
                                    "rule_id": str(r.id),
                                    "target_label": str(r.target_label),
                                    "head": stmt,
                                    "delta": int(r.delta),
                                    "set_static": bool(r.set_static),
                                    "clauses": len(r.clauses),
                                }
                            )
                        except Exception:
                            pass

            # Apply all updates scheduled for this timestep to the interpretation
            changed_count, max_bound_delta = scheduler.flush(
                t=t,
                interpretation=interp,
                default_update_mode=self.config.update_mode,
                emit_facts=self.config.emit_facts,
            )

            if verbose:
                logger.info("[native-engine] t=%s changed=%s max_delta=%.6f", t, changed_count, max_bound_delta)

            # Convergence checks (mirror PyReason modes)
            if convergence_bound_threshold != -1:
                if max_bound_delta <= float(convergence_bound_threshold):
                    converged = True
            elif convergence_threshold != -1:
                if changed_count <= int(convergence_threshold):
                    converged = True
            else:
                # perfect convergence for this iteration if no changes, and nothing pending in future
                if changed_count == 0 and not scheduler.has_pending_after(t):
                    converged = True

            if converged:
                break
            t += 1

        return interp


# -------------------------
# Helpers
# -------------------------

def _clamp01(itv: Interval) -> Interval:
    l = float(itv.lower)
    u = float(itv.upper)
    if l > u:
        return closed(0.0, 1.0)
    l = 0.0 if l < 0.0 else (1.0 if l > 1.0 else l)
    u = 0.0 if u < 0.0 else (1.0 if u > 1.0 else u)
    return closed(l, u)