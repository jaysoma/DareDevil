# Protocol: the announcement as a room probe, Jay's own check

Brief 20 step 5. The simulation (`report.md` section 5) says the method reads r_c with a steady bias of about −25%,
and the echo time to within about 15%. This check measures both in real rooms, and says whether the talkers' CDR
follows the line the probe predicts. Everything below is what the analysis in `harness/range_facing/sim_probe.py`
(`self_path`, `tail_read`, `decay_fit`) and `drr.py` needs. The same functions run on real recordings unchanged.

## What you need

- **The phone, on the same book every time.** The book's reflection arrives under 1 ms after the direct sound. The
  outdoor self-path is measured on the book, so it absorbs that reflection and the room read doesn't count it.
- **The volume:** fixed, and written down. Use the same volume for the calibration and every room. Nothing in a room
  recording can check it.
- **A second recorder for the 1 m reference only:** a second phone or a measurement mic, 48 kHz, gain fixed.
- **A tape measure, and masking tape for marking spots on the floor.**
- **The app's raw two-mic capture:** 48 kHz, both channels. No AGC, noise suppression or echo cancellation. On iOS
  that means the AVAudioSession `measurement` mode. Every one of those would change the tail's level.
- **The app logs the sample at which `/play?name=daredevil_mode_activated.wav` started,** so the dry signal can be
  lined up.

## 1. The outdoor calibration (once per phone, volume and book)

1. **The site:**
   - An open field or a large empty car park, at least 10 m from walls, cars and trees.
   - Wind under about 2 m/s.
   - No traffic noise within 30 dB of the announcement's level at 1 m (check on the reference recorder).
2. **The rig:** the phone on the book on a stand at least 1.5 m above the ground. The ground reflection then arrives at
   least 6 ms after the direct sound, past the 3.3 ms self-path window.
3. **Each take:** both recorders running, then 1 s of quiet, then the announcement, then 3 s of quiet.
4. **The takes:**
   - **On axis:** 5 takes with the reference mic 1.00 m from the phone's speaker, on its axis (the direction the
     speaker faces), at the same height.
   - **For Q:** one take each with the reference mic at 1.00 m at 45°, 90°, 135° and 180° from the speaker's axis,
     horizontally. The phone's directivity Q is the on-axis level over the mean over these directions. The tail is
     driven by the total power, so r_c = sqrt(Q A / 16π) needs it.
5. **What comes out:**
   - The phone's own two-channel recordings: the self-path FIR per mic (`self_path`, the first 3.3 ms).
   - The reference recordings: the level at 1 m. Take the energy of the reference's first 3 ms after the direct
     arrival, so the ground reflection stays out.

## 2. Per room

- **The room log:**
  - Length, width and height (tape measure, to 5 cm).
  - The floor and ceiling materials, and the soft furnishings.
  - A photo from the door and one from the phone's spot.
  - Doors and windows closed. Keep the same people in the room for the whole session.
- **The recording:** one continuous recording per room, both mics. In order:
  1. **The opener.** Jay stands at a taped spot 1.0 m from the phone, faces it, and says "Activate DareDevil mode"
     after at least 1 s of quiet.
  2. **The announcement.** The phone answers. Then 3 s with nobody talking or moving, so the tail and its decay are
     clean. Repeat the announcement 3 times, triggered from the laptop, 4 s apart, to give the probe's own scatter.
  3. **The walk, facing the phone.** One fixed short phrase (say "one two three four") at taped spots. Leave at least
     1 s of silence before each phrase: an onset needs 0.3 s of quiet, and the CDR reads 0.13-0.6 s after it. The
     spots are 0.5, 1, 1.5, 2, 3 and 4 m from the phone, as far as the room allows. Use two bearings per distance (to
     the left and right of the phone's axis), so a spot isn't confused with a bearing.
  4. **The walk, turned.** At 1 m and at 2 m, the same phrase facing 90° left, 90° right and away (180°). Then facing
     the phone again at the same spot: this is the flinging test, measured.
  5. **The room's noise:** 10 s of quiet at the end.
- **The phrase log,** written as you go, not spoken into the recording: per phrase, the spot's distance (m), the
  bearing, the facing (0, 90 left, 90 right, 180), and the phrase number.
- **Rooms:** at least three, as different as possible. For example a small bedroom or bathroom (short distances,
  live), a furnished living room, and a large kitchen or hall. Add one room twice, with a door or curtain changed, as
  dEchorate's one-change test.

## 3. What each recording must contain (the checklist)

| item | why |
|---|---|
| ≥1 s quiet before the announcement | the noise floor `tail_read` subtracts |
| the announcement, its start sample logged | lining up the dry signal and the self-path |
| ≥3 s quiet after it | the decay `decay_fit` reads, and the tail's last part |
| 3 announcements | the probe's own repeat scatter |
| the opener at a measured spot, facing the phone | step 2's anchor |
| walk phrases, each after ≥1 s quiet, with the log | the line the probe predicts, and the facing table |
| room dimensions and photos | Sabine's r_c as a third opinion, and room size for the bias table |
| 10 s room noise at the end | the noise level, for the noise column |

## 4. What gets reported

- **Per room:**
  - **The probe:** r_c and the echo time, with the 3-take spread.
  - **The walk's r_c:** the CDR fitted at slope −20, and the free slope.
  - **The ratio of the two r_c values:** the simulation predicts about 0.75, from the near-source enhancement.
  - **Sabine's r_c:** from the measured volume and the probe's echo time.
- **Absolute range per walk phrase:** r = r_c,probe × 10^(−CDR/20), against the taped distance. Then the same with
  the walk's own r_c, which separates the probe's error from the estimator's.
- **Facing:** the facing table at 1 m and 2 m. Each band's CDR change, and HF − LF against the opener's.
- **Set aside any room the probe fails outright** (no decay fit, or a tail below the floor), and catalogue why.
