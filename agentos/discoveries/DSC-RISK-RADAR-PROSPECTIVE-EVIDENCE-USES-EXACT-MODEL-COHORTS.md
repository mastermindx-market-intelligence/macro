---
key: RISK-RADAR-PROSPECTIVE-EVIDENCE-USES-EXACT-MODEL-COHORTS
claim: >-
  New US Risk Radar forward-log rows can accrue genuinely prospective
  same-model probability evidence without changing the existing ledger: each
  nightly first-writer row carries an issue receipt whose model fingerprint
  binds a declared probability/state source bundle and effective calibration.
  The scorecard prospective lens selects only the latest exact
  epoch+model_fingerprint cohort and never backfills historical rows.
falsifier: >-
  Run python3 -m pytest tests/test_risk_radar_audit.py
  tests/test_risk_radar_scorecard.py -q. The claim is falsified if a historical
  row without a receipt enters the prospective cohort, a duplicate date replaces
  the first receipt, a calibration change leaves the fingerprint unchanged, an
  invalid/tardy receipt is admitted, or current_model_validated becomes true.
so_what: >-
  Future Risk Radar probability research can finally distinguish reconstructed
  history from exact issued-model evidence. Model/source changes rotate the
  cohort automatically, while public-page publication timing and promotion
  authority remain explicitly unclaimed.
kind: data
verified_at: 2026-09-23
verified_by: "python3 -m pytest tests/test_risk_radar_audit.py tests/test_risk_radar_scorecard.py -q"
scope:
  - macro
  - grey-deer-risk-intelligence
  - engine/risk_radar_audit.py
  - engine/risk_radar_scorecard.py
confidence: verified
---
