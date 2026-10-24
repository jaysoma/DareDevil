# Rotation briefs, for local agents (2026-10-24)

Three independent crunches on Jay's rotation walks, one agent each. They share inputs and never write the same file.

## Setup (once, from the DareDevil clone)
```
git pull
git worktree add ../dd-colour -b rotation-colour
git worktree add ../dd-blur   -b rotation-blur
git worktree add ../dd-campp  -b rotation-campp
```
Then one terminal per folder: `cd ../dd-colour`, start the agent, and say: **"Do harness/rotation/briefs/A_colour.md."**
(B_blur.md in dd-blur, C_campp.md in dd-campp.) Each pushes its own branch; merge when its report is in.

## Rules for every brief
- **Write only inside your own folders:** `harness/rotation/<topic>/` and `results/rotation/<topic>/`. Don't edit
  `src/`, `library.json`, `results/INDEX.md`, `harness/rotation/facing_stops.json` or another brief's folders.
- **Scope:** rotation only. Not range, not angle. Don't reach for a finished app feature; measure.
- **Outliers:** set obvious ones aside, say how many and why, and give means of the rest. No medians as headlines.
- **Lead with what held,** then the limits. Plain sentences; numbers with their n.
- **Questions for Jay:** at most three at a time, batched, each naming the walk and the time span. Find what you can
  in the files first: decodes are `tapes/<walk>/transcript.json`.
- **Keep tool output lean:** print summaries, not arrays.

## Shared inputs
- **Audio:**
  - **In the repo:** the 10 labelled walks, `tapes/<walk>/<walk>.raw` (s16le, 2 channels, 48 kHz, no header) or
    `.wav` (030615, 221126: read with soundfile).
  - **The other 13 rotation walks:** on Jay's box at `<root>/Dictate/captures/geonar/tapes/` (see each walk's
    `audio-input.json`).
  - **Spacing:** 157 mm. walk-161331 is folded to 90 deg: 111 mm.
- **Labels:** `harness/rotation/facing_stops.json`. Stops at one spot and one called facing, unsigned (0 = facing
  the phone, 90 = side, 135, 180 = away), with spans and the spot's called distance. A stop runs from its callout to
  the next.
- **Distance ladders (facing the phone, called distances):** `LADDERS` in `harness/rotation/facing_vs_distance.py`.
- **The estimator:** `src/geonar/cdr_direct.py`, `cdr_free_bands` (direction-free CDR; NFFT 2048, hop 512, PSD
  smoothing 0.92). It floors bands at c/2d = 1.1 kHz on the phone, so anything lower must be run unfloored and
  flagged as ill-conditioned. `harness/rotation/band_windows.py` shows it summed in 0.5 s windows.
- **What's known (the bar):** `results/rotation/facing_pooled.md`.
  - **At one spot,** pooled over a stop (about 7 s of speech), CDR 4-8 kHz minus CDR 0.1-1.1 kHz reads lower
    turned away at 9 of 9 spots (−3.1 dB) and to the side at 15 of 16 (−2.1 dB).
  - **The CDR's range statistic** reads 3.5-4 dB lower once turned.
  - **The level's own tilt** jitters 8.7 dB per half second and fails.
  - **Against a single opener stop,** balanced accuracy is only 61%.
  - **Distance moves the contrast** about −3 dB per decade.
- **Context:** brief 20 (`results/range_facing/report.md`) found the facing cue real on LOCATA but drowned by
  per-read jitter. Jay's demo puts a hardcover book against the phone's back, and talkers turned past 120 deg are to
  fade out.
