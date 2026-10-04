# Energy Economic Change Dossiers
## Owner-composed sector/theme intelligence and first Nuclear Value Capture vertical

**Written design proposal — revision 1 — 23 September 2026**

CAPABILITY_STATE: SPEC_ONLY  
MISSION_COMPLETE: false  
DESIGN_REVIEW: REQUIRED  
IMPLEMENTATION_STARTED: false

Operation: \`gmi-energy-sector-research-20260923-sol-001\`. Existing parent: \`WS:GMI-THEME-GRAPH\`. Carrier: Macro draft/HOLD PR #7791, branch \`sol/energy-sector-research-20260923\`. This branch remains research/design only. No Fable receiver, implementation writer, runtime Attempt, release or trade authority is created by this document.

## 1. Decision and intended outcome

Select **owner-composed Economic Change Dossiers inside the existing sector → theme → company workflow**, with Energy-specific economic mechanisms rather than a Robotics-style bill of materials.

The investor job is not simply to find Energy stocks or see a supply-chain diagram. The product must answer, with evidence:

1. What economic development is changing?
2. Which business has the contractual or operating right to capture it?
3. Through what price, volume, fee, spread, rate-base, order, utilization or ownership mechanism does it reach earnings?
4. What capital, working capital, financing, dilution, commissioning or replacement burden must be funded first?
5. How much of the result is attributable to existing common shareholders?
6. What was already expected, using only evidence available at the relevant time?
7. What contrary evidence or missing information would weaken the apparent beneficiary thesis?
8. What does the incumbent Theme/entry/stock workflow say, without allowing this research layer to override it?

The machine job is to preserve these meanings across source revisions, accounting definitions, contract vintages, ownership structures, geographic regimes and expectation vintages without inventing a second graph, estimate warehouse, identity plane, publisher, ranker or trading system.

### 1.1 Selected delivery strategy: bounded B with foundations for later C

**A — editorial Energy research only.** Useful but insufficient. It leaves the investor to reconcile contracts, cash attribution and expectations manually.

**B — owner-composed Economic Change Dossiers. SELECTED.** Existing GMI, Company/Earnings, financial, source, identity, market, rights, publication and entry owners retain truth. Energy adds domain profiles and a bounded read model over accepted owner-native evidence.

**C — universal first-class global economic network. NOT first release.** A global graph of assets, contracts, products, commodities and causal transmission would be powerful, but it would force identity, rights and persistence decisions before a useful release. R6 preserves typed source-scoped relationships and explicit predicates so accepted owners can later promote richer identities and cross-theme transmission without migration from a hidden Energy database.

The first production vertical is **Nuclear Value Capture**. It uses the existing canonical \`theme:nuclear_power\`, primary basket \`nuclear_power\`, and explicitly supplemental \`uranium_miners\` basket. It demonstrates multiple economic archetypes without pretending they share one valuation model: operating generation, nuclear components/services, resource/fuel supply, enrichment/capacity expansion, and development-stage reactor technology.

The next expansion is **Power-Demand Value Capture** across \`data_center_power\`, \`grid_electrification\`, the Energy sector and connected Utilities/Industrials businesses. It reuses the same dossier grammar rather than launching a separate product.

## 2. Canonical source and compatibility frontier

Protected procedure pin: \`mastermindx-market-intelligence/Mastermind@a7d2b3049e5cdc523e91e61a6e9d70a1cb911157\`, Skillpack \`mastermind.sol_skillpack.v1\` v1.0.1/bootstrap 1. INDEX, COLD_START, ACTIVE_EXECUTION, WEB_CEO_DELEGATION, RECONCILE_STATE and CLOSEOUT were consumed from that revision. Direct planning reason: PRINCIPAL_JUDGMENT.

Energy research carrier head before this design write: \`f63bd432ecca279ea129e3b95802ff1760973537\`. Current Macro interface pin for design: \`9438880952d3375b00a042381705c2e6c85305e3\`. Neither pin is deployed-product proof.

Current owner/interface receipts:

| Current interface | Git blob | Design consequence |
|---|---|---|
| \`config/theme_crosswalk.yml\` | \`782dbc519b7bb2d446af91c66c6fb9248722a8b9\` | Canonical theme identity and primary/supplemental basket semantics stay with GMI |
| \`data/baskets/membership.json\` | \`c5b838d59fad8115d40cd369410846e9aaf5ec11\` | Existing membership is descriptive and unchanged by Energy research |
| \`templates/state_of_themes.html.j2\` | \`05017554bb9e64951d195b52583cfbd462bd2f05\` | Existing Theme Tracker shell remains the entry surface |
| \`templates/basket_detail.html.j2\` | \`a3d8846bd27961db2c7877d693e8fd43bf399baa\` | Existing theme detail remains the primary depth surface |
| \`templates/ticker.html.j2\` | \`14276ab2d09a6402e62a8f2fbb86f7c62689e3ec\` | Company-first navigation reuses the incumbent dossier |
| \`contracts/theme_graph/evidence.v1.schema.json\` | \`83dece15e98b9c8775a584afcd6ee09811dad220\` | Current evidence row does not yet contain the richer shared assertion body |
| \`engine/theme_graph/store.py\` | \`63b58860d35bd183c947c85088f83bd53359bb9f\` | Preserve the one Theme Graph writer/store |
| \`contracts/evidence_foundation/vocabulary.v1.json\` | \`441c573dff1f04fca42ffe3d3170eb035e1b17a2\` | K1/reference vocabulary remains existing owner territory |
| \`engine/earnings_narrative/private_publication.py\` | \`0ee93909693893f419f0109f9eba1994d94e2b46\` | Existing private staged publication is the preferred projection carrier if its owner accepts the new role |
| \`app/earnings.py\` | \`3b8251388c8e9ae59b933212a7384faaea61eb27\` | Existing authenticated \`site_full\` transport and private headers are the preferred member-read precedent |
| \`contracts/sector_intelligence/sector_intelligence_packet.v1.schema.json\` | \`de386d5bd4796280f08601804870a9aabb458c60\` | Sector-level federation remains an existing owner; Energy does not replace it |

Important sibling/current carriers:
- #7462 is open/draft and touches \`engine/theme_graph/store.py\`.
- #7664 is open and touches \`scripts/build_state_of_themes.py\`; this design intentionally avoids publishing paid Energy bodies through that public builder.
- #7669 is open/draft and touches \`templates/basket_detail.html.j2\`.
- #7777 is open and introduces the shared \`sector_dossier_read_model.v1\` contract; that contract is not yet on current main.
- Robotics #7773 remains open/draft and proposes one shared optional \`theme_graph.curation_assertion.v1\` path. It is specification/plan evidence, not live capability.
- Technology #7793 proposes a cross-domain \`economic_change_dossier.v1\` direction and existing-private-publisher integration. Energy should converge on an accepted shared version rather than mint an Energy variant.
- Healthcare #7788 independently reaches the same conclusion: reuse one native assertion/evidence path and one paid composition path instead of a domain database.

Any accepted newer shared owner/interface supersedes the exact proposed wire names below. The economic semantics and acceptance requirements remain the Energy contribution.

## 3. Existing Energy identities versus research facets

### 3.1 Existing canonical/theme surfaces

At the design pin, relevant accepted crosswalk entries include:

- \`theme:nuclear_power\` — primary basket \`nuclear_power\`; supplemental \`uranium_miners\`; source-local rotation parent \`Energy Renewable\`.
- \`theme:grid_electrification\` — primary basket \`power_grid\`; source-local rotation parent \`Energy Renewable\`.
- \`theme:solar\` — no primary US basket; source-local rotation parent \`Energy Renewable\`; CN mapping exists.
- \`theme:data_center_power\` — primary basket \`data_center_power\`; \`ai_neoclouds\` is a supplemental demand-driver surface.

The broad \`energy_complex\` basket exists but is explicitly not a canonical theme in the crosswalk. It must not be promoted into a canonical theme merely because it is convenient.

The existing crosswalk itself says \`Energy Renewable\` is only the closest source-local parent for nuclear/grid/solar where a more precise subsector is absent. That is a **crosswalk limitation, not economic equivalence**.

### 3.2 Research-only Energy mechanism families

The following are research facets until the existing GMI owner accepts an identity or mapping. They are not automatically new theme nodes, baskets or ThemeState records:

1. upstream oil/resource production;
2. natural-gas production and basis exposure;
3. gathering/processing/NGL;
4. pipelines and reserved-capacity infrastructure;
5. LNG liquefaction and marketing;
6. refining/conversion;
7. oilfield services;
8. energy equipment and long-cycle manufacturing;
9. merchant generation and retail;
10. regulated utility investment/recovery;
11. contracted generation/asset ownership;
12. nuclear resource and procurement;
13. nuclear conversion/enrichment/fuel services;
14. nuclear components/services;
15. nuclear reactor technology/development;
16. solar manufacturing;
17. solar/wind development and capital recycling;
18. renewable/contracted asset ownership;
19. storage integration;
20. storage asset operation;
21. grid/electrical equipment;
22. EPC/construction;
23. geothermal;
24. renewable fuels;
25. hydrogen/fuel cells;
26. carbon capture/transport/storage;
27. waste-to-energy and other transition mechanisms where materially distinct.

A company can carry multiple roles. Revenue exposure, gross-profit exposure, operational dependence, narrative relevance, theme membership, historical price association and basket weight are separate concepts. Unknown exposure stays unknown.

## 4. Product ontology: five axes that must not collapse

Every Energy dossier keeps these axes separately:

**Structural identity** — sector/subsector/group from existing structural owners.

**Canonical thematic identity** — accepted GMI theme/local-theme/basket relations.

**Source-scoped economic role** — what the business or asset actually does in the cited scope.

**Economic mechanism** — price/volume/spread/fee/rate-base/order/service/resource/capacity/contract/ownership mechanism that can change attributable economics.

**Security context** — exact issuer/security/listing, market/valuation/entry state and point-in-time expectation evidence from their native owners.

The first four can be informative without the fifth. A source-only company record may display attributed research but receives no guessed ticker, price, valuation or stock link.

## 5. Energy Economic Change Dossier semantics

Energy consumes the accepted shared \`economic_change_dossier.v1\` or its owner-approved successor. Do **not** create \`energy_economic_change_dossier.v1\` as a rival contract.

The bounded dossier needs the following semantic sections. Wire names are proposed until the shared owner accepts them.

### 5.1 Scope and identity

- native sector/theme/basket references;
- research facet label with explicit authority/source;
- issuer/security/listing binding or typed unresolved state;
- business/asset/product/configuration source scope;
- geography and currency where material.

### 5.2 What changed

Each accepted material change preserves:
- source event/fact identity;
- publication, observation, business-valid, retention, review and system-record clocks;
- metric or contract definition;
- current/forward/historical status;
- correction/supersession lineage;
- evidence grade and rights state.

### 5.3 Economic capture bridge

The standard Energy bridge is:

\`demand/market change → commercial exposure → unit economics → operating contribution → required capital/financing → ownership/claims → attributable cash per continuing share\`

Not every business uses every step. Missing steps remain unavailable rather than being guessed.

Examples of owner-bound mechanisms:
- producer: realized product prices, basis, volume, hedges/contracts, decline/replacement capital;
- refiner: product-feedstock conversion margin, utilization, outages, compliance/operating cost;
- pipeline/LNG: reserved capacity, throughput, minimum payments, renewal, project capex, marketing exposure;
- regulated utility: approved eligible capital, recovery timing, allowed/earned returns, financing and share count;
- merchant generator: regional power/fuel exposure, hedge vintage, availability, capacity/retail/customer obligations;
- equipment supplier: binding order, cost-to-complete, production/delivery, working capital/advances, service attachment;
- nuclear fuel: realized contract margin, procurement/inventory, expansion commissioning, ownership;
- developer: project development/construction economics, asset sale/recycling and retained ownership;
- storage owner: contracted/merchant dispatch economics, losses, degradation, competition and financing.

### 5.4 Capital and ownership

Always distinguish:
- operating business versus parent;
- consolidated versus proportionate versus common-shareholder claims;
- cash investment versus contributed assets and foregone cash;
- project finance versus corporate debt;
- common shares versus convertibles/warrants/pre-funded instruments;
- repurchase authorization versus actual retired shares;
- customer advances versus earned profit;
- sale proceeds versus future cash from the interest sold.

### 5.5 Expectations and valuation context

R5 freezes evidence grades rather than pretending every consensus source is equally historical:
- \`PRE_EVENT_TIMESTAMPED_VALUE\`;
- \`ISSUER_PROCESS_PLUS_ARCHIVE\`;
- \`ARCHIVAL_CONTEXT_ONLY\`;
- \`POST_EVENT_ONLY\`;
- \`UNAVAILABLE\`.

A surprise/revision is computed only after metric, unit, fiscal horizon, ownership/per-share basis and evidence-time checks pass. Contributor count and aggregation method travel with every aggregate. Panel changes do not become within-analyst revisions. Forecast-year rollover is not an estimate revision.

Market context preserves raw/total-return/benchmark-residual/external-reported distinctions. Stock-minus-index is descriptive, not alpha. Commodity changes are contextual unless a predeclared calibrated exposure model exists.

### 5.6 Counterevidence and falsifiers

Every favorable interpretation has at least one explicit countercase or missing requirement, for example:
- demand forecast revised lower;
- realized price improves while cost rises faster;
- backlog is contingent/unfunded;
- contracted MW are existing output, not new supply;
- margin improvement is a temporary credit/refund/accounting item;
- guidance improvement is purchased through acquisition/dilution;
- cost reduction is competed away into lower selling prices;
- technical milestone belongs to a test asset, not commercial operation;
- improved contract duration requires materially more capital;
- public information was already available before the result.

Counterevidence is first-class display material, not hidden below a positive headline.

## 6. First vertical: Nuclear Value Capture

### 6.1 Why Nuclear is the first Energy proof

Nuclear is the highest-leverage first vertical because it already has:
- an accepted canonical theme \`nuclear_power\`;
- a direct primary basket \`nuclear_power\`;
- an explicitly supplemental fuel basket \`uranium_miners\`;
- existing real-page route \`basket/nuclear_power.html\`;
- materially different company economics in the researched set;
- concrete positive and refusal cases;
- enough source evidence to prove that a thematic narrative cannot be mapped to one generic earnings model.

The first vertical does **not** require every nuclear company to be fully populated.

### 6.2 Core research facets inside the vertical

Display these as reviewed research facets, not new canonical theme nodes unless GMI separately accepts them:

- operating generation / contracted power;
- nuclear components and lifecycle services;
- uranium/resource production and procurement;
- conversion/enrichment/fuel services;
- reactor technology/licensing;
- development-stage generation;
- capital/financing and milestone risk.

### 6.3 First real witnesses

**Cameco / fuel economics**  
Show the source-scoped Q2 Fuel Services realized-price and unit-cost observation, the derived price-minus-cost comparison with its limitations, procurement/production distinction and Westinghouse equity-method attribution. It must not treat Westinghouse sales as additive consolidated revenue or turn spot uranium into all contract realization.

**Centrus / conditional capacity and financing**  
Show funded versus contingent backlog, definitive-but-conditional agreements, current versus prospective capacity, financing instrument rights and actual closing separately. It must not call contingent backlog current revenue or future warrant exercise present cash.

**BWXT / components and services**  
Show a source-backed nuclear component/service role and disclosed operating observations when admitted. Do not apply a reactor-owner power multiple to a supplier merely because both belong to nuclear.

**NuScale / technology milestone refusal**  
NRC standard design approval is a technology/regulatory milestone, not an operating plant or site license. Conventional light-water fuel scope must not inherit a universal HALEU requirement.

**Oklo / test-versus-commercial refusal**  
Groves test-reactor criticality is not Aurora commercial grid operation. Development-stage milestone progress can reduce uncertainty without becoming current electricity revenue.

### 6.4 Primary versus supplemental basket law

The existing \`nuclear_power\` primary basket and \`uranium_miners\` supplemental basket remain distinct. Fuel-supply membership supports a **connected supply exposure** view; it does not silently declare every uranium-miner constituent a member of the direct \`nuclear_power\` primary basket.

The first view may show both populations with explicit relationship basis and accessible table labels. It may not add them together as one denominator or infer weights from basket membership.

## 7. Second vertical foundation: Power-Demand Value Capture

After the Nuclear release proves the common contract, reuse it for:
- \`data_center_power\`;
- \`grid_electrification\`;
- connected Energy, Utilities and Industrials businesses.

This view compares a common demand development across gas producer, midstream infrastructure, merchant/contracted generator, regulated utility, equipment supplier and EPC contractor. It does not rewrite their GICS sector.

The R3 research supplies the core distinctions: forecast level versus revision versus actual load; hedge vintage; retail and capacity obligations; utility recovery/financing; orders versus RPO/backlog; customer advances; commissioning; construction cost recovery; and attributable cash.

This expansion is the beginning of the later richer cross-theme economic network. It remains a read-time composition, not a new causal graph.

## 8. User experience and visual design

### 8.1 Theme-first journey

\`Theme Tracker → Nuclear & SMR Power → Nuclear Value Capture → research facet → company/business/asset → economic bridge → evidence/counterevidence → expectations/valuation context → existing stock/entry workflow\`.

Theme Tracker remains compact. It gains at most a neutral research-depth/change link or summary for an accepted theme; detailed economics belong on the existing theme detail surface.

### 8.2 Company-first journey

\`Stock/company dossier → Energy Economics → applicable theme/facet roles → economic bridge → source/expectation receipts → back to selected theme\`.

A mixed company shows several source-backed roles rather than one “Energy exposure” percentage.

### 8.3 Required visualizations

Use visuals only when they answer a financial question:

1. **Value Capture Bridge** — labeled stages from demand/contract through shareholder cash; no invented numeric widths.
2. **Company × Economic Role Matrix** — role, theme/facet, relationship basis, source quality and exposure state.
3. **Contract / Commissioning Timeline** — agreement, FID, financing, construction, first output, commercial operation, renewal/expiry as distinct clocks.
4. **Earnings Expectations Panel** — fixed-horizon estimates and actuals only where evidence-grade requirements pass; otherwise typed unavailable.
5. **Capital & Ownership Waterfall** — project/business contribution → debt/NCI/other owners → parent/common shareholder; display only when comparable amounts exist.
6. **Relationship View** — toggle physical containment, commercial relationship, ownership and conditional-transmission hypotheses. Unknown relationship magnitude is unweighted.
7. **Counterevidence / What changes the read** — visible beside the positive mechanism.
8. **Geographic dependency view** — only for evidenced jurisdiction/resource/market dependence; not a decorative world map.

No Sankey edge width, “bottleneck score,” exposure percentage, valuation multiple or probability is invented for visual completeness.

## 9. Evidence, rights, clocks and corrections

### 9.1 One shared assertion direction

Consume the accepted shared source-scoped curation assertion implementation from the GMI owner. Energy needs it to express product/business role, contract description, ownership event, reported financial/operating measure, milestone and attributed interpretation with:
- native source/locator;
- exact source scope;
- source publication/observation/retention/review clocks;
- business-valid interval where appropriate;
- limitations and source dependence;
- correction/supersession identity;
- all decision authority false.

If the Robotics proposal has not become the accepted shared implementation, resolve that shared-owner decision once. Do not create an Energy assertion schema.

### 9.2 Numerical facts remain with native financial/company owners

A curation assertion may point to or summarize an admitted numerical fact; it is not a bypass around the financial source owner. Company/Earnings/financial owners retain metric definitions, filing/release identity, management guidance and compatible calculations.

R5 research observations are evidence for the design. They are not themselves a new production consensus warehouse. Current third-party consensus requires rights/admission and historical first-known evidence before production historical-revision claims.

### 9.3 Private/full-fidelity publication

Full detailed research must not enter public Git-tracked Theme Graph data, static HTML, Pages, public R2, source maps, analytics, browser persistent storage or a new domain bucket.

Prefer the existing private Research Vault publication owner and authenticated Macro transport after that owner accepts one shared typed \`economic_changes\` projection role. If Technology or another accepted predecessor has already landed that role, Energy consumes it unchanged.

A missing private binding is a precise architecture gate, not permission to make live research public or create a second store.

### 9.4 Corrections

Source correction, accounting restatement, contract amendment and research interpretation revision remain different events. Append/revise through the accepted native owner with exact prior identity and clocks; never mutate history by URL label alone.

## 10. Null, degraded and conflict behavior

The Energy dossier must distinguish:
- unknown versus zero;
- source not found versus source unavailable;
- source unavailable versus rights restricted;
- no current observation versus observed false;
- source disagreement versus horizon/scope split;
- present operations versus future target;
- contingent versus funded;
- exact versus range versus qualitative;
- company-level value versus segment/project-level value;
- current consensus versus historical archive;
- issuer-process support versus independently timestamped historical estimate.

Use the shared STSI conflict classes where applicable: \`TIMEFRAME_SPLIT\`, \`SCOPE_SPLIT\`, \`FRESHNESS_SPLIT\`, \`COVERAGE_SPLIT\`, \`AUTHORITY_SPLIT\`, \`GENUINE_CONTRADICTION\`, \`UNAVAILABLE\`.

A conflict never disappears because an LLM prefers one narrative.

## 11. Relationship and causality law

Energy research produces typed **descriptive relationships** and **conditional hypotheses**. It does not automatically write causal Theme Graph edges.

Allowed descriptive distinctions include:
- member-of accepted basket/theme;
- source-scoped business role;
- sells product/service to a stated market;
- owns a stated interest;
- contract references a stated index/counterparty;
- project uses a stated technology/input;
- reported metric belongs to a stated business scope.

Conditional transmission — e.g. “higher PJM prices may improve an unhedged merchant generator more than a regulated utility” — remains an attributed hypothesis with assumptions and counterevidence unless the existing relationship/evaluation owner accepts a stronger relation.

Shared membership is never proof of causality.

## 12. Authority and non-goals

Every Energy Economic Change Dossier is context/explanation only.

It may not:
- add/remove basket members or weights;
- change ThemeState stage or recommendation;
- create stock ranks or beneficiary scores;
- change Prophet admission/ranking;
- open/close entry;
- size a position;
- originate an alert/trade;
- promote a research facet into a canonical theme;
- infer “cheap” from a low historical multiple;
- call a benchmark residual alpha;
- assign event-response causality from one observation.

Existing entry/ranking/portfolio/trading owners remain visually and semantically separate.

## 13. First-release completion law

The first Energy vertical is **not complete** when:
- a schema exists;
- a research JSON is committed;
- the Theme Tracker shows a new shell;
- an API returns a fixture;
- unit tests pass;
- CI is green;
- a PR merges.

The Nuclear Value Capture vertical completes only when:
1. at least one accepted real nuclear economic observation traverses its lawful native source/evidence path into the shared dossier;
2. one core-basket role and one supplemental fuel-basket role render with the correct relationship basis;
3. one source-backed milestone/refusal case visibly remains non-operating/non-revenue rather than being promoted;
4. value-capture stages, capital/ownership limitations, sources and clocks are visible;
5. unavailable expectations remain typed unavailable rather than guessed;
6. the existing \`state_of_themes.html\` and \`basket/nuclear_power.html\` path leads to the research without changing existing lane/entry/member decisions;
7. the existing company path can navigate into and back from the relevant Energy research;
8. denied/anonymous/public mirrors cannot recover full-fidelity paid research;
9. exact-head tests, independent review and ordinary CI/release gates pass;
10. deployed browser proof covers desktop/mobile, EN/ZH and dark/light where required;
11. a subsequent real source update or rights-approved retained correction proves the update path rather than a one-time fixture;
12. legacy basket/theme/Prophet/entry outputs are unchanged for the frozen comparison set.

## 14. Acceptance requirements

The implementation plan must map every requirement below to an owner/task/proof. These are specifications, not executed product tests.

**ENE-01** Preserve one canonical Theme Graph and existing owner federation.  
**ENE-02** Broad Energy sector, canonical themes, source-local subthemes, baskets and research facets remain distinct.  
**ENE-03** A research facet cannot mint a canonical node by display alone.  
**ENE-04** A company can carry multiple evidenced roles without forced exclusivity.  
**ENE-05** Unknown exposure percentage remains unknown.  
**ENE-06** Supplemental basket relation does not become reverse primary-theme membership.  
**ENE-07** Source company name never becomes a guessed security.  
**ENE-08** Contract index, formula, option holder, start/expiry and volume scope remain explicit.  
**ENE-09** Future contract/capacity does not become current delivery/revenue.  
**ENE-10** Orders, reservations, RPO/backlog, delivery, revenue, cash and service are separate clocks.  
**ENE-11** Fee-based, dedication, fee-floor and take-or-pay semantics remain distinct.  
**ENE-12** Benchmark spreads are references, not realized company margins.  
**ENE-13** Current cash and sustaining/replacement investment remain separate.  
**ENE-14** Project cash investment includes contributed-asset/opportunity-cost treatment where material.  
**ENE-15** Consolidated, proportionate and common-shareholder cash remain distinct.  
**ENE-16** Customer advances/contract liabilities are not profit.  
**ENE-17** Credit recognition, receivable, transfer and cash receipt remain distinct.  
**ENE-18** Asset-sale proceeds cannot coexist with all future cash from the sold interest.  
**ENE-19** Accounting-policy change cannot independently prove lower economic risk.  
**ENE-20** Resource availability, production and acquired perimeter remain distinguishable.  
**ENE-21** Storage integrator delivery economics do not become storage-owner merchant earnings.  
**ENE-22** Technical/design/test milestone does not become commercial operation.  
**ENE-23** Technology fuel capability does not become measured fuel consumption.  
**ENE-24** Gross-margin break-even does not become free-cash-flow break-even.  
**ENE-25** Corporate-acquisition revenue is not automatically organic growth.  
**ENE-26** Issuer-specific FCF definitions remain visible before normalization.  
**ENE-27** R5 evidence grade travels with every historical expectation.  
**ENE-28** Estimate and actual definitions/units/horizon/ownership basis must match.  
**ENE-29** Panel count/aggregation/turnover travel with aggregate consensus.  
**ENE-30** Panel change cannot be labeled within-analyst revision.  
**ENE-31** Forecast-year rollover is not estimate revision.  
**ENE-32** Later archive retrieval cannot backdate first-known time.  
**ENE-33** Mixed surprise vectors remain mixed; no forced beat/miss bit.  
**ENE-34** Before-open and after-close events use declared different return windows.  
**ENE-35** External reported stock move is not a reproduced return series.  
**ENE-36** Stock-minus-benchmark is descriptive residual, not alpha.  
**ENE-37** Commodity moves remain separate unless an accepted exposure model exists.  
**ENE-38** Confounds are visible and block clean causal labels when untreated.  
**ENE-39** Public access does not establish commercial ingestion/redistribution rights.  
**ENE-40** Source URL is not immutable retention proof.  
**ENE-41** Source correction/restatement preserves prior vintage.  
**ENE-42** Full-fidelity paid research never enters public static artifacts.  
**ENE-43** Entitlement is checked before private provider bytes are opened.  
**ENE-44** Paid success/error paths use private/no-store and noindex/noarchive policy.  
**ENE-45** Browser stores no paid payload or credential in local persistent storage.  
**ENE-46** Missing/partial/restricted/degraded states are explicit and visually distinct.  
**ENE-47** Conflicts use shared typed conflict grammar rather than narrative averaging.  
**ENE-48** UI arithmetic is precomputed by native deterministic owner, not JavaScript.  
**ENE-49** Visual relationship magnitude is unweighted unless comparable evidence supports weight.  
**ENE-50** Accessible table conveys the same semantics as any graph.  
**ENE-51** EN/ZH and dark/light/mobile/desktop preserve the same facts and limitations.  
**ENE-52** Existing theme recommendation/lifecycle output remains unchanged.  
**ENE-53** Existing basket membership/weights remain unchanged.  
**ENE-54** Existing Prophet/member ranking and entry outputs remain unchanged.  
**ENE-55** Existing company/stock route remains canonical.  
**ENE-56** First vertical binds to \`theme:nuclear_power\` rather than a new Energy theme.  
**ENE-57** \`nuclear_power\` primary and \`uranium_miners\` supplemental populations remain distinguishable.  
**ENE-58** Cameco view preserves Fuel Services price/cost scope and Westinghouse equity-method attribution.  
**ENE-59** Centrus view preserves contingent/funded backlog and financing-instrument rights.  
**ENE-60** BWXT is represented as components/services, not plant-owner power economics.  
**ENE-61** NuScale design approval remains distinct from a site operating license/current generation.  
**ENE-62** Oklo test-reactor criticality remains distinct from Aurora commercial generation.  
**ENE-63** Expectations unavailable is an allowed complete state for a company dossier.  
**ENE-64** First unit is bounded; oversize response refuses or narrows rather than silently truncates.  
**ENE-65** Source instruction-like text is inert data, never execution authority.  
**ENE-66** A model-authored interpretation is attributed and cannot self-ratify source facts.  
**ENE-67** Current Theme Graph/store/evidence shared-path writers are reconciled before modification.  
**ENE-68** Current \`basket_detail.html.j2\` writer is reconciled before modification.  
**ENE-69** Public \`build_state_of_themes.py\` is not used as a private research data plane.  
**ENE-70** Sector-dossier #7777, if accepted, is consumed for sector-level projection rather than copied.  
**ENE-71** Shared economic-change contract/private role, if accepted by sibling owner, is consumed rather than cloned.  
**ENE-72** Real source → native owner → dossier → entitled API → existing-page browser path is proven.  
**ENE-73** Anonymous/free/public mirrors are negative-proven.  
**ENE-74** A real correction/update proves post-launch liveness.  
**ENE-75** Research usefulness, predictive validity and decision authority remain separate acceptance dimensions.  
**ENE-76** Fable and workers must not redo R1–R5 foundational research.  
**ENE-77** Fable retains cross-owner integration, collision adjudication, privacy and final acceptance; routine bounded implementation can be delegated.  
**ENE-78** Full Energy coverage remains explicit after the first vertical; one witness never implies sector completeness.

## 15. Required later breadth after the first vertical

The same shared contract must support, without architecture replacement:

- Hydrocarbon cash-cycle: EOG/Valero/KMI/Cheniere/SLB/HAL/Targa/Baker Hughes/EQT archetypes.
- Power-demand value capture: Vistra/Duke/GE Vernova/Quanta/Clearway/Talen/Eaton and connected gas/infrastructure cases.
- Solar/wind: manufacturing, service, development, project ownership and capital recycling.
- Storage: integrator versus asset owner.
- Renewable fuels/hydrogen/geothermal/CCUS/waste-to-energy.
- Global regional comparisons and source/metric definitions.
- Historical expectations/valuation evaluation under the R5 grammar.

The eventual product should let the investor move from **Sector → Theme → Facet/Subtheme → Economic Role → Company/Asset → Evidence → Expectations/Valuation → Existing Entry Context** without losing source scope or inventing causal certainty.

## 16. Review focus

Reviewers should challenge:
1. any new object that duplicates an existing canonical owner;
2. any economic role that silently becomes a theme identity;
3. any relationship whose direction/weight is inferred from membership alone;
4. any source/metric clock collapsed into one page timestamp;
5. any company-level figure attributed to the wrong owner or denominator;
6. any paid/private research exposed in public artifacts;
7. any expectation comparison without evidence-grade and horizon checks;
8. any theme-level positive narrative that hides capital/ownership offsets;
9. any first-vertical implementation that modifies ranking/entry behavior;
10. any implementation plan that assumes sibling draft designs are merged capabilities.

## 17. Design boundary

This document freezes the Energy product thesis and domain semantics for implementation planning. It does not:
- accept the sibling shared assertion or common dossier contract;
- acquire source rights;
- admit current live research rows;
- transfer source custody;
- create an implementation operation;
- assign Fable;
- merge/deploy;
- establish predictive edge or a current investment verdict.

The exact next step is to write the executable implementation plan against this design and current collision/gate state, then prepare the complete Fable CEO packet. The research mission remains incomplete until the R6 design/plan/handoff package is durably verified.
