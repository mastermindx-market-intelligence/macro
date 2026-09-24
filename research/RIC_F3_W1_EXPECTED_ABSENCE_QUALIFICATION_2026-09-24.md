# RIC F3 W1 — Expected-absence path qualification

Seat: Meta-CEO A. Date: 2026-09-24. Packet A-RIC-F3-W1. Branch:
`claude/mo-a-3-a-ric-f3-w1-expected-absence-20260924`. Files touched:
`engine/yield_momentum.py`, `tests/test_yield_momentum.py`, this doc.

## What changed

A carried print on a US federal holiday is **expected** and does **not**
withhold path qualification. A carried print on any other weekday still does.

- Pure helper `expected_absent_grid(index) -> list[bool]` (no network, clock,
  I/O; empty index → `[]`). Uses
  `pandas.tseries.holiday.USFederalHolidayCalendar().holidays(start, end)` —
  same idiom as `engine/capital_structure/sec_discovery_clock.py:35` and
  `engine/ownership_event_wire.py:102`. Constant `HOLIDAY_BASIS = 'us_federal_holidays_v1'`.
- Every series read carries `holiday_basis`,
  `expected_absent_grid_rows` (int), `unexpected_carried_grid_rows` (int),
  `path_qualification_basis = 'captured_source_rows_or_expected_absent'`.
- `path_qualified = bool(all(qualified_rows) and numeric.notna().all() and
  item['source_basis'] == 'captured_source_rows')`, where
  `qualified_rows[i] = observed[i] or expected[i]`.
- `calculation_version` bumped `v2` → `v3`; schema unchanged. New caveat:
  "Expected absences are US federal holidays only; a carried print on any
  other weekday still withholds path qualification."
- `_turn_watch` invoked with `measured.dropna()` — see §Spec deviations.

## What is unchanged

`measured = numeric.where(observed)` untouched — a holiday row stays
unmeasured, so an endpoint landing on a holiday is never promoted to a
measurement. `observation_origin`, `carried_level`, `as_of`, `last_observed`
semantics unchanged. `null_reason` `'endpoint comparisons only; complete
observed path not qualified'` is unchanged (tests pin it). The early-return
`out` at line 155 sets both counters to 0; a `0` is ambiguous between "no
origin evidence" and "no holidays in grid" — W2 must gate on `origin_status`.

## Why

`engine/yield_momentum.py::_series_read` sets `path_qualified = all(observed)
and numeric.notna().all() and source_basis == 'captured_source_rows'`
(research/RIC_F3_PRODUCTION_PROOF_2026_09_22.md:170-184). US Treasury CMT
series do not print on US market holidays; the real 1260-row weekday grid
carries ~54 rows for `us20y` and `path_qualified` is structurally False every
night, leaving `turn_watch` unreachable in production. Recorded law at
research/RATES_OBSERVATION_ORIGIN_2026-09-18.md:21 — "A weekday grid is not a
verified Treasury-session calendar; holidays and other missing observations
can withhold path qualification without invalidating supported endpoints."
This packet keeps that intent and narrows withholding to UNEXPECTED absences.

## Production scale — Good Friday gap (BLOCKER 1)

Driven off the committed source (`data/fred/DGS20.parquet`) on the real
1260-row weekday grid 2021-09-07 → 2026-09-22, this packet returns
`path_qualified = False`, `expected_absent_grid_rows = 53`,
`unexpected_carried_grid_rows = 3`, `turn_watch = None`. The 3 residual
disqualifiers are **Good Fridays** — `2022-04-15`, `2024-03-29`,
`2025-04-18` — which `USFederalHolidayCalendar` does **not** contain.
FROZEN SPEC 1 mandates that calendar idiom; a silent relaxation would
violate the spec. Per AGENTS.md §Adjudication coverage gate, the live
exemplar is named: **this packet does NOT unblock `turn_watch` in
production**. The seat is asked to amend the spec in a follow-up packet
(add Good Friday or move to a Treasury/SIFMA session calendar). The packet
makes **no production claim** about `turn_watch` until then.

## Spec deviations + turn-watch percentile bias

The dropna call (`_turn_watch(measured.dropna(), …)`) was not enumerated by
FROZEN SPEC 2. Semantics of `measured` are unchanged (a holiday row is still
`NaN`); the change is at the percentile denominator. Strict no-op on every
path `path_qualified` could reach on origin/main (zero NaNs there). Genuinely
RED-first: reverting only this line breaks the percentile test
(`assert None == 'extreme_high_watch'`). On a 1260-row grid ending 2026-09-23
with 53 carried holidays, a true observed percentile 0.9198 would have scored
1110/1260 = 0.8810, below the 0.90 threshold. Fix only matters once
`path_qualified` becomes True (see §Production scale — Good Friday gap).

## Fixture before→after numbers (tests a–c, measured on this head)

| Test | Carried | Before → after `path_qualified` | After `turn_watch` | 22d | `expected` | `unexpected` |
|---|---|---|---|---|---|---|
| a (MLK + Presidents) | 2 expected | False → True | `extreme_high_watch` | 22.0 bp | 2 | 0 |
| b (Wed Mar 5) | 1 unexpected | False → False | None | 22.0 bp | 2 | 1 |
| c (endpoint = Presidents) | 1 expected | False → True | `extreme_high_watch` | 22.0 bp; 5d = None | 7 | 0 |

Test (c) grid: `pd.bdate_range(end='2025-02-24', periods=100)`; only 2025-02-17 (Presidents' Day) is the carried print.

## W2 consumer + production liveness

`engine/credit_momentum.py:1125` and `:1805` still read "R6: no yield_momentum.v1 yet" — consumer wiring is LATER (W2) and NOT wired here. The seat reads `turn_watch` on `origin/main` data/transmission/latest.json after the first nightly; the lane makes no production claim until then.
