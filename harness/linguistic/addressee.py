#!/usr/bin/env python3
"""Brief 18 step 3: to whom? Each dialogue act's addressee from the words, from the speaker's focus of attention, and
from both, on AMI meetings with both annotations. The direct test of the Tampere question: does facing add anything
once the words are known?

The target is AMI's annotated addressee: 'group' (every other participant) or one person. Dialogue acts the annotators
left without an addressee are not scored (counted in the summary).

Clues per dialogue act (only what the act itself and the conversation around it hold; nothing from the annotation but
the speaker's focus for the facing condition):
  words   the act ends in '?'; it holds 'you'/'your'; it holds 'we'/'us'/'everyone'/'guys'/'all of'; how long it is; it
          is a short reply (<= 3 words, all of them reply words); per candidate: did they speak the previous turn,
          do they take the next one, did they ask the previous turn's question. Names: AMI participants are addressed
          by name so rarely that no name feature is used (counted in the summary).
  facing  the share of the act the speaker looks at each candidate, at the table, the slide screen, the whiteboard,
          or nowhere annotated; how many people they look at.

Two kinds of predictor, both scored the same way:
  rules    words: a question goes to whoever takes the next turn, a short reply to whoever spoke before, else the
           group. facing: whoever the speaker looks at for more than half the act, else the group. both: the facing
           rule's person when there is one, else the words rule.
  learned  logistic regressions, trained leaving one meeting out: group or one person, then which person (a
           per-candidate model; the highest score wins).
Chance: always 'group' (the majority) for the whole set; a uniform pick among the other participants for 'one person'.
usage: addressee.py <meeting json dir> <out json>
"""
import json
import math
import random
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
from sklearn.linear_model import LogisticRegression

REPLY = {'yeah', 'yes', 'no', 'mm', 'mm-hmm', 'uh-huh', 'okay', 'ok', 'right', 'hmm', 'uh', 'um', 'sure', 'yep', 'nope',
         'alright', 'mm-mm', 'oh', 'ah', 'good', 'cool'}
YOU = {'you', 'your', "you're", 'yours', "you've", "you'll", "you'd", 'yourself'}
WE = {'we', 'us', "we're", "let's", 'everyone', 'everybody', 'guys', 'our', "we've", "we'll"}
PLACES = ('table', 'slide-screen', 'whiteboard')


def load(d):
    words = d['words']
    acts = d['dacts']
    focus = defaultdict(list)
    for f in d['focus']:
        focus[f['spk']].append(f)
    return words, acts, focus


def text(words, a):
    ws = [words[i] for i in range(a['w0'], a['w1'] + 1) if words[i]['spk'] == a['spk']]
    toks = [w['w'].lower() for w in ws]
    q = any('?' in w['punc'] for w in ws)
    return toks, q


def focus_shares(focus, spk, t0, t1, people):
    dur = max(t1 - t0, 1e-3)
    sh = Counter()
    for f in focus.get(spk, []):
        o = min(t1, f['t1']) - max(t0, f['t0'])
        if o > 0:
            key = f['target'] if f['type'] in ('person', 'place') else 'unspecified'
            sh[key] += o / dur
    return {k: min(1.0, v) for k, v in sh.items()}


def items(d):
    words, acts, focus = load(d)
    people = d['people']
    out = []
    for k, a in enumerate(acts):
        if a['addressee'] is None:
            continue
        toks, q = text(words, a)
        if not toks:
            continue
        others = [p for p in people if p != a['spk']]
        prev = next((b for b in reversed(acts[:k]) if b['spk'] != a['spk'] and b['t1'] <= a['t0'] + 0.5), None)
        nxt = next((b for b in acts[k + 1:] if b['spk'] != a['spk'] and b['t0'] >= a['t0']), None)
        prev_q = prev is not None and text(words, prev)[1]
        sh = focus_shares(focus, a['spk'], a['t0'], a['t1'], people)
        short = len(toks) <= 3 and all(t in REPLY for t in toks)
        out.append({
            'meeting': d['meeting'], 'id': a['id'], 'spk': a['spk'], 'type': a['type'], 'label': a['addressee'],
            'others': others, 'n': len(toks),
            'w': {'q': float(q), 'you': float(any(t in YOU for t in toks)), 'we': float(any(t in WE for t in toks)),
                  'loglen': math.log(1 + len(toks)), 'short': float(short), 'prev_q': float(prev_q)},
            'cand_w': {c: {'prev': float(prev is not None and prev['spk'] == c), 'next': float(nxt is not None and nxt['spk'] == c),
                           'asked': float(prev is not None and prev['spk'] == c and prev_q)} for c in others},
            'f': {'person_total': sum(sh.get(c, 0) for c in others), 'n_people': float(sum(sh.get(c, 0) > 0.1 for c in others)),
                  **{p: sh.get(p, 0.0) for p in PLACES}, 'unspecified': sh.get('unspecified', 0.0),
                  'max_person': max([sh.get(c, 0) for c in others] or [0])},
            'cand_f': {c: {'look': sh.get(c, 0.0), 'look_most': float(sh.get(c, 0) > 0 and sh.get(c, 0) == max(sh.get(o, 0) for o in others))}
                       for c in others},
            'prev_spk': prev['spk'] if prev else None, 'next_spk': nxt['spk'] if nxt else None,
            'look_major': max(others, key=lambda c: sh.get(c, 0)) if others and max(sh.get(c, 0) for c in others) > 0.5 else None})
    return out


