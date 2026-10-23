#!/usr/bin/env python3
"""Brief 21: score update policies over time against LOCATA's continuous truth.

Every policy holds one displayed value per utterance at each moment, and is scored on the truth's GRID (50 ms) from the
onset to the utterance's end, at valid truth only:
  error        time-weighted (each grid step counts once): mean and median, and the share of time within tolerance
  coverage     the share of the time a value is shown at all (none before the first read)
  moves        changes of the shown value by more than MOVE_DEG (angle) or MOVE_RATIO (range), per minute of speech;
               for GccPhat's policies counted from the lock on (its settling dot is the same under all of them)
  lag          an out-of-tolerance episode starts when the shown value was within tolerance and then isn't; its length
               is how long until it is within again (or the utterance ends: censored, counted at its observed length)

ANGLE (deg, the pair's bearing; tolerance 10 deg)
  gcc_shipped      GccPhat's stream as shipped: its dot after every push while it settles, then the lock, held
  a2_shipped       Angle2.readUtterance's onset (brief 11's "own onset"), shown from when it recurred (at3), held
  slide<S>_raw     after the lock, every half-second re-read every S seconds is shown: no rule (the jitter reference)
  slide<S>_T<D>    after the lock, a re-read every S seconds moves the shown value only when it passes brief 11's dim rule
                   (margin >= MARGIN, and not within 10 deg of a pause read of share >= PAUSE_SHARE) and differs from
                   the shown value by more than D deg (D = 0, 5, 10, 15)
RANGE (distance ratio to the talker's opener, its first utterance in the recording, whose own utterance is not scored;
       CDR to ratio by the room law, 6 dB per doubling: 10^((CDR_opener - CDR) / 20); tolerance 25%)
  per_utt_<bands>         the CDR of the utterance's first half second, shown from 0.5 s, held (the shipped range)
  slide<W>_<bands>        the CDR of the last W seconds (0.5 or 1; shorter until W is available), every 0.25 s
  bands: shipped (1.1-8 kHz in three bands, as cdr_direct) or lf (0.1-1 kHz)
FACING, two ways. The truth's own rate of change: a perfect facing reading taken per utterance (at its onset), per
  phrase (at each phrase's start) or every 0.25 / 0.5 s, held, scored against the truth's facing. And brief 20's cue
  (HF - LF CDR against the talker's opener) under the same policies (facing_cue's docstring).
MOTION: how far bearing, distance, head orientation and facing move over 0.25, 0.5 and 1 s within voiced speech.

usage: python3 score.py WORK_DIR OUT_DIR
"""
import json
import math
import statistics as st
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

from range_hops import window_db

GRID = 0.05
MARGIN, PAUSE_SHARE = 0.2, 0.5
ANG_TOL, MOVE_DEG = 10.0, 0.5
RNG_TOL_DB, MOVE_RATIO = 20 * math.log10(1.25), 0.10
HOP_S = 512 / 48000
STEPS = (0.25, 0.5)
THRESH = (0, 5, 10, 15)


def load(work):
    cuts, reads = {}, {}
    for p in sorted(work.glob('utt_*.jsonl')):
        for l in open(p):
            c = json.loads(l)
            c.pop('L'); c.pop('R')
            cuts[c['id']] = c
    for p in sorted(work.glob('reads_*.jsonl')):
        for l in open(p):
            q = json.loads(l)
            reads[q['id']] = q
    hops = {}
    for p in sorted(work.glob('hops_*.npz')):
        z = np.load(p)
        for k in z.files:
            cid, band, kind = k.split('#')
            hops.setdefault(cid.replace('|', '/'), {}).setdefault(band, {})[kind] = z[k]
    return cuts, reads, hops


def held_series(ts, events):
    """events: sorted (time, value); the value shown at each t is the last event at or before it (None before)."""
    out, j, cur = [], 0, None
    for t in ts:
        while j < len(events) and events[j][0] <= t + 1e-9:
            cur = events[j][1]; j += 1
        out.append(cur)
    return out


