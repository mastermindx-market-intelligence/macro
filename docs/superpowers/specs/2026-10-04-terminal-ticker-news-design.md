# Terminal Ticker News — Design and Acceptance Specification

Date: 2026-10-04. Parent operation: `ticker-news-r1-20261004-astra-001`.
Status: proposed implementation design; no feed, license, deployment or production acceptance is claimed.

## 1. User outcome and scope

The Chairman commissions end-to-end delivery of a high-quality, low-latency ticker story feed in Mastermind Terminal, initially covering the complete current S&P 500 constituent security set. Stories should arrive promptly without repetitive rows. Source aggregation comes before LLM analysis. GMI-mediated related-subtheme news is a later, separately accepted consumer.

The default task is: select a stock, understand what just happened, distinguish new information from another copy, open the source, and see whether the feed is actually live. Coverage means every constituent has an eligible identity and a truthful coverage state, not that every security must have a story. The constituent count is owner-provided, never hard-coded to 500; share classes and effective membership changes remain explicit.

Non-goals for R1: model summaries, model importance, sentiment-derived signals, automated trading/position sizing, a replacement GMI graph, social-media scraping, website/paywall circumvention, an enterprise vendor purchase, a new fleet scheduler/router/auth system, and native-app business logic duplicated from Terminal web.

## 2. Source and ownership baseline

Protected procedure: Mastermind `5b244a2bbe4c2a94ec25a887eb4a0d8fafe1ea2f`, skillpack 1.0.1, bootstrap 1. Current Macro source baseline: `dbd6968899acd773287f41add5c18f6848c27e07`. Earlier Terminal source census: `3fd79ec4d0f68cebc49cbd610c62547aebe5d073`; refresh its relevant files and branch before Terminal implementation.

Reuse these existing owners:

| Concern | Incumbent |
| --- | --- |
| Qualitative news identity/history | `engine/qbus.py`, `engine/qkernel.py` |
| Financial-news collection/display compatibility | `engine/financial_news.py`, `scripts/build_news.py`, `site/news/by_ticker.json` |
| Security identity and constituent membership | existing Data OS/security-reference and breadth constituent owners |
| Source permissions, retention and delivery entitlements | incumbent source-rights/configuration owners; authenticated resource permission is not redistribution permission |
| Terminal authentication, plan access and API delivery | existing Terminal server/auth/entitlement owners |
| GMI topology and company exposure | GMI graph and existing Company Theme Exposure API/resolver/card |
| Workstream continuity / runtime | Agent OS / Executive OS respectively |

`collectors/polygon_news.py` is a daily sentiment collector, not the live feed. Its 500-name cap prepends narrative basket members and can fall back to 120; it does not establish complete S&P coverage. Do not expand or repurpose it as the live scanner.

Existing qbus v1 is a batch Parquet store. `append_items()` clusters within its supplied batch and rewrites the accumulated file; the financial normalizer can submit one row at a time. Its title/host-derived historical IDs, keep-first behavior, day-grain lookup and batch-representative cluster keys cannot silently become a correction-safe intraday contract. Preserve v1 history and callers. Evolve the same owner explicitly rather than adding a competing news database or changing historical IDs in place.

Collision census: Macro #7982 touches `engine/financial_news.py` and the shared CI manifest; #8057 touches marketing intelligence and the CI manifest; #8186 is a held Events/News official-result lane; #7318 owns GDELT CI enrollment. This program does not take those writers or merge their work. The initial additive contract files avoid those surfaces. No approximate Agent OS workstream ID is invented when the existing parent lookup is unresolved.

## 3. Delivery architecture and alternatives

Rejected A: 500 independent ticker pollers. This duplicates requests and publications, makes coverage and rate limits fragile, and scales costs with the watched universe.

Rejected B: an independent Terminal news database, ticker master and crawler. This forks qbus identity/history and permits inconsistent corrections across products.

Selected C: one admitted global upstream stream or delta cursor per provider account/feed, normalized through a qbus-owned revision contract, then a rebuildable ticker/story read index and authenticated Terminal delivery. Provider IDs and source history stay with qbus; the client is presentation only.

