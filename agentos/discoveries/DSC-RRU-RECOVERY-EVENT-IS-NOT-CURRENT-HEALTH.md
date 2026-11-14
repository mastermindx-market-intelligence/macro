---
key: RRU-RECOVERY-EVENT-IS-NOT-CURRENT-HEALTH
claim: >
  The existing recovery morphology can still say V-shape after a historical
  reclaim has relapsed because it reads the event's fired flag, not current health.
falsifier: >
  Run python3 research/grey_deer/RISK_RADAR_INTEGRITY_PROBES_2026_09_08.py; the claim is refuted if
  a completed reclaim followed by closes below its 20-day average is explicitly
  qualified as weakened/failed rather than solely presented as V-shape recovery.
so_what: >
  Preserve the historical firing and grade it, but compose a separate current
  repair-validity read; never erase historical events to make the current UI right.
kind: architecture
verified_at: 2026-09-08
verified_by: >
  research/grey_deer/RISK_RADAR_INTEGRITY_PROBES_2026_09_08.py failed_reclaim_probe;
  RISK_RADAR_INTEGRITY_RESULTS_2026_09_08.json;
  engine/risk_radar_market_catalysts.py:1198-1397 at eb9e91961ddc4f3043d0dad358602525e66eccda.
scope:
  - "WS:GREY-DEER-RISK-INTELLIGENCE"
  - engine/risk_radar_market_catalysts.py
  - templates/_risk_radar_card.html.j2
confidence: verified
---

This is a presentation-semantic gap, not proof that retaining fired=True is an
incorrect historical event record. The controlled fixture explicitly isolates
current health from freshness. New invalidation thresholds require their own
frozen construction; no trade or de-escalation authority is granted here.
