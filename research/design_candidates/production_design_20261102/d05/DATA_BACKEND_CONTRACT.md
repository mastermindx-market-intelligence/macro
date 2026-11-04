# D05 backend and data contracts

This is a consumer/build contract over existing producers, not a new API, database, provenance service, queue, watcher or lifecycle. Field names described as **native** were read in current source. Fields described as **required presentation qualification** must be supplied or explicitly unavailable; the UI cannot manufacture them. Source references: [S03–S06 and S11](SOURCE_EVIDENCE.md).

## 1. Identity and scope

A valid selected subject is the tuple of existing namespace/universe, native kind and native ID. Display labels are never join keys.

| Object | Required existing identity | What it does not imply |
|---|---|---|
| Sector ETF/fund | Native ticker/code plus region/listing metadata | An equal-weight sector basket or a theme |
| Sector-alias group | Producer group key, kind, market/universe | Official fund holdings or a tradable security |
| Curated basket | basket_id/native ID and b- detail namespace where used | Taxonomy identity or benchmark index membership |
| Broad subsector | Finviz/native subsector key plus cohort | Curated basket performance |
| Nasdaq/Russell complex | amalg- key and ns/russell namespace | Every configured member belongs to the named benchmark today |
| THS concept | CN concept key, kind, CN universe/calendar | US GICS sector, US flow coverage or US session clock |
| Taxonomy node/edge | theme_graph native node IDs, relationship kind, source version if supplied | Rank, performance series or dated thesis |
| Company listing | Owner-resolved listing/symbol, venue, currency, region | Interchangeable ADR, mainland, HK or Canadian cross-listing |

Membership uses the producer's configured members and, where supplied, effective-at/version. If historical effective membership is absent, label current membership and avoid a historical-member claim. A proxy is a relationship with its own coverage, not a replacement identity. Parent sector and members not supplied by Central remain not_supplied.

## 2. Numeric semantics and units

| Measure | Calculation / denominator | Display and restrictions |
|---|---|---|
| Relative wealth | (1 + instrument return) / (1 + benchmark return) − 1 | Percent. Both legs need the same aligned close interval, adjustment basis, currency and valid benchmark identity. |
| Arithmetic excess | instrument return − benchmark/cohort return | Percentage points, not percent relative wealth. A06 member vs_basket is this difference over 20 trading sessions. |
| Period return | Native price/return construction over stated horizon | Percent after explicit fractional-versus-percent adapter. Preserve producer horizon semantics. |
| Directional breadth | advances / (advances + declines) | Percent, unchanged excluded; null if no directional observations. Native breadth_basis is adv_over_adv_plus_dec_excl_unchanged. |
| Price coverage, when the source defines it for a session | Current-session valid price observations / configured eligible members | Separate from breadth and from historical availability. In the illustrative A10 fixture, 100/100 are explicitly current-session priced; 20 advances, 10 declines, 70 unchanged gives 66.7% directional breadth. |
| ETF flow | Change in shares × NAV, summed by native window | USD millions in this US source. Creation/redemption estimate, not secondary-market turnover, performance or investor intent. |
| Confluence price-history availability | Native group.n_priced / unique configured member count | n_priced counts members with any nonempty close history, not current-session prices. Label “Price histories”, not current price coverage. |
| Confluence native coverage_pct | basket_index current live members with positive volume / current live members | Fractional, rounded to 3 decimals. Separate from n_priced/n_members; 4/4 price histories can coexist with 2/4 positive-volume coverage (0.5). No denominator is borrowed from another metric. |
| Stock vs group | member.ret_20d − group 20-session return on group calendar | Percentage points. Preserve separate stock and group gates. |
| Cycle position | Engine-provided oscillator position/basis | 0–100 scale is neither probability nor return; show legacy/canonical version explicitly. |
| Phase age | Engine-owned phase interval and calendar | Trading sessions where specified; lower-bound if start predates available history. Never infer exact age from viewport start. |
| Narrative r10 | Native recent 10-session return, fractional | Percent after conversion; independent of slower strategic score. |
| Durability / Hurst / crowding | Native durability bar fraction, Hurst statistic, crowding z | Distinct labels/units. No local blended confidence score or inferred trade size. |
| Grader hit rate | Resolved-call denominator, conditional directional subset where reported | Include matured/accruing/excluded/neutral counts, cohort/horizon and uncertainty. Not win rate, P&L, calibration or predictive validation. |

