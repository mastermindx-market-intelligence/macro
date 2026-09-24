# Healthcare Theme Intelligence Implementation Plan — R9 review candidate

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans only after the execution gates below clear. Steps use checkbox (`- [ ]`) syntax for tracking. This document itself dispatches nobody.

**Goal:** Deliver a source-qualified Healthcare explanation on the existing Theme Tracker and GLP-1 detail journey, with evidenced economic participation, counterevidence, correction handling and the next discriminating observation.

**Architecture:** Correct the incumbent FDA source/consumer, then reuse the shared Robotics/GMI curation contract with an accepted private tier backed by existing Research Vault primitives. K1 preserves native identity and clocks; F04 composes a descriptive common theme-research view through the existing authenticated Macro API and shared client. No new graph, global drug master, policy store, auth framework, scheduler or trading authority.

**Tech Stack:** The repository's admitted Python environment, pandas/pyarrow, JSON Schema, pytest, FastAPI, Jinja2 and vanilla JavaScript; existing GMI, K1 and Research Vault owners. Do not change dependency versions merely to execute this plan.

**Spec:** R7 `research/healthcare/HEALTHCARE_SOURCE_INTEGRATION_DESIGN_R7_2026-09-23.md`; R8 `research/healthcare/HEALTHCARE_SHARED_ADMISSION_REVIEW_R8_2026-09-23.md`; R9 `research/healthcare/HEALTHCARE_R9_REVIEW_DECISIONS_2026-09-23.md` (explicit proposed amendments). Robotics #7773's native contract remains the shared reference, not a license to duplicate its implementation.

**Status:** REVIEW_READY, not accepted shared architecture, not a worker commission. Source pin `d7711a0a08db8008ffe5975bfb3e6b242e4c70bd`. Research carrier #7788 remains draft/HOLD. Proposed new paths and signatures below do not exist merely because they are specified. Read them as the exact candidate contract for review.

## Global Constraints

- Preserve `glp1_obesity`, `theme:glp1_obesity`, primary basket `obesity_glp1`, `state_of_themes.html` and `basket/obesity_glp1.html`; no membership or weight changes.
- No first-release target price, underpricing claim, probability, ranking, selection, entry gate, position size, alert delivery or trade action.
- Keep source observations, derived calculations, reviewed synthesis and forward claims separate. A source announcing future activity is not observed completion.
- Products/businesses are source-scoped descriptions; only an actual owner-produced bridge supports security enrichment. Required unproved joins refuse; optional links may be omitted.
- Use the same shared `theme_graph.curation_assertion.v1` union. The proposed Healthcare additions are `REPORTED_ECONOMIC_RIGHT` and `REPORTED_SUPPLY_STATUS`; preserve the eight original Robotics predicates and five statement modes.
- Every native envelope/payload change is additive with absent/null legacy compatibility. Do not silently drop fields from persistence.
- Keep publication, business applicability, source capture, retention, review and curation clocks distinct; never infer a timezone or backdate system knowledge.
- Current detailed assertion bodies never enter public Git, `site/**`, public JSON, source maps, browser persistent storage or public mirrors. Synthetic tests and deliberate public editorial research are different objects.
- All protected responses and errors use `Cache-Control: private, no-store`, `Vary: Authorization`, `X-Content-Type-Options: nosniff`, `X-Robots-Tag: noindex, noarchive`.
- Immutable revision/correction and exact-predecessor publication remain owner-controlled. Lost modifying responses require same-carrier readback; no new operation/key or unconditional retry.
- Do not copy source bodies into K1. Do not turn a collection reader or parser into a fictitious physical reader.
- The existing GMI registry remains the rights owner. New field/purpose requirements cannot be satisfied by calling an external source “house curation.”
- Research is not acceptance. All application tests in this plan are NOT_EXECUTED at publication; each task needs actual red/green, regression and review evidence on its implementation head.
- Full twelve-family breadth, valuation/consensus, global source rights and historical evaluation remain explicit later capability obligations.

## Review Focus

1. Warm policy revocation/grant arrival must change future response eligibility without trusting a path-only cache (T04/T05).
2. A late-page failure, changed totals or page-budget cap must not publish a qualified current source sweep (T02).
3. An unbound licensor may be described but must not gain valuation, performance or portfolio enrichment (T03/T06).
4. Changed bytes at the same URL/date and withdrawal of a required input must invalidate the dependent current explanation (T03/T07).
5. New correct text cannot coexist unqualified with the old unsupported supply-glut chip on the same journey (T01/T06/T08).

## Release structure and gates

| Release | Tasks | Useful outcome | Prerequisite |
|---|---|---|---|
| D1 | T01 + T02 | Truthful incumbent supply-source view | Accepted bounded repair scope, current feed custody, source acquisition permissions |
| D2 | T03 + T04 + T05 | One real reviewed assertion reaches the existing shared page through the protected common path | Shared-owner acceptance of R9-D01, R9-D02, R9-D05 and R9-D06; native/rights/private binding |
| D3 | T06 | Complete GLP-1 economic explanation, not only an evidence widget | D2; D1 wherever the old chip is visible; admitted minimal sources |
| D4 | T07 | A real correction and non-metabolic mechanism reuse the same path; breadth is discoverable honestly | D3; second source package and correction evidence |
| Release adjudication | T08, with evidence collected in each task | Exact-head independent acceptance and real-path proof | Candidate release, actual review and production authority |

No schema-only PR is product completion. Tasks may be separate commits; D1/D2/D3/D4 are the useful delivery boundaries. T08 is acceptance support, not a fifth infrastructure release.

