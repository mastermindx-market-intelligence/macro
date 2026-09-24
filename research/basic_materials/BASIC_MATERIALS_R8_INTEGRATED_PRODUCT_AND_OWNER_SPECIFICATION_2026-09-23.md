# Basic Materials Theme Intelligence
## R8 — Integrated product, owner interfaces and the first economic dossier

**Research record date:** 2026-09-23  
**Operation:** `gmi-basic-materials-research-20260923-sol-001`  
**Carrier:** Macro #7796, `sol/basic-materials-research-20260923`  
**Status:** Principal-authored design proposal and integration specification for review. Not an accepted native contract, implementation, deployed product, global census or calibrated stock-selection model.  
**Mission complete:** false. Fable is the intended eventual integration principal; no receiver assignment, delivery, ACK or START is asserted.

## 1. Product decision and the user job

R1–R7 should become an economic research workflow, not seven unrelated reports, a larger ticker taxonomy or a replacement theme engine. The selected design is a **mechanism-first Materials dossier composed from existing owners**. Its recurring question is: what changed; which business or financial claim captures it; how does the change enter retained cash and per-share value; what was already expected; and what evidence would change the interpretation?

The investor should be able to enter from the existing Theme Tracker or relevant sector/detail route, understand an economic change, identify source-supported company exposure, inspect the financial or operating bridge, and return to the existing stock/watchlist workflow. The machine should preserve the exact subject, material form, economic role, measurement basis, clocks, correction lineage, rights and authority. Neither persona is served by a beautiful map that mistakes rising input costs for pricing power, or by an elaborate evidence receipt without a useful explanation.

The full-scale ambition remains proactive, economically informed discovery across the Materials complex and relevant US, China, Hong Kong, Canada and other global exposures. The first release is deliberately bounded, but its semantics must accommodate that ambition. Global breadth, forecast qualification and decision admission are later obligations, not silently discarded requirements.

The minimum first useful result is a paid, read-only **Materials Economics** section within the existing dossier grammar. It must explain four real cases across fertilizers, battery materials, precious-metal contractual rights and forestry cash, including a new-announcement/non-supersession case and honest missingness. It must not rank those unlike businesses against one another. Completion requires approved original evidence traversing the real owner/private-publication path into a visible, usable page; a schema, fixture or unconnected page does not complete it.

### Alternatives and why this design wins

A monolithic Materials score/engine would be easy to market but would combine incomparable economics and duplicate current theme, identity, evidence and decision owners. It is rejected. Independently enhanced pages for each industry would preserve the current fragmentation and inconsistent definitions; they are rejected as the integration architecture. An owner-preserving dossier with shared explanatory grammar and industry-specific models is selected. It costs more interface discipline up front, but allows heterogeneous evidence, narrow capability releases and independent owner evolution without turning a source-specific measure into a universal score.

The strongest objection is the dependence on sparse public disclosures and unfinished native bindings. The response is not to create substitute IDs or inferred numbers. The design preserves useful source-only research while withholding unsupported joins and calculations. Its first real cases are small enough to prove the path before scaling. Later evidence must demonstrate that the extra detail improves decisions or workflow over simpler baselines.

## 2. What has been verified about the current system

Current protected procedure was recovered at Mastermind `a7d2b3049e5cdc523e91e61a6e9d70a1cb911157`, Skillpack1.0.1/bootstrap1. Fresh bounded reads confirmed the same procedure fully read in R7. The current interface-read pin is Macro `9438880952d3375b00a042381705c2e6c85305e3`. This does not rebase the incumbent research branch or requalify deployment. R1–R7 remain immutable research evidence on #7796, whose entry head was `9c23a96d4b2f14cd443fb327eeeef3f88cbbdbb8`.

| Existing owner/interface at the R8 pin | Verified source capability | Important limit for this design |
|---|---|---|
| Shared STSI design | Owner-preserving federation, existing page hierarchy, separate dimensions and typed disagreements | A written architecture is not proof every producer is live |
| `engine/theme_graph/store.py` and evidence schema | Append-only receipts, fixed columns, nightly write discipline and graph-native identity | The closed receipt has no `curation_assertion` payload; an arbitrary added field is rejected by the schema and is not in the store column list |
| `engine/theme_graph/identity_resolution.py` | Existing bridge to Data OS issuer/security/listing identity, with current/historical distinction | Source-native symbol is provenance only; a resolved security does not guarantee a resolved issuer |
| `contracts/evidence_foundation/README.md` and vocabulary | Pointer-only refs, blocks and recipes; native subjects and clocks; all-false decision authority | Current compiler contract has no validated cross-type bridge-object input; native evidence IDs cannot be disguised as security IDs |
| FIF raw ledger and financial packet | Source-bound raw fact and governed query/packet kernels | Kernel/parser/fixture presence is not a live storage adapter, real issuer coverage or permission to synthesize XBRL facts from a press release |
| `engine/market_ontology/exposure_map.py` | Existing research-display-only F04 projection from owner reads | No new magnitude ordering, score, weight or inferred shock-to-theme causality; its identity ordering remains unchanged |
| `scripts/build_state_of_themes.py` | Existing Theme Tracker renderer and stable route | It is not a Materials metric owner; no page-local recalculation or new publisher |
| `app/earnings.py` | Authenticate then enforce `site_full(always=True)` before private reads; private/no-store errors and responses | Existing Earnings namespace is not a generic container for unrelated Materials records |
| Earnings private publication / Research Vault | Immutable objects, verified readback and receipt-bound pointer promotion through an existing private store | Materials still needs an accepted GMI/F04 binding; existence of infrastructure does not prove this binding or its production configuration |

