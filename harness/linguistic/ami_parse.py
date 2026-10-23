#!/usr/bin/env python3
"""AMI's manual annotations (ami_public_manual_1.6.2.zip, https://groups.inf.ed.ac.uk/ami/download/) into one JSON
per meeting, for brief 18.

Per meeting:
  words     every spoken word in time order: {i, spk (the NXT agent letter A-D), t0, t1, w}. Punctuation tokens are
            kept as the `punc` flag on the word before them (a recogniser can emit '?'); vocal sounds and gaps are
            dropped. Words without times are dropped, and counted.
  segments  each speaker's transcribed speech segments: {spk, t0, t1, w0, w1} (word index range)
  dacts     dialogue acts: {id, spk, type (AMI's gloss), w0, w1 (word index range), t0, t1, addressee (None when not
            annotated; else 'group' when it lists every other participant, or the one agent letter)}
  pairs     adjacency pairs (source dact id -> target dact id), when annotated
  focus     focus of attention per participant, when annotated: {spk, t0, t1, type: person/place/unspecified,
            target (agent letter or place)}
  people    the meeting's agent letters (one per words file)
usage: ami_parse.py <manual annotations dir> <out dir> [meeting ...]     (no meetings: every meeting with words)
"""
import json
import re
import sys
import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path

NITE = '{http://nite.sourceforge.net/}'
HREF = re.compile(r'#id\(([^)]+)\)(?:\.\.id\(([^)]+)\))?')


def da_types(root):
    out = {}
    for el in ET.parse(root / 'ontologies' / 'da-types.xml').iter():
        i, g = el.get(NITE + 'id'), el.get('gloss')
        if i and g:
            out[i] = g
    return out


