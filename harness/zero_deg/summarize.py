#!/usr/bin/env python3
"""Tables for results/zero_deg/report.md from pause_gcc.json (and sim_diffuse.json when given).

    python3 summarize.py pause_gcc.json [sim_diffuse.json] > tables.md
"""
import json
import sys

import numpy as np

r = json.load(open(sys.argv[1]))
HPS = [str(h) for h in r['config']['hps']]
PAIRS = ['12', '13', '14', '23', '24', '34']
ROOMS = sorted(r['counts']['silence'], key=lambda s: int(s[4:]))
pct = lambda a, b: f'{100 * a / b:.1f}' if b else '-'
share = lambda c: pct(c[1], c[0])     # c = [frames, near 0, null near 0]


def pooled(s, rooms=ROOMS, pairs=PAIRS, hp='0'):
    n = k = z = 0
    for m in rooms:
        for p in pairs:
            c = r['counts'][s].get(m, {}).get(p, {}).get(hp)
            if c:
                n += c[0]; k += c[1]; z += c[2]
    return n, k, z


def table(head, rows):
    out = ['| ' + ' | '.join(head) + ' |', '|' + '---|' * len(head)]
    out += ['| ' + ' | '.join(str(v) for v in row) + ' |' for row in rows]
    return '\n'.join(out)


hp_head = [f'HP {h} Hz' for h in HPS]
for s in ('silence', 'speechfree'):
    print(f'\n### {s}: pooled over 16 rooms and 6 pairs\n')
    rows = []
    for name, fn in (('peaks within 6 deg of 0, %', lambda c: pct(c[1], c[0])),
                     ('null (no coherence), %', lambda c: pct(c[2], c[0]))):
        rows.append([name] + [fn(pooled(s, hp=h)) for h in HPS])
    rows.append(['frames x pairs'] + [pooled(s, hp=h)[0] for h in HPS])
    print(table([''] + hp_head, rows))

    print(f'\n### {s}: by pair, pooled over rooms (% within 6 deg of 0)\n')
    print(table(['pair', 'mm'] + hp_head + ['null at HP 0'],
                [[p, r['config']['baseline_mm'][p]] + [share(pooled(s, pairs=[p], hp=h)) for h in HPS]
                 + [pct(pooled(s, pairs=[p])[2], pooled(s, pairs=[p])[0])] for p in PAIRS]))

    print(f'\n### {s}: by room, pooled over pairs (% within 6 deg of 0)\n')
    rows = []
    for m in ROOMS:
        n0 = pooled(s, rooms=[m])
        rows.append([m, n0[0] // 6] + [share(pooled(s, rooms=[m], hp=h)) for h in HPS] + [pct(n0[2], n0[0])])
    print(table(['room', 'frames'] + hp_head + ['null at HP 0'], rows))

print('\n### silence: room x pair, % within 6 deg of 0, one table per high-pass\n')
for h in HPS:
    print(f'\n**HP {h} Hz**\n')
    print(table(['room'] + PAIRS, [[m] + [share(r['counts']['silence'][m][p][h]) for p in PAIRS] for m in ROOMS]))

print('\n### silence: strongest quarter of frames (by PHAT peak share), % within 6 deg of 0, pooled pairs (mean)\n')
st = r['strength']['silence']
print(table(['', ] + hp_head, [['all frames'] + [f"{np.mean([st[p][h]['all_near0_pct'] for p in PAIRS]):.1f}" for h in HPS],
                              ['strongest 25%'] + [f"{np.mean([st[p][h]['top25_near0_pct'] for p in PAIRS]):.1f}" for h in HPS]]))

edges = r['coherence_edges_hz']
bands = [f'{a}-{b}' for a, b in zip(edges, edges[1:])]
print('\n### silence: coherence by band, Re(Sab)/sqrt(Saa Sbb), mean over the 6 pairs\n')
f = np.array(r['coherence_freqs_hz'])
d = np.mean(list(r['config']['baseline_mm'].values())) / 1000
sinc = np.sinc(2 * f * d / 343.0)
theory = [f'{sinc[(f >= a) & (f < b) & (f > 0)].mean():.2f}' for a, b in zip(edges, edges[1:])]
rows = [['diffuse, free field, 68.5 mm'] + theory]
for m in ROOMS:
    rows.append([m] + [f"{np.mean([r['coherence_re'][m][p]['band_re'][i] for p in PAIRS]):.2f}" for i in range(len(bands))])
print(table(['Hz'] + bands, rows))
print('\n### silence: magnitude-squared coherence by band, mean over the 6 pairs\n')
print(table(['Hz'] + bands, [[m] + [f"{np.mean([r['coherence_re'][m][p]['band_msc'][i] for p in PAIRS]):.2f}" for i in range(len(bands))]
                             for m in ROOMS]))

if len(sys.argv) > 2:
    sm = json.load(open(sys.argv[2]))
    print('\n### simulation: % within 6 deg of 0\n')
    rows = []
    for d in ('68.5mm', '157.0mm'):
        for k, v in sm[d].items():
            rows.append([d, k] + [v[h] for h in HPS])
    print(table(['pair', 'field'] + hp_head, rows))
