# Terminal Ticker News — End-to-End Implementation Plan

> For agentic workers: use `superpowers:executing-plans` or an admitted `superpowers:subagent-driven-development` route task by task. Existing Mastermind admission, source custody and review law controls. This plan grants no provider activation, purchase, deployment or retry authority.

**Goal:** Deliver a fast, reliable, non-repetitive Terminal story feed for the full owner-defined S&P 500 security universe, followed by expansion without per-ticker upstream polling.

**Architecture:** Extend the existing qbus news/history owner with immutable provider revisions and deterministic current-state/cluster projections. One global provider stream/delta consumer feeds a rebuildable read index; the existing Macro API and Terminal authentication/server/UI owners deliver it. AI and GMI are downstream optional consumers, not ingestion dependencies.

**Tech stack:** Python leaf modules and pytest; proposed owner-internal SQLite WAL migration using the standard library; existing Macro FastAPI application; existing Terminal Next.js/TypeScript/React and Vitest/Playwright. Reuse pinned project dependencies. No new database service, message broker or worker-control system.

**Spec:** `docs/superpowers/specs/2026-10-04-terminal-ticker-news-design.md` (read in full).

**Authority / operation:** current Chairman instruction to lead planning and end-to-end implementation; parent `ticker-news-r1-20261004-astra-001`; initial source carrier `sol/web-ticker-news-r1-20261004-astra-001`. Requested reasoning mode: Pro; actually served model/mode not independently attested. Extra High is a technical recovery option only, never a permission bypass.

## Global constraints

- Cover the exact effective constituent security set; never truncate to 500 or substitute a narrative basket. A quiet security is not missing coverage.
- No LLM, embedding call, model importance or GMI prerequisite in the R1 ingest/display path.
- qbus owns source history/identity; security reference, source-rights, authentication, publication and runtime remain with their incumbent owners.
- Preserve v1 IDs, first-known clocks and history; no in-place reinterpretation or competing live writer.
- Provider source identity is distinct from delivery route; Massive-distributed Benzinga and direct Benzinga cannot count as independent sources.
- Published, provider-updated, received, committed and delivered clocks remain distinct. Unknown is not zero or current.
- Unknown content rights withhold the affected use. No new purchases, terms acceptance, credentials in source/logs, unlicensed payload fixtures or public raw-news archives.
- No anonymous fallback for protected data; revocation must affect open streams and caches.
- No deployment until the actual existing release/admission owner permits it and the exact source, independent review and CI gates pass.
- Material UI proof covers dark/light × EN/ZH × 1440/390, including degraded/restricted states.
- A plan, passing fixtures, published PR, merge, canary and natural production acceptance are separate milestones.

## Review focus

1. Same headline can belong to different stories; different headline can be a revision of one story. Pin upstream IDs and material-number/negation tests in tasks 1–3.
2. An out-of-order update or route mirror can resurrect a withdrawal or overwrite a correction. Pin source-version conflicts, removals and reinstatement in tasks 2/5.
3. A reconnect can omit equal-timestamp records on page boundaries. Pin overlap, exhaustive pagination, crash-before-cursor and expired-client-cursor cases in tasks 4–7.
4. A quiet feed, connected socket or HTTP 200 can conceal stopped ingestion. Pin semantic-age and source-health cases in tasks 5/9.
5. Metadata/body display rights can differ by route and be revoked mid-session. Pin per-field rights, cache invalidation, already-open stream withdrawal and browser leakage cases in tasks 6–9.

## Source/collision map and current execution posture

Protected source: Mastermind `5b244a2bbe4c2a94ec25a887eb4a0d8fafe1ea2f` with compatible INDEX, COLD_START, ACTIVE_EXECUTION, SESSION_RELIABILITY and WEB_CEO_DELEGATION. Macro initial baseline: `dbd6968899acd773287f41add5c18f6848c27e07`. Terminal path discovery advanced to `e86bfe5a9886a43f980e6c62cbfe9668fa8c6eb2`; re-pin exact relevant objects before its modifying wave.

