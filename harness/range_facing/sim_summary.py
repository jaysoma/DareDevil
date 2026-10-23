#!/usr/bin/env python3
"""Brief 20 step 5's tables, from sim_probe.py's output: the probe's r_c and echo time against the truth, by room size,
echo time and noise; and whether the talkers' measured CDR follows the line the probe predicts.

Per room x noise: r_c error = log2(r_c probe / r_c true) (r_c true: the talkers' own true DRRs, slope -20); the echo time
error likewise. The talkers: their true DRR's own slope (does the room keep the law?), the measured CDR's slope and
offset against the probe's line 20 log10(r_c / r), and absolute range r = r_c 10^(-CDR / 20) against the truth, per
band, with the probe's r_c and with the true r_c (the estimator's own share of the error).
usage: sim_summary.py <sim_probe.jsonl> <out json>
"""
import json
import math
import statistics as st
import sys
from collections import defaultdict

import numpy as np

BANDS = ('MF', 'ALL', 'HF', 'MF_raw', 'ALL_raw', 'LF_raw')


def main():
    R = [json.loads(l) for l in open(sys.argv[1])]
    rows = []
    for r in R:
        e_rc = math.log2(r['rc_probe'] / r['rc_true']) if r['rc_probe'] else None
        e_t = math.log2(r['t60_probe'] / r['t60_true']) if r['t60_probe'] else None
        tk = r['talkers']
        lr = np.log10([t['r'] for t in tk])
        drr = np.array([t['drr_true'] for t in tk])
        row = {'size': r['size'], 'rt60': r['rt60_nominal'], 'noise_db': r['noise_db_under_talker_1m'],
               'rc_true': r['rc_true'], 'rc_sabine': r['rc_sabine'], 'rc_probe': r['rc_probe'],
               'rc_err_pct': None if e_rc is None else round(100 * (2 ** e_rc - 1), 1),
               't60_true': r['t60_true'], 't60_probe': r['t60_probe'],
               't60_err_pct': None if e_t is None else round(100 * (2 ** e_t - 1), 1),
               'true_drr_slope': round(float(np.polyfit(lr, drr, 1)[0]), 2)}
        for b in BANDS:
            v = [(math.log10(t['r']), t[b], t['r']) for t in tk if t.get(b) is not None]
            if len(v) < 10:
                continue
            x, y, d = map(np.array, zip(*v))
            sl, ic = np.polyfit(x, y, 1)
            line = 20 * np.log10(r['rc_probe'] / d) if r['rc_probe'] else None
            res = {'slope': round(float(sl), 2),
                   'offset_from_probe_line_db': None if line is None else round(float(np.median(y - line)), 2)}
            for name, rc in (('probe', r['rc_probe']), ('true', r['rc_true'])):
                if rc:
                    e = np.log2(rc * 10 ** (-y / 20) / d)
                    res[f'range_med_abs_doublings_{name}_rc'] = round(float(np.median(np.abs(e))), 2)
                    res[f'range_bias_doublings_{name}_rc'] = round(float(np.median(e)), 2)
            row[b] = res
        # the true DRR through the same line: the law itself, with the estimator out of the way
        e = np.log2(r['rc_probe'] * 10 ** (-drr / 20) / np.array([t['r'] for t in tk])) if r['rc_probe'] else None
        row['range_from_true_drr_med_abs_doublings'] = None if e is None else round(float(np.median(np.abs(e))), 2)
        rows.append(row)

    def agg(key, by):
        g = defaultdict(list)
        for x in rows:
            if x[key] is not None:
                g[x[by]].append(x[key])
        return {k: {'median': round(st.median(v), 1), 'median_abs': round(st.median(abs(a) for a in v), 1), 'n': len(v)}
                for k, v in sorted(g.items())}
    out = {'rows': rows,
           'rc_err_pct_by_size': agg('rc_err_pct', 'size'), 'rc_err_pct_by_rt60': agg('rc_err_pct', 'rt60'),
           'rc_err_pct_by_noise': agg('rc_err_pct', 'noise_db'),
           't60_err_pct_by_size': agg('t60_err_pct', 'size'), 't60_err_pct_by_rt60': agg('t60_err_pct', 'rt60'),
           't60_err_pct_by_noise': agg('t60_err_pct', 'noise_db'),
           'sabine_vs_true_rc_pct': round(st.median(100 * (x['rc_sabine'] / x['rc_true'] - 1) for x in rows), 1),
           'true_drr_slope_median': round(st.median(x['true_drr_slope'] for x in rows), 2)}
    q = [x for x in rows if x['noise_db'] >= 20]
    for b in BANDS:
        v = [x[b] for x in q if b in x]
        if v:
            out[f'talkers_{b}'] = {k: round(st.median(y[k] for y in v if y.get(k) is not None), 2)
                                   for k in v[0] if any(y.get(k) is not None for y in v)}
    out['range_from_true_drr_med_abs_doublings'] = round(st.median(x['range_from_true_drr_med_abs_doublings'] for x in q), 2)
    open(sys.argv[2], 'w').write(json.dumps(out, indent=1))
    print(json.dumps({k: v for k, v in out.items() if k != 'rows'}, indent=1))
    for x in rows:
        print(x['size'], x['rt60'], x['noise_db'], 'rc', x['rc_true'], x['rc_sabine'], x['rc_probe'], x['rc_err_pct'], 't60', x['t60_true'],
              x['t60_probe'], x['t60_err_pct'], 'drr slope', x['true_drr_slope'], 'ALL', x.get('ALL'))


if __name__ == '__main__':
    main()
