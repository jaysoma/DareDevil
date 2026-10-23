# Results by corpus (2026-10-23)

What's measured so far, grouped by dataset, with the report that explains each finding and the file that holds its
numbers. Built for one dashboard per corpus. Numbers here are headlines; the reports carry the caveats.

## STARSS23: Tampere University and Sony, 16 real rooms, labelled sounds with direction and distance
4-capsule array on a rigid sphere (pairs about 69 mm apart), 24 kHz, 100 ms labels.

| finding | headline | report | data |
|---|---|---|---|
| The sphere bends sound | GCC-PHAT reads wide (+5 deg at 30-45, +19 at 45-60); the rigid sphere alone reproduces it within about 1 deg | `starss23/report.md` s2 | `starss23/analysis*.json`, `starss23/lean_compare_12_34.json` |
| Angle2's inward pull, fixed | median error 15.0 -> 10.8 deg; clean onsets (72%) read 8.6 deg beside GCC-PHAT's 9.2 | `angle2_pull.md` | `starss23/after_angle2_fix/compare.json` |
| Score under Jay's rule | single talker: 90.1% kept, 7.6 deg median, 60% within 10 deg; all speech against the sphere: 82.3%, 6.4 deg, 65% | `clean/report.md`, `batchA/starss23/report.md` | `clean/summary.json`, `batchA/starss23/summary.json` |
| Why reads lock wrong | 54% of wrong speech reads sit on another sound that was there (2.5x chance); by cause: scatter 44%, another source during the read 21%, a steady source in the pause 18% | `batchA/starss23/report.md`, `batchA/report.md` s1 | `batchA/summary.json` |
| When to dim | commit when GCC-PHAT's top two peaks differ by >= 0.2 and it isn't on a directional pause read: 64% within 10 deg at 55% committed (52.5% for all reads) | `batchA/report.md` s3 | `batchA/summary.json`, `batchA/commit_curves.png` |
| Range | the direction-free CDR orders 72% of pairs twice as far apart; the first 5 ms of level and a cepstral echo lag are near chance | `batchA/report.md` s4 | `batchA/starss23/range_summary.json` |
| Pauses | no pull to 0 deg: 10.5% of peaks within 6 deg of 0, against 9.5% for no coherence | `zero_deg/report.md` | `zero_deg/pause_gcc.json` |
| DeepFilterNet3 | needs a fixed input gain (lsnr opens on 48% of speech onsets as recorded, 90% with it); opens on half of knocks and doors; the mask isn't a speech track; the shared operator keeps the bearing | `stage2_dfn/report.md` | `stage2_dfn/summary.json` |
| Mask View | two recordings through DFN3 against every labelled sound | `../dfn/README.md` | `../dfn/maskview/starss23-*.json` |
| Held-out exam | not possible: the evaluation set ships without labels | `batchA/report.md` s5 | |

