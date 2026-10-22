# geonar-truth

Phone recordings of Jay walking and talking around the house, with what is needed to work out where he was: the room,
its landmarks, where the phone sat, what he said and when, and what ODAS heard. Built 2026-10-22.

- `library.json` -- every tape: name, when it was recorded (America/Chicago), duration, rotation walk or not.
- `truth_inputs/room.json` -- the room outline and openings; `landmarks.json` -- furniture and fixtures (x, y is each
  one's min corner); `poses.json` -- the phone's place and facing per tape, each with how it was established.
- `tapes/<tape>/transcript.json` -- the Whisper decode (distil-large-v3), segments with times: the words the Truth page shows.
- `tapes/<tape>/odas.json` -- ODAS over the whole tape (today's geonar_odas.exe, the phone pipeline's settings: 157 mm
  baseline, 8 pots, 8 tracks, theta-inactive 0.60). No stops and no truth went into it.
- `tapes/<tape>/audio-input.json` -- the audio's format, length and sha256. The audio itself is not in this repo.

Not included: marked positions (the old stops were paired with silence-separated bursts, which merges positions that are
named without a 3 s pause), and the radio-broadcast walk (walk-153448). Positions are meant to be re-marked from the
transcripts' words against `truth_inputs`.
