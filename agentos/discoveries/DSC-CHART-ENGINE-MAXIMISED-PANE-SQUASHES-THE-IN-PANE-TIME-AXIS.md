---
key: CHART-ENGINE-MAXIMISED-PANE-SQUASHES-THE-IN-PANE-TIME-AXIS
claim: >
  The mm canvas engine draws its time axis INSIDE a pane (the last one), while
  lightweight-charts keeps the axis in its own always-visible row below every pane. The
  product's pane-maximise control does not remove panes; it re-weights them
  (terminal/components/ChartPanel.tsx:2249 gives the maximised pane stretch 1000 and every
  other pane 0.0001), so on mm every non-maximised pane, including the last one, collapses
  to ~0 px and the time axis, its hit band and the crosshair time label vanished with it.
  Fixed in Terminal PR #1085 (commit 6fe63b53f): the axis belongs to the LAST pane tall
  enough to hold the band (`timeAxisOwnerPane` in
  terminal/lib/chart-engine/canvas/inputBridge.ts:34), and that one rule feeds the painter,
  the separator reserve, the input hit test and the overlay label, so maximising any pane
  moves the axis onto it and restoring moves it back.
falsifier: >
  From terminal/ at a head carrying #1085 run
  `npx vitest run lib/__tests__/chartEngineTimeAxisOwner.test.ts` (7 pass). Replace the
  loop body of `timeAxisOwnerPane` (terminal/lib/chart-engine/canvas/inputBridge.ts:34)
  with `return Math.max(0, paneHeights.length - 1);` (the pre-#1085 "last pane" rule) and
  rerun: fewer than 5 red tests, or a maximised-middle-pane layout whose time-axis band is
  still reported at the chart bottom, refutes the claim. A lightweight-charts build that
  loses its time axis under the same 1000 / 0.0001 stretch factors refutes the "LWC never
  noticed" half.
so_what: >
  Any engine feature that mm implements in-pane but LWC implements in a chart-level row
  (time axis today; a future bottom legend or scroll bar) must be keyed on the VISIBLE pane
  set, not on pane index. The product never deletes panes to maximise, so "last pane" is
  wrong whenever a pane is maximised, and no unit test with equal pane heights can see it:
  parity tests for in-pane chrome need a squashed-pane layout case. The same ~0 px squash
  is why ChartPanel's other per-pane chrome must tolerate a zero-height pane.
kind: landmine
verified_at: 2026-10-19
verified_by: >
  Seat session 6dfa7fe4 on 2026-10-19 in the PR #1085 worktree: the maximised mm chart
  reproduced with no time axis before 6fe63b53f (headed probe at 1440x900, `?engine=mm`);
  `npx vitest run lib/__tests__/chartEngineTimeAxisOwner.test.ts` 7 pass at 6fe63b53f;
  reverting the owner rule to "last pane" made 5 of the 7 red; the full chart-engine
  suites at the PR head ce0a10efe: 88 files, 1460 tests green.
scope: [terminal]
confidence: verified
---

LWC's `ChartWidget` lays out `[pane, separator]* + timeAxisWidget` as DOM rows, so a pane
stretched to 0.0001 of the height takes almost nothing and the axis row keeps its own
height. mm's `layoutHeights` divides the whole chart height among panes by the same stretch
factors and the axis band is reserved inside its owner pane; with the old "last pane" owner
the band was reserved inside a ~0 px pane. The owner rule picks the last pane whose height
is at least the band height (`TIME_AXIS_HIT_HEIGHT_PX`), falling back to the last pane when
no pane can hold the band, and the frame painter, the separator reserve
(terminal/lib/chart-engine/canvas/index.ts:394), the hit test and the crosshair overlay all
read the same function.
