# Bearing accuracy under Jay's scoring rule (2026-10-22)

## The rule
Jay: score the working machinery, and set the outliers aside to study rather than let them weigh down the score.
Deviation in percent is read against the 90 deg half-plane, so 1% = 0.9 deg.

1. **Scope:** only |truth| <= 75 deg is analysed.
2. **Read outlier:** a read off by more than 36 deg (40%) is set aside.
3. **Scenario dropped:** a scenario is one setup heard repeatedly. For STARSS23 that's a room through one capsule
   pair; for dEchorate, one wall configuration, source, array and spacing. After step 2, a scenario is dropped whole if
   its remaining reads average more than 22.5 deg (25%) off, or if more than half its reads were outliers.
4. **Score what's left,** always next to how much was set aside.

Each scheme is cleaned on its own. The "both kept" row scores only reads both schemes kept, for a like-for-like
comparison. `harness/scoring/clean_score.py` holds the thresholds; one constant each.

## Results

| | STARSS23 GccPhat | STARSS23 Angle2, fixed | dEchorate GccPhat | dEchorate Angle2, before fix |
|---|---|---|---|---|
| Reads in scope | 8,322 | 8,211 | 13,464 | 13,464 |
| Read outliers set aside | 805 (9.7%) | 1,167 (14.2%) | 385 (2.9%) | 1,089 (8.1%) |
| Scenarios dropped | 1 of 96 | 1 of 96 | 19 of 561 | 0 of 561 |
| Kept | 90.1% | 85.6% | 95.7% | 91.9% |
| Mean error, kept | 10.6 deg | 11.0 deg | 3.1 deg | 8.4 deg |
| Median error, kept | 7.6 deg | 8.4 deg | 1.2 deg | 5.6 deg |
| Within 10 deg, kept | 59.6% | 56.1% | 91.8% | 68.8% |
| Both kept: mean / median / within 10 | 10.0 / 7.0 / 62.5% | 10.6 / 8.1 / 57.7% | 3.0 / 1.1 / 92.1% | 8.3 / 5.6 / 69.5% |

dEchorate is scored against the RIRs' measured direct-path delay. Against the published geometry, GccPhat drops 47
scenarios. That's the 3-23% delay mismatch in that dataset's own geometry, not a failing scheme. The geometry numbers
are in `dechorate_geometry_summary.json`.

## What the rule shows
- **GccPhat still leads on both datasets,** on the like-for-like rows too. With Angle2's fix, the STARSS gap is small:
  7.0 against 8.1 deg median, and 10.0 against 10.6 deg mean.
- **The two schemes fail differently.**
  - GccPhat's failures cluster in whole scenarios. 14 of its 19 dropped dEchorate scenarios are source 5, a loudspeaker
    facing a wall: when the direct sound is weak, it loses whole setups.
  - Angle2's failures are scattered one read at a time across scenarios, so none get dropped.
- **One STARSS scenario fails for every scheme:** room 22 through pair 2-4, where more than half the reads were
  outliers. It's worth studying on its own.
- **The mean is still above the median after cleaning:** 10.6 against 7.6 deg for GccPhat on STARSS. Errors of 10-36
  deg are common, and they're inside the working machinery, not outliers.

## The outliers, by kind
`*_outliers.jsonl` catalogues every set-aside read with its scenario, truth, read, other directions and context.

| Kind | STARSS GccPhat | STARSS Angle2, fixed | dEchorate GccPhat | dEchorate Angle2 |
|---|---|---|---|---|
| Pinned at end-fire (read >= 85 deg) | 360 | 327 | 21 | 162 |
| Mirror (sign flipped) | 63 | 123 | 45 | 144 |
| On a reflective surface's echo | (no labels) | (no labels) | 158 | 117 |
| Truth was its 2nd/3rd direction | 104 | 170 | 92 | 319 |
| Other | 278 | 547 | 69 | 347 |

- **STARSS's end-fire pins** are mostly the sphere. Its lean pushes reads past what a free-field pair can produce, so
  the formula pins them at 90 deg.
- **dEchorate's echo captures** are GccPhat's main failure, as the dEchorate report found.

## Files
- **`summary.json`:** every number above, plus the lean by band on kept reads.
- **`<dataset>_scenarios.json`:** every scenario, with its outlier count and whether it was dropped, and why.
- **`<dataset>_outliers.jsonl`:** the catalogue.
- **STARSS truth without audio:** `results/starss23/truth/`, so the score re-runs from the repo alone.
