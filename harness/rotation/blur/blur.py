#!/usr/bin/env python3
"""Brief B: does the blur, in time, tell facing from turned? (2026-10-24)

Reads envelopes.py's cache, each walk's tapes/<walk>/band_windows.json (for the speech windows and the CDR bar),
harness/rotation/facing_stops.json and the two same-phrase walks' decodes. Writes results/rotation/blur/blur.txt and
blur.json.

STOPS. facing_stops.json's, less each stop's opening announcement (announcement_end): Jay turns only right before or
right after a callout and never talks while turning, so the callout is the one stretch whose facing is unsure.

SPEECH. A stop's speech is facing_pooled.py's: the 0.5 s windows whose total 1.1-8 kHz power is 10 dB over the tape's
20th percentile. Contiguous windows make a run; runs of 1 s or more are kept, and the dips INSIDE a run are what is
measured (a mask on 10 ms frames would cut out the very dips).

MEASURES, per stop:
  mod <band>      2-8 Hz modulation index of the band's intensity envelope (10 ms bins), in dB: per run, the envelope
                  over its mean, minus 1, Hann-tapered, power summed over 2-8 Hz; pooled over the stop's runs by length;
                  scaled so a sinusoidal envelope of index m reads 20 log10 m. Per mic, then the two mics' mean in dB.
  mod hi - lo     mod 4-8 kHz minus mod 0.25-1 kHz (the CDR contrast's shape: the voice's own syllable rate cancels).
  dip hi - lo     the envelope's 90th minus 10th percentile in dB inside runs, high minus low band.
  dmod hi         mod of the PAIR'S DIRECT 4-8 kHz power (envelopes.py: the CDR's direct fraction x the hop's power).
  onset colour    at each onset that rises from quiet inside the stop (80 ms below the tape's floor + 35% of its range
                  in 5 ms frames, then up past floor + 50% within 50 ms; broadband 0.18-11 kHz, both mics; 150 ms and
                  25% left 171645, 215800 and 213304 with under one onset a stop), the 4-8 kHz over
                  0.25-1 kHz energy of the first ON ms minus that of the next 300 ms, floors subtracted, pooled per stop.
SCORING, the same for every measure (and for the CDR contrast, recomputed here): a turned stop (90, 135, 180) against
the mean of its spot's facing-0 stops; a facing-0 stop against its spot's OTHER facing-0 stops (so only spots with two
give a toward case). Toward against turned with a threshold, and for the signed rule a sign, chosen on the other walks
(left out by walk); balanced accuracy. Distance slope: dB per decade over LADDERS (facing_vs_distance.py), per walk,
then the mean.
"""
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from envelopes import BANDS, CACHE, DBANDS, HOP, NFFT, SR, load  # noqa: E402
from facing_pooled import HANDLING_S, feats, lin  # noqa: E402

REPO = HERE.parents[2]
OUT = REPO / 'results/rotation/blur'
LADDERS = {  # facing_vs_distance.py's: walk: [t0, t1, called distance m], all facing the phone
    'walk-213304': [[4, 20, 2], [20, 42, 3], [42, 63, 5], [63, 78, 7]],
    'walk-221126': [[0, 12, 1], [12, 21, 2], [21, 29, 3], [29, 36, 4], [36, 43, 5], [43, 47, 6], [47, 59, 7], [59, 66, 8]],
    'walk-020305': [[2, 18, 1], [18, 54, 2], [54, 90, 3.5]],
    'walk-224302': [[0, 13, 4.5], [13, 35, 2], [35, 78, 6]],
}
BI = {b[0]: j for j, b in enumerate(BANDS)}
DI = {b[0]: j for j, b in enumerate(DBANDS)}
CDR_K = 'CDR hi - lo (4-8 vs 0.1-1.1 kHz)'
RANGE_K = 'range stat (mean CDR 1.1-8 kHz)'
ON_MS = (30, 40, 50)
TAIL_MS = 300
ANNOUNCE_MAX_S, ANNOUNCE_PAD_S = 3.0, 0.25
SET_ASIDE = {  # (walk, stop start): why. Run-based measures (mod, dip, dmod) or onset measures, not the CDR.
    'run': {('walk-122038', 10): 'mod hi - lo 16 dB off its spot on 2 s of speech',
            ('walk-122038', 16): 'mod hi - lo 19 dB off on 2.5 s',
            ('walk-213304', 269): 'mod hi - lo 21 dB off, against one facing-0 stop of 2.5 s',
            ('walk-213304', 291): 'mod hi - lo 11 dB off, against the same single reference'},
    'onset': {('walk-215800', 0): 'facing-0 pair 34 dB apart in onset tilt, on 1.5 s each',
              ('walk-215800', 26): 'the other of that pair'},
}
MIN_SPEECH_S = 2.0           # run-based measures need this much speech in runs, at a stop or a ladder step
QUIET = (80, 0.35, 0.5)      # an onset: 80 ms below the floor + 35% of the tape's range, then past 50% within 50 ms


