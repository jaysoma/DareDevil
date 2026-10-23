#!/usr/bin/env python3
"""Brief 13's tables from reads.jsonl.gz: wrong-lock rates, the cleaned score (Jay's rule), fingerprints, who falls
first, the class catalogue, and the aliasing map.

    python3 analyze.py reads.jsonl.gz OUT_DIR    -> OUT_DIR/summary.json, tables.md, catalogue.jsonl.gz

Fingerprint: every cause-level read is paired with the SAME cut (placement, angle, onset) at baseline, and each clue's
change is the median over pairs (rates: the change in percentage points). So a clue moves only because the cause did.
Who falls first: within a cause, the mildest level at which a scheme's share of reads off by more than 10 deg rises
FALL_PP points over its baseline at that placement.
"""
import gzip
import json
import statistics as st
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scoring'))
import clean_score as cs                                      # noqa: E402

PLACEMENTS = ['free157', 'free69', 'room000000', 'room011111']
SCHEMES = {'gcc': 'GccPhat', 'a2': 'Angle2'}
ABANDS = [(0, 30), (30, 60), (60, 76)]
FALL_PP = 5.0
FAMILIES = {   # cause family -> levels from mildest to most severe
    'steady_pink': ['steady_pink:-30', 'steady_pink:-20', 'steady_pink:-10', 'steady_pink:0'],
    'steady_voice': ['steady_voice:-30', 'steady_voice:-20', 'steady_voice:-10', 'steady_voice:0'],
    'common_mode': ['common_mode:-30', 'common_mode:-20', 'common_mode:-10', 'common_mode:0'],
    'diffuse': ['diffuse:-30', 'diffuse:-20', 'diffuse:-10', 'diffuse:0'],
    'quiet': ['quiet:30', 'quiet:20', 'quiet:10', 'quiet:5'],
    'onset_late': ['onset_offset:+25', 'onset_offset:+50', 'onset_offset:+100', 'onset_offset:+150'],
    'onset_early': ['onset_offset:-25', 'onset_offset:-50'],
    'band_lo': ['band_lo:300', 'band_lo:1100', 'band_lo:2000'],
    'no_pause': ['no_pause'],
}
for _f in ('steady_pink', 'steady_voice', 'common_mode', 'diffuse'):          # cause 6 with a sound in the pause
    FAMILIES[f'no_pause+{_f}'] = [f'no_pause+{c}' for c in FAMILIES[_f]]
CAUSES = ['baseline'] + [c for v in FAMILIES.values() for c in v]
KINDS = ['mirror', 'endfire', 'pause_direction', 'other_source', 'zero_pull', 'aliasing', 'truth_in_2_3', 'drift',
         'other']


def read_of(r, s):
    if s == 'gcc':
        return r['gcc']['angles'][0] if r['gcc'] and r['gcc'].get('angles') else None
    return r['a2']['deg'] if r.get('a2') else None


def key(r):
    return r['id'].split('/', 2)[0], r['id'].rsplit('/', 2)[1], r['id'].rsplit('/', 1)[1]   # placement, angle, onset


def pct(v):
    return round(100 * sum(v) / len(v), 1) if v else None


def med(v):
    v = [x for x in v if x is not None]
    return round(st.median(v), 2) if v else None


def clues(r, s):
    g, a = r['gcc'] or {}, r.get('a2') or {}
    rd = read_of(r, s)
    w = g.get('widths') or [[None, None]]
    other = read_of(r, 'a2' if s == 'gcc' else 'gcc')
    return {
        'gcc_share': (g.get('shares') or [None])[0],
        'gcc_width': (w[0][1] - w[0][0]) if w[0][0] is not None else None,
        'gcc_tie': bool(g.get('tie')),
        'gcc_votes': g.get('votes'),
        'gcc_early_vs_lock': (abs(g['track']['43'] - g['track']['lock'])
                              if g.get('track') and g['track'].get('43') is not None and g['track'].get('lock') is not None else None),
        'a2_edge': a.get('edge') if a else None,
        'a2_first_ms': a.get('first_ms') if a else None,
        'agree5': (abs(rd - other) <= 5) if rd is not None and other is not None else None,
        'pause_share': r.get('pause_share'),
        'snr_mf': r['snr_db']['mf'], 'snr_hf1': r['snr_db']['hf1'], 'snr_hf2': r['snr_db']['hf2'],
    }


RATE_CLUES = ('gcc_tie', 'a2_edge', 'agree5')


