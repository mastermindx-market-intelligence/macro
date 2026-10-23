# Robotics Theme Intelligence — first evidence-to-dossier vertical

**Written design proposal · 23 September 2026 · revision 1**

Operation: `gmi-robotics-bom-research-20260923-sol-001`. Carrier: Macro draft/HOLD PR #7773, `sol/robotics-bom-research-20260923`. Parent mission remains incomplete. This document selects a proposed architecture; it is not an accepted production contract, worker commission, permission to merge, or release receipt.

## 1. Outcome and first scope

The investor's job is to understand what a robotics company actually sells, which part of a robot or deployment system uses it, which applications and research slices it belongs to, whether a commercial relationship is documented, and whether the underlying economics or constraint has changed. The machine's job is to preserve those distinctions over time and expose the supporting evidence without making the reader reconstruct the company from headlines.

Robotics is the reference theme for a reusable model, not an isolated microsite. The full ambition remains an application-to-platform-to-subsystem-to-component-to-process/material-to-business-to-security map, with regional production, supplier alternatives, bottleneck migration and adoption evidence. The first delivery proves the complete user journey on **Precision Motion and Perception**, not all 94 proposed categories at once.

The initial journey is `state_of_themes.html → basket/robotics_automation.html → research slice → company/product assertion → exact source`. Existing thesis, leadership, group participation, member selection, entry, price and earnings owners retain their outputs. New research must not change a recommendation, current basket membership or trade policy.

Acceptance means a signed-in reader can identify a documented component inclusion, distinguish catalog capability from inclusion, inspect quantity and uncertainty, understand ownership or business-scope limitations, and return to the existing stock/group workflow. An anonymous reader cannot obtain the new full-fidelity current research payload through another mirror. A schema, empty widget or passing unit test alone does not meet this outcome.

## 2. Source pins and existing seams

Protected procedure: Mastermind `a5aa42d15c3e5cbfe785b415511de188cff66bd0`, Skillpack 1.0.1/bootstrap 1. Interface-read pin: Macro `bbc684e2acd10319df9b2007882f478ae30f1d70`. The research branch retains its existing base; reading newer interfaces is not a rebase or custody transfer.

The relevant current implementation facts are:

| Existing source at the interface pin | What it supplies | What it does not supply |
|---|---|---|
| `contracts/theme_graph/evidence.v1.schema.json` | Dated, closed evidence receipts with owner identity | A structured product/BOM/ownership assertion body |
| `engine/theme_graph/store.py` | Existing append-only evidence store, fixed columns, nightly-only writer | Automatic persistence of an arbitrary extra field; intraday edge-belief revision semantics |
| `engine/theme_graph/identity_resolution.py` and its owner rows | GMI-to-Data-OS issuer/security/listing resolution | Permission to resolve a new product or company by a similar label |
| `contracts/evidence_foundation/README.md` and `vocabulary.v1.json` | K1 owner-native references, blocks, recipes and clock/subject rules | A fact warehouse; an automatically working cross-type identity bridge |
| `engine/company_intelligence/contracts.py` | Closed fiscal-event/company context | A generic product-catalog intake hidden in earnings highlights |
| `scripts/build_state_of_themes.py` and existing theme consumers | Theme context and established UI composition | A license to recalculate analytical owner states in the browser |

Immutable code references use `https://github.com/mastermindx-market-intelligence/macro/blob/bbc684e2acd10319df9b2007882f478ae30f1d70/` plus the paths above.

The current GMI workstream rejects standalone W4/W5/W6 revival. F04, operation `marketontology-f04-ontology-transmission-20260826-fable-001`, remains downstream product composition; K3-D and the existing relationship owners retain propagation. STSI architecture #7577 remains the page/hierarchy direction. This vertical creates no new program, global identity master or graph authority.

Potential collisions previously identified are #7664, #7455, #7462, #7669 and #7633. Their exact current heads, changed paths and source custody must be refreshed immediately before product-interface writes, not repeatedly during research. This document does not declare their current release state.

## 3. Alternatives and selected representation

**A. A robotics database and graph beside GMI. Rejected.** It is quick to populate but creates competing entity, evidence, correction and refresh authorities. A generated JSON response is fine; a competing canonical store is not.

