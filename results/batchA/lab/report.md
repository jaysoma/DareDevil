# Batch A, brief 13: which cause makes a wrong lock, and its fingerprint (2026-10-23)

## What was run
- **Speech:** human and anechoic. Twelve phrase onsets from four EARS speakers (p002, p003, p004, p007), picked the way
  `harness/dechorate/dechorate_cut.py` picks them: each rises out of silence. The second voice is running speech from
  two other speakers (p001, p005).
- **Placement, the only synthetic part.** The talker sits at -75 to +75 deg in 5 deg steps (31 angles x 12 onsets =
  372 cuts per placement and setting):
  - `free157`, `free69`: exact fractional delays on two free-field points, 157 mm (the phone) and 69 mm (a STARSS pair).
  - `room000000`, `room011111`: dEchorate v1.0's measured RIRs (`dechorate_rir_processed.hdf5`), the 155 mm pair (mics
    0 and 3) of four source/array combinations, all absorbing and all reflective. The measured direct pulse is cut out
    and put back at the talker angle with exact fractional delays. Everything after it (reflections, reverberation)
    stays as measured. So the RIRs carry the room's mechanisms, and no geometry is read from them. The four
    combinations have direct-to-reverberant ratios from +7 to -8 dB.
- **Cut:** 2.0 s, 1.0 s before the onset. Every cut has independent capsule noise 50 dB under the voice.
- **Levels:** each added sound's rms is set relative to the voice's rms over the 0.5 s after the onset, both capsules.
- **Schemes:** both unchanged from `src/schemes/` (`main` at 7770530), fed as the Conductor feeds them. The read starts
  one 512-sample step before the onset handed over, in 512-sample pushes.
- **Records:** one per read in the batch A shared format (`reads.jsonl.gz`, 69,936 records; `truth.jsonl.gz`, one per
  cut, no audio).
- **Scoring:** Jay's rule (`harness/scoring/clean_score.py`). A scenario is one placement x setting x talker angle,
  with its 12 onsets. Every angle is inside the +-75 deg scope.

**One thing at a time.** Each setting changes one thing against `baseline`:

| # | cause | levels | how |
|---|---|---|---|
| 1 | `steady_pink`, `steady_voice` | -30, -20, -10, 0 dB | pink noise or a second talker at +40 deg, sounding through the pause and under the speech; placed like the talker (in the rooms, through another source's measured RIR at the same mics) |
| 2 | `common_mode` | -30 to 0 dB | pink noise identical in both channels |
| 3 | `diffuse` | -30 to 0 dB | pink noise with an ideal diffuse field's coherence at the pair's spacing, sinc(2 f d / c); the rooms use the same model at 155 mm |
| 4 | `band_lo` | 300, 1100, 2000 Hz | the analysis band's low edge, in copies under `harness/batchA_lab/variants/` (not the shipped schemes). GccPhat ships at 300 and Angle2 at 1100, so `band_lo:300` changes only Angle2, `band_lo:1100` only GccPhat, and `band_lo:2000` both |
| 5 | `onset_offset` | -50, -25, +25, +50, +100, +150 ms | the onset handed to both schemes, on the baseline audio |
| 6 | `no_pause` | | GccPhat handed the cut from its read start, so no pause weights its votes. Run on the baseline cuts as briefed, and also on every cut of causes 1-3 (`no_pause+<cause>`): a silent pause gives nothing to weigh |
| 7 | `quiet` | 30, 20, 10, 5 dB SNR | the capsule noise raised to that level under the voice |

## Headline
1. **Angle2 falls first to any coherent sound, at the mildest level run.** A steady source or a common-mode signal
   30 dB under the voice already makes 10-57% of its onsets wrong by more than 10 deg. GccPhat holds to within 0-10%
   until -20 or -10 dB.
   - **What happens:** Angle2 locks onto the other sound, or onto 0 deg for common-mode.
   - **Its own flag doesn't catch it:** those wrong onsets almost all carry `edge: true`.
2. **GccPhat's pause weighting is what protects it from steady sources.** Without it, GccPhat's wrong share under pink
   noise at -10 dB goes from 11-41% to 50-77%. Under common-mode at -20 dB in the rooms, it goes from 5-27% to 52-70%.
   Against a second voice the weighting doesn't help; a voice's spectrum moves too much to weigh out.
3. **A common-mode signal produces the 0 deg pull, and nothing else in the lab does.**
   - **Common-mode:** zero_pull is on 76-90% of GccPhat's wrong reads and 85-90% of Angle2's.
   - **Diffuse noise, the other suspect:** almost never pulls to 0. Its pause read sits within 6 deg of 0 on 0.5-1.6% of
     cuts, which agrees with `results/zero_deg/report.md`.
4. **Diffuse noise and a quiet voice make reads wide and scattered, not locked.** GccPhat is robust down to 0 dB
   diffuse and 5-10 dB SNR. Angle2 loses its clean edges and starts missing at 20-30 dB SNR in the rooms.
5. **Spatial aliasing produced no wrong locks.** In free field, no talker angle gave an aliasing-partner read at
   either spacing, in any band. Raising the low edge didn't help either. In the reflective room it cost GccPhat (3.5% ->
   5.9% -> 8.6% wrong at 300, 1100 and 2000 Hz), and it did nothing anywhere else.
