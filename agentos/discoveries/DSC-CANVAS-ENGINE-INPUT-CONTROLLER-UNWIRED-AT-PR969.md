---
key: CANVAS-ENGINE-INPUT-CONTROLLER-UNWIRED-AT-PR969
claim: >
  At the PR #969 squash (origin/master e0ffafc1f) and on every programme branch cut from it
  (integrate2, paint2, model2, lwcprim, migration) the owned canvas engine's input controller
  `terminal/lib/chart-engine/canvas/input.ts` (pan, wheel zoom with the I02 anchor law, tap and
  long-press, kinetic decay) is complete and unit-tested but is imported by nothing in
  `canvas/index.ts`; `CANVAS_CAPABILITIES.kineticScroll` is therefore `false` and a ChartPanel
  mount that requests kinetic scroll is refused by `createCanvasEngine` before construction, so
  the "mm" engine falls back to LWC and has no pointer interaction at all when mounted directly.
falsifier: >
  A `git grep -n "input" -- terminal/lib/chart-engine/canvas/index.ts` on any of those heads that
  shows an import of `./input`, or a canvas engine instance on those heads responding to a
  pointer drag, would disprove the claim. The claim is dated: once the integrate3 wave (lane
  ce-kinetic-1013) merges, it stops holding for later heads.
so_what: >
  Conformance-lane "done" reports for a renderer module are not evidence that the module is
  wired into the engine; a parity census must include an import-graph check from the engine
  entry point, and the production proof of "mm is selected" must come from a runtime marker
  (`data-chart-engine`) rather than from the URL parameter alone.
confidence: verified
kind: landmine
verified_at: 2026-10-13
verified_by: >
  `git grep -n "from \"./input\"\|input.ts" origin/<branch> -- lib/chart-engine/canvas` run from
  terminal/ for integrate2 (48df88ae8), paint2 (55a7eb94e), model2 (3c25edb86), lwcprim
  (4e0fb5780), migration (fccfb4e14): only lib/__tests__/chartEngineInput.test.ts imports it;
  canvas/index.ts:63 `kineticScroll: false`, :133-135 refusal push; ChartPanel bag passes
  `kineticScroll: { mouse: true, touch: true }` (integrate2 :3989).
scope:
  - terminal
  - chart-engine
---

Resolution commissioned on 2026-10-13: lane ce-kinetic-1013 (grok-4.6, ubuntu0) wires
`createInputController` into `CanvasEngine`, flips the capability, keeps the refusal gate strict
for genuinely unsupported options, and adds the identity marker lane ce-engid-1013
(`container.dataset.chartEngine = impl`).
