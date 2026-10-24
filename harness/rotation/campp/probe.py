#!/usr/bin/env python3
"""Brief C's probes: does any depth of CAM++ tell toward from turned, or carry distance? (2026-10-24)

Reads results/rotation/campp/vectors.npz and vectors_nocallouts.npz (campp_layers.py) and each walk's
tapes/<walk>/band_windows.json.

FACING. The stops of harness/rotation/facing_stops.json, toward (0) against turned (90 or more), each as its vector
minus a reference from its own spot. Two references:
  facing0   the brief's: the mean of the spot's facing-0 stops. A facing-0 stop is taken against the spot's OTHER
            facing-0 stops only (against a mean that includes itself it would read exactly zero, and the label would
            leak); a stop with no reference left is set aside.
  spotmean  the mean of every stop at the spot, whatever its facing. It uses no labels, so nothing is set aside; it is
            the only one that still has toward stops once the callouts are taken out.
Two probes per depth:
  lr    logistic regression on the difference vector (standardised, C = 1, balanced classes; fixed, not tuned)
  far   one number: the cosine distance from the reference, thresholded by a logistic regression on that number
Every probe, baselines included, is scored the same way: left out by walk, balanced accuracy over all held-out stops,
and a permutation test that shuffles the labels within each walk (p = share of shuffles at or above the real score).
Baselines on the same stops, windows and references: the CDR contrast (4-8 minus 0.1-1.1 kHz, facing_pooled.py),
CdrRange's range statistic (mean CDR 1.1-8 kHz), and the final embedding's cosine against the walk's first facing-0
stop (Jay's earlier test).

DISTANCE. The ladders (facing the phone at called distances), all speech. Each step against its walk's first step:
doublings of distance, log2(d / d0), from the depth's difference vector by ridge regression (alpha picked by
leave-one-walk-out inside the training walks), left out by walk. Against CdrRange's law (-20 dB per decade of the range
statistic, no fitting), calling every step the opener's distance, and calling every step the training walks' mean.

    python probe.py [n_perm]      -> results/rotation/campp/numbers.json, probe.txt
"""
import json
import sys
import zlib
from pathlib import Path

import numpy as np
from joblib import Parallel, delayed
from scipy.stats import spearmanr
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.preprocessing import StandardScaler

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / 'harness' / 'rotation'))
from facing_pooled import feats, lin  # noqa: E402

DEPTHS = ('head', 'tdnn', 'block1', 'block2', 'block3', 'stats', 'emb')
INPUTS = ('mean', 'ch0', 'ch1')
CDR_KEYS = {'cdr': 'CDR hi - lo (4-8 vs 0.1-1.1 kHz)', 'range': 'range stat (mean CDR 1.1-8 kHz)'}


def load(name):
    z = np.load(REPO / 'results/rotation/campp' / name)
    meta = json.loads(str(z['meta']))
    return meta, {k: z[k] for k in z.files if k != 'meta'}, cdr_feats(meta)


def cdr_feats(meta):
    """facing_pooled.py's per-stop features on exactly the windows the CAM++ vectors were built from."""
    cache, out = {}, []
    for r in meta:
        if r['walk'] not in cache:
            bw = json.loads((REPO / 'tapes' / r['walk'] / 'band_windows.json').read_text())
            cache[r['walk']] = (bw['win_s'], np.array(bw['t0']), lin(bw['dir_db']), lin(bw['dif_db']), lin(bw['pow_db']))
        w, t0, D, R, P = cache[r['walk']]
        m = np.zeros(len(t0), bool)
        for s0, s1 in r['spans']:
            m |= (t0 >= s0 - 1e-6) & (t0 + w <= s1 + 1e-6)
        f = feats(D[m], R[m], P[m], m.sum())
        out.append({k: f[v] for k, v in CDR_KEYS.items()})
    return out


def cos(a, b):
    return float(a @ b / (np.linalg.norm(a) * np.linalg.norm(b)))


