"""
Native Legal Rules Builder (Native-only)

Builds legal rules as NativeRule objects without any PyReason dependency.
Exports:
- map_burden_to_ann_fn_name()
- default_clause_weights()
- build_support_rule_native()
- build_derivation_rules_native()
- build_rules_for_claim_native()
"""

from __future__ import annotations
from typing import Dict, Any, List, Tuple

from core.native.rules import NativeRule, Clause, default_thresholds_for


# ---------------------------
# Burden mapping
# ---------------------------

def _threshold_to_fn(threshold: float) -> str:
    """
    Map numeric threshold to native annotation function name.
    """
    if threshold >= 0.90:
        return "legal_burden_criminal_090"
    elif threshold >= 0.75:
        return "legal_burden_clear_075"
    # Default civil
    return "legal_burden_civil_051"


def map_burden_to_ann_fn_name(claim: str, jurisdiction: str, burden_cfg: Dict[str, Any]) -> str:
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
    default_thresh = float((burden_cfg or {}).get("DEFAULT_BURDEN", 0.51))
    overrides = (burden_cfg or {}).get("BURDEN_OVERRIDES", {}) or {}

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
# Jurisdiction lineage utilities
# ---------------------------

def compute_jurisdiction_lineage(courts_cfg: Dict[str, Any], jurisdiction: str) -> List[str]:
    """
    Compute jurisdiction lineage using courts_cfg.hierarchy with breadth-first traversal.
    Returns list like [jurisdiction, parent1, parent2, ...] with no duplicates.
    """
    lineage: List[str] = []
    try:
        hier = (courts_cfg or {}).get("hierarchy", {}) or {}
        j = str(jurisdiction or "").strip()
        seen = set()
        frontier = [j]
        while frontier:
            cur = frontier.pop(0)
            if cur in seen or not cur:
                continue
            seen.add(cur)
            lineage.append(cur)
            for parent in (hier.get(cur, []) or []):
                if parent not in seen:
                    frontier.append(parent)
    except Exception:
        # Fallback to just the given jurisdiction
        if jurisdiction:
            lineage = [str(jurisdiction)]
    return lineage

# ---------------------------
# Jurisdiction rule selection (local > parent > federal)
# ---------------------------

def filter_rules_by_jurisdiction(
    rules: List[NativeRule],
    courts_cfg: Dict[str, Any],
    jurisdiction: str,
) -> List[NativeRule]:
    """
    Filter or keep rules based on jurisdictional overrides.

    Policy surface (optional) in courts_cfg:
      rule_overrides:
        US-CA:
          exclude_labels: ["persuasive_support"]
          include_labels: []
        US-FED:
          exclude_labels: []
          include_labels: []

    Semantics:
      - Build lineage [jurisdiction, parent1, parent2, ...] via compute_jurisdiction_lineage
      - Starting from LOCAL down the lineage, collect include/exclude directives
      - LOCAL overrides take precedence (processed first); parents fill only where LOCAL not specified
      - Filtering applies to NativeRule.target_label (node/edge labels), leaving other rules intact
      - If no overrides exist, returns rules unchanged
    """
    overrides = (courts_cfg or {}).get("rule_overrides", {}) or {}
    lineage = compute_jurisdiction_lineage(courts_cfg, jurisdiction)

    include: Dict[str, bool] = {}
    exclude: Dict[str, bool] = {}

    # Process lineage in order: local first, then parents
    for j in lineage:
        if j in overrides:
            cfg = overrides[j] or {}
            for lbl in (cfg.get("include_labels", []) or []):
                k = str(lbl).strip()
                if k and k not in include and k not in exclude:
                    include[k] = True
            for lbl in (cfg.get("exclude_labels", []) or []):
                k = str(lbl).strip()
                if k and k not in include and k not in exclude:
                    exclude[k] = True

    if not include and not exclude:
        return rules

    filtered: List[NativeRule] = []
    for r in rules:
        lbl = str(getattr(r, "target_label", "") or "").strip()
        if not lbl:
            filtered.append(r)
            continue
        # Exclude beats include if both seen in parent layers (shouldn't happen due to precedence)
        if lbl in exclude:
            continue
        if include and (lbl in include):
            filtered.append(r)
        elif include and (lbl not in include):
            # When include set exists, only include listed labels
            continue
        else:
            # No include set, only enforce exclude
            filtered.append(r)
    return filtered

# ---------------------------
# Helpers for building clauses
# ---------------------------

def _cl_node(label: str, vars_: List[str], bound: Tuple[float, float]) -> Clause:
    return Clause(ctype="node", label=label, variables=list(vars_), bound=(float(bound[0]), float(bound[1])))


