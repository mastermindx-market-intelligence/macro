# Semiconductor intelligence — process, materials and EDA/IP research

Research installment 2 — 23 September 2026. This is a substantive editorial research dossier, not the final Fable handoff or an accepted production specification.

Operation: `gmi-semiconductors-research-20260923-sol-001`. Existing parent: `WS:GMI-THEME-GRAPH`. Same carrier: Macro draft/HOLD PR #7780, branch `sol/semiconductors-research-20260923`. Protected procedure: Mastermind `bf764f494b9cd0ecede6234bb472c3344c8e77cc`, compatible Skillpack 1.0.1/bootstrap 1.

Chairman expressly retained the difficult research and synthesis in this principal session so Fable can later orchestrate implementation. Direct-work rationale: PRINCIPAL_JUDGMENT. No Fable, subagent, Executive Attempt or watcher is commissioned. No product code, production contract, native factual admission, live constituent, rank, entry, size, trade or release effect occurs here.

## 1. Material conclusion: semiconductor demand has different drivers

A useful theme system must distinguish design activity, mask sets, wafer/process activity, equipment purchases, site supply, quality requirements, licensing and unit royalties. A generic semiconductor-growth basket would mix different economic mechanisms.

HOYA's 2024 report ties mask-blank demand to design activity and miniaturization more than final-product volumes. Wacker's 2025 report describes strong semiconductor-grade polysilicon alongside solar weakness; mixed-segment sales were EUR882.9m versus EUR949.2m and EBITDA EUR96.2m versus EUR193.4m. Its new purification line increased semiconductor-grade capacity by more than 50%, not all polysilicon or finished-wafer capacity. These figures are mixed-segment observations, not semiconductor-only profitability. [PM01, PM03]

Our proposed research must separate category relevance, underlying activity, realized business exposure and issuer earnings. The user should receive a useful explanation of these distinctions, not reconstruct them from source links or a colorful supplier chart.

### Proposed demand decomposition

| Driver | Research question | Required evidence |
|---|---|---|
| Design activity | Are relevant designs and mask sets increasing? | Comparable complexity, design/mask activity, turnaround and license scope |
| Wafer/process use | Is more accepted material-processing work occurring? | Compatible wafer/product units, mix, steps and net use |
| Equipment | Does required work exceed usable installed capacity? | Configuration, qualified throughput, utilization, upgrades and replacement |
| Quality | Does acceptable output require different contamination control? | Comparable defects/yields, accepted chemistry and substitution |
| Site supply | Is the exact facility system in accepted service? | Project binding, commissioning and delivered specification |
| Licensing | What design asset is licensed and recognized? | Contract/product and current accounting scope |
| Unit royalties | Which products trigger royalty economics? | Eligible shipments and disclosed contract mechanism |
| Business mix | Which issuer and segment capture the activity? | Effective ownership and compatible financial denominator |

These are analytical requirements, not a new forecasting engine. For one specified material/process, `material requirement = wafer activity × accepted steps per wafer × net use per step`. Supplier revenue additionally depends on qualified share, pricing, mix, contract timing and revenue recognition. For compatible equipment, steady-state tool equivalents depend on workload divided by qualified effective throughput, with downtime, utilization and changeovers preserved. Tool equivalents are not new-tool shipments.

Two invented arithmetic examples clarify the distinction: 0.90 wafer activity × 1.20 step intensity = 1.08 workload before efficiency and mix, an 8% increase rather than 20%; 1.20 workload / 1.20 per-tool throughput = unchanged steady-state tool equivalents before other factors. These are definitions and illustrations, not measured semiconductor forecasts. Unknown factors produce an unavailable estimate, not guessed exposure weights.

## 2. Manufacturing dependency findings

### Silicon feedstock, quartzware and finished wafers

SUMCO distinguishes CZ-related and float-zone routes, with FZ avoiding a quartz crucible. Sibelco describes high-purity quartz applications in crucibles and quartzware. These establish route-specific process dependencies, not a claim that quartzware is silicon feedstock inside every die. An alternative growth method does not prove customer-qualified substitution. [PM02, PM04]

Siltronic's epitaxial-wafer descriptions and Soitec's POI acoustic-filter substrate platform require different application and qualification scopes. An engineered filter substrate, silicon epitaxial wafer and development-stage specialty offering cannot inherit one universal advanced-wafer capacity or customer set. [PM05, PM20]