def referenced(meta, idx, design):
    """For the stops `idx`: (rows kept, the reference rows each is taken against), as described above."""
    rows, refs = [], []
    for i in idx:
        r = meta[i]
        spot = [j for j in idx if meta[j]['walk'] == r['walk'] and meta[j]['spot'] == r['spot']]
        ref = [j for j in spot if meta[j]['facing'] == 0 and j != i] if design == 'facing0' else spot
        if ref and len(spot) >= 2:
            rows.append(i); refs.append(ref)
    return rows, refs


def lowo(X, y, walks, fit):
    """Left-out-by-walk predictions (1 = turned) from fit(Xtr, ytr) -> predict(Xte)."""
    p = np.zeros(len(y), int)
    for w in np.unique(walks):
        te = walks == w
        p[te] = fit(X[~te], y[~te])(X[te])
    return p


def bal(y, p):
    return float(np.mean([np.mean(p[y == c] == c) for c in (0, 1)]))


def fit_lr(Xtr, ytr, C=1.0):
    sc = StandardScaler().fit(Xtr)
    m = LogisticRegression(C=C, class_weight='balanced', max_iter=5000).fit(sc.transform(Xtr), ytr)
    return lambda Xte: m.predict(sc.transform(Xte))


def score(X, y, walks, n_perm, seed, fit=fit_lr):
    """Balanced accuracy left out by walk, and the within-walk permutation p."""
    obs = bal(y, lowo(X, y, walks, fit))
    rng = np.random.default_rng(seed); null = []
    for _ in range(n_perm):
        yp = y.copy()
        for w in np.unique(walks):
            k = np.flatnonzero(walks == w); yp[k] = yp[rng.permutation(k)]
        null.append(bal(yp, lowo(X, yp, walks, fit)))
    null = np.array(null)
    return dict(ba=round(obs, 3), p=round(float((1 + np.sum(null >= obs - 1e-12)) / (1 + n_perm)), 4),
                null_mean=round(float(null.mean()), 3), null_95=round(float(np.percentile(null, 95)), 3))


