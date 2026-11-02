# CDV-1 plan seam audit (opus, READ_ONLY) — PARTIAL (turn limit)
Plan: /Users/chriswong/Downloads/2026-09-23-consumer-defensive-cdv1-implementation.md
Checkout: .claude/worktrees/consumer-defensive-cdv1-ca40b6 (HEAD d7711a0a08db, sparse)
Coverage: (a)-(e) inspected; (f)-(j) NOT_CHECKED. pytest --collect-only NOT RUN.

## Ranked findings

F1 MAJOR — (d) plan targets the wrong acquisition seam for discovery.
 Plan :54, :78, :230-257 treats `acquire_results_filing` as "the existing acquisition helper".
 Code: scripts/refresh_event_workspaces.py:236 `acquire_results_filing` in discovery mode has NO production caller;
 its only production call is the pinned-accession AAPL flagship (:370). Discovery-mode callers are tests only
 (tests/test_issuer_profiles_a5a.py:192-225). Production discovery is `discover_new_homebuilder_revisions` (:872)
 -> `_fetch_submissions_candidates` (:739) -> `_resolve_exhibit_for_row` (:759, called :1013), which already does
 discovery boundary, first-publish fiscal-year bound, chain-represented skip, 8-K/A admission, and the F1
 stated-period cross-check (:1016-1025) with `::warning` skips.
 Correction: packet must name BOTH seams; either put the trace in `_resolve_exhibit_for_row`/the discovery loop (the
 real production path) or explicitly justify `acquire_results_filing` discovery mode as the PG-only path and
 replicate boundary/stated-period checks. Do not claim "no new discovery algorithm" while using the unused one.

F2 MAJOR — (d) decode semantics: "decode failure" outcome is unreachable and legacy decode is permissive.
 Code :348-351 and duplicate :781-784: `exhibit_body.decode("utf-8")` falling back to `decode("latin-1")`, which
 never fails; SGML header uses `errors="replace"` (:333, :775). Plan :133-135 and 2.1 ("malformed encoding") require
 a decode-failure outcome and forbid lossy mint.
 Correction: PG path records `decode="utf-8"|"latin-1-fallback"` in the trace and REFUSES exact-evidence minting on
 fallback, while the legacy return keeps latin-1 for byte-identical default behavior. Received bytes are not in the
 legacy dict; trace must carry them (or their digest) separately.

F3 MAJOR — (a)/(b) fiscal_scope cannot reach the extractor; prior-period convention conflicts.
 Plan :186 `extract_pg_release_facts(*, bound, document_id, event_id, fiscal_period)` MATCHES the call at
 engine/company_intelligence/event_workspace_build.py:302-304. But `FiscalPeriod` (events.py:147-159) carries only
 year/quarter/calendar_end — no start, no prior interval — and `pg_profile()` (plan :186) takes no args, so the
 extractor cannot know `prior_end`. Plan test :202 asserts prior `period == '2025-06-30'`; existing house convention for
 prior facts is the label `period="prior_year_same_quarter"` (issuer_profiles.py:580, :680, :1250); current period is
 `calendar_end.isoformat()` (:419-421).
 Correction: either `pg_profile(*, fiscal_scope)` closure (profile built per event) or read the prior column's period
 end literally from the table header; and state explicitly that PG departs from the `prior_year_same_quarter` label
 (the plan says "shapes unchanged", :94). `period` is a single ISO end date, not an interval — duration checks must
 come from fiscal_scope, not the row.

