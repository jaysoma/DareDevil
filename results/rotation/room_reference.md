# The facing reference without labels (2026-10-24)

Script: `harness/rotation/room_reference.py`; table: `room_reference.txt`. 43 stops (16 facing the phone, 27 turned 90 or
more) in 10 walks. Contrast: CDR 4-8 kHz minus CDR 0.1-1.1 kHz, pooled per stop, first 2 s of each tape skipped.

- **The reference has to come from the same session.** A quantile of the same tape's stops beats every reference
  built from the room's other walks (55-67%) and the labelled room mean (63-66%). Each session sits at its own level.
- **The headline 88% is flattering.** It comes from the tape's 75th percentile with the threshold chosen on the other
  walks. That threshold came out 0 dB every time, so the rule became "the top quarter of stops face the phone", which
  fits these walks only because 37% of their stops are facing ones. In a demo where most stops face the phone, the
  same rule would call most of them turned.
- **The rule that should carry over: the top of the spread, and a fixed drop the size of a turn.**
  - **The rule:** the reference is the tape's 90th percentile (in effect its most-facing stop), and a stop is turned
    when it reads more than 1.5 dB below it.
  - **Score:** 78% balanced (13 of 16 facing, 20 of 27 turned), against 67% for the opener.
  - **Why it should carry over:** it only needs a few facing stops in the session, not a set share of them.
- **The size of the step:** facing stops sit +0.8 dB above their tape's 75th percentile, turned ones −1.1 dB, a gap of
  about 2 dB.
