#!/usr/bin/env python3
"""The phone side, from the committed ODAS runs (tapes/*/odas.json): in the house tapes' pauses, where does ODAS's
tallest pot (its per-frame SRP-PHAT peak) sit, and how does that depend on the pot's energy? Pauses are the gaps
between Whisper segments, GUARD_S clear of each. Compare with pause_gcc.py's 'strength' split on STARSS23.

    python3 odas_tapes.py tapes_dir out.json
"""
import json
import sys
from pathlib import Path

import numpy as np

GUARD_S, NEAR0 = 0.5, 6.0


def main():
    tapes, out = Path(sys.argv[1]), Path(sys.argv[2])
    az, en, trk, per_tape = [], [], [], {}
    for f in sorted(tapes.glob('*/odas.json')):
        d = json.load(open(f))
        segs = json.load(open(f.parent / 'transcript.json'))['segments']
        hop = d['hop_s']
        a_t, e_t = [], []
        for ts, tracks, pots in d['frames']:
            t = ts * hop
            if any(s['t0'] - GUARD_S <= t <= s['t1'] + GUARD_S for s in segs):
                continue
            if pots:
                p = max(pots, key=lambda q: q[1])
                a_t.append(p[0]); e_t.append(p[1])
            trk += [x[1] for x in tracks if x[2] > d['settings']['theta_inactive']]
        a_t = np.array(a_t)
        if len(a_t):
            per_tape[f.parent.name] = {'pause_frames': len(a_t), 'top_pot_near0_pct': round(100 * float((abs(a_t) < NEAR0).mean()), 1)}
        az += list(a_t); en += e_t
    az, en, trk = np.array(az), np.array(en), np.array(trk)
    q = np.quantile(en, [0.25, 0.5, 0.75])
    bands = list(zip([0, *q], [*q, np.inf]))
    res = {'pause_frames': len(az), 'guard_s': GUARD_S,
           'top_pot_near0_pct': round(100 * float((abs(az) < NEAR0).mean()), 1),
           'top_pot_exactly0_pct': round(100 * float((az == 0).mean()), 1),
           'by_energy_quartile': [{'E': [round(float(lo), 3), None if hi == np.inf else round(float(hi), 3)],
                                   'near0_pct': round(100 * float((abs(az[(en >= lo) & (en < hi)]) < NEAR0).mean()), 1),
                                   'exactly0_pct': round(100 * float((az[(en >= lo) & (en < hi)] == 0).mean()), 1)}
                                  for lo, hi in bands],
           'active_tracks': len(trk), 'active_tracks_near0_pct': round(100 * float((abs(trk) < NEAR0).mean()), 1),
           'per_tape': per_tape}
    json.dump(res, open(out, 'w'), indent=1)
    print(json.dumps({k: v for k, v in res.items() if k != 'per_tape'}, indent=1))


if __name__ == '__main__':
    main()
