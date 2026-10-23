STATUS: COMPLETE

## STATUS + AUTHORITY

- Operation: `prophet-us-fable-meta-ceo-20260923-001`; lane `pu_w2_cycle_a_diag_prereg`; commissioner: the Fable Meta-CEO seat.
- Authority: R6-D03-01 §1 (`research/prophet_v4/r6_program/rulings/R6-D03-01_SOURCE_READINESS_SCOPE_2026-09-23.md`), R6-B16-01 (`.../rulings/R6-B16-01_ADMISSION_2026-09-23.md`, PR #7842), and R6-B16-01a (`.../rulings/R6-B16-01a_ERA_RATIFICATION_2026-09-23.md`, PR #7845). R6-B16-01a §2 ratifies the window and §3 admits only this macro-only diagnostic; it admits no pilot, trade, sector selection, public surface, or B18 release.
- Evidence basis: the D03 matrix §2 (`.../wave2/D03_SOURCE_READINESS_MATRIX_2026-09-23.md`, PR #7842), the era record (`.../wave2/CYCLE_A_ERA_TREATMENT_RECORD_2026-09-23.md`, PR #7845), and the FRED posture in `research/licenses/PROPHET_US_SOURCE_RIGHTS_REGISTER_2026-09-23.md`. The gate/endpoint format mirrors `research/prophet_v4/B4_ENTRY_POLICY_CALIBRATION_PREREG_2026-09-23.md`; its outcome domain is not imported.
- This preregistration computes no return and admits no trade; it is the gate a later diagnostic run must pass before any return is inspected.

## HYPOTHESES

### Frozen publication-clock transformation

For each calendar period `t`, select the initial-release row for each series as the row with the minimum `realtime_start` for that `(series, period)` in `data/fred_vintage/vintages.parquet`; `realtime_start` is the publication clock. Do not select a later revised row, infer an absent row, interpolate, normalize levels, or use a latest-revised fallback.

### Frozen publication-availability rule

A row for target month `t` is available for a series only when its initial-release `realtime_start` is on or before the end of the third calendar month after `t`. That single deadline applies to every series and every target month, before endpoint evaluation. A target month is available only when every required target and input initial-release row exists and passes its own deadline. A missing or late required row blocks that month. The deadline was chosen before hypothesis evaluation from the observed initial-release lags over all vintage rows: the maximum lag is 86 days for `NEWORDER`, 116 days for `ISRATIO`, 93 days for `INDPRO`, and 80 days for `AWHMAN`, so the third month-end is the first common whole-month boundary after each maximum. The later run must report each series' minimum, median, and maximum lag but may not change this availability rule.

- `ORDER(t) = NEWORDER_first(t) - NEWORDER_first(t-3)`. Positive means order flow strengthening; negative means order flow weakening.
- `INVENTORY(t) = ISRATIO_first(t) - ISRATIO_first(t-3)`. Positive means inventory pressure building; negative means inventory pressure easing.
- `OUTPUT(t) = INDPRO_first(t) - INDPRO_first(t-3)`. Positive means output expanding; negative means output contracting.
- `HOURS(t) = AWHMAN_first(t) - AWHMAN_first(t-3)`. Positive means labor input strengthening; negative means labor input weakening. `HOURS` is report-only and never defines an episode or endpoint.

A trough is a calendar month with a nonpositive transformed value preceded by two positive values and followed by two negative values; a peak is the reverse. Distinct anchor episodes must be separated by at least six calendar months, are ordered by first qualifying month, and are allocated once to the earliest hypothesis that qualifies. Each hypothesis below names all three anchoring transformations; `HOURS` is never an anchor.

### ISRATIO level trough

An `ISRATIO` level trough is a distinct local minimum of the initial-release `ISRATIO_first` level: the month's level is no greater than the two preceding and two following levels, no preceding level within that five-month span is lower, and adjacent equal minima belong to one candidate whose anchor is the earliest minimum. The same publication-availability rule applies to all five level rows. A level trough is never an anchor episode.

### H1 — Order flow leads inventory turns while output contracts

At a distinct `ORDER` trough, `INVENTORY` is nonnegative or rising within three months and an `ISRATIO` level trough follows within zero to twelve months, while `OUTPUT` is negative in at least one month from the `ORDER` trough through that `ISRATIO` trough. Falsifier: an eligible `ORDER` trough without the required inventory and output readings.

### H2 — Output follows order flow with delayed inventory pressure

At a distinct `ORDER` trough, `OUTPUT` has a trough within zero to six months and `INVENTORY` is positive in at least one month over that lead interval. Falsifier: an order-flow trough followed by no output trough, no positive inventory-pressure month, or blocked source months in the interval.

### H3 — Recovery restores output before inventory pressure clears

After a distinct `ORDER` trough followed by a positive `ORDER` value within six months, `OUTPUT` becomes positive within zero to nine months of that recovery month and `INVENTORY` becomes negative within zero to nine months after the output recovery. Falsifier: a qualifying order recovery without the required output and inventory sequence, or blocked source months in the interval.

## PRIMARY ENDPOINT

- **Primary hypothesis:** H1. There is exactly one primary endpoint: the **publication-clock sequence concordance rate**, the proportion of distinct eligible `ORDER`-trough anchor episodes in which the H1 inventory and output conditions both hold.
- **Estimator:** number of H1-concordant anchor episodes divided by the number of distinct eligible `ORDER`-trough anchor episodes after unavailable or blocked anchor episodes are counted in the denominator. Use the exact one-sided binomial 95% confidence interval for the proportion.
- **Null:** the H1 concordance probability is at most 0.50.
- **Pass/fail threshold:** H1 passes only if there are at least 12 distinct eligible anchor episodes, the point estimate is at least 0.60, and the exact lower 95% binomial confidence bound exceeds 0.50. Otherwise it fails; no H2 or H3 result may rescue it.
- **Honest N:** distinct episode count, not months or event fires. Each episode begins at its allocated `ORDER` trough; overlapping candidates within six months belong to the same episode; unavailable or blocked anchors count as failed sequences, and their count is reported separately within the attempted-episode census.
- H2 and H3 are registered mechanism falsifiers and descriptive disclosures, not primary or rescue endpoints. All hypothesis-specific results and blocked episodes must be reported in one table.

## WINDOW AND ERA HANDLING

- Ratified window: **2002-12 → 2025-05-15** on publication clocks, exactly as ruled by R6-B16-01a §2. The target period runs from 2002-12 through 2025-05; its first transform input is 2002-09 and its last is 2025-05. The approximately 269-month span is source-clock information, not an outcome observation.
- Excluded era: **1997-04-15 → 2002-11**, because its pre-NAICS reconstruction regimes are mixed (`M3 2001-05`, `MTIS 2001-06`, `G.17 2002-12`); it may support diagnostic-only splicing but is excluded from this ratified window.
- Excluded era: **2025-05-16 → latest**, because the post-2025 M3 benchmark, `INDPRO` 2022-NAICS conversion on 2025-11-24, and unknown `ISRATIO` benchmark applicability make a new, too-short, partly unknown era.
- A required initial-release vintage row missing inside 2002-12 → 2025-05-15, or publishing later than that period's initial-release publication rule requires, blocks that month. The run must stop before endpoint reporting unless every required month is classified available or blocked under this rule; it must never substitute zero, a lagged value, interpolation, or a revised row.

## DISCLOSURES

- This is macro-only, internal-only, and retrospective. It contains no issuer, no issuer mapping, no sector population, and no trade; survivorship is therefore inapplicable as an issuer-selection fact and is reported as a limitation because aggregate macro series cannot represent failed or delisted firms.
- Rule-5 posture is controlling: every FRED leg is internal-only because FRED/ALFRED model use and redistribution remain unresolved in `research/licenses/PROPHET_US_SOURCE_RIGHTS_REGISTER_2026-09-23.md`. Neither this diagnostic nor its output may be exposed on a user-facing surface.
- `AWHMAN` is a diagnostic-only fourth leg. Report `HOURS` descriptive readings beside eligible episodes, but never use `HOURS` to anchor an episode, define eligibility, alter the endpoint, or rehabilitate a failed hypothesis.
- This diagnostic can describe publication-clock timing among order flow, inventories, output, and the report-only hours measure. It cannot prove causation, select a sector, admit a pilot or trade, support a position or sizing rule, establish capacity, or make any market-direction or profitability claim.
- A failed or passing sequence test says only whether these macro mechanisms cohered in this ratified source-clock window. A failure is not evidence that the broader mechanism family lacks value; a pass is not evidence of alpha.

## RUN CONTRACT

A later run must first verify that this file is merged at a named commit SHA on `origin/main`, record that SHA in its output, and only then compute the endpoint. The run is read-only with respect to all sources.

Required source command:

```text
git show origin/main:data/fred_vintage/vintages.parquet > "$RUN_SCRATCH/vintages.parquet"
```

Required source query:

```text
SELECT series, period, value, realtime_start
FROM read_parquet('$RUN_SCRATCH/vintages.parquet')
WHERE series IN ('NEWORDER', 'ISRATIO', 'INDPRO', 'AWHMAN')
QUALIFY ROW_NUMBER() OVER (
  PARTITION BY series, period ORDER BY realtime_start ASC, realtime_end ASC
) = 1
```

Required source integrity checks, using only that query result:

```text
SELECT series, MIN(realtime_start), MAX(realtime_start), COUNT(*) FROM initial_releases GROUP BY series;
SELECT series, COUNT(*) FROM initial_releases WHERE period >= DATE '2002-09-01' AND period <= DATE '2025-05-01' GROUP BY series;
```

The run must materialize each transformed value only from those initial-release rows, classify every target month available or blocked under the frozen publication rule, and write the endpoint result and complete episode table to `research/prophet_v4/r6_program/wave2/CYCLE_A_MACRO_DIAGNOSTIC_RESULT_2026-09-23.md`. It must not open a return, price, outcome, ledger, scoreboard, or trial artifact before that result and its preregistration compliance review are complete.

### Commit cadence

The seven pre-review commits did not use one commit per numbered section: three commits each completed two sections. That cadence cannot be amended or replayed without rewriting history. This round adds one new commit for the reviewer fixes and preserves the existing commits as immutable evidence.

## EVIDENCE

- Skeleton-first execution: created this file, committed its headings with `STATUS: IN_PROGRESS`, and pushed commit `d9a9a5b172` before substantive work.
- 2026-09-23: `git fetch origin refs/pull/7845/head:refs/remotes/pr/7845` — `* [new ref] refs/pull/7845/head -> pr/7845`.
- 2026-09-23: `git fetch origin refs/pull/7842/head:refs/remotes/pr/7842` — `* [new ref] refs/pull/7842/head -> pr/7842`.
- 2026-09-23: `git show pr/7845:.../R6-B16-01a_ERA_RATIFICATION_2026-09-23.md` — §2 ratified `2002-12 → 2025-05-15`; §3 admitted a macro-only, internal-only, retrospective diagnostic and excluded pilots, public use, and B18 release.
- 2026-09-23: `git show pr/7842:.../R6-B16-01_ADMISSION_2026-09-23.md` — §1 adjudicated independent mechanisms and §3 opened only the macro-only path after rule-4 treatment.
- 2026-09-23: `git show origin/main:.../R6-D03-01_SOURCE_READINESS_SCOPE_2026-09-23.md` — §1 rules 1–5 were read verbatim, including missing-row blocking, macro-only clauses, definition handling, and internal-only rights.
- 2026-09-23: `git show pr/7842:.../D03_SOURCE_READINESS_MATRIX_2026-09-23.md` — §2 recorded `NEWORDER` first realtime `1997-03-26` / 354 months, `ISRATIO` `1997-04-15` / 354, `INDPRO` `1997-01-17` / 357, and no missing vintage months.
- 2026-09-23: `git show pr/7845:.../CYCLE_A_ERA_TREATMENT_RECORD_2026-09-23.md` — publication-clock breaks supplied the two excluded eras and the `INDPRO` 2002-12 / 2025-11-24 boundaries; `AWHMAN` remained UNKNOWN.
- 2026-09-23: `git show origin/main:research/licenses/PROPHET_US_SOURCE_RIGHTS_REGISTER_2026-09-23.md` — FRED/ALFRED posture: internal-only, model use absent.
- 2026-09-23: `git show origin/main:data/fred_vintage/vintages.parquet` into a temporary worktree file, then pandas `read_parquet` printed schema and counts only: series strings; `period` and `realtime_start` timestamps; `AWHMAN` 357 rows, first `1997-01-10`; `INDPRO` 357, first `1997-01-17`; `ISRATIO` 354, first `1997-04-15`; `NEWORDER` 354, first `1997-03-26`. A separate three-row-per-series preview confirmed initial rows are keyed by minimum `realtime_start` and selected the 3-month transformation.
- 2026-09-23 reviewer-fix round: a date-only initial-release aggregation derived publication lags without reading values: across all rows, `NEWORDER` 50/56/86 days, `ISRATIO` 69/74/116, `INDPRO` 41/45/93, and `AWHMAN` 31/34/80 at minimum/median/maximum. The third month-end after each target month is the first common whole-month boundary after every maximum and is therefore the frozen availability deadline.
- 2026-09-23: `git show origin/main:config/dataset_registry.yml` — grain `(series, period, realtime_start)` and `realtime_start` publication-clock semantics; `git show origin/main:research/prophet_v4/B4_ENTRY_POLICY_CALIBRATION_PREREG_2026-09-23.md` supplied the mirrored gate/endpoint format.

## GAPS + MUST-NOTS REFUSED

- No hypothesis result, transformed value, episode, endpoint, confidence interval, or test statistic was computed in this preregistration lane.
- No return, outcome, ledger, scoreboard or trial artifact was opened. No price artifact was opened, and the work contracted above never uses one.
- No `data/` file was written or modified; the tracked parquet was only read from `origin/main`. No latest-revised fallback, interpolation, modeled lag, or inferred vintage row was used.
- No issuer, sector, membership, failed-issuer universe, public surface, production DDL, credential, or credential-bearing path was accessed or created. This lane does not reopen B16, unblock B18, select a trade, or resolve FRED rights.
- Gaps left for the later run: select initial rows with the required query, evaluate availability/blocking, allocate distinct episodes, compute H1 and the two registered falsifiers, and write the result receipt. The current `AWHMAN` break-history UNKNOWN remains a diagnostic-only limitation.
