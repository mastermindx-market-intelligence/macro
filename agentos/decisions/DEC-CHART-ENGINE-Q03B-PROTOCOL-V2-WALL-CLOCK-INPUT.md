---
key: CHART-ENGINE-Q03B-PROTOCOL-V2-WALL-CLOCK-INPUT
question: >
  Q03c diagnosed both zoom overruns of the official Q03b receipt at e206cd046 as couplings
  between the v1 measurement protocol and Chromium rather than engine costs. D1 (mm zoom p95
  20.1-20.8 ms vs lwc 17.9-18.6 ms) is the input phase set by the harness awaiting the
  renderer's ack of each `page.mouse.wheel`: a cheaper handler acks sooner, the next wheel
  lands earlier in the vsync cycle, latency = 2 x vsync - phase, the engines agree within
  0.4 ms at equal phase, and a slower handler scores better
  (DSC:CHART-ENGINE-Q03B-ZOOM-P95-GAP-IS-ACK-PACED-PHASE). D2 (p99 = the first wheel, 33-38 ms,
  both engines) is Chromium's renderer idle wake-up after the bench's 200 ms pre-gesture idle:
  a sharp step at one frame of idle, 3-14 ms with no idle, not removed by a warm-up wheel
  followed by the idle, lazy initialisation and the synthetic-input path refuted
  (DSC:CHART-ENGINE-Q03B-FIRST-WHEEL-IS-RENDERER-IDLE-WAKEUP). Does the zoom half stay held,
  is a protocol change admissible under D10, and under which protocol is the lifting receipt
  taken?
answer: >
  The zoom half of the P03 hold STAYS HELD until an mm receipt PASSES under protocol v2; no v1
  receipt can lift it and no v1 number is reinterpreted or excluded. A protocol change is
  admissible only because it is PROSPECTIVE and SEPARATE: it is ruled here before any v2
  receipt exists, it binds both engines, it changes only how zoom inputs are delivered and
  what state the renderer is in when the gesture starts, and it leaves unchanged every budget
  (input_to_present p95 <= 20 ms, p99 <= 33.4 ms), the gesture (60 wheels of deltaY -120 at
  the chart centre), the pan gesture and its lifted result, the run count (3, median run),
  dpr 2, the reference Mac, the load gate (load1 < 24), the measured-vsync requirement, the
  latency definition (first STATE_PRESENTED_ALL frame at or after the input mark, as for pan),
  and the rule that the first input is in the sample with no exclusions. Protocol v2 is:
  (1) WALL-CLOCK DISPATCH - the 60 wheels are sent through one CDP session per gesture as
  `Input.dispatchMouseEvent` (type mouseWheel, deltaY -120 at the chart centre, the parameters
  `page.mouse.wheel` sends) at scheduled wall-clock times t_i = t_(i-1) + g_i with
  g_i = 17 + 6 x u_i ms, u_i drawn from [0, 1) by mulberry32 seeded with a declared constant
  plus the run index (seed in the receipt and on the CADENCE_DIAG line; the same seed sequence
  for both engines); the harness arms a timer to about 2 ms before each target and spins on the
  Node clock to the target, never in the page; the next dispatch never waits for the renderer's
  ack of the previous one, and all dispatch promises are awaited after the end mark. The 20 ms
  mean gap keeps the ~50 Hz workload the v1 loop reached in practice (input_hz 48-50); the
  17 ms minimum exceeds one 60 Hz frame, so two wheels never share a frame; the accumulated
  jitter spreads the phase over the slot the way a device clock does instead of pinning it to
  t_0. (2) AWAKE START - the 200 ms pre-gesture idle is replaced by a harness-side
  requestAnimationFrame heartbeat (empty callback, installed by page.evaluate after
  `installInputMarks` and before tracing starts); the start mark is written after at least
  200 ms of heartbeat; product code is unchanged. Where the heartbeat ends is fixed by a
  mechanism check taken once before the first official receipt, not by a result: if the
  heartbeat-only lead-in presents no frame (`awake_start.leadin_presentations` = 0 in every
  headed check run of both engines) the heartbeat runs through the end mark
  (`heartbeat_mode: "through"`), so the pipeline is awake for every wheel the way v1's
  ack-paced wheels kept it awake; if the lead-in does present frames, a heartbeat frame could
  answer a wheel ahead of the wheel's own frame, so the heartbeat stops at the first wheel
  (`heartbeat_mode: "until-first-input"`). One mode, recorded in the receipt, for both engines.
  (3) RECEIPT - the receipt carries `protocol: "q03b-v2"` and under zoom
  `dispatch: { gap_min_ms: 17, gap_jitter_ms: 6, seed, scheduled: 60, dispatched: 60,
  dispatch_dev_max_ms }`, `awake_start: { heartbeat_ms, heartbeat_mode, leadin_presentations }`
  and the diag-only `answered_by_prior_frame` count (inputs whose answering frame began
  before their mark); `validateCadenceReceipt` requires `protocol` ("q03b-v1" or "q03b-v2")
  and refuses (INVALID, neither PASS nor FAIL) a v2 receipt whose zoom `input_marks` differs
  from `dispatch.scheduled`, whose `input_unpresented` is not 0, whose `dispatch_dev_max_ms`
  exceeds 2 ms, or whose `heartbeat_mode` is "through" with `leadin_presentations` above 0.
  An INVALID run is repeated, never counted and never read. The prior-frame credit the
  unchanged latency definition allows (v1 headless: mm 43/177 inputs, lwc 0/177) is reported
  under v2, not gated. v1 and v2 receipts are not comparable and are never shown in one table
  without the protocol column. (4) ORDER - the protocol change lands on claude/ce-q03c-1013
  (fabric MiniMax executor; independent qwen3.8-max review; vitest pins of the seeded
  schedule, the receipt keys and the INVALID rules; a headless SMOKE showing 60 marks for 60
  scheduled dispatches, dispatch_dev_max_ms <= 2, the first wheel within the range of wheels
  1-59 with the heartbeat and elevated with the 200 ms idle control) and is pushed BEFORE any
  receipt is taken; the seat then runs the headed heartbeat check on the reference Mac (three
  runs per engine: wheel 0 within the range of wheels 1-59 in every run, the idle-200 control
  elevated, `leadin_presentations` read), fixes `heartbeat_mode`, and measures both engines
  under v2 at that head on port 3111; the hold lifts only on the mm v2 receipt with
  input_to_present_p95_ms <= 20 and input_to_present_p99_ms <= 33.4 over all 60 wheel inputs.
  If mm fails under v2 the hold stands and the failure is recorded; the budgets do not move.
  If the heartbeat fails the headed check in both modes, no receipt is taken and the pre-state
  needs a further prospective ruling; pointer hover is not admitted by this one.
