#!/usr/bin/env python3
"""Cut LOCATA talker onsets (tasks 3 and 4, DICIT array) for batch A, with OptiTrack truth.

LOCATA (https://zenodo.org/records/3630471): one room, a 15-mic DICIT array, talkers wearing OptiTrack markers (head
position and orientation at ~120 Hz), voice activity per source per audio sample. Tasks 3 (one moving talker) and 4
(several moving talkers), dev and eval sets.

Pairs: the two centred on the array's middle mic 7, mics 5-10 (160 mm, the phone is 157) and 6-9 (80 mm). L is the
first mic named. Mics run along the array's x axis; it looks along +y.

An onset is where a talker's array-aligned VAD (VAD_dicit_<talker>.txt) turns on after at least MIN_PAUSE_S off,
inside a stretch the ground truth marks valid (required_time.txt). A cut is 0.5 s before it to 1.0 s after, as a
STARSS23 cut; the onset is at onset_sample. Truth at the onset time:
  deg          the exact two-mic delay to the talker's head, as the schemes define it: R(t) = L(t - tau),
               deg = asin(-tau c / d), c = 343
  deg_end      the same 0.5 s later (talkers walk: how far the truth moved across GccPhat's half second)
  dist_m       head to the pair's centre
  facing_deg   the talker's facing (the head's ref_vec, horizontal) against the direction from the head to the array:
               0 = facing the array, 180 = facing away. ref_vec is checked to be the facing (it follows the walking
               direction) in report.md.
  others       every other talker voice-active in the 0.5 s before or after the onset, with its deg and the share of
               each half second it was active (before, during)
Clues read from the same audio (no scheme involved): snr_db, the voice's level (onset to +0.5 s) over the pause's
(-0.5 s to the onset), both mics, in 300-1100 Hz (mf), 1.1-3 kHz (hf1), 3-8 kHz (hf2); and spec, the voice's power
share in third-octave bands over 300-8000 Hz, for the aliasing class.

usage: python3 locata_cut.py DATA_DIR OUT_DIR   (writes cuts_<set>_task<k>_rec<n>_<pair>.jsonl with audio and
       truth_*.jsonl without)
"""
import base64
import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import soundfile as sf

SR = 48000
C = 343.0
PAIRS = {160: (5, 10), 80: (6, 9)}
PRE_S, POST_S = 0.5, 1.0
MIN_PAUSE_S = 0.3                     # the talker silent this long before an onset
OTHER_S = 0.5
BANDS = {'mf': (300, 1100), 'hf1': (1100, 3000), 'hf2': (3000, 8000)}
THIRDS = [round(1000 * 2 ** (k / 3), 1) for k in range(-5, 13)]   # 315 Hz .. 16 kHz centres; those inside 300-8000 used


def tod(df):
    """Time of day in seconds from the year/month/day/hour/minute/second columns."""
    return df['hour'].to_numpy() * 3600 + df['minute'].to_numpy() * 60 + df['second'].to_numpy()


def interp(t_src, vals, t):
    return np.array([np.interp(t, t_src, vals[:, k]) for k in range(vals.shape[1])])


def lateral(src, ml, mr):
    d = np.linalg.norm(mr - ml)
    tau = (np.linalg.norm(src - mr) - np.linalg.norm(src - ml)) / C
    return math.degrees(math.asin(max(-1.0, min(1.0, -tau * C / d))))


def facing(head, ref, centre):
    """Angle between the head's horizontal ref_vec and the horizontal direction from the head to the array (deg)."""
    a = np.array([ref[0], ref[1]])
    b = np.array([centre[0] - head[0], centre[1] - head[1]])
    if np.linalg.norm(a) < 1e-9 or np.linalg.norm(b) < 1e-9:
        return None
    cos = float(a @ b / np.linalg.norm(a) / np.linalg.norm(b))
    return round(math.degrees(math.acos(max(-1.0, min(1.0, cos)))), 1)


def band_power(x, lo, hi):
    X = np.fft.rfft(x * np.hanning(len(x))[:, None], axis=0)
    f = np.fft.rfftfreq(len(x), 1 / SR)
    m = (f >= lo) & (f < hi)
    return float((np.abs(X[m]) ** 2).sum())


def clues(x2, on):
    """Band SNRs (voice over pause, dB) and the voice's third-octave power shares."""
    pre, voice = x2[on - int(0.5 * SR):on], x2[on:on + int(0.5 * SR)]
    snr = {}
    for k, (lo, hi) in BANDS.items():
        snr[k] = round(10 * math.log10((band_power(voice, lo, hi) + 1e-20) / (band_power(pre, lo, hi) + 1e-20)), 1)
    X = np.abs(np.fft.rfft(voice * np.hanning(len(voice))[:, None], axis=0)) ** 2
    f = np.fft.rfftfreq(len(voice), 1 / SR)
    tot = X[(f >= 300) & (f < 8000)].sum()
    spec = []
    for fc in THIRDS:
        lo, hi = fc / 2 ** (1 / 6), fc * 2 ** (1 / 6)
        if lo < 300 or hi > 8000:
            continue
        spec.append([fc, round(float(X[(f >= lo) & (f < hi)].sum() / max(tot, 1e-30)), 4)])
    return snr, spec


