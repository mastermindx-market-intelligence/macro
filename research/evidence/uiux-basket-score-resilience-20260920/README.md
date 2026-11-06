# Basket Detail: snapshot explanations survive unavailable optional reads

## Mission and source
Continue the Chairman-authorized macro frontend UX sweep on the existing Basket Detail render/injection owner. This follow-up was discovered only after parent PR #7412 merged and deployed. Source base: 09d5c65bfa7c8eb9f169262dff9375eb05ac3b4b. Procedure: Mastermind protected master b75a491db408892dfe6fe7c4bb9d40cfad8efcb3, Skillpack 1.0.1. VPS-only delivery under DEC:UIUX-VPS-ONLY-DELIVERY-20260920. Direct ownership reason: PRINCIPAL_JUDGMENT / bounded real-path repair. No child worker or new publication owner.

## Before / after
Public US and China Basket Detail pages loaded the main snapshot, but optional pulse, turn-watch and cross-market endpoints returned HTTP 401. The existing score-details injector ran only after successful optional data reads, so the snapshot's own explanation disappeared. Sorting also rebuilt the page without restoring it.

The existing render function now invokes the existing injector when available. The injector's original registration also performs one initial pass, covering the already-rendered document case. The injector remains idempotent; it removes its own prior widgets. Successful optional reads retain their existing update path. Missing pulse data still yields no live strip. No new fetch, retry, watcher, cache, state store or runtime hook is introduced.

## Boundaries
Only the template, its 121 existing generated pages, existing registered FTR UI tests and this evidence change. Embedded data, formulas, recommendation and tier order, CSS, all request URLs and authentication are untouched. Nothing pretends to supply authenticated data. The explanation uses only the snapshot already embedded in the public HTML.

## Proof
- The public before-run in production-before.json records all 16 US/China × desktop/mobile × English/Chinese × dark/light cells with the score details absent and optional reads returning 401.
- The exact patched local pages are tested with explicitly forced 401 responses on optional-data routes; all 16 cells retain one usable score disclosure, including after an actual column-sort click. No private renderer is invoked.
- The local capture is a negative-state test, not a production claim or entitlement proof.
- tests.log: 151 passed in the existing Basket Detail/FTR/group-read/personality/navigation/chrome suites. No new CI job or registration plane.
- Runtime shape and all generated pages are guarded in the existing tests/test_ftr_w3_ui.py.

## Acceptance and continuation
BUILT_NOT_PROVEN until this exact source passes hosted CI, an expected-head merge is accepted, the existing locked VPS updater serves the artifact, and verify_resilience.py --base-url https://www.mastermind-x.com completes against the public path without request interception. Preserve the original 401 behavior; do not change access rules to make a screenshot pass. Do not redo parent #7412's accepted copy changes or create another score renderer.
