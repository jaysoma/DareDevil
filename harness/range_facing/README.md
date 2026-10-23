# harness/range_facing: brief 20

Range from the opener with the DRR law, facing from HF − LF, and the announcement as a room probe. The results are in
`results/range_facing/`.

| file | what it does |
|---|---|
| `drr.py` | the direction-free CDR per band (LF, MF, HF, ALL; floored at c/2d and `_raw` not floored) from cut audio, on stdin |
| `run_cdr.sh` | each dataset's own cutter piped through `drr.py`: dEchorate (155 mm, 11 settings), STARSS23 (pairs 1-2 and 3-4), LOCATA |
| `locata_wide.py` | LOCATA cuts on DICIT mics 3-12 (640 mm), the only pair whose LF band is readable (c/2d = 268 Hz) |
| `dechorate_rir.py` | dEchorate's own RIRs: the echo time per setting and band, and the true DRR per source and array |
| `analyze.py` | steps 1-4: the law per room, the opener, turned heads and the compensations, and the facing ladder (to `summary.json`) |
| `sim_probe.py` | step 5: the announcement in pyroomacoustics shoeboxes, with EARS talkers: the probe's r_c and echo time against the truth |
| `sim_summary.py` | step 5's tables (to `sim_summary.json`) |
| `plot.py` | `range_facing.png` |

## The run, as done

```sh
# data: dEchorate v1.0 RIRs and echo notes, EARS (as in harness/dechorate); STARSS23 (harness/starss23); LOCATA
# (harness/batchA/locata/locata_fetch.py)
sh run_cdr.sh dechorate DATA/dechorate DATA/dechorate/ears READS
sh run_cdr.sh starss DATA/starss23 READS
python3 ../batchA/locata/locata_cut.py DATA/locata CUTS && python3 locata_wide.py DATA/locata CUTS
sh run_cdr.sh locata CUTS READS            # 160, 80 and 640 mm; CUTS (audio) can go afterwards
python3 dechorate_rir.py DATA/dechorate/dechorate_rir_processed.hdf5 > READS/dechorate_rir.json
python3 analyze.py READS ../../results/range_facing/summary.json
python3 sim_probe.py DATA/dechorate/ears > READS/sim_probe.jsonl
python3 sim_summary.py READS/sim_probe.jsonl ../../results/range_facing/sim_summary.json
python3 plot.py ../../results/range_facing/summary.json ../../results/range_facing/sim_summary.json ../../results/range_facing/range_facing.png
```

`analyze.py` holds every dEchorate cut pair in memory (about 1.4 million opener pairs), so leave it 1-2 GB.
