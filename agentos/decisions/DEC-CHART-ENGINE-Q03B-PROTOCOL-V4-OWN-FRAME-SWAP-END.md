---
key: CHART-ENGINE-Q03B-PROTOCOL-V4-OWN-FRAME-SWAP-END
question: >
  The official Q03b protocol-v2 receipt at 1b7ec6a6b5ed was a VALID FAIL (mm zoom
  input_to_present p95 21.655 / p99 42.429 ms vs <= 20 / <= 33.4). On 2026-10-18 the Chairman
  approved commissioning a prospective protocol on the new diagnosis that every CDP wheel is
  held behind InsertVisualStateCallback before the Browser forwards it
  (DSC:CHART-ENGINE-Q03B-CDP-WHEEL-HELD-BEHIND-VISUAL-STATE-CALLBACK), budgets unchanged. The
  first draft, v3 (anchor = the Browser forward), failed its own pre-registered fidelity check
  before any receipt (DSC:CHART-ENGINE-Q03B-NEXT-FRAME-ANSWER-IS-NOT-THE-WHEELS-OWN-FRAME).
  Under D10, which rules does the protocol that is actually measured (v4) consist of, what does
  it leave unchanged, and what does each outcome of its single official receipt decide?
answer: >
  Protocol v4 ("q03b-v4") changes the zoom ANSWER, ANCHOR and ENDPOINT and nothing else. ANSWER:
  each zoom wheel is answered by its OWN frame as Chromium attributes it, the renderer-pid
  EventLatency async slice (category exactly "cc,benchmark,input,input.scrolling", event_type
  MOUSE_WHEEL) whose BrowserMainToRendererCompositor stage begin is the unique mutual-nearest
  match of that wheel's Browser RenderWidgetHostImpl::ForwardWheelEvent within 0.1 ms (forward
  k's nearest EventLatency, whose nearest forward of any delta is forward k; an EventLatency
  claimed by two forwards maps neither; an EventLatency id that begins again while still open
  drops both slices, so its wheel goes unmapped). An EventLatency that terminates without a swap-end
  stage (its update rode a later frame) is answered by the first EventLatency, ordered by its
  Commit stage begin, that has both a Commit and a swap-end stage and whose Commit begins
  at-or-after the terminated slice's end (frames sharing a Commit begin take the LATER swap
  end). ENDPOINT: the GPU swap end of that frame, i.e. the
  begin of its SwapEndToPresentationCompositorFrame stage; the OS display stage after the swap
  is excluded (Chairman ruling 2026-10-18); a swap end later than the zoom end mark + 100 ms is
  unpresented. ANCHOR: forward_k minus the busy part of the CDP hold, bias_k = max(0,
  min(busy_k, forward_k - mark_k)), where busy_k = end - mark_k of the outermost renderer-main
  (CrRendererMain) X slice with category token "toplevel" that satisfies start <= mark_k < end,
  else 0 (a task contained in an earlier task is nested and dropped; one that only partly
  overlaps it is kept from the earlier task's end); latency_k = swapEnd_k - (forward_k - bias_k). The forward pairing (FIFO by index,
  0 <= forward - mark <= 30 ms) is kept from v3. RECEIPT: protocol "q03b-v4"; the zoom record
  carries v3's `forward` block plus `own_frame: { mapped, fallback, map_max_ms, bias_p50_ms,
  bias_max_ms, main_tasks }`; the zoom gesture records the extra trace categories "input" and
  "toplevel". INVALID (q03b-v4), neither PASS nor FAIL, when own_frame.mapped !=
  dispatch.scheduled, map_max_ms > 0.1 or main_tasks < 1, in addition to every v3 rule
  (forwards or paired != scheduled, stamp-to-forward outside [0, 30] ms) and every v2 rule
  (input_marks != scheduled, input_unpresented != 0, dispatch_dev_max_ms > 2, heartbeat
  "through" with leadin_presentations > 0). The bench validates BEFORE it prints: an INVALID
  run prints only a CADENCE_INVALID line with no latency, and is repeated unread and never
  counted; the INVALID attempt count of the session is reported alongside the receipt.
  UNCHANGED: the 60 CDP wheels (deltaY -120, chart centre, gaps 17 + 6u ms from
  mulberry32 seeded 0x51c03b00 + run index, acks never awaited), the >= 200 ms "through"
  heartbeat, the budgets (input_to_present p95 <= 20 ms, p99 <= 33.4 ms, nearest-rank, all 60
  wheels, first wheel in the sample, no exclusions), 3 runs with the median run chosen by pan
  p95, dpr 2, the reference Mac (M2 Studio, 100 Hz), port 3111, load1 < 24, prod build with
  NEXT_PUBLIC_CHART_BENCH=1, headed, METRIC_ORDER, and the pan gesture, its answer rule and its
  lifted result. PASS CRITERION: the zoom half rules on the official mm v4 receipt being VALID
  with zoom input_to_present_p95_ms <= 20 AND input_to_present_p99_ms <= 33.4. The receipt's
  aggregate `budget_ok` is not the criterion: it also evaluates the presented-frame INTERVAL
  limits, which an input-bound zoom on a 100 Hz panel reads at 20.004 ms, so a v4 PASS receipt
  still shows budget_ok false (DEC:CHART-ENGINE-Q03-PAN-LIFTED-ZOOM-RULES-ON-INPUT-LATENCY).
  OUTCOMES: the receipt is taken ONCE by the seat at the merged master head that carries
  Terminal PR #1050 (mm, with the lwc receipt in the same session for the ledger only). On a
  PASS, P03 (default engine flip to mm) proceeds, then P04 LWC retirement at least one release
  later. On a VALID FAIL the hold stands, the result is recorded, budgets and workload do not
  move, and v4 is never re-run or amended; any further change needs another prospective DEC on
  a new falsifiable diagnosis. The v2 VALID FAIL stands as recorded. v1-v4 receipts are never
  compared without the protocol column.
rationale: >
  The v2 decision's exit is a prospective ruling that removes a harness artefact, never a
  relaxed result. v3 removed the CDP hold by anchoring at the forward, but its pre-registered
  B1 check (written before any statistic was computed) failed on all four deciding diag runs on
  both criteria: (P1) the next-frame answer shared by v1, v2 and v3 is an EARLIER frame than the
  wheel's own frame on 58/59, 58/59, 59/60 and 53/57 wheels, by a median of 20.00 ms (two
  vsyncs), so no Q03b receipt so far measured the frame the wheel produced; (P2b) the forward
  anchor excludes real main-thread congestion, p95 shifts 2.49 / 3.14 / 1.29 / 6.65 ms against a
  1.0 ms tolerance. The B1 outcome rules, set before the result, prescribed exactly the two
  remedies v4 adopts (answer = the wheel's own EventLatency frame; anchor = forward minus the
  busy part of the hold), so v3 was never measured. The bias is capped at the hold (f - m)
  because an OS wheel arriving at the mark would have waited for the spanning task but never
  for the CDP-only remainder, and is zero when no task spans the mark. ENDPOINT, DISCLOSED AS A
  POST-RESULT CHOICE: the B1 pre-registration did not fix the endpoint. A diagnostic estimate
  (diag traces with extra trace categories, not receipts) at the PERF-C head gave own-frame mm
  p95/p99 18.20/18.98 ms to swap end and 36.58/37.00 to presentation, lwc 28.89/34.03 and
  48.64/50.72; the seat therefore referred the endpoint to the Chairman, who ruled "stop at GPU
  swap" on 2026-10-18 before any v4 receipt. The basis: the median
  SwapEndToPresentationCompositorFrame stage is 20.08 ms (mm) / 15.4 ms (lwc), the macOS
  display stage after the GPU swap that no web engine controls; the budgets bound at PR #998
  were calibrated against a next-frame answer that, per B1, never contained the wheel's own
  display stage, and a presentation endpoint fails every engine by construction against the
  unchanged 20 ms p95 (the original masterplan Q03 budgets are presented-frame interval limits,
  not input-to-display). Every engine-side cost (CDP-free input wait, main-thread dispatch,
  rAF, paint, commit, raster, GPU swap) stays inside the interval and the first wheel stays in
  the sample. PRE-REGISTERED EXPECTATION, disclosed because v4-coded numbers were seen on diag
  traces before the receipt: the PR #1050 v4 code on the same diag traces gives mm p95/p99
  18.065 / 18.962 ms (PERF-C head) and 20.290 / 27.166 ms (pre-PERF-C), lwc 28.839 / 44.898 and
  28.292 / 31.096. The expectation is an mm PASS with about a 2 ms p95 margin that the
  official receipt (receipt categories only, quiet host) may still fail, and an lwc FAIL; the
  gate stays able to fail mm. TASK-RULE SENSITIVITY: using every outermost renderer-main X
  slice instead of "toplevel" slices changes no bias by more than 0.080 ms and the PERF-C mm
  p95/p99 by 0.019 / 0.016 ms, so the task rule does not decide the outcome.
alternatives:
  - option: >
      Take the v3 (forward-anchored, next-frame) receipt as drafted.
    why_not: >
      Its own pre-registered fidelity check failed before any receipt: it answers with an
      earlier frame than the wheel's own and excludes 1.3-6.7 ms of real congestion at p95.
  - option: >
      End the interval at the presentation timestamp of the wheel's own frame.
    why_not: >
      Includes the ~15-20 ms OS display stage after the GPU swap, which no web engine controls,
      and fails both engines by construction against the unchanged 20 ms p95; the Chairman
      ruled the swap end. Lowering or raising a budget instead is forbidden by D10.
  - option: >
      Anchor at the v2 receipt mark (no hold removal) with the own-frame answer.
    why_not: >
      Re-admits the CDP-only InsertVisualStateCallback wait that an OS wheel never pays; the
      bias term keeps only the part of that wait an OS wheel would also have paid.
  - option: >
      Count every main-thread X slice (not only "toplevel") as busy time.
    why_not: >
      Nested slices are parts of one task, so only the outermost counts; the "toplevel" token
      is Chromium's own task marker. Measured sensitivity is <= 0.080 ms per wheel.
  - option: >
      Drop a wheel whose EventLatency terminated without presenting.
    why_not: >
      Exclusions are forbidden; the fallback answers it with the first later presented frame
      that carries its update, so every wheel stays in the sample.
  - option: >
      Inject the wheels at the OS level (CGEventPost) so no CDP hold exists.
    why_not: >
      CGPreflightPostEventAccess is false on the reference Mac; granting it is a macOS privacy
      (TCC) change outside the seat's authority.
  - option: >
      Lift the zoom half on the diagnosis, on the diag estimate, or on lwc failing the same
      budgets.
    why_not: >
      The hold rules on a receipt, never a narrative, a diag trace or parity.
evidence:
  - >
    Chairman rulings in the seat session on 2026-10-18: "approved to commission new protocal
    with new diagnosis" (budgets unchanged; lightweight-charts attribution deferred by the same
    message), and the endpoint answer "Stop at GPU swap", given before any v4 receipt.
  - >
    Terminal PR #1050 (branch claude/ce-q03b-v3-1018), commit bc93b035d4a2 implements v4 on top
    of the v3 forward pairing (9e85a8acc0c1) and PERF-C (dfd18572c), with the fail-closed
    parsing repairs of d0dc7aa09595:
    terminal/lib/chart-engine/bench/cadence.ts:112-150 (protocol note), :191-212 (v4
    constants), :1635-1947 (parseWheelEventLatencies, the mutual-nearest mapping,
    rendererMainTopLevelTasks, ownFrameLatenciesMs, cadenceOwnFrameBlock,
    ownFrameAnsweredByPriorFrame) and :2345-2408 (own_frame shape and the three q03b-v4 INVALID rules);
    terminal/bench/chart-engine.cadence.bench.ts:610-700 (own-frame rows) and :840-860
    (validate before print, CADENCE_INVALID only).
  - >
    terminal/lib/__tests__/chartEngineCadence.test.ts 99 pass; twelve source mutations each
    turn the suite red (M1-M13 without M10, an equivalent mutant: answer = first committed
    frame, no bias, uncapped bias, tail ignored, no competitor-forward check, no duplicate-claim
    check, fallback admits swap-less frames, each of the mapped and map_max INVALID rules
    dropped, and each of the three audit repairs reverted). An independent Python oracle of the
    rule, repairs included, reproduces the TS rows on all four diag traces with 0 mismatches.
  - >
    Independent read-only audit of the v4 code before any receipt (verdict REPAIR_REQUIRED),
    repaired prospectively in d0dc7aa09595: (F1) a top-level task that only partly overlaps an
    earlier one (separately rounded ts/dur) was dropped and is now kept from the earlier task's
    end; (F2) an EventLatency id begun again while open overwrote the first slice and now drops
    both (fail closed: the wheel goes unmapped, so the run is INVALID); (F3) fallback frames
    tied on Commit now take the later swap end, so the order is input-independent. None of the
    three occurs on the seven diag traces (partial overlaps 0, reused open ids 0, Commit ties
    with different swap ends 0), and the four deciding traces' v4 rows are byte-identical
    before and after, so the pre-registered expectation stands unchanged. (F5) the session's
    INVALID attempt count is reported with the receipt so a repeated-until-VALID run is
    visible. (F7) the 0.1 ms map ceiling stays; real map offsets are 0.006-0.053 ms and a
    larger offset fails closed.
  - >
    Counts-only mechanism check at bc93b035d4a2 (receipt trace categories only, headed, load1
    about 160, so not a receipt; no latency printed, the receipt JSON and traces deleted): the
    INVALID rules refused 5 of 6 attempts (dispatch_dev_max_ms 2.14-12.05 > 2; one attempt also
    had an unpresented wheel and mapped 59), and the one VALID-shaped mm attempt had 60 marks,
    60 forwards, 60 paired, 60 mapped, map max 0.023 ms, 0 fallbacks and 1138 top-level
    main-thread tasks; both engines' zoom traces carry the input, input.scrolling and toplevel
    categories and one EventLatency per forward. The official receipt therefore needs the
    quiet host (load1 < 24) the protocol already requires.
  - >
    DSC:CHART-ENGINE-Q03B-NEXT-FRAME-ANSWER-IS-NOT-THE-WHEELS-OWN-FRAME (the B1 result);
    DSC:CHART-ENGINE-Q03B-CDP-WHEEL-HELD-BEHIND-VISUAL-STATE-CALLBACK;
    DSC:CHART-ENGINE-PERF-C-FRAME-COST-CUT;
    DSC:CHART-ENGINE-Q03B-V2-FIRST-WHEEL-ELEVATION-PERSISTS-WITH-HEARTBEAT.
  - >
    DEC:CHART-ENGINE-Q03B-PROTOCOL-V2-WALL-CLOCK-INPUT (the protocol this supersedes and the
    exit it takes); DEC:CHART-ENGINE-Q03-PAN-LIFTED-ZOOM-RULES-ON-INPUT-LATENCY (zoom rules on
    input latency, not interval budgets); masterplan 08_RISKS_AND_DECISIONS.md:18 (D10);
    Terminal PR #998 (budgets bound at 49f0ec2d1).
affects:
  - "WS:NATIVE-CHART-ENGINE"
  - terminal/lib/chart-engine/bench/cadence.ts
  - terminal/bench/chart-engine.cadence.bench.ts
  - terminal/lib/__tests__/chartEngineCadence.test.ts
  - docs/chart-engine-completion/receipts/**
confidence: high
reversibility: easy
decided_by: >
  Chairman (approval to commission the new protocol and the GPU-swap endpoint ruling,
  2026-10-18); remaining rules set by the seat (session 6dfa7fe4-64c1-4a36-a3bc-af2fa0e5ba79)
  under the B1 pre-registration
decided_at: 2026-10-18
supersedes: [DEC:CHART-ENGINE-Q03B-PROTOCOL-V2-WALL-CLOCK-INPUT]
---

# DEC-CHART-ENGINE-Q03B-PROTOCOL-V4-OWN-FRAME-SWAP-END

Recorded before any v4 receipt exists. No v3 receipt was ever taken: the v3 draft (forward
anchor, next-frame answer) failed its pre-registered B1 fidelity check and was replaced by v4
before measurement. Supersedes the v2 decision only in the zoom answer, anchor, endpoint and
the added INVALID rules; the hold, the pan lift, the budgets and the workload carry over
unchanged. Workstream `agentos/workstreams/WS-NATIVE-CHART-ENGINE.md`.

## v2 -> v4 (zoom only)

| element | v2 (1b7ec6a6b5ed) | v4 |
|---|---|---|
| answer | first STATE_PRESENTED_ALL frame at-or-after the mark | the wheel's own EventLatency frame (fallback: first later presented frame by Commit) |
| endpoint | that frame's presentation | that frame's GPU swap end (OS display stage excluded) |
| anchor | `cadence:zoom:input` mark (CDP receipt stamp) | Browser forward minus the busy part of the hold |
| new INVALID rules | — | v3: forwards / paired != 60, stamp-to-forward outside [0, 30] ms; v4: mapped != 60, map max > 0.1 ms, no top-level main-thread task |
| receipt | `protocol: "q03b-v2"` | `protocol: "q03b-v4"` plus `zoom.forward` and `zoom.own_frame` |
| PASS criterion | VALID and zoom input_to_present p95 <= 20, p99 <= 33.4 | unchanged (budget_ok false on interval limits is not the criterion) |
| inputs, seed, heartbeat, budgets, runs, environment, pan | — | unchanged |

## Pre-registered expectation (diag traces, not receipts)

| engine | head | v4 p95 | v4 p99 | expected receipt outcome |
|---|---|---|---|---|
| mm | PERF-C (367f488e5c67 + PR #1050) | 18.065 ms | 18.962 ms | PASS, ~2 ms p95 margin — may still fail |
| mm | pre-PERF-C | 20.290 ms | 27.166 ms | (stress case, not measured) |
| lwc | PERF-C | 28.839 ms | 44.898 ms | FAIL |

A VALID FAIL is final for v4. The receipt is taken once, at the merged master head that
carries Terminal PR #1050; `budget_ok: false` receipts are kept out of
`docs/chart-engine-completion/receipts/` and their numbers are recorded in this workstream.
