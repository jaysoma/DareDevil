#!/usr/bin/env python3
"""What the diffuse-noise hypothesis predicts: the share of GCC-PHAT peaks within 6 deg of 0 for an isotropic field of
plane waves on two free-field points, at STARSS's 68.5 mm and the phone's 157 mm, at each high-pass of pause_gcc.py.

Same frames, band, delay grid and PHAT as pause_gcc.py, built in the frequency domain (each frame: K plane waves from
uniform directions on the sphere, independent complex Gaussian amplitudes per slice). Spectra:
  white      -- diffuse noise flat in frequency, no sensor noise.
  hvac       -- diffuse noise falling 12 dB/octave (power ~ 1/f^2), plus independent white sensor noise in each capsule,
                equal to the diffuse noise at CROSS_HZ: low frequencies are the room's, high frequencies the capsules'.
  sensor     -- only independent sensor noise (no field): the PHAT/grid floor.

    python3 sim_diffuse.py out_dir
"""
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
from pause_gcc import HPS, NEAR0, NFFT, SR, C, steering, peaks   # noqa: E402

FRAMES, K = 3000, 256
CROSSES = [300, 1000, 3000]


def sim(d, kind, cross_hz=1000, seed=0):
    rng = np.random.default_rng(seed)
    f, E, deg = steering(d)
    u = rng.standard_normal((FRAMES, K, 3))
    cosg = (u / np.linalg.norm(u, axis=2, keepdims=True))[..., 0]          # pair axis along x
    out = {}
    X = np.zeros((FRAMES, len(f)), complex)
    for i0 in range(0, FRAMES, 250):
        sl = slice(i0, i0 + 250)
        n = cosg[sl].shape[0]
        S = (rng.standard_normal((n, K, len(f))) + 1j * rng.standard_normal((n, K, len(f)))) / np.sqrt(2 * K)
        ph = np.exp(1j * np.pi * f[None, None, :] * d / C * cosg[sl][..., None])   # +-half the delay at each capsule
        A, B = (S * ph).sum(1), (S * np.conj(ph)).sum(1)
        if kind == 'sensor':
            A, B = np.zeros_like(A), np.zeros_like(B)
        if kind == 'hvac':
            g = cross_hz / np.maximum(f, f[1])                                   # amplitude ~ 1/f, 1 at CROSS_HZ
            A, B = A * g, B * g
        if kind in ('hvac', 'sensor'):
            A = A + (rng.standard_normal(A.shape) + 1j * rng.standard_normal(A.shape)) / np.sqrt(2)
            B = B + (rng.standard_normal(B.shape) + 1j * rng.standard_normal(B.shape)) / np.sqrt(2)
        S2 = A * np.conj(B)
        X[sl] = S2 / np.maximum(np.abs(S2), 1e-30)
    for hp in HPS:
        dg, _ = peaks(X, f, E, deg, hp)
        out[str(hp)] = round(100 * float((np.abs(dg) < NEAR0).mean()), 1)
    return out


def main():
    out = Path(sys.argv[1])
    out.mkdir(parents=True, exist_ok=True)
    res = {'frames': FRAMES, 'plane_waves': K, 'near0_deg': NEAR0, 'nfft': NFFT, 'sr': SR}
    for d in (0.0685, 0.157):
        r = res[f'{d * 1000:.1f}mm'] = {'white': sim(d, 'white'), 'sensor': sim(d, 'sensor')}
        for c in CROSSES:
            r[f'hvac_cross{c}'] = sim(d, 'hvac', c)
        print(d, r, flush=True)
    with open(out / 'sim_diffuse.json', 'w') as fh:
        json.dump(res, fh, indent=1)


if __name__ == '__main__':
    main()
