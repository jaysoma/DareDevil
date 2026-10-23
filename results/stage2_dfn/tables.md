## 1. Level: lsnr (dB), median per recording and pair

| data | quantity | median | p10 | p90 | min | max | n |
|---|---|---|---|---|---|---|---|
| starss23 | speech_dbfs | -41.88 | -49.49 | -36.54 | -63.85 | -30.87 | 314 |
| starss23 | gain_db | 15.33 | 8.39 | 23.25 | 0.0 | 37.85 | 336 |
| starss23 | lsnr_speech_raw | -11.77 | -15.0 | -4.62 | -15.0 | 2.87 | 314 |
| starss23 | lsnr_speech_norm | -6.85 | -12.52 | -1.44 | -14.67 | 0.98 | 314 |
| starss23 | lsnr_gap_raw | -13.16 | -15.0 | -6.59 | -15.0 | 0.31 | 268 |
| starss23 | lsnr_gap_norm | -14.39 | -14.94 | -12.04 | -15.0 | -1.19 | 268 |
| starss23 | lsnr_speech_moved_db | 3.32 | -1.27 | 10.67 | -13.15 | 15.88 | 314 |
| locata | speech_dbfs | -43.74 | -46.4 | -41.89 | -48.71 | -40.92 | 32 |
| locata | gain_db | 17.74 | 15.89 | 20.4 | 14.92 | 22.71 | 32 |
| locata | lsnr_speech_raw | -0.27 | -14.99 | 2.32 | -15.0 | 3.57 | 32 |
| locata | lsnr_speech_norm | 0.92 | -1.91 | 3.07 | -2.53 | 3.66 | 32 |
| locata | lsnr_gap_raw | -4.14 | -15.0 | 5.74 | -15.0 | 9.86 | 32 |
| locata | lsnr_gap_norm | -7.21 | -11.89 | -3.81 | -13.71 | -2.27 | 32 |
| locata | lsnr_speech_moved_db | 2.15 | -2.17 | 13.58 | -3.17 | 14.75 | 32 |

## 2-3. The gates: lsnr over 0 dB (and -5, +5), and the mixdown mask over 0.2-0.5

