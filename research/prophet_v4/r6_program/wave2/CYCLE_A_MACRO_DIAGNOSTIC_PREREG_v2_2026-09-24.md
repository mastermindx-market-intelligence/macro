STATUS: COMPLETE

## AMENDMENT RECORD

| Finding | What changed | Section |
|---|---|---|
| B1 | Every row used for any purpose must have an admissible publication clock, and anchors with any unavailable required month are right-censored and excluded from N; the earliest and latest possible anchors are pinned. | Window and era handling; hypotheses; primary endpoint |
| B2 | Every three-month change is now a same-vintage difference, `Δ3_v(t) = value_v(t) - value_v(t-3)`, with the t−3 row selected at the t vintage; the query no longer keeps only initial rows. | Frozen publication-clock transformation; run contract |
| B3 | Anchors are ORDER events only, every anchor remains in the H1 denominator, and H2 and H3 describe the identical anchor set without allocating or rescuing anchors. | Hypotheses; primary endpoint |
| M1 | The sole event is the ORDER downturn crossing with the frozen sequence `+,+,≤0,−,−`; the unused opposite-direction event is removed. | Hypotheses |
| M2 | Period-month offsets are explicit; H1 inventory uses `Δ3_v ≥ 0` in at least one required month, and the first qualifying ISRATIO level trough is used. | Hypotheses |
| M3 | Counted anchors are chained at 16 period months; N below 12 makes the primary endpoint NOT EVALUABLE rather than failed. | Primary endpoint |
| M4 | The registered null is 2,000 draws of availability-admissible random anchor months under the same separation rule, with seed 20260924; passage requires both the exact-binomial bound and the 95th-percentile comparison. | Primary endpoint |
| M5 | The result is DESCRIPTIVE_ONLY by construction because fewer than 50 matured anchors or N_eff below 20 is unavoidable on about 269 months with 16-month separation; N, N_eff, and the out-of-window status of the current regime are reported. | Primary endpoint; disclosures |
| M6 | The pass/fail path to return inspection is replaced by the exact no-return, no-pilot, no-public-surface, and no-B18 prohibition. | Disclosures |
| M7 | AWHMAN is excluded from availability; null values and missing same-vintage t−3 rows block only their series and month, and a required block right-censors the anchor. | Frozen publication-availability rule; window and era handling |
| M8 | The run contract pins the exact vintages blob and v2 merge SHA, reads the blob rather than the moving path, and verifies every governing record at that SHA. | Status + authority; run contract |
| m1 | The three-month availability deadline remains frozen and discloses that it was fitted to the observed maximum lags and therefore blocks nothing today. | Frozen publication-availability rule |
| m2 | The file records that v1 merged before R6-B16-01 and the D03 matrix reached main, and that the run verifies both at the recorded merge SHA. | Status + authority; run contract |
| m3 | Process narrative about authoring history is removed from this pre-registration. | Run contract |
| m4 | The earliest possible anchor period is derived and stated as 2003-02 alongside the latest possible anchor period 2024-02. | Window and era handling |

## STATUS + AUTHORITY

- Operation: `prophet-us-fable-meta-ceo-20260923-001`; lane `pu_w3_prereg_v2`; commissioner: the Fable Meta-CEO seat.
- Authority: `DEC:PROPHET-US-B16-CYCLE-INTERNAL-DIAGNOSTIC-ERA`, R6-B16-01a, R6-B16-01, R6-D03-01, and the R6-PREREG-01 seat ruling. This amendment is made under `DEC:PROPHET-US-FABLE-META-CEO-DELEGATION` after an independent cross-family Opus review rejected v1 with `RUN MAY START: NO`.
- The blockers were: B1 allowed publication clocks outside the ratified era; B2 subtracted levels from different vintages and admitted a level splice; and B3 allowed an H1-failing anchor to leave the H1 denominator while OUTPUT or INVENTORY turns consumed the separation window.
- v1 merged as `0c9e30ad4da0325b135bbf621b4498174dcc875b` before R6-B16-01 and the D03 matrix commit `89a1a5798aa4694101a87691c7871607422e9bba` were on main. The run must verify v2 and every governing record at `<v2_merge_sha>`.
- This file computes no endpoint, rate, anchor count, or return. It gives the later diagnostic run one frozen procedure and no choice among admissible interpretations.

