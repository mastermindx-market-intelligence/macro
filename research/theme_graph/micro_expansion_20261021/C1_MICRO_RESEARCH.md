# GMI micro-theme expansion C1 — compute & energy groups (2026-10-21)

Status: PROPOSED display-tier taxonomy content for seat ratification — this lane proposes, never ratifies.
Commission: GMI COMPLETION seat (Fable Meta-CEO, Chairman commission 2026-10-21, "microthemes should immensely and aggressively go beyond the original masterplan").
Base: ca7edbcf50df21bd321bffa3433e5f105d3335da · Frozen law: `research/theme_graph/taxonomy_upgrade_v2/SPEC.md` (row keys, tiers, PARENT_OF pairs) · Format exemplar: `research/theme_graph/hierarchy_content/C1_CATEGORIES_AND_COMPUTE_ENERGY.md` (its existing rows are respected and extended, never renamed or re-id'd).
Group C1 themes: `theme:ai_semiconductors`, `theme:memory_storage`, `theme:semicap_equipment`, `theme:data_center_power`, `theme:nuclear_power`, `theme:grid_electrification`, `theme:solar`.

Housekeeping rules observed in this record:

- No issuers, tickers, constituents or "examples of companies" anywhere — rows describe what an equity issuer DOES (defining_activities are verb phrases), never who does it.
- No vendor theme families as sources or nominators (finviz, ths/tonghuashun, china_ths, `ltheme:`, `basket:baskets_china_ths:*`). Every micro cites ≥2 public non-vendor references by name (industry associations, standards bodies, regulator classifications, filing segment vocabulary, trade-press value-chain maps, academic/industry reports).
- `value_chain_position` is display-only per SPEC §1; every proposed micro carries it.
- All proposed ids were checked against every existing id in ALL tiers (10 categories, 18 themes incl. `themes:` keys, 12 sub_themes, 68 micro_themes) — zero collisions.
- Prior C1 adjudications respected: no stance/loser-class naming; no subset rows that merely restate an existing coarse slice (e.g. no SMR row under `theme:reactor_technology`, no front-end stage rows under `theme:fuel_cycle`; the back-end (spent fuel, decommissioning) is genuinely uncovered and is therefore proposed).
- Companion machine-readable file: `research/theme_graph/micro_expansion_20261021/C1_PROPOSED_ROWS.yaml`.
## theme:ai_semiconductors — AI Semiconductors（AI半导体）

Scope: the AI logic-silicon value chain from design tooling and IP through leading-edge manufacturing, integration and the process-materials feedstock. Existing rows (`theme:gpu_merchant_accelerators`, `theme:custom_asic_silicon`, `theme:ai_interconnect_silicon`, `theme:hbm_packaging`, `theme:sic_gan_specialty`) stay; every row below ADDS a mechanism they do not cover.

Sub-theme grouping: three new sub_themes group the additions. `theme:ai_semiconductor_design_chain`（AI芯片设计链）holds the enabler layer that makes chip design itself an industry (EDA, IP, chiplet partitioning). `theme:advanced_packaging_integration`（先进封装与集成）holds the back-end integration positions (logic 2.5D/3D packaging, substrates/interposers, co-packaged optics, OSAT, silicon photonics). `theme:ai_semiconductor_materials`（半导体工艺材料）holds the consumable feedstock positions (masks, photoresist, gases, CMP consumables, large wafers). `theme:advanced_node_foundry` stays a direct theme child as the manufacturing midpoint both design and materials feed.

Theme-tier candidates (prose only): none this pass. The design-chain rows are enablers of chip themes, not a separate "AI design software" theme; packaging integration belongs under this theme because its demand driver is AI logic volume.

### eda-design-automation
- id: theme:eda_design_automation
- name_en: EDA design automation
- name_zh: EDA电子设计自动化
- value_chain_position: enabler
- parent_sub_theme: theme:ai_semiconductor_design_chain
- defining_activities: developing placement/routing/simulation and verification software; licensing time-based tool subscriptions to chip design teams; building AI-assisted design and sign-off flows; maintaining process design-kit (PDK) compatibility with foundry nodes
- distinct_from: theme:custom_asic_silicon — ASIC rows are chip products someone designs; this row is the software toolchain the designing itself runs on
- exclusions: semiconductor IP blocks (separate row), foundry manufacturing, chip design services
- china_relevance: high — EDA is the most-sanctioned chokepoint in the Chinese chip toolchain and a standing 国产替代 category in policy catalogs
- confidence: high
- sources: IEEE International Roadmap for Devices and Systems (IRDS), IEEE; 《国家集成电路产业发展推进纲要》, 国务院 (2014); "Strengthening the Global Semiconductor Supply Chain", SIA/BCG

### semiconductor-ip-licensing
- id: theme:semiconductor_ip_licensing
- name_en: Semiconductor IP licensing
- name_zh: 半导体IP核授权
- value_chain_position: enabler
- parent_sub_theme: theme:ai_semiconductor_design_chain
- defining_activities: designing and licensing reusable processor/interface/foundation IP blocks; collecting per-unit royalties on shipped chips; qualifying IP against foundry PDKs; delivering hard/soft IP macro integration support
- distinct_from: theme:eda_design_automation — tools vs licensable design content; distinct_from theme:custom_asic_silicon — sells design components, never ships chips
- exclusions: EDA software, physical chip production
- china_relevance: medium — domestic CPU/GPU programs license instruction-set and interconnect IP; licensing revenue flows are a disclosed segment vocabulary
- confidence: high
- sources: IRDS, IEEE; UCIe Specification, Universal Chiplet Interconnect Express Consortium; 中国半导体行业协会年度运行报告 (CSIA annual industry report)

### chiplet-partition-design
- id: theme:chiplet_partition_design
- name_en: Chiplet architecture & die-to-die design
- name_zh: 芯粒（Chiplet）架构设计
- value_chain_position: upstream
- parent_sub_theme: theme:ai_semiconductor_design_chain
- defining_activities: partitioning monolithic SoCs into multi-die architectures; implementing die-to-die link PHYs and packaging co-design; licensing chiplet interconnect IP; qualifying multi-source chiplet ecosystems
- distinct_from: theme:ai_semiconductor_design_chain peers — designs the decomposition, not the tools or IP libraries; distinct_from theme:advanced_packaging_2_5d_3d — architecture and standards (UCIe-class) vs the manufacturing of the assembled package
- exclusions: actual assembly/bonding, HBM stacking
- china_relevance: high — 芯粒 is the named breakout path in Chinese trade press around advanced-node export limits
- confidence: medium
- sources: UCIe Specification, UCIe Consortium; IRDS, IEEE

### advanced-node-foundry
- id: theme:advanced_node_foundry
- name_en: Advanced-node logic foundry
- name_zh: 先进制程晶圆代工
- value_chain_position: midstream
- parent_sub_theme: none
- defining_activities: operating leading-edge logic wafer fabs (≤7nm-class and below); running secure PDK-enabled foundry services; multi-project-wafer shuttles and design-tape-out intake; capacity allocation and yield learning on EUV-class flows
- distinct_from: theme:gpu_merchant_accelerators / theme:custom_asic_silicon — manufactures for chip designers rather than designing; distinct_from theme:lithography_tools (semicap) — buys tools, does not build them; distinct_from theme:conventional_dram / memory fabs — logic process flows, not memory arrays
- exclusions: memory wafer fabrication (memory_storage row), OSAT services, equipment manufacture
- china_relevance: high — the central policy target of the Chinese fab-buildout; mature-node vs advanced-node split dominates Chinese disclosure vocabulary
- confidence: high
- sources: SEMI World Fab Forecast, SEMI; "Strengthening the Global Semiconductor Supply Chain", SIA/BCG; IRDS, IEEE

### advanced-packaging-2-5d-3d
- id: theme:advanced_packaging_2_5d_3d
- name_en: 2.5D/3D advanced packaging (AI logic)
- name_zh: 2.5D/3D先进封装制造
- value_chain_position: midstream
- parent_sub_theme: theme:advanced_packaging_integration
- defining_activities: manufacturing silicon-interposer and RDL-based 2.5D assemblies for AI logic; hybrid-bonding 3D die stacking; performing known-good-die and thermal-aware package co-design; qualifying package-level reliability
- distinct_from: theme:hbm_packaging — the existing row frames HBM memory stacking and its packaging angle; this row is AI-LOGIC integration (interposers, hybrid bonding of logic dies), not memory stacks
- exclusions: HBM stack manufacturing (memory side), standard wire-bond OSAT work, substrate manufacturing
- china_relevance: high — 先进封装 is the designated around-the-node strategy in Chinese industry planning
- confidence: high
- sources: IRDS (More-than-Moore chapter), IEEE; SEMI Advanced Packaging standards activity, SEMI

### advanced-substrate-interposer
- id: theme:advanced_substrate_interposer
- name_en: Advanced substrates & interposers (ABF)
- name_zh: 先进基板与载板（ABF载板）
- value_chain_position: upstream
- parent_sub_theme: theme:advanced_packaging_integration
- defining_activities: manufacturing ABF build-up package substrates; producing silicon interposers and RDL carriers; holding fine-line/fine-pitch lithography on organic substrates; capacity-qualifying new substrates for large-body AI packages
- distinct_from: theme:advanced_packaging_2_5d_3d — makes the carrier the package is built on vs performing the assembly; distinct_from theme:hbm_packaging — substrate supply is upstream of all packaging
- exclusions: conventional leadframe/BT substrate commodity work, assembly services
- china_relevance: high — 载板 is a named domestic-gap category in Chinese electronics-materials planning
- confidence: medium
- sources: SEMI Advanced Packaging standards activity, SEMI; IRDS, IEEE

### co-packaged-optics-integration
- id: theme:co_packaged_optics_integration
- name_en: Co-packaged optics integration
- name_zh: 共封装光学（CPO）集成
- value_chain_position: midstream
- parent_sub_theme: theme:advanced_packaging_integration
- defining_activities: integrating optical engines beside switch/compute ASICs in one package; co-designing fiber attach and external laser sources; qualifying optical-electrical co-packaging reliability; shipping CPO-enabled switch systems
- distinct_from: theme:ai_interconnect_silicon — that row is the electrical switch/network silicon; this row integrates PHOTONIC engines into the same package; distinct_from theme:silicon_photonics_devices — device-level chips vs package-level integration
- exclusions: pluggable transceiver module assembly (no dedicated existing row; excluded here to stay mechanism-clean), plain switch ASIC design
- china_relevance: high — CPO/光电共封装 is a tracked direction in Chinese compute-interconnect planning
- confidence: medium
- sources: IEEE 802.3 Ethernet standards activity, IEEE; OCP networking hardware specifications, Open Compute Project

### silicon-photonics-devices
- id: theme:silicon_photonics_devices
- name_en: Silicon photonics chip devices
- name_zh: 硅光子器件
- value_chain_position: midstream
- parent_sub_theme: theme:advanced_packaging_integration
- defining_activities: designing photonic integrated circuits on silicon platforms; manufacturing modulators/germanium photodetectors in wafer fabs; offering photonic foundry shuttle services; licensing photonic PDKs
- distinct_from: theme:co_packaged_optics_integration — the photonic CHIP itself vs its integration into packages; distinct_from theme:ai_interconnect_silicon — optical PHY devices vs electrical switch silicon
- exclusions: transceiver system assembly, CPO package integration, fiber manufacturing
- china_relevance: high — 硅光 is a standing category in Chinese optical-communication supply-chain coverage
- confidence: medium
- sources: IEEE photonic standards activity, IEEE; IRDS, IEEE

### ai-chip-osat
- id: theme:ai_chip_osat
- name_en: Assembly & test services (OSAT)
- name_zh: 封测代工服务（OSAT）
- value_chain_position: midstream
- parent_sub_theme: theme:advanced_packaging_integration
- defining_activities: performing flip-chip/wire-bond assembly at scale; running final test and burn-in for fabless customers; quote-to-bid capacity services across package families; expanding into 2.5D capability from conventional OSAT bases
- distinct_from: theme:advanced_packaging_2_5d_3d — leading-edge interposer/hybrid-bond work vs the conventional high-volume assembly/test service layer; distinct_from theme:semiconductor_ate (semicap) — performs testing as a service vs selling testers
- exclusions: leading-edge 2.5D/3D manufacturing (own row), memory-specific stacking
- china_relevance: high — 封测 is the segment of the Chinese chip chain where domestic share is highest and disclosure vocabulary is stable
- confidence: high
- sources: "Strengthening the Global Semiconductor Supply Chain", SIA/BCG; SEMI assembly & packaging standards, SEMI

### photomask-manufacturing
- id: theme:photomask_manufacturing
- name_en: Photomask manufacturing
- name_zh: 掩膜版制造
- value_chain_position: upstream
- parent_sub_theme: theme:ai_semiconductor_materials
- defining_activities: writing e-beam mask patterns; pellicle mounting and defect inspection/repair; multi-layer EUV mask blank processing; NDA-guarded mask services tied to design tapes
- distinct_from: theme:lithography_tools (semicap) — makes the reticle the tool exposes through, not the exposure tool; distinct_from theme:photoresist_semiconductor_materials — durable imaging master vs consumable resist chemistry
- exclusions: mask-writing equipment, mask inspection tool manufacture
- china_relevance: high — 掩膜版 self-sufficiency is an explicit gap category in Chinese materials planning
- confidence: medium
- sources: IRDS, IEEE; SEMI mask/pellicle standards, SEMI

### photoresist-semiconductor-materials
- id: theme:photoresist_semiconductor_materials
- name_en: Photoresist & imaging materials
- name_zh: 半导体光刻胶
- value_chain_position: upstream
- parent_sub_theme: theme:ai_semiconductor_materials
- defining_activities: formulating g/i-line, KrF, ArF and EUV photoresists; supplying developers, strippers and anti-reflective coatings; joint qualification with scanner/fab process windows; batch-to-batch purity control at ppb level
- distinct_from: theme:photomask_manufacturing — light-sensitive consumable vs durable pattern master; distinct_from theme:electronic_specialty_gases — formulated liquids vs bulk process gases
- exclusions: display/PCB photoresist grades, gases, CMP slurries
- china_relevance: high — 光刻胶 is the canonical 高端材料国产化 category in Chinese trade press
- confidence: high
- sources: 《首台（套）重大技术装备推广应用指导目录》配套材料目录, 工业和信息化部 (MIIT); IRDS, IEEE

### electronic-specialty-gases
- id: theme:electronic_specialty_gases
- name_en: Electronic specialty gases
- name_zh: 电子特气
- value_chain_position: upstream
- parent_sub_theme: theme:ai_semiconductor_materials
- defining_activities: producing high-purity etch/deposition gases (NF3, WF6, C4F8-class); on-site generation and cylinder-pack purification; gas analytics at trace-impurity levels; cylinder/ISO-canister logistics into fabs
- distinct_from: theme:photoresist_semiconductor_materials — gases vs formulated resist liquids; distinct_from theme:fab_facility_systems (semicap) — makes the gas vs delivering/abating it in the fab
- exclusions: bulk nitrogen/oxygen utility supply, gas delivery hardware
- china_relevance: high — 电子特气 is a mature A-share disclosure category with established domestic substitution dynamics
- confidence: high
- sources: SEMI gas/chemicals standards (SEMI C-series), SEMI; IRDS, IEEE

### cmp-polishing-consumables
- id: theme:cmp_polishing_consumables
- name_en: CMP polishing consumables
- name_zh: CMP抛光材料（抛光液/抛垫）
- value_chain_position: upstream
- parent_sub_theme: theme:ai_semiconductor_materials
- defining_activities: formulating silica/ceria slurries per film stack; engineering polyurethane polishing pads; co-optimizing consumable sets with CMP tool removal rates; consumable recycling and filtration services
- distinct_from: theme:cmp_planarization_equipment (semicap) — consumable chemistry vs the polishing machine; distinct_from theme:electronic_specialty_gases — slurry/pad systems vs gases
- exclusions: CMP tool manufacture, post-CMP cleaning chemistry (folded into wet process)
- china_relevance: medium — domestic slurry/pad qualification is an active but narrower substitution front
- confidence: medium
- sources: SEMI materials standards, SEMI; IRDS, IEEE

### large-diameter-silicon-wafers
- id: theme:large_diameter_silicon_wafers
- name_en: Large-diameter silicon wafers (12-inch)
- name_zh: 半导体大硅片（12英寸）
- value_chain_position: upstream
- parent_sub_theme: theme:ai_semiconductor_materials
- defining_activities: pulling 300mm CZ ingots; grinding/lapping/polishing/epi-wafer finishing; flatness and defect spec control for advanced nodes; long-term wafer supply agreements with fabs
- distinct_from: theme:polysilicon_solar_feedstock (solar) — electronic-grade float-zone/CZ silicon for devices vs solar feedstock; distinct_from theme:memory_wafer_fab (memory_storage) — sells raw wafers vs operating memory fabs
- exclusions: SOI specialty wafers as a service, polysilicon production, solar wafers
- china_relevance: high — 大硅片 is one of the best-known domestic-gap categories in Chinese semiconductor materials coverage
- confidence: high
- sources: SEMI wafer standards (SEMI M-series), SEMI; 中国半导体行业协会年度运行报告 (CSIA annual industry report)
## theme:memory_storage — Memory, HBM & Storage（存储与HBM）

Scope: the memory and storage value chain from wafer fabrication through module/system productization and the controller/interface silicon around it. Existing rows (`theme:conventional_dram`, `theme:nand_enterprise_storage`, `theme:hbm_packaging`) stay; every row below ADDS a mechanism they do not cover. No HBM restatement (respects the prior C1 rejection of HBM-duplicate rows).

Sub-theme grouping: one new sub_theme, `theme:memory_product_engineering`（存储产品与工程）, groups the productization/enabler layer (module manufacturing, controllers & firmware, interface chips, embedded storage, distribution, memory PHY/controller IP). The fabrication- and technology-layer rows (memory wafer fab, assembly/test & stacking services, niche memory, persistent memory, processing-in-memory, enterprise storage systems) stay direct theme children because they describe production and technology positions rather than product engineering.

Theme-tier candidates (prose only): none. Cloud object-storage services belong to software infrastructure, not to the memory theme's value chain.

### memory-wafer-fab
- id: theme:memory_wafer_fab
- name_en: Memory wafer fabrication (DRAM & NAND lines)
- name_zh: 存储晶圆制造
- value_chain_position: midstream
- parent_sub_theme: none
- defining_activities: operating gigafab-scale DRAM/NAND fabs; node migration (1x/1y-class DRAM, 2xx-layer NAND); yield learning and stack/process integration; capacity discipline across commodity cycles
- distinct_from: theme:conventional_dram / theme:nand_enterprise_storage — those are product/basket paths (who ships DRAM or NAND product); this row is the fab-process production layer itself; distinct_from theme:advanced_node_foundry (ai_semiconductors) — memory array processes vs logic flows
- exclusions: HBM stacking, module assembly, fab equipment supply
- china_relevance: high — 存储晶圆厂 buildout is a national-priority category in Chinese industrial policy
- confidence: high
- sources: JEDEC JESD79-5C DDR5 SDRAM Standard, JEDEC; 《国家集成电路产业发展推进纲要》, 国务院 (2014)

### memory-assembly-test
- id: theme:memory_assembly_test
- name_en: Memory assembly, test & stacking services
- name_zh: 存储封装测试与堆叠服务
- value_chain_position: midstream
- parent_sub_theme: none
- defining_activities: performing memory-specific back-end assembly (die attach, wire-bond/flip-chip); running memory final test with proprietary test times/timings; providing contract stacking services; wafer-level burn-in for enterprise parts
- distinct_from: theme:hbm_packaging — the existing row is the HBM & advanced packaging segment; this row is the SERVICE layer across memory back-end (incl. non-HBM parts); distinct_from theme:ai_chip_osat (ai_semiconductors) — memory-specific test/stack flows vs logic assembly
- exclusions: HBM segment framing, module productization, equipment manufacture
- china_relevance: high — memory 封测 capacity is a localized segment of the domestic storage chain
- confidence: medium
- sources: JEDEC packaging/test standards, JEDEC; SEMI assembly & packaging standards, SEMI

### memory-module-manufacturing
- id: theme:memory_module_manufacturing
- name_en: Memory module & card manufacturing
- name_zh: 存储模组制造
- value_chain_position: downstream
- parent_sub_theme: theme:memory_product_engineering
- defining_activities: building RDIMM/DIMM memory modules; assembling SSD and memory-card products from wafers/packaged die; firmware flashing and burn-in at module level; channel-ready packaging and fulfillment
- distinct_from: theme:nand_enterprise_storage — the existing row is the NAND & enterprise storage segment; this row is the module fabrication step for BOTH DRAM and NAND product; distinct_from theme:data_center_storage_systems — modules/components vs complete storage systems
- exclusions: controller chip design, wafer fabrication
- china_relevance: high — 存储模组 is a standard domestic segment with established disclosure vocabulary
- confidence: high
- sources: JEDEC module standards (RDIMM family), JEDEC; NVM Express Base Specification 2.0, NVM Express Inc.

### enterprise-ssd-controllers
- id: theme:enterprise_ssd_controllers
- name_en: Enterprise SSD controllers & firmware
- name_zh: 存储主控芯片与固件
- value_chain_position: enabler
- parent_sub_theme: theme:memory_product_engineering
- defining_activities: designing NAND-channel controller SoCs; developing FTL firmware, error correction and zoned-namespace features; qualifying controllers against enterprise workloads; licensing controller platforms to module makers
- distinct_from: theme:nand_enterprise_storage — media/segment vs the controller silicon + firmware that manages it; distinct_from theme:memory_interface_chips — storage-side compute vs DRAM-side interface chips
- exclusions: NAND fabrication, module assembly, host bus adapter silicon
- china_relevance: high — 主控芯片自主化 is a recurring theme in Chinese storage-industry coverage
- confidence: high
- sources: NVM Express Base Specification 2.0, NVM Express Inc.; JEDEC/SNIA solid state storage standards, SNIA

### memory-interface-chips
- id: theme:memory_interface_chips
- name_en: Memory interface & companion chips
- name_zh: 内存接口与配套芯片
- value_chain_position: enabler
- parent_sub_theme: theme:memory_product_engineering
- defining_activities: designing registering clock drivers and data buffers for server memory; building companion power-management and temperature-sensor chips; JEDEC-spec conformance across DDR5 generations; co-qualification with module makers
- distinct_from: theme:conventional_dram — interface silicon around DRAM vs the DRAM itself; distinct_from theme:enterprise_ssd_controllers — RDIMM-side interface vs SSD-side storage controllers
- exclusions: module manufacturing, DRAM fabrication
- china_relevance: high — 内存接口芯片 is an established A-share segment vocabulary with domestic champion dynamics
- confidence: high
- sources: JEDEC JESD79-5C DDR5 SDRAM Standard, JEDEC; JEDEC server-memory module standards, JEDEC

### embedded-storage-solutions
- id: theme:embedded_storage_solutions
- name_en: Embedded storage (eMMC/UFS)
- name_zh: 嵌入式存储（eMMC/UFS）
- value_chain_position: downstream
- parent_sub_theme: theme:memory_product_engineering
- defining_activities: packaging NAND+controller into eMMC/UFS embedded products; JEDEC embedded-standard qualification for mobile/automotive; long-term supply programs for device OEMs; auto-grade reliability screening
- distinct_from: theme:memory_module_manufacturing — socketed/card products vs soldered embedded standards; distinct_from theme:nand_enterprise_storage — mobile/embedded form factors vs enterprise drives
- exclusions: enterprise SSDs, controller chip design as a licensed platform
- china_relevance: medium — a steady domestic segment tied to smartphone/auto electronics cycles
- confidence: high
- sources: JEDEC eMMC/UFS standards, JEDEC; JEDEC automotive storage standards, JEDEC

### niche-memory-products
- id: theme:niche_memory_products
- name_en: Niche & specialty memory (NOR / niche DRAM)
- name_zh: 利基存储（NOR/利基DRAM）
- value_chain_position: midstream
- parent_sub_theme: none
- defining_activities: manufacturing specialty DRAM (consumer/graphics/automotive grades) on trailing nodes; producing NOR flash and SLC NAND; serving code-storage and industrial niches with long lifecycle commitments; specialty-process customization
- distinct_from: theme:conventional_dram — commodity mainstream DRAM vs trailing-node specialty lines; distinct_from theme:nand_enterprise_storage — code-flash niches vs enterprise NAND
- exclusions: HBM, emerging non-volatile media (separate row)
- china_relevance: medium — 利基存储 is the standard Chinese trade-press term for this product family
- confidence: high
- sources: JEDEC specialty-memory standards, JEDEC; 中国半导体行业协会年度运行报告 (CSIA annual industry report)

### persistent-memory-scm
- id: theme:persistent_memory_scm
- name_en: Persistent & storage-class memory
- name_zh: 持久内存与存储级内存（SCM）
- value_chain_position: upstream
- parent_sub_theme: none
- defining_activities: developing new non-volatile media (magnetic/phase-change/ferroelectric classes); qualifying SCM tiers between DRAM and NAND; standardizing persistent-memory programming models; early adopter programs in storage stacks
- distinct_from: theme:niche_memory_products — new media classes vs trailing-node conventional niches; distinct_from theme:processing_in_memory — memory hierarchy placement vs compute-in-memory architecture
- exclusions: mainstream DRAM/NAND, controller firmware
- china_relevance: low — research-stage globally; limited domestic disclosure vocabulary
- confidence: low
- sources: SNIA Solid State Storage Initiative specifications, SNIA; JEDEC standards activity on new memory classes, JEDEC

### processing-in-memory
- id: theme:processing_in_memory
- name_en: Processing-in-memory compute
- name_zh: 存算一体（PIM）
- value_chain_position: enabler
- parent_sub_theme: none
- defining_activities: integrating compute elements inside or beside memory arrays; building PIM-enabled accelerator stacks for AI inference; co-designing software stacks for near-memory execution; memory-vendor/foundry platform partnerships
- distinct_from: theme:persistent_memory_scm — new media vs compute placement; distinct_from theme:gpu_merchant_accelerators (ai_semiconductors) — in-memory execution vs discrete accelerators
- exclusions: conventional accelerator chips, storage-class media development
- china_relevance: medium — 存算一体 is an active Chinese research/startup direction with growing disclosure vocabulary
- confidence: low
- sources: IRDS (memristive/emerging devices chapter), IEEE; ISSCC/AI accelerator industry sessions trade coverage, IEEE Spectrum

### memory-distribution-channel
- id: theme:memory_distribution_channel
- name_en: Memory distribution & channel
- name_zh: 存储分销与渠道
- value_chain_position: downstream
- parent_sub_theme: theme:memory_product_engineering
- defining_activities: franchised distribution of memory components/modules; inventory buffering and price-risk intermediation across spot/contract markets; kitting and logistics for OEM/ODM builds; secondary-market channel services
- distinct_from: theme:memory_module_manufacturing — moves/finances product vs manufactures it; distinct_from theme:data_center_storage_systems — channel services vs system integration
- exclusions: manufacturing, retail e-commerce operations
- china_relevance: high — 存储分销 is a visible listed-company segment in Chinese electronics distribution
- confidence: high
- sources: 中国半导体行业协会年度运行报告 (CSIA annual industry report); NVM Express ecosystem market materials, NVM Express Inc.

### data-center-storage-systems
- id: theme:data_center_storage_systems
- name_en: Enterprise storage systems integration
- name_zh: 企业级存储系统集成（全闪存阵列）
- value_chain_position: downstream
- parent_sub_theme: none
- defining_activities: engineering all-flash arrays and scale-out storage systems; integrating media, controllers and storage software into appliances; enterprise service/support contracts; qualifying systems for virtualized and AI data pipelines
- distinct_from: theme:nand_enterprise_storage — the drive/media segment vs complete system integration; distinct_from theme:memory_module_manufacturing — modules vs engineered systems
- exclusions: cloud storage services (software infrastructure), drive fabrication
- china_relevance: medium — 存储系统/全闪存阵列 is a recognized domestic enterprise-IT segment
- confidence: high
- sources: SNIA storage system specifications, SNIA; NVM Express Base Specification 2.0, NVM Express Inc.

### memory-phy-ip
- id: theme:memory_phy_ip
- name_en: Memory PHY & controller IP
- name_zh: 存储PHY与控制器IP
- value_chain_position: enabler
- parent_sub_theme: theme:memory_product_engineering
- defining_activities: licensing DDR/HBM-class PHY IP; delivering memory-controller IP with protocol stacks; silicon-proven IP on foundry nodes; integration support for SoC teams
- distinct_from: theme:memory_interface_chips — licensable IP vs shipped companion chips; distinct_from theme:semiconductor_ip_licensing (ai_semiconductors) — memory-domain PHY/controller specialization vs logic/foundation IP
- exclusions: chip products, EDA tools
- china_relevance: medium — a narrow but visible domestic IP-design niche serving SoC teams
- confidence: medium
- sources: JEDEC interface standards, JEDEC; UCIe Specification (die-to-die PHY context), UCIe Consortium
## theme:semicap_equipment — Semiconductor Equipment (WFE)（半导体设备（WFE））

Scope: the equipment industry around wafer fabs — the process-tool classes beyond the existing litho/etch-deposition/metrology rows, the back-end equipment layer, and the fab-support chain (facility, automation, services, secondary market). Existing rows (`theme:lithography_tools`, `theme:etch_deposition_equipment`, `theme:process_metrology_inspection`, `theme:wafer_fab_subsystems`) stay; every row below ADDS a distinct tool class or chain layer.

Sub-theme grouping: two new sub_themes. `theme:semi_back_end_equipment`（后道封测设备）holds assembly/packaging toolmaking and test-equipment (ATE) positions. `theme:semicap_support_chain`（设备支持链）holds the around-the-tool layers (fab facility/cleanroom systems, CIM automation software, installation & field services, secondary/refurbished equipment). Six single-tool-class rows (implant, CMP, clean/wet, track, epitaxy/thermal, adjacent-industry equipment) stay direct theme children as siblings of the existing tool rows under `theme:wfe_process_tools`' theme (they remain theme-direct because the existing sub_theme `theme:wfe_process_tools` already carries its frozen rows and the new tool classes are peers, not members of it).

Theme-tier candidates (prose only): none. Fab construction itself is covered under grid/industrial engineering elsewhere; equipment for display/PV/power semis is kept inside this theme as one adjacent-equipment row rather than split into new themes.

### ion-implant-equipment
- id: theme:ion_implant_equipment
- name_en: Ion implant equipment
- name_zh: 离子注入设备
- value_chain_position: midstream
- parent_sub_theme: none
- defining_activities: building medium/high-energy ion implanters; developing beamline and dose-control technology; qualifying implant recipes per node; plasma-doping tool development for advanced flows
- distinct_from: theme:etch_deposition_equipment — different process-step family (doping vs material removal/addition); distinct_from theme:lithography_tools — pattern transfer vs dopant introduction
- exclusions: diffusion furnace thermal steps (epitaxy/thermal row), metrology tools
- china_relevance: high — 离子注入机 is a named domestic first-unit（首台套）equipment category
- confidence: high
- sources: 《首台（套）重大技术装备推广应用指导目录》, 工业和信息化部 (MIIT); IRDS, IEEE

### cmp-planarization-equipment
- id: theme:cmp_planarization_equipment
- name_en: CMP planarization equipment
- name_zh: CMP抛光设备
- value_chain_position: midstream
- parent_sub_theme: none
- defining_activities: manufacturing CMP polish platforms; developing head/plate and endpoint-detection systems; co-optimizing removal-rate performance with consumable vendors; servicing installed tool fleets
- distinct_from: theme:etch_deposition_equipment — mechanical-chemical planarization vs deposition/etch; distinct_from theme:cmp_polishing_consumables (ai_semiconductors) — machine vs slurry/pad consumables
- exclusions: post-CMP cleaning modules beyond the tool, consumable manufacture
- china_relevance: high — a tracked domestic equipment breakpoint category
- confidence: high
- sources: IRDS, IEEE; SEMI equipment standards (SEMI E-series), SEMI

### wet-clean-equipment
- id: theme:wet_clean_equipment
- name_en: Wafer cleaning & wet process equipment
- name_zh: 晶圆清洗与湿法设备
- value_chain_position: midstream
- parent_sub_theme: none
- defining_activities: manufacturing single-wafer and batch wet-cleaning tools; developing megasonic/SC1-SC2 process hardware; building electroplating and wet-etch stations; chemical-recycling and rinse-water reduction systems
- distinct_from: theme:etch_deposition_equipment — wet chemistry process steps vs plasma dry processing; distinct_from theme:fab_facility_systems — process tool vs fab utility systems
- exclusions: CMP polish tools, dry plasma clean integrated in deposition tools
- china_relevance: high — 清洗设备 is a leading domestic-substitution equipment segment
- confidence: high
- sources: SEMI E-series equipment standards, SEMI; 中国电子专用设备工业协会 (CEIA) annual semiconductor-equipment statistics

### coat-develop-track
- id: theme:coat_develop_track
- name_en: Coat-develop track equipment
- name_zh: 涂胶显影设备
- value_chain_position: midstream
- parent_sub_theme: none
- defining_activities: manufacturing resist coat/develop tracks; hotplate/chill and dispense-system engineering; micron-level co-operation with scanner exposure tools; EUV-era track process development
- distinct_from: theme:lithography_tools — the companion track cluster vs the exposure scanner itself; distinct_from theme:photoresist_semiconductor_materials (ai_semiconductors) — dispensing machine vs the resist chemistry
- exclusions: scanner manufacture, resist supply
- china_relevance: high — 涂胶显影 is an established domestic equipment category in A-share disclosure
- confidence: high
- sources: SEMI E-series equipment standards, SEMI; IRDS, IEEE

### epitaxy-thermal-equipment
- id: theme:epitaxy_thermal_equipment
- name_en: Epitaxy & thermal process equipment
- name_zh: 外延与热处理设备
- value_chain_position: midstream
- parent_sub_theme: none
- defining_activities: building epitaxial deposition reactors (Si/SiGe/GaN classes); manufacturing oxidation/diffusion and rapid-thermal-processing furnaces; layer-thickness/uniformity process control; specialty epi services for power/compound lines
- distinct_from: theme:ion_implant_equipment — layer growth/thermal treatment vs dopant implantation; distinct_from theme:etch_deposition_equipment — epi/thermal furnace family vs CVD/PVD/ALD thin-film tooling
- exclusions: thin-film CVD/ALD tools (inside existing etch_deposition row), metrology
- china_relevance: medium — domestic epi/furnace qualification is advancing but less publicly tracked than track/clean tools
- confidence: medium
- sources: IRDS, IEEE; SEMI E-series equipment standards, SEMI

### advanced-packaging-equipment
- id: theme:advanced_packaging_equipment
- name_en: Advanced packaging & assembly equipment
- name_zh: 先进封装与后道设备
- value_chain_position: midstream
- parent_sub_theme: theme:semi_back_end_equipment
- defining_activities: building bonders/placers for 2.5D/3D flows; wafer-level molding, plating and TSV etch tooling; hybrid-bonding tool development; die-attach and flip-chip platform families
- distinct_from: theme:advanced_packaging_2_5d_3d (ai_semiconductors) — toolmaker vs packaging service provider; distinct_from theme:wafer_fab_subsystems — back-end equipment vs front-end subsystem supply
- exclusions: test equipment (ATE row), packaging materials
- china_relevance: high — 后道设备国产化 tracks the domestic 先进封装 buildout
- confidence: high
- sources: SEMI advanced packaging standards, SEMI; 中国电子专用设备工业协会 (CEIA) annual semiconductor-equipment statistics

### semiconductor-ate
- id: theme:semiconductor_ate
- name_en: Semiconductor test equipment (ATE)
- name_zh: 半导体测试设备（ATE）
- value_chain_position: midstream
- parent_sub_theme: theme:semi_back_end_equipment
- defining_activities: manufacturing wafer-sort and final-test ATE systems; device-power/consumption test-head engineering; prober and handler integration; test-program library and correlation services
- distinct_from: theme:ai_chip_osat (ai_semiconductors) — sells testers vs performing test as a service; distinct_from theme:process_metrology_inspection — electrical test vs optical/process metrology
- exclusions: inspection/metrology optics, assembly bonders
- china_relevance: medium — domestic ATE is an active but harder-to-localize segment
- confidence: high
- sources: SEMI test standards, SEMI; IRDS, IEEE

### fab-facility-systems
- id: theme:fab_facility_systems
- name_en: Fab facility & cleanroom systems
- name_zh: 洁净室与厂务系统工程
- value_chain_position: downstream
- parent_sub_theme: theme:semicap_support_chain
- defining_activities: engineering cleanroom HVAC and recirculation air systems; bulk gas and chemical delivery (CUB/CBS) systems; vibration/EMI control and fab wide-area utilities; waste treatment and abatement skids
- distinct_from: theme:etch_deposition_equipment — the facility layer around tools vs process tools; distinct_from theme:electronic_specialty_gases (ai_semiconductors) — delivers/abates gas vs produces it
- exclusions: process equipment, CIM software
- china_relevance: high — 厂务/洁净室 engineering rides every domestic fab shell buildout
- confidence: high
- sources: SEMI facility standards (SEMI F-series), SEMI; 中国电子专用设备工业协会 (CEIA) annual semiconductor-equipment statistics

### fab-automation-cim
- id: theme:fab_automation_cim
- name_en: Fab automation & CIM software
- name_zh: 晶圆厂自动化与CIM软件
- value_chain_position: enabler
- parent_sub_theme: theme:semicap_support_chain
- defining_activities: deploying MES/YMS recipe and lot-control systems; automated material handling systems (AMHS overhead hoist transport); scheduling/dispatch and equipment-automation integration (SECS/GEM); fab data platforms
- distinct_from: theme:fab_facility_systems — software/automation vs physical utilities; distinct_from theme:grid_dispatch_ems_software (grid) — plant-level manufacturing execution vs power-grid dispatch
- exclusions: hardware transport vehicles as a standalone line, EDA software
- china_relevance: high — CIM/MES substitution is a named software breakpoint in domestic fab programs
- confidence: high
- sources: SEMI SECS/GEM equipment-automation standards, SEMI; IRDS, IEEE

### equipment-field-services
- id: theme:equipment_field_services
- name_en: Equipment installation & field services
- name_zh: 半导体设备安装与维保服务
- value_chain_position: downstream
- parent_sub_theme: theme:semicap_support_chain
- defining_activities: rigging/installing and qualifying tools in fabs; long-term service contracts and spare-parts fulfillment; tool upgrades and retrofits; multizone field-engineer networks
- distinct_from: theme:wafer_fab_subsystems — services on installed base vs component supply; distinct_from theme:refurbished_equipment_market — service revenue vs resale/refurbishment of used tools
- exclusions: new-tool manufacture, facility construction
- china_relevance: medium — localization of service/spares is an ongoing but quieter domestic segment
- confidence: high
- sources: SEMI E10/E79 equipment-reliability service standards, SEMI; 中国电子专用设备工业协会 (CEIA) annual semiconductor-equipment statistics

### refurbished-equipment-market
- id: theme:refurbished_equipment_market
- name_en: Secondary & refurbished equipment
- name_zh: 二手及翻新半导体设备
- value_chain_position: downstream
- parent_sub_theme: theme:semicap_support_chain
- defining_activities: sourcing/decommissioning used tools; refurbishing to spec with warranty; reselling into trailing-node, specialty and education fabs; parts harvesting and lifecycle extension
- distinct_from: theme:equipment_field_services — transacts used-tool value vs maintaining new-tool installed base; distinct_from theme:advanced_node_foundry — enables trailing nodes, not leading-edge
- exclusions: new equipment OEM channels, broker-only trading without refurbishment
- china_relevance: medium — a visible channel in Chinese mature-node fab economics
- confidence: medium
- sources: SEMI secondary-equipment guidance, SEMI; 中国电子专用设备工业协会 (CEIA) annual semiconductor-equipment statistics

### adjacent-semiconductor-equipment
- id: theme:adjacent_semiconductor_equipment
- name_en: Adjacent-fab equipment (display, PV, power semis)
- name_zh: 泛半导体设备（显示/光伏/功率半导体）
- value_chain_position: midstream
- parent_sub_theme: none
- defining_activities: adapting litho/etch/deposition platforms for display panels; supplying PV cell/module production equipment; building SiC/GaN power-device process lines; cross-selling tool platforms across electronics manufacturing
- distinct_from: the WFE tool rows — serves display/PV/power-semi fabs, not logic/memory wafer fabs; distinct_from theme:pv_manufacturing_equipment (solar) — multi-industry tool families vs PV-line-dedicated equipment
- exclusions: wafer-fab WFE classes already covered, downstream panel/module production
- china_relevance: high — 泛半导体设备 is the standard Chinese trade-press umbrella for this adjacency
- confidence: medium
- sources: 中国电子专用设备工业协会 (CEIA) annual semiconductor-equipment statistics; SEMI display/PV standards activity, SEMI
## theme:data_center_power — Data Center Power & Cooling（数据中心电力与散热）

Scope: the campus-layer value chain that powers and cools compute facilities — power train equipment, cooling technologies, and the site-energy/integration layer. Existing rows (`theme:liquid_cooling_thermal`, `theme:hv_transformers_switchgear`, `theme:ups_power_conversion`) stay; every row below ADDS a mechanism they do not cover.

Sub-theme grouping: three new sub_themes. `theme:datacenter_cooling_chain`（数据中心散热链）groups the cooling-technology positions (cold plate, immersion, air-side precision cooling, heat rejection/recovery, thermal fluids). `theme:datacenter_power_chain`（数据中心供配电链）groups the electrical train (DC power architecture, generator sets, battery backup, busway/PDU, server PSUs). `theme:datacenter_site_energy`（数据中心场地能源与集成）groups the site/integration layer (behind-the-meter generation, grid interconnection, prefabricated modular builds, DCIM software).

Theme-tier candidates (prose only): none. Behind-the-meter generation stays here (demand-side of the data-center campus) rather than under nuclear/generation themes; nuclear SMR power purchase is noted as a context, not a row.

### cold-plate-liquid-cooling
- id: theme:cold_plate_liquid_cooling
- name_en: Cold-plate direct liquid cooling
- name_zh: 冷板式液冷
- value_chain_position: midstream
- parent_sub_theme: theme:datacenter_cooling_chain
- defining_activities: manufacturing server cold plates and manifolds; building coolant distribution units (CDUs); in-rack quick-disconnect and leak-detection engineering; single/two-phase loop qualification with server OEMs
- distinct_from: theme:liquid_cooling_thermal — the existing row is the broad liquid-cooling & thermal segment; this row is the cold-plate loop TECHNOLOGY specifically; distinct_from theme:immersion_cooling_systems — pumped loops on chips vs dielectric baths
- exclusions: immersion systems, chiller plant, coolant chemistry manufacture
- china_relevance: high — 冷板式液冷 is the dominant Chinese AI-datacenter cooling vocabulary
- confidence: high
- sources: OCP liquid-cooling hardware specifications, Open Compute Project; "Thermal Guidelines for Data Processing Environments", ASHRAE TC 9.9

### immersion-cooling-systems
- id: theme:immersion_cooling_systems
- name_en: Immersion cooling systems
- name_zh: 浸没式液冷
- value_chain_position: midstream
- parent_sub_theme: theme:datacenter_cooling_chain
- defining_activities: engineering single/two-phase immersion tanks; server-board redesign for dielectric immersion; fluid management and filtration loops; tank-farm integration with facility heat rejection
- distinct_from: theme:cold_plate_liquid_cooling — bath immersion vs cold-plate loops; distinct_from theme:liquid_cooling_thermal — specific immersion technology vs the broad segment
- exclusions: cold plates, facility chillers
- china_relevance: medium — 浸没式 is piloted domestically at scale but trails cold-plate adoption
- confidence: high
- sources: OCP immersion-cooling specifications, Open Compute Project; "Thermal Guidelines for Data Processing Environments", ASHRAE TC 9.9

### precision-air-conditioning
- id: theme:precision_air_conditioning
- name_en: Precision air conditioning (CRAC/CRAH)
- name_zh: 机房精密空调
- value_chain_position: midstream
- parent_sub_theme: theme:datacenter_cooling_chain
- defining_activities: manufacturing computer-room air conditioners/handlers; airflow containment engineering (hot/cold aisle); humidity and filtration control for white space; indirect evaporative cooling unit development
- distinct_from: theme:liquid_cooling_thermal — air-side cooling vs liquid loop segment; distinct_from theme:thermal_rejection_heat_recovery — white-space units vs exterior heat-rejection plant
- exclusions: liquid loops, building comfort HVAC
- china_relevance: high — 精密空调 is a stable domestic datacenter equipment category
- confidence: high
- sources: "Thermal Guidelines for Data Processing Environments", ASHRAE TC 9.9; GB 40879-2021《数据中心能效限定值及能效等级》, 中国国家标准

### thermal-rejection-heat-recovery
- id: theme:thermal_rejection_heat_recovery
- name_en: Heat rejection & waste-heat recovery
- name_zh: 冷却塔/干冷器与余热回收
- value_chain_position: midstream
- parent_sub_theme: theme:datacenter_cooling_chain
- defining_activities: engineering cooling towers and dry coolers; free-cooling economizer design; heat-pump boosters exporting waste heat to district networks; water-usage effectiveness optimization
- distinct_from: theme:precision_air_conditioning — exterior heat rejection vs white-space units; distinct_from theme:liquid_cooling_thermal — facility heat export vs IT-space thermal segment
- exclusions: chiller manufacture as standalone, immersion tanks
- china_relevance: medium — 余热回收 is a growing regulatory-adjacent topic in Chinese green-datacenter policy
- confidence: medium
- sources: ISO/IEC 30134 series (data centre KPIs incl. ERF), ISO/IEC; "Thermal Guidelines for Data Processing Environments", ASHRAE TC 9.9

### immersion-thermal-fluids
- id: theme:immersion_thermal_fluids
- name_en: Dielectric fluids & thermal interface materials
- name_zh: 液冷工质与热界面材料
- value_chain_position: upstream
- parent_sub_theme: theme:datacenter_cooling_chain
- defining_activities: formulating synthetic/dielectric immersion fluids; producing thermal greases, pads and phase-change TIMs; chemistry compatibility qualification with server hardware; fluid lifecycle and reclamation services
- distinct_from: theme:immersion_cooling_systems — the working fluid/TIM consumable vs the tank system; distinct_from theme:photoresist_semiconductor_materials — datacenter chemistry vs fab chemistry
- exclusions: CDU/cold-plate hardware, water treatment chemicals for towers
- china_relevance: medium — 液冷工质 domestication tracks the domestic cold-plate/immersion ramp
- confidence: medium
- sources: OCP liquid-cooling specifications (fluid requirements), Open Compute Project; "Thermal Guidelines for Data Processing Environments", ASHRAE TC 9.9

### dc-hvdc-power-architecture
- id: theme:dc_hvdc_power_architecture
- name_en: DC power architecture (240/336V HVDC)
- name_zh: 高压直流供电架构（含巴拿马电源）
- value_chain_position: midstream
- parent_sub_theme: theme:datacenter_power_chain
- defining_activities: engineering 240V/336V DC bus architectures; integrated power-supply units that merge transformer/rectifier stages; rectifier and DC-DC converter platform development; DC distribution protection coordination
- distinct_from: theme:ups_power_conversion — DC bus architecture replacing/integrating the UPS stage vs the UPS product row; distinct_from theme:busway_smart_pdu — source-side architecture vs rack-level distribution hardware
- exclusions: AC UPS products, utility-scale HVDC transmission (grid theme)
- china_relevance: high — 高压直流/巴拿马电源 is a distinctly Chinese datacenter power-train vocabulary with domestic champions
- confidence: high
- sources: ODCC (开放数据中心委员会) datacenter power白皮书 series; OCP power hardware specifications, Open Compute Project

### backup-generator-sets
- id: theme:backup_generator_sets
- name_en: Backup generator sets (diesel/gas)
- name_zh: 备用发电机组（柴油/燃气）
- value_chain_position: midstream
- parent_sub_theme: theme:datacenter_power_chain
- defining_activities: manufacturing standby gensets sized for campus loads; paralleling switchgear and black-start control integration; emissions after-treatment and fuel-storage engineering; long-duration outage testing services
- distinct_from: theme:ups_power_conversion — minutes-scale electromechanical standby vs electronic ride-through conversion; distinct_from theme:behind_meter_generation — emergency standby vs continuous on-site generation
- exclusions: prime-power gas turbines, UPS products
- china_relevance: high — 柴油发电机备电 is the universal Chinese datacenter resiliency requirement
- confidence: high
- sources: Uptime Institute Tier Standard: Topology (backup power requirements); GB/T standards for diesel generating sets, 中国国家标准

### dc-battery-backup
- id: theme:dc_battery_backup
- name_en: Battery backup & BBU systems
- name_zh: 数据中心备电电池（UPS电池/BBU）
- value_chain_position: midstream
- parent_sub_theme: theme:datacenter_power_chain
- defining_activities: supplying VRLA/lithium strings for UPS plants; rack-level battery backup unit (BBU) integration in server shelves; battery monitoring and fire-safety engineering; lithium retirement/replacement services
- distinct_from: theme:ups_power_conversion — energy storage element vs the conversion electronics; distinct_from theme:grid_storage_integration (grid) — facility ride-through batteries vs grid-side energy arbitrage plants
- exclusions: UPS inverters, generator sets, grid-scale BESS
- china_relevance: high — 锂电备电 substitution is an active domestic datacenter build standard
- confidence: high
- sources: Uptime Institute Tier Standard: Topology; ODCC (开放数据中心委员会) datacenter facility白皮书 series

### busway-smart-pdu
- id: theme:busway_smart_pdu
- name_en: Busway & intelligent PDU distribution
- name_zh: 母线槽与智能PDU配电
- value_chain_position: midstream
- parent_sub_theme: theme:datacenter_power_chain
- defining_activities: manufacturing overhead busway trunk systems; intelligent rack PDU metering/switching; branch-circuit monitoring at rack level; tap-off box and busway installation services
- distinct_from: theme:hv_transformers_switchgear — in-building rack-level distribution vs utility-class transformers/switchgear; distinct_from theme:dc_hvdc_power_architecture — delivery hardware vs source architecture
- exclusions: medium-voltage switchgear, UPS products
- china_relevance: high — 母线槽/智能PDU is standard Chinese modular-datacenter fitout vocabulary
- confidence: high
- sources: ODCC (开放数据中心委员会) datacenter facility白皮书 series; Uptime Institute Tier Standard: Topology

### server-power-supplies
- id: theme:server_power_supplies
- name_en: Server PSU & power modules
- name_zh: 服务器电源与电源模组
- value_chain_position: midstream
- parent_sub_theme: theme:datacenter_power_chain
- defining_activities: designing rack-server power supply units; efficiency-stage development (titanium-class conversion); power-shelf and busbar architectures for open racks; hot-swap redundancy qualification
- distinct_from: theme:ups_power_conversion — rack-level conversion vs facility UPS; distinct_from theme:dc_hvdc_power_architecture — PSU product family vs the DC bus design that feeds it
- exclusions: facility UPS, generator sets
- china_relevance: high — 服务器电源/电源模组 is a fast-growing domestic category riding AI rack builds
- confidence: high
- sources: OCP Open Rack power specifications, Open Compute Project; ODCC (开放数据中心委员会) server白皮书 series

### behind-meter-generation
- id: theme:behind_meter_generation
- name_en: Behind-the-meter generation & power procurement
- name_zh: 数据中心自备电源与绿电直供
- value_chain_position: downstream
- parent_sub_theme: theme:datacenter_site_energy
- defining_activities: contracting long-term power purchase agreements; siting on-site generation (gas engines, fuel cells, SMR-PPA structures); microgrid control of campus generation; renewable-certificate and 24/7 clean-energy matching
- distinct_from: theme:backup_generator_sets — continuous/economic generation vs emergency standby; distinct_from theme:grid_interconnection_services — self-supply vs utility interconnection engineering
- exclusions: utility power-plant development, generator-set manufacture
- china_relevance: high — 绿电直供/源网荷储 is the active Chinese policy vocabulary for datacenter energy procurement
- confidence: medium
- sources: "Data Centres and Data Transmission Networks", IEA; ODCC (开放数据中心委员会) datacenter energy白皮书 series

### grid-interconnection-services
- id: theme:grid_interconnection_services
- name_en: Grid interconnection & substation buildout
- name_zh: 数据中心电力接入工程
- value_chain_position: downstream
- parent_sub_theme: theme:datacenter_site_energy
- defining_activities: securing utility interconnection queues and agreements; building dedicated substations and incoming lines; protective-relay coordination with utilities; dual-feed redundancy engineering
- distinct_from: theme:hv_transformers_switchgear — the interconnection ENGINEERING service vs equipment manufacture; distinct_from theme:transmission_substation_epc (grid) — campus-dedicated access vs public transmission-network EPC
- exclusions: transmission network construction, equipment manufacture
- china_relevance: high — 电力接入/变电站配套 is a named bottleneck in Chinese AI-datacenter siting coverage
- confidence: high
- sources: "Electricity Grids and Secure Energy Transitions", IEA; IEEE Std 1547 interconnection framework, IEEE

### prefab-modular-datacenter
- id: theme:prefab_modular_datacenter
- name_en: Prefabricated modular data centers
- name_zh: 预制模块化数据中心
- value_chain_position: downstream
- parent_sub_theme: theme:datacenter_site_energy
- defining_activities: factory-building power/cooling skids and containers; integrating IT, electrical and mechanical modules for site stacking; rapid-deployment commissioning; standardized repeatable campus products
- distinct_from: theme:fab_facility_systems (semicap) — datacenter modules vs fab cleanrooms; distinct_from theme:grid_interconnection_services — productized facility integration vs utility access engineering
- exclusions: IT hardware manufacture, site civil works
- china_relevance: high — 预制舱式/模块化机房 is standard Chinese operator deployment vocabulary
- confidence: high
- sources: ODCC (开放数据中心委员会) modular datacenter白皮书 series; Uptime Institute Tier Standard: Topology

### dcim-energy-management
- id: theme:dcim_energy_management
- name_en: DCIM & energy/carbon management software
- name_zh: 数据中心基础设施管理（DCIM）与能碳软件
- value_chain_position: enabler
- parent_sub_theme: theme:datacenter_site_energy
- defining_activities: deploying data-center infrastructure management platforms; real-time PUE/WUE instrumentation and telemetry; capacity planning and digital-twin modeling; energy-carbon reporting to regulators
- distinct_from: theme:fab_automation_cim (semicap) — facility energy software vs manufacturing execution; distinct_from theme:grid_dispatch_ems_software (grid) — campus energy management vs grid dispatch
- exclusions: IT workload orchestration, facility hardware
- china_relevance: high — 能碳管理/PUE监管 reporting is mandated in Chinese datacenter policy
- confidence: high
- sources: ISO/IEC 30134-2 (PUE), ISO/IEC; GB 40879-2021《数据中心能效限定值及能效等级》, 中国国家标准
## theme:nuclear_power — Nuclear & SMR Power（核能与小型堆）

Scope: the civil nuclear value chain beyond the three existing coarse rows — plant systems and materials, the build/operate/back-end chain, and next-generation systems and applications. Existing rows (`theme:reactor_technology`, `theme:nuclear_components`, `theme:fuel_cycle`) stay and are deliberately NOT re-split: this record respects the prior C1 adjudications that rejected subset rows under them (no SMR row under reactor_technology; no uranium-stage rows under fuel_cycle). The back-end (spent fuel, decommissioning) and non-coarse layers below are genuinely uncovered and are therefore proposed.

Sub-theme grouping: three new sub_themes. `theme:nuclear_plant_systems`（核电站系统与设备）groups the plant-system positions (conventional island, nuclear-grade digital I&C, nuclear-grade materials & forgings). `theme:nuclear_build_operate`（核电建设与运营）groups the project and asset chain (construction EPC, plant operations, spent-fuel management, decommissioning). `theme:next_gen_nuclear`（下一代核能与核能应用）groups the frontier and application positions (Gen-IV systems, non-electric heat/hydrogen, floating platforms, fusion supply chain).

Theme-tier candidates (prose only): fusion could one day warrant its own top-level theme if the technology reaches commercial commitment; today it stays a micro here because its near-term equity exposure is a component supply chain, not an operating industry.

### conventional-island-equipment
- id: theme:conventional_island_equipment
- name_en: Conventional island equipment (turbine island)
- name_zh: 常规岛设备（汽轮发电机组）
- value_chain_position: midstream
- parent_sub_theme: theme:nuclear_plant_systems
- defining_activities: manufacturing steam turbines and generators for NPP thermal cycles; condensers, heaters and moisture-separator-reheaters; turbine-island piping and balance-of-plant integration; retrofit/uprate programs on operating units
- distinct_from: theme:nuclear_components — the existing row is the nuclear-island-side component supply chain; this row is the conventional (thermal-to-electric) island train; distinct_from theme:reactor_technology — plant equipment vs reactor system design
- exclusions: reactor coolant system components (nuclear_components row), EPC construction
- china_relevance: high — 核岛/常规岛 is the standard Chinese nuclear-equipment disclosure split
- confidence: high
- sources: IAEA Nuclear Energy Series (NPP equipment guidance), IAEA; IAEA PRIS plant-system reference data, IAEA

### nuclear-digital-ic
- id: theme:nuclear_digital_ic
- name_en: Nuclear-grade digital I&C
- name_zh: 核级数字化仪控系统
- value_chain_position: enabler
- parent_sub_theme: theme:nuclear_plant_systems
- defining_activities: building reactor protection and safety I&C platforms (DCS class); radiation-hardened/qualified instrumentation supply; full-scope simulator and control-room integration; cybersecurity hardening of safety systems
- distinct_from: theme:nuclear_components — qualified instrumentation & control SYSTEMS vs mechanical components; distinct_from theme:fab_automation_cim (semicap) — safety-class control vs manufacturing execution
- exclusions: conventional island electrical balance-of-plant, plant IT networks
- china_relevance: high — 核级DCS/仪控自主化 is a named domesticization program in Chinese nuclear coverage
- confidence: high
- sources: HAF102《核动力厂设计安全规定》, 国家核安全局 (NNSA); IAEA Nuclear Energy Series (I&C for NPPs), IAEA

### nuclear-grade-forgings-materials
- id: theme:nuclear_grade_forgings_materials
- name_en: Nuclear-grade materials & heavy forgings
- name_zh: 核级材料与大型锻件
- value_chain_position: upstream
- parent_sub_theme: theme:nuclear_plant_systems
- defining_activities: forging reactor pressure vessels, steam generators and pressurizer shells; producing zirconium-alloy cladding tube stock; nuclear-grade welding consumables and specialty steels; code-stamped (ASME/RCC-M class) material qualification
- distinct_from: theme:nuclear_components — supplies qualified RAW material/forgings into component fabrication vs fabricating components; distinct_from theme:conventional_island_equipment — materials vs turbine machinery
- exclusions: finished component manufacture, fuel assembly assembly work
- china_relevance: high — 大型锻件/锆材自主化 is a recurring bottleneck topic in Chinese nuclear coverage
- confidence: high
- sources: 《中国核能发展报告》蓝皮书, 中国核能行业协会; IAEA Nuclear Energy Series (materials), IAEA

### npp-construction-epc
- id: theme:npp_construction_epc
- name_en: Nuclear plant construction & installation (EPC)
- name_zh: 核电工程建设与安装（EPC）
- value_chain_position: midstream
- parent_sub_theme: theme:nuclear_build_operate
- defining_activities: executing nuclear-island civil works and containment construction; heavy-lift module installation and large-equipment placement; construction QA/QC under nuclear codes; schedule management of multi-unit programs
- distinct_from: theme:nuclear_components — construction services vs component supply; distinct_from theme:transmission_substation_epc (grid) — plant-scope EPC vs grid-line EPC
- exclusions: plant operation, equipment manufacture
- china_relevance: high — 核电工程EPC is a large disclosed domestic segment with continuous new-unit starts
- confidence: high
- sources: IAEA PRIS construction-status data, IAEA; 《中国核能发展报告》蓝皮书, 中国核能行业协会

### npp-operations
- id: theme:npp_operations
- name_en: Plant operations & license management
- name_zh: 核电站运营
- value_chain_position: downstream
- parent_sub_theme: theme:nuclear_build_operate
- defining_activities: operating reactor units and managing refueling outages; capacity-factor and fleet-reliability programs; license renewal and regulatory reporting; wholesale electricity sales from NPP fleets
- distinct_from: theme:reactor_technology — operates licensed plants vs designs reactor systems; distinct_from theme:npp_construction_epc — asset operation vs construction delivery
- exclusions: fuel fabrication, plant construction
- china_relevance: high — 核电运营 is the core Chinese nuclear equity segment vocabulary
- confidence: high
- sources: IAEA PRIS operational metrics (capacity factor, outage data), IAEA; World Nuclear Performance Report, World Nuclear Association

### spent-fuel-management
- id: theme:spent_fuel_management
- name_en: Spent-fuel storage, transport & reprocessing
- name_zh: 乏燃料贮运与后处理
- value_chain_position: downstream
- parent_sub_theme: theme:nuclear_build_operate
- defining_activities: building at-reactor and away-from-reactor spent-fuel storage; licensed spent-fuel cask transport logistics; reprocessing and MOX-refabrication plant operations; interim repository development
- distinct_from: theme:fuel_cycle — the existing row covers the FRONT end (mining through enrichment per its source slice); this row is the BACK end, which it does not cover
- exclusions: uranium mining/enrichment (front-end, existing row), decommissioning
- china_relevance: high — 乏燃料后处理/贮运 is a funded national program area in Chinese nuclear planning
- confidence: high
- sources: IAEA Joint Convention on the Safety of Spent Fuel Management, IAEA; 《中国核能发展报告》蓝皮书, 中国核能行业协会

### reactor-decommissioning
- id: theme:reactor_decommissioning
- name_en: Reactor & site decommissioning
- name_zh: 核设施退役
- value_chain_position: downstream
- parent_sub_theme: theme:nuclear_build_operate
- defining_activities: characterizing and decontaminating shutdown plants; remote segmentation and dismantling of activated structures; radioactive-waste packaging and disposal routing; site license termination and reuse
- distinct_from: theme:spent_fuel_management — plant dismantling vs fuel-cycle material management; distinct_from theme:npp_operations — end-of-life work vs operating assets
- exclusions: operating-plant services, waste storage facilities (in spent-fuel row)
- china_relevance: medium — early-stage domestically; China's first wave of retirements is still ahead of developed markets'
- confidence: medium
- sources: IAEA Decommissioning standards & ARTEMIS review framework, IAEA; OECD NEA decommissioning cost reports, OECD NEA

### gen4-reactor-systems
- id: theme:gen4_reactor_systems
- name_en: Generation-IV reactor systems
- name_zh: 第四代核能系统（高温气冷堆/快堆/熔盐堆）
- value_chain_position: midstream
- parent_sub_theme: theme:next_gen_nuclear
- defining_activities: developing non-light-water systems (HTGR, sodium fast reactor, molten-salt classes); demonstrating high-temperature process-heat delivery; licensing advanced fuel forms for Gen-IV cores; building demonstration units
- distinct_from: theme:reactor_technology — the existing row is the REG-PACKET slice for reactor designers broadly (SMR/LWR programs included); this row isolates the NON-light-water GIF technology families, whose supply chains (helium turbomachinery, sodium loops, salt chemistry) differ in mechanism
- exclusions: light-water SMR designs (inside existing row), fusion (own row)
- china_relevance: high — 高温气冷堆/快堆 demonstration units are flagship Chinese nuclear programs
- confidence: medium
- sources: "Technology Roadmap Update for Generation IV Nuclear Energy Systems", Generation IV International Forum; OECD NEA Gen-IV system reports, OECD NEA

### nuclear-heat-hydrogen
- id: theme:nuclear_heat_hydrogen
- name_en: Non-electric nuclear applications (heat & hydrogen)
- name_zh: 核能供热与制氢（非电应用）
- value_chain_position: downstream
- parent_sub_theme: theme:next_gen_nuclear
- defining_activities: supplying district heating from reactor units; industrial steam delivery to chemical parks; high-temperature electrolysis and thermochemical hydrogen programs; seawater desalination co-generation
- distinct_from: theme:npp_operations — sells non-electric energy products vs electricity generation; distinct_from theme:gen4_reactor_systems — the application demand side vs reactor system development
- exclusions: grid electricity sales, reactor technology development
- china_relevance: high — 核能供暖 is already commercial-seasonal in Chinese coastal/northern programs
- confidence: medium
- sources: IAEA Non-electric Applications of Nuclear Energy series, IAEA; 《中国核能发展报告》蓝皮书, 中国核能行业协会

### floating-nuclear-platforms
- id: theme:floating_nuclear_platforms
- name_en: Floating & marine nuclear power platforms
- name_zh: 海上浮动核动力平台
- value_chain_position: midstream
- parent_sub_theme: theme:next_gen_nuclear
- defining_activities: building barge-mounted reactor platforms; marine-grade licensing and classing of floating NPPs; offshore heat/power delivery to shore or offshore assets; mobile-power deployment logistics
- distinct_from: theme:npp_construction_epc — builds a PRODUCT platform vs site-fixed civil works; distinct_from theme:naval_shipbuilding (defense) — civil power platforms vs naval combatants
- exclusions: land-based NPP construction, naval propulsion
- china_relevance: high — 海上浮动核动力平台 is an active Chinese program category with marine-industry crossover
- confidence: medium
- sources: IAEA technical documents on floating nuclear power plants, IAEA; World Nuclear Association information paper on floating NPPs, WNA

### fusion-supply-chain
- id: theme:fusion_supply_chain
- name_en: Fusion energy supply chain
- name_zh: 可控核聚变供应链（超导磁体/偏滤器）
- value_chain_position: upstream
- parent_sub_theme: theme:next_gen_nuclear
- defining_activities: manufacturing high-field superconducting magnets (HTS/LTS); fabricating vacuum vessels, divertors and first-wall components; tritium-breeding blanket and fueling technology development; fusion-grade power supplies and diagnostics
- distinct_from: theme:gen4_reactor_systems — fission Gen-IV systems vs fusion devices; distinct_from theme:nuclear_components — a pre-commercial fusion component base vs fission plant components
- exclusions: fission reactor programs, isotope production (not power)
- china_relevance: high — Chinese fusion-device programs and magnet/component suppliers are prominent in domestic coverage
- confidence: low
- sources: "European Research Roadmap to the Realisation of Fusion Energy", EUROfusion; IAEA fusion device information resources, IAEA
## theme:grid_electrification — Grid & Electrification（电网与电气化）

Scope: the bulk-power and end-use electrification value chain — transmission system classes beyond the existing equipment rows, the digital/flexibility layer, and end-use electrification positions. Existing rows (`theme:hv_transformers_switchgear`, `theme:grid_distribution_automation`, `theme:transmission_hvdc_cabling`) stay; every row below ADDS a mechanism they do not cover.

Sub-theme grouping: three new sub_themes. `theme:transmission_equipment`（输变电系统与设备）groups the bulk-power system positions (UHV programs, flexible-HVDC converter stations, protection & substation automation, FACTS, transmission EPC). `theme:grid_digital_flexibility`（电网数字化与灵活性）groups the flexibility/software chain (grid-side storage integration, virtual power plants, AMI/smart metering, dispatch software, microgrids, line monitoring, power-market operations). `theme:electrification_end_uses`（终端电气化）groups demand-side electrification (EV charging, rail traction, industrial electrification, building heat pumps).

Theme-tier candidates (prose only): none. Battery cell manufacturing is deliberately NOT a row here — it is a distinct value chain outside this group's themes; only the system-integration position is proposed.

### uhv-transmission
- id: theme:uhv_transmission
- name_en: UHV transmission programs & systems
- name_zh: 特高压输电工程与成套设备
- value_chain_position: midstream
- parent_sub_theme: theme:transmission_equipment
- defining_activities: engineering 1000kV AC / ±800kV-class DC corridors; supplying UHV substations and converter stations as integrated packages; corridor EPC and system commissioning; UHV-standard equipment certification
- distinct_from: theme:hv_transformers_switchgear — corridor SYSTEMS engineering vs the transformer/switchgear equipment class; distinct_from theme:transmission_hvdc_cabling — overhead UHV corridors vs HVDC cable links
- exclusions: distribution networks, individual equipment manufacture (existing rows)
- china_relevance: high — 特高压 is a signature Chinese grid-buildout category with its own standard system
- confidence: high
- sources: 《电力系统安全稳定导则》GB 38755-2019, 中国国家标准; "Electricity Grids and Secure Energy Transitions", IEA

### flexible-hvdc-converter-valves
- id: theme:flexible_hvdc_converter_valves
- name_en: Flexible HVDC & converter valves (VSC)
- name_zh: 柔性直流输电与换流阀
- value_chain_position: midstream
- parent_sub_theme: theme:transmission_equipment
- defining_activities: manufacturing voltage-source-converter valves (IGBT-class); modular multilevel converter engineering; multi-terminal DC grid control and protection; offshore-wind export and interconnector delivery
- distinct_from: theme:transmission_hvdc_cabling — converter-station power electronics vs the cable link itself; distinct_from theme:uhv_transmission — VSC technology class vs corridor programs (may co-exist on UHV-DC projects)
- exclusions: cable manufacture, substation automation
- china_relevance: high — 柔直/换流阀 is standard Chinese grid-equipment vocabulary for offshore and multi-terminal projects
- confidence: high
- sources: CIGRE Technical Brochures (SC B4 DC systems & power electronics), CIGRE; "Electricity Grids and Secure Energy Transitions", IEA

### grid-protection-substation-automation
- id: theme:grid_protection_substation_automation
- name_en: Protection, relays & substation automation
- name_zh: 继电保护与变电站自动化
- value_chain_position: midstream
- parent_sub_theme: theme:transmission_equipment
- defining_activities: manufacturing protective relays and bay controllers; IEC 61850 digital-substation engineering; disturbance recording and fault-locating systems; wide-area protection scheme deployment
- distinct_from: theme:hv_transformers_switchgear — protection/control intelligence vs primary switching apparatus; distinct_from theme:grid_distribution_automation — substation/protection layer vs feeder automation
- exclusions: switchgear hardware, distribution feeders (existing rows)
- china_relevance: high — 继电保护 is a distinct domestic equipment-software segment with stable disclosure vocabulary
- confidence: high
- sources: IEC 61850 substation communication standard, IEC; IEEE power system relaying standards, IEEE PES

### facts-reactive-compensation
- id: theme:facts_reactive_compensation
- name_en: FACTS & reactive power compensation
- name_zh: 柔性交流输电与无功补偿（SVG/STATCOM）
- value_chain_position: midstream
- parent_sub_theme: theme:transmission_equipment
- defining_activities: manufacturing static VAR generators/STATCOMs; series-compensation and SVC engineering; harmonic filtering and power-quality plants; dynamic reactive support for renewable-heavy grids
- distinct_from: theme:flexible_hvdc_converter_valves — AC-side compensation electronics vs DC conversion; distinct_from theme:hv_transformers_switchgear — power-electronic compensation vs primary equipment
- exclusions: HVDC valves, substation protection
- china_relevance: high — SVG/无功补偿 is required vocabulary in Chinese renewable-integration coverage
- confidence: high
- sources: CIGRE Technical Brochures (compensation & power quality), CIGRE; IEEE FACTS application guides, IEEE PES

### transmission-substation-epc
- id: theme:transmission_substation_epc
- name_en: Transmission & substation engineering (EPC/design)
- name_zh: 输变电工程建设（EPC/电力设计院）
- value_chain_position: downstream
- parent_sub_theme: theme:transmission_equipment
- defining_activities: designing transmission lines and substations (design-institute work); EPC execution of grid corridors; geotechnical/routing and permitting services; commissioning and handover to grid operators
- distinct_from: theme:uhv_transmission — general grid EPC across voltage classes vs the UHV program class; distinct_from theme:grid_interconnection_services (data_center_power) — public-network works vs campus-dedicated access
- exclusions: equipment manufacture, grid operation
- china_relevance: high — 电力设计院/输变电EPC is the classic Chinese grid construction segment
- confidence: high
- sources: "Electricity Grids and Secure Energy Transitions", IEA; 中国电力企业联合会 (CEC) annual power-supply reports

### grid-storage-integration
- id: theme:grid_storage_integration
- name_en: Grid-side storage integration
- name_zh: 储能系统集成（电网侧/独立储能电站）
- value_chain_position: downstream
- parent_sub_theme: theme:grid_digital_flexibility
- defining_activities: engineering standalone/grid-side battery storage plants; power-conversion system (PCS) and EMS integration; capacity-market and ancillary-service participation; storage-safety and augmentation services
- distinct_from: theme:dc_battery_backup (data_center_power) — grid asset participation vs facility ride-through; distinct_from theme:virtual_power_plants — utility-scale plant assets vs aggregated distributed load flexibility
- exclusions: battery cell/pack manufacture, datacenter backup batteries
- china_relevance: high — 电网侧/独立储能 is a major Chinese grid-investment category
- confidence: high
- sources: "Electricity Grids and Secure Energy Transitions", IEA; IEC 62933 electrical energy storage standards, IEC

### virtual-power-plants
- id: theme:virtual_power_plants
- name_en: Virtual power plants & load aggregation
- name_zh: 虚拟电厂与负荷聚合
- value_chain_position: downstream
- parent_sub_theme: theme:grid_digital_flexibility
- defining_activities: aggregating distributed flexible loads and DERs; demand-response dispatch against grid signals; VPP platform operation and settlement; flexibility-market program participation
- distinct_from: theme:grid_storage_integration — aggregated flexibility vs utility-scale storage assets; distinct_from theme:grid_dispatch_ems_software — market-facing aggregator services vs transmission dispatch software
- exclusions: utility dispatch centers, cell manufacturing
- china_relevance: high — 虚拟电厂 is now formal policy vocabulary in Chinese power-market reform documents
- confidence: high
- sources: "Electricity Grids and Secure Energy Transitions", IEA; 国家能源局 demand-response/virtual-pilot policy documents, 国家能源局 (NEA)

### ami-smart-metering
- id: theme:ami_smart_metering
- name_en: Smart metering & AMI systems
- name_zh: 智能电表与用电信息采集（AMI）
- value_chain_position: midstream
- parent_sub_theme: theme:grid_digital_flexibility
- defining_activities: manufacturing smart electricity meters; deploying head-end/data-collection systems; meter-data management and time-of-use settlement support; gas/water multi-utility metering adjacencies
- distinct_from: theme:grid_distribution_automation — the metering/data chain vs feeder automation equipment; distinct_from theme:grid_asset_monitoring — customer-end measurement vs network asset monitoring
- exclusions: distribution switchgear, dispatch software
- china_relevance: high — 用电信息采集/智能电表 is a mature Chinese grid-IT procurement category
- confidence: high
- sources: IEC 62056 (DLMS/COSEM) metering standard, IEC; 中国电力企业联合会 (CEC) annual power-supply reports

### grid-dispatch-ems-software
- id: theme:grid_dispatch_ems_software
- name_en: Grid dispatch & EMS software
- name_zh: 电网调度自动化系统（EMS）
- value_chain_position: enabler
- parent_sub_theme: theme:grid_digital_flexibility
- defining_activities: building energy management/SCADA platforms for grid control centers; state estimation and security-constrained dispatch; renewable forecasting integration; market-clearing and settlement software
- distinct_from: theme:grid_distribution_automation — the existing row was admitted precisely to fold in "grid software and distribution automation vendors" at the feeder level; this row isolates CONTROL-CENTER dispatch/EMS, a different mechanism (system-operation software vs feeder hardware/software); no vendor wording
- exclusions: feeder automation hardware, VPP aggregator services
- china_relevance: high — 调度自动化 is a core domestic grid-software segment
- confidence: medium
- sources: 《电力监控系统安全防护规定》, 国家发展改革委; IEEE PES EMS/SCADA application guides, IEEE PES

### microgrid-solutions
- id: theme:microgrid_solutions
- name_en: Microgrids & campus energy systems
- name_zh: 微电网与园区能源系统
- value_chain_position: downstream
- parent_sub_theme: theme:grid_digital_flexibility
- defining_activities: engineering industrial-park and island microgrids; PV+storage+load coordination control; grid-connected/islanded transition management; microgrid energy contracting (EMC models)
- distinct_from: theme:behind_meter_generation (data_center_power) — multi-asset microgrid systems vs generation procurement; distinct_from theme:grid_storage_integration — integrated campus systems vs standalone grid assets
- exclusions: utility distribution networks, cell manufacturing
- china_relevance: high — 微电网/源网荷储一体化 is standard Chinese park-energy policy vocabulary
- confidence: high
- sources: IEEE Std 1547 (DER interconnection), IEEE; 国家能源局 microgrid/park integrated-energy pilot documents, 国家能源局 (NEA)

### grid-asset-monitoring
- id: theme:grid_asset_monitoring
- name_en: Grid asset monitoring & intelligent inspection
- name_zh: 输电线路在线监测与智能巡检
- value_chain_position: downstream
- parent_sub_theme: theme:grid_digital_flexibility
- defining_activities: deploying line dynamic-rating and weather monitoring; drone/robotic corridor inspection services; transformer/partial-discharge condition monitoring; asset-health analytics for grid fleets
- distinct_from: theme:ami_smart_metering — network asset telemetry vs customer metering; distinct_from theme:transmission_substation_epc — O&M services vs construction delivery
- exclusions: protection relays, metering hardware
- china_relevance: high — 输电线路智能巡检 is a visible Chinese grid-O&M digitization segment
- confidence: medium
- sources: CIGRE Technical Brochures (asset management & condition monitoring), CIGRE; 中国电力企业联合会 (CEC) annual power-supply reports

### power-market-operations
- id: theme:power_market_operations
- name_en: Electricity market operations & trading
- name_zh: 电力现货市场与电力交易
- value_chain_position: enabler
- parent_sub_theme: theme:grid_digital_flexibility
- defining_activities: operating spot-market clearing platforms; retail/power-trading intermediation for industrial customers; ancillary-service market services; forecasting and settlement systems
- distinct_from: theme:grid_dispatch_ems_software — market institutions/trading vs control-center dispatch software; distinct_from theme:virtual_power_plants — market operation/intermediation vs asset aggregation
- exclusions: financial power futures exchanges, dispatch hardware
- china_relevance: high — 电力现货市场建设 is an active nationwide Chinese reform program
- confidence: medium
- sources: 国家能源局 power-market construction documents, 国家能源局 (NEA); IEA electricity-market reform reviews, IEA

### ev-charging-infrastructure
- id: theme:ev_charging_infrastructure
- name_en: EV charging infrastructure & charging services
- name_zh: 充电桩与充电运营
- value_chain_position: downstream
- parent_sub_theme: theme:electrification_end_uses
- defining_activities: manufacturing AC/DC charging equipment; charging-network operation and roaming platforms; fleet/destination depot buildouts; V2G and managed-charging pilots
- distinct_from: theme:grid_distribution_automation — charging loads/services vs feeder automation; distinct_from theme:rail_traction_electrification — road electrification vs railway traction power
- exclusions: EV manufacture, battery manufacturing
- china_relevance: high — 充电桩/充电运营 is a large, well-disclosed Chinese segment
- confidence: high
- sources: IEC 61851 conductive charging standard, IEC; GB/T 18487.1《电动汽车传导充电系统》, 中国国家标准

### rail-traction-electrification
- id: theme:rail_traction_electrification
- name_en: Railway electrification & traction power
- name_zh: 电气化铁路与牵引供电
- value_chain_position: downstream
- parent_sub_theme: theme:electrification_end_uses
- defining_activities: engineering catenary/contact systems; traction substations and return circuits; onboard/offboard power-electrics for rolling stock; electrification of mainline and urban transit
- distinct_from: theme:transmission_substation_epc — rail traction systems vs public grid EPC; distinct_from theme:ev_charging_infrastructure — rail vs road electrification
- exclusions: rolling-stock vehicle manufacture, grid transmission
- china_relevance: high — 电气化铁路/牵引供电 is a long-established Chinese rail-industry segment
- confidence: high
- sources: IEC 60850 railway fixed-installation supply standard, IEC; 中国电力企业联合会 (CEC) annual power-supply reports

### industrial-electrification
- id: theme:industrial_electrification
- name_en: Industrial electrification & electricity substitution
- name_zh: 工业电气化与电能替代（电锅炉/电窑炉）
- value_chain_position: downstream
- parent_sub_theme: theme:electrification_end_uses
- defining_activities: converting industrial process heat to electric (electric boilers, kilns, furnaces); mechanical-drive and heat-pump steam retrofits; industrial demand-side management programs; electrode/e-resistance equipment supply
- distinct_from: theme:building_electrification_heatpumps — industrial process heat vs buildings; distinct_from theme:microgrid_solutions — end-use conversion vs campus energy systems
- exclusions: grid infrastructure, residential heating
- china_relevance: high — 电能替代 is formal Chinese utility/policy vocabulary
- confidence: high
- sources: "Electricity Grids and Secure Energy Transitions", IEA; 国家能源局 electricity-substitution policy documents, 国家能源局 (NEA)

### building-electrification-heatpumps
- id: theme:building_electrification_heatpumps
- name_en: Building electrification & heat pumps
- name_zh: 建筑电气化与热泵
- value_chain_position: downstream
- parent_sub_theme: theme:electrification_end_uses
- defining_activities: manufacturing air/water/ground-source heat pumps; converting space/water heating from fossil to electric; building management integration and load flexibility; district-scale electric heating networks
- distinct_from: theme:industrial_electrification — buildings vs industrial process heat; distinct_from theme:precision_air_conditioning (data_center_power) — HVAC-for-comfort vs datacenter white-space cooling
- exclusions: gas networks, industrial kilns
- china_relevance: high — 清洁取暖/热泵 is an established Chinese energy-transition program area
- confidence: high
- sources: "Electricity Grids and Secure Energy Transitions", IEA; IEA heat-pump technology reports, IEA
## theme:solar — Solar（光伏）

Scope: the photovoltaic value chain from silicon feedstock through materials, cells/modules, power electronics, plant development and end-of-life. Existing rows (`theme:polysilicon_solar_feedstock`, `theme:pv_cell_module_manufacturing`, `theme:solar_inverters`, `theme:solar_trackers_bos`) stay; every row below ADDS a mechanism they do not cover.

Sub-theme grouping: two new sub_themes. `theme:pv_upstream_materials`（光伏上游辅材）groups the consumable-material positions (glass/encapsulants, metallization paste, quartz crucibles & diamond wire). `theme:pv_plant_development`（光伏电站开发与运营）groups the plant/asset chain (utility-scale IPP, distributed PV, BIPV, PV+storage, O&M, recycling, testing & certification, agrivoltaics/floating). Five technology rows (ingot/wafer slicing, advanced cell manufacturing, perovskite/tandem, PV manufacturing equipment, module-level power electronics) stay direct theme children as peers of the frozen `theme:pv_manufacturing_chain` rows.

Theme-tier candidates (prose only): none. Solar hydrogen and battery cells are distinct value chains outside this group; thermal CSP is dormant globally and is not proposed.

### silicon-ingot-wafer-slicing
- id: theme:silicon_ingot_wafer_slicing
- name_en: Ingot growth & wafer slicing
- name_zh: 光伏硅片（拉棒/切片）
- value_chain_position: upstream
- parent_sub_theme: none
- defining_activities: growing monocrystalline ingots (CZ); diamond-wire slicing into wafers; kerf recycling and wafer thinning programs; large-wafer format transitions (182/210-class)
- distinct_from: theme:polysilicon_solar_feedstock — converts feedstock INTO wafers vs producing the polysilicon itself; distinct_from theme:pv_cell_module_manufacturing — wafer input vs cell/module processing
- exclusions: polysilicon production, electronic-grade wafers (ai_semiconductors row)
- china_relevance: high — 拉棒/切片 is the standard Chinese solar upstream segment vocabulary
- confidence: high
- sources: "Trends in Photovoltaic Applications", IEA PVPS; "Photovoltaics Report", Fraunhofer ISE

### advanced-cell-manufacturing
- id: theme:advanced_cell_manufacturing
- name_en: Advanced cell manufacturing (TOPCon/HJT/BC)
- name_zh: 高效电池制造（TOPCon/HJT/BC）
- value_chain_position: midstream
- parent_sub_theme: none
- defining_activities: running selective-emitter/passivating-contact cell lines; platform transitions (TOPCon/HJT/back-contact classes); cell-efficiency process control and metrology; capacity upgrade economics
- distinct_from: theme:pv_cell_module_manufacturing — the existing row covers cell+module manufacturing broadly; this row isolates the CELL-TECHNOLOGY platform layer (efficiency transitions) rather than manufacturing volume; distinct_from theme:perovskite_tandem_pv — silicon platform families vs next-junction devices
- exclusions: module assembly, equipment manufacture
- china_relevance: high — 电池片技术路线 (TOPCon/HJT/XBC) is the central Chinese solar trade-press axis
- confidence: high
- sources: "Photovoltaics Report", Fraunhofer ISE; Best Research-Cell Efficiency Chart, NREL

### perovskite-tandem-pv
- id: theme:perovskite_tandem_pv
- name_en: Perovskite & tandem cells
- name_zh: 钙钛矿及叠层电池
- value_chain_position: midstream
- parent_sub_theme: none
- defining_activities: developing perovskite single-junction and silicon-tandem stacks; stability/encapsulation qualification (ISOS protocols); pilot-line coating and laser scribing processes; tandem-cell certification pathways
- distinct_from: theme:advanced_cell_manufacturing — next-junction device class vs incumbent silicon platforms; distinct_from theme:pv_cell_module_manufacturing — device development vs mainstream manufacturing
- exclusions: silicon cell lines, module assembly
- china_relevance: high — 钙钛矿 is a prominent Chinese industrialization direction with pilot capacity
- confidence: medium
- sources: Best Research-Cell Efficiency Chart, NREL; "Photovoltaics Report", Fraunhofer ISE

### pv-manufacturing-equipment
- id: theme:pv_manufacturing_equipment
- name_en: PV manufacturing equipment
- name_zh: 光伏制造设备
- value_chain_position: enabler
- parent_sub_theme: none
- defining_activities: building ingot growth and wafering tools; cell-process equipment (PECVD/diffusion/plating classes); module line equipment (stringers, laminators, testers); turnkey line integration services
- distinct_from: theme:adjacent_semiconductor_equipment (semicap) — PV-line-dedicated equipment vs multi-industry tool families; distinct_from theme:advanced_cell_manufacturing — sells the line vs operating it
- exclusions: wafer/cell production, polysilicon plant EPC
- china_relevance: high — 光伏设备 is a strong domestic equipment segment exporting globally
- confidence: high
- sources: "Trends in Photovoltaic Applications", IEA PVPS; 中国光伏行业协会 (CPIA)《中国光伏产业发展路线图》

### mlpe-power-electronics
- id: theme:mlpe_power_electronics
- name_en: Module-level power electronics (optimizers/microinverters)
- name_zh: 组件级电力电子（优化器/微逆）
- value_chain_position: midstream
- parent_sub_theme: none
- defining_activities: manufacturing module-level optimizers; building microinverters; rapid-shutdown and safety-standard compliance; module-embedded power-electronics partnerships
- distinct_from: theme:solar_inverters — the existing row covers string/central inverter architectures; this row is the MODULE-level device class with a different safety/market mechanism (rooftop segment, per-panel MPPT)
- exclusions: string/central inverters, storage PCS
- china_relevance: medium — 微逆/优化器 domestic adoption is rising from a lower base than string inverters
- confidence: high
- sources: IEC 61215 / IEC 61730 module qualification & safety framework, IEC; "Trends in Photovoltaic Applications", IEA PVPS

### pv-glass-encapsulants
- id: theme:pv_glass_encapsulants
- name_en: PV glass & encapsulant films
- name_zh: 光伏玻璃与封装胶膜
- value_chain_position: upstream
- parent_sub_theme: theme:pv_upstream_materials
- defining_activities: melting ultra-clear patterned/rolled PV glass; producing EVA/POE encapsulant films; backsheet and edge-seal materials; anti-reflective/durable glass coating lines
- distinct_from: theme:polysilicon_solar_feedstock — glass/film materials vs silicon feedstock; distinct_from theme:pv_cell_module_manufacturing — module materials vs module assembly
- exclusions: float architectural glass, wafer-level materials
- china_relevance: high — 光伏玻璃/胶膜 is a concentrated Chinese upstream segment with distinct capacity cycles
- confidence: high
- sources: IEC 61215 module qualification (materials context), IEC; 中国光伏行业协会 (CPIA) annual development reports

### pv-silver-paste
- id: theme:pv_silver_paste
- name_en: Solar metallization paste & materials
- name_zh: 光伏银浆与金属化材料
- value_chain_position: upstream
- parent_sub_theme: theme:pv_upstream_materials
- defining_activities: formulating front/back silver pastes per cell platform; silver-reduction and copper-plating transition programs; firing-profile co-optimization with cell makers; paste yield and contact-resistance control
- distinct_from: theme:pv_cell_module_manufacturing — cell consumable vs cell production; distinct_from theme:cmp_polishing_consumables (ai_semiconductors) — PV metallization chemistry vs CMP slurries
- exclusions: silver refining, module assembly
- china_relevance: high — 光伏银浆国产化 is a tracked import-substitution topic in Chinese solar coverage
- confidence: high
- sources: 中国光伏行业协会 (CPIA)《中国光伏产业发展路线图》; "Photovoltaics Report", Fraunhofer ISE

### quartz-crucibles-diamond-wire
- id: theme:quartz_crucibles_diamond_wire
- name_en: Quartz crucibles & wafering consumables
- name_zh: 石英坩埚与金刚线耗材
- value_chain_position: upstream
- parent_sub_theme: theme:pv_upstream_materials
- defining_activities: pulling fused-silica crucibles for CZ growth; producing diamond wire and guide wheels; slurry-free slicing consumable systems; crucible lifetime and contamination control
- distinct_from: theme:silicon_ingot_wafer_slicing — the consumable chain vs ingot/wafer production itself; distinct_from theme:large_diameter_silicon_wafers (ai_semiconductors) — PV-grade consumables vs electronic wafers
- exclusions: ingot growth, silicon purification
- china_relevance: high — 石英坩埚/金刚线 are established Chinese consumable categories with domestic champions
- confidence: high
- sources: "Photovoltaics Report", Fraunhofer ISE; 中国光伏行业协会 (CPIA) annual development reports

### utility-scale-pv-ipp
- id: theme:utility_scale_pv_ipp
- name_en: Utility-scale PV development & IPP
- name_zh: 集中式光伏电站开发与运营（IPP）
- value_chain_position: downstream
- parent_sub_theme: theme:pv_plant_development
- defining_activities: developing ground-mount utility projects; owning/operating generation fleets (IPP model); power-purchase and grid-parity contracting; project-finance structuring and asset rotation
- distinct_from: theme:distributed_pv_commercial_residential — utility ground-mount assets vs rooftop/C&I segments; distinct_from theme:pv_plant_om — asset ownership vs contracted O&M services
- exclusions: module manufacturing, distribution-network assets
- china_relevance: high — 集中式电站/运营商标杆 is core Chinese solar downstream vocabulary
- confidence: high
- sources: "Trends in Photovoltaic Applications", IEA PVPS; IRENA "Renewable Capacity Statistics"

### distributed-pv-commercial-residential
- id: theme:distributed_pv_commercial_residential
- name_en: Distributed PV (C&I and residential)
- name_zh: 分布式光伏（工商业与户用）
- value_chain_position: downstream
- parent_sub_theme: theme:pv_plant_development
- defining_activities: rooftop/C&I project origination and EPC; residential channel programs and financing models; self-consumption and net-metering settlement; rural household distribution networks
- distinct_from: theme:utility_scale_pv_ipp — distributed rooftop segments vs utility fleets; distinct_from theme:bipv_building_integration — mounted rooftop systems vs envelope-integrated products
- exclusions: utility ground-mount, module manufacturing
- china_relevance: high — 户用/工商业分布式 is the fastest-cycled Chinese solar downstream segment
- confidence: high
- sources: "Trends in Photovoltaic Applications", IEA PVPS; 中国光伏行业协会 (CPIA) annual development reports

### bipv-building-integration
- id: theme:bipv_building_integration
- name_en: Building-integrated PV (BIPV)
- name_zh: 光伏建筑一体化（BIPV）
- value_chain_position: downstream
- parent_sub_theme: theme:pv_plant_development
- defining_activities: producing PV façade/roofing products; structural and fire-code qualification for envelope integration; design-in with architectural programs; curtain-wall and skylight system delivery
- distinct_from: theme:distributed_pv_commercial_residential — envelope-integrated construction products vs mounted rooftop installations; distinct_from theme:pv_glass_encapsulants — finished building products vs material supply
- exclusions: conventional rooftop racking, façade glass without PV function
- china_relevance: medium — BIPV policy pull exists (整县推进 adjacency) but scale trails mounted distributed
- confidence: high
- sources: IEC 63092 BIPV standards activity, IEC; 中国光伏行业协会 (CPIA) annual development reports

### solar-storage-integration
- id: theme:solar_storage_integration
- name_en: PV-plus-storage systems
- name_zh: 光储一体化系统
- value_chain_position: downstream
- parent_sub_theme: theme:pv_plant_development
- defining_activities: engineering DC-coupled solar+storage plants; hybrid inverter/PCS coordination; firm-shaping power sales contracts; storage augmentation planning alongside PV fleets
- distinct_from: theme:grid_storage_integration (grid) — plant-level hybrid systems vs standalone grid-side storage assets; distinct_from theme:utility_scale_pv_ipp — hybrid asset class vs pure PV generation
- exclusions: standalone BESS, cell manufacturing
- china_relevance: high — 光储一体化/配储 is a structural requirement in Chinese renewable procurement
- confidence: high
- sources: "Trends in Photovoltaic Applications", IEA PVPS; IEC 62933 electrical energy storage standards, IEC

### pv-plant-om
- id: theme:pv_plant_om
- name_en: PV plant O&M & asset management
- name_zh: 光伏电站运维与资产管理
- value_chain_position: downstream
- parent_sub_theme: theme:pv_plant_development
- defining_activities: contracted O&M across PV fleets; drone/robot soiling and hot-spot inspection; generation-yield analytics and repowering; asset-management and performance-guarantee services
- distinct_from: theme:utility_scale_pv_ipp — third-party O&M services vs asset ownership; distinct_from theme:grid_asset_monitoring (grid) — plant-scope services vs network-asset monitoring
- exclusions: EPC construction, asset ownership
- china_relevance: high — 电站运维 is a growing Chinese solar services segment as fleets age
- confidence: high
- sources: IEA PVPS Task 13 performance/reliability reports, IEA PVPS; IEC 62446 PV system documentation/commissioning standard, IEC

### pv-recycling-circularity
- id: theme:pv_recycling_circularity
- name_en: Module recycling & circularity
- name_zh: 光伏组件回收与循环利用
- value_chain_position: downstream
- parent_sub_theme: theme:pv_plant_development
- defining_activities: delamination and material separation from retired modules; silver/silicon/glass recovery processes; reverse-logistics and compliance under WEEE-class rules; recycled-material resale into supply chains
- distinct_from: theme:pv_plant_om — end-of-life processing vs operating-phase services; distinct_from theme:pv_glass_encapsulants — recovery vs primary material production
- exclusions: module manufacturing, plant O&M
- china_relevance: medium — 退役组件回收 is emerging Chinese policy territory as first-generation fleets age
- confidence: medium
- sources: IEA PVPS Task 12 end-of-life management reports, IEA PVPS; IRENA/IEA-PVPS "End-of-Life Management: Solar PV Panels"

### pv-testing-certification
- id: theme:pv_testing_certification
- name_en: PV testing & certification services
- name_zh: 光伏检测认证服务
- value_chain_position: enabler
- parent_sub_theme: theme:pv_plant_development
- defining_activities: IEC 61215/61730 type-testing laboratories; bankability and yield-estimation reports; factory inspections and certification issuance; field performance testing services
- distinct_from: theme:pv_plant_om — certification/bankability services vs contracted O&M; distinct_from theme:semiconductor_ate (semicap) — module/product certification vs chip ATE
- exclusions: plant O&M, equipment manufacture
- china_relevance: medium — domestic labs participate in the global certification chain for Chinese exports
- confidence: high
- sources: IEC 61215 / IEC 61730 standards, IEC; IEA PVPS Task 13 quality documentation, IEA PVPS

### agrivoltaics-floating-pv
- id: theme:agrivoltaics_floating_pv
- name_en: Agrivoltaics & floating PV
- name_zh: 农光/渔光互补与水面光伏
- value_chain_position: downstream
- parent_sub_theme: theme:pv_plant_development
- defining_activities: developing agricultural co-location projects (crop+PV); building reservoir/lake floating arrays; dual-use land/lease structuring; aquaculture-PV integrated operations
- distinct_from: theme:utility_scale_pv_ipp — dual-use siting formats vs conventional ground-mount; distinct_from theme:distributed_pv_commercial_residential — utility-adjacent water/agri formats vs rooftop
- exclusions: conventional ground-mount, offshore wind
- china_relevance: high — 农光互补/渔光互补 is native Chinese solar deployment vocabulary with large domestic fleets
- confidence: high
- sources: "Guideline for Agriphotovoltaics", Fraunhofer ISE; "Trends in Photovoltaic Applications", IEA PVPS
