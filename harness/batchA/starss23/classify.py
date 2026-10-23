#!/usr/bin/env python3
"""Batch A on STARSS23, step 2: the shared record per read, its wrong-read classes, the score under Jay's rule.

Inputs (work dir): truth_XY.jsonl (cut_all.py), raw_XY.jsonl (runner.mjs), sphere_grid_reads.jsonl (sphere_grid.py
through runner.mjs). Outputs (out dir):
  reads.jsonl       one line per read, in the shared batch A format (cloud_sessions.md). Top-level `classes` are
                    GccPhat's angle 1's; Angle2's are in a2.classes. Extra fields are additions, never renames.
  truth.jsonl       the truth alone, no audio.
  catalogue.jsonl   every read off by more than 10 deg, per scheme, with its classes: one line each, to listen to.
  summary.json      the score under the rule, the class tables, overlaps, examples, and the lean comparison.

THE REFERENCE. The array is a rigid sphere, which reads every bearing wider than the geometric lateral angle (+19 deg
at 45-60 for GccPhat). Brief 9: don't call that wrong. So a read is judged against what the same scheme reads from the
same direction through the sphere alone (sphere_grid.py, interpolated): truth.sphere_deg.<scheme>. The geometric
lateral angle stays in truth.deg, and the rule's score is given against both.

THE CLASSES, for a read off its reference by more than 10 deg (moderate) or 36 deg (outlier):
  mirror                   |ref| >= 10 and the read within 10 deg of -ref
  end-fire pin             |read| >= 85
  pause direction          within 10 deg of GccPhat's read of the 0.5 s before the onset, that read itself more than
                           10 deg from the reference (so it is a different direction, not the talker's own last word)
  another labelled source  within 10 deg of another source active from 0.5 s before to 0.5 s after the onset (its own
                           sphere reference), that source more than 10 deg from the reference
  0 deg pull               |read| < 6 while |ref| > 15
  aliasing partner         the read's delay and the reference's differ by one period of a frequency f with
                           c/2d <= f <= 8 kHz, and f's third-octave band holds >= ALIAS_SHARE of the voice's power
                           over the pause
  truth was angle 2 or 3   GccPhat's angle 2 or 3 (Angle2: its second family) within 10 deg of the reference
  drift                    GccPhat only: its first draw (43 ms) within 10 deg of the reference, its lock not
  facing                   never: STARSS has no facing truth
  other                    none of these
usage: classify.py <work dir> <out dir>
"""
import bisect
import json
import math
import random
import statistics as st
import sys
from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'scoring'))
import clean_score as CS                                                   # noqa: E402

C = 343.0
PAIRS = __import__('os').environ.get('PAIRS', '12 13 14 23 24 34').split()
OK, OUT = 10.0, 36.0
ALIAS_SHARE = 0.05
THIRD_EDGES = 2 ** (1 / 6)
BANDS = ((0, 15), (15, 30), (30, 45), (45, 60), (60, 90))
CLASSES = ['mirror', 'end-fire pin', 'pause direction', 'another labelled source', '0 deg pull', 'aliasing partner',
           'truth was angle 2 or 3', 'drift', 'facing', 'other']


def load_grid(path):
    g = defaultdict(dict)
    for l in open(path):
        r = json.loads(l)
        p, az, el = r['id'].split('/')
        gcc = r['gcc']['angles'][0] if r.get('gcc') and r['gcc']['angles'] else None
        a2 = r['a2']['deg'] if r.get('a2') else None
        g[p][(int(az), int(el))] = {'gcc': gcc, 'a2': a2}
    return g


