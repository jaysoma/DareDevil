# The colour of rotation on LOCATA, with tracked facing (brief D, 2026-10-24)

**The pattern holds outside Jay's house. On LOCATA the contrast (CDR 4-8 kHz minus CDR 0.1-1.1 kHz) reads +0.3 dB
facing and −2.6 dB turned, against Jay's +0.0 and −2.3, and Jay's own −1 dB threshold, unchanged, calls toward
against turned at 81% (75% at home).** What the 45° view adds is that the U has a step, not a ramp: 45° reads like
facing (+0.0 dB against −0.4 at 0°), the drop comes between 45° and 90° and is complete by 90°, and 90, 135 and 180
read alike. So "toward" covers about ±60°, and nothing on this cue separates 120° from 90°.

The limit, before the numbers: LOCATA holds little speech that is one talker alone. 46 stretches pass the rules,
1.9 s of speech each (Jay's stops pool 7.2 s), and 18 of them come from one recording (eval task 4, recording 2).
Every number below carries its n, and several bins are thin (180°: 2 stretches).

- Scripts: `harness/rotation/locata/locata_bins.py` (the band powers, run on Jay's box) and `locata_rotation.py`
  (steps 1-5).
- Output: `numbers.json` (every stretch, with its bands) and `run.txt`, beside this file. Band powers per 0.1 s bin:
  `bins/<recording>.json`.
- Audio: Dictate's LOCATA tapes (`Dictate/geonar/locata_tapes.py`: DICIT mics 5 and 10, 160 mm, not normalised).
  Tracks: `results/animation/locata/`.
- Estimator: brief A's `octave_windows.py` (direction-free CDR, NFFT 2048, hop 512, smoothing 0.92), unfloored, summed
  in 0.1 s bins on the track grid. At 160 mm, c/2d is 1.07 kHz, so every band below 1.1 kHz is ill-conditioned (marked
  *), the contrast's low band included, as on the phone.

## 1. Stretches
- **A bin is usable** when the talker's voice activity covers at least half of it and the other talker's covers none
  of it, nor 0.3 s either side. The guard is there because the PSD smoothing remembers about 0.13 s, and 0.3 s leaves
  under 10% of the other talker's power.
- **A stretch** grows from a usable bin while every tracked bin in its span, pauses included, keeps the facing within
  20° of the span's mean and the head within 0.3 m of its mean position. It is kept if it has at least 1.5 s of usable
  speech, and it pools only those bins.

| recording | 0 | 45 | 90 | 135 | 180 |
|---|---|---|---|---|---|
| dev task 3, rec 1 | 0 | 1 | 2 | 0 | 0 |
| dev task 3, rec 2 | 1 | 1 | 1 | 1 | 1 |
| dev task 3, rec 3 | 2 | 2 | 0 | 0 | 0 |
| dev task 4, rec 2 | 0 | 1 | 0 | 1 | 0 |
| dev task 4, rec 3 | 1 | 0 | 0 | 0 | 0 |
| eval task 3, rec 1 | 1 | 1 | 0 | 1 | 1 |
| eval task 3, rec 2 | 2 | 0 | 0 | 0 | 0 |
| eval task 3, rec 3 | 0 | 1 | 0 | 0 | 0 |
| eval task 3, rec 4 | 1 | 1 | 0 | 0 | 0 |
| eval task 3, rec 5 | 2 | 0 | 0 | 0 | 0 |
| eval task 4, rec 1 | 0 | 0 | 0 | 1 | 0 |
| eval task 4, rec 2 | 3 | 8 | 3 | 4 | 0 |
| eval task 4, rec 3 | 0 | 1 | 0 | 0 | 0 |
| **all** | **13** | **17** | **6** | **8** | **2** |

- **Task 4's talkers overlap.** Each talker speaks 35-51 s per recording, but only 8-16 s of it alone. With the
  guard, that falls to 3-7 s, in bursts under 1.5 s. Dev task 4 recording 1 and eval task 4 recordings 4 and 5 give
  no stretch at all. Eval task 4 recording 2 is the exception: its talkers take turns, so it gives 18 stretches.
- **Moving isn't the limit.** Dropping the 0.3 m head rule adds only 3 stretches. Dropping the guard adds 19 (65 in
  all), and the sensitivity run below shows the same picture.
- **Outliers:** none set aside. The contrast runs from −5.9 to +4.8 dB, with nothing detached from the rest. One
  eval task 3 recording 4 stretch (4.7-6.5 s) is 6 dB brighter at 4-8 kHz than the same talker's other stretch, but
  its contrast (+4.8) sits inside the facing spread.

## 2. The U at 45° steps
Each stretch is taken against the same recording and talker's facing stretches (within 30°) at a distance within
0.5 m. Only 18 stretches have such a reference, so the table also gives the reference at any distance (35 stretches).
Distances barely differ between bins anyway: the bin means are 1.8-2.0 m, with sd 0.3-0.6 m.

**The contrast, mean (sd, n), dB against the facing reference:**

| facing | within 0.5 m | any distance | raw, no reference (all stretches) |
|---|---|---|---|
| 0 | −1.7 (3.6, 4) | −0.7 (n 9) | −0.4 (2.1, 13) |
| 45 | +0.6 (3.0, 7) | +0.3 (n 13) | +0.0 (2.2, 17) |
| 90 | −3.6 (n 1) | −2.5 (n 4) | −3.3 (1.5, 6) |
| 135 | −2.8 (2.0, 4) | −2.4 (n 7) | −2.8 (1.8, 8) |
| 180 | −0.9 (1.2, 2) | −0.9 (n 2) | −2.4 (1.3, 2) |

- **At 90° and past, every stretch with a reference reads lower:** 7 of 7 within 0.5 m and 13 of 13 at any distance.
  In Jay's walks it was 26 of 27 turned stops.
- **The drop is done by 90°, as in Jay's walks.** At 90° the raw contrast is already −3.3 dB, and 135° (−2.8) and
  180° (−2.4) read no lower. The bottom is flat.
- **45° is still facing.** The raw contrast at 45° (+0.0) matches 0° (−0.4). The 4-8 kHz CDR does dip a little: raw
  +4.1, +3.5, −0.2, −1.3 and −0.8 dB at 0, 45, 90, 135 and 180°, so 45° carries about a seventh of the full drop.
- **The 0° row isn't 0** because each facing stretch is taken against the other one to three facing stretches, and
  one stretch's contrast scatters 2.5 dB within a session (sd). That noise sets every limit below.

**Per octave, against the reference at any distance: direct / diffuse / total / CDR, dB** (n 13, 4, 7 and 2 at 45,
90, 135 and 180°):

| band | 45 | 90 | 135 | 180 |
|---|---|---|---|---|
| 125 * | −3.4 / −1.0 / −2.5 / −2.4 | −4.1 / −3.1 / −4.3 / −1.0 | −2.5 / −1.5 / −2.5 / −1.0 | +2.5 / −0.4 / +0.7 / +2.9 |
| 250 * | −1.8 / +0.4 / −1.1 / −2.1 | −3.9 / −0.1 / −2.8 / −3.7 | −5.2 / −2.9 / −4.4 / −2.3 | −5.5 / −1.2 / −4.3 / −4.2 |
| 500 * | −1.0 / +0.2 / −0.7 / −1.2 | −6.3 / −3.2 / −5.3 / −3.1 | −6.0 / −1.4 / −4.3 / −4.6 | −3.1 / −0.4 / −2.1 / −2.7 |
| 1k * | −0.8 / −0.8 / −0.8 / −0.1 | −2.8 / −0.3 / −2.0 / −2.6 | −2.9 / −0.1 / −1.7 / −2.8 | −5.9 / −4.2 / −5.1 / −1.8 |
| 2k | −3.4 / −2.0 / −3.0 / −1.4 | −4.1 / −1.5 / −3.0 / −2.5 | −7.6 / −2.9 / −5.7 / −4.8 | −1.9 / −0.1 / −1.1 / −1.8 |
| 4-8k | −2.4 / −1.0 / −1.9 / −1.3 | −11.1 / −5.3 / −8.8 / −5.8 | −8.0 / −2.4 / −5.7 / −5.5 | −4.0 / −0.4 / −2.5 / −3.6 |

- **The top is where turning bites, as at home.** At 4-8 kHz, turning to 90-135° drops the direct sound by 8-11 dB
  and the CDR by 5.5-5.8 dB, against 4.8 and 2.6 dB at Jay's 90°. The diffuse moves about half as much as the
  direct, as in brief A.
- **What doesn't carry over: the low band isn't still here.** The low-band CDR falls too, raw +4.5, +3.5, +3.1, +1.4
  and +1.6 dB at 0, 45, 90, 135 and 180°. At home, 500 Hz moved −0.8 to +0.5 dB. So the contrast's drop (about
  −3 dB) is smaller than the 4-8 kHz CDR's (about −5). The level drops at low frequencies are likely also partly
  speech content, since the stretches are short and the talkers' effort varies, and each bin rests on 2-13
  stretches.

