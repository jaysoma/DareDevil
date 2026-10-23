#!/usr/bin/env python3
"""Is a talker's ref_vec its facing? Walking people mostly face where they go: per recording and talker, the angle
between the horizontal ref_vec and the horizontal walking direction over 0.1 s, while walking faster than 0.3 m/s.

usage: python3 facing_check.py DATA_DIR OUT.json
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

root, res = Path(sys.argv[1]), {}
for d in sorted(root.glob('*/task*/recording*/dicit')):
    for p in sorted(d.glob('position_source_*.txt')):
        s = pd.read_csv(p, sep='\t')
        t = (s.hour * 3600 + s.minute * 60 + s.second).to_numpy()
        X = s[['x', 'y']].to_numpy()
        v = (X[12:] - X[:-12]) / (t[12:] - t[:-12])[:, None]
        sp = np.linalg.norm(v, axis=1)
        m = sp > 0.3
        r = s[['ref_vec_x', 'ref_vec_y']].to_numpy()[6:-6][m]
        if not m.any():
            continue
        ang = np.degrees(np.arccos(np.clip((r * v[m]).sum(1) / np.linalg.norm(r, axis=1) / sp[m], -1, 1)))
        res[f"{d.parts[-4]}/{d.parts[-3]}/{d.parts[-2]}/{p.stem.replace('position_source_', '')}"] = {
            'walking_frames': int(m.sum()), 'median_deg': round(float(np.median(ang)), 1),
            'within_45': round(float(np.mean(ang < 45)), 3), 'beyond_135': round(float(np.mean(ang > 135)), 3)}
allang = list(res.values())
res['_all'] = {'talker_tracks': len(allang), 'median_of_medians': round(float(np.median([a['median_deg'] for a in allang])), 1),
               'worst_median': max(a['median_deg'] for a in allang),
               'mean_beyond_135': round(float(np.mean([a['beyond_135'] for a in allang])), 3)}
Path(sys.argv[2]).write_text(json.dumps(res, indent=1))
print(json.dumps(res['_all']))
