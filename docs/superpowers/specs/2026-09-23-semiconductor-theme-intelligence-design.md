# Semiconductor Theme Intelligence — B-first design with a staged path to C

**Written specification for Chairman review · 23 September 2026 · revision 1**

**Decision:** deliver a useful compositional Semiconductor dossier first (B). Preserve the semantics that make later shared entity resolution and richer industrial queries possible (C). Do not implement C before B acceptance or make B depend on a universal product/facility graph.

Operation: `gmi-semiconductors-research-20260923-sol-001`. Parent: `WS:GMI-THEME-GRAPH`. Carrier: Macro draft/HOLD PR #7780, `sol/semiconductors-research-20260923`. Research baseline: `f69026264debb265877076a442c7d9211d251fdc`. Current Chairman decision was recorded at `d40ebbb0d18a62a680029743d11e05502c51edb1`. Procedure: Mastermind `4c1b3d389286df2a4b5b98a4d4491f2c8a1263f2`, compatible Skillpack 1.0.1/bootstrap 1. Native interface-read pin: Macro `56c8ef2fce6f740dd853f4ffb29574ae5b729c17`; this is not a rebase.

The Chairman approved B with foundations for C and delegated the practical design choice to Sol. That permits this written specification, not acceptance of its contents, an implementation plan, deployment, or a worker commission. Fable remains the intended later implementation orchestrator. No product code, production schema, live curation data, market signal, portfolio or trading effect is made here.

## 1. Outcome and the decision being made

The investor's job is to understand what a semiconductor business does, why a particular industrial change matters to it, what constrains commercial realization, how the change could affect its economics, and what evidence would overturn that interpretation. The machine's job is to retain product, process, relationship, financial and temporal meaning so each future question does not require rebuilding the industry from headlines.

The full ambition is a living semiconductor intelligence system across design/IP, logic, memory, analog, power, RF, sensors, materials, equipment, fabrication, packaging/test, manufacturing infrastructure and their application markets. The moat is accumulated, correction-safe industrial evidence connected to governed economic interpretation and learning—not the visual graph by itself.

**B is a complete first product, not a disposable demo.** A signed-in reader must complete a journey from `state_of_themes.html` through the existing semiconductor detail experience to a granular research slice, source-scoped industrial evidence, a validated company relationship, economic interpretation and management-guidance history. The reader must be able to return to the incumbent company/stock workflow. Correct refusal is part of that journey, but an empty collection of refusals is not acceptance.

**C is a later evolution of the same owners.** After B is accepted, independently governed global product/process/facility identities and qualified relationship queries can connect source-scoped descriptions across documents and themes. A larger graph does not gain financial, forecast, identity or trading authority by containing more nodes.

Rejected choices: A alone is too weak on economic interpretation; immediate C burdens the first release with global identity and query infrastructure. The selected B-to-C path keeps the economic user job now and defers only the broader identity/query capabilities.

## 2. Release boundary: what B must actually deliver

B includes two proof sets in one shared experience:

| Proof set | Industrial question | Mandatory economic/context result | Necessary limitation |
|---|---|---|---|
| HBM and advanced packaging | Which generation, configuration and packaging route is described, and what milestone changed? | At least one correctly bound issuer's prior management outlook, subsequent actual and new outlook, with an explanation of the relevant business mechanism. | Broad issuer guidance is not HBM-only guidance. A catalog packaging diagram does not prove a particular memory supplier's procurement route. |
| SiC/GaN and specialty manufacturing | Is a source describing a plan, operating start, qualified product, or realized output? | At least one correctly bound issuer's operating/financial context and management-outlook comparison, including the difference between ramp benefits and cost/price pressure. | A reported operating start does not establish full yield, customer approval, allocation or unit cost. |

The first proof set is the deep flagship. The second is required before B acceptance so the implementation cannot hard-code an AI-only industry model. These are bounded real-data demonstrations, not a required full census of every semiconductor company.

B also includes research-slice filters, company/business-role rows, the five industrial views in section 7, evidence/limitations drawers, explicit comparison refusals, historical-source views, and cross-theme reference navigation. Existing recommendation, timing, constituent selection, ranking and stock-entry sections remain owned and computed by their incumbents.

B does not require numerical global capacity, customer-confidential yields, precise revenue purity for every business, licensed historical Street consensus, a global product master, a market-incorporation estimator, a graph database, automated supply-chain simulation, or new trade rules. Their absence cannot erase a supported operating event; it does limit conclusions that require those inputs.

A release claiming B complete must pass both positive proof sets and the negative-state acceptance floor in section 16. Shipping only a source drawer, ontology, or authenticated empty API is a partial milestone, not B.

## 3. Fresh interface evidence and what it permits

The following were inspected at the native interface pin above. These are source-contract facts, not runtime or production acceptance receipts. Exact locators are relative to that immutable commit.

