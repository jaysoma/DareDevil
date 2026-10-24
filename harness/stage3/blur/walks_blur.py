#!/usr/bin/env python3
"""Brief N, first slice (2026-10-24): blur on Jay's 10 labelled walks, compared within each spot.
Blur = mean entropy (bits) of wav2vec2-lv-60-espeak-cv-ft's per-frame phoneme odds over speech frames; no language
model; one mic (channel 0); 16 kHz. Per stop (harness/rotation/facing_stops.json), its speech windows (voiced, past each
tape's first 2 s) are decoded in pieces of up to 8 s and their frames pooled. Two versions: every word, and with the
stop's opening callout (its first decode segment, up to 3 s) taken out, since words move blur too.
Each turned stop is taken against its own spot's facing-0 stops; the headline counts spots and stops, never a pooled
median. The CDR contrast (4-8 minus 0.1-1.1 kHz) on the same stops sits beside it.
    python3 walks_blur.py <model dir>"""
import json, sys
from pathlib import Path
import numpy as np, soundfile as sf, torch
from scipy.signal import resample_poly
from transformers import Wav2Vec2ForCTC
REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / 'harness/rotation'))
from facing_pooled import lin, feats
K = 'CDR hi - lo (4-8 vs 0.1-1.1 kHz)'
ROOM = {'walk-122038': 'living', 'walk-125621': 'living', 'walk-171645': 'living', 'walk-221126': 'living', 'walk-213304': 'kitchen',
        'walk-215800': 'kitchen', 'walk-224302': 'kitchen', 'walk-231705': 'kitchen', 'walk-231921': 'kitchen', 'walk-030615': 'other'}
md = Path(sys.argv[1]); model = Wav2Vec2ForCTC.from_pretrained(md).eval(); pad = json.loads((md / 'vocab.json').read_text()).get('<pad>', 0)
def frames_entropy(x48):
    out = []
    for a in range(0, len(x48), 8 * 48000):
        s = resample_poly(x48[a:a + 8 * 48000], 1, 3).astype(np.float32)
        if len(s) < 1600: continue
        s = (s - s.mean()) / (s.std() + 1e-7)
        with torch.no_grad():
            lp = torch.log_softmax(model(torch.from_numpy(s)[None]).logits[0], -1).numpy()
        sp = lp.argmax(-1) != pad; p = np.exp(lp[sp]); out.append(-(p * lp[sp]).sum(-1) / np.log(2))
    return np.concatenate(out) if out else np.array([])
stops = json.loads((REPO / 'harness/rotation/facing_stops.json').read_text())['stops']
rows = []
for walk, spots in stops.items():
    raw = REPO / 'tapes' / walk / f'{walk}.raw'
    x = (np.fromfile(raw, dtype='<i2').reshape(-1, 2)[:, 0].astype(np.float32) / 32768) if raw.exists() else sf.read(REPO / 'tapes' / walk / f'{walk}.wav', dtype='float32')[0][:, 0]
    bw = json.loads((REPO / 'tapes' / walk / 'band_windows.json').read_text()); t0 = np.array(bw['t0']); W = bw['win_s']
    D, R, P = lin(bw['dir_db']), lin(bw['dif_db']), lin(bw['pow_db']); tot = 10 * np.log10(P[:, 1:].sum(1)); voiced = (tot >= np.percentile(tot, 20) + 10) & (t0 >= 2)
    segs = json.loads((REPO / 'tapes' / walk / 'transcript.json').read_text())['segments']
    for spot, sl in spots.items():
        if spot == 'dist_m': continue
        for a, b, fd in sl:
            if fd not in (0, 90, 135, 180): continue
            call = next((s for s in segs if s['t0'] <= a + 0.5 and s['t1'] > a), None)
            cut = min(call['t1'], a + 3.0) + 0.25 if call else a
            res = {}
            for name, start in (('all', a), ('no callout', cut)):
                m = voiced & (t0 >= start) & (t0 + W <= b)
                if m.sum() < 2: res[name] = (np.nan, 0, np.nan); continue
                ent = frames_entropy(np.concatenate([x[int(t * 48000):int((t + W) * 48000)] for t in t0[m]]))
                res[name] = (float(ent.mean()) if len(ent) else np.nan, int(m.sum()), feats(D[m], R[m], P[m], m.sum())[K])
            rows.append(dict(walk=walk, spot=spot, room=ROOM[walk], dist=stops[walk]['dist_m'][spot], facing=fd, a=a, b=b,
                             blur=res['all'][0], n=res['all'][1], contrast=res['all'][2],
                             blur_nc=res['no callout'][0], n_nc=res['no callout'][1], contrast_nc=res['no callout'][2]))
json.dump(rows, open(REPO / 'results/stage3/blur/walks_rows.json', 'w'), indent=0, default=float)
out = []
for ver, bk, ck in (('every word', 'blur', 'contrast'), ('opening callout out', 'blur_nc', 'contrast_nc')):
    out.append(f"\n== {ver}: each turned stop minus its own spot's facing stops ==")
    out.append("walk     spot  room     | facing blur | turned stops: facing angle, blur change (bits), contrast change (dB)")
    up = tot = 0; ups = {}; cup = 0; misfit = []
    for (walk, spot) in sorted({(r['walk'], r['spot']) for r in rows}):
        st = [r for r in rows if r['walk'] == walk and r['spot'] == spot and r[bk] == r[bk]]
        f0 = [r for r in st if r['facing'] == 0]
        if not f0: continue
        fb, fc = np.mean([r[bk] for r in f0]), np.mean([r[ck] for r in f0])
        cells = []
        for r in st:
            if r['facing'] == 0: continue
            d, dc = r[bk] - fb, r[ck] - fc; tot += 1; up += d > 0; cup += dc < 0
            k = (r['room'], r['dist'] <= 2); ups.setdefault(k, [0, 0]); ups[k][0] += d > 0; ups[k][1] += 1
            cells.append(f"{r['facing']}: {d:+.2f} / {dc:+.1f}")
            if d <= 0: misfit.append(f"{walk[5:]} {spot} {r['facing']} deg, {r['a']}-{r['b']} s: blur {d:+.2f} bits, contrast {dc:+.1f} dB")
        out.append(f"{walk[5:]}  {spot:4s} {st[0]['room']:8s} | {fb:.2f} | " + '   '.join(cells))
    out.append(f"turned stops blurrier than their spot's facing: {up} of {tot};  contrast lower: {cup} of {tot}")
    out.append('by room and distance (blurrier / turned stops): ' + ', '.join(f"{k[0]} {'2 m' if k[1] else '4-6 m'} {v[0]}/{v[1]}" for k, v in sorted(ups.items())))
    out.append('the ones that go the other way: ' + ('; '.join(misfit) if misfit else 'none'))
txt = '\n'.join(out); print(txt); (REPO / 'results/stage3/blur/walks.txt').write_text(txt.strip() + '\n')
