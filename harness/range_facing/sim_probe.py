#!/usr/bin/env python3
"""Brief 20 step 5, simulated: the phone's announcement as a room probe, in pyroomacoustics shoeboxes.

The phone plays probe/daredevil_mode_activated.wav from a speaker SPK_OFF from its lower mic; both mics record it, with
PRE_S of quiet before (the noise read). Everything but the direct sound is the room's: its energy is the reverberant
level, L_W + 10 log10(4/A) in level terms, and its free decay after the last word is the echo time.

The calibration, outdoors (free field, the same noise): the phone's own mics give each one's direct path as a short
least-squares FIR (NTAP), and a mic 1 m on axis gives the level there. In the room, the outdoor direct path's prediction
is subtracted from each mic's recording, and the rest, over PROBE_BAND (0.5-4 kHz), less the noise's share, per unit of
the dry signal's band energy, is the reverberant gain G_rev; G_1m is the same for the 1 m recording outdoors. Then

    r_c = 1 m * sqrt(G_1m / G_rev),      A = 16 pi r_c^2 / Q   (Q = 1: every source here is omni)

and the predicted DRR of a talker at r is 20 log10(r_c / r). (A regularised deconvolution of the announcement was tried
first and dropped: its leakage sits about 40 dB under the 3 cm direct sound, which is where the room's tail is.)
The phone's volume must be the same as at calibration: nothing in the room checks it.

The talkers are EARS phrase onsets (dechorate_cut.clean_onsets) placed at DISTS from the phone at random bearings, 1.5
m high, with the phone on a 0.8 m table (no table in the model). Their cuts go through drr.cdr_bands: the measured CDR
per band, against the predicted line, and against each talker's true DRR (direct +-1 ms of the simulated RIR, both
mics' mean, against everything after).

Truth per room: r_c from the talkers' true DRRs (slope fixed at -20 dB/decade), Sabine's r_c sqrt(A/16 pi) with the
model's own absorption, and the echo time measured on the talkers' RIRs (Schroeder, T20 x 3, both mics, mean).
Noise: white, independent per mic, NOISE_DB below the talker's direct level at 1 m (talker and noise both on). The
announcement is PROBE_GAIN_DB louder than the talker at 1 m (a phone speaker at full volume against conversation).

stdout: one JSON line per room x noise level (the probe's reads, the truth, and the talkers' reads).
usage: sim_probe.py <EARS dir> [--seed 0]
"""
import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np
import pyroomacoustics as pra
import soundfile as sf
from scipy.linalg import solve_toeplitz
from scipy.signal import fftconvolve, butter, sosfiltfilt

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parents[1] / 'harness' / 'dechorate'))
from drr import cdr_bands                                           # noqa: E402
from dechorate_cut import clean_onsets                              # noqa: E402

SR = 48000
PROBE = HERE.parents[1] / 'probe' / 'daredevil_mode_activated.wav'
PROBE_BAND = (500.0, 4000.0)
NTAP = 160                                                          # the self-path FIR: 3.3 ms
PRE_S = 0.3                                                         # quiet before the announcement (the noise read)
SPK_OFF = np.array([0.0, -0.03, -0.005])                            # the speaker: 3 cm past the lower mic, at the phone's edge
PAIR_M = 0.157                                                      # the phone's two mics
SIZES = {'small 3.5x4x2.6': (3.5, 4.0, 2.6), 'medium 5x6x2.8': (5.0, 6.0, 2.8),
         'large 8x10x3.2': (8.0, 10.0, 3.2), 'hall 12x15x4': (12.0, 15.0, 4.0)}
RT60S = (0.25, 0.4, 0.6, 0.9)
NOISE_DB = (50.0, 35.0, 20.0, 10.0, 0.0)
PROBE_GAIN_DB = 10.0
DISTS = (0.5, 0.75, 1.0, 1.5, 2.0, 3.0, 4.0)
N_TALK = 4                                                          # EARS onsets per position


def band(x, lo, hi):
    return sosfiltfilt(butter(4, [lo, hi], btype='band', fs=SR, output='sos'), x)


def bandE(x, noise_pw=0.0):
    """Band energy over PROBE_BAND, less the noise's share (noise_pw per sample, already in band)."""
    return max(float(np.sum(band(x, *PROBE_BAND) ** 2)) - noise_pw * len(x), 0.0)


def self_path(y, dry, ntap=NTAP):
    """The direct path speaker -> mic as a short FIR, least squares from a free-field recording (well conditioned)."""
    n = 1 << int(math.ceil(math.log2(len(y) + len(dry))))
    Xd = np.fft.rfft(dry, n)
    ac = np.fft.irfft(np.abs(Xd) ** 2, n)[:ntap]
    xc = np.fft.irfft(np.fft.rfft(y, n) * np.conj(Xd), n)[:ntap]
    return solve_toeplitz(ac, xc)


