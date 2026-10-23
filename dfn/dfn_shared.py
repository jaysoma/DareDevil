r"""dfn_shared.py <tape> [--t0 S --t1 S] -- ONE DFN mask, both channels, phase intact.

THE IDEA (Jay, 2026-10-01). DeepFilterNet3 is monaural: `forward` takes one spectrum and returns
`(spec_e, m, lsnr, df_coefs)`, and `enhance()` keeps only `spec_e` and throws the other three away.
But `m` is the REAL ERB mask and `df_coefs` the complex deep-filter coefficients, and the model's own
`mask()` and `df_op()` will apply them to ANY spectrum. So:

    spec_mono = 0.5 * (spec_L + spec_R)        exact, by linearity of the STFT
    m, lsnr, coefs  <- model(spec_mono)        ONE instance, not two
    spec_L' = apply(m, coefs, spec_L)
    spec_R' = apply(m, coefs, spec_R)          the SAME operator on both

WHY THE SAME OPERATOR IS THE WHOLE POINT. Two independent DFN instances cannot work: neither sees the
other's channel, so neither can produce anything spatial, and each would apply a DIFFERENT filter --
which is precisely the operation that scrambles the inter-channel relationship the bearing is made of.
One shared operator does not:

    LEVEL RATIO.  A common real gain cannot change a ratio:  (g|X_L|)/(g|X_R|) = |X_L|/|X_R|.
                  The inter-channel level difference -- the head-shadow cue -- passes through intact.

    TIME DELAY.   Deep filtering is  Y(t,f) = SUM_i C_i(t,f) X(t-i,f),  linear along time. For a TDOA,
                  X_L(t,f) = X_R(t,f) e^-j2*pi*f*tau at EVERY frame with the same factor, so
                  Y_L = SUM_i C_i X_R(t-i) e^-j2*pi*f*tau = e^-j2*pi*f*tau Y_R. The phase difference
                  factors straight out of the sum. Exact for a stationary talker; a source moving
                  inside the 50 ms look-back (df_order 5 at a 10 ms hop) smears it slightly, and only
                  below 4.8 kHz, because deep filtering covers only the first nb_df = 96 bins. Above
                  that there is no complex stage at all, just the real gain.

WHAT THIS SCRIPT IS FOR, AND WHAT IT IS NOT. It does not estimate position. It prints the INGREDIENTS
a position estimate would be built from, per stop, beside the truth -- because the formula is the part
still to be decided, and inventing one here would hide whether the ingredients are any good.

The ingredient that matters most is the pair of mask-weighted covariances:

    PHI_s[f] = SUM_t   w  X X^H          w = the mask, upsampled to linear frequency
    PHI_n[f] = SUM_t (1-w) X X^H         X = the 2-vector of channel spectra

PHI_s gives a bearing with the noise statistically separated rather than merely filtered, and the
coherent share of PHI_s is a direct-to-diffuse ratio that is MEASURED rather than assumed. That last
part is the prize: every DRR this project has tried was built on `onset_tail_db`, which turned out to
read the ambient floor and RISE +11 dB/decade -- it was measuring its own gate, not the room. A
mask-derived PHI_n is an actual estimate of the diffuse field.

Reads dd/in.raw: the 2-channel 48 kHz int16 that ODAS itself was fed, so every number here is
comparable like-for-like with what odas.json already holds.
"""
import argparse
import io
import json
import os
import sys

import numpy as np

SR = 48000
CH = 2


def _stops(tape_dir):
    p = os.path.join(tape_dir, "stops.json")
    if not os.path.isfile(p):
        return []
    try:
        st = json.load(io.open(p, encoding="utf-8"))
    except Exception:
        return []
    out = []
    for s in st:
        if not isinstance(s, dict):
            continue
        t0, t1 = s.get("t0"), s.get("t1")
        if not isinstance(t0, (int, float)) or not isinstance(t1, (int, float)):
            continue
        out.append({"t0": float(t0), "t1": float(t1),
                    "label": str(s.get("label", "")), "r": s.get("r")})
    return out


