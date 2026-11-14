---
key: RRU-CURRENT-RADAR-CAN-MASK-MISSING-OBSERVATIONS
claim: >
  International radar compute can emit calm for an all-null composite or present
  a prior score under the latest benchmark date without exposing the score age.
falsifier: >
  Run python3 research/grey_deer/RISK_RADAR_INTEGRITY_PROBES_2026_09_08.py; the claim is refuted
  if actual compute returns a current unavailable state for the all-null case
  and exposes or refuses the prior score when the latest composite row is missing.
so_what: >
  Fix source-to-consumer null and observation-clock semantics, not just private
  band labels; absence must not become current calm or refresh old evidence.
kind: data
verified_at: 2026-09-08
verified_by: >
  research/grey_deer/RISK_RADAR_INTEGRITY_PROBES_2026_09_08.py;
  RISK_RADAR_INTEGRITY_RESULTS_2026_09_08.json;
  engine/risk_radar_intl.py:177-195,315-410 at eb9e91961ddc4f3043d0dad358602525e66eccda.
scope:
  - "WS:GREY-DEER-RISK-INTELLIGENCE"
  - engine/risk_radar_intl.py
  - engine/market_state.py
confidence: verified
---

Controlled fixtures call the actual public compute function with a valid benchmark
and all-null or final-null composite series. These demonstrate reachable function
behavior, not a measured production incidence rate. Fixing the arithmetic alone
will not close these separate current-reading defects.
