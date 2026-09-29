---
key: TERMINAL-CHART-OWNERSHIP-IS-FLAT-NOT-LEAKING
claim: >
  Terminal's ChartPanel does NOT leak chart resources across symbol/timeframe
  churn. Measured over 53 settled generations (52 alternating symbol/timeframe
  transitions across 4 symbols x 3 timeframes), live ownership is bit-identical
  on every single generation: 10 series / 10 tracked / 0 orphans / 3 panes
  [6,1,3] / 0 custom price lines / 1 marker plugin / 1 paneSync registration /
  11 DOM overlays / 15 canvases. Compare add/remove, overlay-indicator
  add/remove, sub-pane insert+reorder, chart-family swap and replay enter/exit
  each round-trip exactly (3 distinct signatures over 25 samples, every excursion
  returning to the identical base). Final unmount leaves 0 canvases and 0
  product-owned resources. The raw-lightweight-charts call-site counts that
  motivated the suspicion (45 chartRef.current, 51 .addSeries vs 9
  .removeSeries) are ARCHITECTURAL DEBT SIGNALS, NOT leak evidence: the removals
  are loop bodies over owner maps, so the ratio is expected.
falsifier: >
  Any generation in e2e/chart-ownership-stress.spec.ts reporting a non-zero
  orphanSeries / orphanPricePaneLines, or a monotonically rising series/canvas
  count, refutes the flatness claim for that churn class. The discriminators are
  NOT vacuous: both were mutation-tested by injecting a real leak (skipping a
  removeSeries; anchoring price lines off-pool) and both caught it at the FIRST
  generation (18 orphan series; 3 orphan price lines). A churn class the spec
  does not exercise is out of scope of the claim, not covered by it — the known
  uncovered path is Pine hlines, which need a Supabase-backed saved script
  (lib/scriptsFixtureDb.ts is read-only) and are covered by adapter unit tests
  instead.
so_what: >
  Stop commissioning "ChartPanel leaks" investigations from call-site counts
  alone; the census is cheap (window.__mmChartOwnership() in dev, or the e2e
  spec) and settles it in one run. Chart Engine P2/P3 migration is therefore
  justified as DEBT REDUCTION and renderer replacement, never as a leak fix, and
  must not be scheduled on a memory-pressure rationale. Three genuine
  stale-ownership defects DID exist and were repaired in the same PR (Pine
  hlines anchored on a foreign series escaping the indicator price-line pool;
  clearChartData not clearing Pine studies; teardown not detaching the
  session-shading primitive nor nulling the TTM/MACD marker-plugin refs) — none
  of them leaked under symbol/timeframe churn, which is exactly why counting
  call sites found them and counting memory would not have.
kind: runtime
verified_at: 2026-09-18
verified_by: "terminal PR #635 (mastermindx-market-intelligence/mastermind-terminal) — ChartEngine.inventory() over lightweight-charts' own public surface (chart.panes() -> pane.getSeries() -> series.priceLines()), dev probe window.__mmChartOwnership, e2e/chart-ownership-stress.spec.ts 4/4 desktop, lib/__tests__/lwcAdapter.test.ts 62/62, both discriminators mutation-proven"
scope:
  - "terminal"
  - "terminal/components/ChartPanel.tsx"
  - "terminal/lib/chart-engine/"
  - "chart engine P2/P3 planning"
confidence: verified
---

Measurement plane, for anyone re-running this: the census must read
lightweight-charts' own public surface, never the adapter's `this.series` map —
ChartPanel still creates series raw, so that map is empty and a census built on
it reports a confident zero. Note also that `ISeriesApi.priceLines()` returns
only `createPriceLine` lines; the automatic last-value line is invisible to it,
so `priceLines: 0` at steady state is correct, not a broken probe.

The remaining chart-engine debt is real but separate from this claim: ChartPanel
still owns ~5 raw series families, marker plugins, price lines and the shading
primitive through `unwrap()`, so every new family must remember to register with
the right owner map. The recommended next bounded slice is moving price-line
ownership behind the contract (`SeriesHandle.createPriceLine` + handle-scoped
disposal), because that is the family where a miss is silent.
