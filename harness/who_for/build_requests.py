#!/usr/bin/env python3
"""Brief 22, steps 1 and 3: real requests to a person, where they were said, and car instructions in real calls.

Source: the Switchboard Dialog Act Corpus (github.com/cgpotts/swda), the telephone calls brief 19 streamed, with each
sub-utterance's DAMSL dialogue-act tag. A dialogue act is a tagged sub-utterance plus the sub-utterances the same caller
continues it with ('+'). The real requests, all said by one caller to the other:
  directive   tagged ad (action-directive): "you might try ...", "hold it down a little longer"
  ask         a yes/no question (qy...) that is a request: it opens with can / could / would / will you, or
              do you want to
  commit      tagged co, cc or oo (commit, offer): "I'll ...", the kind brief 19's to_person templates imitated
Only acts of at least MIN_WORDS words (in a recogniser's form) are kept.

Windows, in brief 19's form: WINDOW + 1 phrases, the stream segmented as brief 19's calls() segments it (one phrase per
caller utterance), the target at a random position 5..25 away from the edges.
  inplace   the request where it was said: its call around it, its own utterance split into [before, request, after]
            so the request is a phrase of its own and nothing is moved
  spliced   the same words spliced into a different call, brief 19's way (inside caller A's turn): as foreign to the
            talk around them as brief 19's generated to_person phrases were
  car       (step 3) every SLURP test-split car instruction spliced into a call, brief 19's way, one per window
Every window is scored for every device (score_who.py); the same text, two places.

usage: build_requests.py SOURCES_DIR OUT_DIR  ->  OUT_DIR/requests.jsonl (windows), OUT_DIR/requests_index.jsonl (no
text: conversation, act index, tags, kind, position; the recipe that is committed)
"""
import csv
import io
import json
import random
import re
import sys
import zipfile
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'device_directed'))
import build_set as B                                                          # noqa: E402
import methods as M                                                            # noqa: E402

SEED = 22
WINDOW = B.WINDOW
MIN_WORDS = 3
ASK = re.compile(r'^(can|could|would|will) you\b|^do you want to\b')


def clean(t):
    return re.sub(r'\s+', ' ', B.SWDA_JUNK.sub(' ', t)).strip(' ,')


def calls_with_acts(src):
    """Per call: brief 19's phrases (one per caller utterance) and the dialogue acts inside them."""
    z = zipfile.ZipFile(src / 'swda' / 'swda.zip')
    out = {}
    for n in sorted(z.namelist()):
        if not n.endswith('.utt.csv') or '__MACOSX' in n:
            continue
        rows = list(csv.DictReader(io.TextIOWrapper(z.open(n), encoding='utf-8')))
        utts, acts = [], []
        cur, key, last_act = [], None, {}
        for r in rows:
            k = (r['caller'], r['utterance_index'])
            if k != key and cur:
                utts.append({'caller': key[0], 'parts': cur})
                cur = []
            key = k
            t = clean(r['text'])
            tag = r['act_tag']
            if tag.startswith('+') and r['caller'] in last_act:
                a = last_act[r['caller']]
                if t:
                    a['parts'].append((len(utts), len(cur)))
            else:
                a = {'tag': tag, 'caller': r['caller'], 'parts': [(len(utts), len(cur))] if t else []}
                acts.append(a)
                last_act[r['caller']] = a
            if t:
                cur.append(t)
        if cur:
            utts.append({'caller': key[0], 'parts': cur})
        out[Path(n).stem.replace('.utt', '')] = (utts, acts)
    return out


def kind_of(tag, text):
    t0 = tag.split('^')[0].split('(')[0].split('@')[0].split(',')[0].rstrip('*')
    if t0 == 'ad':
        return 'directive'
    if t0 == 'qy' and ASK.match(M.asr(text)):
        return 'ask'
    if t0 in ('co', 'cc', 'oo'):
        return 'commit'
    return None