The existing Robotics specification at reference head `f10211657c6c31df3c9af73cd4b9484e2dd7690a` proposes a shared optional native curation assertion, clock subtype and private admission. Its document blob is `d248fd1b4c9b48df8f5c95c3bdd742c2a8ef7007`. That is a design dependency, not evidence the extension landed. Materials must consume or contribute through that owner rather than create a second curation format. This R8 operation does not change #7773 or its receiver/custody.

**Capability conclusion:** the explanatory product is `SPEC_ONLY`; useful identity, reference, calculation and private-transport source exists, but the chosen real-source Materials path is not production-proven. No production connector, admitted record or accepted financial/security join has been demonstrated by these reads.

## 3. One ontology, several independent questions

The ten navigation families from R1 remain useful: base/industrial metals; ferrous materials; precious metals; battery/strategic materials; construction/industrial minerals; commodity chemicals; specialty/functional materials; industrial gases; fertilizers/crop inputs; and forest products/packaging. They are **research navigation families**, not ten new canonical GMI themes or an exclusive sector classification.

Within those families, R2–R7 supply role-specific cohorts. The integrated model should not flatten copper concentrate production, refining, fabrication and streaming into one exposure. Nor should it create duplicate global material objects because graphite appears in both battery and industrial applications. Resolve accepted entities through current owners; retain unadmitted product/business descriptions in their source namespace.

### Object distinctions that must survive

A structural sector or industry is supplied by its roster/taxonomy owner. A canonical theme is an accepted GMI narrative identity. A source-local subtheme preserves its source's own identity and rights; similar labels do not create a canonical crosswalk. A research facet is a bounded descriptive filter in this product, not a new market state or graph node. A basket is an admitted measurement universe with its own membership and weighting. A business, asset or product is source-scoped until its existing identity owner supports stronger identity. An issuer, security and listing remain separate even when a familiar ticker appears in all three conversations. A royalty or stream is an economic right and not a second physical producer.

For example, Weyerhaeuser can be relevant to a Materials research view without this project changing its structural sector classification. A company can appear in several application views without multiplying its sales or turning overlap into independent evidence. Research labels must not silently change existing price-basket membership.

### Eight reusable economic lenses

1. **Demand and usable supply:** application units, intensity, quality, deliverability and inventory boundaries.
2. **Realized unit economics:** comparable prices, input costs, fees, co-products and contractual timing.
3. **Physical productivity and commercial acceptance:** recovery, reliability, qualification, throughput and actual sales.
4. **Contractual value capture:** ownership, payability, ongoing payments, thresholds, covered volumes and obligations.
5. **Cash conversion and funding:** working capital, maintenance/growth investment, available funding and financial claims.
6. **Local competition and product mix:** feasible delivered alternatives, specification, geography, freight and comparable populations.
7. **Durability and reinvestment:** customer value, retention, competition and returns on additional capital.
8. **Expectation and security expression:** the correct prior information set and separately owned valuation, leadership and entry context.

These lenses consolidate repeated questions across the family studies. They are not eight scores, universal lifecycle stages or a new producer of ThemeState. A lens can be unavailable, descriptive, scenario-based or supported by a native measured series. Coverage in one lens never silently fills another.

### Company exposure as measurements, not one percentage

Preserve reported revenue/profit exposure, attributable production, economic ownership, contract receipts, scenario sensitivities and statistical return sensitivity separately. Every value needs numerator, denominator, period, currency, consolidation basis, method and source. Undisclosed exposure remains unknown. A parent segment and its internal inputs do not both count as external revenue. A source statement about qualification does not establish financial materiality.

Historical exposure uses the ownership, listing, contract and membership that existed in the admissible information set. Current-membership or current-rule recomputations must be labelled as such rather than called historical replay. The first release does not implement new basket weighting or a global asset master.

## 4. First-release proof set and targeted source closure

R8 rechecked five original HTML documents, rather than replaying the family crawls. The selected public sources are short analytical proof material, not a retained private production dataset. Their source periods and publication dates remain distinct from this research date.

