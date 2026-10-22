"""Angle2.readUtterance before and after a change, on every room cut set: trace.mjs on each, then per set the lean at
|truth| 30-60 deg (negative = nearer 0), median |error|, share within 10 deg, share with no onset; for the after
version also the share decided on a rising edge, the lean on those and on the rest, and whether the rest read exactly
as before. usage: python before_after.py <cuts dir> <before schemes dir> <after schemes dir> <out dir>"""
import json, os, subprocess, sys, glob
from concurrent.futures import ThreadPoolExecutor
import numpy as np
cuts, before, after, out = sys.argv[1:5]
here = os.path.dirname(os.path.abspath(__file__)); os.makedirs(out, exist_ok=True)
def trace(job):
    tag, d, f = job
    p = f'{out}/{tag}_{os.path.basename(f)}'
    if not os.path.exists(p):
        with open(p, 'w') as fh: subprocess.run(['node', f'{here}/trace.mjs', f, d], stdout=fh, check=True)
    return [{k: v for k, v in json.loads(l).items() if k != 'reads'} for l in open(p)]
files = sorted(glob.glob(f'{cuts}/*.jsonl'))
with ThreadPoolExecutor(4) as ex:
    B = list(ex.map(trace, [('before', before, f) for f in files])); A = list(ex.map(trace, [('after', after, f) for f in files]))
def stats(D):
    got = [d for d in D if d['onset'] is not None]
    lean = [(d['onset'] - d['truth']) * np.sign(d['truth']) for d in got if 30 <= abs(d['truth']) <= 60]
    err = np.array([abs(d['onset'] - d['truth']) for d in got])
    return dict(n=len(D), lean=float(np.median(lean)) if lean else None, err=float(np.median(err)) if len(err) else None,
                w10=float(np.mean(err <= 10)) if len(err) else None, none=1 - len(got) / len(D))
def by_angle(D):
    r = {}
    for a in sorted({abs(d['truth']) for d in D}):
        v = [(d['onset'] - d['truth']) * (np.sign(d['truth']) or 1) for d in D if abs(d['truth']) == a and d['onset'] is not None]
        r[int(a)] = float(np.median(v)) if v else None
    return r
R = {}
for f, b, a in zip(files, B, A):
    n = os.path.basename(f)[:-6]
    e, rest = [d for d in a if d['edge']], [d for d in a if d['edge'] is False]
    same = np.mean([x['onset'] == y['onset'] for x, y in zip(b, a) if y['edge'] is False]) if rest else None
    R[n] = dict(before=stats(b), after=stats(a), edge_share=len(e) / len(a), after_edge=stats(e) if e else None,
                after_rest=stats(rest) if rest else None, rest_same_as_before=None if same is None else float(same),
                before_by_angle=by_angle(b), after_by_angle=by_angle(a))
json.dump(R, open(f'{out}/before_after.json', 'w'), indent=1)
f1 = lambda v: '' if v is None else f'{v:+.1f}'
print('| cuts | before lean | after lean | before err | after err | before w10 | after w10 | none | on edge | lean on edge | lean rest |')
print('|---|---|---|---|---|---|---|---|---|---|---|')
for n, r in R.items():
    print(f"| {n} | {f1(r['before']['lean'])} | {f1(r['after']['lean'])} | {r['before']['err']:.1f} | {r['after']['err']:.1f} | "
          f"{100 * r['before']['w10']:.0f}% | {100 * r['after']['w10']:.0f}% | {100 * r['after']['none']:.0f}% | {100 * r['edge_share']:.0f}% | "
          f"{f1(r['after_edge'] and r['after_edge']['lean'])} | {f1(r['after_rest'] and r['after_rest']['lean'])} |")
print('fallback reads identical to before:', np.mean([r['rest_same_as_before'] for r in R.values() if r['rest_same_as_before'] is not None]))
