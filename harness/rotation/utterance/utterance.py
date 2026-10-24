#!/usr/bin/env python3
"""Brief G: how much speech the facing call needs (2026-10-24).

The call is round 1's: the contrast CDR 4-8 kHz minus CDR 0.1-1.1 kHz, below one fixed threshold (about -1 dB) means
turned. Round 1 scored it on whole stops (~7 s of pooled speech); the live app gets one utterance at a time.

    python harness/rotation/utterance/utterance.py          # numbers -> results/rotation/utterance/numbers.json
    python harness/rotation/utterance/utterance.py --plot   # and the figures

THE SPEECH MASK. A hop is speech when its own 1.1-8 kHz power, smoothed over 5 hops (53 ms), is at least 10 dB over the
tape's 20th percentile: facing_pooled.py's rule, read per hop instead of per 0.5 s window. Each tape's first
HANDLING_S is skipped (the phone's ding and handling).

UTTERANCES. Each decode segment (tapes/<walk>/transcript.json), widened by PAD_S at either end (never past the midpoint
to its neighbour, since the decode's edges are approximate) and clipped to the stop, is cut at pauses of PAUSE_S or more
in the speech mask. A piece shorter than MIN_UTT_S is a breath or a click, not an utterance, and is dropped.

ONE UTTERANCE, AS THE APP READS IT. The estimator restarts cold at the utterance's first speech hop, as the Conductor's
does at each onset, and its first SETTLE_S of hops are not used. The whole-utterance contrast sums the speech hops from
there to the end. The Conductor's range read sums every hop from SETTLE_S to RANGE_READ_S (conductor.py: the frames
whose window ends by onset + 0.5 s).

THE THRESHOLD is fixed_threshold.py's, recomputed left out by walk on the other walks' whole stops: the number a live
app would carry. A second threshold, chosen on the other walks' utterances themselves, shows how much of any loss is a
shift of the contrast at short lengths rather than scatter.
"""
import argparse
import contextlib
import io
import json
import runpy
import sys
from pathlib import Path

import numpy as np

import hops
from hops import HOP, HOP_S, NFFT, REPO, SR

