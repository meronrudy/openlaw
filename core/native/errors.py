"""
Native Reasoner Error Types

Typed exceptions for configuration, compilation, grounding, temporal, evaluation,
and validation failures. These provide actionable messages with contextual fields
(rule_id, premises, timestep, statement, etc.) to aid diagnosis and remediation.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict, List, Optional


class NativeEngineError(Exception):
    """Base error for all native reasoner failures."""


@dataclass
class ConfigError(NativeEngineError):
    """Configuration or policy error."""
    message: str
    config_path: Optional[str] = None
    key: Optional[str] = None
    context: Optional[Dict[str, Any]] = None

    def __str__(self) -> str:
        loc = f" at {self.config_path}" if self.config_path else ""
        key = f" (key={self.key})" if self.key else ""
        return f"ConfigError{loc}{key}: {self.message}"


@dataclass
class CompilationError(NativeEngineError):
    """Rule compilation/parsing error."""
    message: str
    rule_id: Optional[str] = None
    rule_text: Optional[str] = None
    position: Optional[int] = None
    context: Optional[Dict[str, Any]] = None

    def __str__(self) -> str:
        rid = f"[rule_id={self.rule_id}] " if self.rule_id else ""
        pos = f" at pos {self.position}" if self.position is not None else ""
        return f"CompilationError {rid}{self.message}{pos}"


@dataclass
class GroundingError(NativeEngineError):
    """Variable grounding, join, or candidate lookup error."""
    message: str
    rule_id: Optional[str] = None
    premises: Optional[List[str]] = None
    statement: Optional[str] = None
    context: Optional[Dict[str, Any]] = None

    def __str__(self) -> str:
        rid = f"[rule_id={self.rule_id}] " if self.rule_id else ""
        prem = f" premises={self.premises}" if self.premises else ""
        stmt = f" statement={self.statement}" if self.statement else ""
        return f"GroundingError {rid}{self.message}{prem}{stmt}"


@dataclass
class TemporalError(NativeEngineError):
    """Temporal windowing or validity interval error."""
    message: str
    rule_id: Optional[str] = None
    timestep: Optional[int] = None
    valid_from: Optional[str] = None
    valid_to: Optional[str] = None
    context: Optional[Dict[str, Any]] = None

    def __str__(self) -> str:
        rid = f"[rule_id={self.rule_id}] " if self.rule_id else ""
        ts = f" t={self.timestep}" if self.timestep is not None else ""
        vf = f" valid_from={self.valid_from}" if self.valid_from else ""
        vt = f" valid_to={self.valid_to}" if self.valid_to else ""
        return f"TemporalError {rid}{self.message}{ts}{vf}{vt}"


@dataclass
class EvaluationError(NativeEngineError):
    """Fixed-point evaluation or aggregation/threshold failure."""
    message: str
    rule_id: Optional[str] = None
    aggregator: Optional[str] = None
    threshold: Optional[str] = None
    details: Optional[Dict[str, Any]] = None

    def __str__(self) -> str:
        rid = f"[rule_id={self.rule_id}] " if self.rule_id else ""
        agg = f" aggregator={self.aggregator}" if self.aggregator else ""
        thr = f" threshold={self.threshold}" if self.threshold else ""
        return f"EvaluationError {rid}{self.message}{agg}{thr}"


@dataclass
class ValidationError(NativeEngineError):
    """Parity validation failure between engines."""
    message: str
    reason: Optional[str] = None
    key: Optional[str] = None
    left: Optional[Any] = None
    right: Optional[Any] = None
    context: Optional[Dict[str, Any]] = None

    def __str__(self) -> str:
        r = f" reason={self.reason}" if self.reason else ""
        k = f" key={self.key}" if self.key else ""
        return f"ValidationError: {self.message}{r}{k}"