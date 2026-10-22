# Angle2's inward pull: reproduced, explained, fixed for most onsets (2026-10-22)

Brief 2 of `cloud_sessions.md`. On STARSS23, `Angle2.readUtterance` read 2-19 deg nearer 0 than GccPhat on the same
cuts, growing with angle (`results/starss23/report.md`, section 2).

## What was run
- **Rooms:** pyroomacoustics 0.10.1, image-source model at 48 kHz. The pair's axis is horizontal, 157 mm (the phone) or
  69 mm (a STARSS pair), on a bare pair with no mount. The talker is at 1.5 m and at the pair's height, -60 to +60 deg
  in 10 deg steps. Room configs:
  - free field;
  - partial rooms (6 x 5 x 3 m; the pair 1.5 m off the floor and 1.5 m from the back wall): direct plus the floor, one
    wall, floor + wall, floor + ceiling, or all six walls at order 1;
  - full shoeboxes: small 3.5 x 3 x 2.5 m, mid 6 x 5 x 3 m, big 10 x 8 x 3.5 m, each at RT60 0.2, 0.4 and 0.7 s.
- **What real rooms add besides reflections:**
  - `+n` diffuse noise (spherically isotropic coherence, 1/f) at 30, 20 or 10 dB under the speech;
  - `+ctx` the clip's own preceding words in place of silence;
  - `+jit` the onset handed over 0-100 ms early, as a STARSS 100 ms label frame would place it.
- **Speech:** 21 word onsets from 5 clean clips (LibriSpeech and CMU Arctic, from GitHub), 273 cuts per set.
- **Totals:** 47 configs at 2 spacings, so 94 sets and 25,662 cuts.
- **Schemes:** both ran unchanged through `harness/starss23/run_schemes.mjs`. The harness is `harness/rooms/`.
- **Lean:** the signed error along the truth's side, median; negative means read nearer 0. Where one number is given,
  it is the median over |truth| 30-60 deg.
- **STARSS23 check (step 3):** run after Zenodo access was opened. All 6 capsule pairs, 8,532 reads, before and after
  the fix on the same cuts. Results in section 4.

## 1. Reflections alone don't pull it in
With every onset coming out of silence, Angle2's onset is within about 2 deg of the truth in every room and at both
spacings. That covers the floor alone, one wall, all six walls at order 1, and every shoebox up to RT60 0.7 s. Its
precedence rule works: the first 3 ms windows hold the direct sound alone.

**The pull needs a room plus anything that delays the count:** noise, the previous phrase's tail, or a late onset label.

**Smallest room that pulls it in:**
- **Floor + ceiling at 10 dB SNR, 157 mm.** -3.6 deg at 30 and -8.9 at 60.
- **The small shoebox at RT60 0.2 s and 20 dB SNR.** -2.9 at 30, -4.2 at 50.
- **For comparison, the floor alone at 10 dB SNR.** -0.7, i.e. no pull.

It grows with fewer metres and less SNR. The worst cases are the small room at RT60 0.4 s with 10-20 dB SNR, or with
noise, tail and jitter together.

Angle2 onset lean, before the fix, by |truth| (157 mm):

| set | 10 | 20 | 30 | 40 | 50 | 60 |
|---|---|---|---|---|---|---|
| free + 20 dB noise | -0.4 | -0.2 | -0.7 | -1.9 | +0.1 | -1.2 |
| small room, RT60 0.4, no noise | (all within 1.5 deg) | | | | | |
| floor + ceiling, 10 dB | -0.4 | -1.5 | -3.6 | -1.5 | -3.8 | -8.9 |
| mid room, RT60 0.4, 20 dB + tail + jitter | -2.3 | -3.2 | -4.3 | -3.1 | -7.8 | -5.8 |
| small room, RT60 0.4, 20 dB | -1.4 | -7.8 | -6.8 | -3.9 | -28.5 | -19.8 |
| small room, RT60 0.4, 10 dB | -1.7 | -7.2 | -16.2 | -21.9 | -26.4 | -29.3 |
| small room, RT60 0.4, 20 dB + tail + jitter | -5.5 | -14.6 | -12.5 | -11.8 | -28.5 | -38.8 |

