# Who are the words for? Words against facing (2026-10-23)

A summary of the evidence so far for Jay's argument: that what someone says, and where it sits in the talk around it,
decides whether words are meant for a device better than which way the talker faces. Written to be shown to the
Tampere group (Turi, Politis, Sudarsanam and Virtanen, "Speaker head orientation estimation with a single microphone
array using phase spectrogram features", arXiv 2607.02129). Their introduction names device addressing in smart
homes, addressee recognition in meetings, and driver attention as uses for an orientation estimate. Every number below
links to the report that produced it; the limits are stated with them.

## 1. Meetings: words and facing for picking the addressee (AMI)
`results/linguistic/ami/report.md`, section 3.
- **Data:** the 14 AMI meetings that carry both addressee labels and focus-of-attention labels (where each person
  looks, annotated from video). 5,963 dialogue acts with an annotated addressee: 3,454 to the group, 2,509 to one
  person. All four-person meetings.
- **Predictors:**
  - **Words:** a question mark, "you", "we", length, a short reply, who spoke the previous turn and who takes the next.
    No names.
  - **Facing:** the share of the act the speaker looks at each person, the table, the slides or the whiteboard.
  - Logistic regression, one meeting held out at a time.

| | right addressee |
|---|---|
| always "the group" | 57.9% |
| facing alone | 56.7% |
| words alone | 60.2% |
| words and facing | 64.4% |

- **Facing adds to the words when one person is addressed:** +9.9 points on naming which person (95% interval 6.5 to
  13.0, better in 13 of 14 meetings).
- **It doesn't help decide group or one person:** +1.3 points (-0.1 to 2.7).
- **Overall it adds 4.2 points** (2.1 to 6.0).
- **Limits:**
  - The facing here is annotated gaze, so it's better than any acoustic orientation estimate would be.
  - 14 meetings, all four people around a table.
  - The word features are simple.

## 2. Devices: finding an instruction in a stream of other speech (spliced test set)
`results/device_directed/report.md`.
- **Data:** SLURP's spoken commands (CC BY 4.0), grouped by device, spliced whole into:
  - AMI meetings;
  - Switchboard telephone calls (an instruction inside one caller's turn: the speakerphone case);
  - public-domain songs;
  - a monologue stand-in.

  1,000 windows, 36.7 hours of non-device speech, text in a recogniser's form.
- **Method, Jay's proposal:** score each phrase by how well it fits the device's instructions, minus how well it fits
  the talk around it. No facing, no audio.

| method | instructions found at 1 false accept per hour | at 10 per hour |
|---|---|---|
| keyword spotting | 9% | 33% |
| shape only (a 22M-parameter sentence model) | 61% | 89% |
| shape minus fit to the surrounding talk (Jay's) | **89%** | **98.5%** |

- **The contrast isn't just spotting the odd phrase out.** A real phrase spliced in from another conversation is
  accepted 0-2% of the time at 1 per hour, and 13% at 10.
- **Inside a phone call** (the speakerphone case), instructions are found 90-100% of the time at 10 per hour.
- **Open: who the instruction is for.** The same instructions rewritten as said to a person ("I'll text Sam that
  ...", "Dave, can you ...") are accepted 83% of the time at 1 per hour. Those rewrites were spliced in from outside,
  though, so they were as foreign to the surrounding talk as the real instructions. Section 3 has the real test.

## 3. Real requests to people, where they were said (Switchboard)
`results/who_for/report.md` (brief 22). 620 real requests from one caller to the other (directives, "can you ..."
questions, "I'll ..." commitments), left in their own calls, scored with brief 19's methods and thresholds unchanged.
- **They're rarely taken for device instructions:** Jay's contrast accepts 4.4% at 10 false accepts per hour and 0.2%
  at 1 per hour. Brief 19's 83-96% for to-a-person phrases was mostly an artefact of generating them from device
  commands and splicing them in.
- **Context does the work Jay said it would:** the same words spliced into another call are accepted 19.6% of the
  time. For 86% of request-and-device pairs they score lower in their own conversation than spliced elsewhere.
- **The speakerphone case on real calls:** car instructions spliced into Switchboard calls score above real requests
  in other calls 99.9% of the time. At the car's 1-per-hour threshold, 97% of instructions are found and 0.5% of real
  requests accepted. Those that pass are mostly talk about operating a gadget, or asking the other caller to hold on:
  ambiguous to a human too.
- **Grammar cues ("you", "I'll", names) add little on real speech** (3 points or less), because the hard cases are rare
  and the cues fire on device commands too.
- **Limits:** text, not recogniser output; telephone conversation, one corpus; AMI's requests weren't reachable.

## What this supports, and what it doesn't yet
- **Supported:** for a device, the words alone find instructions in ongoing speech at about one false accept per
  hour, from text, with a model small enough for a phone. Orientation isn't needed for that step.
- **Supported:** among people in a meeting, facing earns a modest place. It's worth about 10 points when choosing
  which person is addressed, and nothing when deciding whether the whole group is.
- **Now shown, on real telephone speech:** words in their context separate an instruction to a device from a request
  to a person. 97% of instructions found, 0.5% of real requests accepted (brief 22).
- **Not tested here:** an acoustic orientation estimate in place of annotated gaze, and recogniser errors (both sets
  use reference text).

## The constructive side, from DareDevil's own data
Orientation decided whether a two-microphone bearing could be trusted. On LOCATA, at the phone's spacing, no read of a
talker alone and facing the array was more than 10 deg off (0 of 52). Alone and facing away, 62% were (n = 16).
`results/batchA/locata/report.md`. An orientation estimate may be as useful for telling a localizer when to trust
itself as for deciding who is being addressed.
