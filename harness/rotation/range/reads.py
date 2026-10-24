#!/usr/bin/env python3
"""Brief E's reads (2026-10-24): every utterance's CDR band powers, as the Conductor reads them, on Jay's rotation walks
and ladders and on LOCATA. Run on Jay's box, where the audio is; writes results/rotation/range/reads.json (no audio).

    <Whisper venv python> harness/rotation/range/reads.py --root C:/Projects/GithubRoot/Dictate/captures/geonar/tapes

THE ONSETS. Jay's walks: the Conductor's own ears (src/geonar/attacks.py), fed the tape in its 512-sample CHUNKs, every
open a fresh utterance that closes where the next opens or at the ears' own close (conductor.py _listen/at, WALK_BACK
off). LOCATA: the animation files' scored events (results/animation/locata/*.json, bake.py's onsets), each closed at the
end of the talker's speech span it opens; their truth (tracked distance, facing) comes with them.

THE READ is conductor.py _due's, v13: a CdrFreeStream started cold at the onset, the frames whose window starts at
onset + SETTLE_S or later, and
    short   those whose window ENDS by onset + RANGE_READ_S (0.5 s): 30 frames, what CdrRange reads today
    whole   every frame to the utterance's close, capped at CAP_S (an utterance the ears never close can run 20 s
            across a turn; a callout opens a fresh utterance, so a read rarely crosses into the next stop)
Per band the direct and diffuse powers are summed over the frames and kept as dB; the ratio is taken by the scorer.

THE BANDS: the Conductor's three (floored at c/2d) and four below c/2d, run UNFLOORED -- the diffuse field is coherent
across the pair there too, so the formula is ill-conditioned (brief 20), and kept as flagged:
    L100   0.1-1.1 kHz raw (the facing contrast's low band)   L125  125-500 Hz raw   L500  0.5-1.1 kHz raw
    B1 1.1-2   B2 2-4   B3 4-8 kHz (floored)
THE BEARING per read: GCC-PHAT over 3-8 kHz on the read's first 0.5 s, the peak lag as an angle off broadside; only
used by the gated candidate to ask "the same spot, within 5 deg?".
"""
import argparse
import glob
import json
import math
import sys
from pathlib import Path

import numpy as np
import soundfile as sf

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / 'src'))
from geonar.attacks import Attacks  # noqa: E402
from geonar.cdr_direct import ALPHA, C, HOP, NFFT, SR, CdrFreeStream  # noqa: E402

SETTLE_S, RANGE_READ_S, CHUNK = 0.13, 0.5, 512        # conductor.py
CAP_S = 6.0                                           # a whole-utterance read stops here (a 20 s utterance adds nothing)
BANDS = (('L100', 100, 1100, False), ('L125', 125, 500, False), ('L500', 500, 1100, False),
         ('B1', 1100, 2000, True), ('B2', 2000, 4000, True), ('B3', 4000, 8000, True))
LADDER_WALKS = ('walk-213304', 'walk-221126', 'walk-020305', 'walk-224302')