**B. Force every product into an existing theme/company node, or put factual bodies in K1/QLedger. Rejected.** A reducer model is not a company, and a source-local topic is not a physical component. K1 is a reference layer; the registered QLedger object is a forward claim. These shortcuts would make valid-looking records mean the wrong thing.

**C. Extend native GMI curation evidence in place, using source-scoped object descriptions, then compose the existing pages. Selected proposal.** Add one optional, strictly versioned curation-assertion payload to the existing evidence owner. Retain the native evidence identity/store/writer. Do not add global product/component/business node kinds in the first vertical. Products, robot configurations and business units are source-scoped descriptions inside a reviewed assertion until their proper identity owner supports a stronger binding.

This choice is narrower than a universal industrial knowledge graph, but it supports useful component, company-role and financial-scope research immediately after acceptance. It leaves a lawful path to later first-class products instead of baking in an improvised product master.

### 3.1 Native extension, not a second ledger

The proposed field name is `curation_assertion`; its proposed payload version is `theme_graph.curation_assertion.v1`. Both are **design names, not current enrolled contracts**. Before use, the implementation must add the field to the existing closed evidence schema, native column list, serialization and reader validation, together with discriminating round-trip tests. Existing receipts remain byte-semantically unchanged and expose the new field as absent/null. A field-only schema patch that the store drops is unacceptable.

New assertions are admitted through the incumbent GMI curation/probation and publication discipline. This design does not grant a request handler, browser or research script permission to append. Existing nightly admission stays defaultless and fail-closed. No second curation queue, retry loop, latest-state file or scheduler is introduced.

The evidence receipt describes **the publication of a reviewed house assertion**, and therefore may use `kind=operator_curation`. Its `source_ref` must identify the immutable house-curation revision and exact assertion selector, not merely the external URL. `published_at` is truthfully the publication of that house curation. The upstream source's own publication date is a separate field and may be unknown. The curation date must never be presented as when the supplier originally published the information or when the business event occurred.

The existing `effective_at` meaning is not repurposed. For this receipt it describes the curation publication event, explicitly equal to that release date. The asserted business event's effective date is separate and typed. Existing readers must not display the envelope's curation date as business-world validity. This distinction is a compatibility gate, not a footnote.

The immutable curation revision is derived from canonical reviewed assertion content, including source vintage/locator, scope and review record. This distinguishes two statements in one document and changed bytes at one URL on the same date. The exact native identity grammar is frozen in the implementation plan; no unverified digest or source-retention receipt may be invented to satisfy it.

### 3.2 What is inside a source assertion

The payload has closed, bounded sections:

| Section | Required meaning |
|---|---|
| Source | Publisher, exact document/URL, locator, upstream publication value and grain, observed/retained clocks, original-source lineage, native retention pointer/digest state |
| Review | Curation revision, reviewer/admission receipt, review date, explicit accepted or held disposition; model extraction never self-ratifies |
| Subject and object | Source-native business/product/platform labels, publisher model identifier and generation/configuration where stated; optional validated canonical company binding |
| Predicate | Exactly one assertion type; separate quantity and financial observations are not packed into a generic partnership edge |
| Statement mode | Reported historical/current fact, catalog description, announced arrangement, forward target, or explicitly attributed interpretation |
| Scope | Application, technology facet, product family, configuration, company/business, region basis, period and denominator; unknown fields remain typed unknown |
| Observation | Value or range, unit, quantity basis, gross/net basis, stock/flow distinction, estimate/report status and precision |
| Temporal applicability | Business-valid date/interval or explicit unknown; source publication, first observation and system retention are not collapsed |
| Limitations | What the source establishes, what it does not establish, coverage, source dependence and expiry/review trigger |
| Correction | Exact predecessor assertion/reference and reason; withdrawal or replacement appends, never rewrites history |

Initial assertion types: `PRODUCT_CAPABILITY`, `DOCUMENTED_PRODUCT_INCLUSION`, `ANNOUNCED_DEVELOPMENT_AGREEMENT`, `DEPLOYMENT_TARGET`, `REPORTED_DEPLOYMENT`, `OWNERSHIP_EVENT`, `REPORTED_FINANCIAL_MEASURE`, and `REPORTED_OPERATING_MEASURE`. A controlled, versioned type list is preferable to accepting arbitrary model-authored predicates. These types classify evidence; they do not create new economic graph edges or a trading decision state machine.

