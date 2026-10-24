#!/usr/bin/env python3
"""Brief D, steps 1-5: the colour of rotation on LOCATA, with tracked facing (2026-10-24).

Reads results/animation/locata/<recording>.json (tracks: facing, distance, position, voice activity, every 0.1 s) and
results/rotation/locata/bins/<recording>.json (locata_bins.py: direct, diffuse and total power per segment, 0.1 s bins).

- **Stretches.** A bin is usable for a talker when the talker's voice activity covers at least half of it and the
  other talker's covers none of it, nor GUARD_S either side (the PSD smoothing, 0.92 per hop, remembers about 0.13 s;
  0.3 s leaves under 10% of the other talker's power). A stretch grows from a usable bin while every tracked bin in
  its span, pauses included, keeps the facing within 20 deg of the span's mean and the head within 0.3 m of its mean
  position. It is kept with at least 1.5 s of usable bins, which are what it pools.
- **Pooled quantities,** per band, as brief A's: direct, diffuse and total level (dB per hop) and the CDR (summed
  direct over summed diffuse). The contrast is CDR 4-8 kHz minus CDR 0.1-1.1 kHz (below c/2d = 1.07 kHz: the low band
  is ill-conditioned, as on the phone). The range statistic is CdrRange's: the mean of the CDR in dB over 1.1-2, 2-4
  and 4-8 kHz.
- **The reference (steps 2 and 4's ceiling)** is the same recording and talker's facing stretches (within 30 deg), at
  a distance within 0.5 m for step 2; the stretch itself is never its own reference.

Writes results/rotation/locata/numbers.json and run.txt; prints the summary.
"""
import json
from collections import defaultdict
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[3]
TRACKS = REPO / 'results/animation/locata'
OUT = REPO / 'results/rotation/locata'
JAY = (REPO / 'results/rotation/fixed_threshold.txt').read_text().strip()
JAY_TH = (-1.25, -1.00)          # fixed_threshold.txt: the threshold chosen on each left-out walk ranged over these
GUARD_S = 0.3
FACE_TOL, HEAD_TOL, MIN_S = 20.0, 0.3, 1.5
TOWARD, TURNED, FADE = 30.0, 90.0, 120.0
BINS = (0, 45, 90, 135, 180)

# segments in locata_bins.py: 88 100 177 354 707 1100 1414 2000 2828 4000 8000 Hz
OCT = {'125': [0, 1], '250': [2], '500': [3], '1k': [4, 5], '2k': [6, 7], '4-8k': [9]}
EXTRA = {'0.1-1.1k': [1, 2, 3, 4], '1.1-2k': [5, 6], '2-4k': [7, 8]}
BANDS = {**OCT, **EXTRA}
ILL = {'125', '250', '500', '1k', '0.1-1.1k'}   # reach below c/2d = 1.07 kHz
Q = ('dir', 'dif', 'tot', 'cdr')


def lin(a):
    return 10 ** (np.asarray(a, float) / 10)


def cover(segs, t, lo=0.0, hi=0.1):
    """Share of each bin [t + lo, t + hi) covered by the segments."""
    c = np.zeros(len(t))
    for s, e in segs:
        c += np.clip(np.minimum(t + hi, e) - np.maximum(t + lo, s), 0, None)
    return c / (hi - lo)


def pooled(D, R, P, hops):
    out = {}
    for b, s in BANDS.items():
        d, r, p = D[:, s].sum(), R[:, s].sum(), P[:, s].sum()
        out[b] = {'dir': 10 * np.log10(d / hops), 'dif': 10 * np.log10(r / hops), 'tot': 10 * np.log10(p / hops),
                  'cdr': 10 * np.log10(d / r)}
    return out


def contrast(q):
    return q['4-8k']['cdr'] - q['0.1-1.1k']['cdr']


def range_stat(q):
    return float(np.mean([q[b]['cdr'] for b in ('1.1-2k', '2-4k', '4-8k')]))