Before any implementation write, reconcile the actual existing shared carrier and current path custody. Known historical overlaps are #7462 on GMI store, #7669 on basket template, #7664 on Theme Tracker builder. Their old numbers are navigation, not live lease proof. Do not merge/rebase the research branch into production. Use the incumbent lawful implementation carrier or create the single necessary carrier from then-current main after gates clear. Never create a second shared writer because the other session is quiet.

## File responsibilities

| Path | Role and change type |
|---|---|
| `collectors/fda_shortages.py` | Existing collector: complete-sweep validation, versioned observations and atomic current selection in its incumbent Parquet artifact |
| `engine/fda_scarcity.py` | Existing source-status interpretation and chip; remove unsupported economic inference |
| `engine/foresight_cascade.py`, `scripts/build_foresight.py` | Existing integration only; carry truthful metadata without creating another collector schedule |
| `tests/test_foresight_cascade.py`, `tests/test_fda_shortages_generation.py` (new) | Intended status/acquisition/freshness/history cases |
| `contracts/theme_graph/curation_assertion.v1.schema.json`, `engine/theme_graph/curation_assertion.py` | Proposed shared Robotics contract; extend once, not independently in Healthcare |
| `contracts/theme_graph/evidence.v1.schema.json`, `engine/theme_graph/store.py`, `scripts/check_theme_graph_contracts.py` | Native optional payload, round-trip and validation; current legacy rows unchanged |
| `engine/theme_graph/private_evidence.py` (proposed shared backend) | Private tier of the same native evidence collection; existing Research Vault protocols, not a foreign object store/schema |
| `engine/theme_graph/rights.py`, `config/theme_sources.yml` | Effective-policy snapshot and reviewed field/purpose enforcement within incumbent owner |
| `contracts/evidence_foundation/vocabulary.v1.json`, `tests/test_evidence_foundation_contract.py` | Truthful native subtype reader/identity/clocks; preserve legacy bindings |
| `engine/market_ontology/theme_research.py`, `contracts/market_ontology/theme_research.v1.schema.json` (proposed shared) | Pure descriptive composer/common wire; no runtime internet fetch or new truth store |
| `app/theme_research.py` (proposed shared), `app/main.py` | Common entitled read route and router registration, no new API process |
| `site/assets/js/theme-research.js`, `site/assets/css/theme-research.css` (proposed shared) | Data-free client, accessible layout and request cancellation |
| `templates/state_of_themes.html.j2`, `templates/basket_detail.html.j2` | Existing shared shell/mounts, no embedded current facts or navigation replacement |
| `tests/test_theme_graph_curation_assertion.py`, `tests/test_theme_graph_private_evidence.py`, `tests/test_theme_research_api.py`, `tests/test_theme_research_ui.py` (proposed) | Shared native/transport/UI tests |
| `tests/test_healthcare_theme_research.py`, `tests/test_healthcare_theme_research_corrections.py` (proposed) | Domain scope, economic synthesis, correction and coverage |

New shared names require reconciliation with actual code at execution. An already accepted equivalent is reused and this plan's interface map is amended once; it is not kept as a parallel implementation. The implementation may not invent live object keys, review receipts, sources or identities to satisfy these tests.

## Common test conventions

All source records in code examples below are synthetic. `T0` and `T1` mean explicit UTC test datetimes parsed with `datetime.fromisoformat`; these are not upstream timezone assumptions. Monetary/rate examples use `Decimal`, never floating-point assertions about issuer-rounded inputs. Test factories live in the relevant test file or `tests/fixtures/theme_research/`; they are not production data or a canonical registry.

For one native fixture, generate `source_bytes=b"Synthetic publisher: Alpha grants Beta worldwide commercialization rights to Product Q. Alpha receives a tiered royalty on Beta's net sales; exact rates and other terms are not disclosed."`; compute its real SHA-256; retain it in the existing LocalStore temporary backend; create the actual local test receipt from those bytes. Use source-native labels Alpha/Beta and null security binding. A local accepted-review fixture is explicitly marked `fixture_only` and is rejected by live admission. Never use a plausible `co:us:PRIVATE_EXAMPLE` as proof of an actual security. Each task defines any additional helper it uses.

### Task T01: Correct supply meaning in the incumbent visible consumer

**Files:** existing `engine/fda_scarcity.py`, `engine/foresight_cascade.py`, `tests/test_foresight_cascade.py`.

**Consumes:** normalized source rows plus a qualified-capture receipt (T02 supplies live receipts; synthetic receipts are permitted for tests). **Produces proposed interfaces:** `summarize_supply(rows, *, capture, now, max_capture_age) -> dict`; existing `compute_fda_scarcity` and `format_theme_feed_chip` remain compatibility entry points over the new semantics.

The summary retains per-molecule/presentation `national_status`, `manufacturer_availability`, `observed_record_count`, unclassified/absent coverage and source clocks. `source_status` is one of `CURRENT_REPORTED`, `RESOLVED_REPORTED`, `DISCONTINUATION_REPORTED`, `MIXED_REPORTED`, `UNCLASSIFIED`, `NO_MATCHING_RECORDS`, `UNAVAILABLE`. This is a descriptive result, not a new lifecycle. It has no “glut” or investment-tone field. Freshness is separate and uses an explicit owner-reviewed `max_capture_age`; there is no hidden universal threshold.

- [ ] **Step 1: Add discriminating tests to the actual incumbent consumer.**

```python
from datetime import datetime, timedelta, timezone
from engine.fda_scarcity import summarize_supply

def test_current_available_is_not_resolution():
    now = datetime(2026, 9, 23, 12, tzinfo=timezone.utc)
    capture = {"qualified": True, "finished_at": now.isoformat(),
               "atomic_snapshot_proven": False}
    rows = [{"generic_name": "semaglutide", "status": "Current",
             "availability": "Available", "package_ndc": "TEST-A"}]
    out = summarize_supply(rows, capture=capture, now=now,
                           max_capture_age=timedelta(days=2))
    assert out["source_status"] == "CURRENT_REPORTED"
    assert out["rows"][0]["manufacturer_availability"] == "Available"
    assert "glut" not in out["label"].lower()
```

