# Brief 8: does `Angle2.readSound` find the first reflection, its angle and its lag?

`readSound` runs unchanged, on the dEchorate cuts (clean EARS speech through the measured RIRs, all 11 wall
configurations) and on batch A's LOCATA talker onsets. Findings: `results/first_reflection/report.md`.

## Run
    harness/first_reflection/run_all.sh DECHORATE_DATA EARS_DIR LOCATA_DATA WORK results/first_reflection

The data comes from the dEchorate harness (`harness/dechorate/README.md`) and from `harness/batchA/locata/locata_fetch.py`.
On 4 cores this takes about 10 minutes, mostly running `readSound` on 19,008 dEchorate cuts. Audio stays in WORK.

| script | does |
|---|---|
| `read_sound.mjs` | Finds each cut's first sound with Angle2's own stream, then calls `readSound` at that frame and records `decided`, the onset, the reflection's angle, `gap_ms`, `fit` and why it's undecided. |
| `score_dechorate.py` | Scores the onset under Jay's rule, the reflection against the labelled echoes (angle, lag, both, chance), the echoes outside the 1-12 ms window, and the wall placement. |
| `score_locata.py` | Scores the onset under Jay's rule, the lag against the floor and ceiling echoes from the tracked head, and the lag as a range cue next to the CDR. |
| `analyze.py` | Writes `tables.md`. |

## Choices
- **Truth on dEchorate** is `harness/dechorate/truth.py`'s measured mode, as every dEchorate score since brief 3.
  The south wall never counts as reflective.
- **The reflection is scored only where the rule kept the onset:** decided reads whose onset wasn't set aside.
  Every read the rule set aside is catalogued in `*_onset_outliers.jsonl`.
- **The wall is placed in the plane through the pair's axis and the true source,** on both sides of the axis, since two
  mics can't tell which. A ceiling or floor can't be placed this way, and the report says so.
- **LOCATA's echoes:** the floor is at z = 0 and the ceiling at 3.0 m (LOCATA paper, 7.1 × 9.8 × 3 m). The mouth is
  taken as 0.12 m below the head marker, as in brief 10. The walls can't be placed: the release doesn't say where they
  are in the tracker's coordinates.