def main():
    src, out = Path(sys.argv[1]), Path(sys.argv[2])
    out.mkdir(parents=True, exist_ok=True)
    rng = random.Random(SEED)
    calls = calls_with_acts(src)
    # brief 19's own segmentation of the same calls, for the spliced windows
    stream = B.calls(src)
    reqs = []
    for cid, (utts, acts) in calls.items():
        for ai, a in enumerate(acts):
            if not a['parts']:
                continue
            us = sorted({u for u, _ in a['parts']})
            if len(us) != 1:                         # an act spread over several utterances: keep acts inside one
                continue
            u = us[0]
            idx = [p for uu, p in a['parts']]
            text = ' '.join(utts[u]['parts'][p] for p in idx)
            k = kind_of(a['tag'], text)
            if k and len(M.asr(text).split()) >= MIN_WORDS:
                reqs.append({'call': cid, 'act': ai, 'tag': a['tag'], 'kind': k, 'caller': a['caller'], 'utt': u,
                             'idx': idx, 'text': text})
    windows, index = [], []
    for n, q in enumerate(reqs):
        utts, _ = calls[q['call']]
        # the host utterance split into before / request / after, so the request is a phrase of its own, in place
        parts = utts[q['utt']]['parts']
        before = ' '.join(p for i, p in enumerate(parts) if i < min(q['idx']))
        after = ' '.join(p for i, p in enumerate(parts) if i > max(q['idx']))
        seq = [{'text': ' '.join(x['parts']), 'caller': x['caller']} for x in utts]
        host = [{'text': before, 'caller': q['caller']}] if before else []
        host += [{'text': q['text'], 'caller': q['caller'], 'label': 'real_request', 'kind': q['kind'], 'tag': q['tag']}]
        host += [{'text': after, 'caller': q['caller']}] if after else []
        seq = seq[:q['utt']] + host + seq[q['utt'] + 1:]
        target = host[len(host) - (2 if after else 1)]
        seq = [p for p in seq if p is target or M.asr(p['text'])]      # as brief 19's calls(): no empty phrases
        tpos = next(i for i, p in enumerate(seq) if p is target)
        if len(seq) < WINDOW + 1:
            continue
        pos = rng.randrange(5, WINDOW - 5)
        a = tpos - pos
        if a < 0 or a + WINDOW + 1 > len(seq):           # too near the call's start or end: centre it as far as it goes
            a = min(max(0, tpos - pos), len(seq) - WINDOW - 1)
            pos = tpos - a
            if not 3 <= pos <= WINDOW - 3:
                continue
        w = [dict(p) for p in seq[a:a + WINDOW + 1]]
        for p in w:
            p.setdefault('label', 'stream')
        wid = f'r{n:04d}'
        windows.append({'id': wid + 'i', 'set': 'inplace', 'kind': q['kind'], 'call': q['call'], 'pos': pos,
                        'phrases': w})
        # the same words in a different call, brief 19's splice
        others = [k for k in stream if k != q['call'] and len(stream[k]) >= WINDOW]
        k = rng.choice(others)
        st = rng.randrange(0, len(stream[k]) - WINDOW + 1)
        sw = [dict(p, label='stream') for p in stream[k][st:st + WINDOW]]
        cand = [i for i in range(5, WINDOW - 5) if sw[i - 1].get('caller') == 'A'] or list(range(5, WINDOW - 5))
        sp = rng.choice(cand)
        sw.insert(sp, {'text': q['text'], 'caller': 'A', 'label': 'real_request', 'kind': q['kind'], 'tag': q['tag']})
        windows.append({'id': wid + 's', 'set': 'spliced', 'kind': q['kind'], 'call': k, 'pos': sp, 'phrases': sw})
        index.append({'id': wid, 'call': q['call'], 'act_index': q['act'], 'tag': q['tag'], 'kind': q['kind'],
                      'inplace_pos': pos, 'spliced_into': k, 'spliced_start': st, 'spliced_pos': sp})
    # step 3: every SLURP test-split car instruction spliced into a call, brief 19's way
    ins = B.instructions(src)
    for n, c in enumerate(ins['test']['car']):
        k = rng.choice([k for k in stream if len(stream[k]) >= WINDOW])
        st = rng.randrange(0, len(stream[k]) - WINDOW + 1)
        sw = [dict(p, label='stream') for p in stream[k][st:st + WINDOW]]
        cand = [i for i in range(5, WINDOW - 5) if sw[i - 1].get('caller') == 'A'] or list(range(5, WINDOW - 5))
        sp = rng.choice(cand)
        sw.insert(sp, {'text': c['text'], 'caller': 'A', 'label': 'instruction', 'slurp_id': c['slurp_id']})
        windows.append({'id': f'c{n:04d}', 'set': 'car_in_calls', 'kind': 'instruction', 'call': k, 'pos': sp,
                        'phrases': sw})
        index.append({'id': f'c{n:04d}', 'slurp_id': c['slurp_id'], 'call': k, 'start': st, 'pos': sp})
    with open(out / 'requests.jsonl', 'w') as fh:
        for w in windows:
            fh.write(json.dumps(w) + '\n')
    with open(out / 'requests_index.jsonl', 'w') as fh:
        for r in index:
            fh.write(json.dumps(r) + '\n')
    print(json.dumps({'requests_found': Counter(q['kind'] for q in reqs),
                      'windows': Counter((w['set'], w['kind']) for w in windows).most_common()}, default=str))


if __name__ == '__main__':
    main()
