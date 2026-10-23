# Brief 16: DFN's internals, a live speech gate, and why the mask helped the ghost (2026-10-23)

## What was run
- **Model:** the stock DeepFilterNet3 (deepfilternet 0.5.6, its released weights), with Jay's shared operator
  (`dfn/dfn_shared.py`):
  - one model pass on the L+R mixdown;
  - its mask and deep filter applied identically to L and R;
  - the 12 dB attenuation limit.
- **Whole recordings, in order, as the app runs.**
  - STARSS23: all 168 development recordings, through capsule pairs 1-2 and 3-4. That's 14,996 of batch A's reads:
    11,936 speech onsets and 3,060 others (footsteps, door, knock, ...).
  - LOCATA: all 16 recordings batch A read (tasks 3 and 4), both pairs: 682 reads.
  - 30.2 hours of audio per level, keyed by batch A's `id`. Batch A's records are untouched; this adds files.
- **Two levels throughout (test 1):**
  - `raw`: as recorded.
  - `norm`: one fixed gain per recording and pair, putting labelled speech at -26 dBFS. Labels are STARSS23's speech
    classes or LOCATA's VAD.
- **GccPhat:** run through batch A's own path. The raw variant reproduces batch A's stored read on 14,973 of 14,982
  STARSS23 reads and 679 of 682 LOCATA reads.
- **Scoring:** classes and Jay's rule exactly as batch A computed them. STARSS23 is judged against the sphere
  reference; LOCATA against the tracked head.
- **Harness:** `harness/stage2_dfn/` (README there). The one scheme copy is `harness/fixes/GccPhatMask.mjs`.

**One deviation from Jay's script.** `dfn_shared.py` passes the 12 dB limit to `model.mask`. That clamps the mask
floor, but leaves the deep-filter band below 4.8 kHz unlimited. Its help text, and the stock `enhance()`, apply it as a
blend instead: lim x noisy + (1 - lim) x enhanced. This run uses the blend, on both channels. If the app uses the
mask clamp, tests 2, 3 and 6 are unaffected; tests 4 and 5 should be re-checked.

## Headline
1. **Level decides everything about DFN's gate.**
   - **STARSS23:** speech is recorded at -42 dBFS (median; -64 to -31). At that level `lsnr` crosses 0 dB on only 48%
     of speech onsets. Normalised to -26 dBFS, 91% are open within one second.
   - **Normalising raises `lsnr` during speech** by a median 3.3 dB on STARSS23 (-13 to +16) and 2.2 dB on LOCATA
     (-3 to +15). Jay's LOCATA observation (-5.4 to +3.3 dB) holds.
   - **The app needs a fixed input gain before DFN.**
2. **`lsnr` over 0 dB works as a speech gate, but less cleanly than on Jay's tapes.**
   - **Normalised, STARSS23:** it opens on 91% of speech onsets. It crosses within 50 ms of `attacks.py`'s MF onset on
     65% of them (median difference 0 ms).
   - **But it also opens:** in gaps, at 22 opens per minute of gap, with 2.5% of gap frames open. On 31% of non-speech
     onsets, led by laughter (72%), door/cupboard (46%) and knock (47%). Footsteps open it on 15%.
   - **Soft first words:** it misses more of them. Within 300 ms it opens on 62% of the softest quarter of onsets,
     against 91% of the loudest.
3. **The mask isn't a usable speech track at any threshold.**
   - **At 0.5:** it misses 74% of speech onsets.
   - **At 0.3:** it misses 35%, and still opens on 10% of non-speech onsets.
   - **At 0.2:** it opens on 23% of gap frames and on 48% of footsteps.
   - Jay's "missed the soft first word and opened on footsteps" reproduces, depending on the threshold. The mask's
     misses don't depend on how soft the onset is; `lsnr`'s do.
