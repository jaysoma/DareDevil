#!/usr/bin/env python3
"""The decisive test on the phone itself (run where the tapes are: their audio is not in this repo). For each tape's
pauses: the share of GCC-PHAT peaks within 6 deg of 0 at each high-pass, frame by frame and summed over 0.5 s, and the
pause coherence by band -- the same measures as pause_gcc.py, at the phone's 157 mm and 48 kHz.

How to read it:
  diffuse noise    -- Re coherence ~ sinc(2 pi f d / c): about 1 below 300 Hz, falling through 1.1 kHz, ~0 above;
                      the 0 deg share falls when the high-pass reaches 1100 Hz.
  common mode      -- (electrical crosstalk, a shared codec path, one channel copied into the other) Re coherence near 1
                      ABOVE 1.1 kHz too, and the 0 deg share survives every high-pass.
Pauses are the gaps between Whisper segments (tapes/<tape>/transcript.json), GUARD_S clear of each.

    python3 phone_pause.py path/to/tapes_audio_dir [tapes_dir_in_repo] > phone_pause.json
The audio dir holds <tape>.raw (int16 LE, 2 channels interleaved, 48 kHz), as audio-input.json describes.
"""
import json
import sys
from pathlib import Path

import numpy as np

SR, NFFT, HOP, HI_HZ, TAUS, C, D = 48000, 2048, 512, 8000, 241, 343.0, 0.157
HPS = [0, 100, 300, 1100]
NEAR0, GUARD_S, SKIP_START_S = 6.0, 0.5, 1.0
SUM_FRAMES = 47                       # GccPhat.mjs's half second: 47 frame starts
EDGES = [0, 100, 300, 1100, 2500, 8000]


def main():
    audio = Path(sys.argv[1])
    tapes = Path(sys.argv[2]) if len(sys.argv) > 2 else Path(__file__).resolve().parents[2] / 'tapes'
    f = np.fft.rfftfreq(NFFT, 1 / SR)[:int(HI_HZ * NFFT / SR) + 1]
    tau = np.linspace(-D / C, D / C, TAUS)
    deg = np.degrees(np.arcsin(np.clip(-tau * C / D, -1, 1)))
    E = np.exp(-2j * np.pi * np.outer(f, tau))
    win = np.hanning(NFFT + 1)[:-1]
    sinc = np.sinc(2 * f * D / C)
    out = {'baseline_mm': 157, 'near0_deg': NEAR0, 'hps': HPS, 'coherence_edges_hz': EDGES,
           'diffuse_free_field_re': [round(float(sinc[(f >= a) & (f < b) & (f > 0)].mean()), 2) for a, b in zip(EDGES, EDGES[1:])],
           'tapes': {}}

    def near0(P, hp):
        k0 = max(1, int(np.ceil(hp * NFFT / SR)))
        j = np.real(P[:, k0:] @ E[k0:]).argmax(1)
        return round(100 * float((np.abs(deg[j]) < NEAR0).mean()), 1) if len(j) else None

    for td in sorted(tapes.iterdir()):
        raw = audio / f'{td.name}.raw'
        if not raw.exists() or not (td / 'transcript.json').exists():
            continue
        x = np.fromfile(raw, '<i2').reshape(-1, 2).astype(np.float64) / 32768
        segs = json.load(open(td / 'transcript.json'))['segments']
        ok = np.ones(len(x), bool)
        ok[:int(SKIP_START_S * SR)] = False
        for s in segs:
            ok[max(0, int((s['t0'] - GUARD_S) * SR)):int((s['t1'] + GUARD_S) * SR)] = False
        starts = np.array([s for s in range(0, len(x) - NFFT + 1, HOP) if ok[s] and ok[s + NFFT - 1]], int)
        if len(starts) < SUM_FRAMES:
            continue
        seg = np.stack([x[s:s + NFFT] for s in starts]) * win[None, :, None]
        X = np.fft.rfft(seg, axis=1)[:, :len(f)]
        A, B = X[..., 0], X[..., 1]
        S = A * np.conj(B)
        P = S / np.maximum(np.abs(S), 1e-30)
        bl, i = [], 0                                   # non-overlapping runs of SUM_FRAMES consecutive frames
        while i + SUM_FRAMES <= len(starts):
            if starts[i + SUM_FRAMES - 1] - starts[i] == (SUM_FRAMES - 1) * HOP:
                bl.append(i); i += SUM_FRAMES
            else:
                i += 1
        Ss = S[np.array(bl)[:, None] + np.arange(SUM_FRAMES)].sum(1) if bl else S[:0]
        Ps = Ss / np.maximum(np.abs(Ss), 1e-30)
        g = np.real(S.sum(0)) / np.sqrt((np.abs(A) ** 2).sum(0) * (np.abs(B) ** 2).sum(0) + 1e-30)
        out['tapes'][td.name] = {
            'pause_frames': int(len(starts)), 'summed_reads': len(bl),
            'near0_pct_frame': {str(h): near0(P, h) for h in HPS},
            'near0_pct_summed': {str(h): near0(Ps, h) for h in HPS},
            'coherence_re': [round(float(g[(f >= a) & (f < b) & (f > 0)].mean()), 2) for a, b in zip(EDGES, EDGES[1:])]}
        print(td.name, out['tapes'][td.name], file=sys.stderr, flush=True)
    json.dump(out, sys.stdout, indent=1)


if __name__ == '__main__':
    main()
