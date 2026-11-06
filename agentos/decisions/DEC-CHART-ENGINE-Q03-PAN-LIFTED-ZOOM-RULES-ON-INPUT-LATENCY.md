---
key: CHART-ENGINE-Q03-PAN-LIFTED-ZOOM-RULES-ON-INPUT-LATENCY
question: >
  The official presented-frame cadence receipts (claude/ce-cadence-1013 at
  453f92fb4e7a74504292aaf250edbf79ed27bb67, stacked on master 2c16b32e6; prod build,
  headed Chromium, dpr 2, three runs, Mac M2 Ultra on a 100 Hz panel, load1 21.4) show
  the canvas engine ("mm") inside budget on pan (p95 10.002 ms, p99 20.003 ms) but at
  20.004 ms zoom p95 against the 20 ms budget, with one presented frame per wheel input
  at 50.2 Hz dispatch and no frame later than two vsync slots. Is the P03 hold lifted,
  and what rules the zoom half?
answer: >
  The PAN half of the P03 hold is LIFTED on that receipt. The ZOOM half is neither lifted
  nor failed by the presented-interval metric: at 50 Hz wheel dispatch on a 100 Hz panel
  the interval cannot read below two vsync slots (20.004 ms) whatever the renderer does,
  so the metric measures the harness there. Budgets stay at p95 <= 20 ms / p99 <= 33.4 ms
  (D10). The zoom half rules on the Q03b per-input presentation latency (each input
  event's timeStamp to the first STATE_PRESENTED_ALL presentation at or after it; p95 <=
  20 ms, p99 <= 33.4 ms, dropped frames never counted, panel refresh measured from the
  trace and stored in the receipt), whose budgets were bound in code on
  claude/ce-cadence2-1013 (49f0ec2d1) before any Mac receipt. The P03 default flip stays
  held until the Q03b receipt for mm passes; P04 still waits for the P03 transition
  release.
rationale: >
  The interval receipt satisfies every validity condition of the P03 decision (trace
  records present, STATE_PRESENTED_ALL only, partial separate, dropped reported, input
  rate recorded, dpr 2, visible range moved) and pan is inside budget with 200 inputs
  at 97.8 Hz presenting 202 frames, so the pan half is decided by the instrument the hold
  named. For zoom the same receipt shows presented_per_input = 1 and dropped = 1 of 60:
  the renderer presents every wheel input in the very next slot, and the 20.004 ms is the
  wheel spacing (19.9 ms) rounded up to the panel's 10.002 ms vsync quantum. Reading
  20.004 as 20 would be a post-result relaxation; keeping the hold on a metric that
  cannot read lower would be a hold with no exit. Per-input presentation latency is
  attributable to the renderer and independent of dispatch rate, and its budgets were
  committed before the first measurement, so it can rule without violating D10.
alternatives:
  - option: >
      Treat 20.004 ms as meeting the 20 ms budget (vsync quantization) and lift the hold.
    why_not: >
      D10 forbids post-result relaxation, and a pass on an input-bound metric would not
      be evidence of renderer cadence either.
  - option: >
      Raise the wheel dispatch rate to 100 Hz or more so intervals can read one slot.
    why_not: >
      Changing the declared workload after the result is the reduced-workload comparison
      D10 names; it would still measure dispatch, not presentation.
  - option: >
      Lower the zoom p95 budget to the observed 20 or 30 ms floor.
    why_not: >
      D10.
  - option: >
      Keep the hold on the interval metric and wait for a passing receipt.
    why_not: >
      The metric cannot pass at the declared workload on this panel, so the hold would
      never resolve and would decide nothing.