Research consequence: identify grade, route, qualified source and application before asserting shortage or substitutability. A dramatic raw-material headline without these bindings cannot support a universal downstream loss estimate.

### Blank, mask, writer and exposure

AGC describes EUV mask-blank construction. Tekscend describes photomask manufacturing and a named IMS writer delivered and installed at AMTC Dresden in November 2024. Keep blank, patterned mask and writing equipment separate. An installed writer is not a measured flow of accepted masks. [PM06, PM07, PM08]

The relevant hypothesis may concern more designs, more complex mask sets, longer writing/inspection or offsetting productivity. None should be silently reduced to a universal EUV-shortage claim.

### Patterning chemistry and adoption

Tokyo Ohka Kogyo distinguishes photoresist and related developer, rinse and stripping materials. JSR/Inpria/Lam describe non-exclusive cooperation involving metal-oxide resist and dry-process IP. That is not proof of exclusive procurement, all-fab qualification or recurring production volume. [PM09, PM10]

Preserve catalog capability, collaboration, process selection, customer qualification and recurring use as different milestones. A theme filter may span them, but the displayed relationship cannot strengthen because the application sounds commercially attractive.

### Deposition and subsystems

ASM International describes EmerALD thin-film deposition for advanced gate applications. VAT describes a pressure-control subsystem applicable to CVD/ALD. Merck KGaA reports distinct material, specialty-gas and delivery-system roles. This supports layered process research, not an inferred ASM-to-VAT or Merck-to-specific-tool procurement edge. ASM International and ASMPT are different entities. [PM16, PM17, PM21]

### CMP and contamination control

Ebara supplies the tool-level example; Fujimi supplies material-specific slurry examples; Entegris supplies CMP consumable, filtration and cleanup roles. Separate tool configuration, slurry/film compatibility, pad, contamination control and achieved result. Optional monitoring cannot be assumed present on every installation, and a catalog formulation is not automatically a qualified replacement. [PM12, PM18, PM19]

More cleaning or demanding surfaces do not necessarily imply proportionally more chemical liters. SCREEN's official SU-3400 excerpt describes chemical-use efficiency, but full release/product body access failed; numerical conditions remain held. Productivity, recycling, material substitution and yield must be explicit competing mechanisms. [PM31]

### Site gases and thin-die processing

Linde's Samsung project had a mid-2026 target. Air Liquide's named Micron Idaho project had an end-2025 target; its July 2026 Idaho announcement identifies a customer category, not a buyer name, and targets 2028. These dates do not prove commissioning. Do not resolve the unnamed buyer or combine phases from geography alone. [PM13, PM14, PM15]

DISCO's dicing-before-grinding description establishes a process alternative for thin-wafer handling, not a named HBM customer's qualified route. This connects packaging research to manufacturing without inventing a supply edge. [PM22]

## 3. EDA/IP is a function-specific dependency matrix

Cadence's April 22, 2026 release differentiates N2/A16 certification from ongoing A14 work. Siemens' same-day release identifies particular Calibre, Solido and thermal-analysis scopes, including specified advanced nodes. These need not disagree: the certified functions differ. [PM23, PM24]

Represent `vendor/product → function → version → foundry/process → PDK/interface version → evidenced milestone → date`. Simulation, physical verification, implementation, thermal analysis and interface IP are not one vendor-wide readiness flag. A certification is not a tapeout, silicon validation or volume shipment.

Rambus' controller documentation separates the controller from a selected PHY. Neither represents manufactured HBM stack capacity. Arm's filing describes licensing and royalty economics alongside its own-silicon program, whose end-2026 production remains a target, not observed output. [PM25, PM27]

AI-assisted synthesis may explain these records; it cannot originate a certification or signoff. Marketing claims of AI automation do not establish measured engineering productivity or accepted end-to-end design validation.

## 4. Dated business ownership is part of the ontology

Fujifilm's completed transaction covers Entegris Electronic Chemicals, not all Entegris CMP assets. Rambus' PHY disposition closed September 6, 2023, distinct from next-day publication. Arm reports the Artisan disposition to Cadence on August 26, 2025. [PM11, PM26, PM27]

Synopsys acquired Ansys; Keysight later announced completion of specified Optical Solutions and PowerArtist purchases. Qualcomm announced completion of Alphawave. Tekscend's reported name/listing history also prevents a permanently private/old-name classification. [PM07, PM28, PM29, PM30]