| data | level | gate | speech onsets | opened % | already open % | missed % | latency median s | within 100 ms % | vs MF onset median s | within 50 ms of MF % | gap frames open % | gap opens / min | non-speech onsets | non-speech opened % |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| locata | norm | lsnr | 682 | 84.3 | 15.7 | 0.0 | -0.02 | 63.0 | -0.01 | 65.3 | 14.61 | 164.12 | 0 |  |
| locata | norm | lsnr+5 | 682 | 88.7 | 1.9 | 9.4 | 0.0 | 53.1 | 0.01 | 62.3 | 2.06 | 44.76 | 0 |  |
| locata | norm | lsnr-5 | 682 | 63.8 | 36.2 | 0.0 | -0.03 | 60.7 | -0.06 | 43.1 | 40.56 | 256.5 | 0 |  |
| locata | norm | mask0.2 | 682 | 10.0 | 90.0 | 0.0 | -0.08 | 55.9 | -0.15 | 27.8 | 89.34 | 140.02 | 0 |  |
| locata | norm | mask0.3 | 682 | 67.6 | 32.1 | 0.3 | -0.12 | 44.0 | -0.13 | 27.3 | 27.08 | 177.89 | 0 |  |
| locata | norm | mask0.4 | 682 | 95.0 | 4.0 | 1.0 | -0.03 | 47.2 | -0.03 | 32.4 | 7.27 | 83.78 | 0 |  |
| locata | norm | mask0.5 | 682 | 88.7 | 0.0 | 11.3 | 0.05 | 36.5 | 0.07 | 15.7 | 1.23 | 23.53 | 0 |  |
| locata | raw | lsnr | 682 | 60.4 | 28.0 | 11.6 | -0.03 | 45.9 | -0.03 | 41.4 | 30.95 | 157.8 | 0 |  |
| locata | raw | lsnr+5 | 682 | 65.7 | 11.7 | 22.6 | -0.02 | 53.3 | -0.01 | 50.3 | 17.07 | 146.33 | 0 |  |
| locata | raw | lsnr-5 | 682 | 40.5 | 52.8 | 6.7 | -0.07 | 41.7 | -0.04 | 31.5 | 51.65 | 136.57 | 0 |  |
| locata | raw | mask0.2 | 682 | 30.1 | 66.7 | 3.2 | -0.03 | 52.2 | -0.01 | 36.1 | 68.97 | 32.71 | 0 |  |
| locata | raw | mask0.3 | 682 | 69.2 | 12.9 | 17.9 | -0.01 | 38.3 | -0.0 | 30.2 | 31.84 | 98.7 | 0 |  |
| locata | raw | mask0.4 | 682 | 49.0 | 0.6 | 50.4 | 0.14 | 26.6 | 0.15 | 16.1 | 0.61 | 14.92 | 0 |  |
| locata | raw | mask0.5 | 682 | 25.5 | 0.3 | 74.2 | 0.36 | 16.1 | 0.36 | 5.5 | 0.02 | 1.15 | 0 |  |
| starss23 | norm | lsnr | 11936 | 89.8 | 1.6 | 8.6 | 0.06 | 43.8 | -0.0 | 64.9 | 2.53 | 22.3 | 1232 | 30.6 |
| starss23 | norm | lsnr+5 | 11936 | 67.3 | 0.2 | 32.5 | 0.13 | 34.7 | 0.02 | 53.7 | 1.17 | 13.46 | 1232 | 20.9 |
| starss23 | norm | lsnr-5 | 11936 | 90.7 | 6.0 | 3.3 | 0.04 | 50.3 | -0.02 | 61.3 | 6.06 | 43.25 | 1232 | 39.9 |
| starss23 | norm | mask0.2 | 11936 | 74.4 | 18.7 | 6.9 | -0.03 | 30.2 | -0.07 | 22.5 | 23.5 | 175.26 | 1232 | 52.7 |
| starss23 | norm | mask0.3 | 11936 | 62.2 | 2.6 | 35.2 | 0.17 | 24.7 | 0.1 | 16.9 | 5.51 | 11.49 | 1232 | 9.9 |
| starss23 | norm | mask0.4 | 11936 | 46.1 | 0.4 | 53.5 | 0.29 | 18.4 | 0.22 | 9.0 | 1.63 | 6.31 | 1232 | 3.2 |
| starss23 | norm | mask0.5 | 11936 | 26.3 | 0.0 | 73.7 | 0.37 | 15.2 | 0.31 | 3.6 | 0.02 | 0.36 | 1232 | 0.2 |
| starss23 | raw | lsnr | 11936 | 45.8 | 2.3 | 51.9 | 0.05 | 39.8 | -0.01 | 52.3 | 7.57 | 68.83 | 1232 | 27.1 |
| starss23 | raw | lsnr+5 | 11936 | 33.2 | 0.5 | 66.3 | 0.1 | 35.0 | 0.01 | 49.9 | 3.01 | 37.36 | 1232 | 17.3 |
| starss23 | raw | lsnr-5 | 11936 | 54.9 | 8.6 | 36.4 | 0.02 | 41.4 | -0.03 | 42.4 | 18.75 | 105.28 | 1232 | 33.8 |
| starss23 | raw | mask0.2 | 11936 | 41.7 | 41.9 | 16.4 | -0.08 | 29.0 | -0.09 | 15.7 | 60.35 | 99.92 | 1232 | 37.0 |
| starss23 | raw | mask0.3 | 11936 | 29.9 | 16.2 | 53.9 | 0.04 | 29.0 | 0.02 | 14.0 | 30.76 | 36.62 | 1232 | 19.3 |
| starss23 | raw | mask0.4 | 11936 | 17.9 | 3.3 | 78.7 | 0.16 | 22.8 | 0.1 | 9.2 | 11.79 | 30.98 | 1232 | 10.0 |
| starss23 | raw | mask0.5 | 11936 | 3.8 | 0.0 | 96.2 | 0.44 | 7.9 | 0.4 | 2.4 | 0.06 | 0.41 | 1232 | 0.5 |

