# Healthcare intelligence — research foundation R1

Research date: 2026-09-23. Operation: `gmi-healthcare-deep-research-20260923-sol-001`.

**Status: PRINCIPAL-LED RESEARCH / NOT AN IMPLEMENTATION SPECIFICATION / NOT A FABLE COMMISSION.** This is the first cumulative research foundation. It does not claim exhaustive Healthcare coverage, validated investment signals, approved canonical memberships, deployed ingestion, or product acceptance. Sol retains the difficult domain research and synthesis under the Chairman's present instruction; Fable is reserved for a later implementation-orchestration handoff.

## 1. Outcome and product thesis

The user should be able to move from a Healthcare development to a defensible explanation of its significance: which disease and patient segment it concerns; which technology and commercial assets are involved; which suppliers and delivery dependencies matter; which companies have an evidenced economic interest; what could prevent adoption; and what would change the conclusion. The machine should preserve the evidence, temporal scope, ownership boundaries and uncertainty behind that explanation.

The intended advantage is not a longer list of biotech companies. It is a maintained chain from **scientific evidence through treatment access to economic exposure**, combined with supply constraints, substitutions and explicit disconfirming evidence. Company narratives, approval counts and expanding factories are insufficient substitutes for that chain.

Research priority is separate from price-basket eligibility, security selection, entry timing and trading authority. This program does not originate or size trades.

## 2. What already exists — exact inspected state

Repository: `mastermindx-market-intelligence/macro`; inspection/base commit: `668237947e016f679782e41e61c91c9133a5ea99`. Protected Mastermind Skillpack: `bf764f494b9cd0ecede6234bb472c3344c8e77cc`, version 1.0.1, bootstrap major 1. All statements below concern inspected repository artifacts, not a live-browser or runtime acceptance test.

| Existing owner or artifact | Verified observation | Consequence for this program |
| --- | --- | --- |
| `agentos/workstreams/WS-GMI-THEME-GRAPH.md` | GMI owns the semantic/evidence spine; downstream F04 composition and native transmission ownership remain separate. | Extend existing contracts; do not create a Healthcare graph authority or propagation engine. |
| `docs/superpowers/specs/2026-09-20-sector-theme-subtheme-intelligence-system-design.md` | The proposed shared architecture distinguishes sector, subsector, canonical theme, source-local subtheme, measurement basket and company/security. | A new research label is not permission to mint canonical themes or price memberships. |
| Robotics PR #7773, head `f10211657c6c31df3c9af73cd4b9484e2dd7690a` | Research, specification, plan and Fable handoff were present on an open draft PR. | Reuse the method and coordinate with its owner; do not describe the template as deployed. |
| `scripts/build_state_of_themes.py` | Existing Theme Tracker builder consumes `site/basketdata/clinical_pipeline.json` and renders the stable `state_of_themes.html` route. | Integrate through the current page/data owners, not a disconnected Healthcare microsite. |
| `config/clinical_modalities.yml` | Nine configured modality rows are mapped to three theme IDs. | Preserve compatibility while researching richer orthogonal classification. |
| `engine/theme_clinical.py` | Legacy selection and phase-as-of-ingestion defects are disclosed; a BioCatalyst point-in-time seam exists. | Reuse the evidence seam, retain disclosures, and verify coverage before analytical promotion. |
| `scripts/build_biocatalyst.py` | The public page is a data-free shell; trial facts are intended to arrive through a same-origin, site-full-protected runtime API. | Do not put the eventual full-fidelity trial corpus into public static output or Git history. Source presence is not runtime proof. |

### Concrete coverage observation

At the inspected commit, `site/basketdata/clinical_pipeline.json` was generated at `2026-09-23T04:34:52.143842+00:00`. It reports 2,560 stored studies, nine modalities and three themes. Its selected plane is `legacy`; point-in-time availability is false and point-in-time rows consumed are zero. The displayed point-in-time fraction is 0.0 for all three themes: 1,883 legacy studies for `diagnostics_lifesci`, 554 for `glp1_obesity`, and 123 for `medical_devices`.

