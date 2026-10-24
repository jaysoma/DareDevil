#!/usr/bin/env python3
"""Jay's decode-blur test on the same-phrase walks (2026-10-24): Android SpeechRecognizer replaying walk-231705 (2 m)
and walk-231921 (5 m), where he says "there are six fresh beers in the fridge" 3-6 times at each facing.
Per utterance that holds the phrase:
  content words right, out of six / fresh / beers / fridge per phrase said (a phrase is counted per 'fridge|bridge'-like
  ending in the final, and at least one)
  drops: a partial that doesn't extend the one before (the recogniser threw its guess away and restarted)
  corrections: a partial that changes a word already shown
  longest wait for a new word, from the utterance's begin of speech to its end
  the CDR contrast (4-8 kHz minus 0.1-1.1 kHz) over the utterance's voiced windows, as an independent blur reading
Facing from harness/rotation/facing_stops.json (callout utterances excluded: only finals with 'fresh|fridge|bridge')."""
import json, re, sys
from pathlib import Path
import numpy as np
REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / 'harness/rotation'))
from facing_pooled import lin, feats
K = 'CDR hi - lo (4-8 vs 0.1-1.1 kHz)'
W = lambda s: re.sub(r"[^\w' ]+", ' ', s.lower()).split()
stops = json.loads((REPO / 'harness/rotation/facing_stops.json').read_text())['stops']
rows = []
for walk in ('walk-231705', 'walk-231921'):
    log = json.loads((REPO / 'tapes' / walk / 'recognizer.json').read_text())['log']
    U = {}
    for e in log:
        if e['utt'] < 0: continue
        r = U.setdefault(e['utt'], dict(begin=None, end=None, parts=[], final=None)); t = e['tape_clock'] / 48000
        if e['event'] == 'begin' and r['begin'] is None: r['begin'] = t
        if e['event'] == 'end': r['end'] = t
        if e['event'] == 'partial': r['parts'].append((t, e['text']))
        if e['event'] == 'segment': r['final'] = e['text']
    bw = json.loads((REPO / 'tapes' / walk / 'band_windows.json').read_text()); t0 = np.array(bw['t0'])
    D, R, P = lin(bw['dir_db']), lin(bw['dif_db']), lin(bw['pow_db']); tot = 10 * np.log10(P[:, 1:].sum(1))
    voiced = (tot >= np.percentile(tot, 20) + 10) & (t0 >= 2)
    spans = [(a, b, fd) for s, v in stops[walk].items() if s != 'dist_m' for a, b, fd in v]
    for u, r in sorted(U.items()):
        if not r['final'] or not re.search(r'fresh|fridge|bridge|beer', r['final'].lower()) or r['begin'] is None: continue
        fd = next((f for a, b, f in spans if a <= r['begin'] < b), None)
        if fd is None: continue
        fw = W(r['final']); n = max(1, sum(w in ('fridge', 'bridge') for w in fw))
        right = sum(min(fw.count(w), n) for w in ('six', 'fresh', 'beers', 'fridge'))
        drops = corr = 0; prev = []
        for t, txt in r['parts']:
            c = W(txt)
            if prev and c[:len(prev)] != prev:
                if c and prev and c[0] != prev[0] and not c[0].startswith(prev[0]): drops += 1
                else: corr += 1
            prev = c
        grow, best = [], 0
        for t, txt in r['parts']:
            if len(W(txt)) > best: best = len(W(txt)); grow.append(t)
        wait = float(np.max(np.diff([r['begin']] + grow + [r['end'] or grow[-1]])))
        m = voiced & (t0 + 0.5 > r['begin']) & (t0 < (r['end'] or r['begin'] + 3))
        rows.append(dict(walk=walk, dist=2 if walk == 'walk-231705' else 5, facing=fd, phrases=n, right=right / (4 * n),
                         drops=drops / n, corr=corr / n, wait=wait, contrast=feats(D[m], R[m], P[m], m.sum())[K] if m.sum() else np.nan,
                         final=r['final']))
out = []
for dist in (2, 5):
    out.append(f"\n{dist} m ({'walk-231705' if dist == 2 else 'walk-231921'}):  facing | takes | content words right | drops per phrase | corrections per phrase | longest wait for a word (s) | CDR contrast (dB)")
    for fd in (0, 90, 135, 180):
        s = [r for r in rows if r['dist'] == dist and r['facing'] == fd]
        if s:
            out.append(f"  {fd:3d} | {sum(r['phrases'] for r in s):2d} | {np.mean([r['right'] for r in s]) * 100:4.0f}% | {np.mean([r['drops'] for r in s]):.2f} | {np.mean([r['corr'] for r in s]):.2f} | {np.mean([r['wait'] for r in s]):.2f} | {np.nanmean([r['contrast'] for r in s]):+.1f}")
txt = '\n'.join(out); print(txt)
(REPO / 'results/rotation/decode_blur/same_phrase.txt').write_text(txt.strip() + '\n')
json.dump(rows, open(REPO / 'results/rotation/decode_blur/same_phrase_rows.json', 'w'), indent=0, default=float)
for r in rows: print(f"{r['walk'][5:]} {r['facing']:3d} right {r['right']*100:3.0f}% drops {r['drops']:.1f} wait {r['wait']:.2f} | {r['final'][:70]}")
