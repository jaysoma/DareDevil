#!/bin/sh
# Brief 20: per-band CDR for every cut of a dataset, via that dataset's own cutter (no audio kept).
# usage: run_cdr.sh dechorate <dEchorate data> <EARS dir> <out dir>
#        run_cdr.sh starss <STARSS23 root> <out dir>
#        run_cdr.sh locata <LOCATA cuts dir (locata_cut.py's output)> <out dir>
HERE=$(cd "$(dirname "$0")" && pwd); ROOT=$HERE/../..
case $1 in
  dechorate)
    mkdir -p "$4"
    for room in 000000 010000 011000 011100 011110 011111 001000 000100 000010 000001 020002; do
      (cd "$ROOT/harness/dechorate" && python3 dechorate_cut.py "$2" "$3" --room $room --spacings 155 --out /dev/stdout 2>/dev/null | grep "^{") |
        python3 "$HERE/drr.py" > "$4/dechorate_$room.jsonl" && echo "dechorate $room: $(wc -l < "$4/dechorate_$room.jsonl")"
    done ;;
  starss)
    mkdir -p "$3"
    for p in "1 2" "3 4"; do
      python3 "$ROOT/harness/batchA/starss23/cut_all.py" "$2" --pair $p 2>/dev/null | grep -F '"kind": "speech"' | python3 "$HERE/drr.py" > "$3/starss_$(echo $p | tr -d ' ').jsonl" &&
        echo "starss $p: $(wc -l < "$3/starss_$(echo $p | tr -d ' ').jsonl")"
    done ;;
  locata)
    mkdir -p "$3"
    cat "$2"/cuts_*.jsonl | python3 "$HERE/drr.py" > "$3/locata.jsonl" && echo "locata: $(wc -l < "$3/locata.jsonl")" ;;
esac
