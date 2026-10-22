#!/usr/bin/env python3
"""Brief 4: the 0 deg peak in silence, on STARSS23. In label-free pauses, how many GCC-PHAT peaks land within 6 deg of 0,
and does that share collapse when the low frequencies are high-passed out?

Pauses come from the metadata (100 ms frames). Two sets:
  silence    -- no labelled event of any class in the frame, nor in the GUARD_AFTER frames before it (reverb tails of
                the last event) nor the GUARD_BEFORE frames after it.
  speechfree -- no speech (classes 0, 1) by the same rule; other labelled events may sound.
Each analysis frame is 1024 samples at the native 24 kHz (42.7 ms, the same span as GccPhat.mjs's 2048 at 48 kHz),
Hann, every 512 samples, kept only when it lies wholly inside a pause. Per frame and capsule pair: the PHAT of
L conj(R), from HP Hz (0 means from the first non-DC slice) to 8 kHz, scored over 241 delays across the pair as in
GccPhat.mjs; the tallest is the frame's peak. The angle convention is the pair's lateral angle (0 = broadside), so the
sign does not matter here: only |deg| < 6 is counted.

Null: the same frames with the second capsule taken from a different pause frame of the same file (half the file's
pause frames away). Same spectra, no inter-channel coherence: what PHAT and the delay grid give by themselves.

Coherence: per room and pair, the pause frames' summed cross-spectrum, as Re(Sab)/sqrt(Saa Sbb) per slice. A diffuse
field reads sinc(2 pi f d / c) on two free-field points (positive below c / 2d, 2.5 kHz at 68.5 mm); a common-mode
electrical signal reads ~1 at every frequency; a single directional source reads cos(2 pi f tau).

    python3 pause_gcc.py /path/to/starss23 out_dir
"""
import csv
import json
import math
import sys
from collections import defaultdict
from itertools import combinations
from pathlib import Path

import numpy as np
import soundfile as sf

SR, NFFT, HOP, HI_HZ, TAUS, C = 24000, 1024, 512, 8000, 241, 343.0
HPS = [0, 100, 300, 1100, 2500]       # 2500: the 1100 Hz of a 157 mm pair, scaled to 68.5 mm (c / 2d)
NEAR0 = 6.0
FRAME_S = 0.1
GUARD_AFTER, GUARD_BEFORE = 3, 1      # label frames kept clear after an event ends / before one starts
SKIP_START_S = 2.0                    # the clapper that starts each scene may sit unlabelled at the top
SPEECH = {0, 1}
R = 0.042
CAPS = {1: (45, 35), 2: (-45, -35), 3: (135, -35), 4: (-135, 35)}
PAIRS = list(combinations([1, 2, 3, 4], 2))
DEG_BINS = np.arange(-90, 92, 2)      # histogram edges, 2 deg


def cap_xyz(n):
    az, el = (math.radians(v) for v in CAPS[n])
    return np.array([R * math.cos(el) * math.cos(az), R * math.cos(el) * math.sin(az), R * math.sin(el)])


def load_meta(path):
    rows = defaultdict(set)
    with open(path, newline='') as fh:
        for r in csv.reader(fh):
            if r:
                rows[int(r[0])].add(int(r[1]))
    return rows


def pause_mask(rows, n_frames, classes):
    """Per 100 ms label frame: True when no event of `classes` (None = any) is active in it or the guard frames."""
    active = np.zeros(n_frames, bool)
    for f, cl in rows.items():
        if f < n_frames and (classes is None and cl or classes is not None and cl & classes):
            active[f] = True
    ok = ~active
    for k in range(1, GUARD_AFTER + 1):
        ok[k:] &= ~active[:-k]
    for k in range(1, GUARD_BEFORE + 1):
        ok[:-k] &= ~active[k:]
    ok[:int(SKIP_START_S / FRAME_S)] = False
    return ok


