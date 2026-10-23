# Batch A on STARSS23: why the angle locks onto a wrong direction (brief 9, 2026-10-23)

Jay: "the scheme I choose seems to lock on to the wrong angle. NOT the reflection, just not correct." This is the
STARSS23 half of batch A. It covers every onset in 16 real rooms, which wrong locks happen, and what each read knew at
the moment it was made. Brief 11 joins it with LOCATA (10) and the mechanism lab (13).

## What was run
- **Data:** STARSS23 development set, MIC format (https://zenodo.org/records/7880637), all 6 capsule pairs (68.5-68.8
  mm). Truth is the optical tracker: direction and distance at each onset, plus every other labelled source active from
  0.5 s before to 0.5 s after it.
- **Every onset of every class:** 7,498 per pair, 44,988 reads in all.
  - **Speech:** 35,808 reads, of which 8,562 are speech alone (the old single-talker set, plus 30 onsets the old cutter
    lost to duplicated metadata rows).
  - **Other sounds:** 9,180 reads. Laughter is 4,338 of them, then footsteps, instruments, doors, clapping, bells,
    telephones, music, water and knocks.
- **Schemes:** `src/schemes/` unchanged (GccPhat and Angle2 as on main), fed as the Conductor feeds them. The runner
  records the shared batch A record per read.
- **Facing:** STARSS has no facing truth, so the facing class is empty.
- **Harness:** `harness/batchA/starss23/`.

**Checks:**
- **Every one of the 8,532 earlier single-talker reads reproduces exactly, for both schemes.** That's against
  `results/starss23/`.
- **The harness copy of GccPhat's sum matches the stream's lock on 100% of reads.** It supplies the vote total, the
  pause read and the band SNRs.
- **No read:** GccPhat has no lock on 42 reads, and Angle2's `readUtterance` gives no read on 1,888 (4.2%).

### The sphere reference
STARSS's capsules sit on a rigid sphere, and the sphere reads every bearing wider than the geometric angle
(`results/starss23/report.md`, section 2). Brief 9: don't call that wrong. So each read is judged against what the same
scheme reads from the same direction through the sphere alone, with no room: `truth.sphere_deg`, interpolated from a
5 x 10 deg grid of sphere-only reads (`sphere_grid.py`).

**Checking the grid:**
- **Against the exact per-direction simulation** (`harness/starss23/analysis/sphere_sim.py`) on 600 real cut
  directions, it agrees within 0.1-0.4 deg median in every band except 45-60 deg on pair 1-2 (2.2 deg).
- **Against the sphere reference, the kept reads' mean lean is -0.7 to +2.3 deg in every band.** Against the geometric
  angle it is +0.4 to +11.7. So the reference takes out the sphere's lean and little else.

**The earlier report's lean table** (solo speech, pairs 1-2 and 3-4, median, against the geometric angle):

| \|truth\| | 0-15 | 15-30 | 30-45 | 45-60 | 60-90 |
|---|---|---|---|---|---|
| GccPhat, real rooms (this run) | +2.0 | +1.6 | +5.4 | +18.7 | +26.8 |
| GccPhat, real rooms (report section 2) | +1.7 | +1.6 | +5.4 | +19.0 | +26.8 |
| GccPhat, sphere alone (grid) | +0.6 | +1.0 | +5.5 | +14.5 | +21.2 |
| GccPhat, against its sphere reference | +0.3 | -1.0 | -0.6 | +1.2 | +6.0 |
| Angle2, real rooms | +2.4 | +0.7 | +2.6 | +10.5 | +14.3 |
| Angle2, sphere alone (grid) | +0.8 | +1.4 | +5.1 | +13.5 | +20.0 |
| Angle2, against its sphere reference | +0.8 | -1.3 | -1.7 | -3.7 | -3.0 |

GccPhat's lean is the sphere's. Angle2 still sits a few degrees inside its sphere reference from 30 deg out: the remains
of the room pull that brief 2 cut by two-thirds.

## 1. The score under Jay's rule
The rule in `results/clean/report.md`: |reference| <= 75 deg; reads off by more than 36 deg set aside; a room-and-pair
scenario averaging over 22.5 deg, or losing over half its reads, dropped whole. Against the sphere reference:

