#!/usr/bin/env python3
"""Range alongside the angle, on the same LOCATA cuts; nothing here feeds the angle. Scored for consistency, not metres.

Cues per cut (range.jsonl):
  level_db      FiveMsAmplitude's read, in the recording's own scale: 20 log10 of the amplitude of L + R, R turned by GccPhat's locked delay, over the
                5 ms from the onset, 300 Hz-8 kHz (RangeScheme.power, src/range/FiveMsAmplitude.js, in numpy). Louder is
                nearer.
  cdr_db        the direction-free CDR (src/geonar/cdr_direct.py, cdr_free_bands and cdr_free_db, imported) over the half
                second from the onset, with each band's own value in cdr_bands_db. More direct is nearer.
  echo_lag_ms   the strongest real-cepstrum peak at 1-12 ms over the first 30 ms of voice (L + R aligned as above).
                The floor echo's lag shortens with distance, but voiced speech puts its pitch period (2.5-12 ms) in the
                same range: floor_lag_ms (from the tracked geometry, mouth taken 0.12 m below the head marker) is
                written beside it so the report can say which the measurement follows.

Scores (range_summary.json), per pair spacing, cue by cue:
  ordering       the same talker in the same recording; every pair of cuts whose true distances differ by 1.25x
                 (1.15-1.35), 1.5x (1.4-1.6) or 2x (1.8-2.2): the share the cue orders correctly
  repeatability  the same talker within 0.3 m of the same spot: the median absolute difference of the cue, next to the
                 median difference over 2x-distance pairs (the step the cue has to resolve)

usage: python3 range_cues.py WORK_DIR OUT_DIR   (WORK_DIR: cuts_*.jsonl with audio, preds_*.jsonl)
"""
import base64
import itertools
import json
import math
import statistics as st
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'src' / 'geonar'))
from cdr_direct import cdr_free_bands, cdr_free_db, FREE_BANDS  # noqa: E402

SR, C = 48000, 343.0
WIN = 240                       # FiveMsAmplitude's 5 ms
MIC_Z_OFFSET = 0.12             # mouth below the head marker, m (an assumption, stated in the report)
RATIOS = {'1.25x': (1.15, 1.35), '1.5x': (1.4, 1.6), '2x': (1.8, 2.2)}
SPOT_M = 0.3


