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