Path: provider adapter → boundary timestamp and schema validation → rights/identity qualification → qbus durable revision commit → bounded incremental story index → authenticated API/SSE → Terminal panel. Async optional enrichment is downstream and cannot delay ingestion or erase original evidence.

The serving index is non-authoritative: it is rebuildable from the accepted qbus history, has no independent writer/publisher truth, and can be discarded without losing source observations. No Kafka, new distributed queue, new global registry or new control plane is required.

### Persistence and migration decision

First deliver and review a pure contract/reducer independent of storage. Then qualify the existing qbus owner for incremental writes. The proposed physical implementation is an owner-internal SQLite WAL backend on a local persistent filesystem, with transactional revision/index/outbox/cursor updates and one admitted writer. It is a replacement backend for the affected qbus ingestion path, not a second active news authority. Do not deploy it on a shared network filesystem. No additional database service purchase is proposed.

Before selecting that backend in production, enumerate every qbus writer/reader, prove the legacy read projection and replay identity, import the original v1 records losslessly, preserve their original IDs/clocks, and exercise rollback. Existing Parquet becomes an owner-produced compatibility projection for migrated rows; it must not independently accept the same migrated live news. A backend switch stays disabled until single-writer custody, exact mapping, projection parity and crash/recovery proof pass. If this migration cannot be qualified independently, retain the pure source work and return the exact owner conflict; do not improvise a parallel store.

## 4. Provider contracts and procurement boundary

Research checked against primary vendor documentation on 2026-10-04:

- Benzinga News WebSocket: `wss://api.benzinga.com/api/v1/news/stream`; envelope includes message ID, kind, `data.action`, item ID, timestamp and content. Documentation explicitly describes created, updated and removed actions. REST catch-up is `/api/v2/news` using `updatedSince`, with `/api/v2/news-removed` for removals. Read the current OpenAPI/AsyncAPI when implementing; do not infer a cursor/replay guarantee from marketing copy.
- Massive Benzinga: `/benzinga/v2/news`, not sunset v1. Preserve upstream `benzinga_id`, `published`, `last_updated`, tickers, title, optional teaser/body and `next_url`. The published parameter list does not establish a reliable updated-since or deletion contract; absent such evidence, this adapter is coverage/history supplement, not a correction-complete substitute for the direct stream.
- Benzinga press releases can supplement primary issuer announcements. Reuters/LSEG and other wires are later quality upgrades, not blockers for building a provider-neutral core.

Direct Benzinga and Massive-distributed Benzinga are two delivery routes for the same upstream publication, not independent corroboration. Use upstream namespace `benzinga` plus its article ID; record transport separately. Different rights on two routes must not be combined into a broader permission.

Before activation, obtain an owner-backed capability/rights receipt: exact product/account/feed, internal ingestion, headline display, teaser display, body storage/display, image use, historical retention, derivative/LLM processing, redistribution, audience/tier, expiry and revocation. Unknown means withheld for the affected use. Existing API access or an individual $99 plan is not commercial-display permission. Do not purchase, accept terms or activate a new provider on this commission alone. Existing entitled metadata may be probed through the existing credential owner without exposing a key; unauthorized 401/403 is not a retry instruction.

Primary references:
- https://docs.benzinga.com/ws-reference/data-websocket/get-news-stream
- https://docs.benzinga.com/ws-reference/actions
- https://docs.benzinga.com/openapi/news-api.spec.yml
- https://docs.benzinga.com/asyncapi/news-stream.yml
- https://www.benzinga.com/apis/blog/mastering-the-benzinga-newsfeed-api/
- https://massive.com/docs/rest/partners/benzinga/news
- https://www.massive.com/changelog
- https://www.benzinga.com/apis/cloud-product/press-releases/

## 5. Core data and clock contract

Keep source observations separate from inferred clusters and presentation state.

`NewsRevision`: schema version; upstream namespace; provider item ID; transport; transport message ID when available; action (`created`, `updated`, `removed`); publisher-published time; provider-updated/event time when provided; independently recorded received time; title; optional permitted teaser/body reference and digest; original URL; provider ticker tags; owner-resolved security IDs; category/tag metadata; rights receipt reference; content fingerprint; revision ID; validation/clock state.

