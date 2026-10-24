#!/usr/bin/env python3
"""Brief 22's numbers.

Thresholds are brief 19's, unchanged: results/device_directed/summary.json, per method and device, where that device's
false accepts first reach 1 and 10 per hour across its streams (150 words a minute).

Step 1  Real requests to a person (Switchboard: directive, ask, commit), in place and spliced into another call: the share
        each method accepts, per device and pooled (each request is scored against each of the four devices), next to
        brief 19's generated to_person and subject phrases at the same thresholds. Paired: the same words in place against
        spliced, per method (does belonging to the conversation lower the contrast score?).
Step 2  The cues. (a) How often each fires on each kind of phrase. (b) Each cue as a veto on brief 19's best method
        (MiniLM contrast): a phrase it fires on is not accepted; the threshold is re-chosen so the stream's false
        accepts stay at 1 and 10 per hour, and hits, generated hard negatives and real requests are counted there.
        (c) A small learned combination: logistic regression on MiniLM contrast (standardised per device on the stream)
        and the cues, cross-fitted in two folds (brief 19's windows split by window, real requests by call); never
        trained on brief 19's generated phrases, which are scored but held out. What each cue adds: contrast alone, plus
        each cue, all cues.
Step 3  Jay's speakerphone case on real calls, for the car: every SLURP car test command spliced into a Switchboard call,
        against the real requests in other calls; the full curve (hits, real requests accepted, false accepts per hour
        of the calls themselves).
Catalogue: the real requests accepted at 10 per hour, by kind and cue (ids only: Switchboard's text isn't redistributed).

usage: evaluate_who.py REPO B19_SET_DIR B19_SCORES_DIR WHO_DIR OUT_DIR
"""
import json
import math
import sys
import zlib
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

REPO, SETD, B19S, WHO, OUT = map(Path, sys.argv[1:6])
DEVICES = ('car', 'kitchen', 'watch', 'general')
METHODS = ['keyword', 'shape_ngram', 'contrast_ngram', 'contrast_ngram_past', 'shape_embed', 'contrast_embed',
           'contrast_embed_past']
BEST = 'contrast_embed'
TARGETS = (1, 10)
WPM = 150
sys.path.insert(0, str(REPO / 'harness/who_for'))
import cues as C                                                               # noqa: E402

CUES = C.CUES
b19sum = json.load(open(REPO / 'results/device_directed/summary.json'))
TH = {(m, d, t): b19sum[m][d][f'at_{t}fa']['threshold'] for m in METHODS for d in DEVICES for t in TARGETS
      if b19sum.get(m, {}).get(d, {}).get(f'at_{t}fa')}
pct = lambda v: round(100 * float(np.mean(v)), 1) if len(v) else None

# ------------------------------------------------------------------------------------------------ brief 19's own set
rows = [json.loads(l) for l in open(SETD / 'set.jsonl')]
b19 = {m: {q['id']: q['scores'] for q in map(json.loads, open(B19S / f'scores_{m}.jsonl'))} for m in METHODS}
cue19 = {q['id']: q['cues'] for q in map(json.loads, open(WHO / 'cues_b19.jsonl'))}
P = []                                       # every phrase of brief 19's set: one dict
for r in rows:
    for i, p in enumerate(r['phrases']):
        lab = p['label'] if p['label'] != 'hard_negative' else 'hard_' + p['hard']
        P.append({'win': r['id'], 'device': r['device'], 'stream': r['stream'], 'label': lab,
                  'words': max(1, len(p['text'].split())), 'cues': cue19[r['id']][i],
                  **{m: b19[m][r['id']][i] for m in METHODS}})
# ------------------------------------------------------------------------------------------------ brief 22's windows
R, CAR = [], []
for l in open(WHO / 'scores_requests.jsonl'):
    w = json.loads(l)
    if w['set'] == 'car_in_calls':
        for p in w['phrases']:
            CAR.append({'win': w['id'], 'label': p['label'], 'cues': p['cues'], 'words': max(1, w['words'][p['i']]),
                        **{m: p['car'][m] for m in METHODS}})
    else:
        p = w['phrases'][0]
        R.append({'win': w['id'], 'set': w['set'], 'kind': w['kind'], 'cues': p['cues'],
                  'words': w['words'][p['i']], **{d: p[d] for d in DEVICES}})
