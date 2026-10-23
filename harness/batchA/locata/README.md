# Batch A on LOCATA (brief 10)

Real talkers walking in one room, recorded by the DICIT array, with OptiTrack truth for each head's position and facing.
Both schemes in `src/schemes/` run unchanged. Every read is recorded in batch A's shared format, and the wrong ones are
classified. Findings: `results/batchA/locata/report.md`.

## 1. Data (outside the repo; never commit audio)
    python3 harness/batchA/locata/locata_fetch.py DATA

Fetches only tasks 3 and 4, DICIT array, dev and eval (136 files, 5.5 GB) out of LOCATA's 6.2 and 13 GB zips
(https://zenodo.org/records/3630471). It uses HTTP range requests and skips the talkers' close-talk recordings.
`zipfile` checks each file's CRC.

## 2. Run everything (under a minute on 4 cores)
    harness/batchA/locata/run_all.sh DATA WORK results/batchA/locata

| step | script | writes |
|---|---|---|
| cut onsets, truth, band SNRs, voice spectrum | `locata_cut.py` | `WORK/cuts_*.jsonl` (audio), `WORK/truth_*.jsonl` |
| both schemes, every recorded clue | `record_reads.mjs` | `WORK/preds_*.jsonl` |
| is ref_vec the facing? | `facing_check.py` | `facing_check.json` |
| range cues, scored for consistency | `range_cues.py` | `range.jsonl`, `range_summary.json` |
| shared record, classes, Jay's rule | `build_records.py` | `reads.jsonl`, `truth.jsonl`, `summary.json`, `locata_<pair>_*` |
| tables for the report | `analyze.py` | `tables.md` |

## 3. Choices worth knowing
- **Pairs:** mics 5-10 (160 mm) and 6-9 (80 mm), both centred on mic 7. L is the first mic named.
- **Onsets:** where a talker's array-aligned VAD (`VAD_dicit_*`) turns on after at least 0.3 s off, inside the
  stretch `required_time.txt` marks valid.
- **Truth:** the exact two-mic delay to the tracked head, in the schemes' own convention (c = 343). Facing is the
  head's `ref_vec` against the direction to the array; `facing_check.py` confirms `ref_vec` is the facing.
- **Scenario,** for Jay's rule: one recording, one talker, one pair.
- **`classes`:** one flat list of `"<scheme>:<name>"` strings, scheme `gcc` or `a2`, so a single record can say which
  scheme each class belongs to. Every wrong read carries its severity (`moderate` > 10 deg, `outlier` > 36 deg) plus
  each class that fits. `build_records.py` defines them. `cause` is null: this is real data.
- **`truth.jsonl`** holds everything about a cut that isn't in the shared record: which talker, the head position,
  how far the truth moved over the half second, and when each other talker spoke.