def tail_read(y, dry, g, pre):
    """The room's part of one mic's recording: y less the outdoor self-path's prediction. Returns the room's band energy
    per unit dry band energy (noise corrected, from the PRE pre-roll), the direct path's (as a check on the volume), and
    the echo time from the free decay after the announcement ends (10 ms envelope, -5 to -25 dB or 5 dB over the floor
    if that comes first, x3: T20 as the truth's)."""
    yb = band(y, *PROBE_BAND)
    noise_pw = float(np.mean(yb[:pre] ** 2))
    pred = fftconvolve(dry, g)[:len(y) - pre]
    res = y.copy(); res[pre:pre + len(pred)] -= pred
    e_dry = float(np.sum(band(dry, *PROBE_BAND) ** 2))
    G_rev = bandE(res[pre:], noise_pw) / e_dry
    G_dir = bandE(np.concatenate([np.zeros(pre), pred])[pre:], 0.0) / e_dry
    # free decay: from the dry's last 10 ms frame within 20 dB of its peak
    blk = int(0.01 * SR)
    de = band(dry, *PROBE_BAND) ** 2
    nb = len(de) // blk
    fe = 10 * np.log10(de[:nb * blk].reshape(nb, blk).mean(1) + 1e-30)
    end = pre + (int(np.max(np.nonzero(fe > fe.max() - 20)[0])) + 1) * blk
    t = yb[end:]
    nt = len(t) // blk
    db = 10 * np.log10((t[:nt * blk].reshape(nt, blk) ** 2).mean(1) + 1e-30)
    fl = 10 * np.log10(noise_pw + 1e-30)
    T60 = None
    i_hi = next((i for i in range(nt) if db[i] < db[0] - 5), None)
    if i_hi is not None:
        i_lo = next((i for i in range(i_hi, nt) if db[i] < max(fl + 5, db[0] - 25)), nt)    # T20, as the truth's
        if i_lo - i_hi >= 4:
            slope = np.polyfit(np.arange(i_hi, i_lo) * blk / SR, db[i_hi:i_lo], 1)[0]
            T60 = -60.0 / slope if slope < 0 else None
    return G_rev, G_dir, T60, {'decay_db_over_floor': round(float(db[0] - fl), 1)}


def schroeder_t60(h):
    e = np.cumsum((h ** 2)[::-1])[::-1]
    db = 10 * np.log10(e / e[0] + 1e-30)
    i5, i25 = np.argmax(db < -5), np.argmax(db < -25)
    return 3 * (i25 - i5) / SR


