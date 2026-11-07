# D04 — Builder guidance and acceptance plan

**D04-SPEC/0.1.0. This is a design/build specification, not a product implementation commission.** No application, API, database, route or production configuration was changed. Implementation follows actual reference acceptance and a later Chairman commission. Current foundations and native composition remain blocked as recorded in [PAPER_REVIEW_AND_GATES.md](PAPER_REVIEW_AND_GATES.md).

## 1. What a builder should construct

Build a coherent discovery-to-shortlist journey around the existing analytical objects: a dense result table/map, source-qualified selection and comparison, context inspection, exact named return, and explicit owner-qualified saving. Keep the evaluators separate. A technical confluence rate, a Top Picks rank, a flow measure, a fund holding change and a dislocation episode are different evidence. There is no new universal opportunity score.

The [113-capability ledger](CAPABILITY_LEDGER.md) is the regression contract. The [route/data contract](ROUTES_AND_DATA.md), [compatibility map](COMPATIBILITY.md) and [interaction specification](PRODUCT_AND_UX.md) are authoritative within this candidate's scope. The proposed inspector/comparison/return adapters must compose with F01/F02 and incumbent owners; they do not create new navigation, auth, membership, retry, queue or persistence services.

## 2. Exact code boundaries

Paths below are inspected at the pins in [SOURCE_INDEX.md](SOURCE_INDEX.md). They identify where later changes belong; they are not claims that each listed file needs editing.

| Boundary | Existing files / producer | Reuse and proposed change | Owner / shared risk |
| --- | --- | --- | --- |
| Technical Confluence | Macro `templates/confluence_screener.html.j2`; `scripts/build_confluence_screener.py`; `engine/tech_confluence.py`; `site/factordata/tech_confluence.json` | Retain evaluator, rank, variable D/W recipe and access. Recompose comparable rows, correct train/test/month-mean labels, add explicit availability and generation agreement through existing adapter. | D04; producer owner; shared auth. Do not alter miner calculations to fit a design. |
| Top Picks | `templates/discovery.html.j2`; `scripts/build_discovery.py`; existing top_picks/residual_alpha/equity_factors/extension helpers | Reuse rank/entry dimensions, source session and stock links. Apply common evidence/return presentation without merging signal families. | D04; existing model owners; D07 detail. |
| Curated baskets | `scripts/build_baskets.py` → `scripts/build_theme_detail.py:build_detail_pages` → `templates/basket_detail.html.j2`; `data/baskets/membership.json`; `lib/pages.py` | Preserve catalog49 and regional template inputs, score/timing/history/member depth; add explicit curation/back-projection and comparison receipts. | D13 membership; D05 sector return; D19/D20 regional consumers. A US change to shared template requires representative regional review. |
| Basket gateway | `templates/baskets.html.j2` with build-supplied theme_ids | Preserve validated theme/narrative/no-JS resolution and multi-script ordering. | D05 receiver; D04 incoming path. |
| Quant Lab | `templates/advanced.html.j2`; `scripts/build_site.py:build_advanced_page`; cross_asset/portfolio snapshots and factor/holdings context | Preserve all ten analytical anchors and real matrix/risk/stress/factor sections. Use progressive disclosure only after task/anchor parity. | D04; F01/F02/F03; existing model owners. |
| ETFs | `templates/etfs.html.j2`; `_etf_macros.html.j2`; four shared row partials; existing holdings_signals/etf_board/etf_consensus producers | Keep public backdrop/coverage and server-protected graded rows in parity. Do not fork static/hydrated rendering. | D04; source producers; auth. |
| Movers | `site/movers.html` inspected authoritative receiver | Preserve fixed replacement to Stocks hub and canonical/noindex/follow/no-JS behavior. No invented separate builder. | Stocks hub owner; D04 compatibility. |
| Macro heatmaps | `templates/sector_heatmap.html.j2`; shared `templates/heatmap.js`; build_sp500_heatmap/build_themes_heatmap invoked by build_site | Reuse source-dependent sizing/aggregation, palette/neutral thresholds, timeframe availability, payload stock_url and refresh. Strengthen full-scope/table/coverage access. | Shared heatmap consumers and D05; avoid breaking regional overlays. |
| Sector compatibility | `templates/si_workspace.js`; `templates/subsectors.js`; Sector Central template | Preserve24 merged mappings, special receivers, four datasets and scroll/lazy-mount semantics. D04 supplies a change request if its integration needs an owner change. | D05 owns; D04 does not duplicate that workspace. |
| Discover shell/body | Terminal `app/(shell)/discover/page.tsx`; `components/workspaces/DiscoverWorkspace.tsx`; existing active-pane mounts | Retain six tabs, SignupGate, pushState, chooser, shell event and explicit reset nonces. Integrate shared context using F01 seam, not a parallel router. | F01 plus pane owners; D04 body. |
| Screener | `components/ScreenerView.tsx`; `components/SmartScreensPanel.tsx`; existing technicalScreenControls, fundamentalScan and Smart Screen predicate/client/record modules | Preserve all criteria and three-valued logic. Make device/account save scope explicit and keep existing CAS/ACK/pending machinery. | Existing Smart Screens owner; D23 save boundary. |
| Terminal heatmap | Existing HeatmapView/HeatmapPageRoot and `lib/heatmapCapitalization.ts`; flow/manifest adapters | Keep PRICE/FLOW, MAP/TABLE, sizing definitions, full-scope calculations and bounded overlays. Add qualified comparison/return adapters after reference acceptance. | D04 and data producers; membership D13. |
| Dislocations | `app/(shell)/dislocations/page.tsx`; `components/dislocations/DislocationsView.tsx`; `lib/dislocations/types.ts`; `/api/v1/dislocations` | Preserve episodes, states, knowable-at order, evidence, delayed bars and access. Improve unavailable/stale-empty meaning without numeric score invention. | Existing detector/API owner; D07 detail. |
| Save persistence | Current `/api/smart-screens`, current `/api/thesis-saved-views`, current savedViews and client owner modules; draft#778 typed candidate separately | Reuse each exact owner. The typed heatmap definition and recovery migration are dependencies. Do not append unsupported fields to validators or introduce D04 storage. | D23; current Smart Screens owner. |
| Global search / exact return | F01 companySearchContext, incumbent route/history events and D07 destination seam | Extend only through qualified owner contract. Prove same-document, same-origin and explicitly approved cross-origin handoff separately. | F01/D07; no global D04 context store. |