A source saying it targets a future deployment is an observed **source statement** with forward-target content. It is not an observation that the future deployment has happened. Both layers must survive the wire and visible copy. The first vertical does not register GMI as another forecast-originating owner.

A source-scoped object key is unique only within that native assertion/source namespace. Two similar product labels from different documents are not automatically merged. Unknown model revision is visibly unknown. A later accepted global identity mapping may connect source objects, but cannot overwrite the original evidence.

### 3.3 Identity, K1 and compilation

Use existing validated GMI/Data-OS identity-resolution rows for stock-page links, security joins and listing eligibility. A source-only record can still show a supplier's attributed name and product evidence, but it must say that the listing is not bound and must not acquire live valuation, stock performance or portfolio relevance from a guessed ticker.

K1 references native GMI evidence IDs. Its current vocabulary admits that native evidence subject; it does not admit an arbitrary product ID or a consumer-invented company join. Compile one native-evidence-subject block/recipe at a time where valid. The F04 page can present such independently typed results in an approved thematic research section; it must not assert that they passed a unified security-subject recipe.

The added payload also introduces upstream-source and business-applicability clocks. K1 needs an explicit opt-in curation-subtype binding under the same GMI owner/physical reader, with every such native clock preserved and legacy evidence bindings unchanged. That binding is proposed, not currently enrolled. A reference to the old receipt envelope alone must not be advertised as a complete clock-preserving reference to the new assertion. Until the subtype binding is accepted, the full assertion block remains unavailable rather than silently losing clocks.

Cross-owner financial/company/market panels retain their own identities and receipts. Until the required validated bridge is actually supported and consumed, a combined recipe must remain refused/degraded. A source-family mapping declaration is not proof that the bridge exists. The UI must not hide a K1 refusal behind a fully composed-looking response.

### 3.4 Retention and protected publication

Raw documents and current claim bodies use the existing owner-approved private retention/artifact path. No new bucket or database is authorized. A URL and web-search result alone do not prove immutable native retention. Records with missing retention or review may remain in research; they do not enter the accepted current product as fully qualified claims.

Any new current GMI curation rows containing the detailed product payload must be excluded from public Git/Pages/R2 staging. Reusing an existing store does not exempt its new bytes from access law. The publisher's allowlist/private binding must be proven before adding live records. If that binding is absent, hold the live admission rather than creating a new storage plane or committing private content into the repository.

## 4. Granularity, quantities and financial meaning

Keep two overlapping dimensions: **applications** such as humanoids, factory robots, warehouse systems and surgery; and **technology facets** such as rotary motion, linear motion, perception and touch. A facet is a versioned research filter, not automatically a canonical theme or tradable basket. A company may participate in several facets with different evidence.

BOM quantities apply to a named model/configuration, not every generation from an OEM. Quantities carry `per_robot`, `per_joint`, `per_hand`, `per_cell`, `per_installation` or another accepted explicit basis. Do not multiply a per-hand quantity by two without an independently supported hands-per-robot assumption.

An integrated actuator and its motor/reducer/encoder are two views of the same assembly. Cost aggregation selects one non-overlapping purchase boundary. Mixing parent assembly costs and contained component costs refuses. Costs also retain currency, year, order volume, manufacturing-versus-selling-versus-installed basis, and whether tooling, integration, tax or software is included. Missing costs produce an unweighted map, not invented Sankey widths.

Revenue share requires a numerator and denominator for the same entity, fiscal period, currency and consolidation basis. “Not separately disclosed” is not zero. Segment revenue, total company revenue, supplier market share, basket weight and stock beta are not interchangeable. Ownership events change the applicable business-to-issuer interpretation only from their evidenced effective date; announced transactions remain distinct from completed transactions. Minority ownership is not consolidated operating revenue.

HDS's June-quarter product/region operating table is a useful real input to this design. Preserve its reported rounded totals separately from sums of displayed cells. Orders and sales are period flows; backlog is an end-period stock. A book-to-bill ratio is an explicitly derived monetary ratio, never a delivery lead time, utilization rate, robot count or proof of a global shortage. The primary-source register below provides the exact report and pages.

## 5. Supply constraints and monitoring

