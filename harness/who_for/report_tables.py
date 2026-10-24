#!/usr/bin/env python3
"""Brief 22's tables.md and curves.png from evaluate_who.py's output.

usage: report_tables.py EVAL_DIR OUT_DIR
"""
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt                                               # noqa: E402

EV, OUT = Path(sys.argv[1]), Path(sys.argv[2])
OUT.mkdir(parents=True, exist_ok=True)
r = json.load(open(EV / 'summary.json'))
c1 = json.load(open(EV / 'curves_step1.json'))
c3 = json.load(open(EV / 'curves_step3.json'))
SERIES = ['#2a78d6', '#eb6834', '#1baf7a', '#eda100']                    # validated categorical slots 1-4
INK, INK2, GRID = '#0b0b0b', '#52514e', '#e4e3df'


def tbl(head, rows):
    o = ['| ' + ' | '.join(map(str, head)) + ' |', '|' + '---|' * len(head)]
    return '\n'.join(o + ['| ' + ' | '.join('' if v is None else str(v) for v in x) + ' |' for x in rows])


T = ['# Brief 22: tables\n']
T.append('## Step 1: accepted at brief 19\'s thresholds (% of real requests, each against all four devices)\n')
rows = []
for k, v in r['step1_accept'].items():
    m, t = k.split('|')
    rows.append([m, t, v['inplace|all'][0], v['spliced|all'][0], v['inplace|directive'][0], v['inplace|ask'][0],
                 v['inplace|commit'][0], v['b19_generated']['to_person'], v['b19_generated']['subject'],
                 v['b19_generated']['hits']])
T.append(tbl(['method', 'FA/h', 'real, in place', 'real, spliced', 'directive', 'ask', 'commit',
              'b19 to_person (generated)', 'b19 subject (generated)', 'b19 hits'], rows))
T.append('\n### Per device, MiniLM contrast at 10 FA/h (in place / spliced)\n')
v = r['step1_accept']['contrast_embed|10']
T.append(tbl(['device', 'in place', 'spliced'], [[d, v['inplace|all'][1][d], v['spliced|all'][1][d]]
                                                 for d in ('car', 'kitchen', 'watch', 'general')]))
T.append('\n### The same words in place against spliced (paired, every request x device)\n')
T.append(tbl(['method', 'median score in place - spliced', '% lower in place', 'pairs'],
             [[m, x['median_inplace_minus_spliced'], x['share_lower_in_place'], x['n']] for m, x in r['step1_paired'].items()]))
s = r['step1_device_shaped']
T.append(f"\n### Device-shaped real requests ({s['requests']} requests, {s['pairs']} request x device pairs passing the "
         'device\'s MiniLM shape threshold at 10 FA/h): MiniLM contrast accepts\n')
T.append(tbl(['', 'in place', 'spliced'], [['at 1 FA/h', s['accepted_contrast_embed_1fa_inplace'], s['accepted_contrast_embed_1fa_spliced']],
                                           ['at 10 FA/h', s['accepted_contrast_embed_10fa_inplace'], s['accepted_contrast_embed_10fa_spliced']]]))
T.append('\n### Full curves: % accepted as the threshold moves (per device, pooled), by false accepts per hour\n')
for m, cv in c1.items():
    T.append(f'\n**{m}**\n')
    keys = [k for k in cv if k != 'fa_per_hour']
    T.append(tbl(['FA/h'] + keys, [[cv['fa_per_hour'][i]] + [cv[k][i] for k in keys] for i in range(len(cv['fa_per_hour']))]))
T.append('\n## Step 2a: how often each cue fires (%)\n')
cues = ['vocative', 'you', 'first_person', 'past_reported', 'bare_imperative']
T.append(tbl(['phrases', 'n'] + cues, [[g, x['n']] + [x[c] for c in cues] for g, x in r['cue_rates'].items()]))
T.append('\n## Step 2b: each cue as a veto on MiniLM contrast (threshold re-chosen so stream FA/h stay at the target)\n')
rows = []
for k, x in r['step2_veto'].items():
    for t in ('1', '10'):
        y = x[t]
        rows.append([k, t, y['hits'], y['to_person'], y['subject'], y['foreign'], y['real_requests']])
