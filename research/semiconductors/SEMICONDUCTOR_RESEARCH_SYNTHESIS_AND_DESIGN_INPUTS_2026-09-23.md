# Semiconductor Intelligence — Cross-Installment Synthesis and Design Inputs

**23 September 2026 · research synthesis · not the written product specification and not the Fable handoff**

Operation: `gmi-semiconductors-research-20260923-sol-001`. Parent: `WS:GMI-THEME-GRAPH`. Existing carrier: Macro draft/HOLD PR #7780, branch `sol/semiconductors-research-20260923`. This synthesis consumes the five principal research installments on the same carrier and current native-owner evidence. It does not approve a production contract, create a new graph/identity/expectation store, or authorize implementation.

## 1. The research thesis after five installments

A useful Semiconductor Theme is not a ticker map and not a single supply-chain Sankey. It is a **source-grounded explanatory dossier over multiple existing owners**. For a selected technology, manufacturing step, application or company, the reader should be able to answer five linked questions:

1. **What physically exists or is required?** — package/component/material/configuration and containment.
2. **How is it manufactured?** — process steps, equipment, materials, facility route and qualification.
3. **What commercial relationship is actually documented?** — capability, inclusion, development agreement, supply, license, shipment or service; never inferred merely from category adjacency.
4. **What is the qualified capacity/economic constraint?** — announced versus installed versus qualified versus producing versus shipped output, in compatible units and scopes.
5. **How can the industrial change transmit into per-share economics and expectations?** — volume/content/price/share/mix, recognition, margins, capital needs, diluted shares, management outlook and only those external expectations supplied by accepted native owners.

The machine job is to preserve these distinctions through time, not flatten them into a confidence score. The user job is to understand the mechanism, evidence, limitations and next discriminating observation without reconstructing the industry from source links.

## 2. Unified vocabulary to carry into design

The research now has enough cross-domain evidence to freeze a vocabulary for design review. These are **semantic requirements**, not new production schemas.

| Concept | Meaning | Explicitly not |
|---|---|---|
| `research_slice` | Versioned research/filter view such as HBM, SiC, lithography, robot motor drive or same-perimeter guide acceleration | Automatically a canonical theme, portfolio basket or security universe |
| `source_assertion` | Reviewed, source-scoped statement retaining publisher, locator, clocks, statement mode, object/configuration and limitations | Global truth merely because a source says it |
| `source_object` | Product, platform, business, process or configuration as identified within a source | Automatically a globally resolved product identity |
| `documented_relationship` | Exact relation type such as inclusion, license, manufacturing partnership, supply, process use or announced development | Generic `SUPPLIES` inferred from two relevant companies |
| `physical_containment` | Part/assembly/material relation within a specified product/configuration | Manufacturing equipment as a component of the finished chip |
| `manufacturing_dependency` | Process/equipment/material/facility capability required to make an object | Proof that every vendor in that category is a qualified substitute |
| `capacity_observation` | Dated measurement/target in a defined unit and facility/process/product scope | One universal semiconductor-capacity number |
| `qualification_state` | Source-supported process/product/customer applicability | Company-wide certification inferred from one device/fab certificate |
| `economic_mechanism` | Causal research path such as volume, content, ASP, share, mix, utilization, yield, service, royalty or license timing | Portfolio weight or return forecast |
| `management_outlook` | Issuer-authored future metric with its period, definition, assumptions and publication clock | Street consensus |
| `external_consensus` | Licensed/accepted native estimate object when one exists | Locally scraped or backfilled analyst history |
| `house_expectation` | Existing accepted forecast-owner output with model/input/evaluation receipt | An interpretation silently promoted from research prose |
| `actual_result` | Reported period result under its native accounting/perimeter definition | Retroactive replacement of the prior expectation vintage |
| `market_incorporation` | Accepted native owner’s point-in-time evidence about market response | A universal GMI gap score or causal inference from price alone |
| `business_binding` | Source-scoped operating business and ownership interval | Automatically the whole public issuer |
| `security_binding` | Native validated issuer/security/listing identity | A guessed ticker based on a similar company name |

## 3. Clocks and state transitions that must stay separate

Across BOM, capacity, earnings and expectations, the same anti-leakage law recurs. Preserve at least:

- source publication/availability time;
- system observation/recording time;
- business-effective date or interval where the source establishes one;
- future target window where relevant;
- curation/review publication time;
- correction/supersession lineage.

Do not use curation date as the supplier's publication date. Do not turn a target date into a completed event because time passed. Do not overwrite historical expectation vintages with actuals or later guidance. Do not use a current analyst snapshot as though it existed months earlier.

