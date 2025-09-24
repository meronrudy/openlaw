import os
import pytest

# Integration parity test harness
# Skips gracefully if the PyReason legal rule catalog or heavy deps are unavailable.

def _legal_rules_available():
    try:
        import core.adapters.pyreason_bridge  # noqa: F401
        # The bridge references core.rules.legal_rules; ensure it is importable
        import importlib
        importlib.import_module("core.rules.legal_rules")
        return True
    except Exception:
        return False


@pytest.mark.skipif(not _legal_rules_available(), reason="Legal rules or PyReason env not available")
def test_dual_engine_parity_on_sample_graph():
    # Enable native fact emission for parity
    os.environ["NATIVE_ENGINE_EMIT_FACTS"] = "1"
    # Ensure we keep PyReason as baseline runner for the bridge call path
    os.environ["LEGAL_ENGINE_IMPL"] = "pyreason"

    from core.native.validator import DualEngineValidator

    v = DualEngineValidator()
    # Use a small bundled graph; adjust path if your legal corpus is elsewhere
    graph_path = "pyreason/tests/friends_graph.graphml"
    report = v.validate_graphml(
        graphml_path=graph_path,
        claim="breach_of_contract",
        jurisdiction="US-CA",
        reporters_cfg_path=None,
        courts_cfg_path=None,
        burden_cfg_path=None,
        redaction_cfg_path=None,
        tmax=1,
        verbose=False,
    )
    assert isinstance(report, dict)
    # This assertion enforces exact equality parity per acceptance criteria
    assert report.get("match") is True, f"Parity mismatch: {report}"