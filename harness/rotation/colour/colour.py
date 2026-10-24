#!/usr/bin/env python3
"""Brief A, steps 3-8: how rotation changes the colour of speech, against how distance does (2026-10-24).

Reads harness/rotation/colour/facing_stops_signed.json and results/rotation/colour/windows/<walk>.json (from
octave_windows.py). Per stop, the speech windows (total power 1.1-8 kHz at least 10 dB over the tape's 20th
percentile, as facing_pooled.py) are summed and, per band, four quantities are taken once: the direct level, the
diffuse level, the total level (each dB per speech window) and the CDR (direct over diffuse). Everything is taken
against the same spot's facing-0 stops. Writes results/rotation/colour/numbers.json and the figures; prints a summary.

Note that a CDR contrast IS a direct colour against a diffuse colour: CDR_hi - CDR_lo = (Dir_hi - Dir_lo) - (Dif_hi -
Dif_lo), since each band's CDR is its direct level minus its diffuse level. So the two families the brief names are one.
"""
import itertools
import json
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[3]
OUT = REPO / 'results/rotation/colour'
SIGNED = json.loads((REPO / 'harness/rotation/colour/facing_stops_signed.json').read_text())

# segments in octave_windows.py: 88 100 177 354 707 1100 1414 2000 2828 4000 8000 Hz
OCT = {'125': [0, 1], '250': [2], '500': [3], '1k': [4, 5], '2k': [6, 7], '4-8k': [9]}
EXTRA = {'0.1-1.1k': [1, 2, 3, 4], '1.1-2k': [5, 6], '2-4k': [7, 8]}
BANDS = {**OCT, **EXTRA}
CENTRE = {'125': 125, '250': 250, '500': 500, '1k': 1000, '2k': 2000, '4-8k': 5657, '0.1-1.1k': 330, '1.1-2k': 1480,
          '2-4k': 2830}
Q = ('dir', 'dif', 'tot', 'cdr')
CCW = {'walk-213304', 'walk-224302'}   # the walks Jay turned counterclockwise; the rest turn clockwise (his default)
START_S = 2.5   # the record-start transient: on 8 of the 15 two-channel tapes the first 2 s read a 4-8 kHz CDR over 12 dB (up to 27),
                # the phone being handled, not a talker at 2 m. Those windows are set aside on every tape.
LADDERS = {  # facing_vs_distance.py's, copied (importing it would rewrite its results file)
    'walk-213304': [[4, 20, 2], [20, 42, 3], [42, 63, 5], [63, 78, 7]],
    'walk-221126': [[0, 12, 1], [12, 21, 2], [21, 29, 3], [29, 36, 4], [36, 43, 5], [43, 47, 6], [47, 59, 7], [59, 66, 8]],
    'walk-020305': [[2, 18, 1], [18, 54, 2], [54, 90, 3.5]],
    'walk-224302': [[0, 13, 4.5], [13, 35, 2], [35, 78, 6]],
}
TURNS = {  # continuous turns: decode spans of a full circle, and a facing-the-phone stretch before it as reference
    'walk-160546': {'circles': [[16.1, 33.0]], 'ref': [5.6, 16.0], 'said': "'rotating counterclockwise as I'm talking' (16.1 s) ... 'I just did an entire circle' (30-35 s)"},
    'walk-161331': {'circles': [[8.2, 21.4]], 'ref': [0.0, 8.2], 'said': "'rotate clockwise this time slowly while I'm talking' (8.2 s) ... 'now I'm facing the phone again' (21.4 s); folded, 111 mm"},
    'walk-044350': {'circles': [[11.0, 20.0], [23.0, 35.0], [78.0, 87.0]], 'ref': [0.0, 11.0], 'said': "'rotate clockwise in the same spot' (11-20 s, 'end of rotation'); 'rotating counterclockwise while I'm talking' (23 s, then moves off ~35 s); 'rotating, talking clockwise ... now facing the front' (78-87 s), between walks"},
    'walk-140956': {'circles': [], 'ref': None, 'said': "reads the Second Amendment text while turning; the decode calls only '90 degrees counterclockwise' (0 s), no circle"},
    'walk-221126': {'circles': [[228.1, 236.6]], 'ref': [221.1, 228.0], 'said': "'I'm rotating counter[clockwise] ... I'm talking ... entire time' (228.1 s) ... 'now [facing the phone] again' (233.6-236.6 s); 6 m"},
    'walk-020305': {'circles': [[125.7, 138.1]], 'ref': [90.0, 119.5], 'said': "'now dead center' (125.7 s) ... 'counterclockwise' (128.4 s) ... 'now dead center' (138.1 s); small carpeted room"},
}
MONO = {'walk-171542': "the second channel is digital silence for the whole tape (.raw and .wav alike): one capsule, no CDR"}
_cache = {}


