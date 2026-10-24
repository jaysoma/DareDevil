#!/usr/bin/env python3
"""Step 3 of the facing scheme, without labels (2026-10-24): is the top of the contrast's spread a usable "facing"
reference? Per stop, CDR 4-8 kHz minus CDR 0.1-1.1 kHz pooled over its speech (facing_pooled.py's way, the first 2 s of
each tape skipped). Toward = facing 0, turned = 90 or more. The reference is a quantile of stops whose facing is never
looked at: those of the same tape (what a live session has), or of the same room's other walks. The labelled version
(brief A: the mean of known facing-0 stops) is the ceiling. Threshold below the reference: chosen on the other walks,
and fixed at 1.5 dB. Balanced accuracy, left out by walk."""
import json
import numpy as np
from facing_pooled import HANDLING_S, REPO, feats, lin

K = 'CDR hi - lo (4-8 vs 0.1-1.1 kHz)'
ROOM = {'walk-122038': 'living', 'walk-125621': 'living', 'walk-171645': 'living', 'walk-221126': 'living',
        'walk-213304': 'kitchen', 'walk-215800': 'kitchen', 'walk-224302': 'kitchen', 'walk-231705': 'kitchen',
        'walk-231921': 'kitchen', 'walk-030615': 'other'}
lab = json.loads((REPO / 'harness/rotation/facing_stops.json').read_text())['stops']
S = []
for walk, spots in lab.items():
    bw = json.loads((REPO / 'tapes' / walk / 'band_windows.json').read_text())
    t0 = np.array(bw['t0']); D, R, P = lin(bw['dir_db']), lin(bw['dif_db']), lin(bw['pow_db'])
    tot = 10 * np.log10(P[:, 1:].sum(1)); voiced = (tot >= np.percentile(tot, 20) + 10) & (t0 >= HANDLING_S)
    for spot, stops in spots.items():
        if spot == 'dist_m':
            continue
        for a, b, fd in stops:
            m = voiced & (t0 >= a) & (t0 + bw['win_s'] <= b)
            if m.sum() >= 2 and (fd == 0 or fd >= 90):
                S.append(dict(walk=walk, room=ROOM[walk], toward=fd == 0, c=feats(D[m], R[m], P[m], m.sum())[K]))
walks = sorted({s['walk'] for s in S})


def score(ref_of, fixed=None):
    d = {s_i: S[s_i]['c'] - ref_of(S[s_i]) for s_i in range(len(S))}
    def bal(idx, th):
        t = [d[i] >= -th for i in idx if S[i]['toward']]; u = [d[i] < -th for i in idx if not S[i]['toward']]
        return (np.mean(t) if t else np.nan, np.mean(u) if u else np.nan)
    tp = tn = nt = nu = 0
    for w in walks:
        test = [i for i in range(len(S)) if S[i]['walk'] == w]; train = [i for i in range(len(S)) if S[i]['walk'] != w]
        th = fixed if fixed is not None else max(np.arange(0, 4.01, 0.25), key=lambda x: np.nanmean(bal(train, x)))
        for i in test:
            if S[i]['toward']: nt += 1; tp += d[i] >= -th
            else: nu += 1; tn += d[i] < -th
    return f"{tp}/{nt} toward, {tn}/{nu} turned, balanced {(tp / nt + tn / nu) / 2 * 100:.0f}%"


out = [f"{len(S)} stops ({sum(s['toward'] for s in S)} toward, {sum(not s['toward'] for s in S)} turned), {len(walks)} walks"]
out.append("| reference | threshold chosen on the other walks | fixed 1.5 dB |\n|---|---|---|")
lab_room = lambda s: np.mean([x['c'] for x in S if x['room'] == s['room'] and x['walk'] != s['walk'] and x['toward']] or [np.nan])
out.append(f"| labelled: the room's other walks' facing-0 mean (brief A's) | {score(lab_room)} | {score(lab_room, 1.5)} |")
for q in (50, 75, 90, 100):
    tape = lambda s, q=q: np.percentile([x['c'] for x in S if x['walk'] == s['walk']], q)
    room = lambda s, q=q: np.percentile([x['c'] for x in S if x['room'] == s['room'] and x['walk'] != s['walk']] or [np.nan], q)
    out.append(f"| no labels: the tape's own stops, {q}th percentile | {score(tape)} | {score(tape, 1.5)} |")
    out.append(f"| no labels: the room's other walks, {q}th percentile | {score(room)} | {score(room, 1.5)} |")
share = np.mean([s['toward'] for s in S])
out.append(f"\nFacing-0 stops are {share * 100:.0f}% of these walks' stops; in a demo, where people mostly face the phone, the top of the spread sits nearer facing.")
txt = '\n'.join(out); (REPO / 'results/rotation/room_reference.txt').write_text(txt + '\n'); print(txt)
