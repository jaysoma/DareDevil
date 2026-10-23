# Brief 21: when to re-read within an utterance (angle, range, facing)

Scores update policies over time against LOCATA's continuous truth: where the talker was, how far away, and which way
they faced, every 50 ms while they spoke. Findings: `results/resample/report.md`.

## Run
    harness/resample/run_all.sh LOCATA_DIR WORK results/resample

LOCATA_DIR comes from `harness/batchA/locata/locata_fetch.py` (tasks 3 and 4, DICIT array, dev and eval).

| script | does |
|---|---|
| `cut_utterances.py` | Cuts each talker's utterances (VAD merged across gaps under 0.3 s, brief 10's onset rule) and phrases (gaps of 0.1 s or more), for the 160 and 80 mm pairs, with the truth on a 50 ms grid. |
| `GccPhatSpan.mjs` | A harness copy of `src/schemes/GccPhat.mjs`, unchanged, with two functions appended: `readSpan` (the lock's read over any half second, weighted by the utterance's own onset pause; at the lock's own place it reproduces the stream's lock on 660 of 660 utterances) and `readPause` (batch A's pause read). |
| `run_reads.mjs` | Per utterance: GccPhat's stream as shipped (every settling read and the lock), Angle2's onset, the pause read, and a half-second re-read every 0.25 s from the lock on. |
| `range_hops.py` | A copy of `src/geonar/cdr_direct.py`'s direction-free CDR with one switch, the c/2d clamp, which would otherwise empty the 0.1-1 kHz band. The copy matches `src` exactly with the clamp on. Per-hop powers per utterance, summed over any window. |
| `score.py` | Every policy against the truth: time-weighted error, moves, lag. Also the motion statistics and the facing analysis. Definitions are in its docstring. |
| `tables.py` | Writes `tables.md` and `tradeoff.png`. |

`src/` is unchanged.
