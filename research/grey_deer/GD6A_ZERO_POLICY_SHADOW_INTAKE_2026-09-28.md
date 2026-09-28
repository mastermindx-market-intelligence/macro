# GD-6A R5: existing Prophet build and publication integration

**BUILT_NOT_PROVEN / PARTIAL. MISSION_COMPLETE:false. PR #8141 stays DRAFT/HOLD-FOR-SOL until required release evidence is available.**

Operation `gd6a-us-shadow-intake-20260928-sol-001`, same branch
`claude/gd6a-us-shadow-intake-20260928`; R5 begins from
`56a4c5b83195e4a11445a481543499e6c63b23a8`.

## Current review decision

The current Chairman explicitly permits self-audit instead of waiting for an independent reviewer. R5 uses author/Sol source audit and discriminating tests. This is not called independent review. It removes the reviewer-placement dependency for this software slice, not financial-policy promotion, required CI, deployment authorization or ordinary production proof. The current exposed Executive route is readonly and its state call returned incomplete installed Macro objects. No reviewer, worker or watcher was dispatched.

## Actual product-path change

The previous component had only a qualification CLI. `scripts/build_prophet.py` now calls its additive shadow writer after native plan/rank/management computations and before publishing its existing index. The writer reuses the exact board already frozen by `_freeze_origination_source_board`; it never rereads the mutable current board. The same existing JSON snapshot helper freezes the risk envelope in the existing content-addressed `data/prophet/origination_sources/` root. It does not create another store, collector or ledger.

The generated `site/prophet/market_eligibility.json` is accompanied by an additive `market_eligibility_shadow` index receipt carrying its raw SHA256, sidecar identity, source snapshots, decision/window clocks, row count and data status. This is a server-side binding, not a browser-generated eligibility decision. Existing full plan-book protection and the public-R2 health-only split remain unchanged.

The existing `scripts/ci/daily_engine_prophet_checkpoint.sh` accepts exactly the new sidecar filename. All existing race checks, manifest bounds and output ownership remain; no new workflow/publisher. The existing synapse-read-gate test command gains the new publication test, with every prior suite retained.

## Source truth and failure behavior

The board's price-through session is distinct from its wrapper publication date. A newer wrapper cannot refresh old prices. A mismatched price session yields one UNAVAILABLE disposition per intact row; an unreadable board, malformed/future wrapper or wrong digest still refuses. This explicitly corrects the R4 test that conflated wrapper-date equality with the source-session contract. It does not widen eligibility.

The native `lib.nyse_calendar.expected_last_session` and its next-session/settle boundary determine the window. No new calendar or arbitrary hour/day TTL is introduced. This remains an EOD-source shadow window, not an assertion of intraday market-risk freshness. Subsecond observation time is retained so newly produced evidence is not falsely rejected by a rounded-down decision clock.

A native FRESH coverage summary with missing/unmapped hazard interpretation or absent measured-state interpretation is UNAVAILABLE. Zero policies is not missing risk knowledge. A source gap can still publish an unavailable shadow artifact, retaining every board row. On snapshot/artifact failure the index publishes an explicit unavailable receipt with **no artifact path**: it does not point at an old apparently healthy file. Consumers must follow the exact index/hash binding, not fetch an unbound latest sidecar.

The existing snapshot helper retains its own filesystem contract; the prior R4 no-follow/nonblocking CLI hardening is not asserted to cover every ancestor or every native builder read.

## No activation

Current Risk Envelope v0 emits zero policies and episodes. No synthetic active policy is added. AVAILABLE/ELIGIBLE continues to mean `NO_MARKET_POLICY_CONSTRAINT_NOT_BUY_PERMISSION`. All eight action flags remain false. Rank, admission, B4 entry truth, original plans, personal holdings, sizing, buy alerts and trading are unchanged. Re-entry, reductions and live recommendation restrictions remain separately qualified native-policy capabilities. No numerical study, outcome, fit or predictive-performance claim is introduced.

## Executed qualification

Python3.12.13: **88 tests passed, 58 subtests passed**. This includes all existing GD-6A tests, 18 new publication tests, and the existing full `build_prophet.main` smoke now asserting the new receipt. The main smoke uses its original synthetic price/management fixtures; it is not a production-market full-nightly run. Full native modules execute; 61 imported source files were copied from exact matching source blobs into an isolated fixture, not a shared checkout.

Command:

```sh
python3.12 -m pytest tests/test_prophet_market_eligibility.py tests/test_prophet_market_eligibility_native.py tests/test_prophet_market_eligibility_publication.py tests/test_prophet_bridge.py::test_end_to_end_smoke --basetemp <owned-test-directory> -q
```

Final log SHA256 `949c61ea2ffd3d00df9c033dc3d13f8a3ead82ebcbe47748829745378472d862`.

Two changed-path fault controls failed for the intended assertions: deleting the actual builder call fails the main smoke; removing the exact checkpoint allowlist addition fails the executed native shell-case test. Originals were restored byte-for-byte. The shell test is the actual allowlist fragment, not a full remote commit/publish run. An initial default-pytest invocation emitted unrelated stale temporary-directory cleanup warnings; subsequent tests used an explicit owned base directory, and no unrelated cleanup repair was attempted.

Real committed board and risk envelope at the R5 base were also processed through the actual freeze/writer/helper and bound reader in an isolated output directory: **69/69 rows, exact order/content preserved, source state AVAILABLE, zero errors, all action flags false**. Source session2026-09-25. Raw source hashes:

- board `934f56ac94e057cd5c0f1466d4a24a09382e8e253c2e59f10c9b248bcf7445a8`;
- envelope `ae32e124808cf4fb64ef69687b32ad78382a71dd2f9b366eebbc06995ede45ae`.

This is real-input native-helper proof, **not** hosted CI, deployed publication, authenticated browser/API behavior or forward-outcome accrual. Native evidence is retained under `/Volumes/Mastermind/evidence/gd6a-us-shadow-intake-20260928-sol-001/publication-r5/`.

## Exact next capability

Obtain permitted required current-base/registered-suite release evidence and consume actual diagnostics; the prior explicitly blocked CI-status request is not retried or proxied. Release this same source only when its remaining checks/acceptance are satisfied. Then prove one ordinary settled build -> Git checkpoint -> served sidecar/index -> bound consumer, with rank/plan parity and the next ordinary refresh. The saved source receipt is not that production event.

After publication, the unfinished business capability is individually registered risk/de-risking policy -> shadow counterfactual evaluation -> scoped recommendation enforcement and portfolio-specific exposure controls. Keep existing Grey Deer policy/grant/promotion owners; do not convert a red label or this zero-policy shadow into a live order. Preserve H1/Cycle, Seat B#7107/#7094, the other research seats and original CEO UI release.

Protected procedure loaded: Mastermind `e981ec1b0b6e3bd47e267b6abc92adee4a94d6a8`, compatible Skillpack1.0.1/bootstrap1. Current outer Chairman intent supplies the self-audit exception. No source custody transfer, automatic wake or production activation.
