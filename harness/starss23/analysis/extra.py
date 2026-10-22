import json, statistics as st, sys
from collections import defaultdict
from pathlib import Path
W = Path(sys.argv[1]); PAIRS = ['12', '13', '14', '23', '24', '34']
rows = []
for p in PAIRS:
    for lc, lp in zip(open(W / f'cuts_{p}.jsonl'), open(W / f'preds_{p}.jsonl')):
        c = json.loads(lc); q = json.loads(lp)
        rows.append(dict(pair=p, room=c['room'], t=c['truth_lateral'], el=c['el'], dist=c['dist_cm'], gcc=q.get('gcc'), a2=q.get('a2')))
med = lambda v: round(st.median(v), 1) if v else None
side = lambda r: 1 if r['t'] > 0 else -1
rooms = sorted({r['room'] for r in rows}, key=lambda s: int(s[4:]))
out = {}
# 1. GccPhat outward lean per room, 30-60 band: same everywhere (the array) or room by room?
out['gcc_lean_30_60_by_room'] = {m: med([(r['gcc'][0] - r['t']) * side(r) for r in rows if r['room'] == m and r['gcc'] and 30 <= abs(r['t']) < 60]) for m in rooms}
# 2. Angle2 against GccPhat on the same cut, along the truth's side (negative = Angle2 nearer 0 than GccPhat)
out['a2_minus_gcc_by_band'] = {}
for lo, hi in [(0, 15), (15, 30), (30, 45), (45, 60), (60, 90)]:
    v = [(r['a2'][0] - r['gcc'][0]) * side(r) for r in rows if r['a2'] and r['gcc'] and lo <= abs(r['t']) < hi]
    out['a2_minus_gcc_by_band'][f'{lo}-{hi}'] = {'n': len(v), 'median': med(v), 'share_inward': round(100 * sum(x < 0 for x in v) / len(v))}
# 3. error by distance and by elevation (0-40 band)
for key, bins in (('dist', [(0, 150), (150, 250), (250, 350), (350, 1000)]), ('el', [(-90, -20), (-20, 0), (0, 20), (20, 90)])):
    out[f'err_by_{key}_0_40'] = {}
    for lo, hi in bins:
        sel = [r for r in rows if r['gcc'] and r['a2'] and abs(r['t']) < 40 and r[key] is not None and lo <= r[key] < hi]
        out[f'err_by_{key}_0_40'][f'{lo}-{hi}'] = {'n': len(sel) // 6, 'gcc': med([abs(r['gcc'][0] - r['t']) for r in sel]),
                                                    'a2': med([abs(r['a2'][0] - r['t']) for r in sel])}
out['room_median_dist_cm'] = {m: med([r['dist'] for r in rows if r['room'] == m and r['dist'] is not None and r['pair'] == '12']) for m in rooms}
# 4. room rank consistency across pairs (Spearman of per-room GccPhat median error, 0-40 band)
def ranks(v):
    o = sorted(range(len(v)), key=lambda i: v[i]); r = [0] * len(v)
    for k, i in enumerate(o): r[i] = k
    return r
def spear(a, b):
    ra, rb = ranks(a), ranks(b); n = len(a)
    return 1 - 6 * sum((x - y) ** 2 for x, y in zip(ra, rb)) / (n * (n * n - 1))
M = {p: [med([abs(r['gcc'][0] - r['t']) for r in rows if r['room'] == m and r['pair'] == p and r['gcc'] and abs(r['t']) < 40]) or 99 for m in rooms] for p in PAIRS}
sp = [spear(M[a], M[b]) for i, a in enumerate(PAIRS) for b in PAIRS[i + 1:]]
out['room_rank_spearman_across_pairs'] = {'min': round(min(sp), 2), 'median': round(st.median(sp), 2), 'max': round(max(sp), 2)}
# 5. per-room distance vs per-room error (is the 'room' effect just how far away people stood?)
d = [out['room_median_dist_cm'][m] for m in rooms]; e = [med([abs(r['gcc'][0] - r['t']) for r in rows if r['room'] == m and r['gcc'] and abs(r['t']) < 40]) for m in rooms]
out['spearman_room_dist_vs_err'] = round(spear(d, e), 2)
json.dump(out, open(W / 'analysis_extra.json', 'w'), indent=1); print(json.dumps(out, indent=1))
