# Lane C1 — Rotation / leadership-persistence state variable (PIT-safe)

**Data class.** The price stores are FINAL-VINTAGE (as observed today, not point-in-time) and the universes are SURVIVOR-SELECTED (current membership only). Sector ETF closes are from `data/yahoo/`, breadth and SPY from the same store, the 10y TIPS real yield from `data/fred/DFII10.parquet`, and the incumbent PIT regime store from `data/regime/regime_v2_pit.parquet`.

**ANSWER FIRST.** Lane C1 is **BROKEN** on its AR(1) lag-21 control: `corr(LP(t), LP(t-21)) = -0.0404` (PASS threshold > 0.5). The direction control PASSES (`mean_LP_fast = -0.0883` < `mean_LP_persistent = 0.0796`). Per spec §POSITIVE CONTROLS, the table is still exported and `controls.status = "BROKEN"` is recorded honestly in `result.json`. The BROKEN verdict is pre-declared (reviewer-verified on identical input vintage); this lane does not re-tune to recover the AR(1) gate.

## Summary

- Table: `rotation_state_daily.parquet` — 6,942 rows, 1999-02-25 → 2026-09-30 (first date LP is computable → last SPY session)
- Sidecar: `rotation_cuts_daily.parquet` — per-session (lo, hi) tercile cuts the pipeline used
- One-session PIT shift applied: exported row at date `t` = unshifted computation at `t-1`
- Expanding-window terciles for LP, breadth_spread, dfii_impulse (≥ 756 prior non-NaN sessions gate)
- Forward-fill of missing sector / FRED closes limited to ≤ 5 sessions
- Repo head: `052e02d085b01f29baf499357e224c836d8eb224`

## Positive controls (the gating numbers)

| Control | Value | PASS / FAIL | Threshold |
|---|---|---|---|
| AR(1) lag 21 of LP | **-0.0404** | **FAIL** | > 0.5 |
| mean LP, fast windows (F) | **-0.0883** | — | — |
| mean LP, persistent windows (P) | **0.0796** | — | — |
| Direction: `mean(F) < mean(P)` | -0.0883 < 0.0796 | **PASS** | strict < |
| mean LP, overall | -0.0168 | — | — |
| **controls.status** | **BROKEN** | — | PASS only if both pass |

### Window-level diagnostics (sessions / months / mean LP / fast-share)

| Window | Class | n_sessions | n_months | mean LP | share labelled "fast" |
|---|---|---:|---:|---:|---:|
| 2020-11-09..2020-12-31 | fast | 37 | 2 | -0.0885 | 0.3514 |
| 2021-02-01..2021-03-31 | fast | 42 | 2 | -0.0881 | 0.3333 |
| 2022-01-03..2022-06-30 | persistent | 124 | 6 | 0.1622 | 0.1774 |
| 2023-03-01..2023-06-30 | persistent | 85 | 4 | -0.0030 | 0.2706 |

### LP autocorrelation profile (description only)

| lag | corr(LP(t), LP(t-lag)) |
|---:|---:|
| 1 | +0.8274 |
| 5 | +0.4706 |
| 10 | +0.2252 |
| 21 | -0.0404 |
| 42 | -0.0699 |
| 63 | +0.0402 |

## Calibrated control (post-hoc sensitivity, added 2026-10-04 after the primary verdict was recorded)

The pre-declared > 0.5 lag-21 gate was uncalibrated. The POSITIVE control (fixed sector drift + iid per-session noise) shows that even with strong fixed sector leadership, lag-21 LP autocorrelation only reaches a median of **+0.2533** — well below 0.5. This means the gate could not have passed by construction, regardless of the real data. This sensitivity positions the OBSERVED value between two reference panels built on the observed 6,942-session index and the 11-sector availability mask.

**Disclosure (G3):** the POSITIVE control noise is iid per session, so its lag-5 / lag-10 autocorrelation is ≈ 0 by construction. The control calibrates only the lag-21 persistence level, not the lag profile.