### Non-speech onsets that open the gate, by class (STARSS23): n, % opened

| level | gate | class n / % opened |
|---|---|---|
| norm | lsnr | musical instrument 242 / 15.3; laughter 224 / 71.9; footsteps 184 / 15.2; door/cupboard 146 / 45.9; bell 96 / 3.1; domestic sounds 82 / 25.6; telephone 70 / 8.6; clapping 60 / 18.3; music 60 / 30.0; knock 36 / 47.2; water tap 32 / 25.0 |
| norm | lsnr+5 | musical instrument 242 / 7.4; laughter 224 / 52.2; footsteps 184 / 4.3; door/cupboard 146 / 40.4; bell 96 / 3.1; domestic sounds 82 / 12.2; telephone 70 / 2.9; clapping 60 / 10.0; music 60 / 28.3; knock 36 / 38.9; water tap 32 / 12.5 |
| norm | lsnr-5 | musical instrument 242 / 21.9; laughter 224 / 77.7; footsteps 184 / 29.3; door/cupboard 146 / 57.5; bell 96 / 7.3; domestic sounds 82 / 35.4; telephone 70 / 24.3; clapping 60 / 26.7; music 60 / 35.0; knock 36 / 77.8; water tap 32 / 28.1 |
| norm | mask0.2 | musical instrument 242 / 34.7; laughter 224 / 75.0; footsteps 184 / 48.4; door/cupboard 146 / 64.4; bell 96 / 43.8; domestic sounds 82 / 50.0; telephone 70 / 34.3; clapping 60 / 71.7; music 60 / 41.7; knock 36 / 66.7; water tap 32 / 46.9 |
| norm | mask0.3 | musical instrument 242 / 9.5; laughter 224 / 29.5; footsteps 184 / 7.6; door/cupboard 146 / 3.4; bell 96 / 0.0; domestic sounds 82 / 6.1; telephone 70 / 1.4; clapping 60 / 1.7; music 60 / 6.7; knock 36 / 8.3; water tap 32 / 0.0 |
| norm | mask0.4 | musical instrument 242 / 6.6; laughter 224 / 5.4; footsteps 184 / 3.8; door/cupboard 146 / 0.7; bell 96 / 0.0; domestic sounds 82 / 1.2; telephone 70 / 0.0; clapping 60 / 0.0; music 60 / 3.3; knock 36 / 0.0; water tap 32 / 3.1 |
| norm | mask0.5 | musical instrument 242 / 0.8; laughter 224 / 0.0; footsteps 184 / 0.0; door/cupboard 146 / 0.0; bell 96 / 0.0; domestic sounds 82 / 0.0; telephone 70 / 0.0; clapping 60 / 0.0; music 60 / 1.7; knock 36 / 0.0; water tap 32 / 0.0 |
| raw | lsnr | musical instrument 242 / 14.5; laughter 224 / 49.6; footsteps 184 / 20.7; door/cupboard 146 / 47.9; bell 96 / 2.1; domestic sounds 82 / 22.0; telephone 70 / 11.4; clapping 60 / 43.3; music 60 / 3.3; knock 36 / 52.8; water tap 32 / 15.6 |
| raw | lsnr+5 | musical instrument 242 / 7.9; laughter 224 / 28.1; footsteps 184 / 15.8; door/cupboard 146 / 41.8; bell 96 / 2.1; domestic sounds 82 / 6.1; telephone 70 / 11.4; clapping 60 / 15.0; music 60 / 3.3; knock 36 / 33.3; water tap 32 / 9.4 |
| raw | lsnr-5 | musical instrument 242 / 19.0; laughter 224 / 62.9; footsteps 184 / 26.1; door/cupboard 146 / 44.5; bell 96 / 15.6; domestic sounds 82 / 31.7; telephone 70 / 14.3; clapping 60 / 48.3; music 60 / 13.3; knock 36 / 61.1; water tap 32 / 21.9 |
| raw | mask0.2 | musical instrument 242 / 35.1; laughter 224 / 47.3; footsteps 184 / 18.5; door/cupboard 146 / 52.7; bell 96 / 49.0; domestic sounds 82 / 32.9; telephone 70 / 22.9; clapping 60 / 43.3; music 60 / 16.7; knock 36 / 58.3; water tap 32 / 21.9 |
| raw | mask0.3 | musical instrument 242 / 14.9; laughter 224 / 29.9; footsteps 184 / 20.7; door/cupboard 146 / 21.9; bell 96 / 0.0; domestic sounds 82 / 14.6; telephone 70 / 22.9; clapping 60 / 38.3; music 60 / 8.3; knock 36 / 25.0; water tap 32 / 0.0 |
| raw | mask0.4 | musical instrument 242 / 9.1; laughter 224 / 8.5; footsteps 184 / 10.9; door/cupboard 146 / 13.7; bell 96 / 0.0; domestic sounds 82 / 3.7; telephone 70 / 12.9; clapping 60 / 43.3; music 60 / 0.0; knock 36 / 8.3; water tap 32 / 3.1 |
| raw | mask0.5 | musical instrument 242 / 0.4; laughter 224 / 0.0; footsteps 184 / 0.0; door/cupboard 146 / 0.7; bell 96 / 0.0; domestic sounds 82 / 0.0; telephone 70 / 0.0; clapping 60 / 6.7; music 60 / 0.0; knock 36 / 0.0; water tap 32 / 0.0 |

