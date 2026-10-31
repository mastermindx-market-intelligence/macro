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
- sources: IEEE International Roadmap for Devices and Systems (IRDS), IEEE; 《国家集成电路产业发展推进纲要》, 国务院 (2014); "Strengthening the Global Semiconductor Supply Chain", SIA/BCG; IEEE IRDS, "Design" chapter; SIA, "State of the U.S. Semiconductor Industry" (annual); 赛迪顾问（CCID）, 中国EDA产业白皮书系列

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
- sources: IRDS, IEEE; UCIe Specification, Universal Chiplet Interconnect Express Consortium; 中国半导体行业协会年度运行报告 (CSIA annual industry report); IEEE IRDS, "Design" and "Beyond CMOS" chapters; BCG × SIA, "Strengthening the Global Semiconductor Supply Chain in an Uncertain Era" (2021); 赛迪顾问（CCID）集成电路IP专题报告

### chiplet-partition-design
- id: theme:chiplet_partition_design
- name_en: Chiplet architecture & die-to-die design
- name_zh: 芯粒（Chiplet）架构设计
- value_chain_position: upstream
- parent_sub_theme: theme:ai_semiconductor_design_chain
- defining_activities: partitioning monolithic SoCs into multi-die architectures; implementing die-to-die link PHYs and packaging co-design; licensing chiplet interconnect IP; qualifying multi-source chiplet ecosystems; multi-source die sourcing across mixed process nodes and vendors integrated in one package; chiplet architecture and reference-flow licensing
- distinct_from: theme:ai_semiconductor_design_chain peers — designs the decomposition, not the tools or IP libraries; distinct_from theme:advanced_packaging_2_5d_3d — architecture and standards (UCIe-class) vs the manufacturing of the assembled package
- exclusions: actual assembly/bonding, HBM stacking
- china_relevance: high — 芯粒 is the named breakout path in Chinese trade press around advanced-node export limits
- confidence: medium
- sources: UCIe Specification, UCIe Consortium; IRDS, IEEE; UCIe Consortium, "Universal Chiplet Interconnect Express (UCIe) Specification" 1.0+; IEEE IRDS, "Heterogeneous Integration" chapter; Yole Group, advanced packaging report series

### advanced-node-foundry
- id: theme:advanced_node_foundry
- name_en: Advanced-node logic foundry
- name_zh: 先进制程晶圆代工
- value_chain_position: midstream
- parent_sub_theme: none
- defining_activities: operating leading-edge logic wafer fabs (≤7nm-class and below); running secure PDK-enabled foundry services; multi-project-wafer shuttles and design-tape-out intake; capacity allocation and yield learning on EUV-class flows; advanced-node yield-ramp and capacity-allocation management at wafer scale
- distinct_from: theme:gpu_merchant_accelerators / theme:custom_asic_silicon — manufactures for chip designers rather than designing; distinct_from theme:lithography_tools (semicap) — buys tools, does not build them; distinct_from theme:conventional_dram / memory fabs — logic process flows, not memory arrays
- exclusions: memory wafer fabrication (memory_storage row), OSAT services, equipment manufacture
- china_relevance: high — the central policy target of the Chinese fab-buildout; mature-node vs advanced-node split dominates Chinese disclosure vocabulary
- confidence: high
- sources: SEMI World Fab Forecast, SEMI; "Strengthening the Global Semiconductor Supply Chain", SIA/BCG; IRDS, IEEE; IEEE, "International Roadmap for Devices and Systems (IRDS)" (annual); SIA, "State of the U.S. Semiconductor Industry" (annual); BCG × SIA, "Strengthening the Global Semiconductor Supply Chain in an Uncertain Era" (2021)

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
- defining_activities: manufacturing ABF build-up package substrates; producing silicon interposers and RDL carriers; holding fine-line/fine-pitch lithography on organic substrates; capacity-qualifying new substrates for large-body AI packages; rigid/flex substrate families qualified to flip-chip and 2.5D assembly line rules; multi-year lead-time capacity expansion
- distinct_from: theme:advanced_packaging_2_5d_3d — makes the carrier the package is built on vs performing the assembly; distinct_from theme:hbm_packaging — substrate supply is upstream of all packaging
- exclusions: conventional leadframe/BT substrate commodity work, assembly services
- china_relevance: high — 载板 is a named domestic-gap category in Chinese electronics-materials planning
- confidence: medium
- sources: SEMI Advanced Packaging standards activity, SEMI; IRDS, IEEE; Yole Group, "Status of the Advanced Packaging Industry" (annual report series); 赛迪顾问（CCID Consulting）, 集成电路产业白皮书系列（封装基板章节）; IEEE IRDS, "Heterogeneous Integration" chapter

### co-packaged-optics-integration
- id: theme:co_packaged_optics_integration
- name_en: Co-packaged optics integration
- name_zh: 共封装光学（CPO）集成
- value_chain_position: midstream
- parent_sub_theme: theme:advanced_packaging_integration
- defining_activities: integrating optical engines beside switch/compute ASICs in one package; co-designing fiber attach and external laser sources; qualifying optical-electrical co-packaging reliability; shipping CPO-enabled switch systems; external laser source engineering at package level; SerDes-replacing optical link co-design into assembly flows
- distinct_from: theme:ai_interconnect_silicon — that row is the electrical switch/network silicon; this row integrates PHOTONIC engines into the same package; distinct_from theme:silicon_photonics_devices — device-level chips vs package-level integration
- exclusions: pluggable transceiver module assembly (no dedicated existing row; excluded here to stay mechanism-clean), plain switch ASIC design
- china_relevance: high — CPO/光电共封装 is a tracked direction in Chinese compute-interconnect planning
- confidence: medium
- sources: IEEE 802.3 Ethernet standards activity, IEEE; OCP networking hardware specifications, Open Compute Project; OIF, CPO-related implementation agreements and white papers; IEEE, optical interconnect sessions / "Journal of Lightwave Technology" industry surveys; Ethernet Alliance, "Ethernet Roadmap"

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
- distinct_from: theme:advanced_packaging_2_5d_3d — leading-edge interposer/hybrid-bond work vs the conventional high-volume assembly/test service layer; distinct_from theme:semiconductor_ate (semicap) — performs testing as a service vs selling testers; distinct_from theme:system_level_test_services — conventional assembly/final-test services vs system-level test specialty capacity
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
- defining_activities: writing e-beam mask patterns; pellicle mounting and defect inspection/repair; multi-layer EUV mask blank processing; NDA-guarded mask services tied to design tapes; merchant mask-blank manufacturing (quartz/EUV multilayer); reticle-set management across node ramps
- distinct_from: theme:lithography_tools (semicap) — makes the reticle the tool exposes through, not the exposure tool; distinct_from theme:photoresist_semiconductor_materials — durable imaging master vs consumable resist chemistry
- exclusions: mask-writing equipment, mask inspection tool manufacture
- china_relevance: high — 掩膜版 self-sufficiency is an explicit gap category in Chinese materials planning
- confidence: medium
- sources: IRDS, IEEE; SEMI mask/pellicle standards, SEMI; SEMI, photomask standards (P-series) program; SPIE, "Advanced Lithography + Patterning" proceedings (BACUS conference); 赛迪顾问（CCID）, 集成电路材料与部件专题

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
### theme:system_level_test_services
- id: `theme:system_level_test_services` · name_en: "System-level test (SLT) services" · name_zh: "系统级测试服务" · value_chain_position: midstream · parent_sub_theme: `theme:advanced_packaging_integration`
- defining_activities: executing post-assembly device test in system-like electrical/thermal conditions; running burn-in and stress screening on finished accelerators; providing contract test capacity with rapid fixture turnaround; feeding test data back into package and die yield models.
- distinct_from: `theme:process_metrology_inspection` (semicap, existing) — that is in-fab wafer process control; this is packaged-device functional test as a service. Distinct from `theme:semiconductor_ate`: testers for sale vs test capacity operated for hire; distinct from `theme:ai_chip_osat` — SLT system-like post-assembly test specialty vs conventional assembly/final-test services
- exclusions: wafer-sort-only test; ATE equipment manufacturing (semicap_equipment).
- china_relevance: medium — domestic OSAT expansion into SLT is an active trade-press theme; smaller than packaging itself.
- confidence: medium
- sources: IEEE, "International Test Conference (ITC)" proceedings; Semiconductor Engineering (trade press), test/system-level-test coverage; 中国半导体行业协会, 集成电路封测行业运行情况报告.

### theme:optical_transceiver_modules
- id: `theme:optical_transceiver_modules` · name_en: "Optical transceiver modules" · name_zh: "光模块" · value_chain_position: midstream · parent_sub_theme: `theme:ai_network_fabric`
- defining_activities: manufacturing pluggable optical transceivers (400G/800G/1.6T-class) for cluster networking; packaging lasers, photodetectors and DSPs into module form factors; qualifying optical/electrical interfaces to multi-source agreements; scaling module test capacity with AI cluster shipments.
- distinct_from: `theme:ai_interconnect_silicon` (existing) — electrical switch/SerDes silicon vs the photonic-electronic conversion module (TOSA/ROSA/DSP) at the link's ends; distinct from `theme:co_packaged_optics_integration` — front-panel pluggable modules vs photonics integrated into the switch package
- exclusions: switch ASICs (ai_interconnect_silicon); undersea/telecom long-haul systems without data-center demand linkage; bare optical components with no module integration.
- china_relevance: high — China is the dominant global manufacturing base for data-center optical modules (光模块), a standing 中国半导体行业协会/CCID trade line.
- confidence: high
- sources: Optical Internetworking Forum (OIF), implementation agreements for 800G-class links; Ethernet Alliance, "Ethernet Roadmap" (annual); 中国半导体行业协会光电组件分会（光模块行业报告系列）.

### theme:network_offload_processors
- id: `theme:network_offload_processors` · name_en: "Network offload processors (DPU/SmartNIC)" · name_zh: "智能网卡与 DPU" · value_chain_position: midstream · parent_sub_theme: `theme:ai_network_fabric`
- defining_activities: building programmable network interface processors that offload storage, security and virtualization from host CPUs; integrating Arm-class cores with network, crypto and RDMA accelerators; shipping DPUs as data-center infrastructure SKUs; programming offload pipelines for AI cluster fabrics.
- distinct_from: `theme:pcie_fabric_silicon` — fixed PCIe switch/retimer fabric vs programmable offload processors. Distinct from `theme:ai_interconnect_silicon` — host-side I/O endpoint vs switch fabric.
- exclusions: server CPUs; security appliances (cybersecurity theme); pure host-bus adapters without programmable offload.
- china_relevance: medium — domestic DPU programs are an active but early segment (trade press: DPU/智能网卡).
- confidence: medium
- sources: NVM Express, Inc., "NVMe over Fabrics" specification family; IEEE, DPU/SmartNIC survey literature and Hot Interconnects proceedings; Ethernet Alliance roadmap.

### theme:pcie_fabric_silicon
- id: `theme:pcie_fabric_silicon` · name_en: "PCIe switch & fabric silicon" · name_zh: "PCIe 交换与连接芯片" · value_chain_position: midstream · parent_sub_theme: `theme:ai_network_fabric`
- defining_activities: manufacturing PCIe packet switches that fan one host root port to many accelerators; building retimers and Redriver silicon for board-level signal integrity; implementing CXL-capable link silicon on PCIe PHYs; qualifying switch firmware/topology management.
- distinct_from: `theme:ai_interconnect_silicon` (existing) — cluster-scale Ethernet/InfiniBand network silicon vs intra-host PCIe/CXL fabric.
- exclusions: cluster network switch silicon; DPU offload processors (separate row); passive connectors.
- china_relevance: medium — PCIe switch is a named domestic-gap component in Chinese IC supply-chain reporting.
- confidence: medium
- sources: PCI-SIG, "PCI Express Base Specification" revisions; CXL Consortium, "Compute Express Link Specification"; IEEE IRDS, interconnect chapter.

### theme:edge_inference_processors
- id: `theme:edge_inference_processors` · name_en: "Edge inference processors (NPUs)" · name_zh: "端侧 AI 推理芯片" · value_chain_position: downstream · parent_sub_theme: none
- defining_activities: designing neural processing units for smartphones, PCs, vehicles and cameras; optimizing integer/low-precision inference at milliwatt-to-tens-of-watts budgets; integrating NPU IP with camera/display and connectivity subsystems; shipping device-side model-compiler toolchains.
- distinct_from: `theme:gpu_merchant_accelerators` — datacenter rack-scale accelerators vs device-scale inference silicon.
- exclusions: datacenter training/inference accelerators; general application processors without an NPU story; robotics perception (machine_vision under robotics_automation).
- china_relevance: high — 端侧AI芯片 is a flagship domestic design segment (AI phone/PC/vehicle silicon, trade press: 端侧算力).
- confidence: high
- sources: IEEE IRDS, "Mobile/edge" roadmap content; MLPerf (MLCommons), "MLPerf Inference: Edge" benchmark categories; 中国半导体行业协会, 集成电路设计行业运行情况.

### theme:ai_power_delivery_silicon
- id: `theme:ai_power_delivery_silicon` · name_en: "AI power-delivery silicon" · name_zh: "AI 供电电源芯片" · value_chain_position: enabler · parent_sub_theme: none
- defining_activities: building multiphase voltage regulators and vertical power stages feeding accelerator cores; integrating power-management ICs with telemetry for per-die power capping; developing on-package integrated voltage regulators for sub-volt rails; co-designing power stages for rising rack power density.
- distinct_from: `theme:ups_power_conversion` (data_center_power, existing) — facility-scale conversion/UPS vs package/board-level power silicon. Distinct from `theme:hv_transformers_switchgear` — grid/campus hardware vs chip-level converters.
- exclusions: facility UPS, busway, transformers (data_center_power); wide-bandgap module markets without AI-compute linkage.
- china_relevance: medium — 电源管理芯片国产化 is an active CCID/协会 theme, mid-scale.
- confidence: medium
- sources: IEEE, "Applied Power Electronics Conference (APEC)" proceedings; IEEE IRDS, power-delivery related chapters; 中国半导体行业协会, 电源管理芯片市场报告（协会/CCID 系列）.

