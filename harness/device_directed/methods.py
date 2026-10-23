#!/usr/bin/env python3
"""Brief 19's methods. Each scores every phrase of a window for the window's device; higher = more likely meant for it.

  keyword        Keyword spotting, the baseline: how many of the device's keywords the phrase contains. Each device's
                 KEYWORDS words are found automatically, not picked by hand: the words most over-represented in its
                 training instructions against general English (Brown), by log-odds with a prior, function words
                 excluded.
  shape_ngram    Shape only, small n-gram models: the phrase's mean per-word log-probability under a trigram model of
                 the device's training instructions, minus under a trigram model of general English (Brown). How
                 much more it sounds like the device's instructions than like English in general.
  contrast_ngram Shape and contrast (Jay's), n-gram: the same device fit, minus the fit to the surrounding stream: the
                 English model adapted to the window's other phrases with a word cache (CACHE weight).
  shape_embed    Shape only, sentence embeddings (all-MiniLM-L6-v2, ONNX): mean cosine similarity to the device's TOPK
                 nearest training instructions.
  contrast_embed Shape and contrast (Jay's), embeddings: that device fit minus the phrase's mean cosine similarity to its
                 TOPK nearest other phrases in the window.
  llm            A general model asked directly: the window's phrases are numbered and the model is asked which one, if
                 any, is someone speaking to the device. A phrase's score is the probability the model puts on its
                 number as the answer (llama.cpp, Qwen2.5 Instruct, 4-bit).

The n-gram, keyword and embedding methods also exist as causal variants (context = only the phrases before) where it
matters: contrast_*_past.
"""
import math
import re
import time
from collections import Counter, defaultdict

import numpy as np

TOK = re.compile(r"[a-z]+(?:'[a-z]+)?|\d+")
KEYWORDS = 25
CACHE = 0.2
TOPK = 5
UNSEEN, UNSEEN_MASS = 1e-6, 0.01     # an unseen word's probability, the same in every model


def toks(s):
    return TOK.findall(s.lower())


def asr(s):
    """A phrase as a recogniser would hand it over: lowercase words (apostrophes kept), no punctuation or case."""
    return ' '.join(re.findall(r"[a-z0-9]+(?:'[a-z]+)?", s.lower().replace('-', ' ')))


# ---------------------------------------------------------------- interpolated Kneser-Ney trigram
class KN3:
    """Interpolated Kneser-Ney trigram with absolute discount D, open vocabulary (unknown words share the unigram floor)."""

    def __init__(self, sentences, D=0.75):
        self.D = D
        c3, c2, c1 = Counter(), Counter(), Counter()
        for s in sentences:
            w = ['<s>', '<s>'] + toks(s) + ['</s>']
            for i in range(2, len(w)):
                c3[(w[i - 2], w[i - 1], w[i])] += 1
        # continuation counts for the lower orders
        self.c3 = c3
        self.h2 = Counter(); self.n2 = Counter()                    # trigram history totals and distinct followers
        cont2 = Counter()                                            # N1+(. w1 w2)
        for (a, b, c), n in c3.items():
            self.h2[(a, b)] += n; self.n2[(a, b)] += 1; cont2[(b, c)] += 1
        self.c2 = cont2
        self.h1 = Counter(); self.n1 = Counter(); cont1 = Counter()
        for (b, c), n in cont2.items():
            self.h1[b] += n; self.n1[b] += 1; cont1[c] += 1
        self.c1 = cont1
        self.tot1 = sum(cont1.values())
        self.V = len(cont1) + 1

    def p1(self, w):
        # A word this model never saw gets the same fixed probability UNSEEN in every model, so in a difference of two
        # models it cancels instead of favouring the smaller one (whose add-k floor would be higher). Seen words share
        # the rest of the mass by their continuation counts.
        c = self.c1.get(w, 0)
        return (1 - UNSEEN_MASS) * c / self.tot1 if c else UNSEEN

    def p2(self, b, w):
        h = self.h1.get(b, 0)
        if not h:
            return self.p1(w)
        return max(self.c2.get((b, w), 0) - self.D, 0) / h + self.D * self.n1[b] / h * self.p1(w)

    def p3(self, a, b, w):
        h = self.h2.get((a, b), 0)
        if not h:
            return self.p2(b, w)
        return max(self.c3.get((a, b, w), 0) - self.D, 0) / h + self.D * self.n2[(a, b)] / h * self.p2(b, w)

    def logprobs(self, s):
        w = ['<s>', '<s>'] + toks(s) + ['</s>']
        return [math.log(self.p3(w[i - 2], w[i - 1], w[i])) for i in range(2, len(w))]