def _read_stereo(path, t0=None, t1=None):
    """dd/in.raw -> float32 [2, N] in [-1, 1], optionally one window."""
    n_frames = os.path.getsize(path) // (CH * 2)
    a = 0 if t0 is None else max(0, int(t0 * SR))
    b = n_frames if t1 is None else min(n_frames, int(t1 * SR))
    if b <= a:
        raise SystemExit("empty window: %s..%s of %.1f s" % (t0, t1, n_frames / SR))
    with io.open(path, "rb") as f:
        f.seek(a * CH * 2)
        raw = np.frombuffer(f.read((b - a) * CH * 2), dtype="<i2")
    x = raw.reshape(-1, CH).T.astype(np.float32) / 32768.0
    return np.ascontiguousarray(x)


def coh_drr(Lc, Rc, W, f_hz, lo=1100.0, hi=8000.0, d_m=0.157, c=343.0):
    """THE ESTIMATOR UNDER TEST. Mask-weighted spatial covariance of a 2-mic pair.

    Lc, Rc : [T, F] complex spectra, already denoised by the shared operator
    W      : [T, F] real weights in [0, 1] -- the upsampled DFN mask
    f_hz   : [F] bin centre frequencies

    Returns a dict: coherence, drr_db, bearing_deg, tau_s, level_db, and the EFFECTIVE sample
    count, because every bias in here scales as 1/sqrt(that) and the raw frame count overstates it
    whenever the mask concentrates its weight on a handful of frames.

    BAND 1.1-8 kHz, and not a new choice: below it a 157 mm pair is in-phase bass and reads 0 deg.
    """
    import numpy as _np
    Wn = 1.0 - W
    eps = 1e-20

    def _cov(weight):
        sll = (weight * (Lc * _np.conj(Lc)).real).sum(axis=0)
        srr = (weight * (Rc * _np.conj(Rc)).real).sum(axis=0)
        slr = (weight * (Lc * _np.conj(Rc))).sum(axis=0)
        return sll, srr, slr

    sll, srr, slr = _cov(W)
    band = (f_hz >= lo) & (f_hz <= hi)

    # COHERENT SHARE. The time sum inside _cov is a COHERENT integration: a stable inter-channel
    # phase adds up, a random one cancels. Taking |.| per bin and summing across bins afterwards is
    # the incoherent step, which is right -- different frequencies carry independent information.
    coh = _np.abs(slr[band]).sum() / (_np.sqrt(sll[band].sum() * srr[band].sum()) + eps)

    # DRR from the SAME covariance, so unlike onset_tail_db there is no second window that can
    # wander off and measure something else. For a direct term of power rho against unit diffuse
    # power, PHI_LR -> rho and 0.5(PHI_LL + PHI_RR) -> rho + 1, so this returns 10log10(rho).
    tot = 0.5 * (sll[band].sum() + srr[band].sum())
    coh_pow = _np.abs(slr[band]).sum()
    drr = 10.0 * _np.log10((coh_pow + eps) / max(tot - coh_pow, eps))

    # BEARING: arg(PHI_LR) is a straight line in frequency whose slope is the TDOA.
    ph = _np.unwrap(_np.angle(slr[band]))
    wts = _np.abs(slr[band])
    ff = f_hz[band]
    tau = float(-_np.polyfit(2 * _np.pi * ff, ph, 1, w=wts)[0]) if wts.sum() > 0 else float("nan")
    bear = float(_np.degrees(_np.arcsin(_np.clip(tau * c / d_m, -1.0, 1.0))))

    sw = float(W.sum())
    n_eff = (sw * sw / float((W * W).sum())) if (W * W).sum() > 0 else 0.0
    return {"coherence": float(coh), "drr_db": float(drr), "bearing_deg": bear, "tau_s": tau,
            "level_db": float(10.0 * _np.log10(tot / max(sw, 1.0) + eps)), "n_eff": n_eff}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("tape")
    ap.add_argument("--root", default=r"C:\Projects\GithubRoot\Dictate\captures\geonar")
    ap.add_argument("--t0", type=float, default=None)
    ap.add_argument("--t1", type=float, default=None)
    ap.add_argument("--atten-lim-db", type=float, default=12.0,
                    help="Jay's setting; applied as the same linear blend on both channels, so it "
                         "is phase-preserving like everything else here")
    args = ap.parse_args()

    tape_dir = os.path.join(args.root, args.tape)
    in_raw = os.path.join(tape_dir, "dd", "in.raw")
    if not os.path.isfile(in_raw):
        raise SystemExit("no raw stereo: " + in_raw)

    import torch
    from df.enhance import init_df, df_features

    model, df_state, _ = init_df(log_level="ERROR")
    model.eval()
    nb_df = int(getattr(model, "nb_df", 96))
    hop = df_state.hop_size()
    fft = df_state.fft_size()
    print("DFN3  sr=%d fft=%d hop=%d (%.1f ms)  nb_df=%d (-> %.1f kHz)  df_order=%s"
          % (df_state.sr(), fft, hop, 1000.0 * hop / df_state.sr(), nb_df,
             nb_df * df_state.sr() / fft / 1000.0, getattr(model, "df_order", "?")))

    stops = _stops(tape_dir)
    if args.t0 is not None or args.t1 is not None:
        stops = [{"t0": args.t0 or 0.0, "t1": args.t1 or 1e9, "label": "window", "r": None}]
    if not stops:
        raise SystemExit("no stops.json and no --t0/--t1; nothing to measure")

    print("\n%-26s %7s %9s %9s %9s %9s %9s %8s"
          % ("stop", "truth_m", "bear_deg", "coh", "drr_dB", "lsnr_dB", "lvl_dB", "n_eff"))
    rows = []
    for st in stops:
        x = _read_stereo(in_raw, st["t0"], st["t1"])
        # mono in the TIME domain -- identical to averaging the spectra, and it keeps every channel
        # on one analysis pass so the framing cannot drift between them
        mono = 0.5 * (x[0] + x[1])
        audio = torch.from_numpy(np.stack([x[0], x[1], mono], axis=0))

        with torch.no_grad():
            spec, erb_feat, spec_feat = df_features(audio, df_state, nb_df, device="cpu")
            # spec: [C, 1, T, F, 2]; the mono channel is index 2 and it alone drives the model
            spec_m_in = spec[2:3].clone()
            _, m, lsnr, coefs = model(spec_m_in, erb_feat[2:3], spec_feat[2:3])

            # THE SHARED OPERATOR, applied identically to L and R.
            lim = None
            if args.atten_lim_db:
                lim = torch.tensor([abs(args.atten_lim_db)], dtype=torch.float32)
            out = []
            for c in (0, 1):
                s_c = spec[c:c + 1].clone()
                s_mask = model.mask(s_c.clone(), m, lim)
                s_df = model.df_op(s_c.clone(), coefs)
                s_df[..., nb_df:, :] = s_mask[..., nb_df:, :]
                out.append(torch.view_as_complex(s_df.squeeze(0).squeeze(0).contiguous()))
            L, R = out[0], out[1]                      # [T, F] complex, denoised, phase intact

            # the mask on the linear frequency grid, which is what weights the covariances
            w = m.matmul(model.mask.erb_inv_fb).squeeze(0).squeeze(0)      # [T, F] real in [0,1]

        Lc, Rc, W = L.numpy(), R.numpy(), w.numpy().astype(np.float64)
        f_hz = np.arange(Lc.shape[1]) * df_state.sr() / fft
        r = coh_drr(Lc, Rc, W, f_hz)
        ls = float(lsnr.mean())
        tr = st.get("r")
        print("%-26s %7s %9.1f %9.3f %9.2f %9.2f %9.2f %8.0f"
              % (st["label"][:26], ("%.2f" % tr) if isinstance(tr, (int, float)) else "-",
                 r["bearing_deg"], r["coherence"], r["drr_db"], ls, r["level_db"], r["n_eff"]))
        rows.append(dict(r, label=st["label"], t0=st["t0"], t1=st["t1"], truth_m=tr, lsnr_db=ls))

    out_p = os.path.join(tape_dir, "dfn_shared.json")
    io.open(out_p, "w", encoding="utf-8").write(json.dumps(rows, indent=1))
    print("\nwrote " + out_p)
    print("\ncoh  = coherent share of the mask-weighted covariance, 1.1-8 kHz")
    print("drr  = coherent vs residual power in that same covariance, dB")
    print("lsnr = DFN's own local SNR estimate, dB")
    print("lvl  = mask-weighted level of the denoised pair, dB")
    print("\nNo position is estimated here on purpose -- that formula is the open question.")


if __name__ == "__main__":
    sys.exit(main())
