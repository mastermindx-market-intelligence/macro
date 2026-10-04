# Finance intelligence product experience and owner-preserving read/data contract — 23 September 2026

**Operation:** `gmi-finance-sector-research-20260923-sol-001`  
**Carrier:** Macro Draft/HOLD PR #7786, `sol/finance-sector-research-20260923`  
**State:** PRODUCT / DATA-CONTRACT DESIGN PROPOSAL / DRAFT-HOLD  
**Mission complete:** false  
**Authority:** design only. This document grants no product-code write, schema enrollment, source admission, graph write, route deployment, basket membership, rank, recommendation, entry, sizing, trade, merge, release or worker commission.

## 0. Source, interface and ownership boundary

- Protected procedure: `mastermindx-market-intelligence/Mastermind@bf764f494b9cd0ecede6234bb472c3344c8e77cc`, Skillpack 1.0.1/bootstrap major 1.
- Current Finance research predecessor head: `488dea268cd55672fa930ec96f56cd582691f000`.
- Original Finance research base: Macro `668237947e016f679782e41e61c91c9133a5ea99`.
- Latest read-only Macro interface pin checked during this design: `fc5c1fc49e4f552d8e3e55b5528a6d280d7415e8`.
- Current accepted architecture reference: `docs/superpowers/specs/2026-09-20-sector-theme-subtheme-intelligence-system-design.md`.
- Theme Tracker remains `state_of_themes.html`; its stable identifiers remain `state_of_themes` / `theme_lanes` and must not be renamed.
- Existing Financials sector route observed in product/tests: `sectors/XLF.html`.
- Existing Finance-related basket routes include `basket/us_sector_financials.html`, `basket/payments_fintech.html`, `basket/regional_banks.html` and `basket/insurance.html` where present.
- Final implementation paths, active carrier collisions and exact API placement must be refreshed immediately before product writes. This document does not claim the lifecycle state of currently open sibling PRs.

Canonical owners remain:

- security/issuer/listing identity: existing Data OS/GMI identity owners;
- canonical/local theme identity and evidence: GMI Theme Graph/ThemeState;
- sector/subsector/group observations: incumbent sector/group owners;
- company financial/event facts: company/earnings intelligence owners;
- analyst revisions and valuation: incumbent revision/valuation owners;
- rates/credit/macro: specialist owners;
- price/relative-strength/entry: accepted market/leadership/Prophet owners;
- publication/access: existing site/API/publisher owners;
- outcome learning: existing Evaluation OS/QLedger-compatible owners;
- product composition: accepted MarketOntology F04 / entity read-adapter direction.

This design creates no rival canonical store, graph, score, publisher, queue, scheduler, cache, watcher or evaluation ledger.

## 1. Outcome and 10/10 user job

A serious investor should be able to start from Theme Tracker, enter the Financials system, and answer:

1. What changed in the financial system or a Finance subtheme?
2. Which exact operating variables are improving or deteriorating?
3. How do those variables reach revenue, losses, capital, EPS, FCF, BVPS/TBVPS or NAV/share?
4. What did the market appear to expect?
5. Which valuation anchor is appropriate for this business model?
6. Why is the theme/company rerating, de-rating or failing to respond?
7. Is price leading, confirming or contradicting the fundamental/expectation path?
8. Which companies are direct exposures, diversified exposures, enablers, proxies or disrupted incumbents?
9. What evidence supports each statement, with dates, units, denominator and limitations?
10. What observable development would change the interpretation?

The machine job is to compose the relevant owner outputs at read time while preserving identity, clocks, nulls, rights, corrections, authority and disagreements.

Completion is not a taxonomy or passing schema test. It requires a real signed-in user to complete this journey with current production-path evidence, while an anonymous user cannot retrieve the current private payload through another mirror.

## 2. Alternatives and selected architecture

### 2.1 New standalone Finance microsite

**Rejected as the default.** It could show the research quickly but would create a parallel navigation, product and possibly publication plane beside Sector Intelligence, Theme Tracker, baskets and stock pages.

A later dedicated route may be justified only if the accepted cross-sector system view cannot fit the incumbent route architecture without harming other sectors. This design does not assume that exception.

