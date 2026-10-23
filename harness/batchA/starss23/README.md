# Batch A on STARSS23 (brief 9)

Why the angle locks onto a wrong direction, on real talkers in 16 rooms, and what each read knew at the time. Both
schemes run unchanged from `src/schemes/`; everything recorded here is read beside them and feeds nothing back.
Results: `results/batchA/starss23/`.

## Steps
Data: `metadata_dev.zip` and `mic_dev.zip` from https://zenodo.org/records/7880637, unzipped into `<root>`.

    sh harness/batchA/starss23/run_all.sh <root> <work> src/schemes      # every onset, 6 pairs: truth_XY + raw_XY
    python3 harness/batchA/starss23/sphere_grid.py | node harness/batchA/starss23/runner.mjs src/schemes \
        > <work>/sphere_grid_reads.jsonl                                  # what each scheme reads through the sphere alone
    python3 harness/batchA/starss23/classify.py <work> results/batchA/starss23
    sh harness/batchA/starss23/run_range.sh <root> <work>                 # range, alongside
    python3 harness/batchA/starss23/range_cues.py --score <work> results/batchA/starss23/range_summary.json

About an hour on 4 cores for the angle, 20 minutes for range. No audio and no cuts are written to disk: `cut_all.py`
streams into the runners.

## Files
- **`cut_all.py`:** every onset of every class (not only solo speech), with the other sources active from 0.5 s before
  to 0.5 s after it. `solo` marks starss_cut.py's single-talker test, so the old set is a subset.
- **`runner.mjs`:** both schemes, fed as the Conductor feeds them, plus the shared record's clues. GccPhat's vote total,
  pause read, band SNRs and third-octave voice shares come from a harness copy of its sum. `gcc.replica_ok` checks the
  copy against the stream on every read.
- **`sphere_grid.py`:** the reference. The STARSS capsules sit on a rigid sphere, which reads every bearing wider than
  the geometric angle. Each read is judged against what the same scheme reads from the same direction through the
  sphere alone, interpolated from a 5 x 10 deg grid.
- **`classify.py`:** the shared record per read, the wrong-read classes (definitions in its docstring), Jay's scoring
  rule (`harness/scoring/clean_score.py`), the catalogue and the clue medians.
- **`range_cues.py`, `run_range.sh`:** the three range cues and their consistency scores.

## The record (`reads.jsonl.gz`)
The shared batch A format, field names exact. Additions, never renames:
- **Top-level `classes`:** GccPhat's angle 1. Angle2's are in `a2.classes`.
- **Per scheme:** `err` (against the sphere reference), `err_geo` (against the geometric angle), and `severity`: `ok`
  at 10 deg or less, `moderate` up to 36, `outlier` beyond.
- **`truth.sphere_deg`:** `{gcc, a2}`. Each other source carries its own.
- **`gcc` extras:** `votes_of` (the slice count), `frames`, `replica_ok`.
- **Top level:** `pause_share`, `voice_bands`.
- **`truth` extras:** `kind`, `class`, `solo`, `file`, `onset_s`, `az`, `el`, `lateral_span` and `src`.
