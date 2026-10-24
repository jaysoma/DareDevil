#!/usr/bin/env python3
"""Per-hop band powers for brief G (2026-10-24): band_windows.py's estimator, kept at every 10.7 ms hop instead of
summed into 0.5 s windows, so an utterance (often 1-3 s) and the Conductor's 0.13-0.5 s range read can be cut out.

THE ESTIMATOR is band_windows.py's, unchanged: cdr_direct.cdr_free_bands over LF_raw 0.1-1.1 kHz (unfloored), B1 1.1-2,
B2 2-4, B3 4-8 kHz (floored at c/2d); NFFT 2048, hop 512, PSD smoothing 0.92. Per hop it gives the direct, diffuse and
total power per band, plus the hop's own (unsmoothed) power over 1.1-8 kHz, which is what the speech mask reads: the
smoothed PSD trails ~130 ms past each word and would bridge the pauses an utterance is cut at.

TWO WAYS TO RUN IT. `tape()` runs it once over the whole tape, warm, as band_windows.py does (cached in .cache/).
`cold()` restarts it at a given sample, as the Conductor does at each onset (conductor.py: "The instrument now starts
cold AT the onset"), so its first SETTLE_S of hops are the estimator's own business.

Audio: the 10 labelled walks are in tapes/<walk>/; the others are on Jay's box at <root>/<audio-input.json file>,
root defaulting to the folder this clone sits in (C:/Projects/GithubRoot, beside Dictate/). A .wav is read with its
header (band_windows.py reads it as raw and gets 11 frames of noise at the start; harmless there, avoided here).
"""
import json
import sys
import wave
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / 'src'))
from geonar.cdr_direct import ALPHA, C, HOP, NFFT, SR  # noqa: E402

BANDS = (('LF_raw', 100.0, 1100.0, False), ('B1', 1100.0, 2000.0, True), ('B2', 2000.0, 4000.0, True),
         ('B3', 4000.0, 8000.0, True))
HOP_S = HOP / SR
CACHE = Path(__file__).with_name('.cache')
ROOT = REPO.parent


def baseline(walk):
    lib = {t['name']: t for t in json.loads((REPO / 'library.json').read_text())['tapes']}
    folded = lib.get(walk, {}).get('folded_deg')
    return 0.157 if not folded else 0.157 * np.sin(np.radians(folded) / 2)   # hinge opening, 180 = flat (fold.json)


def audio(walk, root=ROOT):
    here = sorted((REPO / 'tapes' / walk).glob(walk + '.*'))
    here = [p for p in here if p.suffix in ('.raw', '.wav')]
    p = here[0] if here else Path(root) / json.loads((REPO / 'tapes' / walk / 'audio-input.json').read_text())['file']
    if p.suffix == '.wav':
        with wave.open(str(p)) as w:
            assert (w.getframerate(), w.getnchannels(), w.getsampwidth()) == (SR, 2, 2), p
            b = w.readframes(w.getnframes())
    else:
        b = p.read_bytes()
    return np.frombuffer(b, dtype='<i2').reshape(-1, 2).astype(np.float32) / 32768.0


def run(x, d):
    """x (n, 2). Returns per-hop D, R, P (hops, 4 bands) and the hop's own 1.1-8 kHz power E (hops,)."""
    n = (len(x) - NFFT) // HOP + 1
    f = np.fft.rfftfreq(NFFT, 1.0 / SR)
    gn = np.sinc(2 * f * d / C)
    floor = C / (2 * d)
    masks = np.array([(f >= (max(lo, floor) if fl else lo)) & (f < hi) for _, lo, hi, fl in BANDS], float)
    emask = ((f >= 1100) & (f < 8000)).astype(float)
    win = np.hanning(NFFT)
    D = np.zeros((n, len(BANDS))); R = np.zeros_like(D); P = np.zeros_like(D); E = np.zeros(n)
    psd = None
    for c0 in range(0, n, 2048):
        idx = np.arange(c0, min(n, c0 + 2048))
        seg = np.stack([x[i * HOP:i * HOP + NFFT] for i in idx])
        X1 = np.fft.rfft(seg[:, :, 0] * win, axis=1); X2 = np.fft.rfft(seg[:, :, 1] * win, axis=1)
        a11, a22, a12 = np.abs(X1) ** 2, np.abs(X2) ** 2, X1 * np.conj(X2)
        p11 = np.empty_like(a11); p22 = np.empty_like(a22); p12 = np.empty_like(a12)
        for j in range(len(idx)):
            if psd is None:
                psd = [a11[j], a22[j], a12[j]]
            else:
                psd = [ALPHA * psd[0] + (1 - ALPHA) * a11[j], ALPHA * psd[1] + (1 - ALPHA) * a22[j],
                       ALPHA * psd[2] + (1 - ALPHA) * a12[j]]
            p11[j], p22[j], p12[j] = psd
        gx = p12 / (np.sqrt(p11 * p22) + 1e-20)
        xx, rr = np.abs(gx) ** 2, np.real(gx)
        disc = np.maximum(gn ** 2 * rr ** 2 - gn ** 2 * xx + gn ** 2 - 2 * gn * rr + xx, 0.0)
        cdr = np.clip((xx - gn * rr + np.sqrt(disc)) / np.maximum(1 - xx, 1e-6), 0.0, 1e4)
        frac, pw = cdr / (1 + cdr), 0.5 * (p11 + p22)
        D[idx] = (frac * pw) @ masks.T; R[idx] = ((1 - frac) * pw) @ masks.T; P[idx] = pw @ masks.T
        E[idx] = (0.5 * (a11 + a22)) @ emask
    return D, R, P, E


def tape(walk, root=ROOT):
    """The whole tape, warm. Cached: .cache/<walk>.npz."""
    CACHE.mkdir(exist_ok=True)
    p = CACHE / (walk + '.npz')
    if p.exists():
        z = np.load(p)
        return {k: z[k] for k in z.files}
    x = audio(walk, root)
    D, R, P, E = run(x, baseline(walk))
    np.savez(p, D=D, R=R, P=P, E=E)
    return dict(D=D, R=R, P=P, E=E)


def cold(x, d, i0, i1):
    """Hops i0..i1 (tape hop indices) re-run from a cold estimator started at hop i0's first sample."""
    D, R, P, _ = run(x[i0 * HOP:(i1 - 1) * HOP + NFFT], d)
    return D, R, P