This is a coverage observation, not proof that every stored row is wrong. It means historical claim validity cannot be inferred from the artifact's fresh generation date. Even its observation dates differ: the liquid-biopsy subsection's most recent registration month is May 2026 while the overall artifact is dated September 23.

The current grouping puts ADCs, radioligands, gene editing, CAR-T and mRNA alongside liquid biopsy under `diagnostics_lifesci`. That may serve a legacy indicator but is inadequate as the sole research ontology. Do not silently rename the theme or reassign existing baskets. A compatibility-preserving facet projection is the research direction.

Existing authority remains display/context only: rank, gate, size and escalation are false, with no fusion into `fused_obs_z`. Existing wording about registration activity being a leading capital-commitment indicator is a hypothesis to evaluate, not accepted causal or predictive evidence.

## 3. Healthcare needs linked dimensions, not one classification tree

**Design proposal.** Use the existing GMI semantic/evidence spine to support multiple views of the same source-scoped assertions. A navigation tree can be a useful projection, but it should not become the only representation.

| Dimension | Question it answers | Essential distinction |
| --- | --- | --- |
| Disease and indication | Which condition, subtype and treatment setting? | Disease family is not the exact approved indication. |
| Patient and treatment context | Which age group, biomarker status, line of therapy and prior treatment? | Trial population, approved population and payer-covered population may differ. |
| Molecular target or biological mechanism | What biological process is addressed? | Target, gene, protein expression and mutation are not interchangeable labels. |
| Therapeutic or diagnostic modality | How does the intervention work or measure? | ADC, radioligand, gene editing, cell therapy and diagnostic assay are separate dimensions from disease. |
| Asset, formulation and combination | Which investigational agent, marketed product or combination? | One agent can have multiple formulations, indications and combinations. |
| Evidence program and study | Which trial, arm, comparator, endpoint and analysis? | A study is not a development program; a program is not a company. |
| Regulatory status | Which authority, territory, application and indication version? | Submission, authorization, label expansion and withdrawal are different events. |
| Manufacturing and physical inputs | Which process, product-qualified site and component? | Generic technical capability is not an actual qualified supplier relationship. |
| Access and delivery | Which diagnostics, treatment centers, practitioners and care setting? | Eligible patients are not the number able to begin or complete treatment. |
| Payment and commercialization | Who pays, under which policy and contractual terms? | Coverage is not payment amount, realized net price or manufacturer revenue. |
| Economic interest and company ownership | Who receives product sales, service fees, royalties or profit shares? | Subsidiary, license holder, sponsor, manufacturer and listed issuer can differ. |
| Time and evidence quality | What was known, when, and with what support? | Publication time, event time, observation period and ingestion time are different clocks. |

NCI's vocabulary infrastructure supplies useful external terminology and versioned concept mappings; it does not supply Mastermind's investment exposure ontology. Retain namespace and release metadata rather than importing clinical labels as canonical investment themes. [S01]

### A worked semantic join

An oncology company can be associated with a HER2-directed ADC, one or more breast-cancer settings, a companion diagnostic, an external manufacturing process and territorial commercialization rights. The company should be discoverable through each relevant lens without making those lenses mutually exclusive or treating every connection as a separate holding.

The FDA companion-diagnostic table demonstrates why the join requires the assay, specimen, biomarker, therapeutic product and indication rather than a generic company-to-oncology tag. Its December 2025 Enhertu decision also binds a particular treatment setting and diagnostic requirement. [S03, S04]

Unknown or undisclosed targets remain unknown. Semantic similarity may nominate a mapping for review; it must not silently establish a target, supply relationship or economic right.

## 4. Coverage map to guide the next research waves

The following are **research coverage families**, not new canonical theme IDs or approved basket memberships. They deliberately overlap across disease, technology and business-model views. Their breadth preserves the complete Healthcare mission while the first worked cases test the architecture.