### Broad rotation engine

Native horizons: **1D, 1W, 1M, MTD, 3M, 6M, 1Y, YTD**.

- rs[h] = performance[h] − cross-sectional median[h], in percentage points.
- zrs[h] standardizes eligible cross-sectional relative returns.
- rs_ratio = mean(zrs[1M], zrs[3M]).
- rs_mom = mean(zrs[1W], zrs[1M]) − mean(zrs[3M], zrs[6M]).
- Quadrants use the source's nonnegative boundary rules. Both axes are dimensionless; neither is relative wealth versus SPY.
- Acceleration compares short and longer weekly pace: 1W minus 3M weekly pace, with the native 1M fallback. Week conversions are 1, 4.345, 13.04, 26.07 and 52.14 for 1W/1M/3M/6M/1Y. Unit is percentage points per week.
- Insufficient z-score observations currently can fall back to zero. The consumer needs an availability qualifier from the owner; otherwise display unavailable, not a measured neutral point.
- The detail's member list is capped at 30, sorted by 1M performance. Show the cap and count; do not claim all constituents are visible.
- Zero acceleration requires neutral copy. A non-positive else branch must not label exact zero as falling.

### Benchmark and series integrity

The display benchmark must equal the actual calculation benchmark. The audited sector path's hard-coded SPY calculation and broader metadata flexibility are a contract risk; mismatch is an integrity error, not a cosmetic label fix. Preserve and disclose basket unbounded fill versus sector bounded fill until the producer owner resolves the difference. Do not infer dividend adjustment, FX conversion, survivorship treatment, membership timing or full historical availability from a rebased line. Missing source qualification remains explicit.

## 3. Clocks, history and corrections

Every visible measure retains the relevant **observation/session**, **availability**, **computation/build** and **publication** clocks when supplied. They are not interchangeable. A file checkout mtime or HTML build time cannot become a market observation time.

- Current daily reading: state settled/provisional if the producer supplies it and show the market/calendar.
- Reconstructed history: later computation over past observations; no contemporaneous-knowledge claim.
- Recorded then: original archived observation/availability identity must exist and precede the user cutoff.
- Published snapshot: immutable bytes/version that a user could have seen; distinct from reconstructed data.
- Confirmed turn: event date and confirmation/available-at date are separate. Append-only marker integrity prohibits retroactive redating.
- Historical cutoff: every date comparison, projection status and source selection uses that cutoff, not the current wall clock.
- Mixed generation: current row, series, event context and benchmark must match required generation/session. Withhold only the affected comparison and preserve valid sections.
- Corrections: consume native correction_lineage/first_observed/first_displayed/supersedes when supplied. Do not derive a “revised” badge from a differing value alone. Central's correction_contract.status is none_native; SC-092 remains blocked for that capability.

### Projection interval state machine

Use valid source dates and the selected analysis cutoff:

| Condition | Required presentation |
|---|---|
| Entire interval ahead | Dated historical rhythm estimate, its basis and qualification; never a guaranteed event |
| Interval has started, median still ahead | “Window in progress”; retain the original interval |
| Median elapsed, upper bound ahead | “Median date passed”; remaining historical window remains visible, not a rolled new estimate |
| Upper bound elapsed | “No current forward estimate”; show original median/window as historical context |
| Missing, malformed or reversed interval | Unavailable with reason; no guessed date |
| New confirmed turn | Preserve prior record and bind any new projection to the new source identity |

