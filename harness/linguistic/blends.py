#!/usr/bin/env python3
"""
blends.py -- the Fisher model as AUDITOR and CORRECTOR of the acoustic attribution.

Its own process, like identity.py, for the same reason: live.py diarizes and serves. If this dies,
or the model stalls, or Ollama is not running, words keep painting from pitch exactly as before and
nobody notices except this page. It is never on the critical path -- the acoustic layer places every
word the moment it is spoken, and this arrives behind with corrections and flags.

WHY IT IS NOT ALLOWED TO SIMPLY DECIDE. It is very good at this -- better, measured, than audio
separation -- but it reads TEXT. It cannot know that speaker 1 is Jay, it cannot know where anybody
is sitting, and it cannot rule until the sentence exists. So it corrects, and it disagrees, and the
acoustics keep the final say on anything the acoustics were sure about.

PRECEDENCE, the whole contract in three lines:
  - a word the acoustics placed confidently keeps its speaker; a model disagreement is RECORDED
  - a word the acoustics declined to place is the model's to rule on
  - a pass that moves too many CONFIDENT words is rejected wholesale

THE N-TO-2 PROBLEM. The model is tuned on Fisher: two-party telephone calls. Feeding it three
speakers makes it collapse two of them together. The decomposition is by CONTIGUOUS WINDOW, never
by speaker filter -- walk backwards from the newest word until a third speaker would enter, and stop
there. Every pass is then a real two-party exchange with no holes in it.

Filtering instead (keep A and C, drop B) would produce a text where A and C appear to answer each
other at moments they never did, which corrupts the exact signal -- conversational continuity -- that
the model is being paid for.

Windows overlap, so N speakers are covered by a rolling chain of dyads: A/B, then B/C as C takes
over, then C/A. Every speaker is judged against whoever they actually speak NEXT TO, which is the
only place a handoff can be ambiguous. Two speakers who never spoke adjacently never needed a pass.

NO BUFFERS. Every pass re-reads the journal from live.py and holds nothing between passes. The only
memory is which window was last judged, so an unchanged window is not re-asked.
"""
import argparse
import json
import sys
import threading
import time
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import dlm_align as dl

DIART = "http://127.0.0.1:8822"
OLLAMA = "http://127.0.0.1:11434/api/generate"
MODEL = "diarizationlm-fisher"

# MEASURED, NOT CHOSEN. 96-word and 109-word prompts came back with no speaker tags at all -- the
# model stops doing the task rather than doing it badly, so this is a validity limit and not a
# speed one.
MAX_WORDS = 50
MIN_WORDS = 8

# HOW MANY CONFIDENT WORDS MAY MOVE before the whole pass is refused.
#
# The denominator is the CONFIDENT words alone, and that is the important part. The original guard
# counted moves against every word in the window, on the assumption that a large move meant the
# model had gone rogue. That assumption is wrong: hand it a window whose tags alternate speaker by
# speaker and it still returns the right attribution, because it re-derives from the text rather
# than propagating what it was given. Under the old denominator, the passes that fixed the most
# would have been the first ones thrown away. Moving undecided words is the job. Moving words pitch
# was sure about is the thing worth refusing.
MAX_CONF_MOVE = 0.34

STATE = {"passes": 0, "applied": 0, "moved": 0, "flags": 0, "rejects": 0, "skipped": 0,
         "last": "idle", "last_ms": 0, "window": ""}
FLAGS = []               # confident words the model disagreed about: the audit trail


def _get(url, timeout=4):
    with urllib.request.urlopen(url, timeout=timeout) as f:
        return json.loads(f.read() or b"{}")


def label_at(rows, t):
    """(cluster label, confident?) for a word at time t on diart's clock.

    CONFIDENT means the word falls INSIDE a diarized block. A word that lands in a gap -- between
    blocks, at a handoff, in the silence the cutter did not claim -- gets the nearest preceding
    block's label as a HYPOTHESIS, flagged unconfident. That is the same fallback the page draws
    with, so this judges exactly what the viewer sees, and it is also precisely the population the
    model is here to rule on.
    """
    inside = [r for r in rows if r["t0"] <= t <= r["t1"]]
    if inside:
        return max(inside, key=lambda r: r["t0"])["spk"], True
    before = [r for r in rows if r["t0"] <= t]
    if not before:
        return None, False
    return max(before, key=lambda r: r["t0"])["spk"], False


def window_of(words, rows):
    """The newest contiguous stretch containing exactly two speakers.

    Walks backwards and stops the moment a THIRD label would enter. Returns the words in order with
    their hypothesis label and whether the acoustics were confident about it.
    """
    tagged = []
    for w in words:
        if w.get("kind") == "partial" or not str(w.get("text") or "").strip():
            continue            # a partial is a hypothesis about SOUND; it has no place here
        lab, conf = label_at(rows, float(w.get("t") or 0.0))
        if lab is None:
            continue
        tagged.append((w, lab, conf))
    take, seen = [], []
    for item in reversed(tagged):
        lab = item[1]
        if lab not in seen:
            if len(seen) == 2:
                break           # a third speaker: the window ends here, with no hole in it
            seen.append(lab)
        take.append(item)
        if len(take) >= MAX_WORDS:
            break
    take.reverse()
    return take, seen


# HOW MANY CORES THE AUDITOR MAY TAKE. This is the reason it can run behind everything else
# without being felt: it is a background job by parameter, not by hope. The original
# implementation pinned it at 3 and that is where this starts; --threads moves it.
NUM_THREAD = [3]