Do not infer primary-company relevance merely from a vendor's array of mentioned tickers. Preserve `provider_tagged` versus independently qualified `primary_subject` routing. Ambiguous aliases are not resolved by blindly uppercasing a word; share-class/provider formats map through the existing identity owner. Keep unresolved evidence observable without leaking it into the wrong ticker.

Published, updated, received, durable-commit, indexed and client-received clocks have different meanings. Never backdate our knowledge to a provider publication stamp. Reject naive/invalid required timestamps, keep unsupported precision unknown, and surface clock anomalies instead of clamping negative lag to zero. A late historical record is not a newly published breaking event. Evaluation uses the actual first receipt and the membership/rights state knowable at that time.

Source item identity is independent of headline and URL. Revision identity includes meaningful normalized content and source version, but not local receipt time or delivery route. Duplicate deliveries preserve first receipt. An older update cannot replace a newer revision. Different content at the same provider version is an explicit conflict, never arbitrary last-write-wins. A removal with incomplete clock/content is a conservative withdrawal observation; resurrection requires an explicitly qualified later source event. Ticker corrections remove old index memberships and add new ones atomically.

History is retained only as permitted. A removal hides the affected publication immediately; legal deletion/retention obligations can require purging payload bytes while retaining only permitted audit metadata. Do not promise permanent full-text retention. A cluster with another independently licensed live source can survive one source removal; a sole-source removal becomes withdrawn, not a stale clickable headline.

## 6. Deduplication without suppressing new information

Tier 1: exact upstream item/version/message identity and permitted-content hashes.
Tier 2: canonical URL and exact normalized headline with entity, time and salient-number constraints; retain all source receipts.
Tier 3: bounded candidate retrieval by shared qualified security/event family and recent window, then conservative token/shingle comparison. No all-history pairwise scan, embeddings or LLM in R1.

Stable cluster IDs must not change merely because a higher-tier publisher arrives. Cross-route copies do not inflate source count. Independent reporting remains available under an expandable source group; `4 sources` means four distinct upstream editorial origins, not four hostnames or API deliveries.

Preserve negation, directional verbs, monetary values, percentages, dates, fiscal period, rating firm/action and deal status. `guidance $8.2B` versus `$9.1B`, `approves` versus `does not approve`, rumor versus confirmation, and one analyst versus another are not duplicates. A broad shared theme is insufficient to merge company events. Avoid transitive A≈B≈C chaining when A and C differ materially. Uncertain cases remain separate; false merging is worse than an extra row.

Updates are either non-material enrichment (no list jump) or new factual developments (visible update label). Corrections and removals remain visible to clients that saw the old item. Saved/read state uses stable IDs, not list positions.

## 7. Fetch, resume and failure behavior

Global stream intake continues independently of which ticker is open. Initial universe filtering uses an exact versioned constituent snapshot, not a fixed-length slice. One shared adapter serves all subscribers.

REST catch-up uses an overlap window, inclusive boundary and exhaustive bounded pagination. Advance a cursor only after the corresponding revisions and any required quarantine evidence are durably committed. Same-time items spanning pages, out-of-order updates, missing pages, 429, 5xx, disconnects and partial responses must not silently advance the watermark. Bound page count and report `gap_unresolved` rather than dropping overflow.

Validate vendor-provided next URLs against the allowed origin/path before attaching credentials; reject cross-origin URLs and redact query credentials from errors/logs. No client receives provider keys, raw untrusted HTML, service credentials or unentitled source payloads.

Connection status, last message, last successful catch-up, backlog, source-event age, per-security coverage and semantic freshness are separate health facts. A quiet ticker is not an outage. A working socket with a stopped upstream is not proof of current news.

## 8. Terminal API and experience