Read existing `engine/qbus.py`, `engine/qkernel.py`, `engine/financial_news.py`, `collectors/polygon_news.py`, `scripts/build_news.py`. Existing public service family is Macro `app/main.py` and its routers. Terminal `api/main.py` is a historical Phase-0 stub with unguarded/deferred authentication; it is NOT the production news host. Terminal's existing `terminal/app/api/company-theme-context/[symbol]` is an adjacent authenticated server boundary to inspect, not a route to overload.

Macro #7982 owns active guidance work in `engine/financial_news.py`; #8057 owns marketing story-evidence changes; #8186 is held Events/News work; #7318 owns GDELT CI enrollment. Do not edit or adopt their source. Shared CI manifest enrollment is serialized at integration, not delegated to parallel writers. The first new leaf modules do not modify any of those paths.

Executive observation during planning was read-only; it did not dispatch this program. Workbench C3's observed binding was limited to its canary/document paths, not Macro/Terminal. Native managed-workspace and GitHub source actions are separately available. Do not describe a connected tool, queued intent or prepared packet as a running child. Use an admitted existing Fabric/manual route only after positive admission; otherwise direct source/test work proceeds without raw provider spawning.

No exact Agent OS news workstream was resolved from the focused lookup. Preserve that gap; attach to the real qualitative/Terminal owner after exact record discovery. Do not create a guessed WS identity or a second task database. This source carrier holds implementation evidence meanwhile.

---

## Phase A — Correctness kernel (no network, credentials or deployment)

### Task 1: Provider-neutral revision normalization

**Files:** create `engine/qbus_news_contract.py`; test `tests/test_qbus_news_contract.py`.

**Consumes:** documented Benzinga WS/REST and Massive Benzinga v2 JSON, caller-supplied aware `received_at`. No ambient clock, network, config or filesystem.

**Produces:** immutable `NewsRevision`; `normalize_news(payload: Mapping[str, object], *, transport: str, received_at: datetime) -> NewsRevision`; `NewsContractError` with sanitized stable reason codes. Supported transports: `benzinga_ws`, `benzinga_rest`, `massive_benzinga_v2`.

Freeze fields: `source`, `source_item_id`, `transport`, `message_id`, `action`, `published_at`, `updated_at`, `source_event_at`, `received_at`, `title`, `url`, `teaser`, `provider_tickers`, `channels`, `tags`, `body_sha256`, `content_hash`, `revision_id`. Optional body content is fingerprinted only in this leaf result, not retained or emitted to clients. This contract is not a rights grant or canonical ticker resolver.

- [ ] Write failures for distinct IDs with identical titles; same upstream article across direct and Massive routes; receipt-time-independent revision identity; RFC2822/RFC3339 UTC conversion; invalid/naive clocks; booleans masquerading as numeric IDs; unsupported action/transport; removed events without content; empty/oversized malformed strings; no raw-body/secret echo in exceptions.
- [ ] Run `python -m pytest -q tests/test_qbus_news_contract.py` and record genuine RED before implementing.
- [ ] Implement the frozen dataclass and strict bounded normalizers. Preserve provider ticker spelling, stable source identity, optional fields and immutable tuples. For action `removed`, require source item identity but permit missing publication/content clocks; use receipt time only as our observation, never as invented provider time.
- [ ] Run owning tests plus compile validation. Verify importing/calling the module performs no network/filesystem/ambient-clock work. Record exact source digest and executed result.
- [ ] Commit the reviewed unit on the existing source carrier; do not enable a collector.

### Task 2: Deterministic current-state reduction and withdrawals

**Files:** create `engine/qbus_news_reducer.py`; test `tests/test_qbus_news_reducer.py`.

**Consumes:** task-1 `NewsRevision` and previously persisted `NewsState | None`.
**Produces:** `reduce_revision(previous: NewsState | None, incoming: NewsRevision, *, restoration_qualified: bool = False) -> Reduction`. `Reduction` reports `accepted`, `duplicate`, `stale`, `conflict` or `withdrawn`, resulting state, and explicit ticker removals/additions. State retains stable source item identity and earliest actual receipt.