| | reads in scope | set aside (> 36 deg) | scenarios dropped (of 96) | kept | mean | median | within 10 deg |
|---|---|---|---|---|---|---|---|
| **Speech, all:** GccPhat | 30,710 | 17.2% | 2 | 82.3% | 9.5 | 6.4 | 65.2% |
| Angle2 | 30,141 | 23.3% | 3 | 75.5% | 11.0 | 8.2 | 57.0% |
| **Speech alone:** GccPhat | 7,393 | 7.0% | 1 | 92.8% | 8.4 | 5.5 | 69.7% |
| Angle2 | 7,434 | 12.5% | 1 | 87.2% | 9.8 | 7.1 | 61.9% |
| **Speech, another source active:** GccPhat | 23,094 | 20.6% | 2 | 78.9% | 9.8 | 6.7 | 63.8% |
| Angle2 | 22,506 | 26.9% | 3 | 71.8% | 11.5 | 8.6 | 55.0% |
| **Other sounds:** GccPhat | 7,675 | 25.0% | 1 | 75.0% | 10.1 | 6.8 | 62.6% |
| Angle2 | 7,422 | 24.0% | 2 | 75.2% | 10.3 | 7.3 | 61.3% |

- **Dropped scenarios:** room 2 pair 2-4 and room 23 pair 3-4 for GccPhat on all speech; room 2 pairs 1-4 and 2-4 and
  room 22 pair 1-4 for Angle2.
- **Against the geometric angle,** GccPhat on all speech keeps 80.7% at 11.2 / 8.2 deg and 56.7% within 10. All numbers
  are in `summary.json` under `score`.
- **The single-talker set the earlier reports scored is the easy fifth.** Speech with another source active is 75% of
  all speech here. It loses 2.5-3x as many reads to the outlier rule (20.6% against 7.0% for GccPhat).
- **GccPhat leads Angle2 on speech in every subset.** On other sounds the two are level.

**By room** (GccPhat, all speech, median error against the sphere reference, share within 10 deg):

| room | 2 | 4 | 6 | 7 | 8 | 9 | 10 | 12 | 13 | 14 | 15 | 16 | 21 | 22 | 23 | 24 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| median | 17.8 | 9.8 | 6.7 | 6.6 | 8.2 | 12.2 | 4.7 | 8.9 | 6.1 | 5.2 | 4.2 | 6.2 | 12.2 | 14.4 | 17.2 | 8.9 |
| within 10 | 29% | 51% | 63% | 67% | 55% | 41% | 69% | 53% | 62% | 69% | 73% | 61% | 45% | 40% | 31% | 53% |

## 2. Which wrong locks happen
A wrong read is off its reference by more than 10 deg: moderate up to 36 deg, an outlier beyond. A read can be in several
classes. All shares below are of the wrong reads in scope.

**Class definitions** (in `classify.py`):
- **Pause direction:** within 10 deg of GccPhat's read of the 0.5 s before the onset, that read being a different
  direction from the talker (more than 10 deg away).
- **Another labelled source:** within 10 deg of another labelled source active around the onset, that source more than
  10 deg from the talker.
- **Aliasing partner:** the delay error is one period of a frequency above c/2d (2.5 kHz) whose third-octave band holds
  at least 5% of the voice.
- **Chance:** the same test with the pause, the other sources or angles 2-3 taken from a random cut of the same room and
  pair.

**GccPhat, speech:** 30,710 reads in scope; 8,900 moderate and 5,282 outliers, so 14,182 wrong.

| class | moderate | outlier | share of wrong | chance | the only class |
|---|---|---|---|---|---|
| pause direction | 3,079 | 2,720 | 40.9% | 16.1% | 1,225 |
| another labelled source | 2,475 | 2,722 | 36.6% | 15.1% | 786 |
| **either of those two** | | | **53.7%** (67.4% of outliers) | | |
| drift (right at 43 ms, wrong at the lock) | 1,636 | 804 | 17.2% | | 880 |
| truth was angle 2 or 3 | 257 | 2,104 | 16.6% | 12.4% | 300 |
| end-fire pin | 911 | 1,309 | 15.7% | | 863 |
| 0 deg pull | 543 | 406 | 6.7% | | 154 |
| mirror | 322 | 538 | 6.1% | | 133 |
| aliasing partner | 0 | 95 | 0.7% | | 13 |
| other | 3,140 | 544 | 26.0% | | 3,684 |

**Angle2, speech:** 30,141 in scope; 10,049 moderate and 7,026 outliers.

| class | moderate | outlier | share of wrong | chance | the only class |
|---|---|---|---|---|---|
| pause direction | 2,933 | 2,791 | 33.5% | 13.9% | 1,436 |
| another labelled source | 2,545 | 2,833 | 31.5% | 14.2% | 1,211 |
| **either of those two** | | | **45.4%** (53.1% of outliers) | | |
| truth was its second family | 1,106 | 1,600 | 15.8% | 10.7% | 943 |
| end-fire pin | 659 | 1,235 | 11.1% | | 936 |
| 0 deg pull | 726 | 537 | 7.4% | | 358 |
| mirror | 404 | 880 | 7.5% | | 460 |
| aliasing partner | 0 | 90 | 0.5% | | 18 |
| other | 4,669 | 1,552 | 36.4% | | 6,221 |

