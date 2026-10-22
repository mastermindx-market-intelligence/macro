# A5 — Transport / coverage observability gaps (News Intelligence Estate)

BASE 64ef5131a5f50fb65f0ad25a049a457e18258495 · census 2026-10-22 · census at BASE; no live probe; RETAINED receipts are dated, never asserted as current.

**A1 seed read (read-only):** branch `lane/ne-a1-matrix-20261022-r1` at `a3964f812d48db844ea7cb362632ed26a652a145` (`git fetch origin` + `git show FETCH_HEAD:research/news_intelligence_estate_20261021/A1_SOURCE_DELIVERY_MATRIX.md`); its content matched the inline packet copy. Row labels for §3 below follow A1 §2.1–§2.11. No provider, VPS, R2 or service was contacted; no credential was read; data/ and site/ are omitted from this sparse worktree and were never materialized.

**Cite legend.** `H` = engine/qbus_news_receipts.py · `R` = scripts/run_qbus_news.py · `API` = app/ticker_news.py · `I` = engine/qbus_news_intake.py · `BZ` = collectors/benzinga_news.py · `AL` = collectors/alpaca_news.py · `MV` = engine/massive_news.py · `GD` = engine/gdelt_client.py · `RSS` = engine/news_rss.py · `CB` = collectors/base.py · `A1 §x` = the seed file above. Mode keys: **Q** quiet-vs-outage · **C** cursor/page gap · **A** auth expiry · **S** schema drift · **B** poll-budget saturation · **R** reconnect. All `file:line` cites were read at BASE; §4 below spot-verifies ten of them against the cited lines.

The estate has exactly one durable transport-health artifact family: the writer's `qbus.news_health.v1` receipt (`H:25`, written `R:201-232`, conservatively re-projected `H:249-330`, served `API:357-372`) plus the collect lane's tracked `data/run_status.json` (`CB:24,121-128`). Everything else in Families B–K degrades to log lines. The nine gaps below (G1–G9) are all closable inside those two existing surfaces; none needs a new store, router, scheduler, queue, daemon or registry.

---

## 1. Summary

| # | mode | EXISTS | primary evidence | MISSING (short) | proposal size |
| --- | --- | --- | --- | --- | --- |
| 1 | quiet-vs-outage | partial | API:404-421 (`quiet` derivation); H:305-321 (stale→unavailable/degraded) | per-source fetch-outcome health for nightly Families D–K; observation-age for `additional_sources` (G1, G2) | M |
| 2 | cursor/page gap | partial | BZ:303,313-317 (budget→gap, cursor frozen); I:80-97 (checkpoint/overlap, `page_budget_exhausted`) | gap-episode timestamps; any cursor observable for Families D–K (G3, G4) | S |
| 3 | auth expiry | partial | H:156-161 (receipt `expires_at`); API:339-344,614 (per-request revalidation→503) | pre-failure expiry countdown in receipts/inventory; auth-specific WS classification (G5, G6) | S |
| 4 | schema drift | partial | contract codes engine/qbus_news_contract.py:283-312; counted R:313-315,344-345 | drift/ignore/gap counters are process-memory + exit-receipt only, absent from the served health receipt (G7) | S |
| 5 | poll-budget saturation | partial | AL:150-158,174-183,283-284 (429 ladder + `backoff_active`); GD:36-51,116,139 (breaker) | catch-up duration/overrun measurement; 429/backoff counters; breaker state in any receipt (G8) | S |
| 6 | reconnect | partial | R:429-446 (disconnect count + backoff), :215-216 (served counters); API:1094,1083-1086 (reader resume + heartbeat) | disconnect→reconnect latency; reader-side missed-event observable across a drop (G9) | S |

Eight of nine gaps are single-file-or-two S-sized changes to files that already exist; G1 is M because it touches three nightly modules plus one aggregation write. Gap count: **9**. Bounded build proposals: **6** (§2).

---

## 2. The six failure modes

### 2.1 Quiet versus outage — can the estate tell "provider had no news" from "our transport is down"?

