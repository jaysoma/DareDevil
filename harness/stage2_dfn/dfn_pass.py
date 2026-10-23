#!/usr/bin/env python3
"""Brief 16: one DeepFilterNet3 pass over each whole recording, for one capsule pair, at one input level.

Runs in its own venv (deepfilternet 0.5.6 needs torch 2.0 / torchaudio 2.0 and numpy < 2): see README.md.

THE OPERATOR (dfn/dfn_shared.py, Jay's): the stock DFN3 model, run ONCE on the L+R mixdown; its ERB mask and deep-filter
coefficients applied identically to L and R. The 12 dB attenuation limit is the stock enhance()'s: the output spectrum is
lim * noisy + (1 - lim) * enhanced, on both channels. (dfn_shared.py passes the limit to model.mask instead, which
clamps the mask but leaves the deep-filter band, below 4.8 kHz, unlimited; its help text says "the same linear blend on
both channels", which is what is done here.) Whole recordings, in order, as the app runs: the GRUs carry state through
the gaps. Frame k of DFN's 10 ms grid is centred on sample 480 k (measured: an impulse at sample 24000 lands in frame
50 alone).

LEVEL (test 1): `raw` feeds the recording as it is; `norm` multiplies it by ONE gain per recording and pair, chosen so
the mixdown's rms over labelled speech (STARSS23 speech classes; LOCATA's VAD, any talker) is -26 dBFS.

A second pass on capsule L alone gives test 4's single-capsule mask.

Per recording, pair and level this writes:
  frames/<tag>.npz   on DFN's 10 ms grid: lsnr (mixdown pass), lsnr_cap (L pass), mask_mix and mask_cap (the mask on
                     linear frequency, mean over 300 Hz - 8 kHz), level_db (the mixdown's own level, dBFS), plus the
                     gain and speech level.
  attacks/<tag>.json src/geonar/attacks.py's MF opens over the raw pair (raw level only; it is level-free).
  cuts/<tag>.jsonl   (temporary, deleted once read) for each batch A read in this recording and pair: batch A's cut
                     window (0.5 s before to 1.0 s after the onset) of the raw pair (L, R) and the DFN pair (DL, DR) at
                     batch A's int16 scale, and the two masks averaged over GccPhat's lock window on GccPhat's own
                     slices (wmix, wcap). run_gcc.mjs reads them at once.
  preds/<tag>.jsonl  GccPhat per read: raw, dfn, mix, cap (raw only at the raw level: the raw pair is the same at both).
  clues/<tag>.jsonl  per read: lsnr at the onset and its max over the first 200 ms, the single-capsule lsnr, the mask's
                     share of GccPhat's band over its lock window (mixdown and capsule masks).
  cost/<tag>.json    seconds of audio, seconds of DFN.

usage: dfn_pass.py JOBS.jsonl OUT_DIR --level raw|norm --shard K --of N
"""
import argparse
import base64
import os
import subprocess
import json
import math
import sys
import time
from pathlib import Path

import numpy as np
import soundfile as sf
import torch
from scipy.signal import resample_poly

SR, HOP, NFFT_DFN = 48000, 480, 960
ATTEN_DB = 12.0
TARGET_DBFS = -26.0
# GccPhat's slices and lock window (src/schemes/GccPhat.mjs)
G_NFFT, G_HOP, G_LO, G_HI, G_FRAMES, PREROLL = 2048, 512, 300, 8000, 47, 512
G_K0, G_K1 = math.ceil(G_LO * G_NFFT / SR), math.floor(G_HI * G_NFFT / SR)
G_F = np.arange(G_K0, G_K1 + 1) * SR / G_NFFT
PRE_S, POST_S = 0.5, 1.0


def load_pair(job):
    """(x [N, 2] float64 at 48 kHz, speech mask [N] bool, batch A int16 scale)"""
    if job['dataset'] == 'starss23':
        x, sr = sf.read(job['wav'], dtype='float64')
        x2 = resample_poly(x[:, [job['caps'][0] - 1, job['caps'][1] - 1]], 2, 1, axis=0)
        sp = np.zeros(len(x2), bool)
        for line in open(job['meta']):
            r = line.strip().split(',')
            if len(r) > 1 and int(r[1]) in (0, 1):
                f = int(r[0])
                sp[f * 4800:(f + 1) * 4800] = True
        return x2, sp, 32767.0
    x, sr = sf.read(job['wav'], dtype='float64')
    assert sr == SR
    x2 = x[:, [job['mics'][0] - 1, job['mics'][1] - 1]]
    sp = np.zeros(len(x2), bool)
    for v in job['vads']:
        a = np.loadtxt(v, skiprows=1, usecols=(-1,)) > 0
        n = min(len(a), len(sp))
        sp[:n] |= a[:n]
    return x2, sp, 0.5 * 32767 / np.abs(x2).max()


