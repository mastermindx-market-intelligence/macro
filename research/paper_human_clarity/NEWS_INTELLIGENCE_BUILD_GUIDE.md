# News Intelligence — clarity implementation guide

Commission: 8 November 2026. This guide preserves the systems detail removed from the product composition. It implements the Chairman's presentation direction, recorded in DESIGN_DOCTRINE §8. The Paper changes are applied; application behavior and remaining implementation work are distinguished below.

## Current design destinations

Paper file: https://app.paper.design/file/01M5EXPMQTSBFBAM8KKG83FTZH

| Surface | Page and current nodes | Purpose |
|---|---|---|
| Product | p-2-0, gallery 3GX-0; rail 27L-0; activity light 2G9-0 and dark 2JL-0 | Copy/extract the actual child product frames, not the gallery |
| Count help | p-4-0, gallery 3H4-0; How counts work 2NG-0; Sources 2OM-0 | Separate EN/ZH explanations with named returns |
| Legacy states | p-1-0; count detail roots 1-0, H3-0, M3-0 | Exact original charts/tables with concise Sources and How counts work controls |
| Build | p-3-0, gallery 3H0-0; original 27K-0, 1UF-0, 2FG-0, 1FM-0; preserved detail 2QK-0 | Architecture, state contracts, original specimen and relocated paragraphs |
| News rules | 2J5-0 inside Build 27K-0 | Human-first placement rule outside the product |
| Canonical rule | Design System file 01M312VSDSZFVT45674GDVJVZN, p-9-0, law 9X3-0 inside 9ZX-0 | Portfolio-wide design law |

The old specimen and architecture frames remain references. A design-only control is not proof that the application implements it. Canvas galleries arrange complete frames without merging their product and builder contents.

## User workflow

Headlines remain the main task. The activity entry opens a compact count/chart view without changing ticker, source selection, review filter, scroll, expanded report or review status. It shows reports and grouped stories for the last 24 hours, owner-issued activity state, history, one truthful calculation time, and named Sources / How counts work entries. Headlines returns to the prior rail position. Preserve the last focused story or fall back to the feed heading if it disappeared.

“How counts work” is a secondary user explanation, initially closed. It explains units, window, baseline and coverage only when requested. Sources identifies the configured permitted source set and distinct outlet meaning. Published/received audit counts, exact formulas and provenance are below the primary activity view.

Keep partial coverage and missing comparisons visible. The neutral coverage metric never implies sentiment, importance, price direction, trade permission or position size. Do not invent “Live counts” from the rail's live indicator.

## Current source owners

Macro pinned ad00e5676aa94d22918b3b92d8026bd45328536c:

- engine/qbus_news_velocity.py — count, baseline and comparison calculation.
- engine/qbus_news_store.py — source/report/cluster projection.
- app/ticker_news.py — snapshot/error handling and flow inclusion.

Terminal protected master pinned f0af84bbd6c28c2f6477bd8ffc031903979023bd:

- terminal/components/news/NewsFlowStrip.tsx — count summary and disclosure.
- terminal/components/news/NewsFlowTally.tsx — historical chart.
- terminal/lib/newsFlowLex.ts — EN/ZH strings.
- terminal/lib/newsValidation.ts — parser and unavailable isolation.
- terminal/components/news/TickerNewsPanel.tsx — mounting and rail state.
- terminal/components/news/useTickerNewsFeed.ts — snapshot and stream refresh.

Existing Macro design specifications:

- research/product_intelligence_local_delivery/NEWS_RAIL_R3_SPEC_2026-10-22.md governs headline rows, evidence ladders, clocks and review controls.
- research/product_intelligence_local_delivery/WAVE_B_NEWS_FLOW_RAIL_SPEC_2026-10-12.md describes the count feature's original design. Current implementation supersedes stale behavioral statements identified below.
- Existing docs/specimens/news-flow.html and news-flow.light.css in Terminal remain specimen tooling, not proof of a shipped light theme.

## Numeric and data contract — preserve

1. Reports are distinct (source, source_item_id) pairs, active and rights-allowed, with curated/editorial filtering where enabled.
2. Stories are distinct cluster IDs among counted reports; an unclustered report is a singleton story. Two reports about one event remain two reports and one story.
3. Rolling 24-hour and seven-day windows include both ends: [as_of − window, as_of].
4. History is 28 UTC calendar-day buckets, oldest first, excluding the current UTC day. The outlined rolling 24h mark must stay distinct from these daily bars.
5. history_days_observed is the capped calendar span since the earliest eligible report, not verified ingestion-day coverage. Baseline eligibility requires >=20.
6. Typical is the median of all 28 bucket values once eligible. Comparison uses the unrounded median; display rounds to at most one decimal.
7. Busier: r24 >= 2 × median AND r24 − median >=3. Quieter: median >=2 AND r24 <=median/2. Otherwise typical. The client must not recompute these from a rounded displayed median.
8. catching_up/degraded produce partial coverage and no comparison. Available counts may be incomplete. Do not render unavailable as zero or partial as typical.
9. Calculation/parser failure isolates the flow feature and preserves news rows. No permitted source set yields no_accessible_sources.
10. as_of is calculation time in UTC; it is not the latest article's publication timestamp.
11. Only status=active counts; withdrawn and unknown statuses do not.
12. A report must have been received by as_of. Prefer first_received_at, then projection receipt; exclude if neither is readable. A null/blank published timestamp falls back to possession time. An invalid nonempty timestamp can raise, causing flow unavailable through API isolation.
13. Redelivery preserves the first receipt fallback where available. Published-basis and received-basis counts sum to reports_24h; the Terminal parser enforces this.
14. sources_counted is the allowed source set used in calculation, not necessarily contributors in the last 24h. Source IDs and outlet identities differ.

