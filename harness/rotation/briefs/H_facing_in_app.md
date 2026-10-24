# Brief H: put the facing call and the range correction into the app (Jay's option b)

Read `README.md` here first. This brief may change `src/` (the Conductor and CdrRange) and `render/README.md`; nothing
else runs beside it. Folders for its scripts and numbers: `harness/rotation/inapp/`, `results/rotation/inapp/`.
Worktree: `git worktree add ../dd-inapp -b rotation-inapp`.

## What's decided (from data)
- **Angle:** unchanged. GccPhat re-reads every 0.25 s and moves on a committed change over 5 deg (brief 21).
- **Range:** one read per utterance from 0.13-0.5 s after the onset (`RANGE_READ_S`, Conductor v13; brief 21).
- **Facing: one call per utterance, once 2 s of speech is in, then held** (brief G: 75% on a 2-4 s utterance, 63% on
  the half-second read, nothing more from longer speech).
  - **The cue:** the contrast, CDR 4-8 kHz minus unfloored CDR 0.1-1.1 kHz.
  - **The call:** turned below about −1 dB (`results/rotation/fixed_threshold.txt`; 81% unchanged on LOCATA, brief D).
  - **Under 2 s:** no call.
- **Range correction, Jay's option b:** when the 2 s facing call says turned, the range read is corrected once:
  statistic + k × (−1 dB − contrast). The dot then moves at most once more in that utterance. Brief E fitted k = 0.9
  with both numbers from the same half second; under option b they come from different spans.

## Steps
1. **Fit k for option b.**
   - **The numbers:** the range statistic from 0.13-0.5 s; the contrast from 0.13-2.0 s, on utterances of 2 s or
     more (brief G's utterances, `harness/rotation/utterance/`).
   - **Fit:** k left out by walk on Jay's walks.
   - **Scores, brief E's way** (`harness/rotation/range/`): the fling on Jay's stops, ordering on the ladders, and
     LOCATA's scores.
   - **Compare** against today and against E's half-second version.
   - **Gate:** if no k beats today on the fling without losing more than 5 points of ladder ordering, stop and report.
2. **The Conductor (VERSION 14):**
   - **The new band:** add 0.1-1.1 kHz to the CDR stream, unfloored, as a fourth band after the three in `cdrf`. Keep
     the first six values as they are, so CdrRange's old reading is unchanged.
   - **Longer frames:** keep sending CDR frames until `FACING_READ_S = 2.0` s after the onset.
   - **The range read still commits** only from frames that end by `RANGE_READ_S`.
3. **CdrRange:**
   - **At 0.5 s:** draw range exactly as today.
   - **At 2.0 s:** sum the fourth band and the 4-8 kHz band over 0.13-2.0 s and take the contrast. Set facing to
     `facing` or `turned`. If turned, correct the range once with step 1's k.
   - **Expose it:** `facing(f)` returns that state (it returns null today), and the state is null before 2 s and for
     shorter utterances.
   - **Document it** at the constants, the way the file already does.
4. **Regression:**
   - **Unchanged:** every existing harness that runs CdrRange or the Conductor must reproduce today's output for
     utterances under 2 s and for facing calls.
   - **Changed:** list what changes, and why.
   - **Tests:** add a small test fixture.
5. **`render/README.md`:** the new `facing` field, and that a turned talker is drawn faded. Jay's fade line is 120 deg,
   but the cue can't tell 120 from 90, so in practice it fades past about side-on.

## Report
`results/rotation/inapp/report.md`: k and its scores, what changed in `src/`, and the regression result.
