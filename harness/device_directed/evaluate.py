#!/usr/bin/env python3
"""Score brief 19: hits against false accepts per hour, per method, device and stream type; hard negatives apart.

  positives      the spliced instruction in each instruction window, scored by its own device's detector
  negatives      every stream phrase (not spliced) of every window, scored by that window's device; their duration is
                 their word count at WPM words a minute
  hard negatives the spliced to_person and subject phrases, and the foreign-phrase control (real talk from the other
                 stream), reported apart at the same thresholds
  the curve      every threshold: hit rate and false accepts per hour, per method and device (curves.json)
  operating      the threshold where the device's false accepts per hour first reach 1 and 10 (all its streams
  points         pooled); hit rate per stream type there, and how many hard negatives pass it
  failing        a device and stream type where even the best method finds under half the instructions at 10 false
                 accepts per hour: set aside to study, with examples of the misses
  false accepts  at 10 per hour, catalogued by kind: device vocabulary (a keyword of the device), request shape (opens like
                 a command or a request), question, short (two words or fewer), other

usage: python3 evaluate.py SET_DIR SCORES_DIR OUT_DIR
"""
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

WPM = 150
TARGETS = (1.0, 10.0)
DEVICES = ('car', 'kitchen', 'watch', 'general')
STREAMS = ('ami', 'calls', 'lyrics', 'monologue')
REQUEST = re.compile(r"^(please |hey |ok |okay )?(set|send|text|email|play|turn|remind|call|add|tell|start|book|order|"
                     r"find|show|give|wake|post|dim|make|put|cancel|delete|remove|schedule|get|check|read|open|stop|"
                     r"switch|create|look|search|can you|could you|would you|will you|i want|i need|i'd like)\b")


def words(t):
    return max(1, len(t.split()))


def load(setd, scored):
    rows = {r['id']: r for r in map(json.loads, open(setd / 'set.jsonl'))}
    methods = {}
    for p in sorted(scored.glob('scores_*.jsonl')):
        m = p.stem.replace('scores_', '')
        methods[m] = {q['id']: q for q in map(json.loads, open(p))}
    return rows, methods


def split(rows, sc):
    """Per device: positives (score, stream, window id), negatives (score, words, stream, text, window id), hard."""
    pos, neg, hard = defaultdict(list), defaultdict(list), defaultdict(list)
    for wid, r in rows.items():
        s = sc[wid]['scores']
        d = r['device']
        for i, p in enumerate(r['phrases']):
            if p['label'] == 'instruction':
                pos[d].append((s[i], r['stream'], wid, p['text']))
            elif p['label'] == 'hard_negative':
                hard[d].append((s[i], p['hard'], r['stream'], wid, p['text']))
            else:
                neg[d].append((s[i], words(p['text']), r['stream'], wid, p['text']))
    return pos, neg, hard


def curve(pos, neg):
    """Hit rate and false accepts per hour at every distinct threshold (accept when score >= threshold)."""
    hours = sum(w for _, w, *_ in neg) / WPM / 60
    ps = np.sort(np.array([x[0] for x in pos]))
    ns = np.sort(np.array([x[0] for x in neg]))
    th = np.unique(np.concatenate([ps, ns]))[::-1]
    hit = 1 - np.searchsorted(ps, th, side='left') / len(ps)
    fa = (len(ns) - np.searchsorted(ns, th, side='left')) / hours
    return th, hit, fa, hours


def at_fa(th, hit, fa, target):
    """The lowest threshold whose false accepts per hour stay at or under the target."""
    ok = np.where(fa <= target)[0]
    if not len(ok):
        return None
    i = ok[-1]
    return float(th[i]), float(hit[i]), float(fa[i])


def auc_fa(hit, fa, max_fa=60.0):
    """Mean hit rate over 0..max_fa false accepts per hour: the area under the curve, normalised."""
    o = np.argsort(fa)
    x, y = np.concatenate([[0], fa[o]]), np.concatenate([[0], np.maximum.accumulate(hit[o])])
    keep = x <= max_fa
    x, y = np.append(x[keep], max_fa), np.append(y[keep], y[keep][-1])
    return float(np.trapezoid(y, x) / max_fa)


def kind(text, kw):
    t = text.lower().strip()
    w = re.findall(r"[a-z']+", t)
    if len(w) <= 2:
        return 'short'
    if set(w) & kw:
        return 'device vocabulary'
    if REQUEST.match(t):
        return 'request shape'
    if t.endswith('?'):
        return 'question'
    return 'other'