def lin(a):
    return 10 ** (np.asarray(a, float) / 10)


def load(walk):
    if walk not in _cache:
        w = json.loads((OUT / 'windows' / f'{walk}.json').read_text())
        D, R, P = lin(w['dir_db']), lin(w['dif_db']), lin(w['pow_db'])
        tot = 10 * np.log10(P[:, 5:].sum(1)); t0 = np.array(w['t0'])
        w.update(t0=t0, D=D, R=R, P=P, voiced=(tot >= np.percentile(tot, 20) + 10) & (t0 >= START_S))
        _cache[walk] = w
    return _cache[walk]


def ill(walk, band):
    w = load(walk)
    return any(w['segments'][s]['ill_conditioned'] for s in BANDS[band])


def quant(D, R, P, n):
    """Per band: dir, dif, tot (dB per speech window) and cdr (dB), from summed linear powers (rows = windows)."""
    out = {}
    for b, s in BANDS.items():
        d, r, p = D[:, s].sum(), R[:, s].sum(), P[:, s].sum()
        out[b] = {'dir': 10 * np.log10(d / n), 'dif': 10 * np.log10(r / n), 'tot': 10 * np.log10(p / n),
                  'cdr': 10 * np.log10(d / r)}
    return out


def pool(walk, a, b):
    w = load(walk)
    m = w['voiced'] & (w['t0'] >= a) & (w['t0'] + w['win_s'] <= b)
    if m.sum() < 2:
        return None, 0
    return quant(w['D'][m], w['R'][m], w['P'][m], m.sum()), int(m.sum())


def per_window(walk, a, b):
    w = load(walk)
    m = w['voiced'] & (w['t0'] >= a) & (w['t0'] + w['win_s'] <= b)
    return [quant(w['D'][i:i + 1], w['R'][i:i + 1], w['P'][i:i + 1], 1) for i in np.flatnonzero(m)]


def room_of(walk):
    for r, ws in SIGNED['rooms'].items():
        if r != 'note' and walk in ws:
            return r


def stops():
    rows = []
    for walk, spots in SIGNED['stops'].items():
        for spot, st in spots.items():
            for a, b, fu, fs, how in st:
                q, n = pool(walk, a, b)
                if q is None:
                    continue
                rows.append(dict(walk=walk, spot=spot, dist=float(spot.rstrip('m')), room=room_of(walk), t0=a, t1=b,
                                 unsigned=fu, signed=fs, how=how, n=n, q=q))
    for key in {(r['walk'], r['spot']) for r in rows}:          # degrees turned since facing the phone, and the leg
        seen_turn = False
        for r in sorted([r for r in rows if (r['walk'], r['spot']) == key], key=lambda r: r['t0']):
            if r['unsigned'] == 0:
                r['progress'] = 360 if seen_turn else 0
            else:
                seen_turn = True
                r['progress'] = None if r['signed'] is None else (360 - r['signed']) % 360 if r['walk'] in CCW else r['signed']
            r['leg'] = (None if r['progress'] is None else 'facing' if r['progress'] in (0, 360) else
                        'out' if r['progress'] < 180 else 'away' if r['progress'] == 180 else 'back')
    for key in {(r['walk'], r['spot']) for r in rows}:          # each against its spot's facing-0 stops
        st = [r for r in rows if (r['walk'], r['spot']) == key]
        ref = [r for r in st if r['unsigned'] == 0]
        for r in st:
            r['has_ref'] = bool(ref)
            r['d'] = {b: {k: r['q'][b][k] - np.mean([x['q'][b][k] for x in ref]) for k in Q} for b in BANDS} if ref else None
    return rows