### theme:ai_server_board_integration
- id: `theme:ai_server_board_integration` · name_en: "AI server board & system integration" · name_zh: "AI 服务器板卡与整机" · value_chain_position: downstream · parent_sub_theme: none
- defining_activities: designing accelerator carrier boards and baseboards to OCP-class specifications; integrating 4/8-GPU server SKUs with power, thermal and fabric topologies; manufacturing/assembly at scale for cloud and enterprise buyers; validating system firmware and rack-scale interop.
- distinct_from: `theme:gpu_merchant_accelerators` — the accelerator chip vs the boards/servers that host it. Distinct from the data_center_power rows (`theme:ups_power_conversion`, `theme:hv_transformers_switchgear`) — compute enclosure vs power infrastructure.
- exclusions: facility power/cooling (data_center_power); chip design (compute-silicon rows); hyperscale cloud services (out of taxonomy scope).
- china_relevance: high — China is a leading manufacturing base for AI servers (服务器板卡/整机, CCID/协会 standing line).
- confidence: high
- sources: Open Compute Project, "Open Rack" and server specification family; Uptime Institute, "Global Data Center Survey" (infrastructure context); 赛迪顾问（CCID）, 中国AI服务器市场报告系列.

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
- defining_activities: building RDIMM/DIMM memory modules; assembling SSD and memory-card products from wafers/packaged die; firmware flashing and burn-in at module level; channel-ready packaging and fulfillment; RDIMM/MRDIMM and SSD assembly from dies and controllers; channel inventory management across memory price cycles
- distinct_from: theme:nand_enterprise_storage — the existing row is the NAND & enterprise storage segment; this row is the module fabrication step for BOTH DRAM and NAND product; distinct_from theme:data_center_storage_systems — modules/components vs complete storage systems
- exclusions: controller chip design, wafer fabrication
- china_relevance: high — 存储模组 is a standard domestic segment with established disclosure vocabulary
- confidence: high
- sources: JEDEC module standards (RDIMM family), JEDEC; NVM Express Base Specification 2.0, NVM Express Inc; JEDEC, RDIMM/MRDIMM module standards (JESD family); TrendForce, module/DRAM module market research; 中国半导体行业协会存储行业报告

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
- sources: NVM Express Base Specification 2.0, NVM Express Inc.; JEDEC/SNIA solid state storage standards, SNIA; NVM Express, Inc., "NVM Express Base Specification"; SNIA, Solid State Storage Initiative technical work; 中国半导体行业协会/赛迪顾问, SSD主控芯片产业报告

### memory-interface-chips
- id: theme:memory_interface_chips
- name_en: Memory interface & companion chips
- name_zh: 内存接口与配套芯片
- value_chain_position: enabler
- parent_sub_theme: theme:memory_product_engineering
- defining_activities: designing registering clock drivers and data buffers for server memory; building companion power-management and temperature-sensor chips; JEDEC-spec conformance across DDR5 generations; co-qualification with module makers; CKD (clock driver) generations for high-speed DDR5; MRDIMM-sideband power/temperature companion chips
- distinct_from: theme:conventional_dram — interface silicon around DRAM vs the DRAM itself; distinct_from theme:enterprise_ssd_controllers — RDIMM-side interface vs SSD-side storage controllers
- exclusions: module manufacturing, DRAM fabrication
- china_relevance: high — 内存接口芯片 is an established A-share segment vocabulary with domestic champion dynamics
- confidence: high
- sources: JEDEC JESD79-5C DDR5 SDRAM Standard, JEDEC; JEDEC server-memory module standards, JEDEC; JEDEC, DDR5 RDIMM/MRDIMM module and companion-chip standards (JESD79-5 family and sideband function specs); 中国半导体行业协会, 内存接口芯片行业报告（协会/CCID 系列）

### embedded-storage-solutions
- id: theme:embedded_storage_solutions
- name_en: Embedded storage (eMMC/UFS)
- name_zh: 嵌入式存储（eMMC/UFS）
- value_chain_position: downstream
- parent_sub_theme: theme:memory_product_engineering
- defining_activities: packaging NAND+controller into eMMC/UFS embedded products; JEDEC embedded-standard qualification for mobile/automotive; long-term supply programs for device OEMs; auto-grade reliability screening; UFS revision performance-class qualification; soldered storage SKU supply to device OEMs
- distinct_from: theme:memory_module_manufacturing — socketed/card products vs soldered embedded standards; distinct_from theme:nand_enterprise_storage — mobile/embedded form factors vs enterprise drives
- exclusions: enterprise SSDs, controller chip design as a licensed platform
- china_relevance: medium — a steady domestic segment tied to smartphone/auto electronics cycles
- confidence: high
- sources: JEDEC eMMC/UFS standards, JEDEC; JEDEC automotive storage standards, JEDEC; JEDEC, "Universal Flash Storage (UFS)" and "eMMC" standards (JESD220 family); TrendForce, mobile storage market research; 中国半导体行业协会存储行业报告

### niche-memory-products
- id: theme:niche_memory_products
- name_en: Niche & specialty memory (NOR / niche DRAM)
- name_zh: 利基存储（NOR/利基DRAM）
- value_chain_position: midstream
- parent_sub_theme: none
- defining_activities: manufacturing specialty DRAM (consumer/graphics/automotive grades) on trailing nodes; producing NOR flash and SLC NAND; serving code-storage and industrial niches with long lifecycle commitments; specialty-process customization; embedded-memory and small-batch specialty processes on trailing nodes; supply-cycle management disconnected from server DRAM
- distinct_from: theme:conventional_dram — commodity mainstream DRAM vs trailing-node specialty lines; distinct_from theme:nand_enterprise_storage — code-flash niches vs enterprise NAND
- exclusions: HBM, emerging non-volatile media (separate row)
- china_relevance: medium — 利基存储 is the standard Chinese trade-press term for this product family
- confidence: high
- sources: JEDEC specialty-memory standards, JEDEC; 中国半导体行业协会年度运行报告 (CSIA annual industry report); TrendForce / DRAMeXchange, niche DRAM market research; 赛迪顾问（CCID）, 中国存储市场白皮书系列; JEDEC, legacy DDR standards (JESD79 family)

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
- defining_activities: integrating compute elements inside or beside memory arrays; building PIM-enabled accelerator stacks for AI inference; co-designing software stacks for near-memory execution; memory-vendor/foundry platform partnerships; PIM-enabled memory SKUs shipping with vendor SDKs; PIM benchmarks with AI framework integrations
- distinct_from: theme:persistent_memory_scm — new media vs compute placement; distinct_from theme:gpu_merchant_accelerators (ai_semiconductors) — in-memory execution vs discrete accelerators
- exclusions: conventional accelerator chips, storage-class media development
- china_relevance: medium — 存算一体 is an active Chinese research/startup direction with growing disclosure vocabulary
- confidence: low
- sources: IRDS (memristive/emerging devices chapter), IEEE; ISSCC/AI accelerator industry sessions trade coverage, IEEE Spectrum; IEEE IRDS, memory and "Beyond CMOS"/new-compute chapters; IEEE, PIM literature (e.g., ISCA/MICRO industry-track papers); JEDEC, HBM3 standard (JESD238) context for in-stack logic

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
- distinct_from: theme:nand_enterprise_storage — the drive/media segment vs complete system integration; distinct_from theme:memory_module_manufacturing — modules vs engineered systems; distinct_from theme:software_defined_storage_platforms — engineered appliance systems vs storage control software
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
### theme:lpdram_low_power_memory
- id: `theme:lpdram_low_power_memory` · name_en: "Low-power mobile memory (LPDDR)" · name_zh: "低功耗移动内存（LPDDR）" · value_chain_position: midstream · parent_sub_theme: `theme:memory_product_engineering`
- defining_activities: manufacturing LPDDR5/5X-class DRAM for phones, tablets and AI PCs; co-packaging LPDRAM with application processors (PoP); qualifying low-voltage speed grades per JEDEC revisions; supplying AI-edge devices with increasing memory-per-device content.
- distinct_from: `theme:conventional_dram` (existing) — server/PC DDR DIMM path vs low-power mobile/packaged DRAM product class.
- exclusions: server RDIMMs; automotive-qualified memory programs (separate row); HBM (hbm_packaging).
- china_relevance: high — domestic DRAM capacity growth centers on LPDDR-class products (存储国产化, CCID/协会 standing line).
- confidence: high
- sources: JEDEC, "JESD209-5 Low Power Double Data Rate (LPDDR5)"; TrendForce / DRAMeXchange, memory market research series; 中国半导体行业协会存储行业报告（协会/CCID 系列）.

### theme:automotive_grade_memory
- id: `theme:automotive_grade_memory` · name_en: "Automotive-grade memory" · name_zh: "车规级存储" · value_chain_position: midstream · parent_sub_theme: `theme:memory_product_engineering`
- defining_activities: qualifying DRAM/NAND to automotive reliability regimes (AEC-Q100, ISO 26262 flows); supplying infotainment, ADAS and telematics memory with long-term availability commitments; running automotive-grade temperature/lifetime screening; supporting functional-safety documentation for carmakers.
- distinct_from: `theme:lpdram_low_power_memory` — same media families but the qualification/availability regime (车规认证) is the distinct market mechanism and product line.
- exclusions: consumer-grade memory sold into vehicles without automotive qualification; automotive compute SoCs (no memory mechanism).
- china_relevance: high — 汽车存储 is a fast-growing named segment in Chinese auto-electronics trade press.
- confidence: medium
- sources: Automotive Electronics Council, "AEC-Q100" failure-mechanism-based qualification; ISO, "ISO 26262 Road vehicles — Functional safety"; 中国汽车工业协会车规电子相关行业报告.

### theme:nearline_hard_disk_drives
- id: `theme:nearline_hard_disk_drives` · name_en: "Nearline hard disk drives (HDD)" · name_zh: "近线机械硬盘" · value_chain_position: midstream · parent_sub_theme: `theme:memory_product_engineering`
- defining_activities: manufacturing high-capacity nearline drives (PMR/SMR, helium-filled) for hyperscale cold and warm data; developing energy-assisted recording (HAMR/MAMR) areal-density roadmaps; selling exabyte-scale capacity into cloud storage pools; servicing drive fleet reliability programs.
- distinct_from: `theme:nand_enterprise_storage` — magnetic recording media vs flash; the AI-memory-cycle framing in the existing row is NAND-centric.
- exclusions: consumer/desktop drives; SSDs; tape (separate row).
- china_relevance: medium — HDD manufacturing is offshore; Chinese demand (hyperscale/archive) is the relevance, not domestic production.
- confidence: high
- sources: IDEMA, hard-drive industry standards body publications; TrendForce, enterprise storage market research; SNIA, storage industry technical work (HDD/SMR working content).

### theme:tape_archival_storage
- id: `theme:tape_archival_storage` · name_en: "Tape archival storage" · name_zh: "磁带归档存储" · value_chain_position: midstream · parent_sub_theme: `theme:memory_product_engineering`
- defining_activities: manufacturing LTO-class tape cartridges and drives for cold archives; operating sequential-access libraries for hyperscale and media archives; advancing cartridge capacity per LTO roadmap generations; supplying air-gapped backup media for ransomware-resilient archives.
- distinct_from: `theme:nearline_hard_disk_drives` — sequential tape library economics vs random-access disk; distinct cost-per-TB cold tier.
- exclusions: HDD; optical disc; consumer backup services.
- china_relevance: medium — 磁带存储 in China is a niche archive tier (domestic demand rising with data-regulation retention).
- confidence: medium
- sources: LTO Consortium, "LTO Ultrium technology roadmap"; SNIA, "Solid State Storage / archival" technical publications.

### theme:cxl_memory_expansion_devices
- id: `theme:cxl_memory_expansion_devices` · name_en: "CXL memory expansion & pooling devices" · name_zh: "CXL 内存扩展与池化" · value_chain_position: midstream · parent_sub_theme: `theme:memory_product_engineering`
- defining_activities: building CXL-attached memory expansion units decoupled from host DIMM slots; implementing memory pooling/sharing switches and controllers on CXL protocols; qualifying Type-3 device latency and metadata handling; enabling composable memory for AI servers.
- distinct_from: `theme:conventional_dram` — DDR5 DIMMs vs CXL-attached expansion/pooling appliances; distinct from `theme:pcie_fabric_silicon` (ai_semiconductors) — memory-protocol endpoints vs generic PCIe fabric.
- exclusions: standard RDIMMs; DPU offload (separate row); SSDs presented over CXL as storage.
- china_relevance: medium — CXL 池化 is an early server-ecosystem theme in Chinese data-center trade press.
- confidence: medium
- sources: CXL Consortium, "Compute Express Link Specification" (memory Type-3/pooling); JEDEC, DDR5/MRDIMM-adjacent standards (JESD79-5, sideband/MR modules); SNIA, composable-infrastructure technical work.

### theme:software_defined_storage_platforms
- id: `theme:software_defined_storage_platforms` · name_en: "Software-defined storage platforms" · name_zh: "软件定义存储" · value_chain_position: downstream · parent_sub_theme: `theme:memory_product_engineering`
- defining_activities: building distributed storage control software over commodity hardware; virtualizing block/file/object pools into service catalogs; integrating tiering, erasure coding and data-reduction pipelines; licensing subscriptions across hybrid-cloud estates.
- distinct_from: `theme:nand_enterprise_storage` (existing) — storage control software vs NAND/storage hardware framing; complements `theme:enterprise_ssd_controllers` (silicon) with the platform-software layer; distinct from `theme:data_center_storage_systems` — storage control software vs engineered appliance systems
- exclusions: hardware appliances as such; backup SaaS without storage-platform mechanism; database software.
- china_relevance: medium — 软件定义存储 is an established Chinese enterprise-IT category (信创 storage stacks).
- confidence: medium
- sources: SNIA, "Software Defined Storage" technical publications; CNCF / open-storage ecosystem foundation documentation (e.g., Cloud Native Storage landscape); 赛迪顾问（CCID）, 中国软件定义存储市场报告系列.

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
- defining_activities: building medium/high-energy ion implanters; developing beamline and dose-control technology; qualifying implant recipes per node; plasma-doping tool development for advanced flows; implant-angle-control systems; dose-uniformity and wafer-charging qualification
- distinct_from: theme:etch_deposition_equipment — different process-step family (doping vs material removal/addition); distinct_from theme:lithography_tools — pattern transfer vs dopant introduction
- exclusions: diffusion furnace thermal steps (epitaxy/thermal row), metrology tools
- china_relevance: high — 离子注入机 is a named domestic first-unit（首台套）equipment category
- confidence: high
- sources: 《首台（套）重大技术装备推广应用指导目录》, 工业和信息化部 (MIIT); IRDS, IEEE; SEMI, "World Fab Forecast" (tool-class coverage); IEEE IRDS, "Front End Processes" chapter; 赛迪顾问（CCID）, 中国半导体设备市场白皮书系列

### cmp-planarization-equipment
- id: theme:cmp_planarization_equipment
- name_en: CMP planarization equipment
- name_zh: CMP抛光设备
- value_chain_position: midstream
- parent_sub_theme: none
- defining_activities: manufacturing CMP polish platforms; developing head/plate and endpoint-detection systems; co-optimizing removal-rate performance with consumable vendors; servicing installed tool fleets; removal-rate uniformity qualification across copper/tungsten/dielectric steps; pad/conditioner ecosystem servicing
- distinct_from: theme:etch_deposition_equipment — mechanical-chemical planarization vs deposition/etch; distinct_from theme:cmp_polishing_consumables (ai_semiconductors) — machine vs slurry/pad consumables
- exclusions: post-CMP cleaning modules beyond the tool, consumable manufacture
- china_relevance: high — a tracked domestic equipment breakpoint category
- confidence: high
- sources: IRDS, IEEE; SEMI equipment standards (SEMI E-series), SEMI; SEMI, "World Fab Forecast"; IEEE IRDS, "Front End Processes" chapter; 中国电子专用设备工业协会（CEPEIA）行业运行报告

