#!/bin/sh
# Batch A range on STARSS23, after run_all.sh: re-cut each pair and read the three range cues (range_cues.py), using
# that pair's raw_XY.jsonl only for GccPhat's locked delay. The angle is not touched.
# usage: run_range.sh <starss23 root> <work dir>      (JOBS=4 by default); then range_cues.py --score <work> <out>
ROOT=$1; W=$2; HERE=$(dirname "$0")
printf '1 2\n1 3\n1 4\n2 3\n2 4\n3 4\n' | xargs -P "${JOBS:-4}" -n 2 sh -c '
  p=$0$1
  python3 '"$HERE"'/cut_all.py '"$ROOT"' --pair $0 $1 2> /dev/null |
    python3 '"$HERE"'/range_cues.py '"$W"'/raw_$p.jsonl > '"$W"'/range_$p.jsonl 2> '"$W"'/range_$p.log &&
    echo "range $p: $(wc -l < '"$W"'/range_$p.jsonl)" || echo "FAIL range $p: $(tail -3 '"$W"'/range_$p.log)"'
echo RANGE DONE
