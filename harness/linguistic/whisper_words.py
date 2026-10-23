#!/usr/bin/env python3
"""Brief 18 step 1, third condition: what a real recogniser makes of the far-field audio, with AMI's speakers.

faster-whisper (base.en, int8, CPU) on the rebuilt far-field audio (sdm_rebuild.py), with word timestamps. Each
recognised word takes the AMI speaker whose manual words overlap it most in time; with no overlap, the speaker of the
nearest AMI word within 1 s; otherwise it has no speaker and is dropped (counted). `overlapped`: AMI words of more than
one speaker overlap it. `short`: as transcripts.py (a turn of at most 3 reply words).
usage: whisper_words.py <meeting json dir> <audio dir> <out dir> [--model base.en] [--threads 2] MEETING ...
       writes <out>/<meeting>.whisper.jsonl, and <out>/<meeting>.whisper.stats.json
"""
import argparse
import bisect
import json
import sys
import time
from pathlib import Path

import soundfile as sf

sys.path.insert(0, str(Path(__file__).resolve().parent))
from transcripts import mark_short    # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('json_dir'); ap.add_argument('audio_dir'); ap.add_argument('out')
    ap.add_argument('--model', default='base.en'); ap.add_argument('--threads', type=int, default=2)
    ap.add_argument('meetings', nargs='+')
    a = ap.parse_args()
    from faster_whisper import WhisperModel
    model = WhisperModel(a.model, device='cpu', compute_type='int8', cpu_threads=a.threads)
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    for mid in a.meetings:
        d = json.loads((Path(a.json_dir) / f'{mid}.json').read_text())
        ref = sorted(d['words'], key=lambda w: w['t0'])
        starts = [w['t0'] for w in ref]
        t0 = time.perf_counter()
        audio, sr = sf.read(str(Path(a.audio_dir) / f'{mid}.sdm.wav'), dtype='float32')    # 16 kHz mono, as Whisper takes it
        assert sr == 16000, sr
        segs, info = model.transcribe(audio, language='en', word_timestamps=True,
                                      vad_filter=False, beam_size=5)
        words = [w for s in segs for w in (s.words or [])]
        dt = time.perf_counter() - t0
        seq, unmapped = [], 0
        for w in words:
            s, e = w.start, w.end
            j = bisect.bisect_left(starts, s - 10)
            ov = {}
            near = None
            while j < len(ref) and ref[j]['t0'] < e + 1.0:
                r = ref[j]
                o = min(e, r['t1']) - max(s, r['t0'])
                if o > 0:
                    ov[r['spk']] = ov.get(r['spk'], 0) + o
                gap = max(r['t0'] - e, s - r['t1'], 0)
                if gap <= 1.0 and (near is None or gap < near[0]):
                    near = (gap, r['spk'])
                j += 1
            spk = max(ov, key=ov.get) if ov else (near[1] if near else None)
            if spk is None:
                unmapped += 1
                continue
            seq.append({'spk': spk, 't': round((s + e) / 2, 3), 'w': w.word.strip(), 'overlapped': len(ov) > 1})
        seq = mark_short(seq)
        with open(out / f'{mid}.whisper.jsonl', 'w') as fh:
            for x in seq:
                fh.write(json.dumps(x) + '\n')
        n_ref = sum(1 for w in d['words'] if w['t0'] < 600)
        st = {'meeting': mid, 'model': a.model, 'seconds': round(dt, 1), 'whisper_words': len(words), 'mapped': len(seq),
              'unmapped': unmapped, 'ami_words_in_span': n_ref,
              'same_next_pct': round(100 * sum(seq[k]['spk'] == seq[k + 1]['spk'] for k in range(len(seq) - 1)) / max(len(seq) - 1, 1), 1)}
        (out / f'{mid}.whisper.stats.json').write_text(json.dumps(st))
        print(json.dumps(st), flush=True)


if __name__ == '__main__':
    main()
