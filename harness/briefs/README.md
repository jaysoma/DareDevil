# Stage 2 and 3/4 briefs, for local agents (2026-10-24)

Four independent runs. One agent each, one worktree each, and no two write the same file.

```
git pull
git worktree add ../dd-diart    -b stage2-diart      # "Do brief 15 in cloud_sessions.md (diart), locally."
git worktree add ../dd-identity -b stage2-identity   # "Do harness/briefs/I_identity.md."
git worktree add ../dd-handover -b stage2-handover   # "Do harness/briefs/K_handover.md."
git worktree add ../dd-asr      -b stage34-asr       # "Do harness/briefs/L_asr.md."
```

## Rules for every brief
- **Write only inside your own folders,** named in your brief. Don't edit `src/`, `library.json`,
  `results/INDEX.md` or another brief's folders.
- **Measured and unmeasured, kept apart.** Every number comes from a run in your folders, with its n. Any
  explanation you didn't test is labelled "untested" in the same sentence. Jay objects to guesses dressed as findings.
- **Outliers:** set obvious ones aside, say how many and why, and give means of the rest. No medians as headlines.
- **Lead with what held,** then the limits. Plain sentences.
- **Questions for Jay:** three at most, batched, each naming the recording and time. Look in the files first.
- **Learned models and the walks' callouts.** Jay's rotation walks have him saying "rotated 90 degrees" and "facing
  the phone". CAM++'s middle layers learned those words instead of the facing (`results/rotation/campp/report.md`).
  Any learned model scored on those walks must have the callout segments removed (`tapes/<walk>/transcript.json`).
- **Stage 1's rule:** every utterance is a new speaker, and the same place doesn't mean the same speaker. Stage 2 is
  where that changes, from the voice, never from the place alone.
- **Keep tool output lean:** summaries, not arrays.

## What's on Jay's box (use it; if something's missing, say so and stop that part, don't substitute)
- **Corpora:** LOCATA (zips), AMI (far-field and headset audio, with its annotations), SLURP, Switchboard and
  his walks' raw audio (`Dictate/captures/geonar/tapes/`, 10 also in this repo under `tapes/<walk>/`).
- **Models:**
  - **CAM++:** `speaker_embeddings/campplus_zh_en_advanced.onnx`, with Dictate's `geonar/voiceopen.py` front end.
  - **TitaNet:** `geonar/titanet_emb.py`.
  - **diart, faster-whisper, NVIDIA Parakeet** if installed.
- **The schemes:**
  - **Angle:** `src/schemes/GccPhat.mjs`, read with `reread: false` as the harnesses do.
  - **Range:** `src/schemes/CdrRange.js`.
  - **Callers:** `harness/batchA/locata/record_reads.mjs` shows how a harness calls them.
