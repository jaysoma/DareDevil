#!/usr/bin/env python3
"""Brief H's Conductor test (2026-10-24): v14's CDR frames on a synthetic tape, no audio needed. Exits non-zero on any
failure.

    <Whisper venv python> harness/rotation/inapp/test_conductor.py

THE TAPE (8 s, 48 kHz): a faint diffuse hiss throughout, and two bursts of a coherent source arriving 3 samples apart:
3 s from 1.0 s (the opener, which goes through the provisional path) and 0.6 s from 5.5 s (closed by the ears' one
second of quiet before its 2 s frame).
THE CHECKS
    - no CDR frame is handed while the session's first utterance is provisional
    - every frame carries 8 values; the first six are the three range bands, cold from the onset (brief E's own
      estimator, harness/rotation/range/reads.py), the last two 0.1-1.1 kHz unfloored
    - the first frame ends 0.1813 s after the onset and the last by 2.0 s (hops 13-183: 171 frames)
    - the short utterance stops at its close: no frame of its hop 183
"""
import json
import math
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / 'src'))
sys.path.insert(0, str(REPO / 'harness/rotation/range'))
from geonar import conductor as C  # noqa: E402
from reads import BANDS, Stream  # noqa: E402  (brief E's estimator: L100, L125, L500, B1, B2, B3)

SR, D = 48000, 0.157
failed = 0


def check(ok, what):
    global failed
    failed += not ok
    print(('ok   ' if ok else 'FAIL ') + what)


class Tape:
    def __init__(self, x):
        self.x, self.frames = x, len(x)

    def raw(self, start, n):
        if start < 0 or n <= 0 or start + n > self.frames:
            return None
        return self.x[start:start + n, 0], self.x[start:start + n, 1]

    def close(self):
        pass


def tape():
    rng = np.random.default_rng(14)
    n = 8 * SR
    x = rng.normal(0, 20, (n, 2))                                       # the hiss, independent per capsule
    for t0, dur in ((1.0, 3.0), (5.5, 0.6)):
        a, b = int(t0 * SR), int((t0 + dur) * SR)
        s = rng.normal(0, 3000, b - a + 3)
        x[a:b, 0] += s[3:]; x[a:b, 1] += s[:-3]                         # one source, 3 samples apart
        x[a:b] += rng.normal(0, 600, (b - a, 2))                        # and its room
    return np.clip(x, -32768, 32767).astype(np.int16)


def main():
    x = tape()
    items = []
    c = C.Conductor('synthetic', Tape(x), D, items.append)
    c.open(gate={'version': 'attacks'}, inputs=[])
    onset_at = None
    early = 0
    for now in range(C.CHUNK, len(x) + 1, C.CHUNK):
        c.step(now)
        if onset_at is None and any(i.get('event') == 'onset' for i in items):
            onset_at = len(items)
        if onset_at is None:
            early += sum(i.get('to') == 'range' for i in items)
    c.close(len(x))
    check(early == 0, f'no CDR frames while provisional ({early} handed)')
    opens = {i['utt']: i['onset_s'] for i in items if i.get('event') in ('open', 'onset') and not i.get('provisional')}
    frames = {}
    for i in items:
        if i.get('to') == 'range':
            frames.setdefault(i['utt'], []).extend(i['frames'])
    check(len(opens) == 2, f'two utterances heard ({len(opens)}: {json.dumps({k: round(v, 3) for k, v in opens.items()})})')
    long_u, short_u = sorted(opens, key=lambda u: opens[u])[:2]
    for u, label in ((long_u, 'the opener (3 s)'), (short_u, 'the short one (0.6 s)')):
        fr, on = frames.get(u, []), opens[u]
        check(all(len(f['cdrf']) == 8 for f in fr), f'{label}: every frame carries 8 values ({len(fr)} frames)')
        ages = [f['t'] - on for f in fr]
        check(fr and abs(ages[0] - (13 * 512 + 2048) / SR) < 2e-4, f'{label}: first frame ends {ages[0]:.4f} s after the onset')
        check(max(ages) <= C.FACING_READ_S + 1e-4, f'{label}: last frame ends {max(ages):.4f} s after the onset')
    check(len(frames[long_u]) == 171, f'the opener: hops 13-183, 171 frames ({len(frames[long_u])})')
    check(max(f['t'] - opens[short_u] for f in frames[short_u]) < (183 * 512 + 2048) / SR - 1e-3,
          'the short one: closed before its hop 183, so no 2 s frame')
    # the values, against brief E's estimator run cold from the opener's onset
    on = int(round(opens[long_u] * SR))
    xs = x.astype(np.float64) / 32768.0
    Dp, Rp = Stream(D).run(xs, on, 184)
    order = [BANDS.index(b) for b in BANDS if b[0] in ('B1', 'B2', 'B3')] + [0]             # B1, B2, B3, then L100
    gap = 0.0
    for f in frames[long_u]:
        k = round(((f['t'] - opens[long_u]) * SR - 2048) / 512)      # t is stamped to 0.1 ms
        want = [10 * math.log10(max(v, 1e-30)) for j in order for v in (Dp[k, j], Rp[k, j])]
        gap = max(gap, max(abs(a - b) for a, b in zip(f['cdrf'], want)))
    check(gap < 1e-3, f'the opener: all 8 values match brief E\'s estimator, cold from the onset (largest gap {gap:.2e} dB)')
    print(f'{failed} failed' if failed else 'all passed')
    sys.exit(1 if failed else 0)


if __name__ == '__main__':
    main()
