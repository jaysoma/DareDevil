#!/usr/bin/env python3
"""Tables for results/batchA/locata/report.md, from reads.jsonl, truth.jsonl and the summaries build_records.py and
range_cues.py wrote. Prints markdown.

usage: python3 analyze.py OUT_DIR > tables.md
"""
import json
import math
import statistics as st
import sys
from pathlib import Path

import numpy as np
from scipy.stats import rankdata

out = Path(sys.argv[1])
reads = [json.loads(l) for l in open(out / 'reads.jsonl')]
truth = {t['id']: t for t in map(json.loads, open(out / 'truth.jsonl'))}
SCOPE, HIT, OUT = 75.0, 10.0, 36.0
SP = [160, 80]
BANDS = [(0, 15), (15, 30), (30, 45), (45, 60), (60, 75.01)]
NAMES = ['mirror', 'endfire_pin', 'pause_direction', 'another_source', 'zero_pull', 'aliasing_partner',
         'truth_was_2nd_3rd', 'drift', 'facing', 'other']


def gread(r):
    return r['gcc']['angles'][0] if r['gcc'] else None


def aread(r):
    return r['a2']['deg'] if r['a2'] else None


SCHEMES = {'GccPhat': gread, 'Angle2': aread}


def pct(v):
    return f'{100 * sum(v) / len(v):.0f}%' if v else '-'


def scope(sp=None):
    return [r for r in reads if abs(r['truth']['deg']) <= SCOPE and (sp is None or r['pair_mm'] == sp)]


print('## The data\n')
print('| set | task | recordings | talkers | onsets (per pair) | with another talker active | facing > 120 deg | distance, median (m) |')
print('|---|---|---|---|---|---|---|---|')
for s in ('dev', 'eval'):
    for task in ('task3', 'task4'):
        ts = [truth[r['id']] for r in reads if r['pair_mm'] == 160 and truth[r['id']]['set'] == s and truth[r['id']]['task'] == task]
        if not ts:
            continue
        print(f"| {s} | {task[-1]} | {len({t['recording'] for t in ts})} | {len({(t['recording'], t['talker']) for t in ts})} | "
              f"{len(ts)} | {pct([bool(t['truth']['others']) for t in ts])} | "
              f"{pct([t['truth']['facing_deg'] is not None and t['truth']['facing_deg'] > 120 for t in ts])} | "
              f"{st.median(t['truth']['dist_m'] for t in ts):.2f} |")
r160 = [r for r in reads if r['pair_mm'] == 160]
print(f"\nIn scope (|truth| <= 75 deg): {len(scope(160))} of {len(r160)} onsets per pair. "
      f"Truth moved across the half second (|deg_end - deg|), median "
      f"{st.median(abs(truth[r['id']]['truth']['deg_end'] - r['truth']['deg']) for r in r160):.1f} deg, 90th percentile "
      f"{np.percentile([abs(truth[r['id']]['truth']['deg_end'] - r['truth']['deg']) for r in r160], 90):.1f}.")

print('\n## Sign and replica checks\n')
for sp in SP:
    rs = scope(sp)
    for name, f in SCHEMES.items():
        e1 = [abs(f(r) - r['truth']['deg']) for r in rs if f(r) is not None]
        e2 = [abs(f(r) + r['truth']['deg']) for r in rs if f(r) is not None]
        print(f'- {sp} mm, {name}: median error {st.median(e1):.1f} deg with the convention as computed, '
              f'{st.median(e2):.1f} flipped.')
ck = json.load(open(out / 'summary.json'))['checks']
print(f"- GccPhat's lock rebuilt here (for the vote total) equals the stream's angle 1 on {ck['replica_agrees']} of "
      f"{ck['gcc_reads']} reads. Scheme errors: GccPhat {ck['gcc_err']}, Angle2 {ck['a2_err']}; no read: GccPhat "
      f"{ck['gcc_none']}, Angle2 {ck['a2_none']}.")

