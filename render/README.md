# Render

`Render.html` is the page that draws what the pair hears, played against a tape. It's served by Jay's local Voice
server and fetches from its routes, so it doesn't run from GitHub on its own:
- `geonar/tapes`, `geonar/truth`, `geonar/anglerays`, `geonar/decode`
- `math/process`, `math/positions`
- `maskview-data`, `rangelab-fixture`, `speaker2d-scene`

**The DFN mask panel** (bottom right) draws `dfn/maskview.py`'s bake for the playing tape, live: the 32-band ERB gain
map for the last 5 s, MaskView's raw level / mean mask / `lsnr` lines, and a strip of the LF, MF and HF mask with
the HF-to-LF tilt.
- **It appears** when the scheme name starts with `dfn`, or with `?mask=1` in the URL.
- **Its data** comes from `maskview-data?name=<tape>`: one JSON per walk, like `dfn/maskview/walk-205043.json`.
- **It never draws ahead of what was heard.** DFN3 looks 2 frames ahead, so frame k is final at (k + 3) x 10 ms.

There's also a live speech spectrogram panel (top left: magma, 0-8 kHz, the last 5 s heard).

A note in the code worth keeping in view: on LOCATA, the mask's HF-to-LF tilt tracked range (rho -0.5 to -0.67
against distance), not facing.

**Bearing after the lock (2026-10-23, `GccPhat.mjs`).** The stream no longer just holds its lock. Every 250 ms it
re-reads the newest half second, and position 1 moves only when that re-read commits (brief 11's rule) and differs by
more than 5 deg. Position 1 now carries `committed` (whether the shown read passes the rule; draw it dimmed when false)
and `moves` (how many times it has moved this utterance), and the stream's output carries `reread` (re-reads, moves,
committed, and the pause's own read). `createStream(..., { reread: false })` restores lock-and-hold.

**Range (Conductor v13).** The range is handed only the utterance's first half second of CDR frames (`RANGE_READ_S`),
so it reads once and holds. `RANGE_READ_S = None` restores v12.

**Facing (Conductor v14, `CdrRange.js`, 2026-10-24, brief H).** Each utterance now gets one facing call, 2 s after its
onset.
- **The field:** `facing(f)` returns `"facing"`, `"turned"` or `null`, and `facingContrast(f)` returns the dB behind
  it (CDR 4-8 kHz minus CDR 0.1-1.1 kHz, turned below −1 dB).
  - **Null** until the utterance's 2 s frame, and for any utterance that closes before it (about three in four).
  - **Held** after the utterance closes, until the next one opens.
- **The dot:** it is placed at 0.5 s as before. When the call is turned it moves once more, at 2 s, nearer by the range
  correction. It doesn't move at all on a facing call.
- **Draw a turned talker faded.** The page already does this for a timeline entry carrying `turned: true` (the disc at
  0.4, the bubble at 0.45, the "turned" label).
  - **The missing wire is in Voice, not here:** MathPass.mjs must write `turned: range.facing() === "turned"` into the
    timeline. Today it never sets it.
- **What "turned" means:** Jay's fade line is 120 deg, but the cue can't tell 120 from 90 (brief A's flat-bottomed U).
  In practice a talker fades once past about side-on, and 45 deg reads as facing (brief D).
- **How often it's right:** 76% balanced on Jay's walks (51 calls) and 68% on LOCATA (62). Brief G's 2-4 s utterances
  scored 75%.