### wet-clean-equipment
- id: theme:wet_clean_equipment
- name_en: Wafer cleaning & wet process equipment
- name_zh: 晶圆清洗与湿法设备
- value_chain_position: midstream
- parent_sub_theme: none
- defining_activities: manufacturing single-wafer and batch wet-cleaning tools; developing megasonic/SC1-SC2 process hardware; building electroplating and wet-etch stations; chemical-recycling and rinse-water reduction systems; dry-cleaning and bevel/polish prep tools; particle-removal and metallic-contamination spec qualification
- distinct_from: theme:etch_deposition_equipment — wet chemistry process steps vs plasma dry processing; distinct_from theme:fab_facility_systems — process tool vs fab utility systems
- exclusions: CMP polish tools, dry plasma clean integrated in deposition tools
- china_relevance: high — 清洗设备 is a leading domestic-substitution equipment segment
- confidence: high
- sources: SEMI E-series equipment standards, SEMI; 中国电子专用设备工业协会 (CEIA) annual semiconductor-equipment statistics; SEMI, "World Fab Forecast"; SEMI International Standards (surface preparation/EHS-related standards program); 中国电子专用设备工业协会（CEPEIA）行业运行报告

### coat-develop-track
- id: theme:coat_develop_track
- name_en: Coat-develop track equipment
- name_zh: 涂胶显影设备
- value_chain_position: midstream
- parent_sub_theme: none
- defining_activities: manufacturing resist coat/develop tracks; hotplate/chill and dispense-system engineering; micron-level co-operation with scanner exposure tools; EUV-era track process development; matched track-exposure cluster throughput; resist-film uniformity control at advanced nodes
- distinct_from: theme:lithography_tools — the companion track cluster vs the exposure scanner itself; distinct_from theme:photoresist_semiconductor_materials (ai_semiconductors) — dispensing machine vs the resist chemistry
- exclusions: scanner manufacture, resist supply
- china_relevance: high — 涂胶显影 is an established domestic equipment category in A-share disclosure
- confidence: high
- sources: SEMI E-series equipment standards, SEMI; IRDS, IEEE; SEMI, "World Fab Forecast"; IEEE IRDS, lithography integration chapters; 中国电子专用设备工业协会（CEPEIA）行业运行报告

### epitaxy-thermal-equipment
- id: theme:epitaxy_thermal_equipment
- name_en: Epitaxy & thermal process equipment
- name_zh: 外延与热处理设备
- value_chain_position: midstream
- parent_sub_theme: none
- defining_activities: building epitaxial deposition reactors (Si/SiGe/GaN classes); manufacturing oxidation/diffusion and rapid-thermal-processing furnaces; layer-thickness/uniformity process control; specialty epi services for power/compound lines; selective epitaxy for source/drain and device-stack steps; susceptor/precursor lifecycle servicing; laser-anneal and RTP systems with oxidation/nitridation ambient control; thermal-budget qualification for advanced-node stacks
- distinct_from: theme:ion_implant_equipment — layer growth/thermal treatment vs dopant implantation; distinct_from theme:etch_deposition_equipment — epi/thermal furnace family vs CVD/PVD/ALD thin-film tooling
- exclusions: thin-film CVD/ALD tools (inside existing etch_deposition row), metrology
- china_relevance: medium — domestic epi/furnace qualification is advancing but less publicly tracked than track/clean tools
- confidence: medium
- sources: IRDS, IEEE; SEMI E-series equipment standards, SEMI; SEMI, "World Fab Forecast"; IEEE IRDS, "Front End Processes" chapter; 中国电子专用设备工业协会（CEPEIA）行业运行报告

### advanced-packaging-equipment
- id: theme:advanced_packaging_equipment
- name_en: Advanced packaging & assembly equipment
- name_zh: 先进封装与后道设备
- value_chain_position: midstream
- parent_sub_theme: theme:semi_back_end_equipment
- defining_activities: building bonders/placers for 2.5D/3D flows; wafer-level molding, plating and TSV etch tooling; hybrid-bonding tool development; die-attach and flip-chip platform families; molding/underfill/reflow tooling for large compute packages; sub-micron bond-alignment qualification
- distinct_from: theme:advanced_packaging_2_5d_3d (ai_semiconductors) — toolmaker vs packaging service provider; distinct_from theme:wafer_fab_subsystems — back-end equipment vs front-end subsystem supply
- exclusions: test equipment (ATE row), packaging materials
- china_relevance: high — 后道设备国产化 tracks the domestic 先进封装 buildout
- confidence: high
- sources: SEMI advanced packaging standards, SEMI; 中国电子专用设备工业协会 (CEIA) annual semiconductor-equipment statistics; Yole Group, "Status of the Advanced Packaging Industry" (equipment coverage); SEMI, advanced packaging standards/reports; 赛迪顾问（CCID）, 中国半导体设备市场白皮书系列

### semiconductor-ate
- id: theme:semiconductor_ate
- name_en: Semiconductor test equipment (ATE)
- name_zh: 半导体测试设备（ATE）
- value_chain_position: midstream
- parent_sub_theme: theme:semi_back_end_equipment
- defining_activities: manufacturing wafer-sort and final-test ATE systems; device-power/consumption test-head engineering; prober and handler integration; test-program library and correlation services; AI-device power/thermal test-envelope qualification; test-cell software and characterization flows
- distinct_from: theme:ai_chip_osat (ai_semiconductors) — sells testers vs performing test as a service; distinct_from theme:process_metrology_inspection — electrical test vs optical/process metrology
- exclusions: inspection/metrology optics, assembly bonders
- china_relevance: medium — domestic ATE is an active but harder-to-localize segment
- confidence: high
- sources: SEMI test standards, SEMI; IRDS, IEEE; IEEE, "International Test Conference (ITC)" proceedings; SEMI, test-related standards program; 赛迪顾问（CCID）, 中国半导体设备市场白皮书系列

### fab-facility-systems
- id: theme:fab_facility_systems
- name_en: Fab facility & cleanroom systems
- name_zh: 洁净室与厂务系统工程
- value_chain_position: downstream
- parent_sub_theme: theme:semicap_support_chain
- defining_activities: engineering cleanroom HVAC and recirculation air systems; bulk gas and chemical delivery (CUB/CBS) systems; vibration/EMI control and fab wide-area utilities; waste treatment and abatement skids; gas cabinets/valve manifolds and bulk specialty-gas delivery loops; delivery purity/moisture qualification with fab-wide gas and chemical telemetry
- distinct_from: theme:etch_deposition_equipment — the facility layer around tools vs process tools; distinct_from theme:electronic_specialty_gases (ai_semiconductors) — delivers/abates gas vs produces it
- exclusions: process equipment, CIM software
- china_relevance: high — 厂务/洁净室 engineering rides every domestic fab shell buildout
- confidence: high
- sources: SEMI facility standards (SEMI F-series), SEMI; 中国电子专用设备工业协会 (CEIA) annual semiconductor-equipment statistics; SEMI, gas/chemical delivery-related facilities standards program; IEEE IRDS, "Factory Integration" chapter; 中国电子专用设备工业协会（CEPEIA）行业报告

### fab-automation-cim
- id: theme:fab_automation_cim
- name_en: Fab automation & CIM software
- name_zh: 晶圆厂自动化与CIM软件
- value_chain_position: enabler
- parent_sub_theme: theme:semicap_support_chain
- defining_activities: deploying MES/YMS recipe and lot-control systems; automated material handling systems (AMHS overhead hoist transport); scheduling/dispatch and equipment-automation integration (SECS/GEM); fab data platforms; OHT/stocker AMHS fleets with MCS carrier-management software to SEMI E-series interfaces; sorter/stocker integration with MES flows
- distinct_from: theme:fab_facility_systems — software/automation vs physical utilities; distinct_from theme:grid_dispatch_ems_software (grid) — plant-level manufacturing execution vs power-grid dispatch
- exclusions: EDA software
- china_relevance: high — CIM/MES substitution is a named software breakpoint in domestic fab programs
- confidence: high
- sources: SEMI SECS/GEM equipment-automation standards, SEMI; IRDS, IEEE; SEMI, interface and factory-automation standards (E-series, e.g., carrier management and equipment automation); IEEE IRDS, "Factory Integration" chapter; 赛迪顾问（CCID）, 中国半导体设备市场白皮书系列

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
- defining_activities: sourcing/decommissioning used tools; refurbishing to spec with warranty; reselling into trailing-node, specialty and education fabs; parts harvesting and lifecycle extension; secondary-market deal brokering across regions
- distinct_from: theme:equipment_field_services — transacts used-tool value vs maintaining new-tool installed base; distinct_from theme:advanced_node_foundry — enables trailing nodes, not leading-edge
- exclusions: new equipment OEM channels, broker-only trading without refurbishment
- china_relevance: medium — a visible channel in Chinese mature-node fab economics
- confidence: medium
- sources: SEMI secondary-equipment guidance, SEMI; 中国电子专用设备工业协会 (CEIA) annual semiconductor-equipment statistics; SEMI, "World Fab Forecast" (capacity/fab-economics context); Semiconductor Engineering / EE Times (trade press) on secondary equipment markets; 中国电子专用设备工业协会（CEPEIA）行业报告

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
### theme:probe_card_test_interfaces
- id: `theme:probe_card_test_interfaces` · name_en: "Probe cards & test interfaces" · name_zh: "探针卡与测试接口" · value_chain_position: upstream · parent_sub_theme: `theme:semi_back_end_equipment`
- defining_activities: manufacturing MEMS/cantilever probe cards for wafer sort; building test sockets, loadboards and contactors for final test; iterating fine-pitch contact technology for advanced devices; supplying consumable contact cycles to test floors.
- distinct_from: `theme:semiconductor_ate` — contact consumables/interfaces vs tester systems; a recurring-consumable mechanism distinct from capital tools.
- exclusions: ATE systems; SLT fixtures (ai row).
- china_relevance: high — 探针卡国产化 is an active domestic substitution category (trade press/CCID).
- confidence: medium
- sources: IEEE, "Semiconductor Wafer Test Workshop (SWTest)" proceedings; IEEE ITC proceedings (probe/contact sessions); 赛迪顾问（CCID）半导体耗材/部件专题报告.

### theme:vacuum_subsystem_components
- id: `theme:vacuum_subsystem_components` · name_en: "Vacuum subsystem components" · name_zh: "真空子系统与部件" · value_chain_position: upstream · parent_sub_theme: `theme:equipment_component_periphery`
- defining_activities: manufacturing dry/turbo/cryo vacuum pumps for process chambers; supplying valves, throttle controllers, gauges and seals into tool builds; qualifying particle/condensable performance for deposition and etch ambients; aftermarket-servicing installed pump fleets.
- distinct_from: `theme:wafer_fab_subsystems` (existing) — the broad subsystem layer vs the vacuum-generation/flow component class specifically (a recognized standalone segment in Chinese equipment-parts reporting).
- exclusions: RF power (separate row); tool-integrated subsystems designed only inside OEM tools (subsystems row).
- china_relevance: high — 真空部件 is a headline 设备零部件国产化 category (CCID/协会).
- confidence: high
- sources: SEMI, "World Fab Forecast" (subsystem supply context); 赛迪顾问（CCID）, 中国半导体设备零部件白皮书系列; 中国电子专用设备工业协会（CEPEIA）行业报告.

### theme:rf_power_matching_subsystems
- id: `theme:rf_power_matching_subsystems` · name_en: "RF power & matching subsystems" · name_zh: "射频电源与匹配子系统" · value_chain_position: upstream · parent_sub_theme: `theme:equipment_component_periphery`
- defining_activities: manufacturing RF generators and impedance-match networks for plasma tools; supplying DC/pulsed bias supplies and remote plasma sources; qualifying plasma stability and match speed across process recipes; servicing generator fleets in fabs.
- distinct_from: `theme:vacuum_subsystem_components` — plasma-energy delivery vs vacuum generation/flow; both are the component classes inside the broad wafer_fab_subsystems layer.
- exclusions: RFFoundry-level power distribution (fab facilities row); communications RF components (no linkage).
- china_relevance: high — 射频电源 is a named 零部件国产化 priority (CCID standing line).
- confidence: high
- sources: 赛迪顾问（CCID）, 中国半导体设备零部件白皮书系列; SEMI, standards for RF/plasma-related equipment interfaces; 中国电子专用设备工业协会（CEPEIA）行业报告.

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
- defining_activities: manufacturing computer-room air conditioners/handlers; airflow containment engineering (hot/cold aisle); humidity and filtration control for white space; indirect evaporative cooling unit development; airside economizers and containment airflow optimization; air-cooled hall retrofits for rising rack densities
- distinct_from: theme:liquid_cooling_thermal — air-side cooling vs liquid loop segment; distinct_from theme:thermal_rejection_heat_recovery — white-space units vs exterior heat-rejection plant
- exclusions: liquid loops, building comfort HVAC
- china_relevance: high — 精密空调 is a stable domestic datacenter equipment category
- confidence: high
- sources: "Thermal Guidelines for Data Processing Environments", ASHRAE TC 9.9; GB 40879-2021《数据中心能效限定值及能效等级》, 中国国家标准; ASHRAE TC 9.9, "Thermal Guidelines for Data Processing Environments"; AHRI, "AHRI 550/590" performance rating standard (chilled-water/dx equipment context); ODCC（开放数据中心委员会）制冷技术规范系列

### thermal-rejection-heat-recovery
- id: theme:thermal_rejection_heat_recovery
- name_en: Heat rejection & waste-heat recovery
- name_zh: 冷却塔/干冷器与余热回收
- value_chain_position: midstream
- parent_sub_theme: theme:datacenter_cooling_chain
- defining_activities: engineering cooling towers and dry coolers; free-cooling economizer design; heat-pump boosters exporting waste heat to district networks; water-usage effectiveness optimization; municipal heat-offtake contracting with revenue-graded heat supply
- distinct_from: theme:precision_air_conditioning — exterior heat rejection vs white-space units; distinct_from theme:liquid_cooling_thermal — facility heat export vs IT-space thermal segment
- exclusions: chiller manufacture as standalone, immersion tanks
- china_relevance: medium — 余热回收 is a growing regulatory-adjacent topic in Chinese green-datacenter policy
- confidence: medium
- sources: ISO/IEC 30134 series (data centre KPIs incl. ERF), ISO/IEC; "Thermal Guidelines for Data Processing Environments", ASHRAE TC 9.9; IEA, "Data Centres and Data Transmission Networks" (2020, heat-reuse analysis); ASHRAE TC 9.9 liquid/thermal publications; 北极星电力网/ODCC 数据中心余热利用专题（trade press）

### immersion-thermal-fluids
- id: theme:immersion_thermal_fluids
- name_en: Dielectric fluids & thermal interface materials
- name_zh: 液冷工质与热界面材料
- value_chain_position: upstream
- parent_sub_theme: theme:datacenter_cooling_chain
- defining_activities: formulating synthetic/dielectric immersion fluids; producing thermal greases, pads and phase-change TIMs; chemistry compatibility qualification with server hardware; fluid lifecycle and reclamation services; water-glycol and single/two-phase dielectric fluid formulation for liquid loops and immersion tanks; coolant recycling and lifecycle management at fleet scale; gap-pad/gel/phase-change TIM grades for die-to-cold-plate paths qualified under power cycling; low-pump-out TIM iteration for cold-plate fleets
- distinct_from: theme:immersion_cooling_systems — the working fluid/TIM consumable vs the tank system; distinct_from theme:photoresist_semiconductor_materials — datacenter chemistry vs fab chemistry
- exclusions: CDU/cold-plate hardware, water treatment chemicals for towers
- china_relevance: medium — 液冷工质 domestication tracks the domestic cold-plate/immersion ramp
- confidence: medium
- sources: OCP liquid-cooling specifications (fluid requirements), Open Compute Project; "Thermal Guidelines for Data Processing Environments", ASHRAE TC 9.9; ASHRAE, "Emergence and Expansion of Liquid Cooling in Mainstream Data Centers" (white paper); Open Compute Project, cooling-environment/coolant specifications; ODCC（开放数据中心委员会）液冷技术规范系列; ASHRAE TC 9.9, "Thermal Guidelines for Data Processing Environments"; IEEE, "Semiconductor Thermal Measurement and Management Symposium (SEMI-THERM)" proceedings

