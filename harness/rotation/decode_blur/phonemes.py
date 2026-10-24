#!/usr/bin/env python3
"""What arrived, sound by sound, with no language model (2026-10-24). Jay: "take away the model".
facebook/wav2vec2-lv-60-espeak-cv-ft, a CTC phoneme recogniser (IPA, espeak style), greedy, no language model, run on
one mic (channel 0, so the two mics' sum can't comb-filter the highs) of each phrase take that Android's log marks
(begin of speech to end, +-0.2 s), 48 -> 16 kHz.
Per take:
  PER: phoneme error rate of "six fresh beers in the fridge" against the best-matching stretch of what it heard
  (semi-global edit distance), so "there's" / "there are" doesn't matter;
  the key consonants heard right: s (six), f and sh (fresh), b and z (beers), f and dʒ (fridge);
  blur: the mean entropy (bits) of the recogniser's per-frame odds over speech frames, which needs no reference.
    python3 phonemes.py <model dir>"""
import json, re, sys
from pathlib import Path
import numpy as np, torch
from scipy.signal import resample_poly
from transformers import Wav2Vec2ForCTC
REPO = Path(__file__).resolve().parents[3]
md = Path(sys.argv[1]); model = Wav2Vec2ForCTC.from_pretrained(md).eval()
vocab = json.loads((md / 'vocab.json').read_text()); inv = {i: t for t, i in vocab.items()}
pad = vocab.get('<pad>', 0)
def tok(cands):
    for c in cands:
        if c in vocab: return c
    raise SystemExit(f'none of {cands} in vocab')
REF = [tok(['s']), tok(['ɪ']), tok(['k']), tok(['s']), tok(['f']), tok(['ɹ', 'r']), tok(['ɛ']), tok(['ʃ']), tok(['b']),
       tok(['ɪɹ', 'ɪ']), *([] if 'ɪɹ' in vocab else [tok(['ɹ', 'r'])]), tok(['z']), tok(['ɪ']), tok(['n']), tok(['ð']), tok(['ə']),
       tok(['f']), tok(['ɹ', 'r']), tok(['ɪ']), tok(['dʒ', 'd'])]
KEY = {0: 's (six)', 4: 'f (fresh)', 7: 'ʃ (fresh)', 8: 'b (beers)'}
KEY[len(REF) - 4 - (0 if 'ɪɹ' in vocab else 0)] = 'f (fridge)'
KEY[REF.index(tok(['z']))] = 'z (beers)'; KEY[len(REF) - 1] = 'dʒ (fridge)'
def align(ref, hyp):
    m, n = len(ref), len(hyp); D = np.zeros((m + 1, n + 1)); D[1:, 0] = np.arange(1, m + 1)
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            D[i, j] = min(D[i - 1, j] + 1, D[i, j - 1] + 1, D[i - 1, j - 1] + (ref[i - 1] != hyp[j - 1]))
    j = int(np.argmin(D[m])); cost = D[m, j]; i = m; hit = set()
    while i > 0 and j > 0:
        if D[i, j] == D[i - 1, j - 1] + (ref[i - 1] != hyp[j - 1]):
            if ref[i - 1] == hyp[j - 1]: hit.add(i - 1)
            i, j = i - 1, j - 1
        elif D[i, j] == D[i - 1, j] + 1: i -= 1
        else: j -= 1
    return cost / m, hit
stops = json.loads((REPO / 'harness/rotation/facing_stops.json').read_text())['stops']
rows = []
for walk in ('walk-231705', 'walk-231921'):
    x = np.fromfile(REPO / 'tapes' / walk / f'{walk}.raw', dtype='<i2').reshape(-1, 2)[:, 0].astype(np.float32) / 32768
    log = json.loads((REPO / 'tapes' / walk / 'recognizer.json').read_text())['log']; U = {}
    for e in log:
        if e['utt'] < 0: continue
        r = U.setdefault(e['utt'], dict(begin=None, end=None, final=None)); t = e['tape_clock'] / 48000
        if e['event'] == 'begin' and r['begin'] is None: r['begin'] = t
        if e['event'] == 'end': r['end'] = t
        if e['event'] == 'segment': r['final'] = e['text']
    spans = [(a, b, fd) for s, v in stops[walk].items() if s != 'dist_m' for a, b, fd in v]
    for u, r in sorted(U.items()):
        if not r['final'] or not re.search(r'fresh|fridge|bridge|beer', r['final'].lower()) or r['begin'] is None or r['end'] is None: continue
        fd = next((f for a, b, f in spans if a <= r['begin'] < b), None)
        if fd is None: continue
        seg = x[int((r['begin'] - 0.2) * 48000):int((r['end'] + 0.2) * 48000)]
        s16 = resample_poly(seg, 1, 3).astype(np.float32); s16 = (s16 - s16.mean()) / (s16.std() + 1e-7)
        with torch.no_grad():
            lp = torch.log_softmax(model(torch.from_numpy(s16)[None]).logits[0], -1).numpy()
        ids = lp.argmax(-1); hyp = [inv[i] for k, i in enumerate(ids) if i != pad and (k == 0 or i != ids[k - 1])]
        p = np.exp(lp); ent = -(p * lp).sum(-1) / np.log(2); speech = ids != pad
        per, hit = align(REF, hyp)
        rows.append(dict(walk=walk, dist=2 if walk.endswith('705') else 5, facing=fd, per=per,
                         keys={v: (k in hit) for k, v in KEY.items()}, blur=float(ent[speech].mean()) if speech.any() else np.nan,
                         heard=''.join(hyp)))
out = ['facing | takes | PER on "six fresh beers in the fridge" | key consonants heard right | blur: mean entropy, bits']
for dist in (2, 5):
    out.append(f'{dist} m:')
    for fd in (0, 90, 135, 180):
        s = [r for r in rows if r['dist'] == dist and r['facing'] == fd]
        if s:
            kh = np.mean([np.mean(list(r['keys'].values())) for r in s])
            out.append(f"  {fd:3d} | {len(s):2d} | {np.mean([r['per'] for r in s]) * 100:4.0f}% | {kh * 100:4.0f}% | {np.nanmean([r['blur'] for r in s]):.3f}")
out.append('\nkey consonants heard right, all takes, facing (0) against turned (90-180):')
for k in KEY.values():
    f0 = [r['keys'][k] for r in rows if r['facing'] == 0]; tu = [r['keys'][k] for r in rows if r['facing'] >= 90]
    out.append(f"  {k:12s} facing {np.mean(f0) * 100:4.0f}% (n {len(f0)})   turned {np.mean(tu) * 100:4.0f}% (n {len(tu)})")
txt = '\n'.join(out); print(txt)
(REPO / 'results/rotation/decode_blur/phonemes.txt').write_text(txt + '\n')
json.dump(rows, open(REPO / 'results/rotation/decode_blur/phonemes_rows.json', 'w'), indent=0, ensure_ascii=False, default=float)
for r in rows[:6] + rows[-4:]: print(f"{r['walk'][5:]} {r['facing']:3d} PER {r['per'] * 100:3.0f}% | {r['heard'][:80]}")