Add table-driven cases for current+resolved => MIXED_REPORTED; discontinuation-only => DISCONTINUATION_REPORTED; unknown status => UNCLASSIFIED; qualified empty => NO_MATCHING_RECORDS; unqualified/absent capture => UNAVAILABLE. A valid current+limited row remains current. Opposite-status molecules are observed, not “no records.” A stale capture does not acquire a fresh date from rendering. A recent acquisition with old or unknown source-generation metadata must not label the underlying source fresh; carry both freshness dimensions and refuse the unsupported present-tense conclusion. Assert old chip and common view share this qualified interpretation.

- [ ] **Step 2: Run red.** `python -m pytest tests/test_foresight_cascade.py -q`. Record the relevant missing-interface/assertion failure before implementation; unrelated import failures are not semantic red proof.
- [ ] **Step 3: Implement the minimal status separation.**

```python
def classify_status(raw):
    value = str(raw or "").strip().casefold()
    return {"current": "CURRENT_REPORTED", "resolved": "RESOLVED_REPORTED",
            "to be discontinued": "DISCONTINUATION_REPORTED"}.get(value, "UNCLASSIFIED")
```

Use availability only as its own field. Aggregate comparable rows into an explicit mixture rather than overwriting current with resolved. Preserve raw values and coverage. Version any changed machine-band semantics deliberately; update every existing consumer of the old band in the same useful release, rather than letting a new enum silently act as an old numeric signal.

- [ ] **Step 4: Run green and incumbent cascade regressions.** Inspect the rendered chip for synthetic mixed/stale/unknown cases. Do not run the R7 characterization expecting the corrected code to reproduce defects.
- [ ] **Step 5: Commit the bounded change with its tests.** `git add engine/fda_scarcity.py engine/foresight_cascade.py tests/test_foresight_cascade.py && git commit -m "fix(healthcare): preserve scoped supply status in existing consumer"`. No merge or release claim yet.

### Task T02: Make acquisition and forward history truthful in the same collector

**Files:** `collectors/fda_shortages.py`, `scripts/build_foresight.py`, new `tests/test_fda_shortages_generation.py`; incumbent cache stays `data/fda/shortages.parquet` and live bytes are not committed by a worker without source-owner permission.

**Proposed interfaces:** `collect_shortage_sweep(fetch_page, *, clock, page_size, max_pages) -> dict`; `save_shortage_observation(result, *, path) -> dict`; `read_shortage_observation(*, path) -> dict`. Existing `fetch_shortages`/`load_shortages_cache` wrappers return the selected qualified frame for compatible callers; consumers needing freshness use the receipt-aware function.

The result's required keys are `qualified`, `rows`, `capture`, `failure_code`. Capture preserves `started_at`, `finished_at`, `source_generation`, `raw_count`, `unique_count`, `reported_total`, `completeness`, `atomic_snapshot_proven`. A synthetic complete response with total zero is different from a failed request. Unknown or inconsistent metadata cannot establish a complete sweep.

- [ ] **Step 1: Write late-page-failure and history tests.**

```python
from datetime import datetime, timezone
from collectors.fda_shortages import collect_shortage_sweep

def test_late_page_failure_refuses_promotion():
    def fetch_page(skip, limit):
        if skip:
            raise OSError("synthetic second page failure")
        return {"meta": {"last_updated": "2026-09-23",
                         "results": {"total": 2}},
                "results": [{"package_ndc": "TEST-A", "generic_name": "semaglutide",
                             "initial_posting_date": "09/01/2026", "status": "Current"}]}
    result = collect_shortage_sweep(fetch_page,
        clock=lambda: datetime(2026, 9, 23, 12, tzinfo=timezone.utc),
        page_size=1, max_pages=2)
    assert result["qualified"] is False
    assert result["failure_code"] == "PAGE_FAILED"
```

Also cover metadata drift; duplicate/repeated pages; cap reached before total; missing key that cannot support cross-generation identity; parser failure; valid empty; complete single page; first-page network failure. Persist two synthetic complete sweeps, the second changing/removing a row: prior observation remains readable, current selection reflects only the second sweep, absence is “not observed in this sweep,” not “shortage resolved.” Load a legacy cache and assert historical capture time remains unknown.

- [ ] **Step 2: Run red.** `python -m pytest tests/test_fda_shortages_generation.py -q`.
- [ ] **Step 3: Implement bounded acquisition and atomic cache-envelope replacement.**

```python
# Core promotion predicate; validate metadata and identity before evaluating it.
qualified = (failure_code is None and reached_reported_total
             and consistent_generation and no_repeated_page and keys_unambiguous)
atomic_snapshot_proven = False  # complete pagination is not transaction isolation
```

Use the existing writer/lane and same artifact. Add observation-version columns to retain captured generations; keep the current qualified selection and last refresh receipt in bounded Parquet metadata so a complete empty source still has a receipt. Temp-file plus atomic replace preserves the prior artifact on write failure. On acquisition failure, only a successfully saved failure receipt may update the envelope; it never promotes partial source rows. Keep the previous qualified generation's original capture/source dates. A failed metadata write is reported honestly, not treated as persisted. No second scheduler or standalone history directory.

Do not infer a stable source identity from blank NDCs. Preserve a content-scoped record as such; where identity is ambiguous, refuse the cross-generation comparison. Compare counts without claiming source atomicity. Keep the incumbent page budget until the source owner explicitly changes it.

