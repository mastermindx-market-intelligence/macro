# Consumer Defensive CDV-1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. Fable is the Chairman-selected principal integrator; routine engineering belongs to the existing eligible capacity fabric. This document does not bind a receiver or start a worker.

**Goal:** Deliver one real, current-source P&G demand-and-earnings explanation in the existing Staples research journey, with exact private evidence drilldown, correction-aware currentness, and unchanged legacy market decisions.

**Architecture:** Reuse the native Earnings issuer/profile, source-document, event/workspace and fiscal identity contracts. A bounded deterministic interpretation becomes a versioned member of the existing private Earnings publication, using its current Research Vault store and pointer. The accepted shared sector shell renders the result; the browser neither calculates financial conclusions nor owns source truth.

**Tech Stack:** The repository's existing Python/pytest, Decimal, native JSON validators, FastAPI, Jinja2, vanilla JavaScript and browser-test environment. Use the implementation checkout's locked versions; no new data provider, framework, model runtime or production dependency is introduced by this plan.

**Spec:** `docs/superpowers/specs/2026-09-23-consumer-defensive-economic-dossier-design.md` at `de3086fff1a883f2375ced3c9e8c713e8566f29b`, plus the six clarifications in `research/consumer_defensive/CONSUMER_DEFENSIVE_R5_DESIGN_REVIEW_2026-09-23.md` at `bc9c2426c693f478c007c517d44e69b88d4b1b4f`. The full six-milestone destination remains in `CONSUMER_DEFENSIVE_MASTERPLAN_R5_2026-09-23.md` at `5fa43c0585f979263a2a7e28e4b468077c14aa55`.

## Global Constraints

- The target native shape remains `event_fact.v1`.
- The outer `event_workspace.v1` remains backward-readable.
- Cap the selected display at 24 native observations, four source workspace revisions and 24 comparison rows.
- The minimum useful release does not require an LLM call.
- A historical user query must not fall back to the newest source when the requested vintage is absent.
- Use the current `require_user` then `enforce_site_full(always=True)` order.
- Preserve private/no-store, Vary Authorization, nosniff and noindex/noarchive on success and error.
- A company link requires the existing validated native issuer/listing bridge.
- A GMI membership link requires an admitted relationship.
- No browser calculation may change numeric or qualitative owner conclusions.
- All rank/gate/size/originate/entry/Prophet effects remain literal false.
- New detailed content is private by default. No protected payload in public Git, HTML/JSON, source maps, caches, telemetry or an alternate R2 mirror.
- Native organic sales are not household consumption. Combined volume/mix is not pure volume. Reported and core EPS are separate definitions, not competing truth claims.
- This research branch remains documentation-only. Do not merge, rebase, deploy or put implementation on #7792 merely to execute the plan.

## Review Focus

1. A newer filing is discovered but its exhibit cannot be fetched: old evidence may remain visible, but it must say current processing is pending rather than up to date. Task 2 tests this.
2. A number remains valid while table columns change order: the parser must bind the correct period and basis or emit typed absence, not trust the old column position. Task 1 tests this.
3. An unrelated normal wire publication follows a v2 launch: protected native evidence must persist in the same publication closure and must not be silently downgraded or lost. Tasks 4 and 5 test this.
4. A source drawer opens after a newer generation has been published: it must show the exact evidence supporting the already displayed claim, or a clear unavailable result, never a different vintage. Task 6 tests this.
5. A member logs out while a request is pending: old responses and private drawer content must be discarded; no storage or telemetry may retain them. Task 7 tests this.

---

## 0. Authority, source pins and evidence boundaries

Operation: `gmi-consumer-defensive-research-20260923-sol-001`. Carrier: Macro #7792 / `sol/consumer-defensive-research-20260923`. This is the incumbent research/planning operation, not a newly admitted Executive job.

The Chairman's response to the written R5 review was "good job, continue next turn". This continues the design into implementation planning. It does not certify source retention, technical review or runtime execution. The final buildout method remains Fable-led integration with existing eligible workers. There is no need to ask the Chairman to repeat the original research commission or select that method again.

Fresh protected procedure: `Mastermind@a7d2b3049e5cdc523e91e61a6e9d70a1cb911157`, Skillpack 1.0.1/bootstrap 1. INDEX and ACTIVE_EXECUTION changed and were read at this revision; companion blobs were checked against their complete previously loaded text. The current procedure scopes gates to the affected action and rejects duplicate administrative approvals for routine commissioned work. Actual source custody, reserved architecture/privacy decisions and platform consent remain mandatory.

Implementation inspection pin: Macro `dd4d965de7d52f4c68f6dbc984c7a05a70e0d62b`. Research base remains `c4da107fe729e46b4d4036b3e0e290390315d0fd`; no rebase occurred. Before a product write, refresh only the owned paths, relevant active writers and effects against then-current main. Do not treat an old author or an inaccessible status as proof that a source lease expired.

### Current source observations

| Source at inspection pin | Verified implication |
|---|---|
| `scripts/refresh_event_workspaces.py` | `acquire_results_filing` already discovers SEC results exhibits, but discovery can skip a failed newer candidate and return an older one. The public refresh is not a private PG admission path. |
| `engine/company_intelligence/event_workspace.py` | Native generation preview exists; workspace generation hashing includes build clock and predecessor. Reuse it, including semantic-no-op handling. |
| `engine/company_intelligence/documents.py` | `source_document.v1` and `source_span.v1` distinguish held-byte replay from address-only references. |
| `engine/earnings_release/binding.py` | `BoundRelease.source` is the document's raw source string. Span coordinates are UTF-8 bytes of that bound string, not automatically the original HTTP octets. |
| `engine/earnings_narrative/private_publication.py` | The complete staging closure and manifest currently accept record/context objects. New native roles require explicit versioned extension. One current pointer already exists. |
| `scripts/build_earnings_public_wire.py` | The existing normal producer stages private records/context as part of the wire run; public files remain redacted. The economic extension must join this normal transaction, not an after-the-fact append. |
| `app/earnings.py`, `tests/test_earnings_api.py` | Existing paid auth, private headers, safe error mapping and one cache-refresh-on-missing behavior are reusable. |
| STSI #7777 | Open/unmerged at `4122e3b7e1524482216fb156f201f8229c14011b`; five-file contract slice only. The completed shared mount is not established by that PR. |

No fresh live PG accession, retained document, production identity or deployment has been certified in this planning turn. The issuer's July 29, 2026 release is an external regression-design reference. Real source selection uses the existing collector at execution time. A search result or these research values must never be converted into a forged native receipt.

### Four action-local prerequisites

G1: The Earnings owner accepts the bounded PG metric definitions and private admission policy before producer enrollment. G2: Real issuer/source/retention evidence exists before any live claim is published. G3: Private publication/readers accept v2 closure and downgrade protection before enabling v2 data. G4: The shared STSI/F04 owner supplies or accepts the existing-shell mount before the sector UI is released.

Tasks can be implemented and tested in an isolated candidate without claiming these live prerequisites have passed. A held shared mount does not stop a path-disjoint parser or publisher test. It also does not authorize a competing shell. Source-writer and effect fences remain binding.

## 1. File responsibilities and dependency graph

All new paths in this section are planned additions, not claims that those files exist.

