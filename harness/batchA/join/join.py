#!/usr/bin/env python3
"""Brief 11: join batch A (9 STARSS23, 10 LOCATA, 13 lab), attribute, test the fix copies, choose commit-or-dim, range.

usage: join.py <out dir> --starss shipped=<reads.jsonl.gz> [name=<reads.jsonl.gz> ...]
               --locata-truth <truth.jsonl> --locata shipped=<reads.jsonl> [name=<reads.jsonl> ...]
               --lab <lab reads.jsonl.gz> --range-starss <range.jsonl.gz> --range-locata <range.jsonl>
writes <out>/summary.json, <out>/moved.jsonl.gz, <out>/commit_curves.png
"""
import argparse
import gzip
import json
import math
import statistics as st
import sys
from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'scoring'))
import common as C        # noqa: E402
import rules as RU        # noqa: E402
import clean_score as CS  # noqa: E402

SCHEMES = {'gcc': 'GccPhat', 'a2': 'Angle2'}


def pct(a, b):
    return round(100 * a / b, 1) if b else None


def kv(arg):
    k, v = arg.split('=', 1)
    return k, v


# ---- 1. attribution -----------------------------------------------------------------------------------------------
def attribute(rows):
    out = {}
    for s in SCHEMES:
        for kind in ('speech', 'other'):
            w = [r for r in rows if r['scheme'] == s and r['kind'] == kind and C.in_scope(r) and r['err'] > C.OK]
            if not w:
                continue
            o = [r for r in w if r['err'] > C.OUT]
            prim, carry, prim_o = Counter(), Counter(), Counter()
            for r in w:
                f = C.fits(r)
                prim[f[0]] += 1
                for c in f:
                    carry[c] += 1
                if r['err'] > C.OUT:
                    prim_o[f[0]] += 1
            n_all = sum(1 for r in rows if r['scheme'] == s and r['kind'] == kind and C.in_scope(r))
            out[f'{SCHEMES[s]} {kind}'] = {
                'reads_in_scope': n_all, 'wrong': len(w), 'outliers': len(o),
                'causes': {c: {'primary_pct': pct(prim[c], len(w)), 'primary_of_outliers_pct': pct(prim_o[c], len(o)),
                               'carries_pct': pct(carry[c], len(w))} for c in C.CAUSES},
                'ranking': [c for c, _ in prim.most_common()]}
    return out


def lab_check(lab):
    out = {}
    for s in SCHEMES:
        conf = defaultdict(Counter)
        for r in lab:
            if r['scheme'] == s and r['err'] > C.OK:
                conf[C.lab_family(r['cause'])][C.fits(r)[0]] += 1
        out[SCHEMES[s]] = {fam: {'wrong_reads': sum(c.values()), 'attributed_pct': {k: pct(v, sum(c.values())) for k, v in c.most_common()}}
                           for fam, c in conf.items()}
    return out


# ---- 2. the fix copies against the shipped schemes ----------------------------------------------------------------
def score_set(rows):
    rows = [r for r in rows if C.in_scope(r)]
    n = len(rows)
    base = {'reads': n, 'within10_pct': pct(sum(r['err'] <= 10 for r in rows), n), 'over36_pct': pct(sum(r['err'] > 36 for r in rows), n),
            'median_err': round(st.median(r['err'] for r in rows), 1) if rows else None}
    scoped, kept, read_out, scen_out, scen_rows = CS.clean([{'id': r['id'], 'scenario': r['scenario'], 'truth': r['ref'], 'read': r['x']} for r in rows])
    base['rule'] = {'set_aside_pct': pct(len(read_out), len(scoped)), 'scenarios_dropped': sum(x['dropped'] for x in scen_rows),
                    'scenarios': len(scen_rows), 'kept_pct': pct(len(kept), len(scoped)), 'score': CS.stats(kept)}
    return base


