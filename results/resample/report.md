# When to re-read within an utterance: angle, range and facing (2026-10-23)

Brief 21, on LOCATA. The truth runs continuously while people walk and talk: the tracked head's bearing, distance and
facing, every 50 ms of every utterance. Each update policy shows one value at each moment and is scored against that
truth over time:
- **error:** time-weighted, and the share of time within tolerance
- **jitter:** moves per minute
- **lag:** how long the shown value stays out of tolerance once it has drifted out

**Short answer:**
- **Angle: re-read.** A half-second GccPhat re-read every 0.25 s, moving the shown bearing only when the read passes
  brief 11's dim rule and differs by more than 5 deg, is right (within 10 deg) 61% of the time for moving talkers,
  against 50% for the shipped hold. It halves the lag, from 1.1 to 0.5 s. It costs about 36 moves a minute, against 173
  if every re-read were shown. For still talkers it changes nothing.
- **Range: don't re-read within an utterance.** The per-utterance CDR, as shipped, is the best of the policies tried.
  Sliding 0.5 s or 1 s windows are noisier than the movement they'd track, and follow a real 20% change of distance
  about as often as a coin.
- **Facing: no update cadence helps yet, because the cue barely reads facing.** Per phrase is per utterance here
  (1.05 phrases per utterance), and the head turns a median 25 deg within an utterance. Brief 20's cue (HF minus LF CDR)
  separates toward from away only weakly: AUC 0.61-0.64, intervals overlapping across every cadence. When the head
  really turns, the sliding cue follows the right way 56-62% of the time, about chance.

