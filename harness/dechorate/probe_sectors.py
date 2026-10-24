#!/usr/bin/env python3
"""Left, front or right for each wall echo, through the announcement (2026-10-24). Reuses probe_echoes.py's
deconvolution and picking on dEchorate's 155 mm pairs. Sector by the pair's angle: front within 30 deg of broadside,
else left or right by sign. The left/right sign is calibrated on the direct paths (est against labelled)."""
import json
import sys
from pathlib import Path

import h5py
import numpy as np
import soundfile as sf
from scipy.signal import sosfiltfilt

sys.path.insert(0, str(Path(__file__).resolve().parent))
from probe_echoes import C, D, INVERTED, REPO, SOS, SR, deconv, peaks  # noqa: E402

FRONT = 30.0
sector = lambda d: 'front' if abs(d) <= FRONT else ('right' if d > 0 else 'left')


def direct_deg(hl, hr):
    i = int(np.argmax(np.abs(hl[:SR // 10]) + np.abs(hr[:SR // 10]))); L = int(0.0005 * SR); n = 4 * L
    cc = np.fft.irfft(np.fft.rfft(hl[i - L:i + L], n) * np.conj(np.fft.rfft(hr[i - L:i + L], n)), n * 16)
    m = int(D / C * SR * 16) + 16
    cc = np.concatenate([cc[-m:], cc[:m + 1]]); tau = (np.argmax(cc) - m) / (SR * 16)
    return float(np.degrees(np.arcsin(np.clip(tau * C / D, -1, 1))))


probe, _ = sf.read(REPO / 'probe/daredevil_mode_activated.wav')
H = h5py.File(sys.argv[1], 'r'); rng = np.random.default_rng(0)
recs, cal = [], []
for f in sorted((REPO / 'results/animation/dechorate').glob('0*.json')):
    doc = json.loads(f.read_text()); R = H[f.stem][()]
    for su in doc['setups']:
        if su['spacing_mm'] != 155:
            continue
        hl, hr = ((R[:, m, su['src']] * (-1.0 if m in INVERTED else 1.0)) for m in su['mics'])
        tru = [sosfiltfilt(SOS, h) for h in (hl, hr)]
        est = []
        for h in (hl, hr):
            y = np.convolve(probe, h); y = y + rng.standard_normal(len(y)) * np.std(y) * 10 ** (-45 / 20)
            est.append(sosfiltfilt(SOS, deconv(y, probe)[:len(h)]))
        cal.append((direct_deg(*tru), su['truth']['deg_measured']))
        for name, pair in (('true', tru), ('probe', est)):
            ps, _ = peaks(*pair, 1.0)
            for e in su['truth']['echoes']:
                if not e['reflective'] or e['surface'] in ('floor', 'ceiling'):
                    continue
                m = [p for p in ps if abs(p['delay_ms'] - e['delay_ms']) <= 0.35]
                if m:
                    p = min(m, key=lambda p: abs(p['delay_ms'] - e['delay_ms']))
                    recs.append((name, e['surface'], e['deg'], p['deg']))
c = np.array(cal); s = 1.0 if np.mean(np.sign(c[:, 0]) == np.sign(c[:, 1])) >= 0.5 else -1.0
out = [f"left/right sign from {len(c)} direct paths: {s:+.0f}, agreeing {np.mean(np.sign(s * c[:, 0]) == np.sign(c[:, 1])) * 100:.0f}%"]
for name in ('true', 'probe'):
    r = [x for x in recs if x[0] == name]
    t = [sector(x[2]) for x in r]; e = [sector(s * x[3]) for x in r]
    acc = np.mean([a == b for a, b in zip(t, e)]); share = {k: t.count(k) / len(t) for k in ('left', 'front', 'right')}
    out.append(f"\n{name} response: {len(r)} wall echoes found (reflective walls, floor and ceiling left out); sector right {acc * 100:.0f}%,"
               f" guessing the commonest sector {max(share.values()) * 100:.0f}%")
    out.append('  labelled \\ read   left  front  right')
    for k in ('left', 'front', 'right'):
        out.append(f"  {k:16s} " + '  '.join(f"{sum(1 for a, b in zip(t, e) if a == k and b == j):5d}" for j in ('left', 'front', 'right')))
txt = '\n'.join(out)
(REPO / 'results/probe_echoes/sectors.txt').write_text(txt + '\n'); print(txt)
