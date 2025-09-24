# OpenLaw Legal Reasoning (Native Engine — Default)

This repository provides a production-ready, legal reasoning stack centered on a deterministic Native Engine. It includes a native adapter/bridge for legal workloads, a jurisdiction-aware rule builder, authority multipliers, a document-to-graph ingestion CLI, GraphML fixtures, configuration bundles, CI with coverage gating, and comprehensive docs.

What’s new
- Native-only default architecture:
  - Deterministic fixed-point engine with threshold semantics and aggregation registry
  - Privacy-aware interpretation exports with redaction
- Legal adapter and builder:
  - [NativeLegalBridge.__init__()](core/adapters/native_bridge.py:55) with strict config validation and privacy defaults
  - [build_rules_for_claim()](core/adapters/native_bridge.py:450) wires burden-of-proof, statutory styles, and authority multipliers
  - Canonical rule builder: [build_rules_for_claim_native()](core/rules_native/native_legal_builder.py:373)
- Authority multipliers (config-driven):
  - [_compute_authority_multipliers()](core/adapters/native_bridge.py:325) combines treatment modifiers, recency decay, jurisdiction alignment, and court-level weights
- Ingestion pipeline:
  - Document → GraphML via [doc_to_graph_auto()](nlp/doc_to_graph.py:180) or [doc_to_graph()](nlp/doc_to_graph.py:96)
  - CLI tool: [scripts/ingest/doc_to_graph_cli.py](scripts/ingest/doc_to_graph_cli.py:1)
- CI and quality gates:
  - Native unit/integration CI with coverage ≥ 80%: [.github/workflows/native-ci.yml](.github/workflows/native-ci.yml:1)
- Legal data compliance:
  - Privacy defaults and redaction profiles in exports, data handling guidance in [docs/LEGAL_DATA_COMPLIANCE.md](docs/LEGAL_DATA_COMPLIANCE.md)

Core implementation files
- Native adapter (default entrypoint): [core/adapters/native_bridge.py](core/adapters/native_bridge.py:1)
- Native legal rules builder (canonical): [core/rules_native/native_legal_builder.py](core/rules_native/native_legal_builder.py:1)
- Engine facade and engine:
  - [NativeLegalFacade.run_reasoning()](core/native/facade.py:75)
  - [FixedPointEngine.run()](core/native/engine.py:61)
- Aggregators and legal operators: [ANNOTATION_REGISTRY](core/native/annotate.py:285)
- Interpretation export (privacy-aware): [Interpretation.export()](core/native/interpretation.py:127)
- Graph utilities (GraphML + label extraction): [extract_specific_labels()](core/native/graph.py:101)
- NLP/doc ingestion:
  - [doc_to_graph_auto()](nlp/doc_to_graph.py:180), [doc_to_graph()](nlp/doc_to_graph.py:96)
  - CLI: [doc_to_graph_cli.py](scripts/ingest/doc_to_graph_cli.py:1)

1. Installation (Python 3.10 recommended)

```bash
python -m venv .venv
source .venv/bin/activate

# Core deps for native engine path
pip install -r requirements.txt
```

Optional (dev)
- Parity tools and heavy extras are not required; the project operates native-first.
- Add pytest-cov locally if you want coverage reports that match CI:
  - pip install pytest-cov

2. Configuration (Native)

Primary config files:
- Courts and default clause weights with optional hierarchy/overrides:
  - [config/courts.yaml](config/courts.yaml:1)
- Authority multipliers (recency, jurisdiction alignment, court levels, treatment modifiers):
  - [config/precedent_weights.yaml](config/precedent_weights.yaml:1)
- Statutory interpretation preferences (textualism, purposivism, lenity):
  - [config/statutory_prefs.yaml](config/statutory_prefs.yaml:1)
- Redaction rules for export profiles:
  - [config/compliance/redaction_rules.yml](config/compliance/redaction_rules.yml:1)

Bridge constructor (strict mode)
- [NativeLegalBridge.__init__()](core/adapters/native_bridge.py:55) validates all configs and can fail-fast:

```python
from core.adapters.native_bridge import NativeLegalBridge

bridge = NativeLegalBridge(
    courts_cfg_path="config/courts.yaml",
    precedent_weights_cfg_path="config/precedent_weights.yaml",
    statutory_prefs_cfg_path="config/statutory_prefs.yaml",
    redaction_cfg_path="config/compliance/redaction_rules.yml",
    privacy_defaults=True,
    strict_mode=True,  # raise on invalid config
)
```

3. Quick start (GraphML → reasoning → export)

Using example fixtures in examples/graphs:
- friends_graph.graphml
- group_chat_graph.graphml

