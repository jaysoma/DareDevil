#!/usr/bin/env python3
"""Tables for results/first_reflection/report.md from the two scorers' outputs. Prints markdown.

usage: python3 analyze.py OUT_DIR > tables.md
"""
import gzip
import json
import sys
from collections import Counter
from pathlib import Path

import numpy as np

out = Path(sys.argv[1])
D = json.load(open(out / 'dechorate_summary.json'))
Dr = [json.loads(l) for l in gzip.open(out / 'dechorate_reads.jsonl.gz', 'rt')]
ROOMS = ['000000', '000001', '000010', '000100', '001000', '010000', '011000', '011100', '011110', '011111', '020002']
NAME = {'000000': 'none', '000001': 'north', '000010': 'east', '000100': 'south (measures as none)', '001000': 'west',
        '010000': 'ceiling', '011000': 'ceiling, west', '011100': '+ south', '011110': '+ east', '011111': '+ north',
        '020002': 'ceiling, north, furniture'}


def hc(d, n):
    if not d or d.get(f'{n}_hit_pct') is None:
        return '-'
    return f"{d[f'{n}_hit_pct']:.1f}% / {d[f'{n}_chance_pct']:.1f}%"


print('## dEchorate\n')
o = D['onset_rule']
print(f"readSound's onset under Jay's rule: {o['in_scope']} reads in scope, {o['read_outliers']} set aside "
      f"({o['read_outliers_pct']}%), {o['scenarios_dropped']} of {o['scenarios']} scenarios dropped; kept "
      f"{o['kept_pct']}%: mean {o['score']['mean_err']}, median {o['score']['median_err']} deg, "
      f"{o['score']['within_10_pct']}% within 10 deg. Outlier kinds: "
      + ', '.join(f'{k} {v}' for k, v in o['outlier_kinds'].items()) + '.\n')
print('Undecided, why (in scope): ' + ', '.join(f'"{k}" {v}' for k, v in D['undecided_why'].items()) + '.\n')
print('The first frame (s) sits at ' + ', '.join(f'{v} ms' for v in D['first_frame_ms_from_onset'].values())
      + ' from the true onset (5th, 25th, 50th, 75th, 95th percentile).\n')
for sp in (155, 65):
    print(f'\n**{sp} mm, decided reads whose onset the rule kept** (hit / chance; within 10 deg, within 0.25 ms)\n')
    print('| config | reflective | decided | reads | earliest distinct: scored (outside 1-12 ms) | angle | lag | both | '
          'any reflective: angle | lag | both |')
    print('|---|---|---|---|---|---|---|---|---|---|---|')
    for room in ROOMS + ['all']:
        r = D['reflection'][f'kept_onsets|{sp}|{room}']
        e, a = r['earliest_distinct'], r['any_reflective']
        print(f"| {room} | {NAME.get(room, '')} | {r.get('decided_pct')}% | {r['decided_reads']} | {e['scored']} "
              f"({e['echo_outside_window']}) | {hc(e, 'angle')} | {hc(e, 'lag')} | {hc(e, 'both')} | {hc(a, 'angle')} | "
              f"{hc(a, 'lag')} | {hc(a, 'both')} |")
    print(f'\n**{sp} mm, by source** (all configurations; any reflective echo)\n')
    print('| source | reads | angle | lag | both |')
    print('|---|---|---|---|---|')
    for s in range(6):
        r = D['reflection'][f'kept_onsets|{sp}|src{s}']
        a = r['any_reflective']
        print(f"| {s}{' (faces a wall)' if s in (4, 5) else ''} | {r['decided_reads']} | {hc(a, 'angle')} | {hc(a, 'lag')} | {hc(a, 'both')} |")

dec = [r for r in Dr if r['decided']]
g = np.array([r['gap_ms'] for r in dec])
same = np.array([abs(r['refl']['deg'] - r['onset']['deg']) <= 10 for r in dec])
print('\n**What the decided reflection is** (all decided reads, both spacings):\n')
print(f'- gap_ms percentiles (5/25/50/75/95): ' + ', '.join(f'{v:.2f}' for v in np.percentile(g, [5, 25, 50, 75, 95]))
      + f' ms; {100 * (g <= 1.05).mean():.0f}% exactly at the 1 ms floor (MIN_GAP_MS).')
