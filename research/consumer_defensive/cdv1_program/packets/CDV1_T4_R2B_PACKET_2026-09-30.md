# CDV-1 T4 — ROUND B of two (same branch and PR as round A)

LANE `cdv1_t4_private_publication_r2b` — BUILD CDV-1 Task 4, round B, on PR #8245 (branch `claude/cdv1-t4-private-publication-v2`). Continuation mode: you start on the branch head that round A pushed and the seat verified. The seat owns readiness, labels, review and merge.

This packet is complete on its own. Where it differs from the plan, the packet rules. Each difference is a seat ruling. Round A's rulings R-A1–R-A12 stay binding; nothing here weakens them.

## C0 GATE (first actions; quote the outputs under EVIDENCE)
1. Run `git fetch origin main` and, as a separate command, `git fetch origin claude/cdv1-t4-private-publication-v2`. Quote `git rev-parse HEAD origin/claude/cdv1-t4-private-publication-v2 origin/main`. HEAD must equal the branch tip and equal `12da187d257283214e070bb8496774df2423c6e8`. If not, STOP with STATUS BLOCKED. Never `git checkout -B`; every push is `git push origin HEAD:refs/heads/claude/cdv1-t4-private-publication-v2`.
2. `git grep -n "def validate_native_closure\|class EarningsPrivateClosureError\|def assert_native_rights\|v2 private publication is not enabled" -- engine/earnings_narrative/private_publication.py` must show all four. If one is missing, STOP with STATUS BLOCKED.
3. `sed -n '33p' engine/earnings_narrative/private_publication.py` must print `PRIVATE_PREFIX = "earnings_wire_private/v1"`.
4. Quote the RED/GREEN baseline: `python -m pytest tests/test_earnings_economic_private_store.py tests/test_earnings_private_store.py -q -p no:cacheprovider` (in the RUNS venv) must pass before you edit anything.
5. Reading aid, never a gate: round A's packet is `research/consumer_defensive/cdv1_program/packets/CDV1_T4_R2A_PACKET_2026-09-30.md` on `origin/main` (`git show origin/main:<path>`). The plan is on `sol/consumer-defensive-research-20260923`, Task 4 (its own `git fetch`). Every plan sentence that binds this round is quoted below.

## MISSION
Finish Task 4 on the same PR: publish a v2 generation by exact predecessor, keep v1 publication from overwriting v2, give Tasks 5 and 6 the readers they consume, and wire the suite into CI and the deploy restart list.

Plan 4.3 binds: "A v2 publish records and checks the predecessor pointer bytes used to prepare the candidate immediately before promotion. If they differ, abort before writing the pointer and reconcile. Where the existing store has no atomic conditional-write facility, do not claim this check alone is a distributed compare-and-swap. … Never apply the existing best-effort restore behavior to an uncertain v2 pointer write; return the exact unknown effect for same-carrier reconciliation."

Plan 4.4 binds: "Publish mixed closure, read it, rerun identical preparation and prove no new source or derived revision. Attempt v1-only promotion over installed v2 and require explicit refusal. Remove an economic slot without a retirement instruction and require refusal. Corrupt an immutable object under its existing key and require fail-closed behavior, not overwrite. Run `tests/test_earnings_private_store.py` together with the new suite."

