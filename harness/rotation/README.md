# harness/rotation

The rotation walks: how they got into this repo, and what has been computed on them. Everything here runs on Jay's box,
where the audio is; the paths inside are that machine's.

| File | What it does |
|---|---|
| `add_rotation.mjs` | Adds walks to `library.json`, `truth_inputs/poses.json` and `tapes/<walk>/` (`transcript.json`, `audio-input.json`) without rebuilding either file. A walk with no truth file gets a null pose that says so. |
| `odas_rot.mjs` | The whole-tape ODAS run behind each `tapes/<walk>/odas.json`, with the first 29 tapes' settings. A folded walk runs on its chord: walk-161331, folded to 90 deg, on 111 mm. |
| `rotation_labels.mjs` | Writes each rotation walk's `experiment`, `held_voice_s` and `note` into `library.json`. |
| `held_sounds.py` | Finds held vowels in the sound itself, since a decode has no words for them: 1.5 s of one steady pitch, voiced against the tape's own level range. The source of `held_voice_s`. |
| `band_windows.py` | Per-band direct, diffuse and total power in 0.5 s windows over each whole tape, for the facing test; writes `tapes/<walk>/band_windows.json`. |

The CAM++ scores in `speaker_embeddings/voiceopen/` come from Dictate's `geonar/voiceopen.py`. None of the rotation walks
had a fixture, so their utterances are the phone's own gate record (`siri_gate.json`), and each file says
`"spans_from": "siri_gate"`.

Two notes on `band_windows.py`:

- **Header bytes.** It reads every tape as raw samples. A walk whose audio is a `.wav` (030615, 160546, 161331, 221126,
  223157) has a 44-byte header, which becomes 11 frames of noise at the very start; the channels stay aligned.
- **The folded spacing.** It computes a folded walk's spacing as `sin((180 - folded_deg) / 2)`. Everywhere else
  (`fold.json`, the Conductor, `odas_rot.mjs`), `folded_deg` is the hinge's opening, with 180 = flat, and the chord is
  157 mm × `sin(folded_deg / 2)`. The two agree at 90 deg, which is the only folded walk so far.
