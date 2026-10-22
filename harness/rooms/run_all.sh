#!/bin/sh
# Every room config (or those in $CONFIGS) at 157 and 69 mm: cuts, then both schemes unchanged. usage: run_all.sh <utts.npy> <work dir> [schemes dir]
set -e
U=$1; W=$2; SCH=${3:-src/schemes}; mkdir -p "$W/cuts" "$W/preds"
for c in ${CONFIGS:-$(python3 harness/rooms/rooms.py --list)}; do for d in 0.157 0.069; do echo "$c $d"; done; done |
  xargs -P "${JOBS:-4}" -n 2 sh -c 'python3 harness/rooms/rooms.py '"$U"' $0 $1 '"$W"'/cuts/$0_$1.jsonl >/dev/null &&
    node harness/starss23/run_schemes.mjs '"$W"'/cuts/$0_$1.jsonl '"$SCH"' > '"$W"'/preds/$0_$1.jsonl && echo done $0 $1'
