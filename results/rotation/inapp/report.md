# Brief H: the facing call and the range correction, in the app (Jay's option b)

**k = 1.1, and it's built: Conductor v14 hands a fourth CDR band and runs to 2 s, and CdrRange draws at 0.5 s, calls
facing at 2 s and corrects a turned range once.** The gate passes, but only just. Left out by walk, option b cuts a
turned talker's throw from 0.33 to 0.31 doublings (0.28 in-sample at k 1.1) and costs 0.7 points of ladder ordering. Brief
E's same-half-second correction got 0.19 for 10 points. The gain is small because only 143 of 559 utterances reach their
2 s frame. The regression is clean: today's range is reproduced to 0.001 dB on all 559 utterances, and every one of the
143 facing calls matches.

## Step 1: k for option b

The range statistic is read over 0.13-0.5 s, as today. When the utterance's 2 s frame is handed, the contrast over
0.13-2.0 s (CDR 4-8 kHz minus unfloored CDR 0.1-1.1 kHz) calls it, and a turned call adds k × (−1 dB − contrast). The
utterances are brief E's (the Conductor's ears on Jay's walks, the scored events on LOCATA), and the scores are brief
E's own functions run on them. Brief E's short read is reproduced exactly: 899 reads, 0 dB apart.

| | today | E, half second (k 0.9) | **option b, k left out** | option b, k 1.1 (in-sample) |
|---|---|---|---|---|
| **Fling:** mean \|log2\| over 29 turned stops, doublings | 0.327 | 0.187 | **0.314** | 0.279 |
| **Signed** at 90 / 135 / 180° (+ = drawn farther) | +0.26 / +0.38 / +0.39 | +0.08 / +0.08 / +0.09 | +0.19 / +0.35 / +0.19 | +0.20 / +0.35 / +0.24 |
| **Turned stops closer than today** | – | 23 of 29 | 15 of 29 (10 tied) | – |
| **Facing vs facing floor** (12 stops) | 0.255 | 0.249 | 0.289 | 0.275 |
| **Ladders:** read pairs ≥1.5x apart in order (568) | 82.0% | 71.7% | **81.3%** | 81.3% |
| **LOCATA, all reads (206):** within 1.5x / mean err / off 2x+ / ordering | 67% / 0.36 / 25 / 77% | 69% / 0.37 / 18 / 81% | 68% / 0.35 / 23 / 76% | 68% / 0.35 / 23 / 76% |
| **LOCATA, facing ≤45° (71)** | 86% / 0.31 / 2 / 79% | 87% / 0.30 / 1 / 83% | 87% / 0.29 / 2 / 79% | 87% / 0.29 / 2 / 79% |
| **LOCATA, turned ≥90° (73)** | 45% / 0.43 / 19 / 63% | 51% / 0.42 / 13 / 54% | 47% / 0.43 / 17 / 61% | 47% / 0.43 / 17 / 61% |

LOCATA's columns for option b use k fitted on all of Jay's walks (1.1), as brief E did.

### What held
1. **The gate passes.** k left out beats today on the fling (0.314 against 0.327), at 0.7 points of ladder ordering,
   inside the 5 allowed. On all walks, every k from 0.1 to 2.0 beats today, and none loses more than 0.8 points.
2. **The 2 s call is right about three times in four.**
   - **Jay's walks:** 76% balanced (16 of 22 facing reads called facing, 23 of 29 turned called turned).
   - **LOCATA:** 68% (23 of 33, 19 of 29).
   - **Brief G** got 75% on 2-4 s utterances.
3. **It costs almost no distance.** It corrects only utterances that run to 2 s and are called turned, so far fewer
   facing reads are wrongly "corrected" than in brief E's half-second version.
   - **Ladders:** 82.0 → 81.3%, against E's 72%. Two walks lose: 221126 84 → 74 and 224302 70 → 65. The other two are
     unchanged.
   - **LOCATA:** about even (68% within 1.5x against 67%, 23 off by 2x+ against 25).
4. **Where it does reach, it corrects.**
   - **At 180°:** 10 of the 42 reads in stops at 180° run to 2 s, and all 10 are called turned. Their stops' throw
     falls from +0.39 to +0.19 doublings.
   - **At 135°:** 1 of 13 reads reaches 2 s, so it barely moves (+0.38 → +0.35).

### Why the gain is small
- **Coverage.** On Jay's walks, 143 of 559 utterances (26%) reach the 2 s frame, and 70 of those are called turned.
  - **In the turned stops:** 29 of 154 reads reach it.
  - **The rest are drawn as today**, so 10 of the 29 turned stops don't move at all.
  - **LOCATA:** 84 of 340.
