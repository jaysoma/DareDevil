# Truth recovery summary

Run 2026-10-22 over the 29 tapes in jaysoma/DareDevil. Poses were checked only against ODAS, the stop positions and room geometry; none of the recordist's own bearing schemes were used.

Tier A = place resolved, pose high-confidence, placement tight enough (<= 8 deg of angular uncertainty) and predicted bearing within 70 deg. Tier B = place resolved but one of those fails. Tier C = no place (distance/angle only, unmapped place, or dead pair).
Confidence 'recollection' = set from Jay's answers on 2026-10-22; where ODAS disagrees, the evidence line says so.


| tape | recorded | pose | sign | confidence | A | B | C |
|---|---|---|---|---|---|---|---|
| walk-002736 | 2026-09-14 00:27 | assigned | ? | unverified | 0 | 0 | 1 |
| walk-111830 | 2026-09-22 11:18 | P4 | - | medium | 0 | 1 | 9 |
| walk-114614 | 2026-09-22 11:46 | P4 | ? | recollection | 0 | 0 | 5 |
| walk-125621 | 2026-09-19 12:56 | assigned | ? | unverified | 0 | 0 | 5 |
| walk-154655 | 2026-09-19 15:46 | assigned | ? | unverified | 0 | 0 | 8 |
| walk-155937 | 2026-09-19 15:59 | assigned | ? | unverified | 0 | 0 | 7 |
| walk-165255 | 2026-09-23 16:52 | assigned | ? | unverified | 0 | 0 | 4 |
| walk-170343 | 2026-09-19 17:03 | P4 | - | low | 0 | 1 | 3 |
| walk-180036 | 2026-09-23 18:00 | assigned | ? | unverified | 0 | 0 | 5 |
| walk-194532 | 2026-09-28 19:45 | excluded | ? | unresolved | 0 | 0 | 6 |
| walk-194940 | 2026-09-24 19:49 | unresolved | ? | unresolved | 0 | 0 | 3 |
| walk-195454 | 2026-09-24 19:54 | excluded | ? | unresolved | 0 | 0 | 6 |
| walk-203939 | 2026-09-23 20:39 | assigned | + | high | 2 | 2 | 0 |
| walk-204738 | 2026-09-15 20:47 | assigned | ? | unverified | 0 | 0 | 2 |
| walk-204753 | 2026-09-29 20:47 | P3 | + | high | 2 | 2 | 1 |
| walk-205043 | 2026-09-22 20:50 | assigned | ? | unverified | 0 | 0 | 4 |
| walk-205606 | 2026-09-23 20:56 | P1 | + | recollection | 0 | 4 | 2 |
| walk-210054 | 2026-09-24 21:00 | P3 | + | high | 2 | 3 | 0 |
| walk-211959 | 2026-09-23 21:19 | P1 | + | medium | 0 | 5 | 0 |
| walk-212347 | 2026-09-28 21:23 | excluded | ? | unresolved | 0 | 0 | 6 |
| walk-213150 | 2026-09-29 21:31 | P4 | + | high | 1 | 2 | 2 |
| walk-214241 | 2026-09-29 21:42 | P1 | + | medium | 0 | 2 | 2 |
| walk-214457 | 2026-09-29 21:44 | P2 | - | medium | 0 | 1 | 4 |
| walk-221126 | 2026-09-21 22:11 | assigned | ? | unverified | 0 | 0 | 15 |
| walk-223157 | 2026-09-21 22:31 | assigned | ? | unverified | 0 | 0 | 1 |
| walk-224459 | 2026-09-17 22:44 | assigned | ? | unverified | 0 | 0 | 10 |
| walk-225729 | 2026-09-26 22:57 | assigned | ? | unverified | 0 | 0 | 1 |
| walk-225905 | 2026-09-26 22:59 | assigned | ? | unverified | 0 | 0 | 1 |
| walk-233828 | 2026-09-14 23:38 | assigned | ? | unverified | 0 | 0 | 9 |
| **total** | | | | | **7** | **23** | **122** |

Poses: P1 kitchen bar (0.35, 4.2) facing -133; P2 left of TV (-3.4, -0.25) facing 47; P3 left wall (-4.0, 2.2) facing 89; P4 TV stand (-2.15, -0.2) facing 0; "assigned" = the pose in poses.json where it differs from all four. Sign = the ODAS azimuth sign that fits, relative to ODAS's own convention: compare signs between tapes, not with the map.

## Self-check

Five random tier-A stops were re-derived with a different estimator (median of all active ODAS azimuths in the stop, instead of the mode). Three agreed within 4 deg; two did not: walk-203939 J4 (predicted 72 deg, measured 36 -- beyond the pair's reliable range) and walk-213150 "L section" (placement radius 1 m at 4.4 m, +-13 deg). Tier A was tightened accordingly (the two rules above) and all six remaining tier-A stops were re-checked: every one within 6 deg.

In 5 of those 6, the measured bearing is smaller in magnitude than predicted (e.g. 37.7 -> 33.9, -23.8 -> -17.8): readings pulled toward 0 deg. Six stops prove nothing, but it is the direction a floor/ceiling-reflection or chassis bias would push.

## ODAS hears 0 deg when nobody is talking

Across all tapes, 47% of ODAS's active directions during PAUSES lie within 6 deg of 0, and 46% during speech. A real source in the room would move with the phone; this does not -- it sits at 0 on the TV stand, the left wall and the kitchen bar alike. The HVAC vent shows up at its predicted bearing only on some tapes (e.g. walk-213150, walk-221126). A pose-independent 0 deg in silence points to something common to both capsules (low-frequency diffuse noise, which is coherent at zero lag for a 157 mm pair, or electrical crosstalk; ODAS ran with no high-pass, ssl_hp_hz 0), not to the room.
