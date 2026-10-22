#!/usr/bin/env python3
"""Score scheme predictions on dEchorate cuts: the onset against the direct-path TDOA, the reflection against the
labelled first-order echoes. Writes a JSON summary and prints the tables.

usage: python3 dechorate_score.py META.jsonl PREDS.jsonl OUT.json [measured|geometry]   (truth.py: which truth)
META holds the cuts' truth (the cut lines without audio); PREDS the run_schemes.mjs output, matched by id.
"""
import json
import statistics as st
import sys
from collections import defaultdict

import numpy as np

HIT = 10.0          # deg: a read within this of a truth direction is a hit (as in the STARSS23 report)
TIGHT = 5.0

import truth

meta = {m['id']: m for m in truth.read_jsonl(sys.argv[1])}
truth.apply(list(meta.values()), sys.argv[4] if len(sys.argv) > 4 else 'measured')
preds = {p['id']: p for p in truth.read_jsonl(sys.argv[2])}
assert set(meta) == set(preds), 'cuts and predictions differ'
rows = [(meta[k], preds[k]) for k in sorted(meta)]


def med(v):
    return round(float(st.median(v)), 1) if v else None


def share(v):
    return round(sum(v) / len(v), 3) if v else None


BANDS = [(0, 15), (15, 30), (30, 45), (45, 60), (60, 91)]


def onset_stats(pairs):
    err = [abs(p - m['truth_deg']) for m, p in pairs]
    lean = [abs(p) - abs(m['truth_deg']) for m, p in pairs if abs(m['truth_deg']) >= 15]
    scope = [abs(p - m['truth_deg']) for m, p in pairs if abs(m['truth_deg']) <= 60]
    band = {}
    for lo, hi in BANDS:
        sel = [(m, p) for m, p in pairs if lo <= abs(m['truth_deg']) < hi]
        band[f'{lo}-{min(hi, 90)}'] = {'n': len(sel), 'median_err': med([abs(p - m['truth_deg']) for m, p in sel]),
                                      'lean': med([abs(p) - abs(m['truth_deg']) for m, p in sel])}
    # a miss (> HIT off) that lands on a reflective surface's echo direction (one more than HIT from the direct)
    miss = [(m, p) for m, p in pairs if abs(p - m['truth_deg']) > HIT]
    on_echo = [near(p, distinct(m)) for m, p in miss]
    return {'n': len(err), 'median_err': med(err), 'within5': share([e <= TIGHT for e in err]),
            'within10': share([e <= HIT for e in err]), 'lean_median_15plus': med(lean),
            'in_scope': {'n': len(scope), 'median_err': med(scope), 'within10': share([e <= HIT for e in scope])},
            'by_band': band, 'misses': len(miss), 'miss_on_echo': share(on_echo)}


def distinct(m):
    """Reflective surfaces' echo directions more than HIT from the direct one: those a read can tell from the onset."""
    return [e['deg'] for e in m['echoes'] if e['reflective'] and abs(e['deg'] - m['truth_deg']) > HIT]


def echo_sets(m):
    """The labelled first-order echo directions, filtered three ways."""
    reflective = [e for e in m['echoes'] if e['reflective']]
    apart = distinct(m)
    return {'any': [e['deg'] for e in m['echoes']],
            'reflective': [e['deg'] for e in reflective],
            'earliest_reflective': [reflective[0]['deg']] if reflective else [],
            'earliest_distinct': apart[:1]}


def near(x, dirs):
    return any(abs(x - d) <= HIT for d in dirs)


def refl_stats(items, rng):
    """items: (meta, refl_deg, lag_ms) with refl_deg not None. Chance: another cut's read (of a different source) against
    this cut's echoes."""
    out = {'n': len(items)}
    if not items:
        return out
    reads = [r for _, r, _ in items]
    srcs = [m['src'] for m, _, _ in items]
    for key in ('any', 'reflective', 'earliest_reflective', 'earliest_distinct'):
        hit, chance, n = [], [], 0
        for i, (m, r, _) in enumerate(items):
            dirs = echo_sets(m)[key]
            if not dirs:
                continue
            n += 1
            hit.append(near(r, dirs))
            j = rng.integers(len(items))
            tries = 0
            while srcs[j] == m['src'] and tries < 20:
                j = rng.integers(len(items)); tries += 1
            chance.append(near(reads[j], dirs))
        out[key] = {'n': n, 'hit': share(hit), 'chance': share(chance)}
    out['is_direct_again'] = share([abs(r - m['truth_deg']) <= HIT for m, r, _ in items])
    lag_err = []
    for m, r, lag in items:
        ref = [e for e in m['echoes'] if e['reflective']]
        if lag is not None and ref:
            lag_err.append(lag - ref[0]['delay_ms'])
    out['lag_minus_earliest_echo_ms_median'] = med(lag_err)
    out['lag_ms_median'] = med([lag for _, _, lag in items if lag is not None])
    return out


def summarise(sel, rng):
    gcc = [(m, p['gcc'][0]) for m, p in sel if p.get('gcc')]
    a2 = [(m, p['a2'][0]) for m, p in sel if p.get('a2')]
    a2r = [(m, p['a2'][1], (p['a2_ms'][1] - p['a2_ms'][0]) if p['a2_ms'][1] is not None else None)
           for m, p in sel if p.get('a2') and p['a2'][1] is not None]
    g23 = [(m, a, None) for m, p in sel if p.get('gcc') for a in p['gcc'][1:3]]
    return {'cuts': len(sel), 'gcc_onset': onset_stats(gcc), 'a2_onset': onset_stats(a2),
            'a2_no_read': len(sel) - len(a2), 'a2_refl': refl_stats(a2r, rng), 'gcc_angles23': refl_stats(g23, rng),
            'rir_vs_geometry_tdoa_us_median': med([abs(m['rir_tau_ms'] - m['truth_tau_ms']) * 1000 for m, _ in sel])}


def main():
    rng = np.random.default_rng(0)
    res = {}
    groups = defaultdict(list)
    for m, p in rows:
        # sources 4 and 5 face a wall, away from most arrays (dEchorate's "invdirectional"); 0-3 face into the room
        facing = 'away' if m['src'] in (4, 5) else 'toward'
        for room in ('all', m['room']):
            groups[(room, m['spacing_mm'], 'all')].append((m, p))
            groups[(room, m['spacing_mm'], facing)].append((m, p))
    for k in sorted(groups):
        res['|'.join(map(str, k))] = summarise(groups[k], rng)
    json.dump(res, open(sys.argv[3], 'w'), indent=1)
    for sp in sorted({m['spacing_mm'] for m, _ in rows}, reverse=True):
        print(f'\n== {sp} mm, all six sources ==')
        print('room    | GCC med  <=10 | A2 med  <=10  lean | A2 refl: n  any(ch)    rfl(ch)    first(ch)  =direct')
        for k in sorted(groups):
            if k[1] != sp or k[2] != 'all':
                continue
            s = res['|'.join(map(str, k))]
            g, a, r = s['gcc_onset'], s['a2_onset'], s['a2_refl']
            f = lambda d: f"{d['hit']:.2f}({d['chance']:.2f})" if d and d.get('hit') is not None else '   -      '
            print(f"{k[0]:7} | {g['median_err']:5} {g['within10']:5.2f} | {a['median_err']:5} {a['within10']:5.2f} "
                  f"{a['lean_median_15plus']!s:>5} | {r['n']:5} {f(r.get('any'))} {f(r.get('reflective'))} "
                  f"{f(r.get('earliest_reflective'))} {r.get('is_direct_again')}")


if __name__ == '__main__':
    main()