# ---- contrasts --------------------------------------------------------------------------------------------------------
FAMILIES = {
    'CDR hi - lo (= direct colour - diffuse colour)': lambda q, h, l: q[h]['cdr'] - q[l]['cdr'],
    'direct colour': lambda q, h, l: q[h]['dir'] - q[l]['dir'],
    'diffuse colour': lambda q, h, l: q[h]['dif'] - q[l]['dif'],
    'total colour (level tilt)': lambda q, h, l: q[h]['tot'] - q[l]['tot'],
    'direct colour - total colour': lambda q, h, l: (q[h]['dir'] - q[l]['dir']) - (q[h]['tot'] - q[l]['tot']),
}


def pairs():
    for h, l in itertools.permutations(BANDS, 2):
        if CENTRE[h] > CENTRE[l] and not set(BANDS[h]) & set(BANDS[l]):
            yield h, l


def contrast(fam, h, l):
    return lambda q: FAMILIES[fam](q, h, l)


def CONTRAST_OF_RECORD(q):      # the bar's contrast, CDR 4-8 kHz minus 0.1-1.1 kHz (facing_pooled.py)
    return q['4-8k']['cdr'] - q['0.1-1.1k']['cdr']


def facing_stats(rows, f):
    """Effect of turning (unsigned >= 90) on a stop-level contrast f(q), against the spot's facing-0 mean."""
    spots = sorted({(r['walk'], r['spot']) for r in rows if r['has_ref']})
    turned, rep, spot_turn = [], [], []
    for key in spots:
        st = [r for r in rows if (r['walk'], r['spot']) == key]
        f0 = [f(r['q']) for r in st if r['unsigned'] == 0]
        ref = np.mean(f0)
        rep += [x - ref for x in f0] if len(f0) > 1 else []
        t = [f(r['q']) - ref for r in st if r['unsigned'] >= 90]
        turned += t
        if t:
            spot_turn.append(np.mean(t))
    n_rep_spots = sum(1 for key in spots if sum(1 for r in rows if (r['walk'], r['spot']) == key and r['unsigned'] == 0) > 1)
    n_rep = len(rep)
    noise = np.sqrt(np.sum(np.square(rep)) / max(n_rep - n_rep_spots, 1))   # sd of one facing-0 stop about its spot mean
    return dict(effect=float(np.mean(turned)), sd_turned=float(np.std(turned, ddof=1)), n_turned=len(turned),
                below=int(sum(x < 0 for x in turned)), spots_below=int(sum(x < 0 for x in spot_turn)),
                n_spots=len(spot_turn), noise_rep=float(noise), n_rep=n_rep)


def jitter(rows, f):
    dev, ns = [], []
    for r in rows:
        v = np.array([f(q) for q in per_window(r['walk'], r['t0'], r['t1'])])
        dev += list(v - v.mean()); ns.append(len(v))
    return float(np.std(dev)), float(np.std(dev) / np.sqrt(np.mean(ns)))


def ladder_rows():
    out = {}
    for walk, steps in LADDERS.items():
        out[walk] = [(dist, pool(walk, a, b)[0]) for a, b, dist in steps if pool(walk, a, b)[0] is not None]
    return out


def slope(lad, f):
    s = []
    for walk, rr in lad.items():
        s.append(np.polyfit(np.log10([d for d, _ in rr]), [f(q) for _, q in rr], 1)[0])
    return float(np.mean(s)), float(np.std(s, ddof=1)), [float(x) for x in s]


# ---- steps ------------------------------------------------------------------------------------------------------------
def fingerprint_rotation(rows, key):
    """Per band and quantity: per facing (signed or unsigned), mean and sd over spots of the spot-mean delta, n spots."""
    out = {}
    facings = sorted({r[key] for r in rows if r[key] is not None and r['has_ref']})
    for b in BANDS:
        out[b] = {}
        for k in Q:
            out[b][k] = {}
            for fd in facings:
                per_spot = []
                for sp in sorted({(r['walk'], r['spot']) for r in rows}):
                    v = [r['d'][b][k] for r in rows if (r['walk'], r['spot']) == sp and r['has_ref'] and r[key] == fd]
                    if v:
                        per_spot.append(np.mean(v))
                if per_spot:
                    out[b][k][fd] = dict(mean=float(np.mean(per_spot)),
                                         sd=float(np.std(per_spot, ddof=1)) if len(per_spot) > 1 else None,
                                         n=len(per_spot))
    return out