4. **The ghost hypothesis doesn't hold here.**
   - **No mixdown effect:** the mask from the L+R mixdown and the mask from one capsule give the same GccPhat
     results, within 2% in every class.
   - **No dip where L and R cancel:** the mixdown's mask is no lower than the capsule's in those bands (difference
     0.00). Such bands are only 3% (STARSS23) and 7% (LOCATA) of GccPhat's slices anyway.
   - **What mask-weighting does do:** it moves as many reads into 10 deg as out of it (661 in, 685 out on STARSS23).
     It adds about 10 aliasing-partner reads (86 -> 96) and removes about 80 of 601 0 deg pulls.
   - Jay's ghost was on the 5 ms read, which this brief doesn't test.
5. **The shared operator preserves the bearing.**
   - **LOCATA:** GccPhat reads the DFN pair within 1 deg of the raw pair on 91% of reads, and within 5 deg on 98%.
   - **STARSS23:** 63-71% within 1 deg, 90-93% within 5 deg.
   - **Where it moves, it helps more than it hurts:** on STARSS23 normalised, 565 reads move into 10 deg and 349 out.
6. **DFN's clues barely separate GccPhat's right reads from its wrong ones.** Normalised, the best are `lsnr`'s maximum
   over the first 200 ms (AUC 0.59 on STARSS23, 0.61 on LOCATA) and the mask's share of the band (0.58, 0.61). At the
   recorded level every clue is at chance.
7. **DFN fits the live budget easily.**
   - **Cost:** 0.08 s per second of audio for the mixdown pass with the shared operator, on one CPU thread.
   - **Look-ahead, measured:** 2 frames. A frame's mask and `lsnr` change only once input 20 ms past the frame's centre
     arrives, so DFN sees a sound 30-40 ms after it starts, against diart's 500 ms.

## 1. Level
Per recording and pair, the median of `lsnr` over labelled speech frames and over gap frames, in dB:

| data | speech level (dBFS) | gain to -26 (dB) | lsnr, speech: raw -> norm | lsnr, gaps: raw -> norm | lsnr moved, speech |
|---|---|---|---|---|---|
| STARSS23 | -41.9 (p10 -49.5, p90 -36.5) | +15.3 | -11.8 -> -6.9 | -13.2 -> -14.4 | +3.3 (p10 -1.3, p90 +10.7) |
| LOCATA | -43.7 (-46.4 to -41.9) | +17.7 | -0.3 -> +0.9 | -4.1 -> -7.2 | +2.2 (p10 -2.2, p90 +13.6) |

- **Normalising lifts `lsnr` in speech and lowers it in gaps:** the gap separation widens.
- **STARSS23's speech-frame medians stay low after normalising.** Its labels mark whole 100 ms frames, phrase pauses
  included, and other sources often sound under the talker.
- **`lsnr` can carry long memory.** At a quiet level, two passes that differed only in history more than 5 s back
  stayed up to 30 dB apart for 5 s (README). A live gate's first seconds after start-up shouldn't be trusted.

## 2. `lsnr` as a live speech gate
**Each speech onset:** where `lsnr` first goes over the threshold, from 0.3 s before to 1.0 s after. It counts as
"already open" when `lsnr` was over the threshold for the whole 100 ms before, and "missed" when it never crosses.
STARSS23's onsets come from labels at 100 ms; LOCATA's from the VAD. The onsets are counted once per pair: 5,968
STARSS23 speech onsets x 2 pairs, and 341 LOCATA onsets x 2.

| data, level, gate | opened | already open | missed | latency, median | within 50 ms of the MF onset | gap frames open | opens / min of gap | non-speech onsets opened |
|---|---|---|---|---|---|---|---|---|
| STARSS23 raw, lsnr > 0 | 46% | 2% | 52% | +50 ms | 52% | 7.6% | 69 | 27% |
| STARSS23 norm, lsnr > 0 | 90% | 2% | 9% | +60 ms | 65% | 2.5% | 22 | 31% |
| STARSS23 norm, lsnr > +5 | 67% | 0% | 33% | +130 ms | 54% | 1.2% | 13 | 21% |
| STARSS23 norm, lsnr > -5 | 91% | 6% | 3% | +40 ms | 61% | 6.1% | 43 | 40% |
| LOCATA raw, lsnr > 0 | 60% | 28% | 12% | -30 ms | 41% | 31% | 158 | |
| LOCATA norm, lsnr > 0 | 84% | 16% | 0% | -20 ms | 65% | 15% | 164 | |

