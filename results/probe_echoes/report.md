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
- **Direction is where two mics fail.** A found echo's angle is 24-47 deg off on average, with front and back already
  folded together (the book's job). Brief 8 found the same for the talker's own reflections.
- **So what comes out is distances, not walls:** "something hard about 1.6 m away", not where it is.
- **Not tested here:**
  - **Speaker placement:** dEchorate's loudspeakers stand 1-4 m from the arrays. On the phone the speaker is on the
    array, so the direct sound is 30-40 dB above a wall 2 m away, not 0-25 dB. The picking would have to work
    against the tail, not the direct sound.
  - **The phone body:** it carries the speaker's vibration straight to the mics.
  - **The book:** it reflects inside the first half millisecond, so it merges with the direct sound.
