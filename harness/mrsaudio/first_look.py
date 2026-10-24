#!/usr/bin/env python3
"""MRSAudio (MRSSpeech) first look, 2026-10-23.

40 random utterances from each of three dramas that have audio uploaded, their pose files, and a plain GCC-PHAT delay
per utterance (a quick estimator written here, not GccPhat.mjs). Needs file_index.parquet from the dataset root
(https://huggingface.co/datasets/verstar/MRSAudio, CC BY 4.0 on the card) and pyarrow.

    python3 first_look.py <folder with file_index.parquet>

Layout found: MRSSpeech/<drama>/<drama>_缩混_cut_<start>_<end>_<A|B>.wav is one utterance, 2-channel binaural at
48 kHz; the .npy beside it is the talker's position, one row per 50 ms: x, y, z (m, from the head), time in the
whole recording (ms), and a tag number. x is the ear axis.
"""
import os
import subprocess
import sys
import urllib.parse
from concurrent.futures import ThreadPoolExecutor

import numpy as np
import pandas as pd
import soundfile as sf

B = "https://huggingface.co/datasets/verstar/MRSAudio/resolve/main/"
C = 343.0


def get(src, dst):
    if not os.path.exists(dst):
        subprocess.run(["curl", "-sSL", "-m", "120", "-o", dst, B + urllib.parse.quote(src)], check=True)
    return dst


def tdoa(x, sr, n=1024, lo=200, hi=6000, up=16, maxs=1.2e-3):
    """Left-minus-right delay (s) over the utterance's louder half of frames, PHAT-weighted, 200 Hz-6 kHz."""
    w = np.hanning(n)
    fr = np.lib.stride_tricks.sliding_window_view(x, n, axis=0)[::n // 2]
    X = np.fft.rfft(fr * w, axis=-1)
    p = (np.abs(X[:, 0]) ** 2 + np.abs(X[:, 1]) ** 2).sum(-1)
    keep = p >= np.quantile(p, 0.5)
    S = (X[keep, 0] * np.conj(X[keep, 1])).sum(0)
    f = np.fft.rfftfreq(n, 1 / sr)
    S[(f < lo) | (f > hi)] = 0
    S = S / (np.abs(S) + 1e-20)
    cc = np.fft.irfft(S, n * up)
    L = int(maxs * sr * up)
    cc = np.concatenate([cc[-L:], cc[:L + 1]])
    return (np.argmax(cc) - L) / (sr * up)


def main(folder):
    os.chdir(folder)
    d = pd.read_parquet('file_index.parquet')
    sp = d[d.relative_path.str.startswith('MRSSpeech')]
    dramas = sp.relative_path.str.split('/').str[1].unique()
    print(len(dramas), 'dramas with audio in the index')
    os.makedirs('cuts', exist_ok=True)
    rows = []
    for k, dr in enumerate(dramas[[0, 20, 45]]):
        wavs = sp[sp.relative_path.str.contains('/' + dr + '/', regex=False)].relative_path.tolist()
        sel = np.random.default_rng(k).choice(wavs, size=min(40, len(wavs)), replace=False)
        jobs = [j for i, w in enumerate(sel) for j in ((w, f'cuts/{k}_{i}.wav'), (w[:-4] + '.npy', f'cuts/{k}_{i}.npy'))]
        with ThreadPoolExecutor(8) as ex:
            list(ex.map(lambda j: get(*j), jobs))
        for i, w in enumerate(sel):
            a = np.load(f'cuts/{k}_{i}.npy')
            x, sr = sf.read(f'cuts/{k}_{i}.wav')
            rows.append(dict(drama=k, cut=w.split('/')[-1], x=a[:, 0].mean(), y=a[:, 1].mean(), z=a[:, 2].mean(),
                             move=float(np.hypot(*(a[:, :2].max(0) - a[:, :2].min(0)))), tau_ms=tdoa(x, sr) * 1e3))
    r = pd.DataFrame(rows)
    r['dist'] = np.hypot(r.x, r.y)
    r['dist3'] = np.sqrt(r.x ** 2 + r.y ** 2 + r.z ** 2)
    print(f"{len(r)} utterances; horizontal distance 10/50/90th pct {np.round(np.percentile(r.dist, [10, 50, 90]), 2)} m,"
          f" max {r.dist.max():.2f}; within 1.5 m {(r.dist <= 1.5).mean() * 100:.0f}%")
    st = r[r.move < 0.2].copy()
    th = np.arcsin(np.clip(st.x / st.dist3, -1, 1))
    for lab, s in (('y', st.y / st.dist3), ('x', st.x / st.dist3)):
        print(f"delay against {lab}/r, {len(st)} standing still: corr {np.corrcoef(s, st.tau_ms)[0, 1]:+.2f}")
    for name, g in (('free field', lambda t, p: p * np.sin(t)), ('rigid head (Woodworth)', lambda t, p: p * (t + np.sin(t)))):
        p = min((np.abs(st.tau_ms - g(th, q)).mean(), q) for q in np.linspace(0.1, 0.8, 701))[1]
        grid = np.radians(np.linspace(-90, 90, 3601))
        rd = np.degrees(grid[np.argmin(np.abs(g(grid, p)[None, :] - st.tau_ms.values[:, None]), axis=1)])
        err = np.abs(rd - np.degrees(th))
        out = err > 20
        print(f"{name}, fitted {p:.3f} ms: {out.sum()} of {len(err)} off by >20 deg; the rest mean {err[~out].mean():.1f} deg")
    r.to_csv('first_look_rows.csv', index=False)


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else '.')