| Task | Source responsibility | Planned paths |
|---|---|---|
| 1 | PG native semantics, extraction and strict selected-fact validation | Create `engine/company_intelligence/pg_profile.py`, `engine/company_intelligence/economic_observations.py`; modify `issuer_profiles.py` only at the profile/publication-policy dispatch seam; create `tests/test_pg_economic_observations.py` and `tests/earnings_economic_fixtures.py`. |
| 2 | Source selection/currentness and private native preparation | Modify `scripts/refresh_event_workspaces.py` in the existing acquisition helper; add the private native-preparation function to `pg_profile.py`; create `tests/test_pg_economic_source_selection.py`. |
| 3 | Deterministic explanation, comparisons and semantic output validation | Create `engine/earnings_narrative/economic_interpretation.py`, `tests/test_earnings_economic_interpretation.py`. |
| 4 | Existing private record/manifest evolution and exact evidence closure | Modify `engine/earnings_narrative/private_publication.py`, `tests/test_earnings_private_store.py`; create `tests/test_earnings_economic_private_store.py`. |
| 5 | Normal producer integration and continuity across runs | Create `engine/earnings_narrative/private_economic_stage.py`; modify `scripts/build_earnings_public_wire.py`, `scripts/publish_company_intelligence_r2.py`, and the existing `earnings-public-wire.yml` step/arguments only as needed; create `tests/test_earnings_economic_refresh.py`. |
| 6 | Authenticated current-selector and pinned evidence read | Modify `app/earnings.py`, `tests/test_earnings_api.py`; create `tests/test_earnings_economic_api.py`. |
| 7 | Existing-shell display and compact navigation | Create `templates/earnings_wire/earnings-economic.js` and a shared partial `templates/earnings_wire/_economic_dossier.html.j2`; modify accepted shared hooks in `templates/sector.html.j2` and `templates/state_of_themes.html.j2`; create `tests/test_earnings_economic_browser.py`. No independent layout system. |
| 8 | CI, release qualification and real-path acceptance | Extend the existing CI command group containing `tests/test_earnings_private_store.py` in `.github/ci/legacy-jobs.yml`; add the new Python suites there with existing dependencies. Extend existing publisher/liveness tests, not a second workflow or scheduler. |

No changes to GMI membership, ThemeState, Prophet, Board V2, entry policy, model routing, token balancing or portfolio sizing belong to these tasks.

Dependency order: Task 1 -> Task 2 and Task 3; Tasks 1-3 -> Task 4; Tasks 2-4 -> Task 5; Task 4 -> Task 6; Tasks 3 and 6 plus G4 -> Task 7; all -> Task 8. Tasks 2 and 3 may overlap only with disjoint file grants. Task 4 owns private-publication edits exclusively; Task 6 must not edit that file independently. This is one integrated vertical, not eight simultaneous writers or eight automatic PRs.

## 2. Contract decisions used by every task

### 2.1 Native selected observations

Use existing `event_fact.v1` present/absence shapes unchanged. Add no source scope JSON hidden inside a string. Each selected metric has one code-reviewed definition in `pg_profile.py`: value kind, unit, scale, accounting/perimeter basis, company or segment scope, quarter duration, and allowed comparison family.

The selected namespace is `pg_` followed by a finite reviewed key. It is an issuer profile vocabulary, not a global registry or new identity authority. The twenty proposed keys are:

```
pg_reported_sales_growth_pct
pg_organic_sales_growth_pct
pg_total_volume_growth_pct
pg_organic_volume_growth_pct
pg_price_contribution_pp
pg_mix_contribution_pp
pg_fx_contribution_pp
pg_other_contribution_pp
pg_diluted_eps
pg_prior_diluted_eps
pg_reported_eps_growth_pct
pg_core_eps
pg_prior_core_eps
pg_core_eps_growth_pct
pg_core_reconciliation_context
pg_beauty_organic_sales_growth_pct
pg_grooming_organic_sales_growth_pct
pg_health_care_organic_sales_growth_pct
pg_fabric_home_organic_sales_growth_pct
pg_baby_feminine_family_organic_sales_growth_pct
```

`pg_core_reconciliation_context` is a bounded native text observation, not a number. Price, mix, FX and Other are contributions to a reported growth bridge; retain the original percentage display label and semantic contribution class. Other is not silently decomposed into acquisitions and rounding. Total versus organic volume definitions remain distinct. Five segment growth rows are optional; do not add them into sector breadth or profit purity.

For prior EPS facts, `period` identifies the prior fiscal interval even though the fact is present in the current release. Definition metadata ties current/prior keys to the same economic measure. The event ID identifies the source event, not the period being measured. Fiscal interval and publication/observation clocks must remain distinct.

### 2.2 Strict selected-fact checks

`validate_selected_facts(workspace, *, source_texts, fiscal_scope)` returns the selected native rows only after checking: exact present/absence key sets; at most 24 selected observations; unique fact IDs and metric/scope/period keys; correct event; finite non-boolean numbers where numeric; recognized units/bases; valid quarter/prior interval; body digest and byte replay; and mutually exclusive value/absence. The caller supplies `fiscal_scope` as four ISO dates `(current_start, current_end, prior_start, prior_end)` from the admitted source/calendar binding; validate their ordering, expected fiscal pair and quarter duration. This is not a consumer-selected override. Its policy is opt-in for the new profile; it does not reinterpret legacy workspaces globally.

`source_texts` is a caller-held mapping from native document ID to the exact decoded text bound by the native document. It is not a global document store. Missing text refuses a purported byte-replayed fact. Native `typed_absence.v1` reasons stay in the existing closed vocabulary. Economic comparison absences belong in the derived interpretation, not invented native absence reasons.

### 2.3 Source capture and native preparation

The existing acquisition helper gains an opt-in trace result while retaining its exact legacy return when the option is absent. A trace records the ordered SEC candidates and their actual outcomes: excluded non-results, no exhibit, fetch failure, decode failure, selected. It also preserves the highest relevant known candidate, selected candidate, source metadata and real observation clock. A failed newer fetch produces pending/unverified currentness, not a newer-success claim.

A native acquisition result distinguishes received bytes and decoded text. The decoded text's UTF-8 bytes define the existing span digest; the received-byte digest and declared encoding are separate transport provenance. No `errors='replace'` decode may mint exact financial evidence. Store both bodies only within the existing approved private retention/publication owner when they differ; do not substitute a hash of JSON or a page URL.

`prepare_pg_workspace(acquisition, *, prior, observed_at)` uses the native registry and `build_event_workspace` with the PG profile, and uses `preview_generation_identity` to freeze a native workspace without the public writer. Carry unchanged first-observed clocks and corrected state forward. Reuse identical prior content when the native input, profile version and interpretation-relevant context did not change. Do not hash a new wall clock into an unchanged economic result simply to create activity.

### 2.4 Derived interpretation wire

`earnings.economic_interpretation/v1` is a proposed closed, versioned derived shape. It contains identity; build/version/input receipts; selection/currentness; native fact handles; demand/earnings/optional segment findings; missing context; next evidence; clocks/coverage; and all-false authority. The exact top-level keys are:

```
schema interpretation_id issuer event_id build selection observations
comparisons findings missing_context next_evidence quality clocks authority
```

Each observation is a native handle `(workspace_generation_id, event_id, fact_id)` and display metadata. Numeric values returned to the browser are verified projections of the native rows, never authoritative independent facts. Comparison rows identify formula, input handles, result, rounding and state. Revalidate native inputs and recompute deterministic relationships at the trusted read boundary before rendering an explanation from an untrusted stored mapping.

`authority` has exactly six boolean keys: `can_rank`, `can_gate`, `can_size`, `can_originate`, `can_open_entry` and `may_modify_prophet`; every value is literal false. Native workspace `authority="context_only"` remains a separate, unchanged native field. No missing or extra authority key is accepted.

`semantic_revision` is the digest of the admitted PG metric/profile definition and `code_revision` is the digest of the deterministic interpreter code closure, supplied by the trusted builder from its actual source revision. Arbitrary browser/model strings are not code provenance. The trusted read uses the matching supported rule version; an unsupported historical version returns unavailable rather than silently recomputing history with current rules.

