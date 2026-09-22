---
key: TERMINAL-OBSOLETE-404-CAN-HIDE-RECOVERED-CHART-DATA
claim: >
  Terminal dataCache can hide newly recovered OHLC for ten minutes when an obsolete
  request writes a 404/410 absence after invalidation or LRU eviction; negative writes
  must share the current-inflight ownership guard already used for positive writes.
falsifier: >
  Run terminal/lib/__tests__/dataCacheRequestOwnership.test.ts at Terminal base
  e5ccacf4ab327ad414c6f9fa6000f0a720a8ea55: five race cases fail. Move the absence write
  into the existing identity guard as in 2bdadcb7b77bcbace318846abd9d7ad674bde1e4:
  all nine cases pass. A stale request still changing the current absence cache refutes repair.
so_what: >
  Preserve one request-ownership boundary for both cache success and absence; do not add
  another cache, generation store or timer. Keep real current 404/410 suppression and
  transient-failure recovery. Reconcile Terminal PR 705 before rebuilding this correction.
kind: landmine
verified_at: 2026-09-21
verified_by: >
  Terminal PR 705 at 2bdadcb7b77bcbace318846abd9d7ad674bde1e4; npm test --
  lib/__tests__/dataCacheRequestOwnership.test.ts; full npm test -- --maxWorkers=2 --minWorkers=2.
scope:
  - mastermind-terminal
  - terminal/lib/dataCache.ts
  - terminal/lib/__tests__/dataCacheRequestOwnership.test.ts
confidence: verified
---

## Mechanism and validation

`getJSONResult` checks remembered absence before returning fresh cached data. Previously,
`doFetch` called `rememberAbsence` outside its existing `current.inflight === inflight`
guard. A delayed old response therefore hid a newer success even though the positive
response path was protected correctly. The repaired request may still return its own
truthful absence to its original caller, but cannot mutate the newer cache state.

The deterministic tests use the real `getJSONResult`, `invalidate`, `getOhlc` and cache
APIs, with controlled network completion. They cover both absence codes, one/all-key
invalidation, eviction, genuine current absence, superseded success, and transient 503.
Full qualification: 378 files / 6,081 tests passed / four existing TODO; TypeScript and
new-test ESLint passed. Real responsive quote-single-flight and chart-view/reset
regressions: eight passed / ten existing viewport-specific skips / zero failures.
No FPS, whole-page latency improvement or production deployment is inferred from this.

## Continuation and non-duplication

The cache correction merged as `5fee4ab7517095c04a1fbab17c6b273826fd6446` and was deployed
through the existing exact-target build owner. Production acceptance is Terminal PR 705
comment 5769817029: live marker and source hash match the accepted release, fresh public
chart checks passed at all three viewports, and desktop completed NVDA → AAPL → NVDA
without reload, page errors or horizontal overflow. The rare obsolete-absence race is
proven by the exact-source regression above; the production browser run proves normal
chart behavior and the deployed identity, not a naturally observed 404 race or an FPS gain.
The release is DO_NOT_REDO. Current protected procedure for the continuing chart programme
is Mastermind@4ca1b97e65de9d4ba8c868b9d708fb7620a8a76f.
The related chart settings upgrade, PR 701, is independently deployed and browser-proven
at e5ccacf4ab327ad414c6f9fa6000f0a720a8ea55; receipt is Terminal PR 701 comment 5768037719.
Clock optimization PR 702 remains held on a mobile marker-tooltip failure. Its exact
failure was returned to existing repair PR 688; do not create a second marker writer.
Current delivery state remains in those GitHub carriers, not in this dated discovery.
No workstream or runtime identity is invented here; the full chart-upgrade mission is incomplete.
