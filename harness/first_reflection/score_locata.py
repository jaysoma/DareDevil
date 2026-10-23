#!/usr/bin/env python3
"""Brief 8 on LOCATA: Angle2.readSound on batch A's talker onsets (results/batchA/locata/truth.jsonl, same ids).

LOCATA labels no echoes, but two follow from the tracked head and the array (truth `head`, `centre`; mic positions from
the release's position_array files):
  floor     the mouth (MOUTH_BELOW m under the head marker, as brief 10) mirrored in z = 0
  ceiling   mirrored in z = ROOM_H: the room is 7.1 x 9.8 x 3 m (Evers et al., "The LOCATA Challenge", 2020,
            arXiv 1909.01008), with z = 0 taken as the floor (heads track at 1.36-1.64 m, the array at 1.30 m)
The walls can't be placed: the release does not say where they are in the tracker's coordinates.
An echo's lag is (path via the image - direct path) / c at the pair's centre; its angle is the image's exact two-mic
delay in the schemes' convention.

  ONSET     readSound's onset angle under Jay's rule (scenario: recording, talker, pair), catalogued.
  LAG       gap_ms within LAG_HIT ms of the floor's (or ceiling's) lag; angle within 10 deg of that echo; both.
            Chance: another talker's decided read against this cut's lags.
  RANGE     whether gap_ms orders distance, as batch A scored its range cues (same talker, same recording and pair;
            pairs of cuts 1.25x, 1.5x and 2x apart; spread within 0.3 m of one spot), next to the CDR (batch A's
            range.jsonl) on the same cuts, and next to the true floor lag scored the same way: what a perfect floor-echo
            reader would get.

usage: python3 score_locata.py WORK_DIR BATCHA_LOCATA_DIR LOCATA_DATA OUT_DIR   (WORK_DIR: sound_*.jsonl)
"""
import itertools
import json
import math
import statistics as st
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'scoring'))
import clean_score as cs  # noqa: E402

C = 343.0
MOUTH_BELOW, ROOM_H = 0.12, 3.0
ANGLE_HIT, LAG_HIT = 10.0, 0.25
MIN_GAP, MAX_GAP = 1.0, 12.0
RATIOS = {'1.25x': (1.15, 1.35), '1.5x': (1.4, 1.6), '2x': (1.8, 2.2)}
SPOT_M = 0.3


def pct(v):
    return round(100 * sum(v) / len(v), 1) if v else None


def lateral(src, ml, mr):
    d = np.linalg.norm(mr - ml)
    tau = (np.linalg.norm(src - mr) - np.linalg.norm(src - ml)) / C
    return math.degrees(math.asin(max(-1.0, min(1.0, -tau * C / d))))


def mics_of(data, t):
    a = pd.read_csv(Path(data) / t['set'] / t['task'] / t['recording'] / 'dicit' / 'position_array_dicit.txt', sep='\t',
                    nrows=1).iloc[0]
    return [np.array([a[f'mic{i}_x'], a[f'mic{i}_y'], a[f'mic{i}_z']]) for i in t['mics']]


def echoes(t, ml, mr):
    P = np.array(t['centre'])
    m = np.array(t['truth']['head'], float)
    m[2] -= MOUTH_BELOW
    out = {}
    for name, z in (('floor', -m[2]), ('ceiling', 2 * ROOM_H - m[2])):
        im = np.array([m[0], m[1], z])
        out[name] = {'delay_ms': (np.linalg.norm(im - P) - np.linalg.norm(m - P)) / C * 1000,
                     'deg': lateral(im, ml, mr)}
    return out


