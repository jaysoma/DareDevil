#!/usr/bin/env python3
"""Batch A range, alongside the angle and never feeding it: three cues per onset, from the same cut audio.

  five_ms     FiveMsAmplitude's read (src/range/FiveMsAmplitude.js, power() ported): the power of L + R with R turned
              by GccPhat's locked delay, 300 Hz-8 kHz, over the 5 ms from the onset (the stream's first vote, one step
              after the read start). The cue is 1 / amplitude: louder is nearer.
  cdr_db      the direction-free CDR (src/geonar/cdr_direct.py, cdr_free_bands), direct and diffuse powers summed from
              0.13 s to 0.6 s after the onset as the Conductor does, 10 log10(direct / diffuse) per band, then the mean
              over the bands that lie above c/2d (for STARSS's 68.5 mm pairs only 4-8 kHz and the top of 2-4 kHz do).
  echo_ms     the strongest early echo's lag, 1-12 ms: the peak of the real cepstrum, averaged over both channels and
              over the frames of the onset's first 300 ms. A floor or ceiling echo is a cepstral peak at its lag; so is
              the voice's pitch period, which is why brief 6 asks first whether the echo can be found at all.

stdin: cut_all.py's stream for one pair. argv: that pair's raw_XY.jsonl (for GccPhat's locked delay).
usage: cut_all.py ROOT --pair 1 2 | range_cues.py raw_12.jsonl > range_12.jsonl
       range_cues.py --score <work dir> <out json>
"""
import base64
import json
import math
import statistics as st
import sys
from collections import defaultdict
from itertools import combinations
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'src' / 'geonar'))
from cdr_direct import cdr_free_bands, FREE_BANDS, HOP as CDR_HOP, NFFT as CDR_NFFT   # noqa: E402

SR, C = 48000, 343.0
WIN5 = 240
CEP_N, CEP_HOP, CEP_S = 2048, 512, 0.3


def five_ms(L, R, at, tau_s):
    """FiveMsAmplitude.power over L/R[at:at+240], ported: per-bin DFT, R turned by tau, 300 Hz-8 kHz; amplitude sqrt(2P)."""
    l, r = L[at:at + WIN5].astype(float), R[at:at + WIN5].astype(float)
    n = len(l)
    l, r = (l - l.mean()) / 32768, (r - r.mean()) / 32768
    k0, k1 = max(1, math.ceil(300 * n / SR)), min((n >> 1) - 1, math.floor(8000 * n / SR))
    lf, rf = np.fft.fft(l), np.fft.fft(r)                    # e^-j, as the JS loop
    k = np.arange(k0, k1 + 1)
    rot = np.exp(-1j * 2 * np.pi * (k * SR / n) * tau_s)
    b = 0.5 * (lf[k] + rf[k] * rot)
    P = float(np.sum(np.abs(b) ** 2) / (n * n))
    return math.sqrt(2 * P)


