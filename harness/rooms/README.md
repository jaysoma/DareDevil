# Image-source rooms: Angle2's inward pull, with known truth

Clean speech played from -60..+60 deg (10 deg steps) at 1.5 m in simulated rooms, heard by a horizontal 2-mic pair at
157 mm (the phone) and 69 mm (a STARSS23 tetrahedron pair). The cuts use the STARSS23 harness's format, so
`harness/starss23/run_schemes.mjs` runs the schemes on them unchanged. Results: `results/angle2_pull.md`.

## 1. Speech (21 onsets, no audio committed)
Five clean clips, all from GitHub, so no Zenodo access is needed:
- `cmu_arctic_us_aew_a0001.wav`, `cmu_arctic_us_axb_a0004.wav`:
  https://github.com/LCAV/pyroomacoustics/tree/master/examples/input_samples
- `5703-47212-0000.hq.ogg`, `3436-172162-0000.hq.ogg`, `198-209-0000.hq.ogg` (LibriSpeech excerpts):
  https://github.com/librosa/data/tree/main/audio

Put them in one folder, then:

    pip install pyroomacoustics soundfile scipy numpy
    python harness/rooms/onsets.py <clips folder> <work>/utts.npy      # also writes utts_ctx.npy

## 2. Rooms, then both schemes
    harness/rooms/run_all.sh <work>/utts.npy <work>            # every config in rooms.py --list, both spacings
    CONFIGS="box_small_rt0.4+n20 free+n20" harness/rooms/run_all.sh <work>/utts.npy <work>

Configs (`rooms.py --list`): `free`; partial rooms with one or two walls kept (`floor`, `east`, `south`, `floor_east`,
`floor_south`, `floor_ceiling`, `order1_all`); shoeboxes `box_{small,mid,big}_rt{0.2,0.4,0.7}`. Modifiers:
`+n<SNR>` diffuse noise, `+ctx` the clip's own preceding words, `+jit` the onset handed over 0-100 ms early. The report
used the base configs plus:

    for b in free box_mid_rt0.4 box_small_rt0.4; do for m in +n30 +n20 +n10 +ctx +jit +n20+ctx+jit; do echo $b$m; done; done
    floor+n20 floor+n10 south+n20 floor_south+n20 floor_ceiling+n20 floor_ceiling+n10 order1_all+n20 order1_all+n10
    box_big_rt0.4+n20 box_big_rt0.4+n10 box_small_rt0.2+n20 box_mid_rt0.2+n20

## 3. Score
- `score.py <work>`: per-angle lean for both schemes, from `run_schemes.mjs`'s predictions.
- `trace.mjs cuts.jsonl <schemes dir> [truth] [max]`: every counted window of `readUtterance`.
- `sweep.py <work>/cuts out.json name=<schemes dir> ...`: Angle2's onset for several copies of the schemes folder
  (used for the `U_AGREE` / `U_HITS` / `U_WIN` ablation).
- `before_after.py <work>/cuts <before schemes> <after schemes> <out>`, then `summary.py <out>`: the before/after
  tables.
- `analysis/probe.mjs` + `analysis/policies.py`: dump every window and try other counting rules offline.
