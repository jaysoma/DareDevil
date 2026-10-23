## The data

| set | task | recordings | talkers | onsets (per pair) | with another talker active | facing > 120 deg | distance, median (m) |
|---|---|---|---|---|---|---|---|
| dev | 3 | 3 | 3 | 18 | 0% | 17% | 2.04 |
| dev | 4 | 3 | 6 | 109 | 91% | 19% | 1.64 |
| eval | 3 | 5 | 5 | 37 | 0% | 22% | 1.92 |
| eval | 4 | 5 | 10 | 177 | 87% | 12% | 2.05 |

In scope (|truth| <= 75 deg): 341 of 341 onsets per pair. Truth moved across the half second (|deg_end - deg|), median 2.1 deg, 90th percentile 6.6.

## Sign and replica checks

- 160 mm, GccPhat: median error 5.9 deg with the convention as computed, 42.9 flipped.
- 160 mm, Angle2: median error 5.9 deg with the convention as computed, 42.3 flipped.
- 80 mm, GccPhat: median error 6.1 deg with the convention as computed, 41.6 flipped.
- 80 mm, Angle2: median error 7.1 deg with the convention as computed, 38.4 flipped.
- GccPhat's lock rebuilt here (for the vote total) equals the stream's angle 1 on 682 of 682 reads. Scheme errors: GccPhat 0, Angle2 0; no read: GccPhat 0, Angle2 3.

## Under Jay's rule

| pair | scheme | in scope | read outliers set aside | scenarios dropped | kept | mean / median, kept | within 10 deg, kept |
|---|---|---|---|---|---|---|---|
| 160 mm | GccPhat | 341 | 42 (12.3%) | 0 of 24 | 87.7% | 7.5 / 5.2 | 83.3% |
| 160 mm | Angle2 | 339 | 64 (18.9%) | 0 of 24 | 81.1% | 7.0 / 4.8 | 82.2% |
| 160 mm | both kept (260) | | | | | GccPhat 7.5 / 5.2, Angle2 6.7 / 4.7 | 82.7% / 83.5% |
| 80 mm | GccPhat | 341 | 35 (10.3%) | 0 of 24 | 89.7% | 7.3 / 5.2 | 81.4% |
| 80 mm | Angle2 | 340 | 61 (17.9%) | 0 of 24 | 82.1% | 7.5 / 5.4 | 75.6% |
| 80 mm | both kept (268) | | | | | GccPhat 7.3 / 5.2, Angle2 7.4 / 5.3 | 81.3% / 76.9% |

