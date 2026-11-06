# Risk Radar replay — complete-outcome repair

Authority: current Chairman instruction to improve Risk Radar research and models.
Source: Mastermind `b75a491db408892dfe6fe7c4bb9d40cfad8efcb3`, Skillpack1.0.1/bootstrap1.
Carrier: `claude/risk-radar-replay-maturity-20260920`.
Base: macro `83746deb2f3f4ce2de6ef4e683d66e9337087e38`.
Direct execution: PRINCIPAL_JUDGMENT / CRITICAL_PATH_SHORTCUT; no worker transfer.

## Reproduced defects

`engine/risk_radar_backtest.py::state_accuracy` formed a forward minimum with
whatever future observations remained, even when the requested horizon was incomplete.
It then thresholded NaN into False and called dropna on that boolean result.
Consequently the last unfinished rows counted as evaluated forecasts, including the
last row with no future observation. In a fixed synthetic 30-close / 21-session case,
the original source counted 30 forecasts although only 9 had complete windows.

A second defect was in `compare_calib`: missing F1 evidence was converted to zero,
so a proposed score could beat an unmeasured baseline. Six new deterministic regression
tests failed on the original code before the correction; no live model was retuned.

## Bounded correction

Require positive integer horizons and H complete future observations. Select from
non-null outcomes before boolean labels can hide missingness. Both incomplete positive
and negative tails are excluded, without outcome-dependent sample selection. Return
unknown metrics for an empty scored population, and report n_unscored separately.
A calibration comparison is ready only when both candidates have both required scores;
unknown evidence cannot earn an improvement. The complete-data improvement rule is unchanged.

This aligns the complete-horizon discipline with the existing forward grader; it
changes no risk probability, weight, threshold, policy, store, or historical ledger.

## Verification and limits

All seven added regressions now pass. The full local Radar + canonical grader run
has 42 passes and five failures. The same five tests fail on the unmodified parent
backtest module in the same environment (35 passes, six new tests deselected).
They require the absent market-data store; they are not waived or called green.
Exact transcripts: `evidence/replay-maturity-20260920/{red,green,base}.log`.

The synthetic tail-drop fixture now scores 9 complete forecasts, not 30. This is
an evaluator correctness result, NOT a new empirical model performance claim.
No real-market replay, calibration proposal, collector or historical regrading was run.
Existing price alignment, per-leg onset tests, permutation method, thresholds,
validated-leg requirements and current calibration remain outside this patch.

This is independent of PR7492's issued-probability diagnostic. Both improve research
truthfulness, but neither demonstrates improved live prediction or grants a trade.
Required exact-head CI, release review and production publication remain separate.

Final adversarial hardening: comparison scores must also be finite numeric values
in [0,1], excluding booleans. An interim null-only guard accepted a synthetic
infinite F1 as improvement; the seventh regression now rejects that counterexample
and other malformed scores. Final full local result: 42 passed, with the same
five base-inherited market-data failures. `verification.json` binds the final
source hash and exact failed-test identities; no real-data gate is waived.
