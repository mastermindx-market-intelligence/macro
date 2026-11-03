# Paper parity acceptance contract — PR #723 PP1/PP2

**Parent disposition: ACCEPTED WITH THE CORRECTIONS IN THIS EDITION.** This is the frozen PP1/PP2 implementation contract; no further routine design sign-off is needed. Preserve the incumbent writer, existing started operations, source/review/CI/deploy gates, and final authenticated visual acceptance. Current Mastermind source pin: `72f44f0b1e2b98aac1f64461a5adea6ba0c31dc7`.

**Purpose and binding.** This is an implementation-ready visual and interaction contract for the incumbent #723 writer (`f77d3f70`; completed `oi-1c`, current `oi-1e` repair, serialized PP1/PP2). It is not a source patch, test result, PR review, or release approval. It resolves the hierarchy that the deployed captures fail: matrix top at **816.625 px** (1440×900), **1082.984 px** (820×1180), and **1804.547 px** (390×844). Map, active scope, and the selected-node action must lead; history and diagnostics must be reachable by progressive disclosure.

**Evidence boundary.** I viewed authenticated live desktop/tablet/phone captures and actual Paper pixels: `paper-reference-BPN-0` at 1440×1024, `paper-reference-F21-0` at 768×1024, and `paper-reference-CYI-0` at 390×844. Paper's actual pixels establish the two-column desktop, side-by-side 768 tablet, and phone map-plus-selection hierarchy. The Paper design-token hash is `55dd37b7` (not a complete document revision); it supplies exact design values below. Paper uses illustrative data only. 820×1180 is a required production viewport, but its Paper adaptation is an acceptance threshold extrapolated from the viewed 768×1024 tablet, not a separately viewed Paper board. The source packet's original six blobs were at `85e4…`; the writer's continuity receipt says five parity blobs are byte-identical at `14a331…` and `037a67…`; `MatrixCompanion` only threads a local `fetchStatus` to the empty state. The original PR branch was fetched at `037a67abe59cd5bbf768a0eaccf2f7ef2ad43b3d`. Reconcile the later chart-engine repair and any future source change before implementation. Thus the visual findings remain applicable, but makes **no claim of candidate tests, CI, integration, or live behavior**.

## Deterministic reading hierarchy

Use the shared `StrikeExpiryMatrix`, reducer, chart pin, MobileSheet, locale, and options snapshot owner. Do not build a second stack.

1. **Header/identity:** show root, session/EOD truth, selected lens, and active scope before the map. Receipt clocks appear only where their payload fields exist; absence is `unavailable`, never an inferred source/build/spot/OI time. 0DTE remains a source-session property, not an intraday clock.
2. **Scope and same-scope totals:** default Gamma with global normalization. Scope controls operate as a draft: Apply commits; Cancel/Escape discards and restores focus. Totals, dominant/opposing node, expiry mix, matrix, inspector, pin, and chart all use one root/session/scope/reducer identity. Global means comparison across the full selected scope, including selected rows and expiries outside the scrolled viewport; per-column remains selectable and visibly warns that colors are not cross-column comparable.
3. **Map and selection:** a readable strike×expiry grid leads. Select a visible cell or dominant node; the selected strike/expiry/value/action becomes adjacent (desktop/tablet) or immediately below the grid (phone). Map colors mean gamma sign/magnitude (cyan positive, violet negative); they must not inherit price-up/down polarity. Missing is hatched/labelled and differs from measured zero. The actual intensity law stays P5–P95 plus square-root and is labelled as such; do not adopt Paper's illustrative `asinh` label.
4. **Inspector and disclosure:** selection supplies exact node context, same-session expiry mix, partial denomination, and pin-to-chart. History, market memory, methodology, and diagnostics follow below or live behind disclosure. Save, draft alert, Observe, per-cell call/put split, and PIT analogs remain held/unavailable; no visual shell may imply activation.

## Reference values and proposed acceptance thresholds

| Surface | Paper values actually exported/viewed | Required production acceptance |
| --- | --- | --- |
| Shared visual language | `#0F1115` page, `#181B21` panel, `#343B48/#343D4B` 1px rules, 8–10px rounded panels; Inter 11–13px metadata, 12px controls/cells, 18–25px title/summary, monospaced tabular metrics. Cyan `#70DAD6`, violet negative semantics. | Reuse compatible Terminal tokens rather than literal duplicate tokens; equivalent contrast and 1px division must be visible in dark and light. Do not use the present bright-blue active-control treatment for exposure sign. |
| Desktop 1440×900 | Viewed 1440 map reference has 56px rail, 44px category row, 66px title row, 90px summary, 50px lens/scope row, then map and ~306px inspector. Its grid has 15 strikes × 8 expiries in the full selected scope. | By y=900, show identity + active scope, same-scope total, at least **7 readable rows and 3 expiry columns**, and selected-node action without document scrolling. At ≥1200px content width use map + inspector two columns; map takes remaining width, inspector 288–320px. |
| Tablet 820×1180 | Viewed 768×1024 Paper board retains map and inspector side-by-side. It shows three expiry columns, seven visible strike rows, a compact header, and a coverage/partial card beneath the map. Exact 44px target sizing below is a proposed production acceptance requirement, not a measurement from screenshot pixels. | At 820×1180 retain side-by-side map/inspector; map must display **≥6 rows × 3 expiry columns** with 44px row targets. Selected action remains in initial reading area; partial/coverage fits beneath the map or after it before history. |
| Phone 390×844 | Viewed board shows compact identity, 44px controls, summary, **7 × 3** matrix, `7/15 strikes · 3/8 expiries shown`, global-scale label, then a selected-cell strip and Inspect action before bottom nav. | At 390×844, display **≥7 44px rows × 3 expiry columns**, current scope and global/per-column state, and selected-cell strip/action before bottom navigation. Grid is horizontally contained; full scope remains 15×8 (or actual source cardinality) and selected totals do not change with scroll. |