T.append(tbl(['veto', 'FA/h', 'hits', 'to_person (gen.)', 'subject (gen.)', 'foreign (real)', 'real requests'], rows))
T.append('\n## Step 2c: learned combination (logistic regression, cross-fitted; never trained on generated phrases)\n')
rows = []
for k, x in r['step2_combo'].items():
    for t in ('1', '10'):
        y = x[t]
        rows.append([k, t, y['hits'], y['to_person'], y['subject'], y['foreign'], y['real_requests']])
T.append(tbl(['features', 'FA/h', 'hits', 'to_person (gen.)', 'subject (gen.)', 'foreign (real)', 'real requests'], rows))
T.append('\nCoefficients (fold 0), all cues: ' + json.dumps(r['step2_combo']['all cues']['coefficients_fold0']))
T.append('\n## Step 3: car instructions in real calls against real requests in other calls\n')
rows = []
for m, x in r['step3'].items():
    ops = x.get('at_brief19_car_thresholds') or x.get('at_calls_fa')
    for t in ('1', '10'):
        y = ops[t]
        rows.append([m, t, y['hits'], y['real_requests_accepted'], y.get('calls_fa_per_hour', t),
                     x['p_instruction_above_request']])
T.append(tbl(['method', 'FA/h (brief 19 car threshold; combos: the calls\' own)', 'car instructions found',
              'real requests accepted', 'calls FA/h at that threshold', 'P(instruction scores above request)'], rows))
T.append('\n## Real requests accepted at 10 FA/h (MiniLM contrast): catalogue\n')
T.append('```\n' + json.dumps(r['catalogue_summary'], indent=1) + '\n```')
(OUT / 'tables.md').write_text('\n'.join(T) + '\n')

# ------------------------------------------------------------------------------------------------------------ figure
plt.rcParams.update({'font.size': 9, 'axes.edgecolor': INK2, 'axes.labelcolor': INK2, 'xtick.color': INK2,
                     'ytick.color': INK2, 'axes.spines.top': False, 'axes.spines.right': False})
fig, ax = plt.subplots(1, 2, figsize=(11, 4.2), facecolor='#fcfcfb')
cv = c1['contrast_embed']
labels = [('hits', 'device instructions (brief 19)'), ('to_person (generated, spliced)', 'to a person: generated, spliced'),
          ('real requests, spliced', 'real requests: spliced elsewhere'), ('real requests, in place', 'real requests: in place')]
marks = ['o', 's', '^', 'D']
for (k, lab), col, mk in zip(labels, SERIES, marks):
    ax[0].plot(cv['fa_per_hour'], cv[k], color=col, lw=2, marker=mk, ms=4, label=lab)
ax[0].legend(frameon=False, fontsize=8, loc='center left', labelcolor=INK)
ax[0].set_xscale('log'); ax[0].set_xlim(0.2, 70); ax[0].set_ylim(-2, 102)
from matplotlib.ticker import FuncFormatter                                    # noqa: E402
plain = FuncFormatter(lambda v, _: f'{v:g}')
ax[0].xaxis.set_major_formatter(plain)
ax[0].set_xlabel('false accepts per hour of other speech (threshold per device)'); ax[0].set_ylabel('% accepted')
ax[0].set_title('MiniLM contrast: who gets through', color=INK, loc='left', fontsize=10)
ax[0].grid(True, color=GRID, lw=0.8); ax[0].set_axisbelow(True)
for (m, lab), col, mk in zip([('contrast_embed', 'MiniLM contrast'), ('contrast_ngram', 'n-gram contrast'),
                              ('shape_embed', 'MiniLM shape'), ('keyword', 'keywords')], SERIES, marks):
    x = c3[m]
    ax[1].plot([100 * v for v in x['real_request_accept']], [100 * v for v in x['hit']], color=col, lw=2,
               label=f"{lab} (P = {x['p_instruction_above_request']})")
ax[1].set_xscale('symlog', linthresh=1); ax[1].set_xlim(0, 100); ax[1].set_ylim(-2, 102)
ax[1].xaxis.set_major_formatter(plain)
ax[1].set_xlabel('% of real requests to the other caller accepted'); ax[1].set_ylabel('% of car instructions found')
ax[1].set_title('Speakerphone case on real calls (car)', color=INK, loc='left', fontsize=10)
ax[1].grid(True, color=GRID, lw=0.8); ax[1].set_axisbelow(True)
ax[1].legend(frameon=False, fontsize=8, loc='lower right', labelcolor=INK)
fig.tight_layout()
fig.savefig(OUT / 'curves.png', dpi=140, facecolor=fig.get_facecolor())
print('wrote', OUT)