## What was run
- **Data:** LOCATA tasks 3 and 4, DICIT array, dev and eval, the 160 mm pair (mics 5-10, the phone's spacing) and the
  80 mm pair (mics 6-9).
  - **Utterances:** 330 per pair, 12.5 minutes of speech. An utterance is a talker's VAD merged across gaps under 0.3 s,
    brief 10's onset rule. They're short: median 2.1 s, longest 5.8 s.
  - **Phrases:** VAD runs split by gaps of 0.1 s or more.
- **Truth:** on a 50 ms grid from each onset to the utterance's end, at valid tracking only:
  - **bearing:** the exact two-mic delay to the head, in the schemes' convention
  - **distance:** to the pair's centre
  - **head orientation:** `ref_vec`, which brief 10 checked is the facing direction
  - **facing:** relative to the array
- **The schemes:** `src/` is unchanged.
  - **The copy:** `harness/resample/GccPhatSpan.mjs` is GccPhat with one read appended. `readSpan` sums the lock's same
    47 frames over any half second and weights them by the utterance's own onset pause. Placed where the lock sits, it
    reproduces the stream's lock on 660 of 660 utterances.
  - **CDR:** a copy of `cdr_direct.py`'s direction-free CDR, with its c/2d clamp switchable for the 0.1-1 kHz band. With
    the clamp on, it matches `src` exactly.
- **The dim rule** (brief 11): commit a read when GccPhat's angle-1 share minus its angle-2 share is at least 0.2, and
  it isn't within 10 deg of a pause read of share 0.5 or more. 51% of the re-reads pass it, about the same as onset
  locks (55%).

## 1. How fast things move while someone talks
At the 160 mm pair, during voiced speech (median / 90th percentile; `tables.md` has 0.25 s and task by task):

| over | bearing | distance | head orientation | facing the array |
|---|---|---|---|---|
| 0.5 s | 2.2 / 6.7 deg | 0.04 / 0.15 m (2.5 / 9.5%) | 5.3 / 19 deg | 5.5 / 19 deg |
| 1 s | 4.5 / 13.4 deg | 0.09 / 0.28 m (4.8 / 17.5%) | 9.4 / 35 deg | 10 / 34 deg |

- **The bearing over half a second** matches brief 10's 2.1 / 6.6 deg.
- **The head turns more than twice as fast as the bearing changes.**
- **Distance changes slowly:** a median 5% a second.

## 2. Angle
All 330 utterances, 160 mm. Error in deg; tolerance 10 deg.

| policy | time within 10 deg | median / mean error | moves per minute after the lock | out of tolerance: median / 90th pct episode (s) |
|---|---|---|---|---|
| GccPhat as shipped: settle, lock, hold | 56.5% | 8.1 / 15.2 | 0 | 1.05 / 2.46 |
| Angle2 at its own onset, held | 45.8% | 11.5 / 20.0 | 0 | 1.12 / 2.41 |
| re-read every 0.25 s, every read shown | 63.6% | 6.4 / 15.9 | 173 | 0.40 / 1.40 |
| re-read every 0.25 s, dim rule, move on any change | 63.7% | 6.5 / 15.0 | 90 | 0.50 / 1.60 |
| **re-read every 0.25 s, dim rule, move if > 5 deg** | **62.4%** | **6.9 / 15.1** | **36** | **0.50 / 1.67** |
| re-read every 0.25 s, dim rule, move if > 10 deg | 60.3% | 7.3 / 15.4 | 23 | 0.60 / 1.62 |
| re-read every 0.25 s, dim rule, move if > 15 deg | 59.0% | 7.6 / 15.6 | 19 | 0.70 / 1.75 |
| re-read every 0.5 s, dim rule, move if > 5 deg | 61.4% | 7.2 / 15.0 | 26 | 0.65 / 1.74 |
| re-read every 0.5 s, dim rule, move if > 10 deg | 59.6% | 7.5 / 15.3 | 18 | 0.70 / 1.78 |

**Moving against still talkers** (the true bearing moved more than 10 deg within the utterance, or not):

| policy | moving (147): time within 10 deg | moving: moves per minute | still (183): time within 10 deg | still: moves per minute |
|---|---|---|---|---|
| shipped hold | 49.8% | 0 | 63.7% | 0 |
| every 0.25 s, every read shown | 64.1% | 191 | 63.1% | 152 |
| every 0.25 s, dim rule, > 5 deg | 61.0% | 45 | 63.8% | 25 |
| every 0.25 s, dim rule, > 10 deg | 57.9% | 27 | | |

- **The gain is all in the moving talkers:** 50% to 61%, with the lag halved. For still talkers re-reading gains
  nothing, and costs 25 moves a minute with the rule (152 without it). `tradeoff.png` plots the trade-off.
- **The dim rule is what makes re-reading usable.** It keeps nearly all of the accuracy every read shown would give
  (63.7% against 63.6%) at half the moves, and the 5 deg threshold halves them again for 1.3 points.
- **Every 0.25 s beats every 0.5 s** at the same threshold by about a point, with a slightly shorter lag (0.5 against
  0.65 s).
- **The mean error stays at about 15 deg under every policy.** It's carried by the other talker's reads (batch A), and
  no update policy removes those. The median falls from 8.1 to 6.9 deg.
- **Angle2 held at its own onset** is the weakest policy here (45.8%). It's an onset read, not meant to track.
- **The 80 mm pair** says the same: shipped 56.7%, every 0.25 s with the rule and 5 deg 62.4%. **By task**, the single
  talker of task 3 gains most: 64.9% to 73.6% with the rule and 5 deg, 76.3% with every read shown.

## 3. Range
160 mm. Distance as a ratio to the talker's opener (their first utterance in the recording, which isn't itself
scored), from the CDR by the room law, 6 dB per doubling. Tolerance 25% (1.9 dB). 306 utterances.

| policy | time within 25% | median / mean error (dB) | moves per minute | follows a real > 20% change (57 utterances) |
|---|---|---|---|---|
| **per utterance, shipped bands (as shipped)** | **50.6%** | **1.92 / 2.44** | 0 | never moves |
| sliding 0.5 s, shipped bands | 30.5% | 3.16 / 3.50 | 77 | 57.9% right way |
| sliding 1 s, shipped bands | 35.2% | 2.71 / 3.15 | 35 | 57.9% right way |
| per utterance, LF band (0.1-1 kHz) | 38.8% | 2.44 / 3.09 | 0 | never moves |
| sliding 0.5 s, LF band | 34.6% | 2.81 / 3.42 | 91 | 52.6% right way |
| sliding 1 s, LF band | 36.1% | 2.78 / 3.29 | 40 | 57.9% right way |

- **Re-reading range within an utterance makes it worse.** A talker's distance moves about 5% a second, and the
  0.5-1 s CDR's own scatter is far larger. Where the distance really does change by more than 20% within an utterance,
  the sliding range moves the right way about as often as chance (53-58%).
- **The first half second is the best read.** Probably because it holds the onset, before the room's tail builds up;
  this run doesn't test why.
- **The LF band alone is worse than the shipped bands** at every window. Brief 20 asks whether LF resists turned heads.
  That's a different question, but LF doesn't help here.
- **The 80 mm pair** says the same: per utterance 45.9%, sliding 1 s 31.4%.
- **No rate clamp,** as Jay removed it on 2026-09-30.

