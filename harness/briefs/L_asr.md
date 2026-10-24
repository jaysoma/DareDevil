# Brief L: device-directed words on real recogniser output (Stage 3/4, for Tampere)

Read `README.md` here first. Folders: `harness/linguistic/asr/`, `results/linguistic/asr/`.

## The question
Briefs 19 and 22 found that Jay's contrast scores a phrase by how well it fits a device's instructions, minus how well
it fits the talk around it. On reference text it finds 89% of instructions at 1 false accept per hour, 98.5% at 10,
and accepts real requests to people only 0.2-4.4% of the time. Both reports list the same limit: "text, not
recogniser output". Does it survive a recogniser's errors, on audio?

## Data and tools
- **The method, unchanged:** `harness/device_directed/` (brief 19: `build_set.py`, `methods.py`, `score.py`,
  `evaluate.py`) and `harness/who_for/` (brief 22).
- **Audio:**
  - **SLURP's** recorded commands.
  - **AMI's far-field meetings,** one distant mic.
  - **Switchboard's** calls, if on Jay's box.
- **Recognisers:** NVIDIA Parakeet (TDT 0.6B) as the main one, and faster-whisper (medium.en) as the second. Fixed
  gain, no AGC.

## Steps
1. **Splice in audio, not text.**
   - **What goes where:** brief 19's windows, rebuilt from audio. Each SLURP command's recording is placed inside an
     AMI (or Switchboard) stretch at the spot brief 19 put its text.
   - **Level:** match the command's speech level to the surrounding speech's. Record that level, and also run at −6
     and −12 dB.
   - **What runs where:** where brief 19 used monologue or song stand-ins, run only the AMI and Switchboard parts
     and say so.
2. **Recognise each window,** with both recognisers, keeping word timings and confidences.
3. **Score with brief 19's methods and thresholds, unchanged:**
   - **Measures:** instructions found at 1 and 10 false accepts per hour, and the share of spliced real phrases
     accepted.
   - **Comparison:** each beside brief 19's reference-text numbers on the same windows.
4. **Brief 22's real requests,** if Switchboard audio is there: real requests to the other caller, left in their own
   calls and recognised from audio. Report the acceptance at the same thresholds.
5. **Where it breaks:** word error rate per window against the reference, and the score's loss against word error
   rate. Are the misses commands the recogniser garbled, or context it garbled?

## Report
`results/linguistic/asr/report.md` and a numbers JSON. Open with whether the contrast survives a recogniser, and at
what word error rate it stops, in two sentences. Write it so it can sit beside `results/addressee_findings.md` for
the Tampere group.