`interpretation_id` derives from canonical inputs, selected semantics and code version. Exclude wall-clock-only display rebuild time. Currentness is a separately bound observation; a material currentness change can create a new derived result without changing the source revision. Never label that as an issuer correction.

### 2.5 Private publication wire and lifetime

Keep the existing `PRIVATE_PREFIX`, `POINTER_KEY`, object store, generation transaction and private route family. No second current file, lookup service, queue or curation store.

`earnings.tier_payload/v2` preserves v1 record fields and adds required `economic_interpretation`, either a valid object or a typed unavailable result. V1 remains byte-semantically readable. V2 permits the explicit page kind `earnings_economic_dossier` for a native-only record; do not fabricate a public story packet just to satisfy old provenance. For this kind, public_facts is zero, locked_facts is the count of actual displayed native observations, and legacy HTML fields can be empty. The shared consumer uses the typed interpretation, not HTML carrying a hidden financial model.

`earnings.private_manifest/v2` preserves existing record/context catalogs and their original source binding, and adds a closed `native` section plus `previous_manifest` receipt. The native section contains `workspaces`, `documents`, `source_bodies`, `selections`, and `economic_slots`. These are receipt roles in the same publication, not new canonical stores. Each record names its actual native dependencies. Its SEC source is not attributed to the unrelated story-packet generation in the legacy source block.

`economic_slots` resolves an already-admitted native issuer to one record slug and selected event for current display. It is a derived display selector in this manifest, not an issuer registry, second event catalog or security-resolution authority. Symbols resolve through the accepted native issuer registry. Do not key canonical economic identity solely by a ticker.

Workspace/document metadata use existing native JSON shapes. Raw and decoded source bodies use role-bound content-addressed artifacts in the same private owner. Extend receipt validation to explicit JSON, raw-byte and UTF-8-text roles; the role fixes suffix/media type and maximum. Existing JSON objects stay unchanged. Any new native-role metadata is closed per role. JSON objects use canonical UTF-8 encoding; raw bodies preserve received octets; text bodies preserve the exact decoded UTF-8 span string. Each role has its own byte count/digest. Source-document identity never equals its content hash by assumption. Limit this first slice to four workspace revisions, 24 displayed facts, 24 comparisons, and eight MiB per retained source body. These source limits are proposed safety bounds; oversized input is held rather than truncated into an apparently exact receipt.

Every reference must resolve to a present, digest-checked artifact of the right role and identity. Reject missing, unused/unexpected, cyclic predecessor, cross-issuer, mismatched-source and over-limit artifacts. A matching current pointer alone does not prove closure. Preserve existing complete readback and pointer-last promotion.

The four-workspace bound applies to a single selected record/read closure; it is not permission to delete older immutable generations or truncate the historical source record. Old generations remain addressable under their existing retention policy, even when the current record no longer selects them.

A v1-only candidate must not overwrite an installed v2 generation or remove a v2 slot without an explicit owner-controlled retirement. Normal runs rederive or receipt-verify retained native records, and keep their original clocks. A missing prior read is an error, not empty history. Withdrawal or retention expiry is explicit and does not authorize a fabricated replacement.

### 2.6 API and display snapshot binding

Retain `/api/earnings/v1/records/{slug}`. Add an adjacent read-only `/api/earnings/v1/economic/{ticker}` selector in the same router, auth and private-store owner. It returns a safe view with the selected immutable generation/record identity and interpretation. It never scans arbitrary storage keys or falls back to a public source.

Add `/api/earnings/v1/records/{slug}/economic-evidence/{fact_id}` with exact generation, manifest-digest and record-digest bindings from the displayed response. Authorize first; validate the generation using its existing immutable manifest and closure. Resolve only a fact named in the selected record. A changed current pointer cannot redirect this request to a different revision. A missing requested vintage produces an unavailable/missing response, never a latest fallback.

Evidence responses expose permitted inert context and supporting header/period information, not the whole private raw body, credentials or object keys. Apply source display/retention rights at read time. Retired/restricted evidence is unavailable even if older bytes remain physically stored.

## Task 1: Native PG profile and strict scoped facts

**Files:** the Task-1 paths in section 1. No live source publication in this task.

**Interfaces:** `pg_issuer()` returns the existing `IssuerIdentity`; `pg_profile()` returns existing `IssuerProfile`. `extract_pg_release_facts(*, bound, document_id, event_id, fiscal_period)` returns native rows. `validate_selected_facts(workspace, *, source_texts, fiscal_scope)` returns validated rows or raises `EconomicObservationError`. Add a keyword-only `publication='public'|'private'` selection to existing profile lookup only where needed; default legacy behavior remains identical. Do not append PG to the public production registry.

- [ ] **1.1 Write the discriminator fixture and failing tests.** Create a small original synthetic HTML release in `tests/earnings_economic_fixtures.py`. It must contain a full-year table before a quarter table, repeated EPS values, a driver table, one combined-volume/mix negative control, a changed-order version, a dash/blank pair and a hostile markup version. Its docstring says synthetic, never live source. Build it through native `bind_release_document`; compute actual fixture hashes and span receipts, never literal invented digests. Provide fixture functions `pg_bound_case(kind)`, `pg_workspace_case(kind)` and `pg_source_texts(kind)` for the following tests and later tasks.

```python
@pytest.mark.parametrize('kind', ['annual_first', 'columns_reordered'])
def test_quarter_and_basis_are_bound(kind):
    workspace = pg_workspace_case(kind)
    rows = validate_selected_facts(
        workspace, source_texts=pg_source_texts(kind),
        fiscal_scope=('2026-04-01', '2026-06-30', '2025-04-01', '2025-06-30'),
    )
    by_metric = {row['metric']: row for row in rows if 'value' in row}
    assert by_metric['pg_diluted_eps']['value'] == 1.25
    assert by_metric['pg_prior_diluted_eps']['value'] == 1.50
    assert by_metric['pg_core_eps']['value'] == 1.45
    assert by_metric['pg_prior_diluted_eps']['period'] == '2025-06-30'
    assert all(row['event_id'] == workspace['event_id'] for row in rows)
```

The numbers above are synthetic test values, intentionally not copied current source facts. Add parameterized failures for duplicate metric/fact ID, boolean number, infinity/NaN, wrong event/body/period/basis/unit, both value and typed_absence, unknown extra field, and 25 selected observations. Blank is absent; dash is zero only when the fixture supplies an explicit neutral convention. Unknown or mixed volume never passes the pure-volume rule. Include multibyte characters before a numeric token to expose byte-versus-character indexing defects.

- [ ] **1.2 Run the new file RED.** `python -m pytest tests/test_pg_economic_observations.py -q`. Expected failures are missing new profile/validator or semantic mismatches, not missing third-party dependencies. Record the actual result.

- [ ] **1.3 Implement profile semantics and extraction.** Use the native normalized disclosure blocks and byte receipts. Match heading, row label, column header and period together; permit reordering, refuse ambiguity. Reuse existing receipt helpers rather than implementing substring-hash provenance again. Extract literals only; computed growth belongs in Task 3. Reconciliation text is bounded and source-backed. Store the twenty definitions in the profile module, including permitted current/prior pair and segment scope.

```python
# Dispatch stays explicit; this is an addition to the existing lookup seam.
if publication == 'private' and normalized_ticker == 'PG':
    from .pg_profile import pg_profile
    return pg_profile()
# Existing public dispatch continues unchanged after this branch.
```

Validate the mode before dispatch. Caller mode alone does not authorize publication; the actual public writer guard in Task 5 is independently mandatory. Bind real PG identity from the native identity owner during source admission, not from a generated ticker guess. No global issuer registry is created.

