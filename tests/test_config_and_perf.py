import json

from core.config.validator import validate_all
from scripts.benchmarks.perf_benchmark import run_once


def test_config_validator_ok():
    ok, errors = validate_all(
        burden_path="config/policy/burden.yml",
        courts_path="config/normalize/courts.yml",
        reporters_path="config/normalize/reporters.yml",
        redaction_path="config/compliance/redaction_rules.yml",
    )
    assert ok, f"Config validation failed: {errors}"


def test_perf_benchmark_smoke():
    # Run a single small reasoning pass and verify latency + interpretation shape.
    latency, interp_json = run_once(
        disable_jit=False,
        tmax=1,
        jurisdiction="US-CA",
        claim="breach_of_contract",
        emit_interpretation=True,
    )

    assert latency > 0.0
    # For a tiny graph, this should be well under a practical ceiling
    assert latency < 5.0, f"Unexpectedly high latency: {latency}s"

    # Validate interpretation JSON structure
    assert isinstance(interp_json, dict)
    # Find at least one timestep with at least one component entry
    assert any(isinstance(v, dict) and len(v) > 0 for v in interp_json.values())

    # Bounds sanity: some component should have a label mapping to (lower, upper)
    found_bounds = False
    for tmap in interp_json.values():
        for comp, labels in tmap.items():
            if isinstance(labels, dict):
                for _, bnd in labels.items():
                    if isinstance(bnd, (list, tuple)) and len(bnd) == 2:
                        lower, upper = bnd
                        assert 0.0 <= lower <= 1.0
                        assert 0.0 <= upper <= 1.0
                        found_bounds = True
                        break
            if found_bounds:
                break
        if found_bounds:
            break

    assert found_bounds, "Did not find any (lower, upper) bounds in interpretation output"

def test_perf_benchmark_jit_off_parity():
    """
    Parity smoke check with JIT disabled: ensures execution succeeds and returns an interpretation.
    """
    latency, interp_json = run_once(
        disable_jit=True,
        tmax=1,
        jurisdiction="US-CA",
        claim="breach_of_contract",
        emit_interpretation=True,
    )
    assert latency > 0.0
    assert isinstance(interp_json, dict)
    # At least one timestep with at least one component entry
    assert any(isinstance(v, dict) and len(v) > 0 for v in interp_json.values())