| Ref | Source and inspected scope | Verified boundary | Consequence for this design |
|---|---|---|---|
| N01 | `contracts/theme_graph/evidence.v1.schema.json`, full; blob `83dece15e98b9c8775a584afcd6ee09811dad220` | Closed row; dated source receipt; no industrial assertion payload. Rights booleans are mint-time snapshots. | A structured payload requires an accepted shared native extension. Publication cannot trust old row booleans alone. |
| N02 | `engine/theme_graph/store.py`, lines 1–190; blob `63b58860d35bd183c947c85088f83bd53359bb9f` | Explicit evidence columns, keep-first receipt identity, append-only belief/lifecycle records, defaultless nightly write gate. | Schema and persistence must evolve together. Request handlers do not become writers. Existing correction/identity homes remain canonical. |
| N03 | `contracts/theme_graph/nodes.v1.schema.json`, full; blob `14b34a5d65e82ba5a5f6a14e85ecf32508de6351` | Existing node kinds do not include product, process or facility. Source-local themes are not physical-object IDs. | B cannot disguise physical objects as themes or companies. C requires separately reviewed native identity extensions. |
| N04 | `contracts/theme_graph/identity_resolution.v1.schema.json`, full; blob `63239b29ce376c9f2708af9e86ba772bc3a55e0f` | Company-node bridge only; a resolved security can lack resolved issuer evidence; issuer field is current identity, not historical lineage. | Validate each axis independently. Do not use a current issuer mapping to attribute a historical business event. |
| N05 | `contracts/evidence_foundation/README.md`, lines 1–160; blob `a47e898309813636cf167c517492aa569aa296ca` | K1 references native objects; it is not a store. Current recipe compilation lacks a validated cross-type bridge-object slot. Date/day versus instant cutoffs can be ambiguous. | Separate native blocks are valid; an unsupported unified security recipe is not. Preserve native clocks and typed refusal. |
| N06 | `engine/company_intelligence/event_workspace.py`, lines 1–120; blob `efdbd91156b2a94e6e8bdca7e8cae454a6860e68` | Earnings workspace has facts/guidance/claims/source fields, immutable manifest lineage and context-only authority. | Use this owner, but field existence does not prove production guidance coverage for our witnesses. |
| N07 | `contracts/financial_intelligence_packet.schema.json`, lines 1–150; blob `876f7002b4100c7bd08e5741417578134ecc7522` | Governed financial packet; separate source-event and system-recorded cutoffs; current entity contract requires a CIK. | Preserve two-cutoff semantics. Do not invent a CIK for foreign/private businesses or claim universal entity coverage. |
| N08 | `engine/theme_graph/rights.py`, lines 1–165; blob `63ba2b60e9be6615208fab5b53b1fbcb44f4f433` | Registry authority; unknown families refuse; registry load is cached by path. | Reuse rights owner and require tested refresh/revocation behavior. A changed registry file alone is not proof a long-lived process has consumed it. |
| N09 | `app/earnings.py`, full; blob `3b8251388c8e9ae59b933212a7384faaea61eb27` | Authentication and paid-feature enforcement before private-store reads; private/no-store success/error transport. | Reuse the pattern and existing storage ownership. An Earnings private binding does not automatically authorize GMI payloads. |
| N10 | `templates/basket_detail.html.j2`, lines 1–90; blob `a3d8846bd27961db2c7877d693e8fd43bf399baa` | Existing shared detail shell, language/theme behavior and incumbent market sections. | Extend the shared shell once; no semiconductor-specific replacement page. |

Robotics PR #7773 was freshly read at `f10211657c6c31df3c9af73cd4b9484e2dd7690a`. Its body records an accepted design/plan and intended Fable route, but this is not a runtime START receipt. Its optional curation-assertion proposal is the shared dependency. The current N01/N02 sources still lack that field. Coordinate one extension; do not fork it.

Historical audits in the fifth installment reported incomplete consensus and price-vintage capabilities. They remain useful warnings, not a fresh all-company availability census. For this release, consensus and incorporation stay unavailable unless the respective current owner provides accepted, licensed, time-valid objects. This is a capability gate, not an assertion that no subscription exists anywhere.

Prior custody references #7462, #7669 and #7664 are navigation for the implementation owner. No product path is modified here; their then-current heads and interfaces must be reconciled before writes. The earlier #7669 metadata/body mismatch is not silently resolved by this design.

## 4. Ownership and composition

The data flow is:

`approved source retention -> incumbent source/domain intake -> native reviewed assertion or financial/event object -> validated native identity/clock/rights references -> bounded F04/shared-Theme composition -> authenticated reader`

GMI owns industrial curation and research-slice membership. Earnings owns issuer events, source documents, guidance and actual-result context. Financial Intelligence owns governed accounting measures and formulas. The native Data/Stock and Earnings identity owners own issuer/security/listing and permitted historical aliases. K1 owns reference/block/recipe semantics, never claim-body storage. Existing F04/shared Themes composition owns the reader experience. Existing source rights, private retention and publication owners control access. Existing evaluation and forecast owners retain any future predictive or decision authority.

A page can present several native blocks under a theme without pretending they form a single resolved security-subject recipe. For a financial/company link, the page must have the appropriate validated native bridge. If the bridge is absent, show the industrial business by its source label and mark the company link unavailable. Do not repair that state by joining names, symbols, URLs, or model embeddings.

At least one validated industrial-to-company navigation path in each proof set is mandatory for B. The financial pane itself may retain the native Earnings issuer/event subject. A complete K1 cross-owner security recipe remains refused until K1 accepts a real bridge interface; B does not weaken that contract.

The new composition response is a bounded, derived transport object, not a new fact database. Each section preserves its native object identity, revision, source clocks, rights/coverage result and typed subject. Its generation identifies the selected tuple of owner revisions and the composition definition; it does not imply every owner was observed at the same instant. Durable projections, where necessary, use existing approved publisher facilities and remain rebuildable derivatives, never independent truth.

## 5. Shared industrial assertion requirements

