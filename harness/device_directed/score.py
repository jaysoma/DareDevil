#!/usr/bin/env python3
"""Score every phrase of every window of set.jsonl with each method in methods.py, for the window's device.

usage: python3 score.py SET_DIR SOURCES_DIR OUT_DIR [--methods keyword shape_ngram ...] [--minilm DIR] [--gguf FILE]...
Every phrase is first put in the form a recogniser would give it (methods.asr): lowercase words, no punctuation. The
sources differ in typography (SLURP is lowercase and unpunctuated, AMI and Switchboard are not), and a method must
not find the spliced phrase by its punctuation.
Writes OUT_DIR/scores_<method>.jsonl (one line per window: its id and one score per phrase) and OUT_DIR/cost.json
(model size on disk and seconds per phrase, single-threaded except the general model, which uses --threads).
"""
import argparse
import json
import os
import time
import zipfile
from pathlib import Path

import numpy as np

import methods as M

ALL = ['keyword', 'shape_ngram', 'contrast_ngram', 'contrast_ngram_past', 'shape_embed', 'contrast_embed',
       'contrast_embed_past']


def brown(src):
    z = zipfile.ZipFile(src / 'nltk' / 'brown.zip')
    sents = []
    for n in z.namelist():
        if n.startswith('brown/c') and len(Path(n).name) == 4:
            for line in z.read(n).decode('utf-8', 'replace').splitlines():
                w = [t.rsplit('/', 1)[0] for t in line.split()]
                if w:
                    sents.append(' '.join(w))
    return sents


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('set_dir'); ap.add_argument('src'); ap.add_argument('out')
    ap.add_argument('--methods', nargs='+', default=ALL)
    ap.add_argument('--minilm'); ap.add_argument('--gguf', nargs='*', default=[]); ap.add_argument('--threads', type=int, default=4)
    ap.add_argument('--limit', type=int, default=0)
    ap.add_argument('--resume', action='store_true', help='general models: keep windows already scored, do the rest')
    a = ap.parse_args()
    setd, src, out = Path(a.set_dir), Path(a.src), Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    rows = [json.loads(l) for l in open(setd / 'set.jsonl')]
    if a.limit:
        rows = rows[:a.limit]
    train = json.load(open(setd / 'instructions_train.json'))
    costp = out / 'cost.json'
    cost = json.loads(costp.read_text()) if costp.exists() else {}
    n_phr = sum(len(r['phrases']) for r in rows)

    need_ngram = any(m in a.methods for m in ('keyword', 'shape_ngram', 'contrast_ngram', 'contrast_ngram_past'))
    if need_ngram:
        bg_s = brown(src)
        bg = M.KN3(bg_s)
        dev = {d: M.KN3(s) for d, s in train.items()}
        kw = {d: set(M.keywords(s, bg_s)) for d, s in train.items()}
        (out / 'keywords.json').write_text(json.dumps({d: sorted(v) for d, v in kw.items()}, indent=1))

    def write(name, fn, size_bytes, note):
        t0 = time.process_time()
        with open(out / f'scores_{name}.jsonl', 'w') as fh:
            for r in rows:
                fh.write(json.dumps({'id': r['id'], 'scores': [round(float(x), 5) for x in fn(r)]}) + '\n')
        dt = time.process_time() - t0
        cost[name] = {'seconds_per_phrase': round(dt / n_phr, 6), 'model_bytes': size_bytes, 'note': note}
        print(f'{name}: {dt / n_phr * 1000:.2f} ms per phrase', flush=True)

    texts = lambda r: [M.asr(p['text']) for p in r['phrases']]
    if 'keyword' in a.methods:
        write('keyword', lambda r: [len(set(M.toks(t)) & kw[r['device']]) for t in texts(r)],
              sum(len(w) + 1 for v in kw.values() for w in v), f'{M.KEYWORDS} words per device')
    if need_ngram:
        size = lambda m: (len(m.c3) + len(m.c2) + len(m.c1)) * 8           # one 8-byte count per stored n-gram
        mean = lambda v: sum(v) / len(v)
        if 'shape_ngram' in a.methods:
            write('shape_ngram', lambda r: [mean(dev[r['device']].logprobs(t)) - mean(bg.logprobs(t)) for t in texts(r)],
                  size(bg) + sum(size(m) for m in dev.values()), 'KN trigrams, counts at 8 bytes each')
        for name, past in (('contrast_ngram', False), ('contrast_ngram_past', True)):
            if name in a.methods:
                def f(r, past=past):
                    t = texts(r)
                    out_ = []
                    for i, s in enumerate(t):
                        ctx = t[:i] if past else t[:i] + t[i + 1:]
                        out_.append(mean(dev[r['device']].logprobs(s)) - mean(M.cache_logprobs(bg, s, ctx)))
                    return out_
                write(name, f, size(bg) + sum(size(m) for m in dev.values()), 'KN trigrams plus a word cache of the window')
    if any(m.endswith('embed') or m.endswith('embed_past') for m in a.methods):
        emb = M.MiniLM(a.minilm)
        t0 = time.process_time()
        dev_e = {d: emb(s) for d, s in train.items()}
        cost['embed_train_instructions_s'] = round(time.process_time() - t0, 1)
        size = os.path.getsize(Path(a.minilm) / 'onnx' / 'model.onnx')
        cache = {}

        def E(r):
            if r['id'] not in cache:
                cache[r['id']] = emb(texts(r))
            return cache[r['id']]
        t0 = time.process_time()
        for r in rows:
            E(r)
        enc_s = (time.process_time() - t0) / n_phr
        dev_fit = lambda r: M.topk_mean(E(r) @ dev_e[r['device']].T)
        if 'shape_embed' in a.methods:
            write('shape_embed', dev_fit, size, f'all-MiniLM-L6-v2 ONNX fp32; encoding {enc_s * 1000:.1f} ms per phrase')
        for name, past in (('contrast_embed', False), ('contrast_embed_past', True)):
            if name in a.methods:
                def f(r, past=past):
                    e = E(r)
                    s = e @ e.T
                    fit = dev_fit(r)
                    out_ = []
                    for i in range(len(e)):
                        others = s[i, :i] if past else np.concatenate([s[i, :i], s[i, i + 1:]])
                        out_.append(fit[i] - (M.topk_mean(others) if len(others) else 0.0))
                    return out_
                write(name, f, size, f'all-MiniLM-L6-v2 ONNX fp32; encoding {enc_s * 1000:.1f} ms per phrase')
    for g in a.gguf:
        name = 'llm_' + Path(g).stem.replace('-instruct-q4_k_m', '').replace('qwen2.5-', 'qwen')
        ask = M.Asker(g, threads=a.threads)
        path = out / f'scores_{name}.jsonl'
        done = {json.loads(l)['id'] for l in open(path)} if a.resume and path.exists() else set()
        todo = [r for r in rows if r['id'] not in done]
        t0 = time.time()
        with open(path, 'a' if done else 'w') as fh:
            for k, r in enumerate(todo):
                p = ask(r['device'], texts(r))
                fh.write(json.dumps({'id': r['id'], 'scores': [round(float(x), 6) for x in p[1:]], 'none': round(float(p[0]), 6)}) + '\n')
                fh.flush()
                if k % 50 == 0:
                    print(f'{name}: {len(done) + k}/{len(rows)} windows, {time.time() - t0:.0f} s', flush=True)
        dt = time.time() - t0
        if todo:
            ph = sum(len(r['phrases']) for r in todo)
            cost[name] = {'seconds_per_phrase': round(dt / ph, 5), 'seconds_per_window': round(dt / len(todo), 3),
                          'model_bytes': os.path.getsize(g), 'timed_windows': len(todo),
                          'note': f'llama.cpp, Q4_K_M, {a.threads} CPU threads, wall clock'}
        costp.write_text(json.dumps(cost, indent=1))
    costp.write_text(json.dumps(cost, indent=1))


if __name__ == '__main__':
    main()
