#!/usr/bin/env python3
"""What each scheme reads on the STARSS23 array when nothing is wrong: the rigid sphere alone, no room.

STARSS's capsules sit on a hard sphere (radius 4.2 cm), which lengthens the delay between capsules, so every bearing
reads wider than the geometric lateral angle (results/starss23/report.md, section 2: +19 deg at 45-60). Brief 9: don't
call the sphere's lean wrong. So each real read is judged against what the same scheme reads from the same direction
through the sphere alone.

This writes cuts in cut_all.py's format for a grid of directions (azimuth every 5 deg, elevation -80..+40 every 10 deg,
which spans STARSS's -79..+40), each pair: a noise burst from 0.5 s, through the sphere response of
harness/starss23/analysis/sphere_sim.py (the STARSS README's formula, same series, same time convention check), plus
noise 40 dB down. runner.mjs reads them like any cut; classify.py interpolates the grid.
usage: sphere_grid.py > grid_cuts.jsonl
"""
import base64
import json
import math
import sys

import numpy as np
from scipy.special import eval_legendre, spherical_jn, spherical_yn

R, C, SR, NMAX = 0.042, 343.0, 48000, 30
CAPS = {1: (45, 35), 2: (-45, -35), 3: (135, -35), 4: (-135, 35)}
AZ = range(-180, 180, 5)
EL = range(-80, 41, 10)


def unit(az, el):
    az, el = math.radians(az), math.radians(el)
    return np.array([math.cos(el) * math.cos(az), math.cos(el) * math.sin(az), math.sin(el)])


N = int(1.5 * SR)
f = np.fft.rfftfreq(N, 1 / SR)
ka = 2 * np.pi * f * R / C
ka[0] = 1e-6
dh = [spherical_jn(n, ka, derivative=True) - 1j * spherical_yn(n, ka, derivative=True) for n in range(NMAX + 1)]


def sphere(cosg):
    return sum((1j ** (n - 1)) / dh[n] * (2 * n + 1) * eval_legendre(n, cosg) for n in range(NMAX + 1)) / ka ** 2


def free(cosg):
    return np.exp(1j * ka * cosg)


def main():
    rng = np.random.default_rng(3)
    n0 = int(0.5 * SR)
    for pair in ((1, 2), (1, 3), (1, 4), (2, 3), (2, 4), (3, 4)):
        p1, p2 = unit(*CAPS[pair[0]]), unit(*CAPS[pair[1]])
        d = float(np.linalg.norm(R * (p2 - p1)))
        axis = (p2 - p1) / np.linalg.norm(p2 - p1)
        u = unit(0, 0); k = np.searchsorted(f, 500)
        flip = np.sign(np.angle(sphere(p1 @ u)[k] / sphere(p2 @ u)[k])) != np.sign(np.angle(free(p1 @ u)[k] / free(p2 @ u)[k]))
        for az in AZ:
            for el in EL:
                u = unit(az, el)
                s = np.zeros(N)
                s[n0:] = rng.standard_normal(N - n0) * np.hanning(2 * (N - n0))[N - n0:][::-1] ** 0.1
                S = np.fft.rfft(s)
                H = [sphere(p @ u) for p in (p1, p2)]
                if flip:
                    H = [np.conj(h) for h in H]
                x = [np.fft.irfft(S * h, N) for h in H]
                m = max(np.abs(x[0]).max(), np.abs(x[1]).max())
                pcm = [np.clip(v / m * 8000 + rng.standard_normal(N) * 8000 * 10 ** (-40 / 20) * 0.3, -32768, 32767).astype('<i2') for v in x]
                lat = math.degrees(math.asin(max(-1, min(1, float(u @ axis)))))
                sys.stdout.write(json.dumps({
                    'dataset': 'sphere', 'scenario': f'sphere pair {pair[0]}{pair[1]}', 'id': f'{pair[0]}{pair[1]}/{az}/{el}',
                    'pair': list(pair), 'az': az, 'el': el, 'baseline_m': round(d, 5), 'truth_lateral': round(lat, 2),
                    'onset_sample': n0, 'L': base64.b64encode(pcm[0].tobytes()).decode(),
                    'R': base64.b64encode(pcm[1].tobytes()).decode()}) + '\n')
        print(pair, 'flip' if flip else 'no flip', file=sys.stderr)


if __name__ == '__main__':
    main()
