---
key: RRU-ONE-EXPERIENCE-SEPARATE-TRUTHS
question: >
  Should the cross-region Risk Radar upgrade combine Grey Deer into one user
  experience, or keep the oversized Three Reads block and separate recovery UI?
answer: >
  Use one compact Risk Radar experience across regions, including early repair,
  failed recovery and material change, while preserving separate measured trend,
  hazard, repair, quality and individually authorized policy. Remove the oversized
  standalone homepage block through incumbent PR 6685, not a competing rebuild.
rationale: >
  The Chairman's September 8 commission asks for useful early danger and turning
  points, not more disconnected indicators. Source archaeology found existing
  recovery sensors and grading but no recovery rendering in the custom US dialog,
  plus an already-built compact-homepage PR. Unifying presentation recovers the
  user journey without merging incompatible probabilities, data clocks or authority.
alternatives:
  - option: One weighted universal risk and recovery score
    why_not: It hides disagreement and creates unearned shared authority.
  - option: Keep the separate oversized Grey Deer homepage panel
    why_not: It duplicates explanation while consuming the primary viewport.
  - option: Rebuild risk and recovery engines from scratch
    why_not: Existing sensors, composer and grading owners must be reused.
evidence:
  - Current live Chairman September 8 screenshots/commission and continuation.
  - research/grey_deer/RISK_RADAR_ALL_REGIONS_UPGRADE_FREEZE_2026-09-08.md
  - templates/dashboard.html.j2:12431-12533 at eb9e91961ddc4f3043d0dad358602525e66eccda
  - templates/_risk_radar_card.html.j2:146-250 at the same source pin
  - Macro PR 6684 merged; Macro PR 6685 head 151e88528f5d269fd83945329392a4660a1d42f4 remains held.
affects:
  - "WS:GREY-DEER-RISK-INTELLIGENCE"
  - research/grey_deer/
  - engine/risk_envelope.py
  - templates/_risk_radar_card.html.j2
  - templates/_risk_radar_dlg.html.j2
  - templates/dashboard.html.j2
confidence: high
reversibility: costly
decided_by: ceo-sol
decided_at: 2026-09-08
---

This is a product boundary decision, not a live implementation or policy activation.
It preserves `DEC:RISK-STATE-HAZARD-POLICY-SEPARATION` and
`DEC:REPAIR-IS-ORTHOGONAL-AND-FIRST-CLASS`; no old decision is deleted or globally
superseded. The compact-homepage implementation retains its existing writer/release
owner. New exact visual and statistical constructions need their own bounded packets.

The first implementation dependency is trustworthy input aggregation and clocks.
RRU-1A has a research candidate and discriminating tests, not an installed fix.
A field that is missing, stale or future-dated cannot be silently recast as calm,
and a historical recovery event cannot stand in for present recovery health.

The program is not complete until users can see and understand real hazard, repair,
failed-repair and quality transitions across supported regions, with preserved
counterfactuals and measured false-alarm/missed-recovery cost.
