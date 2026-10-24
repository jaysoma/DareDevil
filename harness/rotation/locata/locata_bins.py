#!/usr/bin/env python3
"""Brief D, the band powers: direct, diffuse and total power per segment, in 0.1 s bins on LOCATA's own track grid
(2026-10-24).

The estimator is octave_windows.py's (cdr_direct's direction-free CDR: NFFT 2048, hop 512, PSD smoothing 0.92), run
UNFLOORED on the same segments

    88 | 100 | 177 | 354 | 707 | 1100 | 1414 | 2000 | 2828 | 4000 | 8000 Hz

but summed in 0.1 s bins instead of 0.5 s windows, so a stretch can keep only the bins where its talker speaks and the
other talker doesn't. A hop goes to the bin its centre falls in. The pair is DICIT mics 5 and 10, 160 mm, so c/2d is
1.07 kHz and every segment below 1.1 kHz carries `ill_conditioned`. The audio is Dictate's LOCATA tapes
(`Dictate/geonar/locata_tapes.py`: mic 5 left, mic 10 right, 48 kHz, not normalised). Run where the audio is:

    python harness/rotation/locata/locata_bins.py --root C:/Projects/GithubRoot [recording ...]

Writes results/rotation/locata/bins/<recording>.json.
"""
import argparse
import json
import sys
import wave
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / 'harness/rotation/colour'))
sys.path.insert(0, str(REPO / 'src'))
from geonar.cdr_direct import C, HOP, NFFT, SR  # noqa: E402
import octave_windows as ow  # noqa: E402
from octave_windows import EDGES, octave_windows  # noqa: E402

ow.WIN_S = HOP / SR   # one-hop windows: octave_windows then returns every hop, which is binned below by its centre

BIN_S = 0.1
TRACKS = REPO / 'results/animation/locata'
OUT = REPO / 'results/rotation/locata/bins'


def load(rec, root):
    with wave.open(str(Path(root) / 'Dictate/captures/geonar/tapes' / f'locata-{rec}.wav')) as w:
        assert w.getnchannels() == 2 and w.getsampwidth() == 2 and w.getframerate() == SR
        b = w.readframes(w.getnframes())
    return np.frombuffer(b, '<i2').reshape(-1, 2).astype(np.float32) / 32768.0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('recordings', nargs='*')
    ap.add_argument('--root', default='C:/Projects/GithubRoot')
    ap.add_argument('--force', action='store_true')
    a = ap.parse_args()
    recs = a.recordings or [r['recording'] for r in json.loads((TRACKS / 'index.json').read_text())]
    OUT.mkdir(parents=True, exist_ok=True)
    for rec in recs:
        out = OUT / f'{rec}.json'
        if out.exists() and not a.force:
            print(rec, 'done already'); continue
        baseline = json.loads((TRACKS / f'{rec}.json').read_text())['array']['pairs']['160']['mm'] / 1000
        floor = C / (2 * baseline)
        x = load(rec, a.root)
        _, D, R, P = octave_windows(x, baseline)
        tc = (np.arange(len(D)) * HOP + NFFT / 2) / SR
        b = np.floor(tc / BIN_S + 1e-9).astype(int)
        nb = b.max() + 1
        Db, Rb, Pb = (np.zeros((nb, D.shape[1])) for _ in range(3))
        for A, Ab in ((D, Db), (R, Rb), (P, Pb)):
            np.add.at(Ab, b, A)
        hops = np.bincount(b, minlength=nb)

        def db(v):
            return np.round(10 * np.log10(np.maximum(v, 1e-30)), 2).tolist()
        doc = {'recording': rec, 'baseline_m': baseline, 'c_over_2d_hz': round(floor), 'bin_s': BIN_S,
               'segments': [{'lo_hz': lo, 'hi_hz': hi, 'ill_conditioned': bool(lo < floor)}
                            for lo, hi in zip(EDGES[:-1], EDGES[1:])],
               't0': np.round(np.arange(nb) * BIN_S, 2).tolist(), 'hops': hops.tolist(),
               'dir_db': db(Db), 'dif_db': db(Rb), 'pow_db': db(Pb),
               'estimator': 'octave_windows.py / cdr_direct direction-free CDR, unfloored, summed per segment and 0.1 s bin'}
        out.write_text(json.dumps(doc, separators=(',', ':')))
        print(rec, nb, 'bins')


if __name__ == '__main__':
    main()
