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
  though, so they were as foreign to the surrounding talk as the real instructions. Brief 22 tests real requests to
  people in their own context, and adds the cues that say who words are for.

## What this supports, and what it doesn't yet
- **Supported:** for a device, the words alone find instructions in ongoing speech at about one false accept per
  hour, from text, with a model small enough for a phone. Orientation isn't needed for that step.
- **Supported:** among people in a meeting, facing earns a modest place. It's worth about 10 points when choosing
  which person is addressed, and nothing when deciding whether the whole group is.
- **Not yet shown:** that words alone separate "an instruction to the device" from "the same request said to a
  person", in real speech. That's brief 22.
- **Not tested here:** an acoustic orientation estimate in place of annotated gaze, and recogniser errors (both sets
  use reference text).

## The constructive side, from DareDevil's own data
Orientation decided whether a two-microphone bearing could be trusted. On LOCATA, at the phone's spacing, no read of a
talker alone and facing the array was more than 10 deg off (0 of 52). Alone and facing away, 62% were (n = 16).
`results/batchA/locata/report.md`. An orientation estimate may be as useful for telling a localizer when to trust
itself as for deciding who is being addressed.