evidence:
  - >
    Official mm receipt cadence-mm-453f92fb4e7a74504292aaf250edbf79ed27bb67-m2studio.json
    (generated 2026-10-13T18:23:22Z): pan inputs 200, input_hz 97.8, presented 202,
    partial 0, dropped 0, p50 10.002, p95 10.002, p99 20.003; zoom inputs 60, input_hz
    50.2, presented 60, partial 0, dropped 1, p50 20.004, p95 20.004, p99 30.005;
    violations [zoom.presented_p95_ms 20.004 > 20]; budget_ok false. Three runs: zoom
    p95 30 / 20 / 20, pan p95 10 / 10 / 10.
  - >
    Official lwc receipt (18:23:38Z): pan 10.003 / 20.004 (dropped 3), zoom 30.006 /
    30.019 (input_hz 47.6), budget_ok false. Same input floor, same reading.
  - >
    Sidecar: head 453f92fb4, port 3111, load1 15.92 before / 21.44 at run / 24.42 after,
    displays 2 x 3440x1440 at 100 Hz and 2 x at 50 Hz; refresh inferred from the 10.002 ms
    interval quantum. Build fresh at the head (Turbopack compiled at 18:22Z, #994
    lastGenerationByPrimitive present in the server chunks).
  - >
    DSC-CHART-ENGINE-PRESENTED-INTERVAL-IS-INPUT-BOUND (the floor mechanism and reading
    rule); Terminal PR #995 (the interval instrument); claude/ce-cadence2-1013 49f0ec2d1
    (input_to_present_p95_ms 20 / input_to_present_p99_ms 33.4 bound before any receipt).
  - >
    Masterplan 01_MASTERPLAN.md:215 (presented-frame interval p95 <= 20 ms, p99 <= 33.4 ms,
    actual presentation trace) and 08_RISKS_AND_DECISIONS.md:18 (D10: bind budgets and
    workload prospectively; no post-result target lowering).
affects:
  - "WS:NATIVE-CHART-ENGINE"
  - terminal/lib/chart-engine/bench/**
  - terminal/bench/**
  - terminal/lib/chart-engine/canvas/**
  - docs/chart-engine-completion/**
confidence: high
reversibility: easy
decided_by: coo-fable (seat session 6dfa7fe4-64c1-4a36-a3bc-af2fa0e5ba79)
decided_at: 2026-10-13
supersedes: [DEC:CHART-ENGINE-P03-FLIP-GATED-ON-PRESENTED-FRAME-CADENCE]
superseded_by: DEC:CHART-ENGINE-Q03B-ZOOM-HOLD-STANDS-TWO-DEFECTS
---

# DEC-CHART-ENGINE-Q03-PAN-LIFTED-ZOOM-RULES-ON-INPUT-LATENCY

Seat ruling 6 of the 2026-10-13 chart-engine completion wave. Supersedes the P03 gate
decision's lift condition; the hold itself continues. Workstream
`agentos/workstreams/WS-NATIVE-CHART-ENGINE.md`.

## Official receipts at 453f92fb4 (Mac, prod, headed, dpr 2, 100 Hz panel)

| engine | gesture | inputs | input_hz | presented | dropped | p50 ms | p95 ms | p99 ms | budget 20 / 33.4 |
|---|---|---|---|---|---|---|---|---|---|
| mm | pan | 200 | 97.8 | 202 | 0 | 10.002 | 10.002 | 20.003 | PASS |
| mm | zoom | 60 | 50.2 | 60 | 1 | 20.004 | 20.004 | 30.005 | p95 over by 0.004 (input-bound) |
| lwc | pan | 200 | 94.1 | 205 | 3 | 10.002 | 10.003 | 20.004 | PASS |
| lwc | zoom | 60 | 47.6 | 61 | 0 | 20.004 | 30.006 | 30.019 | input-bound |

Both receipts carry `budget_ok: false` and therefore are not committed under
`docs/chart-engine-completion/receipts/`; the values above are the record.

## Hold status after this decision

| half | state | rules on |
|---|---|---|
| pan | LIFTED | this receipt (P03 lift condition met literally) |
| zoom | HELD, NAMED-INPUT-BOUND | Q03b per-input presentation latency for mm, p95 <= 20 ms and p99 <= 33.4 ms, measured refresh in the receipt |

## What lifts the remaining hold

One official Q03b receipt for mm taken on the Mac in prod mode at the cadence2 head (or a
descendant that changes no renderer code) with load1 below 24 and dpr 2, showing
`input_to_present_p95_ms <= 20` and `input_to_present_p99_ms <= 33.4` over the declared
zoom workload, with every input assigned its own latency, dropped frames never counted,
and `display.vsync_ms` measured from the trace. A receipt without input marks is
INVALID. If it fails, Q03 becomes a renderer defect against
`terminal/lib/chart-engine/canvas/` and the flip stays held; the budgets do not move.