The first view displays separate source observations for demand/orders, backlog, production, qualified capacity, lead time, substitution, pricing and margin. It does not calculate a single bottleneck score. A component may be technologically critical without being supply-constrained, and announced capacity may fail to become qualified output.

Each observation's comparison key includes component/product family, manufacturer/business, region basis, application where known, period, unit, gross/net basis, source method and revision. Only matching keys support a change calculation. Geography by sales subsidiary is not the location of the final robot factory. Revenue from an application is not revenue from one unmentioned customer.

Use the existing ingestion/refresh owners. New issuer releases, product replacements, ownership events and corrected native sources trigger recomputation through those owners, not a robotics watcher service. A new unsupported relationship becomes a review candidate, never an automatic `SUPPLIES` edge. A previously accepted fact remains historically readable when its current review window expires.

For the bounded first release, current means **latest accepted evidence available**, not every fact observed today. Show the upstream period and publication date beside the display build time. An undated catalog page reads “publication date unavailable; observed on [date].” Lapsed review, withdrawn source, unresolved identity and rights restriction each have distinct states and actions.

Future bottleneck migration analysis asks whether an easing constraint is followed by productive deployments, whether a new constraint becomes binding, and whether suppliers retain pricing or lose content through insourcing. It remains an attributed hypothesis until supported by the existing relationship and evaluation owners. This specification does not expand K3-D or generate automatic portfolio actions.

## 6. Product, transport and visual behavior

The existing Theme Tracker remains the thesis-health board. Add a Robotics research entry with the two initial facets, dated evidence coverage, one source-backed change and a direct detail link. Research coverage is not an attractiveness ranking. A new marker is not counted as another independent confirmation of a legacy theme signal.

The existing robotics detail page gains a read-only research module with: a concise mechanism summary; application/technology filters; company/product rows; documented inclusion/arrangement details; operating-constraint observations; and evidence/limitations. Preserve the incumbent timing and holdings sections unchanged. Do not clone the shared detail shell or calculate owner signals in JavaScript.

The initial supply-chain display is an unweighted layered map with synchronized accessible table. Nodes are clearly labeled as source-scoped products, businesses, applications or component facets. Lines say “catalog application,” “documented inclusion,” “announced development” or another exact type. A source-reported relationship cannot look like an independently verified current procurement link. Color is supplementary; line labels and keyboard-accessible descriptions carry the meaning.

BOM containment within one platform is acyclic. The broader economic relationship view may legitimately contain reciprocal roles: supply and planned customer deployment are separate labeled lines, not an invalid cycle that gets deleted. Selectable views must distinguish physical assembly, commercial relationships and market measurement rather than blending them into one visually causal graph.

A pinned evidence drawer shows the original statement context, source locator, date, units/denominator, uncertainty and supersession. Use short lawful excerpts or original paraphrase, not copied reports. Deep links preserve the selected facet and return route without persistent storage of the private response. Mobile uses stacked rows and the same source records, not a second calculation.

### Transport contract

Use the existing Macro authenticated `require_user → enforce_site_full(always=True)` pattern. A proposed adjacent read-only route is `GET /api/themes/robotics/research/v1`; the final route and module placement require incumbent interface reconciliation. It uses retained accepted owner data, not a new browser-time internet crawler.

Apply private/no-store, Vary and existing noindex/nosniff behavior on success and errors. Do not embed the current full payload in `site/**`, source maps, a public seed, preloaded HTML, service-worker cache, localStorage or IndexedDB. A public shell and small deliberately approved editorial examples are different from the paid current snapshot. Permission to publish the research proposal is not permission to publish the production map.

Record the deployed code revision and exact input generation/digests. A render timestamp cannot replace a stale source watermark. If owner generations are incoherent, refuse the affected composed section with an exact reason while keeping independent legacy panels functional.

Target budgets for the first bounded view are no external network requests during composition, at most 50 accepted assertions in the initial response, and warm API p95 at or below one second on the target host. These are proposed acceptance goals, not measurements already achieved. Pagination/filtering must not change the population used by analytical owner metrics. Measure before adding any precompute or caching infrastructure.

## 7. Mandatory real cases