F4 MAJOR — (b) there is no native `event_fact.v1` validator to reuse; workspace always carries non-PG facts.
 `validate_event_workspace` (event_workspace.py:279-345) only checks `facts` is a list; fact shapes are dict literals:
 present {schema,fact_id,event_id,metric,value,unit,period,basis,source_span} (issuer_profiles.py:319-342),
 absent {schema,fact_id,event_id,metric,typed_absence} (:345-358). `build_event_workspace` unconditionally adds
 `fact_revenue_gaap`/metric `revenue` (event_workspace_build.py:271-298) and `fact_questions_count` (:323-349).
 Plan key names `value/metric/period/event_id` MATCH. Correction: `validate_selected_facts` must filter to the `pg_`
 namespace before "exact key set" and 24-cap checks, and the packet must say the key-set validator is NEW code, not
 reuse. Absence reasons: closed set documents.py:72-87 (14 reasons, enforced in TypedAbsence.__post_init__ :508-510)
 — plan :129 MATCHES.

F5 MINOR — (a) lookup seam exists; plan snippet names differ; issuer seam not covered.
 `profile_for_ticker(ticker)` issuer_profiles.py:1293-1303 (local var `normalized`, not `normalized_ticker`);
 separate `issuer_for_ticker` :1280-1290 (homebuilders only; AAPL returns None). `IssuerProfile` (:155-181) required
 fields: `ticker`, `extract_release_facts`, `extract_transcript_claims`; optional `extract_guidance` (default []).
 `build_event_workspace` needs a `registry: IssuerRegistry` resolving the ticker (event_workspace_build.py:108-113,
 :193-196); `production_registry()` (event_workspace.py:180-193) must NOT gain PG per plan :186, so the packet must
 specify a private `IssuerRegistry([pg_issuer()])`. Tests pin `profile_for_ticker("LEN"/"NVR") is None`
 (tests/test_issuer_profiles_a5a.py:135-142) — a kw-only `publication=` default keeps these green.
 Also `_release_span_payload` hard-codes `rights_profile="rp_public_primary_v1"` (issuer_profiles.py:304-316); a
 private PG extractor reusing it mislabels rights. Correction: PG helper passes a private rights profile.

F6 MINOR — (e) `preview_generation_identity` signature MATCHES (event_workspace.py:477-493) but returns only an id
 string; it does not "freeze a native workspace" (plan :137, :257). The id is a NEST id over all workspaces in the
 map, hashes `generated_at` (:450-474), and `build_event_workspace` returns `generation_id=""` plus private keys
 `_source_sha256`, `_aliases` (event_workspace_build.py:545-562) and `generated_at=_iso(clock)`.
 Correction: packet must stamp `generation_id`/strip private keys itself (mirroring write_workspace_generation :531-547)
 and pass a carried-forward `generated_at` or the "no new wall clock" rule (plan :137) fails.
 `build_event_workspace` signature (event_workspace_build.py:108-126) takes `exhibit_body: str`, `filing` mapping,
 `transcript`, `observed_at`, `source_available_at`, `prior_*` — it binds internally; plan fixtures calling
 `bind_release_document` directly for workspaces duplicate binding (OK for Task-1 bound cases only).

F7 NIT — (c) binding/receipts MATCH. `bind_release_document(*, cik, accession, body: str, form, filing_date,
 acceptance_datetime, report_date, exhibit_url, content_type, registry)` binding.py:244-296; `BoundRelease.source`
 = `document.raw_source` (:140-142) which equals the supplied body unchanged (disclosure_diff.py:897-918, :944);
 `source_sha256` = sha256(body utf-8). Receipt helpers: `receipt_for_literal(*, source, source_sha256, search_start,
 search_end, literal)` receipts.py:233-262 (unique-literal, markup-masked), `replay_receipt` :138,
 `SpanReceipt.byte_start/byte_end/span_text` :81-94; span minting via documents.text_span :373-430. Fixture needs no
 other call to get real digests. No `SourceDocument` "validation" function exists — validation is
 `SourceDocument.__post_init__` (documents.py:175-199); no `from_payload`. Plan :257 wording should say construct.

