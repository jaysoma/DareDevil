# Brief G: how much speech the facing call needs (2026-10-24)

**The call needs about 2 s of speech: one utterance of 2-4 s scores 75% balanced (n 54), as well as a whole stop, and
2.2 s pooled from any stop does the same. One short utterance is not enough (under 1 s: 59%, n 111; the Conductor's
0.13-0.5 s read: 63%, n 176), but two utterances pooled at the same spot and facing get back to 79% (n 29).**

The call throughout is round 1's: the contrast CDR 4-8 kHz minus CDR 0.1-1.1 kHz, called turned below a fixed threshold.
The threshold is recomputed with each walk left out, on the other walks' whole stops (−1.25 to −1.00 dB), so every score
here is on a walk the threshold never saw. Facing = facing 0; turned = 90, 135 or 180.

Files: `harness/rotation/utterance/` (`hops.py` per-hop estimator, `utterance.py` everything else, `figures.py`);
`numbers.json` (every figure below, plus each utterance as a row); `utterance_run.txt` (the printed summary);
`pooling_curve.png`; `continuous_turns.png`.

## What held

### One utterance alone (step 2)
Every utterance is read as the app reads it: the estimator restarts cold at the utterance's first speech hop, the first
0.13 s is dropped (the Conductor's `SETTLE_S`), and the speech hops from there to the end are pooled.

| length | n | facing: mean contrast (sd) | turned: mean (sd) | balanced | facing called facing | turned called turned |
|---|---|---|---|---|---|---|
| under 1 s | 111 | −0.9 dB (2.6) | −2.3 (2.8) | **59%** | 19/35 | 49/76 |
| 1-2 s | 64 | −0.3 (2.9) | −2.5 (2.0) | **67%** | 20/31 | 23/33 |
| 2-4 s | 54 | +0.1 (1.9) | −2.8 (1.6) | **75%** | 11/16 | 31/38 |
| 4 s and over | 1 | | | not scored | | |
| all | 230 | −0.5 (2.6) | −2.5 (2.4) | 66% | 50/82 | 104/148 |

- **The loss is scatter, not a shift.** A threshold chosen on the other walks' utterances instead of their stops scores
  58%, 66% and 74% in the same bins. Retuning for short speech buys nothing. The facing mean does sag 1 dB under 1 s,
  but the spread (2.6-2.9 dB) is what sinks it.
- **Half the under-1 s bin is word tails.** The 0.3 s pause rule splits off the end of a sentence ("...the fridge" in
  231921 and 231705). 53 of the 111 pieces have under 0.25 s of speech after the settle; they score 54%. The other 58
  score 64%. The live app's recogniser would mostly not split there, so 64% is the fairer figure for a short utterance.
- **A full sentence is enough.** The 2-4 s bin's 75% equals round 1's stop-level figure. The same 42 stops pooled whole
  score 73% here (11/16 facing, 20/26 turned).

### The pooling curve (step 3, `pooling_curve.png`)
Contiguous speech of each length is drawn 300 times from inside each stop (speech hops only, pauses skipped) and called
with the stop threshold. Each stop's share of correct draws counts once.

| seconds pooled | 0.5 | 1 | 2 | 3 | 4 | 5 | 7 |
|---|---|---|---|---|---|---|---|
| the 16 stops with 7 s or more | 70% | 75% | 76% | 79% | 81% | 83% | 81% |
| every stop with that much speech | 63% (42) | 67% (40) | 75% (35) | 77% (30) | 79% (24) | 77% (19) | 81% (16) |
| scatter of one stop's draws (sd) | 2.1 dB | 1.6 | 1.1 | 0.9 | 0.7 | 0.6 | 0.3 |

- **Across every stop, 70% comes at 1.4 s and 75% at 2.2 s.** The 16 long stops are easier (whole, they score 81%
  against 73% for all 42), so on them alone the call reaches 70% at 0.5 s and 75% at 1.2 s. The all-stops row is the
  one to plan on, since it includes the spots where Jay said less.
- **The utterances sit on the curve.** One utterance alone (cold estimator) lands within 2-4 points of the warm
  subsamples at the same length (59/67/75% at a mean of 0.54/1.43/2.44 s). So the cold start costs little beyond the
  settle.
- **Turned is the easy side.** At every length, turned is called right 80-96% of the time and facing only 60-74%. The
  threshold sits about 1 dB under the facing mean, so the facing scatter is what limits the call.
- A threshold retuned at each length (chosen on the other walks' draws) does worse, at 63-72%. With 16 stops it
  overfits, so keep the stop threshold.

### Pooling at a held angle (step 5)
Each utterance is summed with the earlier ones in its group and the group's running contrast is called.

| group | 1 utterance | 2 | 3 | 4 |
|---|---|---|---|---|
| same spot and same facing | 65% (n 30, 1.1 s) | **79%** (29, 2.2 s) | 83% (26, 3.0 s) | 89% (22, 3.8 s) |
| same, only the 22 groups with 4 or more utterances | 70% | 80% | 83% | 89% |
| one stop (callout to callout) | 70% (42) | 78% (36) | 80% (29) | 83% (26) |

- **Two utterances reach the stop-level 75%** (about 2.2 s of speech). That is the pooling curve's 2 s, reached by
  adding utterances instead of waiting inside one. On the fixed population of 22 groups the climb is the same, so it
  isn't groups dropping out. From 5 utterances on, it is 88-100%, but on only 6-17 groups.
- **Pooling by spot alone breaks the call.** Summing every utterance at a spot, whatever the facing, gives 83% on the
  first utterance and then 42-60% (n 10 spots). Turned speech is averaged with the facing speech before it. A held
  angle can't see a turn in place, so on its own it groups exactly this way. The pooling above holds only when the
  group is one facing.

### The Conductor's window (step 4)
On the 176 utterances of 0.5 s or more, the same utterance is read two ways. The Conductor's range read takes every hop
from 0.13 s to 0.5 s after onset. The whole utterance takes all its speech hops.

| read | balanced | facing | turned |
|---|---|---|---|
| 0.13-0.5 s (the Conductor's range read) | **63%** | 39/66 | 73/110 |
| whole utterance | **71%** | 43/66 | 84/110 |

The short read isn't biased: it averages 0.2 dB under the whole utterance. But it scatters 2.6 dB around it
(correlation 0.54), and a retuned threshold only lifts it to 64%. For facing, the range's half-second read is too short;
the call needs the rest of the utterance.

### The continuous turns (step 6, `continuous_turns.png`)
Each utterance is called with the threshold chosen on all 10 labelled walks (−1.25 dB). Angles are where the
utterance's midpoint falls if the turn ran at an even rate.

- **160546 (counterclockwise, 1.25 m):** facing before the turn, 3 of 3. Through the circle it reads +0.2 dB at 43°,
  −0.6 at 98° (called facing), −1.5 at 170°, −2.0 at 206°, −2.2 at 239°, −3.3 at 284° (all called turned), and back to
  +2.3 at 356°. It follows the turn utterance by utterance. The 90° side reads facing.
- **161331 (clockwise, 2 m, folded to 111 mm):** facing before, 2 of 2. Turned at 172° (−2.3) and 209° (−4.4). Its two
  long utterances (5.5 s from 0° to 150°, and 4.6 s from 230° to 360°) each straddle facing and side, and both read
  facing.
- **020305 (counterclockwise, small carpeted room):** turned at 140°, 182° and 298°, facing at 85° and 344°. At 246° it
  reads +2.9 dB, called facing. The stretch before it, taken as facing the phone, is called facing 9 times of 13 (see
  question 2).

## Limits
- **n is small where it matters most.** 54 utterances of 2-4 s; one of 4 s or more; 16 stops with 7 s of speech. The
  bins' rates are ±6-12 points on their n.
- **Set aside:**
  - **walk-122038, whole:** its decode runs 1.5-2.5 s late. Only 18% of the speech in its stops falls inside a decode
    segment, against 90-100% on every other walk, so the cuts found 2 utterances there (question 1).
  - **One utterance:** 221126 at 186.0-186.5 s reads +16.6 dB, 15 dB from every other.
  - **49 pieces under 0.25 s,** dropped as breaths and clicks.
  - **The stop threshold is round 1's own,** so it still includes 122038.
- **The speech mask is per hop here.** A hop is speech when its 1.1-8 kHz power (smoothed over 53 ms) is 10 dB over the
  tape's 20th percentile. It finds 6.0 s per stop against round 1's 0.5 s windows, and scores whole stops at 73%, not
  75%. The per-hop estimator reproduces `band_windows.json` to 0.01 dB when summed into its windows.
- **The live app's utterances are the recogniser's, not these.** Cutting at 0.3 s pauses splits sentences the phone
  would keep whole, which is why the under-1 s bin is half tails.
- **Every utterance is Jay.** "Every utterance is a new speaker" is the case being planned for; these numbers are one
  voice in two rooms.

## Questions for Jay
1. **walk-122038, 8-35 s:** the speech comes in bursts at 8-10, 13-15, 20-22, 26-28 and 32-35 s. The decode places its
   callouts at 9.7, 16.2, 22.5, 27.0, 29.5 and 34.6 s. Are the bursts the callouts themselves ("90 degrees to the
   right", "facing away", "90 degrees facing left", "facing the phone again")? If so, each stop in `facing_stops.json`
   holds the next callout, and 23-27 s (labelled 90) holds the "facing the phone" one.
2. **walk-020305, 90-125 s** (brief A's facing stretch): the decode has "now two meters from the phone dead center, I'm
   going to do a rotation, I'm going to talk while I rotate clockwise" partway through. Did a clockwise turn happen in
   there, before the counterclockwise one at 128 s? The 4.7 s utterance at 112.7 s reads turned (−1.6 dB).
3. **walk-020305, 133-135 s:** at about 250° on the counterclockwise turn, the call reads +2.9 dB, as facing as
   anything on the tape. Was anything close in front of you there (the bed, the tapestries)?