| Research family | Subtheme and dependency questions to resolve |
| --- | --- |
| Therapeutic demand and disease markets | Oncology; immunology; metabolic disease and obesity; cardiovascular and renal disease; neuroscience; rare inherited disorders; infectious disease and vaccines; reproductive and women's health. |
| Therapeutic technology platforms | Small molecules; peptides; monoclonal and multispecific antibodies; ADCs and other conjugates; radiopharmaceuticals; RNA therapeutics; gene transfer/editing; autologous and allogeneic cell therapies. |
| Diagnostics and precision medicine | Tissue pathology; molecular profiling; liquid biopsy; minimal residual disease; companion diagnostics; imaging agents; inherited-disease testing; screening versus treatment monitoring. |
| Life-science tools | Sequencing; proteomics; single-cell and spatial analysis; laboratory instruments; reagents and assays; research models; lab automation; scientific data and analysis software. |
| Development and manufacturing services | CROs; trial-site services; recruitment and trial technology; biologics CDMOs; peptide/API synthesis; high-potency chemistry and conjugation; vectors/cell processing; sterile fill-finish and analytical release. |
| Devices and interventional care | Surgical systems; cardiovascular interventions; electrophysiology; orthopedics; neurostimulation; diabetes monitoring and delivery; diagnostic imaging; catheters, disposables and enabling components. |
| Healthcare software and AI | Imaging algorithms; clinical decision support; documentation workflows; EHR/interoperability; revenue-cycle administration; remote monitoring; drug-discovery software; real-world evidence infrastructure. |
| Providers and care settings | Hospitals; ambulatory surgery; specialty physician practices; outpatient oncology; home health; behavioral health; dialysis; post-acute and long-term care. |
| Payers and access administration | Commercial insurance; Medicare-related plans; Medicaid-related plans; PBMs; specialty-drug access; utilization management; outcomes-based agreements; employer-sponsored administration. |
| Distribution and healthcare infrastructure | Drug wholesalers; specialty pharmacies; cold-chain logistics; medical supplies; sterilization; packaging and delivery devices; facility equipment; workforce/training constraints. |
| Cross-sector dependencies | Semiconductors; sensors and optics; robotics; cloud/compute; specialty chemicals; biomaterials; energy and facility reliability; transport and isotope infrastructure. |
| Adjacent animal-health lens | Companion-animal therapeutics; livestock health; vaccines; diagnostics; veterinary tools; veterinary services; distribution; overlap with human-health suppliers. Keep scope and customer economics distinct. |

Breadth is not completion. Providers, managed care, PBMs, broad life-science tools, general pharmaceutical portfolios and animal health still require dedicated dossiers. This initial source set is intentionally stronger on dependency structure, advanced therapies, diagnostics and devices than on the entire investable company universe.

## 5. Worked cases: facts, inference and falsifiers

These cases are original, limited research summaries of public sources. They are not a production product catalog or a substitute for the underlying regulatory label or full contract.

### Case A — ADC exposure can be licensing, manufacturing, or both

Lonza's May 7, 2026 BMS notice describes an exclusive single-target technology license; the target is undisclosed. It assigns development, manufacturing and commercialization to BMS and describes contingent economics for a Lonza affiliate. This does **not** establish a Lonza manufacturing contract for that asset. [S05]

Separately, Lonza's June 30, 2026 Visp announcement describes planned payload-linker expansion, with operation expected in 2028. Its described chain includes antibody production, conjugation, drug product and quality control. This is evidence of planned investment and a disclosed process architecture, not measured current industry shortage or completed incremental output. [S06]

**Research conclusion:** distinguish technology licensor, payload/linker producer, antibody manufacturer, conjugator, analytical provider and finished-product supplier. Capture exclusivity at its actual target/product scope. Do not attribute a technology-platform pipeline to a specific factory without evidence.

**Next proof:** disclosed service contracts, product-qualified manufacturing scope, independent capacity evidence, commissioning milestones, utilization and the relevant revenue basis. Keep undisclosed customer identities null; Lonza also publishes integrated-supply notices without naming the customer. [S07]

### Case B — Radiopharmaceutical bottlenecks must be isotope-, site- and date-specific

Novartis's November 10, 2025 Carlsbad opening announcement explicitly said the site had been filed with FDA as an additional supply point and that commercial manufacturing could begin after approval. Opening and authorized commercial supply were therefore distinct at that source date. That historical pending status must not be carried forward as a September 2026 fact without a new receipt. [S08]

