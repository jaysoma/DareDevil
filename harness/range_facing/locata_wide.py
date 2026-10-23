#!/usr/bin/env python3
"""Brief 20: LOCATA cuts on a wide DICIT pair, mics 3-12 (640 mm, centred on mic 7 as the phone-width pairs are), so
the LF band (0.1-1 kHz) is readable down to c/2d = 268 Hz: the physics check on the brief's LF yardstick, which the
phone's 157 mm pair can't read (floored at 1.1 kHz). Same onsets and truth as batchA/locata/locata_cut.py, which
this runs with only its pair table changed.
usage: python3 locata_wide.py DATA_DIR OUT_DIR
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'batchA' / 'locata'))
import locata_cut    # noqa: E402

locata_cut.PAIRS = {640: (3, 12)}

if __name__ == '__main__':
    locata_cut.main()