- [ ] **1.4 Run GREEN and mutation controls.** Restore a positional annual-column selection, skip body replay, and zero-fill a blank one at a time; each mutant must fail a named test. Then rerun the full new file and existing issuer/workspace tests selected by `python -m pytest tests -k 'issuer_profile or event_workspace' --collect-only -q`; run the exact collected existing files without unrelated suites.

- [ ] **1.5 Commit the independently reviewable result.** `git add engine/company_intelligence/pg_profile.py engine/company_intelligence/economic_observations.py engine/company_intelligence/issuer_profiles.py tests/test_pg_economic_observations.py tests/earnings_economic_fixtures.py && git commit -m 'feat(earnings): validate private PG economic facts at source scope'`.

## Task 2: Truthful source selection and private native preparation

**Files:** existing `scripts/refresh_event_workspaces.py`, new `pg_profile.py` preparation seam, `tests/test_pg_economic_source_selection.py`.

**Interfaces:** Extend `acquire_results_filing(*, cik, http_get, accession=None, trace=None)` with an optional callback that receives a completed bounded acquisition trace. Default return and public behavior stay unchanged. `prepare_pg_workspace(acquisition, *, prior, observed_at)` returns native workspace, native document metadata, decoded source, received-byte receipt and currentness context; it performs no public write. The preparation result is an in-memory input to Tasks 3-5, not another persisted ledger.

- [ ] **2.1 Write failing tests around the existing injectable HTTP seam.** Use a fake `http_get` mapping of submissions, SGML and exhibit responses. The fixture has a newer results filing returning 503, an older valid results filing, and a still newer non-results filing. The trace must distinguish these outcomes. Also test 8-K/A, no report date, missing acceptance timestamp, two plausible exhibits, malformed encoding, same-source rebuild and unavailable prior generation.

```python
def test_older_fallback_is_not_current():
    events = []
    selected = acquire_results_filing(
        cik='0000080424', http_get=fixture_http_get('newer_fetch_failed'),
        trace=events.append,
    )
    assert selected['accession'] == fixture_accession('older')
    trace = events[-1]
    assert trace['newest_relevant_accession'] == fixture_accession('newer')
    assert trace['selected_accession'] == fixture_accession('older')
    assert trace['currentness'] == 'newer_source_pending'
    assert trace['excluded_non_results'] == 1
```

Define `fixture_http_get` and `fixture_accession` in the Task-1 helper module; they return synthetic fixture mappings, not a real SEC accession. A callback-less call must return exactly the prior legacy dictionary. A failure to read the prior published object must raise, not reset first observation or corrected state.

- [ ] **2.2 Run RED.** `python -m pytest tests/test_pg_economic_source_selection.py -q`.

- [ ] **2.3 Add the trace to the existing acquisition loop.** Do not introduce another network client, retry count, source queue or discovery algorithm. Capture received bytes and chosen decode without modifying the old return by default. Retain candidate outcome history at native collector scope. Limit trace size; if bounded recent coverage cannot establish currentness, return unverified rather than declare complete global SEC coverage. Exact-accession requests never silently fall back.

Prepare the native event using admitted registry, explicit fiscal scope, actual source clocks and the existing builder. Do not infer fiscal quarter solely from the 8-K report date. The selected release may contain both Q4 and FY; choose the quarterly event only after document-level scope validation. Preserve the distinct native filing/event grouping conventions. PG's admission requires current CIK/listing/fiscal-calendar evidence; absent authority is a source gate, not a synthetic default.

Use `preview_generation_identity(workspaces, generated_at, previous_generation_id=...)` for native identity without invoking the public writer. Freeze source-text and received-byte hashes separately. Call native `SourceDocument` validation. Never set `holds_bytes=True` based solely on a successful URL fetch if the owner has not retained and read back the source.

- [ ] **2.4 Run GREEN and correction tests.** Verify unchanged source carries first observation; changed bytes at the same URL yield a new revision; an 8-K/A is not a second fiscal quarter; a code-only change does not alter SEC acceptance time; missing prior bytes do not create a new root. Run existing acquisition/refresh tests located with `python -m pytest tests -k 'refresh_event_workspaces' --collect-only -q`, then their exact files.

- [ ] **2.5 Commit.** `git add scripts/refresh_event_workspaces.py engine/company_intelligence/pg_profile.py tests/test_pg_economic_source_selection.py tests/earnings_economic_fixtures.py && git commit -m 'feat(earnings): preserve private acquisition currentness and revision clocks'`.

## Task 3: Deterministic demand and earnings interpretation

**Files:** `engine/earnings_narrative/economic_interpretation.py`, `tests/test_earnings_economic_interpretation.py`.

**Interfaces:** `build_economic_interpretation(workspace, *, source_texts, fiscal_scope, selection, semantic_revision, code_revision)` returns a closed interpretation. `validate_economic_interpretation(payload, *, workspaces, source_texts, fiscal_scope)` recomputes reference and comparison validity. `compare_eps(current, prior, *, precision)` returns a derived comparison or an explicit non-comparable result. Inputs are validated native facts, not a browser's floats.

- [ ] **3.1 Write rule and arithmetic tests before code.** Fixtures supply positive headline growth/flat organic; combined volume/mix; opposite reported/core EPS direction; negative/zero/uncertain prior EPS; optional segment and reconciliation absence; 25 comparison rows; fake fact selector; changed code version; identical inputs. All source fields come through the Task-1 fixtures. The new builder receives `fiscal_scope` explicitly from Task 2; it may not reconstruct quarter duration from an isolated end date.

```python
def test_positive_headline_does_not_become_positive_organic_demand():
    result = build_case_interpretation('headline_positive_organic_flat')
    codes = {item['rule_id'] for item in result['findings']}
    assert 'reported_vs_organic_difference' in codes
    assert 'consumer_demand_unchanged' not in codes
    assert all(value is False for value in result['authority'].values())
    assert 'consensus' in {item['subject'] for item in result['missing_context']}


def test_zero_prior_has_no_invented_growth_rate():
    result = compare_eps(Decimal('1.20'), Decimal('0'), precision=None)
    assert result['state'] == 'not_comparable'
    assert result['value'] is None
    assert result['reason'] == 'nonpositive_prior'
```

`build_case_interpretation` is a test helper in the Task-1 module that calls the actual new builder with actual fixture inputs; it must not hardcode the expected findings. Keep it small and make its contents visible to the reviewer.

- [ ] **3.2 Run RED.** `python -m pytest tests/test_earnings_economic_interpretation.py -q`.

- [ ] **3.3 Implement closed shapes and ordered rules.** Use Decimal for derived arithmetic, preserving the source's stated rate as a separate value. Missing inputs produce a named missing-context item or a declined comparison, not zero. EPS comparisons require same measure family, unit, share/accounting basis and correct fiscal pair. A provided uncertainty interval touching zero refuses an unqualified rate; a merely small positive number has no invented threshold.

```python
# Core formula only after the comparison contract validates the pair.
rate = (current / prior - Decimal('1')) * Decimal('100')
# Store it as derived, with both native input handles and explicit precision.
```

Implement fixed rule IDs for headline/organic difference, positive organic with nonpositive pure volume, reported/core earnings disagreement, incomplete margin-to-cash bridge, segment-scope limitation and missing consensus. Prefer native reported EPS growth when available; derived growth is labeled approximate if amounts are rounded. No consensus beat, recommendation, score or cross-company ranking. Source prose can be displayed inertly but never selects rules, tools or privileged actions.

- [ ] **3.4 Run GREEN and integrity mutations.** A comparison input replaced with another period must fail. Altering the stored result without changing inputs must fail trusted validation. A rewrite-only version change changes derived identity while native source clocks remain identical. A source correction invalidates dependent comparison handles. Run all three new unit files together.

