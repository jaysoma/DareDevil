#!/usr/bin/env python3
r"""maskview_starss.py -- the Mask View bake for a STARSS23 recording, with its labelled sounds.

Jay, 2026-10-23: "maskview should be set up to display the data from STARSS." The walk bakes (maskview.py) carry
the app's own onsets and a Whisper transcript. A STARSS23 recording carries something better for a reader who
isn't Jay: every sound is labelled by the Tampere/Sony annotators, with its class, source, direction and distance
in 100 ms frames. So this bake keeps maskview.py's tracks and grid exactly, and swaps the walk's overlays for the
labels.

SAME DOCUMENT AS maskview.py. Every field the Mask View and Render.html read is here with the same name, scale and
grid (10 ms DFN frames, the same q8 ranges). What differs:
    onsets   one entry per labelled event: t_s (its first label frame), end_s, gate_t_s null, plus kind
             ("speech" or "other"), cls and label.
    decode   the same events as readable lines ({t, end, kind, text}), in time order, for the event list.
    source   "starss23", with the recording, room, capsule pair and the label convention.

WHAT GOES INTO THE MODEL. One capsule pair of the MIC format, mixed down to mono the way the app mixes L and R,
then 24 kHz -> 48 kHz (DFN3 runs at 48 kHz). Nothing is recorded above 12 kHz, so DFN's top ERB bands see only the
resampler's floor. The level is as recorded: no gain, no normalisation (Jay's rule: a fixed gain or nothing).

LEVEL. STARSS23's MIC files are quiet: active speech sits around -50 to -65 dBFS, and as recorded DFN calls almost
all of it noise (lsnr stays at its -15 dB floor). So the model is run twice. As recorded, for the record (doc
"as_recorded"), and with ONE FIXED GAIN for the whole recording that brings labelled active speech to SPEECH_DBFS
(brief 16's -26 dBFS). That gain is what the tracks show (doc "gain_db"). A fixed gain changes no phase and no
ratio between channels; it is not AGC. raw_db and the band levels stay as recorded.

THE LABELS. STARSS23 metadata rows: frame (100 ms), class, source index, azimuth, elevation, distance (cm).
Azimuth is 0 deg straight ahead and positive to the left (counter-clockwise), per the dataset. An event is a run
of frames of one class and source index; a gap of more than GAP_FRAMES starts a new event. Label frames are 100 ms,
so an onset can be up to 100 ms early or late against the audio.

    python3 dfn/maskview_starss.py <starss23 root> <recording> <out.json> [--pair 1,2]

<starss23 root> holds mic_dev/ and metadata_dev/ as unzipped from https://zenodo.org/records/7880637.
"""
import argparse
import base64
import csv
import glob
import json
import os
import sys

import numpy as np

SR = 48000
FRAME = 480                        # 10 ms at 48 kHz: DFN3's own hop
BANDS = [("LF", 100.0, 1000.0), ("MF", 1000.0, 4000.0), ("HF", 4000.0, 8000.0)]
DB_LO, DB_HI = -50.0, 45.0         # as maskview.py: dBFS = this - 46.35
LSNR_LO, LSNR_HI = -16.0, 36.0
CHUNK_S = 20.0
GAP_FRAMES = 3                     # a gap of more than 300 ms in one class and source starts a new event
LABEL_S = 0.1
SPEECH_DBFS = -26.0                # brief 16: one fixed gain brings active speech here
CLASSES = ["Female speech", "Male speech", "Clapping", "Telephone", "Laughter", "Domestic sounds", "Footsteps",
           "Door", "Music", "Musical instrument", "Water tap", "Bell", "Knock"]
SPEECH = {0, 1}


def q8(a, lo, hi):
    v = np.clip((np.asarray(a, dtype=np.float64) - lo) / max(hi - lo, 1e-9), 0, 1)
    return base64.b64encode((v * 255 + 0.5).astype(np.uint8).tobytes()).decode("ascii")