- **The MF comparison:** on onsets where both fire within 0.3 s, the `lsnr` crossing and `attacks.py`'s MF open
  differ by a median 0 ms (STARSS23) and -10 ms (LOCATA). About two-thirds fall within 50 ms of each other.
  - Jay's "within 16 ms" holds for the middle of the distribution, not all of it.
  - The latency against the label is dominated by STARSS23's 100 ms label grid.
- **LOCATA's "gaps"** are only 1.7 minutes, mostly between words inside a talker's turn. The rate there says `lsnr`
  flickers across 0 between words. It isn't a fair test of opening in silence; STARSS23's 96 minutes are.
- **Non-speech onsets that open the gate, STARSS23 normalised.** Counted only where no speech is labelled from 0.5 s
  before to 0.5 s after:

  | class | onsets | opened |
  |---|---|---|
  | laughter | 224 | 72% |
  | knock | 36 | 47% |
  | door/cupboard | 146 | 46% |
  | music | 60 | 30% |
  | domestic sounds | 82 | 26% |
  | water tap | 32 | 25% |
  | clapping | 60 | 18% |
  | musical instrument | 242 | 15% |
  | footsteps | 184 | 15% |
  | telephone | 70 | 9% |
  | bell | 96 | 3% |

  Laughter is voice, so opening on it is arguably right. Impulsive sounds (knock, door) open it about half the time.
- **For Stage 1's bubble-or-ring switch:** `lsnr` alone would draw a bubble for about one door or knock in two. It needs
  a second test.

## 3. The mask as a speech track
The mask here is the mixdown's mean over 300 Hz-8 kHz. Nothing sets its threshold, so four were tried:

| STARSS23 norm, mask over | missed speech onsets | gap frames open | opens / min of gap | non-speech opened | footsteps opened |
|---|---|---|---|---|---|
| 0.2 | 7% (19% already open) | 23.5% | 175 | 53% | 48% |
| 0.3 | 35% | 5.5% | 11 | 10% | 8% |
| 0.4 | 54% | 1.6% | 6 | 3% | 4% |
| 0.5 | 74% | 0.0% | 0.4 | 0.2% | 0% |

- **No threshold gives both few misses and few false opens.** `lsnr` > 0 dominates every row: 9% missed at 2.5% of gap
  frames.
- **Soft first words** (STARSS23 pair 1-2, % of onsets open within 300 ms, by voice-over-pause quartile in 300-1100 Hz,
  softest first):

  | gate | Q1 | Q2 | Q3 | Q4 |
  |---|---|---|---|---|
  | lsnr > 0, norm | 62 | 72 | 82 | 91 |
  | mask > 0.3, norm | 41 | 37 | 43 | 50 |

  The mask misses at about the same rate whatever the onset's level. `lsnr` misses soft onsets more. So "the mask
  missed the soft first word" is the mask missing first words in general.

## 4. Why mask-weighting helped the ghost: the hypothesis tested
**The hypothesis.** The L+R mixdown cancels bands where the channels are out of phase, so a mask from it under-weights
them. What's left over-represents the bands where the true delay and its aliasing partners line up.

**The setup.**
- **Variants:** GccPhat's votes weighted per frequency slice by the mask averaged over its half-second lock window,
  from (a) the mixdown, (b) capsule L alone, (c) no mask. The mask multiplies the pause weights.
