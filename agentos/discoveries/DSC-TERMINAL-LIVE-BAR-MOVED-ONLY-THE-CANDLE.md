---
key: TERMINAL-LIVE-BAR-MOVED-ONLY-THE-CANDLE
claim: >
  Until PR #636 the Terminal chart had TWO live-quote accept paths with DIFFERENT reach, and
  neither reached everything. `applyLiveSplice()` (daily + every resampled timeframe) folded the
  quote into the bars and repainted the CANDLE, status, signals and the price tag, but never ran
  `updateAllIndicators()`, `buildIndDataMap()` or any study rebuild — so every indicator, the
  Chart Table and the visual-intelligence readout stayed on the PREVIOUS bar while the candle beside
  them moved. `applyIntradayLiveCandle()` did call all three, but `updateAllIndicators()` only
  re-`setData`s the classic subset (ema, bb, vwap, vol, rsi, stochrsi, macd), so every day-trade and
  premium study froze on the intraday path too. Measured on a 261-bar deterministic fixture whose
  final close moved 125.79 -> 157.24 on ONE accepted REALTIME quote: on D (replace) EMA-20 held
  130.9186, RSI-14 held 17.9332, RVWAP-20 held 132.6920 and the Chart Table `ema` cell held
  130.9186 — all identical to their pre-tick values, with the candle already at 157.24. On 3D
  (append / new bucket) it was worse: the appended bar carried NO study point at all (every study's
  last point stayed stamped 2026-08-06 while the candle was 2026-08-07), the Chart Table had no row
  for the new bucket, and cross-pane sync answered `null` for the new timestamp because
  `reRegisterSync()` had captured a `closeByTime` Map snapshot at registration time. On the intraday
  path RVWAP-20 measured byte-identical (183.3387) across the tick.
falsifier: >
  Run `terminal/e2e/live-bar-sync.spec.ts`. It drives one accepted quote against the fixture and
  reads every witness in one settled generation through the dev-only `window.__mmLiveBarGeneration()`
  hook. Three green tests (D replace, 3D append, intraday 1m) across desktop/tablet/mobile disprove
  the stale half of this claim; deleting `commitLiveBarGeneration`'s body and re-running reproduces
  it, which is how the RED baseline was taken (3/3 red, each on a different limb).
so_what: >
  Do not "fix the live chart" by patching one consumer. Everything downstream of `barsRef.current`
  now belongs to ONE boundary, `commitLiveBarGeneration({ appended })` (DEC:TERMINAL-ONE-LIVE-BAR-
  DERIVATION-BOUNDARY); add a new bar-derived consumer THERE or it will silently freeze exactly like
  these did. Two specific traps this cost time on. (1) A canvas screenshot cannot witness this class
  of defect at all — the candle is correct in every frame; the witness has to be numeric. (2) A
  cached array can be a FALSE witness: `indOverlayRef.vprofile.rows` is the same array object the
  in-place last-bucket rewrite mutates, so on the replace case it looked fresh BEFORE the fix. Assert
  a recomputed scalar (the profile's POC) instead of a value read back out of the structure under
  test. Also note `buildIndDataMap` is NOT called when an indicator is toggled on, only on data load
  and now on a live tick — that residual is real and separate.
kind: landmine
verified_at: 2026-09-18
verified_by: "mastermindx-market-intelligence/mastermind-terminal PR #636; terminal/e2e/live-bar-sync.spec.ts; terminal/components/ChartPanel.tsx applyLiveSplice / applyIntradayLiveCandle"
scope:
  - mastermind-terminal
  - terminal/components/ChartPanel.tsx
  - terminal/lib/liveBarProjection.ts
  - terminal/lib/paneSync.ts
confidence: verified
---

# One accepted quote used to move the candle and nothing else

The chart accepts a live quote in exactly two places. Before #636 they had different reach, and
the difference was invisible in any screenshot: the candle is right in every frame.

| witness, one accepted REALTIME quote (close 125.79 -> 157.24) | D · replace | 3D · append | intraday 1m |
|---|---|---|---|
| candle close / time | moved | moved (new bucket) | moved |
| EMA-20 | **frozen** 130.9186 | **one bucket behind** | moved |
| RSI-14 | **frozen** 17.9332 | **one bucket behind** | moved |
| RVWAP-20 (day-trade suite) | **frozen** 132.6920 | **one bucket behind** | **frozen** 183.3387 |
| Chart Table `ema` cell | **frozen** 130.9186 | **row absent** | — |
| paneSync `valueAt(lastTime)` | **frozen** 125.79 | **null** | — |

After: every cell above is current in the same settled generation — EMA-20 133.9138, RSI-14
82.6194, RVWAP-20 137.5976, table `ema` 133.9138, sync 157.24, and on the appended bucket a study
point, a table row and a resolvable sync timestamp all exist.

## Why the two paths differed

`applyLiveSplice()` is the daily/resampled lane (`spliceDaily` -> `foldFinalBucket` -> `resampleTf`).
It updated the price series and the bar refs, invalidated the time->index map, repainted status /
signals / tag / candle paint and scheduled Pine — a deliberate, bounded list that simply never grew
the indicator half. `applyIntradayLiveCandle()` (via `lib/liveCandle.ts`) did call
`updateAllIndicators`, `buildIndDataMap` and `reRegisterSync`, which is why the classic overlays
looked live there and made the daily gap easy to misread as "indicators just don't update live".

They do not have a common consumer list any more; they have a common BOUNDARY.

## The sync map was a snapshot, not a lookup

`reRegisterSync()` built a `closeByTime` Map at registration time and closed over it. A replace
therefore mirrored a stale price to peer panes, and an APPEND produced a timestamp the map had
never heard of — `valueAt` returned `null`, which is the crosshair simply going blank on the newest
bar. Resolving through `barIdxMap()` at lookup time fixes both and made the per-tick
`reRegisterSync()` (a full crosshair/range unsubscribe-resubscribe on every quote) unnecessary.

## What a screenshot could not have caught

All three RED runs and all nine GREEN runs turn on numbers that live in the chart's own refs, not
in pixels. `window.__mmLiveBarGeneration()` (dev-only, deleted on unmount, alongside the existing
`__mm*` hooks) returns the candle, every indicator series' tail, the `indRowsAt` row, the registered
`peerValueAt` answer and the recomputed volume-profile POC in one call, so all witnesses are read
inside a single settled generation rather than across frames.