- [ ] **3.5 Commit.** `git add engine/earnings_narrative/economic_interpretation.py tests/test_earnings_economic_interpretation.py tests/earnings_economic_fixtures.py && git commit -m 'feat(earnings): derive bounded source-linked economic explanations'`.

## Task 4: Extend the existing private generation, not a sidecar

**Files:** `engine/earnings_narrative/private_publication.py`, existing store tests and new `tests/test_earnings_economic_private_store.py`.

**Interfaces:** Existing `prepare_private_publication(stage_dir)`, `publish_private_publication(store, prepared)`, `load_private_manifest(store)` and `load_private_record(store, slug, manifest=...)` remain the publisher/reader entry points. New private-owner helper `load_economic_closure(store, *, manifest, slug)` returns the verified native workspace/document/body dependencies and derived result. New `load_private_manifest_version(store, *, generation_id, expected_digest)` resolves only a validated immutable manifest in the existing namespace; it is not a list or arbitrary-object API. Task 4 also implements `load_current_economic_view(store, ticker, *, manifest)` and `load_economic_evidence(store, *, generation_id, manifest_digest, record_digest, slug, fact_id)` for Task 6. The current view includes `generation_id`, `manifest_sha256`, `record_sha256`, `slug`, `interpretation` and the permitted native evidence handles, never private object keys. Its receipt is built from the actual validated current pointer/manifest bytes, not a caller-supplied digest.

- [ ] **4.1 Write failing compatibility and closure tests.** Extend the existing test fixture `_staged_publication` rather than inventing a second Store implementation. Add `stage_economic_case(tmp_path, case)` to the shared test helper: it uses the existing wire/context fixture and native synthetic PG preparation, writes only the permitted off-repo stage tree, and computes all receipts from those bytes. Test v1-only, v1/v2 mixed records, standalone native economic record, absent native source, wrong role/hash/size/issuer, malicious path, symlink, duplicate key with different bound, oversized source, future source clock, predecessor cycle and unsupported schema.

```python
def test_pointer_does_not_move_when_required_source_readback_fails(tmp_path):
    store, baseline = published_v1_case(tmp_path)
    before = store.get_bytes_strict_bounded(POINTER_KEY, MAX_POINTER_BYTES)
    stage = stage_economic_case(tmp_path, 'valid')
    prepared = prepare_private_publication(stage)
    fail_source_readback(store, prepared)
    with pytest.raises(EarningsPrivatePublicationError):
        publish_private_publication(store, prepared)
    assert store.get_bytes_strict_bounded(POINTER_KEY, MAX_POINTER_BYTES) == before
```

The fault fixture must fail the pre-promotion immutable readback, not simulate a pointer-write response loss. A pointer dispatch followed by uncertain readback is a different effect state and must not be blindly retried or automatically restored over a newer writer. Include a separate test for that uncertainty boundary.

- [ ] **4.2 Run RED.** `python -m pytest tests/test_earnings_economic_private_store.py -q`.

- [ ] **4.3 Implement explicit version dispatch and role validation.** Keep named v1 constants readable; add explicit v2 constants. Do not change `RECORD_SCHEMA` to v2 and accidentally cause every old constructor to emit a new schema with old fields. Dispatch on schema and exact key set. Existing v1 code paths must return the same canonical bytes and error behavior.

The v2 manifest's native roles bind each workspace to its actual SourceDocument, source-body receipt, fiscal event, profile revision and selected interpretation. Validate closure before writing and on trusted reads. A native-only record may coexist with the real existing wire/context generation; it does not require a PG story packet. Its source provenance remains separately native. If the existing wire/context generation is genuinely unavailable, this plan does not authorize inventing empty valid-looking wire provenance or another pointer; retain the last verified publication and report the owner dependency. A native-only record is not required to invent a story packet, but it cannot modify the provenance of the existing wire records. Its empty legacy HTML fields are not an excuse to omit typed evidence.

Keep `POINTER_KEY` unchanged. Extend `_artifact`/receipt validation with role-fixed media type and suffix for source bodies; callers cannot choose an arbitrary content type/path. Source transport metadata must bind actual received bytes to decoded UTF-8 text and the native SourceDocument digest. Preserve exact replay semantics. Current display rights are checked later at read time as well as source admission.

```python
# Version dispatch belongs in the existing owner, not in each consumer.
if value.get('schema') == 'earnings.tier_payload/v1':
    return validate_v1_record(value, expected_slug=expected_slug)
if value.get('schema') == 'earnings.tier_payload/v2':
    return validate_v2_record(value, expected_slug=expected_slug)
raise EarningsPrivatePublicationError('unsupported private record schema')
```

`validate_v1_record` is the current validator factored without weakening it; `validate_v2_record` implements the additional closed shape. Generation hashing includes native catalogs and prior-manifest binding, but existing source clocks retain their meaning. The v2 native-source cutoff is separately represented; an unrelated story-source cutoff must not certify a newer SEC source.

The current publisher's process mutex is not a cross-process lease. Reuse existing single-writer workflow/custody fencing. A v2 publish records and checks the predecessor pointer bytes used to prepare the candidate immediately before promotion. If they differ, abort before writing the pointer and reconcile. Where the existing store has no atomic conditional-write facility, do not claim this check alone is a distributed compare-and-swap. Product release requires proven single-writer custody; no new lock service is authorized. Never apply the existing best-effort restore behavior to an uncertain v2 pointer write; return the exact unknown effect for same-carrier reconciliation.

- [ ] **4.4 Run GREEN, downgrade and idempotence tests.** Publish mixed closure, read it, rerun identical preparation and prove no new source or derived revision. Attempt v1-only promotion over installed v2 and require explicit refusal. Remove an economic slot without a retirement instruction and require refusal. Corrupt an immutable object under its existing key and require fail-closed behavior, not overwrite. Run `tests/test_earnings_private_store.py` together with the new suite.

- [ ] **4.5 Commit.** `git add engine/earnings_narrative/private_publication.py tests/test_earnings_private_store.py tests/test_earnings_economic_private_store.py tests/earnings_economic_fixtures.py && git commit -m 'feat(earnings): bind economic evidence into existing private generations'`.

## Task 5: Integrate normal refresh and protect the public path

**Files:** `engine/earnings_narrative/private_economic_stage.py`, `scripts/build_earnings_public_wire.py`, `scripts/publish_company_intelligence_r2.py`, existing `earnings-public-wire.yml`, `tests/test_earnings_economic_refresh.py`.

**Interfaces:** `augment_private_stage(stage_dir, *, acquisition, prior_closure, observed_at)` derives or reuses the selected PG native record and writes only role-bounded members of the existing off-repo staging tree. It performs no object-store writes and owns no current pointer. `assert_public_workspace_admission(workspace)` is a native policy guard invoked before public staging and in the public R2 publication validation. `prior_closure` is obtained through the Task-4 verified reader, not a checkout cache or a second last-good file.

- [ ] **5.1 Write failing normal-run tests.** Use the existing public-wire build test infrastructure with injected source acquisition and local strict store. Cover: clean v1 baseline, first private native launch, an unrelated wire update, unchanged PG source, newer-source fetch failure, malformed newly fetched source, source withdrawal, wholly unavailable prior-store read, and missing collector currentness. Snapshot all preexisting public outputs to prove unchanged bytes.

