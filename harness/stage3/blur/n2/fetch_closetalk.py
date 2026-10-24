#!/usr/bin/env python3
"""Brief N2: fetch LOCATA eval's close-talk recordings (tasks 3 and 4, dicit/audio_source_<talker>.wav), which
batchA/locata/locata_fetch.py skipped. Range requests into eval.zip on Zenodo (record 3630471), as locata_fetch does.
Dev's are already on Jay's box beside each pair48.wav.
    python3 fetch_closetalk.py OUT_DIR    (OUT_DIR holds eval/task<n>/recording<m>/dicit/)"""
import io, re, sys, zipfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'dechorate'))
from ears_fetch import RangeFile
URL = 'https://zenodo.org/api/records/3630471/files/eval.zip/content'
out = Path(sys.argv[1]); pat = re.compile(r'^eval/task[34]/recording\d+/dicit/audio_source_talker\d+\.wav$')
z = zipfile.ZipFile(io.BufferedReader(RangeFile(URL), buffer_size=8 << 20))
for i in z.infolist():
    if not pat.match(i.filename): continue
    dst = out / i.filename
    if dst.exists() and dst.stat().st_size == i.file_size: print('have', i.filename); continue
    tmp = dst.with_suffix('.part')
    with z.open(i) as src, open(tmp, 'wb') as fh:
        while b := src.read(8 << 20): fh.write(b)
    tmp.replace(dst); print('got', i.filename, flush=True)
