# Batch A on LOCATA: wrong locks on real talkers, at the phone's spacing (2026-10-23)

Brief 10. One room, people walking and talking, with OptiTrack truth for every head's position and facing. Both schemes
in `src/schemes/` ran unchanged. Every read is in batch A's shared format (`reads.jsonl`), and every wrong one is
classified.

## What was run
- **Data:** LOCATA (https://zenodo.org/records/3630471), DICIT array.
  - Tasks 3 (one moving talker) and 4 (two moving talkers), dev and eval sets.
  - 16 recordings, 24 talker tracks.
  - The eval set's ground truth is in the release, so both sets are used.
- **Pairs:** mics 5-10 (160 mm, the phone is 157 mm) and mics 6-9 (80 mm). Both are centred on the array's middle mic.
- **Onsets:** where a talker's VAD turns on after at least 0.3 s of that talker's silence, inside the stretch the
  ground truth marks valid.
  - 341 onsets per pair: 55 from task 3, 286 from task 4.
  - Each onset is cut 0.5 s before to 1.0 s after, as a STARSS cut. The schemes are handed the VAD onset.
- **Truth:** the exact two-mic delay to the tracked head, in the schemes' own convention.
  - Every talker stays within ±75 deg, so every read is in scope. Only 2 reads fall at 60-75 deg.
  - Talkers walk: the truth moves a median 2.1 deg over GccPhat's half second (90th percentile 6.6 deg). The truth is
    taken at the onset.
- **Facing:** the head's `ref_vec` against the direction to the array (0 = facing it).
  - `ref_vec` is the facing: over the 24 talker tracks, while walking it sits a median 29 deg from the walking
    direction, and more than 135 deg off on only 1.1% of frames (`facing_check.json`). Head turns account for the rest;
    the worst track's median is 88 deg (eval task 4, recording 1, talker 2).
- **Checks:** the sign convention is right (median error 5.9 deg as computed, 43 deg flipped). GccPhat's lock, rebuilt
  in the harness to get its vote total, matches the stream on 682 of 682 reads. Angle2 gave no onset on 3 of 682.
- **Scoring:** Jay's rule (`harness/scoring/clean_score.py`, imported). A scenario is one recording, one talker, one
  pair.

## Headline, under Jay's rule

| pair | scheme | outliers set aside | scenarios dropped | kept | mean / median, kept | within 10 deg, kept |
|---|---|---|---|---|---|---|
| 160 mm | GccPhat | 42 of 341 (12.3%) | 0 of 24 | 87.7% | 7.5 / 5.2 deg | 83.3% |
| 160 mm | Angle2 | 64 of 339 (18.9%) | 0 of 24 | 81.1% | 7.0 / 4.8 deg | 82.2% |
| 80 mm | GccPhat | 35 of 341 (10.3%) | 0 of 24 | 89.7% | 7.3 / 5.2 deg | 81.4% |
| 80 mm | Angle2 | 61 of 340 (17.9%) | 0 of 24 | 82.1% | 7.5 / 5.4 deg | 75.6% |

- **The ranking:** on the reads both keep, the schemes are level at 160 mm (median 5.2 against 4.7 deg). Angle2 sets
  aside half as many reads again as GccPhat.
- **Before anything is set aside:** at 160 mm, GccPhat is off by more than 10 deg on 27% of reads and by more than
  36 deg on 12%. Angle2 is at 33% and 19%.

## 1. What makes a wrong lock here
Two things, both about the talker rather than the room. Wrong > 10 deg / > 36 deg, 160 mm:

| who else was talking | GccPhat, facing within 60 deg | GccPhat, facing away (> 120) | Angle2, facing within 60 | Angle2, facing away |
|---|---|---|---|---|
| nobody | **0% / 0%** (n=52) | 62% / 19% (n=16) | 2% / 0% (n=52) | 44% / 6% (n=16) |
| another talker, only in the pause before | 8% / 0% (n=25) | 56% / 0% (n=9) | 16% / 4% (n=25) | 44% / 22% (n=9) |
| another talker during the read | 21% / 14% (n=84) | 74% / 37% (n=27) | 38% / 31% (n=84) | 69% / 31% (n=26) |

`tables.md` has the 60-120 deg column and the 80 mm pair, which tell the same story.

- **Alone and facing the array, GccPhat never missed** (0 of 52 reads at 160 mm). That's the working machinery on
  real talkers.
- **The other talker, speaking during the read,** is the biggest source of outliers. In 195 of 341 onsets the other
  talker spoke for more than 20% of the half second. GccPhat's pause weighting can't help, because that voice isn't
  in the pause. Angle2 is hit harder: 31% of its reads are outliers even with the talker facing the array.
  A talker heard only in the pause before costs far less (GccPhat: no outliers), so the pause weighting does its job
  there.
- **Facing away:** even alone, 62% of GccPhat's reads are more than 10 deg off, though only 19% by more than 36 deg.
  With the direct sound turned away, the reflections take over.
- **Distance and angle matter less.** Error rises toward 45-60 deg (40% wrong, against 15% at 0-15 deg). Distance
  shows no steady trend: 15%, 35% and 26% wrong at under 1.5 m, 1.5-2.5 m and over 2.5 m.
- **Lean:** on kept reads GccPhat leans 3-4 deg toward 0 from 15 deg out. **On the clean reads it doesn't** (alone,
  facing within 60 deg: -0.6, +0.9, +0.1 and -1.9 deg by band, n = 5-17). The lean comes from blended reads, where
  the other talker or the room pulls the peak, not from a bias in the scheme. Angle2 is the same.

