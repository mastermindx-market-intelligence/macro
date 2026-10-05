---
key: RISK-RADAR-WARNING-PERSISTENCE-GATE
claim: >-
  On the five preregistered Risk Radar reference anchors, old EARLY component
  classifications do not imply a warning persisted into the peak: four anchors
  had caution persist into T0, 2018 had faded to watch, and the broad-market
  gate was closed at all five T0s.
falsifier: >-
  Re-run scripts/research/risk_radar_episode_atlas.py from PR 7586 against the
  receipt-bound inputs and compare warning_path offsets/persistence with
  research/grey_deer/evidence/episode-warning-path-20260921/verification.json.
so_what: >-
  Future risk research must measure actual gated-state persistence and gate
  latency, not cite first_elevated alone as warning quality; no gate/model
  retune follows until false-positive suppression versus escalation delay is
  tested on a broader population.
kind: data
verified_at: 2026-09-21
verified_by: "PR #7586; protocol 31b05b7dda4b; 51 tests passed"
scope:
  - macro
  - grey-deer-risk-intelligence
  - scripts/research/risk_radar_episode_atlas.py
confidence: verified
---
