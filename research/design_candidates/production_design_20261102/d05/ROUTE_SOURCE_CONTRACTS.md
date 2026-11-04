# D05 route and source contracts

Audit pin df691495abb1c2ba8f61e5624126cb17ad14e056. Assignment route IDs are unchanged. This table resolves gaps in the assignment census; it does not modify that shared registry. Route behavior is specified against the existing builders. [Sources](SOURCE_EVIDENCE.md)

## 1. All thirteen canonical routes

| Canonical page ID | Route | Actual builder → template | Payload / consumer boundary | Candidate and completion obligation |
|---|---|---|---|---|
| macro:allocation | /allocation.html | scripts/build_allocation.py::build_region → allocation.html.j2 → write_page | engine.narrative_rotation.compute_narrative_rotation(region); allocationdata/allocation.json; region snapshots and alerts | A07. Research lifecycle, model weights, risk, alerts and validation all retained. D22 owns allocation meaning. |
| macro:factors | /factors.html | scripts/build_site.py factor build → factors.html.j2 | factordata/factors.json plus IC, breadth, factor series, NW state, seasonality and momentum display | A08 generic unavailable pattern. config/site_access.yml denies the route even to entitled sessions. No customer navigation promotion. |
| macro:rotation_family | /rotation/&lt;key&gt;.html | scripts/build_subsector_rotation_pages.py → subsector_rotation_detail.html.j2 | marketdata/subsector_rotation.json; eight horizons; at most 30 members, 1M order | A12. Preserve native key, cohort, units, source dates and historical archive provenance. D19 reviews China variant separately. |
| macro:sector_central | /sector_central.html | scripts/build_sector_central.py → sector_central.html.j2 + si_workspace.js | engine.sector_central; free data JS/JSON, publication record, own premium payload and existing research handoff | A01/A10/A11. Existing six hash views remain reachable inside task-oriented presentation. |
| macro:sector_cycles | /sector_cycles.html | scripts/build_sector_cycles.py → sector_cycles.html.j2; sector_cycles.js/CSS | SECTOR_CYCLES core, SECTOR_CYCLES_SERIES, SECTOR_NARR, SECTOR_DNA; sectordata/sector_cycles.json | A02 plus retained R3/R4. Native in-shell integration and Dossier Cycle remain owner work, not delivered by #9917 or D05. |
| macro:sectors_family | /sectors/&lt;fund&gt;.html | Four implementations; see regional matrix below | Fund or regional sector source, local constituents and original stock route | A03/A04 and A01/A11 pattern. Do not infer one universal template or ticker from the route placeholder. |
| macro:state_of_themes | /state_of_themes.html | scripts/build_state_of_themes.py::compose, orchestrated by build_site.py → state_of_themes.html.j2 | neuralwebdata theme state/thesis/asymmetry/pathways; phase history; basketdata specialist context; existing consumer contract | A07. Dated thesis/evidence/falsifier, reading order, seven setup legs, source provenance. |
| macro:subsector_family | /subsector/&lt;id&gt;.html | scripts/build_subsector_confluence.py::render_pages → subsector_detail.html.j2 | US subsector/basket confluence; subsectorohlc, subsector_signals, subsector detail; basket b- prefix | A06/A12. Native group gate and stock gate separate; preserve identity and coverage. |
| macro:subsector_nasdaq_family | /subsector_nasdaq/&lt;id&gt;.html | same builder::render_index_pages("nasdaq") → subsector_detail.html.j2 | subsectorohlc_nasdaq / subsector_signals_nasdaq / subsector_nasdaq and configured amalg- groups | A06 exact source fixture. “Nasdaq desk” does not certify every configured company as a current index constituent. |
| macro:subsector_rotation | /subsector_rotation.html | build_site.py → subsector_rotation.html.j2 | Compatibility redirect to sector_central.html#si-movement; shared navigate replace or location.replace, noscript fallback | Keep redirect and return behavior. No new dashboard or duplicate source owner. |
| macro:subsector_russell_family | /subsector_russell/&lt;id&gt;.html | same builder::render_index_pages("russell") → subsector_detail.html.j2 | subsectorohlc_russell / subsector_signals_russell / subsector_russell; configured amalg- groups; shared template | A06 pattern, distinct fixtures required before runtime acceptance. Never mix Nasdaq/S&P/Russell rows. |
| macro:subsectors | /subsectors.html | scripts/build_subsector_confluence.py → subsectors.html.j2 | S&P, Nasdaq, Russell and Baskets artifacts; shared render engine | A12 plus retained confluence. Keep four universes, native sort/search/filter, coverage, class and tier semantics. |
| macro:theme_tree | /theme_tree.html | scripts/build_theme_tree_page.py, also build_site.py → theme_tree.html.j2 | engine.theme_graph.store.read_nodes(current=True), read_edges(); hierarchy_breadth_display; theme crosswalk; identity resolver | A05. D13 owns graph semantics. Membership/proxy map is not a performance rank or thesis forecast. |