### dc-hvdc-power-architecture
- id: theme:dc_hvdc_power_architecture
- name_en: DC power architecture (240/336V HVDC)
- name_zh: 高压直流供电架构（含巴拿马电源）
- value_chain_position: midstream
- parent_sub_theme: theme:datacenter_power_chain
- defining_activities: engineering 240V/336V DC bus architectures; integrated power-supply units that merge transformer/rectifier stages; rectifier and DC-DC converter platform development; DC distribution protection coordination; MV-to-rack DC distribution chains that eliminate legacy AC conversion stages; DC fault-protection qualification for MV bus architectures
- distinct_from: theme:ups_power_conversion — DC bus architecture replacing/integrating the UPS stage vs the UPS product row; distinct_from theme:busway_smart_pdu — source-side architecture vs rack-level distribution hardware
- exclusions: AC UPS products, utility-scale HVDC transmission (grid theme)
- china_relevance: high — 高压直流/巴拿马电源 is a distinctly Chinese datacenter power-train vocabulary with domestic champions
- confidence: high
- sources: ODCC (开放数据中心委员会) datacenter power白皮书 series; OCP power hardware specifications, Open Compute Project; ODCC（开放数据中心委员会）, 240V/336V 直流及中压直流供电技术规范系列; EN 50600 (CENELEC data centre facilities standard); Uptime Institute, "Global Data Center Survey" (topology share data)

### backup-generator-sets
- id: theme:backup_generator_sets
- name_en: Backup generator sets (diesel/gas)
- name_zh: 备用发电机组（柴油/燃气）
- value_chain_position: midstream
- parent_sub_theme: theme:datacenter_power_chain
- defining_activities: manufacturing standby gensets sized for campus loads; paralleling switchgear and black-start control integration; emissions after-treatment and fuel-storage engineering; long-duration outage testing services; ATS paralleling sequences for tier-level redundancy; fuel-polishing and run-test regimes
- distinct_from: theme:ups_power_conversion — minutes-scale electromechanical standby vs electronic ride-through conversion; distinct_from theme:behind_meter_generation — emergency standby vs continuous on-site generation
- exclusions: prime-power gas turbines, UPS products
- china_relevance: high — 柴油发电机备电 is the universal Chinese datacenter resiliency requirement
- confidence: high
- sources: Uptime Institute Tier Standard: Topology (backup power requirements); GB/T standards for diesel generating sets, 中国国家标准; ISO, "ISO 8528 Reciprocating internal combustion engine driven alternating current generating sets"; U.S. EPA, stationary emergency engine regulations (40 CFR 60 Subpart IIII); Uptime Institute, "Global Data Center Survey" (topology context)

### dc-battery-backup
- id: theme:dc_battery_backup
- name_en: Battery backup & BBU systems
- name_zh: 数据中心备电电池（UPS电池/BBU）
- value_chain_position: midstream
- parent_sub_theme: theme:datacenter_power_chain
- defining_activities: supplying VRLA/lithium strings for UPS plants; rack-level battery backup unit (BBU) integration in server shelves; battery monitoring and fire-safety engineering; lithium retirement/replacement services; facility BESS for bridging and peak management; stationary-ESS safety qualification (UL 9540/9540A, NFPA 855)
- distinct_from: theme:ups_power_conversion — energy storage element vs the conversion electronics; distinct_from theme:grid_storage_integration (grid) — facility ride-through batteries vs grid-side energy arbitrage plants
- exclusions: UPS inverters, generator sets, grid-scale BESS
- china_relevance: high — 锂电备电 substitution is an active domestic datacenter build standard
- confidence: high
- sources: Uptime Institute Tier Standard: Topology; ODCC (开放数据中心委员会) datacenter facility白皮书 series; UL, "UL 9540 / UL 9540A" energy storage system safety standards; NFPA, "NFPA 855 Standard for the Installation of Stationary Energy Storage Systems"; ODCC（开放数据中心委员会）, 数据中心储能/备电技术规范系列

### busway-smart-pdu
- id: theme:busway_smart_pdu
- name_en: Busway & intelligent PDU distribution
- name_zh: 母线槽与智能PDU配电
- value_chain_position: midstream
- parent_sub_theme: theme:datacenter_power_chain
- defining_activities: manufacturing overhead busway trunk systems; intelligent rack PDU metering/switching; branch-circuit monitoring at rack level; tap-off box and busway installation services; short-circuit and tap-rating qualification for dense rows; bus-run reconfiguration for changing rack layouts
- distinct_from: theme:hv_transformers_switchgear — in-building rack-level distribution vs utility-class transformers/switchgear; distinct_from theme:dc_hvdc_power_architecture — delivery hardware vs source architecture
- exclusions: medium-voltage switchgear, UPS products
- china_relevance: high — 母线槽/智能PDU is standard Chinese modular-datacenter fitout vocabulary
- confidence: high
- sources: ODCC (开放数据中心委员会) datacenter facility白皮书 series; Uptime Institute Tier Standard: Topology; IEC, "IEC 61439-6 busbar trunking systems"; Uptime Institute, "Global Data Center Survey"; ODCC（开放数据中心委员会）配电技术规范系列

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
- defining_activities: contracting long-term power purchase agreements; siting on-site generation (gas engines, fuel cells, SMR-PPA structures); microgrid control of campus generation; renewable-certificate and 24/7 clean-energy matching; multi-MW stationary fuel-cell arrays operated with grid-forming inverters; hydrogen/reformate fuel-supply integration for stationary fuel-cell plants; behind-the-meter gas turbines contracted ahead of grid upgrades; air-permit and fuel-logistics management for campus generation
- distinct_from: theme:backup_generator_sets — continuous/economic generation vs emergency standby; distinct_from theme:grid_interconnection_services — self-supply vs utility interconnection engineering
- exclusions: utility power-plant development, generator-set manufacture
- china_relevance: high — 绿电直供/源网荷储 is the active Chinese policy vocabulary for datacenter energy procurement
- confidence: medium
- sources: "Data Centres and Data Transmission Networks", IEA; ODCC (开放数据中心委员会) datacenter energy白皮书 series; IEC, "IEC 62282 Fuel cell technologies" standard series; U.S. DOE Hydrogen Program, hydrogen power/demonstration program documents; IEA, "Data Centres and Data Transmission Networks" (2020); Uptime Institute, "Global Data Center Survey" (power-topology trends); IEA, "Energy and AI" (2025, data-center electricity supply analysis); LBNL, "United States Data Center Energy Usage Report" (2024)

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
- distinct_from: theme:fab_facility_systems (semicap) — datacenter modules vs fab cleanrooms; distinct_from theme:grid_interconnection_services — productized facility integration vs utility access engineering; distinct_from theme:prefab_power_modules — power-train module product vs whole-facility modular DC product
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
- defining_activities: deploying data-center infrastructure management platforms; real-time PUE/WUE instrumentation and telemetry; capacity planning and digital-twin modeling; energy-carbon reporting to regulators; model-predictive cooling control for PUE optimization
- distinct_from: theme:fab_automation_cim (semicap) — facility energy software vs manufacturing execution; distinct_from theme:grid_dispatch_ems_software (grid) — campus energy management vs grid dispatch
- exclusions: IT workload orchestration, facility hardware
- china_relevance: high — 能碳管理/PUE监管 reporting is mandated in Chinese datacenter policy
- confidence: high
- sources: ISO/IEC 30134-2 (PUE), ISO/IEC; GB 40879-2021《数据中心能效限定值及能效等级》, 中国国家标准; ODCC（开放数据中心委员会）, 数据中心运营管理/能效技术规范系列; GB 40879-2021, 《数据中心能效限定值及能效等级》; Uptime Institute, "Global Data Center Survey" (management-software adoption data)
### theme:prefab_power_modules
- id: `theme:prefab_power_modules` · name_en: "Prefabricated power modules" · name_zh: "预制化电力模组" · value_chain_position: midstream · parent_sub_theme: `theme:datacenter_power_chain`
- defining_activities: factory-building integrated power trains (MV switchgear-transformer-UPS-PDU in skids); compressing on-site electrical commissioning schedules; standardizing modular power blocks for repeatable halls; delivering containerized power for fast builds.
- distinct_from: `theme:hv_transformers_switchgear` / `theme:ups_power_conversion` — discrete product classes vs the factory-integrated module train that combines them; a recognized product-form trend in Chinese DC construction; distinct from `theme:prefab_modular_datacenter` — the factory-integrated power-train product class vs whole-facility modular DC products
- exclusions: discrete switchgear/UPS products themselves; portable generators.
- china_relevance: high — 一体化电力模组/预制舱 is a flagship Chinese DC supply-chain trend (ODCC specifications).
- confidence: medium
- sources: ODCC（开放数据中心委员会）, 电力模组/预制化数据中心技术规范系列; 工信部, 《新型数据中心发展三年行动计划（2021-2023年）》; Uptime Institute research notes on modular data centers.

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
- defining_activities: manufacturing steam turbines and generators for NPP thermal cycles; condensers, heaters and moisture-separator-reheaters; turbine-island piping and balance-of-plant integration; retrofit/uprate programs on operating units; moisture-separator reheaters and secondary-cycle pumps; rotor/blade lifecycle servicing
- distinct_from: theme:nuclear_components — the existing row is the nuclear-island-side component supply chain; this row is the conventional (thermal-to-electric) island train; distinct_from theme:reactor_technology — plant equipment vs reactor system design
- exclusions: reactor coolant system components (nuclear_components row), EPC construction
- china_relevance: high — 核岛/常规岛 is the standard Chinese nuclear-equipment disclosure split
- confidence: high
- sources: IAEA Nuclear Energy Series (NPP equipment guidance), IAEA; IAEA PRIS plant-system reference data, IAEA; IAEA, Nuclear Energy Series (plant systems reports); World Nuclear Association, plant-systems information papers; 中国核能行业协会, 《中国核能发展报告》蓝皮书

### nuclear-digital-ic
- id: theme:nuclear_digital_ic
- name_en: Nuclear-grade digital I&C
- name_zh: 核级数字化仪控系统
- value_chain_position: enabler
- parent_sub_theme: theme:nuclear_plant_systems
- defining_activities: building reactor protection and safety I&C platforms (DCS class); radiation-hardened/qualified instrumentation supply; full-scope simulator and control-room integration; cybersecurity hardening of safety systems; non-safety plant DCS platforms for plant control; software/firmware qualification under nuclear software QA (IEC 62138/IEC 60880)
- distinct_from: theme:nuclear_components — qualified instrumentation & control SYSTEMS vs mechanical components; distinct_from theme:fab_automation_cim (semicap) — safety-class control vs manufacturing execution
- exclusions: conventional island electrical balance-of-plant, plant IT networks
- china_relevance: high — 核级DCS/仪控自主化 is a named domesticization program in Chinese nuclear coverage
- confidence: high
- sources: HAF102《核动力厂设计安全规定》, 国家核安全局 (NNSA); IAEA Nuclear Energy Series (I&C for NPPs), IAEA; IEC, "IEC 62138 / IEC 60880" nuclear I&C software qualification standard series; IAEA, Nuclear Energy Series (instrumentation & control reports); 中国核能行业协会, 《中国核能发展报告》蓝皮书

### nuclear-grade-forgings-materials
- id: theme:nuclear_grade_forgings_materials
- name_en: Nuclear-grade materials & heavy forgings
- name_zh: 核级材料与大型锻件
- value_chain_position: upstream
- parent_sub_theme: theme:nuclear_plant_systems
- defining_activities: forging reactor pressure vessels, steam generators and pressurizer shells; producing zirconium-alloy cladding tube stock; nuclear-grade welding consumables and specialty steels; code-stamped (ASME/RCC-M class) material qualification; ultralarge press/heat-treatment capacity expansion; nuclear-grade forging QA and material traceability
- distinct_from: theme:nuclear_components — supplies qualified RAW material/forgings into component fabrication vs fabricating components; distinct_from theme:conventional_island_equipment — materials vs turbine machinery
- exclusions: finished component manufacture, fuel assembly assembly work
- china_relevance: high — 大型锻件/锆材自主化 is a recurring bottleneck topic in Chinese nuclear coverage
- confidence: high
- sources: 《中国核能发展报告》蓝皮书, 中国核能行业协会; IAEA Nuclear Energy Series (materials), IAEA; World Nuclear News (trade press), heavy forging capacity coverage; OECD-NEA, nuclear supply-chain reports; 中国核能行业协会, 《中国核能发展报告》蓝皮书

### npp-construction-epc
- id: theme:npp_construction_epc
- name_en: Nuclear plant construction & installation (EPC)
- name_zh: 核电工程建设与安装（EPC）
- value_chain_position: midstream
- parent_sub_theme: theme:nuclear_build_operate
- defining_activities: executing nuclear-island civil works and containment construction; heavy-lift module installation and large-equipment placement; construction QA/QC under nuclear codes; schedule management of multi-unit programs; commissioning-to-fuel-load milestone delivery
- distinct_from: theme:nuclear_components — construction services vs component supply; distinct_from theme:transmission_substation_epc (grid) — plant-scope EPC vs grid-line EPC
- exclusions: plant operation, equipment manufacture
- china_relevance: high — 核电工程EPC is a large disclosed domestic segment with continuous new-unit starts
- confidence: high
- sources: IAEA PRIS construction-status data, IAEA; 《中国核能发展报告》蓝皮书, 中国核能行业协会; World Nuclear Association, "World Nuclear Performance Report" (construction pipeline data); IAEA, Nuclear Energy Series (construction/licensing reports); 中国核能行业协会, 《中国核能发展报告》蓝皮书

### npp-operations
- id: theme:npp_operations
- name_en: Plant operations & license management
- name_zh: 核电站运营
- value_chain_position: downstream
- parent_sub_theme: theme:nuclear_build_operate
- defining_activities: operating reactor units and managing refueling outages; capacity-factor and fleet-reliability programs; license renewal and regulatory reporting; wholesale electricity sales from NPP fleets; power uprates and license-renewal programs; performance-indicator regimes (capacity factor, SCRAM rates)
- distinct_from: theme:reactor_technology — operates licensed plants vs designs reactor systems; distinct_from theme:npp_construction_epc — asset operation vs construction delivery
- exclusions: fuel fabrication, plant construction
- china_relevance: high — 核电运营 is the core Chinese nuclear equity segment vocabulary
- confidence: high
- sources: IAEA PRIS operational metrics (capacity factor, outage data), IAEA; World Nuclear Performance Report, World Nuclear Association; World Nuclear Association, "World Nuclear Performance Report" (operational indicators); Nuclear Energy Institute, "Nuclear Costs in Context" (annual); 中国核能行业协会, 《中国核能发展报告》蓝皮书

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
- sources: IAEA Joint Convention on the Safety of Spent Fuel Management, IAEA; 《中国核能发展报告》蓝皮书, 中国核能行业协会; IAEA, Nuclear Energy Series (spent fuel management reports); World Nuclear Association, fuel-cycle information papers (storage/reprocessing); 中国核能行业协会, 《中国核能发展报告》蓝皮书

