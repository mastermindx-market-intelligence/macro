# D04 — Capability retention ledger

**D04-SPEC/0.1.0 — source/specification candidate.** This ledger binds each analytical capability to a reachable successor and behavioral acceptance case. `RETAIN` means the capability must survive; it does not certify implementation or reference acceptance. `IMPROVE` describes a required design change. `RELOCATE` names an explicit receiver. `BLOCKED_DATA` names unavailable/unqualified support and interim behavior. No removal is proposed or approved.

Baseline paths and evidence are indexed in [SOURCE_INDEX.md](SOURCE_INDEX.md). Exact route/anchor mappings are in [COMPATIBILITY.md](COMPATIBILITY.md). All 62 existing Paper artboard identities are individually retained in [evidence/paper_boards.json](evidence/paper_boards.json); six selected screenshots were visually inspected. This ledger does not pretend all 62 passed visual review. Exact field and saved-object meanings are in [ROUTES_AND_DATA.md](ROUTES_AND_DATA.md).

## Disposition totals

| Disposition | Count |
| --- | ---: |
| RETAIN | 75 |
| RELOCATE | 3 |
| IMPROVE | 30 |
| BLOCKED_DATA | 5 |
| REMOVE | 0 |

Total: **113** capabilities. Every reviewer decision is **NOT_REVIEWED**. All 25 inherited findings/conditions remain **CARRIED_BLOCK**; see [REVIEW_CONTINUITY.md](REVIEW_CONTINUITY.md).

## Relocations and unavailable support

- **D04-C002 — Repeated local scope/context controls: RELOCATE.** Destination/interim: Shared domain context bar within /discover, with per-view semantic adapters; public routes retain their compatibility entries. Owner/dependency: F01/F02; D04; owning views. Reduce repetition only where object and field meanings match; final composition is proposed.
- **D04-C008 — Unsupported regional universe parity: BLOCKED_DATA.** Destination/interim: Unavailable-universe state retaining supported filters and regional links. Owner/dependency: D19/D20 qualify universe; D13 membership; interim show unsupported with scope retained. There is no evidence for universal US-feature parity.
- **D04-C032 — Movers, gainers/losers, activity and return analyzer: RELOCATE.** Destination/interim: Existing /stocks/index.html#today-movers through /movers.html fixed replacement. Owner/dependency: Stocks hub owner; D04 compatibility. This is the current shipped/source destination; preserve rich Stocks-hub functions.
- **D04-C033 — Basket catalog and active theme links: RELOCATE.** Destination/interim: Existing sector_central.html#actnow-section plus basket/<id>.html; #ne-* retained. Owner/dependency: D05; D13; D04. Retain current compatibility receiver instead of reviving a duplicate basket desk.
- **D04-C037 — True point-in-time historical membership before first recorded snapshot: BLOCKED_DATA.** Destination/interim: Qualified back-projected context plus actual available snapshots/changelog. Owner/dependency: D13 and basket producer; interim mark back-projected, show real curation/snapshot dates. Absent historical custody cannot be reconstructed as actual holdings.
- **D04-C073 — Precise USD-cap financial observation date: BLOCKED_DATA.** Destination/interim: Display known provider/cache provenance and unknown financial as-of. Owner/dependency: Market-cap producer; interim do not invent date or substitute quote timestamp. Current cache does not establish a quote-time financial measurement.
- **D04-C078 — Fixed/live typed heatmap saved view: BLOCKED_DATA.** Destination/interim: D23-adopted v2 on existing thesis-saved-view owner, then clear save-type UI. Owner/dependency: D23; interim retain supported existing saves, explain unavailable typed save. Draft#778 contract/migration is not a deployed capability.
- **D04-C094 — Saving technical conditions into Smart Screens: BLOCKED_DATA.** Destination/interim: Explicit unsupported-content explanation; retain technical controls as local research state. Owner/dependency: Smart Screens owner and D23; interim show exact omitted fields before save. Current grammar excludes technical predicates; do not advertise retention that does not exist.

## Full ledger

The [machine-readable ledger](capabilities.json) includes exact route/source/Paper baseline, qualification, owner/dependency and reviewer status for every row. Acceptance IDs refer to [acceptance_cases.json](acceptance_cases.json); all are specified, not run against a redesigned product.

### Shared discovery and route context

Baseline: all ten canonical routes; [source index](SOURCE_INDEX.md), sections S01, S03, S10, S14.

