import os

from core.adapters.native_bridge import NativeLegalBridge


def _run_graph(graph_path: str):
    bridge = NativeLegalBridge(
        courts_cfg_path="config/courts.yaml",
        statutory_prefs_cfg_path="config/statutory_prefs.yaml",
        precedent_weights_cfg_path="config/precedent_weights.yaml",
        privacy_defaults=True,
    )
    g = bridge.load_graphml(graph_path, reverse=False)
    facts_node, facts_edge, _, _ = bridge.parse_graph_attributes(static_facts=True)

    # Build and run for breach_of_contract under US-CA
    rules = bridge.build_rules_for_claim(
        claim="breach_of_contract",
        jurisdiction="US-CA",
        use_conservative=False,
    )
    interp = bridge.run_reasoning(g, facts_node, facts_edge, rules, tmax=1, verbose=False)

    # Use privacy/export enforcement (default_profile: facts only)
    out = bridge.export_interpretation(interp, profile="default_profile")
    assert isinstance(out, dict)
    assert "facts" in out
    assert "supports" in out
    assert "trace" in out
    # default_profile omits supports/trace content
    assert out["supports"] == {}
    assert out["trace"] == []
    # facts structure validation
    facts = out["facts"]
    assert isinstance(facts, dict)
    for k, v in facts.items():
        assert isinstance(k, str)
        assert isinstance(v, (list, tuple)) and len(v) == 2
        assert isinstance(v[0], float) and isinstance(v[1], float)


def test_friends_graph_breach_us_ca():
    _run_graph("examples/graphs/friends_graph.graphml")


def test_group_chat_graph_breach_us_ca():
    _run_graph("examples/graphs/group_chat_graph.graphml")