This has STARSS's shape: inward, and growing with angle. GccPhat in the same sets doesn't lean in from 30 deg out
(-4.3 to +5.3). Its 10-20 deg lean (next section) is a separate effect.

## 2. The mechanism: when the count starts, not U_AGREE or U_HITS
**The candidates, ablated.** Each cell is the onset's lean / median |error| in deg. Every change ran on the same cuts:

| set | mm | as is | U_AGREE 1 | U_AGREE 6 | U_HITS 5 | U_WIN 1.5 ms |
|---|---|---|---|---|---|---|
| small RT0.4, 20 dB | 157 | -7.5 / 6.5 | -9.6 / 7.1 | -9.9 / 7.1 | -10.2 / 6.5 | -28.5 / 10.6 |
| small RT0.4, 20 dB | 69 | -4.3 / 8.5 | -5.0 / 7.0 | -2.7 / 9.4 | -4.9 / 8.9 | -8.4 / 10.3 |
| small RT0.4, 20 dB + tail + jitter | 157 | -21.9 / 13.6 | -25.5 / 14.5 | -22.2 / 15.0 | -22.4 / 12.5 | -30.2 / 14.9 |
| mid RT0.4, 20 dB + tail + jitter | 157 | -4.3 / 4.3 | -3.1 / 3.8 | -4.3 / 4.4 | -3.6 / 3.9 | -22.0 / 8.5 |
| mid RT0.4, 20 dB + tail + jitter | 69 | -5.0 / 6.5 | -4.7 / 6.1 | -6.3 / 7.1 | -6.3 / 6.5 | -7.9 / 8.0 |

- **U_AGREE, scaled either way:** doesn't remove the pull. The brief's lead suspect is out.
- **U_HITS, more recurrences:** no gain.
- **A shorter window:** worse everywhere.

All of it is in `results/angle2_pull/ablation.json`.

**What it is: the gate opens late.** A window counts only once it is 10 dB over the quietest millisecond of the pause.

| set (157 mm, \|truth\| >= 30) | gate opens within 3 ms of the onset | lean | gate opens later | lean |
|---|---|---|---|---|
| small RT0.4, no noise | 63% of cuts | -0.7 | 37% | -14.4 |
| small RT0.4, 20 dB | 15% | +0.0 | 85% | -13.5 |
| mid RT0.4, 20 dB | 17% | +0.0 | 83% | -3.1 |
| free, 20 dB | 32% | +0.0 | 68% | -1.5 |

When the voice rises out of the pause softly, the first window that clears the gate is 25-50 ms into the word. In noise,
or after an earlier phrase, that is most cuts. By then every 3 ms window holds the direct sound and the room together.

Single windows there read far nearer 0. In the small room at 20 dB with tail and jitter, |truth| >= 30, the windows'
median lean is -40 deg and only 9% are within 5 deg of the truth.

The first family to recur 3 times is then a reflection's or a blend. In a clean room the gate opens in the direct-only
first milliseconds, which is why the clean rooms don't pull.

**Why nearer 0 and not anywhere.** The floor, ceiling, front and back walls each mirror the talker without changing its
offset along the mic axis, but they lengthen the path, so the image's lateral angle is smaller. For a 50 deg talker in
the small room, those four first-order images sit at about 20 deg (floor), 27 (ceiling), 24 (back wall) and 18 (front
wall). Only the two
side walls can read wider. So blended reads land between the talker and 0, more so the wider the talker is. That is
the growth with angle.

**One traced cut.** Small room, 20 dB, truth +50, `box_small_rt0.4+n20_u00`. Each entry is ms after the true onset /
deg; the first counted window is 36 ms in:

    36/-67.3 37/11.5 38/17.5 41/-8.3 42/-0.6 43/16.8 44/39.3 45/-90 46/48.1 47/-7.7 48/47.2 49/40.1 ...

The 11.5 family (11.5, 17.5, 16.8) recurs 3 times at 43 ms and is published as the onset. The talker's 48-53 reads come
later and lose.

## 3. The fix (Angle2 only)
**Two tests pick the windows that still hold the direct sound alone:**
- **It is rising:** `U_RISE_DB` = 3 dB over the window `U_RISE_MS` = 3 ms before. That means new sound, and new sound
  reaches the mics direct first.
