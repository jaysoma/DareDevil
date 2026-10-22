#!/usr/bin/env python3
"""Cut single-talker speech onsets out of STARSS23 (MIC format) for a chosen capsule pair, with tracker truth.

Metadata rows (DCASE 2024 format): frame (100 ms), class, source index, azimuth, elevation, distance (cm).
Classes 0 and 1 are female and male speech. A cut is kept only when that speech source is the only active
event for at least MIN_SOLO_S from its onset, so the truth is unambiguous.
"""
import argparse
import base64
import csv
import json
import math
from pathlib import Path

import numpy as np
import soundfile as sf
from scipy.signal import resample_poly

SPEECH = {0, 1}
FRAME_S = 0.1
PRE_S, POST_S, MIN_SOLO_S = 0.5, 1.0, 1.0
R = 0.042
CAPS = {1: (45, 35), 2: (-45, -35), 3: (135, -35), 4: (-135, 35)}


def cap_xyz(n):
    az, el = (math.radians(v) for v in CAPS[n])
    return np.array([R * math.cos(el) * math.cos(az), R * math.cos(el) * math.sin(az), R * math.sin(el)])


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
            az, el = float(r[3]), float(r[4])
            dist = float(r[5]) if len(r) > 5 and r[5] != '' else None
            rows.setdefault(f, []).append((cls, src, az, el, dist))
    return rows


def onsets(rows):
    """(frame, cls, src, az, el, dist) where a speech source starts and stays the only event for MIN_SOLO_S."""
    need = int(round(MIN_SOLO_S / FRAME_S))
    out = []
    for f in sorted(rows):
        for cls, src, az, el, dist in rows[f]:
            if cls not in SPEECH:
                continue
            if any(c == cls and s == src for c, s, *_ in rows.get(f - 1, [])):
                continue                                   # not an onset
            solo = all(len(rows.get(f + k, [])) == 1 and rows[f + k][0][:2] == (cls, src) for k in range(need))
            if not solo or (f - 1 in rows and rows[f - 1]):
                continue                                   # something else sounding at or just before the onset
            out.append((f, cls, src, az, el, dist))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('root')
    ap.add_argument('--pair', nargs=2, type=int, default=[1, 2])
    ap.add_argument('--out', default='cuts.jsonl')
    a = ap.parse_args()
    root = Path(a.root)
    p1, p2 = cap_xyz(a.pair[0]), cap_xyz(a.pair[1])
    d = float(np.linalg.norm(p2 - p1))
    axis = (p2 - p1) / d
    n = 0
    with open(a.out, 'w') as out:
        for wav in sorted(root.glob('mic_dev/**/*.wav')):
            metas = list(root.glob(f'metadata_dev/**/{wav.stem}.csv'))
            if not metas:
                continue
            x, sr = sf.read(str(wav), dtype='float32')
            rows = load_meta(metas[0])
            for f, cls, src, az, el, dist in onsets(rows):
                t = f * FRAME_S
                i0, i1 = int((t - PRE_S) * sr), int((t + POST_S) * sr)
                if i0 < 0 or i1 > len(x):
                    continue
                seg = resample_poly(x[i0:i1, [a.pair[0] - 1, a.pair[1] - 1]], 2, 1, axis=0)   # 24 -> 48 kHz
                pcm = np.clip(seg * 32767, -32768, 32767).astype('<i2')
                lat = math.degrees(math.asin(max(-1, min(1, float(unit(az, el) @ axis)))))
                room = wav.parent.name
                out.write(json.dumps({
                    'file': wav.stem, 'room_fold': room, 'room': wav.stem.split('_')[1] if '_' in wav.stem else room,
                    'onset_s': round(t, 2), 'cls': cls, 'src': src, 'az': az, 'el': el, 'dist_cm': dist,
                    'pair': a.pair, 'baseline_m': round(d, 5), 'truth_lateral': round(lat, 2),
                    'onset_sample': int(PRE_S * 48000), 'L': base64.b64encode(pcm[:, 0].tobytes()).decode(),
                    'R': base64.b64encode(pcm[:, 1].tobytes()).decode()}) + '\n')
                n += 1
    print(f'{n} single-talker speech onsets, pair {a.pair}, baseline {d * 1000:.1f} mm -> {a.out}')


if __name__ == '__main__':
    main()
