#!/bin/sh
# Brief 18 step 2, text only, with the Fisher model: AMI's test-set meetings, the first UNTIL_S seconds of each, both
# transcripts (transcripts.py), JOBS processes of THREADS llama.cpp threads each; then the stand-ins on the same words.
# usage: run_fisher.sh <transcript dir> <gguf> <out dir>      (UNTIL_S=600 JOBS=2 THREADS=2 by default)
TX=$1; GGUF=$2; OUT=$3; HERE=$(cd "$(dirname "$0")" && pwd); mkdir -p "$OUT"
MEETINGS=${MEETINGS:-"ES2004a ES2004b ES2004c IS1009a IS1009b IS1009c TS3003a TS3003b EN2002a EN2002b"}
for m in $MEETINGS; do for t in recog full; do echo "$m $t"; done; done |
  xargs -P "${JOBS:-2}" -n 2 sh -c 'python3 -W ignore '"$HERE"'/run_text.py '"$TX"'/$0.$1.jsonl --model fisher --gguf '"$GGUF"' \
      --threads '"${THREADS:-2}"' --until-s '"${UNTIL_S:-600}"' --out '"$OUT"'/$0.$1.fisher.json > /dev/null 2> '"$OUT"'/$0.$1.fisher.log &&
    echo "done $0 $1: $(python3 -c "import json; d=json.load(open(\"'"$OUT"'/$0.$1.fisher.json\")); print(d[\"per_window_pct\"], d[\"whole_meeting_pct\"], d[\"seconds_per_pass\"])")" ||
    echo "FAIL $0 $1: $(tail -2 '"$OUT"'/$0.$1.fisher.log)"'
for m in $MEETINGS; do for t in recog full; do for s in oracle echo; do
  python3 -W ignore "$HERE/run_text.py" "$TX/$m.$t.jsonl" --model $s --until-s "${UNTIL_S:-600}" --out "$OUT/$m.$t.$s.json" > /dev/null
done; done; done
echo ALL DONE
