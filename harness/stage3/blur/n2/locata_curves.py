#!/usr/bin/env python3
"""Brief N2, steps 1-3 on LOCATA, from locata_blur.py's pieces (results/stage3/blur/n2/pieces.json).
The unit is one talker in one recording ("take"): blur added by the trip already takes the talker and the words out,
but each take is still compared within itself first, then counted across. One room (the HU Berlin lab), so the room
stratum is single; distance bands as brief N (< 1.5, 1.5-3, > 3 m). Wall distance: not available (the files on hand
give no wall coordinates in LOCATA's frame), so the head's place in front of the array (along, ahead) stands in.
- **Set aside first, and counted:** pieces whose close-talk decode has fewer than MIN_REF phonemes (no reference),
  then pieces whose blur added lies more than 3 sd from its take's mean.
- **Step 1, the facing curve:** 45 deg bins. Each turned piece (>= 90 deg) against its own take's facing pieces
  (< 45 deg) in the same distance band; per take, the bin means; across takes, the mean of the within-take
  differences per bin. Order test: Spearman's rho of facing against the measure inside each take x band, summed;
  its null permutes facing within take x band (N_PERM times).
- **Step 2, the distance curve:** facing within 30 deg only; slope of the measure on log2 distance inside each take,
  and the within-take (take-demeaned) slope with its permutation p.
- **Step 3, two factors:** measure ~ facing/180 + log2 distance, left out by recording: as is (one intercept: the
  close-talk reference already sets each take's zero), and within take (both sides take-demeaned).
- **Where it breaks:** takes whose turned pieces aren't blurrier, and pieces with a two-factor residual past 2 sd.
Writes results/stage3/blur/n2/report_numbers.json and curves.txt.
    python3 locata_curves.py"""
import json
from collections import defaultdict
from pathlib import Path
import numpy as np
from scipy.stats import spearmanr
REPO = Path(__file__).resolve().parents[4]
OUT = REPO / 'results/stage3/blur/n2'
MIN_REF, N_PERM, BINS = 6, 10000, ((0, 45), (45, 90), (90, 135), (135, 181))
rng = np.random.default_rng(0)
D = json.loads((OUT / 'pieces.json').read_text(encoding='utf-8'))
band = lambda d: '<1.5 m' if d < 1.5 else ('1.5-3 m' if d <= 3 else '>3 m')
bin_of = lambda f: next(i for i, (a, b) in enumerate(BINS) if a <= f < b)
take = lambda r: f"{r['recording'].replace('_recording', '_rec')}/{r['talker']}"
MEAS = {'blur added (bits)': 'blur_added', 'phoneme errors vs close-talk': 'per', 'far-field blur, raw (bits)': 'far_blur',
        'blur added, every frame (bits)': 'blur_vad_added'}
for r in D['pieces']:
    r['far_blur'] = r['far']['blur']; r['take'] = take(r); r['band'] = band(r['dist']); r['bin'] = bin_of(r['facing'])
out, num = [], {}
P = [r for r in D['pieces']]
noref = [r for r in P if len(r['close']['phones']) < MIN_REF]
P = [r for r in P if len(r['close']['phones']) >= MIN_REF]
far_out = []
for tk in sorted({r['take'] for r in P}):
    s = [r for r in P if r['take'] == tk]
    if len(s) < 4: continue
    v = np.array([r['blur_added'] for r in s]); m, sd = v.mean(), v.std(ddof=1)
    far_out += [r for r in s if abs(r['blur_added'] - m) > 3 * sd]
P = [r for r in P if r not in far_out]
out.append(f"{len(D['pieces'])} pieces in {len({r['take'] for r in D['pieces']})} takes (16 recordings). Set aside: {len(noref)} with under "
           f"{MIN_REF} close-talk phonemes, {len(far_out)} past 3 sd of their take. Kept: {len(P)}.")