## 3. Distance, with real truth
On facing stretches (within 30°), against log10 tracked distance, in dB per decade:

| statistic | pooled | within session (one intercept per recording and talker) | eval task 4, rec 2 alone |
|---|---|---|---|
| contrast | −5.1 ± 4.4 (n 17) | −0.7 ± 6.7 (n 11, 5 sessions) | +2.1 (n 5) |
| range statistic (mean CDR 1.1-8 kHz) | −8.6 ± 2.7 (n 17) | −8.7 ± 3.1 (n 11, 5 sessions) | −4.8 (n 5) |

- **The range statistic falls −8.6 dB per decade,** in line with brief 20's −7.6 on LOCATA, against −2.6 in Jay's
  house. Within a session it is the same, −8.7. Widening to facing within 45° (n 26) gives −9.1 ± 1.9.
- **The contrast can't be called flat or sloped here.** The pooled slope is −5.1 ± 4.4 and the within-session slope
  −0.7 ± 6.7. These stretches span only 0.9-2.5 m (0.45 decade), and a 2.5 dB scatter per stretch over 17 stretches
  can't resolve a few dB per decade. Widening to within 45° (n 26) gives −5.3 ± 2.9 pooled and −1.6 ± 3.8 within a
  session. That leans toward "it falls between sessions, less within one", but it is not a measurement. Only one
  recording has enough facing stretches for a slope of its own.

