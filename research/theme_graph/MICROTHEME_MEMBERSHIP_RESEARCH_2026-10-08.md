# GMI granular microtheme membership — research and implementation decision

**Commission:** October 8, 2026, Chairman Chris. **Prepared:** October 9, 2026 UTC. **Operation:** `theme-micro-membership-20261008-pro-001`. **Owner:** `WS:GMI-THEME-GRAPH`. **Disposition:** proposed research evidence, not canonical membership admission. The parent Theme Fabric mission remains incomplete.

## 1. Decision

Build **evidence-qualified business-activity membership**, not a larger collection of ticker tags. The useful unit is a dated assertion that an identifiable business supplies, owns, operates or develops a particular product/activity, with an explicit economic role and supporting primary evidence. Resolve that business to the incumbent Data OS issuer/security identities separately. Only then can an existing house group or vertical slice be considered for a reviewed group-to-micro binding.

The October 13 accepted Taxonomy V2 hierarchy includes **macro_category → theme → optional sub_theme → micro_theme**, while retaining direct `theme → micro_theme` edges. The 12 intermediate `sub_theme` nodes are a reviewed house vocabulary addition, not new ticker cohorts, and the 68 microtheme IDs remain unchanged. A micro may have both the older direct edge and a new deeper path without being two measurement subjects. Granular company evidence should still use **product, economic role, technology, geography and lifecycle-stage descriptors** under incumbent owners, rather than inventing further nodes, scores or independent issuer identities.

The attached machine-readable research file covers every one of the **68 existing micro IDs**, with proposed inclusion/exclusion predicates, role descriptors and named company/activity candidates. It also supplies explicit counterexamples and a CPU scope-review supplement. Its population is **the candidates investigated in this research**, not all global firms capable of qualifying. A table that has a row for every micro is definition coverage; it is not full-market membership coverage.

**Most valuable first increment:** make this evidence inspectable through the existing membership-evidence owner and review CLI, preserving all old behavior. This gives the curator a usable, source-linked decision packet now without prematurely minting members, widening collection universes or changing market decisions. The following increment is a small owner-admitted group/slice pilot; source publication does not itself authorize that step.

### What the evidence changes

First, a single issuer can occupy several genuine roles without becoming several independent observations. Micron's memory and storage products need separate activity records; NVIDIA's compute and networking products also require separation. That does not create a new company each time the same issuer appears. [S001, S005, S094]

Second, the member set changes with corporate events and new business models. The CyberArk acquisition completed in February 2026; a current security projection must not leave it as a second independent listed issuer alongside its parent. Nextracker's corporate rebranding to Nextpower likewise does not create a second issuer. Arm's March 2026 direct-silicon announcement means that a permanent “IP-only” label is now an inadequate business description. Each case needs dated identity/activity reconciliation, not a manual overwrite of historical meaning. [S033, S098, S100]

Third, stage matters. Readiness, sampling, design approval, a signed contract, a plant under construction and commercial output answer different questions. An operational business may simultaneously have an uncommissioned expansion. The source packet must preserve both facts without promoting the future project. [S003, S012, S024, S027, S029, S057]

Fourth, product function matters more than shared vocabulary. First Solar's thin-film module role does not establish polysilicon demand. Enphase's proprietary chip is not an AI custom-compute accelerator merely because it is an ASIC. Oral incretin treatments also cannot all be used as evidence of peptide API demand. These are research classification distinctions, not forecasts about returns. [S052, S082, S085]

## 2. Current estate and non-duplication boundary

The research source is Macro commit `94a20f53cdb2d866d07089df50567f059bf1073e`. Protected procedure for this published research version is Mastermind commit `9a8e9b50b6158eb38af78a5b867eedba1719b908`, compatible skillpack 1.0.1 / bootstrap major 1 (matching the machine source pin). The original research working handoff used `732cf7be88e7159b4995a8885fbd381cd1484e3e`; that earlier observation is not this version's operative procedure pin. The protected deep-research procedure is `plugins/mastermind-sol/skills/mastermind-deep-research/SKILL.md`; the active-execution and reliability companions remain controlling. Reading a skill does not attest a particular provider's managed Deep Research runtime.

