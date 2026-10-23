#!/usr/bin/env python3
"""Join LOCATA truth and the schemes' reads into batch A's shared record (reads.jsonl), classify every wrong read,
and score the angle under Jay's rule (harness/scoring/clean_score.py, imported, not copied).

Classes, per scheme, for a read off by more than 10 deg (severity 'moderate') or 36 deg ('outlier'). A read can carry
several. Each entry in a record's "classes" list is "<scheme>:<name>", with scheme gcc or a2, so the list stays one
flat list of strings while saying which scheme it is about:
  <s>:moderate | <s>:outlier      the severity
  mirror               read within 10 deg of -truth (|truth| >= 10)
  endfire_pin          |read| >= 85
  pause_direction      read within 10 deg of pause_deg, which is more than 10 deg from the truth
  another_source       read within 10 deg of another talker active then, who is more than 10 deg from the truth
  zero_pull            |read| < 6 while |truth| > 15
  aliasing_partner     the read's delay and the truth's differ by one period 1/f, with f inside the scheme's band, above
                       c/2d, and the voice's third-octave around f holding at least ALIAS_SHARE of its 300-8000 Hz power
  truth_was_2nd_3rd    GccPhat's angle 2 or 3 (Angle2: its second family) within 10 deg of the truth
  drift                GccPhat only: its 43 ms or 100 ms read within 10 deg of the truth, the lock not
  facing               the talker faced more than 120 deg away from the array
  other                none of the above

usage: python3 build_records.py WORK_DIR OUT_DIR    (WORK_DIR holds truth_*.jsonl and preds_*.jsonl)
"""
import json
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'scoring'))
import clean_score as cs  # noqa: E402

C = 343.0
HIT, OUT = 10.0, cs.READ_OUT
ALIAS_SHARE = 0.10
BAND = {'gcc': (300.0, 8000.0), 'a2': (1100.0, 8000.0)}
NAMES = ['mirror', 'endfire_pin', 'pause_direction', 'another_source', 'zero_pull', 'aliasing_partner',
         'truth_was_2nd_3rd', 'drift', 'facing', 'other']


def tau_of(deg, d):
    return -math.sin(math.radians(deg)) * d / C


def aliasing(read, truth, d, scheme, spec):
    dt = abs(tau_of(read, d) - tau_of(truth, d))
    if dt < 1e-7:
        return False
    f = 1.0 / dt
    lo, hi = BAND[scheme]
    if not (lo <= f <= hi and f > C / (2 * d)):
        return False
    for fc, share in spec:
        if fc / 2 ** (1 / 6) <= f < fc * 2 ** (1 / 6):
            return share >= ALIAS_SHARE
    return False


def classify(scheme, read, rec, cut):
    """The classes of one scheme's wrong read (empty when within 10 deg)."""
    t = rec['truth']['deg']
    err = abs(read - t)
    if err <= HIT:
        return []
    out = ['outlier' if err > OUT else 'moderate']
    d = cut['baseline_m']
    if abs(t) >= 10 and abs(read + t) <= HIT:
        out.append('mirror')
    if abs(read) >= 85:
        out.append('endfire_pin')
    p = rec['pause_deg']
    if p is not None and abs(read - p) <= HIT and abs(t - p) > HIT:
        out.append('pause_direction')
    if any(abs(read - o['deg']) <= HIT and abs(t - o['deg']) > HIT for o in rec['truth']['others']):
        out.append('another_source')
    if abs(read) < 6 and abs(t) > 15:
        out.append('zero_pull')
    if aliasing(read, t, d, scheme, cut['spec']):
        out.append('aliasing_partner')
    if scheme == 'gcc':
        if any(abs(a - t) <= HIT for a in rec['gcc']['angles'][1:3]):
            out.append('truth_was_2nd_3rd')
        tr = rec['gcc']['track']
        if any(tr[k] is not None and abs(tr[k] - t) <= HIT for k in ('43', '100')):
            out.append('drift')
    elif rec['a2']['second_deg'] is not None and abs(rec['a2']['second_deg'] - t) <= HIT:
        out.append('truth_was_2nd_3rd')
    f = rec['truth']['facing_deg']
    if f is not None and f > 120:
        out.append('facing')
    if len(out) == 1:
        out.append('other')
    return out


def load(work):
    cuts, preds = {}, {}
    for p in sorted(work.glob('truth_*.jsonl')):
        for l in open(p):
            c = json.loads(l)
            cuts[c['id']] = c
    for p in sorted(work.glob('preds_*.jsonl')):
        for l in open(p):
            q = json.loads(l)
            preds[q['id']] = q
    assert set(cuts) == set(preds), 'truth and reads differ'
    return cuts, preds