Preserve exact business-effective dates when established and otherwise 'completed by publication date'; do not manufacture precision. Legacy brands can remain historical labels without dictating current economic attribution. Native issuer/security/listing bindings are unresolved in this research. No row below is a live constituent or valuation join.

## 5. Thirty-two company/business role records

These are scoped research roles, not a global census, 32 new public companies or revenue-purity estimates. Category adjacency does not create a commercial relationship. All native securities and revenue weights remain unresolved.

| Business | Role and proposed demand lens | Sources |
|---|---|---|
| Wacker | Semiconductor-grade purification; grade-specific demand versus mixed solar segment | PM03 |
| Sibelco | Quartz for crucibles/quartzware; route and qualified source | PM04, PM02 |
| SUMCO | Silicon wafer routes and product categories; application qualification | PM02 |
| Siltronic | Epitaxial wafers and specialty development; application-specific adoption | PM05 |
| Soitec | POI engineered substrates; acoustic-filter demand and qualification | PM20 |
| HOYA | Mask blanks; designs and patterning transitions | PM01 |
| AGC | EUV blank structure/materials; defect requirements and qualification | PM06 |
| Tekscend Photomask | Patterned masks; accepted mask-set delivery | PM07, PM08 |
| IMS Nanofabrication | Mask-writing equipment; mask-shop investment and capability | PM08 |
| Tokyo Ohka Kogyo | Resist and ancillary patterning chemistry; accepted process use | PM09 |
| JSR | Patterning-material collaboration; formulation and licensing scope | PM10 |
| Inpria | Metal-oxide resist; application-specific adoption | PM10 |
| Lam Research | Dry-resist/process collaboration in this installment | PM10 |
| Fujifilm | Acquired electronic chemicals business; correct asset scope | PM11 |
| Entegris | CMP consumables, filtration and cleaning; qualified usage | PM12 |
| Linde | On-site gas systems; contracts, commissioning and delivered supply | PM13 |
| Air Liquide | Gas projects; exact phase and customer binding | PM14, PM15 |
| Merck KGaA / EMD Electronics | Materials versus systems/services; not US Merck | PM21 |
| ASM International | ALD tools; film/process adoption and equipment economics | PM16 |
| VAT | Vacuum control; subsystem content and installed demand | PM17 |
| Fujimi | Material-specific CMP slurries; qualified recipe usage | PM18 |
| Ebara | CMP tools; configuration and productivity | PM19 |
| DISCO | Thinning/singulation; accepted route and handling yield | PM22 |
| SCREEN | Cleaning equipment; excerpt-only efficiency evidence | PM31 |
| MKS | Remote-plasma subsystem; excerpt-only, held detail | PM32 |
| Cadence | EDA and interface/physical IP; function and acquired assets | PM23, PM26, PM27 |
| Siemens EDA | Verification/simulation/thermal functions; scoped certification | PM24 |
| Rambus | Memory-controller IP; historical PHY disposition separate | PM25, PM26 |
| Arm | Processor IP plus described silicon program; separate economics | PM27 |
| Synopsys / Ansys | Design/simulation assets; current ownership and function | PM28, PM29, PM33 |
| Keysight | Acquired optical simulation and PowerArtist businesses | PM29 |
| Qualcomm / Alphawave | Acquired connectivity/custom-silicon business | PM30 |

## 6. Fourteen relationship examples

All remain RESEARCH_ONLY, not admitted native edges. Unknown dates and unnamed customers remain explicit.