B extends the Robotics-proposed optional payload under native GMI evidence rather than creating a semiconductor ledger. The working name `curation_assertion` remains a proposed shared field, not a present contract. Freeze the exact wire name/version with the incumbent owner in the implementation plan. A closed, versioned payload must round-trip through schema, native column serialization, writer, reader and K1 subtype binding. Legacy evidence without the optional payload remains byte-semantically unchanged. Changing the meaning of an existing field or native clock is not an additive change: use the shared owner's required major-version process rather than disguise it as an optional field.

Each reviewed assertion preserves:

| Field group | Required meaning |
|---|---|
| Identity and source | Native receipt ID and immutable reviewed assertion revision; upstream source identity, exact selector/locator, source vintage and lawful retention reference where available. |
| Source-local objects | Source-native label, object kind, manufacturer/model identifier when stated, generation/configuration, and stable local selector within the assertion. Unknown is explicit. |
| Predicate and mode | Exact relationship/observation type; catalog, announced, reported, target, derived calculation or attributed interpretation. Source truth and analyst interpretation are separate. |
| Scope | Product, process, application, business, facility/line, geography basis, fiscal/measurement period, conditions and commercial stage. |
| Quantity | Value/range, unit, currency, denominator, stock/flow, measurement basis, rounding and estimate status. |
| Evidence and reasoning | Supporting and contradicting native references, original lineage, reviewed mechanism, competing explanation, missing measurement and falsifier. |
| Time and corrections | Native publication/availability/recorded/effective/review clocks and target interval; correction/supersession predecessor and reason. |
| Admission and rights | Native review/disposition and rights-family binding; retention/access status. Extraction cannot ratify itself. |
| Optional resolution | Owner-issued company/security or future object mapping reference; absent mappings remain absent, not synthetic IDs. |

A source assertion describes what a source established, not a universal procurement fact. A recorded management target is an observed source statement with forward-looking content, not an observation that the target happened and not a newly originated Mastermind forecast. Review converts extraction into admitted house curation, not into omniscience. Two sources repeating one announcement retain one source lineage for dependence analysis; K1's declarative independence remains unverified unless its owner can establish stronger semantics.

The legacy evidence envelope and new upstream/business clocks must not be conflated. Under the Robotics proposal, a house-curation revision may be the source of an `operator_curation` receipt: envelope publication/effective dates then concern that curation publication, not the upstream business event. The new subtype binding must preserve the upstream source and business-effective clocks explicitly. If an accepted shared contract chooses another lawful envelope, all readers and clock bindings must agree before admission. No reused field silently changes meaning.

No known missing value becomes zero. An undated catalog has an observation date and an unknown publication date. A URL is not proof of immutable retention. A digest identifies bytes only when actually calculated; neither a generated hash nor this document grants source-retention rights.

## 6. The C-compatible foundations included in B

These are required semantics for B's own correctness, not speculative infrastructure:

1. **Immutable assertion references.** Use native receipt identity plus exact revision and local selector. A display-name change does not change what a historical reference meant.
2. **Source objects separate from global entities.** Two descriptions of a product are two evidence objects until an owner validates their relationship. A stable reference is not global product identity.
3. **Typed relationships and scoped roles.** Containment, process enablement, commercial arrangements, ownership and financial context are distinct. A company may have several roles without duplicate issuer truth.
4. **Explicit configuration and measures.** Store the conditions needed for future compatible comparison, rather than burying them in captions.
5. **Separate business and knowledge time.** Later mappings and corrections never become facts that the system knew earlier.
6. **Append-only correction and derivation lineage.** Explain exactly which claim, mapping or source invalidated a derived result. Do not replace history in place.
7. **Read through native owner interfaces.** UI panels do not depend on a particular private storage layout or implement their own identity/financial calculation rules.
8. **Rights and access at every projection.** Promotion into a graph never makes restricted bytes or relationships public.
9. **Evidence-linked consumer results.** The map and explanation refer to the same selected revisions. Future C queries can reuse those inputs rather than parse the prose again.
10. **Named migration acceptance tests.** Identity promotion, split, reversal, rights revocation and historical parity are specified now. The migration service is not built now.

B deliberately does not reserve arbitrary unused global IDs, create a `c_ready` truth flag, ship an empty universal registry, introduce a graph database, define an unrestricted `attributes` dictionary, build a general query language, or start a continuous entity-resolution worker. Future flexibility comes from explicit boundaries and preserved meaning, not from ungoverned extensibility.

## 7. Five industrial views, one evidence base

| View | Reader task | Design rule |
|---|---|---|
| Physical composition | Understand a named chip/package/system configuration. | Acyclic containment within that configuration; an assembly and its contained purchased parts cannot both count in one cost boundary. |
| Manufacturing dependencies | Understand what process/material/equipment capability enables production. | Process necessity is not a named procurement relationship. Catalog alternatives are not qualified substitutes. |
| Commercial relationships | See exactly what arrangement is documented. | Preserve product/voltage/process/site/contract scope, exclusivity only when stated, and announcement versus completion. Reciprocal roles are allowed. |
| Capacity and geography | See which available supply could serve the question. | Distinguish plans, installation, qualification, output, shipments and customer access; physical sites differ from headquarters and ownership. |
| Business and economic context | Explain who may capture the change and how. | Separate operating business, segment, consolidated issuer and security. Scope every revenue/cash/expectation comparison. |

The default map is unweighted. Width requires a supported comparable measure, explicit conversion and a non-overlapping aggregation boundary. Unknown capacity cannot become a thin line suggesting measured scarcity. Different wafer diameters, bits, stacks, packages, equipment revenue and installed cleanroom area cannot be summed.

