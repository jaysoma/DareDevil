#!/usr/bin/env python3
"""Tables (markdown), the curve plot and the committable index of the set, from evaluate.py's outputs.

usage: python3 report_tables.py SET_DIR SCORES_DIR EVAL_DIR OUT_DIR
Writes OUT_DIR/tables.md, OUT_DIR/curves.png, OUT_DIR/set_index.jsonl (no third-party text: sources, positions and
SLURP ids; only the generated hard negatives are written out), and copies the summaries and per-phrase scores.
"""
import json
import shutil
import sys
from pathlib import Path

DEVICES = ('car', 'kitchen', 'watch', 'general')
STREAMS = ('ami', 'calls', 'lyrics', 'monologue')
NAMES = {'keyword': 'keyword spotting', 'shape_ngram': 'shape only (n-gram)', 'contrast_ngram': "shape and contrast (Jay's), n-gram",
         'contrast_ngram_past': "shape and contrast, n-gram, past context only", 'shape_embed': 'shape only (MiniLM)',
         'contrast_embed': "shape and contrast (Jay's), MiniLM", 'contrast_embed_past': 'shape and contrast, MiniLM, past context only',
         'llm_qwen0.5b': 'general model asked (Qwen2.5-0.5B)', 'llm_qwen1.5b': 'general model asked (Qwen2.5-1.5B)'}


def main():
    setd, scd, evd, out = (Path(a) for a in sys.argv[1:5])
    out.mkdir(parents=True, exist_ok=True)
    S = json.load(open(evd / 'summary.json'))
    FA = json.load(open(evd / 'false_accepts.json'))
    cost = json.load(open(scd / 'cost.json'))
    ms = [m for m in NAMES if m in S]
    L = []
    p = L.append
    p('## Pooled over the four devices\n')
    p('| method | model size | time per phrase | mean hit rate, 0-60 FA/h | hits at 1 FA/h | hits at 10 FA/h | '
      'hard negatives accepted at 10 FA/h: to a person / subject | foreign-phrase control accepted |')
    p('|---|---|---|---|---|---|---|---|')
    for m in ms:
        a, c = S[m]['all'], cost.get(m, {})
        mb = c.get('model_bytes')
        size = f'{mb / 1e6:.1f} MB' if mb and mb > 1e5 else (f'{mb} bytes' if mb else '-')
        t = c.get('seconds_per_phrase')
        tt = f'{t * 1000:.2f} ms' if t is not None else '-'
        h1 = (a['at_1fa'] or {}).get('hit_pct')
        a10 = a['at_10fa'] or {}
        hk = a10.get('hard_accept_pct', {})
        p(f"| {NAMES[m]} | {size} | {tt} | {100 * a['auc_0_60fa']:.0f}% | {h1}% | {a10.get('hit_pct')}% | "
          f"{hk.get('to_person')}% / {hk.get('subject')}% | {hk.get('foreign')}% |")
    if any(k.startswith('llm_') for k in S):
        p('\nThe general model\'s own answer (its most likely line, unless it says none):\n')
        for m in ms:
            if m.startswith('llm_') and 'own_answer' in S[m]:
                o = S[m]['own_answer']
                p(f"- {NAMES[m]}: finds {o['hit_pct']}% of instructions at {o['fa_per_hour']} false accepts per hour; "
                  f"accepts {o['hard_accept_pct'].get('to_person')}% of to-a-person and {o['hard_accept_pct'].get('subject')}% "
                  f"of subject hard negatives, and {o['hard_accept_pct'].get('foreign')}% of the foreign-phrase control.")
    for tgt in ('1', '10'):
        p(f'\n## Per device, at {tgt} false accept(s) per hour\n')
        p('| method | device | hits | ami | calls (speakerphone) | lyrics | monologue | hard: to a person | hard: subject | foreign control |')
        p('|---|---|---|---|---|---|---|---|---|---|')
        for m in ms:
            for d in DEVICES:
                a = S[m][d][f'at_{tgt}fa']
                if not a:
                    p(f'| {NAMES[m]} | {d} | (never reaches {tgt}/h) | | | | | | |'); continue
                bs = a['by_stream']
                cell = lambda s: f"{bs[s]['hit_pct']}% ({bs[s]['fa_per_hour']}/h)"
                hk = a['hard_accept_pct']
                p(f"| {NAMES[m]} | {d} | {a['hit_pct']}% | {cell('ami')} | {cell('calls')} | {cell('lyrics')} | "
                  f"{cell('monologue')} | {hk.get('to_person')}% | {hk.get('subject')}% | {hk.get('foreign')}% |")
    p('\n(Each stream cell: hits there, and that stream\'s own false accepts per hour at the device\'s threshold.)\n')
    p('## Failing conditions (best method under 50% hits at 10 FA/h)\n')
    if S['failing_conditions']:
        for k, v in S['failing_conditions'].items():
            p(f"- {k}: best {v['best_method']} at {v['best_hit_pct']}%. Instructions there include: "
              + '; '.join(f'"{x}"' for x in v['instructions'][:4]))
    else:
        p('None.')
    p('\n## False accepts at 10 per hour, by kind\n')
    p('| method | device | false accepts | short (<= 2 words) | device vocabulary | request shape | question | other |')
    p('|---|---|---|---|---|---|---|---|')
    for m in ms:
        for d in DEVICES:
            c = FA.get(f'{m}|{d}')
            if not c:
                continue
            k = c['kinds']
            p(f"| {NAMES[m]} | {d} | {c['false_accepts']} | {k.get('short', 0)} | {k.get('device vocabulary', 0)} | "
              f"{k.get('request shape', 0)} | {k.get('question', 0)} | {k.get('other', 0)} |")
    (out / 'tables.md').write_text('\n'.join(L) + '\n')

    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    C = json.load(open(evd / 'curves.json'))
    fig, axs = plt.subplots(1, 5, figsize=(22, 4.4), sharey=True)
    for ax, d in zip(axs, DEVICES + ('all',)):
        for m in ms:
            c = C.get(f'{m}|{d}')
            if c:
                ax.plot(c['fa_per_hour'], c['hit'], label=NAMES[m], lw=1.6)
        ax.set_xscale('symlog', linthresh=1); ax.set_xlim(0, 300); ax.set_ylim(0, 1)
        ax.axvline(1, color='0.8', lw=0.8); ax.axvline(10, color='0.8', lw=0.8)
        ax.set_title(d if d != 'all' else 'all devices'); ax.set_xlabel('false accepts per hour of other speech')
    axs[0].set_ylabel('share of instructions found')
    axs[-1].legend(fontsize=7, loc='lower right')
    fig.tight_layout(); fig.savefig(out / 'curves.png', dpi=110)

    with open(out / 'set_index.jsonl', 'w') as fh:
        for r in map(json.loads, open(setd / 'set.jsonl')):
            sp = r['phrases'][r['pos']]
            fh.write(json.dumps({'id': r['id'], 'kind': r['kind'], 'device': r['device'], 'stream': r['stream'],
                                 'source': r['source'], 'start': r['start'], 'pos': r['pos'],
                                 'slurp_id': sp.get('slurp_id'), 'intent': sp.get('intent'),
                                 'generated_text': sp['text'] if sp.get('generated') else None}) + '\n')
    for f in ('summary.json', 'false_accepts.json', 'curves.json'):
        shutil.copy(evd / f, out / f)
    for f in list(scd.glob('scores_*.jsonl')) + [scd / 'cost.json', scd / 'keywords.json']:
        shutil.copy(f, out / f.name)
    print((out / 'tables.md').read_text()[:3000])


if __name__ == '__main__':
    main()
