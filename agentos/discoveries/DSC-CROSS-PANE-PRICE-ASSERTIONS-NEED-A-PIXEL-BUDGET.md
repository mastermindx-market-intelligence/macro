---
key: CROSS-PANE-PRICE-ASSERTIONS-NEED-A-PIXEL-BUDGET
claim: >
  A tolerance expressed as a share of the visible price band is not discriminating for
  cross-pane drawing assertions, because the band is wider than the corruption it must
  catch. On a large-cap Terminal chart the band is roughly 7 to 260, while the lowest
  sub-pane is MACD at about -0.8, so a 6% tolerance (+/-15.2) is wider than the 7.7 gap
  between a correct value and a corrupt one. The assertion has to be a PIXEL budget
  (price-per-pixel times a few pixels) anchored on a value measured by a control gesture.
falsifier: >
  In terminal/e2e/drawing-system.spec.ts replace the budget in
  expectClampedToPaneBottom (`band.pricePerPixel * 3`, line 1798 as of this record) with
  any band-proportional tolerance, remove the paneLock and the pre-conversion clamp from
  snap() in terminal/components/ChartPanel.tsx, then run
  `npx playwright test e2e/drawing-system.spec.ts --workers=1 --retries=0`. If the eight
  cross-pane ownership tests still fail, band-proportional tolerance was sufficient and
  this claim is wrong.
so_what: >
  Never assert "the saved value is inside the price band" for a cross-pane gesture: it
  passes vacuously when the gesture never moved, and passes outright whenever a
  neighbouring pane's values happen to fall inside the band. Assert the CLAMP TARGET
  instead, and obtain the expected value by dragging the same tool along the pane's own
  top and bottom edges rather than estimating it. Take the readings at the top and bottom
  EDGES, not as min/max, or an inverted scale silently mislabels which one the target is.
kind: constraint
verified_at: 2026-09-29
verified_by: >
  Observed on mastermind-terminal #774 while building the TERMINAL-04 regression. With a
  6% band tolerance, band = {floor 6.83, ceiling 260.04, tolerance 15.1926} passed against
  corrupt MACD values of -0.835467 and -0.341638. Switching to pricePerPixel * 3 and
  anchoring the calibration at the pane's own edges made all eight tests fail under the
  mutation and pass on the repair.
scope:
  - terminal
  - terminal/e2e/drawing-system.spec.ts
confidence: verified
---

Two Terminal-local traps make such a test silently green if missed. The drawing surface
binds pointermove and pointerup to its own SVG, so a synthetic touch drag whose moves are
dispatched on `window` never commits and the gesture quietly does nothing. And at widths
where the drawing rail sits below the fold, arming a tool scrolls the document, so any
coordinate computed from a box measured before the click lands on the wrong pane —
intermittent by scroll position, so it passes when the test is run alone.
