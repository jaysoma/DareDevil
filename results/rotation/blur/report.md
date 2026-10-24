# The blur, in time, on Jay's rotation walks (brief B, 2026-10-24)

Scripts: `harness/rotation/blur/envelopes.py` (band envelopes per mic and the pair's direct part, cached from the
audio) and `blur.py` (measures, scoring, control, lag check). Labels: `harness/rotation/facing_stops.json`, less each
stop's opening announcement (below). Numbers: `blur.txt` and `blur.json` beside this file.

## The answer
**Time-domain blur loses to the CDR contrast.** On a single mic, the high-minus-low modulation depth doesn't separate
toward from turned (AUC 0.50, against the CDR's 0.91 on the same stops), and it moves −8.6 dB per decade of distance
against the CDR's −3.0. Onset colour leans the predicted way (−3.1 dB to the side, −5.3 away), but at AUC 0.66 it is
still behind the CDR's 0.81 on its stops.

## The stops: announcements dropped
Jay turns only right before or right after a callout, and never talks while turning. So inside a stop, everything is
at the stop's facing except the opening announcement, which could be at either. Each stop now starts where its
announcement ends: the decode segment over the stop's start, capped at 3 s (a merged segment can run on into the new
facing's talk), plus 0.25 s. That drops 2.7 s from each of the 46 stops on average. Most callouts are past tense
("Rotated 90 degrees", "I am now facing away"), so most were probably already at the new facing; dropping them costs
speech, not accuracy.

The CDR barely notices. Its AUC is 0.75 with or without the announcements (as labelled: −2.1 dB to the side, 15 of
16, and −3.1 away, 9 of 9, as in `facing_pooled.md`; announcements dropped: −1.6, 12 of 14, and −2.2, 7 of 7). Two
facing-0 stops at one spot now agree to 1.7 dB rms instead of 3.1, so the announcements were adding noise to the
reference. Without them, 9 stops have too little speech for the CDR, mostly 125621's, 171645's, 215800's and
122038's short stops, where the repeated callout *was* the speech. That leaves 6 toward cases.

## What held
Every measure is scored the same way. A turned stop (90, 135, 180) is taken against the mean of its spot's facing-0
stops. A facing-0 stop is taken against the spot's other facing-0 stops, so only spots with two of them give a toward
case. Toward against turned uses a threshold, and a sign, chosen on the other walks (left out by walk). The CDR is
scored under the same rule on each measure's own stops, so the comparison is like for like.

| measure | side (90) vs facing 0 | away (180) | AUC | left-out balanced accuracy | CDR on the same stops: AUC | distance slope, dB/decade (sd, walks) | decades of distance that fake a turn |
|---|---|---|---|---|---|---|---|
| **CDR 4-8 minus 0.1-1.1 kHz** (the bar) | −1.6 (12/14 below) | −2.2 (7/7) | 0.75 | 56% (2/6 toward, 18/23 turned) | — | −3.0 (3.7, 4) | 0.6 |
| CDR range statistic | −1.8 (14/14) | −2.3 (7/7) | 0.88 | 68% (4/6, 16/23) | — | −1.5 (3.5, 4) | 1.4 |
| **modulation depth 4-8 minus 0.25-1 kHz**, 2-8 Hz, mean of the mics | −0.3 (5/8) | −1.2 (2/4) | 0.50 | 45% (1/4, 9/14) | 0.91 | −8.6 (5.9, 3) | 0.06 |
| modulation depth 4-8 kHz alone | −1.3 (4/8) | −1.5 (2/4) | 0.64 | 62% (1/4, 14/14) | 0.91 | −6.4 (4.2, 3) | 0.2 |
| the pair's direct 4-8 kHz, modulation depth | −1.5 (4/8) | −1.3 (3/4) | 0.66 | 62% (1/4, 14/14) | 0.91 | −5.6 (3.7, 3) | 0.3 |
| **onset colour**, first 40 ms minus next 300 ms | −3.1 (7/12) | −5.3 (3/5) | 0.66 | 40% (3/8, 8/19) | 0.81 | −0.8 (1.2, 4) | (unstable) |
| onset's own tilt, first 40 ms | −5.5 (12/12) | −5.4 (3/5) | 0.74 | 61% (3/8, 16/19) | 0.81 | −0.2 (5.2, 4) | (unstable) |
| tail's tilt, the 300 ms after (40 ms onset) | −2.4 (10/12) | −0.0 (2/5) | 0.66 | 52% (5/8, 8/19) | 0.81 | +0.7 (4.8, 4) | — |

The toward cases are few (4-8 from two to four spots), so the balanced accuracies swing by 10-20 points on one stop.
The AUC uses no threshold and is the number to compare. "Decades that fake a turn" is the turned stops' mean shift
divided by the distance slope: the CDR's turn is worth 0.6 of a decade of distance, while modulation depth's is worth
0.06. The distance slopes come from the ladder walks, which have no turns and aren't trimmed.

- **Why modulation depth fails here: the room's floor fills the dips, not the reverb.** Inside speech runs, the
  envelope's lowest 10% sits only 2.6 dB above the room floor at 4-8 kHz, and 3.9 dB above it at 0.25-1 kHz,
  averaged over 28 stops. The dips already reach the floor. So the measure tracks how far the syllable peaks rise
  over the floor, which is a signal-to-noise reading, and that is why it falls 8.6 dB per decade with distance. The
  dips' height over the floor doesn't move with facing (AUC 0.43).
- **Turning takes the onset's high band, but no faster than a level tilt would.** The onset's own 4-8 / 0.25-1 kHz
  tilt reads below facing at all 12 side stops (−5.5 dB), and the tail's at 10 of 12 (−2.4 dB). The 3 dB between them
  is the brief's mechanism, and it is there on average. But two facing-0 stops at one spot differ by 6-9 dB (rms) in
  onset colour, against 1.7 dB for the CDR. Colour's distance slope also flips sign with the onset window (−3.2,
  −0.8, +3.0 dB per decade at 30, 40, 50 ms), so it can't be read.
