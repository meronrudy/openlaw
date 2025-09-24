#!/usr/bin/env python3
# pylint: disable=import-error
"""
Native Engine Performance Benchmark (PyReason-free)

Measures:
- Latency distribution (avg, p50, p95) over multiple runs
- Peak memory usage
- Optional emission of interpretation for inspection

Examples:
  # Warm up and run 20 iterations with JIT enabled (default)
  python scripts/benchmarks/perf_benchmark.py --iterations 20 --warmup 3

  # Disable Numba JIT for latency comparison
  python scripts/benchmarks/perf_benchmark.py --disable-numba-jit 1 --iterations 10

  # Emit interpretation JSON
  python scripts/benchmarks/perf_benchmark.py --emit-interpretation 1 --iterations 1 --quiet 1
"""

import argparse
import json
import os
import sys
import time
from statistics import mean
from typing import Any, Dict, Tuple

import networkx as nx
import numpy as np

# Optional memory profiler (in requirements.txt)
try:
    from memory_profiler import memory_usage  # type: ignore
    HAS_MEMPROF = True
except Exception:
    HAS_MEMPROF = False

# Respect CLI JIT setting early
parser = argparse.ArgumentParser()
parser.add_argument("--iterations", type=int, default=20)
parser.add_argument("--warmup", type=int, default=3)
parser.add_argument("--disable-numba-jit", type=int, choices=[0, 1], default=0)
parser.add_argument("--tmax", type=int, default=1)
parser.add_argument("--quiet", type=int, choices=[0, 1], default=0)
parser.add_argument("--emit-interpretation", type=int, choices=[0, 1], default=0)
parser.add_argument("--jurisdiction", type=str, default="US-CA")
parser.add_argument("--claim", type=str, default="breach_of_contract")
args, _ = parser.parse_known_args()

if args.disable_numba_jit:
    os.environ["NUMBA_DISABLE_JIT"] = "1"

try:
    import numba  # type: ignore  # noqa: E402
except Exception:
    numba = None  # type: ignore

# In-process toggle as well (best effort; env var is primary)
if numba is not None:
    if args.disable_numba_jit:
        numba.config.DISABLE_JIT = 1  # type: ignore
    else:
        numba.config.DISABLE_JIT = 0  # type: ignore

from core.adapters.native_bridge import NativeLegalBridge  # noqa: E402


def make_min_graph() -> nx.DiGraph:
    g = nx.DiGraph()
    g.add_node("A", case_id="A")
    g.add_node("B", case_id="B", precedential=1.0)
    g.add_edge(
        "A",
        "B",
        cites=1.0,
        same_issue=1.0,
        controlling_relation=1.0,
    )
    return g


def to_jsonable_interpretation(interp_dict: Dict[Any, Dict[Any, Dict[str, Tuple[float, float]]]]) -> Dict[str, Dict[str, Dict[str, Tuple[float, float]]]]:
    """
    Convert interpretation dict (with tuple edge keys etc.) to JSON-serializable.
    """
    out: Dict[str, Dict[str, Dict[str, Tuple[float, float]]]] = {}
    for t, comp_map in interp_dict.items():
        tkey = str(t)
        out[tkey] = {}
        for comp, labels in comp_map.items():
            if isinstance(comp, tuple) and len(comp) == 2:
                ckey = f"{comp[0]}->{comp[1]}"
            else:
                ckey = str(comp)
            out[tkey][ckey] = {}
            for lbl, bounds in labels.items():
                out[tkey][ckey][str(lbl)] = (float(bounds[0]), float(bounds[1]))
    return out


