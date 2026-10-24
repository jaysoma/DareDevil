#!/usr/bin/env python3
"""Cut LOCATA utterances (tasks 3 and 4, DICIT array) with the truth on a time grid, for brief 21's update policies.

An utterance is one talker's array-aligned VAD (VAD_dicit_<talker>.txt) merged across gaps under GAP_S, which is brief
10's onset rule: it starts after at least GAP_S of that talker's silence. Its phrases are the VAD runs merged across
gaps under PHRASE_GAP_S. Pairs and truth as brief 10 (harness/batchA/locata/locata_cut.py, whose helpers are imported):
mics 5-10 (160 mm) and 6-9 (80 mm); the bearing is the exact two-mic delay to the tracked head in the schemes'
convention. On a GRID_S grid from the onset to the utterance's end, the truth holds:
  deg       the bearing
  dist      head to the pair's centre, m
  head_az   the head's horizontal orientation (ref_vec's azimuth), deg
  facing    the angle between the head's orientation and the direction to the array (0 = facing it), deg
  valid     the ground truth is marked valid (required_time.txt)
  phrase    which phrase of the utterance the time falls in, or -1 between phrases
The audio runs from PRE_S before the onset (the pause the schemes weigh against) to POST_S after the end.

usage: python3 cut_utterances.py LOCATA_DIR WORK_DIR   (writes utt_<set>_<task>_<rec>_<pair>.jsonl)
"""
import base64
import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import soundfile as sf

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'batchA' / 'locata'))
from locata_cut import PAIRS, SR, facing, interp, lateral, recordings, tod  # noqa: E402

GAP_S, PHRASE_GAP_S, GRID_S = 0.3, 0.1, 0.05
PRE_S, POST_S = 0.6, 0.1


def runs(v):
    e = np.flatnonzero(np.diff(np.r_[0, v.astype(np.int8), 0]))
    return [[int(a), int(b)] for a, b in zip(e[::2], e[1::2])]


def merge(rs, gap):
    out = []
    for a, b in rs:
        if out and a - out[-1][1] < gap * SR:
            out[-1][1] = b
        else:
            out.append([a, b])
    return out


def main():
    root, out = Path(sys.argv[1]), Path(sys.argv[2])
    out.mkdir(parents=True, exist_ok=True)
    total = 0
    for d in recordings(root):
        set_, task, rec = d.parts[-4], d.parts[-3], d.parts[-2]
        tag = f"{set_}_{task}_{rec.replace('recording', 'rec')}"
        a0 = pd.read_csv(d / 'position_array_dicit.txt', sep='\t').iloc[0]
        mics = {i: np.array([a0[f'mic{i}_x'], a0[f'mic{i}_y'], a0[f'mic{i}_z']]) for i in range(1, 16)}
        with open(d / 'audio_array_timestamps_dicit.txt') as fh:
            fh.readline()
            h, m, s = [float(v) for v in fh.readline().split('\t')[3:6]]
        t0 = h * 3600 + m * 60 + s
        req = pd.read_csv(d / 'required_time.txt', sep='\t')
        t_req, ok = tod(req), req['valid_flag'].to_numpy() > 0
        talkers = sorted(p.stem.replace('position_source_', '') for p in d.glob('position_source_*.txt'))
        x, sr = sf.read(str(d / 'audio_array_dicit.wav'), dtype='float64')
        assert sr == SR
        for spacing, (il, ir) in PAIRS.items():
            ml, mr = mics[il], mics[ir]
            centre = (ml + mr) / 2
            x2 = x[:, [il - 1, ir - 1]]
            g = 0.5 * 32767 / np.abs(x2).max()
            rows = []
            for tk in talkers:
                ps = pd.read_csv(d / f'position_source_{tk}.txt', sep='\t')
                pt, pos, ref = tod(ps), ps[['x', 'y', 'z']].to_numpy(), ps[['ref_vec_x', 'ref_vec_y', 'ref_vec_z']].to_numpy()
                v = pd.read_csv(d / f'VAD_dicit_{tk}.txt', sep='\t')['VAD'].to_numpy() > 0
                phr_all = merge(runs(v), PHRASE_GAP_S)
                for k, (a, b) in enumerate(merge(runs(v), GAP_S)):
                    lo, hi = a - int(PRE_S * SR), b + int(POST_S * SR)
                    if lo < 0 or hi > len(x2):
                        continue
                    phr = [p for p in phr_all if p[0] >= a and p[1] <= b]
                    grid = []
                    for n in range(int((b - a) / SR / GRID_S) + 1):
                        smp = a + int(n * GRID_S * SR)
                        t = t0 + smp / SR
                        head, rv = interp(pt, pos, t), interp(pt, ref, t)
                        pi = next((i for i, p in enumerate(phr) if p[0] <= smp < p[1]), -1)
                        grid.append({'t': round(n * GRID_S, 3), 'deg': round(lateral(head, ml, mr), 2),
                                     'dist': round(float(np.linalg.norm(head - centre)), 3),
                                     'head_az': round(math.degrees(math.atan2(rv[1], rv[0])), 1),
                                     'facing': facing(head, rv, centre),
                                     'valid': bool(np.interp(t, t_req, ok.astype(float)) > 0.5), 'phrase': pi})
                    seg = np.clip(x2[lo:hi] * g, -32768, 32767).astype('<i2')
                    rows.append({'id': f'{tag}/{tk}/{spacing}/{k}', 'recording': tag, 'talker': tk, 'pair_mm': spacing,
                                 'utt': k, 'onset_s': round(a / SR, 3), 'dur_s': round((b - a) / SR, 3),
                                 'baseline_m': round(float(np.linalg.norm(mr - ml)), 5), 'onset_sample': int(PRE_S * SR),
                                 'phrases': [[round((p[0] - a) / SR, 3), round((p[1] - a) / SR, 3)] for p in phr],
                                 'gain': g, 'truth': grid,
                                 'L': base64.b64encode(seg[:, 0].tobytes()).decode(),
                                 'R': base64.b64encode(seg[:, 1].tobytes()).decode()})
            with open(out / f'utt_{tag}_{spacing}.jsonl', 'w') as fh:
                for r in rows:
                    fh.write(json.dumps(r) + '\n')
            total += len(rows)
            print(f'{tag} {spacing} mm: {len(rows)} utterances', flush=True)
    print(f'{total} utterance cuts')


if __name__ == '__main__':
    main()