## 2. The class catalogue (in scope; a read can be in several classes)
Counts of wrong reads at 160 mm (moderate: 10-36 deg off; outlier: over 36 deg):

| class | GccPhat moderate (50) | GccPhat outlier (42) | Angle2 moderate (49) | Angle2 outlier (64) |
|---|---|---|---|---|
| another labelled source (the other talker) | 22 | 33 | 20 | 49 |
| pause direction | 20 | 30 | 26 | 47 |
| truth was angle 2 or 3 (Angle2: its second family) | 29 | 25 | 22 | 11 |
| drift (right at 43 or 100 ms, wrong at the lock) | 27 | 16 | - | - |
| facing away (> 120 deg) | 22 | 15 | 18 | 13 |
| 0 deg pull | 14 | 12 | 6 | 6 |
| mirror | 2 | 6 | 3 | 18 |
| aliasing partner | 0 | 0 | 0 | 1 |
| end-fire pin | 0 | 0 | 0 | 0 |
| other (none of the above) | 1 | 0 | 6 | 3 |

- **"Pause direction" and "another source" are mostly the same event:** the other talker was talking just before the
  onset, so the pause read points at them. Most common outlier overlaps:
  - Angle2: another source + pause direction (18), plus mirror (9).
  - GccPhat: another source + drift + pause direction + truth was angle 2 or 3 (6).
- **GccPhat often had it and lost it:** drift appears in 16 of its 42 outliers. The first 43-100 ms pointed at the
  talker, then the half second filled with the other voice. In 25 of the 42, the right answer was still in the scan
  as angle 2 or 3.
- **Two classes are empty, unlike STARSS:** no end-fire pins and almost no aliasing partners at either spacing. The
  pins on STARSS came from the sphere, and DICIT is free-field.
- **Listenable examples** (file and time) for every class are in `summary.json` under `catalogue`, up to 5 per class.
  - GccPhat, the other talker: dev/task4/recording1, talker 2 at 15.31 s (truth -26.5 deg, read +42.5 deg).
  - GccPhat, 0 deg pull: dev/task4/recording2, talker 2 at 14.34 s (truth -44.3 deg, read +1.4 deg).
  - Angle2, mirror: dev/task3/recording2 at 18.12 s (truth +22.8 deg, read -17.5 deg).
  - The full set-aside catalogue is in `locata_<pair>_outliers.jsonl`.

## 3. Could it tell, at the moment of the read? (a preview for brief 11)
This is the AUC of each clue for telling a read within 10 deg from a miss, 160 mm (0.5 = no information). Brief 11
chooses the rule; this only shows where the signal is.

