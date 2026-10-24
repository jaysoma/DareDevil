# CAM++ under the hood: what it knows about facing (2026-10-24)

Brief C (`harness/rotation/briefs/C_campp.md`). Scripts: `harness/rotation/campp/campp_layers.py` (opens the model up),
`probe.py` (the probes). Numbers: `numbers.json` and `probe.txt` beside this file; the pooled vectors are in
`vectors.npz` (all speech) and `vectors_nocallouts.npz`.

## The answer
**CAM++'s middle layers seem to know facing, but what they hear is Jay's words. With those words taken out, no depth
beats the CDR contrast, and the stop rule fires: no LOCATA.**

- **What held: the CDR contrast.** On the same stops, the same windows and the same reference, with every word about
  the stop taken out, it still separates toward from turned: balanced accuracy 0.87 (p 0.014, 20 stops), and 0.84
  (p 0.049, 17 stops) without walk-122038. The words were never what it read.
- **On the brief's design, CAM++ looks better than the CDR.** Each stop minus its spot's facing-0 stops, a logistic
  regression per depth, left out by walk: 0.70-0.84 on the two channels' mean (0.93 at best, on one channel notched),
  against 0.72 for the CDR contrast. Every depth passes the permutation test.
- **Those stops' words track their facing.** The decodes (`tapes/<walk>/transcript.json`) show facing-0 stops saying
  "two meters in front of the phone, facing the phone" and turned stops saying "rotated 90 degrees clockwise" or
  "facing away". A speaker model's middle layers carry the phonemes, and a probe trained on these stops can learn the
  callout instead of the facing.
- **Take the callouts out and CAM++ falls, deepest first.** The table keeps the reference fixed (the mean of every stop at
  the spot, which uses no labels; see "Why the reference changes") and changes only the speech:

| depth (both channels' mean, unnotched) | brief's reference, all speech | spot mean, all speech | spot mean, no callouts | no callouts, without 122038 |
|---|---|---|---|---|
| head (FCM convolutional front) | 0.84 | 0.93 | 0.80 | 0.71 |
| tdnn (first TDNN layer) | 0.78 | 0.92 | 0.80 | 0.75 |
| block 1 | 0.77 | 0.92 | 0.67 (p 0.055) | 0.59 (p 0.19) |
| block 2 | 0.70 | 0.93 | 0.70 | 0.62 (p 0.075) |
| block 3 | 0.83 | 0.93 | 0.80 | 0.50 (p 0.41) |
| stats pooling | 0.83 | 0.93 | 0.80 | 0.50 (p 0.39) |
| embedding | 0.78 | 0.90 | 0.57 (p 0.24) | 0.46 (p 0.88) |
| **CDR contrast (4-8 minus 0.1-1.1 kHz)** | 0.72 | 0.81 | **0.87** | **0.84** |
| CdrRange's range statistic | 0.71 | 0.93 | 0.93 | 0.80 |
| stops (toward / turned), walks | 37 (10 / 27), 9 | 42 (15 / 27), 9 | 20 (5 / 15), 5 | 17 (4 / 13), 4 |

  Balanced accuracy, left out by walk; p < 0.05 unless shown. With the words gone, the embedding and the last block are
  at chance, and what survives is in the head and first TDNN layer (0.71-0.80), the depths closest to the filterbank.
  That is the spectral tilt the CDR already reads, and none of it beats the CDR. Across all three inputs and both notch
  settings, the best callout-free depth is 0.80 against the CDR's 0.87, and 0.75 against 0.84 without 122038.
- **Turning doesn't move the embedding farther.** The one-number probe, the cosine distance from the spot's reference,
  is at chance at nearly every depth in every run (0.37-0.69). A turned stop sits no farther from the facing-0
  reference than another facing-0 stop does. Jay's earlier test agrees: the embedding's cosine against the walk's first
  facing stop gives 0.48 (p 0.64, 33 stops), his "about 35%" being the same chance level. CAM++ discards facing as it
  was trained to. It isn't hiding a facing direction underneath; what it had underneath was the transcript.
- **The notch, at scale, doesn't do what it did on one walk.** Taking out 1-3 kHz moved the embedding probe from 0.78 to
  0.72 on the brief's design. Without callouts it went the way Jay's note said, 0.57 to 0.67 (p 0.085) and 0.46 to 0.59
  without 122038 (p 0.19), but on 4-5 walks neither is significant. The middle depths move both ways under the notch.
- **Distance: no depth carries it.** On the ladders (11 steps against each walk's first step, 4 walks), ridge regression
  per depth, left out by walk. The best mean error, 0.90 doublings (block 3 and stats, notched), is no better than calling
  every step the training walks' mean (0.95). The depths rank the steps the wrong way round in at least two of the four
  walks. CdrRange's law ranks them the right way round in all four (Spearman 1.0, 1.0, 0.4, 1.0) but is off in scale
  (1.53 doublings). The stop rule said to stop before this step; it was cheap, so it ran.

## Why the reference changes
The brief's reference is the mean of the spot's facing-0 stops. Against a mean that includes itself, a facing-0 stop
reads exactly zero and the label leaks, so each facing-0 stop is taken against the spot's other facing-0 stops, and 6
of 43 stops have none left and are set aside. Once the callouts are out, only one spot (231921's) keeps two facing-0
stops, leaving too few toward stops to train on. The spot mean (every stop at the spot, whatever its facing) uses no
labels, sets aside only spots with a single stop, and works on both sets. Run on all speech it gives the same verdict
as the brief's design, just higher for everything, the CDR included.

## Limits
- **The callout-free set is small:** 20 stops in 5 walks, only 5 of them toward. Walks 125621, 171645 and 215800 are
  almost all callouts and drop out entirely.
- **The callout filter uses the decode's segment times**, widened by 0.25 s, and a segment counts if it names rotation,
  facing, degrees, distance or the phone, misheard forms included ("racing away", "notated"). walk-122038's kept
  windows (2 s per stop) fall in gaps the decode didn't transcribe, so their content is unknown; that's why the table
  also shows the run without it.
- **Many tests:** 7 depths × 3 inputs × 2 probes × 2 notch settings per run. At p < 0.05, about 4 of those 84 should pass
  by chance, so the scattered callout-free passes (tdnn 0.75, p 0.015) are not evidence alone. The logistic probes ran
  200 permutations (smallest p 0.005), the one-number probes and baselines 1000.
- **The probe's one setting** (C = 1) was fixed, not tuned; at C = 0.01 and 100 the all-speech numbers move by 0.02-0.1
  (`lr_C_sensitivity` in `numbers.json`).
- **No outliers were set aside.** The only stops dropped are those under 1 s of speech (one, 122038's second 90-degree stop) and
  those with no reference.
- **Limits of the walks themselves:** 10 walks in Jay's house, with facings and distances he called himself.

## How it was run
- **The model:** `speaker_embeddings/campplus_zh_en_advanced.onnx`, with seven depths exposed as extra outputs. The
  head is the FCM front's reshaped output (320 × T), then the first TDNN layer, the three dense TDNN blocks after
  their transits, the stats pooling (1024) and the 192-value embedding. Frame-level depths are pooled over the stop as
  mean and standard deviation.
- **The front end:** `voiceopen.py`'s exactly: the 97-tap Hamming sinc at 6 kHz, every third sample, and a Kaldi fbank
  (80 bins, povey window, snip_edges off, 20 Hz to Nyquist minus 400 Hz, global mean removed). It is rebuilt outside
  sherpa-onnx so the graph can be tapped, and checked against sherpa's extractor on three spans of walk-231921: cosine
  1.000000.
- **Speech:** the stop's voiced 0.5 s windows, as `facing_pooled.py` picks them, joined end to end. The CDR baselines are
  read from those same windows.
- **The notch:** 1-3 kHz zeroed bin by bin on the whole 16 kHz tape, before the fbank.
- **Inputs:** each channel and their mean. The table shows the mean, and the two channels give the same verdict
  (`probe.txt`). Which capsule is channel 0 varies by tape.
- **Environment:** the DiartLab venv, plus the `onnx` package (which that venv lacks) from a separate folder on
  PYTHONPATH, so the venv itself is unchanged.

## Questions for Jay
1. **LOCATA would be the clean test** (step 6): its talkers' words don't follow their facing. The stop rule says skip
   it. Do you want it run anyway, as the one test where content can't stand in for facing?
2. **The notch clue (walk-231921, 2026-10-03):** was that run on the "six fresh beers in the fridge" sentences only,
   or on whole utterances with the callouts in? If the callouts were in, the 55% to 73% may be the same effect as here.
