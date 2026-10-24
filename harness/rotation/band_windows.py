#!/usr/bin/env python3
"""Per-band direct, diffuse and total power in 0.5 s windows over a whole tape, for the facing test (2026-10-24).

Run on Jay's box, where the raw tapes are; it writes a small tapes/<walk>/band_windows.json (~100 KB) to push. The cloud
sessions then line the windows up with the decode's callouts ("rotated 90 degrees clockwise", "facing away") without
the audio.

    python3 harness/rotation/band_windows.py --root ~                 # every rotation walk in library.json
    python3 harness/rotation/band_windows.py --root ~ walk-213304     # just these

--root is what audio-input.json's `file` is relative to (Dictate/captures/geonar/tapes/<walk>.raw). A tape already
done is skipped unless --force.

WHY WINDOWS AND NOT UTTERANCES. Brief 20 found the facing cue is real on LOCATA (HF - LF of the CDR drops 2.3-3.7 dB when
the talker faces away) but per-read jitter (about 3 dB over a 0.47 s read) hides it, and LOCATA's talkers walk, so reads
couldn't be pooled at one spot. These walks stand, turn and talk. Summing the powers over several seconds at one spot
and one facing is the untested lever, and windows let any span be summed afterwards.

THE ESTIMATOR is src/geonar/cdr_direct.py's cdr_free_bands (the Conductor's range estimator: NFFT 2048, hop 512,
PSD smoothing 0.92, Schwarz & Kellermann's direction-free CDR), run here over four bands:
    LF_raw  0.1-1.1 kHz, NOT floored at c/2d (brief 20's phone-pair LF: ill-conditioned, but the band facing moves least)
    B1      1.1-2 kHz    B2  2-4 kHz    B3  4-8 kHz     (the Conductor's three, floored at c/2d)
Total power (`pow`, both mics' mean) is kept too, so the received spectrum's own tilt can be tried beside the CDR's.
The direction-free CDR is symmetric in the two channels, so the tape's channel order doesn't matter.
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / 'src'))
from geonar.cdr_direct import ALPHA, C, HOP, NFFT, SR  # noqa: E402

BANDS = (('LF_raw', 100.0, 1100.0, False), ('B1', 1100.0, 2000.0, True), ('B2', 2000.0, 4000.0, True),
         ('B3', 4000.0, 8000.0, True))
WIN_S = 0.5
CHUNK = 4096                                     # hops per batch of FFTs


def band_windows(x, baseline_m):
    """x (n, 2) float in [-1, 1]. Returns window start times (s) and per-window, per-band summed powers."""
    n = (len(x) - NFFT) // HOP + 1
    f = np.fft.rfftfreq(NFFT, 1.0 / SR)
    gn = np.sinc(2 * f * baseline_m / C)
    floor = C / (2 * baseline_m)
    masks = np.array([(f >= (max(lo, floor) if fl else lo)) & (f < hi) for _, lo, hi, fl in BANDS], float)  # (4, bins)
    per_win = int(round(WIN_S * SR / HOP))
    nw = -(-n // per_win)
    D = np.zeros((nw, len(BANDS))); R = np.zeros_like(D); P = np.zeros_like(D); N = np.zeros(nw, int)
    win = np.hanning(NFFT)
    psd = None
    for c0 in range(0, n, CHUNK):
        idx = np.arange(c0, min(n, c0 + CHUNK))
        seg = np.stack([x[i * HOP:i * HOP + NFFT] for i in idx])               # (k, NFFT, 2)
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
            D[w] += masks @ (frac * pw); R[w] += masks @ ((1 - frac) * pw); P[w] += masks @ pw; N[w] += 1
    return np.arange(nw) * per_win * HOP / SR, D, R, P, N


def db(a):
    return np.round(10 * np.log10(np.maximum(a, 1e-30)), 2).tolist()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('walks', nargs='*')
    ap.add_argument('--root', default=str(Path.home()))
    ap.add_argument('--force', action='store_true')
    a = ap.parse_args()
    lib = {t['name']: t for t in json.loads((REPO / 'library.json').read_text())['tapes']}
    walks = a.walks or [k for k, t in lib.items() if t.get('rotation')]
    for w in walks:
        out = REPO / 'tapes' / w / 'band_windows.json'
        if out.exists() and not a.force:
            print(w, 'done already'); continue
        meta = json.loads((REPO / 'tapes' / w / 'audio-input.json').read_text())
        raw = Path(a.root).expanduser() / meta['file']
        if not raw.exists():
            print(w, 'no audio at', raw); continue
        x = np.fromfile(raw, dtype='<i2').reshape(-1, 2).astype(np.float32) / 32768.0
        folded = lib.get(w, {}).get('folded_deg')
        baseline = 0.157 if not folded else 2 * 0.0785 * np.sin(np.radians(180 - folded) / 2)
        t0, D, R, P, N = band_windows(x, baseline)
        doc = {'walk': w, 'baseline_m': round(float(baseline), 4), 'win_s': WIN_S, 'hops': N.tolist(),
               'bands': [{'name': b, 'lo_hz': lo, 'hi_hz': hi, 'floored': fl} for b, lo, hi, fl in BANDS],
               't0': np.round(t0, 3).tolist(), 'dir_db': db(D), 'dif_db': db(R), 'pow_db': db(P),
               'estimator': 'cdr_direct.cdr_free_bands over these bands; powers summed per window, in dB'}
        out.write_text(json.dumps(doc, separators=(',', ':')))
        print(w, len(t0), 'windows ->', out.relative_to(REPO))


if __name__ == '__main__':
    main()
