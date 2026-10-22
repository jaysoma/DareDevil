## Onset, all angles and in scope (|truth| <= 60 deg)


**155 mm pairs** (864 cuts per configuration; in scope about 600)

| config | GccPhat median | GccPhat <=10 | Angle2 median | Angle2 <=10 | in scope: GccPhat median / <=10 | in scope: Angle2 median / <=10 |
|---|---|---|---|---|---|---|
| 000000 | 0.4 | 97% | 5.7 | 64% | 0.7 / 96% | 4.1 / 80% |
| 000001 | 0.4 | 97% | 5.2 | 65% | 0.6 / 97% | 4.0 / 81% |
| 000010 | 0.5 | 94% | 6.0 | 63% | 0.7 / 92% | 4.1 / 80% |
| 000100 | 0.4 | 94% | 5.7 | 63% | 0.7 / 92% | 4.1 / 78% |
| 001000 | 0.4 | 96% | 6.1 | 61% | 0.7 / 95% | 4.4 / 76% |
| 010000 | 0.5 | 94% | 6.3 | 61% | 0.6 / 98% | 4.3 / 78% |
| 011000 | 0.7 | 90% | 6.6 | 60% | 0.8 / 93% | 4.7 / 77% |
| 011100 | 0.8 | 88% | 7.3 | 58% | 1.0 / 88% | 4.8 / 74% |
| 011110 | 1.0 | 78% | 7.5 | 58% | 1.3 / 80% | 4.9 / 73% |
| 011111 | 1.5 | 75% | 7.9 | 58% | 1.6 / 78% | 5.5 / 73% |
| 020002 | 1.0 | 84% | 7.1 | 58% | 1.1 / 92% | 4.4 / 75% |
| all | 0.6 | 90% | 6.5 | 61% | 0.7 / 91% | 4.4 / 77% |

**65 mm pairs** (864 cuts per configuration; in scope about 600)

| config | GccPhat median | GccPhat <=10 | Angle2 median | Angle2 <=10 | in scope: GccPhat median / <=10 | in scope: Angle2 median / <=10 |
|---|---|---|---|---|---|---|
| 000000 | 0.7 | 93% | 9.9 | 50% | 1.2 / 90% | 9.0 / 56% |
| 000001 | 0.7 | 92% | 11.0 | 48% | 1.5 / 89% | 9.3 / 52% |
| 000010 | 0.8 | 89% | 10.0 | 50% | 1.3 / 84% | 8.7 / 55% |
| 000100 | 0.6 | 90% | 11.0 | 48% | 1.2 / 85% | 9.2 / 52% |
| 001000 | 0.9 | 91% | 10.7 | 49% | 1.7 / 86% | 9.0 / 54% |
| 010000 | 1.2 | 89% | 10.1 | 49% | 1.7 / 92% | 8.9 / 54% |
| 011000 | 1.3 | 86% | 11.0 | 47% | 1.7 / 89% | 9.7 / 51% |
| 011100 | 1.2 | 83% | 10.7 | 48% | 2.0 / 80% | 9.6 / 51% |
| 011110 | 1.8 | 75% | 11.7 | 45% | 3.1 / 71% | 10.4 / 48% |
| 011111 | 2.0 | 72% | 12.6 | 43% | 3.1 / 70% | 10.7 / 47% |
| 020002 | 1.4 | 83% | 12.1 | 45% | 1.7 / 88% | 10.4 / 48% |
| all | 1.1 | 86% | 11.0 | 48% | 1.7 / 84% | 9.5 / 52% |

## Lean toward 0 (|read| - |truth|, median deg; negative = nearer 0)


**155 mm**

| scheme, config | 0-15 | 15-30 | 30-45 | 45-60 | 60-90 |
|---|---|---|---|---|---|
| GccPhat, ceiling absorbing (00xxxx) | 0.3 (n=720) | 0.0 (n=1080) | 0.1 (n=720) | -0.3 (n=480) | 0.0 (n=1320) |
| GccPhat, ceiling reflective (01xxxx, 02xxxx) | 0.3 (n=864) | -0.1 (n=1296) | -0.1 (n=864) | -0.7 (n=576) | 0.0 (n=1584) |
| Angle2, ceiling absorbing (00xxxx) | 1.6 (n=720) | -1.0 (n=1080) | -0.9 (n=720) | -2.2 (n=480) | -28.6 (n=1320) |
| Angle2, ceiling reflective (01xxxx, 02xxxx) | 1.6 (n=864) | -1.5 (n=1296) | -2.1 (n=864) | -2.9 (n=576) | -32.4 (n=1584) |

**65 mm**

