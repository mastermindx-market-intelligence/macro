---
key: CHART-ENGINE-Q03B-ZOOM-P95-GAP-IS-ACK-PACED-PHASE
claim: >
  Under the Q03b v1 protocol (terminal/bench/chart-engine.cadence.bench.ts:347-349, sixty
  `page.mouse.wheel(0, -120)` calls each awaited, headed Chromium on the reference Mac's 100 Hz
  panel) the mm-vs-lwc zoom input_to_present p95 gap (mm 20.1-20.8 ms vs lwc 17.9-18.6 ms on
  the official e206cd046 receipts) is not a paint-cost difference. Per-wheel frame production
  is equal: every zoom wheel in both engines presents two vsync slots after the preceding
  presentation, and at equal input phase (input mark minus the previous presentation) the two
  engines' latencies agree within 0.4 ms (phase 2-4 ms: 17.6 vs 17.2 ms; phase 0-0.5 ms: 19.7
  vs 19.7 ms). The gap is the phase distribution. Playwright resolves `mouse.wheel` when the
  renderer acks the event, the ack follows the wheel handler, and mm's handler is cheaper
  (headless EventDispatch median 0.27 vs 2.60 ms), so mm's next wheel lands earlier in the
  vsync cycle (18% of mm wheels at phase < 1 ms vs 2% for lwc) and waits longer for the next
  present: latency = 2 x vsync - phase within 0.5 ms, and the handler delta equals the phase
  delta equals the latency delta. A slower handler scores better: a diagnostic capture-phase
  spin of X ms per wheel moves mm p95 from 20.4 (X=0) to 19.0/18.8 (X=2) to 17.3/17.7 (X=4)
  and lifts lwc to 21.8/21.2 at X=4; the share of mm wheels at latency >= 19.5 ms goes
  16.9% -> 1.7% -> 0%.
falsifier: >
  Dispatch the 60 wheels on a wall clock instead of on the renderer ack: replace the awaited loop
  at terminal/bench/chart-engine.cadence.bench.ts:347-349 with scheduled CDP
  `Input.dispatchMouseEvent` sends at gaps of 17 + 6u ms (u uniform, seeded), then from
  terminal/ run `NEXT_PUBLIC_CHART_BENCH=1 npm run build && npm run start -- -p 3111` and
  `BENCH_RUNS=3 BENCH_IMPLS=mm,lwc BENCH_BASE_URL=http://127.0.0.1:3111 npx playwright test -c
  playwright.bench.config.ts chart-engine.cadence` headed on the reference Mac. An mm-minus-lwc
  zoom p95 gap >= 1 ms that persists at equal phase refutes the claim; so does a per-wheel
  compositor/main-thread breakdown showing mm's commit, raster or present stages longer than
  lwc's at equal phase, or the spin falsifier (a capture-phase wheel listener spinning X ms per
  wheel) failing to move p95.
so_what: >
  There is no legitimate canvas/ fix for the v1 p95 gap: any change that makes mm's wheel
  handler slower "passes" and any change that makes it faster "fails". The v1 ack-paced zoom
  gate cannot rank engines on latency, so D1 of
  DEC:CHART-ENGINE-Q03B-ZOOM-HOLD-STANDS-TWO-DEFECTS is resolved by the prospective protocol
  ruling DEC:CHART-ENGINE-Q03B-PROTOCOL-V2-WALL-CLOCK-INPUT (inputs dispatched on a wall clock
  with seeded phase jitter), not by engine work. Do not commission a canvas/ zoom-path
  optimisation against a v1 p95, and never compare a v1 number with a v2 number.
kind: landmine
verified_at: 2026-10-13
verified_by: >
  Fabric lane ce-q03c-d1diag-1013 (ubuntu1, MiniMax-M3, 555 s, ledgered deterministic):
  headless prod build at e206cd046, vsync 16.666 ms, n=177 wheels per engine; per-wheel
  medians lwc vs mm: latency 28.61 vs 30.89 ms, phase 4.73 vs 2.34, EventDispatch 2.60 vs
  0.27, rAF 2.52 vs 1.33, total main thread 12.27 vs 13.12, minor GC 0.66 vs 0.06 ms/wheel;
  latency = 2 x vsync - phase within 0.5 ms. Opus P5 cadence orchestrator headed Mac smoke at
  e206cd046 (port 3113, prod build, 3 runs, vsync 10 ms): mm zoom lat p95 20.1/20.5/19.9,
  lwc 18.0/19.3/18.5; pooled phase bins and the uncommitted capture-listener spin falsifier
  (numbers in the claim). Seat adjudication 2026-10-13; the lane's own "Commit+SubmitToPres
  dominant" naming was rejected on its own P3 table.
scope: [terminal]
confidence: verified
---

# DSC-CHART-ENGINE-Q03B-ZOOM-P95-GAP-IS-ACK-PACED-PHASE

## Mechanism

1. Playwright's `page.mouse.wheel` sends `Input.dispatchMouseEvent` and resolves when the
   renderer acknowledges the event, i.e. after the page's `wheel` listeners ran.
2. The bench dispatches the next wheel immediately after that ack (v1 loop, no delay).
3. Both engines answer a wheel two vsync slots after the preceding presentation (the wheel
   is handled off the BeginFrame, the resulting frame is produced at the next BeginFrame and
   presented at the one after). Latency therefore equals `2 x vsync - phase`.
4. A cheaper handler acks sooner, so the next wheel's phase is smaller and its latency is
   larger. The measured p95 is a property of the harness's ack pacing, not of the renderer.

## Numbers that decide it

| view | lwc | mm | reading |
|---|---|---|---|
| headless per-wheel latency median | 28.61 | 30.89 | +2.28 ms mm |
| headless phase median | 4.73 | 2.34 | -2.39 ms mm |
| headless EventDispatch median | 2.60 | 0.27 | -2.33 ms mm |
| headed share of wheels at phase < 1 ms | 2% | 18% | mm acks sooner |
| headed latency at phase 2-4 ms | 17.2 | 17.6 | equal within 0.4 |
| headed latency at phase 0-0.5 ms | 19.7 | 19.7 | equal |
| headed mm p95 with X ms spin per wheel | X=0 20.4 | X=2 19.0/18.8 | X=4 17.3/17.7 |
| headed lwc p95 with X=4 spin | 21.8/21.2 | | slower handler scores better |
