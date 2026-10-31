# C1 exposure-join census — News Intelligence Estate (2026-10-31)

BASE (HEAD): fff8ab44c690f1c7e68fe3e4cc49fc92663917ee
RUN_ID: NEWS-W3-C1-CENSUS (lane/news-w3-c1-census-r1)
MODEL: glm-5.3 (Fabric review-grade worker under seat 602cd180)
PACKAGE: MASTERPLAN §7.C C1 — "Map news events to dated company/theme/subtheme/product exposures; Existing GMI/identity/CTE joins; ambiguous and unsupported relationships remain explicit nulls" (research/news_intelligence_estate_20261021/MASTERPLAN.md:356)

## Scope and method

Inventory only. For every existing join by which a news object can reach a company,
theme, subtheme or product exposure — and for every identity/CTE/GMI join the C1
package names — this census records where it lives, its keys, its date semantics,
the rights field that travels with it, and its behaviour on ambiguity. All line
numbers are at HEAD `fff8ab44c690f1c7e68fe3e4cc49fc92663917ee`. Every cited line was
printed with `sed -n` at HEAD before writing (Evidence section).

Files examined (all 21 paths from the frozen packet; `test -f` / `test -d`):

| path | status | grep hits / lines |
|---|---|---|
| engine/news_event_ledger.py | EXISTS | 4 / 313 |
| engine/news_events.py | EXISTS | 3 / 724 |
| engine/qbus_news_universe.py | EXISTS | 6 / 215 |
| engine/qbus_news_context.py | EXISTS | 5 / 55 |
| engine/qbus_news_annotate.py | EXISTS | 1 / 88 |
| engine/company_theme_exposure/ (5 files) | EXISTS (dir) | contracts 55/305, health 13/72, successor 118/1050, views 68/470, __init__ 0/5 |
| engine/theme_graph/identity.py | EXISTS | 6 / 237 |
| engine/theme_graph/identity_resolution.py | EXISTS | 0 / 757 (module docstring + statuses carry the semantics; grep pattern matches 0 body lines — clock fields are `resolution_asof`/`known_at`, spelled without the pattern's `as_of`) |
| engine/theme_graph/membership_evidence.py | EXISTS | 58 / 1455 |
| engine/theme_graph/native_disclosure_propagation.py | EXISTS | 1 / 238 |
| engine/theme_graph/issuer_economic_context.py | EXISTS | 1 / 76 |
| engine/theme_graph/ontology.py | EXISTS | 23 / 821 |
| engine/theme_graph/rights.py | EXISTS | 19 / 221 |
| engine/theme_graph/rights_use.py | EXISTS | 19 / 287 |
| engine/market_ontology/ (8 files) | EXISTS (dir) | exposure_map 91/1214, cohort_us_china 15/310, mining_theme_research 14/1160, mining_dependency_binding 10/323, bea_gvc_current 5/522, __init__ 5/16, mining_company_card 0/55, ticker_cik_census 0/830 |
| engine/stock_identity/ (11 files + replay/) | EXISTS (dir) | analog_pit 2/619, pilot 7/334, all others 0 |
| engine/ledger_identity.py | EXISTS | 1 / 372 |
| engine/exposure_math.py | EXISTS | 10 / 182 |
| engine/theme_catalyst_binder.py | EXISTS | 6 / 384 |
| engine/transmission_company_continuation.py | EXISTS | 1 / 373 |
| engine/theme_context.py | EXISTS | 8 / 911 |

Files MISSING: **none**. Every named path exists at HEAD; a missing file would have
been recorded as a census fact, not an error.

The grep (run per file, `grep -n -E "theme_id|subtheme|product_id|exposure|as_of|effective|seendate|received_at|rights" <file>`; counts above, cited lines below). Follow-up targeted greps and `sed -n` reads are listed in Evidence.

Supporting files read for the join chains (cited where a row depends on them):
engine/qbus_news_store.py, engine/qbus_news_velocity.py, engine/qbus_news_intake.py,
engine/qbus_news_universe_snapshot.py, engine/qbus_news_receipts.py,
collectors/benzinga_news.py, engine/news_vector.py, engine/news_flow.py,
engine/financial_news.py, engine/intelligence.py, engine/theme_graph/store.py,
engine/theme_graph/identity.py, scripts/run_qbus_news.py.

Inputs read first (STEP 1): MASTERPLAN.md §5.1–5.4 (lines 226–265), §7.C (352–360);
D1_NEWS_INPUT_TRACE.md (all); B1_SCHEMA_INVENTORY.md (all); A1_SOURCE_DELIVERY_MATRIX.md §3 (122–135).

News object families B1 names (research/news_intelligence_estate_20261021/B1_SCHEMA_INVENTORY.md:14-22):
F1 source report/revision (qbus news store), F2 story group (qbus cluster), F3 legacy
event (news_events + news_event_ledger + legacy qbus items), F4 Chronicle, F5 News
Impact event/proposition/thesis, F6 quantitative observation, F7 consumer context
(intelligence bundle + integrated answer).

D1 consumers that touch company/theme identity (research/news_intelligence_estate_20261021/D1_NEWS_INPUT_TRACE.md):
- T1.3/T1.4 theme_flow → theme_activity fusion, per-basket themes (D1:33-34);
- T4.1 financial_news.mastermind_by_ticker per-ticker flow (D1:92);
- T4.2/T4.3 by_ticker.json → intelligence bundle, ticker-text key (D1:93-94);
- T4.10 qbus store news_flow → app/ticker_news.py per-security API (D1:101);
- T6.3 qbus_news_annotate classify_event into qbus annotations (D1:124);
- Mastermind boundary consumers: get_intelligence / get_news, portfolio/lenses _news_by_ticker/_news_row/_name_rows (D1:143-148, D1:231-239).

## Six meanings and time rules this census is measured against

Quoted from MASTERPLAN §5.1 (table rows, research/news_intelligence_estate_20261021/MASTERPLAN.md:230-237) — the row C1 lives in:

> | Exposure/impact interpretation | Sourced relationship, valid interval, mechanism, assumptions, scenario, counter-evidence and falsifier | GMI/Company Theme Exposure/TXI/MarketOntology/News Impact | (MASTERPLAN.md:236)

The other rows a news→exposure join must not conflate (MASTERPLAN.md:232-237):
Source observation/version carries "published/received/available clocks, rights and correction lineage" (:232); Economic event/claim carries "affected entity, evidence span, supersession" (:234); Consumer decision context carries "Exact accepted inputs, as-of envelope, provenance, uncertainty" (:237). "These are conceptual distinctions, not instructions to create six databases." (:239).

§5.2 Time and identity rules (MASTERPLAN.md:241-247), quoted:

> "Preserve publisher time, first local receipt, source availability, economic effective time, revision availability, materialisation time and consumer decision cutoff separately. A later materialised artifact may reconstruct an earlier cutoff only when its underlying evidence was actually available then. A historical news archive retrieved today is not proof that the system possessed it in the past." (:243)

> "Bind issuer, security/listing, geography and currency through existing identity owners. Ticker text is a display label, not a universal identity. A customer mention, competitor similarity or shared theme cannot manufacture a supplier relationship." (:245)

> "Use time-valid graph membership. Never apply today's taxonomy, company exposure, consensus or final legal state to a historical decision without an explicitly qualified as-of reconstruction." (:247)

§5.4 Correction and independence rules (MASTERPLAN.md:257-263), quoted in part:

> "A copied wire is one originating information family. Ten outlets do not create ten independent confirmations." (:259)

> "A correction creates new history and invalidates affected current derivatives. It does not rewrite what a user could have known earlier." (:261)

> "Corrections invalidate or supersede generated current interpretations while preserving original as-known evidence and decision history." (:263)

A1 §3 independence rules apply to any echo/corroboration field travelling on a join
(A1_SOURCE_DELIVERY_MATRIX.md:122-135; enforcement honesty at :135: independence
counting "not enforced in code" beyond the family rows there).

## Join inventory

One row per join. "from" = news object + key field; "to" = exposure target + key
field. Date semantics names the field and its meaning. Ambiguity: NULL = explicit
null/typed absence; DROP = silently omitted; GUESS = heuristic binding.

### A. News object → company

| join_id | from | to | date semantics | rights carried | ambiguity behaviour | pinned by test |
|---|---|---|---|---|---|---|
| J01 collectors/benzinga_news.py:route_revision (:358-377) | wire NewsRevision `provider_tickers` (:365-372) | company `security_id` via universe `alias_bindings` (:365, :373-376) | universe qualified at one `asof` at ingest; membership half-open `[valid_from, valid_to)` + `known_at` (engine/qbus_news_universe.py:147-162); binding is current-at-ingest, no retroactive read | NONE at this hop (rights enforced at read, J02-J04) | DROP per ticker: unmatched ticker → no security_id appended, item still stored (:369-372); an ambiguous alias anywhere → universe status "held" (engine/qbus_news_universe.py:190-194, :203) → `BenzingaRoutingError("universe_not_qualified")` (:361-362) — fail-closed whole-universe, not per-item NULL | tests/test_benzinga_news.py |
| J02 engine/qbus_news_store.py:snapshot (:1751-1830; read by evidence_for_security :1923-1974, changes_for_security :2185+) | `security_id` → news_security_index (DDL :288-299) → news_states → news_cluster_members → clusters (join :1806-1825) | story/cluster rows (F2) keyed `story_id = source:source_item_id` | NO as-of parameter: current-state read transaction (one read snapshot, :1926-1928); per-report clocks returned verbatim — `published_at`, `updated_at`, `source_event_at`, `received_at`, `version_clock_domain` (:1957-1961) | `NewsReadRights`: allowed_sources + per-field allow_title/url/teaser via `_read_sources`/`_curated_clause` (:1777-1788); redaction on read | exact PK join — nothing to guess; withdrawn/removed member excluded by `status != "active"` (:1944-1945); watermark monotone via append-only change log (:1794-1805) | tests/test_qbus_news_propagation_estate.py |
| J03 engine/qbus_news_store.py:news_flow (:1976-2033) + engine/qbus_news_velocity.py:compute_news_velocity | `security_id` over news_security_index + projection (:50-111 SQL) | per-security flow counts (ticker_news.flow.v1) — not an exposure entity, a count | effective time = `published_at` else `received_at` (engine/qbus_news_velocity.py:290-297); closed windows `[now-24h, now]` vs the `now` parameter (:324-347); `as_of = now` (store :2017) | allowed_sources + url/teaser field rights flow into velocity (store :2024-2031) | NULL typed: no accessible sources → `state: unavailable, reason: no_accessible_sources`, all fields null (store :1999-2015) | tests/test_ticker_news_flow_api.py |
| J04 engine/qbus_news_context.py:news_evidence_bundle (:18-55) | `security_id` param → store.evidence_for_security (:42) | permitted story evidence (qbus.news_evidence.v1), revision-bound (`revision_id` per report, :1953) | `observed_at` = call-time now (:26, :34); no historical as-of; exact current revisions only | FULL: receipts loaded + `derivative_processing` filter (:29-30), `combine_news_rights` (:31), audience enum (:15, :22-23), receipt_refs emitted (:45-50) | NULL typed: no allowed sources → `state: restricted`, empty stories (:39-40) | tests/test_shared_news_intelligence.py |
| J05 engine/financial_news.py:_gdelt_tag (:112-127) → mastermind_by_ticker (site/news/by_ticker.json, D1 T4.1-T4.2) | headline free text | ticker TEXT (display namespace) via entity_resolver.resolve_us confidence ≥ 0.75 + match_entities fallback (:117-127) | per-item `published` = seendate; artifact `asof` = build day (D1:92-93); no as-of reconstruction | NONE (artifact stamped `is_context_only: true`, D1:93) | GUESS: text-resolution heuristic with a confidence floor; no tag → ticker absent from by_ticker; Polygon provider tickers carried verbatim instead (:290-292) | tests/test_entity_resolver.py, tests/test_financial_news.py |
| J06 engine/intelligence.py:build / load_and_build (:234-245, :285-291) | five published artifacts incl. site/news/by_ticker.json `tickers` | bundle row keyed `(ticker).upper()` (:241-245; B1 F7-a1, B1:203) | bundle `as_of` = build date only (B1 F7-c1, B1:206); no per-item clock on the aggregates consumers rank (D1:168) | disclaimer-level only (B1 F7-e1, B1:209) | absent facet → `has_*` false (implicit absence, B1:203); never an id-resolved issuer | tests/test_intelligence.py |
| J07 engine/news_events.py:enrich_with_qbus (:636-724) | headline `_id` (exact) else `title` (shingled fallback) (:697-709); subject = first ticker else theme token (:679-681) | legacy qbus `event_key` → echo {n_sources, n_desks}, novelty_z (:693, :710-716) | `asof` = headline's own seendate day, fallback `date.today()` (:683-690) — event-time as-of with a today fallback; store is keep-first current (B1 F3-b1, B1:95) | NONE | NULL fail-open: missing store → None fields (:645, :717-718); the shingled-title branch is a GUESS-grade heuristic match (B1 G01, B1:247) | tests/test_news_events.py |
| J08 engine/transmission_company_continuation.py (blast channel company name → link; identity law :12-15, :156-175) | TXI chain blast channel company NAME string | `security_id` via `aliases.resolve(VENDOR, symbol, decision_date)` + round-trip check (:12-15) | `decision_date` from the chain's own `asof`; render-time as_of explicitly NOT borrowed (:327-336) | NONE (no source text emitted; href carries only routing keys, :19-23) | NULL typed: `NoLink` reasons unresolved / no_current_symbol / stale_alias / round_trip_mismatch (:12-15, :167); missing/malformed chain asof → identity_unavailable projection (:334-336) | tests/test_transmission_company_continuation.py |

### B. Identity rail (the "identity joins" C1 names)

| join_id | from | to | date semantics | rights carried | ambiguity behaviour | pinned by test |
|---|---|---|---|---|---|---|
| J09 engine/qbus_news_universe.py:qualify_universe (:84-215) + engine/qbus_news_universe_snapshot.py (builder :281-307) | ticker + aliases per security row | `security_id` bindings (`alias_bindings` :198-202) | fully dated: snapshot `effective_at`/`known_at`/`fresh_until` (:110-124); membership `[valid_from, valid_to)` + `known_at` vs supplied `asof` (:147-162); authorities `breadth.current_sp500` / `breadth.sp1500_pit_membership` (snapshot :292-293) | NONE (identity plane) | NULL typed per alias: ambiguous aliases excluded from bindings and listed (`ambiguous_aliases` :190-194) — but any ambiguity holds the WHOLE universe (status "held" :203), which the ingest runner treats as a routing error (J01) | tests/test_qbus_news_universe_snapshot.py, tests/test_qbus_news_intake.py |
| J10 engine/theme_graph/identity_resolution.py:derive_rows / _resolve_node_row / resolve_graph_node_identity (:385-648) | GMI company node `co:<market>:<SYMBOL>[#epoch]` | Data OS `security_id`/`listing_key`/`issuer_id` via `master_inception_exact` or `vendor_alias` (:101) | two-clock law: `resolution_asof` current vs historical mode restricted to DATED alias rows (:485-499); sidecar re-derived every build; `resolve_graph_node_identity(node_id, asof=...)` re-runs purely over committed inputs (:30-36) | NONE (identity plane) | NULL typed: closed states incl. `AMBIGUOUS` → null ids + `refusal_reason` "never picked by precedence/cap/name" (:524-530, :97-101); cross-market collision → `NOT_IN_MASTER` with would_resolve_to receipt (:507-514) | tests/test_theme_graph_identity_resolution.py |
| J11 engine/ledger_identity.py (ticker rename key migrations; :1-76) | old ticker key → new key (e.g. SATS→ECHO effective 2026-06-24, :13) | merged ledger identity (`config.yml quality.ticker_key_migrations`, :54-56) | effective-dated rename, curated-only (detectors propose, curation ratifies, :72-74) | NONE | refuse-by-default: undeclared duplicates are candidates, never identity (:72-74) | tests/ (grep ticker_key_migrations) |
| J12 engine/market_ontology/ticker_cik_census.py (:1-40) | ticker↔CIK pairs over frozen `data/reference/` plane | collision CLASS report (C1 strict, C2 vendor-namespace divergence, C3 CIK access, C4/C5 renderer) — a census, not a join | `decision_date` injected, never wall-clock (:26-27) | NONE | reports; "a census reports; it never fails a build" (:26) | tests/ (grep ticker_cik_census) |
| J13 engine/stock_identity/ (Identity Atlas) | ticker identity fingerprints | descriptive identity artifacts only | `analog_pit.admit_as_of` PIT admission (:195, :544) | authority block all-false stamped on every artifact (engine/stock_identity/authority.py:13-21) | descriptive only — `can_rank/can_size/can_gate/can_originate_signal/can_escalate` all false (authority.py:5-8) | tests/ (grep stock_identity) |

J12/J13 are inventory facts: neither joins a news object to anything (grep counts 0 for the join vocabulary).

### C. News object → theme

| join_id | from | to | date semantics | rights carried | ambiguity behaviour | pinned by test |
|---|---|---|---|---|---|---|
| J14 engine/news_vector.py:classify_theme (:153-160; taxonomy :66-75) | headline title text (keyword match, order-sensitive) | macro narrative bucket (`geopolitics`, `trade`, …) — one label, not a graph node | event row's own `seendate`/`first_seen_utc` (B1 F3-c1/c2); no as-of logic in the classifier | NONE (source_tier honest label only, B1 F3-e1) | DROP: no keyword hit → `None` → off-narrative, the event is dropped from the bus (:154, :204-205) | tests/test_news_vector_themes.py |
| J15 engine/news_flow.py:theme_flow (:86-95; map :30-49) | basket_id via static curated `BASKET_TO_GDELT_THEME` map | news velocity/acceleration per basket over mapped buckets | events' `ts` (from `first_seen_utc`, D1 T1.2) vs `today` 7d window (:92-95); build-day aggregation, no as-of param | NONE | NULL at basket grain: unmapped basket → `None` "no news leg (honest)" (:30-31, :87-90); upstream per-event DROP from J14 | tests/test_news_flow.py |
| J16 engine/company_theme_exposure/views.py:build_exposures (:217-283) | company `ticker` (safe_ticker) → `_active_membership` (:96-132) → `_crosswalk_index` (:135-193) | theme exposure item `{theme_id, name_en, name_zh, basket_id, mapping_qualifier}` (contracts.py:33) | DATED: membership intervals `added`/`removed` vs `run_date` (:120-131); `run_date` = explicit `as_of` param else company-intelligence manifest `generated_at` (:236-239); `theme_state` receipt `{status, as_of, sha256}` with staleness (:56-93) | NONE on rows; envelope `authority: context_only` (contracts.py:20, :170) | NULL typed: unmapped active basket → coverage status + `active_membership_unmapped` warning (:200-214, :265-267); crosswalk basket not accounted for → `ContractError` fail-closed (:190-192); `mapping_qualifier` ∈ {direct, proxy, curated} derived from crosswalk note text (:165-167, validated contracts.py:206-207) — a methodology label, "never an asserted company relationship" (:172-174) | tests/test_company_theme_exposure.py |
| J17 engine/theme_graph/ontology.py:compose_neighborhood / compose_proposal_review (:566+, :736-821) | exact `node_id` (theme:/basket:/ltheme:/co:) — "labels are never fuzzy-matched" (:723-726) | as-of graph relations + mapping proposals (basket:/ltheme:→theme:) | DATED, two clocks: `asof` filters valid time (birth/retire vs asof, :240-247, :263-275); `knowledge_cutoff` filters `computed_at` belief time (:249-261); both echoed on the result (:707-709) | rights receipt per relation endpoint via `_default_rights_resolver`/`_rights_for_relation` (:295-310, :367-385, :424); conflict raises (:385) | NULL typed: `SUBJECT_NOT_FOUND` (:701-706), `ENDPOINT_UNAVAILABLE`, `UNSUPPORTED_SUBJECT`, `RELATION_ABSENT` (:771-810); duplicate visible proposal → error (:782-783) | tests/test_theme_graph_probation_hierarchy.py |
| J18 engine/market_ontology/exposure_map.py:compose_exposure_map (:976-1080; walk :586-660) | CALLER-SUPPLIED `ShockSpec.theme_node_ids` — "never derived … that is a causal claim" (:18-21) | company nodes `co:` via MEMBER_OF (1 hop) / basket-bridge / ltheme-bridge (2 hops) (:597-657), then identity rows (:659-669) | DATED, two clocks: belief collapse "max belief_time <= knowledge_cutoff per edge_id … then valid_from <= asof < valid_to" (:47-55, :476-530); edge substrate columns `valid_from`/`valid_to`/`belief_time` (engine/theme_graph/store.py:58-59) | rights family gate per basket/ltheme plane: `family_for_node_id` + `assert_public_emission_allowed`; refusal → typed abstention (:380-413, :611-625) | NULL typed everywhere — "a rights refusal and an unresolved identifier are all TYPED NULLS … never raises for a data-availability reason" (:22-24): SHOCK_UNKNOWN, NO_THEMES_DECLARED, STORE_UNAVAILABLE, BELIEF_AFTER_KNOWLEDGE_CUTOFF, BELIEF_TIME_UNKNOWN, IDENTITY_UNRESOLVED, NO_RESOLUTION_ROW (:1021-1078, :659-669) | tests/test_market_ontology_exposure_map.py, tests/test_theme_graph_tier_guard.py |

**J18 has no production caller at HEAD**: `compose_exposure_map` is referenced only by `engine/market_ontology/__init__.py:14-16` (re-export) and tests (grep over engine/ scripts/ app/ tests/).

### D. Subtheme

| join_id | from | to | date semantics | rights carried | ambiguity behaviour | pinned by test |
|---|---|---|---|---|---|---|
| J19 engine/theme_graph/identity.py:local_theme_node_id (:165-178) + exposure_map.py `_walk_theme` Path C (:630-652) | vendor subtheme source key (`ltheme:finviz:…`, `ltheme:ths:…`; identity.py:58, :62-63) | canonical `theme:` node ONLY via curated EXPRESSES edge — "deliberately NOT canonical GMI vocabulary … the two meet only through a curated EXPRESSES edge" (identity.py:168-171) | inherits J18's edge clocks (valid_from/valid_to/belief_time) on the EXPRESSES + MEMBER_OF edges walked | rights family per ltheme (rights.py registry; unknown family fails CLOSED, rights.py:23-26); emission gate abstention (exposure_map.py:611-625) | refuse: unknown local-theme family → ValueError, "families do not default into existence" (identity.py:174-176); registered-but-unresolved family → emission refusal (rights.py:27-29); grammar-skip vs rights-ordering guarded so a rights refusal cannot be rewritten as NO_MEMBERSHIP_YET (exposure_map.py:622-629) | tests/test_market_ontology_exposure_map.py |

No news object reaches an `ltheme:` node through any existing join (the only news→theme paths are J14/J15, macro-bucket vocabulary; J18's theme ids are caller-supplied).

### E. Product

| join_id | from | to | date semantics | rights carried | ambiguity behaviour | pinned by test |
|---|---|---|---|---|---|---|
| J20 NONE — no product join exists | — | `product_id` appears in engine/ only as a rights-receipt billing field (engine/qbus_news_receipts.py:43, :137, :187) and Stripe feature wiring (scripts/stripe_bootstrap.py:136-146); no product node, table or edge exists in any inventoried file | — | — | — | — |

Closest existing product-scoped evidence: `build_activity_membership_evidence` returns `scope.product` from a native disclosure fact with `segment: UNDISCLOSED` (engine/theme_graph/membership_evidence.py:1401-1405) — evidence-only, not a product entity join.

### F. GMI owner-side exposure evidence joins (no news input today)

| join_id | from | to | date semantics | rights carried | ambiguity behaviour | pinned by test |
|---|---|---|---|---|---|---|
| J21 engine/theme_graph/membership_evidence.py:build_activity_membership_evidence (:1319-1455) | issuer `co:` node + native disclosure fact (basis must be `native_disclosure_fact`, :1330-1336) | micro-theme `theme:` node evidence (gmi.activity_membership_evidence/v1) | DATED by `knowledge_cutoff` instant: facts/editions with `known_at` > cutoff excluded BEFORE selection (:1340-1346); typed clocks block — publication date-grain, observation/knowledge instants, `effective: UNDISCLOSED` typed null (:1426-1436) | full: `target_definition_rights` + `source_rights` via engine.theme_graph.rights + purpose ruling bindings (:1408-1418) | NULL typed via `ActivityAdmissionRefusal` codes: IDENTITY_HINT_NOT_ADMISSION, GROUP_TO_MICRO_REFUSED, KNOWLEDGE_CUTOFF_EXCLUDED, SPECIES_NOT_ADMITTED, AMBIGUOUS_IDENTITY, IDENTITY_UNRESOLVED, ISSUER_IDENTITY_MISMATCH … (:1203-1209, :1330-1372); "Refuses … rather than guessing" (:1326-1331); `graph_membership_use: NOT_GRANTED` (:1419) | tests/test_gmi_activity_membership_admission.py, tests/test_gmi_activity_proposal_ledger.py |
| J22 engine/theme_graph/native_disclosure_propagation.py:bind_current_supplier (:39-126) | subject/object symbols + owner-qualified disclosure context | current supplier binding → K3 compiler input (issuer_id/security_id parties, :100-104) | CURRENT-ONLY by law: `identity_mode: current`, `query_as_of` must be None (:63-64); clock chain sec_accepted…≤ fact_known ≤ compiled enforced (:70-81); "do not backdate these security/issuer bindings" (:45-47) | purpose/audience pinned inside the context (`private_company_intelligence_context` / `company_intelligence_entitled`, :57-58) | NULL typed refusal codes (NATIVE_SUPPLIER_*); identity change vs pinned snapshot → NATIVE_SUPPLIER_IDENTITY_CHANGED (:96-99) | tests/test_gmi_native_disclosure_propagation.py, tests/test_h20_supplier_conditional.py |
| J23 engine/market_ontology/mining_theme_research.py (research bundle; validity check :213-250) | `anchor_theme_id` query → mining packets with subject id/cik | issuer identity rows (`stable_subject_id`/`cik`) | DATED identity honesty: packet omitted when period precedes issuer `valid_from` unless an accepted `time_valid_bridge` (:218-242); limitation code `omitted:period_before_issuer_validity` (:250) | none on the join; source limitation codes carried | NULL typed: `missing_issuer` blocks financial joins, "do NOT invent one" (:699-702) | tests/test_mining_composition.py, tests/test_mining_witness_expectations.py |

### G. Persisted news objects carrying company/theme text (store rows, not joins)

| join_id | from | to | date semantics | rights carried | ambiguity behaviour | pinned by test |
|---|---|---|---|---|---|---|
| J24 engine/news_event_ledger.py `_EVENT_LOG_COLS` (:75-88) | kept headline row | `tickers` JSON list + `theme` str (display text; produced by J05/J14 upstream) | `first_seen_utc` never overwritten (keep-FIRST, :77; B1 F3-b1), `seendate` publisher date (:78); no effective/available clock (B1 F3-c3) | NONE (B1 F3-e1) | keep-FIRST drops later rows silently — no supersede/withdraw field (B1 F3-d1, B1:100) | tests/test_news_events.py |
| J25 engine/qbus_news_annotate.py:annotate_row (:32-70) | served qbus headline (+teaser when actually served) | `event_type` classification (ticker_news.annotation.v1) — not an exposure target | none (annotation of served text; store clocks govern the item) | `derivative_permitted` receipt gate (derivative_processing boolean, :73-88) | NULL typed: unmatched headline → annotation object with `event_type: null` (:35-37, :52-55); empty title → None (:39-41) | tests/test_qbus_news_annotate.py, tests/test_ticker_news_annotation_api.py |

### H. Vocabulary collisions — "exposure"/"theme" words that are NOT news→exposure joins

| join_id | what it actually is | evidence |
|---|---|---|
| J26 engine/exposure_math.py | dealer OPTIONS dollar exposure (GEX/gamma/vega per contract) — one formula for the options estate; no news, theme or company-exposure semantics | engine/exposure_math.py:1, :126-138 |
| J27 engine/theme_context.py | basket allocation ranks × theme_intel ids (display "Prevailing narrative"); `as_of` from the alloc payload | engine/theme_context.py:620-626 |
| J28 engine/theme_graph/issuer_economic_context.py | issuer_id → current native disclosure contexts (identity_mode current; qualified-empty ≠ unavailable) | engine/theme_graph/issuer_economic_context.py:25-76 |

**Join count: 28 table rows — 21 functioning joins (J01–J11, J14–J19, J21–J23, J25), of which 11 take a news object as the from-side (J01–J08 company, J14–J15 theme, J25 annotation); J24 records the persisted store row those joins produce, not an active join; 2 non-joining identity-census rows (J12, J13); 1 explicit NONE (J20, product); 3 vocabulary collisions (J26–J28).**

## Date-semantics matrix

Is the exposure DATED — does it carry an effective/as-of date distinct from
seen/received, filterable at read time?

| join | DATED | evidence |
|---|---|---|
| J01 route_revision | PARTIAL — membership intervals are dated at qualification, but the written binding is current-at-ingest; no historical re-read | engine/qbus_news_universe.py:147-162 vs collectors/benzinga_news.py:365-376 |
| J02 snapshot/evidence | NO — no as-of parameter; current-state transaction; clocks carried per report, not filtered | engine/qbus_news_store.py:1926-1928, :1957-1961 |
| J03 news_flow | PARTIAL — window math takes an explicit aware `now`, but the item set is current-state with no knowledge cutoff | engine/qbus_news_store.py:1993-2017, engine/qbus_news_velocity.py:324-347 |
| J04 news_evidence_bundle | NO — `observed_at` = call-time now; revision-bound current | engine/qbus_news_context.py:26, :34 |
| J05 _gdelt_tag/by_ticker | NO — build-day asof; per-item published only | D1:92-93 (financial.py:920-925) |
| J06 intelligence bundle | NO — `as_of` = build date | B1:206 (F7-c1); D1:168 |
| J07 enrich_with_qbus | PARTIAL — as-of = the headline's own seendate day, but falls back to `date.today()` and reads a keep-first current store | engine/news_events.py:683-690; B1:95 |
| J08 transmission continuation | PARTIAL — identity resolved at the chain's decision_date (day grain); channel membership itself is not interval-dated | engine/transmission_company_continuation.py:12-15, :327-336 |
| J09 qualify_universe | YES — snapshot effective/known/fresh clocks + [valid_from, valid_to) + known_at vs supplied asof | engine/qbus_news_universe.py:110-162 |
| J10 identity_resolution | YES — resolution_asof; historical mode restricted to DATED alias rows | engine/theme_graph/identity_resolution.py:485-499 |
| J11 ledger_identity | YES — effective-dated curated rename migrations | engine/ledger_identity.py:12-13, :54-56 |
| J12 ticker_cik_census | YES (injected decision_date) — but it is a census, not a join | engine/market_ontology/ticker_cik_census.py:26-27 |
| J13 stock_identity | YES (PIT admit_as_of) — descriptive artifacts only | engine/stock_identity/analog_pit.py:195, :544 |
| J14 classify_theme | NO — keyword label on the event's own clocks | engine/news_vector.py:153-160 |
| J15 theme_flow | NO — rolling 7d window vs build day | engine/news_flow.py:86-95 |
| J16 CTE build_exposures | YES — membership added/removed vs run_date; run_date from as_of param or CI generated_at; theme_state as_of receipt | engine/company_theme_exposure/views.py:120-131, :236-241 |
| J17 ontology neighborhood | YES — asof (valid time) + knowledge_cutoff (belief time), separate | engine/theme_graph/ontology.py:240-275, :707-709 |
| J18 exposure_map | YES — belief_time ≤ knowledge_cutoff, then valid_from ≤ asof < valid_to; two named clocks | engine/market_ontology/exposure_map.py:47-55, :988-995 |
| J19 ltheme path | YES — inherits J18 edge clocks on curated EXPRESSES/MEMBER_OF edges | engine/theme_graph/store.py:58-59 via exposure_map.py:1070-1073 |
| J20 product | n/a — no join exists | engine/qbus_news_receipts.py:43 |
| J21 activity evidence | YES — knowledge_cutoff instant filters known_at before selection; effective clock typed UNDISCLOSED | engine/theme_graph/membership_evidence.py:1340-1346, :1426-1436 |
| J22 native supplier | PARTIAL — current-only by law; clock chain enforced but no historical mode | engine/theme_graph/native_disclosure_propagation.py:63-81 |
| J23 mining research | YES — period vs issuer valid_from withholding | engine/market_ontology/mining_theme_research.py:213-250 |
| J24 event ledger | NO — first_seen/seendate only; no effective/available | engine/news_event_ledger.py:75-88; B1:99 |
| J25 annotate_row | NO | engine/qbus_news_annotate.py:32-70 |

**DATED counts: YES = 11 rows (J09, J10, J11, J12, J13, J16, J17, J18, J19, J21, J23), of which 9 are joining rows (J12/J13 are census/descriptive planes); NO = 8 (J02, J04, J05, J06, J14, J15, J24, J25); PARTIAL = 5 (J01, J03, J07, J08, J22); n/a = 1 (J20).**
Of the YES joins, NONE takes a news object as input.

## Explicit-null audit

Return explicit nulls / typed absences on ambiguity:

- J03 `state: unavailable, reason: no_accessible_sources`, all-null fields (engine/qbus_news_store.py:1999-2015).
- J04 `state: restricted` + empty stories (engine/qbus_news_context.py:39-40).
- J08 `NoLink{reason}` enum + identity_unavailable projection (engine/transmission_company_continuation.py:12-15, :334-336).
- J09 ambiguous aliases named and excluded from bindings (engine/qbus_news_universe.py:190-202).
- J10 `AMBIGUOUS`/`NOT_IN_MASTER`/… null ids + `refusal_reason` + candidate receipts (engine/theme_graph/identity_resolution.py:507-530).
- J16 unmapped basket → coverage `status` + warning; never guessed (engine/company_theme_exposure/views.py:200-214, :265-267).
- J17 `SUBJECT_NOT_FOUND` / `ENDPOINT_UNAVAILABLE` / `UNSUPPORTED_SUBJECT` / `RELATION_ABSENT` (engine/theme_graph/ontology.py:701-710, :787-810).
- J18 typed abstentions for unknown shock, unknown rights family, unresolved identity, future/unknown belief — "never raises for a data-availability reason" (engine/market_ontology/exposure_map.py:22-24).
- J19 unknown family refused outright; rights refusal cannot be rewritten as a data fact (engine/theme_graph/identity.py:174-176; engine/market_ontology/exposure_map.py:622-629).
- J21 typed `ActivityAdmissionRefusal` codes; hints explicitly not admission (engine/theme_graph/membership_evidence.py:1330-1336).
- J23 `omitted:period_before_issuer_validity`; `missing_issuer` blocks rather than invents (engine/market_ontology/mining_theme_research.py:250, :699-702).
- J25 unmatched headline → `event_type: null` inside a typed annotation (engine/qbus_news_annotate.py:52-55).

Drop silently:

- J01 unmatched provider ticker simply not indexed; no per-item record that a ticker failed to bind (collectors/benzinga_news.py:369-372).
- J14 off-narrative headline dropped from the narrative bus (engine/news_vector.py:154, :204-205) — and upstream of J15's per-basket leg.
- J24 keep-FIRST drops later rows/corrections with no supersede field (B1:100, F3-d1).
- J05 entities below the 0.75 confidence floor that `match_entities` also misses are absent with no record (engine/financial_news.py:117-127).

Guess (heuristic binding, not typed absence):

- J05 text entity resolution with a confidence floor + fallback scan (engine/financial_news.py:112-127).
- J07 shingled-title fallback branch of the echo join (engine/news_events.py:703-709; B1 G01).
- J16 `mapping_qualifier` derived from crosswalk note text (direct/proxy/curated) — labelled methodology, fail-closed coverage elsewhere (engine/company_theme_exposure/views.py:165-167, :172-174).
- J15 the static basket→bucket map is a curated coarse linkage, honest about absent baskets (engine/news_flow.py:30-31).
- J14 first-keyword-wins with a fixed taxonomy order (engine/news_vector.py:66-68, :156-159).

## Gaps for C1

Each gap is an evidence gap named against the rows it extends. No implementation is
proposed here.

- **GAP-1 (no dated news→theme join exists).** Every join that takes a news object to a theme (J14, J15) is keyword/static and aggregates on build-day windows; every join that is genuinely dated (J16, J17, J18, J19, J21) takes no news input. No row supplies "news event → theme exposure with a valid interval and knowledge cutoff distinct from seen/received" (MASTERPLAN.md:236, :243, :247).
- **GAP-2 (the dated exposure composer is unwired and its news seam is absent).** J18 (`compose_exposure_map`) has zero production callers (grep: `engine/market_ontology/__init__.py:14-16` + tests only), and its shock→theme link is caller-supplied by design (:18-21). No existing code derives a ShockSpec or `theme_node_ids` from any news object; nothing records what would count as evidence for that derivation.
- **GAP-3 (news aggregates never carry issuer identity).** The consumer chain J05→J06 keys on upper-cased ticker text end to end (engine/intelligence.py:241-245; B1 G08, B1:254); ticker→issuer resolution exists (J09, J10) but is not invoked on any news artifact, so no dated issuer identity or its resolution state travels with a news-derived company exposure (MASTERPLAN.md:245 "Ticker text is a display label").
- **GAP-4 (ingest routing leaves no ambiguity record).** J01 drops unmatched provider tickers silently and J09 holds the whole universe on any ambiguous alias; neither writes a per-item typed null saying "this ticker did not bind" (collectors/benzinga_news.py:369-372; engine/qbus_news_universe.py:190-203). The set of provider tickers that failed to bind is therefore not reconstructable from any store.
- **GAP-5 (qbus reads cannot reconstruct a historical as-of).** J02/J03/J04 read current state with no knowledge cutoff; a `now` in the past would be answered from today's state, contrary to the §5.2 rule that reconstruction requires evidence actually available then (engine/qbus_news_store.py:1926-1928, :2017; MASTERPLAN.md:243).
- **GAP-6 (no product exposure target exists at all).** J20: `product_id` exists only as a rights-receipt billing field (engine/qbus_news_receipts.py:43, :137) and Stripe features; the single product-scoped structure (J21 `scope.product`, membership_evidence.py:1401-1405) is disclosure evidence with `segment: UNDISCLOSED`. There is no product vocabulary for a news object to join to.
- **GAP-7 (subtheme plane is rights-gated and news-unreachable).** J19: vendor subthemes (`ltheme:`) meet canonical themes only through curated EXPRESSES edges with per-family rights gates; no news-side join emits or consumes an `ltheme:` id (engine/theme_graph/identity.py:168-176; engine/market_ontology/exposure_map.py:630-652).
- **GAP-8 (the GMI/CTE owner joins consume no news).** J16's inputs are membership + crosswalk + company-intelligence context; J21/J22 consume native disclosure facts; J23 consumes mining research packets. None reads F1–F7 news objects, so "existing GMI/identity/CTE joins" (MASTERPLAN.md:356) currently join companies to themes without any news event on the from-side.
- **GAP-9 (corrections do not propagate through theme joins).** J24 is keep-first with no supersede (B1:100); J16's theme_state receipt surfaces staleness of the theme plane, not news corrections; J18 handles edge belief revision but has no news input to revise. A corrected or withdrawn news item's exposure implications have no propagation path on any row (MASTERPLAN.md:261, :263).
- **GAP-10 (rights travel on some legs and vanish on others).** Rights are enforced on J02–J04 reads and stamped on J17/J18/J19/J21, but the widest-distribution news artifacts (J05, J06) carry disclaimer-level only, and derived stores drop them (B1 G09, B1:255; A1 §3 gap 6, A1:179). A dated exposure built from those artifacts could not inherit a rights field from any existing row.

## What this census is not

- No design: this document invents no join, store, mapping table, schema, key, clock or precedence rule, and proposes none.
- No ranking or sizing authority: nothing here orders the joins, scores them, or adjudicates which one C1 should use; the MASTERPLAN and the seat own that.
- No correctness claim about any exposure: recording a join's existence, keys and behaviour is not a claim that its output is economically right; J16's `mapping_qualifier` and authority ceilings (`context_only`, `research_display_only`) stay exactly as the owners wrote them.
- No new vocabulary: "subtheme" here means exactly the `ltheme:` planes the theme graph already defines (J19); "product" is reported absent (J20), not defined.
- No reading of data/, site/, credential files or other lanes; no Terminal/BFF code was read (A1 §4.2 records that boundary).

## Evidence

Commands run (in order; all at HEAD `fff8ab44c690f1c7e68fe3e4cc49fc92663917ee`, cwd = the lane worktree). Every cited line above was printed by one of the `sed -n`/Read calls listed here.

STEP 0 fences:
- `git rev-parse HEAD` → `fff8ab44c690f1c7e68fe3e4cc49fc92663917ee`
- `git status --porcelain` → empty
- `git branch --show-current` → `lane/news-w3-c1-census-r1`
- `W=~/lanes/tmp/news-w3-c1-census-r1; mkdir -p $W`
- `ls research/news_intelligence_estate_20261021/` → A1, A5, B1, D1, MASTERPLAN

Inputs (STEP 1):
- `wc -l` on MASTERPLAN/D1/B1/A1 (668/243/293/189)
- `grep -n "^#\|^##" MASTERPLAN.md`, `grep -n "^#\|^##" A1_SOURCE_DELIVERY_MATRIX.md` (outlines)
- Read MASTERPLAN.md:226-335 (§5.1–5.4, §6.2), 352-383 (§7.C–§7.E)
- Read D1_NEWS_INPUT_TRACE.md (all 243 lines)
- Read B1_SCHEMA_INVENTORY.md (all 293 lines)
- Read A1_SOURCE_DELIVERY_MATRIX.md:122-189 (§3 independence rules, §4 consumers, §5 gaps)

Existence (STEP 2): `test -f`/`test -d` loop over all 21 paths → EXISTS ×21 (3 directories), MISSING none; `wc -l` per file.

The census grep, per file (counts in Scope and method):
`grep -c -E "theme_id|subtheme|product_id|exposure|as_of|effective|seendate|received_at|rights" <file>` and the line form `grep -n -E … <file>` over: news_event_ledger, news_events, qbus_news_universe, qbus_news_context, qbus_news_annotate, ledger_identity, exposure_math, theme_catalyst_binder, transmission_company_continuation, theme_context, company_theme_exposure/*.py, theme_graph/{identity,identity_resolution,membership_evidence,native_disclosure_propagation,issuer_economic_context,ontology,rights,rights_use}.py, market_ontology/*.py, stock_identity/*.py.

Join-chain follow-ups (grep -n, then `sed -n`/Read of every cited range):
- `grep -n "def evidence_for_security\|def news_flow\|news_security_index\|subject_ids\|security_id" engine/qbus_news_store.py`; Read store:555-620, 1455-1520, 1751-1830, 1923-2042; `sed -n 288,299p`
- `grep -n "published_at\|received_at\|window\|24h\|7d\|28d" engine/qbus_news_velocity.py`; `sed -n 290,298p`
- `grep -rn "security_ids" engine/ scripts/ collectors/ app/`; `grep -n "security_ids\|alias\|RoutedRevision" collectors/benzinga_news.py engine/qbus_news_intake.py`; `sed -n 350,385p collectors/benzinga_news.py`; `sed -n 440,520p scripts/run_qbus_news.py`
- Read engine/qbus_news_universe.py (all); `grep -rn "qualify_universe"` (consumers); `grep -n "alias_bindings\|security_ids" engine/qbus_news_universe_snapshot.py`; `sed -n 280,340p`
- Read engine/qbus_news_context.py (all); Read engine/qbus_news_annotate.py (all)
- `grep -n "mapping_qualifier\|crosswalk\|def build\|membership" engine/company_theme_exposure/successor.py views.py contracts.py`; Read contracts.py:1-100, 198-207; Read views.py:96-290
- `grep -n "def \|RESOLUTION_STATES\|AMBIGUOUS\|resolution_asof" engine/theme_graph/identity_resolution.py`; `sed -n 60,110p`, `sed -n 485,530p`; head docstring
- `grep -n "def \|EVIDENCE\|MEMBERSHIP" engine/theme_graph/membership_evidence.py`; `sed -n 1186,1250p`, `sed -n 1319,1455p`
- Read native_disclosure_propagation.py (all); Read issuer_economic_context.py (all)
- `grep -n -E <pattern> engine/theme_graph/ontology.py`; `sed -n 240,300p`, `sed -n 700,821p`
- `sed -n 1,60p engine/market_ontology/exposure_map.py`; `sed -n 476,530p`; `sed -n 585,660p`; `sed -n 976,1080p`; `sed -n 50,56p`; `sed -n 1070,1078p`; `grep -rn "compose_exposure_map\|ShockSpec(" --include=*.py engine/ scripts/ app/ tests/`
- `sed -n 60,70p engine/market_ontology/ticker_cik_census.py`; `sed -n 1,30p mining_dependency_binding.py`; `sed -n 1,25p cohort_us_china.py bea_gvc_current.py`; `sed -n 213,253p mining_theme_research.py`
- `grep -n "belief_time\|valid_from\|valid_to\|MEMBER_OF\|EXPRESSES" engine/theme_graph/store.py`
- `grep -n "tickers\|theme" engine/financial_news.py engine/macro_news.py`; `sed -n 108,135p`, `sed -n 255,300p`, `sed -n 877,925p engine/financial_news.py`
- `grep -n "theme" engine/news_vector.py`; `sed -n 60,75p`, `sed -n 153,162p`; Read news_flow.py:28-50, 86-95
- Read news_events.py:620-724; Read news_event_ledger.py:70-109
- Read ledger_identity.py:1-80; Read theme_catalyst_binder.py:1-130, 280-360; Read transmission_company_continuation.py:1-40, 320-345; Read theme_context.py:1-30, 595-640
- `grep -rn "product_id" engine/ scripts/ app/ config/ contracts/`; `grep -rn "subtheme" engine/` (global absence checks for J20/J19)
- `sed -n 236,250p engine/intelligence.py`; `sed -n 285,291p engine/intelligence.py`

Test pinning: `grep -rln "<fn>" tests/` for evidence_for_security, news_flow, route_revision, qualify_universe, build_exposures/build_bundle, active_membership/crosswalk, resolve_graph_node_identity, build_activity_membership_evidence, bind_current_supplier, compose_exposure_map, compose_neighborhood, enrich_with_qbus, annotate_row, theme_flow, theme_catalyst, mastermind_by_ticker, match_entities, resolve_us, classify_theme, novelty_z, event_key_for_title, news_evidence_bundle, mining_theme_research/industrial_views (results in the table's "pinned by test" column).