def main():
    setd, scored, out = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
    out.mkdir(parents=True, exist_ok=True)
    rows, methods = load(setd, scored)
    kw = {d: set(v) for d, v in json.load(open(scored / 'keywords.json')).items()}
    summary, curves = {'methods': sorted(methods)}, {}
    best_cell = defaultdict(dict)
    catalogue = {}
    for m, sc in methods.items():
        if set(sc) != set(rows):
            print(f'skip {m}: scored {len(sc)} of {len(rows)} windows')
            continue
        pos, neg, hard = split(rows, sc)
        res = {}
        for d in DEVICES + ('all',):
            P = [x for dd in DEVICES for x in pos[dd]] if d == 'all' else pos[d]
            N = [x for dd in DEVICES for x in neg[dd]] if d == 'all' else neg[d]
            H = [x for dd in DEVICES for x in hard[dd]] if d == 'all' else hard[d]
            th, hit, fa, hours = curve(P, N)
            curves[f'{m}|{d}'] = {'threshold': th.tolist()[::max(1, len(th) // 400)],
                                  'hit': hit.tolist()[::max(1, len(th) // 400)], 'fa_per_hour': fa.tolist()[::max(1, len(th) // 400)]}
            r = {'positives': len(P), 'negative_hours': round(hours, 2), 'auc_0_60fa': round(auc_fa(hit, fa), 3)}
            for tgt in TARGETS:
                op = at_fa(th, hit, fa, tgt)
                key = f'at_{int(tgt)}fa'
                if op is None:
                    r[key] = None
                    continue
                t, h, f = op
                by_stream = {}
                for s in STREAMS:
                    ps = [x for x in P if x[1] == s]
                    ns = [x for x in N if x[2] == s]
                    hs = sum(w for _, w, *_ in ns) / WPM / 60
                    by_stream[s] = {'hit_pct': round(100 * np.mean([x[0] >= t for x in ps]), 1) if ps else None,
                                    'fa_per_hour': round(sum(x[0] >= t for x in ns) / hs, 1) if hs else None}
                hard_k = {k: round(100 * np.mean([x[0] >= t for x in H if x[1] == k]), 1)
                          for k in ('to_person', 'subject', 'foreign') if any(x[1] == k for x in H)}
                r[key] = {'threshold': round(t, 5), 'hit_pct': round(100 * h, 1), 'fa_per_hour': round(f, 2),
                          'by_stream': by_stream, 'hard_accept_pct': hard_k}
                if d != 'all' and tgt == 10.0:
                    for s in STREAMS:
                        v = by_stream[s]['hit_pct']
                        if v is not None and v > best_cell[(d, s)].get('hit', -1):
                            best_cell[(d, s)] = {'hit': v, 'method': m, 'threshold': t}
                    fas = [x for x in N if x[0] >= t]
                    catalogue[f'{m}|{d}'] = {
                        'false_accepts': len(fas),
                        'kinds': dict(Counter(kind(x[4], kw[d]) for x in fas).most_common()),
                        'by_stream': dict(Counter(x[2] for x in fas)),
                        'examples': [{'window': x[3], 'stream': x[2], 'text': x[4]} for x in sorted(fas, key=lambda x: -x[0])[:8]],
                        'hard_accepted': [{'window': x[3], 'kind': x[1], 'text': x[4]} for x in H if x[0] >= t][:8]}
            res[d] = r
        # the general model's own answer: its most likely line, if not "none"
        if m.startswith('llm_'):
            dec = {'hit': 0, 'pos': 0, 'fa': 0, 'neg_words': 0, 'hard': Counter(), 'hard_n': Counter()}
            for wid, r in rows.items():
                q = sc[wid]
                s = np.array(q['scores'])
                pick = int(np.argmax(s)) if s.max() > q['none'] else None
                for i, p in enumerate(r['phrases']):
                    if p['label'] == 'instruction':
                        dec['pos'] += 1; dec['hit'] += pick == i
                    elif p['label'] == 'hard_negative':
                        dec['hard_n'][p['hard']] += 1; dec['hard'][p['hard']] += pick == i
                    else:
                        dec['neg_words'] += words(p['text']); dec['fa'] += pick == i
            res['own_answer'] = {'hit_pct': round(100 * dec['hit'] / dec['pos'], 1),
                                 'fa_per_hour': round(dec['fa'] / (dec['neg_words'] / WPM / 60), 2),
                                 'hard_accept_pct': {k: round(100 * dec['hard'][k] / dec['hard_n'][k], 1) for k in dec['hard_n']}}
        summary[m] = res
    failing = {}
    for d in DEVICES:
        for s in STREAMS:
            b = best_cell.get((d, s))
            if b and b['hit'] < 50:
                misses = [r['phrases'][r['pos']]['text'] for r in rows.values()
                          if r['kind'] == 'instruction' and r['device'] == d and r['stream'] == s][:6]
                failing[f'{d} {s}'] = {'best_method': b['method'], 'best_hit_pct': b['hit'], 'instructions': misses}
    summary['failing_conditions'] = failing
    summary['best_by_cell_at_10fa'] = {f'{d} {s}': v for (d, s), v in best_cell.items()}
    (out / 'summary.json').write_text(json.dumps(summary, indent=1))
    (out / 'curves.json').write_text(json.dumps(curves))
    (out / 'false_accepts.json').write_text(json.dumps(catalogue, indent=1))
    print(json.dumps({m: {d: (v[d]['at_10fa'] or {}).get('hit_pct') for d in DEVICES + ('all',)}
                      for m, v in summary.items() if isinstance(v, dict) and 'all' in v}, indent=1))


if __name__ == '__main__':
    main()
