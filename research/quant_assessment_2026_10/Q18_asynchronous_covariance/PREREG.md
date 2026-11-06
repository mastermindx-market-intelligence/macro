# Q18 — Asynchronous-session covariance and lead/lag measurement qualification: PREREGISTRATION

Status: frozen before any holdout outcome was computed. The sha256 of this file is
recorded in `FREEZE.log`; `evaluate.py` refuses to run if it changes. Later changes go
only into `PREREG_AMENDMENT.md`.

Author: Claude Opus 5.5 (model ID `claude-opus-5-5`), Q18 author seat, workflow harness commission.
Reference module: `engine/async_session_covariance.py` (research only, nothing wired).

## 1. Question and estimand

Daily closes on different exchange clocks cover different 24-hour windows. The SSE
closes at 15:00 Asia/Shanghai (07:00 UTC), HKEX at 16:00 Asia/Hong_Kong (index close
about 16:10, 08:10 UTC) and NYSE at 16:00 America/New_York (20:00 UTC in EDT, 21:00 UTC
in EST). An Asia return dated t covers (Asia close t-1, Asia close t]. It overlaps the
US return dated t-1 (which contains the whole US session t-1) and the US return dated t
(US overnight, which contains the Asia session t). It does not overlap the US return
dated t+1. Joining on the date label pairs only the second overlap, so the measured
correlation is attenuated.

**Estimand.** The per-quarter 24-hour-window (integrated) correlation between an Asia-close
equity index exposure and the US equity market (SPY), as it would be measured on a
common clock.

**Measurement target (observable proxy for the estimand).** The same index exposure observed
on the US clock: a US-listed ETF on the same or a closely matched index, priced at the
US close. T_b = the realized (uncentered) correlation of proxy P and SPY daily log returns
within quarter b, joined on the US date label (both series are on the NYSE clock, so the
join is synchronous).

**Unit.** A (pair, US calendar quarter) block. A return belongs to the quarter of its end
date label. Because every close falls on its own label date in UTC (07:00 / 08:10 / 20:00
or 21:00 UTC), this equals the quarter of the end UTC instant.

## 2. Clocks

* Input clock: daily session closes. Each series is declared with an IANA zone and a
  local close: SSE `Asia/Shanghai 15:00`, HKEX index `Asia/Hong_Kong 16:10`, NYSE
  `America/New_York 16:00`. Mapping to UTC uses pandas/zoneinfo with DST and is
  flagged per interval (`dst_shift`).
* US early closes (13:00 ET) are not modelled. With daily closes they change no overlap
  pair: the Asia closes (07:00 / 08:10 UTC) stay outside the 17:00–21:00 UTC US close
  band, so the HY pair structure is unchanged. This is a declared limitation, not a
  data repair.
* Output clock: one value per (pair, quarter) block.

## 3. Cohort (pairs), fixed

| Pair | Asia series A (clock) | US-clock proxy P | Proxy match |
|---|---|---|---|
| PAIR_CSI300 | `china/510300.SS` CSI 300 ETF (SSE) | `yahoo/ASHR` (CSI 300) | same index |
| PAIR_HSCEI | `hk/_HSCE` Hang Seng China Enterprises (HKEX index) | `yahoo/FXI` (FTSE China 50) | close but not identical basket |

US anchor S: `yahoo/SPY`. Adjusted `close` is used for SPY, ASHR and FXI, and `close`
for 510300.SS and _HSCE. Nothing else enters the trial family. Holiday rows are absent
(not forward-filled) in the Asia series; this was checked on training rows only.

## 4. Source vintages (macro-main `data/`, read-only, vintage cdab6268)

| File | sha256 |
|---|---|
| data/china/510300.SS.parquet | 604ad25485220ea33728fdbf42cd1f807a5f950117418e6f56a36429170a7579 |
| data/yahoo/ASHR.parquet | fa33964262ceb6e9c6bc9b96aff323deaeba595b40560ce8b0858d933d86d639 |
| data/hk/_HSCE.parquet | 4a77aeb03b2a21612e2a6f773b2b75648c3a34f6bff98216fa9e47d7288cdde7 |
| data/yahoo/FXI.parquet | 041b038b12a8db06534b713ca3511c03bb15872cb87a8ecfdd1959905ce934e5 |
| data/yahoo/SPY.parquet | 6c785d556c22e20f85f89f55597b10469f0fc4c40a577b8efb04bc11964a3152 |