- [ ] **Step 4: Run both T01 and T02 suites; exercise the actual collector-to-chip build with an allowed real complete sweep.** Record acquisition interval, counts, metadata, normalized-source fingerprint, consumer output and limitations. This is source proof, not clinical advice or historical investment validation.
- [ ] **Step 5: Commit and obtain D1 exact-head review before its authorized release.** Use `git add collectors/fda_shortages.py scripts/build_foresight.py tests/test_fda_shortages_generation.py && git commit -m "fix(healthcare): qualify source sweeps and retain forward observations"`.

### Task T03: Enroll the Healthcare meanings in the shared native assertion contract

**Files:** shared proposed `contracts/theme_graph/curation_assertion.v1.schema.json`, `engine/theme_graph/curation_assertion.py`; existing evidence schema/columns/guard; `tests/test_theme_graph_curation_assertion.py`.

**Gate:** shared owner accepts R9-D01, R9-D04 and R9-D05 and reconciles the actual Robotics implementation. This task extends that one contract. **Interfaces:** `validate_assertion(payload) -> dict`, `curation_revision(payload) -> str`, `encode_assertion(payload) -> str`, `decode_assertion(value) -> dict | None`, `source_ref_for(payload) -> str`. These reuse the proposed Robotics names and revision grammar `gmirca_[0-9a-f]{32}`.

Freeze two discriminated payload keys in the shared union: `economic_right` and `supply_status`; each is present only for its corresponding predicate. Existing predicates carry neither. `economic_right` contains the ten semantic groups in R8 section 6, using qualitative terms plus null numerical rate when exact terms are not disclosed. `supply_status` contains source record identity strength, product/presentation/jurisdiction, separate status/availability, generation/capture, completeness and explicit unknowns. Neither branch mints a global product or company identity.

- [ ] **Step 1: Add full round-trip and identity tests.**

```python
import copy
from engine.theme_graph.curation_assertion import encode_assertion, decode_assertion, curation_revision

def test_same_url_new_source_bytes_is_new_revision(native_fixture):
    first = native_fixture  # complete synthetic fixture with retained-byte receipt
    second = copy.deepcopy(first)
    second["source"]["native_digest"] = "b" * 64  # schema-only negative/identity test, never live admission
    assert curation_revision(first) != curation_revision(second)
    assert decode_assertion(encode_assertion(first)) == first
```

The fixture is constructed from the Common test convention plus every required shared-envelope field: source, review, subject, object, predicate, statement_mode, scope, observation, temporal, limitations, correction, authority. Negative live-admission tests reject the changed digest unless actual retained bytes match it. Test two locators in one source; duplicate identical input; omitted/null legacy payload; qualitative rate cannot produce a midpoint; net-sales royalty cannot become profit share; no inferred supply/exclusivity; contingent milestone stays contingent; amended disclosure versus amended agreement; boolean/NaN numerical input rejection; undated/unknown timezone stays typed unknown.

- [ ] **Step 2: Run red.** `python -m pytest tests/test_theme_graph_curation_assertion.py -q`.
- [ ] **Step 3: Add the union branches and canonical revision construction.**

```python
import hashlib, json

def revision_material(payload):
    material = {k: v for k, v in payload.items()
                if k not in {"curation_revision", "transport_receipt", "request_id"}}
    return json.dumps(material, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode("utf-8")

def revision_from_material(body):
    return "gmirca_" + hashlib.sha256(b"gmi-curation-v1\0" + body).hexdigest()[:32]
```

Canonical bytes include review/admission identity and meaning; no payload may claim live review acceptance solely by carrying `accepted=true`. Persist payload through the native private tier in T04; never write live detailed rows into public evidence Parquet during T03. Full 64-character content hashes still verify storage even though the existing planned revision display uses 32 hex characters.

- [ ] **Step 4: Prove encode/decode and legacy-row round-trip, guard integration, declared clock grain and semantic errors.** Rows with conflicting source identity, unsupported predicates or forbidden extra fields refuse.
- [ ] **Step 5: Commit only the shared accepted paths and tests on the single shared carrier.** `git add contracts/theme_graph/curation_assertion.v1.schema.json engine/theme_graph/curation_assertion.py contracts/theme_graph/evidence.v1.schema.json engine/theme_graph/store.py scripts/check_theme_graph_contracts.py tests/test_theme_graph_curation_assertion.py && git commit -m "feat(gmi): extend shared curation meanings for healthcare"`.

### Task T04: Bind the same native evidence to private storage and effective policy

**Files:** proposed shared `engine/theme_graph/private_evidence.py`; existing `engine/theme_graph/store.py`, `engine/theme_graph/rights.py`, reviewed `config/theme_sources.yml`; new `tests/test_theme_graph_private_evidence.py`. Reuse `engine/research_vault/r2_store.py`; change that shared primitive only when a focused failing test proves a missing capability and its owner approves.

**Gate:** R9-D01, R9-D02 and R9-D05 accepted by the shared owner; namespace, writer/lane and audience restrictions explicitly bound. No live cloud writes until that gate clears. **Proposed interfaces:**

| Interface | Meaning |
|---|---|
| `read_policy_snapshot() -> PolicySnapshot` | Reads bounded deployed canonical bytes; returns parsed immutable policy and SHA-256 revision, never caller-selected authority |
| `assert_assertion_use_allowed(policy, assertion, *, purpose) -> None` | Same rights owner; checks every required upstream source/field/use; unknown refuses |
| `prepare_generation(rows, *, binding, reviews, sources, policy) -> PreparedGeneration` | Revalidates exact native assertion/source/review identities; creates only an off-repo staged candidate |
| `publish_generation(binding, prepared, *, expected_version) -> dict` | Uses existing strict store, verifies immutable objects and CAS-promotes the sole private-tier selection |
| `load_generation(binding, *, generation_id=None) -> BoundGeneration` | Opens current or exact retained native generation, bounds/validates all bytes, never silently falls back |
| `read_curation_evidence(binding, *, generation_id) -> list[dict]` | Actual native physical accessor for the private subtype, suitable for truthful K1 enrollment |
| `read_evidence_for_consumer(*, private_generation) -> list[dict]` | Opt-in GMI collection view, legacy plus verified private rows; duplicate native IDs across tiers refuse |

