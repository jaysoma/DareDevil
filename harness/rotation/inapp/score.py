#!/usr/bin/env python3
"""Brief H, step 1 (2026-10-24): fit k for option b, and score it brief E's way. Reads results/rotation/inapp/reads.json
(reads.py); writes results/rotation/inapp/numbers.json and scores.txt.

THE CANDIDATES, each a range statistic S in dB per utterance, drawn as CdrRange draws it (u = 10^((S_open - S) / 20)):
    today         mean CDR of B1, B2, B3 over the 0.13-0.5 s read: CdrRange unchanged
    E (k)         today + k * max(0, THR - contrast), the contrast over the SAME 0.13-0.5 s read (brief E's "corrected")
    option b (k)  today, and when the utterance reaches its 2 s frame, + k * max(0, THR - contrast) with the contrast
                  over 0.13-2.0 s: the range is read at 0.5 s and corrected at most once, at 2 s, only when turned
    contrast = CDR 4-8 kHz minus unfloored CDR 0.1-1.1 kHz; THR = -1 dB (results/rotation/fixed_threshold.txt)
THE 2 S RULE: 'handed' (the Conductor hands the 2 s frame before it closes the utterance: what v14 does) is the main
one; 'speech2' (the backdated close is 2 s or more after the onset) is the brief's literal "utterances of 2 s or more".
THE FIT: k on a 0-2 grid (0.05) minimising the fling over the other walks' turned stops; k = 0 is today.
THE SCORES are brief E's own functions (harness/rotation/range/score.py) run on these reads: the fling on Jay's stops,
read-pair ordering on the ladders, LOCATA's within 1.5x / off 2x / ordering on all, facing and turned reads.
"""
import json
import math
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / 'harness/rotation/range'))
import score as E  # noqa: E402  (brief E's scorer; its DOC is swapped for these reads below)

DOC = json.loads((REPO / 'results/rotation/inapp/reads.json').read_text())
E.DOC = DOC
THR, L = E.THR, 'short'
KS = [round(float(k), 2) for k in np.arange(0, 2.01, 0.05)]
RULES = ('handed', 'speech2')


def has2(r, rule):
    return 'facing' in r and r['facing'][rule]


def contrast2(r):
    return E.contrast(r, 'facing')


def option_b(k, rule):
    return lambda r, _L: E.today(r, L) + (k * max(0.0, THR - contrast2(r)) if has2(r, rule) else 0.0)


def option_b_capped(k, cap):
    """A diagnostic, not shipped: option b with the correction capped at `cap` dB (the 'handed' rule)."""
    return lambda r, _L: E.today(r, L) + (min(cap, k * max(0.0, THR - contrast2(r))) if has2(r, 'handed') else 0.0)


K_SHIPPED = 1.1      # CdrRange.FACING_K: option b's k fitted on all of Jay's walks ('handed')
CAPS = (2.0, 2.5, 3.0)


def drawn(reads, S):
    return np.array([S(r, L) for r in reads])


def fling_of(S, walks):
    rows = [f for w in walks if w in E.STOPS for f in E.fling(w, drawn(DOC['walks'][w]['reads'], S))]
    return [f for f in rows if f['kind'] == 'turned'], [f for f in rows if f['kind'] == 'floor']


def fit(make, walks):
    best = None
    for k in KS:
        t, _ = fling_of(make(k), walks)
        v = np.mean([abs(f['ratio']) for f in t])
        if best is None or v < best[0] - 1e-12:
            best = (v, k)
    return best[1]


def ladders_of(S):
    return [E.ladder(w, drawn(DOC['walks'][w]['reads'], S)) for w in E.LADDERS]


def locata_of(S):
    rows = sum((E.locata(rec, drawn(DOC['locata'][rec]['reads'], S)) for rec in sorted(DOC['locata'])), [])
    return {k: E.locata_summary(rows, f) for k, f in
            (('all', lambda x: True), ('facing', lambda x: x['facing'] is not None and x['facing'] <= 45),
             ('turned', lambda x: x['facing'] is not None and x['facing'] >= 90))}


def summary(turned, floor, lad, loc):
    a = np.array([abs(f['ratio']) for f in turned])
    og = sum(x['order'][0] for x in lad); ot = sum(x['order'][1] for x in lad)
    return dict(fling=float(a.mean()), n_stops=len(a),
                signed={str(fd): float(np.mean([f['ratio'] for f in turned if f['facing'] == fd])) for fd in (90, 135, 180)},
                floor=float(np.mean([abs(f['ratio']) for f in floor])), n_floor=len(floor),
                ladder_order=og / ot, ladder_pairs=ot,
                ladder_per_walk={x['walk']: x['order'][0] / x['order'][1] for x in lad}, locata=loc,
                per_stop=[float(abs(f['ratio'])) for f in turned])


