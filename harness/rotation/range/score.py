#!/usr/bin/env python3
"""Brief E's scores (2026-10-24): which range read moves least when the talker turns, and what it keeps of distance.
Reads results/rotation/range/reads.json (reads.py); writes results/rotation/range/numbers.json and scores.txt.

THE CANDIDATES, each a range statistic S in dB per read, drawn as u = 10^((S_open - S) / 20) (CdrRange's -20 law):
    today      mean CDR of B1, B2, B3 (1.1-8 kHz, floored): CdrRange unchanged
    low 0.1-1.1 / low 125-500   the CDR of one unfloored low band alone (ill-conditioned at the phone's spacing)
    weighted   a weighted mean of L125, L500, B1, B2, B3, each band's weight its distance slope (dB per decade, from
               the ladders) over its turned shift (dB, from the facing stops), both fitted on the other walks
    corrected  today + k * max(0, THR - contrast), contrast = CDR B3 - CDR L100 (brief A's), THR = -1 dB (the fixed
               threshold); k fitted on the other walks to minimise the fling; k = 0 is today
    gated      today's S, but a read the threshold calls turned draws the last read called facing within GATE_DEG of
               its bearing instead, and doesn't update; with none, it draws its own S, marked
    gated, holding the mean    the same, drawing the mean of every earlier facing read within GATE_DEG (a variant)
    gated (truth)   the same gate with the labelled facing as its call: the ceiling a perfect facing call would give
    gated (truth), any bearing, holding the mean   and with no bearing check: the gate's own ceiling
THE SCORES:
    fling      Jay's facing stops: per turned stop, the mean log2 u of its reads against the mean over its spot's
               facing-stop reads, in doublings; reads more than OUT_DBL from their spot's facing centre set aside
    ladders    Jay's facing ladders: each read's log2 u against the ladder's first step, beside the called ratio;
               ordering over read pairs from steps at least 1.5x apart
    LOCATA     brief 20's: the opener is the first lone read facing within 30 deg; every later read's error is
               log2(u) - log2(r / r_open); within 1.5x, mean |error| with reads off by 2x or more set aside, ordering
               over same-talker pairs at least 1.5x apart; all reads, facing (<= 45 deg) and turned (>= 90)
"""
import json
import math
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[3]
HANDLING_S = 2.0                     # facing_pooled.py: each tape's first 2 s are the ding and handling
THR = -1.0                           # fixed_threshold.txt: -1.25 to -1.00 dB
GATE_DEG = 5.0
OUT_DBL = 2.0                        # a read 4x from its spot's facing centre is an outlier
L2 = math.log2(10) / 20              # log2 u per dB of S
LENGTHS = ('short', 'whole')
LADDERS = {  # facing_vs_distance.py
    'walk-213304': [[4, 20, 2], [20, 42, 3], [42, 63, 5], [63, 78, 7]],
    'walk-221126': [[0, 12, 1], [12, 21, 2], [21, 29, 3], [29, 36, 4], [36, 43, 5], [43, 47, 6], [47, 59, 7], [59, 66, 8]],
    'walk-020305': [[2, 18, 1], [18, 54, 2], [54, 90, 3.5]],
    'walk-224302': [[0, 13, 4.5], [13, 35, 2], [35, 78, 6]],
}
DOC = json.loads((REPO / 'results/rotation/range/reads.json').read_text())
BAND = {b['name']: i for i, b in enumerate(DOC['bands'])}
WBANDS = ('L125', 'L500', 'B1', 'B2', 'B3')
STOPS = json.loads((REPO / 'harness/rotation/facing_stops.json').read_text())['stops']


def cdr(r, L):
    return np.array(r[L]['d']) - np.array(r[L]['r'])


def contrast(r, L):
    c = cdr(r, L); return c[BAND['B3']] - c[BAND['L100']]


def today(r, L):
    c = cdr(r, L); return float(np.mean(c[[BAND['B1'], BAND['B2'], BAND['B3']]]))


