# Brief B2: keep the callouts that come after the turn

Read `README.md` here first (rules, inputs). Same folders as brief B: `harness/rotation/blur/`, `results/rotation/blur/`.
Builds on brief B's report (`results/rotation/blur/report.md`, branch `rotation-blur`).

## Why
Brief B dropped each stop's opening callout (its first decode segment, up to 3 s) and found two facing-the-phone stops
at one spot then agree to 1.7 dB rms instead of 3.1. But it also dropped 9 stops whose only speech was the callout.
Jay: **"If I spoke in the past tense, then I had already rotated."** So a past-tense or present-state callout ("Rotated
90 degrees", "I am now facing away", "Facing the phone again", "Now facing the phone") is at the stop's facing and
belongs to the stop. Only a callout said before or during the turn doesn't: future ("I'm going to rotate", "Now I'm
going to rotate another 90") or in progress ("rotating", "turning", "I'm rotating clockwise").

## Steps
1. **Tag every stop's opening callout** in `harness/rotation/facing_stops.json` from the decodes as `after`
   (past tense or present state), `before/during` (future or in progress), or `unclear` (garbled). Write
   `harness/rotation/blur/callout_tense.json` with the walk, the span, the text and the tag. For each `unclear` one,
   list the walk and time for Jay, three at most.
2. **Three rules for a stop's speech:**
   - **all:** the stop as labelled;
   - **dropped:** brief B's rule;
   - **tense:** keep `after` callouts, drop `before/during` ones, set `unclear` aside and count them.
3. **Score under each rule,** brief B's way (left out by walk, AUC first, n always given):
   - the CDR contrast (4-8 minus 0.1-1.1 kHz);
   - CdrRange's range statistic;
   - the onset's own tilt (first 40 ms, 4-8 against 0.25-1 kHz).

   Also give how well two facing-0 stops at one spot agree (dB rms), and how many stops and toward cases survive.
4. **Where the noise came from:** compare the `after` callouts' own values with the rest of their stop, and do the
   same for the `before/during` ones. If the 3.1 → 1.7 dB gain came from the `before/during` callouts alone, say so.

## Report
Add a section "Callout tense (brief B2)" to `results/rotation/blur/report.md`, opening with which rule to use from now
on, in one sentence.
