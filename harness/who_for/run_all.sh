#!/bin/bash
# Brief 22 end to end (about 25 minutes on 4 cores): brief 19's set and scores rebuilt, brief 22's windows, scores, numbers.
# usage: run_all.sh SOURCES_DIR WORK_DIR OUT_DIR   (SOURCES_DIR from fetch_sources.sh)
set -euo pipefail
H=$(cd "$(dirname "$0")" && pwd); R=$(cd "$H/../.." && pwd); SRC=$1; WORK=$2; OUT=$3
B19="$H/../device_directed"
(cd "$B19" && python3 build_set.py "$SRC" "$WORK/set" \
  && python3 score.py "$WORK/set" "$SRC" "$WORK/scores" --minilm "$SRC/models/minilm")
python3 "$H/build_requests.py" "$SRC" "$WORK/req"
python3 "$H/score_who.py" "$SRC" "$WORK/set" "$WORK/scores" "$WORK/req" "$WORK/who" --minilm "$SRC/models/minilm"
python3 "$H/evaluate_who.py" "$R" "$WORK/set" "$WORK/scores" "$WORK/who" "$OUT"
python3 "$H/report_tables.py" "$OUT" "$OUT"
cp "$WORK/who/requests_index.jsonl" "$OUT/"
gzip -c "$WORK/who/scores_requests.jsonl" > "$OUT/scores_requests.jsonl.gz"