- **It is clean:** its peak holds `U_CLEAN` = 0.6 of the band's PHAT votes, i.e. one wave rather than a blend.

**The rule:**
- **The onset:** the first direction to recur `U_EDGE_HITS` = 2 times among those windows, published with `edge: true`.
- **No such direction within the scan:** the first to recur 3 times among all counted windows, exactly as before, with
  `edge: false`.
- **The first reflection:** unchanged.

`readUtterance` also takes an optional `trace` array (every counted window's read) for checking.

**Why both tests:** the rising test alone helps but moves too many onsets the wrong way. On its own at 6 dB, 3 hits, 518
onsets moved to within 10 deg and 241 out of it. With the clean test added at 3 dB, 2 hits, the counts are 850 in and
182 out on that offline grid (`analysis/policies.py`, 32 sets, `results/angle2_pull/policies.json`). That was the
grid's largest net gain.

Rising windows only, with no fallback, are the most accurate, but leave half the noisy-room cuts with no onset
(`rise_only.json`).

### Before / after, all 94 sets
Each cell is the mean over the sets of each set's median:

| sets | mm | lean | median err | within 10 deg | onset on an edge | edge onsets: lean, within 10 | the rest: lean, within 10 | onsets moved in / out of 10 deg |
|---|---|---|---|---|---|---|---|---|
| free field (1) | 157 | -0.7 -> -0.7 | 0.9 -> 0.7 | 99% -> 100% | 100% | -0.7, 100% | | 3 / 0 |
| free field (1) | 69 | +0.0 -> +0.0 | 1.9 -> 1.1 | 86% -> 99% | 100% | +0.0, 99% | | 34 / 0 |
| free + noise/tail/jitter (6) | 157 | -0.7 -> -0.5 | 1.8 -> 1.0 | 95% -> 98% | 94% | -0.5, 99% | -2.3, 88% | 52 / 8 |
| free + noise/tail/jitter (6) | 69 | -0.6 -> -0.7 | 3.8 -> 2.3 | 80% -> 92% | 95% | -0.6, 93% | +7.5, 49% | 229 / 44 |
| rooms, clean (16) | 157 | -0.8 -> -0.7 | 1.2 -> 0.8 | 94% -> 98% | 98% | -0.7, 99% | -6.4, 46% | 191 / 12 |
| rooms, clean (16) | 69 | -0.4 -> -0.4 | 2.5 -> 1.5 | 82% -> 96% | 99% | -0.4, 96% | -4.3, 67% | 648 / 60 |
| rooms + noise/tail/jitter (24) | 157 | -3.7 -> -2.7 | 4.1 -> 3.1 | 78% -> 83% | 67% | -0.6, 94% | -6.1, 66% | 439 / 148 |
| rooms + noise/tail/jitter (24) | 69 | -3.3 -> -2.8 | 6.5 -> 4.5 | 66% -> 77% | 78% | -1.7, 84% | -6.4, 49% | 980 / 285 |

- **Over all sets:** 2,576 onsets moved to within 10 deg of the truth and 557 out of it.
- **The fallback:** onsets that took it are identical to before on every cut. Cuts with no onset are unchanged.
- **Edge onsets:** where an edge onset exists (67-78% of cuts in the noisy rooms), the pull is gone: -0.6 deg at
  157 mm and -1.7 at 69 mm, 94% and 84% within 10 deg.
- **The rest:** where none exists, the old read stands, and the pull is still there (-6 deg).

**By angle, before -> after (GccPhat for reference), 157 mm:**

| set | | 10 | 20 | 30 | 40 | 50 | 60 |
|---|---|---|---|---|---|---|---|
| floor + ceiling, 10 dB | before | -0.4 | -1.5 | -3.6 | -1.5 | -3.8 | -8.9 |
| | after | -1.7 | -2.2 | -0.0 | -0.7 | -3.8 | -3.6 |
| | GccPhat | -1.9 | -2.0 | +0.0 | -0.1 | +0.1 | +0.1 |
| small RT0.2, 20 dB | before | -1.1 | -2.5 | -2.9 | -3.1 | -4.2 | -3.5 |
| | after | -0.7 | -1.9 | -1.1 | -0.7 | -2.8 | -1.2 |
| | GccPhat | -4.3 | -13.5 | +0.0 | +1.8 | +0.8 | +3.1 |
| mid RT0.4, 20 dB + tail + jitter | before | -2.3 | -3.2 | -4.3 | -3.1 | -7.8 | -5.8 |
| | after | -1.1 | -2.5 | -2.2 | -3.1 | -6.9 | -2.4 |
| | GccPhat | -3.3 | -12.6 | +0.0 | -0.7 | -1.4 | +1.0 |
| small RT0.4, 20 dB + tail + jitter | before | -5.5 | -14.6 | -12.5 | -11.8 | -28.5 | -38.8 |
| | after | -5.5 | -12.3 | -2.2 | -11.8 | -25.0 | -38.8 |
| | GccPhat | -5.7 | -14.3 | +0.0 | +3.1 | +0.8 | +4.2 |
| small RT0.4, 10 dB | before | -1.7 | -7.2 | -16.2 | -21.9 | -26.4 | -29.3 |
| | after | -1.7 | -7.5 | -16.2 | -21.2 | -24.7 | -29.3 |
| | GccPhat | -5.7 | -12.3 | -4.3 | +3.1 | +0.4 | +1.5 |

**Not fixed:**
- **The hardest rooms.** These are the small room at 10-20 dB SNR, and the small room with noise, tail and jitter. Only
  13-52% of their cuts have a clean rising edge (13-34% at 157 mm). So at 50-60 deg at 157 mm the median is still the
  old read, -14 to -39 deg.
- **What it means for the read.** On such a cut no single 3 ms window holds the talker alone, and Angle2 doesn't average,
  so there is nothing to recover the direct from. `edge: false` marks those reads, so Render can dim them, the way Jay
  asked for undecided reads ("render both as dimmed speech bubbles").
- **GccPhat, which sums half a second, holds up there** (within 6 deg from 30 deg out). At 10-20 deg it leans in by 4-15
  deg at 157 mm in these rooms. That's its own effect, likely the 300 Hz band's in-phase reverberation (see
  GccPhat.mjs), and STARSS's 69 mm pairs can't show it. Not chased here.

## Caveats
- **Tuned on simulation.** The four constants come from a coarse grid (3 rise levels x 3 share levels x 2 hit counts) on
  these rooms. The tests are generic, rising energy and single-wave dominance. STARSS (section 4) is the out-of-sample
  check, and it holds there.
- **A bare pair:** no phone body, no STARSS sphere.
- **Speech:** 21 onsets from 5 clips, 16 kHz originals upsampled, so nothing above 8 kHz. That is the schemes' band top
  anyway.
- **Geometry:** one talker distance (1.5 m), at the pair's height. A seated or standing talker changes the floor and
  ceiling images' angles.
- **Noise:** ideal diffuse noise. Real pauses also hold other sources and the room's own noise directions.

## 4. STARSS23: the fix on real rooms
**Run:** all 6 capsule pairs re-cut from https://zenodo.org/records/7880637 with `harness/starss23/starss_cut.py`. That
gives 1,422 onsets per pair and 8,532 reads, the same cuts as `results/starss23/report.md`. Both schemes ran through
`run_schemes.mjs`, and `harness/starss23/analysis/compare_fix.py` compared them against that report's predictions.

**Checks:**
- **GccPhat is identical on every read.** Its code didn't change.
- **The before numbers reproduce the report's:** Angle2 nearer 0 than GccPhat by 1.7 / 4.3 / 7.6 / 19.2 deg.
- **Fallback reads are identical to before.** 72% of reads got an edge onset. The other 28% took the old count unchanged.

**Angle2's onset, before -> after, by |truth|.** GccPhat is shown for reference. "vs GccPhat" is Angle2 minus GccPhat on
the same cut, along the truth's side; negative means Angle2 reads nearer 0.

| \|truth\| | reads | vs GccPhat | median err | within 10 deg | on an edge | edge: err, within 10 | rest: err | GccPhat err |
|---|---|---|---|---|---|---|---|---|
| 0-15 | 1998 | -0.2 -> +0.2 | 10.9 -> 7.2 | 47% -> 61% | 74% | 5.7, 70% | 15.4 | 5.1 |
| 15-30 | 1921 | -1.7 -> -0.7 | 11.2 -> 8.0 | 46% -> 57% | 79% | 6.7, 64% | 16.7 | 6.4 |
| 30-45 | 1974 | -4.3 -> -1.5 | 14.9 -> 11.3 | 37% -> 45% | 73% | 9.8, 51% | 18.2 | 8.9 |
| 45-60 | 1666 | -7.6 -> -2.5 | 20.8 -> 15.2 | 28% -> 36% | 71% | 13.0, 41% | 28.2 | 17.3 |
| 60-90 | 861 | -19.2 -> -7.1 | 27.5 -> 22.5 | 13% -> 19% | 47% | 15.8, 28% | 30.2 | 15.6 |
| all | 8420 | -2.8 -> -1.0 | 15.0 -> 10.8 | 37% -> 47% | 72% | 8.6, 55% | 20.2 | 9.2 |

**What it shows:**
- **The pull shrinks by about two-thirds in every band from 15 deg out.** 1,417 onsets moved to within 10 deg of the
  truth, and 571 moved out of it.
- **Edge onsets read about as well as GccPhat.** The median error is 8.6 deg against 9.2, and within 1 deg of it in every
  band. At 45-60 they read better (13.0 against 17.3). That's one 3 ms recurrence against half a second summed.
- **The rest keep the old read and are poor:** 20.2 deg median error. Those are the reads to dim.

Angle2's absolute lean now goes outward (+4.0 at 30-45, +5.7 at 45-60), like GccPhat's (+5.6, +11.3). Before, the room's
inward pull and the sphere's outward lean cancelled. With the pull mostly gone, the STARSS sphere's lean shows through,
as section 2 of the STARSS report predicted.

**Every room improves.** Angle2's median error per room, |truth| < 40, before -> after (GccPhat):

| room | 2 | 4 | 6 | 7 | 8 | 9 | 10 | 12 | 13 | 14 | 15 | 16 | 21 | 22 | 23 | 24 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| before | 18.5 | 16.3 | 11.4 | 9.1 | 13.0 | 14.2 | 9.2 | 10.1 | 10.0 | 10.4 | 5.6 | 8.9 | 16.1 | 14.5 | 15.7 | 14.8 |
| after | 15.5 | 10.3 | 7.0 | 7.1 | 9.4 | 11.6 | 6.7 | 6.9 | 5.4 | 7.2 | 4.4 | 6.5 | 12.3 | 12.5 | 12.5 | 9.6 |
| GccPhat | 15.5 | 8.8 | 6.9 | 4.7 | 6.3 | 10.2 | 6.0 | 5.0 | 3.9 | 4.2 | 3.7 | 4.4 | 10.0 | 11.0 | 8.9 | 5.6 |

**For the phone:**
- **GccPhat is still the better angle 1 overall.** It reads 9.2 deg against 10.8 here.
- **Angle2 now has a trustworthy subset.** Its `edge: true` onsets, nearly 3 in 4, are as good as GccPhat. Its
  `edge: false` onsets are not, and Render should dim them.
- **Where the two schemes agree,** the earlier report found that GccPhat's error drops (6.6 deg). With edge onsets that
  cross-check should get stronger. It isn't re-measured here.

## Files
- **`src/schemes/Angle2.mjs`:** `readUtterance` with the clean-rising-edge onset, the `edge` flag and `trace`.
  `readSound` and `createStream` are untouched.
- **`harness/rooms/`:** the room generator, runners, scorers, and the offline rule search. `README.md` there gives the
  steps. No audio is committed. The speech clips come from GitHub; the cuts are re-made in about 10 minutes.
- **`results/angle2_pull/`:**
  - `before_after.json`: every set, before and after, and by angle;
  - `summary.json`: the table above;
  - `gccphat_by_angle.json`;
  - `ablation.json`: `U_AGREE`, `U_HITS`, `U_WIN`;
  - `rise_only.json`: rising windows only, no fallback;
  - `policies.json`: the offline grid.
- **`results/starss23/after_angle2_fix/`:**
  - `preds_<pair>.jsonl`: both schemes after the fix, with Angle2's `a2_edge`;
  - `compare.json`: every number in section 4.

  The cuts are 546 MB per pair and not committed. Re-make them with `starss_cut.py`.
