---
key: CHART-ENGINE-Q03B-CDP-WHEEL-HELD-BEHIND-VISUAL-STATE-CALLBACK
claim: >
  A wheel sent through CDP `Input.dispatchMouseEvent` (the Q03b v2 zoom workload) is stamped
  when the Browser receives the command and is then held behind
  `RenderWidgetHostImpl::InsertVisualStateCallback` before the Browser forwards it to the
  renderer: Chromium content/browser/devtools/protocol/input_handler.cc
  InputHandler::HandleMouseEvent runs `widget_host->InsertVisualStateCallback(...)` for every
  wheel event ("We make sure the compositor is up to date before sending a wheel event") with
  no first-event condition and no skip flag, and the event time defaults to TimeTicks::Now()
  at receipt. An OS wheel has no such hold. On the reference Mac (headed, dpr 2, 100 Hz) the
  hold is visible in the trace as the delay from each `cadence:zoom:input` mark to the k-th
  Browser-process `RenderWidgetHostImpl::ForwardWheelEvent` slice (category "input"): median
  5.33 ms (mm) and 4.37 ms (lwc), range 0.44-10.53 / 0.99-14.86 ms, 60 of 60 forwards for 60
  marks in both engines at 367f488e5c67 with PERF-C. Because the hold releases only after the
  renderer's next frame, it also COMPRESSES receipt stamps relative to forwards: on the mm
  trace wheel 0 was stamped 6.30 ms before wheel 1 yet forwarded 10.38 ms after its own
  stamp, so a forward can legitimately fall after the next wheel's mark. Every v2 zoom latency
  therefore includes this CDP-only wait; measured from the forward instead, the first wheel is
  32.49 ms (mm) / 43.43 ms (lwc) instead of 42.87 / 52.96 ms from the mark.
falsifier: >
  From terminal/ with a NEXT_PUBLIC_CHART_BENCH=1 prod build on port 3111, run
  `BENCH_HEARTBEAT_MODE=through BENCH_RUNS=3 BENCH_IMPLS=mm,lwc BENCH_BASE_URL=http://127.0.0.1:3111
  npx playwright test -c playwright.bench.config.ts chart-engine.cadence` headed on the
  reference Mac at a head carrying Terminal PR #1050 and read `forwards`, `paired` and
  `stamp_to_forward_p50_ms` on each CADENCE_DIAG line. A VALID run whose
  stamp_to_forward_p50_ms is below 1 ms (no hold), or a Chromium input_handler.cc whose
  HandleMouseEvent forwards wheels without InsertVisualStateCallback, refutes the hold; a run
  whose forwards differ from its 60 marks without a dropped or coalesced wheel refutes the FIFO
  forward order the v4 forward pairing relies on.
so_what: >
  The v2 receipt measured the CDP injection path's hold as if it were engine latency, so v2
  cannot rule the zoom half fairly for either engine. DEC:CHART-ENGINE-Q03B-PROTOCOL-V4-OWN-FRAME-SWAP-END
  keeps the v3 draft's forward rules: it anchors at the forward (minus the capped main-thread
  busy bias), pairs forwards with marks by index (never by a forward-before-next-mark rule,
  which the stamp compression breaks), and refuses as INVALID a run whose forward or paired
  count is not the scheduled 60 or whose stamp-to-forward range leaves [0, 30] ms. OS-level injection is not a substitute on the reference Mac
  (CGPreflightPostEventAccess false; a TCC grant is outside the seat's authority).
kind: runtime
verified_at: 2026-10-18
verified_by: >
  Seat session 6dfa7fe4 on 2026-10-18: source read of Chromium
  content/browser/devtools/protocol/input_handler.cc (HandleMouseEvent and GetEventTimeTicks);
  headed diag traces at 367f488e5c67 with PERF-C (extra trace categories, not receipts), read
  by a counts-only mechanism check through Terminal PR #1050's pairWheelForwards and
  cadenceForwardBlock (terminal/lib/chart-engine/bench/cadence.ts:1405-1440): mm 60 marks /
  60 forwards / 60 paired, stamp-to-forward 0.44 / 5.33 / 10.53 ms; lwc 60 / 60 / 60, 0.99 /
  4.37 / 14.86 ms; a pre-PERF-C diag run that lost a mark (59 marks) pairs only 25 with a
  stamp-to-forward min of -39.28 ms, which the v4 INVALID rules (carried from v3) refuse. The negative case for
  the next-mark rule is pinned as a mutation in terminal/lib/__tests__/chartEngineCadence.test.ts
  (re-adding the rule turns the suite red).
scope: [terminal]
confidence: verified
---
