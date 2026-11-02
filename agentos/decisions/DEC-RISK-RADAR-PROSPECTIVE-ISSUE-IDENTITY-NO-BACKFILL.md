---
key: RISK-RADAR-PROSPECTIVE-ISSUE-IDENTITY-NO-BACKFILL
question: >
  How does the US Risk Radar turn its existing forward ledger into genuinely
  prospective model evidence without rewriting historical rows or creating a
  second validation ledger?
answer: >
  Keep data/risk_radar/forward_log.jsonl as the sole US Risk Radar forward
  ledger. From the prospective epoch onward, the nightly first-writer row carries
  a forecast_issue receipt binding the ledger issue clock to a declared
  probability/state source bundle (risk_radar + indicator/calendar/store/config
  helpers) and the effective calibration SHA-256; their canonical digest is the
  model_fingerprint. Historical rows are never backfilled.
  The scorecard prospective lens may evaluate only rows from the latest exact
  epoch+model_fingerprint cohort. It may verify forward-ledger issue timing, but
  it may not claim public-page publication timing or set current_model_validated
  true without a separate accepted promotion law.
rationale: >
  The existing issued-probability audit correctly refuses current-model
  validation because historical rows do not prove homogeneous model identity or
  first-publication timing. Retrospective state-only refits also failed both a
  fixed 2020+ holdout and a preregistered 2010-2025 expanding-origin walk-forward.
  The highest-authority next evidence therefore comes from future issued calls.
  Adding provenance to the incumbent first-writer ledger preserves one lifecycle
  and lets model changes split cohorts automatically instead of silently mixing
  incompatible forecasts.
alternatives:
  - option: Backfill historical model fingerprints from current code or git history
    why_not: >
      That would convert reconstruction into prospective evidence and could assign
      rows to a model that was not actually executing when the row was first
      written.
  - option: Create a second probability-validation ledger
    why_not: >
      Duplicate ledgers would create competing issue clocks and violate the
      existing forward-log ownership/lifecycle law.
  - option: Treat logged_at on all historical rows as verified publication time
    why_not: >
      logged_at proves only the old ledger receipt clock; it does not prove
      public-page first publication or homogeneous model identity.
  - option: Mark the current model validated once the first prospective rows mature
    why_not: >
      Sample maturity is evidence availability, not a validation threshold. A
      separate preregistered promotion law must own any future validation claim.
evidence:
  - "engine/risk_radar_audit.py — sole nightly first-writer forward ledger"
  - "engine/risk_radar_scorecard.py — historical probability audit keeps publication_timing_verified=false and current_model_validated=false"
  - "PR #7782 — probability proposals require independent Brier + authority do-no-harm"
  - "PR #7801 — expanding-origin state-only probability refit is not promotion-eligible"
affects:
  - "WS:GREY-DEER-RISK-INTELLIGENCE"
  - "engine/risk_radar_audit.py"
  - "engine/risk_radar_scorecard.py"
  - "data/risk_radar/forward_log.jsonl"
confidence: high
reversibility: costly
decided_by: ceo-sol
decided_at: 2026-09-23
---

## Operational boundary

The receipt is additive and fail-soft. If model identity cannot be generated, the
existing forward row may still be written, but that row is excluded from the
prospective cohort. Off-lane renders remain read-only.

## What would reopen this

A new accepted source of stronger issue-time provenance or a separately ratified
model-validation/promotion protocol may extend the prospective lens. Neither
retrospective convenience nor UI copy pressure authorizes backfill or validation.