| ID / capability | Disposition | Successor and reason | Dependency | Acceptance |
| --- | --- | --- | --- | --- |
| D04-C001 · Ten distinct canonical analytical jobs | RETAIN | Existing canonical routes listed in ROUTES_AND_DATA.md. A navigation rationalization must preserve deep analytical tasks. | D04; qualified F01/F02 for composition; existing source owner for implementation | A001, A072 |
| D04-C002 · Repeated local scope/context controls | RELOCATE | Shared domain context bar within /discover, with per-view semantic adapters; public routes retain their compatibility entries. Reduce repetition only where object and field meanings match; final composition is proposed. | F01/F02; D04; owning views | A030, A047, A059 |
| D04-C003 · Global entity search versus local result filter | RETAIN | F01 global search; labeled local list filter in each analytical object. Avoid a second search or identity plane. | F01; D07 | A007, A059 |
| D04-C004 · Exact filter, range, selection, comparison and scroll return | IMPROVE | Existing F01/router history seam plus proposed versioned ReturnContext. Current production state coverage is incomplete; preserve valid context through company research. | F01; D07; D04 | A042, A043 |
| D04-C005 · Deep-link hashes, query values and route receivers | RETAIN | COMPATIBILITY.md receiver matrix and stable canonical entries. Preserve shared links and browser navigation rather than rewriting all users to a default. | D04; qualified F01/F02 for composition; existing source owner for implementation | A002, A003, A004, A005, A006, A071 |
| D04-C006 · Six Discover panes and active-pane lifetime | RETAIN | /discover?tab=screener/heatmap/sectors/leaders/radar/rs-pivot. Keep non-heatmap research dimensions and owning mounts; no new D04 ownership of them. | D05 and current Leaders/Radar/RS owners; F01 | A005, A063 |
| D04-C007 · Cross-region native classification and currency | RETAIN | Current region/asset filter and source-qualified classification controls. Do not collapse native namespaces into US sectors. | D19/D20; D05 | A030, A068 |
| D04-C008 · Unsupported regional universe parity | BLOCKED_DATA | Unavailable-universe state retaining supported filters and regional links. There is no evidence for universal US-feature parity. | D19/D20 qualify universe; D13 membership; interim show unsupported with scope retained. | A055, A068 |
| D04-C009 · Public/member/plan-required boundaries and return | RETAIN | Current route gates and source-protected payload adapters. A common visual shell cannot change entitlement. | F01 auth seam; existing API owners | A012, A020, A056 |
| D04-C010 · Research shortlist without automatic activation | RETAIN | Explicit shortlist/save controls; separate owner-approved monitoring entry. Navigation or save does not create an alert, portfolio position or order. | D23; owning alert/research product | A044, A067 |

### Confluence ranked evidence

Baseline: macro:confluence_screener; [source index](SOURCE_INDEX.md), sections S04, S16.