for r in noref + far_out:
    out.append(f"  set aside: {r['take']} {r['t0']}-{r['t1']} s, facing {r['facing']:.0f}, {r['dist']:.2f} m, close '{''.join(r['close']['phones'])}'")
num['set_aside'] = dict(no_reference=len(noref), past_3sd=len(far_out), kept=len(P))
r_fd = np.corrcoef([r['facing'] for r in P], np.log2([r['dist'] for r in P]))[0, 1]
out.append(f"facing against log distance across the kept pieces: r = {r_fd:+.2f} (the two factors are {'tangled' if abs(r_fd) > 0.3 else 'nearly independent'} here)")
num['facing_logdist_r'] = r_fd
cr = np.corrcoef([r['close']['blur'] for r in P], [r['far']['blur'] for r in P])[0, 1]
out.append(f"close-talk blur against far-field blur, piece by piece: r = {cr:+.2f} (what the talker and words carry, which the subtraction removes)")
num['close_far_blur_r'] = cr

# ---- Step 1
def within_rho(rows, k, perm=False):
    tot = 0.0
    for key in {(r['take'], r['band']) for r in rows}:
        s = [r for r in rows if (r['take'], r['band']) == key]
        if len(s) < 3 or len({round(r['facing']) for r in s}) < 2: continue
        f = np.array([r['facing'] for r in s]); y = np.array([r[k] for r in s])
        if perm: f = rng.permutation(f)
        rho = spearmanr(f, y)[0]
        tot += 0 if np.isnan(rho) else rho
    return tot
num['step1'] = {}
for name, k in MEAS.items():
    out.append(f"\n== Step 1, {name}: each take's turned pieces against its own facing pieces, same distance band ==")
    out.append("take                     band     | facing <45: mean (n) | 45-90 | 90-135 | 135-180 | turned minus facing | rho")
    tk_res, diffs, cnt = [], defaultdict(list), [0, 0]
    for key in sorted({(r['take'], r['band']) for r in P}):
        s = [r for r in P if (r['take'], r['band']) == key]
        f0 = [r[k] for r in s if r['bin'] == 0]
        cells = []
        for b in range(4):
            v = [r[k] for r in s if r['bin'] == b]
            cells.append(f"{np.mean(v):5.2f} ({len(v)})" if v else '   -    ')
        tu = [r for r in s if r['bin'] >= 2]
        rho = spearmanr([r['facing'] for r in s], [r[k] for r in s])[0] if len(s) >= 3 else np.nan
        if f0 and tu:
            fm = np.mean(f0); dd = [r[k] - fm for r in tu]; cnt[0] += sum(x > 0 for x in dd); cnt[1] += len(dd)
            for r in s:
                if r['bin'] > 0: diffs[r['bin']].append(r[k] - fm)
            tk_res.append(dict(take=key[0], band=key[1], facing_mean=fm, n_facing=len(f0), turned_minus_facing=float(np.mean(dd)),
                               n_turned=len(dd), up=int(sum(x > 0 for x in dd)), rho=rho))
            gap = f"{np.mean(dd):+.2f} ({sum(x > 0 for x in dd)}/{len(dd)} up)"
        else:
            gap = 'no facing-and-turned pair'
        out.append(f"{key[0]:24s} {key[1]:8s} | " + ' | '.join(cells) + f" | {gap} | {rho:+.2f}")
    obs = within_rho(P, k); null = np.array([within_rho(P, k, True) for _ in range(N_PERM if k == 'blur_added' else 2000)])
    p = (np.sum(null >= obs) + 1) / (len(null) + 1)
    ntk = len(tk_res); nup = sum(t['turned_minus_facing'] > 0 for t in tk_res)
    out.append(f"takes x bands with turned blurrier/worse on average: {nup} of {ntk}; turned pieces above their own facing mean: {cnt[0]} of {cnt[1]}")
    out.append("across takes, mean of within-take differences from the facing bin: " +
               ', '.join(f"{BINS[b][0]}-{min(180, BINS[b][1])} deg {np.mean(diffs[b]):+.2f} (sd {np.std(diffs[b], ddof=1) if len(diffs[b]) > 1 else 0:.2f}, n {len(diffs[b])})" for b in (1, 2, 3) if diffs[b]))
    byband = {}
    for t in tk_res: byband.setdefault(t['band'], [0, 0, []]); byband[t['band']][0] += t['turned_minus_facing'] > 0; byband[t['band']][1] += 1; byband[t['band']][2].append(t['turned_minus_facing'])
    out.append('by distance band (takes turned blurrier / takes; mean within-take rise): ' +
               ', '.join(f"{b} {v[0]}/{v[1]} ({np.mean(v[2]):+.2f})" for b, v in sorted(byband.items())))
    for bnd in sorted({r['band'] for r in P}):
        dd = defaultdict(list)
        for t in tk_res:
            if t['band'] != bnd: continue
            for r in P:
                if r['take'] == t['take'] and r['band'] == bnd and r['bin'] > 0: dd[r['bin']].append(r[k] - t['facing_mean'])
        if dd: out.append(f"  {bnd}: " + ', '.join(f"{BINS[b][0]}-{min(180, BINS[b][1])} deg {np.mean(dd[b]):+.2f} (n {len(dd[b])})" for b in (1, 2, 3) if dd[b]))
    mono = [np.mean(diffs[b]) for b in (1, 2, 3) if diffs[b]]
    out.append(f"order 0 < 45 < 90 < 135 deg on those means: {'yes' if all(np.diff([0] + mono) > 0) else 'no'};  "
               f"within-take Spearman summed over take x band: {obs:+.2f}, permutation p = {p:.4f}")
    num['step1'][k] = dict(takes=tk_res, takes_up=nup, takes_n=ntk, pieces_up=cnt[0], pieces_n=cnt[1], rho_sum=obs, p_perm=p,
                           by_band={b: dict(up=v[0], n=v[1], mean_rise=float(np.mean(v[2]))) for b, v in byband.items()}, bin_diffs={f"{BINS[b][0]}": dict(mean=float(np.mean(diffs[b])), sd=float(np.std(diffs[b], ddof=1)) if len(diffs[b]) > 1 else None,
                                                             n=len(diffs[b])) for b in (1, 2, 3) if diffs[b]})