The first four installments already require separate modes for catalog capability, documented inclusion, announced agreement, target, reported deployment, ownership event, operating/financial observation and correction. Installment five adds expectation modes. The design should compose these modes rather than inventing a second state machine for Semiconductors.

## 4. Capacity semantics after the adversarial cases

Capacity should be explained as a scoped evidence ladder, not one scalar status. Relevant states include:

`announced / planned -> physically installed or expanded -> process-qualified -> product-qualified -> customer-qualified or approved -> producing -> shipped / accepted -> retired or superseded`

This arrow is explanatory, not a mandatory universal workflow. States can overlap, repeat or regress; a product can qualify on more than one line and approvals can be configuration-specific.

Every observation needs its object and unit: cleanroom area, gross wafer capacity, wafer output, shipments, good dies, stacks, packages, test slots, recognized revenue or customer allocation. UMC showed why shipment/capacity cannot be substituted for an issuer-defined wafer-output utilization ratio. CoWoS showed why package variants are not automatically fungible. HBM showed why generation, stack height, base-die route and supplier must remain explicit.

### Binding-constraint rule

A capacity expansion matters to finished output only if it relieves a binding or prospective constraint in the relevant product route. Front-end wafer capacity can rise while packaging, test, customer qualification or a shared upstream tool remains limiting. Aggregate industry capacity can exceed aggregate demand while one customer/application lacks enough qualified/accessible supply.

The product should therefore report **constraint scope + next observable release condition + alternatives + strongest competing explanation**, not a universal bottleneck score.

## 5. Economic transmission rules after the business-model research

The common chain is:

`industrial event -> relevant content/work -> units / bits / wafers / systems × price/content/share -> recognized revenue -> gross profit -> operating profit -> cash/capital -> diluted per-share economics -> expectation change`

Each business archetype populates the chain differently:

- **merchant foundry:** qualified wafer/package work, utilization, node/mix, pricing, yield, depreciation/start-up costs;
- **fabless/custom platform:** sellable units/content/ASP constrained by manufacturing access and customer ramps;
- **memory:** bits × ASP × mix with inventory/utilization/capex feedback;
- **equipment/process control:** orders -> shipment -> acceptance/revenue plus installed-base/service economics;
- **EDA/IP:** license/subscription/hardware recognition plus separate royalty/customer-shipment clocks;
- **analog/power/embedded:** broad end-market demand, channel inventory, price/mix and internal-factory absorption;
- **OSAT/packaging service:** accepted package/test work, technology/mix, utilization and service/manufacturing margin rather than chip ASP itself.

Research must retain offsets. Die-density improvements can reduce wafer demand for the same finished-device volume. Integration can remove components. Revenue can rise on price while units are flat. Cash can improve through customer advances or incentives. Acquisitions can raise total guidance without same-perimeter organic acceleration.

## 6. Three structural edge cases that prevent a simplistic company taxonomy

### 6.1 Intel: an IDM/foundry segment is not the same as merchant-foundry revenue

Intel's Q1 2026 earnings-call material reports **$5.4 billion of Intel Foundry segment revenue** and separately **$174 million of External Foundry revenue**. The same material describes internal products on 18A/14A and Foundry carrying early-ramp costs. Source: https://download.intel.com/newsroom/2026/earnings/1Q2026-Earnings-Call.pdf (relevant foundry discussion visually inspected).

Design consequence: a foundry research slice needs an `internal/captive versus external/merchant` economic scope. The $5.4 billion segment figure must not be displayed as third-party foundry demand. A company can simultaneously be product designer, manufacturer and merchant foundry candidate.

### 6.2 Samsung: one integrated semiconductor division contains different economic mechanisms

Samsung's Q2 2026 results report the Device Solutions division across Memory, System LSI and Foundry. The issuer describes record Memory results, System LSI mobile/SoC/sensor dynamics, and Foundry improvement/design wins within the same broader division. Source: https://news.samsung.com/global/samsung-electronics-announces-second-quarter-2026-results .

Design consequence: a broad division/issuer financial result is not a foundry revenue series, memory revenue series and System LSI revenue series simultaneously. Evidence must bind to the disclosed business scope and expose nondisclosure rather than inventing a sub-business financial split.

### 6.3 Amkor: outsourced assembly/test is a manufacturing-service business, not a chip-content vendor