The original October 9 crosswalk blob `5796e3e5cf16839c7dbca2bf6d74737b35b547fc` contained 18 canonical themes, 10 macro categories, 68 micros and 93 parent rows. **This was superseded for hierarchy navigation** by merged Taxonomy V2 L02 [#8948](https://github.com/mastermindx-market-intelligence/macro/pull/8948) and L17 [#8999](https://github.com/mastermindx-market-intelligence/macro/pull/8999): the current October 13 crosswalk has 12 intermediate subthemes and 132 parent rows, leaving all 68 micro identities and their existing direct relationships intact. W-C4 #8629 has merged, as have the first M1 coverage-evidence increment #8651 and the existing W-C6/W-C8 reader work. Their code is not rebuilt here. The broad Theme Fabric research #8646 is also already merged; this report extends its membership evidence rather than replacing that investigation. [G1–G5]

The accepted C0 decision is important because older handoffs are no longer sufficient. It keeps researched splits and new taxonomy admissions deferred, preserves historical census corrections, and states that W-C7's stored category shadow is **optional**, not a prerequisite for E1. E1 uses its merged read-time composition law. This commission does not read prices, run E1, start its empirical clock or amend it. Likewise, current C0 does not treat a later merge date as an automatic reason to restamp the existing hierarchy. Older comments must not silently displace that accepted decision. [G2, G6]

The existing research's inherited micro diagnostic was 0 exact / 48 broad proxies / 20 without a primary basket, while its any-parent correction was 0 / 49 / 19. Those are historical parent-proxy diagnostics, not counts of qualified members. They remain separate from this report's new candidate-record counts. No candidate added to this research file closes a canonical admission gate. [G2–G4]

### Existing owners and reuse

| Concern | Incumbent owner and intended use |
|---|---|
| Meaning and hierarchy | GMI crosswalk, materializer, structural reader and curation/probation; no new taxonomy store |
| Legal entity, issuer, security, listing and corporate actions | Data OS; proposed name hints are inputs to qualification, not replacement IDs |
| Actual group members and history | Existing house group or vertical slice; do not create a parallel ticker-rule registry |
| Evidence drilldown | `engine/theme_graph/membership_evidence.py` and `scripts/explain_theme_overlap.py`; explicit research mode only |
| State measurements | Existing ThemeState owner after its current acceptance and source gates |
| Economic propagation | Existing K3-D/relationship owners; membership is not a causal edge |
| Product explanation | F04 and incumbent Terminal/Macro consumers using qualified outputs |
| Ranking, entry, sizing and trading | Existing decision owners; no new authority from this work |

## 3. Membership is an assertion, not a ticker attribute

For research purposes, the conceptual assertion is:

`(operating business, product/activity, economic role, existing micro reference, valid interval, knowledge interval, evidence, scope limitations)`.

This is a conceptual model, **not a newly admitted graph schema**. The attached artifact is a versioned research document consumed by a read-only reviewer. Its row locators are document references, not canonical entity or proposal identities.

The main distinctions are:

**Entity versus security.** A product belongs to a business, which may be a subsidiary or joint venture. The listed issuer may own several such businesses. The same issuer can have more than one listing or share class. Research must not turn each brand, subsidiary, ticker or parent path into independent economic N. In this delivery all canonical entity/security IDs remain null; Data OS qualification is explicitly unperformed.

**Membership versus role.** A CPU designer, foundry, packaging provider, cloud buyer and cooling supplier can all participate in an AI infrastructure mechanism. They do not occupy the same micro/product role. A broader theme connection is useful context, but it must not be converted into a more specific producer assertion without additional evidence.

**Participation versus materiality.** A product page can show a real product. It usually cannot establish the percentage of issuer sales, profit, backlog or capacity attributable to that product. The artifact therefore leaves economic shares null. “Diversified,” “direct product role,” “development-stage,” and “source incomplete” are descriptive qualifications, not model-generated financial weights.

**Effective time versus knowledge time.** A filing period end, publication date, product availability date, curation decision and graph belief date are distinct. Unknown dates remain unknown. A current product page is evidence observed now, not proof it existed in the same form years ago. A dated announcement with a future availability target cannot be read as current operation. The dataset uses nullable, precision-preserving source dates; no annual source is expanded into a fictional January 1 timestamp.

**Hierarchy versus inference.** Child membership may provide parent context after an admitted group-to-micro path exists. Parent membership does not imply every child. Multi-parent paths must preserve one subject and one issuer, rather than multiplying exposure or independent samples. An adjacent supply-chain relationship also does not confer semantic membership or return causation.

### Do not invent a numerical confidence score

A single scalar would hide materially different weaknesses. Prefer explicit review dimensions: identity unresolved; source publication uncertain; commercial stage unproven; product fit contested; revenue denominator absent; corporate event pending; group mapping unadmitted; measurement insufficient. A candidate with a convincing product source and unresolved security identity is not “80% tradable.” It is product-evidenced and identity-unqualified.

## 4. Research method and evidence quality

The work began with the accepted crosswalk and C0 decisions, not a vendor's thematic constituent list. Each micro received a proposed product/role inclusion predicate and at least one investigated candidate. Research then sought issuer product pages, operating/financial announcements, regulator notices and relevant official technical documentation. Sources establish the attributed business facts; the proposed micro fit and exclusion rules remain model-authored research judgments for owner review.

The source register records paraphrases and public links, not mirrored paid text. Retrieval comprised search extracts and selected page reads. **It does not claim that every complete source document was archived or independently authenticated.** Body digests are null where no retained exact body exists. The Git digest of this research package proves its own bytes only. Public access does not settle every downstream republication, capture or machine-use right.

Sources have different evidentiary power. A delivered-product or operating-results statement can support an activity stage. A product catalog supports an offered product but not necessarily sold volume. A design approval supports a regulatory milestone. A partnership release supports the described relationship, not a secret customer, production quantity or financial contribution. Company marketing performance claims were not used as independently validated measurements.

The research uses a two-direction search. Starting from the micro definition finds plausible companies; starting from a company's actual products exposes overbroad micro assignments and missing roles. The second direction is essential: it catches an issuer whose products span GPU, CPU and networking, or a power supplier whose cooling, UPS and switchgear activities differ. It also reveals genuine omissions, such as the still-deferred general/host CPU scope question.

This is not an exhaustive business census. Search visibility, English-language disclosure, private-company opacity, uneven product detail and jurisdictional filing access affect recall. The work supplies a **reviewable starting population**, not a statistically sampled precision/recall estimate or a closed global denominator. Missing companies are unresolved coverage, not proof that they do not participate.

### Alternatives evaluated

| Approach | Useful contribution | Why it is insufficient as membership authority |
|---|---|---|
| Sector/industry classifications | Broad discovery and benchmark/control populations | Company-level dominant activity misses narrow products and mixed business models |
| Parent basket copying | Existing chart context and broad candidate discovery | All children inherit the same constituents, manufacturing false granularity |
| Keyword rules | Cheap candidate screening and explainable retrieval | “AI,” “chip,” “robot,” “cloud” and “copper” do not identify economic roles |
| Text similarity or embeddings | Find overlooked peers and changing product neighborhoods | Similarity can be competitor, customer, supplier, narrative overlap or boilerplate—not the required relation |
| Unconstrained model labeling | Fast first-pass proposals | Can invent identity, dates, revenue shares and roles; must remain proposal-only |
| Full graph/ontology replacement | Theoretical expressive flexibility | Violates existing owners and creates needless migration/control risk |
| Evidence-qualified activity assertions through current owners | Product-level precision with explainable uncertainty | Requires source work and curation; recommended because errors remain inspectable and reversible |

Hoberg–Phillips product-text work supports dynamic product-neighborhood discovery, not a shortcut from similarity to a particular micro role. SEC's APIs offer submission histories and standard entity-wide facts; a complete product-level economic denominator cannot be assumed from Companyfacts. SKOS's distinction between hierarchical and associative concepts is a useful design check, not permission to replace the frozen GMI representation. GLEIF can support legal-entity reconciliation through Data OS, not a second identity authority. [S090–S093]

## 5. Granular case studies and consequential exclusions

### 5.1 Compute, memory and packaging

The existing `hbm_packaging` label spans two economically different activities: memory products and package integration. The research keeps that admitted ID unchanged while placing candidates into explicit roles. TSMC, ASE and Amkor are not assigned the same memory-manufacturer role as the HBM product suppliers. This is a reason to maintain D03's owner review, not silently execute the deferred split. [S001–S003, S010–S012]

The same treatment applies to interconnect. A named switch, NIC or DPU supports a silicon role; an optical module or system-level network operator would need a different product claim. This investigation does not invent optical suppliers merely to make a longer list. D04 remains a scope/admission review. [S005, S007–S009]

Ordinary DRAM and NAND/SSD activity remain visible rather than disappearing inside an HBM label. The product dimensions are separated, but a supplier's overlapping roles cannot be summed as independent issuer observations. Sandisk's separation makes the corporate boundary time-dependent; copying an old parent's constituents would be particularly misleading. [S016–S017, S094]

### 5.2 The CPU gap must be solved without disguising general compute as AI

The existing 68 micros do not include a general CPU micro, and current C0 expressly defers CPU admission. New primary evidence makes this worth a **focused owner decision**. Intel's Xeon and Ethernet launch distinguishes CPU, network-controller and future GPU activities. AMD's July 2026 announcement distinguishes server CPU products, merchant accelerators and particular customer deployment plans. Arm now describes both licensing/CSS and direct-silicon offerings. [S096–S099]

The proposed review should distinguish: general server CPU supply; explicitly evidenced AI/HPC host/orchestration CPU use; and CPU intellectual-property/subsystem licensing. These are research scope labels, not minted node IDs. A separate direct-silicon activity can coexist with licensing within Arm; neither the old pure-licensing label nor a new all-revenue chip-sales label is defensible.

The first question is which existing canonical parent or revised compute scope can honestly contain those activities. The second is whether a named user/machine consumer benefits from a new micro versus existing product-role context. Only then should the owner consider a dated admission/migration. Until that decision, the CPU supplement remains outside the 68-micro membership input. This avoids losing a useful economic development while preserving ontology boundaries.

### 5.3 Infrastructure and nuclear stages

Cooling equipment, UPS, transformers and HVDC cable systems are related but not interchangeable. Product-level roles prevent one diversified electrical issuer from being represented as several independent pure plays. An HVDC contract is a participation receipt, not a commissioning date. [S018–S025]

Nuclear requires even stricter stage labeling. A licensed design is not an operating reactor. A components vendor is not automatically a reactor designer. Fuel mining, conversion and enrichment are different activities, and a demonstration cascade is not its planned commercial expansion. The current combined fuel-cycle ID can support role-qualified evidence without premature canonical splits. [S026–S029]

### 5.4 Cybersecurity and corporate identity

Product roles identify endpoint, network, identity and cloud-security activities. Corporate actions determine how those businesses connect to present-day securities. Acquired businesses retain historical evidence and product identity, but cannot be counted as independent current issuer samples merely because old ticker lists still contain them. This is why business name, proposed parent hint and canonical issuer ID are separate fields. [S030–S034]

### 5.5 Robotics and healthcare overlap

A collaborative arm, mobile robot, industrial arm, servo actuator and vision system are distinct activities. Teradyne's operating businesses illustrate why a parent-level “robotics” label is insufficient. FANUC's product range illustrates why collaborative/industrial overlap does not imply a second issuer. Surgical robotics has legitimate medical-device and automation context, but one installed platform and issuer remain one subject. [S044–S051]

In healthcare, an oral formulation or new indication is often a facet of the same molecule/issuer. API manufacturing, sterile fill-finish, containment and delivery hardware are upstream or adjacent roles, not equivalent therapy originators. A supplier's capability statement does not reveal an undisclosed pharmaceutical customer. Regulatory approval, market availability and sales are separate evidence classes. [S052–S056]

Liquid biopsy provides another useful distinction: assay ownership versus ordering, collection and distribution. Sequencing instruments and research protein-analysis systems are separate tools; neither automatically becomes a clinically authorized assay. Targeted protein panels also remain a scope-review case when the proposed micro explicitly says discovery platforms. [S076–S081]

### 5.6 Materials and solar: do not substitute a supply-chain story for membership

Mining, separated oxides, metals/alloys, magnets, smelting and wire fabrication require different product/asset evidence. The same integrated issuer can occupy several roles while remaining one economic subject. Germanium capability does not establish gallium activity. Explicit utility-structure products are a better basis for the constrained structural-steel micro than adding the whole steel industry. [S062–S069]

Solar shows why technology and stage need to remain visible. Crystalline-silicon and CdTe module manufacturers differ in feedstock relevance. Trackers, non-inverter BOS and inverters are different products. A rebranded tracker company announcing a future conversion line does not automatically have current inverter shipments. These distinctions are important even before any return forecasting is attempted. [S082–S087, S100]

## 6. Recommended qualification workflow

### A. Define a falsifiable membership predicate

Start with the existing micro's meaning and explicit exclusions. The predicate should answer what observable product/activity would qualify and what evidence would disprove the proposed role. A vague “benefits from AI” predicate cannot distinguish direct producers, infrastructure suppliers and buyers. The appendix supplies proposed predicates for owner review, not replacements for the canonical definitions.

### B. Assemble evidence before resolving the investment instrument

Capture the operating-business name, product, role, jurisdiction, stage, source-publication precision and source reference. Prefer actual operating/shipments evidence where available. Keep a product-catalog candidate useful but honestly labeled. Do not discard a valid non-US business merely because a US ticker is absent, and do not invent an ADR or mainland/Hong Kong cross-listing.

### C. Resolve identity through Data OS

Link the business to a legal entity, controlled group, issuer and eligible security using the existing identity owner. Preserve corporate events and effective dates. Resolve one-to-many listings and joint ventures explicitly. A name hint in this research is not that resolution. An unresolved identity must remain a typed gap, not a zero exposure or a guessed canonical ID.

### D. Ratify a group or vertical slice through its current owner

Prefer a qualified existing house group or exact vertical slice. Similar names and overlap are not identity equivalence. If a new group is genuinely necessary, its owning pipeline must assess downstream consumers before admission. The existing census shows that adding baskets can widen prices, options and other all-basket readers. A metadata `tier: micro` flag is not a universal isolation fence. [G3–G5]

### E. Admit a dated group-to-micro binding only through GMI

The frozen hierarchy currently blocks new-tier MEMBER_OF/EXPRESSES use without its amendment/admission path. Do not smuggle membership through a different proposal kind, sidecar YAML, research JSON or ticker-context column. The owner must review endpoint eligibility, consumer behavior, rights and historical meaning before a canonical mapping can materialize. Model proposals cannot self-ratify.

### F. Form measurement cohorts separately

A useful semantic dossier can have one or two clearly evidenced businesses. That does not make its returns, breadth, revisions or options series statistically valid. Each leg needs its own defined population, eligible observations, corporate-action treatment, missingness, concentration and history. Do not pad a thin micro with customers or distant peers to meet an arbitrary member-count minimum.

## 7. Measurement and product value

For the Daily Desk user, the immediate value is a precise answer to “Why does this company appear here?” The explanation should show the product/activity, role, stage, dated source, corporate-identity status and limitations. A company can be a strong semantic example yet a weak equity proxy because the business is small, private, jointly controlled or mixed with unrelated activities.

For machines, the useful output is the same qualified relationship evidence and typed missingness, not a different model-generated truth. F04 can eventually compose a read-time path from the admitted member/group to the micro and parent. The source-to-generation-to-gateway-to-view proof remains required for product acceptance; this research parser does not claim that proof.

A future UI should keep at least three views distinct: businesses with direct evidence; adjacent suppliers/customers/context; and unqualified or development-stage candidates. Filtering by role or stage must not silently change the declared denominator. A thin or missing measurement displays a reason, not a fabricated zero or a reassuring “low exposure” badge.

No return experiment was run here. The research does not establish alpha, a winning theme, validated timing or a buy recommendation. Semantic precision can improve explanation and measurement input quality; incremental forecasting benefit is an empirical hypothesis. Existing E1, future preregistered companions and downstream decision authority remain separate.

### Evaluation before scaling

Construct an owner-reviewed reference set with both positive cases and hard negatives. Split by issuer and time, not random duplicated snippets from the same product page. Measure source entailment, correct role, stage/time accuracy, corporate-identity correctness, unnecessary abstention and missed qualified candidates separately. Report review disagreement and adjudication rather than hiding it in one accuracy number.

For recall, declare the reference population: an exchange universe, a defined issuer sector set or an owner-curated industry list with rights. This report's searched candidates cannot serve as a recall denominator. Non-English and non-US candidates should be evaluated explicitly so a disclosure-language bias does not masquerade as economic absence.

Measure review workload as well as model quality: accepted assertions per review hour, stale assertions detected, false positive removals and the share of unresolved cases requiring source acquisition. These are proposed operational metrics, not observed improvements or model-performance promises.

## 8. Refresh, cost and correction strategy

Reuse existing collection, identity and evidence pipelines. Product launches, filings, acquisition closings, delistings, regulatory decisions and operating/commissioning updates should invalidate the relevant assertion's current projection through the incumbent owners. A routine coverage audit can find missing changes; this commission does not install a watcher, scheduler or new source service.

Use cheap deterministic checks for format, IDs, dates, duplicate records and source-reference integrity. Use language models for candidate discovery and constrained evidence extraction. Reserve difficult scope, corporate-perimeter and disputed membership judgments for the curator or appropriate vertical owner. Economic shares require disclosed or explicitly estimated inputs under their existing authority, never free-form model fractions.

Official public data minimizes procurement but does not eliminate ingestion, language, rights and maintenance cost. SEC standard facts are helpful for entity-level context; product segmentation often still requires the actual filing narrative or segment note. Do not infer that an API's presence makes the required field available, free for every use or sufficiently current. [S091]

On correction, append an owner-supported superseding belief and retain the prior evidence. A source withdrawal or use refusal may suppress current projection without rewriting old observations. Research records can be versioned on GitHub, but GitHub must not become a competing runtime membership database. Fresh evidence for a rejected subject must use the incumbent reconsideration path, not evade rejection by minting a new arbitrary identity.

## 9. Immediate implementation and limits

The safe first source increment is an **explicit research-input mode** on the existing overlap/membership evidence CLI. It should validate the document, enumerate micro coverage, display all candidate/activity records with primary references, separate stage classes and unresolved identities, and refuse any asserted canonical admission or decision authority. Existing `--review` behavior and byte-level output remain unchanged.

The parser's checks are structural: well-formed inputs, known existing micro references, source-reference closure, dates, no duplicate records, no contradictory status/authority fields and truthful totals. They do **not** authenticate a publisher, verify that a page entails every sentence, settle rights, ratify membership or prove identity. The output must say so. An input hash is only a document-integrity identifier.

The input is a commissioned research artifact, not an operational vocabulary or cohort store. The CLI never polls sources, calls providers, reads price stores, creates graph edges, appends proposals, builds baskets or writes production state. The only optional file output is a new user-specified review file, following the existing non-overwrite convention. This gives a named consumer—the incumbent curator/reviewer—an executable way to inspect and challenge the research.

The next canonical implementation remains gated: select a small group/slice pilot; obtain Data OS and product-role evidence; receive the GMI endpoint/admission amendment and necessary vertical countersign; then prove the actual read-time human and machine consumer while keeping forbidden effects unchanged. No independently useful code path is a substitute for those approvals.

## 10. Risks, falsifiers and remaining obligations

The most serious false positives are roles inferred from customers, future stages presented as current, acquired businesses counted twice, generic company descriptions treated as product shares, and parent memberships copied into children. The attached counterexamples are intended to make those failure modes reviewable. Passing a structural parser cannot eliminate them; source/curator review remains required.

The strongest counterargument to the recommended approach is cost: fine-grained membership can become a labor-intensive taxonomy project whose maintenance exceeds its user value. The response is not automatic unrestricted labeling. Start with product explanations and a small set of economically coherent, observable roles; require a named consumer and measurable reduction in ambiguity before adding a canonical split or a new measured cohort.

A second risk is apparent precision. A detailed matrix with one candidate per micro can look complete despite unknown recall and no admitted identities. This report deliberately labels its searched population, retains null IDs/shares and separates structural coverage from qualified cohorts. The candidate appendix should never be imported as a production member list.

A third risk is stale disclosure. Older readiness announcements do not prove current shipments, but neither do they prove shipments never happened. Such records keep their source-stage description and request a later receipt. Current product pages do not establish historical existence. Refresh is an owner obligation, not an excuse to back-project today's roster.

A fourth risk is scope drift. CPU, optical interconnect, HBM/packaging, targeted versus discovery proteomics and medicine formulation/indication boundaries require actual owner decisions. Their unresolved status is informative research, not a reason to guess or replace the accepted ontology.

**Research results:** complete 68-ID review map, named source-linked activity candidates, exclusions, CPU supplement and implementation recommendation. **Still unverified:** complete worldwide membership, Data OS-qualified security mappings, canonical admissions, product-level economic shares, state measurement fitness, predictive benefit, real served user/machine proof and release acceptance. The source review and test receipts added below identify what implementation was actually performed; nothing in this prose self-accepts a deployment.

## 11. Reproducibility and acceptance boundary

The machine file records the exact Macro/crosswalk/procedure references, source dates with precision, record identifiers, null identity/economic fields and publication restrictions. Each existing micro occurs once in its definition section; candidates refer only to those IDs. CPU-review labels are isolated from that section and cannot become graph IDs through the review path.

The package should be checked for the complete 68-ID set, unique source/record IDs, no dangling references, chronological consistency and forbidden authority. After implementation, run the explicit research CLI against this actual dataset and inspect both JSON and Markdown output. Run existing overlap-reader tests to establish unchanged default behavior, and add refusal tests for malformed input, unexpected micro IDs, duplicate records, future publication, private/unsafe URL forms and attempted authority escalation.

Passing those checks proves the research document is mechanically reviewable. It does not convert the source excerpts into independent validation of every proposed membership. Required independent review, binding hosted CI, normal release admission and future natural product proof retain their own status.

## 12. Granular 68-micro review appendix

The following table is generated from the same research records as the JSON. Every entry is **unadmitted research**, and all security identities and economic shares remain unqualified/null. “Commercial evidence” describes what the cited disclosure reports; it is not an investment recommendation or a claim that this session independently audited the business.

| Existing micro | Investigated business/activity candidates | Source references |
|---|---|---|
| `theme:hbm_packaging` | Micron — HBM4 36GB 12H; Samsung Electronics — HBM4; SK hynix — HBM4 development and production readiness; TSMC — CoWoS and 3DFabric; ASE — VIPack; Amkor — Advanced packaging and test | [S001], [S002], [S003], [S010], [S011], [S012] |
| `theme:gpu_merchant_accelerators` | NVIDIA — Rubin GPU; AMD — Instinct MI400 and MI350 families | [S004], [S005], [S006], [S097] |
| `theme:ai_interconnect_silicon` | NVIDIA — Spectrum switch, ConnectX NIC and BlueField DPU; Broadcom — Tomahawk Ultra; Marvell — UALink scale-up solution; Intel — E835 Ethernet controllers | [S005], [S007], [S008], [S009], [S096] |
| `theme:custom_asic_silicon` | Marvell — Custom compute platform | [S008], [S009] |
| `theme:conventional_dram` | Micron — DDR and LPDDR components/modules | [S094] |
| `theme:nand_enterprise_storage` | Micron — 9650 data-center SSD; Sandisk — NAND technology and flash products; Kioxia — Jointly developed 3D NAND | [S001], [S016], [S017] |
| `theme:lithography_tools` | ASML — EUV and DUV lithography systems; Nikon — Semiconductor lithography systems | [S013], [S088] |
| `theme:etch_deposition_equipment` | Lam Research — Etch and deposition systems; Tokyo Electron — EXIM and LEXIA-EX; KLA — Chip-manufacturing etch and deposition product families | [S014], [S089], [S095] |
| `theme:process_metrology_inspection` | ASML — Metrology and inspection systems; KLA — Chip and wafer inspection/metrology | [S013], [S095] |
| `theme:wafer_fab_subsystems` | VAT — Vacuum isolation and pressure-control valves | [S015] |
| `theme:liquid_cooling_thermal` | Vertiv — CoolChip CDU; Motivair — Liquid-cooling portfolio | [S018], [S019] |
| `theme:hv_transformers_switchgear` | GE Vernova Grid Solutions — Transformers and switchgear; Eaton — Switchgear manufacturing | [S022], [S023] |
| `theme:ups_power_conversion` | Eaton — 93PM UPS; Schneider Electric — Galaxy VXL | [S020], [S021] |
| `theme:reactor_technology` | NuScale Power — 77 MWe SMR design | [S029] |
| `theme:nuclear_components` | BWXT — Nuclear components and equipment | [S028] |
| `theme:fuel_cycle` | Cameco — Refining, conversion and fuel manufacturing; Centrus Energy — HALEU demonstration cascade and expansion contract | [S026], [S027] |
| `theme:grid_distribution_automation` | Aclara — Utility grid-edge software; GE Vernova Grid Solutions — Grid automation products | [S023], [S025] |
| `theme:transmission_hvdc_cabling` | Prysmian — Eastern Green Link 4 | [S024] |
| `theme:endpoint_security` | CrowdStrike — Falcon endpoint and runtime security | [S030] |
| `theme:network_security` | Fortinet — FortiGate | [S031] |
| `theme:identity_access_management` | Okta — Workforce Identity; CyberArk — Identity Security platform | [S032], [S033] |
| `theme:cloud_security` | Wiz — Cloud-security platform | [S034] |
| `theme:missiles_munitions_effects` | Raytheon — Patriot and interceptor systems; Javelin joint venture — Javelin weapon system | [S035], [S038] |
| `theme:missile_propulsion_supply` | L3Harris — Javelin and PAC-3 MSE propulsion | [S035], [S036] |
| `theme:defense_sensors_electronics_c2` | Raytheon — LTAMDS | [S039] |
| `theme:autonomous_systems_counter_uas` | AeroVironment — Autonomous systems and post-BlueHalo capability; Raytheon — KuRFS | [S040], [S042] |
| `theme:naval_shipbuilding` | Newport News Shipbuilding — Virginia-class submarine construction; Electric Boat — Virginia-class submarine construction | [S037] |
| `theme:aerospace_components_aftermarket` | Collins Aerospace — Aerostructures and aftermarket | [S041] |
| `theme:military_space_communications` | L3Harris — SDA communications payload design | [S043] |
| `theme:machine_vision` | Cognex — 3D laser profilers | [S044] |
| `theme:industrial_motion_controls` | Rockwell Automation — Kinetix motion-control system | [S048] |
| `theme:collaborative_robot_arms` | Universal Robots — Collaborative robot arms; FANUC — CRX collaborative arm | [S045], [S047] |
| `theme:industrial_robot_arms` | FANUC — Industrial robot range | [S046] |
| `theme:precision_actuators_servo_motors` | Rockwell Automation — Kinetix VPC servo motors; Harmonic Drive product business — FHA-C-H servo actuators | [S048], [S049] |
| `theme:surgical_robotics_systems` | Intuitive Surgical — da Vinci systems | [S050] |
| `theme:glp1_incretin_therapies` | Eli Lilly — Orforglipron / Foundayo; Novo Nordisk — Semaglutide products | [S052], [S053], [S054] |
| `theme:oral_glp1_formulations` | Eli Lilly — Oral orforglipron; Novo Nordisk — Oral semaglutide | [S052], [S053], [S054] |
| `theme:glp1_api_manufacturing` | Bachem — GLP-1 peptide development and GMP API | [S055] |
| `theme:cardiorenal_metabolic_indications` | Novo Nordisk — Semaglutide indication expansion | [S054] |
| `theme:fill_finish_delivery_devices` | Stevanato Group — Ready-to-use cartridges | [S056] |
| `theme:launch_services` | Rocket Lab — Electron launches | [S057] |
| `theme:satellite_broadband_services` | Viasat — Satellite broadband service; Gogo — Galileo aviation connectivity | [S060], [S061] |
| `theme:direct_to_device_connectivity` | AST SpaceMobile — BlueBird direct-to-device system | [S059] |
| `theme:earth_observation` | Planet — Pelican imagery | [S058] |
| `theme:satellite_ground_terminals` | Hughes — HDX and FDX electronically steered terminals | [S060] |
| `theme:rare_earth_separation_refining` | MP Materials — Separated NdPr products; Lynas Rare Earths — Separated rare-earth oxides | [S062], [S063], [S064] |
| `theme:ndfeb_permanent_magnets` | MP Materials — Independence NdFeB magnet production | [S062], [S063] |
| `theme:critical_mineral_mining_development` | MP Materials — Mountain Pass rare-earth operation; Lynas Rare Earths — Mine-to-separated-oxide activities | [S062], [S064] |
| `theme:gallium_germanium_supply_chain` | 5N Plus — Germanium recovery, recycling and refining | [S065] |
| `theme:copper_mining` | Freeport-McMoRan — Copper mine production | [S066] |
| `theme:refined_copper` | Freeport-McMoRan — Indonesia smelter restart; Aurubis — Copper processing operations | [S066], [S067] |
| `theme:structural_steel_electrification` | Nucor — Utility towers and structures | [S068] |
| `theme:copper_wire_cable` | Prysmian / Encore Wire — Copper building wire | [S069] |
| `theme:nitrogen_fertilizer_production` | CF Industries — Ammonia, urea and UAN | [S070] |
| `theme:potash_phosphate_nutrients` | Nutrien — Potash production | [S071] |
| `theme:precision_agriculture_platforms` | John Deere — See and Spray Select | [S072] |
| `theme:medical_imaging` | GE HealthCare — LOGIQ ultrasound systems | [S073] |
| `theme:remote_patient_monitoring` | Abbott — Libre sensing and LibreLinkUp | [S074] |
| `theme:surgical_implants_instruments` | Stryker — Triathlon knee implants; Intuitive Surgical — da Vinci instruments | [S051], [S075] |
| `theme:liquid_biopsy_assays` | Guardant Health — Shield blood-based screening assay | [S076], [S077] |
| `theme:genomic_sequencing` | Illumina — NovaSeq X | [S078] |
| `theme:proteomics_discovery_platforms` | Thermo Fisher Scientific — Orbitrap Astral Zoom; Quanterix — Simoa HD-X | [S079], [S080] |
| `theme:life_science_lab_instruments` | Thermo Fisher Scientific — Orbitrap laboratory systems | [S079] |
| `theme:diagnostic_reagents_kits` | Roche — cobas MPX-E | [S081] |
| `theme:pv_cell_module_manufacturing` | First Solar — Series 7 CdTe modules; JinkoSolar — PV modules | [S082], [S083] |
| `theme:polysilicon_solar_feedstock` | Daqo New Energy — Solar-grade polysilicon | [S084] |
| `theme:solar_inverters` | Enphase Energy — IQ8 microinverters | [S085] |
| `theme:solar_trackers_bos` | Nextpower, formerly Nextracker — NX Horizon and tracker/BOS portfolio | [S086], [S087], [S100] |

### Current intermediate subthemes — navigation only

The 12 accepted `sub_theme` nodes are intermediate house context, not new member cohorts. Twenty-seven micros have a subtheme parent as well as their retained direct theme-parent edge; do not double-count issuers or multiply population denominators.

| Subtheme | Mapped microtheme children | Display value-chain position |
|---|---|---|
| `theme:wfe_process_tools` | `theme:etch_deposition_equipment`, `theme:lithography_tools`, `theme:process_metrology_inspection` | unknown |
| `theme:ai_compute_silicon` | `theme:custom_asic_silicon`, `theme:gpu_merchant_accelerators` | unknown |
| `theme:missile_munition_chain` | `theme:missile_propulsion_supply`, `theme:missiles_munitions_effects` | unknown |
| `theme:satellite_connectivity_services` | `theme:direct_to_device_connectivity`, `theme:satellite_broadband_services` | downstream |
| `theme:robot_arm_systems` | `theme:collaborative_robot_arms`, `theme:industrial_robot_arms` | midstream |
| `theme:glp1_therapy_products` | `theme:glp1_incretin_therapies`, `theme:oral_glp1_formulations` | midstream |
| `theme:glp1_supply_chain` | `theme:fill_finish_delivery_devices`, `theme:glp1_api_manufacturing` | unknown |
| `theme:rare_earth_processing_magnets` | `theme:ndfeb_permanent_magnets`, `theme:rare_earth_separation_refining` | unknown |
| `theme:copper_supply_chain` | `theme:copper_mining`, `theme:copper_wire_cable`, `theme:refined_copper` | unknown |
| `theme:multi_omics_platforms` | `theme:genomic_sequencing`, `theme:liquid_biopsy_assays`, `theme:proteomics_discovery_platforms` | unknown |
| `theme:pv_manufacturing_chain` | `theme:polysilicon_solar_feedstock`, `theme:pv_cell_module_manufacturing` | unknown |
| `theme:ai_clinical_data_devices` | `theme:medical_imaging`, `theme:remote_patient_monitoring` | midstream |

### Exact count and evidence-stage disclosure

The artifact contains **68 definitions, 103 candidate activity records, 100 source references, 14 negative review cases and 3 CPU scope-review records**. These are document counts, not qualified issuer counts. Canonical memberships admitted, Data OS identities qualified and measured cohorts admitted are all **zero** in this delivery.

| Evidence-stage label | Activity records |
|---|---:|
| CAPABILITY_EVIDENCE | 10 |
| COMMERCIAL_EVIDENCE | 27 |
| CONTRACT_EVIDENCE | 3 |
| DEVELOPMENT_EVIDENCE | 7 |
| OFFERED_PRODUCT | 55 |
| SCOPE_REVIEW | 1 |

`COMMERCIAL_EVIDENCE` means a source reports relevant commercial or operating behavior at its own clock. `OFFERED_PRODUCT` is a catalog/offer, `CAPABILITY_EVIDENCE` does not establish sold volume, `CONTRACT_EVIDENCE` does not establish commissioning, `DEVELOPMENT_EVIDENCE` is not full commercial operation, and `SCOPE_REVIEW` is a contested fit. None asserts present-day Data OS-qualified investment membership.

## 13. Source register

Public links and short paraphrases only. Source publication dates are reproduced at their supported precision; undated pages remain undated. Some research used indexed extracts rather than a retained full document. Do not treat this catalog as an authenticity or rights receipt.

**[S001] Micron** — 2026-03-16. HBM4 volume production, PCIe Gen6 SSD and SOCAMM2 are distinct product roles; higher-stack samples are not equivalent to volume shipments. [Primary reference](https://investors.micron.com/news/press-release/2026/Micron-in-High-Volume-Production-of-HBM4-Designed-for-NVIDIA-Vera-Rubin-PCIe-Gen6-SSD-and-SOCAMM2-03-16-2026/default.aspx).

**[S002] Samsung** — 2026-02-12. Samsung reports commercial HBM4 shipment and mass production. [Primary reference](https://news.samsung.com/global/samsung-ships-industry-first-commercial-hbm4-with-ultimate-performance-for-ai-computing).

**[S003] SK hynix** — 2025-09-12. HBM4 development and readiness are documented; this item alone is not proof of subsequent volume shipment. [Primary reference](https://news.skhynix.com/en/sk-hynix-completes-worlds-first-hbm4-development-and-readies-mass-production/).

**[S004] NVIDIA** — 2026-05-31. Rubin platform production announcement identifies GPUs, networking and system partners separately. [Primary reference](https://nvidianews.nvidia.com/news/vera-rubin-full-production-agentic-ai-factory).

**[S005] NVIDIA** — 2026-01-05. Rubin GPU, Vera CPU, ConnectX NIC, BlueField DPU and Spectrum switch are distinct roles within one issuer. [Primary reference](https://nvidianews.nvidia.com/news/rubin-platform-ai-supercomputer).

**[S006] AMD** — 2025. Instinct MI350 accelerators are distinguished from the MI400 roadmap; roadmap dates do not prove delivery. [Primary reference](https://www.amd.com/en/blogs/2025/amd-instinct-mi350-series-and-beyond-accelerating-the-future-of-ai-and-hpc.html).

**[S007] Broadcom** — publication date not established. Tomahawk Ultra is Ethernet switching silicon for AI and HPC, not an optical transceiver. [Primary reference](https://www.broadcom.com/products/ethernet-connectivity/switching/strataxgs/bcm78920-series).

**[S008] Marvell** — 2025-06-11. Custom compute platform and UALink scale-up solution support a custom-silicon candidate role, not customer-specific revenue attribution. [Primary reference](https://investor.marvell.com/news-events/press-releases/detail/94/marvell-expands-custom-compute-platform-with-ualink-scale-up-solution-for-ai-accelerated-infrastructure).

**[S009] Marvell** — 2026-03-31. NVLink Fusion partnership supports proposed custom-compute/connectivity development; production stage is not established by partnership alone. [Primary reference](https://www.marvell.com/company/newsroom/nvidia-ai-ecosystem-expands-marvell-joins-forces-through-nvlink-fusion.html).

**[S010] TSMC** — publication date not established. 3DFabric and CoWoS are foundry/integration packaging services; they do not make TSMC an HBM DRAM manufacturer. [Primary reference](https://www.tsmc.com/english/dedicatedFoundry/technology/platform_HPC_tech_WLSI).

**[S011] ASE** — publication date not established. VIPack is an advanced packaging integration platform; packaging-service participation differs from memory product ownership. [Primary reference](https://ase.aseglobal.com/VIPack/).

**[S012] Amkor** — 2024-10-03. Packaging/test business and TSMC collaboration are documented; the announced US facility is not proof that future capacity is already operating. [Primary reference](https://ir.amkor.com/news-releases/news-release-details/amkor-and-tsmc-expand-partnership-and-collaborate-advanced).

**[S013] ASML** — publication date not established. ASML offers EUV/DUV lithography and metrology/inspection systems as distinct product families. [Primary reference](https://www.asml.com/en/products).

**[S014] Lam Research** — publication date not established. Named etch and deposition tool families support wafer-process equipment participation. [Primary reference](https://www.lamresearch.com/products/our-products/).

**[S015] VAT** — publication date not established. Vacuum pressure-control and isolation valves are fab subsystems, not complete lithography or etch tools. [Primary reference](https://www.vatgroup.com/vacuum-valves/pendulum-vacuum-valves).

**[S016] Sandisk** — 2025-02-24. Sandisk began independent Nasdaq trading after separation; legacy Western Digital flash labels require date-aware identity reconciliation. [Primary reference](https://investor.sandisk.com/news-releases/news-release-details/sandisk-celebrates-nasdaq-listing-after-completing-separation).

**[S017] Sandisk** — 2025-02-19. Kioxia and Sandisk develop NAND technology; next-generation development and current-generation production are different stages. [Primary reference](https://www.sandisk.com/en-us/company/newsroom/press-releases/2025/kioxia-and-sandisk-unveil-next-generation-3d-flash-memory-technology).

**[S018] Vertiv** — publication date not established. CoolChip CDUs are liquid-cooling infrastructure products. [Primary reference](https://www.vertiv.com/en-us/products-catalog/thermal-management/high-density-solutions/vertiv-coolchip-cdu/).

**[S019] Schneider Electric** — 2025-09-29. Motivair liquid-cooling portfolio is offered through Schneider; a controlled business is not a separate listed issuer. [Primary reference](https://www.se.com/us/en/about-us/newsroom/news/press-releases/schneider-electric-unveils-liquid-cooling-portfolio-with-motivair-featuring-dedicated-solutions-and-services-for-hpc-and-ai-workloads-68da975376d417f4a10de42c/).

**[S020] Schneider Electric** — publication date not established. Galaxy VXL is an uninterruptible power supply product; do not infer all Schneider revenue is data-center power. [Primary reference](https://www.se.com/us/en/about-us/newsroom/news/press-releases/schneider-electric-announces-new-solutions-to-address-the-energy-and-sustainability-challenges-spurred-by-ai-674f1aaeda55de201f0ca8c4/).

**[S021] Eaton** — publication date not established. 93PM is a UPS product, distinct from transformer and switchgear activities. [Primary reference](https://www.eaton.com/us/en-us/catalog/backup-power-ups-surge-it-power-distribution/eaton-93pm-ups.html).

**[S022] Eaton** — 2026. Switchgear activity is documented; new facility commissioning remains prospective. [Primary reference](https://www.eaton.com/us/en-us/company/news-insights/news-releases/2026/eaton-expands-operations-in-nebraska-with-new-manufacturing-facility.html).

**[S023] GE Vernova** — publication date not established. Grid Solutions contains transformer, switchgear, HVDC and grid-automation product roles; shares by microtheme are not supplied. [Primary reference](https://www.gevernova.com/grid-solutions).

**[S024] Prysmian** — 2026-02-02. Eastern Green Link 4 is a contracted HVDC cable project; contract signing is not project commissioning. [Primary reference](https://www.prysmian.com/en/media/press-releases/prysmian-signs-contract-for-the-delivery-of-eastern-green-link-4).

**[S025] Hubbell** — 2026-01-27. Aclara utility software supports distribution/grid-edge data and control activities. [Primary reference](https://www.hubbell.com/aclara/en/news/hubbell-launches-modular-scalable-software-that-transforms-utility).

**[S026] Cameco** — publication date not established. Refining, conversion and fuel manufacturing are distinct fuel-services roles; individual product output is not universally disclosed. [Primary reference](https://www.cameco.com/businesses/fuel-services).

**[S027] Centrus** — 2026-07-01. Demonstration production and proposed commercial expansion are different activity stages. [Primary reference](https://www.centrusenergy.com/news/centrus-signs-contract-with-department-of-energy-for-900-million-award-intends-to-transition-haleu-production-cascade-to-commercial-operation/).

**[S028] BWXT** — publication date not established. Nuclear components and equipment include steam generators and other reactor hardware. [Primary reference](https://www.bwxt.com/sectors/nuclear-energy/components-equipment/).

**[S029] NuScale** — 2025-05-29. Design approval establishes reactor-technology development, not an operating reactor fleet. [Primary reference](https://www.nuscalepower.com/press-releases/2025/nuscale-powers-small-modular-reactor-smr-achieves-standard-design-approval-from-us-nuclear-regulatory-commission-for-77-mwe).

**[S030] CrowdStrike** — 2026-03-23. Falcon endpoint and runtime-security products are documented; customer adoption of AI does not turn the vendor into a GPU producer. [Primary reference](https://www.crowdstrike.com/en-us/press-releases/crowdstrike-establishes-the-endpoint-as-the-epicenter-for-ai-security/).

**[S031] Fortinet** — publication date not established. FortiGate is a network firewall product family. [Primary reference](https://www.fortinet.com/products/next-generation-firewall).

**[S032] Okta** — publication date not established. Workforce identity contains authentication, access and governance capabilities. [Primary reference](https://www.okta.com/products/workforce-identity).

**[S033] Palo Alto Networks** — 2026-02-11. CyberArk acquisition completed; its identity-security activity must not be counted as an independent listed issuer after closing. [Primary reference](https://investors.paloaltonetworks.com/news-releases/news-release-details/palo-alto-networks-completes-acquisition-cyberark-secure--ai-era).

**[S034] Google** — 2026-03-11. Wiz acquisition completed into Google Cloud; the business remains a cloud-security subject, not a separately listed security. [Primary reference](https://blog.google/innovation-and-ai/infrastructure-and-cloud/google-cloud/wiz-acquisition/).

**[S035] L3Harris** — 2025-09-15. Propulsion supplier role differs from the Lockheed Martin/Raytheon prime joint venture. [Primary reference](https://www.l3harris.com/newsroom/press-release/2025/09/l3harris-receives-multi-year-javelin-solid-rocket-motor-contract).

**[S036] L3Harris** — 2026-09-08. Contracted propulsion supply supports a component-supplier role, not attribution of the entire system value. [Primary reference](https://www.l3harris.com/newsroom/press-release/2026/09/l3harris-receives-pac-3-mse-propulsion-arsenal-of-freedom).

**[S037] HII** — publication date not established. HII/Newport News and General Dynamics/Electric Boat have distinct partner shipbuilding roles. [Primary reference](https://www.hii.com/products/virginia-class).

**[S038] RTX** — publication date not established. Raytheon system and interceptor activity supports the missile/effects role. [Primary reference](https://www.rtx.com/raytheon/what-we-do/integrated-air-and-missile-defense/global-patriot-solutions).

**[S039] RTX** — publication date not established. LTAMDS is a defense sensor role, not a separate issuer or equivalent missile manufacturing role. [Primary reference](https://www.rtx.com/raytheon/what-we-do/integrated-air-and-missile-defense/ltamds).

**[S040] RTX** — publication date not established. Counter-UAS sensing and systems participation is documented at product-role level. [Primary reference](https://www.rtx.com/raytheon/what-we-do/integrated-air-and-missile-defense/kurfs).

**[S041] RTX** — publication date not established. Collins supplies aerostructures and aftermarket services, distinct from aircraft airline operation. [Primary reference](https://www.rtx.com/collinsaerospace/what-we-do/Industries/commercial-aviation/aerostructures/).

**[S042] AeroVironment** — 2025-09-09. Post-BlueHalo results distinguish autonomous systems and space/cyber/directed-energy business activity. [Primary reference](https://investor.avinc.com/node/19956).

**[S043] L3Harris** — 2024-11-25. Military-space communications payload work is a development/supplier role, not consumer satellite subscriptions. [Primary reference](https://www.l3harris.com/newsroom/editorial/2024/11/l3harris-completes-critical-design-review-space-development-agency).

**[S044] Cognex** — publication date not established. Industrial machine-vision profiling systems support inspection and robot-guidance applications. [Primary reference](https://www.cognex.com/products/machine-vision/3d-laser-profilers).

**[S045] Universal Robots** — 2026-06-18. Universal Robots arms and MiR mobile robots are different activities under Teradyne Robotics. [Primary reference](https://www.universal-robots.com/news-and-media/news-center/teradyne-robotics-unveils-wide-range-production-ready-physical-ai-applications-automate-2026/).

**[S046] FANUC** — publication date not established. Industrial robot products are documented, including an overlapping collaborative line. [Primary reference](https://www.fanucamerica.com/products/robot).

**[S047] FANUC** — publication date not established. CRX is a collaborative robot-arm product, not evidence that a second independent company exists. [Primary reference](https://www.fanucamerica.com/products/robot/crx-10ia).

**[S048] Rockwell Automation** — publication date not established. Kinetix motion-control and servo motor activity supports specific industrial motion roles. [Primary reference](https://www.rockwellautomation.com/en-us/products/hardware/motion-control/kinetix-vpc-continuous-duty.html).

**[S049] Harmonic Drive** — publication date not established. Integrated rotary servo actuator activity is documented; public-parent identity needs Data OS reconciliation. [Primary reference](https://www.harmonicdrive.net/products/rotary-actuators/hollow-shaft-servo-actuators/fha-c-h).

**[S050] Intuitive Surgical** — 2026-01-22. Reported da Vinci placements support actual commercial surgical-robot systems, not approval alone. [Primary reference](https://isrg.intuitive.com/news-releases/news-release-details/intuitive-announces-fourth-quarter-earnings-5).

**[S051] Intuitive Surgical** — publication date not established. Surgical instruments are a consumables/product role within the same issuer as the platform. [Primary reference](https://www.intuitive.com/en-us/products-and-services/da-vinci/instruments).

**[S052] Lilly** — 2026-04-09. Oral orforglipron commercial availability follows approval; it is a small molecule, not a peptide API demand proxy. [Primary reference](https://investor.lilly.com/news-releases/news-release-details/foundayotm-orforglipron-lillys-new-oral-glp-1-pill-weight-loss).

**[S053] FDA** — 2026-04-01. Regulatory approval is a dated, jurisdiction-specific product fact, not a general investment claim. [Primary reference](https://www.fda.gov/news-events/press-announcements/fda-approves-first-new-molecular-entity-under-national-priority-voucher-program).

**[S054] Novo Nordisk** — 2025. Semaglutide products, oral formulation and expanded indications share an issuer and often the same molecule; avoid duplicate factor counts. [Primary reference](https://annualreport.novonordisk.com/2025/introducing-novo-nordisk/2025-at-a-glance.html).

**[S055] Bachem** — publication date not established. GLP-1 peptide development and GMP API capability are described; customer identities and product-specific commercial revenue remain undisclosed here. [Primary reference](https://www.bachem.com/knowledge-center/glucagon-like-peptide-1-glp-1/).

**[S056] Stevanato Group** — 2026. Ready-to-use cartridges support delivery/containment, not peptide API synthesis; future lines must not be treated as operating. [Primary reference](https://www.stevanatogroup.com/en/news-events/news/co-creation-for-glp-1-rtu-cartridges/).

**[S057] Rocket Lab** — 2026-09-11. An executed Electron launch supports launch-service operations; Neutron remains a separate development-stage program. [Primary reference](https://rocketlabcorp.gcs-web.com/news-releases/news-release-details/rocket-lab-successfully-launches-16th-electron-mission-year).

**[S058] Planet** — publication date not established. Pelican imagery has commercial generation-one operations; generation-two plans are separate. [Primary reference](https://docs.planet.com/data/imagery/pelican/).

**[S059] AST SpaceMobile** — publication date not established. Deployed satellites, demonstrations and commercial agreements support direct-to-device development; global continuous commercial service is not established by launches alone. [Primary reference](https://ast-science.com/our-journey/).

**[S060] Hughes** — 2026-03-23. Hughes shipped terminals and Gogo operates installed aviation connectivity; terminal manufacturing and service operation differ. [Primary reference](https://www.hughes.com/resources/press-releases/hughes-and-gogo-announce-major-milestones-in-leo-connectivity-for-business-aviation).

**[S061] Viasat** — 2026. Satellite broadband business exists; the particular F3 service-entry target is not a commissioning receipt. [Primary reference](https://investors.viasat.com/news-releases/news-release-details/viasat-confirms-viasat-3-f3-satellite-launch-april-27-2026).

**[S062] MP Materials** — 2026-02-26. Rare earth mining/separation and first commercial-equipment NdFeB production are separately described; future 10X capacity is not current output. [Primary reference](https://mpmaterials.com/news/mp-materials-reports-fourth-quarter-and-full-year-2025-results).

**[S063] MP Materials** — publication date not established. Metallization, alloying and magnet finishing are distinct steps within one producer. [Primary reference](https://mpmaterials.com/independence).

**[S064] Lynas** — publication date not established. Mine-to-separated-oxide activities are documented; listed future products are not inferred to be producing without a newer receipt. [Primary reference](https://lynasrareearths.com/products-our-products/us-markets/).

**[S065] 5N Plus** — 2026-01-30. Germanium recycling/refining capability and planned expansion are described; this does not establish gallium mining or the future capacity as operating. [Primary reference](https://www.5nplus.com/fr/nouvelles/5n-se-voit-accorder-une-somme-de-181-m-us/).

**[S066] Freeport-McMoRan** — 2026-10-02. Copper mining output and Indonesia smelter restart are reported; future expansion and nameplate capacity are not actual current output. [Primary reference](https://investors.fcx.com/investors/news-releases/news-release-details/2026/Freeport-Provides-Third-Quarter-2026-Operational-Update/default.aspx).

**[S067] Aurubis** — 2025-07-21. Copper processing plant overhaul completion supports an operating refining/smelting role, not a copper mine role. [Primary reference](https://www.aurubis.com/en/bulgaria/media/press-releases/aurubis-zavurshi-nai-golemiya-kapitalen-remont-na-medodobivniya-zavod-v-bulgariya-za-poslednite-30-godini).

**[S068] Nucor** — publication date not established. Steel utility and transmission structures explicitly connect a steel product business to electrification; no blanket steel-sector inclusion follows. [Primary reference](https://nucor.com/products/towers-and-structures/).

**[S069] Prysmian** — publication date not established. Copper building wire is directly offered; Encore Wire is presented as part of the Prysmian family. [Primary reference](https://na.prysmian.com/markets/electrification/industrial-and-construction/building-wire/copper-building-wire).

**[S070] CF Industries** — publication date not established. Ammonia, urea and UAN support nitrogen-fertilizer production; industrial non-fertilizer applications remain separate. [Primary reference](https://www.cfindustries.com/products).

**[S071] Nutrien** — publication date not established. Potash mine operations support the potassium nutrient facet, not automatic phosphate membership. [Primary reference](https://www.nutrien.com/about/our-business/potash).

**[S072] John Deere** — publication date not established. Computer-vision targeted spraying is a precision-agriculture product; generic equipment ownership is insufficient. [Primary reference](https://www.deere.com/en-us/products-solutions/sprayers-and-applicators/see-spray-select).

**[S073] GE HealthCare** — 2026-02-25. LOGIQ ultrasound systems support imaging equipment participation; availability varies by product and jurisdiction. [Primary reference](https://www.gehealthcare.com/en-us/about/newsroom/press-releases/ge-healthcare-introduces-next-level-logiq-ultrasound-systems-driving-improved-everyday-performance-and-smarter-clinical-insights).

**[S074] Abbott** — publication date not established. Libre sensor data-sharing connects patients, caregivers and clinicians; this is remote monitoring support, not an autonomous treatment system. [Primary reference](https://www.support.freestyle.abbott/hc/en-us/articles/36332656335505-How-does-the-LibreLinkUp-app-work).

**[S075] Stryker** — publication date not established. Triathlon knee implants support an orthopaedic implant role. [Primary reference](https://www.stryker.com/us/en/portfolios/orthopaedics/joint-replacement/knee.html).

**[S076] Guardant Health** — 2024-08-01. Shield is commercially available as a blood-based colorectal screening assay; a sequencer supplier is not thereby the assay owner. [Primary reference](https://investors.guardanthealth.com/press-releases/press-releases/2024/Guardant-Healths-FDA-approved-Shield-Blood-Test-Now-Commercially-Available-in-U-S--as-a-Primary-Screening-Option-for-Colorectal-Cancer/default.aspx).

**[S077] Guardant Health** — 2026-03-10. Quest ordering/collection distribution differs from Guardant assay ownership. [Primary reference](https://investors.guardanthealth.com/press-releases/press-releases/2026/Guardant-Healths-Shield-Blood-based-Screening-Test-for-Colorectal-Cancer-Now-Accessible-Through-National-Test-Ordering-and-Collection-Network-of-Quest-Diagnostics/default.aspx).

**[S078] Illumina** — 2026-03-25. NovaSeq X has existing sequencing capabilities plus a separately identified enhancement roadmap. [Primary reference](https://emea.illumina.com/events/webinar/2026/Next4NSX.html).

**[S079] Thermo Fisher Scientific** — publication date not established. Orbitrap Astral supports protein measurement and research instrumentation, not a clinically approved liquid-biopsy test by itself. [Primary reference](https://www.thermofisher.com/us/en/home/industrial/mass-spectrometry/liquid-chromatography-mass-spectrometry-lc-ms/lc-ms-systems/orbitrap-lc-ms/orbitrap-astral-zoom-mass-spectrometer/technology.html).

**[S080] Quanterix** — publication date not established. Simoa HD-X measures protein biomarkers for research; targeted protein panels differ from discovery-wide proteomics. [Primary reference](https://www.quanterix.com/simoa-hd-x-analyzer/).

**[S081] Roche** — 2026-03-30. cobas MPX-E reagents/assay are available in CE-mark accepting markets; assay sales and instrument platforms are distinct roles. [Primary reference](https://www.roche.com/investors/updates/inv-update-2026-03-30).

**[S082] First Solar** — publication date not established. Series 7 uses CdTe thin film, so a PV module manufacturer need not be a polysilicon consumer. [Primary reference](https://www.firstsolar.com/Products/Series-7).

**[S083] JinkoSolar** — 2026-08-26. Reported module shipments support commercial PV activity; storage shipments are a separate denominator. [Primary reference](https://ir.jinkosolar.com/news-releases/news-release-details/jinkosolar-announces-second-quarter-2026-financial-results).

**[S084] Daqo** — publication date not established. Daqo manufactures polysilicon feedstock for PV manufacturers; downstream module makers are not interchangeable with feedstock producers. [Primary reference](https://www.dqsolar.com/).

**[S085] Enphase** — publication date not established. IQ8 converts PV DC output to AC; its internal ASIC does not qualify as an AI custom accelerator. [Primary reference](https://enphase.com/installers/microinverters).

**[S086] Nextpower** — publication date not established. The company history records the Nextracker-to-Nextpower name change and tracker, foundation and eBOS activities; do not count old/new names twice. [Primary reference](https://nextpower.com/company).

**[S087] Nextpower** — 2024-04-23. NX Horizon tracker availability supports a tracker product role. [Primary reference](https://nextpower.com/post/press-release/nextracker-launches-industrys-first-low-carbon-solar-tracker-solution).

**[S088] Nikon** — publication date not established. Semiconductor lithography and flat-panel-display lithography are distinct businesses; only the semiconductor role is relevant here. [Primary reference](https://www.nikon.com/company/corporate/businesses/precision/).

**[S089] Tokyo Electron** — publication date not established. EXIM and LEXIA-EX deposition products support process-tool participation; they are not semiconductor designers. [Primary reference](https://www.tel.com/product/exim.html).

**[S090] Hoberg and Phillips** — publication date not established. Text-based product similarity creates dynamic competitor neighborhoods; similarity is useful for discovery but not proof of a specific product role. [Primary reference](https://hobergphillips.tuck.dartmouth.edu/).

**[S091] SEC** — 2025-04-08. EDGAR APIs expose submission histories and entity-wide standard XBRL facts; custom product/segment attribution cannot be assumed from Companyfacts. [Primary reference](https://www.sec.gov/search-filings/edgar-application-programming-interfaces).

**[S092] W3C** — publication date not established. Broader/narrower concept relations and associative relations are distinct; use this distinction conceptually without replacing GMI's frozen schema. [Primary reference](https://www.w3.org/TR/skos-reference).

**[S093] GLEIF** — publication date not established. Legal-entity and ownership information can support incumbent Data OS reconciliation; no new identity authority is introduced. [Primary reference](https://www.gleif.org/en/lei-data/gleif-api).

**[S094] Micron** — publication date not established. The live product catalog separates DRAM components/modules, low-power DRAM, HBM and graphics memory; one memory-company label loses those distinctions. [Primary reference](https://www.micron.com/products/memory).

**[S095] KLA** — publication date not established. KLA offers inspection, metrology and process tools across chip, wafer and packaging manufacturing; a process-control vendor is not thereby an HBM product manufacturer. [Primary reference](https://www.kla.com/products).

**[S096] Intel** — 2026-05-31. The page publishes May 31 and its event dateline is June 1; Xeon CPU and Ethernet launches differ from the Crescent Island GPU roadmap. [Primary reference](https://newsroom.intel.com/data-center/intel-puts-agentic-ai-xeon-6-networking-ai-systems).

**[S097] AMD** — 2026-07-23. AMD reports EPYC CPU and Instinct MI400 launches and Helios production, while individual customer deployment targets remain prospective. [Primary reference](https://ir.amd.com/news-events/press-releases/detail/1294/aai-2026-amd-delivers-full-stack-compute-for-the-agentic-ai-era).

**[S098] Arm** — 2026-03-24. Arm announced its own AGI CPU silicon alongside IP and CSS offerings; early systems and later broad deployment are different stages. Arm must not be frozen into an IP-only business model. [Primary reference](https://newsroom.arm.com/news/arm-agi-cpu-launch).

**[S099] Arm** — 2026-02-04. The earlier fiscal-quarter disclosure separates royalty from license revenue; it does not negate the later direct-silicon announcement. [Primary reference](https://newsroom.arm.com/news/arm-q3-fye26-results).

**[S100] Nextpower** — 2025. Nextracker rebrands and changes its corporate name to Nextpower while retaining NXT; the new power-conversion product line has future shipment expectations in this announcement. [Primary reference](https://investors.nextpower.com/news/news-details/2025/Nextracker-Rebrands-as-Nextpower-to-Reflect-the-Companys-Position-as-an-Integrated-Power-Technology-Innovator/default.aspx).


## 14. Immutable internal source references

**[G1]** [config/theme_crosswalk.yml](https://github.com/mastermindx-market-intelligence/macro/blob/6b154e09357300964c0720448cee9654bf2585d0/config/theme_crosswalk.yml).

**[G2]** [agentos/decisions/DEC-GMI-THEME-FABRIC-C0-CONVERGENCE.md](https://github.com/mastermindx-market-intelligence/macro/blob/6b154e09357300964c0720448cee9654bf2585d0/agentos/decisions/DEC-GMI-THEME-FABRIC-C0-CONVERGENCE.md).

**[G3]** [research/theme_graph/THEME_FABRIC_COMPLETION_RESEARCH_2026-10-07.md](https://github.com/mastermindx-market-intelligence/macro/blob/6b154e09357300964c0720448cee9654bf2585d0/research/theme_graph/THEME_FABRIC_COMPLETION_RESEARCH_2026-10-07.md).

**[G4]** [research/theme_graph/THEME_FABRIC_CONVERGENCE_HANDOFF_2026-10-07.md](https://github.com/mastermindx-market-intelligence/macro/blob/6b154e09357300964c0720448cee9654bf2585d0/research/theme_graph/THEME_FABRIC_CONVERGENCE_HANDOFF_2026-10-07.md).

**[G5]** [engine/theme_graph/membership_evidence.py](https://github.com/mastermindx-market-intelligence/macro/blob/6b154e09357300964c0720448cee9654bf2585d0/engine/theme_graph/membership_evidence.py).

**[G6]** [research/theme_graph/THEME_HIERARCHY_E1_CHILD_LEADS_PARENT_PREREG_2026-10-07.md](https://github.com/mastermindx-market-intelligence/macro/blob/6b154e09357300964c0720448cee9654bf2585d0/research/theme_graph/THEME_HIERARCHY_E1_CHILD_LEADS_PARENT_PREREG_2026-10-07.md).

## 15. Implementation receipt

**Implementation prepared locally, not released.** The existing GMI membership-evidence owner now has a research-document reviewer and the existing overlap CLI has an explicit `--microtheme-research` read-only mode. This mode verifies the exact incumbent crosswalk blob, all 68 micro IDs, 12 intermediate subthemes, 132 parent edges, source-reference closure, publication precision, null identity/admission/weights, hard negatives, denominators, and strict field allowlists; it neither fetches external sources nor writes graph/market/proposal/state data. Existing `--review` paths are unchanged.

**Executed local verification on the integrated October 13 source base** `macro@6b154e09357300964c0720448cee9654bf2585d0`, Python 3.12, pytest:

- Focused consumer/adversarial suite before the final allowlist strengthening: **41 passed**, exit 0.
- Strengthened consumer/adversarial suite: **47 passed**, exit 0.
- Follow-up adversarial repair: protected-pin prose reconciled to the machine source; additional source clocks/nullable-field refusals, escaped Markdown links, and JSON-only CLI behavior verified with **72 focused tests** and **507 passed, 1 skipped** in the joined owner suite. Those are local results, not final hosted or independent acceptance.
- Existing overlap/review regression subset: **67 passed, 360 deselected**, exit 0.
- Initial joined GMI owner suite: **482 passed, 1 skipped**, exit 0, from `python3.12 -m pytest -q tests/test_theme_graph_local_plane.py tests/test_theme_graph_micro_membership_research.py --tb=short`.
- A real invocation of `python3.12 scripts/explain_theme_overlap.py --microtheme-research research/theme_graph/microtheme_membership_candidates_2026-10-08.json --format markdown --out <new-review-path>` wrote the review successfully; original preview SHA-256 `9b7d20a42855cfcb7f5e4d1bf8fa9249f16e0c6337c5d068f9d972bdca934db4`; amended review-preview SHA-256 `8104b07f1c8152a586007343cd6e643482e5ebd5e3bb7f47a907f249d63b6084`. No pre-existing output was overwritten.
- Sample public-primary-source checks corroborated the separately dated HBM production/sampling distinctions, the corporate-action examples, and the Arm CPU silicon change. These selected checks do not authenticate all 100 source bodies or grant public machine ingestion rights.

**Unproven and held on the amended head:** independent review, binding hosted CI, PR merge, production install, current Data OS identity qualification, canonical group-to-micro membership admission, product measurement sufficiency, real served Terminal/F04 consumer and any ranking/entry/size/trading authority. This implementation is BUILT_NOT_PROVEN and the larger GMI Theme Fabric remains incomplete. The draft PR is GitHub's implementation/evidence carrier; no new lifecycle or runtime registry is created.
