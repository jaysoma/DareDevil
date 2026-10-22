# Task: recover per-tape truth for the walk corpus

You are reconstructing ground truth for ~51 two-microphone recordings ("tapes") made in one house.
The recordist knows WHERE the phone could have been (4 poses) and WHERE he stood (named landmarks),
but not WHICH pose each tape used or WHICH landmark each stop was. Your job is to recover both from
evidence, state your confidence, and send everything you cannot settle to a review list.
Do not guess. An unresolved stop is a correct output; a wrong confident one corrupts every later result.

## Inputs (repo paths)
Read `README.md` at the repo root first; where it and this brief differ on file contents, the README wins.
- `truth_inputs/landmarks.json` — furniture and fixtures. **x, y is each item's MIN corner**; its centre is
  (x + w/2, y + d/2). Spoken places ("center of couch", "end of kitchen bar") are resolved against these.
  Names are the recordist's own; treat them as authoritative.
- `truth_inputs/poses.json` — the phone's place and facing PER TAPE, each with how it was established.
- `truth_inputs/room.json` — room outline and openings.
- `tapes/<tape>/transcript.json` — Whisper (distil-large-v3) segments with times.
- `tapes/<tape>/odas.json` — ODAS over the whole tape (157 mm baseline, 8 pots, 8 tracks). Built with no stops and no truth.
- `tapes/<tape>/audio-input.json` — format, length, sha256 (no audio in the repo).
- `library.json` (repo root) — every tape: name, recording time (America/Chicago), duration, rotation walk or not.

Ignore any `draft_of`, `transcript`, `phone_note`, `mirror`, `sonar_room` or `dots` fields inside room or landmark files:
they are editor state left over from other work and do not describe any tape.

## Step 1 — stops and landmarks (per tape)
1. Segment stops from the transcript's words and segment times ONLY. Do not use silence-separated bursts: they
   merge positions that were named without a 3 s pause (see README). A position change is where a new place is named.
2. For each stop, match what was said there to a landmark name. Matching may be loose
   ("corner of the couch" -> "center of couch"; "far back wall" -> "8/9 meters") but must be justified in one line.
3. Spoken distances or angles ("about 3 meters", "rotated 90 degrees") are recorded as `said`, never converted into a position.
4. No confident match -> the stop goes to the review list with its time span and transcript snippet.

## Step 2 — VERIFY the given phone pose (per tape), from independent evidence only
`poses.json` already assigns a pose to each tape. Do not re-derive it from scratch: check it. Mark a tape's pose
`confirmed` when the evidence below agrees, `disputed` (with the evidence) when it does not, and `circular` when its
recorded provenance is one of the recordist's own bearing schemes (GccPhat, Angle2, etc.) -- those are what this truth
will later be used to evaluate, so a pose they chose cannot be used to grade them; such a tape needs independent
confirmation before its stops can be tier A. Evidence, in order of weight:
1. Session clustering: tapes recorded within the same sitting (same date, close times) share a pose unless the
   transcript says the phone moved.
2. Transcript statements about the phone ("on the TV stand", "bar counter", "top capsule on the right").
3. ODAS bearings at stops with a resolved landmark: for each pose P1-P4 and each capsule sign (+/-), compute each
   landmark's expected bearing. A two-mic pair cannot tell front from back, so compare LATERAL angles
   (fold each bearing to [-90, +90] about the mic axis) and only for |lateral| < 70 deg. Pick the pose+sign with
   the lowest median absolute error; require the runner-up to be at least 1.5x worse, otherwise mark ambiguous.
4. A stationary source during pauses (e.g. the HVAC vent in room.json) as a cross-check: its ODAS bearing in
   silence depends only on the pose.
5. audio-input.json channel order as a constraint on the sign.

## Known issues found before launch (check each; do not assume they are resolved)
- EXCLUDE as unusable for bearing truth: walk-195454 and walk-212347 (dead capsule pair, L/R corr +0.058 and
  +0.12) and walk-194532 (mono duplicate, corr 1.000). Their stops can still be listed, as tier C, flagged `dead_pair`.
- 13 tapes carry the same status line, "2026-09-30 TV-stand stamp; Jay's walk-155937 placement ... puts the phone in
  the same spot". That is one tape's placement applied to others recorded Sep 14-22: treat these poses as UNVERIFIED
  until evidence confirms each one.
- walk-194940: pose inferred partly because "onsets agree" -- the recordist's own scheme. Mark `circular` unless
  independent evidence confirms it.
- CAPSULE ORIENTATION IS A PER-TAPE UNKNOWN. The recordist's convention is that the phone's TOP capsule points to HIS
  LEFT as he faces the phone (for the TV-stand pose, facing +y, that is +x on the map). He confirms he did not always
  follow it: a diagram he drew of one TV-stand tape shows the top capsule toward -x (his right). So do NOT assume a sign
  for any tape: for every tape, test both capsule signs as part of the pose check (Step 2.3) and record which one the
  evidence supports. Use `mirror` and the convention only as a weak prior.
- walk-111830: the recordist says on tape the top capsule is "on the right, where usually you'd be on the left" -- in his
  own frame facing the phone. Expect the sign opposite to the convention there; let the evidence decide.
- walk-114614: the recordist says the phone is "lying on its back" -- a different geometry from the upright TV-stand pose
  it is assigned. Expect `disputed`.
- walk-203939 (the reference walk) sits at (-3.35, -0.2) facing 0, which matches no other tape's pose: confirm whether
  it is a fifth placement or a mis-entered facing for the (-3.4, -0.25) facing ~45 placement.
- walk-165255 and walk-195454 were saved on older map versions (f44f6b, b85e4e) than the rest (a17f2f); check that their
  coordinates are in the same frame.
- `mirror` is true on all 29 tapes, so it carries no information except where it should differ (walk-111830).
- ODAS azimuths are quantised (repeating values such as 0, 3.8, 7.5, 22.6, 51.6, 82.1): about 4 deg steps near
  broadside, coarser toward the ends. Good enough to choose between poses, not to grade fine angles.

## Outputs
- `truth/<tape>.json`:
  `{ "tape", "pose_id", "capsule_sign", "pose_confidence": "high|medium|low|unresolved",
     "pose_evidence": [ "..." ],
     "stops": [ { "t0", "t1", "landmark_id" | null, "said", "match_note", "tier": "A|B|C" } ] }`
  Tier A: landmark resolved AND pose high-confidence. Tier B: landmark resolved, pose medium/low.
  Tier C: no landmark (still usable for repetition-spread metrics).
- `truth/review.md` — every unresolved stop and every ambiguous pose: tape, time span, transcript snippet,
  your top candidates, and the single question that would settle it.
- `truth/summary.md` — table: tape, pose, confidence, stops by tier; plus totals.

## Rules
- Do not edit anything under `truth_inputs/` or `tapes/`.
- Every claim in a truth file must be traceable to an evidence line.
- Finish with a self-check: re-derive 5 random tier-A stops from scratch and report agreement.
