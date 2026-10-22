#!/usr/bin/env python3
"""Tables for results/dechorate/report.md from truth.jsonl and preds.jsonl (run_all.sh). Prints markdown.

usage: python3 analyze.py results/dechorate [measured|geometry] > /tmp/tables.md   (truth.py: which truth)
"""
import json
import statistics as st
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

import truth as truth_mod

HIT = 10.0
d = Path(sys.argv[1])
truth = {m['id']: m for m in truth_mod.read_jsonl(d / 'truth.jsonl.gz')}
preds = {p['id']: p for p in truth_mod.read_jsonl(d / 'preds.jsonl.gz')}
MODE = sys.argv[2] if len(sys.argv) > 2 else 'measured'
SCALE = truth_mod.apply(list(truth.values()), MODE)
rows = [(truth[k], preds[k]) for k in sorted(truth)]
ROOMS = ['000000', '000001', '000010', '000100', '001000', '010000', '011000', '011100', '011110', '011111', '020002']
SP = [155, 65]
rng = np.random.default_rng(0)


def med(v):
    return f'{st.median(v):.1f}' if v else '-'


def pct(v):
    return f'{100 * sum(v) / len(v):.0f}%' if v else '-'


def gcc1(p):
    return p['gcc'][0] if p.get('gcc') else None


def a2on(p):
    return p['a2'][0] if p.get('a2') else None


def a2rf(p):
    return p['a2'][1] if p.get('a2') else None


def distinct(m):
    return [e for e in m['echoes'] if e['reflective'] and abs(e['deg'] - m['truth_deg']) > HIT]


def near(x, dirs):
    return x is not None and any(abs(x - q) <= HIT for q in dirs)


def sel(room=None, sp=None, scope=False, src=None):
    return [(m, p) for m, p in rows if (room is None or m['room'] == room) and (sp is None or m['spacing_mm'] == sp)
            and (not scope or abs(m['truth_deg']) <= 60) and (src is None or m['src'] in src)]


def chance(items, fn_dirs, reads):
    """Hit rate of another source's read against this cut's directions (same spacing)."""
    hits = []
    for m, _ in items:
        dirs = fn_dirs(m)
        if not dirs:
            continue
        while True:
            j = rng.integers(len(reads))
            if reads[j][0] != m['src']:
                break
        hits.append(near(reads[j][1], dirs))
    return hits


print('## Onset, all angles and in scope (|truth| <= 60 deg)\n')
for sp in SP:
    print(f'\n**{sp} mm pairs** (864 cuts per configuration; in scope about 600)\n')
    print('| config | GccPhat median | GccPhat <=10 | Angle2 median | Angle2 <=10 | in scope: GccPhat median / <=10 | in scope: Angle2 median / <=10 |')
    print('|---|---|---|---|---|---|---|')
    for room in ROOMS + [None]:
        a, s = sel(room, sp), sel(room, sp, scope=True)
        e = lambda it, f: [abs(f(p) - m['truth_deg']) for m, p in it if f(p) is not None]
        print(f"| {room or 'all'} | {med(e(a, gcc1))} | {pct([x <= HIT for x in e(a, gcc1)])} | {med(e(a, a2on))} | "
              f"{pct([x <= HIT for x in e(a, a2on)])} | {med(e(s, gcc1))} / {pct([x <= HIT for x in e(s, gcc1)])} | "
              f"{med(e(s, a2on))} / {pct([x <= HIT for x in e(s, a2on)])} |")

print('\n## Lean toward 0 (|read| - |truth|, median deg; negative = nearer 0)\n')
BANDS = [(0, 15), (15, 30), (30, 45), (45, 60), (60, 91)]
for sp in SP:
    print(f'\n**{sp} mm**\n')
    print('| scheme, config | ' + ' | '.join(f'{lo}-{min(hi, 90)}' for lo, hi in BANDS) + ' |')
    print('|---|' + '---|' * len(BANDS))
    for name, f in (('GccPhat', gcc1), ('Angle2', a2on)):
        for label, rooms in (('ceiling absorbing (00xxxx)', ['000000', '000001', '000010', '000100', '001000']),
                             ('ceiling reflective (01xxxx, 02xxxx)', ['010000', '011000', '011100', '011110', '011111', '020002'])):
            cells = []
            for lo, hi in BANDS:
                v = [abs(f(p)) - abs(m['truth_deg']) for room in rooms for m, p in sel(room, sp)
                     if f(p) is not None and lo <= abs(m['truth_deg']) < hi]
                cells.append(f'{med(v)} (n={len(v)})')
            print(f'| {name}, {label} | ' + ' | '.join(cells) + ' |')

