import numpy as np

from core.rules.legal_rules import (
    map_burden_to_fn_name,
    default_clause_weights,
    build_support_rule,
)


def test_map_burden_to_fn_name_overrides_and_defaults():
    burden_cfg = {
        "DEFAULT_BURDEN": 0.51,
        "BURDEN_OVERRIDES": {
            "US-FED": {"criminal": 0.90},
            "US-CA": {"punitive_damages": 0.75},
            "GLOBAL": {"fraud": 0.75},
        },
    }

    # Exact jurisdiction + claim overrides
    assert map_burden_to_fn_name("punitive_damages", "US-CA", burden_cfg) == "legal_burden_clear_075"
    assert map_burden_to_fn_name("criminal", "US-FED", burden_cfg) == "legal_burden_criminal_090"

    # Global claim override applies if jurisdiction override missing that claim
    assert map_burden_to_fn_name("fraud", "US-NY", burden_cfg) == "legal_burden_clear_075"

    # Default civil burden for unmatched claim/jurisdiction
    assert map_burden_to_fn_name("breach_of_contract", "US-TX", burden_cfg) == "legal_burden_civil_051"


def test_default_clause_weights_and_support_rule_build():
    courts_cfg = {"weights": {"controlling": 0.6, "persuasive": 0.3, "contrary": 0.1}}
    w = default_clause_weights(courts_cfg)
    assert len(w) == 3
    assert abs(sum(w) - 1.0) < 1e-9
    # Check ordering roughly stable
    assert w[0] > w[1] > w[2]

    # Build a rule with correct weights vector length (3 clauses)
    rule = build_support_rule(claim="breach_of_contract", ann_fn_name="legal_burden_civil_051", weights=w)
    # The object must exist; parse_rule executed inside and should not raise
    assert rule is not None


def test_support_rule_weight_validation():
    courts_cfg = {"weights": {"controlling": 0.6, "persuasive": 0.3, "contrary": 0.1}}
    w = default_clause_weights(courts_cfg)
    # Wrong length triggers parser validation error; provide 2 instead of 3
    bad_w = np.array(w[:2], dtype=np.float64)

    try:
        build_support_rule(claim="breach_of_contract", ann_fn_name="legal_burden_civil_051", weights=bad_w)
        raised = False
    except Exception:
        raised = True

    assert raised, "Expected an exception when weights length does not match number of clauses"