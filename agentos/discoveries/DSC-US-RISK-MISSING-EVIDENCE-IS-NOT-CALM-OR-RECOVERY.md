---
key: US-RISK-MISSING-EVIDENCE-IS-NOT-CALM-OR-RECOVERY
claim: >-
  On the current US Risk Radar, a numeric legacy sub-score whose structurally
  eligible evidence is absent must be presented as UNAVAILABLE rather than calm,
  while preserving the underlying score/band arithmetic; and a scare missing on
  the current observation must not reuse its last non-null historical value to
  narrate warm, faded or receding risk.
falsifier: >-
  Run python3 -m pytest tests/test_risk_reading_integrity.py
  tests/test_risk_radar.py tests/test_risk_radar_review.py
  tests/test_risk_radar_scorecard.py tests/test_macro_risk_dialog.py -q.
  The claim is falsified if eligible-zero no longer renders calm, an ineligible
  reading renders a numeric bar/band, a current NaN enters warm/faded/receding
  narration, or numerical/state/probability/authority fields change.
so_what: >-
  Risk Detail no longer converts absence into reassurance, and its recovery
  language cannot quietly borrow yesterday's observation. This is a fresh
  current-main extraction of the two still-valid safety semantics from closed
  legacy PR #7236; do not revive that monolith or its obsolete presentation stack.
kind: data
verified_at: 2026-09-25
verified_by: "python3 -m pytest tests/test_risk_radar_review.py tests/test_macro_risk_dialog.py -q"
scope:
  - macro
  - grey-deer-risk-intelligence
  - engine/risk_radar.py
  - templates/dashboard.html.j2
confidence: verified
---