def compare(shipped, copy, label):
    A = {(r['id'], r['scheme']): r for r in shipped if C.in_scope(r)}
    moved, summary = [], {}
    for s in SCHEMES:
        for kind in ('speech', 'other'):
            a = [r for r in shipped if r['scheme'] == s and r['kind'] == kind]
            b = [r for r in copy if r['scheme'] == s and r['kind'] == kind]
            if not a:
                continue
            mi = mo = 0
            for r in b:
                o = A.get((r['id'], s))
                if not o or not C.in_scope(r):
                    continue
                was, now = o['err'] <= 10, r['err'] <= 10
                if was != now:
                    mi += now; mo += was
                    moved.append({'copy': label, 'dataset': r['dataset'], 'scheme': SCHEMES[s], 'kind': kind, 'id': r['id'],
                                  'scenario': r['scenario'], 'ref': r['ref'], 'shipped': o['x'], 'copy_read': r['x'],
                                  'moved': 'in' if now else 'out', 'shipped_cause': C.fits(o)[0] if not was else None,
                                  'copy_cause': C.fits(r)[0] if not now else None,
                                  **{k: r.get(k) for k in ('file', 'onset_s', 'pair', 'set', 'talker')}})
            summary[f'{SCHEMES[s]} {kind}'] = {'shipped': score_set(a), 'copy': score_set(b), 'moved_in': mi, 'moved_out': mo}
    return summary, moved


# ---- 3. commit or dim ---------------------------------------------------------------------------------------------
SAFE = {'agree', 'a2_edge'}       # the lab: under a steady source or common-mode both schemes lock to the same wrong place


def choose_and_test(A, B, nameA, nameB, lab, exclude=()):
    keep = lambda rows: [r for r in rows if C.in_scope(r)]
    A, B = keep(A), keep(B)
    rule, info = _choose_excl(A, exclude) if exclude else RU.choose(A)
    res ={'chosen_on': nameA, 'rule': rule['name'], 'parts': rule['parts'], 'selection': info,
           nameA: RU.evaluate(rule, A), f'{nameB} (untouched)': RU.evaluate(rule, B),
           'no rule': {nameA: RU.evaluate({'name': 'all', 'parts': []}, A), nameB: RU.evaluate({'name': 'all', 'parts': []}, B)}}
    # the lab's coherent causes, where agreement and edge are known to fail
    coh = [r for r in lab if r['cause'].split(':')[0].replace('no_pause+', '') in ('steady_pink', 'steady_voice', 'common_mode')]
    wrong = [r for r in coh if r['err'] > 10]
    res['lab coherent causes'] = dict(RU.evaluate(rule, coh), wrong_reads_committed_pct=pct(sum(RU.commits(rule, r) for r in wrong), len(wrong)))
    return rule, res


def _choose_excl(A, exclude):
    singles = [r for r in RU.candidates(A) if r['parts'][0][0] not in exclude]
    best = None
    for r in singles:
        e = RU.evaluate(r, A)
        if e['committed_pct'] >= 100 * RU.MIN_COMMIT and (best is None or e['within10_committed_pct'] > best[1]['within10_committed_pct']):
            best = (r, e)
    pool = sorted(singles, key=lambda r: -(RU.evaluate(r, A)['within10_committed_pct'] or 0))[:40]
    best2 = None
    for a, b in combinations(pool, 2):
        if a['parts'][0][0] == b['parts'][0][0]:
            continue
        rr = RU.both(a, b)
        e = RU.evaluate(rr, A)
        if e['committed_pct'] >= 100 * RU.MIN_COMMIT and (best2 is None or e['within10_committed_pct'] > best2[1]['within10_committed_pct']):
            best2 = (rr, e)
    pick = best if best2 is None or best[1]['within10_committed_pct'] >= best2[1]['within10_committed_pct'] else best2
    return pick[0], {'best_single': best[1], 'best_pair': best2[1] if best2 else None, 'chosen': pick[1]}