### 2.2 Put the full Finance system inside `state_of_themes.html`

**Rejected.** Theme Tracker is a thesis-health/change router. A full company, valuation, system-flow, reserve, credit and evidence workbench would overload it, weaken mobile behavior and duplicate detail surfaces.

### 2.3 Mint one broad canonical `finance` theme

**Rejected.** Finance is a system/sector containing many business models, existing canonical themes, baskets and source-local concepts. Minting a universal theme would flatten rates, credit, payments, insurance, asset management and market infrastructure into a false lifecycle state.

### 2.4 Add an owner-preserving Finance system projection to the incumbent Financials sector journey

**Selected.**

```text
state_of_themes.html
  → system-research entry / connected Fintech & Payments theme
  → sectors/XLF.html Finance intelligence module
  → research slice / existing basket or subtheme detail
  → company/business exposure
  → exact evidence
  → return to existing stock/group/sector workflow
```

The existing `sectors/XLF.html` remains the primary command surface. It may show businesses outside the current XLF roster when they are system-enabling Finance exposures, but they must be visibly labeled `OUTSIDE_SECTOR_ROSTER` with relationship basis. The sector roster and system map remain distinct.

## 3. Theme Tracker integration

### 3.1 Broad Finance is a sector-system entry, not a theme-lifecycle card

Add a bounded **System Research** or accepted equivalent section/entry outside the canonical lifecycle ribbon. The Finance entry displays:

- `Financial System` / `Finance Sector` identity;
- current evidence horizon and coverage;
- one to three material changes from accepted owner observations;
- connected canonical themes, especially `fintech_payments`;
- connected sector/basket routes;
- current operating/expectation/valuation/price conflict summary;
- direct link to `sectors/XLF.html` with the Finance intelligence anchor.

It must say explicitly:

> Sector/system research — not a canonical theme stage or trade call.

### 3.2 Existing `fintech_payments` card

Retain its canonical theme identity, lifecycle and primary basket. Add an adjacent relationship/link such as:

```text
Part of the Financial System dossier
```

This link must not cause the broader Finance sector to inherit the `fintech_payments` stage or vice versa.

### 3.3 Existing Theme Tracker legs

The current global Theme Tracker includes a `bottleneck_tightness` asymmetry leg. Do not reinterpret that field as the primary Finance rerating model.

For Finance:

- global ThemeState/asymmetry dimensions retain their owner-native meaning where applicable;
- the sector-system entry exposes named Finance dimensions separately;
- no Finance-specific reinterpretation mutates the global leg contract;
- a future general architecture change to the global leg vocabulary requires its own owner acceptance.

### 3.4 Finance glance tier

Under a strict word budget:

```text
What changed
Why it matters economically
Where the four planes agree or conflict
Evidence freshness/coverage
```

Example structure, not current copy:

> Payment activity and recurring infrastructure revenue are improving, while regional-bank credit/funding evidence remains mixed. Valuation and price confirmation differ by subtheme. Research context only.

## 4. Financials sector/system dossier on `sectors/XLF.html`

### 4.1 Reading order

1. **Identity, scope and clocks**
2. **What changed**
3. **Four-plane current read**
4. **Rerating map**
5. **Internal Finance-system map**
6. **Subtheme and research-slice navigator**
7. **Company/business exposure matrix**
8. **Macro, regulation and structural-change context**
9. **Conflicts and missing evidence**
10. **Historical/outcome context**
11. **Watch conditions**
12. **Evidence drawer and route-back actions**

The Rerating Map precedes the optional Constraint/Access Map.

### 4.2 Identity and scope

Show separately:

- GICS/sector roster basis and sector ETF;
- equal-weight/cap-weight price surfaces where accepted;
- broader financial-system coverage beyond roster;
- connected canonical themes;
- connected source-local subthemes;
- current evidence/publication clocks;
- current-membership/non-PIT flags;
- authority limits.

### 4.3 What changed

Only owner-recorded material changes enter this tape:

- operating inflection;
- expectation/revision change;
- valuation change;
- price-recognition change;
- capital/risk event;
- subtheme leadership handoff;
- regulatory/structural stage change;
- freshness/coverage degradation or recovery;
- evidence correction/supersession.

Each change shows:

- dimension;
- previous/current state;
- business/subtheme scope;
- source and effective/publication time;
- plain-language consequence;
- whether it is descriptive, not predictive.

### 4.4 Four-plane current read

Separate cards/rows:

#### Operating economics

Owner-native dimensions such as:

- spread/funding/credit;
- volume/take rate/recurring mix;
- flows/fee yield;
- underwriting/reserves;
- margin/capital/per-share compounding.

#### Expectations

- revision direction and breadth;
- guidance/delivery gap;
- dispersion and contributor coverage;
- unavailable/rights-restricted state.

#### Valuation

- declared business-model anchor;
- current/normalized basis;
- own-history/peer context if accepted;
- required-return/rate context;
- no universal cheap/expensive label.

#### Price recognition

- accepted sector/subtheme/company trend and relative-strength dimensions;
- breadth/participation/concentration;
- entry/eligibility remains with incumbent owners;
- no browser-side recalculation.

### 4.5 Plain-language synthesis

Use typed conflict grammar from the accepted sector-theme architecture. Finance-specific examples:

- `OPERATING_UP_EXPECTATIONS_FLAT`
- `EXPECTATIONS_UP_VALUATION_COMPRESSES`
- `PRICE_LEADS_FUNDAMENTALS`
- `FUNDAMENTALS_UP_PRICE_DIVERGES`
- `EARNINGS_UP_PER_SHARE_BOOK_WEAK`
- `AUM_UP_ORGANIC_FLOWS_DOWN`
- `PREMIUM_UP_UNDERWRITING_DOWN`
- `ADOPTION_UP_MONETIZATION_UNPROVEN`

These are proposed display interpretations, not new canonical lifecycle states or signals.

## 5. Finance Rerating Map

### 5.1 Purpose

Explain how a subtheme/business reaches per-share value and what must change for a different multiple.

### 5.2 Required fields

```text
business_model
primary_per_share_anchor
primary_valuation_anchor
operating_driver_chain[]
risk_and_capital_offsets[]
expectation_path
valuation_context
price_recognition
catalysts[]
falsifiers[]
coverage/freshness
source_records[]
```

### 5.3 Visual grammar

Use a layered flow with synchronized accessible table:

```text
operating driver
→ financial statement / balance-sheet bridge
→ per-share anchor
→ expectation revision
→ valuation / required return
→ stock-price recognition
```

Line labels carry exact meaning. Color remains supplementary.

### 5.4 Examples

**Regional bank**

```text
deposit mix/cost + asset repricing + credit
→ NII/PPNR − provision
→ ROTCE and TBVPS
→ EPS/TBV estimates
→ P/TBV versus cost of equity
→ price/relative strength/breadth
```

**Payment network**

```text
volume + cross-border + transactions + services − incentives
→ revenue/margin/FCF
→ EPS/FCF/share
→ revisions
→ P/E/FCF required return
→ price recognition
```

**P&C insurer**

```text
rate/exposure − frequency/severity/cat/expense ± reserve development
+ investment income
→ operating earnings and BVPS
→ expectations
→ P/B/P/E versus normalized ROE
→ price recognition
```

## 6. Financial-system map

### 6.1 Three selectable maps

1. **Contractual money/risk flow**
2. **Regulated infrastructure/access**
3. **Public-equity business/economics**

Never blend them into one visually causal graph.

### 6.2 Node types

- system domain;
- workflow stage;
- business/source-scoped product;
- legal entity/issuer;
- security/listing;
- regulator/rail/venue/infrastructure;
- customer/counterparty class;
- research slice;
- canonical/local theme and basket reference.

### 6.3 Relationship types

Use the closed research relationship grammar proposed in the Finance foundation, subject to owner enrollment. Generic `PARTNERS_WITH` is insufficient when a precise role is known.

### 6.4 Evidence state

Every line shows one of:

- reported current relationship;
- source-reported capability;
- announced arrangement;
- system membership;
- regulatory status;
- derived view-time relationship;
- unresolved/held.

Operational dependency is not revenue materiality.

## 7. Subtheme/research-slice navigator

### 7.1 Families

- funding/deposits and banks;
- consumer/specialty/mortgage credit;
- private credit and alternatives;
- payments/money movement;
- exchanges/trading/clearing/custody;
- ratings/data/index/software;
- asset/wealth/retirement;
- insurance/reinsurance/brokers/data;
- structural disruption.

### 7.2 Slice states

- `SEMANTIC_ONLY`;
- `RESEARCH_EVIDENCE_AVAILABLE`;
- `MEASURABLE`;
- `PRICE_SURFACE_AVAILABLE`;
- `EVALUATION_CONTEXT_AVAILABLE`;
- `RIGHTS_RESTRICTED`;
- `STALE`;
- `HELD_FOR_REVIEW`.

These are product-coverage states, not theme lifecycle or trade states.

### 7.3 Direct versus proxy expression

Every priced slice declares:

- primary/direct basket if accepted;
- supplementary/proxy baskets;
- issuer/business exposure basis;
- outside-sector members;
- current-membership/PIT status;
- overlap and concentration.

## 8. Company/business exposure matrix

### 8.1 Rows

A row is a validated business/issuer/security binding or an explicitly source-only business observation. Diversified companies may have multiple business rows sharing one issuer/security.

### 8.2 Columns

```text
company / business
workflow role
principal / agency / fiduciary / utility / data / software mode
revenue mechanism
retained risks
funding / capital dependency
source-backed exposure and denominator
primary per-share anchor
valuation anchor
current four-plane conflict
research-slice memberships
identity/evidence health
```

### 8.3 Exposure roles

- `DIRECT_PURE_OR_HIGH_EXPOSURE`
- `DIRECT_DIVERSIFIED`
- `ENABLER_OR_TOLL_COLLECTOR`
- `SECOND_ORDER_BENEFICIARY`
- `PROXY_OR_ADJACENCY`
- `AT_RISK_OR_DISRUPTED`
- `HEDGE_OR_OFFSET`

These are descriptive basket/research roles, not weights or recommendations.

### 8.4 Comparison safety

The UI disables or warns on direct comparison when:

- metric populations differ;
- periods/clocks differ;
- gross/net or average/end bases differ;
- one issuer is mixed-business and another pure-play;
- identity or rights are unresolved;
- current versus point-in-time membership differs;
- valuation anchors are incompatible.

## 9. Structural Change module

Placed after the operating/rerating sections.

### 9.1 Stage ladder

```text
technical
legal permission
operational integration
production
adoption
monetization
earnings materiality
valuation recognition
```

### 9.2 Required view

- workflow before/after;
- incumbents/challengers/enablers;
- current stage and exact evidence;
- revenue/cost/capital/cannibalization bridge;
- legal/effective dates;
- adoption denominator;
- falsifiers;
- valuation optionality versus realized earnings.

## 10. Historical/outcome context

Consume accepted Evaluation OS outputs only.

Show:

- archetype and cohort;
- sample size/coverage;
- fundamental and market outcome separately;
- valuation/regime split;
- controls and limitations;
- no probability language unless calibrated and accepted;
- no ranking/trade authority.

When unavailable:

> Historical outcome context is not yet qualified for this state.

Do not synthesize an answer from unrelated episodes.

## 11. Watch conditions

Watch conditions are observable evidence requirements, not alerts to trade.

Each contains:

```text
condition
business/subtheme scope
why it matters
data/source owner
expected clock
current state
what change would support/challenge the interpretation
```

Examples:

- deposit cost and mix advance faster/slower than asset repricing;
- CAY ex-cat loss trend improves while reserve development remains stable;
- organic flows turn positive in higher-fee strategies;
- tokenized production activity repeats and reaches material revenue;
- price continues to lead without estimate confirmation.

## 12. Evidence drawer

### 12.1 Required content