| clue | for GccPhat's read | for Angle2's read |
|---|---|---|
| GccPhat share margin, angle 1 - angle 2 | **0.72** | 0.66 |
| GccPhat share, angle 1 | 0.70 | 0.64 |
| GccPhat 43 ms read agrees with the lock | 0.68 | 0.62 |
| Angle2 agrees with GccPhat | 0.62 | **0.73** |
| read away from the pause direction | 0.63 | 0.47 |
| votes after pause weighting | 0.59 | 0.67 |
| band SNRs (300-1100 Hz, 1.1-3 kHz, 3-8 kHz) | 0.55-0.57 | 0.60-0.64 |
| GccPhat width / tie | 0.53 / 0.57 | 0.50 / 0.54 |

The best single clues are moderate (0.70-0.73), and each tracks the classes above. A blended scan has a low margin
between angles 1 and 2; drift shows as the 43 ms read disagreeing with the lock; and Angle2 is right mostly when it
agrees with GccPhat.

## 4. Range, alongside (consistency, not metres)
These are the same talker in the same recording, as pairs of cuts whose true distances differ by the given ratio. The
spread is between cuts within 0.3 m of the same spot.

| cue (160 mm) | ordered right: 1.25x | 1.5x | 2x | spread at one spot | step at 2x |
|---|---|---|---|---|---|
| direction-free CDR (`cdr_direct.py`), 0.5 s | 57% | 62% | **78%** | 1.3 dB | 2.5 dB |
| onset level, 5 ms (FiveMsAmplitude) | 51% | 54% | 54% | 8.4 dB | 9.9 dB |
| echo lag within 12 ms (cepstrum) | 56% | 60% | 51% | 1.5 ms | 1.8 ms |

At 80 mm the CDR orders 71% of 2x pairs, with a spread of 0.9 dB against a 1.7 dB step.
- **Only the CDR is a consistent range cue.** It orders 78% of 2x steps, and its spread at one spot is about half the
  step it has to resolve. Below 1.5x it's close to chance.
- **The 5 ms onset level isn't one.** It's at chance, and its spread at one spot (8 dB) is as large as a doubling of
  distance (10 dB). Talkers turn their heads and start words at different levels.
- **The cepstral echo lag doesn't measure the floor echo.** It lands within 0.25 ms of the floor echo's geometric lag
  on only 6% of cuts; voiced speech puts its pitch period in the same 2.5-12 ms range. Getting a floor-echo lag needs
  the direct sound cancelled first, as `Angle2.readSound` does, and that's brief 8's subject.

## For brief 11
- **The record format:** `classes` is one flat list of `"<scheme>:<name>"` strings (`gcc:` or `a2:`). Each wrong read
  carries its severity (`moderate` or `outlier`) plus every class that fits. `cause` is null throughout.
  `truth.jsonl` adds what the shared record doesn't hold: which talker, the head position, how far the truth moved,
  and when each other talker spoke (`before` and `during`, shares of each half second).
- **The two causes to fix first,** on this data:
  1. Another voice inside the read. That needs separation or a shorter read: GccPhat's early reads were right in 16
     of its 42 outliers.
  2. The talker facing away. That needs a dim, not a fix: alone and facing away, a read is wrong more often than right.

## Caveats
- **One room, and few onsets in task 3:** that talker speaks almost without pause. 88 onsets have nobody else talking,
  52 of them facing the array, so the cleanest cells are small.
- **The onset is LOCATA's VAD, not the Conductor's ears.** Angle2's onset family starts a median 12 ms before it.
- **Truth is the head marker.** The mouth is a few cm in front of it, which is under 2 deg at these distances.
- **The echo-lag geometry assumes the mouth is 0.12 m below the marker.** Every 5 cm of error there moves the
  expected lag by about 0.1 ms, far short of the 1.7 ms median gap.

## Files
- **Records:** `reads.jsonl` (the shared record) and `truth.jsonl` (truth without audio). Everything re-runs from these.
- **Scores:** `summary.json` (Jay's rule per pair, the class catalogue with overlaps and examples, the checks) and
  `locata_<pair>_summary.json`, `_scenarios.json` and `_outliers.jsonl` (`clean_score.py`'s outputs).
- **Range:** `range.jsonl` and `range_summary.json`.
- **Checks and tables:** `facing_check.json` and `tables.md` (every table, both pairs).
- **Rebuild:** `harness/batchA/locata/run_all.sh` (see its README). The data is fetched by `locata_fetch.py`.
