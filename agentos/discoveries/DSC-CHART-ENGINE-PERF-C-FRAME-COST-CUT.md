---
key: CHART-ENGINE-PERF-C-FRAME-COST-CUT
claim: >
  The owned mm canvas engine's per-frame main-thread cost was dominated by two allocations
  that grew with the visible range, not with what is drawn: `timeAxisTicks` built a `Date`
  for every candidate tick of every unit, and the line LOD materialised every in-view point
  before decimating it. PERF-C (Terminal PR #1050, commit dfd18572c) generates candidate ticks
  arithmetically per unit and constructs a `Date` only for a placed tick
  (terminal/lib/chart-engine/canvas/ticks.ts), and streams points into min/max-per-pixel
  buckets through `LineDecimator` (terminal/lib/chart-engine/canvas/lod.ts), with output
  identical to the old generator and to the batch `lineDecimate` on oracle tests that include
  pre-1970 dates, leap days, the `Date` range edges, NaN rows, ties, gaps and non-finite
  values. On headed mm diag traces at 367f488e5c67 (reference Mac, dpr 2, 100 Hz, run 1 before
  vs after): pan FireAnimationFrame median 5.63 -> 3.09 ms, zoom FireAnimationFrame p90
  5.83 -> 2.85 ms, the first wheel's BeginMainFrame main-thread time between its mark and its
  presentation 24.77 -> 8.17 ms, mark-anchored zoom latency median 17.00 -> 12.29 ms, and the
  forward-anchored first wheel 43.32 -> 32.49 ms.
falsifier: >
  From terminal/ run `npx vitest run lib/__tests__/chartEngineLod.test.ts
  lib/__tests__/chartEnginePerfFrame.test.ts`; any red oracle case (a tick or decimated
  point that differs from the pre-PERF-C generator) refutes the "identical output" half. A
  headed mm diag trace of the cadence bench at a head carrying PR #1050 whose pan
  FireAnimationFrame median is 5 ms or more, or whose first-wheel BeginMainFrame time is
  within 10 % of the pre-PERF-C 24.77 ms, refutes the cost half.
so_what: >
  The first-wheel cost the v2 receipt failed on was partly the engine's own frame cost:
  PERF-C removes about 16.6 ms of first-wheel main-thread work; in the diag traces the
  v4-coded mm zoom figures move from p95 20.290 / p99 27.166 ms before PERF-C to 18.065 /
  18.962 after (DEC:CHART-ENGINE-Q03B-PROTOCOL-V4-OWN-FRAME-SWAP-END). The v4 receipt is therefore taken
  at a master head that carries PERF-C; a receipt at an older head measures the old frame
  cost. The engine stays opt-in (`?engine=mm`) until that receipt passes.
kind: runtime
verified_at: 2026-10-18
verified_by: >
  Seat session 6dfa7fe4 on 2026-10-18: `npx vitest run lib/__tests__/chartEngineLod.test.ts
  lib/__tests__/chartEnginePerfFrame.test.ts` at commit dfd18572c (44 pass); a full `npm
  test` on the PERF-C plus v3-draft tree (12,339 pass); headed diag traces at 367f488e5c67 before
  (03:46Z) and after (04:14Z) PERF-C, read with per-BeginMainFrame FireAnimationFrame and
  per-wheel stage scripts (pan rAF median 5.63 / 3.09, zoom rAF p90 5.83 / 2.85, wheel-0
  BeginMainFrame 24.77 / 8.17 ms). Diag traces carry extra trace categories and are not
  receipts.
scope: [terminal]
confidence: verified
---
