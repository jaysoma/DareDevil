#!/usr/bin/env python3
"""The confound check for facing_pooled.py (2026-10-24): facing the phone, does the facing cue move with distance?

Facing-the-phone stops at called distances, from the three walks that step out (213304, 221126, 020305) and one that
steps between spots (224302). Per walk, each feature is fitted against log10 distance; a facing cue that doesn't move
with distance has a slope near 0 dB per decade, where the range statistic should fall.
"""
import json
from pathlib import Path

import numpy as np

from facing_pooled import FEATS, REPO, feats, lin

LADDERS = {  # walk: [t0, t1, called distance m], all facing the phone
    'walk-213304': [[4, 20, 2], [20, 42, 3], [42, 63, 5], [63, 78, 7]],
    'walk-221126': [[0, 12, 1], [12, 21, 2], [21, 29, 3], [29, 36, 4], [36, 43, 5], [43, 47, 6], [47, 59, 7], [59, 66, 8]],
    'walk-020305': [[2, 18, 1], [18, 54, 2], [54, 90, 3.5]],
    'walk-224302': [[0, 13, 4.5], [13, 35, 2], [35, 78, 6]],
}
out = []
slopes = {k: [] for k in FEATS}
for walk, steps in LADDERS.items():
    bw = json.loads((REPO / 'tapes' / walk / 'band_windows.json').read_text())
    t0 = np.array(bw['t0']); D, R, P = lin(bw['dir_db']), lin(bw['dif_db']), lin(bw['pow_db'])
    tot = 10 * np.log10(P[:, 1:].sum(1)); voiced = tot >= np.percentile(tot, 20) + 10
    rows = []
    for a, b, dist in steps:
        m = voiced & (t0 >= a) & (t0 + bw['win_s'] <= b)
        if m.sum() >= 2:
            rows.append((dist, feats(D[m], R[m], P[m], m.sum())))
    x = np.log10([r[0] for r in rows])
    line = f"{walk[5:]} ({len(rows)} distances, {min(r[0] for r in rows)}-{max(r[0] for r in rows)} m):"
    for k in FEATS:
        y = np.array([r[1][k] for r in rows]); s = np.polyfit(x, y, 1)[0]
        slopes[k].append(s); line += f"  {k.split(' (')[0]} {s:+.1f}"
    out.append(line + '  dB per decade')
out.append('mean slope over the four walks, dB per decade: ' +
           ', '.join(f"{k.split(' (')[0]} {np.mean(v):+.1f}" for k, v in slopes.items()))
txt = '\n'.join(out)
(REPO / 'results/rotation/facing_vs_distance.txt').write_text(txt + '\n')
print(txt)
