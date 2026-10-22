"""Lean per room config, spacing and true angle: the signed error along the truth's side (negative = read nearer 0),
median over the utterances, for GccPhat's angle 1 and Angle2.readUtterance's onset. Prints a markdown table per scheme
and writes every number to <work>/score.json. usage: python score.py <work dir> [configs...]"""
import glob, json, os, sys
import numpy as np
W = sys.argv[1]
rows = {}
for p in sorted(glob.glob(f'{W}/preds/*.jsonl')):
    name = os.path.basename(p)[:-6]
    cfg, d = name.rsplit('_', 1)
    if len(sys.argv) > 2 and cfg not in sys.argv[2:]: continue
    truth = {}
    for l in open(f'{W}/cuts/{name}.jsonl'):
        c = json.loads(l); truth[c['file'] + '@' + str(c['truth_lateral'])] = c['truth_lateral']
    preds = [json.loads(l) for l in open(p)]
    cuts = [json.loads(l)['truth_lateral'] for l in open(f'{W}/cuts/{name}.jsonl')]
    by = {}
    for t, q in zip(cuts, preds):
        for s, v in (('gcc', q.get('gcc') and q['gcc'][0]), ('a2', q.get('a2') and q['a2'][0])):
            if v is None: continue
            by.setdefault((s, t), []).append((v - t) * (1 if t >= 0 else -1) if t else abs(v))
    rows[(cfg, d)] = {f'{s}|{t:g}': float(np.median(e)) for (s, t), e in by.items()}
    rows[(cfg, d)].update({f'{s}|n': sum(len(e) for (ss, _), e in by.items() if ss == s) for s in ('gcc', 'a2')})
angles = [10, 20, 30, 40, 50, 60]
for s, label in (('a2', 'Angle2 onset'), ('gcc', 'GccPhat angle 1')):
    print(f'\n{label}: median lean (deg, - = nearer 0), mean of +-angle')
    print('| config | mm | ' + ' | '.join(f'{a}' for a in angles) + ' |'); print('|---|---|' + '---|' * len(angles))
    for (cfg, d), r in rows.items():
        v = [np.mean([r.get(f'{s}|{a}', np.nan), r.get(f'{s}|{-a}', np.nan)]) for a in angles]
        print(f'| {cfg} | {float(d) * 1000:.0f} | ' + ' | '.join(f'{x:+.1f}' for x in v) + ' |')
json.dump({f'{c}_{d}': r for (c, d), r in rows.items()}, open(f'{W}/score.json', 'w'), indent=1)
