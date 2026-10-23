#!/usr/bin/env python3
"""
bench_dlm.py -- what does the Fisher model ADD on top of diart, measured on real meetings.

THE INPUT IS THE PRODUCTION INPUT, not a simulation of one: ground-truth words from AMI, labelled
by joining them to a REAL diart run over the same audio, with the same window rule blends.py uses.
So the input error is diart's actual error, including its overlap failures, not noise we invented.

    python bench_dlm.py --rttm run.rttm --words EN2002a.jsonl --until 300

Reports, per window and overall:
  before   how often diart's label agrees with who really spoke
  after    the same after the model re-attributes the window
  delta    what the model bought

SCORING IS PERMUTATION-FREE. Cluster "speaker1" is not speaker "MEE071"; the names are arbitrary on
both sides. Every window is scored under the best mapping of its labels onto its true speakers, so
a perfect diarization with the names swapped scores 100%, as it should.

TIMING IS TAKEN FROM OLLAMA'S OWN COUNTERS, not the wall clock: load / prompt / generation are
three different costs and only one of them is per-pass. A cold model reload inside the wall clock
is what makes a fast model look slow.
"""
import argparse
import itertools
import json
import sys
import time
import urllib.request

import dlm_align as dl

OLLAMA = "http://127.0.0.1:11434/api/generate"
MODEL = "diarizationlm-fisher"
MAX_WORDS = 50
MIN_WORDS = 8
NUM_THREAD = [0]        # 0 = ollama default; --threads pins it to background mode


def load_rttm(path):
    rows = []
    for line in open(path, encoding="utf-8"):
        p = line.split()
        if len(p) >= 8 and p[0] == "SPEAKER":
            rows.append({"t0": float(p[3]), "t1": float(p[3]) + float(p[4]), "spk": p[7]})
    return rows


def load_words(path, until):
    out = []
    for line in open(path, encoding="utf-8"):
        line = line.strip()
        if not line:
            continue
        d = json.loads(line)
        t = (float(d["t0"]) + float(d["t1"])) / 2.0
        if until and t > until:
            break
        if str(d.get("w") or "").strip():
            out.append({"t": t, "w": str(d["w"]).strip(), "truth": d["spk"]})
    out.sort(key=lambda x: x["t"])
    return out


def label_at(rows, t):
    """Identical join to blends.py: inside a block is confident, otherwise nearest preceding."""
    inside = [r for r in rows if r["t0"] <= t <= r["t1"]]
    if inside:
        return max(inside, key=lambda r: r["t0"])["spk"], True
    before = [r for r in rows if r["t0"] <= t]
    if not before:
        return None, False
    return max(before, key=lambda r: r["t0"])["spk"], False


def windows(tagged):
    """Contiguous stretches of at most MAX_WORDS holding exactly two hypothesis labels."""
    out, i = [], 0
    while i < len(tagged):
        take, seen = [], []
        j = i
        while j < len(tagged) and len(take) < MAX_WORDS:
            lab = tagged[j]["hyp"]
            if lab not in seen:
                if len(seen) == 2:
                    break
                seen.append(lab)
            take.append(tagged[j])
            j += 1
        if len(take) >= MIN_WORDS and len(seen) == 2:
            out.append(take)
        i = j if j > i else i + 1
    return out


def best_acc(labels, truth):
    """Accuracy under the best mapping of label names onto true speaker names."""
    ls, ts = sorted(set(labels)), sorted(set(truth))
    if not ls or not ts:
        return 0.0
    best = 0
    for perm in itertools.permutations(ts, min(len(ls), len(ts))):
        m = dict(zip(ls, perm))
        best = max(best, sum(1 for a, b in zip(labels, truth) if m.get(a) == b))
    return best / len(truth)