Detailed immutable file links, including exact Terminal subpaths, are in the source index. F03 owns organization and canonical crosswalk updates; no file/page moves or registry replacement occur here.

## 3. Implementation sequence after admission

1. **Freeze the reference inputs.** Obtain qualified F01/F02 releases, reconcile their original unknown effects with their owners, and obtain exact D04 file/page/anchor/writer admission. Re-read target and overlap, compose the normal-data task and material states, capture actual artboards, and complete independent review. No final domain freeze on candidate chrome.
2. **Lock source meaning and compatibility.** Agree with existing producers on count units, availability, identity, clocks and corrections. Preserve the24 mappings,49 basket IDs, six tabs, detail hosts and regional fragment boundaries. Correct Confluence training/test/month-mean language before any misleading new presentation ships.
3. **Implement display adapters at current seams.** Pass through existing domain payloads with explicit field metadata. Keep data evaluation server/source-owned and local filters in their existing grammar. Add meaningful table access and stable selection; never derive full-scope breadth from the rendered500 tiles.
4. **Integrate return and comparison.** Prove exact normal return before adding save. Use membership versions and observation receipts; disclose replay limits. Restore after layout with generation checks and logical anchors. The same-origin and cross-origin paths require separate evidence.
5. **Integrate owner-qualified saves.** Preserve current device, Smart Screen and thesis behaviors. Adopt typed heatmap only when D23 has qualified schema/migration/readback. Review included and excluded fields: #778 does not store arbitrary display/comparison settings or full recovery drafts. Keep original request custody and no blind duplicate create.
6. **Run regression and accessibility paths, then staged release only under later authority.** Complete all applicable cases below with realistic payloads and failure injection. Update accepted immutable references if behavior changes. Route implementation through existing CI/review/deployment ownership. No automatic merge/deployment is implied by this plan.