def cdr(x, d, on):
    dirp, difp = cdr_free_bands(x, d)
    i0 = int((on + 0.13 * SR) // CDR_HOP)
    i1 = int((on + 0.6 * SR - CDR_NFFT) // CDR_HOP) + 1
    D, F = dirp[i0:i1].sum(axis=0), difp[i0:i1].sum(axis=0)
    per = [None if (D[b] + F[b]) <= 0 else round(10 * math.log10(max(D[b], 1e-30) / max(F[b], 1e-30)), 2) for b in range(len(FREE_BANDS))]
    v = [p for p in per if p is not None]
    return (round(sum(v) / len(v), 2) if v else None), per


def echo(x, on):
    w = np.hanning(CEP_N)
    lo, hi = int(0.001 * SR), int(0.012 * SR)
    acc = np.zeros(CEP_N)
    k = 0
    for s in range(on, on + int(CEP_S * SR) - CEP_N + 1, CEP_HOP):
        for ch in (0, 1):
            X = np.fft.rfft(x[s:s + CEP_N, ch] * w)
            acc += np.fft.irfft(np.log(np.abs(X) + 1e-9), CEP_N)
            k += 1
    acc /= max(k, 1)
    q = int(np.argmax(acc[lo:hi])) + lo
    return round(q / SR * 1000, 3), round(float(acc[q] / (np.std(acc[lo:hi]) + 1e-12)), 2)


def run(raw_path):
    raw = {}
    for l in open(raw_path):
        r = json.loads(l)
        raw[r['id']] = r
    for line in sys.stdin:
        c = json.loads(line)
        i16 = lambda s: np.frombuffer(base64.b64decode(s), dtype='<i2')
        L, R = i16(c['L']), i16(c['R'])
        on_s = str(int(c['onset_s'])) if float(c['onset_s']).is_integer() else repr(float(c['onset_s']))   # as runner.mjs prints it
        cid = f"{''.join(map(str, c['pair']))}/{c['file']}/{on_s}/{c['cls']}/{c['src']}"
        g = raw.get(cid, {}).get('gcc') or {}
        d, on = c['baseline_m'], c['onset_sample']
        out = {'id': cid, 'file': c['file'], 'room': c['room'], 'cls': c['cls'], 'kind': c['kind'], 'src': c['src'], 'solo': c['solo'],
               'az': c['az'], 'el': c['el'], 'dist_m': None if c['dist_cm'] is None else c['dist_cm'] / 100}
        if g.get('angles'):
            tau = -math.sin(math.radians(g['angles'][0])) * d / C
            amp = five_ms(L, R, on, tau)
            out['five_ms_amp'] = amp
            out['five_ms_inv'] = None if amp <= 0 else round(1 / amp, 4)
        x = np.stack([L, R], axis=1).astype(float) / 32768
        out['cdr_db'], out['cdr_bands'] = cdr(x, d, on)
        out['echo_ms'], out['echo_peak'] = echo(x, on)
        sys.stdout.write(json.dumps(out) + '\n')


def xyz(r):
    a, e = math.radians(r['az']), math.radians(r['el'])
    return np.array([math.cos(e) * math.cos(a), math.cos(e) * math.sin(a), math.sin(e)]) * r['dist_m']


CUES = {'1 / amplitude, first 5 ms': ('five_ms_inv', +1, 'log'), 'direction-free CDR': ('cdr_db', -1, 'lin'),
        'early echo lag': ('echo_ms', -1, 'lin')}


def score(W, outp):
    rows = defaultdict(list)
    for p in Path(W).glob('range_*.jsonl'):
        pair = p.stem.split('_')[1]
        for l in open(p):
            r = json.loads(l)
            if r['kind'] == 'speech' and r['dist_m']:
                rows[(pair, r['file'], r['cls'], r['src'])].append(r)
    res = {'talker': 'one file, one speech class, one source index (STARSS has no talker identity across files)', 'cues': {}}
    for name, (key, sign, scale) in CUES.items():
        order = {1.25: [0, 0], 1.5: [0, 0], 2.0: [0, 0]}
        same, far = [], []
        for grp in rows.values():
            for a, b in combinations(grp, 2):
                va, vb = a.get(key), b.get(key)
                if va is None or vb is None or va <= 0 and scale == 'log':
                    continue
                ra = max(a['dist_m'], b['dist_m']) / min(a['dist_m'], b['dist_m'])
                diff = (math.log10(va / vb) * 20 if scale == 'log' else va - vb)
                if ra >= 1.25 and va != vb:
                    nearer_a = a['dist_m'] < b['dist_m']
                    right = (diff * sign < 0) if nearer_a else (diff * sign > 0)
                    for th in order:
                        if ra >= th:
                            order[th][0] += right; order[th][1] += 1
                if np.linalg.norm(xyz(a) - xyz(b)) <= 0.3:
                    same.append(abs(diff))
                if ra >= 2.0:
                    far.append(abs(diff))
        res['cues'][name] = {
            'unit': 'dB' if scale == 'log' or key == 'cdr_db' else 'ms',
            'ordering': {f'{th}x': {'pairs': n, 'correct_pct': round(100 * k / n, 1) if n else None} for th, (k, n) in order.items()},
            'repeatability_same_spot_0.3m': {'pairs': len(same), 'median_abs_diff': round(st.median(same), 2) if same else None,
                                             'p90_abs_diff': round(float(np.percentile(same, 90)), 2) if same else None},
            'difference_at_2x_distance': {'pairs': len(far), 'median_abs_diff': round(st.median(far), 2) if far else None}}
    lags = [r['echo_ms'] for g in rows.values() for r in g if r.get('echo_ms') is not None]
    res['echo_lag_ms_histogram'] = {f'{lo}-{lo + 1}': sum(lo <= v < lo + 1 for v in lags) for lo in range(1, 12)}
    Path(outp).write_text(json.dumps(res, indent=1))
    print(json.dumps(res, indent=1))


if __name__ == '__main__':
    if sys.argv[1] == '--score':
        score(sys.argv[2], sys.argv[3])
    else:
        run(sys.argv[1])
