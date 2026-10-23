#!/usr/bin/env python3
"""Brief 20 steps 1-4 on the CDR reads (run_cdr.sh's output): the DRR law per room, range from the opener, turned heads,
and coarse facing. Writes summary.json; report.md is written from it.

Rows. dEchorate: room = wall setting, a "recording" = one setting x array (the phone stays, the talker moves over the 6
sources). STARSS23: room = roomNN, recording = file, talker = (class, source index), all speech onsets (solo ones
flagged), both capsule pairs (1-2, 3-4: 68.5 mm). LOCATA: one room, recording = recording x pair, talker = OptiTrack
talker; pairs 160 mm (the phone's), 80 mm, and 640 mm (locata_wide.py: the only one whose LF band is readable).

Bands: LF (0.1-1 kHz floored at c/2d: empty on every pair but 640 mm), LF_raw (not floored), MF, HF, ALL (floored) and
ALL_raw. The law: DRR = 20 log10(r_c / r); the CDR per band stands in for the DRR.

Step 1, per room and band: the free fit CDR = a + b log10 r (slope b, its standard error, the scatter about it), and
the law's fit with the slope held at -20 (r_c = 10^(mean(CDR + 20 log10 r) / 20), the scatter about that). A room's
band "fails outright" when its free slope isn't below 0 by two standard errors (no distance in it at all). dEchorate
also gets its RIRs' own DRR (dechorate_rir.py) through the same fits, and each setting's echo time.

Step 2, the opener: per recording, the first onset of a talker alone (STARSS: solo; LOCATA: no other talker active and
facing the array within 30 deg; dEchorate: every cut in turn, as it has no timeline). Every later read's predicted
distance ratio is 10^((CDR_opener - CDR) / 20); its error is log2(predicted / true ratio). Scored as batch A scored
range: same-talker pairs ordered (ratio >= 1.25 / 1.5 / 2), the spread between reads within 0.3 m of one spot, and
the step between reads 2x apart, here in predicted doublings (and in dB, as batch A's). Beside the law's error: the
no-information baseline (every later read at the opener's distance) and, as a diagnostic only, the error with the
CDR's own slope (fitted on the other recordings) in place of -20.
A recording fails outright when its median |error| is over a doubling; its reads are set aside, and listed.

Step 3 (LOCATA): CDR_band = a + b log10 r + c (facing / 180 deg), bootstrapped over recordings: c is how far each band
moves from facing the array to facing away, at a fixed distance. The flinging test: pairs of one talker's reads with
heads within 0.3 m and facing at least 60 deg apart (against at most 20 deg apart): the jump in predicted range.
Two compensations, scored as step 2: range from LF alone, and ALL - k (F - F_opener), F = HF - LF the facing estimate,
k fitted on the other recordings (leave one recording out).

Step 4 (LOCATA): facing from F - F_opener, log10 r as a covariate, logistic regression left out by recording. Rungs on
the unsigned facing (0 = toward): toward/away (90 deg); front/side/back (45, 135: the quadrants with the two sides
merged, because a two-mic cue, and LOCATA's unsigned truth, can't tell a left turn from a right); 45 deg steps.
Accuracy, balanced accuracy, chance (the majority share and 1/k), and a permutation p (labels shuffled within each
recording). A rung fails when p >= 0.05; the ladder stops at the first that fails.

usage: analyze.py <reads dir> <out summary.json>
"""
import json
import math
import statistics as st
import sys
from collections import defaultdict
from itertools import combinations
from pathlib import Path

import numpy as np

BANDS = ('LF', 'LF_raw', 'MF', 'HF', 'ALL', 'ALL_raw')
LOG2_10 = math.log2(10)
RNG = np.random.default_rng(0)