`PolicySnapshot` has `revision`, `policy`, `loaded_at`; `BoundGeneration` has `generation_id`, `native_rows`, `manifest_digest`, `policy_at_admission`, `source_receipts`. Binding fields are `store`, `namespace`, `writer_grant`, `mode`, `approval_ref`. A live binding requires actual owner approval; `mode=fixture_only` cannot publish into a production store. Typed structures are implementation contracts to add under GMI, not a new runtime grant framework.

Proposed hard bounds: 128 KiB per native assertion, 16 KiB per selector, 4 MiB per manifest, 2,048 native rows per private generation, and 512 KiB / 50 evidence blocks per response. These are reviewable engineering limits, not measured source maxima. Enforce before allocating/serializing; excess required evidence produces an explicit unavailable result, never silent truncation. Do not trust a manifest-provided maximum to enlarge the code bound.

The private-tier current selector is a proposed addition to the existing GMI owner, not an already-proven feature. It is the sole selector for this subtype, not another per-theme state plane. Metadata selectors contain IDs/digests, not authoritative duplicate bodies. Legacy collection selection is unchanged.

- [ ] **Step 1: Write warm-policy, storage and predecessor tests.**

```python
# Functions below are the proposed GMI interfaces, exercised through the local binding.
from engine.theme_graph.private_evidence import publish_generation, load_generation

def test_exact_predecessor_conflict_cannot_replace_current(local_binding, prepared_a, prepared_b):
    first = publish_generation(local_binding, prepared_a, expected_version=None)
    result = publish_generation(local_binding, prepared_b, expected_version=None)
    assert result["state"] == "CONFLICT"
    assert load_generation(local_binding).generation_id == first["generation_id"]
```

Build `local_binding` with the existing temporary LocalStore and explicit fixture-only approval. `prepared_a/b` come from `prepare_generation` over the synthetic fixture in Appendix A and byte-matched local receipts. Test source/object length mismatch, corrupt manifest, oversized stream, unknown rights, cross-tier duplicate ID, source digest mismatch, object identity collision, incomplete staging and lost CAS response. Simulate the latter by committing then throwing; reconcile the exact selector/readback and return the established effect without a second pointer write. A second reader failure leaves EFFECT_UNKNOWN, not absence.

Warm-policy test: read allowed bytes, atomically replace the same deployed test path with denied bytes, invoke the next request, and assert denial before any private body read. Reverse the transition to prove grant arrival. If policy changes during body assembly, the pre-serialization revision check must abort. Do not clear caches manually in the acceptance test to make it pass.

- [ ] **Step 2: Run red.** `python -m pytest tests/test_theme_graph_private_evidence.py -q`.
- [ ] **Step 3: Implement the private backend and policy snapshot under their existing owners.**

```python
# Called only after immutable objects and review/source receipts have verified.
def promote_verified_selector(binding, selector_key, selector_bytes, expected_version):
    previous = binding.store.get_bytes_strict_bounded_versioned(selector_key, 16 * 1024)
    if previous.version != expected_version:
        return {"state": "CONFLICT"}
    applied = binding.store.put_bytes_strict_conditional(
        selector_key, selector_bytes, expected_version=expected_version,
        content_type="application/json")
    return {"state": "APPLIED" if applied else "CONFLICT"}
```

Use the actual `StrictConditionalWriteStore` protocol. Do not fall back to permissive `get_bytes` on strict-read failure. Immutable write collision is accepted only when exact bytes match. `False` is a predecessor conflict; operational failures require readback reconciliation. Source retention limits govern historical body availability; audit metadata is not permission to retain forbidden bodies forever.

Read policy from a bounded open of canonical deployed bytes, compute SHA-256, validate before private access, and cache only bounded parsed content by digest. The request rechecks policy digest before emitting. A denied required input removes the dependent synthesis, not only its citation. Private GMI payloads never enter repository-backed legacy evidence.

- [ ] **Step 4: Run native-store, policy and legacy contract suites; verify same-row encode/decode through the real LocalStore backend.** No cloud proof follows from local success. Confirm import alone opens no credentials/cloud connection.
- [ ] **Step 5: Commit the shared-owner change and tests.** `git add engine/theme_graph/private_evidence.py engine/theme_graph/store.py engine/theme_graph/rights.py config/theme_sources.yml tests/test_theme_graph_private_evidence.py && git commit -m "feat(gmi): bind private curation to native evidence and current policy"`.

### Task T05: Complete one common protected evidence-to-page path

**Files:** proposed common `engine/market_ontology/theme_research.py`, `contracts/market_ontology/theme_research.v1.schema.json`, `app/theme_research.py`; existing `app/main.py`, K1 vocabulary/tests; shared JS/CSS and existing page mounts; new shared API/UI tests.

**Consumes:** bound private native generation, policy snapshot, reviewed profile, exact native identity rows. **Produces:** `compose_theme_research(*, theme_id, generation, policy, identity_rows, profile, now) -> dict`; `GET /api/themes/{theme_id}/research/v1`; shared mount `data-theme-research` whose value is the canonical theme ID. The composer performs no network, writes, implicit product identity or model inference.

