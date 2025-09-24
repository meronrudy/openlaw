Native Engine Architecture and Integration Guide

Status: stable interfaces; parity-gated migration ready

1. Overview
The native engine provides open-world, graph-temporal inference semantics with probability intervals and legal-specific aggregators. It is designed for deterministic, explainable inference.

Key objectives:
- Deterministic fixed-point evaluation over graph-structured facts and rules
- Legal-aware aggregation (burdens of proof, conservative/min, precedent-weighted)
- Privacy defaults and minimal surface for compliance-friendly outputs

2. Module map
Engine and scheduling
- [FixedPointEngine](core/native/engine.py:1)
- [TemporalScheduler](core/native/temporal.py:1)

Grounding, indices, and facts
- [FactsIndex](core/native/facts.py:228)
- [NodeFacts](core/native/facts.py:37)
- [EdgeFacts](core/native/facts.py:132)
- Grounder (deterministic variable joins; index-aware) [module](core/native/grounder.py:1)
- Labels/adjacency indices [module](core/native/labels.py:1)

Semantics
- Probability intervals and algebra [module](core/native/intervals.py:1)
- Annotation functions (burdens, conservative, precedent-weighted) [module](core/native/annotate.py:1)

Rules and compilation
- Native rule model [module](core/native/rules.py:1)
- Minimal textual rule DSL parser [module](core/native/compiler.py:1)

Interpretation and validation
- Interpretation export (facts, supports, trace) [module](core/native/interpretation.py:1)
- Facade and exact-equality validator [module](core/native/facade.py:1)
- Dual engine validator [module](core/native/validator.py:1)


3. Data model
- Statement keys: "Label(nodeId)" and "Label(u,v)" normalized as strings for deterministic comparison and JSON export.
- Intervals: closed [l,u], clamped to [0,1]; invalid intersections collapse to [0,1].
  - [Interval](core/native/intervals.py:1)

- Facts indices:
  - Node facts: label → nodeId → Interval, with dense node indexing [NodeFacts](core/native/facts.py:37)
  - Edge facts: label → (u,v) → Interval, with dense edge indexing [EdgeFacts](core/native/facts.py:132)
  - Combined [FactsIndex](core/native/facts.py:228)


4. Deterministic engine loop
- Fixed-point agenda over t ∈ [0..tmax), or until convergence thresholds are met.
- Deterministic ordering:
  - Rules sorted by id
  - Nodes and edges sorted lexicographically
  - Assignment enumeration uses stable key encoding

- Update modes:
  - intersection: existing ∩ new
  - override: narrowest-interval-wins with deterministic tie-break

- Convergence policies:
  - delta_interpretation: bounded change in number of facts
  - delta_bound: max absolute bound delta ≤ threshold
  - perfect: continue to tmax

See [FixedPointEngine](core/native/engine.py:1)

5. Temporal scheduling
- Each proposed head (node/edge) schedules a [ScheduledUpdate](core/native/temporal.py:1) with:
  - statement key, interval, mode (intersection/override), set_static flag, source rule id
- TemporalScheduler groups updates per statement, merges deterministically (narrowest first), and applies static behavior.

6. Grounding and clause evaluation
- Index-aware grounding of variable assignments across node and edge clauses.
- Deterministic assignment order; stable traversal through adjacency maps.
- Clause evaluation computes threshold satisfaction and collects intervals per clause for aggregation.

Grounder (overview) [module](core/native/grounder.py:1)

7. Thresholds and aggregation
- Threshold semantics (modes: number/percent, bases: total/available).
  - [evaluate_threshold(...)](core/native/thresholds.py:1)

- Aggregators:
  - average, average_lower, maximum, minimum
  - legal_burden_civil_051, legal_burden_clear_075, legal_burden_criminal_090
  - legal_conservative_min
  - precedent_weighted (new; weights map clause classes)
  - Registry: [ANNOTATION_REGISTRY](core/native/annotate.py:226)

8. Interpretation format
- get_dict() → {"facts": {statement: (l,u)}, "supports": {...}, "trace": [...]}
- Facts-only by default (privacy-preserving); traces optional/minimal.
  - [Interpretation](core/native/interpretation.py:33)


10. Configuration
- Facts emission (native parity/testing):
  - NATIVE_ENGINE_EMIT_FACTS=1 to include facts in interpretation (default: 0) [facade](core/native/facade.py:57)
- Privacy defaults:
  - No atom traces; save_graph_attrs_to_rule_trace disabled by default [facade](core/native/facade.py:43)

11. CI and benchmarks
  - [native-parity-and-tests.yml](.github/workflows/native-parity-and-tests.yml:1)
- Benchmark entrypoint:
  - [native_bench.py](scripts/bench/native_bench.py:1)

12. Extensibility
- Add new legal aggregators in [annotate.py](core/native/annotate.py:1) and register by name.
- Extend threshold types in [thresholds.py](core/native/thresholds.py:1) as needed.
- Enable JIT selectively (shim is optional) [jit](core/native/jit.py:1)