## HYPOTHESES

### Frozen publication-clock transformation

For each period `t` and series `s ∈ {NEWORDER, ISRATIO, INDPRO}`, select the source row `value_v(t)` whose `realtime_start = v` is the first `realtime_start` for `(s, t)` and whose `realtime_start ∈ [2002-12-01, 2025-05-15]`. Select the t−3 row for the same series as the observation for period t−3 whose interval `[realtime_start, realtime_end)` contains `v`; when `realtime_end` is null, treat that interval as open-ended. The same-vintage change is exactly:

`Δ3_v(t) = value_v(t) - value_v(t-3)`

If the store cannot supply either admissible row, or either `value` is null, period `t` is blocked for that series. Do not use a later revised `value_v(t)`, a different-vintage `value_v(t−3)`, zero, interpolation, normalization, a lagged value, or a latest-revised fallback. This rule prevents a level splice: benchmark, re-reference, index-base, and NAICS-versus-SIC changes cannot enter as fake three-month changes.

- `ORDER(t) = Δ3_v(NEWORDER,t)`.
- `INVENTORY(t) = Δ3_v(ISRATIO,t)`.
- `OUTPUT(t) = Δ3_v(INDPRO,t)`.
- `HOURS(t)` is report-only and is defined only when AWHMAN supplies both same-vintage levels; it never anchors, blocks, alters eligibility, or rehabilitates a result.
- `Δ3_v` is defined for period `t` only when both period months are within the ratified target era: t−3 is never imported from 2002-09 through 2002-11.

### Frozen publication-availability rule

A required row is available only when every row used for that row's transformation has `realtime_start ∈ [2002-12-01, 2025-05-15]`, a non-null `value`, and, for t−3, an interval containing `v`. In addition, the first publication for target month `t` must be on or before the end of the third period month after `t`. The deadline remains frozen from v1 and applies to every series and every required target month before event construction.

The deadline was fitted to the maximum observed lags across all vintage rows — 86 days for NEWORDER, 116 for ISRATIO, 93 for INDPRO, and 80 for AWHMAN — so the third month-end was the first common whole-month boundary after every maximum. That fit means it blocks no source currently known to the receipts and is retained only as a frozen publication guard, not as a claim that every future source is late. AWHMAN is excluded from the availability rule because it anchors nothing. A null `value` or missing same-vintage t−3 row blocks that month for that series; if that series is required at that month for an anchor or an outcome below, the anchor is right-censored.

An ORDER downturn crossing is the sole anchor event. It is a period `t` at which the ORDER sequence, in consecutive period months, is exactly `+,+,≤0,−,−` for offsets `t−2,t−1,t,t+1,t+2`. This definition is exhaustive; no opposite-direction event, other crossing, reconstructed neighbour, or runner-selected substitute exists. All five months and the three t−3 rows behind the three transformed months must be availability-admissible.

### ISRATIO level trough

For period `u`, an ISRATIO level trough exists when the same-vintage ISRATIO levels at `u−2,u−1,u,u+1,u+2` are ordered so that the level at `u` is less than or equal to both neighbours and no earlier level in that five-month span is lower. Adjacent equal minima are one candidate whose qualifying month is the earliest minimum. For H1, use the FIRST level trough whose period month lies in `[t,t+12]`; existence of a later trough cannot replace a missing or blocked first trough. All five levels, their required t−3 rows, and every publication clock must be admissible. A level trough is never an anchor.

