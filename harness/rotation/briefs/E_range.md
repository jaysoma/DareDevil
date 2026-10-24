# Brief E: a range that turning doesn't throw off

Read `README.md` here first (rules, inputs, round 1's results). Folders: `harness/rotation/range/`,
`results/rotation/range/`. Worktree: `git worktree add ../dd-range -b rotation-range`.

## The goal
Jay: "If we can't [read the shape of rotation], then just having rotation NOT throw off range is enough." Today a turn
lowers CdrRange's statistic by 1.8-2.5 dB, so a turned talker is drawn 1.2-1.3x farther. Find the range read that
moves least when the talker turns, without losing what it knows about distance.

## Today's range, the bar
- **CdrRange** (`src/schemes/CdrRange.js`): the mean over 1.1-2, 2-4 and 4-8 kHz of the direction-free CDR. It's
  read once per utterance, from the Conductor's frames between 0.13 and 0.5 s after the onset (`RANGE_READ_S`), then
  held.
- **Units:** relative to the opener at −20 dB per decade, u = 10^((CDR_open − CDR)/20).
- **What brief 20 found** (`results/range_facing/report.md`):
  - On LOCATA's 160 mm pair: 69% within 1.5x of the true distance ratio.
  - The low band below 1.1 kHz is ill-conditioned at the phone's spacing.
  - A high-minus-low correction "doesn't earn its keep" per half-second read.

## Candidates (score every one the same way)
1. **The low band alone.** Brief A found the CDR below 1 kHz barely moves with facing (500 Hz: −0.8 to +0.5 dB). Use
   0.1-1.1 kHz or 125-500 Hz, unfloored and flagged ill-conditioned. Does it still carry distance?
2. **Bands weighted by how little facing moves them,** against how much distance does.
3. **Corrected:** the range statistic plus k times how far the facing contrast (CDR 4-8 minus 0.1-1.1 kHz) sits below
   the fixed facing threshold (about −1 dB). Fit k left out by walk; k = 0 is today's range.
4. **Gated:** when the fixed threshold says turned, keep the last facing read at the same angle (within 5 deg) and
   don't update. If there's no earlier facing read, draw the turned read but mark it.
5. **Today's CdrRange**, unchanged.

## Scoring
- **Rotation's fling, on Jay's walks:**
  - **The data:** at each spot in `harness/rotation/facing_stops.json`, the range drawn for turned stops against
    the spot's facing stops, as a ratio. The goal is 1.0.
  - **What to give:** the mean of |log2 ratio| (in doublings) over turned stops, after setting obvious outliers
    aside and counting them.
- **Distance, on Jay's ladders:** `LADDERS` in `harness/rotation/facing_vs_distance.py`, all facing, with called
  distances. Give each read's ratio to the ladder's first step against the called ratio, plus ordering.
- **Distance and turning together, on LOCATA:** tracked distance and facing (`results/animation/locata/*.json`,
  audio on Jay's box). Use brief 20's scoring: error in doublings against the true ratio to the opener, share within
  1.5x, and ordering. Score all reads, facing reads only, and turned reads only.
- **Two read lengths:** the Conductor's 0.13-0.5 s read, and the whole utterance.

## Report
`results/rotation/range/report.md` and a numbers JSON. Open with the candidate you'd put in CdrRange, in two
sentences. Give its fling and its distance score beside today's. If nothing beats "gated", say so: Jay's fallback is
that rotation simply mustn't move the dot.
