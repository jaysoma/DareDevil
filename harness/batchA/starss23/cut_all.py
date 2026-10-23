#!/usr/bin/env python3
"""Batch A cuts from STARSS23 (MIC format), one capsule pair: EVERY onset of EVERY class, streamed.

An onset is a frame (100 ms) where a source (class, source index) is active and was not in the frame before. Unlike
harness/starss23/starss_cut.py, nothing is required to be alone: the other sources active around the onset are the
point (brief 9's "another labelled source" class). Each onset records:
  - kind: 'speech' (classes 0, 1) or 'other' (footsteps, door, knock, ...): Stage 1 renders every sound;
  - solo: starss_cut.py's test (the only event for MIN_SOLO_S from the onset, and nothing in the frame before), so the
    old single-talker set is the solo speech subset and its reads can be checked against the earlier runs;
  - the tracker's direction and distance at the onset frame, and the lateral angle for this pair, plus the lateral span
    over the onset's first half second (a moving source shows here);
  - others: every other source active from 0.5 s before the onset to 0.5 s after (the pause the schemes look at, and
    GccPhat's half second), with its class, its lateral angle at the active frame nearest the onset, and whether it was
    sounding before the onset, after it, or both.

Same cut as starss_cut.py: 0.5 s before to 1.0 s after the onset, 24 -> 48 kHz, onset at sample 24000.

stdout: one JSON line per cut with the audio (base64 int16), for runner.mjs / range_cues.py.
--truth FILE: the same lines without audio.
usage: cut_all.py <starss23 root> --pair 1 2 [--truth truth_12.jsonl] [--limit N]
"""
import argparse
import base64
import csv
import json
import math
import sys
from pathlib import Path

import numpy as np
import soundfile as sf
from scipy.signal import resample_poly

CLASSES = ['female speech', 'male speech', 'clapping', 'telephone', 'laughter', 'domestic sounds', 'footsteps',
           'door/cupboard', 'music', 'musical instrument', 'water tap', 'bell', 'knock']
SPEECH = {0, 1}
FRAME_S = 0.1
PRE_S, POST_S, MIN_SOLO_S = 0.5, 1.0, 1.0
AROUND = 5                      # frames either side of the onset searched for other sources (0.5 s)
R = 0.042
CAPS = {1: (45, 35), 2: (-45, -35), 3: (135, -35), 4: (-135, 35)}


def unit(az_deg, el_deg):
    az, el = math.radians(az_deg), math.radians(el_deg)
    return np.array([math.cos(el) * math.cos(az), math.cos(el) * math.sin(az), math.sin(el)])


def load_meta(path):
    rows = {}
    with open(path, newline='') as fh:
        for r in csv.reader(fh):
            if not r:
                continue
            f, cls, src = int(r[0]), int(r[1]), int(r[2])
            dist = float(r[5]) if len(r) > 5 and r[5] != '' else None
            rows.setdefault(f, {})[(cls, src)] = (float(r[3]), float(r[4]), dist)
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('root')
    ap.add_argument('--pair', nargs=2, type=int, default=[1, 2])
    ap.add_argument('--truth')
    ap.add_argument('--limit', type=int)
    a = ap.parse_args()
    root = Path(a.root)
    p1, p2 = unit(*CAPS[a.pair[0]]) * R, unit(*CAPS[a.pair[1]]) * R
    d = float(np.linalg.norm(p2 - p1))
    axis = (p2 - p1) / d
    lat = lambda az, el: round(math.degrees(math.asin(max(-1.0, min(1.0, float(unit(az, el) @ axis))))), 2)
    need = int(round(MIN_SOLO_S / FRAME_S))
    tr = open(a.truth, 'w') if a.truth else None
    n = 0
    for wav in sorted(root.glob('mic_dev/**/*.wav')):
        metas = list(root.glob(f'metadata_dev/**/{wav.stem}.csv'))
        if not metas:
            continue
        rows = load_meta(metas[0])
        info = sf.info(str(wav))
        sr, total = info.samplerate, info.frames
        x = None
        for f in sorted(rows):
            for (cls, src), (az, el, dist) in sorted(rows[f].items()):
                if (cls, src) in rows.get(f - 1, {}):
                    continue                                   # not an onset
                t = f * FRAME_S
                i0, i1 = int((t - PRE_S) * sr), int((t + POST_S) * sr)          # as starss_cut.py, sample for sample
                if i0 < 0 or i1 > total:
                    continue
                solo = all(list(rows.get(f + k, {})) == [(cls, src)] for k in range(need)) and not rows.get(f - 1)
                span = [lat(*rows[g][(cls, src)][:2]) for g in range(f, f + AROUND + 1) if (cls, src) in rows.get(g, {})]
                others = {}
                for g in range(f - AROUND, f + AROUND + 1):
                    for key, (oaz, oel, odist) in rows.get(g, {}).items():
                        if key == (cls, src):
                            continue
                        o = others.setdefault(key, {'cls': key[0], 'src': key[1], 'class': CLASSES[key[0]],
                                                    'before': False, 'during': False, 'near': None})
                        if g < f: o['before'] = True
                        else: o['during'] = True
                        if o['near'] is None or abs(g - f) < abs(o['near'][0] - f):
                            o['near'] = (g, oaz, oel, odist)
                oth = []
                for o in others.values():
                    g, oaz, oel, odist = o.pop('near')
                    oth.append(dict(o, deg=lat(oaz, oel), az=oaz, el=oel, dist_cm=odist, frame_offset=g - f))
                rec = {'file': wav.stem, 'room_fold': wav.parent.name, 'room': wav.stem.split('_')[1],
                       'onset_s': round(t, 2), 'cls': cls, 'class': CLASSES[cls], 'kind': 'speech' if cls in SPEECH else 'other',
                       'src': src, 'az': az, 'el': el, 'dist_cm': dist, 'solo': solo, 'pair': a.pair,
                       'baseline_m': round(d, 5), 'truth_lateral': lat(az, el), 'lateral_span': [min(span), max(span)],
                       'others': oth, 'onset_sample': int(PRE_S * 48000)}
                if tr:
                    tr.write(json.dumps(rec) + '\n')
                if x is None:
                    x, _ = sf.read(str(wav), dtype='float32')
                seg = resample_poly(x[i0:i1, [a.pair[0] - 1, a.pair[1] - 1]], 2, 1, axis=0)   # 24 -> 48 kHz
                pcm = np.clip(seg * 32767, -32768, 32767).astype('<i2')
                rec['L'] = base64.b64encode(pcm[:, 0].tobytes()).decode()
                rec['R'] = base64.b64encode(pcm[:, 1].tobytes()).decode()
                sys.stdout.write(json.dumps(rec) + '\n')
                n += 1
                if a.limit and n >= a.limit:
                    print(f'{n} onsets (limit), pair {a.pair}', file=sys.stderr)
                    return
    print(f'{n} onsets, pair {a.pair}, baseline {d * 1000:.1f} mm', file=sys.stderr)


if __name__ == '__main__':
    main()