for room in ('000000', '010000', '011111'):
    gg = [r['gap_ms'] for r in dec if r['id'].startswith(room)]
    print(f'- {room}: median gap {np.median(gg):.2f} ms, {100 * np.mean(np.array(gg) <= 1.05):.0f}% at 1 ms.')
print(f'- The reflection within 10 deg of readSound\'s own onset: {100 * same.mean():.0f}% of decided reads '
      f'({100 * same[g <= 1.05].mean():.0f}% of those at 1 ms).')

print('\n**Echoes readSound\'s 1-12 ms window cannot see** (155 mm, in scope, reflective surfaces only):\n')
print('| config, surface | inside | after 12 ms | before 1 ms |')
print('|---|---|---|---|')
for k, c in D['echo_window'].items():
    print(f"| {k} | {c.get('inside', 0)} | {c.get('after 12 ms', 0)} | {c.get('before 1 ms', 0)} |")
ew = D['earliest_distinct_in_window']
print('\nThe earliest distinct echo falls outside the window on '
      + ', '.join(f"{v['outside']} of {v['inside'] + v['outside']} cuts at {k}" for k, v in ew.items()) + '.\n')

print('**The wall, where angle and lag both hit** (medians):\n')
print('| pair, surface | reads | reflection point off the wall (m): front / better side | normal error (deg) | '
      'source-to-wall, estimated / true (m) |')
print('|---|---|---|---|---|')
for k, v in D['wall'].items():
    print(f"| {k} | {v['n']} | {v['front_side']['off_wall_m']} / {v['better_side']['off_wall_m']} | "
          f"{v['front_side']['normal_err_deg']} / {v['better_side']['normal_err_deg']} | "
          f"{v['better_side']['src_wall_m']} / {v['true_src_wall_m']} |")

L = json.load(open(out / 'locata_summary.json'))
print('\n## LOCATA\n')
for sp in (160, 80):
    o = L[f'onset_rule_{sp}mm']
    print(f"- {sp} mm onset under the rule: {o['read_outliers']} of {o['in_scope']} set aside, {o['scenarios_dropped']} "
          f"of {o['scenarios']} scenarios dropped; kept: mean {o['score']['mean_err']}, median {o['score']['median_err']} "
          f"deg, {o['score']['within_10_pct']}% within 10 deg.")
print('\n| pair | reads | decided | floor: lag hit / chance | angle | both | ceiling: lag hit / chance | either: lag |'
      ' gap - floor lag, median (ms) | floor lag, 5/50/95 (ms) |')
print('|---|---|---|---|---|---|---|---|---|---|')
for sp in (160, 80):
    s = L['lag'][f'kept_onsets|{sp}']
    f, c, e = s['floor'], s['ceiling'], s['either']
    print(f"| {sp} mm | {s['decided_reads']} | {s['decided_pct']}% | {f['lag_hit_pct']}% / {f['lag_chance_pct']}% | "
          f"{f['angle_hit_pct']}% | {f['both_hit_pct']}% | {c['lag_hit_pct']}% / {c['lag_chance_pct']}% | {e['lag_hit_pct']}% | "
          f"{s['gap_minus_floor_ms']['50']} | {' / '.join(str(v) for v in s['floor_ms'].values())} |")
print(f"\nThe floor echo is more than 10 deg from the direct direction on "
      f"{L['lag']['kept_onsets|160']['floor_distinct_from_direct_pct']}% of 160 mm reads. Undecided, why (160 mm): "
      + ', '.join(f'"{k}" {v}' for k, v in L['lag']['undecided_why|160'].items()) + '.')
print('\n**Range from the echo** (same talker, same recording and pair; ordered right at 1.25x / 1.5x / 2x; spread within '
      '0.3 m of one spot; the step at 2x)\n')
print('| pair | cue | 1.25x | 1.5x | 2x | spread at one spot | step at 2x |')
print('|---|---|---|---|---|---|---|')
for sp in (160, 80):
    for cue, v in L['range'][f'{sp}mm'].items():
        op, n = v['ordering_pct'], v['ordering_pairs']
        print(f"| {sp} mm | {cue} | {op['1.25x']}% (n={n['1.25x']}) | {op['1.5x']}% (n={n['1.5x']}) | {op['2x']}% "
              f"(n={n['2x']}) | {v['spread_one_spot']} (n={v['spot_pairs']}) | {v['step_2x']} |")
