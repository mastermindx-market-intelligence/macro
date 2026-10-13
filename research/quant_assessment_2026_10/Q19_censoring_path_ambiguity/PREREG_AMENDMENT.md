# Q19 PREREG amendment 1: operational definitions before the primary run

- Amends: `PREREG.md`, sha256 `dedbe342c380b950a4b367e6295ad17b09661cec15fcd06f5ebe9aba9a644af6`. PREREG.md itself is unchanged.
- Written: Fri Oct  9 10:56:05 UTC 2026 (from `date -u`).
- Timing: written **after** the baseline run (RUNS.log entry 1) and **before** any primary run. The baseline reads no outcome values (`uses_outcome_values: false`), only status/reason, coverage, duplicate and checkpoint counts. No barrier crossing, E, E_p or bound had been computed on real data when this was written.
- `evaluate.py` at the time of writing: sha256 `37b160e5771e927ba08290228832110835565d3062684f27087083e02b0928dd`.
  - It was edited after the baseline run. The baseline used `ea8e6f68…928a`.
  - The edit implements A5 and adds per-date and per-class count reporting. Neither touches the baseline logic.
  - Every run records the evaluate.py sha in RUNS.log.
- Module `engine/outcome_first_passage_ambiguity.py`: sha256 `bd11dc00240aed68a5ebb8ef08eb7aa07c78cf4aaa727027ca7947566a2ef52d`.
  - Its docstring verdict line is updated after the primary run.

## Why

The PREREG fixed the estimand, split, barriers, bootstrap and verdict rule. The baseline run then showed data shapes that need an exact definition so the evaluator has no discretion left:

- 4,093 episodes have no session row.
- 1,063 eod rows are `incomplete|decision_after_target_close`.
- 4,703 episodes have shorter horizons but no 10d row.
- The checkpoint `records` count is exactly 2× the episodes per session_date on all 28 dates.

None of the items below changes the estimand, the split rule, b, the bootstrap parameters, the thresholds or the verdict rule.

## Items

- **A1 Row completeness.** A session row is *complete* when all of these hold:
  - `classify_attrition(status, reason)` gives `observed` (top-level `status == "complete"`, null reason);
  - `underlying.status == "complete"`;
  - entry price and both extrema values are finite numbers;
  - `underlying.entry_time` is present.

  A row that is top-level complete but fails any of the other conditions is `informative_unknown`, reason `underlying_incomplete_or_extrema_missing`.
- **A2 Duplicates.** If one (episode, horizon) has several complete rows that disagree on entry price, high, low or entry_time, that episode is `invalid` with reason `duplicate_rows_disagree`. The baseline found 0 such duplicates.
- **A3 Float equality** uses `math.isclose(rel_tol=1e-9, abs_tol=0)`.
- **A4 Path class.** A path is the (ticker, entry_time) group of episodes.
  - If any member is observed, the path is `observed` when all observed members agree on entry/high/low (A3), otherwise `invalid` (`path_rows_disagree`).
  - Otherwise it is `informative_unknown` if any member is informative.
  - Otherwise it is `invalid` if any member is invalid.
  - Otherwise it is `administrative_pending`.
  - Paths whose members mix classes are counted and reported (`mixed_class_paths`).
- **A5 No-session-row episodes.** These have no entry_time, so they cannot join a real path.
  - They are grouped into pseudo-paths keyed by (ticker, `decision_at` rounded up to the next whole UTC hour). An episode with no decision_at is keyed by its own episode_id.
  - Pseudo-paths are dated by the episode `session_date` and classed `informative_unknown` (reason `no_session_row`).
  - This keeps their count on the same path-level footing as the deduplicated observed paths. Counting them per episode would inflate the full-denominator width against path-level observed units.
  - A pseudo-path may correspond to a real path that has other observed members. Keeping it separate is conservative: it can only widen the full-denominator bounds.
  - Episode-level counts per path class are reported as well (`episode_counts_by_path_class`).
- **A6 Representative episode.** An observed path's question clock (10d `matured_at`) and finer rows come from the lexicographically smallest observed `episode_id` in the path.
- **A7 Non-complete finer rows.** A finer row (eod/1d/3d/5d) that is present but not complete (for example eod `incomplete|decision_after_target_close`) is treated as missing, as in PREREG §6: the path keeps its coarse state and the reason is counted (`<h>:incomplete`).
- **A8 Missing evidence clock.** If both `matured_at` and `provenance.source_available_at` are missing on a finer row, the evidence is inadmissible (`availability_unknown`).
- **A9 Split and blocks.**
  - Split dates are the sorted distinct dates over all dated units of every class. TRAIN is the first 14 of those dates, per PREREG §12.
  - Bootstrap blocks are the TEST dates, in order, that have at least one observed unit.
  - TEST dates with no observed unit are reported (`test_dates_all` vs `test_dates_with_observed`) but carry no E information.
  - The PREREG §15 "TEST dates" minimum counts dates with observed units.
- **A10 LOTO.** Leave-one-ticker-out runs over every ticker with observed TEST units. Each pass drops all of that ticker's TEST units.
- **A11 5d secondary.** Uses the same TRAIN-fitted b and the same rules with finer windows eod/1d/3d. It never bears on the verdict.
- **A12 Incidence units** (TEST only):
  - An observed unit's event is its refined state at the horizon index where it first crossed, or the 10d index when the coarse state was kept and was identified. An observed unit with state `neither` has no event and is set at time 10.
  - A pending unit is censored at the largest horizon index with a complete row among its members.
  - An informative or invalid unit is censored at 0.
  - Non-informative censoring is asserted only for calendar-driven pending units. Informative classes are never treated as benign, so the module is expected to return `bounds_only`.
- **A13 RUNS.log time stamps.** The `--utc` string is supplied by the caller from `date -u`. evaluate.py reads no clock.

## Run discipline

There is one primary run. A re-run is allowed only for a crash or a demonstrable implementation defect. Any re-run is logged in RUNS.log and described in an addendum to this file before it happens.
