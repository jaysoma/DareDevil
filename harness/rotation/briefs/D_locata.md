# Brief D: the colour of rotation on LOCATA, with tracked facing

Read `README.md` here first (rules, inputs, what's known). Folders: `harness/rotation/locata/`,
`results/rotation/locata/`. Worktree: `git worktree add ../dd-locata -b rotation-locata`.

## Why
Jay's walks gave one consistent pattern: turning dims the top of the direct sound against the bottom.
- **The pattern:** CDR 4-8 kHz minus CDR 0.1-1.1 kHz reads about 2 dB lower once turned, and lower at 26 of 27 turned
  stops.
- **The shape:** almost all of the drop comes in the first 90 deg, flat to 270 and back by 360. The low band barely
  moves.
- **Where it was measured:** Jay's house, with self-called facings. One fixed threshold, no reference, scores 75%.
- **Reports:** `results/rotation/colour/report.md`, `results/rotation/room_reference.md`,
  `results/rotation/fixed_threshold.txt`.

LOCATA tests it in another room with tracked heads: facing truth to the degree (so 45 deg steps can be seen), real
distances, and a 160 mm pair close to the phone's 157 mm.

## Inputs
- **Tracks:** `results/animation/locata/*.json`, tasks 3 and 4, dev and eval. Each talker every 0.1 s:
  - `facing_deg` (0 = facing the array), `dist_m`, `along_m` and `ahead_m`;
  - `speech` segments;
  - the 160 mm pair's `lateral_deg`.

  `harness/animation/bake.py` shows how they came from LOCATA's own files, and which DICIT mics make the 160 mm pair.
- **Audio:** LOCATA's zips on Jay's disk, or streamed by range request as `bake.py` and `add_words.py` do.
- **Band powers:** `harness/rotation/colour/octave_windows.py` (brief A's octave bands) or `harness/rotation/band_windows.py`,
  at the pair's own spacing. At 160 mm, c/2d is 1.07 kHz: flag the bands below it as ill-conditioned, as brief A did.

## Steps
1. **Stretches, not stops.** LOCATA's talkers walk, so pool over stretches instead:
   - the talker is voice-active, the other talker is not (the other talker is what made batch A's outliers);
   - facing stays within 20 deg of the stretch's mean and the head within 0.3 m;
   - for at least 1.5 s.

   Bin the stretches by unsigned facing (0, 45, 90, 135, 180) and report how many there are per bin, per recording.
2. **The U at 45 deg steps.** Per stretch, compute the pooled octave-band direct, diffuse and total power and the CDR,
   and the contrast. Take each against the same recording's facing stretches (within 30 deg) at a similar distance
   (within 0.5 m). Give the mean, sd and n per facing bin. Is the drop mostly done by 90 deg, as in Jay's walks?
3. **Distance, with real truth.** On facing stretches only, fit the contrast and CdrRange's statistic (the mean CDR over
   1.1-8 kHz) against log10 tracked distance, per recording and over all. Brief 20 measured the range statistic at
   −7.6 dB per decade here. Does the contrast stay flat with distance, unlike in Jay's house?
4. **No reference: one fixed threshold.** Every stretch is read on its own, as Stage 1 must (every utterance is a new
   speaker). Score toward (within 30 deg) against turned (90 deg or more), and fade (120 deg or more) against the rest,
   as balanced accuracy:
   - **Jay's number, unchanged:** the contrast's threshold from his walks (`results/rotation/fixed_threshold.txt`,
     about −1 dB).
   - **LOCATA's own number:** chosen on the other recordings, left out by recording.
   - **The ceiling:** the labelled per-recording reference (the recording's other facing stretches).
5. **Beside Jay's walks:** one table putting LOCATA's numbers next to `results/rotation/fixed_threshold.txt`.

## Report
`results/rotation/locata/report.md` and a numbers JSON. Open, in two sentences, with whether the pattern holds outside
Jay's house and what the 45 deg view adds.