| Case | Required useful output | What it must not imply |
|---|---|---|
| Nutrien Q2 2026 manufactured phosphate | Explain the difference between a higher reported blended selling price and lower reported unit gross margin | Fertilizer-only pricing, global phosphate profitability or a stock recommendation |
| NOVONIX September 9 qualification report | Keep customer testing and internal testing separate; show conditional future sales separately | 12/14 becomes 86% qualification, success probability or current sellable capacity |
| NOVONIX September 16 ACP announcement | Describe an announced nonbinding collaboration as a separate proposition | A newer company announcement proves the older customer specification issue has been resolved |
| Wheaton/BHP Antamina closing | Describe source-reported payable participation, ongoing payment and delivery threshold | Mine ownership/control, duplicate physical supply, a fully verified current legal contract or a modeled investment return |
| Weyerhaeuser Q2 2026 cash/FAD | Show operating cash less total capital spending beside the issuer's separately adjusted distribution metric | Growth spending did not consume cash or adjusted FAD is automatically sustainable free cash flow |
| AMS and Conch historical missingness cases | Clearly show unavailable version-bound quote or China quantitative comparison and the exact next evidence needed | Stale numbers are current, zero exposure, no Chinese opportunity, or complete global coverage |

Nutrien's selected table is manufactured product across fertilizer, industrial and feed uses. It reports selling price 781 versus 714, cost 812 versus 646 and gross margin -31 versus 68 US dollars per product tonne for Q2 2026 versus Q2 2025. The comparison is not its entire consolidated margin or a pure DAP quotation. [E01]

NOVONIX's September9 release reports customer testing meeting 12/14 parameters, unlike its internal all-parameter result. The September16 document is explicitly a nonbinding MOU for collaboration with ACP Technologies. This targeted new source **does not supersede the customer-test proposition merely because it is later**. It is not evidence that no later qualification update exists anywhere. [E02–E03]

Wheaton's April1 closing release reports an initial 33.75% payable-silver share, a fixed 90% payable factor, a 100-million-ounce threshold before the share becomes 22.5%, a US$4.3bn upfront payment and 20%-of-spot ongoing payments. The proof case is an attributed summary of that source, not legal-contract completeness or a claim about the threshold's current remaining balance. [E04]

Weyerhaeuser reports 399m USD operating cash, 139m capital expenditures and 323m adjusted FAD after 63m of adjustments for Q2. The source identifies the specified growth-facility capital. Displaying 260m cash after all reported capex beside adjusted FAD explains the boundary rather than declaring one figure false. [E05]

Martin Marietta's original-page R8 fetch failed. Its R7 case remains historical research evidence but is not required for the first successful-source proof set. This is a selection decision, not deletion of the original research or a claim that the issuer source is globally unavailable. The earlier AMS version mismatch and Conch image limitation are retained without another identical failed crawl.

The first production acceptance requires all four issuer subjects above to have their admitted source-native records and correct reader behavior; the two NOVONIX documents are two different propositions for the same issuer. Missingness examples supplement rather than replace that positive evidence. No exact Data OS IDs, native curation IDs, source-retention hashes or publication receipts have been invented in the manifest.

## 5. Route each claim to the owner that can preserve its meaning

### Formal financial observations

Where a governed metric and valid filing-package occurrence already exist, FIF remains the financial measurement owner. Use its declared query, vintage and formula semantics. A press-release unit cost or non-GAAP metric cannot be transformed into a fictional XBRL occurrence merely to obtain a familiar financial ID. A parser listed in the vocabulary does not fetch or prove a real packet. The implementer must identify the actual admitted occurrence/packet and physical reader, or declare the block unavailable.

### Source-specific operating, financial-definition and business claims

Use the shared GMI curation-assertion design for reviewed source-attributed claims that have no applicable formal native metric, including qualification statements, contract descriptions and issuer-defined non-GAAP measures. Do not create a second Materials assertion field or put opaque JSON inside `source_ref`. The shared extension must survive the closed schema, native serialization, fixed-column store and readers before any real payload is admitted.

A measure already owned by FIF should be referenced rather than recopied as a competing authoritative fact. A source-specific curation observation can explain its different definition but must retain that distinction. Curation review accepts a source-bound interpretation; it does not certify the underlying company's engineering or accounting as independently audited by Mastermind.

### Deterministic explanations and scenarios

A derived subtraction or bridge is a bounded consumer projection with explicit inputs, formula version, comparison key and arithmetic basis. It is not a new raw fact, new global metric catalog or implicit rewrite of an issuer measure. Reuse an existing governed formula when applicable. For the first slice, permit only explicitly reviewed small formulas over accepted inputs; do not install a general code-execution service or accept model-authored executable expressions.

