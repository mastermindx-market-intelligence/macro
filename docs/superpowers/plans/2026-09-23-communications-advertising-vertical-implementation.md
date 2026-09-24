# Communications Advertising Economics — First Vertical Implementation Plan

> **For agentic workers:** Use the installed `superpowers:subagent-driven-development` or `superpowers:executing-plans` workflow for the admitted task. The Chairman selected Fable as final principal integrator; this document does not dispatch a worker or choose a provider account.

**Goal:** An entitled investor can open the existing Theme Tracker research entry, compare Meta, Alphabet, The Trade Desk and Magnite at the correct business/financial scope, understand reported changes and dated company-guidance delivery, inspect limitations, and finish in the existing company/watchlist workflow.

**Architecture:** Consume one shared GMI curation-assertion extension and its native evidence storage, with a narrow signed-measure/measurement-context amendment. Keep K1 native-evidence blocks separate, compose a deterministic F04 view, and use the existing Macro entitlement and shared-page presentation paths. No duplicate source, metric, identity, graph, refresh, publication, outcome or trading authority.

**Tech stack:** Existing Python, pandas/parquet, JSON Schema, pytest, FastAPI, Jinja2 and vanilla browser JavaScript/CSS. Use repository-supported installed versions; this plan requests no package upgrade.

**Spec:** `docs/superpowers/specs/2026-09-23-communications-business-intelligence-design.md`, revision 1, commit `d65263dc15a8dc3ddded35b1529c535c881175bd`, blob `2cf3918e95715cd924a5a5f402201e4053e2a036`.

**Status:** Proposed implementation plan and required proof, not executed work, accepted shared-contract amendment or source admission. The written design and shared-owner review remain outstanding. Research PR #7794 stays Draft/HOLD. Product code starts only on an admitted current-main implementation carrier after incumbent effect/custody reconciliation, never by silently turning this older research branch into the application branch.

## Global constraints

- Preserve the fixed four-issuer denominator even when a company or required source is missing. A partial comparison is not acceptance of the full first vertical.
- Current economic base, incremental sensitivity and conditional future opportunity remain different dimensions. No theme weight or stock-ranking score is populated.
- The shared dependency is Robotics #7773's `theme_graph.curation_assertion.v1` path, not a competing Communications schema/store. If an accepted successor already exists, consume it and implement only the missing semantic delta.
- Physical negative quantities remain rejected. Signed financial measures are admitted only where the reviewed definition and recipe both allow them.
- Guidance is an observed source statement about a future period, not an achieved operating fact or a new forecast owner. Original company guidance is not analyst consensus.
- Source publication, financial period, observation, retention, curation/review and correction clocks remain distinct. A date-only clock cannot establish an intraday surprise cutoff.
- Actual private retention/publication binding must be proven before real detailed evidence admission. Do not choose another data root, bucket or public seed to bypass this gate.
- Use the existing identity bridge. No ticker equality, CIK guess, label match or research-row identifier substitutes for a native issuer/security/listing receipt.
- K1 remains pointer-only and does not acquire a cross-type identity bridge. Independent native-subject blocks may be presented together, not claimed to be one accepted security-subject recipe.
- Proposed API is `GET /api/themes/communications/research/v1`; unknown query fields are rejected. No source URL/path, arbitrary ticker, formula, prompt, cutoff or portfolio input is accepted.
- Auth and `enforce_site_full(..., always=True)` precede private reads. All response paths preserve private/no-store, noindex/noarchive, nosniff and appropriate Vary headers.
- Limits: four issuer panels, 96 observed assertions, 32 derived results, 16 source descriptors, 240 characters per short narrative field, 256 KiB encoded response. These are design bounds, not measured service levels.
- No live LLM is required for calculations or serving. Deterministic templates and reviewed interpretation are the first implementation.
- The closed Theme Tracker adds only a compact research entry outside scored canonical-theme cards. No nineteenth theme, new large hero, board re-ranking or new navigation family.
- Dark/light are deliberate canonical art directions; EN/ZH, 1440-pixel desktop and 390-pixel mobile all require proof. Source text is escaped. Private responses do not enter static HTML, public JSON, source maps or browser persistent storage.
- Existing company page owns the watchlist write. This API is read-only and receives no user holdings or watchlist mutation.
- CI, merge, deployed source, live source admission, browser proof and acceptance are separate. No step below is marked executed.

