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
**The tape has no voice in the gaps where held vowels would be, so there is nothing to measure.** Whether Jay was
holding a vowel there is unknown: the walk is a month old, and a decode has no words for a vowel either way. These are
the gaps between the distance calls:

| time (s) | decoded speech (Whisper) | the tape |
|---|---|---|
| 3.6-8.1 | "This is about 2 meters facing the phone right in the center." | speech |
| 8.1-20.4 | — | room floor |
| 20.4-23.2 | "This is about 3 meters facing the phone right in the center." | speech |
| 23.2-42.1 | — | room floor |
| 42.1-47.1 | "This is about 5 meters." / "Basically the phone, right?" / "This is that?" | speech |
| 47.1-63.4 | — | room floor |
| 63.4-74.6 | "In the kitchen now, this is about 7 meters maybe more." / "Basically the phone right dead center." | speech |

The audio itself answers what the decode can't. From 500 Hz to 8 kHz the gaps sit 2-4 dB over the floor, where a
held vowel at 2-7 m would read about 20 dB up. So either he was quiet there, or the capture lost his voice and kept
the room. The tape runs on unbroken (428 s, hum throughout), so if a voice was lost, a dropped link (which would leave
zeros or cut time out) fits less well than something on the phone blanking a steady voice. Listening to 8-20 s would
tell the two apart.

The 36 "held" stretches (76.9 s) that `held_sounds.py` found, and that `library.json`'s `held_voice_s` counts, are
mains hum in those gaps, not the vowels. In all 36, the strongest 50-2000 Hz bin is 60 or 120 Hz, and 27 sit within
2 dB of the tape's 20th-percentile 1.1-8 kHz power. The 6 m facing stops (251-356 s) are talking, with 0-25% overlap,
so they stay in the scoring.

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
- **The held-vowel control needs a fresh tape.** walk-213304 has no voice at 8-20, 23-42 and 47-63 s, and whether
  one was made there is unknown. A walk holding "aaah" at 2 m would show whether the capture keeps a steady voice.

## Callout tense (brief B2)
**From now on, keep the callouts said after the turn, set the bare "Rotate" ones aside, and skip each tape's first
2 s, which hold the handling of the phone, not speech.**

Script: `harness/rotation/blur/tense.py`. Tags: `harness/rotation/blur/callout_tense.json`. Numbers: `tense.txt`,
`tense.json`.

**Every opening callout was said after the turn, or can't be told from the decode.** Of the 46, 40 are past tense
or present state ("Rotated 90 degrees", "I am now facing away", "Facing phone again", "Just rotated"). None is future
or in progress. The other 6 are unclear: five bare "Rotate 90 degrees" (Whisper drops the -d of "Rotated" before
"ninety", so it could be either) and 213304's garbled "Rout 90 degrees".

**The tape-start handling was the larger noise source.** Five tapes (231921, 231705, 171645, 215800, 030615) open with
1-1.5 s of handling: starting the recording, setting the phone down. It reads 11-31 dB over the tape's speech, is
nearly fully coherent (4-8 kHz CDR 10-30 dB), and passes the speech mask. It lands in two facing-0 stops that start
at 0 s: 231705's only one, which is the reference for all four of that spot's turned stops, and 215800's first, which
reads 9.3 dB whole against its partner's 4.0. Brief B's drop rule removed it without meaning to.

The three rules, with each tape's first 2 s skipped:

| rule | measure | stops scored | toward cases | side vs facing 0 | away | AUC | left-out balanced | facing-0 agreement, dB rms | on the 6 toward stops every rule keeps |
|---|---|---|---|---|---|---|---|---|---|
| all | CDR 4-8 minus 0.1-1.1 kHz | 37 | 10 | −1.7 (15/16 below) | −2.7 (9/9) | 0.75 | 71% (6/10, 22/27) | 2.47 | 2.38 |
| dropped | CDR 4-8 minus 0.1-1.1 kHz | 29 | 6 | −1.6 (12/14) | −2.2 (7/7) | 0.75 | 56% (2/6, 18/23) | 1.71 | 1.71 |
| **tense** | CDR 4-8 minus 0.1-1.1 kHz | 37 | 10 | −1.7 (15/16) | −2.7 (9/9) | 0.75 | 71% (6/10, 22/27) | 2.56 | 2.24 |
| all | CdrRange's range statistic | 37 | 10 | −1.8 (16/16) | −2.5 (9/9) | 0.91 | 78% (7/10, 23/27) | 1.13 | 0.90 |
| dropped | CdrRange's range statistic | 29 | 6 | −1.8 (14/14) | −2.3 (7/7) | 0.88 | 68% (4/6, 16/23) | 1.20 | 1.20 |
| **tense** | CdrRange's range statistic | 37 | 10 | −1.7 (16/16) | −2.5 (9/9) | 0.92 | 83% (7/10, 26/27) | 1.07 | 0.77 |
| all | onset's own tilt, first 40 ms | 30 | 10 | −7.0 (12/12) | −8.0 (4/6) | 0.75 | 62% (6/10, 13/20) | 5.69 | 6.00 (8 stops) |
| dropped | onset's own tilt, first 40 ms | 27 | 8 | −5.5 (12/12) | −5.4 (3/5) | 0.74 | 61% (3/8, 16/19) | 5.70 | 5.70 (8) |
| **tense** | onset's own tilt, first 40 ms | 30 | 10 | −6.9 (12/12) | −8.0 (4/6) | 0.75 | 62% (6/10, 13/20) | 5.69 | 6.00 (8) |

The onset tilt keeps brief B's set-aside of 215800's facing-0 pair, and needs 2 onsets a stop, so it scores 30.

- **The tense rule keeps everything the drop rule threw away, at no cost.** It keeps all 37 stops and all 10 toward
  cases, against 29 and 6, and its AUCs match or beat the drop rule's (0.75 and 0.92 against 0.75 and 0.88). With 10
  toward cases instead of 6, its left-out accuracies are the ones to trust (71% and 83%).
- **Where brief B's 3.1 → 1.7 dB came from:** not from callouts said before the turn, since there are none. On the
  six toward stops every rule keeps, agreement goes 3.32 dB (handling and callouts in) → 2.38 (handling out) → 1.71
  (callouts out too). The handling is most of it. The last 0.7 dB is three spots' worth of scatter, not callouts at
  the wrong facing. A callout's CDR contrast differs from the rest of its stop by 1.63 dB rms (22 `after` callouts),
  just as any same-length stretch does (1.52 dB rms, 12 baselines). Its mean offset is +0.03 dB.
- **CdrRange's range statistic was the measure the handling hurt most.** Its facing-0 agreement goes from 5.8 dB rms
  to 1.1 with the first 2 s skipped. It is now the best facing measure here: AUC 0.91-0.92, and 26 of 27 turned stops
  caught under the tense rule.
- **The bar moves:** `results/rotation/facing_pooled.md` scores the stops with the handling in. Without it, the CDR
  contrast reads −1.7 dB to the side and −2.7 away (bar: −2.1 and −3.1), still 15 of 16 and 9 of 9 below. The range
  statistic reads −1.8 and −2.5, not 3.5-4 dB lower. That file is outside this brief's folders, so it is unchanged.
- **Brief B's blur verdict doesn't move:** its scored stops already started after the handling.

## Questions for Jay
1. **Were these said after turning, as "Rotated"?** Whisper's decode, with what follows each:

   | walk | time (s) | callout | next |
   |---|---|---|---|
   | 231921 | 28.6-30.2 | "Rotate 90 degrees." | 31.2: "There are six fresh beers in the fridge." |
   | 171645 | 6.8-13.4 | "Rotate 90 degrees clockwise, same position." | 13.4: "Rotate 90 degrees clockwise, facing away from the phone." |
   | 171645 | 13.4-19.9 | "Rotate 90 degrees clockwise, facing away from the phone." | 19.9: "Rotate 90 degrees clockwise, same position, about two meters." |
   | 171645 | 19.9-30.1 | "Rotate 90 degrees clockwise, same position, about two meters." | 30.1: "Darn it, I just faced the phone just now." |
   | 215800 | 26.3-29.6 | "Rotate clockwise 90 degrees." (the walk's other three say "Rotated") | 29.6: "Same distance now facing the phone." |

   If so, they move to `after`, and the tense rule matches "all" with the handling skipped.
2. **213304, 337.4-341.3 s:** "Rout 90 degrees." / "Down, face of the phone," / "about 5 meters." Was that "Rotated
   90 degrees, now facing the phone", said after the turn?
3. **Two fixes outside this brief's folders:** rerun `facing_pooled.md` with each tape's first 2 s skipped? And make
   `held_sounds.py` reject 60/120 Hz hum before `held_voice_s` is trusted? Its docstring's thresholds also differ
   from its code's.