def left_out(make):
    """k fitted with each walk left out; every walk's fling and ladder scored with its own left-out k. LOCATA with the
    k fitted on all of Jay's walks."""
    walks = sorted(DOC['walks'])
    ks, turned, floor, lad = {}, [], [], []
    for w in walks:
        k = fit(make, [v for v in walks if v != w]); ks[w] = k
        t, f = fling_of(make(k), [w]); turned += t; floor += f
        if w in E.LADDERS:
            lad.append(E.ladder(w, drawn(DOC['walks'][w]['reads'], make(k))))
    k_all = fit(make, walks)
    return summary(turned, floor, lad, locata_of(make(k_all))), ks, k_all


def fixed(S):
    walks = sorted(DOC['walks'])
    t, f = fling_of(S, walks)
    return summary(t, f, ladders_of(S), locata_of(S))


def facing_call(rule):
    """The 2 s call per utterance: facing stops (0) against turned (90+), on Jay's walks and LOCATA."""
    out = {}
    fc, tc = [], []
    for w in E.STOPS:
        reads = DOC['walks'][w]['reads']
        for _, _, fd, idx in E.stop_reads(w):
            for i in idx:
                if has2(reads[i], rule) and fd in (0, 90, 135, 180):
                    (fc if fd == 0 else tc).append(contrast2(reads[i]) >= THR)
    out['walks'] = dict(facing_called_facing=float(np.mean(fc)), n_facing=len(fc),
                        turned_called_turned=float(1 - np.mean(tc)), n_turned=len(tc),
                        balanced=float((np.mean(fc) + 1 - np.mean(tc)) / 2))
    fc, tc = [], []
    for v in DOC['locata'].values():
        for r in v['reads']:
            if has2(r, rule) and r['facing_deg'] is not None:
                f = abs(r['facing_deg'])
                (fc if f <= 45 else tc if f >= 90 else []).append(contrast2(r) >= THR)
    out['locata'] = dict(facing_called_facing=float(np.mean(fc)) if fc else None, n_facing=len(fc),
                         turned_called_turned=float(1 - np.mean(tc)) if tc else None, n_turned=len(tc),
                         balanced=float((np.mean(fc) + 1 - np.mean(tc)) / 2) if fc and tc else None)
    return out


def coverage(rule):
    """How many utterances reach the 2 s call, how many are corrected; on the stops, by labelled facing."""
    n = n2 = nt = 0
    by = {fd: [0, 0, 0] for fd in (0, 90, 135, 180)}       # reads, reaching 2 s, called turned
    for w, v in DOC['walks'].items():
        reads = v['reads']
        for r in reads:
            n += 1; n2 += has2(r, rule); nt += has2(r, rule) and contrast2(r) < THR
        for _, _, fd, idx in E.stop_reads(w):
            if fd in by:
                for i in idx:
                    by[fd][0] += 1; by[fd][1] += has2(reads[i], rule); by[fd][2] += has2(reads[i], rule) and contrast2(reads[i]) < THR
    nl = sum(len(v['reads']) for v in DOC['locata'].values())
    nl2 = sum(has2(r, rule) for v in DOC['locata'].values() for r in v['reads'])
    return dict(walk_reads=n, reach_2s=n2, called_turned=nt, by_facing={str(k): v for k, v in by.items()},
                locata_reads=nl, locata_reach_2s=nl2)


def sweep(make):
    """In-sample, all walks: fling and ladder ordering at every k (the gate asks whether ANY k passes)."""
    out = []
    for k in KS:
        s = fixed(make(k))
        out.append(dict(k=k, fling=s['fling'], ladder_order=s['ladder_order'], locata_within=s['locata']['all']['within_1_5x']))
    return out


def check_against_E():
    """These reads' short read must be brief E's, utterance for utterance."""
    ed = json.loads((REPO / 'results/rotation/range/reads.json').read_text())
    worst, n, missing = 0.0, 0, 0
    for part in ('walks', 'locata'):
        for name, v in ed[part].items():
            mine = {r['t']: r for r in DOC[part][name]['reads']}
            for r in v['reads']:
                m = mine.get(r['t'])
                if m is None:
                    missing += 1; continue
                n += 1
                worst = max(worst, float(np.max(np.abs(np.array(m['short']['d']) - r['short']['d']))),
                            float(np.max(np.abs(np.array(m['short']['r']) - r['short']['r']))))
    return dict(reads_compared=n, missing=missing, largest_gap_db=worst)