- **OBSERVED** lag-21 LP autocorrelation: **-0.0404**
- **POSITIVE CONTROL** (200 sims, fixed sector drift with `std(drifts) == cs_std = 0.030204` + iid N(0, idio_std = 0.030158) noise per session, simulated on the observed 6,942-session index and 11-sector availability mask): median lag-21 = **+0.2533** (5th pct = +0.2366, 95th pct = +0.2711); median lag-5 = +0.0303, median lag-10 = +0.0319
- **NULL** (200 sims): NULL: per non-overlapping 21-session block of the OBSERVED r21 panel and availability mask, draw ONE permutation of the sector identities (seed 20261004) and apply that permutation to every row of the block (r21 and availability permuted jointly). Within-block persistence is preserved; cross-block persistence is destroyed. 95th-pct lag-21 = **+0.0498** (median = +0.0017, 5th pct = -0.0436); median lag-5 = +0.3269, median lag-10 = +0.0970
- **Pre-declared rule:** CALIBRATED_PASS iff observed lag-21 autocorr > null 95th percentile AND >= 0.5 * positive-control median; else CALIBRATED_FAIL.
- **Outcome:** **CALIBRATED_FAIL** (observed -0.0404 vs null p95 +0.0498; positive-control 0.5×median = +0.1267). controls.status remains BROKEN — this sensitivity does not change the primary verdict.

## Agreement with incumbent PIT regime store (rotation_tercile × flag_rotation_persistence)

Raw inner join produced **6,880** rows. After dropping rows with NaN `rotation_tercile` (burn-in before the first computable tercile), **6,124** rows remain (756 dropped). The incumbent PIT regime store ends on **2026-07-02**, so the join stops there even though our exported table runs to 2026-09-30.

| rotation_tercile | flag=True | flag=False | row total |
|---|---:|---:|---:|
| fast | 386 | 1637 | 2023 |
| mid | 398 | 1610 | 2008 |
| persistent | 383 | 1710 | 2093 |

Cohen's κ — binary input: rotation_tercile vs flag_rotation_persistence:

| Era | n | κ (persistent) | κ (fast, per masterplan §5.3) |
|---|---:|---:|---:|
| Overall | 6,124 | -0.0129 | +0.0004 |
| <=2009 | 1,975 | +0.0289 | -0.0348 |
| 2010-2019 | 2,516 | -0.0237 | -0.0226 |
| 2020-2026 | 1,633 | -0.0479 | +0.0889 |

Both binaries are reported because the masterplan §5.3 defines κ on `rotation_tercile == "fast"` while the spec wording uses `"persistent"`; the spec text governs the primary binary (`kappa_persistent`).

Agreement is near zero in every era — the incumbent `flag_rotation_persistence` is not aligned with our LP-based tercile. The two are different concepts: `flag_rotation_persistence` is a single-session flag from the regime cascade; our `rotation_tercile` is a relative-position label in an expanding window. The agreement is **reported**, not used to tune LP (per spec).

## Contingency: rotation_tercile × transition_state

| rotation_tercile | NEW_REGIME | STABLE | TRANSITIONING | WEAKENING |
|---|---|---|---|---|
| fast | 448 | 863 | 451 | 261 |
| mid | 325 | 966 | 423 | 294 |
| persistent | 291 | 1114 | 392 | 296 |

## Joined-row composition by `pit_class` × era

| Era | pit_class composition | sessions |
|---|---|---:|
| <=2009 | {'mixed': 1.0} | 1,975 |
| 2010-2019 | {'mixed': 1.0} | 2,516 |
| 2020-2026 | {'pit_vintage': 0.9541, 'mixed': 0.0459} | 1,633 |

Pre-2020 the incumbent store reports all rows as `mixed`; the `pit_vintage` class only appears from 2020 onward. The pre-2020 share is therefore not informative about agreement.

## Tercile counts (after shift, non-NaN labels only)

| Variable | label | sessions |
|---|---|---:|
| rotation | fast | 2,030 |
| rotation | mid | 2,041 |
| rotation | persistent | 2,115 |
| breadth | narrow | 2,280 |
| breadth | mid | 1,406 |
| breadth | broad | 1,428 |
| dfii | falling | 1,560 |
| dfii | mid | 1,873 |
| dfii | rising | 1,763 |

