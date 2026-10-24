#!/usr/bin/env python3
"""Brief B2: keep the callouts that come after the turn (2026-10-24).

Jay: "If I spoke in the past tense, then I had already rotated." Each stop's opening callout (the decode segment that
starts nearest the stop's start, among those over it) is tagged from its text:
    after          past tense or present state ("Rotated 90 degrees", "I am now facing away", "Facing phone again")
    before/during  future or in progress ("I'm going to rotate", "rotating")
    unclear        garbled, or the bare "Rotate 90 degrees": Whisper drops the -d of "Rotated" before "ninety", so it
                   could be either
Three rules for a stop's speech: all (as labelled), dropped (brief B: from announcement_end on), tense (keep `after`
callouts, drop the rest as brief B does; `unclear` ones are counted). Jay settled the six unclear ones as `after`
(2026-10-24: "Rotated means AFTER rotated"; 213304's "Rout 90 degrees" too), so tense now equals all. Every rule skips
each tape's first HANDLING_S (facing_pooled.py), the handling of the phone. Scored brief B's way (blur.score). Writes
harness/rotation/blur/callout_tense.json, results/rotation/blur/tense.txt and tense.json.
"""
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent))
from blur import REPO, SET_ASIDE, Tape, announcement_end, cdr_measures, onset_measures, score  # noqa: E402
from facing_pooled import HANDLING_S  # noqa: E402

OUT = REPO / 'results/rotation/blur'
KEYS = ('CDR hi - lo', 'CDR range stat', 'onset tilt 40')
TAGS = {  # (walk, stop start): tag, why. Read from tapes/<walk>/transcript.json (Whisper).
    ('walk-231921', 7): ('after', 'present state; the walk opens here'),
    ('walk-231921', 29): ('after', '"Rotate[d]": Jay, Rotated means after'),
    ('walk-231921', 47): ('after', '"Racing away" = facing away, present state'),
    ('walk-231921', 78): ('after', 'past tense'),
    ('walk-231921', 98): ('after', 'past tense'),
    ('walk-231921', 122): ('after', 'present state'),
    ('walk-231705', 0): ('after', 'present state; the walk opens here'),
    ('walk-231705', 22): ('after', 'past tense'),
    ('walk-231705', 36): ('after', 'present state'),
    ('walk-231705', 63): ('after', 'past tense'),
    ('walk-231705', 84): ('after', 'past tense'),
    ('walk-125621', 18): ('after', 'present state, repeated'),
    ('walk-125621', 25): ('after', 'present state, repeated'),
    ('walk-125621', 37): ('after', 'present state'),
    ('walk-125621', 45): ('after', 'present state; a walk, not a turn, before it'),
    ('walk-125621', 58): ('after', 'state ("90 degrees, clockwise"), repeated'),
    ('walk-125621', 66): ('after', '"Pacing away" = facing away, present state'),
    ('walk-171645', 3): ('after', 'present state; the walk opens here'),
    ('walk-171645', 7): ('after', '"Rotate[d]": Jay, Rotated means after'),
    ('walk-171645', 13): ('after', '"Rotate[d]", then "facing away from the phone": Jay, Rotated means after'),
    ('walk-171645', 20): ('after', '"Rotate[d]": Jay, Rotated means after'),
    ('walk-171645', 30): ('after', 'past tense ("I just faced the phone")'),
    ('walk-215800', 0): ('after', 'present state; the walk opens here'),
    ('walk-215800', 10): ('after', 'past tense'),
    ('walk-215800', 16): ('after', 'past tense'),
    ('walk-215800', 22): ('after', 'past tense'),
    ('walk-215800', 26): ('after', '"Rotate[d]", as the walk\'s other three: Jay, Rotated means after'),
    ('walk-122038', 10): ('after', 'present state'),
    ('walk-122038', 16): ('after', 'present state'),
    ('walk-122038', 23): ('after', 'present state'),
    ('walk-122038', 27): ('after', 'present state'),
    ('walk-030615', 4): ('after', 'present state; the walk opens here'),
    ('walk-030615', 34): ('after', 'present state'),
    ('walk-030615', 73): ('after', '"I\'m not rotated" = I\'m now rotated, past participle'),
    ('walk-030615', 106): ('after', 'present state'),
    ('walk-030615', 123): ('after', 'present state'),
    ('walk-224302', 35): ('after', 'present state'),
    ('walk-224302', 78): ('after', 'past tense'),
    ('walk-213304', 251): ('after', '"Walk forward, facing": a walk, facing the phone throughout'),
    ('walk-213304', 269): ('after', 'past tense, and "I called it after I rotated"'),
    ('walk-213304', 291): ('after', '"basing away" = facing away, present state'),
    ('walk-213304', 312): ('after', '"Notated" = rotated, past tense'),
    ('walk-213304', 337): ('after', '"Rout 90 degrees" = rotated, said after the turn (Jay)'),
    ('walk-221126', 161): ('after', 'present state'),
    ('walk-221126', 205): ('after', '"I\'m at 9[0] degrees", present state'),
    ('walk-221126', 221): ('after', 'present state'),
}