| ID / capability | Disposition | Successor and reason | Dependency | Acceptance |
| --- | --- | --- | --- | --- |
| D04-C011 · Runtime daily answer/count above the fold | IMPROVE | Dedicated answer slot with source-bound count in every primary variant. Inherited PRC-001/VTC-001 and R2-HERO-ANSWER stay open until real composition. | D04; qualified F01/F02 for composition; existing source owner for implementation | A011, A058 |
| D04-C012 · Eligible top-three builder rank and stable ties | RETAIN | Comparable rank1–3 rows; source rank labels. UI filters must not manufacture ranking or alter eligibility. | D04; qualified F01/F02 for composition; existing source owner for implementation | A008, A013 |
| D04-C013 · Variable-depth structured D/W recipe legs | RETAIN | Explicit builder-owned leg rows with adequate height. Preserve actual recipe depth without unsupported timeframe identities. | D04; qualified F01/F02 for composition; existing source owner for implementation | A009 |
| D04-C014 · Recent and older validation side by side | IMPROVE | Same evidence columns/stack grammar on every rank. Recent/older rate, sample size and months must be directly comparable. | D04; qualified F01/F02 for composition; existing source owner for implementation | A010, A058, A074 |
| D04-C015 · Sample basis, fire history, frequency and edge pp | RETAIN | Evidence row and accessible expanded source details. Preserve n_test/n_train, months, fires and temporal basis; units remain distinct. | D04; qualified F01/F02 for composition; existing source owner for implementation | A010, A057 |
| D04-C016 · Unavoidable honesty about historical rates and entry meaning | IMPROVE | Plain-language glance-tier caveat adjacent to primary answer. Disclosure cannot hide a critical qualification. | D04; qualified F01/F02 for composition; existing source owner for implementation | A011, A052 |
| D04-C017 · Rank-1 free matching identities and wrapping links | RETAIN | DEMO-proven ticker/company link grammar, current real identity adapter at runtime. Free useful path must stay usable with many/long names. | D04; qualified F01/F02 for composition; existing source owner for implementation | A012, A014 |
| D04-C018 · Public counts and comparable evidence for paid rows | RETAIN | Rank2/3 same evidence grammar with identity lock area. Entitlement hides identities, not public evidence structure. | D04; qualified F01/F02 for composition; existing source owner for implementation | A012, A058 |
| D04-C019 · Protected identity hydration, CTA, failure and expiry | IMPROVE | Existing protected payload read with honest pending/denied/error copy. Prevent false unlock or name leakage; don't interpret the hydrated browser state as public bytes. | D04; qualified F01/F02 for composition; existing source owner for implementation | A012, A056, A075 |
| D04-C020 · Presentation filters and filter-empty distinction | RETAIN | Optional labeled filter on published ranked rows. Retain only truthful scope; filter-empty never rewrites global zero. | D04; qualified F01/F02 for composition; existing source owner for implementation | A008, A013 |
| D04-C021 · Freshness, as-of and provenance | IMPROVE | Visible source-date anchor plus detail. Raw missing payload/default-zero behavior needs an explicit unavailable state. | D04; qualified F01/F02 for composition; existing source owner for implementation | A011, A057 |
| D04-C022 · Brand, dark identity and language-sensitive colors | IMPROVE | F01 brand and F02 dark/light tokens, nonsemantic convergence motif. Correct MASTERMINDX and preserve character without colored container borders. | F01/F02 | A051, A052, A059 |
| D04-C023 · Focus, hover, loading, empty, stale and disabled specimens | IMPROVE | Actual editable state scenes with localized copy. State labels in a frame are not demonstrated interaction. | D04; qualified F01/F02 for composition; existing source owner for implementation | A053, A055, A058 |
| D04-C024 · 24 legacy mappings and distinct #sc/#theme/regional #b contracts | RETAIN | Exact current receiver and anchor inventory; missing retired-anchor adapters remain explicit. Current executable table has24, correcting the handoff's23; preserve source receiver ownership and distinguish US b- paths from regional #b fragments. | D04; qualified F01/F02 for composition; existing source owner for implementation | A002, A003, A004 |
| D04-C025 · All predecessor findings and conditions | RETAIN | Existing RIG continuity, all 25 CARRIED_BLOCK until evidence-backed resolution. No prose remedy or agent advice closes an inherited review finding. | Existing RIG owner and admitted independent reviewers | A065, A066 |

### Top Picks and Movers

Baseline: macro:discovery, macro:movers; [source index](SOURCE_INDEX.md), sections S05, S15.

| ID / capability | Disposition | Successor and reason | Dependency | Acceptance |
| --- | --- | --- | --- | --- |
| D04-C026 · Top Picks, Sectors and Sector index navigation | RETAIN | Existing sections with consistent Discover entry labels. Preserve alternate scan paths. | D04; qualified F01/F02 for composition; existing source owner for implementation | A015 |
| D04-C027 · Top conviction and Avoid universes | RETAIN | Distinct rank sides and source evidence. Avoid is not a negative color rendering of the same shortlist. | D04; qualified F01/F02 for composition; existing source owner for implementation | A015 |
| D04-C028 · Hide-stretch and sector filters | RETAIN | Scope controls with clear applied state. Retain research filtering while rank stays source-owned. | D04; qualified F01/F02 for composition; existing source owner for implementation | A015, A016 |
| D04-C029 · Conviction/alpha versus BUY entry timing, trend and extension | RETAIN | Dense rank table with separate evidence fields. A highly ranked company need not be an immediate entry. | D04; qualified F01/F02 for composition; existing source owner for implementation | A015, A057 |
| D04-C030 · Source date, signal validity and generation time | IMPROVE | Separate observation/valid-through/generated labels. Avoid treating stale signals as current from a recent build stamp. | D04; qualified F01/F02 for composition; existing source owner for implementation | A016, A057 |
| D04-C031 · Stock detail links and exact return | IMPROVE | Current stock.html#ticker seam with F01/D07 qualified return adapter. Keep entity identity and original shortlist position. | F01; D07 | A007, A042 |
| D04-C032 · Movers, gainers/losers, activity and return analyzer | RELOCATE | Existing /stocks/index.html#today-movers through /movers.html fixed replacement. This is the current shipped/source destination; preserve rich Stocks-hub functions. | Stocks hub owner; D04 compatibility | A006, A071 |

### Curated baskets and detailed research

Baseline: macro:baskets, macro:basket_family; [source index](SOURCE_INDEX.md), sections S07.