- **k is poorly pinned.** The fling is flat in k from 0.8 to 1.5 (0.279-0.282 in-sample), so leaving one walk out
  swings k from 0.8 to 2.0.
  - **The swing is outliers, not the turn:**
    - **walk-221126's opener at 6.7 s** ("One meter from the phone", facing) reads a contrast of −11.1 dB. The next
      most extreme of the 227 calls is −6.3.
    - **43 of the 227 calls** sit below −3 dB.
  - **Capping the correction steadies it** (a diagnostic only; nothing is capped in `src/`):

    | cap | fling, k left out | k left out | ladders |
    |---|---|---|---|
    | none (shipped) | 0.314 | 0.8-2.0 | 81.3% |
    | 3.0 dB | 0.270 | 1.4-2.0 | 81.2% |
    | 2.5 dB | 0.275 | 1.35-2.0 | 81.2% |
    | 2.0 dB | 0.281 | 1.05-2.0 | 81.3% |

### The brief's literal rule does worse
"Utterances of 2 s or more" can mean two things.
- **Handed (what v14 does, and what's fitted above).** The Conductor hands the 2 s frame, because the ears haven't
  closed the utterance yet.
- **Speech2.** The utterance's backdated close is 2 s or more after its onset.

They differ because the ears close an utterance about 1 s after its speech stops, and the frames run until then.
- **Calls:** 76 utterances pass the speech2 rule against 143 handed. So 67 of v14's calls come from utterances with
  1-2 s of speech and the rest quiet.
- **Why the quiet doesn't matter much:** quiet frames weigh little in a sum of powers.
- **Under speech2 the call scores worse here:** 61% balanced on 24 stop reads, against 76% on 51.
- **Its k fails left out:** 0.339 against today's 0.327. In-sample it's 0.307.
- **Small n,** but nothing here argues for waiting on the backdated close, which would also put the call a second
  later.

## Step 2-3: what changed in `src/`

- **`geonar/cdr_direct.py`:** `CdrFreeStream` takes `unfloored` bands, masked from their own low edge and returned
  after the floored ones. It defaults to none, so every existing caller is unchanged.
- **`geonar/conductor.py`, VERSION 14:**
  - **The fourth band:** `cdrf` carries 0.1-1.1 kHz unfloored (`FACING_LOW_HZ`) as values 7-8. The first six are the
    three range bands, as before.
  - **Longer frames:** they run until their window ends `FACING_READ_S = 2.0` s after the onset. `RANGE_READ_S = 0.5`
    stays, documented as the span CdrRange commits its range from.
  - **The opener:**
    - **No frames while provisional.** No CDR frames are handed while the session's first utterance has no onset yet.
    - **A cold start at the onset.** When the gate names that onset, the CDR restarts cold there.
    - **Before,** the opener's instrument ran warm from sample 0, and MathPass cut its frames at the onset.
    - **Why:** CdrRange now times both reads from an utterance's first frame, and the opener sets the unit. This is also
      what the Conductor's own 10-10 note says ("the instrument now starts cold AT the onset"), and how briefs E and G
      read every utterance.
- **`schemes/CdrRange.js`** (documented at the new constants, `RANGE_READ_S` and the block above it):
  - **Timing:** a frame's hop is `FIRST_HOP` (13) plus its hops after the utterance's first frame.
  - **The range** sums only hops 13-42 (the frames ending by 0.5 s) and draws on hop 42, with the same statistic.
  - **The facing call** sums CDR 4-8 kHz and 0.1-1.1 kHz over hops 13-183 and calls on hop 183. A turned call adds
    `FACING_K` × (−1 − contrast), once. Later redraws keep the correction, and a facing call adds nothing.
  - **The opener** is corrected the same way, so it stays 1.000 u.
  - **The fields:** `facing(f)` returns `"facing"`, `"turned"` or `null` (before 2 s, or for an utterance that closed
    first), held until the next utterance. `facingContrast(f)` gives the dB.
  - **Frame length:** `cdrf` of 6 or more values is read (it was exactly 6).
  - **The constants:** `FACING_K = 1.1`, `FACING_THR_DB = −1`, `FACING_READ_S = 2`, and `SR`/`HOP`/`NFFT`/`FIRST_HOP`,
    the Conductor's.
- **`render/README.md`:** the facing field, the second dot move, and the fade. A turned talker is drawn faded. Jay's
  line is 120°, but the cue can't tell 120 from 90, so it fades past about side-on.

## Step 4: the regression

`harness/rotation/inapp/regress.py` plays src's Conductor before brief H (v13, commit 16f18f4) and now (v14) over
Jay's 11 walks, and `regress.mjs` reads each stream with CdrRange, before and now, the way MathPass does. MathPass holds
frames until the onset is confirmed, cuts them at it, and stamps onset_idx and the bearing. The results are in
`regression.txt` and `regression.json`.

### Unchanged
- **The frames:** 0 of 21,060 frames v13 hands differ from v14's first six values, the openers aside.
- **The range at 0.5 s:** for all 559 utterances brief E scored, the drawn statistic is brief E's "today" to within
  0.0008 dB.
- **The held dot:** it is option b's statistic in the tape's unit to within 0.002 dB.
- **Utterances under 2 s or called facing:** none of them moves after its 0.5 s draw.
- **The facing calls:** 143 made, 143 expected, 0 mismatches in presence or verdict. The contrast matches Python to
  0.002 dB.

### Changed, and why
1. **The opener's frames:** all 621 differ, because v14 starts the opener's CDR cold at its onset (above). This shifts
   every tape's unit: the one change to "today" made on purpose.
2. **When CdrRange draws: 0.49 s after the onset (hop 42), from the 30 frames ending by 0.5 s.**
   - **Before,** its first step came 0.5 s after its first frame (0.68 s after the onset), from everything summed.
   - **A latent bug in v13 as committed.** v13's frames end 0.31 s after the first frame, so that step never came:
     the old CdrRange on a v13 stream drew **no range on any of 722 utterances**. MathPass would have drawn every dot at
     its 1 u placeholder.
   - **Live is unaffected.** The live stack is still Dictate's v12, which hands every frame, so this never shipped.
3. **The old CdrRange can't read a v14 stream.** It requires `cdrf.length === 6`, so it ignores 8-value frames and
   draws nothing.
   - **The values are kept,** as the brief asked: the first six are unchanged.
   - **But the old reader is not.** Conductor v14 and the new CdrRange must ship together.
4. **Turned utterances:** they move a second time, at 2 s (70 of 559 on Jay's walks).
5. **The new CdrRange on a v12 stream** (what's live) would read the 0.5 s read, not v12's running window, and never
   call facing: there's no fourth band.

### Tests
- **`test_cdrrange.mjs`:** `fixture.json`, four utterances of walk-224302's v14 stream (built by `make_fixture.py`).
  - **The utterances:** the opener (called facing), one under 2 s, one called facing, one called turned.
  - **The expected values** are worked out in Python from `reads.json`, not from CdrRange.
  - **It checks:**
    - the 0.5 s statistic, the call, the contrast and the correction;
    - the number of moves and the hop each happens on (42, and 183 if turned);
    - u at each.
  - **And two variants:** the turned utterance cut at 1.99 s (no call, one draw), and the stream stripped to v13's
    6 values and 0.5 s (same range, no call).
  - **Result:** 37 checks pass.
- **`test_conductor.py`:** v14 on a synthetic 8 s tape, two coherent bursts in hiss. It checks:
  - no frames while provisional;
  - 8 values per frame;
  - hops 13-183 (171 frames) on the 3 s burst;
  - the 0.6 s burst closing before its 2 s frame;
  - all 8 values against brief E's estimator run cold from the onset (5e-5 dB).
  - **Result:** all pass.

## Limits
- **Not deployed.** `src/` here is the staging copy. Dictate runs Conductor v12, and Voice runs its own CdrRange.js
  (which also still sets the slope from the opener, a difference that predates this brief). Nothing outside this repo
  changed.
- **Render won't fade anyone yet.** Render already dims a timeline entry with `turned: true`, but Voice's MathPass.mjs
  never sets it, and it doesn't call `facing()`. That one line is in Voice.
- **The regression reads CdrRange the way MathPass does,** not through MathPass itself. MathPass's own gate on showing
  a range (only when the bearing moved over 5° from the last lock) is outside it.
- **Pooling isn't fully off.** CdrRange joins a pool when |bearing − pool's| ≤ `POOL_DEG`, and `POOL_DEG = 0` still
  passes two equal bearings. The regression driver first stamped every utterance at 0° and pooled them all; it now
  stamps distinct bearings. Real bearings rarely tie exactly. Not touched.
- **160 extra draws.** The app also draws 160 utterances brief E never scored, on Jay's walks. Their speech closes
  before 0.5 s, but the ears' close comes a second later, so the 0.5 s frame is handed. That was true of v13 too.
- **Small n:** 29 turned stops, 51 facing calls inside stops, 4 ladders.
- **LOCATA's utterances** close at the next scored event or the end of the talker's speech, not at the ears' close, so
  its 84 calls aren't exactly the ones the app would make there.

## Questions for Jay
1. **Cap the correction?** I'd cap it at 2.5 dB, the largest turn shift round 1 measured (away: 2.5 dB).
   - **The risk without one:** on walk-221126 the opener at 6.7 s ("One meter from the phone", facing) reads −11.1 dB.
     It is corrected by 11.1 dB, which would draw that whole tape 3.6x farther.
   - **What it buys:** left out, the fling falls 0.314 → 0.275 at the same ladder ordering, and k steadies (1.35-2.0).
     The k fitted with the cap is 1.85, so the cap and k go together.
   - **Not built,** pending your go.
2. **Wire it up and deploy?** That means MathPass writing `turned` from `range.facing()`, then Conductor v14 into
   Dictate and CdrRange into Voice/RangeMath, together, since the old CdrRange reads nothing from v14.

## Files
- **`harness/rotation/inapp/reads.py`:** audio → `reads.json`. Brief E's reads plus the 0.13-2.0 s facing read, with
  each utterance's handed / speech2 flags. No audio.
- **`harness/rotation/inapp/score.py`:** `reads.json` → `numbers.json` and `scores.txt`: the fit, every score, the k
  sweeps and the capped diagnostic.
- **`harness/rotation/inapp/regress.py` and `regress.mjs`:** → `regression.json` and `regression.txt`. The streams go to
  a work folder outside the repo.
- **`harness/rotation/inapp/make_fixture.py`, `fixture.json`, `test_cdrrange.mjs`, `test_conductor.py`:** the tests.