def fingerprint_distance(lad):
    return {b: {k: dict(zip(('mean', 'sd', 'per_walk'), slope(lad, lambda q, b=b, k=k: q[b][k]))) for k in Q}
            for b in BANDS}


def out_back(rows):
    """Spots with a side stop on the way out (90 turned) and on the way back (270 turned): per band, back minus out, and
    back minus away (180). The control: the closing facing-0 stop minus the opening one, at the same spots' walks."""
    def diff(a, b):
        return {x: {k: float(b['q'][x][k] - a['q'][x][k]) for k in Q} for x in BANDS}
    res, ctrl = [], []
    for sp in sorted({(r['walk'], r['spot']) for r in rows}):
        st = sorted([r for r in rows if (r['walk'], r['spot']) == sp], key=lambda r: r['t0'])
        out = [r for r in st if r['progress'] == 90]; back = [r for r in st if r['progress'] == 270]
        away = [r for r in st if r['progress'] == 180]
        if out and back:
            res.append(dict(walk=sp[0], spot=sp[1], ccw=sp[0] in CCW, out=[out[-1]['t0'], out[-1]['t1']],
                            back=[back[-1]['t0'], back[-1]['t1']], back_out=diff(out[-1], back[-1]),
                            back_away=diff(away[-1], back[-1]) if away else None,
                            contrast_back_out=float(CONTRAST_OF_RECORD(back[-1]['q']) - CONTRAST_OF_RECORD(out[-1]['q']))))
        o = [r for r in st if r['progress'] == 0]; c = [r for r in st if r['progress'] == 360]
        if o and c:
            ctrl.append(dict(walk=sp[0], spot=sp[1], close_open=diff(o[0], c[-1]),
                             contrast_close_open=float(CONTRAST_OF_RECORD(c[-1]['q']) - CONTRAST_OF_RECORD(o[0]['q']))))

    def summary(L, key):
        L = [x for x in L if x[key]]
        return {b: {k: dict(mean=float(np.mean([x[key][b][k] for x in L])), higher=int(sum(x[key][b][k] > 0 for x in L)),
                            n=len(L)) for k in Q} for b in BANDS}
    return dict(spots=res, control=ctrl, back_out=summary(res, 'back_out'), back_away=summary(res, 'back_away'),
                close_open=summary(ctrl, 'close_open'))


def room_reference(rows, f):
    """Per room, the reference is every facing-0 stop's contrast in that room from OTHER walks; the threshold is chosen
    on the other walks too (left out by walk). Toward = facing 0; turned = 90 or more; fade = past 120."""
    rr = [r for r in rows if r['room'] in ('kitchen', 'living room (inferred)')]
    for r in rr:
        ref = [f(x['q']) for x in rr if x['room'] == r['room'] and x['unsigned'] == 0 and x['walk'] != r['walk']]
        r['_v'] = f(r['q']) - np.mean(ref)

    def best_th(train, pos):
        cands = sorted({r['_v'] for r in train})
        def bal(th):
            a = [r['_v'] >= th for r in train if not pos(r)]; b = [r['_v'] < th for r in train if pos(r)]
            return (np.mean(a) if a else 0) / 2 + (np.mean(b) if b else 0) / 2
        return max(cands, key=bal)

    res = {}
    for name, keep, pos in (('toward vs turned', lambda r: r['unsigned'] in (0,) or r['unsigned'] >= 90, lambda r: r['unsigned'] >= 90),
                            ('fade (past 120) vs not', lambda r: True, lambda r: r['unsigned'] > 120)):
        hit = {True: [], False: []}; per_room = {}
        for w in sorted({r['walk'] for r in rr}):
            train = [r for r in rr if r['walk'] != w and keep(r)]
            th = best_th(train, pos)
            for r in rr:
                if r['walk'] == w and keep(r):
                    ok = (r['_v'] < th) if pos(r) else (r['_v'] >= th)
                    hit[pos(r)].append(ok); per_room.setdefault(r['room'], {True: [], False: []})[pos(r)].append(ok)
        res[name] = dict(balanced=float((np.mean(hit[True]) + np.mean(hit[False])) / 2),
                         positive=f"{sum(hit[True])} of {len(hit[True])}", negative=f"{sum(hit[False])} of {len(hit[False])}",
                         per_room={k: dict(positive=f"{sum(v[True])} of {len(v[True])}", negative=f"{sum(v[False])} of {len(v[False])}")
                                   for k, v in per_room.items()})
    # how many facing-0 stops before the reference settles
    settle = {}
    for room in ('kitchen', 'living room (inferred)'):
        f0 = [f(r['q']) for r in sorted(rr, key=lambda r: (r['walk'], r['t0'])) if r['room'] == room and r['unsigned'] == 0]
        sd0 = float(np.std(f0, ddof=1)); N = len(f0)
        run = np.cumsum(f0) / np.arange(1, N + 1)                    # in recording order (walk, then time)
        settle[room] = dict(n=N, sd_one_stop=sd0, sd_of_k_mean=[round(sd0 / np.sqrt(k), 2) for k in range(1, 11)],
                            k_for_1db=int(np.ceil(sd0 ** 2)), running_mean_minus_final=[round(x, 2) for x in run - run[-1]],
                            values=[round(x, 2) for x in f0])
    return res, settle