```python
def test_unrelated_wire_update_preserves_private_native_evidence(tmp_path):
    first = run_economic_wire_fixture(tmp_path, wire='w1', source='pg1')
    second = run_economic_wire_fixture(tmp_path, wire='w2', source='pg1')
    assert second.pg_source_sha == first.pg_source_sha
    assert second.pg_first_observed_at == first.pg_first_observed_at
    assert second.pg_interpretation_id == first.pg_interpretation_id
    assert second.native_closure_verified
    assert not second.public_contains_private_sentinel


def test_newer_bad_source_keeps_dated_last_good_not_false_freshness(tmp_path):
    old = run_economic_wire_fixture(tmp_path, wire='w1', source='pg1')
    new = run_economic_wire_fixture(tmp_path, wire='w2', source='pg2_bad')
    assert new.pg_source_sha == old.pg_source_sha
    assert new.currentness == 'newer_source_pending'
    assert new.pg_first_observed_at == old.pg_first_observed_at
```

`run_economic_wire_fixture` is a test driver for the real builder, stage augmenter, prepare/publish and readers against a strict local store, not a simulated result constructor. It returns measured output fields. Define it in the shared fixture module and make every transition visible in the test receipt.

- [ ] **5.2 Run RED.** `python -m pytest tests/test_earnings_economic_refresh.py -q`.

- [ ] **5.3 Wire the augmentation into the incumbent normal producer.** Call it after legacy private record/context staging and before `prepare_private_publication`. Current wire fast paths must still check whether native source/semantic/currentness inputs require change; an unchanged wire source is not proof that the PG source is unchanged. Conversely, don't rebuild unchanged native facts on every page or tick. Include new rendering/interpretation code in the existing relevant version fingerprint so code changes cannot be missed by a shortcut.

```python
# In the existing producer's private staging path, never after pointer promotion.
augment_private_stage(
    private_destination,
    acquisition=acquired_native_result,
    prior_closure=verified_prior_native_closure,
    observed_at=actual_observation_clock,
)
# The existing private publisher then validates and publishes the complete stage.
```

If collection fails but prior closure is verified, keep dated last-good evidence and make currentness pending/unverified. If prior closure itself cannot be verified, do not mint an empty root, retire records, or move the pointer. Preserve existing public-wire failure rules; this feature does not change its 48-hour outage policy into a universal economic-data freshness rule.

Public admission guard: newly admitted detailed PG workspaces/metric profiles are private under the native profile policy. Exclude them from the ordinary public registry and reject accidental public staging/upload. The guard is a second check at the publication boundary, not a caller-supplied `private=True` flag that can be stripped. Current approved public teasers and existing Apple/homebuilder workspaces remain unchanged. A real legacy public PG object, if discovered during admission, is reconciled by exact field/policy rather than erased.

Modify only the existing workflow invocation/staging arguments. Use its established credentials, runner and single-writer concurrency. Do not add a schedule, separate PG workflow, secret-export step or direct provider call. Ensure its private publication completes before public shells are staged, as the existing tests already require.

- [ ] **5.4 Run GREEN and privacy scans.** Run all new tests plus `tests/test_earnings_public_wire.py`, `tests/test_earnings_private_store.py` and the relevant existing public-company-publisher tests. Insert a distinctive synthetic private sentinel and search the entire generated public artifact tree, source maps, catalog and logs. The sentinel must not occur. Repeat with economic input disabled to prove legacy output invariance.

- [ ] **5.5 Commit.** `git add engine/earnings_narrative/private_economic_stage.py scripts/build_earnings_public_wire.py scripts/publish_company_intelligence_r2.py .github/workflows/earnings-public-wire.yml tests/test_earnings_economic_refresh.py tests/earnings_economic_fixtures.py && git commit -m 'feat(earnings): maintain economic evidence through normal private refresh'`.

## Task 6: Same-owner API and revision-pinned evidence

**Files:** `app/earnings.py`, existing/new API tests. Add routes before the broad private catch-all where route matching requires it; test the assembled app, not only an isolated router.

**Interfaces:** `load_current_economic_view(store, ticker, *, manifest)` uses the native issuer binding and `economic_slots` to return a safe projected view. `load_economic_evidence(store, *, generation_id, manifest_digest, record_digest, slug, fact_id)` resolves only the exact bound immutable record/closure. Implement both as readers in the existing private publication owner; no second repository/query service. These functions are planned additions owned by Task 4's integrator; Task 6 requests the needed signatures rather than starting a competing writer.

- [ ] **6.1 Write failing route tests.** Follow the existing `entitled_client` and denial-before-store pattern. Test anonymous 401, unentitled 403, invalid ticker/slug/generation/fact ID, valid-but-absent 404, corrupt closure 503, unsupported schema and same private headers on all paths. Test encoded slash/dot-segment/query injection and duplicate parameters. Unauthenticated requests must not disclose whether an issuer/event exists.

```python
def test_drawer_uses_displayed_generation_after_current_changes(economic_client):
    shown = economic_client.get('/api/earnings/v1/economic/PG').json()
    economic_client.publish_fixture_revision('next')
    reply = economic_client.get(
        '/api/earnings/v1/records/' + shown['slug']
        + '/economic-evidence/' + shown['interpretation']['observations'][0]['fact_id'],
        params={'generation': shown['generation_id'],
                'manifest_sha256': shown['manifest_sha256'],
                'record_sha256': shown['record_sha256']},
    )
    assert reply.status_code == 200
    assert reply.json()['source_sha256'] == shown['interpretation']['observations'][0]['source_sha256']
    assert 'object_key' not in reply.text
```

`economic_client` wraps FastAPI TestClient and the real strict local-store fixture; its `publish_fixture_revision` invokes the actual private publisher. Do not implement the test by returning hardcoded source hashes from a stubbed evidence function.

- [ ] **6.2 Run RED.** `python -m pytest tests/test_earnings_economic_api.py -q`.

- [ ] **6.3 Add the two read-only routes using existing authorization.** Authenticate and enforce site_full before constructing/reading the private store or resolving private coverage. Reuse current safe error/header helpers. Validate a pinned generation against its native immutable manifest and expected digest; do not accept arbitrary object keys, hosts or paths. Use the selected snapshot throughout the request. Existing one-time cache refresh for a missing current record remains bounded and must not rewrite an explicitly historical request.

```python
@router.get('/api/earnings/v1/economic/{ticker}')
def current_economic_view(ticker: str,
                          user: dict = Depends(require_site_full_user)):
    del user
    try:
        store = _build_store()
        manifest = _current_manifest(store)
        view = load_current_economic_view(store, ticker, manifest=manifest)
    except EarningsPrivateRecordNotFound:
        raise _private_error(404, 'earnings evidence not found') from None
    except EarningsPrivatePublicationError:
        raise _private_error(503, 'earnings evidence temporarily unavailable') from None
    return JSONResponse(view, headers=_PRIVATE_HEADERS)
```

Validate syntax separately into safe 400 responses; authorization still happens first. The new evidence route shares the same discipline. Serve only the permitted contextual span and headers/labels needed to understand it; no full-document dump. Check current retention/display permission even for old pinned generations. If rights are unavailable, return a typed unavailable or safe denial instead of a public URL fallback. The code above illustrates route wiring; validation tests define the required complete behavior.

- [ ] **6.4 Run GREEN and assembled-app tests.** Run `tests/test_earnings_api.py` and `tests/test_earnings_economic_api.py`. Check that every paid route hits auth rather than a silent 404 on import/mount failure. Test that a missing older generation does not return the current record and that stored numerical tampering fails read-time validation.

- [ ] **6.5 Commit.** `git add app/earnings.py tests/test_earnings_api.py tests/test_earnings_economic_api.py tests/earnings_economic_fixtures.py && git commit -m 'feat(earnings): serve pinned private economic evidence through existing API'`. Coordinate any private-owner reader changes on Task 4's same writer grant.