The visible-row/column counts are acceptance thresholds, not a claim about any particular live payload. If source cardinality is lower, show all actual rows/columns and retain the count denominator. The existing 101-row display cap is permitted only with visible N-of-M counts and a working reveal-selection route.

## Actual hooks and proposed acceptance hooks

Keep these actual hooks: `[data-options-companion]`, `[data-options-root]`, `[data-options-session]`, `[data-options-scope]`, `[data-testid=options-scope-toggle]`, `options-scope-editor`, `options-scope-expiries`, `options-scope-window`, `options-scope-norm`, `options-scope-apply`, `options-scope-cancel`, `[data-options-total]`, `options-scope-structure`, `options-dominant-node`, `options-opposing-node`, `[data-options-inspector]`, `options-selection-outside`, `options-selection-offscreen`, `options-reveal-selection`, `options-node-context`, and the shared matrix's existing selection semantics.

Add stable **proposed** hooks only if the existing matrix lacks an equivalent: `[data-testid=options-map-layout]`, `options-map-grid`, `options-selected-summary`, `options-inspect-node`, `options-missing-key`, `options-scale-basis`, `options-coverage`, `options-receipts`, `options-newer-snapshot`, and `options-chart-return`. They name browser-observable promises; class names and DOM nesting remain implementation choices.

## Falsifiable browser acceptance (all dark/light and EN/ZH)

1. At 1440×900, 820×1180, and 390×844, the map grid begins before history/diagnostics and meets the row/column thresholds above; no horizontal document overflow.
2. `[data-options-scope]` reports applied vs editing; changing a control changes only draft controls. Cancel/Escape restores prior scope and focus; Apply commits it.
3. Initial Gamma scope uses global normalization. Per-column selection exposes the non-comparable-colors warning; the scale basis says P5–P95/square-root, never asinh.
4. A matrix cell, `options-dominant-node`, and `options-opposing-node` each select the same exact strike+expiry in `[data-options-inspector]`; changing root/session clears stale selection and pins.
5. Selection retains root, strike, expiry, and source session through Map → Pin/chart → return; the chart instance remains mounted and map scroll restores (record before/after scroll position).
6. A missing cell is visually and textually distinct from a numeric zero; partial totals show known/expected denominator and never present known subtotal as complete total.
7. 0DTE filters only the source-session expiry slice. It does not create a live/intraday timestamp or substitute a source session.
8. Exact strike bounds accept finite `From ≤ To` and show DTE; invalid/non-finite/order-invalid input blocks Apply with an explanation, never a zero/empty-data fiction.
9. A newer snapshot announced during node inspection remains queued; it is not silently swapped below selected context/pin. Applying it binds the new session everywhere.
10. Keyboard tab behavior uses the existing perspective tab controls (arrows/Home/End); Escape hierarchy closes scope before companion, and mobile actions remain at least 44px.
11. Receipt fields show only supplied source/build/spot/OI values; missing fields say unavailable. Gamma sign and hedge sign remain separately named and cannot share a polarity label.
12. Held Save, alert, Observe, call/put split, and PIT analogs remain unavailable/labelled held; no POST, persistence, alert activation, or fabricated data follows their rendering.

## Final-source-to-live proof required

The writer must recapture the final exact head after PP1/PP2, bind responsive screenshots and browser assertions to that head, run affected checks plus `npm run test:e2e:responsive`, complete the existing PR #723 carrier's required CI/merge/deploy chain, and then produce authenticated production captures at the three contract viewports. Those captures must prove the final deployed source, current root/session and actual entitlement path. A local fixture, Paper export, source hash, or green isolated check is insufficient.

## Limitations and non-goals

This contract does not invent data, clocks, latency, market values, tests, or production results. It preserves shared renderer/reducer, exact source identity, missingness, gamma-versus-hedge polarity, and staged scope. It does not authorize changes to the held features or release process. Paper screenshot evidence now exists for 1440×1024, 768×1024, and 390×844; only the 820×1180 requirement is a responsive extrapolation pending final product captures.

Parent acceptance retains the raw Sol report unchanged, SHA256 `8d9e09e7b35bb0d8c8689e2e858ac9cb701a31c7091cbb5b150993cdd45e18bd`. Parent corrections: tablet screenshot has seven visible strike rows; tablet44px target is proposed, not a pixel-derived source value; global normalization is full selected scope, not the viewport; custody/current source wording updated.