### H1 — Order flow leads inventory turns while output contracts

At an ORDER downturn crossing `t`, H1 holds when both conditions hold:

1. INVENTORY has `Δ3_v ≥ 0` in at least one of period months `t,t+1,t+2,t+3`.
2. The first qualifying ISRATIO level trough in period months `[t,t+12]` exists, and OUTPUT has `Δ3_v < 0` in at least one period month from `t` through that trough's period month.

Every offset in this section is a period-month offset, not a publication-date or trading-time offset. Availability applies to every required target, input, t−3, level-trough neighbour, and follow-through month. An anchor lacking any required reading is not a failure: it is RIGHT-CENSORED and excluded from N.

### H2 — Output follows order flow with delayed inventory pressure

On the identical ORDER-anchor set used by H1, an OUTPUT downturn crossing occurs in period months `[t,t+6]`; H2 holds when INVENTORY has `Δ3_v > 0` in at least one period month from `t` through that crossing. H2 is a secondary, non-rescue description. An unavailable required reading makes its H2 description RIGHT-CENSORED, without changing anchor membership, H1, N, or the primary endpoint.

### H3 — Recovery restores output before inventory pressure clears

On the identical ORDER-anchor set used by H1, find the first period month `r ∈ [t,t+6]` with `ORDER Δ3_v > 0`; H3 holds when OUTPUT has `Δ3_v > 0` in `[r,r+9]` and INVENTORY has `Δ3_v < 0` in a period month from the first qualifying positive OUTPUT month through nine period months after that month. H3 is a secondary, non-rescue description. An unavailable required reading makes its H3 description RIGHT-CENSORED, without changing anchor membership, H1, N, or the primary endpoint.

## PRIMARY ENDPOINT

- **Primary hypothesis:** H1. The endpoint is the H1 concordance rate among counted, availability-admissible ORDER downturn-crossing anchors. Anchors are ORDER events only; every admissible anchor enters the H1 denominator exactly once.
- **Estimator:** H1 concordant anchors divided by `N`, where `N` is the number of counted anchors. A RIGHT-CENSORED anchor is excluded from N and reported separately as neither concordant nor failed.
- **Chain rule:** Walk anchors forward in period time. Keep the first anchor, skip every later anchor within 16 period months of the last COUNTED anchor, and keep the first anchor at least 16 period months after it; repeat. The identical counted set is used by H1, H2, H3, and the null.
- **Null:** Draw 2,000 random-anchor sets. Each draw samples N anchor months uniformly from all availability-admissible period months in the window, subject to the same 16 period-month separation. Compute the H1 rate for each draw. Seed is fixed at 20260924 before the run. Two-decimal ISRATIO ties remain qualifying level troughs; the null absorbs that looseness.
- **Threshold:** H1 passes only when the observed rate is at least 0.60, the exact one-sided binomial lower 95% confidence bound is greater than 0.50, and the observed rate is greater than the 95th percentile of the null-draw rates. All three conditions are required.
- **Evaluability:** If N is less than 12, the primary endpoint is NOT EVALUABLE. That is a registered result, not a failure or a pass.
- **Honest N and reporting:** Report N, RIGHT-CENSORED count, the chain rule and skipped anchors, exact binomial interval, null 95th percentile, and `N_eff`. With independent trials, the exact binomial bound stands; report the dependence disclosure beside it. H2 and H3 are secondary descriptions on the identical anchor set and never rescue H1.
- **Descriptive status:** The result is `DESCRIPTIVE_ONLY` whenever fewer than 50 matured anchors are available or `N_eff < 20`. On about 269 months with 16-month separation this will be the case, so the run's result is `DESCRIPTIVE_ONLY` by construction. Report N and `N_eff`; the window ends 2025-05-15, so 2025-05-16 through today is OUT of window and no claim about today is made.

## WINDOW AND ERA HANDLING

