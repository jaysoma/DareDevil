# Brief 18 on AMI: who said what, and to whom (2026-10-23/24)

Jay's FisherDiarization pipeline (text only, `stage3.py`) is run over AMI meetings in batch. Words are scored against
facing for the addressee.

**What ran and what didn't:**
- **Steps 1 and 3 ran in full.**
- **Step 2 ran with the Fisher model** (DiarizationLM-8b-Fisher-v2, Jay's `q4_k_m.gguf`, llama.cpp on CPU) on 10 of
  AMI's test meetings, the first 600 s of each, over three transcripts: full, recog and Whisper's. Two labelled
  stand-ins (oracle and echo) ran on the same words, and on all 171 meetings, as the pipeline's ceiling and floor.
- **The Whisper condition ran** (faster-whisper base.en on the far-field mixdown, the same 10 meetings).
- **The diart-first path didn't run** (see Blocked).

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
   - **The Fisher model bears it out** (10 meetings, first 600 s, medians). It gets 85.1% of each window right on
     recognizer-style words (80.7% full, 88.3% Whisper's), between echo's ~51% and the oracle's ~98%. But the
     whole meeting is 52.2% (45.5%, 53.5%), under giving every word to the most talkative speaker
     (58.4%, 55.0%, 56.6%). It beats that baseline in 7 of 30 runs.
   - **On this CPU it can't keep stage3's pace:** 18.6-22.3 s per pass of about 40 words with 4 threads
     (medians), against the 10 s the live loop allows. On the real clock, the passes fall 14-18 minutes behind over
     10 minutes of meeting.
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

**The third condition, Whisper** (`whisper_words.py`):
- **What ran:** faster-whisper base.en (int8, CPU, word timestamps) on the far-field mixdown of the 10 step 2 meetings,
  first 600 s.
- **The audio:** rebuilt from the Hugging Face `edinburghcstr/ami` sdm parquets (`sdm_rebuild.py`), since AMI's own
  audio host refused intermittently.
- **Speakers:** each recognized word takes the AMI speaker whose manual words overlap it most in time.
- **What it found:**
  - **Coverage:** Whisper gives 81% as many words as AMI's manual transcript (65-86%). Only 34 of 11,194 words have no
    AMI word within 1 s.
  - **One speaker at a time:** the next word is the same speaker's 96.8% of the time (median), as with "recog". The
    recognizer drops what's spoken over.
  - **Speed:** 48-88 s per 600 s of audio on 2 CPU threads.

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
- **Per window, the Fisher model lands between echo and oracle,** as expected (see the subsection below). The window
  split is what it can improve.
- **Whole meeting, it is capped by `pick()`** at two speakers.
- **Short replies and overlapped words** score low even for the oracle (about 30% and 40%, whole meeting). They're the
  words most often folded into the wrong one of the two labels.

### The Fisher model

`run_fisher.sh` runs `run_text.py --model fisher` with Jay's model.
- **The model:** DiarizationLM-8b-Fisher-v2 `q4_k_m.gguf` in llama-cpp-python 0.3.36, n_ctx 4096, 4 CPU threads, one
  run at a time. Two at once outgrew the session's 14.3 GB of memory.
- **The data:** 10 test-set meetings (ES2004a-c, IS1009a-c, TS3003a-b, EN2002a-b), the first 600 s of each, three
  transcripts.
- **The clock:** each pass is counted as 10 s, as on hardware that answers in 10 s. That gives the model the windows
  stage3 would see live, whatever this CPU's speed.
- **The stand-ins** ran on the same words, so the three are directly comparable. The 600 s cut also changes the
  stand-ins' numbers from the 171-meeting table above: in a meeting's first 10 minutes, two people often do most of the
  talking.
- **Failures:** no run failed outright, that is, more than a quarter of passes untagged or below echo per window.
  `fisher_summary.json` has every run.

| medians, 10 meetings | Fisher: per window | whole meeting | oracle: per window, whole | echo: per window, whole | baseline | speakers out / present | s per pass | words per pass |
|---|---|---|---|---|---|---|---|---|
| recog | **85.1%** | **52.2%** | 98.4%, 79.6% | 51.2%, 44.9% | 58.4% | 2 / 4 | 18.6 | 38.5 |
| full | **80.7%** | **45.5%** | 96.6%, 62.6% | 51.6%, 42.1% | 55.0% | 2 / 4 | 22.3 | 40.2 |
| whisper | **88.3%** | **53.5%** | 97.9%, 78.5% | 51.4%, 44.5% | 56.6% | 2 / 4 | 17.6 | 36.5 |

- **Per window, the model does most of what the oracle does:** 81-88% against 97-98%, from echo's 51%. It is best on
  Whisper's words and worst on the full transcript, whose overlaps and backchannels put three or more speakers into
  more windows.
- **Whole meeting, it doesn't beat the simplest baseline.** Its median sits 3-10 points under "all to the most
  talkative", and it wins in 7 of 30 runs.
  - **The cap still binds:** the model, like the oracle, never names more than two speakers. Where two people dominate
    the 10 minutes (IS1009b-c, TS3003a-b), the oracle reaches 95-100% whole-meeting and the model 51-84%.
- **Speed on this CPU:** 15-38 s per pass (median 18-22 s) for about 40 new words, so roughly 2x slower than the 10 s
  pass. EN2002a-b (four fast talkers, longer windows) are the slowest.
- **The real clock** (passes take what they really take): ES2004a, 2 threads while a second run shared the CPU.
  - **Speed:** 103-110 s per pass.
  - **Windows:** they grew to 83-89 new words each.
  - **Lag:** the loop ended 14-18 minutes behind a 10-minute meeting.
  - **Scores:** per window 77.3% (recog) and 70.9% (full), whole meeting 40.7% and 48.7%. That is close to the 10 s clock's 81.5/75.0% and 43.0/34.4%.
  - **What it means:** live use needs the model on faster hardware, not just a longer window.

Every run:

| meeting | transcript | words | Fisher: per window | whole meeting | oracle: per window, whole | echo: per window, whole | baseline (most talkative) | s per pass |
|---|---|---|---|---|---|---|---|---|
| EN2002a | full | 2143 | 62.9% | 35.2% | 87.0%, 41.2% | 49.5%, 34.8% | 46.9% | 37.6 |
| EN2002a | recog | 1716 | 77.3% | 40.5% | 94.1%, 43.1% | 50.3%, 37.2% | 52.2% | 23.4 |
| EN2002a | whisper | 1664 | 70.5% | 36.8% | 88.3%, 41.3% | 49.4%, 35.9% | 49.3% | 21.7 |
| EN2002b | full | 1827 | 64.1% | 35.9% | 86.4%, 42.4% | 50.8%, 32.3% | 37.9% | 32.7 |
| EN2002b | recog | 1316 | 73.8% | 32.9% | 94.6%, 50.5% | 51.1%, 32.9% | 39.6% | 22.1 |
| EN2002b | whisper | 1199 | 69.5% | 33.4% | 90.3%, 40.2% | 49.7%, 31.0% | 38.9% | 20.9 |
| ES2004a | full | 1106 | 75.0% | 34.4% | 90.2%, 47.5% | 52.7%, 34.0% | 40.1% | 22.1 |
| ES2004a | recog | 956 | 81.5% | 43.0% | 94.2%, 47.9% | 51.2%, 34.1% | 40.5% | 18.4 |
| ES2004a | whisper | 721 | 77.5% | 38.7% | 92.0%, 58.5% | 50.8%, 33.6% | 46.6% | 18.0 |
| ES2004b | full | 1254 | 84.6% | 46.0% | 97.9%, 77.8% | 51.8%, 45.0% | 69.7% | 19.7 |
| ES2004b | recog | 1174 | 88.0% | 74.6% | 98.6%, 78.7% | 51.4%, 47.0% | 73.9% | 20.1 |
| ES2004b | whisper | 1037 | 91.2% | 62.1% | 99.8%, 78.8% | 51.6%, 47.3% | 73.7% | 15.1 |
| ES2004c | full | 1353 | 76.9% | 37.8% | 95.3%, 46.6% | 51.5%, 33.0% | 34.3% | 22.6 |
| ES2004c | recog | 1239 | 82.2% | 34.9% | 98.2%, 62.4% | 50.4%, 33.1% | 34.9% | 20.3 |
| ES2004c | whisper | 1065 | 88.5% | 44.3% | 96.3%, 61.7% | 51.4%, 33.1% | 35.4% | 15.0 |
| IS1009a | full | 1325 | 70.9% | 45.1% | 90.9%, 42.3% | 50.4%, 39.2% | 56.9% | 22.6 |
| IS1009a | recog | 1147 | 79.8% | 45.7% | 95.6%, 80.4% | 52.0%, 42.7% | 63.4% | 17.7 |
| IS1009a | whisper | 1054 | 77.2% | 44.9% | 95.7%, 78.2% | 52.3%, 41.6% | 59.3% | 17.8 |
| IS1009b | full | 1640 | 87.7% | 50.7% | 98.7%, 95.7% | 51.9%, 48.2% | 76.6% | 22.5 |
| IS1009b | recog | 1565 | 89.8% | 61.6% | 99.8%, 98.7% | 51.2%, 49.6% | 79.5% | 18.8 |
| IS1009b | whisper | 1414 | 91.7% | 81.2% | 99.7%, 98.4% | 51.4%, 49.4% | 81.8% | 17.9 |
| IS1009c | full | 1213 | 89.4% | 50.5% | 98.8%, 97.7% | 52.9%, 49.6% | 53.0% | 18.7 |
| IS1009c | recog | 1175 | 90.1% | 67.7% | 100.0%, 99.1% | 51.9%, 49.6% | 53.4% | 18.0 |
| IS1009c | whisper | 1007 | 92.7% | 68.4% | 100.0%, 99.7% | 51.7%, 50.0% | 54.0% | 15.6 |
| TS3003a | full | 1204 | 84.4% | 53.7% | 99.3%, 98.7% | 51.8%, 49.5% | 95.5% | 20.1 |
| TS3003a | recog | 1165 | 90.5% | 59.3% | 100.0%, 99.9% | 51.4%, 50.0% | 98.7% | 17.5 |
| TS3003a | whisper | 1009 | 88.2% | 73.2% | 100.0%, 99.5% | 52.0%, 49.9% | 98.0% | 17.1 |
| TS3003b | full | 1208 | 90.2% | 57.7% | 99.0%, 94.5% | 51.5%, 47.6% | 67.0% | 17.6 |
| TS3003b | recog | 1190 | 90.2% | 58.7% | 99.1%, 94.5% | 51.2%, 47.6% | 67.6% | 17.5 |
| TS3003b | whisper | 990 | 90.3% | 83.8% | 99.6%, 95.5% | 51.4%, 47.8% | 72.3% | 17.5 |

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
- **The diart-first path** (`bench_dlm.py`) didn't run. diart's segmentation model, `pyannote/segmentation-3.0`, is
  gated on Hugging Face and needs an access token, which this session doesn't have. With a token in the environment's
  secrets, the rest is reachable: AMI's audio (rebuilt here from the sdm parquets) and diart's embedding model.
- **The 600 s cut:** step 2's model runs cover the first 10 minutes of 10 meetings. Each 10-minute run took 15-38
  minutes of CPU here, so whole meetings, or more of them, need a GPU or a long unattended run.

## Files
- **`results/linguistic/ami/`:**
  - `report.md`;
  - `transcripts_summary.json`: per meeting, both transcripts;
  - `standins.json`: per meeting, both transcripts, oracle and echo;
  - `addressee.json`: every number in section 3, by meeting;
  - `fisher_summary.json`: step 2 with the Fisher model, every run, the medians, the real-clock runs.
- **`harness/linguistic/`:**
  - `ami_parse.py`: AMI's manual annotations to one JSON per meeting;
  - `transcripts.py`: the two transcripts, their statistics and the baselines;
  - `run_text.py`: stage3 in batch, with the Fisher model or a stand-in;
  - `run_fisher.sh`: the 10-meeting runs, resumable; `summarize_fisher.py`: their table;
  - `sdm_rebuild.py`: AMI's far-field mixdown from the Hugging Face sdm parquets; `whisper_words.py`: the Whisper
    transcript with AMI's speakers;
  - `addressee.py`: section 3;
  - Jay's files, copied unchanged, listed in its README.
- **Data:** AMI's manual annotations, from https://groups.inf.ed.ac.uk/ami/AMICorpusAnnotations/ami_public_manual_1.6.2.zip
  (23 MB, CC BY 4.0). The far-field audio comes from https://huggingface.co/datasets/edinburghcstr/ami (sdm). Whisper's weights
  are https://huggingface.co/Systran/faster-whisper-base.en, and the model is https://huggingface.co/google/DiarizationLM-8b-Fisher-v2
  (`q4_k_m.gguf`). No audio, weights or transcripts are committed.
