#!/usr/bin/env python3
"""Brief 13's cuts: human speech (EARS) placed at a known lateral angle, with one cause changed at a time.

Placements (the only synthetic part is WHERE the talker is):
  free157, free69   exact fractional delays on two free-field points, 157 mm (the phone) and 69 mm (a STARSS pair).
  room000000, room011111   dEchorate v1.0 measured RIRs (dechorate_rir_processed.hdf5, https://zenodo.org/records/5562386),
                    configuration 000000 (all absorbing) and 011111 (all reflective), the 155 mm pair (mics 0 and 3) of
                    one array. The talker's direct path is the measured loudspeaker pulse (L's, +-0.5/1.0 ms around its
                    peak) placed at the talker angle with exact fractional delays; everything else in the measured RIR
                    (reflections, reverberation) stays where it was measured. So the RIR carries the room's mechanisms,
                    and no geometry is taken from it: the truth is the angle we placed.
                    Four (source, array) combinations, sources 0-3 (those facing into the room), one per onset in turn.
Talker angles -75..+75 deg in 5 deg steps, N_ONSETS speech onsets each (EARS phrase onsets rising out of silence, as
harness/dechorate/dechorate_cut.py picks them). A cut is 2.0 s: 1.0 s before the onset, 1.0 s after.

Every cut carries a capsule floor: independent white noise FLOOR_DB under the voice (the voice's rms over the 0.5 s
after its onset, both channels). Causes (all levels are the added sound's rms relative to that voice level):
  baseline              nothing else.
  steady_pink:<dB>      pink noise from INTERF_DEG, through the whole cut (pause and speech), placed like the talker
                        (free: exact delays; room: its own measured RIR from another source at the same array).
  steady_voice:<dB>     a second talker (EARS speakers p001/p005, running speech) from INTERF_DEG, the same way.
  common_mode:<dB>      pink noise identical in both channels.
  diffuse:<dB>          pink noise with the coherence of an ideal diffuse field at the pair's spacing, sinc(2 f d / c).
  quiet:<dB>            the capsule floor raised to <dB> under the voice (30, 20, 10, 5 dB SNR).
Causes 4-6 (band edge, onset offset, no pause history) reuse the baseline audio and change only the run.

Truth per cut: deg (the placed angle, the schemes' convention R(t) = L(t - tau), deg = asin(-tau c / d)), and the other
labelled source (steady_* only). Plus, for the clue step, nothing else: the clues are measured from the audio.

usage: lab_cut.py EARS_TALKERS EARS_INTERF RIR_HDF5 --placement free157 --cause steady_pink:-20 --out cuts.jsonl
"""
import argparse
import base64
import json
import math
import sys
from pathlib import Path

import h5py
import numpy as np
import soundfile as sf

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'dechorate'))
import dechorate_cut as dc                                    # noqa: E402  (its phrase-onset picker, INVERTED)

SR, C = 48000, 343.0
PRE_S, POST_S = 1.0, 1.0
N = int((PRE_S + POST_S) * SR)
ON = int(PRE_S * SR)
ANGLES = list(range(-75, 80, 5))
N_ONSETS = 12
FLOOR_DB = -50.0
INTERF_DEG = 40.0
PLACEMENTS = {'free157': 0.157, 'free69': 0.069, 'room000000': 0.155, 'room011111': 0.155}
COMBOS = [(0, 0), (1, 2), (2, 4), (3, 5)]                       # (source, array) for the rooms, one per onset in turn
KER = (24, 48)                                                  # the direct pulse: samples before / after its peak


def onsets(ears):
    dc.PRE_S, dc.POST_S = PRE_S, POST_S
    return dc.clean_onsets(ears, N_ONSETS)


def frac_delay(x, delay, n=None):
    """x delayed by `delay` samples (fractional), circular over a zero-padded FFT; returns n samples."""
    n = n or len(x)
    m = 1 << int(np.ceil(np.log2(len(x) + 64)))
    X = np.fft.rfft(x, m)
    w = np.arange(len(X)) / m
    return np.fft.irfft(X * np.exp(-2j * np.pi * w * delay), m)[:n]


def tau_of(deg, d):
    return -math.sin(math.radians(deg)) * d / C                 # seconds; R lags L by tau


class Room:
    def __init__(self, hdf5, room):
        self.H = h5py.File(hdf5, 'r')[room][()]

    def ir(self, src, arr, deg, d):
        """(hL, hR, t0): the pair's impulse responses with the direct pulse re-timed to `deg`; t0 = the direct's centre."""
        il, ir_ = 5 * arr + 0, 5 * arr + 3
        hl, hr = (self.H[:, m, src] * (-1.0 if m in dc.INVERTED else 1.0) for m in (il, ir_))
        pl, pr = int(np.argmax(np.abs(hl))), int(np.argmax(np.abs(hr)))
        b, a = KER
        win = np.ones(b + a)
        t = 8                                                    # cosine tapers at both ends of the pulse window
        win[:t] = 0.5 - 0.5 * np.cos(np.pi * np.arange(t) / t)
        win[-t:] = win[:t][::-1]
        ker = hl[pl - b:pl + a] * win
        g = np.abs(hr[pr]) / np.abs(hl[pl])                      # R's capsule gain, kept
        tails = []
        for h, p in ((hl, pl), (hr, pr)):
            tl = h.copy()
            tl[p - b:p + a] *= 1 - win
            tails.append(tl)
        t0 = (pl + pr) / 2
        tau = tau_of(deg, d) * SR
        out = []
        for tl, delay, gain in ((tails[0], t0 - tau / 2 - b, 1.0), (tails[1], t0 + tau / 2 - b, g)):
            k = np.zeros(len(tl))
            k[:len(ker)] = ker * gain
            out.append(frac_delay(k, delay) + tl)
        return out[0], out[1], t0


