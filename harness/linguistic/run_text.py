#!/usr/bin/env python3
"""Brief 18 step 2, text only: Jay's stage3.py run over an AMI meeting's words, offline, scored two ways.

stage3.py is a live service; this drives its own logic in batch. Imported unchanged from this folder: dlm_align (the
prompt and its parsing) and stage3.Pass (placing completion words, the majority pinning of a window's relative labels
onto the running speakers, pick() for a label with nothing behind it). run_pass()'s window rule is restated here
line for line, with the HTTP call to Ollama replaced by `model`. Nothing is told how many people there are.

Words arrive as a recogniser's phrases would: a phrase ends at a pause over PHRASE_GAP_S or at PHRASE_MAX words. One
pass per phrase, as stage3 does: the first waits for MIN_WORDS, then each takes the newest CONTEXT settled words (a
contiguous two-speaker stretch) plus up to MAX_NEW new words.

THE MODEL (--model):
  fisher   DiarizationLM-8b-Fisher-v2, Q4_K_M GGUF, through llama.cpp on CPU (--gguf): raw completion of the prompt,
           temperature 0, stop at [eod], num_ctx 4096, as models/Modelfile.fisher.
  oracle   NOT the model. A perfect two-speaker labeller: tags the window's words by their true speakers, at most two
           tags (any third true speaker in the window shares the second tag). It measures the pipeline's own ceiling:
           how well the N-speaker chaining can do when every two-way split is right.
  echo     NOT the model. Returns its input unchanged (settled labels, then the alternating prior): what the window
           rule and the pinning give with no information at all.

SCORES (per meeting, --out JSON):
  per window      each pass's new words, under that window's best mapping of labels to true speakers (bench_dlm.py's
                  permutation-free scoring): the two-way split
  whole meeting   one mapping for the meeting (each label to the true speaker it most overlaps, one to one): the
                  chaining too. Plus speakers invented against present, and splits (one person's words spread over two
                  labels, each holding >= 20% of them) and merges (one label holding >= 20% of each of two people's)
  breakdowns      short replies and overlapped words, whole-meeting mapping
  baseline        everything to the meeting's most talkative speaker
  timing          seconds per pass (fisher only), words per pass
usage: run_text.py <transcript.jsonl from transcripts.py> --model fisher|oracle|echo [--gguf PATH] [--threads 4]
                   [--until-s SECONDS] --out <out.json>
"""
import argparse
import itertools
import json
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import dlm_align as dl     # noqa: E402
import stage3 as S3        # noqa: E402

PHRASE_GAP_S, PHRASE_MAX = 0.5, 20


def phrases(seq):
    out, cur = [], []
    for k, x in enumerate(seq):
        if cur and (x['t'] - seq[k - 1]['t'] > PHRASE_GAP_S or len(cur) >= PHRASE_MAX):
            out.append(cur); cur = []
        cur.append(x)
    if cur:
        out.append(cur)
    return out


class Fisher:
    def __init__(self, gguf, threads):
        from llama_cpp import Llama
        self.llm = Llama(model_path=gguf, n_ctx=4096, n_threads=threads, verbose=False)

    def __call__(self, prompt, n_words, truth=None, prior=None):
        r = self.llm.create_completion(prompt, temperature=0.0, max_tokens=min(1536, n_words * 4 + 64), stop=['[eod]'])
        return r['choices'][0]['text']


def oracle(prompt, n_words, truth, prior):
    """Tags by the window's true speakers, first appearance order, at most two tags."""
    words = prompt[:-len(S3.PO.prompt_suffix)].split()
    ws = [w for w in words if not w.startswith(S3.PO.speaker_prefix)]
    order = []
    for t in truth:
        if t not in order:
            order.append(t)
    tag = {t: str(min(i + 1, 2)) for i, t in enumerate(order)}
    return dl.create_diarized_text(ws, [tag[t] for t in truth], S3.PO)


def echo(prompt, n_words, truth=None, prior=None):
    return prompt[:-len(S3.PO.prompt_suffix)]


def reset():
    S3._next[0] = 0
    S3.WORDS.clear()
    S3._backlog.clear()
    S3.STATE.update({'words': 0, 'passes': 0, 'rejects': 0, 'speakers': 0, 'first_word_ms': 0, 'pass_ms': 0, 'last': ''})


def run_pass(model, words, log):
    """stage3.run_pass(), restated: the same window, the same prior, the same parsing; model in place of Ollama."""
    settled = [w for w in words if w['spk']]
    new = [w for w in words if not w['spk']][:S3.MAX_NEW]
    if not new or (not settled and len(new) < S3.MIN_WORDS):
        return False
    ctx, seen = [], []
    for w in reversed(settled):
        if len(ctx) >= S3.CONTEXT:
            break
        if w['spk'] not in seen:
            if len(seen) == 2:
                break
            seen.append(w['spk'])
        ctx.insert(0, w)
    before = settled[:len(settled) - len(ctx)]
    p = S3.Pass(ctx, new, before)
    prompt = dl.create_diarized_text(p.ns, p.prior, S3.PO) + S3.PO.prompt_suffix
    t0 = time.perf_counter()
    completion = model(prompt, len(p.ns), [w['truth'] for w in p.win], p.prior)
    dt = time.perf_counter() - t0
    for t in completion.split(' '):
        t = t.strip()
        if not t:
            continue
        if t.startswith(S3.PO.speaker_prefix) and t.endswith(S3.PO.speaker_suffix):
            p.cur = t[len(S3.PO.speaker_prefix):-len(S3.PO.speaker_suffix)] or p.cur
        else:
            p.word(dl.normalize_text(t) or t)
    p.finish()
    log.append({'ctx': len(ctx), 'new': len(new), 's': round(dt, 3), 'new_ids': [w['k'] for w in new],
                'tagged': S3.PO.speaker_prefix in completion})
    return True