`evaluate.py` recomputes these hashes and stops with INSUFFICIENT_DATA if a file is
missing. It stops with an error if a hash differs from this table.

## 5. Estimators (declared; no lag or window search on outcomes)

All are applied to (A, S) log returns within the block. All correlations are realized
(uncentered).

* **E0 — naive same-label (incumbent baseline).** Inner join on the date label, then
  correlation. This is the complete-case convention of
  `engine/neuralweb/covariance_spine.py::_build_factors_block`, reproduced in `RUNS.log`.
* **E1 — fixed lag-1 (incumbent convention).** Each A return dated t is paired with the
  last S return dated strictly before t. This is the `.shift(1)` overnight-transmission
  convention of `engine/hk_global_beta.py` and `engine/cn_global_beta.py`.
* **E2 — Hayashi–Yoshida on declared close timestamps (primary challenger).** The sum of
  rA_i·rS_j over intervals with positive overlap, normalised by realized variances over
  the participating intervals. It needs at least 40 overlap pairs.
* **E3 — weekly bucket sums (descriptive only).** Log returns are summed by ISO week of
  the label date, and the weeks are correlated.

## 6. Preprocessing (all fitted on TRAINING rows only)

* Log close-to-close returns on each series' own calendar. Invalid prices are bridged,
  never zero-filled. A measured zero return is kept.
* Per-series winsorisation of interval log returns at that series' training-period
  (label date < 2020-01-01) 0.1% and 99.9% quantiles. The same bounds are applied to
  holdout returns.
* There are no other hyperparameters. The eligibility minimums below are fixed here.

## 7. Chronological split, outcome windows, eligibility

* Training: label dates < 2020-01-01. It is used only for winsorisation bounds and
  descriptive in-sample block statistics, which are reported and never used to choose
  anything.
* Holdout: US calendar quarters 2020Q1 to 2026Q3 inclusive (27 quarters). 2026Q4 is
  incomplete at the data vintage and is excluded.
* A (pair, quarter) block is eligible if it has at least 40 matched P–S days (target), at
  least 40 matched A–S label days (E0), at least 40 lag pairs (E1) and at least 40 HY
  pairs (E2), with every state `MEASURED`. Ineligible blocks are dropped and reported
  as attrition with their reason.
* Pre-freeze exposure, disclosed: holdout rows were touched only as file metadata (shape,
  first/last index, the first two rows). No holdout return, correlation or estimator
  value was computed before the freeze. The baseline reproduction (`baseline_repro.py`)
  read training rows only (< 2020-01-01).

## 8. Hypotheses and practical effect bar

Per eligible block: d0 = |E0 − T| − |E2 − T| and d1 = |E1 − T| − |E2 − T|.

* **H1 (primary).** mean(d0) over all eligible holdout pair-blocks ≥ **0.05**, AND the
  95% moving-block-bootstrap CI lower bound of mean(d0) > 0, AND the per-pair mean
  d0 > 0 for both pairs.
* **H2 (secondary, incumbent lag convention).** The point estimate of mean(d1) ≥ 0. Its
  bootstrap CI is reported.
* E3 and the training-period block statistics are descriptive only.

Practical bar rationale (decided before the holdout and calibrated on synthetic data
only). A quarter has about 60 daily returns, so the sampling SE of a correlation is
about 0.1. A 0.05 mean reduction in absolute correlation error is half a quarterly SE
and is material for any covariance input. A synthetic check (rho 0.3–0.6, 62-day blocks,
closes at 0.29/0.83 of the day) gave expected d0 of 0.06–0.22. Under a pure
attenuation mechanism, the bar is therefore reachable but not guaranteed.

## 9. Trial family

One primary trial: E2 vs E0 on the two pairs above, quarterly, against the proxy target.
H2 is one secondary comparison. There are no other estimators, pairs, block lengths,
lags or bars, and no repeated holdout search. No prior HY or nonsynchronous trial exists
in the repository (collision grep in §12).