**(a) EXISTS TODAY.**
- The writer receipt carries two independent freshness clocks — `last_successful_catchup` (REST path) and `last_stream_event_at` (push path) — plus state and `gap_unresolved` (`R:201-221`). `parse_health_receipt` then projects them conservatively: observation older than 120 s → `unavailable/receipt_stale`; unresolved gap → `degraded`; fresh catch-up with no story is still allowed to be `live` (`H:305-321`, pinned by `test_fresh_health_can_be_live_without_recent_story_when_catchup_is_fresh`, tests/test_qbus_news_receipts.py:136).
- The API turns that into a user-visible `quiet` state exactly at the quiet-vs-outage seam: writer `live` + zero rows for the ticker → `quiet`; writer `unavailable` but a supplemental source available → `quiet` or `degraded` by row count (`API:404-421`), embedded as `source_health` in every snapshot (`API:802`) and tested (`test_live_source_with_no_ticker_rows_reports_quiet`, tests/test_ticker_news_api.py:279). Quiet SSE streams emit heartbeat comments so a quiet connection stays distinguishable from a dead one (`API:1083-1086`; test at tests/test_ticker_news_api.py:350).
- Supplemental Massive intake reports its own `state` + `last_successful_poll` + `last_error` inside `additional_sources` of the same receipt (`R:220`, `I:144-154`), and receipt validation pins the extra-state vocabulary (`H:351`).
- Collect-lane families (B, F, G, H, J) have a per-adapter outcome record with status `ok|stale|failed|dead|skipped|blocked` in the tracked `data/run_status.json`, a 3-strike circuit breaker with a 20 h half-open probe, and a frozen-tail detector (`CB:121-128`, `CB:21,117`, `CB:300-319`).

**(b) MISSING.**
- **G1 — no per-source health artifact for the nightly build families (D: RSS/Google-News/official feeds, GDELT artlist).** `RSS._fetch` degrades to `log.debug` and returns None identically for "feed empty" and "feed unreachable" (`RSS:110-118`); `build_news` logs module-level failures only (scripts/build_news.py:171,189,216). Quiet and outage are indistinguishable by construction for every D row.
- **G2 — `additional_sources` carry no writer observation age.** Extra states are validated (`H:351`) but never age-projected the way the primary receipt is (`H:305-321`); the API's only cross-check is state equality (`API:410-413`). A supplemental lane whose writer thread died keeps its last `available` forever. (The existing test at tests/test_qbus_news_receipts.py:273 rightly forbids *inventing upstream recency*; the missing field is the writer's own `observed_at`, which is writer-side evidence, not an upstream claim.)

**(c) BOUNDED BUILD PROPOSAL.** Two edits, no new surface. (1) Add `observed_at` to `SupplementalNewsIntake.health()` (`I:144-154`) and have `parse_health_receipt` project each extra's age with the same 120 s budget used for the primary (`H:249-330`), surfacing `degraded/stale_supplemental` through `_curated_health` (`API:390-402`). (2) Reuse the collect lane's existing health artifact shape for the nightly families: have `RSS._fetch`, the GDELT caller and `macro_news` return a per-source outcome (`FetchResult`-shaped, `CB:121-128` — status/error/last_date, no new schema) and aggregate them in `scripts/build_news.py` into the already-tracked `data/run_status.json` under a `news_feeds` key (the file already exists as the nightly health surface; this adds a section, not a store). Files changed: engine/qbus_news_intake.py, engine/qbus_news_receipts.py, app/ticker_news.py, engine/news_rss.py, engine/gdelt_client.py, scripts/build_news.py. Discriminating test: a feed whose HTTP fetch raises and a feed that returns 200 with zero items must produce different statuses (`failed` vs `ok` with `rows=0`) in the `news_feeds` section — the quiet/outage seam, asserted per source.

### 2.2 Cursor / page gap — is a missed page, cursor reset or truncated window detected and recorded?

**(a) EXISTS TODAY.**
- Primary REST catch-up is budget-aware end to end: page families return an exhaustion flag (`BZ:252-275`), `fetch_delta` turns it into `gap_unresolved` + `hold_reasons` `news_page_budget_exhausted`/`removed_page_budget_exhausted` and **freezes the cursor** at the old base instead of advancing past unobserved content (`BZ:313-317`), and every window re-reads `overlap_seconds` of history (`BZ:303`). The same DeltaBatch contract is shared by the Alpaca transport, including its page-token budget and identical cursor freeze (`AL:262-327`, overlap `AL:103,293`).
- A gap is not only detected but held and replayed exactly once: `apply_catch_up_batch` commits a cursor-only hold when gapped (`BZ:412-434`), the runner counts it (`R:270-273`), the receipt goes `degraded/gap_unresolved` (`H:308-309`), and the replay tests prove exactly-once overlap redelivery, gap-holds-cursor, null-cursor lookback retention, and failure-without-hole (`test_overlap_redelivery_is_exactly_once` :331, `test_page_budget_gap_holds_cursor_until_later_catchup` :445, `test_null_cursor_gap_keeps_lookback_base_across_a_later_catchup` :477, `test_failed_catchup_holds_cursor_and_recovery_leaves_no_hole` :633 — all tests/test_run_qbus_news_gap_replay.py).
- Store-level CAS: a concurrent commit surfaces `CursorConflict` instead of a silent overwrite (`engine/qbus_news_store.py:1582-1584`); every commit returns a `CommitReceipt` with inserted/duplicate/stale/conflict/applied/withdrawn counters (`engine/qbus_news_store.py:143-155`).
- Supplemental Massive intake checkpoints `checkpoint/since/through/next_url/publishers` in the cursor, refuses to advance the checkpoint when the page budget is exhausted (`page_budget_exhausted`, `I:80-97`), resumes the exact `next_url` continuation (`I:127-131`), and rejects malformed cursors (`invalid_supplemental_cursor`, `I:133-135`); tests pin continuation and revocation (`test_page_budget_resumes_exact_continuation_without_advancing_completed_coverage`, tests/test_qbus_news_intake.py:110).
- Reader side: `ticker_news.changes.v1` exposes `next_sequence`/`has_more` (`API:835-845`) so a client can detect its own gap.

