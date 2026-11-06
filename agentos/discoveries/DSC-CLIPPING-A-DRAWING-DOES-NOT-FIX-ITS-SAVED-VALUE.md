---
key: CLIPPING-A-DRAWING-DOES-NOT-FIX-ITS-SAVED-VALUE
claim: >
  Clipping a chart drawing to the price pane removes the visual symptom of a cross-pane
  gesture while leaving the persisted endpoint on the wrong scale, so the measurement, the
  percentage label, and every later edit or reload of that drawing remain wrong. A render
  mask is never a repair for a value that was already written.
falsifier: >
  Apply only the SVG clipPath, drag a Date + Price Range endpoint from the price pane into
  a Stochastic sub-pane, and read the PUT body to /api/drawings. Finding a price-scale
  value in points[1].p refutes this; finding the oscillator reading (e.g. 44 on a ~$180
  instrument) confirms it.
so_what: >
  When a chart defect is reported as "the shape looks wrong", check the saved document
  before accepting a render-layer fix. For Terminal drawings the fix belongs in the
  gesture's pane ownership (snap() paneLock + clamp before conversion), and the clip is
  kept only as the cosmetic half. Review rule that follows: a regression test asserting
  rendered geometry cannot prove this class of fix, because the clip already satisfies it.
kind: constraint
verified_at: 2026-09-29
verified_by: >
  Mutation control on mastermind-terminal #774: pane lock and clamp removed from snap()
  with #748's clipPath left in place. All 8 persisted-endpoint tests fail (creation,
  endpoint handle, whole-drawing move, Shift+Measure, logarithmic, inverted, coarse
  pointer, collapsed pane) while both tests that assert only clipping still pass. Corrupt
  values observed: 0.39911, -0.835467, -0.341638 against a measured pane floor of
  5.12 +/- 1.71. ChartPanel.tsx restored byte-identical afterwards.
scope:
  - terminal
  - terminal/components/ChartPanel.tsx
  - terminal/e2e/drawing-system.spec.ts
confidence: verified
---

The two halves are independent: ownership decides what is SAVED, the clip decides what is
DRAWN. Shipping only the second is what made the defect look fixed.