| ID / capability | Disposition | Successor and reason | Dependency | Acceptance |
| --- | --- | --- | --- | --- |
| D04-C033 · Basket catalog and active theme links | RELOCATE | Existing sector_central.html#actnow-section plus basket/<id>.html; #ne-* retained. Retain current compatibility receiver instead of reviving a duplicate basket desk. | D05; D13; D04 | A003 |
| D04-C034 · All 49 stable current basket IDs | RETAIN | Exact generated /basket/<id>.html family. Do not retain a stale48-count label or rename valid IDs. | D04; qualified F01/F02 for composition; existing source owner for implementation | A003, A018 |
| D04-C035 · Equal-weight monthly construction | RETAIN | Method/legend and detail history. Construction affects interpretation of performance and comparison. | D04; qualified F01/F02 for composition; existing source owner for implementation | A018, A024 |
| D04-C036 · Index-inclusion mask versus actual curation date | IMPROVE | Separate added and curated_added provenance display. Back-projected membership is not a historical watch record. | D13 membership; basket producer | A018 |
| D04-C037 · True point-in-time historical membership before first recorded snapshot | BLOCKED_DATA | Qualified back-projected context plus actual available snapshots/changelog. Absent historical custody cannot be reconstructed as actual holdings. | D13 and basket producer; interim mark back-projected, show real curation/snapshot dates. | A018, A068 |
| D04-C038 · Group breadth, earnings and co-movement read | RETAIN | Basket summary and evidence detail. Preserve the basket's diagnostic context. | D04; qualified F01/F02 for composition; existing source owner for implementation | A019 |
| D04-C039 · Health, gated act-now and standout/within-basket context | RETAIN | Distinct theme-health, entry and member-research views. Do not turn research priority into unsupported numeric potential. | D04; qualified F01/F02 for composition; existing source owner for implementation | A019, A067 |
| D04-C040 · Cycles, multi-timeframe and flow evidence | RETAIN | Deep evidence sections and linked member detail. Preserve analytical depth beyond the first fold. | D04; qualified F01/F02 for composition; existing source owner for implementation | A019 |
| D04-C041 · Timing/risk, bull age, overbought, clean entry, rollover and flip distance | RETAIN | Timing/risk section with display-only qualification. Maintain action-relevant context without creating an order trigger. | D04; qualified F01/F02 for composition; existing source owner for implementation | A019, A067 |
| D04-C042 · Score composition, performance, breadth and score history | RETAIN | Comparison/history sections with named bases. Different scores and horizons remain interpretable. | D04; qualified F01/F02 for composition; existing source owner for implementation | A019, A057 |
| D04-C043 · Sortable holdings, research-priority order and refreshed disclosure/focus | RETAIN | Dense member table and source-defined expandable rows. Preserve task state after refresh and detail exploration. | D04; qualified F01/F02 for composition; existing source owner for implementation | A019, A042 |
| D04-C044 · Membership changelog, cross-market references and exact back path | RETAIN | Existing detail provenance and ../sector_central.html#actnow-section; region-qualified links. Shared regional template does not prove equal data coverage. | D05; D13; D19/D20 | A003, A007, A018, A068 |

### Quant Lab

Baseline: macro:advanced; [source index](SOURCE_INDEX.md), sections S06.

| ID / capability | Disposition | Successor and reason | Dependency | Acceptance |
| --- | --- | --- | --- | --- |
| D04-C045 · AI-versus-rest breadth split | RETAIN | #vsb-breadth-split-section. Maintain comparison cohort and qualification. | D04; qualified F01/F02 for composition; existing source owner for implementation | A017, A069 |
| D04-C046 · Cross-asset concentration, PC1 and63-day correlation | RETAIN | #cross-asset matrix. Retain source horizon and concentration meaning. | D04; qualified F01/F02 for composition; existing source owner for implementation | A017, A069 |
| D04-C047 · Risk budget | RETAIN | #risk-budget. Keep portfolio risk context distinct from ranking. | D04; qualified F01/F02 for composition; existing source owner for implementation | A017, A069 |
| D04-C048 · Stress replay | RETAIN | #stress-replay. Retain scenario/assumption context. | D04; qualified F01/F02 for composition; existing source owner for implementation | A017, A069 |
| D04-C049 · Factor IC scorecard | RETAIN | #factor-scorecard. Preserve sample and evaluation meaning. | D04; qualified F01/F02 for composition; existing source owner for implementation | A017, A069 |
| D04-C050 · Dials, votes and weakest-link context | RETAIN | #dials. Maintain multi-signal analytical structure. | D04; qualified F01/F02 for composition; existing source owner for implementation | A017, A069 |
| D04-C051 · Market internals | RETAIN | #internals. Keep underlying breadth/participation diagnostics. | D04; qualified F01/F02 for composition; existing source owner for implementation | A017 |
| D04-C052 · Size and style | RETAIN | #size-style. Preserve cross-sectional segmentation. | D04; qualified F01/F02 for composition; existing source owner for implementation | A017 |
| D04-C053 · Sector ETF accumulation | RETAIN | #accumulation. Retain holdings/accumulation context. | D04; qualified F01/F02 for composition; existing source owner for implementation | A017, A021 |
| D04-C054 · Holdings flows | RETAIN | #holdings. Do not replace with generic ETF prices. | D04; qualified F01/F02 for composition; existing source owner for implementation | A017, A021 |