- **The nearest single-mic number is the onset's own tilt, and it isn't blur.** At 40-50 ms it gives AUC 0.74-0.78,
  against the CDR's 0.81 on the same stops. It is a level tilt taken where the direct sound leads, and it was the best
  of about 30 rows tried.
- **The pair's direct part adds nothing at the syllable rate.** The CDR's direct fraction comes from PSDs with about
  130 ms of memory, so it can only follow the envelope below about 1.2 Hz. Between 2 and 8 Hz, the direct part's
  modulation is just the power's (AUC 0.66, against 0.64 for the 4-8 kHz band alone).
- **Neither mic is better** (AUC 0.55 and 0.50; slopes −9.2 and −8.0 dB per decade). The capsule order is unmarked
  for 9 of the 11 walks, so the channels can't be named top and bottom.
- **The speech mask isn't the problem.** Taken over the whole stop, pauses and all (the way a room's modulation
  transfer is read off running speech), modulation depth does no better: AUC 0.50.
- **Before the announcements were dropped,** the verdict was the same: modulation depth reached AUC 0.62 against the
  CDR's 0.72, and onset colour 0.57 against 0.77.

## The lag check (231705 at 2 m, 231921 at 5 m, "there are six fresh beers in the fridge")
The phrases are never spoken while turning, so nothing here comes from a turn in progress.

**As briefed, the envelope cross-correlation has no lag to read.** In all 39 phrases, the peak of the 4-8 kHz dB
envelope against the 0.25-1 kHz one lands at the edge of the search (100 ms). Over a whole phrase, the correlation
follows the word's own order (the high band's /s/ and /ʃ/ fall between the vowels), not the room. The peak height
(0.13-0.26) doesn't move with facing either. On that framing, Jay's doubt holds.

Correlating where each band's envelope rises (its onset strength) does give a peak inside the search:

| walk | facing | phrases | lag, ms (sd); − = high band first | peak r (sd) |
|---|---|---|---|---|
| 231705 | 0 | 3 | −9.0 (5.2) | 0.14 (0.03) |
| 231705 | 90 / 135 / 180 | 9 / 3 / 4 | −21.1 (10.2) / −22.2 (9.3) / −18.3 (12.2) | 0.12 / 0.10 / 0.06 |
| 231921 | 0 | 6 | −7.2 (31.6) | 0.07 (0.01) |
| 231921 | 90 / 135 / 180 | 6 / 3 / 5 | −28.9 (14.0) / −24.9 (10.8) / −20.5 (24.1) | 0.08 / 0.06 / 0.07 |