```python
from core.adapters.native_bridge import NativeLegalBridge

b = NativeLegalBridge(
    courts_cfg_path="config/courts.yaml",
    precedent_weights_cfg_path="config/precedent_weights.yaml",
    statutory_prefs_cfg_path="config/statutory_prefs.yaml",
    redaction_cfg_path="config/compliance/redaction_rules.yml",
    privacy_defaults=True,
)

g = b.load_graphml("examples/graphs/friends_graph.graphml", reverse=False)
facts_node, facts_edge, _, _ = b.parse_graph_attributes(static_facts=True)

rules = b.build_rules_for_claim(
    claim="breach_of_contract",
    jurisdiction="US-CA",
    use_conservative=False,
)

interp = b.run_reasoning(
    graph=g, facts_node=facts_node, facts_edge=facts_edge, rules=rules, tmax=1
)

# Privacy-aware export (facts only by default profile)
out = b.export_interpretation(interp, profile="default_profile")
print(out["facts"])
```

4. Document ingestion CLI (doc → GraphML)

Convert raw text to a GraphML legal graph using NLP (auto) or regex-only (no NLP):

```bash
# Auto mode (NER + citations if available)
python -m scripts.ingest.doc_to_graph_cli ./my_case.txt -o examples/graphs/generated_case.graphml --mode auto --jurisdiction US-CA --default-year 2020

# Regex-only mode (always available)
python -m scripts.ingest.doc_to_graph_cli ./my_case.txt -o examples/graphs/generated_case.graphml --mode regex
```

Key ingestion functions:
- [doc_to_graph_auto()](nlp/doc_to_graph.py:180) and [doc_to_graph()](nlp/doc_to_graph.py:96)

5. Authority multipliers (how it works)

At build-time, if you do not explicitly pass clause weights, the bridge computes multipliers:
- [_compute_authority_multipliers()](core/adapters/native_bridge.py:325):
  - Treatment modifier: e.g., followed/criticized/overruled weights
  - Recency decay: exponential half-life with a floor
  - Jurisdiction alignment: exact/ancestor/sibling/foreign
  - Court level weights: e.g., US_SCOTUS=1.0, STATE_TRIAL ~0.78
- Applied to the top-level support rule weights in:
  - [build_rules_for_claim()](core/adapters/native_bridge.py:450)

You can still pass explicit weights to override.

6. Aggregators and legal styles

Aggregators (registered in [ANNOTATION_REGISTRY](core/native/annotate.py:285)):
- Burden-of-proof: [legal_burden_civil_051()](core/native/annotate.py:175), [legal_burden_clear_075()](core/native/annotate.py:186), [legal_burden_criminal_090()](core/native/annotate.py:197)
- Conservative: [legal_conservative_min()](core/native/annotate.py:208)
- Precedent-weighted: [precedent_weighted()](core/native/annotate.py:226)

Interpretation styles (weight tuning):
- textualism, purposivism, lenity via [statutory_prefs.yaml](config/statutory_prefs.yaml:1)

7. Privacy and compliance

- Default exports are facts-only; supports/trace require audit_profile.
  - [Interpretation.export()](core/native/interpretation.py:127)
  - [export_interpretation()](core/adapters/native_bridge.py:536)
- Redaction profiles:
  - [config/compliance/redaction_rules.yml](config/compliance/redaction_rules.yml:1)
- Guidance and controls:
  - [docs/LEGAL_DATA_COMPLIANCE.md](docs/LEGAL_DATA_COMPLIANCE.md)

8. CI (coverage gating, native-first)

- Native unit/integration CI with coverage ≥ 80%:
  - [.github/workflows/native-ci.yml](.github/workflows/native-ci.yml:1)


10. Examples and benchmarks

- End-to-end example: [scripts/examples/mini_end_to_end.py](scripts/examples/mini_end_to_end.py:1)
- Benchmarks:
  - [scripts/bench/native_bench.py](scripts/bench/native_bench.py:1)
  - [scripts/benchmarks/perf_benchmark.py](scripts/benchmarks/perf_benchmark.py:1)

11. Troubleshooting and docs

- Troubleshooting: [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md:1)
- Configuration reference (additions for native engine and redaction): [docs/CONFIGURATION_REFERENCE.md](docs/CONFIGURATION_REFERENCE.md:1)
- API guides and examples:
  - [docs/OPENLAW_API_GUIDE.md](docs/OPENLAW_API_GUIDE.md:1)
  - [docs/OPENLAW_API_EXAMPLES.md](docs/OPENLAW_API_EXAMPLES.md:1)

License
- OpenLaw code under repository license terms.