### Soft first words (STARSS23 pair 1-2): % of speech onsets open within 300 ms, by MF voice-over-pause quartile (softest first)

| level|gate | quartile edges dB | Q1 | Q2 | Q3 | Q4 |
|---|---|---|---|---|---|
| norm|lsnr | [2.2, 7.8, 14.8] | 61.9 | 71.9 | 81.6 | 90.6 |
| norm|lsnr+5 | [2.2, 7.8, 14.8] | 31.0 | 40.0 | 50.8 | 71.9 |
| norm|lsnr-5 | [2.2, 7.8, 14.8] | 75.1 | 84.2 | 89.5 | 94.6 |
| norm|mask0.2 | [2.2, 7.8, 14.8] | 79.6 | 74.7 | 83.1 | 86.6 |
| norm|mask0.3 | [2.2, 7.8, 14.8] | 40.5 | 36.9 | 43.2 | 49.9 |
| norm|mask0.4 | [2.2, 7.8, 14.8] | 25.1 | 22.7 | 24.1 | 27.1 |
| norm|mask0.5 | [2.2, 7.8, 14.8] | 13.6 | 10.8 | 11.0 | 12.8 |
| raw|lsnr | [2.2, 7.8, 14.8] | 28.7 | 34.3 | 45.1 | 53.8 |
| raw|lsnr+5 | [2.2, 7.8, 14.8] | 17.2 | 19.6 | 27.3 | 41.1 |
| raw|lsnr-5 | [2.2, 7.8, 14.8] | 45.6 | 50.2 | 63.2 | 66.1 |
| raw|mask0.2 | [2.2, 7.8, 14.8] | 78.2 | 73.1 | 81.9 | 78.6 |
| raw|mask0.3 | [2.2, 7.8, 14.8] | 35.7 | 31.0 | 39.7 | 42.3 |
| raw|mask0.4 | [2.2, 7.8, 14.8] | 13.0 | 9.5 | 14.6 | 16.7 |
| raw|mask0.5 | [2.2, 7.8, 14.8] | 1.7 | 0.9 | 1.2 | 1.2 |

## 4-5. GccPhat by variant: raw pair (none), mask from the mixdown (mix), from capsule L (cap), DFN pair (dfn), at each level