**(b) MISSING.**
- **G3 — the gap episode itself is unrecorded.** `gap_unresolved` is a bool (`R:214`); there is no `gap_first_seen_at`, no cleared-at, no episode duration. When the flag clears (`R:275-281`), the outage window is unrecoverable from any artifact; `catchups_gap` reaches only the process-exit receipt (`R:69-70,715`).
- **G4 — Families D–K have no cursor observable at all.** RSS/GDELT windows are re-fetched by recency (`RSS:274-285`) with no checkpoint; a failed nightly build leaves a silent hole with no last-position record.

**(c) BOUNDED BUILD PROPOSAL.** Add `gap_first_seen_at` (and clear it) beside `gap_unresolved` in `_health_payload` (`R:201-221`), validate it like the other optional times (`H:268-274` pattern), and let it flow to readers untouched through `_source_health` (`API:357-372`). For G4, the §2.1 `news_feeds` outcome record carries `last_complete_window` per source in the same `run_status.json` write. Files changed: scripts/run_qbus_news.py, engine/qbus_news_receipts.py, app/ticker_news.py (passthrough only), plus the §2.1 aggregation for D–K. Discriminating test: two consecutive degraded receipts carry an identical `gap_first_seen_at`, and the first healthy receipt after carries `null` — episode boundary observable without a new store.

### 2.3 Auth expiry — is credential/entitlement expiry or a 401/403 surfaced before delivery silently stops?

**(a) EXISTS TODAY.**
- Rights receipts carry `effective_at`/`expires_at` and fail closed: an expired or malformed receipt loads as None (`H:46,156-161`; `test_rights_file_loader_missing_invalid_or_expired_is_none`, tests/test_qbus_news_receipts.py:122). The writer refuses to start on an unqualified/expired receipt, no network, via `--check-activation` (`test_cli_check_activation_fails_closed_on_expired_rights`, tests/test_run_qbus_news_health.py:469).
- The reader revalidates per request with `now=...` (`API:339-344`) and maps missing rights to 503 (`API:614`); streams emit explicit `ticker_news.restricted.v1` events instead of silently continuing (`API:1026-1035,1072-1075`). Supplemental intake revalidates rights **between network submission and durable write** and lands in `restricted`/`rights_unavailable` on revocation (`I:44-50,65-70,112-115`; tests at tests/test_qbus_news_intake.py:96,141,203).
- Provider-side rejection is code-classified: Benzinga REST raises `http_{status}` (so 401/403 are visible codes, `BZ:135-142`), Massive raises `MASSIVE_AUTH_REJECTED` for 401/403 (`MV:58,167-172`) which the intake preserves verbatim as `last_error` (`I:99-102`), and both reach the served receipt as `last_catchup_error`/`additional_sources[].last_error` (`R:218-220`).

**(b) MISSING.**
- **G5 — no pre-failure expiry observable.** Nothing surfaces "rights expire in N days": the receipt and the inventory carry state, never `expires_at` (inventory loads the rights receipt at scripts/ticker_news_inventory.py:280-297 but reports only `rights_unavailable` on failure). Expiry is discovered at the first failing request or preflight.
- **G6 — stream-path auth failures are unclassifiable.** A WS connect failure yields only the class-name fallback `exception_*` (`R:121-126`); a revoked key that manifests as a dropped handshake is indistinguishable from a network fault in `last_stream_error`.