The other sounds rank the same way. For GccPhat: pause direction 39.9% (chance 14.9%), another labelled source 43.2%
(16.5%), angle 2 or 3 19.6%, end-fire 16.8%. Their tables are in `summary.json` under `classes` and `chance`.

**What this says:**
- **The main wrong lock on real talkers is another direction that was also sounding.** That is either what filled the
  pause before the onset, or another labelled source around it. It covers over half of GccPhat's wrong speech reads and
  two-thirds of its outliers, at 2.5-3x the chance rate.
- **The pause and the labelled sources are largely the same thing.** The commonest overlap is exactly those two (1,445
  reads). Of GccPhat's 5,799 pause-direction reads, 3,483 had a labelled source sounding before the onset in that
  direction. The other 2,316 locked to a pause direction no label explains: an unlabelled sound, or the room's own.
- **"Truth was angle 2 or 3" is barely above chance** (16.6% against 12.4%), as the earlier report found. The talker is
  usually not just one place down the scan.
- **The 0 deg pull and aliasing are small.** The 0 deg pull is 7% of wrong reads. Aliasing is under 1%: STARSS speech
  (24 kHz, upsampled) carries well under 1% of its power above the 2.5 kHz where these pairs start to alias, so few
  frequencies there qualify. That may differ on the phone's 157 mm pair, where aliasing starts at 1.1 kHz.
- **The end-fire pins** are reads stuck at +-90, wider than the sphere predicts for that direction.
- **"Other" is mostly moderate** (3,140 of 3,684): 10-36 deg off, with no competing direction to blame.

### Did it start right and drift, or start wrong?
GccPhat, speech in scope, its first draw (43 ms) against the lock:

| | right at the lock | wrong at the lock |
|---|---|---|
| right at 43 ms | 7,247 (23.6%) | 2,440 (7.9%): drift |
| wrong at 43 ms | 9,281 (30.2%): recovered | 11,742 (38.2%) |

83% of wrong locks were already wrong at the first draw; 17% started right and summed their way off. The first draw is
a poor guide on its own: 30% of reads start wrong and end right.

## 3. What each read knew at the time
Medians or rates, for reads within 10 deg (ok), 10-36 deg (moderate) and beyond 36 deg (outlier). Speech, against the
sphere reference.

| clue | GccPhat ok | moderate | outlier | Angle2 ok | moderate | outlier |
|---|---|---|---|---|---|---|
| GccPhat angle 1 share | 0.58 | 0.51 | 0.45 | 0.58 | 0.53 | 0.47 |
| GccPhat votes after pause weighting (of 329) | 182 | 153 | 142 | 188 | 165 | 151 |
| GccPhat tie flag | 5.7% | 12.5% | 25.9% | 6.7% | 10.6% | 18.0% |
| GccPhat change from 43 ms to the lock (deg) | 12.4 | 15.7 | 22.0 | 11.5 | 14.7 | 24.6 |
| Angle2 edge onset | 72.2% | 58.6% | 50.8% | 78.8% | 59.3% | 44.2% |
| schemes agree within 5 deg | 43.2% | 29.0% | 26.8% | 52.6% | 26.1% | 20.3% |
| voice over pause, 300-1100 Hz (dB) | 9.4 | 7.3 | 4.5 | 10.1 | 7.8 | 5.8 |
| voice over pause, 1.1-3 kHz (dB) | 7.7 | 5.7 | 3.1 | 8.5 | 6.2 | 4.3 |
| voice over pause, 3-8 kHz (dB) | 4.8 | 2.9 | 1.9 | 5.2 | 3.6 | 2.6 |
| another labelled source active | 70.5% | 75.1% | 90.0% | 68.6% | 74.5% | 86.3% |

**Every clue moves the right way, and none separates cleanly on its own:**
- **Strongest:** the voice-over-pause level (about 5 dB from ok to outlier), the tie flag (6% against 26%), the two
  schemes agreeing, and Angle2's edge.
- **Weakest:** the share, because the PHAT share is high for any coherent direction, wrong or right.

Choosing the commit-or-dim rule is brief 11's job. This table is what it starts from.

## 4. Range, alongside
A separate script on the same cut audio (`range_cues.py`), never touching the angle. It covers same-talker speech pairs
across all 6 capsule pairs.

"Same talker" here is one file, one speech class and one source index. STARSS has no identity across files, and a
source index can be reused within a file, so some pairs mix two people.

| cue | ordered right, 1.25x / 1.5x / 2x apart | same spot (within 0.3 m): median, 90th pct difference | median difference at 2x |
|---|---|---|---|
| direction-free CDR (`cdr_free_bands`, 0.13-0.6 s) | 63.5% / 66.4% / 71.6% | 1.4 dB, 3.8 dB | 1.4 dB |
| 1 / amplitude of the first 5 ms (FiveMsAmplitude) | 56.0% / 57.6% / 61.1% | 6.4 dB, 17.3 dB | 4.6 dB |
| early echo lag, 1-12 ms (cepstral peak) | 52.6% / 55.4% / 54.1% | 1.2 ms, 5.0 ms | 2.4 ms |