def load(d):
    d = Path(d)
    rows = []
    rir = json.loads((d / 'dechorate_rir.json').read_text())
    for f in sorted(d.glob('dechorate_*.jsonl')):
        for l in open(f):
            r = json.loads(l)
            rows.append({'ds': 'dechorate', 'room': r['room'], 'rec': f"{r['room']}/a{r['array']}", 'who': 'src',
                         'spot': f"s{r['src']}", 't': None, 'dist': r['dist_m'], 'xyz': None, 'facing': None, 'alone': True,
                         'pair': 155, 'cdr': r['cdr'], 'id': r['id'],
                         'drr_rir': rir[r['room']]['drr'][f"s{r['src']}/a{r['array']}"]})
    for f in sorted(d.glob('starss_*.jsonl')):
        pair = f.stem.split('_')[1]
        for l in open(f):
            r = json.loads(l)
            if not r.get('dist_cm'):
                continue
            dm = r['dist_cm'] / 100
            a, e = math.radians(r['az']), math.radians(r['el'])
            rows.append({'ds': 'starss23', 'room': r['room'], 'rec': f"{pair}/{r['file']}", 'who': (r['cls'], r['src']),
                         'spot': None, 't': r['onset_s'], 'dist': dm,
                         'xyz': [math.cos(e) * math.cos(a) * dm, math.cos(e) * math.sin(a) * dm, math.sin(e) * dm],
                         'facing': None, 'alone': bool(r['solo']), 'pair': pair, 'cdr': r['cdr'],
                         'id': f"{pair}/{r['file']}/{r['onset_s']}/{r['cls']}/{r['src']}", 'overlap': len(r['others'])})
    f = d / 'locata.jsonl'
    if f.exists():
        for l in open(f):
            r = json.loads(l)
            t = r['truth']
            rows.append({'ds': 'locata', 'room': f"locata {r['pair_mm']}mm", 'rec': f"{r['set']}_{r['task']}_{r['recording']}/{r['pair_mm']}",
                         'who': r['talker'], 'spot': None, 't': r['onset_s'], 'dist': t['dist_m'], 'xyz': t['head'],
                         'facing': t['facing_deg'], 'alone': not t['others'], 'pair': r['pair_mm'], 'cdr': r['cdr'],
                         'id': r['id'], 'overlap': len(t['others'])})
    return rows


def fit(x, y):
    """y = a + b x: (a, b, se_b, residual sd)."""
    x, y = np.asarray(x, float), np.asarray(y, float)
    A = np.c_[np.ones_like(x), x]
    coef, *_ = np.linalg.lstsq(A, y, rcond=None)
    res = y - A @ coef
    n = len(x)
    s2 = float(res @ res) / max(n - 2, 1)
    se = math.sqrt(s2 / max(float(((x - x.mean()) ** 2).sum()), 1e-12))
    return float(coef[0]), float(coef[1]), se, float(res.std())


def law(dist, y):
    lr = np.log10(dist)
    a, b, se, sd = fit(lr, y)
    k = np.asarray(y) + 20 * lr
    return {'n': len(y), 'slope': round(b, 2), 'slope_se': round(se, 2), 'intercept_db': round(a, 2), 'scatter_db': round(sd, 2),
            'rc_m_at_-20': round(10 ** (float(k.mean()) / 20), 3), 'scatter_at_-20_db': round(float(k.std()), 2),
            'fails': not (b + 2 * se < 0)}


def step1(rows):
    out = defaultdict(dict)
    by = defaultdict(list)
    for r in rows:
        if r['ds'] == 'starss23' and not r['alone']:
            continue
        by[(r['ds'], r['room'])].append(r)
    for (ds, room), g in sorted(by.items()):
        res = {'dist_range_m': [round(min(r['dist'] for r in g), 2), round(max(r['dist'] for r in g), 2)]}
        for b in BANDS:
            v = [(r['dist'], r['cdr'][b]) for r in g if r['cdr'].get(b) is not None]
            if len(v) >= 10:
                res[b] = law(*zip(*v))
        if ds == 'dechorate':
            res['rir_drr'] = {b: law([r['dist'] for r in g], [r['drr_rir'][b] for r in g])
                              for b in ('LF', 'MF', 'HF', 'ALL')}
            # the CDR against the RIRs' DRR: how much of the true DRR's swing the CDR follows
            res['cdr_vs_rir_drr'] = {b: round(fit([r['drr_rir'][b2] for r in g], [r['cdr'][b] for r in g])[1], 2)
                                     for b, b2 in (('MF', 'MF'), ('ALL', 'ALL'), ('HF', 'HF'), ('LF_raw', 'LF'))}
        out[ds][room] = res
    return out