## 10. Dependence-aware uncertainty and honest N

* Moving-block bootstrap over holdout TIME blocks (quarters): block length 4 quarters,
  B = 5000, seed 18, 95% percentile CI. Both pairs of a quarter are resampled jointly.
* Newey–West (Bartlett, lag 3) SE of the per-quarter cross-pair mean of d0 is a
  cross-check.
* Honest N is the number of distinct eligible holdout quarters, with pair-blocks
  reported separately. Daily rows are never N.

## 11. Verdict rules, falsifier and stop rule

* **INSUFFICIENT_DATA** if a required input file is missing, if fewer than 16 holdout
  quarters have at least one eligible pair-block, or if either pair has fewer than 12
  eligible holdout blocks. The missing input is named.
* **KEEP** if and only if H1 holds and H2 holds.
* **REJECT** otherwise.
* Falsifier: H1 failing (mean d0 < 0.05, or CI lower bound ≤ 0, or a pair with mean
  d0 ≤ 0) falsifies the claim that the HY interval-qualified estimator materially
  improves on the naive same-label incumbent for these asynchronous pairs. H2 failing
  means the HY estimator does not beat the existing fixed lag-1 convention, and that
  also yields REJECT.
* Stop rule: the holdout is evaluated once. A rerun is permitted only to fix a
  demonstrable code bug. It is logged in RUNS.log and explained in PREREG_AMENDMENT.md
  before rerunning, and it never changes pairs, estimators, blocks, bars or eligibility.
* A synthetic witness with known truth runs inside `evaluate.py` and is outside the
  trial family.

## 12. Non-duplication (incumbent refresh and collision check)

The `_base` snapshot at d252f919 was searched for `hayashi`, `yoshida`, `refresh.time`,
`nonsynchronous`, `asynchronous` and `epps` in `engine/` and `scripts/`. The only hits
were unrelated "refresh timestamp" strings (`live_quotes.py`, `build_context_candidates.py`).
`engine/async_session_covariance.py` is absent from `_base/engine`.

Incumbents and the narrow relation:

* `engine/neuralweb/covariance_spine.py::_build_factors_block`: complete-case Pearson on
  a date-label join, trailing at most 252 rows. This is E0 here. It is reproduced, not
  modified.
* `engine/hk_global_beta.py` and `engine/cn_global_beta.py`: rolling beta to the S&P 500
  lagged one day ("overnight US->Asia transmission"). This is E1 here. Not modified, not
  re-implemented as a beta product.
* `engine/hk_adr_bridge.py`: ADR overnight display mapping. A different object (a price
  bridge, not a covariance). Untouched.
* `engine/contagion.py`: Diebold–Yilmaz spillover on US-listed (synchronous) country
  ETFs, frozen. A different estimand. Untouched.
* `engine/btc_correlation_regime.py`, `engine/rotation_corr.py`, `engine/cross_asset.py`:
  rolling correlation displays. Not duplicated; no display work here.
* `engine/session_anchor.py`: absolute session-calendar bucketing. Not duplicated; this
  module only declares close clocks for interval mapping.
* EXCLUSIONS: crossasset unknown-data display (#8664). No copy or gauge changes. Q18
  only qualifies the numerical interval measurement. Dependency order is Q18 → Q08
  (estimation/shrinkage, PSD repair) → Q17. Q18 reports PSD and never repairs it; Q08 is
  not yet available, which is a limitation.

DNR boundaries respected: DNR:KILL-OUTCOME-AUDITION (no lag/estimator chosen on
outcomes), DNR:KILL-FUSED-COMPOSITE and DNR:KILL-REGIME-SCORECARD (no composite or
score), DNR:KILL-CAUSAL-DAG-ALPHA (lead/lag here is measurement timing, not causal
alpha), DNR:KILL-LLM-ORIGINATION (no language model originates any number).

## 13. Attrition and support reporting

Per pair, the following are reported: rows in, invalid prices, zero-return days (kept
as measured), holiday-gap intervals, bridged intervals, the DST-shift share of US
intervals, eligible and dropped blocks with reasons, and matched-day counts per block.
