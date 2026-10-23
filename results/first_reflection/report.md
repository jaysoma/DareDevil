# First reflection: does `Angle2.readSound` find the echo, its angle and its lag? (2026-10-23)

Brief 8. `readSound` cancels the direct sound, then looks for the earliest positive, delayed copy of the voice in what
remains. It had never been scored. It ran unchanged on two datasets:
- **dEchorate:** clean EARS speech through the measured RIRs, 11 wall configurations, 19,008 cuts. The truth is the
  labelled first-order echoes.
- **LOCATA:** batch A's 682 real-talker onsets. The truth is the floor and ceiling echoes computed from the tracked
  heads.

**Short answer: no.** Its reflection is right in angle and lag together about as often as chance, on both datasets.
Its lag sits just past the 1 ms floor of its own window whatever the room, and on real talkers it neither matches the
floor echo nor ranks distance. A floor-echo lag would be a near-perfect range cue in principle, but `readSound`
doesn't measure it.

## What was run
- **The read:** each cut's first sound is found by Angle2's own stream, pushed the way the math host runs it.
  `readSound` is then called at that frame ("`s` at the sound's first frame"). All 19,617 reads where the stream found
  a sound match what it read there itself; on the other 73 (all LOCATA) it found none.
  - That frame sits a median 12 ms after the true onset (5th-95th percentile: -9 to +225 ms). It's on the stream's
    512-sample frame grid.
- **Truth on dEchorate:** as every dEchorate score since brief 3. The direct angle comes from the RIRs' measured
  delay, and each echo's angle is scaled by its pair's fitted factor. An echo's lag is its image path minus the direct
  path at the pair's centre. The south wall never counts as reflective.
- **Hits:** angle within 10 deg; lag within 0.25 ms (12 samples); "both" means one echo passes both tests. Chance is
  another source's read against this cut's echoes, as in `results/dechorate/report.md`.
- **Scoring:** Jay's rule applies to `readSound`'s onset angle. The reflection is scored on decided reads whose onset
  the rule kept. Everything set aside is catalogued in `*_onset_outliers.jsonl`.

## 1. dEchorate

**The onset under the rule:** 834 of 13,464 in-scope reads set aside (6.2%), no scenario dropped. Kept: mean 6.9,
median 4.1 deg, 77% within 10 deg.
- The set-aside kinds: mirror 116, on a reflective echo 102, other 608.
- This is close to `readUtterance`'s onset on the same cuts (`results/clean/report.md`: 8.4 / 5.6 deg before its fix).

**The decided share is about 40% in every configuration,** including all-absorbing 000000 (41%). Deciding doesn't
depend on there being an echo. Undecided reads in scope, by reason:
- "no start out of a quieter moment": 6,406. The frame grid often puts `s` 12-23 ms into the voice, so the 10-30 ms
  reference before it isn't quiet.
- "no clear first arrival": 896.
- "no clean copy found": 695.

**The reflection, 155 mm** (decided reads with the onset kept; hit / chance):

| config | reflective | decided | earliest distinct echo: angle | lag | both | any reflective echo: angle | lag | both |
|---|---|---|---|---|---|---|---|---|
| 000001 | north | 42% | 13% / 12% | 0% / 0% | 0% / 0% | 12% / 7% | 0% / 0% | 0% / 0% |
| 000010 | east | 43% | 16% / 12% | 0% / 3% | 0% / 0% | 13% / 8% | 0% / 0% | 0% / 0% |
| 001000 | west | 41% | 11% / 11% | 1% / 3% | 0% / 0% | 11% / 10% | 0% / 2% | 0% / 0% |
| 010000 | ceiling | 39% | 19% / 14% | 5% / 3% | 0% / 0% | 26% / 14% | 10% / 5% | 4% / 1% |
| 011000 | ceiling, west | 38% | 13% / 14% | 6% / 6% | 1% / 1% | 28% / 27% | 9% / 5% | 3% / 0% |
| 011111 | all but south | 33% | 10% / 12% | 5% / 4% | 0% / 1% | 46% / 51% | 9% / 7% | 1% / 2% |
| **all** | | **40%** | **12% / 13%** | **4% / 3%** | **0.3% / 0.3%** | **25% / 21%** | **6% / 4%** | **1.2% / 0.4%** |