- exact source/publisher/document;
- source locator;
- lawful excerpt/paraphrase;
- source publication, observation, period and business-effective clocks;
- native metric/relationship name;
- unit, population, denominator and basis;
- reported/derived/estimated state;
- limitations and what the source does not prove;
- identity and rights status;
- correction/supersession;
- owner/review/admission state;
- authority caps.

### 12.2 User behavior

- drawer is pinned and linkable inside authenticated state;
- deep links preserve selected section/slice/company and return route;
- no current private response persists in localStorage or IndexedDB;
- use lawful short excerpts/original paraphrase rather than copied reports.

## 13. Page-specific read projection

### 13.1 Selected composition model

A deterministic, side-effect-free Finance view composer consumes exact accepted owner outputs. It emits a page/read response but does not become canonical state.

Conceptual flow:

```text
accepted owner artifacts / readers
→ exact source manifest and generation checks
→ identity and clock validation
→ owner-preserving Finance adapter
→ page-specific view projection
→ schema validation
→ authenticated response
```

### 13.2 Inputs

Applicable accepted subsets of:

- `sector_intelligence_packet.v1`;
- `theme_intelligence.consumer.v1`;
- ThemeState and Theme Graph latest-belief readers;
- group/member observations and leadership;
- company/earnings facts;
- revisions and valuation observations;
- macro/rates/credit context;
- accepted Finance curation assertions;
- market/price/entry owner reads;
- evaluation/outcome context.

An unavailable input produces typed degradation, not invented synthesis.

### 13.3 Output proposal

```text
finance_system_dossier.view.v0_1

snapshot_identity
source_manifest
identity
scope
relationships
material_changes[]
current_dimensions[]
rerating_maps[]
system_views[]
research_slices[]
company_business_rows[]
macro_and_regulatory_context[]
structural_changes[]
conflicts[]
watch_conditions[]
outcome_context
source_records[]
coverage_quality
freshness
authority_caps
```

This is a design name, not an enrolled contract.

### 13.4 Snapshot identity

Derived deterministically from:

- exact input owner identities/generations/content hashes;
- composer version;
- accepted curation revision set;
- rights/access profile;
- requested view/scope.

Do not derive identity from current time or mutable file modification time.

### 13.5 Authority caps

Every response explicitly sets applicable capabilities, expected all false for decision authority:

```text
may_rank: false
may_gate: false
may_size: false
may_trade: false
may_create_theme: false
may_change_membership: false
may_write_graph: false
may_admit_source: false
```

## 14. Finance source assertion projection

### 14.1 Native evidence extension

Reuse the existing GMI evidence-owner extension pattern proposed by the Robotics reference vertical. Finance source assertions add domain sections rather than create a Finance fact database.

Proposed Finance fields inside an accepted versioned curation assertion:

```text
finance_scope:
  system_domain
  workflow
  workflow_stage
  business_role
  revenue_mechanism
  risk_carrier
  funding_capital_dependency
  regulatory_perimeter

finance_measurement:
  native_metric
  normalized_family
  value/unit/currency
  stock_flow_rate_count
  average_end
  gross_net_notional
  numerator/denominator
  organic_acquired_market_fx
  reported_derived_estimated

finance_rerating_context:
  primary_per_share_anchor
  primary_valuation_anchor
  operating_bridge
  limitation
```

The closed native assertion type vocabulary remains proposal-only until the existing evidence schema/store/reader/admission path is extended and round-trip tested.

### 14.2 No global business/product master in the first vertical

Source-scoped business/product/workflow labels remain inside reviewed assertions until the canonical identity owner supports stronger first-class identity. Validated issuer/security links use existing identity-resolution rows.

## 15. Transport and access

### 15.1 Static shell plus authenticated current payload

- existing served pages may carry an anonymous/public shell and deliberately approved static copy;
- current full-fidelity Finance research is fetched through one existing Macro authenticated read path;
- use the established `require_user → enforce_site_full(always=True)` pattern;
- private/no-store, Vary, noindex and nosniff protections apply to success and errors;
- no current response in public `site/**`, public Git/Pages, public R2, source maps, service workers, localStorage or IndexedDB.

### 15.2 Proposed route

Preferred conceptual route:

```text
GET /api/sectors/XLF/finance-intelligence/v1
```

The exact final route/module requires incumbent API and collision reconciliation. A different adjacent route is acceptable if it preserves the same owner/access contract. Do not create a new server or transport.

### 15.3 Request behavior

Allowed bounded filters:

- research slice;
- system view;
- company/business;
- horizon;
- source/evidence drawer selector.

Reject arbitrary query execution, browser-time web crawling, model-authored graph queries and state-changing requests.

### 15.4 Caching

Prefer request-time pure composition from retained owner outputs. Any in-process cache must be:

- tenant-neutral where appropriate;
- keyed by full source manifest/snapshot identity;
- invalidated by source change;
- non-durable;
- not a second truth store;
- private/no-store at the client boundary.

## 16. Null, stale, conflict and error behavior

### 16.1 Null states

- `NOT_DISCLOSED`
- `NOT_APPLICABLE`
- `SOURCE_UNAVAILABLE`
- `RIGHTS_RESTRICTED`
- `IDENTITY_UNRESOLVED`
- `PERIOD_OR_BASIS_MISMATCH`
- `NOT_YET_MEASURABLE`
- `HELD_FOR_REVIEW`

### 16.2 Freshness

Each dimension carries its owner’s freshness/clock. The page-level time is a response-generation time, not a statement that all evidence is current.

### 16.3 Conflicts

Use accepted conflict classes plus Finance-specific explanation. Do not average away contradictory owner reads.

### 16.4 Source refusal

When a required cross-owner identity or clock bridge is absent, refuse the combined panel while allowing independently valid panels to render with clear separation.

### 16.5 Access/errors

Access failures and validation failures return the same protective headers as success. Do not leak current identifiers, source snippets or entitlement detail through error messages.

## 17. First production vertical

The selected first vertical remains:

# Financial Rails & Market Infrastructure

Facets:

1. **Money Movement**
2. **Securities Infrastructure**

### 17.1 First user journey

```text
Theme Tracker
→ Financial System entry
→ sectors/XLF.html#finance-intelligence
→ choose Money Movement or Securities Infrastructure
→ inspect workflow and company/business rows
→ open rerating map
→ compare operating / expectations / valuation / price
→ inspect exact evidence
→ return to basket/stock/sector workflow
```

### 17.2 Initial company/business set

Use only source-qualified, identity-resolved records. Research candidates include:

- Visa;
- Mastercard;
- CME;
- ICE;
- Nasdaq;
- Fiserv;
- FIS;
- BNY;
- State Street;
- S&P Global;
- Moody’s.

Candidate status does not pre-authorize production admission.

### 17.3 Initial required measures

- branded/processed/switched/settled transactions;
- payment/transaction value and cross-border;
- incentives/rebates/take rate;
- exchange ADV/open interest/RPC;
- recurring data/software/ARR;
- clearing/collateral/custody/AUC/A;
- ratings/index-linked assets;
- EPS/FCF and correct valuation anchors;
- source, clocks and limitations.

## 18. First-vertical acceptance

A signed-in user can, using real current production-path data:

1. distinguish issuer, acquirer, gateway, processor and network;
2. distinguish venue, broker/dealer, CCP/clearing agency, settlement/CSD, custodian, data and ratings roles;
3. see exactly how a key operating variable reaches revenue, margin, EPS/FCF and valuation;
4. see who retains credit, liquidity, inventory, counterparty, operational or regulatory risk;
5. distinguish recurring from transaction revenue;
6. distinguish adoption/volume from monetization;
7. inspect current expectation, valuation and price conflict without a fused score;
8. open the exact source and limitation;
9. navigate to existing stock/basket/sector context;
10. encounter honest null/degraded states when evidence is absent.

Anonymous users cannot retrieve the current full-fidelity response through primary or alternate paths.

## 19. Product tests and proof

### 19.1 Contract and semantics

- schema closedness;
- legacy evidence compatibility;
- round-trip persistence of optional Finance assertion;
- unknown/null distinction;
- native metric retained;
- gross/net/stock/flow/average/end enforcement;
- identity/source scope;
- correction/supersession;
- authority caps.