def score_series(shown, truth, valid, tol, move, dist, ts=None, move_from=0.0):
    """shown/truth on the grid; dist(a, b) is the error between two values. Moves are counted from move_from (s) on:
    GccPhat's dot settles in its first half second under every policy alike, so its moves count from the lock."""
    err, lags, moves, prev, inside, ep = [], [], 0, None, None, None
    cov = []
    ts = ts or [0.0] * len(shown)
    for s, t, ok, tt in zip(shown, truth, valid, ts):
        if s is not None and prev is not None and dist(s, prev) > move and tt >= move_from - 1e-9:
            moves += 1
        if s is not None:
            prev = s
        if not ok:
            continue
        cov.append(s is not None)
        if s is None:
            continue
        e = dist(s, t)
        err.append(e)
        now = e <= tol
        if inside is True and not now:
            ep = 0
        if ep is not None:
            if now:
                lags.append(ep * GRID); ep = None
            else:
                ep += 1
        inside = now
    if ep is not None:
        lags.append(ep * GRID)
    return err, cov, moves, lags


def summarise(acc, tol):
    e = [x for a in acc for x in a['err']]
    lags = [x for a in acc for x in a['lags']]
    minutes = sum(a['dur'] for a in acc) / 60
    minutes_after = sum(a.get('dur_after', a['dur']) for a in acc) / 60
    return {'utterances': len(acc), 'grid_points': len(e),
            'coverage_pct': round(100 * np.mean([x for a in acc for x in a['cov']]), 1) if acc else None,
            'mean_err': round(float(np.mean(e)), 2) if e else None, 'median_err': round(float(np.median(e)), 2) if e else None,
            'within_tol_pct': round(100 * np.mean([x <= tol for x in e]), 1) if e else None,
            'moves_per_min': round(sum(a['moves'] for a in acc) / minutes_after, 1) if minutes_after else None,
            'lag_episodes': len(lags), 'lag_median_s': round(float(np.median(lags)), 2) if lags else None,
            'lag_p90_s': round(float(np.percentile(lags, 90)), 2) if lags else None}


def angle_policies(c, q):
    ts = [g['t'] for g in c['truth']]
    track = [(t, d) for t, d in q['track']]
    pol = {'gcc_shipped': held_series(ts, track)}
    a2 = q.get('a2')
    pol['a2_shipped'] = held_series(ts, [(max(0.0, a2['at3']), a2['deg'])]) if a2 else [None] * len(ts)
    if 'lock' not in q:
        return pol
    lock_t = q['lock']['t']
    p = q.get('pause')
    for step in STEPS:
        # the re-reads come every 0.25 s from the lock; every 0.5 s is every second one of them
        k = round(step / 0.25)
        sl = [s for s in q['slides'] if round((s[0] - lock_t) / 0.25) % k == 0]
        pol[f'slide{step}_raw'] = held_series(ts, track + [(s[0], s[1]) for s in sl])
        for thr in THRESH:
            ev, cur = list(track), q['lock']['deg']
            for t, deg, share, margin in sl:
                ok = margin >= MARGIN and not (p and p['share'] >= PAUSE_SHARE and abs(deg - p['deg']) <= 10)
                if ok and abs(deg - cur) > thr:
                    cur = deg; ev.append((t, deg))
            pol[f'slide{step}_T{thr}'] = held_series(ts, ev)
    return pol


def range_policies(c, h, opener_db):
    ts = [g['t'] for g in c['truth']]
    out = {}
    for band in ('shipped', 'lf'):
        dp, fp = h[band]['dir'], h[band]['dif']
        nh = len(dp)
        first = window_db(dp, fp, 0, min(nh, round(0.5 / HOP_S)))
        conv = lambda db: None if db is None or opener_db[band] is None else 10 ** ((opener_db[band] - db) / 20)
        out[f'per_utt_{band}'] = held_series(ts, [(0.5, conv(first))])
        for W in (0.5, 1.0):
            ev = []
            t = 0.5
            while t <= c['dur_s'] + 1e-9:
                b = min(nh, round(t / HOP_S)); a = max(0, b - round(W / HOP_S))
                ev.append((round(t, 3), conv(window_db(dp, fp, a, b))))
                t += 0.25
            out[f'slide{W}_{band}'] = held_series(ts, ev)
    return out


def ang_dist(a, b):
    return abs(a - b)


def rng_dist(a, b):
    return abs(20 * math.log10(a / b))


def wrap(d):
    return abs((d + 180) % 360 - 180)


def auc(pos, neg):
    """The chance a value from pos beats one from neg (ties half)."""
    from scipy.stats import rankdata
    if not pos or not neg:
        return None
    rk = rankdata(np.array(pos + neg, float))
    return round(float((rk[:len(pos)].sum() - len(pos) * (len(pos) + 1) / 2) / (len(pos) * len(neg))), 3)