# ---- what each read belongs to on Jay's walks -------------------------------------------------------------------------
def stop_reads(walk):
    """[(spot, stop index, facing, [read indices])] for the walk's labelled stops."""
    reads = DOC['walks'][walk]['reads']; out = []
    for spot, stops in STOPS.get(walk, {}).items():
        if spot == 'dist_m':
            continue
        for j, (a, b, fd) in enumerate(stops):
            idx = [i for i, r in enumerate(reads) if a <= r['t'] < b and r['t'] >= HANDLING_S]
            if idx:
                out.append((spot, j, fd, idx))
    return out


def step_reads(walk):
    reads = DOC['walks'][walk]['reads']
    return [(dist, [i for i, r in enumerate(reads) if a <= r['t'] < b and r['t'] >= HANDLING_S]) for a, b, dist in LADDERS[walk]]


# ---- fitting the weighted and corrected candidates on a set of walks ----------------------------------------------------
def band_shift_and_slope(walks, L):
    """Per band of WBANDS: the mean turned-minus-facing shift (dB) over turned stops, and the mean ladder slope."""
    shift = {b: [] for b in WBANDS}; slope = {b: [] for b in WBANDS}
    for w in walks:
        reads = DOC['walks'][w]['reads']
        st = stop_reads(w)
        for spot in {s for s, *_ in st}:
            f = [i for s, _, fd, idx in st if s == spot and fd == 0 for i in idx]
            if not f:
                continue
            for s, _, fd, idx in st:
                if s == spot and fd >= 90:
                    for b in WBANDS:
                        k = BAND[b]
                        shift[b].append(np.mean([cdr(reads[i], L)[k] for i in idx]) - np.mean([cdr(reads[i], L)[k] for i in f]))
        if w in LADDERS:
            steps = [(d, idx) for d, idx in step_reads(w) if idx]
            for b in WBANDS:
                k = BAND[b]
                x = [math.log10(d) for d, idx in steps]; y = [np.mean([cdr(reads[i], L)[k] for i in idx]) for d, idx in steps]
                slope[b].append(np.polyfit(x, y, 1)[0])
    return {b: float(np.mean(shift[b])) for b in WBANDS}, {b: float(np.mean(slope[b])) for b in WBANDS}


def weights(walks, L):
    sh, sl = band_shift_and_slope(walks, L)
    w = np.array([max(0.0, -sl[b]) / max(abs(sh[b]), 0.25) for b in WBANDS])
    return w / w.sum() if w.sum() > 0 else np.ones(len(WBANDS)) / len(WBANDS)


def weighted_S(wts):
    return lambda r, L: float(np.dot(wts, cdr(r, L)[[BAND[b] for b in WBANDS]]))


def corrected_S(k):
    return lambda r, L: today(r, L) + k * max(0.0, THR - contrast(r, L))


# ---- drawing: the plain candidates read per utterance, the gate holds ---------------------------------------------------
def draw(reads, L, S, gate=None, hold='last', gate_deg=GATE_DEG):
    """Drawn S per read, in time order, and a mark per read: 'held', 'turned, none to hold' or ''.
    gate: None, or a function read index -> True when the read is called turned. hold: 'last' draws the latest read
    called facing within GATE_DEG (the brief's), 'mean' the mean of all of them (a variant)."""
    out, marks, facing = [], [], []          # facing: [(deg, S)] of reads called facing, latest last
    for i, r in enumerate(reads):
        s = S(r, L)
        if gate is None:
            out.append(s); marks.append(''); continue
        if not gate(i):
            facing.append((r['deg'], s)); out.append(s); marks.append('')
            continue
        near = [v for d, v in facing if abs(d - r['deg']) <= gate_deg]
        held = (near[-1] if hold == 'last' else float(np.mean(near))) if near else None
        out.append(s if held is None else held); marks.append('turned, none to hold' if held is None else 'held')
    return np.array(out), marks


def gate_by_threshold(reads, L):
    return lambda i: contrast(reads[i], L) < THR


def gate_by_truth(walk):
    """The labelled facing as the call, for the ceiling; reads outside stops count as facing."""
    turned = {i for _, _, fd, idx in stop_reads(walk) if fd >= 90 for i in idx}
    return lambda i: i in turned


