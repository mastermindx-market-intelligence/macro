---
key: CHART-ENGINE-Q03B-V2-FIRST-WHEEL-ELEVATION-PERSISTS-WITH-HEARTBEAT
claim: >
  Under bench protocol q03b-v2 (DEC:CHART-ENGINE-Q03B-PROTOCOL-V2-WALL-CLOCK-INPUT: a bench-side
  requestAnimationFrame heartbeat running >= 200 ms before and through the zoom gesture,
  heartbeat_mode "through", leadin_presentations 0, sixty wall-clock CDP wheel sends at
  17 + 6u ms) the first wheel is still the zoom p99 in all three official mm runs, in official lwc run 1, in
  all three runs of the later ledger-only lwc comparator, and within 0.6 ms of the run maximum in
  official lwc run 2 (35.2 vs 35.7), on the reference Mac (prod build at 1b7ec6a6b5ed, headed, dpr 2, 100 Hz, load1 19.62): wheel-0
  input_to_present 42.8 / 42.4 / 38.9 ms (mm) and 42.6 / 35.2 (official runs 1-2; run 3 aborted in the harness) and 41.6 / 52.3 / 47.2 (comparator) ms (lwc) against 20 ms for two vsync slots,
  while wheels 1-59 stay within 32.1 (mm) / 35.7 (lwc) ms. This refutes
  DSC:CHART-ENGINE-Q03B-FIRST-WHEEL-IS-RENDERER-IDLE-WAKEUP by its own falsifier: the
  renderer was demonstrably awake (BeginFrames ticking through the lead-in, 0 lead-in
  presentations by construction) and the elevation persisted across the 3 mm runs and all 5 completed lwc runs. The
  heartbeat removes the idle-wake-up component but not the first-wheel cost; the remaining
  mechanism is not yet isolated (the first wheel's answering frame begins 12-20 ms after its
  mark and that frame's begin-to-present is ~24 ms mm / ~34 ms lwc in the headed traces —
  a pipeline-fill or first-input scroll-latching signature, not idle wake-up).
falsifier: >
  From terminal/ run `NEXT_PUBLIC_CHART_BENCH=1 npm run build && npm run start -- -p 3111` and
  `BENCH_HEARTBEAT_MODE=through BENCH_RUNS=3 BENCH_IMPLS=mm,lwc BENCH_BASE_URL=http://127.0.0.1:3111
  npx playwright test -c playwright.bench.config.ts chart-engine.cadence` headed on the
  reference Mac and read wheel 0 from the CADENCE_DIAG line. A first wheel presenting within
  two vsync slots (<= 20 ms) in >= 2 of 3 valid runs of either engine refutes this record; so
  does a trace showing the first-wheel answering frame beginning within one vsync slot of the
  mark with a begin-to-present equal to the steady-state frames.
so_what: >
  The Q03b zoom p99 budget (33.4 ms over all 60 inputs, first input included) is still failed
  by BOTH engines under protocol v2 (lwc official runs 1-2: p95 25.5 / 25.3, p99 42.6 / 35.7; ledger-only comparator 3/3:
  p95 26.2 / 24.8 / 25.6, p99 41.6 / 52.3 / 47.2), so the zoom hold of
  DEC:CHART-ENGINE-Q03B-PROTOCOL-V2-WALL-CLOCK-INPUT stands and the P03 default flip stays
  held. The next legitimate step is a new falsifiable diagnosis of the first-wheel cost with
  an awake renderer (first-input compositor scroll-latching / hit-test, non-passive wheel
  listener first dispatch, first BeginMainFrame-with-input), recorded prospectively as a
  protocol v3 DEC before any receipt — never a post-result exclusion, warm-up wheel or
  larger n (D10).
kind: runtime
verified_at: 2026-10-14
verified_by: >
  Seat (Fable session 6dfa7fe4) official Q03b protocol-v2 receipt 2026-10-14T07:11Z at
  1b7ec6a6b5ed80f49db2b9d4353cadb98a3f79a8 (zsh q03_official.sh: port 3111, prod build with
  NEXT_PUBLIC_CHART_BENCH=1, headed, dpr 2, 100 Hz panel, BENCH_RUNS 3, BENCH_HEARTBEAT_MODE
  through, load1 19.71 before / 19.62 at run / 18.66 after): CADENCE_DIAG zoom_first_lat_ms
  mm 42.812 / 42.429 / 38.945 and lwc 42.639 / 35.187 with zoom_rest_lat_max_ms mm 32.111 /
  23.866 / 25.674 and lwc 29.57 / 35.713; heartbeat_ms 258.6-267.6, leadin_presentations 0,
  dispatch_dev_max_ms <= 1.331, 60/60 marks and 0 unpresented in every completed run. lwc run 3
  aborted in the harness (page.evaluate "Execution context was destroyed" in waitReady,
  terminal/bench/chart-engine.cadence.bench.ts:169), so that session has no lwc receipt file. A
  complete ledger-only lwc comparator (not a ruling input) followed at 2026-10-14T07:57:33Z on
  the same head and port 3111 (load1 17.98 before / 17.98 at run / 16.79 after): zoom_first_lat_ms
  41.612 / 52.34 / 47.199 with zoom_rest_lat_max_ms 29.711 / 31.34 / 28.998, heartbeat_ms
  261.6-261.9, leadin_presentations 0, counted-run dispatch_dev_max_ms 1.367 / 1.661 / 0.328 (run
  3's first attempt was INVALID at 2.016 > 2 and was repeated unread); its median receipt
  cadence-lwc-1b7ec6a6b5ed80f49db2b9d4353cadb98a3f79a8-m2studio.json is budget_ok false and is
  frozen in the seat scratchpad (receipts-1b7ec6a6b5ed-comparator-lwc). The mm
  receipt is budget_ok false (zoom input_to_present p95 21.655 / p99 42.429) and is not
  committed; the receipt directory is frozen in the seat scratchpad
  (receipts-1b7ec6a6b5ed.ruling-0711Z).
scope: [terminal]
confidence: verified
supersedes: [DSC:CHART-ENGINE-Q03B-FIRST-WHEEL-IS-RENDERER-IDLE-WAKEUP]
---
