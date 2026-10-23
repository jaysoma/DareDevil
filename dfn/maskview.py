r"""maskview.py <tape> -- bakes maskview.json: the whole tape as one timeline, raw against DFN's mask.

JAY, 2026-10-02: "Let me see a visualization of the raw track, and the mask track with a time slider
so I can drag back and forth. Less is more."

WHY THE WHOLE TAPE AND NOT PER UTTERANCE. dfnlab.json is cut into utterances, which is right for
comparing one arrival with another but wrong for dragging through a walk -- the interesting thing is
what happens BETWEEN the marked moments, and a per-utterance file has thrown that away.

ONE GRID FOR EVERYTHING. DFN works in 10 ms frames, so the raw level is measured in 10 ms frames too
rather than on the CDR hop (10.67 ms) the rest of the project uses. A page that has to reconcile two
grids draws two lines that disagree by half a frame and the disagreement looks like a finding.

MONO ONLY, DELIBERATELY. The shared-mask pass stacks L, R and the mixdown because it needs all three
denoised. Here only the MASK and the lsnr are wanted, and both are computed from the mixdown alone --
so one channel through the model instead of three, which is also what keeps an 85 s tape inside
memory in a single pass.

WHAT IS CARRIED, all on the same 10 ms grid:
    raw_db / lf_db / mf_db / hf_db   the untouched signal, broadband and in three bands
    mask_mean                        the average of DFN's 32 ERB gains -- how much it kept
    lsnr                             DFN's own speech-to-noise estimate, clamped at -15 dB
    mask32                           the full [T, 32] gain map, for an optional heatmap
Plus the onsets and the decode, so the timeline can be read against what was being said.
"""
import argparse
import base64
import io
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cdr_direct import SR                                      # noqa: E402
from rot_bearing import source_of, read_stereo                 # noqa: E402

FRAME = 480                        # 10 ms at 48 kHz -- DFN3's own hop
BANDS = [("LF", 100.0, 1000.0), ("MF", 1000.0, 4000.0), ("HF", 4000.0, 8000.0)]
# The levels are 10 log10 of the summed power of a Hann-windowed 10 ms frame, NOT dBFS: dBFS = this - 46.35
# (Render.html applies that offset). The old range, -95..-5, clipped everything above about -51 dBFS, so on
# walk-205043 more than half the frames sat on the ceiling. This range covers -96..-1 dBFS.
DB_LO, DB_HI = -50.0, 45.0
LSNR_LO, LSNR_HI = -16.0, 36.0
CHUNK_S = 20.0                     # DFN in slices, so a long tape cannot blow memory


