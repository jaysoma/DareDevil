r"""dfnlab_data.py <tape> [--ranges ...] -- bakes dfnlab.json beside the tape, for Voice's DfnLab page.

WHY A SIDECAR AND NOT A LIVE ROUTE. Voice serves bytes and holds no numpy, by design -- the same
reason voicemel.json exists. Everything expensive (the DFN pass, two CDR runs) happens here, once,
and the page just draws.

WHAT IT CARRIES, per gate utterance:

    env       the waveform peak envelope, ONE VALUE PER CDR HOP so the colour and the shape share an
              index -- the picture is the waveform tinted by the direct-to-diffuse ratio at that
              instant, which is the whole point: you see which syllables arrived straight from the
              mouth and which arrived as room.
    cdr_raw   cdr_direct on the untouched pair
    cdr_dfn   cdr_direct on the pair after ONE shared DFN operator (see dfn_cdr.py for why one)
    lsnr      DFN's own SNR estimate, 10 ms frames. Drawn with its -15 dB clamp marked, because on
              most utterances here it sits flat on that rail and that IS the finding.
    mask      the [T, 32] ERB gain as uint8, base64 -- what the model believed was speech, per band.

Quantisation follows voicemel's lead: a byte per cell, range stated in the header, so a 10-utterance
tape is a few hundred KB instead of several MB of JSON floats.
"""
import argparse
import base64
import io
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cdr_direct import cdr_direct, SR, HOP                      # noqa: E402

CH = 2
PREROLL_S = 0.6
TAIL_S = 0.40
MASK_HOP_S = 0.010


def _read_stereo(path, t0, t1):
    n = os.path.getsize(path) // (CH * 2)
    a, b = max(0, int(t0 * SR)), min(n, int(t1 * SR))
    if b <= a:
        return None
    with io.open(path, "rb") as f:
        f.seek(a * CH * 2)
        raw = np.frombuffer(f.read((b - a) * CH * 2), dtype="<i2")
    return raw.reshape(-1, CH).astype(np.float64) / 32768.0


def dfn_pass(x, model, df_state, nb_df, torch, atten_db=None):
    """x: [N,2] -> (denoised [N,2], mask [T,32], lsnr [T]). One operator from the mono mixdown.

    atten_db caps how far any bin may be pushed down, which is the setting the app actually ships
    (Jay runs 12). Uncapped, DFN drove far and away-facing utterances to -112 dB on walk-171645 --
    real behaviour of the model, but not behaviour the demo will ever exhibit, so an experiment run
    without the cap measures something that cannot be deployed.
    """
    from df.enhance import df_features
    L = x[:, 0].astype(np.float32)
    R = x[:, 1].astype(np.float32)
    mono = (0.5 * (L + R)).astype(np.float32)
    with torch.no_grad():
        spec, erb_feat, spec_feat = df_features(
            torch.from_numpy(np.stack([L, R, mono], axis=0)), df_state, nb_df, device="cpu")
        _, m, lsnr, coefs = model(spec[2:3].clone(), erb_feat[2:3], spec_feat[2:3])
        lim = None
        if atten_db:
            lim = torch.tensor([abs(float(atten_db))], dtype=torch.float32)
        outs = []
        for c in (0, 1, 2):
            s_c = spec[c:c + 1].clone()
            s_mask = model.mask(s_c.clone(), m, lim)
            s_df = model.df_op(s_c.clone(), coefs)
            s_df[..., nb_df:, :] = s_mask[..., nb_df:, :]
            outs.append(s_df.squeeze(0).squeeze(0))
        stacked = torch.view_as_complex(torch.stack(outs, dim=0).contiguous()).numpy()
    y = df_state.synthesis(stacked)
    out = np.stack([y[0], y[1]], axis=1).astype(np.float64)
    n = min(len(out), len(x))
    return out[:n], m.squeeze(0).squeeze(0).numpy(), lsnr.squeeze().numpy()


