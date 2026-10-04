# Commission 4 — Effective-Dated Economic Exposure & Supply-Chain Graph

**Date:** 2026-10-04  
**Commission type:** Research / architecture only  
**Implementation authority:** NONE — this report does not authorize production code, live-pipeline modification, data purchase, portfolio behavior, trading behavior, or new source-decision authority.

## Source and repository receipts

Protected Mastermind source law was re-pinned immediately before publication:

- Mastermind: mastermindx-market-intelligence/Mastermind@84df29801d4078724c2b603a136de5aa1532cdfe
- Skillpack: mastermind.sol_skillpack.v1, version 1.0.1, bootstrap-major 1 compatible
- Required procedures loaded from that same protected commit:
  - docs/sol_skills/INDEX.md
  - docs/sol_skills/ACTIVE_EXECUTION.md
  - docs/sol_skills/SESSION_RELIABILITY.md

Research archaeology was performed against:

- Mastermind research pin: 03f7ca04cd5b0a3abf7166221dd77d403c7f95df
- Macro research pin: 1b4edfb438f7ff7edca5097f0c90243a49207d1e
- Terminal research pin: fb6f5cc39e592e7f9967835a85617b4fef427b09

Before publication, Macro main was rechecked at df5d4acb8703b0a36c25571611c7411553bb4217. The ten commits after the research pin did not modify the graph/K3-D/F04/identity/economic-propagation source surfaces used for this report; the only path match in the bounded compare was an unrelated Options Alpha recovery workstream.

Resolved repository identities:

- Core Mastermind: mastermindx-market-intelligence/Mastermind
- Macro / Neural Web / Theme Graph / Research Vault: mastermindx-market-intelligence/macro
- Terminal / charting: mastermindx-market-intelligence/mastermind-terminal

Research Vault is a Macro subsystem under engine/research_vault rather than a separate canonical repository.

---

# A. Executive conclusion

## Recommendation

Mastermind should ultimately have an **effective-dated economic relationship intelligence system**, but it should **not** be implemented as a new all-owning “Economic Graph” database.

The correct architecture has three layers.

### Layer 1 — native evidence and fact owners

SEC filings, government awards, physical shipment observations, mineral/energy statistics, company disclosures, licensed vendor records, Research Vault evidence, and specialist datasets retain their native provenance and canonical ownership.

### Layer 2 — Graph-1 economic relationship projection

A governed, effective-dated relationship view maps owner-backed facts into directional economic relationships such as:

- supplier → customer;
- product → component;
- company → facility;
- company/segment → end market;
- company → commodity;
- company/product → policy exposure;
- process/product → capacity constraint.

It may eventually be materialized for query performance, but it must remain a derivable, receipt-backed projection rather than a second source of truth.

### Layer 3 — hypothesis and decision consumers

K3-D Economic Propagation should compose Graph-1 with:

- Graph-2: fundamental, product, theme and narrative similarity;
- Graph-3: residual market behavior, participation and incorporation.

MarketOntology F04 should explain transmission and opportunity paths. Neural Web should distribute governed context. Portfolio V3 should consume evidence with independence accounting. None of these consumers should originate supplier/customer truth.

## Three-graph law

Mastermind should preserve the existing separation:

> **Graph 1:** why economic/fundamental transfer can occur.  
> **Graph 2:** why firms/products are comparable.  
> **Graph 3:** how the market is currently treating them.

This separation is load-bearing.

## Strategic importance

This is **P0 strategic infrastructure**, but P0 means:

- settle ownership;
- get point-in-time semantics correct;
- admit only high-precision relationship truth;
- preserve evidence receipts;
- prove independent predictive value.

It does **not** mean “buy the largest graph and ingest millions of edges.”

A trustworthy Graph-1 plane can improve:

- earnings read-through;
- government/policy impact mapping;
- commodity and capacity shock propagation;
- supplier/customer demand inference;
- bottleneck detection;
- theme/subtheme grounding;
- second-order news analysis;
- Research Vault usefulness;
- forward fundamental expectation updates;
- cross-company catalyst discovery;
- falsification of false thematic narratives.

Academic evidence supports real network propagation and delayed information diffusion:

- Cohen & Frazzini, “Economic Links and Predictable Returns,” Journal of Finance.
- Menzly & Ozbas, “Market Segmentation and Cross-Predictability of Returns,” Journal of Finance.
- Barrot & Sauvagnat, “Input Specificity and the Propagation of Idiosyncratic Shocks in Production Networks,” QJE.
- Carvalho et al., “Supply Chain Disruptions: Evidence from the Great East Japan Earthquake,” QJE.
- Acemoglu et al., “The Network Origins of Aggregate Fluctuations,” Econometrica.

These findings establish a strong research hypothesis. They do **not** establish that historical return alpha survives today. Mastermind must revalidate everything with contemporary point-in-time data and controls for the intelligence it already possesses.

## Central architectural ruling

**Do not resurrect standalone GMI W4.**

Current Macro contains a Chairman decision explicitly rejecting a standalone GMI W4 relationship graph. Current ownership is already partitioned:

- GMI Theme Graph → semantic/theme substrate and ThemeState;
- K3-D / Alpha Integration → Graph-1/2/3 propagation-hypothesis composition;
- MarketOntology F04 → transmission/opportunity/product composition;
- specialist owners → native facts.

The existing K3-D PR remains held/draft and its own evidence reports zero live role-specific Graph-1 rows sufficient for a normal positive real-data path.

The missing capability is therefore **role-specific Graph-1 economic relationship truth**, not another propagation engine.

---

# B. Current-state census

## B1. Macro Theme Graph is already a serious temporal graph substrate

Current Macro includes:

- contracts/theme_graph/**
- engine/theme_graph/**
- data/theme_graph/**
- config/theme_crosswalk.yml
- config/theme_sources.yml

The edge contract is append-only and bitemporal. It already distinguishes:

- valid/effective time;
- evidence time;
- belief time;
- computation generation;
- reconstruction versus observed eras;
- source/date provenance;
- evidence references;
- rights classes;
- contradictory evidence.

The edge vocabulary already reserves:

- SUPPLIES
- ENABLES
- BOTTLENECK_OF
- BENEFITS_FROM
- CATALYST_OF

It also reserves independent exposure dimensions:

- economic_share
- trading_beta
- attention_share

Those reserved fields do **not** mean an economic relationship graph is already live.

At the research pin, data/theme_graph/_meta.json reported roughly:

| Metric | Observed state |
|---|---:|
| Nodes | 3,882 |
| Append-only edge rows | 25,100 |
| Latest-belief edge rows | 12,863 |
| Evidence records | 22 |
| Identity-resolution rows | 2,807 |
| Capability rows | 644 |
| Measurement candidates | 505 |
| Semantic-only capabilities | 138 |
| Resolved identities | 2,376 |
| Finviz local subthemes | 268 |
| Finviz member edges | 2,365 |
| THS concepts | 375 |
| Canonical strategic themes | 18 |

Production materialization remains primarily semantic/membership:

- company → basket MEMBER_OF;
- basket/local-theme → canonical theme EXPRESSES;
- ETF → basket TRACKS;
- source-local theme/subtheme structures.

The graph deliberately refuses to manufacture unsupported company→theme or firm→firm economic relationships.

## B2. The economic-share gap is explicitly known

The W2 exposure-decomposition probe is highly relevant.

Its result was:

- economic_share: ABSTAIN / blocked on ingestion;
- no per-company segment/theme revenue source existed that could support a lawful formula;
- no formula was minted merely because the schema had a field.

That is correct behavior.

Trading beta is not economic exposure. Attention is not economic exposure. These dimensions must remain separate.

## B3. Three distinct graphs already exist as architecture

Prior research/economic_propagation work correctly separated:

### Graph 1 — economic relationship

Customer, supplier, partner, product, component, facility, geography, commodity, regulation, capacity, bottleneck and other cash-flow/physical dependencies.

### Graph 2 — fundamental/narrative similarity

Comparable businesses, products, KPIs, themes, filing similarity, peers and narrative exposure.

### Graph 3 — residual market behavior

Residual co-movement, participation, group lifecycle, sympathy, leadership and incorporation.

The three may join through a hypothesis object. They must not be flattened into one RELATED edge or opaque score.

## B4. K3-D is the correct hypothesis composer, not Graph-1 truth

The existing K3-D commission already freezes the correct scope:

- no fourth graph/store;
- no scalar propagation score;
- no customer/supplier inference from theme membership;
- no customer/supplier inference from sympathy or co-movement;
- no participation/breadth target-generation shortcut;
- no invented economic_share;
- exact identity required;
- typed abstention when Graph-1 evidence is absent.

Current PR macro#6514 remains open/draft/held.

Its current real-owner proof reports **zero live role-specific Graph-1 rows** sufficient for a fully populated positive path. Its positive case is synthetic; real cases often abstain.

That is the central missing capability this commission should address.

## B5. MarketOntology F04 is downstream composition

F04 already owns the explanation/product layer and distinguishes:

- LIVE_TRACE: owner-backed facts satisfying clocks, rights, correction and identity law;
- SCENARIO: explicit assumptions that do not mutate source truth.

It also correctly refuses arbitrary multiplication of hop coefficients or mixed-horizon effects.

F04 should consume Graph-1, not determine supplier/customer truth.

## B6. Neural Web is a cognitive/context bus

Mastermind already consumes Neural Web artifacts and can use graph/context contradictions as decision context.

Neural Web should distribute relationship paths, contradictions, uncertainty and propagation summaries after canonical owners establish them. It should not originate economic edges.

## B7. Current bottleneck logic is heuristic

Mastermind contains manually configured bottleneck chains and basket-relative logic.

Useful prior knowledge exists, but a future economic bottleneck layer should increasingly consume:

- dependency magnitude;
- specificity;
- substitutability;
- spare capacity;
- qualification lead time;
- inventory;
- alternate-source availability.

A bottleneck is usually a **state**, not a permanent company label.

## B8. Research Vault is an evidence corpus

Research Vault lives in Macro under engine/research_vault with analysis integration under engine/research_intelligence.

Its existing architecture already has useful integrity concepts:

- fail-closed authoritative reads;
- unavailable ≠ legitimately empty;
- producer clocks;
- freshness checks;
- explicit coverage;
- public-safe metadata separated from document bodies;
- grounded analysis persistence.

Institutional research can propose:

- relationship candidates;
- product/component mappings;
- capacity constraints;
- substitutes;
- exposure estimates.

Those claims should remain source-span-backed candidate evidence until an authorized relationship owner admits them.

## B9. No canonical firm relationship graph was found in Mastermind

The inspected Mastermind estate already has substantial:

- fundamentals;
- themes;
- news;
- macro;
- options;
- political/government evidence;
- institutional/fund data;
- earnings expectations;
- research synthesis;
- heuristic bottleneck chains.

No canonical effective-dated company/product/supplier/customer relationship authority was found in Mastermind itself.

Research-desk prose can reason about second- and third-order impacts, but prose reasoning is not relationship truth.

## B10. Observability itself has drift

Mastermind data/census/CENSUS.md at the protected research pin was generated on 2026-07-16, while Macro Theme Graph metadata was generated on 2026-10-03.

The future economic relationship plane should ship with freshness and coverage observability from day one.

---

# C. State-of-the-art research

## C1. Supply-chain edges can transmit real economic shocks

Barrot & Sauvagnat show economically meaningful customer effects from supplier disruptions, especially where inputs are specific.

Carvalho et al. show both upstream and downstream propagation through direct and indirect firm relationships after the Great East Japan Earthquake.

Acemoglu et al. show theoretically how input-output topology and higher-order dependencies can amplify micro shocks.

Implication:

**edge existence is insufficient.**

Propagation depends on:

- direction;
- magnitude;
- specificity;
- substitutability;
- concentration;
- inventory;
- capacity;
- qualification time;
- pass-through;
- geography;
- timing.

## C2. Linked-firm information has historically diffused imperfectly

Cohen & Frazzini found historically delayed incorporation of major-customer information into supplier prices.

Menzly & Ozbas found cross-predictability across supplier/customer industries, with weaker effects where analyst coverage and institutional ownership were greater.

Mastermind's stricter question should be:

> After controlling for sector, theme, market beta, news, expectations, options, revisions and macro, does point-in-time economic relationship evidence add independent predictive information?

## C3. Product competition belongs primarily in Graph-2

Hoberg-Phillips text-based network industries provide dynamic firm-specific competitor/product similarity sets from 10-K product descriptions.

That is valuable for:

- competitor discovery;
- substitute candidates;
- product-space similarity;
- competition intensity.

It remains Graph-2 unless separate evidence establishes an actual economic relationship.

A supplier disruption does not automatically benefit a competitor. Substitution requires:

- product compatibility;
- qualification;
- spare capacity;
- logistics/geography compatibility;
- correct timing;
- no shared upstream bottleneck.

## C4. Industry input-output tables are priors, not firm edges

BEA Input-Output data can provide:

- industry input intensity;
- direct/indirect requirement structure;
- macro propagation priors;
- coverage-gap diagnostics.

It must not be used to assert that Company X supplies Company Y.

## C5. Operational supply-chain platforms model richer entities

Modern commercial systems increasingly represent:

- legal entities;
- facilities;
- products;
- components;
- materials;
- shipments;
- ownership;
- nth-tier suppliers;
- substitutes;
- risk events.

Examples include S&P/Panjiva, Sayari, Altana, Interos, Everstream and Exiger.

But an operational current-state graph is not automatically appropriate for historical investment research. Historical point-in-time reconstruction, corrections and rights must be separately proven.

---

# D. Source landscape

| Source | Coverage | History | Latency | PIT quality | Corrections | Rights | Cost class | Best use |
|---|---|---|---|---|---|---|---|---|
| SEC EDGAR raw filings + APIs | U.S. public issuers | Decades; structured XBRL modern history | Seconds/minutes | **High if original receipts are archived** | Amendments/corrections/deletions | Public access subject to SEC automation policy | Free | P0 explicit counterparty/product/geography/major-customer evidence |
| Existing Macro filing/fundamental owners | Already-normalized issuer evidence | Existing-system dependent | Existing pipelines | Potentially high | Inherit native owner law | Existing rights | Existing | Prefer owner output over duplicate ingestion |
| USAspending / GovRev | Awards, transactions, recipients, agencies, subawards | Long federal history | Transactional | Medium-high with native clocks | Modifications/versioning | Public | Free | Government/program exposure; project through GovRev |
| BEA Input-Output | U.S. industry/commodity relationships | Long annual/benchmark vintages | Annual | High industry PIT, not firm PIT | Published vintages | Public | Free | Industry prior and propagation structure |
| Census International Trade | Product-country trade aggregates | 2010+ API depth | Monthly | High aggregate vintage if archived | Annual revisions | Public | Free | Product-country/geography physical context |
| BTS Freight Analysis Framework | Freight by region/commodity/mode | Multi-generation | Periodic | High coarse-grain PIT | Versioned | Public | Free | Logistics/geographic constraint priors |
| USGS Mineral Commodity Summaries | 90+ nonfuel minerals | Long annual history | Annual | High published-vintage PIT | Annual editions | Public/CC0 release | Free | Critical-mineral availability and import reliance |
| EIA Open Data | Power, generation, fuels, capability | Long, series-dependent | Hourly to monthly | Strong physical timestamps | Series revisions | Open API | Free | Power/fuel/capacity evidence |
| Open Supply Hub | Manufacturing facilities, sectors/products, parents | Contributor dependent | Variable | Medium | Contributor updates | API terms | Low-medium | Facility identity/enrichment, not complete public-company truth |
| Hoberg-Phillips TNIC | U.S. product similarity/competition | Annual historical network | Annual | Good Graph-2 PIT if tied to filing availability | Annual regeneration | Academic/research terms | Low | Competitor/substitute candidates and controls |
| S&P Business Relationships Analytics | Large disclosed + estimated supplier/customer universe | Marketplace advertises 2005+ | Vendor docs conflict on cadence | Vendor claims PIT | Must verify exact correction semantics | Commercial | Enterprise | Strong first commercial bake-off candidate |
| FactSet Revere Supply Chain | Customers/suppliers/competitors/partners | Legacy docs report 2003+ | Filing-driven | Current PIT semantics must be verified | Must verify | Commercial | Enterprise | Commercial bake-off candidate |
| LSEG Value Chains | Supplier/customer data + org IDs + freshness/confidence | Public history unclear | Current API | Historical PIT unclear | Update-date fields exist | Entitlement-specific | Enterprise | Cheap probe if already entitled; do not assume PIT |
| S&P Panjiva | Physical shipment records / company links | 2007+ | Source dependent | **Vendor Marketplace says Point In Time: No** | Source dependent | Commercial | Enterprise | Physical corroboration / forward shadow, not naive historical backfill |
| Sayari Graph | Global company/ownership/trade graph | Decade+ source corpus advertised | Continuous | Requires PIT validation | Source-specific | Commercial | Enterprise-high | Private-company identity/trade enrichment |
| Altana | Companies/facilities/products/shipments/value chains | Living graph | Continuous | Investment PIT not established | Living/inferred graph | Commercial | Enterprise-high | P2 multi-tier/product/facility work |
| Interos | Very large modeled company/interdependency graph | Commercial | Continuous | Unknown | Continuous | Commercial | Enterprise-high | Operational risk / deep-tier discovery |
| Everstream | Multi-tier company/facility/material event network | Commercial | Dynamic | Unknown | Dynamic | Commercial | Enterprise-high | Operational disruption overlay |
| Exiger | Parts/materials/specifications/BOM/supplier graph | Commercial | Dynamic | Unknown | Proprietary | Commercial | Enterprise-high | P2 defense/industrial BOM and alternate-supplier mapping |

## Vendor conclusion

Do **not** select a global vendor yet.

Recommended first commercial evaluation:

1. S&P Business Relationships Analytics;
2. current FactSet Revere Supply Chain;
3. LSEG Value Chains only if Mastermind already has a useful entitlement.

Panjiva can be valuable physical evidence, but its Marketplace description marks Point In Time as No; that is not sufficient for historical investment backfilling.

Altana/Sayari/Interos/Everstream/Exiger should be evaluated after P0/P1 prove consumer demand for private-company, facility, N-tier or BOM detail.

---

# E. Canonical data model

## E1. Contract first; graph database later

Do not begin by selecting Neo4j, TigerGraph or another graph database.

The canonical model should be:

source evidence → owner-native fact → normalized Graph-1 observation → effective-dated relationship state → derived path

A graph-serving layer is an implementation optimization, not the source of truth.

## E2. Identity model

Reuse existing canonical identities.

At minimum distinguish:

- Company
- Legal entity
- Security
- Business segment
- Product
- Component
- Facility
- End market
- Commodity
- Technology standard
- Capacity resource
- Policy/program

Company ≠ legal entity ≠ security ≠ facility ≠ product.

A shipment between subsidiaries does not automatically establish the same economic relation or magnitude between two listed parents.

## E3. Relationship taxonomy

Initial narrow directional vocabulary:

| Relation | Direction | Notes |
|---|---|---|
| SUPPLIES_TO | supplier → customer | Requires role-specific evidence |
| LICENSES_TO | licensor → licensee | Do not collapse into supplier |
| DISTRIBUTES_FOR | distributor → producer/principal | Preserve role |
| MANUFACTURES_FOR | manufacturer → brand/customer | Foundry/EMS/CDMO use |
| OPERATES_FACILITY | company → facility | Operation vs ownership stays distinct |
| PRODUCES_PRODUCT | company/facility → product | |
| USES_COMPONENT | product/company → component | |
| SELLS_IN_END_MARKET | company/segment/product → end market | |
| EXPOSED_TO_GEOGRAPHY | company/segment → geography | Keep revenue/assets/cost basis |
| EXPOSED_TO_COMMODITY | company/product → commodity | State input/output side |
| CAPEX_DEPENDS_ON | company/industry → product/resource | |
| DEPENDS_ON_STANDARD | product/company → standard | Evidence-backed only |
| SUBJECT_TO_POLICY | company/product → policy/program | |
| BENEFITS_FROM_POLICY | company/product → policy/program | State mechanism |
| BOTTLENECKED_BY | process/product → capacity/resource | Usually state-dependent |
| SUBSTITUTE_FOR | product/company → product/company | Requires substitution basis |
| COMPETES_WITH | company/product ↔ company/product | Usually Graph-2 unless economic evidence exists |

Do not persist mechanical inverse edges when they can be derived.

COMMON_CUSTOMER and COMMON_SUPPLIER should generally be derived paths, not independent source claims.

Never use generic RELATED as propagation evidence.

## E4. Minimum logical contracts

### economic_relation_observation/v1

One source-backed assertion.

Required semantic fields should include:

- observation_id;
- stable relationship key;
- source node reference;
- target node reference;
- relation type/direction;
- optional product/component/segment/facility references;
- claim basis;
- explicit versus inferred class;
- source receipt;
- source text span or structured coordinate;
- exact identity-resolution receipt;
- rights state;
- full temporal clocks;
- source revision;
- processing generation;
- correction lineage;
- extraction method/model version;
- quality dimensions.

Suggested claim-basis classes:

- issuer_disclosed;
- structured_government;
- shipment_observed;
- vendor_disclosed;
- vendor_estimated;
- research_report_proposed;
- model_proposed.

Only admitted evidence classes should create usable Graph-1 facts.

### economic_exposure_measure/v1

Relationship existence and magnitude must be separate.

Possible dimensions:

- supplier revenue share;
- customer revenue share;
- procurement share;
- COGS share;
- shipment value;
- shipment volume;
- capacity share;
- geography revenue share;
- commodity input intensity;
- capex dependency.

Fields should include:

- relationship/node reference;
- dimension;
- value or interval;
- unit/currency;
- numerator/denominator;
- period;
- basis;
- source receipt;
- formula ID if derived;
- estimate model/version if estimated;
- uncertainty;
- full clocks.

There should not be a generic weight = 0.63.

### economic_relation_state/v1

Resolved effective-dated view over admitted observations:

- relationship key;
- canonical source/target references;
- role/direction;
- effective_from/effective_to;
- known_at;
- belief_time;
- state = active | disputed | stale | superseded | unknown;
- corroborating receipts;
- contradictory receipts;
- source-family coverage;
- rights state.

Conflicting observations should coexist and be inspectable; do not average them into one confidence scalar.

### propagation_parameter/v1

Learn later from empirical evidence:

- mechanism;
- relation type;
- shock direction;
- operating-response direction;
- lag distribution;
- attenuation by hop;
- specificity/substitutability/spare-capacity buckets;
- sample size;
- uncertainty;
- regime;
- provenance.

### event_exposure_path/v1

Derived and normally ephemeral/cacheable:

event → source node → Graph-1 path → exposed target → operating mechanism

Carry:

- every edge receipt;
- hop count;
- first-/second-order classification;
- exposure dimensions;
- alternative explanations;
- common-cause controls;
- falsifiers;
- lag range;
- unavailable dimensions;
- zero automatic trading authority.

## E5. Temporal semantics

Every time-sensitive observation should distinguish:

### event_time
When the underlying event/transaction/shipment occurred or the economic reporting period applies.

### as_of
The research/query cutoff being reconstructed.

### observed_at
When Mastermind's collector first actually observed the source bytes.

### available_at / known_at
Earliest conservative time Mastermind could legally and technically use the observation.

### ingested_at
When the source entered its canonical owner.

### effective_from / effective_to
When the relationship was economically believed valid.

### discovered_at
When Mastermind first extracted or recognized the relationship.

### belief_time
When the corresponding Mastermind belief state became valid.

### source_revision
Native filing/amendment/version.

### processing_generation
Parser/model/formula generation.

### correction_generation
Append-only correction lineage.

Example:

A 10-K filed on 2026-02-20 may disclose that Customer X represented 18% of 2025 revenue.

It may support:

- effective_from = 2025-01-01

but absent earlier evidence:

- known_at >= 2026-02-20

A 2025 backtest may not use that relationship simply because the filing describes 2025.

The same rule applies to commercial vendor historical reconstructions.

## E6. Corrections must be append-only

A corrected source observation must not rewrite what Mastermind historically knew.

Current view:
- show corrected/superseding belief.

Historical view before correction:
- preserve original belief state.

## E7. Quality must stay multidimensional

Do not collapse data quality into confidence = 0.83.

Preserve separately:

- provenance tier;
- role explicitness;
- identity certainty;
- magnitude basis;
- freshness;
- corroboration;
- contradiction;
- rights;
- extraction method;
- adjudication status.

---

# F. Derived intelligence

## F1. Deterministic calculations before LLM reasoning

Calculate:

### Relationship concentration
- top-customer share;
- top-supplier share;
- customer/supplier HHI;
- single-source dependence.

### Economic exposure
- disclosed revenue dependency;
- procurement/COGS dependency;
- geographic exposure;
- commodity input intensity;
- facility/capacity concentration.

### Change
- new relationship;
- terminated relationship;
- magnitude change;
- expanding/declining shipment activity;
- changing concentration.

### Dependency state
- sole source / multi-source;
- viable alternate count;
- geographic co-concentration;
- common upstream dependency.

### Physical evidence
- shipment volume/value;
- plant capacity/utilization;
- power/mineral availability;
- freight/geographic constraints.

### Graph topology
- typed direct degree;
- first-/second-order reachable exposure;
- path concentration;
- bridge nodes;
- common suppliers/customers.

Graph centrality may be a research feature. It must not masquerade as economic exposure.

## F2. Bottleneck intelligence

A bottleneck is better represented by independent dimensions such as:

- dependency magnitude;
- input specificity;
- low substitutability;
- low spare capacity;
- long qualification/replenishment lag.

Do not immediately fuse them into a single bottleneck score.

## F3. Propagation mechanics

### Supply shock
supplier/facility/resource shock → downstream customer

Modulated by:

- procurement share;
- capacity share;
- specificity;
- inventory;
- alternates;
- pass-through;
- lead time.

### Demand shock
customer/end-market shock → upstream suppliers

Examples:

- hyperscaler capex revision;
- auto production;
- smartphone units;
- defense program awards;
- data-center buildout.

### Policy shock
policy → product/geography/program → company → counterparty

Do not jump directly from policy to ticker.

### Product/standard transition
standard/product shift → component requirement → capacity → producers → customers/substitutes

## F4. Second-order propagation

Default research traversal should probably stop at **two economic hops**.

Three-plus-hop propagation should remain special-case research until incremental value is proven.

For each path:

- block cycles;
- deduplicate economically equivalent paths;
- retain hop-specific evidence;
- expose common causes;
- expose competing explanations;
- attenuate uncertainty rather than multiplying arbitrary coefficients.

## F5. Substitution effects

A disrupted supplier can benefit an alternative only if Mastermind can establish:

1. product/economic substitutability;
2. qualification compatibility;
3. available capacity;
4. logistics/geographic compatibility;
5. compatible timing;
6. no shared upstream bottleneck.

This is where Graph-1 and Graph-2 deliberately meet without being fused.

## F6. Cheap LLM role

Cheap models are appropriate for:

- high-recall candidate extraction;
- document triage;
- product/component phrase extraction;
- candidate role/direction;
- end-market tagging;
- candidate contradiction pairing;
- ontology mapping;
- source-span discovery.

Every candidate must cite source coordinates.

A cheap model may not directly create an admitted Graph-1 relationship.

## F7. Frontier LLM role

Frontier models are appropriate for:

- ambiguous commercial disclosures;
- complicated filing clauses;
- product/component/BOM interpretation;
- policy-to-product mechanism reasoning;
- substitute-candidate generation;
- alternative explanations and falsifiers;
- multi-source research synthesis;
- user-facing explanation over governed facts.

They should not invent:

- counterparties;
- economic share;
- effective dates;
- identity mappings;
- edge confidence;
- trading recommendations.

---

# G. Mastermind integration map

| Producer | Canonical owner | Evidence family | Consumer |
|---|---|---|---|
| SEC/company disclosures | Existing filing/fundamental owner after P0 census | Graph-1 issuer-disclosed relationships/exposures | Graph-1 projection → K3-D → F04 → Mastermind |
| Government awards/transactions | GovRev | Government/program/company relations | Graph-1 projection → policy propagation |
| Research Vault | Research Vault + Research Intelligence | Source-span-backed relationship proposals | Adjudication/research; never automatic truth |
| GMI Theme Graph | GMI | Theme/subtheme semantic membership | Graph-2 context and target generation |
| Baskets/Group Reads | Existing group owner | Comparability/participation | Graph-2/Graph-3 controls |
| Market/price/options owners | Existing market owners | Residual-market evidence | Graph-3 / validation |
| BEA IO | Macro physical/economic source adapter | Industry priors | Graph-1 plausibility; not firm-edge originator |
| Census/BTS | Physical/trade owner | Product-country-region logistics | Propagation context |
| USGS/EIA | Commodity/physical owner | Commodity/capacity state | Bottleneck/event propagation |
| Licensed relationship vendor | Licensed source adapter | Disclosed/estimated Graph-1 observations | Projection + validation |
| Shipment provider | Physical-trade owner | Observed shipment evidence | Corroboration / current activity |
| Stock Identity / Data OS | Existing identity owner | Exact entity/security identity | All joins |
| Graph-1 projection | Derived non-authoritative view | Effective-dated economic relationships | K3-D / F04 / research / bottleneck |
| K3-D | Alpha Intelligence | Graph-1/2/3 propagation hypothesis | Research/decision context |
| MarketOntology F04 | MarketOntology | Explanation/transmission composition | UI/research |
| Neural Web | Existing cognitive bus | Condensed paths/contradictions | Mastermind Brain |
| Portfolio V3 | Existing portfolio owner | Independence-aware evidence use | Decision Snapshot / later decisions |

Key ownership law:

**Research Vault contributes evidence.  
GMI contributes themes.  
Native source adapters contribute relationship observations.  
K3-D composes hypotheses.  
F04 explains transmission.  
Neural Web distributes context.  
Portfolio V3 decides.**

No layer should silently become all of the others.

---

# H. Empirical validation program

## H1. Prove graph correctness before alpha

Build a stratified human-adjudicated gold set covering:

- customer;
- supplier;
- manufacturer;
- distributor;
- license;
- product/component;
- geography;
- commodity;
- facility;
- capacity/bottleneck.

Measure:

- entity-resolution precision;
- role precision;
- direction precision;
- effective-date correctness;
- known-at correctness;
- termination handling;
- correction replay;
- magnitude extraction error;
- false-edge rate.

Any automatic admission path should preregister a high precision floor. A candidate first gate is **≥95% role+direction precision**, subject to stricter adjudication after observing error costs.

Below-gate observations can remain candidate/review evidence.

## H2. Commercial vendor bake-off

Do not ask which vendor has the most edges.

Ask:

> Which vendor adds the largest quantity of lawful, PIT-correct, economically useful information beyond Mastermind's public-source baseline?

For S&P BRA, FactSet Revere and any existing LSEG entitlement measure:

- public-source overlap;
- incremental edges;
- false positives;
- stale edges;
- identity disagreements;
- estimated-magnitude calibration;
- termination/correction behavior;
- known-at reconstruction;
- licensing;
- incremental predictive information.

Vendor estimates are not ground truth.

## H3. Fundamental read-through validation

Primary outcomes should be operating fundamentals, not only returns.

After event A at source company, test whether linked target B subsequently shows:

- revenue surprise;
- EPS surprise;
- margin change;
- guidance revision;
- analyst-revision movement where PIT history permits;
- backlog/order/KPI change;
- capex change;
- inventory change.

This validates real economic propagation.

## H4. Expectations validation

Measure whether Graph-1 improves expectation updates beyond current Mastermind:

- consensus revisions;
- dispersion;
- earnings-expectation fields;
- implied volatility/skew;
- event-specific expected KPI/fundamental changes.

The North Star is not just “X is exposed.” It is:

> “Observation Y should change forward expectations for X through mechanism Z.”

## H5. Market validation

Only after fundamental validation, study abnormal returns at horizons such as:

- H+1;
- H+5;
- H+21;
- H+63.

Control for:

- market;
- sector;
- theme/subtheme;
- size;
- liquidity;
- momentum;
- Graph-2 similarity;
- Graph-3 residual beta;
- group momentum;
- own-company news;
- macro events;
- analyst coverage;
- institutional ownership where clean.

## H6. Required ablations

| Model | Question |
|---|---|
| Graph-1 only | Does economic relationship carry independent information? |
| Graph-2 only | Is similarity alone enough? |
| Graph-3 only | Is market sympathy enough? |
| Graph-1 + Graph-2 | Does economics add beyond comparability? |
| Graph-1 + Graph-3 | Does economics add beyond co-movement? |
| Graph-1 + Graph-2 + Graph-3 | Does full composition improve outcomes? |
| Disclosed-only Graph-1 | Is explicit truth sufficient? |
| Vendor-estimated Graph-1 | Does inferred/estimated coverage add value? |
| Public-source baseline | What can Mastermind build itself? |
| Public + commercial | What is the marginal value of the subscription? |

## H7. Falsification battery

Use:

- degree-preserving randomized networks;
- industry-preserving edge randomization;
- same-theme but unlinked firms;
- time-reversed relationships;
- reversed direction;
- placebo dates;
- deliberately delayed known_at;
- high-degree-hub removal;
- removal of vendor-estimated edges;
- target own-news controls.

If predictive value survives arbitrary network rewiring, it probably was not a supply-chain signal.

## H8. Statistical hygiene

Use:

- rolling/expanding PIT splits;
- no current-snapshot historical graph;
- event/date clustering;
- overlapping-event controls;
- FDR/multiple-testing procedures;
- regime stability;
- coverage-stratified analysis;
- proper scoring rules/calibration for probabilities;
- incremental explanatory metrics;
- interval coverage/MAE for magnitude estimates.

No promotion from one attractive backtest.

---

# I. Risks and failure modes

## 1. Current-state lookahead

Never reconstruct 2021 with a 2026 graph unless the provider can prove historical known-at state.

Every replay must require:

known_at <= test_cutoff

## 2. Effective time confused with knowledge time

A relationship may have economically existed before Mastermind learned it. Keep both clocks.

## 3. Relationship laundering

Never convert:

- theme membership;
- ETF membership;
- product similarity;
- residual beta;
- common ownership;
- generic agreement text;
- government-award adjacency;

into supplier/customer truth.

## 4. Missing relationship interpreted as false

No known supplier edge means:

unknown / uncovered

not:

no supplier relationship exists.

## 5. False precision

Estimated COGS share must not be displayed as disclosed COGS share.

## 6. Vendor lock-in

Canonical identity must remain Mastermind-owned. Vendor IDs remain source references.

## 7. Inference contamination

Observed/disclosed versus inferred/model-estimated edges must remain distinguishable.

## 8. Stale edges

A five-year-old disclosure cannot remain active forever by default.

## 9. Correction leakage

Today's corrected filing cannot overwrite what the historical system knew before correction.

## 10. Parent/subsidiary aggregation error

Transactions at subsidiary/facility level must not be automatically attributed to listed-parent economics.

## 11. Shipment ≠ dependency

Freight records may name forwarders, consignees or intermediaries.

## 12. Common cause mistaken for propagation

Customer and supplier can move because of the same macro/theme/commodity shock.

## 13. Hub inflation

Highly connected nodes can dominate path counts; path evidence is not independent by default.

## 14. Portfolio double-counting

Theme, relationship, news and market reaction can all derive from one event. Portfolio V3 must retain dependence.

## 15. LLM authority creep

Models should propose and explain; contracts and evidence owners should admit truth.

---

# J. Build priority

## P0

- Resolve Graph-1 ownership/admission under current source law.
- Preserve the existing prohibition on standalone GMI W4.
- Freeze observation, exposure, temporal, correction and rights contracts.
- Build adjudicated gold-set validation and PIT replay before scale.
- Start with high-precision U.S. issuer-disclosed relationships from existing filing owners.
- Reuse exact Stock Identity/Data OS references.
- Ship coverage/freshness/unknown/correction observability with the first source.
- Give K3-D/F04 read-only shadow access to real Graph-1 facts when interface law permits.
- Maintain zero trading/portfolio authority.

## P1

- Add independently typed exposure magnitudes: revenue, procurement/COGS, geography, capacity, product and commodity.
- Project GovRev relationships without duplicating GovRev.
- Add BEA/Census/BTS/USGS/EIA physical-economic priors.
- Run S&P BRA vs FactSet/current LSEG bake-off.
- Use shipment data prospectively/shadow unless historical PIT is contractually proven.
- Execute fundamental/expectation/predictive validation.

## P2

- Private-company/facility/deep-tier/BOM enrichment only for proven consumer cases.
- Evaluate Sayari/Altana/Interos/Everstream/Exiger or domain-specific sources.
- Learn propagation lag/pass-through/substitutability empirically.
- Expand product/component/standard ontology after initial identities prove useful.

## Defer

- Dedicated graph database until query scale proves need.
- Global exhaustive private-company network.
- Routine three-plus-hop propagation.
- Portfolio/Prophet consumption until predictive independence is proven.

## Reject

- Standalone GMI W4 relationship authority under current law.
- One fused economic-exposure/confidence/propagation score.
- Backfilling today's vendor graph into historical dates.
- Theme/co-movement/similarity → customer/supplier inference.
- LLM-authored relationship truth.
- Automatic trading/ranking/sizing/gating from Graph-1 before validation.
- New identity, GovRev, theme or research truth planes duplicating existing owners.

---

# K. Proposed implementation phases

## Phase 0 — ownership and admission

Before persistent Graph-1 implementation:

1. Refresh current Mastermind/Macro/Terminal heads.
2. Re-read current owner/decision registries.
3. Reconcile:
   - GMI W4 prohibition;
   - K3-D state;
   - F04 ownership;
   - Stock Identity/Data OS;
   - filing/fundamental owners;
   - GovRev;
   - Research Vault;
   - Evidence Foundation.
4. Publish one explicit ownership/adoption decision.

Exit: one canonical answer to who may emit, normalize, project and consume Graph-1.

If ownership remains ambiguous, stop the modifying lane rather than creating another graph.

## Phase 1 — contracts + gold set

Freeze:

- node references;
- relationship observations;
- exposure measurements;
- temporal semantics;
- correction semantics;
- rights;
- non-authority.

Create a hostile, adjudicated gold corpus.

Exit: validators can distinguish valid supplier/customer evidence from theme, similarity and market behavior.

## Phase 2 — explicit-disclosure public pilot

Implement a narrow U.S. lane using already-authorized filing owners.

Initial relation types:

- named major customer;
- explicitly named supplier;
- contract manufacturer/foundry/CDMO;
- distributor;
- licensor/licensee;
- explicit product/component dependency.

Models may propose candidates with spans; admission remains governed.

Exit: high-precision PIT relationship corpus with full receipts.

## Phase 3 — exposure + physical corroboration

Add:

- disclosed relationship magnitude;
- customer concentration;
- procurement/COGS where supported;
- geography;
- product;
- commodity;
- capacity/facility qualifiers;
- sector-level physical priors;
- GovRev projection.

Exit: Graph-1 describes economics without collapsing unlike dimensions.

## Phase 4 — commercial bake-off

Trial only:

- S&P BRA;
- FactSet Revere;
- LSEG if already entitled.

Use Panjiva or similar shipment data primarily for physical corroboration/forward observation unless PIT history is proven.

Exit: evidence-based buy/no-buy.

## Phase 5 — K3-D/F04 shadow propagation

Feed real Graph-1 into:

- K3-D;
- F04;
- bottleneck research.

No ranking/trading authority.

Exit: first- and bounded second-order paths are sourced, useful and falsifiable.

## Phase 6 — empirical promotion

Run historical and prospective PIT validation.

Require:

- fundamental improvement;
- expectation improvement;
- independent contribution beyond Graph-2/3;
- source-quality stability;
- regime stability.

Only then consider Portfolio V3/Prophet evaluation.

## Phase 7 — selective deep graph

Only if validated consumer value requires it:

- private entities;
- facilities;
- BOMs;
- nth-tier suppliers;
- alternative suppliers;
- qualification constraints;
- product standards.

This is where specialty commercial platforms become justified.

---

# Kill criteria

Do not scale or promote the data family if:

1. admitted role/direction precision cannot clear its preregistered gate;
2. rights/PIT filters leave insufficient useful history;
3. relationship expiration cannot be maintained;
4. vendor estimated magnitudes fail calibration;
5. predictive value disappears after Graph-2/Graph-3/sector/common-event controls;
6. Graph-1 adds no incremental fundamental forecasting information;
7. paid data adds little beyond public-source Graph-1;
8. vendor rights do not clearly permit intended persistence/derivation/display;
9. historical corrections/vintages cannot be reconstructed;
10. useful output depends on model-invented relationships;
11. implementation requires duplicating GMI, identity, GovRev, Research Vault, K3-D or F04 ownership;
12. no named consumer justifies the maintenance burden.

A failed validation is a successful research result if it prevents Mastermind from building an expensive correlation machine.

---

# L. Exact implementation handoff

## FOLLOW-ON IMPLEMENTATION COMMISSION — GRAPH-1 P0: ECONOMIC RELATIONSHIP EVIDENCE CONTRACT + EXPLICIT-DISCLOSURE PILOT

### Mission

Implement the smallest production-quality foundation for a lawful point-in-time **Graph-1 economic relationship evidence plane**, preserving all current Mastermind/Macro source owners.

This commission is intentionally narrower than the full economic-graph vision.

It does **not** authorize:

- a global supply-chain graph;
- commercial data purchase;
- new trading signals;
- portfolio behavior;
- Prophet integration;
- standalone GMI relationship authority.

### Mandatory bootstrap

Before any modifying action:

1. Pin current protected mastermindx-market-intelligence/Mastermind master.
2. Read current docs/sol_skills/INDEX.md and all required same-commit procedures.
3. Pin current Macro main and Terminal master.
4. Census current PRs/decisions/owners touching:
   - GMI Theme Graph;
   - K3-D;
   - MarketOntology F04;
   - Data OS / Stock Identity;
   - Evidence Foundation;
   - issuer filing/fundamental owners;
   - GovRev;
   - Research Vault.
5. Revalidate that no later decision reassigned Graph-1 ownership.

Do not treat the SHAs in this research report as current execution authority.

### First gate — ownership ruling

Produce one adoption map stating:

- owner of raw relationship evidence;
- owner of normalized relationship contracts;
- whether the Graph-1 projection is ephemeral or materialized;
- if materialized, why it is a derived index and not a competing truth store;
- identity owner;
- K3-D boundary;
- F04 boundary;
- GMI boundary;
- GovRev boundary;
- Research Vault boundary.

If a new persistent surface would violate current GMI-W4/K3-D/F04 owner decisions, stop that modifying lane and return the exact collision. Do not rename the same duplicate and continue.

### Bounded implementation scope after ownership clearance

Build only:

1. canonical relationship-observation contract;
2. exposure-measure contract where needed for explicit magnitudes;
3. temporal/correction/rights semantics;
4. deterministic validation;
5. read-only Graph-1 query projection;
6. explicit-disclosure U.S. pilot using already-authorized filing owners;
7. gold-set/adversarial evaluation harness;
8. freshness/coverage/quality observability;
9. read-only K3-D/F04 shadow consumption if their current contracts permit it.

### P0 relation classes

Limit automatic/admitted scope to strongly evidenced roles such as:

- named major customer;
- explicitly named supplier;
- contract manufacturer;
- foundry;
- CDMO;
- distributor;
- licensor/licensee;
- explicitly named product/component dependency.

Do not broaden ontology merely to maximize edge count.

### Required temporal fields

Every admitted observation must carry or explicitly type as unavailable:

- event_time;
- as_of;
- observed_at;
- available_at / known_at;
- ingested_at;
- effective_from;
- effective_to;
- discovered_at;
- belief_time;
- source_revision;
- processing_generation;
- correction_generation.

Historical replay must enforce both knowledge time and effective time.

### Required provenance

Every relationship must resolve to:

- exact source receipt;
- source document/record ID;
- structured coordinate or text span;
- entity-resolution receipt;
- extraction method/version;
- rights state.

No receipt means no admitted Graph-1 edge.

### Extraction law

Use deterministic parsing wherever structure exists.

LLMs may propose unstructured candidates only with exact supporting spans.

A model proposal is never automatically authoritative.

### Magnitude law

Do not mint generic economic_share.

Where a source provides magnitude, preserve its actual semantic dimension:

- supplier revenue share;
- customer revenue share;
- procurement/COGS share;
- relationship value;
- volume;
- capacity share.

Disclosed and estimated values remain separate classes.

Unknown remains null.

### Required hostile tests

At minimum reject:

- same theme → supplier;
- same basket → supplier;
- residual correlation → commercial relationship;
- generic 8-K agreement → customer/supplier;
- co-ownership → operating relationship;
- government-award adjacency → supplier/customer;
- current edge appearing before historical known_at;
- correction retroactively rewriting historical belief;
- unresolved identity becoming a ticker guess;
- vendor/model estimate presented as disclosed;
- missing edge interpreted as negative evidence;
- LLM candidate with no source span;
- expired relationship remaining active indefinitely.

### Gold-set requirement

Before automatic admission, evaluate a stratified adjudicated corpus.

Preregister the role+direction precision threshold before reading final results.

A candidate first automatic-tier requirement is **≥95% precision**; the implementation owner may recommend a stricter threshold based on observed error costs, but may not quietly lower the threshold to pass.

### PIT replay proof

Provide at least:

- one relation whose effective date precedes disclosure but correctly remains unavailable to an earlier as-of query;
- one correction/amendment;
- one termination/expiry;
- one unknown/no-coverage state;
- one identity ambiguity that correctly abstains.

### Consumer proof

If current K3-D/F04 contracts permit read-only input, demonstrate:

1. one real Graph-1-backed propagation hypothesis;
2. one typed Graph-1 abstention;
3. one case with Graph-2/Graph-3 evidence but no lawful Graph-1 relationship.

This is shadow research proof only. It grants no trading authority.

### Observability acceptance

Expose at minimum:

- latest producer time;
- count by relationship type;
- count by source family;
- exact-identity resolution rate;
- unknown/ambiguous identities;
- relationship-age distribution;
- stale/expired counts;
- correction generations;
- disclosed vs estimated magnitude coverage;
- missing magnitude coverage;
- rights-blocked counts;
- source freshness.

Do not recreate the stale-census problem.

### Explicit non-goals

This commission must not:

- purchase a commercial provider;
- build a fourth K3 graph;
- resurrect GMI W4;
- introduce a graph database solely because the data is graphical;
- build deep N-tier BOM mapping;
- create a propagation score;
- modify Prophet;
- modify portfolio rank/gate/size;
- trade;
- create new autonomous alerts;
- build MarketOntology UI;
- create another identity plane;
- duplicate GovRev;
- duplicate Research Vault;
- fill unknown relationships through model inference.

### Acceptance packet

Return with:

- current source-law pins;
- ownership/adoption decision;
- final contracts;
- changed-file census;
- gold-set composition/results;
- precision/error analysis;
- PIT replay evidence;
- correction/termination proof;
- rights/identity proof;
- observability proof;
- K3-D/F04 shadow proof or exact reason it remains gated;
- independent adversarial review;
- focused tests and hosted CI;
- explicit confirmation that no commercial source was purchased and no trading/portfolio authority changed.

### Stop condition

P0 is complete when Mastermind can truthfully answer:

> “At historical cutoff T, what role-specific economic relationships did we actually know, from what evidence, for what effective period, with what disclosed exposure dimensions, and what did we explicitly not know?”

If answering that question requires present-day information, inferred causality, ambiguous identity or duplicated ownership, P0 is not complete.

Do **not** continue from P0 into commercial procurement, deep-tier mapping, Portfolio integration or Prophet integration without a separate accepted commission.

---

# Primary-source / reference bibliography

- Mastermind Theme Graph and economic-propagation source: current repository paths cited above.
- Cohen, Lauren, and Andrea Frazzini. “Economic Links and Predictable Returns.” Journal of Finance. https://doi.org/10.1111/j.1540-6261.2008.01379.x
- Menzly, Lior, and Oguzhan Ozbas. “Market Segmentation and Cross-predictability of Returns.” Journal of Finance. https://doi.org/10.1111/j.1540-6261.2010.01578.x
- Barrot, Jean-Noël, and Julien Sauvagnat. “Input Specificity and the Propagation of Idiosyncratic Shocks in Production Networks.” QJE. https://doi.org/10.1093/qje/qjw018
- Carvalho, Vasco et al. “Supply Chain Disruptions: Evidence from the Great East Japan Earthquake.” QJE. https://doi.org/10.1093/qje/qjaa044
- Acemoglu, Daron et al. “The Network Origins of Aggregate Fluctuations.” Econometrica. https://doi.org/10.3982/ECTA9623
- Hoberg, Gerard, and Gordon Phillips. “Product Market Synergies and Competition in Mergers and Acquisitions: A Text-Based Analysis.” NBER/product-market-network research family. https://www.nber.org/papers/w15991
- SEC EDGAR APIs: https://www.sec.gov/search-filings/edgar-application-programming-interfaces
- SEC EDGAR access/data guidance: https://www.sec.gov/search-filings/edgar-search-assistance/accessing-edgar-data
- BEA Input-Output Accounts: https://www.bea.gov/data/industries/input-output-accounts-data
- Census International Trade API: https://www.census.gov/data/developers/data-sets/international-trade.html
- BTS Freight Analysis Framework: https://www.bts.gov/faf
- USGS Mineral Commodity Summaries: https://www.usgs.gov/centers/national-minerals-information-center/mineral-commodity-summaries
- EIA Open Data: https://www.eia.gov/opendata/
- Open Supply Hub API: https://info.opensupplyhub.org/resources/api-documentation
- S&P Business Relationships Analytics: https://www.marketplace.spglobal.com/en/datasets/business-relationships-analytics-%281739270615%29
- S&P Panjiva: https://www.marketplace.spglobal.com/en/datasets/panjiva-supply-chain-intelligence-%2822%29
- Sayari Graph: https://sayari.com/platform/graph/
- Altana Supply Chain Graph: https://docs.altana.ai/concepts/supply-chain-graph/article.html
- Interos: https://www.interos.ai/our-software
- Everstream Analytics sub-tier visibility: https://www.everstream.ai/platform/platform-sub-tier-visibility/
- Exiger supply-chain platform: https://www.exiger.com/supply-chain/

---

## Bottom line

The highest-value project is **not** “build the biggest supply-chain graph.”

It is:

1. establish a tiny, extremely trustworthy point-in-time Graph-1 relationship truth layer;
2. make every edge source-backed, effective-dated, correction-safe and rights-aware;
3. preserve Graph-1/2/3 independence;
4. feed K3-D/F04/Neural Web as consumers;
5. validate incremental fundamental and expectation value;
6. expand into deep-tier commercial data only where measured value justifies the cost.

That architecture converts Mastermind from “many relationship-like signals” into an evidence-grounded economic propagation system without recreating the duplicate-control-plane problems the current estate already warns against.
