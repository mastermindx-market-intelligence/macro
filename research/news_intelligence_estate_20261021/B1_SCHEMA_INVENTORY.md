# B1 schema inventory — news object families
BASE: 64ef5131a5f50fb65f0ad25a049a457e18258495
RUN_ID: ne-b1-inventory-20261022-r1
MODEL: glm-5.3-flash
VERDICT: PASS

Census of identity, clock, correction, rights, writer, reader and cross-reference
fields of every existing news object family in macro at BASE. Vocabulary follows
MASTERPLAN.md §5 (six meanings; clocks published/received/available/effective/
materialised/cutoff; correction/independence rules) and §7 B1. Every table row
ends with at least one `path:line` that exists at BASE. Absent facts print
`ABSENT` with the grep used. All paths repo-relative; all line numbers at BASE.

Families inventoried:
- F1 source report / revision — engine/qbus_news_store.py + engine/qbus_news_contract.py
- F2 story group — engine/qbus_news_cluster.py (+ cluster tables in the store)
- F3 legacy event — engine/news_events.py + engine/news_event_ledger.py (+ legacy items store engine/qbus.py read by F3)
- F4 Chronicle — engine/chronicle/ (12 modules listed in §F4)
- F5 News Impact event / proposition / thesis — contracts/news_impact/*.schema.json + engine/news_impact core modules
- F6 quantitative observation — engine/news_impact/observation.py, engine/macro_surprise.py + six named value owners
- F7 consumer context — engine/intelligence.py + app/integrated_answer.py

---

## F1 — Source report / revision (qbus news store)

Owner: `engine/qbus_news_store.py` (sqlite store, 2,374 ln), `engine/qbus_news_contract.py`
(normalization contract, 496 ln). Intent doc: docs/ops/shared-news-intelligence.md.

| # | fact | fields / behaviour | evidence |
|---|------|--------------------|----------|
| F1-a1 | Revision record fields | `NewsRevision`: schema, source, source_item_id, transport, message_id, action, action_explicit, published_at, updated_at, source_event_at, received_at, version_at, version_clock_domain, title, url, teaser, provider_tickers, channels, tags, body_sha256, content_hash, revision_id, clock_anomalies | engine/qbus_news_contract.py:43-67 |
| F1-a2 | Source identity | `source_item_id` = the wire's own item id, validated non-empty token | engine/qbus_news_contract.py:100-108, engine/qbus_news_contract.py:301 |
| F1-a3 | revision_id format | sha256 of `source\|source_item_id\|(removed\|article)\|content_hash\|version_clock_domain\|version_at.isoformat()`, hex[:32] | engine/qbus_news_contract.py:196-207 |
| F1-a4 | content_hash format | sha256 over stable-json of {body_sha256, channels, tags, teaser, tickers, title, url} | engine/qbus_news_contract.py:178-194 |
| F1-b1 | immutable revision | `news_revisions` append-only, PK `revision_id`; INSERT at persist | engine/qbus_news_store.py:239-244, engine/qbus_news_store.py:1101 |
| F1-b2 | current pointer | `news_states` PK(source, source_item_id) holds `current_revision_id`, `status`, `last_sequence`, `universe_revision`; overwritten on commit | engine/qbus_news_store.py:261-271, engine/qbus_news_store.py:1175 |
| F1-b3 | delivery ledger | `news_deliveries` append-only, UNIQUE(revision_id, transport, message_id, received_at) | engine/qbus_news_store.py:250-259 |
| F1-b4 | materialised projection | `news_state_projection` denormalises current title/url/teaser/clocks per state; overwritten with the state | engine/qbus_news_store.py:273-286, engine/qbus_news_store.py:1142 |
| F1-c1 | published | `published_at` from wire `content.created`, aware UTC, required unless removed | engine/qbus_news_contract.py:314-317 |
| F1-c2 | received | `received_at` (required, aware UTC) from caller at normalize | engine/qbus_news_contract.py:284-290 |
| F1-c3 | effective (source event) | `source_event_at` from wire `data.timestamp`, required | engine/qbus_news_contract.py:300-303 |
| F1-c4 | version (revision time) | `version_at` = `updated_at or source_event_at`; `version_clock_domain` ∈ {benzinga_article_updated, benzinga_stream_event} | engine/qbus_news_contract.py:323-327 |
| F1-c5 | updated (publisher revision) | `updated_at` from wire `content.updated` | engine/qbus_news_contract.py:319-321 |
| F1-c6 | available | ABSENT — no availability clock column or field. grep: `git grep -in "available_at\|availability" -- engine/qbus_news_store.py engine/qbus_news_contract.py` → no match |
| F1-c7 | cutoff | ABSENT as a row clock; ingest position is carried by `news_cursors` (source_key→cursor) instead | engine/qbus_news_store.py:389-392 |
| F1-c8 | clock anomalies | `clock_anomalies` ∈ {updated_before_published, event_before_published} recorded on the revision | engine/qbus_news_contract.py:209-216, engine/qbus_news_contract.py:279 |
| F1-d1 | correction actions | `action` ∈ {created, updated, removed}; deleted/removed both normalize to `removed` | engine/qbus_news_contract.py:167-176 |
| F1-d2 | withdrawal propagation | reduce_revision dispositions include `withdrawn`; withdrawal removes/blankets the state projection and is counted per commit; syndication-member withdrawal does not project blank fields as a cluster update | engine/qbus_news_store.py:1640-1697, engine/qbus_news_store.py:1483-1484 |
| F1-d3 | restoration gate | `restoration_qualified` flag on RoutedRevision gates re-appearance of a removed item | engine/qbus_news_store.py:105-111, engine/qbus_news_store.py:597 |
| F1-e1 | rights fields | `SourceReadRights{source, allow_title, allow_url, allow_teaser}`; `NewsReadRights{allowed_sources, allow_title, allow_url, allow_teaser, source_fields}`; duplicate receipts may only narrow, never broaden | engine/qbus_news_store.py:113-141 |
| F1-e2 | rights enforcement | `_redact_story` applies field rights on read; `_curated_clause`/`_read_sources` filter by allowed sources | engine/qbus_news_store.py:645-671, engine/qbus_news_store.py:784-807 |
| F1-f1 | writer | `NewsStore.commit(revisions, expected_cursor, next_cursor)` — BEGIN IMMEDIATE, per-revision persist + reduce; cursor conflict aborts | engine/qbus_news_store.py:1562-1601 |
| F1-f2 | artifact | sqlite db, CLI default `data/qbus/qbus.sqlite3`; file chmod 0600 | scripts/run_qbus_news.py:473, engine/qbus_news_store.py:730-732 |
| F1-g1 | readers (8 of 13 shown) | app/ticker_news.py:50; engine/qbus_news_context.py:13; engine/qbus_news_receipts.py:22; scripts/verify_ticker_news.py:36; scripts/ticker_news_inventory.py:31; scripts/migrate_qbus_news.py:24; scripts/benchmark_qbus_news_retrieval.py:103; app/deploy/update.sh:2414 (deploy watchdog regex). +5 more (benchmarks/migrations) |
| F1-h1 | cross-ref to securities | `news_security_index(security_id, source, source_item_id)` maps wire items to internal security ids | engine/qbus_news_store.py:288-299 |
| F1-h2 | cross-ref to clusters | `news_cluster_members(source, source_item_id, cluster_id, story_id)` — every state row belongs to at most one F2 cluster | engine/qbus_news_store.py:314-323 |
| F1-h3 | provider tickers | `provider_tickers` tuple carried verbatim on the revision (display-grade, provider namespace) | engine/qbus_news_contract.py:61 |

## F2 — Story group (qbus news cluster)

Owner: `engine/qbus_news_cluster.py` (440 ln) + cluster tables in engine/qbus_news_store.py.

| # | fact | fields / behaviour | evidence |
|---|------|--------------------|----------|
| F2-a1 | member identity | `ClusterItem{source, source_item_id, title, observed_at, subject_ids, event_family, published_at}`; `story_id = f"{source}:{source_item_id}"` | engine/qbus_news_cluster.py:37-50 |
| F2-a2 | cluster identity | `cluster_id = "ev2_" + sha256(anchor story_id)[:16]` — derived from the anchor's source-assigned id, not from content | engine/qbus_news_cluster.py:216-218 |
| F2-a3 | policy stamp | `cluster_policy_version` = constant, or constant + every non-default field repr (provenance stamp recorded per cluster) | engine/qbus_news_cluster.py:64-85 |
| F2-b1 | anchor immutable | `news_clusters` row (anchor_story_id, anchor_title, anchor_observed_at) is immutable once minted; retrieval index is "pure optimization state for immutable anchors" | engine/qbus_news_store.py:301-309, engine/qbus_news_store.py:328-338 |
| F2-b2 | mutable part | `subject_ids_json` (retained subject union) is UPDATEd when a later member joins | engine/qbus_news_store.py:1330-1336 |
| F2-b3 | one-cluster-per-item | `news_cluster_members` PK(source, source_item_id) — a member belongs to exactly one cluster | engine/qbus_news_store.py:314-321 |
| F2-c1 | observed | `observed_at` on ClusterItem; anchored from the F1 state's `first_received_at` at cluster mint | engine/qbus_news_cluster.py:42, engine/qbus_news_store.py:1347-1354 |
| F2-c2 | published | `published_at` optional on ClusterItem/ClusterCandidate | engine/qbus_news_cluster.py:45, engine/qbus_news_cluster.py:61 |
| F2-c3 | window (grouping clock bound) | `ClusterPolicy.window_seconds` (default 6h) bounds candidate anchoring | engine/qbus_news_cluster.py:66-68, engine/qbus_news_cluster.py:390 |
| F2-c4 | available / effective / materialised / cutoff | ABSENT — grep: `git grep -in "available_at\|effective\|cutoff\|materialis" -- engine/qbus_news_cluster.py` → no match |
| F2-d1 | correction propagation | member withdrawal handled in F1 reduce; a withdrawn member's blank fields never project as the live cluster update (syndication guard) | engine/qbus_news_store.py:1483-1484, engine/qbus_news_store.py:1678-1697 |
| F2-d2 | index vs corrections | fingerprint/postings never rewritten on member corrections; rebuilt writer-only | engine/qbus_news_store.py:328-338, engine/qbus_news_store.py:1243 |
| F2-e1 | rights | ABSENT — grep: `git grep -in "rights\|licence\|license\|redistribut" -- engine/qbus_news_cluster.py` → no match (titles stored in the clear in `news_clusters.anchor_title`) |
| F2-f1 | writer | cluster mint/expand inside F1's state-commit transaction: INSERT news_clusters (store:1362) / INSERT news_cluster_members (store:1407) / UPDATE subject_ids_json (store:1330) | engine/qbus_news_store.py:1345-1411 |
| F2-g1 | readers (6 of 8 shown) | engine/qbus_news_retrieval.py:309,393,431,687; engine/qbus_news_velocity.py:59-83; +2 more in retrieval joins |
| F2-h1 | cross-ref to F1 | members keyed (source, source_item_id) = F1 news_states PK; `retrieval_json` evidence column | engine/qbus_news_store.py:314-321 |
| F2-h2 | cross-ref to securities | `subject_ids_json` holds internal security ids (expanded into the index on join) | engine/qbus_news_store.py:1330-1339 |

## F3 — Legacy event (keep-FIRST owners)

Owners: `engine/news_events.py` (classification + qbus enrichment), `engine/news_event_ledger.py`
(parquet keep-FIRST log), plus the legacy items store `engine/qbus.py` that F3 reads back.

| # | fact | fields / behaviour | evidence |
|---|------|--------------------|----------|
| F3-a1 | ledger columns | event_id, first_seen_utc, seendate, title, domain, source_tier, event_type, direction, centrality, tickers, theme, novelty_z | engine/news_event_ledger.py:76-89 |
| F3-a2 | event_id format | canonical: `qkernel.event_id(source="", url=domain, title=title)` (norm_title\|domain-host basis); fallback sha1(title\|domain)[:16] | engine/news_common.py:110-116, engine/news_event_ledger.py:272-288 |
| F3-a3 | legacy items identity | `item_id = qkernel.item_id(source, url, title, lang)` — content hash of source+url+title; keep-FIRST key of data/qbus/items.parquet | engine/qbus.py:61, engine/qbus.py:113-121, engine/qbus.py:12 |
| F3-a4 | story cluster id (legacy) | `event_key` = 16-char hash of the cluster REPRESENTATIVE (lowest source_tier, earliest _crawled_at, then item_id), assigned by shingled-title clustering | engine/qbus.py:176-186 |
| F3-b1 | immutable | keep-FIRST: existing row (incl. first_seen_utc) preserved, new row silently dropped | engine/news_event_ledger.py:9-12, engine/news_event_ledger.py:105-128 |
| F3-b2 | no current pointer | none — flat parquet, no state table | engine/news_event_ledger.py:76-89 |
| F3-c1 | received | `first_seen_utc` = persist-time now_iso, never overwritten | engine/news_event_ledger.py:164, engine/news_event_ledger.py:77 |
| F3-c2 | published | `seendate` = publisher date carried from the headline dict; legacy items also carry `seendate` + `timestamp_quality` and `_crawled_at` (local crawl time) | engine/news_event_ledger.py:82, engine/qbus.py:70-72 |
| F3-c3 | available / effective / materialised / cutoff | ABSENT — grep: `git grep -in "available_at\|effective_at\|cutoff\|materialis" -- engine/news_event_ledger.py engine/news_events.py` → no match |
| F3-d1 | correction / supersession | ABSENT — keep-FIRST drops later rows; no supersede/withdraw field exists. grep: `git grep -in "supersed\|withdraw\|correct" -- engine/news_event_ledger.py` → no match |
| F3-e1 | rights | ABSENT — only `source_tier` honest-label (stock_wire/tier1/quality/official); no licence/redistribution field. grep: `git grep -in "rights\|licence\|license\|redistribut" -- engine/news_event_ledger.py engine/news_events.py engine/qbus.py` → no match |
| F3-f1 | writer | `persist_kept_events` / `persist_reject_sample` — atomic parquet replace | engine/news_event_ledger.py:63-67, engine/news_event_ledger.py:105-128, engine/news_event_ledger.py:191-214 |
| F3-f2 | artifact | data/news/event_log.parquet; data/news/reject_sample.parquet | engine/news_event_ledger.py:13-14, engine/news_event_ledger.py:34-35 |
| F3-f3 | caller | scripts/build_news.py persists both after the keep/drop pass | scripts/build_news.py:395, scripts/build_news.py:414 |
| F3-g1 | readers (5 of 9 shown) | scripts/grade_news_events.py:3 (PIT event-log reader); engine/news_impact/thesis.py:190 (news_event_ledger input field); scripts/build_news.py:371-416 (writer); +6 more (feeds/brain tools) |
| F3-g2 | legacy qbus readers | engine/news_events.py:626-633 (qbus.read_items); engine/qbus.py:324,445,502,563 (echo_stats/novelty_z/event_key_for_title) |
| F3-h1 | cross-ref F3→legacy items | `enrich_with_qbus`: exact `item_id` join first (headline `_id`), else **shingled-title fallback** `event_key_for_title(title, asof)` keyed off the headline's own seendate day | engine/news_events.py:699-711 |
| F3-h2 | cross-ref fields out | `echo` {n_sources, n_desks} and `novelty_z` read back from the legacy store; `tickers` JSON list (display text) | engine/news_events.py:668-673, engine/news_event_ledger.py:85-87 |
| F3-h3 | classification payload | `event` = classify_event result (event_type, direction, numbers) attached display-only, never mutating keep/drop | engine/news_events.py:398-441, engine/news_events.py:645-652 |

## F4 — Chronicle

Owner: `engine/chronicle/` — 12 modules: adapters.py (548), context_pack.py (272),
earnings_calls.py (908), governor.py (245), impact.py (1309), manifest.py (126),
market_feed_alias.py (712), rollups.py (220), schema.py (188), spine.py (237),
state_log.py (293), __init__.py (32).

| # | fact | fields / behaviour | evidence |
|---|------|--------------------|----------|
| F4-a1 | event id | `id = "cev-<source>-<sha256(source\|source_ref\|date)[:12]>"` — deterministic idempotency key, full-regeneration stable | engine/chronicle/schema.py:45-53 |
| F4-a2 | event fields | id, ts, date, source, source_ref, kind, title, facts (digit-safe truncated), tickers, themes, horizon_hint, weight_hint, links{site, source, receipt} | engine/chronicle/schema.py:91-137, engine/chronicle/schema.py:56-57 |
| F4-a3 | kinds | KINDS = report, signal_close, print, earnings, state_flip; HORIZON_BY_KIND fixed map | engine/chronicle/schema.py:31-42 |
| F4-b1 | no revisions — regenerated | events.jsonl is fully recomputed every run and lands byte-identical (union keeps rows missing from a later snapshot) | engine/chronicle/spine.py:85-133, engine/chronicle/spine.py:144-165, engine/chronicle/spine.py:221-236 |
| F4-c1 | ts (published/effective blend) | `ts` = source `published_at` when it carries T, else `date T00:00:00Z` | engine/chronicle/adapters.py:103-114 |
| F4-c2 | date | event business date (published_at[:10], close_date, reported_date, release_date) | engine/chronicle/adapters.py:103-104, engine/chronicle/adapters.py:210, engine/chronicle/adapters.py:428-435 |
| F4-c3 | received / available / effective / materialised / cutoff | ABSENT — no per-event field. grep: `git grep -in "received_at\|available_at\|effective_at\|cutoff" -- engine/chronicle/schema.py engine/chronicle/adapters.py` → no match. Materialisation is stamped only on the store sidecar (manifest envelope + sha256/row counts) | engine/chronicle/manifest.py:1-12, engine/chronicle/manifest.py:30-40 |
| F4-d1 | retraction | `apply_authoritative_retractions` removes only `source == "prophet_ledger"` events whose source_ref is in the effective quarantine set; malformed correction receipts abort the build | engine/chronicle/spine.py:167-200 |
| F4-d2 | propagation | none outward: Chronicle is a derived view; the raw Prophet ledger and correction receipts retain the audit trail | engine/chronicle/spine.py:174-178 |
| F4-e1 | rights | ABSENT — grep: `git grep -in "rights\|licence\|license\|redistribut" -- engine/chronicle/` → no match (facts are truncated for third-party-derived content instead) | engine/chronicle/schema.py:64-89 |
| F4-f1 | writer | governor builds the store and atomically writes events.jsonl + rollups + manifest.json | engine/chronicle/governor.py:62-95, engine/chronicle/spine.py:221-236 |
| F4-f2 | artifact | data/chronicle/events.jsonl (+ rollups, manifest.json, state_log.jsonl, earnings_call_events.jsonl) | engine/chronicle/context_pack.py:43, engine/chronicle/earnings_calls.py:47 |
| F4-g1 | readers (6 of ~10 shown) | engine/chronicle/context_pack.py:43; scripts/build_theme_graph.py; scripts/build_site.py; scripts/run_press.py; scripts/build_research_pages.py; scripts/check_append_only_assertions.py; +4 more |
| F4-h1 | cross-ref: source_ref | research_vault → vault item_id (adapters.py:118); prophet_ledger → ledger row_id (adapters.py:209); macro_release → `<release>#<release_date>` (adapters.py:327); earnings → `<ticker>#<reported_date>` (adapters.py:428); risk_band → `risk_radar_forward_log#<date>` (adapters.py:510); earnings_call → `source_record_id` (earnings_calls.py:885) | engine/chronicle/adapters.py:118,209,327,428,510; engine/chronicle/earnings_calls.py:885 |
| F4-h2 | display identity | `tickers`/`themes` are plain text lists (display-grade, no security id join) | engine/chronicle/schema.py:124-127 |

## F5 — News Impact event / proposition / thesis

Owners: contracts/news_impact/*.schema.json (17 contract files) + engine/news_impact/
(validate.py, producer.py, producer_facts.py, thesis.py, cluster.py, issuer.py, …).

| # | fact | fields / behaviour | evidence |
|---|------|--------------------|----------|
| F5-a1 | fact identity | envelope `fact_id` pattern `^fact_[0-9a-f]{24}$`; minted `fact_ + sha256(case_id\|template)[:24]` | contracts/news_impact/fact_log.v1.schema.json:88 ($defs.fact_id), engine/news_impact/producer.py:269 |
| F5-a2 | log identity | `log_seq` integer sequence + `record_kind` per record; `fact_key` typed object | contracts/news_impact/fact_log.v1.schema.json:438, :441 ($defs.log_record required) |
| F5-a3 | source document | `document_id` (text_safe) + evidence `span_id`, `document_version`, `text_sha256` | contracts/news_impact/news_impact_event.v1.schema.json:326 ($defs.source_span_v1) |
| F5-a4 | company identity | `company_id` pattern `^cik:(?!0{10}$)[0-9]{10}$`; issuer resolution ladder explicit_cik → registry → ledger → absent (typed absence, never ticker-inferred) | contracts/news_impact/fact_log.v1.schema.json:82 ($defs.company_id), engine/news_impact/issuer.py:13-38, engine/news_impact/issuer.py:80 |
| F5-a5 | cluster ref | `cluster_id` pattern `^ev2_[0-9a-f]{16}$` — the F2 owner format; news_impact clustering consumes the owner's `new_cluster_id`, never mints its own | contracts/news_impact/fact_log.v1.schema.json:100 ($defs.cluster_id), engine/news_impact/cluster.py:16-33 |
| F5-b1 | immutable log | "Append-only fact log"; the mutable thesis is forbidden — the view is ONLY F(fact_log, owner_snapshot, as_of_utc) | engine/news_impact/thesis.py:1-14 |
| F5-b2 | artifact | DEFAULT_LOG_PATH data/news_impact/fact_log.jsonl (documentation-only default, never opened by the module); producer writes {name}.jsonl + {name}_report.json under its out dir | engine/news_impact/thesis.py:39, engine/news_impact/producer.py:336-355 |
| F5-c1 | observed | `observed_at` (RFC3339); producer sets `max(seendate, available)` | contracts/news_impact/news_impact_event.v1.schema.json:783 ($defs.envelope), :805 (observed_at), engine/news_impact/producer.py:258-271 |
| F5-c2 | available | `source_available_at`; producer stamps filing_date + T23:59:59Z (day-coarse) | contracts/news_impact/news_impact_event.v1.schema.json:783 ($defs.envelope), :812 (source_available_at), engine/news_impact/producer.py:264, :270 |
| F5-c3 | decision/as-of clocks (thesis) | thesis_view: `decision_cut`, `as_of_utc`, `deadline`, `next_expected_observation`; determinism rule: no clock reads, as_of_utc always a parameter | contracts/news_impact/thesis_view.v1.schema.json:8 (required), :54 (decision_cut), :55 (as_of_utc), :92 (next_expected_observation), :98 (deadline), engine/news_impact/thesis.py:13-14 |
| F5-c4 | received / effective / materialised / cutoff | ABSENT as named fields — grep: `git grep -in "received_at\|effective_at" -- contracts/news_impact/` → no match; arrival-side clock is folded into `observed_at`; window/cutoff arithmetic lives in F6 observation_window |
| F5-d1 | correction pointer | `supersedes_fact_id` (nullable, same fact_id pattern) on every event + log record; correction replay via supersedes_fact_id is freeze D16 | contracts/news_impact/news_impact_event.v1.schema.json:783 ($defs.envelope), engine/news_impact/thesis.py:8-9 |
| F5-d2 | producer-side revisions | producer_facts sorts candidates by observed_at, emits fact_revision records and the supersede decision (`decision.supersedes_fact_id`) | engine/news_impact/producer_facts.py:327-350, engine/news_impact/producer_facts.py:379-399 |
| F5-d3 | linked structure | `reports_fact_id`, `linked_fact_ids`, `owner_claim_ids` per record; `original_proposition_fact_id`, `supporting_claim_ids`, `contrary_claim_ids`, `live_fact_ids` on thesis_view | contracts/news_impact/fact_log.v1.schema.json:500-510 ($defs.log_record: owner_claim_ids, reports_fact_id, linked_fact_ids), contracts/news_impact/thesis_view.v1.schema.json:53-62 (original_proposition_fact_id, supporting_claim_ids, contrary_claim_ids), :110 (live_fact_ids) |
| F5-d4 | negation/withdrawal | `negated` boolean on event templates; quarantine_note.v1 def; label lifecycle `weakening_conditions` on thesis_view | contracts/news_impact/news_impact_event.v1.schema.json:1134 (capital_allocation_event properties), :1246 (negated), :2313 (quarantine_note.v1), contracts/news_impact/thesis_view.v1.schema.json:104 (weakening_conditions) |
| F5-e1 | rights | evidence-span rights: source_span_v1 requires `rights_profile`, `display_excerpt`, `receipt_state`, `receipt`, `unreplayable_reason` | contracts/news_impact/news_impact_event.v1.schema.json:326, :329 ($defs.source_span_v1 required) |
| F5-f1 | writer | producer.run(bundles, labels, out) writes out/{name}.jsonl (one event per line) + {name}_report.json; source bytes verified against bundle source_sha256 before emit | engine/news_impact/producer.py:336-355, engine/news_impact/producer.py:278-281 |
| F5-g1 | readers (7 of ~15 shown) | research/prophet_v4/news_to_business_impact_20261006/benchmark/results_w2/tools/score_benchmark.py:38-39; research/prophet_v4/news_to_business_impact_20261006/benchmark/results_w2/tools/check_label.py:15; research/prophet_v4/news_to_business_impact_20261006/benchmark/results_w2/tools/compare_gates_paired.py:39-40; research/prophet_v4/news_to_business_impact_20261006/benchmark/results_w2/tools/build_routing_check.py:30; research/prophet_v4/news_to_business_impact_20261006/benchmark/results_w2/tools/canon_returns.py:35; tests/test_news_impact_observation.py; +8 more research/CI tools |
| F5-h1 | cross-ref to F2 | `cluster_id` ev2_ format; cluster.py reuses qbus owner clustering (`new_cluster_id`) | contracts/news_impact/fact_log.v1.schema.json:100 ($defs.cluster_id), engine/news_impact/cluster.py:289-322 |
| F5-h2 | cross-ref to company events | `ci_event_id` oneOf: {form: company_event.v1, event_id `^evt_cik[0-9]{10}_[0-9]{4}(q[1-4]\|fy)_[a-z0-9]+$`} or typed absence | contracts/news_impact/fact_log.v1.schema.json:249 ($defs.ci_event_ref) |
| F5-h3 | cross-ref to F6/filing | `document_id` + source_span locators bind to the EDGAR filing document; driver_bridge/channel_mapping both carry fact_id + company_id; channel_mapping adds `inherits_from_fact_id` | contracts/news_impact/driver_bridge.v1.schema.json:11-12, :26, :32 (fact_id, company_id), contracts/news_impact/channel_mapping.v1.schema.json:12-13, :40, :46, :347 (fact_id, company_id, inherits_from_fact_id), contracts/news_impact/news_impact_event.v1.schema.json:326 ($defs.source_span_v1) |
| F5-h4 | benchmark-side refs | label_return{case_id, labeler_family, model_vintage, prompt_version, template}; adjudication_record{case_id, template, field, values, ruling, resolved_value, adjudicator}; sample_manifest{tape_sha256, cases_sha256, manifest_sha256, seed} | contracts/news_impact/label_return.v1.schema.json:10-14 (case_id, labeler_family, model_vintage, prompt_version, template), contracts/news_impact/adjudication_record.v1.schema.json:10-17 (case_id, template, field, values, ruling, resolved_value, adjudicator), contracts/news_impact/sample_manifest.v1.schema.json:744-756 (tape_sha256, cases_sha256, manifest_sha256, seed) |

## F6 — Quantitative observation

Core: engine/news_impact/observation.py (window/cutoff arithmetic), engine/macro_surprise.py
(FRED surprise). Six value owners named below (each holds a numeric value with unit/period):
1. engine/earnings_release/figures.py — earnings release figures (GAAP/adjusted basis owner)
2. engine/release_actuals.py — official macro-release actual receipts (Release Radar)
3. engine/macro_surprise.py — FRED series surprise statistics
4. engine/k3e_expectation_surface.py — consensus expectation observations (K3E)
5. engine/news_impact/observation.py — observation-window geometry (cutoff owner; no values)
6. engine/company_intelligence/events.py (+ event_id_adapter.py) — canonical company event ids that F5 ci_event_id points at

| # | fact | fields / behaviour | evidence |
|---|------|--------------------|----------|
| F6-a1 | value (earnings) | `ReleaseFigure{concept, label, value, basis, units, currency, period_label, period_end, receipt, scale_factor}`; doctrine: "a number without basis, units, period, and source is" not admissible | engine/earnings_release/figures.py:240-263, engine/earnings_release/figures.py:6 |
| F6-a2 | basis | Basis enum GAAP\|NON_GAAP; absences distinguish basis_undeclared from concept_not_present | engine/earnings_release/figures.py:52-55, engine/earnings_release/figures.py:63-73 |
| F6-a3 | identity (release_actuals) | receipt_id = `official_actual: + sha256(canonical identity)[:24]`; identity = {release, period, sequence:"first", metric_id, value, source_sha256} | engine/release_actuals.py:320-332, engine/release_actuals.py:437-444 |
| F6-a4 | identity (expectations) | `observation_id` + observation_type over ESTIMATE_TYPES {average, median, high, low, growth, year_ago}; record classes earnings_estimate / revenue_estimate | engine/k3e_expectation_surface.py:22-23, engine/k3e_expectation_surface.py:29-35 |
| F6-a5 | identity (company event) | canonical `evt_cik##########_YYYY(q[1-4]\|fy)_<slug>` — issuer-keyed, deliberately readable, correction-stable; FiscalPeriod typed | engine/company_intelligence/events.py:147-201 |
| F6-b1 | revision/vintage | release_actuals pins `sequence: "first"` + `exact_target_id = metric_id + "_printed_first"` and refuses derived prints ("derives a CPI… by differencing unrelated vintages" is the defect); k3e carries `correction_state` + `supersedes_observation_id`; macro_surprise has NO vintage — FRED serves latest-revised only | engine/release_actuals.py:440-451, engine/release_actuals.py:1-9, engine/k3e_expectation_surface.py:31-32, engine/macro_surprise.py:8-12 |
| F6-c1 | published/available (expectations) | `source_published_at`, `source_effective_at`, `provider_observed_at`, `system_observed_at`, plus `expectation_state`/`expectation_state_as_of` (CURRENT/stale state machine) | engine/k3e_expectation_surface.py:32-35, engine/k3e_expectation_surface.py:495-551 |
| F6-c2 | published (actuals) | `source_released_at`, `observed_at`, `verified_at`, `release_date` | engine/release_actuals.py:461-470 |
| F6-c3 | cutoff (windows) | observation_window.v1: T0 anchors, information cutoff inclusive, 16:00 America/New_York session stamps, matched windows counted in trading sessions | engine/news_impact/observation.py:1-45, engine/news_impact/observation.py:272-288, engine/news_impact/observation.py:440-522 |
| F6-c4 | period (as-of envelope) | macro_surprise: `asof` filter keeps records with `date <= asof_date`; period = FRED observation date; cadence map monthly/weekly/quarterly | engine/macro_surprise.py:449-455, engine/macro_surprise.py:498-503 |
| F6-d1 | value fields (macro) | latest_val, prior_val, delta_vs_prior, delta_vs_3m/6m, z3y, z5y, surprise_size {inline, notable, large}; prior is the REVISED prior (labelled honestly "vs revised prior") | engine/macro_surprise.py:487-530, engine/macro_surprise.py:9-12 |
| F6-d2 | unit/scale/currency | figures: `units`, `currency` (nullable, currency_undeclared absence), `scale_factor`; release_actuals: `unit`, `actual_raw` vs scaled `actual`, `published_precision`; expectations: `unit`, `currency`, `basis` columns | engine/earnings_release/figures.py:247-253, engine/release_actuals.py:451-455, engine/k3e_expectation_surface.py:34 |
| F6-e1 | rights | expectations carry `rights_class` with BLOCKED_RIGHTS {RIGHTS_BLOCKED, UNLICENSED, PROHIBITED, BLOCKED} and DISPLAY_ONLY_RIGHTS {DISPLAY_ONLY}; other F6 owners: ABSENT — grep: `git grep -in "rights" -- engine/release_actuals.py engine/macro_surprise.py engine/earnings_release/` → no match | engine/k3e_expectation_surface.py:24-25 |
| F6-f1 | writers | release_actuals → official-actual receipt rows + defect sidecar `official_actual_defects.json`; macro_surprise cache → data/macro/fred_surprise_cache/<series_id>.json (12h TTL); expectations parquet at data/revisions/expectation_observations.parquet (+ attempts) | engine/release_actuals.py:121-128, engine/macro_surprise.py:285-295, engine/k3e_expectation_surface.py:17-18 |
| F6-g1 | readers | observation geometry: only tests + research at BASE (tests/test_news_impact_observation.py; research/prophet_v4/news_to_business_impact_20261006/phase1_designs/AMENDMENTS_W1C.md); macro_surprise consumed by the macro news pipeline; release_actuals by Release Radar owners; expectations by k3e surfaces + app/integrated_answer.py:307 | engine/news_impact/observation.py (grep `compute_window_geometry` → 3 files), app/integrated_answer.py:332 |
| F6-h1 | cross-ref | release_actuals `exact_target_id` → MRI release targets (`<metric_id>_printed_first`); k3e `issuer_ref`/`security_ref` → identity owners; company event ids are the target of F5 `ci_event_id`; observation_window subjects carry cik: identity untouched | engine/release_actuals.py:448, engine/k3e_expectation_surface.py:34, contracts/news_impact/fact_log.v1.schema.json:249 ($defs.ci_event_ref), engine/news_impact/observation.py:6-8 |

## F7 — Consumer context

Owners: engine/intelligence.py (per-ticker bundle, SCHEMA intelligence.by_ticker.v2),
app/integrated_answer.py (receipted answer legs).

| # | fact | fields / behaviour | evidence |
|---|------|--------------------|----------|
| F7-a1 | row identity | bundle rows keyed by ticker TEXT upper-cased: `t = (ticker).upper()`; row = {ticker, news, alt, radar, standout, has_* , read, brain, note} | engine/intelligence.py:240-248 |
| F7-a2 | answer identity | leg refs {route, as_of, generation_id, owner_hash, content_hash}; content_hash = sha256 of canonical json; consumed_receipt + null_reasons with closed reason set | app/integrated_answer.py:193-239, app/integrated_answer.py:204-216 |
| F7-b1 | bundle rebuild | bundle is recomputed each build from published artifacts; no revisions, no persistence of its own beyond the site artifact | engine/intelligence.py:225-270, engine/intelligence.py:283-291 |
| F7-c1 | as_of (decision cutoff) | bundle `as_of` = date only (`today.isoformat()`), plus `generated_utc`; site consumers also read `asof` on news/by_ticker.json ('asof', no underscore) | engine/intelligence.py:261-263, engine/signal_sanity.py:168 |
| F7-c2 | answer as-of | per-leg `as_of` = max(provenance.recorded_at) else max(accepted_at) else request clock; request echoes recorded_cutoff_at/source_snapshot_at, never reads them | app/integrated_answer.py:425-434, app/integrated_answer.py:435-438 |
| F7-d1 | corrections | none of its own; correction state is whatever the upstream artifact carried at read time. grep: `git grep -in "supersed\|correct" -- engine/intelligence.py` → no match |
| F7-e1 | rights | disclaimer-level only ("Context only…"); no licence field. grep: `git grep -in "rights\|licen[cs]" -- engine/intelligence.py` → no match | engine/intelligence.py:33-36 |
| F7-f1 | writer | scripts/build_intelligence.py: build() → site/intelligence/by_ticker.json (+ radar_news) | scripts/build_intelligence.py:66-77 |
| F7-f2 | answer writer | integrated answer composes legs in-process (receipts returned to caller; no news store written) | app/integrated_answer.py:370-445 |
| F7-g1 | readers (6 shown) | engine/briefing.py:233-238; scripts/build_briefing.py:28; engine/neuralweb/contradictions.py:574; engine/signal_sanity.py:168; scripts/build_stock_library.py:3871; engine/china_intel_hub.py:138-140 (chinanews variant) |
| F7-h1 | cross-refs in | inputs are five published artifacts: site/news/by_ticker.json, site/altdata/mastermind.json, site/altdata/by_ticker.json, site/basketdata/radar_ticker.json, site/factordata/us_standouts.json — all joined on ticker text | engine/intelligence.py:230-235, engine/intelligence.py:283-290 |
| F7-h2 | cross-refs out (answer) | legs reference k3e expectation surface, company event result, theme context, forensics query route + owner_hash/response_sha256 | app/integrated_answer.py:307, app/integrated_answer.py:346-360, app/integrated_answer.py:439-445 |

---

## Answers

**Q1 — identity key per family; content-addressed, source-assigned, or sequence?**
F1: revision_id is content-addressed over (source, source_item_id, content_hash, clock domain, version_at) [F1-a3]; the (source, source_item_id) pair is source-assigned [F1-a2]. F2: story_id = source-assigned pair; cluster_id is derived from the anchor's source-assigned id via sha256[:16] — not content of the story text [F2-a1, F2-a2]. F3: event_id = content hash of (norm_title, domain) [F3-a2]; legacy item_id = content hash of (source, url, title) [F3-a3]; event_key = hash of the cluster representative [F3-a4]. F4: cev-<source>-<sha256(source|source_ref|date)[:12]> — content-addressed over source pointer + date [F4-a1]. F5: fact_id = content hash of (case_id, template) [F5-a1]; log_seq is the only sequence field [F5-a2]. F6: release receipts content-addressed over {release, period, sequence, metric_id, value, source_sha256} [F6-a3]; observation_id in expectations [F6-a4]; evt_cik canonical ids are issuer+period-assigned, deliberately not hashed [F6-a5]. F7: ticker text for bundles [F7-a1]; route+content_hash for answer refs [F7-a2].

**Q2 — immutable revisions vs current pointers?**
Immutable append-only: F1 news_revisions + news_deliveries [F1-b1, F1-b3]; F5 fact log [F5-b1]; F3 ledger rows are immutable once written but nothing newer is kept — keep-FIRST drops corrections entirely [F3-b1]. Current pointer: F1 news_states.current_revision_id [F1-b2] with an overwritten projection [F1-b4]. Regenerated-in-place (no revision history): F2 subject union [F2-b2], F4 events.jsonl (byte-stable full recompute) [F4-b1], F6 caches/parquet current rows [F6-f1], F7 bundle [F7-b1]. Immutable anchors exist inside F2 (anchor columns) while its subject union mutates [F2-b1, F2-b2].

**Q3 — which of the six clocks does each family carry, and where do two families name one clock differently?**
published: F1 published_at [F1-c1]; F2 published_at (optional) [F2-c2]; F3 seendate [F3-c2]; F4 ts/date [F4-c1, F4-c2]; F5 none (day-coarse source_available_at stands in) [F5-c2]; F6 source_published_at [F6-c1], source_released_at [F6-c2]. received: F1 received_at [F1-c2]; F3 first_seen_utc [F3-c1]; F2 observed_at (= F1 first_received_at) [F2-c1]; F5 folds receipt into observed_at [F5-c4]; F6 provider_observed_at/system_observed_at split it in two [F6-c1]. available: F5 source_available_at [F5-c2]; F6 source_effective_at [F6-c1]; F1/F2/F3/F4 ABSENT [F1-c6, F2-c4, F3-c3, F4-c3]. effective: F1 source_event_at [F1-c3]; F6 source_effective_at [F6-c1]; others ABSENT or blended into ts/date [F4-c1]. materialised: no family carries a per-row field (F1 projection table and F4 manifest sidecar are the closest artefacts) [F1-b4, F4-c3]. cutoff: F6 observation_window cutoff [F6-c3]; F7 as_of [F7-c1, F7-c2]; F1 uses cursors, not a row clock [F1-c7]. Same-clock/different-name collisions: received ≡ observed_at (F2) ≡ first_seen_utc (F3) ≡ observed_at (F5, mixed with availability); available ≡ source_available_at (F5) ≡ source_effective_at (F6); published ≡ seendate (F3) ≡ ts (F4).

**Q4 — how are correction/withdrawal represented, and does any family consume another family's correction?**
F1: action=removed + withdrawn dispositions + restoration gate [F1-d1, F1-d2, F1-d3]. F2 consumes F1's withdrawal (syndication guard prevents blank projection; index never rewritten on corrections) [F2-d1, F2-d2]. F5: supersedes_fact_id chain + negated flag + quarantine receipts [F5-d1, F5-d2, F5-d4]. F4 consumes Prophet quarantine receipts (the one cross-family correction consumption) [F4-d1, F4-d2]. F3: none — later rows silently dropped [F3-d1]. F6: k3e correction_state + supersedes_observation_id [F6-b1]; release_actuals pins "first" sequence against later revisions [F6-b1]. F7: none [F7-d1].

**Q5 — where are rights fields, and which family drops them when it derives from another?**
Rights exist in: F1 per-source per-field read rights (title/url/teaser) [F1-e1, F1-e2]; F5 evidence-span rights_profile/display_excerpt/receipt_state [F5-e1]; F6 k3e rights_class with BLOCKED/DISPLAY_ONLY classes [F6-e1]. Dropped on derivation: F2 stores anchor_title in the clear with no rights carry [F2-e1]; F3 persists title text with only a source_tier label [F3-e1]; F4 facts/truncation but no rights field [F4-e1]; F7 republishes news bundles with disclaimer only [F7-e1].

**Q6 — which cross-family references already exist, and which joins rely on ticker/headline/time heuristics?**
Existing id-based refs: F1↔F2 via (source, source_item_id) and cluster members [F2-h1]; F5→F2 via ev2_ cluster_id (owner-minted) [F5-h1]; F5→F6/company events via ci_event_id evt_cik… [F5-h2]; F5→filings via document_id + spans [F5-h3]; F4→owners via source_ref pointers [F4-h1]; F6→MRI targets via exact_target_id [F6-h1]; F3→legacy qbus via item_id exact join (when `_id` present) [F3-h1]; F7→owners via owner_hash/route refs in answer legs [F7-h2]. Heuristic joins: F3→legacy items falls back to shingled-title + asof-day match `event_key_for_title(title, asof)` [F3-h1]; all of F7 joins five artifacts on upper-cased ticker text [F7-a1, F7-h1]; F4 earnings events embed `<ticker>#<date>` composite in source_ref [F4-h1]; chronicle tickers[] and F3 tickers are display text with no id join [F4-h2, F3-h2].

**Q7 — same name/different meaning, or different keys/same object?**
"observed_at": F2 (cluster observation time = first receipt) [F2-c1] vs F5 (max of seen/available arrival stamp) [F5-c1] vs F6 provider_observed_at/system_observed_at [F6-c1]. "cluster": F2 cluster_id ev2_ (anchor-derived) [F2-a2] vs F3 event_key (representative-derived, same 16-hex shape, different namespace and store) [F3-a4] vs F5 cluster_id (deliberately the F2 one) [F5-a5]. "event": F3 event_id (title|domain hash) [F3-a2] vs F5 ci_event_id evt_cik… [F5-h2] vs F4 id cev-… [F4-a1]. Company event keyed three ways: evt_cik canonical / cie_ 24-hex / TICKER-YYYYQn transcript key, resolved by an alias adapter [F6-a5, engine/company_intelligence/event_id_adapter.py:30-56]. "prior": macro_surprise prior = revised prior [F6-d1] vs release_actuals sequence:"first" first-print baseline [F6-b1]. "as_of": date-granular in F7 bundle [F7-c1] vs instant-granular in answer legs [F7-c2] vs as_of_utc parameter in thesis_view [F5-c3]. Identity of a security: provider_tickers [F1-h3] vs security_id [F1-h1] vs subject_ids [F2-h2] vs ticker text [F7-a1] vs cik: [F5-a4] vs issuer_ref [F6-h1].

---

## Collision and gap table

| id | kind | families | field/concept | evidence (path:line on each side) | minimal join (existing fields only) |
|----|------|----------|---------------|-----------------------------------|-------------------------------------|
| G01 | GAP | F3→legacy qbus | report→story join falls back to shingled-title + asof-day heuristic when `_id` is absent | engine/news_events.py:699-705 vs engine/news_events.py:706-711 | Always stamp the headline's existing `_id` with the qbus `item_id` at ingest so the exact-join branch (df["item_id"] == item_id) is the only path needed. |
| G02 | GAP | F1, F3, F4 | correction/withdrawal not represented in the legacy event log at all (keep-FIRST silently drops) | engine/qbus_news_store.py:1640-1697 vs engine/news_event_ledger.py:11-12 | Impossible with existing fields only: event_log.parquet has no supersede column; the single existing owner that would carry it is engine/news_event_ledger.py's `_EVENT_LOG_COLS` (a new row kind or column in that owner). |
| G03 | COLLISION | F2 vs F3 | two "one story" cluster keys with the same 16-hex shape: ev2_ anchor-hash vs event_key representative-hash | engine/qbus_news_cluster.py:216-218 vs engine/qbus.py:176-186 | Join through the member rows both sides already carry: qbus.py items carry `item_id`, F2 members carry (source, source_item_id) — match on the item identity, never on the two hash namespaces. |
| G04 | COLLISION | F2, F5, F6 | `observed_at` means cluster-receipt time (F2), arrival stamp max(seen, available) (F5), and provider/system split (F6) | engine/qbus_news_cluster.py:42 vs engine/news_impact/producer.py:258-271 vs engine/k3e_expectation_surface.py:32-33 | At each read, pair observed_at with its family's own companion clock (F1 first_received_at basis, F5 source_available_at, F6 source_effective_at) instead of comparing observed_at across families. |
| G05 | COLLISION | F5, F6 (company events) | same company event under three keys: evt_cik canonical, cie_ 24-hex, TICKER/YYYYQn narrative key | engine/company_intelligence/events.py:182-201 vs engine/company_intelligence/event_id_adapter.py:30-56 vs engine/company_intelligence/event_id_adapter.py:37-45 | Route every consumer through the existing alias adapter (canonical_event_id/parse_canonical_event_id) so only the evt_cik canonical form crosses family boundaries. |
| G06 | COLLISION | F3, F4, F5 | the word "event_id"/"id" names three formats: title-hash, cev- hash, fact/evt ids | engine/news_event_ledger.py:272-288 vs engine/chronicle/schema.py:45-53 vs contracts/news_impact/fact_log.v1.schema.json:88 ($defs.fact_id) | When joining, always qualify by the owner format prefix (cev- / fact_ / evt_cik / ev2_) before comparing ids; no new field needed, only disciplined use of the existing `schema`/`source` columns each row already carries. |
| G07 | COLLISION | F1, F2, F5, F6, F7, k3e | one issuer, five identity formats: provider_tickers, security_id, ticker text, cik:, issuer_ref | engine/qbus_news_contract.py:61 vs engine/qbus_news_store.py:288-299 vs engine/intelligence.py:240-243 vs contracts/news_impact/fact_log.v1.schema.json:82 ($defs.company_id) vs engine/k3e_expectation_surface.py:34 | Resolve ticker text → cik at read time through the existing ledger ticker_cik_ledger.json + issuer ladder (engine/news_impact/issuer.py:25-28, :107); keep each family's native field in place. |
| G08 | GAP | F7 | the consumer bundle joins five upstream artifacts on upper-cased ticker text with no issuer id or as-of narrowing beyond a date | engine/intelligence.py:240-243 vs engine/intelligence.py:261-263 | Enrich each bundle row with the cik resolved by the existing issuer ladder/ledger at build time (issuer.py rungs), and carry the per-artifact `asof`/`generated_utc` already present in the inputs. |
| G09 | GAP | F1, F2, F3, F4 | derived families drop rights: cluster anchor_title, event_log title, chronicle facts carry no rights field while F1 enforces per-source field rights | engine/qbus_news_store.py:113-141 vs engine/qbus_news_store.py:301-309 vs engine/news_event_ledger.py:76-89 vs engine/chronicle/schema.py:91-137 | Derivatives read source text only through the existing rights owner (NewsReadRights/_redact_story path, engine/qbus_news_store.py:645-671; receipts module engine/qbus_news_receipts.py:22) so the stamp travels with the read, not with the copy. |
| G10 | COLLISION | F6 | "prior" names two different baselines: revised prior (macro_surprise) vs first-print (release_actuals) | engine/macro_surprise.py:9-12 vs engine/release_actuals.py:440-451 | When both exist for the same release/period/metric_id, take the baseline from release_actuals' `exact_target_id` first-print row and label the macro_surprise delta "vs revised prior" (its own existing honest label). |
| G11 | GAP | F5→F1 | no field in any news_impact contract references a qbus revision_id/source_item_id; the only existing news-side link is cluster_id (story grain, not report grain) | contracts/news_impact/fact_log.v1.schema.json:100 ($defs: cluster_id present, no source_item_id/revision_id field) vs engine/qbus_news_store.py:239-244 | Impossible with existing fields only at report grain: the single existing owner that could carry it is the fact_log `provenance` object (origin_document_id/origin_claim_id already exist there) — a report ref would reuse `provenance.origin_document_id`, not a new column. |
| G12 | GAP | F4 | no per-event materialisation/received clock; events.jsonl is regenerated with only a manifest sidecar stamp | engine/chronicle/spine.py:221-236 vs engine/chronicle/manifest.py:1-12 | Consumers take materialisation time from the existing manifest envelope stamp + per-ledger sha256/row counts (governor-written sidecar) instead of adding a field to events. |
| G13 | COLLISION | F5, F6, F7 | "as_of"/"observed" stamps at three granularities: date string, RFC3339 instant, parameterised as_of_utc | engine/intelligence.py:261-263 vs app/integrated_answer.py:425-434 vs contracts/news_impact/thesis_view.v1.schema.json:54-55 (as_of_utc, decision_cut) | Normalize at the consumer boundary: parse with the existing `_normalize_clock` (app/integrated_answer.py:174-192) and compare only same-granularity stamps; keep each artifact's native precision. |
| G14 | GAP | F1, F5 | availability clocks that do exist are day-coarse: source_available_at = filing_date T23:59:59Z; F1 has none | engine/news_impact/producer.py:264, :270 vs (F1 ABSENT, engine/qbus_news_contract.py grep) | Where the source carries a finer stamp, derive source_available_at from the existing wire `updated_at`/filing acceptance field already present in the same row; otherwise keep the typed absence, never invent a clock. |
| G15 | COLLISION | F3 vs F1 | two stores both called "qbus": legacy items parquet (data/qbus/items.parquet) vs sqlite news store (data/qbus/qbus.sqlite3) with disjoint id spaces | engine/qbus.py:12-13 vs scripts/run_qbus_news.py:473 | Join them only through each row's existing source fields (item_id basis source+url+title vs news source+source_item_id) at read time; never assume an id from one exists in the other. |

At least every collision/gap surfaced by Q3–Q7 appears above: Q3 clock-name
collisions → G04, G13, G14; Q4 correction gaps → G02, G12; Q5 rights drops → G09;
Q6 heuristic joins → G01, G08; Q7 name/key collisions → G03, G05, G06, G07, G10, G15,
and the cross-family grain gap → G11.

## Self-check evidence (10 random rows, sed -n '<line>p' at BASE)

| id | path:line | printed source line at BASE (≤120 chars) |
|----|-----------|------------------------------------------|
| F1-b3 | engine/qbus_news_store.py:250-259 | CREATE TABLE IF NOT EXISTS news_deliveries ( |
| F1-e2 | engine/qbus_news_store.py:645-671 | def _redact_story( |
| F2-b1 | engine/qbus_news_store.py:301-309 | CREATE TABLE IF NOT EXISTS news_clusters ( |
| F2-c3 | engine/qbus_news_cluster.py:66-68 | window_seconds: int = 6 * 3600 |
| F3-a4 | engine/qbus.py:176-186 | def assign_event_keys(rows: list[dict], thresh: float = 0.6, |
| F3-g2 | engine/news_events.py:626-633 | def _load_qbus_df(): |
| F3-h3 | engine/news_events.py:398-441 | def classify_event(title: str, body: str = "") -> dict \| None: |
| F4-c2 | engine/chronicle/adapters.py:103-104 | if not item_id or not date: |
| F5-c4 | ABSENT — grep at BASE: `git grep -in "received_at\|effective_at" -- contracts/news_impact/` → no match | ABSENT confirmed at BASE (no match) |
| F6-g1 | app/integrated_answer.py:332 | def _expectation_chips(day: datetime.date) -> dict[str, dict[str, Any]]: |