6. **Onset errors barely matter.**
   - **Both schemes** absorb -50 to +100 ms.
   - **+150 ms in the reflective room:** 13% (GccPhat) and 11% (Angle2) are wrong. The pause they're handed then holds
     the word's own start, and the weighting removes the talker's own slices.
7. **Every cause leaves a fingerprint in the recorded clues,** strong enough to tell them apart (section 3). The
   strongest single clue is the pause read: how directional it is (`pause_share`), and where it points.

## 1. Wrong-lock rates
Each cell is GccPhat / Angle2: the % of reads off by more than 10 deg, with the % off by more than 36 deg in
brackets. There are 372 reads per cell.

| cause | free157 | free69 | room000000 | room011111 |
|---|---|---|---|---|
| baseline | 0 (0) / 1 (0) | 0 (0) / 9 (0) | 0 (0) / 1 (0) | 4 (2) / 2 (0) |
| steady_pink:-30 | 0 (0) / 23 (12) | 1 (0) / 38 (12) | 0 (0) / 25 (14) | 2 (1) / 10 (5) |
| steady_pink:-20 | 2 (0) / 32 (20) | 7 (0) / 46 (18) | 6 (1) / 54 (35) | 14 (9) / 32 (18) |
| steady_pink:-10 | 11 (2) / 55 (36) | 26 (5) / 61 (30) | 39 (16) / 72 (45) | 41 (17) / 60 (36) |
| steady_pink:0 | 76 (43) / 80 (52) | 81 (48) / 81 (49) | 86 (52) / 83 (50) | 87 (52) / 79 (45) |
| steady_voice:-30 | 0 (0) / 38 (25) | 1 (0) / 46 (26) | 0 (0) / 24 (16) | 2 (1) / 10 (5) |
| steady_voice:-20 | 2 (1) / 49 (30) | 4 (2) / 53 (32) | 1 (0) / 36 (20) | 5 (2) / 22 (14) |
| steady_voice:-10 | 10 (5) / 59 (34) | 13 (6) / 60 (36) | 12 (6) / 48 (31) | 14 (9) / 30 (19) |
| steady_voice:0 | 32 (20) / 66 (40) | 31 (18) / 68 (41) | 39 (23) / 53 (31) | 36 (20) / 40 (23) |
| common_mode:-30 | 0 (0) / 20 (9) | 0 (0) / 42 (19) | 0 (0) / 55 (35) | 10 (5) / 57 (36) |
| common_mode:-20 | 1 (0) / 39 (23) | 5 (2) / 50 (20) | 5 (2) / 70 (46) | 27 (13) / 74 (46) |
| common_mode:-10 | 8 (0) / 61 (42) | 28 (8) / 63 (27) | 34 (11) / 81 (50) | 54 (27) / 84 (52) |
| common_mode:0 | 72 (37) / 83 (52) | 84 (52) / 78 (42) | 75 (42) / 84 (52) | 84 (52) / 84 (52) |
| diffuse:-30 | 0 (0) / 1 (0) | 0 (0) / 11 (0) | 0 (0) / 3 (0) | 3 (1) / 8 (2) |
| diffuse:-20 | 0 (0) / 1 (0) | 0 (0) / 12 (0) | 0 (0) / 16 (7) | 3 (0) / 21 (8) |
| diffuse:-10 | 0 (0) / 7 (4) | 3 (0) / 22 (1) | 3 (0) / 30 (12) | 6 (0) / 39 (23) |
| diffuse:0 | 2 (0) / 27 (11) | 22 (0) / 48 (4) | 14 (0) / 51 (22) | 22 (2) / 61 (28) |
| quiet:30 | 0 (0) / 2 (0) | 0 (0) / 12 (0) | 0 (0) / 4 (2) | 3 (1) / 10 (5) |
| quiet:20 | 0 (0) / 3 (1) | 0 (0) / 16 (0) | 0 (0) / 20 (7) | 2 (0) / 27 (12) |
| quiet:10 | 0 (0) / 12 (4) | 3 (0) / 30 (2) | 3 (0) / 34 (16) | 9 (0) / 50 (27) |
| quiet:5 | 1 (0) / 20 (8) | 4 (0) / 42 (4) | 7 (0) / 47 (20) | 18 (2) / 62 (30) |
| onset_offset:-50 | 0 (0) / 1 (0) | 0 (0) / 9 (0) | 0 (0) / 1 (0) | 4 (2) / 2 (0) |
| onset_offset:+50 | 0 (0) / 1 (0) | 0 (0) / 9 (0) | 0 (0) / 1 (0) | 5 (3) / 2 (0) |
| onset_offset:+100 | 0 (0) / 0 (0) | 0 (0) / 4 (0) | 0 (0) / 0 (0) | 4 (2) / 4 (2) |
| onset_offset:+150 | 0 (0) / 0 (0) | 1 (1) / 0 (0) | 6 (4) / 0 (0) | 13 (6) / 11 (7) |
| band_lo:300 | 0 (0) / 1 (0) | 0 (0) / 13 (0) | 0 (0) / 0 (0) | 4 (2) / 4 (1) |
| band_lo:1100 | 0 (0) / 1 (0) | 0 (0) / 9 (0) | 0 (0) / 1 (0) | 6 (4) / 2 (0) |
| band_lo:2000 | 0 (0) / 1 (0) | 0 (0) / 6 (0) | 0 (0) / 2 (0) | 9 (6) / 4 (2) |