print('\n## Under Jay\'s rule\n')
print('| pair | scheme | in scope | read outliers set aside | scenarios dropped | kept | mean / median, kept | within 10 deg, kept |')
print('|---|---|---|---|---|---|---|---|')
for sp in SP:
    s = json.load(open(out / f'locata_{sp}mm_summary.json'))
    for name in ('GccPhat', 'Angle2'):
        x = s[name]
        sc = x['score']
        print(f"| {sp} mm | {name} | {x['in_scope']} | {x['read_outliers']} ({x['read_outliers_pct']}%) | "
              f"{x['scenarios_dropped']} of {x['scenarios']} | {x['kept_pct']}% | {sc['mean_err']} / {sc['median_err']} | "
              f"{sc['within_10_pct']}% |")
    cm = s['common']
    print(f"| {sp} mm | both kept ({cm['reads']}) | | | | | GccPhat {cm['GccPhat']['mean_err']} / {cm['GccPhat']['median_err']}, "
          f"Angle2 {cm['Angle2']['mean_err']} / {cm['Angle2']['median_err']} | {cm['GccPhat']['within_10_pct']}% / "
          f"{cm['Angle2']['within_10_pct']}% |")
print('\nLean (signed error along the truth\'s side, mean deg; negative = nearer 0), kept reads:\n')
print('| pair | scheme | ' + ' | '.join(f'{lo:.0f}-{hi:.0f}' for lo, hi in BANDS) + ' |')
print('|---|---|' + '---|' * len(BANDS))
for sp in SP:
    s = json.load(open(out / f'locata_{sp}mm_summary.json'))
    for name in ('GccPhat', 'Angle2'):
        lb = s[name]['score']['lean_mean_by_band']
        print(f'| {sp} mm | {name} | ' + ' | '.join(f"{v['mean']} (n={v['n']})" for v in lb.values()) + ' |')

print('\n## Wrong locks, in scope (raw, before the rule sets anything aside)\n')
print('| pair | scheme | split | n | wrong > 10 deg | wrong > 36 deg |')
print('|---|---|---|---|---|---|')
for sp in SP:
    for name, f in SCHEMES.items():
        rs = [r for r in scope(sp) if f(r) is not None]
        groups = [('all', rs)]
        groups += [(f'|truth| {lo:.0f}-{hi:.0f}', [r for r in rs if lo <= abs(r['truth']['deg']) < hi]) for lo, hi in BANDS]
        groups += [(f"task {t}", [r for r in rs if truth[r['id']]['task'] == f'task{t}']) for t in (3, 4)]
        groups += [('another talker active', [r for r in rs if r['truth']['others']]),
                   ('alone', [r for r in rs if not r['truth']['others']])]
        groups += [(f'facing {lo}-{hi} deg', [r for r in rs if r['truth']['facing_deg'] is not None
                                               and lo <= r['truth']['facing_deg'] < hi]) for lo, hi in ((0, 60), (60, 120), (120, 181))]
        groups += [(f'distance {lo}-{hi} m', [r for r in rs if lo <= r['truth']['dist_m'] < hi]) for lo, hi in ((0, 1.5), (1.5, 2.5), (2.5, 9))]
        for g, sel in groups:
            e = [abs(f(r) - r['truth']['deg']) for r in sel]
            print(f'| {sp} mm | {name} | {g} | {len(e)} | {pct([x > HIT for x in e])} | {pct([x > OUT for x in e])} |')

print('\n## Who else was talking, and which way the talker faced (in scope; wrong > 10 deg / > 36 deg)\n')
others = lambda r: truth[r['id']]['truth']['others']
CONTEXT = [('alone', lambda r: not others(r)),
           ('another talker only in the pause before', lambda r: others(r) and all(o['during'] == 0 for o in others(r))),
           ('another talker during the read (> 20% of its 0.5 s)', lambda r: any(o['during'] > 0.2 for o in others(r)))]