def opener_reference(rows, f):
    """The bar's version: each stop against its walk's first facing-0 stop, threshold left out by walk."""
    per = {}
    for w in sorted({r['walk'] for r in rows}):
        st = sorted([r for r in rows if r['walk'] == w], key=lambda r: r['t0'])
        ref = next((r for r in st if r['unsigned'] == 0), None)
        if ref and len(st) > 1:
            per[w] = [(r['unsigned'], f(r['q']) - f(ref['q'])) for r in st if r is not ref]
    tp = fn = tn = fp = 0
    for w in per:
        train = [p for o, v in per.items() if o != w for p in v]
        def bal(th):
            t = [x >= th for fd, x in train if fd == 0]; u = [x < th for fd, x in train if fd != 0]
            return (np.mean(t) if t else 0) / 2 + (np.mean(u) if u else 0) / 2
        th = max(sorted({x for _, x in train}), key=bal)
        for fd, x in per[w]:
            if fd == 0: tp += x >= th; fn += x < th
            else: tn += x < th; fp += x >= th
    return dict(balanced=float((tp / (tp + fn) + tn / (tn + fp)) / 2), toward=f"{tp} of {tp + fn}", turned=f"{tn} of {tn + fp}")


def turn_series(f, dip_db, pool_s=3.0):
    """Sliding pooled contrast over each continuous-turn walk: windows of pool_s seconds, step 0.5 s, at least 3 speech
    windows each; against the facing stretch before the turn (or the whole tape's mean)."""
    out = {}
    for walk, info in TURNS.items():
        w = load(walk)
        t, v = [], []
        k = int(pool_s / w['win_s'])
        for i in range(len(w['t0']) - k + 1):
            m = np.zeros(len(w['t0']), bool); m[i:i + k] = True; m &= w['voiced']
            if m.sum() >= 3:
                t.append(float(w['t0'][i] + pool_s / 2)); v.append(f(quant(w['D'][m], w['R'][m], w['P'][m], m.sum())))
        t, v = np.array(t), np.array(v)
        if info['ref']:
            ref = pool(walk, *info['ref'])[0]; ref = f(ref) if ref else float(np.mean(v))
        else:
            ref = float(np.mean(v))
        still = (t >= info['ref'][0]) & (t <= info['ref'][1]) if info['ref'] else np.zeros(len(t), bool)
        inside = np.zeros(len(t), bool)
        for a, b in info['circles']:
            inside |= (t >= a) & (t <= b)
        circ = []
        for a, b in info['circles']:
            m = (t >= a) & (t <= b)
            o = ~m & (t >= a - 15) & (t <= b + 15)
            circ.append(dict(span=[a, b], min_db=float(v[m].min() - ref) if m.any() else None,
                             t_min=float(t[m][np.argmin(v[m])]) if m.any() else None,
                             mean_in=float(v[m].mean() - ref) if m.any() else None,
                             mean_around=float(v[o].mean() - ref) if o.any() else None, n=int(m.sum())))
        for c, (a, b) in zip(circ, info['circles']):          # separate excursions below the stop-level turned effect
            m = (t >= a) & (t <= b)
            below = (v[m] - ref) < dip_db
            c['dips'] = int(np.sum(below[1:] & ~below[:-1]) + (below[0] if below.size else 0))
        out[walk] = dict(t=t.round(2).tolist(), v=(v - ref).round(2).tolist(), ref_span=info['ref'], said=info['said'],
                         circles=circ, baseline_m=w['baseline_m'],
                         sd_still=float(np.std(v[still])) if still.sum() > 2 else None,
                         frac_below_outside=float(np.mean((v[~inside] - ref) < dip_db)))
    return out


