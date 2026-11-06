# RIC F3 W1 — Expected-absence path qualification

Seat: Meta-CEO A. 2026-09-24. Packet A-RIC-F3-W1 (lane `mo_a3_ric_f3_w1`: 3 MiniMax-fix / qwen-review rounds, then seat
round 1). Branch `claude/mo-a-3-a-ric-f3-w1-expected-absence-20260924`. Files: `engine/yield_momentum.py`, `tests/test_yield_momentum.py`, this doc.

## What changed

A carried print on an **expected absence** does **not** withhold path qualification; a carried print on any
other weekday still does. Expected absences = US federal holidays **and Good Friday** (seat amendment 1 below).

- `_ExpectedAbsenceCalendar(AbstractHolidayCalendar)` with `rules = USFederalHolidayCalendar.rules + [GoodFriday]`
  (the `USFederalHolidayCalendar` idiom of `engine/capital_structure/sec_discovery_clock.py:35` and
  `engine/ownership_event_wire.py:102`, plus pandas' `GoodFriday`). `HOLIDAY_BASIS = 'us_federal_holidays_plus_good_friday_v1'`.
- Pure helper `expected_absent_grid(index) -> list[bool]` (no network, clock or I/O; empty index → `[]`).
- Every series read carries `holiday_basis`, `expected_absent_grid_rows` (int), `unexpected_carried_grid_rows`
  (int), `path_qualification_basis = 'captured_source_rows_or_expected_absent'` (also on the early-return `out`).
- `path_qualified = bool(all(observed[i] or expected[i]) and numeric.notna().all() and source_basis == 'captured_source_rows')`.
- `calculation_version` `fixed_grid_origin.v2` → `v3` (qualification semantics changed); `schema` unchanged
  (`yield_momentum.v1`). Caveat appended: "Expected absences are US federal holidays and Good Friday only; a
  carried print on any other weekday still withholds path qualification."
- `_turn_watch`: the `< 60` guard and the `TURN_LOOKBACK` window still count **grid intervals**
  (`horizon_basis: fixed_weekday_grid_intervals`); only the percentile denominator now excludes the NaN rows of
  expected absences (seat amendment 2). The call site passes the grid-based `measured`, never `measured.dropna()`.

## Seat amendments to the FROZEN SPEC (Meta-CEO A, 2026-09-24; Chairman override 09-06, no Sol carrier needed)

1. **Calendar (spec §1 said federal only).** Measured through this head on origin/main
   `data/fred/DGS{2,5,10,20,30}.parquet`, 1260-row weekday grid 2021-11-24 → 2026-09-22: each series carries 54
   rows = 51 federal-holiday rows + 3 Good Fridays (2022-04-15, 2024-03-29, 2025-04-18). Two federal-holiday dates
   printed (2021-12-31, 2023-11-10) and two Good Fridays printed (2023-04-07, 2026-04-03 — NFP-day early closes).
   Federal-only leaves `unexpected_carried_grid_rows = 3` on all five series, so `path_qualified` stays False in
   production forever (lane review minor 1 — the ruling's WHY unmet); federal + Good Friday leaves 0.
2. **Percentile denominator (spec §2 did not enumerate it).** The lane's `_turn_watch(measured.dropna(), …)`
   re-based the guard and the window to observed samples (lane review major 1, contradicting the module invariant
   "NEVER compact the calculation horizon"). The seat kept the denominator correction — without it a 1260-row grid
   with 58 expected rows scores each NaN as "not ≤ latest" and drags ~0.92 → ~0.88, withholding
   `extreme_high_watch` — but moved it inside `_turn_watch` so guard and window stay grid-based. Severability:
   reverting only the denominator fails only `test_turn_watch_percentile_excludes_carried_holiday_nans`.

## What is unchanged

`measured = numeric.where(observed)` — a holiday row stays unmeasured, an endpoint landing on one is never
promoted to a measurement; `observation_origin`, `carried_level`, `as_of`, `last_observed` semantics; the
`null_reason` literal `'endpoint comparisons only; complete observed path not qualified'` (tests pin it); the
early-return `out` sets both counters to 0, which is ambiguous with "no holidays in grid" — W2 gates on
`origin_status` / `path_qualification_basis`, never on the counters alone.

Reachable states W2 must handle: (a) `path_qualified True` together with `status 'stale'`,
`observation_origin 'carried'`, `level None`, `turn_watch None` — the latest grid row is an expected absence
(measured: 100-row grid ending 2025-02-17). `path_qualified` no longer implies a measured latest row.
(b) `expected_absent_grid_rows` is a **calendar census** (58 on the production grid), not a carry census
(54 carried rows): expected dates that printed are still counted.

## Why

`engine/yield_momentum.py::_series_read` required every one of the 1260 grid rows observed
(`research/RIC_F3_PRODUCTION_PROOF_2026_09_22.md:170-184`), while Treasury CMT series skip US market holidays, so
`path_qualified` was structurally False and `turn_watch` unreachable in production although every fixture prints every
weekday. Recorded law `research/RATES_OBSERVATION_ORIGIN_2026-09-18.md:21` ("A weekday grid is not a verified Treasury-session
calendar; holidays and other missing observations can withhold path qualification without invalidating supported endpoints") keeps its intent; withholding is narrowed to UNEXPECTED absences.

## Fixture numbers (tests a–e, this head; `python3 -m pytest tests/test_yield_momentum.py -q` → 39 passed)

| Test | Grid | Carried | `path_qualified` before → after | `turn_watch` | 22d | expected | unexpected |
|---|---|---|---|---|---|---|---|
| a MLK + Presidents' Day | 100 rows from 2025-01-02 | 2 expected | False → True | `extreme_high_watch` | 22.0 bp; accel 0.0 | 3 (Good Friday 04-18 printed, still counted) | 0 |
| b ordinary Wed 2025-03-05 | same | 1 unexpected | False → False | None | 22.0 bp | 3 | 1 |
| c endpoint = Presidents' Day | 100 rows ending 2025-02-24 | 1 expected | False → True | — | 22.0 bp; 5d None | 7 | 0 |
| d pure helper | 2025 grid | — | — | — | — | flags exactly 01-20, 02-17, 04-18 | — |
| e percentile regression | 1260 rows ending 2026-09-23 | 58 expected | True | `extreme_high_watch` (1105/1202 = 0.919 ≥ 0.90; grid denominator would score 0.877) | — | 58 | 0 |

## Production scale (measured through this head against origin/main parquets, 2026-09-24)

- Grid ending 2026-09-22 (the last printed date): all five series `path_qualified True`, expected 58, unexpected
  0, `observation_origin captured_source_row`; `turn_watch` = 2y None (22d +47 bp, percentile below 0.90),
  5y / 10y / 20y / 30y `extreme_high_watch` (22d +40 / +22 / +8 / +2 bp).
- Grid ending 2026-09-23 (the shape the 09-23 nightly baked — the frame extends to the bake date before FRED
  prints it): `path_qualified False`, `unexpected_carried_grid_rows 1` (the trailing row), origin `carried`,
  status `stale`, `turn_watch None`. A not-yet-printed weekday is a genuine unexpected absence; this matches
  origin/main `data/transmission/latest.json` today (v2, `as_of 2026-09-21`, origin carried on all five).
- Liveness condition: `turn_watch` becomes non-null on the first nightly whose frame's last grid row is a printed
  date (`observation_origin == 'captured_source_row'`). The seat reads that on main after each nightly; this
  packet makes no production claim.

## W2 consumer note

`engine/credit_momentum.py:1125` and `:1805` still read "R6: no yield_momentum.v1 yet" — consumer wiring is W2, NOT wired
here, and starts only after one nightly shows `turn_watch` non-null on main. The new caveat is EN machine-vocabulary payload
text; no template reads `yield_momentum` today (`rg yield_momentum templates/` → 0), so no crops are owed at this head, but W2
must render the condition as a plain sentence in both languages via `t('EN','ZH')` under the plain-language law, never the raw caveat.