FACE = [('facing 0-60', 0, 60), ('60-120', 60, 120), ('away, 120-180', 120, 181)]
print('| pair | scheme | who else | ' + ' | '.join(f[0] for f in FACE) + ' | all facings |')
print('|---|---|---|' + '---|' * (len(FACE) + 1))
for sp in SP:
    for name, f in SCHEMES.items():
        for cname, cf in CONTEXT:
            cells = []
            for _, lo, hi in FACE + [('all', 0, 181)]:
                sel = [r for r in scope(sp) if cf(r) and f(r) is not None and r['truth']['facing_deg'] is not None
                       and lo <= r['truth']['facing_deg'] < hi]
                e = [abs(f(r) - r['truth']['deg']) for r in sel]
                cells.append(f"{pct([x > HIT for x in e])} / {pct([x > OUT for x in e])} (n={len(e)})" if e else '-')
            print(f'| {sp} mm | {name} | {cname} | ' + ' | '.join(cells) + ' |')
print('\nLean on the clean reads only (alone, facing within 60 deg, within 36 deg), mean deg, negative = nearer 0:\n')
print('| pair | scheme | ' + ' | '.join(f'{lo:.0f}-{hi:.0f}' for lo, hi in BANDS[:4]) + ' |')
print('|---|---|' + '---|' * 4)
for sp in SP:
    for name, f in SCHEMES.items():
        cl = [r for r in scope(sp) if not others(r) and r['truth']['facing_deg'] is not None and r['truth']['facing_deg'] < 60
              and f(r) is not None and abs(f(r) - r['truth']['deg']) <= OUT]
        cells = []
        for lo, hi in BANDS[:4]:
            v = [(f(r) - r['truth']['deg']) * (1 if r['truth']['deg'] > 0 else -1) for r in cl if lo <= abs(r['truth']['deg']) < hi]
            cells.append(f'{st.mean(v):+.1f} (n={len(v)})' if v else '-')
        print(f'| {sp} mm | {name} | ' + ' | '.join(cells) + ' |')
a2f = [r['a2']['first_ms'] for r in reads if r['a2']]
print(f"\nAngle2's onset family starts {st.median(a2f):.0f} ms from the VAD onset at the median "
      f"(5th-95th percentile {np.percentile(a2f, 5):.0f} to {np.percentile(a2f, 95):.0f} ms; negative = before it).")

print('\n## The class catalogue (in scope)\n')
summ = json.load(open(out / 'summary.json'))['catalogue']
print('| pair | scheme | severity | wrong reads | ' + ' | '.join(NAMES) + ' |')
print('|---|---|---|---|' + '---|' * len(NAMES))
for sp in SP:
    for s, name in (('gcc', 'GccPhat'), ('a2', 'Angle2')):
        for sev in ('moderate', 'outlier'):
            c = summ[f'{s} {sp}mm {sev}']
            print(f"| {sp} mm | {name} | {sev} | {c['reads']} | " + ' | '.join(str(c['classes'].get(n, 0)) for n in NAMES) + ' |')
print('\nMost common overlaps (160 mm, outliers):\n')
for s, name in (('gcc', 'GccPhat'), ('a2', 'Angle2')):
    c = summ[f'{s} 160mm outlier']
    print(f"- {name}: " + '; '.join(f'{k} {v}' for k, v in list(c['overlaps'].items())[:6]))

print('\n## Can it tell at the moment of the read? (in scope, 160 mm)\n')
print('AUC of each clue for telling a read within 10 deg from one off by more (0.5 = no information; '
      'below 0.5, the clue is higher on misses).\n')


def auc(pos, neg):
    """Mann-Whitney: the chance a right read's clue beats a wrong one's (ties count half)."""
    if not pos or not neg:
        return None
    rk = rankdata(np.array(pos + neg, float))
    return (rk[:len(pos)].sum() - len(pos) * (len(pos) + 1) / 2) / (len(pos) * len(neg))


