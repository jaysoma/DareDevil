# Brief 18 harness: Jay's FisherDiarization pipeline, copied for the AMI run

Copied unchanged from the private repo `jaysoma/FisherDiarization` at commit 72d056e (2026-10-23), as brief 18 asks
("change nothing there; copy what you need"):

| file | role in brief 18 |
|---|---|
| `blends.py` | the two-speakers-at-a-time window: walk back from the newest word until a third speaker would enter, at most 50 words |
| `stage3.py` | text only: new words enter with alternating tags, settled words keep theirs, a window's labels pinned by majority |
| `bench_dlm.py` | diart first, then the Fisher model corrects; per-window, permutation-free scoring |
| `dlm_align.py` | DiarizationLM's prompt and alignment utilities, vendored by Jay |
| `Modelfile.fisher` | the Ollama Modelfile: raw template, temperature 0, stop at `[eod]`, num_ctx 4096 |

None of these files has a hard-coded `C:\` path. The ones that do (`ami_stats.py`, `bench.py`, `onnx_models.py`,
`probe.py`, `whosaid.py`) belong to the pitch and diart-model paths, which brief 18 leaves out.

`blends.py` and `stage3.py` are live services: they read words from local HTTP feeds and post results back.
`run_text.py` (below) drives `stage3.py`'s logic in batch over a meeting's words instead.

## Added for the AMI run (this repo's own)
- **`ami_parse.py`:** AMI's manual annotations to one JSON per meeting: words, segments, dialogue acts with addressee,
  adjacency pairs and focus of attention.
- **`transcripts.py`:** AMI's full transcript and a recogniser-style one (overlaps resolved), with their statistics and
  the baselines.
- **`run_text.py`:** `stage3.py`'s logic in batch over a meeting. It runs the Fisher model through llama.cpp, or a
  labelled stand-in (oracle or echo).
- **`addressee.py`:** step 3, addressee from the words, from focus of attention, and from both.

Results so far: `results/linguistic/ami/report.md`.

## Status (2026-10-23, first session): blocked before any run
- **The model:** DiarizationLM-8b-Fisher-v2 is on `huggingface.co` only, and the environment's network policy denies
  that host (HTTP 403 at the proxy), with its file CDNs `cdn-lfs.huggingface.co` and `cas-bridge.xethub.hf.co`. Ollama's
  registry (`registry.ollama.ai`, `ollama.com`) is denied too.
- **The data:** the AMI corpus host `groups.inf.ed.ac.uk` and the Hugging Face copy (`edinburghcstr/ami`, on
  `huggingface.co`) are both denied.

The brief says to report and stop in both cases, so nothing was run and no scores exist.

**To unblock,** add these under the environment's Network access, Allowed domains (keep Allow package managers ticked):
- `huggingface.co`, `cdn-lfs.huggingface.co`, `cas-bridge.xethub.hf.co`;
- `groups.inf.ed.ac.uk`.

**Two things to know before the run:**
- **Disk:** a Q4_K_M GGUF is about 4.9 GB (the repo's README). If none is published, it has to be made from the full
  weights, about 16 GB more on disk.
- **Access:** if the model page asks for licence acceptance (it's a Llama 3 finetune), a Hugging Face token is needed
  in the environment as well. That couldn't be checked from here.