`tables.md` has the rest:
- **The other onset offsets:** -25 and +25 ms are the same as the baseline row.
- **The wrong-read rates by |truth| band** (0-30, 30-60 and 60-75 deg).
- **The cleaned score for every cell:** kept %, mean, median and within 10 deg.

**Under the scoring rule:**
- **Baseline:** every placement keeps 98-100% of reads.
  - GccPhat: median 0.1-0.5 deg.
  - Angle2: median 0.9-2.3 deg.
- **Angle2 under the coherent causes, cleaned:** it keeps 32-86% of reads at -20 dB, against 87-100% for GccPhat. On
  what it keeps, its mean is 4-11 deg. The rule drops the locked reads, but the onsets it keeps are still worse.
- **Angle2 at 69 mm, baseline:** 9% of reads are off by more than 10 deg. They're concentrated at |truth| 60-75 (20%
  wrong there, against 3% at 0-30), where one sample of delay spans many degrees on a short pair. Their kinds are other
  and endfire, not aliasing.

### Who falls first
The mildest level at which the share of reads off by more than 10 deg rises 5 points over that scheme's baseline at
that placement (GccPhat / Angle2; "-" means never within the levels run):

| cause | free157 | free69 | room000000 | room011111 |
|---|---|---|---|---|
| steady_pink | -10 / -30 | -20 / -30 | -20 / -30 | -20 / -30 |
| steady_voice | -10 / -30 | -10 / -30 | -10 / -30 | -10 / -30 |
| common_mode | -10 / -30 | -20 / -30 | -20 / -30 | -30 / -30 |
| diffuse | - / -10 | 0 / -10 | 0 / -20 | 0 / -30 |
| quiet (SNR, dB) | - / 10 | - / 20 | 5 / 20 | 10 / 30 |
| onset late | - / - | - / - | +150 / - | +150 / +150 |
| onset early | - / - | - / - | - / - | - / - |
| band low edge | - / - | - / - | - / - | 2000 / - |
| no pause, silent pause | - | - | - | - |
| no pause + steady_pink | -20 | -20 | -20 | -30 |
| no pause + steady_voice | -10 | -10 | -10 | -10 |
| no pause + common_mode | -20 | -20 | -30 | -30 |

**Angle2 falls first in every coherent cause, and at the mildest level run.** GccPhat is never first. In the
reflective room, common-mode reaches GccPhat at -30 dB too.

