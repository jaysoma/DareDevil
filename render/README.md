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
