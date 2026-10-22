# dEchorate harness: onset and first reflection, scored against measured RIRs

Clean speech is convolved with dEchorate's measured room impulse responses (one room, 11 wall configurations, 6 calibrated
sources, six 5-mic linear arrays). Each pair of capsules gets the direct-path delay and every first-order echo's direction
and delay as truth. Your schemes run unchanged. Findings: `results/dechorate/report.md`.

## 1. Data (outside the repo; never commit audio)
- From https://zenodo.org/records/5562386 (dEchorate v1.0): `dechorate_rir_processed.hdf5` (357 MB).
- From https://zenodo.org/records/6576203 (v2.0): `dEchorate_echo_notes.pkl` (calibrated mic and source positions) and
  `dEchorate_database.csv`. v2.0's `dEchorate_rirs_gzip7.hdf5` (4.2 GB) can't be read (see the report);
  `fix_superblock.py` repairs the first fault, but the second isn't repairable.
- Clean speech: `python3 ears_fetch.py DATA/ears` pulls 16 anechoic 48 kHz read sentences from 4 EARS speakers
  (github.com/facebookresearch/ears_dataset) using range reads, without downloading whole zips.

`pip install h5py numpy scipy soundfile` (plus `pyroomacoustics` only if you run the dataset's own scripts).

## 2. Run everything
    harness/dechorate/run_all.sh DATA DATA/ears WORK results/dechorate

For each wall configuration: `dechorate_cut.py` makes 1,728 cuts (6 sources x 6 arrays x 2 pairs x 24 speech
onsets), `run_schemes.mjs` runs `GccPhat` and `Angle2.readUtterance` on them, and only truth and predictions are kept.
Then `dechorate_score.py` writes `scores.json`, and `analyze.py` writes `tables.md` (measured truth) and
`tables_geometry.md` (the published geometry). Four cores take about 5 minutes.

## 3. Pieces
- `dechorate_cut.py`: cuts and truth. Pairs are mics 0-3 (155 mm, the phone) and 2-3 (65 mm, STARSS) of each array.
  Six capsules are wired with inverted polarity and are flipped back.
- `truth.py`: chooses the truth the scores use (the direct-path delay measured in the RIRs, by default).
- `echo_check.py`: how loud each surface's echo is in the measured RIRs, per configuration (`echo_check.json`).
- `safe_pickle.py`: loads the echo notes while allowing only numpy arrays to be rebuilt.
