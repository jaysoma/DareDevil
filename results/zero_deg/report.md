# The 0 deg peak in silence, on STARSS23 (2026-10-22)

## Question
ODAS puts 47% of its active pause directions within 6 deg of 0 on every phone placement (HANDOFF.md, "Done" item 2).
The top suspect was low-frequency diffuse noise, which is coherent at zero lag. If that's the cause, the share of
GCC-PHAT peaks near 0 in STARSS23 pauses should collapse as the high-pass rises, and the mechanism would be general
rather than the phone's.

## Answer
**There is no 0 deg peak in STARSS23 pauses, so there is nothing to collapse.** At high-pass 0, 10.5% of the GCC-PHAT
peaks fall within 6 deg of 0. A null with no coherence between the capsules gives 9.5%. A high-pass at 1100 Hz takes
the share to 9.2%. This holds in all 16 rooms and all 6 pairs, and it holds whether the peak is read frame by frame or
summed over half a second as `GccPhat.mjs` reads.

**The suspected noise is there, in every room.** Coherence between the capsules in the pauses is 0.99 below 300 Hz and
about 0.7 at 300-1100 Hz, in all 16 rooms: diffuse low-frequency noise, coherent at zero lag. It just doesn't pull
GCC-PHAT's peak to 0. A simulated ideal diffuse field agrees: at most 16-23% near 0 at 68.5 mm and 13-19% at the
phone's 157 mm, never 47%.

**So low-frequency diffuse noise is unlikely to be the phone's 0 deg.** On the phone, ODAS's 0 deg peaks get sharper
as the frame gets stronger: in the strongest quarter of pause frames, 30% sit within 6 deg of 0 and 18% exactly on
0.0 (corrected; see "Second correction"). On STARSS the strongest quarter gives 11%. A peak that tightens on zero lag as the frame gets stronger is what a
signal identical in both channels does: electrical crosstalk, a shared codec path, or one channel leaking into the
other. That's the brief's other suspect. `harness/zero_deg/phone_pause.py` settles it on the phone's own audio (see
"Next").

