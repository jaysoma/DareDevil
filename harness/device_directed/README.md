# Brief 19: device-directed words in a stream

This harness builds a test set with known answers, scores every phrase with each method, and measures hits against
false accepts per hour. Text only. Findings: `results/device_directed/report.md`.

## Run
    harness/device_directed/fetch_sources.sh SOURCES     # the sources, models and pip packages
    harness/device_directed/run_all.sh SOURCES WORK results/device_directed

The two general models take about 3.5 hours on 4 CPU cores; everything else takes about 10 minutes.

## Network
Besides PyPI, the run needs `raw.githubusercontent.com` (SLURP, SWDA, NLTK data), `zenodo.org` (AMI) and two Hugging
Face hosts for the models: `huggingface.co` and `us.aws.cdn.hf.co`, the CDN that file downloads are redirected to. No
token is needed. Hugging Face's other hosts, AMI's own site, Project Gutenberg, Wikisource and TalkBank are blocked from
this environment.

## Pieces
| script | does |
|---|---|
| `build_set.py` | Builds the set: 1,000 windows of 30 stream phrases, each with one phrase spliced in. The sources, the device grouping and the hard negatives are documented in its docstring. |
| `methods.py` | Every method: keyword spotting, shape and contrast with n-gram models and with MiniLM, and the general model asked directly. |
| `score.py` | Scores every phrase of every window with each method, after putting all text in a recogniser's form (lowercase words, no punctuation). Records model size and time per phrase. |
| `evaluate.py` | Builds the curves of hits against false accepts per hour, the operating points at 1 and 10 per hour, the hard negatives, the failing conditions and the false-accept catalogue. |
| `report_tables.py` | Writes `tables.md`, `curves.png` and `set_index.jsonl`, the set's recipe with no third-party text. |

## What's committed and what isn't
The results hold only the recipe: each window's source, block, splice position and SLURP id, plus the hard negatives
generated here. The scores are numbers only. No transcript text is committed: Switchboard's licence doesn't allow
redistributing it, and SLURP and AMI are left out too for simplicity, even though their CC BY licences would allow it.
`build_set.py`, rerun on the fetched sources, rebuilds the identical set (seed 19). The false-accept catalogue quotes
short phrases for analysis.
