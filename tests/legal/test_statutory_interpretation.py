import math

from core.rules_native.native_legal_builder import build_rules_for_claim_native


def _get_support_rule(rules, claim: str):
    head = f"support_for_{claim}"
    for r in rules:
        if getattr(r, "target_label", "") == head:
            return r
    raise AssertionError("support rule not found")


def _approx_eq(a: float, b: float, tol: float = 1e-6) -> bool:
    return abs(a - b) <= tol


def test_textualism_downweights_persuasive():
    claim = "breach_of_contract"
    jurisdiction = "US-CA"
    courts_cfg = {
        "weights": {"controlling": 0.6, "persuasive": 0.3, "contrary": 0.1},
        # empty hierarchy for this test
        "hierarchy": {},
    }
    statutory_prefs = {
        "default_style": "textualism"
    }
    rules = build_rules_for_claim_native(
        claim=claim,
        jurisdiction=jurisdiction,
        courts_cfg=courts_cfg,
        burden_cfg={"DEFAULT_BURDEN": 0.51},
        statutory_prefs=statutory_prefs,
    )
    sr = _get_support_rule(rules, claim)
    w_ctrl, w_pers, w_contra = sr.weights
    # Textualism should modestly downweight persuasive (from 0.3)
    assert w_pers < 0.3
    # Normalization keeps sum near 1
    assert _approx_eq(w_ctrl + w_pers + w_contra, 1.0, 1e-6)
    # Controlling share typically increases after normalization
    assert w_ctrl > 0.6


def test_purposivism_upweights_persuasive():
    claim = "breach_of_contract"
    jurisdiction = "US-CA"
    courts_cfg = {
        "weights": {"controlling": 0.6, "persuasive": 0.3, "contrary": 0.1},
        "hierarchy": {},
    }
    statutory_prefs = {
        "default_style": "purposivism"
    }
    rules = build_rules_for_claim_native(
        claim=claim,
        jurisdiction=jurisdiction,
        courts_cfg=courts_cfg,
        burden_cfg={"DEFAULT_BURDEN": 0.51},
        statutory_prefs=statutory_prefs,
    )
    sr = _get_support_rule(rules, claim)
    w_ctrl, w_pers, w_contra = sr.weights
    # Purposivism should modestly upweight persuasive (from 0.3)
    assert w_pers > 0.3
    assert _approx_eq(w_ctrl + w_pers + w_contra, 1.0, 1e-6)
    # Controlling share typically decreases slightly after normalization
    assert w_ctrl < 0.6


def test_lenity_upweights_contrary():
    claim = "criminal_statute"
    jurisdiction = "US-FED"
    courts_cfg = {
        "weights": {"controlling": 0.6, "persuasive": 0.3, "contrary": 0.1},
        "hierarchy": {},
    }
    statutory_prefs = {
        "default_style": "lenity"
    }
    rules = build_rules_for_claim_native(
        claim=claim,
        jurisdiction=jurisdiction,
        courts_cfg=courts_cfg,
        burden_cfg={"DEFAULT_BURDEN": 0.90},
        statutory_prefs=statutory_prefs,
    )
    sr = _get_support_rule(rules, claim)
    w_ctrl, w_pers, w_contra = sr.weights
    # Lenity should slightly upweight contrary (from 0.1)
    assert w_contra > 0.1
    assert _approx_eq(w_ctrl + w_pers + w_contra, 1.0, 1e-6)


def test_style_fallback_to_parent_in_hierarchy():
    """
    If a jurisdiction has no explicit style override, it should fall back to parent in courts_cfg.hierarchy.
    """
    claim = "breach_of_contract"
    jurisdiction = "US-CA"
    courts_cfg = {
        "weights": {"controlling": 0.6, "persuasive": 0.3, "contrary": 0.1},
        "hierarchy": {
            "US-CA": ["US-FED"],
            "US-FED": []
        },
    }
    statutory_prefs = {
        "default_style": "textualism",  # global default
        "style_overrides": {
            # No override for US-CA, but parent has default purposivism
            "US-FED": {
                "default": "purposivism"
            }
        }
    }
    rules = build_rules_for_claim_native(
        claim=claim,
        jurisdiction=jurisdiction,
        courts_cfg=courts_cfg,
        burden_cfg={"DEFAULT_BURDEN": 0.51},
        statutory_prefs=statutory_prefs,
    )
    sr = _get_support_rule(rules, claim)
    w_ctrl, w_pers, w_contra = sr.weights
    # Expect purposivism effect via parent fallback: persuasive > baseline 0.3
    assert w_pers > 0.3
    assert _approx_eq(w_ctrl + w_pers + w_contra, 1.0, 1e-6)