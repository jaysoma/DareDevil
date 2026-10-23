#!/usr/bin/env python3
"""Tables and the trade-off plot for results/resample/report.md, from score.py's summary.json.

usage: python3 tables.py SUMMARY_DIR OUT_DIR   (writes tables.md and tradeoff.png; copies summary.json)
"""
import json
import shutil
import sys
from pathlib import Path

src, out = Path(sys.argv[1]), Path(sys.argv[2])
out.mkdir(parents=True, exist_ok=True)
S = json.load(open(src / 'summary.json'))
L = []
p = L.append

p('## 1. How fast things move during voiced speech (LOCATA, 160 mm pair; median / 90th percentile)\n')
p('| over | bearing (deg) | distance (m) | distance (%) | head orientation (deg) | facing the array (deg) |')
p('|---|---|---|---|---|---|')
for h in ('0.25', '0.5', '1.0'):
    for tk in ('all', 'task3', 'task4'):
        m = S['motion'][f'{h}s {tk}']
        c = lambda q: f"{m[q]['median']} / {m[q]['p90']}"
        p(f"| {h} s ({tk}) | {c('bearing_deg')} | {c('dist_m')} | {c('dist_pct')} | {c('head_deg')} | {c('facing_deg')} |")

ANG = ['gcc_shipped', 'a2_shipped'] + [f'slide{s}_{t}' for s in (0.25, 0.5) for t in ('raw', 'T0', 'T5', 'T10', 'T15')]
NAME = lambda k: {'gcc_shipped': 'GccPhat as shipped (settle, lock, hold)', 'a2_shipped': 'Angle2 at its onset, held'}.get(
    k, k.replace('slide', 're-read every ').replace('_raw', ' s, every read shown').replace('_T', ' s, dim rule and > ') + (' deg' if '_T' in k else ''))
for split in ('all', 'moving', 'still', 'task3', 'task4'):
    p(f'\n## 2. Angle, {split} utterances (160 mm; error in deg, tolerance 10 deg)\n')
    if split == 'moving':
        p('(utterances in which the true bearing moved more than 10 deg)\n')
    p('| policy | utterances | time within 10 deg | median / mean error | moves per minute after the lock | out-of-tolerance episodes: count, median / 90th pct length (s) |')
    p('|---|---|---|---|---|---|')
    for k in ANG:
        v = S['angle'].get(f'160|{split}|{k}')
        if v:
            p(f"| {NAME(k)} | {v['utterances']} | {v['within_tol_pct']}% | {v['median_err']} / {v['mean_err']} | {v['moves_per_min']} | "
              f"{v['lag_episodes']}, {v['lag_median_s']} / {v['lag_p90_s']} |")
p('\n80 mm pair, all utterances:\n')
p('| policy | time within 10 deg | median / mean error | moves per minute | episodes, median / 90th pct (s) |')
p('|---|---|---|---|---|')
for k in ANG:
    v = S['angle'].get(f'80|all|{k}')
    if v:
        p(f"| {NAME(k)} | {v['within_tol_pct']}% | {v['median_err']} / {v['mean_err']} | {v['moves_per_min']} | {v['lag_episodes']}, {v['lag_median_s']} / {v['lag_p90_s']} |")

RNG = [f'{a}_{b}' for b in ('shipped', 'lf') for a in ('per_utt', 'slide0.5', 'slide1.0')]
for sp in (160, 80):
    p(f'\n## 3. Range, {sp} mm (distance ratio to the opener; error in dB of distance, tolerance 25% = 1.9 dB)\n')
    p('| policy | utterances | time within 25% | median / mean error (dB) | moves per minute | episodes, median / 90th pct (s) | follows a real >20% change |')
    p('|---|---|---|---|---|---|---|')
    for k in RNG:
        v = S['range'].get(f'{sp}|all|{k}')
        f = S['range_follows_real_change'].get(f'{sp}|{k}', {})
        fol = f"{f.get('moved_right_way_pct')}% right way (n={f.get('utterances')})" if f and not f.get('did_not_move_pct') else 'never moves'
        if v:
            p(f"| {k.replace('per_utt', 'per utterance (shipped)').replace('slide', 'sliding ').replace('_', ' s, ', 1) if 'slide' in k else k.replace('per_utt_', 'per utterance, ')} | "
              f"{v['utterances']} | {v['within_tol_pct']}% | {v['median_err']} / {v['mean_err']} | {v['moves_per_min']} | "
              f"{v['lag_episodes']}, {v['lag_median_s']} / {v['lag_p90_s']} | {fol} |")

p('\n## 4. Facing: the truth\'s own rate of change (a perfect facing reading, held)\n')
p('| update | time within 30 deg | median / mean error (deg) | updates per minute |')
p('|---|---|---|---|')
for k, v in S['facing_truth'].items():
    p(f"| {k.replace('_', ' ')} | {v['within_tol_pct']}% | {v['median_err']} / {v['mean_err']} | {v['moves_per_min']} |")
fs = S['facing_spread']
p(f"\nFacing turns a median {fs['utterance']['median_deg']} deg within an utterance (90th percentile {fs['utterance']['p90_deg']}; "
  f"over 30 deg in {fs['utterance']['over_30_pct']}%), and {fs['phrase']['median_deg']} deg within a phrase. An utterance has "
  f"{S['phrases_per_utterance']} phrases on average, so per phrase and per utterance are nearly the same updates.")
(out / 'tables.md').write_text('\n'.join(L) + '\n')
shutil.copy(src / 'summary.json', out / 'summary.json')

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
fig, axs = plt.subplots(1, 3, figsize=(15, 4.4), sharey=True)
for ax, split in zip(axs, ('all', 'moving', 'still')):
    for k in ANG:
        v = S['angle'].get(f'160|{split}|{k}')
        if not v:
            continue
        mk = 'o' if '0.25' in k else ('s' if '0.5' in k else '*')
        ax.scatter(v['moves_per_min'], v['within_tol_pct'], marker=mk, s=60)
        ax.annotate(k.replace('slide', '').replace('_shipped', ''), (v['moves_per_min'], v['within_tol_pct']), fontsize=7,
                    xytext=(4, 3), textcoords='offset points')
    ax.set_xscale('symlog', linthresh=1); ax.set_title(f'{split} utterances, 160 mm')
    ax.set_xlabel('moves per minute after the lock (jitter)')
axs[0].set_ylabel('share of time within 10 deg of the talker')
fig.tight_layout(); fig.savefig(out / 'tradeoff.png', dpi=110)
print((out / 'tables.md').read_text()[:2500])