def main():
    reads, out = sys.argv[1], Path(sys.argv[2])
    out.mkdir(parents=True, exist_ok=True)
    R = defaultdict(list)                      # (cause, placement) -> records
    with gzip.open(reads, 'rt') as fh:
        for l in fh:
            r = json.loads(l)
            R[r['cause'], r['placement']].append(r)
    base = {key(r): r for p in PLACEMENTS for r in R['baseline', p]}
    res = {'rates': {}, 'clean': {}, 'fingerprint': {}, 'falls_first': {}, 'kinds': {}, 'wrong_vs_right': {}}
    catalogue = []
    for cause in CAUSES:
        for p in PLACEMENTS:
            rows = R.get((cause, p), [])
            if not rows:
                continue
            for s in SCHEMES:
                if cause.startswith('no_pause') and s == 'a2':
                    continue
                got = [(r, read_of(r, s)) for r in rows]
                got = [(r, x) for r, x in got if x is not None]
                if not got:
                    continue
                err = [(r, abs(x - r['truth']['deg'])) for r, x in got]
                k = f'{cause}|{p}|{s}'
                res['rates'][k] = {
                    'n': len(rows), 'read': len(got), 'no_read_pct': round(100 * (1 - len(got) / len(rows)), 1),
                    'over10_pct': pct([e > 10 for _, e in err]), 'over36_pct': pct([e > 36 for _, e in err]),
                    'median_err': med([e for _, e in err]),
                    'over10_by_band': {f'{a}-{b}': pct([e > 10 for r, e in err if a <= abs(r['truth']['deg']) < b])
                                       for a, b in ABANDS},
                    'over36_by_band': {f'{a}-{b}': pct([e > 36 for r, e in err if a <= abs(r['truth']['deg']) < b])
                                       for a, b in ABANDS}}
                # Jay's rule: scenario = this placement x cause x talker angle (its 12 onsets)
                rows_c = [{'id': r['id'], 'scenario': r['scenario'], 'truth': r['truth']['deg'], 'read': x,
                           'others': [], 'ctx': {}} for r, x in got]
                scoped, kept, rout, sout, scen = cs.clean(rows_c)
                res['clean'][k] = {'in_scope': len(scoped), 'read_outliers': len(rout),
                                   'scenarios': len(scen), 'scenarios_dropped': sum(x['dropped'] for x in scen),
                                   'kept_pct': round(100 * len(kept) / len(scoped), 1) if scoped else None,
                                   'score': cs.stats(kept)}
                # kinds among wrong reads, with examples
                kc = Counter()
                for r, x in got:
                    for kd in r['classes'].get(s, []):
                        kc[kd] += 1
                        if kd != 'over36':
                            catalogue.append({'scheme': SCHEMES[s], 'kind': kd, 'cause': cause, 'placement': p,
                                              'id': r['id'], 'truth': r['truth']['deg'], 'read': round(x, 1),
                                              'over36': 'over36' in r['classes'][s], 'pause_deg': r.get('pause_deg'),
                                              'clean': r['clean'], 'combo': r['combo']})
                wrong = sum(1 for _, e in err if e > 10)
                if cause == 'baseline' or cause.startswith('band_lo'):
                    am = defaultdict(lambda: [0, 0])
                    for r, e in err:
                        a = am[int(r['truth']['deg'])]
                        a[0] += e > 10
                        a[1] += 'aliasing' in r['classes'].get(s, [])
                    res.setdefault('alias_map', {})[k] = {str(t): v for t, v in sorted(am.items())}
                res['kinds'][k] = {'wrong': wrong, **{kd: kc.get(kd, 0) for kd in KINDS + ['over36']}}
                # wrong vs right: clue medians
                cw = [clues(r, s) for r, e in err if e > 10]
                cr = [clues(r, s) for r, e in err if e <= 10]
                res['wrong_vs_right'][k] = {c: [pct([x[c] for x in grp if x[c] is not None]) if c in RATE_CLUES
                                                else med([x[c] for x in grp]) for grp in (cr, cw)]
                                            for c in (cw or cr or [{}])[0]}
                # fingerprint against the same cut at baseline
                if cause != 'baseline':
                    fp = defaultdict(list)
                    for r, _ in got:
                        b = base.get(key(r))
                        if not b or read_of(b, s) is None:
                            continue
                        c1, c0 = clues(r, s), clues(b, s)
                        for c in c1:
                            if c1[c] is None or c0[c] is None:
                                continue
                            fp[c].append((float(c1[c]) - float(c0[c])) * (100 if c in RATE_CLUES else 1))
                    res['fingerprint'][k] = {c: (round(st.mean(v), 1) if c in RATE_CLUES else round(st.median(v), 2))
                                             for c, v in fp.items()}
    # absolute clues per cause x placement: what the read knew, scheme-free
    res['clues_abs'] = {}
    for (cause, p), rows in R.items():
        cl = [clues(r, 'gcc') for r in rows]
        pd = [(r.get('pause_deg'), r['truth']) for r in rows]
        res['clues_abs'][f'{cause}|{p}'] = {
            **{c: (pct([x[c] for x in cl if x[c] is not None]) if c in RATE_CLUES else med([x[c] for x in cl]))
               for c in cl[0]},
            'pause_near_talker': pct([d is not None and abs(d - t['deg']) <= 10 for d, t in pd]),
            'pause_near_other': pct([d is not None and any(abs(d - o['deg']) <= 10 for o in t['others']) for d, t in pd]),
            'pause_near_0': pct([d is not None and abs(d) < 6 for d, t in pd])}
    # who falls first
    for fam, levels in FAMILIES.items():
        for p in PLACEMENTS:
            for s in SCHEMES:
                b = res['rates'].get(f'baseline|{p}|{s}')
                if not b:
                    continue
                first = None
                for lv in levels:
                    x = res['rates'].get(f'{lv}|{p}|{s}')
                    if x and x['over10_pct'] is not None and x['over10_pct'] - b['over10_pct'] >= FALL_PP:
                        first = lv
                        break
                res['falls_first'][f'{fam}|{p}|{s}'] = first
    (out / 'summary.json').write_text(json.dumps(res, indent=1))
    with gzip.open(out / 'catalogue.jsonl.gz', 'wt') as fh:
        for c in catalogue:
            fh.write(json.dumps(c) + '\n')
    tables(res, catalogue, out)


