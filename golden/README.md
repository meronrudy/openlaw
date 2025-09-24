Golden corpus for PyReason outputs used in native-engine parity validation

Contents
- pyreason_version.txt: pinned PyReason version used to generate the corpus
- snapshots/: JSON files produced by running PyReason on reference graphs with legal rules
- scripts:
  - ../scripts/golden/freeze_pyreason_outputs.py: CLI to freeze a graph run
  - ../scripts/golden/make_corpus.sh: helper to generate a multi-graph corpus (optional)

Pinning
- Version: 3.1.0 (vendored in this repository under pyreason/)
  - Source: pyreason/setup.py

How to generate a snapshot
1) Ensure your environment can import the vendored PyReason and its numba dependencies (see pyreason/requirements.txt).
2) Run the freezer script:
   python scripts/golden/freeze_pyreason_outputs.py \
     --graph pyreason/tests/friends_graph.graphml \
     --claim breach_of_contract \
     --jurisdiction US-CA \
     --out-dir golden/snapshots \
     --tmax 1
3) The script writes a timestamped JSON file under golden/snapshots/.

Batch generation
- Optionally use scripts/golden/make_corpus.sh to generate a set of snapshots for available test graphs.
- You can safely re-run; snapshots are timestamped and do not overwrite.

Notes
- The parity validator (scripts/migrate/dual_validate.py) compares exact equality of facts and bounds at the final timestep.
- LEGAL_ENGINE_IMPL=pyreason|native toggles engine selection in the bridge; for parity generation, use PyReason.
- NATIVE_ENGINE_EMIT_FACTS=1 enables native fact emission when validating parity.

Paths
- You may need to adjust config paths (reporters/courts/burden/redaction) depending on your local setup. The freezer accepts None for these and will rely on minimal defaults.