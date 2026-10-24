# Brief K: same speaker or new? Joining angle, range and voice

Read `README.md` here first. Folders: `harness/stage2/handover/`, `results/stage2/handover/`.

## The question
In Stage 2 each new utterance either belongs to a speaker already in the session or starts a new one. The app has
three things to decide with: where it comes from (GccPhat's angle), how far (CdrRange's units) and what it sounds like
(CAM++). The same place doesn't mean the same speaker, and people walk, so no single cue can be trusted alone. Find
the rule from data.

## Data
- **LOCATA task 4** (two moving talkers, tracked, per-talker voice activity) and **task 3** (one moving talker).
  160 mm pair.
- **AMI meetings** (four seated people, many sessions): angle from two mics of the far-field circular array,
  - **The pair:** opposite mics, about 200 mm; give `GccPhat` the true spacing.
  - **Voice:** the same array mic.
  - **Labels:** speaker segments from AMI's annotations.
- **Jay's walks** with more than one talker, if `library.json` lists any, using decodes and the walks' truth files.
  If none have per-utterance speaker truth, skip them and say so.

## Steps
1. **Per utterance,** taken as the app takes it:
   - **Angle:** GccPhat's lock at 0.5 s, plus whether it committed (brief 11's dim rule).
   - **Range:** CdrRange's read at 0.5 s.
   - **Voice:** a CAM++ embedding of the first 2 s, or the whole utterance if shorter. Brief I runs beside this one,
     so use your own embeddings.
   - **Time:** the gap since each known speaker's last utterance.
2. **Per (utterance, known speaker) pair, the features:**
   - the angle difference from that speaker's last committed angle
   - the log range ratio
   - the cosine to that speaker's running centroid
   - the time gap

   The label is same or different, from the truth.
3. **Rules, left out by recording:**
   - each cue alone (a threshold);
   - angle and voice;
   - all four (a logistic regression).

   Give the accuracy, how often one person is split into two (a false new speaker) and how often two are merged into
   one, for each.
4. **Where each cue fails:**
   - when a talker walks (the angle moves, the voice stays);
   - when two talkers stand near the same angle (the angle agrees, the voice doesn't);
   - for short utterances (the voice is unreliable).

   Name recordings and times.
5. **A decision rule Jay can read:** thresholds, in plain words, with their error rates.

## Report
`results/stage2/handover/report.md` and a numbers JSON. Open with the rule you'd ship and its split and merge rates, in
two sentences.
