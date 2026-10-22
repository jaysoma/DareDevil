#!/bin/bash
# The whole dEchorate run: every wall configuration, cut -> run both schemes -> keep the truth (no audio) and predictions.
# usage: run_all.sh DATA_DIR EARS_DIR WORK_DIR OUT_DIR   (WORK_DIR holds the cuts while a room runs; never commit it)
set -euo pipefail
H=$(cd "$(dirname "$0")" && pwd); DATA=$1; EARS=$2; WORK=$3; OUT=$4
mkdir -p "$WORK" "$OUT"
one() {
  room=$1
  python3 "$H/dechorate_cut.py" "$DATA" "$EARS" --room "$room" --out "$WORK/cuts_$room.jsonl"
  node "$H/run_schemes.mjs" "$WORK/cuts_$room.jsonl" "$H/../../src/schemes" > "$WORK/preds_$room.jsonl"
  python3 -c "import json,sys
for l in open(sys.argv[1]):
    c = json.loads(l); c.pop('L'); c.pop('R'); print(json.dumps(c))" "$WORK/cuts_$room.jsonl" > "$WORK/meta_$room.jsonl"
  rm "$WORK/cuts_$room.jsonl"
}
export -f one; export H DATA EARS WORK
printf '%s\n' 000000 000001 000010 000100 001000 010000 011000 011100 011110 011111 020002 | xargs -P "$(nproc)" -I{} bash -c 'one {}'
cat "$WORK"/meta_*.jsonl | gzip -n > "$OUT/truth.jsonl.gz"
cat "$WORK"/preds_*.jsonl | gzip -n > "$OUT/preds.jsonl.gz"
python3 "$H/dechorate_score.py" "$OUT/truth.jsonl.gz" "$OUT/preds.jsonl.gz" "$OUT/scores.json" measured
python3 "$H/dechorate_score.py" "$OUT/truth.jsonl.gz" "$OUT/preds.jsonl.gz" "$OUT/scores_geometry.json" geometry > /dev/null
python3 "$H/analyze.py" "$OUT" measured > "$OUT/tables.md"
python3 "$H/analyze.py" "$OUT" geometry > "$OUT/tables_geometry.md"