- [ ] RED tests: replay idempotence; newer/older updates; same-version different-content conflict; changed title with stable item; ticker correction; known-clock and clockless removals; stale updates after removal; cross-item rejection; explicit qualified reinstatement only; no publication stamp replacing first receipt.
- [ ] Implement pure reduction. Unknown-clock withdrawals stay withdrawn until an owner-qualified reinstatement; a caller-facing boolean is not itself authority and adapters must not derive it from untrusted payload fields. Conflict cannot silently select an arbitrary provider mirror.
- [ ] GREEN property/permutation tests distinguish valid source-order invariance from genuinely ambiguous same-version content. Prove input objects are not mutated.
- [ ] Commit and retain adversarial witnesses as regression tests.

### Task 3: Exact universe and conservative incremental clustering

**Files:** create `engine/qbus_news_universe.py`, `engine/qbus_news_cluster.py`; tests `tests/test_qbus_news_universe.py`, `tests/test_qbus_news_cluster.py`.

**Consumes:** an injected, owner-identified constituent snapshot and owner-resolved security aliases; accepted task-2 states. No new security master, name scraper or GMI inference.
**Produces:** `qualify_universe(snapshot, *, asof) -> UniverseQualification`; `cluster_candidates(incoming, candidates, *, policy) -> ClusterDecision` and stable cluster/source membership references.

- [ ] RED universe tests: variable constituent count/share classes; missing owner revision; stale/future snapshot; additions/removals by effective and known time; ambiguous alias; basket-first truncation explicitly rejected; no-story versus unsupported security.
- [ ] Implement an exact-set comparison and explicit coverage reasons. Inputs supplied by an existing owner remain source-attributed; absence of membership evidence is not an empty universe.
- [ ] RED clustering tests: direct/Massive mirrors count once; multi-source reporting remains inspectable; late higher-quality source does not re-key; guidance-number, negation, fiscal-period, analyst-firm and rumor/confirmation counterexamples do not merge; no theme-only merge; transitive chaining refuses; uncertain case stays separate.
- [ ] Implement bounded candidate matching using existing qkernel primitives where appropriate, retaining discriminating full-title/number tokens outside v1's truncated identity semantics. Stable IDs are independent of the selected representative.
- [ ] GREEN performance test records candidates examined, not just wall time, so an accidental all-history scan fails. Commit without changing existing global qkernel behavior.

---

## Phase B — One durable owner, global intake and recovery

### Task 4: Qualify and migrate the qbus persistence path

**Files:** create `engine/qbus_news_store.py`, `scripts/migrate_qbus_news.py`; extend `engine/qbus.py` only after its complete caller census; tests `tests/test_qbus_news_store.py`, `tests/test_qbus_news_migration.py` plus existing `tests/test_qbus.py`.

**Interfaces:** `NewsStore.commit(revisions, *, expected_cursor, next_cursor) -> CommitReceipt`; `snapshot(security_id, *, limit, cursor, rights) -> NewsSnapshot`; `changes(after_sequence, *, limit, rights) -> ChangePage`. Commit atomically persists source observation, reducer result, affected ticker indexes, outbox and source cursor. A receipt identifies actual durable sequence and backend generation.

- [ ] Census all qbus read/write callers at the exact base. Produce a mapping for v1 IDs/columns/clocks and write ownership. Resolve any active writer before changing its backend.
- [ ] RED tests: crash before/after commit, restart replay, duplicate insert, same-version conflict, concurrent stale cursor, index movement, withdrawal before catch-up, read-only SQL access, snapshot/cursor consistency and read-after-restart.
- [ ] Implement the owner-internal transactional backend with schema version, bounded transactions, foreign-key/uniqueness constraints and restrictive local file permissions. No client or secondary service writes the store. Do not treat SQLite concurrency as distributed multi-writer ownership.
- [ ] RED/GREEN migration tests use a disposable copy of a pinned legacy fixture. Preserve every v1 ID and first-known timestamp, expose a compatibility read projection, and prove no live row is separately canonical in Parquet and SQLite. Migration is restartable and never rewrites the source archive.
- [ ] Prove rollback to the prior compatible reader/generation without resurrecting withdrawn data or bypassing rights. Production selector remains OFF until independent review, writer custody, backup/restore and parity evidence pass.
- [ ] Commit source and evidence; do not execute migration on production data during source qualification.