class Tape:
    def __init__(self, walk):
        z = np.load(CACHE / f'{walk}.npz')
        self.E = z['E'].astype(np.float64)                                      # (ms, 2, bands)
        self.Dh, self.Th = z['Dh'].astype(np.float64), z['Th'].astype(np.float64)
        n10 = len(self.E) // 10
        self.E10 = self.E[:n10 * 10].reshape(n10, 10, 2, -1).sum(1)
        bw = json.loads((REPO / 'tapes' / walk / 'band_windows.json').read_text())
        self.t0, self.win = np.array(bw['t0']), bw['win_s']
        self.D, self.R, self.P = lin(bw['dir_db']), lin(bw['dif_db']), lin(bw['pow_db'])
        tot = 10 * np.log10(self.P[:, 1:].sum(1))
        self.voiced = (tot >= np.percentile(tot, 20) + 10) & (self.t0 >= HANDLING_S)   # the tape-start handling
        self.quiet = tot <= np.percentile(tot, 20)
        self.floor1 = np.percentile(self.E, 10, axis=0)                          # (2, bands) per 1 ms bin
        self.floor10 = np.percentile(self.E10, 10, axis=0)
        self.onsets = self._onsets()

    def runs(self, a, b, mask=None, min_s=1.0):
        m = (self.voiced if mask is None else mask) & (self.t0 >= a) & (self.t0 + self.win <= b)
        out, i, idx = [], 0, np.flatnonzero(m)
        while i < len(idx):
            j = i
            while j + 1 < len(idx) and idx[j + 1] == idx[j] + 1:
                j += 1
            ta, tb = self.t0[idx[i]], self.t0[idx[j]] + self.win
            if tb - ta >= min_s - 1e-6:
                out.append((ta, tb))
            i = j + 1
        return out

    def _onsets(self):
        bb = [BI[f'oct{f}'] for f in (250, 500, 1000, 2000, 4000, 8000)]
        e1 = self.E[:, :, bb].sum((1, 2))
        n5 = len(e1) // 5
        l5 = 10 * np.log10(e1[:n5 * 5].reshape(n5, 5).mean(1) + 1e-20)
        l1 = 10 * np.log10(e1 + 1e-20)
        fl, ld = np.percentile(l5, 10), np.percentile(l5, 95)
        q, up = fl + QUIET[1] * (ld - fl), fl + QUIET[2] * (ld - fl)
        qn = QUIET[0] // 5
        on, i = [], qn
        while i < n5 - 10:
            if l5[i] >= q and np.all(l5[i - qn:i] < q) and l5[i:i + 10].max() >= up:
                k = np.flatnonzero(l1[(i - 1) * 5:(i + 1) * 5] >= q)
                on.append((i - 1) * 5 + (k[0] if len(k) else 5))
                i += qn
            else:
                i += 1
        self.onset_th = (fl, q, up)
        return np.array(on)


def modsq(e, fs):
    """Per run: sum over 2-8 Hz of the tapered relative envelope's power (an rms index squared), and its length."""
    x = e / e.mean() - 1
    w = np.hanning(len(x)); w /= np.sqrt(np.mean(w ** 2))
    X = np.fft.rfft((x - x.mean()) * w)
    f = np.fft.rfftfreq(len(x), 1 / fs)
    return 2 * np.sum(np.abs(X[(f >= 2) & (f <= 8)]) ** 2) / len(x) ** 2


def pooled_db(parts):
    """parts: [(m^2, n)]. Pooled index in dB, scaled so a sinusoidal envelope of index m reads 20 log10 m."""
    num = sum(m * n for m, n in parts); den = sum(n for _, n in parts)
    return 10 * np.log10(2 * num / den) if den else np.nan