Current Cycles already implements a guarded median-elapsed path requiring native overdue=true and a date before META.today's month. Retain this accepted work. The full interval classification above is a target contract; Retail basket detail has a separate reported elapsed-window defect. Reconcile the original path before any repair. No automatic rolling to a later month.

### Scientific qualification

B12 PARITY_FAILS remains disclosed: the inherited comparison reports 13/19 feature mismatches and 44/80 synthetic month-end direction disagreements. Do not promote current hazard output to MODEL/PASS until the science owner proves compatible inputs, cohort, epoch, horizon and qualification. W42's 4/6 qualified cells do not qualify up/3m or up/6m; those remain PRIOR. W46 sizing remains inert at 1.0; W51 lead-lag remains STOP. Preserve descriptive history, conditional uncertainty and observed outcomes without extending forecast/trade authority.

## 4. Native publication and research adapter

### sector_central.publication.v1

Native fields: as_of, built_utc, secondary_sources (flows_html, si_handoff, action_board, baskets, grader), premium_payload (path, written, withheld_rows), history_mode=observed_at_build, correction_contract.status=none_native, crowding_input and research_handoff metadata.

Secondary reads distinguish absent, malformed, read_error and ok, with inline error state where appropriate. Preserve these modes instead of a generic empty array. Mandatory engine failure in the focused publication lane must not publish a fresh successful empty reading.

Free consumers are sector_central_data.js and sectordata/sector_central.json. Paid action rows use their own premiumdata/sector_central.json, not us_stocks.json. Keep the pre-HTML preview/locked split aligned with the same source list and validate payload schema/page before hydration. Existing public-context lanes remain public; D05 does not expand or reduce entitlements.

### sector_central.research_handoff.v1

Reuse engine/sector_research_handoff.py. Native version=1 structure:

- subject: kind, native_kind, id, name_en, name_zh, canonical_entity_ref, canonical_status.
- snapshot: artifact, session, generation {as_of,built_utc}, clock=settled_daily_session, content_sha256.
- source: producer, publication_schema, secondary-source status map.
- methods: evidence_mode=descriptive, claim=no_recommendation, methods_ref=null and methods_status=not_bound until the owner binds a real destination.
- return_context: route sector_central.html, query.g, hash #map, safely encoded href.
- destinations: detail, detail_reason, sector-only Prophet bridge, research=null / receiver_not_bound.
- relationships: parent_sector and members supplied/not_supplied.
- dossier: adapter_only. Governance, authority_caps, input_receipts and dossier_hash are not provided by this adapter.

The row digest is SHA256 over canonical sorted compact UTF-8 JSON excluding its research_handoff key. Re-attaching the adapter must not change the digest. A group proxy ticker is only a supplied canonical reference, not proof of a Company listing or parent relationship.

The UX return requirements extend the existing shared originNav/receiver contract; they do not create another authoritative return store. Until receivers support full filters/focus/history, report partial application rather than “exact return restored.”

## 5. Cycles transport and lazy data

Existing builder emits:

| File/global | Content | Loading contract |
|---|---|---|
| sector_cycles_data.js / SECTOR_CYCLES | Core metadata/cards; sectors' oscillator and turns; guarded rotation context | Initial meaningful rendering |
| sector_cycles_series_data.js / SECTOR_CYCLES_SERIES | Price for every family; non-sector osc/turns; sector fx/usd_record/rs_history where supplied | Deferred after first paint; same publication identity |
| sector_cycles_narr_data.js / SECTOR_NARR | Dated narratives keyed by native series ID | On focus/detail demand; TTL/stale quarantine |
| sector_cycles_dna_data.js / SECTOR_DNA | Historical mechanisms / history-rhymes | On demand |
| sectordata/sector_cycles.json | Full unsplit native model | External/debug consumers, unchanged by split |