### reactor-decommissioning
- id: theme:reactor_decommissioning
- name_en: Reactor & site decommissioning
- name_zh: 核设施退役
- value_chain_position: downstream
- parent_sub_theme: theme:nuclear_build_operate
- defining_activities: characterizing and decontaminating shutdown plants; remote segmentation and dismantling of activated structures; radioactive-waste packaging and disposal routing; site license termination and reuse; low/intermediate-level waste characterization and disposal routing; decommissioning cost-provision and trust-fund management
- distinct_from: theme:spent_fuel_management — plant dismantling vs fuel-cycle material management; distinct_from theme:npp_operations — end-of-life work vs operating assets
- exclusions: operating-plant services, waste storage facilities (in spent-fuel row)
- china_relevance: medium — early-stage domestically; China's first wave of retirements is still ahead of developed markets'
- confidence: medium
- sources: IAEA Decommissioning standards & ARTEMIS review framework, IAEA; OECD NEA decommissioning cost reports, OECD NEA; OECD-NEA, reports on decommissioning policies, strategies and costs; IAEA, Nuclear Energy Series (decommissioning reports); 中国核能行业协会, 《中国核能发展报告》蓝皮书

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
- defining_activities: supplying district heating from reactor units; industrial steam delivery to chemical parks; high-temperature electrolysis and thermochemical hydrogen programs; seawater desalination co-generation; extraction-steam district heating supply; industrial heat-offtake contracts with chemical parks
- distinct_from: theme:npp_operations — sells non-electric energy products vs electricity generation; distinct_from theme:gen4_reactor_systems — the application demand side vs reactor system development
- exclusions: grid electricity sales, reactor technology development
- china_relevance: high — 核能供暖 is already commercial-seasonal in Chinese coastal/northern programs
- confidence: medium
- sources: IAEA Non-electric Applications of Nuclear Energy series, IAEA; 《中国核能发展报告》蓝皮书, 中国核能行业协会; 中国核能行业协会, 《中国核能发展报告》蓝皮书 (核能供暖 program); U.S. DOE Office of Nuclear Energy, hydrogen demonstration program documents; IAEA, Nuclear-Renewable/hybrid heat applications reports

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
### theme:haleu_advanced_fuel_supply
- id: `theme:haleu_advanced_fuel_supply` · name_en: "HALEU advanced fuel supply" · name_zh: "高浓低浓铀（HALEU）燃料供应" · value_chain_position: upstream · parent_sub_theme: `theme:advanced_nuclear_fuel_chain`
- defining_activities: enriching uranium to high-assay low-enriched levels (5–20% U-235); building HALEU deconversion and transport capacity; contracting HALEU supply for advanced-reactor fuel lines; licensing HALEU transport containers.
- distinct_from: `theme:fuel_cycle` (existing) — that row spans legacy mining-through-enrichment (LEU); HALEU is the distinct high-assay enrichment/supply layer for advanced reactors.
- exclusions: natural/LEU uranium mining and conversion (fuel_cycle); fuel forms fabrication (TRISO row).
- china_relevance: high — China operates centrifuge enrichment at scale and is building advanced-reactor fuel capacity (中国核能行业协会蓝皮书).
- confidence: medium
- sources: U.S. DOE, "HALEU Availability Program" documents; OECD-NEA / IAEA, "Uranium: Resources, Production and Demand" ("Red Book", biennial); World Nuclear Association, fuel-cycle information papers.

### theme:triso_fuel_form_fabrication
- id: `theme:triso_fuel_form_fabrication` · name_en: "TRISO coated-particle fuel fabrication" · name_zh: "TRISO 包覆燃料制造" · value_chain_position: upstream · parent_sub_theme: `theme:advanced_nuclear_fuel_chain`
- defining_activities: fabricating coated-particle (TRISO) fuel kernels and overcoatings; compacting pebbles/prisms for high-temperature gas reactors; qualifying fuel performance under irradiation test programs; scaling fuel-form production lines for advanced reactor orders.
- distinct_from: `theme:haleu_advanced_fuel_supply` — enrichment supply vs fuel-form manufacture; distinct from `theme:fuel_cycle` — advanced fuel forms vs legacy pellet/assembly cycle.
- exclusions: light-water fuel assemblies (separate row); reactor design (reactor_technology).
- china_relevance: high — China operates HTGR-class high-temperature reactors with domestic coated-fuel lines (中国核能行业协会蓝皮书).
- confidence: medium
- sources: Idaho National Laboratory / U.S. DOE, Advanced Gas Reactor (AGR) fuel program publications; IAEA, "Advances in Small Modular Reactor Technology Developments" (supplement series); 中国核能行业协会, 《中国核能发展报告》蓝皮书.

### theme:fuel_assembly_fabrication
- id: `theme:fuel_assembly_fabrication` · name_en: "Nuclear fuel assembly fabrication" · name_zh: "核燃料组件制造" · value_chain_position: upstream · parent_sub_theme: `theme:advanced_nuclear_fuel_chain`
- defining_activities: converting enriched UF6 into UO2 powder and pellets; pressing/sintering pellets and fabricating cladding into fuel rods; assembling rods into PWR/BWR fuel assemblies under nuclear QA programs; delivering reload batches under utility contracts.
- distinct_from: `theme:fuel_cycle` (existing) — the existing row is scoped mining-through-enrichment; this is the fabrication tail converting enriched product into qualified assemblies.
- exclusions: enrichment itself (fuel_cycle / HALEU rows); TRISO forms (separate row).
- china_relevance: high — domestic fuel fabrication is self-sufficiency core for Chinese reactor fleets (中国核能行业协会蓝皮书).
- confidence: high
- sources: IAEA, Nuclear Energy Series (nuclear fuel cycle reports); OECD-NEA / IAEA "Red Book" (fuel-cycle stage framing); World Nuclear Association, "The Nuclear Fuel Report".

### theme:medical_isotope_production
- id: `theme:medical_isotope_production` · name_en: "Medical isotope production" · name_zh: "医用同位素生产" · value_chain_position: downstream · parent_sub_theme: `theme:next_gen_nuclear`
- defining_activities: irradiating targets in reactors/accelerators for Mo-99, iodine and other medical isotopes; processing and distributing isotopes under GMP; building dedicated isotope production reactors; contracting hospital radiopharmacy supply chains.
- distinct_from: `theme:npp_operations` — isotope irradiation/processing services vs power generation; a distinct product line on nuclear infrastructure.
- exclusions: radiopharmaceutical drug development (healthcare themes); power reactors without isotope programs.
- china_relevance: medium — 医用同位素自主供应 is a named Chinese program (原子能机构/卫健委 plan), domestic capacity still scaling.
- confidence: medium
- sources: IAEA, Nuclear Energy Series (radioisotope production reports); OECD-NEA, "The Supply of Medical Radioisotopes" report series; 国家原子能机构（CAEA）医用同位素发展规划文件.

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
- defining_activities: engineering 1000kV AC / ±800kV-class DC corridors; supplying UHV substations and converter stations as integrated packages; corridor EPC and system commissioning; UHV-standard equipment certification; UHV transformers/reactors/GIS engineering at 1000kV-class AC corridors; UHV standards and engineering know-how export
- distinct_from: theme:hv_transformers_switchgear — corridor SYSTEMS engineering vs the transformer/switchgear equipment class; distinct_from theme:transmission_hvdc_cabling — overhead UHV corridors vs HVDC cable links; distinct_from theme:hvdc_converter_stations — AC corridors vs DC converter terminals
- exclusions: distribution networks, individual equipment manufacture (existing rows)
- china_relevance: high — 特高压 is a signature Chinese grid-buildout category with its own standard system
- confidence: high
- sources: 《电力系统安全稳定导则》GB 38755-2019, 中国国家标准; "Electricity Grids and Secure Energy Transitions", IEA; CIGRE, technical brochures on UHV AC systems; 中国电力企业联合会, 《中国电力行业年度发展报告》; 国家能源局, 《新型电力系统发展蓝皮书》(2023)

### grid-protection-substation-automation
- id: theme:grid_protection_substation_automation
- name_en: Protection, relays & substation automation
- name_zh: 继电保护与变电站自动化
- value_chain_position: midstream
- parent_sub_theme: theme:transmission_equipment
- defining_activities: manufacturing protective relays and bay controllers; IEC 61850 digital-substation engineering; disturbance recording and fault-locating systems; wide-area protection scheme deployment; protection-settings and teleprotection commissioning; legacy-substation digital secondary retrofits
- distinct_from: theme:hv_transformers_switchgear — protection/control intelligence vs primary switching apparatus; distinct_from theme:grid_distribution_automation — substation/protection layer vs feeder automation
- exclusions: switchgear hardware, distribution feeders (existing rows)
- china_relevance: high — 继电保护 is a distinct domestic equipment-software segment with stable disclosure vocabulary
- confidence: high
- sources: IEC 61850 substation communication standard, IEC; IEEE power system relaying standards, IEEE PES; IEC, "IEC 61850" substation communication networks standard series; IEEE, power system relaying committee publications (e.g., protective relaying guides); 中国电力企业联合会, 《中国电力行业年度发展报告》

### facts-reactive-compensation
- id: theme:facts_reactive_compensation
- name_en: FACTS & reactive power compensation
- name_zh: 柔性交流输电与无功补偿（SVG/STATCOM）
- value_chain_position: midstream
- parent_sub_theme: theme:transmission_equipment
- defining_activities: manufacturing static VAR generators/STATCOMs; series-compensation and SVC engineering; harmonic filtering and power-quality plants; dynamic reactive support for renewable-heavy grids; synchronous condenser plants; dynamic reactive support for HVDC terminals and oscillation damping
- distinct_from: theme:hvdc_converter_stations — AC-side compensation electronics vs DC conversion; distinct_from theme:hv_transformers_switchgear — power-electronic compensation vs primary equipment
- exclusions: HVDC valves, substation protection
- china_relevance: high — SVG/无功补偿 is required vocabulary in Chinese renewable-integration coverage
- confidence: high
- sources: CIGRE Technical Brochures (compensation & power quality), CIGRE; IEEE FACTS application guides, IEEE PES; IEEE, "IEEE 1031" STATCOM planning/design guide; CIGRE, technical brochures on reactive power compensation (SC B4); 中国电力企业联合会, 《中国电力行业年度发展报告》

### transmission-substation-epc
- id: theme:transmission_substation_epc
- name_en: Transmission & substation engineering (EPC/design)
- name_zh: 输变电工程建设（EPC/电力设计院）
- value_chain_position: downstream
- parent_sub_theme: theme:transmission_equipment
- defining_activities: designing transmission lines and substations (design-institute work); EPC execution of grid corridors; geotechnical/routing and permitting services; commissioning and handover to grid operators; overhead/underground/submarine circuit construction (installation, not cable making); right-of-way, foundation and tower-erection campaigns
- distinct_from: theme:uhv_transmission — general grid EPC across voltage classes vs the UHV program class; distinct_from theme:grid_interconnection_services (data_center_power) — public-network works vs campus-dedicated access
- exclusions: equipment manufacture, grid operation
- china_relevance: high — 电力设计院/输变电EPC is the classic Chinese grid construction segment
- confidence: high
- sources: "Electricity Grids and Secure Energy Transitions", IEA; 中国电力企业联合会 (CEC) annual power-supply reports; IEA, "Electricity Grids and Secure Energy Transitions" (2023, buildout/lead-time analysis); U.S. DOE, "National Transmission Needs Study" (2023); 中国电力企业联合会, 《中国电力行业年度发展报告》

### grid-storage-integration
- id: theme:grid_storage_integration
- name_en: Grid-side storage integration
- name_zh: 储能系统集成（电网侧/独立储能电站）
- value_chain_position: downstream
- parent_sub_theme: theme:grid_digital_flexibility
- defining_activities: engineering standalone/grid-side battery storage plants; power-conversion system (PCS) and EMS integration; capacity-market and ancillary-service participation; storage-safety and augmentation services; hybrid renewable-plus-storage plant engineering; augmentation and warranty servicing regimes
- distinct_from: theme:dc_battery_backup (data_center_power) — grid asset participation vs facility ride-through; distinct_from theme:virtual_power_plants — utility-scale plant assets vs aggregated distributed load flexibility
- exclusions: battery cell/pack manufacture, datacenter backup batteries
- china_relevance: high — 电网侧/独立储能 is a major Chinese grid-investment category
- confidence: high
- sources: "Electricity Grids and Secure Energy Transitions", IEA; IEC 62933 electrical energy storage standards, IEC; IEA, "Batteries and Secure Energy Transitions" (2024); IEC, "IEC 62933" electrical energy storage standard series; 国家能源局, 《新型电力系统发展蓝皮书》(2023)

### virtual-power-plants
- id: theme:virtual_power_plants
- name_en: Virtual power plants & load aggregation
- name_zh: 虚拟电厂与负荷聚合
- value_chain_position: downstream
- parent_sub_theme: theme:grid_digital_flexibility
- defining_activities: aggregating distributed flexible loads and DERs; demand-response dispatch against grid signals; VPP platform operation and settlement; flexibility-market program participation; sub-second fleet telemetry dispatch; participant revenue settlement
- distinct_from: theme:grid_storage_integration — aggregated flexibility vs utility-scale storage assets; distinct_from theme:grid_dispatch_ems_software — market-facing aggregator services vs transmission dispatch software
- exclusions: utility dispatch centers, cell manufacturing
- china_relevance: high — 虚拟电厂 is now formal policy vocabulary in Chinese power-market reform documents
- confidence: high
- sources: "Electricity Grids and Secure Energy Transitions", IEA; 国家能源局 demand-response/virtual-pilot policy documents, 国家能源局 (NEA); U.S. DOE, "Pathways to Commercial Liftoff: Virtual Power Plants"; 国家能源局, 《新型电力系统发展蓝皮书》(2023); FERC, Order 2222 (DER aggregation in wholesale markets)

### ami-smart-metering
- id: theme:ami_smart_metering
- name_en: Smart metering & AMI systems
- name_zh: 智能电表与用电信息采集（AMI）
- value_chain_position: midstream
- parent_sub_theme: theme:grid_digital_flexibility
- defining_activities: manufacturing smart electricity meters; deploying head-end/data-collection systems; meter-data management and time-of-use settlement support; gas/water multi-utility metering adjacencies; data concentrators and remote connect/disconnect services; high-frequency consumption telemetry for DSO operations
- distinct_from: theme:grid_distribution_automation — the metering/data chain vs feeder automation equipment; distinct_from theme:grid_asset_monitoring — customer-end measurement vs network asset monitoring
- exclusions: distribution switchgear, dispatch software
- china_relevance: high — 用电信息采集/智能电表 is a mature Chinese grid-IT procurement category
- confidence: high
- sources: IEC 62056 (DLMS/COSEM) metering standard, IEC; 中国电力企业联合会 (CEC) annual power-supply reports; IEC, "IEC 62056 (DLMS/COSEM)" metering standard series; NIST, Smart Grid interoperability framework documents; 中国电力企业联合会, 《中国电力行业年度发展报告》

