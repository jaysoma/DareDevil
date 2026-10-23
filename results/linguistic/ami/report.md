# Brief 18 on AMI: who said what, and to whom (2026-10-23, partial: the Fisher model is not yet reachable)

Jay's FisherDiarization pipeline (text only, `stage3.py`) is run over AMI meetings in batch. Words are scored against
facing for the addressee.

**What ran and what didn't:**
- **Steps 1 and 3 ran in full.**
- **Step 2 ran only with two clearly labelled stand-ins for the model,** which measure the pipeline's own ceiling and
  floor. The model itself is not yet downloadable, and nothing here is presented as its result.
- **The diart-first path and the Whisper condition didn't run** (see Blocked).

## What it says
1. **A recogniser's words are mostly one speaker at a time, as Jay said.** In AMI's manual transcript, 81.5% of words
   are followed by the same speaker's (median over 171 meetings). Resolve the overlaps as a recogniser would and it's
   95.8%. But a 50-word window still holds a third speaker for a third of words (32.6%), so "rarely more than two" is
   optimistic at blends.py's length.
2. **The text-only path can't name more than two people.** This holds on every one of AMI's 171 meetings, whatever the
   model does.
   - **Why:** `stage3.py`'s `pick()` gives a window label with no settled words behind it to the window's other known
     speaker, else to whoever spoke most recently before the window. Only if nobody did is it somebody new. Once two
     speakers exist, a third is always folded into one of them.
   - **The effect:** a perfect two-speaker labeller (the oracle stand-in) gets 99.5% of each window right, but only
     44.6% of the whole meeting. That's against 40.3% for giving every word to the most talkative speaker
     (recogniser-style words, medians).
   - **What it means:** so the text-only path's whole-meeting score is capped near the baseline before the Fisher
     model is even asked. Fixing that needs a different rule for opening a new speaker, not a better model.
3. **Facing adds to the words when one person is addressed, and not otherwise** (14 meetings, 5,963 addressed acts).
   - **Which person:** words and facing together pick the right one 55.8% of the time, against 45.9% for words alone
     (+9.9 points, 95% interval 6.5 to 13.0, better in 13 of 14 meetings).
   - **Group or one person:** facing doesn't help tell them apart (+1.3, -0.1 to 2.7).
   - **Overall:** words and facing get 64.4% against 60.2% for words alone; always saying "the group" gets 57.9%.

## 1. The words two ways
`transcripts.py`. "Full" is AMI's manual transcript, every word in time order. "Recog" is overlaps resolved as a
recogniser would: a word overlapping another speaker's is kept only if its own speech segment is the longest of those
involved. "Longer" stands in for "louder", since the manual annotations carry no levels. It drops 11.6% of words (the
median).

| median over 171 meetings (range) | full | recog |
|---|---|---|
| words overlapping another speaker's | 24.9% (6.9-50.3) | 14.6% (3.6-32.6) |
| short replies ("yeah", "mm-hmm") | 4.6% | 0.5% |
| the next word is the same speaker's | 81.5% (61.2-93.7) | **95.8%** (89.0-98.4) |
| 50-word windows holding a third speaker | 61.7% | 32.6% |
| baseline: all to the most talkative, whole meeting | 38.8% (26.7-79.4) | 40.3% |
| baseline: all to each two-speaker window's majority | 81.7% | 84.4% |

Short replies nearly vanish from the recogniser's view, because most backchannels are spoken over someone. Every
meeting is in `transcripts_summary.json`.

**The third condition** (Whisper on the far-field mixdown) didn't run. AMI's audio downloads, but Whisper's weights
don't (see Blocked).

