---
workstream: "WS:GREY-DEER-RISK-INTELLIGENCE"
session: "claude/risk-radar-replay-maturity-20260920"
model: sol
ended_because: blocked
mission: Correct incomplete-outcome scoring and unknown-baseline comparisons in the existing Risk Radar replay evaluator.
state_before: >
  Original source counted 30 forecasts in a synthetic 30-close/21-session case
  with only 9 complete outcome windows. Missing F1 was substituted with zero
  by compare_calib, allowing an unmeasured baseline to be beaten.
changed:
  - path: engine/risk_radar_backtest.py
    what: Require complete positive-integer horizons, exclude unknown outcomes, and refuse incomplete comparisons.
  - path: tests/test_risk_radar.py
    what: Add deterministic maturity and score-validity regressions on the existing directly enrolled suite.
  - path: research/grey_deer/RISK_RADAR_REPLAY_MATURITY_REPAIR_2026-09-20.md
    what: Record exact reproduction, correction and the empirical-evidence ceiling.
verified:
  - claim: All six new tests fail against the original source and pass after the correction.
    command: "pytest tests/test_risk_radar.py -k replay_maturity; then owning Radar + grader suites"
    result: "Original: six failures. Corrected full run: 42 pass, five unrelated data-dependent failures."
  - claim: The five broader-suite failures reproduce on the unmodified baseline module.
    command: "Load backtest module from Git base83746deb and run the same old tests in the same environment."
    result: "Same five failed test identities; 35 pass and six new regressions deselected."
unverified:
  - claim: All real-data evidence gates pass on the repaired evaluator.
    what_would_verify: Required owning CI and the canonical market-data store; no data gate was waived.
  - claim: The repair is merged and deployed.
    what_would_verify: Exact-head release acceptance, normal merge and existing publisher proof.
unresolved:
  - "Local source store is absent; five real-data tests fail equally on base and candidate."
  - "No live forecast accuracy or calibration improvement is claimed from synthetic tests."
next_actions:
  - "Publish this exact repair and consume owning CI; repair only attributable findings."
  - "Merge only after the required release checks and review, then verify the existing deployed evaluator."
  - "Keep historical adverse-episode research separate and version-specific; never tune on PR7492's zero-event sample."
do_not_redo:
  - "Do not rerun PR7467/7482's completed UI release or accepted GD-3 natural-event proof."
  - "Do not alter the current calibration, weights, probabilities, policies or canonical ledgers."
  - "Do not waive market-data tests, use incomplete positive-only tails, or substitute zero for unknown F1."
  - "PR6989/7236/6685 retain their original holds and source custody."
danger_areas:
  - "Only state_accuracy maturity and compare_calib readiness are changed; per-leg onset/permutation methodology is NOT revalidated."
  - "The synthetic 30-to-9 result is a correctness witness, not real-market predictive performance."
prs: [7492]
---

# Replay maturity correction

Base `83746deb2f3f4ce2de6ef4e683d66e9337087e38`; protected Skillpack
`b75a491db408892dfe6fe7c4bb9d40cfad8efcb3` (1.0.1/bootstrap1).
Direct principal execution: PRINCIPAL_JUDGMENT / CRITICAL_PATH_SHORTCUT.
No worker START/transfer, new store, scheduler, scoring authority or retry plane.
This is a separate source carrier from PR7492's issued-probability diagnostic.
Evidence: `research/grey_deer/evidence/replay-maturity-20260920/`.
