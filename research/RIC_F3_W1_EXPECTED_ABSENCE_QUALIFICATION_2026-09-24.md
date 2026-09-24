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
  `engine/ownership_event_wire.py:102`. Module constant
  `HOLIDAY_BASIS = 'us_federal_holidays_v1'`.
- Every series read now carries `holiday_basis`,
  `expected_absent_grid_rows` (int), `unexpected_carried_grid_rows` (int),
  `path_qualification_basis = 'captured_source_rows_or_expected_absent'`.
- `path_qualified` now requires `all(qualified_rows) and numeric.notna().all()
  and source_basis == 'captured_source_rows'`, where
  `qualified_rows[i] = observed[i] or expected[i]`.
- `calculation_version` bumped `v2` → `v3`; schema unchanged. One new caveat:
  "Expected absences are US federal holidays only; a carried print on any
  other weekday still withholds path qualification."
- `_turn_watch` invoked with `measured.dropna()` (see §Turn-watch
  percentile bias). Denominator is the observed sample, not the grid length.

## What is unchanged

`measured = numeric.where(observed)` untouched — a holiday row stays
unmeasured, so an endpoint landing on a holiday is never promoted to a
measurement. `observation_origin`, `carried_level`, `as_of`, `last_observed`
semantics unchanged. The `null_reason` literal
`'endpoint comparisons only; complete observed path not qualified'` is
unchanged (tests pin it). The early-return `out` at line 155 sets both
counters to 0; a `0` is therefore ambiguous between "no origin evidence" and
"no holidays in grid" — W2 must gate on `origin_status`.

## Why

`engine/yield_momentum.py::_series_read` sets `path_qualified = all(observed)
and numeric.notna().all() and source_basis == 'captured_source_rows'`
(research/RIC_F3_PRODUCTION_PROOF_2026_09_22.md:170-184). US Treasury CMT
series do not print on US market holidays; the real 1260-row weekday grid
carries 54 rows for `us20y` and `path_qualified` is structurally False every
night, leaving `turn_watch` unreachable in production while 34 pre-existing
tests stay green. Recorded law at research/RATES_OBSERVATION_ORIGIN_2026-09-18.md:21
— "A weekday grid is not a verified Treasury-session calendar; holidays and
other missing observations can withhold path qualification without
invalidating supported endpoints." This packet keeps that intent and narrows
withholding to UNEXPECTED absences.

## Turn-watch percentile bias (production scale)

`_turn_watch` (engine/yield_momentum.py:136) computes
`percentile = float((trailing <= trailing.iloc[-1]).mean())` over
`trailing = values.iloc[-TURN_LOOKBACK:]`. With prior `values=measured`,
every carried holiday row is `NaN`, `(NaN <= x)` is `False`, and the
denominator was the **grid length (1260)**, not the observed sample (~1207).
On the production 1260-row weekday grid ending 2026-09-23, **53 US federal
holidays fall inside**; a true observed percentile of 0.9198 scored
1110/1260 = 0.8810, below the 0.90 threshold and silently suppressing
`extreme_high_watch` on the rising regime this packet exists to unblock.
Fix: `_turn_watch(measured.dropna(), …)`. RED-first regression asserts
`turn_watch == 'extreme_high_watch'` on a fixture engineered so biased
denominator scores 0.881 and post-fix scores 0.9198.

## Fixture before→after numbers (tests a–c)

`expected_absent_grid_rows` counts every grid date the calendar flags as a
US federal holiday, not just the carried ones.

| Test | Carried | Before → after `path_qualified` | After `turn_watch` | 22d | `expected` | `unexpected` |
|---|---|---|---|---|---|---|
| a (MLK + Presidents) | 2 expected | False → True | `extreme_high_watch` | 22.0 bp | 2 | 0 |
| b (Wed Mar 5) | 1 unexpected | False → False | None | 22.0 bp | 2 | 1 |
| c (endpoint = Presidents) | 1 expected | False → True | n/a (insufficient) | 22.0 bp; 5d = None | 7 | 0 |

Test (c)'s grid is `pd.bdate_range(end='2025-02-24', periods=100)`
(2024-10-08 → 2025-02-24); the calendar flags seven holidays inside it; only
2025-02-17 is the carried print — the other six carry measured rows.

## W2 consumer + production liveness

`engine/credit_momentum.py:1125` and `:1805` still read "R6: no
yield_momentum.v1 yet" — consumer wiring is LATER (W2) and NOT wired here.
The seat reads `turn_watch` on `origin/main` data/transmission/latest.json
after the first nightly; the lane makes no production claim until then.