| ID | Subject → object | Predicate and time distinction | Forbidden inference / source |
|---|---|---|---|
| PMX01 | JSR/Inpria → Lam | Non-exclusive collaboration, September 2025 announcement | Exclusive supply or universal adoption; PM10 |
| PMX02 | IMS → Tekscend/AMTC | Installation reported by 2024-11-12; precise installation day unestablished | Qualified masks/month; PM08 |
| PMX03 | Linde → Samsung | Announced expansion 2025-04-29; mid-2026 target | Realized commissioning from elapsed target; PM13 |
| PMX04 | Air Liquide → Micron | Named contract 2024-06-05; end-2025 target | Actual operation or identity with later phase; PM14 |
| PMX05 | Air Liquide → unnamed customer | Announcement 2026-07-23; 2028 target | Guessing buyer from geography; PM15 |
| PMX06 | Fujifilm → Electronic Chemicals | Completion reported by 2023-10-02; exact close day not separately established | Acquisition of all Entegris CMP; PM11 |
| PMX07 | Cadence → Rambus PHY | Exact close 2023-09-06; publication 2023-09-07 | Treating controller IP as the same asset; PM26 |
| PMX08 | Cadence → Arm Artisan | Exact asset disposition 2025-08-26 | All Arm IP transferred; PM27 |
| PMX09 | Synopsys → Ansys | Completed acquisition 2025-07-17 | Ignoring later asset dispositions; PM28 |
| PMX10 | Keysight → Optical Solutions/PowerArtist | Completion reported by 2025-10-17; exact close day not separately established | All optical software or all Ansys; PM29 |
| PMX11 | Qualcomm → Alphawave | Completion reported by 2025-12-18; exact close day not separately established | Native listing binding; PM30 |
| PMX12 | Cadence → TSMC processes | Function-scoped certification 2026-04-22 | Every tool/IP at every node; PM23 |
| PMX13 | Siemens → TSMC processes | Function-scoped certification 2026-04-22 | Universal end-to-end flow readiness; PM24 |
| PMX14 | Positron → Cadence | Reported licensed/design use by 2026-04-22 | Completed tapeout or volume shipment; PM23 |

## 7. Twelve bottleneck research cards

These are falsifiable questions, NOT twelve proven shortages. Each specifies the missing measurement and a competing explanation. Proposed monitoring uses existing ingestion/review owners; no watcher is created.

| ID / subject | Hypothesis and measurement needed | Alternative and falsifier | Sources |
|---|---|---|---|
| PMB01 Qualified silicon | A semiconductor grade could tighten despite weak commodity aggregates. Measure same-grade orders, delivery, qualified output and inventories in compatible units/site/period. | Mix or inventory correction may explain it. Stable delivery and sufficient accepted output falsify shortage. | PM03 |
| PMB02 Quartz/crucibles | Route-specific input constraints may affect qualified CZ lines. Need product/origin qualification, crucibles, inventory days and affected-line output. | Logistics or customer inventory may dominate. Accepted alternative supply or unaffected output falsifies binding constraint. | PM02, PM04 |
| PMB03 Design-to-mask | More designs could pressure blank/writing turnaround without proportional wafer growth. Need comparable mask complexity, accepted turnaround and demand. | Respins or complexity mix may explain delays. Stable/shorter comparable turnaround falsifies capacity pressure. | PM01, PM06, PM08 |
| PMB04 Resist transition | New material/process combinations may change demand after qualification. Need named adoption, layer scope, accepted defect/yield and recurring orders. | A pilot or license may never become production. No adoption, alternatives or simplification falsify broad benefit. | PM09, PM10 |
| PMB05 Deposition/subsystems | Architecture changes may raise selected processing requirements. Need accepted steps, configuration, throughput, allocation and subsystem content. | Productivity or a different route can offset intensity. Output growth without utilization/order pressure weakens bottleneck thesis. | PM16, PM17, PM21 |
| PMB06 CMP | Specific recipes may constrain slurry, pad, monitoring or tools. Need matched material/recipe, qualification, yield and delivery. | Tuning or optional-module gaps may be the cause. Qualified alternatives or tool headroom falsify supply shortage. | PM12, PM18, PM19 |
| PMB07 Cleaning | Sensitive processes may need better control, not more liters. Need same-process defects, net use, reuse and delivered quality. | Efficiency reduces volume; value per unit may change. Stable quality and falling net use weaken volume-growth thesis. | PM09, PM12, PM21, PM31 |
| PMB08 Gas commissioning | Announced projects may be unavailable until accepted service. Need exact phase, commissioning and delivered specification. | Customer fab delays may dominate. Accepted supply ahead of need falsifies gas bottleneck. | PM13–PM15 |
| PMB09 Thin-die integration | Handling/singulation may constrain a specific route. Need comparable thickness, breakage/yield and qualified throughput. | Upstream defects or assembly handling may dominate. Stable good-unit yield and capacity headroom falsify it. | PM22 |
| PMB10 EDA readiness | A missing required function may delay a specific design. Need tool/version/task/node/PDK receipt and actual use milestone. | Licensing, staffing or design schedule may be the issue. Accepted required function in actual workflow falsifies readiness gap. | PM23, PM24, PM33 |
| PMB11 Controller/PHY | Integration depends on compatible IP, not only one catalog label. Need chosen revisions, PDK/interface support and silicon validation. | Package/memory supply may be limiting instead. Validated integration without timing/delivery constraint falsifies IP bottleneck. | PM25, PM26 |
| PMB12 Attribution | Outdated asset ownership can misassign exposure. Need asset scope, exact/evidenced-by date, native identity and comparable segment disclosure. | Legacy branding or consolidated reporting can obscure the role. Confirmed current scope resolves mapping; financial exposure may remain unknown. | PM07, PM11, PM26–PM30 |

