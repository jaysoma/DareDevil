#!/usr/bin/env python3
"""Make dEchorate cuts: clean anechoic speech onsets (EARS) convolved with dEchorate's measured RIRs, one mic pair at a
time, with the direct-path and first-order echo truth from the dataset's calibrated geometry.

dEchorate: one 5.705 x 5.965 x 2.355 m room, 11 wall configurations (room_code digits: floor, ceiling, west, south,
east, north; 1 or 2 = reflective panels, 0 = absorbing), six 5-mic linear arrays (mics 0-29). The RIRs are v1.0's
dechorate_rir_processed.hdf5 (https://zenodo.org/records/5562386): 48 kHz, (20000, 30 mics, 7 sources) per room, aligned
so the direct path sits at its time of flight. Columns 0-5 are the 6 calibrated sources (each column's first arrivals
match that source's time of flight to 1-3 samples on every mic); column 6 matches none of the listed positions and is
not used. v2.0's dEchorate_rirs_gzip7.hdf5 (record 6576203) cannot be read: see results/dechorate/report.md.
The SOUTH panel is never scored as reflective: flipping it (000100 against 000000) adds nothing at any first-order echo
time (echo_check.py), and the floor is absorbing in every configuration.

A cut is 1.5 s at 48 kHz like a STARSS cut: 0.5 s of quiet, then a speech onset. The clean clip starts at a phrase onset
in an EARS sentence (a rise of 25 dB from a dip), with true silence put in front of it, so the onset rises out of quiet.
Independent noise at SNR_DB below the speech's level stands in for the mics' own floor. The cut is aligned so the direct
sound reaches the nearer mic at onset_sample.

Truth, in the schemes' own convention (R(t) = L(t - tau), deg = asin(-tau c / d) with their c = 343): L is the pair's
lower-numbered mic. Each first-order image source (one per surface) gives an echo with its own tau, deg, delay after the
direct sound (at the pair's centre) and whether that surface is reflective in this configuration. rir_tau_ms is the
direct-path delay measured in the pair's two RIRs; truth.py decides which of the two the scores use.

usage: python3 dechorate_cut.py DATA_DIR EARS_DIR --room 011000 --out cuts.jsonl
"""
import argparse
import base64
import json
import math
from pathlib import Path

import h5py
import numpy as np
import soundfile as sf
from scipy.signal import fftconvolve

from safe_pickle import load_echo_notes

SR = 48000
C_SCHEME = 343.0                              # what GccPhat.mjs and Angle2.mjs use to turn a delay into an angle
C_ROOM = 331.3 + 0.606 * 24                   # dEchorate's own (main_geometry_from_echo_calibration.py, 24 C)
ROOM = (5.705, 5.965, 2.355)
# surface -> (axis, wall coordinate); south is y = 0 and west is x = 0 by the source aims in the calibration script
SURFACES = {'floor': (2, 0.0), 'ceiling': (2, ROOM[2]), 'west': (0, 0.0), 'south': (1, 0.0),
            'east': (0, ROOM[0]), 'north': (1, ROOM[1])}
ORDER = ['floor', 'ceiling', 'west', 'south', 'east', 'north']   # room_code digit order
PAIRS = {155: (0, 3), 65: (2, 3)}             # spacing (mm) -> mic offsets inside an array: the phone's and STARSS's
# Six capsules read every direct path with inverted polarity, in all 11 rooms and for every source facing into the room
# (the direct peak's sign; sources 4 and 5 face a wall and agree on 97-100% of mics). A fixed wiring property, not the
# room's, and a phone's two capsules share polarity: these channels are flipped back before convolving.
INVERTED = (0, 5, 17, 20, 23, 28)
PRE_S, POST_S, FADE_S = 0.5, 1.0, 0.01
SNR_DB = 30.0
N_ONSETS = 24


def clean_onsets(ears_dir, n_total):
    """Phrase onsets: a 10 ms frame 25 dB over the file's floor after a 200 ms dip to within 8 dB of it, 1 s apart."""
    per_file = []
    files = sorted(Path(ears_dir).glob('*.wav'))
    for f in files:
        x, sr = sf.read(str(f), dtype='float64')
        assert sr == SR
        fr = SR // 100
        n = len(x) // fr
        e = 10 * np.log10((x[:n * fr].reshape(n, fr) ** 2).mean(1) + 1e-14)
        flo = np.percentile(e, 5)
        last, ons = -10 ** 9, []
        for i in range(20, n - 110):
            if e[i] >= flo + 25 and e[i - 1] < flo + 25 and e[i - 20:i].min() <= flo + 8 and i - last >= 100:
                # the sample where the rise starts: first sample of the frame block over the dip level + 10 dB
                seg = x[(i - 2) * fr:(i + 1) * fr]
                thr = 10 ** ((e[i - 20:i].min() + 10) / 20)
                j = int(np.argmax(np.abs(seg) > thr))
                ons.append(((i - 2) * fr + j, x))
                last = i
        per_file.append((f.stem, ons))
    # spread the picks evenly over speakers and files
    speakers = sorted({s.split('_')[0] for s, _ in per_file})
    k_spk = n_total // len(speakers)
    picks = []
    for spk in speakers:
        pool = [(s, o) for s, ons in per_file if s.startswith(spk) for o in ons]
        idx = np.linspace(0, len(pool) - 1, k_spk).round().astype(int)
        for q in idx:
            stem, (on, x) = pool[q]
            pre = int(FADE_S * SR)
            clip = x[on - pre:on + int(POST_S * SR)].copy()
            clip[:pre] *= 0.5 - 0.5 * np.cos(np.pi * np.arange(pre) / pre)
            full = np.concatenate([np.zeros(int(PRE_S * SR) - pre), clip])   # onset at PRE_S exactly
            picks.append({'clean': f'{stem}@{on / SR:.3f}', 'x': full})
    return picks


