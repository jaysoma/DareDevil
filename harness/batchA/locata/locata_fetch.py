#!/usr/bin/env python3
"""Fetch only the LOCATA files batch A needs (tasks 3 and 4, DICIT array) out of dev.zip and eval.zip on Zenodo
(https://zenodo.org/records/3630471), with HTTP range requests: the zips are 6.2 and 13 GB, the files used about 4 GB.
The talkers' close-talk recordings (audio_source_*.wav) are not needed and are skipped.

usage: python3 locata_fetch.py OUT_DIR [--sets dev eval] [--tasks 3 4] [--threads 6]
"""
import argparse
import io
import re
import sys
import zipfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'dechorate'))
from ears_fetch import RangeFile  # noqa: E402

URL = 'https://zenodo.org/api/records/3630471/files/{}.zip/content'


def open_zip(name):
    return zipfile.ZipFile(io.BufferedReader(RangeFile(URL.format(name)), buffer_size=8 << 20))


def fetch(name, member, out):
    dst = out / member
    if dst.exists() and dst.stat().st_size == member_size[(name, member)]:
        return f'have {member}'
    dst.parent.mkdir(parents=True, exist_ok=True)
    tmp = dst.with_suffix(dst.suffix + '.part')
    for attempt in range(5):
        try:
            with open_zip(name).open(member) as src, open(tmp, 'wb') as fh:
                while True:
                    b = src.read(8 << 20)
                    if not b:
                        break
                    fh.write(b)
            tmp.rename(dst)
            return f'got {member}'
        except Exception as e:  # a reset connection: start the member again
            err = e
    return f'FAILED {member}: {err}'


member_size = {}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('out')
    ap.add_argument('--sets', nargs='+', default=['dev', 'eval'])
    ap.add_argument('--tasks', nargs='+', default=['3', '4'])
    ap.add_argument('--threads', type=int, default=6)
    a = ap.parse_args()
    out = Path(a.out)
    pat = re.compile(rf"^(dev|eval)/task({'|'.join(a.tasks)})/recording\d+/dicit/(?!audio_source_)[^/]+$")
    jobs = []
    for name in a.sets:
        for i in open_zip(name).infolist():
            if pat.match(i.filename):
                member_size[(name, i.filename)] = i.file_size
                jobs.append((name, i.filename))
    jobs.sort(key=lambda j: -member_size[j])               # big audio first, so the long ones overlap
    print(f'{len(jobs)} files, {sum(member_size.values()) / 1e9:.2f} GB uncompressed', flush=True)
    with ThreadPoolExecutor(a.threads) as ex:
        for r in ex.map(lambda j: fetch(j[0], j[1], out), jobs):
            print(r, flush=True)


if __name__ == '__main__':
    main()
