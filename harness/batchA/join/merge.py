#!/usr/bin/env python3
"""A record set taking GccPhat's read from one scheme set and Angle2's from another, read for read (same ids, same
truth): brief 11's final schemes, when each scheme's best version comes from a different copy.
usage: merge.py <gcc source reads> <a2 source reads> <out reads>    (.jsonl or .jsonl.gz, in and out)"""
import gzip
import json
import sys
from pathlib import Path


def lines(p):
    return gzip.open(p, 'rt') if p.endswith('.gz') else open(p)


g_src, a_src, outp = sys.argv[1:4]
A = {}
for l in lines(a_src):
    r = json.loads(l)
    A[r['id']] = r['a2']
out = gzip.open(outp, 'wt') if outp.endswith('.gz') else open(outp, 'w')
n = 0
for l in lines(g_src):
    r = json.loads(l)
    r['a2'] = A[r['id']]
    out.write(json.dumps(r) + '\n')
    n += 1
out.close()
print(n, 'reads merged ->', Path(outp).name)