def ask(words, spks, po):
    body = json.dumps({
        "model": MODEL,
        "prompt": dl.create_diarized_text(words, spks, po) + po.prompt_suffix,
        "stream": False,
        "options": {"temperature": 0, "stop": ["[eod]"],
                    "num_thread": NUM_THREAD[0],
                    "num_predict": min(1024, len(words) * 3 + 64)},
    }).encode()
    req = urllib.request.Request(OLLAMA, data=body, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=300) as r:
        return json.loads(r.read())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rttm", required=True)
    ap.add_argument("--words", required=True)
    ap.add_argument("--until", type=float, default=0.0)
    ap.add_argument("--limit", type=int, default=0, help="stop after N windows")
    ap.add_argument("--out", default="")
    ap.add_argument("--threads", type=int, default=0)
    a = ap.parse_args()
    NUM_THREAD[0] = a.threads

    rows, words = load_rttm(a.rttm), load_words(a.words, a.until)
    tagged = []
    for w in words:
        lab, conf = label_at(rows, w["t"])
        if lab is None:
            continue
        tagged.append({"w": w["w"], "truth": w["truth"], "hyp": lab, "conf": conf, "t": w["t"]})
    wins = windows(tagged)
    if a.limit:
        wins = wins[:a.limit]
    print("%d words joined to %d diart rows -> %d windows\n" % (len(tagged), len(rows), len(wins)))

    po = dl.PromptOptions()
    tot_w = before_ok = after_ok = 0
    rejects = 0
    load_ms, prompt_ms, gen_ms, gen_tok = [], [], [], []
    detail = []
    for n, win in enumerate(wins, 1):
        ws = [x["w"] for x in win]
        truth = [x["truth"] for x in win]
        seen = sorted({x["hyp"] for x in win})
        m = {lab: str(i + 1) for i, lab in enumerate(seen)}
        spks = [m[x["hyp"]] for x in win]
        t0 = time.perf_counter()
        try:
            resp = ask(ws, spks, po)
        except Exception as e:                                    # noqa: BLE001
            print("  window %d: model error %s" % (n, e))
            continue
        wall = (time.perf_counter() - t0) * 1000
        new = dl.correct_labels(ws, spks, resp.get("response", "").strip(), po)
        b = best_acc(spks, truth)
        if new is None or len(new) != len(ws):
            rejects += 1
            aft = b                       # a rejected pass changes nothing, so it scores as before
            mark = "REJECT"
        else:
            aft = best_acc(new, truth)
            mark = "%+.0f%%" % ((aft - b) * 100)
        load_ms.append(resp.get("load_duration", 0) / 1e6)
        prompt_ms.append(resp.get("prompt_eval_duration", 0) / 1e6)
        gen_ms.append(resp.get("eval_duration", 0) / 1e6)
        gen_tok.append(resp.get("eval_count", 0))
        tot_w += len(ws)
        before_ok += b * len(ws)
        after_ok += aft * len(ws)
        detail.append({"n": n, "words": len(ws), "before": round(b, 3), "after": round(aft, 3),
                       "wall_ms": int(wall)})
        print("  %3d  %2dw  before %3.0f%%  after %3.0f%%  %-7s  %5dms wall "
              "(load %4dms, gen %4dms/%dtok)"
              % (n, len(ws), b * 100, aft * 100, mark, wall,
                 load_ms[-1], gen_ms[-1], gen_tok[-1]))

    if not tot_w:
        print("nothing scored")
        return 1
    print("\n%-22s %s" % ("windows scored", len(detail)))
    print("%-22s %.1f%%" % ("diart alone", before_ok / tot_w * 100))
    print("%-22s %.1f%%" % ("after fisher", after_ok / tot_w * 100))
    print("%-22s %+.1f points" % ("delta", (after_ok - before_ok) / tot_w * 100))
    print("%-22s %d" % ("rejected passes", rejects))
    if gen_ms:
        gs = sorted(gen_ms)
        tps = sum(gen_tok) / max(sum(gen_ms) / 1000.0, 1e-9)
        print("\n%-22s %.0f ms (median), %.0f ms first call" % ("model load", sorted(load_ms)[len(load_ms)//2], load_ms[0]))
        print("%-22s %.0f ms (median)" % ("prompt eval", sorted(prompt_ms)[len(prompt_ms)//2]))
        print("%-22s %.0f ms (median), %.0f tok/s" % ("generation", gs[len(gs)//2], tps))
    if a.out:
        with open(a.out, "w", encoding="utf-8") as f:
            json.dump({"detail": detail, "before": before_ok / tot_w, "after": after_ok / tot_w},
                      f, indent=1)
        print("\nwrote %s" % a.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
