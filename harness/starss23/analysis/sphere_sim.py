"""Does the em32's rigid sphere alone explain GccPhat's outward lean on STARSS23? Synthesize each real cut's direction
(pair 1-2 and 3-4) through the README's rigid-sphere response and through free field, same noise, no room."""
import base64, json, math, random, sys
import numpy as np
from scipy.special import spherical_jn, spherical_yn, eval_legendre
R, C, SR, NMAX = 0.042, 343.0, 48000, 30
CAPS = {1: (45, 35), 2: (-45, -35), 3: (135, -35), 4: (-135, 35)}
def unit(az, el):
    az, el = math.radians(az), math.radians(el); return np.array([math.cos(el) * math.cos(az), math.cos(el) * math.sin(az), math.sin(el)])
N = int(1.5 * SR); f = np.fft.rfftfreq(N, 1 / SR); ka = 2 * np.pi * f * R / C; ka[0] = 1e-6
dh = [spherical_jn(n, ka, derivative=True) - 1j * spherical_yn(n, ka, derivative=True) for n in range(NMAX + 1)]
def sphere(cosg):   # README formula; time convention fixed below against free field
    s = sum((1j ** (n - 1)) / dh[n] * (2 * n + 1) * eval_legendre(n, cosg) for n in range(NMAX + 1))
    return s / ka ** 2
def free(cosg): return np.exp(1j * ka * cosg)       # e^{+i k r.u}: capsule nearer the source leads
rng = np.random.default_rng(3)
out = {}
for pair in ((1, 2), (3, 4)):
    cuts = [json.loads(l) for l in open(f'{sys.argv[1]}/cuts_{pair[0]}{pair[1]}.jsonl')]
    random.seed(1); cuts = random.sample(cuts, 300)
    p1, p2 = unit(*CAPS[pair[0]]), unit(*CAPS[pair[1]])
    d = np.linalg.norm(R * (p2 - p1))
    # convention check: the sphere's inter-capsule phase must turn the same way as free field at low ka
    u = unit(0, 0); g1, g2 = p1 @ u, p2 @ u
    k = np.searchsorted(f, 500)
    flip = np.sign(np.angle(sphere(g1)[k] / sphere(g2)[k])) != np.sign(np.angle(free(g1)[k] / free(g2)[k]))
    for kind in ('sphere', 'free'):
        with open(f'{sys.argv[2]}/sim_{kind}_{pair[0]}{pair[1]}.jsonl', 'w') as fh:
            for c in cuts:
                u = unit(c['az'], c['el'])
                s = np.zeros(N); n0 = int(0.5 * SR); s[n0:] = rng.standard_normal(N - n0) * np.hanning(2 * (N - n0))[N - n0:][::-1] ** 0.1
                S = np.fft.rfft(s)
                H = [sphere(p @ u) for p in (p1, p2)] if kind == 'sphere' else [free(p @ u) for p in (p1, p2)]
                if kind == 'sphere' and flip: H = [np.conj(h) for h in H]
                x = [np.fft.irfft(S * h, N) for h in H]
                m = max(np.abs(x[0]).max(), np.abs(x[1]).max())
                pcm = [np.clip(v / m * 8000 + rng.standard_normal(N) * 8000 * 10 ** (-40 / 20) * 0.3, -32768, 32767).astype('<i2') for v in x]
                lat = math.degrees(math.asin(max(-1, min(1, float(u @ ((p2 - p1) / np.linalg.norm(p2 - p1)))))))
                fh.write(json.dumps({'file': c['file'], 'room': 'sim', 'onset_s': c['onset_s'], 'pair': list(pair), 'baseline_m': round(float(d), 5),
                                     'truth_lateral': round(lat, 2), 'onset_sample': n0, 'az': c['az'], 'el': c['el'],
                                     'L': base64.b64encode(pcm[0].tobytes()).decode(), 'R': base64.b64encode(pcm[1].tobytes()).decode()}) + '\n')
    print(pair, 'flip' if flip else 'no flip', 'baseline', round(d * 1000, 1))