## Task 7: Shared dossier display with real evidence navigation

**Files:** the Task-7 source/partial/test paths, the accepted sector hook, and the existing template asset-copy/build registration. Do not edit STSI #7777 while another live writer holds its paths.

**Interfaces:** Proposed shared mount `mountEarningsEconomicDossier(root, {issuer, fetchAuthenticated, onAuthChange})` returns `destroy()`. `root` is the existing shared panel slot; it is not a new dashboard. The injected authenticated fetch and auth-change subscription come from the existing site session client. Confirm that client interface against the accepted shared shell before wiring; don't create another Supabase client or store bearer tokens independently.

- [ ] **7.1 Obtain the actual shared-slot binding and write browser tests RED.** Required slot properties: a bounded existing detail panel; a native issuer selector; an authenticated read callback; responsive existing styles; an evidence drawer/focus return; and lifecycle cleanup. At the inspection pin this accepted hook is not yet proven. Fable must reconcile the current shared owner and add only the narrow hook on its lawful carrier. A test-only root can exercise the component meanwhile but is not sector-path proof.

Use the real generated template in Playwright with mocked server responses for deterministic contract cases, then an authorized actual source for release proof. Proposed selectors are `data-economic-root`, `data-economic-period`, `data-economic-basis`, `data-economic-rule`, `data-economic-evidence` and `data-economic-state`; they are test/display attributes, not analytical state owners.

```python
@pytest.mark.parametrize('width', [1440, 820, 390])
@pytest.mark.parametrize('lang', ['en', 'zh'])
@pytest.mark.parametrize('theme', ['dark', 'light'])
def test_reported_and_core_remain_distinct(page, economic_site, width, lang, theme):
    economic_site.open_shared_sector(page, width=width, lang=lang, theme=theme)
    root = page.locator('[data-economic-root]')
    assert root.locator('[data-economic-period]').count() >= 1
    assert root.locator('[data-economic-basis="reported"]').count() >= 1
    assert root.locator('[data-economic-basis="core"]').count() >= 1
    root.locator('[data-economic-evidence]').first.focus()
    page.keyboard.press('Enter')
    assert page.get_by_role('dialog').is_visible()
    page.keyboard.press('Escape')
    assert root.locator('[data-economic-evidence]').first.evaluate(
        '(el) => el === document.activeElement')
```

The three widths times two languages times two themes give twelve combinations. The site fixture uses the accepted actual sector template and new partial; it cannot implement an independent substitute page. Add logout-during-fetch, late earlier-response, missing-context, known-newer-source-pending, unsupported schema, no overflow, hostile source markup, grayscale labels and company-link unresolved tests.

- [ ] **7.2 Run RED.** `python -m pytest tests/test_earnings_economic_browser.py -q`. A missing accepted mount is a named integration gate, not a reason to claim a mock passed production.

- [ ] **7.3 Implement rendering-only JavaScript and shared markup.** Fetch through the existing session client with request cache disabled. Use DOM textContent for source-derived text. Render server-provided values and rule wording; no browser arithmetic or inferred trading labels. Pin source clicks to the displayed generation/digest. Do not turn a source URL into unsanitized HTML. Bound outstanding requests with AbortController and an in-memory auth/request epoch; this is component request cleanup, not a new application identity or retry system.

```javascript
let epoch = 0;
let pending = null;
function clearPrivateView() {
  epoch += 1;
  if (pending) pending.abort();
  pending = null;
  root.replaceChildren();
}
// Each fetch captures epoch; discard its result after auth change/destroy.
```

Use existing spacing, typography and dark/light tokens. No new hero or always-expanded full-sector report. The tracker change is one compact entry to the accepted sector module; it must not add duplicate scoring or expand the main dashboard height. The US `/sectors/XLP.html` route is not a global Consumer Defensive identity. Company and GMI links are rendered only when their proper owners provide valid bindings.

Do not write private state to localStorage, IndexedDB, service workers, console output or analytics. On logout destroy the evidence drawer and invalidate in-flight results. Optional unavailable context stays understandable without swallowing the useful demand/earnings explanation.

- [ ] **7.4 Run GREEN and inspect output surfaces.** Execute all 12 viewport/language/theme combinations and keyboard/focus tests. Check network/storage/console/telemetry capture with a synthetic private sentinel. Validate the existing template/site asset parity using the repository's actual asset-copy guard. Run `node --check templates/earnings_wire/earnings-economic.js`. No visual/UI acceptance is claimed from syntax alone.

- [ ] **7.5 Commit on the accepted shared integration carrier.** Stage only the named JS/partial/template hook, parity output and tests. Commit message: `feat(themes): render private demand and earnings quality in shared dossier`. Preserve the source-owner grant and exact main/sibling base; do not cherry-pick held shared source as if it were accepted.

## Task 8: Qualify, release and prove natural continuation

**Files:** named CI registration, existing publication/liveness tests, and the incumbent Agent OS/GitHub proof records. Do not create another pipeline or watcher for this task.

**Interfaces:** Consume exact candidate/source/private-generation identities from Tasks 1-7. Produce an independently reviewed release receipt and actual browser/reader proof for the same release. Existing CI, deployment, source-admission and runtime owners remain authoritative.

- [ ] **8.1 Register all new suites in the actual owning CI command group.** Locate the existing command containing `tests/test_earnings_private_store.py` in `.github/ci/legacy-jobs.yml` and extend it with the new unit/API suites. Browser tests use the existing browser-capable owner rather than silently skipping missing Playwright. Declare dependencies through the incumbent manifest; do not add a duplicate package environment or self-hosted runner.

```bash
python -m pytest tests/test_pg_economic_observations.py \
  tests/test_pg_economic_source_selection.py \
  tests/test_earnings_economic_interpretation.py \
  tests/test_earnings_economic_private_store.py \
  tests/test_earnings_economic_refresh.py \
  tests/test_earnings_economic_api.py \
  tests/test_earnings_private_store.py tests/test_earnings_api.py -q
python -m pytest tests/test_earnings_economic_browser.py -q
node --check templates/earnings_wire/earnings-economic.js
git diff --check
```

Record all skips and why. A critical acceptance case skipped is still unproved. These commands are planned, not executed in the research turn.

- [ ] **8.2 Complete independent review and staged-order proof.** Review source selection, source-span semantics, reference closure, v1/v2 compatibility, public leak prevention, rights enforcement, auth-before-read, generation pinning, source/correction clocks and fixed semantic bounds. Require exact-head receipts. CI delay blocks merge/release, not independent allowed corrections or review. No empty push to restart checks.

Release ordering: deploy compatible v1/v2 readers and safe unavailable UI first while no new v2 data is enabled; verify existing v1 behavior. Then enable the private producer on the incumbent single-writer path, publish/verify the v2 closure, and verify the real source-to-user result. Do not deploy a v2 writer ahead of v2 readers. Withdrawing a feature does not authorize downgrading the stored pointer to v1; compatible readers can show unavailable while history stays intact.

- [ ] **8.3 Admit one real source through the actual source owner.** Record real issuer/listing/fiscal binding, actual accession/exhibit, received and decoded digests, retention/readback receipt, native workspace generation, profile revision and interpretation digest. No research fixture, made-up accession or local synthetic receipt is eligible. A known newer unparsed source must be visible as pending. If the latest release's format no longer fits the profile, repair the bounded profile under its normal grant rather than freeze the old example as current.

- [ ] **8.4 Prove the authentic visible journey.** Under an entitled account, open the accepted US Staples module through existing navigation, inspect reported versus organic growth, separate reported/core earnings, the selected period, missing optional context and a source drawer. Confirm the drawer's hash/native handles match the displayed interpretation. Navigate to the existing company workflow only through a valid owner binding. Record exact release, HTTP headers, native generation and browser evidence. Do not capture secrets or protected full payloads in public PR screenshots/artifacts.

