#!/bin/bash
# Brief 19 end to end: build the set, score every phrase with every method, evaluate, write the results.
# The two general models take about 3.5 hours on 4 CPU cores; everything else about 10 minutes.
# usage: run_all.sh SOURCES_DIR WORK_DIR OUT_DIR   (SOURCES_DIR from fetch_sources.sh)
set -euo pipefail
H=$(cd "$(dirname "$0")" && pwd); SRC=$1; WORK=$2; OUT=$3
cd "$H"
python3 build_set.py "$SRC" "$WORK/set"
python3 score.py "$WORK/set" "$SRC" "$WORK/scores" --minilm "$SRC/models/minilm" \
  --gguf "$SRC/models/qwen2.5-0.5b-instruct-q4_k_m.gguf" "$SRC/models/qwen2.5-1.5b-instruct-q4_k_m.gguf" --threads 4
python3 evaluate.py "$WORK/set" "$WORK/scores" "$WORK/eval"
python3 report_tables.py "$WORK/set" "$WORK/scores" "$WORK/eval" "$OUT"
