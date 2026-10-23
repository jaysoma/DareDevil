# Cloud session briefs

One brief per Claude Code cloud session (claude.ai/code, repo jaysoma/DareDevil). Paste a brief as the session's first
message. The briefs don't depend on each other, so run them in parallel. Each session starts fresh: it knows only this
repo and the brief.

Prerequisites for every session:
- Code in the repo: `src/schemes/` (GccPhat, Angle2), `src/geonar/` (conductor and its modules), `harness/starss23/`.
- Network access in the environment that allows `zenodo.org`.
- The Claude GitHub App installed on this repo, so the session can push its results branch.

Scoring, for every brief from 5 on: Jay's rule in `results/clean/report.md` (|truth| <= 75 deg only; reads off by
more than 36 deg set aside; scenarios averaging over 22.5 deg, or losing over half their reads, dropped whole). Report
the cleaned mean and median next to how much was set aside, and catalogue the outliers. `harness/scoring/clean_score.py`
implements it.

---

## 1. STARSS23 real-audio run

DONE in Jay's 2026-10-22 session: `results/starss23/report.md`.
Don't start this one.

Read HANDOFF.md, then harness/starss23/. Download `metadata_dev.zip` and `mic_dev.zip` from
https://zenodo.org/records/7880637 into a data directory outside the repo; never commit audio.

Cut single-talker speech onsets with `starss_cut.py`. Do this for every one of the 6 capsule pairs, not only (1,2) and
(3,4). Run every scheme in `src/schemes/` unchanged through `run_schemes.mjs`, then score with `starss_score.py`.

Answer, with numbers per room and per pair:
- Does each scheme's error hold across the 16 rooms (general) or vary by room (tuned)?
- Does each scheme lean toward 0 deg beyond what the synthetic plane-wave test shows?
- When angle 1 is wrong, is angle 2 or angle 3 right?

The tetrahedron pairs are about 69 mm apart, not the phone's 157 mm. Compare across rooms and pairs; don't report the
absolute error as the phone's. Commit `results/starss23/report.md` and the per-cut predictions (JSONL) to a branch.

## 2. Angle2 inward pull

DONE in the 2026-10-22 cloud session: `results/angle2_pull.md`. It covers the mechanism, the fix, before/after in
rooms, and the STARSS re-check (section 4: Angle2's pull against GccPhat is down by about two-thirds, and every room
improves).

Read HANDOFF.md, `results/starss23/report.md` (section 2), then `src/schemes/Angle2.mjs`. REVISED 2026-10-22 after
the STARSS23 run: `readUtterance` reads 2-19 deg nearer 0 than GccPhat on the same real cuts, growing with angle, but
with exact fractional delays and no room it is within 1 deg everywhere. The pull comes with reflections. A plane-wave
test cannot show it, so don't start there.

Also read `results/dechorate/report.md` (section 2): in measured RIRs, a strong ceiling echo 2.6 ms late does not pull
Angle2 in (it pulls GccPhat ~1 deg), yet Angle2 already leans 1-3 deg in scope with every panel absorbing.

1. Reproduce it with reflections. Use image-source rooms (`pip install pyroomacoustics`) at 157 mm and at 69 mm: a
   direct path plus a floor and one wall, then a full shoebox. Sweep -60 to +60 deg. Find the smallest room that pulls
   it in.
2. Find the mechanism. Candidates: `U_AGREE = 3` samples merging direct and reflection reads into one family; the
   recurrence count (`U_HITS`) letting a near-0 reflection family reach 3 first; the 3 ms window holding the direct and
   a reflection together. Log every window's read for a few pulled cuts and show which it is.