def openers(rows):
    """Per recording: the opener row and the later rows."""
    rec = defaultdict(list)
    for r in rows:
        rec[r['rec']].append(r)
    out = []
    for k, g in sorted(rec.items()):
        if g[0]['ds'] == 'dechorate':
            out.append((k, None, g))
            continue
        g.sort(key=lambda r: r['t'])
        ok = [r for r in g if r['alone'] and (r['facing'] is None or r['facing'] <= 30)]
        if not ok:
            continue
        o = ok[0]
        out.append((k, o, [r for r in g if r['t'] > o['t']]))
    return out


def val(r, band, comp=None):
    if comp is None:
        return r['cdr'].get(band)
    return comp(r)


def loro_slopes(rows, band, comp=None):
    """Per recording: the CDR's own dB per decade, from the other recordings of its dataset (each centred on its own
    mean, so rooms' offsets don't count). A diagnostic of the law's -20, not a replacement for it."""
    by = defaultdict(list)
    for r in rows:
        v = val(r, band, comp)
        if v is not None:
            by[(r['ds'], r['rec'])].append((math.log10(r['dist']), v))
    cen = {}
    for k, g in by.items():
        x, y = np.array(g).T
        cen[k] = (x - x.mean(), y - y.mean())
    out = {}
    for (ds, rec) in by:
        X = np.concatenate([cen[k][0] for k in cen if k[0] == ds and k[1] != rec])
        Y = np.concatenate([cen[k][1] for k in cen if k[0] == ds and k[1] != rec])
        out[rec] = float(X @ Y / (X @ X))
    return out


