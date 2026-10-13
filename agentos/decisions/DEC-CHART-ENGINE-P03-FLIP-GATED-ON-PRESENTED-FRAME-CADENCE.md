---
key: CHART-ENGINE-P03-FLIP-GATED-ON-PRESENTED-FRAME-CADENCE
question: >
  The official bench receipts for the canvas engine ("mm") at claude/ce-perf-1013
  8395ceea9 pass 4 of 6 budgets but miss pan/zoom p95 (about 40 ms / 20 ms against an
  18 ms budget), and the rented engine ("lwc") shows the same pan floor on the same
  harness. May the P03 default-engine flip (mm as the default, lwc as rollback) proceed
  on those receipts, either by reading the miss as a harness artifact or by lowering the
  budget to the observed floor?
answer: >
  No. The P03 flip is HELD until a presented-frame cadence trace taken at the same head
  (Chromium PipelineReporter frames in STATE_PRESENTED_ALL, measured over a real pan drag
  and a wheel-zoom burst) shows p95 <= 20 ms and p99 <= 33.4 ms for mm. The hold is lifted
  only by that measurement; budgets, corpus size, run count and drift tolerances are never
  lowered after a result. The existing pan/zoom p95 numbers are recorded as Q03
  NAMED-UNRESOLVED, neither accepted nor failed.
rationale: >
  The bench harness drives pan with 200 synthetic mouse moves separated by a 16 ms wait
  and zoom with 60 wheel events separated by a 50 ms wait, then takes frame deltas around
  that dispatch. Both engines flooring at the same pan value is consistent with the harness
  measuring its own input cadence rather than the renderer, but the same data cannot tell a
  slow renderer from a slow driver. A proxy that cannot distinguish the two is not evidence
  of a pass, and a parity argument against lwc is not a presentation measurement. The
  masterplan's cadence acceptance names an actual presentation trace with no rAF or
  draw-call proxy, and its D10 rule forbids moving a target after a result. The user-facing
  blast radius of a default flip is the whole Terminal chart surface, so the flip waits for
  the one instrument that can rule.
alternatives:
  - option: >
      Lower the pan/zoom p95 budget from 18 ms to the observed floor (about 40 ms) and
      accept the receipts.
    why_not: >
      D10 forbids lowering a target after a result; a budget tuned to the output measures
      nothing.
  - option: >
      Accept the receipts on parity: lwc shows the same floor, so mm is no worse.
    why_not: >
      Parity on an input-cadence proxy is not a presentation measurement; the acceptance
      criterion is an absolute presented-frame cadence, not relative to the rented engine.
  - option: >
      Flip the default now behind the existing one-flag rollback and measure in production.
    why_not: >
      Rollback limits damage, it does not replace acceptance; the flip is user-facing and
      the instrument that can rule is buildable in one lane.
evidence:
  - >
    Official bench protocol: Terminal docs/chart-engine-completion/bench.md (prod-mode
    build with NEXT_PUBLIC_CHART_BENCH=1, headed Chromium, 1440x900 at dpr 2, three runs,
    budgets first_paint 150 / pan,zoom p95 18 / live 4 / screenshot 50 / heap 60).
  - >
    Harness mechanics: terminal/bench/chart-engine.bench.ts pan loop = mouse.move +
    waitForTimeout(16) x200, zoom loop = mouse.wheel(0,-120) + waitForTimeout(50) x60;
    frame deltas and p95 in terminal/lib/chart-engine/bench/corpus.ts.
  - >
    Receipts taken 2026-10-13 ~15:00Z on the Mac at claude/ce-perf-1013 8395ceea9:
    mm budget_ok=false (4/6, pan_p95 ~40 ms, zoom_p95 ~20 ms); lwc pan_p95 at the same
    floor. Not committed (budget_ok=false receipts never enter docs/chart-engine-completion/receipts/).
  - >
    Cadence instrument commissioned 2026-10-13 15:16Z as lane OPUS-P5 (branch
    claude/ce-cadence-1013 stacked on ce-perf): CDP Tracing with the
    disabled-by-default-devtools.timeline.frame category, presented = STATE_PRESENTED_ALL,
    window = first input dispatch to last dispatch + 100 ms, absence of records is a
    FAILURE, never a rAF fallback.
affects:
  - "WS:NATIVE-CHART-ENGINE"
  - terminal/lib/chart-engine/bench/**
  - terminal/bench/**
  - docs/chart-engine-completion/**
confidence: high
reversibility: easy
decided_by: coo-fable (seat session 6dfa7fe4-64c1-4a36-a3bc-af2fa0e5ba79)
decided_at: 2026-10-13
---

# DEC-CHART-ENGINE-P03-FLIP-GATED-ON-PRESENTED-FRAME-CADENCE

Seat ruling 5 of the 2026-10-13 chart-engine completion wave. Workstream:
`agentos/workstreams/WS-NATIVE-CHART-ENGINE.md`. Work package P03 (default flip) and
P04 (lwc retirement) both wait on this gate; P04 additionally waits for the P03
transition release.

## What lifts the hold

One official cadence receipt per engine, taken on the Mac in prod mode at the perf head
(or a descendant that changes no renderer code), showing for mm:
`pan_p95 <= 20 ms`, `pan_p99 <= 33.4 ms`, `zoom_p95 <= 20 ms`, `zoom_p99 <= 33.4 ms`,
with `presented` counted from PipelineReporter STATE_PRESENTED_ALL records only, partial
presentations counted separately, dropped frames never counted, and the input rate
recorded alongside. A receipt with no trace records, an unmoved visible range, or a
device pixel ratio other than 2 is INVALID and does not rule.

## If the trace fails

Q03 becomes a real renderer finding: it goes back to the canvas owner as a defect against
`terminal/lib/chart-engine/canvas/`, the P03 flip stays held, and the rented engine stays
the default. The budget still does not move.