## Verdict table
(a) MISMATCH-minor (seam exists: profile_for_ticker :1293; registry gap F5)
(b) MATCHES keys / MISMATCH prior-period convention + no validator (F3, F4)
(c) MATCHES (F7)
(d) MISMATCH (signature cik/http_get/accession MATCHES :236-238; legacy keys cik,accession,form,filing_date,
    acceptance_datetime,report_date,exhibit_url,exhibit_body,items :358-366; skip points :327-332 header,
    :334-339 no EX-99.1, :342-347 exhibit fetch, :352-357 empty; wrong production seam F1; decode F2)
(e) MATCHES signatures / MISMATCH semantics (F6)
(f) NOT_CHECKED  (g) NOT_CHECKED  (h) NOT_CHECKED  (i) NOT_CHECKED  (j) NOT_CHECKED
pytest --collect-only counts: NOT RUN.

## Part 2 (f)(g)(h)

### (f) engine/earnings_narrative/private_publication.py — checkpoint 1
Constants :33-50: PRIVATE_PREFIX="earnings_wire_private/v1", POINTER_KEY=".../current.json", POINTER_SCHEMA
"earnings.private_pointer/v1", MANIFEST_SCHEMA="earnings.private_manifest/v1", RECORD_SCHEMA="earnings.tier_payload/v1",
MAX_POINTER_BYTES 16KiB, MAX_MANIFEST_BYTES 8MiB, MAX_RECORD_BYTES 2MiB. Entry points exist with plan signatures:
prepare_private_publication(stage_dir) :318, publish_private_publication(store, prepared) :672,
load_private_manifest(store) :748, load_private_record(store, slug, *, manifest=None) :793. MATCHES.
Store: engine/research_vault/r2_store.py Store :49 (get_bytes/put_bytes/list_prefix/exists/upload_time);
StrictBoundedReadStore :72 `get_bytes_strict_bounded(key, maximum_bytes)` :84 — EXISTS; plan test :317/:323 call
shape MATCHES (via _bounded_read :455-465).

F8 MAJOR — plan :347 says "where the existing store has no atomic conditional-write facility ... no new lock
service". A CAS primitive ALREADY EXISTS: r2_store.py:105-127 `StrictConditionalWriteStore` with
`get_bytes_strict_bounded_versioned(key, maximum_bytes) -> VersionedBytes` and
`put_bytes_strict_conditional(key, data, *, expected_version, content_type)` (+
`validate_strict_conditional_write_capability`). private_publication does NOT use it today: pointer promotion is an
unconditional `store.put_bytes(POINTER_KEY, ...)` :726 with best-effort restore of `prior` on echo mismatch :731-739.
Correction: Task 4 packet should use the existing versioned read + conditional put for the v2 pointer promotion
(expected_version = version read when preparing), not a read-compare-then-blind-put; and must not reuse the :735
restore on an uncertain v2 write (plan intent correct, mechanism exists).

