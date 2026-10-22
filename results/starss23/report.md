# STARSS23: GccPhat and Angle2 on real rooms (2026-10-22)

## What was run
- **Data:** STARSS23 development set, MIC format (https://zenodo.org/records/7880637). The truth is the optical tracker,
  not anyone's marks.
- **Cuts:** 1,422 speech onsets where one talker is the only active source, across 16 rooms (Tampere rooms 2-16, Tokyo
  rooms 21-24).
- **Capsule pairs:** all 6, each about 68.5 mm apart. That's 8,532 reads per scheme.
- **Schemes:** `src/schemes/GccPhat.mjs` (angle 1 at the lock, plus angles 2 and 3) and `Angle2.readUtterance` (onset
  and first reflection). Both ran unchanged, through `harness/starss23/run_schemes.mjs`.
- **Sign:** checked, not assumed. The harness convention is correct: median error 8 deg, against 50 deg flipped.

## Headline

| | median error | within 10 deg | by pair (median error) |
|---|---|---|---|
| GccPhat, angle 1 | 9.2 deg | 53% | 7.6 to 12.8 |
| Angle2, onset | 15.0 deg | 37% | 12.6 to 18.7 |

GccPhat is better than Angle2 in all 6 pairs and in all 16 rooms.

Error by true lateral angle:

| \|truth\| | 0-15 | 15-30 | 30-45 | 45-60 | 60-90 |
|---|---|---|---|---|---|
| GccPhat | 5.1 | 6.4 | 8.9 | 17.3 | 15.6 |
| Angle2 | 10.9 | 11.2 | 14.9 | 20.8 | 27.5 |

## 1. General or tuned?
Mostly general, with a few harder rooms. The ranking of the rooms isn't stable from one pair to the next.

GccPhat's median error per room, below 40 deg only (so each room's mix of angles doesn't drive it):
- 3.7 to 6.9 deg in 10 rooms.
- 8.8 to 11.0 deg in rooms 4, 9, 21, 22 and 23.
- 15.5 deg in room 2.

A fixed room property would rank the rooms the same way whichever pair listens. It doesn't: across the 15 pairings of
pairs, the Spearman correlation of the room ranks is 0.38 at the median, and ranges from -0.04 to 0.65. Distance
doesn't explain the rooms either: each room's median talker distance against its error gives a Spearman of 0.05.

Angle2 shows the same picture, shifted up: 5.6 to 18.5 deg.

## 2. Does it lean toward 0 in real rooms?
"Lean" here is the error measured along the truth's side (negative means toward 0), for pairs 1-2 and 3-4:

| \|truth\| | 0-15 | 15-30 | 30-45 | 45-60 | 60-90 (n=42) |
|---|---|---|---|---|---|
| GccPhat, real rooms | +1.7 | +1.6 | +5.4 | +19.0 | +26.8 |
| GccPhat, rigid sphere, no room | +0.3 | +1.1 | +4.9 | +18.9 | +27.4 |
| Angle2, real rooms | +1.3 | +0.5 | -1.2 | +4.5 | -3.3 |
| Angle2, rigid sphere, no room | +0.6 | +1.3 | +4.8 | +15.6 | +27.4 |
| Either scheme, free field, no room | 0.0 | 0.0 | -0.2 | -0.3 | -0.8 |

**GccPhat leans out, not in, and the array accounts for all of it.** STARSS's capsules sit on an acoustically hard
sphere of radius 4.2 cm (per the STARSS23 README). Sound bending around the sphere lengthens the delay between capsules,
so every bearing reads wider than it is. `harness/starss23/analysis/sphere_sim.py` pushes 300 real cut directions per pair
through the README's rigid-sphere response, with no room. It reproduces GccPhat's real lean band for band, to within
about 1 deg. **So real rooms add essentially no lean to GccPhat.** This lean belongs to the STARSS array: don't read it
as the phone's, and don't correct the phone for it.

**Angle2 leans in, and the room causes it.** On the same sphere with no room, Angle2 leans out just like GccPhat. In real
rooms it reads 6 to 11 deg nearer 0 than that from 30 deg out, and about 30 deg nearer at 60-90 (only 42 cuts).
Measured cut by cut against GccPhat, Angle2 sits nearer 0 by a median of 1.7 deg (15-30), 4.3 (30-45), 7.6 (45-60) and
19.2 (60-90), across all six pairs.

**A correction to the previous session:** with exact fractional delays and no room, Angle2 is within 1 deg everywhere
(free-field row above). The earlier synthetic result (-28 read as -19.5) doesn't reproduce here. That pull appears with
reflections, not on a clean wavefront. `U_AGREE` may still be part of the mechanism, since it decides which reads count
as one direction once reflections are in the windows. But a plane-wave test can't show it.

## 3. When angle 1 is wrong, is angle 2 or 3 right?
No. The baseline below is "chance": the other angles of a randomly chosen cut, tested against this cut's truth.
- **GccPhat:** angle 1 is off by more than 10 deg on 4,005 reads. Angle 2 or 3 is within 10 deg of the truth on 5.0% of
  them, against 14.6% by chance. Worse than chance: they sit at least 10 deg from angle 1 by construction, and the truth
  usually stays near angle 1 even when angle 1 misses.
- **Angle2:** the onset is off on 5,284 reads. The first reflection is within 10 deg of the truth on 17.8% of them,
  against 12.1% by chance. Barely above chance.

So angles 2 and 3 are not an alternative talker position. As Render already draws them, they're room features.

**One usable signal:** when the two schemes agree to within 5 deg (29% of reads), GccPhat's median error is 6.6 deg.
When they don't, it's 10.2.

## What this means for the phone
- **For angle 1, use GccPhat over Angle2.readUtterance.** Here it's better everywhere, by about 6 deg at the median.
- **Angle2's inward pull is real and comes with the room.** Brief 2 has been revised to test it with reflections
  (dEchorate RIRs or these cuts), not on plane waves.
- **The house tapes' inward lean (5 of 6 tier-A stops) was measured with ODAS.** ODAS is a GCC-type method, and on
  STARSS that family picks up no lean from rooms. The phone's own body is the next suspect: the STARSS sphere shows a
  mount alone can move bearings by 5-27 deg. That's a hypothesis, not a result.

## Caveats
- **Spacing:** about 68.5 mm, not 157 mm. Spatial aliasing starts near 2.5 kHz, not 1.1 kHz.
- **Mount:** a rigid sphere, not a phone chassis.
- **Sample rate:** STARSS audio is 24 kHz, upsampled to 48 kHz for the schemes.
- **Correlated pairs:** the six pairs hear the same 1,422 onsets, so they aren't independent samples.
- **Truth resolution:** the tracker's truth comes in 100 ms frames, and it's the head marker's direction.

## Files
- **`preds_<pair>.jsonl`:** each scheme's angles per cut.
- **`analysis.json`, `analysis_extra.json`, `lean_compare_12_34.json`:** every number above.
- **The cuts (546 MB per pair) aren't committed.** Re-make them with `harness/starss23/starss_cut.py`.
- **Re-make the analysis:** `harness/starss23/analysis/analyze.py`, `extra.py` and `sphere_sim.py`. Each takes the
  folder holding the cuts and predictions.