Novartis had separately described Pluvicto supply as unconstrained in January 2024. DOE's actinium material discusses a different isotope and supply problem. These are not automatically contradictory observations about one generic radiopharmaceutical shortage. DOE's detailed page was search-visible but not fully retrievable in this session, so it is a research lead, not a current quantified supply census. [S09, S10]

**Research conclusion:** the chain should distinguish isotope availability, product-specific production, quality release, transport, treatment-center access and patient throughput. Supplier concentration alone does not establish the binding constraint. A source's radioactive-decay claim must be checked for the specific isotope before generalizing it to the entire modality.

**Next proof:** refresh product/site authorization and actual commercial release; obtain isotope-specific dated supply evidence; separately test treatment-center and scheduling constraints. No claim of a current sector-wide shortage or a current supplier winner is accepted here.

### Case C — Gene editing requires clinical, operational and economic views

FDA's July 1, 2026 Casgevy supplement expanded the U.S. indication to patients aged two and older with the specified SCD or TDT conditions. The notice separately describes pediatric study populations and extrapolation; trial enrollment ages cannot simply be copied into the approved-label population. It also identifies autologous edited stem cells and the conditioning requirement. [S11]

Vertex's June 30, 2026 Form 10-Q describes its lead role and CRISPR's 40% share of net commercial profits/losses and specified development costs, subject to adjustments. A profit-sharing percentage is not a product-revenue percentage. [S12]

CMS's CGT Access Model supplies a separate access layer: it is voluntary and uses outcomes-based agreements with participating states and manufacturers. It is not universal coverage for every gene therapy, patient or payer. [S13]

**Research conclusion:** autologous versus allogeneic, ex vivo versus in vivo, editing versus gene transfer, manufacturing release and treatment delivery must remain distinct facets. Approval expansion is not automatically equivalent to increased near-term treated volume. Profit share, royalty, reimbursed development cost and consolidated sales require different economic fields.

**Next proof:** current patient-start/collection/infusion measures, treatment-center capability, payer-specific criteria and relevant net economics. Do not manufacture those values from an approval announcement.

### Case D — Diagnostics connect biomarkers to decisions, not just to companies

The FDA companion-diagnostic list supports product- and indication-specific relationships rather than a single universal precision-oncology membership. Preserve specimen, tested feature, assay version and regulatory decision references. [S03]

**Research conclusion:** distinguish analytical capability, clinical evidence, regulatory authorization, coverage, test utilization and realized laboratory economics. Screening, therapy selection and residual-disease monitoring are different jobs even where similar sequencing equipment is involved. A diagnostic association does not prove an exclusive relationship, sales conversion or an installed instrument base.

**Next proof:** indication-specific labels and payer policies, source-period test volumes, reimbursement realizations and documented component/tool dependencies. The initial packet does not nominate a diagnostic stock basket.

### Case E — Healthcare AI requires a workflow and adoption denominator

FDA describes its AI-device list as non-comprehensive, periodically updated and derived from available authorization materials. Its entries distinguish clearance/authorization/approval routes and contain regulatory submission references. This is not a census of every healthcare AI company or every commercially adopted algorithm. [S14, S15]

AccessGUDID supplies device identifiers and versioned device records; those are useful joins but not issuer identities or revenue measurements. A listing alone cannot establish hospital adoption or paid usage. [S16]

**Research conclusion:** separate clinical-device software, administrative workflow software and scientific discovery tools. Do not force every Healthcare AI business through a device-authorization gate, and do not treat authorization as economic success. Test the specific workflow, intended use, deployment setting, buyer and payment mechanism.

**Next proof:** licensed deployments or usage, workflow integration, clinical validation applicable to the actual version, procurement friction and disclosed recurring economics. Algorithm count is not an investment score.

### Case F — Surgical technology has both installed-base and usage economics

Intuitive's Q2 2026 release separately reports approximately $1.73 billion of instruments/accessories revenue and $685 million of systems revenue, with procedure activity and leasing contributing to the operating picture. Systems placements alone do not describe the business. These are reported period figures, not a forecast. [S17]

