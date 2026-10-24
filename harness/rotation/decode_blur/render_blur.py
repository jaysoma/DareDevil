#!/usr/bin/env python3
"""Blur, drawn (2026-10-24): one take of "there are six fresh beers in the fridge" at each facing, walk-231705 (2 m).
Row 1, focus: the direct share of the sound per frequency and moment, from both mics (the direction-free CDR's
  c/(1+c), the Conductor's estimator: NFFT 2048, hop 512, PSD smoothing 0.92). Bright = direct, dark = room.
  Below c/2d = 1.09 kHz (dashed) the estimate is ill-conditioned.
Row 2, phonemes: the no-language-model decoder's odds per 20 ms (wav2vec2-lv-60-espeak-cv-ft, one mic), for the
  phonemes of the phrase and its commonest confusions. Sharp = one bright cell per moment; blurry = smeared.
    python3 render_blur.py <model dir> <out.png>"""
import json, re, sys
from pathlib import Path
import numpy as np, torch
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
from scipy.signal import resample_poly
from transformers import Wav2Vec2ForCTC
REPO = Path(__file__).resolve().parents[3]; SR, NFFT, HOP, ALPHA, C, D = 48000, 2048, 512, 0.92, 343.0, 0.157
md = Path(sys.argv[1]); model = Wav2Vec2ForCTC.from_pretrained(md).eval()
vocab = json.loads((md / 'vocab.json').read_text()); inv = {i: t for t, i in vocab.items()}
ROWS = [t for t in ['ð', 'ɛ', 'ɹ', 'ɑː', 's', 'ɪ', 'k', 'f', 'p', 'ʃ', 'b', 'iː', 'z', 'n', 'ə', 'æ', 'ʌ', 'ɜː', 'ɚ', 'dʒ'] if t in vocab]
walk = 'walk-231705'
x = np.fromfile(REPO / 'tapes' / walk / f'{walk}.raw', dtype='<i2').reshape(-1, 2).astype(np.float32) / 32768
log = json.loads((REPO / 'tapes' / walk / 'recognizer.json').read_text())['log']; U = {}
for e in log:
    if e['utt'] < 0: continue
    r = U.setdefault(e['utt'], dict(begin=None, end=None, final=None)); t = e['tape_clock'] / SR
    if e['event'] == 'begin' and r['begin'] is None: r['begin'] = t
    if e['event'] == 'end': r['end'] = t
    if e['event'] == 'segment': r['final'] = e['text']
stops = [(a, b, f) for s, v in json.loads((REPO / 'harness/rotation/facing_stops.json').read_text())['stops'][walk].items() if s != 'dist_m' for a, b, f in v]
def decode(seg):
    s16 = resample_poly(seg[:, 0], 1, 3).astype(np.float32); s16 = (s16 - s16.mean()) / (s16.std() + 1e-7)
    with torch.no_grad():
        p = torch.softmax(model(torch.from_numpy(s16)[None]).logits[0], -1).numpy()
    ids = p.argmax(-1); sp = ids != vocab.get('<pad>', 0)
    return p, ids, sp, float(-(p[sp] * np.log2(p[sp] + 1e-12)).sum(-1).mean())
cut = lambda r: x[int((r['begin'] - 0.2) * SR):int((r['end'] + 0.2) * SR)]
takes = {}
for u, r in sorted(U.items()):
    if r['final'] and r['end'] and re.search(r'fridge|bridge', r['final'].lower()):
        fd = next((f for a, b, f in stops if a <= r['begin'] < b), None)
        if fd is not None: takes.setdefault(fd, []).append((r, decode(cut(r))[3], len(re.findall(r'fridge|bridge', r['final'].lower()))))
take, mean_blur = {}, {}
for fd, L in takes.items():                        # the single-phrase take nearest its facing's mean blur over all takes
    mean_blur[fd] = (np.mean([b for _, b, _ in L]), len(L))
    take[fd] = min([t for t in L if t[2] == 1] or L, key=lambda t: abs(t[1] - mean_blur[fd][0]))[0]
