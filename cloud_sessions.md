# Cloud session briefs

One brief per Claude Code cloud session (claude.ai/code, repo jaysoma/DareDevil). Paste a brief as the session's first
message. The briefs don't depend on each other, so run them in parallel. Each session starts fresh: it knows only this
repo and the brief.

Prerequisites for every session:
- Code in the repo, at `src/` (conductor, attacks, schemes) and `harness/starss23/`.
- Network access in the environment that allows `zenodo.org`.
- The Claude GitHub App installed on this repo, so the session can push its results branch.

---

## 1. STARSS23 real-audio run

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

Read HANDOFF.md, then `src/schemes/Angle2.mjs`. In the synthetic plane-wave test, `readUtterance` pulls toward 0 deg
(-28 reads -19.5, 24.6 reads 8.3). The suspect is `U_AGREE = 3`, a fixed delay tolerance in samples, which is a large
share of a short pair's lag range.

1. Reproduce the pull at 69 mm and at 157 mm.
2. Make the tolerance scale with the pair spacing (for example, a fixed fraction of the maximum lag), or find the
   real cause.
3. Re-run the synthetic sweep from -60 to +60 deg in 2 deg steps.

Change Angle2 only, never GccPhat. Commit the fix and `results/angle2_uagree.md` with a before/after table to a branch.

## 3. dEchorate onset and first-reflection truth

Read HANDOFF.md. From https://zenodo.org/records/6576203, download `dEchorate_rirs_gzip7.hdf5`,
`dEchorate_database.csv`, `dEchorate_echo_notes.pkl` and `main_geometry_from_echo_calibration.py` (about 4.2 GB
total). Skip the speech, babble and noise files.

For each wall configuration and source, pick mic pairs, convolve clean speech with the measured RIRs, and run
`Angle2.readUtterance` and `GccPhat`. Score the onset direction against the direct-path TDOA, and the "first
reflection" against the labelled first-order echoes. Report hit rates by wall configuration.

Commit `results/dechorate/report.md` to a branch.

## 4. The 0 deg peak in silence, on independent data

Read HANDOFF.md, item 2 of "Done". ODAS puts 47% of active pause directions within 6 deg of 0, and the top suspect is
low-frequency diffuse noise that is coherent at zero lag. Test this on STARSS23 pause segments, with no speech active
per the labels. Measure the share of GCC-PHAT peaks within 6 deg of 0 at high-pass 0, 100, 300 and 1100 Hz, for each
pair and room.

If the 0 deg share collapses with the high-pass, the mechanism is general and not the phone's. Commit
`results/zero_deg/report.md` to a branch.