def step2(rows, band, comp=None, ds_filter=None):
    """Ratio error, ordering, spread, step, per dataset; recordings failing outright are set aside. Beside the law's
    error: the no-information baseline (every ratio 1: the opener's distance for everyone) and the error with the CDR's
    own slope (loro_slopes) in place of -20."""
    errs = defaultdict(list)
    per_rec = {}
    slopes = loro_slopes(rows, band, comp)
    for k, o, later in openers(rows):
        if ds_filter and later and later[0]['ds'] != ds_filter:
            continue
        e = []                       # (read, dB below the opener, true log2 ratio)
        if o is None:                # dEchorate: every cut as the opener in turn
            vals = [(r, val(r, band, comp)) for r in later]
            vals = [(r, v) for r, v in vals if v is not None]
            for (ra, va), (rb, vb) in combinations(vals, 2):
                e.append((rb, va - vb, math.log2(rb['dist'] / ra['dist'])))
                e.append((ra, vb - va, math.log2(ra['dist'] / rb['dist'])))
        else:
            vo = val(o, band, comp)
            if vo is None:
                continue
            for r in later:
                v = val(r, band, comp)
                if v is not None:
                    e.append((r, vo - v, math.log2(r['dist'] / o['dist'])))
        if not e:
            continue
        ds = (o or later[0])['ds']
        law_e = [dl / 20 * LOG2_10 - tl for _, dl, tl in e]
        med = st.median(abs(x) for x in law_e)
        per_rec[k] = {'ds': ds, 'room': later[0]['room'], 'n': len(e), 'median_abs_err_doublings': round(med, 2),
                      'bias_doublings': round(st.median(law_e), 2), 'fails': med > 1.0,
                      'opener_dist_m': None if o is None else o['dist']}
        if med <= 1.0:
            sl = min(slopes.get(k, -20.0), -0.5)
            errs[ds].extend((r, x, -tl, dl / -sl * LOG2_10 - tl) for (r, dl, tl), x in zip(e, law_e))
    res = {}
    for ds, e in errs.items():
        a = [abs(x[1]) for x in e]
        res[ds] = {'reads': len(e), 'median_abs_err_doublings': round(st.median(a), 2),
                   'median_factor': round(2 ** st.median(a), 2), 'bias_doublings': round(st.median(x[1] for x in e), 2),
                   'within_1.5x_pct': round(100 * np.mean([x <= math.log2(1.5) for x in a]), 1),
                   'within_2x_pct': round(100 * np.mean([x <= 1 for x in a]), 1),
                   'baseline_ratio1_median_abs_doublings': round(st.median(abs(x[2]) for x in e), 2),
                   'baseline_ratio1_within_1.5x_pct': round(100 * np.mean([abs(x[2]) <= math.log2(1.5) for x in e]), 1),
                   'own_slope_median_abs_doublings': round(st.median(abs(x[3]) for x in e), 2),
                   'own_slope_within_1.5x_pct': round(100 * np.mean([abs(x[3]) <= math.log2(1.5) for x in e]), 1),
                   'true_ratio_beyond_1.5x_pct': round(100 * np.mean([abs(x[2]) > math.log2(1.5) for x in e]), 1)}
        far = [x for x in e if abs(x[2]) >= 1]        # reads at least 2x nearer or farther than the opener
        if far:
            res[ds]['reads_2x_from_opener'] = len(far)
            res[ds]['law_median_abs_doublings_2x_from_opener'] = round(st.median(abs(x[1]) for x in far), 2)
            res[ds]['own_slope_median_abs_doublings_2x_from_opener'] = round(st.median(abs(x[3]) for x in far), 2)
        bad = [x for x in e if abs(x[1]) > 1]
        res[ds]['outliers_over_2x'] = len(bad)
        if ds != 'dechorate':
            bad = [x[0] for x in bad]
            res[ds]['outliers_by_cause'] = {
                'another talker active': sum(1 for r in bad if r.get('overlap')),
                'facing away (>90 deg)': sum(1 for r in bad if (r['facing'] or 0) > 90 and not r.get('overlap')),
                'nearer than 1 m': sum(1 for r in bad if r['dist'] < 1 and not r.get('overlap') and (r['facing'] or 0) <= 90),
                'other': sum(1 for r in bad if not r.get('overlap') and (r['facing'] or 0) <= 90 and r['dist'] >= 1)}
    failed = sorted(k for k, v in per_rec.items() if v['fails'])
    keep = {r['id'] for r in rows if r['rec'] not in failed}
    order = ordering(rows, band, comp, keep)
    for ds in res:
        res[ds].update(order.get(ds, {}))
    return {'by_dataset': res, 'recordings_failed': {k: per_rec[k] for k in failed},
            'recordings': len(per_rec), 'per_recording': per_rec}


def ordering(rows, band, comp, keep):
    """Batch A's range score on one band's predicted range: same-talker pairs."""
    g = defaultdict(list)
    for r in rows:
        if r['id'] in keep:
            v = val(r, band, comp)
            if v is not None:
                g[(r['ds'], r['rec'], r['who'])].append((r, v))
    res = defaultdict(lambda: {'o': {1.25: [0, 0], 1.5: [0, 0], 2.0: [0, 0]}, 'same': [], 'far': []})
    for (ds, _, _), grp in g.items():
        R = res[ds]
        for (a, va), (b, vb) in combinations(grp, 2):
            ratio = max(a['dist'], b['dist']) / min(a['dist'], b['dist'])
            diff = va - vb
            if ratio >= 1.25 and diff != 0:
                right = (diff > 0) == (a['dist'] < b['dist'])
                for th in R['o']:
                    if ratio >= th:
                        R['o'][th][0] += right; R['o'][th][1] += 1
            near = (a['spot'] == b['spot']) if ds == 'dechorate' else math.dist(a['xyz'], b['xyz']) <= 0.3
            if near:
                R['same'].append(abs(diff))
            if ratio >= 2:
                R['far'].append(abs(diff))
    out = {}
    for ds, R in res.items():
        out[ds] = {'ordering_pct': {f'{th}x': round(100 * k / n, 1) if n else None for th, (k, n) in R['o'].items()},
                   'ordering_pairs_2x': R['o'][2.0][1],
                   'spread_one_spot_db': round(st.median(R['same']), 2) if R['same'] else None,
                   'step_at_2x_db': round(st.median(R['far']), 2) if R['far'] else None,
                   'spread_one_spot_doublings': round(st.median(R['same']) / 20 * LOG2_10, 2) if R['same'] else None,
                   'step_at_2x_doublings': round(st.median(R['far']) / 20 * LOG2_10, 2) if R['far'] else None}
    return out