def interp(grid, az, el, scheme):
    """Bilinear in azimuth (wrapping, 5 deg) and elevation (-80..40, 10 deg) of the scheme's sphere-only read."""
    az = ((az + 180) % 360) - 180
    a0 = math.floor(az / 5) * 5
    a1 = a0 + 5 if a0 + 5 < 180 else -180
    el = max(-80, min(40, el))
    e0 = min(30, math.floor((el + 80) / 10) * 10 - 80)
    e1 = e0 + 10
    wa, we = (az - a0) / 5, (el - e0) / 10
    pts = [(grid.get((a0, e0), {}).get(scheme), (1 - wa) * (1 - we)), (grid.get((a1, e0), {}).get(scheme), wa * (1 - we)),
           (grid.get((a0, e1), {}).get(scheme), (1 - wa) * we), (grid.get((a1, e1), {}).get(scheme), wa * we)]
    pts = [(v, w) for v, w in pts if v is not None]
    if not pts or sum(w for _, w in pts) <= 0:
        return None
    return round(sum(v * w for v, w in pts) / sum(w for _, w in pts), 2)


def jsnum(v):
    """A number as JavaScript prints it (runner.mjs builds the ids): 5.0 -> '5'."""
    return str(int(v)) if float(v).is_integer() else repr(float(v))


def tau(deg, d):
    return -math.sin(math.radians(deg)) * d / C


def classify(x, ref, d, others, pause, alts, early, bands):
    """The classes of one wrong read x against its reference ref (pair spacing d metres)."""
    cl = []
    if abs(ref) >= 10 and abs(x + ref) <= 10:
        cl.append('mirror')
    if abs(x) >= 85:
        cl.append('end-fire pin')
    if pause is not None and abs(x - pause) <= 10 and abs(pause - ref) > 10:
        cl.append('pause direction')
    if any(o is not None and abs(x - o) <= 10 and abs(o - ref) > 10 for o in others):
        cl.append('another labelled source')
    if abs(x) < 6 and abs(ref) > 15:
        cl.append('0 deg pull')
    dt = abs(tau(x, d) - tau(ref, d))
    if dt > 0 and bands:
        f = 1 / dt
        if C / (2 * d) <= f <= 8000:
            for fc, share in bands:
                if share is not None and fc / THIRD_EDGES <= f < fc * THIRD_EDGES and share >= ALIAS_SHARE:
                    cl.append('aliasing partner')
                    break
    if any(a is not None and abs(a - ref) <= 10 for a in alts):
        cl.append('truth was angle 2 or 3')
    if early is not None and abs(early - ref) <= 10:
        cl.append('drift')
    return cl or ['other']


def severity(err):
    return 'ok' if err <= OK else 'moderate' if err <= OUT else 'outlier'


def lean_by_band(rows, key, ref_key):
    out = {}
    for lo, hi in BANDS:
        v = [(r[key] - r[ref_key]) * (1 if r[ref_key] > 0 else -1) for r in rows
             if r[key] is not None and r[ref_key] is not None and lo <= abs(r[ref_key]) < hi and abs(r[ref_key]) >= 1]
        out[f'{lo}-{hi}'] = {'n': len(v), 'median': round(st.median(v), 1) if v else None}
    return out


