---
key: RISK-RADAR-POST-PARITY-EVIDENCE-REALIGNMENT
claim: >-
  After replay/live parity repair #7632, the corrected modern US Risk Radar
  state ladder is point-monotonic at H5/H10/H21; H21 elevated is 30.3% (n=33)
  rather than the stale replay's 11.1% (n=36), while risk-off is 43.8% (n=224).
  The broad-market gate remains selective (2020+ H21 precision 42.0%, recall
  36.7%, fire-rate 15.4%), and five-session caution persistence remains too
  common for a new alert (68.8% modern fire-rate despite 1.36x lift).
falsifier: >-
  Re-run the four studies under
  research/grey_deer/RISK_RADAR_REPLAY_PARITY_RERUN_PREREG_2026-09-21.md
  using the receipt-bound inputs and merged parity transition. Population hashes,
  state cells, gate confusion matrices, and fixed-episode paths must reproduce
  the corrected receipts.
so_what: >-
  Preserve caution as risk-building context, elevated as a higher-risk but
  evidence-thin transition tier, and risk-off as the strongest high-risk tier.
  Do not create a persistence alert or retune live probabilities from these
  reconstructed buckets. Next evaluate the complete displayed probability
  surface (state plus conjunction) under the corrected replay, with a separately
  frozen protocol and issued/prospective evidence kept distinct.
kind: data
verified_at: 2026-09-21
verified_by: "post-#7632 replay rerun protocol e9ff3d234df1; corrected result receipts"
scope:
  - macro
  - grey-deer-risk-intelligence
  - engine/risk_radar.py
  - engine/risk_radar_backtest.py
  - risk-radar-research
confidence: verified
---