def facing_cue(cuts, hops):
    """Brief 20's facing estimate, F = HF CDR - unfloored LF CDR, taken against the talker's opener (F - F_opener), read
    under each update policy and scored on the grid against the tracked facing: how well the shown value separates
    toward (< 90 deg) from away, raw and with log distance (relative to the opener) regressed out as brief 20 did; and,
    in utterances where the head really turns (facing changes > 45 deg first to last), whether the shown value moves
    the right way (turning away should lower F). The opener's own utterance isn't scored."""
    def F(h, a, b):
        hf = window_db(h['hf']['dir'], h['hf']['dif'], a, b)
        lf = window_db(h['lf']['dir'], h['lf']['dif'], a, b)
        return None if hf is None or lf is None else hf - lf
    by_talker = defaultdict(list)
    for c in cuts.values():
        by_talker[(c['recording'], c['talker'], c['pair_mm'])].append(c)
    pts = defaultdict(list)
    turns = defaultdict(list)
    for (rec, tk, sp), cs in by_talker.items():
        cs.sort(key=lambda c: c['onset_s'])
        op = next((c for c in cs if c['truth'][0]['valid'] and c['id'] in hops), None)
        if op is None:
            continue
        h0 = hops[op['id']]
        f_open = F(h0, 0, min(len(h0['hf']['dir']), round(0.5 / HOP_S)))
        d_open = op['truth'][0]['dist']
        if f_open is None:
            continue
        for c in cs:
            if c is op or c['id'] not in hops:
                continue
            h = hops[c['id']]
            nh = len(h['hf']['dir'])
            win = lambda t0, t1: F(h, max(0, round(t0 / HOP_S)), min(nh, round(t1 / HOP_S)))
            pols = {'per_utterance': [(0.5, win(0, 0.5))],
                    'per_phrase': [(min(p0 + 0.5, c['dur_s']), win(p0, min(p0 + 0.5, c['dur_s']))) for p0, _ in c['phrases']]}
            for W in (0.5, 1.0):
                pols[f'sliding_{W}s'] = [(round(t, 3), win(max(0, t - W), t)) for t in np.arange(0.5, c['dur_s'] + 1e-9, 0.25)]
            ts = [g['t'] for g in c['truth']]
            for name, ev in pols.items():
                ev = [(t, v - f_open) for t, v in ev if v is not None]
                shown = held_series(ts, ev)
                seen = []
                for g, v in zip(c['truth'], shown):
                    if v is None or not g['valid'] or g['facing'] is None:
                        continue
                    pts[f'{sp}|{name}'].append((v, g['facing'], math.log10(g['dist'] / d_open), c['id']))
                    seen.append((v, g['facing']))
                if len(seen) >= 2 and abs(seen[-1][1] - seen[0][1]) > 45:
                    dv = seen[-1][0] - seen[0][0]
                    turns[f'{sp}|{name}'].append(None if dv == 0 else (dv < 0) == (seen[-1][1] > seen[0][1]))
    out = {}
    for k, v in sorted(pts.items()):
        f = np.array([x[0] for x in v]); fac = np.array([x[1] for x in v]); ld = np.array([x[2] for x in v])
        A = np.vstack([np.ones_like(ld), ld]).T
        resid = f - A @ np.linalg.lstsq(A, f, rcond=None)[0]
        tw = fac < 90
        from scipy.stats import spearmanr
        tr = turns.get(k, [])
        # grid points within an utterance are not independent: the interval resamples whole utterances
        ids = np.array([x[3] for x in v]); uniq = np.unique(ids)
        idx = {u: np.flatnonzero(ids == u) for u in uniq}
        rng = np.random.default_rng(0)
        boots = []
        for _ in range(200):
            sel = np.concatenate([idx[u] for u in rng.choice(uniq, len(uniq))])
            a_ = auc(f[sel][tw[sel]].tolist(), f[sel][~tw[sel]].tolist())
            if a_ is not None:
                boots.append(a_)
        out[k] = {'grid_points': len(v), 'utterances': len(uniq), 'away_share_pct': round(100 * float(np.mean(~tw)), 1),
                  'auc_toward_vs_away': auc(f[tw].tolist(), f[~tw].tolist()),
                  'auc_95pct_interval_by_utterance': [round(float(np.percentile(boots, 2.5)), 3), round(float(np.percentile(boots, 97.5)), 3)],
                  'auc_distance_removed': auc(resid[tw].tolist(), resid[~tw].tolist()),
                  'spearman_with_facing': round(float(spearmanr(f, fac)[0]), 3),
                  'head_turns': len(tr),
                  'moved_right_way_pct': round(100 * sum(x is True for x in tr) / len(tr), 1) if tr else None,
                  'did_not_move_pct': round(100 * sum(x is None for x in tr) / len(tr), 1) if tr else None}
    return out


