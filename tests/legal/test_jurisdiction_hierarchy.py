from core.rules_native.native_legal_builder import compute_jurisdiction_lineage


def test_lineage_simple_chain():
    courts_cfg = {
        "hierarchy": {
            "US-CA": ["US-FED"],
            "US-FED": ["INTL"],
            "INTL": []
        }
    }
    lineage = compute_jurisdiction_lineage(courts_cfg, "US-CA")
    # Expect BFS order starting from the jurisdiction down its parents, without duplicates
    assert lineage == ["US-CA", "US-FED", "INTL"]


def test_lineage_handles_missing_entries():
    # Missing jurisdiction in hierarchy should fall back to just the given jurisdiction
    courts_cfg = {"hierarchy": {"US-FED": []}}
    lineage = compute_jurisdiction_lineage(courts_cfg, "US-NY")
    assert lineage == ["US-NY"]


def test_lineage_no_cycles_and_no_duplicates():
    # Even with a cycle in config, function should avoid duplicates gracefully
    courts_cfg = {
        "hierarchy": {
            "A": ["B"],
            "B": ["A"],  # cycle
        }
    }
    lineage = compute_jurisdiction_lineage(courts_cfg, "A")
    # First element is the starting jurisdiction; second includes its parent; no infinite loop
    assert lineage[0] == "A"
    assert "B" in lineage
    # Ensure no duplicates
    assert len(lineage) == len(set(lineage))