def rank_contrasts(rows, lad, spread_decades=0.5):
    """Every family x band pair: facing effect (turned against facing 0), its distance slope, its noise. The distance
    slope used is the RMS over the four ladders (they disagree in sign); the noise is one facing-0 stop's sd about its
    spot's mean. The combined score divides the effect by the noise and by the slope times spread_decades (2 to 6 m is
    0.48 decade, the spread of distances one room's facing-0 stops are taken at), added in quadrature."""
    pw = {id(r): per_window(r['walk'], r['t0'], r['t1']) for r in rows}
    out = []
    for fam in FAMILIES:
        for h, l in pairs():
            f = contrast(fam, h, l)
            s = facing_stats(rows, f)
            sl, sl_sd, per = slope(lad, f)
            dev, ns = [], []
            for r in rows:
                v = np.array([f(q) for q in pw[id(r)]]); dev += list(v - v.mean()); ns.append(len(v))
            j = float(np.std(dev))
            rms = float(np.sqrt(np.mean(np.square(per))))     # the ladders disagree in sign, so the mean hides it
            s.update(family=fam, hi=h, lo=l, ill_conditioned_lo=CENTRE[l] < 1100, slope=sl, slope_sd=sl_sd,
                     slope_per_walk=per, slope_rms=rms, jitter_window=j, jitter_pooled=j / np.sqrt(np.mean(ns)),
                     over_slope=abs(s['effect']) / max(rms, 1e-6),
                     over_noise=abs(s['effect']) / s['noise_rep'],
                     score=abs(s['effect']) / np.hypot(s['noise_rep'], rms * spread_decades))
            out.append(s)
    return sorted(out, key=lambda s: -s['score'])


