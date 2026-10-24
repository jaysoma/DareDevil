# The colour of rotation, against the colour of distance (brief A, 2026-10-24)

**I'd keep CDR 4-8 kHz minus CDR 0.1-1.1 kHz, the contrast `facing_pooled` already uses.** It reads lower at 26 of 27
turned stops (−2.2 dB). Of the 15 candidates tried, it is also the one that still separates facing from turned when
the reference is the whole room rather than one opener: 75% balanced, and 79% for the fade past 120°.

Scripts: `harness/rotation/colour/octave_windows.py` (step 2, run on Jay's box) and `colour.py` (steps 3-8). Labels:
`harness/rotation/colour/facing_stops_signed.json`, with Jay's corrections of 2026-10-24: 231921 turns clockwise
throughout, 224302's turn is counterclockwise, and 221126's 205-221 s stop is split into 90, 180 and 270. Numbers: `numbers.json` and `colour_run.txt` beside this file.
Figures: `fingerprints.png` and `continuous_turns.png`. Data: 43 stops at 11 spots in 10 walks, 7.2 s of speech per
stop; all 43 are signed.

## 1. The shape of rotation
The x axis is the degrees turned since facing the phone: 90 is the side on the way out, 270 the side on the way back,
and 360 is facing the phone again. Jay turns clockwise except in 213304 and 224302, and he speaks after each turn, so
each stop is one held facing. Each value is in dB against the same spot's facing-0 stops, as the mean over spots:
90 out (9 spots), 180 away (9), 270 back (7). Bands marked * are below c/2d = 1.09 kHz, where the CDR is
ill-conditioned.

| band | direct 90 / 180 / 270 | diffuse 90 / 180 / 270 | total 90 / 180 / 270 | CDR 90 / 180 / 270 |
|---|---|---|---|---|
| 125 * | +0.2 / −0.4 / −0.7 | −0.1 / +0.1 / −0.4 | +0.0 / −0.1 / −0.5 | +0.3 / −0.5 / −0.3 |
| 250 * | −1.6 / −2.0 / −1.9 | +0.1 / −0.8 / −0.2 | −0.9 / −1.6 / −1.5 | −1.7 / −1.2 / −1.8 |
| 500 * | −2.5 / −2.2 / −1.0 | −1.7 / −2.3 / −1.5 | −2.1 / −2.2 / −1.3 | −0.8 / +0.1 / +0.5 |
| 1k * | −2.4 / −3.4 / −0.9 | −1.4 / −1.9 / −0.2 | −2.0 / −2.7 / −0.7 | −1.0 / −1.5 / −0.8 |
| 2k | −1.8 / −2.6 / −2.1 | −0.5 / −0.5 / −0.7 | −1.2 / −1.6 / −1.5 | −1.4 / −2.2 / −1.5 |
| 4-8k | −4.8 / −6.0 / −4.5 | −2.2 / −2.8 / −2.2 | −3.7 / −4.6 / −3.6 | −2.6 / −3.2 / −2.2 |

- **The shape is a wide, flat-bottomed U, and it lives in the highs.**
  - At 4-8 kHz the direct level falls 4.8 dB in the first 90°. It then drops only another 1-2 dB through 180 (−6.0)
    and 225 (−6.8, 2 spots), climbs back to −4.5 at 270 and returns to 0 at 360.
  - Facing to side is most of the change. Side to away is a small step, which is why toward against turned is
    separable and 90 against 180 isn't.
- **The colour tilts with the turn:** at 180, the direct sound falls from −0.4 dB at 125 Hz to −6.0 dB at 4-8 kHz. That
  is the mouth's directivity.
- **The diffuse moves less, but it does move:** −2.8 dB at 4-8 kHz at 180, about half of the direct's drop. The voice
  isn't just quieter, since 125 Hz holds (total −0.1 dB, sd 0.8). Part of what the estimator calls diffuse follows
  where he faces, such as early reflections off whatever is in front of him.
- **The CDR draws the same U with a third to a half of the scatter.**
  - At 4-8 kHz it reads −2.6, −3.2 and −2.2 dB at 90, 180 and 270, with an sd over spots of 1.2-1.6 dB, against
    3.3-4.1 for the direct level.
  - Below 1 kHz it hardly moves (−0.8 to +0.5 dB at 500 Hz). That makes the low band the anchor that facing leaves
    alone.
- **It closes:** back at 360, every band reads within 0.5 dB of the opening facing, so a walk doesn't drift.

## 2. Out against back: 180 → 270 is brighter, and the way back may be a little brighter than the way out
There are 6 spots with a side stop both ways: 030615, 171645, 215800, 231705 and 231921 clockwise, and 213304
counterclockwise. 213304's way back is its 90, so out against back isn't the same as left against right.

| walk (spot) | out → back (s) | total 4-8 kHz, back − out | contrast, back − out |
|---|---|---|---|
| 030615 (2 m) | 34-56 → 106-123 | +4.4 | +3.0 |
| 171645 (2 m) | 7-13 → 20-30 | +0.5 | +0.2 |
| 213304 (6 m, CCW) | 269-289 → 312-337 | +0.1 | +0.2 |
| 215800 (2 m) | 10-16 → 22-26 | +2.6 | +0.5 |
| 231705 (2 m) | 22-36 → 84-128 | −1.4 | +0.1 |
| 231921 (5 m) | 29-47 → 98-122 | +0.1 | +0.2 |

- **From 180 to 270, the way back gets louder at the top.** At 4-8 kHz the 270 stop reads above the 180 stop before it
  by +2.4 dB in the direct sound (6 of 6 spots) and +1.6 dB in total (5 of 6). The diffuse rises +0.9 dB. Below
  1 kHz the change is under 0.6 dB. This is what Jay hears, and it is the U's far wall: the mouth coming back round.
- **Back against out, at the same side: the same direction, but within the noise.**
  - The way back reads higher at 4-8 kHz at 5 of 6 spots: total +1.0 dB, direct +1.5 dB, diffuse +0.6 dB.
  - The contrast is higher at all 6, but by only +0.1 to +0.5 dB at five of them; 030615 is +3.0.
  - Below 1 kHz the way back is slightly lower (−0.7 to −1.0 dB in total).
  - The control, Jay's last facing-phone stop against his first at the same spot, is 0.0 dB at 4-8 kHz on average.
    But spot by spot it ranges from −6.7 to +6.3 dB (5 spots), so two stops at one facing can differ by far more than
    1 dB.
  - The lift is consistent in sign, but this data can't size it. If it is real, it sits in the direct sound, which
    fits the mouth pointing a little toward the phone on the way back; that is a guess, not a measurement.
- **What he faced:** 030615 says "facing the wall" at 90 on the way out. It is the spot with the largest
  difference: the contrast reads 3.0 dB lower there than at 270 on the way back. A hard surface close in front looks
  like a deeper turn.

## 3. The continuous turns: one dip per turn where there is speech to pool
The contrast is pooled over 3 s, against a stretch facing the phone before the turn (`continuous_turns.png`).

- **160546 (1.25 m, counterclockwise, 16-33 s):** one trough, bottoming at −3.5 dB at 26.6 s, near the half-turn. It
  is back to +2.5 dB by 31 s, when he says "I just did an entire circle". The still stretch scatters 1.7 dB.
- **161331 (2 m, clockwise, 8-21 s, folded to 111 mm):** one trough from 10 to 17 s, bottoming at −2.9 dB at 13.5 s
  (the turn's midpoint is 14.8 s), then back above 0 by 18 s. The still stretch scatters 0.6 dB.
- **020305 (small carpeted room, 126-138 s):** it dips to −3.5 dB at 127.8 s, but the stretch facing the phone just
  before it scatters 1.5 dB and itself crosses −2.2 dB. I can't call this one.
- **044350 and 140956:** too little speech (50 and 40 pooled points over 131 and 111 s). No answer from these.
- **221126 (6 m, counterclockwise, 228-237 s):** no speech clears the gate during the turn (below), so it has no
  points.
- **171542 is mono** (below), so it has no CDR.

## 4. The room as the reference beats the opener
Per room, the reference is the mean of every facing-0 stop from the room's other walks, and the threshold is chosen on
those other walks too (left out by walk). The kitchen has 5 walks: 8 facing-0 stops and 15 turned. The living room
has 4 walks: 6 facing-0 and 9 turned. Results for the contrast picked above:

- **Toward against turned (90° or more): 75% balanced.** 19 of 24 turned stops called turned and 10 of 14 facing
  stops called facing (kitchen 12 of 15 and 5 of 8; living room 7 of 9 and 5 of 6).
- **Fade (past 120°) against the rest: 79% balanced.** 8 of 10 fade stops caught and 22 of 28 others kept.
- **Against the walk's opener (the bar's test): 67%.** All 27 turned stops are caught, but only 2 of 6 later
  facing-the-phone stops. The bar reported 61%; the difference is the record-start transient (below) inside two of
  the openers.
- **The reference settles after about 5 facing-0 stops.** One facing-0 stop scatters 2.2 dB around its room's mean
  (kitchen) or 2.0 dB (living room). A mean of k stops errs by about 2.1/√k, which falls under 1 dB (half the turned
  effect) at 5 stops, about 35 s of speech facing the phone. In recording order, the living room's running mean is
  within 0.8 dB of its final value from the 2nd stop on. The kitchen's is within 0.3 dB at the 2nd stop, but a 215800
  stop reading 4 dB high swings it out to 1.1 dB at the 4th.

## 5. Which contrast, and why not the others
A CDR contrast **is** the direct colour against the diffuse colour. Each band's CDR is its direct level minus its
diffuse level, so CDR_hi − CDR_lo = (Dir_hi − Dir_lo) − (Dif_hi − Dif_lo), and the brief's two families are one.

I scored all 145 pairs over 9 bands and 5 families. The score is the turned effect divided by two noise terms added in
quadrature. The first is one facing-0 stop's sd about its spot. The second is the RMS ladder slope times 0.5 decade,
which is 2 to 6 m, the spread of distances in one room. The top eight, plus every CDR contrast against 4-8 kHz, were
then tried with the room as the reference; all 15 are in `numbers.json` → `tried_with_room`.

| contrast | turned effect (dB) | turned stops reading lower | stop noise (dB) | window jitter, pooled | ladder slopes (dB/decade) | score (rank) | room reference | fade | opener |
|---|---|---|---|---|---|---|---|---|---|
| **CDR 4-8k − 0.1-1.1k** | **−2.2** | **26 of 27** | 1.7 | 0.6 | −7, +10, +1, −7 | 0.56 (#24) | **75%** | **79%** | 67% |
| CDR 4-8k − 500 | −2.6 | 25 of 27 | 1.7 | 0.7 | −7, +6, +0, −5 | 0.81 (#4) | 59% | 56% | 56% |
| CDR 4-8k − 125 | −2.7 | 26 of 27 | 1.8 | 0.7 | −6, +12, +0, −14 | 0.54 (#26) | 62% | 59% | 71% |
| CDR 4-8k − 2-4k | −0.9 | 22 of 27 | 0.5 | 0.5 | −2, +10, −3, +0 | 0.32 (#79) | 73% | 55% | 66% |
| CDR 2k − 500 | −1.5 | 20 of 27 | 1.6 | 0.6 | −1, +3, +2, −4 | 0.73 (#8) | 60% | 50% | 60% |
| direct − total colour, 4-8k − 500 | −1.1 | 25 of 27 | 0.7 | 0.3 | −3, +2, +0, −2 | 0.86 (#3) | 68% | 74% | 69% |
| direct − total colour, 2k − 500 | −0.7 | 23 of 27 | 0.6 | 0.3 | −0, +0, +1, −2 | 0.95 (#1) | 68% | 66% | 55% |
| direct colour 4-8k − 125 | −5.0 | 25 of 27 | 4.6 | 1.9 | −7, +14, +3, −12 | 0.74 (#7) | 66% | 72% | 58% |
| total colour (level tilt) 4-8k − 125 | −3.9 | 24 of 27 | 3.9 | 1.8 | −5, +9, +2, −4 | 0.80 (#5) | 52% | 54% | 56% |
| diffuse colour 2-4k − 500 | +1.5 | 8 of 27 | 1.2 | 1.3 | +2, +2, −1, +4 | 0.87 (#2) | 49% | 40% | 31% |

The ladder slopes are in the order 213304, 221126, 020305, 224302.

- **On paper, the narrower low anchors look slightly better.** CDR 4-8k against 500 Hz or 125 Hz moves −2.6 to
  −2.7 dB over the same 1.7 dB stop noise (effect over noise 1.5, against 1.2).
- **With the room as the reference, they fall to 59-62%.** Averaging four octaves steadies the anchor across spots.
- **"Direct − total colour" is the same cue in other units:** it is the direct fraction CDR/(1+CDR), which shrinks the
  effect and the noise together.
- **CDR 4-8 against 2-4 kHz** reaches 73% for toward against turned, but on a 0.9 dB effect, and it fails the fade
  (55%).
- **The levels and the diffuse colours fail** (40-56%).

## What didn't hold
- **Distance doesn't lower the direct sound evenly across bands on these ladders.** Called distance moves almost
  nothing consistently (four ladders, dB per decade, mean ± sd):
  - Total level: −3.0 ± 1.3 at 500 Hz and −3.6 ± 4.7 at 4-8 kHz, where free field would be −20.
  - CDR: near 0 in most bands. Only 2-4 kHz falls the same way on all four ladders (−3.5 ± 1.1).
  - This matches the bar's range statistic (−1.5 dB per decade on these walks), not LOCATA's −20 law.
- **The contrast's distance slope is not one number.** It is −6.6 and −6.8 dB per decade on the two kitchen ladders,
  +9.9 on the living-room ladder (221126, 1-7 m) and +1.0 in the small carpeted room. Stop noise alone allows
  2.6-4.9 dB per decade per ladder, so 221126 is a real difference: distance moves this contrast differently by room.
  The mean (−0.6 dB per decade) hides that, which is why the ranking uses the RMS slope.
- **Stops disagree more than the windows predict.** Two facing-0 stops at one spot differ by 1.7 dB (sd) in the
  contrast, against the 0.6 dB the half-second jitter predicts for a pooled stop, and by up to 6.7 dB in the 4-8 kHz
  level. This floor, not the jitter, is what limits the out-against-back comparison.

## Set aside, and limits
- **The record-start transient.** On 8 of the 15 two-channel tapes, the first 2 s read a 4-8 kHz CDR above 12 dB, up
  to 27 dB. That is the phone being handled, not a talker at 2 m. The first 2.5 s of every tape are left out. This
  touches two labelled stops (231705 0-22 s, 215800 0-10 s) and the first rung of three ladders. Before the fix,
  231705 read 13-20 dB "quieter" at 500 Hz-1 kHz when turned.
- **walk-171542 is mono.** Its second channel is digital silence for the whole tape, in both the `.raw` and the
  `.wav`, so it is out of step 8. Its `tapes/walk-171542/band_windows.json` (outside this brief's folders) is
  meaningless for the same reason.
- **221126 at 6 m is under the speech gate.** The gate is the tape's 20th percentile plus 10 dB, which is 18.6 dB
  here, and the speech at 6 m peaks at 17-19 dB. Its facing stop at 161-200 s keeps 8 of 76 windows (4 s). The
  stops after it (90, 180 and 270 at 205-221 s, facing again at 221-228 s) and the turn at 228-237 s keep 0 or 1
  window each, so the split changes no number.
- **Rooms:** the kitchen is `library.json`'s tag. The living room (122038, 125621, 171645, 221126) is inferred, and
  030615 ("a small room") is out of the room test.
- **Limits:** 10 walks in Jay's house, with self-called facings and distances. 225° is 2 spots. There are no 45° or
  135°-on-the-way-out stops, so the U's walls are drawn from 0 to 90 and from 270 to 360 only.

## For Jay, when convenient
- **Which room were 122038, 125621, 171645, 221126 and 030615 in?**
