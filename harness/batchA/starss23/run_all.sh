#!/bin/sh
# Batch A on STARSS23: every onset, all six pairs, cut straight into the runner (no cut files on disk).
# usage: run_all.sh <starss23 root> <work dir> [schemes dir]      (JOBS=3 by default)
# writes <work>/truth_XY.jsonl (cut_all.py, no audio) and <work>/raw_XY.jsonl (runner.mjs), then prints "done XY"
ROOT=$1; W=$2; SCH=${3:-src/schemes}; mkdir -p "$W"
HERE=$(dirname "$0")
printf '1 2\n1 3\n1 4\n2 3\n2 4\n3 4\n' | xargs -P "${JOBS:-3}" -n 2 sh -c '
  p=$0$1
  python3 '"$HERE"'/cut_all.py '"$ROOT"' --pair $0 $1 --truth '"$W"'/truth_$p.jsonl 2> '"$W"'/cut_$p.log |
    node '"$HERE"'/runner.mjs '"$SCH"' > '"$W"'/raw_$p.jsonl 2> '"$W"'/run_$p.log &&
    echo "done $p: $(wc -l < '"$W"'/raw_$p.jsonl) reads; $(cat '"$W"'/cut_$p.log); $(cat '"$W"'/run_$p.log)" ||
    echo "FAIL $p: $(tail -3 '"$W"'/cut_$p.log '"$W"'/run_$p.log)"'
echo ALL DONE
