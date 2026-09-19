---
key: TERMINAL-ONE-LIVE-BAR-DERIVATION-BOUNDARY
question: >
  When the Terminal chart accepts a live quote that mutates the developing bar, what carries that
  ONE bar generation to every consumer derived from it — the indicator series, the Chart Table /
  visual-intelligence readout, the overlay render pass and the cross-pane sync lookup — without
  recreating the chart, the panes or the React tree?
answer: >
  One derivation boundary, `commitLiveBarGeneration({ appended })` in ChartPanel. The two accept
  paths (`applyLiveSplice` for daily + resampled, `applyIntradayLiveCandle` for the one-second
  aggregate) own ACCEPTANCE ONLY — fold the quote, decide replace-vs-append, refuse an out-of-order
  packet — and then hand the generation to that single function. It recomputes closes, invalidates
  the time->index map, re-`setData`s the classic in-place series via the existing
  `updateAllIndicators`, re-runs every other study's OWN builder through a series-reuse chart facade,
  refreshes `buildIndDataMap` from the SAME bars, repaints status / signals / tag / candle paint,
  schedules the rAF overlay pass, and re-runs Pine under a generation guard. Every built-in study is
  classified once, in `lib/liveBarProjection.ts`, as `inplace-series` / `inplace-rebuild` /
  `render-pass` / `not-bar-derived`; a unit test fails if an `IND_ORDER` key has no class. paneSync's
  `valueAt` resolves through `barIdxMap()` at LOOKUP time instead of a `closeByTime` Map snapshotted
  at registration, which removes the per-tick `reRegisterSync()` entirely. Out-of-order packets are
  refused PER LANE (`acceptsLiveTick`), and replay, EOD basis and non-spliceable bases still
  short-circuit before the boundary.
rationale: >
  The defect was asymmetry between two accept paths, not a missing update in one of them
  (DSC:TERMINAL-LIVE-BAR-MOVED-ONLY-THE-CANDLE). Patching the daily path to match the intraday path
  would have left BOTH of them updating only the classic subset, and would have preserved the shape
  that produced the bug: two hand-maintained consumer lists that drift. A boundary makes the reach of
  a bar generation a single readable list, so the next bar-derived consumer is added in one place or
  not at all. Re-running each study's own builder (rather than teaching the live path to recompute
  studies) keeps ONE owner for both the math and the row->point mapping — the alternative duplicates
  every indicator's projection logic into a second, live-only implementation that can silently
  diverge from the one used on load. The facade exists because the library forbids the obvious
  mechanism: emptying a pane deletes it (DSC:LWC-EMPTYING-A-SUBPANE-DELETES-IT), so the series must
  be reused, not recreated. Per-lane tick ordering is not a detail: the quote hub falls back
  REALTIME -> DELAYED_15M, which moves `asOfMs` back ~15 minutes, and an unscoped comparison would
  freeze the developing candle until the delayed clock caught up — that was found by review AFTER
  the first implementation was already open as a PR.
alternatives:
  - option: Make `applyLiveSplice` call the same three functions `applyIntradayLiveCandle` already called
    why_not: >
      Restores symmetry at the wrong level. `updateAllIndicators()` only re-setData's the classic
      subset, so every day-trade / premium study would still freeze on BOTH paths — measured:
      RVWAP-20 was byte-identical across an intraday tick. It also keeps two consumer lists.
  - option: Re-run `rebuildIndicators()` (the full build path) on each accepted quote
    why_not: >
      It removes and re-adds series, so lightweight-charts deletes each emptied sub-pane and slides
      higher panes down — pane heights and order reset several times a second. It also re-registers
      sync and the overlay pool per tick.
  - option: Remount ChartPanel / recreate the chart on each quote
    why_not: >
      Explicitly fenced by the brief, and it destroys view state: visible range, pane sizing, drawing
      layer and the crosshair all reset per tick. A quote is a data mutation, not a lifecycle event.
  - option: A live-only recomputation of each study inside the live path
    why_not: >
      Duplicates every indicator's projection logic into a second implementation that is exercised
      only by live ticks, so it drifts from the load path silently and is the hardest kind of drift
      to notice — the values are plausible, just wrong.
  - option: Keep `reRegisterSync()` per tick and rebuild its `closeByTime` map each time
    why_not: >
      A full crosshair/range unsubscribe-resubscribe per quote to fix a lookup that should not have
      been a snapshot. Resolving through `barIdxMap()` at lookup time makes the domain track the bars
      for free and deletes the per-tick work.
