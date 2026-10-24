#!/usr/bin/env python3
"""The opener as the facing reference, now that the ding is out (2026-10-24). Jay: every recording begins facing the
phone; what spoils the opener is the phone's own ding, which is very loud and fully coherent. Rules, all label-free past
the opener, on each walk's stops after its opener:
  opener:        the opener alone; turned if more than T below it
  running:       start at the opener; a stop within T of the reference joins the facing set, and the reference is that
                 set's mean (causal: each stop sees only what came before)
  90th pct:      the tape's stops, 90th percentile (not causal; room_reference.md's rule)
Ding guard: windows whose 4-8 kHz CDR exceeds DING_DB are dropped (the phone's speaker reads 10-30 dB; brief B2),
besides the first 2 s."""
import json
import numpy as np
from facing_pooled import HANDLING_S, REPO, feats, lin

K = 'CDR hi - lo (4-8 vs 0.1-1.1 kHz)'
OPENER = {'walk-030615': (4, 17), 'walk-231705': (2, 22), 'walk-231921': (7, 29), 'walk-171645': (3, 7),
          'walk-215800': (2, 10), 'walk-213304': (2, 20), 'walk-224302': (2, 13), 'walk-221126': (2, 12),
          'walk-122038': (27, 35), 'walk-125621': (37, 45)}   # the last two: no clean speech before their first turn
lab = json.loads((REPO / 'harness/rotation/facing_stops.json').read_text())['stops']


def run(ding_db):
    per, dropped, kept = {}, 0, 0
    for walk, spots in lab.items():
        bw = json.loads((REPO / 'tapes' / walk / 'band_windows.json').read_text())
        t0 = np.array(bw['t0']); D, R, P = lin(bw['dir_db']), lin(bw['dif_db']), lin(bw['pow_db'])
        tot = 10 * np.log10(P[:, 1:].sum(1)); voiced = (tot >= np.percentile(tot, 20) + 10) & (t0 >= HANDLING_S)
        hf = 10 * np.log10(D[:, 3] / R[:, 3]); ding = hf > ding_db
        dropped += int((voiced & ding).sum()); kept += int((voiced & ~ding).sum()); voiced &= ~ding
        def c(a, b):
            m = voiced & (t0 >= a) & (t0 + bw['win_s'] <= b)
            return feats(D[m], R[m], P[m], m.sum())[K] if m.sum() >= 2 else None
        oa, ob = OPENER[walk]
        st = sorted((a, b, fd) for s, v in spots.items() if s != 'dist_m' for a, b, fd in v)
        stops = [(a, fd, c(a, b)) for a, b, fd in st if not (a == oa and b == ob) and (fd == 0 or fd >= 90)]
        per[walk] = (c(oa, ob), [(a, fd, x) for a, fd, x in stops if x is not None])
    return per, dropped, kept


def score(per, rule, T):
    tp = nt = tn = nu = 0
    for walk, (op, stops) in per.items():
        if op is None:
            continue
        facing = [op]; allc = [x for _, _, x in stops]
        for a, fd, x in stops:
            ref = {'opener': op, 'running': np.mean(facing), '90th pct': np.percentile(allc, 90)}[rule]
            called = x >= ref - T
            if rule == 'running' and called:
                facing.append(x)
            if fd == 0: nt += 1; tp += called
            else: nu += 1; tn += not called
    return f"{tp}/{nt} facing, {tn}/{nu} turned, {(tp / nt + tn / nu) / 2 * 100:.0f}%"


out = []
for ding_db in (99, 12, 10):
    per, dr, kp = run(ding_db)
    out.append(f"ding guard {'off' if ding_db == 99 else f'at {ding_db} dB'}: {dr} of {dr + kp} speech windows dropped")
    for rule in ('opener', 'running', '90th pct'):
        out.append(f"  {rule:9s} " + '   '.join(f"T={T}: {score(per, rule, T)}" for T in (1.0, 1.5, 2.0)))
txt = '\n'.join(out); (REPO / 'results/rotation/opener_reference.txt').write_text(txt + '\n'); print(txt)
