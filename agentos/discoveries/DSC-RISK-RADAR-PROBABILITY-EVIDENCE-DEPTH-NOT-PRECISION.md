---
key: RISK-RADAR-PROBABILITY-EVIDENCE-DEPTH-NOT-PRECISION
claim: >-
  The corrected US Risk Radar displayed probabilities have useful risk-gradient
  information but unequal exact-cell evidence depth. The product now exposes the
  accepted modern historical sample behind the current probability without
  changing the probability itself; thin cells are labeled thin rather than
  presenting noisy realized rates as precision.
falsifier: >-
  Re-run scripts/build_risk_radar_probability_evidence.py from the accepted
  displayed-probability audit, then run the probability-evidence tests and compare
  the current compute() probability fields with an evidence-disabled _drawdown_prob
  call. Any probability/state/gate difference or producer/artifact drift falsifies
  the display-only claim.
so_what: >-
  Future Risk Radar UX may use calibration_evidence for provenance and evidence
  depth only. Do not use it to rank, gate, size, escalate, or retune trades. Any
  probability change still requires a separately preregistered candidate and
  accepted promotion evidence; issued/prospective forecasts remain higher authority.
kind: data
verified_at: 2026-09-22
verified_by: "accepted probability audit PR #7683 + probability-evidence source/browser receipts"
scope:
  - macro
  - grey-deer-risk-intelligence
  - engine/risk_radar.py
  - engine/market_state.py
  - templates/_risk_envelope_band.html.j2
confidence: verified
---