## Review focus

1. A legitimate negative cash result must survive, without allowing a negative physical count or an arbitrary producer-selected numeric domain. Tasks 1 and 3.
2. A paid response arriving after logout must not repaint private content; a restored browser page must revalidate. Task 6.
3. One missing issuer must remain in coverage and cannot quietly make a three-company result look complete. Task 4.
4. A source revision at the same URL/date must change the affected comparison while preserving historical evidence and untouched panels. Tasks 1, 2 and 4.
5. GAAP cash, an issuer-defined cash subtotal and a lower-bound expectation must not become a generic peer ranking. Tasks 3 and 4.

## File and custody map

All new paths below are proposed, not files observed at the source pin. Existing source was read at Macro `da092e5d4a64dbb7c3958826f8cd60d7cbd02cc5`. The exact source blobs are in spec section 2. The native writer signatures were additionally read through `store.py` lines 245–410 at the same blob. The browser-auth example was read in `site/market_memory.js` lines 1–100, blob `2552e862c9b2e3ae6ccfa76725b763851d4e6b66`.

| Unit | Paths and responsibility |
|---|---|
| Shared assertion | Consume or extend proposed `contracts/theme_graph/curation_assertion.v1.schema.json`, `engine/theme_graph/curation_assertion.py`, `tests/test_theme_graph_curation_assertion.py`; one owner/custody, not a second implementation |
| Native persistence/binding | Existing `contracts/theme_graph/evidence.v1.schema.json`, `engine/theme_graph/store.py`, `scripts/check_theme_graph_contracts.py`, `contracts/evidence_foundation/vocabulary.v1.json`, `tests/test_evidence_foundation_contract.py` |
| Comparison/F04 | Proposed `engine/market_ontology/communications_measures.py`, `engine/market_ontology/communications_research.py`, `contracts/market_ontology/communications_business_research.v1.schema.json`, `tests/test_communications_measures.py`, `tests/test_communications_research.py` |
| API adapter | Proposed `app/communications_research.py`, `tests/test_communications_research_api.py`; existing `app/main.py` router registration; existing auth/paywall owners unchanged |
| Shared-page client | Proposed `templates/communications_research.js`, `templates/communications_research.css`, `tests/test_communications_research_ui.py`; existing `templates/state_of_themes.html.j2` gets the minimal mount/includes and existing asset publication path |
| Test fixtures | Proposed `tests/fixtures/communications/first_vertical.json`; derived from the public reference cases, with clearly synthetic test-only admission/identity fixtures from existing owner tests |
| Real evidence | Existing owner-approved private paths only, resolved during Task 7. No new live storage directory is specified or authorized |

Before product writes, Fable reconciles the exact current files and live modifying effects once, including the shared Robotics assertion work and historically overlapping #7462/#7664/#7669 paths. Those PR numbers are collision leads, not current ownership claims. A historical author or absent reply is not a lease; an unresolved live effect is not expired. Shared changes stay with the admitted shared writer. Independent comparison and UI tests can proceed using explicit fixtures while dependent source admission remains held.

The tasks below are dependency-sized work units, not a demand for eight separate PRs. Prefer one useful A1 vertical with its prerequisites consumed through their actual owners. Do not merge a succession of empty infrastructure-only features and call the investor job finished.

## Proposed pure interfaces

The following names and signatures are part of this plan, not existing APIs. Use frozen dataclasses and closed validation in the proposed modules; no arbitrary dictionaries cross the production boundary.

```python
# communications_measures.py
from dataclasses import dataclass
from decimal import Decimal
from typing import Literal

@dataclass(frozen=True)
class Measure:
    ref: str
    metric: str
    population: str
    period: tuple[str, str]
    currency: str | None
    scale: Decimal
    basis: str
    value: Decimal | None
    domain: str
    definition_ref: str

@dataclass(frozen=True)
class Guidance:
    ref: str
    metric: str
    population: str
    period: tuple[str, str]
    currency: str | None
    scale: Decimal
    basis: str
    lower: Decimal | None
    upper: Decimal | None
    lower_inclusive: bool | None
    upper_inclusive: bool | None
    published: str
    vintage: str
    definition_ref: str

@dataclass(frozen=True)
class Result:
    status: Literal['COMPARABLE', 'QUALIFIED', 'INCOMPATIBLE', 'UNAVAILABLE']
    value: Decimal | None
    label: str
    refs: tuple[str, ...]
    reason: str | None

# Public functions; comparison definitions and domains are from reviewed recipes.
# compare_period(current, prior, *, mode='pct') -> Result
# compare_guidance(actual, guide) -> Result
# cash_bridge(*, inflow, outflows, expected_refs) -> Result
# validate_view(payload) -> None, in communications_research.py
# compose_communications_research(*, owner_bundle, generated_at) -> dict
```

