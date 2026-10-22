"""Which truth the scores use.

measured (default): the direct-path delay measured in each pair's two RIRs (cross-correlation of +-2 ms around the direct
  path, upsampled 16x; no labelled echo arrives within 1 ms of it). The labelled echoes' delays are the image-source ones
  scaled by the pair's own factor k, fitted over its 66 direct paths (11 rooms x 6 sources): the measured delays run
  3-23% longer than the calibrated geometry predicts, consistently per pair, as if each pair were that much wider.
geometry: the calibrated positions as dEchorate publishes them, unscaled.
"""
import gzip
import json
import math
from collections import defaultdict

C_SCHEME = 343.0


def lateral(tau_ms, d):
    return math.degrees(math.asin(max(-1.0, min(1.0, -tau_ms / 1000 * C_SCHEME / d))))


def apply(metas, mode='measured'):
    """metas: list of cut dicts (no audio). Rewrites truth_deg and each echo's deg in place for `mode`; returns k per pair."""
    if mode == 'geometry':
        return {}
    xy = defaultdict(lambda: [0.0, 0.0])
    for m in metas:
        s = xy[tuple(m['mics'])]
        s[0] += m['truth_tau_ms'] * m['rir_tau_ms']
        s[1] += m['truth_tau_ms'] ** 2
    k = {p: a / b for p, (a, b) in xy.items()}
    for m in metas:
        kk, d = k[tuple(m['mics'])], m['baseline_m']
        m['truth_deg'] = lateral(m['rir_tau_ms'], d)
        for e in m['echoes']:
            e['deg'] = lateral(kk * e['tau_ms'], d)
    return k


def read_jsonl(path):
    """A JSONL file, gzipped or not."""
    path = str(path)
    with (gzip.open(path, 'rt') if path.endswith('.gz') else open(path)) as fh:
        return [json.loads(line) for line in fh if line.strip()]
