#!/usr/bin/env python3
"""Brief H, step 4 (2026-10-24): the regression. src's Conductor (v14) and the one before it (v13, from git) are played
over Jay's walks, and their streams read by src's CdrRange and the one before it, the way Voice's MathPass reads them
(regress.mjs). Writes results/rotation/inapp/regression.json and regression.txt; the streams go to --work (no audio).

    <Whisper venv python> harness/rotation/inapp/regress.py --root C:/Projects/GithubRoot/Dictate/captures/geonar/tapes

THE CHECKS
    frames    v14's first six cdrf values against v13's, frame for frame, over every frame v13 hands (window end by
              0.5 s): identical, except the opener's (v14 starts its CDR cold at the onset; v13 ran it on from sample 0)
    today     v14 read by the new CdrRange: the statistic drawn at 0.5 s against brief E's 'today' per utterance
              (results/rotation/inapp/reads.json, the same utterances), and nothing drawn again for any utterance
              that has no 2 s call or is called facing
    option b  the 2 s call against reads.json's contrast over 0.13-2.0 s and its 'handed' flag, and the correction
              against FACING_K x (-1 - contrast)
    v13       v13 read by the old CdrRange (both as committed before brief H): whether it draws at all
"""
import argparse
import importlib.util
import json
import math
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
import soundfile as sf

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / 'src'))
from geonar import conductor as C14  # noqa: E402

BEFORE = '16f18f4'          # the commit before brief H's src changes
K = 1.1                     # CdrRange.FACING_K
THR = -1.0


class WavSource:
    """The tape, read where it lies, as conductor.TapeSource does (CDR and the ears are symmetric in L and R)."""

    def __init__(self, path):
        self.x, sr = sf.read(path, dtype='int16', always_2d=True)
        assert sr == C14.SR and self.x.shape[1] == 2, path
        self.frames = len(self.x)

    def raw(self, start, n):
        if start < 0 or n <= 0 or start + n > self.frames:
            return None
        s = self.x[start:start + n]
        return s[:, 0], s[:, 1]

    def close(self):
        pass


def from_git(rev, path, dst):
    dst.write_text(subprocess.run(['git', 'show', f'{rev}:{path}'], cwd=REPO, capture_output=True, text=True, check=True).stdout,
                   encoding='utf-8')
    return dst


def module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    return m


def play(mod, wav, baseline, dst):
    """One unpaced play, as conductor.play() does; every item but the bearing's audio is kept."""
    src = WavSource(wav)
    with dst.open('w', encoding='utf-8') as fh:
        def send(item):
            if item.get('to') != 'bearing':
                fh.write(json.dumps(item, separators=(',', ':')) + '\n')
        c = mod.Conductor(Path(wav).stem, src, baseline, send)
        c.open(gate={'version': 'attacks'}, inputs=[])
        for now in range(mod.CHUNK, src.frames + 1, mod.CHUNK):
            c.step(now)
        c.close(src.frames)
    return dst


def frames_of(path):
    """{utt: {t: cdrf}} and the opener's index."""
    out, opener = {}, None
    for line in path.read_text(encoding='utf-8').splitlines():
        it = json.loads(line)
        if it.get('to') == 'range':
            out.setdefault(it['utt'], {}).update({f['t']: f['cdrf'] for f in it['frames']})
        elif it.get('event') == 'onset' and opener is None:
            opener = it['utt']
    return out, opener