| scheme, config | 0-15 | 15-30 | 30-45 | 45-60 | 60-90 |
|---|---|---|---|---|---|
| GccPhat, ceiling absorbing (00xxxx) | -0.4 (n=720) | 0.1 (n=840) | 0.2 (n=480) | 0.6 (n=720) | 0.0 (n=1560) |
| GccPhat, ceiling reflective (01xxxx, 02xxxx) | -0.4 (n=864) | 0.0 (n=1008) | 0.7 (n=600) | -1.3 (n=888) | 0.0 (n=1824) |
| Angle2, ceiling absorbing (00xxxx) | 1.9 (n=720) | 0.0 (n=840) | -1.2 (n=480) | -3.1 (n=720) | -16.8 (n=1560) |
| Angle2, ceiling reflective (01xxxx, 02xxxx) | 1.8 (n=864) | -0.7 (n=1008) | -2.1 (n=600) | -4.1 (n=888) | -19.2 (n=1824) |

## Ceiling only: 000000 against 010000, same sources, pairs and speech (in scope, 15-60 deg)

| spacing | scheme | lean, all absorbing | lean, ceiling reflective | paired change, median | ceiling echo nearer 0 than direct |
|---|---|---|---|---|---|
| 155 mm | GccPhat | -0.1 | -0.4 | -0.3 (n=456) | 100% |
| 155 mm | Angle2 | -1.1 | -1.6 | 0.0 (n=456) | 100% |
| 65 mm | GccPhat | 0.0 | -1.2 | -1.0 (n=408) | 94% |
| 65 mm | Angle2 | -1.3 | -1.1 | 0.0 (n=408) | 94% |

## First reflection: Angle2's second family against the labelled first-order echoes

Hit = within 10 deg. "Distinct" = the earliest echo from a reflective surface that is more than 10 deg from the direct direction (the only kind a read can tell from the onset). Chance = another source's read against this cut's echoes.


**155 mm**

| config | reads | earliest distinct: hit / chance | any reflective: hit / chance | any first-order (incl. absorbing): hit / chance | same as direct | lag, median ms | earliest distinct echo delay, median ms |
|---|---|---|---|---|---|---|---|
| 000000 | 864 | - / - | - / - | 60% / 49% | 27% | 3.0 | - |
| 000001 | 864 | 12% / 13% | 13% / 10% | 61% / 50% | 24% | 3.0 | 13.1 |
| 000010 | 864 | 11% / 12% | 11% / 11% | 60% / 49% | 24% | 3.0 | 11.6 |
| 000100 | 864 | - / - | - / - | 58% / 51% | 24% | 3.0 | - |
| 001000 | 864 | 12% / 11% | 12% / 10% | 62% / 52% | 24% | 3.0 | 8.2 |
| 010000 | 864 | 22% / 14% | 29% / 15% | 62% / 52% | 25% | 3.0 | 2.6 |
| 011000 | 864 | 19% / 15% | 38% / 22% | 64% / 49% | 24% | 3.0 | 3.6 |
| 011100 | 864 | 19% / 10% | 37% / 23% | 64% / 50% | 25% | 3.0 | 3.6 |
| 011110 | 864 | 17% / 12% | 45% / 33% | 62% / 51% | 25% | 3.0 | 3.6 |
| 011111 | 864 | 19% / 11% | 55% / 42% | 64% / 50% | 25% | 3.0 | 3.6 |
| 020002 | 864 | 16% / 12% | 35% / 25% | 59% / 52% | 23% | 3.0 | 3.9 |
| all | 9504 | 16% / 12% | 31% / 21% | 61% / 51% | 25% | 3.0 | 4.6 |

**65 mm**

| config | reads | earliest distinct: hit / chance | any reflective: hit / chance | any first-order (incl. absorbing): hit / chance | same as direct | lag, median ms | earliest distinct echo delay, median ms |
|---|---|---|---|---|---|---|---|
| 000000 | 864 | - / - | - / - | 53% / 47% | 10% | 3.0 | - |
| 000001 | 864 | 9% / 9% | 9% / 10% | 52% / 48% | 12% | 3.0 | 12.0 |
| 000010 | 864 | 9% / 11% | 10% / 9% | 51% / 48% | 12% | 3.0 | 11.4 |
| 000100 | 864 | - / - | - / - | 51% / 49% | 12% | 3.0 | - |
| 001000 | 864 | 12% / 9% | 12% / 9% | 52% / 48% | 11% | 3.0 | 8.3 |
| 010000 | 864 | 15% / 12% | 16% / 14% | 51% / 47% | 13% | 3.0 | 2.6 |
| 011000 | 864 | 14% / 12% | 27% / 17% | 52% / 46% | 13% | 3.0 | 3.7 |
| 011100 | 864 | 15% / 12% | 28% / 20% | 54% / 48% | 12% | 3.0 | 3.7 |
| 011110 | 864 | 16% / 12% | 35% / 29% | 54% / 47% | 11% | 3.0 | 3.8 |
| 011111 | 864 | 14% / 11% | 41% / 34% | 53% / 48% | 12% | 3.0 | 3.8 |
| 020002 | 864 | 15% / 11% | 25% / 23% | 51% / 50% | 13% | 3.0 | 3.9 |
| all | 9504 | 13% / 11% | 22% / 19% | 52% / 49% | 12% | 3.0 | 4.8 |

