# Brief N2: blur added by the trip, on LOCATA (2026-10-24)

**On LOCATA, blur reads facing within each recording, but only past about 1.5 m.** From 1.5 to 3 m, turned speech
is blurrier than the same talker's facing speech in 9 of 9 takes (+0.38 bits on average). Under 1.5 m it is
blurrier in 1 of 4, with a mean change of -0.01 bits. **Blur can be told apart from distance as a factor, but not
from blur alone.** Facing and distance each explain their own share and add up (left out by recording, R² 0.22 and
0.15, together 0.33). But turning all the way away adds as much blur as about two doublings of distance, so a single
blur reading can't say which of the two happened. That needs the second cue (Step 4).

Scripts: `harness/stage3/blur/n2/` (`fetch_closetalk.py`, `locata_blur.py`, `locata_curves.py`).
Numbers: `report_numbers.json`, every table in `curves.txt`, every piece in `pieces.json`.

## What was measured
- **Recordings:** tasks 3 and 4, dev and eval, 16 recordings. Four talkers (1, 2, 4 and 5), one room (the HU Berlin
  lab, RT60 0.55 s), 0.6-3.1 m from the array.
- **Far field:** mic 5 only, one mic of the 160 mm pair.
- **Reference:** the talker's close-talk mic. Eval's close-talk files had never been fetched; `fetch_closetalk.py`
  pulled the 15 of them from Zenodo into `Dictate/captures/locata_zenodo/eval/`.
- **Decoder:** wav2vec2-lv-60-espeak-cv-ft, greedy, no language model. Each signal is decoded on its own.
- **Lone speech:** the talker's voice activity, with any other talker cut out, plus 0.3 s either side of them.
  - In task 4 the two talkers overlap almost constantly, so it gives few pieces (task 3: 64, task 4: 45).
