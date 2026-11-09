---
key: RISK-RADAR-HISTORICAL-ROWS-DO-NOT-SATISFY-PROSPECTIVE-READINESS
claim: >-
  The committed US Risk Radar forward ledger at method freeze contains 52 historical
  rows and zero receipt-bearing exact-model prospective rows. All 52 are excluded
  from the new prospective cohort as missing_issue_receipt; validation readiness is
  not_started, promotion_review_eligible=false, current_model_validated=false, and
  public_validation_ready=false.
falsifier: >-
  On method commit 75d21ff6b478687971126a8790cda825bdd683f7, run
  engine.risk_radar_scorecard.probability_audit over the committed
  data/risk_radar/forward_log.jsonl with today=2026-09-24. The claim is falsified
  if any historical row enters the prospective cohort or readiness is not
  not_started.
so_what: >-
  Prospective evidence starts only after the receipt contract ships. Historical
  accuracy may remain descriptive, but it cannot be relabeled as exact current-model
  validation and cannot satisfy the frozen readiness bar.
kind: data
verified_at: 2026-09-24
verified_by: "python3 -m pytest tests/test_risk_radar_scorecard.py -q"
scope:
  - macro
  - grey-deer-risk-intelligence
  - risk-radar-probability-validation
confidence: verified
---
