#!/usr/bin/env python3
"""Cause 4's band copies: GccPhat.mjs and Angle2.mjs with the analysis band's LOW EDGE moved to 300, 1100 or 2000 Hz.
Copies only; src/schemes/ is never touched. Defaults: GccPhat 300 Hz, Angle2 1100 Hz, so lo300 changes Angle2 alone,
lo1100 changes GccPhat alone, and lo2000 changes both.

GccPhat's band is LO_HZ alone. Angle2's is LO_HZ (its scan bins) plus a hard-coded scipy butter(6, [1100, 8000])
bandpass (SOS), so the SOS is regenerated with the same call at the new edge.

    python3 variants.py <src/schemes> <out dir>    -> <out>/lo300/, lo1100/, lo2000/
"""
import re
import sys
from pathlib import Path

from scipy.signal import butter

EDGES = [300, 1100, 2000]


def sos_js(lo):
    s = butter(6, [lo, 8000], 'bandpass', fs=48000, output='sos').tolist()
    rows = ['[' + ', '.join(repr(float(v)) for v in r) + ']' for r in s]
    return 'const SOS = [' + ',\n  '.join(rows) + '];'


def main():
    src, out = Path(sys.argv[1]), Path(sys.argv[2])
    gcc, a2 = (src / 'GccPhat.mjs').read_text(), (src / 'Angle2.mjs').read_text()
    for lo in EDGES:
        d = out / f'lo{lo}'
        d.mkdir(parents=True, exist_ok=True)
        note = f'// BAND COPY for harness/batchA_lab (cause 4): the analysis band starts at {lo} Hz. Not the shipped scheme.\n'
        g, n1 = re.subn(r'LO_HZ = \d+,', f'LO_HZ = {lo},', gcc, count=1)
        a, n2 = re.subn(r'LO_HZ = \d+,', f'LO_HZ = {lo},', a2, count=1)
        a, n3 = re.subn(r'const SOS = \[\[.*?\]\];', sos_js(lo), a, count=1, flags=re.S)
        assert n1 == n2 == n3 == 1, (n1, n2, n3)
        (d / 'GccPhat.mjs').write_text(note + g)
        (d / 'Angle2.mjs').write_text(note + a)
        print(d)


if __name__ == '__main__':
    main()