fig, ax = plt.subplots(3, 4, figsize=(17, 9), gridspec_kw={'height_ratios': [3, 3, 0.5]})
f = np.fft.rfftfreq(NFFT, 1 / SR); gn = np.sinc(2 * f * D / C); top = f <= 8000; win = np.hanning(NFFT)
for col, fd in enumerate((0, 90, 135, 180)):
    r = take[fd]; seg = cut(r)
    n = (len(seg) - NFFT) // HOP + 1; psd = None; fr = np.zeros((n, top.sum()))
    for i in range(n):
        X1, X2 = np.fft.rfft(seg[i * HOP:i * HOP + NFFT, 0] * win), np.fft.rfft(seg[i * HOP:i * HOP + NFFT, 1] * win)
        now = (np.abs(X1) ** 2, np.abs(X2) ** 2, X1 * np.conj(X2))
        psd = now if psd is None else tuple(ALPHA * o + (1 - ALPHA) * q for o, q in zip(psd, now))
        gx = psd[2] / (np.sqrt(psd[0] * psd[1]) + 1e-20); xx, rr = np.abs(gx) ** 2, np.real(gx)
        c = np.clip((xx - gn * rr + np.sqrt(np.maximum(gn ** 2 * rr ** 2 - gn ** 2 * xx + gn ** 2 - 2 * gn * rr + xx, 0))) / np.maximum(1 - xx, 1e-6), 0, 1e4)
        fr[i] = c[top] / (1 + c[top])
    from scipy.ndimage import median_filter
    e = np.array([10 * np.log10(np.mean(seg[i * HOP:i * HOP + NFFT] ** 2) + 1e-12) for i in range(n)])
    fr = median_filter(fr, size=(3, 5)); fr[e < np.percentile(e, 35)] = np.nan       # pauses masked, by time
    cm = plt.get_cmap('magma').copy(); cm.set_bad('#1b1b1b')
    A = ax[0, col]; A.imshow(fr.T, origin='lower', aspect='auto', cmap=cm, vmin=0, vmax=1,
                             extent=[0, n * HOP / SR, 0, 8]); A.axhline(1.09, ls='--', c='w', lw=0.8)
    A.set_title(f"facing {fd}°  (2 m)\nblur over all {mean_blur[fd][1]} takes: {mean_blur[fd][0]:.2f} bits", fontsize=12)
    A.set_ylabel('kHz' if col == 0 else ''); A.set_xlabel('s')
    p, ids, sp, ent = decode(seg)
    P = p[sp][:, [vocab[t] for t in ROWS]]
    B = ax[1, col]; B.imshow(P.T, origin='lower', aspect='auto', cmap='viridis', vmin=0, vmax=1)
    B.set_yticks(range(len(ROWS))); B.set_yticklabels(ROWS if col == 0 else [], fontsize=9); B.set_xticks([])
    B.set_xlabel(f"this take: blur {ent:.2f} bits", fontsize=10)
    heard = ''.join(inv[i] for k, i in enumerate(ids) if sp[k] and (k == 0 or i != ids[k - 1]))
    ax[2, col].axis('off'); ax[2, col].text(0.5, 0.5, heard, ha='center', va='center', fontsize=12)
ax[0, 0].text(-0.28, 0.5, 'focus\n(direct share,\n2 mics)', transform=ax[0, 0].transAxes, ha='center', va='center', fontsize=11)
ax[1, 0].text(-0.28, 0.5, 'phonemes heard\n(no language\nmodel, 1 mic)', transform=ax[1, 0].transAxes, ha='center', va='center', fontsize=11)
fig.suptitle('Blur: "there are six fresh beers in the fridge" at 2 m, each facing\'s most typical take', fontsize=15)
plt.tight_layout(rect=[0.03, 0, 1, 0.96]); plt.savefig(sys.argv[2], dpi=110); print('saved', sys.argv[2])
