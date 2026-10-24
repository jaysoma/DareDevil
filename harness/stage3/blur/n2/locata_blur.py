#!/usr/bin/env python3
"""Brief N2 (2026-10-24): blur added by the trip on LOCATA tasks 3 and 4 (dev and eval, 16 recordings).
Decoder: wav2vec2-lv-60-espeak-cv-ft, greedy CTC, no language model, 48 -> 16 kHz, each decode normalised as the model
expects. Far field: one mic of the 160 mm DICIT pair (mic 5). Reference: the talker's close-talk mic
(audio_source_<talker>.wav, sample-aligned with the array; the lag is checked per stretch and logged).
- **Lone speech:** a talker's voice activity (results/animation/locata/<recording>.json) with any other talker's
  cut out, and GUARD_S either side of it (brief N: no other talker within 0.3 s). Each lone stretch of at least MIN_S
  is decoded whole, far field and close-talk, padded PAD_S either side.
- **Pieces:** the tracked facing moves 25-50 deg inside a typical utterance, so each stretch is cut where the facing
  leaves a FACE_TOL window or the head moves more than HEAD_TOL from the piece's mean (brief D's stretch rule); a piece
  is kept at MIN_S or more. Its decoder frames (20 ms) are the ones whose centre falls inside it.
Per piece, far field and close-talk alike:
  blur        mean entropy (bits) of the per-frame phoneme odds over speech frames (argmax not blank), as phonemes.py
  blur_vad    the same over every frame of the piece (all inside the talker's voice activity)
  phones      the greedy phoneme string
  level_db    RMS (dBFS) of the piece
and across them: per = edit distance of the far string to the close string over the close string's length; survival
by sound class = the share of the close string's phonemes of that class the far string matches in the alignment.
Writes results/stage3/blur/n2/pieces.json; locata_curves.py reads it.
    python3 locata_blur.py <model dir> <dev captures dir> <eval zenodo dir>"""
import json, sys
from pathlib import Path
import numpy as np, soundfile as sf, torch
from scipy.signal import resample_poly, correlate
from transformers import Wav2Vec2ForCTC
REPO = Path(__file__).resolve().parents[4]
GUARD_S, MIN_S, PAD_S, FACE_TOL, HEAD_TOL, SR = 0.3, 0.8, 0.2, 40.0, 0.3, 48000
MIC = 5
md, dev_dir, eval_dir = (Path(a) for a in sys.argv[1:4])
model = Wav2Vec2ForCTC.from_pretrained(md).eval()
vocab = json.loads((md / 'vocab.json').read_text(encoding='utf-8')); inv = {i: t for t, i in vocab.items()}
pad = vocab.get('<pad>', 0)
VOWEL = set('aeiouəɛɪɐʊʌæɔɑɚᵻɜɒyøœɨɯɵʉ')
CLASS = {'weak fricative': {'f', 'θ', 'v', 'ð'}, 'strong fricative': {'s', 'ʃ', 'z', 'ʒ'},
         'stop': {'p', 'b', 't', 'd', 'k', 'ɡ'}, 'nasal': {'m', 'n', 'ŋ'}}
def cls(p):
    for k, s in CLASS.items():
        if p in s: return k
    core = p.replace('ː', '').replace('̃', '')
    return 'vowel' if core and all(c in VOWEL for c in core) else None

def decode(x48):
    s = resample_poly(x48, 1, 3).astype(np.float32); s = (s - s.mean()) / (s.std() + 1e-7)
    with torch.no_grad():
        lp = torch.log_softmax(model(torch.from_numpy(s)[None]).logits[0], -1).numpy()
    return lp

def collapse(ids):
    return [inv[i] for k, i in enumerate(ids) if i != pad and (k == 0 or i != ids[k - 1])]

def align(ref, hyp):
    """Global edit distance and which ref positions are matched."""
    m, n = len(ref), len(hyp); D = np.zeros((m + 1, n + 1)); D[:, 0] = np.arange(m + 1); D[0, :] = np.arange(n + 1)
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            D[i, j] = min(D[i - 1, j] + 1, D[i, j - 1] + 1, D[i - 1, j - 1] + (ref[i - 1] != hyp[j - 1]))
    i, j, hit = m, n, set()
    while i > 0 and j > 0:
        if D[i, j] == D[i - 1, j - 1] + (ref[i - 1] != hyp[j - 1]):
            if ref[i - 1] == hyp[j - 1]: hit.add(i - 1)
            i, j = i - 1, j - 1
        elif D[i, j] == D[i - 1, j] + 1: i -= 1
        else: j -= 1
    return D[m, n], hit

def lone(speech, others):
    out = []
    for a, b in speech:
        segs = [(a, b)]
        for oa, ob in others:
            nxt = []
            for s, e in segs:
                ca, cb = oa - GUARD_S, ob + GUARD_S
                if cb <= s or ca >= e: nxt.append((s, e)); continue
                if ca > s: nxt.append((s, ca))
                if cb < e: nxt.append((cb, e))
            segs = nxt
        out += [(s, e) for s, e in segs if e - s >= MIN_S]
    return out

