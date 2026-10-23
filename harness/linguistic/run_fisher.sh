#!/bin/sh
# Brief 18 step 2, text only, with the Fisher model: AMI's test-set meetings, the first UNTIL_S seconds of each, every
# transcript in TRANSCRIPTS (transcripts.py's full and recog, whisper_words.py's whisper), JOBS processes of THREADS
# llama.cpp threads each; then the stand-ins on the same words. A run whose output exists is skipped, so this resumes.
# usage: run_fisher.sh <transcript dir> <gguf> <out dir>      (UNTIL_S=600 JOBS=2 THREADS=2 by default)
#   long: start it detached, e.g. setsid nohup sh run_fisher.sh ... > log 2>&1 &
TX=$1; GGUF=$2; OUT=$3; HERE=$(cd "$(dirname "$0")" && pwd); mkdir -p "$OUT"
MEETINGS=${MEETINGS:-"ES2004a ES2004b ES2004c IS1009a IS1009b IS1009c TS3003a TS3003b EN2002a EN2002b"}
TRANSCRIPTS=${TRANSCRIPTS:-"recog full whisper"}
for m in $MEETINGS; do for t in $TRANSCRIPTS; do [ -s "$OUT/$m.$t.fisher.json" ] || echo "$m $t"; done; done |
  xargs -P "${JOBS:-2}" -n 2 sh -c 'python3 -W ignore '"$HERE"'/run_text.py '"$TX"'/$0.$1.jsonl --model fisher --gguf '"$GGUF"' \
      --threads '"${THREADS:-2}"' --until-s '"${UNTIL_S:-600}"' --out '"$OUT"'/$0.$1.fisher.json > /dev/null 2> '"$OUT"'/$0.$1.fisher.log &&
    echo "$(date +%H:%M) done $0 $1" || echo "$(date +%H:%M) FAIL $0 $1: $(tail -2 '"$OUT"'/$0.$1.fisher.log)"'
for m in $MEETINGS; do for t in $TRANSCRIPTS; do for s in oracle echo; do
  [ -s "$OUT/$m.$t.$s.json" ] || python3 -W ignore "$HERE/run_text.py" "$TX/$m.$t.jsonl" --model $s --until-s "${UNTIL_S:-600}" --out "$OUT/$m.$t.$s.json" > /dev/null
done; done; done
echo "$(date +%H:%M) ALL DONE"
