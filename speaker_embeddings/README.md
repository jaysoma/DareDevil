# speaker_embeddings

What CAM++ and TitaNet produced on Jay's walks, copied from `Dictate/captures/geonar/`. The 20 MB tracker files (`runs/*-track.json`, which also carry per-window voiceprint diagnostics from both models) are left out.

| Path | What it is |
|---|---|
| `voiceprint-jay-campplus.json` | Jay's CAM++ voiceprint: a 192-value centroid built from windows across 35 tapes, with how tightly the windows sit around it (median, p10 and p90 cosine). |
| `voiceprints-jay-20260928.json` | Seven 192-value embeddings of Jay saying "hey Siri". The file does not name the model. |
| `voiceopen/<walk>.json` | CAM++, from `geonar/voiceopen.py`: each tape enrols on its own opening, and every utterance gets a cosine score against that enrolment. Scores only, no vectors. |
| `titanet/walk-125621.npz` | TitaNet, from `geonar/titanet_emb.py`: embeddings for 25 utterances of the 360° rotation walk, as `emb` (25 × 192), `t`, `dur` and `oi`. |
| `campplus_rttm/<walk>.campplus.rttm` | CAM++ speaker turns for five walks. |

Not here: the notched CAM++ run on walk-231921 (2026-10-03). No file kept it. Its result survives only in notes: notching out 1–3 kHz, where F1–F3 carry the identity CAM++ keys on, made the embedding move with heading (facing-vs-away leave-one-out 55% → 73%, n = 11), while the clean embedding still held identity. Nothing saved CAM++'s per-utterance vectors or anything from inside the model, so looking under its hood means a fresh run.