HANDLING_S = 2.0
PAUSE_S = 0.3
PAD_S = 0.2
MIN_UTT_S = 0.25
SETTLE_S, RANGE_READ_S = 0.13, 0.5          # conductor.py
K0 = int(np.ceil(SETTLE_S / HOP_S))         # first hop after the settle: 13
K_READ = int((RANGE_READ_S * SR - NFFT) // HOP)   # last hop whose window ends by 0.5 s: 42
BINS = ((0, 1), (1, 2), (2, 4), (4, 99))
POOL_S = (0.5, 1, 2, 3, 4, 5, 7)
DRAWS = 300
GRID = np.arange(-15, 15.01, 0.25)
TURNS = {'walk-160546': dict(circle=(16.1, 33.0), ref=(5.6, 16.0), dir='counterclockwise, 1.25 m'),   # colour.py
         'walk-161331': dict(circle=(8.2, 21.4), ref=(0.0, 8.2), dir='clockwise, 2 m, folded to 111 mm'),
         'walk-020305': dict(circle=(125.7, 138.1), ref=(90.0, 119.5), dir='counterclockwise, small carpeted room')}
# walk-122038's decode runs 1.5-2.5 s late on its first callouts: 18% of the speech in its stops falls inside a decode
# segment (90-100% on every other walk), so cutting by segments finds 2 utterances, and its stops, read from that decode,
# may each hold the next callout. Set aside here; the stop threshold (round 1's) still includes it.
SET_ASIDE = {'walk-122038': 'decode 1.5-2.5 s late against the speech; 18% of its stop speech inside a segment'}
OUT = REPO / 'results/rotation/utterance'
RNG = np.random.default_rng(20261024)


def contrast(D, R):
    """CDR 4-8 kHz minus CDR 0.1-1.1 kHz from summed powers (bands LF_raw, B1, B2, B3)."""
    return float(10 * np.log10(D[3] / R[3]) - 10 * np.log10(D[0] / R[0]))


def speech(E):
    e = 10 * np.log10(np.convolve(E, np.ones(5) / 5, mode='same') + 1e-30)
    t = np.arange(len(E)) * HOP_S
    late = t >= HANDLING_S
    return late & (e >= np.percentile(e[late], 20) + 10)


def stop_thresholds():
    """fixed_threshold.py's threshold per left-out walk, on band_windows' whole stops, and one on all of them."""
    sys.path.insert(0, str(REPO / 'harness/rotation'))
    with contextlib.redirect_stdout(io.StringIO()):
        g = runpy.run_path(str(REPO / 'harness/rotation/room_reference.py'))
    S = g['S']
    c = np.array([s['c'] for s in S]); y = np.array([s['toward'] for s in S]); w = np.array([s['walk'] for s in S])
    best = lambda m: float(max(GRID, key=lambda t: (np.mean(c[m & y] >= t) + np.mean(c[m & ~y] < t)) / 2))
    return {wk: best(w != wk) for wk in g['walks']}, best(np.ones(len(c), bool))


def cuts(segs, a, b, sp):
    """Utterances (first hop, last hop + 1) inside [a, b] s."""
    segs = sorted(segs, key=lambda s: s['t0'])
    out = []
    for k, s in enumerate(segs):
        lo, hi = s['t0'] - PAD_S, s['t1'] + PAD_S
        if k:
            lo = max(lo, (segs[k - 1]['t1'] + s['t0']) / 2)
        if k + 1 < len(segs):
            hi = min(hi, (s['t1'] + segs[k + 1]['t0']) / 2)
        lo, hi = max(lo, a, HANDLING_S), min(hi, b)
        if hi <= lo:
            continue
        i_lo, i_hi = int(np.ceil(lo / HOP_S)), int((hi * SR - NFFT) // HOP) + 1
        idx = np.flatnonzero(sp[i_lo:max(i_lo, i_hi)]) + i_lo
        if not len(idx):
            continue
        for run in np.split(idx, np.flatnonzero(np.diff(idx) * HOP_S > PAUSE_S) + 1):
            out.append((int(run[0]), int(run[-1]) + 1))
    return out


def utterances(walk, spans, sp, x, d, segs):
    """spans: [(a, b, facing, spot, stop_id)]. Cold reads of each utterance."""
    rows, dropped = [], 0
    for a, b, fd, spot, sid in spans:
        for i0, i1 in cuts(segs, a, b, sp):
            dur = (i1 - i0) * HOP_S
            if dur < MIN_UTT_S:
                dropped += 1
                continue
            D, R, _ = hops.cold(x, d, i0, i1)
            k = np.arange(len(D))
            whole = (k >= K0) & sp[i0:i0 + len(D)]
            r = dict(walk=walk, spot=spot, facing=fd, stop=sid, t0=round(i0 * HOP_S, 3), t1=round(i1 * HOP_S, 3),
                     dur=round(dur, 3), speech_s=round(whole.sum() * HOP_S, 3),
                     D=D[whole].sum(0).tolist(), R=R[whole].sum(0).tolist(), c=contrast(D[whole].sum(0), R[whole].sum(0)))
            if dur >= RANGE_READ_S:
                m = (k >= K0) & (k <= K_READ)
                r['c_read'] = contrast(D[m].sum(0), R[m].sum(0))
            rows.append(r)
    return rows, dropped


def bal(c, y, th):
    """Balanced accuracy, facing's and turned's hit rates; th per row."""
    c, y, th = map(np.asarray, (c, y, th))
    if not y.any() or y.all():
        return None
    a, b = np.mean(c[y] >= th[y]), np.mean(c[~y] < th[~y])
    return dict(bal=round(float((a + b) / 2) * 100, 1), facing=f"{int(np.sum(c[y] >= th[y]))}/{int(y.sum())}",
                turned=f"{int(np.sum(c[~y] < th[~y]))}/{int((~y).sum())}")


def tuned(c, y, w):
    """Threshold per row chosen on the other walks' rows of the same kind."""
    c, y, w = map(np.asarray, (c, y, w))
    th = {}
    for wk in set(w):
        m = w != wk
        th[wk] = max(GRID, key=lambda t: (np.mean(c[m & y] >= t) + np.mean(c[m & ~y] < t)) / 2)
    return np.array([th[v] for v in w])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--plot', action='store_true')
    plot = ap.parse_args().plot
    TH, TH_ALL = stop_thresholds()
    lab = json.loads((REPO / 'harness/rotation/facing_stops.json').read_text())['stops']
    U, stops, dropped = [], [], 0
    for walk, spots in lab.items():
        if walk in SET_ASIDE:
            continue
        h = hops.tape(walk); sp = speech(h['E']); x = hops.audio(walk); d = hops.baseline(walk)
        segs = json.loads((REPO / 'tapes' / walk / 'transcript.json').read_text())['segments']
        spans = []
        for spot, ss in spots.items():
            if spot == 'dist_m':
                continue
            for a, b, fd in ss:
                if fd == 0 or fd >= 90:
                    sid = len(stops)
                    spans.append((a, b, fd, spot, sid))
                    i = np.arange(len(sp))
                    m = sp & (i * HOP_S >= a) & (i * HOP_S + NFFT / SR <= b)
                    stops.append(dict(walk=walk, spot=spot, facing=fd, a=a, b=b, idx=np.flatnonzero(m),
                                      c=contrast(h['D'][m].sum(0), h['R'][m].sum(0)) if m.sum() >= 2 else None))
        rows, dr = utterances(walk, spans, sp, x, d, segs)
        U += rows; dropped += dr
    stops = [s for s in stops if s['c'] is not None]
    for s in stops:
        s['toward'] = s['facing'] == 0; s['th'] = TH[s['walk']]
    for u in U:
        u['toward'] = u['facing'] == 0; u['th'] = TH[u['walk']]
    N = {}
    lines = []; say = lines.append

    # 0. the bar, on this per-hop speech mask: whole stops against the left-out stop threshold
    sc = [s['c'] for s in stops]; sy = [s['toward'] for s in stops]
    N['stops'] = dict(n=len(stops), speech_s_mean=round(float(np.mean([len(s['idx']) for s in stops]) * HOP_S), 1),
                      thresholds=dict(min=min(TH.values()), max=max(TH.values()), all_walks=TH_ALL),
                      whole_stop=bal(sc, sy, [s['th'] for s in stops]))
    say(f"stops {len(stops)}, speech per stop {N['stops']['speech_s_mean']} s (per-hop mask); whole stop: {N['stops']['whole_stop']}")
    say(f"left-out stop thresholds {min(TH.values()):+.2f} to {max(TH.values()):+.2f} dB; all walks {TH_ALL:+.2f}")

    # 1-2. one utterance alone
    c = np.array([u['c'] for u in U]); y = np.array([u['toward'] for u in U]); th = np.array([u['th'] for u in U])
    w = np.array([u['walk'] for u in U]); dur = np.array([u['dur'] for u in U])
    out_ = np.abs(c - np.median(c)) > 15
    N['utterances'] = dict(n=len(U), dropped_short=dropped, outliers=int(out_.sum()),
                           outlier_rows=[{k: U[i][k] for k in ('walk', 't0', 't1', 'dur', 'c')} for i in np.flatnonzero(out_)],
                           dur_mean=round(float(dur.mean()), 2),
                           per_walk={wk: int(np.sum(w == wk)) for wk in sorted(set(w))})
    keep = ~out_
    th_u = tuned(c[keep], y[keep], w[keep])
    th_u_full = np.full(len(c), np.nan); th_u_full[keep] = th_u
    N['alone'] = {}
    for lo, hi in BINS + ((0, 99),):
        m = keep & (dur >= lo) & (dur < hi)
        name = 'all' if (lo, hi) == (0, 99) else (f'{lo}-{hi} s' if hi < 99 else f'{lo} s and over')
        N['alone'][name] = dict(n=int(m.sum()), dur_mean=round(float(dur[m].mean()), 2),
                                facing_mean=round(float(c[m & y].mean()), 2), facing_sd=round(float(c[m & y].std()), 2),
                                turned_mean=round(float(c[m & ~y].mean()), 2), turned_sd=round(float(c[m & ~y].std()), 2),
                                stop_threshold=bal(c[m], y[m], th[m]), utterance_threshold=bal(c[m], y[m], th_u_full[m]))
        a = N['alone'][name]
        say(f"alone {name:>12}: n {a['n']:3d} (mean {a['dur_mean']} s)  facing {a['facing_mean']:+.1f}±{a['facing_sd']:.1f}"
            f"  turned {a['turned_mean']:+.1f}±{a['turned_sd']:.1f}  stop th {a['stop_threshold']}  utt th {a['utterance_threshold']}")
    spch = np.array([u['speech_s'] for u in U])
    for name, m in (('under 1 s, 0.25 s or more of speech', keep & (dur < 1) & (spch >= 0.25)),
                    ('under 1 s, tails (under 0.25 s of speech)', keep & (dur < 1) & (spch < 0.25))):
        N['alone'][name] = dict(n=int(m.sum()), dur_mean=round(float(dur[m].mean()), 2),
                                stop_threshold=bal(c[m], y[m], th[m]), utterance_threshold=bal(c[m], y[m], th_u_full[m]))
        say(f"alone {name}: {N['alone'][name]}")
    N['alone']['utterance_thresholds'] = dict(min=float(np.min(th_u)), max=float(np.max(th_u)))

    # 3. the pooling curve: contiguous speech subsampled inside each stop (warm, tape-wide estimator)
    draws = {}
    for si, s in enumerate(stops):
        h = hops.tape(s['walk'])
        cd = np.vstack([np.zeros((1, 4)), np.cumsum(h['D'][s['idx']], 0)])
        cr = np.vstack([np.zeros((1, 4)), np.cumsum(h['R'][s['idx']], 0)])
        for L in POOL_S:
            m = int(round(L / HOP_S))
            if len(s['idx']) >= m:
                st = RNG.integers(0, len(s['idx']) - m + 1, DRAWS)
                Dm, Rm = cd[st + m] - cd[st], cr[st + m] - cr[st]
                draws[si, L] = 10 * np.log10(Dm[:, 3] / Rm[:, 3]) - 10 * np.log10(Dm[:, 0] / Rm[:, 0])
    full = [si for si in range(len(stops)) if (si, max(POOL_S)) in draws]
    N['pooling'] = dict(population=f"{len(full)} stops with at least {max(POOL_S)} s of speech "
                                   f"({sum(stops[i]['toward'] for i in full)} facing, {sum(not stops[i]['toward'] for i in full)} turned)",
                        draws=DRAWS, curve={})
    def frac_bal(si_list, L, thf):
        fa = [np.mean(draws[i, L] >= thf(i, L)) for i in si_list if stops[i]['toward']]
        tu = [np.mean(draws[i, L] < thf(i, L)) for i in si_list if not stops[i]['toward']]
        return round(float((np.mean(fa) + np.mean(tu)) / 2) * 100, 1), round(float(np.mean(fa)) * 100, 1), round(float(np.mean(tu)) * 100, 1)
    def matched(si_list, L):
        """threshold chosen on the other walks' draws at this length, stops weighted equally"""
        ths = {}
        for wk in {stops[i]['walk'] for i in si_list}:
            o = [i for i in si_list if stops[i]['walk'] != wk]
            ths[wk] = max(GRID, key=lambda t: (np.mean([np.mean(draws[i, L] >= t) for i in o if stops[i]['toward']]) +
                                               np.mean([np.mean(draws[i, L] < t) for i in o if not stops[i]['toward']])) / 2)
        return lambda i, L: ths[stops[i]['walk']]
    for L in POOL_S:
        allL = [si for si in range(len(stops)) if (si, L) in draws]
        b, fa, tu = frac_bal(full, L, lambda i, L: stops[i]['th'])
        bm = frac_bal(full, L, matched(full, L))[0]
        ba = frac_bal(allL, L, lambda i, L: stops[i]['th'])[0]
        sd = float(np.mean([draws[i, L].std() for i in full]))
        N['pooling']['curve'][L] = dict(bal=b, facing=fa, turned=tu, bal_length_matched_threshold=bm,
                                        bal_all_stops_with_this_much=ba, n_all=len(allL), draw_sd_in_stop=round(sd, 2))
        say(f"pool {L:>3} s: bal {b}% (facing {fa}, turned {tu}); matched th {bm}%; all {len(allL)} stops {ba}%; in-stop sd {sd:.2f} dB")
    xs = list(POOL_S)
    def cross(level, ys):
        for i in range(1, len(xs)):
            if ys[i - 1] < level <= ys[i]:
                return round(xs[i - 1] + (level - ys[i - 1]) / (ys[i] - ys[i - 1]) * (xs[i] - xs[i - 1]), 1)
        return None if ys[0] < level else xs[0]
    ys = [N['pooling']['curve'][L]['bal'] for L in xs]; ya = [N['pooling']['curve'][L]['bal_all_stops_with_this_much'] for L in xs]
    N['pooling']['reaches'] = {'70%': cross(70, ys), '75%': cross(75, ys)}
    N['pooling']['reaches_all_stops'] = {'70%': cross(70, ya), '75%': cross(75, ya)}
    say(f"pooling reaches 70% at {cross(70, ys)} s, 75% at {cross(75, ys)} s; all stops: {N['pooling']['reaches_all_stops']}")

    # 4. the Conductor's 0.13-0.5 s read, against the whole utterance (same utterances: 0.5 s and longer)
    m = keep & np.array(['c_read' in u for u in U])
    cr_ = np.array([u.get('c_read', np.nan) for u in U])
    N['read'] = dict(n=int(m.sum()), read=bal(cr_[m], y[m], th[m]), whole=bal(c[m], y[m], th[m]),
                     read_tuned=bal(cr_[m], y[m], tuned(cr_[m], y[m], w[m])),
                     read_minus_whole_mean=round(float(np.mean(cr_[m] - c[m])), 2),
                     read_minus_whole_sd=round(float(np.std(cr_[m] - c[m])), 2),
                     corr=round(float(np.corrcoef(cr_[m], c[m])[0, 1]), 2),
                     read_facing_mean=round(float(cr_[m & y].mean()), 2), read_turned_mean=round(float(cr_[m & ~y].mean()), 2),
                     read_sd_facing=round(float(cr_[m & y].std()), 2), read_sd_turned=round(float(cr_[m & ~y].std()), 2))
    say(f"read: {N['read']}")

    # 5. pooling at a held angle: each utterance summed with the earlier ones at its spot and facing
    N['held'] = {}
    for key_name, key in (('spot and facing', lambda u: (u['walk'], u['spot'], u['facing'])),
                          ('stop (one callout to the next)', lambda u: (u['walk'], u['stop'])),
                          ('spot only, whatever the facing', lambda u: (u['walk'], u['spot']))):
        acc, seen = {}, {}
        rows = []
        for i in sorted(np.flatnonzero(keep), key=lambda i: (U[i]['walk'], U[i]['t0'])):
            u = U[i]; g = key(u)
            Dg, Rg, ng, sg = acc.get(g, (np.zeros(4), np.zeros(4), 0, 0.0))
            Dg, Rg, ng, sg = Dg + u['D'], Rg + u['R'], ng + 1, sg + u['speech_s']
            acc[g] = (Dg, Rg, ng, sg)
            rows.append((ng, contrast(Dg, Rg), u['toward'], u['th'], sg))
        curve = {}
        for k in range(1, 13):
            r = [q for q in rows if q[0] == k]
            b = bal([q[1] for q in r], [q[2] for q in r], [q[3] for q in r])
            if b:
                curve[k] = dict(**b, n=len(r), pooled_s=round(float(np.mean([q[4] for q in r])), 1))
        first = next((k for k, v in curve.items() if v['bal'] >= 75), None)
        size = {}
        for i in np.flatnonzero(keep):
            size[key(U[i])] = size.get(key(U[i]), 0) + 1
        order = sorted(np.flatnonzero(keep), key=lambda i: (U[i]['walk'], U[i]['t0']))
        big = [size[key(U[i])] >= 4 for i in order]
        fixed = {}
        for k in range(1, 5):
            r = [q for q, bg in zip(rows, big) if bg and q[0] == k]
            b = bal([q[1] for q in r], [q[2] for q in r], [q[3] for q in r])
            if b:
                fixed[k] = dict(**b, n=len(r))
        N['held'][key_name] = dict(curve=curve, first_k_at_75=first, groups_of_4_or_more=fixed)
        say(f"   fixed population (groups of 4+): " + '; '.join(f"{k}: {v['bal']}% n{v['n']}" for k, v in fixed.items()))
        say(f"held [{key_name}]: " + '; '.join(f"{k}: {v['bal']}% n{v['n']} {v['pooled_s']}s" for k, v in curve.items()))

    # 6. the continuous turns
    N['turns'] = {}
    for walk, T in TURNS.items():
        h = hops.tape(walk); sp = speech(h['E']); x = hops.audio(walk); d = hops.baseline(walk)
        segs = json.loads((REPO / 'tapes' / walk / 'transcript.json').read_text())['segments']
        rows, _ = utterances(walk, [(0, len(sp) * HOP_S, None, 'tape', -1)], sp, x, d, segs)
        (a0, a1), (r0, r1) = T['circle'], T['ref']
        def where(r):
            mid = (r['t0'] + r['t1']) / 2
            if a0 <= mid <= a1:
                return round(360 * (mid - a0) / (a1 - a0))
            return 'ref' if r0 <= mid <= r1 else None
        ut = [dict(t0=r['t0'], t1=r['t1'], dur=r['dur'], c=round(r['c'], 2), call='facing' if r['c'] >= TH_ALL else 'turned',
                   at=where(r)) for r in rows]
        mid_turn = [u for u in ut if isinstance(u['at'], int) and 90 <= u['at'] <= 270]
        edge_turn = [u for u in ut if isinstance(u['at'], int) and not 90 <= u['at'] <= 270]
        ref = [u for u in ut if u['at'] == 'ref']
        N['turns'][walk] = dict(**T, threshold=TH_ALL, utterances=ut,
                                ref_calls=f"{sum(u['call'] == 'facing' for u in ref)}/{len(ref)} called facing",
                                turn_90_to_270=f"{sum(u['call'] == 'turned' for u in mid_turn)}/{len(mid_turn)} called turned",
                                turn_edges=f"{sum(u['call'] == 'turned' for u in edge_turn)}/{len(edge_turn)} called turned")
        say(f"turn {walk}: ref {N['turns'][walk]['ref_calls']}; 90-270 {N['turns'][walk]['turn_90_to_270']}; edges {N['turns'][walk]['turn_edges']}")

    OUT.mkdir(parents=True, exist_ok=True)
    N['set_aside'] = SET_ASIDE
    N['rows'] = [{k: (round(v, 3) if isinstance(v, float) else v) for k, v in u.items() if k not in ('D', 'R')} for u in U]
    (OUT / 'numbers.json').write_text(json.dumps(N, indent=1, default=lambda o: o.item() if hasattr(o, 'item') else str(o)))
    print('\n'.join(lines))
    if plot:
        import figures
        figures.draw(N, OUT)


if __name__ == '__main__':
    main()
