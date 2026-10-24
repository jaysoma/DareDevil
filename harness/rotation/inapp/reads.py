#!/usr/bin/env python3
"""Brief H's reads (2026-10-24): brief E's per-utterance reads, plus the 2 s facing read option b needs. Run on Jay's box,
where the audio is; writes results/rotation/inapp/reads.json (no audio).

    <Whisper venv python> harness/rotation/inapp/reads.py --root C:/Projects/GithubRoot/Dictate/captures/geonar/tapes

THE UTTERANCES are brief E's (harness/rotation/range/reads.py): on Jay's walks the Conductor's own ears fed the tape in
its 512-sample CHUNKs, on LOCATA the animation files' scored events. Each one also carries WHEN it was closed:
    decided   the chunk at which the ears made the close (the next open, or CLOSE_MS of quiet: about 1 s after the
              backdated close). The Conductor hands CDR frames up to here, so this, not the backdated close, says
              whether the 2 s frame ever reaches CdrRange. LOCATA has no ears: decided = the close.
THE READS, both cold-started at the onset, frames from SETTLE_S on, band powers summed per band (E's Stream):
    short     frames whose window ends by RANGE_READ_S (0.5 s): the range read, exactly brief E's 'short'
    facing    frames whose window ends by FACING_READ_S (2.0 s): the facing read, kept when the utterance reaches it
              handed   the Conductor hands the 2 s frame (decided reaches it): what v14 does, the main rule
              speech2  the backdated close is 2 s or more after the onset: the brief's "utterances of 2 s or more"
"""
import argparse
import glob
import json
import math
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / 'src'))
sys.path.insert(0, str(REPO / 'harness/rotation/range'))
from geonar.attacks import Attacks  # noqa: E402
from geonar.cdr_direct import HOP, NFFT, SR  # noqa: E402
from reads import BANDS, CHUNK, LADDER_WALKS, SETTLE_S, RANGE_READ_S, Stream, load  # noqa: E402  (brief E's)

FACING_READ_S = 2.0
K0 = -(-int(round(SETTLE_S * SR)) // HOP)              # first hop at or after onset + SETTLE_S: 13
K_SHORT = (int(RANGE_READ_S * SR) - NFFT) // HOP        # last hop whose window ends by 0.5 s: 42
K_FACE = (int(FACING_READ_S * SR) - NFFT) // HOP        # last hop whose window ends by 2.0 s: 183
FACE_END = K_FACE * HOP + NFFT                          # that frame's window end, samples after the onset


def utterances(x):
    """The Conductor's utterances: (onset, close, decided) frames from its ears, every open a fresh one."""
    ears, out, cur = Attacks(), [], None
    for now in range(CHUNK, len(x) + 1, CHUNK):
        for kind, frame in ears.feed(x[now - CHUNK:now, 0] * 32768, x[now - CHUNK:now, 1] * 32768):
            if kind == 'open':
                if cur is not None:
                    out.append((cur, frame, now))
                cur = frame
            elif cur is not None:
                out.append((cur, frame, now)); cur = None
    if cur is not None:
        out.append((cur, len(x), len(x)))
    return out


def read(stream, x, onset, close, decided):
    """One utterance's short read (None under E's own rule: the close comes before the 0.5 s frame) and facing read."""
    k_whole = (min(close, len(x)) - onset - NFFT) // HOP
    if k_whole < K_SHORT:
        return None
    n = K_FACE + 1 if onset + FACE_END <= len(x) else K_SHORT + 1
    D, R = stream.run(x, onset, n)
    db = lambda a: [round(10 * math.log10(max(v, 1e-30)), 3) for v in a]
    s = slice(K0, K_SHORT + 1)
    out = {'short': {'d': db(D[s].sum(0)), 'r': db(R[s].sum(0)), 'n': K_SHORT + 1 - K0},
           'close_s': round((close - onset) / SR, 3), 'decided_s': round((decided - onset) / SR, 3)}
    if n == K_FACE + 1:
        f = slice(K0, K_FACE + 1)
        out['facing'] = {'d': db(D[f].sum(0)), 'r': db(R[f].sum(0)), 'n': K_FACE + 1 - K0,
                         'handed': bool(onset + FACE_END <= decided), 'speech2': bool(close - onset >= FACING_READ_S * SR)}
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--root', default='C:/Projects/GithubRoot/Dictate/captures/geonar/tapes')
    a = ap.parse_args()
    root = Path(a.root)
    lab = json.loads((REPO / 'harness/rotation/facing_stops.json').read_text())['stops']
    lib = {t['name']: t for t in json.loads((REPO / 'library.json').read_text())['tapes']}
    out = {'about': __doc__.split('\n\n')[0], 'bands': [{'name': b, 'lo_hz': lo, 'hi_hz': hi, 'floored': fl}
                                                          for b, lo, hi, fl in BANDS],
           'settle_s': SETTLE_S, 'range_read_s': RANGE_READ_S, 'facing_read_s': FACING_READ_S, 'walks': {}, 'locata': {}}
    for w in sorted(set(lab) | set(LADDER_WALKS)):
        folded = lib.get(w, {}).get('folded_deg')
        d = 0.157 if not folded else 0.157 * math.sin(math.radians(folded) / 2)
        x = load(root / f'{w}.wav')
        st, reads = Stream(d), []
        for on, cl, dec in utterances(x):
            r = read(st, x, on, cl, dec)
            if r is not None:
                reads.append({'t': round(on / SR, 3), 'end': round(cl / SR, 3), **r})
        out['walks'][w] = {'baseline_m': d, 'reads': reads}
        nf = sum('facing' in r and r['facing']['handed'] for r in reads)
        print(w, len(reads), 'reads,', nf, 'with the 2 s frame handed', flush=True)
    for f in sorted(glob.glob(str(REPO / 'results/animation/locata/*_task*_recording*.json'))):
        doc = json.loads(Path(f).read_text())
        name = doc['recording']
        x = load(root / f'locata-{name}.wav')
        d = doc['array']['pairs']['160']['mm'] / 1000
        st, reads = Stream(d), []
        ts = sorted(e['t'] for e in doc['events'])
        for e in doc['events']:
            on = int(round(e['t'] * SR))
            spans = doc['tracks'][e['talker']]['speech']
            end = next((b for s, b in spans if s - 0.3 <= e['t'] < b), e['t'] + 1.0)
            nxt = next((t for t in ts if t > e['t']), math.inf)    # every onset is a fresh utterance: the next one closes it
            close = int(min(end, nxt) * SR)
            r = read(st, x, on, int(end * SR), close)               # E's short-read rule on the speech span, as E had it
            if r is None:
                continue
            reads.append({'t': e['t'], 'end': end, 'talker': e['talker'], 'dist_m': e['truth']['dist_m'],
                          'facing_deg': e['truth'].get('facing_deg'), 'others': len(e.get('others') or []), **r})
        out['locata'][name] = {'baseline_m': d, 'reads': reads}
        print(name, len(reads), 'reads', flush=True)
    dst = REPO / 'results/rotation/inapp/reads.json'
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(json.dumps(out, separators=(',', ':')))


if __name__ == '__main__':
    main()
