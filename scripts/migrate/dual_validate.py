#!/usr/bin/env python3
"""
Dual Engine Parity Validator (Exact Equality)

Runs PyReason (via bridge) and the Native Reasoner (via facade) on the same inputs
and validates exact equality for both derived fact keys and probability intervals.

Usage:
    python scripts/migrate/dual_validate.py \
        --graph examples/legal/min_case_graph.graphml \
        --claim breach_of_contract \
        --jurisdiction US-CA \
        --tmax 1 \
        --emit-native-facts

Exit codes:
    0 = parity match (exact)
    2 = mismatch detected
    3 = execution error
"""

from __future__ import annotations
import argparse
import json
import os
import sys
from typing import Any, Dict

# Parity validator
from core.native.validator import DualEngineValidator


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Dual-run parity validator for PyReason vs Native Reasoner (exact equality)."
    )
    parser.add_argument("--graph", required=True, help="Path to GraphML file")
    parser.add_argument("--claim", required=True, help="Legal claim identifier (e.g., breach_of_contract)")
    parser.add_argument("--jurisdiction", default="US-FED", help="Jurisdiction code (default: US-FED)")
    parser.add_argument("--reporters", default="config/normalize/reporters.yml", help="Reporters config path")
    parser.add_argument("--courts", default="config/normalize/courts.yml", help="Courts config path")
    parser.add_argument("--burden", default="config/policy/burden.yml", help="Burden policy config path")
    parser.add_argument("--redaction", default="config/compliance/redaction_rules.yml", help="Redaction rules config path")
    parser.add_argument("--tmax", type=int, default=1, help="Max timesteps (default: 1; -1 for until convergence)")
    parser.add_argument("--convergence-threshold", type=float, default=-1.0, help="Max changed facts allowed for convergence (default: -1 disabled)")
    parser.add_argument("--convergence-bound-threshold", type=float, default=-1.0, help="Max interval delta allowed for convergence (default: -1 disabled)")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose engine output")
    parser.add_argument(
        "--emit-native-facts",
        action="store_true",
        help="Emit native facts to interpretation for non-empty parity checks (default: disabled -> empty facts for both).",
    )

    args = parser.parse_args()

    # Control native emission via environment (read by the native facade)
    if args.emit_native_facts:
        os.environ["NATIVE_ENGINE_EMIT_FACTS"] = "1"

    try:
        validator = DualEngineValidator()
        report: Dict[str, Any] = validator.validate_graphml(
            graphml_path=args.graph,
            claim=args.claim,
            jurisdiction=args.jurisdiction,
            reporters_cfg_path=args.reporters,
            courts_cfg_path=args.courts,
            burden_cfg_path=args.burden,
            redaction_cfg_path=args.redaction,
            use_conservative=False,
            tmax=args.tmax,
            convergence_threshold=args.convergence_threshold,
            convergence_bound_threshold=args.convergence_bound_threshold,
            verbose=args.verbose,
        )
        print(json.dumps(report, indent=2, sort_keys=True, default=str))
        if report.get("match") is True:
            return 0
        return 2
    except KeyboardInterrupt:
        print("\nCancelled by user.", file=sys.stderr)
        return 3
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 3


if __name__ == "__main__":
    sys.exit(main())