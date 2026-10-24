"""held_sounds.py -- where a tape holds a vowel (or a hum), from the sound itself. Talking wobbles in pitch and pulses
with its syllables; a held "aaah" keeps one pitch at one level. 50 ms frames of the mono tape at 16 kHz; voiced = above
the halfway mark between the tape's own floor (10th percentile) and its loud end (95th) AND periodic (normalised
autocorrelation >= .45 at a 80-400 Hz lag). A held stretch: 1.5 s in which >= 90% of frames are voiced, the pitch lag
stays within 6% of its median, and the level varies by <= 2.5 dB. The phone tapes sit only ~8 dB over their floor,
so every threshold is the tape's own. For labelling the rotation walks (Jay, 2026-10-23: "ones where I rotate while
holding a vowel. Those are important").
    python held_sounds.py walk-213304 walk-215800 ...
"""
import os
import sys

import numpy as np

CAP = r'C:\Projects\GithubRoot\Dictate\captures\geonar'
FR, WIN = 800, 30                                 # 50 ms frames at 16 kHz; a 1.5 s window


def mono16k(w):
    raw, wav = (os.path.join(CAP, 'tapes', w + ext) for ext in ('.raw', '.wav'))
    if os.path.exists(raw):
        b = open(raw, 'rb').read()
    else:                                         # the WAV's own data chunk (some tapes' headers libsndfile won't open)
        b, p = open(wav, 'rb').read(), 12
        while p + 8 <= len(b) and b[p:p + 4] != b'data':
            p += 8 + int.from_bytes(b[p + 4:p + 8], 'little') + (int.from_bytes(b[p + 4:p + 8], 'little') & 1)
        b = b[p + 8:p + 8 + int.from_bytes(b[p + 4:p + 8], 'little')]
    x = np.frombuffer(b[:len(b) // 4 * 4], dtype='<i2').reshape(-1, 2).astype(np.float32) / 32768
    m = x.mean(axis=1)
    return m[:len(m) // 3 * 3].reshape(-1, 3).mean(axis=1)    # 48 -> 16 kHz, averaging three as the low-pass


for w in sys.argv[1:]:
    try:
        m = mono16k(w)
    except FileNotFoundError:
        print(f'{w}: no tape on disk')
        continue
    n = len(m) // FR
    fr = m[:n * FR].reshape(n, FR)
    db = 10 * np.log10(np.mean(fr ** 2, axis=1) + 1e-12)
    lo, hi = np.percentile(db, 10), np.percentile(db, 95)
    ac = np.fft.irfft(np.abs(np.fft.rfft(fr - fr.mean(axis=1, keepdims=True), 2048, axis=1)) ** 2, axis=1)[:, :201]
    lag = 40 + ac[:, 40:201].argmax(axis=1)
    voiced = (db > lo + .25 * (hi - lo)) & (ac[:, 40:201].max(axis=1) / np.maximum(ac[:, 0], 1e-12) >= .35)
    held = np.zeros(n, bool)
    for i in range(0, n - WIN + 1):
        v = voiced[i:i + WIN]
        if v.mean() < .8:
            continue
        lg, lv = lag[i:i + WIN][v], db[i:i + WIN][v]
        if np.all(np.abs(lg - np.median(lg)) <= .08 * np.median(lg)):        # one pitch; the level may swing (he turns)
            held[i:i + WIN] = True
    runs, i = [], 0
    while i < n:
        if held[i]:
            j = i
            while j + 1 < n and held[j + 1]:
                j += 1
            runs.append((i * .05, (j - i + 1) * .05))
            i = j + 1
        else:
            i += 1
    tot = sum(d for _, d in runs)
    print(f"{w}: {len(runs):2d} held, {tot:5.1f} s of {n * .05:4.0f} s (range {hi - lo:4.1f} dB) | "
          + '  '.join(f"{a:.0f}s+{d:.1f}" for a, d in runs[:6]), flush=True)