def main():
    W, OUTD = Path(sys.argv[1]), Path(sys.argv[2])
    OUTD.mkdir(parents=True, exist_ok=True)
    grid = load_grid(W / 'sphere_grid_reads.jsonl')
    recs = []
    for p in PAIRS:
        for lt, lr in zip(open(W / f'truth_{p}.jsonl'), open(W / f'raw_{p}.jsonl')):
            t, r = json.loads(lt), json.loads(lr)
            assert r['id'] == f"{p}/{t['file']}/{jsnum(t['onset_s'])}/{t['cls']}/{t['src']}", (r['id'], t['file'])
            d = t['baseline_m']
            sref = {s: interp(grid[p], t['az'], t['el'], s) for s in ('gcc', 'a2')}
            oth = [dict(deg=o['deg'], **{'class': o['class']}, before=o['before'], during=o['during'], az=o['az'], el=o['el'],
                        dist_m=None if o['dist_cm'] is None else round(o['dist_cm'] / 100, 2),
                        sphere_deg={s: interp(grid[p], o['az'], o['el'], s) for s in ('gcc', 'a2')}) for o in t['others']]
            truth = {'deg': t['truth_lateral'], 'dist_m': None if t['dist_cm'] is None else round(t['dist_cm'] / 100, 2),
                     'facing_deg': None, 'others': oth, 'sphere_deg': sref, 'az': t['az'], 'el': t['el'],
                     'lateral_span': t['lateral_span'], 'file': t['file'], 'room': t['room'], 'onset_s': t['onset_s'],
                     'cls': t['cls'], 'class': t['class'], 'kind': t['kind'], 'solo': t['solo'], 'src': t['src'], 'pair': p}
            rec = {'dataset': 'starss23', 'scenario': f"{t['room']} pair {p}", 'id': r['id'], 'pair_mm': r['pair_mm'],
                   'truth': truth, 'gcc': r.get('gcc'), 'a2': r.get('a2'), 'pause_deg': r.get('pause_deg'),
                   'pause_share': r.get('pause_share'), 'snr_db': r.get('snr_db'), 'voice_bands': r.get('voice_bands'),
                   'classes': [], 'cause': None}
            g = rec['gcc']
            if g and g['angles'] and sref['gcc'] is not None:
                x = g['angles'][0]
                g['err'] = round(abs(x - sref['gcc']), 2); g['err_geo'] = round(abs(x - truth['deg']), 2); g['severity'] = severity(g['err'])
                if g['err'] > OK:
                    rec['classes'] = classify(x, sref['gcc'], d, [o['sphere_deg']['gcc'] if o['sphere_deg']['gcc'] is not None else o['deg'] for o in oth],
                                              rec['pause_deg'], g['angles'][1:], g['track'].get('43'), rec['voice_bands'])
            a = rec['a2']
            if a and a['deg'] is not None and sref['a2'] is not None:
                x = a['deg']
                a['err'] = round(abs(x - sref['a2']), 2); a['err_geo'] = round(abs(x - truth['deg']), 2); a['severity'] = severity(a['err'])
                a['classes'] = classify(x, sref['a2'], d, [o['sphere_deg']['a2'] if o['sphere_deg']['a2'] is not None else o['deg'] for o in oth],
                                        rec['pause_deg'], [a['second_deg']], None, rec['voice_bands']) if a['err'] > OK else []
            recs.append(rec)
    with open(OUTD / 'reads.jsonl', 'w') as fh:
        for r in recs:
            fh.write(json.dumps(r) + '\n')
    with open(OUTD / 'truth.jsonl', 'w') as fh:
        for r in recs:
            fh.write(json.dumps({'id': r['id'], 'scenario': r['scenario'], 'pair_mm': r['pair_mm'], 'truth': r['truth']}) + '\n')

    # ---- the score under Jay's rule, per scheme and subset, against the sphere reference and the geometric truth
    subsets = {'speech': lambda r: r['truth']['kind'] == 'speech',
               'speech, alone (the old single-talker set)': lambda r: r['truth']['kind'] == 'speech' and r['truth']['solo'],
               'speech, with another source active': lambda r: r['truth']['kind'] == 'speech' and r['truth']['others'],
               'other sounds': lambda r: r['truth']['kind'] == 'other'}
    def rows_of(r, s, ref):
        x = r['gcc']['angles'][0] if s == 'gcc' and r['gcc'] and r['gcc']['angles'] else (r['a2']['deg'] if s == 'a2' and r['a2'] else None)
        t = r['truth']['sphere_deg'][s] if ref == 'sphere' else r['truth']['deg']
        if x is None or t is None:
            return None
        return {'id': r['id'], 'scenario': r['scenario'], 'truth': t, 'read': x, 'ctx': {}}
    score = {}
    for sub, f in subsets.items():
        for ref in ('sphere', 'geometric'):
            for s, name in (('gcc', 'GccPhat'), ('a2', 'Angle2')):
                rows = [x for x in (rows_of(r, s, ref) for r in recs if f(r)) if x]
                scoped, kept, read_out, scen_out, scen_rows = CS.clean([dict(x) for x in rows])
                score.setdefault(sub, {}).setdefault(ref, {})[name] = {
                    'reads': len(rows), 'in_scope': len(scoped), 'read_outliers': len(read_out),
                    'read_outliers_pct': round(100 * len(read_out) / max(len(scoped), 1), 1),
                    'scenarios': len(scen_rows), 'scenarios_dropped': sum(x['dropped'] for x in scen_rows),
                    'dropped': [x['scenario'] for x in scen_rows if x['dropped']],
                    'kept_pct': round(100 * len(kept) / max(len(scoped), 1), 1), 'score': CS.stats(kept)}

    # ---- the classes: counts per scheme, kind and severity; overlaps; examples to listen to
    tables, overlaps, examples, cat = {}, {}, {}, []
    rnd = random.Random(9)
    for s, name in (('gcc', 'GccPhat'), ('a2', 'Angle2')):
        for kind in ('speech', 'other'):
            sel = [r for r in recs if r['truth']['kind'] == kind and r[s] and r[s].get('err') is not None
                   and abs(r['truth']['sphere_deg'][s]) <= CS.SCOPE]
            n = len(sel)
            wrong = [r for r in sel if r[s]['err'] > OK]
            t = {'reads_in_scope': n, 'moderate': sum(r[s]['severity'] == 'moderate' for r in sel),
                 'outlier': sum(r[s]['severity'] == 'outlier' for r in sel), 'by_class': {}}
            for c in CLASSES:
                cls_of = (lambda r: r['classes']) if s == 'gcc' else (lambda r: r['a2']['classes'])
                m = [r for r in wrong if c in cls_of(r)]
                t['by_class'][c] = {'moderate': sum(r[s]['severity'] == 'moderate' for r in m),
                                    'outlier': sum(r[s]['severity'] == 'outlier' for r in m),
                                    'share_of_wrong_pct': round(100 * len(m) / max(len(wrong), 1), 1),
                                    'only_this_class': sum(cls_of(r) == [c] for r in m)}
                pool = sorted(m, key=lambda r: (r['truth']['file'], r['truth']['onset_s']))
                rnd.shuffle(pool)
                seen, ex = set(), []
                for r in pool:
                    if r['truth']['file'] in seen:
                        continue
                    seen.add(r['truth']['file'])
                    ex.append({'file': r['truth']['file'], 'onset_s': r['truth']['onset_s'], 'pair': r['truth']['pair'],
                               'class': r['truth']['class'], 'truth_deg': r['truth']['deg'], 'ref_deg': r['truth']['sphere_deg'][s],
                               'read': r['gcc']['angles'][0] if s == 'gcc' else r['a2']['deg'], 'classes': cls_of(r)})
                    if len(ex) >= 6:
                        break
                examples.setdefault(name, {}).setdefault(kind, {})[c] = ex
            combos = Counter(tuple(sorted((r['classes'] if s == 'gcc' else r['a2']['classes']))) for r in wrong)
            pairs = Counter()
            for r in wrong:
                for a, b in combinations(sorted(r['classes'] if s == 'gcc' else r['a2']['classes']), 2):
                    pairs[f'{a} + {b}'] += 1
            overlaps.setdefault(name, {})[kind] = {'combinations': [[list(k), v] for k, v in combos.most_common(15)],
                                                   'pairs': dict(pairs.most_common(15))}
            tables.setdefault(name, {})[kind] = t
            for r in wrong:
                cat.append({'scheme': name, 'id': r['id'], 'file': r['truth']['file'], 'onset_s': r['truth']['onset_s'],
                            'pair': r['truth']['pair'], 'room': r['truth']['room'], 'class': r['truth']['class'], 'solo': r['truth']['solo'],
                            'truth_deg': r['truth']['deg'], 'ref_deg': r['truth']['sphere_deg'][s],
                            'read': r['gcc']['angles'][0] if s == 'gcc' else r['a2']['deg'], 'err': r[s]['err'], 'severity': r[s]['severity'],
                            'classes': r['classes'] if s == 'gcc' else r['a2']['classes'],
                            'others': [[o['class'], o['deg']] for o in r['truth']['others']], 'pause_deg': r['pause_deg']})
    # ---- chance for the classes that match a direction the cut carried: the same test with that direction taken from a
    # random other cut of the same scenario (room and pair), against this read and this reference
    chance = {}
    by_scen = defaultdict(list)
    for r in recs:
        by_scen[r['scenario']].append(r)
    feats = lambda r, s: (r['pause_deg'], [o['sphere_deg'][s] if o['sphere_deg'][s] is not None else o['deg'] for o in r['truth']['others']],
                          (r['gcc']['angles'][1:] if r['gcc'] else []) if s == 'gcc' else [r['a2']['second_deg']] if r['a2'] else [])
    for s, name in (('gcc', 'GccPhat'), ('a2', 'Angle2')):
        for kind in ('speech', 'other'):
            wrong = [r for r in recs if r['truth']['kind'] == kind and r[s] and r[s].get('err') is not None and r[s]['err'] > OK
                     and abs(r['truth']['sphere_deg'][s]) <= CS.SCOPE]
            hit, base = Counter(), Counter()
            for r in wrong:
                x = r['gcc']['angles'][0] if s == 'gcc' else r['a2']['deg']
                ref, d = r['truth']['sphere_deg'][s], r['pair_mm'] / 1000
                own = classify(x, ref, d, feats(r, s)[1], feats(r, s)[0], feats(r, s)[2], None, None)
                mate = rnd.choice(by_scen[r['scenario']])
                pa, ot, al = feats(mate, s)
                sh = classify(x, ref, d, ot, pa, al, None, None)
                for c in ('pause direction', 'another labelled source', 'truth was angle 2 or 3'):
                    hit[c] += c in own; base[c] += c in sh
            chance.setdefault(name, {})[kind] = {c: {'observed_pct': round(100 * hit[c] / max(len(wrong), 1), 1),
                                                    'chance_pct': round(100 * base[c] / max(len(wrong), 1), 1)} for c in hit}
            # what the pause held when a read locked to it: a labelled source sounding before the onset, or nothing labelled
            pz = [r for r in wrong if 'pause direction' in (r['classes'] if s == 'gcc' else r['a2']['classes'])]
            lab = sum(1 for r in pz if any(o['before'] and abs((o['sphere_deg'][s] if o['sphere_deg'][s] is not None else o['deg']) - r['pause_deg']) <= 10
                                           for o in r['truth']['others']))
            chance[name][kind]['pause direction']['pause held a labelled source'] = lab
            chance[name][kind]['pause direction']['pause held nothing labelled near that direction'] = len(pz) - lab
    with open(OUTD / 'catalogue.jsonl', 'w') as fh:
        for c in cat:
            fh.write(json.dumps(c) + '\n')

    # ---- the clues, wrong against right (what brief 11 would commit or dim on)
    clues = {}
    for s, name in (('gcc', 'GccPhat'), ('a2', 'Angle2')):
        sel = [r for r in recs if r['truth']['kind'] == 'speech' and r[s] and r[s].get('err') is not None and abs(r['truth']['sphere_deg'][s]) <= CS.SCOPE]
        def med(rows, fn):
            v = [x for x in (fn(r) for r in rows) if x is not None]
            return round(st.median(v), 3) if v else None
        fns = {'gcc share': lambda r: r['gcc']['shares'][0] if r['gcc'] and r['gcc']['shares'] else None,
               'gcc width': lambda r: (r['gcc']['widths'][0][1] - r['gcc']['widths'][0][0]) if r['gcc'] and r['gcc']['widths'] else None,
               'gcc votes': lambda r: r['gcc']['votes'] if r['gcc'] else None,
               'gcc tie': lambda r: float(r['gcc']['tie']) if r['gcc'] else None,
               'gcc 43 ms to lock': lambda r: abs(r['gcc']['track']['43'] - r['gcc']['angles'][0]) if r['gcc'] and r['gcc']['angles'] and r['gcc']['track']['43'] is not None else None,
               'a2 edge': lambda r: None if not r['a2'] or r['a2']['edge'] is None else float(r['a2']['edge']),
               'schemes agree within 5 deg': lambda r: float(abs(r['gcc']['angles'][0] - r['a2']['deg']) <= 5) if r['gcc'] and r['gcc']['angles'] and r['a2'] else None,
               'snr mf dB': lambda r: r['snr_db']['mf'] if r['snr_db'] else None,
               'snr hf1 dB': lambda r: r['snr_db']['hf1'] if r['snr_db'] else None,
               'snr hf2 dB': lambda r: r['snr_db']['hf2'] if r['snr_db'] else None,
               'another source active': lambda r: float(bool(r['truth']['others']))}
        rate = lambda rows, fn: (lambda v: round(100 * sum(v) / len(v), 1) if v else None)([x for x in (fn(r) for r in rows) if x is not None])
        binary = {'gcc tie', 'a2 edge', 'schemes agree within 5 deg', 'another source active'}
        clues[name] = {(k + ' (% of reads)' if k in binary else k + ' (median)'):
                       {sev: (rate if k in binary else med)([r for r in sel if r[s]['severity'] == sev], fn) for sev in ('ok', 'moderate', 'outlier')}
                       for k, fn in fns.items()}

    # ---- the lean, as results/starss23/report.md section 2 (solo speech, pairs 1-2 and 3-4, against geometric truth)
    lean = {}
    solo = [r for r in recs if r['truth']['kind'] == 'speech' and r['truth']['solo'] and r['truth']['pair'] in ('12', '34')]
    flat = [{'t': r['truth']['deg'], 'gcc': r['gcc']['angles'][0] if r['gcc'] and r['gcc']['angles'] else None,
             'a2': r['a2']['deg'] if r['a2'] else None, 'gs': r['truth']['sphere_deg']['gcc'], 'as': r['truth']['sphere_deg']['a2']} for r in solo]
    lean['GccPhat, real rooms'] = lean_by_band(flat, 'gcc', 't')
    lean['GccPhat, rigid sphere, no room (grid)'] = lean_by_band(flat, 'gs', 't')
    lean['Angle2, real rooms'] = lean_by_band(flat, 'a2', 't')
    lean['Angle2, rigid sphere, no room (grid)'] = lean_by_band(flat, 'as', 't')
    lean['GccPhat, real against its sphere reference'] = lean_by_band(flat, 'gcc', 'gs')
    lean['Angle2, real against its sphere reference'] = lean_by_band(flat, 'a2', 'as')

    counts = Counter((r['truth']['kind'], r['truth']['solo']) for r in recs)
    summary = {'reads': len(recs), 'by_kind': {f'{k} {"solo" if s else "not solo"}': v for (k, s), v in counts.items()},
               'by_class_of_sound': dict(Counter(r['truth']['class'] for r in recs).most_common()),
               'replica_ok_pct': round(100 * sum(1 for r in recs if r['gcc'] and r['gcc'].get('replica_ok')) / len(recs), 2),
               'gcc_no_read': sum(1 for r in recs if not r['gcc'] or not r['gcc']['angles']),
               'a2_no_read': sum(1 for r in recs if not r['a2']),
               'alias_share_threshold': ALIAS_SHARE, 'score': score, 'classes': tables, 'overlaps': overlaps,
               'examples': examples, 'chance': chance, 'clues_by_severity': clues, 'lean': lean}
    (OUTD / 'summary.json').write_text(json.dumps(summary, indent=1))
    print(json.dumps({k: summary[k] for k in ('reads', 'by_kind', 'replica_ok_pct', 'gcc_no_read', 'a2_no_read')}, indent=1))


if __name__ == '__main__':
    main()