def true_drr(h):
    pk = int(np.argmax(np.abs(h))); w = int(0.001 * SR)
    d = np.sum(h[max(0, pk - w):pk + w] ** 2); return d, np.sum(h ** 2) - d


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('ears'); ap.add_argument('--seed', type=int, default=0)
    a = ap.parse_args()
    rng = np.random.default_rng(a.seed)
    dry, sr = sf.read(str(PROBE), dtype='float64'); assert sr == SR
    talks = clean_onsets(a.ears, 16)
    s_rms = np.sqrt(np.mean(np.concatenate([p['x'][int(0.5 * SR):] for p in talks]) ** 2))
    dry = dry / np.sqrt(np.mean(dry ** 2)) * s_rms * 10 ** (PROBE_GAIN_DB / 20)
    pre = int(PRE_S * SR)
    tail = int(2.0 * SR)

    def record(h, sig):
        y = np.concatenate([np.zeros(pre), fftconvolve(dry, h), np.zeros(tail)])[:pre + len(dry) + tail]
        return y + rng.normal(0, sig, len(y))

    # the calibration, outdoors (free field: no reflections): the self-path on both mics, and the level 1 m on axis
    e_dry = float(np.sum(band(dry, *PROBE_BAND) ** 2))
    ff = pra.ShoeBox([40.0, 40.0, 40.0], fs=SR, max_order=0)
    ph = np.array([20.0, 20.0, 20.0]); spk = ph + [-PAIR_M / 2, 0, 0] + SPK_OFF
    ff.add_microphone_array(np.c_[ph + [-PAIR_M / 2, 0, 0], ph + [PAIR_M / 2, 0, 0], spk + [0, -1.0, 0]])
    ff.add_source(spk); ff.compute_rir()
    cal = {}
    for nd in NOISE_DB:
        sig = s_rms / (4 * math.pi) * 10 ** (-nd / 20)
        g = [self_path(record(ff.rir[m][0], sig)[pre:], dry) for m in (0, 1)]
        y1 = record(ff.rir[2][0], sig)
        n_pw = float(np.mean(band(y1, *PROBE_BAND)[:pre] ** 2))
        cal[nd] = {'g': g, 'G_1m': bandE(y1[pre:], n_pw) / e_dry}
    for sname, dim in SIZES.items():
        dim = np.array(dim)
        for rt in RT60S:
            e_abs, mo = pra.inverse_sabine(rt, dim)
            room = pra.ShoeBox(dim, fs=SR, materials=pra.Material(e_abs), max_order=min(mo, 150), air_absorption=False)
            phone = np.array([0.42 * dim[0], 0.45 * dim[1], 0.8])
            mics = np.c_[phone + [-PAIR_M / 2, 0, 0], phone + [PAIR_M / 2, 0, 0]]
            room.add_microphone_array(mics)
            room.add_source(mics[:, 0] + SPK_OFF)
            pos = []
            for r in DISTS:
                for _ in range(2):
                    for _try in range(200):
                        az = rng.uniform(0, 2 * math.pi)
                        h = 1.5 - 0.8
                        rh = math.sqrt(max(r ** 2 - h ** 2, 0.0)) if r > h else 0.0
                        p = phone + [rh * math.cos(az), rh * math.sin(az), (h if r > h else r)]
                        if np.all(p[:2] > 0.3) and np.all(p[:2] < dim[:2] - 0.3):
                            break
                    else:
                        continue
                    pos.append((r, p)); room.add_source(p)
            room.compute_rir()
            S = sum(2 * (dim[i] * dim[j]) for i, j in ((0, 1), (0, 2), (1, 2)))
            A_sab = S * e_abs                                         # Sabine's A with the model's own absorption
            rc_sab = math.sqrt(A_sab / (16 * math.pi))
            t60_true = float(np.mean([schroeder_t60(room.rir[m][k + 1]) for m in (0, 1) for k in range(len(pos))]))
            drr_t = []
            for k, (r, p) in enumerate(pos):
                dd = [true_drr(room.rir[m][k + 1]) for m in (0, 1)]
                drr_t.append(10 * math.log10(sum(d for d, _ in dd) / sum(f for _, f in dd)))
            drr_t = np.array(drr_t); lr = np.log10([r for r, _ in pos])
            rc_true = 10 ** np.mean((drr_t + 20 * lr) / 20)          # fixed slope -20
            for nd in NOISE_DB:
                sig = s_rms / (4 * math.pi) * 10 ** (-nd / 20)
                # the announcement
                reads = [tail_read(record(room.rir[m][0], sig), dry, cal[nd]['g'][m], pre) for m in (0, 1)]
                G_rev = float(np.mean([x[0] for x in reads]))
                t60s = [x[2] for x in reads if x[2]]
                rc_est = math.sqrt(cal[nd]['G_1m'] / G_rev) if G_rev > 0 else None
                # the talkers
                talkers = []
                for k, (r, p) in enumerate(pos):
                    for q in rng.choice(len(talks), N_TALK, replace=False):
                        x = talks[q]['x']
                        L = fftconvolve(x, room.rir[0][k + 1])[:len(x) + 4800]
                        R = fftconvolve(x, room.rir[1][k + 1])[:len(x) + 4800]
                        d0 = int(np.argmax(np.abs(room.rir[0][k + 1])))
                        L, R = L[d0:d0 + len(x)], R[d0:d0 + len(x)]
                        L = L + rng.normal(0, sig, len(L)); R = R + rng.normal(0, sig, len(R))
                        c = cdr_bands(np.stack([L, R], 1), PAIR_M, int(0.5 * SR))
                        talkers.append({'r': r, 'drr_true': round(float(drr_t[k]), 2),
                                        **{b: c[b] for b in ('LF_raw', 'MF', 'HF', 'ALL', 'MF_raw', 'ALL_raw')}})
                rec = {'size': sname, 'dim': dim.tolist(), 'rt60_nominal': rt, 'noise_db_under_talker_1m': nd,
                       'max_order': int(min(mo, 150)), 'rc_true': round(float(rc_true), 3), 'rc_sabine': round(rc_sab, 3),
                       't60_true': round(t60_true, 3), 'rc_probe': None if rc_est is None else round(rc_est, 3),
                       'A_probe': None if rc_est is None else round(16 * math.pi * rc_est ** 2, 2), 'A_sabine': round(A_sab, 2),
                       't60_probe': round(float(np.mean(t60s)), 3) if t60s else None,
                       'probe_reads': [x[3] for x in reads], 'G_1m_cal': cal[nd]['G_1m'], 'G_rev': G_rev, 'talkers': talkers}
                print(json.dumps(rec), flush=True)
                print(f'{sname} rt{rt} n{nd}: rc true {rc_true:.2f} sabine {rc_sab:.2f} probe {rc_est and round(rc_est, 2)}; '
                      f't60 true {t60_true:.2f} probe {rec["t60_probe"]}', file=sys.stderr, flush=True)


if __name__ == '__main__':
    main()