### Task 5: Global Benzinga stream plus correction-safe catch-up

**Files:** create `collectors/benzinga_news.py`, `collectors/massive_benzinga_news.py`, `scripts/run_qbus_news.py`; tests `tests/test_benzinga_news.py`, `tests/test_massive_benzinga_news.py`, `tests/test_qbus_news_recovery.py`.

**Interfaces:** adapters yield task-1 revisions and source checkpoint candidates; only task-4 durable commit advances their acknowledged cursor. Credential and source-use checks are injected from existing owners. `run_qbus_news` is a foreground service entry point for the existing runtime supervisor, not a scheduler/control plane.

- [ ] Read current vendor OpenAPI/AsyncAPI and freeze a source-linked protocol fixture. Do not use actual paid article text in committed tests.
- [ ] RED tests use fake transports: create/update/remove; reconnect; malformed envelope; same-second pages; partial page; looping/cross-origin `next_url`; timeout/429/5xx; 401/403; restart between store commit and ACK; update to an old publication; removed-ID catch-up; exceeded page budget and explicit gap.
- [ ] Implement one global connection or delta cursor, rate-limit/backoff through existing adapter primitives, bounded payload/message buffers, cancellation and credential-redacted logs. Do not launch 500 independent requests or collectors per browser tab.
- [ ] Implement Massive v2 as a separately labeled supplement. Without a qualified update/removal feed, it cannot certify correction-complete failover. Preserve route-specific rights and upstream identity.
- [ ] GREEN tests prove that failed persistence never advances the cursor and browser demand does not change upstream connection count. Measure configured rate ceilings using fake time.
- [ ] Build a read-only entitlement/rights preflight report through existing owners. Keep activation OFF for unknown or refused rights; do not buy the add-on.

### Task 6: Existing Macro API read/stream composition

**Files:** create `app/ticker_news.py`; modify only the router registration in `app/main.py` after reading its exact current auth/service middleware; test `tests/test_ticker_news_api.py`.

**Interfaces:** private qbus-backed snapshot/story/change reads; current principal/tier and source-use verdict supplied by incumbent auth/rights. These serve no raw vendor endpoint and do not start ingestion inside a request.

- [ ] Inspect existing `app/company_intelligence.py`, `app/gate.py`, `app/paywall.py` and main registration; reuse their relevant service-auth and audience/entitlement boundaries rather than copying another auth system.
- [ ] RED API tests: denied user, invalid security/cursor, restricted headline versus body, rights revocation, cache cross-user leakage, request limit, source failure, interrupted stream, expired resume cursor and ordinary quiet state.
- [ ] Implement typed `snapshot`, `story` and incremental change/SSE endpoints with bounded request sizes and heartbeat/health events. A cursor is scoped to the snapshot/backend/rights context. Revocation removes affected content from an open feed and invalidates derived caches.
- [ ] GREEN real ASGI tests use task-4 store code with synthetic data. Assert secrets, untrusted HTML and restricted payload fields never enter responses. Do not use historical Terminal `api/main.py` as a production shortcut.

---

## Phase C — Terminal feature, not a separate news website

### Task 7: Terminal server contract and proxy

**Repository:** `mastermindx-market-intelligence/mastermind-terminal`, fresh exact master and separate operation-bound source workspace/carrier.
**Files:** create `terminal/lib/newsContract.ts`, `terminal/lib/server/tickerNews.ts`, `terminal/app/api/news/[symbol]/route.ts`, `terminal/app/api/news/stream/route.ts`, `terminal/app/api/news/stories/[storyId]/route.ts`; tests in `terminal/lib/__tests__/tickerNews*.test.ts`.