- [ ] **8.5 Prove adverse access and next-run behavior.** Verify anonymous and unentitled refusals, safe malformed/missing/corrupt responses, no private mirrors/persistent browser state, logout cleanup, and unchanged legacy market/entry outputs. Then consume one normal subsequent run: same source must preserve native observation time, or an actual new/corrected source must produce a new correctly linked result. An unchanged run proves normal continuation, not an actual issuer correction; correction semantics are separately tested with controlled mutation. No waiting chat or fabricated daemon is required.

- [ ] **8.6 Close the task truthfully through existing owners.** If natural follow-on proof remains outstanding, label built but not fully proven and retain its actual durable owner/return path. Only real started execution with a lawful return path supports DURABLE_EXECUTION_RUNNING. A queued job or delivered packet does not. Update Agent OS and the implementation PR with the exact proof deficit and next action; do not mark the whole six-milestone Consumer Defensive program complete after CDV-1.

## 3. Complete acceptance traceability

Every item below remains NOT_EXECUTED by this research turn. Task ownership is specific; overlapping test obligations do not create additional accepted test counts.

| Spec case | Owning task | Required discriminating proof |
|---|---:|---|
| CDV1-01 | 2,8 | Real source/issuer/filing admission, not authored live facts |
| CDV1-02 | 1 | Repeated literal binds the correct table or refuses |
| CDV1-03 | 1 | Quarter selected when annual data occur first |
| CDV1-04 | 1 | Blank/dash/reported-neutral distinctions |
| CDV1-05 | 3 | Positive headline with reported-flat organic |
| CDV1-06 | 1,3 | Mixed volume does not become pure units |
| CDV1-07 | 3 | Reported rate versus rounded-input derivation |
| CDV1-08 | 3 | Nonpositive/uncertain prior denominator |
| CDV1-09 | 3,7 | Separate reported/core trends and reconciliation |
| CDV1-10 | 1,3 | Segment and company scope do not create breadth/purity |
| CDV1-11 | 1 | Unknown nested metric/extra field refused |
| CDV1-12 | 1 | Present plus absence rejected |
| CDV1-13 | 1,4,6 | Wrong body/event span refused end to end |
| CDV1-14 | 1,3 | Valid fiscal pair and duration for comparisons |
| CDV1-15 | 3,7 | Supported explanation with explicit optional absence |
| CDV1-16 | 3 | Management range not licensed consensus |
| CDV1-17 | 2,6,7 | Native issuer useful; unresolved security join visible |
| CDV1-18 | 7 | No fabricated GMI membership from display |
| CDV1-19 | 2,4,5 | Changed same-URL source creates linked revision |
| CDV1-20 | 2,5 | Unchanged source retains first observation |
| CDV1-21 | 2,5,7 | Newer failed source leaves pending currentness |
| CDV1-22 | 2,5,7 | Unavailable reference does not claim up to date |
| CDV1-23 | 4,6 | Absent historical vintage never falls back |
| CDV1-24 | 3,5 | Code-only result revision preserves source clocks |
| CDV1-25 | 4,5,8 | Public publisher rejects protected content |
| CDV1-26 | 6,8 | Auth and entitlement precede storage/coverage reads |
| CDV1-27 | 6 | Safe malformed/absent/unavailable errors and headers |
| CDV1-28 | 7,8 | Actual source drawer and company return path |
| CDV1-29 | 7 | Viewports, languages, themes, focus and accessible table |
| CDV1-30 | 7,8 | No persistent/browser/telemetry disclosure |
| CDV1-31 | 1,5,8 | Legacy native/public/market behavior invariant |
| CDV1-32 | 1,7 | Hostile markup/instructions remain inert |
| CDV1-33 | 4,8 | Closure-before-pointer; uncertain effects reconciled |
| CDV1-34 | 4,5,6 | Explicit v1/v2 dispatch and no silent downgrade |
| CDV1-35 | 3,6,8 | All decision-authority booleans false |
| CDV1-36 | 2,5,8 | Normal follow-on run and separately tested correction |

## 4. Build gates, release gates and the Fable execution boundary

The plan is not a claim that every dependency is ready. Native source/retention, the private schema roles, the shared hook and actual product-write leases must be reconciled through the existing owners. Fable is responsible for those integration judgments, not for rediscovering Consumer Defensive economics. Task-local proof/CI steps and existing release authority remain in force.

No new human approval is invented merely to repeat the commissioned plan/build sequence. A material change to the selected scope, data rights, public/private boundary or spend returns to its actual decision owner. A live/shared writer or uncertain effect must not be displaced. Where no such modifier exists, direct bounded work can proceed through lawful tools; absence of a historical session response is not an indefinite block.

This plan narrows the first vertical but does not abandon CDV-2 through CDV-6. The later work remains business exposure, channel/cash transmission, expectations/valuation, non-US coverage and learning/proactive delivery. No new alpha score or trade instruction is hidden inside this explanatory release.

A final Fable packet must carry: this plan and the accepted written design/clarifications; the twelve-family/six-milestone masterplan; exact source pins; current writer/dependency state; all 36 acceptance cases; public/private and correction rules; the latest verified effect; and a real return path. A packet's existence is not deliberate live delivery, receiver binding, ACK, START or custody transfer. This research turn has performed none of those execution actions.

## 5. Source register and verification scope

All native paths above were located through the GitHub connector. Load their exact inspection revision rather than search-index snippets before implementing. Relevant immutable code blobs recorded during planning:

| Native file | Blob at inspection pin |
|---|---|
| `engine/earnings_narrative/private_publication.py` | `0ee93909693893f419f0109f9eba1994d94e2b46` |
| `scripts/refresh_event_workspaces.py` | `7d01aacb3bec29e42de799eeed480d16f930389b` |
| `engine/company_intelligence/event_workspace.py` | `efdbd91156b2a94e6e8bdca7e8cae454a6860e68` |
| `engine/company_intelligence/documents.py` | `21ef185557d54e8b4c24c4e84c6f94bf3ea1190b` |
| `engine/earnings_release/binding.py` | `f5aa2942bac08a81df5bfa56aba9c8af32c5c3e0` |
| `scripts/build_earnings_public_wire.py` | `00490a81355544e5d55733852e38c2881e4e827c` |
| `tests/test_earnings_api.py` | `eb1959601df287381b5e384c4bf26bace1ce701b` |

External references, reviewed for semantic suitability rather than native admission:

- P&G's July 29, 2026 issuer release: https://www.pginvestor.com/news/news-details/2026/PG-Announces-Fourth-Quarter-and-Fiscal-Year-2026-Results/default.aspx . It distinguishes quarter/annual reporting, issuer-defined organic growth and reported/core earnings. Do not convert the public webpage into a SEC accession or retention receipt.
- SEC API documentation: https://www.sec.gov/search-filings/edgar-application-programming-interfaces . Aggregated facts do not replace all issuer-defined or disaggregated disclosures. Use the actual native exhibit path for the selected observations.

The plan's test code and proposed interfaces are implementation instructions, not installed code or observed application passes. Current verification is limited to document completeness, reference/type consistency, acceptance coverage and exact persistence. Product unit/API/browser tests, live-source admission, independent security review, release qualification and investment evaluation are not performed by writing this document.

**Current program disposition:** SPEC_ONLY; implementation plan prepared for the existing execution route. MISSION_COMPLETE: false. Keep #7792 Draft/HOLD as the research/evidence carrier. No product branch, native source, worker, Fable receiver, runtime Attempt, watcher, deployment or trade effect is created by this plan.
