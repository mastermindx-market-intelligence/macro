---
key: CHART-ENGINE-Q03B-FIRST-WHEEL-IS-RENDERER-IDLE-WAKEUP
claim: >
  The 33-38 ms first-wheel latency that sets the zoom p99 (nearest-rank p99 of 60 inputs =
  the maximum) in every headed Q03b run of BOTH engines is Chromium's renderer main-thread
  scheduler idle wake-up, triggered by the bench's 200 ms pre-gesture idle
  (terminal/bench/chart-engine.cadence.bench.ts:343 `waitForTimeout(200)` before the zoom
  gesture; :276 for pan). It is not lazy first-zoom initialisation in the engines or the host,
  and not the harness's synthetic-input path. Dose-response is a sharp step at one frame of
  idle (headed Mac, prod build at e206cd046, wheel-0 latency ms, 3 runs per engine):
  idle 0 -> mm 3.0/5.8/14.5, lwc 8.8/11.6/13.3; idle 16 -> mm 24.8/33.9/31.8, lwc
  40.9/24.0/25.3; idle 50/100/200/500 stay at 27-46 ms in both engines. A warm-up wheel
  followed by the same idle does not remove it (warm+idle200: mm 35.9/39.7/65.3, lwc
  41.0/36.8/42.4) and warm+idle0 is low again (mm 14.1/36.9/15.5, lwc 9.9/9.4/10.7).
  Headless: the first input's LatencyInfo.Flow begins 1.1-1.8 ms after its mark (faster than
  inputs 2-5), the dominant first-input task is one ThreadControllerImpl::RunTask of 48.9 ms
  (mm) / 14.6 ms (lwc) with no GC and no compile, and a non-passive wheel listener accounts
  for only ~6 ms on a bare page (26.7 vs 20.5). Pan is not elevated.
falsifier: >
  Replace the `waitForTimeout(200)` at terminal/bench/chart-engine.cadence.bench.ts:343 with a
  bench-side requestAnimationFrame heartbeat running for >= 200 ms up to and through the first
  wheel, then from terminal/ run `NEXT_PUBLIC_CHART_BENCH=1 npm run build && npm run start -- -p
  3111` and `BENCH_RUNS=3 BENCH_IMPLS=mm,lwc BENCH_BASE_URL=http://127.0.0.1:3111 npx playwright
  test -c playwright.bench.config.ts chart-engine.cadence` headed on the reference Mac and read
  wheel 0's latency from the dump. A first-wheel elevation above two vsync slots that persists
  across >= 3 runs per engine with the heartbeat refutes the claim; so does a first wheel after
  >= 16 ms of renderer idle presenting within two slots in either engine without the heartbeat,
  or a lazy-initialisation signature (compile, GC, first-use allocation, module evaluation) in
  the first-wheel task of either engine's trace.
so_what: >
  No engine or host code owns the first-wheel cost: both engines and every web page pay the
  idle wake-up on the first input after a frame of idle. A product keep-awake (an idle rAF
  heartbeat shipped to users) would remove it only by burning CPU and battery while the chart
  is idle and is rejected. The v1 protocol's 200 ms pre-gesture idle therefore makes the zoom
  p99 of a 60-input sample measure Chromium, and no engine can pass it. D2 of
  DEC:CHART-ENGINE-Q03B-ZOOM-HOLD-STANDS-TWO-DEFECTS is resolved by the prospective ruling
  DEC:CHART-ENGINE-Q03B-PROTOCOL-V2-WALL-CLOCK-INPUT (the gesture starts from an awake
  renderer; the first input stays in the sample; no exclusions; budgets unchanged), never by a
  post-result exclusion, a warm-up wheel or a larger n (D10).
kind: runtime
verified_at: 2026-10-13
verified_by: >
  Fabric lane ce-q03c-d2diag2-1013 (ubuntu1, MiniMax-M3, 1872 s, ledgered deterministic;
  evidence branch claude/ce-q03c-d2diag2-1013 @ 07826dafbc6be94f09e1123ed6424b8d7f4386c6,
  files terminal/bench/q03c/{d2-diag.bench.ts,bare-wheel.html,analyze.cjs,f4-timestamps.cjs,
  f5-tasks.cjs}; traces kept outside the repo): falsifiers F1 bare passive/non-passive, F2
  warm-up before tracing, F3 idle dose-response (idle 0 -> first_med 2.4 ms both engines,
  idle 16 -> mm 57.8 / lwc 40.0), F4 LatencyInfo.Flow timestamps, F5 task dump. Opus P5
  cadence orchestrator headed Mac first-wheel falsifier at e206cd046 (port 3113, prod build,
  3 runs x 2 engines per idle step, load1 12-23; diagnostic spec copies archived in the seat
  scratchpad, worktree tracked-clean). Listener registration:
  terminal/lib/chart-engine/canvas/inputBridge.ts:324 `{ passive: false }` (lwc is also
  non-passive).
scope: [terminal]
confidence: verified
superseded_by: DSC:CHART-ENGINE-Q03B-V2-FIRST-WHEEL-ELEVATION-PERSISTS-WITH-HEARTBEAT
---

# DSC-CHART-ENGINE-Q03B-FIRST-WHEEL-IS-RENDERER-IDLE-WAKEUP

## Headed Mac first-wheel latency (ms, wheel 0 of the zoom gesture, 3 runs per cell)

| pre-gesture state | mm | lwc |
|---|---|---|
| idle 0 | 3.0 / 5.8 / 14.5 | 8.8 / 11.6 / 13.3 |
| idle 16 | 24.8 / 33.9 / 31.8 | 40.9 / 24.0 / 25.3 |
| idle 50 | 30.9 / 33.5 / 30.7 | 38.0 / 37.0 / 27.5 |
| idle 100 | 32.0 / 30.0 / 29.1 | 35.1 / 43.1 / 31.7 |
| idle 200 (v1 protocol) | 31.7 / 34.2 / 44.4 | 36.8 / 37.2 / 34.3 |
| idle 500 | 38.1 / 39.9 / 35.7 | 46.5 / 35.3 / 35.6 |
| warm-up wheel + idle 200 | 35.9 / 39.7 / 65.3 | 41.0 / 36.8 / 42.4 |
| warm-up wheel + idle 0 | 14.1 / 36.9 / 15.5 | 9.9 / 9.4 / 10.7 |

Hypotheses closed: (a) non-passive listener — partial, ~6 ms of a bare page's first wheel;
(b) lazy first-zoom initialisation — refuted (warm-up does not help when an idle follows);
(c) harness synthetic-input path — refuted (the first input's flow starts sooner than later
inputs'); (d) renderer idle wake-up — supported headless and confirmed headed in both engines.