A `Measure` is a private in-memory adapter of an already validated native assertion, not another persisted fact. `population`, `basis`, `definition_ref`, currency and scale are exact admitted comparison metadata. `compare_period` permits the explicit prior-year same-quarter interval only through the reviewed recipe; it never decides from duration alone that unrelated periods are comparable. `cash_bridge` takes positive magnitude outflow records and a closed expected-ref set, refusing duplicates or omissions. Signed source values remain representable but cannot be subtracted twice through a sign-convention guess.

`owner_bundle` is an internal typed result assembled from actual native readers or an explicit test fixture. Its fields are fixed issuer slots, native evidence rows and decoded assertions, source manifests, curation-subtype block results, identity/route results and rights/read health. It is not user input, a new serialized store, or a substitute for a validated owner bridge.

### Task 1 — Integrate the shared financial-assertion amendment

**Outcome:** the one curation path can represent losses, cash outflows, units, ranges and original guidance without weakening Robotics.

**Consumes:** the accepted current shared assertion contract or its explicitly reviewed proposal, plus spec section 4.
**Produces:** the shared validator/codec with optional `measurement_context`; a type-scoped `validate_numeric_domain(predicate, domain, value)` helper; legacy behavior preserved.

- [ ] Read the current shared schema/codec and check the proposed amendment against its accepted revision. If another admitted writer owns the path, send the exact delta through that owner rather than implementing a clone. No source release is inferred from reading its plan.
- [ ] Add closed measurement-context fields exactly as spec section 4 defines. Resolve each numeric domain from its reviewed definition and verify agreement with the consumer recipe; a supplied `signed_amount` label alone is not authority.
- [ ] Write discriminating numeric-domain tests. `ValueError` below may be the shared contract's existing subclass, but do not introduce a second error hierarchy merely for this consumer.

```python
from decimal import Decimal
import pytest
from engine.theme_graph.curation_assertion import validate_numeric_domain

def test_signed_financial_cash_and_physical_count_are_distinct():
    validate_numeric_domain('REPORTED_FINANCIAL_MEASURE', 'signed_amount', Decimal('-5855'))
    with pytest.raises(ValueError):
        validate_numeric_domain('DOCUMENTED_PRODUCT_INCLUSION', 'nonnegative_count', Decimal('-1'))
    with pytest.raises(ValueError):
        validate_numeric_domain('DOCUMENTED_PRODUCT_INCLUSION', 'signed_amount', Decimal('-1'))
    with pytest.raises(ValueError):
        validate_numeric_domain('REPORTED_FINANCIAL_MEASURE', 'signed_amount', Decimal('NaN'))
```

- [ ] Run `python3 -m pytest tests/test_theme_graph_curation_assertion.py -q`. Prove the missing behavior fails before implementing it; absence of the shared dependency is a dependency failure, not a test PASS.
- [ ] Implement domain checks, period ordering, positive scale, unknown/range/inclusivity behavior and FORWARD_TARGET compatibility in the shared validator. The revision hash includes the new context. Physical-count semantics and all-false authority stay intact.
- [ ] Add legacy-null, unknown-field, zero/negative scale, reversed range, future guidance versus achieved-result, same-URL changed-byte and changed-selector tests using the incumbent shared assertion fixture. Extend that actual fixture; do not import this research JSON as a native accepted receipt.
- [ ] Run focused shared tests plus existing Theme Graph contract regressions. Commit the exact admitted scope only; record the dependency SHA consumed by the consumer task.

### Task 2 — Prove native persistence and K1 clock binding

**Outcome:** the assertion survives the actual native write/read boundary and its source clocks remain visible in the accepted evidence subtype.

