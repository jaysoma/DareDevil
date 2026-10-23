## 1. How fast things move during voiced speech (LOCATA, 160 mm pair; median / 90th percentile)

| over | bearing (deg) | distance (m) | distance (%) | head orientation (deg) | facing the array (deg) |
|---|---|---|---|---|---|
| 0.25 s (all) | 1.08 / 3.34 | 0.02 / 0.08 | 1.25 / 4.79 | 2.7 / 10.0 | 2.9 / 10.2 |
| 0.25 s (task3) | 1.46 / 3.89 | 0.05 / 0.1 | 2.82 / 6.0 | 3.8 / 13.1 | 3.4 / 13.53 |
| 0.25 s (task4) | 1.0 / 3.22 | 0.02 / 0.07 | 1.07 / 4.33 | 2.6 / 9.6 | 2.8 / 9.9 |
| 0.5 s (all) | 2.17 / 6.66 | 0.04 / 0.15 | 2.46 / 9.45 | 5.3 / 19.0 | 5.5 / 19.1 |
| 0.5 s (task3) | 2.91 / 7.54 | 0.1 / 0.2 | 5.63 / 12.05 | 7.0 / 24.2 | 6.7 / 23.14 |
| 0.5 s (task4) | 2.04 / 6.4 | 0.04 / 0.13 | 2.13 / 8.47 | 4.9 / 18.4 | 5.3 / 18.7 |
| 1.0 s (all) | 4.46 / 13.36 | 0.09 / 0.28 | 4.75 / 17.51 | 9.4 / 34.8 | 10.1 / 34.2 |
| 1.0 s (task3) | 6.11 / 13.68 | 0.21 / 0.39 | 11.49 / 23.92 | 13.4 / 42.7 | 11.5 / 38.9 |
| 1.0 s (task4) | 4.16 / 13.26 | 0.07 / 0.25 | 4.08 / 15.56 | 8.7 / 34.4 | 9.8 / 33.6 |

## 2. Angle, all utterances (160 mm; error in deg, tolerance 10 deg)

| policy | utterances | time within 10 deg | median / mean error | moves per minute after the lock | out-of-tolerance episodes: count, median / 90th pct length (s) |
|---|---|---|---|---|---|
| GccPhat as shipped (settle, lock, hold) | 330 | 56.5% | 8.08 / 15.24 | 0.0 | 179, 1.05 / 2.46 |
| Angle2 at its onset, held | 330 | 45.8% | 11.49 / 20.01 | 0.0 | 114, 1.12 / 2.41 |
| re-read every 0.25 s, every read shown | 330 | 63.6% | 6.36 / 15.88 | 172.7 | 320, 0.4 / 1.4 |
| re-read every 0.25 s, dim rule and > 0 deg | 330 | 63.7% | 6.51 / 14.97 | 89.8 | 237, 0.5 / 1.6 |
| re-read every 0.25 s, dim rule and > 5 deg | 330 | 62.4% | 6.89 / 15.12 | 35.7 | 239, 0.5 / 1.67 |
| re-read every 0.25 s, dim rule and > 10 deg | 330 | 60.3% | 7.32 / 15.42 | 22.6 | 246, 0.6 / 1.62 |
| re-read every 0.25 s, dim rule and > 15 deg | 330 | 59.0% | 7.58 / 15.59 | 18.6 | 237, 0.7 / 1.75 |
| re-read every 0.5 s, every read shown | 330 | 62.6% | 6.69 / 15.9 | 92.5 | 280, 0.5 / 1.5 |
| re-read every 0.5 s, dim rule and > 0 deg | 330 | 62.2% | 6.94 / 14.94 | 47.4 | 228, 0.65 / 1.72 |
| re-read every 0.5 s, dim rule and > 5 deg | 330 | 61.4% | 7.15 / 15.02 | 26.4 | 233, 0.65 / 1.74 |
| re-read every 0.5 s, dim rule and > 10 deg | 330 | 59.6% | 7.53 / 15.27 | 18.4 | 235, 0.7 / 1.78 |
| re-read every 0.5 s, dim rule and > 15 deg | 330 | 58.2% | 7.74 / 15.47 | 14.7 | 225, 0.8 / 1.83 |

## 2. Angle, moving utterances (160 mm; error in deg, tolerance 10 deg)

(utterances in which the true bearing moved more than 10 deg)