index = {json.loads(l)['id']: json.loads(l) for l in open(WHO / 'requests_index.jsonl')}
for r in R:
    r['call'] = index[r['win'][:-1]]['call']

res = {'counts': {'requests': Counter(f"{r['set']} {r['kind']}" for r in R),
                  'car_in_calls_windows': len({c['win'] for c in CAR}),
                  'brief19_phrases': Counter(p['label'] for p in P)}}


# ----------------------------------------------------------------------------------------------------------- step 1
def accept(sel, m, t):
    """Share of real requests accepted, pooled over devices (each request against each device) and per device."""
    per = {d: pct([r[d][m] >= TH[m, d, t] for r in sel]) for d in DEVICES}
    return pct([r[d][m] >= TH[m, d, t] for r in sel for d in DEVICES]), per


s1 = {}
for m in METHODS:
    for t in TARGETS:
        if (m, 'car', t) not in TH:
            continue
        e = {}
        for st in ('inplace', 'spliced'):
            for k in ('all', 'directive', 'ask', 'commit'):
                sel = [r for r in R if r['set'] == st and (k == 'all' or r['kind'] == k)]
                e[f'{st}|{k}'] = accept(sel, m, t)
        hard = b19sum[m]['all'][f'at_{t}fa']['hard_accept_pct']
        e['b19_generated'] = {'to_person': hard.get('to_person'), 'subject': hard.get('subject'),
                              'foreign': hard.get('foreign'), 'hits': b19sum[m]['all'][f'at_{t}fa']['hit_pct']}
        s1[f'{m}|{t}'] = e
res['step1_accept'] = s1
# paired: the same words in place against spliced
pair = {}
by = defaultdict(dict)
for r in R:
    by[r['win'][:-1]][r['set']] = r
for m in METHODS:
    d_ = [by[k]['inplace'][d][m] - by[k]['spliced'][d][m] for k in by for d in DEVICES if len(by[k]) == 2]
    pair[m] = {'median_inplace_minus_spliced': round(float(np.median(d_)), 4),
               'share_lower_in_place': pct([x < 0 for x in d_]), 'n': len(d_)}
res['step1_paired'] = pair
# device-shaped real requests: those whose shape (MiniLM) passes the device's 10/h shape threshold
shaped = [(r, d) for r in R if r['set'] == 'inplace' for d in DEVICES if r[d]['shape_embed'] >= TH['shape_embed', d, 10]]
shaped_sp = [(by[r['win'][:-1]]['spliced'], d) for r, d in shaped]
res['step1_device_shaped'] = {
    'pairs': len(shaped), 'requests': len({r['win'] for r, _ in shaped}),
    'accepted_contrast_embed_10fa_inplace': pct([r[d][BEST] >= TH[BEST, d, 10] for r, d in shaped]),
    'accepted_contrast_embed_10fa_spliced': pct([r[d][BEST] >= TH[BEST, d, 10] for r, d in shaped_sp]),
    'accepted_contrast_embed_1fa_inplace': pct([r[d][BEST] >= TH[BEST, d, 1] for r, d in shaped]),
    'accepted_contrast_embed_1fa_spliced': pct([r[d][BEST] >= TH[BEST, d, 1] for r, d in shaped_sp])}
res['request_words'] = {k: float(np.median([r['words'] for r in R if r['set'] == 'inplace' and r['kind'] == k]))
                        for k in ('directive', 'ask', 'commit')}
res['request_words']['b19_instructions'] = float(np.median([p['words'] for p in P if p['label'] == 'instruction']))
res['request_words']['b19_to_person'] = float(np.median([p['words'] for p in P if p['label'] == 'hard_to_person']))

# ----------------------------------------------------------------------------------------------------------- step 2a
groups = {'b19 instructions': [p for p in P if p['label'] == 'instruction'],
          'b19 stream phrases': [p for p in P if p['label'] == 'stream'],
          'b19 to_person (generated)': [p for p in P if p['label'] == 'hard_to_person'],
          'b19 subject (generated)': [p for p in P if p['label'] == 'hard_subject'],
          'b19 foreign (real)': [p for p in P if p['label'] == 'hard_foreign'],
          'real directive': [r for r in R if r['set'] == 'inplace' and r['kind'] == 'directive'],
          'real ask': [r for r in R if r['set'] == 'inplace' and r['kind'] == 'ask'],
          'real commit': [r for r in R if r['set'] == 'inplace' and r['kind'] == 'commit'],
          'car in calls (SLURP car tests)': [c for c in CAR if c['label'] == 'instruction']}
