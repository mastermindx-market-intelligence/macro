---
key: RISK-RADAR-EXPANDING-STATE-PROBABILITY-REFIT-DOES-NOT-PROMOTE
claim: >-
  The preregistered 2010-2025 annual expanding-origin Risk Radar state-only
  probability recalibration does not outperform the shipped static displayed
  probability surface out-of-fold. Candidate Brier is worse at H5, H10 and H21,
  calibration error is worse at all three horizons, and annual wins are only
  7/16, 6/16 and 5/16 respectively. The candidate preserves the H21 authority
  partition but is not promotion-eligible.
falsifier: >-
  Run scripts/research/risk_radar_probability_walkforward.py from method commit
  5b02b000f8162a4233eb0eca74e70a990cde2d71 on the receipt-bound committed
  inputs and compare result SHA-256
  b87080767abb3c15e1dbc9c28be7aa1c1b5cb0b8765f7a65a74880d854ad0e9e.
  The fold surfaces, population hashes, paired Brier deltas, WACE and frozen
  promotion verdict must reproduce.
so_what: >-
  Do not replace the shipped Risk Radar probability surface with this simple
  expanding state-only Jeffreys+PAV rule and do not fit a second candidate to
  the now-observed 2010-2025 folds. Keep the current odds, evidence-depth
  disclosure and probability-specific self-correction guard; new calibration
  evidence should come from a separately preregistered independent method or
  genuinely issued/prospective forecast outcomes.
kind: data
verified_at: 2026-09-23
verified_by: "python3 -m pytest tests/test_risk_radar_probability_walkforward.py -q"
scope:
  - macro
  - grey-deer-risk-intelligence
  - risk-radar-probability-calibration
confidence: verified
---