Amkor describes itself as a provider of outsourced semiconductor packaging and test services. Q2 2026 net sales were **$1.898 billion**, with Computing and Automotive & Industrial cited as record end-market revenue areas and ongoing advanced packaging/test capacity expansion. Source: https://ir.amkor.com/news-releases/news-release-details/amkor-technology-reports-financial-results-second-quarter-2026 .

Design consequence: the ontology needs an OSAT/service role distinct from a material supplier, foundry and integrated package owner. A package configuration can use an OSAT without making the OSAT's revenue equal the finished chip's value or without proving which customer/product consumed a given line.

## 7. Company classification should be faceted, not one label

A company/business record should therefore expose independent facets:

- business model: fabless, merchant foundry, IDM, captive/internal manufacturing, OSAT, equipment, materials, EDA/IP, component/product vendor;
- physical role: product/component/material/process/equipment/package/test;
- manufacturing role: designer, wafer fab, assembly, test, substrate/material, tool/process provider;
- economic role: product seller, manufacturing service, royalty/licensing, subscription, service/installed base;
- application/end-market exposure;
- geography/site scope;
- ownership/effective interval;
- evidence confidence/limitations;
- validated security binding when available.

A company can carry several facets with different evidence. These facets should not become separate duplicate company records or ticker entries.

## 8. Expectation intelligence: the first vertical can be useful before Street consensus exists

Current Mastermind owner recovery establishes a clean first product boundary:

1. prior management outlook;
2. actual result;
3. new management outlook;
4. explicit assumptions/definition/perimeter changes;
5. external consensus, house expectation and market-incorporation evidence **only when accepted native owners provide them**.

The six bounded point-in-time replays in `POINT_IN_TIME_EXPECTATION_REPLAY_AND_OWNER_BOUNDARY_2026-09-23.md` demonstrate that this management-guidance slice can add value while still refusing hindsight leakage or false consensus semantics.

A historical view must never show later actuals/guidance at an earlier cutoff. An acquisition-perimeter change can make a raw guide delta incomparable. Retired KPIs are not zeroes. A management-guide beat is not a consensus beat. Price moves are not causal attribution.

## 9. Research-to-product information architecture requirements

The shared theme template should support synchronized but separately typed views:

### Theme / research-slice summary
- thesis/mechanism summary;
- dated research coverage and important changes;
- affected companies/businesses by source-backed role;
- key bottleneck/qualification questions;
- expectation/economic changes where available;
- direct route into the existing company/theme workflow.

### Industrial map
Selectable layers rather than one overloaded graph:
- physical containment;
- manufacturing route/process dependencies;
- documented commercial relationships;
- capacity/qualification/geography;
- economic/business ownership.

### Company/business dossier
- exact business role and applicable ownership interval;
- source-scoped products/processes/configurations;
- relationships with exact predicate/state;
- capacity/constraint evidence and limitations;
- economic mechanism and compatible reported financial scope;
- prior management outlook -> actual -> new outlook when available;
- native security link only after validated identity.

### Evidence drawer/table
- publisher and exact locator;
- source statement mode;
- all relevant clocks;
- units, denominator, configuration and geography;
- review/retention status;
- limitations and supersession/correction.

### Degraded/refusal states
- unlicensed historical consensus;
- unresolved security/product identity;
- incomparable metric/perimeter;
- unknown qualification/customer allocation;
- stale/withdrawn source;
- missing private publication right;
- unsupported point-in-time market attribution.

An empty panel must not make unavailable data look like zero or no change.

## 10. Research collections are explanation tools, not portfolios

Across the installments, useful research collections include HBM generations, advanced packaging variants, lithography/mask infrastructure, materials/process intensity, SiC/GaN, mature/specialty foundry, robotics component routes and economic mechanisms such as same-perimeter guide acceleration or utilization recovery.

These collections can overlap. Membership answers **why this company/business is relevant to the research question**, not whether the stock should be bought. Purity/exposure, evidence quality, business materiality and market attractiveness remain separate dimensions. No collection changes incumbent basket constituents or trading outputs merely because research coverage exists.

## 11. Cross-theme graph requirements

Semiconductor intelligence should be referenced by Robotics, AI Infrastructure, Datacenters, Automotive, Energy, Defense and Industrial Automation rather than copied into independent taxonomies.

The cross-theme edge should be application scoped. Examples:

- Robotics -> motor drive -> gate driver/current sense/MCU/processor/sensor configuration;
- Datacenter AI -> accelerator -> HBM/package/networking/power route;
- EV/energy -> inverter/on-board charging -> SiC/GaN/device/module/process route;
- Automotive SDV -> centralized compute/networking/sensing -> relevant silicon and displaced legacy modules.

