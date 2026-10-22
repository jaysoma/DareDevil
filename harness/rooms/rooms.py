"""Image-source rooms for Angle2's inward pull: the clean utterances of onsets.py, played from -60..+60 deg at 1.5 m
in a chosen room, heard by a horizontal 2-mic pair. Writes cuts in the STARSS23 harness's format, so
harness/starss23/run_schemes.mjs reads them unchanged.

Geometry: the pair's centre at MIC, its axis along x (L at -d/2, R at +d/2); the talker at the same height, TALK_M away,
at +deg toward R (deg = asin of the direction's x component, the harness's lateral angle). Walls a reflection is not
wanted from absorb everything; image order 1 for the partial rooms, Sabine's order for the shoeboxes.
What real rooms add besides reflections, as modifiers on a config name (box_mid_rt0.4+n20+ctx+jit):
  +n<SNR>  spherically diffuse noise (coherence sinc(2 pi f d / c), 1/f spectrum) at SNR dB under the speech's RMS over
           the 1 s after the onset;
  +ctx     the clip's own 0.5 s before the onset (earlier words, their reverb tail) instead of silence (<utts>_ctx.npy);
  +jit     the onset handed to the schemes 0-100 ms early, as a 100 ms label frame would place it (STARSS23).
usage: python rooms.py <utts.npy> <config> <spacing_m> <out.jsonl>     (python rooms.py --list for the configs)"""
import base64, json, math, sys
import numpy as np, pyroomacoustics as pra
from scipy.signal import fftconvolve
SR, TALK_M, PRE = 48000, 1.5, 24000
ANGLES = list(range(-60, 61, 10))
WALLS = ('west', 'east', 'south', 'north', 'floor', 'ceiling')     # x=0, x=X, y=0 (behind the pair), y=Y, z=0, z=Z
# partial rooms: 6 x 5 x 3 m, pair at (3, 1.5, 1.5); east wall 3 m to R's side, south wall 1.5 m behind, floor 1.5 m below
PART = dict(dims=(6, 5, 3), mic=(3, 1.5, 1.5))
CONFIGS = {
    'free': dict(PART, keep=()),
    'floor': dict(PART, keep=('floor',)),
    'east': dict(PART, keep=('east',)),
    'south': dict(PART, keep=('south',)),
    'floor_east': dict(PART, keep=('floor', 'east')),
    'floor_south': dict(PART, keep=('floor', 'south')),
    'floor_ceiling': dict(PART, keep=('floor', 'ceiling')),
    'order1_all': dict(PART, keep=WALLS),
}
for rt in (0.2, 0.4, 0.7):                                        # full shoeboxes, small to large, the pair 1.5 m off the floor
    CONFIGS[f'box_small_rt{rt}'] = dict(dims=(3.5, 3, 2.5), mic=(1.75, 0.8, 1.5), rt60=rt)
    CONFIGS[f'box_mid_rt{rt}'] = dict(dims=(6, 5, 3), mic=(3, 1.5, 1.5), rt60=rt)
    CONFIGS[f'box_big_rt{rt}'] = dict(dims=(10, 8, 3.5), mic=(5, 2.5, 1.5), rt60=rt)

def room(cfg, d):
    dims = np.array(cfg['dims'], float)
    if 'rt60' in cfg:
        absorb, order = pra.inverse_sabine(cfg['rt60'], dims)
        r = pra.ShoeBox(dims, fs=SR, materials=pra.Material(absorb), max_order=order, air_absorption=False)
    else:
        mats = {w: pra.Material(0.1 if w in cfg['keep'] else 1.0) for w in WALLS}
        r = pra.ShoeBox(dims, fs=SR, materials=mats, max_order=1 if cfg['keep'] else 0, air_absorption=False)
    m = np.array(cfg['mic'], float)
    r.add_microphone_array(np.c_[m - [d / 2, 0, 0], m + [d / 2, 0, 0]])
    return r, m

def diffuse(n, d, rng):
    """Two channels of spherically diffuse 1/f noise across spacing d, unit RMS."""
    N = 1 << int(np.ceil(np.log2(n))); f = np.fft.rfftfreq(N, 1 / SR)
    rho = np.sinc(2 * f * d / 343.0)                              # np.sinc(x) = sin(pi x)/(pi x): sin(k d)/(k d)
    a = rng.standard_normal((2, len(f))) + 1j * rng.standard_normal((2, len(f)))
    shape = 1 / np.sqrt(np.maximum(f, 50))
    x = [np.fft.irfft(a[0] * shape, N)[:n], np.fft.irfft((rho * a[0] + np.sqrt(1 - rho ** 2) * a[1]) * shape, N)[:n]]
    return [v / np.sqrt(np.mean(x[0] ** 2)) for v in x]

if __name__ == '__main__':
    if sys.argv[1] == '--list': print('\n'.join(CONFIGS)); sys.exit()
    name, d, outp = sys.argv[2], float(sys.argv[3]), sys.argv[4]
    base, *mods = name.split('+')
    utts = np.load(sys.argv[1][:-4] + '_ctx.npy' if 'ctx' in mods else sys.argv[1])
    snr = next((float(m[1:]) for m in mods if m.startswith('n')), None)
    cfg, rng = CONFIGS[base], np.random.default_rng(7)
    with open(outp, 'w') as fh:
        for deg in ANGLES:
            r, m = room(cfg, d)
            a = math.radians(deg)
            r.add_source(m + TALK_M * np.array([math.sin(a), math.cos(a), 0]))
            r.compute_rir()
            h = [r.rir[0][0], r.rir[1][0]]
            first = int(np.argmax(np.abs(h[0]) > 0.5 * np.abs(h[0]).max()))   # the direct path's sample in the mic signal
            for k, u in enumerate(utts):
                x = [fftconvolve(u, hh)[:len(u)] for hh in h]
                if snr is not None:
                    rms = np.sqrt(np.mean(x[0][PRE + first:PRE + first + SR] ** 2))
                    x = [v + nz * rms * 10 ** (-snr / 20) for v, nz in zip(x, diffuse(len(u), d, rng))]
                on = PRE + first - (int(rng.integers(0, 4800)) if 'jit' in mods else 0)
                peak = max(np.abs(x[0]).max(), np.abs(x[1]).max())
                pcm = [np.clip(v / peak * 8000 + rng.standard_normal(len(u)) * 8000 * 10 ** (-60 / 20), -32768, 32767).astype('<i2') for v in x]
                fh.write(json.dumps({'file': f'{name}_u{k:02d}', 'room': name, 'onset_s': round(on / SR, 4), 'pair': [1, 2],
                                     'baseline_m': d, 'truth_lateral': float(deg), 'onset_sample': on, 'true_onset': PRE + first, 'utt': k,
                                     'L': base64.b64encode(pcm[0].tobytes()).decode(), 'R': base64.b64encode(pcm[1].tobytes()).decode()}) + '\n')
    print(name, d, len(ANGLES) * len(utts), 'cuts ->', outp)