| data | variant | reads | >10 % | >36 % | aliasing | 0 deg pull | other | moved in | moved out | kept % | mean | median | within 10 % |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| locata | cap@norm | 682 | 28.6 | 12.5 | 0 | 41 | 7 | 9 | 20 | 87.5 | 7.3 | 5.1 | 81.6 |
| locata | cap@raw | 682 | 27.1 | 11.6 | 0 | 37 | 5 | 13 | 14 | 88.4 | 7.3 | 5.1 | 82.4 |
| locata | dfn@norm | 682 | 27.0 | 11.0 | 0 | 38 | 8 | 7 | 7 | 89.0 | 7.3 | 5.0 | 82.0 |
| locata | dfn@raw | 682 | 26.7 | 10.6 | 0 | 40 | 7 | 8 | 6 | 89.4 | 7.4 | 5.1 | 82.0 |
| locata | mix@norm | 682 | 28.6 | 12.5 | 0 | 41 | 6 | 9 | 20 | 87.5 | 7.2 | 5.1 | 81.6 |
| locata | mix@raw | 682 | 27.0 | 11.0 | 0 | 33 | 5 | 16 | 16 | 89.0 | 7.3 | 5.3 | 82.0 |
| locata | raw | 682 | 27.0 | 11.3 | 0 | 39 | 4 | 0 | 0 | 88.7 | 7.4 | 5.2 | 82.3 |
| starss23 | cap@norm | 14982 | 48.4 | 19.1 | 96 | 501 | 1849 | 668 | 661 | 80.9 | 9.7 | 6.6 | 63.9 |
| starss23 | cap@raw | 14982 | 48.6 | 19.0 | 95 | 518 | 1846 | 667 | 692 | 81.0 | 9.8 | 6.8 | 63.5 |
| starss23 | dfn@norm | 14980 | 47.0 | 18.8 | 84 | 592 | 1618 | 565 | 349 | 82.1 | 9.4 | 6.3 | 65.2 |
| starss23 | dfn@raw | 14982 | 47.9 | 19.3 | 90 | 586 | 1672 | 388 | 306 | 80.7 | 9.5 | 6.4 | 64.8 |
| starss23 | mix@norm | 14982 | 48.4 | 19.1 | 93 | 509 | 1864 | 685 | 671 | 80.8 | 9.7 | 6.6 | 64.0 |
| starss23 | mix@raw | 14982 | 48.6 | 19.0 | 96 | 522 | 1841 | 661 | 685 | 80.8 | 9.8 | 6.8 | 63.6 |
| starss23 | raw | 14982 | 48.4 | 19.5 | 86 | 601 | 1639 | 0 | 0 | 80.5 | 9.6 | 6.4 | 64.1 |

### Every class, wrong reads (>10 deg)

| data|variant | aliasing | zero_pull | other | mirror | endfire | pause_direction | other_source | truth_in_2_3 | drift | facing |
|---|---|---|---|---|---|---|---|---|---|---|
| locata|cap@norm | 0 | 41 | 7 | 15 | 0 | 103 | 109 | 85 | 88 | 70 |
| locata|cap@raw | 0 | 37 | 5 | 15 | 0 | 102 | 107 | 78 | 85 | 72 |
| locata|dfn@norm | 0 | 38 | 8 | 15 | 0 | 95 | 103 | 79 | 83 | 71 |
| locata|dfn@raw | 0 | 40 | 7 | 15 | 0 | 94 | 104 | 78 | 79 | 69 |
| locata|mix@norm | 0 | 41 | 6 | 15 | 0 | 103 | 109 | 85 | 90 | 70 |
| locata|mix@raw | 0 | 33 | 5 | 18 | 0 | 100 | 105 | 75 | 85 | 72 |
| locata|raw | 0 | 39 | 4 | 16 | 0 | 98 | 108 | 83 | 81 | 71 |
| starss23|cap@norm | 96 | 501 | 1849 | 425 | 1088 | 2725 | 2666 | 887 | 1300 | 0 |
| starss23|cap@raw | 95 | 518 | 1846 | 465 | 1120 | 2768 | 2681 | 884 | 1276 | 0 |
| starss23|dfn@norm | 84 | 592 | 1618 | 430 | 1044 | 2860 | 2788 | 1237 | 1255 | 0 |
| starss23|dfn@raw | 90 | 586 | 1672 | 435 | 1072 | 2939 | 2767 | 1275 | 1266 | 0 |
| starss23|mix@norm | 93 | 509 | 1864 | 425 | 1108 | 2732 | 2670 | 884 | 1286 | 0 |
| starss23|mix@raw | 96 | 522 | 1841 | 471 | 1145 | 2786 | 2697 | 866 | 1268 | 0 |
| starss23|raw | 86 | 601 | 1639 | 456 | 1083 | 3003 | 2840 | 1341 | 1283 | 0 |

