# DareDevil handoff (2026-10-22)

For whoever picks this up next: a new Claude session, or Jay. Read this first, then `agent_task_truth_recovery.md`.

## The project
A live app that renders what a 2-mic array "hears": a Galaxy Z Flip4, unfolded, suspended in clips at 1.5 m, top and
bottom capsules 157 mm apart, 48 kHz raw (UNPROCESSED) capture. The goal is the blind-person problem: place human
talkers by speech, the way a binaural listener would. If the array hears one utterance from two directions (direct
plus reflection), it renders both. It will be demoed to researchers in a room Jay has never recorded in, so the
methods must generalise beyond his house.

- **Angle:** about 75% (his estimate). Front 180 deg only; the extremes beyond roughly +-60 deg are out of scope.
  A recurring 0 deg mystery.
- **Orientation:** about 60%. Only near-facing; anything without line of sight is discarded.
- **Range:** given up in absolute terms. Relative units anchored on the opening utterance ("Activate DareDevil mode!")
  are the intended form; no unit callouts.

## The pipeline (JavaScript, strict four-layer separation, no bounces)
`conductor.py` (v12) directs and holds no math. It finds onsets with its own ears (`attacks.py`: MF 300-1100 Hz decides
WHEN; HF decides WHERE), streams each utterance's raw audio to a bearing scheme from one 512-sample step before the
onset, with 20 x 512 samples of pause history, and streams CDR frames to range. Bearing schemes are drop-in `.mjs`:
- **GccPhat.mjs:** textbook GCC-PHAT summed over the first half second, 300 Hz-8 kHz, each slice weighted by the voice
  over the pause; reports angles 1-3 with widths.
- **Angle2.mjs:** `readUtterance` is the one Jay settled on (the "30-second accumulation" scheme): 3 ms windows 1 ms
  apart, 1.1-8 kHz; the first direction to recur 3 times is the onset, the next the first reflection.
- Range: `FiveMsAmplitude.js` (1 / amplitude of the first 5 ms). Orientation: `RotationTracker.js` (mel-band lateral
  cue against a facing reference).

## Done this session
1. **Truth recovery for the 29 house tapes** (repo `jaysoma/DareDevil`, all JSON, no audio). Results are in
   `geonar-truth-results.zip`, delivered to Jay and not yet committed (GitHub is not linked to the session).
   - 7 tier-A, 23 tier-B and 122 tier-C stops. Poses were checked against ODAS only, never against Jay's schemes.
   - walk-203939 is a fifth placement: left of the TV, facing 0.
   - walk-111830's capsule flip shows in the data.
   - Jay answered the pose questions on 2026-10-22 ("recollection" in the files).
2. **ODAS hears 0 deg in silence** on every phone placement: 47% of active pause directions fall within 6 deg of 0,
   pose-independent, so the cause is common to both capsules rather than the room. Top suspect: low-frequency diffuse
   noise, coherent at zero lag across 157 mm (ODAS ran with `ssl_hp_hz` 0).
3. **Inward lean:** in 5 of the 6 tier-A stops checked, the measured bearing is smaller in magnitude than predicted.
4. **STARSS23 harness** (`starss23-harness.zip`, also in `/home/claude/starss/`). Steps: cut single-talker speech
   onsets, run the schemes unchanged, score against the optical tracker.
   - Synthetic plane-wave test: GccPhat is within 0.5 deg on every cut.
   - Angle2.readUtterance pulls toward 0 even with no room (-28 reads -19.5, 24.6 reads 8.3). The method contributes to
     the inward lean. Suspect: `U_AGREE = 3` samples is a fixed delay tolerance, a large share of a short pair's range.

## In progress at handoff
STARSS23 (DCASE 2024 Task 3) on real audio, in this cloud session. Network access was opened to Zenodo on 2026-10-22.
- Metadata downloaded: 168 label files, 1,428 single-talker speech onsets across 16 rooms.
- `mic_dev.zip` (3.4 GB) downloading to `/home/claude/data/starss23/` at about 4 MB/s.
- Then:
  - `python3 starss_cut.py /home/claude/data/starss23 --pair 1 2 --out cuts_12.jsonl` (repeat for `--pair 3 4`)
  - `node run_schemes.mjs cuts_12.jsonl schemes > preds_12.jsonl`
  - `python3 starss_score.py cuts_12.jsonl preds_12.jsonl`
- STARSS's MIC format is a tetrahedron of radius 4.2 cm: any capsule pair is about 69 mm apart, not 157 mm. Compare
  across rooms and pairs; don't read the absolute error as the phone's.

## Next
1. Read the STARSS23 report. Questions it answers:
   - Does each scheme's error hold across 16 rooms (general) or vary by room (tuned)?
   - Does it lean toward 0 in real rooms beyond what the synthetic test shows?
   - Is angle 2 or 3 right when angle 1 is wrong?
2. Fix or explain Angle2's synthetic inward pull (start with `U_AGREE` scaled to the pair spacing), then re-run.
3. dEchorate (Zenodo 6576203; annotations already pulled from GitHub): measured RIRs in 11 wall configurations with
   labelled first-order echoes. This is truth for the onset and first-reflection claims.
4. Unsupervised use of the house tapes: within each stop, the direction recurring on every utterance is the talker and
   directions recurring at a fixed offset are reflections. No markings needed.
5. The 0 deg cause: re-run ODAS with a high-pass (e.g. 300 Hz) and compare the share of 0 deg in pauses.

## Working with Jay
- Peer-level, direct; pushback welcome; quiz him on his own code.
- Ask few questions, batched, in chat, naming the walk and time slice. He objects to supplying answers the agent should
  find. Prefer data with independent truth (STARSS23, dEchorate) over hand-marked house truth.
- He wants a general method for rooms he has never been in, not fits to his house.
