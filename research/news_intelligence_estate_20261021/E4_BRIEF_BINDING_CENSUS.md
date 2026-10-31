# E4 Brief binding census — News Intelligence Estate (2026-10-31)

## Scope and method

HEAD: `19c31737672217939906b3861682e40de57d2395` (branch `lane/news-w4-e4-bindings-r1`, clean tree).
Work package: MASTERPLAN.md:379 row E4 and §3 P1-B (MASTERPLAN.md:182-188). Method: read the
named inputs, then grep each inventory file for
`budget|spend|reserv|cost|token|grant|audience|rights|publish|emit|refus|dedup|idempot|request_id|job_id|single|lock|revision|supersed|invalidat|correct`,
open only what the grep hit, and record one row per mechanism found. Every line cited below was
printed at HEAD before writing.

Files examined (all 20 exist; **MISSING: none**):

- Inputs: `research/news_intelligence_estate_20261021/MASTERPLAN.md`,
  `docs/ops/shared-news-intelligence.md`,
  `research/news_intelligence_estate_20261021/D1_NEWS_INPUT_TRACE.md`,
  `research/news_intelligence_estate_20261021/A1_SOURCE_DELIVERY_MATRIX.md`.
- Code: `engine/qbus_news_context.py`, `engine/press/desk_planner.py`, `engine/press/writer.py`,
  `engine/press/qbus_news.py`, `engine/neuralweb/brain_gateway.py`,
  `engine/neuralweb/ask_brain.py`, `engine/context_index/packet.py`,
  `engine/chronicle/context_pack.py`, `engine/marketing/authority.py`,
  `engine/marketing/desk_feed.py`, `engine/marketing/outbox.py`,
  `engine/marketing/story_lock.py`, `engine/news_llm.py`, `config.yml`, `config/press.yml`,
  `engine/alerts.py`, `scripts/run_press.py`, `scripts/marketing_publisher.py`,
  `scripts/close_pass_publish.py`, `scripts/publish_company_theme_exposure_r2.py`,
  `scripts/mirror_terminal_context_r2.py`, `scripts/fetch_r2.py`, `scripts/audit_r2.py`,
  `app/main.py`, `app/prophet_daily_brief.py`, `app/brain_runs.py`, plus the admission
  workflows `.github/workflows/press-publish.yml`, `marketing-publish.yml`, `close-pass.yml`.

Grep hit counts (the spec pattern, per file): qbus_news_context.py 16; desk_planner.py 106;
writer.py 137; brain_gateway.py 1031; context_index/packet.py 44; chronicle/context_pack.py 25;
marketing/authority.py 12; marketing/desk_feed.py 33; news_llm.py 12; alerts.py 11;
run_press.py 244; marketing_publisher.py 452; close_pass_publish.py 36;
publish_company_theme_exposure_r2.py 16; mirror_terminal_context_r2.py 0; fetch_r2.py 14;
audit_r2.py 41; app/main.py 138; prophet_daily_brief.py 3. A zero count is itself a census
fact: `scripts/mirror_terminal_context_r2.py` matches no binding keyword — it is a pure
fail-soft copy step (scripts/mirror_terminal_context_r2.py:16-19).

Out-of-scope and untouched: no code change, no owner/queue/store/budget/endpoint invented, no
legacy path enabled, no credential file read, `data/` and `site/` trees not read.

## The four unqualified bindings

MASTERPLAN.md:79 (§2.1 row "Shared Brief mode"):

> | Shared Brief mode | Detailed on-demand, permission-aware, correction-safe design | Design only; durable job/artifact/publication/spend bindings unqualified | Bind existing runtime/artifact/budget owners, run evaluation, build endpoint before UI, prove zero-demand and correction behaviour |

MASTERPLAN.md:182-188 (§3 P1-B) — quoted by line:

- :184 "The approved direction is explicit demand and shared reuse among equivalently entitled readers. News arrival, page opening or ticker changes in Headlines mode should not create inference work by themselves."
- :186 "The current design did not qualify a shared durable Brief artifact owner, cross-process request owner, conditional publication operation or enforceable pre-call spend reservation. Logging successful usage after a call is not admission. Resolve those bindings before enabling the endpoint or adding a Brief tab."
- :188 "Use an extractive baseline and an injected adapter first, then compare admitted models on the same rights-eligible corpus. Preserve failures, timeouts and uncertain-cost attempts under their original identity. [S14]"