**Research conclusion:** reuse the Robotics cross-sector connection while adding procedures, disposable attachment, leasing and service economics. A robotic-system manufacturer and its suppliers should not be duplicated as distinct securities merely because both Healthcare and Robotics views include them.

**Next proof:** product-specific and geographic utilization, consumable/service exposure and documented supplier relationships. Preserve the existing Robotics owner rather than redoing the Robotics BOM.

### Case G — Payment datasets describe a population and accounting basis

CMS's Part B drug methodology concerns fee-for-service beneficiaries and excludes Medicare Advantage. Its federal catalog describes HCPCS-level spending inclusive of Medicare payment and beneficiary liability. The catalog's 2026 update points to a 2024 data resource; release date is not the economic observation period. [S18, S19]

**Research conclusion:** claims-based spending can corroborate a scoped adoption hypothesis but cannot be substituted for a manufacturer's global net sales, all-payer utilization or current-quarter demand. Coverage decisions also have their own national/local determination process. [S20]

**Next proof:** exact dataset release, measurement years, code-to-product mapping, population exclusions and reconciliation to company disclosures. Never sum overlapping payer views into an invented total market.

### Case H — A picks-and-shovels company can monetize both product and IP

Halozyme's Q2 2026 SEC-filed release separately identifies $307.7 million in royalties within $481.0 million total revenue and describes product sales alongside licensing relationships. This is a concrete example of why supplier economics cannot be reduced to units manufactured. [S21]

**Research conclusion:** distinguish actual royalty receipts, product revenue, upfront consideration and contingent milestones. A newly announced license is not the same thing as an approved partner product generating royalties. An enabling technology can cross multiple disease themes without each theme independently receiving the company's entire revenue.

**Next proof:** partner/product allocation where disclosed, contract duration and scope, relevant competitive substitutions, and the materiality of each economic channel. No allocation is invented when disclosures are insufficient.

## 6. Evidence architecture: source truth before analytical interpretation

These are proposed research requirements to map onto existing contracts, not a new evidence database.

### Source roles and their limits

| Source family | Useful evidence unit | What it cannot establish by itself |
| --- | --- | --- |
| ClinicalTrials.gov / existing BioCatalyst | Versioned study record, dates, design, interventions and results where available | Clinical success, program-level unique-asset counts, economic spending, historical states reconstructed from today's record. |
| FDA drug/application records | Application, supplement, label, review and decision | Global approval, payer coverage, uptake or a current stock's exact economic ownership. Drugs@FDA also has stated coverage limits. [S02] |
| FDA diagnostics/device records | Submission, assay/device, intended use and authorization type | A complete commercial AI universe, actual installed base or issuer revenue. [S03, S14, S16] |
| NCI terminology and NLM terminology | Versioned external concepts and mappings | An investment classification or unrestricted rights to every third-party vocabulary bundled with them. [S01, S22] |
| CMS coverage and spending | Policy version, payer geography, population and period-specific utilization/spending | All-payer/global demand, individual treatment eligibility from a generic theme page, or manufacturer net sales. [S13, S18–S20] |
| Regulatory financial filings | Disclosed revenue channels, segment scope, contracts and contingencies | Undisclosed subtheme revenue percentages or future commercial conversion. [S12, S17, S21] |
| Company announcements | Attributed statements about agreements, investment plans and milestones | Independent proof of scarcity, finished capacity or unqualified clinical claims. [S05–S09] |
| Original clinical evidence | Study design, denominator, effect estimates, comparators, safety and follow-up | Automatic transfer to another indication, agent, modality or patient population. This evidence-quality deep dive is owed next. |

The first-pass source register contains access-quality notes. A search result is not equivalent to a successfully read underlying page. No production endpoint reliability, sustained refresh cadence, historical completeness or redistribution entitlement was tested in this wave.

### Clocks and status

For each assertion, preserve as applicable: source publication time; event/effective time; observation interval; first-known time within Mastermind; retrieval time; source revision; correction/supersession time; and date precision. Unknown date parts remain unknown. Do not fabricate midnight timestamps or pretend a year-only commissioning expectation is a day-level event.

