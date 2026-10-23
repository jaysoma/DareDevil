#!/bin/sh
# Brief 11 on LOCATA: brief 10's cuts (harness/batchA/locata/locata_cut.py), then one runner for every scheme set, so
# LOCATA's records carry the same clues as STARSS23's (pause_share, voice bands): harness/batchA/starss23/runner.mjs.
# usage: locata_run.sh <locata data> <work dir> <name=schemes dir> ...
#   writes <work>/truth.jsonl (no audio) and <work>/reads_<name>.jsonl
set -e
DATA=$1; W=$2; shift 2
HERE=$(cd "$(dirname "$0")" && pwd); ROOT=$HERE/../../..
mkdir -p "$W/cuts"
[ -n "$(ls "$W"/cuts/cuts_*.jsonl 2>/dev/null)" ] || python3 "$ROOT/harness/batchA/locata/locata_cut.py" "$DATA" "$W/cuts"
cat "$W"/cuts/truth_*.jsonl > "$W/truth.jsonl"
for spec in "$@"; do
  name=${spec%%=*}; dir=${spec#*=}
  cat "$W"/cuts/cuts_*.jsonl | node "$ROOT/harness/batchA/starss23/runner.mjs" "$dir" > "$W/reads_$name.jsonl" 2> "$W/run_$name.log"
  echo "$name: $(wc -l < "$W/reads_$name.jsonl") reads; $(cat "$W/run_$name.log")"
done
