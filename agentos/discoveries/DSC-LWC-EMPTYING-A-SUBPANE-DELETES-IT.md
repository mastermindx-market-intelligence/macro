---
key: LWC-EMPTYING-A-SUBPANE-DELETES-IT
claim: >
  In lightweight-charts 5.2.0, removing the LAST series from a pane deletes the pane itself and
  slides every higher pane down. `ChartModel._internal_removeSeries` ends with
  `_private__cleanupIfPaneIsEmpty(paneImpl)`, which splices the pane out of `_private__panes`
  whenever `!pane._internal_preserveEmptyPane() && dataSources().length === 0 && panes.length > 1`.
  `_private__preserveEmptyPane` defaults to FALSE and the Terminal never sets it, so the behaviour
  is always armed. This is what makes the obvious implementation of "recompute a study" —
  `removeSeries()` then `addSeries()` — unusable on a live tick: it destroys and recreates the
  sub-pane, resetting its height and reordering the panes above it, several times a second.
falsifier: >
  `grep -n "_private__cleanupIfPaneIsEmpty" node_modules/lightweight-charts/dist/lightweight-charts.development.mjs`
  and read the guard; `grep -rn "preserveEmptyPane" terminal/{components,lib,app}` returning nothing
  confirms the default still applies. Behaviourally: remove an RSI pane's only series and read
  `chart.panes().length` — it drops by one. A future version that makes `preserveEmptyPane` default
  true, or a Terminal that starts setting it, retires this.
so_what: >
  Never carry a study to a new bar generation by re-creating its series. Re-run the study's OWN
  builder against a chart FACADE whose `addSeries()` hands back the series that key already owns —
  `seriesReuseChart(chart, owned, key)` in `terminal/lib/liveBarProjection.ts`. That keeps exactly
  one owner for the math and the row->point mapping while adding zero lifecycle churn. Two calls
  must be swallowed by the wrapper, and both were found the hard way: `applyOptions` (the post-build
  `keepIndicatorPaneAxisLabelsOnly` pass runs AFTER the builder, so replaying the builder's option
  literals silently re-enables the native last-value line it had just removed) and `createPriceLine`
  (static guides — RSI 80/20, ADX 20/25, MACD 0, Accum bands — would stack one copy per quote). The
  same constraint is why "just remount the chart on each quote" is not an available shortcut.
kind: constraint
verified_at: 2026-09-18
verified_by: "node_modules/lightweight-charts/dist/lightweight-charts.development.mjs:7351 (_cleanupIfPaneIsEmpty) and :5235 (_private__preserveEmptyPane = false); mastermind-terminal PR #636"
scope:
  - mastermind-terminal
  - terminal/components/ChartPanel.tsx
  - terminal/lib/liveBarProjection.ts
confidence: verified
---

# An emptied pane is a deleted pane

```js
// lightweight-charts 5.2.0, ChartModel
_private__cleanupIfPaneIsEmpty(pane) {
    if (!pane._internal_preserveEmptyPane() && (pane._internal_dataSources().length === 0 && this._private__panes.length > 1)) {
        this._private__panes.splice(this._internal_getPaneIndex(pane), 1);
        this._internal_fullUpdate();
        return true;
    }
    return false;
}
```

`_internal_removeSeries` calls it unconditionally on the way out, and `_private__preserveEmptyPane`
is initialised to `false`. The Terminal sets it nowhere, so any sub-pane study whose series are
removed takes its pane with it.

That rules out the two implementations a session naturally reaches for first when a live bar needs a
non-classic study refreshed:

- **remove + re-add the series** — deletes and recreates the pane per quote;
- **re-run `rebuildIndicators()`** — the same thing for every active study at once, plus a full
  re-registration of sync and the overlay pool.

## The shape that does work

A study's builder computes its projection AND creates the series it draws into. A live bar wants the
first half only. `seriesReuseChart` is a `Proxy` over the chart whose `addSeries()` returns
`owned[i]`, wrapped by `reuseSeries()`; everything else forwards to the real chart, bound to it.

A builder's series COUNT is a function of its params, the timeframe and the intraday branch — never
of the bars — so a live tick can only ever ask for exactly what the key already owns. When that
stops holding, `addSeries` throws (`live refresh: <key> asked for more series than it owns`) and the
caller aborts rather than stranding a half-updated study or leaking an untracked series onto the
chart. `terminal/lib/__tests__/liveBarProjection.test.ts` pins that, and pins that a re-run builder
cannot restyle or re-decorate.