A report for a quarter can contain subsequent events. Its fiscal end date must not be stamped onto every narrative claim. A promised future event remains an expectation after its expected date passes until a new source resolves it.

For study activity, separate registration, study start, primary completion, full completion, result posting and company readout guidance. Harvard's research-operations definition ties primary completion to final collection of primary-outcome data, not publication of an investment catalyst. [S24]

### Proposed economic-exposure record

A research assertion should be able to express: source-local subject; eventual existing company/security resolution; business unit; asset or service; value-chain role; counterpart; territory; indication; contract scope; economic channel; amount or range; currency; reporting period; accounting basis; whether disclosed or inferred; source locator; freshness; and unresolved conditions.

Permitted missingness matters. `unknown`, `not_disclosed`, `not_applicable`, `stale` and an evidenced zero must not collapse into one number. An exposure confidence label describes evidence quality, not expected investment return. Do not build a new numerical Healthcare score merely to hide these differences.

### Rights and publication

RxNorm's official terms distinguish NLM-created normalized names/codes from proprietary source material in the full dataset. Full-release access and downstream use have separate licensing considerations. Do not conclude that a government-hosted composite dataset is wholly unrestricted. [S22]

Persist original research summaries and public references here. Later full-fidelity evidence should follow the existing authenticated publication and rights owners. Never paste licensed corpora, individual health records, private pricing contracts, or paid-provider payloads into public Git history. The present program does not require patient-level personal information.

## 7. Bottleneck research should identify the binding constraint, not repeat a story

**Proposed bottleneck assertion:** constrained node; specific product/process/geography; relevant demand; available capacity and compatible units; observed symptom; substitution possibilities; expansion/relief path; source dates; economic beneficiary mechanism; counterevidence; confidence; and a falsifier.

Keep separate research statuses: candidate constraint, observed constraint within scope, relief announced, relief operationally evidenced, resolved within scope, and unresolved/conflicted. These are proposed analytical labels on existing evidence, not a new operational lifecycle plane.

A useful dossier must answer four different questions: Is something technically hard? Is supply actually constrained? Can a specific company capture economics from the constraint? Can competitors, substitution or new capacity remove that advantage? Evidence for one question does not answer the other three.

### Initial research priorities, not findings of shortage

| Candidate constraint | Why investigate | Evidence required to accept or reject |
| --- | --- | --- |
| ADC payload/linker, conjugation and release capability | The case evidence identifies distinct specialized stages and planned investment. | Product-qualified supply, capacity scope, utilization/lead times and alternatives. Expansion alone is insufficient. |
| Radiopharmaceutical delivery chain | Historical production changes and site approvals show multiple possible constraints. | Separate isotope, manufacturing, quality, logistics and center-throughput evidence; reject undifferentiated shortage claims. |
| Autologous therapy delivery | Regulatory and payment sources identify a treatment pathway beyond editing the cells. | Current collection-to-infusion observations, center capacity, access criteria and manufacturing outcomes. |
| Precision diagnostics adoption | Authorization is indication-specific while economics depend on usage and payment. | Relevant labels, payer policies, ordering/utilization and realized payment evidence. |
| Procedure-linked devices | Company reporting separates equipment and usage-linked revenue. | Procedures, installed base, lease model and consumable/service attachment by comparable period. |
| Healthcare data semantics and rights | Registry and terminology limitations can distort every downstream basket. | Versioned source contracts, qualified identity joins, rights checks and measured coverage. |

No scarce-supplier basket, pricing-power claim or bottleneck winner is accepted by this first wave.

## 8. Product implications for the shared template

The Healthcare projection should answer a task before presenting a dense graph. A useful initial interaction is: select a theme or development; see the exact disease/modality/access scope; inspect companies by economic role; inspect the weakest evidenced dependency; compare the thesis with disconfirming evidence; and preserve a research note with its sources.

Candidate views to test with the shared-template owner:

