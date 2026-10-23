#!/usr/bin/env python3
"""Brief 8 on dEchorate: score Angle2.readSound's first reflection against the labelled first-order echoes.

Truth is harness/dechorate/truth.py's 'measured' mode, as every dEchorate score since brief 3: the direct angle from the
RIRs' own direct-path delay, each echo's angle from its image-source delay scaled by the pair's fitted factor k. An
echo's lag is its image-source path minus the direct path, over c, at the pair's centre (truth `delay_ms`).

  ONSET       readSound's onset angle under Jay's rule (harness/scoring/clean_score.py): scope |truth| <= 75, reads off
              by more than 36 deg set aside, scenarios (configuration, source, array, spacing) dropped whole as the rule
              says. Everything set aside is catalogued.
  REFLECTION  on the decided reads whose onset the rule kept (the working machinery), per configuration, spacing and
              source. The echoes scored are the reflective surfaces' (south never: it does not measurably reflect,
              results/dechorate/report.md). 'Earliest distinct' is the earliest of them more than 10 deg from the direct.
                angle   the reflection within ANGLE_HIT deg of the echo
                lag     gap_ms within LAG_HIT ms of the echo's delay
                both    angle and lag right for the same echo: the real test
              Chance: another source's decided read (same spacing) against this cut's echoes, as in the dEchorate report.
              Echoes whose delay falls outside readSound's window (MIN_GAP_MS 1 to MAX_GAP_MS 12) are reported, and a
              cut whose earliest distinct echo is outside it is scored apart, not counted as a miss.
  THE WALL    where angle and lag are both right: the true source distance r with readSound's direct angle, the echo's
              angle and gap_ms give the source and its image in the plane through the pair's axis and the source, on
              either side of the axis (two mics cannot tell which). The wall estimate is the perpendicular bisector of
              source and image. Reported: how far its reflection point (the midpoint) lands from the real surface, the
              angle between its normal and the surface's, and the estimated source-to-wall distance against the real.

usage: python3 score_dechorate.py WORK_DIR DECHORATE_DATA OUT_DIR   (WORK_DIR: truth_<room>.jsonl, sound_<room>.jsonl)
"""
import gzip
import json
import math
import statistics as st
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'dechorate'))
sys.path.insert(0, str(HERE.parent / 'scoring'))
import clean_score as cs  # noqa: E402
import truth as tmod  # noqa: E402
from dechorate_cut import C_ROOM, SURFACES  # noqa: E402
from safe_pickle import load_echo_notes  # noqa: E402

ANGLE_HIT, LAG_HIT = 10.0, 0.25
MIN_GAP, MAX_GAP = 1.0, 12.0                       # Angle2.MIN_GAP_MS, MAX_GAP_MS
ROOMS = ['000000', '000001', '000010', '000100', '001000', '010000', '011000', '011100', '011110', '011111', '020002']


def pct(v):
    return round(100 * sum(v) / len(v), 1) if v else None


def load(work):
    rows = []
    for room in ROOMS:
        tr = [json.loads(l) for l in open(work / f'truth_{room}.jsonl')]
        sd = {q['id']: q for q in map(json.loads, open(work / f'sound_{room}.jsonl'))}
        for t in tr:
            rows.append((t, sd[t['id']]))
    k = tmod.apply([t for t, _ in rows], 'measured')
    return rows, k


def in_window(e):
    return MIN_GAP <= e['delay_ms'] < MAX_GAP


def reflective(t):
    return [e for e in t['echoes'] if e['reflective']]


def distinct(t):
    return [e for e in reflective(t) if abs(e['deg'] - t['truth_deg']) > ANGLE_HIT]


def hits(q, echoes):
    """(angle, lag, both) against a list of echoes: any echo for each test; 'both' needs one echo passing both."""
    a = any(abs(q['refl']['deg'] - e['deg']) <= ANGLE_HIT for e in echoes)
    g = any(abs(q['gap_ms'] - e['delay_ms']) <= LAG_HIT for e in echoes)
    b = any(abs(q['refl']['deg'] - e['deg']) <= ANGLE_HIT and abs(q['gap_ms'] - e['delay_ms']) <= LAG_HIT for e in echoes)
    return a, g, b