## HARD LAWS (violations are seat-reportable)
- Never `git add -A`; add named files only. Never force-push, rebase, amend, or use bare `git stash`/`pop`.
- Never `gh pr ready|merge|edit|review|comment`, never `gh pr create` (the PR exists), and never add labels. At most 3 `gh` calls in total and no CI polling.
- Never print, copy or open credentials (`~/.glm`, `~/.minimax`, `~/.codex/auth*`, `ext/glm_shim/.token`, any `.env`).
- Never write outside OWNED FILES. Never write under `data/` or `site/`: this is a SPARSE tree, and a write there truncates committed artifacts. Never run `python3 scripts/worktree_sparse.py full`.
- Never edit STSI PR #7777's paths. Never touch the research carrier PR #7792 or its branch.
- Do not stop to ask questions and never end on a status note. Record blocks under GAPS and finish the packet. A lane that ends with "I'm finishing…" commits nothing and is a wasted slot.
- All numbers in fixtures are SYNTHETIC test values, never copied live P&G facts. No test uses the network.
- Reported and core EPS are separate definitions; organic sales are not household consumption; combined volume/mix is not pure volume; all rank/gate/size/originate/entry/Prophet effects stay literal false; the LLM never originates a signal.
- Trailer on EVERY commit: `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
- Push with `git push origin HEAD:refs/heads/claude/cdv1-t4-private-publication-v2` (no force). Treat "Everything up-to-date" as FAILURE when a commit was expected.

## FILES
OWNED (the only files you may change or create):
- `engine/earnings_narrative/private_publication.py`
- `tests/test_earnings_economic_private_store.py`
- `tests/earnings_economic_private_fixtures.py`
- `.github/ci/legacy-jobs.yml` (one new job and the closure widenings of R-B13, nothing else)
- `tests/test_ci_pack.py` (one `CURATED_EXCLUSIVE` entry, nothing else)
- `app/deploy/update.sh` (the restart regex of R-B14, nothing else)
- `tests/test_deploy_update_self_heal.py` (the `MUST_RESTART` entries of R-B14, nothing else)

FROZEN (never edit; a failing frozen test is a finding for GAPS):
- Tasks 1–3 and the legacy suite exactly as round A listed them. `tests/test_earnings_private_store.py` must stay `18 passed`, unedited.
- Round A's tests in `tests/test_earnings_economic_private_store.py`: add tests, never delete or weaken one. If a round-A test contradicts a ruling below, report it under GAPS instead of editing it.
- `app/earnings.py`, `templates/**`, `research/**` and every other file.

## MEASURED INTERFACES (seat probes on main and on round A's head; build on these, do not re-derive them)
- **Stores.** `engine.research_vault.r2_store.StrictConditionalWriteStore` is a `runtime_checkable` Protocol with `get_bytes_strict_bounded_versioned(key, maximum_bytes) -> VersionedBytes(data, version)`, `validate_strict_conditional_write_capability()` and `put_bytes_strict_conditional(key, data, *, expected_version, content_type) -> bool`. `True` means written. `False` has exactly one meaning: the backing authority rejected the supplied predecessor. Anything else raises. `expected_version=None` means "the key must be absent". `LocalStore` implements it (its version is `"sha256:<hex>"` of the bytes); `R2Store` implements it and maps HTTP 409/412 to `False`. `LocalStore.put_bytes_strict_conditional` does NOT call `put_bytes`, so the legacy `CountingLocalStore.put_calls` never records a conditional write.
- **v1 publish** (`publish_private_publication`, main lines 672–746): type checks; `_PUBLISH_LOCK`; `_validated_prepared_payloads`; `_unique_verified_payloads`; the fast path `_existing_exact_publication` (a matching pointer, manifest and every artifact, or `None`); the pooled `_put_verified_artifact` writes; `_put_verified` of the manifest; a plain read of the prior pointer (same generation → return; an older `published_at` → "stale private publication cannot rewind current"); `store.put_bytes(POINTER_KEY)`; an echo read; on a mismatch a best-effort restore of the prior pointer, then "private earnings pointer read-back mismatch"; a replay through `load_private_manifest`.
- `_put_verified(store, *, key, body, maximum)` hardcodes `content_type="application/json"`. It reads the key, refuses a different existing body ("immutable private earnings object collision"), writes when absent, and reads back ("private earnings object read-back mismatch").
- **Legacy doubles** (import them, never copy them): `CountingLocalStore(root)` with `put_calls`; `FailingArtifactStore(root, *, failing_key)`; `_staged_publication(dir) -> (public_dir, private_dir, slug)`.
- **Identity.** `pg_profile.pg_private_registry().resolve_ticker(ticker, *, asof)` returns a `ListingResolution` (`.company_id`, `.ticker`, …) or `None`; `asof` is a `datetime.date` or an ISO date string; it raises `IdentityError` when two issuers match.
- **Task 3 observations** have `handle`, `metric`, `fact_id`, `family`, `group`, `label` (`en`, `zh`), `event_id`, `period`, `basis`, `native_basis`. A typed absence adds `typed_absence` and has `value_and_unit` `None`. A valued row adds `value`, `unit`, `source_excerpt` (a `str`) and `value_and_unit`, and a `unit == "text"` row also `source_text`. **No observation carries a `source_sha256`.**
- **Consumers.** `app/earnings.py` caches `load_private_manifest(store)` for 30 s, serves `load_private_record(store, slug, manifest=…)` as-is on `/api/earnings/v1/records/{slug}`, maps `EarningsPrivateRecordNotFound` to 404 (after one forced refresh) and every other error to 503. The wire page (`templates/earnings_wire/earnings-wire.js:73`) throws unless `payload.schema === 'earnings.tier_payload/v1'` and the slug matches.
- **Deploy.** `app/deploy/update.sh` line 1254 holds the API restart regex. It already matches `engine/company_intelligence/.*\.py` and `engine/theme_graph/(store|rights)\.py`; its earnings group is `engine/earnings_narrative/(__init__|context_packets|contracts|digest|private_publication|promotion|public_wire|story|story_packets)\.py`; it has no `engine/earnings_release/` entry. `engine/earnings_release/` holds `__init__.py`, `binding.py`, `figures.py`, `filing_key.py`, `receipts.py`. `MUST_RESTART` in `tests/test_deploy_update_self_heal.py` starts at line 248; its earnings block is at lines 357–367.
- **CI.** The template is the `earnings-economic-source-selection` job (`.github/ci/legacy-jobs.yml`, line 14421): `if: ${{ false }}`, `gate: code`, `scope: exclusive`, an explicit sorted `paths:` list, ubuntu-latest, Python 3.12, one `pip install` step, one pytest step. The next job is `earnings-economic-dossier:` (line 14481). `CURATED_EXCLUSIVE` in `tests/test_ci_pack.py` names it at line 4329. `test_curated_exclusive_scopes_cover_their_own_import_closure` fails and lists the missing paths when a curated job's `paths:` do not cover its import closure.

## SEAT RULINGS R-B1–R-B14 (binding)

### R-B1 — the surface
Add below round A's classes, each a subclass of `EarningsPrivatePublicationError`:
- `EarningsPrivatePublishConflict(reason, message=None)` with `.reason` in `PUBLISH_CONFLICT_REASONS = ("predecessor_conflict", "downgrade_refused", "slot_removed", "retirement_invalid", "chain_not_extended", "conditional_write_unavailable", "stale_native_cutoff", "installed_unreadable")`.
- `EarningsPrivatePointerEffectUnknown(generation_id, pointer_sha256, expected_version)` with those three attributes and the fixed message "private earnings pointer write effect is unknown".
- `EarningsEconomicNotFound(reason, message=None)`, a subclass of `EarningsPrivateRecordNotFound`, with `.reason` in `NOT_FOUND_REASONS = ("no_slot", "unknown_generation", "unknown_record", "unknown_fact", "absent_fact")`.
- `EarningsEconomicUnavailable(reason, message=None)` with `.reason` in `READ_UNAVAILABLE_REASONS = ("interpretation_unsupported", "rights_refused", "evidence_retired")`. It is NOT a subclass of `EarningsPrivateRecordNotFound`.
- `EarningsPrivateManifestNotCurrent`, raised only by R-B10.
- Two public syntax validators beside `validate_slug` and `validate_ticker`, because Task 6 imports them for its 400 responses and the grammar must exist once: `validate_generation_id(value: str) -> str` accepts exactly `_GENERATION_RE` and otherwise raises `EarningsPrivatePublicationError("invalid earnings generation id")`; `validate_digest(value: str) -> str` accepts exactly `_SHA_RE` and otherwise raises `EarningsPrivatePublicationError("invalid earnings digest")`. Each tests `type(value) is str` before the pattern. R-B8 calls them and keeps its own mapping: a value either one refuses is `unknown_generation` there.

The three reason-carrying classes follow R-A3: a reason outside the tuple is a `ValueError`, `str(exc)` is the message or one fixed sentence per reason, and no message contains a body excerpt, an object key or a digest. Add every new public name, the five new readers and the four tuples to `__all__`.

### R-B2 — one read of the installed generation
Move the body of `load_private_manifest` into one private helper that takes the pointer bytes and returns `(pointer, manifest_bytes, manifest)`. `load_private_manifest` keeps its signature, its return value and every message. Every other reader of the current generation (R-B3, R-B4, R-B6, R-B10, R-B11) goes through this helper. A second helper used only by publication and by R-B3 wraps it and turns any `EarningsPrivatePublicationError` it raises into `EarningsPrivatePublishConflict("installed_unreadable")` (`from exc`).

### R-B3 — `load_private_predecessor(store) -> dict | None`
Task 5 writes the predecessor into the stage (R-A9 reads `previous_manifest` from the stage), and only the owner reads the pointer. Return `None` when the pointer is absent. Otherwise return exactly the five fields `generation_id`, `manifest_key`, `manifest_sha256`, `manifest_bytes`, `published_at` of the validated pointer, after the R-B2 publication helper has bound its manifest (else `installed_unreadable`).

### R-B4 — v1 publication
- `publish_private_publication` dispatches on the prepared manifest's schema: v1 goes to the v1 transaction, `MANIFEST_SCHEMA_V2` to R-B5. R-A11's guard is removed.
- The v1 transaction stays as it is, with three additions and nothing else:
  1. A v1 preparation with a non-empty `retired_slots` is `retirement_invalid`, before any store call.
  2. **Downgrade.** When the fast path returns `None`, and before any object write, read the installed generation through the R-B2 publication helper. An installed v2 manifest is `downgrade_refused`, always: retirement moves one v2 generation to another and never back to v1. An installed manifest that cannot be read is `installed_unreadable`. The same helper runs again on the prior pointer read at promotion, after the same-generation return and before the `published_at` rule.
  3. `_put_verified` gains `content_type: str = "application/json"`. `_put_verified_artifact` passes the artifact's `content_type`, so a source body is stored as `text/plain; charset=utf-8`. v1 calls pass nothing new.
- The v1 pointer write stays a plain `put_bytes` with its restore. The legacy suite counts it, and v1 runs under the existing single-writer workflow custody. Do not change it.

### R-B5 — the v2 transaction (in this order, under `_PUBLISH_LOCK`)
1. **Capability.** The store must satisfy `isinstance(store, StrictConditionalWriteStore)` and `store.validate_strict_conditional_write_capability()` must return, else `conditional_write_unavailable`. This runs before any read or write. Its fixed sentence says the store offers no conditional pointer write so v2 promotion is refused; no message anywhere claims a distributed compare-and-swap. (The store is not an untrusted v2 value; R-A8's `type(x) is T` rule does not apply to it.)
2. **Candidate.** `_validated_prepared_payloads(prepared)` and then `validate_native_closure(prepared.manifest, <every prepared payload by object key>)` in the full scope.
3. **Rights.** If `native.selections` is not empty, `assert_native_rights()` (R-A10; `rights_refused`).
4. **Fast path.** `_existing_exact_publication`, unchanged. A returned pointer is returned.
5. **Installed.** `get_bytes_strict_bounded_versioned(POINTER_KEY, MAX_POINTER_BYTES)` (a raise is `EarningsPrivatePublicationError("private earnings object read failed")`), then the R-B6 rules against that pointer.
6. **Objects.** The pooled `_put_verified_artifact` writes, then `_put_verified` of the manifest, exactly as v1 does.
7. **Pre-promotion readback.** Read back, bounded by role maximum, every object the manifest names, and build `object key → bytes`. An absent object is left out of the map. Call `validate_native_closure(prepared.manifest, <that map>)` in the full scope. Read the manifest back; bytes other than `prepared.manifest_bytes` are `EarningsPrivateClosureError("digest_mismatch")`. Any failure leaves the pointer unmoved.
8. **Promotion.** Read the pointer again with `get_bytes_strict_bounded_versioned`. Its five fields must still equal `previous_manifest` (else `predecessor_conflict`). Then `put_bytes_strict_conditional(POINTER_KEY, pointer_bytes, expected_version=<that read's version>, content_type="application/json")`:
   - `False` → `predecessor_conflict`;
   - a raise → `EarningsPrivatePointerEffectUnknown` (`from exc`);
   - `True` → a bounded echo read. The written bytes → continue. Other bytes, `None`, or a raise → `EarningsPrivatePointerEffectUnknown`.
   The v2 path calls the conditional write once. It never restores, never writes the pointer a second time and never calls `put_bytes` on `POINTER_KEY`.
9. **Replay.** `load_private_manifest(store)` must equal the prepared manifest, as in v1.

Re-running the same preparation reconciles an interrupted or uncertain run: the fast path finds a pointer that already names it, and otherwise the predecessor still matches.

### R-B6 — rules against the installed generation (one helper, called at R-B5 step 5)
With `installed` the pointer read at step 5 (or `None`):
1. **Predecessor.** `previous_manifest` must equal the pointer's five fields; `None` equals only an absent pointer. Else `predecessor_conflict`.
2. If a pointer exists, read its generation through the R-B2 publication helper (`installed_unreadable`). The v1 rewind rule applies: a candidate `published_at` older than the installed one raises the v1 message.
3. If the installed manifest is v2:
   - `stale_native_cutoff`: the candidate's `native_source_cutoff` is earlier than the installed one.
   - `retirement_invalid`: a retired company id is not an installed slot, or is still a slot in the candidate.
   - `slot_removed`: an installed slot's company id is neither a candidate slot nor retired.
   - `chain_not_extended`: for every installed selection whose `(company_id, event_id)` the candidate also selects, the installed chain must be a prefix of the candidate's chain, entry for entry (`{"workspace", "document"}` equal). A candidate may drop an older event's selection; it may never rewrite or shorten a chain it keeps. (Task 2's review N1: a re-accepted accession cannot replace a stored revision.)
4. If the installed manifest is v1 or absent, a non-empty `retired_slots` is `retirement_invalid`.

Consequence, stated in the PR: an event holds at most `MAX_NATIVE_CHAIN` revisions ever. A fifth is refused (`over_limit` at preparation, or `chain_not_extended` if a chain were trimmed). Task 5 must surface that as a typed hold and never trim.

### R-B7 — the uncertainty boundary
`EarningsPrivatePointerEffectUnknown` carries `generation_id` (the candidate's), `pointer_sha256` (sha256 of the bytes the owner tried to write) and `expected_version` (the version passed). The owner does nothing after it: no restore, no retry, no second read-modify-write. Same-carrier reconciliation is re-running the same preparation (R-B5, last paragraph).

### R-B8 — `load_private_manifest_version(store, *, generation_id, expected_digest)`
- `generation_id` must match `_GENERATION_RE` and `expected_digest` `_SHA_RE`, both exact `str`; else `EarningsEconomicNotFound("unknown_generation")`.
- Read `f"{PRIVATE_PREFIX}/manifests/{generation_id}.json"`, bounded by `MAX_MANIFEST_BYTES`. Absent, or a sha256 other than `expected_digest`, is `unknown_generation`. Never fall back to the current generation.
- Bytes that match the digest but fail `validate_private_manifest`, or a manifest whose `generation_id` differs, are corrupt: `EarningsPrivatePublicationError` (a 503 for Task 6), never not-found.
- Return the validated manifest, v1 or v2. It is not a list API and takes no object key.

### R-B9 — `load_economic_closure(store, *, manifest, slug)`
- `validate_private_manifest(manifest)`. A malformed slug, a v1 manifest, a slug not in `records`, or a slug without a selection is `EarningsEconomicNotFound("unknown_record")`.
- Read exactly the objects that slug's closure names: its record, and each chain entry's workspace, document and source body. Read them bounded by role maximum; leave an absent one out. Call `validate_native_closure(manifest, objects, slugs=(slug,))`.
- `interpretation_unsupported` from the closure becomes `EarningsEconomicUnavailable("interpretation_unsupported")`. Every other closure error propagates unchanged (a 503 for Task 6).
- Return the closure's entry for the slug (`record`, `selection`, `interpretation`, `chain`). This reader checks no rights: Task 5 uses it to carry the prior closure forward.
- **Stale carry (added by the seat after round A's verification).** The signature is `load_economic_closure(store, *, manifest, slug, interpretation="verify")`. `interpretation` must be exactly the `str` `"verify"` (the default, which behaves exactly as above) or `"stale_ok"`; any other value raises `ValueError` before any store read. With `"stale_ok"`, every check of the default path still runs on the record, the selection and every chain entry, and the stored interpretation still passes its shape, schema, `interpretation_id`, `event_id` and issuer checks. If, and only if, `validate_economic_interpretation` then raises `UnsupportedInterpretationVersion` (the stored `build` revisions differ from the running module's), the entry is returned with `"interpretation": None` and one added key, `"interpretation_state": "stale"`, and the rebuild is skipped. Otherwise the full re-validation and rebuild run as in the default path and the entry carries `"interpretation_state": "current"`. A `profile_version` mismatch and a schema mismatch stay `interpretation_unsupported` in both modes: a profile or schema change is a governed migration, not a code refresh. Every other closure error propagates unchanged in both modes. In the default mode the entry keeps exactly its four keys. `load_current_economic_view`, `load_economic_evidence`, `prepare_private_publication` and `publish_private_publication` never use `"stale_ok"`. Only Task 5 does, to re-derive an interpretation from a verified chain after the Task 3 module changed. Why: `CODE_REVISION` is the sha256 of the Task 3 file's bytes. Without this path, the first edit to that file would leave Task 5 unable to read the chain it must extend (R-B6 `chain_not_extended`), and the private refresh would stop for good.

### R-B10 — `load_current_economic_view(store, ticker, *, manifest)`
1. `validate_ticker(ticker)`; a refusal is `EarningsEconomicNotFound("no_slot")`.
2. Read the current generation through R-B2 → `(pointer, manifest_bytes, current)`. If `validate_private_manifest(manifest) != current`, raise `EarningsPrivateManifestNotCurrent` (Task 6 refreshes its cache once and retries).
3. A v1 `current` is `no_slot`. Resolve the ticker with `resolve_ticker(ticker, asof=current["native_source_cutoff"][:10])` behind the R-A8 seam (a raise is `EarningsPrivatePublicationError`, a 503). `None`, or a company without an `economic_slots` entry, is `no_slot`.
4. `assert_native_rights()`; a refusal is `EarningsEconomicUnavailable("rights_refused")`.
5. Load the slot's slug through R-B9 with `current`.
6. Return exactly: `generation_id`; `manifest_sha256` (sha256 of `manifest_bytes`, the bytes actually read); `record_sha256` (the slug's record receipt `sha256` in `current`); `slug`; `interpretation` (the stored object, in `TOP_LEVEL_KEYS` order, unmodified); `source` = `{"document_id": <newest chain document's document_id>, "source_sha256": <its content_sha256>}`. Nothing else. `canonical_json_bytes(view)` contains no object key, no `PRIVATE_PREFIX` and no `"objects/sha256"`.

### R-B11 — `load_economic_evidence(store, *, generation_id, manifest_digest, record_digest, slug, fact_id)`
1. `manifest = load_private_manifest_version(store, generation_id=…, expected_digest=manifest_digest)`.
2. A v1 manifest, a slug without a selection, or a `record_digest` that is not exactly the slug's record receipt `sha256`, is `unknown_record`.
3. The closure through R-B9 with that manifest.
4. `assert_native_rights()` → `rights_refused` (current rights, even for an old pinned generation).
5. **Retention.** Read the current generation through R-B2. If it is not v2, or its `economic_slots` has no entry for the selection's `company_id`, raise `EarningsEconomicUnavailable("evidence_retired")`. (Plan 6.3: "Check current retention/display permission even for old pinned generations.") A newer generation that keeps the company, even under another slug or event, retains the old evidence.
6. `fact_id` must be a `str` equal to one observation's `fact_id`, else `unknown_fact`. An observation with `typed_absence`, or whose `source_excerpt` is absent or not a non-empty `str`, is `absent_fact`.
7. Return exactly: `generation_id`; `manifest_sha256` (sha256 of the bytes read); `record_sha256`; `slug`; `fact_id`; `document_id` and `source_sha256` (the newest chain document's, as in R-B10); `observation` (the stored observation, unmodified); `source_text` = `{"text": <its source_excerpt>, "lang": "en"}`. Only the excerpt leaves the owner, never the source body. Task 6 builds the spec §6.4 response (`header.{en,zh}`, `period`, `source_text`, `precision_note.{en,zh}`) from this result; the owner does not.

### R-B12 — `load_private_record` over a v2 generation
Unchanged for v1 records. For a v2 record: a `page == DOSSIER_PAGE` record raises `EarningsPrivateRecordNotFound("earnings record is not covered")`. A wire record returns its v1 projection: every key except `economic_interpretation`, with `schema` set to `RECORD_SCHEMA`, returned through `validate_v1_record(…, expected_slug=slug)`. The existing record route and the wire page keep working over a v2 generation. `load_private_manifest` and `load_private_context_packet` stay shape-only.

### R-B13 — CI wiring
- A new job `earnings-economic-private-publication`, placed directly above `  earnings-economic-dossier:`, built like the template: `if: ${{ false }}`, `gate: code`, `scope: exclusive`, `timeout-minutes: 20`, ubuntu-latest, Python `"3.12"`. One install step with the comment `# requests and jinja2: the legacy suite's _staged_publication imports scripts.build_earnings_public_wire`, running `pip install pytest pyyaml requests jinja2`. One test step: `python -m pytest tests/test_earnings_private_store.py tests/test_earnings_economic_private_store.py -q`.
- Its `paths:` are the measured import closure of the two suites and the fixture module, sorted and explicit, never a glob. Start from the three test files and the owner, run the closure test, add exactly the paths it lists as missing, and repeat until it passes.
- Add `"earnings-economic-private-publication",` to `CURATED_EXCLUSIVE` in `tests/test_ci_pack.py` directly after `"earnings-economic-source-selection",`, with a one-line comment `# 2026-09-30: CDV-1 Task 4 owns the v2 private generation.`
- **Widenings.** Round A's module-level imports put Tasks 1–3 into the closure of every curated job that reaches the owner. The closure test names the jobs and paths (the seat measured about 23 for `biocatalyst-worker`, 27 `consumer-cyclical-economic-change`, 2 `conviction-profile`, 27 `finance-intelligence`, 5 `industrials-result-cash`, 2 `unrun-picks-boards`; re-measure, do not copy). Add exactly the listed paths, sorted into each job's list. Change no other line of any other job.
- **Dependency law** (seat ruling 2026-09-24). Prove each job you add or widen under its own install line: a fresh venv with exactly that job's `pip install` packages, then for the new job its pytest command, and for a widened job `python -c "import engine.earnings_narrative.private_publication"`. A `ModuleNotFoundError` means adding the package to that job's single install line and proving again.
- `python scripts/check_contract_delta.py --base origin/main` must report 0 introduced.

### R-B14 — deploy restart wiring
The API imports the owner, so every module the owner newly loads must restart the API. In the regex on `app/deploy/update.sh` line 1254 only: add `economic_interpretation` to the `engine/earnings_narrative/(…)\.py` group directly after `digest`, and add the group `engine/earnings_release/(__init__|binding|figures|filing_key|receipts)\.py` directly after it. Add the six paths to `MUST_RESTART`: `engine/earnings_narrative/economic_interpretation.py` after `…/digest.py`, and the five `engine/earnings_release/…` paths after `…/story_packets.py`. Measure the rest: `python -c "import engine.earnings_narrative.private_publication, sys; [print(m.__file__) for m in list(sys.modules.values()) if getattr(m, '__file__', None) and '/engine/' in m.__file__]"` and check every printed repository path against the regex. A path it misses beyond these six goes under GAPS with the seat's name for it; do not widen the regex further.

## FIXTURES (`tests/earnings_economic_private_fixtures.py`)
Extend round A's module; keep every round-A name and behavior.
- `ConditionalCountingStore(CountingLocalStore)` records `conditional_calls` (the keys) and takes four test hooks, all off by default: raise before the conditional write, raise after it wrote, answer the echo read of `POINTER_KEY` with foreign bytes, and write foreign pointer bytes with `put_bytes` right after the first versioned read of `POINTER_KEY` that follows the write of `race_after_key`.
- `NoConditionalStore`: a strict bounded store that delegates to a `LocalStore` and has no conditional methods, so it is not a `StrictConditionalWriteStore`. It counts every call it receives.
- `published_v1_case(tmp_path) -> (store, baseline)`: `_staged_publication(tmp_path / "v1")`, prepare its private stage, publish into `ConditionalCountingStore(tmp_path / "private-r2")`, return the store and the returned pointer.
- `stage_economic_case(tmp_path, case, *, name="economic")` keeps round A's behavior and adds one step: if `tmp_path / "private-r2"` holds a pointer, the stage's `previous_manifest` is `load_private_predecessor(LocalStore(tmp_path / "private-r2"))`; otherwise `None`. This is the convention the plan's test relies on. `name` selects the sub-directory so one test can stage twice.
- A new case `"empty_native"`: a v2 stage with the AAPL wire record, a `native/` directory, empty catalogs, no selection and no slot.
- `fail_source_readback(store, prepared)`: arms the store so that, once `prepared.manifest_key` has been written, reads of the prepared artifact whose `content_type` is `text/plain; charset=utf-8` return different bytes of the same length. Object writes and their echo reads are untouched, so only R-B5 step 7 can see it.
- A rights fixture writes a permitting registry (`sec_edgar`, `derived_display_ok`) under `tmp_path` and patches `private_publication.NATIVE_RIGHTS_REGISTRY_PATH` to it; the refusing variant writes a separate file. Use it (autouse in the v2 publish and reader tests) so that no test passes because rights refused. Never assert what the production registry says.

## TESTS (`tests/test_earnings_economic_private_store.py`; every refusal asserts its class and `exc.reason`)
1. **Plan 4.1, verbatim** — `test_pointer_does_not_move_when_required_source_readback_fails`, exactly as the plan prints it. Beside it: a control twin (same steps without `fail_source_readback`: the pointer moves to the v2 generation), and a reason twin (with the fault: `digest_mismatch`, and `POINTER_KEY` in neither `put_calls` nor `conditional_calls`).
2. **Capability.** `NoConditionalStore`, and a store whose capability check raises: `conditional_write_unavailable`, with zero reads and zero writes recorded.
3. **Uncertain pointer.** Raise before the write: `EarningsPrivatePointerEffectUnknown`, the pointer keeps the old bytes, one conditional call, no `put_bytes` on `POINTER_KEY`. Write then raise: the same error, the pointer holds the new bytes (no restore), one conditional call. Foreign echo: the same error, no restore. The error's three attributes are right, and its message holds no digest. Re-running the same preparation after "write then raise" returns the pointer with zero writes.
4. **Predecessor.** A stage bound to `None` over an installed pointer, and a stage bound to another generation: `predecessor_conflict` with `put_calls == []`. The race hook: `predecessor_conflict`, and the foreign bytes are still the pointer.
5. **Mixed publish and read (4.4).** Publish `valid` over the v1 baseline. `load_private_manifest` returns the v2 manifest. `load_private_record` for the AAPL slug returns canonical bytes equal to the baseline's record. The dossier slug is `EarningsPrivateRecordNotFound`. A v2 wire-record case returns its v1 projection with `schema == RECORD_SCHEMA` and no `economic_interpretation`.
6. **Idempotence (4.4).** Publishing the same preparation again returns the same pointer with no new `put_calls` or `conditional_calls`, and the chain, document ids and interpretation id are unchanged.
7. **Downgrade (4.4).** Over installed v2, a v1 preparation is `downgrade_refused` with `put_calls == []` and the pointer unchanged. A v1 preparation with `retire_slots` is `retirement_invalid`. A v1 publish over a pointer whose manifest was deleted is `installed_unreadable`.
8. **Slots (4.4).** After `valid`, `empty_native` without retirement is `slot_removed`; with `retire_slots=("cik:0000080424",)` it publishes. Retiring a company that is not installed, and one still present in the candidate, is `retirement_invalid`.
9. **Chain prefix.** `valid` then the corrected chain publishes (the chain extends). The corrected chain then the amended chain for the same event is `chain_not_extended`, and so is a candidate that shortens the installed chain.
10. **Cutoff.** A candidate cutoff one second before the installed one is `stale_native_cutoff`; an equal cutoff publishes.
11. **Corrupt immutable (4.4).** After publishing `valid`, rewrite the stored source body with same-length bytes. Re-publishing the same preparation fails with the v1 message "immutable private earnings object differs"; a new candidate naming that object fails with "immutable private earnings object collision". The corrupt bytes stay, the pointer is unchanged, and no `put_bytes` or conditional write targeted that key or the pointer.
12. **Manifest version.** The right id and digest return the manifest. A wrong digest, an unknown id, a malformed id and a malformed digest are `unknown_generation`. After a newer publish, the older generation still resolves to itself. Bytes that match their digest but fail validation are an `EarningsPrivatePublicationError` that is not an `EarningsPrivateRecordNotFound`.
13. **Closure reader.** Returns the dossier slug's chain and interpretation. An unknown slug, the AAPL slug and a v1 manifest are `unknown_record`. A same-length corrupt source body is `digest_mismatch`. A tampered number in the stored interpretation, with every receipt resealed by round A's helpers so all digests match, is `interpretation_mismatch` (the read-time re-validation catches it, not a digest). Patching `pg_profile.PG_PROFILE_VERSION` is `EarningsEconomicUnavailable("interpretation_unsupported")`. **Stale carry:** unpatched, `interpretation="stale_ok"` returns `interpretation_state == "current"` and the stored interpretation. With `economic_interpretation.CODE_REVISION` patched to `"0" * 64`, the default mode is `EarningsEconomicUnavailable("interpretation_unsupported")`, while `"stale_ok"` returns the same record, selection and chain as the unpatched read, with `interpretation` None and `interpretation_state == "stale"`. Under the same patch, in `"stale_ok"`: a same-length corrupt source body is still `digest_mismatch`; an interpretation whose `interpretation_id` no longer equals the selection's, with every receipt resealed, is still `interpretation_mismatch`; and the patched `PG_PROFILE_VERSION` is still `interpretation_unsupported`. `load_current_economic_view` and `load_economic_evidence` are still `interpretation_unsupported`. `interpretation="STALE_OK"`, `interpretation=None` and a `str` subclass instance of `"stale_ok"` each raise `ValueError`, with no store read recorded.
14. **Current view.** Exactly the six keys; `manifest_sha256` equals the pointer's; `record_sha256` equals the manifest's receipt; `interpretation` equals the stored record's; `source` equals the newest document's id and `content_sha256`; no object key or prefix in its canonical bytes. `ZZZZ`, `AAPL` and a v1 current generation are `no_slot`. The previous generation's manifest is `EarningsPrivateManifestNotCurrent`. The refusing registry is `rights_refused`.
15. **Evidence.** Take the view of `valid`, publish the corrected chain, and resolve the first view's first valued fact at its pinned generation: 200-equivalent, its `generation_id` is the first view's, and its `source_sha256` is the first view's `source["source_sha256"]`. A wrong `record_digest` is `unknown_record`; an unknown fact is `unknown_fact`; a typed-absence fact is `absent_fact`; the refusing registry is `rights_refused`; after `empty_native` with retirement, the old evidence is `evidence_retired`. Exactly the nine keys, `source_text == {"text": observation["source_excerpt"], "lang": "en"}`, and no object key in its canonical bytes.
16. **Predecessor reader.** An empty store is `None`; after the v1 baseline it is the pointer minus `schema`; with the installed manifest deleted it is `installed_unreadable`.
17. **Surface.** `validate_generation_id` and `validate_digest` return a real id and digest unchanged and refuse a `str` subclass instance, a non-`str`, upper-case hex and a trailing newline. The four tuples, the class hierarchy of R-B1, `__all__`, and no message with a digest or object key.

## MUTANTS (each: edit, run, quote the failing test NAME, `git checkout -- <file>`, prove `git diff --quiet`)
(a) remove the v1 downgrade refusal at both call sites; (b) skip R-B5 step 7; (c) restore the prior pointer after `EarningsPrivatePointerEffectUnknown`; (b1) replace the conditional write with `put_bytes`; (b2) drop the view's current-manifest comparison; (b3) ignore `record_digest`; (b4) skip the chain-prefix rule; (b5) allow slot removal; (b6) skip the evidence reader's rights check; (b7) skip the retention check; (b8) in `"stale_ok"`, treat every interpretation error as stale; (b9) make the default mode behave as `"stale_ok"`.

## WORK ORDER (short steps; commit and push after each)
1. R-B1 and the surface tests, quoted failing first (RED).
2. R-B2, R-B3, R-B4 and the fixture stores.
3. R-B5, R-B6, R-B7 and test groups 1–11.
4. R-B8 to R-B12 and test groups 12–17.
5. R-B13 and R-B14 in one commit: `ci(earnings): wire the private-generation suites and the owner's import closure`.
6. Mutants, the runs below, the merge check.

## RUNS (quote each rc line under EVIDENCE)
- A clean venv **outside the repository tree**, on CPython 3.12 like CI: `uv venv --python 3.12 <dir>` (uv is `/opt/homebrew/bin/uv`), then `uv pip install --python <dir>/bin/python pytest pyyaml requests jinja2` and nothing else. Quote `<dir>/bin/python --version`. Run each pytest command with `<dir>/bin/python -m pytest …` under `bash -c 'ulimit -s hard; …'`.
- `python -m pytest tests/test_earnings_private_store.py tests/test_earnings_economic_private_store.py -q -p no:cacheprovider` (GREEN; the legacy file unedited and `18 passed` within it).
- The Task 1–3 suites still pass: `python -m pytest tests/test_pg_economic_observations.py tests/test_pg_economic_observations_probes.py tests/test_pg_economic_observations_probes_r1*.py tests/test_pg_economic_source_selection.py tests/test_earnings_economic_interpretation.py -q -p no:cacheprovider`.
- `python -m pytest tests/test_earnings_api.py tests/test_earnings_public_wire.py -q -p no:cacheprovider`. If either needs an omitted sparse tree, quote the error under GAPS; do not opt the tree in.
- `python -m pytest tests/test_ci_pack.py -q -p no:cacheprovider` (the whole file, about 5 minutes).
- `python -m pytest tests/test_deploy_update_self_heal.py -q -p no:cacheprovider` and `python -m pytest tests/test_ship_loop_guard.py -q -p no:cacheprovider -k restart_predicate`.
- The dependency-law venvs of R-B13, each with its install line and result.
- `python -m pyflakes` on the three owned Python files (pyflakes in a second venv).
- `sed -n '33p' engine/earnings_narrative/private_publication.py`; `python scripts/check_contract_delta.py --base origin/main` (quote the summary); `git diff --name-only origin/main...HEAD` (only the seven owned files).

## COMMON RULING (binding)
- **Short steps, pushed as they land.** After each step: `git add <named paths>`, commit with a message that names only that step's hunks, then push. Push an unfinished step as `wip(...)` rather than holding it.
- **Real probes.** A test must be able to fail against a plausible wrong implementation. Never restate the code in a test. A refusal test that would also pass because rights, capability or the predecessor refused first is vacuous: give each refusal test a passing twin or a reason assertion.
- **One rule, one place.** If a rule seems to need a special case, report it under GAPS instead.
- **The PR.** It exists; do not open another and do not edit its body. The seat writes the body.

Before the final push: `git fetch origin main`. If `origin/main` moved, `git merge --no-ff origin/main` (never rebase). On a conflict keep both sides and never discard main's side. A conflict outside OWNED FILES means STOP with STATUS BLOCKED naming it. After any merge, re-run the RUNS, re-measure R-B13's closure, and re-check line 33.

## GAPS RULE
If an R-B item contradicts the plan text quoted here, Tasks 1–3's measured behavior, round A's code, or another R-B item, or cannot be met, implement everything else and report that item under GAPS with its reason. The seat rules on it. Never silently drop or reinterpret an item.

## NOT DONE UNLESS
- Every RUNS line is quoted with its rc, and the new suite and the legacy suite pass in the clean venv.
- The 17 test groups exist, the plan's test is verbatim, and each refusal test asserts a class and a reason.
- The twelve mutants each fail a named test and are restored.
- Line 33 is unchanged and lines 13–33 match R-A1 except the one import line R-B5 needs (`from engine.research_vault.r2_store import StrictBoundedReadStore, StrictConditionalWriteStore, Store`), which is the only change above line 33.
- The v2 path never calls `put_bytes` on `POINTER_KEY` and calls the conditional write at most once per publish (quote the `git grep -n "POINTER_KEY"` lines).
- Every commit carries the trailer and is pushed, with no force and no amend.

## RETURN (final message, exactly these sections)
- **STATUS:** COMPLETE | PARTIAL | BLOCKED.
- **RESULT:** head sha; files; each R-B item with its line refs; the public names you added; the new job's `paths:` count and each widened job with its added-path count.
- **EVIDENCE:** the C0 outputs; quoted rc lines for RED, GREEN, the legacy suite, the Task 2 and Task 3 suites, `tests/test_earnings_api.py`, `tests/test_ci_pack.py`, the deploy tests, each dependency-law venv, each mutant with its failing test name, pyflakes, contract-delta and the line-33 check.
- **GAPS.**
- **DEVIATIONS:** each with its R-B id, or "none".

Then EXACTLY ONE final stdout sentinel line `<LABEL>: <STATUS> <sha>`.