def recordings(root):
    for d in sorted(root.glob('*/task*/recording*/dicit')):
        if (d / 'audio_array_dicit.wav').exists():
            yield d


def main():
    root, out = Path(sys.argv[1]), Path(sys.argv[2])
    out.mkdir(parents=True, exist_ok=True)
    total = 0
    for d in recordings(root):
        set_, task, rec = d.parts[-4], d.parts[-3], d.parts[-2]
        tag = f"{set_}_{task}_{rec.replace('recording', 'rec')}"
        arr = pd.read_csv(d / 'position_array_dicit.txt', sep='\t')
        a0 = arr.iloc[0]
        mics = {i: np.array([a0[f'mic{i}_x'], a0[f'mic{i}_y'], a0[f'mic{i}_z']]) for i in range(1, 16)}
        with open(d / 'audio_array_timestamps_dicit.txt') as fh:
            fh.readline()
            h, m, s = [float(v) for v in fh.readline().split('\t')[3:6]]
        t0 = h * 3600 + m * 60 + s                                  # time of day of audio sample 0
        req = pd.read_csv(d / 'required_time.txt', sep='\t')
        t_req, ok = tod(req), req['valid_flag'].to_numpy() > 0
        talkers = sorted(p.stem.replace('position_source_', '') for p in d.glob('position_source_*.txt'))
        pos, vad = {}, {}
        for tk in talkers:
            ps = pd.read_csv(d / f'position_source_{tk}.txt', sep='\t')
            pos[tk] = (tod(ps), ps[['x', 'y', 'z']].to_numpy(), ps[['ref_vec_x', 'ref_vec_y', 'ref_vec_z']].to_numpy())
            vad[tk] = pd.read_csv(d / f'VAD_dicit_{tk}.txt', sep='\t')['VAD'].to_numpy() > 0
        x, sr = sf.read(str(d / 'audio_array_dicit.wav'), dtype='float64')
        assert sr == SR
        at = lambda tk, t: (interp(pos[tk][0], pos[tk][1], t), interp(pos[tk][0], pos[tk][2], t))
        valid = lambda t: bool(np.interp(t, t_req, ok.astype(float)) > 0.5)
        for spacing, (il, ir) in PAIRS.items():
            ml, mr = mics[il], mics[ir]
            centre = (ml + mr) / 2
            x2 = x[:, [il - 1, ir - 1]]
            g = 0.5 * 32767 / np.abs(x2).max()                    # one gain per recording and pair: levels comparable
            rows = []
            for tk in talkers:
                v = vad[tk]
                edges = np.flatnonzero(v[1:] & ~v[:-1]) + 1
                for on in edges:
                    if on < int(PRE_S * SR) or on + int(POST_S * SR) > len(x2):
                        continue
                    if v[on - int(MIN_PAUSE_S * SR):on].any():
                        continue
                    t = t0 + on / SR
                    if not (valid(t) and valid(t + 0.5)):
                        continue
                    head, ref = at(tk, t)
                    head_end, _ = at(tk, t + 0.5)
                    others = []
                    for ot in talkers:
                        if ot == tk:
                            continue
                        before = vad[ot][max(0, on - int(OTHER_S * SR)):on]
                        during = vad[ot][on:on + int(OTHER_S * SR)]
                        if before.any() or during.any():
                            others.append({'deg': round(lateral(at(ot, t)[0], ml, mr), 2), 'class': 'talker', 'who': ot,
                                           'before': round(float(before.mean()), 2), 'during': round(float(during.mean()), 2)})
                    snr, spec = clues(x2, on)
                    seg = x2[on - int(PRE_S * SR):on + int(POST_S * SR)] * g
                    pcm = np.clip(seg, -32768, 32767).astype('<i2')
                    rows.append({
                        'dataset': 'locata', 'scenario': f'{tag} {tk} {spacing}mm',
                        'id': f'{tag}/{tk}/{spacing}/{on / SR:.3f}', 'pair_mm': spacing, 'mics': [il, ir],
                        'set': set_, 'task': task, 'recording': rec, 'talker': tk, 'onset_s': round(on / SR, 3),
                        'baseline_m': round(float(np.linalg.norm(mr - ml)), 5), 'onset_sample': int(PRE_S * SR),
                        'centre': [round(float(q), 4) for q in centre],
                        'truth': {'deg': round(lateral(head, ml, mr), 2), 'dist_m': round(float(np.linalg.norm(head - centre)), 3),
                                  'facing_deg': facing(head, ref, centre), 'others': others,
                                  'deg_end': round(lateral(head_end, ml, mr), 2),
                                  'head': [round(float(q), 3) for q in head], 'height_m': round(float(head[2]), 3)},
                        'snr_db': snr, 'spec': spec, 'gain': g,
                        'L': base64.b64encode(pcm[:, 0].tobytes()).decode(),
                        'R': base64.b64encode(pcm[:, 1].tobytes()).decode()})
            with open(out / f'cuts_{tag}_{spacing}.jsonl', 'w') as fh:
                for r in rows:
                    fh.write(json.dumps(r) + '\n')
            total += len(rows)
            print(f'{tag} {spacing} mm: {len(rows)} onsets from {len(talkers)} talker(s)', flush=True)
    print(f'{total} cuts')


if __name__ == '__main__':
    main()