**(c) BOUNDED BUILD PROPOSAL.** (1) Add `rights_expires_at` (min across the loaded receipts, which the runner and inventory both already load — `R` main wiring, scripts/ticker_news_inventory.py:287-297) to the health payload and the inventory's rights section; `_curated_health` passes it through unchanged. This is a field on an existing receipt kind, not a new artifact. (2) For G6, map `handshake`/`denied`-class stream errors to a stable `stream_auth_rejected` diagnostic code at the connect site before `_error_code` fallback. Files changed: scripts/run_qbus_news.py, engine/qbus_news_receipts.py (validation), scripts/ticker_news_inventory.py, app/ticker_news.py (passthrough). Discriminating test: a receipt whose `rights_expires_at` is in the past parses to state `restricted` at the API projection (`API:404-421` extension) rather than `live` — expiry surfaces before any delivery stop.

### 2.4 Schema drift — is an upstream payload shape change rejected, counted and surfaced, or silently dropped?

**(a) EXISTS TODAY.**
- The contract layer rejects with typed codes, never silently: `normalize_news` raises `unsupported_transport/invalid_payload/invalid_kind/invalid_content/source_item_id_mismatch/...` (engine/qbus_news_contract.py:283-312 and the field validators :72-175), and Massive poll carries `MASSIVE_MALFORMED_RESPONSE`/`MASSIVE_ROW_MALFORMED`/`MASSIVE_PAYLOAD_TOO_LARGE` (`MV:60-65`).
- Drift is counted on both transports: malformed/oversized stream frames and normalization failures increment `stream_errors`; non-news frames increment `stream_ignored` (`R:313-315,323-328,344-345`); a catch-up contract failure increments `catchups_failed` and records the code in `last_catchup_error` (`R:262-263`) — which **is** served in the receipt (`R:218`). Commit-level surprises are counted per commit in `CommitReceipt` (`engine/qbus_news_store.py:143-155`) and reducer dispositions (`stale`/`conflict`/`withdrawn`) are distinguished (`engine/qbus_news_store.py:1620-1698`).
- Collect-lane families have column-contract checks with alarms (`CB:462-470` region, `CB:505-548`) writing `dark_columns` to run_status.

**(b) MISSING.**
- **G7 — the drift counters are not in the served receipt.** `stream_errors`, `stream_ignored`, `catchups_gap` and `health_write_failures` exist in `RunnerStats` (`R:57-66`) but `_health_payload` serializes only `connect_attempts/disconnects/catchups_failed` (`R:215-217`); the rest survive only in the `qbus.news_runner_exit.v1` receipt printed at shutdown (`R:69-70,715`). A drift storm in progress is invisible to the API and the inventory; and drift is not distinguishable from transport flapping (one lumped `stream_errors`).

**(c) BOUNDED BUILD PROPOSAL.** Publish the four existing counters: add them to `_health_payload` (`R:201-221`) and to `parse_health_receipt`'s validated non-negative integers alongside `connect_attempts` (`H:291-301` pattern), then extend the count of published fields in `parse_health_receipt`'s result dict (`H:322-345`). No new receipt kind; the API and inventory surface them automatically via the existing load path. Files changed: scripts/run_qbus_news.py, engine/qbus_news_receipts.py. Discriminating test: feed the runner 50 malformed frames then one valid frame → receipt shows `stream_errors=50` while `last_stream_error` stays null and state remains `live`; and `parse_health_receipt` rejects a negative counter (`health_connect_attempts` precedent, tests/test_qbus_news_receipts.py:213).

### 2.5 Poll-budget saturation — are rate limits, 429s and poll-interval overruns measured?

**(a) EXISTS TODAY.**
- The Alpaca REST client runs a real 429 ladder with `Retry-After` honor, doubling 60 s→900 s cap, reset on success, and a hard `backoff_active` guard that turns saturation into a *visible catch-up failure* (`AL:34-37,150-158,174-193,283-284`); `test_backoff_active_is_a_failed_catchup` proves the saturation path is observable (tests/test_run_qbus_news_gap_replay.py:739). Benzinga REST propagates `http_{status}` + `Retry-After` (`BZ:135-142`), Massive classifies 429 as `MASSIVE_RATE_LIMITED` (`MV:59,170-171`) which lands as intake `last_error`.
- GDELT (nightly families) has the strongest budget telemetry outside qbus: a 30 s/75 s retry ladder, a cross-process breaker stamp `data/gdelt/rate_limit_until` with a 900 s configurable cooldown, an explicit `rate_limited` return sentinel, and a cross-process pace gate (`GD:36-51,102-123,139-155`, `wait_turn` at `GD:188+`).
- The intake poll cadence is bounded (60 s interval, `I:23,25-26`) and budget exhaustion is a named state (`page_budget_exhausted`, `I:95-97`). The reader API rate-limits per user with 429 + `Retry-After` (`API:248-255`).

