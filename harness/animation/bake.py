#!/usr/bin/env python3
"""One joined file per recording, for Jay's dashboard animations (2026-10-23).

Every number already measured, joined by recording, so a page can draw each sound where it truly was and where the
schemes read it, without the audio. No scheme is run here; this only reads committed results (and, for LOCATA, the
tracked positions and voice activity, streamed out of the release zip by range requests).

    python3 harness/animation/bake.py starss  <starss23 root with metadata_dev/>  results/animation/starss23
    python3 harness/animation/bake.py locata  results/animation/locata
    python3 harness/animation/bake.py dechorate results/animation/dechorate

The schema is in results/animation/README.md.
"""
import csv
import gzip
import io
import json
import math
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
C = 343.0
CLASSES = ["Female speech", "Male speech", "Clapping", "Telephone", "Laughter", "Domestic sounds", "Footsteps",
           "Door", "Music", "Musical instrument", "Water tap", "Bell", "Knock"]
SPEECH = {0, 1}
DIM_MARGIN, DIM_PAUSE_SHARE, DIM_PAUSE_DEG = 0.203, 0.5, 10.0     # brief 11's rule (results/batchA/report.md s3)
REFLECTION_NOTE = ("unverified: brief 8 scored these reflection reads at chance in angle and delay together "
                   "(results/first_reflection/report.md); don't draw them as a wall echo")


def r1(v, n=1):
    return None if v is None else round(float(v), n)


def jl(path):
    op = gzip.open if str(path).endswith('.gz') else open
    with op(path, 'rt') as fh:
        for line in fh:
            if line.strip():
                yield json.loads(line)


def dim_of(gcc, pause_deg=None, pause_share=None):
    """Brief 11's commit-or-dim rule on GccPhat's read. True = draw dimmed."""
    sh = (gcc.get('shares') or []) + [0.0, 0.0]
    margin = sh[0] - sh[1]
    on_pause = (pause_share is not None and pause_deg is not None and pause_share >= DIM_PAUSE_SHARE
                and abs(gcc['angles'][0] - pause_deg) <= DIM_PAUSE_DEG)
    return bool(margin < DIM_MARGIN or on_pause), round(margin, 3)


def write(out, name, doc):
    out.mkdir(parents=True, exist_ok=True)
    (out / f'{name}.json').write_text(json.dumps(doc, separators=(',', ':')))


# ---------------------------------------------------------------- STARSS23 -------------------------------------------
STARSS_CAPS = {1: (45, 35), 2: (-45, -35), 3: (135, -35), 4: (-135, 35)}