### grid-dispatch-ems-software
- id: theme:grid_dispatch_ems_software
- name_en: Grid dispatch & EMS software
- name_zh: 电网调度自动化系统（EMS）
- value_chain_position: enabler
- parent_sub_theme: theme:grid_digital_flexibility
- defining_activities: building energy management/SCADA platforms for grid control centers; state estimation and security-constrained dispatch; renewable forecasting integration; market-clearing and settlement software; DERMS integration for distributed-energy dispatch; network modeling (state estimation, power flow, contingency analysis)
- distinct_from: theme:grid_distribution_automation — the existing row was admitted precisely to fold in "grid software and distribution automation vendors" at the feeder level; this row isolates CONTROL-CENTER dispatch/EMS, a different mechanism (system-operation software vs feeder hardware/software); no vendor wording; distinct_from theme:dcim_energy_management (data_center_power) — control-center/grid-side software vs facility energy software
- exclusions: feeder automation hardware, VPP aggregator services
- china_relevance: high — 调度自动化 is a core domestic grid-software segment
- confidence: medium
- sources: 《电力监控系统安全防护规定》, 国家发展改革委; IEEE PES EMS/SCADA application guides, IEEE PES; IEC, "IEC 61970/61968" Common Information Model standard series; IEEE, "IEEE 2030" smart grid interoperability standards family; 中国电力企业联合会, 《中国电力行业年度发展报告》

### microgrid-solutions
- id: theme:microgrid_solutions
- name_en: Microgrids & campus energy systems
- name_zh: 微电网与园区能源系统
- value_chain_position: downstream
- parent_sub_theme: theme:grid_digital_flexibility
- defining_activities: engineering industrial-park and island microgrids; PV+storage+load coordination control; grid-connected/islanded transition management; microgrid energy contracting (EMC models); seamless grid-connect/island transition controllers; resilience-as-a-service operations
- distinct_from: theme:behind_meter_generation (data_center_power) — multi-asset microgrid systems vs generation procurement; distinct_from theme:grid_storage_integration — integrated campus systems vs standalone grid assets
- exclusions: utility distribution networks, cell manufacturing
- china_relevance: high — 微电网/源网荷储一体化 is standard Chinese park-energy policy vocabulary
- confidence: high
- sources: IEEE Std 1547 (DER interconnection), IEEE; 国家能源局 microgrid/park integrated-energy pilot documents, 国家能源局 (NEA); IEEE, "IEEE 2030.7 / 2030.8" microgrid controller standards; U.S. DOE, microgrid program reports; 国家能源局, 新能源微电网示范政策文件

### grid-asset-monitoring
- id: theme:grid_asset_monitoring
- name_en: Grid asset monitoring & intelligent inspection
- name_zh: 输电线路在线监测与智能巡检
- value_chain_position: downstream
- parent_sub_theme: theme:grid_digital_flexibility
- defining_activities: deploying line dynamic-rating and weather monitoring; drone/robotic corridor inspection services; transformer/partial-discharge condition monitoring; asset-health analytics for grid fleets; dynamic line-rating computation that raises usable transfer capacity; ratings integrated into EMS security-constrained dispatch with synced fault/oscillation sensing
- distinct_from: theme:ami_smart_metering — network asset telemetry vs customer metering; distinct_from theme:transmission_substation_epc — O&M services vs construction delivery
- exclusions: protection relays, metering hardware
- china_relevance: high — 输电线路智能巡检 is a visible Chinese grid-O&M digitization segment
- confidence: medium
- sources: CIGRE Technical Brochures (asset management & condition monitoring), CIGRE; 中国电力企业联合会 (CEC) annual power-supply reports; U.S. DOE, dynamic line rating studies/programs; CIGRE, technical brochures on dynamic rating (SC B2); IEEE, transmission & distribution committee publications on line ratings

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
- defining_activities: manufacturing AC/DC charging equipment; charging-network operation and roaming platforms; fleet/destination depot buildouts; V2G and managed-charging pilots; megawatt charging for heavy fleet depots; managed charging integrated with grid tariffs
- distinct_from: theme:grid_distribution_automation — charging loads/services vs feeder automation; distinct_from theme:rail_traction_electrification — road electrification vs railway traction power
- exclusions: EV manufacture, battery manufacturing
- china_relevance: high — 充电桩/充电运营 is a large, well-disclosed Chinese segment
- confidence: high
- sources: IEC 61851 conductive charging standard, IEC; GB/T 18487.1《电动汽车传导充电系统》, 中国国家标准; 国家能源局/中国电动汽车充电基础设施促进联盟, 充电基础设施年度运行数据; IEC, "IEC 61851" EV conductive charging standard series; IEA, "Global EV Outlook" (charging infrastructure chapters)

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
### theme:electrical_steel_core_materials
- id: `theme:electrical_steel_core_materials` · name_en: "Electrical steel & core materials" · name_zh: "电工钢（取向硅钢）铁芯材料" · value_chain_position: upstream · parent_sub_theme: `theme:transmission_equipment`
- defining_activities: producing grain-oriented electrical steel for transformer cores; slitting/stacking cores and wound-core fabrication; developing low-loss/high-permeability grades for efficient transformers; supplying amorphous and specialist core materials.
- distinct_from: `theme:hv_transformers_switchgear` (existing) — the core material input vs transformer/switchgear products; a recognized upstream bottleneck in transformer supply chains.
- exclusions: finished transformers/switchgear (existing row); non-electrical steel.
- china_relevance: high — 取向硅钢 is a large Chinese specialty-steel segment (行业协会/工信部 raw-material reporting).
- confidence: high
- sources: IEA, "Electricity Grids and Secure Energy Transitions" (2023, supply-chain chapters); 中国钢铁工业协会, 电工钢产品与市场报告; U.S. DOE, "National Transmission Needs Study" (2023, grid-hardware supply context).

### theme:hvdc_converter_stations
- id: `theme:hvdc_converter_stations` · name_en: "HVDC converter stations & valves" · name_zh: "换流站与换流阀" · value_chain_position: midstream · parent_sub_theme: `theme:transmission_equipment`
- defining_activities: manufacturing converter valves (LCC thyristor and VSC MMC topologies); engineering converter-station controls and cooling systems; supplying converter transformers and smoothing reactors; commissioning multi-terminal HVDC schemes; multi-terminal DC grid control and protection; offshore-wind export and interconnector delivery
- distinct_from: `theme:transmission_hvdc_cabling` (existing) — cable systems vs converter-station power electronics; the two halves of an HVDC link; distinct from `theme:uhv_transmission` — VSC technology class vs corridor programs (may co-exist on UHV-DC projects)
- exclusions: cable manufacture (existing row); HVAC substations (switchgear row).
- china_relevance: high — 换流阀/换流站 is core Chinese UHV program vocabulary (CEC/国网).
- confidence: high
- sources: CIGRE, technical brochures on HVDC systems (Study Committee B4); IEA, "Electricity Grids and Secure Energy Transitions" (2023); 中国电力企业联合会, 《中国电力行业年度发展报告》; CIGRE Technical Brochures (SC B4 DC systems & power electronics), CIGRE; "Electricity Grids and Secure Energy Transitions", IEA

### theme:advanced_overhead_conductors
- id: `theme:advanced_overhead_conductors` · name_en: "Advanced overhead conductors" · name_zh: "节能导线与复合材料导线" · value_chain_position: upstream · parent_sub_theme: `theme:transmission_equipment`
- defining_activities: manufacturing high-temperature/low-sag conductors (composite-core, zirconium alloys); developing lower-loss conductor grades for corridor upgrades; reconductoring existing lines to raise capacity without new rights-of-way; qualifying conductor hardware/fittings systems.
- distinct_from: `theme:transmission_hvdc_cabling` (existing) — underground/submarine insulated cable systems vs overhead bare conductors; distinct from `theme:grid_asset_monitoring` — conductor hardware vs rating sensors.
- exclusions: insulated power cable (existing row); copper rod/wire commodity (copper_wire_cable under copper_steel_electrify).
- china_relevance: high — 节能导线/碳纤维导线 is a named Chinese grid-materials category (CEC/国网物资 reporting).
- confidence: medium
- sources: CIGRE, technical brochures on overhead conductors (SC B2); U.S. DOE, "National Transmission Needs Study" (2023, advanced-conductor capacity context); 中国电力企业联合会, 《中国电力行业年度发展报告》.

### theme:grid_forming_inverter_technology
- id: `theme:grid_forming_inverter_technology` · name_en: "Grid-forming inverter technology" · name_zh: "构网型逆变器" · value_chain_position: enabler · parent_sub_theme: `theme:grid_digital_flexibility`
- defining_activities: engineering inverters that set voltage/frequency references autonomously (grid-forming control); qualifying IBR plants to new interconnection standards; retrofitting storage/wind/PV plants with grid-forming firmware; supplying synthetic inertia services to low-inertia grids.
- distinct_from: `theme:solar_inverters` (existing, solar) — PV plant inverter products (grid-following default) vs the grid-forming capability class now specified separately in grid codes; distinct from `theme:grid_storage_integration` — control technology vs the storage plants.
- exclusions: standard grid-following PV inverters (solar row); STATCOM/SVC hardware (reactive row).
- china_relevance: high — 构网型技术 is being deployed in Chinese high-renewables provinces (西藏/新疆 pilots, CEC reporting).
- confidence: medium
- sources: IEEE, "IEEE 2800-2022" interconnection standard for inverter-based resources; NERC, reliability guidelines for BPS-connected inverter-based resources; 中国电力企业联合会, 《中国电力行业年度发展报告》.

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
- defining_activities: growing monocrystalline ingots (CZ); diamond-wire slicing into wafers; kerf recycling and wafer thinning programs; large-wafer format transitions (182/210-class); feedstock upgrading/sideways purification into wafer grade; large-format wafer platform transitions (M10/G12-class)
- distinct_from: theme:polysilicon_solar_feedstock — converts feedstock INTO wafers vs producing the polysilicon itself; distinct_from theme:pv_cell_module_manufacturing — wafer input vs cell/module processing
- exclusions: polysilicon production, electronic-grade wafers (ai_semiconductors row)
- china_relevance: high — 拉棒/切片 is the standard Chinese solar upstream segment vocabulary
- confidence: high
- sources: "Trends in Photovoltaic Applications", IEA PVPS; "Photovoltaics Report", Fraunhofer ISE; ITRPV, "International Technology Roadmap for Photovoltaic" (wafering chapter); CPIA（中国光伏行业协会）, 《中国光伏产业发展路线图》; IEA, "Special Report on Solar PV Global Value Chains" (2022)

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
- defining_activities: developing perovskite single-junction and silicon-tandem stacks; stability/encapsulation qualification (ISOS protocols); pilot-line coating and laser scribing processes; tandem-cell certification pathways; coating/deposition scale-up (spin, slot-die, evaporation) to module area
- distinct_from: theme:advanced_cell_manufacturing — next-junction device class vs incumbent silicon platforms; distinct_from theme:pv_cell_module_manufacturing — device development vs mainstream manufacturing
- exclusions: silicon cell lines, module assembly
- china_relevance: high — 钙钛矿 is a prominent Chinese industrialization direction with pilot capacity
- confidence: medium
- sources: Best Research-Cell Efficiency Chart, NREL; "Photovoltaics Report", Fraunhofer ISE; NREL, perovskite database and efficiency-chart publications; ITRPV, "International Technology Roadmap for Photovoltaic" (emerging-technology chapter); Fraunhofer ISE, "Photovoltaics Report"

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
- sources: "Trends in Photovoltaic Applications", IEA PVPS; 中国光伏行业协会 (CPIA)《中国光伏产业发展路线图》; CPIA（中国光伏行业协会）, 《中国光伏产业发展路线图》(设备章节); ITRPV, "International Technology Roadmap for Photovoltaic" (process/equipment roadmaps); SEMI, photovoltaic standards program

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
- defining_activities: melting ultra-clear patterned/rolled PV glass; producing EVA/POE encapsulant films; backsheet and edge-seal materials; anti-reflective/durable glass coating lines; thin-glass and glass-glass formats for dual-glass modules
- distinct_from: theme:polysilicon_solar_feedstock — glass/film materials vs silicon feedstock; distinct_from theme:pv_cell_module_manufacturing — module materials vs module assembly
- exclusions: float architectural glass, wafer-level materials
- china_relevance: high — 光伏玻璃/胶膜 is a concentrated Chinese upstream segment with distinct capacity cycles
- confidence: high
- sources: IEC 61215 module qualification (materials context), IEC; 中国光伏行业协会 (CPIA) annual development reports; CPIA（中国光伏行业协会）, 《中国光伏产业发展路线图》; ITRPV, "International Technology Roadmap for Photovoltaic" (module materials chapter); IEA, "Special Report on Solar PV Global Value Chains" (2022)

### pv-silver-paste
- id: theme:pv_silver_paste
- name_en: Solar metallization paste & materials
- name_zh: 光伏银浆与金属化材料
- value_chain_position: upstream
- parent_sub_theme: theme:pv_upstream_materials
- defining_activities: formulating front/back silver pastes per cell platform; silver-reduction and copper-plating transition programs; firing-profile co-optimization with cell makers; paste yield and contact-resistance control; fine-line pastes for TOPCon/HJT contact systems; paste-screen-fire window qualification per cell architecture
- distinct_from: theme:pv_cell_module_manufacturing — cell consumable vs cell production; distinct_from theme:cmp_polishing_consumables (ai_semiconductors) — PV metallization chemistry vs CMP slurries
- exclusions: silver refining, module assembly
- china_relevance: high — 光伏银浆国产化 is a tracked import-substitution topic in Chinese solar coverage
- confidence: high
- sources: 中国光伏行业协会 (CPIA)《中国光伏产业发展路线图》; "Photovoltaics Report", Fraunhofer ISE; CPIA（中国光伏行业协会）, 《中国光伏产业发展路线图》(辅材章节); ITRPV, metalization chapter; Fraunhofer ISE, "Photovoltaics Report" (annual)

### quartz-crucibles-diamond-wire
- id: theme:quartz_crucibles_diamond_wire
- name_en: Quartz crucibles & wafering consumables
- name_zh: 石英坩埚与金刚线耗材
- value_chain_position: upstream
- parent_sub_theme: theme:pv_upstream_materials
- defining_activities: pulling fused-silica crucibles for CZ growth; producing diamond wire and guide wheels; slurry-free slicing consumable systems; crucible lifetime and contamination control; crucible purity/lifetime qualification for multi-load campaigns; inner-liner sand and crucible-scrap recycling
- distinct_from: theme:silicon_ingot_wafer_slicing — the consumable chain vs ingot/wafer production itself; distinct_from theme:large_diameter_silicon_wafers (ai_semiconductors) — PV-grade consumables vs electronic wafers
- exclusions: ingot growth, silicon purification
- china_relevance: high — 石英坩埚/金刚线 are established Chinese consumable categories with domestic champions
- confidence: high
- sources: "Photovoltaics Report", Fraunhofer ISE; 中国光伏行业协会 (CPIA) annual development reports; 中国有色金属工业协会硅业分会, 硅产业链市场报告系列; CPIA（中国光伏行业协会）, 《中国光伏产业发展路线图》(辅材章节); ITRPV, materials chapter