## GccPhat angles 2 and 3 against the echoes (all configurations with a reflective surface)

| spacing | reads | earliest distinct: hit / chance | any reflective: hit / chance |
|---|---|---|---|
| 155 mm | 15067 | 19% / 12% | 27% / 20% |
| 65 mm | 9790 | 15% / 9% | 25% / 20% |

## When the onset misses (> 10 deg), does it point at a reflective echo?

| spacing | scheme | misses | on a distinct reflective echo | chance |
|---|---|---|---|---|
| 155 mm | GccPhat | 885 | 50% | 28% |
| 155 mm | Angle2 | 3094 | 25% | 20% |
| 65 mm | GccPhat | 1205 | 27% | 14% |
| 65 mm | Angle2 | 4108 | 21% | 16% |

## Sources facing into the room (0-3) against facing a wall (4, 5), in scope

| spacing | scheme | facing in: median / <=10 | facing a wall: median / <=10 |
|---|---|---|---|
| 155 mm | GccPhat | 0.5 / 97% | 4.2 / 79% |
| 155 mm | Angle2 | 3.5 / 85% | 7.2 / 62% |
| 65 mm | GccPhat | 1.1 / 96% | 7.2 / 62% |
| 65 mm | Angle2 | 8.1 / 57% | 12.9 / 41% |

## Truth check: direct-path delay measured in the RIRs against the calibrated geometry

| pair (mics) | spacing | k (measured / geometric delay) | rms residual, geometry (samples) | rms residual after k (samples) |
|---|---|---|---|---|
| 0-3 | 155 mm | 1.030 | 0.89 | 0.78 |
| 2-3 | 65 mm | 1.138 | 0.91 | 0.38 |
| 5-8 | 155 mm | 1.081 | 1.32 | 0.69 |
| 7-8 | 65 mm | 1.111 | 1.08 | 0.87 |
| 10-13 | 155 mm | 1.081 | 1.07 | 0.52 |
| 12-13 | 65 mm | 1.137 | 0.71 | 0.26 |
| 15-18 | 155 mm | 1.088 | 1.44 | 0.49 |
| 17-18 | 65 mm | 1.146 | 1.04 | 0.45 |
| 20-23 | 155 mm | 1.085 | 1.33 | 0.51 |
| 22-23 | 65 mm | 1.233 | 1.50 | 0.53 |
| 25-28 | 155 mm | 1.092 | 1.53 | 0.34 |
| 27-28 | 65 mm | 1.138 | 1.11 | 0.58 |

## Angle2's reflection timing: lag of the second family's first read after the onset family's

| config | lag, 5 / 25 / 50 / 75 / 95th percentile (ms) | earliest distinct echo delay, median (ms) |
|---|---|---|
| 000000 | -2 / 1 / 3 / 7 / 22 | - |
| 000001 | -2 / 1 / 3 / 7 / 21 | 12.9 |
| 000010 | -2 / 1 / 3 / 7 / 22 | 11.5 |
| 000100 | -2 / 1 / 3 / 8 / 21 | - |
| 001000 | -2 / 1 / 3 / 7 / 19 | 8.3 |
| 010000 | -2 / 1 / 3 / 7 / 22 | 2.6 |
| 011000 | -2 / 1 / 3 / 7 / 18 | 3.7 |
| 011100 | -2 / 1 / 3 / 7 / 18 | 3.7 |
| 011110 | -2 / 1 / 3 / 7 / 17 | 3.7 |
| 011111 | -2 / 1 / 3 / 7 / 16 | 3.7 |
| 020002 | -2 / 1 / 3 / 7 / 19 | 3.9 |

Spearman, lag against the earliest distinct echo delay: 0.06 (n=13848)

Angle2 returned no onset on 0 of 19008 cuts; no reflection on 0. GccPhat errors: 0; Angle2 errors: 0.