print('\n## Ceiling only: 000000 against 010000, same sources, pairs and speech (in scope, 15-60 deg)\n')
print('| spacing | scheme | lean, all absorbing | lean, ceiling reflective | paired change, median | ceiling echo nearer 0 than direct |')
print('|---|---|---|---|---|---|')
for sp in SP:
    base = {m['id'].split('/', 1)[1]: (m, p) for m, p in sel('000000', sp)}
    ceil = {m['id'].split('/', 1)[1]: (m, p) for m, p in sel('010000', sp)}
    for name, f in (('GccPhat', gcc1), ('Angle2', a2on)):
        l0, l1, dl, nearer = [], [], [], []
        for k, (m0, p0) in base.items():
            m1, p1 = ceil[k]
            if not 15 <= abs(m0['truth_deg']) <= 60 or f(p0) is None or f(p1) is None:
                continue
            a, b = abs(f(p0)) - abs(m0['truth_deg']), abs(f(p1)) - abs(m1['truth_deg'])
            l0.append(a); l1.append(b); dl.append(b - a)
            ce = next(e for e in m1['echoes'] if e['surface'] == 'ceiling')
            nearer.append(abs(ce['deg']) < abs(m1['truth_deg']))
        print(f'| {sp} mm | {name} | {med(l0)} | {med(l1)} | {med(dl)} (n={len(dl)}) | {pct(nearer)} |')

print('\n## First reflection: Angle2\'s second family against the labelled first-order echoes\n')
print('Hit = within 10 deg. "Distinct" = the earliest echo from a reflective surface that is more than 10 deg from the direct '
      'direction (the only kind a read can tell from the onset). Chance = another source\'s read against this cut\'s echoes.\n')
for sp in SP:
    print(f'\n**{sp} mm**\n')
    print('| config | reads | earliest distinct: hit / chance | any reflective: hit / chance | any first-order (incl. absorbing): hit / chance | same as direct | lag, median ms | earliest distinct echo delay, median ms |')
    print('|---|---|---|---|---|---|---|---|')
    for room in ROOMS + [None]:
        it = [(m, p) for m, p in sel(room, sp) if a2rf(p) is not None]
        reads = [(m['src'], a2rf(p)) for m, p in it]
        dd = lambda m: [e['deg'] for e in distinct(m)][:1]
        rr = lambda m: [e['deg'] for e in m['echoes'] if e['reflective']]
        aa = lambda m: [e['deg'] for e in m['echoes']]
        h = lambda fn: [near(a2rf(p), fn(m)) for m, p in it if fn(m)]
        c = lambda fn: chance(it, fn, reads)
        lag = [p['a2_ms'][1] - p['a2_ms'][0] for m, p in it if p['a2_ms'][1] is not None]
        dly = [distinct(m)[0]['delay_ms'] for m, p in it if distinct(m)]
        print(f"| {room or 'all'} | {len(it)} | {pct(h(dd))} / {pct(c(dd))} | {pct(h(rr))} / {pct(c(rr))} | "
              f"{pct(h(aa))} / {pct(c(aa))} | {pct([abs(a2rf(p) - m['truth_deg']) <= HIT for m, p in it])} | {med(lag)} | {med(dly)} |")

print('\n## GccPhat angles 2 and 3 against the echoes (all configurations with a reflective surface)\n')
print('| spacing | reads | earliest distinct: hit / chance | any reflective: hit / chance |')
print('|---|---|---|---|')
for sp in SP:
    it = [(m, a) for m, p in sel(None, sp) if p.get('gcc') for a in p['gcc'][1:3] if any(e['reflective'] for e in m['echoes'])]
    reads = [(m['src'], a) for m, a in it]
    dd = lambda m: [e['deg'] for e in distinct(m)][:1]
    rr = lambda m: [e['deg'] for e in m['echoes'] if e['reflective']]
    hd = [near(a, dd(m)) for m, a in it if dd(m)]
    hr = [near(a, rr(m)) for m, a in it if rr(m)]
    print(f'| {sp} mm | {len(it)} | {pct(hd)} / {pct(chance(it, dd, reads))} | {pct(hr)} / {pct(chance(it, rr, reads))} |')