rs = scope(160)
clues = {
    'GccPhat share (angle 1)': ('gcc', lambda r: r['gcc']['shares'][0]),
    'GccPhat width (deg, narrower = higher)': ('gcc', lambda r: -(r['gcc']['widths'][0][1] - r['gcc']['widths'][0][0])),
    'GccPhat share margin, angle 1 - angle 2': ('gcc', lambda r: r['gcc']['shares'][0] - (r['gcc']['shares'][1] if len(r['gcc']['shares']) > 1 else 0)),
    'GccPhat no tie': ('gcc', lambda r: 0 if r['gcc']['tie'] else 1),
    'GccPhat votes after pause weighting': ('gcc', lambda r: r['gcc']['votes']),
    'GccPhat 43 ms read agrees with lock (-|diff|)': ('gcc', lambda r: -abs(r['gcc']['track']['43'] - r['gcc']['angles'][0]) if r['gcc']['track']['43'] is not None else None),
    'Angle2 agrees with GccPhat (-|diff|)': ('both', lambda r: -abs(r['a2']['deg'] - r['gcc']['angles'][0]) if r['a2'] else None),
    'away from the pause direction (|read - pause|)': ('gcc', lambda r: abs(r['gcc']['angles'][0] - r['pause_deg']) if r['pause_deg'] is not None else None),
    'SNR 300-1100 Hz': ('gcc', lambda r: r['snr_db']['mf']),
    'SNR 1.1-3 kHz': ('gcc', lambda r: r['snr_db']['hf1']),
    'SNR 3-8 kHz': ('gcc', lambda r: r['snr_db']['hf2']),
    'Angle2 edge (clean rising onset)': ('a2', lambda r: 1 if r['a2']['edge'] else 0),
    'Angle2 at3 earlier (-ms)': ('a2', lambda r: -r['a2']['at3_ms']),
}
print('| clue | for GccPhat\'s read | for Angle2\'s read |')
print('|---|---|---|')
for name, (_, fn) in clues.items():
    cells = []
    for sch, f in SCHEMES.items():
        pos, neg = [], []
        for r in rs:
            if f(r) is None or not r['gcc']:
                continue
            try:
                v = fn(r)
            except (TypeError, KeyError):
                v = None
            if v is None:
                continue
            (pos if abs(f(r) - r['truth']['deg']) <= HIT else neg).append(v)
        a = auc(pos, neg)
        cells.append(f'{a:.2f}' if a is not None else '-')
    print(f'| {name} | ' + ' | '.join(cells) + ' |')

rp = out / 'range_summary.json'
if rp.exists():
    R = json.load(open(rp))
    print('\n## Range, alongside\n')
    print('| pair | cue | ordered right: 1.25x | 1.5x | 2x | repeat spread (same spot, median abs diff) | 2x step (median abs diff) |')
    print('|---|---|---|---|---|---|---|')
    for sp in SP:
        for cue, s in R[f'{sp}mm'].items():
            o = s['ordering']
            cell = lambda k: f"{100 * o[k]['correct']:.0f}% (n={o[k]['pairs']})" if o[k]['correct'] is not None else '-'
            print(f"| {sp} mm | {cue} | {cell('1.25x')} | {cell('1.5x')} | {cell('2x')} | {s['repeat_median_abs_diff']} "
                  f"(n={s['repeat_pairs']}) | {s['step_2x_median_abs_diff']} |")
    if 'echo_lag_vs_floor' in R:
        e = R['echo_lag_vs_floor']
        print(f"\nThe cepstral echo lag is within 0.25 ms of the floor echo's geometric lag on {100 * e['within_0.25ms']:.0f}% "
              f"of cuts (median difference {e['median_abs_diff_ms']} ms, n={e['n']}).")