def best_map(pred, truth):
    """Best one-to-one mapping of predicted labels onto true speakers (maximise agreement); returns hits."""
    P, T = sorted(set(pred)), sorted(set(truth))
    c = Counter(zip(pred, truth))
    best = 0
    if len(P) <= len(T):
        for perm in itertools.permutations(T, len(P)):
            best = max(best, sum(c[(p, t)] for p, t in zip(P, perm)))
    else:
        for perm in itertools.permutations(P, len(T)):
            best = max(best, sum(c[(p, t)] for p, t in zip(perm, T)))
    return best


def whole_mapping(pred, truth):
    """One-to-one mapping for the whole meeting (greedy on overlap counts, then exact if small)."""
    P, T = sorted(set(pred)), sorted(set(truth))
    c = Counter(zip(pred, truth))
    if len(P) <= 7 and len(T) <= 7:
        best, mp = -1, {}
        small, large = (P, T) if len(P) <= len(T) else (T, P)
        for perm in itertools.permutations(large, len(small)):
            pairs = list(zip(small, perm)) if small is P else [(b, a) for a, b in zip(small, perm)]
            v = sum(c[pt] for pt in pairs)
            if v > best:
                best, mp = v, dict(pairs)
        return mp
    mp, used = {}, set()
    for (p, t), n in c.most_common():
        if p not in mp and t not in used:
            mp[p] = t; used.add(t)
    return mp


def score(seq, log, until_n):
    pred = [x['spk'] for x in seq[:until_n]]
    truth = [x['truth'] for x in seq[:until_n]]
    n = len(pred)
    ok = [p is not None for p in pred]
    # per window: each pass's new words
    hits = tot = 0
    for e in log:
        ids = [k for k in e['new_ids'] if k < until_n]
        if not ids:
            continue
        hits += best_map([pred[k] for k in ids], [truth[k] for k in ids]); tot += len(ids)
    mp = whole_mapping([p for p in pred if p], [t for p, t in zip(pred, truth) if p])
    right = [pred[k] is not None and mp.get(pred[k]) == truth[k] for k in range(n)]
    by_t = defaultdict(Counter); by_p = defaultdict(Counter)
    for p, t in zip(pred, truth):
        if p:
            by_t[t][p] += 1; by_p[p][t] += 1
    splits = sum(1 for t, c in by_t.items() if sum(v >= 0.2 * sum(c.values()) for v in c.values()) >= 2)
    tot_t = Counter(truth)
    merges = sum(1 for p, c in by_p.items() if sum(v >= 0.2 * tot_t[t] for t, v in c.items()) >= 2)
    sub = lambda f: (lambda ix: round(100 * sum(right[k] for k in ix) / len(ix), 1) if ix else None)([k for k in range(n) if f(seq[k])])
    return {'words': n, 'labelled_pct': round(100 * sum(ok) / n, 1) if n else None,
            'per_window_pct': round(100 * hits / tot, 1) if tot else None,
            'whole_meeting_pct': round(100 * sum(right) / n, 1) if n else None,
            'speakers_present': len(tot_t), 'speakers_invented': len(by_p), 'splits': splits, 'merges': merges,
            'short_replies_pct': sub(lambda x: x['short']), 'overlapped_pct': sub(lambda x: x['overlapped']),
            'baseline_most_talkative_pct': round(100 * tot_t.most_common(1)[0][1] / n, 1) if n else None,
            'passes': len(log), 'untagged_passes': sum(not e['tagged'] for e in log),
            'seconds_per_pass': round(sum(e['s'] for e in log) / len(log), 3) if log else None,
            'words_per_pass': round(sum(e['ctx'] + e['new'] for e in log) / len(log), 1) if log else None}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('transcript')
    ap.add_argument('--model', choices=('fisher', 'oracle', 'echo'), required=True)
    ap.add_argument('--gguf')
    ap.add_argument('--threads', type=int, default=4)
    ap.add_argument('--until-s', type=float)
    ap.add_argument('--out', required=True)
    a = ap.parse_args()
    seq = [json.loads(l) for l in open(a.transcript)]
    if a.until_s:
        seq = [x for x in seq if x['t'] <= a.until_s]
    model = Fisher(a.gguf, a.threads) if a.model == 'fisher' else oracle if a.model == 'oracle' else echo
    reset()
    words = S3.WORDS
    log = []
    for k, x in enumerate(seq):
        x['k'] = k
    for ph in phrases(seq):
        for x in ph:
            words.append({'w': x['w'], 'n': dl.normalize_text(x['w']) or x['w'], 'spk': None, 'truth': x['spk'], 'k': x['k']})
        while run_pass(model, words, log):
            pass
    pred = {w['k']: w['spk'] for w in words}
    for x in seq:
        x['spk_true'], x['truth'] = x['spk'], x['spk']
        x['spk'] = pred.get(x['k'])
    res = score(seq, log, len(seq))
    res.update({'transcript': Path(a.transcript).name, 'model': a.model, 'until_s': a.until_s})
    Path(a.out).write_text(json.dumps(res, indent=1))
    print(json.dumps(res))


if __name__ == '__main__':
    main()