def cache_logprobs(bg, s, context):
    """The English model adapted to the window: (1 - CACHE) * P_bg(w | h) + CACHE * P_cache(w)."""
    cnt = Counter(t for c in context for t in toks(c))
    n = sum(cnt.values())
    w = ['<s>', '<s>'] + toks(s) + ['</s>']
    out = []
    for i in range(2, len(w)):
        pc = cnt.get(w[i], 0) / n if n else 0.0
        out.append(math.log((1 - CACHE) * bg.p3(w[i - 2], w[i - 1], w[i]) + CACHE * pc))
    return out


# ---------------------------------------------------------------- keywords
# function words never count as keywords: a spotter keyed on "my" or "what" is not a keyword spotter
STOP = set("""a about above after again against all am an and any are as at be because been before being below between
both but by can could did do does doing down during each few for from further had has have having he her here hers
herself him himself his how i if in into is it its itself just let me more most my myself no nor not now of off on once
only or other our ours ourselves out over own please same she should so some such than that the their theirs them
themselves then there these they this those through to too under until up very was we were what what's when where which
while who whom why will with would you your yours yourself yourselves i'm it's don't can't i'd i'll you're""".split())


def keywords(dev_sents, bg_sents, k=KEYWORDS, prior=0.01):
    """Monroe et al.'s log-odds with an informative Dirichlet prior: the content words most over-represented in the
    device's training instructions against general English."""
    a, b = Counter(t for s in dev_sents for t in toks(s)), Counter(t for s in bg_sents for t in toks(s))
    na, nb = sum(a.values()), sum(b.values())
    allc = a + b
    n0 = sum(allc.values())
    z = {}
    for w, ca in a.items():
        if ca < 5 or w in STOP:
            continue
        cb = b.get(w, 0)
        aw = prior * allc[w] / n0 * 1e4
        a0 = prior * 1e4
        d = math.log((ca + aw) / (na + a0 - ca - aw)) - math.log((cb + aw) / (nb + a0 - cb - aw))
        var = 1 / (ca + aw) + 1 / (cb + aw)
        z[w] = d / math.sqrt(var)
    return [w for w, _ in sorted(z.items(), key=lambda x: -x[1])[:k]]


# ---------------------------------------------------------------- embeddings (all-MiniLM-L6-v2, ONNX)
class MiniLM:
    def __init__(self, folder):
        import onnxruntime as ort
        from tokenizers import Tokenizer
        self.tok = Tokenizer.from_file(f'{folder}/tokenizer.json')
        self.tok.enable_truncation(128)
        self.tok.enable_padding()
        so = ort.SessionOptions(); so.intra_op_num_threads = 1
        self.sess = ort.InferenceSession(f'{folder}/onnx/model.onnx', so, providers=['CPUExecutionProvider'])
        self.inputs = {i.name for i in self.sess.get_inputs()}

    def __call__(self, texts, batch=64):
        out = []
        for i in range(0, len(texts), batch):
            enc = self.tok.encode_batch(texts[i:i + batch])
            ids = np.array([e.ids for e in enc], dtype=np.int64)
            att = np.array([e.attention_mask for e in enc], dtype=np.int64)
            feed = {'input_ids': ids, 'attention_mask': att}
            if 'token_type_ids' in self.inputs:
                feed['token_type_ids'] = np.zeros_like(ids)
            h = self.sess.run(None, feed)[0]                       # (batch, tokens, 384)
            m = att[..., None].astype(np.float32)
            v = (h * m).sum(1) / np.maximum(m.sum(1), 1e-9)          # mean pooling, as sentence-transformers
            out.append(v / np.linalg.norm(v, axis=1, keepdims=True))
        return np.vstack(out)


