# dEchorate: onset and first-reflection truth (2026-10-22)

## What was run
- **Room and RIRs:** dEchorate is one 5.7 x 6.0 x 2.4 m room whose surfaces can each be made reflective or absorbing.
  It comes in 11 wall configurations, with 6 calibrated loudspeakers and six 5-mic linear arrays. The RIRs used are v1.0's
  `dechorate_rir_processed.hdf5` (https://zenodo.org/records/5562386), at 48 kHz, aligned so the direct path sits at its
  time of flight. The calibrated positions and echo labels come from v2.0 (https://zenodo.org/records/6576203).
- **Speech:** 24 phrase onsets from 4 EARS speakers (2 women, 2 men; anechoic studio recordings at 48 kHz). Each onset
  has 0.5 s of true silence in front of it, and each mic gets independent noise 30 dB below the speech level.
- **Pairs:** two pairs per array. Mics 0-3 are 155 mm apart (the phone's 157 mm). Mics 2-3 are 65 mm apart (STARSS's
  69 mm).
- **Scale:** 11 configurations x 6 sources x 6 arrays x 2 pairs x 24 onsets = **19,008 cuts per scheme**.
- **Schemes:** `GccPhat` (angle 1, plus angles 2 and 3) and `Angle2.readUtterance` (onset and first reflection), run
  unchanged through `harness/dechorate/run_schemes.mjs`. Each scheme was given the true onset, not the Conductor's.
- **Hit:** a read within 10 deg of the truth. **In scope:** truth within ±60 deg, the app's range.
- Both schemes returned a read on every cut, with no errors.

## Data problems, and what was done about each
1. **v2.0's 4.2 GB RIR file doesn't open.** Its MD5 matches Zenodo, so the download is fine; the file itself is broken.
   - Its superblock gives the end of the file as byte 2,048. `fix_superblock.py` corrects that.
   - The `rir` group's B-tree then points to byte 4,024,414,793 for 7 of the 11 configurations, and the file is all zeros
     there.
   - v1.0's processed file holds all 11 configurations, 30 mics and 7 source columns.
   - Columns 0-5 are calibrated sources 0-5: on every mic, each column's first arrival is within 1-3 samples of that
     source's time of flight. Column 6 matches no listed position (at least 70 samples off) and isn't used.
2. **Six capsules (0, 5, 17, 20, 23 and 28) have inverted polarity.** Each inverts the direct path in every room and for
   every source facing into the room. Uncorrected, a pair's cross-spectrum flips sign. Those channels are flipped back,
   since a phone's two capsules share polarity.
3. **Which surfaces actually reflect** (`echo_check.json`, echo peak relative to the direct peak, median):
   - Ceiling: -5.6 dB when reflective, against -20 dB when absorbing. It's the only strong echo.
   - West, east and north walls: 4 to 7 dB above their absorbing level.
   - Floor: absorbing in every configuration.
   - South wall: flipping it (000100 against 000000) adds nothing at any first-order echo time. It's never scored as
     reflective.
4. **The measured direct-path delays don't match the calibrated geometry.**
   - Measured in each pair's two RIRs, the direct-path delay is 3-23% longer than the published positions predict.
   - One factor per pair explains it across all 66 direct paths (11 rooms x 6 sources): the error falls from 0.7-1.5
     samples rms to 0.3-0.9 (`tables.md`, last section). The pairs behave as if that much wider.
   - The schemes hear the RIRs, so **the truth is the measured direct-path delay**. Echo delays are the image-source
     delays scaled by the same per-pair factor (`truth.py`).
   - The same run scored against the published geometry is in `tables_geometry.md`. Below, "geometry" quotes it wherever
     the conclusion would change.
   - Under measured truth, 82-86% of cuts beyond 60 deg have a delay longer than the pair's maximum, so their truth clamps
     at ±90. That band can't be scored, which is one more reason to stay in scope.

## Headline (in scope, all 11 configurations)

| | 155 mm: median | 155 mm: within 10 deg | 65 mm: median | 65 mm: within 10 deg |
|---|---|---|---|---|
| GccPhat, angle 1 | 0.7 deg | 91% | 1.7 deg | 84% |
| Angle2, onset | 4.4 deg | 77% | 9.5 deg | 52% |

GccPhat is ahead in every configuration at both spacings. Under the geometry truth it's 3.4 deg and 87% against
Angle2's 4.9 deg and 76% at 155 mm, so the ranking holds either way.

## 1. Onset hit rate by wall configuration (in scope; median error / share within 10 deg)

| config | reflective | GccPhat 155 mm | Angle2 155 mm | GccPhat 65 mm | Angle2 65 mm |
|---|---|---|---|---|---|
| 000000 | none | 0.7 / 96% | 4.1 / 80% | 1.2 / 90% | 9.0 / 56% |
| 000001 | north | 0.6 / 97% | 4.0 / 81% | 1.5 / 89% | 9.3 / 52% |
| 000010 | east | 0.7 / 92% | 4.1 / 80% | 1.3 / 84% | 8.7 / 55% |
| 000100 | (south, measures as none) | 0.7 / 92% | 4.1 / 78% | 1.2 / 85% | 9.2 / 52% |
| 001000 | west | 0.7 / 95% | 4.4 / 76% | 1.7 / 86% | 9.0 / 54% |
| 010000 | ceiling | 0.6 / 98% | 4.3 / 78% | 1.7 / 92% | 8.9 / 54% |
| 011000 | ceiling, west | 0.8 / 93% | 4.7 / 77% | 1.7 / 89% | 9.7 / 51% |
| 011100 | + south | 1.0 / 88% | 4.8 / 74% | 2.0 / 80% | 9.6 / 51% |
| 011110 | + east | 1.3 / 80% | 4.9 / 73% | 3.1 / 71% | 10.4 / 48% |
| 011111 | + north | 1.6 / 78% | 5.5 / 73% | 3.1 / 70% | 10.7 / 47% |
| 020002 | ceiling, north, furniture | 1.1 / 92% | 4.4 / 75% | 1.7 / 88% | 10.4 / 48% |

- **GccPhat:** the ceiling alone costs it nothing. Its hit rate drops as walls are added: 96% to 78% at 155 mm, and 90%
  to 70% at 65 mm.
- **Angle2:** starts lower and drops less (80% to 73%, and 56% to 47%). With every surface absorbing, it already misses
  1 cut in 5 at 155 mm, so most of its error isn't the room.
- **Facing a wall:** sources 4 and 5 face a wall, away from most arrays, so their direct sound is weak. In scope at
  155 mm:
  - GccPhat falls from 0.5 deg / 97% (sources facing in) to 4.2 deg / 79%.
  - Angle2 falls from 3.5 deg / 85% to 7.2 deg / 62%.
- **Where GccPhat's misses point:** half of its misses at 155 mm point at a reflective surface's echo, against 28% by
  chance. When GccPhat fails, a reflection has captured it. Angle2's misses land on echoes only slightly above chance
  (25% against 20%).

## 2. Does it lean toward 0? (for brief 2)
Lean is |read| - |truth| in deg, median; negative means nearer 0. 155 mm, with the 0-15 deg band left out because
taking |x| near 0 makes it positive by construction.

| | 15-30 | 30-45 | 45-60 |
|---|---|---|---|
| GccPhat, ceiling absorbing | 0.0 | +0.1 | -0.3 |
| GccPhat, ceiling reflective | -0.1 | -0.1 | -0.7 |
| Angle2, ceiling absorbing | -1.0 | -0.9 | -2.2 |
| Angle2, ceiling reflective | -1.5 | -2.1 | -2.9 |

At 65 mm Angle2 reads 0.0, -1.2 and -3.1 with the ceiling absorbing, and -0.7, -2.1 and -4.1 with it reflective.

**Angle2 leans in even when every surface absorbs, and the lean grows with angle.** That matches the STARSS run. The size
in scope is smaller here: 1-3 deg, against STARSS's 2-8 deg relative to GccPhat.

**The ceiling test: 000000 against 010000**, with the same sources, pairs and speech. The ceiling echo is strong
(-5.6 dB), arrives 2.6 ms after the direct sound, and comes from nearer 0 than the direct sound on 100% of 155 mm cuts.
- **Angle2:** 67% of its reads change, but as many move out as in (34% and 33%). The median change is 0.0 deg and the
  mean -0.7 deg.
- **GccPhat:** 45% of its reads move in and 6% out, with a mean of -1.1 deg. At 65 mm it's 69% in, 7% out and -1.5 deg.

So a single strong early reflection pulls **GccPhat** slightly inward. It doesn't pull Angle2. For brief 2, this rules
out "one strong early echo nearer 0" as the cause of Angle2's lean. Angle2's lean is already present with every panel
absorbing, which still leaves echoes at about -20 dB and the measured responses of the loudspeakers and capsules.

## 3. First reflection
`Angle2.readUtterance`'s second family is scored against the labelled first-order echoes of the reflective surfaces.
"Earliest distinct" is the earliest such echo more than 10 deg from the direct sound; it's the only kind a read can tell
from the onset. Chance is another source's read against this cut's echoes.

| config | 155 mm: earliest distinct, hit / chance | 155 mm: any reflective | 65 mm: earliest distinct | 65 mm: any reflective |
|---|---|---|---|---|
| 000001 (north) | 12% / 13% | 13% / 10% | 9% / 9% | 9% / 10% |
| 000010 (east) | 11% / 12% | 11% / 11% | 9% / 11% | 10% / 9% |
| 001000 (west) | 12% / 11% | 12% / 10% | 12% / 9% | 12% / 9% |
| 010000 (ceiling) | 22% / 14% | 29% / 15% | 15% / 12% | 16% / 14% |
| 011000 | 19% / 15% | 38% / 22% | 14% / 12% | 27% / 17% |
| 011100 | 19% / 10% | 37% / 23% | 15% / 12% | 28% / 20% |
| 011110 | 17% / 12% | 45% / 33% | 16% / 12% | 35% / 29% |
| 011111 | 19% / 11% | 55% / 42% | 14% / 11% | 41% / 34% |
| 020002 | 16% / 12% | 35% / 25% | 15% / 11% | 25% / 23% |
| all | 16% / 12% | 31% / 21% | 13% / 11% | 22% / 19% |

(000000 and 000100 have no reflective surface to score.) Each configuration's chance comes from one random draw over 864
reads, so it's good to about ±2%.

- **Angle2's "first reflection" is barely above chance.** It's best with only the ceiling reflective (22% against 14%),
  and at chance with a single wall. On 25% of 155 mm cuts it's the direct direction again.
- **Its timing isn't the reflection's.** The second family's first read comes a median of 3 ms after the onset family's
  first read, in every configuration including all-absorbing. The earliest real echo is 2.6 ms late with the ceiling and
  8-13 ms with a single wall. Against the earliest distinct echo's delay, the Spearman correlation is 0.06
  (n = 13,848). The 3 ms is `U_WIN`, the window length, not the room.
- **GccPhat angles 2 and 3** hit the earliest distinct echo 19% of the time against 12% by chance at 155 mm, and 15%
  against 9% at 65 mm. That's no better than Angle2.

## What this means for the app
- **Onset:** keep GccPhat as the bearing. In a measured room with real reflective panels it finds the direct path to
  within 1-2 deg on 91% (155 mm) of in-scope cuts. Its failures are capture by a reflection, mostly from talkers facing
  away.
- **First reflection:** neither scheme gets it. Angle2's second family is a 3 ms window artifact, not an arrival. Render
  should keep drawing it as a room feature, not as "the first reflection".
- **Angle2's inward lean** is real here too (1-3 deg in scope, growing with angle), but a strong early echo doesn't cause
  it. Brief 2's image-source sweep should look elsewhere: the low-level reflections and the recurrence and family rules.

## Caveats
- The truth is the measured direct path; see "Data problems" item 4. Under the published geometry, GccPhat reads 2-5 deg
  wider, by exactly the amount the RIRs themselves read wider. The rankings and the reflection results don't change.
- Every onset here is a phrase onset after true silence, with white noise at 30 dB below the speech. Real pauses carry
  room noise and the previous phrase's tail.
- Each scheme got the true onset. The Conductor's ears (`attacks.py`) find their own, which this doesn't test.
- One room, so this tests the wall configuration, not the room. Compare the STARSS run for 16 different rooms.

## Files
- `truth.jsonl.gz`: every cut's truth, with no audio.
- `preds.jsonl.gz`: both schemes' reads.
- `scores.json`, `tables.md`: measured truth. `scores_geometry.json`, `tables_geometry.md`: published geometry.
- `echo_check.json`: the per-surface echo levels.
- Rebuild everything with `harness/dechorate/run_all.sh` (see `harness/dechorate/README.md`).
