"""Answer brief 1's three questions over all six STARSS23 capsule pairs (sign +1, which the scorer shows is right)."""
import json, statistics as st, sys
from collections import defaultdict
from pathlib import Path

W = Path(sys.argv[1])
PAIRS = ['12', '13', '14', '23', '24', '34']
rows = []
for p in PAIRS:
    with open(W / f'cuts_{p}.jsonl') as fc, open(W / f'preds_{p}.jsonl') as fp:
        for lc, lp in zip(fc, fp):
            c = json.loads(lc); q = json.loads(lp)
            rows.append(dict(pair=p, room=c['room'], file=c['file'], onset=c['onset_s'], t=c['truth_lateral'],
                             az=c['az'], el=c['el'], dist=c['dist_cm'], gcc=q.get('gcc'), a2=q.get('a2')))
med = lambda v: round(st.median(v), 1) if v else None
def pct(v, thr=10): return round(100 * sum(1 for x in v if x <= thr) / len(v)) if v else None
S = {'GccPhat': lambda r: r['gcc'][0] if r['gcc'] else None,
     'Angle2': lambda r: r['a2'][0] if r['a2'] else None}
out = {}
for name, f in S.items():
    R = [(r, f(r)) for r in rows if f(r) is not None]
    o = out[name] = {'n': len(R), 'median_abs_err': med([abs(p - r['t']) for r, p in R]),
                     'within10_pct': pct([abs(p - r['t']) for r, p in R])}
    # per pair
    o['by_pair'] = {p: med([abs(q - r['t']) for r, q in R if r['pair'] == p]) for p in PAIRS}
    # per room, all pairs pooled, and per room within the 0-40 deg band only (removes the angle mix)
    rooms = sorted({r['room'] for r, _ in R}, key=lambda s: int(s[4:]))
    o['by_room'] = {m: med([abs(q - r['t']) for r, q in R if r['room'] == m]) for m in rooms}
    o['by_room_0_40'] = {m: med([abs(q - r['t']) for r, q in R if r['room'] == m and abs(r['t']) < 40]) for m in rooms}
    o['n_room'] = {m: sum(1 for r, _ in R if r['room'] == m) // 6 for m in rooms}
    # room x pair, 0-40 band: does a room's rank hold across pairs?
    o['room_pair_0_40'] = {m: {p: med([abs(q - r['t']) for r, q in R if r['room'] == m and r['pair'] == p and abs(r['t']) < 40])
                               for p in PAIRS} for m in rooms}
    # lean: error measured along the truth's side, for |truth| >= 15 (near 0 the side is noise); negative = toward 0
    bands = [(15, 30), (30, 45), (45, 60), (60, 90)]
    o['lean'] = {}
    for lo, hi in bands:
        v = [(q - r['t']) * (1 if r['t'] > 0 else -1) for r, q in R if lo <= abs(r['t']) < hi]
        o['lean'][f'{lo}-{hi}'] = {'n': len(v), 'median_signed': med(v),
                                   'share_inward': round(100 * sum(1 for x in v if x < 0) / len(v)) if v else None,
                                   'median_abs': med([abs(x) for x in v])}
    o['abs_by_band'] = {f'{lo}-{hi}': med([abs(q - r['t']) for r, q in R if lo <= abs(r['t']) < hi]) for lo, hi in [(0, 15)] + bands}
# rescue: GccPhat angles 2/3, Angle2's reflection, when angle 1 is off by > 10
g = [r for r in rows if r['gcc']]
off = [r for r in g if abs(r['gcc'][0] - r['t']) > 10]
resc = [r for r in off if any(abs(a - r['t']) <= 10 for a in r['gcc'][1:])]
out['GccPhat']['rescue'] = {'off': len(off), 'rescued': len(resc), 'pct': round(100 * len(resc) / len(off), 1),
                            'has_angle2': sum(1 for r in off if len(r['gcc']) > 1)}
# chance baseline for the rescue: a random other cut's angles 2/3 against this truth
import random
random.seed(0)
ch = 0
for r in off:
    o2 = random.choice(g)
    if any(abs(a - r['t']) <= 10 for a in o2['gcc'][1:]): ch += 1
out['GccPhat']['rescue']['chance_pct'] = round(100 * ch / len(off), 1)
a = [r for r in rows if r['a2']]
off2 = [r for r in a if abs(r['a2'][0] - r['t']) > 10]
resc2 = [r for r in off2 if r['a2'][1] is not None and abs(r['a2'][1] - r['t']) <= 10]
ch2 = sum(1 for r in off2 if (lambda o2: o2['a2'][1] is not None and abs(o2['a2'][1] - r['t']) <= 10)(random.choice(a)))
out['Angle2']['rescue'] = {'off': len(off2), 'rescued': len(resc2), 'pct': round(100 * len(resc2) / len(off2), 1),
                           'has_refl': sum(1 for r in off2 if r['a2'][1] is not None), 'chance_pct': round(100 * ch2 / len(off2), 1)}
# do the two schemes agree with each other, and is the truth there when they do?
both = [r for r in rows if r['gcc'] and r['a2']]
agree = [r for r in both if abs(r['gcc'][0] - r['a2'][0]) <= 5]
out['agreement'] = {'n': len(both), 'agree_within5_pct': round(100 * len(agree) / len(both)),
                    'gcc_err_when_agree': med([abs(r['gcc'][0] - r['t']) for r in agree]),
                    'gcc_err_when_not': med([abs(r['gcc'][0] - r['t']) for r in both if r not in agree])}
json.dump(out, open(W / 'analysis.json', 'w'), indent=1)
print(json.dumps({k: {kk: vv for kk, vv in v.items() if kk not in ('room_pair_0_40',)} for k, v in out.items()}, indent=1))