def topk_mean(sims, k=TOPK):
    k = min(k, sims.shape[-1])
    return np.sort(sims, axis=-1)[..., -k:].mean(-1)


# ---------------------------------------------------------------- the general model
DEVICE_WORDS = {'car': "a car's voice assistant (navigation, messages, travel)",
                'kitchen': "a kitchen voice assistant (cooking, recipes, coffee, ordering food)",
                'watch': "a smartwatch voice assistant (alarms, reminders, calendar, time)",
                'general': "a home voice assistant (questions, music, news, weather, lights, lists)"}


class Asker:
    """llama.cpp with a 4-bit Qwen2.5 Instruct. One prompt per window; the next token's distribution over the phrase
    numbers (and 0 for none) is the answer."""

    def __init__(self, gguf, threads=4):
        from llama_cpp import Llama
        self.llm = Llama(model_path=gguf, n_ctx=4096, n_threads=threads, logits_all=False, verbose=False)
        self.num_ids = {}
        for n in range(0, 100):
            t = self.llm.tokenize(str(n).encode(), add_bos=False, special=False)
            self.num_ids[n] = t[0]

    def prompt(self, device, phrases):
        lines = '\n'.join(f'{i + 1}. {p}' for i, p in enumerate(phrases))
        sys = ('You read transcripts of speech overheard by a device. Most of it is people talking to each other, or '
               'singing, or talking to themselves. Answer with one number only.')
        user = (f'The device is {DEVICE_WORDS[device]}. Here is what it heard, one phrase per line:\n\n{lines}\n\n'
                f'Which line, if any, is someone speaking directly to the device, giving it an instruction or asking it '
                f'something? Answer with the line number, or 0 if none is.')
        return (f'<|im_start|>system\n{sys}<|im_end|>\n<|im_start|>user\n{user}<|im_end|>\n'
                f'<|im_start|>assistant\n')

    def last_logits(self):
        """The logits after the last evaluated token, straight from the context (this llama-cpp-python keeps no copy
        unless logits_all, which would cost a vocabulary-sized row per prompt token)."""
        return np.array(np.ctypeslib.as_array(self.llm._ctx.get_logits(), shape=(self.llm.n_vocab(),)), dtype=np.float64)

    def __call__(self, device, phrases):
        """Probability over 0..len(phrases) for the first answer token. Numbers above 9 are tokenized as single tokens
        by Qwen's tokenizer (digits are split: '12' -> '1','2'), so two-digit answers are scored by their first digit
        times the second token's probability."""
        self.llm.reset()
        toks_ = self.llm.tokenize(self.prompt(device, phrases).encode(), add_bos=False, special=True)
        self.llm.eval(toks_)
        logits = self.last_logits()
        digits = {d: self.llm.tokenize(str(d).encode(), add_bos=False)[0] for d in range(10)}
        lp = logits - logits.max()
        p = np.exp(lp); p /= p.sum()
        first = {d: p[t] for d, t in digits.items()}
        n = len(phrases)
        out = np.zeros(n + 1)
        out[0] = first[0]
        # one-digit lines
        for i in range(1, min(n, 9) + 1):
            out[i] = first[i]
        # two-digit lines: P(first digit) * P(second digit | first digit), one extra eval per first digit used
        state = self.llm.save_state()
        for d1 in range(1, n // 10 + 1):
            if first[d1] < 1e-6:
                continue
            self.llm.load_state(state)
            self.llm.eval([digits[d1]])
            l2 = self.last_logits()
            p2 = np.exp(l2 - l2.max()); p2 /= p2.sum()
            # "1" alone (then end of turn) is line 1; "1" then a digit is line 1x
            stop = sum(p2[t] for t in self.llm.tokenize(b'<|im_end|>', add_bos=False, special=True))
            out[d1] = first[d1] * stop if d1 <= n else 0.0
            for d2 in range(10):
                k = d1 * 10 + d2
                if 10 <= k <= n:
                    out[k] = first[d1] * p2[digits[d2]]
        return out
