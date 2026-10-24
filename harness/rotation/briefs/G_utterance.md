# Brief G: how much speech the facing call needs

Read `README.md` here first (rules, inputs, round 1's results). Folders: `harness/rotation/utterance/`,
`results/rotation/utterance/`. Worktree: `git worktree add ../dd-utt -b rotation-utt`.

## The question
Round 1's 75% came from stops of about 7 s of pooled speech. The live app gets one utterance at a time, often 1-3 s,
and in Stage 1 every utterance is a new speaker. How short can the speech be before the fixed facing threshold
(contrast CDR 4-8 minus 0.1-1.1 kHz, about −1 dB; `results/rotation/fixed_threshold.txt`) stops working? And does
pooling the utterances at one held angle buy back what a single one loses?

## Steps
1. **Utterances.** Inside each stop of `harness/rotation/facing_stops.json`, split the speech into utterances. Use the
   decode's segments (`tapes/<walk>/transcript.json`) cut at pauses of 0.3 s or more in the voiced windows, and skip
   each tape's first 2 s.
2. **One utterance alone.** Compute the contrast from that utterance's pooled windows. Classify with the fixed
   threshold, recomputed left out by walk. Give the balanced accuracy, binned by utterance length (under 1 s, 1-2, 2-4,
   4 s and over).
3. **The pooling curve.** Within stops, subsample contiguous speech of 0.5, 1, 2, 4 and 7 s, many draws each. Plot the
   balanced accuracy against seconds pooled, and say where it reaches 70% and 75%.
4. **The Conductor's window.** Score the 0.13-0.5 s read the Conductor commits for range, against the whole utterance.
5. **Pooling at a held angle.** Pool each utterance with the earlier utterances at the same spot and the same facing
   (what holding the angle would group), and score again. Say how many utterances it takes to reach the stop-level 75%.
6. **The continuous turns** (160546, 161331, 020305, from brief A): plot the per-utterance call through each turn.

## Report
`results/rotation/utterance/report.md` and a numbers JSON. Open with how many seconds of speech the call needs, and
whether one utterance is enough, in two sentences.