### ETF and fund moves

Baseline: macro:etfs; [source index](SOURCE_INDEX.md), sections S08.

| ID / capability | Disposition | Successor and reason | Dependency | Acceptance |
| --- | --- | --- | --- | --- |
| D04-C055 · Public non-graded stance, rotation backdrop and honest totals | RETAIN | Free ETF header/overview. Public entry remains useful without exposing graded records. | D04; qualified F01/F02 for composition; existing source owner for implementation | A020 |
| D04-C056 · Full fund coverage directory and footer | RETAIN | Coverage directory with source freshness. Preserve breadth of research universe. | D04; qualified F01/F02 for composition; existing source owner for implementation | A020, A021 |
| D04-C057 · Protected graded board and fresh/add/trim views | RETAIN | Existing tier_payload.v1 hydration from shared partials. Keep row parity and correct access boundary. | D04; qualified F01/F02 for composition; existing source owner for implementation | A020 |
| D04-C058 · Consensus favored, fund coverage and trajectories | RETAIN | Current engine-owned evidence and history context. Preserve consensus and trajectory dimensions. | D04; qualified F01/F02 for composition; existing source owner for implementation | A020, A021 |
| D04-C059 · Share change versus weight change versus price drift | IMPROVE | Explicit units, filing clock and comparison labels. A price move cannot stand in for a holdings decision. | D04; qualified F01/F02 for composition; existing source owner for implementation | A021, A057 |
| D04-C060 · Stock-linked fund flows and return | RETAIN | Current stockdata/fund_flows.json consumer and company detail seam. Preserve source/stock relationships. | D07; fund-flow producer | A007, A021, A042 |

### Macro market and theme heatmaps

Baseline: macro:sector_heatmap; [source index](SOURCE_INDEX.md), sections S09.

| ID / capability | Disposition | Successor and reason | Dependency | Acceptance |
| --- | --- | --- | --- | --- |
| D04-C061 · S&P company map and theme/subtheme map | RETAIN | Two map modes with distinct hierarchy/identity. Tiles represent different objects; keep meaning visible. | D04; qualified F01/F02 for composition; existing source owner for implementation | A022, A023 |
| D04-C062 · 503-tile S&P snapshot and provider sector labels | RETAIN | Source-qualified sector grouping. Mixed provider labels cannot be silently collapsed. | D04; qualified F01/F02 for composition; existing source owner for implementation | A022 |
| D04-C063 · Timeframe metadata including disabled intraday | RETAIN | Timeframe control honors available flag. A populated historical value does not establish availability. | D04; qualified F01/F02 for composition; existing source owner for implementation | A022 |
| D04-C064 · Market-cap weighted sector aggregate versus median/count basis | RETAIN | Measure-specific legend and aggregate explanation. Prevent misleading comparisons between different aggregation rules. | D04; qualified F01/F02 for composition; existing source owner for implementation | A024 |
| D04-C065 · Theme hierarchy, overlap and look-through counts | IMPROVE | 40-group/268-subtheme source example with deduplicated company view. 2339 appearances are not2339 distinct instruments. | D13; heatmap producer | A023, A068 |
| D04-C066 · Membership date versus price date and unknown coverage | IMPROVE | Visible clock/coverage strip and detail provenance. Older theme membership must remain visible beside newer prices. | D04; qualified F01/F02 for composition; existing source owner for implementation | A023, A057 |
| D04-C067 · Color scale, neutral deadband and locale palette | RETAIN | Declared1D/longer-window bins, +/-0.05pp breadth and EN/ZH convention. Preserve actual mathematical/locale semantics. | D04; qualified F01/F02 for composition; existing source owner for implementation | A024, A046, A052 |
| D04-C068 · Sort cap/move/A–Z, local search and mobile list | RETAIN | Current map toolbar and meaningful table/list equivalent. Retain dense scan and offscreen access. | D04; qualified F01/F02 for composition; existing source owner for implementation | A024, A025, A050 |
| D04-C069 · Member/header popovers and payload-owned stock link | RETAIN | Accessible inspector/table action using stock_url. Do not hardcode stock.html when payload specifies Terminal. | D04; qualified F01/F02 for composition; existing source owner for implementation | A007, A022, A053 |
| D04-C070 · No-cache refresh, live1D overlay and rotation link | RETAIN | Existing refresh/provenance and sector_central.html#si-movement. Different windows/feed freshness remain explicit. | D05; heatmap producer | A024, A029, A057 |

