---
key: RISK-RADAR-GATE-SELECTIVITY-VS-LATENCY
claim: >-
  On the current historical reconstruction for the 5%-within-21-observation
  Risk Radar target, the shipped broad-market gate materially raises precision
  and cuts fire rate but confirms only 42 of 110 distinct event anchors by T0,
  versus 103 of 110 with a pre-gate loud state.
falsifier: >-
  Re-run scripts/research/risk_radar_gate_latency.py from its accepted source
  revision on the receipt-bound inputs and compare result.json population hashes,
  canonical cross-checks, daily confusion matrices, and event-latency rows.
so_what: >-
  Do not remove the selective loud-alert gate or cite ungated loud state as the
  replacement; instead preserve early deterioration as a quieter display-tier
  warning and require a separate preregistered promotion study before changing
  gate thresholds, probabilities, weights, policy, or capital authority.
kind: data
verified_at: 2026-09-21
verified_by: "python3 scripts/research/risk_radar_gate_latency.py && python3 -m pytest tests/test_risk_radar.py tests/test_risk_radar_scorecard.py tests/test_risk_radar_review.py -q"
scope:
  - macro
  - grey-deer-risk-intelligence
  - engine/risk_radar.py
  - scripts/research/risk_radar_gate_latency.py
confidence: verified
---
