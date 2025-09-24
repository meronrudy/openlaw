import os
import json
import glob
import pytest

def _golden_snapshots():
    return sorted(glob.glob("golden/snapshots/*.json"))

def _flatten_pr_interpretation(pr_dict):
    """
    Flatten PyReason get_dict() structure at the last timestep to a statement->(l,u) map.
    pr_dict is the nested dict from the golden snapshot under key "interpretation".
    """
    if not isinstance(pr_dict, dict) or not pr_dict:
        return {}
    # The structure is {time -> {component -> {label: (l,u)}}}
    # keys for time may be ints or strings; pick max
    times = []
    for k in pr_dict.keys():
        try:
            times.append(int(k))
        except Exception:
            # already int?
            if isinstance(k, int):
                times.append(k)
    if not times:
        return {}
    t = max(times)
    layer = pr_dict.get(t, pr_dict.get(str(t), {}))
    facts = {}
    for comp, labels in (layer or {}).items():
        # comp is either node_id or a 2-tuple (u,v)
        if isinstance(comp, (list, tuple)) and len(comp) == 2:
            u, v = str(comp[0]), str(comp[1])
            for lbl, lu in (labels or {}).items():
                facts[f"{str(lbl)}({u},{v})"] = (float(lu[0]), float(lu[1]))
        else:
            nid = str(comp)
            for lbl, lu in (labels or {}).items():
                facts[f"{str(lbl)}({nid})"] = (float(lu[0]), float(lu[1]))
    return facts

def _rules_available():
    try:
        import core.adapters.pyreason_bridge  # noqa: F401
        return True
    except Exception:
        return False

@pytest.mark.skipif(not _rules_available(), reason="PyReason bridge not available; skipping golden parity")
def test_golden_snapshots_parity_with_native():
    """
    Compares Native engine output to frozen PyReason golden snapshots.

    Requires:
      - LEGAL_ENGINE_IMPL (bridge default 'pyreason' is fine for rule building)
      - NATIVE_ENGINE_EMIT_FACTS=1 to emit native facts for comparison
    """
    snaps = _golden_snapshots()
    if not snaps:
        # Auto-freeze a baseline corpus using the bundled PyReason and bridge
        from scripts.golden.freeze_pyreason_outputs import run_freeze
        seeds = [
            ("pyreason/tests/friends_graph.graphml", "breach_of_contract", "US-CA"),
            ("pyreason/tests/group_chat_graph.graphml", "breach_of_contract", "US-CA"),
        ]
        gen = []
        for gpath, claim, juris in seeds:
            try:
                out_path = run_freeze(
                    graphml_path=gpath,
                    claim=claim,
                    jurisdiction=juris,
                    reporters_cfg_path=None,
                    courts_cfg_path=None,
                    burden_cfg_path=None,
                    redaction_cfg_path=None,
                    out_dir="golden/snapshots",
                    tmax=1,
                    convergence_threshold=-1.0,
                    convergence_bound_threshold=-1.0,
                    verbose=False,
                )
                gen.append(out_path)
            except Exception as e:
                print(f"[golden-parity] Freeze failed for {gpath}: {e}")
        snaps = gen

    # Ensure native emits facts for parity
    os.environ["NATIVE_ENGINE_EMIT_FACTS"] = "1"

    from core.adapters.pyreason_bridge import PyReasonLegalBridge
    from core.native.facade import NativeLegalFacade

    native = NativeLegalFacade(privacy_defaults=True)

    effective = 0
    for snap in snaps:
        with open(snap, "r", encoding="utf-8") as f:
            record = json.load(f)
        meta = record.get("meta", {})
        interp_nested = record.get("interpretation", {})

        # Allow opt-out per snapshot via meta.skip
        if meta.get("skip") is True:
            continue

        expected = _flatten_pr_interpretation(interp_nested)
        # Skip placeholder/empty golden outputs (e.g., sample templates)
        if not expected:
            # Optional: log to stdout so CI shows which were skipped
            print(f"[golden-parity] Skipping empty snapshot: {snap}")
            continue

        graph_path = meta.get("graphml_path")
        claim = meta.get("claim", "breach_of_contract")
        jurisdiction = meta.get("jurisdiction", "US-CA")
        tmax = int(meta.get("tmax", 1))

        # Build inputs via bridge (rules and facts)
        bridge = PyReasonLegalBridge(
            reporters_cfg_path=None,
            courts_cfg_path=None,
            burden_cfg_path=None,
            redaction_cfg_path=None,
            privacy_defaults=True,
            engine_impl="pyreason",
        )
        graph = bridge.load_graphml(graph_path, reverse=False)
        facts_node, facts_edge, _, _ = bridge.parse_graph_attributes(static_facts=True)
        pr_rules = bridge.build_rules_for_claim(
            claim=claim,
            jurisdiction=jurisdiction,
            use_conservative=False,
        )

        # Run native
        interp = native.run_reasoning(
            graph=graph,
            facts_node=facts_node,
            facts_edge=facts_edge,
            rules=pr_rules,
            tmax=tmax,
            verbose=False,
        )
        actual = interp.get_dict().get("facts", {})

        # Exact equality of keys and tuples
        assert set(actual.keys()) == set(expected.keys()), f"Facts keys mismatch for snapshot {snap}"
        for k in expected.keys():
            assert tuple(actual[k]) == tuple(expected[k]), f"Interval mismatch for {k} in snapshot {snap}"
        effective += 1

    if effective == 0:
        pytest.skip("No non-empty golden snapshots available to validate")