Parallel implementation is permissible only on separable owned files with actual grants. Shared shell, source template, save owner and Paper canvas remain coordinated single-writer surfaces. A waiting dependency blocks only its lane.

## 4. Reference composition and component boundaries

Use F01 header/nav/global-search/assistant/inspector slots once. Use released F02 typography, semantic color, spacing, table, button, select, chip, disclosure, dialog, status and data-format roles. Bind exact token/component identifiers from the released catalog; do not invent approved token names in this candidate. Preserve existing authorized local assets. No remote asset import or branding copy is needed.

The primary object is the dense map/table or three comparable Confluence ranks. A small scope/quality strip and an inspector support it. Avoid a decorative hero or a generic card feed that eliminates comparison. Make values, units and sample bases readable at the actual available content width. Colored container borders/accent stripes are prohibited by current doctrine; focus outlines remain legitimate.

At candidate geometry, useful widths are288/358/728/788/1008/1168/1328px for320/390/768/1024/1280/1440/1600 viewports. A320px dock plus24px gap leaves664/824/984 at1280/1440/1600. These are calculations, not measured accepted compositions. Recalculate against released foundations and the domain's true minimum. Below a useful dock threshold, inspection uses an accessible overlay/full-screen surface. Never silently collapse global navigation just to fit a screenshot.

The [foundation refresh](FOUNDATION_DELTA_20261104.md) preserves conditional focus ownership and active-owner Escape. Shared320+24 evidence geometry does not replace the focused Terminal reader: D06/host retain its360px initial width, requested300–520px clamp and incumbent `mm.railW`. Qualified effective fitting must not overwrite the preference. Brain lifecycle remains with its existing widget/host owner; close/resize does not cancel an answer or resolve a save.

The logical scenes C01–C13 in the Paper brief cover normal scan, complete comparison, Confluence evidence/locks, basket depth, saved-state recovery and phone return. They are composition instructions, not actual newly created artboard IDs. Validate light/dark, EN/ZH, long labels, dense rows, all read/write outcomes, focus/keyboard/touch and reduced motion. A reference count or screenshot cannot substitute for an actual task.

## 5. Data adaptation, validation and failure handling

Treat incoming availability, access, freshness, coverage and mutation outcome as independent axes. Validate source schema, universe and generation before combining results. Render a last-good snapshot with age when appropriate; never substitute an empty array for an unreadable source. A false404 absence, a403 denial and a transient timeout are different states. Use existing read generation/abort protections and dispose subscriptions; an aborted read is not cancellation of a save effect.

Use source-issued listing/episode/basket IDs, not row index, translated name or ticker alone. Preserve currency scope. Label unknown financial as-of for cached market cap. Preserve distinct membership/price/build/filing clocks. Null means missing/unavailable unless the producer supplies a more specific reason; it never becomes numeric zero for ranking, sizing or comparison.

A comparison is permitted only after metric/unit/currency, horizon/calendar, cohort and session basis are qualified. Otherwise show explicit side-by-side evidence without subtracting it. For missing fixed-cohort data, report both matched intersection and whole-cohort possibility bounds. The bounds are identification bounds, not confidence or probability. A fixed-membership saved view is not a frozen observation or historical portfolio.

Correct source gaps through the producer and renderer together. Specific open seams are Confluence missing payload→zero defaults, malformed identity array→empty, public/protected generation mismatch, older/train copy, basket-created fallback pretending freshness, and unavailable market-cap financial date. The design may expose uncertainty now; it cannot manufacture missing data.

## 6. Acceptance cases and evidence policy

[acceptance_cases.json](acceptance_cases.json) contains **75 Given/When/Then cases**. Every one is currently **NOT_RUN_PRODUCT_ACCEPTANCE**. The verification report in this package checks only artifact integrity, coverage links and arithmetic examples. It does not execute the website, a redesigned product or DB migration.