Required wire fields: `schema`, `theme_id`, `primary_basket_id`, `generation_id`, `method_version`, `policy_revision`, `evidence_blocks`, `synthesis`, `coverage`, `degradations`, `authority`. Native storage credentials/object keys never reach the wire. Browser-visible source citations use approved source locators, not private storage URLs. All authority flags are literal false.

- [ ] **Step 1: Write entitlement-before-read, lossless-clock and legacy-interface tests.**

```python
from fastapi.testclient import TestClient

def test_unauthorized_request_never_opens_private_body(mounted_app, read_spy):
    response = TestClient(mounted_app).get("/api/themes/glp1_obesity/research/v1")
    assert response.status_code == 401
    assert read_spy.calls == 0
    assert response.headers["cache-control"] == "private, no-store"
    assert response.headers["vary"] == "Authorization"
```

`mounted_app` mounts the actual proposed router with the existing `require_user -> enforce_site_full(always=True)` dependency; `read_spy` replaces only the private reader boundary, not authentication. Separate tests exercise an actual accepted test token via the repository's existing auth fixtures, 403/404/503, malformed/encoded paths, invalid theme allowlist, unknown profile, integrity error and safe storage error. Test every richer native clock survives K1; legacy success cannot qualify a richer subtype missing clocks. Required unproved security joins refuse; the native-evidence-subject read is not advertised as security composition.

- [ ] **Step 2: Run red.** `python -m pytest tests/test_theme_research_api.py tests/test_evidence_foundation_contract.py tests/test_theme_research_ui.py -q`.
- [ ] **Step 3: Implement the smallest complete shared journey.** Enroll a truthful private accessor and subtype in the K1 vocabulary; do not change legacy clock bindings. Authenticate before store access, bind one generation/policy, compose, recheck policy revision, return private headers on success/error. Invalid required data refuses; optional data gives typed degradation. A parser or declaration is not physical read proof.

The client uses the existing site's auth client, not a new token store. Verify its current `MDXAuth.client()` contract in `templates/theme.js` at implementation; do not invent a helper API. Register one listener using that existing client's documented session-change callback. Keep an incrementing request sequence plus AbortController; clearing or changing session increments sequence before DOM clear. Render only when the response sequence still equals current sequence and the same session is eligible. No protected data in localStorage, IndexedDB, service workers or asset files.

```javascript
let requestSequence = 0;
let controller = null;
function invalidatePrivateView(clearView) {
  requestSequence += 1;
  if (controller) controller.abort();
  controller = null;
  clearView();
}
function responseStillCurrent(sequence) { return sequence === requestSequence; }
```

Use textContent for source text; do not inject source HTML. Reuse global navigation and design tokens. Provide locked, integrity-unavailable, stale, partial, empty and normal states with an accessible table; no new global banner/header. First prove the shared path on one admitted source assertion, whether Robotics or Healthcare as accepted by the shared owner.

- [ ] **Step 4: Prove local API/UI parity, then one permitted real native source through the actual entitled browser.** Include dark/light, EN/ZH, desktop 1440/mobile 390; test logout/in-flight response, direct route, back navigation and public/static mirrors. Negative public proof covers exact alternate paths, not a global unsupported “nothing leaked” claim.
- [ ] **Step 5: Commit the common path once and complete D2 review.** Include the source/clock/policy binding receipt and exact consumer proof; a blank widget or schema pass is not D2 complete. Keep pending shared or production gates explicit.

### Task T06: Enroll the complete Healthcare explanation, not just the evidence drawer

**Files:** the accepted common composer/wire/client/profile; `tests/test_healthcare_theme_research.py`; existing GLP-1 mount. Healthcare profile lives within the common composer or its accepted profile configuration, not a new server or page.

**Consumes:** minimal admitted R7 evidence package plus selected R2/R3 counterevidence, each refreshed for its intended use; actual native assertion IDs; policy; optional verified security bridges. **Produces:** five ordered sections `change`, `mechanism`, `participants`, `counterevidence`, `next_observation`, each with supporting native assertion IDs and conclusion limits. Reviewed synthesis is bounded content tied to exact dependencies; it is not generated ad hoc in a browser.

- [ ] **Step 1: Write the user-job and unsafe-inference tests.**

```python
from engine.market_ontology.theme_research import compose_theme_research

def test_unbound_licensor_has_no_invented_stock_enrichment(healthcare_inputs):
    out = compose_theme_research(**healthcare_inputs)
    participant = next(p for p in out["synthesis"]["participants"]
                       if p["source_label"] == "Alpha")
    assert participant["security_id"] is None
    assert participant["stock_url"] is None
    assert participant["valuation"] is None
    assert participant["economic_basis"] == "royalty_on_net_sales"
```

`healthcare_inputs` uses the actual common composer signature, synthetic Alpha/Beta assertions from Appendix A, and empty actual bridge rows. Add cases for net-sales versus profits, qualitative versus exact rates, conditional payment, worldwide versus one-jurisdiction scope, group versus drug pricing, and no manufacturing inference. Missing consensus leaves economic explanation available but `underpricing`, `target_price`, `expected_return` unavailable. Two repeated issuer disclosures count as two source references without automatic independence. Source permissions do not grant clinical or trade authority.

- [ ] **Step 2: Run red.** `python -m pytest tests/test_healthcare_theme_research.py -q`.
- [ ] **Step 3: Implement bounded profile selection and deterministic eligibility.**

```python
# The review supplies these dependencies; a model does not infer authority.
missing_required = required_assertion_ids - eligible_assertion_ids
show_current_synthesis = not missing_required
# When false, render eligible independent facts plus an explicit missing reason;
# never reuse the old paragraph with its citations silently removed.
```