- **First, the mechanism directly.** For each read, each GccPhat slice's in-phase ratio |L+R|^2 / 2(|L|^2+|R|^2), over
  the same window. Do the masks dip where L and R cancel (ratio < 0.25)?

| data (norm) | slices that cancel | mixdown mask: cancel / add bands | capsule mask: cancel / add | mixdown - capsule, in cancel bands |
|---|---|---|---|---|
| STARSS23 | 3% | 0.25 / 0.25 | 0.25 / 0.25 | 0.00 |
| LOCATA | 7% | 0.36 / 0.29 | 0.38 / 0.30 | -0.01 |

**The first half of the hypothesis fails, for three reasons:**
- **Few bands cancel.** Over half a second of real speech, few slices cancel at all.
- **No dip.** Where they do, the mixdown's mask is no lower than a single capsule's.
- **The ERB mask can't follow the comb.** Both masks are slightly higher in LOCATA's cancelling bands than in its
  adding ones. The 32 ERB bands above about 2 kHz are as wide as the spacing of the comb a 160 mm delay cuts into the
  mixdown (nulls 2.1 kHz apart or more), so one band can't follow a single null.

**Then the classes.** Batch A's classes of GccPhat's reads off by more than 10 deg, all of STARSS23's 14,982 reads:

| variant | > 10 deg | aliasing partner | 0 deg pull | other | moved in / out of 10 deg, against (c) | kept / mean / median, Jay's rule |
|---|---|---|---|---|---|---|
| (c) no mask | 48.4% | 86 | 601 | 1,639 | | 80.5% / 9.6 / 6.4 |
| (a) mixdown mask, raw level | 48.6% | 96 | 522 | 1,841 | 661 / 685 | 80.8% / 9.8 / 6.8 |
| (b) capsule mask, raw level | 48.6% | 95 | 518 | 1,846 | 667 / 692 | 81.0% / 9.8 / 6.8 |
| (a) mixdown mask, norm | 48.4% | 93 | 509 | 1,864 | 685 / 671 | 80.8% / 9.7 / 6.6 |
| (b) capsule mask, norm | 48.4% | 96 | 501 | 1,849 | 668 / 661 | 80.9% / 9.7 / 6.6 |

LOCATA (682 reads): 27.0% wrong with no mask, 27.0-28.6% with either mask, no aliasing partners in any variant, and
moves of 9-16 in against 14-20 out.

**What the classes show:**
- **(a) and (b) are the same,** within 2% in every class and at both levels. Whatever mask-weighting does, the mixdown isn't
  the cause.
- **Mask-weighting itself is a wash for GccPhat's half-second sum:**
  - aliasing partners +8 to +12%;
  - 0 deg pulls -13 to -17%;
  - "other" +12 to +14%;
  - moves in and out in balance.
- **Jay's finding was on the 5 ms read** (FiveMsAmplitude's window), where one short window has few frequency votes and
  a mask could tip it. That read isn't GccPhat's lock and isn't tested here.

## 5. The shared operator on real cuts
GccPhat (shipped, unchanged) on the DFN pair against the raw pair, read by read:

| data, level | reads | same within 1 deg | within 5 deg | moved > 10 deg | moved into / out of 10 deg of the truth |
|---|---|---|---|---|---|
| LOCATA raw | 682 | 92% | 98% | 1.5% | 8 / 6 |
| LOCATA norm | 682 | 91% | 98% | 1.8% | 7 / 7 |
| STARSS23 raw | 14,982 | 71% | 93% | 4.3% | 388 / 306 |
| STARSS23 norm | 14,980 | 63% | 90% | 6.2% | 565 / 349 |

**The bearing is preserved for a single talker in a quiet room** (LOCATA), as the math says. STARSS23 moves more, for
three reasons:
- **Overlap:** its cuts often hold other sources that DFN suppresses.
- **The sphere:** its capsules sit on a rigid sphere.
- **Movement:** talkers move within the half second, which the shared deep filter smears below 4.8 kHz.