Proposed API family: `GET /api/news/[symbol]`, `GET /api/news/stream`, `GET /api/news/stories/[storyId]`. Bind exact implementations to existing Terminal auth/entitlement/server patterns before editing. Snapshot returns schema, canonical security, ordered rows, resume cursor, coverage, source health and explicit `live`, `catching_up`, `degraded`, `quiet`, `restricted` or `unavailable` state. The cursor is opaque and account/rights scoped. Streams emit versioned upsert, remove, health and reset events. Expired cursor produces a new snapshot/reset, never silent missing data. Rights revocation filters both snapshot and already-open stream.

Keep provider credentials server-side. Use the existing product access policy, validate requested symbols/cursors, enforce bounded page/subscription counts, and rate-limit through incumbent middleware. Do not add anonymous fallback for restricted data. SSE is preferred for server-to-client headlines; browser/native WebSocket is unnecessary unless the existing transport owner materially favors it. Long-lived upstream collection must not run inside a per-request serverless handler.

The web stock detail/Terminal ticker panel is the first surface; the existing iOS News placeholder consumes the same web/API capability later without reimplementing routing or entitlements in Swift. Preserve chart/selected ticker state. Default: clean reverse chronology, headline, real source, age, category and collapsed additional coverage. Pause auto-insertion while reading older rows and expose a `new stories` affordance. Opening details must preserve list scroll and ticker context.

Progressive filters: All / Company / Earnings & Guidance / Analyst / Filings / Releases. Low-value promotional/automated roundups are quieted by versioned deterministic policy with reversible reasons, not deleted from history. Full text and images appear only where entitled. Publisher text is labeled as such, never presented as our AI analysis.

Dark treatment: existing Terminal command-surface tokens, quiet raised rows, restrained emphasis, no decorative ticker cards. Light treatment: existing research-workspace tokens, white row material, legible hairlines and explicit hierarchy rather than merely swapping colors. Both preserve dense readable chronology, EN/ZH UI copy, keyboard focus, accessible live announcements, reduced motion, desktop 1440 and mobile 390 behavior. No new palette or opaque runtime stylesheet.

## 9. Performance and proof

Engineering targets, not measured vendor promises: receipt-to-durable-index p95 ≤250 ms and p99 ≤1 s at the declared load; index-to-open-client p95 ≤500 ms. Source-publication-to-client p95 ≤3 s is an aspirational push-feed comparison and must be reported separately by provider/source/clock quality. A REST fallback advertises its measured polling/catch-up lag and never masquerades as push.

Load envelope for initial tests: 10 new revisions/s sustained, burst 100/s for 60 s, 100 concurrent readers, and the exact admitted constituent set. Measure on the actual intended host before accepting these figures; synthetic results are implementation evidence only. No benchmark may weaken correctness, omit slow/dropped events or hide gaps from the denominator.

Release acceptance requires: all constituents represented or explicitly withheld with reasons; reliable identities; duplicate/update/removal tests; no credential/content-rights leakage; restart and disconnect recovery; bounded resource use; full UI matrix; exact-head CI and independent review; deployment through the existing release owner; rollback; and at least five actual trading sessions of provider quality/latency observation including an earnings/event burst. Start a canary before the soak, but call it a canary. Sunday synthetic tests do not satisfy natural-market proof.

Per-source scorecard measures delivered coverage against a frozen licensed reference set, precision of ticker routing, duplicate escape rate, false merges, update/removal delay, gap duration, and actual first receipt. Target ≥99% recall of selected licensed reference events within 60 s, ≥99% routing precision on reviewed samples, ≤1% duplicate-row escape, and zero false merges on the named critical counterexample set. Report sample sizes, missing-reference limitations and uncertainty; these thresholds do not imply access to all news everywhere.

## 10. GMI and later AI boundary

Reserve nullable relation metadata but do not fabricate it. Later related news consumes current accepted GMI/local-subtheme identities and Company Theme Exposure evidence with exact generation, validity/knowledge clocks, role and relation reference. It displays `Related via …`, not direct company news. Stale, unqualified or revoked relations disable only Related; direct news continues. No inferred economic percentage, causal certainty or new candidate/position authority.

Later LLM work deduplicates and clusters first, reuses permitted vendor metadata, analyzes once per material event version, and caches by source revision/model/prompt. Cost accounting and source-grounded fact verification remain separate acceptance. R1 makes no predictive-importance or trade-performance claim.