def plot(curves, path):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(1, 2, figsize=(12, 6.2), sharey=False)
    for ax, (title, series) in zip(axes, curves.items()):
        for label, pts, style in series:
            if len(pts) == 1:
                ax.plot([pts[0][0]], [pts[0][1]], style, label=label, ms=8)
            else:
                ax.plot([p[0] for p in pts], [p[1] for p in pts], style, label=label, lw=1.6)
        ax.set_title(title, fontsize=10)
        ax.set_xlabel('reads committed (%)')
        ax.set_ylabel('committed reads within 10 deg (%)')
        ax.set_xlim(0, 102)
        ax.grid(alpha=0.3)
        ax.legend(fontsize=7, loc='upper center', bbox_to_anchor=(0.5, -0.14), ncol=1, frameon=False)
    fig.tight_layout()
    fig.savefig(path, dpi=130)


# ---- 4. range -----------------------------------------------------------------------------------------------------
def range_rows(starss_path, locata_path):
    out = []
    for l in C.opener(starss_path):
        r = json.loads(l)
        if r['kind'] != 'speech' or not r['dist_m']:
            continue
        a, e = math.radians(r['az']), math.radians(r['el'])
        xyz = [math.cos(e) * math.cos(a) * r['dist_m'], math.cos(e) * math.sin(a) * r['dist_m'], math.sin(e) * r['dist_m']]
        out.append({'dataset': 'starss23', 'id': r['id'], 'who': (r['id'].split('/')[0], r['file'], r['cls'], r['src']),
                    'dist': r['dist_m'], 'xyz': xyz, 'cdr': r.get('cdr_db'),
                    'level': None if not r.get('five_ms_amp') else 20 * math.log10(r['five_ms_amp']), 'echo': r.get('echo_ms')})
    for l in C.opener(locata_path):
        r = json.loads(l)
        out.append({'dataset': 'locata', 'id': r['id'], 'who': (r['pair_mm'], r['who']), 'dist': r['dist_m'], 'xyz': r['head'],
                    'cdr': r.get('cdr_db'), 'level': r.get('level_db'), 'echo': r.get('echo_lag_ms')})
    return out


