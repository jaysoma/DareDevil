#!/usr/bin/env python3
"""
stage3.py -- STAGE 3, LIVE: decoded words sorted into speakers in real time (Jay 2026-10-14).

    phone (every decoded phrase) -> Dictate merge stream -> this -> Fisher, streamed -> /voice/who

TEXT ONLY. No pitch, no audio, no timing, no phrase boundaries: nothing acoustic touches a label.
The recogniser's phrases are read for one thing, the ORDER of the words.

REAL TIME, three ways (10-14 -- the first run sat 10-30 s behind):
  ONE PASS PER SEALED PHRASE. The phrase is the event; a phrase that lands mid-pass is in the next.
  SHORT CONTEXT. A pass is the last CONTEXT settled words plus what is new. Fisher re-emits the whole
                 window before it reaches the new words, so the window's length IS the latency.
  STREAMED. Ollama streams the completion; each new word is placed and sent to the page the moment
            its speaker tag comes out, not when the pass ends.

THE ANNOTATION. A new word enters with an uninformative label, alternating word by word -- the prior
wordprint.py records Fisher still sorts into correct turns. Settled words keep their labels. The
FIRST pass waits for MIN_WORDS: on a short window with nothing settled, Fisher echoes the alternation
back instead of sorting it (measured 10-14: 20 words echoed, 60 sorted).

1 -> N (blends.py, the argument Jay won). Fisher is two-party. The context is CONTIGUOUS, walked back
from the newest settled word until a third speaker would enter -- never a speaker filter. A window's
labels are relative; the settled words in it pin them onto the running speakers by majority. A label
with no settled words behind it is the window's other known speaker, else whoever spoke most recently
before the window, else somebody new. Nothing is told how many people there are.

ONE PASS AT A TIME, off the reading thread (live_attrib.py, measured: a pass run inline stalls the
stream). Serves /stream (SSE, one event per placed word) and /status on 127.0.0.1:8832 -- local only.
When Dictate's feed closes this exits and the page says so; nothing reconnects.

Run (windowless):  DiartLab\.venv\Scripts\pythonw.exe stage3.py
"""
import json
import threading
import time
import urllib.request
from collections import deque
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import dlm_align as dl

FEED = "http://127.0.0.1:8012/ODAS_SpeechRecognizer_Merge_Stream"
OLLAMA = "http://127.0.0.1:11434/api/generate"
MODEL = "diarizationlm-fisher"
PORT = 8832
CONTEXT = 16          # settled words a pass carries -- each one costs latency before a new word
MAX_NEW = 80          # new words one pass takes on; more wait for the next pass, oldest first
MIN_WORDS = 40        # the first pass waits for this much text (the echo, above)
KEEP = 400            # words remembered; nothing older can enter a window anyway
NAMES = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"

PO = dl.PromptOptions()
LOCK = threading.Lock()
WORDS = []            # {"w": as decoded, "n": normalised for the model, "spk": None | "A".."Z"}
STATE = {"feed": "connecting", "words": 0, "passes": 0, "rejects": 0, "speakers": 0,
         "first_word_ms": 0, "pass_ms": 0, "last": ""}
_busy = threading.Semaphore(1)
_next = [0]
_subs = []
_backlog = deque(maxlen=3000)


def new_speaker():
    name = NAMES[min(_next[0], len(NAMES) - 1)]
    _next[0] += 1
    STATE["speakers"] = min(_next[0], len(NAMES))
    return name


def publish(ev):
    _backlog.append(ev)
    for q, bell in list(_subs):
        q.append(ev)
        bell.set()


def pick(seen, used, before):
    """Who a window label with no settled words behind it belongs to."""
    for g in seen:                              # the window's other known speaker
        if g not in used:
            return g
    for w in reversed(before):                  # whoever spoke most recently before the window
        if w["spk"] and w["spk"] not in used:
            return w["spk"]
    return new_speaker()                        # nobody else known: somebody new


class Pass:
    """One streamed Fisher pass: places completion words onto the window's words as they arrive."""

    def __init__(self, ctx, new, before):
        self.win = ctx + new
        self.n_ctx = len(ctx)
        self.before = before
        self.ns = [w["n"] for w in self.win]
        self.labels = [None] * len(self.win)
        self.seen = []
        for w in ctx:
            if w["spk"] not in self.seen:
                self.seen.append(w["spk"])
        rel = {g: str(k + 1) for k, g in enumerate(self.seen)}
        alt = iter("12" * len(new))
        self.prior = [rel[w["spk"]] for w in ctx] + [next(alt) for _ in new]
        self.k = 0                              # the next window word a completion word lands on
        self.cur = "1"
        self.votes = {}
        self.mapping = None
        self.t0 = time.perf_counter()
        self.first = None

    def word(self, cw):
        """A completion word arrived under the current tag: place it, allowing a skipped word or two."""
        k, placed = self.k, []
        for j in range(k, min(k + 4, len(self.ns))):
            if self.ns[j] == cw:
                placed = list(range(k, j + 1))
                break
        if not placed and k < len(self.ns):
            placed = [k]                        # a substitution: the model reworded this one
        for i in placed:
            self.settle(i, self.cur)
        if placed:
            self.k = placed[-1] + 1

    def settle(self, i, lab):
        self.labels[i] = lab
        w = self.win[i]
        if i < self.n_ctx:                      # context: a vote for which speaker this label is
            d = self.votes.setdefault(lab, {})
            d[w["spk"]] = d.get(w["spk"], 0) + 1
            return
        if self.mapping is None:                # the first new word: the context is all in, so map
            self.mapping, used = {}, set()
            for _, l, g in sorted(((c, l, g) for l, d in self.votes.items() for g, c in d.items()),
                                  reverse=True):
                if l not in self.mapping and g not in used:
                    self.mapping[l] = g
                    used.add(g)
        if lab not in self.mapping:
            with LOCK:
                self.mapping[lab] = pick(self.seen, set(self.mapping.values()), self.before)
        w["spk"] = self.mapping[lab]
        if self.first is None:
            self.first = time.perf_counter()
            STATE["first_word_ms"] = int((self.first - self.t0) * 1000)
        publish({"spk": w["spk"], "w": w["w"]})

    def finish(self):
        """Words the model dropped take the label of the word before them -- no holes."""
        lab = self.labels[self.n_ctx - 1] if self.n_ctx else "1"
        for i in range(self.n_ctx, len(self.win)):
            if self.labels[i] is None:
                self.settle(i, lab)
            lab = self.labels[i]