- **Company exposure table:** role, economic channel, materiality evidence, territory, period and unknowns, rather than a confidence-free logo cloud.
- **Dependency view:** typed links distinguishing evidence, physical supply, access and economic interests; each expandable into a source-backed assertion.
- **Catalyst timeline:** separate actual decisions from estimated completion and sponsor guidance; show corrections rather than replacing history.
- **Bottleneck dossier:** what is constrained, what has changed, who might benefit, and what would falsify it.
- **Evidence/coverage panel:** last source observation, retrieval freshness, point-in-time support, unmapped records and missing rights.

No new visual language is specified here. The eventual design must use existing governed components, preserve dark/light and EN/ZH behavior, and receive real-path browser proof. Research feasibility is not frontend acceptance.

## 9. Research gates before Fable receives a final build packet

1. **Domain breadth and falsification:** expand beyond the initial case-heavy foundation into disease/platform, tools/manufacturing, devices, services/payers and cross-sector dossiers. Include competing hypotheses and evidence against attractive narratives.
2. **Company and economic mapping:** produce source-backed company/business/asset relationships, current ownership/security joins and explicit unknown materiality. No name-only stock lists presented as research completion.
3. **Data feasibility:** inspect existing source/evidence adapters; test bounded authorized reads and actual historical/version behavior; map field coverage and rights. Do not ask Fable to discover that a critical source is inaccessible or unsuitable during coding.
4. **Integration and product synthesis:** refresh only the current owners/PRs that the proposed shared contracts touch; specify additive projections and rejected duplicate approaches.
5. **Written design and implementation plan:** bounded vertical slices with persona, data consumer, UI path, tests, negative cases and production/browser acceptance. Obtain the applicable review/approval before implementation.
6. **Fable CEO handoff:** only when the above are mature, commission orchestration with precise research artifacts, open questions, execution boundaries and proof criteria. Routine extraction, engineering and validation can then use the least-scarce capable workers; foundational judgment stays with the research principal until this gate.

The next primary research unit is the therapeutic/platform-to-economic-rights dossier: compare advanced oncology, metabolic therapies and cell/gene approaches, using product/indication/rights-aware records and a deliberate negative-evidence sample. In parallel within the same research program, keep the unresolved source/time-access questions visible rather than silently treating them as solved.

## 10. Source register

All sources were consulted on 2026-09-23. `read` means relevant page/filing content was exposed and inspected; it does not imply the entire source corpus was acquired. `indexed only` means the underlying page was not successfully read. Company statements remain attributed, including when hosted by SEC. Exact live rights, completeness and service reliability remain separate acquisition gates.

