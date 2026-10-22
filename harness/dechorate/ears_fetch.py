#!/usr/bin/env python3
"""Pull a few clean (anechoic, 48 kHz) read sentences from EARS (github.com/facebookresearch/ears_dataset) without
downloading whole speaker zips: the zip's directory and the chosen members are fetched with HTTP range requests.

usage: python3 ears_fetch.py OUT_DIR [--speakers p001 p002 ...] [--per 4]
"""
import argparse
import io
import urllib.request
import zipfile
from pathlib import Path

URL = 'https://github.com/facebookresearch/ears_dataset/releases/download/dataset/{}.zip'
# two men, two women by speaker_statistics.json; American English natives where available
DEFAULT = ['p002', 'p003', 'p004', 'p007']


class RangeFile(io.RawIOBase):
    """A read-only, seekable view of a remote file, fetched in ranges."""

    def __init__(self, url):
        req = urllib.request.Request(url, method='HEAD')
        with urllib.request.urlopen(req) as r:
            self.url, self.size = r.geturl(), int(r.headers['Content-Length'])
        self.pos = 0

    def seekable(self):
        return True

    def readable(self):
        return True

    def tell(self):
        return self.pos

    def seek(self, off, whence=0):
        self.pos = {0: off, 1: self.pos + off, 2: self.size + off}[whence]
        return self.pos

    def readinto(self, b):
        n = min(len(b), self.size - self.pos)
        if n <= 0:
            return 0
        req = urllib.request.Request(self.url, headers={'Range': f'bytes={self.pos}-{self.pos + n - 1}'})
        with urllib.request.urlopen(req) as r:
            data = r.read()
        b[:len(data)] = data
        self.pos += len(data)
        return len(data)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('out')
    ap.add_argument('--speakers', nargs='+', default=DEFAULT)
    ap.add_argument('--per', type=int, default=4)
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    for spk in a.speakers:
        zf = zipfile.ZipFile(io.BufferedReader(RangeFile(URL.format(spk)), buffer_size=1 << 20))
        names = sorted(n for n in zf.namelist() if 'sentences' in n and n.endswith('_regular.wav'))[:a.per]
        for n in names:
            dst = out / f'{spk}_{Path(n).name}'
            if not dst.exists():
                dst.write_bytes(zf.read(n))
            print(dst)


if __name__ == '__main__':
    main()
