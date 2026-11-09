---
key: RISK-RADAR-REPLAY-LIVE-STATE-PARITY-DEFECT
claim: >-
  The historical US Risk Radar state replay did not reproduce the shipped live
  escalation rules: it used a rejected naive two-hot-Tier-A conjunction and a
  permissive Tier-B escalation path instead of validated armed+confirm plus the
  live Tier-B eligibility exclusions. On the 2026-09-21 committed inputs this
  changes 152 of 8,216 known historical state days (1.85%) and 46 of 1,687
  since 2020 (2.73%).
falsifier: >-
  Run the replay/live parity tests in tests/test_risk_radar.py and compare
  engine.risk_radar_backtest.state_series with engine.risk_radar.compute on
  synthetic cases covering (1) two hot scares without a validated arm,
  (2) validated arm plus a second scare at watch, and (3) a measured-zero
  Tier-B firing leg. All must return the same state under an open context gate.
so_what: >-
  Replay-based warning persistence, gate latency, caution persistence, and
  state-ladder calibration results produced before the parity repair must be
  rerun before they can support state/probability/gate changes. Recorded
  forward-probability audits remain a separate evidence class. Do not retune
  live probabilities, bands, weights, gates, policy, or capital authority from
  the invalidated replay buckets.
kind: data
verified_at: 2026-09-21
verified_by: "python3 -m pytest tests/test_risk_radar.py -k replay_matches_live -q"
scope:
  - macro
  - grey-deer-risk-intelligence
  - engine/risk_radar.py
  - engine/risk_radar_backtest.py
  - scripts/research/risk_radar_gate_latency.py
  - scripts/research/risk_radar_caution_persistence.py
  - scripts/research/risk_radar_episode_atlas.py
confidence: verified
---