# ---- rules ---------------------------------------------------------------------------------------------------------
def rule_words(x):
    if x['w']['q'] and x['next_spk']:
        return x['next_spk']
    if x['w']['short'] and x['prev_spk']:
        return x['prev_spk']
    return 'group'


def rule_facing(x):
    return x['look_major'] or 'group'


def rule_both(x):
    return x['look_major'] or rule_words(x)


# ---- learned -------------------------------------------------------------------------------------------------------
def act_vec(x, which):
    v = []
    if which in ('words', 'both'):
        v += list(x['w'].values()) + [max(c['prev'] for c in x['cand_w'].values()), max(c['next'] for c in x['cand_w'].values())]
    if which in ('facing', 'both'):
        v += list(x['f'].values())
    return v


def cand_vec(x, c, which):
    v = []
    if which in ('words', 'both'):
        v += list(x['cand_w'][c].values()) + [x['w']['q'] * x['cand_w'][c]['next'], x['w']['short'] * x['cand_w'][c]['prev']]
    if which in ('facing', 'both'):
        v += list(x['cand_f'][c].values())
    return v


def learned(train, test, which):
    X1 = np.array([act_vec(x, which) for x in train]); y1 = np.array([x['label'] == 'group' for x in train])
    m1 = LogisticRegression(max_iter=2000, class_weight='balanced').fit(X1, y1)
    ind = [x for x in train if x['label'] != 'group']
    X2 = np.array([cand_vec(x, c, which) for x in ind for c in x['others']])
    y2 = np.array([c == x['label'] for x in ind for c in x['others']])
    m2 = LogisticRegression(max_iter=2000).fit(X2, y2)
    out = []
    for x in test:
        g = m1.predict_proba(np.array([act_vec(x, which)]))[0][list(m1.classes_).index(True)]
        sc = m2.predict_proba(np.array([cand_vec(x, c, which) for c in x['others']]))[:, list(m2.classes_).index(True)]
        person = x['others'][int(np.argmax(sc))]
        out.append(('group' if g >= 0.5 else person, person))
    return out


def score(xs, preds, person_preds=None):
    n = len(xs)
    g = [i for i, x in enumerate(xs) if x['label'] == 'group']
    o = [i for i, x in enumerate(xs) if x['label'] != 'group']
    res = {'acts': n, 'accuracy_pct': round(100 * sum(preds[i] == xs[i]['label'] for i in range(n)) / n, 1),
           'group_recall_pct': round(100 * sum(preds[i] == 'group' for i in g) / len(g), 1) if g else None,
           'one_person_exact_pct': round(100 * sum(preds[i] == xs[i]['label'] for i in o) / len(o), 1) if o else None,
           'group_vs_one_pct': round(100 * sum((preds[i] == 'group') == (xs[i]['label'] == 'group') for i in range(n)) / n, 1)}
    if g and o:
        res['macro_pct'] = round((res['group_recall_pct'] + res['one_person_exact_pct']) / 2, 1)
    if person_preds is not None and o:
        res['which_person_given_one_pct'] = round(100 * sum(person_preds[i] == xs[i]['label'] for i in o) / len(o), 1)
    return res