### utility-scale-pv-ipp
- id: theme:utility_scale_pv_ipp
- name_en: Utility-scale PV development & IPP
- name_zh: 集中式光伏电站开发与运营（IPP）
- value_chain_position: downstream
- parent_sub_theme: theme:pv_plant_development
- defining_activities: developing ground-mount utility projects; owning/operating generation fleets (IPP model); power-purchase and grid-parity contracting; project-finance structuring and asset rotation
- distinct_from: theme:distributed_pv_commercial_residential — utility ground-mount assets vs rooftop/C&I segments; distinct_from theme:pv_plant_om — asset ownership vs contracted O&M services; distinct_from theme:pv_project_development_epc — asset ownership vs contracted develop-and-build services
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
- distinct_from: theme:utility_scale_pv_ipp — distributed rooftop segments vs utility fleets; distinct_from theme:bipv_building_integration — mounted rooftop systems vs envelope-integrated products; distinct_from theme:pv_project_development_epc — channel/financing programs vs third-party EPC execution
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
- defining_activities: producing PV façade/roofing products; structural and fire-code qualification for envelope integration; design-in with architectural programs; curtain-wall and skylight system delivery; weatherproof mounting and electrical integration delivered with building envelope trades
- distinct_from: theme:distributed_pv_commercial_residential — envelope-integrated construction products vs mounted rooftop installations; distinct_from theme:pv_glass_encapsulants — finished building products vs material supply
- exclusions: conventional rooftop racking, façade glass without PV function
- china_relevance: medium — BIPV policy pull exists (整县推进 adjacency) but scale trails mounted distributed
- confidence: high
- sources: IEC 63092 BIPV standards activity, IEC; 中国光伏行业协会 (CPIA) annual development reports; IEA PVPS, Task 15 "Building Integrated PV" reports; Fraunhofer ISE, BIPV guidance publications; 住建部, 绿色建筑/光伏建筑一体化标准文件

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
- defining_activities: contracted O&M across PV fleets; drone/robot soiling and hot-spot inspection; generation-yield analytics and repowering; asset-management and performance-guarantee services; robotic module cleaning and inverter/tracker servicing; availability/PR guarantees under O&M contracts
- distinct_from: theme:utility_scale_pv_ipp — third-party O&M services vs asset ownership; distinct_from theme:grid_asset_monitoring (grid) — plant-scope services vs network-asset monitoring
- exclusions: EPC construction, asset ownership
- china_relevance: high — 电站运维 is a growing Chinese solar services segment as fleets age
- confidence: high
- sources: IEA PVPS Task 13 performance/reliability reports, IEA PVPS; IEC 62446 PV system documentation/commissioning standard, IEC; SolarPower Europe, "O&M Best Practice Guidelines"; IEA PVPS, Task 13 performance/reliability reports; NREL, "U.S. Solar Photovoltaic System and Energy Storage Cost Benchmark" (O&M cost lines)

### pv-recycling-circularity
- id: theme:pv_recycling_circularity
- name_en: Module recycling & circularity
- name_zh: 光伏组件回收与循环利用
- value_chain_position: downstream
- parent_sub_theme: theme:pv_plant_development
- defining_activities: delamination and material separation from retired modules; silver/silicon/glass recovery processes; reverse-logistics and compliance under WEEE-class rules; recycled-material resale into supply chains; high-value silicon and silver stream recovery; recycled-content certification under e-waste regimes
- distinct_from: theme:pv_plant_om — end-of-life processing vs operating-phase services; distinct_from theme:pv_glass_encapsulants — recovery vs primary material production
- exclusions: module manufacturing, plant O&M
- china_relevance: medium — 退役组件回收 is emerging Chinese policy territory as first-generation fleets age
- confidence: medium
- sources: IEA PVPS Task 12 end-of-life management reports, IEA PVPS; IRENA/IEA-PVPS "End-of-Life Management: Solar PV Panels"; IRENA / IEA-PVPS, "End-of-Life Management: Solar Photovoltaic Panels"; EU WEEE directive (PV collection/recovery) framework documents; CPIA（中国光伏行业协会）, 回收相关专题报告

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
- defining_activities: developing agricultural co-location projects (crop+PV); building reservoir/lake floating arrays; dual-use land/lease structuring; aquaculture-PV integrated operations; float/mooring/anchoring engineering for reservoirs; floating inverter/substation integration on platform arrays; elevated/bifacial arrays preserving crop machinery lanes; light/water/crop-yield trade-off co-management and dual-use land-classification outcomes
- distinct_from: theme:utility_scale_pv_ipp — dual-use siting formats vs conventional ground-mount; distinct_from theme:distributed_pv_commercial_residential — utility-adjacent water/agri formats vs rooftop
- exclusions: conventional ground-mount, offshore wind, offshore (marine) PV
- china_relevance: high — 农光互补/渔光互补 is native Chinese solar deployment vocabulary with large domestic fleets
- confidence: high
- sources: "Guideline for Agriphotovoltaics", Fraunhofer ISE; "Trends in Photovoltaic Applications", IEA PVPS; World Bank / SERIS, "Where Sun Meets Water: A Report on Floating Solar"; IEA PVPS, floating PV task reports; 国家能源局, 光伏发电建设运行统计（年度）; Fraunhofer ISE, "Agrivoltaics: Opportunities for Agriculture and the Energy Transition"; IEA PVPS, agrivoltaics task reports
### theme:thin_film_pv_modules
- id: `theme:thin_film_pv_modules` · name_en: "Thin-film PV modules (CdTe/CIGS)" · name_zh: "薄膜光伏组件" · value_chain_position: midstream · parent_sub_theme: none
- defining_activities: depositing CdTe/CIGS absorbers on glass at module scale; integrating front contacting and encapsulation in glass-glass laminates; qualifying thin-film yield/energy-yield vs c-Si benchmarks; running high-throughput glass-to-glass lines.
- distinct_from: `theme:perovskite_tandem_pv` — established compound thin-film production vs emerging perovskite systems; distinct from `theme:pv_cell_module_manufacturing` — non-silicon device mechanism.
- exclusions: a-Si (commercially marginal); c-Si modules.
- china_relevance: medium — 薄膜光伏 is a small domestic niche vs c-Si dominance (CPIA data), pilot lines only.
- confidence: medium
- sources: U.S. DOE, "Solar Photovoltaics Supply Chain Review" (2022, CdTe chapter); NREL, "U.S. Solar Photovoltaic System and Energy Storage Cost Benchmark" series; IEA, "Special Report on Solar PV Global Value Chains" (2022).

### theme:pv_project_development_epc
- id: `theme:pv_project_development_epc` · name_en: "PV project development & EPC" · name_zh: "电站开发与 EPC" · value_chain_position: downstream · parent_sub_theme: `theme:pv_plant_development`
- defining_activities: developing sites (land, interconnection, permitting); engineering and procuring utility-scale/distributed plants; constructing and commissioning PV power plants; selling plants/PPAs into operating portfolios.
- distinct_from: `theme:pv_plant_om` — build vs operate; distinct from `theme:solar_trackers_bos` (existing) — project execution vs BOS hardware supply; distinct from `theme:utility_scale_pv_ipp` — contracted develop-and-build execution vs asset ownership; distinct from `theme:distributed_pv_commercial_residential` — third-party EPC execution vs channel/financing programs
- exclusions: module/BOS/inverter manufacturing; O&M services (separate row).
- china_relevance: high — 电站开发/EPC is the core Chinese downstream segment (国家能源局 installation statistics).
- confidence: high
- sources: IEA PVPS, "Trends in Photovoltaic Applications" (annual); SolarPower Europe, "Global Market Outlook"; 国家能源局, 光伏发电建设运行统计（年度）.


