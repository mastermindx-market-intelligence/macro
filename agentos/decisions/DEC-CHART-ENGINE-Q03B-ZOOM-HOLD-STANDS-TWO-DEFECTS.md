---
key: CHART-ENGINE-Q03B-ZOOM-HOLD-STANDS-TWO-DEFECTS
question: >
  The official Q03b per-input presentation-latency receipt (claude/ce-cadence2-1013 at
  e206cd04659b7bbd714f8afbbc12f4f9ceec6a0c; prod build, headed Chromium, dpr 2, three runs,
  Mac M2 Ultra on the 100 Hz panel, vsync_ms 10 measured from the trace, load1 10.2 at run,
  input_unpresented 0 for every gesture) shows the canvas engine ("mm") inside budget on pan
  (input_to_present p95 9.138 ms, p99 9.639 ms) but over budget on zoom (p95 20.562 ms against
  20, p99 37.175 ms against 33.4), with the incumbent lwc on the same host at zoom p95 18.341 ms
  (pass) and p99 38.407 ms (fail). Does the zoom half of the P03 hold lift, and what is the
  defect?
answer: >
  The zoom half of the P03 default-flip hold STAYS HELD. The receipt is valid (input marks
  present, every input presented, vsync measured) and mm fails both zoom latency budgets, so
  per DEC:CHART-ENGINE-Q03-PAN-LIFTED-ZOOM-RULES-ON-INPUT-LATENCY the result is a renderer
  finding and no budget, run count, gesture size or dispatch workload moves (D10). The failure
  is split into two defects with different owners. D1 is mm-only: mm zoom p95 is 20.1, 20.6 and
  20.8 ms on the three runs, 2.2-2.9 ms above lwc (17.9, 18.3, 18.6 ms) on the same host, panel
  and load; that is a cost on the canvas engine's wheel -> zoom -> paint path, owned by
  terminal/lib/chart-engine/canvas/. D2 is shared: the p99 of a 60-input gesture is its single
  worst input, and that input is the first wheel of the gesture in every headed run of both
  engines (33-38 ms, three to four 10 ms slots); because the incumbent pays it too, it sits
  below the engine layer (wheel-listener registration, lazy first-zoom initialisation in the
  host or engines, or the harness's synthetic-input path) and is diagnosed before it is fixed.
  Both are commissioned as Q03c on claude/ce-q03c-1013 (forked from e206cd046): D1 fix lane
  with an independent review, D2 diagnosis lane producing a falsifiable discovery and an
  app-side fix only if the cause is app-side. The pan half stays lifted. What lifts the zoom
  half is one official Q03b mm receipt taken by the seat on the Mac at the Q03c head (a
  descendant of e206cd046 that changes renderer or host code only under Q03c) with load1 below
  24, dpr 2, measured vsync, input_to_present_p95_ms <= 20 and input_to_present_p99_ms <= 33.4
  over the declared zoom workload (60 wheel inputs, no warm-up, no exclusions). If D2 proves to
  be the harness's synthetic-input path, the seat rules prospectively on the protocol in a
  separate decision before any receipt is taken under a changed protocol; the budgets still do
  not move.
rationale: >
  The Q03 decision named this exact exit: a failing Q03b receipt becomes a renderer defect and
  the hold continues. Splitting the failure matters because the two overruns have different
  evidence. The p95 gap is reproducible across all three runs and is absent from lwc under
  identical conditions, so it is attributable to mm and is fixable inside canvas/ without
  touching the instrument. The p99 overrun is carried by one input in every run of both
  engines; treating it as an mm defect would send a fix to the wrong layer, and treating it as
  noise would be the post-result relaxation D10 forbids. A warm-up wheel or a larger n would
  change the declared workload after seeing the result, so neither is admissible; the only
  lawful paths are an app-side fix that removes the cold start for real users, or a
  prospective protocol ruling if the cold start is an artefact of CDP input dispatch that real
  wheels do not pay. Keeping budgets fixed and moving the receipt to the fix head keeps the
  gate meaningful: it can still fail.
alternatives:
  - option: >
      Lift the zoom half on the lwc comparison (mm is within 2-3 ms of the incumbent and
      beats it on pan).
    why_not: >
      The hold rules on absolute budgets bound before measurement, not on parity with lwc;
      D10 forbids substituting a comparison the receipt was not declared to make.
  - option: >
      Add one warm-up wheel before the start mark, or raise the zoom gesture to 120 inputs so a
      single cold-start input no longer decides the p99.
    why_not: >
      Both change the declared workload after the result (D10); the first also hides a cost
      real users may pay on their first wheel.
  - option: >
      Exclude the first input from the latency sample as a known harness artefact.
    why_not: >
      Not yet shown to be a harness artefact; the Q03c D2 diagnosis has to establish that
      with falsifiers before any protocol change, and the change would be a separate
      prospective ruling.
  - option: >
      Treat the whole failure as an mm renderer defect and fix it in canvas/.
    why_not: >
      The p99 input fails identically on lwc, so a canvas/ fix cannot remove it; only the
      p95 gap is mm's.
evidence:
  - >
    Official mm receipt cadence-mm-e206cd04659b7bbd714f8afbbc12f4f9ceec6a0c-m2studio.json
    (median run 2, generated 2026-10-13T19:58Z): pan inputs 200, input_hz 98.9, presented 202,
    dropped 0, presented p95 10.002 / p99 10.002, input_marks 200, input_unpresented 0,
    input_to_present p50 8.271 / p95 9.138 / p99 9.639; zoom inputs 60, input_hz 50.1,
    presented 60, dropped 1, presented p95 30.005 / p99 30.005, input_marks 60,
    input_unpresented 0, input_to_present p50 17.827 / p95 20.562 / p99 37.175; violations
    [zoom.presented_p95_ms, zoom.input_to_present_p95_ms, zoom.input_to_present_p99_ms];
    budget_ok false. Per run zoom latency p95 20.1 / 20.6 / 20.8, p99 37.4 / 37.2 / 32.8;
    pan latency p95 9.2 / 9.1 / 9.0.
  - >
    Official lwc receipt (same session): pan latency p95 9.560 / p99 16.578 (dropped 2); zoom
    input_hz 48.2, latency p50 17.031 / p95 18.341 / p99 38.407; per run zoom p95 17.9 / 18.3 /
    18.6, p99 35.4 / 38.4 / 35.1; budget_ok false (zoom presented p95 30.004, zoom latency p99).
  - >
    Sidecar: head e206cd046, port 3111, load1 7.83 before / 10.17 at run / 9.68 after, display
    vsync_ms 10 / hz 100, host Darwin 25.5.0 24 x Apple M2 Ultra dpr 2, prod build fresh at the
    head with NEXT_PUBLIC_CHART_BENCH=1. Receipts and sidecar are retained by the seat; both
    receipts carry budget_ok false and are not committed under docs/chart-engine-completion/receipts/.
  - >
    Opus P5b cadence orchestrator report (headed Mac smokes at a8a7d484c and e206cd046, nine
    runs across both engines): the nearest-rank p99 of 60 zoom inputs is the largest value and
    in every run it is input 0, the first wheel event; the trace shows two NO_UPDATE BeginFrames
    after the first wheel and one after every later wheel; the penalty appears in both engines.
  - >
    DEC:CHART-ENGINE-Q03-PAN-LIFTED-ZOOM-RULES-ON-INPUT-LATENCY (the exit this decision
    takes); DSC:CHART-ENGINE-PRESENTED-INTERVAL-IS-INPUT-BOUND (why the interval metric could
    not rule); Terminal PR #998 (the Q03b instrument, budgets bound at 49f0ec2d1 before any
    receipt); masterplan 08_RISKS_AND_DECISIONS.md:18 (D10).
