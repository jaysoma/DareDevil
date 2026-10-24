#!/usr/bin/env python3
"""Does pooling seconds of speech at one spot separate the facings? (2026-10-24)

Reads harness/rotation/facing_stops.json and each walk's tapes/<walk>/band_windows.json. Per stop, the speech windows
(total power 1.1-8 kHz at least 10 dB over the tape's 20th percentile) are summed, and per band the CDR and the level
are taken once. Features: CDR 4-8 kHz minus CDR 0.1-1.1 kHz (brief 20's HF - LF), CDR 4-8 minus 1.1-2 kHz, the level's
own tilt (4-8 minus 1.1-2 kHz), and the range statistic (CdrRange's mean CDR over 1.1-8 kHz). Each is taken against
the mean of its spot's facing-0 stops. Per-window values give the half-second jitter brief 20 reported.
"""
import json
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[2]
FEATS = {'CDR hi - lo (4-8 vs 0.1-1.1 kHz)': lambda c, l: c[3] - c[0],
         'CDR hi - mid (4-8 vs 1.1-2 kHz)': lambda c, l: c[3] - c[1],
         'level tilt (4-8 vs 1.1-2 kHz)': lambda c, l: l[3] - l[1],
         'range stat (mean CDR 1.1-8 kHz)': lambda c, l: np.mean(c[1:])}


def lin(a):
    return 10 ** (np.asarray(a, float) / 10)


def feats(D, R, P, n):
    c = 10 * np.log10(D.sum(0) / R.sum(0)); l = 10 * np.log10(P.sum(0) / n)
    return {k: float(f(c, l)) for k, f in FEATS.items()}


def main():
    lab = json.loads((REPO / 'harness/rotation/facing_stops.json').read_text())['stops']
    rows, jitter = [], {k: [] for k in FEATS}
    for walk, spots in lab.items():
        bw = json.loads((REPO / 'tapes' / walk / 'band_windows.json').read_text())
        t0 = np.array(bw['t0']); D, R, P = lin(bw['dir_db']), lin(bw['dif_db']), lin(bw['pow_db'])
        tot = 10 * np.log10(P[:, 1:].sum(1)); voiced = tot >= np.percentile(tot, 20) + 10
        for spot, stops in spots.items():
            if spot == 'dist_m':
                continue
            for a, b, fd in stops:
                m = voiced & (t0 >= a) & (t0 + bw['win_s'] <= b)
                if m.sum() < 2:
                    continue
                rows.append(dict(walk=walk, spot=spot, facing=fd, n=int(m.sum()), **feats(D[m], R[m], P[m], m.sum())))
                per = [feats(D[i:i + 1], R[i:i + 1], P[i:i + 1], 1) for i in np.flatnonzero(m)]
                for k in FEATS:
                    v = np.array([p[k] for p in per]); jitter[k] += list(v - v.mean())
    out = []
    say = out.append
    say(f"{len(rows)} stops at {len({(r['walk'], r['spot']) for r in rows})} spots in {len({r['walk'] for r in rows})} walks; "
        f"speech per stop {np.mean([r['n'] for r in rows]) * 0.5:.1f} s on average\n")
    for k in FEATS:
        d = {90: [], 135: [], 180: []}; spot_away = []
        for key in sorted({(r['walk'], r['spot']) for r in rows}):
            st = [r for r in rows if (r['walk'], r['spot']) == key]
            ref = [r[k] for r in st if r['facing'] == 0]
            if not ref:
                continue
            ref = np.mean(ref)
            for r in st:
                if r['facing'] in d:
                    d[r['facing']].append(r[k] - ref)
            aw = [r[k] - ref for r in st if r['facing'] == 180]
            if aw:
                spot_away.append(np.mean(aw))
        j = np.std(jitter[k])
        say(f"## {k}\n- half-second jitter (sd of one window about its stop): {j:.1f} dB; pooled over a stop's"
            f" ~{np.mean([r['n'] for r in rows]):.0f} windows: ~{j / np.sqrt(np.mean([r['n'] for r in rows])):.1f} dB")
        for fd, v in d.items():
            if v:
                say(f"- facing {fd} against the spot's facing 0: mean {np.mean(v):+.1f} dB, sd {np.std(v):.1f}, n {len(v)},"
                    f" below facing 0 in {sum(x < 0 for x in v)} of {len(v)}")
        say(f"- spots where facing away reads below facing the phone: {sum(x < 0 for x in spot_away)} of {len(spot_away)}\n")
    say('Per stop, against the spot\'s facing 0 (dB):')
    say('| walk | spot | facing | speech (s) | ' + ' | '.join(k.split(' (')[0] for k in FEATS) + ' |')
    say('|---|---|---|---|' + '---|' * len(FEATS))
    for key in sorted({(r['walk'], r['spot']) for r in rows}):
        st = [r for r in rows if (r['walk'], r['spot']) == key]
        ref = {k: np.mean([r[k] for r in st if r['facing'] == 0] or [np.nan]) for k in FEATS}
        for r in st:
            say(f"| {r['walk'][5:]} | {r['spot']} | {r['facing']} | {r['n'] * 0.5:.1f} | " +
                ' | '.join(f"{r[k] - ref[k]:+.1f}" for k in FEATS) + ' |')
    txt = '\n'.join(out)
    (REPO / 'results/rotation/facing_pooled.txt').write_text(txt + '\n')
    print(txt)


if __name__ == '__main__':
    main()
