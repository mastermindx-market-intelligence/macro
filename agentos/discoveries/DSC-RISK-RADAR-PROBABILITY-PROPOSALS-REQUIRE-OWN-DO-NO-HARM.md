---
key: RISK-RADAR-PROBABILITY-PROPOSALS-REQUIRE-OWN-DO-NO-HARM
claim: >-
  Risk Radar prob_cal proposals must not inherit acceptance from alert-F1 improvement.
  A probability-changing proposal is eligible only when paired displayed-probability
  Brier is non-worse at H5/H10/H21 on both full and 2020+ history, at least one
  scored cell strictly improves, the scored outcome populations are identical, and
  the H21 Market-State authority partition is unchanged.
falsifier: >-
  Run the probability-guard tests in tests/test_risk_radar_review.py and replay the
  committed pre-2020 OOS candidate through
  engine.risk_radar_backtest._probability_do_no_harm. Any probability-changing
  proposal that passes despite Brier harm, population drift, no strict gain, or an
  authority-partition change falsifies this claim.
so_what: >-
  Future A6 lane-(ii) self-correction may still tune bands/legs under the existing
  alert gate, but prob_cal is no longer a free passenger. The rejected pre-2020
  candidate remains rejected and no live probability changes are authorized by this
  guardrail work.
kind: data
verified_at: 2026-09-23
verified_by: "python3 -m pytest tests/test_risk_radar_review.py -q"
scope:
  - macro
  - grey-deer-risk-intelligence
  - engine/risk_radar_backtest.py
  - engine/risk_radar_review.py
confidence: verified
---