rationale: >
  The Q03b hold decision named this exit: a defect that is the harness's, not the engine's,
  is cured by a separate prospective protocol ruling, never by relaxing the result. Both
  diagnoses meet that bar with falsifiers that ran. D1's cure must remove the ack coupling
  itself: with the next wheel scheduled by a wall clock the phase no longer depends on the
  handler, so an engine can no longer improve its score by being slower, and uniform jitter
  over one slot keeps the phase from being pinned by a cadence commensurate with vsync. D2's
  cure must remove the idle, not the input: the first wheel stays in the sample and still
  decides the p99, but it is measured from an awake renderer, which is the state a user's
  wheel finds after any pointer movement over the chart. The budgets stay where they were
  bound (49f0ec2d1). Under v2 on the reference panel the uniform-phase model predicts a p95
  near 20.5 ms for both engines (559 pooled headed inputs: 20.56 ms, 9.2 % above 20 ms), so
  the gate remains able to fail mm on any wheel that needs a third slot, and may fail both
  engines by a fraction of a millisecond; a shared failure is recorded as a shared failure,
  not an engine difference, and the budgets still do not move. That is what keeps it a gate.
  Measuring both engines under v2 preserves the comparison the ledger has carried since Q03.
alternatives:
  - option: >
      Lift the zoom half on the diagnosis alone, since neither defect is an engine cost.
    why_not: >
      The hold rules on a receipt, not a narrative; a gate that cannot fail mm is not a gate.
  - option: >
      Keep v1 and "fix" D1 in canvas/ (a slower wheel handler) or D2 in the product (an idle
      rAF keep-awake).
    why_not: >
      The first games the instrument at the engine's expense; the second burns every user's
      CPU and battery while idle to buy a bench number.
  - option: >
      Exclude the first input, add a warm-up wheel, or raise the zoom gesture to 120 inputs.
    why_not: >
      Post-result workload changes forbidden by D10; and a warm-up wheel followed by the same
      idle still pays the wake-up (headed warm+idle200: mm 35.9/39.7/65.3 ms).
  - option: >
      Start the gesture from pointer hover (crosshair updates) instead of a heartbeat.
    why_not: >
      Crosshair work differs per engine and would reintroduce an engine-dependent pre-state.
  - option: >
      Fixed 20 ms cadence with no jitter.
    why_not: >
      20 ms is exactly two slots of the reference panel, so every wheel would land at one
      phase fixed by t_0; the receipt would measure the start instant, not the renderer.
  - option: >
      Lower the latency budgets to the two-slot floor, or rule on lwc parity.
    why_not: >
      D10 forbids both after a result.
  - option: >
      Stop the heartbeat at the first wheel in every case (the renderer wakes once, then the
      wheels keep it awake).
    why_not: >
      With wall-clock gaps the pipeline can go idle between wheels, and one frame of idle is
      already elevated (headed idle-16: mm 24.8-33.9 ms, lwc 24.0-40.9 ms), so the browser's
      wake-up would enter every wheel's measurement in both engines; the mode is instead fixed
      by the lead-in presentation check, which is a mechanism, not a result.
  - option: >
      Match each input to its own frame (Chromium EventLatency) instead of the first
      presentation after the mark.
    why_not: >
      A definition change that would also touch the lifted pan metric; the prior-frame credit
      is reported under v2 and left to a later ruling if it decides anything.
