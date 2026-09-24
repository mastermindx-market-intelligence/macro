# Finance Sector Intelligence Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox syntax for tracking.

**Goal:** Ship a paid, evidence-backed Finance Intelligence journey that lets a reader move from Financials to granular Finance subthemes, understand the operating-to-per-share rerating mechanism, inspect company exposure and evidence, and return to existing stock/basket/sector workflows without creating duplicate truth planes.

**Architecture:** Keep Theme Tracker as the canonical-theme router and Sector Intelligence as the Financials outer owner. Build one read-only Finance projection composed from existing Theme Graph, Financial Intelligence, expectations/revisions, market-data, basket, macro/rates/credit and identity owners. Current full-fidelity research stays authenticated/private/no-store. The first real vertical is Financial Rails & Market Infrastructure; the same contract then expands across Banking/Credit, Asset/Wealth/Insurance and Global/Disruption domains.

**Tech Stack:** Python 3, FastAPI, JSON Schema Draft 2020-12, existing Sector Intelligence contract registry, existing Theme Graph/Evidence Foundation, Jinja/static site templates, vanilla JS/CSS, pytest, existing browser-proof harness.

**Spec:** research/finance/FINANCE_R11_PRODUCT_AND_VISUALIZATION_ARCHITECTURE_FREEZE_2026-09-23.md. Supporting source-law: research/finance/FINANCE_R12_CURRENT_MAIN_ARCHITECTURE_COLLISION_AND_CUSTODY_REVIEW_2026-09-24.md and research/finance/FINANCE_R10_WHOLE_CASE_SYNTHESIS_AND_ADVERSARIAL_REVIEW_2026-09-23.md.

## Global Constraints

- Implementation starts from then-current Macro main, never from PR #7786.
- PR #7786 remains Draft/HOLD research evidence and is not auto-merged.
- Re-pin protected Mastermind procedure before modification.
- Reconcile #7870, #7777, #7462, #7664, #7849, #7797 and #7669 before touching overlapping paths.
- Consume the accepted shared Theme Graph curation-assertion contract; never create a Finance-specific evidence ledger.
- Consume the accepted Sector Dossier contract as the Financials outer object when it lands; never create a parallel sector truth plane.
- No new universal Finance canonical theme.
- Existing regional_banks, payments_fintech, insurance, XLF legs, intl_banks and intl_insurers remain incumbent basket/context owners.
- First release admits zero new price baskets unless the basket owner separately approves PIT membership, security identity, rights and weighting.
- No duplicate identity, source, revisions, valuation, price, basket, queue, auth or publication store.
- Financial Intelligence is consumed for supported facts but is not treated as a complete global security master.
- Current full-fidelity research bodies never ship in public Git/static HTML/localStorage/IndexedDB/service-worker caches.
- All API success and error paths are authenticated where required, private/no-store, Vary Authorization, noindex/noarchive and nosniff.
- No Finance attractiveness score, rank, gate, position size or trade authority.
- Four analytical planes remain separate: operating economics, expectations, valuation and price recognition.
- Every valuation displays denominator, horizon and information clock.
- Every material exposure displays numerator/denominator or an explicit missing state.
- Browser acceptance: 1440 and 390, EN/ZH, light/dark, keyboard-only, visible focus, reduced-motion, no page-level horizontal scroll on mobile.

## Review Focus

1. A global issuer has source evidence but no canonical PIT security binding: render attributed evidence with IDENTITY_UNRESOLVED and no guessed stock/valuation join.
2. Historical analyst consensus is unavailable: render NO_HISTORICAL_CONSENSUS and preserve management guidance separately.
3. A capital/accounting regime changes the denominator: render REGIME_BREAK_NOT_COMPARABLE and suppress percent-change arithmetic.
4. Two slices share most securities or the same driver: expose overlap rather than count both as independent confirmation.
5. The private evidence service is unavailable or stale: keep the legacy Financials/Theme Tracker surfaces functional and show a bounded degraded state without leaking private payload.

---

## File structure and ownership

Expected new files after current-owner reconciliation:

- contracts/sector_intelligence/finance_intelligence_read_model.v1.schema.json — display/read contract only.
- data/sector_intelligence/fixtures/finance_intelligence_read_model.v1.valid.json — synthetic contract fixture only.
- engine/sector_intelligence/finance_projection.py — pure owner-preserving composition.
- engine/sector_intelligence/finance_overlap.py — deterministic overlap calculations.
- tests/test_finance_intelligence_contract.py — schema/authority/negative contract tests.
- tests/test_finance_intelligence_projection.py — composition/conflict/null/regime tests.
- tests/test_finance_overlap.py — overlap arithmetic and hierarchy tests.
- app/finance_intelligence.py OR accepted existing Sector Intelligence router — authenticated read route only; choose exactly one after pickup reconciliation.
- tests/test_finance_intelligence_api.py — auth/no-store/error/degraded tests.
- templates/finance_intelligence.html.j2 — public shell only.
- site/assets/js/finance-intelligence.js — rendering/filter/accessibility only, no analytical owner math.
- site/assets/css/finance-intelligence.css — scoped styles using accepted design tokens.
- scripts/build_finance_intelligence_shell.py — deterministic static shell builder if current site pattern requires it.
- tests/test_finance_intelligence_page.py — shell/static contract.
- tests/js/finance_intelligence.test.mjs — client rendering and degraded states.
- tests/test_finance_owner_preservation.py — no duplicate owners / no public full-fidelity payload / canonical theme count unchanged.

Shared paths may be modified only after exact current custody is reconciled:
- templates/state_of_themes.html.j2
- app/main.py
- accepted Sector Intelligence router/registry
- accepted shared theme-research assets

Protected/no-direct-edit by Finance unless separately released:
- engine/theme_graph/store.py
- config/theme_crosswalk.yml
- data/baskets/membership.json
- global identity/security stores
- global theme.css while an incumbent design-system writer owns it

---

### Task 0: Fable pickup, current-main and source-custody freeze

**Files:**
- Create on implementation carrier: agentos/handoffs/GMI-FINANCE-IMPLEMENTATION-<date>-fable.md
- Do not modify product code in this task.

**Interfaces:**
- Consumes: PR #7786 R10/R11/R12 exact artifacts.
- Produces: exact current-main SHA, active dependency heads, owned-path matrix, implementation operation key and separate PICKUP_ACK/START receipts.

- [ ] **Step 1: Re-pin protected procedure and current Macro main**

Read INDEX, ACTIVE_EXECUTION, WEB_CEO_DELEGATION, COMMISSION_WAVE, WORKER_AVENUE_ROUTING, source-continuity and dialogue laws from one protected Mastermind SHA.

Record the exact current Macro main SHA.

- [ ] **Step 2: Reconcile dependency carriers**

Read current heads/file sets for #7870, #7777, #7462, #7664, #7849, #7797 and #7669.

Expected output is a table with one of:
FREE, CONSUME_ACCEPTED, WAIT_FOR_OWNER, COORDINATE_SHARED_EDIT, STALE_CUSTODY_CLAIM.

- [ ] **Step 3: Create a fresh implementation branch from current main**

The implementation branch name should be operation-specific, for example:
sol/finance-intelligence-implementation-<date>

Do not branch from #7786.

- [ ] **Step 4: Emit separate START only after gates clear**

PICKUP_ACK is context receipt only. START means product/source execution has actually begun.

- [ ] **Step 5: Commit the implementation checkpoint**

Commit only the new implementation handoff/checkpoint.

**Acceptance:** exact fresh-main ancestry, no overlapping active writer ignored, no product code modified before START.

---

### Task 1: Consume shared foundations and add the Finance read contract

**Files:**
- Create: contracts/sector_intelligence/finance_intelligence_read_model.v1.schema.json
- Create: data/sector_intelligence/fixtures/finance_intelligence_read_model.v1.valid.json
- Create: tests/test_finance_intelligence_contract.py
- Modify: engine/sector_intelligence/contracts.py only if the accepted registry does not auto-discover the new schema.