def run_measures(tp, runs):
    """Modulation and dip measures over a list of runs. None under MIN_SPEECH_S: on a second or so of envelope the
    2-8 Hz index reads +/-10 dB (215800's turned stops)."""
    if sum(b - a for a, b in runs) < MIN_SPEECH_S - 1e-6:
        return None
    r = {}
    per_mic = {}
    for m in range(2):
        for name, j in BI.items():
            parts, dips = [], []
            for a, b in runs:
                e = tp.E10[int(a * 100):int(b * 100), m, j]
                parts.append((modsq(e, 100.0), len(e)))
                d = 10 * np.log10(e + 1e-20)
                dips.append((np.percentile(d, 90) - np.percentile(d, 10), len(e)))
            per_mic[(m, name)] = (pooled_db(parts), sum(x * n for x, n in dips) / sum(n for _, n in dips))
    for name in BI:
        r[f'mod {name}'] = np.mean([per_mic[(m, name)][0] for m in range(2)])
        r[f'dip {name}'] = np.mean([per_mic[(m, name)][1] for m in range(2)])
    for m in range(2):
        r[f'mod hi - lo ch{m}'] = per_mic[(m, 'hi')][0] - per_mic[(m, 'lo')][0]
    for name in ('hi', 'lo'):
        j = BI[name]
        r[f'dip over floor {name}'] = float(np.mean([10 * np.log10(np.percentile(np.concatenate(
            [tp.E10[int(a * 100):int(b * 100), m, j] for a, b in runs]), 10) / tp.floor10[m, j]) for m in range(2)]))
    r['mod hi - lo'] = r['mod hi'] - r['mod lo']
    r['dip hi - lo'] = r['dip hi'] - r['dip lo']
    hc = (np.arange(len(tp.Dh)) * HOP + NFFT / 2) / SR
    fs = SR / HOP
    for name, j in DI.items():
        pd, pt = [], []
        for a, b in runs:
            s = (hc >= a) & (hc < b)
            pd.append((modsq(tp.Dh[s, j] + 1e-20, fs), s.sum())); pt.append((modsq(tp.Th[s, j], fs), s.sum()))
        r[f'dmod {name}'] = pooled_db(pd); r[f'tmod {name}'] = pooled_db(pt)
    r['dmod hi - mod lo'] = r['dmod hi'] - r['mod lo']
    r['dmod - tmod hi'] = r['dmod hi'] - r['tmod hi']
    r['speech_s'] = sum(b - a for a, b in runs)
    return r


def span_measures(tp, a, b):
    """mod hi - lo over the whole stop, pauses and all (as an MTF is read off running speech), no speech mask."""
    v = {nm: np.mean([pooled_db([(modsq(tp.E10[int(a * 100):int(b * 100), m, BI[nm]], 100.), 1)]) for m in range(2)])
         for nm in ('hi', 'lo')}
    return {'span mod hi - lo': v['hi'] - v['lo']}


def onset_measures(tp, a, b):
    on = tp.onsets[(tp.onsets >= a * 1000) & (tp.onsets <= b * 1000 - ON_MS[-1] - TAIL_MS)]
    r = {'n_onsets': int(len(on))}
    if len(on) < 2:
        return r
    hi, lo = BI['hi'], BI['lo']
    for L in ON_MS:
        acc = {}
        for m in range(2):
            for part, (u, v) in (('on', (0, L)), ('tail', (L, L + TAIL_MS))):
                for band, j in (('hi', hi), ('lo', lo)):
                    e = sum(tp.E[t + u:t + v, m, j].sum() for t in on) - len(on) * (v - u) * tp.floor1[m, j]
                    acc[(m, part, band)] = max(e, 1e-3 * sum(tp.E[t + u:t + v, m, j].sum() for t in on))
        for m in range(2):
            col = {p: 10 * np.log10(acc[(m, p, 'hi')] / acc[(m, p, 'lo')]) for p in ('on', 'tail')}
            r[f'onset colour {L} ch{m}'] = col['on'] - col['tail']
            r[f'onset tilt {L} ch{m}'] = col['on']
            r[f'tail tilt {L} ch{m}'] = col['tail']
        for k in ('onset colour', 'onset tilt', 'tail tilt'):
            r[f'{k} {L}'] = np.mean([r[f'{k} {L} ch{m}'] for m in range(2)])
    return r


def cdr_measures(tp, a, b):
    m = tp.voiced & (tp.t0 >= a) & (tp.t0 + tp.win <= b)
    if m.sum() < 2:
        return {}
    f = feats(tp.D[m], tp.R[m], tp.P[m], m.sum())
    return {'CDR hi - lo': f[CDR_K], 'CDR range stat': f[RANGE_K]}


def announcement_end(segs, a):
    """Where a stop's opening announcement ends. Jay turns only right before or right after announcing, and never
    talks while turning (2026-10-24), so the announcement is the one stretch whose facing is unsure: it is the decode
    segment over the stop's start, capped at ANNOUNCE_MAX_S (a merged segment can run on into the new facing's
    talk), plus ANNOUNCE_PAD_S."""
    ends = [min(g['t1'], g['t0'] + ANNOUNCE_MAX_S) for g in segs if g['t0'] < a + 0.5 and g['t1'] > a - 0.5]
    return max([a] + [e + ANNOUNCE_PAD_S for e in ends])