def stretches_of(rec):
    doc = json.loads((TRACKS / f'{rec}.json').read_text())
    bw = json.loads((OUT / 'bins' / f'{rec}.json').read_text())
    D, R, P, hops = lin(bw['dir_db']), lin(bw['dif_db']), lin(bw['pow_db']), np.array(bw['hops'])
    out = []
    for tk, tr in doc['tracks'].items():
        t = np.array(tr['t'])
        bi = np.round(t / 0.1).astype(int)
        ok_bin = bi < len(hops)
        others = [s for o, ot in doc['tracks'].items() if o != tk for s in ot['speech']]
        usable = (cover(tr['speech'], t) >= 0.5) & (cover(others, t, -GUARD_S, 0.1 + GUARD_S) == 0) & ok_bin
        fa = np.array(tr['facing_deg'], float); pos = np.c_[tr['along_m'], tr['ahead_m']].astype(float)
        dist = np.array(tr['dist_m'], float)
        good = np.isfinite(fa) & np.isfinite(pos).all(1)
        i, n = 0, len(t)
        while i < n:
            if not (usable[i] and good[i]):
                i += 1; continue
            j = i + 1
            while j < n and good[j]:
                f, p = fa[i:j + 1], pos[i:j + 1]
                if np.abs(f - f.mean()).max() > FACE_TOL or np.hypot(*(p - p.mean(0)).T).max() > HEAD_TOL:
                    break
                j += 1
            k = np.flatnonzero(usable[i:j]) + i
            if len(k) * 0.1 >= MIN_S - 1e-9:
                b = bi[k]
                q = pooled(D[b], R[b], P[b], hops[b].sum())
                out.append(dict(rec=rec, set=doc['set'], task=doc['task'], talker=tk, t0=float(t[i]),
                                t1=float(t[k[-1]] + 0.1), speech_s=round(len(k) * 0.1, 1),
                                facing=float(fa[k].mean()), dist=float(dist[k].mean()), q=q,
                                contrast=float(contrast(q)), range=range_stat(q)))
            i = j
    return out


def fbin(f):
    return min(BINS, key=lambda b: abs(f - b))


def refs(S, s, near=None):
    return [x for x in S if x is not s and x['rec'] == s['rec'] and x['talker'] == s['talker'] and
            x['facing'] <= TOWARD and (near is None or abs(x['dist'] - s['dist']) <= near)]


def ms(v):
    v = np.asarray(v, float)
    return {'mean': round(float(v.mean()), 2), 'sd': round(float(v.std(ddof=1)), 2) if len(v) > 1 else None,
            'n': int(len(v))} if len(v) else {'mean': None, 'sd': None, 'n': 0}


def step2(S, near=0.5):
    """Each stretch against its reference (same recording and talker, facing, within 0.5 m), per facing bin."""
    rows = []
    for s in S:
        r = refs(S, s, near=near)
        if not r:
            continue
        d = {b: {k: s['q'][b][k] - np.mean([x['q'][b][k] for x in r]) for k in Q} for b in BANDS}
        rows.append(dict(s=s, bin=fbin(s['facing']), d=d, contrast=s['contrast'] - np.mean([x['contrast'] for x in r]),
                         range=s['range'] - np.mean([x['range'] for x in r]), nref=len(r)))
    table = {}
    for b in BINS:
        R = [x for x in rows if x['bin'] == b]
        table[b] = {'contrast': ms([x['contrast'] for x in R]), 'range': ms([x['range'] for x in R]),
                    'bands': {band: {k: ms([x['d'][band][k] for x in R]) for k in Q} for band in BANDS},
                    'lower_contrast': int(sum(x['contrast'] < 0 for x in R))}
    return rows, table


def fit(x, y):
    x, y = np.asarray(x, float), np.asarray(y, float)
    if len(x) < 3 or np.ptp(x) < 1e-6:
        return None
    A = np.c_[x, np.ones_like(x)]
    beta, res, *_ = np.linalg.lstsq(A, y, rcond=None)
    e = y - A @ beta
    se = np.sqrt(e @ e / max(len(x) - 2, 1) / ((x - x.mean()) ** 2).sum())
    return {'slope': round(float(beta[0]), 2), 'se': round(float(se), 2), 'n': int(len(x)),
            'dist_m': [round(float(10 ** x.min()), 2), round(float(10 ** x.max()), 2)]}


