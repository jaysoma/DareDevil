#!/usr/bin/env python3
"""The app's version of facing_pooled.py (2026-10-24): each stop against the walk's FIRST facing-0 stop (the opener's
role), toward (0) against turned (90, 135, 180), with a threshold chosen on the other walks (left out by walk)."""
import json
import numpy as np
from facing_pooled import HANDLING_S, REPO, feats, lin

K = 'CDR hi - lo (4-8 vs 0.1-1.1 kHz)'
lab = json.loads((REPO / 'harness/rotation/facing_stops.json').read_text())['stops']
per = {}
for walk, spots in lab.items():
    bw = json.loads((REPO / 'tapes' / walk / 'band_windows.json').read_text())
    t0 = np.array(bw['t0']); D, R, P = lin(bw['dir_db']), lin(bw['dif_db']), lin(bw['pow_db'])
    tot = 10 * np.log10(P[:, 1:].sum(1)); voiced = (tot >= np.percentile(tot, 20) + 10) & (t0 >= HANDLING_S)
    st = sorted((a, b, fd) for s, v in spots.items() if s != 'dist_m' for a, b, fd in v)
    vals = []
    for a, b, fd in st:
        m = voiced & (t0 >= a) & (t0 + bw['win_s'] <= b)
        if m.sum() >= 2:
            vals.append((a, fd, feats(D[m], R[m], P[m], m.sum())[K]))
    ref = next((v for v in vals if v[1] == 0), None)
    if ref and len(vals) > 1:
        per[walk] = [(fd, x - ref[2]) for a, fd, x in vals if (a, fd, x) != ref]
tp = fn = tn = fp = 0
for w in per:
    train = [p for o, v in per.items() if o != w for p in v]
    cands = sorted({x for _, x in train})
    def bal(th):
        t = [x >= th for fd, x in train if fd == 0]; u = [x < th for fd, x in train if fd != 0]
        return (np.mean(t) if t else 0) / 2 + (np.mean(u) if u else 0) / 2
    th = max(cands, key=bal)
    for fd, x in per[w]:
        if fd == 0: tp += x >= th; fn += x < th
        else: tn += x < th; fp += x >= th
txt = (f"{len(per)} walks; each stop against the walk's first facing-phone stop; threshold left out by walk\n"
       f"facing the phone, called toward: {tp} of {tp + fn}\nturned (90-180), called turned: {tn} of {tn + fp}\n"
       f"balanced accuracy {(tp / (tp + fn) + tn / (tn + fp)) / 2 * 100:.0f}% (chance 50%)")
(REPO / 'results/rotation/facing_from_opener.txt').write_text(txt + '\n'); print(txt)