def _cl_edge(label: str, vars_: List[str], bound: Tuple[float, float]) -> Clause:
    return Clause(ctype="edge", label=label, variables=list(vars_), bound=(float(bound[0]), float(bound[1])))


# ---------------------------
# Rule builders (Native)
# ---------------------------

def build_support_rule_native(claim: str, ann_fn_name: str, weights: List[float]) -> NativeRule:
    """
    Build a top-level support rule for a claim using a burden-aware annotation function.

      support_for_{claim}(x) : {ann_fn_name} <- 
          controlling_support(x):[0.51,1], 
          persuasive_support(x):[0.51,1], 
          contrary_authority(x):[0,0.49]

    The weights are injected as clause weights in the same order as the body:
      [controlling_support, persuasive_support, contrary_authority]
    """
    head = f"support_for_{claim}"
    clauses: List[Clause] = [
        _cl_node("controlling_support", ["x"], (0.51, 1.0)),
        _cl_node("persuasive_support", ["x"], (0.51, 1.0)),
        _cl_node("contrary_authority", ["x"], (0.0, 0.49)),
    ]
    nr = NativeRule(
        id=f"support_{claim}_burdened",
        rule_type="node",
        target_label=head,
        head_variables=["x"],
        clauses=clauses,
        thresholds=default_thresholds_for(clauses),
        head_bound=None,            # use annotation function
        ann_fn=str(ann_fn_name or ""),
        weights=list(weights or [1.0, 1.0, 1.0]),
        set_static=False,
    )
    nr.validate()
    return nr


def build_derivation_rules_native() -> List[NativeRule]:
    """
    Build foundational derivation rules expected by the legal ontology.

    Conventions (labels expected in graph attrs/facts):
      - cites(x,y)
      - same_issue(x,y)
      - controlling_relation(x,y)
      - persuasive_relation(x,y)
      - precedential(y)
      - contrary_to(x,y)
    """
    rules: List[NativeRule] = []

    # controlling_for(x,y) edge label
    c1 = [
        _cl_edge("cites", ["x", "y"], (1.0, 1.0)),
        _cl_edge("same_issue", ["x", "y"], (0.51, 1.0)),
        _cl_edge("controlling_relation", ["x", "y"], (1.0, 1.0)),
        _cl_node("precedential", ["y"], (1.0, 1.0)),
    ]
    r1 = NativeRule(
        id="derive_controlling_for",
        rule_type="edge",
        target_label="controlling_for",
        head_variables=["x", "y"],
        clauses=c1,
        thresholds=default_thresholds_for(c1),
        head_bound=(1.0, 1.0),
        ann_fn="",
        weights=[],
        set_static=False,
    )
    r1.validate()
    rules.append(r1)

    # persuasive_for(x,y) edge label
    c2 = [
        _cl_edge("cites", ["x", "y"], (1.0, 1.0)),
        _cl_edge("same_issue", ["x", "y"], (0.51, 1.0)),
        _cl_edge("persuasive_relation", ["x", "y"], (1.0, 1.0)),
    ]
    r2 = NativeRule(
        id="derive_persuasive_for",
        rule_type="edge",
        target_label="persuasive_for",
        head_variables=["x", "y"],
        clauses=c2,
        thresholds=default_thresholds_for(c2),
        head_bound=(1.0, 1.0),
        ann_fn="",
        weights=[],
        set_static=False,
    )
    r2.validate()
    rules.append(r2)

    # controlling_support(x) node label from controlling_for edges
    c3 = [
        _cl_edge("controlling_for", ["x", "y"], (1.0, 1.0)),
    ]
    r3 = NativeRule(
        id="derive_controlling_support",
        rule_type="node",
        target_label="controlling_support",
        head_variables=["x"],
        clauses=c3,
        thresholds=default_thresholds_for(c3),
        head_bound=(0.51, 1.0),
        ann_fn="",
        weights=[],
        set_static=False,
    )
    r3.validate()
    rules.append(r3)

    # persuasive_support(x) node label from persuasive_for edges
    c4 = [
        _cl_edge("persuasive_for", ["x", "y"], (1.0, 1.0)),
    ]
    r4 = NativeRule(
        id="derive_persuasive_support",
        rule_type="node",
        target_label="persuasive_support",
        head_variables=["x"],
        clauses=c4,
        thresholds=default_thresholds_for(c4),
        head_bound=(0.51, 1.0),
        ann_fn="",
        weights=[],
        set_static=False,
    )
    r4.validate()
    rules.append(r4)

    # contrary_authority(x) node label from contrary_to edges
    c5 = [
        _cl_edge("contrary_to", ["x", "y"], (1.0, 1.0)),
    ]
    r5 = NativeRule(
        id="derive_contrary_authority",
        rule_type="node",
        target_label="contrary_authority",
        head_variables=["x"],
        clauses=c5,
        thresholds=default_thresholds_for(c5),
        head_bound=(1.0, 1.0),
        ann_fn="",
        weights=[],
        set_static=False,
    )
    r5.validate()
    rules.append(r5)

    return rules


