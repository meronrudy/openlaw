"""
Native Rule Compiler

Translates external rule specifications into native rules usable by the
FixedPointEngine. During migration, provides a transitional adapter that can
compile PyReason Rule objects (pyreason.scripts.rules.rule.Rule) to NativeRule.

Goal: allow dual-run parity while progressively eliminating PyReason.
"""

from __future__ import annotations
import re
from typing import Any, List, Tuple

try:
    # Optional types when PyReason is present during migration
    from pyreason.scripts.numba_wrapper.numba_types.interval_type import closed as pr_closed  # noqa: F401
except Exception:
    pr_closed = None  # type: ignore

from .rules import NativeRule, Clause, ThresholdSpec, default_thresholds_for


def _extract_rule_pyreason(pr_rule_obj: Any) -> NativeRule:
    """
    Best-effort extraction from a PyReason Rule (pr_rule.rule), returning a NativeRule.

    Assumptions:
      - pr_rule is an instance of pyreason.scripts.rules.rule.Rule
      - pr_rule.rule is a numba-backed Rule object with .get_* methods
    """
    # Access the internal numba-backed Rule
    r = getattr(pr_rule_obj, "rule", pr_rule_obj)

    # Head info
    rule_name = getattr(r, "get_rule_name", None)
    rule_type = getattr(r, "get_rule_type", None)
    target = getattr(r, "get_target", None)
    head_vars = getattr(r, "get_head_variables", None)
    delta = getattr(r, "get_delta", None)
    clauses_get = getattr(r, "get_clauses", None)
    bnd_get = getattr(r, "get_bnd", None)
    thresholds_get = getattr(r, "get_thresholds", None)
    ann_fn_get = getattr(r, "get_annotation_function", None)
    weights_get = getattr(r, "get_weights", None)
    edges_get = getattr(r, "get_edges", None)
    static_get = getattr(r, "is_static", None) or getattr(r, "is_static_rule", None)

    # Resolve fields
    name_val = rule_name() if callable(rule_name) else str(getattr(r, "name", "rule"))
    type_val = rule_type() if callable(rule_type) else "node"
    target_lbl = target().get_value() if callable(target) else str(getattr(r, "target", ""))  # label proxy
    head_vars_val = list(head_vars()) if callable(head_vars) else list(getattr(r, "head_variables", []))
    delta_val = int(delta()) if callable(delta) else int(getattr(r, "delta", 0))

    # Clauses: list of tuples (ctype, label, subset(list[str]), interval, operator)
    clauses_val: List[Clause] = []
    if callable(clauses_get):
        for c in list(clauses_get()):
            ctype = str(c[0])
            clabel = c[1].get_value() if hasattr(c[1], "get_value") else str(c[1])
            cvars = list(c[2])
            ib = c[3]
            op = str(c[4])
            bound = (float(ib.lower), float(ib.upper))
            clauses_val.append(Clause(ctype=ctype, label=clabel, variables=cvars, bound=bound, operator=op))
    else:
        # Fallback
        clauses_val = []

    # Thresholds: list of tuples (quantifier, (mode, base), value)
    thresholds_val: List[ThresholdSpec] = []
    if callable(thresholds_get):
        for t in list(thresholds_get()):
            thresholds_val.append(ThresholdSpec(str(t[0]), (str(t[1][0]), str(t[1][1])), float(t[2])))
    else:
        thresholds_val = default_thresholds_for(clauses_val)

    # Head bound or annotation
    ann_fn_name = ann_fn_get() if callable(ann_fn_get) else ""
    head_bnd = bnd_get() if callable(bnd_get) else None
    head_bound_tuple: Tuple[float, float] | None = None
    if ann_fn_name:
        head_bound_tuple = None
    else:
        if head_bnd is not None:
            head_bound_tuple = (float(head_bnd.lower), float(head_bnd.upper))
        else:
            head_bound_tuple = (1.0, 1.0)

    # Weights
    weights_val: List[float] = []
    if callable(weights_get):
        w = list(weights_get())
        weights_val = [float(x) for x in w]

    # Edge inference metadata
    infer_edges = False
    infer_label = ""
    if callable(edges_get):
        eg = edges_get()
        # eg is a tuple (source_var, target_var, label_obj)
        if isinstance(eg, tuple) and len(eg) == 3:
            src, dst, lobj = eg
            infer_edges = bool(src) and bool(dst)
            try:
                infer_label = lobj.get_value()
            except Exception:
                infer_label = ""
    static_flag = bool(static_get()) if callable(static_get) else False

    nr = NativeRule(
        id=name_val or f"{type_val}_{target_lbl}",
        rule_type="node" if type_val == "node" else "edge",
        target_label=target_lbl,
        head_variables=head_vars_val,
        delta=delta_val,
        clauses=clauses_val,
        thresholds=thresholds_val,
        head_bound=head_bound_tuple if not ann_fn_name else None,
        ann_fn=str(ann_fn_name or ""),
        weights=weights_val,
        infer_edges=infer_edges,
        infer_edge_label=infer_label,
        set_static=static_flag,
        qualifiers={},  # bridge populates qualifiers on edges; here leave empty
    )
    nr.validate()
    return nr