The first view opens one selected neighborhood, initially capped at 40 visible objects and 80 relationships as a proposed interaction budget, not a measured performance claim. The synchronized table provides pagination for the remaining authorized results and says that the map is a partial view. Collapsing groups must preserve the accessible relation labels and visible coverage denominator. Rendering should use the existing design system and shared visualization components where available; a library choice is deferred to the implementation plan, not used to justify a new platform.

## 8. Capacity and economic reasoning

Capacity is a collection of scoped observations, not a single company status. The relevant dimensions include facility/line, wafer diameter, process, product/configuration, application, qualification evidence, commercial access, interval, output unit and denominator. Stages may overlap or regress; the design adds no universal qualification lifecycle.

A constraint card answers: what might be limiting, for which product/customer/time window, what supports that interpretation, which alternative could matter, what remains unknown, and what observation would show relief. It also shows the strongest competing explanation. Technical importance alone is not evidence of scarcity or pricing power.

B's default economic output is a reviewed mechanism, not an automatically quantified causal model:

`industrial change -> units/content/price/share/mix -> recognized revenue -> recurring profit -> cash/capital -> diluted per-share economics -> expectation context`

Each arrow names supporting evidence, scope and possible offsets. A company may gain a higher-value integrated product while another of its businesses loses displaced content. A positive industrial event can coexist with lower contribution due to price erosion. Neither outcome becomes a stock recommendation.

Any numerical derivation must use the existing accepted financial/calculation owner and a versioned definition with explicit input references. The page must not implement another formula engine. The research's toy cost and capacity examples remain clearly marked illustrations; they are not shipped as calibrated production forecasts. Unsupported calculations are unavailable while supported observations remain visible.

Revenue purity requires compatible numerator and denominator, ownership and fiscal period. Chip counts are not robot counts; supplier share is not portfolio weight; source confidence is not economic exposure. Issuer-defined cash flow and a derived cash measure are separately labeled. Current segment subtotals cannot be added to their components. Internal/captive foundry revenue is not merchant demand, and OSAT service revenue is not the value of the finished chip.

## 9. Management expectations, historical views and refusal

The expectation pane distinguishes prior management outlook, subsequent reported actual, and new management outlook. External consensus, house forecasts and market-incorporation evidence are separate optional native-owner sections. An unavailable external baseline does not invalidate management-history research, but a management-guidance comparison must never be labeled a consensus beat.

Compatibility requires the same measure, unit/currency, fiscal period/horizon, GAAP/non-GAAP basis, acquisition/divestiture perimeter, continuing-operations scope and applicable metric definition. Assumptions such as FX, tax, shares or excluded geographies remain visible. Where a change invalidates comparability, show both reported values but refuse an organic or like-for-like delta without a valid bridge. Preserve ranges; label arithmetic midpoints as derived rather than reported values.

There are three honest views:

- **Latest accepted evidence:** current admitted native revisions, with original source periods and review dates visible. It is not real-time universal coverage.
- **Source-history research:** reconstruct what sources had published by a cutoff using retained vintages, explicitly retrospective when our system recorded them later.
- **System historical replay:** only when native source-availability, recorded time, identity/mapping vintage and other required cutoffs support what the system actually knew then.

A historical report describing a prior-quarter event does not make that event known before publication. A date-only source and an intraday cutoff on that date are ambiguous unless an accepted owner provides an exact boundary; the consumer cannot assign midnight. Current-rule recomputation or hindsight-corrected views must not be described as original historical replay.

Current GMI issuer resolution is not historical issuer lineage (N04). A future C mapping learned after the selected cutoff cannot be used in system replay. Where permitted, the UI can offer a separately labeled retrospective identity view; it must show the newer mapping vintage and not overwrite the original result.

The current financial packet's CIK requirement (N07) limits that particular native path. Foreign/private operating businesses can still appear as source-scoped industrial evidence. They do not receive a made-up CIK or guessed listing. Extension of financial entity coverage belongs to the financial/identity owners, not to a semiconductor-side exception.

## 10. Reader experience and machine-consumer contract

The existing Theme board remains the overview. Add a semiconductor research entry using the shared component, showing available research slices, dated coverage and one accepted material change. Do not recalculate incumbent thesis or timing states. The shared detail page adds a Research section without cloning the shell.

A selected slice opens with four concise elements: **what changed; why it matters economically; what could offset it; what evidence is missing or next**. Facts, issuer targets and house interpretation are visibly distinguished. The reader can move to company/business roles, select a graph view, inspect a constraint, and open the exact evidence drawer. A source-link list alone is not the intelligence.

The company section keeps industrial relevance separate from investment attractiveness. Each business row explains inclusion and the supporting relationship. Public/private/unresolved businesses are distinguishable; native security links appear only with correct binding. No research coverage number becomes a buy score.

The evidence drawer shows publisher, document/locator, assertion mode, source/recording/effective dates, configuration, unit/denominator, revision and limitations. It offers only short lawful excerpts or original paraphrase. A restricted document need not be downloadable to make an authorized assertion understandable. A logged-out user must not obtain the private claim through an evidence pointer, export or alternate route.

The logical read request contains an existing theme key, a versioned research-slice selection, selected view, time mode and applicable cutoffs; pagination is bounded and the same owner revision tuple is retained across pages. The implementation plan freezes the exact endpoint and wire names only after current route/interface reconciliation. This design authorizes one adjacent read-only composition surface within the existing API, not a second backend or browser-side internet fetch.

