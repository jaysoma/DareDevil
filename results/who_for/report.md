# Who it's for: real requests to people, in their own context (2026-10-23)

Brief 22, text only. It builds on brief 19 (`results/device_directed/report.md`) and reuses its set, models, methods and
per-device thresholds unchanged. The rebuild reproduces brief 19's scores exactly: the same numbers on all 1,000 windows
for every method, and `score_who.py` re-checks this before it scores anything new.

**Short answer:**
- **Brief 19's hardest number was mostly an artefact.** Its generated to-person phrases were accepted 96% of the time
  at 10 false accepts per hour, because they were (a) made from device commands and (b) spliced in from outside.
  - **Real requests to a person, where they were said** (Switchboard, 620 of them): MiniLM contrast accepts 4.4% at
    10 per hour and 0.2% at 1 per hour.
  - **Of that drop, context explains a lot.** The same words spliced into another call are accepted 19.6% of the time.
    Among real requests that do have a device's shape, it's 43% in place against 97% spliced.
  - **The rest is that real requests rarely sound like device commands at all.**
- **Contrast does what Jay said it would.** The same words score lower in their own conversation than spliced into
  another, for 86% of request-and-device pairs (MiniLM). Shape alone can't tell them apart, by construction.
- **The cues add little on real speech.** As vetoes:
  - **"You":** costs 6 points of hits for 1.6 points fewer real requests accepted.
  - **First-person narration:** cuts the generated to-person phrases by 20 points, but barely touches real requests,
    which rarely use it.
  - **The learned combination:** moves every number by 3 points or less.
  - **Why so little:** on real speech the hard cases are rare, and the cues fire on device commands too ("can you
    ..." is a common command).
- **Jay's speakerphone case, on real calls:** car instructions spliced into Switchboard calls score above real requests
  in other calls 99.9% of the time (MiniLM contrast). At brief 19's car threshold for 1 false accept per hour it finds
  97% of the instructions and accepts 0.5% of the real requests.
  - **The cases that pass** are mostly talk about operating a gadget and asking the other caller to hold on: the
    genuine ambiguity, now measured.
- **Not run:**
  - **AMI's requests:** AMI's annotation host is refused by this environment's network policy, and no mirror exists on
    Zenodo or Hugging Face.
  - **Step 4 (a small general model):** brief 19's general-model follow-up hasn't landed. There are no model scores on
    `main`.

## The set
- **Real requests to a person (step 1)** come from the Switchboard Dialog Act Corpus (`github.com/cgpotts/swda`), the
  telephone calls brief 19 streamed. A dialogue act is a tagged sub-utterance plus the same caller's continuations. Acts
  of at least 3 words, spoken by one caller to the other:

  | kind | DAMSL tag | n | median words |
  |---|---|---|---|
  | directive | `ad` (action-directive) | 502 | 7 |
  | ask | a yes/no question (`qy`) opening "can/could/would/will you" or "do you want to" | 33 | 8 |
  | commit | `co`, `cc`, `oo` (commit, offer): the "I'll ..." kind brief 19's templates imitated | 85 | 7 |

  For comparison, brief 19's instructions have a median of 7 words, and its generated to-person phrases 11.
- **Two windows per request,** each in brief 19's form (31 phrases, the target 5-25 phrases from either edge):
  - **in place:** its own call around it. Its utterance is split into before, request and after, so the request is a
    phrase of its own and nothing is moved.
  - **spliced:** the same words inserted into a different call, inside caller A's turn, exactly as brief 19 spliced.

  Every request is scored against all four devices, so a rate below pools 2,480 request-and-device pairs.
- **Step 3:** all 328 SLURP test-split car commands, each spliced into a Switchboard call the same way.
- **Thresholds:** brief 19's committed per-device operating points. That's where a device's false accepts first reach
  1 and 10 per hour across brief 19's streams, at 150 words a minute.
  - **For reference:** at the 10 per hour thresholds, 1.1% of ordinary call phrases pass.

## 1. Real requests, in their own place
Each cell is the % accepted at brief 19's thresholds, pooled over the four devices:

| method | per hour | real, in place | the same words, spliced | brief 19's generated to_person | brief 19's hits |
|---|---|---|---|---|---|
| keyword spotting | 10 | 0.9 | 0.9 | 51.9 | 32.7 |
| shape only, n-gram | 10 | 2.3 | 2.3 | 74.4 | 92.1 |
| contrast, n-gram | 10 | 2.4 | 3.4 | 81.9 | 94.6 |
| shape only, MiniLM | 10 | 3.8 | 3.8 | 88.1 | 89.4 |
| **contrast, MiniLM** | **10** | **4.4** | **19.6** | **95.6** | **98.5** |
| contrast, MiniLM, past only | 10 | 0.6 | 2.7 | 85.6 | 92.3 |
| **contrast, MiniLM** | **1** | **0.2** | **2.3** | **83.1** | **89.2** |

- **Real requests are rarely shaped like device commands.** Shape alone accepts 2-4% of them, against 74-88% of brief
  19's generated phrases. Those were rewrites of device commands ("I'll set an alarm for six"); a real Switchboard
  request is about the conversation's own topic.
- **Context matters as Jay predicted.** For the contrast methods, the same words are accepted more often spliced into
  a stranger's call than in their own: MiniLM 19.6% against 4.4% at 10 per hour.
  - **Paired, request by request:** MiniLM contrast scores lower in place for 86% of the pairs (median -0.072), and
    n-gram contrast for 74%. Shape alone is identical in both places, by construction.
- **The like-for-like test.** Brief 19's phrases were device-shaped, so the fair comparison is real requests that also
  are. These are the 88 requests (93 request-and-device pairs) that pass a device's MiniLM shape threshold at 10 per
  hour:

  | MiniLM contrast accepts | in place | spliced |
  |---|---|---|
  | at 10 per hour | **43%** | 97% |
  | at 1 per hour | **6.5%** | 45% |

  Spliced, they behave exactly like brief 19's generated phrases (97% against its 96%). In place, contrast rejects more
  than half. **So brief 19's hardest number was largely an artefact of splicing, but not wholly: 43% of device-shaped
  real requests still pass at 10 per hour.**
- **By device,** MiniLM contrast at 10 per hour, in place against spliced:
  - car: 5.3% against 28.1%;
  - kitchen: 6.3% against 27.4%;
  - watch: 2.4% against 10.2%;
  - general: 3.4% against 12.6%.
- **By kind,** in place at 10 per hour: directives 4.1%, asks 3.8%, commits 5.9%.

**The live variant (past context only)** accepts 0.6% of real requests in place, but it also loses hits: 92% against
98.5%, as brief 19 found.

## 2. Who-it's-for cues
**How often each fires** (%):

| phrases | n | vocative | you | first person | past/reported | bare imperative |
|---|---|---|---|---|---|---|
| brief 19 instructions | 520 | 0 | 6.3 | 1.2 | 1.9 | 42.5 |
| brief 19 stream phrases | 30,000 | 0.3 | 11.3 | 2.0 | 9.7 | 1.3 |
| brief 19 to_person (generated) | 160 | 10.6 | 13.8 | 20.0 | 18.1 | 0 |
| brief 19 subject (generated) | 160 | 7.5 | 16.2 | 3.1 | 20.0 | 3.8 |
| real directives | 502 | 0 | 50.2 | 3.6 | 3.2 | 13.5 |
| real asks | 33 | 0 | 100 | 0 | 9.1 | 0 |
| real commits | 85 | 0 | 30.6 | 41.2 | 1.2 | 17.6 |
| car commands (step 3) | 328 | 0 | 8.5 | 2.4 | 0.6 | 50.0 |

- **Real requests to a person almost never open with a name.** Not one of 620 does: phone callers know who they're
  talking to. "You" is the common marker (50% of directives); commits carry first-person narration (41%).
- **The generated phrases' cues are their templates.** On brief 19's set, each cue's effect is partly circular; the
  real requests are the honest test.
- **Device commands are often bare imperatives** (43-50%), and 6-9% say "you" ("can you ...").

**Each cue as a veto on MiniLM contrast.** A phrase the cue fires on is rejected, and the threshold is re-chosen so
the streams' false accepts stay at the target. The "none" row is recomputed by the same routine, so the rows compare
directly. It differs slightly from brief 19's own numbers, since the threshold sits just above the last allowed false
accept.

| veto | per hour | hits | to_person (gen.) | subject (gen.) | foreign (real) | real requests |
|---|---|---|---|---|---|---|
| none | 1 | 91.9 | 85.0 | 78.8 | 1.9 | 0.3 |
| none | 10 | 98.3 | 98.1 | 95.0 | 20.0 | 4.4 |
| vocative | 10 | 98.3 | 87.5 | 87.5 | 18.8 | 4.4 |
| you | 10 | 92.7 | 84.4 | 81.2 | 15.6 | 2.8 |
| first person | 10 | 97.1 | 78.1 | 91.9 | 19.4 | 4.2 |
| past/reported | 10 | 96.9 | 81.2 | 76.9 | 14.4 | 4.6 |
| first person + past | 10 | 95.8 | 61.3 | 74.4 | 15.0 | 4.4 |
| all four | 1 | 84.4 | 44.4 | 50.0 | 0.0 | 0.1 |
| all four | 10 | 90.6 | 48.1 | 56.9 | 9.4 | 3.1 |

- **On brief 19's generated phrases, the cues look strong.** All four halve to-person acceptance (98% -> 48%). That's
  the circularity: they are the templates.
- **On real requests they barely move anything** (4.4% -> 3.1% with all four). Real requests that pass contrast mostly
  have no person cue, or only "you", which commands share.
- **The price is hits:** -7.7 points for all four. "You" alone costs 5.6, because commands ask "can you ...".

**A small learned combination.** Logistic regression on MiniLM contrast (standardised per device) and the cues:
- **Cross-fitted in two folds:** brief 19's windows split by window, real requests by call.
- **Training:** brief 19's instructions as positives, its stream phrases and the real requests as negatives. It never
  trains on brief 19's generated phrases, which are only scored.

| features | per hour | hits | to_person (gen.) | subject (gen.) | real requests |
|---|---|---|---|---|---|
| contrast only | 1 | 92.3 | 85.6 | 78.8 | 0.3 |
| all cues | 1 | 91.9 | 83.1 | 76.9 | 0.2 |
| contrast only | 10 | 98.5 | 98.1 | 96.2 | 4.3 |
| + you | 10 | 98.7 | 96.2 | 96.2 | 3.2 |
| + bare imperative | 10 | 98.8 | 98.1 | 96.2 | 5.2 |
| all cues | 10 | 98.8 | 95.6 | 93.1 | 3.8 |

- **The coefficients take the expected signs.** Fold 0: vocative -2.1, you -2.0, first person -1.3, bare imperative
  +0.3, past/reported +0.1.
- **Every rate moves by 3 points or less.** Among phrases whose contrast is high enough to matter, the cues are rare,
  and they fire on commands too.
- **What each cue adds, alone, on real requests** (one cue added to contrast, at 10 per hour):

  | cue added | real requests accepted |
  |---|---|
  | none (contrast only) | 4.3% |
  | + "you" | 3.2% |
  | + first person | 4.2% |
  | + past or reported | 4.1% |
  | + vocative | 4.3% |
  | + bare imperative | 5.2% (it marks commands, so it lets more through) |

## 3. Jay's speakerphone case, on real calls
All 328 SLURP car commands, each spliced into one side of a Switchboard call, against the 620 real requests in other
calls, scored by the car detector:

| method | car commands found at 1/h | real requests accepted at 1/h | calls' FA/h at that threshold | found at 10/h | real requests at 10/h | P(command above request) |
|---|---|---|---|---|---|---|
| keyword spotting | 12.2% | 0.0% | 0.35 | 32.0% | 0.0% | 0.831 |
| shape only, n-gram | 85.4% | 0.3% | 0.49 | 96.0% | 1.6% | 0.994 |
| contrast, n-gram | 93.3% | 0.5% | 0.91 | 97.3% | 2.7% | 0.996 |
| shape only, MiniLM | 87.2% | 0.0% | 0.21 | 96.6% | 3.9% | 0.989 |
| **contrast, MiniLM** | **97.0%** | **0.5%** | **0.56** | **99.4%** | **5.3%** | **0.999** |
| contrast, MiniLM, past only | 86.0% | 0.0% | 0.21 | 96.0% | 0.6% | 0.999 |
| learned combination, all cues (the calls' own 1 and 10/h) | 97.9% | 1.0% | 1 | 99.4% | 5.3% | 0.999 |

`curves.png` (right) gives the full curve; `tables.md` and `curves_step3.json` hold every point.

- **On real calls the instructions stand apart** from what callers ask of each other: MiniLM contrast ranks a command
  above a request 99.9% of the time.
- **The calls' own false accepts stay close to brief 19's rates** (0.6 and 10.4 per hour at its 1 and 10 per hour
  thresholds), so the thresholds carry over.
- **What this doesn't show:** a real person-directed message with a car command's exact content ("text Sam I missed my
  flight", said to the other caller). Switchboard callers rarely say such things, so the hard case is now shown to be
  rare in real calls, but not solved.

## The real requests that get through, by kind
At 10 per hour, MiniLM contrast accepts 108 request-and-device pairs (79 requests); `accepted_requests.jsonl` has ids
and cues, no text. Read one by one, they fall into a few kinds. Described here, not quoted: Switchboard's licence
doesn't allow redistributing its text.
- **Talk about operating a gadget,** said to the other caller: turning off a stereo, changing the TV channel, pushing a
  button, starting the call's recording. This is Jay's ambiguity, real. The words are a device command; only the
  conversation says they're for the other person.
- **Managing the call:** asking the other caller to hold on a minute, or to go ahead. These are short imperatives that
  look like commands.
- **Advice in a device's domain:** a cooking tip (kitchen), a suggestion about when to exercise or call (watch),
  watching the news tonight (general).
- **Ordinary directives** that happen to sit near a device's shape ("tell me about it").

**The patterns:**
- **Devices:** the kitchen and car detectors account for most (39 and 33 of 108).
- **Cues:** half carry a person cue (49 "you", 9 first person). None carries a vocative.
- **Length:** the median length is 7 words.

## Every condition, and what was set aside
- **Every method, threshold and kind** is in `tables.md`, with the full curves from 0.25 to 60 false accepts per hour.
- **Set aside to study, not failing:**
  - "Ask" has only 33 requests, so its rates are coarse.
  - Keyword spotting accepts almost no real requests (0.9%), but only because it finds a third of the instructions.
- **No condition fails outright** (a method finding under half the instructions at 10 per hour), except keyword
  spotting, as in brief 19.

## Not run, and why
- **AMI's requests (step 1's second source).** AMI's dialogue-act and addressee annotations
  (`ami_public_manual_1.6.2.zip`) are only on `groups.inf.ed.ac.uk`. This environment's network policy refuses that
  host: HTTP 403 at the proxy's CONNECT, a policy denial, not the site limiting traffic.
  - **No mirror:** neither Zenodo's AMI snapshot (transcripts and summaries only) nor Hugging Face has the dialogue
    acts.
  - **To add AMI:** allow `groups.inf.ed.ac.uk` in the environment's network settings, then extend
    `build_requests.py` with AMI's suggestion and request acts (`ami_parse.py` from brief 18 reads them).
- **Step 4, a small general model.** The brief makes it conditional on brief 19's follow-up, which hasn't landed. Brief
  19's report says its Qwen runs were still going, and `main` has no model scores. There's no best size to use, so
  this step waits for that follow-up.

## Caveats
- **Telephone calls only.** Switchboard is two strangers on an assigned topic. Requests in a car, kitchen or
  living room, between people who share the device, would be more device-like more often. This measures how rare the
  hard case is in real conversation; it doesn't solve it.
- **The DAMSL tags decide what counts as a request.** Directives include soft suggestions ("you might try ...").
- **Text, with known phrase boundaries,** as in brief 19. Real devices get recogniser errors and voice-activity
  segmentation.
- **The cue rules are fixed, simple and English-only.** A name list can't tell a vocative from a name in a message
  ("text Sam"); only phrase-initial names count. On brief 19's set the cues are partly circular, because the generated
  phrases were made from the same patterns.

## Files
- **`results/who_for/`:**
  - `report.md`;
  - `tables.md` (every table and curve);
  - `curves.png`;
  - `summary.json` (every number);
  - `curves_step1.json`, `curves_step3.json`;
  - `accepted_requests.jsonl` (the catalogue: ids, cues, scores);
  - `requests_index.jsonl` (the recipe: call, act index, tag, kind, positions);
  - `scores_requests.jsonl.gz` (every score and cue, numbers only).
- **`harness/who_for/`:** the run (README there).