**Interfaces:**
- Consumes: accepted sector_dossier_read_model.v1 outer contract; accepted shared Theme Graph curation assertion when available.
- Produces: contract id finance_intelligence_read_model.v1.

- [ ] **Step 1: Write failing schema-registry test**

~~~python
def test_finance_contract_is_registered_and_display_only():
    registry = ContractRegistry.from_repo(ROOT)
    payload = json.loads(FIXTURE.read_text())
    registry.validate("finance_intelligence_read_model.v1", payload)
    assert payload["authority_caps"] == {
        "rank": False, "gate": False, "size": False, "trade": False
    }
~~~

Run:
pytest tests/test_finance_intelligence_contract.py -q

Expected: fail because contract/fixture is absent.

- [ ] **Step 2: Add the closed Finance read schema**

Required top-level fields:

~~~json
{
  "contract_id": "finance_intelligence_read_model.v1",
  "schema_version": "1.0.0",
  "generated_at": "...",
  "knowledge_cutoff": "...",
  "common_as_of": "...",
  "sector_ref": "sector:financials",
  "coverage": {},
  "material_changes": [],
  "domains": [],
  "slices": [],
  "company_exposures": [],
  "system_views": [],
  "macro_matrix": [],
  "conflicts": [],
  "freshness": {},
  "input_receipts": [],
  "authority_caps": {"rank": false, "gate": false, "size": false, "trade": false}
}
~~~

Each slice must carry:
slice_id, domain_id, name_en/name_zh, basket_state, rerating, indicators, valuation_anchor, conflicts, falsifiers, freshness, evidence_refs.

The rerating block must contain separate operating, expectations, valuation and price fields with explicit availability states.

- [ ] **Step 3: Add negative contract tests**

Test:
- missing knowledge_cutoff fails;
- a fifth fused score field is rejected by additionalProperties false;
- authority rank=true fails;
- regime-break values require comparability_state;
- historical consensus value without source/time fails.

- [ ] **Step 4: Run contract tests**

Run:
pytest tests/test_finance_intelligence_contract.py -q

Expected: all pass.

- [ ] **Step 5: Commit**

Commit message:
feat(sector-intelligence): add finance read-model contract

---

### Task 2: Build pure owner-preserving projection composition

**Files:**
- Create: engine/sector_intelligence/finance_projection.py
- Create: tests/test_finance_intelligence_projection.py

**Interfaces:**
- Consumes: already-read owner payloads; no network or store writes.
- Produces:
  compose_finance_projection(inputs: FinanceOwnerInputs, *, generated_at: datetime, knowledge_cutoff: datetime) -> dict

Define:

~~~python
@dataclass(frozen=True)
class FinanceOwnerInputs:
    sector_dossier: Mapping[str, Any]
    theme_evidence: Sequence[Mapping[str, Any]]
    financial_packets: Mapping[str, Mapping[str, Any]]
    expectation_observations: Mapping[str, Sequence[Mapping[str, Any]]]
    market_observations: Mapping[str, Sequence[Mapping[str, Any]]]
    basket_context: Mapping[str, Mapping[str, Any]]
    macro_context: Mapping[str, Any]
    identity_bindings: Mapping[str, Mapping[str, Any]]
~~~

- [ ] **Step 1: Write tests for four-plane separation and nulls**

~~~python
def test_missing_consensus_stays_missing():
    out = compose_finance_projection(inputs_without_consensus(), generated_at=NOW, knowledge_cutoff=NOW)
    card = by_slice(out, "card_networks")
    assert card["rerating"]["expectations"]["state"] == "NO_HISTORICAL_CONSENSUS"
    assert card["rerating"]["valuation"]["state"] != "IMPUTED_FROM_PRICE"
~~~

Also test IDENTITY_UNRESOLVED and REGIME_BREAK_NOT_COMPARABLE.

- [ ] **Step 2: Implement pure composition**

Rules:
- no I/O;
- never rewrite owner source values;
- normalize only into explicitly labelled comparison families;
- preserve source-native metric/value beside normalized family;
- compute conflict labels deterministically from explicit states;
- never generate rank/gate/size/trade fields.

