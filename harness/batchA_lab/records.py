#!/usr/bin/env python3
"""Brief 13: turn one audio set's cuts and its runs into batch A records (one JSON line per read, the shared format).

For each run (a cause applied at run time, or none) and cut:
  gcc.votes   GccPhat's vote total after pause weighting, at the lock: sum over its slices of max(0, min(1, 1 - N/P)),
              N the slice's mean power over the PAUSE_MS before the read's onset, P its mean power over the read's 47
              frames -- GccPhat.mjs's own weights(), mirrored here (the stream does not expose them). With no pause
              (cause 6) every slice counts fully: the slice count.
  snr_db      voice over pause, dB, both capsules' power: the 0.5 s after the onset handed over against the 0.5 s
              before it, in 300-1100 Hz (mf), 1.1-3 kHz (hf1) and 3-8 kHz (hf2).
  classes     for each scheme, every kind a read off by more than 10 deg carries (a read can carry several):
              mirror, endfire, pause_direction, other_source, zero_pull, aliasing, truth_in_2_3, drift, facing
              (never here: no facing truth), other. 'over36' is added when it is off by more than 36 deg.
  alias       the frequency whose period is the read's delay error, f = 1 / |tau_read - tau_truth|, and how much of the
              voice sits in the third-octave around it, as a ratio to an even spread (in log frequency) over the
              scheme's band. 'aliasing' needs f inside the band and a ratio of ALIAS_RATIO or more.

usage: records.py cuts.jsonl RUNS_JSON out_reads.jsonl
  RUNS_JSON: [{"cause": "...", "preds": "path", "offset_ms": 0, "nopause": false, "gcc_lo": 300, "a2_lo": 1100}, ...]
"""
import base64
import json
import math
import sys

import numpy as np

SR, C = 48000, 343.0
NFFT, HOP, HI_HZ, PAUSE_MS, LOCK_FRAMES = 2048, 512, 8000, 200, 47
HANN = 0.5 - 0.5 * np.cos(2 * np.pi * np.arange(NFFT) / (NFFT - 1))
BANDS = {'mf': (300, 1100), 'hf1': (1100, 3000), 'hf2': (3000, 8000)}
WRONG, OUTLIER, ALIAS_RATIO = 10.0, 36.0, 2.0


def frames_power(L, R, starts, k0, k1):
    X = np.fft.rfft(np.stack([L[s:s + NFFT] for s in starts]) * HANN, axis=1)[:, k0:k1 + 1]
    Y = np.fft.rfft(np.stack([R[s:s + NFFT] for s in starts]) * HANN, axis=1)[:, k0:k1 + 1]
    return ((np.abs(X) ** 2 + np.abs(Y) ** 2) / 2).mean(0)


def votes(L, R, on, lo_hz, nopause):
    k0, k1 = math.ceil(lo_hz * NFFT / SR), math.floor(HI_HZ * NFFT / SR)
    if nopause:
        return float(k1 - k0 + 1)
    frm = on - HOP
    a = frm + HOP - int(PAUSE_MS * SR / 1000) - NFFT // 2
    b = frm + HOP + NFFT // 2
    if a < 0:
        return float(k1 - k0 + 1)
    N = frames_power(L, R, list(range(a, b - NFFT + 1, HOP)), k0, k1)
    P = frames_power(L, R, [frm + HOP * i for i in range(LOCK_FRAMES)], k0, k1)
    return float(np.clip(1 - N / np.maximum(P, 1e-30), 0, 1).sum())


def band_db(x, lo, hi):
    F = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x), 1 / SR)
    return float((np.abs(F[(f >= lo) & (f < hi)]) ** 2).sum())