def compile_pyreason_rules_to_native(pr_rules: List[Any]) -> List[NativeRule]:
    """
    Compile a list of PyReason rules to NativeRule list.
    Safe to call even if PyReason is not present: rules without accessible shape
    will be skipped.
    """
    out: List[NativeRule] = []
    for pr in pr_rules:
        try:
            out.append(_extract_rule_pyreason(pr))
        except Exception:
            # Skip if rule cannot be introspected; native engine can operate with
            # other inputs or remain stub during early migration.
            continue
    return out


# --------- Minimal textual rule parser ----------
def parse_text_rules(dsl: str) -> List[NativeRule]:
    """
    Minimal parser for a simple rule DSL.

    Syntax per line:
      rule <ID>: <HeadLabel>(X[,Y]) :- <Clause1>, <Clause2>, ... ; ann=<fn>; weights=w1,w2,...; delta=<int>; set_static=<bool>

    Clauses:
      <Label>(X)  or  <Label>(X,Y)

    Defaults:
      - Clause bound = [0,1]
      - Per-clause threshold = number/total >= 1.0
      - If ann is omitted, head bound defaults to [1,1]
    """
    rules: List[NativeRule] = []
    for raw in dsl.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if not line.lower().startswith("rule "):
            continue

        # Full form with body
        m = re.match(r"^rule\s+([A-Za-z0-9_]+)\s*:\s*([A-Za-z0-9_]+)\s*\(([^)]*)\)\s*:-\s*(.*)$", line, re.IGNORECASE)
        if not m:
            # Accept head-only rule (fact-like head)
            m2 = re.match(r"^rule\s+([A-Za-z0-9_]+)\s*:\s*([A-Za-z0-9_]+)\s*\(([^)]*)\)\s*$", line, re.IGNORECASE)
            if not m2:
                continue
            rid, head_label, head_args = m2.group(1), m2.group(2), m2.group(3).strip()
            head_vars = [a.strip() for a in head_args.split(",") if a.strip()]
            rtype = "edge" if len(head_vars) == 2 else "node"
            nr = NativeRule(
                id=rid,
                rule_type=rtype,
                target_label=head_label,
                head_variables=head_vars,
                clauses=[],
                thresholds=[],
                head_bound=(1.0, 1.0),
                ann_fn="",
                weights=[],
                set_static=False,
            )
            nr.validate()
            rules.append(nr)
            continue

        rid, head_label, head_args, tail = m.group(1), m.group(2), m.group(3).strip(), m.group(4).strip()
        head_vars = [a.strip() for a in head_args.split(",") if a.strip()]
        rtype = "edge" if len(head_vars) == 2 else "node"

        # Split tail into clauses and directives by ';'
        parts = [p.strip() for p in tail.split(";") if p.strip()]
        body_str = parts[0] if parts else ""
        directives = parts[1:] if len(parts) > 1 else []

        # Parse clauses
        clauses: List[Clause] = []
        for ctoken in [c.strip() for c in body_str.split(",") if c.strip()]:
            cm = re.match(r"^([A-Za-z0-9_]+)\s*\(([^)]*)\)\s*$", ctoken)
            if not cm:
                continue
            clabel, cargs = cm.group(1), cm.group(2)
            vars_ = [a.strip() for a in cargs.split(",") if a.strip()]
            ctype = "edge" if len(vars_) == 2 else "node"
            clauses.append(Clause(ctype=ctype, label=clabel, variables=vars_, bound=(0.0, 1.0)))

        thresholds = default_thresholds_for(clauses)

        # Directives
        ann_fn = ""
        weights: List[float] = []
        delta = 0
        set_static = False

        for d in directives:
            if d.lower().startswith("ann="):
                ann_fn = d.split("=", 1)[1].strip()
            elif d.lower().startswith("weights="):
                wstr = d.split("=", 1)[1]
                weights = [float(x.strip()) for x in wstr.split(",") if x.strip()]
            elif d.lower().startswith("delta="):
                try:
                    delta = int(d.split("=", 1)[1].strip())
                except Exception:
                    delta = 0
            elif d.lower().startswith("set_static="):
                val = d.split("=", 1)[1].strip().lower()
                set_static = val in ("1", "true", "yes")

        head_bound = None if ann_fn else (1.0, 1.0)

        nr = NativeRule(
            id=rid,
            rule_type=rtype,
            target_label=head_label,
            head_variables=head_vars,
            delta=delta,
            clauses=clauses,
            thresholds=thresholds,
            head_bound=head_bound,
            ann_fn=ann_fn,
            weights=weights,
            set_static=set_static,
        )
        nr.validate()
        rules.append(nr)

    return rules