**Consumes:** Task 1 shared codec and existing `write_evidence(rows, lane=None, allow_backfill=False)` / `read_evidence()`.
**Produces:** a native curation reader result and validated subtype blocks, not a new evidence collection.

- [ ] Extend the existing evidence schema, append the optional column to `EVIDENCE_COLUMNS`, and encode canonical JSON through the shared codec. Modify only the existing write/read validation path.
- [ ] Add a temporary-root round-trip test to the shared test suite. `accepted_test_assertion` and `native_test_receipt` are test fixtures created here by adapting the existing owner fixtures, with synthetic identity/retention explicitly labeled. Their receipt is the existing evidence-row shape and the payload follows Task 1.

```python
def test_native_round_trip(monkeypatch, tmp_path, accepted_test_assertion, native_test_receipt):
    from engine.theme_graph import store
    from engine.theme_graph.curation_assertion import encode_assertion, decode_assertion
    monkeypatch.setattr(store, 'evidence_path', lambda: tmp_path / 'evidence.parquet')
    row = dict(native_test_receipt)
    row['curation_assertion'] = encode_assertion(accepted_test_assertion)
    assert store.write_evidence([row], lane='nightly') == 1
    assert store.write_evidence([row], lane='nightly') == 0
    got = store.read_evidence().iloc[0]['curation_assertion']
    assert decode_assertion(got) == accepted_test_assertion
```

- [ ] Before live writes, prove that missing lane/render lane cannot append. Never use `allow_backfill=True` to bypass forward admission. In tests patch only the temporary path; do not change a production data root.
- [ ] Add the curation subtype to the existing K1 vocabulary over the same reader. Preserve every registered native clock and explicit unknown grain. Extend `tests/test_evidence_foundation_contract.py` using its actual native-reference fixture and validation API, not guessed cross-type join triples.
- [ ] Pin negative cases: omitted source clock; substituted curation date for upstream publication; body embedded in K1; true authority flag; date-only historical intraday cutoff; and unsupported evidence-to-security recipe. All refuse or degrade according to the existing contract.
- [ ] Run `python3 -m pytest tests/test_theme_graph_curation_assertion.py tests/test_evidence_foundation_contract.py -q`. This proves fixture behavior, not private production binding. Commit and record exact shared source consumed.

### Task 3 — Implement comparable arithmetic and reference fixtures

**Outcome:** valid changes and guidance comparisons are computed, while incompatible measurements cannot manufacture a surprise.

**Files:** new `communications_measures.py`, `tests/test_communications_measures.py`, and the labeled first-vertical test fixture.
**Consumes:** validated measurement assertions from Tasks 1–2; public CV01–CV12 examples in the proof companion.
**Produces:** the frozen `Measure`, `Guidance`, `Result` and three pure comparison functions defined above.

- [ ] Create the fixture with the seven source selectors and source-native units from the proof companion. Keep synthetic test admission/identity separate from copied source values. The application must never read a file under `tests/` as production evidence.
- [ ] Add a concrete test helper in this test module:

```python
from decimal import Decimal as D
from engine.market_ontology.communications_measures import Measure, Guidance, compare_guidance

def m(value, *, metric='revenue', scale='1', basis='reported'):
    return Measure('fixture:actual', metric, 'fixture:issuer',
                   ('2026-04-01', '2026-06-30'), 'USD', D(scale), basis,
                   None if value is None else D(value), 'nonnegative_amount', 'fixture:definition')

def test_inside_range_is_not_above_guidance():
    g = Guidance('fixture:guide', 'revenue', 'fixture:issuer',
                 ('2026-04-01', '2026-06-30'), 'USD', D('1'), 'reported',
                 D('58000'), D('61000'), True, True, '2026-04-29',
                 'original_company_guidance', 'fixture:definition')
    out = compare_guidance(m('60801'), g)
    assert out.label == 'WITHIN_ORIGINAL_RANGE'
    assert out.refs == ('fixture:actual', 'fixture:guide')
    assert compare_guidance(m(None), g).status == 'UNAVAILABLE'
    assert compare_guidance(m('60801', basis='adjusted'), g).status == 'INCOMPATIBLE'
```