class Stream:
    """CdrFreeStream over BANDS, the floored ones floored at c/2d and the rest not; batched over a whole read."""

    def __init__(self, d):
        f = np.fft.rfftfreq(NFFT, 1.0 / SR)
        self.gn = np.sinc(2 * f * d / C)
        self.masks = np.array([(f >= (max(lo, C / (2 * d)) if fl else lo)) & (f < hi) for _, lo, hi, fl in BANDS], float)
        self.win = np.hanning(NFFT)

    def run(self, x, onset, n_hops):
        """Per-hop (direct, diffuse) band powers for hops onset + k*HOP, k < n_hops, from a cold start at the onset."""
        seg = np.stack([x[onset + k * HOP: onset + k * HOP + NFFT] for k in range(n_hops)])
        X1 = np.fft.rfft(seg[:, :, 0] * self.win, axis=1); X2 = np.fft.rfft(seg[:, :, 1] * self.win, axis=1)
        a11, a22, a12 = np.abs(X1) ** 2, np.abs(X2) ** 2, X1 * np.conj(X2)
        D = np.zeros((n_hops, len(BANDS))); R = np.zeros_like(D)
        p = None
        for k in range(n_hops):
            now = (a11[k], a22[k], a12[k])
            p = now if p is None else tuple(ALPHA * o + (1 - ALPHA) * nw for o, nw in zip(p, now))
            p11, p22, p12 = p
            gx = p12 / (np.sqrt(p11 * p22) + 1e-20)
            xx, rr, gn = np.abs(gx) ** 2, np.real(gx), self.gn
            disc = np.maximum(gn ** 2 * rr ** 2 - gn ** 2 * xx + gn ** 2 - 2 * gn * rr + xx, 0.)
            c = np.clip((xx - gn * rr + np.sqrt(disc)) / np.maximum(1 - xx, 1e-6), 0., 1e4)
            frac, pw = c / (1 + c), .5 * (p11 + p22)
            D[k] = self.masks @ (frac * pw); R[k] = self.masks @ ((1 - frac) * pw)
        return D, R


def gcc_deg(x, onset, d):
    """GCC-PHAT, 3-8 kHz, over the first 0.5 s from the onset: the angle off broadside of the peak lag."""
    n = int(0.5 * SR) // HOP
    seg = np.stack([x[onset + k * HOP: onset + k * HOP + NFFT] for k in range(n) if onset + k * HOP + NFFT <= len(x)])
    w = np.hanning(NFFT)
    X1 = np.fft.rfft(seg[:, :, 0] * w, axis=1); X2 = np.fft.rfft(seg[:, :, 1] * w, axis=1)
    f = np.fft.rfftfreq(NFFT, 1.0 / SR)
    G = (X1 * np.conj(X2)); G = (G / (np.abs(G) + 1e-20)).sum(0) * ((f >= 3000) & (f < 8000))
    up = 8
    cc = np.fft.irfft(G, NFFT * up)
    m = int(math.ceil(d / C * SR * up))
    lags = np.concatenate([np.arange(0, m + 1), np.arange(-m, 0)])
    vals = np.concatenate([cc[:m + 1], cc[-m:]])
    tau = lags[np.argmax(vals)] / (SR * up)
    return round(math.degrees(math.asin(max(-1.0, min(1.0, tau * C / d)))), 2)