def facing(meta, Z, cdr, design, n_perm, drop_walks=()):
    stops = [i for i, r in enumerate(meta) if r['kind'] == 'stop' and r['walk'] not in drop_walks]
    rows, refs = referenced(meta, stops, design)
    y = np.array([int(meta[i]['facing'] >= 90) for i in rows])
    walks = np.array([meta[i]['walk'] for i in rows])
    # Only walks that hold both classes can be scored when left out; the rest still train.
    jobs = {}
    for notch in ('clean', 'notch'):
        for inp in INPUTS:
            for d in DEPTHS:
                V = Z[f'{inp}|{notch}|{d}']
                jobs[(notch, inp, d, 'lr')] = np.array([V[i] - V[r].mean(0) for i, r in zip(rows, refs)])
                jobs[(notch, inp, d, 'far')] = np.array([[1 - cos(V[i], V[r].mean(0))] for i, r in zip(rows, refs)])
    for k in CDR_KEYS:
        jobs[('base', 'cdr', k, '1d')] = np.array([[cdr[i][k] - np.mean([cdr[j][k] for j in r])] for i, r in zip(rows, refs)])
    n_lr = max(200, n_perm // 5)
    keys = list(jobs)
    res = Parallel(n_jobs=-1)(delayed(score)(jobs[k], y, walks, n_lr if k[-1] == 'lr' else n_perm,
                                             zlib.crc32('|'.join(k).encode())) for k in keys)
    out = dict(zip(keys, res))
    # Jay's earlier test: the final embedding (both channels' mean, clean) against the walk's first facing-0 stop.
    E = Z['mean|clean|emb']; orow, oval = [], []
    for w in dict.fromkeys(meta[i]['walk'] for i in stops):
        ws = [i for i in stops if meta[i]['walk'] == w]
        first = min((i for i in ws if meta[i]['facing'] == 0), key=lambda i: meta[i]['t0'], default=None)
        if first is not None:
            for i in ws:
                if i != first:
                    orow.append(i); oval.append([cos(E[i], E[first])])
    yo = np.array([int(meta[i]['facing'] >= 90) for i in orow]); wo = np.array([meta[i]['walk'] for i in orow])
    if len(set(wo[yo == 0])) >= 2:  # a threshold needs toward stops in at least two walks besides their openers
        out[('base', 'opener', 'emb cos', '1d')] = dict(score(np.array(oval), yo, wo, n_perm, 7),
                                                        n=len(orow), n_turned=int(yo.sum()))
    # Sensitivity of the main probe to its one fixed setting, on the real labels only (not used to choose anything).
    sens = {d: {str(C): round(bal(y, lowo(jobs[('clean', 'mean', d, 'lr')], y, walks,
                                          lambda a, b, C=C: fit_lr(a, b, C))), 3) for C in (0.01, 1.0, 100.0)}
            for d in DEPTHS}
    info = dict(design=design, n=len(rows), n_turned=int(y.sum()), n_toward=int((1 - y).sum()), walks=len(set(walks)),
                speech_s_mean=round(float(np.mean([meta[i]['speech_s'] for i in rows])), 1),
                dropped_walks=list(drop_walks),
                set_aside=[f"{meta[i]['walk'][5:]} {meta[i]['spot']} facing {meta[i]['facing']}" for i in stops if i not in rows])
    per = [dict(walk=meta[i]['walk'][5:], spot=meta[i]['spot'], facing=meta[i]['facing'], speech_s=meta[i]['speech_s'],
                cdr=round(float(jobs[('base', 'cdr', 'cdr', '1d')][n, 0]), 2),
                emb_far=round(float(jobs[('clean', 'mean', 'emb', 'far')][n, 0]), 4))
           for n, i in enumerate(rows)]
    return dict(info=info, n_perm=n_perm, n_perm_lr=n_lr, probes={'|'.join(k): v for k, v in out.items()},
                lr_C_sensitivity=sens, per_stop=per)


def fit_ridge(Xtr, ytr, wtr):
    """Ridge with alpha picked by leave-one-walk-out inside the training walks."""
    grid = 10.0 ** np.arange(-2, 6)

    def make(a, X, y):
        sc = StandardScaler().fit(X); m = Ridge(alpha=a).fit(sc.transform(X), y)
        return lambda Xt: m.predict(sc.transform(Xt))
    err = []
    for a in grid:
        e = []
        for w in np.unique(wtr):
            te = wtr == w
            e += list(np.abs(make(a, Xtr[~te], ytr[~te])(Xtr[te]) - ytr[te]))
        err.append(np.mean(e))
    a = grid[int(np.argmin(err))]
    return make(a, Xtr, ytr), float(a)


def distance(meta, Z, cdr):
    lad = [i for i, r in enumerate(meta) if r['kind'] == 'ladder']
    opener = {}
    for i in lad:
        opener.setdefault(meta[i]['walk'], i)  # LADDERS lists each walk's steps in time order
    rows = [i for i in lad if opener[meta[i]['walk']] != i]
    y = np.array([np.log2(meta[i]['dist_m'] / meta[opener[meta[i]['walk']]]['dist_m']) for i in rows])
    walks = np.array([meta[i]['walk'] for i in rows])

    def summary(pred):
        rho = [spearmanr(pred[walks == w], y[walks == w])[0] if np.ptp(pred[walks == w]) > 0 else np.nan
               for w in np.unique(walks) if (walks == w).sum() >= 2]
        return dict(mae_dbl=round(float(np.mean(np.abs(pred - y))), 3),
                    within_1p5x=f'{int(np.sum(np.abs(pred - y) <= np.log2(1.5)))} of {len(y)}',
                    rho_per_walk=[None if np.isnan(r) else round(float(r), 2) for r in rho])
    out = {}
    dR = np.array([cdr[i]['range'] - cdr[opener[meta[i]['walk']]]['range'] for i in rows])
    out['CdrRange law (-20 dB/decade)'] = summary(-dR / 20 * np.log2(10))
    out['everyone at the opener'] = summary(np.zeros(len(y)))
    out["the training walks' mean"] = summary(np.array([y[walks != w].mean() for w in walks]))
    for notch in ('clean', 'notch'):
        for d in DEPTHS:
            V = Z[f'mean|{notch}|{d}']
            X = np.array([V[i] - V[opener[meta[i]['walk']]] for i in rows])
            pred, alphas = np.zeros(len(y)), []
            for w in np.unique(walks):
                te = walks == w
                f, a = fit_ridge(X[~te], y[~te], walks[~te]); pred[te] = f(X[te]); alphas.append(a)
            out[f'{d} ({notch})'] = dict(summary(pred), alphas=alphas)
    info = dict(n=len(rows), walks=len(set(walks)),
                steps={w[5:]: [meta[i]['dist_m'] for i in lad if meta[i]['walk'] == w] for w in opener})
    return dict(info=info, results=out)


def lines_for(name, F):
    i, P = F['info'], F['probes']
    L = [f"\nFACING [{name}]: {i['n']} stops in {i['walks']} walks ({i['n_toward']} toward, {i['n_turned']} turned), "
         f"{i['speech_s_mean']} s speech each; set aside {len(i['set_aside'])}"]
    for k in CDR_KEYS:
        r = P[f'base|cdr|{k}|1d']; L.append(f"  baseline {CDR_KEYS[k]:36s} {r['ba']:.2f}  p {r['p']:.3f}")
    if 'base|opener|emb cos|1d' in P:
        r = P['base|opener|emb cos|1d']
        L.append(f"  baseline embedding cos vs walk's first facing stop {r['ba']:.2f}  p {r['p']:.3f}  (n {r['n']})")
    for notch in ('clean', 'notch'):
        for inp in INPUTS:
            L.append(f'  {notch:5s} {inp:4s} ' + ' '.join(
                f"{d} {P[f'{notch}|{inp}|{d}|lr']['ba']:.2f}/{P[f'{notch}|{inp}|{d}|lr']['p']:.3f}"
                f",{P[f'{notch}|{inp}|{d}|far']['ba']:.2f}/{P[f'{notch}|{inp}|{d}|far']['p']:.3f}" for d in DEPTHS))
    L.append('  lr at C = 0.01 / 1 / 100 (mean, clean): ' +
             '  '.join(f"{d} {'/'.join(map(str, v.values()))}" for d, v in F['lr_C_sensitivity'].items()))
    return L


def main():
    n_perm = int(sys.argv[1]) if len(sys.argv) > 1 else 1000
    allsp, quiet = load('vectors.npz'), load('vectors_nocallouts.npz')
    runs = {'all speech, facing-0 reference (the brief)': facing(*allsp, 'facing0', n_perm),
            'all speech, spot-mean reference': facing(*allsp, 'spotmean', n_perm),
            'no callouts, spot-mean reference': facing(*quiet, 'spotmean', n_perm),
            'no callouts, spot-mean reference, without 122038': facing(*quiet, 'spotmean', n_perm, ('walk-122038',))}
    dist = distance(*allsp)
    L = ['balanced accuracy left out by walk / p from within-walk shuffles; per depth: lr, far']
    for name, F in runs.items():
        L += lines_for(name, F)
    L.append(f"\nDISTANCE: {dist['info']['n']} ladder steps against their walk's opener, {dist['info']['walks']} walks")
    for k, v in dist['results'].items():
        L.append(f"  {k:30s} mean error {v['mae_dbl']:.2f} doublings, within 1.5x {v['within_1p5x']}, "
                 f"Spearman per walk {v['rho_per_walk']}")
    txt = '\n'.join(L)
    print(txt)
    (REPO / 'results/rotation/campp/probe.txt').write_text(txt + '\n')
    (REPO / 'results/rotation/campp/numbers.json').write_text(json.dumps(dict(facing=runs, distance=dist), indent=1))


if __name__ == '__main__':
    main()