print('\n## When the onset misses (> 10 deg), does it point at a reflective echo?\n')
print('| spacing | scheme | misses | on a distinct reflective echo | chance |')
print('|---|---|---|---|---|')
for sp in SP:
    for name, f in (('GccPhat', gcc1), ('Angle2', a2on)):
        it = [(m, p) for m, p in sel(None, sp) if f(p) is not None and abs(f(p) - m['truth_deg']) > HIT
              and any(e['reflective'] for e in m['echoes'])]
        dirs = lambda m: [e['deg'] for e in distinct(m)]
        reads = [(m['src'], f(p)) for m, p in it]
        print(f'| {sp} mm | {name} | {len(it)} | {pct([near(f(p), dirs(m)) for m, p in it])} | {pct(chance(it, dirs, reads))} |')

print('\n## Sources facing into the room (0-3) against facing a wall (4, 5), in scope\n')
print('| spacing | scheme | facing in: median / <=10 | facing a wall: median / <=10 |')
print('|---|---|---|---|')
for sp in SP:
    for name, f in (('GccPhat', gcc1), ('Angle2', a2on)):
        cells = []
        for src in ((0, 1, 2, 3), (4, 5)):
            e = [abs(f(p) - m['truth_deg']) for m, p in sel(None, sp, True, src) if f(p) is not None]
            cells.append(f'{med(e)} / {pct([x <= HIT for x in e])}')
        print(f'| {sp} mm | {name} | ' + ' | '.join(cells) + ' |')

print('\n## Truth check: direct-path delay measured in the RIRs against the calibrated geometry\n')
print('| pair (mics) | spacing | k (measured / geometric delay) | rms residual, geometry (samples) | rms residual after k (samples) |')
print('|---|---|---|---|---|')
for pair in sorted({tuple(m['mics']) for m, _ in rows}):
    ms = [m for m, _ in rows if tuple(m['mics']) == pair and m['clean'] == rows[0][0]['clean']]
    x = np.array([m['truth_tau_ms'] for m in ms]); y = np.array([m['rir_tau_ms'] for m in ms])
    k = (x @ y) / (x @ x)
    print(f"| {pair[0]}-{pair[1]} | {ms[0]['spacing_mm']} mm | {k:.3f} | {np.sqrt(np.mean((y - x) ** 2)) * 48:.2f} | "
          f"{np.sqrt(np.mean((y - k * x) ** 2)) * 48:.2f} |")

print('\n## Angle2\'s reflection timing: lag of the second family\'s first read after the onset family\'s\n')
print('| config | lag, 5 / 25 / 50 / 75 / 95th percentile (ms) | earliest distinct echo delay, median (ms) |')
print('|---|---|---|')
for room in ROOMS:
    it = sel(room)
    lag = [p['a2_ms'][1] - p['a2_ms'][0] for m, p in it if p.get('a2_ms') and p['a2_ms'][1] is not None]
    dly = [distinct(m)[0]['delay_ms'] for m, p in it if distinct(m)]
    print(f"| {room} | {' / '.join(f'{v:.0f}' for v in np.percentile(lag, [5, 25, 50, 75, 95]))} | {med(dly)} |")
x, y = [], []
for m, p in rows:
    if distinct(m) and p['a2_ms'][1] is not None:
        x.append(distinct(m)[0]['delay_ms']); y.append(p['a2_ms'][1] - p['a2_ms'][0])
from scipy.stats import spearmanr
print(f'\nSpearman, lag against the earliest distinct echo delay: {spearmanr(x, y)[0]:.2f} (n={len(x)})')
nores = sum(1 for m, p in rows if not p.get('a2'))
print(f'\nAngle2 returned no onset on {nores} of {len(rows)} cuts; no reflection on '
      f'{sum(1 for m, p in rows if p.get("a2") and p["a2"][1] is None)}. GccPhat errors: '
      f'{sum(1 for m, p in rows if "gcc_err" in p)}; Angle2 errors: {sum(1 for m, p in rows if "a2_err" in p)}.')
