---
key: TERMINAL-TACTICAL-MINUTE-EVIDENCE-CLASS
question: What evidence class may the existing Radar minute seam provide to Terminal Tactical Intelligence?
answer: >
  Admit the current VendorMinuteReader only as a corrected-history minute-path source for retrospective ambiguity
  refinement. Do not classify its historical rows as "known at the time" and do not classify its current-session
  reads as production-live freshness evidence until separate source-arrival proof exists. MinuteBar.knowable_at is
  the mathematical aggregate-close clock, not a vendor delivery or acquisition receipt.
rationale: >
  VendorMinuteReader requests current adjusted=true aggregates and returns a SessionTape whose vintage is only
  polygon_minute_aggs:<session>. It records neither acquisition time nor per-bar source availability/correction
  identity, and adjusted history can be retroactively rescaled. Its completed-session cache persists derived 4H
  buckets with pack/substrate adjustment stamps, not raw minute observations or their historical availability.
  Therefore it can truthfully refine order inside corrected historical bars, but cannot reconstruct what a live
  decision actually knew. The entitlement manifest proves API/WS access, not minute-arrival latency.
alternatives:
- option: Treat MinuteBar start+60 seconds as historical known-at
  why_not: That is when the aggregate can mathematically close, not proof the vendor delivered that exact observation then.
- option: Treat the 2026-08-08 entitlement probe as current live-freshness proof
  why_not: Entitlement and auth/subscribe success do not establish RTH data-frame latency or current source freshness.
- option: Build a new raw-minute archive for TTI now
  why_not: Radar already owns the bounded minute acquisition seam; a duplicate store would create a second data plane.
evidence:
- 'Macro main c3d4b81acee75081138c9e40aba8d7589aa341e3: engine/entry_radar/vendor_minutes.py adjusted=true; SessionTape vintage polygon_minute_aggs:<session>; raw minutes not durably receipted.'
- 'Macro main c3d4b81acee75081138c9e40aba8d7589aa341e3: challengers.MinuteBar.knowable_at = start + 60 seconds.'
- 'data/massive/capability_manifest.json probe 2026-08-08: minute/second aggregates, stock trades/quotes and realtime stock WS entitled; WS proof carried auth+subscribe but zero data frames because that probe ran market-closed.'
- 'Current research host check 2026-09-17: PolygonOptions().enabled() == false on that host. This is host-local and is not an entitlement downgrade.'
- 'Macro #7275 resolver explicitly carries research_resolution_only authority; current-head hardening adds source_clock_proven=false / availability_time_unproven.'
affects:
- WS:TERMINAL-TACTICAL-INTELLIGENCE
- WS:LIVE-ENTRY-RADAR
- engine/entry_radar/vendor_minutes.py
- engine/entry_radar/minute_resolution.py
confidence: high
reversibility: easy
decided_by: ceo-sol
decided_at: '2026-09-17'
---

For R1-B corrected-history evaluation, an accepted resolver may refine an enumerated same-five-minute ambiguity only if the requested minute window is complete and source-qualified under this evidence class. A prospective/live promotion requires a new source receipt measuring current-session availability/freshness on the canonical path; historical as-observed replay requires genuine archived availability receipts rather than inferred clocks.