def build_rules_for_claim_native(
    claim: str,
    jurisdiction: str = "US-FED",
    use_conservative: bool = False,
    courts_cfg: Dict[str, Any] | None = None,
    burden_cfg: Dict[str, Any] | None = None,
    statutory_prefs: Dict[str, Any] | None = None,
) -> List[NativeRule]:
    """
    Compose the support rule for the claim and the derivation rules using native models only.

    Notes:
    - Burden of proof is enforced via the chosen annotation function (legal_burden_* or conservative).
    - Statutory interpretation preferences adjust clause weights (controlling/persuasive/contrary)
      without changing the burden aggregator, preserving threshold semantics.
    """
    courts_cfg = courts_cfg or {}
    burden_cfg = burden_cfg or {}
    statutory_prefs = statutory_prefs or {}

    # Burden-driven aggregator (optionally conservative)
    ann_fn = map_burden_to_ann_fn_name(claim, jurisdiction, burden_cfg)
    if use_conservative:
        ann_fn = "legal_conservative_min"

    # Base weights from courts config
    weights = default_clause_weights(courts_cfg)

    # Inline helpers for style-driven weight tuning
    def _style_from_prefs(juris: str, claim_id: str, prefs: Dict[str, Any], courts_cfg_local: Dict[str, Any]) -> str:
        """
        Resolve interpretation style by checking jurisdiction, then walking parent jurisdictions
        from courts_cfg.hierarchy, falling back to global default_style.
        """
        try:
            style_global = str(prefs.get("default_style", "") or "").strip()
            ov = prefs.get("style_overrides", {}) or {}

            # Build lineage: [juris] + ancestors (BFS order)
            lineage = [juris]
            try:
                hier = (courts_cfg_local or {}).get("hierarchy", {}) or {}
                seen = set([juris])
                frontier = [juris]
                while frontier:
                    cur = frontier.pop(0)
                    for parent in (hier.get(cur, []) or []):
                        if parent not in seen:
                            seen.add(parent)
                            lineage.append(parent)
                            frontier.append(parent)
            except Exception:
                pass

            for jcode in lineage:
                if jcode in ov:
                    jmap = ov[jcode] or {}
                    if claim_id in jmap:
                        return str(jmap[claim_id]).strip()
                    if "default" in jmap:
                        return str(jmap["default"]).strip()
            return style_global
        except Exception:
            return ""

    def _apply_style_to_weights(ws: List[float], style: str) -> List[float]:
        # ws = [w_controlling, w_persuasive, w_contrary]
        if not ws or len(ws) != 3:
            return ws
        w_ctrl, w_pers, w_contra = float(ws[0]), float(ws[1]), float(ws[2])
        if style == "textualism":
            # Downweight persuasive sources modestly
            w_pers *= 0.9
        elif style == "purposivism":
            # Upweight persuasive sources modestly
            w_pers *= 1.1
        elif style == "lenity":
            # Slightly upweight contrary to reflect defendant-favorable bias in penal ambiguity
            w_contra *= 1.1
        total = max(w_ctrl + w_pers + w_contra, 1e-9)
        return [w_ctrl / total, w_pers / total, w_contra / total]

    # Adjust weights per statutory interpretation style (if configured)
    style = _style_from_prefs(jurisdiction, claim, statutory_prefs, courts_cfg)
    if style:
        weights = _apply_style_to_weights(weights, style)

    rules: List[NativeRule] = []
    rules.append(build_support_rule_native(claim=claim, ann_fn_name=ann_fn, weights=weights))
    rules.extend(build_derivation_rules_native())
    # Apply jurisdiction-aware rule selection with explicit overrides (local > parent > federal)
    rules = filter_rules_by_jurisdiction(rules, courts_cfg, jurisdiction)
    return rules


__all__ = [
    "map_burden_to_ann_fn_name",
    "default_clause_weights",
    "compute_jurisdiction_lineage",
    "filter_rules_by_jurisdiction",
    "build_support_rule_native",
    "build_derivation_rules_native",
    "build_rules_for_claim_native",
]