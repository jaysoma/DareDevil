#!/bin/bash
# Brief 21 end to end: cut LOCATA's utterances with their truth, read them, compute the CDR, score every policy.
# LOCATA_DIR from harness/batchA/locata/locata_fetch.py. About 10 minutes on 4 cores; WORK holds audio: never commit it.
# usage: run_all.sh LOCATA_DIR WORK_DIR OUT_DIR
set -euo pipefail
H=$(cd "$(dirname "$0")" && pwd); REPO=$(cd "$H/../.." && pwd); DATA=$1; WORK=$2; OUT=$3
python3 "$H/cut_utterances.py" "$DATA" "$WORK"
ls "$WORK"/utt_*.jsonl | xargs -P "$(nproc)" -I{} bash -c 'f={}; node "$0/run_reads.mjs" "$f" "$1/src/schemes" > "${f/utt_/reads_}"' "$H" "$REPO"
python3 "$H/range_hops.py" "$WORK" > /dev/null
python3 "$H/score.py" "$WORK" "$WORK"
python3 "$H/tables.py" "$WORK" "$OUT"
