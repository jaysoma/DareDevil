# Brief C: what CAM++ knows about facing, under the hood

Read `README.md` here first (rules, inputs, the bar). Folders: `harness/rotation/campp/`, `results/rotation/campp/`.

## The question
Jay: "If CAM++ is able to identify a speaker mostly impervious to rotation and changes in room acoustics, that means it
knows something we don't and it's hiding it under the covers." The model is trained to discard facing by its output,
so look inside it. The voice is known to it, so what's left over in its middle layers may be the channel: facing and
distance. A clue from his notes: notching out 1-3 kHz made the embedding move with heading (toward/away 55% → 73%
left out, n = 11).

## Steps
1. **The model:** `speaker_embeddings/campplus_zh_en_advanced.onnx`.
   - **Front end:** use exactly what Jay's `geonar/voiceopen.py` (Dictate, on his box) uses: resampling, fbank and
     normalisation.
   - **Intermediate tensors:** list the graph's nodes and expose about six depths as extra outputs (the first
     convolutional block, each dense TDNN block, the stats pooling, the embedding).
2. **Per stop** (`facing_stops.json`), run each mic channel and their mean. Per layer, pool over the stop's speech
   frames (mean and standard deviation), then subtract the same spot's facing-0 stops.
3. **Probes:**
   - **Model:** a logistic regression per layer, toward (0) against turned (90 or more).
   - **Validation:** left out by walk, with a permutation test that shuffles labels within each walk (p < 0.05 to
     pass).
   - **Baselines:** the final embedding, the cosine score against the walk's first facing stop (Jay's earlier tries
     reached about 35%), and the CDR contrast (`facing_pooled.md`) on the same stops.
4. **The notch, at scale.** Repeat step 3 with 1-3 kHz notched out of the input.
5. **Distance:** on the ladder walks, a ridge regression of log distance per layer, left out by walk. Does any layer
   carry distance better than CdrRange's statistic (`results/range_facing/report.md`)?
6. **If a layer passes on Jay's walks:** repeat on LOCATA (on Jay's box: tracked facing and distance, the 160 mm pair,
   tasks 3 and 4), facing the array against facing away.

## Stop rule
If no layer beats the CDR contrast on toward against turned at p < 0.05, stop after step 4 and say so.

## Report
`results/rotation/campp/report.md` and a numbers JSON: which depth carries facing (if any), how well, with or without
the notch, and against the baselines.
