#!/usr/bin/env python3
"""Add decoded words to the joined animation files, on Jay's box (faster-whisper; any Whisper size).

None of the three datasets ships transcripts, and the cloud sessions can't download Whisper's weights, so this runs
where the models already are.

  LOCATA (best): each talker wore a close-talking mic (audio_source_<talker>.wav), sample-aligned with the array.
    Whisper on that channel gives clean words that already belong to the right talker. The wav is streamed out of the
    release zip by range requests (about 9-23 MB per talker), so the 19 GB of zips are never downloaded.

        python3 add_words.py locata results/animation/locata --model medium.en

  STARSS23 (rough): far-field, quiet, overlapping talkers. Whisper runs on capsules 1+2 mixed down (one fixed gain,
    no AGC). A word is given to a labelled speech source only when exactly one is active at that 100 ms frame;
    otherwise "src" is null. Each recording is streamed out of Zenodo's mic_dev.zip one file at a time (20-60 MB each,
    about 3.4 GB over all 168), unless --audio points at a local copy.

        python3 add_words.py starss results/animation/starss23 --model medium.en
        python3 add_words.py starss results/animation/starss23 --audio <STARSS23 root with mic_dev/>

  dEchorate: there are no dEchorate recordings in these results. Each clip is a clean EARS read sentence (from its
    onset, 1.0 s of it) played through dEchorate's measured room responses. bake.py already carries each file's whole
    text; this decodes the 16 EARS files (streamed from the EARS release zips, a few MB each) and keeps each clip's own
    words, timed from the clip's onset.

        python3 add_words.py dechorate results/animation/dechorate --model medium.en

Writes "words": [{"t0", "t1", "w", "p", "talker" or "src"}] into each file, times in seconds from the recording start.
"""
import argparse
import io
import json
from pathlib import Path

import numpy as np

LOCATA_ZIP = 'https://zenodo.org/records/3630471/files/{set}.zip?download=1'
STARSS_ZIP = 'https://zenodo.org/records/7880637/files/mic_dev.zip?download=1'


def transcribe(model, x16):
    segs, _ = model.transcribe(x16, language='en', word_timestamps=True, vad_filter=False, beam_size=5)
    out = []
    for s in segs:
        for w in (s.words or []):
            out.append({'t0': round(w.start, 2), 't1': round(w.end, 2), 'w': w.word.strip(), 'p': round(w.probability, 2)})
    return out


def to16k(x, sr):
    from scipy.signal import resample_poly
    from math import gcd
    g = gcd(int(sr), 16000)
    return resample_poly(x, 16000 // g, int(sr) // g).astype(np.float32)


def locata(folder, model):
    import soundfile as sf
    from remotezip import RemoteZip
    zips = {}
    for f in sorted(Path(folder).glob('*_task*_recording*.json')):
        doc = json.loads(f.read_text())
        set_, task, rec = doc['set'], doc['task'], doc['recording'].split('_')[-1]
        z = zips.setdefault(set_, RemoteZip(LOCATA_ZIP.format(set=set_)))
        words = []
        for tk in doc['tracks']:
            name = f'{set_}/{task}/{rec}/dicit/audio_source_{tk}.wav'
            with z.open(name) as fh:
                x, sr = sf.read(io.BytesIO(fh.read()), dtype='float32')
            if x.ndim > 1:
                x = x.mean(axis=1)
            for w in transcribe(model, to16k(x, sr)):
                w['talker'] = tk
                words.append(w)
        doc['words'] = sorted(words, key=lambda w: w['t0'])
        f.write_text(json.dumps(doc, separators=(',', ':')))
        print(f.name, len(words), 'words')


def starss(folder, audio_root, model):
    import soundfile as sf
    z = None
    if not audio_root:
        from remotezip import RemoteZip
        z = RemoteZip(STARSS_ZIP)
    for f in sorted(Path(folder).glob('fold*_room*_mix*.json')):
        doc = json.loads(f.read_text())
        if doc.get('words'):
            continue                                                  # done on an earlier run
        if z is not None:
            with z.open(f"mic_dev/{doc['split']}/{doc['recording']}.wav") as fh:
                x, sr = sf.read(io.BytesIO(fh.read()), dtype='float32', always_2d=True)
        else:
            wav = next(Path(audio_root).glob(f"mic_dev/*/{doc['recording']}.wav"))
            x, sr = sf.read(str(wav), dtype='float32', always_2d=True)
        mono = 0.5 * (x[:, 0] + x[:, 1])
        rms = float(np.sqrt(np.mean(mono ** 2)) + 1e-12)
        mono = mono * min(0.05 / rms, 1.0 / (np.abs(mono).max() + 1e-12))     # one fixed gain for the whole file
        active = {}
        for key, tr in doc['tracks'].items():
            if tr['kind'] == 'speech':
                for fr in tr['f']:
                    active.setdefault(fr, []).append(key)
        words = transcribe(model, to16k(mono, sr))
        for w in words:
            keys = active.get(int((w['t0'] + w['t1']) / 2 / 0.1), [])
            w['src'] = keys[0] if len(keys) == 1 else None
        doc['words'] = words
        f.write_text(json.dumps(doc, separators=(',', ':')))
        print(f.name, len(words), 'words')


def dechorate(folder, model):
    import sys
    import zipfile
    import soundfile as sf
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'dechorate'))
    from ears_fetch import RangeFile, URL as EARS_URL
    POST_S = 1.0                                                     # dechorate_cut.py: the clip runs 1.0 s from its onset
    files = {}
    docs = {f: json.loads(f.read_text()) for f in sorted(Path(folder).glob('*.json')) if f.name != 'index.json'}
    for doc in docs.values():
        for su in doc['setups']:
            for c in su['clips']:
                files.setdefault(c['clip'].split('@')[0], None)
    for key in sorted(files):
        spk, name = key.split('_', 1)
        zf = zipfile.ZipFile(io.BufferedReader(RangeFile(EARS_URL.format(spk)), buffer_size=1 << 20))
        member = next(n for n in zf.namelist() if n.endswith(f'{name}.wav'))
        x, sr = sf.read(io.BytesIO(zf.read(member)), dtype='float32')
        if x.ndim > 1:
            x = x.mean(axis=1)
        files[key] = transcribe(model, to16k(x, sr))
        print(key, len(files[key]), 'words')
    for f, doc in docs.items():
        for su in doc['setups']:
            for c in su['clips']:
                key, at = c['clip'].split('@')[0], c.get('onset_in_file_s') or 0.0
                c['words'] = [{'t0': round(w['t0'] - at, 2), 't1': round(w['t1'] - at, 2), 'w': w['w'], 'p': w['p']}
                              for w in files[key] if w['t1'] > at and w['t0'] < at + POST_S]
        doc['words_note'] = "clips' words from Whisper on the clean EARS files, times from each clip's onset"
        f.write_text(json.dumps(doc, separators=(',', ':')))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('dataset', choices=['locata', 'starss', 'dechorate'])
    ap.add_argument('folder')
    ap.add_argument('--audio', help='STARSS23 root (with mic_dev/)')
    ap.add_argument('--model', default='medium.en')
    ap.add_argument('--device', default='auto')
    a = ap.parse_args()
    from faster_whisper import WhisperModel
    model = WhisperModel(a.model, device=a.device)
    if a.dataset == 'locata':
        locata(a.folder, model)
    elif a.dataset == 'dechorate':
        dechorate(a.folder, model)
    else:
        starss(a.folder, a.audio, model)


if __name__ == '__main__':
    main()
