# Q06 PREREG amendment 1: descriptive attrition stage (geometry only, no verdict effect)

PREREG.md stays frozen at sha256 `23494b5254d5ddf6ef91d6b5835b9ecac47adbcbeed145b0c7895c88dcccc556`.
This file adds to it and changes nothing in it.

Author: Claude Opus 5.5 (model ID `claude-opus-5-5`).

## Reason

Stages `baseline` and `e1` have each run once (RUNS.log). The e1 stage found that the eligible
geometry is very short: one NYSE fill session for 0_7 and two for 8_90. Most `graded_ok` rows
have a null `outcome_end_session_H`: 47,910 in 0_7 and 30,633 in 8_90. e1.json labels that count
`step4_end_missing_pending`. That label is a misnomer. These rows are graded, not pending. Their
interval boundary is simply missing.

The verdict must name the exact missing input. To do that, it must know whether these rows are
recent or immature, or older graded rows that predate the boundary column. No frozen stage
answers that question.

## Change

evaluate.py gains one descriptive stage, `attrition`, that runs once. It does the following:

- Reads the same columns as `e1`: the ledger `event_id, session_date, root, source,
  detector_version, dte_bucket` and the asserted grades geometry list `event_id, graded_ok,
  reason_code, fill_date, outcome_end_session_5, outcome_end_session_21, outcome_end_session_63,
  outcome_end_session_126`. It reads no outcome column.
- Applies the same cohort filters as `e1`.
- Reports, per bucket and per class, the row count, the min and max of `session_date` and
  `fill_date`, and the count per calendar month of `session_date`. The classes are:
  - graded_ok with the end boundary present
  - graded_ok with the end boundary missing
  - not graded_ok, by reason code
- Writes `attrition.json`.

## What does not change

- No threshold, cohort, gate, grid, seed, split or verdict rule changes.
- `e1` and `s1` are not rerun because of this amendment.
- The `attrition` stage feeds nothing into `verdict.json`. It only names the missing input.