# ---- sound classes
out.append("\n== Survival by sound class: share of the close-talk phonemes the far field heard right ==")
out.append("class            | facing <45: share (n) | 45-90 | turned >=90 | takes with turned below their own facing")
num['survival'] = {}
for q in ('weak fricative', 'strong fricative', 'stop', 'nasal', 'vowel'):
    agg = defaultdict(lambda: [0, 0]); below = [0, 0]
    for tk in {r['take'] for r in P}:
        s = [r for r in P if r['take'] == tk]; per_tk = {}
        for g, sel in (('f', lambda r: r['bin'] == 0), ('m', lambda r: r['bin'] == 1), ('t', lambda r: r['bin'] >= 2)):
            h = sum(r['survival'].get(q, [0, 0])[0] for r in s if sel(r)); n = sum(r['survival'].get(q, [0, 0])[1] for r in s if sel(r))
            agg[g][0] += h; agg[g][1] += n; per_tk[g] = h / n if n else None
        if per_tk['f'] is not None and per_tk['t'] is not None: below[1] += 1; below[0] += per_tk['t'] < per_tk['f']
    sh = {g: (agg[g][0] / agg[g][1] if agg[g][1] else float('nan'), agg[g][1]) for g in 'fmt'}
    out.append(f"{q:16s} | {sh['f'][0] * 100:4.0f}% ({sh['f'][1]}) | {sh['m'][0] * 100:4.0f}% ({sh['m'][1]}) | {sh['t'][0] * 100:4.0f}% ({sh['t'][1]}) | {below[0]} of {below[1]}")
    num['survival'][q] = dict(facing=sh['f'], mid=sh['m'], turned=sh['t'], takes_below=below)