def order(rows, cue, nearer_is_larger=True):
    """Batch A's ordering and spread for one cue over rows that have it."""
    by = defaultdict(list)
    for r in rows:
        if r.get(cue) is not None:
            by[r['who']].append(r)
    o = {k: [] for k in RATIOS}
    spot, step = [], []
    sign = 1 if nearer_is_larger else -1
    for rs in by.values():
        for a, b in itertools.combinations(rs, 2):
            near, far = (a, b) if a['dist_m'] < b['dist_m'] else (b, a)
            ratio = far['dist_m'] / max(near['dist_m'], 1e-6)
            for k, (lo, hi) in RATIOS.items():
                if lo <= ratio <= hi:
                    o[k].append(sign * (near[cue] - far[cue]) > 0)
            if 1.8 <= ratio <= 2.2:
                step.append(abs(near[cue] - far[cue]))
            if math.dist(a['head'][:2], b['head'][:2]) <= SPOT_M:
                spot.append(abs(a[cue] - b[cue]))
    return {'ordering_pct': {k: pct(v) for k, v in o.items()}, 'ordering_pairs': {k: len(v) for k, v in o.items()},
            'spread_one_spot': round(st.median(spot), 3) if spot else None, 'spot_pairs': len(spot),
            'step_2x': round(st.median(step), 3) if step else None}


