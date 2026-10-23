#!/usr/bin/env python3
"""Brief 11's fix, in copies of src/schemes/ (which stays as it is): each onset read from its own first milliseconds.

Jay, 2026-10-23: "Don't outsmart it, just render it." No vetoes, no separation. The one change tested is WHEN a read is
made: from the onset's own start, so a sound that starts later can't outvote it, and one that started earlier was read
at its own onset and isn't summed in here.

  onset100   GccPhat locks at the first 100 ms (LOCK_S 0.5 -> 0.1: the frames starting in the first 100 ms, about
             140 ms of audio), not the half second. Angle2 scans from the handed onset (U_BEFORE_MS 100 -> 0), so a
             sound that began before this onset can't win this onset's race.
  onset250   GccPhat locks at 250 ms (LOCK_S 0.25). Angle2 unchanged.

Each copy is the shipped file with only those constants changed (checked: each replacement must match exactly once).
usage: python3 harness/fixes/make_copies.py      (writes harness/fixes/<copy>/GccPhat.mjs and Angle2.mjs)
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / 'src' / 'schemes'
EDITS = {
    'onset100': {'GccPhat.mjs': [('export const LOCK_S = 0.5;      // the half second: every frame that STARTS inside it, 47 of them (533 ms of audio)',
                                  'export const LOCK_S = 0.1;      // brief 11 copy: the frames starting in the onset\'s own first 100 ms (shipped: 0.5)')],
                 'Angle2.mjs': [('U_BEFORE_MS = 100,', 'U_BEFORE_MS = 0,')]},
    'onset250': {'GccPhat.mjs': [('export const LOCK_S = 0.5;      // the half second: every frame that STARTS inside it, 47 of them (533 ms of audio)',
                                  'export const LOCK_S = 0.25;     // brief 11 copy: the frames starting in the onset\'s first 250 ms (shipped: 0.5)')],
                 'Angle2.mjs': []},
}

for name, files in EDITS.items():
    out = ROOT / 'harness' / 'fixes' / name
    out.mkdir(parents=True, exist_ok=True)
    for f, reps in files.items():
        s = (SRC / f).read_text()
        for old, new in reps:
            assert s.count(old) == 1, (name, f, old)
            s = s.replace(old, new)
        (out / f).write_text(s)
    print(name, 'written')