evidence:
  - "mastermindx-market-intelligence/mastermind-terminal PR #636 (base bb2e2270099eb033199dab58e99d61ee5c384b83)"
  - "RED baseline: terminal/e2e/live-bar-sync.spec.ts against pre-fix source, 3/3 failing on three different limbs (EMA frozen on D replace; every study one bucket behind on 3D append; RVWAP frozen intraday)"
  - "GREEN: same spec 9/9 across desktop 1440x900 / tablet 820x1180 / mobile 390x844"
  - "261-bar fixture, close 125.79 -> 157.24 on one accepted REALTIME quote: EMA-20 130.9186 -> 133.9138, RSI-14 17.9332 -> 82.6194, RVWAP-20 132.6920 -> 137.5976, Chart Table ema 130.9186 -> 133.9138, paneSync valueAt 125.79 -> 157.24"
  - "3D append: paneSync valueAt null -> 157.24 for the new bucket; Chart Table row absent -> present"
  - "terminal/lib/__tests__/liveBarProjection.test.ts (17 tests) pins the registry partition, per-lane tick ordering and the reuse facade"
  - "full vitest 337 files / 5573 passed; chart-adjacent e2e 52 passed + 4 skipped; responsive/layout/drawings/mobile-chart-chrome 97 passed + 71 skipped"
  - "no chart or pane recreation and no range jump asserted in-spec via window.__mmChartAxisOpts()"
affects:
  - mastermind-terminal
  - terminal/components/ChartPanel.tsx
  - terminal/lib/liveBarProjection.ts
  - terminal/lib/paneSync.ts
  - terminal/e2e/live-bar-sync.spec.ts
confidence: high
reversibility: easy
decided_by: session claude/ssd-live-bar-sync-9cf15a
decided_at: 2026-09-18
---

# One bar generation, one derivation boundary

## The boundary

```ts
const commitLiveBarGeneration = ({ appended }: { appended: boolean }) => {
  const rows = barsRef.current; if (!rows.length) return;
  const generation = ++liveGenRef.current;
  closesRef.current = rows.map((r) => r.c);
  barIdxRef.current = { src: null, map: new Map() };   // the time->index map follows the bars
  const closes = closesRef.current;
  if (appended) { applyFutureAxis(); onMeta?.({ total: rows.length }); }
  updateAllIndicators(rows, closes);   // classic in-place series
  refreshLiveStudies(rows, closes);    // every other study, through its own builder
  buildIndDataMap(rows, closes);       // Chart Table + visual intelligence, from the SAME bars
  paintStatus(rows, sliceRef.current);
  renderSignalsRef.current();
  renderTagRef.current?.();
  applySuitePaintRef.current?.();
  scheduleRenderRef.current?.();       // rAF overlay pass (profiles, ORB, cloud fills, pane suites)
  if (dayModeRef.current) setStripBars([...rows]);
  if (liveGenRef.current === generation) schedulePineLiveRerun();   // async work stays guarded
};
```

Nothing else may project an accepted bar. A new bar-derived consumer is added here or it freezes.

## What the accept paths keep

Acceptance, and only acceptance: fold the quote (`spliceDaily`/`foldFinalBucket`/`resampleTf`, or
`mutateLiveCandle`), decide replace vs append, and refuse a superseded packet:

```ts
const tick = { basis: liveQuoteRef.current?.basis ?? "", stamp: liveQuoteStamp(liveQuoteRef.current) };
if (!acceptsLiveTick(liveTickRef.current, tick)) return;
liveTickRef.current = tick;
```

Ordering is **per lane**. Comparing instants across a REALTIME -> DELAYED_15M hub fallback would
refuse every packet for ~15 minutes — a frozen developing candle in production, introduced by the
guard that was supposed to prevent stale repaints. An unstamped basis is accepted rather than
frozen, and an equal stamp is accepted because a corrected print can arrive under the same `ts`.

## Residual, deliberately not carried live

`optlevels` is classified `not-bar-derived`: options levels come from the nightly options build
keyed on the symbol, so a developing bar carries nothing they read. That is a stated contract, not
an oversight — the registry is the place where "this does not follow the live bar" is written down
and test-enforced, which is what stops a study from silently appearing live.

Separately, `buildIndDataMap` is still not called when an indicator is toggled ON (only on data load
and now on a live tick), so a freshly enabled study's Chart Table column stays blank until the next
load or tick. Out of scope for #636 and tracked separately.