### Terminal heatmap and comparison

Baseline: terminal:discover; [source index](SOURCE_INDEX.md), sections S10, S12, S13.

| ID / capability | Disposition | Successor and reason | Dependency | Acceptance |
| --- | --- | --- | --- | --- |
| D04-C071 · PRICE/FLOW layers and MAP/TABLE views | RETAIN | Existing view/layer controls with explicit reset behavior. Preserve analytical distinction and equivalent table access. | D04; qualified F01/F02 for composition; existing source owner for implementation | A025, A027, A028 |
| D04-C072 · Legacy CAP price×volume, USD CAP and EQUAL sizing | IMPROVE | Named size options plus source explanation. CAP proxy is not market capitalization; missing USD cap is not a tiny cap. | D04; qualified F01/F02 for composition; existing source owner for implementation | A026 |
| D04-C073 · Precise USD-cap financial observation date | BLOCKED_DATA | Display known provider/cache provenance and unknown financial as-of. Current cache does not establish a quote-time financial measurement. | Market-cap producer; interim do not invent date or substitute quote timestamp. | A026, A057 |
| D04-C074 · Full-scope breadth versus500 rendered tiles | IMPROVE | Separate eligible/scoped/drawn counts; search/table access to remainder. Rendering limits must not become analytical denominator limits. | D04; qualified F01/F02 for composition; existing source owner for implementation | A025, A027 |
| D04-C075 · Flow net premium/DOI/0DTE/fresh-contract/lean context | RETAIN | Units and caveats within flow inspector/table. Direction is soft evidence, not a probability or forecast. | D04; qualified F01/F02 for composition; existing source owner for implementation | A028 |
| D04-C076 · Manifest fallback, freshness and bounded quote overlay | IMPROVE | Existing adapters with consistent field-specific freshness labels. Resolve EOD-versus-top200 delayed-live ambiguity and preserve last-good data. | D04; qualified F01/F02 for composition; existing source owner for implementation | A027, A029, A061, A063 |
| D04-C077 · Matched-cohort comparison with missing-member bounds | IMPROVE | Shared comparison tray/table within existing heatmap object. Paper comparison honesty must survive integration; observed denominator change is not a trend. | D04; D13 membership; source adapters | A045, A046 |
| D04-C078 · Fixed/live typed heatmap saved view | BLOCKED_DATA | D23-adopted v2 on existing thesis-saved-view owner, then clear save-type UI. Draft#778 contract/migration is not a deployed capability. | D23; interim retain supported existing saves, explain unavailable typed save. | A037, A038, A039 |
| D04-C079 · Original-request save recovery and account boundary | IMPROVE | D23/current owner recovery UI with original owner/request/fingerprint. Retain Paper uncertainty semantics without creating another queue. | D23 | A038, A048 |
| D04-C080 · Selection/inspector and close-return continuity | IMPROVE | Shared selection identity and overlay/dock matched to available width. Do not lose comparison or focus when inspection changes form. | D04; qualified F01/F02 for composition; existing source owner for implementation | A042, A043, A049 |

### Stock Screener and saved screens

Baseline: terminal:discover; [source index](SOURCE_INDEX.md), sections S18, S12.

