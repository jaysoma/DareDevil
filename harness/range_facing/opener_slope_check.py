#!/usr/bin/env python3
"""CdrRange's law against brief 20's, on LOCATA's real room (2026-10-23).

CdrRange (src/schemes/CdrRange.js) sets the law's slope from the opener's own CDR, S = clamp(-0.0274 + 0.1585 cdr_open,
0.6, 1.0), fitted on one shoebox simulator. Brief 20 kept -20 (S = 1). Both are scored here on the committed animation
files: the 160 mm pair, the anchor as bake.py picks it (first lone onset facing the array within 30 deg), every later
read predicted as 10^((cdr_open - cdr) / (20 S)) and compared with the true distance ratio. Error in doublings.
"""
import glob, json, math, sys
import numpy as np

def opener_slope(v):
    return max(0.6, min(1.0, -0.0274 + 0.1585 * v))

laws = [('S = 1 (the -20 law, brief 20)', lambda v0: 1.0), ("S from the opener (CdrRange)", opener_slope),
        ('S = 0.6', lambda v0: 0.6), ('S = 1/3 (the CDR\'s own slope)', lambda v0: 1 / 3),
        ('no range: everyone at the opener', None)]
rows = {name: [] for name, _ in laws}
folder = sys.argv[1] if len(sys.argv) > 1 else 'results/animation/locata'
for f in sorted(glob.glob(f'{folder}/*_task*_recording*.json')):
    d = json.load(open(f))
    ev = [e for e in d['events'] if e['pairs'].get('160', {}).get('range')]
    anc = next((e for e in ev if not e.get('others') and abs(e['truth'].get('facing_deg', 999)) <= 30), None)
    if anc is None:
        continue
    v0, r0 = anc['pairs']['160']['range']['cdr_db'], anc['truth']['dist_m']
    for e in ev:
        if e['t'] <= anc['t']:
            continue
        v, r = e['pairs']['160']['range']['cdr_db'], e['truth']['dist_m']
        for name, law in laws:
            pred = 1.0 if law is None else 10 ** ((v0 - v) / (20 * law(v0)))
            rows[name].append((abs(math.log2(pred * r0 / r)), abs(math.log2(r / r0)) >= 1))
print(f"{'law':36s} {'reads':>5s} {'within 1.5x':>11s} {'off by 2x+':>10s} {'mean error, the rest':>21s} {'true change 2x+: mean error':>28s}")
for name, v in rows.items():
    a = np.array([x[0] for x in v]); big = np.array([x[1] for x in v]); out = a > 1
    print(f"{name:36s} {len(a):5d} {np.mean(a <= math.log2(1.5)) * 100:10.0f}% {out.sum():10d} {a[~out].mean():17.2f} dbl {a[big].mean():24.2f} dbl (n={big.sum()})")
