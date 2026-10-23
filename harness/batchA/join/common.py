"""Brief 11: one row per read and scheme, across STARSS23 (brief 9), LOCATA (brief 10) and the lab (brief 13).

The three record files differ in small ways (where `classes` live, which reference a read is judged against, how the
other sources are written). rows() hides that: every row has the read, its reference, its error, the clues known at
the moment of the read, and the context the truth gives (other sources, facing), which attribution may use and a
commit-or-dim rule may not.
"""
import gzip
import json
import math
from pathlib import Path

OK, OUT = 10.0, 36.0
SCOPE = 75.0


def opener(p):
    p = Path(p)
    return gzip.open(p, 'rt') if p.suffix == '.gz' else open(p)


def clues(r, s):
    """What the math knew at the moment of the read, for scheme s ('gcc' or 'a2'). Nothing from the truth."""
    g, a = r.get('gcc') or {}, r.get('a2') or {}
    sh = g.get('shares') or []
    x_g = g['angles'][0] if g.get('angles') else None
    x_a = a.get('deg')
    t43 = (g.get('track') or {}).get('43')
    w = g.get('widths') or []
    return {
        'share': sh[0] if sh else None,
        'margin': (sh[0] - (sh[1] if len(sh) > 1 else 0.0)) if sh else None,
        'width': (w[0][1] - w[0][0]) if w else None,
        'tie': float(bool(g.get('tie'))) if g else None,
        'votes': g.get('votes'),
        'early_vs_lock': abs(t43 - x_g) if t43 is not None and x_g is not None else None,
        'pause_share': r.get('pause_share'),
        'read_to_pause': (abs((x_g if s == 'gcc' else x_a) - r['pause_deg'])
                          if r.get('pause_deg') is not None and (x_g if s == 'gcc' else x_a) is not None else None),
        'snr_mf': (r.get('snr_db') or {}).get('mf'), 'snr_hf1': (r.get('snr_db') or {}).get('hf1'),
        'snr_hf2': (r.get('snr_db') or {}).get('hf2'),
        'a2_edge': None if a.get('edge') is None else float(a['edge']),
        'agree': abs(x_g - x_a) if x_g is not None and x_a is not None else None,
        'a2_first_ms': a.get('first_ms'),
    }


def row(ds, r, s, ref, others, facing, kind, extra=None):
    g, a = r.get('gcc') or {}, r.get('a2') or {}
    x = (g['angles'][0] if g.get('angles') else None) if s == 'gcc' else a.get('deg')
    if x is None or ref is None:
        return None
    d = {'dataset': ds, 'id': r['id'], 'scenario': r['scenario'], 'pair_mm': r['pair_mm'], 'scheme': s, 'kind': kind,
         'x': x, 'ref': ref, 'err': abs(x - ref), 'clues': clues(r, s), 'pause_deg': r.get('pause_deg'),
         'track43': (g.get('track') or {}).get('43'), 'alts': (g.get('angles') or [])[1:] if s == 'gcc' else [a.get('second_deg')],
         'others': others, 'facing': facing}
    if extra:
        d.update(extra)
    return d


def starss_rows(path):
    """brief 9's reads.jsonl.gz: references are each scheme's sphere-only read for the direction."""
    out = []
    for l in opener(path):
        r = json.loads(l)
        t = r['truth']
        for s in ('gcc', 'a2'):
            ref = t['sphere_deg'][s]
            oth = [{'deg': o['sphere_deg'][s] if o['sphere_deg'][s] is not None else o['deg'], 'class': o['class'],
                    'before': o['before'], 'during': o['during']} for o in t['others']]
            x = row('starss23', r, s, ref, oth, None, t['kind'], {'solo': t['solo'], 'room': t['room'], 'file': t['file'],
                                                                   'onset_s': t['onset_s'], 'pair': t['pair']})
            if x:
                out.append(x)
    return out