An application theme can consume source-backed semiconductor roles without becoming the global owner of semiconductor product identity.

## 12. Approaches to take into the formal design review

These are research-informed alternatives for Chairman review. No approach is approved by this research document.

### Approach A — evidence-only extension inside the existing Theme detail

Use the Robotics-style source-scoped curation assertion and shared detail template to show semiconductor industrial facts and evidence. Keep expectation/economic composition minimal.

**Advantages:** smallest integration surface; lowest collision/privacy risk; quickly proves source -> dossier -> evidence.

**Limit:** leaves much of the new business-model and management-guidance research outside the useful user journey. The result could become an excellent industry encyclopedia but a weaker investment-intelligence system.

### Approach B — compositional Semiconductor dossier across existing native owners

Use the same GMI evidence/curation foundation for industrial assertions, but compose the read-only dossier with existing Earnings/financial/identity/K1/F04 owner outputs for management guidance, actual financial context and validated company/security navigation. Unsupported consensus/market-incorporation states degrade visibly.

**Advantages:** preserves one canonical system while delivering the full user job from physical mechanism through business economics; directly reuses the five-installment research; creates a reusable pattern for other Themes.

**Costs/risks:** more interface reconciliation and acceptance cases; requires careful clock/perimeter/refusal behavior and private publication boundaries.

**Research preference:** this is the strongest candidate for the formal written design because it improves usefulness without creating a duplicate graph, estimate store or financial owner.

### Approach C — first-class universal semiconductor product/process/expectation graph now

Promote products/processes/facilities/businesses/expectations into a new broad canonical graph before the first vertical.

**Advantages:** maximal long-run query power in theory.

**Why research currently rejects it as the first delivery:** it would prematurely create or compete with product identity, evidence, expectation and financial authorities; it also makes Fable/implementation workers solve global identity and rights problems before proving one user journey. The first vertical can preserve source-scoped objects and native references while leaving a future path to accepted first-class identity.

## 13. Research preference to present for Chairman approval

The research supports **Approach B** for the first semiconductor vertical:

`state_of_themes / semiconductor detail -> selected research slice -> source-scoped industrial mechanism -> company/business role -> exact evidence -> prior management outlook / actual / new outlook where accepted -> visible limitations/refusals -> existing company/stock workflow`

The design should prove one complete path deeply rather than shallowly populate every semiconductor slice at once. The full ontology and research corpus remain reusable; implementation can begin with a discriminating vertical such as **HBM / advanced packaging / qualified-capacity + management-guidance economics**, because prior research contains both physical and financial edge cases. A non-AI secondary witness, such as SiC/GaN or specialty foundry/OSAT, should be part of acceptance so the implementation does not accidentally hard-code AI-specific assumptions.

This preference is **not written-spec approval**. The next step is Chairman design review. Only after that review should the architectural written specification be authored and committed under the project design gate.

## 14. What the formal design must prove if Approach B is approved

At minimum:

1. no new graph, identity, consensus, financial-fact, correction, queue or publication authority;
2. one source-scoped assertion contract compatible with current GMI evidence/curation ownership;
3. exact clock and correction behavior from source through UI;
4. source object/product/facility/business roles without guessing global identity;
5. validated company/security links only through existing resolver;
6. management-guidance/actual composition through existing event/financial owners;
7. typed unavailable consensus/market-incorporation states until their owners supply accepted objects;
8. private/no-store publication of full-fidelity current research with no public static leak;
9. shared-template integration rather than a Semiconductor-specific page fork;
10. physical/process/commercial/capacity/economic view separation and accessible synchronized table;
11. unchanged incumbent recommendation/ranking/entry/sizing/trading outputs;
12. one real source-to-visible-result browser proof plus degraded/refusal cases;
13. a second non-AI witness proving the representation is semiconductor-native rather than AI-specific;
14. explicit owner/collision reconciliation immediately before any implementation writes.

## 15. Research frontier after this synthesis

No additional broad sector census should delay design review. Remaining external research should be **question-driven**: only a competitor, process, accounting or qualification case that could invalidate the proposed representation or acceptance criteria justifies reopening a research lane.

The research corpus is not a complete worldwide company census, not a live capacity database, not licensed historical consensus, and not predictive validation. Those limitations should remain visible in the formal design rather than being patched with invented data.

Fable remains uncommissioned. Implementation remains held behind the Chairman's design approval, the written-spec review and the subsequent implementation-plan review.

`MISSION_COMPLETE: false`.