# ---- scores -------------------------------------------------------------------------------------------------------------
def fling(walk, drawn):
    """Per turned stop: (facing deg, signed mean log2 ratio to the spot's facing reads, n reads kept, n set aside).
    Per facing stop at a spot with two or more, the same against the spot's OTHER facing stops: the floor, what a
    statistic's own jitter gives when nobody turned (kind 'floor')."""
    st = stop_reads(walk); out = []
    lu = -drawn * L2                          # log2 u up to the opener's constant, which cancels in every ratio
    for spot in {s for s, *_ in st}:
        f = np.array([lu[i] for s, _, fd, idx in st if s == spot and fd == 0 for i in idx])
        if len(f) == 0:
            continue
        c0 = np.median(f); fk = f[np.abs(f - c0) <= OUT_DBL]; ref = fk.mean()
        for s, _, fd, idx in st:
            if s == spot and fd >= 90:
                v = lu[idx]; keep = np.abs(v - c0) <= OUT_DBL
                if keep.any():
                    out.append(dict(walk=walk, spot=spot, facing=fd, ratio=float(v[keep].mean() - ref),
                                    per_read=(v[keep] - ref).tolist(), n=int(keep.sum()), out=int((~keep).sum()),
                                    out_facing=int(len(f) - len(fk)), kind='turned'))
        fst = [(j, idx) for s, j, fd, idx in st if s == spot and fd == 0]
        for j, idx in fst if len(fst) >= 2 else []:
            o = np.array([lu[i] for jj, ix in fst if jj != j for i in ix]); o = o[np.abs(o - c0) <= OUT_DBL]
            v = lu[idx]; keep = np.abs(v - c0) <= OUT_DBL
            if keep.any() and len(o):
                out.append(dict(walk=walk, spot=spot, facing=0, ratio=float(v[keep].mean() - o.mean()),
                                per_read=(v[keep] - o.mean()).tolist(), n=int(keep.sum()), out=int((~keep).sum()),
                                out_facing=0, kind='floor'))
    return out


def ladder(walk, drawn):
    lu = -drawn * L2
    steps = [(d, idx) for d, idx in step_reads(walk) if idx]
    d0, i0 = steps[0]; ref = lu[i0].mean()
    rows = []
    for d, idx in steps:
        for i in idx:
            rows.append((math.log2(d / d0), lu[i] - ref, d))
    err = np.array([b - a for a, b, d in rows if d != d0])
    keep = np.abs(err) <= OUT_DBL
    good = tot = 0
    for p in range(len(rows)):
        for q in range(p + 1, len(rows)):
            if abs(rows[p][0] - rows[q][0]) >= math.log2(1.5):
                tot += 1; good += (rows[p][1] - rows[q][1]) * (rows[p][0] - rows[q][0]) > 0
    step_means = [(math.log2(d / d0), float(lu[idx].mean() - ref)) for d, idx in steps]
    sx = [a for a, _ in step_means]; sy = [b for _, b in step_means]
    rank = lambda v: np.argsort(np.argsort(v))
    return dict(walk=walk, err=err[keep].tolist(), out=int((~keep).sum()), order=(good, tot),
                steps=step_means, spearman=float(np.corrcoef(rank(sx), rank(sy))[0, 1]) if len(sx) > 2 else float('nan'),
                share=float(np.polyfit(sx, sy, 1)[0]))


def locata(name, drawn):
    reads = DOC['locata'][name]['reads']
    lu = -drawn * L2
    o = next((i for i, r in enumerate(reads) if r['others'] == 0 and r['facing_deg'] is not None and abs(r['facing_deg']) <= 30), None)
    if o is None:
        return []
    r0 = reads[o]['dist_m']
    return [dict(err=float(lu[i] - lu[o] - math.log2(r['dist_m'] / r0)), true=math.log2(r['dist_m'] / r0), drawn=float(lu[i] - lu[o]),
                 talker=r['talker'], facing=abs(r['facing_deg']) if r['facing_deg'] is not None else None, rec=name)
            for i, r in enumerate(reads) if i > o]