# ---- Step 2
num['step2'] = {}
for name, k in list(MEAS.items())[:2]:
    F = [r for r in P if r['facing'] < 30]
    out.append(f"\n== Step 2, {name} against log2 distance, facing within 30 deg ({len(F)} pieces) ==")
    sl, X, Y, G = [], [], [], []
    for tk in sorted({r['take'] for r in F}):
        s = [r for r in F if r['take'] == tk]; x = np.log2([r['dist'] for r in s]); y = np.array([r[k] for r in s])
        if len(s) >= 2: X += list(x - x.mean()); Y += list(y - y.mean()); G += [tk] * len(s)
        if len(s) >= 3 and np.ptp([r['dist'] for r in s]) >= 0.3:
            b = np.polyfit(x, y, 1)[0]; sl.append((tk, b, len(s), min(r['dist'] for r in s), max(r['dist'] for r in s)))
            out.append(f"  {tk:24s} n {len(s):2d}, {sl[-1][3]:.2f}-{sl[-1][4]:.2f} m: {b:+.2f} per doubling")
    X, Y = np.array(X), np.array(Y)
    b = (X @ Y) / (X @ X) if len(X) else np.nan
    null = []
    for _ in range(2000):
        Xp = X.copy()
        for g in set(G):
            ix = [i for i, gg in enumerate(G) if gg == g]; Xp[ix] = rng.permutation(Xp[ix])
        null.append((Xp @ Y) / (X @ X))
    p = (np.sum(np.array(null) >= b) + 1) / (len(null) + 1)
    out.append(f"takes with a rising slope: {sum(s[1] > 0 for s in sl)} of {len(sl)};  within-take slope over {len(X)} pieces: {b:+.2f} per doubling, permutation p = {p:.4f}")
    num['step2'][k] = dict(slopes=[dict(take=s[0], slope=s[1], n=s[2], lo=s[3], hi=s[4]) for s in sl], within_slope=b, n=len(X), p_perm=p)

# ---- Step 3
def design(rows, cols):
    X = [np.ones(len(rows))]
    if 'f' in cols: X.append(np.array([r['facing'] / 180 for r in rows]))
    if 'd' in cols: X.append(np.log2([r['dist'] for r in rows]))
    if 'x' in cols: X.append(np.array([r['facing'] / 180 for r in rows]) * np.log2([r['dist'] for r in rows]))
    return np.array(X).T
def demean(rows, k):
    rr = []
    for tk in {r['take'] for r in rows}:
        s = [r for r in rows if r['take'] == tk]
        if len(s) < 3: continue
        mf, md, my = np.mean([r['facing'] for r in s]), np.mean(np.log2([r['dist'] for r in s])), np.mean([r[k] for r in s])
        rr += [dict(r, facing=r['facing'] - mf, dist=2 ** (np.log2(r['dist']) - md), **{k: r[k] - my}) for r in s]
    return rr