def run_pass():
    with LOCK:
        settled = [w for w in WORDS if w["spk"]]
        new = [w for w in WORDS if not w["spk"]][:MAX_NEW]
        if not new or (not settled and len(new) < MIN_WORDS):
            return False
        ctx, seen = [], []
        for w in reversed(settled):             # contiguous, back from the newest settled word
            if len(ctx) >= CONTEXT:
                break
            if w["spk"] not in seen:
                if len(seen) == 2:
                    break                       # a third speaker would enter: the dyad ends here
                seen.append(w["spk"])
            ctx.insert(0, w)
        before = settled[:len(settled) - len(ctx)]
    p = Pass(ctx, new, before)
    body = json.dumps({
        "model": MODEL,
        "prompt": dl.create_diarized_text(p.ns, p.prior, PO) + PO.prompt_suffix,
        "stream": True,
        "keep_alive": "30m",
        "options": {"temperature": 0, "stop": ["[eod]"],
                    "num_predict": min(1536, len(p.ns) * 4 + 64)},
    }).encode()
    req = urllib.request.Request(OLLAMA, data=body, headers={"Content-Type": "application/json"})
    buf = ""
    with urllib.request.urlopen(req, timeout=120) as r:
        for raw in r:
            chunk = json.loads(raw)
            buf += chunk.get("response", "")
            done = chunk.get("done")
            toks = buf.split(" ")
            buf = "" if done else toks.pop()     # the last token may still be growing
            for t in toks:
                t = t.strip()
                if not t:
                    continue
                if t.startswith(PO.speaker_prefix) and t.endswith(PO.speaker_suffix):
                    p.cur = t[len(PO.speaker_prefix):-len(PO.speaker_suffix)] or p.cur
                else:
                    p.word(dl.normalize_text(t) or t)
            if done:
                break
    p.finish()
    STATE["passes"] += 1
    STATE["pass_ms"] = int((time.perf_counter() - p.t0) * 1000)
    with LOCK:
        del WORDS[:-KEEP]
    return True


def _work():
    try:
        while True:
            before = STATE["words"]
            run_pass()
            if STATE["words"] == before:         # nothing landed during the pass: wait for a phrase
                break
    except Exception as e:                       # noqa: BLE001 -- shown on /status, never healed
        STATE["last"] = "pass: %s: %s" % (e.__class__.__name__, e)
    finally:
        _busy.release()


def kick():
    if _busy.acquire(blocking=False):
        threading.Thread(target=_work, daemon=True).start()


def read_feed():
    with urllib.request.urlopen(FEED, timeout=None) as r:
        STATE["feed"] = "live"
        for raw in r:
            line = raw.decode("utf-8", "replace").strip()
            if not line.startswith("data:"):
                continue
            try:
                d = json.loads(line[5:])
            except ValueError:
                continue
            if d.get("kind") != "phrase":
                continue
            toks = (d.get("text") or "").split()
            if not toks:
                continue
            with LOCK:
                for t in toks:
                    WORDS.append({"w": t, "n": dl.normalize_text(t) or t, "spk": None})
                STATE["words"] += len(toks)
            kick()


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_GET(self):
        if self.path.startswith("/stream"):
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            q, bell = deque(_backlog), threading.Event()
            sub = (q, bell)
            _subs.append(sub)
            try:
                while True:
                    wrote = False
                    while q:
                        self.wfile.write(("data: " + json.dumps(q.popleft()) + "\n\n").encode())
                        wrote = True
                    if not wrote:
                        self.wfile.write(b": ping\n\n")
                    self.wfile.flush()
                    bell.wait(15.0)
                    bell.clear()
            except OSError:
                pass
            finally:
                if sub in _subs:
                    _subs.remove(sub)
            return
        b = json.dumps(STATE).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)


def main():
    srv = ThreadingHTTPServer(("127.0.0.1", PORT), H)
    srv.daemon_threads = True
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    try:
        read_feed()
    except Exception:                            # noqa: BLE001
        pass
    # THE FEED IS GONE: stop. The page shows the stream closed; nothing here reconnects.


if __name__ == "__main__":
    main()