class Dfn:
    def __init__(self):
        from df.enhance import init_df, df_features
        self.df_features = df_features
        self.model, self.st, _ = init_df(log_level='ERROR')
        self.model.eval()
        self.nb_df = self.model.nb_df
        self.inv = self.model.mask.erb_inv_fb.numpy()                      # [32, 481]
        self.f = np.arange(self.inv.shape[1]) * SR / NFFT_DFN

    def run(self, chans, enhance):
        """chans [C, N] float32; the LAST channel drives the model. Returns (mask_lin [T, 481], lsnr [T], enhanced
        [C-1, N] or None): the operator from the last channel applied to the others."""
        n = chans.shape[1]
        self.st.reset()
        if hasattr(self.model, 'reset_h0'):
            self.model.reset_h0(batch_size=1, device='cpu')
        audio = torch.from_numpy(np.pad(chans, ((0, 0), (0, NFFT_DFN))).astype(np.float32))
        with torch.no_grad():
            spec, erb, sfe = self.df_features(audio, self.st, self.nb_df, device='cpu')
            _, m, lsnr, coefs = self.model(spec[-1:].clone(), erb[-1:], sfe[-1:])
            enh = None
            if enhance:
                lim = 10 ** (-ATTEN_DB / 20)
                outs = []
                for c in range(chans.shape[0] - 1):
                    s_c = spec[c:c + 1]
                    s_m = self.model.mask(s_c.clone(), m)
                    s_e = self.model.df_op(s_c.clone(), coefs)
                    s_e[..., self.nb_df:, :] = s_m[..., self.nb_df:, :]
                    z = torch.view_as_complex(s_e.squeeze(1).contiguous())
                    z0 = torch.view_as_complex(s_c.squeeze(1).contiguous())
                    outs.append((z0 * lim + z * (1 - lim)).squeeze(0).numpy())
                syn = self.st.synthesis(np.stack(outs))                     # [C-1, N + 960]
                d = NFFT_DFN - HOP                                         # STFT/ISTFT delay, as enhance() removes
                enh = syn[:, d:d + n]
        w = m[0, 0].numpy() @ self.inv                                      # [T, 481], the mask on linear frequency
        return w, lsnr.reshape(-1).numpy(), enh