Hypothetical scenarios have visibly separate assumptions and results. They cannot replace missing reported data, flow into current ThemeState or be cited as independent evidence. Probability and calibrated expected return require actual evaluation receipts from the appropriate owner and are absent in the first release.

### Meaningful owner boundary

GMI continues to own semantic/topology and approved curation evidence. Data OS owns issuer/security/listing identity. FIF and Earnings retain their native financial and event objects. K1 owns reference validation, not the bodies. F04 owns downstream display composition and retains its no-ranking restrictions. Existing publication, rights and API owners handle retention and access. Existing ThemeState/sector/entry owners retain their verdicts. Evaluation owns the qualification of new predictive use. No R8 file creates another control plane or source-of-truth catalog.

## 6. The two-layer identity design

The current GMI bridge can provide resolved securities while leaving issuer identity unresolved. Therefore `RESOLVED` must be interpreted using the exact native axes, not as permission to bind every business claim to a corporate group. The source-native symbol is not a fallback join key. Cross-listing, ADR, share-class, ownership and effective-date differences remain material.

The first layer is a **source-native research block**. It can truthfully display a publisher-attributed business name, the original proposition, its scope and evidence without claiming a canonical company/security association.

The second layer is **company/security-linked navigation and composition**. It requires the proper source-to-issuer and issuer/security resolution receipts and compatible time scope. A human-recognizable ticker or a JSON declaration naming a bridge is insufficient. Without that evidence, the source block remains useful but stock metrics and portfolio relevance remain unavailable.

K1 currently cannot consume validated cross-type bridge objects in recipe compilation. R8 does not solve this by relabeling evidence subjects as securities. Independently valid blocks may appear as clearly separated research sections, each with its own identity and receipts. A unified company recipe remains refused/degraded until its actual bridge contract and compiler input are accepted and exercised.

This distinction must be visible. The page cannot look like a fully validated joined result while hiding an `identity_unresolved` receipt below it. No late join or browser ticker matching may erase the refusal. The first release's source-only behavior is necessary resilience; full release acceptance still requires lawful company links for the selected admitted cases.

## 7. Measurement and comparison contract

Before a calculation, bind the exact measure, subject/asset, material form, period, currency, unit, scale, numerator/denominator, gross/net and consolidation basis, source method, stock/flow state and relevant exclusions. Not every comparison needs every field, but every economically material field must be known and compatible or explicitly represented as a scenario assumption.

A generic equality of unit strings is insufficient: USD/tonne of concentrate, USD/tonne of a standardized grade and USD/tonne of payable content are different. A growth percentage based on revenue is not a physical-volume change. A reported cost after credits is not the pre-credit physical cost. A contractual percent of payable output is not a percent of ownership. Capital backlog is not annual sales. CFO after working capital cannot have working capital deducted a second time.

The selected Nutrien comparison permits two period-specific unit-margin subtractions from the same source table and their difference because the comparison table gives a common manufactured-product basis and periods. It does not authorize reconstruction of the entire segment margin from one blended price. The Weyerhaeuser bridge presents two labelled views; it does not force adjusted FAD into a generic FCF definition.

Published precision is retained. A difference between rounded components and a published total remains a residual unless the original source resolves it. An unresolved economic perimeter is not automatically rounding. Mathematical success and semantic eligibility must be reported independently.

For missingness, distinguish a measured zero, an observed false predicate, no disclosure, invalid units, stale evidence, unresolved identity, rights blocked and technical unavailability. Unknown must not become a default neutral reading. A missing Chinese issuer comparison is not zero Chinese exposure. Coverage denominators describe the chosen cohort and eligible inputs, not the entire Materials universe by inference.

## 8. Clocks, corrections and proposition-level freshness

Preserve source publication, first availability/observation, system retention, business-valid time, measurement period, forecast horizon, curation publication, model/build time and review due where the owner supports them. A date-only value remains date-only. Do not invent midnight UTC or a filing acceptance time from the file's modified date.

The proposed shared curation envelope identifies publication of the house assertion. Its upstream source and business clocks are separate. A new envelope date cannot make an old economic observation current. The subtype's K1 binding must expose those clocks without repurposing the original vocabulary; version evolution follows the existing contract rules.

Freshness attaches to a proposition, not just an issuer or URL. The September16 NOVONIX MOU should update the relevant collaboration proposition. It does not refresh the September9 customer test, retire it or prove its completion. A revised fiscal comparison can supersede the relevant measure without erasing a separate contract or operating fact in the same document.

Correction is append-and-recompile through existing owners. It names exact predecessors, preserves both source vintages and invalidates affected derived outputs. Reopening a source page is not a new independent observation. K1's dependence annotations are declarative/unverified; R8 does not add automatic deduplication or count repeated URLs as independent confirmation.

The product should display latest accepted evidence **for each applicable horizon**, not claim every fact is live today. A currently unreviewed or stale block remains historically inspectable where rights permit, but it cannot lead a current conclusion without its limitations being obvious.

