#!/usr/bin/env bash
# Generate a golden corpus of PyReason outputs for parity validation.
# Usage:
#   bash scripts/golden/make_corpus.sh
# Optional env:
#   GRAPH_LIST: space-separated list of GraphML paths (default: a few bundled examples)
#   CLAIM: legal claim id (default: breach_of_contract)
#   JURIS: jurisdiction (default: US-CA)
#   OUT_DIR: output directory for snapshots (default: golden/snapshots)
#   TMAX: timesteps (default: 1)

set -euo pipefail

THIS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" &>/dev/null && pwd)"
REPO_ROOT="$(cd "${THIS_DIR}/../.." &>/dev/null && pwd)"

GRAPH_LIST_DEFAULT="pyreason/tests/friends_graph.graphml"
GRAPH_LIST="${GRAPH_LIST:-$GRAPH_LIST_DEFAULT}"

CLAIM="${CLAIM:-breach_of_contract}"
JURIS="${JURIS:-US-CA}"
OUT_DIR="${OUT_DIR:-golden/snapshots}"
TMAX="${TMAX:-1}"

echo "[golden-corpus] repo=${REPO_ROOT}"
echo "[golden-corpus] graphs=${GRAPH_LIST}"
echo "[golden-corpus] claim=${CLAIM} juris=${JURIS} tmax=${TMAX}"
echo "[golden-corpus] out_dir=${OUT_DIR}"

cd "${REPO_ROOT}"

PY=python
if ! command -v python &>/dev/null; then
  if command -v python3 &>/dev/null; then PY=python3; else echo "Python not found"; exit 1; fi
fi

for G in ${GRAPH_LIST}; do
  if [ ! -f "${G}" ]; then
    echo "[golden-corpus] WARN: graph not found: ${G}" >&2
    continue
  fi
  echo "[golden-corpus] Freezing ${G} ..."
  "${PY}" scripts/golden/freeze_pyreason_outputs.py \
    --graph "${G}" \
    --claim "${CLAIM}" \
    --jurisdiction "${JURIS}" \
    --out-dir "${OUT_DIR}" \
    --tmax "${TMAX}" || {
      echo "[golden-corpus] ERROR freezing ${G}" >&2
      exit 2
    }
done

echo "[golden-corpus] Done."