def score(items, pool, rng):
    """items: (truth, read) decided; pool: same-spacing decided reads for chance. Earliest-distinct and any-reflective."""
    res = {'decided_reads': len(items)}
    for key, sel in (('earliest_distinct', lambda t: distinct(t)[:1]), ('any_reflective', reflective)):
        hit = {'angle': [], 'lag': [], 'both': []}
        ch = {'angle': [], 'lag': [], 'both': []}
        outside = 0
        for t, q in items:
            es = sel(t)
            if not es:
                continue
            if key == 'earliest_distinct' and not in_window(es[0]):
                outside += 1
                continue
            for name, v in zip(('angle', 'lag', 'both'), hits(q, es)):
                hit[name].append(v)
            while True:
                t2, q2 = pool[rng.integers(len(pool))]
                if t2['src'] != t['src']:
                    break
            for name, v in zip(('angle', 'lag', 'both'), hits(q2, es)):
                ch[name].append(v)
        res[key] = {'scored': len(hit['angle']), 'echo_outside_window': outside,
                    **{f'{n}_hit_pct': pct(hit[n]) for n in hit}, **{f'{n}_chance_pct': pct(ch[n]) for n in ch}}
    return res


def wall(t, q, k, notes):
    """Place the wall from one read whose angle and lag both hit an echo; that echo's surface is the real wall."""
    e = next(e for e in reflective(t) if abs(q['refl']['deg'] - e['deg']) <= ANGLE_HIT and abs(q['gap_ms'] - e['delay_ms']) <= LAG_HIT)
    mics, srcs = notes['mics'].T, notes['srcs'].T
    ml, mr = mics[t['mics'][0]], mics[t['mics'][1]]
    P, S = (ml + mr) / 2, srcs[t['src']]
    u = (mr - ml) / np.linalg.norm(mr - ml)
    w = (S - P) - ((S - P) @ u) * u
    v = w / np.linalg.norm(w)
    kk = k[tuple(t['mics'])]
    phys = lambda deg: math.asin(max(-1.0, min(1.0, math.sin(math.radians(deg)) / kk)))   # read angle -> physical
    r = t['dist_m']
    td, te = phys(q['onset']['deg']), phys(q['refl']['deg'])
    S_est = P + r * (math.sin(td) * u + math.cos(td) * v)
    ax, wc = SURFACES[e['surface']]
    nrm = np.zeros(3); nrm[ax] = 1.0
    true_dist = abs(S[ax] - wc)
    out = {}
    for side in (+1, -1):
        I = P + (r + C_ROOM * q['gap_ms'] / 1000) * (math.sin(te) * u + side * math.cos(te) * v)
        M, n = (S_est + I) / 2, (I - S_est) / np.linalg.norm(I - S_est)
        out[side] = {'off_wall_m': abs(M[ax] - wc), 'normal_err_deg': math.degrees(math.acos(min(1.0, abs(float(n @ nrm))))),
                     'src_wall_m': float(np.linalg.norm(I - S_est) / 2), 'true_src_wall_m': true_dist}
    best = min(out.values(), key=lambda d: d['off_wall_m'])
    return e['surface'], out[+1], best