### 19.2 Composition

- exact source manifest;
- deterministic snapshot identity;
- owner-specific freshness;
- mixed-clock handling;
- conflict classification;
- unavailable owner input;
- no owner recalculation in browser;
- no duplicate graph/publisher/store.

### 19.3 Access and privacy

- signed-in Full allowed;
- Free/anonymous denial as required;
- private/no-store/Vary/noindex/nosniff on success and errors;
- zero current payload in static artifacts, source maps, service worker, local storage, alternate mirrors and evidence fixtures;
- deep-link behavior without private persistence.

### 19.4 UI behavior

Browser evidence matrix:

```text
desktop + mobile
EN + ZH
dark + light
rest + selected slice + evidence drawer + degraded state
keyboard + screen-reader semantics
reduced motion
```

No hover-only meaning. Tables provide accessible equivalents to maps.

### 19.5 Real-path proof

- real current owner inputs;
- visible response on deployed authenticated path;
- one full user journey from Theme Tracker to evidence and back;
- one honest missing/rights/identity-degraded journey;
- exact release/source identity;
- production access denial through alternate mirror;
- no claim of acceptance from CI alone.

## 20. Ordered implementation slices — design only

### V0 — interface and owner reconciliation

Refresh current main, active carriers, paths, contracts, access/publication and source rights. Resolve whether the generic curation assertion extension is accepted and who owns the Finance subtype.

### V1 — evidence and read contract

Extend existing native evidence/store/reader path if accepted; implement pure Finance view adapter with fixtures and no UI.

### V2 — first useful vertical

Money Movement + Securities Infrastructure on the real `state_of_themes → XLF → detail → evidence` journey.

### V3 — balance-sheet and credit

Banks, cards, auto, mortgage, private-credit managers and BDC vehicles with seven-clock models.

### V4 — asset/wealth/insurance

Flows/fees, wealth/cash, underwriting/reserves, life/spread/capital, brokers/data.

### V5 — structural change

Stablecoins, tokenization, instant payments, open banking, AI, private markets and core modernization with stage ladder.

### V6 — historical/outcome context

Only after accepted point-in-time evaluation outputs exist.

### V7 — full breadth, hardening and production acceptance

Expand research slices, international coverage, source rights, negative/degraded proof, learning and documentation.

Every slice must deliver a named user capability. Infrastructure-only PRs do not count as product completion.

## 21. Collision and custody law

Before any implementation wave:

- refresh exact heads/diffs/owners for Theme Tracker, sector pages, Theme Graph evidence/store/identity, F04/entity adapter, authenticated API, access/entitlement, publication and evaluation;
- identify incumbent writer per path/interface;
- consume accepted contracts only;
- keep one modifying operation on one carrier;
- no blind rebase/merge or takeover;
- no second store, graph, queue, publisher, source admission or outcome ledger;
- research PR #7786 remains records-only until a separately accepted implementation plan and commission.

## 22. Fable and worker decomposition boundary

Fable CEO is reserved for:

- current-main architecture/collision adjudication;
- cross-owner interface and source-right decisions;
- implementation wave orchestration;
- difficult integration/review/acceptance;
- release and production proof under granted authority.

Lower-scarcity bounded avenues should later handle, after contracts freeze:

- primary-source transcription under fixed schemas;
- fixture generation;
- contract/store/reader mechanical implementation;
- bounded UI modules;
- tests and browser evidence;
- source coverage audits;
- routine repair.

This document is not yet the final Fable handoff.

## 23. Explicit non-claims

This design does not establish:

- accepted implementation paths or API route;
- enrolled schemas;
- admitted Finance source assertions;
- current company valuations or consensus;
- accepted basket memberships;
- completed historical evaluation;
- code, tests, CI, deployment or browser proof;
- Fable delivery, ACK, START or execution.

## 24. Exact next action

Run the whole-program research and collision gap review against the required final handoff contents. Close remaining intellectual gaps—especially source rights, exact first-vertical assertions, international coverage, valuation/expectation joins and implementation acceptance—before drafting the final Fable CEO master handoff.