### Cause 6: what the pause weighting is worth
GccPhat's reads off by more than 10 deg, %, with the weighting -> without it (more in `tables.md`):

| cause | free157 | free69 | room000000 | room011111 |
|---|---|---|---|---|
| steady_pink:-20 | 2 -> 9 | 7 -> 16 | 6 -> 30 | 14 -> 27 |
| steady_pink:-10 | 11 -> 50 | 26 -> 54 | 39 -> 74 | 41 -> 77 |
| common_mode:-20 | 1 -> 7 | 5 -> 17 | 5 -> 52 | 27 -> 70 |
| common_mode:-10 | 8 -> 46 | 28 -> 55 | 34 -> 84 | 54 -> 84 |
| steady_voice:-10 | 10 -> 11 | 13 -> 14 | 12 -> 15 | 15 -> 15 |
| diffuse:0 | 2 -> 4 | 22 -> 32 | 14 -> 33 | 22 -> 44 |

With a silent pause the weighting changes nothing: `no_pause` on the baseline cuts is identical, since every weight is
about 1.

## 2. The mechanisms, traced

### Angle2 and a steady source (causes 1 and 2)
Three of Angle2's rules combine here:
- **The gate:** a window counts once it is 10 dB over the quietest millisecond of the pause.
- **The edge tests:** an edge window rises 3 dB and holds 0.6 of the votes.
- **The precedence rule:** the first direction to collect two edge hits wins.

A steady coherent source breaks all three:
- **Pink noise, talker at -75, noise at +40, -30 dB** (`free157/steady_pink:-30/-75/1`). Windows, as ms from the onset
  / deg, with `*` marking an edge window:

      -10/39* -9/40* -8/40* -7/-73* -6/-75* -5/37 -4/38* ...

  The voice's 10 ms fade-in raises the level, so the window passes the rise test. But in the 1.1-8 kHz band the window's
  delay peak is still the noise's, and a single directional noise holds most of the votes, so it passes the clean test
  too. The noise collects its two edge hits one window before the talker's -73 and -75. The onset is published at +40,
  with `edge: true`.
- **Second voice** (`free157/steady_voice:-30/-75/0`). The interfering talker starts a word 48 ms before the true onset,
  inside the 100 ms that `readUtterance` looks back. That's a genuinely new, rising, clean sound, and it wins. Of
  Angle2's wrong onsets with a second voice at -30 dB, 91-98% begin before the handed onset (median -67 to -88 ms, by
  placement).
- **Common-mode:** the same race as pink noise, but the noise's direction is 0 deg.

Angle2 has no pause weighting, and its "new sound" test can't tell new energy from new direction. So a coherent
source 30 dB down still wins the race in about 1 cut in 4.

### GccPhat and a steady source
GccPhat sums half a second. Its pause weights silence the slices the pause already held, so a steady source loses
its votes, until it is loud enough to own slices where the voice is weak. From -10 dB it wins the scan (pause
direction = other source on 94% of its wrong reads). A second voice isn't steady in spectrum, so the weights can't
remove it. GccPhat survives it to -20 dB by summing alone.

### The 0 deg pull
The `zero_pull` kind (|read| < 6 while |truth| > 15) appears on:
- **common-mode:** 76-90% of GccPhat's wrong reads and 85-90% of Angle2's;
- **diffuse:** 0-5%;
- **quiet:** 0-6%;
- **everything else:** never, except Angle2's onsets 150 ms late in the reflective room.

A signal identical in both channels makes the 0 deg pull. Diffuse noise doesn't, even at 0 dB. That's the same answer
`results/zero_deg/report.md` gave on STARSS23 pauses, now from the other side.

### Diffuse noise and a quiet voice
- **What they do:** no lock to any direction. Peaks widen; GccPhat's angle-1 width grows from 12.5 to 37-40 deg at
  -10 dB diffuse or 10 dB SNR.
- **Angle2:** loses its clean edges (100% -> 63-68%), and its onset comes later (+27 to +33 ms).
- **Kinds:** its wrong reads are mostly `other` and `truth_in_2_3`, scattered rather than drawn to one place.

### Aliasing (cause 4)
- **With no noise:** no talker angle produced a read off by more than 10 deg in free field, for GccPhat at either
  spacing.