split_cycles_payload is lossless by globally unique entity ID across sectors/baskets/nasdaq/russell. Missing ID leaves the record intact in core rather than inventing one. The input is not mutated. Native rotation/fragmentation context is stamped before split and session-aligned with the consumer; do not re-trust a raw optional file without this guard.

The forward log keeps first observation per date/ID. Backtest turn records require valid counts, common tau_months, valid as_of and consistent pooled totals. Label BACKTEST separately from prospective records. Never merge those cohorts into a flattering single rate.

## 6. Confluence and regional payloads

Native group detail includes group, kind, as_of, ohlc_dir, sig_dir, back, stock_base and generated_utc. Group data includes configured n_members, n_priced, fractional coverage_pct, count-based reliability, native state/class, entry and members.

OHLC array order is [YYYY-MM-DD, open, high, low, close, dollar_volume]. NaN/Infinity are serialized to null. Preserve the US/NYSE versus CN calendar and exact source namespace. Marker integrity uses the existing append-only merge; do not deduplicate by display date or move markers.

Native Nasdaq fixture as of 2026-10-30:

| Listing | Price | 20-session return | Excess versus basket | Stock tier |
|---|---:|---:|---:|---|
| VRT | 232.50 | −7.8% | +13.7 pp | T2 |
| CEG | 262.38 | +1.9% | +23.4 pp | Unavailable |
| NBIS | 154.14 | −36.5% | −15.0 pp | Unavailable |
| CRWV | 54.87 | −38.8% | −17.3 pp | Unavailable |

Group: amalg-ai-power-neoclouds, kind sector, 4 configured/4 members with price history, n_live=4, native positive-volume coverage_pct=1.0, reliability low, BELOW_TREND, side avoid, entry eligible=false, buyable=false, above200=false, reason flat:cut. VRT's separate stock buyable=true does not override the group. Member price is the last available close per member; this path does not supply a per-member timestamp. The group as_of cannot certify every member price is from that date. The table is source evidence, not a recommendation or current quote.

Basket thin/gateable census has a source/publication split: current compute_basket_confluence emits n_listed, n_gateable (successfully scored groups), n_thin, n_below_min_members and n_unscored. However, the committed site/marketdata/basket_confluence.json read at this audit pin has only n_baskets/n_high/n_med/n_low_conf/thin_share in coverage. SC-066's inherited gate remains held pending actual publication and consumer proof, rather than a claim that engine fields are still absent. n_gateable is not buyable or entry-eligible; display “scored groups” if the owner accepts that wording.

US, Nasdaq and Russell use separate directories/artifacts. China THS has its own keys/calendar and china_lookup base. Canada and HK maintain their regional routes and listing identity. Unsupported regional flow/forecast/constituent coverage remains unavailable; never fill with US values.

## 7. Research and taxonomy producer contracts

State of Themes reads site/neuralwebdata/theme_state.json, theme_thesis.json, theme_asymmetry.json and theme_pathways.json; data/neuralweb/theme_phase_history.jsonl; basketdata/options_witness.json, clinical_pipeline.json, trade_flows.json and foresight_cascade.json. theme_crosswalk maps a story to its primary basket; it does not make those objects identical.

Existing outputs include research_priority.json and theme_lanes.v1, with **theme_intelligence.consumer.v1**. Preserve dimensions leadership, thesis, crowding, entry and health separately. Native owner dimensions whitelist state/reason/label/value/band, source_records, clocks, watermarks, bar_status and correction_lineage. Source-record keys retain identity only; authority requests are stripped.

Independent evidence requires the shared tuple source_family (or evidence_family), parent_identity, observation_session and input_hash (or source_input_hash). Repeated projections of one observation are one evidence family, not multiple confirmations. Missing identity cannot contribute independent confirmation.