The initial real narrative explains how treatment activity, net realization, cost, retained rights and capacity relief may diverge. Reuse R7's source-specific Lilly/Chugai case, but refresh actual sources/rights before admission; do not assume old filenames prove current figures. A valid source-only business can be useful without pretending to be a tradable security. Price/leadership panels remain untouched owner outputs, not inputs to an unvalidated causal conclusion.

- [ ] **Step 4: Run domain/shared regressions and real browser exercise.** Ask a reviewer who did not write the text to identify the observed change, mechanism, participant, counterargument and next observation without prompting an answer. Record misunderstandings; no synthetic user-success claim. The old FDA output in this journey must be corrected or explicitly superseded under accepted owner law. Existing basket members, weights, ranks and entry decisions must match baseline.
- [ ] **Step 5: Commit only Healthcare profile/tests and the minimal shared enrollment.** Complete D3 with source-to-visible-result evidence and held predictive claims; do not copy the common client into a Healthcare-specific fork.

### Task T07: Demonstrate a correction and a distinct non-metabolic mechanism

**Files:** same common owner/profile; `tests/test_healthcare_theme_research_corrections.py`; existing acceptance evidence location. No new storage/registry.

**Proposed interface:** `reconcile_research_dependencies(*, current_assertions, prior_synthesis) -> dict`, pure logic under the common composer. It returns exact invalidating refs, whether the current conclusion is eligible, and needed re-review. New approved synthesis receives a new content identity. It does not silently rewrite the predecessor.

- [ ] **Step 1: Write required-source withdrawal and changed-disclosure tests.**

```python
from engine.market_ontology.theme_research import reconcile_research_dependencies

def test_withdrawn_required_source_suppresses_current_conclusion():
    result = reconcile_research_dependencies(
        current_assertions={"ev:0000000000000001": {"state": "withdrawn"}},
        prior_synthesis={"required_assertion_ids": ["ev:0000000000000001"],
                         "revision": "fixture-synthesis-1"})
    assert result["current_conclusion_eligible"] is False
    assert result["invalidating_refs"] == ["ev:0000000000000001"]
```

The ID is an explicitly synthetic native-ID-shaped fixture, never an actual source resolution. Test a factual correction separately from a revised interpretation and an actual contract amendment. History cannot bypass revoked rights. A newly observed source date cannot manufacture old system knowledge.

- [ ] **Step 2: Run red.** `python -m pytest tests/test_healthcare_theme_research_corrections.py -q`.
- [ ] **Step 3: Implement dependency reconciliation and second profile example through the same wire.** Select the already-researched provider/procedure case whose scope and data qualify; the proposed first contrast is procedure/case-mix economics from R4/R5, not a second drug licensor. Keep total versus same-facility measures and noncontrolling interests separate. If that source is not admitted, leave the example unavailable rather than invent one.

Render all twelve research families with `selective`, `not_yet_productized` or another accepted coverage label. Families are research navigation, not new canonical theme IDs. A family with one worked case cannot display “complete.” Do not add illustrative companies to a price basket.

- [ ] **Step 4: Run correction/coverage suites, then an admitted real updated source to the visible page.** A controlled synthetic withdrawal tests failure behavior; it does not substitute for the real revised-input proof. Where no real correction exists, preserve that acceptance as pending and prove an actual new observation without mislabeling it as a correction.
- [ ] **Step 5: Commit D4 and record exactly which source-change and adverse cases were actually exercised.** The broader sector roadmap remains incomplete; no universal Healthcare acceptance claim.

### Task T08: Independent release adjudication and final Fable execution return

**Files:** existing Agent OS checkpoint and the actual implementation PR/evidence paths; no new acceptance service. **Consumes:** exact candidate source, actual test output, source/admission/binding receipts, user-path evidence and independent review. **Produces:** an owner-accepted release disposition or precise held gate; not a generated PASS from this plan.

- [ ] **Step 1: Freeze candidate and evidence denominator.** Include all 41 R8 cases, seven new R9 acceptance specifications and six R9 review decisions and the complete browser cell matrix. Per-case outcomes are PASS/FAIL/BLOCKED only with exact observed evidence; untouched cases remain NOT_EXECUTED. Record scope of each result, source generation, policy revision and implementation commit.
- [ ] **Step 2: Run the declared test commands on the exact candidate.** A useful minimum is:

```bash
python -m pytest tests/test_foresight_cascade.py tests/test_fda_shortages_generation.py tests/test_theme_graph_curation_assertion.py tests/test_theme_graph_private_evidence.py tests/test_evidence_foundation_contract.py tests/test_theme_research_api.py tests/test_theme_research_ui.py tests/test_healthcare_theme_research.py tests/test_healthcare_theme_research_corrections.py -q
```

Use actual accepted test filenames if the shared owner reconciled them; record the map. Missing test files are not skips that produce acceptance. Include the relevant unchanged recommendation/entry regression suite supplied by its owner. Hosted CI, local tests, merge and browser acceptance are separate facts.

- [ ] **Step 3: Obtain independent semantic/security and implementation review.** Reviewer examines scope, source meaning, clocks, privacy, current policy, no guessed identity, preserved owner authority and five-part user job. Fable's implementation orchestration is not a substitute for independent review of its own work. Retain routine tasks with the least-scarce capable admitted workers; no foundational sector research fan-out.
- [ ] **Step 4: Execute only the authorized release and prove the actual deployed path.** Demonstrate allowed source -> native admission -> private generation -> entitled API -> existing-page result. Verify anonymous/expired/403/error behavior, no public body in checked mirrors, and logout race. No production credential ceremony is performed by this research plan.
- [ ] **Step 5: Update existing durable owners.** Report exact release, accepted scope, still-missing coverage/valuation/history, effect uncertainty and next action. Do not mark the full Healthcare mission complete when only D1–D4 are accepted. No automatic worker wake follows from a final chat response.