def tbl(head, rows):
    o = ['| ' + ' | '.join(map(str, head)) + ' |', '|' + '---|' * len(head)]
    return '\n'.join(o + ['| ' + ' | '.join('' if v is None else str(v) for v in r) + ' |' for r in rows])


def tables(res, catalogue, out):
    L = []
    P = PLACEMENTS
    for s, name in SCHEMES.items():
        L.append(f'\n## {name}: share of reads off by more than 10 deg / more than 36 deg, %\n')
        rows = []
        for c in CAUSES:
            row = [c]
            for p in P:
                x = res['rates'].get(f'{c}|{p}|{s}')
                row.append(f"{x['over10_pct']} / {x['over36_pct']}" if x else '')
            rows.append(row)
        L.append(tbl(['cause'] + P, rows))
        L.append(f'\n## {name}: off by more than 10 deg, by |truth| band (0-30 / 30-60 / 60-75), %\n')
        rows = []
        for c in CAUSES:
            row = [c]
            for p in P:
                x = res['rates'].get(f'{c}|{p}|{s}')
                row.append(' / '.join(str(x['over10_by_band'][f'{a}-{b}']) for a, b in ABANDS) if x else '')
            rows.append(row)
        L.append(tbl(['cause'] + P, rows))
        L.append(f'\n## {name}: cleaned score (Jay\'s rule): kept %, mean / median error of kept, within 10 deg of kept\n')
        rows = []
        for c in CAUSES:
            row = [c]
            for p in P:
                x = res['clean'].get(f'{c}|{p}|{s}')
                if not x or not x['score']:
                    row.append('' if not x else f"kept {x['kept_pct']}%")
                    continue
                sc = x['score']
                row.append(f"{x['kept_pct']}%: {sc['mean_err']} / {sc['median_err']}, {sc['within_10_pct']}% "
                           f"({x['read_outliers']} out, {x['scenarios_dropped']} sc.)")
            rows.append(row)
        L.append(tbl(['cause'] + P, rows))
    L.append('\n## Cause 6 with a sound in the pause: GccPhat off by >10 deg / >36 deg, %, with the pause weighting -> without\n')
    rows = []
    for fam in ('steady_pink', 'steady_voice', 'common_mode', 'diffuse'):
        for c in FAMILIES[fam]:
            row = [c]
            for p in P:
                a, b = res['rates'].get(f'{c}|{p}|gcc'), res['rates'].get(f'no_pause+{c}|{p}|gcc')
                row.append(f"{a['over10_pct']}/{a['over36_pct']} -> {b['over10_pct']}/{b['over36_pct']}" if a and b else '')
            rows.append(row)
    L.append(tbl(['cause'] + P, rows))
    L.append('\n## Who falls first: the mildest level at which reads off by >10 deg rise 5 points over baseline\n')
    rows = []
    for fam in FAMILIES:
        row = [fam]
        for p in P:
            row.append(' / '.join(str(res['falls_first'].get(f'{fam}|{p}|{s}') or '-').split(':')[-1] for s in SCHEMES))
        rows.append(row)
    L.append('(GccPhat / Angle2; "-" = never within the levels run)\n')
    L.append(tbl(['cause'] + P, rows))
    clist = ['gcc_share', 'gcc_width', 'gcc_tie', 'gcc_votes', 'gcc_early_vs_lock', 'a2_edge', 'a2_first_ms', 'agree5',
             'pause_share', 'snr_mf', 'snr_hf1', 'snr_hf2']
    L.append('\n## Fingerprint: each clue\'s change against the same cut at baseline, median over placements\n')
    L.append('(per placement, the median change over cuts; tie, edge and agreement as the change in % points. Clues are '
             'properties of the cut and run, so this is GccPhat\'s read set; Angle2\'s is the same where both read)\n')
    rows = []
    for c in CAUSES[1:]:
        ks = [f'{c}|{p}|gcc' for p in P if f'{c}|{p}|gcc' in res['fingerprint']]
        if not ks:
            continue
        row = [c]
        for cl in clist:
            v = [res['fingerprint'][k].get(cl) for k in ks]
            v = [x for x in v if x is not None]
            row.append(round(st.median(v), 2) if v else None)
        rows.append(row)
    L.append(tbl(['cause'] + clist, rows))
    alist = clist + ['pause_near_talker', 'pause_near_other', 'pause_near_0']
    L.append('\n## Clues as they stand (not changes), median over placements of each placement\'s median / rate\n')
    rows = []
    for c in CAUSES:
        ks = [f'{c}|{p}' for p in P if f'{c}|{p}' in res['clues_abs']]
        if not ks:
            continue
        row = [c]
        for cl in alist:
            v = [res['clues_abs'][k].get(cl) for k in ks]
            v = [x for x in v if x is not None]
            row.append(round(st.median(v), 2) if v else None)
        rows.append(row)
    L.append(tbl(['cause'] + alist, rows))
    wl = ['gcc_share', 'gcc_width', 'gcc_tie', 'agree5', 'a2_edge', 'pause_share']
    for s, name in SCHEMES.items():
        L.append(f'\n## {name}: clues on its right reads -> its wrong reads (>10 deg), all placements pooled by median\n')
        rows = []
        for c in CAUSES:
            ks = [f'{c}|{p}|{s}' for p in P if f'{c}|{p}|{s}' in res['wrong_vs_right']]
            if not ks:
                continue
            row = [c]
            for cl in wl:
                pr = [res['wrong_vs_right'][k].get(cl, [None, None]) for k in ks]
                a = [x[0] for x in pr if x[0] is not None]
                b = [x[1] for x in pr if x[1] is not None]
                row.append(f"{round(st.median(a), 2) if a else '-'} -> {round(st.median(b), 2) if b else '-'}")
            rows.append(row)
        L.append(tbl(['cause'] + wl, rows))
    for s, name in SCHEMES.items():
        L.append(f'\n## Kinds of {name}\'s wrong reads (>10 deg), all placements: count of wrong reads carrying each kind\n')
        rows = []
        for c in CAUSES:
            ks = [f'{c}|{p}|{s}' for p in P if f'{c}|{p}|{s}' in res['kinds']]
            if not ks:
                continue
            tot = {kd: sum(res['kinds'][k][kd] for k in ks) for kd in ['wrong'] + KINDS + ['over36']}
            rows.append([c] + [tot[kd] for kd in ['wrong'] + KINDS + ['over36']])
        L.append(tbl(['cause', 'wrong'] + KINDS + ['over36'], rows))
    L.append('\n## Aliasing map (cause 4, no noise): talker angles with reads off by >10 deg, as wrong/aliasing-class of 12\n')
    rows = []
    for k, am in sorted(res.get('alias_map', {}).items()):
        bad = [f"{t}: {v[0]}/{v[1]}" for t, v in am.items() if v[0]]
        rows.append(k.split('|') + ['; '.join(bad) or 'none'])
    L.append(tbl(['run', 'placement', 'scheme', 'angles (wrong/aliasing)'], rows))
    # three examples per (scheme, cause, kind)
    L.append('\n## Examples to listen to: three per scheme, cause and kind (id = placement/cause/angle/onset)\n')
    ex = defaultdict(list)
    for c in catalogue:
        kk = (c['scheme'], c['cause'], c['kind'])
        if len(ex[kk]) < 3:
            ex[kk].append(f"{c['id']} read {c['read']} ({c['clean']})")
    rows = [[a, b, k, '; '.join(v)] for (a, b, k), v in sorted(ex.items())]
    L.append(tbl(['scheme', 'cause', 'kind', 'examples'], rows))
    (out / 'tables.md').write_text('\n'.join(L) + '\n')


if __name__ == '__main__':
    main()