def pieces(a, b, t, fac, pos):
    """Facing-stable pieces of [a, b) on the 0.1 s track grid."""
    idx = np.flatnonzero((t >= a - 0.05) & (t < b)); out = []; i = 0
    while i < len(idx):
        j = i
        while j + 1 < len(idx):
            s = idx[i:j + 2]
            if np.isnan(fac[s]).any() or np.ptp(fac[s]) > FACE_TOL or np.linalg.norm(pos[s] - pos[s].mean(0), axis=1).max() > HEAD_TOL: break
            j += 1
        s = idx[i:j + 1]; p0, p1 = max(a, t[s[0]] - 0.05), min(b, t[s[-1]] + 0.05)
        if p1 - p0 >= MIN_S and not np.isnan(fac[s]).any(): out.append((p0, p1, s))
        i = j + 1
    return out

def side(lp, x, fr, a0, a1):
    """One signal's measures over frames fr and samples [a0, a1)."""
    p = np.exp(lp[fr]); ent = -(p * lp[fr]).sum(-1) / np.log(2); ids = lp[fr].argmax(-1); sp = ids != pad
    seg = x[a0:a1]
    return dict(blur=float(ent[sp].mean()) if sp.any() else float('nan'), blur_vad=float(ent.mean()),
                speech_frames=int(sp.sum()), phones=collapse(ids), level_db=float(10 * np.log10(np.mean(seg ** 2) + 1e-20)))

rows, lags = [], []
for f in sorted((REPO / 'results/animation/locata').glob('*_task*.json')):
    d = json.loads(f.read_text()); rec = d['recording']; set_, task, rn = rec.split('_')
    if set_ == 'dev':
        ad = dev_dir / f"{task}-{rn}-dicit"; far = sf.read(ad / 'pair48.wav', dtype='float64')[0][:, 0]   # pair48: mic5, mic10
    else:
        ad = eval_dir / set_ / task / rn / 'dicit'; far = sf.read(ad / 'audio_array_dicit.wav', dtype='float64')[0][:, MIC - 1]
    tr = d['tracks']
    for tk, v in tr.items():
        close = sf.read(ad / f'audio_source_{tk}.wav', dtype='float64')[0]
        close = close[:, 0] if close.ndim > 1 else close
        assert len(close) == len(far), (rec, tk, len(close), len(far))
        others = [s for k2, v2 in tr.items() if k2 != tk for s in v2['speech']]
        t = np.array(v['t'], float); fac = np.array(v['facing_deg'], float)
        pos = np.c_[v['along_m'], v['ahead_m']].astype(float); dist = np.array(v['dist_m'], float)
        for a, b in lone(v['speech'], others):
            s0, s1 = int(max(0, a - PAD_S) * SR), int(min(len(far) / SR, b + PAD_S) * SR)
            xc, xf = close[s0:s1], far[s0:s1]
            # lag of the far mic behind the close-talk mic, over +-30 ms (the trip is 2-11 ms at these distances)
            L = int(0.03 * SR); cc = correlate(xf, xc, mode='full', method='fft')[len(xc) - 1 - L:len(xc) + L]
            lag_ms = (int(np.argmax(np.abs(cc))) - L) / SR * 1000
            lags.append(dict(recording=rec, talker=tk, a=a, lag_ms=lag_ms, trip_ms=float(np.nanmean(dist[(t >= a) & (t < b)])) / 343 * 1000))
            lpc, lpf = decode(xc), decode(xf)
            nfr = min(len(lpc), len(lpf)); fc = s0 / SR + 0.02 * np.arange(nfr) + 0.0125   # frame centres, s
            for p0, p1, s in pieces(a, b, t, fac, pos):
                fr = np.flatnonzero((fc >= p0) & (fc < p1))
                if len(fr) < 10: continue
                a0, a1 = int(p0 * SR), int(p1 * SR)
                c, fa = side(lpc, close, fr, a0, a1), side(lpf, far, fr, a0, a1)
                dist_e, hit = align(c['phones'], fa['phones'])
                surv = {}
                for k, ph in enumerate(c['phones']):
                    q = cls(ph)
                    if q: surv.setdefault(q, [0, 0]); surv[q][0] += k in hit; surv[q][1] += 1
                rows.append(dict(recording=rec, set=set_, task=task, talker=tk, t0=round(p0, 3), t1=round(p1, 3),
                                 facing=float(fac[s].mean()), facing_ptp=float(np.ptp(fac[s])), dist=float(np.nanmean(dist[s])),
                                 along=float(pos[s, 0].mean()), ahead=float(pos[s, 1].mean()),
                                 close=c, far=fa, per=float(dist_e / max(1, len(c['phones']))), survival=surv,
                                 blur_added=fa['blur'] - c['blur'], blur_vad_added=fa['blur_vad'] - c['blur_vad'],
                                 level_added=fa['level_db'] - c['level_db']))
    print(rec, sum(r['recording'] == rec for r in rows), 'pieces', flush=True)
out = REPO / 'results/stage3/blur/n2'; out.mkdir(parents=True, exist_ok=True)
json.dump(dict(pieces=rows, lags=lags), open(out / 'pieces.json', 'w', encoding='utf-8'), indent=0, ensure_ascii=False)
lg = np.array([l['lag_ms'] - l['trip_ms'] for l in lags])
print(f"{len(rows)} pieces; far-field lag minus the trip's delay over {len(lg)} stretches: mean {lg.mean():+.1f} ms, "
      f"within 2 ms in {np.mean(np.abs(lg) < 2) * 100:.0f}%")