- **Pieces:** within one utterance the tracked facing moves 25-50 deg, so each lone stretch is decoded whole and then
  cut where the facing leaves a 40 deg window or the head moves more than 0.3 m (brief D's rule).
  - A piece is kept at 0.8 s or longer (mean 1.45 s).
  - That gives 109 pieces in 21 takes (talker x recording). One piece is set aside because its close-talk decode had
    only 5 phonemes; none is past 3 sd. **108 are kept.**
- **Per piece:**
  - **Blur added:** far-field blur minus close-talk blur, each the mean per-frame entropy over speech frames.
  - **Errors:** the far-field phonemes against the close-talk phonemes, as an edit distance.
  - **Survival by sound class:** the share of each class the far field heard right.
- **Timing:** the far mic lags the close-talk by the trip's delay plus a steady 8-11 ms (in 71% of stretches). That is
  under one 20 ms decoder frame, and pieces are padded by 0.2 s, so it does not move a piece's measures.
- **Check:** close-talk blur is flat across facing: 0.88, 0.89, 0.85 and 0.87 bits from the 0-45 bin to 135-180.
  The far field rises 1.02, 1.23, 1.47, 1.65. That is what the subtraction should see.
- **Not done: distance to the wall.** The files on hand give no wall coordinates in LOCATA's frame. Each piece's
  head position in front of the array (along, ahead) is in `pieces.json` instead.

## Step 1: the facing curve, compared within each take
Each turned piece (90 deg or more) is compared with its own take's facing pieces (under 45 deg) in the same
distance band. The per-take, per-bin table is in `curves.txt`.

| measure | takes x bands, turned worse | turned pieces above their own facing | within-take order test, p |
|---|---|---|---|
| blur added | **10 of 13** | 18 of 24 | **0.004** |
| phoneme errors vs close-talk | 10 of 13 | 16 of 24 | 0.007 |
| far-field blur, raw (no subtraction) | 9 of 13 | 15 of 24 | 0.04 |
| blur added, every frame of the piece | 9 of 13 | 16 of 24 | 0.002 |

- **The order test:** Spearman's rho of facing against blur inside each take x band, summed. The null shuffles facing
  within take x band, 10,000 times.
- **Subtracting the close-talk helps.** Raw far-field blur still carries the talker and the words (close against far,
  r = +0.48), and its p is ten times larger.

**By distance band** (blur added, mean within-take rise over the facing bin, n = turned pieces):

| band | takes turned blurrier | 45-90 deg | 90-135 deg | 135-180 deg |
|---|---|---|---|---|
| 1.5-3 m | **9 of 9**, +0.38 bits | +0.27 (n 12) | +0.15 (n 7) | +0.51 (n 12) |
| under 1.5 m | 1 of 4, -0.01 bits | -0.04 (n 3) | +0.02 (n 3) | -0.08 (n 2) |
| over 3 m | one facing piece; no comparison | | | |

- **The curve is not monotonic:** at 1.5-3 m the 90-135 bin (n 7) dips below 45-90. Across all bands the bin means
  are +0.21, +0.11 and +0.42 bits (sd about 0.5).
- **Phoneme errors** follow the same pattern: 8 of 9 takes at 1.5-3 m, 2 of 4 under 1.5 m.
- **The 45-90 bin is high because of three task-4 pieces at about 2 m** (81, 84 and 48 deg; see "Where it breaks").
  With so few pieces per bin, this order isn't settled.

## Survival by sound class
The share of close-talk phonemes the far field heard right:

| class | facing (< 45) | 45-90 | turned (>= 90) | takes with turned below their own facing |
|---|---|---|---|---|
| weak fricatives (f, θ, v, ð) | 88% (64) | 50% (20) | 57% (42) | 6 of 9 |
| strong fricatives (s, ʃ, z, ʒ) | 94% (84) | 86% (28) | 73% (64) | 6 of 9 |
| stops | 90% (172) | 80% (81) | 67% (109) | 7 of 12 |
| nasals | 98% (92) | 88% (41) | 76% (71) | 6 of 12 |
| vowels | 87% (322) | 77% (133) | 60% (221) | **11 of 12** |

- **Weak fricatives fall furthest, and first:** most of their drop has happened by 45-90 deg. Strong fricatives
  survive best. Both fit Jay's walks ("fresh": f went from 38% to 7%, s survived).
- **Vowels fall too, and in the most takes.** On LOCATA the blur isn't only in the high consonants.
- Shares are summed over takes within one room.

## Step 2: the distance curve (facing within 30 deg, 33 pieces)
- **Blur added rises with distance:** the slope rises in 6 of the 7 takes that span 0.3 m or more. Within take it is
  +0.27 bits per doubling of distance (30 pieces, permutation p = 0.009).
- **Phoneme errors:** 5 of 7 takes, +0.13 per doubling (p = 0.046).

## Step 3: the two factors, left out by recording

| model | blur added, as is (108) | blur added, within take (99) | errors, as is | errors, within take |
|---|---|---|---|---|
| facing alone, held-out R² | 0.17 | 0.22 | 0.14 | 0.15 |
| distance alone | 0.05 | 0.15 | 0.05 | 0.13 |
| both | **0.21** | **0.33** | 0.18 | 0.26 |
| both, plus facing x distance | 0.22 | 0.32 | 0.18 | 0.24 |
| fit: per 180 deg | +0.78 bits | +0.74 | +0.33 | +0.29 |
| fit: per doubling of distance | +0.27 bits | +0.38 | +0.12 | +0.17 |

- **"As is"** uses one intercept, since the close-talk already sets each take's zero. **"Within take"** subtracts each
  take's mean from both sides.
- **The two factors barely overlap here** (facing against log distance, r = +0.11), and their shares add.
- **Facing is the larger factor** over LOCATA's range (0.6-3.1 m, about 2.3 doublings).
- **On one blur reading the two are interchangeable.** Turning fully away (+0.74 to +0.78 bits) costs as much as two
  to three doublings of distance. A talker at 1 m facing away blurs like one at roughly 4-7 m facing the array.
- **The distance band matters more than a linear interaction shows.** A linear facing x distance term adds nothing
  held out, yet the band table gives 9 of 9 against 1 of 4. The effect looks like a threshold, not a slope (untested).

## Where it breaks
**Three takes go the other way, all under 1.5 m.** None is reversed by much; each is close to zero:
- **dev task 4 rec 2, talker 2:** the turned piece, 92 deg at 1.15 m, adds 0.08 bits. The facing pieces add 0.31
  (1.16 m) and 0.12 (0.76 m).
- **eval task 3 rec 1, talker 2:** 137 and 151 deg at 1.3-1.4 m add -0.02 and +0.18 bits. The one facing piece
  (42 deg, 1.32 m) adds 0.16.
  - **The 137 deg piece reads 5.5 dB louder** at the far mic, relative to the close-talk, than the facing piece. The
    far mic shouldn't get louder when the talker turns away, so something at the close-talk mic may have changed
    (untested).
- **eval task 4 rec 2, talker 2:** 118 deg at 1.16 m adds -0.08. The facing piece (17 deg, 0.90 m) adds 0.07.
- **What they share:** a distance under 1.5 m, and a head 0.6-1.3 m in front of the array.
- **An explanation, untested:** the room's critical distance. With V = 209 m³ and RT60 = 0.55 s it is about 1.1 m for
  an omni source, larger facing and smaller turned. Under about 1.5 m the turned talker's direct sound may still
  match the reverberation, so the decoder still gets a clean copy.
  - **That fits Jay's walks:** the kitchen at 2 m was blurrier at 15 of 15 turned stops.
  - **One gap:** brief N1's living-room misfit, 125621, is at 4 m, so this doesn't explain it.

**Pieces off the two-factor fit by 2 sd or more:** 8 of 108, and 7 lie above it.
- **Five are task 4 pieces at 1.7-2.8 m,** and three of those (48, 81 and 84 deg) make up the high 45-90 bin.
  - **Their talkers are the ones whose close-talk sits 5-17 dB above the far mic.** In eval task 4 rec 2, talker 2's
    "level added" is -16 dB, against about -1 dB for talker 2 in eval task 3 rec 1. That is consistent with the
    close-talk mic gain differing per take. It doesn't move blur, but level is only comparable within a take.
  - **Why task 4 sits high is open.** One untested candidate: in task 4 the other talker has only just stopped (at
    least 0.3 s earlier), and the room's tail of their voice may still be there.
- **The one below the fit:** eval task 3 rec 3, talker 4, 56 deg at 2.58 m. Its close-talk decode is unusually
  blurry (1.40 bits), so the subtraction overcorrects.

## Not settled
- **Little data per take:** 108 pieces of 0.8-2 s from four talkers in one room, and only 13 take x band cells with
  both facing and turned pieces. Under 1.5 m there are just 4 takes and 8 turned pieces.
- **The order:** blur rises from facing to turned, but the 45-90 and 90-135 bins are not in order.
- **Only one decoder here.** Whether a second phoneme model sees the same is brief N4's.
- **Step 4 (Jay's model) is not done here:** the brief runs it after all four parts.
  - `pieces.json` has each piece's far-field and close-talk level for the dB side.
  - **The close-talk gain differs per take,** so the range call has to use level within a take, or the far-field
    level alone.