def read(stream, x, onset, end, d):
    """One utterance's short and whole reads: summed band powers in dB, frame counts, and its level and bearing."""
    settle = int(round(SETTLE_S * SR))
    k0 = -(-settle // HOP)                                           # first hop at or after onset + SETTLE_S
    k_short = (int(RANGE_READ_S * SR) - NFFT) // HOP                  # last hop whose window ends by onset + 0.5 s
    end = min(end, onset + int(CAP_S * SR), len(x))
    k_whole = (end - onset - NFFT) // HOP
    if k_whole < k_short:
        return None
    D, R = stream.run(x, onset, k_whole + 1)
    db = lambda a: [round(10 * math.log10(max(v, 1e-30)), 3) for v in a]
    s = slice(k0, k_short + 1); w = slice(k0, k_whole + 1)
    lev = x[onset: onset + int(RANGE_READ_S * SR)]
    return {'short': {'d': db(D[s].sum(0)), 'r': db(R[s].sum(0)), 'n': k_short + 1 - k0},
            'whole': {'d': db(D[w].sum(0)), 'r': db(R[w].sum(0)), 'n': k_whole + 1 - k0},
            'level_dbfs': round(10 * math.log10(float((lev ** 2).mean()) + 1e-20), 2), 'deg': gcc_deg(x, onset, d)}


def check_against_conductor(x, onset, d):
    """The floored bands must be the Conductor's own CdrFreeStream frames, summed (the reproduction check)."""
    ref = CdrFreeStream(d)
    k0 = -(-int(round(SETTLE_S * SR)) // HOP); k1 = (int(RANGE_READ_S * SR) - NFFT) // HOP
    dd = np.zeros(3)
    for k in range(k1 + 1):
        a, _ = ref.frame(x[onset + k * HOP: onset + k * HOP + NFFT])
        if k >= k0:
            dd += a
    mine, _ = Stream(d).run(x, onset, k1 + 1)
    return float(np.max(np.abs(10 * np.log10(mine[k0:, 3:].sum(0) / dd))))


def utterances(x):
    """The Conductor's utterances: (onset, close) frames from its ears, every open a fresh one."""
    ears, out, cur = Attacks(), [], None
    for now in range(CHUNK, len(x) + 1, CHUNK):
        for kind, frame in ears.feed(x[now - CHUNK:now, 0] * 32768, x[now - CHUNK:now, 1] * 32768):
            if kind == 'open':
                if cur is not None:
                    out.append((cur, frame))
                cur = frame
            elif cur is not None:
                out.append((cur, frame)); cur = None
    if cur is not None:
        out.append((cur, len(x)))
    return out


def load(path):
    x, sr = sf.read(path, dtype='float32', always_2d=True)
    assert sr == SR and x.shape[1] == 2, path
    return x


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--root', default='C:/Projects/GithubRoot/Dictate/captures/geonar/tapes')
    a = ap.parse_args()
    root = Path(a.root)
    lab = json.loads((REPO / 'harness/rotation/facing_stops.json').read_text())['stops']
    lib = {t['name']: t for t in json.loads((REPO / 'library.json').read_text())['tapes']}
    out = {'about': __doc__.split('\n\n')[0], 'bands': [{'name': b, 'lo_hz': lo, 'hi_hz': hi, 'floored': fl}
                                                          for b, lo, hi, fl in BANDS],
           'settle_s': SETTLE_S, 'range_read_s': RANGE_READ_S, 'cap_s': CAP_S, 'walks': {}, 'locata': {}}
    worst = 0.0
    for w in sorted(set(lab) | set(LADDER_WALKS)):
        folded = lib.get(w, {}).get('folded_deg')
        d = 0.157 if not folded else 0.157 * math.sin(math.radians(folded) / 2)
        x = load(root / f'{w}.wav')
        st, reads = Stream(d), []
        for i, (on, cl) in enumerate(utterances(x)):
            r = read(st, x, on, cl, d)
            if r is None:
                continue
            if i < 3:
                worst = max(worst, check_against_conductor(x, on, d))
            reads.append({'t': round(on / SR, 3), 'end': round(cl / SR, 3), **r})
        out['walks'][w] = {'baseline_m': d, 'reads': reads}
        print(w, len(reads), 'reads', flush=True)
    for f in sorted(glob.glob(str(REPO / 'results/animation/locata/*_task*_recording*.json'))):
        doc = json.loads(Path(f).read_text())
        name = doc['recording']
        x = load(root / f'locata-{name}.wav')
        d = doc['array']['pairs']['160']['mm'] / 1000
        st, reads = Stream(d), []
        for e in doc['events']:
            on = int(round(e['t'] * SR))
            spans = doc['tracks'][e['talker']]['speech']
            end = next((b for s, b in spans if s - 0.3 <= e['t'] < b), e['t'] + 1.0)
            r = read(st, x, on, int(end * SR), d)
            if r is None:
                continue
            reads.append({'t': e['t'], 'end': end, 'talker': e['talker'], 'dist_m': e['truth']['dist_m'],
                          'facing_deg': e['truth'].get('facing_deg'), 'others': len(e.get('others') or []), **r})
        out['locata'][name] = {'baseline_m': d, 'reads': reads}
        print(name, len(reads), 'reads', flush=True)
    out['conductor_check_db'] = round(worst, 6)
    dst = REPO / 'results/rotation/range/reads.json'
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(json.dumps(out, separators=(',', ':')))
    print('largest gap to the Conductor\'s own CdrFreeStream on the floored bands:', worst, 'dB')


if __name__ == '__main__':
    main()
