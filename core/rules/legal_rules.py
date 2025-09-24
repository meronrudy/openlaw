"""
Legal rules catalog and utilities for PyReason integration.

Provides:
- map_burden_to_fn_name(): map jurisdiction/claim to an annotation function name
- default_clause_weights(): produce default [controlling, persuasive, contrary] weights
- build_support_rule(): build the top-level support rule with a burden-aware annotation fn
- build_derivation_rules(): foundational derivation rules for controlling/persuasive/contrary signals

These functions are consumed by the bridge in [python.PyReasonLegalBridge](core/adapters/pyreason_bridge.py:1).
"""

from typing import Dict, Any, List
import numpy as np

from pyreason.scripts.rules.rule import Rule as PRRule


# ---------------------------
# Burden mapping
# ---------------------------

def _threshold_to_fn(threshold: float) -> str:
    """
    Map numeric threshold to annotation function name.
    """
    if threshold >= 0.90:
        return "legal_burden_criminal_090"
    elif threshold >= 0.75:
        return "legal_burden_clear_075"
    # Default civil
    return "legal_burden_civil_051"


def map_burden_to_fn_name(claim: str, jurisdiction: str, burden_cfg: Dict[str, Any]) -> str:
    """
    Resolve which legal burden annotation function to use given claim and jurisdiction.

    burden_cfg example:
      DEFAULT_BURDEN: 0.51
      BURDEN_OVERRIDES:
        US-CA:
          punitive_damages: 0.75
        US-NY:
          fraud: 0.75
        US-FED:
          criminal: 0.90
    """
    default_thresh = float(burden_cfg.get("DEFAULT_BURDEN", 0.51))
    overrides = burden_cfg.get("BURDEN_OVERRIDES", {}) or {}

    # Normalize keys
    j = str(jurisdiction or "").strip()
    c = str(claim or "").strip()

    if j in overrides:
        # Strict match on claim key first
        jmap = overrides[j] or {}
        if c in jmap:
            try:
                return _threshold_to_fn(float(jmap[c]))
            except Exception:
                pass
        # Fallback: category names (e.g., "criminal", "civil") if present
        for k in ("criminal", "civil", "clear_and_convincing"):
            if k in jmap:
                try:
                    return _threshold_to_fn(float(jmap[k]))
                except Exception:
                    pass

    # Global defaults category-level (optional)
    if "GLOBAL" in overrides:
        g = overrides["GLOBAL"] or {}
        if c in g:
            try:
                return _threshold_to_fn(float(g[c]))
            except Exception:
                pass

    # Default
    return _threshold_to_fn(default_thresh)


# ---------------------------
# Weights
# ---------------------------

def default_clause_weights(courts_cfg: Dict[str, Any]) -> List[float]:
    """
    Produce a [w_controlling, w_persuasive, w_contrary] vector summing to 1.0.
    courts_cfg example:
      weights:
        controlling: 0.6
        persuasive: 0.3
        contrary: 0.1
    """
    weights_cfg = (courts_cfg or {}).get("weights", {}) or {}
    w_ctrl = float(weights_cfg.get("controlling", 0.6))
    w_pers = float(weights_cfg.get("persuasive", 0.3))
    w_contra = float(weights_cfg.get("contrary", 0.1))
    total = max(w_ctrl + w_pers + w_contra, 1e-9)
    w = [w_ctrl / total, w_pers / total, w_contra / total]
    return w


# ---------------------------
# Rule builders
# ---------------------------

def build_support_rule(claim: str, ann_fn_name: str, weights: List[float]) -> PRRule:
    """
    Build a top-level support rule for a claim:
      support_for_{claim}(x) : {ann_fn_name} <- 0 controlling_support(x) : [0.51,1], persuasive_support(x) : [0.51,1], contrary_authority(x) : [0,0.49]

    The weights are injected as clause weights in the same order as the body:
      [controlling_support, persuasive_support, contrary_authority]
    """
    head = f"support_for_{claim}"
    rule_text = (
        f"{head}(x) : {ann_fn_name} <- "
        f"0 controlling_support(x):[0.51,1], "
        f"persuasive_support(x):[0.51,1], "
        f"contrary_authority(x):[0,0.49]"
    )
    # Provide a descriptive name for trace/debug
    name = f"support_{claim}_burdened"
    # PRRule accepts optional weights list; the parser will validate length
    return PRRule(rule_text=rule_text, name=name, weights=np.array(weights, dtype=np.float64))


def build_derivation_rules() -> List[PRRule]:
    """
    Build foundational derivation rules. These rely on labels that the pipeline/normalization step
    should provide via GraphML or Facts (e.g., cites edges, same_issue edges, controlling_relation edges).

    Conventions (labels expected to be present as graph attributes or Facts):
      - cites(x,y) : edge label indicating x cites y
      - same_issue(x,y) : edge label indicating overlapping legal issue
      - controlling_relation(x,y) : edge label indicating y is controlling for x (derived from court hierarchy/jurisdiction)
      - persuasive_relation(x,y) : edge label indicating y is persuasive for x
      - precedential(y) : node label that y is precedential (published, not depublished)
      - contrary_to(x,y) : edge label indicating y is contrary authority relative to x

    These baseline rules can be refined as the ontology matures.
    """
    rules: List[PRRule] = []

    # controlling_for(x,y) as edge label
    r1 = (
        "controlling_for(x,y) : [1,1] <- "
        "0 cites(x,y):[1,1], same_issue(x,y):[0.51,1], "
        "controlling_relation(x,y):[1,1], precedential(y):[1,1]"
    )
    rules.append(PRRule(rule_text=r1, name="derive_controlling_for"))

    # persuasive_for(x,y) as edge label (non-controlling but supportive)
    r2 = (
        "persuasive_for(x,y) : [1,1] <- "
        "0 cites(x,y):[1,1], same_issue(x,y):[0.51,1], persuasive_relation(x,y):[1,1]"
    )
    rules.append(PRRule(rule_text=r2, name="derive_persuasive_for"))

    # controlling_support(x) node label from controlling_for edges
    r3 = (
        "controlling_support(x) : [0.51,1] <- "
        "0 controlling_for(x,y):[1,1]"
    )
    rules.append(PRRule(rule_text=r3, name="derive_controlling_support"))

    # persuasive_support(x) node label from persuasive_for edges
    r4 = (
        "persuasive_support(x) : [0.51,1] <- "
        "0 persuasive_for(x,y):[1,1]"
    )
    rules.append(PRRule(rule_text=r4, name="derive_persuasive_support"))

    # contrary_authority(x) node label from contrary_to edges
    r5 = (
        "contrary_authority(x) : [1,1] <- "
        "0 contrary_to(x,y):[1,1]"
    )
    rules.append(PRRule(rule_text=r5, name="derive_contrary_authority"))

    return rules