def range_score(rows, keep=None):
    """Ordering (same talker, distance ratio >= 1.25 / 1.5 / 2) and spread at one spot (within 0.3 m), per cue, per
    dataset. keep: an id set; only pairs whose two reads are both in it count."""
    res = {}
    for ds in ('starss23', 'locata'):
        g = defaultdict(list)
        for r in rows:
            if r['dataset'] == ds and (keep is None or r['id'] in keep):
                g[r['who']].append(r)
        res[ds] = {}
        for cue in ('cdr', 'level', 'echo'):            # each reads larger when nearer
            order = {1.25: [0, 0], 1.5: [0, 0], 2.0: [0, 0]}
            same, far = [], []
            for grp in g.values():
                for a, b in combinations(grp, 2):
                    va, vb = a[cue], b[cue]
                    if va is None or vb is None or not a['dist'] or not b['dist']:
                        continue
                    ratio = max(a['dist'], b['dist']) / min(a['dist'], b['dist'])
                    diff = va - vb
                    if ratio >= 1.25 and diff != 0:
                        right = (diff > 0) == (a['dist'] < b['dist'])   # nearer: more direct, louder, a longer floor-echo lag
                        for th in order:
                            if ratio >= th:
                                order[th][0] += right; order[th][1] += 1
                    if math.dist(a['xyz'], b['xyz']) <= 0.3:
                        same.append(abs(diff))
                    if ratio >= 2:
                        far.append(abs(diff))
            res[ds][cue] = {'ordering_pct': {f'{th}x': pct(k, n) for th, (k, n) in order.items()},
                            'pairs': {f'{th}x': n for th, (k, n) in order.items()},
                            'spread_one_spot': round(st.median(same), 2) if same else None, 'spot_pairs': len(same),
                            'step_at_2x': round(st.median(far), 2) if far else None}
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('out')
    ap.add_argument('--starss', nargs='+', type=kv)
    ap.add_argument('--locata-truth')
    ap.add_argument('--locata', nargs='+', type=kv)
    ap.add_argument('--lab')
    ap.add_argument('--range-starss')
    ap.add_argument('--range-locata')
    ap.add_argument('--final', default='shipped', help='the scheme set the rule is chosen for')
    a = ap.parse_args()
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    S = {k: C.starss_rows(v) for k, v in a.starss}
    L = {k: C.locata_rows(v, a.locata_truth) for k, v in a.locata}
    lab = C.lab_rows(a.lab)
    res = {'reads': {'starss23': {k: len(v) // 2 for k, v in S.items()}, 'locata': {k: len(v) // 2 for k, v in L.items()}, 'lab': len(lab) // 2}}

    res['1_attribution'] = {'starss23': attribute(S['shipped']), 'locata': attribute(L['shipped']), 'lab_check': lab_check(lab)}
    print('attribution done', file=sys.stderr)

    res['2_fix'], moved = {}, []
    for k in S:
        if k == 'shipped':
            continue
        sm, mv = compare(S['shipped'], S[k], k); res['2_fix'][f'starss23 {k}'] = sm; moved += mv
        if k in L:
            sm, mv = compare(L['shipped'], L[k], k); res['2_fix'][f'locata {k}'] = sm; moved += mv
            res['2_fix'][f'attribution locata {k}'] = attribute(L[k])
        res['2_fix'][f'attribution starss23 {k}'] = attribute(S[k])
    res['2_fix']['shipped'] = {'starss23': {f'{SCHEMES[s]} {kind}': score_set([r for r in S['shipped'] if r['scheme'] == s and r['kind'] == kind])
                                            for s in SCHEMES for kind in ('speech', 'other')},
                               'locata': {f'{SCHEMES[s]} {mm} mm': score_set([r for r in L['shipped'] if r['scheme'] == s and r['pair_mm'] == mm])
                                          for s in SCHEMES for mm in (160, 80)}}
    for k in L:
        res['2_fix'].setdefault('locata_by_pair', {})[k] = {f'{SCHEMES[s]} {mm} mm': score_set([r for r in L[k] if r['scheme'] == s and r['pair_mm'] == mm])
                                                           for s in SCHEMES for mm in (160, 80)}
    with gzip.open(out / 'moved.jsonl.gz', 'wt') as fh:
        for m in moved:
            fh.write(json.dumps(m) + '\n')
    print('fix done', file=sys.stderr)

    fin = a.final
    gS = [r for r in S[fin] if r['scheme'] == 'gcc']
    gL = [r for r in L[fin] if r['scheme'] == 'gcc']
    glab = [r for r in lab if r['scheme'] == 'gcc']
    res['3_commit'] = {'scheme': f'GccPhat ({fin})'}
    rules = {}
    for tag, excl in (('any clue', ()), ('without agreement or edge', ('agree', 'a2_edge'))):
        r1, e1 = choose_and_test(gS, gL, 'starss23', 'locata', glab, excl)
        r2, e2 = choose_and_test(gL, gS, 'locata', 'starss23', glab, excl)
        res['3_commit'][tag] = {'chosen on starss23': e1, 'chosen on locata': e2}
        rules[tag] = (r1, r2)
        print('rule', tag, r1['name'], '|', r2['name'], file=sys.stderr)
    # THE GENERAL RULE: the margin threshold every chosen rule shares (0.203, STARSS23's decile), with the lab's pause rule
    # (dim a read within 10 deg of a pause read of share >= 0.5), which none of the searched rules has and the lab says
    # is needed against steady sources. Chosen on STARSS23 + the lab; LOCATA never touched it.
    gen = {'name': 'margin >= 0.203 and not on a pause read of share >= 0.5', 'parts': [('margin', '>=', 0.203), ('pause', 'pause', 0.5)]}
    inS = [r for r in gS if C.in_scope(r)]; inL = [r for r in gL if C.in_scope(r)]
    coh = [r for r in glab if r['cause'].split(':')[0].replace('no_pause+', '') in ('steady_pink', 'steady_voice', 'common_mode')]
    labo = [r for r in glab if r not in coh]
    res['3_commit']['general rule'] = {
        'rule': gen['name'], 'starss23': RU.evaluate(gen, inS), 'locata (untouched)': RU.evaluate(gen, inL),
        'lab coherent causes': dict(RU.evaluate(gen, coh), wrong_reads_committed_pct=pct(sum(RU.commits(gen, r) for r in coh if r['err'] > 10), sum(r['err'] > 10 for r in coh))),
        'lab, everything else': RU.evaluate(gen, labo),
        'by kind, starss23': {k: RU.evaluate(gen, [r for r in inS if r['kind'] == k]) for k in ('speech', 'other')},
        'Angle2 (final), same rule on its own reads': {'starss23': RU.evaluate(gen, [r for r in S[fin] if r['scheme'] == 'a2' and C.in_scope(r)]),
                                                       'locata': RU.evaluate(gen, [r for r in L[fin] if r['scheme'] == 'a2' and C.in_scope(r)])}}
    rules['general'] = (gen, gen)
    # the plot: each dataset, the chosen rules' clues swept, plus the chosen points
    curves = {}
    for nameX, rows in (('STARSS23', gS), ('LOCATA', gL)):
        rows = [r for r in rows if C.in_scope(r)]
        series = []
        for clue, op, style in (('margin', '>=', '-'), ('share', '>=', '--'), ('snr_hf1', '>=', '-.')):
            series.append((f'{clue} {op} t, swept', RU.curve(clue, op, rows), style))
        sub = [r for r in rows if RU.commits({'name': '', 'parts': [('pause', 'pause', 0.5)]}, r)]
        series.append(('margin >= t swept, and not on a pause read of share >= 0.5',
                       [(p[0] * len(sub) / len(rows), p[1], p[2]) for p in RU.curve('margin', '>=', sub)], 'k-'))
        for tag, (r1, r2) in rules.items():
            if tag == 'general':
                e = RU.evaluate(r1, rows)
                series.append((f'the general rule: {r1["name"]}', [(e['committed_pct'], e['within10_committed_pct'])], 'r*'))
                continue
            for who, rr in (('chosen on STARSS23', r1), ('chosen on LOCATA', r2)):
                e = RU.evaluate(rr, rows)
                series.append((f'{who} ({tag}): {rr["name"]}', [(e['committed_pct'], e['within10_committed_pct'])], 'o' if 'STARSS' in who else 's'))
        e = RU.evaluate({'name': 'all', 'parts': []}, rows)
        series.append(('commit everything', [(100.0, e['within10_committed_pct'])], 'k^'))
        curves[f'{nameX}: GccPhat ({fin}), every onset in scope'] = series
    plot(curves, out / 'commit_curves.png')
    print('rules done', file=sys.stderr)

    rr = range_rows(a.range_starss, a.range_locata)
    res['4_range'] = {'all reads': range_score(rr)}
    for tag, (r1, r2) in rules.items():
        com = {r['id'] for r in gS + gL if C.in_scope(r) and RU.commits(r1, r)}
        dim = {r['id'] for r in gS + gL if C.in_scope(r) and not RU.commits(r1, r)}
        # LOCATA range ids carry the pair spacing like the reads; STARSS range ids are the reads' ids
        res['4_range'][f'committed by the rule chosen on STARSS23 ({tag})'] = range_score(rr, com)
        res['4_range'][f'dimmed by it ({tag})'] = range_score(rr, dim)
    (out / 'summary.json').write_text(json.dumps(res, indent=1))
    print('done', file=sys.stderr)


if __name__ == '__main__':
    main()