**(b) MISSING.**
- **G8 — the loop's own budget is unmeasured.** Nothing records catch-up *duration* against the 30 s `catchup_interval_seconds` (`R:143`): an overrun that silently converts the design's "30 s catch-up" into "back-to-back catch-up" is unobservable. The Alpaca backoff state (`_backoff_until`, ladder step) is client-private — saturation appears only as an opaque `last_catchup_error="backoff_active"`, with no 429 counter or remaining-cooldown field. The GDELT breaker state is readable only by opening the stamp file; no health artifact carries it.

**(c) BOUNDED BUILD PROPOSAL.** Add `last_catchup_duration_seconds` + `catchup_overruns` (durations > interval) to `RunnerStats`/`_health_payload` (measure around the existing `_catch_up`/`_drain_catchup` calls, `R:245-299`), and a `last_429_at`/`backoff_until` field to the intake health dict (`I:144-154`) fed from the client's existing ladder state. Publish the GDELT breaker's armed-until timestamp into the §2.1 `news_feeds` outcome when a build short-circuits (`GD:124-134` read is already fail-open). Files changed: scripts/run_qbus_news.py, engine/qbus_news_receipts.py (field validation), engine/qbus_news_intake.py, engine/gdelt_client.py (emit only). Discriminating test: a stubbed client whose fetch sleeps longer than `catchup_interval_seconds` yields `catchup_overruns=1` in the receipt while state stays `live` — saturation without failure becomes visible.

### 2.6 Reconnect — when a stream drops and resumes, is the resume position and its gap observable?

**(a) EXISTS TODAY.**
- Writer side: `connect_attempts` and `disconnects` are cumulative counters *served in the receipt* (`R:215-216`); each drop publishes `degraded` (or `catching_up` pre-first-catch-up) with `last_stream_error` (`R:427-435`); reconnect uses exponential backoff 1 s→60 s reset on success (`R:143-146,367,402,445-446`); receipt parsing rejects future timestamps and stale observations, so a dead writer cannot look connected (`H:283-287,305-307`). `test_runner_publishes_catchup_stream_disconnect_and_exit_health` pins the drop path (tests/test_run_qbus_news_health.py:127).
- Reader side: SSE resumes from an explicit `after_sequence` parameter (`API:1094`), the generator advances its sequence cursor monotonically (`API:1080,1088`), quiet periods emit heartbeats inside the edge idle budget (`API:1083-1086`), and view/permission changes are explicit `reset`/`restricted` events rather than silent truncation (`API:1005-1007,1020-1035,1062-1069`). `next_sequence` on the changes endpoint gives the durable catch-up position (`API:835-845`).

**(b) MISSING.**
- **G9 — no reconnect latency and no missed-event observable.** Timestamps of the last disconnect and of the next successful connect are not recorded (only cumulative counts), so "how long were we dark" is unrecoverable; and on the reader side nothing quantifies events missed between the last delivered sequence and the resume point (the client *can* bridge via `/changes`, but no field tells it whether it should).

**(c) BOUNDED BUILD PROPOSAL.** Add `last_disconnect_at`/`last_connect_at` (derived from the existing `clock()` around the connect loop, `R:380-425`) to `_health_payload`; on the reader, echo `replayed_from_sequence` in the first `ticker_news.snapshot.v1`/changes response after a stream reconnect is out of scope for the writer — instead expose `snapshot.change_sequence` (already present, `API:797`) as the client's gap check and document the contract in the same test. Files changed: scripts/run_qbus_news.py, engine/qbus_news_receipts.py (two optional-time fields), app/ticker_news.py (doc/passthrough only). Discriminating test: a runner whose first connect raises and second succeeds produces a receipt where `last_connect_at − last_disconnect_at ≥ reconnect_base_seconds`, parsed and projected by `parse_health_receipt` (tests/test_run_qbus_news_health.py:127 extension).

---

## 3. Per-source coverage grid