num['step3'] = {}
for name, k in list(MEAS.items())[:2]:
    out.append(f"\n== Step 3, {name} ~ facing/180 + log2 distance, left out by recording ==")
    num['step3'][k] = {}
    for ver, rows in (('as is', P), ('within take', demean(P, k))):
        recs = sorted({r['recording'] for r in rows}); res = {}
        for cols in ('', 'f', 'd', 'fd', 'fdx'):
            sse = sst = 0.0
            for rec in recs:
                tr = [r for r in rows if r['recording'] != rec]; te = [r for r in rows if r['recording'] == rec]
                if ver == 'within take' and cols == '': pred = np.zeros(len(te))
                else:
                    beta = np.linalg.lstsq(design(tr, cols), [r[k] for r in tr], rcond=None)[0]; pred = design(te, cols) @ beta
                y = np.array([r[k] for r in te]); sse += ((y - pred) ** 2).sum()
                base = 0.0 if ver == 'within take' else np.mean([r[k] for r in tr]); sst += ((y - base) ** 2).sum()
            res[cols or 'none'] = 1 - sse / sst
        beta = np.linalg.lstsq(design(rows, 'fd'), [r[k] for r in rows], rcond=None)[0]
        out.append(f"  {ver:11s} ({len(rows)} pieces): held-out R2 facing alone {res['f']:+.2f}, distance alone {res['d']:+.2f}, "
                   f"both {res['fd']:+.2f}, both with facing x distance {res['fdx']:+.2f};  fit on all: {beta[1]:+.2f} per 180 deg, {beta[2]:+.2f} per doubling of distance")
        num['step3'][k][ver] = dict(n=len(rows), r2_facing=res['f'], r2_distance=res['d'], r2_both=res['fd'], r2_interaction=res['fdx'],
                                    per_180deg=beta[1], per_doubling=beta[2], intercept=beta[0])

# ---- Where it breaks
out.append("\n== Where it breaks ==")
s1 = num['step1']['blur_added']['takes']
for t in s1:
    if t['turned_minus_facing'] <= 0:
        s = [r for r in P if r['take'] == t['take'] and r['band'] == t['band']]
        out.append(f"  take going the other way: {t['take']} {t['band']}: turned {t['turned_minus_facing']:+.2f} bits vs its facing pieces "
                   f"({t['n_facing']} facing, {t['n_turned']} turned); " + '; '.join(
                       f"{r['facing']:.0f} deg {r['dist']:.2f} m blur+{r['blur_added']:.2f} lvl{r['level_added']:+.1f} dB at ({r['along']:+.1f},{r['ahead']:.1f})" for r in sorted(s, key=lambda r: r['facing'])))
beta = np.array([num['step3']['blur_added']['as is'][c] for c in ('intercept', 'per_180deg', 'per_doubling')])
res = np.array([r['blur_added'] for r in P]) - design(P, 'fd') @ beta; sd = res.std(ddof=3)
odd = [(r, e) for r, e in zip(P, res) if abs(e) > 2 * sd]
num['misfit_pieces'] = []
for r, e in sorted(odd, key=lambda x: -abs(x[1])):
    out.append(f"  piece off the two-factor fit by {e / sd:+.1f} sd: {r['take']} {r['t0']}-{r['t1']} s, facing {r['facing']:.0f}, {r['dist']:.2f} m, "
               f"close blur {r['close']['blur']:.2f}, far {r['far']['blur']:.2f}, PER {r['per']:.2f}, level added {r['level_added']:+.1f} dB, "
               f"{len(r['close']['phones'])} phones, head at ({r['along']:+.2f}, {r['ahead']:.2f}) m")
    num['misfit_pieces'].append(dict(take=r['take'], t0=r['t0'], t1=r['t1'], facing=r['facing'], dist=r['dist'], resid_sd=e / sd,
                                     close_blur=r['close']['blur'], far_blur=r['far']['blur'], per=r['per'], level_added=r['level_added']))
lg = np.array([l['lag_ms'] - l['trip_ms'] for l in D['lags']])
num['lag_check'] = dict(stretches=len(lg), mean_ms=float(lg.mean()), within_8_11_ms=float(np.mean((lg > 7) & (lg < 11))))
out.append(f"\nclose-talk timing: the far mic lags it by the trip plus {lg.mean():.1f} ms on average ({np.mean((lg > 7) & (lg < 11)) * 100:.0f}% of "
           f"{len(lg)} stretches between 7 and 11 ms): a fixed offset under one 20 ms decoder frame; pieces are padded 0.2 s.")
txt = '\n'.join(out); print(txt)
(OUT / 'curves.txt').write_text(txt + '\n', encoding='utf-8')
json.dump(num, open(OUT / 'report_numbers.json', 'w', encoding='utf-8'), indent=1, default=float, ensure_ascii=False)