| Case | Required visible result | Forbidden inference |
|---|---|---|
| Orbbec / Twinny configuration | Source-reported product inclusion and quantity for the described configuration | Universal camera count, current OEM contract, selling price or customer revenue |
| Parker motor family | Catalog capability with unknown original publication date | Named humanoid inclusion or a dated 2026 product launch |
| Schaeffler / Hexagon | Separate supplied technology and forward deployment roles | Treating a future target as installed robots |
| Zebra and PTC business changes | Dated business ownership/event evidence separate from retained businesses | Applying old operating exposure indefinitely or using announcement date as closing without proof |
| Sanhua | Attributed actuator-development/scale-up evidence; unreported robotics revenue remains unknown | Thermal-management customers, corporate plants or total revenue become robotics-specific |
| HDS | Product/region monetary operating observations with published totals | Order growth becomes unit shortage, blanket humanoid demand or lead time |
| Stabilus / Synapticon | Announced joint-product roles, with quantity/date unknown where unreported | A development announcement becomes qualified capacity or deliveries |
| Legacy robotics basket | Existing identity and membership remain unchanged | New research facets silently rebalance the basket or qualify member entries |

The earlier case sources remain in the foundation packet. The new four-source register is a supplement, not an independent corroborating source for the same underlying disclosure.

## 8. Validation and delivery boundaries

The accompanying acceptance-case file specifies 32 cases across predicate/scope, identity, time/correction, arithmetic, rights/transport and end-to-end rendering. They are **test specifications, not executed product tests**. Research QA may check their identifiers, references and arithmetic; that cannot prove the future implementation passes them.

The first implementation unit should remain a useful vertical: one admitted inclusion assertion plus one catalog capability, native retention/read validation, private API, existing-page consumer, discriminating tests and real-path browser evidence. Include missing/rights-blocked and anonymous-denial states. A contract-only PR must not be described as completing that unit.

Subsequent bounded units add ownership/financial scope, product/region operating observations, then broader application coverage. New price baskets, model-specific cost scenarios and supply-chain-to-trade effects are separate decisions with their own membership, evaluation and authority gates. Do not turn this into a mega-PR or make basic research usefulness wait for every proposed category.

Before any product edit, reconcile the exact native schema/store and theme/detail/API owners, planned-write overlap and private publication binding. Preserve incumbent source custody and held operations. An implementation plan must identify exact paths and commands against that accepted base; this document intentionally does not pretend those commands have already run.

Production acceptance requires an approved source entering the actual native path, accurate visible output on the deployed code, working source and company navigation where identity is resolved, desktop/mobile and EN/ZH/dark/light proof, and no public alternate-path leak. Existing basket/rank/entry behavior must be identical on frozen inputs. Independent review and exact-head release gates remain required.

## 9. Design self-review and next action

Self-review checks: source statements are not world truth; products are not forced into company/theme IDs; a native field survives store round-trip; K1 cannot be used to disguise an unresolved subject; catalog retrieval does not backdate publication; same-day changed evidence cannot be swallowed by a keep-first key; publication and validity clocks remain distinct; financial and geographic scope survives; the new private payload has no public twin; all 32 acceptance cases map to a requirement. This is a design inspection, not independent approval.

The representation decision is now explicit enough for written-spec review. The next step is to accept or amend this specification, then produce the first vertical's executable implementation plan against the incumbent heads. The design does not relax GMI D2/K3-D dependency gates, confer release authority, or complete the parent robotics mission.

## Primary-source supplement

- D1 — Sanhua, interim results published 26 August 2026, PDF pages 28 and 30 (visually checked): https://www1.hkexnews.hk/listedco/listconews/sehk/2026/0826/2026082601555.pdf
- D2 — Parker, K-Series product/application page; original publication date unestablished, observed 23 September 2026: https://discover.parker.com/K-Series
- D3 — Harmonic Drive Systems, first-quarter filing published 7 August 2026, PDF pages 14-16 (visually checked), period 1 April–30 June 2026: https://www2.jpx.co.jp/disc/63240/140120260804507706.pdf
- D4 — Stabilus, Synapticon joint-product announcement, 29 July 2026: https://group.stabilus.com/news-and-events/press-releases/mail/news-synapticon-and-stabilus-form-partnership-to-develop-a-joint-product-line-of-integrated-actuators-for-humanoid-robots

Native-source and source-statement qualifications above are intentional. No official filing is treated as an independent technical audit of a product's performance or proof of a named customer relationship it does not disclose.
