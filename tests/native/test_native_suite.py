import pytest

from core.native.thresholds import Threshold, evaluate_threshold
from core.native.annotate import (
    average,
    maximum,
    minimum,
    legal_burden_civil_051,
    legal_burden_clear_075,
    legal_burden_criminal_090,
    legal_conservative_min,
)
from core.native.intervals import closed, Interval
from core.native.compiler import parse_text_rules
from core.native.interpretation import Interpretation


def _mk_ann_matrix(vals):
    # helper: convert list of (l,u) to annotations = [[Interval]]
    return [[closed(l, u)] for (l, u) in vals]


# ------------------------------
# Thresholds
# ------------------------------

def test_thresholds_number_total():
    thr = Threshold("greater_equal", ("number", "total"), 2.0)
    # satisfied_count=2 of total=3 -> 2 >= 2 True
    assert evaluate_threshold(thr, satisfied_count=2, total_count=3, available_count=None) is True
    # satisfied_count=1 of total=3 -> 1 >= 2 False
    assert evaluate_threshold(thr, satisfied_count=1, total_count=3, available_count=None) is False

    thr_eq = Threshold("equal", ("number", "total"), 1.0)
    assert evaluate_threshold(thr_eq, satisfied_count=1, total_count=5, available_count=None) is True
    assert evaluate_threshold(thr_eq, satisfied_count=2, total_count=5, available_count=None) is False


def test_thresholds_percent_available():
    thr_pct = Threshold("greater", ("percent", "available"), 50.0)  # > 50%
    # available_count=4, satisfied=3 -> 75% > 50% -> True
    assert evaluate_threshold(thr_pct, satisfied_count=3, total_count=10, available_count=4) is True
    # available_count=4, satisfied=2 -> 50% > 50% -> False
    assert evaluate_threshold(thr_pct, satisfied_count=2, total_count=10, available_count=4) is False


# ------------------------------
# Aggregators
# ------------------------------

def test_annotate_average_max_min():
    anns = _mk_ann_matrix([(0.2, 0.7), (0.4, 0.9), (0.6, 0.8)])
    weights = [1.0, 1.0, 1.0]

    iv_avg = average(anns, weights)
    assert isinstance(iv_avg, Interval)
    # Lower ~ average of lowers (0.2+0.4+0.6)/3 = 0.4
    assert abs(iv_avg.lower - 0.4) < 1e-9
    # Upper ~ average of uppers (0.7+0.9+0.8)/3 = 0.8
    assert abs(iv_avg.upper - 0.8) < 1e-9

    iv_max = maximum(anns, weights)
    # Max of clause-weighted sums: with single intervals per clause, equals max(lowers) / max(uppers)
    assert abs(iv_max.lower - 0.6) < 1e-9
    assert abs(iv_max.upper - 0.9) < 1e-9

    iv_min = minimum(anns, weights)
    assert abs(iv_min.lower - 0.2) < 1e-9
    assert abs(iv_min.upper - 0.7) < 1e-9


def test_annotate_legal_burdens_and_conservative():
    anns = _mk_ann_matrix([(0.2, 0.9), (0.55, 0.95)])
    weights = [1.0, 1.0]

    iv_civil = legal_burden_civil_051(anns, weights)
    # lower must be at least 0.51
    assert iv_civil.lower >= 0.51
    assert 0.0 <= iv_civil.upper <= 1.0

    iv_clear = legal_burden_clear_075(anns, weights)
    assert iv_clear.lower >= 0.75

    iv_criminal = legal_burden_criminal_090(anns, weights)
    assert iv_criminal.lower >= 0.90

    iv_cons = legal_conservative_min(anns, weights)
    # Lower should be min of clause-weighted sums (with single items equals min lower)
    assert abs(iv_cons.lower - min(anns[0][0].lower, anns[1][0].lower)) < 1e-9
    # Upper should be average of sums (with single items equals average upper)
    avg_upper = (anns[0][0].upper + anns[1][0].upper) / 2.0
    assert abs(iv_cons.upper - avg_upper) < 1e-9


# ------------------------------
# Interpretation export
# ------------------------------

def test_interpretation_export_and_json():
    interp = Interpretation()
    interp.set_fact("foo(A)", closed(0.3, 0.8))
    interp.set_fact("bar(A,B)", closed(0.5, 0.9))

    d = interp.get_dict()
    assert "facts" in d and "supports" in d and "trace" in d
    assert d["facts"]["foo(A)"] == (0.3, 0.8)
    assert d["facts"]["bar(A,B)"] == (0.5, 0.9)

    j = interp.to_json(indent=0)
    assert '"foo(A)": [0.3, 0.8]' in j or '"foo(A)": [0.3, 0.8]' in j or '"foo(A)": [0.3, 0.8' in j  # robust check

    jl = interp.to_jsonl()
    lines = jl.splitlines()
    assert any('"statement": "foo(A)"' in line for line in lines)
    assert any('"statement": "bar(A,B)"' in line for line in lines)


# ------------------------------
# Compiler parsing
# ------------------------------

def test_compiler_parse_text_rules_basic():
    dsl = "rule R1: head(X) :- p(X), q(X); ann=average; weights=1,1; delta=1; set_static=true"
    rules = parse_text_rules(dsl)
    assert len(rules) == 1
    r = rules[0]
    assert r.id == "R1"
    assert r.rule_type == "node"
    assert r.target_label == "head"
    assert r.head_variables == ["X"]
    assert len(r.clauses) == 2
    assert r.ann_fn == "average"
    assert r.weights == [1.0, 1.0]
    assert r.delta == 1
    assert r.set_static is True


def test_compiler_parse_text_rules_invalid_weights():
    # ann present but only one weight for two clauses -> should raise via validate()
    dsl = "rule R2: head(X) :- p(X), q(X); ann=average; weights=1"
    with pytest.raises(ValueError):
        parse_text_rules(dsl)