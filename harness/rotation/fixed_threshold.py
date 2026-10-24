#!/usr/bin/env python3
"""No reference at all (2026-10-24, Jay: "Every utterance at this stage is a new speaker"): one fixed number on the
contrast (CDR 4-8 kHz minus CDR 0.1-1.1 kHz, pooled per stop), chosen on the other walks."""
import io, contextlib, runpy
import numpy as np
with contextlib.redirect_stdout(io.StringIO()):
    g = runpy.run_path(str(__import__('pathlib').Path(__file__).with_name('room_reference.py')))
S, walks = g['S'], g['walks']
c = np.array([s['c'] for s in S]); y = np.array([s['toward'] for s in S]); w = np.array([s['walk'] for s in S])
tp = tn = 0; ths = []
for wk in walks:
    tr, te = w != wk, w == wk
    th = max(np.arange(-15, 15.01, 0.25), key=lambda t: (np.mean(c[tr & y] >= t) + np.mean(c[tr & ~y] < t)) / 2)
    ths.append(th); tp += np.sum(c[te & y] >= th); tn += np.sum(c[te & ~y] < th)
print(f"facing {c[y].mean():+.1f} dB (sd {c[y].std():.1f}, n {y.sum()}), turned {c[~y].mean():+.1f} (sd {c[~y].std():.1f}, n {(~y).sum()}); "
      f"fixed threshold {min(ths):+.2f} to {max(ths):+.2f} dB: {tp}/{y.sum()} facing, {tn}/{(~y).sum()} turned, balanced {(tp / y.sum() + tn / (~y).sum()) / 2 * 100:.0f}%")