def lf_band(pair):
    return 'LF' if pair == 640 else 'LF_raw'


def step3(rows):
    out = {}
    for pair in (160, 80, 640):
        g = [r for r in rows if r['ds'] == 'locata' and r['pair'] == pair]
        recs = sorted({r['rec'] for r in g})
        res = {}
        for b in BANDS + ('F',):
            def y(r):
                if b == 'F':
                    lf = r['cdr'].get(lf_band(pair))
                    return None if lf is None or r['cdr']['HF'] is None else r['cdr']['HF'] - lf
                return r['cdr'].get(b)
            v = [(r['rec'], math.log10(r['dist']), r['facing'] / 180, y(r)) for r in g if y(r) is not None]
            if len(v) < 20:
                continue

            def coef(sel):
                A = np.array([[1, x[1], x[2]] for x in sel]); Y = np.array([x[3] for x in sel])
                return np.linalg.lstsq(A, Y, rcond=None)[0]
            c = coef(v)
            boots = []
            for _ in range(300):
                pick = RNG.choice(recs, len(recs))
                sel = [x for rr in pick for x in v if x[0] == rr]
                boots.append(coef(sel))
            boots = np.array(boots)
            res[b] = {'n': len(v), 'per_decade_db': round(float(c[1]), 2), 'facing_away_db': round(float(c[2]), 2),
                      'facing_away_ci95': [round(float(q), 2) for q in np.percentile(boots[:, 2], [2.5, 97.5])],
                      'per_decade_ci95': [round(float(q), 2) for q in np.percentile(boots[:, 1], [2.5, 97.5])]}
        # the flinging test
        fl = {}
        for b in ('LF', 'LF_raw', 'MF', 'HF', 'ALL', 'ALL_raw'):
            turned, still = [], []
            grp = defaultdict(list)
            for r in g:
                if r['cdr'].get(b) is not None:
                    grp[(r['rec'], r['who'])].append(r)
            for gg in grp.values():
                for a, c2 in combinations(gg, 2):
                    if math.dist(a['xyz'], c2['xyz']) <= 0.3:
                        j = abs(a['cdr'][b] - c2['cdr'][b]) / 20 * LOG2_10
                        df = abs(a['facing'] - c2['facing'])
                        if df >= 60:
                            turned.append(j)
                        elif df <= 20:
                            still.append(j)
            if turned:
                fl[b] = {'pairs_turned': len(turned), 'jump_turned_doublings': round(st.median(turned), 2),
                         'jump_turned_factor': round(2 ** st.median(turned), 2),
                         'pairs_still': len(still), 'jump_still_doublings': round(st.median(still), 2) if still else None,
                         'jump_still_factor': round(2 ** st.median(still), 2) if still else None}
        out[f'{pair}mm'] = {'facing_regression': res, 'flinging': fl}
    return out