def locata_rows(reads, truth):
    """LOCATA reads (runner.mjs output joined to locata_cut.py truth): reference is the exact delay to the head."""
    T = {}
    for l in opener(truth):
        t = json.loads(l)
        T[t['id']] = t
    out = []
    for l in opener(reads):
        r = json.loads(l)
        t = T[r['id']]
        oth = [{'deg': o['deg'], 'class': 'talker', 'before': o['before'] > 0, 'during': o['during'] > 0,
                'before_share': o['before'], 'during_share': o['during']} for o in t['truth']['others']]
        for s in ('gcc', 'a2'):
            x = row('locata', r, s, t['truth']['deg'], oth, t['truth']['facing_deg'], 'speech',
                    {'set': t['set'], 'talker': t['talker'], 'onset_s': t['onset_s'], 'dist_m': t['truth']['dist_m']})
            if x:
                out.append(x)
    return out


def lab_rows(path):
    out = []
    for l in opener(path):
        r = json.loads(l)
        oth = [{'deg': o['deg'], 'class': o['class'], 'before': True, 'during': True} for o in r['truth']['others']]
        for s in ('gcc', 'a2'):
            x = row('lab', r, s, r['truth']['deg'], oth, None, 'speech', {'cause': r['cause'], 'placement': r['placement']})
            if x:
                out.append(x)
    return out


# ---- attribution: which lab cause's fingerprint a wrong read carries ------------------------------------------------
# The fingerprints, from results/batchA/lab/report.md section 3, with the lab's own threshold for a directional pause
# (pause_share 0.5; the lab's wrong reads under steady sources sit at 0.80-0.89, common-mode at 1.0, diffuse 0.2,
# quiet 0.1, baseline 0.09). In order; a read takes the first that fits as its cause, and every fit is also kept.
PS = 0.5
CAUSES = ['common-mode (0 deg pull)', 'steady source in the pause', 'another source during the read',
          'pause holds the talker (late onset)', 'early onset (first draw on the pause)', 'facing away',
          'scatter (diffuse noise, quiet voice, room)', 'unattributed']


def fits(r):
    c = r['clues']
    x, ref, pd, ps = r['x'], r['ref'], r['pause_deg'], c['pause_share']
    f = []
    if ps is not None and ps >= PS and pd is not None and abs(pd) < 6 and abs(x) < 6:
        f.append(CAUSES[0])
    if ps is not None and ps >= PS and pd is not None and abs(x - pd) <= 10 and abs(pd - ref) > 10:
        f.append(CAUSES[1])
    if any(o['during'] and abs(x - o['deg']) <= 10 and abs(o['deg'] - ref) > 10 for o in r['others']):
        f.append(CAUSES[2])
    if ps is not None and ps >= PS and pd is not None and abs(pd - ref) <= 10:
        f.append(CAUSES[3])
    if r['scheme'] == 'gcc' and c['early_vs_lock'] is not None and c['early_vs_lock'] > 30 and pd is not None \
            and r['track43'] is not None and abs(r['track43'] - pd) <= 10:
        f.append(CAUSES[4])
    if r['facing'] is not None and r['facing'] > 120:
        f.append(CAUSES[5])
    if ps is not None and ps < PS:
        f.append(CAUSES[6])
    return f or [CAUSES[7]]


def lab_family(cause):
    c = cause.split(':')
    base = c[0].replace('no_pause+', '')
    if base in ('steady_pink', 'steady_voice'):
        return 'steady source in the pause'
    if base == 'common_mode':
        return 'common-mode (0 deg pull)'
    if base in ('diffuse', 'quiet'):
        return 'scatter (diffuse noise, quiet voice, room)'
    if base == 'onset_offset':
        return 'pause holds the talker (late onset)' if c[1].startswith('+') else 'early onset (first draw on the pause)'
    return 'none (baseline, band edge, no pause)'


def in_scope(r):
    return abs(r['ref']) <= SCOPE


def tau(deg, d_mm):
    return -math.sin(math.radians(deg)) * d_mm / 1000 / 343.0