## 4. Facing
Two questions: how fast the truth changes (a perfect facing reading, held under each policy), and whether brief 20's
cue, now landed, follows it under each policy.

**The truth's own rate of change** (a perfect reading, held):

| update | time within 30 deg | median / mean error | updates per minute |
|---|---|---|---|
| per utterance | 83.3% | 9.7 / 16.0 deg | 0 |
| per phrase | 83.5% | 9.4 / 15.7 deg | 1.4 |
| every 0.5 s | 99.6% | 1.8 / 3.7 deg | 98 |
| every 0.25 s | 100% | 0.8 / 1.8 deg | 196 |

- **Per phrase is per utterance here.** LOCATA's utterances hold 1.05 phrases on average: these talkers rarely pause
  0.1-0.3 s mid-utterance.
- **The head turns a median 25 deg within an utterance** (90th percentile 67 deg; over 30 deg in 42% of them). Held per
  utterance, even a perfect reading is more than 30 deg off a sixth of the time.
- **So a facing reading would need refreshing within an utterance, about every 0.5 s.**

**Brief 20's cue under each policy.** The cue is F = HF CDR (4-8 kHz) minus unfloored LF CDR (0.1-1 kHz), against the
same talker's opener; facing away should lower it. Each policy's shown value is scored on the grid against the tracked
facing (toward under 90 deg, away over), at 160 mm:

| update | separates toward from away: AUC [95% interval, resampling utterances] | AUC, log distance removed | moves the right way when the head turns > 45 deg (48 turns) |
|---|---|---|---|
| per utterance | 0.62 [0.56, 0.69] | 0.61 | never moves |
| per phrase | 0.61 [0.55, 0.67] | 0.60 | 8% (85% don't move) |
| sliding 0.5 s, every 0.25 s | 0.63 [0.57, 0.69] | 0.63 | 60% |
| sliding 1 s, every 0.25 s | 0.64 [0.57, 0.70] | 0.64 | 56% |

The 80 mm pair is the same (0.61-0.64; `tables.md`).

- **The cue carries a little information about facing,** pooled over talkers and recordings. Every interval sits above
  0.5, and removing distance doesn't change it. Brief 20 found the same cue fails as a classifier: 45% balanced
  accuracy, toward or away, with a threshold carried between recordings. The two results fit together: a weak pooled
  association that a threshold from one recording doesn't carry to another.
- **No cadence reads it better.** The intervals overlap almost entirely: sliding windows score 0.02-0.03 higher, well
  inside the noise.
- **Within an utterance it doesn't follow the head.** When the head turns more than 45 deg, the sliding cue moves the
  right way 56-62% of the time, close to chance on 48 turns (a 95% interval on 48 coin flips spans about 36-64%).
- **So the update cadence isn't facing's bottleneck; the cue is.** Re-reading every 0.5 s would only pay once a cue
  follows the head.

## What this means for the app
- **Angle:** keep the onset read as shipped. After the lock, re-read every 0.25 s and move the dot only when the
  re-read passes the dim rule and differs by more than 5 deg. Use 10 deg if 36 moves a minute is too lively: that gives
  23 moves a minute for 2 points.
- **Range:** keep the one read per utterance from its first half second. Don't slide it.
- **Facing:** don't spend updates on it yet. Brief 20's cue barely reads facing under any cadence. When a cue does
  follow the head, re-read it about every 0.5 s within the utterance; per phrase is too seldom to matter.

## Caveats
- **One room and two talkers at most,** walking slowly; utterances of 2-6 s. Longer monologues would favour re-reading
  more.
- **The truth is the head marker** (the mouth is a few cm in front). Utterance boundaries come from LOCATA's VAD, not
  the Conductor's ears.
- **The range ratios use the fixed 6 dB-per-doubling law** that brief 20 is testing. A different slope would rescale
  every range policy alike, not reorder them.
- **Lag is measured as out-of-tolerance episodes.** An episode still running when the utterance ends counts at its
  observed length.

## Files
- **Summary:** `summary.json`, with every policy by pair, by task, and for moving against still utterances; the motion
  statistics; the range-follows-change test; the facing analysis; and brief 20's cue under each policy
  (`facing_cue`).
- **Tables:** `tables.md`.
- **Plot:** `tradeoff.png`, accuracy against moves per minute for every angle policy.
- **Rebuild:** `harness/resample/` (see its README).
