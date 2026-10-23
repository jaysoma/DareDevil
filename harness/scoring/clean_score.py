#!/usr/bin/env python3
"""Jay's scoring rule (2026-10-22): score the working machinery, set the outliers aside to study.

  "angles at +75 to +90 and -75 to -90, drop them off the analysis ... drop outliers that deviate stupidly ... If an
   entire scenario had deviations over 20-30%, drop the whole scenario. Medians ONLY make sense once we discard these
   values. Outliers are meant to be studied, not weight down percentage of working machinery."

Deviation in percent is read against the 90 deg half-plane (1% = 0.9 deg), so:
  1. SCOPE       |truth| <= 75 deg; everything else is off the analysis.
  2. READ        a read off by more than READ_OUT (40% = 36 deg) is an outlier: set aside, catalogued.
  3. SCENARIO    one physical setup heard repeatedly (STARSS: a room through one capsule pair; dEchorate: one wall
                 configuration, source, array and spacing). After step 2, a scenario whose remaining reads average more
                 than SCEN_MEAN (25% = 22.5 deg) off, or that lost more than SCEN_OUT_SHARE of its reads to step 2, is
                 dropped whole and catalogued.
  4. SCORE       mean and median |error|, share within 10 deg and signed lean, on what is left -- always next to how much
                 was set aside, since a scheme that drops more and scores better is not better.

Each scheme is cleaned on its own; the 'common' line scores only reads both schemes kept, for a like-for-like comparison.

usage: clean_score.py <repo root> <out dir>
"""
import gzip
import json
import math
import statistics as st
import sys
from collections import defaultdict
from pathlib import Path

SCOPE = 75.0
READ_OUT = 0.40 * 90
SCEN_MEAN = 0.25 * 90
SCEN_OUT_SHARE = 0.5
BANDS = ((0, 15), (15, 30), (30, 45), (45, 60), (60, 75))
C = 343.0


def starss(root):
    """(scheme -> rows) for STARSS23: GccPhat, Angle2 after the fix, Angle2 before it."""
    out = defaultdict(list)
    for p in ('12', '13', '14', '23', '24', '34'):
        truth = [json.loads(l) for l in open(root / f'results/starss23/truth/truth_{p}.jsonl')]
        after = [json.loads(l) for l in open(root / f'results/starss23/after_angle2_fix/preds_{p}.jsonl')]
        before = [json.loads(l) for l in open(root / f'results/starss23/preds_{p}.jsonl')]
        for t, a, b in zip(truth, after, before):
            assert t['file'] == a['file'] == b['file'] and t['onset_s'] == a['onset_s'] == b['onset_s']
            base = dict(id=f"{p}/{t['idx']}", scenario=f"{t['room']} pair {p}", truth=t['truth_lateral'],
                        ctx={'file': t['file'], 'onset_s': t['onset_s'], 'src': t['src'], 'dist_cm': t['dist_cm'],
                             'el': t['el']})
            if a.get('gcc'):
                out['GccPhat'].append(dict(base, read=a['gcc'][0], others=a['gcc'][1:]))
            if a.get('a2'):
                out['Angle2 (fixed)'].append(dict(base, read=a['a2'][0], others=[a['a2'][1]], edge=a.get('a2_edge')))
            if b.get('a2'):
                out['Angle2 (before fix)'].append(dict(base, read=b['a2'][0], others=[b['a2'][1]]))
    return out


def dechorate(root, truth_kind):
    """(scheme -> rows) for dEchorate. truth_kind 'measured' (the RIRs' own direct-path delay) or 'geometry'."""
    out = defaultdict(list)
    truth = {}
    with gzip.open(root / 'results/dechorate/truth.jsonl.gz', 'rt') as fh:
        for l in fh:
            t = json.loads(l)
            truth[t['id']] = t
    with gzip.open(root / 'results/dechorate/preds.jsonl.gz', 'rt') as fh:
        for l in fh:
            q = json.loads(l)
            t = truth[q['id']]
            if truth_kind == 'measured':
                s = -t['rir_tau_ms'] / 1000 * C / t['baseline_m']
                deg = math.degrees(math.asin(max(-1.0, min(1.0, s))))
            else:
                deg = t['truth_deg']
            base = dict(id=t['id'], scenario=f"{t['room']} src{t['src']} array{t['array']} {t['spacing_mm']}mm",
                        truth=round(deg, 2), echoes=[e['deg'] for e in t['echoes'] if e['reflective']],
                        ctx={'room': t['room'], 'src': t['src'], 'array': t['array'], 'spacing_mm': t['spacing_mm'],
                             'dist_m': t['dist_m']})
            if q.get('gcc'):
                out['GccPhat'].append(dict(base, read=q['gcc'][0], others=q['gcc'][1:]))
            if q.get('a2'):
                out['Angle2 (before fix)'].append(dict(base, read=q['a2'][0], others=[q['a2'][1]]))
    return out


def kind_of(r):
    """What an outlier looks like, so the catalogue can be studied by kind."""
    t, x = r['truth'], r['read']
    if abs(x) >= 85:
        return 'pinned at end-fire'
    if abs(t) >= 10 and abs(x + t) <= 10:
        return 'mirror (sign flipped)'
    if any(abs(e - x) <= 10 for e in r.get('echoes', [])):
        return 'on a reflective surface\'s echo'
    if any(o is not None and abs(o - t) <= 10 for o in r.get('others', [])):
        return 'truth was its 2nd/3rd direction'
    return 'other'


