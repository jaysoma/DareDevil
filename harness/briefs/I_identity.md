# Brief I: who is speaking, from short far-field utterances

Read `README.md` here first. Folders: `harness/stage2/identity/`, `results/stage2/identity/`.

## The question
Stage 2 has to say whether an utterance's voice is one already heard in the session. Two questions decide the design:
- **Length:** how much speech does CAM++ (or TitaNet) need at the phone's distances?
- **Facing and distance:** do they move the embedding enough to make one person look like two? Jay's view is that
  CAM++ is "mostly impervious to rotation and changes in room acoustics". Measure how mostly.

## Data
- **LOCATA tasks 3 and 4:**
  - **Audio:** the 160 mm DICIT pair (mics 5 and 10); see `harness/rotation/locata/` for how brief D read it.
  - **Tracks:** facing and distance, from `results/animation/locata/*.json`.
  - **Speakers:** per-talker voice activity.
  - **Identity across recordings:** take it from LOCATA's own metadata only. If its talker names aren't the same
    people across recordings, use same-recording trials and say so.
- **AMI far-field:** one distant mic, many speakers with global participant IDs. It supplies the different-speaker
  trials, and the same-speaker trials across meetings.
- **Jay's walks:** one speaker at many distances and facings, using `harness/rotation/facing_stops.json` and the
  ladders in `harness/rotation/facing_vs_distance.py`, with the callouts removed.
- **Close-talk control:** LOCATA's close-talk mics give the same speech with no room. That's the ceiling.

## Steps
1. **Utterances.** Voice-active spans, cut 0.13 s after the onset to lengths of 0.5, 1, 2 and 4 s (whole utterances
   where shorter). Each talker alone: no other voice within 0.3 s.
2. **Trials:** same-speaker and different-speaker pairs, within a recording and across recordings, with each pair's
   distances and facings recorded.
3. **Verification:**
   - **Measures:** per model, per length, the equal error rate and the miss rate at 1% false accepts.
   - **Bins:** by distance (under 1.5 m, 1.5-3 m, over 3 m) and facing (both within 45 deg, one 90 deg or more), on
     far-field audio and close-talk.
4. **Does facing fake a new speaker?** At the same distance, compare three cosine distributions: same speaker, both
   facing; same speaker, one turned; different speakers. How far does a turn move one person toward "someone else"?
   Do the same for distance (one at under 1.5 m, one at over 3 m).
5. **The running voiceprint.** Simulate a session in order. Each new utterance is scored against the centroid of the
   earlier utterances given to its speaker, so the centroid grows as Stage 2 would build it. Score against the same
   speaker's own centroid and against everyone else's. How many utterances until the centroid is reliable?
6. **What the threshold should be:** one fixed cosine threshold chosen left out by recording, and its error rates per
   length and bin.

## Report
`results/stage2/identity/report.md` and a numbers JSON. Open with the minimum utterance length for identity at the
phone's distances, and whether facing or distance needs its own allowance, in two sentences.
