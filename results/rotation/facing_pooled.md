# Facing from pooled speech, on Jay's rotation walks (2026-10-24)

Scripts: `harness/rotation/facing_pooled.py`, `facing_vs_distance.py`, `facing_from_opener.py`. Labels:
`harness/rotation/facing_stops.json` (stops read from the decodes: one spot, one called facing). Data: each walk's
`tapes/<walk>/band_windows.json`. Numbers: the `.txt` files beside this one.

**Rerun 2026-10-24 (brief B2) without each tape's first 2 s.** Six tapes (231921, 231705, 171645, 215800, 030615,
221126) open with 0.5-1.5 s of handling: starting the recording, setting the phone down. It reads up to 31 dB over
the speech, is nearly fully coherent, and passed the speech mask. It sat inside 231705's only facing-0 stop (the
reference for all four of that spot's turned stops), inside 215800's first, and inside 221126's 1 m ladder step. The
first run's numbers are in this file's history; the changes are noted below.

## The answer
**Pooled over a stop, the CDR's high-minus-low contrast separates facing the phone from turned away, at the same spot.**
43 stops at 11 spots in 10 walks, 7.3 s of speech per stop on average:

| facing, against the same spot's facing-the-phone stops | CDR 4-8 kHz minus 0.1-1.1 kHz | reads below facing the phone |
|---|---|---|
| 90 (side) | −1.7 dB (sd 1.5) | 15 of 16 |
| 135 | −3.2 dB | 2 of 2 |
| 180 (away) | −2.7 dB (sd 1.1) | 9 of 9 spots |

The first run read −2.1 and −3.1 dB with the handling in, with spreads of 2.0 and 1.9 dB. Without it, the effect is
a little smaller and a good deal steadier.

- **Why it works now:** one half-second window jitters by 2.3 dB, as brief 20 found on LOCATA (3 dB). Fifteen windows
  at one spot bring that to about 0.6 dB, well under the effect. LOCATA's talkers walked, so they could never be
  pooled like this.
- **Why it's the CDR and not the level:** the level's own tilt (4-8 against 1.1-2 kHz) jitters 8.8 dB per window and
  doesn't separate (6 of 9 spots). The CDR is a ratio within each band, so the voice's own spectrum (which vowel, how
  loud) cancels inside it.
- **Side against away:** −1.7 against −2.7 dB, with 1-1.5 dB of spread between spots. Toward against turned is what
  this gives, not 45° steps.
- **The range statistic moves too, and less than first reported:** CdrRange's mean CDR reads 1.8 dB lower turned to
  the side and 2.5 dB lower turned away (every stop; sd 0.8 and 1.1). A turned talker is drawn about 1.2-1.3x
  farther, not the 1.5x of the first run (3.5-4 dB), which was mostly the handling in 231705's reference. That is
  below brief 20's 3.9 dB on LOCATA.

## What it doesn't do yet
- **Distance moves the contrast a little.** Facing the phone at called distances (four walks, 1-8 m), it falls
  −1.9 dB per decade on average, against −0.6 on LOCATA. The walks disagree: −6.6, +4.7, +1.3 and −6.9 dB per decade.
  Doubling the distance costs about 0.6 dB, a fifth of turning away. The first run read −3.0, with 221126's 1 m step
  holding handling. The range statistic falls −2.6 dB per decade.
- **One opener is a shaky reference.** Against each walk's first facing-the-phone stop, with the threshold chosen on
  the other walks, turned stops are caught 27 of 27, but later facing-the-phone stops only 2 of 6 (balanced 67%;
  first run 61%). Two facing stops at one spot differ by 1-3.6 dB (most in 213304 and 215800), so a single stop sets
  the reference with that error.
- **The stops were picked by hand.** The app would have to find them itself, for instance as spans where the angle
  holds.
- **Limits:** 10 walks, Jay's house, self-called facings and distances.
