STATUS: IN_PROGRESS

## STATUS + AUTHORITY

- Operation: `prophet-us-fable-meta-ceo-20260923-001`; lane `pu_w2_cycle_a_diag_prereg`; commissioner: the Fable Meta-CEO seat.
- Authority: R6-D03-01 §1 (`research/prophet_v4/r6_program/rulings/R6-D03-01_SOURCE_READINESS_SCOPE_2026-09-23.md`), R6-B16-01 (`.../rulings/R6-B16-01_ADMISSION_2026-09-23.md`, PR #7842), and R6-B16-01a (`.../rulings/R6-B16-01a_ERA_RATIFICATION_2026-09-23.md`, PR #7845). R6-B16-01a §2 ratifies the window and §3 admits only this macro-only diagnostic; it admits no pilot, trade, sector selection, public surface, or B18 release.
- Evidence basis: the D03 matrix §2 (`.../wave2/D03_SOURCE_READINESS_MATRIX_2026-09-23.md`, PR #7842), the era record (`.../wave2/CYCLE_A_ERA_TREATMENT_RECORD_2026-09-23.md`, PR #7845), and the FRED posture in `research/licenses/PROPHET_US_SOURCE_RIGHTS_REGISTER_2026-09-23.md`. The gate/endpoint format mirrors `research/prophet_v4/B4_ENTRY_POLICY_CALIBRATION_PREREG_2026-09-23.md`; its outcome domain is not imported.
- This preregistration computes no return and admits no trade; it is the gate a later diagnostic run must pass before any return is inspected.

## HYPOTHESES

### Frozen publication-clock transformation

For each calendar period `t`, select the initial-release row for each series as the row with the minimum `realtime_start` for that `(series, period)` in `data/fred_vintage/vintages.parquet`; `realtime_start` is the publication clock. Do not select a later revised row, infer an absent row, interpolate, normalize levels, or use a latest-revised fallback. A target month is available only when every required initial-release row and every transformation input has published by that target row's `realtime_start`; a missing or late required row blocks that month.

- `ORDER(t) = NEWORDER_first(t) - NEWORDER_first(t-3)`. Positive means order flow strengthening; negative means order flow weakening.
- `INVENTORY(t) = ISRATIO_first(t) - ISRATIO_first(t-3)`. Positive means inventory pressure building; negative means inventory pressure easing.
- `OUTPUT(t) = INDPRO_first(t) - INDPRO_first(t-3)`. Positive means output expanding; negative means output contracting.
- `HOURS(t) = AWHMAN_first(t) - AWHMAN_first(t-3)`. Positive means labor input strengthening; negative means labor input weakening. `HOURS` is report-only and never defines an episode or endpoint.

A trough is a calendar month with a nonpositive transformed value preceded by two positive values and followed by two negative values; a peak is the reverse. Distinct anchor episodes must be separated by at least six calendar months, are ordered by first qualifying month, and are allocated once to the earliest hypothesis that qualifies. Each hypothesis below names all three anchoring transformations; `HOURS` is never an anchor.

### H1 — Order flow leads inventory turns while output contracts

At a distinct `ORDER` trough, `INVENTORY` is nonnegative or rising within three months and an `ISRATIO` level trough follows within zero to twelve months, while `OUTPUT` is negative in at least one month from the `ORDER` trough through that `ISRATIO` trough. Falsifier: an eligible `ORDER` trough without the required inventory and output readings.

### H2 — Output follows order flow with delayed inventory pressure

At a distinct `ORDER` trough, `OUTPUT` has a trough within zero to six months and `INVENTORY` is positive in at least one month over that lead interval. Falsifier: an order-flow trough followed by no output trough, no positive inventory-pressure month, or blocked source months in the interval.

### H3 — Recovery restores output before inventory pressure clears

After a distinct `ORDER` trough followed by a positive `ORDER` value within six months, `OUTPUT` becomes positive within zero to nine months of that recovery month and `INVENTORY` becomes negative within zero to nine months after the output recovery. Falsifier: a qualifying order recovery without the required output and inventory sequence, or blocked source months in the interval.

## PRIMARY ENDPOINT

## WINDOW AND ERA HANDLING

## DISCLOSURES

## RUN CONTRACT

## EVIDENCE

## GAPS + MUST-NOTS REFUSED