| ID / capability | Disposition | Successor and reason | Dependency | Acceptance |
| --- | --- | --- | --- | --- |
| D04-C081 · Market, asset, sector, signal, uptrend and unpriced filters | RETAIN | Current Stock Screener filter model. Preserve all criteria and unknown-value choices. | D04; qualified F01/F02 for composition; existing source owner for implementation | A030 |
| D04-C082 · Currency-qualified liquidity and USD market-cap floors | RETAIN | Current bound-currency filters and explicit market change behavior. Prevent currency reinterpretation of a numeric floor. | D04; qualified F01/F02 for composition; existing source owner for implementation | A030 |
| D04-C083 · 52-week and day-move conditions | RETAIN | Current w52/move controls and explainable chips. Retain near-high/drawdown and up/down/absolute-move dimensions. | D04; qualified F01/F02 for composition; existing source owner for implementation | A030 |
| D04-C084 · Native taxonomy, stale-classification opt-in and density | RETAIN | Source-qualified taxonomy selector and device density preference. Native data namespaces and intentional stale opt-in remain. | D04; qualified F01/F02 for composition; existing source owner for implementation | A030, A068 |
| D04-C085 · Seven current built-in preset IDs | RETAIN | psBuys/psGainers/psDecliners/psNearHigh/psDrawdown/psCn/psHk. Stable presets remain independently reachable. | D04; qualified F01/F02 for composition; existing source owner for implementation | A030, A033 |
| D04-C086 · Technical snapshot, timeframe, position, signals, bar limits and chips | RETAIN | Current technicalScreenControls and bounded technical scan. No OHLC recomputation or silent loss of advanced conditions. | D04; qualified F01/F02 for composition; existing source owner for implementation | A031 |
| D04-C087 · Five fundamental fields with period/family evidence | RETAIN | Current fundamental scan and lazy evidence drawer. Maintain TTM/fiscal-year units, exclusions and unknown logic. | D04; qualified F01/F02 for composition; existing source owner for implementation | A031, A032 |
| D04-C088 · Device preset create/apply/delete and12-record limit | IMPROVE | Labeled On this device preset with accurate supported-field disclosure. Current presets omit fundamental/technical conditions; storage failure must not appear saved. | D04; qualified F01/F02 for composition; existing source owner for implementation | A033 |
| D04-C089 · Current account Smart Screen save/reopen | RETAIN | Existing /api/smart-screens owner, workspace_settings scr_screen records. Preserve grammar1/2 support and account scope. | Smart Screens owner; D23 boundary | A034, A035 |
| D04-C090 · Fundamental grammar, explain and entered/left on demand | RETAIN | Current SmartScreensPanel and three-valued predicate engine. Unknown observation is not an exit event; no alert implied. | D04; qualified F01/F02 for composition; existing source owner for implementation | A032, A034, A035 |
| D04-C091 · Explicit device import and10-account-screen limit | RETAIN | Existing user-initiated import and capacity feedback. No automatic migration or duplicate account object. | D04; qualified F01/F02 for composition; existing source owner for implementation | A034, A048 |
| D04-C092 · ACK/pending state, revision conflict and newer-schema read-only | RETAIN | Current mm.smartScreens owner-scoped client/CAS. Do not replace working recovery with D04 state machinery. | D04; qualified F01/F02 for composition; existing source owner for implementation | A035, A064 |
| D04-C093 · Current thesis saved filters and create/rename/delete | RETAIN | Existing /api/thesis-saved-views and rms_saved_view records. Distinguish current thesis object from screen and typed heatmap. | D23 | A036, A048 |
| D04-C094 · Saving technical conditions into Smart Screens | BLOCKED_DATA | Explicit unsupported-content explanation; retain technical controls as local research state. Current grammar excludes technical predicates; do not advertise retention that does not exist. | Smart Screens owner and D23; interim show exact omitted fields before save. | A031, A034, A048 |

### Dislocations

Baseline: terminal:dislocations; [source index](SOURCE_INDEX.md), sections S11.

| ID / capability | Disposition | Successor and reason | Dependency | Acceptance |
| --- | --- | --- | --- | --- |
| D04-C095 · Confirmed/Forming/Ended with seven episode states | RETAIN | Existing episode groups and source lifecycle. State grouping is not a new score or valuation screen. | D04; qualified F01/F02 for composition; existing source owner for implementation | A040 |
| D04-C096 · Free watchlist and paid Market universes | RETAIN | Current access-scoped view control. Personal watchlist access must not become paid by redesign. | D04; qualified F01/F02 for composition; existing source owner for implementation | A041, A056 |
| D04-C097 · Episode identity, detector lineage and knowable-at sort | RETAIN | Episode rows and evidence inspector. One ticker may have several episodes; preserve provenance. | D04; qualified F01/F02 for composition; existing source owner for implementation | A040, A057 |
| D04-C098 · Delayed bars, freshness, rate-limit and polling status | IMPROVE | Field-specific freshness and visible retry countdown. One-minute polling does not imply one-minute bars. | D04; qualified F01/F02 for composition; existing source owner for implementation | A041, A061 |
| D04-C099 · Catalyst coverage and evidence refs | RETAIN | Evidence drawer with coverage/fresh_until/relevant_until. No catalyst is not the same as unavailable coverage. | D04; qualified F01/F02 for composition; existing source owner for implementation | A041, A057 |
| D04-C100 · Stale-empty, null scores and risk geometry | IMPROVE | Unknown/partial state with supplied risk fields only. Do not invent opportunity numbers or call a stale-empty market quiet. | D04; qualified F01/F02 for composition; existing source owner for implementation | A041 |
| D04-C101 · Chart/company entry and exact episode return | IMPROVE | Current terminal?symbol path plus versioned return seam. Return to same episode/group and viewport, even after data refresh. | F01; D07 | A007, A040, A042 |