The moves there favour the truth. On the DFN pair, GccPhat's "pause direction" class drops from 3,003 to 2,860 wrong
reads, and "truth was angle 2 or 3" from 1,341 to 1,237.

## 6. Clues for brief 11
The AUC is the chance that a wrong GccPhat read (> 10 deg, speech onsets) has a lower clue than a right one; 0.5 is no
signal.

| clue | STARSS23 raw | STARSS23 norm | LOCATA raw | LOCATA norm |
|---|---|---|---|---|
| lsnr at the onset frame | 0.49 | 0.51 | 0.48 | 0.55 |
| lsnr, max over the first 200 ms | 0.50 | **0.59** | 0.52 | **0.61** |
| mask's share of GccPhat's band (lock window) | 0.51 | 0.58 | 0.50 | 0.61 |
| the same from the capsule pass | 0.53 | 0.59 | 0.56 | 0.61 |

**Useful only after normalising, and weak even then.**
- **Normalised:** `lsnr`'s 200 ms maximum is 4.1 dB on right reads against 1.6 dB on wrong ones (STARSS23).
- **Against the lab's pause-read clue:** these are well below it (brief 13: 83% of GccPhat's wrong reads caught at a
  10% cost, in the lab).
- **For brief 11:** worth adding as a second clue, not as the rule.
- **The onset frame itself carries nothing:** `lsnr` at the labelled onset is still near its floor, since DFN takes
  tens of ms to rise.

## 7. Cost and latency
- **Cost** (108,874 s of audio, one CPU thread, torch 2.0.1, on whole recordings):

  | pass | DFN seconds per second of audio |
  |---|---|
  | mixdown pass + the shared operator on L and R + ISTFT | 0.080 |
  | single-capsule pass (mask and lsnr only) | 0.068 |

  A 10 ms frame costs under 1 ms. The live budget holds with room for the rest of the pipeline on a desktop core. A
  phone CPU is slower, but within the same order.
- **Latency, measured** by changing the input from one sample on and finding the first output frame that changes:
  - A frame's mask and `lsnr` depend on input up to 20 ms past the frame's centre (2 frames of look-ahead), plus its
    own 10 ms half-window.
  - So a sound is visible to the gate 30-40 ms after it starts. Diart's is 500 ms.
- **DFN's real lag on onsets:** the measured crossing sits a median 0 ms from the MF onset on STARSS23. So the
  look-ahead costs nothing against `attacks.py`, which already confirms onsets up to 100 ms late.

## Caveats
- **The attenuation limit:** applied as a blend, not as `dfn_shared.py`'s mask clamp (see "One deviation").
- **Speech level** is the rms over labelled speech frames, not ITU-T P.56's active speech level. STARSS23's labels
  include pauses and overlapping sources, so its -26 dBFS target lands a few dB low on active speech.
- **STARSS23's onsets are labelled at 100 ms resolution.** Latency against them is good to about +-50 ms.
  `attacks.py`'s MF onset is the sharper comparison.
- **LOCATA's gaps are short** (1.7 minutes, mostly between words), so its false-open rate isn't comparable with
  STARSS23's.
- **The mask-weighted GccPhat** weights each slice by the mask averaged over its half-second window. A time-frequency
  weighting, frame by frame before the sum, is the other reading of "weight the votes by the mask". It isn't tested.
- **Test 4's single-capsule mask** comes from capsule L only.

## Files
- **`results/stage2_dfn/`:**
  - `report.md`: this report;
  - `tables.md`: every table, including the gate at every threshold and level, and non-speech onsets by class;
  - `summary.json`: every number;
  - `reads.jsonl.gz`: per batch A read, each GccPhat variant's read, error and classes, and the DFN clues (with the
    in-phase mechanism numbers at the norm level).
- **`harness/stage2_dfn/`:** the run (README there).
- **`harness/fixes/GccPhatMask.mjs`:** the mask-weighted GccPhat copy, never shipped.
