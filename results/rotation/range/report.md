# Brief E: a range that turning doesn't throw off

**Put "corrected" in CdrRange.** It is today's statistic plus 0.9 × how far the facing contrast (CDR 4-8 kHz minus
unfloored CDR 0.1-1.1 kHz) falls below −1 dB, over the same 0.13-0.5 s read. It cuts a turned talker's throw from
1.2-1.3x to about 1.07x, and it does better on all of LOCATA's all-reads scores. The cost is about 10 points of read-pair ordering on
Jay's facing ladders. Gated loses to it: the gate costs the same ordering and leaves twice the throw, because a
half-second read can't call facing reliably (57% of facing reads, 79% of turned).

## The headline, beside today's (the Conductor's 0.13-0.5 s read)

| | today | **corrected (k 0.9)** | gated | low band 0.1-1.1 kHz alone |
|---|---|---|---|---|
| **Fling:** mean \|log2\| over 29 turned stops, in doublings | 0.33 | **0.19** | 0.26 | 0.16 |
| **Signed**, at 90 / 135 / 180° (+ = drawn farther) | +0.26 / +0.38 / +0.39 | **+0.09 / +0.10 / +0.10** | +0.17 / +0.30 / +0.30 | +0.02 / −0.09 / −0.03 |
| **Turned stops closer to their spot's facing read than today's** | – | **23 of 29** | 18 of 29 (6 tied) | 22 of 29 |
| **Jay's ladders:** read pairs ≥1.5x apart in the right order (568 pairs) | 82% | 72% | 73% | 69% |
| **LOCATA, all reads (206):** within 1.5x / mean error of the rest / off by 2x+ / ordering | 67% / 0.36 / 25 / 77% | **70% / 0.36 / 18 / 82%** | 67% / 0.35 / 31 / 71% | 63% / 0.43 / 26 / 81% |
| **LOCATA, facing ≤45° (71)** | 86% / 0.31 / 2 / 79% | 87% / 0.30 / 1 / 83% | 83% / 0.31 / 3 / 67% | 70% / 0.41 / 5 / 88% |
| **LOCATA, turned ≥90° (73)** | 45% / 0.43 / 19 / 63% | 51% / 0.42 / 13 / 54% | 48% / 0.41 / 21 / 51% | 52% / 0.50 / 14 / 49% |

A doubling is 2x. +0.38 doublings is 1.30x farther; +0.10 is 1.07x.

## What held

1. **The turn's throw is real on these reads, and matches round 1.**
   - **Today's statistic** reads 1.8 dB lower once turned, against its own facing reads at the same spot.
   - **The drawn range:** turned stops come out 1.20x (90°), 1.30x (135°) and 1.31x (180°) farther. Brief A's
     pooled stops said 1.8-2.5 dB and 1.2-1.3x.
2. **The low band doesn't move with facing at all, and doesn't carry distance well either.**
   - **Turning:** CDR 0.1-1.1 kHz, read unfloored, shifts +0.01 dB when turned (−0.3 dB for 125-500 Hz).
   - **Distance, its own slope:** −3.8 dB per decade on the ladders, against today's −5.0.
   - **Distance, ordering:** it orders 69% of ladder pairs against 82%. 213304 drops 83 → 52% and 224302 70 → 31%.
   - **Facing stop against facing stop:** at the 12 facing stops whose spot has another, it reads 0.38 doublings
     from the spot's other facing stop, against today's 0.26. That is drift with nobody turning: the band is
     ill-conditioned at 157 mm, as brief 20 warned.
3. **Corrected keeps most of the low band's immunity and most of today's distance.**
   - **k is stable:** fitted left out by walk, it lands at 0.85-0.95.
   - **The turned shift** falls from −1.84 dB to −0.59.
   - **Facing reads above −1 dB are untouched** (the hinge), so the correction adds nothing where the talker
     faces the phone and the call agrees.
   - **On LOCATA, a different room and pair** with k carried over from Jay's house:
     - All reads: 70% within 1.5x against 67%, 18 reads off by 2x+ against 25, ordering 82% against 77%.
     - Turned reads: 51% within 1.5x against 45%, and 13 off by 2x+ against 19. Their ordering is worse, though:
       54% against 63% (73 reads).
     - LOCATA's own best k, fitted in-sample, is 0.6, and it scores 0.356 doublings against 0.36 at 0.9: the
       house's k carries over.