def node(scheme, streams):
    r = subprocess.run(['node', str(REPO / 'harness/rotation/inapp/regress.mjs'), str(scheme), *map(str, streams)],
                       capture_output=True, text=True, check=True)
    return [json.loads(l) for l in r.stdout.splitlines()]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--root', default='C:/Projects/GithubRoot/Dictate/captures/geonar/tapes')
    ap.add_argument('--work', default=None)
    a = ap.parse_args()
    work = Path(a.work or tempfile.mkdtemp(prefix='brief_h_'))
    work.mkdir(parents=True, exist_ok=True)
    C13 = module(from_git(BEFORE, 'src/geonar/conductor.py', work / 'conductor_v13.py'), 'conductor_v13')
    old_js = from_git(BEFORE, 'src/schemes/CdrRange.js', work / 'CdrRange_before.js')
    new_js = REPO / 'src/schemes/CdrRange.js'
    reads = json.loads((REPO / 'results/rotation/inapp/reads.json').read_text())
    sys.path.insert(0, str(REPO / 'harness/rotation/range'))
    import score as E  # noqa: E402
    res, txt = {'conductor': [C13.VERSION, C14.VERSION], 'k': K, 'walks': {}}, []
    say = txt.append
    tot = dict(frames=0, frames_diff=0, opener_frames=0, opener_diff=0, utts=0, matched=0, today_gap=0.0, today_n=0,
               redrawn_wrongly=0, calls=0, calls_expected=0, call_mismatch=0, contrast_gap=0.0, corr_gap=0.0,
               old_draws=0, old_utts=0, new_on_v13_gap=0.0, new_on_v13_calls=0, old_on_v14_draws=0, multi_draws=0, u_gap=0.0)
    for w, v in sorted(reads['walks'].items()):
        wav = Path(a.root) / f'{w}.wav'
        s14 = play(C14, wav, v['baseline_m'], work / f'{w}.v14.jsonl')
        s13 = play(C13, wav, v['baseline_m'], work / f'{w}.v13.jsonl')
        # frames: v14's first six values against v13's
        f14, op = frames_of(s14); f13, _ = frames_of(s13)
        fd = fn = od = on = 0
        for u, fr in f13.items():
            for t, c in fr.items():
                same = u in f14 and t in f14[u] and f14[u][t][:6] == c
                if u == op:
                    on += 1; od += not same
                else:
                    fn += 1; fd += not same
        tot['frames'] += fn; tot['frames_diff'] += fd; tot['opener_frames'] += on; tot['opener_diff'] += od
        # today and option b: the new CdrRange on v14
        new14 = node(new_js, [s14])[0]['utts']
        py = {r['t']: r for r in v['reads']}
        rows = []
        drawn = [u for u in new14 if u['S'] is not None]
        s_open = drawn[0]['S'] + drawn[0]['corr'] if drawn else None     # the unit: the first utterance drawn, corrected
        for u in drawn:
            tot['utts'] += 1
            r = py.get(round(u['onset_s'], 3))
            if r is None:
                continue
            tot['matched'] += 1
            gap = abs(u['S'] - E.today(r, 'short')); tot['today_gap'] = max(tot['today_gap'], gap); tot['today_n'] += 1
            want_call = 'facing' in r and r['facing']['handed']
            s_b = E.today(r, 'short') + (K * max(0.0, THR - E.contrast(r, 'facing')) if want_call else 0.0)
            tot['u_gap'] = max(tot['u_gap'], abs(math.log10(u['draws'][-1][1]) * 20 - (s_open - s_b)))
            tot['calls_expected'] += want_call; tot['calls'] += u['facing'] is not None
            if want_call != (u['facing'] is not None):
                tot['call_mismatch'] += 1
            if u['facing'] is not None and want_call:
                con = E.contrast(r, 'facing')
                tot['contrast_gap'] = max(tot['contrast_gap'], abs(u['contrast'] - con))
                want = K * max(0.0, THR - con)
                tot['corr_gap'] = max(tot['corr_gap'], abs(u['corr'] - want))
                if (u['facing'] == 'turned') != (con < THR):
                    tot['call_mismatch'] += 1
            if u['facing'] != 'turned' and len(u['draws']) > 1:
                tot['redrawn_wrongly'] += 1
            tot['multi_draws'] += len(u['draws']) > 2
            rows.append(dict(t=u['onset_s'], S=u['S'], corr=u['corr'], facing=u['facing'], contrast=u['contrast'],
                             draws=len(u['draws'])))
        # v13 as committed: old CdrRange on v13; and each reader on the other's stream
        old13 = node(old_js, [s13])[0]['utts']
        tot['old_utts'] += len(old13); tot['old_draws'] += sum(len(u['draws']) > 0 for u in old13)
        new13 = node(new_js, [s13])[0]['utts']
        by14 = {round(u['onset_s'], 3): u for u in new14 if u['S'] is not None}
        for u in new13:
            m = by14.get(round(u['onset_s'], 3))
            if u['S'] is not None and m is not None and u['utt'] != op:
                tot['new_on_v13_gap'] = max(tot['new_on_v13_gap'], abs(u['S'] - m['S']))
            tot['new_on_v13_calls'] += u['facing'] is not None
        old14 = node(old_js, [s14])[0]['utts']
        tot['old_on_v14_draws'] += sum(len(u['draws']) > 0 for u in old14)
        res['walks'][w] = dict(frames=fn, frames_diff=fd, opener_frames=on, opener_diff=od, utts=rows,
                               old_v13_draws=sum(len(u['draws']) > 0 for u in old13), old_v13_utts=len(old13))
        print(w, f"frames {fd}/{fn} differ (opener {od}/{on}); {len(rows)} utterances read; old CdrRange on v13 drew "
                 f"{res['walks'][w]['old_v13_draws']} of {len(old13)}", flush=True)
    res['totals'] = tot
    say(f"Conductor v{C13.VERSION} -> v{C14.VERSION}, CdrRange before brief H -> now (k {K}), {len(res['walks'])} walks")
    say(f"frames: {tot['frames_diff']} of {tot['frames']} v13 range frames differ in their first six values from v14's "
        f"(openers aside); the openers' {tot['opener_frames']} frames: {tot['opener_diff']} differ")
    say(f"today: {tot['matched']} of {tot['utts']} drawn utterances matched to reads.json by onset; the 0.5 s statistic "
        f"against brief E's 'today': largest gap {tot['today_gap']:.4f} dB over {tot['today_n']}; the u it holds against option b's "
        f"statistic in the tape's unit: largest gap {tot['u_gap']:.4f} dB")
    say(f"held: {tot['redrawn_wrongly']} utterances without a turned call drew more than once; {tot['multi_draws']} drew more than twice")
    say(f"option b: {tot['calls']} 2 s calls made, {tot['calls_expected']} expected (reads.json 'handed'); {tot['call_mismatch']} "
        f"mismatches in presence or verdict; contrast gap {tot['contrast_gap']:.4f} dB, correction gap {tot['corr_gap']:.4f} dB")
    say(f"v13 as committed (old CdrRange on v13): drew a range on {tot['old_draws']} of {tot['old_utts']} utterances")
    say(f"the new CdrRange on a v13 stream: largest gap to its own v14 reading {tot['new_on_v13_gap']:.4f} dB (openers aside), "
        f"{tot['new_on_v13_calls']} facing calls (none expected: v13 has no fourth band and stops at 0.5 s)")
    say(f"the old CdrRange on a v14 stream: drew on {tot['old_on_v14_draws']} utterances (it reads only 6-value cdrf)")
    (REPO / 'results/rotation/inapp/regression.json').write_text(json.dumps(res, indent=1, default=float))
    (REPO / 'results/rotation/inapp/regression.txt').write_text('\n'.join(txt) + '\n')
    print('\n'.join(txt))
    print('streams in', work)


if __name__ == '__main__':
    main()