def figures(fps, fdist, series, best):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    cols = dict(zip(OCT, ['#9aa7b8', '#6c8ebf', '#3f6fb0', '#2e8b57', '#d08a2c', '#c0392b']))
    names = {'dir': 'direct level', 'dif': 'diffuse level', 'tot': 'total level', 'cdr': 'CDR'}
    fig, ax = plt.subplots(2, 4, figsize=(17, 8.2))
    for j, k in enumerate(Q):
        a = ax[0, j]
        for i, b in enumerate(OCT):
            pts = sorted(fps[b][k].items())
            x = np.array([fd for fd, _ in pts]) + (i - 2.5) * 3
            a.errorbar(x, [v['mean'] for _, v in pts], yerr=[v['sd'] or 0 for _, v in pts], color=cols[b], marker='o',
                       ms=4, lw=1.6, capsize=2, label=b + (' *' if CENTRE[b] < 1100 else ''))
        a.axhline(0, color='k', lw=0.6); a.set_ylim(-11, 4)
        a.set_xticks([0, 90, 180, 225, 270, 360])
        a.set_xticklabels(['0\nfacing', '90\nout', '180\naway', '225', '270\nback', '360\nfacing'], fontsize=8)
        a.set_title('rotation: ' + names[k]); a.set_xlabel('degrees turned since facing the phone')
        if j == 0:
            a.set_ylabel("dB against the spot's facing-0 stops\n(mean over spots, bar = sd)")
            a.legend(fontsize=8, title='band (* below c/2d)', title_fontsize=8)
        a = ax[1, j]
        x = np.arange(len(OCT))
        a.bar(x, [fdist[b][k]['mean'] for b in OCT], yerr=[fdist[b][k]['sd'] for b in OCT],
              color=[cols[b] for b in OCT], capsize=3)
        for i, b in enumerate(OCT):
            a.scatter([i] * len(fdist[b][k]['per_walk']), fdist[b][k]['per_walk'], s=9, color='k', zorder=3)
        a.axhline(0, color='k', lw=0.6); a.axhline(-20, color='k', lw=0.6, ls=':')
        a.set_xticks(x); a.set_xticklabels(list(OCT)); a.set_ylim(-28, 14)
        a.set_title('distance: ' + names[k]); a.set_xlabel('octave band (Hz)')
        if j == 0:
            a.set_ylabel('dB per decade of called distance\n(mean of 4 ladders, dots = each; dotted = -20, free field)')
    fig.suptitle("The colour of rotation against the colour of distance, per octave band (Jay's walks)", fontsize=11)
    fig.tight_layout(); fig.savefig(OUT / 'fingerprints.png', dpi=110); plt.close(fig)

    fig, ax = plt.subplots(len(series), 1, figsize=(12, 2.3 * len(series)))
    for a, (w, s) in zip(ax, series.items()):
        t, v = np.array(s['t']), np.array(s['v'], float)
        gap = np.flatnonzero(np.diff(t) > 1.0) + 1                  # no line across silences
        a.plot(np.insert(t, gap, np.nan), np.insert(v, gap, np.nan), color='#3f6fb0', lw=1.4, marker='.', ms=3)
        for c in s['circles']:
            a.axvspan(*c['span'], color='#d08a2c', alpha=0.25)
        if s['ref_span']:
            a.axvspan(*s['ref_span'], color='#2e8b57', alpha=0.15)
        a.axhline(0, color='k', lw=0.6); a.axhline(best['effect'], color='#c0392b', lw=0.8, ls=':')
        a.set_ylabel('dB')
        a.set_title(f"{w}: {best['label']}, pooled over 3 s, against the green stretch (orange = the decode's turn; "
                    f"dotted = the mean turned effect at a stop)", fontsize=9)
    ax[-1].set_xlabel('tape time (s)')
    fig.tight_layout(); fig.savefig(OUT / 'continuous_turns.png', dpi=110); plt.close(fig)


def main():
    rows = stops()
    lad = ladder_rows()
    ranked = rank_contrasts(rows, lad)
    bar = next(s for s in ranked if s['family'].startswith('CDR') and (s['hi'], s['lo']) == ('4-8k', '0.1-1.1k'))
    # the pick: the top 8 by score and every CDR contrast against 4-8 kHz (the bar's among them), each tried with the
    # room as reference; the best balanced accuracy wins
    cdr48 = [s for s in ranked if s['family'].startswith('CDR') and s['hi'] == '4-8k']
    for s in ranked[:8] + [s for s in cdr48 if s not in ranked[:8]]:
        f = contrast(s['family'], s['hi'], s['lo'])
        rr, _ = room_reference(rows, f)
        s['room_balanced'] = rr['toward vs turned']['balanced']; s['room_fade_balanced'] = rr['fade (past 120) vs not']['balanced']
        s['opener_balanced'] = opener_reference(rows, f)['balanced']
    tried = [s for s in ranked if 'room_balanced' in s]
    best = max(tried, key=lambda s: (s['room_balanced'], s['score']))
    for s in tried:
        s['label'] = f"{s['family'].split(' (')[0]} {s['hi']} vs {s['lo']}"
    fb = contrast(best['family'], best['hi'], best['lo']); fbar = contrast(bar['family'], '4-8k', '0.1-1.1k')
    fps, fpu = fingerprint_rotation(rows, 'progress'), fingerprint_rotation(rows, 'unsigned')
    fdist = fingerprint_distance(lad)
    room_b, settle_b = room_reference(rows, fb)
    room_bar, settle_bar = room_reference(rows, fbar)
    series, series_bar = turn_series(fb, best['effect']), turn_series(fbar, bar['effect'])
    figures(fps, fdist, series, best)
    doc = dict(
        about="Brief A numbers (2026-10-24), from harness/rotation/colour/colour.py. dB throughout; levels are dB per "
              "speech window, each against the same spot's facing-0 stops. Bands below c/2d (1.09 kHz) are "
              "ill-conditioned.",
        set_aside=dict(start_transient_s=START_S, mono=MONO, unsigned_doubtful=SIGNED['doubtful']),
        n=dict(stops=len(rows), spots=len({(r['walk'], r['spot']) for r in rows}), walks=len({r['walk'] for r in rows}),
               speech_per_stop_s=float(np.mean([r['n'] for r in rows]) * 0.5),
               signed_stops=sum(r['signed'] is not None for r in rows)),
        rotation_progress=fps, rotation_unsigned=fpu, distance_db_per_decade=fdist,
        ladders={w: [d for d, _ in v] for w, v in lad.items()},
        contrasts_ranked=ranked, bar_contrast=bar, best_contrast=best, tried_with_room=tried,
        out_back=out_back(rows),
        room_reference=dict(best=room_b, best_settle=settle_b, bar=room_bar, bar_settle=settle_bar),
        opener_reference=dict(best=opener_reference(rows, fb), bar=opener_reference(rows, fbar)),
        continuous_turns=dict(best=series, bar={w: dict(circles=v['circles']) for w, v in series_bar.items()}),
        stops=[{k: v for k, v in r.items() if k not in ('q', 'd', '_v')} | {'best': fb(r['q']), 'bar': fbar(r['q'])}
               for r in rows])
    (OUT / 'numbers.json').write_text(json.dumps(doc, indent=1, default=float))
    return doc