Selection of slice, view and time mode may travel through approved non-sensitive URL parameters and existing context mechanisms. Opaque private assertion IDs and user-private research state do not belong in public URLs or referrers without owner approval. The page does not create a new saved-research database; deliberate saving remains with the existing user-state owner.

Desktop and mobile consume the same results. Mobile prioritizes summary and table, with an optional graph. English/Chinese labels preserve canonical terms and conditions rather than creating separate calculations. All selections and the drawer support keyboard use and focus return. The implementation must test long labels, missing translations, restricted records, 320/390/768/1440-pixel viewports, both theme modes and no page-wide horizontal overflow.

An existing machine consumer may receive the same bounded owner-reference composition, with all rank/gate/size/originate/entry authority false. It must not scrape rendered prose as truth or interpret a graph path as a validated forecast. No new agent ingress or automatic research-to-trade pipeline is introduced.

## 11. Degradation that remains useful

Required sections are the selected slice's supported industrial facts, a reviewed mechanism and counterargument, exact evidence access within rights, plus the positive linked company/economic tasks in both proof sets. Optional numerical estimates, unrelated financial entities, Street consensus, house forecasts and causal market attribution can degrade independently.

| Situation | Reader result | Prohibited shortcut |
|---|---|---|
| Missing yield or allocation | Show supported start/shipments and the missing measurement; withhold the yield-dependent estimate. | Delete the known event or fill missing yield with zero. |
| Unresolved company/security link | Keep source-attributed industrial role and label unresolved link. | Guess a ticker or borrow the parent's security. |
| Unsupported K1 cross-type join | Show separately typed native blocks and an explicit composition limit. | Claim a resolved unified recipe from a declared bridge name. |
| No admitted historic consensus | Show management history and consensus unavailable. | Backfill today's snapshot or treat guidance as Street consensus. |
| Accounting/perimeter mismatch | Display both source values with the reason comparison is refused. | Publish a raw subtraction labeled organic growth. |
| Rights revoked | Stop serving the prohibited payload and derived disclosures; return a bounded status that does not reveal protected content. | Continue serving cached bytes because the historic receipt allowed them. |
| Missing private GMI binding | Keep development/test artifacts inert and block live admission. | Store full-fidelity records in public Git or a new emergency bucket. |
| Stale accepted source | Show its period and review status; distinguish historical usefulness from current coverage. | Restamp the source with page-build time. |

Refreshing a section does not combine its new values with old explanatory text invisibly. Pin the contributing revisions. If an owner changes mid-composition, use the still-valid pinned tuple or return section-level stale/refusal; no incoherent mixture may be called a coherent snapshot.

## 12. Rights, private storage and publication

The shared GMI extension must have a proven approved private storage/publication binding before real full-fidelity admission. Existing evidence storage being reusable does not make public Git appropriate. N09 proves an Earnings private transport pattern exists in source; it does not prove that GMI currently has the necessary private binding or rights grant.

The implementation owner must bind the incumbent GMI writer/reader to an approved private artifact path and prove that public projections exclude protected bodies and structure. This must stay under existing GMI and private-retention/publication owners. If that cannot be done lawfully, the live-admission lane returns to the architecture owner; it cannot invent a second evidence store or weaken privacy.

Source rights and paid-product entitlement are separate checks. Permission to read a webpage is not permission to redistribute a dataset. Labeling a model paraphrase house-authored cannot launder upstream restrictions. Current rights must govern every emission, including a historical view. Historic rights snapshots remain audit evidence, not an enduring permission grant.

Authentication and feature entitlement precede private data access. Responses and errors use the existing private/no-store, authorization-varying and noindex patterns. No full payload in public HTML, Git/Pages/R2 mirrors, source maps, service-worker caches, localStorage, IndexedDB, analytics or logs. Public shells may contain deliberately approved editorial examples only. Anonymous counts, hidden labels and query errors must not leak the existence of private relationships.

The implementation must demonstrate rights revocation in a warm process, not just after restart. N08 caches its registry; the owning rights mechanism must supply a safe refresh/revision boundary or the release remains blocked. Do not add a second rights watcher. Logout/account changes must remove private client state and prevent cross-user cache reuse. Historical source removal follows native rights/retention law; retain permitted lineage/tombstones rather than claiming unrestricted permanent retention.

## 13. Refresh, extraction and learning

Use existing source ingestion, review/probation, nightly admission and publication owners. No semiconductor crawler-at-view-time, cron service, duplicate curation queue or watcher is introduced. A producer receives the relevant changed-source or scheduled-refresh inputs through existing mechanisms. Deterministic selection and calculation stay deterministic; model extraction and synthesis are attributable and reviewable.

When a source changes, the native owner appends its new vintage and correction relationship. Dependent assertions, blocks and explanations are marked for recomputation through existing owners. Where automatic dependency traversal is not yet supported, bounded operator review is the explicit method; no consumer silently invents a dependency engine. The implementation plan must identify the actual supported return/refresh path rather than claiming autonomy from a diagram.

Publication must not allow a changed numerical observation to retain a stale causal explanation. If recomputation is unavailable, show the source change and mark the interpretation stale. A pending unreviewed extraction cannot replace accepted evidence.