def main():
    res = {'thr_db': THR, 'check_against_E': check_against_E()}
    txt = []
    say = txt.append
    say(f"E's short read reproduced: {res['check_against_E']}")
    today = fixed(E.today)
    res['today'] = today
    e_lo, e_ks, e_kall = left_out(E.corrected_S)
    res['E_half_second'] = dict(scores=e_lo, k_left_out=e_ks, k_all=e_kall)
    res['E_half_second_k09'] = fixed(E.corrected_S(0.9))
    res['option_b'] = {}
    for rule in RULES:
        make = lambda k, rule=rule: option_b(k, rule)
        lo, ks, kall = left_out(make)
        res['option_b'][rule] = dict(scores=lo, k_left_out=ks, k_all=kall, k09=fixed(make(0.9)),
                                     k_shipped=fixed(make(K_SHIPPED)),
                                     facing_call=facing_call(rule), coverage=coverage(rule), sweep=sweep(make))
    res['E_sweep'] = sweep(E.corrected_S)
    res['capped'] = {}
    for cap in CAPS:
        lo, ks, kall = left_out(lambda k, cap=cap: option_b_capped(k, cap))
        res['capped'][str(cap)] = dict(scores=lo, k_left_out=ks, k_all=kall, k_shipped=fixed(option_b_capped(K_SHIPPED, cap)))

    def row(name, s):
        lc = s['locata']
        f = lambda x: f"{x['within_1_5x']*100:.0f}% / {x['mean_err_rest']:.2f} / {x['off_2x']} of {x['n']} / {x['ordering']*100:.0f}%"
        pw = ', '.join(f"{w[5:]} {v*100:.0f}" for w, v in s['ladder_per_walk'].items())
        sg = s['signed']
        return (f"| {name} | {s['fling']:.3f} (n {s['n_stops']}) | {sg['90']:+.2f} / {sg['135']:+.2f} / {sg['180']:+.2f} |"
                f" {s['floor']:.3f} (n {s['n_floor']}) | {s['ladder_order']*100:.1f}% of {s['ladder_pairs']} ({pw}) |"
                f" {f(lc['all'])} | {f(lc['facing'])} | {f(lc['turned'])} |")
    say('\n| candidate | fling | signed 90 / 135 / 180 | floor | ladder ordering | LOCATA all: within 1.5x / err / off 2x / ordering | facing | turned |')
    say('|---|---|---|---|---|---|---|---|')
    say(row('today', today))
    say(row(f"E, half second (k left out {sorted(set(e_ks.values()))}, all {e_kall})", e_lo))
    say(row('E, half second, k 0.9 fixed', res['E_half_second_k09']))
    for rule in RULES:
        b = res['option_b'][rule]
        say(row(f"option b, {rule} (k left out {sorted(set(b['k_left_out'].values()))}, all {b['k_all']})", b['scores']))
        say(row(f"option b, {rule}, k 0.9 fixed", b['k09']))
        say(row(f"option b, {rule}, k {K_SHIPPED} fixed (in-sample: the shipped k)", b['k_shipped']))
    for cap, c in res['capped'].items():
        say(row(f"diagnostic: option b, handed, capped at {cap} dB (k left out {sorted(set(c['k_left_out'].values()))}, all {c['k_all']})", c['scores']))
        say(row(f"diagnostic: option b, handed, capped at {cap} dB, k {K_SHIPPED} fixed", c['k_shipped']))
    for rule in RULES:
        b = res['option_b'][rule]
        say(f"\n{rule}: 2 s call {json.dumps(b["facing_call"], default=int)}")
        say(f"{rule}: coverage {json.dumps(b["coverage"], default=int)}")
        say(f"{rule}: sweep (k: fling / ladder ordering / LOCATA within 1.5x) " +
            '; '.join(f"{x['k']}: {x['fling']:.3f} / {x['ladder_order']*100:.1f} / {x['locata_within']*100:.0f}" for x in b['sweep'][::2]))
    say("E: sweep " + '; '.join(f"{x['k']}: {x['fling']:.3f} / {x['ladder_order']*100:.1f} / {x['locata_within']*100:.0f}" for x in res['E_sweep'][::2]))
    base = today['per_stop']
    for rule in RULES:
        ps = res['option_b'][rule]['scores']['per_stop']
        res['option_b'][rule]['stops_beating_today'] = int(sum(a < b - 1e-9 for a, b in zip(ps, base)))
        res['option_b'][rule]['stops_tied'] = int(sum(abs(a - b) <= 1e-9 for a, b in zip(ps, base)))
        say(f"{rule}: turned stops closer than today {res['option_b'][rule]['stops_beating_today']} of {len(ps)}, tied {res['option_b'][rule]['stops_tied']}")
    (REPO / 'results/rotation/inapp/numbers.json').write_text(json.dumps(res, indent=1, default=lambda o: o.item()))
    t = '\n'.join(txt)
    (REPO / 'results/rotation/inapp/scores.txt').write_text(t + '\n')
    print(t)


if __name__ == '__main__':
    main()
