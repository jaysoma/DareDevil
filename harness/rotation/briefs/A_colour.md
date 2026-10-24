# Brief A: how rotation changes the colour of speech

Read `README.md` here first (rules, inputs, the bar). Folders: `harness/rotation/colour/`, `results/rotation/colour/`.

## The question
Jay: "Let's JUST solve for how rotation changes the colour of speech." Turning lowers the direct sound most in the high
bands, while the room's diffuse sound (the same voice, averaged over every direction) keeps the voice's true colour.
Distance lowers the direct sound evenly across bands. Measure both shapes, per band, and find the contrast that moves
most with facing and least with distance.

## Steps
1. **Sign the labels.** From the decodes, give each stop in `facing_stops.json` a signed facing (0, 45, 90, 135, 180,
   225, 270, 315; clockwise as Jay turns, seen from above). Write `harness/rotation/colour/facing_stops_signed.json`,
   flagging any you can't sign. Batch the doubtful ones for Jay (walk and time).
2. **Octave bands:** 125, 250, 500 Hz, 1, 2 and 4-8 kHz. Per 0.5 s window, the direct, diffuse and total power per
   band, from the estimator (unfloored below 1.1 kHz, flagged). Pool the speech windows of each stop (as
   `facing_pooled.py` does).
3. **The rotation fingerprint:** per band, the direct level, diffuse level, total level and CDR, each against the same
   spot's facing-0 stops, as a curve over signed facing. Per facing, give the mean and spread over spots, and n.
4. **The distance fingerprint:** the same quantities on the ladder walks, as dB per decade of called distance, per band.
5. **The most rotation-specific contrast:** among band pairs (CDR high minus CDR low, direct colour against diffuse
   colour), rank by facing effect over its distance slope and over its pooled noise. Is 4-8 kHz against 0.1-1.1 kHz
   the best, or does another pair do better?
6. **Left against right:** Jay hears 180 → 270 as noticeably louder. Compare 90 and 270 per band. Is the difference in
   the direct sound or in the diffuse/total (the room, e.g. facing a hard surface)? Name the walks and what he faced.
7. **The room as reference,** instead of the opener: per room (living room, kitchen), take every facing-0 stop's value
   of the best contrast as "facing". Classify each other stop as toward (within 45 deg) or turned (90 or more), and
   past 120 deg as "fade", left out by walk. Report balanced accuracy, and how many facing-0 stops it takes before
   the reference settles.
8. **The continuous turns** (160546, 161331, 044350, 171542, 140956, 020305; audio on Jay's box): does the best contrast
   dip once per full turn? Show it as a time series against the decode's "full circle" spans.

## Report
`results/rotation/colour/report.md`, with a numbers JSON and a figure of the rotation and distance fingerprints per
band. Open with the contrast you'd pick and why, in two sentences.
