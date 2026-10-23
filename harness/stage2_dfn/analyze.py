#!/usr/bin/env python3
"""Brief 16's numbers from dfn_pass.py's output, joined to batch A's records by read id.

usage: analyze.py REPO WORK OUT    -> OUT/summary.json, OUT/tables.md, OUT/reads.jsonl.gz (per read: every variant's
GccPhat read with its classes, and the DFN clues; batch A's records themselves are never changed)

Tests (cloud_sessions.md, brief 16):
  1 LEVEL      every number at both levels: `raw` (as recorded) and `norm` (one gain per recording and pair, labelled
               speech at -26 dBFS). How far lsnr moves.
  2 GATE       lsnr > 0 dB as a live speech gate. Speech onsets: batch A's (STARSS23 labels at 100 ms; LOCATA's VAD).
               For each: when lsnr first goes over 0 dB from 0.3 s before to 1.0 s after (or 'already open' when it was
               over 0 for the whole 100 ms before the onset), and src/geonar/attacks.py's MF open nearest the onset.
               False opens: share of gap frames over 0 dB, and opens per minute of gap (gaps: no labelled event, 300 ms
               after the last and 100 ms before the next; LOCATA: no talker's VAD). Non-speech onsets (STARSS23's other
               classes, no speech labelled from 0.5 s before to 0.5 s after): the share that open the gate within 0.5 s.
  3 MASK GATE  the same with the mask (mean over 300 Hz - 8 kHz) over 0.2-0.5 as the gate (GATES); the soft-first-word miss
               rate by the onset's MF voice-over-pause quartile.
  4 GHOST      GccPhat's votes weighted by the mask from (a) the L+R mixdown (`mix`), (b) capsule L (`cap`), (c) none
               (`raw`): batch A's classes per variant (aliasing partner, 0 deg pull, other, ...), and every read that
               moves in or out of 10 deg against (c).
  5 OPERATOR   GccPhat on the DFN pair (`dfn`) against the raw pair, read by read.
  6 CLUES      lsnr at the onset, its max over 200 ms, the mask's share of the band: how well each separates GccPhat's
               right reads from its wrong ones (AUC).
  7 COST       DFN seconds per second of audio.
"""
import gzip
import json
import math
import statistics as st
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

REPO, WORK, OUT = (Path(p) for p in sys.argv[1:4])
sys.path.insert(0, str(REPO / 'harness/scoring'))
sys.path.insert(0, str(REPO / 'harness/batchA/starss23'))
sys.path.insert(0, str(REPO / 'harness/batchA/locata'))
import clean_score as cs                                                     # noqa: E402
import classify as sclass                                                     # noqa: E402
import build_records as lclass                                               # noqa: E402

HOP_S = 0.01
LEVELS = ['raw', 'norm']
# the gates tried: lsnr over 0 dB (Jay's), and the mask (mixdown, mean over 300 Hz - 8 kHz) over a sweep of thresholds,
# since nothing fixes the mask's; plus lsnr at -5 and +5 dB to show how sensitive its 0 dB is
GATES = ([('lsnr', 'lsnr', 0.0), ('lsnr-5', 'lsnr', -5.0), ('lsnr+5', 'lsnr', 5.0)]
         + [(f'mask{t}', 'mask_mix', t) for t in (0.2, 0.3, 0.4, 0.5)])
NONSPEECH = {'footsteps', 'door/cupboard', 'knock', 'telephone', 'clapping', 'domestic sounds', 'bell', 'water tap',
             'laughter', 'music', 'musical instrument'}


def pct(v):
    v = list(v)
    return round(100 * sum(v) / len(v), 1) if v else None


def med(v):
    v = [x for x in v if x is not None and not (isinstance(x, float) and math.isnan(x))]
    return round(st.median(v), 2) if v else None


def auc(pos, neg):
    """P(a random wrong read scores higher than a random right one), ties half."""
    if not pos or not neg:
        return None
    allv = sorted([(v, 1) for v in pos] + [(v, 0) for v in neg])
    r, i, s = 0.0, 0, 0.0
    ranks = {}
    while i < len(allv):
        j = i
        while j < len(allv) and allv[j][0] == allv[i][0]:
            j += 1
        for k in range(i, j):
            if allv[k][1]:
                s += (i + j + 1) / 2
        i = j
    return round((s - len(pos) * (len(pos) + 1) / 2) / (len(pos) * len(neg)), 3)


