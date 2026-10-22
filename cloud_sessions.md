# Cloud session briefs

One brief per Claude Code cloud session (claude.ai/code, repo jaysoma/DareDevil). Paste a brief as the session's first
message. The briefs don't depend on each other, so run them in parallel. Each session starts fresh: it knows only this
repo and the brief.

Prerequisites for every session:
- Code in the repo: `src/schemes/` (GccPhat, Angle2), `src/geonar/` (conductor and its modules), `harness/starss23/`.
- Network access in the environment that allows `zenodo.org`.
- The Claude GitHub App installed on this repo, so the session can push its results branch.

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
the first reflection. Don't start this one.

DONE in Jay's 2026-10-22 session: `results/dechorate/report.md`. v2.0's RIR file below can't be read; the run used
v1.0's `dechorate_rir_processed.hdf5` (https://zenodo.org/records/5562386). Don't start this one.

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