A fired falsifier is INVALIDATED. The current source returns UNCONFIRMED only for an explicit positive falsifier_n_data_missing. An absent thesis/falsifier_summary instead defaults any_fired=false and n_data_missing=0, which currently yields NOT_DETECTED. This is a source-owner gap: the required target behavior for absent thesis/summary is UNAVAILABLE or UNCONFIRMED, never a successful no-invalidation reading. Do not describe that target as already implemented. Absent crowding is UNKNOWN, not low risk. Page-level stale legs do not prove per-theme health; the current health contract says UNCONFIRMED/PER_THEME_HEALTH_NOT_JOINED when appropriate. Availability/publication and correction clocks can legitimately be null. Never fill them from computation time.

Theme Tree reads current nodes and edges from the existing theme_graph store and hierarchy breadth adapter. Its as_of comes from data/theme_graph/_meta.json belief_time; absent/invalid belief_time displays Date unavailable. File mtimes are explicitly excluded. Store failures yield an honest unavailable/empty shell. Preserve unknown proxy coverage separately from empty children and no search matches. D13 owns taxonomy/relationship semantics and canonical identity resolution.

## 8. Writes, access, caching and durability

### Existing saved investigation owner

Native APIs: watchstore.saveSectorInvestigation({etf,note}) and listSectorInvestigations(). Existing cloud storage is a watchlist named exactly “Sector Intelligence”, with watchlist_symbols section='si'. Signed-in readback uses a real section-filtered server read; reading never creates a list.

The subject is cloud-stored when signed in. Question/snapshot/origin are device-local note data only; no note column exists in this path. Signed-out saves use the existing anonymous local blob. A signed-in failure cannot fall back silently to the anonymous store.

The current ETF input is trimmed/uppercased and must match 1–8 ASCII letters. It is unsuitable for CNQ.TO, mainland/HK symbols or arbitrary theme/group IDs. Do not widen that allowlist or overload symbol with serialized context. Regional/theme saved investigations require the existing owner to adopt a reviewed contract.

Per-symbol in-flight chaining prevents one-tab duplicate insertion. The source explicitly notes no unique index on watchlist_id/symbol; cross-tab races and legacy duplicates still need owner treatment. Readback collapses legacy duplicates by earliest created_at with latest device note. Do not assert global exactly-once durability from that client behavior.

Required UI: distinguish cloud subject saved, notes on this device, pending, confirmed failure and outcome unknown. A resolved function alone cannot prove localStorage succeeded, because local note write errors are caught. Read back the actual note before confirming it. Full cross-device investigation acceptance remains held.

### Access and cache

- Let existing auth settle before paid fetches. Preserve SSR free preview during auth, 401, 403 or offline failure.
- Validate tier payload schema/page and account context. No private rows in public HTML, global cache, cross-account storage or URL.
- Cache read-only evidence by native namespace/entity, region, horizon, cutoff/history mode and source-generation identity. Use the existing artifact revision/hash/version scheme; do not invent an ungrounded freshness TTL.
- Consumer request tokens fence late results after scope, locale, auth or history changes. In-flight writes retain their owner identity; UI navigation does not cancel or replay them.
- Show each source's own freshness. An updated aggregate build does not refresh its oldest ingredient.
- Retry read failures only through an explicit bounded action; confirmed unchanged outage does not trigger a polling loop. No automatic retry for unknown writes.
- factors.html retains deny/404 policy. No new access grant follows from a source route existing.

## 9. Owner acceptance checklist

Backend is ready for build integration only when source owners supply or explicitly reject: benchmark identity/adjustment/fill basis; cohort eligibility/null qualification; required historical membership/available-at evidence; complete generation binding; group versus stock gate mapping; unsupported thin/correction fields; safe exact-return receiver support; regional listing resolution; and persistence capabilities for the promised saved record.

No missing contract may be solved by a frontend-made signal, local score, date, membership edge, correction badge, forecast, sizing factor, independent-evidence count or parallel store.

