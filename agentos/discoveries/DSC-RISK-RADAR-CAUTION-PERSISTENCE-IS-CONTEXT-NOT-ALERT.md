---
key: RISK-RADAR-CAUTION-PERSISTENCE-IS-CONTEXT-NOT-ALERT
claim: >-
  Five consecutive sessions of the shipped gated caution-or-higher state modestly
  increases historical 5%-within-21-observation event separation, but it is far
  too common to serve as a new prominent alert: since 2020 lift is 1.29x while
  the condition is active on 73.3% of eligible sessions; full-history lift is
  1.15x with a 63.4% fire rate.
falsifier: >-
  Re-run scripts/research/risk_radar_caution_persistence.py from its accepted
  revision on the receipt-bound inputs and compare daily population fingerprints,
  confusion matrices, and the fixed five-session construction.
so_what: >-
  Do not turn five-session caution persistence into a new headline warning,
  score escalation, probability adjustment, or capital rule. If surfaced in
  Risk Radar, use it only as neutral duration context inside detail.
kind: data
verified_at: 2026-09-21
verified_by: "python3 -m pytest tests/test_risk_radar.py tests/test_risk_radar_scorecard.py tests/test_risk_radar_review.py -q"
scope:
  - macro
  - grey-deer-risk-intelligence
  - scripts/research/risk_radar_caution_persistence.py
confidence: verified
---