F9 MAJOR — object-key/receipt regex is JSON-only. `_OBJECT_KEY_RE` :56-58 requires `/objects/sha256/xx/<sha>.json`;
`_artifact` :212-221 always mints `.json`; `_validate_receipt` :230-248 requires key tail == `<sha>.json` and a closed
{object_key, sha256, bytes} receipt. Raw-byte / UTF-8-text source-body roles (plan :166, :334) cannot pass without
changing these. Correction: add role-keyed key regexes/suffixes (e.g. .bin/.txt) and a v2-only receipt validator;
v1 manifests must keep failing on non-.json keys (don't widen the shared regex).

F10 MAJOR — prepare refuses any extra stage file. :424-426 `actual_paths != expected_paths` -> "staging tree contains
unexpected files"; stage layout is exactly records/*.json + context/latest.json + context/<ticker>.json (:321-414).
Every records/*.json goes through validate_private_record (v1-only, :149-183: page must be "earnings_wire_article",
locked_facts>=1, exact 8 keys). Task 5 `augment_private_stage` writing native members BEFORE Task 4 lands would make
every normal wire run fail. Correction: hard ordering Task 4 (stage-layout + v2 dispatch) before Task 5 enable; name
the native stage subdir in Task 4's contract.

F11 MINOR — manifest identity: generation_id = sha of canonical manifest (:224-227); `published_at` =
context_manifest knowledge_cutoff (:431), not wall clock; pointer promotion refuses `published_at` rewind (:721-722)
but allows equal. A native-only change under an unchanged wire context yields same published_at, new generation —
allowed. Manifest top-level keys are exact (:250-265) and source block is fixed to the wire context (:432-436) —
plan :162 v2 `native` + `previous_manifest` keys need a v2 validator; `_existing_exact_publication` :596-669 and the
post-promotion replay :743-746 compare against validate_private_manifest, so v2 dispatch must cover both.

### (f) checkpoint 2 — test fixture + v2-dispatch invariants
`_staged_publication(tmp_path) -> (public_dir, private_dir, slug)` EXISTS tests/test_earnings_private_store.py:122-221.
It builds a real AAPL transcript -> write_generation -> write_story_packet_generation -> compile_public_wire_article ->
build_public_wire_manifest -> `publish_public_wire(publication, out_dir=..., private_out_dir=..., company_reader=...)`
(:204-219) — i.e. the stage is produced by the real wire builder, not a Store fixture. Store in tests = LocalStore
(r2_store) + subclasses CountingLocalStore :41, BlockingStrictStore :58, ReadCountingLocalStore :95,
FailingArtifactStore :109 — plan :312 "don't invent a second Store" is satisfiable via FailingArtifactStore pattern.
Invariants a v2 change must keep: :239 asserts `record["schema"] == "earnings.tier_payload/v1"`; :247-260 tamper +
unexpected-file rejection; :323-331 pointer-last idempotence; :597-616 zero-record context-only generation is valid.
F12 MINOR — the record schema literal is DUPLICATED in the producer: scripts/build_earnings_public_wire.py:82
`PREMIUM_PAYLOAD_SCHEMA = "earnings.tier_payload/v1"` (used :1019), separate from private_publication.RECORD_SCHEMA :37.
Correction: Task 4/5 packet must name both constants; keep both at v1 for legacy records (plan :330 intent) and add a
distinct v2 constant only for native records.

### (h) scripts/build_earnings_public_wire.py + workflow — MISMATCH (insertion point)
F13 MAJOR — `prepare_private_publication` is NOT called in build_earnings_public_wire.py (plan :59, :384-395).
It is called only in scripts/publish_earnings_private_store.py:31 (`publish(source_dir, *, local_store=None)` :30;
`publish_private_publication` :37; CLI `--source-dir` :51). Legacy private staging is inside
`publish_public_wire` :1534 at :1567-1570: `_write_premium_payloads(views, private_out_dir=...)` (:1002-1031) then
`_write_context_manifest(manifest, private_out_dir=...)` (:1034-1048). BOTH functions delete every *.json in their
dir that they did not write (:1030-1031, :1046-1048) — a native record pre-staged into records/ is silently erased.
Workflow: .github/workflows/earnings-public-wire.yml ~:122-124 (NOT :68-79, which is setup/env):
  PRIVATE_STAGE="$RUNNER_TEMP/earnings-wire-private-${PUSH_ATTEMPT}"
  python -m scripts.build_earnings_public_wire --private-out-dir "$PRIVATE_STAGE"
  python -m scripts.publish_earnings_private_store --source-dir "$PRIVATE_STAGE"
Correction: the Task 5 hook goes AFTER publish_public_wire's :1569-1570 staging (or as a separate step between the two
workflow commands), never before; and the file list must add scripts/publish_earnings_private_store.py (the actual
prepare/publish caller, where `prior_closure` via the Task-4 reader belongs since it holds the store). Plan's
file list (:81) omits it and names scripts/publish_company_intelligence_r2.py instead.
F14 MINOR — fast path: build() :1628 only takes the "unchanged" shortcut when `private_out_dir is None`; the production
workflow always passes --private-out-dir, so every production run already rebuilds. Plan :384 "current wire fast paths
must still check native inputs" is moot for production; the concern is only the publisher's
`_existing_exact_publication` no-op (:596-669), which is content-addressed and correct if native members are staged.

### (g) app/earnings.py + tests/test_earnings_api.py
Helpers MATCH: `_PRIVATE_HEADERS` :23-28 (Cache-Control "private, no-store", Vary Authorization, nosniff,
X-Robots-Tag "noindex, noarchive"); `_private_error(status_code, detail, inherited=None) -> HTTPException` :42-56;
`require_site_full_user(authorization=Header)` :59-67 = `enforce_site_full(require_user(...), always=True)`;
`_build_store()` :70-80; `_current_manifest(store, *, force=False)` :83-95 (30 s TTL cache :35); `_reset_private_caches`
:98-105. Record route :108-139; catch-all `/api/earnings/v1/records/{remainder:path}` :142-154 -> private 404 after auth.
F15 MAJOR — route shadowing is mandatory, not "where required": FastAPI matches in registration order and the
catch-all :142 `{remainder:path}` matches `/records/{slug}/economic-evidence/{fact_id}`. Correction: register the
evidence route ABOVE :142 and add a test that it returns 200/404-from-handler (not catch-all 404).
F16 MAJOR — plan's route snippet (:437-450) error mapping regresses the house pattern. Existing handler checks
`store is None` (:123-124) and maps ANY exception to 503 with private headers (:137-138); snippet catches only
EarningsPrivateRecordNotFound/EarningsPrivatePublicationError, so a storage/botocore exception becomes a bare 500
without private headers (violates plan :21). Also no ticker syntax -> 400 step (use private_publication.validate_ticker
:135, upper-case regex :53). Correction: copy the :117-139 structure verbatim, incl. `except Exception -> 503`.
F17 MINOR — `/api/earnings/v1/economic/{ticker}` has no auth-gated catch-all; `/economic/PG%2Fx` or
`/economic/PG/extra` falls to the app 404 before auth. Correction: add `/api/earnings/v1/economic/{remainder:path}`
private-404 sibling (mirrors :142) so probes stay behind auth (plan :413 test demands this).
F18 MAJOR (test infra) — `entitled_client` :36-55 is a STUB: `store = object()`, `_build_store` and `_current_manifest`
monkeypatched to return a fake `{"generation_id": ...}` manifest; yields `(client, store, manifest)`. It cannot back
plan :416-431 `economic_client.publish_fixture_revision`. Correction: new fixture = LocalStore + real
publish_private_publication, patch only `_build_store`, call `earnings_api._reset_private_caches()` after each publish
(else the 30 s manifest cache :90-91 serves the old generation).
F19 MINOR — `test_every_paid_route_is_mounted_on_the_assembled_production_app` :200-219 iterates
`_MOUNTED_PAID_PATHS`; plan 6.4 "every paid route hits auth" requires adding both new paths to that tuple.
Invariant: `test_workflow_publishes_private_r2_before_staging_public_html` :272-285 pins workflow ordering
(publish_earnings_private_store before `git add site/stocks/earnings`) — any Task 5 workflow edit must keep it.
Collect: `python3 -m pytest tests/test_earnings_private_store.py tests/test_earnings_api.py --collect-only -q | tail -3`
-> "30 tests collected in 2.89s".

### Part 2 verdicts
(f) MATCHES entry points/Store method names; MISMATCH on CAS availability (F8), JSON-only object keys (F9),
    stage-tree closure (F10), duplicated schema literal (F12). `_staged_publication` EXISTS.
(g) MATCHES helper names; MISMATCH route order/error mapping/fixture (F15-F19).
(h) MISMATCH — prepare/publish live in scripts/publish_earnings_private_store.py, workflow lines ~:122-124 (F13, F14).