def ask(words, spks, po):
    """One completion from the Fisher model. Returns the raw string, or None."""
    body = json.dumps({
        "model": MODEL,
        "prompt": dl.create_diarized_text(words, spks, po) + po.prompt_suffix,
        "stream": False,
        "options": {"temperature": 0, "stop": ["[eod]"],
                    "num_thread": NUM_THREAD[0],
                    "num_predict": min(1024, len(words) * 3 + 64)},
    }).encode()
    req = urllib.request.Request(OLLAMA, data=body, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=180) as r:
        return json.loads(r.read()).get("response", "").strip()


def post_moves(moves, flags):
    """Hand the ruling back to live.py. Moves repaint; flags are recorded and drawn, never applied."""
    body = json.dumps({"moves": moves, "flags": flags}).encode()
    req = urllib.request.Request(DIART + "/moves", data=body,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=5) as r:
        r.read()


def one_pass(po, last_key):
    words = (_get(DIART + "/words").get("words") or [])
    rows = (_get(DIART + "/rows").get("rows") or [])
    if not words or not rows:
        STATE["last"] = "nothing to judge yet"
        return last_key
    take, seen = window_of(words, rows)
    if len(take) < MIN_WORDS or len(seen) < 2:
        STATE["last"] = "one voice (%d words, %d speakers)" % (len(take), len(seen))
        return last_key
    key = (take[0][0]["seq"], take[-1][0]["seq"])
    if key == last_key:
        STATE["skipped"] += 1
        return last_key                       # the window has not moved; asking again is churn

    # THE TWO REAL LABELS BECOME "1" AND "2", sorted so the mapping is stable across passes and a
    # speaker does not swap numbers mid-conversation for no reason.
    m = {lab: str(i + 1) for i, lab in enumerate(sorted(seen))}
    inv = {v: k for k, v in m.items()}
    ws = [str(w["text"]).strip() for w, _l, _c in take]
    spks = [m[l] for _w, l, _c in take]
    conf = [c for _w, _l, c in take]
    STATE["window"] = "%dw %s" % (len(ws), "/".join(sorted(seen)))

    t0 = time.perf_counter()
    try:
        completion = ask(ws, spks, po)
    except Exception as e:                                        # noqa: BLE001
        STATE["last"] = "model unreachable: %s" % e
        return key
    STATE["last_ms"] = int((time.perf_counter() - t0) * 1000)
    STATE["passes"] += 1

    new = dl.correct_labels(ws, spks, completion or "", po)
    if new is None or len(new) != len(ws):
        STATE["rejects"] += 1
        STATE["last"] = "REJECT tagless (%s)" % STATE["window"]
        return key

    n_conf = sum(1 for c in conf if c) or 1
    conf_moved = sum(1 for i in range(len(ws)) if conf[i] and new[i] != spks[i])
    if conf_moved / n_conf > MAX_CONF_MOVE:
        STATE["rejects"] += 1
        STATE["last"] = "REJECT moved %d/%d confident (%s)" % (conf_moved, n_conf, STATE["window"])
        return key

    moves, flags = [], []
    for i, (w, lab, c) in enumerate(take):
        if new[i] == spks[i]:
            continue
        to = inv.get(new[i])
        if to is None:
            continue
        if c:
            # A CONFIDENT WORD IS NOT MOVED. Pitch placed it and pitch wins; this is the audit
            # trail instead. A cluster that collects these steadily is the tell that two people
            # merged into one profile -- which is the one failure the acoustic layer cannot see
            # from the inside, because a merged profile just looks like a wide speaker.
            flags.append({"seq": w["seq"], "text": w["text"], "was": lab, "says": to,
                          "t": w["t"]})
        else:
            moves.append({"seq": w["seq"], "to": to})

    if moves or flags:
        try:
            post_moves(moves, flags)
            STATE["applied"] += len(moves)
            STATE["moved"] += len(moves)
            STATE["flags"] += len(flags)
            FLAGS.extend(flags)
            del FLAGS[:-200]
        except Exception as e:                                    # noqa: BLE001
            STATE["last"] = "could not post: %s" % e
            return key
    STATE["last"] = "%s -> %d moved, %d flagged (%dms)" % (
        STATE["window"], len(moves), len(flags), STATE["last_ms"])
    return key


def loop(interval):
    po = dl.PromptOptions()
    last_key = None
    while True:
        time.sleep(interval)
        try:
            last_key = one_pass(po, last_key)
        except Exception as e:                                    # noqa: BLE001
            STATE["last"] = "pass failed: %s" % e


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_GET(self):
        body = json.dumps({"state": STATE, "flags": FLAGS[-40:], "model": MODEL}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--http", type=int, default=8825)
    # HOW OFTEN TO LOOK. The model is alone on this box now -- it used to share it with the
    # recogniser, which is where the old 30s cooldown came from. A pass on a window that has not
    # changed costs nothing (it is skipped by key), so this is just how promptly a correction
    # lands behind the live paint.
    ap.add_argument("--interval", type=float, default=2.0)
    ap.add_argument("--threads", type=int, default=NUM_THREAD[0],
                    help="cores the model may use; this is what makes it a background job")
    a = ap.parse_args()
    NUM_THREAD[0] = a.threads
    threading.Thread(target=loop, args=(a.interval,), daemon=True).start()
    print("blends: auditing %s on %d threads, answers on http:%d"
          % (MODEL, a.threads, a.http), flush=True)
    ThreadingHTTPServer(("127.0.0.1", a.http), H).serve_forever()


if __name__ == "__main__":
    sys.exit(main())