**Consumes:** task-6 authenticated backend contract and existing Terminal auth/plan/rate-limit helpers, discovered from the current company-theme-context route before coding.
**Produces:** the three public-to-authenticated-client APIs named in the spec, with no provider key or free unauthenticated fallback.

- [ ] Pin actual Terminal auth, server-fetch, service-token, timeout and streaming-host patterns. Record exact dependency paths in the execution receipt. Do not reuse the retired prototype API.
- [ ] RED contract tests mirror every closed enum/null/cursor field; reject oversized/unknown unsafe payloads and mismatched security/generation. Test denied tier and source-specific restrictions separately.
- [ ] Implement server-only upstream calls and stream cancellation/resume. Keep account entitlements and rights checks on the server; cache scope includes actual rights context.
- [ ] GREEN tests include backend fixture round-trip and an actual aborted client. Bind the source/contract versions across both PRs; a compiling independent frontend is not integration proof.

### Task 8: Ticker story panel and existing symbol navigation

**Files:** create `terminal/components/news/TickerNewsPanel.tsx`, `terminal/components/news/StoryRow.tsx`, `terminal/components/news/StoryDetail.tsx`, scoped canonical-token stylesheet, and `terminal/e2e/ticker-news.spec.ts`; mount through the current stock/Terminal selected-symbol owner (read current `TerminalShell`/detail implementation before assigning its exact changed range).

- [ ] Write mounted-component failures for ticker switch, retained scroll/detail state, delayed fetch arriving for the previous ticker, snapshot+stream race, repeated message, removed open story, unread marker, pause while reading and expired-cursor reset.
- [ ] Implement default reverse chronology and compact grouped sources. No sentiment badge, invented impact score or faux AI summary. Distinguish provider-tagged mention from qualified primary subject. Source details and health are progressive disclosure.
- [ ] Implement precise loading/live/catching-up/quiet/degraded/restricted/unavailable states, timestamps, lawful original-source links, keyboard focus, reduced motion and restrained accessible live announcements.
- [ ] Implement EN/ZH UI and deliberate dark/light material treatment using existing product tokens. Do not force an unimplemented GMI Related tab into the default UI.
- [ ] Run Vitest and Playwright on the real component/route composition, then capture all eight theme/language/viewport cells and named failure states. Independent review must judge comprehension and hierarchy, not just screenshots existing.
- [ ] The existing iOS News placeholder is a subsequent shell-consumer task using this same API/web feature and native manifest rules; no duplicated Swift aggregation or auth logic.

### Task 9: End-to-end fault, load, coverage and security qualification

**Files:** `tests/test_ticker_news_end_to_end.py`, `scripts/verify_ticker_news.py`, Terminal E2E additions, source-linked receipts under `research/ticker_news/evidence/` (synthetic or metadata-only permitted evidence).

- [ ] Start the actual source-to-store-to-API-to-browser composition with a synthetic provider, not a mock at the UI boundary. Assert create, correction, ticker reassignment, removal, restart and resume reach the same visible rows.
- [ ] Replay the critical false-merge counterexamples and review routing samples blind to outcomes. Report denominators, unknowns, sample size and source overlap.
- [ ] Measure sustained 10 revisions/s, 100/s for 60 s burst and 100 readers. Receipt-to-index target p95 ≤250 ms/p99 ≤1 s; index-to-client p95 ≤500 ms. Report dropped/backlogged observations instead of omitting them. These are proposed targets until actually measured.
- [ ] Fault-inject disk-full, denied permissions, stopped provider with live socket, corrupt cursor, revoked rights, stale constituent snapshot, cache poisoning and malicious pagination/body input. No bypass or silent fresh label may pass.
- [ ] Run owning regression suites, current CI planner/enrollment and exact-head hosted checks. Serialize shared manifest changes against #7982/#8057/#7318. Obtain an independent whole-feature review through an actually admitted route.

---

## Phase D — Licensed canary, ordinary production proof and closure

### Task 10: Licensing and source-quality gate