def starss(data_root, out):
    data_root, out = Path(data_root), Path(out)
    reads = defaultdict(list)
    for r in jl(ROOT / 'results/batchA/starss23/reads.jsonl.gz'):
        reads[r['truth']['file']].append(r)
    rng = {r['id']: r for r in jl(ROOT / 'results/batchA/starss23/range.jsonl.gz')}
    index = []
    for csv_path in sorted((data_root / 'metadata_dev').glob('*/*.csv')):
        name = csv_path.stem
        tracks = {}
        last = 0
        for row in csv.reader(open(csv_path, newline='')):
            if not row:
                continue
            fr, c, s, az, el, dist = int(row[0]), int(row[1]), int(row[2]), float(row[3]), float(row[4]), float(row[5])
            last = max(last, fr)
            t = tracks.setdefault(f'{c}/{s}', {'class': CLASSES[c], 'kind': 'speech' if c in SPEECH else 'other',
                                               'f': [], 'az': [], 'el': [], 'dist_m': []})
            t['f'].append(fr); t['az'].append(az); t['el'].append(el); t['dist_m'].append(round(dist / 100, 2))
        events = {}
        for r in reads.get(name, []):
            tr = r['truth']
            key = (tr['onset_s'], tr['cls'], tr['src'])
            e = events.setdefault(key, {
                't': tr['onset_s'], 'class': tr['class'], 'kind': tr['kind'], 'src': tr['src'], 'solo': tr['solo'],
                'truth': {'az': tr['az'], 'el': tr['el'], 'dist_m': tr['dist_m']},
                'others': [{'class': o['class'], 'az': o['az'], 'el': o['el'], 'dist_m': o['dist_m'],
                            'before': o['before'], 'during': o['during']} for o in tr.get('others', [])],
                'pairs': {}})
            g = r.get('gcc') or {}
            a2 = r.get('a2') or {}
            rg = rng.get(r['id'], {})
            dim, margin = (dim_of(g, r.get('pause_deg'), r.get('pause_share')) if g.get('angles') else (None, None))
            e['pairs'][tr['pair']] = {
                'truth_deg': tr['deg'], 'sphere_ref_deg': (tr.get('sphere_deg') or {}).get('gcc'),
                'gcc': {'angles': g.get('angles'), 'shares': g.get('shares'), 'widths': g.get('widths'),
                        'track': g.get('track'), 'err': g.get('err'), 'severity': g.get('severity')} if g else None,
                'dim': dim, 'margin': margin,
                'a2': {'deg': a2.get('deg'), 'edge': a2.get('edge'), 'first_ms': a2.get('first_ms'),
                       'err': a2.get('err')} if a2 else None,
                'reflection': {'deg': a2.get('second_deg'), 'source': 'Angle2 second family',
                               'status': REFLECTION_NOTE} if a2.get('second_deg') is not None else None,
                'pause': {'deg': r.get('pause_deg'), 'share': r.get('pause_share')},
                'classes': g.get('classes', r.get('classes')),
                'range': {'cdr_db': rg.get('cdr_db'), 'cdr_bands_db': rg.get('cdr_bands'),
                          'five_ms_inv': r1(rg.get('five_ms_inv'), 2), 'echo_ms': rg.get('echo_ms')} if rg else None}
        evs = sorted(events.values(), key=lambda e: (e['t'], e['class'], e['src']))
        # provisional relative range, anchored on the recording's first lone speech onset (per pair)
        anchor = next((e for e in evs if e['kind'] == 'speech' and e['solo']), None) or \
            next((e for e in evs if e['kind'] == 'speech'), None)
        for e in evs:
            for p, pr in e['pairs'].items():
                a = anchor['pairs'].get(p) if anchor else None
                c0 = a and a.get('range') and a['range'].get('cdr_db')
                c1 = pr.get('range') and pr['range'].get('cdr_db')
                pr['range_rel'] = r1(10 ** ((c0 - c1) / 20), 2) if (c0 is not None and c1 is not None) else None
        doc = {'dataset': 'starss23', 'recording': name, 'room': name.split('_')[1], 'split': csv_path.parent.name,
               'duration_s': round((last + 1) * 0.1, 1), 'frame_s': 0.1,
               'array': {'kind': 'Eigenmike em32, MIC format: 4 capsules on a rigid sphere',
                         'radius_m': 0.042, 'capsules_az_el_deg': STARSS_CAPS,
                         'pairs': sorted({p for e in evs for p in e['pairs']}),
                         'horizontal_pairs': ['14', '23']},
               'conventions': {
                   'az_el': 'STARSS23 labels: azimuth 0 deg ahead and positive to the left, elevation positive up',
                   'truth_deg': "a pair's lateral angle to the source; + = it reaches the pair's second capsule first",
                   'sphere_ref_deg': 'what GccPhat reads for that direction through the sphere alone; judge reads '
                                     'against it, not truth_deg (results/starss23/report.md s2)',
                   'dim': 'brief 11 rule: dim when the top two shares differ by < 0.203, or the read sits within 10 '
                          'deg of a pause read of share >= 0.5',
                   'range_rel': 'provisional: 10^((cdr_anchor - cdr)/20), anchored on the first lone speech onset; '
                                'brief 20 settles the rule'},
               'range_anchor_t': anchor['t'] if anchor else None,
               'range_anchor_dist_m': anchor['truth']['dist_m'] if anchor else None,
               'tracks': tracks, 'events': evs, 'words': None}
        write(out, name, doc)
        index.append({'recording': name, 'room': doc['room'], 'duration_s': doc['duration_s'], 'events': len(evs),
                      'speech_events': sum(e['kind'] == 'speech' for e in evs), 'sources': len(tracks)})
    (out / 'index.json').write_text(json.dumps(index, indent=1))
    print(f'starss23: {len(index)} recordings -> {out}')


# ---------------------------------------------------------------- LOCATA ---------------------------------------------
LOCATA_ZIP = 'https://zenodo.org/records/3630471/files/{set}.zip?download=1'
LOCATA_PAIRS = {'160': (5, 10), '80': (6, 9)}
TRACK_S = 0.1


def _tod(cols):
    return cols['hour'] * 3600 + cols['minute'] * 60 + cols['second']


