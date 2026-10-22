#!/usr/bin/env python3
"""Score scheme predictions against STARSS23 tracker truth.

For each scheme, both capsule signs are tried and reported (the pair's sign vs the schemes' "+ reaches R first"
convention is checked, not assumed). Reports: overall median |error|, by room, by |lateral| band, the signed error
(negative = pulled toward 0), and for GccPhat whether angle 2 or 3 is right when angle 1 is not.
"""
import json
import statistics as st
import sys
from collections import defaultdict

cuts = [json.loads(l) for l in open(sys.argv[1]) if l.strip()]
preds = [json.loads(l) for l in open(sys.argv[2]) if l.strip()]
assert len(cuts) == len(preds), 'cuts and predictions differ in length'


def med(v):
    return round(st.median(v), 1) if v else None


def report(name, first, extra=None):
    print(f'\n== {name} ==')
    for sign in (+1, -1):
        err, inward, by_room, by_band, rescued, n1 = [], [], defaultdict(list), defaultdict(list), 0, 0
        for c, p in zip(cuts, preds):
            f = first(p)
            if f is None:
                continue
            t = sign * c['truth_lateral']
            e = abs(f - t)
            err.append(e)
            inward.append(abs(f) - abs(t))
            by_room[c['room']].append(e)
            by_band[min(int(abs(t) // 20) * 20, 80)].append(e)
            if extra and e > 10:
                n1 += 1
                if any(a is not None and abs(a - t) <= 10 for a in extra(p)):
                    rescued += 1
        if not err:
            print('  no predictions'); return
        print(f'  sign {sign:+d}: n={len(err)}  median |err| {med(err)} deg  within 10 deg {sum(e <= 10 for e in err) / len(err):.0%}'
              f'  median (|pred|-|truth|) {med(inward)} deg')
        print('    by |lateral|: ' + '  '.join(f'{b}-{b + 20}: {med(v)} (n={len(v)})' for b, v in sorted(by_band.items())))
        print('    by room: ' + '  '.join(f'{r}: {med(v)}' for r, v in sorted(by_room.items())))
        if extra:
            print(f'    angle 1 off by >10 deg: {n1}; angle 2 or 3 within 10 deg in {rescued} of those')


report('GccPhat (angle 1 at lock)', lambda p: p['gcc'][0] if p.get('gcc') else None,
       extra=lambda p: p['gcc'][1:] if p.get('gcc') else [])
report('Angle2.readUtterance (onset)', lambda p: p['a2'][0] if p.get('a2') else None)