def main():
    work, out = Path(sys.argv[1]), Path(sys.argv[2])
    out.mkdir(parents=True, exist_ok=True)
    cuts, reads, hops = load(work)
    res = {'checks': {'cuts': len(cuts), 'reads': len(reads), 'span_read_matches_lock': sum(q.get('span_matches_lock', False) for q in reads.values()),
                      'locked': sum('lock' in q for q in reads.values()), 'a2_read': sum(q.get('a2') is not None for q in reads.values())}}

    # ---- motion during voiced speech ----
    mot = defaultdict(lambda: defaultdict(list))
    for c in cuts.values():
        if c['pair_mm'] != 160:
            continue
        g = c['truth']
        task = c['recording'].split('_')[1]
        for h in (0.25, 0.5, 1.0):
            k = round(h / GRID)
            for i in range(len(g) - k):
                a, b = g[i], g[i + k]
                if not (a['valid'] and b['valid'] and a['phrase'] >= 0 and b['phrase'] >= 0):
                    continue
                for tk in ('all', task):
                    m = mot[(h, tk)]
                    m['bearing_deg'].append(abs(b['deg'] - a['deg']))
                    m['dist_m'].append(abs(b['dist'] - a['dist']))
                    m['dist_pct'].append(100 * abs(b['dist'] / a['dist'] - 1))
                    m['head_deg'].append(wrap(b['head_az'] - a['head_az']))
                    if a['facing'] is not None and b['facing'] is not None:
                        m['facing_deg'].append(abs(b['facing'] - a['facing']))
    res['motion'] = {f'{h}s {tk}': {q: {'n': len(v), 'median': round(float(np.median(v)), 2), 'p90': round(float(np.percentile(v, 90)), 2),
                                        'p99': round(float(np.percentile(v, 99)), 2)} for q, v in m.items()}
                     for (h, tk), m in sorted(mot.items())}

    # ---- angle ----
    acc = defaultdict(list)
    for cid, c in cuts.items():
        q = reads[cid]
        truth = [g['deg'] for g in c['truth']]
        valid = [g['valid'] for g in c['truth']]
        task = c['recording'].split('_')[1]
        ts = [g['t'] for g in c['truth']]
        lock_t = q['lock']['t'] if 'lock' in q else 0.0
        for name, shown in angle_policies(c, q).items():
            mf = 0.0 if name == 'a2_shipped' else lock_t + GRID      # from the first step after the dot locks
            e, cov, mv, lags = score_series(shown, truth, valid, ANG_TOL, MOVE_DEG, ang_dist, ts, mf)
            item = {'err': e, 'cov': cov, 'moves': mv, 'lags': lags, 'dur': c['dur_s'], 'dur_after': max(c['dur_s'] - mf, 0.0)}
            for key in (f"{c['pair_mm']}|all|{name}", f"{c['pair_mm']}|{task}|{name}"):
                acc[key].append(item)
            moved = max(truth) - min(truth) > 10
            acc[f"{c['pair_mm']}|{'moving' if moved else 'still'}|{name}"].append(item)
    res['angle'] = {k: summarise(v, ANG_TOL) for k, v in sorted(acc.items())}

    # ---- range ----
    acc = defaultdict(list)
    track_dir = defaultdict(list)
    by_talker = defaultdict(list)
    for cid, c in cuts.items():
        by_talker[(c['recording'], c['talker'], c['pair_mm'])].append(c)
    for key, cs in by_talker.items():
        cs.sort(key=lambda c: c['onset_s'])
        op = next((c for c in cs if c['truth'][0]['valid'] and c['id'] in hops), None)
        if op is None:
            continue
        h0 = hops[op['id']]
        op_db = {b: window_db(h0[b]['dir'], h0[b]['dif'], 0, min(len(h0[b]['dir']), round(0.5 / HOP_S))) for b in ('shipped', 'lf')}
        d_open = op['truth'][0]['dist']
        for c in cs:
            if c is op or c['id'] not in hops:
                continue
            truth = [g['dist'] / d_open for g in c['truth']]
            valid = [g['valid'] for g in c['truth']]
            task = c['recording'].split('_')[1]
            for name, shown in range_policies(c, hops[c['id']], op_db).items():
                e, cov, mv, lags = score_series(shown, truth, valid, RNG_TOL_DB, 20 * math.log10(1 + MOVE_RATIO), rng_dist)
                item = {'err': e, 'cov': cov, 'moves': mv, 'lags': lags, 'dur': c['dur_s']}
                for k2 in (f"{c['pair_mm']}|all|{name}", f"{c['pair_mm']}|{task}|{name}"):
                    acc[k2].append(item)
                # does a moving range follow a real change of distance within the utterance?
                vt = [(s, t) for s, t, ok in zip(shown, truth, valid) if ok and s is not None]
                if len(vt) >= 2 and abs(math.log(vt[-1][1] / vt[0][1])) > math.log(1.2):
                    track_dir[f"{c['pair_mm']}|{name}"].append(
                        (math.log(vt[-1][0] / vt[0][0]) > 0) == (vt[-1][1] > vt[0][1]) if vt[-1][0] != vt[0][0] else None)
    res['range'] = {k: summarise(v, RNG_TOL_DB) for k, v in sorted(acc.items())}
    res['range_follows_real_change'] = {k: {'utterances': len(v), 'moved_right_way_pct': round(100 * sum(x is True for x in v) / len(v), 1),
                                            'did_not_move_pct': round(100 * sum(x is None for x in v) / len(v), 1)}
                                        for k, v in sorted(track_dir.items()) if v}

    # ---- facing: the truth's own rate of change, and what updating less often costs with a perfect reading ----
    fac = defaultdict(list)
    spans = defaultdict(list)
    for c in cuts.values():
        if c['pair_mm'] != 160:
            continue
        g = c['truth']
        ts = [x['t'] for x in g]
        truth = [x['facing'] for x in g]
        valid = [x['valid'] and x['facing'] is not None for x in g]
        if not any(valid):
            continue
        fv = [f for f, ok in zip(truth, valid) if ok]
        spans['utterance'].append(max(fv) - min(fv))
        for pi in range(len(c['phrases'])):
            pv = [x['facing'] for x in g if x['phrase'] == pi and x['valid'] and x['facing'] is not None]
            if pv:
                spans['phrase'].append(max(pv) - min(pv))
        first_valid = lambda t0: next((f for t, f, ok in zip(ts, truth, valid) if ok and t >= t0 - 1e-9), None)
        pols = {'per_utterance': [(0.0, first_valid(0.0))],
                'per_phrase': [(p[0], first_valid(p[0])) for p in c['phrases']]}
        for step in (0.25, 0.5):
            pols[f'every_{step}s'] = [(t, first_valid(t)) for t in np.arange(0, c['dur_s'] + 1e-9, step)]
        for name, ev in pols.items():
            ev = [(t, f) for t, f in ev if f is not None]
            shown = held_series(ts, ev)
            e, cov, mv, lags = score_series(shown, [f if f is not None else 0 for f in truth], valid, 30.0, MOVE_DEG, ang_dist)
            fac[name].append({'err': e, 'cov': cov, 'moves': mv, 'lags': lags, 'dur': c['dur_s']})
    res['facing_truth'] = {k: summarise(v, 30.0) for k, v in fac.items()}
    res['facing_spread'] = {k: {'n': len(v), 'median_deg': round(float(np.median(v)), 1), 'p90_deg': round(float(np.percentile(v, 90)), 1),
                                'over_30_pct': round(100 * np.mean([x > 30 for x in v]), 1)} for k, v in spans.items()}
    res['phrases_per_utterance'] = round(float(np.mean([len(c['phrases']) for c in cuts.values() if c['pair_mm'] == 160])), 2)
    res['facing_cue'] = facing_cue(cuts, hops)
    (out / 'summary.json').write_text(json.dumps(res, indent=1))
    print(json.dumps(res['checks']))


if __name__ == '__main__':
    main()