def main():
    work, out = Path(sys.argv[1]), Path(sys.argv[2])
    out.mkdir(parents=True, exist_ok=True)
    cuts, preds = load(work)
    recs = []
    for k in sorted(cuts):
        c, q = cuts[k], preds[k]
        tr = c['truth']
        g = q.get('gcc')
        if g is not None:
            g = {'angles': g['angles'], 'shares': g['shares'], 'widths': g['widths'], 'tie': g['tie'], 'votes': g['votes'],
                 'track': {str(kk): v for kk, v in g['track'].items()}}
        rec = {'dataset': 'locata', 'scenario': c['scenario'], 'id': k, 'pair_mm': c['pair_mm'],
               'truth': {'deg': tr['deg'], 'dist_m': tr['dist_m'], 'facing_deg': tr['facing_deg'],
                         'others': [{'deg': o['deg'], 'class': o['class']} for o in tr['others']]},
               'gcc': g, 'a2': q.get('a2'), 'pause_deg': q.get('pause_deg'), 'snr_db': c['snr_db'],
               'classes': [], 'cause': None}
        cls = []
        if g:
            cls += [f'gcc:{x}' for x in classify('gcc', g['angles'][0], rec, c)]
        if rec['a2']:
            cls += [f'a2:{x}' for x in classify('a2', rec['a2']['deg'], rec, c)]
        rec['classes'] = cls
        recs.append(rec)
    with open(out / 'reads.jsonl', 'w') as fh:
        for r in recs:
            fh.write(json.dumps(r) + '\n')
    with open(out / 'truth.jsonl', 'w') as fh:
        for k in sorted(cuts):
            c = {kk: v for kk, v in cuts[k].items() if kk not in ('L', 'R', 'gain')}
            fh.write(json.dumps(c) + '\n')

    # ---- Jay's rule, through clean_score ----
    data = defaultdict(list)
    for r in recs:
        base = dict(id=r['id'], scenario=r['scenario'], truth=r['truth']['deg'],
                    ctx={'pair_mm': r['pair_mm'], 'dist_m': r['truth']['dist_m'], 'facing_deg': r['truth']['facing_deg']})
        if r['gcc']:
            data['GccPhat'].append(dict(base, read=r['gcc']['angles'][0], others=r['gcc']['angles'][1:]))
        if r['a2']:
            data['Angle2'].append(dict(base, read=r['a2']['deg'], others=[r['a2']['second_deg']], edge=r['a2']['edge']))
    summary = {'rule': {'scope_deg': cs.SCOPE, 'read_outlier_deg': cs.READ_OUT, 'scenario_mean_deg': cs.SCEN_MEAN,
                        'scenario_outlier_share': cs.SCEN_OUT_SHARE}}
    for sp in (160, 80):
        sub = {s: [r for r in rows if r['ctx']['pair_mm'] == sp] for s, rows in data.items()}
        summary[f'{sp}mm'] = cs.run(f'locata_{sp}mm', sub, out)
    # ---- the class catalogue, in scope ----
    cat = {}
    by_id = {r['id']: r for r in recs}
    for s in ('gcc', 'a2'):
        for sp in (160, 80):
            for sev in ('moderate', 'outlier'):
                sel = [r for r in recs if r['pair_mm'] == sp and abs(r['truth']['deg']) <= cs.SCOPE
                       and f'{s}:{sev}' in r['classes']]
                cnt = Counter(x.split(':')[1] for r in sel for x in r['classes'] if x.startswith(s + ':')
                              and x.split(':')[1] in NAMES)
                ov = Counter(tuple(sorted(x.split(':')[1] for x in r['classes'] if x.startswith(s + ':')
                                          and x.split(':')[1] in NAMES)) for r in sel)
                ex = defaultdict(list)
                for r in sel:
                    for x in r['classes']:
                        n = x.split(':')[1]
                        if x.startswith(s + ':') and n in NAMES and len(ex[n]) < 5:
                            c = cuts[r['id']]
                            ex[n].append({'id': r['id'], 'file': f"{c['set']}/{c['task']}/{c['recording']}/dicit/audio_array_dicit.wav",
                                          'time_s': c['onset_s'], 'truth': r['truth']['deg'],
                                          'read': r['gcc']['angles'][0] if s == 'gcc' else r['a2']['deg']})
                cat[f'{s} {sp}mm {sev}'] = {'reads': len(sel), 'classes': dict(cnt.most_common()),
                                           'overlaps': {'+'.join(k): v for k, v in ov.most_common(12)},
                                           'examples': ex}
    summary['catalogue'] = cat
    summary['checks'] = {'gcc_reads': sum(1 for q in preds.values() if q.get('gcc')),
                         'replica_agrees': sum(1 for q in preds.values() if q.get('gcc') and q.get('gcc_replica_agrees')),
                         'gcc_err': sum(1 for q in preds.values() if 'gcc_err' in q),
                         'a2_err': sum(1 for q in preds.values() if 'a2_err' in q),
                         'gcc_none': sum(1 for q in preds.values() if 'gcc' in q and q['gcc'] is None),
                         'a2_none': sum(1 for q in preds.values() if 'a2' in q and q['a2'] is None)}
    (out / 'summary.json').write_text(json.dumps(summary, indent=1))
    print(json.dumps({k: v for k, v in summary.items() if k != 'catalogue'}, indent=1)[:4000])


if __name__ == '__main__':
    main()
