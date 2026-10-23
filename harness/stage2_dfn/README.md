# Brief 16: DeepFilterNet3's internals on batch A's human-talker data

The stock DeepFilterNet3, run with Jay's shared operator (`dfn/dfn_shared.py`), on every STARSS23 development
recording (capsule pairs 1-2 and 3-4) and every LOCATA recording batch A read (tasks 3 and 4, 160 and 80 mm). It is keyed
by batch A's read `id`. Findings: `results/stage2_dfn/report.md`.

## 1. Environment
deepfilternet 0.5.6 needs torch 2.0 and torchaudio 2.0 (it imports `torchaudio.backend`) and numpy < 2. It runs in its
own venv:

    uv venv -p 3.11 DFNENV && VIRTUAL_ENV=DFNENV uv pip install "torch==2.0.1" "torchaudio==2.0.2" deepfilternet "numpy<2" scipy soundfile

The model's own download (github.com/Rikorose/DeepFilterNet/raw/...) may be blocked by a network policy. The same
file is at
`https://raw.githubusercontent.com/Rikorose/DeepFilterNet/main/models/DeepFilterNet3.zip` (sha256 49c52edc...84d2):
unzip it into `~/.cache/DeepFilterNet/`.

## 2. Data
- **STARSS23:** `mic_dev.zip` and `metadata_dev.zip` from https://zenodo.org/records/7880637, unzipped into one folder.
- **LOCATA:** `python3 harness/batchA/locata/locata_fetch.py LOCATA_DIR`.

## 3. Run
    harness/stage2_dfn/run_all.sh DFNENV STARSS_DIR LOCATA_DIR WORK results/stage2_dfn

On 4 cores this takes about 3 hours. Work holds frames, predictions and clues; cuts are deleted as soon as they're read.

| step | script | writes |
|---|---|---|
| one job per recording and pair, with batch A's reads | `build_jobs.py` | `WORK/jobs.jsonl` |
| DFN over each whole recording, at both levels; GccPhat on each read's variants | `dfn_pass.py` -> `run_gcc.mjs` | `WORK/frames`, `preds`, `clues`, `attacks`, `cost` |
| the tests | `analyze.py` | `summary.json`, `tables.md`, `reads.jsonl.gz` |

`harness/fixes/GccPhatMask.mjs` is the only scheme copy. It is `src/schemes/GccPhat.mjs` with one added option,
`voteMask`: a weight per frequency slice, multiplied into the pause weights. It is not shipped.

## 4. Choices worth knowing
- **The 12 dB attenuation limit** is applied as the stock `enhance()` applies it, `lim * noisy + (1 - lim) * enhanced`,
  on both channels. `dfn_shared.py` passes the limit to `model.mask` instead. That clamps only the mask, not the
  deep-filter band below 4.8 kHz. Its help text describes the blend.
- **Level `norm`:** one gain per recording and pair, putting the mixdown's rms over labelled speech at -26 dBFS.
  STARSS23 uses its speech classes; LOCATA uses any talker's VAD.
- **Long recordings** run in 60 s pieces, each started 30 s early. A whole 9-minute pass needs over 7 GB of memory.
  5 s of warm-up wasn't enough: on a quiet recording DFN's state stayed up to 30 dB apart for 5 s. With 30 s, 3 of
  12,910 frames differ by more than 0.5 dB.
- **Frame k** of DFN's 10 ms grid is centred on sample 480 k.
- **Test 4's single-capsule mask** comes from a second DFN pass on capsule L alone.