## Union ledger
Union of lane A (`lane/gmi-micro-c1-20261021-r6`, PR #9978) and lane B (`lane/gmi-micro-c1-20261021-r9`). Spine = variant B: sub_theme scheme, ids and research sections are B's byte-for-byte except the exact edits recorded below. Every row remains a PROPOSAL (asserted_on 2026-10-21, nominated_from this record); nothing here ratifies. All decisions below were applied in rule order: exact-id overlap (rule 2), then the 25 seat-listed near pairs and the additional scan hits (rule 3), then grafts (rule 4).

**Exact-id overlaps (rule 2)**
- EXACT-OVERLAP kept=`theme:eda_design_automation` (B row + B section) — identical id in both variants; A's unique sources appended to the kept section where missing.
- EXACT-OVERLAP kept=`theme:enterprise_ssd_controllers` (B row + B section) — identical id in both variants; A's unique sources appended to the kept section where missing.
- EXACT-OVERLAP kept=`theme:pv_manufacturing_equipment` (B row + B section) — identical id in both variants; A's unique sources appended to the kept section where missing.
- EXACT-OVERLAP kept=`theme:semiconductor_ip_licensing` (B row + B section) — identical id in both variants; A's unique sources appended to the kept section where missing.
- EXACT-OVERLAP kept=`theme:spent_fuel_management` (B row + B section) — identical id in both variants; A's unique sources appended to the kept section where missing.

**Seat-listed near pairs (rule 3)**
- MERGE kept=`theme:ami_smart_metering` dropped=`theme:advanced_metering_infrastructure` — same AMI metering/head-end/MDM mechanism; kept B id, folded A's concentrator/remote-disconnect/DSO-telemetry detail.
- MERGE kept=`theme:advanced_packaging_equipment` dropped=`theme:advanced_packaging_assembly_equipment` — same back-end assembly equipment mechanism; kept B id, folded A's molding/underfill/reflow and alignment-accuracy detail.
- MERGE kept=`theme:bipv_building_integration` dropped=`theme:building_integrated_pv` — same BIPV envelope-product mechanism; kept B id, folded A's envelope-trade delivery detail.
- MERGE kept=`theme:cmp_planarization_equipment` dropped=`theme:cmp_polishing_equipment` — same CMP tool mechanism; kept B id, folded A's Cu/W/dielectric removal-rate and pad/conditioner detail.
- KEEP-BOTH (`theme:cmp_polishing_equipment` + `theme:cmp_polishing_consumables`) — genuinely distinct mechanisms/value-chain positions: polishing machine (midstream tool) vs slurry/pad consumables (upstream materials); the A equipment id merges into theme:cmp_planarization_equipment (previous pair) and the two B rows already name each other in distinct_from.
- MERGE kept=`theme:co_packaged_optics_integration` dropped=`theme:co_packaged_optics` — same CPO package-integration mechanism; kept B id, folded A's external-laser-source and SerDes-replacement link detail.
- MERGE kept=`theme:dcim_energy_management` dropped=`theme:dcim_energy_management_software` — same DCIM/energy-carbon software mechanism; kept B id, folded A's model-predictive cooling control.
- MERGE kept=`theme:embedded_storage_solutions` dropped=`theme:embedded_flash_storage_ufs` — same eMMC/UFS embedded-storage mechanism; kept B id, folded A's UFS revision qualification and OEM SKU supply.
- MERGE kept=`theme:ev_charging_infrastructure` dropped=`theme:ev_charging_networks` — same charger-equipment + network-operation mechanism; kept B id, folded A's megawatt charging and tariff-integrated managed charging.
- MERGE kept=`theme:agrivoltaics_floating_pv` dropped=`theme:floating_pv_systems` — B's dual-use siting row already covers floating arrays; kept B id, folded A's float/mooring engineering, survival design loads and floating electrical integration.
- NO-ACTION (`theme:floating_pv_systems` vs `theme:pv_manufacturing_equipment`) — false-positive token overlap: water-sited FPV plants vs PV line toolmakers are unrelated mechanisms; the A id is resolved by the pair-10 MERGE and the B equipment row is retained (kept above per the exact-overlap rule).
- MERGE kept=`theme:nuclear_grade_forgings_materials` dropped=`theme:heavy_component_forgings` — B's row is the broader nuclear-grade materials/forgings mechanism; kept B id, folded A's ultralarge-press capacity and forging QA/traceability.
- MERGE kept=`theme:hvdc_converter_stations` dropped=`theme:flexible_hvdc_converter_valves` — one converter-station mechanism; A's row states the more precise/complete mechanism (LCC + VSC-MMC topologies, full station BOM) so A's id is KEPT and B's flexible-HVDC row folded in; a VSC-only row would merely restate a slice of it.
- MERGE kept=`theme:ion_implant_equipment` dropped=`theme:ion_implant_doping_equipment` — same ion-implanter mechanism; kept B id, folded A's angle-control and charging-limit qualification.
- MERGE kept=`theme:niche_memory_products` dropped=`theme:niche_specialty_dram` — B's niche-memory row is the broader recognized product family (specialty DRAM + NOR/SLC NAND); kept B id, folded A's specialty-process and supply-cycle detail.
- MERGE kept=`theme:nuclear_heat_hydrogen` dropped=`theme:nuclear_heat_hydrogen_applications` — same non-electric nuclear applications mechanism; kept B id, folded A's extraction-steam district heat and chemical-park offtake.
- MERGE kept=`theme:npp_construction_epc` dropped=`theme:nuclear_plant_construction_epc` — same nuclear EPC mechanism; kept B id, folded A's commissioning-to-fuel-load milestone delivery.
- MERGE kept=`theme:precision_air_conditioning` dropped=`theme:precision_air_handler_cooling` — same CRAC/CRAH white-space air cooling mechanism; kept B id, folded A's economizer/containment/retrofit detail.
- MERGE kept=`theme:processing_in_memory` dropped=`theme:processing_in_memory_devices` — same PIM compute mechanism; kept B id, folded A's PIM SKU/SDK and benchmark detail.
- MERGE kept=`theme:pv_glass_encapsulants` dropped=`theme:pv_glass_encapsulant_materials` — same PV glass/encapsulant materials mechanism; kept B id, folded A's thin-glass/glass-glass format detail.
- MERGE kept=`theme:facts_reactive_compensation` dropped=`theme:reactive_power_compensation` — same FACTS/reactive-compensation mechanism; kept B id, folded A's synchronous condensers and HVDC-terminal reactive support.
- MERGE kept=`theme:silicon_ingot_wafer_slicing` dropped=`theme:silicon_ingot_wafer_growth` — same ingot-growth/wafering mechanism; kept B id, folded A's feedstock upgrading and M10/G12 format detail.
- MERGE kept=`theme:semiconductor_ate` dropped=`theme:test_ate_equipment` — same ATE tester mechanism; kept B id, folded A's AI-device test envelopes and test-cell software.
- MERGE kept=`theme:conventional_island_equipment` dropped=`theme:turbine_island_equipment` — same conventional/turbine-island equipment mechanism; kept B id, folded A's MSR/secondary-cycle and rotor-blade lifecycle detail.
- MERGE kept=`theme:virtual_power_plants` dropped=`theme:virtual_power_plant_aggregation` — same VPP aggregation mechanism; kept B id, folded A's sub-second dispatch and participant settlement.

**Additional near-duplicates found by the mandated scan (same mechanism, different wording; token overlap < 0.5)**
- MERGE kept=`theme:wet_clean_equipment` dropped=`theme:wafer_cleaning_prep_equipment` — same wet-clean/surface-prep tool mechanism (wording mismatch beat the token heuristic); A's strongest defining activities and sources folded into the kept section.
- MERGE kept=`theme:coat_develop_track` dropped=`theme:coater_developer_tracks` — same coat/develop track mechanism; A's strongest defining activities and sources folded into the kept section.
- MERGE kept=`theme:epitaxy_thermal_equipment` dropped=`theme:epitaxial_growth_equipment` — B's row covers the epitaxy+thermal furnace family; A's epi row is the same mechanism; A's strongest defining activities and sources folded into the kept section.
- MERGE kept=`theme:epitaxy_thermal_equipment` dropped=`theme:thermal_anneal_equipment` — B's row covers the epitaxy+thermal furnace family; A's anneal row is the same mechanism; A's strongest defining activities and sources folded into the kept section.
- MERGE kept=`theme:photomask_manufacturing` dropped=`theme:photomask_maskshop_supply` — same merchant photomask/mask-shop mechanism; A's strongest defining activities and sources folded into the kept section.
- MERGE kept=`theme:refurbished_equipment_market` dropped=`theme:equipment_refurb_remarket` — same secondary/refurbished fab-tool market mechanism; A's strongest defining activities and sources folded into the kept section.
- MERGE kept=`theme:fab_automation_cim` dropped=`theme:fab_automation_amhs` — B's fab-automation row already covers AMHS inside the automation/CIM scope; a standalone AMHS row would duplicate it (B's exclusion of standalone hardware transport is updated by this fold); A's strongest defining activities and sources folded into the kept section.
- MERGE kept=`theme:fab_facility_systems` dropped=`theme:bulk_gas_chemical_delivery_systems` — B's facility row already covers bulk gas/chemical delivery systems; A's strongest defining activities and sources folded into the kept section.
- MERGE kept=`theme:advanced_node_foundry` dropped=`theme:leading_edge_foundry_manufacturing` — same advanced-node logic foundry mechanism (wording mismatch beat the token heuristic); A's strongest defining activities and sources folded into the kept section.
- MERGE kept=`theme:advanced_substrate_interposer` dropped=`theme:abf_package_substrate_supply` — same ABF substrate/interposer supply mechanism; A's strongest defining activities and sources folded into the kept section.
- MERGE kept=`theme:chiplet_partition_design` dropped=`theme:chiplet_multidie_compute` — same chiplet/multi-die design mechanism; A's strongest defining activities and sources folded into the kept section.
- MERGE kept=`theme:memory_module_manufacturing` dropped=`theme:memory_storage_module_assembly` — same memory/storage module assembly mechanism; A's strongest defining activities and sources folded into the kept section.
- MERGE kept=`theme:memory_interface_chips` dropped=`theme:dram_interface_chipsets` — same memory interface/companion-chip mechanism; A's strongest defining activities and sources folded into the kept section.
- MERGE kept=`theme:backup_generator_sets` dropped=`theme:generator_backup_power` — same standby genset mechanism; A's strongest defining activities and sources folded into the kept section.
- MERGE kept=`theme:dc_battery_backup` dropped=`theme:battery_backup_storage_ess` — same facility battery backup/ESS mechanism; A's strongest defining activities and sources folded into the kept section.
- MERGE kept=`theme:behind_meter_generation` dropped=`theme:fuel_cell_prime_power` — B's behind-meter row claims on-site generation siting incl. fuel cells; A's fuel-cell plant row is the same deployment mechanism; A's strongest defining activities and sources folded into the kept section.
- MERGE kept=`theme:behind_meter_generation` dropped=`theme:onsite_gas_turbine_power` — B's behind-meter row claims on-site generation siting incl. gas engines/turbines; A's gas-turbine row is the same deployment mechanism; A's strongest defining activities and sources folded into the kept section.
- MERGE kept=`theme:immersion_thermal_fluids` dropped=`theme:dielectric_coolant_fluids` — B's row is exactly dielectric fluids + TIMs; A's coolant-fluid row is the same consumable-chemistry mechanism; A's strongest defining activities and sources folded into the kept section.
- MERGE kept=`theme:immersion_thermal_fluids` dropped=`theme:thermal_interface_materials` — B's row is exactly dielectric fluids + TIMs; A's TIM row is the same consumable-materials mechanism; A's strongest defining activities and sources folded into the kept section.
- MERGE kept=`theme:thermal_rejection_heat_recovery` dropped=`theme:waste_heat_reuse` — B's row covers heat rejection incl. heat-pump waste-heat export; A's reuse row is the same heat-recovery/export mechanism; A's strongest defining activities and sources folded into the kept section.
- MERGE kept=`theme:dc_hvdc_power_architecture` dropped=`theme:medium_voltage_dc_architecture` — same DC bus power-architecture mechanism (B: 240/336V HVDC incl. integrated units; A: MV-to-rack DC); A's strongest defining activities and sources folded into the kept section.
- MERGE kept=`theme:busway_smart_pdu` dropped=`theme:power_busway_distribution` — same busway/rack power distribution mechanism; A's strongest defining activities and sources folded into the kept section.
- MERGE kept=`theme:nuclear_digital_ic` dropped=`theme:nuclear_i_c_dcs_systems` — same nuclear-grade digital I&C/DCS mechanism; A's strongest defining activities and sources folded into the kept section.
- MERGE kept=`theme:npp_operations` dropped=`theme:nuclear_plant_operations` — same nuclear plant operations mechanism; A's strongest defining activities and sources folded into the kept section.
- MERGE kept=`theme:reactor_decommissioning` dropped=`theme:decommissioning_waste_management` — B's row covers dismantling incl. waste packaging/disposal routing; A's row is the same decommissioning/back-end mechanism; A's strongest defining activities and sources folded into the kept section.
- MERGE kept=`theme:grid_protection_substation_automation` dropped=`theme:grid_protection_control_systems` — same protection-relay/substation secondary mechanism; A's strongest defining activities and sources folded into the kept section.
- MERGE kept=`theme:grid_dispatch_ems_software` dropped=`theme:grid_operating_software` — same control-center grid operating software mechanism (EMS/SCADA/DMS); A's strongest defining activities and sources folded into the kept section.
- MERGE kept=`theme:grid_storage_integration` dropped=`theme:grid_scale_battery_storage` — same grid-side BESS plant mechanism; A's strongest defining activities and sources folded into the kept section.
- MERGE kept=`theme:transmission_substation_epc` dropped=`theme:transmission_line_construction_epc` — B's row covers line+substation design/EPC; A's line-construction row is the same grid construction mechanism; A's strongest defining activities and sources folded into the kept section.
- MERGE kept=`theme:grid_asset_monitoring` dropped=`theme:dynamic_line_rating_sensors` — B's row already covers line dynamic-rating and weather monitoring; A's strongest defining activities and sources folded into the kept section.
- MERGE kept=`theme:microgrid_solutions` dropped=`theme:microgrid_systems_integration` — same microgrid systems mechanism; A's strongest defining activities and sources folded into the kept section.
- MERGE kept=`theme:uhv_transmission` dropped=`theme:ultra_hv_ac_transmission` — same UHV transmission mechanism (wording mismatch beat the token heuristic); A's strongest defining activities and sources folded into the kept section.
- MERGE kept=`theme:quartz_crucibles_diamond_wire` dropped=`theme:quartz_crucible_consumables` — B's row is the broader wafering-consumables chain incl. crucibles; A's crucible row is the same consumable mechanism; A's strongest defining activities and sources folded into the kept section.
- MERGE kept=`theme:pv_silver_paste` dropped=`theme:pv_metalization_pastes` — same PV metallization paste mechanism; A's strongest defining activities and sources folded into the kept section.
- MERGE kept=`theme:perovskite_tandem_pv` dropped=`theme:perovskite_tandem_photovoltaics` — same perovskite/tandem device mechanism; A's strongest defining activities and sources folded into the kept section.
- MERGE kept=`theme:agrivoltaics_floating_pv` dropped=`theme:agrivoltaic_dual_use_systems` — B's dual-use siting row already covers agricultural co-location; A's agrivoltaic row is the same land dual-use mechanism; A's strongest defining activities and sources folded into the kept section.
- MERGE kept=`theme:pv_recycling_circularity` dropped=`theme:pv_recycling_end_of_life` — same PV end-of-life recycling mechanism; A's strongest defining activities and sources folded into the kept section.
- MERGE kept=`theme:pv_plant_om` dropped=`theme:pv_operations_maintenance` — same PV plant O&M mechanism; A's strongest defining activities and sources folded into the kept section.

**Additional KEEP-BOTH pairs found by the mandated scan (distinct mechanisms; distinct_from cross-named)**
- KEEP-BOTH (`theme:software_defined_storage_platforms` + `theme:data_center_storage_systems`) — genuinely different mechanisms: storage control software platforms vs engineered all-flash/scale-out appliance systems.
- KEEP-BOTH (`theme:prefab_power_modules` + `theme:prefab_modular_datacenter`) — genuinely different product mechanisms: factory-integrated power-train modules (电力模组) vs whole-facility modular datacenter products (预制舱).
- KEEP-BOTH (`theme:system_level_test_services` + `theme:ai_chip_osat`) — genuinely different test-chain positions: system-level test specialty capacity vs conventional assembly/final-test (OSAT) services.
- KEEP-BOTH (`theme:pv_project_development_epc` + `theme:utility_scale_pv_ipp`) — genuinely different value-chain positions: contracted develop-and-build (EPC) services vs asset ownership (IPP).
- KEEP-BOTH (`theme:pv_project_development_epc` + `theme:distributed_pv_commercial_residential`) — genuinely different value-chain positions: third-party EPC execution vs channel/financing program models.

**Merge into the kept-A row**
- MERGE kept=`theme:hvdc_converter_stations` dropped=`theme:flexible_hvdc_converter_valves` — one converter-station mechanism; A's row states the fuller mechanism (LCC + VSC-MMC topologies, station BOM), so A's id is kept, B's flexible-HVDC activities/sources folded in, and the row is grafted with parent_sub_theme `theme:transmission_equipment`.

**Grafted A-only micros (rule 4) with their union parent_sub_theme**
- `theme:system_level_test_services` → parent_sub_theme: `theme:advanced_packaging_integration`
- `theme:optical_transceiver_modules` → parent_sub_theme: `theme:ai_network_fabric`
- `theme:network_offload_processors` → parent_sub_theme: `theme:ai_network_fabric`
- `theme:pcie_fabric_silicon` → parent_sub_theme: `theme:ai_network_fabric`
- `theme:edge_inference_processors` → parent_sub_theme: `none` (direct child of the theme)
- `theme:ai_power_delivery_silicon` → parent_sub_theme: `none` (direct child of the theme)
- `theme:ai_server_board_integration` → parent_sub_theme: `none` (direct child of the theme)
- `theme:lpdram_low_power_memory` → parent_sub_theme: `theme:memory_product_engineering`
- `theme:automotive_grade_memory` → parent_sub_theme: `theme:memory_product_engineering`
- `theme:nearline_hard_disk_drives` → parent_sub_theme: `theme:memory_product_engineering`
- `theme:tape_archival_storage` → parent_sub_theme: `theme:memory_product_engineering`
- `theme:cxl_memory_expansion_devices` → parent_sub_theme: `theme:memory_product_engineering`
- `theme:software_defined_storage_platforms` → parent_sub_theme: `theme:memory_product_engineering`
- `theme:probe_card_test_interfaces` → parent_sub_theme: `theme:semi_back_end_equipment`
- `theme:vacuum_subsystem_components` → parent_sub_theme: `theme:equipment_component_periphery`
- `theme:rf_power_matching_subsystems` → parent_sub_theme: `theme:equipment_component_periphery`
- `theme:prefab_power_modules` → parent_sub_theme: `theme:datacenter_power_chain`
- `theme:haleu_advanced_fuel_supply` → parent_sub_theme: `theme:advanced_nuclear_fuel_chain`
- `theme:triso_fuel_form_fabrication` → parent_sub_theme: `theme:advanced_nuclear_fuel_chain`
- `theme:fuel_assembly_fabrication` → parent_sub_theme: `theme:advanced_nuclear_fuel_chain`
- `theme:medical_isotope_production` → parent_sub_theme: `theme:next_gen_nuclear`
- `theme:electrical_steel_core_materials` → parent_sub_theme: `theme:transmission_equipment`
- `theme:hvdc_converter_stations` → parent_sub_theme: `theme:transmission_equipment`
- `theme:advanced_overhead_conductors` → parent_sub_theme: `theme:transmission_equipment`
- `theme:grid_forming_inverter_technology` → parent_sub_theme: `theme:grid_digital_flexibility`
- `theme:thin_film_pv_modules` → parent_sub_theme: `none` (direct child of the theme)
- `theme:pv_project_development_epc` → parent_sub_theme: `theme:pv_plant_development`

**Sub_themes carried over from A (no B sub_theme fits their members)**
- `theme:ai_network_fabric` (`AI Network Fabric`, under theme:ai_semiconductors) — members: `theme:optical_transceiver_modules`, `theme:network_offload_processors`, `theme:pcie_fabric_silicon`.
- `theme:equipment_component_periphery` (`Equipment Components & Periphery`, under theme:semicap_equipment) — members: `theme:vacuum_subsystem_components`, `theme:rf_power_matching_subsystems`.
- `theme:advanced_nuclear_fuel_chain` (`Advanced Nuclear Fuel Chain`, under theme:nuclear_power) — members: `theme:haleu_advanced_fuel_supply`, `theme:triso_fuel_form_fabrication`, `theme:fuel_assembly_fabrication`.

**Final counts**
- theme:ai_semiconductors: sub_themes 4, micro_themes 21 (14 from the B spine + 7 grafted from A)
- theme:memory_storage: sub_themes 1, micro_themes 18 (12 from the B spine + 6 grafted from A)
- theme:semicap_equipment: sub_themes 3, micro_themes 15 (12 from the B spine + 3 grafted from A)
- theme:data_center_power: sub_themes 3, micro_themes 15 (14 from the B spine + 1 grafted from A)
- theme:nuclear_power: sub_themes 4, micro_themes 15 (11 from the B spine + 4 grafted from A)
- theme:grid_electrification: sub_themes 3, micro_themes 19 (15 from the B spine + 4 grafted from A)
- theme:solar: sub_themes 2, micro_themes 18 (16 from the B spine + 2 grafted from A)

Union totals: 121 micro_themes + 20 sub_themes + 240 parents rows (B spine 95 micros → 94 after the one merged-away B row, plus 27 grafts). 
Both variants are fully represented: every A micro either survives as a distinct union row, was merged into its same-mechanism union row (strongest activities/exclusions/sources folded), or was an exact-id duplicate of a B row. The seat's 25 listed near pairs under-counted the true overlap: the mandated scan found 38 additional same-mechanism pairs (merged) plus 4 genuine KEEP-BOTH pairs. After reconciliation every kept row is mechanism-distinct and the union is decisively larger than either variant alone (A 92, B 95 → union 121; +60% of A's mechanism-distinct non-overlapping micros would be 111).

No issuers, tickers or constituents appear anywhere in this record; no vendor theme families were used as sources or nominators; `config/theme_crosswalk.yml` was not edited.
