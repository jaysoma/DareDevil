"""Angle2.readUtterance's onset on room cuts, for one or more copies of the schemes folder: median lean at |truth|
30-60 deg (negative = nearer 0), median |error| over all angles, and the share of cuts with no onset.
usage: python sweep.py <cuts dir> <out json> <variant=schemes dir> ... [-- configs...]"""
import json, os, subprocess, sys, glob
from concurrent.futures import ThreadPoolExecutor
import numpy as np
args = sys.argv[1:]; cfgs = args[args.index('--') + 1:] if '--' in args else None; args = args[:args.index('--')] if '--' in args else args
cuts_dir, outp, variants = args[0], args[1], dict(a.split('=', 1) for a in args[2:])
files = sorted(f for f in glob.glob(f'{cuts_dir}/*.jsonl') if not cfgs or os.path.basename(f).rsplit('_', 1)[0] in cfgs)
here = os.path.dirname(os.path.abspath(__file__))
def run(job):
    v, f = job
    out = subprocess.run(['node', f'{here}/trace.mjs', f, variants[v]], capture_output=True, text=True, check=True).stdout
    D = [json.loads(l) for l in out.splitlines()]
    lean = [(d['onset'] - d['truth']) * np.sign(d['truth']) for d in D if d['onset'] is not None and 30 <= abs(d['truth']) <= 60]
    err = [abs(d['onset'] - d['truth']) for d in D if d['onset'] is not None]
    return v, os.path.basename(f)[:-6], dict(lean=float(np.median(lean)), err=float(np.median(err)),
                                            w10=float(np.mean(np.array(err) <= 10)), none=float(np.mean([d['onset'] is None for d in D])))
with ThreadPoolExecutor(4) as ex: res = list(ex.map(run, [(v, f) for v in variants for f in files]))
R = {}
for v, n, r in res: R.setdefault(n, {})[v] = r
json.dump(R, open(outp, 'w'), indent=1)
print('| cuts | ' + ' | '.join(variants) + ' |'); print('|---|' + '---|' * len(variants))
for n in R: print(f'| {n} | ' + ' | '.join(f"{R[n][v]['lean']:+.1f} / {R[n][v]['err']:.1f} / {100 * R[n][v]['none']:.0f}%" for v in variants) + ' |')
