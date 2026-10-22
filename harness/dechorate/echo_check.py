#!/usr/bin/env python3
"""How loud is each labelled first-order echo in the measured RIRs, per wall configuration? For every calibrated source
(0-5) and mic (0-29): the RIR's peak within +-3 samples of the image source's arrival, over the peak within +-3 samples
of the direct arrival, in dB; the median over source-mic pairs where that echo is at least 1 ms clear of the direct sound
and of every other first-order echo. The processed RIRs are aligned so the direct path sits at its time of flight.

usage: python3 echo_check.py DATA_DIR OUT.json
"""
import json
import sys
from pathlib import Path

import h5py
import numpy as np

from dechorate_cut import C_ROOM, ORDER, SR, image
from safe_pickle import load_echo_notes

data = Path(sys.argv[1])
notes = load_echo_notes(data / 'dEchorate_echo_notes.pkl')
mics, srcs = notes['mics'].T, notes['srcs'].T
f = h5py.File(data / 'dechorate_rir_processed.hdf5', 'r')
peak = lambda h, t: np.abs(h[max(0, t - 3):t + 4]).max()
out = {}
for room in f:
    H = f[room][()]
    res = {s: [] for s in ORDER}
    for j, s in enumerate(srcs):
        for i, m in enumerate(mics):
            h = H[:, i, j]
            t0 = np.linalg.norm(s - m) / C_ROOM
            ts = {w: np.linalg.norm(image(s, w) - m) / C_ROOM for w in ORDER}
            d = peak(h, int(round(t0 * SR)))
            for w in ORDER:
                others = [t0] + [ts[v] for v in ORDER if v != w]
                if min(abs(ts[w] - o) for o in others) < 1e-3:
                    continue
                res[w].append(20 * np.log10(peak(h, int(round(ts[w] * SR))) / d))
    out[room] = {w: {'median_db': round(float(np.median(v)), 1), 'n': len(v)} for w, v in res.items()}
    print(room, '  '.join(f"{w} {out[room][w]['median_db']:6.1f}" for w in ORDER))
json.dump(out, open(sys.argv[2], 'w'), indent=1)