## Appendix A — concrete synthetic native fixture for plan tests

The text of the synthetic source supports the fixture's qualitative royalty and territory assertions; fixture dates and review are explicitly invented test metadata, not historical evidence.

The shared owner may change the proposed wire only by an explicit reviewed amendment; update all tasks and mappings together. This fixture is a schema/test construction, not a model of actual Lilly/Chugai terms. The native source and review objects are locally generated fixture receipts; production rejects their fixture-only admission mode.

```python
import hashlib
import pytest

@pytest.fixture
def native_fixture():
    source_bytes = b"Synthetic publisher: Alpha grants Beta worldwide commercialization rights to Product Q. Alpha receives a tiered royalty on Beta's net sales; exact rates and other terms are not disclosed."
    return {
        "schema": "theme_graph.curation_assertion.v1",
        "curation_revision": None,
        "source": {"publisher": "Synthetic publisher", "source_uri": "urn:test:source:q",
                   "locator": "sentence-1", "native_digest": hashlib.sha256(source_bytes).hexdigest(),
                   "published_at": "2026-09-22", "published_at_grain": "date",
                   "observed_at": "2026-09-23T10:00:00Z", "retained_at": "2026-09-23T10:01:00Z",
                   "retention_ref": "urn:test:retention:q"},
        "review": {"disposition": "accepted", "reviewer": "fixture-reviewer",
                   "reviewed_at": "2026-09-23T11:00:00Z", "review_due_at": None},
        "subject": {"company_node_id": None, "source_business_label": "Alpha",
                    "source_product_label": "Product Q", "source_platform_label": None,
                    "configuration": None},
        "object": {"source_product_label": "Product Q", "configuration": None},
        "predicate": "REPORTED_ECONOMIC_RIGHT", "statement_mode": "REPORTED_FACT",
        "scope": {"canonical_theme_id": "glp1_obesity", "application": "metabolic",
                  "technology_facet": None, "region": "source-defined worldwide",
                  "period": None, "denominator": "net_sales"},
        "observation": {"value": None, "value_high": None, "unit": "royalty_rate",
                        "quantity_basis": None, "gross_net_basis": "net_sales",
                        "stock_flow": None, "estimate_status": "not_disclosed",
                        "precision": "qualitative"},
        "temporal": {"business_valid_from": None, "business_valid_to": None},
        "economic_right": {
            "parties": [{"source_label": "Alpha", "roles": ["grantor", "payee"]},
                        {"source_label": "Beta", "roles": ["grantee", "payer"]}],
            "asset_scope": {"source_label": "Product Q", "formulation": None},
            "grant_scope": {"activities": ["commercialization"], "territory": "worldwide",
                            "exclusivity": None},
            "economic_basis": "royalty_on_net_sales",
            "rate_terms": {"numeric_value": None, "qualitative": "tiered, exact rate undisclosed",
                           "null_reason": "Exact tiers not disclosed in the synthetic source."},
            "trigger_terms": {"value": None, "reason": "Not disclosed."},
            "cost_obligations": {"value": None, "reason": "Not disclosed."},
            "recognition_scope": {"value": None, "reason": "Contractual right, not reported earnings."},
            "applicability": {"value": None, "reason": "Original effective date not disclosed."},
            "limitations": ["No precise rate, issuer materiality or manufacturing right."]},
        "limitations": {"establishes": ["a disclosed source-scoped royalty relationship"],
                        "does_not_establish": ["a real company, retained margin, or security binding"],
                        "coverage": "synthetic sentence", "source_dependence": "single_source",
                        "expiry_trigger": "source correction or review change"},
        "correction": {"predecessor_revision": None, "reason": None},
        "authority": {"can_rank": False, "can_gate": False, "can_size": False,
                      "can_originate": False, "can_open_entry": False}}
```

A schema unit test can use this candidate with `curation_revision=None`; `curation_revision()` derives its identifier without mutating it. Admission adds/verifies the actual revision, retained-source receipt and review object. Test encode/decode at a consistent candidate or admitted stage; do not compare an enriched admitted record to an unenriched candidate and call the difference a store defect.

## Appendix B — full-sector and intelligence roadmap retained

After the first shared workflow is accepted, deepen coherent families rather than adding isolated company tags. The twelve-family source map is carried in the R9 traceability packet from R8, unchanged in meaning.

Stage E1: advanced therapeutics and diagnostics; preserve trial population/analysis version, authorization/access and asset rights. Stage E2: tools/CDMO, devices and procedures; test qualified involvement, utilization, recurring use, cash and provider economics. Stage E3: payers, providers, distribution, software and animal health; retain contract risk, cohort/period, geographic/species distinctions. Stages are research-product expansion sequencing, not runtime states or fixed schedules.

Stage V1: current issuer/security and contemporaneous price/consensus data, lawful historical retention and financing/share-count bridge. Until acquired, no underpricing or forecast-return output. Stage V2: prospective, time-stamped thesis and falsifier records through the existing owner, followed by preregistered evaluation that includes failures, delistings, revised facts, missingness and realistic decision timing. Neither stage silently grants Prophet or trading authority.

The moat is the maintained chain from scientific/operating developments to retained company economics and changing expectations, together with corrections and counterevidence. Citation coverage supports that capability; source count is not its success measure.

## Review and execution boundary

R9 is ready for exact-package review, not independent-approved and not dispatched. Shared reviewer decides the private-tier/policy/common-route amendment; independent Healthcare reviewer checks semantics and all acceptance mappings; the design decision owner then accepts or revises this plan. Fable remains the intended later orchestrator. No additional generic research request is necessary to understand these tasks, but actual source admission, runtime custody and release proof remain real future gates.