The four bindings, as P1-B states them (B1) shared durable Brief **artifact owner**,
(B2) cross-process **request owner** ("one demand -> one piece of inference work; dedup/single-flight
across processes" — commissioning phrasing of :186), (B3) conditional **publication operation**
(permission-aware, correction-safe, revision-invalidating), (B4) enforceable **pre-call spend
reservation** (:186 "Logging successful usage after a call is not admission").

Correction rules the bindings must respect — MASTERPLAN.md:261-263 (§5.4): a correction "creates
new history and invalidates affected current derivatives"; "Corrections invalidate or supersede
generated current interpretations while preserving original as-known evidence and decision
history... must not silently rewrite a user thesis"; "rights withdrawal still controls which source
material may be displayed."

The evidence-side constraint — `docs/ops/shared-news-intelligence.md:20-24`:

> The API process keeps read-only access and no provider credentials. Research,
> briefs and editorial consumers can use `engine.qbus_news_context.news_evidence_bundle`
> with an explicit audience and fresh derivative-processing grant. This is a
> read adapter, not a second store, generator, job queue, cache or publisher.
> No model call or automatic publication is introduced.

## Mechanism inventory

| # | mechanism_id | binding | owns | identity/keys | rights handling | correction handling | failure identity | admitted at HEAD | pinned by test |
|---|---|---|---|---|---|---|---|---|---|
| 1 | `engine/qbus_news_context.py::news_evidence_bundle` (:18) | none (read-only evidence input for any Brief work) | read-only context | schema `qbus.news_evidence.v1`, audience ∈ {site_full, internal_research, blog_draft, marketing_draft} (:15), security_id, receipt_refs, `evidence_sha256` over identity fields (:51-54) | audience whitelist (:22-23); receipts loaded then filtered to `derivative_processing` (:29-30) so revoked/conflicting policy cannot silently leave a grant active (:27-28); `publication_authorized` hard-coded `False` (:37) | reads exact current revisions in one snapshot transaction via the store (:42; engine/qbus_news_store.py:1953); no write-back | restricted/empty states returned as data, not errors (:39-40); callers convert I/O failure to `PrivateNewsUnavailable("qbus_draft_evidence_unavailable")` (engine/press/qbus_news.py:223-224) | YES — blessed for "Research, briefs and editorial consumers" (docs/ops/shared-news-intelligence.md:20-24); wired by press `prepare_slot` (engine/press/qbus_news.py:211,221) | tests/test_shared_news_intelligence.py:426-460 |
| 2 | `engine/qbus_news_store.py::evidence_for_security` (:1923) | none (evidence substrate under row 1) | read-only context | immutable `news_revisions` table keyed (source, source_item_id) (:239-248); snapshot binds stories+field projection+revision refs to one read transaction (:1925-1927) | caller owns audience/use admission (:1925-1926); rights filter applied inside snapshot (:1931) | revisions immutable; reads bind `current_revision_id` per report (:1953); members not `active` dropped (:1940-1941) | none needed on read; ROLLBACK closes the snapshot (:1974) | YES — sole news store behind the one-writer service (MASTERPLAN.md:74) | tests/test_shared_news_intelligence.py:159,199 |
| 3 | `engine/qbus_news_receipts.py::parse_rights_receipt`/`load_rights_set` (:117/:474) | none (rights layer for rows 1-2) | read-only context | receipt_id, source, provider, audience, `expires_at` (:156-161); `derivative_processing: bool = False` default (:49,:198) | expiry is source-local and revalidated (:156-161); "A revoked/expired duplicate must not leave an older grant active" (:488) | N/A (rights, not content) | `NewsReceiptError` codes (:30-33) | YES — load path of row 1 | tests/test_shared_news_intelligence.py:110,120,126 |
| 4 | `engine/press/desk_planner.py::_plan_brief` (:1071) | B2-adjacent (story dedupe identity), B1-adjacent (slot record) | artifact (press slot records; editorial Press, not the shared Brief) | slot id `press-{name}-{as_of}-{story_key(identity_parts)}` (:1176-1178); "Stable story ref, revision-specific staging identity. The former powers dedupe; the latter preserves both audit records when a pending draft is superseded by a corrected transcript" (:1170-1174) | press lexicon and public-link allowlist gate candidates (:1135-1140, :1226-1243) | earnings-call candidates without valid SHA256 revision receipt "skipped fail-closed" (:1118-1127); revision receipt joins slot identity (:1173) | skipped candidates logged with reason (:1122-1126, :1136-1139); never fabricated | YES — staged by scheduled press run (.github/workflows/press-publish.yml:63) | tests/test_press_native_plan_integration.py; tests/test_press_run.py |
| 5 | `scripts/run_press.py::run_stage` + `_write_stage_checkpoint` (:540,:611) | B2/B4-adjacent (pre-call durable marker) | artifact (staging record per slot, `data/press/staging/`) | one JSON per slot keyed by slot id (:608); first write is atomic **exclusive** create `os.link` (:555) — "even a caller bypassing planner deduplication cannot replay an unsettled provider effect" (:543-545) | record carries `admission_receipt`; private admission checks run immediately before each writer call (:640-649) and again at the external request boundary (engine/press/writer.py:956-964) | revision reconciliation re-stages under new identity; prior record retained (rows 4, 7) | checkpoint storage failure **prevents the provider call** (test_press_run.py:253); interrupted slot "stays reserved by the existing planner until its same attempt is reconciled" (:17-18) | YES — same scheduled runs as row 4; also earnings-story-press-stage.yml:54 | tests/test_press_run.py:157-377 |
| 6 | `engine/press/writer.py::RunState` + `write(admitted_token_cap=…)` (:47,:800) | B4 (in-process only) | spend (per-run token budget) | per-run `RunState`, "Not thread-safe by design — one run, one state, one thread" (:47-48) | `llm.enabled` gate (config/press.yml:369 `enabled: true`); admitted lane requires single-provider, attempt-0 shape (:846-861) | N/A (budget rail) | "Never raises. Every failure path records against the RunState" (:806-807); no-call failures carry `provider_usage: no_provider_call, charged_tokens: 0` (:895-899) | YES — press lane default (`run_token_budget: 240000`, config/press.yml:374) | tests/test_press_writer.py:496-500 |
| 7 | `engine/press/writer.py::write` admitted-token reservation (:846-883) | B4 (pre-call token reservation, in-process) | spend | `reservation = input_upper + max_tokens` (:863), recorded as `reserved_total_tokens` (:870); byte-exact input upper bound rather than post-hoc cost (:92-104) | preflight refusal `admitted_token_cap_preflight` when reservation exceeds `min(12_000, tokens_left)` (:872-883; cap constant :42) | N/A | reservation refused **before** the call (:881-883); post-call charge only from provider-reported usage (:991-996) | YES — same lane as row 6 | tests/test_press_writer.py:496-500 (`reserved_total_tokens` asserted) |
| 8 | `scripts/run_press.py::run_emit` (:1130) | B3 (conditional publication, press artifacts) | publication | append-only ledger `data/press/published.jsonl` (:48-50); staged items revalidated before emit (:21-25) | refuses private/qbus news (`press_emit_qbus_approval` :1165), canonical slots (`press_emit_canonical_approval` :1179), external candidates (:1198); `auto_emit_allowed: False` (:514); workflow additionally requires `vars.PRESS_PUBLISH_ENABLED` (:123-126) plus exact promotion bundle/slot/SHA256 (:178-189, :228-239) | `reconcile_earnings_call_revisions` marks `published_revision_changed_requires_correction` (:362,:456); "no historic row is ever rewritten" (:48-50) | failed/mismatched revisions retained as non-emittable records (:502,:516) | YES — scheduled staging live; emit dark by default (press-publish.yml:123 "DARK BY DEFAULT") | tests/test_press_run.py:157-377 |
| 9 | `engine/marketing/outbox.py` (enqueue/transition/apply_decisions :1676/:1931) | B1/B2/B3-adjacent (durable posting-queue artifacts; marketing social, not Briefs) | artifact + request (posting queue) | append-only `items.jsonl`/`status_ledger.jsonl`/`decisions.jsonl` under `data/marketing/outbox/` (:13-17); deterministic ids, id-dedup, text-dedup, near-dup Jaccard (:570) | only the actuator may advance statuses (:5-6); operator approve/hold decisions recorded and applied (:7-9); caps owned by Sentinel config (:9-10, `effective_cap` :360) | status machine: "a sent post can never walk back to approved/queued and re-send" (:110); failed posting retained and reported, never auto-reposted (:95) | cross-process best-effort advisory flock on `<outbox>/.lock`, fail-soft ~2s (:22-27); "display-tier ops state — not a forward signal ledger" (:30-31) | YES — marketing publisher runs on schedule (marketing-publish.yml:57) | tests/test_marketing_outbox.py:176-244 |
| 10 | `engine/marketing/story_lock.py::owner_of` (:125) | B2 (single-claim window; content-keyed, not request-keyed) | request (story ownership claim) | claim key reuses the press lane's "same claim" identity incl. the M3 collapse of differently-worded relays (:16-18); window minutes from config (:51-54) | cross-ACCOUNT only; same account may re-draw its own story (:31) | N/A (claims, not corrections) | malformed timestamps treated as IN-WINDOW — "a malformed row tightens the lock rather than disarming it" (:132-139); state read from emitted outbox items, "no lock-specific store" (:23-26) | YES — enabled by default (:65); the breaking lane's one-owner lock (engine/marketing/desk_feed.py:8-9) | tests/test_marketing_earnings_call_lane.py; tests/test_marketing_press_relay_quality.py |
| 11 | `scripts/marketing_publisher.py` (:1) | B3/B4-adjacent (kill-switched live publication) | publication | takes APPROVED, DUE items from the outbox (:3); durable in-flight marker `approved → posting` written **before the network call** (:30) | kill-switch `sentinel.publish_enabled()` AND `--live` (:20); per-item `validate_postable` (:25) | receipt recorded on success; failure → `posting → failed` with error (:31-32) | item already `posting` at startup is REPORTED and never reposted (:33); per-account daily cap counted ledger-based via `posted_today_by_account` (:21-23) | YES — cron + workflow_dispatch, dark unless repo variable set (marketing-publish.yml:13-14,57) | tests/test_marketing_approval_desk.py |
| 12 | `engine/neuralweb/brain_gateway.py::_held_quota_locks` + `_check_and_increment_quota` (:9036,:9148) | B2/B4 (durable cross-process admission ledger; counts, not token reservation) | spend + request (quota ledgers) | JSON ledgers under `MACRO_API_STATE_DIR/brain_quota/` keyed (user_id, lane, period_key) (:15-17), device keys (:8943-8955), monthly token files (:8987-8988), global `global_spend_{day}.json` (:8991-8994) | tier resolver via PostgREST `user_entitlements`, fail-safe → free (:26-28); zero limit = lane forbidden (:9207); unlimited allowlist (:9181-9182) | N/A (usage ledgers) | exclusive flock held "across the read AND the write", sorted-path deadlock avoidance (:9036-9060); corrupt ledger raises `QuotaLedgerCorrupt` — "refusing to treat as count=0" (:9069-9091); fail-OPEN payers / fail-CLOSED guests (:21-24,:9161-9163) | YES — `/api/brain/chat` wired in app/main.py:1639 | tests/test_brain_gateway_quota_safety.py:102-199 |
| 13 | `engine/neuralweb/brain_gateway.py` global daily ceilings (:168-169,:9014-9019) | B4-adjacent (house-wide daily ceiling; request count + settled tokens) | spend | `global_daily_request_ceiling: 5000`, `global_daily_token_ceiling: 50_000_000` (:168-169); env-overridable (:8997-9015) | independent of every per-user ledger (:24-25) | N/A | "Debit the house-wide request counter even for uncapped lanes" (:9264-9265); token side blocks only on already-settled usage (:9261) | YES — same lane as row 12 | tests/test_brain_gateway_quota_safety.py |
| 14 | `engine/neuralweb/brain_gateway.py::_record_token_usage` (:9391) + `lib.ai_costs.record_usage` (:32) | B4 — post-call settlement, the exact shape P1-B :186 rejects | spend | monthly per-user file + global spend file under the same flock (:9398-9420) | N/A | N/A | "record_usage from response.usage — never estimated" (:32); corrupt token ledger "never rewritten as tokens=0" (:9394-9408) | YES — same lane as row 12 | tests/test_brain_gateway_quota_safety.py:177-199 |
| 15 | `engine/neuralweb/ask_brain.py::_check_and_increment_quota` (:2440) | B4-adjacent (durable count quota, no lock) | spend | per-user-hour and global-day JSON files under `MACRO_API_STATE_DIR` (:2455-2472) | user from authenticated endpoint (app/main.py:1353-1366) | N/A | fails OPEN on I/O errors (:2444-2446); read-check-write without flock (no `_held_quota_locks` import in this module) | YES — `/api/ask` endpoint (app/main.py:1353) | tests/test_ask_brain.py:303-347 |
| 16 | `app/brain_runs.py` run registry (:92-214) | B2-adjacent (run identity + resume; not durable, not dedup) | request (in-flight runs) | `run_id`, user-bound, cursor = count of received events (:323-332) | `get(run_id, user_id)` scopes by user (:251) | N/A | finished runs stay re-attachable for a TTL (:62); in-memory `_runs` dict (:193) coherent only because the API runs a single worker (:36) | YES — `/api/brain/runs/{id}/stream` (app/main.py:1455-1475) | tests/test_brain_streaming.py |
| 17 | `app/main.py::portfolio_brief` (:2145) | B1/B2-adjacent (demand-reuse pattern for a deterministic brief; no inference) | artifact (composed brief, per-request) | in-process cache keyed (uid, ctx-file mtime, holdings fingerprint), TTL 300s (:2033-2035,:2041-2042,:2189-2190); fingerprint makes a population change a cache MISS "by construction" (:2036-2040) | Pro gate: 403 `pro_required` via tier resolver (:2160-2165); `Cache-Control: private,no-store` (:2154) | deterministic recomposition on artifact change (mtime key part) | fail-closed 503 `ctx_unavailable` / `portfolio_store_unavailable`; unknown book "is NOT an empty book" (:2177-2187) | YES — endpoint in the served app (app/main.py:2144) | tests/test_portfolio_brief.py:204-269 |
| 18 | `app/prophet_daily_brief.py::daily_brief_v1` (:138) | none (bounded read admission) | read-only context | pinned query alphabets are the injection guard (:80-90) | authenticated route; admission `BoundedSemaphore(1)` (:69,:148) — "This is not a cross-process budget or a limit on one read's memory use" (:69-71) | stale caller pin conflicts surface as UNAVAILABLE (:92-95) | overlap "fails privately instead of queueing thread-pool work" (:68-69) | YES — route exercised by API tests | tests/test_prophet_daily_brief.py |
| 19 | `engine/context_index/packet.py::build_packet` (:320) | none (retrieval context budget) | read-only context | fused retrieval packet; `TOKEN_BUDGET_HARD_CAP = 8000` (:42,:349) | none (context assembly) | "conflict detection" here is retrieval-result conflict (:167), not content correction | staleness checked (:134); bounded by construction | YES — used by brain gateway (engine/neuralweb/brain_gateway.py:7301) and agentos (scripts/agentos.py:4730) | tests/test_context_index_packet.py |
| 20 | `engine/chronicle/context_pack.py::pack` (:125) | none (deterministic context budget with reserve fractions) | read-only context | per-tier reserve fractions long 20% / medium 30% / short 50%, unused reserve spills down (:6-12,:32,:200-222); "cost = len(text) / 4.0" charged as lines are emitted (:222) | none | events carry receipts inline; no correction write-back (:116-117) | coverage note + `budget_used` reported (:145) | YES — press planner "CALL, never edit" (engine/press/desk_planner.py:862) and marketing desk feed (engine/marketing/desk_feed.py:171) | tests/test_chronicle.py:470-500 |
| 21 | `engine/marketing/authority.py::can_earn`/`should_narrow` (:100,:126) | B3/B4-adjacent (policy gates, display-tier marketing) | none (authority ladder checks) | record fields, not artifacts | earning requires `within_cost_cap` and `no_unresolved_corrections` (:117,:119); narrowing on `correction_rate_elevated` / `exceeded_cost_cap` (:142-144); G3 = "Publish through owned, approved lanes" (:48,:63) | unresolved corrections block earning (:119) — the only in-repo policy coupling of corrections to cost caps | N/A | YES — marketing ladder in nightly use | tests/test_marketing_attribution.py |
| 22 | `engine/alerts.py` daily alert log (:604,:624) | B2-adjacent (idempotent daily emission) | artifact (alert log) | `data/alerts/alerts_log.parquet` keyed (date, rule) — "re-running the same day is idempotent and cannot double-send" (:6-7) | none (internal) | alerts fire on changes, never levels alone (:4-5) | deterministic append | YES — nightly alert phase | tests/test_vsb_radar_alert.py |
| 23 | `scripts/publish_company_theme_exposure_r2.py::publish` (:136) | B1/B3-adjacent (immutable artifact publication pattern) | artifact + publication (R2 objects) | immutable per-company objects + immutable generation manifest, sha256-verified (:1-3,:113-128) | none (public plane) | immutability: correction = new generation, never overwrite | exclusive create `IfNoneMatch: "*"` (:128); `PUBLISH_CONFLICT = 2` exit on divergence (:26) | YES — R2 publish lane | tests/test_publish_company_theme_exposure_r2.py |
| 24 | `scripts/close_pass_publish.py` (:1) | B3-adjacent (conditionally gated live publish) | publication (R2 runtime plane) | publishes the provisional board + graded delta (:3-24) | stand-down env `CLOSE_PASS_NO_PUBLISH` (:56-58); `--dry-run` (:27-29) | every board graded against the next close and the delta published (:22-24) | late start "drops it: the call reviews as an alarm, runs clean and produces nothing" (:67) | YES — scheduled (close-pass.yml:147-149) | tests/test_close_pass_host_runner.py |
| 25 | `scripts/mirror_terminal_context_r2.py::mirror` (:122) | none (fail-soft convenience copy) | artifact (mirrored context JSON) | named artifacts, dry-run (:28,:133-135) | none | none — "never mirror a corrupt file" (:19,:106) | creds absent → skip exit 0 (:17,:145-146); "a freshness convenience, not a gate" (:16) | YES — nightly convenience step | tests/test_company_intelligence_refresh.py |
| 26 | `scripts/fetch_r2.py` + `scripts/audit_r2.py` | none (restore contract + freshness tripwire) | read-only context | content-hash skip vs R2 ETag (:19) | none | none | exit-code contract: "restore failed" must mean "do not publish the local tree over the deep store" (fetch_r2.py:24-27); audit is the dead-man's tripwire writing observability only (audit_r2.py:1-8,:32) | YES — CI/nightly wiring | tests/test_sni_public_exposure.py |
| 27 | `engine/news_llm.py::annotate` (:225) | none — B6 legacy path, default off | spend (if enabled) | headlines annotated in batches; caller `scripts/build_news.py:120` in the nightly `_enrich` | none | none | "No-op pass-through when no provider / disabled / on any error" (:228-229) | NO — `config.yml:4953` `enabled: false`; see §Legacy below | tests/test_ask_brain.py (module imported); re-enable contract engine/news_llm.py:13-19 |

Rows 1-3 are the evidence seam a Brief must read through; rows 4-11 are the editorial
Press/marketing lanes (scheduled, content-keyed); rows 12-16 are the live Brain serving paths
(user-keyed, quota-ledgered); rows 17-18 are existing brief-shaped read endpoints (deterministic);
rows 19-22 are budgeting/policy/idempotency primitives; rows 23-26 are R2 publication patterns;
row 27 is the legacy inference path (B6).

## Binding matrix

| binding | verdict at HEAD | deciding rows and lines |
|---|---|---|
| B1 shared durable Brief ARTIFACT owner | **PARTIAL** | Durable artifact stores exist for adjacent products — press staging + append-only published ledger (rows 5, 8: scripts/run_press.py:11,:48-50), marketing outbox JSONL (row 9: engine/marketing/outbox.py:13-17), immutable qbus revisions (row 2: engine/qbus_news_store.py:239), immutable R2 sidecars (row 23) — but no row owns an artifact whose identity is a *Brief* shared among entitled readers; the evidence adapter is contractually "not a second store" (docs/ops/shared-news-intelligence.md:22-23) and carries `publication_authorized: False` unconditionally (engine/qbus_news_context.py:37). MASTERPLAN.md:186 records the owner as unqualified; nothing at HEAD contradicts that. |
| B2 cross-process REQUEST owner | **PARTIAL** | Cross-process single-flight *primitives* exist: flock'd read-modify-write quota ledgers (row 12: engine/neuralweb/brain_gateway.py:9036-9060), atomic exclusive-create pre-call checkpoint that "cannot replay an unsettled provider effect" (row 5: scripts/run_press.py:543-555), append-only id-dedup with advisory flock (row 9), cross-account claim window (row 10: engine/marketing/story_lock.py:3,:125). But every key is content-, claim- or user-keyed; none maps one *demand* to at-most-one inference job. The only run registry is in-memory and single-worker (row 16: app/brain_runs.py:36,:193), and the press rail self-describes as "never... a separate execution queue" (scripts/run_press.py:546). |
| B3 conditional PUBLICATION operation | **PARTIAL** | Conditional, permission-aware, correction-safe publication exists per lane: press emit revalidation + revision correction markers (row 8: scripts/run_press.py:362,:456,:1165-1198) behind a workflow kill-switch and exact reviewed-bundle promotion (.github/workflows/press-publish.yml:123-126,:228-239); outbox no-walk-back state machine with recorded operator decisions (row 9: engine/marketing/outbox.py:7-9,:110); immutable R2 publish with conflict refusal (row 23). None is a publication operation over Brief artifacts: the Brief evidence seam is explicitly non-publisher (docs/ops/shared-news-intelligence.md:22-24), `publication_authorized` is hard-coded False (engine/qbus_news_context.py:37), and automatic publication of `internal_research` evidence to `site/intelligence/briefing.json` is withheld (docs/ops/shared-news-intelligence.md:765-769). |
| B4 enforceable PRE-CALL SPEND RESERVATION | **PARTIAL** | A genuine pre-call token reservation exists but only in-process, per run: `reservation = input_upper + max_tokens` recorded as `reserved_total_tokens` and refused preflight (row 7: engine/press/writer.py:863,:870,:881-883) against a `RunState` that is "one run, one state, one thread" (row 6: engine/press/writer.py:47-48). The durable cross-process ledgers reserve request COUNTS pre-call (rows 12-13) but settle TOKENS only after the call from provider-reported usage (row 14: engine/neuralweb/brain_gateway.py:32,:9391; engine/press/writer.py:991-996); ask_brain counts without a lock and fails open (row 15: engine/neuralweb/ask_brain.py:2444-2446). That is precisely the shape P1-B rejects: "Logging successful usage after a call is not admission" (MASTERPLAN.md:186). |

## Evaluation corpus (B5)

**NONE at HEAD.** `grep -rn -i -E "extractive baseline|bundle evaluation|60–100 bundle|60-100 bundle"`
over `research/` and `docs/` returns only the masterplan's own obligations:
MASTERPLAN.md:188 ("Use an extractive baseline and an injected adapter first, then compare
admitted models on the same rights-eligible corpus") and MASTERPLAN.md:379 (E4 dependency column:
"Extractive baseline, frozen 60–100 bundle evaluation, permission-aware reuse, cross-process dedup
and conditional publication"). No file matching a Brief evaluation corpus exists
(`find research contracts -iname "*brief*eval*" -o -iname "*brief*corpus*" -o -iname "*bundle*eval*"`
→ empty; no `brief_eval`/`brief_corpus`/`bundle_eval` references in `research contracts tests`).
Wave-3 sequencing confirms the corpus is downstream of the bindings, not present: "After concrete
runtime/artifact/budget bindings, build the shared Brief" (MASTERPLAN.md:416).

## Legacy default-off inference path (B6)

Path: `engine/news_llm.py` + `config.yml` (MASTERPLAN.md:196-204 P1-D; :648 S27).

- `config.yml:4952-4953`: `news_llm:` / `enabled: false` with the W5 P5 R3 comment "DEFAULT OFF —
  zero silent spend"; re-enable contract in the comment (config.yml:4958-4959) and the module
  docstring (engine/news_llm.py:13-19): a scored consumer in `config/qual_ladder.yml`, a qledger
  `claim_family` tag, then flip the flag.
- Activation semantics at HEAD: `enabled()` returns
  `bool(_cfg().get("enabled", False)) and _provider() is not None` (engine/news_llm.py:104) —
  off unless config explicitly sets true AND one of `CLAUDE_CODE_OAUTH_TOKEN` / `ANTHROPIC_API_KEY`
  / `DEEPSEEK_API_KEY` resolves (engine/news_llm.py:110-129). `annotate()` independently
  pass-throughs unless `cfg.get("enabled", False)` (engine/news_llm.py:242-243). The single caller
  is the nightly builder (scripts/build_news.py:120), which calls it unconditionally; the module
  gate makes it a no-op.
- Divergence from the audited text, recorded as fact: P1-D states "`enabled()` and another path
  use `.get("enabled", True)`" (MASTERPLAN.md:198). At HEAD **both** gates in `engine/news_llm.py`
  default `False` (:104,:242); the omission-defaults-True shape survives only in the separate
  press writer lane, `engine/press/writer.py:824` (`llm_cfg.get("enabled", True)`), whose config
  block is `config/press.yml:368-369` (`llm: enabled: true`) — a different, explicitly enabled
  lane, not the legacy news path.
- The masterplan sentence forbidding its use for the Brief service, MASTERPLAN.md:202:

> Do not switch on this legacy path to implement the new Brief service. [S27]

## Owners outside this repository

| owner | binding | the masterplan/ops line naming it | what this census cannot see |
|---|---|---|---|
| Runtime job admission / capacity placement (commissioning packet's "Executive OS") | B2 (job admission), B4 (budget placement) | MASTERPLAN.md:288 "Actual placement and concurrency come from existing Capacity/runtime admission"; :565 "Actual receiver placement and concurrency belong to existing Capacity/runtime owners" | whether any runtime admission plane exists in a given form, its queues, or its identity keys — none is in this tree |
| Capacity/Model Router (model/budget placement) | B4 | MASTERPLAN.md:222/:577 "this report does not authorize new stores, graph owners, model routers, queues, publication systems" — the router is named as an existing external owner, not described | current routing tables, accounts, or budget contracts |
| Terminal Brief UI (Terminal #1081) | B1/B3 (the Brief reader and its tab) | MASTERPLAN.md:78 "#1081 remains Draft... qualify the new sidebar independently of Brief"; :186 "before enabling the endpoint or adding a Brief tab"; :535 "Terminal #1081... Brief remains separately unbuilt"; :621 (S06); :632 (S14 — the Shared Brief design assessment lives at a Terminal-repo path) | the Terminal assessment document itself, its draft state, and any Terminal-side artifact or publication surface |
| Mastermind artifact stores / consumers | B1 (artifact reuse readers) | MASTERPLAN.md:89 (§2.1 "Mastermind tools and assessments... `brain/bot_mcp.py::get_intelligence`"); D1_NEWS_INPUT_TRACE.md:137-157 classifies the Mastermind consumers from excerpts only | Mastermind HEAD beyond the excerpt set; whether any Mastermind-side store could host a shared Brief artifact — asserted nowhere in this repo |

## Gaps for E4

Each gap is an evidence gap at HEAD, phrased against the rows it extends; none proposes an
implementation.

1. **G-B1 (extends rows 2, 5, 8, 9, 17, 23).** No committed record at HEAD carries a *Brief*
   artifact identity with its audience scope and reader set. Press staging records are
   press-desk slots (scripts/run_press.py:608), outbox items are marketing posts
   (engine/marketing/outbox.py:13-17), the portfolio brief is composed per-request and cached
   in-process only (app/main.py:2033-2035), and the evidence seam disclaims storage
   (docs/ops/shared-news-intelligence.md:22-23; engine/qbus_news_context.py:37). No line anywhere
   evidences who owns a Brief artifact shared across Macro/Terminal/Mastermind readers.
2. **G-B2 (extends rows 5, 9, 10, 12, 16).** No mechanism keys inference work by *request*
   identity across processes. Story dedupe is content-keyed (engine/press/desk_planner.py:1104;
   engine/marketing/story_lock.py:16-18), quota ledgers are user/lane-keyed
   (engine/neuralweb/brain_gateway.py:15-17), and the only run registry is process-local
   (app/brain_runs.py:193). No line evidences a demand→job mapping, so the P1-B :184 requirement
   ("News arrival, page opening or ticker changes... should not create inference work by
   themselves") has no existing enforcement owner to bind.
3. **G-B3 (extends rows 1, 8, 9, 11, 23).** No publication operation takes a Brief artifact and
   an audience and decides permission-aware, revision-invalidating publication. Existing
   refusals are lane-specific (scripts/run_press.py:1165-1198), the evidence bundle hard-codes
   `publication_authorized: False` (engine/qbus_news_context.py:37), and automatic publication of
   `internal_research` evidence is withheld in prose (docs/ops/shared-news-intelligence.md:765-769).
   The §5.4 correction rules (MASTERPLAN.md:261-263) have no Brief-side enforcement line.
4. **G-B4 (extends rows 6, 7, 12-15).** No durable, cross-process pre-call token/cost reservation
   exists. The only pre-call reservation is per-run in-process (engine/press/writer.py:47-48,:863-883);
   every durable path settles tokens after the call (engine/neuralweb/brain_gateway.py:32,:9391)
   and one durable counter is unlocked and fail-open (engine/neuralweb/ask_brain.py:2444-2446).
   MASTERPLAN.md:186's rejection of post-call logging as admission therefore still describes
   every durable path at HEAD.
5. **G-B5.** No frozen evaluation corpus is committed (§Evaluation corpus; only the obligations at
   MASTERPLAN.md:188,:379), so "compare admitted models on the same rights-eligible corpus"
   (MASTERPLAN.md:188) has no substrate at HEAD.
6. **G-B6 (record drift).** P1-D's audited claim that the gates default True
   (MASTERPLAN.md:198) is not the HEAD state of `engine/news_llm.py` (:104,:242 both default
   False); the default-True omission shape lives only in the press writer
   (engine/press/writer.py:824). No record at HEAD reconciles the audited source with the
   repaired file, the P1-C drift class (MASTERPLAN.md:190-194) applied to P1-D.

## What this census is not

No design, no proposed owner, queue, store, budget, cache, endpoint, schema or publication path;
no activation of any legacy path; no acceptance, ranking or sizing authority over any mechanism
recorded; no opinion on which mechanism SHOULD be chosen; no reading of credential files; no
`data/` or `site/` tree reads; no code change. Row "binding" labels are census classifications of
what a mechanism could serve, not admissions for Brief use.

## Evidence

Commands run at HEAD `19c31737672217939906b3861682e40de57d2395` (output summarized to the cited
lines; no whole-file dumps):

1. `git rev-parse HEAD`; `git status --porcelain` (empty); `git branch --show-current`
   (`lane/news-w4-e4-bindings-r1`); `mkdir -p ~/lanes/tmp/news-w4-e4-bindings-r1`.
2. `sed -n` reads: MASTERPLAN.md 70-99, 178-209, 255-272, 374-383, 412-421, 598-605, 644-651;
   docs/ops/shared-news-intelligence.md 14-27, 743-792; A1_SOURCE_DELIVERY_MATRIX.md 122-141;
   D1_NEWS_INPUT_TRACE.md 105-134, 137-160.
3. `test -f` loop over all 20 inventory files → all OK, none MISSING; `ls engine/press/`.
4. Spec grep per file (`grep -c -i -E "budget|spend|reserv|cost|token|grant|audience|rights|publish|emit|refus|dedup|idempot|request_id|job_id|single|lock|revision|supersed|invalidat|correct"`) — counts in §Scope; `grep -c news_llm config.yml` → 6.
5. `engine/qbus_news_context.py`: full read (56 lines); `engine/qbus_news_store.py` greps
   (evidence_for_security :1923; sed 1923-1975; news_revisions :239; current_revision_id :1953);
   `engine/qbus_news_receipts.py` structure grep (:30,:49,:117,:156-161,:198,:454,:474,:488).
6. `engine/press/qbus_news.py` sed 195-240 (prepare_slot :211, audience blog_draft :221,
   PrivateNewsUnavailable :224).
7. `engine/press/desk_planner.py`: def map; sed 1071-1260 (_plan_brief: cap :1093, alias block
   :1100-1104, revision receipt gate :1118-1127, identity_parts :1168-1178); `_allowed_links` :1226-1243.
8. `engine/press/writer.py`: sed 40-110 (RunState :47-48, can_start :63, admitted bounds :42,
   :92-104); sed 795-900 (enabled gate :824, reservation :863, reserved_total_tokens :870,
   preflight :876, mute warning :930-936); sed 900-975 (`_admit_private_call` :956-964,
   charge(reported :993); `_provider_usage` :113).
9. `scripts/run_press.py`: sed 1-110 (mode contract :16-18, emit :21-25, ledger :48-50, canonical
   markers :95-107); grep lock/attempt/checkpoint; sed 540-566 (`_write_stage_checkpoint`
   :543-555); sed 600-655 (pre-call checkpoint :611, before_write :640-649); grep emit refusals
   (:1165,:1179,:1198), reconcile (:362,:456), auto_emit_allowed (:514).
10. `.github/workflows/press-publish.yml`: grep + sed 56-66, 225-240 (cron :63; kill-switch
    :123-126; promotion gates :228-239; "emit requires an exact committed reviewed bundle" :178-189).
11. `engine/news_llm.py`: full read (306 lines) — enabled() :100-104, annotate gate :242-243,
    providers :110-129, re-enable contract :13-19; `grep -n "get(\"enabled\", True)"` over
    news_llm.py + writer.py → only writer.py:824; `config.yml` :4952-4959; `config/press.yml`
    :368-376; llm_models :21,:25; callers scripts/build_news.py:100-125.
12. `engine/neuralweb/brain_gateway.py`: header read 1-74; def map; sed 9036-9110 (_held_quota_locks,
    _read_quota); sed 9148-9300 (_check_and_increment_quota); sed 9380-9440 (_record_token_usage);
    ceilings :168-169, :8991-9019, :9261; record_usage sites :14072,:14183,:14288,:14624.
13. `app/main.py`: greps (ask_brain :1353-1366, /api/brain/chat :1639, brain_runs wiring :1455-1475,
    portfolio brief :2023-2200 sed: cache :2041-2042, Pro gate :2160-2165, cache hit :2189).
14. `app/brain_runs.py` structure grep (:36,:62,:193,:214,:323-332);
    `app/prophet_daily_brief.py` sed 55-105 (:69-71,:148);
    `engine/neuralweb/ask_brain.py` :55-110, :2436-2481.
15. `engine/marketing/`: outbox.py sed 1-60 + greps (:110,:113,:176,:360,:570,:1676);
    story_lock.py header + owner_of (:1-3,:16-18,:23-26,:31,:51-54,:125-139); authority.py
    (:48,:63,:100,:117-119,:126,:142-144); desk_feed.py (:6-9,:95,:171).
16. `scripts/marketing_publisher.py` header (:1-36); `scripts/close_pass_publish.py`
    (:1-29,:56-58,:67); `scripts/publish_company_theme_exposure_r2.py` (:1-3,:26,:113-128);
    `scripts/mirror_terminal_context_r2.py` (:16-19,:106,:122); `scripts/fetch_r2.py`
    (:19,:24-27); `scripts/audit_r2.py` (:1-8,:32).
17. Workflow triggers: marketing-publish.yml (:13-14,:33-58), close-pass.yml (:147-149),
    earnings-story-press-stage.yml (:54), ci.yml run_press paths (:3046).
18. B5: `grep -rn -i -E "extractive baseline|bundle evaluation|60–100 bundle|60-100 bundle"
    research/news_intelligence_estate_20261021 docs` → MASTERPLAN.md:188,:379 only;
    `find research contracts -iname "*brief*eval*" -o -iname "*brief*corpus*" -o -iname
    "*bundle*eval*"` → empty; `ls research/news_intelligence_estate_20261021/`.
19. Test pins: `grep -rln/-n` over tests/ for each mechanism —
    test_shared_news_intelligence.py:72-222 (:159,:199); test_brain_gateway_quota_safety.py:102-199;
    test_press_writer.py:496-500,:555-573; test_press_run.py:157-377 (:173,:253,:284);
    test_marketing_outbox.py:89-244; test_ask_brain.py:303-347; test_portfolio_brief.py:204-269;
    test_prophet_daily_brief.py; test_marketing_earnings_call_lane.py /
    test_marketing_press_relay_quality.py (story_lock); test_marketing_approval_desk.py
    (publisher); test_brain_streaming.py (brain_runs); test_chronicle.py:470-500 (context_pack);
    test_context_index_packet.py; test_close_pass_host_runner.py;
    test_publish_company_theme_exposure_r2.py; test_sni_public_exposure.py (fetch/audit_r2);
    test_company_intelligence_refresh.py (mirror).
20. Out-of-tree owner lines: `grep -n` MASTERPLAN.md for capacity/runtime (:288,:565), router/
    publication systems (:222,:577), #1081/Brief tab (:78,:136,:186,:535,:621,:632);
    D1_NEWS_INPUT_TRACE.md:137-157.
