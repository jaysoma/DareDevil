#!/usr/bin/env python3
"""Brief 18 step 1, third condition: AMI's far-field audio for a meeting, rebuilt from the Hugging Face copy.

The AMI host's own audio wasn't reachable from this session; edinburghcstr/ami (config sdm, the single distant
microphone, Array1-01) holds the same channel cut into utterances, each with its begin and end time in the meeting.
Each utterance's audio goes back at its begin time. Where utterances overlap they hold the same far-field channel, so
a later one simply overwrites; between utterances (nobody transcribed speaking) the rebuilt audio is silence, not the
room. That is the one difference from the real recording.
usage: sdm_rebuild.py <dir of sdm test parquet files> <out dir> --until-s 600 MEETING ...
       writes <out>/<meeting>.sdm.wav (16 kHz mono)
"""
import argparse
import io
from pathlib import Path

import numpy as np
import pyarrow.parquet as pq
import soundfile as sf


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('src')
    ap.add_argument('out')
    ap.add_argument('--until-s', type=float, default=600)
    ap.add_argument('meetings', nargs='+')
    a = ap.parse_args()
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    want = set(a.meetings)
    buf, sr_of, n_seg = {}, {}, {}
    for f in sorted(Path(a.src).glob('*.parquet')):
        pf = pq.ParquetFile(f)
        for b in pf.iter_batches(batch_size=256, columns=['meeting_id', 'audio', 'begin_time', 'end_time']):
            d = b.to_pydict()
            for mid, au, t0 in zip(d['meeting_id'], d['audio'], d['begin_time']):
                if mid not in want or t0 >= a.until_s:
                    continue
                x, sr = sf.read(io.BytesIO(au['bytes']), dtype='float32')
                if x.ndim > 1:
                    x = x.mean(axis=1)
                if mid not in buf:
                    buf[mid] = np.zeros(int(a.until_s * sr), dtype=np.float32); sr_of[mid] = sr; n_seg[mid] = 0
                i = int(round(t0 * sr))
                j = min(len(buf[mid]), i + len(x))
                if j > i:
                    buf[mid][i:j] = x[:j - i]; n_seg[mid] += 1
    for mid in sorted(buf):
        sf.write(out / f'{mid}.sdm.wav', buf[mid], sr_of[mid], subtype='PCM_16')
        cover = float(np.mean(np.abs(buf[mid]) > 0))
        print(f'{mid}: {n_seg[mid]} utterances, {sr_of[mid]} Hz, {100 * cover:.0f}% of the first {a.until_s:.0f} s covered')
    for mid in sorted(want - set(buf)):
        print(f'{mid}: not in these files')


if __name__ == '__main__':
    main()