### Cross-cutting Paper and accessibility obligations

Baseline: all ten canonical routes; [source index](SOURCE_INDEX.md), sections S01, S13, S14, S16.

| ID / capability | Disposition | Successor and reason | Dependency | Acceptance |
| --- | --- | --- | --- | --- |
| D04-C102 · Dark/light and EN/ZH material state parity | RETAIN | Qualified F02 variants and localized product copy. Preserve established variants while replacing old shared chrome. | F01/F02; D04 | A051, A052 |
| D04-C103 · Dense map/table visual compression | RETAIN | Primary analytical object, meaningful comparisons, no generic card replacement. Source and Paper density is a functional capability. | D04; qualified F01/F02 for composition; existing source owner for implementation | A025, A058, A060 |
| D04-C104 · Mobile full journey, overlay/dock and useful content widths | IMPROVE | Qualified shell at320/390/768/1024/1280/1440/1600. Old standalone mobile screenshots cannot prove shared-shell task completion. | F01/F02 | A049, A050 |
| D04-C105 · Keyboard/table equivalence, visible focus and touch targets | IMPROVE | Semantic table/list path and localized accessible controls. Every analytical task remains possible without precise tile pointing. | D04; qualified F01/F02 for composition; existing source owner for implementation | A025, A053 |
| D04-C106 · Loading/zero/filter-empty/partial/stale/error/access states | IMPROVE | Actual editable state specimens tied to read contracts. Beautiful exceptional states cannot substitute for normal task proof. | D04; qualified F01/F02 for composition; existing source owner for implementation | A055, A056 |
| D04-C107 · Reduced motion,400% zoom and contained overflow | IMPROVE | F02 motion/access patterns and actual reflow evidence. Preserve task access across density and movement preferences. | F02 | A054 |
| D04-C108 · Saved/pending/failed/uncertain state truth | IMPROVE | Existing owner state machine with explicit localized feedback. No navigation or timeout falsely confirms or cancels a write. | D23 and existing save owners | A035, A038, A044, A048 |
| D04-C109 · Read me, adjacent annotations and immutable review artifacts | IMPROVE | Prepared in-Paper content plus committed source contract; native creation waits for exact admission. Editable explanation and actual after captures remain an owed deliverable. | P00; F01/F02; D04; independent reviewers | A065, A066, A070 |

### Adjacent D05-owned compatibility capabilities

Baseline: D04 incoming compatibility → D05 /sector_central.html#confluence; [source index](SOURCE_INDEX.md), sections S19.

| ID / capability | Disposition | Successor and reason | Dependency | Acceptance |
| --- | --- | --- | --- | --- |
| D04-C110 · Four Subsector Confluence datasets and benchmarks | RETAIN | D05 Sector Central Confluence view via existing #sc-app/#sc-top and dataset detail paths. S&P subsectors, baskets, Nasdaq and Russell retain distinct payloads and detail paths; QQQ/IWM RS is within-index. | D05 source/interaction owner; D13 membership; D04 incoming compatibility | A002, A073 |
| D04-C111 · Subsector verdict, buy-ready/avoid and double-confluence picks | RETAIN | D05 Sector Central Confluence view via existing #sc-app/#sc-top and dataset detail paths. Keep timing-map research jobs separate from technical-combination ranking. | D05 source/interaction owner; D13 membership; D04 incoming compatibility | A002, A073 |
| D04-C112 · Subsector leadership, sector backdrop and Nasdaq internals | RETAIN | D05 Sector Central Confluence view via existing #sc-app/#sc-top and dataset detail paths. Preserve index context, relative strength, breadth/dispersion, display-only states and missing-artifact behavior. | D05 source/interaction owner; D13 membership; D04 incoming compatibility | A002, A073 |
| D04-C113 · Subsector full searchable/sortable table and per-tab state | RETAIN | D05 Sector Central Confluence view via existing #sc-app/#sc-top and dataset detail paths. Retain full group access, scroll generation and correct background-tab lazy initialization. | D05 source/interaction owner; D13 membership; D04 incoming compatibility | A002, A073 |

