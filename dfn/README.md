# Jay's scripts around DeepFilterNet3

These wrap the stock DeepFilterNet3 (https://github.com/Rikorose/DeepFilterNet, dual MIT / Apache-2.0); they don't
modify it. DFN's `enhance()` keeps only the denoised spectrum and discards the model's other outputs. These scripts
call the model directly and keep all four: the ERB mask `m`, the local SNR `lsnr`, and the deep-filter coefficients.

- **`dfn_shared.py`:** one DFN pass on the mono mixdown, with the same mask and deep filter applied to both channels.
  A common real gain can't change the level ratio between channels, and the deep filter is linear in time, so the
  inter-channel phase factors out for a stationary talker. Also the mask-weighted spatial covariance: bearing,
  coherence, and a measured direct-to-diffuse ratio.
- **`dfnlab_data.py`:** per utterance, the envelope, CDR on the raw pair and on the DFN pair, `lsnr` and the mask, for
  the DfnLab page.
- **`maskview.py`:** the whole tape on DFN's 10 ms grid: raw level in three bands, mean mask, `lsnr`, and the full
  32-band mask. It imports `rot_bearing` (`source_of`, `read_stereo`), which isn't in this repo.
- **`maskview_starss.py`:** the same bake for a STARSS23 recording, runnable from this repo. One capsule pair mixed
  down, 24 -> 48 kHz, one fixed gain bringing labelled speech to -26 dBFS (as-recorded figures kept in the file), and
  STARSS23's labelled sounds in place of the walk's onsets and transcript. Bakes in `maskview/`; the Mask View page is
  `docs/maskview.html`.

**First look at STARSS23 (2026-10-23, two recordings, `maskview/starss23-*.json`):**
- **As recorded, DFN calls almost everything noise.** Labelled speech sits at -47.5 and -63.5 dBFS, and `lsnr` is above
  0 dB in 0.4% and 0.0% of frames.
- **With one fixed gain:** in room 16, `lsnr` crossed 0 dB within 0.6 s of 31 of 35 labelled speech onsets (median
  60 ms after the 100 ms label). In room 4, quieter speech, 11 of 18 (median 270 ms).
- **It also opens on sounds that aren't speech:** a knock (+16 dB) and footsteps (+16 dB) in room 16, a telephone ring
  (+10.9 dB) in room 4, with nobody talking. Brief 16 measures this across every recording.

**Jay's findings (2026-10, on his house tapes; his own caution: anything upstream in his pipeline could be the cause):**
- **The mask as a speech track** missed the soft first word and opened on footsteps.
- **`lsnr` as a speech track worked.** It crossed 0 dB at every speech start, within 16 ms of the MF onset, and never
  in gaps.
- **Mask-weighting the 5 ms read** strengthened the ghost reading instead of the voice.
- **Nothing normalises the input level,** and DFN treats the −48 to −51 dBFS tapes as noise. On LOCATA, `lsnr` went
  from −5.4 to +3.3 dB once the level was normalised.