Lean (signed error along the truth's side, mean deg; negative = nearer 0), kept reads:

| pair | scheme | 0-15 | 15-30 | 30-45 | 45-60 | 60-75 |
|---|---|---|---|---|---|---|
| 160 mm | GccPhat | -0.6 (n=85) | -3.9 (n=106) | -4.0 (n=71) | -3.0 (n=34) | None (n=0) |
| 160 mm | Angle2 | 0.2 (n=78) | -1.2 (n=94) | -5.8 (n=65) | -3.9 (n=34) | 15.4 (n=1) |
| 80 mm | GccPhat | -0.5 (n=85) | -4.2 (n=110) | -4.0 (n=70) | -5.1 (n=38) | None (n=0) |
| 80 mm | Angle2 | -1.0 (n=80) | -2.9 (n=97) | -4.6 (n=63) | -3.1 (n=36) | None (n=0) |

## Wrong locks, in scope (raw, before the rule sets anything aside)

| pair | scheme | split | n | wrong > 10 deg | wrong > 36 deg |
|---|---|---|---|---|---|
| 160 mm | GccPhat | all | 341 | 27% | 12% |
| 160 mm | GccPhat | |truth| 0-15 | 91 | 15% | 3% |
| 160 mm | GccPhat | |truth| 15-30 | 116 | 29% | 9% |
| 160 mm | GccPhat | |truth| 30-45 | 85 | 27% | 16% |
| 160 mm | GccPhat | |truth| 45-60 | 47 | 40% | 28% |
| 160 mm | GccPhat | |truth| 60-75 | 2 | 100% | 100% |
| 160 mm | GccPhat | task 3 | 55 | 15% | 2% |
| 160 mm | GccPhat | task 4 | 286 | 29% | 14% |
| 160 mm | GccPhat | another talker active | 253 | 32% | 15% |
| 160 mm | GccPhat | alone | 88 | 14% | 3% |
| 160 mm | GccPhat | facing 0-60 deg | 166 | 12% | 7% |
| 160 mm | GccPhat | facing 60-120 deg | 120 | 28% | 12% |
| 160 mm | GccPhat | facing 120-181 deg | 55 | 69% | 27% |
| 160 mm | GccPhat | distance 0-1.5 m | 110 | 15% | 7% |
| 160 mm | GccPhat | distance 1.5-2.5 m | 169 | 35% | 14% |
| 160 mm | GccPhat | distance 2.5-9 m | 62 | 26% | 16% |
| 160 mm | Angle2 | all | 339 | 33% | 19% |
| 160 mm | Angle2 | |truth| 0-15 | 91 | 25% | 11% |
| 160 mm | Angle2 | |truth| 15-30 | 114 | 30% | 18% |
| 160 mm | Angle2 | |truth| 30-45 | 85 | 39% | 24% |
| 160 mm | Angle2 | |truth| 45-60 | 47 | 45% | 28% |
| 160 mm | Angle2 | |truth| 60-75 | 2 | 100% | 50% |
| 160 mm | Angle2 | task 3 | 55 | 11% | 2% |
| 160 mm | Angle2 | task 4 | 284 | 38% | 22% |
| 160 mm | Angle2 | another talker active | 251 | 40% | 25% |
| 160 mm | Angle2 | alone | 88 | 15% | 2% |
| 160 mm | Angle2 | facing 0-60 deg | 166 | 22% | 16% |
| 160 mm | Angle2 | facing 60-120 deg | 119 | 38% | 20% |
| 160 mm | Angle2 | facing 120-181 deg | 54 | 57% | 24% |
| 160 mm | Angle2 | distance 0-1.5 m | 110 | 23% | 10% |
| 160 mm | Angle2 | distance 1.5-2.5 m | 168 | 36% | 20% |
| 160 mm | Angle2 | distance 2.5-9 m | 61 | 46% | 31% |
| 80 mm | GccPhat | all | 341 | 27% | 10% |
| 80 mm | GccPhat | |truth| 0-15 | 91 | 15% | 3% |
| 80 mm | GccPhat | |truth| 15-30 | 116 | 19% | 5% |
| 80 mm | GccPhat | |truth| 30-45 | 85 | 40% | 18% |
| 80 mm | GccPhat | |truth| 45-60 | 47 | 43% | 19% |
| 80 mm | GccPhat | |truth| 60-75 | 2 | 100% | 100% |
| 80 mm | GccPhat | task 3 | 55 | 15% | 2% |
| 80 mm | GccPhat | task 4 | 286 | 29% | 12% |
| 80 mm | GccPhat | another talker active | 253 | 32% | 13% |
| 80 mm | GccPhat | alone | 88 | 14% | 1% |
| 80 mm | GccPhat | facing 0-60 deg | 166 | 14% | 7% |
| 80 mm | GccPhat | facing 60-120 deg | 120 | 28% | 12% |
| 80 mm | GccPhat | facing 120-181 deg | 55 | 64% | 16% |
| 80 mm | GccPhat | distance 0-1.5 m | 110 | 16% | 5% |
| 80 mm | GccPhat | distance 1.5-2.5 m | 169 | 37% | 14% |
| 80 mm | GccPhat | distance 2.5-9 m | 62 | 19% | 8% |
| 80 mm | Angle2 | all | 340 | 38% | 18% |
| 80 mm | Angle2 | |truth| 0-15 | 91 | 26% | 9% |
| 80 mm | Angle2 | |truth| 15-30 | 115 | 31% | 16% |
| 80 mm | Angle2 | |truth| 30-45 | 85 | 45% | 26% |
| 80 mm | Angle2 | |truth| 45-60 | 47 | 62% | 23% |
| 80 mm | Angle2 | |truth| 60-75 | 2 | 100% | 100% |
| 80 mm | Angle2 | task 3 | 55 | 7% | 0% |
| 80 mm | Angle2 | task 4 | 285 | 44% | 21% |
| 80 mm | Angle2 | another talker active | 252 | 47% | 24% |
| 80 mm | Angle2 | alone | 88 | 11% | 1% |
| 80 mm | Angle2 | facing 0-60 deg | 166 | 30% | 17% |
| 80 mm | Angle2 | facing 60-120 deg | 119 | 45% | 17% |
| 80 mm | Angle2 | facing 120-181 deg | 55 | 47% | 22% |
| 80 mm | Angle2 | distance 0-1.5 m | 110 | 31% | 9% |
| 80 mm | Angle2 | distance 1.5-2.5 m | 169 | 42% | 22% |
| 80 mm | Angle2 | distance 2.5-9 m | 61 | 39% | 23% |

## Who else was talking, and which way the talker faced (in scope; wrong > 10 deg / > 36 deg)

| pair | scheme | who else | facing 0-60 | 60-120 | away, 120-180 | all facings |
|---|---|---|---|---|---|---|
| 160 mm | GccPhat | alone | 0% / 0% (n=52) | 10% / 0% (n=20) | 62% / 19% (n=16) | 14% / 3% (n=88) |
| 160 mm | GccPhat | another talker only in the pause before | 8% / 0% (n=25) | 10% / 0% (n=10) | 56% / 0% (n=9) | 18% / 0% (n=44) |
| 160 mm | GccPhat | another talker during the read (> 20% of its 0.5 s) | 21% / 14% (n=84) | 35% / 18% (n=84) | 74% / 37% (n=27) | 34% / 19% (n=195) |
| 160 mm | Angle2 | alone | 2% / 0% (n=52) | 25% / 5% (n=20) | 44% / 6% (n=16) | 15% / 2% (n=88) |
| 160 mm | Angle2 | another talker only in the pause before | 16% / 4% (n=25) | 20% / 0% (n=10) | 44% / 22% (n=9) | 23% / 7% (n=44) |
| 160 mm | Angle2 | another talker during the read (> 20% of its 0.5 s) | 38% / 31% (n=84) | 45% / 28% (n=83) | 69% / 31% (n=26) | 45% / 30% (n=193) |
| 80 mm | GccPhat | alone | 6% / 0% (n=52) | 5% / 0% (n=20) | 50% / 6% (n=16) | 14% / 1% (n=88) |
| 80 mm | GccPhat | another talker only in the pause before | 4% / 0% (n=25) | 10% / 0% (n=10) | 56% / 0% (n=9) | 16% / 0% (n=44) |
| 80 mm | GccPhat | another talker during the read (> 20% of its 0.5 s) | 23% / 14% (n=84) | 37% / 17% (n=84) | 70% / 26% (n=27) | 35% / 17% (n=195) |
| 80 mm | Angle2 | alone | 2% / 0% (n=52) | 20% / 0% (n=20) | 31% / 6% (n=16) | 11% / 1% (n=88) |
| 80 mm | Angle2 | another talker only in the pause before | 28% / 0% (n=25) | 30% / 0% (n=10) | 33% / 11% (n=9) | 30% / 2% (n=44) |
| 80 mm | Angle2 | another talker during the read (> 20% of its 0.5 s) | 50% / 35% (n=84) | 53% / 24% (n=83) | 59% / 30% (n=27) | 53% / 29% (n=194) |

Lean on the clean reads only (alone, facing within 60 deg, within 36 deg), mean deg, negative = nearer 0:

| pair | scheme | 0-15 | 15-30 | 30-45 | 45-60 |
|---|---|---|---|---|---|
| 160 mm | GccPhat | -0.6 (n=16) | +0.9 (n=17) | +0.1 (n=14) | -1.9 (n=5) |
| 160 mm | Angle2 | -0.9 (n=16) | +1.0 (n=17) | -0.5 (n=14) | -2.0 (n=5) |
| 80 mm | GccPhat | -0.7 (n=16) | -0.7 (n=17) | -2.9 (n=14) | -1.9 (n=5) |
| 80 mm | Angle2 | -1.0 (n=16) | -0.0 (n=17) | -0.5 (n=14) | -1.8 (n=5) |

Angle2's onset family starts -12 ms from the VAD onset at the median (5th-95th percentile -94 to 198 ms; negative = before it).

## The class catalogue (in scope)

| pair | scheme | severity | wrong reads | mirror | endfire_pin | pause_direction | another_source | zero_pull | aliasing_partner | truth_was_2nd_3rd | drift | facing | other |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 160 mm | GccPhat | moderate | 50 | 2 | 0 | 20 | 22 | 14 | 0 | 29 | 27 | 22 | 1 |
| 160 mm | GccPhat | outlier | 42 | 6 | 0 | 30 | 33 | 12 | 0 | 25 | 16 | 15 | 0 |
| 160 mm | Angle2 | moderate | 49 | 3 | 0 | 26 | 20 | 6 | 0 | 22 | 0 | 18 | 6 |
| 160 mm | Angle2 | outlier | 64 | 18 | 0 | 47 | 49 | 6 | 1 | 11 | 0 | 13 | 3 |
| 80 mm | GccPhat | moderate | 57 | 2 | 0 | 24 | 23 | 7 | 0 | 9 | 25 | 25 | 4 |
| 80 mm | GccPhat | outlier | 35 | 6 | 0 | 24 | 30 | 6 | 0 | 20 | 12 | 9 | 0 |
| 80 mm | Angle2 | moderate | 68 | 4 | 0 | 32 | 20 | 5 | 0 | 10 | 0 | 14 | 24 |
| 80 mm | Angle2 | outlier | 61 | 13 | 0 | 49 | 43 | 7 | 0 | 21 | 0 | 12 | 5 |

Most common overlaps (160 mm, outliers):

- GccPhat: another_source+drift+pause_direction+truth_was_2nd_3rd 6; another_source+pause_direction 4; another_source+mirror+pause_direction 3; another_source+drift+truth_was_2nd_3rd 2; another_source+pause_direction+truth_was_2nd_3rd 2; another_source+facing+pause_direction+truth_was_2nd_3rd 2
- Angle2: another_source+pause_direction 18; another_source+mirror+pause_direction 9; another_source+pause_direction+truth_was_2nd_3rd 5; another_source+facing+pause_direction 3; facing 3; another_source+mirror+pause_direction+truth_was_2nd_3rd 3

## Can it tell at the moment of the read? (in scope, 160 mm)

AUC of each clue for telling a read within 10 deg from one off by more (0.5 = no information; below 0.5, the clue is higher on misses).

| clue | for GccPhat's read | for Angle2's read |
|---|---|---|
| GccPhat share (angle 1) | 0.70 | 0.64 |
| GccPhat width (deg, narrower = higher) | 0.53 | 0.50 |
| GccPhat share margin, angle 1 - angle 2 | 0.72 | 0.66 |
| GccPhat no tie | 0.57 | 0.54 |
| GccPhat votes after pause weighting | 0.59 | 0.67 |
| GccPhat 43 ms read agrees with lock (-|diff|) | 0.68 | 0.62 |
| Angle2 agrees with GccPhat (-|diff|) | 0.62 | 0.73 |
| away from the pause direction (|read - pause|) | 0.63 | 0.47 |
| SNR 300-1100 Hz | 0.56 | 0.64 |
| SNR 1.1-3 kHz | 0.55 | 0.62 |
| SNR 3-8 kHz | 0.57 | 0.60 |
| Angle2 edge (clean rising onset) | 0.59 | 0.56 |
| Angle2 at3 earlier (-ms) | 0.45 | 0.40 |

## Range, alongside

| pair | cue | ordered right: 1.25x | 1.5x | 2x | repeat spread (same spot, median abs diff) | 2x step (median abs diff) |
|---|---|---|---|---|---|---|
| 160 mm | level_db | 51% (n=547) | 54% (n=313) | 54% (n=223) | 8.36 (n=380) | 9.88 |
| 160 mm | cdr_db | 57% (n=547) | 62% (n=313) | 78% (n=223) | 1.3 (n=380) | 2.48 |
| 160 mm | echo_lag_ms | 56% (n=547) | 60% (n=313) | 51% (n=223) | 1.48 (n=380) | 1.79 |
| 80 mm | level_db | 49% (n=547) | 53% (n=313) | 55% (n=223) | 8.79 (n=380) | 9.35 |
| 80 mm | cdr_db | 57% (n=547) | 57% (n=313) | 71% (n=223) | 0.87 (n=380) | 1.69 |
| 80 mm | echo_lag_ms | 54% (n=547) | 56% (n=313) | 55% (n=223) | 1.09 (n=380) | 2.25 |

The cepstral echo lag is within 0.25 ms of the floor echo's geometric lag on 6% of cuts (median difference 1.719 ms, n=682).
