"""
Native Interpretation Model

Provides an interpretation structure compatible with downstream consumers and
the PyReason bridge expectations (via get_dict()). Holds probability interval
facts keyed by statement and optional lightweight trace for debugging.

This module is intended to be used by core/native/engine.py and imported by the
native facade. It mirrors the minimal API shape exposed by the PyReason
Interpretation wrapper we previously used.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Tuple, Optional

from core.native.intervals import Interval, closed


@dataclass
class SupportPath:
    """
    Captures a single support path for a derived statement.
    """
    rule_id: str
    authority: str
    premises: List[str]
    confidence: float
    path_confidence: float


@dataclass
class Interpretation:
    """
    Interpretation over statements mapping to probability intervals.
    """
    facts: Dict[str, Interval] = field(default_factory=dict)
    trace: List[Dict[str, Any]] = field(default_factory=list)
    supports: Dict[str, List[SupportPath]] = field(default_factory=dict)

    # Fact management ---------------------------------------------------------

    def set_fact(self, statement: str, interval: Interval) -> None:
        """
        Set/overwrite the probability interval for a statement.
        """
        self.facts[str(statement)] = interval

    def upsert_fact_intersection(self, statement: str, interval: Interval) -> None:
        """
        Update the statement interval using intersection semantics:
          new = old ∩ interval, default old=[0,1] if absent
        """
        key = str(statement)
        if key in self.facts:
            self.facts[key] = self.facts[key].intersection(interval)
        else:
            self.facts[key] = interval

    def get_fact(self, statement: str) -> Optional[Interval]:
        return self.facts.get(str(statement))

    def has_fact(self, statement: str) -> bool:
        return str(statement) in self.facts

    # Support and trace -------------------------------------------------------

    def add_support_path(
        self,
        statement: str,
        rule_id: str,
        authority: str,
        premises: List[str],
        rule_confidence: float,
        path_confidence: float,
    ) -> None:
        path = SupportPath(
            rule_id=str(rule_id),
            authority=str(authority),
            premises=[str(p) for p in premises],
            confidence=float(rule_confidence),
            path_confidence=float(path_confidence),
        )
        self.supports.setdefault(str(statement), []).append(path)

    def add_trace_event(self, event: Dict[str, Any]) -> None:
        """
        Append a lightweight trace event for debugging. This is optional and
        can be disabled by the engine for privacy or performance.
        """
        try:
            self.trace.append(dict(event))
        except Exception:
            # Ensure trace never breaks evaluation
            pass

    # Export ------------------------------------------------------------------

    def get_dict(self) -> Dict[str, Any]:
        """
        Return a stable, serializable representation similar to what downstream
        consumers expect from the PyReason Interpretation.
        """
        out_facts: Dict[str, Tuple[float, float]] = {}
        for k, iv in self.facts.items():
            out_facts[k] = (float(iv.lower), float(iv.upper))

        out_supports: Dict[str, List[Dict[str, Any]]] = {}
        for k, paths in self.supports.items():
            out_supports[k] = [
                {
                    "rule_id": p.rule_id,
                    "authority": p.authority,
                    "premises": list(p.premises),
                    "confidence": p.confidence,
                    "path_confidence": p.path_confidence,
                }
                for p in paths
            ]

        return {
            "facts": out_facts,
            "supports": out_supports,
            "trace": list(self.trace),
        }

    def export(self, profile: str = "default_profile", redaction: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Export interpretation with privacy-aware filtered views.

        Profiles:
          - default_profile: facts only; supports and trace omitted
          - audit_profile: include facts, supports, and trace

        Redaction (optional):
          - redaction: {
              "labels_blocklist": [ "raw_document_text", ... ]
            }
            Blocks facts whose label appears in labels_blocklist.
        """
        data = self.get_dict()
        facts: Dict[str, Tuple[float, float]] = dict(data.get("facts", {}))
        supports = data.get("supports", {})
        trace = data.get("trace", [])

        # Apply label-based redaction if configured
        try:
            block = set((redaction or {}).get("labels_blocklist", []) or [])
            if block:
                def _label_of(stmt: str) -> str:
                    i = stmt.find("(")
                    return stmt[:i] if i > 0 else stmt
                facts = {k: v for k, v in facts.items() if _label_of(k) not in block}
        except Exception:
            pass

        if profile == "audit_profile":
            return {"facts": facts, "supports": supports, "trace": trace}
        # default_profile
        return {"facts": facts, "supports": {}, "trace": []}

    def to_json(self, indent: int = 2) -> str:
        """
        Serialize the interpretation to a JSON string.
        """
        try:
            import json  # local import to avoid global dependency during early bring-up
        except Exception:
            return str(self.get_dict())
        return json.dumps(self.get_dict(), indent=indent, default=str, sort_keys=True)

    def to_jsonl(self) -> str:
        """
        Serialize facts as JSON Lines (one fact per line). Supports downstream pipelines
        that stream fact statements with bounds.
        """
        try:
            import json  # local import to avoid global dependency during early bring-up
        except Exception:
            # Fallback to tab-separated plain lines
            lines = [f"{k}\t{self.facts[k].lower:.6f}\t{self.facts[k].upper:.6f}" for k in sorted(self.facts.keys())]
            return "\n".join(lines)
        lines = []
        for k in sorted(self.facts.keys()):
            iv = self.facts[k]
            lines.append(json.dumps({"statement": k, "lower": float(iv.lower), "upper": float(iv.upper)}, sort_keys=True))
        return "\n".join(lines)
    # Convenience -------------------------------------------------------------

    @staticmethod
    def from_pairs(pairs: List[Tuple[str, Tuple[float, float]]]) -> "Interpretation":
        """
        Build an interpretation from (statement, (l,u)) pairs.
        """
        interp = Interpretation()
        for stmt, (l, u) in pairs:
            interp.set_fact(stmt, closed(float(l), float(u)))
        return interp