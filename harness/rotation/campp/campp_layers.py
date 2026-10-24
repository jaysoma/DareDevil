#!/usr/bin/env python3
"""CAM++ opened up: seven depths of the speaker model, pooled per stop, for brief C (2026-10-24).

The front end is Dictate's geonar/voiceopen.py, reproduced outside sherpa-onnx so the graph can be tapped: the 48 kHz
channel (or the mean of both) through the same 97-tap Hamming sinc at 6 kHz and every third sample; Kaldi fbank, 80 mel
bins, 25/10 ms, povey window, dither 0, snip_edges off, 20 Hz to Nyquist - 400 Hz; samples in [-1, 1]; the fbank's mean
over time subtracted (the model's own metadata: normalize_samples 1, feature_normalize_type global-mean). Against
sherpa's SpeakerEmbeddingExtractor on the same audio this gives cosine 1.000000 (largest difference 1e-4).

Speech is the stop's 0.5 s windows that facing_pooled.py calls voiced (total power 1.1-8 kHz at least 10 dB over the
tape's 20th percentile, from tapes/<walk>/band_windows.json), joined end to end, as voiceopen joins its spans. Each
frame-level depth is pooled over the result as mean and standard deviation per channel.

The depths, by their ONNX tensors:
  head    the FCM convolutional front, reshaped to 320 x T        /head/Reshape_output_0
  tdnn    the first TDNN layer, 128 x T/2                         /xvector/tdnn/nonlinear/relu/Relu_output_0
  block1  dense TDNN block 1 after its transit, 256               /xvector/transit1/linear/Conv_output_0
  block2  dense TDNN block 2 after its transit, 512               /xvector/transit2/linear/Conv_output_0
  block3  dense TDNN block 3 after transit and ReLU, 512          /xvector/out_nonlinear/relu/Relu_output_0
  stats   the stats pooling, mean and sd of block3 (1024)         /xvector/stats/Concat_output_0
  emb     the 192-value embedding                                 embedding

Needs the DiartLab venv (onnxruntime, torchaudio, soundfile) plus the onnx package, which that venv lacks; it was put
on PYTHONPATH from a separate folder so the venv stays as it is.

The stops' own words track their label (facing-0 stops say "facing the phone, two meters", turned ones "rotated 90
degrees"), and the middle of a speaker model hears words. --no-callouts keeps only the speech away from those words.

    python campp_layers.py [--no-callouts]   -> results/rotation/campp/vectors[_nocallouts].npz
"""
import json
import re
import sys
from pathlib import Path

import numpy as np
import onnx
import onnxruntime as ort
import soundfile as sf
import torch
import torchaudio.compliance.kaldi as kaldi

REPO = Path(__file__).resolve().parents[3]
CAP_TAPES = REPO.parent / 'Dictate' / 'captures' / 'geonar' / 'tapes'
MODEL = REPO / 'speaker_embeddings' / 'campplus_zh_en_advanced.onnx'
DEPTHS = {'head': '/head/Reshape_output_0',
          'tdnn': '/xvector/tdnn/nonlinear/relu/Relu_output_0',
          'block1': '/xvector/transit1/linear/Conv_output_0',
          'block2': '/xvector/transit2/linear/Conv_output_0',
          'block3': '/xvector/out_nonlinear/relu/Relu_output_0',
          'stats': '/xvector/stats/Concat_output_0',
          'emb': 'embedding'}
INPUTS = ('ch0', 'ch1', 'mean')
NOTCH = (1000.0, 3000.0)
CALLOUT = re.compile(r'rotat|notat|\brout\b|facing|\bface|degree|meter|metre|phone|away|clockwise|\bleft\b|\bright\b|'
                     r'turn|\b(45|90|135|180|270)\b|pacing|racing|basing|ninety|hundred|seventy|position|distance', re.I)
SR = 16000

# The ladders: facing the phone at called distances (harness/rotation/facing_vs_distance.py).
LADDERS = {
    'walk-213304': [[4, 20, 2], [20, 42, 3], [42, 63, 5], [63, 78, 7]],
    'walk-221126': [[0, 12, 1], [12, 21, 2], [21, 29, 3], [29, 36, 4], [36, 43, 5], [43, 47, 6], [47, 59, 7], [59, 66, 8]],
    'walk-020305': [[2, 18, 1], [18, 54, 2], [54, 90, 3.5]],
    'walk-224302': [[0, 13, 4.5], [13, 35, 2], [35, 78, 6]],
}


def session():
    m = onnx.load(str(MODEL))
    have = {o.name for o in m.graph.output}
    for name in DEPTHS.values():
        if name not in have:
            m.graph.output.append(onnx.helper.make_empty_tensor_value_info(name))
    o = ort.SessionOptions(); o.intra_op_num_threads = 4
    return ort.InferenceSession(m.SerializeToString(), o, providers=['CPUExecutionProvider'])


def tape(walk):
    """The tape's two channels at 48 kHz as float in [-1, 1]: the repo's copy, or the recording machine's."""
    for d in (REPO / 'tapes' / walk, CAP_TAPES):
        if (d / f'{walk}.wav').is_file():
            x, sr = sf.read(str(d / f'{walk}.wav'), dtype='int16'); assert sr == 48000
            return x.astype(np.float32) / 32768.0
        if (d / f'{walk}.raw').is_file():
            return np.fromfile(str(d / f'{walk}.raw'), dtype=np.int16).reshape(-1, 2).astype(np.float32) / 32768.0
    raise FileNotFoundError(walk)