## 8. User journeys and shared-product requirements

**Design proliferation:** a user selects semiconductor design activity and sees blank/mask, EDA/IP and wafer-volume roles separately. Explain the source-supported mechanism and competing effects; do not manufacture a common sector-demand percentage.

**Material disruption:** show the exact grade/route and qualified dependency, what is known about inventory or alternatives, and why a downstream consequence is still unproven. Unknown customer/capacity does not make the mechanism useless, but it forbids precise loss estimates.

**New-node announcement:** show tool/function/version/process/PDK compatibility, the source milestone and date. A certification cannot look like a shipped chip. Separate controller/PHY and other IP requirements.

**Ownership change:** preserve historical and current asset attribution using evidenced intervals. Only existing validated identity joins may expose a security/financial link. Correcting research ownership does not independently retune investment policy.

Reuse `state_of_themes.html`, the existing semiconductor detail route and the shared Robotics/template architecture. Provide a concise mechanism summary, role/facet filters, source drawer, explicit unavailable states and native company return links. Keep physical composition, manufacturing enablement and commercial relations distinct. Use an unweighted map when quantities are unavailable; widths require comparable units and non-overlapping purchase boundaries. No new graph, global product master, store, curation queue, publisher or browser-time crawler.

GMI evidence/curation/identity owners remain canonical; K1 references native records and F04 composes the workflow. The optional Robotics evidence/clock proposal remains a dependency to reconcile, not automatically enrolled semiconductor capability. Private current full-fidelity assertions cannot enter public Git/static mirrors. All records here are editorial proposals and bounded public-source examples.

The eventual accepted assertion must preserve source lineage/locator, upstream publication, observation time, business-valid interval or explicit unknown, subject/object scope, milestone, process/product/configuration, geography basis, quantity/unit/denominator, qualification, corrections, retention and review. Company economics additionally require correct effective asset ownership, fiscal period and consolidation basis. Provenance must support an understandable mechanism, not substitute for one.

## 9. Twenty-two future acceptance requirements

These are design discrimination cases, not executed application tests.

PMV01: blank, mask, writer and exposure remain different roles.
PMV02: crucible quartz is not generic silicon feedstock inside every chip.
PMV03: FZ availability does not prove qualified CZ substitution.
PMV04: grade-specific capacity growth does not apply to all polysilicon.
PMV05: mixed segment financials are not semiconductor-only exposure.
PMV06: catalog, certification, installation, qualification and volume remain separate.
PMV07: non-exclusive cooperation cannot become exclusive procurement.
PMV08: category adjacency cannot originate named supplier contracts.
PMV09: optional tool modules are not presumed installed.
PMV10: unnamed customers and unbound project phases cannot be guessed/aggregated.
PMV11: elapsed targets do not become actual starts.
PMV12: Rambus 2023-09-06 event remains distinct from 2023-09-07 publication.
PMV13: Arm Artisan 2025-08-26 date and limited asset scope survive.
PMV14: dispositions change only the specified business mapping.
PMV15: EDA readiness stays function/tool/node/version scoped.
PMV16: controller IP, PHY IP and manufactured memory remain distinct.
PMV17: future own-silicon production is not realized shipments/revenue.
PMV18: unknown identities, dates, capacity and exposure remain unknown.
PMV19: process intensity can be offset by productivity/reuse; assumptions remain explicit.
PMV20: research confidence cannot create weights, rank, entry, size or trades.
PMV21: current private data uses accepted native/authenticated owners, not static leakage.
PMV22: excerpts and repeated release lineages cannot inflate full-review/independent-evidence counts.

## 10. Primary-source register