## What was run
- **Data:** STARSS23 development set, MIC format (https://zenodo.org/records/7880637): 168 recordings, 16 rooms, all 6
  capsule pairs (68.5-68.8 mm apart, on a rigid sphere of radius 4.2 cm). The audio stays out of the repo.
- **Pauses (`silence`):** 100 ms label frames with no labelled event of any class. I kept them 300 ms clear after an
  event ends and 100 ms before the next begins. I skipped each file's first 2 s, in case the scene-start clapper is
  there. I dropped frames holding digital zeros: the Tampere files end in 1-6 s of zero padding, which carries no labels
  and would otherwise read as silence. Result: 43 minutes of silence, 732,258 frame reads across the 6 pairs.
- **A second set (`speechfree`):** no speech, with the same guards, but other labelled events may sound. That's the
  brief's literal wording. It gives the same answer (tables.md).
- **The read:** 1024-sample Hann frames at the native 24 kHz (42.7 ms, the span of GccPhat.mjs's 2048 at 48 kHz),
  every 512 samples. For each frame and pair: PHAT of L conj(R), from the high-pass up to 8 kHz, scored over 241 delays
  across the pair as in GccPhat.mjs. The tallest delay is the peak. "Near 0" means |lateral angle| < 6 deg.
- **High-passes:** 0, 100, 300 and 1100 Hz, plus 2500 Hz. 2500 Hz is the 1100 Hz of a 157 mm pair scaled to 68.5 mm:
  diffuse coherence holds up to about c / 2d, which is 1.1 kHz on the phone and 2.5 kHz here.
- **Summed:** the same, with 24 consecutive frames' cross-spectra added before the PHAT (0.5 s, as GccPhat.mjs sums),
  one read per block.
- **Null:** the same frames, with the second capsule taken from another pause frame of the same file. The spectra are
  the same, with no coherence between capsules.

## 1. The share near 0, by high-pass
Pooled over 16 rooms and 6 pairs, silence:

| % within 6 deg of 0 | HP 0 | HP 100 | HP 300 | HP 1100 | HP 2500 |
|---|---|---|---|---|---|
| frame by frame | 10.5 | 10.5 | 10.5 | 9.2 | 9.0 |
| summed over 0.5 s | 10.3 | 10.3 | 10.3 | 9.7 | 9.2 |
| null, frame by frame | 9.5 | 9.5 | 9.5 | 9.7 | 10.5 |
| strongest 25% of frames | 11.4 | 11.4 | 11.4 | 10.0 | 9.1 |

**By pair, pooled over rooms (frame by frame):**

| pair | HP 0 | HP 100 | HP 300 | HP 1100 | HP 2500 | null |
|---|---|---|---|---|---|---|
| 1-2 | 12.6 | 12.6 | 12.6 | 11.2 | 10.0 | 9.3 |
| 1-3 | 10.8 | 10.8 | 10.8 | 9.6 | 9.4 | 9.4 |
| 1-4 | 8.3 | 8.3 | 8.2 | 7.2 | 7.5 | 9.6 |
| 2-3 | 10.4 | 10.4 | 10.3 | 9.2 | 9.1 | 9.5 |
| 2-4 | 10.7 | 10.7 | 10.7 | 9.3 | 9.2 | 9.6 |
| 3-4 | 10.3 | 10.3 | 10.2 | 8.8 | 8.9 | 9.5 |

**By room, pooled over pairs (frame by frame):**

| room | reads per pair | HP 0 | HP 100 | HP 300 | HP 1100 | HP 2500 | null |
|---|---|---|---|---|---|---|---|
| 2 | 2358 | 10.2 | 10.3 | 10.2 | 8.7 | 8.2 | 9.7 |
| 4 | 13223 | 10.5 | 10.5 | 10.4 | 8.9 | 8.8 | 9.6 |
| 6 | 6931 | 9.4 | 9.4 | 9.3 | 8.1 | 7.8 | 9.3 |
| 7 | 4553 | 8.2 | 8.2 | 8.1 | 7.0 | 6.8 | 9.1 |
| 8 | 4552 | 11.5 | 11.5 | 11.5 | 9.9 | 9.0 | 9.4 |
| 9 | 13059 | 11.6 | 11.6 | 11.5 | 9.9 | 9.6 | 9.5 |
| 10 | 8934 | 11.3 | 11.3 | 11.2 | 10.6 | 10.9 | 9.6 |
| 12 | 5383 | 11.4 | 11.4 | 11.3 | 9.9 | 8.8 | 9.6 |
| 13 | 7770 | 10.7 | 10.7 | 10.7 | 9.1 | 8.7 | 9.4 |
| 14 | 2190 | 11.2 | 11.2 | 11.1 | 10.2 | 10.2 | 9.6 |
| 15 | 9617 | 12.0 | 12.0 | 11.9 | 10.5 | 10.2 | 9.6 |
| 16 | 8444 | 10.8 | 10.8 | 10.7 | 9.7 | 9.7 | 9.4 |
| 21 | 13823 | 8.9 | 8.9 | 8.9 | 8.2 | 8.6 | 9.5 |
| 22 | 15077 | 10.0 | 10.0 | 10.0 | 8.8 | 8.4 | 9.4 |
| 23 | 1443 | 6.6 | 6.6 | 6.6 | 5.5 | 5.8 | 9.2 |
| 24 | 4686 | 12.0 | 12.0 | 11.9 | 10.3 | 10.0 | 9.6 |

Every room and pair at every high-pass, and the summed read, are in `tables.md`.

- **Over the null:** the median room-and-pair cell sits 0.2 points above it. The high-pass at 1100 Hz moves a cell by
  -1.3 points at the median (range -3.0 to 0.0).
- **The highest cells don't come from zero lag.** They reach 21-25% (room 12 pair 2-4, room 8 pair 3-4, room 6 pair
  1-2), and they hold at 17-21% with the high-pass at 2500 Hz, where diffuse coherence is gone. Each appears on one pair
  of its room and not the others. That's a steady directional source (a vent, a machine) that happens to lie near that
  pair's broadside: the room, not zero lag.

## 2. The diffuse noise is there, and PHAT ignores it
Coherence between the capsules in the pauses, as Re(Sab) / sqrt(Saa Sbb), averaged over the 6 pairs:

| Hz | 0-100 | 100-300 | 300-1100 | 1100-2500 | 2500-8000 |
|---|---|---|---|---|---|
| ideal diffuse field, two free-field points 68.5 mm apart | 1.00 | 0.99 | 0.87 | 0.35 | -0.03 |
| STARSS rooms, lowest to highest | 0.99-1.00 | 0.96-0.98 | 0.65-0.73 | 0.02-0.09 | -0.08-0.11 |

All 16 rooms match the diffuse curve below 300 Hz. They fall below it from 300 Hz up, which the sphere's scattering
and the capsules' own noise would both do. It's the README's "natural background noise (e.g. HVAC noise) in all
recordings ... mostly diffuse".

Why it doesn't make a 0 deg peak: PHAT gives every frequency slice one vote, and a low slice's vote barely tells delays
apart.
- **How few votes:** below 300 Hz there are 12 slices out of the 341 up to 8 kHz.
- **How little each vote separates delays:** at 300 Hz, the phase difference between straight ahead and end-fire is
  0.38 rad across 68.5 mm and 0.86 rad across 157 mm. A zero-lag vote at 300 Hz scores nearly every delay alike.
- **Where the delays are actually decided:** the slices that separate delays sit above about c / 2d, where diffuse
  noise has stopped being coherent.

The simulation (`harness/zero_deg/sim_diffuse.py`) puts this to the test with the same PHAT, frames and delay grid, no
room and no sphere: 256 plane waves per frame, from uniform directions.

| % within 6 deg of 0 | HP 0 | HP 300 | HP 1100 | HP 2500 |
|---|---|---|---|---|
| 68.5 mm, capsule noise only (floor) | 10.0 / 11.6 | 9.9 / 11.6 | 10.3 / 11.2 | 10.5 / 11.2 |
| 68.5 mm, diffuse, flat spectrum | 15.6 / 3.6 | 15.4 / 3.6 | 11.2 / 2.4 | 2.5 / 0.0 |
| 68.5 mm, diffuse falling 12 dB/oct + capsule noise, equal at 1 kHz | 14.3 / 22.8 | 14.1 / 22.8 | 12.3 / 19.2 | 8.9 / 6.4 |
| 157 mm, capsule noise only (floor) | 10.5 / 12.0 | 10.5 / 11.6 | 11.7 / 12.4 | 9.8 / 14.4 |
| 157 mm, diffuse, flat spectrum | 10.3 / 4.0 | 9.9 / 4.0 | 4.1 / 0.4 | 9.8 / 6.4 |
| 157 mm, diffuse falling 12 dB/oct + capsule noise, equal at 1 kHz | 13.3 / 18.8 | 12.8 / 17.2 | 9.1 / 4.8 | 10.9 / 12.0 |

Each cell is frame by frame / summed over 12 independent frames. The other crossover frequencies (300 Hz and 3 kHz)
are in `sim_diffuse.json`.

Even the most favourable diffuse field puts at most 23% near 0, and 19% at the phone's spacing. A high-pass at
1100 Hz takes the phone-spacing case to 5-9%. If the phone's 47% were diffuse noise, it would need far more than a
diffuse field can give.

## 3. The phone's 0 deg looks different
`harness/zero_deg/odas_tapes.py` reads the committed ODAS runs (`tapes/*/odas.json`, 157 mm, `ssl_hp_hz` 0). It takes
only frames in the pauses between Whisper segments, 0.5 s clear of each: 37,651 frames over the 29 tapes.

| ODAS top pot (its frame's SRP-PHAT peak), pauses | within 6 deg of 0 | exactly 0.0 |
|---|---|---|
| weakest quarter of frames | 13.2% | 7.7% |
| second quarter | 15.6% | 8.8% |
| third quarter | 17.8% | 10.6% |
| strongest quarter | 50.3% | 40.8% |
| all frames | 24.4% | 17.1% |
| active tracks (activity > 0.6) | 45.7% | |

- **The 47% is reproduced:** the active tracks give 45.7%.
- **The weak frames look like STARSS:** the phone's weakest frames sit at about the floor, as every STARSS frame does.
- **The strong frames don't:** the phone's strongest quarter sits on zero lag half the time, against 11% for STARSS's
  strongest quarter.
- **Why that rules out diffuse noise:** diffuse noise makes many weak, broad votes, not the frame's strongest peak.
  The tightening points to something common to both channels across the band.

**That's a comparison across methods, not a result.** ODAS is SRP-PHAT on its own grid and frame, read through its
tracker; GCC-PHAT is not run here on the phone's audio. The phone's audio isn't in this repo.

## Correction (same day): one tape is a mono duplicate
Section 3 counted every tape, including the three that `agent_task_truth_recovery.md` excludes: walk-194532 (a mono
duplicate, both channels identical) and walk-195454 and walk-212347 (dead capsule pairs). walk-194532 reads exactly
0.0 deg with E = 1.00 on 100% of its frames: identical channels have zero delay and perfect coherence.

| ODAS, pauses | all 29 tapes | without the 3 excluded tapes |
|---|---|---|
| top pot within 6 deg of 0 | 24.4% | 19.0% |
| top pot exactly 0.0 | 17.1% | 11.2% |
| active tracks within 6 deg of 0 | 45.7% | 44.2% |

The active-track figure, the original 47%, barely moves, so the conclusion stands. The pot shares above were
inflated by that tape.

**Second correction (2026-10-23): the strength split also counted the excluded tapes.** walk-194532's frames are all
exactly 0.0 with E = 1.00, so they land in the strongest quarter. Re-run without the 3 tapes
(`odas_tapes_excluded.json`, 32,108 pause frames over 26 tapes):

| ODAS top pot, pauses, without the 3 excluded tapes | within 6 deg of 0 | exactly 0.0 |
|---|---|---|
| weakest quarter of frames | 13.0% | 7.4% |
| second quarter | 15.7% | 8.9% |
| third quarter | 17.3% | 10.2% |
| strongest quarter | **29.9%** (was 50.3%) | **18.4%** (was 40.8%) |
| all frames | 19.0% | 11.2% |

The trend holds: the share near 0 still rises with frame strength, and the strongest quarter is still about three times
STARSS's 11%. But it's 30%, not 50%. Section 3's table and bullets keep the uncorrected 50% and 41% as first run; the Answer at the
top now uses the corrected figures.
Brief 13's lab found that a signal identical in both channels makes the 0 deg pull and diffuse noise doesn't
(`results/batchA/lab/report.md`), which points the same way.

**Why ODAS says exactly 0.0.** ODAS snaps every peak to a point of its scan sphere: 65 distinct angles appear in these
files, with the nearest neighbours of 0.0 at -2.3 and +3.8. Point 0 of that sphere is the pole (0, 0, 1)
(`src/init/space.c`, confirmed by building it). For a two-capsule pair, every point with the same delay scores the same.
`mod_ssl.c` starts its search at point 0 and keeps the first of equal scores, so any zero-delay win, or a frame where
nothing beats point 0, reports x = 0 and asin(0) = 0.0 exactly. ODAS's tracks are smoothed and spread over about +-3 deg.

## Next: the decisive test, on the phone's audio
Run `python3 harness/zero_deg/phone_pause.py <dir with the tapes' .raw files>` where the tapes live. It measures the
same pause shares at 0, 100, 300 and 1100 Hz, frame by frame and summed, at 157 mm and 48 kHz, plus the pause
coherence by band, for each tape.
- **If it's diffuse noise:** coherence follows the free-field curve for 157 mm (0.99 below 100 Hz, 0.94 at 100-300 Hz,
  0.45 at 300-1100 Hz, about 0 above; the script prints it) or falls below it. The 0 deg share falls with the 1100 Hz
  high-pass.
- **If it's a common-mode signal:** coherence stays well above 0 above 1.1 kHz, and the share survives every
  high-pass. On a synthetic tape with a broadband signal common to both channels in half its pauses, the script
  read 0.48 above 1.1 kHz and 41-42% near 0 at every high-pass.

If it's common-mode, a high-pass won't fix it. Subtracting the coherent part, or checking whether the capture path
mixes channels, would.

## Caveats
- **Array:** 68.5 mm on a rigid sphere, not 157 mm on a phone chassis. The simulation covers both spacings in free
  field only.
- **Pauses are label-free, not sound-free:** unlabelled sounds (anything outside the 13 classes) stay in. That's
  intended, since the phone's pauses aren't sound-free either.
- **ODAS isn't run on STARSS:** section 3 compares ODAS on the phone with GCC-PHAT on STARSS. Running ODAS itself on
  STARSS pauses would close that gap, but the binary in `tapes/*/odas.json` is a Windows build.
- **The null and the floor sit near 10%,** not the 6.7% a uniform spread in angle would give. GCC-PHAT on a uniform
  delay grid puts sin(6 deg), about 10%, of the delay range within 6 deg of 0. Compare against the null, not against
  zero.
- **Room 23 has only 1.4 minutes of silence** (1,443 reads per pair, 49 summed reads). Its low summed share isn't
  meaningful.

## Files
- **`pause_gcc.json`:** counts per set (silence, speechfree) x room x pair x high-pass, frame by frame and summed, with
  the null. Also peak histograms (2 deg bins), the strength split, coherence curves per room and pair, and per-file
  pause totals.
- **`tables.md`:** every table, from `harness/zero_deg/summarize.py pause_gcc.json sim_diffuse.json`, including room x
  pair at each high-pass.
- **`sim_diffuse.json`:** the simulation.
- **`odas_tapes.json`:** the phone-side ODAS split, per tape too.
- **To re-make:** `python3 harness/zero_deg/pause_gcc.py <starss23 dir> <out>` (about 10 minutes on 4 cores, with
  `mic_dev` and `metadata_dev` unzipped in the STARSS23 dir), `sim_diffuse.py <out>`, and
  `odas_tapes.py tapes <out.json>`.

## Logged reads on STARSS23 (same day, after the argmax change)
`GccPhat.mjs` and `Angle2.mjs` now take the max after scoring every delay, return no read for a scan with no peak, and
log every read that lands on 0 deg. Re-run on all 8,532 STARSS23 cuts:
- **Final reads:** all 8,532 identical to `results/starss23/after_angle2_fix/`.
- **Scans with no peak:** GccPhat logged 387, every one with every frequency's vote weighted to 0 by the pause (all
  scores exactly 0). All fell in the settling half second, never at the lock. Before the change, each drew a +90 deg dot
  for that frame. Angle2 logged none.
- **Final reads at exactly 0 deg:** GccPhat 31 and Angle2 39, out of 8,532. For 19 of GccPhat's 31, the truth was within
  6 deg. On STARSS, 0 deg isn't special.
- **What a 0 deg read looks like in the log:** for example `{"score":19.04,"mean":14.92,"min":8.64,"share":0.634,
  "width":[-73.4,60.1]}`. The winner barely clears the mean, and the peak spans most of the arc. That's a read with
  almost no direction in it. Filter the house tapes' console for `[GccPhat] zero` and compare the widths.
