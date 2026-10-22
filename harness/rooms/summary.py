"""Group totals of before_after.py's output: per spacing and kind of room, the mean of each set's lean, median error and
share within 10 deg, before and after; the share decided on a clean rising edge and how those and the rest read; and
how many cuts' onsets moved to within 10 deg of the truth, or out of it. usage: python summary.py <before_after dir>"""
import glob, json, os, sys
import numpy as np
W = sys.argv[1]
R = json.load(open(f'{W}/before_after.json'))
moved = {}
for p in sorted(glob.glob(f'{W}/after_*.jsonl')):
    n = os.path.basename(p)[6:-6]
    for a, b in zip(map(json.loads, open(p)), map(json.loads, open(f'{W}/before_{n}.jsonl'))):
        if a['onset'] is None or b['onset'] is None: continue
        eb, ea = abs(b['onset'] - b['truth']), abs(a['onset'] - a['truth'])
        m = moved.setdefault(n, [0, 0]); m[0] += eb > 10 and ea <= 10; m[1] += eb <= 10 and ea > 10
kinds = {'free field': lambda n: n.startswith('free') and '+' not in n,
         'free field + noise/tail/jitter': lambda n: n.startswith('free') and '+' in n,
         'rooms, clean': lambda n: not n.startswith('free') and '+' not in n,
         'rooms + noise/tail/jitter': lambda n: not n.startswith('free') and '+' in n}
avg = lambda xs, k: np.mean([x[k] for x in xs if x and x[k] is not None]) if any(x and x[k] is not None for x in xs) else float('nan')
print('| sets | mm | lean before -> after | median err before -> after | within 10 before -> after | on edge | edge: lean, within 10 | rest: lean, within 10 | moved in / out |')
print('|---|---|---|---|---|---|---|---|---|')
out = {}
for k, f in kinds.items():
    for d in ('0.157', '0.069'):
        ns = [n for n in R if f(n.rsplit('_', 1)[0]) and n.endswith(d)]
        if not ns: continue
        m = [R[n] for n in ns]
        b, a, e, r = [x['before'] for x in m], [x['after'] for x in m], [x['after_edge'] for x in m], [x['after_rest'] for x in m]
        mi, mo = sum(moved[n][0] for n in ns), sum(moved[n][1] for n in ns)
        out[f'{k} {d}'] = dict(sets=len(ns), before=[avg(b, 'lean'), avg(b, 'err'), avg(b, 'w10')], after=[avg(a, 'lean'), avg(a, 'err'), avg(a, 'w10')],
                               edge_share=float(np.mean([x['edge_share'] for x in m])), edge=[avg(e, 'lean'), avg(e, 'w10')], rest=[avg(r, 'lean'), avg(r, 'w10')], moved=[mi, mo])
        print(f"| {k} ({len(ns)}) | {float(d) * 1000:.0f} | {avg(b, 'lean'):+.1f} -> {avg(a, 'lean'):+.1f} | {avg(b, 'err'):.1f} -> {avg(a, 'err'):.1f} | "
              f"{100 * avg(b, 'w10'):.0f}% -> {100 * avg(a, 'w10'):.0f}% | {100 * out[f'{k} {d}']['edge_share']:.0f}% | {avg(e, 'lean'):+.1f}, {100 * avg(e, 'w10'):.0f}% | "
              f"{avg(r, 'lean'):+.1f}, {100 * avg(r, 'w10'):.0f}% | {mi} / {mo} |")
print('all sets: moved in', sum(v[0] for v in moved.values()), 'out', sum(v[1] for v in moved.values()))
json.dump(out, open(f'{W}/summary.json', 'w'), indent=1)
