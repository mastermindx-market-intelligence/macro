---
key: RIC-PCE-RELEASE-BRIDGE
question: How should Mastermind use CPI and PPI detail to improve the PCE outlook, assessment and release calendar?
answer: Extend the existing Rates/Inflation and Release Radar families with release-dependency context, a separately identified component PCE shadow, and correction-safe assessment and first-print reconciliation; do not build another calendar or forecasting platform.
rationale: The useful capability is explaining incremental evidence and the resulting change in outlook. Existing event, publication, forecast, actual, policy-context and product families already own the needed concepts. A distinct method-versioned candidate preserves the current model while allowing incremental PPI value to be tested rather than assumed.
alternatives:
  - option: Treat fixed monthly PCE thresholds as permanent Fed-action or trade rules.
    why_not: A conditional policy interpretation is not a calibrated decision probability; the post does not establish predictive or trading authority.
  - option: Build a standalone PCE calendar, watcher and forecasting store.
    why_not: This duplicates existing canonical event, source, ledger and product ownership and makes correction and assessment consistency worse.
  - option: Modify the current broad-lag PCE model in place.
    why_not: That would conflate existing forecast history with an unadmitted component method and prevent clean benchmark and method-epoch comparisons.
  - option: Delay all useful product context until every component mapping and forecast test is complete.
    why_not: An honest source-dependency and measurement-risk view is independently useful and can ship descriptively without numerical or trading authority.
evidence:
  - Current Chairman directive on 2026-09-10 to take leadership of the proposal; Macro issue 7030 records the accepted outcome and scoped continuation.
  - Macro ea9ab6da455d8a31ec9a5323a37cb06bcd271b0f engine/release_targets_v11.py uses broad PCE and inflation/PPI lags rather than the proposed detailed component map.
  - Macro ea9ab6da455d8a31ec9a5323a37cb06bcd271b0f scripts/watch_release_publications.py separates publication facts from the nightly research writer.
  - Macro PR 499 and current scripts/build_policy_watch.py retain an existing catalyst spine; PR 7017 currently changes that builder and its template.
  - research/release_forecast/PCE_RELEASE_BRIDGE_ARCHITECTURE_2026-09-10.md contains primary references, the unresolved dental source conflict, methodology-vintage requirements, and the R0 through P4 sequence.
affects:
  - WS:RATES-INFLATION-COMMAND
  - rates-inflation-command
  - engine/release_*
  - research/release_forecast/*
confidence: high
reversibility: easy
decided_by: ceo-sol
decided_at: 2026-09-10
review_by: 2026-09-30
---

# PCE Release Bridge: outcome accepted, numerical method not yet admitted

CEO Sol owns product thesis, source and intelligence architecture, decomposition, integration review and final acceptance for `release-radar-pce-bridge-20260910-sol-001`, under the existing WS:RATES-INFLATION-COMMAND. This does not take ownership of the workstream's other active children.

The canonical detailed architecture is `research/release_forecast/PCE_RELEASE_BRIDGE_ARCHITECTURE_2026-09-10.md`; implementation and transport evidence is projected in Macro #7030. This decision creates no Executive Job, worker identity, placement, queue or runtime authority.

## Frozen boundaries

Preserve existing event identities, publication and correction owners, forecast and score histories, selected-model semantics, policy catalyst context and product consumers. Use an explicitly identified derived PCE nowcast, not an official observation. Observed component coverage, modeled remainder and empirical calibration remain different concepts. A model may explain accepted structured facts but may not invent missing values, weights, times or policy probabilities.

Current PCE model outputs and history remain unchanged while a new component method is researched and tested. No CPI/PPI relative-importance weights may stand in for PCE expenditure shares. Missing components are not silently dropped and renormalized. Methodology publication vintage is distinct from economic reference period, and old forecasts remain immutable across method changes.

The existing nightly-only forward-ledger writer is unchanged. A future intraday recompute requires explicit accepted extension of that owner, not an alternative timer or watcher. Shared CPI/PPI-derived information is not counted as multiple independent confirmations.

## What is not decided or delivered

The exact eight-row primary-source map is not admitted. The BEA-handbook versus BLS-factsheet dental mapping discrepancy remains unresolved, and the announced portfolio/legal/software changes require exact method and vintage confirmation. No complete economic-basket coverage, numerical forecast, calibrated uncertainty, empirical advantage or production capability is claimed.

No new implementation worker has been bound or started. F1, A1 and neighboring Macro Command and Policy Watch source owners are preserved; their historical acknowledgments and old seam releases do not authorize a new writer here. This records-only decision is SPEC_ONLY, not a release.

## Exact continuation

Place one eligible Terra researcher through the existing capacity owner for the architecture's bounded eight-row R0 source-method review. That read-only work can proceed without waiting for the shared producer/UI source holds. Sol accepts each source disposition and separately freezes an owner-compatible P1 context vertical, then routes implementation. Sol retains final acceptance and requires real producer-to-machine-to-browser proof.
