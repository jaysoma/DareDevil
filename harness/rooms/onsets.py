"""Word onsets in clean speech clips, each cut into a 1.5 s utterance: 0.5 s of silence, then 1.0 s of speech from the
onset. An onset is a 5 ms frame within 25 dB of the clip's loudest that follows at least PAUSE_S of frames within 8 dB
of the clip's quiet level (its 10th percentile), traced back to the frame where it leaves that quiet. Clips are
resampled to 48 kHz. Also writes <out>_ctx.npy: the same utterances with the clip's own 0.5 s before the onset (earlier
words and the pause) in place of the silence. usage: python onsets.py <folder of clips> <out.npy>"""
import glob, os, sys
import numpy as np, soundfile as sf
from scipy.signal import resample_poly
PAUSE_S, SR, PRE, POST, FR = 0.08, 48000, 24000, 48000, 240
utts, ctx = [], []
for f in sorted(glob.glob(os.path.join(sys.argv[1], '*'))):
    x, sr = sf.read(f)
    if x.ndim > 1: x = x[:, 0]
    x = resample_poly(x, SR, sr) if sr != SR else x
    x = x / np.abs(x).max()
    n = len(x) // FR
    lev = 10 * np.log10(np.mean(x[:n * FR].reshape(n, FR) ** 2, axis=1) + 1e-12)
    top, q = lev.max(), np.percentile(lev, 10) + 8
    quiet, loud, P = lev <= q, lev >= top - 25, int(PAUSE_S * SR / FR)
    last, k = -SR, 0
    for i in range(P, n):
        if not (loud[i] and quiet[max(0, i - P - 8):i - 8].all()): continue   # loud, with the pause ending 40 ms before
        j = i
        while j > 0 and lev[j - 1] > q: j -= 1                    # back to where it leaves the quiet
        at = j * FR
        if at + POST > len(x) or at - last < SR // 2: continue
        u = np.zeros(PRE + POST); u[PRE:] = x[at:at + POST]
        c = u.copy(); b = x[max(0, at - PRE):at]; c[PRE - len(b):PRE] = b
        utts.append(u); ctx.append(c); last = at; k += 1
    print(os.path.basename(f), k, 'onsets')
np.save(sys.argv[2], np.array(utts)); np.save(sys.argv[2][:-4] + '_ctx.npy', np.array(ctx))
print(len(utts), 'utterances, onset at sample', PRE)