BODY means relevant page text inspected, not all appendices, source-independent corroboration or accepted native retention. EXCERPT means official search extract only. Dates below are publication/report labels, not automatically business-effective dates. Observed 2026-09-23. No original-source content digests or native retention receipts are invented.

| ID | Publisher / date / review | Locator and limit | URL |
|---|---|---|---|
| PM01 | HOYA / 2024 report / BODY | Mask Blanks overview/outlook; historical mechanism, not current orders/share | https://www.hoya.com/ir/2024/en/review/it.html |
| PM02 | SUMCO / undated / BODY | Crystal growth and wafer categories; no universal substitution | https://www.sumcosi.com/english/products/process/ |
| PM03 | Wacker / FY2025, publication day unknown / BODY | Polysilicon performance and purification line; mixed financial denominator | https://reports.wacker.com/2025/annual-report/management-report/segments/polysilicon.html |
| PM04 | Sibelco / undated / BODY | Semiconductor applications; no universal sole-source or shortage claim | https://www.sibelco.com/en/materials/high-purity-quartz |
| PM05 | Siltronic / undated / BODY | Epitaxial products/development; not measured qualified volume | https://www.siltronic.com/en/products/epitaxial-wafers.html |
| PM06 | AGC / undated / BODY | EUV blank structure; not completed masks or scanner | https://www.agcem.com/products/euv-mask-blanks/ |
| PM07 | Tekscend / undated, dated milestones / BODY | Profile/history; no native security binding | https://www.photomask.com/en/about/ |
| PM08 | Tekscend / 2024-11-12 / BODY | IMS/AMTC installation; not qualified output rate | https://www.photomask.com/en/news/press/20241112160857.html |
| PM09 | TOK / undated / BODY | Patterning/ancillary categories; not named procurement | https://www.tok.co.jp/eng/products/semiconductor-pre |
| PM10 | JSR / 2025-09-16, US dateline 09-15 / BODY | Non-exclusive cooperation; not volume adoption | https://www.jsr.co.jp/jsr_e/news/2025/20250916.html |
| PM11 | Fujifilm / 2023-10-02 / BODY | Acquired Electronic Chemicals scope; not all Entegris CMP | https://www.fujifilm.com/us/en/news/semiconductor-materials/fujifilm-completes-acquisition-of-electronic-chemicals-business-from-entegris |
| PM12 | Entegris / undated / BODY | CMP solution body; no customer-specific recipe | https://www.entegris.com/en/home/our-science/by-industry/microelectronics/semiconductor/cmp.html |
| PM13 | Linde / 2025-04-29 / BODY | Pyeongtaek expansion target; actual start unverified | https://www.linde.com/news-and-media/2025/linde-to-expand-supply-of-industrial-gases-to-samsung-in-south-korea |
| PM14 | Air Liquide / 2024-06-05 / BODY | Named Micron project; planned start only | https://www.airliquide.com/group/press-releases-news/2024-06-05/air-liquide-signed-major-contract-support-semiconductor-industry-us-investment-more-250-million |
| PM15 | Air Liquide / 2026-07-23 / BODY | Unnamed customer and 2028 target; buyer/phase unresolved | https://www.airliquide.com/group/press-releases-news/2026-07-23/air-liquide-invests-over-150m-usd-us-facilitate-growth-leading-global-memory-chip-manufacturer |
| PM16 | ASM International / undated / BODY | EmerALD applications; not ASMPT or named customer | https://www.asm.com/our-technology-products/ald/xp4-emerald |
| PM17 | VAT / undated / BODY | Series 61.3 application; no named OEM procurement | https://www.vatgroup.com/series/butterfly-control-vacuum-valve |
| PM18 | Fujimi / undated / BODY | PLANERLITE categories; recipe qualification unproven | https://www.fujimiinc.co.jp/english/service/cmp/lineup.html |
| PM19 | Ebara / undated / BODY | Platform/options; optional functions not universal | https://www.ebara.com/global-en/products/FREX300XA/ |
| PM20 | Soitec / undated / BODY | POI substrates/application; not all engineered wafers | https://www.soitec.com/home/products/product-platforms/poi |
| PM21 | Merck KGaA/EMD / FY2025, updated 2026-03-05 / BODY | Electronics businesses and corporate identity; not pure semiconductor denominator | https://www.reports.emdgroup.com/en/annualreport/2025/management-report/fundamental-information-about-the-group/company-profile-and-structure/electronics.html |
| PM22 | DISCO / undated / BODY | DBG comparison; no named HBM customer/generation | https://www-hq.disco.co.jp/eg/solution/library/dbg/dbg_process.html |
| PM23 | Cadence / 2026-04-22 / BODY | Certification/A14/Positron scopes; not production proof | https://www.cadence.com/en_US/home/company/newsroom/press-releases/pr/2026/cadence-collaborates-with-tsmc-to-accelerate-design-of-next.html |
| PM24 | Siemens / 2026-04-22 / BODY | English Calibre/Solido/thermal body; not vendor-wide readiness | https://news.siemens.com/cs-cz/siemens-eda-tsmc-technology-symposium-2026/ |
| PM25 | Rambus / undated / BODY | Controller/PHY integration; not memory production | https://www.rambus.com/interface-ip/hbm/hbm4-controller/ |
| PM26 | Rambus/SEC / 2023-09-07 / BODY | Item 2.01; exact close day is 09-06 | https://www.sec.gov/Archives/edgar/data/917273/000119312523230180/d524084d8k.htm |
| PM27 | Arm / quarter to 2026-06-30, August filing / BODY | Artisan, license/royalty and silicon program; future output not realized | https://investors.arm.com/node/8361/html |
| PM28 | Synopsys/SEC / 2025-07-17 / BODY | Completed Ansys acquisition; later dispositions separate | https://www.sec.gov/Archives/edgar/data/883241/000114036125026140/ef20051970_425.htm |
| PM29 | Keysight / 2025-10-17 / BODY | Two acquired businesses; not all optical/Ansys products | https://investor.keysight.com/investor-news-and-events/financial-press-releases/press-release-details/2025/Keysight-Completes-Acquisition-of-Synopsys-Optical-Solutions-Group-and-Ansys-PowerArtist/default.aspx |
| PM30 | Qualcomm / 2025-12-18 / BODY | Completion and business; native listing unbound | https://www.qualcomm.com/news/releases/2025/12/qualcomm-completes-acquisition-of-alphawave-semi |
| PM31 | SCREEN / 2022-12-07 / EXCERPT | Official extract; release/product access failed; numerical conditions held | https://www.screen.co.jp/en/news/NR221207E |
| PM32 | MKS / undated / EXCERPT | Official extract; no substantive page body returned | https://www.mks.com/f/r-evolution-5-remote-rf-plasma-source |
| PM33 | Synopsys / 2025-09-24 / EXCERPT | Official extract; opened page exposed navigation, not substantive body | https://news.synopsys.com/2025-09-24-Synopsys-Collaborates-with-TSMC-to-Drive-the-Next-Wave-of-AI-and-Multi-Die-Innovation |