def compensations(rows):
    """Step 3's two compensations, scored as step 2 and by the flinging test, per LOCATA pair."""
    out = {}
    for pair in (160, 80, 640):
        g = [r for r in rows if r['ds'] == 'locata' and r['pair'] == pair]
        lfb = lf_band(pair)
        F = lambda r: None if r['cdr'].get(lfb) is None or r['cdr']['HF'] is None else r['cdr']['HF'] - r['cdr'][lfb]
        ops = {k: o for k, o, _ in openers(g)}
        ks = {}
        for rec in {r['rec'] for r in g}:          # k from the other recordings: ALL = a + b log10 r + k (F - F_opener)
            sel = []
            for r in g:
                o = ops.get(r['rec'])
                if r['rec'] == rec or o is None or F(r) is None or F(o) is None:
                    continue
                sel.append([1, math.log10(r['dist']), F(r) - F(o), r['cdr']['ALL']])
            A = np.array(sel)
            ks[rec] = float(np.linalg.lstsq(A[:, :3], A[:, 3], rcond=None)[0][2])

        def corr(r):
            o = ops.get(r['rec'])
            if o is None or F(r) is None or F(o) is None or r['cdr']['ALL'] is None:
                return None
            return r['cdr']['ALL'] - ks[r['rec']] * (F(r) - F(o))
        res = {'k_median': round(st.median(ks.values()), 2)}
        for name, band, comp in (('ALL', 'ALL', None), ('LF alone', lfb, None), ('ALL corrected by HF-LF', None, corr)):
            s = step2(g, band, comp)
            jt = fling(g, band, comp)
            res[name] = {**s['by_dataset'].get('locata', {}), 'recordings_failed': len(s['recordings_failed']), **jt}
        out[f'{pair}mm'] = res
    return out


def fling(g, band, comp):
    turned, still = [], []
    grp = defaultdict(list)
    for r in g:
        v = val(r, band, comp)
        if v is not None:
            grp[(r['rec'], r['who'])].append((r, v))
    for gg in grp.values():
        for (a, va), (b, vb) in combinations(gg, 2):
            if math.dist(a['xyz'], b['xyz']) <= 0.3:
                j = abs(va - vb) / 20 * LOG2_10
                df = abs(a['facing'] - b['facing'])
                (turned if df >= 60 else still if df <= 20 else []).append(j)
    return {'fling_turned_doublings': round(st.median(turned), 2) if turned else None,
            'fling_still_doublings': round(st.median(still), 2) if still else None}


def step4(rows):
    from sklearn.linear_model import LogisticRegression
    rungs = [('toward / away (90 deg)', [90]), ('front / side / back (45, 135 deg)', [45, 135]),
             ('45 deg steps', [45, 90, 135])]
    out = {}
    for pair in (160, 640, 80):
        g = [r for r in rows if r['ds'] == 'locata' and r['pair'] == pair]
        lfb = lf_band(pair)
        F = lambda r: None if r['cdr'].get(lfb) is None or r['cdr']['HF'] is None else r['cdr']['HF'] - r['cdr'][lfb]
        ops = {k: o for k, o, _ in openers(g)}
        data = [(r['rec'], F(r) - F(ops[r['rec']]), math.log10(r['dist']), r['facing']) for r in g
                if r['rec'] in ops and F(r) is not None and F(ops[r['rec']]) is not None and r is not ops[r['rec']]]
        recs = np.array([d[0] for d in data]); X = np.array([[d[1], d[2]] for d in data]); fac = np.array([d[3] for d in data])
        res = []
        for name, edges in rungs:
            y = np.digitize(fac, edges)

            def loro(yy):
                pred = np.empty_like(yy)
                for rec in np.unique(recs):
                    tr, te = recs != rec, recs == rec
                    if len(np.unique(yy[tr])) < 2:
                        pred[te] = np.bincount(yy[tr]).argmax(); continue
                    m = LogisticRegression(max_iter=1000).fit((X[tr] - X[tr].mean(0)) / X[tr].std(0), yy[tr])
                    pred[te] = m.predict((X[te] - X[tr].mean(0)) / X[tr].std(0))
                return pred
            pred = loro(y)
            k = len(edges) + 1
            bal = lambda yy, pp: float(np.mean([np.mean(pp[yy == c] == c) for c in range(k) if (yy == c).any()]))
            acc, ba = float(np.mean(pred == y)), bal(y, pred)
            perm = []
            for _ in range(100):
                yp = y.copy()
                for rec in np.unique(recs):
                    i = np.flatnonzero(recs == rec); yp[i] = yp[RNG.permutation(i)]
                perm.append(bal(yp, loro(yp)))
            p = (1 + sum(x >= ba for x in perm)) / (1 + len(perm))
            # the distance covariate alone: what facing adds beyond it
            res.append({'rung': name, 'n': len(y), 'classes': [int((y == c).sum()) for c in range(k)],
                        'accuracy_pct': round(100 * acc, 1), 'balanced_pct': round(100 * ba, 1),
                        'chance_majority_pct': round(100 * np.bincount(y).max() / len(y), 1), 'chance_uniform_pct': round(100 / k, 1),
                        'perm_p': round(p, 3), 'fails': p >= 0.05})
            if p >= 0.05:
                break
        out[f'{pair}mm'] = res
    return out