## 4. No reference: one fixed threshold
Every stretch is read on its own. Toward means within 30°, turned 90° or more, fade 120° or more. All scores are
balanced accuracy.

| rule | toward against turned | fade against the rest |
|---|---|---|
| **Jay's number, unchanged (−1.00 dB)** | **81%** (12/17 toward, 11/12 turned) | **74%** (9/10 fade, 21/36 rest) |
| Jay's number, the other end of its range (−1.25 dB) | 80% (13/17, 10/12) | 71% (8/10, 22/36) |
| LOCATA's own number, chosen on the other recordings | 73% (12/17, 9/12); threshold −1.75 to −1.00 | 61% (5/10, 26/36); threshold −3.25 to −1.00 |
| The "ceiling": the recording's other facing stretches as reference | 63% (5/11, 8/10) | 60% (7/9, 11/26) |

- **Jay's threshold carries over as it stands.** It scores 81% here, against 75% on his own walks, and LOCATA's own
  left-out choice lands on the same number (−1.75 to −1.00 dB). The 8-point gap between the two rows is the cost of
  choosing a threshold on 12-17 stretches, not a different optimum.
- **The fade is weaker than toward against turned, because 90° reads as low as 135-180°.** Of the 15 "rest" stretches
  called fade, 6 are at 70-103°, 4 at 43-50° and 5 within 30° (the low end of the facing spread). This cue says "turned past
  about 60°", not "past 120°".
- **The labelled reference is no ceiling here.** 11 of the 46 stretches have no other facing stretch in their
  session. The rest have one to two, each 1.5-3 s, so the reference carries the 2.5 dB per-stretch scatter. Sessions
  also don't sit at different levels: the facing spread within a session (2.5 dB) equals the spread overall (2.4 dB).
  So a same-session reference adds noise and removes nothing. Brief A found the reference needs about 5 stops to
  settle, and LOCATA has at most 3 per talker.