# ---------------------------------------------------------------------------------------------- batch A records, jobs
jobs = {json.loads(l)['tag']: json.loads(l) for l in open(WORK / 'jobs.jsonl')}
read_job = {r['id']: j for j in jobs.values() for r in j['reads']}
recs = {}
with gzip.open(REPO / 'results/batchA/starss23/reads.jsonl.gz', 'rt') as fh:
    for l in fh:
        r = json.loads(l)
        if r['id'] in read_job:
            recs[r['id']] = r
for l in open(REPO / 'results/batchA/locata/reads.jsonl'):
    r = json.loads(l)
    if r['id'] in read_job:
        recs[r['id']] = r
ltruth = {json.loads(l)['id']: json.loads(l) for l in open(REPO / 'results/batchA/locata/truth.jsonl')}
print(len(recs), 'batch A reads joined', file=sys.stderr)


def frames(tag, level):
    p = WORK / 'frames' / f'{tag}_{level}.npz'
    return np.load(p) if p.exists() else None


# ------------------------------------------------------------------------------------------------------------ 7 cost
cost = [json.loads(p.read_text()) for p in (WORK / 'cost').glob('*.json')]
res = {'cost': {
    'audio_s': round(sum(c['audio_s'] for c in cost), 1),
    'rtf_mixdown_pass': round(sum(c['dfn_mix_s'] for c in cost) / sum(c['audio_s'] for c in cost), 4),
    'rtf_capsule_pass': round(sum(c['dfn_cap_s'] for c in cost) / sum(c['audio_s'] for c in cost), 4),
    'note': 'one CPU thread, torch 2.0.1, whole recordings; the mixdown pass includes the shared operator on L and R '
            'and the ISTFT'}}

# ------------------------------------------------------------------------------------------------------- 2, 3 gates
_ACT = {}


def activity(j, n_frames):
    """(speech[T], gap[T]) on DFN's 10 ms grid (cached: LOCATA's VAD files hold one line per sample)."""
    if (j['tag'], n_frames) not in _ACT:
        _ACT[j['tag'], n_frames] = _activity(j, n_frames)
    return _ACT[j['tag'], n_frames]


