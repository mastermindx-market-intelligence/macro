---
key: OPTIONS-VOLATILITY-OWNER-AND-SAVE-BOUNDARY-20261109
claim: >
  At Terminal d7a83d3348a4fcb762d93221f19c4e94cbe4505e the existing volatility helper and panel already own tenor/skew calculations and selected-expiry selection, while VolView supplies no onOpenResearch callback for standalone volatility saving.
falsifier: >
  Inspect terminal/lib/volTenorComparison.ts, terminal/components/vol/VolComparePanel.tsx and VolView.tsx at that pin or a later qualified implementation; prove a standalone save with an admitted exact evidence object and operation/revision readback.
so_what: >
  Reuse the incumbent calculations and selected-expiry fixture, keep standalone Flow/Volatility Save unavailable until its exact object is admitted, and extend the existing Investigation owner instead of inventing another calculator or save service.
kind: architecture
verified_at: 2026-11-09
verified_by: >
  Terminal exact-pin reads: volTenorComparison.ts blob da5b3aafc658ede5cfa67d5ec53fdb43e771b189, VolComparePanel.tsx blob c08bc6e61c4cd97f81018bc9634ac06f355350dc, fixture blob c9c99492fbe3393906061823d7a3ec5c11b2a3aa, VolView.tsx and OPTIONS_R1_W2_FREEZE.md.
scope:
  - mastermind-terminal/terminal/lib/volTenorComparison.ts
  - mastermind-terminal/terminal/components/vol/VolComparePanel.tsx
  - mastermind-terminal/terminal/components/vol/VolView.tsx
  - mastermind-terminal/terminal/e2e/fixtures/options-r1-w3b-vol.json
confidence: verified
---

# Reuse current calculation; do not infer persistence

Canonical repository: mastermindx-market-intelligence/mastermind-terminal. Historical build-pending prose in Macro does not override later implementation at the inspected pin.

Constant tenor interpolates total variance with calendar DTE. Skew interpolates IV in actual strike, using puts at/below reference and calls above in Auto. The panel prefers a supplied selected-expiry smile. The 23 October/2D fixture therefore yields95%40.8, ATM36.9 and105%34.0, with unsupported wings blank. The old displayed30D32.4 does not follow that selection or the inspected30D fixture.

The current Paper specimen is aligned to that source, including $228.38–$243.90 expected-move rounding. Source date, spot clock, one-day-band clock and reference strike retain separate meanings.

The admitted chart Investigation entry creates a ready exposure-chart object and matching sector origin. It does not establish a standalone Flow-print or Volatility-snapshot save. Reuse applyInvestigationRevision/apply_investigation_revision_v2, operation_id, expected_revision, readInvestigation and readInvestigationOperation under terminal.options_exposure. A callback or focused expiry selector is not persistence.

This discovery records source and design reconciliation, not live-feed, save, watch or production acceptance. See [R2–R5](../../research/design_candidates/paper_audit_20261108/followup/SOURCE_RULINGS.md) and build slices F03/F09/F10.
