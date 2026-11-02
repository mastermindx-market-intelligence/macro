# Risk Radar replay: price-path integrity and real historical evidence

Protocol commit: `a3f85ff7b88c9361956f3f618915fea8f1b18201`.
Source base: `78ef3b7b9d50deb02ac06ec7e655b7e892bfd40c`.
Evidence: `evidence/replay-comparability-20260920/real-input-replay.json`.

## Implemented correction
The evaluator now follows the native supplied SPY observations, not a resampled
forecast-date index. Missing, nonfinite or nonpositive prices cannot become quiet
outcomes. All-missing score warmup rows are not predictions. Complete outcomes
carry explicit positive/negative counts, confusion counts and a sample fingerprint.
The existing compare_calib consumer receives these corrected metrics; no live
probability, weight, state threshold, policy, forward ledger or grader was changed.

## Actual stored-data replay — current calibration, not out-of-sample validation
The repository contains the raw inputs previously absent from sparse workspaces.
The replay read 17 input paths (none missing), checked their hashes unchanged, and
covered 8,467 SPY dates from 1993-01-29 through 2026-09-18.
The full-history evaluation removes 251 all-missing warmup dates formerly counted
as quiet predictions. Precision, recall and F1 do NOT improve from this correction.

Since 2020, for the existing elevated-or-higher state and a >=5% close-relative loss:
| Future observations | Evaluated dates | Positive windows | True alerts | False alerts | Missed positive windows |
|---|---:|---:|---:|---:|---:|
| 5 | 1,682 | 60 | 36 | 237 | 24 |
| 10 | 1,677 | 138 | 70 | 203 | 68 |
| 21 | 1,666 | 294 | 108 | 165 | 186 |

These are overlapping daily windows, NOT independent selloffs. Watch/caution are
below this evaluated alert threshold; a missed elevated alert does not mean the
Radar gave no warning. Reconstructed current-calibration history is not a timed
issued-forecast trial, does not validate today's model, and authorizes no retune.

## Boundaries and next research
The proposed extra comparison-readiness guard was platform-blocked before execution.
It is NOT implemented. Its proposed regression cases are preserved verbatim in
`evidence/replay-comparability-20260920/DEFERRED-COMPARISON-REGRESSIONS.py.txt`.
They are not represented as passing tests. Existing comparison tests remain intact.
The shipped slice is native-price/known-prediction correctness, not that guard.
Do not retry the blocked comparator modification without a material approval/tool
change. Retuning remains outside this continuation's authority.

The next scientific question is why the elevated threshold misses positive windows,
including how often watch/caution already warned. That requires explicit episode-
level attribution and a frozen candidate/holdout design, not choosing a threshold
from this table. No new independent-episode count or confidence bound is invented.

PR7498's earlier maturity repair is merged as
`83044e68e91cfc690526acbd65e03485e4c2ddb8` after all required checks passed.
This turn's privileged VPS verification request was blocked before execution;
no remote-shell runtime proof or deployment mutation is claimed from that request.
PR7467 and PR7482's accepted UI releases remain DO_NOT_REDO.