res['cue_rates'] = {g: {c: pct([x['cues'][c] for x in v]) for c in CUES} | {'n': len(v)} for g, v in groups.items()}


# ----------------------------------------------------------------------------------------------------------- step 2b
def op_threshold(neg_scores, neg_words, target):
    """The lowest threshold at which accepted negatives stay at or under target per hour (brief 19's at_fa)."""
    hours = sum(neg_words) / WPM / 60
    s = np.sort(np.array(neg_scores))[::-1]
    k = int(math.floor(target * hours))                 # at most k false accepts
    if k >= len(s):
        return -np.inf
    return float(s[k]) + 1e-9 if k < len(s) else -np.inf


def veto_eval(veto):
    """MiniLM contrast with phrases that fire `veto` (a set of cues) rejected; thresholds re-chosen per device."""
    out = {}
    for t in TARGETS:
        hits, gen, real = [], defaultdict(list), []
        for d in DEVICES:
            dv = [p for p in P if p['device'] == d]
            negs = [p for p in dv if p['label'] == 'stream']
            sc = lambda p: p[BEST] if not any(p['cues'][c] for c in veto) else -np.inf
            th = op_threshold([sc(p) for p in negs], [p['words'] for p in negs], t)
            hits += [sc(p) >= th for p in dv if p['label'] == 'instruction']
            for k in ('hard_to_person', 'hard_subject', 'hard_foreign'):
                gen[k] += [sc(p) >= th for p in dv if p['label'] == k]
            real += [(r[d][BEST] if not any(r['cues'][c] for c in veto) else -np.inf) >= th
                     for r in R if r['set'] == 'inplace']
        out[t] = {'hits': pct(hits), 'to_person': pct(gen['hard_to_person']), 'subject': pct(gen['hard_subject']),
                  'foreign': pct(gen['hard_foreign']), 'real_requests': pct(real)}
    return out


res['step2_veto'] = {'none': veto_eval(set())}
for c in ('vocative', 'you', 'first_person', 'past_reported'):
    res['step2_veto'][c] = veto_eval({c})
res['step2_veto']['first_person+past_reported'] = veto_eval({'first_person', 'past_reported'})
res['step2_veto']['all four'] = veto_eval({'vocative', 'you', 'first_person', 'past_reported'})


# ----------------------------------------------------------------------------------------------------------- step 2c
def fold_of(key):
    return zlib.crc32(key.encode()) % 2


def standardise():
    st = {}
    for d in DEVICES:
        v = np.array([p[BEST] for p in P if p['device'] == d and p['label'] == 'stream'])
        st[d] = (float(v.mean()), float(v.std()))
    return st


ST = standardise()


def feats(score, d, cues, use):
    return [1.0, (score - ST[d][0]) / ST[d][1]] + [float(cues[c]) for c in use]


def fit_lr(X, y, w, l2=1e-2, iters=50):
    X, y, w = np.array(X), np.array(y, float), np.array(w, float)
    b = np.zeros(X.shape[1])
    for _ in range(iters):                                  # Newton steps
        p = 1 / (1 + np.exp(-X @ b))
        g = X.T @ (w * (p - y)) + l2 * b
        H = (X * (w * p * (1 - p))[:, None]).T @ X + l2 * np.eye(len(b))
        b -= np.linalg.solve(H, g)
    return b


