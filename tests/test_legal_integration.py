import networkx as nx

from core.adapters.pyreason_bridge import PyReasonLegalBridge


def test_end_to_end_support_rule_with_controlling_precedent():
    # Build a tiny legal graph in-memory:
    # Case A cites Case B; same issue; B is controlling & precedential.
    g = nx.DiGraph()
    g.add_node("A", case_id="A")
    g.add_node("B", case_id="B", precedential=1.0)

    # Edge A->B with attributes expected by derivation rules
    g.add_edge(
        "A",
        "B",
        cites=1.0,
        same_issue=1.0,
        controlling_relation=1.0,
    )

    bridge = PyReasonLegalBridge(
        reporters_cfg_path="config/normalize/reporters.yml",
        courts_cfg_path="config/normalize/courts.yml",
        burden_cfg_path="config/policy/burden.yml",
        redaction_cfg_path="config/compliance/redaction_rules.yml",
        privacy_defaults=True,  # atom_trace=False, save_graph_attributes_to_rule_trace=False
    )

    # Load the in-memory graph and extract attribute facts
    graph = bridge.load_graph(g, reverse=False)
    facts_node, facts_edge, spec_node_labels, spec_edge_labels = bridge.parse_graph_attributes(static_facts=True)

    # Build rules for a civil claim (default: preponderance 0.51)
    rules = bridge.build_rules_for_claim(claim="breach_of_contract", jurisdiction="US-CA")

    # Run reasoning
    interp = bridge.run_reasoning(
        graph=graph,
        facts_node=facts_node,
        facts_edge=facts_edge,
        rules=rules,
        tmax=1,
        verbose=False,
    )
    results = interp.get_dict()

    # Verify that A has support_for_breach_of_contract with lower bound >= 0.51 at some timestep
    label_key = "support_for_breach_of_contract"
    found = False
    for t, world in results.items():
        if "A" in world and label_key in world["A"]:
            lo, up = world["A"][label_key]
            assert lo >= 0.51 - 1e-9
            assert 0.0 <= lo <= 1.0
            assert 0.0 <= up <= 1.0
            found = True
            break

    assert found, "Expected support_for_breach_of_contract on node A derived from controlling precedent"