- Ratified publication-clock window: every row used for any purpose must have `realtime_start ∈ [2002-12-01, 2025-05-15]`. This binds target rows, input rows, t−3 neighbours, level-trough neighbours, and every follow-through month.
- Excluded era `1997-04-15 → 2002-11`: pre-NAICS and reconstruction regimes are mixed. In particular, INDPRO first published for 2002-09 and 2002-10 before the December-2002 G.17 NAICS conversion is inadmissible, so importing it as a 2002-12 transform input is forbidden.
- Excluded era `2025-05-16 → latest`: the post-2025 M3 benchmark, INDPRO's 2025-11-24 conversion, and UNKNOWN ISRATIO benchmark applicability make a new era that is too short and partly unknown. In particular, NEWORDER and ISRATIO publications for 2025-04 and 2025-05 may occur after 2025-05-16 and cannot be used.
- RIGHT-CENSORING: an anchor for which ANY required outcome or neighbour month has no admissible row inside the era, has a null required value, or has no required same-vintage t−3 row is RIGHT-CENSORED and EXCLUDED from N. It is neither a pass nor a fail. Report every censored anchor with the blocking series and month.
- Earliest possible anchor: the five-month crossing reaches back to `t−2`, and ORDER at `t−2` needs its same-vintage input at `t−5`. Both input publication clocks must be at least 2002-12-01. The first two such period months are 2002-12 and 2003-01, so the earliest possible anchor period is **2003-02**. The lag receipts do not make an earlier anchor available because era admission precedes the three-month deadline.
- Latest possible anchor: H1 requires follow-through through period month `t+15` in the limiting case of a first trough at `t+12` followed by the output reading at that trough. The last admissible period month is 2025-05, so the latest possible anchor period is **2024-02**. The same era bound is applied to shorter realized outcomes: every required month must itself have an admissible publication clock.
- The approximately 269-month span is source-clock information, not an outcome observation. No row outside the era may be selected, transformed, classified, or used to repair a blocked row.

## DISCLOSURES

- This is a macro-only, internal-only, retrospective diagnostic. It has no issuer, issuer mapping, sector population, or trade. Aggregate macro series cannot represent failed or delisted firms, and survivorship is disclosed as a limitation rather than claimed away by macro-only construction.
- Every FRED/ALFRED leg remains internal-only. Neither the diagnostic nor its result may appear on a public or user-facing surface.
- `AWHMAN` is diagnostic-only. It may be reported beside anchors when available but never blocks an anchor, defines eligibility, or changes H1, H2, H3, or the null.
- The diagnostic can describe publication-clock timing among order flow, inventories, and output. It cannot prove causation, select a sector, admit a pilot or trade, support a position or sizing rule, establish capacity, or make a market-direction or profitability claim.
- Neither a pass nor a fail authorizes any return inspection, pilot, public surface or B18 work; the diagnostic is machinery evidence only (DEC:PROPHET-US-B16-CYCLE-INTERNAL-DIAGNOSTIC-ERA).

## RUN CONTRACT

The run is read-only with respect to every source and may start only after this PR merges. The run lane fills `<v2_merge_sha>` from `origin/main` and records it, then verifies this file and every governing record at that SHA.

The run lane fills `<vintages_blob_sha>` with:

```text
git rev-parse <v2_merge_sha>:data/fred_vintage/vintages.parquet
```

It then reads exactly that blob with the following command and records both SHAs in its report:

```text
git cat-file -p <vintages_blob_sha>
```

Required source query, where `target_vintages` is the first-vintage relation:

```text
WITH target_vintages AS (
  SELECT series, period, value, realtime_start, realtime_end
  FROM vintages
  WHERE series IN ('NEWORDER', 'ISRATIO', 'INDPRO')
    AND realtime_start >= DATE '2002-12-01'
    AND realtime_start <= DATE '2025-05-15'
  QUALIFY ROW_NUMBER() OVER (
    PARTITION BY series, period
    ORDER BY realtime_start ASC, realtime_end ASC
  ) = 1
)
SELECT
  target.series,
  target.period AS target_period,
  target.value AS target_value,
  target.realtime_start AS vintage,
  prior.period AS prior_period,
  prior.value AS prior_value
FROM target_vintages AS target
LEFT JOIN vintages AS prior
  ON prior.series = target.series
 AND prior.period = target.period - INTERVAL '3 MONTHS'
 AND prior.realtime_start <= target.realtime_start
 AND (prior.realtime_end > target.realtime_start
      OR prior.realtime_end IS NULL)
QUALIFY ROW_NUMBER() OVER (
  PARTITION BY target.series, target.period
  ORDER BY prior.realtime_start DESC, prior.realtime_end ASC
) = 1
```

No minimum-`realtime_start` filter or row-number qualifier may be applied to `prior`. A missing LEFT-JOIN result, null `value`, or out-of-era publication clock blocks that series-month and feeds B1 right-censoring. The store supports this join because `config/dataset_registry.yml` declares `macro.fred.vintages` at grain `(series, period, realtime_start)` with nullable `value`, non-null `realtime_start`, nullable `realtime_end`, and publication-clock semantics for `realtime_start`.

Required integrity checks report only counts, dates, series, and completeness by series-month; no endpoint is computed until every month is classified available or blocked. Write the complete anchor, censoring, H1/H2/H3, N, `N_eff`, null, and threshold table to `research/prophet_v4/r6_program/wave2/CYCLE_A_MACRO_DIAGNOSTIC_RESULT_v2_2026-09-24.md`. No return, price, outcome, ledger, scoreboard, or trial artifact may be opened before that result and its compliance review are complete.

## EVIDENCE

- Independent review basis: v1 was rejected with `RUN MAY START: NO`; B1, B2, and B3 were blockers, and M1–M8 plus m1–m4 are folded above without softening.
- v1 is the registered first version at merge `0c9e30ad4da0325b135bbf621b4498174dcc875b` and remains unchanged. That merge preceded R6-B16-01 and D03 matrix commit `89a1a5798aa4694101a87691c7871607422e9bba` on main; v2 requires verification at `<v2_merge_sha>`.
- R6-B16-01a §2 supplies the era `2002-12 → 2025-05-15`, the excluded eras, and INDPRO substitution. R6-B16-01 §1 records that AWHMAN anchors nothing.
- The v1 lag receipts are maximum publication lags only: NEWORDER 86 days, ISRATIO 116, INDPRO 93, and AWHMAN 80. They establish the frozen deadline and do not override era admission or establish anchor availability.
- `config/dataset_registry.yml` at the base records `macro.fred.vintages` storage `data/fred_vintage/vintages.parquet`, grain `(series, period, realtime_start)`, nullable `value`, nullable `realtime_end`, and publication-clock `realtime_start`; this schema supports the same-vintage t−3 selection without reading the parquet.
- No `data/fred_vintage/`, `data/prophet/`, `data/prophet_arena/`, `data/prophet_stage_shadow/`, return, outcome, ledger, scoreboard, or trial artifact was opened in this amendment lane. No endpoint, rate, count of anchors, or return was computed or estimated.

## GAPS + MUST-NOTS REFUSED

- The exact calendar day of the December-2002 G.17 NAICS conversion is not established by the governing records; no day-level conversion inference is made. The source era boundary remains 2002-12-01 through 2025-05-15 as ratified.
- No fallback, interpolation, revised row, different-vintage subtraction, moving-path source read, latest-revised level, or runner choice is admitted.
- No endpoint result is claimed, no current-regime claim is made, no issuer or sector is selected, no pilot or public surface is admitted, B18 remains blocked, and no production DDL is applied.

## SUPERSESSION

v2 supersedes v1 for every run; v1 stays as the registered first version; no endpoint was computed under v1.