def snr(L, R, on):
    v, p = slice(on, on + SR // 2), slice(on - SR // 2, on)
    out = {}
    for k, (lo, hi) in BANDS.items():
        pv = band_db(L[v], lo, hi) + band_db(R[v], lo, hi)
        pp = band_db(L[p], lo, hi) + band_db(R[p], lo, hi)
        out[k] = round(10 * math.log10((pv + 1e-20) / (pp + 1e-20)), 1)
    return out


def third_oct(L, R, on):
    """The voice's power per 1/12 octave, 300 Hz - 8 kHz (0.5 s from the true onset): (centres, power)."""
    x = (L[on:on + SR // 2] + R[on:on + SR // 2]) / 2
    F = np.abs(np.fft.rfft(x)) ** 2
    f = np.fft.rfftfreq(len(x), 1 / SR)
    edges = 300 * 2 ** (np.arange(0, 12 * math.log2(8000 / 300) + 1) / 12)
    p = np.array([F[(f >= a) & (f < b)].sum() for a, b in zip(edges, edges[1:])])
    return np.sqrt(edges[:-1] * edges[1:]), p


def alias(read, truth, d, lo, spec):
    tr, tt = -math.sin(math.radians(read)) * d / C, -math.sin(math.radians(truth)) * d / C
    dt = abs(tr - tt)
    if dt < 1e-7:
        return None
    f = 1 / dt
    cen, p = spec
    inb = (cen >= lo) & (cen <= HI_HZ)
    if not (lo <= f <= HI_HZ) or p[inb].sum() <= 0:
        return {'f_hz': round(f), 'ratio': None}
    win = inb & (cen >= f / 2 ** (1 / 6)) & (cen <= f * 2 ** (1 / 6))
    share = p[win].sum() / p[inb].sum()
    even = win.sum() / inb.sum()
    return {'f_hz': round(f), 'ratio': round(float(share / even), 2) if even else None}


def kinds(scheme, read, truth, rec, al):
    """The wrong-read classes of one scheme's read (empty if it is within 10 deg)."""
    err = abs(read - truth)
    if err <= WRONG:
        return []
    k = []
    if abs(truth) >= 10 and abs(read + truth) <= 10:
        k.append('mirror')
    if abs(read) >= 85:
        k.append('endfire')
    if rec.get('pause_deg') is not None and abs(read - rec['pause_deg']) <= 10:
        k.append('pause_direction')
    if any(abs(read - o['deg']) <= 10 for o in rec['truth']['others']):
        k.append('other_source')
    if abs(read) < 6 and abs(truth) > 15:
        k.append('zero_pull')
    if al and al.get('ratio') is not None and al['ratio'] >= ALIAS_RATIO:
        k.append('aliasing')
    alts = rec['gcc']['angles'][1:] if scheme == 'gcc' else [rec['a2'].get('second_deg')]
    if any(a is not None and abs(a - truth) <= 10 for a in alts):
        k.append('truth_in_2_3')
    if scheme == 'gcc':
        e = rec['gcc']['track'].get('43')
        if e is not None and abs(e - truth) <= 10:
            k.append('drift')
    if not k:
        k.append('other')
    if err > OUTLIER:
        k.append('over36')
    return k


def main():
    cuts_path, runs, out_path = sys.argv[1], json.load(open(sys.argv[2])), sys.argv[3]
    preds = [{} for _ in runs]
    for i, r in enumerate(runs):
        for l in open(r['preds']):
            q = json.loads(l)
            preds[i][q['id']] = q
    with open(cuts_path) as fc, open(out_path, 'a') as fo:
        for line in fc:
            c = json.loads(line)
            L = np.frombuffer(base64.b64decode(c['L']), '<i2').astype(np.float64) / 32768
            R = np.frombuffer(base64.b64decode(c['R']), '<i2').astype(np.float64) / 32768
            d, on0, t = c['baseline_m'], c['onset_sample'], c['truth']['deg']
            spec = third_oct(L, R, on0)
            for run, pr in zip(runs, preds):
                q = pr.get(c['id'])
                if q is None:
                    continue
                on = on0 + round(run.get('offset_ms', 0) * 48)
                g = q.get('gcc') or {'angles': [], 'shares': [], 'widths': [], 'tie': False, 'track': {}}
                rec = {'dataset': 'lab', 'scenario': f"{c['placement']}|{run['cause']}|{int(t):+d}",
                       'id': f"{c['placement']}/{run['cause']}/{int(t):+d}/{c['id'].rsplit('/', 1)[1]}",
                       'pair_mm': c['pair_mm'], 'truth': c['truth'],
                       'gcc': dict(g, votes=round(votes(L, R, on, run.get('gcc_lo', 300), run.get('nopause', False)), 2)),
                       'a2': q.get('a2'), 'pause_deg': q.get('pause_deg'), 'pause_share': q.get('pause_share'),
                       'snr_db': snr(L, R, on), 'cause': run['cause'], 'placement': c['placement'],
                       'clean': c['clean'], 'combo': c['combo']}
                cls, al = {}, {}
                if g['angles']:
                    al['gcc'] = alias(g['angles'][0], t, d, run.get('gcc_lo', 300), spec)
                    cls['gcc'] = kinds('gcc', g['angles'][0], t, rec, al['gcc'])
                if rec['a2']:
                    al['a2'] = alias(rec['a2']['deg'], t, d, run.get('a2_lo', 1100), spec)
                    cls['a2'] = kinds('a2', rec['a2']['deg'], t, rec, al['a2'])
                rec['classes'], rec['alias'] = cls, al
                fo.write(json.dumps(rec) + '\n')


if __name__ == '__main__':
    main()