- [ ] **Step 3: Add R10-derived conflict tests**

Pin:
EARNINGS_UP / P_E_DOWN,
BOOK_UP / P_B_DOWN,
POLICY_SUPPORT / NIM_PRESSURE,
REGULATORY_RATIO_DOWN / REGIME_BREAK.

- [ ] **Step 4: Run tests and commit**

Run:
pytest tests/test_finance_intelligence_projection.py -q

Commit:
feat(sector-intelligence): compose finance owner reads

---

### Task 3: Add overlap and basket-state projection without basket ownership

**Files:**
- Create: engine/sector_intelligence/finance_overlap.py
- Create: tests/test_finance_overlap.py

**Interfaces:**
- Consumes candidate/current membership projections.
- Produces:
  security_jaccard(a, b) -> float | None
  weighted_overlap(a, b) -> float | None
  overlap_report(slice_a, slice_b) -> dict

- [ ] **Step 1: Write arithmetic tests**

~~~python
def test_security_jaccard():
    assert security_jaccard({"V", "MA"}, {"MA", "AXP"}) == pytest.approx(1 / 3)
~~~

- [ ] **Step 2: Write hierarchy test**

Manager and vehicle relationships must be reported separately from exact security overlap.

- [ ] **Step 3: Implement five overlap dimensions**

Security, business-line, macro-driver, market-factor and ownership-hierarchy.

No overlap result is a score or membership signal.

- [ ] **Step 4: Run and commit**

Run:
pytest tests/test_finance_overlap.py -q

Commit:
feat(sector-intelligence): expose finance overlap context

---

### Task 4: Qualify private evidence/publication path and source rights

**Files:**
- Prefer shared files from accepted #7870 implementation.
- Create Finance-specific tests only where needed:
  tests/test_finance_private_publication.py

**Interfaces:**
- Consumes accepted Theme Graph curation assertions, rights snapshot API and existing private publication store/route.
- Produces no new storage plane.

- [ ] **Step 1: Verify shared dependency state**

If curation assertion/private publication is not accepted and current, stop only this lane with an exact dependency gate. Continue synthetic projection/UI work.

- [ ] **Step 2: Write privacy tests**