That's 45,020 to 45,101 ordered pairs per cue at 1.25x, and about 356,000 same-spot pairs.

- **The CDR is the only cue that orders distance** clearly better than chance, and it improves with the distance
  ratio.
- **Even the CDR isn't consistent yet.** Its spread at the same spot (1.4 dB) equals its difference at twice the
  distance.
- **The 5 ms level is little better than a coin.** Its same-spot spread (6.4 dB) is larger than the difference a
  doubled distance makes. One 5 ms window holds too little of the voice to be repeatable.
- **The echo lag doesn't order distance.** 42% of its peaks sit at 1-2 ms and the rest spread over the range where
  pitch periods also lie. It finds the voice, not a floor or ceiling echo, which is the check brief 6 asked for first.

Brief 6 (on hold) is the place to take range further.

## Caveats
- **The array:** 68.5 mm on a rigid sphere, not 157 mm on a phone. Aliasing and the low-frequency coherence sit
  elsewhere for the phone. The sphere reference is a model (the STARSS README's formula with white noise), checked
  against the per-direction simulation but not against measured sphere responses.
- **Truth:** the head marker in 100 ms frames. Onsets are label frames, so they can be up to 100 ms early. A talker
  moving during the half second shows in `truth.lateral_span`.
- **Others:** only labelled sources count. Unlabelled sounds and the room's own noise show up as "pause direction" with
  no label, or as "other".
- **Aliasing:** the 5% third-octave share threshold is a choice. Speech carries little energy above 2.5 kHz here, so the
  class is small at any reasonable threshold.
- **Correlated reads:** the 6 pairs hear the same 7,498 onsets, so they aren't independent samples.

## Files (no audio)
- **`reads.jsonl.gz`:** 44,988 reads in the shared batch A format. Top-level `classes` are GccPhat's; Angle2's are in
  `a2.classes`. Additions (never renames) are listed in `harness/batchA/starss23/README.md`.
- **`truth.jsonl.gz`:** the truth alone, with every other source and its sphere reference.
- **`catalogue.jsonl.gz`:** every wrong read (18,251 GccPhat, 21,043 Angle2), with file, time, pair, truth, reference,
  read, classes, the other sources and the pause direction, to listen to.
- **`summary.json`:**
  - `score`: the rule's score, every subset, both references;
  - `classes`, `chance`, `overlaps`;
  - `examples`: up to 6 per class, one per file;
  - `clues_by_severity`, `lean`.
- **`range.jsonl.gz`, `range_summary.json`:** the range cues and their consistency scores.
- **`sphere_grid_reads.jsonl.gz`:** the reference grid.

## Examples to listen to (file, onset, pair: reference -> GccPhat's read)
More are in `summary.json` under `examples`; the full list is in `catalogue.jsonl.gz`.
- **Pause direction:**
  - fold3_room12_mix001 at 138.7 s, pair 2-4: 16.6 -> -2.9
  - fold4_room16_mix006 at 33.4 s, pair 3-4: 45.0 -> -34.5
- **Another labelled source:**
  - fold3_room7_mix003 at 195.0 s, pair 2-4: 12.2 -> -77.2
  - fold3_room21_mix029 at 107.0 s, pair 2-3: 27.7 -> 12.0
- **Drift:**
  - fold4_room24_mix001 at 49.3 s, pair 2-4: 22.4 -> -23.1
  - fold3_room12_mix009 at 15.0 s, pair 1-2: 16.6 -> 27.8
- **Truth was angle 2 or 3:**
  - fold4_room16_mix003 at 54.6 s, pair 1-2: -68.5 -> 32.8
  - fold4_room23_mix003 at 17.9 s, pair 3-4: 4.8 -> 37.5
- **End-fire pin:**
  - fold4_room2_mix003 at 207.5 s, pair 1-4: -63.0 -> -90
  - fold3_room22_mix002 at 91.3 s, pair 2-4: -32.8 -> -90
- **0 deg pull:**
  - fold3_room21_mix003 at 85.5 s, pair 3-4: 39.3 -> -3.8
  - fold3_room13_mix001 at 33.5 s, pair 3-4: 33.7 -> 1.0
- **Mirror:**
  - fold3_room22_mix006 at 5.6 s, pair 1-3: 23.5 -> -17.5
  - fold3_room22_mix010 at 186.9 s, pair 2-4: -65.5 -> 71.8
- **Aliasing partner:**
  - fold3_room4_mix001 at 107.5 s, pair 1-3: 54.1 -> -10.6
  - fold3_room6_mix003 at 91.5 s, pair 2-4: -68.5 -> 4.3
