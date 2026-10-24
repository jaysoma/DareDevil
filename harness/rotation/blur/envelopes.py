#!/usr/bin/env python3
"""Band energy envelopes per mic, and the pair's direct part, for brief B (the blur, in time) (2026-10-24).

Per tape, two things, cached in harness/rotation/blur/.cache/<walk>.npz (not pushed; rebuilt from the audio):

  E    (n_ms, 2 mics, len(BANDS)) energy in 1 ms bins of each band, from a zero-phase Butterworth band-pass
       (order 4, run forward and back, so the bands keep their timing against each other: a causal 250 Hz octave
       lags an 8 kHz one by several ms, which would fake the lag check and the onset colour).
  Dh   (n_hops, len(DBANDS)) the pair's direct power per hop (hop 512, 10.7 ms), and Th the total: the CDR's direct
       fraction per bin (cdr_free_bands' estimator: NFFT 2048, PSD smoothing 0.92, direction-free) times the hop's
       INSTANTANEOUS power, both mics' mean. The fraction comes from PSDs with ~130 ms of memory, so it can only follow
       the envelope at ~1.2 Hz and below; the 2-8 Hz movement of the direct part is mostly the instantaneous power's.
       Bands at or below c/2d (1.1 kHz on 157 mm) are ill-conditioned, so only 2, 4, 8 kHz octaves and 4-8 kHz here.

    py -3.12 harness/rotation/blur/envelopes.py              # the 10 labelled walks and the ladder walks
    py -3.12 harness/rotation/blur/envelopes.py walk-231705  # just these

Audio: tapes/<walk>/<walk>.raw|.wav in the repo, else Dictate/captures/geonar/tapes/ on Jay's box (walk-020305).
"""
import json
import sys
from pathlib import Path

import numpy as np
from scipy.signal import butter, lfilter, sosfiltfilt

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / 'src'))
from geonar.cdr_direct import ALPHA, C, HOP, NFFT, SR  # noqa: E402

CAP = Path(r'C:\Projects\GithubRoot\Dictate\captures\geonar\tapes')
CACHE = Path(__file__).resolve().parent / '.cache'
OCT = (250, 500, 1000, 2000, 4000, 8000)
BANDS = [(f'oct{f}', f / 2 ** .5, f * 2 ** .5) for f in OCT] + [('lo', 250., 1000.), ('hi', 4000., 8000.)]
DBANDS = [('oct2000', 2000 / 2 ** .5, 2000 * 2 ** .5), ('oct4000', 4000 / 2 ** .5, 4000 * 2 ** .5),
          ('oct8000', 8000 / 2 ** .5, 8000 * 2 ** .5), ('hi', 4000., 8000.)]
MS = SR // 1000
WALKS = ['walk-231921', 'walk-231705', 'walk-125621', 'walk-171645', 'walk-215800', 'walk-122038', 'walk-030615',
         'walk-224302', 'walk-213304', 'walk-221126', 'walk-020305']


def load(walk):
    """(n, 2) float32 in [-1, 1]. A .wav is read from its own data chunk."""
    for p in (REPO / 'tapes' / walk / f'{walk}.raw', REPO / 'tapes' / walk / f'{walk}.wav',
              CAP / f'{walk}.raw', CAP / f'{walk}.wav'):
        if p.exists():
            b = p.read_bytes()
            if p.suffix == '.wav':
                q = 12
                while q + 8 <= len(b) and b[q:q + 4] != b'data':
                    q += 8 + int.from_bytes(b[q + 4:q + 8], 'little') + (int.from_bytes(b[q + 4:q + 8], 'little') & 1)
                b = b[q + 8:q + 8 + int.from_bytes(b[q + 4:q + 8], 'little')]
            return np.frombuffer(b[:len(b) // 4 * 4], dtype='<i2').reshape(-1, 2).astype(np.float32) / 32768, p
    raise FileNotFoundError(walk)


def band_energy(x):
    n = len(x) // MS
    E = np.zeros((n, 2, len(BANDS)), np.float32)
    for j, (_, lo, hi) in enumerate(BANDS):
        sos = butter(4, [lo, min(hi, 0.95 * SR / 2)], btype='band', fs=SR, output='sos')
        for m in range(2):
            y = sosfiltfilt(sos, x[:, m].astype(np.float64))
            E[:, m, j] = (y[:n * MS] ** 2).reshape(n, MS).sum(1)
    return E


def direct_part(x, baseline_m):
    n = (len(x) - NFFT) // HOP + 1
    f = np.fft.rfftfreq(NFFT, 1.0 / SR)
    gn = np.sinc(2 * f * baseline_m / C)
    masks = np.array([(f >= lo) & (f < hi) for _, lo, hi in DBANDS], float)
    win = np.hanning(NFFT)
    Dh = np.zeros((n, len(DBANDS))); Th = np.zeros_like(Dh)
    zi = None
    for c0 in range(0, n, 2048):
        idx = np.arange(c0, min(n, c0 + 2048))
        seg = np.stack([x[i * HOP:i * HOP + NFFT] for i in idx])
        X1 = np.fft.rfft(seg[:, :, 0] * win, axis=1); X2 = np.fft.rfft(seg[:, :, 1] * win, axis=1)
        a = np.stack([np.abs(X1) ** 2, np.abs(X2) ** 2, X1 * np.conj(X2)])          # (3, k, bins)
        if zi is None:
            zi = ALPHA * a[:, :1]                                                     # first hop's PSD = its own frame
        psd, zi = lfilter([1 - ALPHA], [1, -ALPHA], a, axis=1, zi=zi)              # band_windows' per-hop recursion
        gx = psd[2] / (np.sqrt(np.real(psd[0]) * np.real(psd[1])) + 1e-20)
        xx, rr = np.abs(gx) ** 2, np.real(gx)
        disc = np.maximum(gn ** 2 * rr ** 2 - gn ** 2 * xx + gn ** 2 - 2 * gn * rr + xx, 0.0)
        cdr = np.clip((xx - gn * rr + np.sqrt(disc)) / np.maximum(1 - xx, 1e-6), 0.0, 1e4)
        inst = 0.5 * np.real(a[0] + a[1])
        Dh[idx] = (cdr / (1 + cdr) * inst) @ masks.T; Th[idx] = inst @ masks.T
    return Dh, Th


def main():
    CACHE.mkdir(exist_ok=True)
    lib = {t['name']: t for t in json.loads((REPO / 'library.json').read_text())['tapes']}
    for w in sys.argv[1:] or WALKS:
        out = CACHE / f'{w}.npz'
        if out.exists():
            print(w, 'cached'); continue
        x, src = load(w)
        folded = lib.get(w, {}).get('folded_deg')
        baseline = 0.157 if not folded else 0.157 * np.sin(np.radians(folded) / 2)
        E = band_energy(x)
        Dh, Th = direct_part(x, baseline)
        np.savez_compressed(out, E=E, Dh=Dh.astype(np.float32), Th=Th.astype(np.float32), baseline_m=baseline)
        print(w, f'{len(x) / SR:.0f} s from {src.name}', flush=True)


if __name__ == '__main__':
    main()