evidence:
  - >
    DSC:CHART-ENGINE-Q03B-ZOOM-P95-GAP-IS-ACK-PACED-PHASE (lane ce-q03c-d1diag-1013 headless
    breakdown; headed phase bins and spin falsifier at e206cd046).
  - >
    DSC:CHART-ENGINE-Q03B-FIRST-WHEEL-IS-RENDERER-IDLE-WAKEUP (lane ce-q03c-d2diag2-1013 at
    07826dafbc6be94f09e1123ed6424b8d7f4386c6; headed idle dose-response at e206cd046).
  - >
    v1 protocol lines at e206cd046: terminal/bench/chart-engine.cadence.bench.ts:342-350
    (mouse.move, waitForTimeout(200), installInputMarks, start mark, sixty awaited
    page.mouse.wheel calls, end mark); :273-283 pan (unchanged by v2);
    terminal/lib/chart-engine/bench/cadence.ts:76-81 CADENCE_BUDGETS, :142-152 CadenceReceipt,
    :616-650 inputLatencyStats, :949 validateCadenceReceipt;
    docs/chart-engine-completion/bench.md:286-330 "Per-input presentation latency (Q03b)".
  - >
    DEC:CHART-ENGINE-Q03B-ZOOM-HOLD-STANDS-TWO-DEFECTS (the exit this decision takes);
    DEC:CHART-ENGINE-Q03-PAN-LIFTED-ZOOM-RULES-ON-INPUT-LATENCY; masterplan
    08_RISKS_AND_DECISIONS.md:18 (D10); Terminal PR #998 (budgets bound at 49f0ec2d1).
affects:
  - "WS:NATIVE-CHART-ENGINE"
  - terminal/bench/chart-engine.cadence.bench.ts
  - terminal/lib/chart-engine/bench/cadence.ts
  - terminal/lib/__tests__/ (cadence receipt and validator tests)
  - docs/chart-engine-completion/bench.md
  - docs/chart-engine-completion/receipts/**
confidence: high
reversibility: easy
decided_by: coo-fable (seat session 6dfa7fe4-64c1-4a36-a3bc-af2fa0e5ba79)
decided_at: 2026-10-13
supersedes: [DEC:CHART-ENGINE-Q03B-ZOOM-HOLD-STANDS-TWO-DEFECTS]
superseded_by: DEC:CHART-ENGINE-Q03B-PROTOCOL-V4-OWN-FRAME-SWAP-END
---

# DEC-CHART-ENGINE-Q03B-PROTOCOL-V2-WALL-CLOCK-INPUT

Seat ruling 8 of the 2026-10-13 chart-engine completion wave. Supersedes the lift clause of
the Q03b hold decision (the lifting receipt is now a v2 receipt); the hold itself, the pan
lift and every budget carry over unchanged. Workstream
`agentos/workstreams/WS-NATIVE-CHART-ENGINE.md`.

## v1 -> v2 (zoom gesture only; pan unchanged)

| element | v1 (e206cd046) | v2 |
|---|---|---|
| wheel dispatch | 60 x `await page.mouse.wheel(0, -120)` (next wheel on the renderer ack) | 60 x CDP `Input.dispatchMouseEvent` at gaps g_i = 17 + 6 x u_i ms, u_i ~ U[0, 1) from seeded mulberry32, never awaiting the previous ack; dispatch_dev_max_ms <= 2 |
| pre-gesture state | `waitForTimeout(200)` (renderer goes idle) | rAF heartbeat (bench-side) for >= 200 ms; `heartbeat_mode` through / until-first-input fixed once by the lead-in presentation check |
| first input | in the sample | in the sample |
| sample size | 60 | 60 |
| budgets | p95 <= 20 / p99 <= 33.4 | unchanged |
| receipt | no protocol field | `protocol: "q03b-v2"`, `zoom.dispatch`, `zoom.awake_start`, diag `answered_by_prior_frame`; INVALID rules in `validateCadenceReceipt` |
| comparability | — | v1 and v2 never in one table without the protocol column |

## What lifts the zoom half

One official mm receipt taken by the seat on the reference Mac at the Q03c head (after the v2
protocol commit and its review), prod build with `NEXT_PUBLIC_CHART_BENCH=1`, port 3111, load1
below 24, dpr 2, measured vsync, three runs, median run, `protocol: "q03b-v2"`, zoom
`input_marks` 60, `input_unpresented` 0, `input_to_present_p95_ms` <= 20 and
`input_to_present_p99_ms` <= 33.4. The lwc receipt is taken in the same session for the ledger.
A failing mm receipt keeps the hold and is recorded; `budget_ok: false` receipts are not
committed under `docs/chart-engine-completion/receipts/`.
