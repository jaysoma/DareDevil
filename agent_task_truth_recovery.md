# Agent task: recover where Jay stood, tape by tape

You are recovering ground truth for 29 phone recordings: for each tape, **where Jay was standing during each stretch of
speech**, as positions on the room map. The old position marks were dropped from this dataset because they were paired
with speech by silence gaps and came out wrong. Your positions come from **what Jay says on the tape**, placed with the
room's landmarks and the phone's pose. Work one tape at a time and report what you could not settle.

Everything is in this repo, and also served read-only at `https://jaysoma.dev/voice/geonar-truth/<path>` (the bare
`/voice/geonar-truth/` lists every file).

## Inputs

| File | What it holds |
|---|---|
| `library.json` | Every tape: `name`, `recorded` (America/Chicago), `duration_s`, `rotation` (turning in place, not walking), `note` |
| `truth_inputs/room.json` | Room outline (`outline`, metres), `openings`, `room_w`, `room_d`, `ceiling_h` |
| `truth_inputs/landmarks.json` | Furniture and fixtures: `kind`, `x`, `y`, `w`, `d` (and `shape`, `size`) |
| `truth_inputs/poses.json` | Per tape: the phone's `x`, `y`, `facing_deg`, `phone_h_m`, `mirror`, and `status` (how the pose was established) |
| `tapes/<tape>/transcript.json` | Whisper decode: `segments` of `{t0, t1, text}` in seconds from the tape's start |
| `tapes/<tape>/odas.json` | ODAS over the whole tape: `frames` of `[timeStamp, tracks [[id, az_deg, activity]], pots [[az_deg, E]]]`, `hop_s` per timeStamp |
| `tapes/<tape>/audio-input.json` | The audio's format, length and sha256 (the audio itself is not here) |

## Conventions (get these right before anything else)

- **Map frame:** metres; x to the right, y up, as the Truth page draws it (y grows away from the TV wall).
- **Landmarks:** `x, y` is the **minimum corner**. A landmark covers `x .. x+w` and `y .. y+d`; its centre is
  `(x + w/2, y + d/2)`. Circles have `d = w`. Several kinds repeat (three `couch` entries, `island` and `island 2`).
- **Phone:** `facing_deg` 0 points toward +y; positive turns clockwise (toward +x). A **bearing** from the phone is
  measured from its facing, clockwise positive, so a point to the phone's right has a positive bearing. A position at
  range `r` and bearing `b` is `(x + r·sin(f+b), y + r·cos(f+b))` with `f = facing_deg`.
- **Times:** transcript `t0`/`t1` are stamped to whole or half seconds; treat them as ±1 s.
- **ODAS `az_deg`:** the two-capsule pair's bearing (asin of x). Its sign relative to the map depends on which capsule
  is the left channel (`mirror`), so calibrate the sign per tape from one stretch whose place is unambiguous before you
  use ODAS for anything else.

## Steps, for each tape

1. **Find the stops in the words.** A stop starts where Jay announces a place ("first position", "this is position 2",
   "I'm at the corner of the kitchen bar", "two meters from the phone") and lasts until the next announcement or until
   he says he is moving ("walking", "talking while I'm walking"). Walking stretches get no position. The last few
   seconds of most tapes are Jay walking back saying "bye Siri"; they are not a position.
2. **Place each stop from what he says**, in this order of strength:
   - a named landmark ("middle of the couch", "corner of the kitchen bar", "the edge of the sectional",
     "in line with the angled door"): map it to coordinates from `landmarks.json`/`room.json`, standing in front of
     the landmark on the side facing the phone unless the words say otherwise;
   - a spoken distance and/or angle from the phone ("about 3.5 meters", "45 degrees", "same bearing"): convert with the
     pose; a bare distance with no angle means straight ahead of the phone's facing;
   - both: use the landmark, and record the spoken distance and angle beside it as a check.
3. **Write down every ambiguity instead of resolving it silently.** If a phrase has two readings ("in line with the
   angled door" can mean *level with* the door or *in the door's direction from the phone*), give both positions.
4. **Optionally check with ODAS.** For each stop, take the strongest track bearings in its time window, starting from
   the first frames after each speech onset (the direct sound arrives first). Report whether they agree with your
   position's bearing. ODAS may choose between two word-readings that differ by more than 20°. **It never overrides
   the words**, and a stop with no clear agreement keeps the words' position, flagged.
5. **Check the pose.** If the words cannot fit the room from the pose in `poses.json` (e.g. a landmark would be behind
   a wall, or a spoken range is far from the landmark's range), say so; do not move the phone yourself.

## Rules

- **The decode is the truth.** Never use earlier marks, stops files or dots from anywhere else.
- **One tape at a time. No aggregation:** no averages or "N of M" scores across tapes, and no constant fitted on
  several tapes. A measured constant (the phone's 1.5 m height) is fine.
- **Rotation walks** (`rotation: true`): Jay stays at one spot and turns; give one position and list the turns with
  their times.
- **The phone moves between tapes**, even tapes minutes apart (194940 and 195454 had different spots). Never copy a
  pose or a position from another tape.
- **Pose trust** follows `poses.json` `status`: "placed by Jay" and "confirmed by Jay" are solid; "inferred" is good;
  "2026-09-30 TV-stand stamp" and "as marked … not re-checked" are unverified, so flag any tape whose words fight its
  pose.
- Don't edit anything under `truth_inputs/` or `tapes/`.

## Output

For each tape write `positions/<tape>.json`:

```json
{
  "tape": "walk-194940",
  "pose_status": "inferred 2026-10-21 ...",
  "stops": [
    {
      "n": 2, "t0": 23.0, "t1": 33.0,
      "words": "This is position 2 in the middle of the couch, right against the couch",
      "basis": "landmark",
      "x": -2.43, "y": 3.95,
      "range_m": 4.16, "bearing_deg": -4,
      "alternatives": [],
      "odas_check": "agrees within 6 deg",
      "confidence": "high",
      "note": ""
    }
  ],
  "questions": ["Which side of the phone is the kitchen bar on?"]
}
```

`basis` is `landmark`, `spoken_range_angle`, `spoken_range` or `unknown`. Leave `x`/`y` null when the words do not place
the stop, and say why in `note`. `confidence` is `high`, `medium` or `low`.

Questions for Jay are for facts he can answer roughly from memory, such as **which side** of the phone something was on
or whether the phone moved. He doesn't remember exact angles, so never ask for one.

Also write `positions/REPORT.md`: one short section per tape listing its stops, every ambiguity, every pose doubt and
every question. Keep it per tape, with no cross-tape totals.

## Worked examples (from Jay, 2026-10-21)

- **walk-194940:** phone on the TV stand, facing 0. Position one is 0–17 s, "in line with the angled door" (ambiguous,
  so give both readings). Position 2 is 23–33 s, "in the middle of the couch, right against the couch". Position 3 is
  33–47 s, "I'm at the corner of the kitchen bar".
- **walk-155937:** phone on the TV stand, facing 0. Jay placed the middle of the couch, where he sat, at 4.26 m and −5°.
  His spoken "about 3.5 meters" was short.
- **walk-195454:** phone at the edge of the sectional, facing 90 (confirmed by Jay). The kitchen-bar and dining-table
  stops lie roughly in a line from the phone.