def stop_rows(tapes, lab, trim=True):
    rows = []
    for walk, spots in lab.items():
        tp = tapes[walk]
        segs = json.loads((REPO / 'tapes' / walk / 'transcript.json').read_text(encoding='utf-8'))['segments']
        for spot, stops in spots.items():
            if spot == 'dist_m':
                continue
            for a0, b, fd in stops:
                a = announcement_end(segs, a0) if trim else a0
                r = dict(walk=walk, spot=spot, facing=fd, a=a0, b=b, from_s=a)
                r.update(cdr_measures(tp, a, b))
                r.update(span_measures(tp, a, b))
                runs = tp.runs(a, b)
                r['speech_s'] = sum(y - x for x, y in runs)
                rm = run_measures(tp, runs)
                if rm:
                    r.update(rm)
                r.update(onset_measures(tp, a, b))
                rows.append(r)
    return rows


def deltas(rows, k):
    """[(walk, facing, delta)]: turned against the spot's facing-0 mean; facing 0 against the spot's other facing-0."""
    out = []
    for key in sorted({(r['walk'], r['spot']) for r in rows}):
        st = [r for r in rows if (r['walk'], r['spot']) == key and np.isfinite(r.get(k, np.nan))]
        ref = [r for r in st if r['facing'] == 0]
        for r in st:
            others = [o[k] for o in ref if o is not r]
            if others:
                out.append((r['walk'], r['facing'], r[k] - np.mean(others)))
    return out


def loo(ds, unsigned):
    walks = sorted({w for w, _, _ in ds})
    tp = fn = tn = fp = 0
    for w in walks:
        tr = [(fd, abs(x) if unsigned else x) for o, fd, x in ds if o != w]
        te = [(fd, abs(x) if unsigned else x) for o, fd, x in ds if o == w]
        if not te or not any(fd == 0 for fd, _ in tr) or not any(fd != 0 for fd, _ in tr):
            continue
        xs = np.sort(np.unique([x for _, x in tr]))
        cands = np.concatenate([[xs[0] - 1], (xs[1:] + xs[:-1]) / 2, [xs[-1] + 1]])
        best = None
        for s in ((1,) if unsigned else (1, -1)):        # unsigned: turned if |d| > th; signed: turned if s*d < th
            for th in cands:
                if unsigned:
                    call = lambda x, th=th: x > th  # noqa: E731
                else:
                    call = lambda x, th=th, s=s: s * x < s * th  # noqa: E731
                t = [not call(x) for fd, x in tr if fd == 0]; u = [call(x) for fd, x in tr if fd != 0]
                ba = np.mean(t) / 2 + np.mean(u) / 2
                if best is None or ba > best[0]:
                    best = (ba, call)
        call = best[1]
        for fd, x in te:
            if fd == 0:
                tp += not call(x); fn += call(x)
            else:
                tn += call(x); fp += not call(x)
    if tp + fn == 0 or tn + fp == 0:
        return None
    return dict(toward_right=int(tp), toward_n=int(tp + fn), turned_right=int(tn), turned_n=int(tn + fp),
                balanced=float((tp / (tp + fn) + tn / (tn + fp)) / 2))


def auc(ds):
    """P(a turned stop's delta < a toward stop's): 1 = turned always reads lower, 0.5 = no separation."""
    tw = [x for _, f, x in ds if f == 0]; tu = [x for _, f, x in ds if f != 0]
    if not tw or not tu:
        return np.nan
    return float(np.mean([(u < t) + 0.5 * (u == t) for u in tu for t in tw]))


def score(rows, k):
    ds = deltas(rows, k)
    if not ds:
        return None
    s = {'n_stops': len(ds), 'by_facing': {}}
    for fd in (0, 90, 135, 180):
        v = [x for _, f, x in ds if f == fd]
        if v:
            s['by_facing'][fd] = dict(mean=float(np.mean(v)), sd=float(np.std(v)), n=len(v),
                                      below=int(sum(x < 0 for x in v)))
    tw = [x for _, f, x in ds if f == 0]; tu = [x for _, f, x in ds if f != 0]
    s['turned_mean'] = float(np.mean(tu)) if tu else np.nan
    s['toward_sd'] = float(np.sqrt(np.mean(np.square(tw)))) if tw else np.nan   # toward deltas centre on 0 by design
    s['signed'] = loo(ds, False); s['unsigned'] = loo(ds, True); s['auc'] = auc(ds)
    own = [r for r in rows if np.isfinite(r.get(k, np.nan))]
    dc = deltas(own, 'CDR hi - lo')
    s['cdr_same_stops'] = dict(signed=loo(dc, False), auc=auc(dc))
    return s


