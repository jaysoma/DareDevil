# Stage 3: blur (founding note, 2026-10-24)

## The claim (Jay's)
A talker who turns away doesn't just get quieter; their speech gets blurry, the way an image goes out of focus.
People don't hear that blur as such because the brain fills in the blanks. A decoder that isn't allowed to fill in
should show it. If blur reads rotation, and loudness reads distance once the turn is accounted for, each cue has one
job:
- **range** = dB
- **rotation** = blur

## What's measured so far (`results/rotation/decode_blur/`)
- **With a language model (Android SpeechRecognizer)**, on Jay's same-phrase walks ("there are six fresh beers in the
  fridge", 3-9 phrases per facing):
  - **At 2 m:** no effect. It decoded the phrase perfectly facing away, 4 times out of 4.
  - **At 5 m:** a lean, 88% of content words right facing against 58-79% turned.
  - **Stalls and restarts** don't follow facing.
- **With no language model** (wav2vec2's phoneme recogniser, greedy CTC, one mic), on the same takes at 2 m, everything
  rises in order from facing to away:
  - **phoneme errors:** 16% → 26% → 29% → 42% at 0, 90, 135 and 180 deg;
  - **blur** (the mean entropy of its per-frame odds, which needs no reference): 0.99 → 1.27 → 1.27 → 1.51 bits.
  - **At 5 m,** turned is worse than facing on every measure, with 180 out of order.
- **Which sounds go:** the f of "fresh" was heard 38% of the time facing and 7% turned (it becomes p). s, sh and z
  mostly survive.

## What it isn't yet
- **Enough:** 2-8 takes per cell, one talker, one room, one phrase.
- **Free of distance:** facing at 5 m (37% errors, 1.56 bits) reads like facing away at 2 m (42%, 1.51 bits).
- **Explained:** that the weak high consonants carry it fits mouth directivity, but this test doesn't show it.

## Next
Brief N (`harness/briefs/N_blur_at_scale.md`): Jay's walks, matrix sentences, and LOCATA, whose close-talk mic gives
each utterance's clean version as the reference.