## 9. Privacy, retention and production publication

The existing private Research Vault substrate and Earnings transport demonstrate a reusable infrastructure direction, not authorization to put Materials into an Earnings record schema. The current GMI evidence parquet path and closed schema must be reconciled with the intended private payload. No live premium assertion body or full source document belongs in public Git, generated site JSON, source maps, service-worker storage, localStorage or IndexedDB.

The source/evidence/publication owners must accept the precise retained object class and binding. Source bytes, extraction, curation, deterministic view and page projection remain distinguishable; there is no second latest-state store. Existing private staging, immutable object readback and promotion discipline should be reused through an accepted extension. Do not create a Materials bucket, publication daemon or competing manifest service to bypass the missing binding.

Authenticate before opening private objects, then enforce the paid entitlement using the incumbent policy even when a global paywall is in observe mode. Preserve private/no-store, Vary, noindex/noarchive and nosniff behavior on successes and errors. Object keys and credentials never become browser URLs. Malformed routes must not expose unguarded alternative paths, cacheable errors or storage details.

Current rights are checked by the source-family authority at read/publication time; mint-time booleans are not permanent permission. Unknown rights remain an admission blocker. A revocation must remove the current display through the existing owner path while preserving any history legally retainable. A Research Vault credential or a publicly readable issuer page does not itself grant broader redistribution rights.

The first release must prove the exact original-input generation and deployed code revision. Source acceptance, private promotion, API success, visible output and user acceptance are distinct. No autonomous refreshing behavior is claimed until a proven existing producer/return path is bound.

## 10. Shared user experience and useful output

Retain `state_of_themes.html` and existing sector, basket and stock routes. Materials is a research section/facet within the shared hierarchy, not a competing landing page or a reclassification of every issuer. Exact placement follows the accepted neighboring template; this specification does not invent a second global header, palette or layout system.

The glance view answers what changed, why it matters and what evidence comes next. Its information hierarchy should be:

1. An original concise economic explanation, with source period and proposition type.
2. The specific business role and material/product scope.
3. A small labelled bridge or table when quantities are comparable.
4. The chief counterargument or unavailable requirement.
5. Source and lawful company/stock navigation.

For Nutrien, the glance should say that higher reported blended prices did not offset the measured cost increase for the stated product scope. For NOVONIX, it should distinguish customer-test progress from final acceptance and keep the newer MOU separate. Wheaton should show the nature and boundaries of the cash right. Weyerhaeuser should explain why adjusted distribution cash differs from operating cash after all stated capital spending.

Use source drawers for original context, clocks, definitions, rights, residuals and correction lineage. Preserve a user's filter and return route without storing private response bodies in browser persistence. On mobile, use stacked labelled comparisons and a reachable source control instead of compressing a wide spreadsheet. Keyboard and screen-reader flows must expose the same interpretation; color cannot be the only carrier of positive/negative or missing meaning.

Dark and light must each preserve hierarchy, readable financial signs and unavailable states using the incumbent design system's distinct treatments. Desktop/mobile, EN/ZH, dark/light and permitted/denied evidence states all belong in acceptance. This is content/interaction specification, not a claim to have supplied reviewed visual mockups or browser proof.

Existing owner conclusions appear as separately labelled dimensions. Economic thesis, material cycle and entry quality may disagree for legitimate scope or horizon reasons. Use the existing conflict grammar, rather than a new all-purpose verdict. Do not classify price and profit as a genuine contradiction merely because their directions differ; they are different measured dimensions.

The existing F04 exposure map's ordering remains identity-based. Research facets do not authorize ordering by a newly invented economic magnitude or attractiveness score. A separate future research-priority policy must be accepted by the existing decision owner before use. Proactive delivery should reuse existing brief/watchlist/publisher workflows when admitted, not create a Materials watcher. It may convey accepted changes without implying an entry or trade.

## 11. Descriptive, scenario and predictive products are different releases

**Descriptive release:** source-backed operating/financial comparisons, business roles, bounded explanations and explicit change conditions. It does not estimate outperformance probabilities or publish a new buy label. This is the first production capability.

**Scenario release:** explicit assumptions, methods and ranges over appropriately bound data. It asks conditional questions and reports sensitivity. It must not fill missing facts, conceal funding assumptions or reuse a hypothetical output as market evidence. A scenario can be useful without a fitted probability.

**Predictive qualification:** separately declared target, horizon, cohort, admissible information set, baselines and outcomes. Model salience, a plausible causal narrative, source count and arithmetic correctness are not demonstrated forecasting skill. Qualification remains with Evaluation and relevant domain owners.

**Decision integration:** accepted candidate context or a model output may eventually be consumed by Prophet under its owner-approved contract and proven evaluation. Research priority, forecast confidence, candidacy, entry, sizing and portfolio execution remain separate. No R8 component directly originates or sizes trades.