def combo(use):
    """Cross-fitted logistic regression; returns held-out scores for brief 19's phrases, the real requests (per device)
    and step 3's car windows (averaged over both folds' models), plus each fold's coefficients."""
    sP = np.zeros(len(P)); sR = {d: np.zeros(len(R)) for d in DEVICES}; coefs = []
    models = []
    for f in (0, 1):
        X, y, w = [], [], []
        for p in P:
            if fold_of(p['win']) != f and p['label'] in ('instruction', 'stream'):
                X.append(feats(p[BEST], p['device'], p['cues'], use)); y.append(p['label'] == 'instruction')
                w.append(1.0 if p['label'] == 'instruction' else 0.2)
        for r in R:
            if r['set'] == 'inplace' and fold_of(r['call']) != f:
                for d in DEVICES:
                    X.append(feats(r[d][BEST], d, r['cues'], use)); y.append(0); w.append(1.0)
        b = fit_lr(X, y, w)
        models.append(b); coefs.append([round(float(x), 3) for x in b])
        for i, p in enumerate(P):
            if fold_of(p['win']) == f:
                sP[i] = np.dot(feats(p[BEST], p['device'], p['cues'], use), b)
        for i, r in enumerate(R):
            if fold_of(r['call']) == f:
                for d in DEVICES:
                    sR[d][i] = np.dot(feats(r[d][BEST], d, r['cues'], use), b)
    sCar = np.array([np.mean([np.dot(feats(c[BEST], 'car', c['cues'], use), b) for b in models]) for c in CAR])
    return sP, sR, sCar, coefs


def combo_eval(use):
    sP, sR, sCar, coefs = combo(use)
    out = {'coefficients_fold0': dict(zip(['bias', 'contrast'] + list(use), coefs[0])),
           'coefficients_fold1': dict(zip(['bias', 'contrast'] + list(use), coefs[1]))}
    for t in TARGETS:
        hits, gen, real = [], defaultdict(list), {'inplace': [], 'spliced': []}
        for d in DEVICES:
            idx = [i for i, p in enumerate(P) if p['device'] == d]
            negs = [i for i in idx if P[i]['label'] == 'stream']
            th = op_threshold([sP[i] for i in negs], [P[i]['words'] for i in negs], t)
            hits += [sP[i] >= th for i in idx if P[i]['label'] == 'instruction']
            for k in ('hard_to_person', 'hard_subject', 'hard_foreign'):
                gen[k] += [sP[i] >= th for i in idx if P[i]['label'] == k]
            for i, r in enumerate(R):
                if r['set'] == 'inplace':
                    real['inplace'].append(sR[d][i] >= th)
        out[t] = {'hits': pct(hits), 'to_person': pct(gen['hard_to_person']), 'subject': pct(gen['hard_subject']),
                  'foreign': pct(gen['hard_foreign']), 'real_requests': pct(real['inplace'])}
    return out, sR, sCar


res['step2_combo'] = {}
combo_scores = {}
for name, use in [('contrast only', []), *[(f'+ {c}', [c]) for c in CUES], ('all cues', CUES)]:
    ev, sR, sCar = combo_eval(use)
    res['step2_combo'][name] = ev
    combo_scores[name] = (sR, sCar)


# ----------------------------------------------------------------------------------------------------------- step 3
def curve3(pos, req, neg, negw):
    """Every threshold: car hits, real requests accepted, false accepts per hour of the calls' own phrases."""
    hours = sum(negw) / WPM / 60
    th = np.unique(np.concatenate([pos, req]))[::-1]
    ps, rs, ns = np.sort(pos), np.sort(req), np.sort(neg)
    hit = 1 - np.searchsorted(ps, th, 'left') / len(ps)
    acc = 1 - np.searchsorted(rs, th, 'left') / len(rs)
    fa = (len(ns) - np.searchsorted(ns, th, 'left')) / hours
    sel = np.linspace(0, len(th) - 1, min(300, len(th))).astype(int)
    auc = float(np.mean([(pos[:, None] > req[None, :]).mean() + 0.5 * (pos[:, None] == req[None, :]).mean()]))
    return {'threshold': th[sel].tolist(), 'hit': hit[sel].tolist(), 'real_request_accept': acc[sel].tolist(),
            'fa_per_hour_calls': fa[sel].tolist(), 'p_instruction_above_request': round(auc, 3), 'hours': round(hours, 2)}


s3, curves3 = {}, {}
pos_rows = [c for c in CAR if c['label'] == 'instruction']
neg_rows = [c for c in CAR if c['label'] == 'stream']
req_rows = [r for r in R if r['set'] == 'inplace']
for m in METHODS:
    pos = np.array([c[m] for c in pos_rows]); neg = np.array([c[m] for c in neg_rows])
    req = np.array([r['car'][m] for r in req_rows])
    cv = curve3(pos, req, neg, [c['words'] for c in neg_rows])
    curves3[m] = cv
    ops = {}
    for t in TARGETS:
        th = TH[m, 'car', t]
        ops[t] = {'hits': pct(pos >= th), 'real_requests_accepted': pct(req >= th),
                  'calls_fa_per_hour': round(float((neg >= th).sum() / cv['hours']), 2)}
    s3[m] = {'at_brief19_car_thresholds': ops, 'p_instruction_above_request': cv['p_instruction_above_request']}