Rotation terciles are balanced (~33/33/33) as expected from expanding-window quantiles; breadth is skewed — `narrow` (2,280) sits about **+33.8%** from an even share (1705); dfii is skewed — `falling` (1,560) sits about **-9.9%** from an even share (1732).

## Honest interpretation

The directional evidence (mean LP is lower in known fast-rotation windows than in known persistent-leadership windows) is consistent with the variable measuring something real about sector leadership persistence. The persistence-at-lag-21 test fails — LP is approximately white noise at a monthly lag. Any consumer that needs a slowly-evolving state should NOT rely on raw LP at lag 21; smoothing or a different lag would be needed. The agreement with `flag_rotation_persistence` is near zero in every era, so the two are not substitutes; if downstream wants "rotation persistence" it must pick one or fuse them deliberately.

## Deviations

- LP autocorrelation profile is reported for lags 1/5/10/21/42/63 as description only. Post-R7 exact Spearman re-rank shifts the lag-10/42/63 values by ≤ 0.0003 relative to the reviewer's pre-R7 values; the 1e-4 tolerance enforced by the test suite applies to recomputation from the exported parquet, which matches exactly. The BROKEN verdict on the lag-21 gate is unchanged.
- Masterplan §5.3 defines κ on rotation_tercile == "fast" while the spec text uses rotation_tercile == "persistent". Both kappas are emitted as kappa_persistent (primary, per spec) and kappa_fast (alt, per masterplan); the spec text governs the binary.
- idio_std and cs_std agree at 4 dp (0.0302): the positive control's idiosyncratic and cross-sectional scales are not distinguishable at that precision

## Gaps

- AR(1) lag 21 control FAILED (value -0.0404 vs threshold 0.5) — see first paragraph.
- The pit_class column reports `mixed` for 100% of pre-2020 joined rows; agreement statistics for those eras are not informative.
- Cohen's κ computed by hand per the spec (po, pe); no library reference for cross-check.

## Provenance

- Host: `m2studio` (seat host m2; this round 2026-10-04)
- python3: `/opt/homebrew/opt/python@3.14/bin/python3.14` 3.14.7
- pandas 3.0.5 / numpy 2.5.2 / pyarrow 25.0.1 / scipy 1.18.0 / pytest 9.1.1
- Frozen tables this round (unchanged): `rotation_state_daily.parquet` sha256 `9361dbf08018f0c23bc6e9b29fa014bc42429ed3289d359adf7a16f52be3e2dd` ; `rotation_cuts_daily.parquet` sha256 `484492539ae42cb3055416c12f144f93f748549bf21e4cf3de2f1e1eb6a002f8`.


## Tests

Round-4 mutant/tamper power (scratch copies of `code/` or `result.json`; clean tree afterwards). Each mutant was applied on a copy and the named test FAILED; the clean suite then passed.

- include-t mutant (`compute_cuts` at `run.py:126` calling `tercile_cuts(v_arr, min(i + 1, n))`): `test_pipeline_cut_unchanged_when_v_prior_only` FAILED — `assert cl0[t0] == cl1[t0] and ch0[t0] == ch1[t0]` (`cut at t0=800 changed after v[800]=+1e6`). pytest: `1 failed`
- rescale-deleted (`positive_control_drifts` without the `drifts * (cs_std / sd)` rescale at `run.py:168-170`): `test_positive_control_drifts_std_equals_cs_std` FAILED — `assert abs(got - cs_std) < 1e-12` (`std(drifts, ddof=0)=0.01910 vs cs_std=0.030204`). pytest: `1 failed`
- calibrated_status tamper (`PASS`): `test_calibrated_control_recompute` FAILED — `assert cc["calibrated_status"] == expected_status` (`json=CALIBRATED_PASS vs recomputed=CALIBRATED_FAIL`). pytest: `1 failed`
- null p95_lag21 tamper (`-0.5`): `test_calibrated_control_recompute` FAILED — `assert abs(p95_from_draws - cc["null"]["p95_lag21"]) < 1e-4` (`p95 from draws=0.0498448 vs stored -0.5`). pytest: `1 failed`

Clean suite (counts only after orchestration):

```
18 passed, 1 skipped in 29.77s
```