| policy | utterances | time within 10 deg | median / mean error | moves per minute after the lock | out-of-tolerance episodes: count, median / 90th pct length (s) |
|---|---|---|---|---|---|
| GccPhat as shipped (settle, lock, hold) | 147 | 49.8% | 10.07 / 14.32 | 0.0 | 121, 1.1 / 2.5 |
| Angle2 at its onset, held | 147 | 35.4% | 15.2 / 19.57 | 0.0 | 92, 1.3 / 2.5 |
| re-read every 0.25 s, every read shown | 147 | 64.1% | 6.34 / 13.74 | 190.8 | 188, 0.35 / 1.5 |
| re-read every 0.25 s, dim rule and > 0 deg | 147 | 63.5% | 6.59 / 12.6 | 103.1 | 146, 0.47 / 1.68 |
| re-read every 0.25 s, dim rule and > 5 deg | 147 | 61.0% | 7.16 / 12.96 | 45.0 | 153, 0.5 / 1.75 |
| re-read every 0.25 s, dim rule and > 10 deg | 147 | 57.9% | 7.92 / 13.45 | 26.6 | 160, 0.6 / 1.75 |
| re-read every 0.25 s, dim rule and > 15 deg | 147 | 54.9% | 8.65 / 13.87 | 20.1 | 153, 0.75 / 1.8 |
| re-read every 0.5 s, every read shown | 147 | 62.2% | 6.77 / 13.55 | 100.8 | 174, 0.45 / 1.6 |
| re-read every 0.5 s, dim rule and > 0 deg | 147 | 60.4% | 7.34 / 12.76 | 53.6 | 150, 0.6 / 1.8 |
| re-read every 0.5 s, dim rule and > 5 deg | 147 | 59.2% | 7.66 / 12.93 | 33.7 | 153, 0.6 / 1.79 |
| re-read every 0.5 s, dim rule and > 10 deg | 147 | 56.4% | 8.3 / 13.36 | 22.2 | 156, 0.7 / 1.83 |
| re-read every 0.5 s, dim rule and > 15 deg | 147 | 53.2% | 9.1 / 13.82 | 16.5 | 148, 0.83 / 1.95 |

## 2. Angle, still utterances (160 mm; error in deg, tolerance 10 deg)

| policy | utterances | time within 10 deg | median / mean error | moves per minute after the lock | out-of-tolerance episodes: count, median / 90th pct length (s) |
|---|---|---|---|---|---|
| GccPhat as shipped (settle, lock, hold) | 183 | 63.7% | 6.78 / 16.21 | 0.0 | 58, 0.95 / 2.32 |
| Angle2 at its onset, held | 183 | 56.9% | 7.88 / 20.48 | 0.0 | 22, 0.45 / 1.15 |
| re-read every 0.25 s, every read shown | 183 | 63.1% | 6.38 / 18.14 | 151.9 | 132, 0.45 / 1.2 |
| re-read every 0.25 s, dim rule and > 0 deg | 183 | 64.0% | 6.43 / 17.47 | 74.5 | 91, 0.5 / 1.45 |
| re-read every 0.25 s, dim rule and > 5 deg | 183 | 63.8% | 6.56 / 17.41 | 25.1 | 86, 0.53 / 1.52 |
| re-read every 0.25 s, dim rule and > 10 deg | 183 | 62.9% | 6.78 / 17.5 | 18.1 | 86, 0.58 / 1.55 |
| re-read every 0.25 s, dim rule and > 15 deg | 183 | 63.3% | 6.7 / 17.41 | 16.9 | 84, 0.58 / 1.54 |
| re-read every 0.5 s, every read shown | 183 | 62.9% | 6.6 / 18.38 | 83.0 | 106, 0.5 / 1.45 |
| re-read every 0.5 s, dim rule and > 0 deg | 183 | 64.1% | 6.57 / 17.26 | 40.3 | 78, 0.68 / 1.55 |
| re-read every 0.5 s, dim rule and > 5 deg | 183 | 63.8% | 6.67 / 17.22 | 18.1 | 80, 0.65 / 1.57 |
| re-read every 0.5 s, dim rule and > 10 deg | 183 | 62.9% | 6.81 / 17.29 | 14.0 | 79, 0.7 / 1.58 |
| re-read every 0.5 s, dim rule and > 15 deg | 183 | 63.5% | 6.67 / 17.21 | 12.5 | 77, 0.7 / 1.55 |

## 2. Angle, task3 utterances (160 mm; error in deg, tolerance 10 deg)

