#!/usr/bin/env python3
"""Brief 20 step 1: what dEchorate's own RIRs say, per wall setting, to set the CDR reads against.

  t60: the echo time per band (Schroeder, T20 x 3), median over every source (0-5) on mics 0 and 3 of each array (the
       cuts' 155 mm pairs), 72 RIRs per band;
  drr: the true DRR per source and array, per band: the direct peak +-1 ms against everything after it, both mics'
       energies summed (the six inverted capsules don't matter to energy).
usage: dechorate_rir.py <dechorate_rir_processed.hdf5> > rir.json
"""
import json
import sys

import h5py
import numpy as np
from scipy.signal import butter, sosfiltfilt

SR = 48000
BANDS = {'LF': (100.0, 1000.0), 'MF': (1000.0, 4000.0), 'HF': (4000.0, 8000.0), 'ALL': (100.0, 8000.0)}


def t60(h):
    e = np.cumsum((h ** 2)[::-1])[::-1]
    db = 10 * np.log10(e / e[0] + 1e-30)
    i5, i25 = int(np.argmax(db < -5)), int(np.argmax(db < -25))
    return 3 * (i25 - i5) / SR if i25 > i5 else None


def main():
    H = h5py.File(sys.argv[1], 'r')
    out = {}
    for room in sorted(H):
        R = H[room][()]
        res = {}
        for b, (lo, hi) in BANDS.items():
            sos = butter(4, [lo, hi], btype='band', fs=SR, output='sos')
            v = [t60(sosfiltfilt(sos, R[:, 5 * a + m, s])) for s in range(6) for a in range(6) for m in (0, 3)]
            v = [x for x in v if x]
            res[b] = round(float(np.median(v)), 3)
        drr = {}
        for b, (lo, hi) in BANDS.items():
            sos = butter(4, [lo, hi], btype='band', fs=SR, output='sos')
            for s in range(6):
                for a in range(6):
                    d = f = 0.0
                    for m in (0, 3):
                        h = R[:, 5 * a + m, s]
                        pk = int(np.argmax(np.abs(h)))
                        hb = sosfiltfilt(sos, h)
                        w = SR // 1000
                        d += float(np.sum(hb[max(0, pk - w):pk + w] ** 2)); f += float(np.sum(hb[pk + w:] ** 2))
                    drr.setdefault(f's{s}/a{a}', {})[b] = round(10 * np.log10(d / f), 2)
        out[room] = {'t60': res, 'drr': drr}
        print(room, res, file=sys.stderr)
    print(json.dumps(out, indent=1))


if __name__ == '__main__':
    main()