This sequencing does not reduce the ambition to documentation. It makes each useful capability observable and prevents an unvalidated research heuristic from becoming trade authority merely because it is displayed beside a stock.

## 12. Evaluation design and falsification

Evaluate semantic correctness first. Can the system reproduce the selected source's scope, avoid the known false inference, expose the right missing state and preserve previous versions? The research contract probe in this packet is narrow: it checks the current evidence schema against synthetic legacy and extended rows. It is not a store, API or application test.

Next evaluate workflow. A reviewer should complete the journey from theme context to company/evidence explanation without relying on the chat. Record whether the source and calculation support the prose, whether the next observation is actionable as a research question, and whether uncertainty is visible. A reviewer should distinguish the September9 test result from the September16 MOU without inferring commercial qualification.

Forecast studies need predeclared targets. Examples include the next comparable unit-margin change, a dated commercial milestone, realized cash conversion or subsequent relative stock return. Do not mix them into one success rate. Compare role-aware features to simple commodity/sector, last-period and existing momentum baselines appropriate to the target. Use source-vintage cutoffs, restatement handling, issuer/listing survival and liquidity constraints. Preserve abstentions and coverage rather than computing performance only on conveniently complete survivors.

Use blocked time splits and source/issuer families that prevent one report or repeated issuer event from leaking into both training and evaluation. Any statistical significance, calibration or confidence interval must be computed from the actual study rather than assigned in advance. Prospective shadow output is needed before a new decision-bearing use can be accepted. More research fields are justified only if they improve explanation, workflow or out-of-sample utility after their maintenance cost.

Natural-event proof must be distinguished from a historical replay or synthetic correction injection. A deliberate fixture correction can test lineage. It does not prove the live source feed recognized a real correction. The final evidence packet should label each proof accordingly.

## 13. Bounded delivery sequence with named capabilities

### V0 — Source-to-dossier economic explanation

Deliver the selected four-issuer proof set plus missingness behavior through existing owners, shared UI and private transport. The vertical includes accepted source retention, typed shared curation or applicable financial references, permitted deterministic comparisons, identity-aware navigation, visible explanations, tests and production/browser proof. Do not split it into infrastructure-only PRs whose combined product path is never accepted.

Prerequisites are explicit below; lawful source/specification work can proceed while a deployment dependency remains held. The research branch stays research-only. Actual implementation uses the current owner-assigned carrier after fresh custody and effect reconciliation; it must not reopen a conflicting writer merely because a historical PR is old.

### V1 — Comparisons and changes at the correct scope

Add proposition-level changes, native correction consumption, comparable company cohorts and the most important regional/material distinctions. Preserve non-PIT labels where historical membership is absent. Use the current shared template and native query owners, not a new comparative database. Prove one real corrected or newly published source changes only the relevant dossier fields.

### V2 — Conditional economics and valuation

Add selected calculation/scenario modules after their numeric, dimensional, accounting and assumption contracts are accepted. Start with the existing researched examples rather than a universal discounted-cash-flow system. Prove assumptions cannot be mistaken for reported values and missing critical inputs refuse rather than fabricate a result.

### V3 — Economically informed proactive discovery

Qualify target-specific research prioritization or forecast features with the existing Evaluation owner, then deliver through current briefs, watchlists and Prophet consumers. Prove the receiving workflow uses the admitted context and preserves decision boundaries. Ranking/entry policy changes require their own accepted evidence and do not inherit authority from V0.

### V4 — Breadth and durable learning

Expand US/China/HK/Canada/global issuer, asset, process, customer and contract coverage by the value of the missing economic question. Add measured outcome feedback under existing owners, not another learning store. A coverage score is descriptive and denominator-bound; it is not an investment confidence score.

Each release retains source costs, failed or unavailable observations, supersession and review obligations. There is no fixed promise about duration, unlimited provider spend or autonomous continuation between chat turns.

## 14. Dependency and gap decisions