def place(x, deg, placement, room=None, combo=None):
    """x (mono, onset at ON) heard at the pair from `deg`: (L, R), the direct's centre arriving at x's own time."""
    d = PLACEMENTS[placement]
    if placement.startswith('free'):
        tau = tau_of(deg, d) * SR
        return frac_delay(x, -tau / 2, N), frac_delay(x, tau / 2, N)
    hl, hr, t0 = room.ir(*combo, deg, d)
    m = 1 << int(np.ceil(np.log2(len(x) + len(hl))))
    X = np.fft.rfft(x, m)
    i0 = int(round(t0))
    return (np.fft.irfft(X * np.fft.rfft(hl, m), m)[i0:i0 + N], np.fft.irfft(X * np.fft.rfft(hr, m), m)[i0:i0 + N])


def pink(n, rng):
    X = np.fft.rfft(rng.standard_normal(n))
    f = np.arange(len(X)); f[0] = 1
    y = np.fft.irfft(X / np.sqrt(f), n)
    return y / np.sqrt(np.mean(y ** 2))


def diffuse_pink(n, d, rng):
    """Two channels of pink noise whose coherence is an ideal diffuse field's at spacing d: sinc(2 f d / c)."""
    A, B = (np.fft.rfft(rng.standard_normal(n)) for _ in range(2))
    f = np.fft.rfftfreq(n, 1 / SR)
    gam = np.sinc(2 * f * d / C)
    tilt = 1 / np.sqrt(np.maximum(f, f[1]))
    l, r = np.fft.irfft(A * tilt, n), np.fft.irfft((gam * A + np.sqrt(np.maximum(0, 1 - gam ** 2)) * B) * tilt, n)
    s = np.sqrt((np.mean(l ** 2) + np.mean(r ** 2)) / 2)
    return l / s, r / s


def interferer_voice(ears_interf, rng):
    """2 s of running speech from the interfering speakers (concatenated sentences, a random start)."""
    xs = [sf.read(str(f), dtype='float64')[0] for f in sorted(Path(ears_interf).glob('*.wav'))]
    x = np.concatenate(xs)
    s = int(rng.integers(0, len(x) - N))
    return x[s:s + N]


def rms2(l, r, a=ON, b=ON + SR // 2):
    return math.sqrt((np.mean(l[a:b] ** 2) + np.mean(r[a:b] ** 2)) / 2)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('ears')
    ap.add_argument('ears_interf')
    ap.add_argument('rirs')
    ap.add_argument('--placement', required=True, choices=list(PLACEMENTS))
    ap.add_argument('--cause', default='baseline')
    ap.add_argument('--out', required=True)
    ap.add_argument('--seed', type=int, default=0)
    a = ap.parse_args()
    kind, _, lev = a.cause.partition(':')
    lev = float(lev) if lev else None
    d = PLACEMENTS[a.placement]
    room = Room(a.rirs, a.placement[4:]) if a.placement.startswith('room') else None
    picks = onsets(a.ears)
    rng = np.random.default_rng(a.seed)
    n = 0
    with open(a.out, 'w') as out:
        for deg in ANGLES:
            for k, p in enumerate(picks):
                combo = COMBOS[k % len(COMBOS)] if room else None
                L, R = place(p['x'][:N], deg, a.placement, room, combo)
                v = rms2(L, R)
                others = []
                if kind in ('steady_pink', 'steady_voice'):
                    s = pink(N, rng) if kind == 'steady_pink' else interferer_voice(a.ears_interf, rng)
                    icombo = ((combo[0] + 1) % 4, combo[1]) if room else None      # another source, the same mics
                    il, ir_ = place(s, INTERF_DEG, a.placement, room, icombo)
                    g = v * 10 ** (lev / 20) / math.sqrt((np.mean(il ** 2) + np.mean(ir_ ** 2)) / 2)
                    L, R = L + g * il, R + g * ir_
                    others = [{'deg': INTERF_DEG, 'class': 'pink noise' if kind == 'steady_pink' else 'voice'}]
                elif kind == 'common_mode':
                    s = pink(N, rng) * v * 10 ** (lev / 20)
                    L, R = L + s, R + s
                elif kind == 'diffuse':
                    nl, nr = diffuse_pink(N, d, rng)
                    L, R = L + nl * v * 10 ** (lev / 20), R + nr * v * 10 ** (lev / 20)
                floor = v * 10 ** ((-lev if kind == 'quiet' else FLOOR_DB) / 20)
                L, R = L + rng.normal(0, floor, N), R + rng.normal(0, floor, N)
                gain = 0.5 * 32767 / max(np.abs(L).max(), np.abs(R).max())
                pl, pr = (np.clip(z * gain, -32768, 32767).astype('<i2') for z in (L, R))
                out.write(json.dumps({
                    'id': f'{a.placement}/{a.cause}/{deg:+d}/{k}', 'placement': a.placement, 'cause': a.cause,
                    'pair_mm': round(d * 1000), 'baseline_m': d, 'onset_sample': ON, 'clean': p['clean'],
                    'combo': list(combo) if combo else None, 'truth': {'deg': float(deg), 'dist_m': None,
                                                                       'facing_deg': None, 'others': others},
                    'L': base64.b64encode(pl.tobytes()).decode(), 'R': base64.b64encode(pr.tobytes()).decode()}) + '\n')
                n += 1
    print(f'{n} cuts {a.placement} {a.cause} -> {a.out}', file=sys.stderr)


if __name__ == '__main__':
    main()
