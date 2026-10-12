---
key: CANVAS-AXIS-STRIP-IS-A-QUANTISED-WITNESS
claim: >
  In the Terminal's lightweight-charts canvas a price-axis strip and a pane body are not
  interchangeable witnesses: the price pane's axis label re-renders on every cent while a study
  pane's axis label is rounded, so a correlation harness pairing the two axis strips reports SPLIT
  on a build that is provably correct.
falsifier: >
  Run `node terminal/e2e/tools/canvas-acceptance.mjs BTC-USD 300` in mastermind-terminal against
  production while the served build carries lib/liveBarProjection.ts; it reads COHERENT off the pane
  bodies. Restore the pre-PR-776 revision of that file, which clipped the two price-axis strips
  instead, and re-run against the same build: it reads SPLIT GENERATION. If both revisions agree on
  one build, this finding is refuted.
so_what: >
  A future session must not treat "the region is on the canvas" as sufficient when choosing a visual
  witness; it must also check that the witness and its comparator respond to the same magnitude of
  change. Prefer pane bodies and keep axis-strip counts as diagnostics only. Related: a low pairing
  ratio is not evidence of the defect, because a study can update every tick and still cross no pixel
  boundary, so only a study body that never repaints while the candle moves freely is a real SPLIT.
kind: landmine
verified_at: 2026-09-29
verified_by: >
  mastermind-terminal PR 776 (fix(acceptance)/witness the pane bodies), which quotes the measurement;
  production app.mastermind-x.com served
  8795dfb1e39c676bc62a80f846e1207979333a22 over 90s on BTC-USD 3D — candle axis 84 moves vs study axis
  1 move, against candle body 5 and study body 5; the same build over 300s read 36 candle-body moves,
  35 study-body moves, 35 paired, ratio 0.972.
scope:
  - mastermind-terminal
  - "mastermind-terminal:terminal/e2e/tools/canvas-acceptance.mjs"
  - "mastermind-terminal:terminal/components/ChartPanel.tsx"
confidence: verified
expires: 2026-12-28
---

## Why the axis strips disagree

`lastValueVisible` is true for the bar-derived study line series, so a study pane's axis does carry a
last-value label and the sensor is not structurally blind — which is what makes the trap convincing.
The label is rounded for display. A correct per-tick update therefore changes the study's value
without changing the rendered glyphs or their pixel row, while the price pane's label tracks raw
price to two decimals and repaints on essentially every tick.

Pairing those two sensors measures **label precision**, not generation coherence, and can only ever
return SPLIT. The observed failure was a harness reporting `"SPLIT GENERATION"` with counts
byte-identical to its own RED baseline — 24 candle moves, 0 study moves — against a build that
contained the repair. It was one step from being reported as a live production defect.

A second fault compounded it: an early exit (`candleAt.length < 24`) ended a nominal 240s run in
roughly 10 seconds, so the matching `24` across both lanes was a saturated counter rather than a
measurement. A run that ends far short of its requested window is a fault, not a verdict.

## Discrimination, measured on one build

The cheapest airtight RED/GREEN pair keeps server, build, bundle and market window fixed and toggles
only a boolean: a runtime-gated early return placed immediately after the generation bump, set from
Playwright's `addInitScript`. Read through the dev-only exact witness, 150s per lane:

| | followers starved | fix active |
|---|---|---|
| generation advances | 25 | 25 |
| candle advances | 15 | 9 |
| `ema` advanced on candle | 0 / 15 | 9 / 9 |
| `macd` advanced on candle | 0 / 15 | 9 / 9 |
| `vol` advanced on candle | 0 / 15 | 8 / 9 |

The generation counter advances identically in both lanes; only the followers differ. Local dev
reaches real live crypto quotes by port-forwarding the Quote Hub the app expects on `HUB_PORT`
(default 3100); without it `/api/quote` is dead locally and a "RED" proves nothing.

## Continuation

This sits one layer below the established rule that a study's live value is drawn into the canvas as
a price-axis label and is therefore invisible to `page.textContent()`, `getByText` and every other
DOM assertion. That rule says *choose the canvas*. This record says choosing the canvas is necessary
but **not sufficient**: two canvas regions can both be live, both be plausible, and still disagree
purely by resolution. The comparator half is the part that actually bit.

The dev-only hooks `window.__mmLiveBarGeneration()` and `window.__mmChartOwnership()` are the exact
witnesses in dev and e2e, but they are stripped from the production bundle — `typeof` is
`"undefined"` on app.mastermind-x.com, confirmed 2026-09-29 — so production acceptance has no hook
and must be visual, which is what makes the region choice load-bearing rather than cosmetic.