- [ ] Resolve the existing source entitlement/rights receipt and approved spend for the exact feed. If absent, prepare one bounded vendor/product decision request; no blanket assertion that an API token licenses redistribution.
- [ ] Compare direct Benzinga and Massive v2 on unique upstream IDs, update/removal completeness and measured source-to-receipt clocks. Distinguish source time error from transport delay. Press releases may be added as a second editorial-origin class if rights permit.
- [ ] Freeze the production source set, reference event sample, current universe version and retention policy. Baseline quality targets are ≥99% sampled reference-event recall within 60 s, ≥99% reviewed routing precision, ≤1% duplicate-row escape and zero merges of the critical counterexample set. Preserve uncertainty and reference-coverage limitations.

### Task 11: Release, canary and natural soak

- [ ] Reconcile exact source/review/CI/custody state in both repositories. Release only through existing deployment owners, with provider keys delivered through their existing secret mechanism and one actual supervised writer.
- [ ] Run a scoped licensed canary: source receipt → durable history → API → authenticated Terminal in the production browser. Capture actual revisions/clocks/health/rights without publishing unlicensed payloads.
- [ ] Prove restart/catch-up, client reconnect, source removal and rights downgrade with controlled tests; identify them as controlled rather than naturally occurring events.
- [ ] Observe at least five actual trading sessions including an event/earnings burst, using existing durable monitoring/return ownership. Do not idle a Web reasoning turn or claim it is monitoring after a final response. Keep owed natural-event proof explicitly open when not yet observed.
- [ ] Verify semantic freshness while an upstream is deliberately stopped; old HTTP 200 files must not remain Live. Verify rollback does not resurrect removed or unentitled content.

### Task 12: Acceptance, expansion and deferred consumers

- [ ] Accept R1 only when the spec's source, coverage, correctness, rights, load, UI, recovery and natural-production gates all pass. Update the actual Agent OS owner and retain exact GitHub evidence/PR/source refs. Release only this operation's clean recoverable workspace after positive completion.
- [ ] Expand through the existing security universe and licensed coverage, without multiplying upstream subscriptions by ticker. Measure small-cap noise separately before widening default filters.
- [ ] Later AI: one enrichment per material cluster version, provider metadata first, cheap model only when justified, source citations, explicit cost/rights budgets, no predictive promotion by default.
- [ ] Later GMI: existing accepted graph/company-exposure references, exact lineage/clocks/roles and visibly separate Related context. Disable only Related on stale/revoked relations. No second theme map or inferred exposure percentage.

## Execution and continuity rules

Start tasks 1 and 2 directly while the harder qbus migration/rights/host integration decisions are reviewed. These leaf units require no new vendor access, storage cutover or frontend changes. Once an admitted worker route is available, delegate frozen adapters, tests and UI units economically; retain ownership of cross-system contracts, integration and acceptance. `WHY NOT FABLE`: routine bounded units are specified and do not require a second frontier principal.

For every unit: genuine RED → implementation → GREEN → exact source/digest → independent review where required → same-carrier publication/readback → reassess the next useful safe dependency. A unit finishing is not parent completion. Preserve any interrupted process or uncertain modification on its original carrier. Do not claim that mode text switches the model, that a queued Job ran, or that a GitHub push deployed the service.

If a Pro write suffers a technical failure, reconcile the exact intended effect and publish a recoverable frontier when possible, then request Extra High for the specific next action as the Chairman requested. Do not switch carriers/models to bypass a permission refusal. Independent safe work remains eligible, but do not enlarge unpersisted effects after a persistence failure.

## Current checkpoint at plan publication

- Spec committed at `e56de2e4062f3eb28a71c9808adc226e8f4bb9db` on the existing branch.
- No source collector, model call, subscription, DB migration, service install, production deployment or background worker started.
- Existing paid source rights and exact natural latency remain unknown.
- Next action: execute task 1 with real failing tests, implement the contract, verify and publish; then task 2. Reconcile each new source effect on this same carrier.
- Mission complete: **false**. A product acceptance claim requires all Phase D gates, not this document.
