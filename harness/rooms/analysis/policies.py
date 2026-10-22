"""Counting rules for the onset, tried offline on probe.mjs window dumps: the first direction to recur among windows
that pass a test (rise over the window 3 ms before, peak share), h times, within u windows of the first counted one;
else the original count. Per rule: lean, median error, within 10 deg (noisy rooms / the rest), and how many onsets moved
to within 10 deg of the truth or out of it, against the original. usage: python policies.py <dump dir> <out.json>"""
import json, glob, os, sys, math
import numpy as np
from concurrent.futures import ProcessPoolExecutor
SR, C, AG = 48000, 343, 3
def load(f):
    out = []
    for l in open(f):
        d = json.loads(l); dd = d['d']
        out.append((d['t'], [(i, db, rise, sh, deg, -math.sin(math.radians(deg)) * dd / C * SR) for i, (ms, db, rise, sh, deg) in enumerate(d['w']) if db >= 10]))
    return out
def first_recur(w, ok, hits, until=None):
    fams = []
    t0 = w[0][0] if w else 0
    for x in w:
        if until is not None and x[0] - t0 > until: return None
        if not ok(x): continue
        f = next((q for q in fams if abs(q[0] - x[5]) <= AG), None)
        if f is None: f = [x[5], x[4], 0]; fams.append(f)
        f[2] += 1
        if f[2] == hits: return f[1]
    return None
ALL = lambda x: True
R = lambda r: (lambda x: x[2] >= r)
RS = lambda r, s: (lambda x: x[2] >= r and x[3] >= s)
def mk(ok, h, until):
    return lambda w: first_recur(w, ok, h, until) if first_recur(w, ok, h, until) is not None else first_recur(w, ALL, 3)
P = {'base': lambda w: first_recur(w, ALL, 3)}
for r in (-99, 3, 6):
    for sh in (.5, .6, .7):
        for h in (2, 3):
            for until in (None, 100):
                P[f'r{r}&s{sh} h{h} u{until}'] = mk(RS(r, sh), h, until)
def score(f):
    name = os.path.basename(f)[:-6]; D = load(f); out = {}
    base = [P['base'](w) for t, w in D]
    for p, run in P.items():
        lean, err, win, lose = [], [], 0, 0
        for (t, w), b in zip(D, base):
            r = run(w)
            if r is None: continue
            err.append(abs(r - t))
            if 30 <= abs(t) <= 60: lean.append((r - t) * np.sign(t))
            if b is not None:
                win += abs(b - t) > 10 and abs(r - t) <= 10; lose += abs(b - t) <= 10 and abs(r - t) > 10
        out[p] = (float(np.median(lean)), float(np.median(err)), float(np.mean(np.array(err) <= 10)), win, lose)
    return name, out
with ProcessPoolExecutor(4) as ex: res = dict(ex.map(score, sorted(glob.glob(sys.argv[1] + '/*.jsonl'))))
json.dump(res, open(sys.argv[2], 'w'), indent=0)
hard = [n for n in res if ('+n' in n or '+ctx' in n or '+jit' in n) and not n.startswith('free')]
clean = [n for n in res if n not in hard]
print('policy'.ljust(22), 'noisy rooms: lean err w10 | clean+free: lean err w10 | became right / wrong')
for p in P:
    h = np.array([res[n][p] for n in hard]); c = np.array([res[n][p] for n in clean])
    print(p.ljust(22), '%+5.1f %4.1f %3.0f%% | %+5.1f %4.1f %3.0f%% | %5d / %5d' % (h[:, 0].mean(), h[:, 1].mean(), 100 * h[:, 2].mean(),
          c[:, 0].mean(), c[:, 1].mean(), 100 * c[:, 2].mean(), sum(res[n][p][3] for n in res), sum(res[n][p][4] for n in res)))