def _read_table(z, name, max_rows=None):
    import pandas as pd
    with z.open(name) as fh:
        return pd.read_csv(io.TextIOWrapper(fh), sep='\t', nrows=max_rows)


def _segments(on, sr):
    on = np.asarray(on, dtype=bool)
    d = np.diff(np.concatenate([[0], on.astype(np.int8), [0]]))
    return [[round(a / sr, 3), round(b / sr, 3)] for a, b in zip(np.flatnonzero(d == 1), np.flatnonzero(d == -1))]


def locata(out):
    from remotezip import RemoteZip
    out = Path(out)
    truth = list(jl(ROOT / 'results/batchA/locata/truth.jsonl'))
    reads = {r['id']: r for r in jl(ROOT / 'results/batchA/locata/reads.jsonl')}
    rng = {r['id']: r for r in jl(ROOT / 'results/batchA/locata/range.jsonl')}
    refl = {r['id']: r for r in jl(ROOT / 'results/first_reflection/locata_reads.jsonl')}
    recs = defaultdict(list)
    for t in truth:
        recs[(t['set'], t['task'], t['recording'])].append(t)
    index = []
    zips = {}
    for (set_, task, rec), rows in sorted(recs.items()):
        if set_ not in zips:
            zips[set_] = RemoteZip(LOCATA_ZIP.format(set=set_))
        z = zips[set_]
        d = f'{set_}/{task}/{rec}/dicit/'
        arr = _read_table(z, d + 'position_array_dicit.txt', max_rows=1).iloc[0]
        mics = {i: np.array([arr[f'mic{i}_x'], arr[f'mic{i}_y'], arr[f'mic{i}_z']]) for i in range(1, 16)}
        ts = _read_table(z, d + 'audio_array_timestamps_dicit.txt', max_rows=1).iloc[0]
        t0 = _tod(ts)
        talkers = sorted({r['talker'] for r in rows})
        names = z.namelist()
        talkers_all = sorted(n.split('position_source_')[1][:-4] for n in names
                             if n.startswith(d + 'position_source_'))
        ml, mr = mics[5], mics[10]
        centre = (ml + mr) / 2
        u = (mr - ml) / np.linalg.norm(mr - ml)
        v = np.array([-u[1], u[0], 0.0])
        tracks = {}
        for tk in talkers_all:
            ps = _read_table(z, d + f'position_source_{tk}.txt')
            tt = _tod(ps).to_numpy() - t0
            grid = np.arange(max(0.0, tt[0]), tt[-1], TRACK_S)
            xyz = np.stack([np.interp(grid, tt, ps[k].to_numpy()) for k in ('x', 'y', 'z')], axis=1)
            ref = np.stack([np.interp(grid, tt, ps[k].to_numpy()) for k in ('ref_vec_x', 'ref_vec_y', 'ref_vec_z')],
                           axis=1)
            rel = xyz - centre
            lat = {}
            for p, (il, ir) in LOCATA_PAIRS.items():
                a, b = mics[il], mics[ir]
                tau = (np.linalg.norm(xyz - b, axis=1) - np.linalg.norm(xyz - a, axis=1)) / C
                lat[p] = np.degrees(np.arcsin(np.clip(-tau * C / np.linalg.norm(b - a), -1, 1)))
            to_arr = -rel[:, :2]
            fac = np.degrees(np.arccos(np.clip(
                (ref[:, 0] * to_arr[:, 0] + ref[:, 1] * to_arr[:, 1]) /
                np.maximum(np.hypot(ref[:, 0], ref[:, 1]) * np.hypot(to_arr[:, 0], to_arr[:, 1]), 1e-9), -1, 1)))
            vad = _read_table(z, d + f'VAD_dicit_{tk}.txt')['VAD'].to_numpy() > 0
            tracks[tk] = {'t': [round(x, 2) for x in grid],
                          'along_m': [round(float(x), 3) for x in rel @ u],
                          'ahead_m': [round(float(x), 3) for x in rel @ v],
                          'height_m': [round(float(x), 3) for x in xyz[:, 2]],
                          'dist_m': [round(float(x), 3) for x in np.linalg.norm(rel, axis=1)],
                          'lateral_deg': {p: [round(float(x), 1) for x in lat[p]] for p in lat},
                          'facing_deg': [round(float(x), 1) for x in fac],
                          'speech': _segments(vad, 48000)}
        # ahead should be positive for talkers in front; flip v if most samples sit behind
        aheads = [a for tk in tracks for a in tracks[tk]['ahead_m']]
        if aheads and np.median(aheads) < 0:
            for tk in tracks:
                tracks[tk]['ahead_m'] = [-a for a in tracks[tk]['ahead_m']]
        events = {}
        for t in rows:
            key = (t['talker'], t['onset_s'])
            e = events.setdefault(key, {'t': t['onset_s'], 'talker': t['talker'], 'kind': 'speech',
                                        'truth': {'dist_m': t['truth']['dist_m'], 'facing_deg': t['truth']['facing_deg'],
                                                  'head': t['truth'].get('head'), 'moved_deg': None},
                                        'others': [{'talker': o.get('who'), 'deg': o.get('deg'),
                                                    'before': o.get('before'), 'during': o.get('during')}
                                                   for o in t['truth'].get('others', [])],
                                        'pairs': {}})
            r = reads.get(t['id'], {})
            g = r.get('gcc') or {}
            a2 = r.get('a2') or {}
            rg = rng.get(t['id'], {})
            fr = refl.get(t['id'], {})
            dim, margin = dim_of(g) if g.get('angles') else (None, None)
            p = str(t['pair_mm'])
            e['pairs'][p] = {
                'truth_deg': t['truth']['deg'], 'truth_deg_end': t['truth'].get('deg_end'),
                'gcc': {'angles': g.get('angles'), 'shares': g.get('shares'), 'widths': g.get('widths'),
                        'track': g.get('track')} if g else None,
                'dim': dim, 'margin': margin,
                'a2': {'deg': a2.get('deg'), 'edge': a2.get('edge'), 'first_ms': a2.get('first_ms')} if a2 else None,
                'pause': {'deg': r.get('pause_deg')},
                'classes': r.get('classes'),
                'range': {'cdr_db': rg.get('cdr_db'), 'cdr_bands_db': rg.get('cdr_bands_db'),
                          'level_db': rg.get('level_db')} if rg else None,
                'reflection': {
                    'read': {'deg': (fr.get('refl') or {}).get('deg') if isinstance(fr.get('refl'), dict)
                             else fr.get('refl'), 'gap_ms': fr.get('gap_ms'), 'decided': fr.get('decided'),
                             'why_not': fr.get('why'), 'source': 'Angle2.readSound', 'status': REFLECTION_NOTE},
                    'angle2_second_deg': a2.get('second_deg'),
                    'truth': {'floor': fr.get('floor'), 'ceiling': fr.get('ceiling'),
                              'note': 'from the tracked head and the array, mouth 0.12 m under the head marker'}}}
        evs = sorted(events.values(), key=lambda e: e['t'])
        anchor = next((e for e in evs if not e['others'] and (e['truth']['facing_deg'] or 180) <= 30), None) or \
            (evs[0] if evs else None)
        for e in evs:
            for p, pr in e['pairs'].items():
                a = anchor['pairs'].get(p) if anchor else None
                c0 = a and a.get('range') and a['range'].get('cdr_db')
                c1 = pr.get('range') and pr['range'].get('cdr_db')
                pr['range_rel'] = r1(10 ** ((c0 - c1) / 20), 2) if (c0 is not None and c1 is not None) else None
        name = f'{set_}_{task}_{rec}'
        doc = {'dataset': 'locata', 'recording': name, 'set': set_, 'task': task,
               'room': {'name': 'Humboldt-Universitaet zu Berlin computing lab', 'size_m': [7.1, 9.8, 3.0],
                        'rt60_s': 0.55},
               'array': {'kind': 'DICIT linear, 15 mics', 'pairs': {p: {'mics': LOCATA_PAIRS[p],
                                                                       'mm': round(1000 * float(np.linalg.norm(
                                                                           mics[LOCATA_PAIRS[p][1]] -
                                                                           mics[LOCATA_PAIRS[p][0]])), 1)}
                                                                   for p in LOCATA_PAIRS}},
               'conventions': {
                   't': 'seconds from the array audio start',
                   'along_m / ahead_m': 'head position in the array frame: along the mic axis (mic 5 -> mic 10) and '
                                        'in front of it, from the pair centre',
                   'lateral_deg / truth_deg': "the exact two-mic angle to the head as the schemes define it",
                   'facing_deg': '0 = the head faces the array, 180 = faces away',
                   'speech': 'the talker\'s voice activity, [start, end] seconds',
                   'dim': 'brief 11 rule, margin part only (these records carry no pause share): dim when the top '
                          'two shares differ by < 0.203',
                   'range_rel': 'provisional: 10^((cdr_anchor - cdr)/20), anchored on the first lone onset facing '
                                'the array within 30 deg; brief 20 settles the rule'},
               'range_anchor_t': anchor['t'] if anchor else None,
               'range_anchor_dist_m': anchor['truth']['dist_m'] if anchor else None,
               'tracks': tracks, 'events': evs, 'words': None}
        write(out, name, doc)
        index.append({'recording': name, 'talkers': talkers_all, 'events': len(evs),
                      'duration_s': max((tr['t'][-1] for tr in tracks.values() if tr['t']), default=None)})
        print(' ', name, len(evs), 'events', talkers_all, flush=True)
    (out / 'index.json').write_text(json.dumps(index, indent=1))
    print(f'locata: {len(index)} recordings -> {out}')