def lock_mask(w, on48):
    """The mask averaged over GccPhat's lock window (47 frames of 2048 from one step before the onset), on its slices."""
    a = on48 - PREROLL
    b = a + (G_FRAMES - 1) * G_HOP + G_NFFT
    k0, k1 = max(0, int(math.ceil(a / HOP))), min(len(w) - 1, int(b // HOP))
    if k1 < k0:
        return None
    lin = w[k0:k1 + 1].mean(0)
    return np.interp(G_F, np.arange(w.shape[1]) * SR / NFFT_DFN, lin)


G_HANN = 0.5 - 0.5 * np.cos(2 * np.pi * np.arange(G_NFFT) / (G_NFFT - 1))


def inphase(x2, on48):
    """Per GccPhat slice over its lock window: |L+R|^2 / 2(|L|^2+|R|^2), 1 where the capsules add, 0 where they
    cancel -- what the L+R mixdown keeps of each band (test 4's mechanism)."""
    a = on48 - PREROLL
    fr = np.stack([x2[a + G_HOP * i:a + G_HOP * i + G_NFFT] for i in range(G_FRAMES)]) * G_HANN[None, :, None]
    S = np.fft.rfft(fr, axis=1)[:, G_K0:G_K1 + 1]
    num = (np.abs(S[..., 0] + S[..., 1]) ** 2).sum(0)
    den = 2 * (np.abs(S[..., 0]) ** 2 + np.abs(S[..., 1]) ** 2).sum(0) + 1e-30
    return num / den


def corr(a, b):
    a, b = a - a.mean(), b - b.mean()
    d = math.sqrt((a * a).sum() * (b * b).sum())
    return float((a * b).sum() / d) if d > 0 else None


def b64(x, scale):
    return base64.b64encode(np.clip(x * scale, -32768, 32767).astype('<i2').tobytes()).decode()


def attacks_opens(x2):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'src' / 'geonar'))
    from attacks import Attacks
    a = Attacks()
    opens = []
    for i in range(0, len(x2), 512):
        for kind, at in a.feed(x2[i:i + 512, 0], x2[i:i + 512, 1]):
            if kind == 'open':
                opens.append(at / SR)
    return opens


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('jobs')
    ap.add_argument('out')
    ap.add_argument('--level', choices=['raw', 'norm'], required=True)
    ap.add_argument('--shard', type=int, default=0)
    ap.add_argument('--of', type=int, default=1)
    a = ap.parse_args()
    torch.set_num_threads(1)
    out = Path(a.out)
    for sub in ('frames', 'attacks', 'cuts', 'cost', 'preds', 'clues'):
        (out / sub).mkdir(parents=True, exist_ok=True)
    jobs = [json.loads(l) for l in open(a.jobs)][a.shard::a.of]
    dfn = Dfn()
    band = (dfn.f >= G_LO) & (dfn.f <= G_HI)
    for job in jobs:
        tag = f"{job['tag']}_{a.level}"
        if (out / 'cost' / f'{tag}.json').exists():
            continue
        x2, sp, scale = load_pair(job)
        mix = x2.mean(1)
        speech_db = 10 * math.log10(np.mean(mix[sp] ** 2) + 1e-20) if sp.any() else None
        gain = 1.0 if a.level == 'raw' or speech_db is None else 10 ** ((TARGET_DBFS - speech_db) / 20)
        g = (x2 * gain).T.astype(np.float32)                                     # [2, N]
        t0 = time.time()
        w_mix, lsnr, enh = dfn.run(np.stack([g[0], g[1], g.mean(0)]), enhance=True)
        t1 = time.time()
        w_cap, lsnr_cap, _ = dfn.run(g[:1], enhance=False)
        t2 = time.time()
        enh = enh.T / gain                                                       # back to the recording's scale
        T = len(lsnr)
        p = np.concatenate([np.zeros(HOP), g.mean(0).astype(np.float64) ** 2, np.zeros(T * HOP + HOP)])
        lev = 10 * np.log10(p[:(T + 1) * HOP].reshape(T + 1, HOP).sum(1)[:T] / (2 * HOP)          # frame k: k*HOP +- HOP
                            + p[HOP:(T + 2) * HOP].reshape(T + 1, HOP).sum(1)[:T] / (2 * HOP) + 1e-20)
        np.savez_compressed(out / 'frames' / f'{tag}.npz', lsnr=lsnr.astype(np.float32),
                            lsnr_cap=lsnr_cap.astype(np.float32), mask_mix=w_mix[:, band].mean(1).astype(np.float32),
                            mask_cap=w_cap[:, band].mean(1).astype(np.float32), level_db=lev.astype(np.float32),
                            gain=gain, speech_db=speech_db if speech_db is not None else np.nan)
        if a.level == 'raw' and not (out / 'attacks' / f"{job['tag']}.json").exists():
            (out / 'attacks' / f"{job['tag']}.json").write_text(json.dumps(attacks_opens(x2)))
        cuts = out / 'cuts' / f'{tag}.jsonl'
        with open(cuts, 'w') as fh, open(out / 'clues' / f'{tag}.jsonl', 'w') as fc:
            for r in job['reads']:
                on = int(round(r['onset_s'] * SR))
                i0, i1 = on - int(PRE_S * SR), on + int(POST_S * SR)
                if i0 < 0 or i1 > len(x2):
                    continue
                wm, wc = lock_mask(w_mix, on), lock_mask(w_cap, on)
                k = int(round(on / HOP))
                ks = slice(k, min(T, k + 20))
                fh.write(json.dumps({
                    'id': r['id'], 'onset_sample': int(PRE_S * SR), 'baseline_m': r['baseline_m'],
                    'L': b64(x2[i0:i1, 0], scale), 'R': b64(x2[i0:i1, 1], scale),
                    'DL': b64(enh[i0:i1, 0], scale), 'DR': b64(enh[i0:i1, 1], scale),
                    'wmix': [round(float(v), 4) for v in wm], 'wcap': [round(float(v), 4) for v in wc]}) + '\n')
                rho = inphase(x2, on)
                cancel, add = rho < 0.25, rho > 0.75
                mech = {'corr_mix_inphase': corr(wm, rho), 'corr_cap_inphase': corr(wc, rho),
                        'corr_mixminuscap_inphase': corr(wm - wc, rho),
                        'mix_cancel': float(wm[cancel].mean()) if cancel.any() else None,
                        'mix_add': float(wm[add].mean()) if add.any() else None,
                        'cap_cancel': float(wc[cancel].mean()) if cancel.any() else None,
                        'cap_add': float(wc[add].mean()) if add.any() else None,
                        'cancel_share': float(cancel.mean())}
                fc.write(json.dumps({'id': r['id'], 'mech': {k2: None if v2 is None else round(v2, 4)
                                                              for k2, v2 in mech.items()},
                                     'lsnr_on': round(float(lsnr[min(k, T - 1)]), 2),
                                     'lsnr_max200': round(float(lsnr[ks].max()), 2),
                                     'lsnr_cap_on': round(float(lsnr_cap[min(k, T - 1)]), 2),
                                     'mask_band': round(float(wm.mean()), 4),
                                     'mask_cap_band': round(float(wc.mean()), 4)}) + '\n')
        t3 = time.time()
        with open(out / 'preds' / f'{tag}.jsonl', 'w') as fp:
            subprocess.run(['node', str(Path(__file__).with_name('run_gcc.mjs')), str(cuts),
                            'raw,dfn,mix,cap' if a.level == 'raw' else 'dfn,mix,cap'], check=True, stdout=fp)
        os.unlink(cuts)
        (out / 'cost' / f'{tag}.json').write_text(json.dumps({
            'tag': tag, 'audio_s': len(x2) / SR, 'dfn_mix_s': t1 - t0, 'dfn_cap_s': t2 - t1, 'gcc_s': time.time() - t3,
            'gain': gain,
            'speech_db': speech_db, 'reads': len(job['reads'])}))
        print('done', tag, flush=True)


if __name__ == '__main__':
    main()
