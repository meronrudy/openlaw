#!/usr/bin/env python3
"""
Native Engine Micro-benchmark

Measures wall-clock latency for the native fixed-point engine on a given graph and rules.
Outputs P50/P95 and memory RSS (if psutil available).

Usage:
  python scripts/bench/native_bench.py \
    --graph pyreason/tests/friends_graph.graphml \
    --claim breach_of_contract \
    --jurisdiction US-CA \
    --runs 30 \
    --warmup 5 \
    --emit-facts

Notes:
- If --emit-facts is set, the native engine will emit facts (NATIVE_ENGINE_EMIT_FACTS=1).
- Engine selection for bridge is ignored here; we use the native facade directly.
"""

from __future__ import annotations
import argparse
import os
import statistics
import time
from typing import Optional

try:
    import psutil  # type: ignore
except Exception:
    psutil = None  # pragma: no cover

from core.adapters.native_bridge import NativeLegalBridge
from core.native.facade import NativeLegalFacade


def percentiles(values, p):
    if not values:
        return 0.0
    return statistics.quantiles(values, n=100)[p - 1] if 1 <= p <= 99 else sorted(values)[int((p / 100.0) * len(values))]


def run_once(graph_path: str, claim: str, jurisdiction: str, verbose: bool = False):
    # Use native bridge to build graph and native rules (PyReason-free)
    bridge = NativeLegalBridge(
        reporters_cfg_path=None,
        courts_cfg_path=None,
        burden_cfg_path=None,
        redaction_cfg_path=None,
        privacy_defaults=True,
    )
    graph = bridge.load_graphml(graph_path, reverse=False)
    facts_node, facts_edge, _, _ = bridge.parse_graph_attributes(static_facts=True)
    native_rules = bridge.build_rules_for_claim(
        claim=claim,
        jurisdiction=jurisdiction,
        use_conservative=False,
    )

    native = NativeLegalFacade(privacy_defaults=True)
    t0 = time.perf_counter()
    interp = native.run_reasoning(
        graph=graph,
        facts_node=facts_node,
        facts_edge=facts_edge,
        rules=native_rules,
        tmax=1,
        verbose=verbose,
    )
    t1 = time.perf_counter()
    # Prevent optimizing-away
    _ = interp.get_dict()
    return (t1 - t0) * 1000.0  # ms


def main():
    ap = argparse.ArgumentParser(description="Native Engine Micro-benchmark")
    ap.add_argument("--graph", required=True, help="Path to GraphML")
    ap.add_argument("--claim", required=True, help="Claim id (e.g., breach_of_contract)")
    ap.add_argument("--jurisdiction", default="US-FED", help="Jurisdiction code (default: US-FED)")
    ap.add_argument("--runs", type=int, default=30, help="Number of measured runs (default: 30)")
    ap.add_argument("--warmup", type=int, default=5, help="Warmup runs (default: 5)")
    ap.add_argument("--emit-facts", action="store_true", help="Enable native fact emission")
    ap.add_argument("--verbose", action="store_true", help="Verbose engine logs")
    args = ap.parse_args()

    if args.emit_facts:
        os.environ["NATIVE_ENGINE_EMIT_FACTS"] = "1"

    # Warmup
    for _ in range(max(0, args.warmup)):
        run_once(args.graph, args.claim, args.jurisdiction, verbose=False)

    # Measured
    latencies = []
    for _ in range(max(1, args.runs)):
        lat_ms = run_once(args.graph, args.claim, args.jurisdiction, verbose=False)
        latencies.append(lat_ms)

    latencies_sorted = sorted(latencies)
    p50 = statistics.median(latencies_sorted)
    p95_index = int(0.95 * (len(latencies_sorted) - 1))
    p95 = latencies_sorted[p95_index] if latencies_sorted else 0.0

    rss_mb = 0.0
    if psutil is not None:
        try:
            rss_mb = psutil.Process(os.getpid()).memory_info().rss / (1024.0 * 1024.0)
        except Exception:
            rss_mb = 0.0

    print("[native-bench] runs=%d warmup=%d" % (len(latencies), args.warmup))
    print("[native-bench] p50=%.2f ms  p95=%.2f ms  rss=%.1f MB" % (p50, p95, rss_mb))


if __name__ == "__main__":
    main()