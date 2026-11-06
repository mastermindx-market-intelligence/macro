---
key: CHART-ENGINE-Q03B-NEXT-FRAME-ANSWER-IS-NOT-THE-WHEELS-OWN-FRAME
claim: >
  The Q03b answer rule shared by protocols v1, v2 and the v3 draft (a zoom wheel is answered by
  the first STATE_PRESENTED_ALL frame at-or-after its anchor) almost never selects the frame
  the wheel itself produced. Chromium attributes each CDP wheel to one renderer-pid
  EventLatency async slice (category "cc,benchmark,input,input.scrolling", event_type
  MOUSE_WHEEL) whose BrowserMainToRendererCompositor stage begins at the Browser
  ForwardWheelEvent (unique nearest match, max offset 0.006-0.053 ms on every trace). On four
  headed diag zoom traces at 367f488e5c67 (reference Mac, dpr 2, 100 Hz; mm and lwc, with and
  without PERF-C) the next-frame answer precedes the wheel's own EventLatency presentation by
  more than 0.5 ms on 58/59, 58/59, 59/60 and 53/57 wheels, by a median of 20.00 ms (two
  vsyncs). The stage sequence of a typical mm wheel, relative to its forward: renderer
  compositor +0.05 ms, main-thread dispatch +9.39 (rAF-aligned input waits about a vsync), the
  engine's own handler work 0.29 ms, Commit +13.73, GPU swap end +15.72, presentation +33.08;
  the SwapEndToPresentationCompositorFrame (OS display) stage has a median of 20.08 ms (mm) /
  15.4 ms (lwc). Separately, anchoring at the forward excludes real main-thread congestion:
  adding back bias_k = min(busy_k, forward_k - mark_k), busy_k being the remainder of the
  renderer-main top-level task spanning the mark, raises the forward-anchored p95 by 2.49 /
  3.14 / 1.29 / 6.65 ms on the same four runs.
falsifier: >
  Take a headed BENCH_DUMP_TRACE=1 zoom trace of the cadence bench at a head carrying Terminal
  PR #1050 on the reference Mac. For each forward, compare the first STATE_PRESENTED_ALL
  presentation at-or-after it (forwardLatenciesMs in
  terminal/lib/chart-engine/bench/cadence.ts) with the presentation of the EventLatency that
  parseWheelEventLatencies and ownFrameLatenciesMs map to it. If the two coincide within
  0.5 ms on at least half of the 60 wheels, or the median gap is below one vsync (10 ms at
  100 Hz), the claim that the next-frame rule misses the wheel's own frame is refuted. If
  adding the capped busy bias changes the forward-anchored p95 by at most 1.0 ms on every
  sound run, the congestion half is refuted.
so_what: >
  No Q03b receipt so far (v1, v2) measured the wheel's own frame, and the v3 draft would not
  have either, so v3 was never measured: its pre-registered B1 check (fidelity and excluded
  congestion, each with a 1.0 ms tolerance) failed on all four deciding runs and its outcome
  rules prescribed the two remedies that protocol v4 adopts
  (DEC:CHART-ENGINE-Q03B-PROTOCOL-V4-OWN-FRAME-SWAP-END): answer with the wheel's own
  EventLatency frame and anchor at the forward minus the capped busy bias. The stage figures
  are why the v4 endpoint is the GPU swap end: the ~15-20 ms display stage after the swap is
  outside any web engine's control and alone would consume the 20 ms p95 budget. Any future
  input-latency gate in this repo should answer through EventLatency, not "next presented
  frame".
kind: runtime
verified_at: 2026-10-18
verified_by: >
  Seat session 6dfa7fe4 on 2026-10-18: a B1 pre-registration written at 12:35:25Z before any
  statistic was computed (deciding criteria P1 answer fidelity and P2b excluded congestion,
  exclusions fixed in advance: d1 mm r2 and d1 lwc r2 excluded at 59 / 57 marks), then a check
  script importing PR #1050's cadence.ts over diag traces diag-perfc1 and diag-d1 r1 (mm and
  lwc) with extra trace categories (not receipts): P1 FAIL 4/4, P2b FAIL 4/4; per-wheel stage
  reads of the EventLatency children for the stage sequence. The v4 code's own-frame rows
  match an independent Python oracle with 0 mismatches on the same four traces.
scope: [terminal]
confidence: verified
---