4. **The cost of corrected is on Jay's ladders.**
   - **Read pairs:** 82 → 72%, and lower on all four ladders (020305 83 → 74, 213304 83 → 61, 221126 84 → 74,
     224302 70 → 61).
   - **Why:** the contrast jitters 2.4 dB per half-second read (sd about its stop's mean, 231 reads). 43% of facing reads fall below −1 dB and get
     "corrected" anyway, so they draw nearer than they should.
   - **Stop means are spared:** facing stop against facing stop, corrected reads 0.25 doublings, the same as today.
     The extra noise is read to read and averages out over a stop.

## The candidates, one by one (short read)

| candidate | fling (29 stops) | facing vs facing floor (12) | own slope (dB/decade) | turned shift (dB) | ladder ordering | LOCATA all: within 1.5x / off 2x+ / ordering |
|---|---|---|---|---|---|---|
| today | 0.33 | 0.26 | −5.0 | −1.84 | 82% | 67% / 25 / 77% |
| low 0.1-1.1 kHz | 0.16 | 0.38 | −3.8 | +0.01 | 69% | 63% / 26 / 81% |
| low 125-500 Hz | 0.22 | 0.45 | −4.7 | −0.32 | 76% | 59% / 30 / 77% |
| weighted | 0.18 | 0.25 | −4.9 | −0.62 | 68% | 65% / 21 / 83% |
| **corrected** | **0.19** | **0.25** | −6.1 | −0.59 | 72% | **70% / 18 / 82%** |
| gated (last facing read) | 0.26 | 0.24 | −5.0 | −1.84 | 73% | 67% / 31 / 71% |
| gated, holding the mean (a variant) | 0.25 | 0.17 | −5.0 | −1.84 | 72% | 67% / 29 / 71% |
| gated (truth as the call): ceiling | 0.28 | 0.26 | −5.0 | −1.84 | 82% | 67% / 28 / 65% |
| gated (truth, any bearing, the mean): the gate's own ceiling | 0.16 | 0.26 | −5.0 | −1.84 | 82% | 68% / 22 / 72% |

"Own slope" and "turned shift" are the statistic's own, before any gate.

- **Weighted** comes out mostly low band: fitted on all of Jay's walks, it weights 125-500 Hz 0.36, 0.5-1.1 kHz 0.40,
  B1 0.13, B2 0.08 and B3 0.04. It inherits the low band's distance loss (68%) and still keeps −0.6 dB of turn.
- **Gated** is only as good as two calls per half-second read.
  - **The facing call** (contrast below −1 dB means turned) is right for 57% of 86 facing reads and 79% of 154
    turned reads on Jay's walks. On LOCATA it gets 63% and 57%. The −1 dB threshold was fitted on ~7 s stops;
    brief G is measuring how much speech the call needs.
  - **The bearing match:** 105 of the turned calls found no facing read within 5°, so they drew their own turned
    read, marked.
  - **Each failure costs:**
    - A facing read called turned freezes the dot at an older read, which costs ladder ordering (82 → 73%).
    - A missed turn draws the turned read.
  - **With both calls perfect** (truth as the call, no bearing check, the mean held), the gate reaches 0.16, the
    low band's fling, with today's distance intact.
  - **That's the fallback's real price:** a facing call that works on a single utterance. With today's per-read
    call, corrected beats it on fling and on LOCATA, and ties it on the ladders.

## Read length: the whole utterance doesn't help the fling

The whole read runs from 0.13 s to the utterance's close, capped at 6 s.

| | today | corrected (k 1.1) | gated | low 0.1-1.1 kHz |
|---|---|---|---|---|
| **Fling** | 0.32 | 0.22 | 0.27 | 0.13 |
| **Signed** 90 / 135 / 180 | +0.25 / +0.40 / +0.39 | +0.00 / +0.01 / −0.00 | +0.20 / +0.24 / +0.34 | +0.02 / −0.03 / −0.01 |
| **Facing vs facing floor** | 0.21 | 0.33 | 0.32 | 0.41 |
| **Ladder ordering** | 84% | 71% | 80% | 68% |
| **LOCATA all:** within 1.5x / off 2x+ / ordering | 70% / 27 / 67% | 74% / 16 / 68% | 70% / 27 / 67% | 66% / 20 / 74% |

- **Longer reads don't lessen the turn:** today's statistic is thrown just as far (1.83 dB).
- **They do steady the stops:** the facing floor drops 0.26 → 0.21, and LOCATA's within-1.5x rises 67 → 70%.
- **Corrected over the whole utterance** removes the bias exactly, but its k becomes unstable: 0.9-1.65 left out by
  walk, and LOCATA's own k is 0.1. Its stop-to-stop jitter rises to 0.33.
- **The short read stays,** as the Conductor has it.

## Limits

- **Small n:** 29 turned stops at 11 spots in 10 walks, and 4 facing ladders. The facing-vs-facing floor has only 12
  stops (spots with two facing stops).
- **The ladders measure ordering, not size:**
  - **Every candidate draws about a quarter of the called change:** the CDR falls about 5 dB per decade here
    against the law's 20.
  - **So the mean error against the called ratio** is 0.8-0.9 doublings for every candidate, and doesn't separate
    them. Ordering does.
- **The bearing is a stand-in:** GCC-PHAT over 3-8 kHz on each read's first 0.5 s, not the app's GccPhat lock.
  At a spot, 44-100% of reads fall within 5° of the spot's median bearing. A steadier bearing helps only the gate.
- **The onsets:**
  - **Jay's walks:** the Conductor's own ears (`attacks.py`), fed the tape in its 512-sample chunks.
  - **LOCATA:** the animation files' scored events, with bake.py's onsets.
  - **The reads:** `cdr_free_bands`' math, cold-started at each onset. The floored bands match the Conductor's
    `CdrFreeStream` to 1e-15 dB.
- **Outliers:** no read sat 4x or more from its spot's facing centre. On the ladders, 1-3 reads per candidate sat 4x
  or more from the called ratio and were set aside. LOCATA's counts of reads off by 2x+ are in the tables.
- **This slope isn't the earlier one.** Today's statistic falls −5.0 dB per decade on these per-utterance reads,
  against the −2.6 that `facing_vs_distance.py` got from pooled half-second windows. The reads differ: these are
  cold-started at each onset, with no speech mask.

## What CdrRange would need

`src/` is untouched, per the rules. The change would be:

1. **The Conductor hands a fourth band** in `cdrf`: 0.1-1.1 kHz, unfloored, over the same frames.
2. **CdrRange draws:**

   S = mean CDR(B1, B2, B3) + 0.9 × max(0, −1 − (CDR B3 − CDR 0.1-1.1 kHz))

   with u = 10^((S_open − S) / 20), as today. The opener gets the same correction, so a turned opener doesn't skew
   the unit.

## Files

- `harness/rotation/range/reads.py`: the audio → `reads.json`. Every utterance's band powers for both read lengths,
  and its bearing and level. No audio.
- `harness/rotation/range/score.py`: `reads.json` → `numbers.json` (every number here, per stop, per ladder walk
  and per subset) and `scores.txt` (the full tables).