# ---------------------------------------------------------------- dEchorate ------------------------------------------
def dechorate(out):
    out = Path(out)
    preds = {r['id']: r for r in jl(ROOT / 'results/dechorate/preds.jsonl.gz')}
    refl = {r['id']: r for r in jl(ROOT / 'results/first_reflection/dechorate_reads.jsonl.gz')}
    ears = json.loads((ROOT / 'harness/animation/ears_transcripts.json').read_text())['transcripts']
    by = defaultdict(lambda: defaultdict(list))
    for t in jl(ROOT / 'results/dechorate/truth.jsonl.gz'):
        by[t['room']][(t['src'], t['array'], t['spacing_mm'])].append(t)
    index = []
    for room, setups in sorted(by.items()):
        items = []
        for (src, arr, sp), cuts in sorted(setups.items()):
            t0 = cuts[0]
            meas = math.degrees(math.asin(max(-1.0, min(1.0, -t0['rir_tau_ms'] / 1000 * C / t0['baseline_m']))))
            clips = []
            for t in cuts:
                p = preds.get(t['id'], {})
                f = refl.get(t['id'], {})
                clip_file, _, at = t['clean'].partition('@')
                clips.append({'id': t['id'], 'clip': t['clean'], 'onset_in_file_s': float(at) if at else None,
                              'file_text': ears.get(clip_file.split('_', 1)[1]),
                              'gcc': p.get('gcc'), 'a2_onset_deg': (p.get('a2') or [None])[0],
                              'reflection': {'angle2_second_deg': (p.get('a2') or [None, None])[1],
                                             'read_sound': {'deg': (f.get('refl') or {}).get('deg')
                                                            if isinstance(f.get('refl'), dict) else f.get('refl'),
                                                            'gap_ms': f.get('gap_ms'), 'decided': f.get('decided')},
                                             'status': REFLECTION_NOTE}})
            items.append({'src': src, 'array': arr, 'spacing_mm': sp, 'mics': t0['mics'],
                          'truth': {'deg_geometry': t0['truth_deg'], 'deg_measured': round(meas, 2),
                                    'dist_m': t0['dist_m'],
                                    'echoes': [{k: e[k] for k in ('surface', 'reflective', 'deg', 'delay_ms')}
                                               for e in t0['echoes']]},
                          'clips': clips})
        doc = {'dataset': 'dechorate', 'room': room,
               'walls': 'six digits: which panels are reflective (1) or absorbing (0), as dEchorate names them',
               'text': 'file_text is the whole EARS file read aloud (EARS transcripts, CC BY-NC 4.0); each clip is 2 s '
                       'around onset_in_file_s, so it holds only part of it',
               'conventions': {'deg_measured': "the pair's angle from the measured RIRs' direct-path delay; score "
                                               "against it (results/clean/report.md)",
                               'echoes': 'first-order image sources per surface: angle at the pair, delay after the '
                                         'direct sound'},
               'setups': items}
        write(out, room, doc)
        index.append({'room': room, 'setups': len(items), 'clips': sum(len(i['clips']) for i in items)})
    (out / 'index.json').write_text(json.dumps(index, indent=1))
    print(f'dechorate: {len(index)} wall settings -> {out}')


if __name__ == '__main__':
    kind = sys.argv[1]
    if kind == 'starss':
        starss(sys.argv[2], sys.argv[3])
    elif kind == 'locata':
        locata(sys.argv[2])
    elif kind == 'dechorate':
        dechorate(sys.argv[2])
    else:
        raise SystemExit(__doc__)
