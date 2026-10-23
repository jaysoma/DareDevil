#!/bin/bash
# Batch A on LOCATA, end to end: cut -> both schemes' records -> range cues -> classify and score -> tables.
# usage: run_all.sh DATA_DIR WORK_DIR OUT_DIR   (DATA_DIR from locata_fetch.py; WORK_DIR holds audio cuts: never commit)
set -euo pipefail
H=$(cd "$(dirname "$0")" && pwd); DATA=$1; WORK=$2; OUT=$3
mkdir -p "$WORK" "$OUT"
python3 "$H/locata_cut.py" "$DATA" "$WORK"
ls "$WORK"/cuts_*.jsonl | xargs -P "$(nproc)" -I{} bash -c 'f={}; node "$0/record_reads.mjs" "$f" "$0/../../../src/schemes" > "${f/cuts_/preds_}"' "$H"
for f in "$WORK"/cuts_*.jsonl; do
  python3 -c "import json,sys
for l in open(sys.argv[1]):
    c = json.loads(l); c.pop('L'); c.pop('R'); print(json.dumps(c))" "$f" > "${f/cuts_/truth_}"
done
python3 "$H/facing_check.py" "$DATA" "$OUT/facing_check.json"
python3 "$H/range_cues.py" "$WORK" "$OUT" > /dev/null
python3 "$H/build_records.py" "$WORK" "$OUT" > /dev/null
python3 "$H/analyze.py" "$OUT" > "$OUT/tables.md"
