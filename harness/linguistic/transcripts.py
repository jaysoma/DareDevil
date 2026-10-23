#!/usr/bin/env python3
"""Brief 18 step 1: the words two ways, as AMI wrote them and as a recogniser would hear them, with what they look like.

  full    AMI's manual transcript: every word, in time order, overlapping speakers interleaved word by word.
  recog   overlaps resolved the way a recogniser would: it can't decode two people at once, so in an overlap it keeps
          one talker. A word that overlaps another speaker's word is kept only when its own speech segment is the
          longest of those involved: the "longer talker" of the brief (AMI's manual annotations carry no per-speaker
          level, so "louder" would need the headset audio). The others' overlapped words are dropped.

Every word carries: spk, t (mid time), w, overlapped (it overlapped another speaker's word), short (it sits in a turn
of at most 3 words, all reply words, e.g. "yeah", "mm-hmm"). A turn is a run of one speaker's consecutive words in that
transcript.

Per meeting, also:
  same_next_pct     the share of words whose next word is the same speaker's (Jay: 85-90% in a recogniser's stream)
  third_in_50_pct   the share of 50-word windows (each word's newest 50) that hold more than two speakers
  baseline          everything to the most talkative speaker, whole meeting; and per window (the two-speaker windows
                    blends.py would cut from the true labels, at most 50 words), each window's majority
usage: transcripts.py <meeting json dir> <out dir> [meeting ...]
       writes <out>/<meeting>.<full|recog>.jsonl and <out>/transcripts_summary.json
"""
import bisect
import json
import sys
from collections import Counter
from pathlib import Path

REPLY = {'yeah', 'yes', 'no', 'mm', 'mm-hmm', 'uh-huh', 'okay', 'ok', 'right', 'hmm', 'uh', 'um', 'sure', 'yep', 'nope',
         'alright', 'mm-mm', 'oh', 'ah', 'good', 'cool'}
MAX_WORDS = 50                     # blends.py's window limit


def overlapped_flags(words):
    """For each word, the other speakers' words overlapping it in time (indices)."""
    order = sorted(range(len(words)), key=lambda i: words[i]['t0'])
    starts = [words[i]['t0'] for i in order]
    out = [[] for _ in words]
    for i, w in enumerate(words):
        if w['t1'] <= w['t0']:
            continue
        j = bisect.bisect_left(starts, w['t0'] - 10.0)
        while j < len(order) and starts[j] < w['t1']:
            k = order[j]
            v = words[k]
            if v['spk'] != w['spk'] and v['t1'] > w['t0'] and v['t0'] < w['t1'] and v['t1'] > v['t0']:
                out[i].append(k)
            j += 1
    return out


def turns(seq):
    """Runs of one speaker's consecutive words: [(start, end)] indices into seq."""
    out, s = [], 0
    for i in range(1, len(seq) + 1):
        if i == len(seq) or seq[i]['spk'] != seq[s]['spk']:
            out.append((s, i))
            s = i
    return out


def mark_short(seq):
    for a, b in turns(seq):
        short = (b - a) <= 3 and all(seq[k]['w'].lower().strip('.,?!') in REPLY for k in range(a, b))
        for k in range(a, b):
            seq[k]['short'] = short
    return seq


def build(d):
    words = d['words']
    ov = overlapped_flags(words)
    seg_len = {}
    for s in d['segments']:
        for k in range(s['w0'], s['w1'] + 1):
            if words[k]['spk'] == s['spk']:
                seg_len[k] = s['t1'] - s['t0']
    full = [{'spk': w['spk'], 't': round((w['t0'] + w['t1']) / 2, 3), 'w': w['w'], 'overlapped': bool(ov[i])}
            for i, w in enumerate(words)]
    recog = []
    for i, w in enumerate(words):
        if ov[i]:
            mine = seg_len.get(i, w['t1'] - w['t0'])
            theirs = max(seg_len.get(k, words[k]['t1'] - words[k]['t0']) for k in ov[i])
            if mine < theirs:
                continue                                 # the other talker's words win this overlap
        recog.append(dict(full[i]))
    full.sort(key=lambda x: x['t']); recog.sort(key=lambda x: x['t'])
    return mark_short(full), mark_short(recog)


def windows_two(seq):
    """blends.py's windows on the true labels, tiled through the meeting: from each window's start, the longest
    contiguous stretch with at most two speakers and at most MAX_WORDS words."""
    out, i = [], 0
    while i < len(seq):
        seen, j = [], i
        while j < len(seq) and j - i < MAX_WORDS:
            if seq[j]['spk'] not in seen:
                if len(seen) == 2:
                    break
                seen.append(seq[j]['spk'])
            j += 1
        out.append((i, j))
        i = j
    return out


def stats(seq):
    n = len(seq)
    if n < 2:
        return None
    same = sum(seq[k]['spk'] == seq[k + 1]['spk'] for k in range(n - 1)) / (n - 1)
    third = 0
    for k in range(n):
        if len({x['spk'] for x in seq[max(0, k - MAX_WORDS + 1):k + 1]}) > 2:
            third += 1
    cnt = Counter(x['spk'] for x in seq)
    top = cnt.most_common(1)[0][1] / n
    wins = windows_two(seq)
    per_win = sum(Counter(seq[k]['spk'] for k in range(a, b)).most_common(1)[0][1] for a, b in wins) / n
    return {'words': n, 'speakers': len(cnt), 'overlapped_pct': round(100 * sum(x['overlapped'] for x in seq) / n, 1),
            'short_pct': round(100 * sum(x['short'] for x in seq) / n, 1),
            'same_next_pct': round(100 * same, 1), 'third_in_50_pct': round(100 * third / n, 1),
            'baseline_whole_meeting_pct': round(100 * top, 1), 'baseline_per_window_pct': round(100 * per_win, 1),
            'windows': len(wins), 'mean_window_words': round(n / len(wins), 1)}


def main():
    src, out = Path(sys.argv[1]), Path(sys.argv[2])
    out.mkdir(parents=True, exist_ok=True)
    files = [src / f'{m}.json' for m in sys.argv[3:]] or sorted(src.glob('*.json'))
    summary = {}
    for f in files:
        d = json.loads(f.read_text())
        if len(d['words']) < 200:
            continue
        full, recog = build(d)
        for name, seq in (('full', full), ('recog', recog)):
            with open(out / f"{d['meeting']}.{name}.jsonl", 'w') as fh:
                for x in seq:
                    fh.write(json.dumps(x) + '\n')
        summary[d['meeting']] = {'full': stats(full), 'recog': stats(recog),
                                 'dropped_by_recogniser_pct': round(100 * (1 - len(recog) / len(full)), 1)}
    (out / 'transcripts_summary.json').write_text(json.dumps(summary, indent=1))
    print(len(summary), 'meetings')


if __name__ == '__main__':
    main()
