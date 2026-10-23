# One joined file per recording, for the dashboard animations

Built by `harness/animation/bake.py` from committed results; no scheme is run. Each dataset has an `index.json` listing
its files. Words for LOCATA and STARSS23 are added on Jay's box by `harness/animation/add_words.py`, which streams the
audio from Zenodo one file at a time. Neither ships transcripts, and the cloud sessions can't fetch Whisper. dEchorate's
clips are read sentences, so their text is already in.

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
- **Which pair to draw:** the four capsules sit on a sphere of radius 4.2 cm at azimuth ±45 and ±135 deg, elevation ±35
  deg. Pairs **14** and **23** are horizontal (68.8 mm; axes along azimuth −135 and 135 deg), so their angle maps onto
  a horizontal half-plane the way the phone's does. Use one of those for a phone-like page. The other four pairs tilt
  45 deg, so their angle is a cone that a flat page can't place.
- **Remember the sphere:** even on a horizontal pair, the sphere bends sound and reads wide. Judge a read against
  `sphere_ref_deg`, not `truth_deg`.

## dEchorate (`dechorate/<wall setting>.json`)
- **Words:** there are no dEchorate recordings here. Each clip is a clean EARS read sentence played through dEchorate's
  measured room responses: 1.0 s from `onset_in_file_s` in the EARS file. `file_text` is the whole file's text (EARS
  transcripts, CC BY-NC 4.0). `add_words.py dechorate` decodes the 16 EARS files and gives each clip its own words.
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

## Range on the page: the anchor
- **`range_rel`** is each read's distance as a multiple of the anchor's, from the CDR by brief 20's rule,
  10^((CDR_anchor − CDR)/20). The anchor is the recording's first lone onset (on LOCATA, also facing the array).
- **On a dashboard,** multiply by `range_anchor_dist_m`, the anchor's true distance. The anchor then sits where it
  truly was, and every later dot is the CDR's own prediction from it. Drawn beside the true track, this shows the
  compression brief 20 measured directly: far talkers land nearer than they are.
- **In the app** there's no true distance. The anchor is 1 unit, and Render's range scale says how big a unit is
  drawn.