def image(src, surface):
    ax, w = SURFACES[surface]
    p = np.array(src, dtype=float)
    p[ax] = 2 * w - p[ax]
    return p


def lateral(tau, d):
    return math.degrees(math.asin(max(-1.0, min(1.0, -tau * C_SCHEME / d))))


def rir_tdoa(hl, hr, around):
    """Measured direct-path delay R - L (s): cross-correlation of 2 ms around the direct peaks, upsampled 16x."""
    w = 192
    sl = hl[max(0, around - w // 2):around + w // 2]
    sr_ = hr[max(0, around - w // 2):around + w // 2]
    up = 16
    n = len(sl) * up
    Fl, Fr = np.fft.rfft(sl, 2 * len(sl)), np.fft.rfft(sr_, 2 * len(sl))
    cc = np.fft.irfft(Fr * np.conj(Fl), 2 * n)
    cc = np.concatenate([cc[-n:], cc[:n]])
    lag = (np.argmax(cc) - n) / up
    return lag / SR


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('data')
    ap.add_argument('ears')
    ap.add_argument('--room', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--srcs', nargs='+', type=int, default=list(range(6)))
    ap.add_argument('--spacings', nargs='+', type=int, default=[155, 65])
    ap.add_argument('--onsets', type=int, default=N_ONSETS)
    ap.add_argument('--seed', type=int, default=0)
    a = ap.parse_args()
    data = Path(a.data)
    notes = load_echo_notes(data / 'dEchorate_echo_notes.pkl')
    mics = notes['mics'].T
    srcs = {j: notes['srcs'][:, j] for j in a.srcs}
    labelled = {s: int(a.room[i]) > 0 for i, s in enumerate(ORDER)}
    rfl = {s: labelled[s] and s != 'south' for s in ORDER}
    picks = clean_onsets(a.ears, a.onsets)
    rng = np.random.default_rng(a.seed)
    H = h5py.File(data / 'dechorate_rir_processed.hdf5', 'r')[a.room][()]
    n = 0
    with open(a.out, 'w') as out:
        for j in a.srcs:
            s = srcs[j]
            for arr in range(6):
                for sp in a.spacings:
                    il, ir = 5 * arr + PAIRS[sp][0], 5 * arr + PAIRS[sp][1]
                    ml, mr = mics[il], mics[ir]
                    d = float(np.linalg.norm(mr - ml))
                    tau = (np.linalg.norm(s - mr) - np.linalg.norm(s - ml)) / C_ROOM
                    mid = (ml + mr) / 2
                    t_dir = np.linalg.norm(s - mid) / C_ROOM
                    echoes = []
                    for surf in ORDER:
                        im = image(s, surf)
                        te = (np.linalg.norm(im - mr) - np.linalg.norm(im - ml)) / C_ROOM
                        echoes.append({'surface': surf, 'reflective': rfl[surf], 'labelled': labelled[surf], 'tau_ms': round(te * 1000, 4),
                                       'deg': round(lateral(te, d), 2),
                                       'delay_ms': round((np.linalg.norm(im - mid) / C_ROOM - t_dir) * 1000, 3)})
                    echoes.sort(key=lambda e: e['delay_ms'])
                    hl, hr = (H[:, m, j] * (-1.0 if m in INVERTED else 1.0) for m in (il, ir))
                    d0 = int(round(min(np.linalg.norm(s - ml), np.linalg.norm(s - mr)) / C_ROOM * SR))
                    meas = rir_tdoa(hl, hr, d0)
                    for k, p in enumerate(picks):
                        L = fftconvolve(p['x'], hl)[d0:d0 + len(p['x'])]
                        R = fftconvolve(p['x'], hr)[d0:d0 + len(p['x'])]
                        on = int(PRE_S * SR)
                        act = np.sqrt(np.mean(np.concatenate([L[on:], R[on:]]) ** 2))
                        sig = act * 10 ** (-SNR_DB / 20)
                        L = L + rng.normal(0, sig, len(L))
                        R = R + rng.normal(0, sig, len(R))
                        g = 0.5 * 32767 / max(np.abs(L).max(), np.abs(R).max())
                        pl = np.clip(L * g, -32768, 32767).astype('<i2')
                        pr = np.clip(R * g, -32768, 32767).astype('<i2')
                        out.write(json.dumps({
                            'id': f'{a.room}/s{j}/a{arr}/{sp}/{k}', 'room': a.room, 'src': j,
                            'array': arr, 'spacing_mm': sp, 'mics': [il, ir], 'clean': p['clean'],
                            'baseline_m': round(d, 5), 'onset_sample': on,
                            'truth_tau_ms': round(tau * 1000, 4), 'truth_deg': round(lateral(tau, d), 2),
                            'rir_tau_ms': round(meas * 1000, 4), 'dist_m': round(float(np.linalg.norm(s - mid)), 3),
                            'echoes': echoes,
                            'L': base64.b64encode(pl.tobytes()).decode(), 'R': base64.b64encode(pr.tobytes()).decode()}) + '\n')
                        n += 1
    print(f'{n} cuts, room {a.room} -> {a.out}')


if __name__ == '__main__':
    main()