| policy | utterances | time within 10 deg | median / mean error | moves per minute after the lock | out-of-tolerance episodes: count, median / 90th pct length (s) |
|---|---|---|---|---|---|
| GccPhat as shipped (settle, lock, hold) | 50 | 64.9% | 6.03 / 9.77 | 0.0 | 25, 1.25 / 2.03 |
| Angle2 at its onset, held | 50 | 63.5% | 6.57 / 10.63 | 0.0 | 26, 1.05 / 1.95 |
| re-read every 0.25 s, every read shown | 50 | 76.3% | 4.77 / 8.0 | 169.3 | 34, 0.3 / 1.39 |
| re-read every 0.25 s, dim rule and > 0 deg | 50 | 74.7% | 4.87 / 7.69 | 89.4 | 31, 0.55 / 1.45 |
| re-read every 0.25 s, dim rule and > 5 deg | 50 | 73.6% | 4.9 / 7.8 | 33.2 | 32, 0.5 / 1.45 |
| re-read every 0.25 s, dim rule and > 10 deg | 50 | 71.3% | 5.18 / 8.17 | 18.2 | 32, 0.58 / 1.45 |
| re-read every 0.25 s, dim rule and > 15 deg | 50 | 68.7% | 5.62 / 8.67 | 10.3 | 27, 1.1 / 1.65 |
| re-read every 0.5 s, every read shown | 50 | 73.9% | 4.79 / 7.83 | 91.8 | 32, 0.5 / 1.49 |
| re-read every 0.5 s, dim rule and > 0 deg | 50 | 71.8% | 5.16 / 8.11 | 46.7 | 30, 0.65 / 1.69 |
| re-read every 0.5 s, dim rule and > 5 deg | 50 | 71.7% | 5.18 / 8.14 | 25.3 | 29, 0.65 / 1.72 |
| re-read every 0.5 s, dim rule and > 10 deg | 50 | 69.2% | 5.45 / 8.48 | 15.8 | 31, 0.8 / 1.65 |
| re-read every 0.5 s, dim rule and > 15 deg | 50 | 67.7% | 5.8 / 8.87 | 7.9 | 27, 1.1 / 1.71 |

## 2. Angle, task4 utterances (160 mm; error in deg, tolerance 10 deg)

| policy | utterances | time within 10 deg | median / mean error | moves per minute after the lock | out-of-tolerance episodes: count, median / 90th pct length (s) |
|---|---|---|---|---|---|
| GccPhat as shipped (settle, lock, hold) | 280 | 55.1% | 8.47 / 16.15 | 0.0 | 154, 1.0 / 2.49 |
| Angle2 at its onset, held | 280 | 42.8% | 13.01 / 21.63 | 0.0 | 88, 1.15 / 2.46 |
| re-read every 0.25 s, every read shown | 280 | 61.5% | 6.75 / 17.21 | 173.3 | 286, 0.45 / 1.4 |
| re-read every 0.25 s, dim rule and > 0 deg | 280 | 61.9% | 6.89 / 16.19 | 89.9 | 206, 0.5 / 1.6 |
| re-read every 0.25 s, dim rule and > 5 deg | 280 | 60.5% | 7.34 / 16.35 | 36.1 | 207, 0.5 / 1.69 |
| re-read every 0.25 s, dim rule and > 10 deg | 280 | 58.4% | 7.73 / 16.64 | 23.4 | 214, 0.62 / 1.64 |
| re-read every 0.25 s, dim rule and > 15 deg | 280 | 57.3% | 7.91 / 16.75 | 20.0 | 210, 0.7 / 1.75 |
| re-read every 0.5 s, every read shown | 280 | 60.7% | 7.08 / 17.25 | 92.7 | 248, 0.5 / 1.5 |
| re-read every 0.5 s, dim rule and > 0 deg | 280 | 60.6% | 7.32 / 16.09 | 47.5 | 198, 0.65 / 1.72 |
| re-read every 0.5 s, dim rule and > 5 deg | 280 | 59.7% | 7.59 / 16.17 | 26.6 | 204, 0.65 / 1.74 |
| re-read every 0.5 s, dim rule and > 10 deg | 280 | 57.9% | 7.85 / 16.42 | 18.8 | 204, 0.7 / 1.79 |
| re-read every 0.5 s, dim rule and > 15 deg | 280 | 56.6% | 8.08 / 16.58 | 15.8 | 198, 0.75 / 1.85 |

80 mm pair, all utterances:

| policy | time within 10 deg | median / mean error | moves per minute | episodes, median / 90th pct (s) |
|---|---|---|---|---|
| GccPhat as shipped (settle, lock, hold) | 56.7% | 8.29 / 14.28 | 0.0 | 182, 1.05 / 2.05 |
| Angle2 at its onset, held | 44.2% | 11.79 / 19.31 | 0.0 | 114, 1.23 / 2.29 |
| re-read every 0.25 s, every read shown | 63.1% | 6.66 / 15.45 | 182.4 | 297, 0.45 / 1.32 |
| re-read every 0.25 s, dim rule and > 0 deg | 63.1% | 6.84 / 13.71 | 100.6 | 242, 0.5 / 1.45 |
| re-read every 0.25 s, dim rule and > 5 deg | 62.4% | 7.01 / 13.87 | 39.2 | 240, 0.5 / 1.45 |
| re-read every 0.25 s, dim rule and > 10 deg | 61.3% | 7.29 / 14.09 | 24.2 | 243, 0.55 / 1.5 |
| re-read every 0.25 s, dim rule and > 15 deg | 59.2% | 7.78 / 14.41 | 17.4 | 231, 0.65 / 1.6 |
| re-read every 0.5 s, every read shown | 62.3% | 6.89 / 15.25 | 93.7 | 276, 0.47 / 1.5 |
| re-read every 0.5 s, dim rule and > 0 deg | 62.4% | 7.03 / 13.79 | 53.0 | 230, 0.53 / 1.5 |
| re-read every 0.5 s, dim rule and > 5 deg | 61.5% | 7.22 / 13.9 | 29.2 | 233, 0.55 / 1.5 |
| re-read every 0.5 s, dim rule and > 10 deg | 60.2% | 7.52 / 14.13 | 19.4 | 230, 0.65 / 1.55 |
| re-read every 0.5 s, dim rule and > 15 deg | 58.2% | 7.99 / 14.46 | 13.2 | 219, 0.7 / 1.7 |

## 3. Range, 160 mm (distance ratio to the opener; error in dB of distance, tolerance 25% = 1.9 dB)

| policy | utterances | time within 25% | median / mean error (dB) | moves per minute | episodes, median / 90th pct (s) | follows a real >20% change |
|---|---|---|---|---|---|---|
| per utterance, shipped | 306 | 50.6% | 1.92 / 2.44 | 0.0 | 35, 0.7 / 1.83 | never moves |
| sliding 0.5 s, shipped | 306 | 30.5% | 3.16 / 3.5 | 77.4 | 218, 0.55 / 1.72 | 57.9% right way (n=57) |
| sliding 1.0 s, shipped | 306 | 35.2% | 2.71 / 3.15 | 34.5 | 162, 0.5 / 1.99 | 57.9% right way (n=57) |
| per utterance, lf | 306 | 38.8% | 2.44 / 3.09 | 0.0 | 32, 0.73 / 2.01 | never moves |
| sliding 0.5 s, lf | 306 | 34.6% | 2.81 / 3.42 | 90.7 | 214, 0.5 / 1.32 | 52.6% right way (n=57) |
| sliding 1.0 s, lf | 306 | 36.1% | 2.78 / 3.29 | 40.2 | 137, 0.5 / 1.5 | 57.9% right way (n=57) |

## 3. Range, 80 mm (distance ratio to the opener; error in dB of distance, tolerance 25% = 1.9 dB)

| policy | utterances | time within 25% | median / mean error (dB) | moves per minute | episodes, median / 90th pct (s) | follows a real >20% change |
|---|---|---|---|---|---|---|
| per utterance, shipped | 306 | 45.9% | 2.19 / 2.81 | 0.0 | 27, 0.6 / 1.19 | never moves |
| sliding 0.5 s, shipped | 306 | 26.3% | 3.48 / 3.91 | 81.7 | 172, 0.5 / 1.95 | 63.2% right way (n=57) |
| sliding 1.0 s, shipped | 306 | 31.4% | 3.11 / 3.56 | 36.7 | 120, 0.75 / 2.15 | 63.2% right way (n=57) |
| per utterance, lf | 306 | 39.6% | 2.47 / 2.73 | 0.0 | 29, 0.7 / 2.1 | never moves |
| sliding 0.5 s, lf | 306 | 33.4% | 2.94 / 3.24 | 90.1 | 195, 0.5 / 1.48 | 52.6% right way (n=57) |
| sliding 1.0 s, lf | 306 | 36.5% | 2.76 / 3.04 | 38.7 | 131, 0.5 / 1.4 | 47.4% right way (n=57) |

## 4. Facing: the truth's own rate of change (a perfect facing reading, held)

| update | time within 30 deg | median / mean error (deg) | updates per minute |
|---|---|---|---|
| per utterance | 83.3% | 9.7 / 15.96 | 0.0 |
| per phrase | 83.5% | 9.4 / 15.66 | 1.4 |
| every 0.25s | 100.0% | 0.8 / 1.75 | 196.4 |
| every 0.5s | 99.6% | 1.8 / 3.71 | 98.1 |

Facing turns a median 25.1 deg within an utterance (90th percentile 66.7; over 30 deg in 41.5%), and 24.5 deg within a phrase. An utterance has 1.05 phrases on average, so per phrase and per utterance are nearly the same updates.