def events_of(csv_path):
    """Runs of one class and source index, with direction and distance at the first frame."""
    rows = sorted((int(r[0]), int(r[1]), int(r[2]), float(r[3]), float(r[4]), float(r[5]))
                  for r in csv.reader(open(csv_path)) if r)
    open_ev, out = {}, []
    for fr, c, s, az, el, dist in rows:
        key = (c, s)
        e = open_ev.get(key)
        if e is None or fr - e["last"] > GAP_FRAMES:
            e = {"cls": c, "src": s, "first": fr, "last": fr, "az": az, "el": el, "dist_cm": dist}
            open_ev[key] = e
            out.append(e)
        e["last"] = fr
    out.sort(key=lambda e: (e["first"], e["cls"], e["src"]))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("root")
    ap.add_argument("recording")
    ap.add_argument("out")
    ap.add_argument("--pair", default="1,2", help="the two MIC-format capsules mixed down, 1-based")
    ap.add_argument("--speech-dbfs", type=float, default=SPEECH_DBFS, help="target level of labelled active speech")
    args = ap.parse_args()
    p, q = (int(v) - 1 for v in args.pair.split(","))

    wavs = glob.glob(os.path.join(args.root, "mic_dev", "*", args.recording + ".wav"))
    csvs = glob.glob(os.path.join(args.root, "metadata_dev", "*", args.recording + ".csv"))
    if len(wavs) != 1 or len(csvs) != 1:
        raise SystemExit("need exactly one wav and one csv for %s, found %d and %d" % (args.recording, len(wavs), len(csvs)))

    import soundfile as sf
    from scipy.signal import resample_poly
    x, sr_in = sf.read(wavs[0], dtype="float32", always_2d=True)
    mono24 = 0.5 * (x[:, p] + x[:, q])
    mono = resample_poly(mono24, SR // sr_in, 1).astype(np.float32) if sr_in != SR else mono24.astype(np.float32)
    dur = len(mono) / SR
    n = len(mono) // FRAME
    print("%s  %d ch at %d Hz, capsules %d+%d  %.2f s  %d frames" % (args.recording, x.shape[1], sr_in, p + 1, q + 1, dur, n))

    # ---- the raw side, on the 10 ms grid (as maskview.py) --------------------------------------
    idx = np.arange(FRAME)[None, :] + FRAME * np.arange(n)[:, None]
    fr = mono[idx].astype(np.float64)
    S = np.abs(np.fft.rfft(fr * np.hanning(FRAME), axis=1)) ** 2
    f = np.fft.rfftfreq(FRAME, 1.0 / SR)
    raw_db = 10.0 * np.log10(S.sum(axis=1) + 1e-20)
    band_db = {nm: 10.0 * np.log10(S[:, (f >= lo) & (f < hi)].sum(axis=1) + 1e-20) for nm, lo, hi in BANDS}

    # ---- the labels ----------------------------------------------------------------------------
    evs = events_of(csvs[0])

    # ---- one fixed gain: labelled active speech to the target level --------------------------
    live = np.zeros(len(mono), dtype=bool)
    for e in evs:
        if e["cls"] in SPEECH:
            live[int(e["first"] * LABEL_S * SR):int((e["last"] + 1) * LABEL_S * SR)] = True
    speech_dbfs = 10.0 * np.log10(float(np.mean(mono[live].astype(np.float64) ** 2)) + 1e-20) if live.any() else None
    gain_db = round(args.speech_dbfs - speech_dbfs, 1) if speech_dbfs is not None else 0.0
    print("labelled active speech %.1f dBFS -> fixed gain %+.1f dB" % (speech_dbfs, gain_db))

    # ---- the model side, in chunks (as maskview.py) -------------------------------------------
    import torch
    from df.enhance import init_df, df_features
    model, df_state, _ = init_df(log_level="ERROR")
    model.eval()
    nb_df = int(getattr(model, "nb_df", 96))
    step = int(CHUNK_S * SR) // FRAME * FRAME

    def run(sig):
        masks, lsnrs = [], []
        with torch.no_grad():
            for a in range(0, len(sig), step):
                seg = sig[a:a + step]
                if len(seg) < FRAME * 4:
                    break
                spec, erb_feat, spec_feat = df_features(torch.from_numpy(seg[None, :]), df_state, nb_df, device="cpu")
                _, m_, ls_, _ = model(spec.clone(), erb_feat, spec_feat)
                masks.append(np.squeeze(m_.numpy()))
                lsnrs.append(np.squeeze(ls_.numpy()).ravel())
        return np.concatenate(masks, axis=0), np.concatenate(lsnrs, axis=0)

    mask0, lsnr0 = run(mono)
    as_recorded = {"speech_dbfs": round(speech_dbfs, 1) if speech_dbfs is not None else None,
                   "mask_mean": round(float(mask0.mean()), 3), "lsnr_mean": round(float(lsnr0.mean()), 2),
                   "lsnr_above_0_pct": round(100 * float((lsnr0 > 0).mean()), 1)}
    mask, lsnr = run((mono * 10 ** (gain_db / 20)).astype(np.float32))
    k = min(n, mask.shape[0], len(lsnr))
    mask, lsnr, raw_db = mask[:k], lsnr[:k], raw_db[:k]
    band_db = {nm: v[:k] for nm, v in band_db.items()}
    mask_mean = mask.mean(axis=1)

    onsets, decode = [], []
    for e in evs:
        t0, t1 = round(e["first"] * LABEL_S, 2), round((e["last"] + 1) * LABEL_S, 2)
        kind = "speech" if e["cls"] in SPEECH else "other"
        name = CLASSES[e["cls"]]
        text = "%s · source %d · az %+d° el %+d° · %.2f m" % (name, e["src"], round(e["az"]), round(e["el"]),
                                                              e["dist_cm"] / 100.0)
        onsets.append({"t_s": t0, "gate_t_s": None, "end_s": t1, "margin_db": None, "kind": kind, "cls": e["cls"],
                       "label": name})
        decode.append({"t": t0, "end": t1, "kind": kind, "text": text})

    room = args.recording.split("_")[1] if "_" in args.recording else ""
    doc = {"tape": args.recording, "frame_ms": FRAME * 1000.0 / SR, "n": int(k), "duration": round(dur, 2),
           "atten_db": 0.0, "gain_db": gain_db, "speech_dbfs_target": args.speech_dbfs, "as_recorded": as_recorded,
           "db_lo": DB_LO, "db_hi": DB_HI, "lsnr_lo": LSNR_LO, "lsnr_hi": LSNR_HI,
           "bands": [[b[0], b[1], b[2]] for b in BANDS],
           "raw_db": q8(raw_db, DB_LO, DB_HI), "lf_db": q8(band_db["LF"], DB_LO, DB_HI),
           "mf_db": q8(band_db["MF"], DB_LO, DB_HI), "hf_db": q8(band_db["HF"], DB_LO, DB_HI),
           "mask_mean": q8(mask_mean, 0.0, 1.0), "lsnr": q8(lsnr, LSNR_LO, LSNR_HI),
           "mask32": q8(mask.T.ravel(), 0.0, 1.0), "mask_bands": int(mask.shape[1]),
           "onsets": onsets, "decode": decode,
           "source": {"dataset": "starss23", "recording": args.recording, "room": room,
                      "split": os.path.basename(os.path.dirname(wavs[0])), "pair": [p + 1, q + 1], "sr_in": int(sr_in),
                      "labels": "STARSS23 metadata, 100 ms frames; azimuth 0 deg ahead, positive to the left",
                      "url": "https://zenodo.org/records/7880637"}}
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(doc, fh)
    sp = sum(o["kind"] == "speech" for o in onsets)
    print("wrote %s (%d frames, %.2f MB): %d events, %d speech" % (args.out, k, os.path.getsize(args.out) / 1e6,
                                                                    len(onsets), sp))
    print("  as recorded:  mask mean %.3f, lsnr mean %+.2f dB, above 0 dB %.1f%%"
          % (as_recorded["mask_mean"], as_recorded["lsnr_mean"], as_recorded["lsnr_above_0_pct"]))
    print("  gain %+.1f dB: mask mean %.3f, lsnr mean %+.2f dB, above 0 dB %.1f%%"
          % (gain_db, mask_mean.mean(), lsnr.mean(), 100 * (lsnr > 0).mean()))


if __name__ == "__main__":
    sys.exit(main())
