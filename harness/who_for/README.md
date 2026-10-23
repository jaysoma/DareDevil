# Brief 22: who it's for, real requests to people in their own context

Text only. This builds on brief 19 (`harness/device_directed/`): its set, models, methods and thresholds are reused
unchanged. Findings: `results/who_for/report.md`.

## Run
    harness/who_for/fetch_sources.sh SOURCES     # brief 19's sources plus NLTK's names list
    harness/who_for/run_all.sh SOURCES WORK results/who_for

This takes about 25 minutes on 4 cores. `fetch_sources.sh` makes one request at a time with a pause between them.

## Pieces
| script | does |
|---|---|
| `build_requests.py` | Finds Switchboard's real requests to the other caller: action-directives, request-questions and commitments, from the DAMSL tags. Builds windows with each one in place (its own call, its utterance split so it's a phrase of its own) and the same words spliced into another call. Also every SLURP car test command spliced into a call (step 3). |
| `cues.py` | The five who-it's-for cues: vocative, "you", first-person narration, past or reported speech, and bare imperative. They are fixed rules, set before any scoring. |
| `score_who.py` | Brief 19's methods, through its own `methods.py`, on brief 22's windows. It first recomputes brief 19's scores on brief 19's own set and stops unless they match. |
| `evaluate_who.py` | Steps 1-3 at brief 19's per-device thresholds, the cue vetoes, the cross-fitted logistic combination, the full curves, and the catalogue. |
| `report_tables.py` | `tables.md` and `curves.png`. |

## What's committed and what isn't
No Switchboard, SLURP or AMI text. The committed files are:
- **`requests_index.jsonl`:** each request's call, act index, tag, kind and position;
- **`scores_requests.jsonl.gz`:** numbers and cue flags;
- **`accepted_requests.jsonl`:** ids, cues and scores.

`build_requests.py`, rerun on the fetched sources, rebuilds the identical windows (seed 22).

## Network
The run needs PyPI, `raw.githubusercontent.com`, `zenodo.org` and `huggingface.co`. AMI's annotation host,
`groups.inf.ed.ac.uk`, was refused by this environment's network policy (HTTP 403 at the proxy's CONNECT). So AMI's
dialogue acts, the second source step 1 names, couldn't be used; see the report.
