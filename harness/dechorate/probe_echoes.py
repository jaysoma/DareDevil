#!/usr/bin/env python3
"""Walls from the phone's own announcement, tried on dEchorate's measured rooms (2026-10-24).

The announcement (probe/daredevil_mode_activated.wav, 1.4 s of TTS) is played through each measured response of the
155 mm pair (dEchorate's mics 0 and 3 of an array, all 6 sources, all 11 wall settings), with noise 45 dB under it.
It is then divided back out (regularised deconvolution: the signal is known, the room is not) to recover the room's
response, and the echoes are picked from that. The same picking runs on the true measured response, so the probe's
own loss is separated from the picking's. Labelled echoes are bake.py's (results/animation/dechorate/<setting>.json:
image-source delays after the direct path and the pair's angle to each, per surface, with whether the surface is
reflective in that setting). An echo is found when a picked peak lies within 0.35 ms of its labelled delay.

dEchorate's loudspeakers stand 1-4 m from the arrays; on the phone the speaker is on the array, so there every echo's
delay is simply twice the wall's distance over c.

    python3 probe_echoes.py <dechorate_rir_processed.hdf5>
"""
import json
import sys
from pathlib import Path

import h5py
import numpy as np
import soundfile as sf
from scipy.signal import butter, hilbert, sosfiltfilt

REPO = Path(__file__).resolve().parents[2]
SR, C, D = 48000, 343.0, 0.155
INVERTED = (0, 5, 17, 20, 23, 28)
SOS = butter(4, [300, 8000], btype='band', fs=SR, output='sos')


def deconv(y, p, lam=1e-3):
    n = 1 << int(np.ceil(np.log2(len(y) + len(p))))
    Y, P = np.fft.rfft(y, n), np.fft.rfft(p, n)
    return np.fft.irfft(Y * np.conj(P) / (np.abs(P) ** 2 + lam * np.mean(np.abs(P) ** 2)), n)


def peaks(hl, hr, sign):
    env = np.abs(hilbert(hl)) + np.abs(hilbert(hr))
    k = np.ones(5) / 5
    env = np.convolve(env, k, 'same')
    t0 = int(np.argmax(env[:SR // 10]))
    lo, hi = t0 + int(0.0008 * SR), t0 + int(0.025 * SR)
    seg = env[lo:hi]
    cand = [i for i in range(1, len(seg) - 1) if seg[i] >= seg[i - 1] and seg[i] >= seg[i + 1]
            and seg[i] >= env[t0] * 10 ** (-25 / 20)]
    cand.sort(key=lambda i: -seg[i])
    out, sep = [], int(0.0004 * SR)
    for i in cand:
        if all(abs(i - j) >= sep for j, _ in out):
            out.append((i, seg[i]))
        if len(out) == 8:
            break
    res = []
    L = int(0.0005 * SR); up = 16
    for i, a in out:
        c = lo + i
        wl, wr = hl[c - L:c + L], hr[c - L:c + L]
        n = 4 * L * up
        cc = np.fft.irfft(np.fft.rfft(wl, n) * np.conj(np.fft.rfft(wr, n)), n)
        m = int(D / C * SR * up) + up
        cc = np.concatenate([cc[-m:], cc[:m + 1]])
        tau = (np.argmax(cc) - m) / (SR * up)
        deg = float(np.degrees(np.arcsin(np.clip(sign * tau * C / D, -1, 1))))
        res.append({'delay_ms': (c - t0) / SR * 1e3, 'deg': deg, 'db': 20 * np.log10(a / env[t0])})
    return res, t0


def main(h5):
    probe, sr = sf.read(REPO / 'probe/daredevil_mode_activated.wav')
    rng = np.random.default_rng(0)
    H = h5py.File(h5, 'r')
    tot = {}
    rows = []
    for f in sorted((REPO / 'results/animation/dechorate').glob('0*.json')):
        doc = json.loads(f.read_text()); setting = f.stem
        R = H[setting][()]
        for su in doc['setups']:
            if su['spacing_mm'] != 155:
                continue
            il, ir = su['mics']                                  # bake.py stores the global mic indices
            hl, hr = ((R[:, m, su['src']] * (-1.0 if m in INVERTED else 1.0)) for m in (il, ir))
            # the sign that makes the true response's direct path read the labelled direct angle
            sign = 1.0
            ys = []
            for h in (hl, hr):
                y = np.convolve(probe, h)
                ys.append(y + rng.standard_normal(len(y)) * np.std(y) * 10 ** (-45 / 20))
            est = [sosfiltfilt(SOS, deconv(y, probe)[:len(h)]) for y, h in zip(ys, (hl, hr))]
            tru = [sosfiltfilt(SOS, h) for h in (hl, hr)]
            ptrue, _ = peaks(*tru, sign); pest, _ = peaks(*est, sign)
            if su['truth'].get('deg_measured') is not None:
                d0 = su['truth']['deg_measured']
            for e in su['truth']['echoes']:
                def hit(ps):
                    m = [p for p in ps if abs(p['delay_ms'] - e['delay_ms']) <= 0.35]
                    return min(m, key=lambda p: abs(p['delay_ms'] - e['delay_ms'])) if m else None
                a, b = hit(ptrue), hit(pest)
                rows.append(dict(setting=setting, surface=e['surface'], reflective=e['reflective'],
                                 delay=e['delay_ms'], deg=e['deg'], true_hit=a is not None, probe_hit=b is not None,
                                 deg_err=(None if b is None else min(abs(b['deg'] - e['deg']), abs(-b['deg'] - e['deg'])))))
            rows.append(dict(setting=setting, surface='_extra', n_true=len(ptrue), n_probe=len(pest),
                             matched=sum(1 for p in pest if any(abs(p['delay_ms'] - e['delay_ms']) <= 0.35 for e in su['truth']['echoes']))))
    ech = [r for r in rows if r['surface'] != '_extra']
    ext = [r for r in rows if r['surface'] == '_extra']
    out = [f"{len(ext)} pair setups (155 mm, 6 sources x 6 arrays x 11 settings); {len(ech)} labelled echoes"]
    for refl in (True, False):
        s = [r for r in ech if r['reflective'] == refl]
        out.append(f"{'reflective' if refl else 'absorbent '} surfaces: found in the true response {np.mean([r['true_hit'] for r in s]) * 100:.0f}%,"
                   f" through the announcement {np.mean([r['probe_hit'] for r in s]) * 100:.0f}% (n {len(s)})")
    out.append('\nreflective surfaces found through the announcement, by surface:')
    for sname in ('floor', 'ceiling', 'west', 'south', 'east', 'north'):
        s = [r for r in ech if r['reflective'] and r['surface'] == sname]
        if s:
            errs = [r['deg_err'] for r in s if r['deg_err'] is not None]
            out.append(f"  {sname:8s} {np.mean([r['probe_hit'] for r in s]) * 100:4.0f}% of {len(s):3d}   delay {np.mean([r['delay'] for r in s]):5.1f} ms"
                       f"   angle error when found {np.mean(errs) if errs else float('nan'):5.1f} deg (front/back folded)")
    out.append(f"\npicked peaks through the announcement: {np.mean([r['n_probe'] for r in ext]):.1f} per setup, of which"
               f" {np.sum([r['matched'] for r in ext]) / np.sum([r['n_probe'] for r in ext]) * 100:.0f}% sit on a labelled first-order echo")
    txt = '\n'.join(out)
    (REPO / 'results/probe_echoes/summary.txt').write_text(txt + '\n')
    print(txt)


if __name__ == '__main__':
    main(sys.argv[1])