- [ ] Run `python3 -m pytest tests/test_communications_measures.py -q` and prove new behavior fails.
- [ ] Implement Decimal-only operations after metadata matching. Explicitly scale USD million guidance to USD thousand actuals. Preserve inclusive/exclusive bounds. A rounded interval straddling a boundary is qualified/indeterminate. Exact floor equality is not a below-floor result.
- [ ] Reject automatic percentages on zero/negative prior denominators; return useful absolute changes through `mode='absolute'`. Refuse double-used cash references, missing expected cash components, mixed scopes/periods/currencies or incompatible definitions. Source-restated or accepted-bridge comparisons require their actual bridge reference.
- [ ] Assert CV01–CV12 values and meaning. Add negative tests for pretending company-defined ex-TAC is GAAP revenue, combining unlike cash definitions, summing overlapping segments, or labeling original guidance as consensus. Rerun all measure tests, then commit the module and fixtures.

### Task 4 — Compose the four-company business view and routes

**Outcome:** all four fixed companies appear with valid evidence, explanations, limitations and qualified company links; no stock score is produced.

**Files:** new F04 composer, closed consumer schema and `tests/test_communications_research.py`.
**Consumes:** Task 2 owner blocks, Task 3 results, exact native identity/route results, current rights/freshness manifests.
**Produces:** `compose_communications_research(*, owner_bundle, generated_at)` and `validate_view(payload)`.

- [ ] Define internal `OwnerBundle` and fixture builder in this module's tests from the field list under Proposed pure interfaces. The production bundle must be constructed after actual owner validation. The fixture builder is named `four_company_bundle` and has keyword options `omit`, `unresolved`, `corrected`, `rights_blocked`, defaulting to empty tuples. It produces explicitly synthetic owner fixtures, not native deployment claims.
- [ ] Write tests before composer implementation:

```python
def test_missing_company_does_not_shrink_denominator(four_company_bundle):
    from engine.market_ontology.communications_research import compose_communications_research
    out = compose_communications_research(
        owner_bundle=four_company_bundle(omit=('Magnite',)),
        generated_at='2026-09-23T12:00:00Z')
    assert out['coverage']['required_issuers'] == 4
    assert len(out['panels']) == 4
    assert out['quality'] == 'partial'
    assert any(p['label'] == 'Magnite' and p['quality'] != 'ready' for p in out['panels'])
    assert all(v is False for v in out['authority'].values())
```

- [ ] Run the focused test red, implement deterministic role ordering and fixed coverage, then test the complete case. Missing optional consensus produces an explicit unavailable field and does not invalidate otherwise complete descriptive evidence.
- [ ] Derive view identity from exact source manifests and recipe revision, excluding volatile response-build time. A correction changes dependent result/input refs; unrelated blocks stay stable. Each source block retains its native evidence subject; do not mark an unsupported security recipe successful.
- [ ] Use current validated GMI/Data OS resolution results and approved route values. Group Alphabet once by actual issuer identity while keeping distinct valid securities. Unknown issuer/security produces no invented stock URL, price or holdings enrichment. Verify route scheme/path and encode the owner-provided fragment safely.
- [ ] Add the four reviewed explanation templates from the proof companion. Each includes direct support, labeled interpretation, contrary/limiting evidence and a watch condition. Reject a recipe that claims cross-company budget transfer from growth differences alone.
- [ ] Enforce response limits, finite/closed JSON and all-false authority. Do not serialize retained source bodies, credential data, private customer data or unapproved rights fields. Run both measure/composer tests and commit the consumer-only scope.

### Task 5 — Add the existing-Macro paid read route

**Outcome:** eligible readers receive the bounded view; ineligible requests never reach private readers and cannot leak via an error response.

**Files:** proposed `app/communications_research.py`, existing `app/main.py`, new API tests.
**Consumes:** Task 4 pure composer and actual owner readers. **Produces:** one router and a dependency `require_communications_user`, plus internal `load_owner_bundle` with no caller-specified paths.

- [ ] Mirror the existing `require_user -> enforce_site_full(always=True)` pattern and existing private APIRoute error treatment. Keep success/error JSON bounded; do not include source bodies or arbitrary exception strings. Register the router explicitly rather than swallowing its import failure.
- [ ] Add a testable `require_communications_user` dependency wrapper for the existing auth policy; this is not a new identity or permission authority. `load_owner_bundle()` invokes only the existing native accessors in the server configuration and refuses unqualified private binding.
- [ ] Write API tests red using FastAPI's existing test harness. `app` below is the fixture mounting only the proposed router; no production server is started.

