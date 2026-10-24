#!/usr/bin/env python3
"""Per-hop direct and diffuse powers for brief 21's range policies, from the direction-free CDR.

`cdr_hops` is src/geonar/cdr_direct.py's cdr_free_bands copied unchanged except for one switch: `clamp`. The original
raises every band's low edge to c/2d (the diffuse field is coherent below it), which empties a 0.1-1 kHz band on a
160 mm pair (c/2d = 1.07 kHz). The LF band is computed with clamp=False, as brief 20 asks; the shipped bands keep the
clamp. A window's CDR is the ratio of its summed powers (cdr_free_db's way), so per-hop powers are computed once per
utterance, from the onset with a fresh PSD state (batch A's per-utterance read started the same way).

usage: python3 range_hops.py WORK_DIR   (reads utt_*.jsonl; writes hops_*.npz: per cut, hop powers for each band set:
       shipped, lf (unfloored, as brief 20's LF_raw) and hf)
"""
import base64
import json
import sys
from pathlib import Path

import numpy as np

SR, HOP, NFFT, C, ALPHA = 48000, 512, 2048, 343.0, 0.92            # as src/geonar/cdr_direct.py
SHIPPED = ((1100.0, 2000.0), (2000.0, 4000.0), (4000.0, 8000.0))   # cdr_direct.FREE_BANDS
LF = ((100.0, 1000.0),)
HF = ((4000.0, 8000.0),)                                         # brief 20's HF, for its facing cue (HF - LF)


def cdr_hops(x, baseline_m, bands, clamp=True):
    n = (len(x) - NFFT) // HOP + 1
    win = np.hanning(NFFT)
    f = np.fft.rfftfreq(NFFT, 1.0 / SR)
    Gn = np.sinc(2 * np.pi * f / C * baseline_m / np.pi)
    lo_ok = C / (2 * baseline_m) if clamp else 0.0
    masks = [(f >= max(lo, lo_ok)) & (f < hi) for lo, hi in bands]
    dirp = np.zeros((n, len(bands))); difp = np.zeros((n, len(bands)))
    P11 = P22 = P12 = None
    for i in range(n):
        seg = x[i * HOP:i * HOP + NFFT]
        X1 = np.fft.rfft(seg[:, 0] * win); X2 = np.fft.rfft(seg[:, 1] * win)
        a11, a22, a12 = np.abs(X1) ** 2, np.abs(X2) ** 2, X1 * np.conj(X2)
        if P11 is None:
            P11, P22, P12 = a11, a22, a12
        else:
            P11 = ALPHA * P11 + (1 - ALPHA) * a11; P22 = ALPHA * P22 + (1 - ALPHA) * a22; P12 = ALPHA * P12 + (1 - ALPHA) * a12
        Gx = P12 / (np.sqrt(P11 * P22) + 1e-20)
        X = np.abs(Gx) ** 2; R = np.real(Gx)
        disc = np.maximum(Gn ** 2 * R ** 2 - Gn ** 2 * X + Gn ** 2 - 2 * Gn * R + X, 0.0)
        c = np.clip((X - Gn * R + np.sqrt(disc)) / np.maximum(1 - X, 1e-6), 0.0, 1e4)
        frac = c / (1.0 + c); pw = 0.5 * (P11 + P22)
        for b, m in enumerate(masks):
            dirp[i, b] = (frac * pw)[m].sum(); difp[i, b] = ((1 - frac) * pw)[m].sum()
    return dirp, difp


def window_db(dirp, difp, a, b):
    """cdr_free_db over hops a..b-1: the mean over bands of 10 log10(summed direct / summed diffuse). Bands with no
    power in the window are left out (on the 80 mm pair the shipped 1.1-2 kHz band is empty above c/2d)."""
    d, r = dirp[a:b].sum(0), difp[a:b].sum(0)
    ok = (d > 0) & (r > 0)
    return float(np.mean(10 * np.log10(d[ok] / r[ok]))) if ok.any() else None


def main():
    work = Path(sys.argv[1])
    for p in sorted(work.glob('utt_*.jsonl')):
        arrs = {}
        for l in open(p):
            c = json.loads(l)
            L = np.frombuffer(base64.b64decode(c['L']), '<i2').astype(float)
            R = np.frombuffer(base64.b64decode(c['R']), '<i2').astype(float)
            x = np.stack([L, R], 1)[c['onset_sample']:] / 32768
            key = c['id'].replace('/', '|')
            for name, bands, clamp in (('shipped', SHIPPED, True), ('lf', LF, False), ('hf', HF, True)):
                dp, fp = cdr_hops(x, c['baseline_m'], bands, clamp)
                arrs[f'{key}#{name}#dir'] = dp.astype(np.float32)
                arrs[f'{key}#{name}#dif'] = fp.astype(np.float32)
        np.savez_compressed(work / p.name.replace('utt_', 'hops_').replace('.jsonl', '.npz'), **arrs)
        print(p.name, flush=True)


if __name__ == '__main__':
    main()