Learning first measures whether readers and existing machine consumers complete the named tasks, whether unsupported joins/attributions are avoided, and which questions remain unanswered. Use existing analytics/evaluation facilities and authorized metadata; do not log private bodies. Preserve specific corrections and rejected inferences so later research benefits from them. Any predictive evaluation or trade-policy promotion belongs to the accepted evaluation/forecast/decision owners and is outside B.

## 14. Evolution toward C: earned capability, not a rewrite

C has three later increments. Their contracts and implementation plans are separate future reviews; this specification commits B to compatibility requirements, not to their code.

| Increment | Newly useful task | Required native-owner extension | Entry evidence |
|---|---|---|---|
| C1 — validated shared objects | Find the same product/process/facility across documents and themes without merging look-alikes. | Accepted object identities and mapping lineage under the existing identity/industrial owners. | B accepted; repeated cross-document task is demonstrably limited by unresolved objects; reviewed mapping gold set and rights are available. |
| C2 — qualified relationship queries | Explore eligible alternative routes or shared dependencies across several sourced relationships. | Existing graph/relationship owner supports scoped, temporal, rights-aware queries and explicitly incomplete answers. | C1 mapping quality/coverage is adequate for the selected task; relation composition rules and point-in-time tests pass. |
| C3 — quantified scenarios where justified | Estimate a scoped change in usable output or economic sensitivity using accepted inputs. | Extend the existing scenario/relationship and financial/evaluation owners, not a new forecasting plane. | Compatible measurements and validation exist; named decision-support gain exceeds the simpler descriptive baseline. |

C1 maps a source-local reference to an owner-issued identity; it does not replace the assertion. Different mappings may apply to different configurations, effective periods or knowledge vintages. A later split or correction appends new mapping decisions and identifies affected derived views. Exact identity, variant-of, part-of and broader/narrower product-family relationships are not interchangeable mapping claims. A campus and a line, or two product generations, must not become one entity merely because the source uses the same name. Unknown relationship remains unknown; language similarity cannot settle it.

Promotion protocol: preserve the B source objects and exact original answers; admit mapping evidence through the owner; evaluate old and candidate projections at explicit cutoffs; explain each intended answer change; validate rights and identity semantics; publish via the incumbent owner only after review. Rollback changes the active derived projection to a previously accepted revision. It does not delete evidence or pretend an effect never occurred.

**Migration parity has two modes.** With the same inputs, mapping version and definition, unchanged B answers must remain identical. With newly accepted mappings, current answers may improve, but the delta must name its evidence and historical B answers must remain reproducible under their old cutoff. A blanket demand that every current answer stay unchanged would prevent legitimate learning; a blanket permission to rewrite history would destroy it.

C does not gain transitive certainty from connected lines. Two plausible relations need not compose into a valid procurement chain; two suppliers can share a hidden upstream; disclosure incompleteness prevents a complete negative answer. Query results need an included/excluded/unknown coverage statement and original references, not just a graph traversal result.

C proceeds only after B production acceptance and an approved next task with a specific user benefit. A globally complete census is not required to start a scoped C increment, but a partial graph must never claim global completeness. Pause an increment when false entity merges, privacy risk or weak task benefit outweigh the gain. Broader industry coverage within B can continue independently.

## 15. Delivery dependency map and cost discipline

This is architectural sequencing, not the executable implementation plan or a worker commission.

| Boundary | Capability unlocked | Gate before advancing |
|---|---|---|
| Shared assertion and private binding | Retain and retrieve a real structured industrial claim lawfully. | GMI schema/persistence/clock extension accepted with Robotics owner; private retention/publication and current rights proven. |
| Industrial dossier | Reader explains a specific product/process/milestone with exact evidence. | Native source/object and company-link semantics; shared shell integration and negative-state behavior. |
| Economic and management-history composition | Reader distinguishes industrial relevance from issuer economics and compares compatible guidance vintages. | Correct native identities, accepted owner objects, time/perimeter compatibility; unsupported cross-owner recipes refused. |
| Two proof sets and regression | One reusable experience works for HBM/packaging and SiC/GaN/specialty manufacturing. | Real production input to visible result, source corrections and access tests, unchanged incumbent market outputs. |
| C1 and later | Broader shared-object/query capabilities. | Accepted B plus section 14's task and validation gates. |

Fable's later principal responsibilities are integration architecture, difficult source/rights/collision decisions, coherent work sequencing, review adjudication and final proof. Routine engineering and checks should use the least-scarce capable admitted worker. Neither this document nor its intended recipient establishes worker placement, START, an Executive attempt or a recurring watcher. No worker must repeat the foundational research; packets should reference exact approved artifacts and unresolved questions.

Do not open separate semiconductor owners for storage, identity, corrections, schedules, retry or auth because a worker prefers an easier implementation. Do not make an empty C abstraction a prerequisite for B. Acceptance is measured in usable tasks, not source count, node count, lines of infrastructure or elapsed compute time.

## 16. Acceptance specification

All SBD requirements below are **future product/migration acceptance specifications**, not executed tests. The prior research's domain-specific examples remain applicable; this table is the release-critical consolidation, not a claim that every previous check was rerun. The B implementation plan must map the 48 B requirements to concrete tests/owners and map the retained witness regressions. The eight C1 requirements are future promotion gates, not implementation tasks or prerequisites for B; a later C plan owns them.