def locata_summary(rows, keep=lambda r: True):
    rows = [r for r in rows if keep(r)]
    if not rows:
        return None
    e = np.array([abs(r['err']) for r in rows]); off = e > 1
    good = tot = 0
    for p in range(len(rows)):
        for q in range(p + 1, len(rows)):
            a, b = rows[p], rows[q]
            if a['rec'] == b['rec'] and a['talker'] == b['talker'] and abs(a['true'] - b['true']) >= math.log2(1.5):
                tot += 1; good += (a['drawn'] - b['drawn']) * (a['true'] - b['true']) > 0
    return dict(n=len(rows), within_1_5x=float(np.mean(e <= math.log2(1.5))), off_2x=int(off.sum()),
                mean_err_rest=float(e[~off].mean()), ordering=good / tot if tot else float('nan'), pairs=tot,
                bias=float(np.mean([r['err'] for r in rows])))


# ---- one candidate, every score -----------------------------------------------------------------------------------------
def candidates_for(test_walks, L, k_fit=None):
    """{name: (S, gate maker)} with the weighted and corrected candidates fitted on every walk but test_walks."""
    train = [w for w in DOC['walks'] if w not in test_walks]
    wts = weights(train, L)
    k = fit_k(train, L) if k_fit is None else k_fit
    return {
        'today': (today, None),
        'low 0.1-1.1 kHz': (lambda r, L: float(cdr(r, L)[BAND['L100']]), None),
        'low 125-500 Hz': (lambda r, L: float(cdr(r, L)[BAND['L125']]), None),
        'weighted': (weighted_S(wts), None),
        'corrected': (corrected_S(k), None),
        'gated': (today, ('threshold', 'last')),
        'gated, holding the mean': (today, ('threshold', 'mean')),
        'gated (truth)': (today, ('truth', 'last')),
        'gated (truth), any bearing, holding the mean': (today, ('truth', 'mean', math.inf)),
    }, dict(weights=dict(zip(WBANDS, np.round(wts, 3).tolist())), k=k)


def fit_k(walks, L):
    best = None
    for k in np.arange(0, 2.01, 0.05):
        S = corrected_S(k)
        v = [abs(f['ratio']) for w in walks if w in STOPS for f in fling(w, draw(DOC['walks'][w]['reads'], L, S)[0])
             if f['kind'] == 'turned']
        if v and (best is None or np.mean(v) < best[0]):
            best = (np.mean(v), round(float(k), 2))
    return best[1]


def drawn_for(reads, L, S, gate, walk=None):
    if gate is None:
        return draw(reads, L, S)
    g = gate_by_threshold(reads, L) if gate[0] == 'threshold' else gate_by_truth(walk)
    return draw(reads, L, S, g, *gate[1:])


def slope_and_shift(S, L, walks):
    """A statistic's own distance slope (dB per decade, ladders) and turned shift (dB, facing stops): the diagnostic."""
    sl, sh = [], []
    for w in walks:
        reads = DOC['walks'][w]['reads']; v = np.array([S(r, L) for r in reads])
        if w in LADDERS:
            steps = [(d, idx) for d, idx in step_reads(w) if idx]
            sl.append(np.polyfit([math.log10(d) for d, _ in steps], [v[idx].mean() for _, idx in steps], 1)[0])
        st = stop_reads(w)
        for spot in {s for s, *_ in st}:
            f = [i for s, _, fd, idx in st if s == spot and fd == 0 for i in idx]
            if f:
                sh += [v[idx].mean() - v[f].mean() for s, _, fd, idx in st if s == spot and fd >= 90]
    return float(np.mean(sl)), float(np.mean(sh))