## LOCATA: Humboldt University lab, real talkers walking, tracked head position and facing
Talkers read VCTK sentences aloud while walking (tasks 3 and 4). DICIT pairs at 160 mm (the phone's 157) and 80 mm.

| finding | headline | report | data |
|---|---|---|---|
| Score under Jay's rule | 160 mm: GCC-PHAT 87.7% kept, 5.2 deg median, 83% within 10 deg | `batchA/locata/report.md` | `batchA/locata/locata_160mm_summary.json` |
| Facing decides trust | alone and facing the array: 0 of 52 reads off by more than 10 deg; alone and facing away: 62% (n = 16) | `batchA/locata/report.md` s1 | `batchA/locata/summary.json`, `batchA/locata/tables.md` |
| Why reads lock wrong | the other talker speaking just before: 38% of wrong reads, 53% of outliers | `batchA/report.md` s1 | `batchA/summary.json` |
| Each sound at its own onset | Angle2 64% -> 73% within 10 deg, outliers 18% -> 13% | `batchA/report.md` s2 | `batchA/moved.jsonl.gz` |
| When to dim | the same rule, untouched: 85% within 10 deg at 51% committed (73% for all) | `batchA/report.md` s3 | `batchA/summary.json` |
| Range | CDR orders 85% of pairs twice as far apart; the true floor-echo delay would order all of them, but no reader finds it yet | `batchA/report.md` s4, `first_reflection/report.md` s2 | `batchA/locata/range_summary.json`, `first_reflection/locata_summary.json` |
| DeepFilterNet3 | the shared operator keeps GCC-PHAT within 1 deg of the raw pair on 91% of reads | `stage2_dfn/report.md` s5 | `stage2_dfn/summary.json` |
| Pending | brief 20 (range from the opener, turned heads, facing ladder), brief 21 (when to re-read) | | |

## dEchorate: Bar-Ilan lab, loudspeakers, 11 wall settings, labelled echoes
| finding | headline | report | data |
|---|---|---|---|
| Score under Jay's rule | 155 mm: GCC-PHAT 95.7% kept, 1.2 deg median, 92% within 10 deg | `clean/report.md`, `dechorate/report.md` | `clean/summary.json` |
| How it fails | echo capture is GCC-PHAT's main failure; a loudspeaker facing a wall loses whole setups | `dechorate/report.md`, `clean/report.md` | `clean/dechorate_measured_outliers.jsonl` |
| First reflection | both schemes' reflection reads are at chance, in angle and lag together; a horizontal pair can't place a ceiling | `dechorate/report.md` s3, `first_reflection/report.md` s1 | `first_reflection/dechorate_summary.json` |

## The mechanism lab: real speech (EARS), one cause added at a time
Placements are synthetic (exact delays, or dEchorate's measured rooms). Not a corpus, but its own page.

| finding | headline | report | data |
|---|---|---|---|
| Who falls first | Angle2 locks onto a steady sound 30 dB under the voice; GCC-PHAT holds to -20/-10 dB | `batchA/lab/report.md` s1 | `batchA/lab/summary.json` |
| The pause weighting | worth about 10 dB to GCC-PHAT against steady sources; nothing against a second voice | `batchA/lab/report.md` s1 | same |
| The 0 deg pull | made only by a signal identical in both channels; diffuse noise doesn't | `batchA/lab/report.md` s2 | same |
| Fingerprints | each cause leaves a recognisable trace in the clues (90-98% attributed back) | `batchA/lab/report.md` s3, `batchA/report.md` s1 | same |

## Jay's phone tapes: Galaxy Z Flip4, house walks
| finding | headline | report | data |
|---|---|---|---|
| The 0 deg in pauses | 44% of tracked pause directions within 6 deg of 0; rises with frame strength (13% -> 30%); ODAS reports exactly 0.0 because of its scan's first point | `zero_deg/report.md` | `zero_deg/odas_tapes_excluded.json` |
| Mask View | walk-205043 through DFN3 | `../dfn/README.md` | `../dfn/maskview/walk-205043.json` |
| Ground truth | 7 tier-A stops over 29 tapes: too few for a scored page yet | `truth/summary.md` | `truth/*.json` |

## Who are the words for: AMI meetings and the spliced device set
A separate thread from the corpora above. `addressee_findings.md` collects it for the Tampere note.

| finding | headline | report | data |
|---|---|---|---|
| Recogniser words | 95.8% of words are followed by the same speaker's (overlaps resolved as a recogniser would) | `linguistic/ami/report.md` s1 | `linguistic/ami/transcripts_summary.json` |
| Words against facing (AMI) | words 60.2%, facing 56.7%, both 64.4% (always "the group" 57.9%); facing adds about 10 points to naming which person | `linguistic/ami/report.md` s3 | `linguistic/ami/addressee.json` |
| Instructions in a stream | Jay's shape-and-contrast finds 89% at 1 false accept per hour (keywords 9%); the same request said to a person passes 83% | `device_directed/report.md` | `device_directed/summary.json`, `device_directed/curves.png` |
| Pending | brief 22 (real requests to people in context), brief 19's small general model | | |
