"""Angle2.readUtterance on STARSS23 before and after the 2026-10-22 onset fix (results/angle2_pull.md), on the same cuts.
Per |truth| band: Angle2's median |error|, share within 10 deg, lean (signed error along the truth's side, negative =
nearer 0) and its offset from GccPhat on the same cut, before and after; the share decided on a clean rising edge and
how those and the rest read; per room; how many onsets moved to within 10 deg or out of it. GccPhat is unchanged, so its
reads must match the old ones exactly (checked).
usage: python compare_fix.py <dir with new cuts_XY.jsonl + preds_XY.jsonl> <dir with old preds_XY.jsonl> [out.json]"""
import json, os, statistics as st, sys
from pathlib import Path
NEW, OLD = Path(sys.argv[1]), Path(sys.argv[2]); PAIRS = os.environ.get('PAIRS', '12 13 14 23 24 34').split()
BANDS = [(0, 15), (15, 30), (30, 45), (45, 60), (60, 90)]
rows, gcc_same, gcc_n = [], 0, 0
for p in PAIRS:
    for lc, ln, lo in zip(open(NEW / f'cuts_{p}.jsonl'), open(NEW / f'preds_{p}.jsonl'), open(OLD / f'preds_{p}.jsonl')):
        c, q, o = json.loads(lc), json.loads(ln), json.loads(lo)
        assert q['file'] == o['file'] and q['onset_s'] == o['onset_s'], (p, q['file'], o['file'])
        gcc_n += 1; gcc_same += q.get('gcc') == o.get('gcc')
        rows.append(dict(pair=p, room=c['room'], t=c['truth_lateral'], gcc=q['gcc'][0] if q.get('gcc') else None,
                         old=o['a2'][0] if o.get('a2') else None, new=q['a2'][0] if q.get('a2') else None, edge=q.get('a2_edge')))
med = lambda v: round(st.median(v), 1) if v else None
pct = lambda v: round(100 * sum(v) / len(v)) if v else None
side = lambda r: 1 if r['t'] > 0 else -1
def stats(sel, k):
    s = [r for r in sel if r[k] is not None]
    return dict(n=len(s), err=med([abs(r[k] - r['t']) for r in s]), w10=pct([abs(r[k] - r['t']) <= 10 for r in s]),
                lean=med([(r[k] - r['t']) * side(r) for r in s if abs(r['t']) >= 15]),
                minus_gcc=med([(r[k] - r['gcc']) * side(r) for r in s if r['gcc'] is not None]))
out = dict(cuts=len(rows), gcc_identical=round(gcc_same / gcc_n, 4), edge_share=pct([bool(r['edge']) for r in rows if r['new'] is not None]))
out['all'] = dict(before=stats(rows, 'old'), after=stats(rows, 'new'), after_edge=stats([r for r in rows if r['edge']], 'new'),
                  after_rest=stats([r for r in rows if r['edge'] is False], 'new'), gcc=stats(rows, 'gcc'))
out['by_band'] = {}
for lo, hi in BANDS:
    sel = [r for r in rows if lo <= abs(r['t']) < hi]
    out['by_band'][f'{lo}-{hi}'] = dict(before=stats(sel, 'old'), after=stats(sel, 'new'), edge_share=pct([bool(r['edge']) for r in sel if r['new'] is not None]),
                                        after_edge=stats([r for r in sel if r['edge']], 'new'), after_rest=stats([r for r in sel if r['edge'] is False], 'new'),
                                        gcc=stats(sel, 'gcc'))
rooms = sorted({r['room'] for r in rows}, key=lambda s: int(s[4:]))
out['by_room_below_40'] = {m: dict(before=stats([r for r in rows if r['room'] == m and abs(r['t']) < 40], 'old')['err'],
                                   after=stats([r for r in rows if r['room'] == m and abs(r['t']) < 40], 'new')['err'],
                                   gcc=stats([r for r in rows if r['room'] == m and abs(r['t']) < 40], 'gcc')['err']) for m in rooms}
both = [r for r in rows if r['old'] is not None and r['new'] is not None]
out['moved_in'] = sum(abs(r['old'] - r['t']) > 10 and abs(r['new'] - r['t']) <= 10 for r in both)
out['moved_out'] = sum(abs(r['old'] - r['t']) <= 10 and abs(r['new'] - r['t']) > 10 for r in both)
out['fallback_identical'] = pct([r['old'] == r['new'] for r in both if r['edge'] is False])
if len(sys.argv) > 3: json.dump(out, open(sys.argv[3], 'w'), indent=1)
print(json.dumps(out, indent=1))