def within(groups):
    """Slope with one intercept per group (recording and talker): the distance effect inside a session."""
    xs, ys = [], []
    for x, y in groups:
        if len(x) >= 2:
            xs.append(np.asarray(x) - np.mean(x)); ys.append(np.asarray(y) - np.mean(y))
    x, y = np.concatenate(xs), np.concatenate(ys)
    b = (x @ y) / (x @ x)
    e = y - b * x
    se = np.sqrt(e @ e / max(len(x) - len(xs) - 1, 1) / (x @ x))
    return {'slope': round(float(b), 2), 'se': round(float(se), 2), 'n': int(len(x)), 'groups': len(xs)}


def step3(S):
    F = [s for s in S if s['facing'] <= TOWARD]
    out = {}
    for key in ('contrast', 'range'):
        per = {}
        for rec in sorted({s['rec'] for s in F}):
            R = [s for s in F if s['rec'] == rec]
            per[rec] = fit(np.log10([s['dist'] for s in R]), [s[key] for s in R])
        g = defaultdict(list)
        for s in F:
            g[(s['rec'], s['talker'])].append(s)
        out[key] = {'per_recording': per,
                    'pooled': fit(np.log10([s['dist'] for s in F]), [s[key] for s in F]),
                    'within_session': within([(np.log10([s['dist'] for s in v]), [s[key] for s in v])
                                              for v in g.values()])}
    return out


def bal(c, pos, th, below_is_pos=False):
    """Balanced accuracy: pos called when c >= th (or c < th with below_is_pos)."""
    call = c < th if below_is_pos else c >= th
    return (np.mean(call[pos]) + np.mean(~call[~pos])) / 2


def score(S, task, value, fixed=None, grid=np.arange(-15, 15.01, 0.25)):
    """toward: toward (<= 30) against turned (>= 90), toward called when value >= th.
    fade: fade (>= 120) against the rest, fade called when value < th. Threshold fixed, or chosen on the other
    recordings (left out by recording)."""
    if task == 'toward':
        S = [s for s in S if s['facing'] <= TOWARD or s['facing'] >= TURNED]
        pos = np.array([s['facing'] <= TOWARD for s in S]); below = False
    else:
        pos = np.array([s['facing'] >= FADE for s in S]); below = True
    v = np.array([value(s) for s in S]); rec = np.array([s['rec'] for s in S]); ok = np.isfinite(v)
    S_ok = ok.copy()
    v, pos, rec = v[S_ok], pos[S_ok], rec[S_ok]
    call = np.zeros(len(v), bool); ths = []
    for r in sorted(set(rec)):
        te, tr = rec == r, rec != r
        if fixed is not None:
            th = fixed
        else:
            th = max(grid, key=lambda t: bal(v[tr], pos[tr], t, below))
        ths.append(float(th))
        call[te] = (v[te] < th) if below else (v[te] >= th)
    hit = call[pos].mean(); rej = (~call[~pos]).mean()
    return {'balanced': round(float((hit + rej) / 2 * 100), 1),
            'pos_called': f'{int(call[pos].sum())}/{int(pos.sum())}',
            'neg_kept': f'{int((~call[~pos]).sum())}/{int((~pos).sum())}',
            'threshold': [round(min(ths), 2), round(max(ths), 2)]}


def step4(S):
    ref_c = {id(s): (np.mean([x['contrast'] for x in refs(S, s)]) if refs(S, s) else np.nan) for s in S}
    raw = lambda s: s['contrast']                       # noqa: E731
    rel = lambda s: s['contrast'] - ref_c[id(s)]        # noqa: E731
    out = {}
    for task in ('toward', 'fade'):
        out[task] = {
            'jay_-1.00': score(S, task, raw, fixed=-1.0),
            'jay_-1.25': score(S, task, raw, fixed=-1.25),
            'locata_own': score(S, task, raw),
            'ceiling_labelled_reference': score(S, task, rel, grid=np.arange(-4, 4.01, 0.25)),
            # not the brief's cue, for comparison: the range statistic and the 4-8 kHz CDR alone, each with its own
            # threshold chosen on the other recordings (both move with distance, so neither is distance-free)
            'side_range_stat_own': score(S, task, lambda s: s['range']),
            'side_cdr_4-8k_own': score(S, task, lambda s: s['q']['4-8k']['cdr']),
        }
        out[task]['ceiling_n_without_reference'] = int(sum(not np.isfinite(ref_c[id(s)]) for s in S))
    return out


