---
key: RISK-RADAR-STATE-LADDER-IS-COARSE-NOT-FIVE-CALIBRATED-BINS
claim: >-
  The current reconstructed US Risk Radar ladder separates downside risk well
  as coarse zones, but not as five independently calibrated probability bins:
  caution is near base risk, risk-off is strongly elevated, and the modern
  elevated cell is thin (H21 n=36) with a wide interval and a point estimate
  below caution.
falsifier: >-
  Re-run scripts/research/risk_radar_state_ladder_calibration.py from its
  accepted revision on the receipt-bound inputs and compare population hashes,
  state cells, moving-block intervals, and canonical state_accuracy parity.
so_what: >-
  Preserve the current plain-language ordering but do not present the elevated
  state's configured probability as high-confidence calibration from reconstructed
  history alone. Keep caution as risk-building context and reserve strongest
  wording for risk-off; any probability retune needs a separate preregistration.
kind: data
verified_at: 2026-09-21
verified_by: "python3 scripts/research/risk_radar_state_ladder_calibration.py && python3 -m pytest tests/test_risk_radar.py tests/test_risk_radar_review.py tests/test_risk_radar_scorecard.py -q"
scope:
  - macro
  - grey-deer-risk-intelligence
  - engine/risk_radar.py
  - scripts/research/risk_radar_state_ladder_calibration.py
confidence: verified
---