def main():
    rows = load(sys.argv[1])
    S = {'rows': {ds: sum(1 for r in rows if r['ds'] == ds) for ds in ('dechorate', 'starss23', 'locata')}}
    S['step1'] = step1(rows)
    rir = json.loads((Path(sys.argv[1]) / 'dechorate_rir.json').read_text())
    from scipy.stats import spearmanr
    S['step1_dechorate_rc_vs_t60'] = {}
    for b in ('MF', 'ALL', 'LF_raw', 'HF'):
        rooms = sorted(S['step1']['dechorate'])
        t60 = [rir[r]['t60']['LF' if b == 'LF_raw' else b] for r in rooms]
        rc = [S['step1']['dechorate'][r][b]['rc_m_at_-20'] for r in rooms]
        rc_rir = [S['step1']['dechorate'][r]['rir_drr']['LF' if b == 'LF_raw' else b]['rc_m_at_-20'] for r in rooms]
        S['step1_dechorate_rc_vs_t60'][b] = {
            't60_s': dict(zip(rooms, t60)), 'cdr_rc_m': dict(zip(rooms, rc)), 'rir_rc_m': dict(zip(rooms, rc_rir)),
            'cdr_rc_spearman': round(float(spearmanr(t60, rc)[0]), 2), 'rir_rc_spearman': round(float(spearmanr(t60, rc_rir)[0]), 2),
            'cdr_rc_loglog_slope': round(float(np.polyfit(np.log10(t60), np.log10(rc), 1)[0]), 2),
            'rir_rc_loglog_slope': round(float(np.polyfit(np.log10(t60), np.log10(rc_rir), 1)[0]), 2)}   # Sabine: -0.5
    S['step2'] = {}
    for b in BANDS:
        s = step2(rows, b)
        S['step2'][b] = {'by_dataset': s['by_dataset'], 'recordings': s['recordings'],
                         'recordings_failed': s['recordings_failed']}
    # STARSS: solo later reads only, as a check on what overlaps cost
    solo = [r for r in rows if r['ds'] != 'starss23' or r['alone']]
    S['step2_starss_solo_only'] = {b: step2([r for r in solo if r['ds'] == 'starss23'], b)['by_dataset'] for b in ('MF', 'ALL', 'ALL_raw', 'HF')}
    S['step2_locata_by_pair'] = {p: {b: step2([r for r in rows if r['ds'] == 'locata' and r['pair'] == p], b)['by_dataset'].get('locata')
                                     for b in BANDS} for p in (160, 80, 640)}
    S['step3'] = step3(rows)
    S['step3_compensations'] = compensations(rows)
    S['step4'] = step4(rows)
    Path(sys.argv[2]).write_text(json.dumps(S, indent=1, default=str))
    print(json.dumps({k: S[k] for k in ('rows', 'step3_compensations', 'step4')}, indent=1, default=str))


if __name__ == '__main__':
    main()
