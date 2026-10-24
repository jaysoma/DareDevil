# Brief B: the blur, in time

Read `README.md` here first (rules, inputs, the bar). Folders: `harness/rotation/blur/`, `results/rotation/blur/`.

## The question
When a talker turns away, the direct high band weakens and the room's sound fills in what's left. In time, that should
show as smearing: the dips between syllables fill in, and an onset's first instants lose their high band. Do these
single-mic measures separate facing from turned at least as well as the CDR contrast, and do they move less with
distance?

## Steps
1. **Modulation depth per band.** For octave bands 250 Hz-8 kHz, take each band's envelope over a stop's speech and
   measure how deep its dips go relative to its peaks: the modulation spectrum at 2-8 Hz, the syllable rate. Do it per
   mic, and on the pair's direct part if you can.
   - **Control:** in walk-213304's held vowels (77 s), envelopes barely dip. Jay notes that vowels never dip below the
     room floor. Measure them separately and say whether this measure is usable there.
2. **Onset colour.** At each onset that rises from quiet inside a stop, compare the high-to-low band energy of the first
   30-50 ms with that of the following 300 ms. The direct sound arrives first, so turning should take more of the
   onset's high band than the tail's.
3. **The lag check, cheaply.** On the two same-phrase walks (231705, 231921: "there are six fresh beers in the fridge" at
   every facing), cross-correlate the 4-8 kHz envelope with the 250-1000 Hz envelope per phrase. Does the lag or the
   peak height change with facing? Jay doubts it; one table settles it.
4. **Score each measure the same way:** against the same spot's facing-0 stops (signed or unsigned), toward against
   turned, left out by walk. Give its distance slope from the ladder walks. Put them in one table beside the CDR
   contrast's numbers from `facing_pooled.md`.

## Report
`results/rotation/blur/report.md` and a numbers JSON. Open with whether time-domain blur beats, matches or loses to
the CDR contrast, in two sentences.
