# STARSS23 harness: your bearing schemes, scored in 16 rooms you have never been in

Truth here comes from the dataset's optical tracker, not from you. Nothing to mark.

## 1. Download (on your machine; ~3.4 GB)
From https://zenodo.org/records/7880637 get `mic_dev.zip` and `metadata_dev.zip`. Unzip both into one folder, e.g.
`D:\starss23\` so you have `mic_dev\...\*.wav` and `metadata_dev\...\*.csv`.

## 2. Cut the speech
    pip install numpy scipy soundfile
    python starss_cut.py D:\starss23 --pair 1 2 --out cuts_12.jsonl

Takes every male/female speech event that is the ONLY active source for at least 1 s, cuts 0.5 s before its onset
to 1.0 s after, upsamples 24 kHz -> 48 kHz (your schemes assume 48 kHz), and records the tracker's azimuth,
elevation and distance plus the lateral angle that capsule pair should hear.

The MIC format is a 4-capsule tetrahedron, radius 4.2 cm (capsules at az/el 45/35, -45/-35, 135/-35, -135/35 deg,
per the DCASE task description). Any pair is ~6.9 cm apart -- less than half your phone's 157 mm, so expect coarser
angles and aliasing above ~2.5 kHz instead of ~1.1 kHz. Run more than one pair (`--pair 1 2`, `--pair 3 4`) to see
whether a result depends on the pair.

## 3. Run your schemes headless
    node run_schemes.mjs cuts_12.jsonl path\to\RangeMath > preds_12.jsonl

Imports your own `GccPhat.mjs` and `Angle2.mjs` unchanged and feeds them each cut exactly as the Conductor would
(read starts one 512-sample step before the onset).

## 4. Score
    python starss_score.py cuts_12.jsonl preds_12.jsonl

Per scheme: error by room, by |lateral angle| band, signed error (does it lean toward 0?), and the share of cuts
whose 2nd/3rd angle is the true one when the 1st is not. Both capsule signs are scored, because the pair's sign
convention vs yours is not something to assume; the right one will be obvious.