3. Fix it in Angle2 only, never GccPhat. Check the fix on the room sweep, and on the STARSS cuts if you can make them
   (`harness/starss23/starss_cut.py`, data from https://zenodo.org/records/7880637).

Commit the fix and `results/angle2_pull.md` (mechanism, before/after table) to a branch.

## 3. dEchorate onset and first-reflection truth

DONE in a 2026-10-22 cloud session: `results/dechorate/report.md`. GccPhat finds the direct path; neither scheme finds
the first reflection. v2.0's RIR file below can't be read; the run used v1.0's `dechorate_rir_processed.hdf5`
(https://zenodo.org/records/5562386). Don't start this one.

Read HANDOFF.md. From https://zenodo.org/records/6576203, download `dEchorate_rirs_gzip7.hdf5`,
`dEchorate_database.csv`, `dEchorate_echo_notes.pkl` and `main_geometry_from_echo_calibration.py` (about 4.2 GB
total). Skip the speech, babble and noise files.

For each wall configuration and source, pick mic pairs, convolve clean speech with the measured RIRs, and run
`Angle2.readUtterance` and `GccPhat`. Score the onset direction against the direct-path TDOA, and the "first
reflection" against the labelled first-order echoes. Report hit rates by wall configuration.

Commit `results/dechorate/report.md` to a branch.

## 4. The 0 deg peak in silence, on independent data

DONE in a 2026-10-22 cloud session: `results/zero_deg/report.md`. No 0 deg peak in STARSS23 pauses, though the
low-frequency diffuse noise is there; the phone-side test is `harness/zero_deg/phone_pause.py`.
Don't start this one.

Read HANDOFF.md, item 2 of "Done". ODAS puts 47% of active pause directions within 6 deg of 0, and the top suspect is
low-frequency diffuse noise that is coherent at zero lag. Test this on STARSS23 pause segments, with no speech active
per the labels. Measure the share of GCC-PHAT peaks within 6 deg of 0 at high-pass 0, 100, 300 and 1100 Hz, for each
pair and room.

If the 0 deg share collapses with the high-pass, the mechanism is general and not the phone's. Commit
`results/zero_deg/report.md` to a branch.

---

## 5. dEchorate with the fixed Angle2

FOLDED INTO BRIEF 7 (2026-10-22). Don't start this one; brief 7 runs the fixed Angle2 on dEchorate as part of its work.

Read HANDOFF.md, `results/dechorate/report.md` and `results/angle2_pull.md`. `src/schemes/Angle2.mjs` on `main` now has
brief 2's fix: `readUtterance` counts clean, rising windows first and flags its onset `edge: true`; otherwise it falls
back to the old count, flagged `edge: false`. The dEchorate run was made before the fix.

1. Re-run `harness/dechorate/run_all.sh` with the current `src/schemes/`. Record Angle2's `edge` flag per cut.
2. Report before and after for Angle2, per wall configuration, at 155 mm and 65 mm: median error, share within 10 deg,
   lean by |truth| band, and the share of cuts with an edge onset. GccPhat hasn't changed, so its reads should
   reproduce exactly. Check that, and stop if they don't.
3. The agreement rule from STARSS23: when GccPhat and Angle2 agree within 5 deg and Angle2's onset is an edge, what is
   GccPhat's error? And when they disagree, or when there's no edge? Give each case's share of cuts.
4. Did Angle2's second family (the "first reflection") change?

Score against the measured direct-path truth and the published geometry, as the first run did. Then extend
`harness/scoring/clean_score.py` to the new predictions and report under the scoring rule above. Commit
`results/dechorate/after_angle2_fix/` and a short section in `results/dechorate/report.md` to a branch.

## 6. Relative distance: which physical cue ranks talkers by distance?

ON HOLD (Jay, 2026-10-22): range waits until bearing is settled. Don't start this one.

Read HANDOFF.md (the Range line: relative units anchored on the opening utterance, no metres). Then read
`src/range/FiveMsAmplitude.js` and `src/geonar/cdr_direct.py`, whose notes record what was already tried. The question:
which cue puts talkers in the right order of distance, in rooms it has never seen?

**The cues to test, each from the onset of an utterance:**
- **Level.** The 1 / amplitude of the first 5 ms (FiveMsAmplitude), and the level over the first 50 ms and the first
  500 ms. Physics: the direct sound falls 6 dB per doubling of distance. Confounds: how loudly the talker speaks, and
  which way they face.
- **Direct-to-diffuse ratio.** `cdr_free_bands` and `cdr_free_db` in `cdr_direct.py`, per band (1.1-2, 2-4 and 4-8
  kHz), with each band's floor raised to c/2d for the pair's spacing. Sum the powers from 0.13 s to 0.6 s after the
  onset, as the Conductor does. Physics: the reverberant level is about the same everywhere in a room, so the ratio
  falls 6 dB per doubling whatever the talker's loudness. Confounds: facing, and the room.
- **Floor and ceiling echo lag.** The lag of the strongest early echo, 1-12 ms, from each channel's autocorrelation or
  cepstrum, summed over the onset's first 100-300 ms. Physics: the extra path is sqrt(r^2 + H^2) - r, with H the mic
  height plus the mouth height for the floor, and the two distances below the ceiling added together for the ceiling.
  So the lag shrinks as the talker moves away, independent of loudness, facing or room size. Check first whether the
  echo can be found in speech at all.
- **Near-field level difference between the two capsules.** Expect it to vanish beyond about 1 m; confirm.

**The data:**
- **STARSS23** (https://zenodo.org/records/7880637). `harness/starss23/starss_cut.py` cuts carry `dist_cm`, `room`,
  `file` and `src` (the talker). Lengthen `POST_S` locally if a cue needs more than 1 s. Truth is the head marker's
  distance from the array.
- **dEchorate**, with `harness/dechorate/`. Every source-to-array distance is known, across 11 wall configurations, so
  it shows how each cue depends on the room's reflectivity. Use the published geometry for distance truth; its RIRs'
  delays run 3-23% long, but distance doesn't use the delay.

**Scoring:**
- **Pairwise order:** within one file and one talker, for pairs whose true distances differ by at least 1.25x, 1.5x
  and 2x, the share of pairs each cue orders correctly.
- **Anchored:** each talker's first onset in a file is the anchor. Score predicted r/r0 against true r/r0, as a log
  error.
- **Breakdowns:** per cue, per band, per room or wall configuration. Then the best pair of cues together.
- **The verdict:** which cue holds across rooms (general) and which needs tuning per room.

Commit `results/distance/report.md` and the harness under `harness/distance/` to a branch.

---

# Stage 1: what a two-ear listener hears

Jay's stages: Stage 1 is acoustic and spatial, two raw streams, binaural. Every sound that registers is rendered where
the array heard it come from, with speech as a bubble and everything else as rings. A talker facing the wall is
rendered where the math says the speech came from, which can be the wall. So Stage 1's truth is **the direction the
sound arrived from**, not where the source stands. The first onset and the first reflection are the core: showing that
a sound came off a wall is the demo. Stage 2 (identity, diart) waits until Stage 1 is settled.

## 7. dEchorate, scored by where the sound arrived from

Read HANDOFF.md, `results/dechorate/report.md` and `results/clean/report.md`. This brief includes brief 5.

1. **Re-run the schemes.** Run `harness/dechorate/run_all.sh` with the current `src/schemes/`, which includes the fixed
   Angle2 with its `edge` flag. GccPhat's reads should reproduce the first run exactly; stop if they don't.
2. **Build a second truth per cut: the strongest early arrival.** From the two RIRs of the cut's mic pair, measure the
   peak at the direct path and at each labelled first-order echo (`truth.py` has the times). The arrival truth is the
   direct path when its peak is within 6 dB of the strongest echo, and otherwise the strongest echo's direction. Report
   how often each surface is the arrival, by source. Sources 4 and 5 face a wall.
3. **Score both schemes against both truths,** under the scoring rule above, per wall configuration, spacing (155 and
   65 mm) and source facing.
   - **The headline:** for wall-facing sources, the share of reads that land on the strongest arrival when it's an echo.
     That's "rendered the wall correctly".
   - **Re-sort the outlier catalogue:** which of the old outliers were correct renderings under arrival truth?
4. **Brief 5's questions:** Angle2 before and after its fix, and the agreement rule (GccPhat and Angle2 within 5 deg,
   with an edge onset) against both truths.

Commit `results/dechorate_arrival/` (report, summary, catalogue) and the harness changes to a branch.

## 8. First reflection: does `Angle2.readSound` find the echo, its angle and its lag?

Read HANDOFF.md, `results/dechorate/report.md` (section 3) and `src/schemes/Angle2.mjs`. `readSound` cancels the
direct sound, then looks for the earliest positive, delayed copy of the voice in what remains: a direction and a lag.
Only `readUtterance`'s second family was scored before, and that turned out to be a window artifact. `readSound` has
never been scored.

1. **Run `readSound` on the same dEchorate cuts** (`harness/dechorate/`, clean EARS speech through the measured RIRs),
   with `s` at the sound's first frame. Record `decided`, the onset, the reflection's angle, `gap_ms` and `fit`.
2. **Score against the labelled first-order echoes of the reflective surfaces,** per wall configuration, spacing and
   source:
   - **Angle:** is the reflection within 10 deg of the earliest distinct echo, or of any reflective echo?
   - **Lag:** is `gap_ms` within 0.25 ms of that echo's delay?
   - **Both at once:** the real test.
   - **Chance:** as `results/dechorate/report.md` computed it.
   - **The decided share:** reported with every score.
3. **Lag limit.** Keep `MAX_GAP_MS` at 12, Jay's limit: don't chase echoes beyond it. Report which labelled echoes fall
   outside the window, so a miss there isn't counted against the method.
4. **Place the wall.** Where angle and lag are both right, use the true source distance (a stand-in for the range the
   app doesn't have yet) with the direct angle, the echo angle and the lag. That gives the image source, and from it
   the reflecting wall's position. Report how far that lands from the real wall: this is the "it came off that wall"
   test.
5. **Then on people: LOCATA** (added 2026-10-23; Jay prefers human talkers to dEchorate's loudspeakers). Use batch A's
   LOCATA onsets and truth (`results/batchA/locata/truth.jsonl`, `harness/batchA/locata/`, the 160 and 80 mm pairs).
   LOCATA has no labelled echoes, but the floor echo's lag follows from the tracked head and the array's position:
   (path via the floor image - direct path) / c. Brief 10 computed it, with the mouth 0.12 m below the head marker.
   - **Lag:** is `gap_ms` within 0.25 ms of the floor echo's lag, or of the ceiling's or a wall's if the room's
     dimensions are in the release or the LOCATA paper? Chance as in step 2.
   - **Range from the echo:** the floor echo's lag shrinks as the talker moves away. Score whether `gap_ms` orders
     distance, as batch A scored its range cues: ordered right at 1.25x, 1.5x and 2x apart, and the spread at one
     spot. Put it beside the CDR's numbers from `results/batchA/locata/report.md`. This is the test of whether a
     geometric range cue exists at all with two mics.

Score under the rule above, and catalogue every read set aside. Commit `results/first_reflection/` and the harness to a
branch. Don't change Angle2's defaults.

---

# Batch A: why the angle locks onto a wrong direction, and can it tell when it has

Jay, 2026-10-22: "My problem for weeks has been the scheme I choose seems to lock on to the wrong angle. NOT the
reflection, just not correct." The goal is to render the limits of what the math can provide. Angle must be correct;
range only consistent (the same spot reads the same, and further reads further), as a person judges it. So, at the
moment of each read, using only what the math knows then, can it tell a bullseye from a miss?

Human talkers only for geometry. dEchorate's loudspeakers are a control at most.

**The shared spec, for briefs 9 and 10**

*Record per read*, from a harness-side runner. Don't change `src/schemes/`, and add nothing that feeds back into the
angle:
- **GccPhat:** angles 1-3 with share and width; the tie flag; the vote total after pause weighting; and its read at the
  first draw (43 ms), at 100 ms, at 250 ms and at the lock. Did it start right and drift, or start wrong?
- **Angle2's onset:** the read, `edge`, `first` and `at3`, and the second family.
- **Pause direction:** GccPhat's read of the 0.5 s before the onset, using the same `readSum`. That's whatever was
  sounding before the voice.
- **Signal clues:** the voice-over-pause level in dB, in the bands 300-1100 Hz, 1.1-3 kHz and 3-8 kHz.
- **Truth:** direction, distance, and the talker's facing where the data has it. Also every other active source in
  the cut, with its direction.

*Classify every wrong read:* off by more than 10 deg for the moderate class, and more than 36 deg for the outlier
class, per the scoring rule. A read can be several of these; report the overlaps:
- **Mirror:** read ≈ -truth.
- **End-fire pin:** |read| >= 85.
- **Pause direction:** within 10 deg of what was sounding before the onset (a steady source).
- **Another labelled source:** within 10 deg of one active at the time.
- **0 deg pull:** |read| < 6 while |truth| > 15.
- **Aliasing partner:** the read's delay and the truth's differ by one period of a frequency in the band, above c/2d,
  that carries a large share of the voice.
- **Truth was angle 2 or 3:** the right answer was in the scan, just not on top.
- **Drift:** the early read was right and the lock wasn't.
- **Facing:** the talker faced more than 120 deg away (where the data has facing).
- **Other.**

Give the catalogue per class with examples (file and time), so each class can be listened to.

*Range, alongside, without touching the angle:* a separate script and a separate output file, from the same cut
audio. The cues are the onset level (FiveMsAmplitude's 5 ms), the direction-free CDR per band
(`src/geonar/cdr_direct.py`), and the floor/ceiling echo lag within the first 12 ms. Score consistency, not metres:
- **Ordering:** the same talker, pairs whose true distances differ by 1.25x, 1.5x and 2x. Share correctly ordered.
- **Repeatability:** the same talker within 0.3 m of the same spot. Spread of the cue.

Score angle under the scoring rule at the top. Commit everything to a branch: no audio, but the truth and per-read
records so brief 11 can run from the repo alone.

**The plan: three agents in parallel, then one to join them**

| Agent | Brief | Asks | Data |
|---|---|---|---|
| 1 | 9 | Which wrong locks happen in many real rooms, and what each read knew at the time | STARSS23 development set, 16 rooms, real talkers |
| 2 | 10 | The same, at the phone's spacing, with tracked head facing and several talkers | LOCATA, DICIT 16 cm and 8 cm pairs, real talkers |
| 3 | 13 | Which cause produces which wrong lock, and its fingerprint in the clues | Human speech (EARS) placed by exact delays and by dEchorate's measured RIRs, one cause at a time |
| then | 11 | Match real wrong locks to causes, fix the top ones, choose commit-or-dim, run once on held-out data | Outputs of 9, 10 and 13, then the STARSS23 evaluation set |

Agents 1 and 2 find what goes wrong on real people. Agent 3 shows what each suspected cause looks like when it's the
only thing changed. Brief 11 joins them. Nobody changes `src/schemes/`: proposed fixes go into a copy under
`harness/` and are compared side by side.

**The record format, shared by 9, 10 and 13** (one JSON line per read, `reads.jsonl`, plus `truth.jsonl` without
audio):

    {"dataset", "scenario", "id", "pair_mm",
     "truth": {"deg", "dist_m", "facing_deg"|null, "others": [{"deg", "class"}]},
     "gcc": {"angles": [deg...], "shares": [...], "widths": [[lo,hi]...], "tie", "votes",
             "track": {"43": deg, "100": deg, "250": deg, "lock": deg}},
     "a2": {"deg", "edge", "first_ms", "at3_ms", "second_deg"},
     "pause_deg", "snr_db": {"mf", "hf1", "hf2"},
     "classes": [...], "cause": null | "<agent 3 knob and level>"}

Keep field names exact so brief 11 joins the three without translation.

## 9. Batch A on STARSS23 (16 rooms, real talkers)

DONE 2026-10-23: `results/batchA/starss23/report.md`. Over half of GccPhat's wrong speech locks (two-thirds of its
outliers) sit on another direction that was also sounding: the pause's or another labelled source's, at 2.5-3x chance.

Cut with `harness/starss23/starss_cut.py`, all six pairs. Record the speech onsets, and also the other classes' onsets
(footsteps, door, knock, phone and so on) under a separate label, since Stage 1 renders every sound. STARSS has no
facing truth. Truth for other active sources comes from the metadata frames around each onset. The array is a rigid
sphere: compare leans with `results/starss23/report.md` section 2, and don't call the sphere's lean wrong. Commit to
`results/batchA/starss23/`.

## 10. Batch A on LOCATA (one room, human talkers, tracked position and facing)

DONE in a 2026-10-23 cloud session: `results/batchA/locata/report.md`. Alone and facing the array, GccPhat never
missed; the other talker speaking during the read and facing away make the wrong locks. Only the CDR is a
consistent range cue. Don't start this one.

Data: https://zenodo.org/records/3630471, `dev.zip` (6.2 GB), plus `eval.zip` (13 GB) if its ground truth is
included. Use the tasks with human talkers and a static array: 3 (one moving talker) and 4 (several moving talkers).
Use the DICIT array's pairs at 16 cm (the phone is 15.7 cm) and 8 cm. Truth is the OptiTrack position and orientation
of each talker, and onsets come from each source's voice-activity record. The talker's facing relative to the array is
in the data, so the facing class is real here. With several talkers in task 4, the "another labelled source" class is
the multi-talker case. Commit to `results/batchA/locata/`.

## 11. After 9, 10 and 13: join, fix, choose commit-or-dim, then one held-out run

READY 2026-10-23: 9, 10 and 13 are merged to `main`. Two things they found that this brief must respect:
- **The two schemes agreeing isn't a safe confidence clue on its own.** Under a steady directional source or a
  common-mode signal, both lock onto the same wrong direction (lab, section 3), and Angle2's `edge` flag is set on those
  wrong onsets too. Test any rule that uses agreement or `edge` against the lab's coherent causes as well.
- **Facing is a real cause on LOCATA.** Alone and facing away, GccPhat is more than 10 deg off on 62% of reads. The
  phone has no facing truth at run time, so a rule may use only clues recorded at the moment of the read.

Read all three results.
1. **Attribute.** Match each real wrong lock from 9 and 10 to the cause whose fingerprint (from 13) it carries. Rank
   the causes by their share of wrong locks on real talkers, per dataset.
2. **Render each sound at its own onset, in a copy.** Jay (2026-10-23): "Don't outsmart it, just render it. If I'm in
   the middle of 'Friends, Romans, countrymen' and someone's cellphone dings, render it, and then back to me: 'Lend me
   your ears.'" So:
   - **No vetoes.** Don't skip a peak because it matches the pause or another source, and don't pick "the talker's"
     peak by rule.
   - **No source separation** (DUET or similar). Who is talking is diart's job, in Stage 2.
   - **The fix to test:** each onset gets its own read from its own first milliseconds, so a sound that starts later
     can't outvote it, and one that started earlier is read at its own onset instead of being summed in. The data
     says there's room: GccPhat's 43-100 ms read was right in 16 of LOCATA's 42 outliers, and 17% of STARSS23's wrong
     locks started right and drifted.
   - **Scoring:** every onset against its own source, speech and other sounds alike. A read of the ding at the ding's
     onset is right.

   Change a copy of the schemes under `harness/fixes/`; leave `src/schemes/` alone. Re-score 9's and 10's reads with
   the copy, and report every read that moved in or out of 10 deg.
3. **Commit or dim.** Choose the simplest rule (one or two thresholds on the recorded clues) on STARSS23, and test it
   untouched on LOCATA. Then the other way round. Plot the share of reads committed against the share of those within
   10 deg. A rule that works only where it was chosen is tuned, not general: say so.
4. **Range:** which cue is consistent in both datasets, and whether committing on the angle rule also picks reads whose
   range is consistent.
5. **Held-out exam, once.** Run the final schemes and rule on the STARSS23 evaluation set
   (https://zenodo.org/records/7880637, `mic_eval.zip`), which nothing so far has touched. If its labels aren't in
   the release, report that and stop. Report whatever comes out, with no tuning after the run.

Commit `results/batchA/report.md` to a branch.

## 13. Mechanism lab: which cause makes a wrong lock, and its fingerprint

DONE in a 2026-10-23 cloud session: `results/batchA/lab/report.md` (records in `results/batchA/lab/reads.jsonl.gz`).
Don't start this one.

Read HANDOFF.md, `results/angle2_pull.md`, `results/zero_deg/report.md` and the batch A spec above. The speech is
human (EARS, via `harness/dechorate/ears_fetch.py`). Only the placement is synthetic: exact fractional delays at
157 mm and 69 mm in free field, and dEchorate's measured RIRs (155 mm pair) in configuration 000000 (all absorbing)
and 011111 (all reflective). Don't derive geometry from the loudspeaker RIRs; they only carry the mechanisms.
Talker angles span -75 to +75 deg in 5 deg steps.

**Change one thing at a time.** For each setting, run both schemes unchanged and record in the shared format, with
`cause` set:
1. **A steady directional source** (pink noise, then a second voice) at a known angle, sounding through the pause and
   under the speech, from 30 dB below the voice to 0 dB. Does the read lock to it?
2. **A common-mode signal**, identical in both channels, at the same levels. The 0 deg pull.
3. **Diffuse noise** with the pair's true coherence, at the same levels.
4. **Spatial aliasing.** With no noise, find which talker angles produce aliasing-partner reads. Then vary the
   analysis band's low edge (300, 1100, 2000 Hz) in a copy of the schemes only, and say so.
5. **Late or early onset.** Hand the schemes an onset -50 to +150 ms off the true one.
6. **No pause history.** The same cuts handed to GccPhat without the pause before the onset, so its votes aren't
   weighted.
7. **A quiet voice.** The voice at 30, 20, 10 and 5 dB over a floor of capsule noise only.

**For each cause and level, report:**
- **Wrong-lock rate:** over 10 deg and over 36 deg, per scheme and angle band.
- **Fingerprint:** which recorded clues move with it (share, width, edge, agreement, pause direction, band SNRs) and
  by how much. That's what brief 11 uses to attribute real failures.
- **Who falls first:** the level at which each scheme starts losing reads.

Score under the scoring rule above. Commit `results/batchA/lab/` and `harness/batchA_lab/` to a branch.

---

# Orientation: head direction from two mics, on public data with real talkers

Context: Turi, Politis, Sudarsanam and Virtanen (Tampere) estimate speaker head orientation from one array in
https://arxiv.org/abs/2607.02129 (July 2026). They use the STFT phase of each channel in 4 ms windows, a deep network,
simulated training (pyroomacoustics plus 22 directivity patterns) and fine-tuning on the public Direction-of-Voice
dataset (Ahuja et al., UIST 2020, https://github.com/FIGLAB/DirectionOfVoice). On that real data, with 8 orientations
45 deg apart, trained on session 1 and tested on session 2 and the other way round, they report: DoV's own method
65.4%, theirs trained on real data only 62.6%, theirs pre-trained and fine-tuned 73.2%. They test no 2-mic
configuration, and say the model "still lacks strong generalization".

## 12. Direction-of-Voice with two of its four mics, and Jay's RotationTracker

Read HANDOFF.md and `src/orientation/RotationTracker.js`. That's Jay's tracker: a mel-band lateral cue against a
facing reference built from enrolment utterances. Its constants are frozen for holdout testing; don't retune
`cueScale` or the bands.

1. **Get the DoV raw dataset** from the links in the FIGLAB README. If its host is blocked by the network policy, report
   the domain and stop. Its ReSpeaker array's channels 1-4 are raw. Take the geometry from the ReSpeaker documentation
   and choose two pairs: the widest, and one adjacent.
2. **Reproduce the paper's real-data protocol exactly:** 8 classes, session 1 to 2 and 2 to 1, with accuracy as the
   paper defines it plus the mean angular error.
3. **Methods, each on the two-mic pairs only:**
   - **RotationTracker as written.** Build each participant's facing reference from that participant's 0 deg
     utterances in the training session. It estimates |sin(theta)| plus continuity, so report what it can and cannot
     resolve: front/back and left/right from a single utterance.
   - **A transparent baseline,** the same as RotationTracker but on per-band level differences, so readers can see what
     the hand-built cue adds.
4. **Report next to the paper's numbers** (65.4%, 62.6%, 73.2% on all channels), with the per-class confusion matrix,
   per distance (1, 3 and 5 m) and per room. State plainly that the comparison is two mics against their array.

Score under the scoring rule above, with outliers catalogued. Commit `results/orientation_dov/` and the harness to a
branch. No audio in the repo.

## 14. Orientation from which wall lights up

QUEUED for a later stage (Jay, 2026-10-22). Don't start this one yet. Built from scratch on purpose: Jay's earlier
version of this idea hit about 35% of the time in his living room and kitchen.

Jay's idea (2026-10-22): the talker under a microscope (raw audio, DFN masks) showed no repeatable rotation pattern.
What does change consistently as a talker turns is the reflections. Any room reduces to four walls, so the talker's
facing should be decidable at 0, 90, 180 and 270 deg.

**The physics, made precise.**
- **The directions don't move.** When a talker turns in place, the image sources (the reflections' directions and
  delays) stay put, because they depend only on where the talker stands and where the walls are.
- **The brightness does.** The mouth beams high frequencies forward (10-20 dB front to back above about 2 kHz), so the
  wall the talker faces returns a brighter echo.
- **Low frequencies are the yardstick.** They radiate nearly equally in every direction, so in each echo the ratio of
  high to low frequencies says how directly the mouth was pointed at that wall.
- **The cue:** among the early reflections, which one has the highest high-to-low ratio, measured against the direct
  sound's own ratio.

**The two-mic catch, to handle explicitly.**
- **Side walls** (perpendicular to the mic axis) put their echoes at clearly different angles.
- **Front wall, back wall, floor and ceiling** all mirror the talker without changing its offset along the axis. Their
  echoes read near the talker's angle and differ mainly in delay.
- **So "which wall" needs angle and lag together.** That's brief 8's problem: keep the 12 ms limit.

**Steps.**
1. **LOCATA, tasks 3 and 4** (human talkers, OptiTrack head orientation, static DICIT array, 16 cm pair; the data is
   on Zenodo 3630471, as in brief 10). Get the room's dimensions and the array's pose from the LOCATA documentation; if
   they're missing, say so and stop. For each speech onset, compute the first-order image sources from the talker's
   tracked position. Measure each image source's echo in the pair's signals at its predicted delay and angle. Speech
   isn't a click, so use a matched filter or the direct-sound-cancelled residual as `Angle2.readSound` does. Record
   each echo's level and high-to-low ratio (1.1-2 kHz against 4-8 kHz), relative to the direct sound.
2. **Predict the facing quadrant** relative to the room: the wall whose echo is brightest relative to the direct, with
   the direct-to-echo balance deciding "toward the array" against "away". Score it against the tracked head
   orientation as a 4-class accuracy (chance is 25%) plus a confusion matrix. Report it next to RotationTracker on the
   same onsets.
3. **Mechanism check on dEchorate.** Loudspeakers aren't heads, but sources 4 and 5 face walls with labelled echoes. Does
   the faced wall's echo come out brightest? A check, not a geometry result.
4. **180 deg is an odd one** (Jay). Score each onset against its own tracked orientation, never as a change from the
   previous one: a turn from 180 to 270 registers more energy change than the turn from 0 to 90. Report 180 deg
   separately, and normalise every echo against that onset's own direct sound.
5. **Where it breaks.** By talker distance from each wall, by angle, and by whether the faced wall is a side wall or a
   front/back wall: the two-mic catch above.

Score under the scoring rule, catalogue every set-aside read, and commit `results/orientation_reflections/` and
`harness/orientation_reflections/` to a branch.

---

# Stage 2 groundwork: diart and DFN on the same audio

Stage 1 stays first; these queue behind batch A.
- **Brief 15 (diart) is ready** once a Hugging Face token is stored as an environment secret, from an account that has
  accepted the user conditions for `pyannote/segmentation`, `pyannote/segmentation-3.0` and `pyannote/embedding`. Diart
  runs out of the box (`pip install diart`, its own defaults): that's what worked best for Jay, and every modified
  version did worse. Never commit model weights.
- **Brief 16 (DFN) is ready.** Jay's scripts in `dfn/` wrap the stock DeepFilterNet3 (`pip install deepfilternet`),
  so no fork is needed. Read `dfn/README.md` first: his findings there are the hypotheses to test.

Both briefs run on the same human-talker data as batch A, keyed by batch A's read `id`, and write separate files. They
add fields; they never change batch A's records.

## 15. Diart for multi-speaker: who is talking, and does pooling by voice give each talker's angle?

1. **Counting and attribution in rooms it hasn't seen,** at Jay's live latency (500 ms):
   - **Data:** LOCATA task 4 (several moving talkers, per-source voice activity, tracked positions), STARSS23 clips
     with overlapping speech, and AMI if it's reachable.
   - **Scoring:** diarization error, speaker-count error, missed and false speaker changes, plus how often one person
     is split into two voices and two people merged into one.
   - **Settings:** diart out of the box. Record the exact version and defaults it ran with; tune nothing.
2. **Input channel:** one raw capsule. If brief 16 has run, also try its DFN-enhanced capsule (a stand-in for the
   Android-processed stream). Does cleaning the voice help diart?
3. **Pooling by voice.**
   - Pool GccPhat's reads inside each diart voice's segments to get each voice's place, and score it against the
     tracked positions.
   - **Cross-talk:** while two voices overlap, compare the single read from the mix with each voice's pooled place.
   - **Voices to places:** how many voices map to one place, and how often one voice spans two.
4. **Diart as a whisper next to Jay's ears:** diart's speaker changes, snapped to the nearest onset by `attacks.py`'s
   rule, against the true onsets. Diart is never the clock.

Commit `results/stage2_diart/` and `harness/stage2_diart/` to a branch.

## 16. DFN's internals: a live speech gate, and why the mask helped the ghost

Read `dfn/README.md` and `dfn/dfn_shared.py`. Use the stock DeepFilterNet3 with Jay's shared operator: one model pass,
the same mask and deep filter on both channels, and the attenuation limit at 12 dB as the app ships. Run on batch A's
human-talker cuts (STARSS23, and LOCATA with its per-source voice activity), keyed by batch A's `id`.

1. **Level first.** Run every test twice: as recorded, and with one fixed gain per recording that brings active speech
   to about -26 dBFS. A fixed gain changes neither phase nor the ratio between channels; never use time-varying AGC.
   Report how much `lsnr` moves (Jay saw -5.4 to +3.3 dB on LOCATA).
2. **`lsnr` as a live speech gate.**
   - **Onsets:** when does it cross 0 dB, against the true speech onsets (LOCATA voice activity; STARSS labels at
     100 ms) and against `attacks.py`'s MF onset?
   - **False opens:** how often does it cross 0 dB in gaps, and on STARSS's non-speech classes (footsteps, door,
     knock, phone)? Stage 1 draws speech as a bubble and everything else as rings, so this is the switch.
   - **Latency:** measure DFN3's real look-ahead, and compare it with diart's 500 ms.
3. **The mask as a speech track:** replicate Jay's finding of a missed soft first word and opening on footsteps, with
   rates.
4. **Why mask-weighting helped the ghost.** The hypothesis to test: the L+R mixdown cancels the bands where the two
   channels are out of phase, so a mask computed from it under-weights those bands. What's left over-represents bands
   where the true delay and its aliasing partners line up. In a copy under `harness/fixes/`, weight GccPhat's votes by
   the mask computed from:
   - (a) the L+R mixdown
   - (b) one capsule
   - (c) no mask

   Count batch A's aliasing-partner, 0 deg pull and "other" classes for each, and every read that moves in or out of
   10 deg.
5. **The shared operator,** checked on real cuts: GccPhat on the DFN pair against the raw pair, read by read. Is the
   bearing preserved, as the math says it should be for a stationary talker?
6. **Clues for brief 11:** `lsnr` at the onset, and the mask's share of the band, as commit-or-dim clues.
7. **Cost:** processing time per second of audio, against the live budget.

Score under the scoring rule; commit `results/stage2_dfn/` and `harness/stage2_dfn/` to a branch.

## 17. Orientation from DFN run on each capsule separately

DROPPED (Jay, 2026-10-23): not worth crunching. Don't start this one. Step 3's single-channel cues (tilt, lsnr,
coh_drr against facing, with distance as a covariate) move into the orientation work when it comes off hold.

Jay's earlier attempt fed L and R into DFN as two separate streams
and compared what it kept in each, to read the talker's facing. It didn't work. This brief finds out whether it could
have, before spending more on it.

1. **Physics first, cheaply.** At 1, 2 and 4 m, the two capsules (157 mm apart) see the talker's mouth from directions
   about 9, 4.5 and 2.2 deg apart. Using a measured speech directivity (DirPat, which the Tampere paper also uses), predict
   the largest L-R difference in level per band that a turn of the head can produce across that spread, at every facing.
   Compare it with the capsules' own mismatch, measured on LOCATA's pauses. If the predicted difference is below the
   mismatch, report that the per-capsule split can't carry orientation at this spacing, and stop.
2. **Only if step 1 leaves room:** run DFN separately on each capsule of LOCATA's 16 cm pair (tasks 3 and 4, tracked
   head orientation). Take the per-band difference in mask and `lsnr` between L and R, and test it against the tracked
   facing, with distance held as a covariate.
3. **Either way:** test the cues that physics says do change with facing, on one channel: the mask's HF/LF tilt, `lsnr`,
   and the mask-weighted direct-to-diffuse ratio from `dfn/dfn_shared.py`'s `coh_drr`. Hold distance as a covariate.
   Render.html's note says the tilt tracked range, not facing, on LOCATA, so separating the two is the point.

Score under the scoring rule; commit `results/orientation_dfn/` to a branch.

---

# Stage 3/4 groundwork: linguistic context

Jay (2026-10-23): "Linguistic context is the way." A blind listener knows he's being addressed from his name, from
who answers whom, and from what's being said, not from which way the talker faces. With every word decoded (Jay's
raw-audio route into Android's SpeechRecognizer decodes all talkers, TV and radio included), the words themselves can
say who said what, and to whom. Head orientation, even if solved perfectly, is a permanent "maybe" for whatever sits
in front of someone.

## 18. AMI: who said what, and to whom, from the words

DRAFT, waiting on Jay: the Fisher model's name and source, and his labeling script that turns its two-speaker split
into 1-N speakers. Put the script in `harness/linguistic/` when he shares it. Don't start until this line is gone.

Data: the AMI Meeting Corpus (https://groups.inf.ed.ac.uk/ami/corpus/): real meetings of about four people, with
word-level transcripts that give every word's speaker and time. Check what the manual annotations hold before
relying on them: dialogue acts with an addressee on a subset of meetings, and focus of attention (where each person
looks) on a subset. If the AMI host is blocked by the network policy, try the Hugging Face copy (`edinburghcstr/ami`)
for transcripts and audio; if neither is reachable, report that and stop. Commit derived scores only, never audio.

1. **Who said what, from the words alone.** Cut each meeting into windows (2, 5 and 10 minutes). Strip the speaker
   labels and timing, keep the word order, and run Jay's pipeline.
   - **Score:** word-level speaker accuracy after the best one-to-one mapping of its labels to AMI's speakers, the
     number of speakers it finds against the number who spoke, and turn-boundary accuracy.
   - **Break it down** by the number of active speakers in the window (2 to 5), by overlap, and by short replies
     ("yeah", "mm-hmm"), which carry little context.
   - **Baseline:** everything to the window's most talkative speaker.
2. **The same with recognised text, if the audio is reachable.** Run Whisper on the far-field array mixdown, map its
   words to AMI's speakers by time, and repeat step 1. The gap between steps 1 and 2 is what recognition errors cost.
3. **To whom: words against facing.** On meetings with both addressee and focus-of-attention labels, predict each
   dialogue act's addressee two ways, then both together:
   - **Words:** names and vocatives, question-and-answer pairs, and who takes the next turn.
   - **Facing:** the annotated focus of attention of the speaker during the act.
   - **Score:** accuracy against the annotated addressee, split into "the group" and "one person", with chance for
     each.
   This is the direct test of the Tampere question: does facing add anything once the words are known?

Score in Jay's spirit: report every meeting, set aside meetings that fail outright to study separately, and catalogue
the failures by kind. Commit `results/linguistic/ami/` and `harness/linguistic/` to a branch.