All source builders/templates are directly linked in SOURCE_EVIDENCE.md S03–S06. ROUTE_MATRIX.csv preserves original census columns alongside the resolved audit result.

## 2. Regional /sectors/ matrix

| Region | Builder function / location | Template | Source-proven example | Native Company adapter | Data meaning |
|---|---|---|---|---|---|
| US | build_site.py::render_sector_pages | sector.html.j2 | /sectors/XLK.html family | stock.html#TICKER | US sector/fund detail with existing factor/insider enrichment; no claim that a theme basket equals the ETF |
| Canada | build_canada.py sector-page render | canada_sector.html.j2 | /sectors/XEG.TO.html | canada_stock.html#SYMBOL | CAD/Toronto listing; source “holdings” are sector-alias constituent groups unless reported fund holdings/effective date is independently supplied |
| China | build_china.py sector-page render | china_sector.html.j2 | /sectors/512690.SS.html | china_lookup.html#SYMBOL | Mainland fund/sector and CN calendar; concept family is a separate THS context |
| HK | build_hk.py sector-page render | hk_sector.html.j2 | /sectors/hk-energy.html | hk_lookup.html#SYMBOL | Local sector slug generated from name; not a fund ticker; local OHLC chart |

Canada XEG source members include ENB.TO, TRP.TO, CNQ.TO, SU.TO, CVE.TO, IMO.TO, TOU.TO, PPL.TO and WCP.TO. This is an inspected source snapshot, not a claim of current reported XEG holdings or historical effective membership. Existing Canada/China TradingView dependencies are inherited implementation choices; D05 introduced no remote Paper assets.

Regional allocation variants already exist in build_allocation.py's PAGES mapping for US/China/HK/Canada. Preserve the native filenames and regional basket links from that mapping; do not invent aliases. D19/D20 receive regional semantic review; D22 receives model allocation review. D07 receives listing/Company route integration.

## 3. Compatibility navigation: exact current aliases

The old disposition ledger described 21 aliases. The current audited si_workspace.js contains the following 24; this audit supersedes the stale count without changing the shared router.

| Legacy anchor | Canonical current view | Scroll target |
|---|---|---|
| actnow-section | overview | actnow-section |
| regime | overview | regime |
| grader | overview | grader |
| si-map | map | si-map |
| rotmap-section | map | rotmap-section |
| sc-cyclemap | map | sc-cyclemap |
| board | map | board |
| si-movement | moving | si-movement |
| rc-events-mount | moving | rc-events-mount |
| rotation-app | moving | rotation-app |
| si-money | money | si-money |
| internals-section | money | internals-section |
| scc-leadership | money | scc-leadership |
| explore-section | explore | explore-section |
| table-section | explore | table-section |
| chart-section | explore | chart-section |
| forming-narratives | explore | forming-narratives |
| tm-mount | explore | tm-mount |
| confluence | confluence | si-confluence |
| sc-app | confluence | sc-app |
| sc-top | confluence | sc-top |
| accumulation-section | moving | accumulation-section |
| si-heat-section | explore | theme-heat-section |
| si-measured | map | si-measured |

Keep #theme-* resolution and #read-* source-trace resolution as distinct behaviors. Unknown hash falls back to overview; empty hash uses replacement rather than an extra history entry. Mount the visible view and its dependencies once; lazy data arriving after a scope change cannot steal selection or focus. Back/Forward and same-page hash changes must restore meaningful state; static link existence is not proof of that behavior.