def five_ms(L, R, on, tau):
    """RangeScheme.power over the 5 ms from the onset, as an amplitude in dB (full scale = 0 dB)."""
    l, r = L[on:on + WIN].astype(float), R[on:on + WIN].astype(float)
    n, scale = len(l), 1 / 32768
    l, r = (l - l.mean()) * scale, (r - r.mean()) * scale
    k = np.arange(n)
    k0, k1 = max(1, math.ceil(300 * n / SR)), min(n // 2 - 1, math.floor(8000 * n / SR))
    Lf, Rf = np.fft.fft(l), np.fft.fft(r)
    P = 0.0
    for kk in range(k0, k1 + 1):
        rot = np.exp(-1j * 2 * np.pi * (kk * SR / n) * tau)
        b = 0.5 * (Lf[kk] + Rf[kk] * rot)
        P += abs(b) ** 2 / (n * n)
    return 20 * math.log10(math.sqrt(2 * P) + 1e-12)


def echo_lag(L, R, on, tau):
    shift = int(round(tau * SR))
    seg_l = L[on:on + int(0.03 * SR)].astype(float)
    seg_r = R[on + shift:on + shift + int(0.03 * SR)].astype(float)
    if len(seg_r) != len(seg_l):
        seg_r = R[on:on + int(0.03 * SR)].astype(float)
    x = (seg_l + seg_r) * np.hanning(len(seg_l))
    X = np.fft.rfft(x, 4096)
    f = np.fft.rfftfreq(4096, 1 / SR)
    logm = np.log(np.abs(X) + 1e-9)
    logm[(f < 300) | (f > 8000)] = logm[(f >= 300) & (f <= 8000)].mean()
    cep = np.fft.irfft(logm)
    q = np.arange(len(cep)) / SR * 1000
    m = (q >= 1.0) & (q <= 12.0)
    return float(q[m][np.argmax(cep[m])])


def floor_lag(head, centre):
    hs, hm = head[2] - MIC_Z_OFFSET, centre[2]
    r = math.hypot(head[0] - centre[0], head[1] - centre[1])
    return (math.hypot(r, hs + hm) - math.hypot(r, hs - hm)) / C * 1000


def main():
    work, out = Path(sys.argv[1]), Path(sys.argv[2])
    preds = {}
    for p in work.glob('preds_*.jsonl'):
        for l in open(p):
            q = json.loads(l)
            preds[q['id']] = q
    rows = []
    for p in sorted(work.glob('cuts_*.jsonl')):
        for l in open(p):
            c = json.loads(l)
            q = preds[c['id']]
            L = np.frombuffer(base64.b64decode(c['L']), '<i2')
            R = np.frombuffer(base64.b64decode(c['R']), '<i2')
            on, d = c['onset_sample'], c['baseline_m']
            deg = q['gcc']['angles'][0] if q.get('gcc') else 0.0
            tau = -math.sin(math.radians(deg)) * d / C          # GccPhat's locked delay, as the app would hand it
            x = np.stack([L, R], 1).astype(float) / 32768
            dirp, difp = cdr_free_bands(x[on:on + SR // 2], d)
            bands = [round(10 * math.log10(max(dirp[:, b].sum(), 1e-30) / max(difp[:, b].sum(), 1e-30)), 2)
                     for b in range(len(FREE_BANDS))]
            head = c['truth']['head']
            rows.append({'id': c['id'], 'scenario': c['scenario'], 'pair_mm': c['pair_mm'],
                         'who': f"{c['set']}/{c['task']}/{c['recording']}/{c['talker']}",
                         'dist_m': c['truth']['dist_m'], 'head': head,
                         'level_db': round(five_ms(L, R, on, tau) + 20 * math.log10(32768 / c['gain']), 2),
                         'cdr_db': round(cdr_free_db(dirp, difp), 2), 'cdr_bands_db': bands,
                         'echo_lag_ms': round(echo_lag(L, R, on, tau), 3),
                         'floor_lag_ms': round(floor_lag(head, c['centre']), 3)})
    with open(out / 'range.jsonl', 'w') as fh:
        for r in rows:
            fh.write(json.dumps(r) + '\n')
    summary = {}
    cues = {'level_db': +1, 'cdr_db': +1, 'echo_lag_ms': +1}       # +1: a larger value means nearer
    for sp in sorted({r['pair_mm'] for r in rows}, reverse=True):
        by = defaultdict(list)
        for r in rows:
            if r['pair_mm'] == sp:
                by[r['who']].append(r)
        s = {}
        for cue, sign in cues.items():
            order = {k: [] for k in RATIOS}
            step, spot = [], []
            for rs in by.values():
                for a, b in itertools.combinations(rs, 2):
                    near, far = (a, b) if a['dist_m'] < b['dist_m'] else (b, a)
                    ratio = far['dist_m'] / max(near['dist_m'], 1e-6)
                    for k, (lo, hi) in RATIOS.items():
                        if lo <= ratio <= hi:
                            order[k].append(sign * (near[cue] - far[cue]) > 0)
                    if 1.8 <= ratio <= 2.2:
                        step.append(abs(near[cue] - far[cue]))
                    if math.dist(a['head'][:2], b['head'][:2]) <= SPOT_M:
                        spot.append(abs(a[cue] - b[cue]))
            s[cue] = {'ordering': {k: {'pairs': len(v), 'correct': round(sum(v) / len(v), 3) if v else None}
                                   for k, v in order.items()},
                      'repeat_median_abs_diff': round(st.median(spot), 2) if spot else None, 'repeat_pairs': len(spot),
                      'step_2x_median_abs_diff': round(st.median(step), 2) if step else None}
        summary[f'{sp}mm'] = s
    fl = [(r['echo_lag_ms'], r['floor_lag_ms']) for r in rows if r['floor_lag_ms'] is not None]
    if fl:
        summary['echo_lag_vs_floor'] = {'n': len(fl), 'within_0.25ms': round(sum(abs(a - b) <= 0.25 for a, b in fl) / len(fl), 3),
                                        'median_abs_diff_ms': round(st.median(abs(a - b) for a, b in fl), 3)}
    (out / 'range_summary.json').write_text(json.dumps(summary, indent=1))
    print(json.dumps(summary, indent=1))


if __name__ == '__main__':
    main()
