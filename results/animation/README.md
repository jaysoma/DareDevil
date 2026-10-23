# One joined file per recording, for the dashboard animations

Built by `harness/animation/bake.py` from committed results; no scheme is run. Each dataset has an `index.json` listing
its files. Words are added on Jay's box by `harness/animation/add_words.py`. None of the datasets ships transcripts,
and the cloud sessions can't fetch Whisper.

| folder | files | what a tile is |
|---|---|---|
| `locata/` | 16 recordings (tasks 3 and 4, dev and eval), 341 onsets | Real talkers walking in one lab room, tracked. The closest to the phone: a horizontal pair at 160 mm. Start here. |
| `starss23/` | 168 recordings, every labelled onset | 16 real rooms, every sound labelled. The array is a sphere, so a pair's angle is a cone, not an azimuth (see below). |
| `dechorate/` | 11 wall settings | Static loudspeakers in one lab room; clean speech through measured responses. Labelled echoes per surface. |

## LOCATA (`locata/<set>_<task>_<recording>.json`)
- **`tracks[talker]`**, every 0.1 s, `t` in seconds from the array audio start:
  - `along_m` and `ahead_m`: the head in the array frame, from the pair centre (along the mic axis, and in front of it);
  - `height_m`, `dist_m`;
  - `lateral_deg[160|80]`: the exact two-mic angle to the head, as the schemes define it;
  - `facing_deg`: 0 = facing the array, 180 = facing away;
  - `speech`: the talker's voice activity as [start, end] seconds.

  Checked: at every onset these agree with batch A's truth within 0.12 deg (median 0.02).
- **`events`**, one per onset. Each has `truth`: distance, facing and head position, plus `others`, the other talker if
  sounding. Then per pair:
  - **`gcc`:** GccPhat's three angles, their shares and widths, and `track` (its read at 43, 100 and 250 ms, and at the
    lock), for drawing it settle.
  - **`dim`:** brief 11's rule. These records carry no pause share, so it's the margin part only.
  - **`a2`:** Angle2's onset read.
  - **`range`:** CDR in dB, all bands and per band.
  - **`range_rel`:** provisional relative range, anchored on the first lone onset facing the array.
  - **`reflection`:** see below.

## STARSS23 (`starss23/<recording>.json`)
- **`tracks["class/source"]`:** every labelled sound every 100 ms (`f` frame index, `az`, `el`, `dist_m`), straight from
  the dataset's labels. Azimuth is 0 deg ahead and positive to the left.
- **`events`**, one per labelled onset (`kind` speech or other). Each has the true direction and distance, the other
  sources sounding around it, and per capsule pair (`12` ... `34`):
  - **`truth_deg`:** the pair's angle to the source.
  - **`sphere_ref_deg`:** what GccPhat reads for that direction through the sphere alone. Judge reads against it.
  - **`gcc`, `dim`:** the full brief 11 rule, with the pause test.
  - **`a2`, `pause`, `range`, `range_rel`:** as for LOCATA.
- **Drawing a read:** a pair's angle is the angle from that pair's axis, which runs from its first capsule to its second
  (`array.capsules_az_el_deg`). The axes tilt ±35 deg, so a read drawn as a horizontal azimuth sits off the true
  azimuth by geometry alone. A 2D page should either draw the cone's horizontal cut, or pick the pair whose axis is
  nearest horizontal for the source.

## dEchorate (`dechorate/<wall setting>.json`)
- **`setups`**, one per source × array × spacing. Each has `truth` (the pair's angle from the measured direct delay,
  `deg_measured`; the geometric angle; distance; `echoes` per surface with angle, delay and whether it's reflective in
  this setting), and `clips`, one per speech clip with the reads.

## The first reflection
- **What's in the files:**
  - **The reads:** Angle2's second family (STARSS23, LOCATA, dEchorate) and `Angle2.readSound` (LOCATA, dEchorate),
    with a direction and, for `readSound`, a delay `gap_ms`.
  - **The truth:** LOCATA's floor and ceiling echoes worked out from the tracked head (`reflection.truth`), and
    dEchorate's labelled echoes.
- **Status:** brief 8 scored the reads at chance in angle and delay together. They carry a `status` line saying so.
  Draw them dimmed, labelled as candidates, or not at all. The truth echoes are safe to draw as "what the math should
  find".
- **Placing a reflection in the room,** once a reflection read and a range work. Inputs: the talker at range r and
  angle θ, the reflection's angle φ, and its delay Δ after the direct sound.
  - **The talker:** P = r (sin θ, cos θ), as (along, ahead).
  - **The image source:** I = (r + cΔ) (sin φ, cos φ), with c = 343 m/s.
  - **The wall:** the perpendicular bisector of P to I. It passes through (P + I) / 2, with its normal along I - P.
  - **Units:** relative range works: the wall lands in the same relative units as the talker.
  - **What it can't do:**
    - A horizontal pair can't place the floor or ceiling, whose images sit straight below or above the talker at
      nearly the same angle.
    - A two-mic angle can't tell front from back. With the phone backed by a book and everyone in front, take the
      front half.