def parse(root, mid, types, people):
    words, id_ix = [], {}
    dropped = 0
    for f in sorted((root / 'words').glob(f'{mid}.*.words.xml')):
        spk = f.name.split('.')[1]
        for el in ET.parse(f).getroot():
            tag = el.tag.split('}')[-1]
            wid = el.get(NITE + 'id')
            if tag != 'w':
                id_ix[wid] = ('skip', spk, None)
                continue
            if el.get('punc') == 'true':
                id_ix[wid] = ('punc', spk, el.text)
                continue
            t0, t1 = el.get('starttime'), el.get('endtime')
            if t0 is None or t1 is None:
                dropped += 1
                id_ix[wid] = ('skip', spk, None)
                continue
            words.append({'spk': spk, 't0': float(t0), 't1': float(t1), 'w': (el.text or '').strip(), 'punc': '', 'id': wid})
            id_ix[wid] = ('w', spk, len(words) - 1)
    # punctuation onto the word before it, per speaker file order
    for f in sorted((root / 'words').glob(f'{mid}.*.words.xml')):
        last = None
        for el in ET.parse(f).getroot():
            k = id_ix.get(el.get(NITE + 'id'))
            if not k:
                continue
            if k[0] == 'w':
                last = k[2]
            elif k[0] == 'punc' and last is not None:
                words[last]['punc'] += k[2] or ''
    order = sorted(range(len(words)), key=lambda i: (words[i]['t0'], words[i]['t1'], words[i]['spk']))
    new_of = {old: new for new, old in enumerate(order)}
    words = [words[i] for i in order]
    for i, w in enumerate(words):
        w['i'] = i
    file_words = defaultdict(list)                       # per speaker, the words' ids in file order, to resolve ranges
    for f in sorted((root / 'words').glob(f'{mid}.*.words.xml')):
        for el in ET.parse(f).getroot():
            file_words[f.name].append(el.get(NITE + 'id'))
    pos = {fn: {wid: k for k, wid in enumerate(ids)} for fn, ids in file_words.items()}

    def span(href):
        """word indices (new order) covered by an NXT child href, skipping punctuation and vocal sounds."""
        fn = href.split('#')[0]
        m = HREF.search(href)
        if not m or fn not in pos:
            return []
        a = pos[fn].get(m.group(1)); b = pos[fn].get(m.group(2) or m.group(1))
        if a is None or b is None:
            return []
        out = []
        for wid in file_words[fn][a:b + 1]:
            k = id_ix.get(wid)
            if k and k[0] == 'w':
                out.append(new_of[k[2]])
        return out

    segs = []
    for f in sorted((root / 'segments').glob(f'{mid}.*.segments.xml')):
        spk = f.name.split('.')[1]
        for el in ET.parse(f).getroot():
            ix = [i for c in el if c.tag == NITE + 'child' for i in span(c.get('href'))]
            t0, t1 = el.get('transcriber_start'), el.get('transcriber_end')
            if ix and t0 and t1:
                segs.append({'spk': spk, 't0': float(t0), 't1': float(t1), 'w0': min(ix), 'w1': max(ix)})
    others = sorted(people)
    dacts = []
    for f in sorted((root / 'dialogueActs').glob(f'{mid}.*.dialog-act.xml')):
        spk = f.name.split('.')[1]
        if len(spk) != 1:
            continue
        for el in ET.parse(f).getroot():
            ix = [i for c in el if c.tag == NITE + 'child' for i in span(c.get('href'))]
            if not ix:
                continue
            typ = None
            for c in el:
                if c.tag == NITE + 'pointer' and c.get('role') == 'da-aspect':
                    m = HREF.search(c.get('href'))
                    typ = types.get(m.group(1)) if m else None
            ad = el.get('addressee')
            if ad is not None:
                lst = sorted(a.strip() for a in ad.split(',') if a.strip())
                rest = [a for a in others if a != spk]
                ad = 'group' if (len(lst) > 1 or (rest and lst == rest and len(rest) > 1)) else (lst[0] if lst else None)
            dacts.append({'id': el.get(NITE + 'id'), 'spk': spk, 'type': typ, 'w0': min(ix), 'w1': max(ix),
                          't0': words[min(ix)]['t0'], 't1': words[max(ix)]['t1'], 'addressee': ad,
                          'addressee_raw': el.get('addressee')})
    dacts.sort(key=lambda d: (d['t0'], d['t1']))
    pairs = []
    ap = root / 'dialogueActs' / f'{mid}.adjacency-pairs.xml'
    if ap.exists():
        for el in ET.parse(ap).getroot():
            src = tgt = None
            for c in el:
                if c.tag == NITE + 'pointer':
                    m = re.search(r'#id\(([^)]+)\)', c.get('href') or '')
                    if m and c.get('role') == 'source': src = m.group(1)
                    if m and c.get('role') == 'target': tgt = m.group(1)
            if src and tgt:
                pairs.append([src, tgt])
    focus = []
    for f in sorted((root / 'focus').glob(f'{mid}.*.foa.xml')):
        spk = f.name.split('.')[1]
        for el in ET.parse(f).getroot():
            typ = el.get('type')
            tgt = el.get('nxt_agent') if typ == 'person' else el.get('place')
            focus.append({'spk': spk, 't0': float(el.get('starttime')), 't1': float(el.get('endtime')), 'type': typ, 'target': tgt})
    return {'meeting': mid, 'people': sorted(people), 'words': words, 'segments': segs,
            'dacts': dacts, 'pairs': pairs, 'focus': focus, 'dropped_untimed_words': dropped}


def main():
    root, out = Path(sys.argv[1]), Path(sys.argv[2])
    out.mkdir(parents=True, exist_ok=True)
    types = da_types(root)
    mids = sys.argv[3:] or sorted({f.name.split('.')[0] for f in (root / 'words').glob('*.words.xml')})
    for mid in mids:
        people = sorted({f.name.split('.')[1] for f in (root / 'words').glob(f'{mid}.*.words.xml')})
        d = parse(root, mid, types, people)
        (out / f'{mid}.json').write_text(json.dumps(d))
        n_ad = sum(x['addressee'] is not None for x in d['dacts'])
        print(f"{mid}: {len(d['people'])} people, {len(d['words'])} words, {len(d['dacts'])} dacts "
              f"({n_ad} with addressee), {len(d['focus'])} focus spans, {len(d['pairs'])} pairs")


if __name__ == '__main__':
    main()