def clean(rows):
    scoped = [r for r in rows if abs(r['truth']) <= SCOPE]
    for r in scoped:
        r['err'] = abs(r['read'] - r['truth'])
    by = defaultdict(list)
    for r in scoped:
        by[r['scenario']].append(r)
    kept, read_out, scen_out, scen_rows = [], [], [], []
    for sc, rs in by.items():
        good = [r for r in rs if r['err'] <= READ_OUT]
        bad = [r for r in rs if r['err'] > READ_OUT]
        mean_good = st.mean(r['err'] for r in good) if good else float('inf')
        share_bad = len(bad) / len(rs)
        dropped = mean_good > SCEN_MEAN or share_bad > SCEN_OUT_SHARE
        scen_rows.append({'scenario': sc, 'reads': len(rs), 'read_outliers': len(bad),
                          'mean_err_after_outliers': round(mean_good, 1) if good else None, 'dropped': dropped,
                          'why': ('mean over 22.5 deg' if mean_good > SCEN_MEAN else 'over half its reads were outliers')
                          if dropped else None})
        for r in bad:
            read_out.append(dict(r, reason='read off by more than 36 deg', kind=kind_of(r)))
        if dropped:
            for r in good:
                scen_out.append(dict(r, reason='scenario dropped', kind=kind_of(r) if r['err'] > 10 else 'within 10 deg'))
        else:
            kept.extend(good)
    return scoped, kept, read_out, scen_out, scen_rows


def stats(kept):
    if not kept:
        return None
    e = [r['err'] for r in kept]
    side = lambda r: 1 if r['truth'] > 0 else -1
    lean = {}
    for lo, hi in BANDS:
        v = [(r['read'] - r['truth']) * side(r) for r in kept if lo <= abs(r['truth']) < hi and abs(r['truth']) >= 1]
        lean[f'{lo}-{hi}'] = {'n': len(v), 'mean': round(st.mean(v), 1) if v else None}
    return {'n': len(kept), 'mean_err': round(st.mean(e), 1), 'median_err': round(st.median(e), 1),
            'within_10_pct': round(100 * sum(x <= 10 for x in e) / len(e), 1), 'lean_mean_by_band': lean}


def run(name, data, out):
    res, catalogue, scen_tables = {}, [], {}
    kept_ids = {}
    for scheme, rows in data.items():
        scoped, kept, read_out, scen_out, scen_rows = clean([dict(r) for r in rows])
        n_scen = len(scen_rows)
        n_drop = sum(s['dropped'] for s in scen_rows)
        res[scheme] = {
            'reads_total': len(rows), 'in_scope': len(scoped),
            'read_outliers': len(read_out), 'read_outliers_pct': round(100 * len(read_out) / len(scoped), 1),
            'scenarios': n_scen, 'scenarios_dropped': n_drop,
            'reads_in_dropped_scenarios': len(scen_out),
            'kept': len(kept), 'kept_pct': round(100 * len(kept) / len(scoped), 1),
            'score': stats(kept),
            'outlier_kinds': {k: sum(1 for r in read_out if r['kind'] == k) for k in sorted({r['kind'] for r in read_out})}}
        kept_ids[scheme] = {r['id']: r for r in kept}
        for r in read_out + scen_out:
            catalogue.append({'dataset': name, 'scheme': scheme, 'id': r['id'], 'scenario': r['scenario'],
                              'truth': r['truth'], 'read': round(r['read'], 2), 'err': round(r['err'], 1),
                              'others': [None if o is None else round(o, 1) for o in r.get('others', [])],
                              'edge': r.get('edge'), 'reason': r['reason'], 'kind': r['kind'], **r['ctx']})
        scen_tables[scheme] = sorted(scen_rows, key=lambda s: (not s['dropped'], s['scenario']))
    schemes = list(data)
    if len(schemes) >= 2:
        a, b = schemes[0], schemes[1]
        common = kept_ids[a].keys() & kept_ids[b].keys()
        res['common'] = {'schemes': [a, b], 'reads': len(common),
                         a: stats([kept_ids[a][i] for i in common]), b: stats([kept_ids[b][i] for i in common])}
    (out / f'{name}_summary.json').write_text(json.dumps(res, indent=1))
    (out / f'{name}_scenarios.json').write_text(json.dumps(scen_tables, indent=1))
    with open(out / f'{name}_outliers.jsonl', 'w') as fh:
        for r in catalogue:
            fh.write(json.dumps(r) + '\n')
    return res


def main():
    root, out = Path(sys.argv[1]), Path(sys.argv[2])
    out.mkdir(parents=True, exist_ok=True)
    allres = {'rule': {'scope_deg': SCOPE, 'read_outlier_deg': READ_OUT, 'scenario_mean_deg': SCEN_MEAN,
                       'scenario_outlier_share': SCEN_OUT_SHARE}}
    allres['starss23'] = run('starss23', starss(root), out)
    allres['dechorate_measured'] = run('dechorate_measured', dechorate(root, 'measured'), out)
    allres['dechorate_geometry'] = run('dechorate_geometry', dechorate(root, 'geometry'), out)
    (out / 'summary.json').write_text(json.dumps(allres, indent=1))
    print(json.dumps(allres, indent=1))


if __name__ == '__main__':
    main()