## 4. Producer → receiver map

| Producer / artifact | Receiver | Existing semantics to preserve | Gap handling |
|---|---|---|---|
| engine.sector_central.compute | Central free payload and template | Sector score, regime, breadth and cycle context | Focused publication lane may fail closed; do not turn missing mandatory source into a valid empty page |
| basketdata/action_board.json | Central Brief/action lanes | Full lane counts; paid name split; source-provided destinations | Typed source failure; preserve public preview; no invented rank or entry |
| basketdata/si_handoff.json | Brief/flow context | Display context, no path into action-lane placement | Generic heading on absent/corrupt artifact |
| basketdata/baskets.json | Explore and Bottoming Watch | Measured basket performance; display-only watch context | No signal/timing-state promotion |
| sponsor sector_flow_periods | ETF flow table | Delta shares × NAV, native window sums, own asof/depth | Missing remains null; qualify aggregate coverage |
| marketdata/subsector_rotation.json | Broad rotation map/detail | Cohort-relative standardized coordinates, eight periods, top-30 detail | Insufficient eligible observations cannot be displayed as measured neutral zero |
| confluence JSON and per-group files | Four-universe board/detail | Group gates, stock setup tiers, configured/priced counts, marker integrity | No universe mixing or stock-gate override |
| sector_cycles core/series/NARR/DNA | Cycles | Lossless ID-based lazy hydration, dates, narrative TTL and family support | Missing optional context must not suppress valid core; no mixed generation |
| sector_central.research_handoff.v1 | Dossier/Research adapters | Native subject, row digest, generation, descriptive mode, safe return href | adapter_only; governance/authority/input receipts/dossier hash not supplied |
| theme_intelligence.consumer.v1 | State of Themes and research | Owner dimensions, evidence identity, clocks, correction lineage | Missing joins remain UNAVAILABLE/UNCONFIRMED; never invent independent confirmations |
| watchstore.saveSectorInvestigation / listSectorInvestigations | Sector Research/Watches | Existing cloud subject + device-local note, account isolation, section='si' | Regional symbols/full cross-device context require owner contract; no new store |

## 5. Source-backed audit defects and requested owner work

1. **Observed production scope mismatch:** Sectors 11 versus 38 themes in the map/list. Require one coherent selected scope and reject late data from old scope.
2. **Correct history suppression to retain:** Oct30 current versus Nov2 reconstructed history was withheld; do not “fix” it by mixing dates.
3. **Retail elapsed projection:** inherited owner report identifies a Jan2026 median/window ending Apr2026 displayed as a next turn during Nov2026. Basket detail owner must reconcile that source path. Current sector_cycles.js already has projPast/forecastCardHTML median-elapsed handling; preserve it and extend only where the full window/invalid-date contract is unmet.
4. **Relative trend producer ordering:** the audited Central builder calls emit_relative_trend_additive(fdir, …) before its later local fdir assignment, inside a caught exception. This source-path defect can skip this additive emission. Confirm the original producer's intended ordering and fix there; do not invent a browser fetch or claim a feed is live solely because the function exists.
5. **Authorization failure path:** public preview versus premium payload must fail closed. The broad build path has tolerant fallbacks requiring focused auth-owner review; no access-policy patch is made in D05.
6. **Research durability:** current subject cloud save differs from device-local question/snapshot/origin, and the existing ETF save allowlist excludes regional listing strings. Do not imply full durable investigation support.
7. **Existing source contracts remain partial:** native Central correction metadata remains absent (SC-092). The current basket engine now emits thin/scored census fields, but the committed basket_confluence payload at the audit pin lacks them; SC-066 remains held for publication/consumer proof. Its n_gateable means successfully scored groups, not entry eligibility. Preserve the inherited block until the actual source path proves the new fields.

These are specifications/owner gates, not claims of repaired production code.

8. **Missing falsifier evidence:** State of Themes currently defaults an absent thesis/falsifier summary to false/zero and can emit NOT_DETECTED. Explicit positive missing-count becomes UNCONFIRMED, but complete absence does not. The existing research producer must distinguish absence before the UI can claim no invalidation was detected. This is recorded as a source-owner repair requirement, not a local signal override.

