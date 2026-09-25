# RIC F3 W2 — trailing publication-lag tolerance (`fixed_grid_origin.v4`)

Seat: Meta-CEO A (Claude5 session 2bb0da13), 2026-09-25. Parent: RIC F3 (MAS-245) → W1 `research/RIC_F3_W1_EXPECTED_ABSENCE_QUALIFICATION_2026-09-24.md`.
Display-tier only: no authority, sizing or trading semantics change (`display_only`, `authority False`, `can_*` False unchanged).

## What changed

`engine/yield_momentum.py::_series_read` now treats a **bounded trailing publication lag** as an expected absence:

- `TRAILING_PUBLICATION_LAG_ROWS = 3` (weekday grid rows), `LAG_BASIS = 'fred_next_business_day_publication_v1'`.
- The trailing run is the maximal suffix of grid rows with no captured source row. Its non-holiday rows are the lag (`trailing_publication_lag_rows`); its holidays are counted in `trailing_expected_absent_rows`.
- When `0 < lag ≤ 3`, every unexpected absence lies inside that run, and the run is a finite carried-forward fill, momentum is **measured at the last captured source row**: the unobserved suffix is dropped, the fixed 5/22/63 weekday-grid intervals end at that row, `as_of` is that row's date, `level` its value, `measurement_origin = 'last_captured_source_row'`. `frame_as_of`, `observation_origin` (`'carried'` for the frame's latest row), `carried_level` and `last_observed` (which still describes the full grid: age, `is_current_grid_row`) are unchanged.
- A lag beyond 3 rows, or any interior unexpected absence, withholds exactly as before; the `null_reason` now ends with `; trailing publication lag N rows exceeds tolerance 3` or `; interior unexpected absence withholds the path`. Pinned literals stay as prefixes.
- A nonfinite latest print is a corrupt row, not a lag (unchanged: unqualified).
- A frame ending on a holiday with nothing lagging behind it keeps W1 state (a) (path qualified, no measurement promoted).
- `calculation_version` `fixed_grid_origin.v3 → v4`; one caveat added naming the tolerance and the dating rule.

## Why (measured, `data/transmission/latest.json` on origin/main)

| bake | version | source `as_of` (2y/10y/30y) | `frame_as_of` | trailing carried | `path_qualified` | `turn_watch` |
|---|---|---|---|---|---|---|
| 969883bc | v3 | 2026-09-22 | 2026-09-24 | 2 | False | null |
| fab3ad33 | v2 | 2026-09-22 | 2026-09-23 | 1 | False | null |
| 69b22c3b | v2 | 2026-09-21 | 2026-09-23 | 2 | False | null |
| f4269027 | v2 | 2026-09-18 | 2026-09-21 | 1 | False | null |
| e77ddced | v2 | 2026-09-18 | 2026-09-21 | 1 | False | null |
| f43207a3 | legacy | 2026-09-18 | — | — | — | 22d velocity 48 / 29 / 10 bp, turn_watch set |

FRED DGS* (Treasury CMT) publishes each date's value the next business day (~16:15 ET); the nightly bakes at ~00:00Z, the evening of the frame date. The frame's last 1–3 weekday rows are therefore always carried, `_series_read` hit `pd.isna(measured.iloc[-1])` and returned `status 'stale'`, `null_reason 'latest grid value is missing, nonfinite or carried; no new measured momentum'` for every tenor on every nightly since the fixed-grid rewrite. W1 (holidays) was correct and is untouched; it could never reach this row.

**Why 3 rows:** the measured lag over six bakes was 1–3 (Friday value lands the following Monday evening bake as a 3-row run: Fri lag + no weekend rows + Mon lag counts as 2; a holiday inside the run is counted separately). Four or more carried rows means the source itself stopped printing and stays unqualified.

**Honest dating rule:** `as_of` printed to any consumer is the last captured source row, never the frame date; display copy must say "as of <as_of>" (and may say "stale by N rows" from `trailing_publication_lag_rows`). `frame_as_of` remains available for the frame clock.

## What W3 (consumer wiring) needs

`engine/credit_momentum.py` (interim T-bond block at ~:1125 / ~:1805, "R6: no yield_momentum.v1 yet") reads `series.<tenor>.velocity_bp` / `turn_watch` / `as_of` / `measurement_origin`; it must print `as_of` (not `frame_as_of`), pass `turn_watch` through as a display-tier watch only (A7: never originate a score), and treat `measurement_origin == 'latest_grid_row'` with `status 'stale'` as the honest empty state. Liveness proof = the first nightly after this merge showing non-null `velocity_bp.22d` on tenors whose lag is ≤ 3.

## Tests (RED first, `tests/test_yield_momentum.py`)

Three pins moved deliberately (flat-frame carry, real-builder carry, 3-row carried tail: measured at the captured row, `last_observed` unchanged); new: lag 1/2/3 measured with correct endpoint dates and `as_of`; lag 4 stale with the tolerance suffix; interior absence + lag withholds; holiday inside the run skipped to the captured row; frame ending on a holiday keeps W1 state (a); nonfinite trailing print not a lag; determinism + wire-key superset + v4 caveat.
