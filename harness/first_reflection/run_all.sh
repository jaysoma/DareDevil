#!/bin/bash
# Brief 8, end to end: Angle2.readSound on the dEchorate cuts (all 11 wall configurations) and on batch A's LOCATA
# onsets, then the scores. Audio cuts live in WORK only; never commit them.
# usage: run_all.sh DECHORATE_DATA EARS_DIR LOCATA_DATA WORK OUT
set -euo pipefail
H=$(cd "$(dirname "$0")" && pwd); REPO=$(cd "$H/../.." && pwd)
DDATA=$1; EARS=$2; LDATA=$3; WORK=$4; OUT=$5
mkdir -p "$WORK/dechorate" "$WORK/locata" "$OUT"
strip() { python3 -c "import json,sys
for l in open(sys.argv[1]):
    c = json.loads(l); c.pop('L'); c.pop('R'); print(json.dumps(c))" "$1"; }
export -f strip
one() {
  room=$1; W=$WORK/dechorate
  python3 "$REPO/harness/dechorate/dechorate_cut.py" "$DDATA" "$EARS" --room "$room" --out "$W/cuts_$room.jsonl" > /dev/null
  node "$H/read_sound.mjs" "$W/cuts_$room.jsonl" "$REPO/src/schemes" > "$W/sound_$room.jsonl"
  strip "$W/cuts_$room.jsonl" > "$W/truth_$room.jsonl"
  rm "$W/cuts_$room.jsonl"
}
export -f one; export H REPO DDATA EARS WORK
printf '%s\n' 000000 000001 000010 000100 001000 010000 011000 011100 011110 011111 020002 | xargs -P "$(nproc)" -I{} bash -c 'one {}'
# LOCATA: batch A's cuts (same onsets and ids as results/batchA/locata/truth.jsonl)
python3 "$REPO/harness/batchA/locata/locata_cut.py" "$LDATA" "$WORK/locata" > /dev/null
ls "$WORK"/locata/cuts_*.jsonl | xargs -P "$(nproc)" -I{} bash -c 'f={}; node "$0/read_sound.mjs" "$f" "$1/src/schemes" > "${f/cuts_/sound_}"' "$H" "$REPO"
python3 "$H/score_dechorate.py" "$WORK/dechorate" "$DDATA" "$OUT"
python3 "$H/score_locata.py" "$WORK/locata" "$REPO/results/batchA/locata" "$LDATA" "$OUT"
python3 "$H/analyze.py" "$OUT" > "$OUT/tables.md"