## 11. Verification and remaining research

Offline companion: `SEMICONDUCTOR_CHUNK2_RESEARCH.json`, produced by `build_chunk2.py`; the expanded portable dossier is separately rendered from those authored records, not mislabeled as a downloaded byte-identical copy of this canonical Markdown.

Observed QA: **26 integrity checks PASS; 0 product tests; no independent review.** Checks cover unique IDs/URLs, 30 BODY versus 3 EXCERPT records, locators/limits, unresolved identity/exposure, references, 14 scoped relationships, dates, 12 falsifiable cards, 22 future acceptance specifications, two arithmetic examples, JSON round-trip and overlap with the prior source register. New 33 URLs are distinct from the prior 38: cumulative 71 URLs, not 71 full-document reviews or independent confirmations. Canonical publication readback is separately required; this sentence does not self-certify it.

Still absent: global qualified-capacity, lead-time, inventory, yield, market-share and contract-price series; full regional/competitor coverage; accepted securities and comparable business exposure; native retention/admission; approved semiconductor design; implementation and production proof. Catalog capability does not close those gaps.

Next bounded research chunk: **non-AI semiconductor demand and components** — analog/signal-chain, MCUs/embedded compute, power silicon/SiC/GaN, RF/acoustic filters, sensors, mature/specialty foundries and conventional memory. Develop Robotics/automotive/industrial application-to-component mappings and separate end demand, inventories and qualification. Follow with facility-qualified capacity and business economics before the written design and final Fable implementation packet. Preserve the existing shared template; no interface custody changes here.

MISSION_COMPLETE: false. Keep PR #7780 draft/HOLD. No automatic merge, Fable handoff or background execution is implied.
