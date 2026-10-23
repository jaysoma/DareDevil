#!/usr/bin/env python3
"""Brief 22: brief 19's methods, unchanged, on brief 22's windows, plus the who-it's-for cues.

The formulas are brief 19's (harness/device_directed/score.py), called from its own methods.py on the same models
(Brown and SLURP-train trigrams, the same keywords, all-MiniLM-L6-v2). check_against_brief19() recomputes brief 19's
scores for its own set and requires them to match exactly before anything else is scored.

Scored per window:
  inplace, spliced   the target phrase (the real request), for EVERY device (car, kitchen, watch, general)
  car_in_calls       every phrase, for the car device (the stream phrases give that stream's false accepts)
  brief 19's set     every phrase for its window's device: the cue features are added to brief 19's own scores

usage: score_who.py SOURCES_DIR B19_SET_DIR B19_SCORES_DIR REQ_DIR OUT_DIR --minilm DIR
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'device_directed'))
import methods as M                                                            # noqa: E402
from score import brown                                                       # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
import cues as CUES                                                            # noqa: E402

DEVICES = ('car', 'kitchen', 'watch', 'general')
METHODS = ['keyword', 'shape_ngram', 'contrast_ngram', 'contrast_ngram_past', 'shape_embed', 'contrast_embed',
           'contrast_embed_past']


class Scorer:
    def __init__(self, src, train, minilm):
        bg_s = brown(src)
        self.bg = M.KN3(bg_s)
        self.dev = {d: M.KN3(s) for d, s in train.items()}
        self.kw = {d: set(M.keywords(s, bg_s)) for d, s in train.items()}
        self.emb = M.MiniLM(minilm)
        self.dev_e = {d: self.emb(s) for d, s in train.items()}
        self.cache = {}

    def E(self, texts):
        new = [t for t in dict.fromkeys(texts) if t not in self.cache]
        if new:
            for t, v in zip(new, self.emb(new)):
                self.cache[t] = v
        return np.stack([self.cache[t] for t in texts])

    def phrase(self, texts, i, d):
        """Every brief 19 method's score for phrase i of a window (texts in recogniser form), for device d."""
        mean = lambda v: sum(v) / len(v)
        s = texts[i]
        dfit = mean(self.dev[d].logprobs(s))
        e = self.E(texts)
        fit = float(M.topk_mean(e[i:i + 1] @ self.dev_e[d].T)[0])
        sims = e @ e[i]
        allo = np.concatenate([sims[:i], sims[i + 1:]])
        past = sims[:i]
        return {
            'keyword': len(set(M.toks(s)) & self.kw[d]),
            'shape_ngram': dfit - mean(self.bg.logprobs(s)),
            'contrast_ngram': dfit - mean(M.cache_logprobs(self.bg, s, texts[:i] + texts[i + 1:])),
            'contrast_ngram_past': dfit - mean(M.cache_logprobs(self.bg, s, texts[:i])),
            'shape_embed': fit,
            'contrast_embed': fit - float(M.topk_mean(allo)),
            'contrast_embed_past': fit - (float(M.topk_mean(past)) if len(past) else 0.0)}


def check_against_brief19(sc, setd, b19, n=60):
    rows = [json.loads(l) for l in open(setd / 'set.jsonl')][:n]
    ref = {m: {q['id']: q['scores'] for q in map(json.loads, open(b19 / f'scores_{m}.jsonl'))} for m in METHODS}
    worst = 0.0
    for r in rows:
        t = [M.asr(p['text']) for p in r['phrases']]
        for i in range(len(t)):
            got = sc.phrase(t, i, r['device'])
            for m in METHODS:
                worst = max(worst, abs(got[m] - ref[m][r['id']][i]))
    if worst > 1e-4:
        raise SystemExit(f'does not reproduce brief 19: worst difference {worst}')
    return worst


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('src'); ap.add_argument('b19_set'); ap.add_argument('b19_scores'); ap.add_argument('req'); ap.add_argument('out')
    ap.add_argument('--minilm', required=True)
    a = ap.parse_args()
    src, setd, b19, req, out = map(Path, (a.src, a.b19_set, a.b19_scores, a.req, a.out))
    out.mkdir(parents=True, exist_ok=True)
    train = json.load(open(setd / 'instructions_train.json'))
    CUES.init(src)
    sc = Scorer(src, train, a.minilm)
    worst = check_against_brief19(sc, setd, b19)
    print(f'reproduces brief 19 on its first 60 windows: worst difference {worst:.2e}', flush=True)
    with open(out / 'scores_requests.jsonl', 'w') as fh:
        for l in open(req / 'requests.jsonl'):
            w = json.loads(l)
            t = [M.asr(p['text']) for p in w['phrases']]
            if w['set'] == 'car_in_calls':
                res = [{'i': i, 'label': p['label'], 'cues': CUES.cues(t[i]), 'car': sc.phrase(t, i, 'car')}
                       for i, p in enumerate(w['phrases'])]
            else:
                i = w['pos']
                res = [{'i': i, 'label': 'real_request', 'cues': CUES.cues(t[i]),
                        **{d: sc.phrase(t, i, d) for d in DEVICES}}]
            fh.write(json.dumps({'id': w['id'], 'set': w['set'], 'kind': w['kind'], 'phrases': res,
                                 'words': [len(x.split()) for x in t]}) + '\n')
    # the cues on every phrase of brief 19's own set (its scores are reused from its own files)
    with open(out / 'cues_b19.jsonl', 'w') as fh:
        for l in open(setd / 'set.jsonl'):
            r = json.loads(l)
            fh.write(json.dumps({'id': r['id'], 'cues': [CUES.cues(M.asr(p['text'])) for p in r['phrases']]}) + '\n')
    (out / 'requests_index.jsonl').write_text((req / 'requests_index.jsonl').read_text())
    print('scored', flush=True)


if __name__ == '__main__':
    main()