At 65 mm: the earliest distinct echo's angle 14% / 13%, lag 5% / 3%, both 0.4% / 0.4%; any reflective echo, both
1.4% / 0.2%. Every configuration, both spacings and each source are in `tables.md`.

- **Both at once is at chance.** The only consistent "both" hits come from the ceiling, the one strong echo: 4% where
  it's the only reflective surface (chance 1%).
- **With one reflective wall, the lag never matches:** 0-1% in 000001, 000010 and 001000. Most of those walls' echoes
  arrive after 12 ms (next point).

**Echoes outside `readSound`'s window** (`MAX_GAP_MS` kept at 12, per Jay):
- The ceiling's echo is always inside (it arrives 1.5-4.3 ms after the direct sound).
- The north wall's is after 12 ms on 336 of 624 cuts, the east's on 216 of 624, the west's on 192 of 624.
- Where the earliest distinct echo is outside the window (984 of 4,920 cuts at 155 mm), the cut is scored apart, not
  counted as a miss. Every surface and configuration is in `tables.md`.

**What the decided "reflection" actually is:**
- 32% of decided lags sit exactly at the 1 ms floor (`MIN_GAP_MS`), and the median is 1.21-1.28 ms in every
  configuration, all-absorbing 000000 included.
- 31% of the "reflections" point within 10 deg of `readSound`'s own onset.
- So most decided reads find what's left of the direct sound just past the earliest lag allowed, not a wall. That's the
  same pattern brief 3 found in `readUtterance`'s second family (a fixed 3 ms lag, its window length).

**Placing the wall,** from the reads where angle and lag both hit:

| surface | reads | reflection point off the real surface | normal's error | source-to-wall, estimated / true |
|---|---|---|---|---|
| ceiling, 155 mm | 25 | 0.89 m | 87 deg | 0.30 / 0.91 m |
| ceiling, 65 mm | 30 | 0.82 m (better side) | 81 deg | 0.65 / 1.26 m |
| west wall, 155 mm | 1 | 0.17 m (better side; 1.81 m on the front side) | 7 deg | 1.70 / 1.63 m |

- **A ceiling can't be placed by a horizontal pair.** Its image sits straight above the talker, so the lateral angle
  barely changes. The estimate lands in the wrong orientation (about 85 deg off).
- **The one wall hit lands 0.17 m from the west wall,** on the right side of the axis. A pair can't tell which side,
  though: the other side lands 1.8 m off.
- One read isn't evidence. "It came off that wall" can't be tested here, because `readSound` almost never gets both the
  angle and the lag of a wall.

## 2. LOCATA: real talkers
**Onset under the rule:**
- At 160 mm, 41 of 307 reads set aside (mirror 5, other 35, truth was a later direction 1). Kept: mean 7.4, median
  5.4 deg, 80% within 10 deg.
- At 80 mm, 38 of 302 set aside. Kept: 7.7 / 5.5 deg, 75% within 10 deg.
- On 73 of 682 cuts (11%) Angle2's stream found no sound at all. It seeds its floor from the cut's first frame, which
  in LOCATA often already holds the other talker or the room, so the voice never clears it by 10 dB.

**Decided:** 24% at 160 mm, 19% at 80 mm. That leaves 69 and 55 scorable reads.

| pair | decided reads | floor echo: lag hit / chance | angle | both | ceiling: lag hit / chance | lag minus floor lag, median |
|---|---|---|---|---|---|---|
| 160 mm | 69 | 5.8% / 1.4% | 19% | 2.9% (2 reads) | 0% / 0% | -2.6 ms |
| 80 mm | 55 | 0% / 3.6% | 11% | 0% | 1.8% / 0% | -2.2 ms |

- **The floor echo arrives 3.2-5.7 ms after the direct sound** (median 4.5 ms). `readSound`'s lag is a median 2.6 ms
  short of it.
