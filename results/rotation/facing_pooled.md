# Facing from pooled speech, on Jay's rotation walks (2026-10-24)

Scripts: `harness/rotation/facing_pooled.py`, `facing_vs_distance.py`, `facing_from_opener.py`. Labels:
`harness/rotation/facing_stops.json` (stops read from the decodes: one spot, one called facing). Data: each walk's
`tapes/<walk>/band_windows.json`. Numbers: the `.txt` files beside this one.

## The answer
**Pooled over a stop, the CDR's high-minus-low contrast separates facing the phone from turned away, at the same spot.**
43 stops at 11 spots in 10 walks, 7.3 s of speech per stop on average:

| facing, against the same spot's facing-the-phone stops | CDR 4-8 kHz minus 0.1-1.1 kHz | reads below facing the phone |
|---|---|---|
| 90 (side) | −2.1 dB | 15 of 16 |
| 135 | −2.7 dB | 2 of 2 |
| 180 (away) | −3.1 dB | 9 of 9 spots |

- **Why it works now:** one half-second window jitters by 2.4 dB, as brief 20 found on LOCATA (3 dB). Fifteen windows
  at one spot bring that to about 0.6 dB, well under the effect. LOCATA's talkers walked, so they could never be
  pooled like this.
- **Why it's the CDR and not the level:** the level's own tilt (4-8 against 1.1-2 kHz) jitters 8.7 dB per window and
  doesn't separate (5 of 9 spots). The CDR is a ratio within each band, so the voice's own spectrum (which vowel, how
  loud) cancels inside it.
- **Side against away:** −2.1 against −3.1 dB, with 2 dB of spread between spots. Toward against turned is what this
  gives, not 45° steps.
- **The range statistic moves too:** CdrRange's mean CDR reads 3.5 dB lower turned to the side and 4.0 dB lower turned
  away (every stop), so a turned talker is drawn about 1.5x farther, as brief 20 measured (3.9 dB).

## What it doesn't do yet
- **Distance moves the contrast a little.** Facing the phone at called distances (four walks, 1-8 m), it falls
  −3.0 dB per decade on average, against −0.6 on LOCATA. Doubling the distance costs about 0.9 dB, a third of
  turning away.
- **One opener is a shaky reference.** Against each walk's first facing-the-phone stop, with the threshold chosen on
  the other walks: turned stops are caught 24 of 27, but later facing-the-phone stops only 2 of 6 (balanced 61%). Two
  facing stops at one spot differ by 1-5 dB in some walks (215800, 213304), so a single stop sets the reference
  with that error.
- **The stops were picked by hand.** The app would have to find them itself, for instance as spans where the angle
  holds.
- **Limits:** 10 walks, Jay's house, self-called facings and distances.
