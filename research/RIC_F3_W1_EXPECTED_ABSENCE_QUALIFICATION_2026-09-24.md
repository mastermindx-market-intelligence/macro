# RIC F3 W1 — Expected-absence path qualification

Seat: Meta-CEO A. Date: 2026-09-24. Packet A-RIC-F3-W1. Branch:
`claude/mo-a-3-a-ric-f3-w1-expected-absence-20260924`. Files touched:
`engine/yield_momentum.py`, `tests/test_yield_momentum.py`, this doc.

## What changed

A carried print on a US federal holiday is **expected** and does **not**
withhold path qualification. A carried print on any other weekday still does.

- New pure helper `expected_absent_grid(index) -> list[bool]` in
  `engine/yield_momentum.py` (no network, clock or I/O; empty index → `[]`).
  Uses `pandas.tseries.holiday.USFederalHolidayCalendar().holidays(start,
  end)` — the same idiom as `engine/capital_structure/sec_discovery_clock.py:35`
  and `engine/ownership_event_wire.py:102`.
- New module constant `HOLIDAY_BASIS = 'us_federal_holidays_v1'`.
- Every series read now carries (in addition to existing keys):
  `holiday_basis`, `expected_absent_grid_rows` (int),
  `unexpected_carried_grid_rows` (int),
  `path_qualification_basis = 'captured_source_rows_or_expected_absent'`.
- `path_qualified` now requires
  `all(qualified_rows) and numeric.notna().all() and source_basis == 'captured_source_rows'`,
  where `qualified_rows[i] = observed[i] or expected[i]`.
- `calculation_version` bumped from `fixed_grid_origin.v2` to
  `fixed_grid_origin.v3` (qualification semantics changed). Schema unchanged.
- One new caveat appended to `caveats`:
  "Expected absences are US federal holidays only; a carried print on any
  other weekday still withholds path qualification."

## What is unchanged

`measured = numeric.where(observed)` stays untouched — a holiday row remains
unmeasured, so an endpoint landing on a holiday is never promoted to a
measurement. `observation_origin`, `carried_level`, `as_of`, `last_observed`
semantics are unchanged. The `null_reason` literal
`'endpoint comparisons only; complete observed path not qualified'` is
unchanged (tests pin it).

## Why

`engine/yield_momentum.py::_series_read` sets `path_qualified = all(observed)
and numeric.notna().all() and source_basis == 'captured_source_rows'`
(research/RIC_F3_PRODUCTION_PROOF_2026_09_22.md:170-184). US Treasury CMT
series do not print on US market holidays; the real 1260-row weekday grid
carries 54 rows for `us20y` and `path_qualified` is structurally False every
night, leaving `turn_watch` unreachable in production while 24 tests stay
green. The recorded law is research/RATES_OBSERVATION_ORIGIN_2026-09-18.md:21
— "A weekday grid is not a verified Treasury-session calendar; holidays and
other missing observations can withhold path qualification without
invalidating supported endpoints." This packet keeps that intent and narrows
the withholding to UNEXPECTED absences.

## Fixture before→after numbers (tests a–c)

| Test | Carried print | path_qualified | turn_watch | 22d velocity |
|---|---|---|---|---|
| a (MLK + Presidents) | 2 expected absences | True | `extreme_high_watch` | 22.0 bp |
| b (Wed Mar 5) | 1 unexpected absence | False | None | (qualified_rows fails) |
| c (endpoint = Presidents) | 1 expected absence | True | n/a | 22.0 bp; 5d = None |

`unexpected_carried_grid_rows` is 0/1/0 across a/b/c;
`expected_absent_grid_rows` is 2/2/2.

## W2 consumer note

`engine/credit_momentum.py:1125` and `:1805` still read
"R6: no yield_momentum.v1 yet" — the consumer wiring is a LATER packet (W2)
and is **NOT** wired here. This packet changes only the engine-side
qualification; it adds no consumer coupling and alters no feed.

## Production liveness

The seat reads `turn_watch` on `origin/main` data/transmission/latest.json
after the first nightly. The lane makes no production claim until that read
is observed; this packet is the engine-side prerequisite.
