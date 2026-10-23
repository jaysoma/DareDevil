#!/usr/bin/env python3
"""Brief 16's job list: one job per recording and capsule pair, with batch A's reads for it (id, onset, spacing).

STARSS23: every recording of the development set (the gate tests want gaps and non-speech onsets too, not only batch A's
reads), pairs 1-2 and 3-4 (disjoint capsules). LOCATA: every recording batch A read (tasks 3 and 4), both pairs.

usage: build_jobs.py REPO STARSS_ROOT LOCATA_ROOT OUT.jsonl [--starss-pairs 12 34]
"""
import argparse
import gzip
import json
from collections import defaultdict
from pathlib import Path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('repo')
    ap.add_argument('starss')
    ap.add_argument('locata')
    ap.add_argument('out')
    ap.add_argument('--starss-pairs', nargs='+', default=['12', '34'])
    a = ap.parse_args()
    repo, starss, locata = Path(a.repo), Path(a.starss), Path(a.locata)
    jobs = []
    reads = defaultdict(list)
    with gzip.open(repo / 'results/batchA/starss23/truth.jsonl.gz', 'rt') as fh:
        for l in fh:
            t = json.loads(l)
            p = t['id'].split('/')[0]
            if p in a.starss_pairs:
                reads[t['truth']['file'], p].append({'id': t['id'], 'onset_s': t['truth']['onset_s'],
                                                     'baseline_m': round(t['pair_mm'] / 1000, 5)})
    for wav in sorted(starss.glob('mic_dev/*/*.wav')):
        meta = next(starss.glob(f'metadata_dev/*/{wav.stem}.csv'), None)
        if meta is None:
            continue
        for p in a.starss_pairs:
            jobs.append({'dataset': 'starss23', 'tag': f'starss23_{wav.stem}_{p}', 'wav': str(wav), 'meta': str(meta),
                         'caps': [int(p[0]), int(p[1])], 'pair': p, 'file': wav.stem,
                         'reads': sorted(reads.get((wav.stem, p), []), key=lambda r: r['onset_s'])})
    lreads = defaultdict(list)
    lmics = {}
    for l in open(repo / 'results/batchA/locata/truth.jsonl'):
        t = json.loads(l)
        k = (t['set'], t['task'], t['recording'], t['pair_mm'])
        lmics[k] = t['mics']
        lreads[k].append({'id': t['id'], 'onset_s': t['onset_s'], 'baseline_m': t['baseline_m']})
    for (s, task, rec, mm), rs in sorted(lreads.items()):
        d = locata / s / task / rec / 'dicit'
        jobs.append({'dataset': 'locata', 'tag': f'locata_{s}_{task}_{rec}_{mm}', 'wav': str(d / 'audio_array_dicit.wav'),
                     'vads': [str(v) for v in sorted(d.glob('VAD_dicit_*.txt'))], 'mics': lmics[s, task, rec, mm],
                     'pair': str(mm), 'set': s, 'task': task, 'recording': rec,
                     'reads': sorted(rs, key=lambda r: r['onset_s'])})
    with open(a.out, 'w') as fh:
        for j in jobs:
            fh.write(json.dumps(j) + '\n')
    print(len(jobs), 'jobs:', sum(j['dataset'] == 'starss23' for j in jobs), 'STARSS23,',
          sum(j['dataset'] == 'locata' for j in jobs), 'LOCATA;', sum(len(j['reads']) for j in jobs), 'reads')


if __name__ == '__main__':
    main()