Facing the phone, the high band's rise leads the low band's by 7-9 ms. Turned, it leads by 18-29 ms, in both walks:
a turned phrase reads below a toward one with probability 0.79 (231705: 16 turned, 3 toward) and 0.65 (231921: 14
turned, 6 toward). The peak height drops with turning at 2 m (0.79) but not at 5 m (0.40). One reading is that once
the direct high band weakens, the vowels' own high-band rise sinks under the floor, and the fricatives' earlier rise
is what's left. That is a shift in which onsets count, not a delay in the room. It rests on nine toward phrases, so
it is a lead, not a cue.

## The held-vowel control, walk-213304
**There are no held vowels on this tape to measure.** The 36 "held" stretches (76.9 s) that `held_sounds.py` found,
and that `library.json` labels this walk by, are mains hum. In all 36, the strongest 50-2000 Hz bin is 60 or
120 Hz, and 27 of them sit within 2 dB of the tape's 20th-percentile 1.1-8 kHz power, between the callouts. The
0-78 s ladder span is silent between the distance calls (2-4 dB over the floor above 500 Hz), and only 3% of its
voiced windows overlap a "held" stretch. The 6 m facing stops (251-356 s) are talking, with 0-25% overlap.

What the hum shows instead is what a sound without syllable dips reads:

| octave | modulation depth, hum stretches | talking, same tape | quiet | dips over the floor: talking |
|---|---|---|---|---|
| 250 Hz | −4.9 dB | +2.9 | −3.9 | +2.4 dB |
| 1 kHz | −7.6 | +4.8 | −11.0 | +2.1 |
| 4 kHz | −3.7 | +5.0 | −18.9 | +2.0 |
| 8 kHz | −0.0 | +9.4 | −8.5 | +3.5 |

**Modulation depth can't be used on a held vowel.** A steady sound with nothing to dip reads 8-13 dB below talking,
so a turn would have to be read inside a steady sound's own wobble. Jay's note that vowels never dip below the room
floor fits what talking shows here: even talking dips only 2-3.5 dB above the floor on this tape.

## Limits
- **Set aside** (`SET_ASIDE` in `blur.py`): run-based measures on 4 stops that read 11-21 dB off their spot.
  These are 122038's two turned stops (2-2.5 s of speech) and 213304's 90 and 180 stops, both against a single 2.5 s
  facing-0 reference. Onset measures on 215800's facing-0 pair (1.5 s each), whose onset tilts are 34 dB apart. The
  means above are of the rest. Run-based measures also need 2 s of speech in runs, which 14 stops lack once the
  announcements are dropped. Onset measures need 2 onsets, which 12 lack.
- **The onset detector was loosened:** an onset rises after 80 ms below the floor plus 35% of the tape's range. With
  150 ms and 25%, 171645, 215800 and 213304 had under one onset per stop.
- **Distance slopes for run-based measures come from 3 walks.** 221126's ladder steps each hold a single 1 s run
  of speech, under the 2 s cut. The slopes spread 4-6 dB per decade from walk to walk.
- **About 30 measure-and-window rows were tried,** so the best single row is flattered. The rows named in the brief
  (modulation depth hi−lo, onset colour) are the ones to judge by.
- **The direct-part estimator reads 1.9 dB higher than `band_windows.json`'s 4-8 kHz CDR** (sd 0.5, 15 stops),
  because it weights the direct fraction by instantaneous power rather than smoothed. A constant offset leaves a
  modulation depth unchanged.
- Same walks, room and self-called facings as the bar.

## Questions for Jay
1. **walk-213304, 0-78 s and the 6 m stops (251-356 s):** did you hold vowels on this walk? The tape has only
   callouts there, and the 77 s that `held_sounds.py` counted is 60/120 Hz hum. If the held vowels are on another
   tape, which one? That is where the control can be run.
2. **`held_sounds.py` takes mains hum for a held vowel** (and its docstring's thresholds differ from its code's).
   Should it reject 60/120 Hz and require the 1.1-8 kHz power over the floor before `held_voice_s` is trusted? That is
   outside this brief's folders, so it's untouched.