Rows are the A1 §2.1–§2.11 row labels (36 enumerated labels; the seed's summary says "35 source rows" — the delta is a counting-convention question, §5). Cells: **covered** (durable/readable artifact at BASE) · **partial** (in-memory, log-line, or fail-closed-only) · **none** (nothing found — greps listed in §2 apply estate-wide: `receipt|source_health|health|last_success|last_error|cursor|next_page|page_token|since|rate|budget|429|retry|backoff|reconnect|websocket|stream|expires|401|403|auth|schema|validate|drift|quiet|stale|heartbeat`). `A1 §x` cites mark cells evidenced by the seed rather than re-read here.

| # | A1 row (§) | Q | C | A | S | B | R |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | Benzinga direct — benzinga_rest+benzinga_ws (§2.1) | covered (R:201-221; API:404-421) | covered (BZ:303,313-317; tests gap-replay :445) | partial (BZ:135-142 REST codes; WS fallback R:121-126) | partial (contract codes; counters exit-only R:69-70) | partial (BZ:101-114 budget; no overrun measure) | covered (R:215-216,429-446) |
| 2 | Benzinga via Alpaca — alpaca_rest+alpaca_ws (§2.1) | covered (same receipt; A1 §2.1 RETAINED readbacks) | covered (AL:262-327 gap+freeze; R:693 cursor ns) | partial (AL:180-186 http codes; no expiry countdown) | partial (AL protocol errors → stream/catchup counters) | partial (AL:150-158,174-183,283-284 ladder; no counter in receipt) | covered (R:215-216,429-446) |
| 3 | Benzinga-on-Massive — massive_benzinga_v2 (§2.1) | none (no wired runner, A1 §2.1) | none (no wired runner) | none (no transport grant) | partial (contract admits transport, qbus_news_contract.py:283-289) | none | none |
| 4 | massive:zacks.com (§2.1) | covered (I:144-154 via R:220; API:410-413) | covered (I:80-97,126-135) | partial (I:65-70 rights; MV:58,167-172 auth code) | covered (MV:60-65 → I:99-102 durable last_error) | partial (I:95-97 budget state; no 429 counter) | none (polled — no stream) |
| 5 | massive:fool.com (§2.1) | covered (same intake health) | covered (same intake cursor) | partial (same rights/auth codes) | covered (same) | partial (same) | none (polled) |
| 6 | massive:globenewswire.com (§2.1) | covered (same intake health) | covered (same intake cursor) | partial (same) | covered (same) | partial (same) | none (polled) |
| 7 | massive:&lt;other domain&gt; (§2.1) | partial (mechanism only; fail-closed qkernel, A1 §2.1) | partial (same mechanism) | partial (no receipt → restricted, I:112-115) | partial (same contract) | partial (same) | none (polled) |
| 8 | Polygon news sentiment (§2.2) | partial (CB:121-128 run_status; polygon blocked without key, collectors/polygon_news.py:140-142) | none (daily snapshot, no cursor; A1 §2.2) | partial (key-absent → blocked, :140-142) | partial (column contract CB:462-470 region) | partial (tier budget probe, A1 §2.2) | none (nightly) |
| 9 | Tiingo REST + BOATS archive (§2.3) | partial (receipt identity/validation per response, collectors/tiingo_archive.py:180-190) | none (external-drive archive, no cursor) | partial (token env/key file, A1 §2.3) | partial (validate_receipt raises, :185-190; no counter) | none | none (session-driven; no reconnect telemetry, A1 §2.3) |
| 10 | Publisher direct RSS (§2.4) | partial (degrade log only, RSS:110-118) | none (recency re-fetch, RSS:274-285) | none (keyless) | partial (parse guards, RSS:160-162) | none | none |
| 11 | Google-News RSS aggregation (§2.4) | partial (same RSS degrade) | none | none (keyless) | partial (same) | none | none |
| 12 | Official agency RSS OFFICIAL_FEEDS (§2.4) | partial (same degrade path, A1 §2.4) | none | none (keyless) | partial (same) | none | none |
| 13 | financial_news per-name/ETF/sector (§2.4) | partial (same) | none | none | partial (same) | none | none |
| 14 | special-situations / special_intl RSS (§2.4) | partial (same) | none | none | partial (same) | none | none |
| 15 | GDELT artlist funnel (§2.4) | partial (`rate_limited` sentinel GD:38; breaker stamp GD:119-123) | none | none (keyless) | partial (parse degrade logs) | covered (GD:36-51,116,139-155 ladder + cross-process breaker + wait_turn GD:188+) | none |
| 16 | GDELT timeline — HK (§2.4) | partial (breaker shared) | none | none | partial | partial (wait_turn pace gate GD:188+) | none |
| 17 | GDELT timelinetone — China Leg B (§2.4) | none (unwired, A1 §2.4) | none | none | none | none | none |
| 18 | Marketing wire RSS ×11 (§2.5) | partial (outbox kill-switches; repo-recorded live-verify date, A1 §2.5) | none (found in A1 §2.5) | partial (key env gates, A1 §2.5) | none (found) | partial (poll intervals + salience, A1 §2.5) | none (found) |
| 19 | Truth Social mirrors (§2.5) | partial (same daemon gates) | partial (conditional-GET recency posture, A1 §2.5) | none (published mirrors) | none | partial (per-source intervals, A1 §2.5) | none |
| 20 | X/Twitter twitterapi.io (§2.5) | partial (daemon gates) | none (found) | partial (paid key + spend caps, A1 §2.5) | none | partial (spend counters, A1 §2.5) | partial (x_stream websocket, A1 §2.5 — no reconnect telemetry found) |
| 21 | Alpaca news lane — marketing (§2.5) | partial (daemon gates) | none (found) | partial (key env pair, A1 §2.5) | none | partial (min_interval + limit, A1 §2.5) | none (found) |
| 22 | Substack public RSS (§2.6) | partial (CB:121-128 + breaker CB:602-610) | none | none (keyless; PR-gated registry) | partial (column contract) | partial (breaker skip) | none |
| 23 | Hacker News Algolia (§2.6) | partial (same) | none | none (keyless) | partial (same) | partial (same) | none |
| 24 | EDGAR 8-K velocity (§2.6) | partial (same) | none | none (public filings) | partial (same) | partial (same) | none |
| 25 | Federal Register API (§2.7) | partial (breaker; degraded-coverage log, A1 §2.7) | none (first-seen PK, no gap detect) | none (keyless) | partial (column contract) | partial (0.5 s pace, A1 §2.7) | none |
| 26 | White House WordPress RSS (§2.7) | partial (hourly sentinel no-op on unchanged; processed.json dedupe state, A1 §2.7) | partial (processed.json = processed-position state, A1 §2.7) | none (keyless) | partial | partial (hourly cadence) | none |
| 27 | China official corpora (§2.7) | partial (breaker) | partial (checkpointed collect lane, A1 §2.7) | none (keyless) | partial (column contract) | partial (paced/cached, A1 §2.7) | none |
| 28 | SF Fed sentiment index (§2.7) | partial (stale-after tracking, A1 §2.7; breaker) | none (daily file replace) | none (official publication) | partial (column contract) | none | none |
| 29 | CN flash wires ×5 (§2.8) | partial (degrade-to-[] per source, engine/cn_newswires.py:31-34,331) | none | none (keyless; THS Referer contract :16-19 is transport, not auth) | partial (fixture-pinned item contract, :27-33) | none (TTL cache, no budget measure) | none |
| 30 | CCTV 新闻联播 (§2.8) | partial (breaker) | partial (incremental daily walk, A1 §2.8) | none | partial (column contract) | partial (daily pacing) | none |
| 31 | CN wire tone snapshot (§2.8) | partial (breaker) | none (per-run snapshot) | none | partial (column contract) | none | none |
| 32 | EC press corner (§2.9) | partial (per-run degraded-coverage warning, A1 §2.9; breaker) | none | none (CC BY 4.0, A1 §2.9) | partial (column contract) | partial (tier-1 preflight reachability, A1 §2.9) | none |
| 33 | Bank of England news (§2.9) | partial (same) | none | none (OGL v3.0) | partial (same) | partial (same preflight) | none |
| 34 | ECB press — excluded (§2.9) | none (intentionally excluded) | none | none (rights-unverified exclusion) | none | none | none |
| 35 | HKEXnews filings (§2.10) | partial (breaker) | none | none (public filings) | partial (deterministic category map, A1 §2.10) | none | none |
| 36 | Finlight AI feed (§2.11) | partial (returns [] when disabled, A1 §2.11) | none | partial (key-gated; [] without key, A1 §2.11) | none | none | none |

**Grid tallies (216 cells):** covered 16 · partial 93 · none 107. Every Family-A primary/supplemental mode with a wired runner is covered or partial; every `none` outside Family A row 3/17/34 is a nightly, keyless, or dark-by-default family whose only transport telemetry is a degrade log — exactly G1/G4's blast radius.

---

## 4. Proposed build sequence (A5 build, wave 2)

Ordered so each step lands on the receipts the previous step validated; each item is one lane, docs/tests-first, no new store/registry (program law §11). "Receipt kinds" are the existing `qbus.news_health.v1`, `qbus.news_runner_exit.v1`, `ticker_news.snapshot.v1`, `ticker_news.changes.v1`, `ticker_news.inventory.v1`, and the tracked `data/run_status.json` — no new kinds.

1. **Publish drift/budget counters in the served receipt (closes G7).** Inputs: `RunnerStats` R:57-66; `_health_payload` R:201-221; `parse_health_receipt` non-negative-int validation + result H:291-301,322-345. Tests: tests/test_run_qbus_news_health.py:219 (write-failure counting precedent), tests/test_qbus_news_receipts.py:213 (counter validation). Discriminator: 50 malformed frames → `stream_errors=50` served while state stays `live`.
2. **Gap-episode timestamps (G3).** Inputs: `gap_unresolved` R:214,270-273; optional-time parsing H:268-274; `_source_health` passthrough API:357-372. Tests: tests/test_run_qbus_news_gap_replay.py:445,477. Discriminator: `gap_first_seen_at` stable across consecutive degraded receipts, null after recovery.
3. **Rights-expiry + stream-auth classification (G5, G6).** Inputs: receipt `expires_at` H:46,156-161; inventory rights section scripts/ticker_news_inventory.py:280-297; `_error_code` fallback R:113-126; API projection API:404-421. Tests: tests/test_run_qbus_news_health.py:433,469 (check-activation), tests/test_ticker_news_inventory.py. Discriminator: expired `rights_expires_at` projects `restricted`, never `live`.
4. **Reconnect latency fields (G9).** Inputs: connect loop R:380-425; counters R:215-216; tests/test_run_qbus_news_health.py:127. Discriminator: `last_connect_at − last_disconnect_at ≥ reconnect_base_seconds` in the parsed receipt.
5. **Intake observation-age + saturation fields (G2 + intake half of G8).** Inputs: `SupplementalNewsIntake.health()` I:144-154; extras validation H:351; `_curated_health` API:390-402; the no-invented-recency law tests/test_qbus_news_receipts.py:273. Tests: tests/test_qbus_news_intake.py:110,241. Discriminator: stale writer observation → curated `degraded` while the extra's own last poll stays `available`.
6. **Nightly-family fetch-outcome health (G1 + G4 + GDELT half of G8).** Inputs: `FetchResult` shape CB:121-128; `RSS._fetch` RSS:110-118; GDELT breaker reads GD:119-134; aggregation point scripts/build_news.py (serial spine, config/dag.yml:696-699); existing tracked artifact `data/run_status.json` (CB:24). Tests: new per-source outcome unit tests beside tests/test_qbus_news_intake.py; collector-shape test beside collectors/base.py usage. Discriminator: HTTP-failure feed vs zero-item feed produce different statuses in `news_feeds`; GDELT breaker armed → outcome `rate_limited_without_fetch` with the armed-until timestamp.

Sizes: items 1-5 are S (one to three files, one receipt kind each); item 6 is M (three nightly modules + one aggregation write). Total 6 lanes.

---

## 5. Open questions / unknowns

1. **WS auth-failure classification (feeds G6).** Unknown whether the Benzinga/Alpaca websocket signals auth rejection in a frame distinguishable from a network drop before the HTTP layer exists; the code path currently collapses both to `exception_*` (R:121-126). Unknown because no provider contract doc is in-tree and no live probe was permitted.
2. **A1 row-count delta.** The seed's footer says "35 source rows" while §2.1-§2.11 enumerate 36 labels; the counting convention (maybe Benzinga-on-Massive or the unwired Leg B row is not counted) is not stated in the seed. This grid follows the enumerated labels.
3. **`restricted` at receipt level.** `_state_from_health` accepts `restricted` (API:417) but `qbus.news_health.v1` validation rejects it (`_HEALTH_STATES`, H:27), and no writer emits it into the receipt; intake `restricted` reaches the API only via `additional_sources` (valid there, H:351). Whether any future writer-side `restricted` is intended is unstated.
4. **Concurrent writers to `data/run_status.json`.** The collect lane (scripts/collect.py) and the proposed `news_feeds` aggregation in build_news would both write the tracked file; the DAG runs build_news on a serial spine (config/dag.yml:696-699), but whether collect.py and build_news ever share a process/window — and therefore whether a read-modify-write merge rule is needed — was not verified from the DAG alone.
5. **Clock domains for Families D-K (A1 §5.10).** Without `received_at`/`available_at` on RSS/GDELT rows, window coverage cannot be recomputed after the fact; closing G4's `last_complete_window` answers "when did we last look", not "what arrived when". Left to the clock-domain decision A1 already flagged.
6. **Sparse-tree limitation.** data/ and site/ are omitted by policy (config/sparse_worktree.json); the on-disk shapes of `data/run_status.json` and the GDELT stamp were read from code, not from a real artifact. No absence above should be read as repo absence.
7. **RETAINED receipts are dated, never asserted as current.** The RETAINED 2026-10-20/21 readbacks cited by A1 (PRs #9846/#9942/#9963) describe past timestamps only; this census adds no delivery claim of its own — every STATE here is a telemetry-coverage claim, not a liveness claim.