def frames_in(mask, n_samples):
    """Start samples of the analysis frames lying wholly inside masked label frames."""
    lab = int(FRAME_S * SR)                                     # 2400 samples > NFFT: a frame touches at most two
    starts = np.arange(0, min(n_samples, len(mask) * lab) - NFFT + 1, HOP)
    return starts[mask[starts // lab] & mask[(starts + NFFT - 1) // lab]]


def steering(d):
    f = np.fft.rfftfreq(NFFT, 1 / SR)
    k1 = int(np.floor(HI_HZ * NFFT / SR))
    tmax = d / C
    tau = np.linspace(-tmax, tmax, TAUS)
    deg = np.degrees(np.arcsin(np.clip(-tau * C / d, -1, 1)))
    E = np.exp(-2j * np.pi * np.outer(f[:k1 + 1], tau))       # score(tau) = Re sum X e^(-j 2 pi f tau)
    return f[:k1 + 1], E, deg


def peaks(X, f, E, deg, hp):
    """X: frames x slices cross-spectrum (already PHAT). Returns the peak angle per frame and its share."""
    k0 = max(1, int(np.ceil(hp * NFFT / SR)))
    sc = np.real(X[:, k0:] @ E[k0:])
    j = sc.argmax(1)
    return deg[j], sc[np.arange(len(j)), j] / (E.shape[0] - k0)


def main():
    root, out = Path(sys.argv[1]), Path(sys.argv[2])
    out.mkdir(parents=True, exist_ok=True)
    geo = {}
    for p in PAIRS:
        d = float(np.linalg.norm(cap_xyz(p[1]) - cap_xyz(p[0])))
        geo[p] = (d, *steering(d))
    f = geo[PAIRS[0]][1]
    win = np.hanning(NFFT + 1)[:-1]
    # counts[set][room][pair][hp] = [frames, near0, null_near0], hist the same keyed set/room/pair/hp
    counts = defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: [0, 0, 0]))))
    hist = defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: np.zeros(len(DEG_BINS) - 1, int)))))
    shares = defaultdict(lambda: defaultdict(list))            # (set, hp) -> [(share, near0)] for a strength split
    coh = defaultdict(lambda: defaultdict(lambda: [np.zeros(len(f), complex), np.zeros(len(f)), np.zeros(len(f))]))
    per_file = []
    wavs = sorted(root.glob('mic_dev/**/*.wav'))
    for i, wav in enumerate(wavs):
        metas = list(root.glob(f'metadata_dev/**/{wav.stem}.csv'))
        if not metas:
            continue
        room = wav.stem.split('_')[1]
        x, sr = sf.read(str(wav), dtype='float64')
        assert sr == SR, sr
        rows = load_meta(metas[0])
        n_lab = int(len(x) / (FRAME_S * SR))
        rec = {'file': wav.stem, 'room': room, 'dur_s': round(len(x) / SR, 1)}
        for set_name, classes in (('silence', None), ('speechfree', SPEECH)):
            st = frames_in(pause_mask(rows, n_lab, classes), len(x))
            rec[f'{set_name}_frames'] = int(len(st))
            if len(st) < 2:
                continue
            seg = np.stack([x[s:s + NFFT] for s in st]) * win[None, :, None]      # frames x NFFT x 4
            Xc = np.fft.rfft(seg, axis=1)[:, :len(f)]                               # frames x slices x 4
            rec[f'{set_name}_rms_db'] = round(float(10 * np.log10(np.mean(seg[..., 0] ** 2) + 1e-20)), 1)
            shift = len(st) // 2
            for p in PAIRS:
                d, _, E, deg = geo[p]
                A, B = Xc[..., p[0] - 1], Xc[..., p[1] - 1]
                S = A * np.conj(B)
                Sn = A * np.conj(np.roll(B, shift, axis=0))
                if set_name == 'silence':
                    c = coh[room][p]
                    c[0] += S.sum(0); c[1] += (np.abs(A) ** 2).sum(0); c[2] += (np.abs(B) ** 2).sum(0)
                P = S / np.maximum(np.abs(S), 1e-30)
                Pn = Sn / np.maximum(np.abs(Sn), 1e-30)
                for hp in HPS:
                    dg, sh = peaks(P, f, E, deg, hp)
                    dn, _ = peaks(Pn, f, E, deg, hp)
                    near = np.abs(dg) < NEAR0
                    cnt = counts[set_name][room][p][hp]
                    cnt[0] += len(dg); cnt[1] += int(near.sum()); cnt[2] += int((np.abs(dn) < NEAR0).sum())
                    hist[set_name][room][p][hp] += np.histogram(dg, DEG_BINS)[0]
                    shares[set_name, hp][p].append(np.stack([sh, near]).T)
        per_file.append(rec)
        print(f'{i + 1}/{len(wavs)} {wav.stem} silence {rec.get("silence_frames", 0)} speechfree {rec.get("speechfree_frames", 0)}',
              flush=True)

    key = lambda p: f'{p[0]}{p[1]}'
    res = {'config': {'sr': SR, 'nfft': NFFT, 'hop': HOP, 'hi_hz': HI_HZ, 'taus': TAUS, 'hps': HPS, 'near0_deg': NEAR0,
                      'guard_after_frames': GUARD_AFTER, 'guard_before_frames': GUARD_BEFORE, 'skip_start_s': SKIP_START_S,
                      'baseline_mm': {key(p): round(geo[p][0] * 1000, 1) for p in PAIRS}},
           'counts': {s: {r: {key(p): {str(h): v for h, v in hh.items()} for p, hh in pp.items()} for r, pp in rr.items()}
                      for s, rr in counts.items()},
           'hist_edges': DEG_BINS.tolist(),
           'hist': {s: {r: {key(p): {str(h): v.tolist() for h, v in hh.items()} for p, hh in pp.items()} for r, pp in rr.items()}
                    for s, rr in hist.items()},
           'per_file': per_file}
    # strength split: the share of near-0 peaks among each pair's strongest quarter of frames (PHAT peak share)
    strong = {}
    for (s, hp), pp in shares.items():
        for p, chunks in pp.items():
            a = np.concatenate(chunks)
            q = np.quantile(a[:, 0], 0.75)
            top = a[a[:, 0] >= q]
            strong.setdefault(s, {}).setdefault(key(p), {})[str(hp)] = {
                'all_near0_pct': round(100 * a[:, 1].mean(), 1), 'top25_near0_pct': round(100 * top[:, 1].mean(), 1),
                'median_share': round(float(np.median(a[:, 0])), 4)}
    res['strength'] = strong
    edges = [0, 100, 300, 1100, 2500, 8000]
    res['coherence_edges_hz'] = edges
    res['coherence_re'] = {}
    for r, pp in coh.items():
        for p, (sab, saa, sbb) in pp.items():
            g = np.real(sab) / np.sqrt(saa * sbb + 1e-30)
            msc = np.abs(sab) ** 2 / (saa * sbb + 1e-30)
            res['coherence_re'].setdefault(r, {})[key(p)] = {
                'band_re': [round(float(g[(f >= lo) & (f < hi) & (f > 0)].mean()), 3) for lo, hi in zip(edges, edges[1:])],
                'band_msc': [round(float(msc[(f >= lo) & (f < hi) & (f > 0)].mean()), 3) for lo, hi in zip(edges, edges[1:])],
                'curve_re': [round(float(v), 3) for v in g]}
    res['coherence_freqs_hz'] = [round(float(v), 1) for v in f]
    with open(out / 'pause_gcc.json', 'w') as fh:
        json.dump(res, fh)
    print('wrote', out / 'pause_gcc.json')


if __name__ == '__main__':
    main()