```python
from fastapi import HTTPException

def test_auth_denial_precedes_private_read(app, client, monkeypatch):
    from app import communications_research as cr
    def deny():
        raise HTTPException(401, 'Authentication required')
    def forbidden_read():
        raise AssertionError('private owner read after denial')
    app.dependency_overrides[cr.require_communications_user] = deny
    monkeypatch.setattr(cr, 'load_owner_bundle', forbidden_read)
    try:
        r = client.get('/api/themes/communications/research/v1')
        assert r.status_code == 401
        assert r.headers['cache-control'] == 'private, no-store'
        assert 'noindex' in r.headers['x-robots-tag']
    finally:
        app.dependency_overrides.clear()
```

- [ ] Implement success, anonymous, free-tier, expired-session, malformed query, owner-unavailable and unexpected-error paths. A server-side owner failure returns a generic private unavailable error, not a credential/path/stack disclosure. Unknown query parameters fail 422; do not accept a hidden `source_url` or `ticker` option.
- [ ] Run tests proving entitlement-off global switches do not bypass `always=True`, headers survive all error paths, and an oversized response fails closed. The consumer route remains GET-only and cannot append evidence, write watchlists or call an LLM.
- [ ] Run `python3 -m pytest tests/test_communications_research_api.py -q` plus applicable existing access-boundary tests. Commit without enabling a live production fixture or asserting deployment.

### Task 6 — Integrate the compact shared-page interaction

**Outcome:** the user can discover and use the comparison without inflating or changing the existing theme board.

**Files:** minimal Theme Tracker template mount/includes, proposed canonical client/style source under `templates/`, UI tests and approved existing asset-build inclusion. Generated `site/` output is produced through the incumbent builder/publication path, not hand-maintained as a second source.
**Consumes:** Task 5 API; existing `MDXAuth.client().auth.getSession()` pattern as actually exposed through `MDXAuth.client()` then `client.auth.getSession()`; existing template/design components. **Produces:** one accessible research disclosure/module shared by entry and hash navigation.

- [ ] Before styling, bind the approved existing shared detail/disclosure component and dark/light design tokens. If the shared template lacks the required interaction, the same shared-template owner adds the minimal component; do not create a separate Communications shell or font/palette. Record the exact accepted reference used.
- [ ] Add a closed-by-default `<details id="communications-research">` mount only if the accepted shared interaction is disclosure-based; otherwise mount that accepted interaction with this stable anchor. Its summary identifies Communications research, not a new canonical-theme card. Opening fetches once; closing does not alter board state.
- [ ] Use the existing auth client and a same-origin API call. The design pattern is:

```javascript
const client = await window.MDXAuth.client();
const result = await client.auth.getSession();
const token = result && result.data && result.data.session && result.data.session.access_token;
const headers = {Accept: 'application/json'};
if (token) headers.Authorization = 'Bearer ' + token;
const response = await fetch('/api/themes/communications/research/v1', {
  credentials: 'same-origin', cache: 'no-store', headers, signal: controller.signal
});
```

This fragment is planned code, not run here. Read the current auth lifecycle before binding session changes; use its existing subscription, not polling or a second token cache. Guard each in-flight result with the active session/request identity. Abort and clear on sign-out/session change, and revalidate on page restore before showing old private state.

- [ ] Render through safe DOM text, validated links and semantic tables/disclosures. No untrusted `innerHTML`. Show the declared period, units and unavailable consensus; do not calculate financial ratios in JavaScript. Add EN/ZH reviewed labels and dark/light treatment from the same component system.
- [ ] Add browser tests to the repository's existing supported runner for: no request while closed; one request on open; direct hash open; no repaint from a stale post-logout response; bfcache/pageshow revalidation; keyboard open/close/focus restoration; long Chinese copy; 390-pixel stack; and missing company/expired-session states. Keep expected requests and panel counts exact.
- [ ] Add a template regression asserting the canonical-theme collection count/order and existing theme calculation inputs are byte/semantically unchanged by this entry. Run existing design-system/style-injection checks on changed lines. A screenshot alone does not establish no leakage.
- [ ] Commit source and only the generated artifacts required by existing publication rules. No live current payload may be embedded in a JS fixture, screenshot repository, source map or public JSON.

### Task 7 — Qualify real native admission, identity and private publication