- **Toward up to 45° or 60°** with Jay's −1 dB: 82% (19/26 toward) and 81% (21/30). This is the step from section 2,
  seen in the scores.
- **Without the eval task 4 recording 2 stretches** (28 left): 78% toward against turned (9/13, 6/7) and 71% fade.
  The pattern isn't one recording's.

**Side check, not the brief's cue:** with a threshold chosen on the other recordings, the range statistic alone
scores 83% (17/17 toward, 8/12 turned) and the 4-8 kHz CDR alone 88%; for the fade, 86% and 91%. These beat the
contrast on LOCATA only because every talker here is 0.9-3 m away. Turned, the range statistic reads 3.5-4.9 dB lower
than facing. That is 0.4-0.6 decade of distance at LOCATA's −8.6 dB per decade, and Jay's rooms span 1-8 m. The
contrast is the cue meant to survive distance, so it stays the pick. Read through CdrRange's −20 dB per decade unit,
turning draws the talker 1.5-1.8x farther here, against 1.2-1.3x at home.

**Sensitivity, no guard around the other talker** (65 stretches: 18, 21, 12, 12 and 2 per bin): the raw contrast
reads −0.1, +0.1, −2.3, −2.3 and −2.4 dB per bin. Jay's −1 dB scores 78% toward against turned and 71% fade,
LOCATA's own number 69% and 66%, and the reference 70% and 62%. Same picture.

## 5. Beside Jay's walks

| | Jay's walks (`fixed_threshold.txt`, brief A) | LOCATA (this brief) |
|---|---|---|
| unit | stop at one spot, 7.2 s of speech | stretch, 1.9 s of speech (1.5-3.3) |
| room, pair | his house (3 rooms), phone 157 mm | Berlin computing lab (T60 0.55 s), DICIT 160 mm |
| facing truth | called, 0/90/135/180 | tracked, binned 0/45/90/135/180 |
| contrast facing | +0.0 dB (sd 1.9, n 16) | +0.3 dB (sd 2.4, n 17) |
| contrast turned (≥ 90°) | −2.3 dB (sd 1.7, n 27) | −2.6 dB (sd 1.5, n 12) |
| turned reading lower than reference | 26 of 27 | 13 of 13 (any distance), 7 of 7 (within 0.5 m) |
| shape | done by 90°, flat to 270° | 45° = facing, done by 90°, flat to 180° |
| low band (0.1-1.1 kHz CDR) when turned | barely moves (−0.8 to +0.5 dB at 500 Hz) | falls about 3 dB by 135-180° |
| fixed threshold | −1.25 to −1.00 dB, chosen on the other walks | Jay's −1.00 unchanged; own choice −1.75 to −1.00 |
| toward against turned, fixed threshold | 75% (11/16, 22/27) | 81% (12/17, 11/12) |
| fade (≥ 120°) against the rest | 79% (room reference, brief A) | 74% (Jay's −1.00, no reference) |
| per-session reference | the tape's 90th percentile − 1.5 dB: 78% | the recording's facing stretches: 63% |
| range statistic, dB per decade | −2.6 (called distance) | −8.6 ± 2.7 (tracked) |
| contrast, dB per decade | −6.6 to +9.9 by ladder, about −3 overall | −5.1 ± 4.4 pooled, −0.7 ± 6.7 within session |

## What didn't hold, and the limits
- **LOCATA is thin for this.** 46 stretches in 13 recordings, 2 at 180° and 6 at 90°, and 18 from one recording.
  Three task 4 recordings give nothing, because their talkers seldom speak alone. The headline numbers rest on 17
  facing and 12 turned stretches.
- **The low band moves here.** This contrast's anchor was chosen because facing left it alone in Jay's house. On
  LOCATA the low-band CDR falls too, so the contrast keeps only half to two-thirds of the 4-8 kHz CDR's drop. That it still
  scores 81% says the high band carries it. Whether the low band's fall is the room or the short stretches can't be
  told from 2-8 stretches per bin.
- **The distance question stays open for the contrast.** 0.45 decade of tracked distance and 17 stretches can't
  resolve a slope of a few dB per decade.
- **The fade boundary isn't on this cue.** 90° reads like 135-180°, so "past 120°" can't be told from "past 90°".