def decimate(x, sr=48000):
    """voiceopen.py's resampler, verbatim."""
    k = sr // SR
    taps = 97; kk = np.arange(-(taps // 2), taps // 2 + 1); fc = 6000.0 / sr
    h = 2 * fc * np.sinc(2 * fc * kk) * np.hamming(taps); h /= h.sum()
    return np.convolve(x, h, mode='same')[::k].astype(np.float32)


def notch(y):
    """1-3 kHz taken out of the whole 16 kHz tape, bin by bin."""
    Y = np.fft.rfft(y.astype(np.float64)); f = np.fft.rfftfreq(len(y), 1 / SR)
    Y[(f >= NOTCH[0]) & (f <= NOTCH[1])] = 0
    return np.fft.irfft(Y, len(y)).astype(np.float32)


def signals(walk):
    """{(input, notched): 16 kHz signal} for both channels and their mean (the mean taken at 48 kHz, as voiceopen)."""
    x = tape(walk)
    base = {'ch0': decimate(x[:, 0]), 'ch1': decimate(x[:, 1]), 'mean': decimate(x.mean(1))}
    return {**{(k, False): v for k, v in base.items()}, **{(k, True): notch(v) for k, v in base.items()}}


def callouts(walk):
    """The decode's segments that say anything about the stop itself (rotation, facing, degrees, distance, the phone,
    misheard forms included), widened by 0.25 s: the words that track the label."""
    seg = json.loads((REPO / 'tapes' / walk / 'transcript.json').read_text())['segments']
    return [(s['t0'] - 0.25, s['t1'] + 0.25) for s in seg if CALLOUT.search(s['text'])]


def voiced_spans(walk, a, b, no_callouts=False):
    """The stop's voiced 0.5 s windows, merged where they touch: [[t0, t1], ...] and the speech they hold (s). With
    no_callouts, a window touching a callout segment is dropped."""
    bw = json.loads((REPO / 'tapes' / walk / 'band_windows.json').read_text())
    t0 = np.array(bw['t0']); P = 10 ** (np.asarray(bw['pow_db'], float) / 10)
    tot = 10 * np.log10(P[:, 1:].sum(1)); voiced = tot >= np.percentile(tot, 20) + 10
    m = voiced & (t0 >= a) & (t0 + bw['win_s'] <= b)
    if no_callouts:
        m &= np.array([not any(c0 < t + bw['win_s'] and t < c1 for c0, c1 in callouts(walk)) for t in t0])
    spans = []
    for t in t0[m]:
        if spans and t - spans[-1][1] < 0.01:
            spans[-1][1] = t + bw['win_s']
        else:
            spans.append([float(t), float(t + bw['win_s'])])
    return spans, float(m.sum() * bw['win_s'])


def layers(sess, y):
    """Every depth for one stretch of 16 kHz speech: frame-level ones pooled to mean and sd, the rest as they are."""
    f = kaldi.fbank(torch.from_numpy(y)[None], num_mel_bins=80, sample_frequency=SR, dither=0.0, snip_edges=False,
                    low_freq=20, high_freq=-400, window_type='povey').numpy()
    f = (f - f.mean(0, keepdims=True)).astype(np.float32)
    outs = sess.run(list(DEPTHS.values()), {'x': f[None]})
    v = {}
    for (k, _), o in zip(DEPTHS.items(), outs):
        o = o[0]
        v[k] = np.concatenate([o.mean(-1), o.std(-1)]) if o.ndim == 2 else o.reshape(-1)
    return v


def main(no_callouts=False):
    stops = json.loads((REPO / 'harness/rotation/facing_stops.json').read_text())['stops']
    jobs = {}  # walk -> [(kind, spot, facing, dist, a, b)]
    for walk, spots in stops.items():
        for spot, st in spots.items():
            if spot != 'dist_m':
                jobs.setdefault(walk, []).extend([('stop', spot, fd, spots['dist_m'][spot], a, b) for a, b, fd in st])
    for walk, steps in LADDERS.items():
        jobs.setdefault(walk, []).extend([('ladder', f'{d}m', 0, d, a, b) for a, b, d in steps])
    sess = session()
    meta, vec = [], {(i, n, k): [] for i in INPUTS for n in (False, True) for k in DEPTHS}
    for walk, js in jobs.items():
        sig = signals(walk); kept = 0
        for kind, spot, fd, dist, a, b in js:
            spans, speech = voiced_spans(walk, a, b, no_callouts)
            if speech < 1.0:
                continue
            for (inp, nt), y in sig.items():
                seg = np.concatenate([y[int(s * SR):int(e * SR)] for s, e in spans])
                for k, v in layers(sess, seg).items():
                    vec[(inp, nt, k)].append(v)
            meta.append(dict(kind=kind, walk=walk, spot=spot, facing=fd, dist_m=dist, t0=a, t1=b, speech_s=speech,
                             spans=spans))
            kept += 1
        print(f'{walk}: {kept} of {len(js)} stretches with 1 s of speech or more')
    out = {f'{i}|{"notch" if n else "clean"}|{k}': np.array(v, np.float32) for (i, n, k), v in vec.items()}
    dst = REPO / f'results/rotation/campp/vectors{"_nocallouts" if no_callouts else ""}.npz'
    np.savez_compressed(dst, meta=json.dumps(meta), **out)
    print(f'{len(meta)} stretches -> {dst.relative_to(REPO)}; dims ' +
          ', '.join(f'{k} {out[f"mean|clean|{k}"].shape[1]}' for k in DEPTHS))


if __name__ == '__main__':
    main('--no-callouts' in sys.argv)