def main():
    work, data, out = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
    out.mkdir(parents=True, exist_ok=True)
    rows, k = load(work)
    rng = np.random.default_rng(0)
    notes = load_echo_notes(data / 'dEchorate_echo_notes.pkl')
    summary = {'n_cuts': len(rows), 'errors': sum(1 for _, q in rows if 'err' in q),
               'no_sound': sum(1 for _, q in rows if q.get('sound') is None),
               'k_per_pair': {f'{a}-{b}': round(v, 3) for (a, b), v in k.items()}}

    # ---- the onset, under Jay's rule ----
    data = {'readSound onset': [dict(id=t['id'], scenario=f"{t['room']} src{t['src']} array{t['array']} {t['spacing_mm']}mm",
                                     truth=round(t['truth_deg'], 2), read=q['onset']['deg'],
                                     others=[q['refl']['deg']] if q.get('refl') else [],
                                     echoes=[e['deg'] for e in reflective(t)],
                                     ctx={'room': t['room'], 'src': t['src'], 'array': t['array'],
                                          'spacing_mm': t['spacing_mm'], 'decided': q.get('decided'),
                                          'gap_ms': q.get('gap_ms'), 'why': q.get('why')})
                                for t, q in rows if q.get('onset')]}
    summary['onset_rule'] = cs.run('dechorate_onset', data, out)['readSound onset']
    _, kept, read_out, scen_out, _ = cs.clean([dict(r) for r in data['readSound onset']])
    kept_ids = {r['id'] for r in kept}

    # ---- decided share, and why not ----
    dec = defaultdict(list)
    why = Counter()
    for t, q in rows:
        if abs(t['truth_deg']) > cs.SCOPE or not q.get('onset'):
            continue
        dec[(t['room'], t['spacing_mm'])].append(bool(q.get('decided')))
        if not q.get('decided'):
            why[q.get('why')] += 1
    summary['undecided_why'] = dict(why.most_common())
    s_ms = [q['sound']['s_ms'] for _, q in rows if q.get('sound')]
    summary['first_frame_ms_from_onset'] = {p: round(float(np.percentile(s_ms, p)), 2) for p in (5, 25, 50, 75, 95)}

    # ---- the reflection ----
    decided_kept = [(t, q) for t, q in rows if q.get('decided') and t['id'] in kept_ids]
    decided_scope = [(t, q) for t, q in rows if q.get('decided') and abs(t['truth_deg']) <= cs.SCOPE]
    pools = {sp: [(t, q) for t, q in decided_scope if t['spacing_mm'] == sp] for sp in (155, 65)}
    res = {}
    for label, items in (('kept_onsets', decided_kept), ('all_in_scope', decided_scope)):
        for sp in (155, 65):
            its = [(t, q) for t, q in items if t['spacing_mm'] == sp]
            res[f'{label}|{sp}|all'] = score(its, pools[sp], rng)
            for room in ROOMS:
                sel = [(t, q) for t, q in its if t['room'] == room]
                r = score(sel, pools[sp], rng)
                r['decided_pct'] = pct(dec[(room, sp)])
                res[f'{label}|{sp}|{room}'] = r
            for src in range(6):
                res[f'{label}|{sp}|src{src}'] = score([(t, q) for t, q in its if t['src'] == src], pools[sp], rng)
    for sp in (155, 65):
        res[f'kept_onsets|{sp}|all']['decided_pct'] = pct([v for (room, s), vs in dec.items() if s == sp for v in vs])
    summary['reflection'] = res

    # ---- which labelled echoes the 1-12 ms window cannot see ----
    win = defaultdict(lambda: Counter())
    for t, _ in rows:
        if t['spacing_mm'] != 155 or abs(t['truth_deg']) > cs.SCOPE:
            continue
        for e in reflective(t):
            win[(t['room'], e['surface'])]['inside' if in_window(e) else ('before 1 ms' if e['delay_ms'] < MIN_GAP else 'after 12 ms')] += 1
    summary['echo_window'] = {f'{r} {s}': dict(c) for (r, s), c in sorted(win.items())}
    ed_out = Counter()
    for t, _ in rows:
        d = distinct(t)
        if d and abs(t['truth_deg']) <= cs.SCOPE:
            ed_out[(t['spacing_mm'], in_window(d[0]))] += 1
    summary['earliest_distinct_in_window'] = {f'{sp}mm': {'inside': ed_out[(sp, True)], 'outside': ed_out[(sp, False)]}
                                              for sp in (155, 65)}

    # ---- the wall ----
    walls = defaultdict(list)
    for t, q in decided_kept:
        if hits(q, reflective(t))[2]:
            surf, front, best = wall(t, q, k, notes)
            walls[(t['spacing_mm'], surf)].append((front, best))
    wsum = {}
    for (sp, surf), v in sorted(walls.items()):
        f = lambda key, which: round(st.median(x[which][key] for x in v), 2)
        wsum[f'{sp}mm {surf}'] = {
            'n': len(v),
            'front_side': {'off_wall_m': f('off_wall_m', 0), 'normal_err_deg': f('normal_err_deg', 0),
                           'src_wall_m': f('src_wall_m', 0)},
            'better_side': {'off_wall_m': f('off_wall_m', 1), 'normal_err_deg': f('normal_err_deg', 1),
                            'src_wall_m': f('src_wall_m', 1),
                            'within_0.25m': pct([x[1]['off_wall_m'] <= 0.25 for x in v])},
            'true_src_wall_m': round(st.median(x[0]['true_src_wall_m'] for x in v), 2)}
    summary['wall'] = wsum
    (out / 'dechorate_summary.json').write_text(json.dumps(summary, indent=1))

    # ---- the reads, without audio, for anyone re-scoring ----
    with gzip.open(out / 'dechorate_reads.jsonl.gz', 'wt') as fh:
        for t, q in rows:
            fh.write(json.dumps({'id': t['id'], 'truth_deg': round(t['truth_deg'], 2), 'kept': t['id'] in kept_ids,
                                 **{kk: q.get(kk) for kk in ('decided', 'onset', 'refl', 'gap_ms', 'why', 'sound')}}) + '\n')
    print(json.dumps({kk: v for kk, v in summary.items() if kk not in ('reflection', 'echo_window')}, indent=1)[:3000])


if __name__ == '__main__':
    main()