**Outcome:** the first slice consumes real accepted owner data rather than passing exclusively on fixtures.

**Consumes:** Tasks 1–6, current configured native owners and their admission/review permissions. **Produces:** existing-owner evidence and acceptance receipts identifying actual source/reader/generation, not a new operational registry.

- [ ] Fable/shared source owner identifies the exact current private retention/publication binding already approved for detailed GMI curation. Record configured location and source of authority in the existing private receipt. If none is proven, hold real admission and escalate that specific architecture decision; do not create a replacement storage system or silently use public evidence.parquet.
- [ ] Retain the seven source documents/selected facts through the actual owner path with real digests and publication/observation clocks. Obtain source review and rights disposition for the declared four-company use. A Git research citation is not substituted for these receipts.
- [ ] Resolve all four company/issuer/eligible-listing routes through the actual identity owner. Preserve Alphabet instrument alternatives. Any unresolved required journey keeps the four-company release partial while its source-only explanation remains usable.
- [ ] Admit observations only through the existing allowed writer/admission path; confirm decoded readback and K1 subtype clocks. No render/API/browser writer and no backfill bypass. Record the actual receipt and generation produced by this action.
- [ ] Compare live API results to the admitted values, not to assumptions that fixture values must remain current. Corrected or newer company reports require a new reviewed input generation and recomputation. Preserve the original fixtures as historical tests.
- [ ] Use actual publisher inventories to test absence of detailed current payloads from public Git/Pages, static HTML/JSON, public R2, source maps and alternate mirrors. Report the exact tested set; do not claim all mirrors from a single URL. Rights denial must be proven before serialization, not only hidden by CSS.
- [ ] Mark native qualification complete only when receipts and negative publication proof are read back. A missing identity or private binding blocks this task's acceptance, not all independent code work. No hypothetical path/receipt is prefilled in this plan.

### Task 8 — Independent review, real-path proof and scoped release

**Outcome:** the four-company investor job works on the real deployed path without changing theme/trade authority.

**Consumes:** exact implementation head and Task 7 live owner receipts. **Produces:** independent review, exact-head release evidence and bounded A1 acceptance under existing owners.

- [ ] Obtain independent review of signed/bounded math, source meaning, identity, clocks, privacy and shared-template integration. The author cannot self-certify this gate. Resolve findings on the same admitted carrier and re-run the affected tests.
- [ ] Run current repository Agent OS/source validation and the exact required CI checks. The commands in this plan are test instructions, not this research turn's results. Preserve source/merge/deployment identities separately and do not outrun pending checks.
- [ ] In the deployed environment, prove source-to-comparison-to-company-to-user-initiated existing watchlist behavior for all four issuers. Verify exactly what write the user action produced; opening a company page is not saving a watchlist item.
- [ ] Capture the dark/light x EN/ZH x 1440/390 matrix and representative anonymous/free/expired/missing/corrected states. Record sanitized proof through the incumbent private evidence owner; do not publish current paid payloads as screenshots or response dumps.
- [ ] Prove fallback: the existing theme board still works when the module is unavailable, a corrected fact changes only dependent explanations, and unauthorized endpoints/mirrors cannot reveal the view. Rollback removes/disables the module through the existing release mechanism without deleting native evidence history.
- [ ] Only after current release authority and exact-head gates pass may the admitted release owner deploy/release the implementation. Research PR #7794 remains a separate design carrier unless explicitly released for its own purpose; no blanket auto-merge.
- [ ] Update existing Agent OS and applicable projections with A1's actual capability and remaining sector roadmap. Do not mark the whole Communications mission complete. Future forecasting, regional modules and predictive promotion retain their separate qualification.

## CRV acceptance coverage — written requirements, none executed here

