# Device-directed words in a stream: does the instruction's shape find it? (2026-10-23)

Brief 19, text only. Jay's proposal: every device hears every word and listens only for phrases shaped like its own
instructions, and a phrase that fits the device but not the surrounding talk is meant for the device. This builds a test
set with known answers and measures four kinds of method on it:
- keyword spotting
- the instruction's shape alone
- shape and contrast (Jay's)
- a small general model asked directly

**Short answer:**
- **Shape finds instructions, and contrast makes it better.** Jay's shape-and-contrast with a small sentence-embedding
  model finds 89% of spliced instructions at 1 false accept per hour of other speech, and 98.5% at 10 per hour. Keyword
  spotting finds 9% and 33% at the same rates.
- **It isn't just spotting the odd phrase out.** A real phrase spliced in from another conversation is accepted only
  0-2% of the time (13% for the best model at 10 per hour), so a phrase also needs the device's shape.
- **Shape can't tell who it's meant for.** The same instructions said to a person are accepted almost as often as the
  real ones: 82-96% at 10 per hour, 51-83% at 1 per hour. So are remarks about the device's subject. Jay's speakerphone
  case ("Text Sam, I missed my flight") is the hard case, and on its words alone the methods here don't solve it.
- **A small general model asked directly does far worse.** Qwen2.5-1.5B finds 12% of instructions at 1 false accept
  per hour and 26% at 10. It also accepts commands said to a person as often as real ones. Qwen2.5-0.5B answers by line
  position, not content, and finds almost nothing.

## The set (`harness/device_directed/build_set.py`; labels known by construction)
- **Instructions:** SLURP's spoken commands (CC BY 4.0), grouped by device.
  - **car:** directions, traffic, taxis, tickets, sending email and social posts. SLURP has no phone-call commands.
  - **kitchen:** recipes, cooking, coffee, ordering food. SLURP has almost no oven or timer commands.
  - **watch:** alarms, reminders and calendar, the time.
  - **general:** everything else (weather, music, news, lights, questions).
  - The shape models learn from the training split; only commands from the test split are spliced in.
- **Streams,** each window 30 consecutive phrases:
  - **AMI meetings** (CC BY 4.0), one sentence per phrase.
  - **Switchboard telephone calls** (via SWDA), one utterance per phrase, with the instruction placed inside one
    caller's turn. That's the speakerphone case.
  - **Public-domain songs:** Blake's *Songs of Innocence and of Experience* and the King James Psalms, one line or
    verse per phrase.
  - **Monologue:** long speeches from Hamlet, Macbeth and Julius Caesar. This is a stand-in, because no free corpus of
    real self-talk (muttering, thinking aloud) was reachable. TalkBank, Wikisource and Gutenberg are blocked here.
- **Splicing:** one phrase per window, whole, never interleaved, away from the window's edges.
  - 520 instruction windows: 40 per device for AMI, calls and songs, and 10 per device for the small monologue
    source.
  - 480 hard-negative windows, in AMI and calls, 40 per device of each kind:
    - **to a person** (*generated*): the same imperative test commands rewritten as said to someone ("I'll text Sam
      that ...", "Dave, can you ... for me?", "I was going to ... but I forgot").
    - **subject** (*generated*): talk about the device's topic to a person ("did you set the oven to 400?").
    - **foreign** (real, not generated): a control. It's a phrase of at least five words from the other conversation
      stream, so it's as out of place as a spliced instruction but meant for no device.
- **Form:** every phrase is put in a recogniser's form first (lowercase words, no punctuation). The sources differ in
  typography, and no method should find the splice by its commas.
- **Duration:** non-device speech is timed at 150 words a minute, which gives 36.7 hours of it in the set.

## The methods (`harness/device_directed/methods.py`)
Each method scores every phrase for the window's own device.

| method | what it scores | size | time per phrase |
|---|---|---|---|
| keyword spotting | how many of the device's 25 keywords the phrase contains (found automatically: content words most over-represented in its training commands against general English) | 0.6 kB | 0.01 ms |
| shape only, n-gram | the device's trigram model's fit minus a general-English (Brown) model's fit, per word | 11 MB of counts | 0.05 ms |
| shape and contrast (Jay's), n-gram | the device fit minus the fit to the surrounding stream (the English model with a cache of the window's words) | same | 0.17 ms |
| shape only, MiniLM | mean cosine similarity to the device's 5 nearest training commands (all-MiniLM-L6-v2, 22M parameters, ONNX) | 90 MB fp32 (about 23 MB as int8) | 0.65 ms, plus 12.9 ms to encode a phrase (one thread, measured while the general model ran on the same CPU) |
| shape and contrast (Jay's), MiniLM | that fit minus the similarity to the phrase's 5 nearest neighbours in the window | same | 0.47 ms, plus encoding |
| general model asked | numbered window, "which line, if any, is someone speaking to the device?"; score = probability on that line's number (Qwen2.5-0.5B and 1.5B Instruct, 4-bit, llama.cpp) | 0.49 / 1.1 GB | about 4.5 s per 31-line window on 4 CPU threads (0.15 s per phrase; section 4) |

Each contrast method also runs with the past only (the phrases before, as a live device would hear them). That costs a
little: with MiniLM, 72% instead of 89% at 1 per hour.

## 1. Hits against false accepts (all devices pooled)
`curves.png` has the full curves per device. The table gives operating points, with the threshold set per device where
false accepts first reach 1 or 10 per hour across all its streams.

| method | mean hit rate over 0-60 FA/h | hits at 1 FA/h | hits at 10 FA/h | to a person accepted at 10 FA/h | subject accepted at 10 FA/h | foreign control accepted at 10 FA/h |
|---|---|---|---|---|---|---|
| keyword spotting | 58% | 9% | 33% | 52% | 21% | 2.5% |
| shape only, n-gram | 94% | 83% | 92% | 74% | 58% | 0% |
| **shape and contrast (Jay's), n-gram** | 96% | 84% | 95% | 82% | 71% | 0.6% |
| shape only, MiniLM | 92% | 61% | 89% | 88% | 69% | 1.9% |
| **shape and contrast (Jay's), MiniLM** | **99%** | **89%** | **98.5%** | 96% | 93% | 13% |
| general model asked, Qwen2.5-0.5B | 2% | 0% | 0.6% | 0.6% | 0.6% | 0.6% |
| general model asked, Qwen2.5-1.5B | 36% | 12% | 26% | 28% | 18% | 0.6% |

- **Contrast helps on both model types:** n-gram 83% to 84% at 1 per hour, and MiniLM 61% to 89%. It helps most where
  the shape model is fuzziest.
- **It isn't just finding the splice.** The foreign control (real speech that's equally out of place) is accepted
  0-2% of the time, and 13% for MiniLM-contrast at 10 per hour. A phrase has to look like the device's commands as well
  as unlike its surroundings.
- **Keyword spotting is far behind,** and every keyword false accept is, by definition, device vocabulary in ordinary
  talk ("is there a next meeting in thirty minutes").

## 2. Per device and stream (at 10 false accepts per hour, Jay's contrast with MiniLM)

| device | hits | AMI meetings | calls (speakerphone) | songs | monologue stand-in | to a person | subject | foreign |
|---|---|---|---|---|---|---|---|---|
| car | 100% | 100% (17/h) | 100% (8.9/h) | 100% (1.5/h) | 100% (7.4/h) | 97.5% | 95% | 27.5% |
| kitchen | 100% | 100% (15/h) | 100% (9.2/h) | 100% (0.5/h) | 100% (23/h) | 100% | 100% | 22.5% |
| watch | 100% | 100% (22/h) | 100% (5.8/h) | 100% (1.1/h) | 100% (7.3/h) | 100% | 97.5% | 12.5% |
| general | 93% | 95% (19/h) | 90% (7.8/h) | 97.5% (0.9/h) | 80% (15/h) | 95% | 87.5% | 15% |

In brackets are each stream's own false accepts per hour at the device's threshold.

- **Meetings make the most false accepts (15-22 per hour); songs make almost none.** AMI's meetings are about designing
  a remote control, full of buttons, settings and schedules.
- **At 1 false accept per hour,** the same method finds 95% (car), 98% (kitchen), 95% (watch) and 79% (general).
  "General" is hardest, because its commands (questions, music, news) look most like ordinary talk.
- **The speakerphone stream** (an instruction inside one side of a phone call) is found at 90-100%.
- Every device and stream for every method is in `tables.md`.
- **Failing conditions** (no method finds half the instructions at 10 per hour): none.

## 3. Hard negatives: who the words are for
At the threshold giving 1 false accept per hour, MiniLM-contrast still accepts 83% of to-a-person rewrites and 73% of
subject talk (n-gram contrast: 51% and 31%). At 10 per hour it accepts 96% and 93%.

That's not a flaw in these particular models. It's what "shape" means: "Dave, can you set an alarm for six for me?" has
the command's shape whoever it's addressed to. The cues that do separate the two are small and lexical:
- a name or "you" as the addressee ("Dave, can you ...")
- first-person narration ("I'll ...", "I was going to ...")
- tense ("but I forgot")

None of the shape methods is built to weigh them; each scores how command-like a phrase is, not who it addresses.

One caveat makes the hard negatives harder than real life. They're spliced from outside, so they're as foreign to the
surrounding talk as the instructions are. A real "I'll text Sam that I missed my flight" usually belongs to the
conversation around it, which would lower its contrast score. This set can't measure that, because it has no real
person-directed requests in their own context.

## 4. The general model asked directly
Qwen2.5-0.5B- and 1.5B-Instruct (4-bit GGUF, llama.cpp, 4 CPU threads) scored all 1,000 windows.
- **The prompt:** each window's 31 lines, numbered, and "Which line, if any, is someone speaking directly to the
  device ...? Answer with the line number, or 0 if none is."
- **A phrase's score:** the probability the model puts on its line's number as the first answer (two-digit lines: first
  digit times second).
- **Its own answer:** its most likely line, unless "0" is likelier.

| model | size | time per window | hits at 1 FA/h | hits at 10 FA/h | its own answer: hits, false accepts per hour | own answer accepts: to a person / subject / foreign |
|---|---|---|---|---|---|---|
| Qwen2.5-0.5B | 0.49 GB | 2.9 s alone (4.9 s with the CPU shared) | 0% | 0.6% | 1.9%, 26 per hour | 2.5% / 2.5% / 3.8% |
| Qwen2.5-1.5B | 1.1 GB | 4.6 s | 12% | 26% | 27%, 17 per hour | 29% / 21% / 5% |

- **0.5B answers by position, not content.** Its top line is line 5 in 446 windows and line 14 in 269, whatever the
  text. Its picks scatter around the true line with no fixed offset, so this isn't a numbering bug in the scorer. Its
  1.9% is below the 1 in 31 a blind pick would get.
- **1.5B reads the text a little.** By device at 10 per hour it finds 19-35% of the instructions, most in the songs
  (where an instruction stands out from the verse) and least in the AMI meetings (8-30%).
- **1.5B can't tell who it's for either.** Its own answer accepts 29% of the to-a-person rewrites, about the same rate
  as real instructions (27%). The foreign control, at 5%, shows it isn't simply picking the odd line out.
- **Cost:** about 0.15 s of 4-core CPU per phrase: some 860 times the n-gram contrast (0.17 ms), and 11 times MiniLM's
  13 ms per phrase including encoding. On this task a model of this size, asked this way, is both the slowest method and,
  apart from keyword spotting, the weakest. A larger model, or one fine-tuned on device commands, might do better; this
  brief asked for one a phone could plausibly run.

## False accepts, by kind (at 10 per hour; `false_accepts.json` has examples)
- **n-gram methods:** mostly very short phrases, two words or fewer ("Input.", "Potato.", "Hi."), whose few words carry
  no evidence either way. A minimum phrase length would remove most of them, but that's a rule to choose and test
  separately.
- **MiniLM methods:** mostly meeting talk near a device topic ("How long is the meeting?", "Do we need another meeting
  this week?" for the watch; "Uh this is this email" for the car). That's near-miss talk, not noise.
- **keyword spotting:** every false accept is device vocabulary in ordinary speech.

## A modelling fix, stated
In the first run the n-gram models gave a word they'd never seen a higher probability in the small device model than in
the large English one. Shakespeare's spellings and rare names then scored as device-like. Every model now gives an
unseen word the same fixed probability, so unseen words cancel in a difference. That was a correction, not a tuning
choice, and it raised n-gram shape from 74% to 92% at 10 per hour.

## Caveats
- **This is text.** Real devices get recogniser output with errors, and phrase boundaries from a voice-activity
  detector. Splicing assumes the boundaries are known.
- **The device grouping follows SLURP's intents.** Calls, oven and timer commands are missing or rare, and SLURP's
  commands were recorded by people told to speak to a device. The commands are real speech; the contexts are spliced.
- **The hard negatives are generated by templates,** and some read awkwardly ("I need to tell myself about the cheapest
  flight fares after this call").
- **The monologue stream is scripted verse,** a stand-in for real self-talk.
- **The songs and monologue sources are small:** 44 and 14 of their 30-phrase blocks were reused in a second window,
  with a different splice.

## Files
- **Recipe:** `set_index.jsonl` (no third-party text: each window's source, block, splice position, SLURP id, and the
  generated hard negatives) and `keywords.json`.
- **Scores:** `scores_<method>.jsonl` (per phrase, numbers only; `scores_llm_*` also hold the model's probability of
  "none") and `cost.json` (size and time).
- **Evaluation:** `summary.json` (every operating point, device, stream and hard-negative kind), `curves.json` and
  `curves.png` (the full curves), and `false_accepts.json` (by kind, with examples).
- **Tables:** `tables.md`.
- **Rebuild:** `harness/device_directed/` (see its README). `fetch_sources.sh` gets the sources and models, and
  `run_all.sh` runs everything.