def _b64u8(a, lo, hi):
    q = np.clip((np.asarray(a, dtype=np.float64) - lo) / max(hi - lo, 1e-9), 0.0, 1.0)
    return base64.b64encode((q * 255.0 + 0.5).astype(np.uint8).tobytes()).decode("ascii")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("tape")
    ap.add_argument("--root", default=r"C:\Projects\GithubRoot\Dictate\captures\geonar")
    ap.add_argument("--ranges", default="")
    ap.add_argument("--baseline-mm", type=float, default=157.0)
    args = ap.parse_args()

    td = os.path.join(args.root, args.tape)
    in_raw = os.path.join(td, "dd", "in.raw")
    if not os.path.isfile(in_raw):
        raise SystemExit("no raw stereo: " + in_raw)
    fx = json.load(io.open(os.path.join(td, "odas.json"), encoding="utf-8"))
    stops = json.load(io.open(os.path.join(td, "stops.json"), encoding="utf-8"))
    if args.ranges:
        for s, v in zip(stops, [float(v) for v in args.ranges.split(",")]):
            s["r"] = v

    import torch
    from df.enhance import init_df
    model, df_state, _ = init_df(log_level="ERROR")
    model.eval()
    nb_df = int(getattr(model, "nb_df", 96))
    d_m = args.baseline_mm / 1000.0

    widths = np.asarray(df_state.erb_widths(), dtype=np.float64)
    edges = np.concatenate([[0.0], np.cumsum(widths)]) * (SR / 2.0) / float(widths.sum())
    band_hz = [round(float(v), 1) for v in 0.5 * (edges[:-1] + edges[1:])]

    ons = [o for o in (fx.get("onsets") or [])
           if isinstance(o.get("utt_end_s"), (int, float)) and o["utt_end_s"] > o["t_s"] + 0.3]

    utts = []
    for si, st in enumerate(stops):
        lab = chr(ord("A") + si)
        for o in [o for o in ons if st["t0"] <= o["t_s"] <= st["t1"]]:
            t0, t1 = float(o["t_s"]), float(o["utt_end_s"])
            x = _read_stereo(in_raw, t0 - PREROLL_S, t1 + TAIL_S)
            if x is None or len(x) < 4096:
                continue
            y, mask, lsnr = dfn_pass(x, model, df_state, nb_df, torch)

            cur = {}
            for tag, sig in (("raw", x), ("dfn", y)):
                _, _, cdr_db, _ = cdr_direct(sig, d_m)
                cur[tag] = np.asarray(cdr_db, dtype=np.float64)
            nh = int(min(len(cur["raw"]), len(cur["dfn"])))

            # envelope on the SAME hop grid as cdr, so index i is one instant in both
            mono = 0.5 * (x[:, 0] + x[:, 1])
            env = np.zeros(nh)
            for i in range(nh):
                seg = mono[i * HOP:(i + 1) * HOP]
                if len(seg):
                    env[i] = float(np.abs(seg).max())

            skip = int(PREROLL_S * SR / HOP)            # where the real utterance starts, in hops
            gate_end = int((PREROLL_S + (t1 - t0)) * SR / HOP)
            utts.append({
                "stop": lab, "truth_m": st.get("r"), "t0": round(t0, 2), "t1": round(t1, 2),
                "hops": nh, "gate0": skip, "gate1": min(gate_end, nh),
                "env": _b64u8(env, 0.0, max(float(env.max()), 1e-6)),
                "env_max": round(float(env.max()), 5),
                "cdr_raw": [round(float(v), 2) for v in cur["raw"][:nh]],
                "cdr_dfn": [round(float(v), 2) for v in cur["dfn"][:nh]],
                "lsnr": [round(float(v), 2) for v in np.asarray(lsnr).ravel()],
                "mask": _b64u8(mask, 0.0, 1.0),
                "mask_t": int(mask.shape[0]),
                "d5_db": o.get("d5_db"),
            })
            print("  %s %5.2f m  %5.1f s  %4d hops  cdr_raw %6.2f  cdr_dfn %6.2f"
                  % (lab, st.get("r") or -1, t1 - t0, nh,
                     float(np.median(cur["raw"][skip:])), float(np.median(cur["dfn"][skip:]))))

    doc = {"tape": args.tape, "cdr_hop_s": round(HOP / SR, 6), "mask_hop_s": MASK_HOP_S,
           "preroll_s": PREROLL_S, "bands": len(band_hz), "band_hz": band_hz,
           "lsnr_clamp_db": -15.0, "baseline_mm": args.baseline_mm, "utts": utts}
    out_p = os.path.join(td, "dfnlab.json")
    io.open(out_p, "w", encoding="utf-8").write(json.dumps(doc))
    print("\nwrote %s  (%d utterances, %.2f MB)" % (out_p, len(utts), os.path.getsize(out_p) / 1e6))


if __name__ == "__main__":
    sys.exit(main())
