#!/usr/bin/env python3
"""
Mini end-to-end run for Native Legal integration (falls back to PyReason if native bridge unavailable).

- Loads the minimal example GraphML (examples/graphs/friends_graph.graphml)
- Builds legal rules for a sample civil claim
- Runs reasoning via the Native bridge by default (PyReason bridge as fallback)
- Prints the interpretation as a Python dict

Usage:
  python scripts/examples/mini_end_to_end.py --graph examples/graphs/friends_graph.graphml --jurisdiction US-CA --claim breach_of_contract
"""

import argparse
from typing import Optional

try:
    from core.adapters.native_bridge import NativeLegalBridge as Bridge
except Exception:
    from core.adapters.pyreason_bridge import PyReasonLegalBridge as Bridge


def run(graph_path: str, jurisdiction: str, claim: str, tmax: int = 1, verbose: bool = False):
    bridge = Bridge(
        reporters_cfg_path="config/normalize/reporters.yml",
        courts_cfg_path="config/normalize/courts.yml",
        burden_cfg_path="config/policy/burden.yml",
        redaction_cfg_path="config/compliance/redaction_rules.yml",
        statutory_prefs_cfg_path="config/statutory_prefs.yaml",
        precedent_weights_cfg_path="config/precedent_weights.yaml",
        privacy_defaults=True,  # atom_trace=False, save_graph_attributes_to_rule_trace=False
    )
    graph = bridge.load_graphml(graph_path, reverse=False)
    facts_node, facts_edge, _, _ = bridge.parse_graph_attributes(static_facts=True)
    rules = bridge.build_rules_for_claim(claim=claim, jurisdiction=jurisdiction)
    interp = bridge.run_reasoning(graph, facts_node, facts_edge, rules, tmax=tmax, verbose=verbose)
    results = interp.get_dict()
    print(results)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--graph", type=str, default="examples/graphs/friends_graph.graphml")
    parser.add_argument("--jurisdiction", type=str, default="US-CA")
    parser.add_argument("--claim", type=str, default="breach_of_contract")
    parser.add_argument("--tmax", type=int, default=1)
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()
    run(args.graph, args.jurisdiction, args.claim, tmax=args.tmax, verbose=args.verbose)


if __name__ == "__main__":
    main()