| ID | Discriminating behavior | Owning tasks |
|---|---|---|
| CRV-01 | Negative consolidated cash survives; physical negative counts fail | 1,3 |
| CRV-02 | Unknown numeric values stay null and do not become zero | 1,3,4 |
| CRV-03 | Unknown fields, nonfinite values and invalid scale fail closed | 1,3,4 |
| CRV-04 | Original range/floor/ceiling and inclusivity remain explicit | 1,3 |
| CRV-05 | Same URL/date changed bytes or locator creates a new assertion revision | 1,2,4 |
| CRV-06 | Legacy Robotics assertions survive absent/null measurement context | 1,2 |
| CRV-07 | Native column/codec round-trip retains measurement context | 2 |
| CRV-08 | Render/missing-lane cannot write; rerun does not duplicate receipt | 2,7 |
| CRV-09 | Upstream, reporting, observation and curation clocks do not collapse | 1,2,4 |
| CRV-10 | Correction appends; historical evidence remains and dependent result changes | 2,4,8 |
| CRV-11 | K1 retains native evidence subject and all-false authority | 2,4 |
| CRV-12 | Unsupported cross-type/security recipe stays refused | 2,4 |
| CRV-13 | Unresolved identity gets no guessed stock, price or portfolio binding | 4,7 |
| CRV-14 | Alphabet appears once economically with explicit eligible securities | 4,7,8 |
| CRV-15 | Valid owner route reaches the actual existing company page | 4,7,8 |
| CRV-16 | Missing issuer stays in four-company denominator and prevents full ready | 4 |
| CRV-17 | Mixed definition/period/currency/gross-net comparison is refused or bridged explicitly | 3,4 |
| CRV-18 | Zero/negative prior values do not generate misleading percent growth | 3 |
| CRV-19 | Cash components appear once; issuer cash is not assigned to Search | 3,4 |
| CRV-20 | Ex-TAC, GAAP revenue and source-defined cash stay distinguished | 3,4 |
| CRV-21 | No cross-role revenue sum or implied budget-transfer causality | 3,4 |
| CRV-22 | Rounded-boundary ambiguity is not forced into a surprise verdict | 3 |
| CRV-23 | No consensus estimate means unavailable consensus, not a guessed surprise | 3,4,6 |
| CRV-24 | Explanation carries support, interpretation, limitation and watch condition | 4,6 |
| CRV-25 | Fixed limits/closed JSON hold; oversized response cannot silently truncate | 4,5 |
| CRV-26 | Authentication and entitlement denial occur before private owner reads | 5,7 |
| CRV-27 | Private headers and sanitized errors survive every response path | 5,7 |
| CRV-28 | Arbitrary URL/path/ticker/formula/prompt/query input fails; no API mutation | 5 |
| CRV-29 | Closed entry does not inflate/recalculate/reorder canonical theme board | 6,8 |
| CRV-30 | One deliberate-open request; no polling, source crawl or LLM call | 5,6 |
| CRV-31 | Logout races cannot repaint private data; restored page revalidates | 6,8 |
| CRV-32 | Public artifacts and browser persistent storage contain no current paid view | 6,7,8 |
| CRV-33 | Dark/light and EN/ZH both preserve hierarchy, units and state meanings | 6,8 |
| CRV-34 | 1440/390 layouts, keyboard and screen-reader navigation remain usable | 6,8 |
| CRV-35 | Escaped source text and safe URLs cannot execute markup or redirect unsafely | 4,6 |
| CRV-36 | Actual qualified source/identity/private binding, not fixtures, drives acceptance | 7,8 |
| CRV-37 | Existing user-initiated watchlist action is separately proven from navigation | 8 |
| CRV-38 | Alternate-mirror denial, coherent generation and rollback preserve prior board | 4,7,8 |
| CRV-39 | Independent review and source/CI/deploy/browser receipts are separate | 8 |
| CRV-40 | No membership/ranking/trade promotion; A1 does not complete whole program | 1,4,8 |

## Plan review and remaining gates

All sixteen specification sections map into Tasks 1–8 and the full-program roadmap retained in the spec. This plan details A1 rather than prescribing unqualified formulas for every later family. The seven prior research phases and company map remain the substantive expansion content, not work for each engineer to repeat.

Unresolved execution conditions are exact: acceptance of the shared financial amendment; its actual native/K1 implementation; a proven existing private owner binding; live identity/route qualification; independent design/code review; real-source/browser acceptance. No claim is made that any of these was closed merely by writing this document. The chosen Fable principal integration method remains unchanged, and no Fable provider session has been bound or STARTed.

The first next principal action is to review this specification/plan against the shared assertion owner, resolve the narrowly scoped compatibility/privacy decisions, and prepare the final Fable execution packet on the existing organizational path. Research continuation remains on #7794; admitted implementation uses its own current-main custody. This distinction is a planned transition, not an authorized retry or transfer of an unknown effect.
