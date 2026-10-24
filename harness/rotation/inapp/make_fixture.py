#!/usr/bin/env python3
"""Brief H's test fixture (2026-10-24): four utterances of walk-224302's Conductor v14 stream (regress.py's --work), with
what CdrRange must draw for each, worked out in Python from reads.json -- not from CdrRange. Writes fixture.json here.

    <Whisper venv python> harness/rotation/inapp/make_fixture.py --work <regress.py's work folder>

    2.096 s   the opener, 2 s or more, called facing: the unit, drawn once
    5.599 s   under 2 s: drawn once at 0.5 s, no call
    16.468 s  2 s or more, called facing: drawn once, no correction
    57.077 s  2 s or more, called turned: drawn at 0.5 s, corrected once at 2 s
"""
import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / 'harness/rotation/range'))
import score as E  # noqa: E402

WALK, PICK, K, THR = 'walk-224302', (2.096, 5.599, 16.468, 57.077), 1.1, -1.0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--work', required=True)
    a = ap.parse_args()
    items = [json.loads(l) for l in (Path(a.work) / f'{WALK}.v14.jsonl').read_text().splitlines()]
    reads = {r['t']: r for r in json.loads((REPO / 'results/rotation/inapp/reads.json').read_text())['walks'][WALK]['reads']}
    keep = {it['utt'] for it in items if it.get('event') in ('open', 'onset') and round(it['onset_s'], 3) in PICK}
    stream = [it for it in items if it.get('utt') in keep and it.get('to') in ('render', 'range')]
    expect, s_open = [], None
    for t in PICK:
        r = reads[t]
        S = E.today(r, 'short')
        call = None
        if 'facing' in r and r['facing']['handed']:
            con = E.contrast(r, 'facing'); call = 'turned' if con < THR else 'facing'
        corr = K * (THR - con) if call == 'turned' else 0.0
        if s_open is None:
            s_open = S + corr                                     # the opener sets the unit, corrected like the rest
        u05 = 10 ** ((s_open - S) / 20) if t != PICK[0] else 1.0
        expect.append(dict(onset_s=t, S=round(S, 4), facing=call, contrast=round(con, 4) if call else None,
                           corr=round(corr, 4), u_at_0_5=round(u05, 5), u_final=round(10 ** ((s_open - S - corr) / 20), 5),
                           draws=2 if call == 'turned' and t != PICK[0] else 1))
    doc = {'about': __doc__.split('\n\n')[0], 'walk': WALK, 'k': K, 'thr_db': THR, 'expect': expect, 'stream': stream}
    (REPO / 'harness/rotation/inapp/fixture.json').write_text(json.dumps(doc, separators=(',', ':')))
    print(len(stream), 'items;', json.dumps(expect, indent=1))


if __name__ == '__main__':
    main()