| ID | Stage | Discriminating requirement |
|---|---|---|
| SBD-01 | B | Theme board leads to the existing semiconductor detail and a populated research slice, without a replacement shell. |
| SBD-02 | B | HBM proof set shows configuration, distinct milestone, source and a usable business/economic explanation. |
| SBD-03 | B | SiC/GaN/specialty proof set shows the same workflow without AI-specific field assumptions. |
| SBD-04 | B | Each proof set contains at least one validated company navigation and a real management-outlook/actual/new-outlook sequence. |
| SBD-05 | B | Map, table, explanation and drawer resolve to the same selected native revisions. |
| SBD-06 | B | A source-only private or foreign business remains useful without a guessed security or fabricated CIK. |
| SBD-07 | B | One company can participate in several research slices; no live constituents or rankings change. |
| SBD-08 | B | Supported facts, issuer targets, derived calculations and house interpretation have distinguishable labels. |
| SBD-09 | B | Optional industrial assertion survives schema, native columns, write/read round-trip and subtype clock projection. |
| SBD-10 | B | Legacy receipts without the optional field retain their meaning and reader behavior. |
| SBD-11 | B | Stable source-local selectors do not mint global physical-object IDs or misuse theme/company node kinds. |
| SBD-12 | B | Catalog capability, documented inclusion, agreement and shipment cannot substitute for each other. |
| SBD-13 | B | Sampled and volume configurations remain distinct; an adjacent release does not transfer stage or wafer origin. |
| SBD-14 | B | Physical containment, process enablement and reciprocal commercial roles are separately represented. |
| SBD-15 | B | Parent assembly and contained components cannot both contribute to one purchase-boundary total. |
| SBD-16 | B | Mixed wafer diameters, output/shipments, period-end run rates and unlike output units remain distinguishable. |
| SBD-17 | B | Upstream publication, business-effective, source-available, recorded and house-curation clocks survive without renaming. |
| SBD-18 | B | A target does not become achieved because its date passes; new evidence can advance a supported milestone. |
| SBD-19 | B | Date-only versus intraday same-day cutoffs refuse unsupported precision rather than assign midnight. |
| SBD-20 | B | Retrospective source-history and actual system historical replay are visibly different modes. |
| SBD-21 | B | Current issuer identity is not used as historical ownership lineage without an accepted historical bridge. |
| SBD-22 | B | Correction appends a new revision and invalidates dependent explanation without overwriting its predecessor. |
| SBD-23 | B | A new observation cannot be silently paired with an old causal summary under one coherent generation label. |
| SBD-24 | B | Syndicated/counterpart reports preserve shared lineage; distinct URLs do not certify independence. |
| SBD-25 | B | Management guidance is never relabeled external consensus or a Mastermind forecast. |
| SBD-26 | B | Acquisition/perimeter, GAAP/non-GAAP, fiscal horizon and definition mismatches refuse unsupported comparable deltas. |
| SBD-27 | B | Arithmetic midpoint is marked derived; range and rounding remain accessible. |
| SBD-28 | B | Segment totals, parent/NCI attribution, internal foundry and OSAT service revenue retain their economic scope. |
| SBD-29 | B | Incentives, customer advances, asset transfers and operating cash measures are not conflated with recurring profit. |
| SBD-30 | B | Research confidence, chip counts and semantic relevance cannot become revenue purity or portfolio weights. |
| SBD-31 | B | Missing yield/allocation refuses dependent estimates while leaving the known operating event visible. |
| SBD-32 | B | A K1 native block cannot become a unified security recipe without supported subject/bridge proof. |
| SBD-33 | B | Private data reads follow authentication and entitlement checks, including malformed-path and error cases. |
| SBD-34 | B | Real GMI assertion admission waits for an approved private owner binding; public evidence staging contains no protected payload. |
| SBD-35 | B | Revoking source rights in a warm process prevents later prohibited emissions; old row snapshots do not authorize them. |
| SBD-36 | B | Logout/account switching clears private client state and prevents cross-user cache reuse. |
| SBD-37 | B | Public mirrors, page source, source maps, browser storage, logs and analytics expose no current full-fidelity private dossier. |
| SBD-38 | B | Counts, labels, pointers and error differences do not disclose restricted relationship existence. |
| SBD-39 | B | Historical viewing uses current emission rights; restricted-source lineage follows native retention policy. |
| SBD-40 | B | Refresh and review use existing writers/schedulers; request-time reads cannot self-admit claims or spawn a new worker. |
| SBD-41 | C1 | Promoting two source objects to one validated product preserves both original assertions and their locators. |
| SBD-42 | C1 | Same product label with conflicting manufacturer/configuration is not auto-merged. |
| SBD-43 | C1 | A later mapping split appends new decisions, identifies impacted views and preserves old source references. |
| SBD-44 | C1 | A mapping learned after a historical system cutoff cannot change the answer at that cutoff. |
| SBD-45 | C1 | Identical inputs/mapping/definition reproduce B's prior answer; intended current changes carry explicit mapping evidence. |
| SBD-46 | C1 | Mapping rollback restores a previously accepted projection without deleting evidence or changing rights. |
| SBD-47 | C1 | Cross-theme identity reuse does not merge different configurations or duplicate a joint-venture facility. |
| SBD-48 | C1 | Restricted source relationships remain restricted after entity promotion, merging, splitting and query projection. |
| SBD-49 | B | Keyboard, focus return, small screens, long labels, EN/ZH and both theme modes work on the real shared routes. |
| SBD-50 | B | Map limits and pagination expose partial coverage; an incomplete neighborhood is not labeled a complete supply chain. |
| SBD-51 | B | Frozen same-input comparisons preserve incumbent recommendations, entries, member order and missing-coverage output. |
| SBD-52 | B | A real admitted source revision reaches the authorized visible reader; candidate files or fixtures alone do not pass. |
| SBD-53 | B | Both proof sets pass real source-to-company-to-economics tasks and their essential negative cases before B acceptance. |
| SBD-54 | B | Existing-owner loss, rights change and source correction produce honest stale/degraded/refused results without public fallback. |
| SBD-55 | B | Every machine-facing rank/gate/size/originate/entry authority stays false; research is not an automatic trade input. |
| SBD-56 | B | B ships with no C registry, new global-object rows, second graph store or autonomous resolver; C's later gate is explicit. |

