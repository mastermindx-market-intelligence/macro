# Theme List query rendering — bounded repair

The accepted parent is `3acd4fb0efe00793fc9987f1a6e45a512b26e5dd`. The source-bound receipt is [theme-query-reuse-validation.json](theme-query-reuse-validation.json). This is an incremental performance repair to the already delivered complete List and native return path.

## Cause and change

The previous query handler rebuilt the complete matching Theme List through `innerHTML` on every input. Instrumentation separated assignment cost from the browser's script, style and layout duration counters. For the expanded-list clear action, assignment itself took 109.8 ms and the full action-to-second-frame observation took 678.2 ms at 4× CPU throttling.

The view now retains the current complete unfiltered Theme List and reconciles its existing child nodes for query-only changes. Nonmatching rows are detached. Matching rows, links, disclosures and focus keep their DOM identities; counts and the empty state preserve the original semantics. The original full renderer remains the fallback until a full unfiltered list exists.

The cache belongs to one view, clears on full layout (including timeframe, sort, language, theme, data and presentation changes), and is released when that view retires. No data producer, shared navigation, observer, overlay or history owner changed. Search still writes history once and keeps the market summary unchanged.

## Comparable controlled measurements

Same generated page, committed data snapshots, browser, instrumentation, 1440 px viewport, 4× CPU and 26-action sequence. The baseline uses the accepted parent's JavaScript. The candidate uses the generated served asset with its exact digest.

| Action | Before | Candidate | List HTML writes |
| --- | ---: | ---: | --- |
| Theme query a | 216.6 ms | 83.8 ms | 1 → 0 |
| Theme query aapl | 47.7 ms | 28.4 ms | 1 → 0 |
| Expanded Theme query a | 512.4 ms | 121.0 ms | 1 → 0 |
| Expanded Theme clear | 678.2 ms | 175.6 ms | 1 → 0 |

The maximum of the same 26-action probe fell from 678.2 to 292.5 ms. Its median was 126.65 before and 128.55 ms after, so this evidence supports reduced query-tail cost, not a blanket speed-up. Warm ordinary clear remains up to 292.5 ms. Full initial renders and control changes still build complete lists.

The final wider probe exercised eight switch cycles, the incumbent controlled overlay and 100 actions across 1440, 390 and 320 px. Maxima were 391.2, 292.4 and 288.6 ms respectively. All scoped lifecycle, request and browser-error invariants passed. These observations are local stress measurements, not field INP or a latency percentile.

Script/layout/style/task counters include driver input preparation. Their intervals overlap the event-to-frame and HTML-assignment measurements; do not sum them.

## Semantic, return and collection proof

- 90 paired rendered-state comparisons across 1440 EN dark, 390 ZH light and 320 EN light matched the accepted parent. Coverage includes queries, no matches, clear, expanded members, timeframe, sort, language, theme and refresh notifications, counts, order, text, links and logical focus. Candidate-only assertions also prove the same surviving company node remains connected and focused.
- All 45 existing affected return-journey cases passed, producing 29 screenshots and zero page errors.
- 89 shared heatmap Node tests and 84 focused Python contract/helper tests passed. Syntax, diff, paired-asset equality, added-line design, runtime-style and committed-visual-evidence gates passed.
- Separate by-value CDP retention checks at all three widths collected retired views and found zero growth in DOM nodes, documents or event listeners, without extra feed requests or page errors.
- Root inspected actual desktop and phone screenshots for row readability, focus, counts, disclosure layout and clipping. The existing small metric-card ellipsis remains; this phase does not restyle accepted UI.

The locator-driven timing probe still records driver-held node/listener growth. It is explicitly unqualified for retention conclusions; that historic instrumentation artifact was not treated as a product leak. Refresh parity uses an unchanged supplied snapshot, and does not prove live-feed freshness.

## Reproducible evidence

- [Before](../../../ux-evidence/d04-us-heatmap-return-20261104/performance-render-before.json)
- [Comparable candidate](../../../ux-evidence/d04-us-heatmap-return-20261104/performance-render-candidate.json)
- [Final wider timing](../../../ux-evidence/d04-us-heatmap-return-20261104/performance-render-qualified.json)
- [Clean retention](../../../ux-evidence/d04-us-heatmap-return-20261104/retention-render-qualified.json)
- [90 semantic comparisons](../../../ux-evidence/d04-us-heatmap-return-20261104/list-reuse/report.json)
- [45 return cases](../../../ux-evidence/d04-us-heatmap-return-20261104/render-functional/browser-report.json)

All release holds and whole-programme acceptance boundaries remain. No merge, un-draft, enqueue, auto-merge, relabel or deployment is authorized by these results.