for name in ('contrast only', 'all cues'):
    sR, sCar = combo_scores[name]
    pos = np.array([sCar[i] for i, c in enumerate(CAR) if c['label'] == 'instruction'])
    neg = np.array([sCar[i] for i, c in enumerate(CAR) if c['label'] == 'stream'])
    req = np.array([sR['car'][i] for i, r in enumerate(R) if r['set'] == 'inplace'])
    cv = curve3(pos, req, neg, [c['words'] for c in neg_rows])
    curves3[f'combo: {name}'] = cv
    # at the calls' own 1 and 10 false accepts per hour
    ops = {}
    for t in TARGETS:
        th = op_threshold(neg.tolist(), [c['words'] for c in neg_rows], t)
        ops[t] = {'hits': pct(pos >= th), 'real_requests_accepted': pct(req >= th)}
    s3[f'combo: {name}'] = {'at_calls_fa': ops, 'p_instruction_above_request': cv['p_instruction_above_request']}
res['step3'] = s3

# ----------------------------------------------------------------------------------------------------- catalogue
cat = []
for r in R:
    if r['set'] != 'inplace':
        continue
    for d in DEVICES:
        if r[d][BEST] >= TH[BEST, d, 10]:
            cat.append({'id': r['win'], 'call': r['call'], 'device': d, 'kind': r['kind'], 'words': r['words'],
                        'cues': [c for c in CUES if r['cues'][c]], 'contrast': round(r[d][BEST], 3),
                        'shape': round(r[d]['shape_embed'], 3)})
res['catalogue_summary'] = {
    'accepted_pairs': len(cat), 'requests': len({c['id'] for c in cat}),
    'by_kind': Counter(c['kind'] for c in cat), 'by_device': Counter(c['device'] for c in cat),
    'with_any_person_cue': pct([bool(set(c['cues']) & {'vocative', 'you', 'first_person', 'past_reported'}) for c in cat]),
    'by_cue': Counter(x for c in cat for x in c['cues']),
    'words_median': float(np.median([c['words'] for c in cat])) if cat else None}
OUT.mkdir(parents=True, exist_ok=True)
(OUT / 'summary.json').write_text(json.dumps(res, indent=1, default=dict))
(OUT / 'curves_step3.json').write_text(json.dumps(curves3))
with open(OUT / 'accepted_requests.jsonl', 'w') as fh:
    for c in cat:
        fh.write(json.dumps(c) + '\n')
print(json.dumps({'step1_best_10': res['step1_accept'][f'{BEST}|10'], 'paired': res['step1_paired'],
                  'shaped': res['step1_device_shaped']}, indent=1, default=dict))

# ------------------------------------------------------------------------------------------------ the full curves (step 1)
GRID = [0.25, 0.5, 1, 2, 3, 5, 7, 10, 15, 20, 30, 45, 60]
curves1 = {}
for m in ('contrast_embed', 'contrast_embed_past', 'contrast_ngram', 'shape_embed', 'shape_ngram', 'keyword'):
    cv = defaultdict(list)
    for t in GRID:
        acc = defaultdict(list)
        for d in DEVICES:
            dv = [p for p in P if p['device'] == d]
            negs = [p for p in dv if p['label'] == 'stream']
            th = op_threshold([p[m] for p in negs], [p['words'] for p in negs], t)
            acc['hits'] += [p[m] >= th for p in dv if p['label'] == 'instruction']
            acc['to_person (generated, spliced)'] += [p[m] >= th for p in dv if p['label'] == 'hard_to_person']
            acc['real requests, in place'] += [r[d][m] >= th for r in R if r['set'] == 'inplace']
            acc['real requests, spliced'] += [r[d][m] >= th for r in R if r['set'] == 'spliced']
        cv['fa_per_hour'].append(t)
        for k, v in acc.items():
            cv[k].append(pct(v))
    curves1[m] = dict(cv)
(OUT / 'curves_step1.json').write_text(json.dumps(curves1))
