# Brief N: blur at scale (Stage 3)

Read `README.md` here first (rules). Folders: `harness/stage3/blur/`, `results/stage3/blur/`. Worktree:
`git worktree add ../dd-blur3 -b stage3-blur`. Start with `results/stage3/blur.md` and
`harness/rotation/decode_blur/phonemes.py`, which is the method to scale up.

## The question
Is blur, meaning how much a decoder with no language model mishears speech and how unsure it is, a repeatable reading
of which way a talker faces? And can it be told apart from distance? Jay's model: range = dB, rotation = blur.
- **The rule:** no Whisper, and no decoder with a language model, for any blur measure. Android's results may be
  reported beside them as the "brain that fills in".

## Decoders
- **Main:** wav2vec2's phoneme recogniser, `facebook/wav2vec2-lv-60-espeak-cv-ft` (greedy CTC, IPA).
- **Second, to show the effect isn't one model's:** `facebook/wav2vec2-xlsr-53-espeak-cv-ft`, and Allosaurus if it
  installs.
- **Input:** one mic (channel 0), so the pair's sum can't comb-filter the highs; 16 kHz; fixed gain, no AGC.

## Measures, per take
- **Blur:** the mean entropy (bits) of the per-frame phoneme odds over speech frames. No reference needed.
- **Errors:** the phoneme error rate against a reference: the known text where there is one, and on LOCATA the same
  decoder's output on the close-talk mic.
  - **On LOCATA, "blur added by the trip":** far-field minus close-talk, for both blur and errors. That removes the
    talker and the words.
- **Survival by sound class:** weak fricatives (f, th, v), strong ones (s, sh, z), stops, nasals and vowels: the
  share heard right.

## Data
1. **Jay's rotation walks:**
   - **Stops:** every stop in `harness/rotation/facing_stops.json`, signed with brief A's
     `harness/rotation/colour/facing_stops_signed.json`.
   - **Phrase takes:** from Android's logs where they exist (`tapes/<walk>/recognizer.json`), otherwise from the
     decode's segments.
   - **Continuous turns:** 160546, 161331 and 020305 (audio on Jay's box).
2. **Matrix sentences,** if Jay has recorded them: 10 random five-word sentences, each slot from a closed set of 10
   words, at 0/45/90/135/180/270 deg, at 2 m and 5 m. Use them as the headline test, since there's nothing to guess.
3. **LOCATA tasks 3 and 4** (on Jay's box):
   - **Audio:** the 160 mm DICIT pair, one mic.
   - **Truth:** tracked facing and distance, from `results/animation/locata/`.
   - **Utterances:** a talker alone, no other talker within 0.3 s.
   - **Reference:** the close-talk mic.

## How to sort the data (Jay's condition: no flattening)
Pooling everything into one median has flattened every effect this project has chased. Rooms differ: near a wall, in
a lively room or in a carpeted "sound-sink" room, blur won't divide the same way.
- **Compare within, then count across.** Every facing effect is first taken inside one recording at one spot: turned
  takes against that spot's own facing takes. The headline is then how many recordings show blur rising from facing
  to turned, with the size of the rise in each. Never one pooled number across rooms.
- **Strata, reported separately:**
  - **Room:** kitchen, living room, bedroom office (carpeted), LOCATA's lab.
  - **Distance band:** under 1.5 m, 1.5-3 m, over 3 m.
  - **Distance to the nearest wall,** where the layout is known: `truth_inputs/landmarks.json` and `poses.json` for
    Jay's house, the room geometry for LOCATA.
- **The ones that don't fit:** recordings or spots that go the other way are set aside and studied separately, never
  averaged in. Name them, and say what's different about them (room, wall, distance, level). They may be the finding.
- **Means of what's kept, with n,** after obvious outliers are set aside and counted. No medians as headlines.

## Steps
1. **The facing curve:** blur and errors against facing (45 deg bins), at fixed distance bands. Give the mean, spread
   and n per bin, and the order test: is it monotonic from 0 to 180? Use a permutation test within recording.
2. **The distance curve:** facing within 30 deg only, blur against log distance.
3. **Two factors:** fit blur on facing and log distance together, left out by recording. How much does each explain?
4. **Jay's model, tried:**
   - **Facing:** call it from blur alone (toward against turned), left out by recording, beside the CDR contrast's
     75-81%.
   - **Range:** then call it from level (dB) corrected for that facing call, beside CdrRange's scores
     (`results/rotation/range/report.md`).
5. **Where it breaks:** recordings, times and talkers where blur and facing disagree.

## Report
`results/stage3/blur/report.md` and a numbers JSON. Open with whether blur reads facing at scale, and whether it can
be told apart from distance, in two sentences. Keep every untested explanation labelled as such.