if __name__ == '__main__':
    d = main()
    print(d['n'])
    print('top 12 contrasts (score = effect / hypot(noise, slope x 0.5 decade)):')
    for s in d['contrasts_ranked'][:12]:
        print(f"  {s['family'][:28]:28} {s['hi']:>6} vs {s['lo']:<8} effect {s['effect']:+5.1f} below {s['below']}/"
              f"{s['n_turned']} | slope {s['slope']:+5.1f} | noise {s['noise_rep']:.1f} jit {s['jitter_pooled']:.1f} | "
              f"/slope {s['over_slope']:4.1f} /noise {s['over_noise']:4.1f} score {s['score']:4.2f}")
    b = d['bar_contrast']
    print(f"bar (CDR 4-8k vs 0.1-1.1k): rank {d['contrasts_ranked'].index(b) + 1} of {len(d['contrasts_ranked'])}, "
          f"effect {b['effect']:+.1f}, slope {b['slope']:+.1f} {['%+.1f' % x for x in b['slope_per_walk']]}, "
          f"noise {b['noise_rep']:.1f}, score {b['score']:.2f}")
    print('tried with the room as reference:')
    for s in d['tried_with_room']:
        print(f"  {s['label']:40} score {s['score']:.2f}  room {s['room_balanced'] * 100:3.0f}%  fade {s['room_fade_balanced'] * 100:3.0f}%"
              f"  opener {s['opener_balanced'] * 100:3.0f}%")
    print('pick:', d['best_contrast']['label'])
    print('room reference:', json.dumps(d['room_reference']['best']))
    print('settle:', {k: (v['n'], round(v['sd_one_stop'], 2), v['k_for_1db'], v['running_mean_minus_final']) for k, v in d['room_reference']['best_settle'].items()})
    print('opener:', d['opener_reference'])
    for w, v in d['continuous_turns']['best'].items():
        print('turn', w, [{k: (round(c[k], 1) if isinstance(c[k], float) else c[k]) for k in c} for c in v['circles']],
              'sd still', v['sd_still'] and round(v['sd_still'], 2), 'frac below outside', round(v['frac_below_outside'], 2))
    ob = d['out_back']
    for x in ob['spots']:
        print('out/back', x['walk'][5:], x['spot'], 'ccw' if x['ccw'] else 'cw', x['out'], '->', x['back'], 'tot back-out',
              {b: round(x['back_out'][b]['tot'], 1) for b in OCT}, 'contrast', round(x['contrast_back_out'], 1))
    for name in ('back_out', 'back_away', 'close_open'):
        for k in Q:
            print(name, k, {b: (round(ob[name][b][k]['mean'], 1), f"{ob[name][b][k]['higher']}/{ob[name][b][k]['n']}") for b in OCT})
    print('control contrast', [(x['walk'][5:], round(x['contrast_close_open'], 1)) for x in ob['control']])
    for b in OCT:
        print('progress', b, {k: {fd: (round(v['mean'], 1), v['sd'] and round(v['sd'], 1), v['n']) for fd, v in d['rotation_progress'][b][k].items()} for k in Q})