def opening(segs, a):
    over = [g for g in segs if g['t0'] < a + 0.5 and g['t1'] > a - 0.5]
    return max(over, key=lambda g: g['t0']) if over else None


def measures(tp, a, b, walk, a0):
    r = cdr_measures(tp, a, b)
    if (walk, a0) not in SET_ASIDE['onset']:
        v = onset_measures(tp, a, b).get('onset tilt 40')
        if v is not None:
            r['onset tilt 40'] = v
    return r


def toward(rows, k):
    """{(walk, stop start): delta} for facing-0 stops against their spot's other facing-0 stops."""
    out = {}
    for key in {(r['walk'], r['spot']) for r in rows}:
        st = [r for r in rows if (r['walk'], r['spot']) == key and r['facing'] == 0 and np.isfinite(r.get(k, np.nan))]
        for r in st:
            o = [x[k] for x in st if x is not r]
            if o:
                out[(r['walk'], r['a'])] = r[k] - np.mean(o)
    return out


def rms(v):
    v = list(v)
    return float(np.sqrt(np.mean(np.square(v)))) if v else np.nan


def main():
    lab = json.loads((REPO / 'harness/rotation/facing_stops.json').read_text())['stops']
    tapes, tags, rows = {}, [], {'all': [], 'dropped': [], 'tense': []}
    pieces = []
    for walk, spots in lab.items():
        tp = tapes.setdefault(walk, Tape(walk))
        segs = json.loads((REPO / 'tapes' / walk / 'transcript.json').read_text(encoding='utf-8'))['segments']
        for spot, stops in spots.items():
            if spot == 'dist_m':
                continue
            for a, b, fd in stops:
                g = opening(segs, a)
                tag, why = TAGS[(walk, a)]
                cut = announcement_end(segs, a)
                tags.append(dict(walk=walk, stop=[a, b, fd], callout=[g['t0'], g['t1']], text=g['text'].strip(),
                                 tag=tag, why=why, dropped_to=round(cut, 2)))
                base = dict(walk=walk, spot=spot, facing=fd, a=a, b=b, tag=tag)
                starts = {'all': a, 'dropped': cut, 'tense': a if tag == 'after' else cut}
                for rule, s in starts.items():
                    s1 = max(s, HANDLING_S)                  # Tape's speech mask skips it too
                    rows[rule].append({**base, 'from_s': s1, **measures(tp, s1, b, walk, a)})
                # step 4: the callout against the rest of its stop, and a same-length piece of the rest against
                # what follows it (the baseline: how much any stretch that long differs from its stop)
                L = cut - a; a1 = max(a, HANDLING_S)
                p = dict(walk=walk, a=a, facing=fd, tag=tag, callout=measures(tp, a1, cut, walk, a),
                         rest=measures(tp, cut, b, walk, a), piece=measures(tp, cut, cut + L, walk, a),
                         after_piece=measures(tp, cut + L, b, walk, a))
                pieces.append(p)
    (HERE / 'callout_tense.json').write_text(json.dumps(
        {'about': 'Each stop\'s opening callout in facing_stops.json, tagged by tense from the Whisper decode (brief B2, '
                  '2026-10-24). after = past tense or present state, so said at the stop\'s facing; before/during = '
                  'future or in progress; unclear = garbled, or the bare "Rotate". dropped_to = where brief B\'s rule '
                  'restarts the stop.', 'callouts': tags}, indent=1, ensure_ascii=False), encoding='utf-8')

    lines, J = [], {'rules': {}}
    say = lines.append
    n = {t: sum(x['tag'] == t for x in tags) for t in ('after', 'before/during', 'unclear')}
    say(f"opening callouts: {n['after']} after, {n['before/during']} before/during, {n['unclear']} unclear "
        f"(of {len(tags)})")
    for x in tags:
        if x['tag'] != 'after':
            say(f"- {x['tag']}: {x['walk'][5:]} {x['callout'][0]:.1f}-{x['callout'][1]:.1f} s (stop {x['stop'][0]}-"
                f"{x['stop'][1]}, facing {x['stop'][2]}): \"{x['text']}\"")
    common = {k: set.intersection(*[set(toward(rows[r], k)) for r in rows]) for k in KEYS}
    say('\n| rule | measure | stops scored | toward cases | 90 vs facing 0 | 180 | AUC | left-out balanced | '
        'facing-0 agreement, dB rms | same on the pairs every rule keeps |')
    say('|---|---|---|---|---|---|---|---|---|---|')
    for rule, rr in rows.items():
        for k in KEYS:
            s = score(rr, k); tw = toward(rr, k)
            bf = s['by_facing']; lo = s['signed']
            f = lambda fd: f"{bf[fd]['mean']:+.1f} ({bf[fd]['below']}/{bf[fd]['n']})" if fd in bf else '-'  # noqa: E731
            same = rms(tw[c] for c in common[k])
            J['rules'].setdefault(rule, {})[k] = dict(score=s, toward_rms=rms(tw.values()), toward_n=len(tw),
                                                     same_pairs_rms=same, same_pairs_n=len(common[k]))
            say(f"| {rule} | {k} | {s['n_stops']} | {len(tw)} | {f(90)} | {f(180)} | {s['auc']:.2f} | "
                f"{lo['balanced'] * 100:.0f}% ({lo['toward_right']}/{lo['toward_n']}, {lo['turned_right']}/"
                f"{lo['turned_n']}) | {rms(tw.values()):.2f} | {same:.2f} (n {len(common[k])}) |")
    say('\nThe callout against the rest of its stop (dB), and the baseline: a same-length stretch just after the '
        'callout against the rest after it.')
    say('| measure | tag | n | callout minus rest: mean | rms | baseline n | baseline rms |')
    say('|---|---|---|---|---|---|---|')
    for k in KEYS:
        for t in ('after', 'before/during', 'unclear'):
            d = [p['callout'][k] - p['rest'][k] for p in pieces if p['tag'] == t and k in p['callout'] and k in p['rest']]
            bl = [p['piece'][k] - p['after_piece'][k] for p in pieces
                  if p['tag'] == t and k in p['piece'] and k in p['after_piece']]
            J.setdefault('pieces', {}).setdefault(k, {})[t] = dict(n=len(d), mean=float(np.mean(d)) if d else None,
                                                                   rms=rms(d), base_n=len(bl), base_rms=rms(bl))
            if d or bl:
                say(f"| {k} | {t} | {len(d)} | {np.mean(d) if d else np.nan:+.2f} | {rms(d):.2f} | {len(bl)} | "
                    f"{rms(bl):.2f} |")
    J['pieces_per_stop'] = pieces
    txt = '\n'.join(lines)
    (OUT / 'tense.txt').write_text(txt + '\n', encoding='utf-8')
    (OUT / 'tense.json').write_text(json.dumps(J, indent=1, default=lambda o: o.item() if hasattr(o, 'item') else str(o)),
                                    encoding='utf-8')
    print(txt)


if __name__ == '__main__':
    main()