def q8(a, lo, hi):
    v = np.clip((np.asarray(a, dtype=np.float64) - lo) / max(hi - lo, 1e-9), 0, 1)
    return base64.b64encode((v * 255 + 0.5).astype(np.uint8).tobytes()).decode("ascii")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("tape")
    ap.add_argument("--root", default=r"C:\Projects\GithubRoot\Dictate\captures\geonar")
    ap.add_argument("--atten", type=float, default=0.0, help="0 = uncapped; the app ships 12")
    args = ap.parse_args()

    import torch
    from df.enhance import init_df, df_features
    model, df_state, _ = init_df(log_level="ERROR")
    model.eval()
    nb_df = int(getattr(model, "nb_df", 96))

    td = os.path.join(args.root, args.tape)
    fx = json.load(io.open(os.path.join(td, "odas.json"), encoding="utf-8"))
    dur = float(fx.get("duration") or 0.0)
    src = source_of(td, args.root, args.tape)

    x = read_stereo(src, 0.0, dur)
    if x is None:
        raise SystemExit("could not read " + args.tape)
    mono = (0.5 * (x[:, 0] + x[:, 1])).astype(np.float32)
    n = len(mono) // FRAME
    print("%s  %.2f s  %d frames of %d samples" % (args.tape, dur, n, FRAME))

    # ---- the raw side, on the same 10 ms grid ------------------------------------------------
    idx = np.arange(FRAME)[None, :] + FRAME * np.arange(n)[:, None]
    fr = mono[idx].astype(np.float64)
    w = np.hanning(FRAME)
    S = np.abs(np.fft.rfft(fr * w, axis=1)) ** 2
    f = np.fft.rfftfreq(FRAME, 1.0 / SR)
    raw_db = 10.0 * np.log10(S.sum(axis=1) + 1e-20)
    band_db = {}
    for nm, lo, hi in BANDS:
        m = (f >= lo) & (f < hi)
        band_db[nm] = 10.0 * np.log10(S[:, m].sum(axis=1) + 1e-20)

    # ---- the model side, in chunks -----------------------------------------------------------
    masks, lsnrs = [], []
    step = int(CHUNK_S * SR) // FRAME * FRAME
    with torch.no_grad():
        for a in range(0, len(mono), step):
            seg = mono[a:a + step]
            if len(seg) < FRAME * 4:
                break
            spec, erb_feat, spec_feat = df_features(
                torch.from_numpy(seg[None, :]), df_state, nb_df, device="cpu")
            _, m_, ls_, _ = model(spec.clone(), erb_feat, spec_feat)
            masks.append(np.squeeze(m_.numpy()))
            lsnrs.append(np.squeeze(ls_.numpy()).ravel())
            print("  frames %6d .. %6d" % (a // FRAME, a // FRAME + masks[-1].shape[0]), flush=True)
    mask = np.concatenate(masks, axis=0)
    lsnr = np.concatenate(lsnrs, axis=0)

    k = min(n, mask.shape[0], len(lsnr))
    mask, lsnr = mask[:k], lsnr[:k]
    raw_db = raw_db[:k]
    for nm in band_db:
        band_db[nm] = band_db[nm][:k]
    mask_mean = mask.mean(axis=1)

    wp = os.path.join(args.root, args.tape + "-whisper.json")
    segs = []
    if os.path.isfile(wp):
        segs = [{"t": round(float(s.get("t0", s.get("start")) or 0), 2),
                 "text": (s.get("text") or "")[:120]}
                for s in (json.load(io.open(wp, encoding="utf-8")).get("segments") or [])
                if s.get("text")]

    ons = [{"t_s": round(float(o["t_s"]), 3),
            "gate_t_s": (round(float(o["gate_t_s"]), 3)
                         if isinstance(o.get("gate_t_s"), (int, float)) else None),
            "end_s": (round(float(o["utt_end_s"]), 3)
                      if isinstance(o.get("utt_end_s"), (int, float)) else None),
            "margin_db": round((o.get("d5_db") or 0) - (o.get("floor_db") or 0), 1)}
           for o in (fx.get("onsets") or [])]

    doc = {"tape": args.tape, "frame_ms": FRAME * 1000.0 / SR, "n": int(k),
           "duration": round(dur, 2), "atten_db": args.atten,
           "db_lo": DB_LO, "db_hi": DB_HI, "lsnr_lo": LSNR_LO, "lsnr_hi": LSNR_HI,
           "bands": [[b[0], b[1], b[2]] for b in BANDS],
           "raw_db": q8(raw_db, DB_LO, DB_HI),
           "lf_db": q8(band_db["LF"], DB_LO, DB_HI),
           "mf_db": q8(band_db["MF"], DB_LO, DB_HI),
           "hf_db": q8(band_db["HF"], DB_LO, DB_HI),
           "mask_mean": q8(mask_mean, 0.0, 1.0),
           "lsnr": q8(lsnr, LSNR_LO, LSNR_HI),
           "mask32": q8(mask.T.ravel(), 0.0, 1.0), "mask_bands": int(mask.shape[1]),
           "onsets": ons, "decode": segs}
    out = os.path.join(td, "maskview.json")
    io.open(out, "w", encoding="utf-8").write(json.dumps(doc))
    print("\nwrote %s  (%d frames, %.2f MB)  mask mean %.3f  lsnr mean %+.2f dB"
          % (out, k, os.path.getsize(out) / 1e6, mask_mean.mean(), lsnr.mean()))


if __name__ == "__main__":
    sys.exit(main())