| ID | Primary source / date or scope | Locator | Access |
| --- | --- | --- | --- |
| S01 | NCI, Vocabulary for Cancer Research; updated 2025-09-03 | https://www.cancer.gov/about-nci/organization/cbiit/vocabulary | read |
| S02 | FDA, About Drugs@FDA; product and document coverage | https://www.fda.gov/drugs/drug-approvals-and-databases/about-drugsfda | read |
| S03 | FDA, authorized companion diagnostic devices; indication-specific table | https://www.fda.gov/medical-devices/in-vitro-diagnostics/list-fda-authorized-companion-diagnostic-devices-in-vitro-and-imaging-tools | read |
| S04 | FDA, Enhertu with pertuzumab decision; 2025-12-15 | https://www.fda.gov/drugs/drug-approvals-and-databases/fda-approves-fam-trastuzumab-deruxtecan-nxki-pertuzumab-unresectable-or-metastatic-her2-positive | indexed primary text |
| S05 | Lonza/BMS technology license; 2026-05-07 | https://www.lonza.com/media-advisories/2026-05-07-14-00 | read |
| S06 | Lonza Visp payload-linker expansion; 2026-06-30 | https://www.lonza.com/news/2026-06-30-07-00 | read |
| S07 | Lonza integrated ADC supply, unnamed partner; 2024-10-22 | https://www.lonza.com/news/2024-10-22-07-00 | indexed primary text |
| S08 | Novartis Carlsbad opening and pending supply approval; 2025-11-10 | https://www.novartis.com/us-en/news/media-releases/novartis-opens-new-radioligand-therapy-manufacturing-facility-california-part-23b-us-expansion-plan | read |
| S09 | Novartis Indianapolis production/supply statement; 2024-01-05, historical only | https://www.novartis.com/news/media-releases/novartis-expands-production-pluvictotm-addition-its-largest-and-most-advanced-radioligand-therapy-manufacturing-facility-indianapolis | indexed primary text |
| S10 | DOE/NIDC, Multiple Production Methods Underway to Provide Actinium-225; publication date unresolved | https://isotopes.gov/information/actinium-225 | indexed only; full-page request returned 403; no current capacity acceptance |
| S11 | FDA, Casgevy pediatric supplement; 2026-07-01 | https://www.fda.gov/news-events/press-announcements/fda-approves-first-gene-therapy-young-children-sickle-cell-disease | read |
| S12 | Vertex Form 10-Q, quarter ended 2026-06-30; Note B, CRISPR JDCA | https://www.sec.gov/Archives/edgar/data/875320/000087532026000259/vrtx-20260630.htm | read; do not infer every event date from quarter end |
| S13 | CMS, Cell and Gene Therapy Access Model; page modified 2026-05-07 | https://www.cms.gov/priorities/innovation/innovation-models/cgt | read |
| S14 | FDA, AI-enabled device list; limitations and submission records | https://www.fda.gov/medical-devices/artificial-intelligence-enabled-medical-devices/list-artificial-intelligence-enabled-medical-devices | read |
| S15 | FDA, AI-enabled devices overview; device-regulatory pathway distinctions | https://www.fda.gov/medical-devices/digital-health-center-excellence/artificial-intelligence-enabled-medical-devices | indexed primary text |
| S16 | NLM AccessGUDID, Device Lookup API; identifiers and version fields | https://accessgudid.nlm.nih.gov/resources/developers/device_lookup_api | read; no live API acceptance test |
| S17 | Intuitive Q2 2026 earnings release, SEC exhibit; period ended 2026-06-30 | https://www.sec.gov/Archives/edgar/data/1035267/000103526726000047/q226ex-991earningsrelease.htm | read |
| S18 | CMS, Medicare Part B Spending by Drug Methodology; modified 2025-07-22 | https://data.cms.gov/resources/medicare-part-b-spending-by-drug-methodology | indexed primary text |
| S19 | Federal CMS Part B drug dataset catalog; updated 2026-06-25, resource year 2024 | https://catalog.data.gov/dataset/medicare-part-b-spending-by-drug | indexed primary text |
| S20 | CMS, Medicare Coverage Determination Process | https://www.cms.gov/medicare/coverage/determination-process | read |
| S21 | Halozyme Q2 2026 release, SEC exhibit; released 2026-08-06 | https://www.sec.gov/Archives/edgar/data/1159036/000115903626000103/ex991q220268-k.htm | read |
| S22 | NLM, RxNorm Terms of Service; normalized terminology versus bundled sources | https://www.nlm.nih.gov/research/umls/rxnorm/docs/termsofservice.html | indexed primary text |
| S23 | CTTI, AACT data dictionary; study tables keyed by NCT ID | https://aact.ctti-clinicaltrials.org/data_dictionary | indexed only; page open failed; navigation lead, not adapter validation |
| S24 | Dana-Farber/Harvard Cancer Center, research-operations primary-completion definition | https://www.dfhcc.harvard.edu/research/clinical-research-support/office-of-data-quality/services-support/clinicaltrialsgov-and-ctrp | read |

### Explicit retrieval limitations

ClinicalTrials.gov's rendered documentation pages exposed only JavaScript shells on attempted opens. A bounded web-tool request for `NCT04784715` via its v2 API was also inaccessible through this tool. This is a tool-path limitation, not proof that the API or existing BioCatalyst runtime is unavailable. CTTI and DOE had the source-specific limitations recorded above. No blind repetition or production acquisition was attempted. Resolve only the needed capability through an authorized supported path in a later source-feasibility wave.

## 11. Continuation boundary

Parent mission remains incomplete. This foundation is a reviewed-by-author research artifact, not an independent review or an accepted product design. Companion negative cases define what future evidence and code must not infer. Continue on the same research branch, preserve the existing Agent OS continuation, and do not create a final Fable handoff yet.
