#!/usr/bin/env python3
"""Brief A, step 2: direct, diffuse and total power in octave bands, per 0.5 s window, over a whole tape (2026-10-24).

The estimator is band_windows.py's (cdr_direct's direction-free CDR: NFFT 2048, hop 512, PSD smoothing 0.92), run
UNFLOORED over narrow segments that any band can be summed from afterwards:

    88 | 100 | 177 | 354 | 707 | 1100 | 1414 | 2000 | 2828 | 4000 | 8000 Hz

so the octaves 125 (88-177), 250 (177-354), 500 (354-707), 1k (707-1414), 2k (1414-2828) and 4-8 kHz, and the bar's
own bands (0.1-1.1, 1.1-2, 4-8 kHz), are all sums of segments. Below c/2d (1.09 kHz at 157 mm, 1.55 kHz folded to
111 mm) the diffuse field is coherent across the pair too, so the CDR there is ill-conditioned: every segment carries
an `ill_conditioned` flag. Run where the audio is:

    python harness/rotation/colour/octave_windows.py --root C:/Projects/GithubRoot [walk ...]

Writes results/rotation/colour/windows/<walk>.json. Header bytes of a .wav are skipped (read with `wave`).
"""
import argparse
import json
import sys
import wave
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / 'src'))
from geonar.cdr_direct import ALPHA, C, HOP, NFFT, SR  # noqa: E402

EDGES = (88.0, 100.0, 177.0, 354.0, 707.0, 1100.0, 1414.0, 2000.0, 2828.0, 4000.0, 8000.0)
WIN_S = 0.5
CHUNK = 4096
WALKS = ['walk-231921', 'walk-231705', 'walk-125621', 'walk-171645', 'walk-215800', 'walk-122038', 'walk-030615',
         'walk-224302', 'walk-213304', 'walk-221126',                                     # labelled stops
         'walk-020305',                                                                   # ladder (and a turn)
         'walk-160546', 'walk-161331', 'walk-044350', 'walk-140956']                      # continuous turns (171542 is mono)
OUT = REPO / 'results/rotation/colour/windows'


def octave_windows(x, baseline_m):
    """x (n, 2) float. Window start times and per-window, per-segment summed direct, diffuse and total power."""
    n = (len(x) - NFFT) // HOP + 1
    f = np.fft.rfftfreq(NFFT, 1.0 / SR)
    gn = np.sinc(2 * f * baseline_m / C)
    masks = np.array([(f >= lo) & (f < hi) for lo, hi in zip(EDGES[:-1], EDGES[1:])], float)
    per_win = int(round(WIN_S * SR / HOP))
    nw = -(-n // per_win)
    D = np.zeros((nw, len(masks))); R = np.zeros_like(D); P = np.zeros_like(D)
    win = np.hanning(NFFT)
    psd = None
    for c0 in range(0, n, CHUNK):
        idx = np.arange(c0, min(n, c0 + CHUNK))
        seg = np.stack([x[i * HOP:i * HOP + NFFT] for i in idx])
        X1 = np.fft.rfft(seg[:, :, 0] * win, axis=1); X2 = np.fft.rfft(seg[:, :, 1] * win, axis=1)
        a11, a22, a12 = np.abs(X1) ** 2, np.abs(X2) ** 2, X1 * np.conj(X2)
        for j, i in enumerate(idx):
            if psd is None:
                psd = [a11[j], a22[j], a12[j]]
            else:
                psd = [ALPHA * psd[0] + (1 - ALPHA) * a11[j], ALPHA * psd[1] + (1 - ALPHA) * a22[j],
                       ALPHA * psd[2] + (1 - ALPHA) * a12[j]]
            p11, p22, p12 = psd
            gx = p12 / (np.sqrt(p11 * p22) + 1e-20)
            xx, rr = np.abs(gx) ** 2, np.real(gx)
            disc = np.maximum(gn ** 2 * rr ** 2 - gn ** 2 * xx + gn ** 2 - 2 * gn * rr + xx, 0.0)
            cdr = np.clip((xx - gn * rr + np.sqrt(disc)) / np.maximum(1 - xx, 1e-6), 0.0, 1e4)
            frac, pw = cdr / (1 + cdr), 0.5 * (p11 + p22)
            w = i // per_win
            D[w] += masks @ (frac * pw); R[w] += masks @ ((1 - frac) * pw); P[w] += masks @ pw
    return np.arange(nw) * per_win * HOP / SR, D, R, P


def load(meta, root):
    p = REPO / meta['in_repo'] if meta.get('in_repo') else Path(root) / meta['file']
    if p.suffix == '.wav':
        with wave.open(str(p)) as w:
            assert w.getnchannels() == 2 and w.getsampwidth() == 2 and w.getframerate() == SR
            b = w.readframes(w.getnframes())
    else:
        b = p.read_bytes()
    return np.frombuffer(b, '<i2').reshape(-1, 2).astype(np.float32) / 32768.0, p


def db(a):
    return np.round(10 * np.log10(np.maximum(a, 1e-30)), 2).tolist()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('walks', nargs='*')
    ap.add_argument('--root', default='C:/Projects/GithubRoot')
    ap.add_argument('--force', action='store_true')
    a = ap.parse_args()
    lib = {t['name']: t for t in json.loads((REPO / 'library.json').read_text())['tapes']}
    OUT.mkdir(parents=True, exist_ok=True)
    for w in a.walks or WALKS:
        out = OUT / f'{w}.json'
        if out.exists() and not a.force:
            print(w, 'done already'); continue
        x, src = load(json.loads((REPO / 'tapes' / w / 'audio-input.json').read_text()), a.root)
        folded = lib.get(w, {}).get('folded_deg')
        baseline = 0.157 if not folded else 0.157 * np.sin(np.radians(folded) / 2)
        floor = C / (2 * baseline)
        t0, D, R, P = octave_windows(x, baseline)
        doc = {'walk': w, 'source': src.name, 'baseline_m': round(float(baseline), 4), 'c_over_2d_hz': round(floor),
               'win_s': WIN_S,
               'segments': [{'lo_hz': lo, 'hi_hz': hi, 'ill_conditioned': bool(lo < floor)}
                            for lo, hi in zip(EDGES[:-1], EDGES[1:])],
               't0': np.round(t0, 3).tolist(), 'dir_db': db(D), 'dif_db': db(R), 'pow_db': db(P),
               'estimator': 'band_windows.py / cdr_direct direction-free CDR, unfloored, summed per segment and window'}
        out.write_text(json.dumps(doc, separators=(',', ':')))
        print(w, len(t0), 'windows')


if __name__ == '__main__':
    main()