- **Its lags look the same as on dEchorate:** median 1.3 ms, with 23% at the 1 ms floor, and 20% point back at the
  onset's own direction. The floor echo is the strong, early one here, and it's still not what `readSound` finds.
- At 160 mm the floor echo is more than 10 deg from the direct sound on half the reads, so its angle could in principle
  be told apart.

**Range from the echo** (batch A's test: same talker, ordered right at 1.25x / 1.5x / 2x distance; spread within 0.3 m of
one spot against the step at 2x):

| 160 mm | 1.25x | 1.5x | 2x | spread at one spot | step at 2x |
|---|---|---|---|---|---|
| `readSound` gap_ms (decided reads only) | 63% (n=19) | 68% (n=22) | 67% (n=9) | 1.23 ms (n=17) | 0.44 ms |
| CDR, on those same cuts | 47% | 91% | 67% | 1.2 dB | 4.1 dB |
| the true floor lag, on every cut | 100% | 100% | 100% | 0.09 ms | 1.55 ms |
| CDR, on every cut (batch A) | 57% | 62% | 78% | 1.3 dB | 2.5 dB |

- **A geometric range cue exists with two mics, in principle.** The true floor-echo lag orders every pair at all three
  ratios. It runs from about 5.2 ms under 1.5 m to 3.0 ms beyond 3 m, and barely moves at one spot (0.09 ms against a
  1.55 ms step at 2x). Its 100% is partly built in, since the lag is a function of distance and head height; the useful
  number is the precision a reader needs. The median step between talkers 1.25x apart is 0.48 ms, so a reader has to be
  good to about a quarter of a millisecond.
- **`readSound` doesn't deliver it.** At one spot its lag spreads 1.23 ms, three times the step it would need to resolve
  2x, and its ordering rests on 9-22 pairs. At 80 mm it's worse (25% at 2x, n=8).
- **The CDR is still the only working range cue** (78% at 2x on every cut). On `readSound`'s decided subset it's noisy
  too, with as few as 9 pairs.

## What this means
- **`readSound`'s first reflection shouldn't be rendered as a wall echo.** On both datasets its angle and lag together
  are at chance. Its lag is mostly the residue of the direct sound at the 1 ms edge of its window, in an absorbing room
  as much as a reflective one.
- **The echo lag is worth measuring, but not this way.** On real talkers the floor echo is strong and early (3-6 ms), and
  its lag would rank distance almost perfectly. A reader that finds it needs a cancellation that leaves less of the
  direct sound behind, or a search that starts past the residue. That's a new method, outside this brief.
- **Placing a wall** needs both the angle and the lag right first. With a horizontal pair it can only ever work for
  walls, not the floor or ceiling, and it would still have to guess which side of the axis the wall is on.

## Caveats
- **dEchorate's sources are loudspeakers,** which is why LOCATA was added. LOCATA has only 69 decided, kept reads at
  160 mm.
- **LOCATA's echo truth rests on assumptions:** z = 0 is the floor, the ceiling is at 3.0 m (the LOCATA paper's room
  height), and the mouth is 0.12 m below the head marker. Every 5 cm of error in the mouth height moves the floor lag
  by about 0.1 ms, far less than the 2.6 ms gap.
- **`readSound` ran with no Conductor floor (`floor = null`).** Its first frame is on the stream's 512-sample grid, not
  at the true onset, which is what "the sound's first frame" means in the app too.
- **Angle2's defaults weren't changed.**

## Files
- **dEchorate:** `dechorate_summary.json` (all scores, the echo window, the wall placement), `dechorate_reads.jsonl.gz`
  (every read without audio) and `dechorate_onset_{summary,scenarios,outliers}` (the rule's outputs and catalogue).
- **LOCATA:** `locata_summary.json` (lag, chance and range), `locata_reads.jsonl` and
  `locata_onset_{160,80}mm_{summary,scenarios,outliers}`.
- **Tables:** `tables.md`, every table here plus every configuration, spacing and source.
- **Rebuild:** `harness/first_reflection/run_all.sh` (see its README).