- **Angle2's misses** are mostly at 69 mm, concentrated at |truth| 60-75, and are endfire or other. None of them is an
  aliasing partner (the read's delay error matching one period of a band frequency where the voice is strong).
- **The aliasing kind elsewhere is coincidence.** It shows up only under steady sources, where the interferer's
  direction happens to sit a period away.
- **The band edge:** moving it to 1100 or 2000 Hz changes nothing in free field. In the reflective room it hurts
  GccPhat (3.5 -> 5.9 -> 8.6%), which argues for keeping 300 Hz.

### Onset off by -50 to +150 ms (cause 5)
- **Early (-50 ms):** GccPhat's first draw reads the pause, 43 deg from its lock at the median, then recovers by the
  lock.
- **Late (+25 to +100 ms):** fine.
- **+150 ms in the rooms:** 6-13% wrong. The handed "pause" then holds the word's start, so the pause weights remove the
  talker's own slices. The pause read points at the talker (100% of cuts from +50 ms).

## 3. Fingerprints: what each cause leaves in the clues
These are the values as recorded, not changes: the median over placements of each placement's median or rate.
`tables.md` also gives each clue's change against the same cut at baseline, and the clues on right vs wrong reads.

| cause | pause share | pause at the other source % | pause at 0 % | pause at the talker % | GccPhat width deg | votes | first draw vs lock deg | Angle2 edge % | Angle2 first ms | agree within 5 % | SNR 300-1100 dB |
|---|---|---|---|---|---|---|---|---|---|---|---|
| baseline | 0.10 | 0 | 9 | 11 | 12.6 | 323 | 0 | 100 | -5 | 87 | 41 |
| steady_pink:-20 | 0.92 | 100 | 0 | 13 | 17.5 | 216 | 1.1 | 99 | +10 | 54 | 23 |
| steady_voice:-20 | 0.86 | 94 | 0 | 13 | 13.2 | 310 | 0.5 | 100 | -29 | 51 | 20 |
| common_mode:-20 | 1.00 | 0 | 100 | 16 | 19.7 | 206 | 1.1 | 100 | +9 | 48 | 25 |
| diffuse:-10 | 0.19 | 0 | 0.5 | 12 | 37.4 | 131 | 2.5 | 68 | +27 | 52 | 16 |
| quiet:10 | 0.11 | 0 | 9 | 12 | 40.3 | 122 | 3.3 | 63 | +33 | 43 | 21 |
| onset_offset:+50 | 0.76 | 0 | 10 | 100 | 11.9 | 210 | 0.3 | 100 | -5 | 87 | 10 |
| onset_offset:-50 | 0.11 | 0 | 11 | 10 | 12.7 | 320 | 42.7 | 100 | -5 | 87 | 61 |
| band_lo:2000 | 0.12 | 0 | 9 | 11 | 10.8 | 250 | 0 | 100 | 0 | 88 | 41 |

**How to tell them apart:**
- **Steady directional source:** a directional pause read (share about 0.9) pointing at it. The wrong read sits on the
  pause direction.
  - A second voice also makes Angle2's onset start well before the handed onset.
- **Common-mode:** a pause read of share 1.0 at 0 deg, and wrong reads at 0.
- **Diffuse noise:** a weak pause read (share 0.19, never at 0). Wide peaks, fewer votes, few Angle2 edges, late onsets.
- **Quiet voice:** the same as diffuse, but the pause read is as weak as baseline's (0.11).
  - Diffuse and quiet are told apart only by the pause share, and only weakly. They also behave alike.
- **Late onset:** a strong pause read pointing at the talker itself, and fewer votes.
- **Early onset:** the first draw far from the lock.

**What does *not* separate wrong from right reads under these causes:**
- **Agreement between the schemes.** Under a steady source or common-mode from -20 dB, 47-96% of GccPhat's wrong reads
  agree with Angle2 to within 5 deg, because both lock onto the same wrong direction.
- **Angle2's `edge` flag.** Its wrong onsets from coherent sources are edge onsets on 90-100% of reads.

**A first cut at commit-or-dim, for brief 11 to test on real rooms.** "Dim a read that sits within 10 deg of a pause
read whose share is 0.5 or more" catches 83% of GccPhat's wrong reads and 74% of Angle2's, over all the lab's added-sound
causes. It also dims 10% and 13% of their right reads: those are talkers near the other source, or near 0 under
common-mode. That's lab data, where the steady sources are the main failure. It needs 9's and 10's real reads before it
means anything.

## Answers, briefly
- **Steady directional source:**
  - Locks Angle2 from -30 dB.
  - Locks GccPhat from -20/-10 dB; the pause weighting buys GccPhat about 10 dB against pink noise.
  - Fingerprint: a directional pause read at the source.
- **Common-mode:**
  - The 0 deg pull. Angle2 from -30 dB. GccPhat from -10 dB at 157 mm in free field, -20 dB at 69 mm and in the
    absorbing room, and -30 dB in the reflective room.
  - Fingerprint: a pause read of share 1.0 at 0 deg.
- **Diffuse noise:**
  - Scatter, not a lock. GccPhat holds through 0 dB at 157 mm in free field and falls only at 0 dB elsewhere. Angle2
    slips from -30 to -10 dB, depending on the placement.
  - Fingerprint: wide peaks, few edges, a weak pause read not at 0.
- **Aliasing:** none in free field. Raising the band's low edge only hurts, in the reflective room.
- **Onset error:** harmless from -50 to +100 ms. At +150 ms in rooms it hurts both, through the pause weights.
- **No pause history:** irrelevant with a silent pause. It is GccPhat's main defence against steady sources and
  common-mode, and does nothing against a second voice.
- **Quiet voice:** GccPhat holds to 5-10 dB SNR; Angle2 slips from 20-30 dB SNR in the rooms.

## For brief 11
- **The record format:**
  - `classes` is a dict by scheme, `{"gcc": [...], "a2": [...]}`, not one list: each record holds both schemes' reads.
  - `over36` is added to a scheme's list when its read is off by more than 36 deg.
  - Extra fields: `alias` (the aliasing frequency and voice ratio per scheme), `pause_share`, `placement`, `clean`,
    `combo`.
  - `cause` holds the setting, e.g. `steady_pink:-20` or `no_pause+common_mode:-10`.
  - The `truth` fields follow the spec; `dist_m` and `facing_deg` are null here.
- **`gcc.votes`:** the vote total after pause weighting, at the lock. It is GccPhat's own weights, mirrored in
  `records.py` because the stream doesn't expose them. Rebuilding the weighted scan in numpy reproduced GccPhat's lock
  angle and share exactly on every cut checked (29 of 29).
- **`gcc.track`:**
  - `"43"`: the first draw, which comes at 53 ms, two frames in.
  - `"100"`, `"250"`: the read standing at 100 and 250 ms after the read start.
  - `lock`: the read at the lock.
- **`pause_deg`, `pause_share`:** GccPhat's unweighted read of the 0.5 s ending at the onset handed over.

## Caveats
- **The placements are a model.**
  - Free field has no body.
  - The rooms re-time only the direct path. The reflections keep the measured source's directions whatever the talker
    angle, so their angles relative to the talker are not those of a real talker at that angle.
- **Diffuse noise is the ideal sinc model,** in the rooms too, not the rooms' own late-field coherence.
- **One interferer angle (+40 deg).** A talker at -40 deg has its mirror on the interferer, so "mirror" and "other
  source" overlap there. Both are counted, as the spec asks.
- **Twelve onsets per angle from four speakers.** That's enough for rates, not for speaker effects.
- **Facing:** there is no facing truth here, so that class never fires.

## Files
- **`results/batchA/lab/`:**
  - `reads.jsonl.gz`: every record;
  - `truth.jsonl.gz`: every cut, no audio;
  - `summary.json`: rates, cleaned scores, fingerprints, clues on right vs wrong reads, absolute clues, who falls first,
    kinds, the aliasing map;
  - `tables.md`: every table;
  - `catalogue.jsonl.gz`: every wrong read with its kinds and its EARS clip and time, to listen to.
- **`harness/batchA_lab/`:**
  - `lab_cut.py`: placements and causes;
  - `run_lab.mjs`: the runner;
  - `records.py`: clues, classes, records;
  - `variants.py` and `variants/`: the band copies;
  - `run_all.py`: everything;
  - `analyze.py`: the tables.
- **To re-make it all:**
  - Get the data: `python3 harness/dechorate/ears_fetch.py EARS --speakers p002 p003 p004 p007 p001 p005`, then move
    p001 and p005 into their own folder. Download `dechorate_rir_processed.hdf5` from https://zenodo.org/records/5562386.
  - Run `python3 harness/batchA_lab/run_all.py EARS EARS_INTERF RIRS WORK OUT`, then `analyze.py OUT/reads.jsonl.gz OUT`.
  - It takes about 70 minutes on 4 cores.