| Gap | Why it matters | First-release disposition and exact resolution |
|---|---|---|
| Shared GMI curation schema/store/subtype | Closed current receipt cannot carry the required source-scoped measurements | Required: consume the accepted Robotics/shared owner extension; round-trip real claims and preserve subtype clocks. Do not create a second field |
| Private GMI/F04 publication binding | Existing infrastructure does not admit this payload automatically | Required: current rights/publication owners bind retained objects and prove no public copy or alternative path |
| Real native source records | A URL and this research file are not approved retained input | Required for selected cases: immutable original, source selector, review and current rights receipts |
| Company/security navigation | Native evidence subject is not the same as a tradable security | Required for full selected-case acceptance: actual source-to-issuer and existing Data OS/GMI resolution. Source-only fallback remains explicit |
| Unified K1 cross-type compilation | Current recipe refuses native-only/cross-type subjects | Do not fake it. Independent blocks may ship honestly; a unified recipe waits for its existing owner to accept and consume bridge inputs |
| FIF live coverage | Kernel and fixture do not establish issuer/metric availability | Optional to the curation-based first explanation when no formal metric is claimed; required before displaying a FIF-derived metric |
| Shared-template placement | Parallel source custody and visual review remain separate | Required before UI edits: reconcile the exact accepted template/current writer; supply dual-theme/locale/viewport proof |
| Broad China and global numeric coverage | Current family research is uneven and some originals were unavailable | Visible gap, not a V0 blocker to the four admitted cases; no global-completeness claim; prioritize source closure for selected next cohorts |
| Full individual contract/legal terms | Announcement does not prove all current conditions | Restrict V0 to attributed dated summary; financial valuation of the right waits for complete relevant terms |
| Forecast/candidate admission | Narrative quality does not prove prediction | Held beyond descriptive V0; define and pass owner-specific evaluation before any decision use |

An old PR number is navigation, not a live lease. This design does not prove current source custody or create an assignment for its intended Fable receiver. Refresh only the planned implementation paths and material dependencies when that step is authorized. Missing worker placement does not require giving routine research work back to the Chairman.

## 15. Thirty-two first-capability acceptance requirements

The following are specifications, not executed product tests. `R8_INTEGRATION_MANIFEST_2026-09-23.json` binds them to proof cases and dependency decisions.

- **BM-R8-01:** Sector, canonical theme, source-local subtheme, facet and basket identities remain distinct.
- **BM-R8-02:** Descriptive Materials membership never changes a structural sector or live basket.
- **BM-R8-03:** Company, issuer, security and listing links require the correct accepted identity axes.
- **BM-R8-04:** No ticker-equality or source-symbol fallback resolves an unsupported join.
- **BM-R8-05:** Existing closed native receipt rejects an unsupported extra assertion; accepted extension is explicitly versioned.
- **BM-R8-06:** The accepted assertion survives native storage/readback without dropped fields or legacy semantic changes.
- **BM-R8-07:** Formal financial facts remain with FIF when applicable; press-release data are not fictional XBRL occurrences.
- **BM-R8-08:** K1 references remain pointer-only and do not embed source/owner bodies.
- **BM-R8-09:** Native evidence subjects cannot impersonate security subjects in a recipe.
- **BM-R8-10:** Separate valid blocks never masquerade as one successfully joined company recipe.
- **BM-R8-11:** Prices/costs/quantities require matching economically material comparison scope.
- **BM-R8-12:** Reported precision and unresolved perimeter residuals are retained.
- **BM-R8-13:** Nutrien's chosen comparison retains blended manufactured-product, currency and period scope.
- **BM-R8-14:** NOVONIX internal testing, customer test and conditional future sales remain separate.
- **BM-R8-15:** The later nonbinding MOU does not supersede or resolve the customer-test proposition.
- **BM-R8-16:** Wheaton's contractual interest is not mine ownership or additional physical production.
- **BM-R8-17:** Weyerhaeuser's adjusted FAD does not erase growth capital paid in the period.
- **BM-R8-18:** Date, availability, retention, curation and forecast clocks remain lossless and grain-aware.
- **BM-R8-19:** Corrections append and invalidate only affected derived outputs with explicit predecessor lineage.
- **BM-R8-20:** A second URL or projection is not independently verified corroboration.
- **BM-R8-21:** Unknown, zero, false, stale, rights-blocked and unresolved-identity states remain distinguishable.
- **BM-R8-22:** AMS version mismatch and China quantitative gap do not become current values or zero exposure.
- **BM-R8-23:** Current source rights are checked independently of mint-time flags.
- **BM-R8-24:** Approved private source/assertion bodies cannot be recovered from public Git/site/cache/mirrors.
- **BM-R8-25:** Authentication and paid entitlement precede private-object reads, including malformed routes and errors.
- **BM-R8-26:** F04 identity ordering and research-display-only authority remain unchanged.
- **BM-R8-27:** Hypothetical assumptions and results are separated from reported evidence and cannot silently fill missing data.
- **BM-R8-28:** Historical replay uses supported native vintages and knowledge cutoffs, not today's membership or revisions.
- **BM-R8-29:** Existing recommendations, ranks, entries, sizes and portfolio outputs are unchanged on frozen inputs.
- **BM-R8-30:** The real deployed route completes source-to-explanation-to-lawful-company navigation for all selected positive cases.
- **BM-R8-31:** Desktop/mobile, EN/ZH, dark/light, keyboard and evidence-denial cases remain usable and semantically consistent.
- **BM-R8-32:** Exact code/input/private-publication receipts, independent review and required live/browser evidence are durable before acceptance.