## Known source/spec gaps — do not silently conceal or “repair” by copy

- Current upsert/remove SSE handling triggers a cursor-less first-page snapshot, which recomputes flow. Flow is absent from SSE payloads but can update indirectly after events. Older “never updates from streaming” prose is stale.
- The engine fills 28 buckets with zeros; after eligibility, all enter the median. The chart shows pre-history days as “no record”. Thus no-record values can influence the current baseline as zeros. Preserve this known calculation limitation in methodology/engineering follow-up; do not change the engine in a visual-only pass or claim independently verified collection coverage.
- Older METHOD prose says distinct stories; current METHOD counts distinct reports. Current cluster policy provenance can contain contributing versions or an unknown/pre-column state; do not replace it with a fixed guessed constant.
- The pinned component still combines chart, audit table and paragraphs behind a “?” control. The new separate Activity / Sources / How counts work / Headlines destinations are intentional implementation work, not an existing behavior claim.
- The current strip's Escape-on-opener logic assumes no focusable children. New links/buttons invalidate that assumption.

## State and interaction implementation

Reuse the existing components, parser, backend and state owners. Do not create a second count engine, data store, review ledger or fetch pipeline.

1. Refactor the strip into its existing compact summary and a clearly labelled Activity control.
2. Retain the existing tally; move audit fields into Sources and user methodology. Show the current count/window and state only once in each active view. Preserve missing-history, zero dots, outlined 24h mark and partial treatment.
3. Add accessible named disclosure state using the incumbent component/state patterns. Enter/Space opens; Tab reaches all controls; Escape works from inside; close restores the actual opener and original feed context. Do not put interactive controls in nested buttons.
4. Keep source selection, review actions and report expansion independent. Opening/closing explanations does not mark reports reviewed, change filters or imply persistence.
5. EN/ZH use the current lexicon. Test actual long labels; preserve meaning rather than compress into jargon. Dark is the production target at the pinned source; light/ZH specimens alone do not prove locale/theme rollout.
6. Update specimen generator snapshots if markup changes. Do not edit generated HTML alone; verify the actual component render.

## Focused acceptance before app delivery

- Normal, limited history, empty, recorded zero, partial, stale, unavailable and no-accessible-sources states retain their meaning.
- Current numeric engine outputs are identical across the presentation change; 13 reports/9 stories/limited and 27 reports/12 stories/typical9 examples remain distinct.
- Calendar-day/rolling-window distinction and baseline-null treatment survive.
- Freshness is honest through initial load, refresh, symbol/source changes, stream upsert/remove and failed snapshots.
- Keyboard/touch flows open/close all disclosures, return focus and retain investigation state.
- Narrow viewport, supported EN/ZH and target themes have readable typography, no clipping and adequate controls.
- No builder paths/test names/acceptance prose enters customer component text. No methodology wall is open by default.
- Capture actual browser proof on the implemented component before claiming app delivery. Paper screenshots verify only design.

## Preservation mapping

| Original target | Disposition | Preserved destination |
|---|---|---|
| 27K-0 with 27W-0 builder prose/tokens | Move | Build p-3-0, same IDs |
| 27L-0 product rail | Keep and isolate | Product p-2-0, same ID |
| 28N-0 curation explanation | Move out of repeated default header | Build 27W-0; retain filtering semantics in Sources help |
| 2AH-0 provisional grouping prose | Move duplicated explanation | Build 27W-0; Scope unverified and next-check remain in product |
| 1FM-0 crowded light specimen and all L1–L6 details | Archive intact | Build p-3-0, same IDs |
| 1UF-0 row anatomy / evidence details | Move | Build p-3-0, same IDs |
| 2FG-0 claim comparison architecture | Move | Build p-3-0, same ID |
| Count summary/history | Recompose | Product 2G9-0 light and 2JL-0 dark; cloned original chart semantics preserved |
| 8U-0, JG-0, JJ-0, OB-0, OD-0 | Move intact | Build 2QK-0; exact methods and counting caveats retained |
| 6J-0, H6-0, M8-0 | Move shell/specimen annotations | Build 2QK-0 |
| Legacy detail controls | Add named help entries | 2QO-0, 2QU-0, 2R0-0; minimum 40px control height in these specimens |
| New EN/ZH methods | Separate user explanation | 2NH-0 / 2NK-0 inside 2NG-0 |
| New EN/ZH source details | Separate user explanation | 2ON-0 / 2OR-0 inside 2OM-0 |

## Applied verification

The principal rendered the final light and dark compact activity references after their final placement. The 27 reports / 12 stories and 13 reports / 9 stories examples remain distinct; the limited-history gap and outlined rolling-24h mark remain visible. Count time is explicitly UTC. EN and ZH actions fit without footnote walls. The original count graphs were cloned, not redrawn from guessed numbers.

Legacy details were checked after relocation: exact charts, counts, units and source data remain; implementation paragraphs are outside the product. Build text and new help contrast were inspected. Parent and row membership for the Product, Help and Build galleries were read back after arrangement.

See APPLIED_EFFECTS.json for the applied node maps and FINAL_QA.json for scope and evidence. These are Paper design checks. The browser/keyboard/stream/permission cases above remain the application's delivery acceptance; this task did not implement or deploy them.