def main():
    src, outp = Path(sys.argv[1]), Path(sys.argv[2])
    meets = []
    for f in sorted(src.glob('*.json')):
        d = json.loads(f.read_text())
        if any(a['addressee'] for a in d['dacts']) and d['focus']:
            meets.append(d)
    X = [x for d in meets for x in items(d)]
    unscored = sum(1 for d in meets for a in d['dacts'] if a['addressee'] is None)
    by_m = defaultdict(list)
    for x in X:
        by_m[x['meeting']].append(x)
    res = {'meetings': sorted(by_m), 'acts_scored': len(X), 'acts_without_addressee_label': unscored,
           'labels': dict(Counter('group' if x['label'] == 'group' else 'one person' for x in X)),
           'people_per_meeting': {m: len(d['people']) for m, d in ((d['meeting'], d) for d in meets)}}
    # chance
    o = [x for x in X if x['label'] != 'group']
    res['chance'] = {'always group': score(X, ['group'] * len(X)),
                     'one person, uniform pick among the others (expected)': round(100 * sum(1 / len(x['others']) for x in o) / len(o), 1),
                     'one person, previous speaker': round(100 * sum(x['prev_spk'] == x['label'] for x in o) / len(o), 1),
                     'one person, next speaker': round(100 * sum(x['next_spk'] == x['label'] for x in o) / len(o), 1)}
    # rules
    res['rules'] = {}
    for name, fn in (('words', rule_words), ('facing', rule_facing), ('both', rule_both)):
        res['rules'][name] = score(X, [fn(x) for x in X])
    # learned, leave one meeting out
    res['learned'] = {}
    for which in ('words', 'facing', 'both'):
        preds, persons = [None] * len(X), [None] * len(X)
        idx = {id(x): i for i, x in enumerate(X)}
        for m in by_m:
            train = [x for x in X if x['meeting'] != m]
            test = by_m[m]
            for x, (p, q) in zip(test, learned(train, test, which)):
                preds[idx[id(x)]], persons[idx[id(x)]] = p, q
        res['learned'][which] = score(X, preds, persons)
        res['learned'][which]['by_meeting'] = {m: score(by_m[m], [preds[idx[id(x)]] for x in by_m[m]], [persons[idx[id(x)]] for x in by_m[m]]) for m in by_m}
        res['learned'][which]['_preds'] = {m: ([preds[idx[id(x)]] for x in by_m[m]], [persons[idx[id(x)]] for x in by_m[m]]) for m in by_m}
    # does facing add once the words are known? both - words, resampling meetings (2000 draws), 95% interval
    rng = random.Random(18)
    ms = sorted(by_m)
    def stat(sample, which, key):
        xs = [x for m in sample for x in by_m[m]]
        pr = {k: [] for k in ('p', 'q')}
        for m in sample:
            bm = res['learned'][which]['_preds'][m]
            pr['p'] += bm[0]; pr['q'] += bm[1]
        return score(xs, pr['p'], pr['q'])[key]
    res['facing_adds'] = {}
    for key in ('accuracy_pct', 'macro_pct', 'one_person_exact_pct', 'which_person_given_one_pct', 'group_vs_one_pct'):
        d0 = stat(ms, 'both', key) - stat(ms, 'words', key)
        draws = []
        for _ in range(2000):
            smp = [rng.choice(ms) for _ in ms]
            draws.append(stat(smp, 'both', key) - stat(smp, 'words', key))
        draws.sort()
        res['facing_adds'][key] = {'both_minus_words': round(d0, 1), 'ci95': [round(draws[50], 1), round(draws[1949], 1)],
                                   'meetings_where_both_beats_words': sum(stat([m], 'both', key) > stat([m], 'words', key) for m in ms)}
    for which in res['learned']:
        res['learned'][which].pop('_preds', None)
    # how often the words name someone: AMI participants rarely address each other by name
    res['by_type'] = {}
    for typ, n in Counter(x['type'] for x in X).most_common(8):
        sub = [x for x in X if x['type'] == typ]
        res['by_type'][typ] = {'acts': n, 'group_pct': round(100 * sum(x['label'] == 'group' for x in sub) / n, 1)}
    Path(outp).write_text(json.dumps(res, indent=1))
    print(json.dumps({k: res[k] for k in ('acts_scored', 'labels', 'chance', 'rules')}, indent=1))
    print(json.dumps({k: {kk: vv for kk, vv in v.items() if kk != 'by_meeting'} for k, v in res['learned'].items()}, indent=1))
    print(json.dumps(res['facing_adds'], indent=1))


if __name__ == '__main__':
    main()
