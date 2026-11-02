---
key: PROPHET-US-D11-RELEASE-PATH-INCUMBENT-CONTROLS
question: >
  How are Prophet US release, entitlement and rollback needs governed without building a new
  feature-flag, release-control or shadow-run plane? (R6 decision D11)
answer: >
  D11 is resolved by incumbent controls only. A new feature-flag, release-control or
  shadow-run plane is not built for Prophet US. Every R6 release need maps by KIND onto an
  existing control with an owner: new display panels use `config.yml: us_board_gate.panels`,
  `panel_preview_rows`, and same-PR `premium.enforced_early` plus plans-page disclosure; new
  B4 policy versions ship by merge as in-code frozen constants and fail closed on version
  mismatch; live-plane units remain STAGED-NOT-ARMED behind explicit operator controls and
  documented kill switches; served bytes move through path-filtered render jobs, committed
  `site/` bytes, a VPS pull of at most three minutes, and validated Caddy changes. Entitled
  user proof requires a real authenticated `ux-evidence` session; anonymous capture and
  synthetic login are never substituted.
rationale: >
  The release-path census found no incumbent `feature_flag` or `release_control` mechanism
  in the tree, but it did find eleven existing controls with owners sufficient to cover the
  release needs by kind. Reusing those controls avoids a second release authority while
  keeping display rollout, policy versioning, live-plane arming, rollback, and entitlement
  evidence under their existing disciplines.
alternatives:
  - option: Build a new feature-flag or release-control plane for Prophet US.
    why_not: It duplicates incumbent controls and creates a second release authority without an established release need.
  - option: Add a runtime toggle to select B4 policy behavior.
    why_not: B05/B12 must ship frozen constants; a shadow read is at most a separate display-tier artifact with its own validity discipline, never a switch that selects the authoritative policy.
  - option: Persist `ENTRY_OPEN` or create a future B4 cache without D01 validity discipline.
    why_not: No producer persists `ENTRY_OPEN` today; introducing that hazard is forbidden, and any future cache must use next-session validity, lineage discipline, and the authenticated path.
  - option: Treat synthetic login or anonymous capture as entitled-user proof.
    why_not: The B20 acceptance gate requires a real authenticated `ux-evidence` run; `capture_page_evidence.py` is anonymous-only by law.
evidence:
  - research/prophet_v4/r6_program/wave0/D11_RELEASE_PATH_CENSUS_2026-09-23.md
  - research/prophet_v4/r6_program/rulings/SEAT_RULING_R6-D11-01_2026-09-23.md
  - Macro PR 7822 (merged 22ac4fa0), carrying the census and ruling after lane PR 7821 was closed as superseded
affects:
  - WS:PROPHET-US-V4-RECOVERY
confidence: high
reversibility: costly
decided_by: coo-fable
decided_at: 2026-09-23
---

## Scope

Resolves R6 decision D11 for Prophet US release, entitlement, and rollback paths. Build
units may ship STAGED-NOT-ARMED under the mapped incumbent controls.

Unresolved: live-plane go-live is an EXACT_HUMAN_GATE requiring the operator to set
`ENTRY_RADAR_LIVE_ENABLE=1`; the seat never sets that environment arm or flips
`PAYWALL_ENABLED`. D11-a through D11-c remain open non-blockers.

## What this decision does not do

It does not authorize live-plane go-live, a paywall flip, production DDL, a new release
plane, or a persisted `ENTRY_OPEN` artifact. It does not make rollback reverse forward
ledgers, grades, origination receipts, or user state: a revert changes only what a NEW card
says, while those ledgers remain irreversible.