Assert:
- unauthenticated request blocked;
- free/non-entitled request blocked according to accepted paywall behavior;
- success has private, no-store;
- errors have private, no-store;
- no detailed assertion bodies appear under site/** or public source maps.

- [ ] **Step 3: Test rights refusal**

A rights_family that is unresolved/internal-only must not appear as a public/full-fidelity assertion.

- [ ] **Step 4: Commit tests/adapters only after owner path is known**

No new bucket, database, latest-state JSON or env override.

---

### Task 5: Admit and compose Money Movement real witnesses

**Files:**
- No public full-fidelity source bodies.
- Add only accepted curation records through the shared owner.
- Tests/fixtures may use synthetic/minimal redacted records.

**Interfaces:**
- Witnesses: V, MA, FI, FIS.
- Slices: card_networks, merchant_acquiring_processing, issuer_processing.

- [ ] **Step 1: Use existing R1–R9 research as the source census**

Do not ask workers to rediscover the sector. Workers may verify exact locators, rights and transcribe into the frozen assertion contract.

- [ ] **Step 2: Admit source-backed role assertions**

Visa/Mastercard:
network vs issuer/acquirer distinction, volume/transactions, incentives/services.

Fiserv/FIS:
merchant/acquirer/processor/core/issuer-processing roles with disclosed denominator and business scope.

- [ ] **Step 3: Add denominator tests**

A transaction-volume observation must not populate revenue exposure.
A business with no separated segment denominator must remain DIRECT_DIVERSIFIED or EXPOSURE_NOT_SEPARATELY_DISCLOSED.

- [ ] **Step 4: Compose one real Money Movement projection**

Require exact evidence refs, clocks and explicit missing consensus where absent.

- [ ] **Step 5: Commit accepted code/tests; keep live assertion data in approved private owner**

---

### Task 6: Admit and compose Securities Infrastructure real witnesses

**Files:** same owner paths as Task 5; no parallel store.

**Interfaces:**
- Witnesses: CME, ICE, NDAQ, BNY, STT, SPGI, MCO.
- Slices: exchanges_trading_venues, custody_asset_servicing, market_reference_data, ratings_credit_information, indices_benchmarks_etf_plumbing.

- [ ] **Step 1: Admit role assertions from existing research**

Keep venue, clearing, custody, data, index and ratings roles separate.

- [ ] **Step 2: Add mixed-business tests**

Nasdaq must retain multiple businesses rather than a single exchange purity label.
State Street AUC/A must not be converted mechanically into servicing revenue.
HKEX-style investment-income logic belongs in the generic tests: transaction growth is not all issuer growth.

- [ ] **Step 3: Compose a real Securities Infrastructure projection**

- [ ] **Step 4: Verify negative states and commit**

---

### Task 7: Add authenticated Finance API route

**Files:**
- Preferred: extend accepted Sector Intelligence router.
- If no router exists after owner reconciliation: Create app/finance_intelligence.py.
- Modify: app/main.py only for router registration.
- Test: tests/test_finance_intelligence_api.py
- Check: app/deploy/update.sh restart behavior if a new app router file is introduced.

**Interfaces:**
- GET /api/sector-intelligence/financials/finance/v1
- Returns finance_intelligence_read_model.v1.
- No writes.

- [ ] **Step 1: Write auth/private-header tests**

~~~python
def test_finance_api_is_private(client, entitled_user):
    r = client.get(URL, headers=entitled_user)
    assert r.status_code == 200
    assert r.headers["cache-control"] == "private, no-store"
    assert r.headers["vary"] == "Authorization"
~~~

Also assert 401/402/503 paths retain private headers.

- [ ] **Step 2: Implement route using accepted entitlement idiom**

Reuse require_user → enforce_site_full(always=True) or the accepted successor.

- [ ] **Step 3: No network I/O during request composition**

All upstream sources are existing owner reads/private retained data.

- [ ] **Step 4: Add incoherent-generation degradation test**

If required owner generations cannot be reconciled, return the precise unavailable section/state rather than a falsely coherent payload.

- [ ] **Step 5: Run and commit**

---

### Task 8: Build Finance Intelligence shell and core visuals

**Files:**
- Create: templates/finance_intelligence.html.j2
- Create: site/assets/js/finance-intelligence.js
- Create: site/assets/css/finance-intelligence.css
- Create: scripts/build_finance_intelligence_shell.py if current site pattern requires generation.
- Test: tests/test_finance_intelligence_page.py
- Test: tests/js/finance_intelligence.test.mjs

**Interfaces:**
- Consumes API read model only.
- Produces no analytical state.

- [ ] **Step 1: Write shell tests**

Require:
What Changed, Rerating Map, System Map, Subtheme Atlas, Company Exposure, Macro Matrix, Constraint Map, Evidence Drawer.

- [ ] **Step 2: Render Rerating Map first**

Desktop horizontal, mobile vertical.
Each node shows state, primary metric, clock and evidence action.

- [ ] **Step 3: Implement three selectable system views**

contractual_flow, infrastructure_access, public_equity_economics.

Never mix their edge semantics.

- [ ] **Step 4: Implement 52-slice atlas**

Semantic-only slices show no-basket state honestly.

- [ ] **Step 5: Implement exposure/conflict/evidence views**

No hidden scoring.
Evidence drawer must preserve focus and show source/locator/clocks/denominator/limitations.

- [ ] **Step 6: Run JS/page tests and commit**

---

### Task 9: Add Theme Tracker and Financials entry points without changing theme semantics

**Files:**
- Modify templates/state_of_themes.html.j2 only after #7870/shared mount custody is reconciled.
- Modify the current Financials context template/builder only through its incumbent owner-compatible seam.
- Do not modify scripts/build_state_of_themes.py if #7664 or accepted successor owns it.

**Interfaces:**
- Produces links only; no Finance stage/rank.

- [ ] **Step 1: Test canonical theme count unchanged**

~~~python
def test_finance_entry_does_not_become_canonical_theme(rendered):
    assert rendered.canonical_theme_count == BASELINE_COUNT
    assert "Finance Intelligence" in rendered.sector_deep_dives
~~~

- [ ] **Step 2: Add Sector Deep Dives Finance entry**

Outside canonical Watch/Broadening/Re-rating/Accelerating lanes.

- [ ] **Step 3: Add Financials context launch**

Existing equal-weight Financials thesis remains "participation gauge, not a buy list."

- [ ] **Step 4: Run targeted theme/basket non-interference tests and commit**

---

### Task 10: Expand Banking, Credit, Mortgage and Private Credit

**Files:**
- Reuse finance projection contract and private evidence owner.
- Add tests under tests/test_finance_intelligence_projection.py or focused companion if size requires.

**Interfaces:**
- Consume already researched banking/credit census and metric dictionary from PR #7786.

- [ ] **Step 1: Populate semantic slices**

Deposit Franchise Quality, regional/super-regional, NIM normalization, CRE, cards/consumer, specialty, mortgage originators, mortgage servicers, private-credit managers and BDC/direct-lending vehicles.

- [ ] **Step 2: Preserve manager-vs-vehicle law**

Private-credit manager and BDC must never share one earnings/valuation model.

- [ ] **Step 3: Add credit/vintage/null/regime tests**

Provision vs allowance vs charge-off stay distinct.
EPS accretion cannot substitute for TBVPS/capital.

- [ ] **Step 4: Verify real representative records and commit**

No new broad basket admission required.

---

### Task 11: Expand Asset/Wealth/Insurance

**Interfaces:**
- Consume PR #7786 asset/wealth/insurance census and metric dictionary.

- [ ] **Step 1: Populate asset/wealth slices**

Passive, active, wealth, retirement, alternatives, private-credit managers, fund administration.

- [ ] **Step 2: Populate insurance slices**

Personal P&C, commercial/specialty P&C, reinsurance, brokers, life/annuity, claims/data/workflow.

- [ ] **Step 3: Add denominator tests**

AUM/AUA/AUC are distinct.
Written premium != earned underwriting value.
Broker commissions != carrier premium.
Local solvency != parent distributable capital.

- [ ] **Step 4: Commit**

---

### Task 12: Expand Global/Regional and Structural Disruption semantics

**Interfaces:**
- Consume R9 global/regional packet plus disruption research.

- [ ] **Step 1: Preserve native regional measures**

No universal CET1/NPL/solvency/VONB normalization without comparability state.

- [ ] **Step 2: Render listing/security unresolved states**

A/H/ADR/share-class/currency remain first-class.

- [ ] **Step 3: Add disruption slices**

Stablecoin, digital custody/tokenization, open banking and agentic/AI finance remain semantic-first unless accepted exposure data exists.

- [ ] **Step 4: Add HKRBC regime-break test**

Old-basis 457% and HKRBC 304% must not render a -153pp deterioration.

- [ ] **Step 5: Commit**

---

### Task 13: Candidate basket overlays and overlap diagnostics

**Files:**
- No mutation to data/baskets/membership.json in this task.
- Consume current basket owner reads.

- [ ] **Step 1: Display incumbent broad context**

regional_banks, payments_fintech, insurance and existing XLF legs.

- [ ] **Step 2: Display candidate cohort state**

For Tier-1 research slices show candidate membership only where exposure/identity evidence exists.
Label CURRENT_MEMBERSHIP_ONLY or PIT_MEMBERSHIP_INCOMPLETE as appropriate.

- [ ] **Step 3: Show overlap**

Security/business/driver/factor/ownership overlap.

- [ ] **Step 4: Add regression test that candidate membership cannot write basket owner**

- [ ] **Step 5: Commit**

A later separate owner-approved wave may admit a new price basket after PIT/security/rights review.

---

### Task 14: Full degraded-state, accessibility and privacy qualification

**Files:**
- Tests only plus bounded fixes in files owned by Tasks 7–9.

- [ ] **Step 1: Run deterministic test set**

At minimum:
pytest tests/test_finance_intelligence_contract.py tests/test_finance_intelligence_projection.py tests/test_finance_overlap.py tests/test_finance_intelligence_api.py tests/test_finance_intelligence_page.py tests/test_finance_owner_preservation.py -q

Run JS tests for finance-intelligence.

- [ ] **Step 2: Privacy/source scan**

Assert no current full-fidelity assertion payload or private source object is emitted under site/**.

- [ ] **Step 3: Negative-state fixtures**

Prove:
NO_HISTORICAL_CONSENSUS,
IDENTITY_UNRESOLVED,
REGIME_BREAK_NOT_COMPARABLE,
SOURCE_STALE,
SOURCE_RIGHTS_HELD,
PIT_MEMBERSHIP_INCOMPLETE,
CAUSAL_EFFECT_UNMEASURED.

- [ ] **Step 4: Accessibility tests**

Keyboard focus, drawer focus restore, reduced motion, screen-reader labels, no color-only meaning.

- [ ] **Step 5: Commit qualification fixes**

---

### Task 15: Real-path browser proof and independent review

**Files:**
- Evidence under existing approved UX evidence conventions only.
- Do not commit private API bodies.

- [ ] **Step 1: Deploy candidate through accepted non-production/production-proof path**

Use exact head/release identity.

- [ ] **Step 2: Capture browser journey**

Prove:
state_of_themes → Financials → Finance Intelligence → Money Movement → company/evidence → Securities Infrastructure → existing stock route.

- [ ] **Step 3: Capture matrix**

1440/390 × light/dark × EN/ZH plus keyboard journey.

- [ ] **Step 4: Prove unauthorized and degraded paths**

Paid content unavailable to unauthenticated/non-entitled viewer; public shell reveals no private payload.

- [ ] **Step 5: Independent review**

Reviewer receives exact head, specs, tests and browser receipts.
Review must challenge:
owner duplication, identity guessing, clock leakage, hidden scoring, public-data leakage, basket survivorship and mobile accessibility.

- [ ] **Step 6: Repair only on same carrier and re-review changed head**

---

### Task 16: Release acceptance and program continuation

**Files:** existing release/Agent OS/PR evidence paths only.

- [ ] **Step 1: Require remote-complete source proof**

Exact implementation head is pushed and matches reviewed head.

- [ ] **Step 2: Require CI/security/browser proof**

Green CI alone is insufficient.

- [ ] **Step 3: Production-path acceptance**

A signed-in persona completes the real user journey on the accepted release.

- [ ] **Step 4: Reconcile product capability**

Only then may first-vertical Finance Intelligence be called PROVEN_LIVE.

- [ ] **Step 5: Preserve remaining expansion state**

If Tasks 10–13 are not all production-qualified at that point, keep the broader Finance programme PARTIAL and continue on fresh bounded waves. Do not call a first-vertical launch the entire 52-slice program complete.

---

## Self-review

**Spec coverage:** The plan maps owner preservation, four-plane rerating, 52-slice atlas, first vertical, evidence privacy, identity nulls, basket coexistence, overlap, global/regional comparability, UI hierarchy, mobile/accessibility and browser/production proof to explicit tasks.

**Placeholder scan:** No implementation task relies on an unspecified field or unspecified error behavior. Dynamic source-custody questions are explicit preflight gates with fail-closed behavior.

**Type consistency:** finance_intelligence_read_model.v1 is the sole new Finance read contract; compose_finance_projection returns that contract; API and UI consume the same contract. Overlap functions are display/context only.

**Review-focus tests:** all five review-focus cases are assigned to Tasks 1–4, 9, 12–14.

## Execution handoff

Execution method is already selected by Chairman intent: Fable is the coordinating principal, using the existing worker fabric for bounded tasks. Fable owns dependency/custody adjudication, integration and final acceptance; workers own the task-sized code/test/source-validation labor.
