#!/usr/bin/env python3
"""Brief 13, the whole lab: every placement x audio set -> cut -> run both schemes (and the run-time causes) ->
batch A records. Cuts are deleted as soon as their records are written; only truth and records are kept.

    python3 run_all.py EARS_TALKERS EARS_INTERF RIR_HDF5 WORK OUT
-> OUT/reads.jsonl.gz (one record per read and run), OUT/truth.jsonl.gz (one per cut, no audio).
"""
import gzip
import zlib
import json
import os
import subprocess
import sys
from multiprocessing import Pool
from pathlib import Path

H = Path(__file__).resolve().parent
SRC = H.parents[1] / 'src' / 'schemes'
VAR = H / 'variants'
PLACEMENTS = ['free157', 'free69', 'room000000', 'room011111']
LEVELS = [-30, -20, -10, 0]
AUDIO = (['baseline'] + [f'{k}:{v}' for k in ('steady_pink', 'steady_voice', 'common_mode', 'diffuse') for v in LEVELS]
         + [f'quiet:{v}' for v in (30, 20, 10, 5)])
# runs on the baseline audio: (cause, schemes dir, extra args, gcc band low edge, a2 band low edge)
BASE_RUNS = ([('baseline', SRC, [], 300, 1100)]
             + [(f'band_lo:{lo}', VAR / f'lo{lo}', [], lo, lo) for lo in (300, 1100, 2000)]
             + [(f'onset_offset:{o:+d}', SRC, ['--offset-ms', str(o)], 300, 1100) for o in (-50, -25, 25, 50, 100, 150)]
             + [('no_pause', SRC, ['--nopause', '--gcc-only'], 300, 1100)])


# cause 6 where it can matter: the pause holds a sound. The same cuts as those sets (the same seed), GccPhat only.
NP_AUDIO = [a for a in AUDIO if a.split(':')[0] in ('steady_pink', 'steady_voice', 'common_mode', 'diffuse')]


def job(arg):
    placement, audio, ears, interf, rirs, work, np_only = arg
    tag = f"{placement}_{audio.replace(':', '_')}"
    rec = Path(work) / 'rec' / f"{tag}{'_np' if np_only else ''}.jsonl"
    if rec.exists():
        return tag
    cuts = Path(work) / f'cuts_{tag}.jsonl'
    subprocess.run([sys.executable, str(H / 'lab_cut.py'), ears, interf, rirs, '--placement', placement, '--cause', audio,
                    '--out', str(cuts), '--seed', str(zlib.crc32(tag.encode()) % 10 ** 6)], check=True, stderr=subprocess.DEVNULL)
    runs = BASE_RUNS if audio == 'baseline' else [(audio, SRC, [], 300, 1100)]
    if np_only:
        runs = [(f'no_pause+{audio}', SRC, ['--nopause', '--gcc-only'], 300, 1100)]
    spec = []
    for cause, sdir, extra, glo, alo in runs:
        pred = Path(work) / f'pred_{tag}_{cause.replace(":", "_")}.jsonl'
        with open(pred, 'w') as fh:
            subprocess.run(['node', str(H / 'run_lab.mjs'), str(cuts), str(sdir), *extra], check=True, stdout=fh)
        spec.append({'cause': cause, 'preds': str(pred), 'offset_ms': int(extra[1]) if extra[:1] == ['--offset-ms'] else 0,
                     'nopause': '--nopause' in extra, 'gcc_lo': glo, 'a2_lo': alo})
    sp = Path(work) / f'runs_{tag}.json'
    sp.write_text(json.dumps(spec))
    tmp = rec.with_suffix('.tmp')
    tmp.unlink(missing_ok=True)
    subprocess.run([sys.executable, str(H / 'records.py'), str(cuts), str(sp), str(tmp)], check=True)
    with open(Path(work) / 'truth' / f'{tag}.jsonl', 'w') if not np_only else open(os.devnull, 'w') as ft:
        for l in open(cuts):
            c = json.loads(l)
            for k in ('L', 'R'):
                c.pop(k)
            ft.write(json.dumps(c) + '\n')
    tmp.rename(rec)
    cuts.unlink()
    for s in spec:
        os.unlink(s['preds'])
    print('done', tag, flush=True)
    return tag


def main():
    ears, interf, rirs, work, out = sys.argv[1:6]
    for sub in ('rec', 'truth'):
        (Path(work) / sub).mkdir(parents=True, exist_ok=True)
    jobs = ([(p, a, ears, interf, rirs, work, False) for a in AUDIO for p in PLACEMENTS]
            + [(p, a, ears, interf, rirs, work, True) for a in NP_AUDIO for p in PLACEMENTS])
    with Pool(os.cpu_count()) as pool:
        for _ in pool.imap_unordered(job, jobs):
            pass
    Path(out).mkdir(parents=True, exist_ok=True)
    with gzip.open(Path(out) / 'reads.jsonl.gz', 'wt') as fo:
        for p in PLACEMENTS:
            for a in AUDIO:
                fo.write(open(Path(work) / 'rec' / f"{p}_{a.replace(':', '_')}.jsonl").read())
            for a in NP_AUDIO:
                fo.write(open(Path(work) / 'rec' / f"{p}_{a.replace(':', '_')}_np.jsonl").read())
    with gzip.open(Path(out) / 'truth.jsonl.gz', 'wt') as fo:
        for p in PLACEMENTS:
            for a in AUDIO:
                fo.write(open(Path(work) / 'truth' / f"{p}_{a.replace(':', '_')}.jsonl").read())
    print('wrote', out)


if __name__ == '__main__':
    main()