def absolute_bins(S):
    """No reference at all: each facing bin's raw values, over every recording."""
    return {b: {k: ms([f(s) for s in S if fbin(s['facing']) == b]) for k, f in (
        ('contrast', lambda s: s['contrast']), ('range', lambda s: s['range']),
        ('cdr_4-8k', lambda s: s['q']['4-8k']['cdr']), ('cdr_0.1-1.1k', lambda s: s['q']['0.1-1.1k']['cdr']),
        ('dist', lambda s: s['dist']))} for b in BINS}


def main():
    recs = [r['recording'] for r in json.loads((TRACKS / 'index.json').read_text())]
    S = [s for rec in recs for s in stretches_of(rec)]
    lines = []
    p = lines.append
    p(f"{len(S)} stretches, {sum(s['speech_s'] for s in S):.0f} s of speech pooled, "
      f"{np.mean([s['speech_s'] for s in S]):.1f} s each (range {min(s['speech_s'] for s in S)}-"
      f"{max(s['speech_s'] for s in S)}), {len(recs)} recordings")
    per_rec = {rec: {b: sum(1 for s in S if s['rec'] == rec and fbin(s['facing']) == b) for b in BINS} for rec in recs}
    p('stretches per facing bin (0/45/90/135/180):')
    for rec, c in per_rec.items():
        p(f"  {rec:24s} " + ' '.join(f'{c[b]:3d}' for b in BINS))
    tot = {b: sum(c[b] for c in per_rec.values()) for b in BINS}
    p(f"  {'all':24s} " + ' '.join(f'{tot[b]:3d}' for b in BINS))

    rows, table = step2(S)
    p(f'\nstep 2: {len(rows)} stretches with a reference (same recording+talker, facing <= 30, within 0.5 m)')
    p('bin | contrast mean/sd/n (lower) | range | 4-8k dir | 4-8k dif | 4-8k cdr | 0.1-1.1k cdr | 125 tot')
    for b in BINS:
        T = table[b]
        f = lambda m: f"{m['mean']:+.1f}/{m['sd'] if m['sd'] is not None else float('nan'):.1f}/{m['n']}" if m['n'] else '-'  # noqa: E731
        p(f"{b:3d} | {f(T['contrast'])} ({T['lower_contrast']}) | {f(T['range'])} | {f(T['bands']['4-8k']['dir'])} | "
          f"{f(T['bands']['4-8k']['dif'])} | {f(T['bands']['4-8k']['cdr'])} | {f(T['bands']['0.1-1.1k']['cdr'])} | "
          f"{f(T['bands']['125']['tot'])}")

    ab = absolute_bins(S)
    p('\nno reference, raw per bin: contrast | range | cdr 4-8k | cdr 0.1-1.1k | dist (mean/sd/n)')
    for b in BINS:
        p(f"{b:3d} | " + ' | '.join(f"{ab[b][k]['mean']:+.1f}/{ab[b][k]['sd'] or float('nan'):.1f}/{ab[b][k]['n']}"
                                    for k in ('contrast', 'range', 'cdr_4-8k', 'cdr_0.1-1.1k', 'dist')))
    rows_any, table_any = step2(S, near=None)
    p(f'\nstep 2, reference at any distance: {len(rows_any)} stretches with a reference')
    for b in BINS:
        T = table_any[b]
        p(f"{b:3d} | contrast {T['contrast']['mean'] if T['contrast']['n'] else float('nan'):+.1f} "
          f"(n {T['contrast']['n']}, {T['lower_contrast']} lower) | 4-8k cdr "
          f"{T['bands']['4-8k']['cdr']['mean'] if T['contrast']['n'] else float('nan'):+.1f} | 4-8k dir "
          f"{T['bands']['4-8k']['dir']['mean'] if T['contrast']['n'] else float('nan'):+.1f}")

    d3 = step3(S)
    p('\nstep 3 (facing stretches): dB per decade of tracked distance')
    for k, v in d3.items():
        per = ', '.join(f"{r[:1]}{r.split('_')[1][-1]}r{r[-1]} {x['slope']:+.1f}" for r, x in v['per_recording'].items() if x)
        p(f"  {k}: pooled {v['pooled']['slope']:+.1f} ± {v['pooled']['se']:.1f} (n {v['pooled']['n']}), "
          f"within session {v['within_session']['slope']:+.1f} ± {v['within_session']['se']:.1f} "
          f"(n {v['within_session']['n']}, {v['within_session']['groups']} sessions); per recording: {per}")

    d4 = step4(S)
    p('\nstep 4:')
    for task, v in d4.items():
        for k, x in v.items():
            if isinstance(x, dict):
                p(f"  {task:6s} {k:28s} {x['balanced']:5.1f}%  pos {x['pos_called']:>7s}  neg {x['neg_kept']:>7s}  "
                  f"th {x['threshold']}")
        p(f"  {task:6s} ceiling: {v['ceiling_n_without_reference']} stretches have no reference")
    F = [s['contrast'] for s in S if s['facing'] <= TOWARD]; Tn = [s['contrast'] for s in S if s['facing'] >= TURNED]
    p(f"\nLOCATA: facing {np.mean(F):+.1f} dB (sd {np.std(F):.1f}, n {len(F)}), turned {np.mean(Tn):+.1f} "
      f"(sd {np.std(Tn):.1f}, n {len(Tn)})")
    p(f'Jay:    {JAY}')

    # sensitivity: no guard around the other talker's speech (more task-4 stretches, some of the other's power kept)
    global GUARD_S
    keep, GUARD_S = GUARD_S, 0.0
    S0 = [s for rec in recs for s in stretches_of(rec)]
    GUARD_S = keep
    d4_0, ab0 = step4(S0), absolute_bins(S0)
    p(f"\nsensitivity, guard 0 s: {len(S0)} stretches, per bin {[sum(fbin(s['facing']) == b for s in S0) for b in BINS]}")
    p('  raw contrast per bin: ' + ', '.join(f"{b} {ab0[b]['contrast']['mean']:+.1f} (n {ab0[b]['contrast']['n']})" for b in BINS))
    for task, v in d4_0.items():
        p(f"  {task:6s} " + ', '.join(f"{k} {x['balanced']:.0f}%" for k, x in v.items() if isinstance(x, dict)))
    txt = '\n'.join(lines)
    print(txt)
    (OUT / 'run.txt').write_text(txt + '\n', encoding='utf-8')

    def slim(s):
        return {k: (round(v, 3) if isinstance(v, float) else v) for k, v in s.items() if k != 'q'} | {
            'bands': {b: {k: round(float(x), 2) for k, x in s['q'][b].items()} for b in BANDS}}
    doc = {'brief': 'harness/rotation/briefs/D_locata.md',
           'rules': {'guard_s': GUARD_S, 'facing_tol_deg': FACE_TOL, 'head_tol_m': HEAD_TOL, 'min_speech_s': MIN_S,
                     'toward_deg': TOWARD, 'turned_deg': TURNED, 'fade_deg': FADE, 'bins_deg': BINS,
                     'ill_conditioned_bands': sorted(ILL), 'c_over_2d_hz': 1072},
           'stretches_per_bin': per_rec,
           'step2_against_facing_reference': {str(b): v for b, v in table.items()},
           'step2_reference_at_any_distance': {str(b): v for b, v in table_any.items()},
           'raw_per_bin_no_reference': {str(b): v for b, v in ab.items()},
           'step3_distance_db_per_decade': d3,
           'step4_no_reference': d4,
           'facing_turned_contrast': {'facing': ms(F), 'turned': ms(Tn)},
           'jay_fixed_threshold': JAY,
           'sensitivity_guard_0s': {'n': len(S0), 'raw_per_bin': {str(b): v for b, v in ab0.items()}, 'step4': d4_0},
           'stretches': [slim(s) for s in S]}
    (OUT / 'numbers.json').write_text(json.dumps(doc, indent=1, default=float), encoding='utf-8')


if __name__ == '__main__':
    main()