def main():
    work, batch, data, out = (Path(a) for a in sys.argv[1:5])
    out.mkdir(parents=True, exist_ok=True)
    truth = {t['id']: t for t in map(json.loads, open(batch / 'truth.jsonl'))}
    cdr = {r['id']: r['cdr_db'] for r in map(json.loads, open(batch / 'range.jsonl'))}
    reads = {}
    for p in sorted(work.glob('sound_*.jsonl')):
        for l in open(p):
            q = json.loads(l)
            reads[q['id']] = q
    assert set(reads) == set(truth), 'reads and batch A truth differ'
    mic_cache = {}
    rows = []
    for k, t in truth.items():
        key = (t['set'], t['task'], t['recording'], tuple(t['mics']))
        if key not in mic_cache:
            mic_cache[key] = mics_of(data, t)
        ml, mr = mic_cache[key]
        e = echoes(t, ml, mr)
        q = reads[k]
        rows.append({'id': k, 'pair_mm': t['pair_mm'], 'who': f"{t['set']}/{t['task']}/{t['recording']}/{t['talker']}",
                     'scenario': t['scenario'], 'truth_deg': t['truth']['deg'], 'dist_m': t['truth']['dist_m'],
                     'head': t['truth']['head'], 'alone': not t['truth']['others'],
                     'facing_deg': t['truth']['facing_deg'], 'echo': e,
                     'floor_ms': e['floor']['delay_ms'], 'cdr_db': cdr.get(k), 'q': q,
                     'gap_ms': q.get('gap_ms') if q.get('decided') else None})
    summary = {'n_cuts': len(rows), 'errors': sum('err' in r['q'] for r in rows),
               'no_sound': sum(r['q'].get('sound') is None for r in rows)}
    # ---- onset under Jay's rule ----
    data_rule = {}
    for sp in (160, 80):
        data_rule[sp] = {'readSound onset': [dict(id=r['id'], scenario=r['scenario'], truth=r['truth_deg'],
                                                  read=r['q']['onset']['deg'],
                                                  others=[r['q']['refl']['deg']] if r['q'].get('refl') else [],
                                                  ctx={'decided': r['q'].get('decided'), 'gap_ms': r['gap_ms'],
                                                       'why': r['q'].get('why'), 'alone': r['alone'],
                                                       'facing_deg': r['facing_deg']})
                                             for r in rows if r['pair_mm'] == sp and r['q'].get('onset')]}
        summary[f'onset_rule_{sp}mm'] = cs.run(f'locata_onset_{sp}mm', data_rule[sp], out)['readSound onset']
    kept = set()
    for sp in (160, 80):
        _, kp, _, _, _ = cs.clean([dict(r) for r in data_rule[sp]['readSound onset']])
        kept |= {r['id'] for r in kp}
    # ---- the lag (and angle) against the floor and ceiling ----
    rng = np.random.default_rng(0)
    res = {}
    for sp in (160, 80):
        sc = [r for r in rows if r['pair_mm'] == sp and abs(r['truth_deg']) <= cs.SCOPE and r['q'].get('onset')]
        dec = [r for r in sc if r['q'].get('decided')]
        why = Counter(r['q'].get('why') for r in sc if not r['q'].get('decided'))
        for label, items in (('kept_onsets', [r for r in dec if r['id'] in kept]), ('all_in_scope', dec)):
            s = {'decided_pct': pct([bool(r['q'].get('decided')) for r in sc]), 'decided_reads': len(items)}
            for name in ('floor', 'ceiling', 'either'):
                names = ['floor', 'ceiling'] if name == 'either' else [name]
                lag, ang, both, ch = [], [], [], []
                for r in items:
                    es = [r['echo'][n] for n in names]
                    g, a = r['gap_ms'], r['q']['refl']['deg']
                    lag.append(any(abs(g - e['delay_ms']) <= LAG_HIT for e in es))
                    ang.append(any(abs(a - e['deg']) <= ANGLE_HIT for e in es))
                    both.append(any(abs(g - e['delay_ms']) <= LAG_HIT and abs(a - e['deg']) <= ANGLE_HIT for e in es))
                    while True:
                        o = items[rng.integers(len(items))]
                        if o['who'] != r['who']:
                            break
                    ch.append(any(abs(o['gap_ms'] - e['delay_ms']) <= LAG_HIT for e in es))
                s[name] = {'lag_hit_pct': pct(lag), 'lag_chance_pct': pct(ch), 'angle_hit_pct': pct(ang),
                           'both_hit_pct': pct(both)}
            s['floor_distinct_from_direct_pct'] = pct([abs(r['echo']['floor']['deg'] - r['truth_deg']) > ANGLE_HIT for r in items])
            s['gap_minus_floor_ms'] = {p: round(float(np.percentile([r['gap_ms'] - r['floor_ms'] for r in items], p)), 3)
                                       for p in (5, 25, 50, 75, 95)} if items else None
            s['floor_ms'] = {p: round(float(np.percentile([r['floor_ms'] for r in items], p)), 3) for p in (5, 50, 95)} if items else None
            s['ceiling_ms'] = {p: round(float(np.percentile([r['echo']['ceiling']['delay_ms'] for r in items], p)), 3)
                               for p in (5, 50, 95)} if items else None
            res[f'{label}|{sp}'] = s
        res[f'undecided_why|{sp}'] = dict(why.most_common())
    summary['lag'] = res
    # ---- range from the echo ----
    rng_res = {}
    for sp in (160, 80):
        dec = [r for r in rows if r['pair_mm'] == sp and r['gap_ms'] is not None]
        allr = [r for r in rows if r['pair_mm'] == sp]
        rng_res[f'{sp}mm'] = {
            'readSound gap_ms (decided reads)': order(dec, 'gap_ms'),
            'CDR, same decided cuts': order(dec, 'cdr_db'),
            'true floor lag, same decided cuts': order(dec, 'floor_ms'),
            'true floor lag, every cut': order(allr, 'floor_ms'),
            'CDR, every cut': order(allr, 'cdr_db')}
    summary['range'] = rng_res
    (out / 'locata_summary.json').write_text(json.dumps(summary, indent=1))
    with open(out / 'locata_reads.jsonl', 'w') as fh:
        for r in rows:
            q = r['q']
            fh.write(json.dumps({'id': r['id'], 'truth_deg': r['truth_deg'], 'dist_m': r['dist_m'], 'kept': r['id'] in kept,
                                 'floor': {kk: round(v, 3) for kk, v in r['echo']['floor'].items()},
                                 'ceiling': {kk: round(v, 3) for kk, v in r['echo']['ceiling'].items()},
                                 **{kk: q.get(kk) for kk in ('decided', 'onset', 'refl', 'gap_ms', 'why', 'sound')}}) + '\n')
    print(json.dumps({k: v for k, v in summary.items() if k not in ('range',)}, indent=1)[:3500])


if __name__ == '__main__':
    main()
