#!/usr/bin/env python3
"""Brief 20: the direction-free CDR per band, as the DRR estimate, from cut audio.

The estimator is src/geonar/cdr_direct.py's cdr_free_bands (Schwarz & Kellermann's DOA-independent CDR), imported for
its constants and restated here with the brief's bands and one change made optional: cdr_free_bands floors every band
at c/2d, the frequency below which a diffuse field is coherent across the pair too and direct and diffuse can't be told
apart. At the phone's 157 mm that's 1.1 kHz, so the brief's LF band (0.1-1 kHz) is empty when floored. Each band is
therefore read both ways:
  <band>      floored at c/2d, as cdr_direct.py does (None when nothing of the band is left)
  <band>_raw  not floored: the same formula run where it is ill-conditioned (Gn near 1)
Bands: LF 0.1-1 kHz, MF 1-4 kHz, HF 4-8 kHz, ALL 0.1-8 kHz. Direct and diffuse powers are summed over WINDOW
(0.13-0.6 s after the onset, as the Conductor commits) and the ratio taken once, as cdr_free_bands' callers do.
Also per band: the level (dB, both mics' mean power over the same window).

stdin: cuts (JSON lines with L, R base64 int16 at 48 kHz, onset_sample, baseline_m, and any truth fields).
stdout: the same lines without the audio, plus 'cdr' {band: dB}.
usage: <cutter> | python3 drr.py [--keep id,dist_m,...]
"""
import base64
import json
import math
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'src' / 'geonar'))
from cdr_direct import SR, HOP, NFFT, ALPHA, C     # noqa: E402

BANDS = {'LF': (100.0, 1000.0), 'MF': (1000.0, 4000.0), 'HF': (4000.0, 8000.0), 'ALL': (100.0, 8000.0)}
WINDOW = (0.13, 0.6)


def cdr_bands(x, baseline_m, on, bands=BANDS):
    """x (n, 2) float. Per band: floored and unfloored CDR (dB) and level (dB) over WINDOW after sample `on`."""
    win = np.hanning(NFFT)
    f = np.fft.rfftfreq(NFFT, 1.0 / SR)
    Gn = np.sinc(2 * f * baseline_m / C)                       # diffuse coherence sin(kd)/(kd)
    lo_ok = C / (2 * baseline_m)
    i0 = int((on + WINDOW[0] * SR) // HOP)
    i1 = int((on + WINDOW[1] * SR - NFFT) // HOP) + 1
    n = (len(x) - NFFT) // HOP + 1
    masks = {}
    for b, (lo, hi) in bands.items():
        masks[b] = (f >= max(lo, lo_ok)) & (f < hi)
        masks[b + '_raw'] = (f >= lo) & (f < hi)
    D = {k: 0.0 for k in masks}; F = {k: 0.0 for k in masks}; P = {k: 0.0 for k in masks}
    P11 = P22 = P12 = None
    for i in range(min(n, i1)):                                  # the PSDs smooth from the cut's start, as a stream would
        seg = x[i * HOP:i * HOP + NFFT]
        X1 = np.fft.rfft(seg[:, 0] * win); X2 = np.fft.rfft(seg[:, 1] * win)
        a11, a22, a12 = np.abs(X1) ** 2, np.abs(X2) ** 2, X1 * np.conj(X2)
        if P11 is None:
            P11, P22, P12 = a11, a22, a12
        else:
            P11 = ALPHA * P11 + (1 - ALPHA) * a11; P22 = ALPHA * P22 + (1 - ALPHA) * a22; P12 = ALPHA * P12 + (1 - ALPHA) * a12
        if i < i0:
            continue
        Gx = P12 / (np.sqrt(P11 * P22) + 1e-20)
        X = np.abs(Gx) ** 2; R = np.real(Gx)
        disc = np.maximum(Gn ** 2 * R ** 2 - Gn ** 2 * X + Gn ** 2 - 2 * Gn * R + X, 0.0)
        c = np.clip((X - Gn * R + np.sqrt(disc)) / np.maximum(1 - X, 1e-6), 0.0, 1e4)
        frac = c / (1.0 + c); pw = 0.5 * (P11 + P22)
        for k, m in masks.items():
            if m.any():
                D[k] += float((frac * pw)[m].sum()); F[k] += float(((1 - frac) * pw)[m].sum()); P[k] += float(pw[m].sum())
    out = {}
    for k, m in masks.items():
        out[k] = None if not m.any() or D[k] + F[k] <= 0 else round(10 * math.log10(max(D[k], 1e-30) / max(F[k], 1e-30)), 2)
        out['level_' + k] = None if not m.any() or P[k] <= 0 else round(10 * math.log10(P[k]), 2)
    return out


def main():
    for line in sys.stdin:
        if not line.strip():
            continue
        c = json.loads(line)
        L = np.frombuffer(base64.b64decode(c.pop('L')), dtype='<i2').astype(float) / 32768
        R = np.frombuffer(base64.b64decode(c.pop('R')), dtype='<i2').astype(float) / 32768
        c['cdr'] = cdr_bands(np.stack([L, R], axis=1), c['baseline_m'], c['onset_sample'])
        sys.stdout.write(json.dumps(c) + '\n')


if __name__ == '__main__':
    main()
