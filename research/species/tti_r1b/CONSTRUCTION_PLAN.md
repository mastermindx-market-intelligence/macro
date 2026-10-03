# R1-B v4 synthetic construction implementation plan

> Execute inline with superpowers:executing-plans and test-driven-development.

**Goal:** Turn the frozen v4 fresh-low/reclaim rules into a runnable causal construction and explanation consumer without opening empirical outcomes.
**Architecture:** Pure per-session in-memory construction using the existing exchange calendar and standard indexed OHLCV frames. No production registry/event integration. A synthetic-only CLI demonstrates forming, confirmation, continuation, expiry and missing-data behavior.
**Tech stack:** Existing Python/pandas/pytest; no additional dependencies.
**Spec:** research/species/TTI_R1B_V4_PREREG.md, config_v4.json, V4_FREEZE_RECEIPT.json.
**Authority:** Chairman continuing commission; #7274 comment 5745472291 narrows the earlier all-code scheduling hold to its actual empirical/shared-source boundary.

## Global constraints
- Keep v4 prereg/config bytes unchanged (config SHA256 24b5a89f8df9c441160f1162c0f08d62796e842e29fff3c55766160fe388bc19).
- No TrialLedger writes, historical input reads, outcome calculations, ranks, alerts, probabilities or orders.
- No dependency on unaccepted R1-A code, no new provider/session/calendar/store.
- Inputs are completed five-minute bars; candidate, confirmation and future eligible-entry times stay distinct.
- Entry time = actual decision/confirmation + one full five-minute latency interval; no price is claimed filled.
- Prior session/ATR/price basis must qualify; unavailable never becomes negative.

## Review focus
Future data must not rewrite an earlier event; overlapping anchors must be ordered by actual confirmation time; an expired earlier anchor must not consume a later selector; duplicate/missing bars preserve earlier events; candidate and episode lows stay separate.

## Task 1 — Causal construction
Files: create engine/entry_radar/tactical_exhaustion.py; extend existing CI-owned tests/test_entry_radar_w3_detectors.py.
Interface: construct_session(frame, symbol, session, prior_session, prior_close, prior_atr, asof, config_bytes, price_basis='adjusted') -> JSON-compatible report.
- [x] RED tests for candidate geometry, strict/equal low, completed cutoff, confirmation race and latency.
- [x] Implement exact config-hash binding and sequential per-bar construction, selectors deduplicated by actual event time.
- [x] Add fail-closed tests for gaps, invalid prices, zero volume, duplicates, wrong basis, stale prior inputs, off-grid and early-close sessions.
- [x] Add future-mutation and independent-selector controls; run full existing detector suite.

## Task 2 — Executable explanation consumer
File: scripts/research/terminal_tactical_r1b_preview.py; test via existing detector suite.
- [x] RED subprocess test of synthetic-only JSON/Markdown rendering.
- [x] Implement literal synthetic examples only, explicit synthetic/no-live-authority output.
- [x] Show candidate/confirmation/entry timing, frozen reclaim/invalidation and unresolved reasons; no market input option.

## Task 3 — Evidence and publication
- [x] Run all focused and relevant Radar tests; verify prereg/config and shared ledger unchanged.
- [x] Preserve synthetic report and verification receipt (not an empirical result).
- [ ] Commit/push same #7274 branch; update its description and Agent OS current state.
- [ ] Keep empirical/review/merge/production gates held; do not restart completed R1-A experiments or claim a reviewed edge.
