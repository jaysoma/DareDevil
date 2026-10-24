# Walls from the phone's own announcement, tried on dEchorate (2026-10-24)

Script: `harness/dechorate/probe_echoes.py`. Numbers: `summary.txt`. The announcement (`probe/daredevil_mode_activated.wav`)
was played through dEchorate's measured responses for the 155 mm pairs (396 setups: 6 sources x 6 arrays x 11 wall
settings), with noise 45 dB under it, then divided back out to recover the room's response. Echoes were picked from
that (the 8 strongest peaks 0.8-25 ms after the direct sound, within 25 dB of it) and matched to the labelled
first-order echoes within 0.35 ms.

- **The announcement is a good enough probe.** Echoes picked through it match the labelled walls as often as echoes
  picked from the true measured response (59% against 58% of reflective surfaces). Dividing out 1.4 s of TTS loses
  nothing that matters here.
- **The picking is the weak part, not the probe.**
  - **Reflective against absorbent:** reflective surfaces are found 59% of the time and absorbent ones 42%, against
    roughly 23% by chance. Only 34% of the picked peaks sit on a labelled first-order echo; the rest are
    higher-order echoes, furniture and the other arrays.
  - **The ceiling** is the clear one (85%), being early (2.7 ms) and alone. The walls, at 10-13 ms, are found 28-54%
    of the time.
- **Direction, corrected 2026-10-24.** The first run's angles were wrong: the echo cross-correlation's lags were
  scaled 16x too small, so every echo read near broadside. Fixed, a found echo's angle is off by 6 deg on average
  for the ceiling, and 14-26 deg for the walls (front and back folded together).
- **Left, front or right** (`probe_sectors.py`, `sectors.txt`; front within 30 deg of broadside; the left/right sign
  calibrated on the direct paths, 96% agreeing):
  - **Overall:** the sector is right for 53% of found wall echoes through the announcement, against 35% for
    always guessing the commonest sector. That matches the true response (51%), so the probe isn't the limit.
  - **Front holds:** 52 of 56 front walls read front.
  - **The side walls are pulled to the middle:** 35 of 61 left and 31 of 58 right walls read front. When a read
    does say left or right, its side is right about 3 times in 4 (40 of 53).
  - **Why:** a 1 ms window around a side wall's echo also holds nearer-broadside arrivals.
- **So what comes out is distances, plus a rough side:** "something hard about 1.6 m away, probably in front".
- **Not tested here:**
  - **Speaker placement:** dEchorate's loudspeakers stand 1-4 m from the arrays. On the phone the speaker is on the
    array, so the direct sound is 30-40 dB above a wall 2 m away, not 0-25 dB. The picking would have to work
    against the tail, not the direct sound.
  - **The phone body:** it carries the speaker's vibration straight to the mics.
  - **The speaker sits right next to the bottom mic (Jay):** the bottom mic hears the direct sound some 20 dB
    louder than the top one, may clip, and a small speaker driven loud distorts. Dividing out the announcement
    assumes neither happens. Calibrating each mic's own path from the speaker once (open space, book on) is what
    removes it.
  - **The book:** it reflects inside the first half millisecond, so it merges with the direct sound.
