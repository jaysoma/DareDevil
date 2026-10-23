#!/bin/bash
# Brief 16 end to end: jobs -> DFN pass (both levels, 4 shards each) -> analysis.
# usage: run_all.sh DFNENV STARSS_ROOT LOCATA_ROOT WORK OUT
#   DFNENV: the venv holding deepfilternet 0.5.6 (README.md); WORK holds frames, preds, clues (no audio is kept).
set -euo pipefail
H=$(cd "$(dirname "$0")" && pwd); REPO=$(cd "$H/../.." && pwd)
ENV=$1; STARSS=$2; LOCATA=$3; WORK=$4; OUT=$5
mkdir -p "$WORK" "$OUT"
python3 "$H/build_jobs.py" "$REPO" "$STARSS" "$LOCATA" "$WORK/jobs.jsonl"
N=$(nproc)
for level in raw norm; do
  for k in $(seq 0 $((N - 1))); do
    "$ENV/bin/python" "$H/dfn_pass.py" "$WORK/jobs.jsonl" "$WORK" --level $level --shard $k --of $N \
      > "$WORK/log_${level}_$k.txt" 2>&1 &
  done
  wait
done
python3 "$H/analyze.py" "$REPO" "$WORK" "$OUT"