def ladder_slopes(tapes, k, kind):
    sl = {}
    for walk, steps in LADDERS.items():
        tp = tapes[walk]; xs, ys = [], []
        for a, b, d in steps:
            if kind == 'cdr':
                v = cdr_measures(tp, a, b).get(k)
            elif kind == 'span':
                v = span_measures(tp, a, b).get(k)
            elif kind == 'onset':
                v = onset_measures(tp, a, b).get(k)
            else:
                rm = run_measures(tp, tp.runs(a, b)); v = rm.get(k) if rm else None
            if v is not None and np.isfinite(v):
                xs.append(np.log10(d)); ys.append(v)
        if len(xs) >= 3:
            sl[walk] = float(np.polyfit(xs, ys, 1)[0])
    return sl


def held_runs(walk):
    """held_sounds.py's detection, as its code runs it (50 ms frames of the 16 kHz mono; voiced at floor + 25% of the
    range and autocorrelation >= .35; 1.5 s with >= 80% voiced and the pitch lag within 8% of its median)."""
    x, _ = load(walk)
    m = x.mean(axis=1); m = m[:len(m) // 3 * 3].reshape(-1, 3).mean(axis=1)
    FR, WIN = 800, 30
    n = len(m) // FR
    fr = m[:n * FR].reshape(n, FR)
    db = 10 * np.log10(np.mean(fr ** 2, axis=1) + 1e-12)
    lo, hi = np.percentile(db, 10), np.percentile(db, 95)
    ac = np.fft.irfft(np.abs(np.fft.rfft(fr - fr.mean(axis=1, keepdims=True), 2048, axis=1)) ** 2, axis=1)[:, :201]
    lag = 40 + ac[:, 40:201].argmax(axis=1)
    voiced = (db > lo + .25 * (hi - lo)) & (ac[:, 40:201].max(axis=1) / np.maximum(ac[:, 0], 1e-12) >= .35)
    held = np.zeros(n, bool)
    for i in range(0, n - WIN + 1):
        v = voiced[i:i + WIN]
        if v.mean() < .8:
            continue
        lg = lag[i:i + WIN][v]
        if np.all(np.abs(lg - np.median(lg)) <= .08 * np.median(lg)):
            held[i:i + WIN] = True
    d = np.diff(np.concatenate([[0], held.astype(int), [0]]))
    return [(a * .05, b * .05) for a, b in zip(np.flatnonzero(d == 1), np.flatnonzero(d == -1))]


def control_213304(tp, held):
    """Held vowels against talking on the same tape, and the tape's quiet as the measure's own floor."""
    hm = np.zeros(len(tp.t0), bool)
    for a, b in held:
        hm |= (tp.t0 + tp.win > a) & (tp.t0 < b)
    held_runs_ = [(a, b) for a, b in held if b - a >= 1.5]
    talk = tp.runs(0, 1e9, tp.voiced & ~hm)
    quiet = tp.runs(0, 1e9, tp.quiet)
    out = {'held_s': sum(b - a for a, b in held), 'held_n': len(held), 'talk_s': sum(b - a for a, b in talk),
           'quiet_s': sum(b - a for a, b in quiet)}
    for name, rr in (('held', held_runs_), ('talk', talk), ('quiet', quiet)):
        m = run_measures(tp, rr)
        out[name] = {k: m[k] for k in m if k.startswith('mod oct') or k in ('mod hi', 'mod lo', 'mod hi - lo')}
        # how far the envelope's dips (10th percentile of 10 ms bins) sit above the band's floor, mics' mean
        fl = {}
        for nm, j in BI.items():
            if not nm.startswith('oct'):
                continue
            v = []
            for mic in range(2):
                e = np.concatenate([tp.E10[int(a * 100):int(b * 100), mic, j] for a, b in rr])
                v.append(10 * np.log10(np.percentile(e, 10) / tp.floor10[mic, j]))
            fl[nm] = float(np.mean(v))
        out[name]['dip_over_floor_db'] = fl
    # which facing stops on this tape are held
    out['stops_held_fraction'] = []
    for a, b, fd in json.loads((REPO / 'harness/rotation/facing_stops.json').read_text())['stops']['walk-213304']['6m']:
        m = tp.voiced & (tp.t0 >= a) & (tp.t0 + tp.win <= b)
        out['stops_held_fraction'].append([a, b, fd, float((m & hm).sum() / max(m.sum(), 1))])
    # what the held stretches are: the strongest 50-2000 Hz bin of each, and its level against the speech threshold
    x, _ = load('walk-213304'); peaks = []
    tot = 10 * np.log10(tp.P[:, 1:].sum(1)); p20 = np.percentile(tot, 20)
    for a, b in held:
        seg = x[int(a * SR):int(b * SR)].mean(1)
        S = np.abs(np.fft.rfft(seg * np.hanning(len(seg)))) ** 2; f = np.fft.rfftfreq(len(seg), 1 / SR)
        k = (f > 50) & (f < 2000)
        m = (tp.t0 + tp.win > a) & (tp.t0 < b)
        peaks.append([float(f[k][np.argmax(S[k])]), float(np.mean(tot[m]) - p20)])
    out['held_peak_hz_and_level_over_p20_db'] = peaks
    out['held_at_mains'] = int(sum(min(abs(hz - 60), abs(hz - 120)) <= 2 for hz, _ in peaks))
    out['held_within_2db_of_p20'] = int(sum(lv <= 2 for _, lv in peaks))
    out['ladder_held_fraction'] = float((hm & tp.voiced & (tp.t0 < 78)).sum() / max((tp.voiced & (tp.t0 < 78)).sum(), 1))
    return out


def env_ms(tp, a, b, j, log):
    e = tp.E[int(a * 1000):int(b * 1000), :, j].sum(1)
    k = np.hanning(11); k /= k.sum()
    e = np.convolve(e, k, mode='same')
    return 10 * np.log10(e + 1e-20) if log else e


def xcorr(h, l, maxlag=100):
    h, l = (h - h.mean()) / h.std(), (l - l.mean()) / l.std()
    lags = np.arange(-maxlag, maxlag + 1)
    cc = np.array([np.mean(h[max(0, L):len(h) + min(0, L)] * l[max(0, -L):len(l) - max(0, L)]) for L in lags])
    i = int(np.argmax(cc))
    dl = 0.0
    if 0 < i < len(cc) - 1:
        den = cc[i - 1] - 2 * cc[i] + cc[i + 1]
        dl = 0.5 * (cc[i - 1] - cc[i + 1]) / den if den else 0.0
    return float(lags[i] + dl), float(cc[i]), float(cc[maxlag]), bool(i in (0, len(cc) - 1))


def lag_check(tapes, lab):
    rows = []
    for walk in ('walk-231705', 'walk-231921'):
        stops = lab[walk][next(s for s in lab[walk] if s != 'dist_m')]
        segs = json.loads((REPO / 'tapes' / walk / 'transcript.json').read_text())['segments']
        tp = tapes[walk]
        for s in segs:
            if 'beers' not in s['text'] or s['t1'] - s['t0'] < 2.0:
                continue
            mid = (s['t0'] + s['t1']) / 2
            fd = next((f for a, b, f in stops if a <= mid < b), None)
            if fd is None:
                continue
            a, b = s['t0'] - 0.1, s['t1'] + 0.2
            r = dict(walk=walk, facing=fd, t0=s['t0'])
            h, l = env_ms(tp, a, b, BI['hi'], True), env_ms(tp, a, b, BI['lo'], True)
            r['env'] = dict(zip(('lag_ms', 'peak', 'zero', 'edge'), xcorr(h, l, 100)))
            k = np.hanning(11); k /= k.sum()
            dh = np.convolve(np.maximum(np.diff(h), 0), k, 'same'); dl = np.convolve(np.maximum(np.diff(l), 0), k, 'same')
            r['onset'] = dict(zip(('lag_ms', 'peak', 'zero', 'edge'), xcorr(dh, dl, 50)))
            rows.append(r)
    return rows


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    lab = json.loads((REPO / 'harness/rotation/facing_stops.json').read_text())['stops']
    walks = sorted(set(lab) | set(LADDERS))
    tapes = {w: Tape(w) for w in walks}
    rows = stop_rows(tapes, lab)
    for r in rows:
        for fam, keep in (('run', lambda k: k.startswith(('mod ', 'dip ', 'dmod ', 'tmod '))),
                          ('onset', lambda k: k.startswith(('onset ', 'tail ')))):
            if (r['walk'], r['a']) in SET_ASIDE[fam]:
                for k in [k for k in r if keep(k)]:
                    r.pop(k)
                r.setdefault('set_aside', []).append(fam)
    raw = stop_rows(tapes, lab, trim=False)
    lines, J = [], {'stops': rows}
    say = lines.append
    cut = [r['from_s'] - r['a'] for r in rows]
    say(f"set aside: {len(SET_ASIDE['run'])} stops from the run-based measures, {len(SET_ASIDE['onset'])} from the onset ones "
        "(SET_ASIDE gives why)")
    say(f"opening announcements dropped: {sum(c > 0 for c in cut)} of {len(rows)} stops, {np.mean(cut):.1f} s on average")
    for nm, rr in (('stops as labelled (the bar)', raw), ('announcements dropped', rows)):
        sc = score(rr, 'CDR hi - lo'); bf = sc['by_facing']
        say(f"CDR hi - lo, {nm}: 90 {bf[90]['mean']:+.1f} ({bf[90]['below']}/{bf[90]['n']} below), "
            f"180 {bf[180]['mean']:+.1f} ({bf[180]['below']}/{bf[180]['n']}), AUC {sc['auc']:.2f}")
    say(f"{len(rows)} stops; {sum('mod hi' in r for r in rows)} with >= {MIN_SPEECH_S:.0f} s of speech in runs; "
        f"speech per stop {np.mean([r.get('speech_s', 0) for r in rows]):.1f} s in runs; "
        f"onsets per stop {np.mean([r['n_onsets'] for r in rows]):.1f}")
    keys = (['CDR hi - lo', 'CDR range stat', 'mod hi - lo', 'mod hi - lo ch0', 'mod hi - lo ch1', 'span mod hi - lo', 'dip hi - lo',
             'dmod hi', 'dmod hi - mod lo', 'dmod - tmod hi', 'dip over floor hi', 'dip over floor lo'] + [f'mod {b}' for b in BI] +
            [f'{k} {L}' for L in ON_MS for k in ('onset colour', 'onset tilt', 'tail tilt')] +
            [f'onset colour 40 ch{m}' for m in range(2)])
    kind = lambda k: ('cdr' if k.startswith('CDR') else 'span' if k.startswith('span') else  # noqa: E731
                      'onset' if ('onset' in k or 'tail' in k) else 'run')
    J['scores'] = {}
    say('| measure | 90 | 180 | turned mean | toward rms | AUC | LOO signed | LOO unsigned | CDR on these stops: LOO, AUC |'
        ' slope/decade (sd, walks) | (3, no 213304) | decades to fake a turn |')
    say('|---|---|---|---|---|---|---|---|---|---|---|---|')
    for k in keys:
        s = score(rows, k)
        if not s:
            continue
        s['slopes'] = ladder_slopes(tapes, k, kind(k))
        sv = list(s['slopes'].values()); s3 = [v for w, v in s['slopes'].items() if w != 'walk-213304']
        s['slope_mean'] = float(np.mean(sv)) if sv else np.nan
        s['slope_mean_no213304'] = float(np.mean(s3)) if s3 else np.nan
        s['slope_sd'] = float(np.std(sv)) if sv else np.nan
        s['slope_walks'] = len(sv)
        s['decades_per_turn'] = float(abs(s['turned_mean'] / s['slope_mean'])) if sv else np.nan
        J['scores'][k] = s
        bf = s['by_facing']
        f = lambda fd: (f"{bf[fd]['mean']:+.1f} ({bf[fd]['below']}/{bf[fd]['n']} below)" if fd in bf else '-')  # noqa: E731
        g = lambda d: f"{d['balanced'] * 100:.0f}% ({d['toward_right']}/{d['toward_n']}, {d['turned_right']}/{d['turned_n']})" if d else '-'  # noqa: E731
        cs = s['cdr_same_stops']
        say(f"| {k} | {f(90)} | {f(180)} | {s['turned_mean']:+.2f} | {s['toward_sd']:.2f} | {s['auc']:.2f} | "
            f"{g(s['signed'])} | {g(s['unsigned'])} | {g(cs['signed'])}, {cs['auc']:.2f} | "
            f"{s['slope_mean']:+.2f} ({s['slope_sd']:.1f}, {s['slope_walks']}) | {s['slope_mean_no213304']:+.2f} | "
            f"{s['decades_per_turn']:.2f} |")
    main_k = ['CDR hi - lo', 'mod hi - lo', 'onset colour 40', 'onset tilt 30', 'dmod - tmod hi', 'dip over floor hi']
    say('\nPer stop, against the spot\'s facing-0 stops (a facing-0 stop against the other ones), dB:')
    say('| walk | spot | facing | speech s | onsets | ' + ' | '.join(main_k) + ' |')
    say('|---|---|---|---|---|' + '---|' * len(main_k))
    for key in sorted({(r['walk'], r['spot']) for r in rows}):
        st = [r for r in rows if (r['walk'], r['spot']) == key]
        for r in st:
            vals = []
            for k in main_k:
                ref = [o[k] for o in st if o['facing'] == 0 and o is not r and np.isfinite(o.get(k, np.nan))]
                v = r.get(k, np.nan)
                vals.append(f"{v - np.mean(ref):+.1f}" if ref and np.isfinite(v) else '-')
            say(f"| {r['walk'][5:]} | {r['spot']} | {r['facing']} | {r.get('speech_s', 0):.1f} | {r['n_onsets']} | "
                + ' | '.join(vals) + ' |')
    held = held_runs('walk-213304')
    J['control_213304'] = control_213304(tapes['walk-213304'], held)
    c = J['control_213304']
    say(f"\n213304 control: {c['held_n']} held stretches, {c['held_s']:.1f} s; talking {c['talk_s']:.0f} s; quiet "
        f"{c['quiet_s']:.0f} s; ladder (0-78 s) voiced windows that are held: {c['ladder_held_fraction'] * 100:.0f}%")
    say(f"held_sounds' stretches whose strongest 50-2000 Hz bin is 60 or 120 Hz: {c['held_at_mains']} of {c['held_n']}; "
        f"within 2 dB of the tape's 20th-percentile 1.1-8 kHz power: {c['held_within_2db_of_p20']} of {c['held_n']}")
    say('stops held fraction: ' + ', '.join(f"{a}-{b} f{fd} {x * 100:.0f}%" for a, b, fd, x in c['stops_held_fraction']))
    say('| band | mod held | mod talk | mod quiet | dip over floor held | talk | quiet |')
    say('|---|---|---|---|---|---|---|')
    for nm in [b for b in BI if b.startswith('oct')]:
        say(f"| {nm} | {c['held']['mod ' + nm]:+.1f} | {c['talk']['mod ' + nm]:+.1f} | {c['quiet']['mod ' + nm]:+.1f} | "
            f"{c['held']['dip_over_floor_db'][nm]:+.1f} | {c['talk']['dip_over_floor_db'][nm]:+.1f} | "
            f"{c['quiet']['dip_over_floor_db'][nm]:+.1f} |")
    lr = lag_check(tapes, lab)
    J['lag_check'] = lr
    say('\nlag check, per phrase, 4-8 kHz against 0.25-1 kHz (+ = high band later; mean (sd)). Onset strength: the '
        'rise of each band\'s dB envelope (half-wave rectified, 10 ms smoothing), lags to 50 ms. Envelope as briefed: '
        'the dB envelopes themselves, lags to 100 ms.')
    say('| walk | facing | phrases | onset lag ms | onset peak r | envelope peak r | envelope peaks at the 100 ms edge |')
    say('|---|---|---|---|---|---|---|')
    for walk in ('walk-231705', 'walk-231921'):
        for fd in (0, 90, 135, 180):
            v = [r for r in lr if r['walk'] == walk and r['facing'] == fd]
            if v:
                o = [r['onset'] for r in v]; e = [r['env'] for r in v]
                say(f"| {walk[5:]} | {fd} | {len(v)} | {np.mean([x['lag_ms'] for x in o]):+.1f} "
                    f"({np.std([x['lag_ms'] for x in o]):.1f}) | {np.mean([x['peak'] for x in o]):.2f} "
                    f"({np.std([x['peak'] for x in o]):.2f}) | {np.mean([x['peak'] for x in e]):+.2f} | "
                    f"{sum(x['edge'] for x in e)} of {len(v)} |")
    for walk in ('walk-231705', 'walk-231921'):
        for q in ('lag_ms', 'peak'):
            tw = [r['onset'][q] for r in lr if r['walk'] == walk and r['facing'] == 0]
            tu = [r['onset'][q] for r in lr if r['walk'] == walk and r['facing'] != 0]
            a_ = np.mean([(u < t) + 0.5 * (u == t) for u in tu for t in tw])
            J.setdefault('lag_auc', {})[f'{walk} {q}'] = float(a_)
            say(f"- {walk[5:]} onset {q}: turned phrases read below toward ones with probability {a_:.2f} "
                f"({len(tu)} turned, {len(tw)} toward)")
    txt = '\n'.join(lines)
    (OUT / 'blur.txt').write_text(txt + '\n', encoding='utf-8')
    (OUT / 'blur.json').write_text(json.dumps(J, indent=1, default=lambda o: o.item() if hasattr(o, 'item') else str(o)),
                                   encoding='utf-8')
    print(txt)


if __name__ == '__main__':
    main()