## 17. Retained research witnesses and source provenance

The five-installment corpus remains the evidence foundation. This design is not a new primary-source sweep or an assertion that every research entry has completed native admission. Source review depth, rights, mirror limitations and unresolved measurements stay with the exact source records.

All paths below are relative to `research/semiconductors/` in Macro. The immutable research head `f69026264debb265877076a442c7d9211d251fdc` contains all nine artifacts; individual publication revisions are preserved in the cumulative owner record.

| Ref | Artifact | Witnesses carried into B |
|---|---|---|
| R01 | `SEMICONDUCTOR_RESEARCH_FOUNDATION_2026-09-23.md` | HBM generation/configuration milestones, CoWoS variants, material/substrate distinction, source-scoped role versus procurement. |
| R02 | `RESEARCH_QA_AND_RELATIONSHIP_EXAMPLES_2026-09-23.md` | Named versus category-only relationships and evidence-review limitations. |
| R03 | `PROCESS_MATERIALS_EDA_RESEARCH_2026-09-23.md` | Manufacturing-route dependencies, scoped EDA certification, license/royalty and asset-perimeter distinctions. |
| R04 | `APPLICATIONS_CYCLES_ECONOMIC_CAPTURE_2026-09-23.md` | Reference design versus actual OEM BOM, inventory/price/mix, cash definitions and accounting scopes. |
| R05 | `QUALIFIED_CAPACITY_COMPETITIVE_ECONOMICS_2026-09-23.md` | UMC denominator recovery, qualification/site scope, shared facility and product-specific relationships. |
| R06 | `CAPACITY_SCENARIOS_BASKETS_AND_PROOF_REQUIREMENTS_2026-09-23.md` | Later ST operations evidence superseding older target-only knowledge, Hua Hong denominator/NCI, incomplete route calculations and hypothesis tests. |
| R07 | `BUSINESS_MODELS_EXPECTATIONS_AND_RERATING_2026-09-23.md` | Business archetypes, management versus external/house expectations, economic offsets and definition/perimeter conditions. |
| R08 | `POINT_IN_TIME_EXPECTATION_REPLAY_AND_OWNER_BOUNDARY_2026-09-23.md` | Six guidance-history cases; especially Cadence acquisition-perimeter refusal and different source/system cutoffs. |
| R09 | `SEMICONDUCTOR_RESEARCH_SYNTHESIS_AND_DESIGN_INPUTS_2026-09-23.md` | Faceted business taxonomy including captive manufacturing, integrated divisions and OSATs; shared user job and original A/B/C alternatives. |

The first production dataset must be assembled from rights-admitted primary sources through native owners, not loaded blindly from research Markdown or portable JSON. Exact source clauses and applicable fiscal periods must be rechecked when constructing production witness inputs. No additional public factual or numerical forecast claim is made by the design itself.

## 18. Open implementation gates, not hidden assumptions

| Gate | Owner and required proof | What can proceed without it |
|---|---|---|
| Shared industrial payload | GMI/Robotics owner accepts the one native extension, serialization and subtype clocks. | Written design review and bounded fixture-based semantic tests; no live native admission. |
| Private binding and current rights | GMI plus existing retention/publication/rights owners prove the approved path and warm-process revocation. | Source research and inert design work; no paid-payload publication. |
| Actual financial/guidance coverage | Earnings/financial owners provide accepted real objects for both witness issuers and preserve metric/time scope. | Industrial explanation work; cannot claim full B if both economic proof paths remain empty. |
| Native identity links | Company/security and Earnings owners provide the correct current/historical bridge for the selected task. | Source-only evidence remains visible; required B positive links still need proof. |
| Shared consumer custody | Current template/F04 and affected source owners reconcile the planned change surface. | Path-disjoint documentation; no competing template edits. |
| Written-spec approval | Chairman reviews this artifact. | Corrections and targeted design research; no executable implementation plan or product code yet. |
| C task/evidence gate | After accepted B, appropriate owner approves a scoped shared-object/query benefit with migration tests. | B release, coverage improvements and ordinary source updates. |

No gate is solved by creating a duplicate authority. No one missing optional datum stops unrelated research. Conversely, a real private-publication or required identity failure cannot be hidden behind a polished screen.

## 19. Review and next action

This document selects the architecture and defines its boundaries, user behavior, required semantics, proof and evolution conditions. It is not the command-by-command implementation plan. The next artifact after written-spec approval is the executable B implementation plan with then-current path custody, native contract decisions, test mapping, bounded rollout and production-proof responsibilities.

Before that plan: self-review this exact specification for contradictions, unresolved owner claims, missing negative cases and hidden C dependencies. Present it to the Chairman for written-spec approval. Fable receives the mature research, accepted written design and reviewed implementation plan only afterward; it is not commissioned by this document.

**MISSION_COMPLETE: false. Written specification submitted for review; no production or C acceptance is claimed.**