def main():
    walks = sorted(DOC['walks'])
    res = {'thr_db': THR, 'gate_deg': GATE_DEG, 'out_dbl': OUT_DBL, 'lengths': {}}
    txt = []
    say = txt.append
    for L in LENGTHS:
        R = {}
        fits = {}
        for w in walks:                                   # left out by walk: fling and ladders
            cands, fit = candidates_for([w], L); fits[w] = fit
            reads = DOC['walks'][w]['reads']
            for name, (S, gate) in cands.items():
                d, marks = drawn_for(reads, L, S, gate, w)
                r = R.setdefault(name, {'fling': [], 'ladder': [], 'marks': {'held': 0, 'turned, none to hold': 0}, 'locata': []})
                if w in STOPS:
                    r['fling'] += fling(w, d)
                if w in LADDERS:
                    r['ladder'].append(ladder(w, d))
                for m in marks:
                    if m:
                        r['marks'][m] += 1
        cands_all, fit_all = candidates_for([], L)        # LOCATA: fitted on all of Jay's walks
        for name, (S, gate) in cands_all.items():
            for rec in sorted(DOC['locata']):
                reads = DOC['locata'][rec]['reads']
                if gate is not None and gate[0] == 'truth':
                    g = lambda i, reads=reads: reads[i]['facing_deg'] is not None and abs(reads[i]['facing_deg']) >= 90
                    d, _ = draw(reads, L, S, g, *gate[1:])
                else:
                    d, _ = drawn_for(reads, L, S, gate)
                R[name]['locata'] += locata(rec, d)
        # the facing call itself, per read
        calls = {'facing': [], 'turned': []}
        for w in STOPS:
            reads = DOC['walks'][w]['reads']
            for _, _, fd, idx in stop_reads(w):
                for i in idx:
                    (calls['facing'] if fd == 0 else calls['turned'] if fd >= 90 else []).append(contrast(reads[i], L) >= THR)
        lc = {'facing': [], 'turned': []}
        for rec, v in DOC['locata'].items():
            for r in v['reads']:
                if r['facing_deg'] is not None:
                    f = abs(r['facing_deg'])
                    (lc['facing'] if f <= 45 else lc['turned'] if f >= 90 else []).append(contrast(r, L) >= THR)
        out = {'fits_left_out': fits, 'fit_all_walks': fit_all, 'candidates': {},
               'facing_call': {'walks': {'facing_called_facing': float(np.mean(calls['facing'])), 'n_facing': len(calls['facing']),
                                         'turned_called_turned': float(1 - np.mean(calls['turned'])), 'n_turned': len(calls['turned'])},
                               'locata': {'facing_called_facing': float(np.mean(lc['facing'])), 'n_facing': len(lc['facing']),
                                          'turned_called_turned': float(1 - np.mean(lc['turned'])), 'n_turned': len(lc['turned'])}}}
        say(f"\n=== read: {L} ===")
        fc = out['facing_call']
        say(f"facing call per read at {THR} dB: Jay's walks {fc['walks']['facing_called_facing']*100:.0f}% of {fc['walks']['n_facing']} facing reads"
            f" called facing, {fc['walks']['turned_called_turned']*100:.0f}% of {fc['walks']['n_turned']} turned reads called turned; LOCATA"
            f" {fc['locata']['facing_called_facing']*100:.0f}% of {fc['locata']['n_facing']} / {fc['locata']['turned_called_turned']*100:.0f}% of {fc['locata']['n_turned']}")
        say(f"fit on all walks: weights {fit_all['weights']}, k {fit_all['k']}; left out: k {sorted({f['k'] for f in fits.values()})}")
        say('| candidate | fling: mean |log2| (stops) | floor: facing vs facing | signed: 90 / 135 / 180 | stops beating today | fling per read | set aside |'
            ' own slope dB/dec | turned shift dB | ladders: mean |err| / signed | ladder share of called | ladder ordering (per walk) |'
            ' LOCATA all: within 1.5x / mean err / off 2x / ordering | facing | turned | marks |')
        base = [abs(f['ratio']) for f in R['today']['fling'] if f['kind'] == 'turned']
        for name, r in R.items():
            fo = [f for f in r['fling'] if f['kind'] == 'floor']; fo_a = np.array([abs(f['ratio']) for f in fo])
            fl = [f for f in r['fling'] if f['kind'] == 'turned']; a = np.array([abs(f['ratio']) for f in fl])
            beat = int(sum(x < y - 1e-9 for x, y in zip(a, base))); tie = int(sum(abs(x - y) <= 1e-9 for x, y in zip(a, base)))
            sg = {fd: np.mean([f['ratio'] for f in fl if f['facing'] == fd]) for fd in (90, 135, 180)}
            pr = np.concatenate([np.abs(f['per_read']) for f in fl])
            so = sum(f['out'] for f in fl); sof = sum({(f['walk'], f['spot']): f['out_facing'] for f in fl}.values())
            pw = ', '.join(f"{x['walk'][5:]} {x['order'][0] / x['order'][1] * 100:.0f}" for x in r['ladder'])
            le = np.concatenate([x['err'] for x in r['ladder']]); lo = sum(x['out'] for x in r['ladder'])
            og = sum(x['order'][0] for x in r['ladder']); ot = sum(x['order'][1] for x in r['ladder'])
            share = np.mean([x['share'] for x in r['ladder']])
            S = cands_all[name][0]
            sl, sh = slope_and_shift(S, L, walks)
            loc = {k: locata_summary(r['locata'], f) for k, f in
                   (('all', lambda x: True), ('facing', lambda x: x['facing'] is not None and x['facing'] <= 45),
                    ('turned', lambda x: x['facing'] is not None and x['facing'] >= 90))}
            fmt = lambda s: f"{s['within_1_5x']*100:.0f}% / {s['mean_err_rest']:.2f} / {s['off_2x']} of {s['n']} / {s['ordering']*100:.0f}%"
            say(f"| {name} | {a.mean():.3f} (n {len(a)}) | {fo_a.mean():.3f} (n {len(fo_a)}) | {sg[90]:+.2f} / {sg[135]:+.2f} / {sg[180]:+.2f} |"
                f" {beat} of {len(a)} ({tie} tied) | {pr.mean():.2f} (n {len(pr)}) |"
                f" {so} turned, {sof} facing | {sl:+.1f} | {sh:+.2f} | {np.abs(le).mean():.2f} / {le.mean():+.2f} (n {len(le)}, {lo} aside) |"
                f" {share:.2f} | {og / ot * 100:.0f}% of {ot} ({pw}) | {fmt(loc['all'])} | {fmt(loc['facing'])} | {fmt(loc['turned'])} |"
                f" {r['marks']['held']} held, {r['marks']['turned, none to hold']} unheld |")
            out['candidates'][name] = dict(
                fling=dict(mean_abs_dbl=float(a.mean()), n_stops=len(a), signed_by_facing={str(k): float(v) for k, v in sg.items()},
                           floor_mean_abs_dbl=float(fo_a.mean()), n_floor_stops=len(fo_a), stops_beating_today=beat, stops_tied=tie,
                           per_read_mean_abs_dbl=float(pr.mean()), n_reads=len(pr), set_aside_turned=so, set_aside_facing=sof,
                           stops=[{k: v for k, v in f.items() if k != 'per_read'} for f in fl + fo]),
                slope_db_per_decade=sl, turned_shift_db=sh,
                ladders=dict(mean_abs_err_dbl=float(np.abs(le).mean()), mean_signed_err_dbl=float(le.mean()), n=len(le), set_aside=lo, ordering=og / ot, pairs=ot,
                             share_of_called=float(share),
                             per_walk=[{k: v for k, v in x.items() if k != 'err'} for x in r['ladder']]),
                locata=loc, marks=r['marks'])
        # LOCATA's own k, as a diagnostic: does the house's k carry to another room?
        best = min(((np.mean([abs(x['err']) for x in sum((locata(rec, draw(DOC['locata'][rec]['reads'], L, corrected_S(k))[0])
                                                        for rec in DOC['locata']), []) if abs(x['err']) <= 1]), round(float(k), 2))
                    for k in np.arange(0, 2.01, 0.1)))
        out['locata_own_k'] = {'k': best[1], 'mean_err_rest': float(best[0])}
        say(f"LOCATA's own best k (in-sample, mean error of the reads within 2x): {best[1]} -> {best[0]:.3f} dbl")
        res['lengths'][L] = out
    (REPO / 'results/rotation/range/numbers.json').write_text(json.dumps(res, indent=1, default=lambda o: o.item()))
    t = '\n'.join(txt)
    (REPO / 'results/rotation/range/scores.txt').write_text(t + '\n')
    print(t)


if __name__ == '__main__':
    main()