def _activity(j, n_frames):
    speech = np.zeros(n_frames, bool)
    anyev = np.zeros(n_frames, bool)
    if j['dataset'] == 'starss23':
        for line in open(j['meta']):
            r = line.strip().split(',')
            if len(r) < 2:
                continue
            f = int(r[0])
            a, b = f * 10, min(n_frames, f * 10 + 10)
            anyev[a:b] = True
            if int(r[1]) in (0, 1):
                speech[a:b] = True
    else:
        for v in j['vads']:
            x = np.loadtxt(v, skiprows=1, usecols=(-1,)) > 0
            m = min(len(x) // 480, n_frames)
            s = x[:m * 480].reshape(m, 480).any(1)
            speech[:m] |= s
        anyev = speech.copy()
    gap = ~anyev
    for k in range(1, 31):                                   # 300 ms after the last event
        gap[k:] &= ~anyev[:-k]
    for k in range(1, 11):                                   # 100 ms before the next
        gap[:-k] &= ~anyev[k:]
    gap[:200] = False                                        # the first 2 s (STARSS23's scene-start clapper)
    return speech, gap


def gate_open_at(track, k_on, thr):
    """(state, latency s): 'already' when the gate was open the whole 100 ms before; else the first frame over thr from
    0.3 s before to 1.0 s after; None when it never opened."""
    T = len(track)
    pre = track[max(0, k_on - 10):k_on]
    if len(pre) and (pre > thr).all():
        return 'already', None
    for k in range(max(0, k_on - 30), min(T, k_on + 100)):
        if track[k] > thr and (k == 0 or track[k - 1] <= thr):
            return 'opened', round((k - k_on) * HOP_S, 3)
    return 'missed', None


# ----------------------------------------------------------------------------------------------------------- 1 level
lev = defaultdict(lambda: defaultdict(list))
for tag, j in jobs.items():
    fr = {lv: frames(tag, lv) for lv in LEVELS}
    if any(v is None for v in fr.values()):
        continue
    ds = j['dataset']
    speech, gap = activity(j, len(fr['raw']['lsnr']))
    if not np.isnan(float(fr['raw']['speech_db'])):
        lev[ds]['speech_dbfs'].append(float(fr['raw']['speech_db']))
    lev[ds]['gain_db'].append(20 * math.log10(float(fr['norm']['gain'])))
    for lv in LEVELS:
        for name, m in (('speech', speech), ('gap', gap)):
            if m.any():
                lev[ds][f'lsnr_{name}_{lv}'].append(float(np.median(fr[lv]['lsnr'][m])))
    if speech.any():
        lev[ds]['lsnr_speech_moved_db'].append(float(np.median(fr['norm']['lsnr'][speech]) - np.median(fr['raw']['lsnr'][speech])))
res['level'] = {ds: {k: {'median': med(v), 'min': round(min(v), 2), 'max': round(max(v), 2),
                         'p10': round(float(np.percentile(v, 10)), 2), 'p90': round(float(np.percentile(v, 90)), 2),
                         'n': len(v)} for k, v in d.items()} for ds, d in lev.items()}


gate = {}
soft = defaultdict(list)
for lv in LEVELS:
    for ds in ('starss23', 'locata'):
        for gname, key, thr in GATES:
            on_state, lat, mf_diff, gap_open, gap_eps, gap_min, other_open = Counter(), [], [], [], 0, 0.0, []
            for tag, j in jobs.items():
                if j['dataset'] != ds:
                    continue
                fr = frames(tag, lv)
                if fr is None:
                    continue
                tr = fr[key]
                speech, gap = activity(j, len(tr))
                atk = json.loads((WORK / 'attacks' / f'{tag}.json').read_text()) \
                    if (WORK / 'attacks' / f'{tag}.json').exists() else []
                g = tr > thr
                gap_open.append((int((g & gap).sum()), int(gap.sum())))
                gap_eps += int((g[1:] & ~g[:-1] & gap[1:]).sum())
                gap_min += gap.sum() * HOP_S / 60
                for r in j['reads']:
                    rec = recs.get(r['id'])
                    if rec is None:
                        continue
                    k_on = int(round(r['onset_s'] / HOP_S))
                    kind = rec['truth'].get('kind', 'speech') if ds == 'starss23' else 'speech'
                    if kind == 'speech':
                        state, l = gate_open_at(tr, k_on, thr)
                        on_state[state] += 1
                        if l is not None:
                            lat.append(l)
                            near = [a for a in atk if abs(a - r['onset_s']) <= 0.3]
                            if near:
                                mf = min(near, key=lambda a: abs(a - r['onset_s']))
                                mf_diff.append(round(r['onset_s'] + l - mf, 3))
                        if ds == 'starss23' and r['id'].startswith('12/'):
                            soft[lv, gname].append((rec['snr_db']['mf'], state == 'opened' and l <= 0.3 or
                                                    state == 'already'))
                    elif all('speech' not in o['class'] for o in rec['truth']['others']):
                        seg = tr[k_on:k_on + 50]
                        pre = tr[max(0, k_on - 10):k_on]
                        other_open.append((rec['truth']['class'], bool((seg > thr).any() and not (pre > thr).all())))
            n_on = sum(on_state.values())
            gk = sum(a for a, _ in gap_open), sum(b for _, b in gap_open)
            gate[f'{ds}|{lv}|{gname}'] = {
                'speech_onsets': n_on, 'opened_pct': pct([1] * on_state['opened'] + [0] * (n_on - on_state['opened'])),
                'already_open_pct': round(100 * on_state['already'] / n_on, 1) if n_on else None,
                'missed_pct': round(100 * on_state['missed'] / n_on, 1) if n_on else None,
                'latency_s': {'median': med(lat), 'p10': round(float(np.percentile(lat, 10)), 3) if lat else None,
                              'p90': round(float(np.percentile(lat, 90)), 3) if lat else None,
                              'within_100ms_pct': pct(abs(x) <= 0.1 for x in lat)},
                'vs_mf_onset_s': {'n': len(mf_diff), 'median': med(mf_diff),
                                  'within_50ms_pct': pct(abs(x) <= 0.05 for x in mf_diff)},
                'gap_open_pct': round(100 * gk[0] / gk[1], 2) if gk[1] else None,
                'gap_opens_per_min': round(gap_eps / gap_min, 2) if gap_min else None, 'gap_minutes': round(gap_min, 1),
                'nonspeech_onsets': len(other_open), 'nonspeech_open_pct': pct(o for _, o in other_open),
                'nonspeech_by_class': {c: [n, pct(o for cc, o in other_open if cc == c)]
                                       for c, n in Counter(c for c, _ in other_open).most_common()}}
res['gate'] = gate
res['soft_first_word'] = {}
for (lv, gname), v in soft.items():
    qs = np.percentile([x for x, _ in v], [25, 50, 75])
    res['soft_first_word'][f'{lv}|{gname}'] = {
        'mf_snr_quartile_edges_db': [round(float(q), 1) for q in qs],
        'open_within_300ms_pct_by_quartile': [pct(o for x, o in v if (i == 0 or x > qs[i - 1]) and (i == 3 or x <= qs[i]))
                                              for i in range(4)]}


# -------------------------------------------------------------------------------------------- 4, 5, 6 reads per variant
def classes_of(rec, v):
    """Batch A's classes for variant read v (GccPhat angle 1), against batch A's reference: (err, classes)."""
    x = v['angles'][0]
    if rec['dataset'] == 'starss23':
        ref = rec['truth']['sphere_deg']['gcc']
        d = rec['pair_mm'] / 1000
        err = abs(x - ref)
        if err <= 10:
            return err, []
        oth = [o['sphere_deg']['gcc'] if o['sphere_deg']['gcc'] is not None else o['deg'] for o in rec['truth']['others']]
        cl = sclass.classify(x, ref, d, oth, rec['pause_deg'], v['angles'][1:], v['track'].get('43'), rec['voice_bands'])
        return err, cl
    r2 = dict(rec, gcc=dict(rec['gcc'], angles=v['angles'], track=v['track']))
    err = abs(x - rec['truth']['deg'])
    cl = lclass.classify('gcc', x, r2, ltruth[rec['id']])
    return err, [c for c in cl if c not in ('moderate', 'outlier')]


CANON = {'aliasing partner': 'aliasing', 'aliasing_partner': 'aliasing', '0 deg pull': 'zero_pull',
         'zero_pull': 'zero_pull', 'other': 'other', 'mirror': 'mirror', 'end-fire pin': 'endfire',
         'endfire_pin': 'endfire', 'pause direction': 'pause_direction', 'pause_direction': 'pause_direction',
         'another labelled source': 'other_source', 'another_source': 'other_source',
         'truth was angle 2 or 3': 'truth_in_2_3', 'truth_was_2nd_3rd': 'truth_in_2_3', 'drift': 'drift',
         'facing': 'facing'}
KINDS = ['aliasing', 'zero_pull', 'other', 'mirror', 'endfire', 'pause_direction', 'other_source', 'truth_in_2_3',
         'drift', 'facing']

preds = defaultdict(dict)                                     # id -> 'raw' | 'dfn@raw' | 'mix@norm' ... -> read
clues = defaultdict(dict)
for p in (WORK / 'preds').glob('*.jsonl'):
    lv = p.stem.rsplit('_', 1)[1]
    for l in open(p):
        q = json.loads(l)
        for v in ('raw', 'dfn', 'mix', 'cap'):
            if q.get(v):
                preds[q['id']]['raw' if v == 'raw' else f'{v}@{lv}'] = q[v]
for p in (WORK / 'clues').glob('*.jsonl'):
    lv = p.stem.rsplit('_', 1)[1]
    for l in open(p):
        q = json.loads(l)
        clues[q['id']][lv] = {k: v for k, v in q.items() if k != 'id'}

VARIANTS = ['raw', 'mix@raw', 'cap@raw', 'dfn@raw', 'mix@norm', 'cap@norm', 'dfn@norm']
rows = defaultdict(list)                                     # (dataset, variant) -> per-read rows
out_reads = []
replica = Counter()
for rid, pv in preds.items():
    rec = recs.get(rid)
    if rec is None or 'raw' not in pv:
        continue
    ds = rec['dataset']
    b = rec['gcc']['angles'][0] if rec['gcc'] and rec['gcc'].get('angles') else None
    replica[ds, b is not None and abs(pv['raw']['angles'][0] - b) <= 0.5] += 1
    line = {'id': rid, 'dataset': ds, 'variants': {}, 'dfn_clues': clues.get(rid, {})}
    for v in VARIANTS:
        if v not in pv:
            continue
        err, cl = classes_of(rec, pv[v])
        ref = rec['truth']['sphere_deg']['gcc'] if ds == 'starss23' else rec['truth']['deg']
        line['variants'][v] = {'deg': pv[v]['angles'][0], 'err': round(err, 2), 'classes': cl}
        rows[ds, v].append({'id': rid, 'scenario': rec['scenario'], 'truth': ref, 'read': pv[v]['angles'][0],
                            'err': err, 'kinds': [CANON.get(c, c) for c in cl], 'others': [], 'ctx': {},
                            'kind': rec['truth'].get('kind', 'speech') if ds == 'starss23' else 'speech'})
    out_reads.append(line)
res['replica_check'] = {f'{ds}': {'same_as_batchA_within_0.5deg': replica[ds, True], 'differs': replica[ds, False]}
                        for ds in ('starss23', 'locata')}

res['variants'] = {}
for (ds, v), rs in rows.items():
    base = {r['id']: r for r in rows[ds, 'raw']}
    wrong = [r for r in rs if r['err'] > 10]
    moved_in = [r['id'] for r in rs if r['err'] <= 10 and base.get(r['id']) and base[r['id']]['err'] > 10]
    moved_out = [r['id'] for r in rs if r['err'] > 10 and base.get(r['id']) and base[r['id']]['err'] <= 10]
    scoped, kept, rout, sout, scen = cs.clean([dict(r) for r in rs])
    sc = cs.stats(kept)
    res['variants'][f'{ds}|{v}'] = {
        'reads': len(rs), 'over10_pct': pct(r['err'] > 10 for r in rs), 'over36_pct': pct(r['err'] > 36 for r in rs),
        'speech_over10_pct': pct(r['err'] > 10 for r in rs if r['kind'] == 'speech'),
        'kinds': {k: sum(k in r['kinds'] for r in wrong) for k in KINDS},
        'moved_in': len(moved_in), 'moved_out': len(moved_out), 'moved_in_ids': moved_in[:20],
        'moved_out_ids': moved_out[:20],
        'clean': {'kept_pct': round(100 * len(kept) / len(scoped), 1) if scoped else None,
                  'read_outliers': len(rout), 'scenarios_dropped': sum(s['dropped'] for s in scen),
                  'mean': sc['mean_err'] if sc else None, 'median': sc['median_err'] if sc else None,
                  'within10': sc['within_10_pct'] if sc else None}}

# 5: DFN pair against raw pair, read by read
res['operator'] = {}
for ds in ('starss23', 'locata'):
    for lv in LEVELS:
        d = [abs(pv[f'dfn@{lv}']['angles'][0] - pv['raw']['angles'][0]) for rid, pv in preds.items()
             if rid in recs and recs[rid]['dataset'] == ds and f'dfn@{lv}' in pv and 'raw' in pv]
        if d:
            res['operator'][f'{ds}|{lv}'] = {'reads': len(d), 'same_within_1deg_pct': pct(x <= 1 for x in d),
                                             'within_5deg_pct': pct(x <= 5 for x in d),
                                             'moved_over_10deg_pct': pct(x > 10 for x in d),
                                             'median_abs_change': med(d)}

# 6: clues against GccPhat's right / wrong (raw variant)
res['clues'] = {}
for ds in ('starss23', 'locata'):
    base = {r['id']: r for r in rows[ds, 'raw'] if r['kind'] == 'speech'}
    for lv in LEVELS:
        for c in ('lsnr_on', 'lsnr_max200', 'mask_band', 'lsnr_cap_on', 'mask_cap_band'):
            pairs = [(clues[i][lv][c], r['err'] > 10) for i, r in base.items() if lv in clues.get(i, {})]
            wrong = [x for x, w in pairs if w]
            right = [x for x, w in pairs if not w]
            # a low clue should mean a wrong read: AUC of (-clue) for wrong vs right
            res['clues'][f'{ds}|{lv}|{c}'] = {'right_median': med(right), 'wrong_median': med(wrong),
                                              'auc_low_means_wrong': auc([-x for x in wrong], [-x for x in right]),
                                              'n_right': len(right), 'n_wrong': len(wrong)}

# 4's mechanism: does the mixdown's mask dip where L and R cancel, relative to one capsule's mask? (norm level only:
# dfn_pass.py measures it from the norm-level pass)
res['mechanism'] = {}
for ds in ('starss23', 'locata'):
    m = [clues[i]['norm']['mech'] for i in clues if 'norm' in clues[i] and 'mech' in clues[i]['norm']
         and i in recs and recs[i]['dataset'] == ds]
    if not m:
        continue
    g = lambda k: [x[k] for x in m if x.get(k) is not None]
    dc = [x['mix_cancel'] - x['cap_cancel'] for x in m if x.get('mix_cancel') is not None and x.get('cap_cancel') is not None]
    da = [x['mix_add'] - x['cap_add'] for x in m if x.get('mix_add') is not None and x.get('cap_add') is not None]
    res['mechanism'][ds] = {
        'reads': len(m), 'median_cancel_share': med(g('cancel_share')),
        'median_corr_mix_vs_inphase': med(g('corr_mix_inphase')), 'median_corr_cap_vs_inphase': med(g('corr_cap_inphase')),
        'median_corr_mix_minus_cap_vs_inphase': med(g('corr_mixminuscap_inphase')),
        'share_corr_mix_minus_cap_positive': pct(x > 0 for x in g('corr_mixminuscap_inphase')),
        'mix_minus_cap_in_cancel_bands': med(dc), 'mix_minus_cap_in_add_bands': med(da),
        'mask_in_cancel_vs_add_bands': {'mix': [med(g('mix_cancel')), med(g('mix_add'))],
                                        'cap': [med(g('cap_cancel')), med(g('cap_add'))]}}

OUT.mkdir(parents=True, exist_ok=True)
(OUT / 'summary.json').write_text(json.dumps(res, indent=1))
with gzip.open(OUT / 'reads.jsonl.gz', 'wt') as fh:
    for l in out_reads:
        fh.write(json.dumps(l) + '\n')
print(json.dumps({k: res[k] for k in ('cost', 'replica_check', 'operator')}, indent=1))


# ------------------------------------------------------------------------------------------------------------ tables
def tbl(head, rows):
    o = ['| ' + ' | '.join(map(str, head)) + ' |', '|' + '---|' * len(head)]
    return '\n'.join(o + ['| ' + ' | '.join('' if v is None else str(v) for v in r) + ' |' for r in rows])


T = []
T.append('## 1. Level: lsnr (dB), median per recording and pair\n')
rows = []
for ds, d in res['level'].items():
    for k in ('speech_dbfs', 'gain_db', 'lsnr_speech_raw', 'lsnr_speech_norm', 'lsnr_gap_raw', 'lsnr_gap_norm',
              'lsnr_speech_moved_db'):
        if k in d:
            rows.append([ds, k, d[k]['median'], d[k]['p10'], d[k]['p90'], d[k]['min'], d[k]['max'], d[k]['n']])
T.append(tbl(['data', 'quantity', 'median', 'p10', 'p90', 'min', 'max', 'n'], rows))
T.append('\n## 2-3. The gates: lsnr over 0 dB (and -5, +5), and the mixdown mask over 0.2-0.5\n')
rows = []
for k, g in sorted(res['gate'].items()):
    rows.append(k.split('|') + [g['speech_onsets'], g['opened_pct'], g['already_open_pct'], g['missed_pct'],
                                g['latency_s']['median'], g['latency_s']['within_100ms_pct'],
                                g['vs_mf_onset_s']['median'], g['vs_mf_onset_s']['within_50ms_pct'],
                                g['gap_open_pct'], g['gap_opens_per_min'], g['nonspeech_onsets'],
                                g['nonspeech_open_pct']])
T.append(tbl(['data', 'level', 'gate', 'speech onsets', 'opened %', 'already open %', 'missed %', 'latency median s',
              'within 100 ms %', 'vs MF onset median s', 'within 50 ms of MF %', 'gap frames open %',
              'gap opens / min', 'non-speech onsets', 'non-speech opened %'], rows))
T.append('\n### Non-speech onsets that open the gate, by class (STARSS23): n, % opened\n')
rows = []
for k, g in sorted(res['gate'].items()):
    if k.startswith('starss23'):
        rows.append(k.split('|')[1:] + ['; '.join(f'{c} {n} / {p}' for c, (n, p) in g['nonspeech_by_class'].items())])
T.append(tbl(['level', 'gate', 'class n / % opened'], rows))
T.append('\n### Soft first words (STARSS23 pair 1-2): % of speech onsets open within 300 ms, by MF voice-over-pause '
         'quartile (softest first)\n')
T.append(tbl(['level|gate', 'quartile edges dB', 'Q1', 'Q2', 'Q3', 'Q4'],
             [[k, v['mf_snr_quartile_edges_db']] + v['open_within_300ms_pct_by_quartile']
              for k, v in sorted(res['soft_first_word'].items())]))
T.append('\n## 4-5. GccPhat by variant: raw pair (none), mask from the mixdown (mix), from capsule L (cap), DFN pair '
         '(dfn), at each level\n')
rows = []
for k, v in sorted(res['variants'].items()):
    c = v['clean']
    rows.append(k.split('|') + [v['reads'], v['over10_pct'], v['over36_pct'], v['kinds']['aliasing'],
                                v['kinds']['zero_pull'], v['kinds']['other'], v['moved_in'], v['moved_out'],
                                c['kept_pct'], c['mean'], c['median'], c['within10']])
T.append(tbl(['data', 'variant', 'reads', '>10 %', '>36 %', 'aliasing', '0 deg pull', 'other', 'moved in', 'moved out',
              'kept %', 'mean', 'median', 'within 10 %'], rows))
T.append('\n### Every class, wrong reads (>10 deg)\n')
T.append(tbl(['data|variant'] + KINDS, [[k] + [v['kinds'][c] for c in KINDS] for k, v in sorted(res['variants'].items())]))
T.append('\n## 4. Mechanism: the mask in bands where L and R cancel (in-phase ratio < 0.25) and add (> 0.75), norm level\n')
T.append(tbl(['data', 'reads', 'cancel share', 'mix: cancel / add', 'cap: cancel / add', 'mix - cap in cancel bands',
              'mix - cap in add bands', 'corr(mix - cap, in-phase)', '% positive'],
             [[ds, m['reads'], m['median_cancel_share'], m['mask_in_cancel_vs_add_bands']['mix'],
               m['mask_in_cancel_vs_add_bands']['cap'], m['mix_minus_cap_in_cancel_bands'],
               m['mix_minus_cap_in_add_bands'], m['median_corr_mix_minus_cap_vs_inphase'],
               m['share_corr_mix_minus_cap_positive']] for ds, m in res['mechanism'].items()]))
T.append('\n## 5. The shared operator: GccPhat on the DFN pair against the raw pair, read by read\n')
T.append(tbl(['data|level', 'reads', 'same within 1 deg %', 'within 5 %', 'moved > 10 deg %', 'median |change|'],
             [[k, v['reads'], v['same_within_1deg_pct'], v['within_5deg_pct'], v['moved_over_10deg_pct'],
               v['median_abs_change']] for k, v in sorted(res['operator'].items())]))
T.append('\n## 6. Clues: GccPhat\'s right reads against its wrong ones (speech onsets, raw variant). AUC: the chance a '
         'wrong read has the lower clue (0.5 = no signal)\n')
T.append(tbl(['data|level|clue', 'right median', 'wrong median', 'AUC', 'right n', 'wrong n'],
             [[k, v['right_median'], v['wrong_median'], v['auc_low_means_wrong'], v['n_right'], v['n_wrong']]
              for k, v in sorted(res['clues'].items())]))
T.append('\n## 7. Cost\n')
T.append(tbl(['audio s', 'DFN s per audio s, mixdown pass + shared operator', 'capsule pass'],
             [[res['cost']['audio_s'], res['cost']['rtf_mixdown_pass'], res['cost']['rtf_capsule_pass']]]))
(OUT / 'tables.md').write_text('\n'.join(T) + '\n')