Use discriminating fixtures: four recipe legs, tied source ranks, all eligible count greater than displayed3, unequal monthly samples, contradictory conviction/entry signals, missing/ineligible cap, non-null unavailable timeframe, stale-public/new-private generation, denied payload, unknown Smart Screen predicate, overlapping memberships, fixed-group missing observations, stale-empty dislocations, lost storage and an original-request timeout. Expected values must be independently derived, not copied from the implementation under test.

| Area | Cases | Required proof |
| --- | --- | --- |
| Routes, receivers and entity identity | A001–A007, A071, A073 | Cold direct links, final URL/view/target, no-JS fallbacks, Back/Forward, each special fragment family and benchmark. |
| Confluence and source meaning | A008–A014, A058, A074–A075 | Normal-data ranks and paired eras, exact month-mean math, variable legs, free/paid byte boundary, generation and missingness distinctions. |
| Top Picks, baskets, Quant Lab, fund moves | A015–A021, A069 | Deep module/task retention, history/curation truth, signal dimensions, row/payload parity and unit/clock meaning. |
| Heatmaps and screeners | A022–A035 | Full-scope accounting, size/color/availability, market/native classification, fundamentals/technical unknowns and existing save limits. |
| Saves, episodes and exact return | A036–A048 | Owner API/readback, fixed/live scope, original request, episode ties, full and partial return disclosures, no silent account mutation. |
| Reference/accessibility/first useful view | A049–A060, A070 | Actual width/theme/locale/state captures, keyboard/touch, contrast/reflow, normal task and editable annotations. |
| Resilience, performance, rollback and ownership | A061–A068, A072 | Race/disposal, capacity/field budgets, migration/rollback, no-action boundary, source ownership and real review receipts. |

Tests requiring a source or ownership dependency remain blocked with that specific dependency; do not mark them not-applicable to make the matrix green. Pure compatibility redirects need no invented save-success specimen. All 25 inherited review conditions remain carried until their actual artifacts and independent findings close them.

## 7. Performance and usability budgets

Future targets are LCP≤2.5s, INP≤200ms and CLS≤0.1 at p75, measured separately for mobile and desktop. There are no current measurements in this package. Report representative data volume, hardware/network, measurement method and field sample; don't attach a passing number to a synthetic screenshot.

Mount only the active Discover pane and lazy evidence drawers. Keep the existing quote overlay bounded (top200; source batches100) and separate display pruning from full-universe evaluation. Large table rendering can be windowed without losing accessible row counts, search, selection or stable return anchors. Avoid loading every analytical route to render the overview. Preserve Sector Central's layout-before-lazy-init dependency and background-tab behavior.

Important phone controls target44px under house policy. Verify applicable contrast, noncolor meaning, keyboard access and400% reflow; necessary complex2D interaction stays inside the component with a meaningful table/list alternative. Honor reduced motion. Proposed research metrics are task completion, successful named return, unexplained reset frequency, comprehension of missingness and save semantics, and duplicate request count. No usability score has been measured here.

## 8. Rollout, rollback and ownership

A later commissioned implementation must use the existing product release process. Keep old routes/anchors live while new composition is evaluated. Preserve source evaluators and protected payload omission. Feature gating, if needed, belongs to the incumbent release system; D04 does not add a parallel rollout registry.

Rollback returns the UI to its prior reader while retaining saved records, schema version, original request identity and evidence receipts. Never delete or downgrade a newer saved schema to make an old screen load. Unknown versions are read-only or offer owner-supported export/recovery. A failed render or denied API cannot be repaired by bypassing entitlement or writing elsewhere.

The current deliverable is complete as a bounded source/specification package. The programme remains PARTIAL: native after-compositions, qualified foundations, D23 adoption for proposed persistence, independently admitted reference review and subsequent product implementation are separate owed stages. Exact next actions and owner evidence appear in the Paper gate table and README.

