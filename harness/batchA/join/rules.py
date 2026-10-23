"""Brief 11 step 3: commit or dim, with the simplest rule on the clues known at the moment of the read.

A rule is one or two thresholds. Each clue has the direction physics expects (a taller, more decided peak commits; a read
sitting on a directional pause dims), so a threshold says how far, never which way:
  share >= t, margin >= t, votes >= t, width <= t, early_vs_lock <= t, snr_* >= t, agree <= t (the two schemes within t
  deg), not a tie, a2_edge, and the lab's pause rule: dim when the read is within 10 deg of a pause read whose share is
  >= t.

THE CRITERION, fixed before any result was seen: on the dataset the rule is chosen on, the rule with the highest share
within 10 deg among the reads it commits, while committing at least MIN_COMMIT of them. A tie goes to the rule with
fewer thresholds. Thresholds are tried at that dataset's own deciles of the clue. The rule is then applied unchanged to
the other dataset.
"""
import itertools

MIN_COMMIT = 0.5
SINGLE = {
    'share': ('>=',), 'margin': ('>=',), 'votes': ('>=',), 'width': ('<=',), 'early_vs_lock': ('<=',),
    'snr_mf': ('>=',), 'snr_hf1': ('>=',), 'snr_hf2': ('>=',), 'agree': ('<=',),
}


def qs(vals, k=10):
    v = sorted(x for x in vals if x is not None)
    if not v:
        return []
    return sorted({round(v[min(len(v) - 1, int(len(v) * i / k))], 4) for i in range(1, k)})


def make(clue, op, t):
    if clue == 'tie':
        return {'name': 'not a tie', 'parts': [('tie', '==', 0.0)]}
    if clue == 'a2_edge':
        return {'name': 'Angle2 onset on an edge', 'parts': [('a2_edge', '==', 1.0)]}
    if clue == 'pause':
        return {'name': f'not on a pause read of share >= {t}', 'parts': [('pause', 'pause', t)]}
    return {'name': f'{clue} {op} {t}', 'parts': [(clue, op, t)]}


def commits(rule, r):
    c = r['clues']
    for clue, op, t in rule['parts']:
        if op == 'pause':
            if c['pause_share'] is not None and c['read_to_pause'] is not None and c['pause_share'] >= t and c['read_to_pause'] <= 10:
                return False
            continue
        v = c.get(clue)
        if v is None:
            return False
        if op == '>=' and not v >= t: return False
        if op == '<=' and not v <= t: return False
        if op == '==' and v != t: return False
    return True


def both(a, b):
    return {'name': f"{a['name']} and {b['name']}", 'parts': a['parts'] + b['parts']}


def evaluate(rule, rows):
    n = len(rows)
    com = [r for r in rows if commits(rule, r)]
    ok = sum(r['err'] <= 10 for r in com)
    dim = [r for r in rows if not commits(rule, r)]
    return {'rule': rule['name'], 'reads': n, 'committed_pct': round(100 * len(com) / n, 1) if n else None,
            'within10_committed_pct': round(100 * ok / len(com), 1) if com else None,
            'over36_committed_pct': round(100 * sum(r['err'] > 36 for r in com) / len(com), 1) if com else None,
            'within10_dimmed_pct': round(100 * sum(r['err'] <= 10 for r in dim) / len(dim), 1) if dim else None,
            'right_reads_kept_pct': round(100 * ok / max(sum(r['err'] <= 10 for r in rows), 1), 1)}


def candidates(rows):
    singles = []
    for clue, (op,) in SINGLE.items():
        for t in qs([r['clues'][clue] for r in rows]):
            singles.append(make(clue, op, t))
    singles += [make('tie', None, None), make('a2_edge', None, None)] + [make('pause', None, t) for t in (0.3, 0.4, 0.5, 0.6, 0.7, 0.8)]
    return singles


def choose(rows):
    """The best rule on these rows under the criterion: the best single rule, and the best pair of single rules."""
    singles = candidates(rows)
    scored = []
    for r in singles:
        e = evaluate(r, rows)
        if e['committed_pct'] is not None and e['committed_pct'] >= 100 * MIN_COMMIT:
            scored.append((e['within10_committed_pct'], -1, r, e))
    best1 = max(scored, key=lambda s: (s[0], s[1]))
    # pairs: the 40 best singles (by the criterion, any commit share) combined two at a time
    pool = sorted(((evaluate(r, rows)['within10_committed_pct'] or 0, r) for r in singles), key=lambda s: -s[0])
    pool = [r for _, r in pool if not r['parts'][0][0] in ()][:40]
    best2 = None
    for a, b in itertools.combinations(pool, 2):
        if a['parts'][0][0] == b['parts'][0][0]:
            continue
        rr = both(a, b)
        e = evaluate(rr, rows)
        if e['committed_pct'] is not None and e['committed_pct'] >= 100 * MIN_COMMIT:
            if best2 is None or e['within10_committed_pct'] > best2[0]:
                best2 = (e['within10_committed_pct'], -2, rr, e)
    pick = best1 if best2 is None or best1[0] >= best2[0] else best2
    return pick[2], {'best_single': best1[3], 'best_pair': best2[3] if best2 else None, 'chosen': pick[3]}


def curve(clue, op, rows, rule_parts=None, steps=30):
    """Committed share against the share within 10 deg among them, sweeping one clue's threshold (the plot)."""
    v = sorted(r['clues'][clue] for r in rows if r['clues'][clue] is not None)
    pts = []
    for i in range(steps + 1):
        t = v[min(len(v) - 1, int((len(v) - 1) * i / steps))] if v else None
        rule = {'name': '', 'parts': [(clue, op, t)]}
        e = evaluate(rule, rows)
        if e['committed_pct']:
            pts.append((e['committed_pct'], e['within10_committed_pct'], t))
    return pts
