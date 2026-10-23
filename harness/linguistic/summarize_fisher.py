#!/usr/bin/env python3
"""Brief 18 step 2's table: the Fisher model's text-only runs (run_fisher.sh) beside the stand-ins, every meeting and
transcript, plus medians, the timing, and the failures set aside.

A run "fails outright" when the model leaves more than a quarter of its passes untagged (it stopped doing the task) or
its per-window score is below the echo stand-in's (it did worse than no information). Failures are listed, kept out of
the medians, and catalogued by kind.
usage: summarize_fisher.py <fisher out dir> <out json>
"""
import json
import statistics as st
import sys
from collections import defaultdict
from pathlib import Path

KEYS = ('words', 'per_window_pct', 'whole_meeting_pct', 'baseline_most_talkative_pct', 'speakers_present',
        'speakers_invented', 'splits', 'merges', 'short_replies_pct', 'overlapped_pct', 'passes', 'untagged_passes',
        'seconds_per_pass', 'words_per_pass')


def main():
    src, outp = Path(sys.argv[1]), Path(sys.argv[2])
    runs = defaultdict(dict)
    for f in sorted(src.glob('*.json')):
        parts = f.stem.split('.')
        if len(parts) != 3:
            continue
        m, t, model = parts
        d = json.loads(f.read_text())
        runs[(m, t)][model] = {k: d.get(k) for k in KEYS}
    table, failed = [], []
    for (m, t), r in sorted(runs.items()):
        if 'fisher' not in r:
            continue
        f, e = r['fisher'], r.get('echo', {})
        why = []
        if f['passes'] and f['untagged_passes'] / f['passes'] > 0.25:
            why.append('untagged passes')
        if e.get('per_window_pct') is not None and f['per_window_pct'] is not None and f['per_window_pct'] < e['per_window_pct']:
            why.append('below echo per window')
        row = {'meeting': m, 'transcript': t, **{f'{model}_{k}': v.get(k) for model, v in r.items() for k in ('per_window_pct', 'whole_meeting_pct')},
               **{k: f[k] for k in KEYS}, 'failed': why}
        (failed if why else table).append(row)
    med = {}
    for t in sorted({r['transcript'] for r in table}):
        rows = [r for r in table if r['transcript'] == t]
        med[t] = {k: round(st.median(r[k] for r in rows if r.get(k) is not None), 1)
                  for k in ('fisher_per_window_pct', 'oracle_per_window_pct', 'echo_per_window_pct', 'fisher_whole_meeting_pct',
                            'oracle_whole_meeting_pct', 'echo_whole_meeting_pct', 'baseline_most_talkative_pct', 'speakers_invented',
                            'speakers_present', 'splits', 'merges', 'short_replies_pct', 'overlapped_pct', 'seconds_per_pass',
                            'words_per_pass', 'untagged_passes')
                  if any(r.get(k) is not None for r in rows)}
        med[t]['runs'] = len(rows)
    res = {'medians_by_transcript': med, 'runs': table, 'failed': failed}
    real = {}
    for f in sorted(src.glob('*.fisher_realclock.json')):
        d = json.loads(f.read_text())
        real[f.stem] = {k: d.get(k) for k in KEYS + ('clock_behind_at_end_s',)}
    res['real_clock'] = real
    Path(outp).write_text(json.dumps(res, indent=1))
    print(json.dumps(med, indent=1))
    print('failed:', [(r['meeting'], r['transcript'], r['failed']) for r in failed])


if __name__ == '__main__':
    main()
