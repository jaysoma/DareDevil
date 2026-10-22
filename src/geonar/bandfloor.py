"""THE BAND'S FLOOR, PER FREQUENCY, FOR THE BEARING (Jay, 2026-10-12: "So are we taking 5ms or 21ms frames" -- "Yeah let's
try it and see" -- "Sounds good. Let's see if it works.").

Angle weighs every frequency of its read by how far that frequency stands above its own floor -- what ODAS's localiser
does, and the reason its candidates found Jay at quiet onsets where an unweighted read did not (walk-203939, 56 s). Measured
on that walk's five onsets with this weighting, a 21 ms read sat within 10 deg of the mark 25 of the first 30 ms at 19 s
and 10 at 37.7 s; a 5 ms read, 9 and 1. The floor has to run through the silence before anyone speaks, and only the
Conductor hears that -- the bearing is handed nothing before an onset (Jay, 2026-10-10) -- so it is kept here and handed
over with every onset.

THE FLOOR is detect_onsets.py's rule, unchanged, run per frequency: every STEP (10 ms), in dB, floor = 0.90 floor + 0.10
level when the level is below it (down fast: a lull re-anchors it), else 0.999 floor + 0.001 level (up barely: speech
does not drag it along); it starts at the first step. The floor is the one exception to "no averaging" (Jay,
2026-10-08). THE LEVEL is Angle's own arithmetic, so the two compare like for like: the last FRAME samples, first
difference x[n] - 0.97 x[n-1], Hann, zero-filled to NFFT, each bin's power in LO_HZ..HI_HZ averaged over the two
capsules, on the capsules' own int16 scale.
"""
import math

import numpy as np

SR = 48000
FRAME, NFFT, PRE, LO_HZ, HI_HZ = 1024, 2048, 0.97, 1100, 8000      # Angle.mjs's read
STEP = 480                                                         # detect_onsets.py's 10 ms step
K = np.arange(int(math.ceil(LO_HZ * NFFT / SR)), int(math.floor(HI_HZ * NFFT / SR)) + 1)
HANN = np.hanning(FRAME)


def settings():
    return {'what': 'per-frequency floor for the bearing', 'frame': FRAME, 'nfft': NFFT, 'band_hz': [LO_HZ, HI_HZ],
            'step': STEP, 'rule': 'detect_onsets: down 0.90/0.10, up 0.999/0.001 (dB)', 'bins': int(len(K))}


class BandFloor:
    """Fed the source as the Conductor's clock advances; value() is the floor now, one dB per bin of Angle's band."""

    def __init__(self):
        self.db = None
        self.next = FRAME + 1                                      # the first step whose frame the audio holds

    def feed(self, src, now):
        while self.next <= now:
            pair = src.raw(self.next - FRAME - 1, FRAME + 1)       # one sample before, for the first difference
            if pair:
                l, r = (np.asarray(x, dtype=np.float64) for x in pair)
                fl = np.fft.rfft((l[1:] - PRE * l[:-1]) * HANN, NFFT)[K]
                fr = np.fft.rfft((r[1:] - PRE * r[:-1]) * HANN, NFFT)[K]
                lev = 10 * np.log10(0.5 * (np.abs(fl) ** 2 + np.abs(fr) ** 2) + 1e-12)
                self.db = lev if self.db is None else np.where(lev < self.db, 0.90 * self.db + 0.10 * lev,
                                                               0.999 * self.db + 0.001 * lev)
            self.next += STEP

    def value(self):
        return None if self.db is None else [round(float(v), 2) for v in self.db]