## 4. Mechanism: the mask in bands where L and R cancel (in-phase ratio < 0.25) and add (> 0.75), norm level

| data | reads | cancel share | mix: cancel / add | cap: cancel / add | mix - cap in cancel bands | mix - cap in add bands | corr(mix - cap, in-phase) | % positive |
|---|---|---|---|---|---|---|---|---|
| starss23 | 14996 | 0.03 | [0.25, 0.25] | [0.25, 0.25] | -0.0 | -0.0 | 0.03 | 53.9 |
| locata | 682 | 0.07 | [0.36, 0.29] | [0.38, 0.3] | -0.01 | -0.0 | 0.14 | 66.7 |

## 5. The shared operator: GccPhat on the DFN pair against the raw pair, read by read

| data|level | reads | same within 1 deg % | within 5 % | moved > 10 deg % | median |change| |
|---|---|---|---|---|---|
| locata|norm | 682 | 90.9 | 97.9 | 1.8 | 0.0 |
| locata|raw | 682 | 91.6 | 98.2 | 1.5 | 0.0 |
| starss23|norm | 14980 | 62.8 | 89.8 | 6.2 | 0.56 |
| starss23|raw | 14982 | 71.2 | 92.8 | 4.3 | 0.49 |

## 6. Clues: GccPhat's right reads against its wrong ones (speech onsets, raw variant). AUC: the chance a wrong read has the lower clue (0.5 = no signal)

| data|level|clue | right median | wrong median | AUC | right n | wrong n |
|---|---|---|---|---|---|
| locata|norm|lsnr_cap_on | 1.77 | 1.37 | 0.557 | 498 | 184 |
| locata|norm|lsnr_max200 | 7.0 | 5.81 | 0.613 | 498 | 184 |
| locata|norm|lsnr_on | 1.67 | 1.64 | 0.548 | 498 | 184 |
| locata|norm|mask_band | 0.37 | 0.35 | 0.606 | 498 | 184 |
| locata|norm|mask_cap_band | 0.38 | 0.36 | 0.605 | 498 | 184 |
| locata|raw|lsnr_cap_on | 4.06 | 4.54 | 0.489 | 498 | 184 |
| locata|raw|lsnr_max200 | 8.07 | 7.78 | 0.515 | 498 | 184 |
| locata|raw|lsnr_on | 1.59 | 2.57 | 0.479 | 498 | 184 |
| locata|raw|mask_band | 0.25 | 0.25 | 0.501 | 498 | 184 |
| locata|raw|mask_cap_band | 0.31 | 0.29 | 0.561 | 498 | 184 |
| starss23|norm|lsnr_cap_on | -12.49 | -12.6 | 0.507 | 6337 | 5597 |
| starss23|norm|lsnr_max200 | 4.07 | 1.62 | 0.589 | 6337 | 5597 |
| starss23|norm|lsnr_on | -12.85 | -13.03 | 0.509 | 6337 | 5597 |
| starss23|norm|mask_band | 0.2 | 0.19 | 0.58 | 6337 | 5597 |
| starss23|norm|mask_cap_band | 0.21 | 0.19 | 0.587 | 6337 | 5597 |
| starss23|raw|lsnr_cap_on | -10.63 | -10.91 | 0.499 | 6337 | 5597 |
| starss23|raw|lsnr_max200 | -5.47 | -6.16 | 0.503 | 6337 | 5597 |
| starss23|raw|lsnr_on | -11.9 | -11.82 | 0.485 | 6337 | 5597 |
| starss23|raw|mask_band | 0.2 | 0.2 | 0.511 | 6337 | 5597 |
| starss23|raw|mask_cap_band | 0.2 | 0.19 | 0.526 | 6337 | 5597 |

## 7. Cost

| audio s | DFN s per audio s, mixdown pass + shared operator | capsule pass |
|---|---|---|
| 108873.9 | 0.0797 | 0.0675 |