def run_once(disable_jit: bool, tmax: int, jurisdiction: str, claim: str, emit_interpretation: bool):
    bridge = NativeLegalBridge(
        reporters_cfg_path="config/normalize/reporters.yml",
        courts_cfg_path="config/normalize/courts.yml",
        burden_cfg_path="config/policy/burden.yml",
        redaction_cfg_path="config/compliance/redaction_rules.yml",
        privacy_defaults=True,
    )

    graph = bridge.load_graph(make_min_graph(), reverse=False)
    facts_node, facts_edge, _, _ = bridge.parse_graph_attributes(static_facts=True)
    rules = bridge.build_rules_for_claim(claim=claim, jurisdiction=jurisdiction)

    start = time.perf_counter()
    interp = bridge.run_reasoning(
        graph=graph,
        facts_node=facts_node,
        facts_edge=facts_edge,
        rules=rules,
        tmax=tmax,
        verbose=False,
    )
    end = time.perf_counter()
    latency = end - start

    interp_json = None
    if emit_interpretation:
        interp_json = to_jsonable_interpretation(interp.get_dict())

    return latency, interp_json


def main():
    # Warmup runs
    for _ in range(max(args.warmup, 0)):
        _ = run_once(
            disable_jit=bool(args.disable_numba_jit),
            tmax=args.tmax,
            jurisdiction=args.jurisdiction,
            claim=args.claim,
            emit_interpretation=False,
        )

    # Timed runs with optional memory tracking
    latencies = []

    def _measure():
        lat, _ = run_once(
            disable_jit=bool(args.disable_numba_jit),
            tmax=args.tmax,
            jurisdiction=args.jurisdiction,
            claim=args.claim,
            emit_interpretation=bool(args.emit_interpretation),
        )
        latencies.append(lat)

    peak_mem = None
    if HAS_MEMPROF:
        # memory_usage returns a list; we track peak across iterations by executing runs in-process
        mem_samples = []
        for _ in range(args.iterations):
            if args.emit_interpretation:
                # When emitting interpretation, defer to direct call to obtain the JSON result
                lat, interp_json = run_once(
                    disable_jit=bool(args.disable_numba_jit),
                    tmax=args.tmax,
                    jurisdiction=args.jurisdiction,
                    claim=args.claim,
                    emit_interpretation=True,
                )
                latencies.append(lat)
                # store last result on stdout if requested
                last_interp_json = interp_json
            else:
                # use memory profiler wrapper
                ms = memory_usage((run_once, (bool(args.disable_numba_jit), args.tmax, args.jurisdiction, args.claim, False)), interval=0.05)
                mem_samples.extend(ms)
                # run once more to capture latency
                lat, _ = run_once(
                    disable_jit=bool(args.disable_numba_jit),
                    tmax=args.tmax,
                    jurisdiction=args.jurisdiction,
                    claim=args.claim,
                    emit_interpretation=False,
                )
                latencies.append(lat)
        if mem_samples:
            peak_mem = max(mem_samples)
    else:
        last_interp_json = None
        for _ in range(args.iterations):
            lat, interp_json = run_once(
                disable_jit=bool(args.disable_numba_jit),
                tmax=args.tmax,
                jurisdiction=args.jurisdiction,
                claim=args.claim,
                emit_interpretation=bool(args.emit_interpretation),
            )
            latencies.append(lat)
            last_interp_json = interp_json

    # Compute stats
    lat_array = np.array(latencies, dtype=np.float64)
    stats = {
        "iterations": int(args.iterations),
        "jit_disabled": bool(args.disable_numba_jit),
        "tmax": int(args.tmax),
        "avg_s": float(mean(latencies)),
        "p50_s": float(np.percentile(lat_array, 50)),
        "p95_s": float(np.percentile(lat_array, 95)),
        "peak_mem_mib": float(peak_mem) if peak_mem is not None else None,
    }

    out = {"stats": stats}
    if args.emit_interpretation:
        out["interpretation"] = last_interp_json

    if not args.quiet:
        print(json.dumps(out, indent=2, sort_keys=True))
    else:
        print(json.dumps(out, sort_keys=True))


if __name__ == "__main__":
    sys.exit(main())