## 16. Research verification and exit boundary

The accompanying manifest is a research planning artifact. It contains no invented native IDs or claimed live source bindings. A narrow local contract probe uses the exact pinned GMI evidence schema to check a synthetic legacy row, an unsupported assertion field, a missing publication value and extra financial fields. These tests demonstrate the current contract boundary; they do not prove store, K1, API or production behavior. Separate manifest checks cover path/digest references, requirement IDs, proof-case roles, explicit missingness and all-false decision/native-admission flags.

R8 establishes an integrated design, not final accepted implementation readiness. The next bounded unit must close the shared curation/private-binding/identity contract decisions for V0 and freeze executable paths and tests with the actual owners. It should update this specification where necessary rather than write another generic economic survey. Routine labor can then be packaged for the least-scarce capable workers under Fable's eventual integration responsibility, once actual delivery and START occur.

The parent remains incomplete. No deployed Materials result, real-source admission, independent design acceptance, forecast advantage or Fable pickup is claimed. Current research progress belongs to #7796 and the cumulative Agent OS handoff, not to the survival of this chat.

## 17. Source and interface register

### Targeted public originals (R8 rechecked)

**E01:** Nutrien, Q2 2026 release, August5. Phosphate manufactured-product table; Q2 versus prior-year period; USD/product tonne. https://www.nutrien.com/news/press-releases/nutrien-reports-second-quarter-2026-results-1753

**E02:** NOVONIX, customer-test update, September9. Opening test paragraphs and conditional sales expectation. https://www.novonixgroup.com/news/lead-customer-feedback-marks-progress-in-qualification/

**E03:** NOVONIX/ACP, September16 nonbinding MOU. Opening paragraph and proposed collaboration scope. A separate proposition from E02, not proof of customer acceptance. https://www.novonixgroup.com/news/novonix-and-acp-technologies-partner-to-strengthen-domestic-supply-chain-for-battery-grade-anode-materials/

**E04:** Wheaton, Antamina stream closing, April1. Source-reported transaction and payment/threshold terms. Current full legal terms and remaining threshold balance are not verified by this release. https://www.wheatonpm.com/news/news-details/2026/Wheaton-Precious-Metals-Announces-Closing-of-Silver-Stream-with-BHP-on-Antamina/default.aspx

**E05:** Weyerhaeuser, Q2 2026 release dated July30, original SEC exhibit. Adjusted FAD reconciliation and footnote. Exact SEC acceptance timestamp was not captured. https://www.sec.gov/Archives/edgar/data/106535/000119312526326124/wy-ex99_1.htm

Public readability is not a source-retention receipt, an independent verification of management statements or blanket redistribution permission. R8 intentionally uses concise original analysis rather than reproducing reports. Earlier source registers retain their scope and failed-access limits.

### Current implementation-interface references

All current references below use Macro `9438880952d3375b00a042381705c2e6c85305e3`, not a moving default branch.

- STSI design `docs/superpowers/specs/2026-09-20-sector-theme-subtheme-intelligence-system-design.md`, blob `d3bb8a03d4e571a058a499bd35a1a94c7c8e8971`.
- `engine/theme_graph/store.py`, blob `63b58860d35bd183c947c85088f83bd53359bb9f`.
- `contracts/theme_graph/evidence.v1.schema.json`, blob `83dece15e98b9c8775a584afcd6ee09811dad220`.
- `engine/theme_graph/identity_resolution.py`, blob `8eefa1c2f5e5d3514f6487bf869f154ce2751011`.
- `contracts/evidence_foundation/README.md`, blob `a47e898309813636cf167c517492aa569aa296ca`; selected bindings in `vocabulary.v1.json` inspected at the same pin.
- `engine/fundamental_forensics/raw_ledger.py`, blob `42ccf3ff0e58ed33d91d9868a5db7b01814c04f5`.
- `engine/fundamental_forensics/financial_intelligence_packet.py`, blob `99fb3da6920d0804dbb9a3b36609826b78a38ee4`.
- `engine/market_ontology/exposure_map.py`, blob `d383419c0814ec90bb0a84335fcbaaa8ca0db39c`.
- `scripts/build_state_of_themes.py`, blob `dfdd260552e9ada447963ed42ff02ffbc88e9a89`.
- `app/earnings.py`, blob `3b8251388c8e9ae59b933212a7384faaea61eb27`.
- `engine/earnings_narrative/private_publication.py`, blob `0ee93909693893f419f0109f9eba1994d94e2b46`.

The historical Robotics design is separately pinned in section2. Search results returned an indexed revision different from current main; they were navigation only. A guessed `scripts/build_sectors.py` path returned404 and is not included as an owner. A container raw-source download failed DNS before writing; GitHub connector reads supplied the actual source evidence. No current UI placement, source custody or deployed runtime state is inferred from search snippets.
