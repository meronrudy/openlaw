#!/usr/bin/env python3
"""
Freeze PyReason outputs into a golden corpus for parity validation.

Usage:
  python scripts/golden/freeze_pyreason_outputs.py \
      --graph pyreason/tests/friends_graph.graphml \
      --claim breach_of_contract \
      --jurisdiction US-CA \
      --reporters config/normalize/reporters.yml \
      --courts config/normalize/courts.yml \
      --burden config/policy/burden.yml \
      --redaction config/compliance/redaction_rules.yml \
      --out-dir golden/snapshots

Emits a timestamped JSON with structure:
{
  "meta": {
    "graphml_path": "...",
    "claim": "...",
    "jurisdiction": "...",
    "tmax": 1,
    "generated_at": "UTC timestamp",
    "pyreason_version": "3.1.0"
  },
  "interpretation": { ... PyReason get_dict() ... }
}
"""

from __future__ import annotations
import argparse
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

# Bridge path (PyReason engine)
from core.adapters.pyreason_bridge import PyReasonLegalBridge


def run_freeze(
    graphml_path: str,
    claim: str,
    jurisdiction: str,
    reporters_cfg_path: Optional[str],
    courts_cfg_path: Optional[str],
    burden_cfg_path: Optional[str],
    redaction_cfg_path: Optional[str],
    out_dir: str,
    tmax: int = 1,
    convergence_threshold: float = -1.0,
    convergence_bound_threshold: float = -1.0,
    verbose: bool = False,
) -> str:
    """
    Execute PyReason via the bridge and dump interpretation to a golden JSON file.

    Returns:
        The output file path written.
    """
    bridge = PyReasonLegalBridge(
        reporters_cfg_path=reporters_cfg_path,
        courts_cfg_path=courts_cfg_path,
        burden_cfg_path=burden_cfg_path,
        redaction_cfg_path=redaction_cfg_path,
        privacy_defaults=True,
    )

    graph = bridge.load_graphml(graphml_path, reverse=False)
    facts_node, facts_edge, spec_node_labels, spec_edge_labels = bridge.parse_graph_attributes(static_facts=True)
    pr_rules = bridge.build_rules_for_claim(
        claim=claim,
        jurisdiction=jurisdiction,
        use_conservative=False,
    )

    interp = bridge.run_reasoning(
        graph=graph,
        facts_node=facts_node,
        facts_edge=facts_edge,
        rules=pr_rules,
        tmax=tmax,
        convergence_threshold=convergence_threshold,
        convergence_bound_threshold=convergence_bound_threshold,
        verbose=verbose,
    )

    data = interp.get_dict()

    out_dir_path = Path(out_dir)
    out_dir_path.mkdir(parents=True, exist_ok=True)
    ts = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
    base = Path(graphml_path).stem
    out_file = out_dir_path / f"{base}__{claim}__{jurisdiction}__t{tmax}__{ts}.json"

    # Compose golden record with metadata
    record = {
        "meta": {
            "graphml_path": str(graphml_path),
            "claim": str(claim),
            "jurisdiction": str(jurisdiction),
            "tmax": int(tmax),
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "pyreason_version": "3.1.0",
        },
        "interpretation": data,
    }

    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(record, f, indent=2, default=str, sort_keys=True)

    return str(out_file)


def main():
    p = argparse.ArgumentParser(description="Freeze PyReason outputs into golden corpus JSON")
    p.add_argument("--graph", required=True, help="Path to GraphML file")
    p.add_argument("--claim", required=True, help="Claim identifier (e.g., breach_of_contract)")
    p.add_argument("--jurisdiction", default="US-FED", help="Jurisdiction code (default: US-FED)")
    p.add_argument("--reporters", dest="reporters_cfg_path", default=None, help="Reporters config YAML")
    p.add_argument("--courts", dest="courts_cfg_path", default=None, help="Courts config YAML")
    p.add_argument("--burden", dest="burden_cfg_path", default=None, help="Burden policy YAML")
    p.add_argument("--redaction", dest="redaction_cfg_path", default=None, help="Redaction rules YAML")
    p.add_argument("--out-dir", required=True, help="Directory to write golden outputs")
    p.add_argument("--tmax", type=int, default=1, help="Max timesteps (default: 1)")
    p.add_argument("--conv-threshold", type=float, default=-1.0, help="Convergence threshold (delta_interpretation)")
    p.add_argument("--conv-bound-threshold", type=float, default=-1.0, help="Convergence bound threshold (delta_bound)")
    p.add_argument("--verbose", action="store_true", help="Verbose engine logs")
    args = p.parse_args()

    out_path = run_freeze(
        graphml_path=args.graph,
        claim=args.claim,
        jurisdiction=args.jurisdiction,
        reporters_cfg_path=args.reporters_cfg_path,
        courts_cfg_path=args.courts_cfg_path,
        burden_cfg_path=args.burden_cfg_path,
        redaction_cfg_path=args.redaction_cfg_path,
        out_dir=args.out_dir,
        tmax=args.tmax,
        convergence_threshold=args.conv_threshold,
        convergence_bound_threshold=args.conv_bound_threshold,
        verbose=args.verbose,
    )
    print(f"[golden-freeze] Wrote: {out_path}")


if __name__ == "__main__":
    main()