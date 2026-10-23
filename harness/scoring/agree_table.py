#!/usr/bin/env python3
"""GccPhat's error on STARSS23 single-talker onsets, split by whether the two schemes agree and whether Angle2 found a
clean rising onset (brief 2's `edge`). Reads the committed predictions after the Angle2 fix; no audio needed.

Raw error against the geometric angle, before Jay's cleaning rule, so the shares are of every read both schemes made.
Caution from brief 13's lab (results/batchA/lab/report.md, section 3): under a steady directional source or a
common-mode signal both schemes lock onto the same wrong direction, so agreement is a candidate clue, not a rule.

    python3 harness/scoring/agree_table.py <repo root> <out.json>
"""
import json
import statistics as st
import sys
from pathlib import Path

AGREE_DEG = 5.0


def main():
    root, out = Path(sys.argv[1]), Path(sys.argv[2])
    rows = []
    for p in ('12', '13', '14', '23', '24', '34'):
        truth = [json.loads(l) for l in open(root / f'results/starss23/truth/truth_{p}.jsonl')]
        pred = [json.loads(l) for l in open(root / f'results/starss23/after_angle2_fix/preds_{p}.jsonl')]
        for t, a in zip(truth, pred):
            assert t['file'] == a['file'] and t['onset_s'] == a['onset_s']
            if a.get('gcc') and a.get('a2'):
                rows.append((t['truth_lateral'], a['gcc'][0], a['a2'][0], bool(a.get('a2_edge'))))
    n = len(rows)

    def summ(sel):
        e = [abs(g - t) for t, g, _, _ in sel]
        return {'reads': len(sel), 'share_pct': round(100 * len(sel) / n, 1), 'gcc_median_err': round(st.median(e), 1),
                'gcc_within_10_pct': round(100 * sum(x <= 10 for x in e) / len(e), 1)}

    agree = lambda r: abs(r[1] - r[2]) <= AGREE_DEG
    res = {'reads_both_schemes': n, 'agree_deg': AGREE_DEG,
           'agree_and_edge': summ([r for r in rows if agree(r) and r[3]]),
           'agree': summ([r for r in rows if agree(r)]),
           'disagree': summ([r for r in rows if not agree(r)]),
           'no_edge': summ([r for r in rows if not r[3]]),
           'all': summ(rows)}
    out.write_text(json.dumps(res, indent=1))
    print(json.dumps(res, indent=1))


if __name__ == '__main__':
    main()
