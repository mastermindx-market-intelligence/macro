---
key: MACRO-ALERT-CENTER-MARKET-CHANGES-DESK-EXPERIENCE-FREEZE
question: >
  What product/experience architecture should govern the redesign of Macro's shared
  alerts.html page before Figma and implementation?
answer: >
  Keep Alert Center as the shared Macro Monitor-archetype Market Changes Desk. Its
  identity is a board-day change-log timeline with Now / Explore / History tasks.
  What Matters Now is a deterministic 0-3 lead group inside the timeline, not a
  dashboard hero. Demote the pressure gauge, scoreboard, storyline taxonomy, raw
  priority numbers and repeated methodology from Tier 1. Preserve the existing alert
  IDs, score, source tiers/severity, clocks, coverage, recurrence, validation and push
  authority. Use an in-place evidence inspector; reserve Situation for future grounded
  cross-domain intelligence. Keep private monitoring/delivery in Terminal/F08 owners.
rationale: >
  The current live page makes triage machinery dominate the user job: a sampled 60-row
  board had 55 rows at the same priority 48, 55 minor, 57 watch-tier and 43 recurring,
  while the mobile fold showed no actual alert row. Binding design law assigns alerts.html
  to the monitor archetype, not command_center. Existing source law already distinguishes
  time, coverage, recurrence, validation and source authority correctly; the defect is
  hierarchy and synthesis, not a missing alert backend. The hardened contract was accepted
  by Chris after a deeper review and is now the basis for Figma.
alternatives:
  - option: "Reskin the existing Alert Command Center"
    why_not: >
      Preserves the wrong hierarchy, score compression, story-taxonomy acreage and mobile
      scan tax even if the cards look better.
  - option: "Turn Alert Center into another Command Center"
    why_not: >
      Duplicates start.html's product identity and violates the design-system archetype
      boundary. The alert route's distinctive job is maintaining the change log.
  - option: "Make cross-domain AI Situations the default v1 object"
    why_not: >
      Current clusters and same-source bundles do not earn causal/cross-domain identity.
      Doing so would turn visual design into a false capability claim.
  - option: "Build a new alert/event service for the redesign"
    why_not: >
      Existing alert_triage/time/coverage/publication owners already supply the facts. A
      parallel service would duplicate authority without unlocking the primary user job.
evidence:
  - "research/alert_intelligence/MACRO_ALERTS_MARKET_CHANGES_DESK_EXPERIENCE_FREEZE_20260914.md"
  - "research/alert_intelligence/MACRO_ALERTS_MARKET_CHANGES_DESK_HARDENING_20260914.md"
  - "research/alert_intelligence/MACRO_ALERTS_FIGMA_EXECUTION_BRIEF_20260914.md"
  - "docs/DESIGN_DOCTRINE.md — user-first progressive disclosure"
  - "research/MASTER_PRODUCT_DESIGN_SYSTEM_V1.md — alerts.html is monitor archetype"
  - "engine/alert_triage.py and engine/alert_time.py at Macro 2e972811e82a56928e5f4871300ecb91daf0bed3"
affects:
  - macro
  - alerts.html
  - alert-center-v2
confidence: high
reversibility: medium
decided_by: "Chairman Chris approval; product/architecture freeze by Sol"
decided_at: 2026-09-14
---

## Scope

This decision freezes the user-facing target for design. It changes no runtime or source authority.
Current capability state for the redesign remains **SPEC_ONLY** until Figma and implementation move
through their separate acceptance gates.

## Exact experience

- **Now:** board-day timeline with 0-3 deterministic lead observations, then ordinary changes.
- **Explore:** complete accessible observation population with search/filters.
- **History:** actual observed firings/corrections, never interpolated persistence.
- **Inspector:** what changed, why it matters, original evidence, optional source-supported current
  read, context, ranking/validation receipt, observed history and canonical source destination.
- **Coverage:** blocking evidence loss withdraws whole-market synthesis but preserves usable surviving
  evidence.
- **Related observations:** same-source/exact-subject grouping only; explicitly not independent confirmation.

Lead eligibility stays the accepted v1 display rule: known event time, canonical fresh window
(`age_days <= 2`), fresh `act`, or fresh post-governance major/critical `watch`; no `context`, no
future event, no model promotion. Max three; no padding.

## No-rebuild / no-false-capability law

The redesign does not create a new alert score, event identity, persistence claim, database, reader,
queue, scheduler or private notification owner. Prophet and News do not appear as live shared Macro
alert sources until their canonical owner contracts actually support that integration. Personal
holdings/watchlist/thesis relevance, read/archive, quiet hours, email preferences and delivery stay
outside shared static Macro HTML.

The existing Terminal Figma work remains a separate preserved product asset and must not be renamed
or overwritten to satisfy this Macro program.

## Exact continuation

Next action is Figma execution under
`research/alert_intelligence/MACRO_ALERTS_FIGMA_EXECUTION_BRIEF_20260914.md`. Create/reconcile a
clearly separate target named **MastermindX — Macro Alert Center — Market Changes Desk**, then build
Now complete/quiet/partial states and the evidence inspector before Explore/History. If the Figma
connection cannot create a separate file, stop at that real capability boundary rather than silently
repurposing a Terminal file.
