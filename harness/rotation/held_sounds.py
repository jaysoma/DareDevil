"""held_sounds.py -- where a tape holds a vowel, from the sound itself. Talking wobbles in pitch and pulses with its
syllables; a held "aaah" keeps one pitch. 50 ms frames of the mono tape at 16 kHz.
  voiced: above the tape's floor (10th percentile) by a quarter of the way to its loud end (95th), AND periodic
          (normalised autocorrelation >= .35 at an 80-400 Hz lag, the peak INSIDE that range, 2026-10-24), AND a
          voice's band: 1.1-4 kHz power at least VOICE_DB over that band's own floor (0 dB: just not below it).
  held:   1.5 s in which >= 80% of frames are voiced and the pitch lag stays within 8% of its median. The level isn't
          checked: it swings as he turns.
  hum guard (2026-10-24): a window whose pitch sits within 2 Hz of a multiple of 60 Hz and never moves (lag spread of
          1 sample or less) is mains, not a voice. A held human vowel jitters by a few samples.
Before 2026-10-24 the pitch could sit on the search's edge. Low-frequency room rumble (fridge, air) still correlates at
the shortest lag, so it read as a dead-steady 400 Hz "vowel": all 36 of walk-213304's held stretches (77 s) were that.
For labelling the rotation walks (Jay, 2026-10-23: "ones where I rotate while holding a vowel. Those are important").
    python held_sounds.py walk-213304 walk-215800 ...      (the repo's tapes/<walk>/ copy first, else CAP)
"""
import os
import sys

import numpy as np

CAP = r'C:\Projects\GithubRoot\Dictate\captures\geonar'
FR, WIN = 800, 30                                 # 50 ms frames at 16 kHz; a 1.5 s window
VOICE_DB = 0.0
REPO_TAPES = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'tapes')


def mono16k(w):
    here = [os.path.join(REPO_TAPES, w, w + ext) for ext in ('.raw', '.wav')]
    raw, wav = here if any(os.path.exists(h) for h in here) else [os.path.join(CAP, 'tapes', w + ext) for ext in ('.raw', '.wav')]
    if os.path.exists(raw):
        b = open(raw, 'rb').read()
    else:                                         # the WAV's own data chunk (some tapes' headers libsndfile won't open)
        b, p = open(wav, 'rb').read(), 12
        while p + 8 <= len(b) and b[p:p + 4] != b'data':
            p += 8 + int.from_bytes(b[p + 4:p + 8], 'little') + (int.from_bytes(b[p + 4:p + 8], 'little') & 1)
        b = b[p + 8:p + 8 + int.from_bytes(b[p + 4:p + 8], 'little')]
    x = np.frombuffer(b[:len(b) // 4 * 4], dtype='<i2').reshape(-1, 2).astype(np.float32) / 32768
    m = x.mean(axis=1)
    m = m[:len(m) // 3 * 3].reshape(-1, 3).mean(axis=1)       # 48 -> 16 kHz, averaging three as the low-pass
    from scipy.signal import butter, sosfiltfilt               # 2026-10-24: rumble below ~90 Hz swamped the pitch search
    return sosfiltfilt(butter(4, 90, btype='high', fs=16000, output='sos'), m).astype(np.float32)


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
    sp = np.abs(np.fft.rfft(fr * np.hanning(FR), axis=1)) ** 2
    f = np.fft.rfftfreq(FR, 1 / 16000)
    vb = 10 * np.log10(sp[:, (f >= 1100) & (f <= 4000)].sum(axis=1) + 1e-12)
    inside = (lag > 41) & (lag < 199)               # a pitch at the search's edge is no pitch: rumble peaks at lag 40
    voiced = ((db > lo + .25 * (hi - lo)) & (ac[:, 40:201].max(axis=1) / np.maximum(ac[:, 0], 1e-12) >= .35)
              & inside & (vb >= np.percentile(vb, 10) + VOICE_DB))
    hum = 0
    held = np.zeros(n, bool)
    for i in range(0, n - WIN + 1):
        v = voiced[i:i + WIN]
        if v.mean() < .8:
            continue
        lg, lv = lag[i:i + WIN][v], db[i:i + WIN][v]
        if np.all(np.abs(lg - np.median(lg)) <= .08 * np.median(lg)):        # one pitch; the level may swing (he turns)
            f0 = 16000 / np.median(lg)
            if lg.max() - lg.min() <= 1 and abs(f0 - 60 * round(f0 / 60)) <= 2:
                hum += 1; continue                                           # mains: dead steady, on a 60 Hz multiple
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
    print(f"{w}: {len(runs):2d} held, {tot:5.1f} s of {n * .05:4.0f} s (range {hi - lo:4.1f} dB; {hum} windows set aside as hum) | "
          + '  '.join(f"{a:.0f}s+{d:.1f}" for a, d in runs[:6]), flush=True)