affects:
  - "WS:NATIVE-CHART-ENGINE"
  - terminal/lib/chart-engine/canvas/**
  - terminal/lib/chart-engine/bench/**
  - terminal/bench/**
  - docs/chart-engine-completion/**
confidence: high
reversibility: easy
decided_by: coo-fable (seat session 6dfa7fe4-64c1-4a36-a3bc-af2fa0e5ba79)
decided_at: 2026-10-13
supersedes: [DEC:CHART-ENGINE-Q03-PAN-LIFTED-ZOOM-RULES-ON-INPUT-LATENCY]
---

# DEC-CHART-ENGINE-Q03B-ZOOM-HOLD-STANDS-TWO-DEFECTS

Seat ruling 7 of the 2026-10-13 chart-engine completion wave. Supersedes the Q03 decision's
lift clause (the receipt that lifts the zoom half is now taken at the Q03c fix head, which
changes renderer code); the pan lift and the budgets carry over unchanged. Workstream
`agentos/workstreams/WS-NATIVE-CHART-ENGINE.md`.

## Official Q03b receipts at e206cd046 (Mac, prod, headed, dpr 2, 100 Hz panel, vsync 10 ms)

| engine | gesture | inputs | input_hz | lat p50 ms | lat p95 ms | lat p99 ms | per-run p95 | per-run p99 | budget 20 / 33.4 |
|---|---|---|---|---|---|---|---|---|---|
| mm | pan | 200 | 98.9 | 8.271 | 9.138 | 9.639 | 9.2 / 9.1 / 9.0 | 14.3 / 9.6 / 9.3 | PASS |
| mm | zoom | 60 | 50.1 | 17.827 | 20.562 | 37.175 | 20.1 / 20.6 / 20.8 | 37.4 / 37.2 / 32.8 | FAIL (p95, p99) |
| lwc | pan | 200 | — | — | 9.560 | 16.578 | — | — | PASS |
| lwc | zoom | 60 | 48.2 | 17.031 | 18.341 | 38.407 | 17.9 / 18.3 / 18.6 | 35.4 / 38.4 / 35.1 | FAIL (p99) |

Every input was presented (`input_unpresented` 0); the receipts carry `budget_ok: false`
and are therefore not committed under `docs/chart-engine-completion/receipts/`.

## The two defects

| id | who pays | measurement | attribution | owner | exit |
|---|---|---|---|---|---|
| D1 | mm only | zoom lat p95 20.1–20.8 ms vs lwc 17.9–18.6 ms, all three runs | wheel → zoom → paint cost inside the canvas engine | `terminal/lib/chart-engine/canvas/` (Q03c fix lane, independent review) | official Q03b mm receipt at the Q03c head with zoom p95 ≤ 20 |
| D2 | both engines | p99 = the first wheel of the gesture, 33–38 ms, every run | below the engine layer: listener registration, lazy first-zoom init, or the harness's synthetic-input path | Q03c diagnosis lane → DSC with falsifiers; app-side fix only if app-side | zoom p99 ≤ 33.4 on the same receipt, or a separate prospective protocol ruling if D2 is harness-only |

## Hold status after this decision

| half | state | rules on |
|---|---|---|
| pan | LIFTED | unchanged (Q03 interval receipt; Q03b latency agrees) |
| zoom | HELD, two named defects | one official Q03b mm receipt at the Q03c head, budgets unchanged |

## What this decision forbids

No warm-up wheel, no larger zoom n, no exclusion of the first input, no budget change, no
lwc-parity substitute, and no receipt taken under a changed protocol before a separate
prospective ruling. The flip (P03) and the LWC removal (P04) stay behind this hold.