## 2. Who said what: the text-only path
`run_text.py` drives `stage3.py`'s own logic in batch: its windows, its alternating prior, its placement of the
completion's words, and its majority pinning onto the running speakers. Phrases end at a 0.5 s pause or 20 words, and
there's one pass per phrase, as stage3 does live. Two stand-ins replace the model until it can be fetched. Neither is a
model result:
- **Oracle:** a perfect two-speaker labeller (tags the window's true speakers, at most two tags).
- **Echo:** returns its input unchanged (no information).

All 171 meetings, medians:

| | per window | whole meeting | baseline (most talkative) | speakers out / present | splits | merges |
|---|---|---|---|---|---|---|
| oracle, recog | 99.5% | 44.6% | 40.3% | 2 / 4 | 3 | 2 |
| oracle, full | 96.1% | 42.4% | 38.8% | 2 / 4 | 4 | 2 |
| echo, recog | 58.3% | 33.6% | 40.3% | 2 / 4 | 4 | 2 |
| echo, full | 59.3% | 32.8% | 38.8% | 2 / 4 | 4 | 2 |

- **Never more than two speakers:** in all 342 oracle runs (171 meetings, two transcripts) the output has exactly two.
  That covers 4-person, 3-person and 5-person meetings alike. Echo's runs have a median of two as well. Every meeting is in `standins.json`.
- **Per window, the Fisher model's real result will land between echo (58%) and oracle (99.5%).** The window split is
  what it can improve.
- **Whole meeting, it will be capped near 45%,** because of `pick()`.
- **Short replies and overlapped words** score low even for the oracle (about 30% and 40%, whole meeting). They're the
  words most often folded into the wrong one of the two labels.

## 3. To whom: words against facing
`addressee.py`, on the 14 meetings with both addressee and focus-of-attention labels (ES2008a, IS1000a, IS1001a-c,
IS1003b and d, IS1006b and d, IS1008a-d, TS3005a; all four-person).
- **Acts scored:** 5,963 have an annotated addressee: 3,454 to the group and 2,509 to one person. Another 2,980 acts
  carry no addressee label and aren't scored.
- **Clues:**
  - Words: a question mark, "you", "we", length, a short reply, and per candidate whether they spoke the previous turn
    or take the next one.
  - Facing: the share of the act the speaker looks at each person, the table, the slides or the whiteboard.
- **No names:** no name feature is used. AMI's participants are rarely addressed by name, and the transcript doesn't
  say which name is whose.

| predictor | overall | group, recalled | one person, exact | macro | group or one | which person, given one |
|---|---|---|---|---|---|---|
| chance: always the group | 57.9% | 100% | 0% | 50.0% | 57.9% | |
| chance: uniform among the other three | | | | | | 33.3% |
| chance: the previous speaker | | | | | | 66.2% |
| rule: words (a question to the next speaker, a reply to the previous, else the group) | 62.4% | 87.8% | 27.5% | 57.6% | 66.4% | |
| rule: facing (whoever is looked at most of the act, else the group) | 57.6% | 67.9% | 43.3% | 55.6% | 60.1% | |
| rule: both (facing's person if any, else words) | 59.2% | 60.0% | 58.2% | 59.1% | 63.8% | |
| learned: words | 60.2% | 70.6% | 45.9% | 58.2% | 68.8% | 69.2% |
| learned: facing | 56.7% | 67.8% | 41.5% | 54.6% | 59.6% | 72.9% |
| learned: both | **64.4%** | 70.6% | **55.8%** | **63.2%** | 70.1% | **78.9%** |

Learned is logistic regression, leaving one meeting out each time (14 folds). Macro is the mean of group recall and
one-person exact.

**Does facing add once the words are known?** Both against words alone, learned, resampling meetings (2,000 draws):

| | gain | 95% interval | meetings where both wins |
|---|---|---|---|
| overall | +4.2 | 2.1 to 6.0 | 11 of 14 |
| macro | +5.0 | 2.8 to 6.9 | 13 of 14 |
| one person, exact | +9.9 | 6.5 to 13.0 | 13 of 14 |
| which person, given one | +9.7 | 5.5 to 12.9 | 12 of 14 |
| group or one | +1.3 | -0.1 to 2.7 | 9 of 14 |

- **Facing helps answer "which person", not "the group or one person".** The speaker's eyes point at the person they
  answer.
- **Facing doesn't help say whether the act is for everyone.** People look at the slides or the table when talking to
  the group, and also when talking to one person.
- **The words are strongest on turn-taking:** a one-person act goes to the previous speaker 66% of the time.

**Meetings that go against the trend:**
- **TS3005a:** the one meeting where adding facing hurts (overall 52.4% for words, 47.6% for both).
- **IS1003d and IS1006d:** the weakest overall (51% and 50% with words alone).

Every meeting is in `addressee.json` under `learned.<predictor>.by_meeting`.

## Blocked, and what's left
- **The Fisher model.** DiarizationLM-8b-Fisher-v2 is public and not gated, and its repo carries a `q4_k_m.gguf` (the
  file Jay runs). But every file download from Hugging Face redirects to `us.aws.cdn.hf.co`, which the network policy
  denies; `cdn-lfs.huggingface.co` is denied too. llama.cpp (llama-cpp-python 0.3.36) is built and the driver is ready:
  `run_text.py --model fisher --gguf <path>`.
  - **Still to run:** the text-only path on 10 or more meetings, both transcripts, with seconds per pass.
- **The diart-first path** (`bench_dlm.py`). It needs diart's segmentation and embedding models, which come from the
  same Hugging Face CDN, plus AMI's audio, which is reachable.
- **Whisper on the far-field mixdown.** Its weights are on `openaipublic.azureedge.net` (denied) or the Hugging Face
  CDN.

**To unblock all three,** allow `us.aws.cdn.hf.co`, `cdn-lfs.huggingface.co` and `openaipublic.azureedge.net`.

## Files
- **`results/linguistic/ami/`:**
  - `report.md`;
  - `transcripts_summary.json`: per meeting, both transcripts;
  - `standins.json`: per meeting, both transcripts, oracle and echo;
  - `addressee.json`: every number in section 3, by meeting.
- **`harness/linguistic/`:**
  - `ami_parse.py`: AMI's manual annotations to one JSON per meeting;
  - `transcripts.py`: the two transcripts, their statistics and the baselines;
  - `run_text.py`: stage3 in batch, with the Fisher model or a stand-in;
  - `addressee.py`: section 3;
  - Jay's files, copied unchanged, listed in its README.
- **Data:** AMI's manual annotations, from https://groups.inf.ed.ac.uk/ami/AMICorpusAnnotations/ami_public_manual_1.6.2.zip
  (23 MB, CC BY 4.0). No audio, weights or transcripts are committed.
