"""
Native Legal Reasoning Facade
- API-preserving facade for replacing PyReason with a native engine
- Provides run_reasoning(...) compatible with PyReason bridge call sites
- Includes exact-equality validator helpers for dual-engine parity gating
"""
from __future__ import annotations
from typing import Any, Dict, List, Optional, Tuple
import logging
import os

from core.native.engine import FixedPointEngine, EngineConfig
from core.native.compiler import compile_pyreason_rules_to_native
from core.native.rules import NativeRule

logger = logging.getLogger(__name__)

class NativeEngineError(Exception):
    """Base error for native reasoner"""

class ValidationError(NativeEngineError):
    """Validation failure between engines"""

class NotImplementedComponentError(NativeEngineError):
    """Raised when a referenced component is not yet implemented"""

class NativeInterpretation:
    """
    Minimal interpretation object with API similar to PyReason Interpretation
    get_dict() returns a serializable representation
    (Kept for backward import-compatibility in validator)
    """
    def __init__(self, facts: Dict[str, Tuple[float, float]] | None = None, trace: Optional[List[Dict[str, Any]]] = None):
        self._facts: Dict[str, Tuple[float, float]] = facts or {}
        self._trace: List[Dict[str, Any]] = trace or []

    def get_dict(self) -> Dict[str, Any]:
        return {"facts": self._facts, "trace": list(self._trace)}

class NativeLegalFacade:
    """
    API-preserving facade used by legal workflows in place of PyReason bridge.
    """
    def __init__(self, privacy_defaults: bool = True):
        # Privacy posture flags (no-op placeholders; tracing controlled in engine config)
        self.privacy_defaults = privacy_defaults
        self.atom_trace = not privacy_defaults and False
        self.save_graph_attrs_to_rule_trace = not privacy_defaults and False

        # Engine configuration defaults (aligned with ReasoningConfig)
        self.aggregator = "min"
        self.alpha = 0.8
        self.enable_jit = False
        self.deterministic = True
        self.update_mode = "intersection"  # or "override"

        # Parity bring-up control: do not emit facts unless explicitly enabled
        # to avoid spurious inequality before full parity is achieved.
        env_emit = os.getenv("NATIVE_ENGINE_EMIT_FACTS", "").strip().lower()
        self.emit_facts = env_emit in ("1", "true", "yes")

    def _engine(self) -> FixedPointEngine:
        cfg = EngineConfig(
            aggregator=self.aggregator,
            alpha=self.alpha,
            enable_jit=self.enable_jit,
            deterministic=self.deterministic,
            update_mode=self.update_mode,
            atom_trace=self.atom_trace,
            save_graph_attrs_to_rule_trace=self.save_graph_attrs_to_rule_trace,
            emit_facts=self.emit_facts,
        )
        return FixedPointEngine(cfg)

    def run_reasoning(
        self,
        graph: Any,
        facts_node: Any,
        facts_edge: Any,
        rules: List[Any],
        tmax: int = 1,
        convergence_threshold: float = -1,
        convergence_bound_threshold: float = -1,
        verbose: bool = False,
    ):
        """
        Execute native reasoning with a call signature compatible with
        PyReasonLegalBridge.run_reasoning(...).

        rules may be PyReason Rule objects; they will be compiled to NativeRule.
        """
        # Accept either already-native rules or PyReason rules; compile only what is needed
        native_rules: List[NativeRule] = []
        try:
            native_rules = [r for r in rules if isinstance(r, NativeRule)]
            to_compile = [r for r in rules if not isinstance(r, NativeRule)]
        except Exception:
            to_compile = rules
        if to_compile:
            native_rules.extend(compile_pyreason_rules_to_native(to_compile))

        # Run native engine
        engine = self._engine()
        interp = engine.run(
            graph=graph,
            facts_node=facts_node,
            facts_edge=facts_edge,
            rules=native_rules,
            tmax=tmax,
            convergence_threshold=convergence_threshold,
            convergence_bound_threshold=convergence_bound_threshold,
            verbose=verbose,
        )
        return interp

class ExactEqualityValidator:
    """
    Validates parity between native and pyreason interpretations with exact
    equality requirements for both derived facts and probability intervals.
    """
    def validate(self, left: Any, right: Any) -> Dict[str, Any]:
        ldict = left.get_dict() if hasattr(left, "get_dict") else {}
        rdict = right.get_dict() if hasattr(right, "get_dict") else {}

        lfacts: Dict[str, Tuple[float, float]] = ldict.get("facts", {})
        rfacts: Dict[str, Tuple[float, float]] = rdict.get("facts", {})

        # Keys must match exactly
        lkeys = set(lfacts.keys())
        rkeys = set(rfacts.keys())
        if lkeys != rkeys:
            return {
                "match": False,
                "reason": "facts_keys_mismatch",
                "left_only": sorted(lkeys - rkeys),
                "right_only": sorted(rkeys - lkeys),
            }

        # Intervals must match exactly
        for k in sorted(lfacts.keys()):
            if tuple(lfacts[k]) != tuple(rfacts[k]):
                return {
                    "match": False,
                    "reason": "interval_mismatch",
                    "key": k,
                    "left": lfacts[k],
                    "right": rfacts[k],
                }

        return {"match": True}

def wrap_pyreason_interpretation(pyreason_interp: Any) -> NativeInterpretation:
    """
    Convert PyReason Interpretation (nested by time -> component -> {label: (l,u)})
    into a flat facts mapping suitable for ExactEqualityValidator.

    Strategy:
      - Use the last timestep (max key) from the PyReason interpretation dict
      - For node entries: emit "label(node_id)" -> (l, u)
      - For edge entries: emit "label(u,v)"     -> (l, u)
    """
    facts: Dict[str, Tuple[float, float]] = {}
    try:
        d = pyreason_interp.get_dict()
        if isinstance(d, dict) and d:
            # Determine last timestep
            try:
                times = [int(k) for k in d.keys()]
            except Exception:
                # keys may already be ints
                times = list(d.keys())
            if len(times) > 0:
                t = max(times)
                layer = d.get(t, {})
                # layer: { component (node_id or (u,v)) -> { label_str: (l,u) } }
                for comp, labels in layer.items():
                    if isinstance(comp, (tuple, list)) and len(comp) == 2:
                        u, v = str(comp[0]), str(comp[1])
                        for lbl, lu in (labels or {}).items():
                            facts[f"{str(lbl)}({u},{v})"] = (float(lu[0]), float(lu[1]))
                    else:
                        nid = str(comp)
                        for lbl, lu in (labels or {}).items():
                            facts[f"{str(lbl)}({nid})"] = (float(lu[0]), float(lu[1]))
    except Exception:
        facts = {}
    return NativeInterpretation(facts=facts)