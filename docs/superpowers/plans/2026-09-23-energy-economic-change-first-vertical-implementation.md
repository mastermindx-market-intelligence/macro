# Energy Economic Change Dossiers — First Vertical Implementation Plan

> **Execution instruction:** This is an implementation blueprint, not proof that any task has run. The assigned Fable CEO/orchestrator or accepted successor must execute task-by-task under current source/admission law, delegate bounded routine work where efficient, and retain integration/collision/privacy/final-acceptance judgment.

**Goal:** Ship the first production-proven **Nuclear Value Capture** Energy vertical so an entitled investor can move from Theme Tracker into the existing Nuclear & SMR detail, distinguish direct theme members from supplemental fuel exposure, understand how each selected business captures or fails to capture nuclear growth, inspect source/clock/limitations and honest expectations availability, then return to the existing company/entry workflow without changing any ranking, basket, entry, sizing or trade behavior.

**Architecture:** Consume existing GMI Theme Graph/ThemeState, Company/Earnings/financial/source owners, Data OS identity, accepted shared curation assertions, the accepted shared \`economic_change_dossier.v1\` (or owner-approved successor), F04 composition, the existing private Research Vault publisher and current authenticated Macro transport. Energy contributes domain-specific role/bridge adapters and first-source profiles. No Energy database, second graph, estimate warehouse, publisher, scheduler, ranker or trade engine.

**Reviewed design:** \`docs/superpowers/specs/2026-09-23-energy-economic-change-dossier-design.md\`, content commit \`33774cd8fb89ddcf156469dec60e90bfb0b2ef82\`, Git blob \`d6dac80bead5a028da8d757b419c896b1b8437ed\`.

**State:** Research/design implementation blueprint. Implementation starts from then-current Macro \`main\` on a fresh product carrier after the gates below; it does not convert PR #7791 into the implementation branch.

## 1. Frozen sources, authority and non-negotiable laws

- Research operation: \`gmi-energy-sector-research-20260923-sol-001\`; existing parent \`WS:GMI-THEME-GRAPH\`.
- Research/design carrier: draft/HOLD PR #7791, branch \`sol/energy-sector-research-20260923\`.
- Current design interface pin: \`macro@9438880952d3375b00a042381705c2e6c85305e3\`.
- Protected procedure: \`Mastermind@a7d2b3049e5cdc523e91e61a6e9d70a1cb911157\`, Skillpack v1.0.1/bootstrap 1.
- R1–R5 Energy research is DO_NOT_REDO. Use the durable checkpoint and exact research artifacts; Fable is the build principal, not the foundational researcher.
- No change to existing theme/basket membership or weight, ThemeState stage/recommendation, Theme Tracker lane, member ordering, Prophet admission/ranking, entry, sizing, alerts or trade origination.
- No shared membership → causal edge inference.
- No research facet → canonical theme promotion by implementation convenience.
- No guessed ticker/security identity.
- No private/full-fidelity current research in Git-tracked Theme Graph data, Pages, public R2, static HTML, source maps, analytics or browser persistent storage.
- No model arithmetic in browser. All numerical comparisons come from accepted deterministic owner code or render typed unavailable.
- No estimate surprise/revision without R5 definition/horizon/evidence-grade checks.
- No current “cheap,” “expensive,” “alpha,” target-price or stock-return claim from this plan.
- Green CI/merge is not production acceptance.

## 2. Current collision and shared-interface gates

These are execution prerequisites, not a new gate service.

| Gate | Current evidence | Required action before dependent write |
|---|---|---|
| G1 Theme Graph store custody | #7462 open/draft, touches \`engine/theme_graph/store.py\` | Reconcile exact current head/effect/source writer; consume accepted successor or wait. Never copy the store change to a rival PR |
| G2 shared curation assertion | Robotics #7773 proposes \`theme_graph.curation_assertion.v1\`; current main still lacks it | Existing GMI owner accepts one shared schema/store/subtype/private binding. Energy consumes exact accepted version |
| G3 shared Economic Change Dossier | Technology #7793 proposes common \`economic_change_dossier.v1\` and existing private publisher role | Consume accepted shared contract/publisher role or coordinate one common owner change; never create an Energy clone |
| G4 sector dossier | #7777 open with \`sector_dossier_read_model.v1\` contract, not on current main | Optional for first Nuclear vertical; consume after acceptance for sector-level Energy projection, never block theme vertical unnecessarily |
| G5 Theme Tracker public builder | #7664 open and touches \`scripts/build_state_of_themes.py\` | First release must not use this public builder as paid research data plane; reconcile only if a later public-shell change requires its output |
| G6 basket-detail template | #7669 open/draft, touches \`templates/basket_detail.html.j2\` | Reconcile exact accepted current template and live writer before edits |
| G7 company/paid route | Existing \`ticker.html.j2\`, private Earnings publisher and \`app/earnings.py\` exist | Recheck current writer/capability before modification; reuse accepted shared economic-change route/role when present |
| G8 source/right admission | R1–R5 are public-source research, not production ingestion licenses | Existing source/evidence owner admits only required fields and display rights; missing rights yields restricted/unavailable |
| G9 release | exact-head tests, independent review, normal CI, deploy, browser proof | No product-complete claim before real source-to-user proof |

A source or shared gate blocks only its dependent path. Pure adapters, schemas/tests under a currently free owner and fixture-only UI development can continue when genuinely path-disjoint.

## 3. First vertical source/identity scope

### 3.1 Theme and basket identity

Use accepted current identity:
- canonical theme: \`theme:nuclear_power\`;
- primary basket: \`nuclear_power\`;
- supplemental fuel basket: \`uranium_miners\`.

Never merge primary and supplemental membership into one denominator. The public shell may enumerate current accepted basket members because that membership is already public, but private economic research is fetched only through accepted authenticated projection.

### 3.2 First company/business witnesses

Use the smallest source-backed set that proves the economic distinctions:

1. **Cameco / CCJ** — supplemental fuel-supply role; Fuel Services realized price/cost scope, uranium production/procurement distinction, Westinghouse equity-method attribution.
2. **Centrus / LEU** — supplemental fuel/enrichment role; funded versus contingent backlog, definitive-but-conditional arrangements, current versus prospective capacity, financing instrument rights and closing.
3. **BWXT** — primary nuclear basket role; components/services economics, not plant-owner merchant generation.
4. **NuScale / SMR** — primary nuclear basket technology role; design approval is not site operating license/current generation.
5. **Oklo / OKLO** — primary nuclear basket development-stage role; test-reactor criticality is not Aurora commercial grid operation.

Before live admission, resolve each selected issuer/security/listing through the existing identity owner. If a research source cannot bind to an accepted security, render source attribution only and no stock/valuation enrichment.

### 3.3 Expectations state

The first Nuclear vertical may ship with \`expectations.status=UNAVAILABLE\` for a selected company when no admitted comparable estimate source exists. This is a valid complete state under ENE-63. Do not acquire or invent a consensus subscription merely to avoid an honest gap.

## 4. Proposed file map

Actual shared-file names from accepted predecessor contracts take precedence.

### Shared owner dependencies — consume, do not duplicate
- accepted \`contracts/theme_graph/curation_assertion.v1.schema.json\`;
- accepted curation codec/store/readers/Evidence Foundation subtype;
- accepted \`contracts/market_ontology/economic_change_dossier.v1.schema.json\` or successor;
- accepted private \`economic_changes\` projection role/version;
- accepted shared authenticated economic-change read route.

### Energy domain adapters
- Create \`engine/market_ontology/energy_economic_change.py\` — pure Energy mechanism/role adapter into the shared dossier; no source fetch, persistence, scoring or trading.
- Create \`tests/test_market_ontology_energy_economic_change.py\`.

### Selected source profiles
Under the existing Company/Earnings/source owner after G8:
- create or extend one owner-approved Energy/nuclear source profile module rather than a crawler; proposed path \`engine/company_intelligence/nuclear_value_profiles.py\`;
- create \`tests/test_company_nuclear_value_profiles.py\`;
- retained/private exact source bytes live only under the incumbent approved source owner, not this module or Git.

### Existing private projection
After G3/G7:
- extend the existing shared \`economic_changes\` role/provider only if not already generic enough;
- reuse existing \`engine/earnings_narrative/private_publication.py\`, \`scripts/publish_earnings_private_store.py\`, and \`app/earnings.py\`;
- create/extend focused shared-route tests, not a second Energy private publisher.

### Existing-page presentation
- create \`site/assets/js/energy-economic-change.js\` only if the accepted shared economic-change client is not already domain-generic;
- create \`site/assets/css/energy-economic-change.css\` only for Energy-specific visual semantics not covered by the shared client;
- add neutral public mounts/links to the accepted current \`templates/state_of_themes.html.j2\`, \`templates/basket_detail.html.j2\`, and \`templates/ticker.html.j2\` only after G6/G7;
- create \`tests/test_energy_economic_change_ui.py\`;
- create \`tests/test_energy_economic_change_non_regression.py\`.

Do not edit generated \`site/basket/nuclear_power.html\` or stock HTML directly.

## 5. Shared Energy input interface

Energy-specific Python dataclasses are implementation detail and must serialize into the accepted shared dossier. Proposed pure input roles:

\`\`\`python
@dataclass(frozen=True)
class EnergyRole:
    issuer_id: str
    business_label: str
    role_kind: str
    canonical_theme_id: str | None
    basket_relation: str | None  # primary_member / supplemental_member / none
    source_refs: tuple[str, ...]
    limitations: tuple[str, ...]

@dataclass(frozen=True)
class EconomicBridgeStep:
    step_kind: str  # demand, commercial_exposure, unit_economics, capital, ownership, shareholder_cash
    state: str      # observed, forward, unavailable, restricted
    value_ref: str | None
    narrative: str
    source_refs: tuple[str, ...]
    assumptions: tuple[str, ...]

@dataclass(frozen=True)
class ExpectationContext:
    state: str
    evidence_grade: str
    metric_definition: str | None
    fiscal_horizon: str | None
    aggregate_method: str | None
    contributor_count: int | None
    estimate_value: Decimal | None
    source_ref: str | None
    limitations: tuple[str, ...)
\`\`\`

The exact field names are proposed. The semantic requirements are binding; shared-owner naming wins.

Validation must fail closed for:
- non-finite numerics;
- incompatible units;
- unknown role enum;
- primary/supplemental relation inconsistent with accepted membership inputs;
- future milestone relabeled observed operation;
- source-less numerical claim;
- authority bit true;
- unresolved identity passed into valuation enrichment;
- surprise/revision without compatible R5 evidence.

## 6. Task 1 — Reconcile current owners and freeze one implementation carrier

**Outcome:** One exact current-main implementation carrier and one set of shared interfaces are authorized before effects.

- [ ] Re-pin protected Mastermind procedure.
- [ ] Read current Macro main and PR #7791 checkpoint; confirm research artifacts are DO_NOT_REDO.
- [ ] Refresh #7462, #7669, #7664, #7777, #7773, #7793 and any accepted successors only for relevant paths.
- [ ] Record whether the shared curation assertion and shared economic-change contract/private projection are accepted/live, accepted-but-unmerged, or still proposal.
- [ ] Resolve the exact current private publication owner and route. Do not infer an API from a sibling plan.
- [ ] Bind a fresh implementation operation and branch from then-current main through existing placement/source-custody law. Research PR #7791 remains HOLD/reference.
- [ ] Freeze exact first witnesses and identity/basket bindings.
- [ ] Record source/right admission state for each selected witness.
- [ ] Do not create a replacement store/route because one gate is unresolved.

**Proof:** immutable gate/identity/source receipt on the implementation carrier; no product code if the required owner is unresolved.

## 7. Task 2 — Consume the shared curation/evidence path

**Outcome:** Energy source-scoped roles can be represented through the one accepted GMI evidence owner.

If the shared curation assertion has landed:
- [ ] write tests using the actual accepted schema/version;
- [ ] validate one source-scoped role for Cameco and one primary-basket role for BWXT;
- [ ] prove source publication/observation/retention/review/business-valid clocks remain distinct;
- [ ] prove unresolved security identity does not gain a stock link;
- [ ] prove authority remains all false;
- [ ] prove no live research row is committed to public Git-tracked evidence storage.

If it has **not** landed:
- [ ] do not clone it;
- [ ] provide the exact Energy requirements ENE-04, 07–11, 22, 39–43, 56–62 to the shared GMI owner;
- [ ] continue Task 3 pure adapters with synthetic typed fixtures only;
- [ ] keep real admission blocked.

**Shared regression command after interface exists:**

\`\`\`bash
python -m pytest \
  tests/test_theme_graph_curation_assertion.py \
  tests/test_theme_graph_contracts.py \
  tests/test_evidence_foundation_contract.py \
  -q -p no:cacheprovider
\`\`\`

Use accepted successor test names if current main differs.

## 8. Task 3 — Implement the pure Energy mechanism adapter

**Files:** proposed \`engine/market_ontology/energy_economic_change.py\`, \`tests/test_market_ontology_energy_economic_change.py\`.

**Outcome:** Given already validated owner-native inputs, emit an Energy profile for the shared dossier without fetching sources, mutating graph state, calculating a score or changing decisions.

Tests first:
- [ ] nuclear primary member remains primary;
- [ ] uranium-miner/fuel member remains supplemental;
- [ ] multi-role company produces separate role records;
- [ ] unknown exposure remains null;
- [ ] Cameco Westinghouse equity-method sales cannot be added to consolidated revenue;
- [ ] Centrus contingent backlog remains contingent;
- [ ] NuScale design approval refuses \`operating_generation\`;
- [ ] Oklo test criticality refuses \`commercial_generation\`;
- [ ] BWXT components role does not inherit merchant-power economics;
- [ ] expectations unavailable emits typed unavailable, not zero;
- [ ] counterevidence remains adjacent to the favorable hypothesis;
- [ ] all authority bits false;
- [ ] no causal edge is persisted.

Proposed interface:

\`compose_energy_profile(selection, *, owner_inputs, as_of, knowledge_cutoff) -> SharedEconomicChangeDossier\`

No default \`datetime.now()\` inside the pure function. Caller supplies cutoffs from existing owner context.

**Focused command:**

\`\`\`bash
python -m pytest tests/test_market_ontology_energy_economic_change.py -q -p no:cacheprovider
\`\`\`

## 9. Task 4 — Admit and extract the first bounded Nuclear witnesses

**Owner:** existing source + Company/Earnings/financial owners, not Market Ontology.

### Cameco
- [ ] retain/resolve the correct Q2 2026 source used in R4, not the known misdirected web/Q1 link;
- [ ] admit only required Fuel Services measures and their definitions/period;
- [ ] preserve realized price versus unit cost scope;
- [ ] preserve uranium production/deliveries/procurement as distinct measures where used;
- [ ] preserve Westinghouse equity-method accounting and elimination treatment;
- [ ] source correction lineage includes the resolved R1/R4 link mismatch rather than hiding it.

### Centrus
- [ ] retain Q2/financing sources under existing owner;
- [ ] encode funded versus contingent backlog and conditional agreements without summing nested categories;
- [ ] preserve financing instrument type, pricing, actual close and future warrant exercise separately;
- [ ] no post-close available-cash amount is invented from gross offering size.

### BWXT / NuScale / Oklo
- [ ] admit source-scoped role/milestone evidence only;
- [ ] preserve exact milestone object;
- [ ] reject plant-output/earnings inference absent an operating asset/right;
- [ ] preserve source date and event/effective clocks.

**Source qualification tests:** exact selected facts/definitions, wrong-period sources, duplicate/syndicated copies, incompatible metric definitions, rights-restricted display and correction.

Fixtures contain only redistributable bounded data. Private/full source bodies never enter Git merely to make tests pass.

## 10. Task 5 — Compose the shared Economic Change Dossier

**Dependency:** Task 3 plus accepted shared dossier contract from G3.

The shared dossier for a selected issuer/theme must include the accepted equivalents of:
- scope and identity;
- one or more Energy roles;
- what changed;
- economic capture bridge;
- capital/financing;
- ownership/attribution;
- expectations/valuation context;
- counterevidence/falsifiers;
- coverage/freshness/conflicts;
- source/definition/version vector;
- safe navigation;
- all-false authority.

First unit bounds:
- max 5 selected companies in the Nuclear theme summary;
- max 12 role rows per request;
- max 40 material-change/evidence rows;
- max 80 relationship rows;
- no pagination in v1;
- oversize input refuses or requires narrower selection rather than silent truncation.

The composer does not:
- fetch a URL;
- open arbitrary filesystem paths;
- run an LLM;
- compute a stock rank;
- invent exposure weights;
- recalculate a second financial truth;
- mutate graph membership.

**Focused command:**

\`\`\`bash
python -m pytest \
  tests/test_market_ontology_energy_economic_change.py \
  <accepted-shared-economic-change-contract-tests> \
  -q -p no:cacheprovider
\`\`\`

## 11. Task 6 — Publish through the existing private owner

**Dependency:** accepted G3 private role/binding.

Prefer an already-landed generic \`economic_changes\` role in the existing private Research Vault publication family. If the role does not yet exist, the shared publication owner introduces it once; Energy does not create its own store, pointer or job.

Tests must prove:
- v1/backward compatibility where applicable;
- strict shared dossier schema;
- manifest object identity/digest;
- current source rights checked at request time;
- no public/static/Pages/R2 artifact contains full dossier;
- private staging outside repo;
- readback before pointer promotion;
- promotion conflict fails closed;
- old generation remains current after failed publish;
- rights revocation prevents display while preserving history;
- fake fixture provider cannot be selected in production.

A dossier is a derived projection, not the source of truth. Manifest rights metadata cannot override current source rights.

## 12. Task 7 — Serve one accepted shared private read

Prefer the accepted generic authenticated economic-change route. If Technology or another shared owner has already landed a route, Energy consumes it. Do not add \`/api/energy/*\` merely for branding.

Required behavior:
- entitlement enforced before provider access;
- selector resolves through native identity, not guessed ticker;
- optional theme context must validate against accepted local route/theme identity;
- success and expected errors carry \`Cache-Control: private, no-store\`, \`Vary: Authorization\`, \`X-Content-Type-Options: nosniff\`, \`X-Robots-Tag: noindex, noarchive\`;
- invalid selector/cutoff returns private 400;
- not-admitted selection returns private 404;
- private binding/integrity failure returns generic private 503;
- typed business-data refusal remains a valid dossier with null result/reason, not a store error;
- no request-controlled source URL, filesystem path, bucket key, metric formula, prompt or credential.

Route tests must prove free/anonymous user cannot cause private provider invocation.

## 13. Task 8 — Add existing-page Nuclear Value Capture UI

**Dependencies:** current accepted templates and shared API contract; reconcile #7669 before \`basket_detail.html.j2\`.

Theme Tracker:
- neutral compact Nuclear research entry only;
- no full paid payload in static HTML;
- do not change the existing recommendation/lifecycle/ranking card.

Nuclear detail:
- one Nuclear Value Capture mount on the current \`nuclear_power\` detail;
- explicit tabs/filter for core theme versus supplemental fuel supply;
- role matrix and value-capture bridge;
- contract/milestone timeline;
- expectations panel that renders typed unavailable honestly;
- counterevidence beside mechanism;
- source/clock/limitations drawer;
- accessible table equivalent to any relationship visualization.

Company dossier:
- additive “Energy Economics” link/mount only when an accepted dossier exists;
- preserve return navigation to the selected Nuclear context;
- no duplicate company route.

Browser client:
- reuse existing \`MDXAuth\`;
- fetch only after entitlement;
- \`cache:"no-store"\`;
- no paid payload in localStorage/IndexedDB/service-worker/analytics;
- ignore/abort stale in-flight results after logout/navigation/generation change;
- use escaped/textContent rendering;
- no financial arithmetic, dynamic script injection, eval or source-instruction execution.

UI tests:
- EN/ZH × dark/light × 1440/390 semantic parity;
- keyboard/focus;
- typed unavailable/restricted/conflict states;
- primary/supplemental distinction readable without color;
- no source bodies/URLs/values preloaded in public template beyond already-public membership/navigation;
- repeated initialization safe.

## 14. Task 9 — Freeze non-regression and privacy

Create \`tests/test_energy_economic_change_non_regression.py\`.

Freeze before/after:
- \`nuclear_power\` basket members/weights;
- \`uranium_miners\` basket members/weights;
- ThemeState recommendation/lifecycle/stage for affected themes;
- Theme Tracker lane/entry fields;
- member ordering/Prophet presence and existing entry fields;
- public page payload hashes/selected values excluding the intentional neutral shell/mount.

Fail if full private dossier/source assertion appears in:
- public \`site/state_of_themes.html\`;
- public \`site/basket/nuclear_power.html\`;
- public stock HTML;
- public \`site/**/*.json\`;
- source maps;
- tracked Theme Graph data rows in the implementation diff;
- browser persistent stores.

The schema/code can be public. Live full-fidelity research cannot.

## 15. Task 10 — Real source-to-browser Nuclear proof

No fixture substitution.

1. Admit the selected real source records through accepted owners.
2. Read back exact source/fact/assertion identities and generation.
3. Build one Cameco or Centrus dossier with the correct primary/supplemental relation.
4. Build one BWXT/core role.
5. Build at least one NuScale/Oklo typed refusal showing milestone ≠ operation.
6. Publish via existing private owner and read back immutable projection.
7. Serve through the accepted authenticated route.
8. Browser-prove Theme Tracker → Nuclear detail → selected company → source/limitations → existing stock/entry workflow.
9. Verify anonymous/free/public mirrors negative.
10. Verify expectations unavailable displays as unavailable, not zero.
11. Verify existing Nuclear theme/entry/basket outputs unchanged.
12. Run exact-head focused + impacted regression suites.
13. Obtain independent exact-head semantic/code review.
14. Pass normal CI/merge/release owner.
15. Repeat browser proof on deployed bytes.
16. Require a later real source update or rights-approved retained correction replay to prove publication/update liveness.

Completion remains nonterminal if any private/admission/identity gate is bypassed or if only fixture/browser-local evidence exists.

## 16. Task 11 — Expand using the same architecture, not another product

After Nuclear first vertical acceptance:
- Hydrocarbon Value Capture from R2;
- Power-Demand Value Capture from R3;
- Solar/wind manufacturer/developer/asset-owner cases from R4;
- Storage integrator/asset owner;
- Hydrogen/geothermal/renewable fuels/CCUS;
- global expectations/valuation from R5.

Sector-level Energy projection may consume #7777's accepted sector-dossier interface once live. The theme/company economic-change dossier remains the detail engine. Do not fork the architecture by subtheme.

## 17. Acceptance map

| Requirement band | Primary task(s) |
|---|---|
| ENE-01–07 owner/taxonomy/identity | Tasks 1–5 |
| ENE-08–26 economic semantics | Tasks 3–5, 10 |
| ENE-27–38 expectations/market/evaluation | Tasks 3, 5, 8, 10 |
| ENE-39–45 evidence/rights/privacy | Tasks 1, 2, 4, 6–10 |
| ENE-46–51 null/conflict/UI | Tasks 5, 7, 8, 10 |
| ENE-52–55 decision non-regression | Tasks 8–10 |
| ENE-56–63 Nuclear first vertical | Tasks 3–5, 8, 10 |
| ENE-64–66 bounds/model behavior | Tasks 3, 5, 7–10 |
| ENE-67–71 collisions/shared owners | Tasks 1–2, 5–8 |
| ENE-72–75 real-path acceptance/evaluation separation | Tasks 9–10 |
| ENE-76–78 orchestration/breadth | Tasks 1, 11, Fable packet |

No checkbox means the requirement has passed until its actual product proof is recorded.

## 18. Suggested focused test surface

Use exact current successors when names differ. After all first-vertical files exist, expected categories are:

\`\`\`bash
python -m pytest \
  tests/test_theme_graph_curation_assertion.py \
  tests/test_theme_graph_contracts.py \
  tests/test_evidence_foundation_contract.py \
  tests/test_company_nuclear_value_profiles.py \
  tests/test_market_ontology_energy_economic_change.py \
  <shared-economic-change-contract-tests> \
  <shared-private-economic-change-tests> \
  <shared-economic-change-api-tests> \
  tests/test_energy_economic_change_ui.py \
  tests/test_energy_economic_change_non_regression.py \
  tests/test_state_of_themes.py \
  tests/test_site_access_boundary.py \
  -q -p no:cacheprovider
git diff --check
\`\`\`

Do not predict a PASS count. Add only impacted incumbent tests discovered from actual imports/write paths and current CI registry.

## 19. Work sequencing and delegation

This is an implementation dependency sequence, not a replacement runtime DAG.

- Task 1 is Fable/principal-owned and runs first.
- Task 2 is shared-owner dependent; a bounded shared-contract worker may implement it only under accepted custody.
- Task 3 is a good bounded worker task after shared wire shape is frozen.
- Task 4 can be split by source/company only if each worker has non-overlapping source/profile files and a shared exact metric contract; Fable consumes/normalizes the returns.
- Task 5 is integration-critical and should stay with a senior bounded implementer plus Fable review.
- Tasks 6/7 can be handled by existing private-publisher/API specialists once the shared role is frozen.
- Task 8 can be a UI specialist after template custody is clear.
- Task 9 is independent adversarial/privacy/non-regression review.
- Task 10 is Fable-owned integration/acceptance with bounded test/browser assistance.
- Task 11 starts only after first vertical accepted.

**WHY FABLE:** remaining execution requires sustained cross-owner collision/privacy/interface adjudication and final end-to-end acceptance.  
**WHY NOT FABLE for routine work:** source adapters, pure calculators, isolated tests and UI implementation are bounded after interfaces freeze and should use the least-scarce capable avenue.

Never fan out multiple workers against \`store.py\`, shared publisher files or shared templates concurrently.

## 20. Fable handoff readiness

Before the final Fable packet is called execution-ready, it must contain current dispositions for G1–G9 and exact accepted versions of:
- shared curation assertion;
- shared economic-change dossier;
- private projection role;
- authenticated read route;
- selected source/identity bindings;
- current template owners.

Unknown gates remain exact dependencies. They do not invalidate path-disjoint pure work, and they do not authorize an Energy-specific substitute.

Fable must consume R1–R6 artifacts rather than re-research Energy. Research questions return to Sol only when a material implementation discovery falsifies or leaves unresolved a domain assumption not already answered by R1–R5.

## 21. Planning verification and effect boundary

This plan itself changes no production behavior. Planning verification must check:
- all 78 ENE requirements appear in the design;
- every requirement band maps to a task;
- first vertical uses existing \`theme:nuclear_power\`;
- primary/supplemental distinction is explicit;
- no Energy database/publisher/graph/ranker is proposed;
- current collisions #7462/#7669/#7664/#7777 are named;
- R5 expectation-evidence grammar is retained;
- shared sibling contracts are dependencies/proposals, not claimed live;
- real-path completion law includes privacy, browser and non-regression proof;
- no placeholders remain.

Only research/design/plan/continuity artifacts belong on PR #7791. Product code must use a fresh implementation carrier from then-current main.

The next principal action after verification is to prepare the cumulative R6 checkpoint and complete Fable CEO handoff packet, still without assigning a receiver until deliberate delivery/placement occurs.
