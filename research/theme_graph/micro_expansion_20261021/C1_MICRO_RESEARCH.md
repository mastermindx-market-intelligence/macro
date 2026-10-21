# GMI micro-theme expansion C1 — compute, memory, equipment, power, nuclear, grid, solar

Status: DRAFT taxonomy content PROPOSED for seat ratification — this lane proposes rows only, never ratifies.
Commission: GMI COMPLETION seat (Fable Meta-CEO, Chairman commission 2026-10-21, "microthemes should immensely and aggressively go beyond the original masterplan").
Base commit: `ca7edbcf50df21bd321bffa3433e5f105d3335da` (origin/main). asserted_on: 2026-10-21. Lane: `lane/gmi-micro-c1-20261021-r6`.
Proposed rows file: `research/theme_graph/micro_expansion_20261021/C1_PROPOSED_ROWS.yaml`.
Scope law: display/navigation vocabulary only — no weights, no scores, no constituents, no tickers, no issuer names anywhere in row content. Existing rows are never renamed or re-id'd. No vendor theme families (finviz / ths / tonghuashun, `ltheme:`, `basket:baskets_china_ths:*`) are used as sources or nominators. New rows ADD to existing micro-themes and state mechanism distinctness against the nearest existing row.

Totals proposed: 92 micro_themes + 19 sub_themes + 194 parent rows. Per theme: ai_semiconductors 13 · memory_storage 12 · semicap_equipment 15 · data_center_power 12 · nuclear_power 12 · grid_electrification 15 · solar 13.

---

## theme:ai_semiconductors — AI Semiconductors

Existing rows preserved: sub_theme `theme:ai_compute_silicon` (micros `theme:gpu_merchant_accelerators`, `theme:custom_asic_silicon`), micros `theme:hbm_packaging` (shared with memory_storage), `theme:ai_interconnect_silicon`.

**Sub-theme grouping.** The AI-semiconductor value chain runs design → manufacture → package/test → interconnect → deploy. Three new sub_themes group the additions: `theme:ai_manufacturing_chain` (the merchant make step: leading-edge foundry manufacturing, package-substrate supply, system-level test services) as midstream; `theme:ai_network_fabric` (the data-movement layer around the accelerator: optical transceivers, co-packaged optics, network offload processors, PCIe fabric silicon) as midstream; `theme:ai_design_enablement` (the toolchain that makes chips designable: EDA flows, semiconductor IP, chiplet/multi-die system engineering) as enabler. Three rows stay direct children of the theme: edge inference processors (downstream deployment), AI power-delivery silicon (enabler), and AI server board/system integration (downstream).

**Theme-tier candidates (prose only).** None. `ai_software` remains out of V1 scope per the C1 hierarchy record REJECTED table; AI-server thermal and facility power belong to data_center_power, not here.

### theme:leading_edge_foundry_manufacturing
- id: `theme:leading_edge_foundry_manufacturing` · name_en: "Leading-edge foundry manufacturing" · name_zh: "先进制程晶圆代工" · value_chain_position: midstream · parent_sub_theme: `theme:ai_manufacturing_chain`
- defining_activities: manufacturing customers' advanced-node (≤7nm-class) logic wafers on contract; qualifying new process nodes and design-rule shrunks; operating litho/etch/deposition tool fleets at wafer scale; managing advanced-node yield ramps and capacity allocation.
- distinct_from: `theme:gpu_merchant_accelerators` / `theme:custom_asic_silicon` — those are chip product/design programs; this is the merchant manufacturing step that fabricates them. Distinct from `theme:lithography_tools` (semicap): equipment sellers vs wafer manufacturers.
- exclusions: memory wafer fabrication (memory_storage); equipment makers (semicap_equipment); mature-node analog/mixed-signal foundry without AI-compute exposure.
- china_relevance: high — advanced-node foundry capacity is a declared national self-sufficiency priority (国家集成电路产业发展推进纲要 policy line).
- confidence: high
- sources: IEEE, "International Roadmap for Devices and Systems (IRDS)" (annual); SIA, "State of the U.S. Semiconductor Industry" (annual); BCG × SIA, "Strengthening the Global Semiconductor Supply Chain in an Uncertain Era" (2021).

### theme:abf_package_substrate_supply
- id: `theme:abf_package_substrate_supply` · name_en: "Package substrate (ABF) supply" · name_zh: "封装基板（载板）" · value_chain_position: upstream · parent_sub_theme: `theme:ai_manufacturing_chain`
- defining_activities: manufacturing fine-line build-up package substrates (ABF-class) for large compute dies; building multi-layer interposers and rigid/flex substrates; qualifying substrate geometries to flip-chip and 2.5D assembly line rules; capacity expansion on multi-year lead times.
- distinct_from: `theme:hbm_packaging` — HBM row is memory-cube stacking and packaging services; this row is the passive interconnect component (substrate) supplied into packaging. Distinct from `theme:wafer_fab_subsystems` (semicap): fab tool parts vs packaging component.
- exclusions: leadframes and low-pin-count substrates without AI-compute linkage; organic package materials chemistry (no house theme hosts process materials).
- china_relevance: high — 载板 is a named domestic-substitution layer in Chinese IC trade press and CCID reports.
- confidence: high
- sources: Yole Group, "Status of the Advanced Packaging Industry" (annual report series); 赛迪顾问（CCID Consulting）, 集成电路产业白皮书系列（封装基板章节）; IEEE IRDS, "Heterogeneous Integration" chapter.

### theme:system_level_test_services
- id: `theme:system_level_test_services` · name_en: "System-level test (SLT) services" · name_zh: "系统级测试服务" · value_chain_position: midstream · parent_sub_theme: `theme:ai_manufacturing_chain`
- defining_activities: executing post-assembly device test in system-like electrical/thermal conditions; running burn-in and stress screening on finished accelerators; providing contract test capacity with rapid fixture turnaround; feeding test data back into package and die yield models.
- distinct_from: `theme:process_metrology_inspection` (semicap, existing) — that is in-fab wafer process control; this is packaged-device functional test as a service. Distinct from `theme:test_ate_equipment` (proposed): testers for sale vs test capacity operated for hire.
- exclusions: wafer-sort-only test; ATE equipment manufacturing (semicap_equipment).
- china_relevance: medium — domestic OSAT expansion into SLT is an active trade-press theme; smaller than packaging itself.
- confidence: medium
- sources: IEEE, "International Test Conference (ITC)" proceedings; Semiconductor Engineering (trade press), test/system-level-test coverage; 中国半导体行业协会, 集成电路封测行业运行情况报告.

### theme:chiplet_multidie_compute
- id: `theme:chiplet_multidie_compute` · name_en: "Chiplet & multi-die compute systems" · name_zh: "芯粒（Chiplet）多裸片计算" · value_chain_position: midstream · parent_sub_theme: `theme:ai_design_enablement`
- defining_activities: partitioning large compute products into multiple manufactured dies; implementing die-to-die interfaces on standard interconnect specifications; sourcing dies from mixed process nodes and vendors and integrating them in one package; licensing chiplet architectures and reference flows.
- distinct_from: `theme:custom_asic_silicon` — ASIC row is monolithic custom compute silicon; this row is multi-die partitioning with explicit die-to-die interconnect (UCIe-class). Distinct from `theme:hbm_packaging` — memory stacking vs compute-die integration.
- exclusions: single-die ASIC/GPU products; pure memory stacking (hbm_packaging).
- china_relevance: medium — chiplet is the declared advanced-packaging path where leading-edge litho is constrained (Chinese trade press: 先进封装/芯粒).
- confidence: medium
- sources: UCIe Consortium, "Universal Chiplet Interconnect Express (UCIe) Specification" 1.0+; IEEE IRDS, "Heterogeneous Integration" chapter; Yole Group, advanced packaging report series.

### theme:optical_transceiver_modules
- id: `theme:optical_transceiver_modules` · name_en: "Optical transceiver modules" · name_zh: "光模块" · value_chain_position: midstream · parent_sub_theme: `theme:ai_network_fabric`
- defining_activities: manufacturing pluggable optical transceivers (400G/800G/1.6T-class) for cluster networking; packaging lasers, photodetectors and DSPs into module form factors; qualifying optical/electrical interfaces to multi-source agreements; scaling module test capacity with AI cluster shipments.
- distinct_from: `theme:ai_interconnect_silicon` (existing) — electrical switch/SerDes silicon vs the photonic-electronic conversion module (TOSA/ROSA/DSP) at the link's ends.
- exclusions: switch ASICs (ai_interconnect_silicon); undersea/telecom long-haul systems without data-center demand linkage; bare optical components with no module integration.
- china_relevance: high — China is the dominant global manufacturing base for data-center optical modules (光模块), a standing 中国半导体行业协会/CCID trade line.
- confidence: high
- sources: Optical Internetworking Forum (OIF), implementation agreements for 800G-class links; Ethernet Alliance, "Ethernet Roadmap" (annual); 中国半导体行业协会光电组件分会（光模块行业报告系列）.

### theme:co_packaged_optics
- id: `theme:co_packaged_optics` · name_en: "Co-packaged optics (CPO)" · name_zh: "共封装光学（CPO）" · value_chain_position: midstream · parent_sub_theme: `theme:ai_network_fabric`
- defining_activities: integrating photonic engines onto the switch/accelerator package beside the ASIC; engineering fiber attach and external laser sources at package level; co-designing electricalSerDes-replacing optical links into package assembly flows; qualifying reliability of photonic-integrated packages.
- distinct_from: `theme:optical_transceiver_modules` — front-panel pluggable modules vs photonics integrated into the switch package. Distinct from `theme:ai_interconnect_silicon` — the optics layer vs the switch silicon.
- exclusions: pluggable modules (separate row); telecom coherent optics; passive fiber/cable assemblies.
- china_relevance: medium — CPO is an active Chinese research/manufacturing investment theme but pre-mainstream (trade press: 共封装光学).
- confidence: medium
- sources: OIF, CPO-related implementation agreements and white papers; IEEE, optical interconnect sessions / "Journal of Lightwave Technology" industry surveys; Ethernet Alliance, "Ethernet Roadmap".

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

### theme:eda_design_automation
- id: `theme:eda_design_automation` · name_en: "EDA design automation software" · name_zh: "EDA 设计自动化软件" · value_chain_position: enabler · parent_sub_theme: `theme:ai_design_enablement`
- defining_activities: licensing logic synthesis, place-and-route and physical verification toolchains; providing AI-specific design flows (multi-die assembly, thermal/electrical co-analysis); selling emulation/fPGA prototyping capacity for accelerator verification; maintaining foundry-certified process design kits.
- distinct_from: `theme:ai_compute_silicon` (existing) — design toolchain enablers vs the silicon products the tools help design.
- exclusions: general-purpose enterprise software; semiconductor manufacturing equipment; IP block licensing (separate row).
- china_relevance: high — 国产EDA substitution is an explicit national priority (国家集成电路政策与CCID报告).
- confidence: high
- sources: IEEE IRDS, "Design" chapter; SIA, "State of the U.S. Semiconductor Industry" (annual); 赛迪顾问（CCID）, 中国EDA产业白皮书系列.

### theme:semiconductor_ip_licensing
- id: `theme:semiconductor_ip_licensing` · name_en: "Semiconductor IP licensing" · name_zh: "半导体 IP 授权" · value_chain_position: enabler · parent_sub_theme: `theme:ai_design_enablement`
- defining_activities: licensing processor interconnect and interface IP blocks (SerDes/PHY, memory controllers); delivering foundation IP certified to foundry nodes; providing layout hardening and IP integration services; collecting per-unit royalties on shipped designs.
- distinct_from: `theme:eda_design_automation` — reusable design blocks under license vs tools that manipulate designs. Distinct from `theme:custom_asic_silicon` — IP is licensed for others' chips, not shipped as silicon.
- exclusions: EDA software; chiplet-to-die standards (chiplet row); design services building full chips (custom_asic row).
- china_relevance: medium — domestic IP portfolio building is a recurring China IC policy theme, smaller than EDA.
- confidence: medium
- sources: IEEE IRDS, "Design" and "Beyond CMOS" chapters; BCG × SIA, "Strengthening the Global Semiconductor Supply Chain in an Uncertain Era" (2021); 赛迪顾问（CCID）集成电路IP专题报告.

### theme:edge_inference_processors
- id: `theme:edge_inference_processors` · name_en: "Edge inference processors (NPUs)" · name_zh: "端侧 AI 推理芯片" · value_chain_position: downstream · parent_sub_theme: none (direct child of theme)
- defining_activities: designing neural processing units for smartphones, PCs, vehicles and cameras; optimizing integer/low-precision inference at milliwatt-to-tens-of-watts budgets; integrating NPU IP with camera/display and connectivity subsystems; shipping device-side model-compiler toolchains.
- distinct_from: `theme:gpu_merchant_accelerators` — datacenter rack-scale accelerators vs device-scale inference silicon.
- exclusions: datacenter training/inference accelerators; general application processors without an NPU story; robotics perception (machine_vision under robotics_automation).
- china_relevance: high — 端侧AI芯片 is a flagship domestic design segment (AI phone/PC/vehicle silicon, trade press: 端侧算力).
- confidence: high
- sources: IEEE IRDS, "Mobile/edge" roadmap content; MLPerf (MLCommons), "MLPerf Inference: Edge" benchmark categories; 中国半导体行业协会, 集成电路设计行业运行情况.

### theme:ai_power_delivery_silicon
- id: `theme:ai_power_delivery_silicon` · name_en: "AI power-delivery silicon" · name_zh: "AI 供电电源芯片" · value_chain_position: enabler · parent_sub_theme: none (direct child of theme)
- defining_activities: building multiphase voltage regulators and vertical power stages feeding accelerator cores; integrating power-management ICs with telemetry for per-die power capping; developing on-package integrated voltage regulators for sub-volt rails; co-designing power stages for rising rack power density.
- distinct_from: `theme:ups_power_conversion` (data_center_power, existing) — facility-scale conversion/UPS vs package/board-level power silicon. Distinct from `theme:hv_transformers_switchgear` — grid/campus hardware vs chip-level converters.
- exclusions: facility UPS, busway, transformers (data_center_power); wide-bandgap module markets without AI-compute linkage.
- china_relevance: medium — 电源管理芯片国产化 is an active CCID/协会 theme, mid-scale.
- confidence: medium
- sources: IEEE, "Applied Power Electronics Conference (APEC)" proceedings; IEEE IRDS, power-delivery related chapters; 中国半导体行业协会, 电源管理芯片市场报告（协会/CCID 系列）.

### theme:ai_server_board_integration
- id: `theme:ai_server_board_integration` · name_en: "AI server board & system integration" · name_zh: "AI 服务器板卡与整机" · value_chain_position: downstream · parent_sub_theme: none (direct child of theme)
- defining_activities: designing accelerator carrier boards and baseboards to OCP-class specifications; integrating 4/8-GPU server SKUs with power, thermal and fabric topologies; manufacturing/assembly at scale for cloud and enterprise buyers; validating system firmware and rack-scale interop.
- distinct_from: `theme:gpu_merchant_accelerators` — the accelerator chip vs the boards/servers that host it. Distinct from the data_center_power rows (`theme:ups_power_conversion`, `theme:hv_transformers_switchgear`) — compute enclosure vs power infrastructure.
- exclusions: facility power/cooling (data_center_power); chip design (compute-silicon rows); hyperscale cloud services (out of taxonomy scope).
- china_relevance: high — China is a leading manufacturing base for AI servers (服务器板卡/整机, CCID/协会 standing line).
- confidence: high
- sources: Open Compute Project, "Open Rack" and server specification family; Uptime Institute, "Global Data Center Survey" (infrastructure context); 赛迪顾问（CCID）, 中国AI服务器市场报告系列.

### theme:ai_manufacturing_chain (sub_theme)
- id: `theme:ai_manufacturing_chain` · name_en: "AI Chip Manufacturing Chain" · name_zh: "AI 芯片制造链" · value_chain_position: midstream
- note: Groups the merchant make step — foundry manufacturing, package substrates, system-level test — distinct from the compute-silicon product sub_theme.
- nominated_from: research:research/theme_graph/micro_expansion_20261021/C1_MICRO_RESEARCH.md
- parent: theme:ai_semiconductors

### theme:ai_network_fabric (sub_theme)
- id: `theme:ai_network_fabric` · name_en: "AI Network Fabric" · name_zh: "AI 网络互连" · value_chain_position: midstream
- note: Groups the data-movement layer around the accelerator — optics, co-packaged photonics, offload processors, PCIe fabric — distinct from electrical switch silicon.
- nominated_from: research:research/theme_graph/micro_expansion_20261021/C1_MICRO_RESEARCH.md
- parent: theme:ai_semiconductors

### theme:ai_design_enablement (sub_theme)
- id: `theme:ai_design_enablement` · name_en: "AI Chip Design Enablement" · name_zh: "AI 芯片设计赋能" · value_chain_position: enabler
- note: Groups the design toolchain — EDA flows, IP licensing, chiplet engineering — the enabler tier of the AI chip value chain.
- nominated_from: research:research/theme_graph/micro_expansion_20261021/C1_MICRO_RESEARCH.md
- parent: theme:ai_semiconductors

---

## theme:memory_storage — Memory, HBM & Storage

Existing rows preserved: micros `theme:hbm_packaging` (shared), `theme:conventional_dram`, `theme:nand_enterprise_storage`.

**Sub-theme grouping.** Two new sub_themes: `theme:memory_product_stack` (product classes by media and deployment: LPDDR/mobile, niche DRAM, embedded UFS/eMMC, automotive-grade memory, nearline HDD, tape archival, processing-in-memory, CXL expansion) as midstream; `theme:storage_stack_integration` (component and system layers: enterprise SSD controllers, module assembly, DRAM interface chipsets, software-defined storage platforms) as midstream-to-downstream. The existing three micros remain direct theme children.

**Theme-tier candidates (prose only).** None. A generic "semiconductor materials" theme candidate is noted once under semicap_equipment and would host memory precursors if the seat ever ratifies it.

### theme:lpdram_low_power_memory
- id: `theme:lpdram_low_power_memory` · name_en: "Low-power mobile memory (LPDDR)" · name_zh: "低功耗移动内存（LPDDR）" · value_chain_position: midstream · parent_sub_theme: `theme:memory_product_stack`
- defining_activities: manufacturing LPDDR5/5X-class DRAM for phones, tablets and AI PCs; co-packaging LPDRAM with application processors (PoP); qualifying low-voltage speed grades per JEDEC revisions; supplying AI-edge devices with increasing memory-per-device content.
- distinct_from: `theme:conventional_dram` (existing) — server/PC DDR DIMM path vs low-power mobile/packaged DRAM product class.
- exclusions: server RDIMMs; automotive-qualified memory programs (separate row); HBM (hbm_packaging).
- china_relevance: high — domestic DRAM capacity growth centers on LPDDR-class products (存储国产化, CCID/协会 standing line).
- confidence: high
- sources: JEDEC, "JESD209-5 Low Power Double Data Rate (LPDDR5)"; TrendForce / DRAMeXchange, memory market research series; 中国半导体行业协会存储行业报告（协会/CCID 系列）.

### theme:niche_specialty_dram
- id: `theme:niche_specialty_dram` · name_en: "Niche & specialty DRAM" · name_zh: "利基型存储器" · value_chain_position: midstream · parent_sub_theme: `theme:memory_product_stack`
- defining_activities: manufacturing legacy-node and specialty DRAM (SDR/DDR3-class, consumer DRAM) for set-top, networking and industrial buyers; running specialty processes (embedded-memory, small-batch) on trailing-edge nodes; serving connectivity and appliance markets with long product lifecycles; managing supply cycles disconnected from server DRAM.
- distinct_from: `theme:conventional_dram` — mainstream DDR4/DDR5 commodity vs trailing-edge specialty/consumer DRAM classes recognized separately in DRAM market research.
- exclusions: LPDDR (separate row); NAND families; SRAM/MCU embedded memory without DRAM mechanism.
- china_relevance: high — 利基存储 is a named Chinese memory-segment strategy (domestic niche-DRAM expansion).
- confidence: medium
- sources: TrendForce / DRAMeXchange, niche DRAM market research; 赛迪顾问（CCID）, 中国存储市场白皮书系列; JEDEC, legacy DDR standards (JESD79 family).

### theme:embedded_flash_storage_ufs
- id: `theme:embedded_flash_storage_ufs` · name_en: "Embedded flash storage (UFS/eMMC)" · name_zh: "嵌入式闪存（UFS/eMMC）" · value_chain_position: midstream · parent_sub_theme: `theme:memory_product_stack`
- defining_activities: manufacturing UFS and eMMC embedded flash for smartphones and connected devices; integrating NAND die with controllers into JEDEC-defined embedded packages; qualifying performance classes per UFS revisions; supplying device OEMs with soldered storage SKUs.
- distinct_from: `theme:nand_enterprise_storage` (existing) — enterprise SSD systems/datacenter NAND vs soldered embedded device storage in JEDEC UFS/eMMC form factors.
- exclusions: client/enterprise SSDs; removable media cards; raw NAND die trade.
- china_relevance: high — domestic NAND capacity and device ecosystem make 嵌入式存储 a core China segment.
- confidence: high
- sources: JEDEC, "Universal Flash Storage (UFS)" and "eMMC" standards (JESD220 family); TrendForce, mobile storage market research; 中国半导体行业协会存储行业报告.

### theme:automotive_grade_memory
- id: `theme:automotive_grade_memory` · name_en: "Automotive-grade memory" · name_zh: "车规级存储" · value_chain_position: midstream · parent_sub_theme: `theme:memory_product_stack`
- defining_activities: qualifying DRAM/NAND to automotive reliability regimes (AEC-Q100, ISO 26262 flows); supplying infotainment, ADAS and telematics memory with long-term availability commitments; running automotive-grade temperature/lifetime screening; supporting functional-safety documentation for carmakers.
- distinct_from: `theme:lpdram_low_power_memory` — same media families but the qualification/availability regime (车规认证) is the distinct market mechanism and product line.
- exclusions: consumer-grade memory sold into vehicles without automotive qualification; automotive compute SoCs (no memory mechanism).
- china_relevance: high — 汽车存储 is a fast-growing named segment in Chinese auto-electronics trade press.
- confidence: medium
- sources: Automotive Electronics Council, "AEC-Q100" failure-mechanism-based qualification; ISO, "ISO 26262 Road vehicles — Functional safety"; 中国汽车工业协会车规电子相关行业报告.

### theme:nearline_hard_disk_drives
- id: `theme:nearline_hard_disk_drives` · name_en: "Nearline hard disk drives (HDD)" · name_zh: "近线机械硬盘" · value_chain_position: midstream · parent_sub_theme: `theme:memory_product_stack`
- defining_activities: manufacturing high-capacity nearline drives (PMR/SMR, helium-filled) for hyperscale cold and warm data; developing energy-assisted recording (HAMR/MAMR) areal-density roadmaps; selling exabyte-scale capacity into cloud storage pools; servicing drive fleet reliability programs.
- distinct_from: `theme:nand_enterprise_storage` — magnetic recording media vs flash; the AI-memory-cycle framing in the existing row is NAND-centric.
- exclusions: consumer/desktop drives; SSDs; tape (separate row).
- china_relevance: medium — HDD manufacturing is offshore; Chinese demand (hyperscale/archive) is the relevance, not domestic production.
- confidence: high
- sources: IDEMA, hard-drive industry standards body publications; TrendForce, enterprise storage market research; SNIA, storage industry technical work (HDD/SMR working content).

### theme:tape_archival_storage
- id: `theme:tape_archival_storage` · name_en: "Tape archival storage" · name_zh: "磁带归档存储" · value_chain_position: midstream · parent_sub_theme: `theme:memory_product_stack`
- defining_activities: manufacturing LTO-class tape cartridges and drives for cold archives; operating sequential-access libraries for hyperscale and media archives; advancing cartridge capacity per LTO roadmap generations; supplying air-gapped backup media for ransomware-resilient archives.
- distinct_from: `theme:nearline_hard_disk_drives` — sequential tape library economics vs random-access disk; distinct cost-per-TB cold tier.
- exclusions: HDD; optical disc; consumer backup services.
- china_relevance: medium — 磁带存储 in China is a niche archive tier (domestic demand rising with data-regulation retention).
- confidence: medium
- sources: LTO Consortium, "LTO Ultrium technology roadmap"; SNIA, "Solid State Storage / archival" technical publications.

### theme:processing_in_memory_devices
- id: `theme:processing_in_memory_devices` · name_en: "Processing-in-memory (PIM) devices" · name_zh: "存算一体（PIM）" · value_chain_position: midstream · parent_sub_theme: `theme:memory_product_stack`
- defining_activities: embedding compute logic inside DRAM/HBM stacks to cut data movement; shipping PIM-enabled memory SKUs with vendor SDKs; co-designing models/runtimes for near-memory execution; publishing PIM benchmarks with AI framework integrations.
- distinct_from: `theme:conventional_dram` — compute-capable memory vs standard DRAM; distinct from `theme:chiplet_multidie_compute` (ai_semiconductors) — compute in the memory stack vs compute-die partitioning.
- exclusions: near-memory accelerators on standard DIMMs without in-stack logic; pure HBM bandwidth products.
- china_relevance: medium — 存算一体 is an active domestic research/startup field, pre-scale.
- confidence: low
- sources: IEEE IRDS, memory and "Beyond CMOS"/new-compute chapters; IEEE, PIM literature (e.g., ISCA/MICRO industry-track papers); JEDEC, HBM3 standard (JESD238) context for in-stack logic.

### theme:cxl_memory_expansion_devices
- id: `theme:cxl_memory_expansion_devices` · name_en: "CXL memory expansion & pooling devices" · name_zh: "CXL 内存扩展与池化" · value_chain_position: midstream · parent_sub_theme: `theme:memory_product_stack`
- defining_activities: building CXL-attached memory expansion units decoupled from host DIMM slots; implementing memory pooling/sharing switches and controllers on CXL protocols; qualifying Type-3 device latency and metadata handling; enabling composable memory for AI servers.
- distinct_from: `theme:conventional_dram` — DDR5 DIMMs vs CXL-attached expansion/pooling appliances; distinct from `theme:pcie_fabric_silicon` (ai_semiconductors) — memory-protocol endpoints vs generic PCIe fabric.
- exclusions: standard RDIMMs; DPU offload (separate row); SSDs presented over CXL as storage.
- china_relevance: medium — CXL 池化 is an early server-ecosystem theme in Chinese data-center trade press.
- confidence: medium
- sources: CXL Consortium, "Compute Express Link Specification" (memory Type-3/pooling); JEDEC, DDR5/MRDIMM-adjacent standards (JESD79-5, sideband/MR modules); SNIA, composable-infrastructure technical work.

### theme:enterprise_ssd_controllers
- id: `theme:enterprise_ssd_controllers` · name_en: "Enterprise SSD controllers" · name_zh: "企业级 SSD 主控芯片" · value_chain_position: enabler · parent_sub_theme: `theme:storage_stack_integration`
- defining_activities: designing SSD controller SoCs with NVMe/ECC/FTL pipelines; licensing controller IP and firmware to drive makers; qualifying controllers against enterprise workload classes; developing QLC-capable and ZNS firmware generations.
- distinct_from: `theme:nand_enterprise_storage` (existing) — the basket row frames NAND and storage systems; this row is the controller silicon/firmware component layer.
- exclusions: NAND die manufacturing; finished SSD modules (module assembly row); storage software platforms (separate row).
- china_relevance: high — SSD主控国产化 is a standing Chinese storage-industry theme (协会/CCID).
- confidence: high
- sources: NVM Express, Inc., "NVM Express Base Specification"; SNIA, Solid State Storage Initiative technical work; 中国半导体行业协会/赛迪顾问, SSD主控芯片产业报告.

### theme:memory_storage_module_assembly
- id: `theme:memory_storage_module_assembly` · name_en: "Memory & storage module assembly" · name_zh: "内存与存储模组制造" · value_chain_position: midstream · parent_sub_theme: `theme:storage_stack_integration`
- defining_activities: assembling DRAM modules (RDIMM/MRDIMM) and SSDs from dies and controllers; branding and channel-distributing module SKUs; firmware integration and burn-in screening at module level; channel inventory management across memory price cycles.
- distinct_from: `theme:dram_interface_chipsets` — module assembly vs companion-chip silicon. Distinct from `theme:nand_enterprise_storage` — assembly/branding layer vs the basket's NAND-and-systems framing.
- exclusions: wafer fabrication; controller design (separate row); raw-die distribution.
- china_relevance: high — 存储模组 is a large, competitive Chinese segment (内存条/SSD 模组厂, trade press standard vocabulary).
- confidence: high
- sources: JEDEC, RDIMM/MRDIMM module standards (JESD family); TrendForce, module/DRAM module market research; 中国半导体行业协会存储行业报告.

### theme:dram_interface_chipsets
- id: `theme:dram_interface_chipsets` · name_en: "DRAM interface & companion chipsets" · name_zh: "内存接口及配套芯片" · value_chain_position: enabler · parent_sub_theme: `theme:storage_stack_integration`
- defining_activities: manufacturing register clock drivers, data buffers and SPD hub chips for DDR5/MRDIMM modules; shipping module power-management and temperature-sensor companions; qualifying chipsets against JEDEC module specs with memory makers; moving into CKD (clock driver) generations for high-speed DDR5.
- distinct_from: `theme:memory_storage_module_assembly` — companion silicon on the module vs module assembly; distinct from `theme:conventional_dram` — enabling chips vs the DRAM die itself.
- exclusions: DRAM die; SSD controllers; module assembly.
- china_relevance: high — 内存接口芯片 is a globally significant Chinese-led segment (trade press: 内存接口芯片).
- confidence: high
- sources: JEDEC, DDR5 RDIMM/MRDIMM module and companion-chip standards (JESD79-5 family and sideband function specs); 中国半导体行业协会, 内存接口芯片行业报告（协会/CCID 系列）.

### theme:software_defined_storage_platforms
- id: `theme:software_defined_storage_platforms` · name_en: "Software-defined storage platforms" · name_zh: "软件定义存储" · value_chain_position: downstream · parent_sub_theme: `theme:storage_stack_integration`
- defining_activities: building distributed storage control software over commodity hardware; virtualizing block/file/object pools into service catalogs; integrating tiering, erasure coding and data-reduction pipelines; licensing subscriptions across hybrid-cloud estates.
- distinct_from: `theme:nand_enterprise_storage` (existing) — storage control software vs NAND/storage hardware framing; complements `theme:enterprise_ssd_controllers` (silicon) with the platform-software layer.
- exclusions: hardware appliances as such; backup SaaS without storage-platform mechanism; database software.
- china_relevance: medium — 软件定义存储 is an established Chinese enterprise-IT category (信创 storage stacks).
- confidence: medium
- sources: SNIA, "Software Defined Storage" technical publications; CNCF / open-storage ecosystem foundation documentation (e.g., Cloud Native Storage landscape); 赛迪顾问（CCID）, 中国软件定义存储市场报告系列.

### theme:memory_product_stack (sub_theme)
- id: `theme:memory_product_stack` · name_en: "Memory Product Stack" · name_zh: "存储产品矩阵" · value_chain_position: midstream
- note: Groups product classes by media and deployment — LPDDR, niche DRAM, UFS/eMMC, automotive, HDD, tape, PIM, CXL — distinct from the HBM packaging slice.
- nominated_from: research:research/theme_graph/micro_expansion_20261021/C1_MICRO_RESEARCH.md
- parent: theme:memory_storage

### theme:storage_stack_integration (sub_theme)
- id: `theme:storage_stack_integration` · name_en: "Storage Stack Integration" · name_zh: "存储栈集成" · value_chain_position: downstream
- note: Groups component and system integration layers — controllers, module assembly, interface chipsets, software-defined platforms — downstream of wafer fabrication.
- nominated_from: research:research/theme_graph/micro_expansion_20261021/C1_MICRO_RESEARCH.md
- parent: theme:memory_storage

---

## theme:semicap_equipment — Semiconductor Equipment (WFE)

Existing rows preserved: sub_theme `theme:wfe_process_tools` (micros `theme:lithography_tools`, `theme:etch_deposition_equipment`, `theme:process_metrology_inspection`), micro `theme:wafer_fab_subsystems`.

**Sub-theme grouping.** The equipment value chain extends beyond the three named tool classes into (a) the remaining front-end process-tool families — added under the EXISTING sub_theme `theme:wfe_process_tools` (ion implant, CMP, thermal/anneal, clean/wet prep, coater-developer tracks, epitaxy); (b) back-end capital: new sub_theme `theme:advanced_packaging_test_equipment` (packaging assembly tools, ATE, probe cards); (c) the component/periphery supply behind toolmakers: new sub_theme `theme:equipment_component_periphery` (vacuum subsystems, RF power subsystems, photomask/mask-shop supply, refurbishment/remarket); and (d) fab automation and facility systems: new sub_theme `theme:fab_automation_facility_systems` (AMHS automation, bulk gas/chemical delivery).

**Theme-tier candidates (prose only).** A "semiconductor process materials" theme (photoresists, specialty gases, sputtering targets, wet chemicals, CMP slurries) is a genuine gap: these upstream consumables have no home theme today and were deliberately NOT added under semicap_equipment, which is an equipment theme. Flag for the seat as a possible new top-level theme; no row proposed here.

### theme:ion_implant_doping_equipment
- id: `theme:ion_implant_doping_equipment` · name_en: "Ion implant & doping equipment" · name_zh: "离子注入设备" · value_chain_position: midstream · parent_sub_theme: `theme:wfe_process_tools` (existing)
- defining_activities: manufacturing medium/high-energy ion implanters for dopant introduction; building plasma doping and implant-angle-control systems; qualifying dose uniformity and wafer charging limits; servicing beamline consumables and upgrades.
- distinct_from: `theme:etch_deposition_equipment` (existing) — material removal/addition vs dopant implantation; sibling tool family inside wfe_process_tools.
- exclusions: diffusion furnaces (thermal row); metrology of dopant profiles (metrology row).
- china_relevance: high — 离子注入机 is a headline 国产半导体设备 category (CCID/协会 equipment reports).
- confidence: high
- sources: SEMI, "World Fab Forecast" (tool-class coverage); IEEE IRDS, "Front End Processes" chapter; 赛迪顾问（CCID）, 中国半导体设备市场白皮书系列.

### theme:cmp_polishing_equipment
- id: `theme:cmp_polishing_equipment` · name_en: "CMP planarization equipment" · name_zh: "CMP 抛光设备" · value_chain_position: midstream · parent_sub_theme: `theme:wfe_process_tools` (existing)
- defining_activities: manufacturing chemical-mechanical polishers for global planarization; pairing polish platforms with in-situ endpoint metrology; qualifying removal-rate uniformity across copper/tungsten/dielectric steps; servicing pad/conditioner ecosystems.
- distinct_from: `theme:etch_deposition_equipment` — mechanical-chemical planarization vs etch/deposition chemistries.
- exclusions: CMP slurry/pad materials (no materials theme hosts them — flagged prose candidate).
- china_relevance: high — CMP设备国产化 is an active named category in Chinese equipment reporting.
- confidence: high
- sources: SEMI, "World Fab Forecast"; IEEE IRDS, "Front End Processes" chapter; 中国电子专用设备工业协会（CEPEIA）行业运行报告.

### theme:thermal_anneal_equipment
- id: `theme:thermal_anneal_equipment` · name_en: "Thermal processing & anneal equipment" · name_zh: "热处理与退火设备" · value_chain_position: midstream · parent_sub_theme: `theme:wfe_process_tools` (existing)
- defining_activities: manufacturing vertical furnaces, RTP and laser-anneal systems for dopant activation and film treatment; controlling oxidation/nitridation ambient chemistry; qualifying thermal budgets for advanced-node stacks; servicing heater and tube lifecycles.
- distinct_from: `theme:epitaxial_growth_equipment` — heat treatment of existing films vs ordered single-crystal film growth; sibling tool family inside wfe_process_tools.
- exclusions: implant (separate row); deposition chemistries (etch/deposition row).
- china_relevance: high — 炉管/退火设备国产化 is an active category (CEPEIA/CCID).
- confidence: high
- sources: SEMI, "World Fab Forecast"; IEEE IRDS, "Front End Processes" chapter; 中国电子专用设备工业协会（CEPEIA）行业运行报告.

### theme:wafer_cleaning_prep_equipment
- id: `theme:wafer_cleaning_prep_equipment` · name_en: "Wafer cleaning & surface-prep equipment" · name_zh: "清洗与湿法设备" · value_chain_position: midstream · parent_sub_theme: `theme:wfe_process_tools` (existing)
- defining_activities: manufacturing single-wafer and batch wet-cleaning systems; building dry-cleaning and bevel/polish prep tools; qualifying particle-removal and metallic-contamination specs; supplying high-throughput clean steps for every process level.
- distinct_from: `theme:etch_deposition_equipment` — surface preparation vs patterned material removal/addition.
- exclusions: wet-chemical formulations (materials flag); CMP (separate row).
- china_relevance: high — 清洗设备国产化 is one of the strongest domestic equipment categories (CCID standing line).
- confidence: high
- sources: SEMI, "World Fab Forecast"; SEMI International Standards (surface preparation/EHS-related standards program); 中国电子专用设备工业协会（CEPEIA）行业运行报告.

### theme:coater_developer_tracks
- id: `theme:coater_developer_tracks` · name_en: "Coater/developer tracks" · name_zh: "涂胶显影设备" · value_chain_position: midstream · parent_sub_theme: `theme:wfe_process_tools` (existing)
- defining_activities: manufacturing coat/bake/develop tracks coupled to exposure tools; controlling resist-film uniformity at advanced nodes; synchronizing track-exposure throughput (matched clusters); servicing wafer-handling and dispense subsystems.
- distinct_from: `theme:lithography_tools` (existing) — the exposure tool vs the paired pre/post-exposure track; distinct products recognized separately in fab toolcounts.
- exclusions: photoresist chemistry (materials flag); EUV light sources (inside litho tool scope).
- china_relevance: high — 涂胶显影机国产化 is an established domestic equipment line (CCID).
- confidence: high
- sources: SEMI, "World Fab Forecast"; IEEE IRDS, lithography integration chapters; 中国电子专用设备工业协会（CEPEIA）行业运行报告.

### theme:epitaxial_growth_equipment
- id: `theme:epitaxial_growth_equipment` · name_en: "Epitaxial growth equipment" · name_zh: "外延生长设备" · value_chain_position: midstream · parent_sub_theme: `theme:wfe_process_tools` (existing)
- defining_activities: manufacturing CVD/MOCVD epi reactors for silicon and compound epitaxy; growing selective epitaxy for source/drain and device-stack steps; qualifying epi thickness/dopant uniformity; servicing susceptors and precursors handling.
- distinct_from: `theme:thermal_anneal_equipment` — ordered crystal film growth vs anneal/diffusion treatment; distinct from `theme:etch_deposition_equipment` by epitaxial (single-crystal) mechanism.
- exclusions: GaN/SiC power-device epi without fab-WFE linkage (flag under materials/SiC prose); MBE research tools.
- china_relevance: high — 外延设备国产化 is an active domestic category (CEPEIA/CCID).
- confidence: high
- sources: SEMI, "World Fab Forecast"; IEEE IRDS, "Front End Processes" chapter; 中国电子专用设备工业协会（CEPEIA）行业运行报告.

### theme:advanced_packaging_assembly_equipment
- id: `theme:advanced_packaging_assembly_equipment` · name_en: "Advanced packaging & assembly equipment" · name_zh: "先进封装与组装设备" · value_chain_position: midstream · parent_sub_theme: `theme:advanced_packaging_test_equipment`
- defining_activities: manufacturing die-attach/bonders for flip-chip, 2.5D/3D and hybrid bonding; building TSV etch, plating and thin-wafer handling lines; supplying molding, underfill and reflow equipment for large compute packages; qualifying sub-micron bond alignment accuracy.
- distinct_from: `theme:wfe_process_tools` — front-end process tools vs back-end assembly capital. Distinct from `theme:hbm_packaging` (ai/memory) — packaging service/product rows vs the equipment that enables them.
- exclusions: OSAT assembly services (packaging rows in ai/memory themes); ATE (separate row).
- china_relevance: high — 封装设备国产化 is a named CCID/协会 equipment category.
- confidence: high
- sources: Yole Group, "Status of the Advanced Packaging Industry" (equipment coverage); SEMI, advanced packaging standards/reports; 赛迪顾问（CCID）, 中国半导体设备市场白皮书系列.

### theme:test_ate_equipment
- id: `theme:test_ate_equipment` · name_en: "Semiconductor test systems (ATE)" · name_zh: "半导体测试机（ATE）" · value_chain_position: midstream · parent_sub_theme: `theme:advanced_packaging_test_equipment`
- defining_activities: manufacturing automatic test equipment for SoC/memory/analog devices; building wafer-sort and final-test testhead/pin-electronics platforms; qualifying AI-device power/thermal test envelopes; selling test-cell software and characterization flows.
- distinct_from: `theme:process_metrology_inspection` (existing) — in-line process control vs finished-device functional/parametric test. Distinct from `theme:system_level_test_services` (ai_semiconductors) — tester manufacturers vs contract test capacity.
- exclusions: handlers/probers/probe cards (probe-card row); SLT services (ai row).
- china_relevance: high — 测试机国产化 is an active named equipment category (CCID).
- confidence: high
- sources: IEEE, "International Test Conference (ITC)" proceedings; SEMI, test-related standards program; 赛迪顾问（CCID）, 中国半导体设备市场白皮书系列.

### theme:probe_card_test_interfaces
- id: `theme:probe_card_test_interfaces` · name_en: "Probe cards & test interfaces" · name_zh: "探针卡与测试接口" · value_chain_position: upstream · parent_sub_theme: `theme:advanced_packaging_test_equipment`
- defining_activities: manufacturing MEMS/cantilever probe cards for wafer sort; building test sockets, loadboards and contactors for final test; iterating fine-pitch contact technology for advanced devices; supplying consumable contact cycles to test floors.
- distinct_from: `theme:test_ate_equipment` — contact consumables/interfaces vs tester systems; a recurring-consumable mechanism distinct from capital tools.
- exclusions: ATE systems; SLT fixtures (ai row).
- china_relevance: high — 探针卡国产化 is an active domestic substitution category (trade press/CCID).
- confidence: medium
- sources: IEEE, "Semiconductor Wafer Test Workshop (SWTest)" proceedings; IEEE ITC proceedings (probe/contact sessions); 赛迪顾问（CCID）半导体耗材/部件专题报告.

### theme:photomask_maskshop_supply
- id: `theme:photomask_maskshop_supply` · name_en: "Photomask & mask-shop supply" · name_zh: "光掩模版（光罩）" · value_chain_position: upstream · parent_sub_theme: `theme:equipment_component_periphery`
- defining_activities: patterning and qualifying advanced-node reticles in merchant mask shops; manufacturing mask blanks (quartz/EUV multilayer) upstream of patterning; running mask inspection/repair as part of mask lifecycle services; managing reticle sets across node ramps.
- distinct_from: `theme:lithography_tools` (existing) — the exposure tool vs the reticle product/supply chain the tool consumes.
- exclusions: mask-writer equipment (inside litho tool scope); photoresist (materials flag).
- china_relevance: high — 光罩/掩模版国产化 is a priority substitution category in Chinese supply-chain reporting.
- confidence: high
- sources: SEMI, photomask standards (P-series) program; SPIE, "Advanced Lithography + Patterning" proceedings (BACUS conference); 赛迪顾问（CCID）, 集成电路材料与部件专题.

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

### theme:fab_automation_amhs
- id: `theme:fab_automation_amhs` · name_en: "Fab automation & AMHS" · name_zh: "工厂自动化与物料搬运（AMHS）" · value_chain_position: enabler · parent_sub_theme: `theme:fab_automation_facility_systems`
- defining_activities: building automated material handling systems (OHT/STK) moving lots between tools; implementing MCS scheduling and carrier-management software to SEMI interface standards; integrating sorters/stockers with MES flows; expanding cleanroom automation for mega-fabs.
- distinct_from: `theme:wafer_fab_subsystems` — tool-internal subsystems vs inter-tool factory logistics automation (SEMI E-series interface standards scope).
- exclusions: process tools; facility HVAC/power (facility row).
- china_relevance: high — 厂务自动化/AMHS国产化 is an active domestic category (CCID/协会).
- confidence: medium
- sources: SEMI, interface and factory-automation standards (E-series, e.g., carrier management and equipment automation); IEEE IRDS, "Factory Integration" chapter; 赛迪顾问（CCID）, 中国半导体设备市场白皮书系列.

### theme:bulk_gas_chemical_delivery_systems
- id: `theme:bulk_gas_chemical_delivery_systems` · name_en: "Bulk gas & chemical delivery systems" · name_zh: "大宗气体与化学品输送系统" · value_chain_position: enabler · parent_sub_theme: `theme:fab_automation_facility_systems`
- defining_activities: building gas cabinets, valve manifolds and bulk specialty-gas delivery; installing chemical distribution/slurry delivery loops; qualifying purity/moisture control to fab specs; monitoring fab-wide gas/chemical telemetry.
- distinct_from: `theme:wafer_fab_subsystems` (existing) — facility-to-tool delivery infrastructure vs tool-internal subsystems; distinct from `theme:vacuum_subsystem_components` — delivery/flow of gases & chemicals vs vacuum generation.
- exclusions: gas/chemical production itself (materials flag); abatement (facility scope, no row).
- china_relevance: high — 电子大宗气体系统国产化 is an active fab-construction theme (CCID/trade press).
- confidence: medium
- sources: SEMI, gas/chemical delivery-related facilities standards program; IEEE IRDS, "Factory Integration" chapter; 中国电子专用设备工业协会（CEPEIA）行业报告.

### theme:equipment_refurb_remarket
- id: `theme:equipment_refurb_remarket` · name_en: "Equipment refurbishment & remarket" · name_zh: "设备翻新与再流通" · value_chain_position: downstream · parent_sub_theme: `theme:equipment_component_periphery`
- defining_activities: acquiring deinstalled fab tools for refurbishment; reconditioning and re-qualifying tools to secondary buyers; brokering secondary-market tool deals across regions; harvesting spare parts from retired fleets.
- distinct_from: `theme:wafer_fab_subsystems` — secondary-life tool market vs new-equipment subsystem supply; a distinct aftermarket mechanism recognized in fab-economic reporting.
- exclusions: new tool sales; field service contracts on new tools.
- china_relevance: medium — 二手设备/翻新市场 is a recurring topic as mature-node capacity expands in China (trade press).
- confidence: medium
- sources: SEMI, "World Fab Forecast" (capacity/fab-economics context); Semiconductor Engineering / EE Times (trade press) on secondary equipment markets; 中国电子专用设备工业协会（CEPEIA）行业报告.

### theme:advanced_packaging_test_equipment (sub_theme)
- id: `theme:advanced_packaging_test_equipment` · name_en: "Advanced Packaging & Test Equipment" · name_zh: "先进封装与测试设备" · value_chain_position: midstream
- note: Groups back-end capital — packaging assembly tools, ATE, probe cards — distinct from the front-end wfe_process_tools sub_theme.
- nominated_from: research:research/theme_graph/micro_expansion_20261021/C1_MICRO_RESEARCH.md
- parent: theme:semicap_equipment

### theme:equipment_component_periphery (sub_theme)
- id: `theme:equipment_component_periphery` · name_en: "Equipment Components & Periphery" · name_zh: "设备零部件与配套" · value_chain_position: upstream
- note: Groups the component/periphery supply behind toolmakers — vacuum and RF subsystems, photomasks, refurb/remarket — the 国产零部件 substitution layer.
- nominated_from: research:research/theme_graph/micro_expansion_20261021/C1_MICRO_RESEARCH.md
- parent: theme:semicap_equipment

### theme:fab_automation_facility_systems (sub_theme)
- id: `theme:fab_automation_facility_systems` · name_en: "Fab Automation & Facility Systems" · name_zh: "厂务自动化与设施系统" · value_chain_position: enabler
- note: Groups factory logistics automation and facility delivery systems (AMHS, bulk gas/chemical) — the enabler tier of the equipment chain.
- nominated_from: research:research/theme_graph/micro_expansion_20261021/C1_MICRO_RESEARCH.md
- parent: theme:semicap_equipment

---

## theme:data_center_power — Data Center Power & Cooling

Existing rows preserved: micros `theme:liquid_cooling_thermal`, `theme:hv_transformers_switchgear` (shared with grid_electrification), `theme:ups_power_conversion`.

**Sub-theme grouping.** Three new sub_themes: `theme:datacenter_backup_generation` (upstream on-site/backup energy: gensets, fuel cells, gas turbines, battery ESS); `theme:datacenter_thermal_chain` (the thermal product chain: interface materials, coolant fluids, precision air handling, waste-heat reuse — sitting beside the existing liquid_cooling_thermal row); `theme:datacenter_distribution_architecture` (new power-architecture products: MVDC architecture, busway, prefab power modules). One row stays direct: DCIM/energy-management software (enabler).

**Theme-tier candidates (prose only).** None. Data-center real-estate development and cloud platform operations are out of scope (the C1 hierarchy record rejected `hyperscaler_neocloud_hosting`); campus utility interconnection belongs to grid_electrification.

### theme:generator_backup_power
- id: `theme:generator_backup_power` · name_en: "Backup generator power" · name_zh: "备用柴油发电机组" · value_chain_position: upstream · parent_sub_theme: `theme:datacenter_backup_generation`
- defining_activities: manufacturing diesel gensets sized for facility emergency load; integrating emissions aftertreatment to air-permit classes; paralleling gensets with ATS sequences for tier-level redundancy; servicing fuel-polishing and run-test regimes.
- distinct_from: `theme:ups_power_conversion` (existing) — engine-generator primary movers vs UPS conversion electronics; the classic two halves of the backup chain.
- exclusions: fuel cells and turbines (separate rows); portable gensets without facility class.
- china_relevance: high — 数据中心柴发 is a large domestic supply segment (ODCC/数据中心 trade press).
- confidence: high
- sources: ISO, "ISO 8528 Reciprocating internal combustion engine driven alternating current generating sets"; U.S. EPA, stationary emergency engine regulations (40 CFR 60 Subpart IIII); Uptime Institute, "Global Data Center Survey" (topology context).

### theme:fuel_cell_prime_power
- id: `theme:fuel_cell_prime_power` · name_en: "Fuel cell power systems" · name_zh: "燃料电池供电系统" · value_chain_position: upstream · parent_sub_theme: `theme:datacenter_backup_generation`
- defining_activities: deploying stationary fuel-cell plants for prime/continuous data-center power; integrating hydrogen or reformate fuel supply chains; operating multi-MW fuel-cell arrays with grid-forming inverters; qualifying fuel-cell systems to stationary standards.
- distinct_from: `theme:generator_backup_power` — electrochemical conversion vs combustion gensets; positioned for prime power rather than emergency-only.
- exclusions: backup-only fuel cells without prime-power ambition (still this row's scope if data-center), hydrogen production itself.
- china_relevance: medium — 氢能/燃料电池数据中心应用 is exploratory in China (氢能产业 policy context), smaller than gensets.
- confidence: medium
- sources: IEC, "IEC 62282 Fuel cell technologies" standard series; U.S. DOE Hydrogen Program, hydrogen power/demonstration program documents; IEA, "Data Centres and Data Transmission Networks" (2020).

### theme:onsite_gas_turbine_power
- id: `theme:onsite_gas_turbine_power` · name_en: "On-site gas turbine power" · name_zh: "现场燃机自备电源" · value_chain_position: upstream · parent_sub_theme: `theme:datacenter_backup_generation`
- defining_activities: installing behind-the-meter gas turbines/engines for data-center campuses; contracting firm on-site generation ahead of grid upgrades; integrating turbines with campus microgrid controls; managing air permits and fuel logistics.
- distinct_from: `theme:generator_backup_power` — prime-power thermal machines vs emergency standby gensets; distinct from `theme:fuel_cell_prime_power` — combustion vs electrochemical.
- exclusions: grid PPAs without on-site equipment; utility peakers (grid theme).
- china_relevance: medium — 自备燃机 is nascent for Chinese DCs (mostly West-bound 东数西算 power siting), heavier in Western AI-campus news.
- confidence: medium
- sources: Uptime Institute, "Global Data Center Survey" (power-topology trends); IEA, "Energy and AI" (2025, data-center electricity supply analysis); LBNL, "United States Data Center Energy Usage Report" (2024).

### theme:battery_backup_storage_ess
- id: `theme:battery_backup_storage_ess` · name_en: "Battery backup & facility ESS" · name_zh: "锂电备电与储能系统" · value_chain_position: midstream · parent_sub_theme: `theme:datacenter_backup_generation`
- defining_activities: replacing lead-acid strings with lithium racks in UPS plants; deploying facility BESS for bridging and peak management; qualifying batteries to stationary ESS safety test methods; integrating BMS telemetry into facility monitoring.
- distinct_from: `theme:ups_power_conversion` (existing) — electrochemical storage + BMS vs power-conversion electronics; complements it in the same chain.
- exclusions: grid front-of-meter ESS (grid_electrification row); UPS inverters themselves.
- china_relevance: high — China's lithium supply chain makes 锂电备电 the dominant new DC battery route (ODCC specifications).
- confidence: high
- sources: UL, "UL 9540 / UL 9540A" energy storage system safety standards; NFPA, "NFPA 855 Standard for the Installation of Stationary Energy Storage Systems"; ODCC（开放数据中心委员会）, 数据中心储能/备电技术规范系列.

### theme:thermal_interface_materials
- id: `theme:thermal_interface_materials` · name_en: "Thermal interface materials (TIM)" · name_zh: "导热界面材料" · value_chain_position: midstream · parent_sub_theme: `theme:datacenter_thermal_chain`
- defining_activities: formulating gap pads, gels and phase-change TIMs for die-to-cold-plate paths; qualifying bulk conductivity and bond-line stability under power cycling; supplying high-watt-density TIM grades for accelerator packages; iterating low-pressure-out TIMs for cold-plate fleets.
- distinct_from: `theme:liquid_cooling_thermal` (existing) — package-level conduction materials vs cooling systems/loops; the material layer the loops depend on.
- exclusions: cold plates and CDUs (liquid cooling row); facility air handlers (separate row).
- china_relevance: high — 导热材料 is an active domestic materials segment (新材料 trade press/CCID).
- confidence: medium
- sources: ASHRAE TC 9.9, "Thermal Guidelines for Data Processing Environments"; IEEE, "Semiconductor Thermal Measurement and Management Symposium (SEMI-THERM)" proceedings; ODCC（开放数据中心委员会）液冷技术规范系列.

### theme:dielectric_coolant_fluids
- id: `theme:dielectric_coolant_fluids` · name_en: "Coolant & dielectric fluids" · name_zh: "冷却液与介电工质" · value_chain_position: midstream · parent_sub_theme: `theme:datacenter_thermal_chain`
- defining_activities: formulating water-glycol and single/two-phase dielectric fluids for liquid loops and immersion tanks; qualifying fluids for materials compatibility and pumpability; recycling and coolant lifecycle management at fleet scale; specifying chemistry standards with cooling-system OEMs.
- distinct_from: `theme:thermal_interface_materials` — the working fluid vs the conduction interface; distinct from `theme:liquid_cooling_thermal` — consumable chemistry vs cooling equipment.
- exclusions: chillers/CDUs (liquid cooling row); TIMs (separate row).
- china_relevance: high — 冷却液国产化 is an active domestic liquid-cooling supply theme (ODCC 液冷规范 context).
- confidence: medium
- sources: ASHRAE, "Emergence and Expansion of Liquid Cooling in Mainstream Data Centers" (white paper); Open Compute Project, cooling-environment/coolant specifications; ODCC（开放数据中心委员会）液冷技术规范系列.

### theme:precision_air_handler_cooling
- id: `theme:precision_air_handler_cooling` · name_en: "Precision air handling (CRAC/CRAH)" · name_zh: "机房精密空调" · value_chain_position: midstream · parent_sub_theme: `theme:datacenter_thermal_chain`
- defining_activities: manufacturing CRAC/CRAH units and airside economizers for white space; optimizing fan walls and containment airflow; integrating controls with DCIM thermal telemetry; retro-fitting air-cooled halls for rising rack densities.
- distinct_from: `theme:liquid_cooling_thermal` (existing) — air-side cooling equipment vs liquid loops; the co-existing主流 air path for mainstream racks.
- exclusions: liquid loops/immersion (liquid cooling row); building comfort HVAC without white-space class.
- china_relevance: high — 机房精密空调 is a mature large domestic segment (ODCC/行业报告).
- confidence: high
- sources: ASHRAE TC 9.9, "Thermal Guidelines for Data Processing Environments"; AHRI, "AHRI 550/590" performance rating standard (chilled-water/dx equipment context); ODCC（开放数据中心委员会）制冷技术规范系列.

### theme:waste_heat_reuse
- id: `theme:waste_heat_reuse` · name_en: "Data-center waste heat reuse" · name_zh: "数据中心余热回收" · value_chain_position: downstream · parent_sub_theme: `theme:datacenter_thermal_chain`
- defining_activities: capturing rejected heat at higher loop temperatures for district heating; engineering heat-pump boosters and heat exchangers to export grade; contracting heat offtake with municipal networks; qualifying revenue-graded heat supply.
- distinct_from: `theme:liquid_cooling_thermal` — heat export/recovery systems vs heat rejection; a distinct downstream mechanism with municipal-buyer economics.
- exclusions: cooling plant itself; campus space heating done incidentally without export systems.
- china_relevance: medium — 余热回收 pilots exist in northern China (清洁供暖 policy context), not yet systemic.
- confidence: medium
- sources: IEA, "Data Centres and Data Transmission Networks" (2020, heat-reuse analysis); ASHRAE TC 9.9 liquid/thermal publications; 北极星电力网/ODCC 数据中心余热利用专题（trade press）.

### theme:medium_voltage_dc_architecture
- id: `theme:medium_voltage_dc_architecture` · name_en: "Medium-voltage DC power architecture" · name_zh: "中压直流供电架构" · value_chain_position: midstream · parent_sub_theme: `theme:datacenter_distribution_architecture`
- defining_activities: engineering MV-to-rack DC distribution (rectifier-MV bus-DC/DC chains); eliminating conversion stages vs legacy AC paths; standardizing high-voltage rack/bus interfaces; qualifying protection for DC fault behavior.
- distinct_from: `theme:ups_power_conversion` (existing) — end-to-end DC architecture vs UPS product class; distinct from `theme:hv_transformers_switchgear` — AC primary equipment vs DC distribution chain.
- exclusions: 48V rack-level only without MV tier; UPS units as such.
- china_relevance: high — 中压直流 (HVDC-for-DC) is a named Chinese operator architecture line (ODCC/中国电信级白皮书).
- confidence: medium
- sources: ODCC（开放数据中心委员会）, 240V/336V 直流及中压直流供电技术规范系列; EN 50600 (CENELEC data centre facilities standard); Uptime Institute, "Global Data Center Survey" (topology share data).

### theme:power_busway_distribution
- id: `theme:power_busway_distribution` · name_en: "Overhead busway & rack power distribution" · name_zh: "数据中心母线槽配电" · value_chain_position: midstream · parent_sub_theme: `theme:datacenter_distribution_architecture`
- defining_activities: manufacturing overhead busway trunking with tap-off boxes; engineering rack PDUs and whips from busway to IT load; qualifying short-circuit and tap ratings for dense rows; reconfiguring bus runs for changing rack layouts.
- distinct_from: `theme:hv_transformers_switchgear` (existing) — low/medium-voltage in-room trunking vs HV/campus primary equipment; distinct from `theme:ups_power_conversion` — distribution hardware vs conversion electronics.
- exclusions: MVDC architecture (separate row); building wire/cable (copper_wire_cable under copper_steel_electrify).
- china_relevance: high — 小母线/母线槽 is the standard Chinese DC fit-out vocabulary (ODCC).
- confidence: high
- sources: IEC, "IEC 61439-6 busbar trunking systems"; Uptime Institute, "Global Data Center Survey"; ODCC（开放数据中心委员会）配电技术规范系列.

### theme:prefab_power_modules
- id: `theme:prefab_power_modules` · name_en: "Prefabricated power modules" · name_zh: "预制化电力模组" · value_chain_position: midstream · parent_sub_theme: `theme:datacenter_distribution_architecture`
- defining_activities: factory-building integrated power trains (MV switchgear-transformer-UPS-PDU in skids); compressing on-site electrical commissioning schedules; standardizing modular power blocks for repeatable halls; delivering containerized power for fast builds.
- distinct_from: `theme:hv_transformers_switchgear` / `theme:ups_power_conversion` — discrete product classes vs the factory-integrated module train that combines them; a recognized product-form trend in Chinese DC construction.
- exclusions: discrete switchgear/UPS products themselves; portable generators.
- china_relevance: high — 一体化电力模组/预制舱 is a flagship Chinese DC supply-chain trend (ODCC specifications).
- confidence: medium
- sources: ODCC（开放数据中心委员会）, 电力模组/预制化数据中心技术规范系列; 工信部, 《新型数据中心发展三年行动计划（2021-2023年）》; Uptime Institute research notes on modular data centers.

### theme:dcim_energy_management_software
- id: `theme:dcim_energy_management_software` · name_en: "DCIM & energy management software" · name_zh: "数据中心能碳管理软件（DCIM）" · value_chain_position: enabler · parent_sub_theme: none (direct child of theme)
- defining_activities: monitoring facility power/cooling telemetry in DCIM platforms; optimizing PUE via model-predictive cooling control; managing capacity and asset chains across halls; reporting energy/carbon compliance to operators and regulators.
- distinct_from: `theme:grid_operating_software` (grid_electrification, proposed) — utility-side grid software vs facility-side DC management; distinct from all power/cooling hardware rows.
- exclusions: IT workload orchestration; grid dispatch software (grid theme).
- china_relevance: high — DCIM/能碳管理 is a standard Chinese DC software category (ODCC, 双碳 policy context).
- confidence: high
- sources: ODCC（开放数据中心委员会）, 数据中心运营管理/能效技术规范系列; GB 40879-2021, 《数据中心能效限定值及能效等级》; Uptime Institute, "Global Data Center Survey" (management-software adoption data).

### theme:datacenter_backup_generation (sub_theme)
- id: `theme:datacenter_backup_generation` · name_en: "Backup & On-site Generation" · name_zh: "备电与自备电源" · value_chain_position: upstream
- note: Groups the energy-supply tier — gensets, fuel cells, gas turbines, battery ESS — upstream of conversion and distribution.
- nominated_from: research:research/theme_graph/micro_expansion_20261021/C1_MICRO_RESEARCH.md
- parent: theme:data_center_power

### theme:datacenter_thermal_chain (sub_theme)
- id: `theme:datacenter_thermal_chain` · name_en: "Data Center Thermal Chain" · name_zh: "散热与热管理链" · value_chain_position: midstream
- note: Groups the thermal product chain — interface materials, coolant fluids, precision air handling, heat reuse — beside the existing liquid-cooling row.
- nominated_from: research:research/theme_graph/micro_expansion_20261021/C1_MICRO_RESEARCH.md
- parent: theme:data_center_power

### theme:datacenter_distribution_architecture (sub_theme)
- id: `theme:datacenter_distribution_architecture` · name_en: "Data Center Distribution Architecture" · name_zh: "数据中心配电架构" · value_chain_position: midstream
- note: Groups new power-architecture product forms — MVDC architecture, busway, prefab power modules — downstream of energy supply.
- nominated_from: research:research/theme_graph/micro_expansion_20261021/C1_MICRO_RESEARCH.md
- parent: theme:data_center_power

---

## theme:nuclear_power — Nuclear & SMR Power

Existing rows preserved: micros `theme:reactor_technology`, `theme:nuclear_components`, `theme:fuel_cycle`.

**Sub-theme grouping.** Three new sub_themes: `theme:advanced_nuclear_fuel_chain` (upstream: HALEU supply, TRISO fuel-form fabrication, fuel-assembly fabrication — the fabrication tail the existing fuel_cycle row, scoped "mining through enrichment", does not cover); `theme:nuclear_plant_supply_chain` (midstream: EPC construction, heavy forgings, digital I&C/DCS, conventional-island equipment); `theme:nuclear_back_end_lifecycle` (downstream: decommissioning/waste, spent-fuel management). Three rows stay direct: plant operations, nuclear heat/hydrogen applications, medical isotope production.

**Theme-tier candidates (prose only).** None. Marine propulsion stays under defense_aerospace (`naval_shipbuilding`); radiopharmaceuticals belong to healthcare.

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

### theme:nuclear_plant_construction_epc
- id: `theme:nuclear_plant_construction_epc` · name_en: "Nuclear plant construction & EPC" · name_zh: "核电工程建造（EPC）" · value_chain_position: midstream · parent_sub_theme: `theme:nuclear_plant_supply_chain`
- defining_activities: executing nuclear-island civil works and containment construction; managing EPC schedules under nuclear QA regimes; coordinating module installation and heavy-lift campaigns; delivering commissioning-to-fuel-load milestones.
- distinct_from: `theme:nuclear_components` (existing) — component manufacturing vs the engineering/construction act; distinct from `theme:reactor_technology` — build execution vs reactor design.
- exclusions: component fabrication (separate rows); plant operation (separate row).
- china_relevance: high — China runs the world's largest reactor construction pipeline (核电工程建设, 中国核能行业协会蓝皮书).
- confidence: high
- sources: World Nuclear Association, "World Nuclear Performance Report" (construction pipeline data); IAEA, Nuclear Energy Series (construction/licensing reports); 中国核能行业协会, 《中国核能发展报告》蓝皮书.

### theme:heavy_component_forgings
- id: `theme:heavy_component_forgings` · name_en: "Heavy nuclear forgings" · name_zh: "核电大型铸锻件" · value_chain_position: upstream · parent_sub_theme: `theme:nuclear_plant_supply_chain`
- defining_activities: forging reactor pressure vessels, steam generators and pressurizers from large ingots; maintaining nuclear-grade forging QA and material traceability; expanding ultralarge press/heat-treatment capacity; supplying forgings into global reactor schedules.
- distinct_from: `theme:nuclear_components` (existing) — the broad components layer vs the heavy-forging class specifically (the recognized bottleneck segment in nuclear supply-chain reporting).
- exclusions: valves/pumps/instrumentation (inside the broad components row); I&C (separate row).
- china_relevance: high — 核电锻件国产化 is complete-to-expanding in China, a standing 蓝皮书/trade line.
- confidence: high
- sources: World Nuclear News (trade press), heavy forging capacity coverage; OECD-NEA, nuclear supply-chain reports; 中国核能行业协会, 《中国核能发展报告》蓝皮书.

### theme:nuclear_i_c_dcs_systems
- id: `theme:nuclear_i_c_dcs_systems` · name_en: "Nuclear instrumentation & control (DCS)" · name_zh: "核电数字化仪控（DCS）" · value_chain_position: enabler · parent_sub_theme: `theme:nuclear_plant_supply_chain`
- defining_activities: supplying safety-class digital I&C platforms for reactor protection; engineering non-safety DCS for plant control; qualifying software/firmware under nuclear software QA; licensing platforms with regulators per plant class.
- distinct_from: `theme:nuclear_components` (existing) — electronic protection/control systems vs mechanical components; a distinct engineering discipline with its own qualification regime.
- exclusions: security systems (cybersecurity theme); plant simulators as services (inside I&C scope).
- china_relevance: high — 核电仪控（DCS）国产化 is an established Chinese segment (蓝皮书/行业报告).
- confidence: high
- sources: IEC, "IEC 62138 / IEC 60880" nuclear I&C software qualification standard series; IAEA, Nuclear Energy Series (instrumentation & control reports); 中国核能行业协会, 《中国核能发展报告》蓝皮书.

### theme:turbine_island_equipment
- id: `theme:turbine_island_equipment` · name_en: "Conventional-island (turbine island) equipment" · name_zh: "常规岛设备" · value_chain_position: midstream · parent_sub_theme: `theme:nuclear_plant_supply_chain`
- defining_activities: supplying steam turbines, generators and moisture-separator reheaters for nuclear plants; manufacturing condensers and secondary-cycle pumps; matching turbine trains to reactor thermal output classes; servicing rotor/blade lifecycles.
- distinct_from: `theme:nuclear_components` (existing) — the conventional (secondary) island vs nuclear-island components; distinct procurement classes in plant bills of material.
- exclusions: nuclear-island primaries (components/forgings rows); fossil/gas turbine markets without nuclear linkage.
- china_relevance: high — 常规岛设备 is standard Chinese nuclear-industry vocabulary (蓝皮书/公司披露口径).
- confidence: high
- sources: IAEA, Nuclear Energy Series (plant systems reports); World Nuclear Association, plant-systems information papers; 中国核能行业协会, 《中国核能发展报告》蓝皮书.

### theme:nuclear_plant_operations
- id: `theme:nuclear_plant_operations` · name_en: "Nuclear plant operations" · name_zh: "核电站运营" · value_chain_position: downstream · parent_sub_theme: none (direct child of theme)
- defining_activities: operating licensed reactors and selling generation into power markets; executing refueling outages and fleet maintenance programs; pursuing power uprates and license renewals; operating under performance-indicator regimes (capacity factor, SCRAM rates).
- distinct_from: `theme:reactor_technology` — reactor designers vs licensed operators; the downstream generation-asset layer the whole supply chain feeds.
- exclusions: construction (EPC row); fuel supply (fuel rows); utility non-nuclear generation.
- china_relevance: high — China's operating fleet is the world's largest under construction plus operating base (中国核能行业协会蓝皮书).
- confidence: high
- sources: World Nuclear Association, "World Nuclear Performance Report" (operational indicators); Nuclear Energy Institute, "Nuclear Costs in Context" (annual); 中国核能行业协会, 《中国核能发展报告》蓝皮书.

### theme:decommissioning_waste_management
- id: `theme:decommissioning_waste_management` · name_en: "Decommissioning & waste management" · name_zh: "核设施退役与废物管理" · value_chain_position: downstream · parent_sub_theme: `theme:nuclear_back_end_lifecycle`
- defining_activities: dismantling retired reactors and decontaminating sites; characterizing, packaging and disposing of low/intermediate-level waste; managing decommissioning cost provisions and trust funds; returning sites for reuse under regulatory closeout.
- distinct_from: `theme:spent_fuel_management` — plant dismantling/site waste vs spent-fuel storage/reprocessing; distinct end-of-life mechanisms.
- exclusions: operating-waste logistics inside plants; spent fuel (separate row).
- china_relevance: medium — Chinese decommissioning backlog is smaller today (young fleet) but 退役治理 is a named program line.
- confidence: medium
- sources: OECD-NEA, reports on decommissioning policies, strategies and costs; IAEA, Nuclear Energy Series (decommissioning reports); 中国核能行业协会, 《中国核能发展报告》蓝皮书.

### theme:spent_fuel_management
- id: `theme:spent_fuel_management` · name_en: "Spent fuel storage & reprocessing" · name_zh: "乏燃料贮运与后处理" · value_chain_position: downstream · parent_sub_theme: `theme:nuclear_back_end_lifecycle`
- defining_activities: storing spent fuel in pools and dry casks at interim sites; transporting spent fuel under licensed cask regimes; reprocessing spent fuel to recover uranium/plutonium; engineering deep-geological disposal programs.
- distinct_from: `theme:decommissioning_waste_management` — spent-fuel back-end vs plant dismantling; distinct from `theme:fuel_cycle` (front-end mining/enrichment scope).
- exclusions: MOX refabrication (inside reprocessing scope note); reactor operations.
- china_relevance: high — 乏燃料后处理 is a strategic Chinese program line (蓝皮书), with pilot and commercial-scale plants in planning.
- confidence: medium
- sources: IAEA, Nuclear Energy Series (spent fuel management reports); World Nuclear Association, fuel-cycle information papers (storage/reprocessing); 中国核能行业协会, 《中国核能发展报告》蓝皮书.

### theme:nuclear_heat_hydrogen_applications
- id: `theme:nuclear_heat_hydrogen_applications` · name_en: "Nuclear heat & hydrogen applications" · name_zh: "核能供热与制氢" · value_chain_position: downstream · parent_sub_theme: none (direct child of theme)
- defining_activities: supplying district heating from reactor extraction steam; demonstrating high-temperature steam electrolysis with nuclear heat/Power; contracting industrial heat offtake from reactor parks; integrating nuclear heat with chemical-park users.
- distinct_from: `theme:nuclear_plant_operations` — electricity generation vs heat/hydrogen products from the same asset class.
- exclusions: non-nuclear hydrogen production; geothermal/solar heat.
- china_relevance: high — 核能供暖 is operating at scale in Chinese districts (蓝皮书 standing line).
- confidence: medium
- sources: 中国核能行业协会, 《中国核能发展报告》蓝皮书 (核能供暖 program); U.S. DOE Office of Nuclear Energy, hydrogen demonstration program documents; IAEA, Nuclear-Renewable/hybrid heat applications reports.

### theme:medical_isotope_production
- id: `theme:medical_isotope_production` · name_en: "Medical isotope production" · name_zh: "医用同位素生产" · value_chain_position: downstream · parent_sub_theme: none (direct child of theme)
- defining_activities: irradiating targets in reactors/accelerators for Mo-99, iodine and other medical isotopes; processing and distributing isotopes under GMP; building dedicated isotope production reactors; contracting hospital radiopharmacy supply chains.
- distinct_from: `theme:nuclear_plant_operations` — isotope irradiation/processing services vs power generation; a distinct product line on nuclear infrastructure.
- exclusions: radiopharmaceutical drug development (healthcare themes); power reactors without isotope programs.
- china_relevance: medium — 医用同位素自主供应 is a named Chinese program (原子能机构/卫健委 plan), domestic capacity still scaling.
- confidence: medium
- sources: IAEA, Nuclear Energy Series (radioisotope production reports); OECD-NEA, "The Supply of Medical Radioisotopes" report series; 国家原子能机构（CAEA）医用同位素发展规划文件.

### theme:advanced_nuclear_fuel_chain (sub_theme)
- id: `theme:advanced_nuclear_fuel_chain` · name_en: "Advanced Nuclear Fuel Chain" · name_zh: "先进核燃料链" · value_chain_position: upstream
- note: Groups HALEU supply, TRISO fuel forms and fuel-assembly fabrication — the fabrication/supply tiers beyond the legacy fuel_cycle row's mining-through-enrichment scope.
- nominated_from: research:research/theme_graph/micro_expansion_20261021/C1_MICRO_RESEARCH.md
- parent: theme:nuclear_power

### theme:nuclear_plant_supply_chain (sub_theme)
- id: `theme:nuclear_plant_supply_chain` · name_en: "Nuclear Plant Supply Chain" · name_zh: "核电设备与建造" · value_chain_position: midstream
- note: Groups EPC construction, heavy forgings, digital I&C and conventional-island equipment — the build-the-plant tier.
- nominated_from: research:research/theme_graph/micro_expansion_20261021/C1_MICRO_RESEARCH.md
- parent: theme:nuclear_power

### theme:nuclear_back_end_lifecycle (sub_theme)
- id: `theme:nuclear_back_end_lifecycle` · name_en: "Nuclear Back-End Lifecycle" · name_zh: "核设施后端与退役" · value_chain_position: downstream
- note: Groups decommissioning/waste and spent-fuel management — the back-end-of-life tier.
- nominated_from: research:research/theme_graph/micro_expansion_20261021/C1_MICRO_RESEARCH.md
- parent: theme:nuclear_power

---

## theme:grid_electrification — Grid & Electrification

Existing rows preserved: micros `theme:hv_transformers_switchgear` (shared with data_center_power), `theme:grid_distribution_automation`, `theme:transmission_hvdc_cabling`.

**Sub-theme grouping.** Two new sub_themes: `theme:grid_equipment_supply` (upstream/midstream equipment: electrical-steel core materials, protection/secondary systems, reactive compensation, HVDC converter stations, UHV AC transmission, advanced conductors, line construction EPC); `theme:grid_software_flexibility` (enabler/downstream flexibility: grid operating software, AMI metering, VPP aggregation, grid-scale batteries, grid-forming inverters, dynamic line rating, microgrids). One row stays direct: EV charging networks (downstream electrification load).

**Theme-tier candidates (prose only).** Two genuine gaps for the seat: an `offshore_wind` theme (turbines, foundations, installation vessels, offshore substations currently have no home theme) and an `energy_storage` theme (storage is represented here only as a grid micro; a standalone storage theme would host cells, integrators and software). No rows proposed in this lane.

### theme:electrical_steel_core_materials
- id: `theme:electrical_steel_core_materials` · name_en: "Electrical steel & core materials" · name_zh: "电工钢（取向硅钢）铁芯材料" · value_chain_position: upstream · parent_sub_theme: `theme:grid_equipment_supply`
- defining_activities: producing grain-oriented electrical steel for transformer cores; slitting/stacking cores and wound-core fabrication; developing low-loss/high-permeability grades for efficient transformers; supplying amorphous and specialist core materials.
- distinct_from: `theme:hv_transformers_switchgear` (existing) — the core material input vs transformer/switchgear products; a recognized upstream bottleneck in transformer supply chains.
- exclusions: finished transformers/switchgear (existing row); non-electrical steel.
- china_relevance: high — 取向硅钢 is a large Chinese specialty-steel segment (行业协会/工信部 raw-material reporting).
- confidence: high
- sources: IEA, "Electricity Grids and Secure Energy Transitions" (2023, supply-chain chapters); 中国钢铁工业协会, 电工钢产品与市场报告; U.S. DOE, "National Transmission Needs Study" (2023, grid-hardware supply context).

### theme:grid_protection_control_systems
- id: `theme:grid_protection_control_systems` · name_en: "Grid protection & secondary systems" · name_zh: "继电保护与二次系统" · value_chain_position: midstream · parent_sub_theme: `theme:grid_equipment_supply`
- defining_activities: manufacturing protective relays and bay controllers; engineering substation SCADA and station LAN to IEC 61850; commissioning protection settings and teleprotection links; retrofitting legacy substations with digital secondary systems.
- distinct_from: `theme:hv_transformers_switchgear` (existing) — primary (power-carrying) equipment vs secondary protection/control layer; distinct from `theme:grid_distribution_automation` (existing) — substation protection vs feeder automation.
- exclusions: breaker/transformer hardware itself; utility IT (grid software row).
- china_relevance: high — 继电保护与二次设备 is a strong domestic segment (国网招标体系, CEC reporting).
- confidence: high
- sources: IEC, "IEC 61850" substation communication networks standard series; IEEE, power system relaying committee publications (e.g., protective relaying guides); 中国电力企业联合会, 《中国电力行业年度发展报告》.

### theme:advanced_metering_infrastructure
- id: `theme:advanced_metering_infrastructure` · name_en: "Smart metering & AMI" · name_zh: "智能电表与 AMI" · value_chain_position: downstream · parent_sub_theme: `theme:grid_software_flexibility`
- defining_activities: manufacturing smart electricity meters and data concentrators; operating AMI head-end and meter-data-management systems; enabling time-of-use and remote connect/disconnect services; rolling out high-frequency consumption telemetry for DSO operations.
- distinct_from: `theme:grid_distribution_automation` (existing) — feeder automation control vs the edge metering layer and its head-end systems.
- exclusions: gas/water meters without grid-electricity linkage; home energy devices.
- china_relevance: high — 智能电表 is a mature, export-active Chinese segment (中国电力企业联合会/行业报告).
- confidence: high
- sources: IEC, "IEC 62056 (DLMS/COSEM)" metering standard series; NIST, Smart Grid interoperability framework documents; 中国电力企业联合会, 《中国电力行业年度发展报告》.

### theme:grid_operating_software
- id: `theme:grid_operating_software` · name_en: "Grid operating software (EMS/ADMS/DERMS)" · name_zh: "电网调度与运营软件" · value_chain_position: enabler · parent_sub_theme: `theme:grid_software_flexibility`
- defining_activities: building energy management and distribution management platforms; modeling networks (state estimation, power flow, contingency analysis); dispatching DERs through DERMS integrations; modernizing market/settlement interfaces for utilities.
- distinct_from: `theme:grid_distribution_automation` (existing) — automation field hardware vs the software platform layer; distinct from `theme:dcim_energy_management_software` (data_center_power) — utility-side vs facility-side.
- exclusions: protection hardware (equipment row); trading/exchange platforms (financial_services).
- china_relevance: high — 电网调度自动化/国产电网软件 is a core domestic segment (CEC/国网体系 reporting).
- confidence: high
- sources: IEC, "IEC 61970/61968" Common Information Model standard series; IEEE, "IEEE 2030" smart grid interoperability standards family; 中国电力企业联合会, 《中国电力行业年度发展报告》.

### theme:virtual_power_plant_aggregation
- id: `theme:virtual_power_plant_aggregation` · name_en: "Virtual power plant aggregation" · name_zh: "虚拟电厂聚合" · value_chain_position: downstream · parent_sub_theme: `theme:grid_software_flexibility`
- defining_activities: aggregating distributed batteries, EVs and flexible loads into tradable portfolios; bidding VPP capacity/energy into wholesale and ancillary markets; dispatching fleet telemetry with sub-second control signals; settling participant revenues.
- distinct_from: `theme:grid_operating_software` — utility-owned operational platforms vs merchant DER aggregation market participation; distinct from `theme:grid_scale_battery_storage` — software aggregation of others' assets vs owning storage plants.
- exclusions: utility EMS (software row); single-site microgrids (microgrid row).
- china_relevance: high — 虚拟电厂 is an explicit Chinese policy program (新型电力系统 blue book, provincial pilots).
- confidence: high
- sources: U.S. DOE, "Pathways to Commercial Liftoff: Virtual Power Plants"; 国家能源局, 《新型电力系统发展蓝皮书》(2023); FERC, Order 2222 (DER aggregation in wholesale markets).

### theme:grid_scale_battery_storage
- id: `theme:grid_scale_battery_storage` · name_en: "Grid-scale battery storage systems" · name_zh: "电网侧储能系统" · value_chain_position: midstream · parent_sub_theme: `theme:grid_software_flexibility`
- defining_activities: integrating grid-scale BESS plants (cells to HV interconnection); operating storage for energy shifting, frequency response and capacity markets; engineering hybrid renewable-plus-storage plants; servicing augmentation and warranty regimes.
- distinct_from: `theme:battery_backup_storage_ess` (data_center_power, proposed) — front-of-meter utility ESS vs facility backup; distinct from `theme:solar_inverters` (existing, solar) — storage PCS/systems vs PV inverter products.
- exclusions: consumer batteries; DC backup batteries (data_center_power row); cell chemistry manufacturing itself (no home theme — flag as prose candidate).
- china_relevance: high — 新型储能 is a national-scale Chinese buildout (国家能源局/CEC statistics).
- confidence: high
- sources: IEA, "Batteries and Secure Energy Transitions" (2024); IEC, "IEC 62933" electrical energy storage standard series; 国家能源局, 《新型电力系统发展蓝皮书》(2023).

### theme:grid_forming_inverter_technology
- id: `theme:grid_forming_inverter_technology` · name_en: "Grid-forming inverter technology" · name_zh: "构网型逆变器" · value_chain_position: enabler · parent_sub_theme: `theme:grid_software_flexibility`
- defining_activities: engineering inverters that set voltage/frequency references autonomously (grid-forming control); qualifying IBR plants to new interconnection standards; retrofitting storage/wind/PV plants with grid-forming firmware; supplying synthetic inertia services to low-inertia grids.
- distinct_from: `theme:solar_inverters` (existing, solar) — PV plant inverter products (grid-following default) vs the grid-forming capability class now specified separately in grid codes; distinct from `theme:grid_scale_battery_storage` — control technology vs the storage plants.
- exclusions: standard grid-following PV inverters (solar row); STATCOM/SVC hardware (reactive row).
- china_relevance: high — 构网型技术 is being deployed in Chinese high-renewables provinces (西藏/新疆 pilots, CEC reporting).
- confidence: medium
- sources: IEEE, "IEEE 2800-2022" interconnection standard for inverter-based resources; NERC, reliability guidelines for BPS-connected inverter-based resources; 中国电力企业联合会, 《中国电力行业年度发展报告》.

### theme:reactive_power_compensation
- id: `theme:reactive_power_compensation` · name_en: "Reactive power compensation (SVC/STATCOM)" · name_zh: "无功补偿装置（SVC/STATCOM）" · value_chain_position: midstream · parent_sub_theme: `theme:grid_equipment_supply`
- defining_activities: manufacturing SVC/STATCOM and synchronous condenser plants; stabilizing voltage on weak and high-IBR grids; supplying dynamic reactive support for HVDC terminals; commissioning damping of oscillations in series-compensated corridors.
- distinct_from: `theme:hv_transformers_switchgear` (existing) — compensation electronics/machines vs primary switchgear/transformers; distinct from `theme:grid_forming_inverter_technology` — dedicated compensation plant vs IBR control capability.
- exclusions: capacitor banks without dynamic control; substation primary equipment.
- china_relevance: high — 无功补偿/调相机 is standard Chinese grid-strengthening vocabulary (CEC/国网 reporting).
- confidence: medium
- sources: IEEE, "IEEE 1031" STATCOM planning/design guide; CIGRE, technical brochures on reactive power compensation (SC B4); 中国电力企业联合会, 《中国电力行业年度发展报告》.

### theme:hvdc_converter_stations
- id: `theme:hvdc_converter_stations` · name_en: "HVDC converter stations & valves" · name_zh: "换流站与换流阀" · value_chain_position: midstream · parent_sub_theme: `theme:grid_equipment_supply`
- defining_activities: manufacturing converter valves (LCC thyristor and VSC MMC topologies); engineering converter-station controls and cooling systems; supplying converter transformers and smoothing reactors; commissioning multi-terminal HVDC schemes.
- distinct_from: `theme:transmission_hvdc_cabling` (existing) — cable systems vs converter-station power electronics; the two halves of an HVDC link.
- exclusions: cable manufacture (existing row); HVAC substations (switchgear row).
- china_relevance: high — 换流阀/换流站 is core Chinese UHV program vocabulary (CEC/国网).
- confidence: high
- sources: CIGRE, technical brochures on HVDC systems (Study Committee B4); IEA, "Electricity Grids and Secure Energy Transitions" (2023); 中国电力企业联合会, 《中国电力行业年度发展报告》.

### theme:transmission_line_construction_epc
- id: `theme:transmission_line_construction_epc` · name_en: "Transmission line construction & EPC" · name_zh: "输电线路工程建造" · value_chain_position: midstream · parent_sub_theme: `theme:grid_equipment_supply`
- defining_activities: engineering and building overhead transmission lines; constructing underground/submarine cable circuits (installation, not cable making); managing right-of-way, foundations and tower erection; delivering substation civil/electrical balance-of-plant.
- distinct_from: `theme:hv_transformers_switchgear` and `theme:transmission_hvdc_cabling` (existing) — equipment/cable manufacturing vs the construction/EPC act that installs them.
- exclusions: equipment and cable manufacturing themselves; maintenance-only services (no row).
- china_relevance: high — 电网工程建造 is a major Chinese infrastructure segment (CEC annual statistics).
- confidence: high
- sources: IEA, "Electricity Grids and Secure Energy Transitions" (2023, buildout/lead-time analysis); U.S. DOE, "National Transmission Needs Study" (2023); 中国电力企业联合会, 《中国电力行业年度发展报告》.

### theme:dynamic_line_rating_sensors
- id: `theme:dynamic_line_rating_sensors` · name_en: "Dynamic line rating & line sensing" · name_zh: "线路动态增容与感知" · value_chain_position: enabler · parent_sub_theme: `theme:grid_software_flexibility`
- defining_activities: deploying conductor tension/sag and weather sensors for real-time ratings; computing dynamic line ratings that raise usable transfer capacity; integrating ratings into EMS security-constrained dispatch; monitoring line faults/oscillations with synced sensing.
- distinct_from: `theme:advanced_overhead_conductors` — sensing/rating software-sensor layer vs conductor hardware; distinct from `theme:grid_operating_software` — line-side sensing vs network platform software.
- exclusions: conductor replacement itself; substation protection (equipment row).
- china_relevance: medium — 输电线路智能感知 is an emerging Chinese grid-digitalization line (CEC/国网数字化 reporting).
- confidence: medium
- sources: U.S. DOE, dynamic line rating studies/programs; CIGRE, technical brochures on dynamic rating (SC B2); IEEE, transmission & distribution committee publications on line ratings.

### theme:microgrid_systems_integration
- id: `theme:microgrid_systems_integration` · name_en: "Microgrid systems & integration" · name_zh: "微电网系统集成" · value_chain_position: downstream · parent_sub_theme: `theme:grid_software_flexibility`
- defining_activities: engineering islandable power systems (PV/storage/gens) for campuses and remote sites; supplying microgrid controllers with seamless grid-connect/island transitions; optimizing multi-asset dispatch and fuel strategies; delivering resilience-as-a-service operations.
- distinct_from: `theme:virtual_power_plant_aggregation` — single-site islandable systems vs market-wide aggregation of distributed assets; distinct from `theme:datacenter_backup_generation` — multi-asset microgrids vs facility backup chain.
- exclusions: campus backup generators alone (data_center_power row); utility distribution automation (existing row).
- china_relevance: medium — 微电网 is a pilot-stage Chinese segment (新能源微电网示范 programs).
- confidence: medium
- sources: IEEE, "IEEE 2030.7 / 2030.8" microgrid controller standards; U.S. DOE, microgrid program reports; 国家能源局, 新能源微电网示范政策文件.

### theme:ev_charging_networks
- id: `theme:ev_charging_networks` · name_en: "EV charging networks & equipment" · name_zh: "充电网络与充电桩" · value_chain_position: downstream · parent_sub_theme: none (direct child of theme)
- defining_activities: manufacturing AC/DC fast chargers and charging modules; operating public charging networks with roaming payments; deploying megawatt charging for heavy fleets; integrating managed charging with grid tariffs.
- distinct_from: `theme:grid_distribution_automation` (existing) — electrification demand infrastructure vs utility automation; complements `theme:grid_scale_battery_storage` (storage assets vs charging assets).
- exclusions: vehicle manufacturing; battery swapping stations for two-wheelers; home sockets without network mechanism.
- china_relevance: high — 充电基础设施 is the world's largest Chinese buildout (中国充电联盟/CEC statistics).
- confidence: high
- sources: 国家能源局/中国电动汽车充电基础设施促进联盟, 充电基础设施年度运行数据; IEC, "IEC 61851" EV conductive charging standard series; IEA, "Global EV Outlook" (charging infrastructure chapters).

### theme:ultra_hv_ac_transmission
- id: `theme:ultra_hv_ac_transmission` · name_en: "Ultra-high-voltage AC transmission" · name_zh: "特高压交流输电" · value_chain_position: midstream · parent_sub_theme: `theme:grid_equipment_supply`
- defining_activities: building 1000kV-class AC corridors and substations; engineering UHV transformers/reactors/GIS at voltage classes unique to long-distance bulk transfer; operating UHV systems for inter-regional power balancing; exporting UHV standards/engineering know-how.
- distinct_from: `theme:hv_transformers_switchgear` (existing) — the UHV corridor/system engineering class vs standard HV equipment products; distinct from `theme:hvdc_converter_stations` — AC corridors vs DC converter terminals.
- exclusions: standard 220–500kV equipment (existing rows); HVDC links (separate row).
- china_relevance: high — 特高压 is a signature Chinese grid program (CEC/国网; CIGRE UHV brochures co-authored by Chinese utilities).
- confidence: high
- sources: CIGRE, technical brochures on UHV AC systems; 中国电力企业联合会, 《中国电力行业年度发展报告》; 国家能源局, 《新型电力系统发展蓝皮书》(2023).

### theme:advanced_overhead_conductors
- id: `theme:advanced_overhead_conductors` · name_en: "Advanced overhead conductors" · name_zh: "节能导线与复合材料导线" · value_chain_position: upstream · parent_sub_theme: `theme:grid_equipment_supply`
- defining_activities: manufacturing high-temperature/low-sag conductors (composite-core, zirconium alloys); developing lower-loss conductor grades for corridor upgrades; reconductoring existing lines to raise capacity without new rights-of-way; qualifying conductor hardware/fittings systems.
- distinct_from: `theme:transmission_hvdc_cabling` (existing) — underground/submarine insulated cable systems vs overhead bare conductors; distinct from `theme:dynamic_line_rating_sensors` — conductor hardware vs rating sensors.
- exclusions: insulated power cable (existing row); copper rod/wire commodity (copper_wire_cable under copper_steel_electrify).
- china_relevance: high — 节能导线/碳纤维导线 is a named Chinese grid-materials category (CEC/国网物资 reporting).
- confidence: medium
- sources: CIGRE, technical brochures on overhead conductors (SC B2); U.S. DOE, "National Transmission Needs Study" (2023, advanced-conductor capacity context); 中国电力企业联合会, 《中国电力行业年度发展报告》.

### theme:grid_equipment_supply (sub_theme)
- id: `theme:grid_equipment_supply` · name_en: "Grid Equipment Supply" · name_zh: "电网设备供应" · value_chain_position: upstream
- note: Groups materials and primary/secondary equipment supply — electrical steel, protection systems, compensation, HVDC/UHV hardware, conductors, line EPC.
- nominated_from: research:research/theme_graph/micro_expansion_20261021/C1_MICRO_RESEARCH.md
- parent: theme:grid_electrification

### theme:grid_software_flexibility (sub_theme)
- id: `theme:grid_software_flexibility` · name_en: "Grid Software & Flexibility" · name_zh: "电网软件与灵活性" · value_chain_position: enabler
- note: Groups the software/flexibility tier — grid operating software, AMI, VPP, grid batteries, grid-forming technology, line sensing, microgrids.
- nominated_from: research:research/theme_graph/micro_expansion_20261021/C1_MICRO_RESEARCH.md
- parent: theme:grid_electrification

---

## theme:solar — Solar

Existing rows preserved: sub_theme `theme:pv_manufacturing_chain` (micros `theme:polysilicon_solar_feedstock`, `theme:pv_cell_module_manufacturing`), micros `theme:solar_inverters`, `theme:solar_trackers_bos`.

**Sub-theme grouping.** Three new sub_themes: `theme:pv_upstream_supply` (between feedstock and cells: ingot/wafer growth, quartz crucibles, glass/encapsulants, metalization pastes — the material steps the existing chain rows bracket); `theme:pv_technology_frontiers` (device-system transitions: perovskite/tandem, thin film); `theme:pv_downstream_deployment` (project-tier: BIPV, agrivoltaics, floating PV, O&M, development/EPC, recycling). One row stays direct: `theme:pv_manufacturing_equipment` (the machines that make cells/modules — enabler of the manufacturing chain).

**Theme-tier candidates (prose only).** None as rows. Solar-plus-storage hybrid plants sit deliberately beside `grid_scale_battery_storage` (grid_electrification) and `solar_inverters` (existing); PV cell-technology generations (TOPCon/HJT/BC) remain inside the existing `pv_cell_module_manufacturing` row rather than as subsets.

### theme:silicon_ingot_wafer_growth
- id: `theme:silicon_ingot_wafer_growth` · name_en: "Silicon ingot & wafer growth" · name_zh: "单晶拉棒与硅片" · value_chain_position: upstream · parent_sub_theme: `theme:pv_upstream_supply`
- defining_activities: growing monocrystalline ingots by Czochralski pulling; slicing wafers by diamond-wire sawing with thin-wire roadmaps; upgrading/sideways-purifying feedstock into wafer-grade; scaling large-format wafer platforms (M10/G12-class).
- distinct_from: `theme:polysilicon_solar_feedstock` (existing) — polysilicon feedstock production vs the ingot/wafer step that consumes it; distinct from `theme:pv_cell_module_manufacturing` — wafer input vs cell/module processing.
- exclusions: polysilicon plants (existing row); semiconductor-grade wafer makers (semiconductor value chain).
- china_relevance: high — 硅片/拉棒 is dominated by Chinese capacity (CPIA 路线图 standing data).
- confidence: high
- sources: ITRPV, "International Technology Roadmap for Photovoltaic" (wafering chapter); CPIA（中国光伏行业协会）, 《中国光伏产业发展路线图》; IEA, "Special Report on Solar PV Global Value Chains" (2022).

### theme:quartz_crucible_consumables
- id: `theme:quartz_crucible_consumables` · name_en: "Quartz crucible consumables" · name_zh: "石英坩埚耗材" · value_chain_position: upstream · parent_sub_theme: `theme:pv_upstream_supply`
- defining_activities: manufacturing fused-silica crucibles for ingot pulling; qualifying crucible purity/lifetime against multi-load campaigns; recycling inner-liner sand and crucible scrap; scaling crucible supply with puller fleets.
- distinct_from: `theme:silicon_ingot_wafer_growth` — the consumable the puller consumes vs the wafer product; a recognized auxiliary-material layer in PV supply-chain reporting.
- exclusions: semiconductor crucibles (semiconductor chain); generic quartzware.
- china_relevance: high — 石英坩埚 is a named 辅材 supply topic in Chinese PV trade press (硅业分会/CPIA).
- confidence: medium
- sources: 中国有色金属工业协会硅业分会, 硅产业链市场报告系列; CPIA（中国光伏行业协会）, 《中国光伏产业发展路线图》(辅材章节); ITRPV, materials chapter.

### theme:pv_glass_encapsulant_materials
- id: `theme:pv_glass_encapsulant_materials` · name_en: "PV glass & encapsulant materials" · name_zh: "光伏玻璃与封装胶膜" · value_chain_position: upstream · parent_sub_theme: `theme:pv_upstream_supply`
- defining_activities: rolling ultra-clear tempered glass for module fronts/backs; extruding EVA/POE encapsulant films and backsheets; qualifying optical/transmission and weathering grades; scaling thin-glass and glass-glass formats for dual-glass modules.
- distinct_from: `theme:pv_cell_module_manufacturing` (existing) — module assembly vs the encapsulant/front-glass materials layer; a distinct 辅材 segment in CPIA roadmaps.
- exclusions: module assembly itself; construction glass without PV grades.
- china_relevance: high — 光伏玻璃/胶膜 is a globally dominant Chinese materials segment (CPIA/trade press).
- confidence: high
- sources: CPIA（中国光伏行业协会）, 《中国光伏产业发展路线图》; ITRPV, "International Technology Roadmap for Photovoltaic" (module materials chapter); IEA, "Special Report on Solar PV Global Value Chains" (2022).

### theme:pv_metalization_pastes
- id: `theme:pv_metalization_pastes` · name_en: "PV metalization pastes" · name_zh: "光伏银浆与金属化" · value_chain_position: upstream · parent_sub_theme: `theme:pv_upstream_supply`
- defining_activities: formulating silver pastes for front/back contacts and busbars; developing silver-reduced/copper-plating metalization routes; qualifying paste-screen-fire windows per cell architecture; supplying fine-line pastes for TOPCon/HJT contact systems.
- distinct_from: `theme:pv_cell_module_manufacturing` (existing) — cell production vs the contact-material consumable layer; recognized as a distinct 辅材 line in CPIA roadmaps.
- exclusions: silver bullion; busbar ribbon without paste mechanism.
- china_relevance: high — 光伏银浆国产化 is an established Chinese materials story (CPIA/trade press).
- confidence: medium
- sources: CPIA（中国光伏行业协会）, 《中国光伏产业发展路线图》(辅材章节); ITRPV, metalization chapter; Fraunhofer ISE, "Photovoltaics Report" (annual).

### theme:pv_manufacturing_equipment
- id: `theme:pv_manufacturing_equipment` · name_en: "PV manufacturing equipment" · name_zh: "光伏制造设备" · value_chain_position: enabler · parent_sub_theme: none (direct child of theme)
- defining_activities: building cell-process toolsets (texturing, diffusion, PECVD/ALD, plating); supplying module-line equipment (stringers, laminators, testers); engineering turnkey cell/module line capacity; upgrading lines across cell-architecture transitions.
- distinct_from: `theme:pv_cell_module_manufacturing` (existing) — the machines that make cells/modules vs the cell/module producers; mirrors the semicap_equipment distinction in the PV chain.
- exclusions: ingot pullers/wafer saws as such (upstream row scope boundary — equipment sellers remain here); consumable materials.
- china_relevance: high — 光伏设备 is an export-strong Chinese segment (CPIA equipment data).
- confidence: high
- sources: CPIA（中国光伏行业协会）, 《中国光伏产业发展路线图》(设备章节); ITRPV, "International Technology Roadmap for Photovoltaic" (process/equipment roadmaps); SEMI, photovoltaic standards program.

### theme:perovskite_tandem_photovoltaics
- id: `theme:perovskite_tandem_photovoltaics` · name_en: "Perovskite & tandem photovoltaics" · name_zh: "钙钛矿及叠层电池" · value_chain_position: midstream · parent_sub_theme: `theme:pv_technology_frontiers`
- defining_activities: developing perovskite single-junction and perovskite/silicon tandem devices; scaling coating/deposition routes (spin, slot-die, evaporation) to module area; qualifying stability/encapsulation for field lifetimes; piloting tandem production lines beside silicon capacity.
- distinct_from: `theme:pv_cell_module_manufacturing` (existing) — incumbent crystalline-silicon cell production vs the new absorber/tandem device system.
- exclusions: mainstream PERC/TOPCon/HJT silicon lines (existing row); research-only perovskite without module-area scaling.
- china_relevance: high — 钙钛矿 is a heavily invested Chinese PV frontier (CPIA/trade press, pilot lines).
- confidence: medium
- sources: NREL, perovskite database and efficiency-chart publications; ITRPV, "International Technology Roadmap for Photovoltaic" (emerging-technology chapter); Fraunhofer ISE, "Photovoltaics Report".

### theme:thin_film_pv_modules
- id: `theme:thin_film_pv_modules` · name_en: "Thin-film PV modules (CdTe/CIGS)" · name_zh: "薄膜光伏组件" · value_chain_position: midstream · parent_sub_theme: `theme:pv_technology_frontiers`
- defining_activities: depositing CdTe/CIGS absorbers on glass at module scale; integrating front contacting and encapsulation in glass-glass laminates; qualifying thin-film yield/energy-yield vs c-Si benchmarks; running high-throughput glass-to-glass lines.
- distinct_from: `theme:perovskite_tandem_photovoltaics` — established compound thin-film production vs emerging perovskite systems; distinct from `theme:pv_cell_module_manufacturing` — non-silicon device mechanism.
- exclusions: a-Si (commercially marginal); c-Si modules.
- china_relevance: medium — 薄膜光伏 is a small domestic niche vs c-Si dominance (CPIA data), pilot lines only.
- confidence: medium
- sources: U.S. DOE, "Solar Photovoltaics Supply Chain Review" (2022, CdTe chapter); NREL, "U.S. Solar Photovoltaic System and Energy Storage Cost Benchmark" series; IEA, "Special Report on Solar PV Global Value Chains" (2022).

### theme:building_integrated_pv
- id: `theme:building_integrated_pv` · name_en: "Building-integrated PV (BIPV)" · name_zh: "光伏建筑一体化（BIPV）" · value_chain_position: downstream · parent_sub_theme: `theme:pv_downstream_deployment`
- defining_activities: manufacturing PV products that double as roofing/facade/glazing elements; engineering weatherproof mounting and electrical integration into buildings; certifying fire/structural building-code compliance; delivering BIPV projects with building envelope trades.
- distinct_from: `theme:pv_project_development_epc` — conventional ground/rooftop project build vs building-envelope-integrated product systems; distinct from `theme:solar_trackers_bos` (existing) — utility BOS hardware vs building-envelope products.
- exclusions: standard rooftop rack-mounted PV; solar thermal facades.
- china_relevance: high — 光伏建筑一体化 is policy-pushed in China (整县推进/绿色建筑 standards).
- confidence: medium
- sources: IEA PVPS, Task 15 "Building Integrated PV" reports; Fraunhofer ISE, BIPV guidance publications; 住建部, 绿色建筑/光伏建筑一体化标准文件.

### theme:agrivoltaic_dual_use_systems
- id: `theme:agrivoltaic_dual_use_systems` · name_en: "Agrivoltaic dual-use systems" · name_zh: "农光互补系统" · value_chain_position: downstream · parent_sub_theme: `theme:pv_downstream_deployment`
- defining_activities: engineering elevated/bifacial arrays preserving crop machinery lanes; co-managing light, water and crop-yield trade-offs; contracting with agricultural operators for land dual-use; qualifying dual-use land-classification outcomes.
- distinct_from: `theme:pv_project_development_epc` — dual-use agricultural system design/economics vs generic project EPC; distinct from `theme:floating_pv_systems` — land agriculture vs water siting.
- exclusions: fencing-only solar grazing without engineered dual-use; greenhouse hydroponics without PV.
- china_relevance: high — 农光/渔光互补 is a mass-scale Chinese deployment category (国家能源局 project statistics).
- confidence: medium
- sources: Fraunhofer ISE, "Agrivoltaics: Opportunities for Agriculture and the Energy Transition"; IEA PVPS, agrivoltaics task reports; 国家能源局, 光伏发电建设运行统计（年度）.

### theme:floating_pv_systems
- id: `theme:floating_pv_systems` · name_en: "Floating PV systems" · name_zh: "水上漂浮光伏" · value_chain_position: downstream · parent_sub_theme: `theme:pv_downstream_deployment`
- defining_activities: engineering floats, moorings and anchoring for reservoirs/lakes; managing water-level/survival design loads; integrating floating inverters/substations on platform arrays; delivering reservoir-scale FPV plants.
- distinct_from: `theme:agrivoltaic_dual_use_systems` — water-sited float/mooring engineering vs land agriculture; distinct from `theme:solar_trackers_bos` (existing) — floating structures vs tracker/BOS hardware.
- exclusions: offshore (marine) PV; land-based systems.
- china_relevance: high — 漂浮式光伏 is a leading Chinese deployment niche (CPIA/国家能源局 statistics).
- confidence: medium
- sources: World Bank / SERIS, "Where Sun Meets Water: A Report on Floating Solar"; IEA PVPS, floating PV task reports; 国家能源局, 光伏发电建设运行统计（年度）.

### theme:pv_recycling_end_of_life
- id: `theme:pv_recycling_end_of_life` · name_en: "PV recycling & end-of-life" · name_zh: "组件回收与退役处理" · value_chain_position: downstream · parent_sub_theme: `theme:pv_downstream_deployment`
- defining_activities: decommissioning and transporting retired modules; separating glass/silicon/metals via delamination and recovery processes; recovering high-value silicon and silver streams; certifying recycled-content and compliance under e-waste regimes.
- distinct_from: `theme:pv_operations_maintenance` — in-life O&M vs end-of-life processing; a distinct downstream mechanism scaling with early retirements.
- exclusions: repowering (development scope); generic e-waste without PV mechanism.
- china_relevance: medium — 退役回收 is an emerging Chinese program line (CPIA/trade press), fleet still young.
- confidence: medium
- sources: IRENA / IEA-PVPS, "End-of-Life Management: Solar Photovoltaic Panels"; EU WEEE directive (PV collection/recovery) framework documents; CPIA（中国光伏行业协会）, 回收相关专题报告.

### theme:pv_operations_maintenance
- id: `theme:pv_operations_maintenance` · name_en: "PV plant operations & maintenance" · name_zh: "电站运维（O&M）" · value_chain_position: downstream · parent_sub_theme: `theme:pv_downstream_deployment`
- defining_activities: operating plant SCADA and performance monitoring; executing module cleaning (including robotic), inverter and tracker servicing; diagnosing underperformance with aerial/IV-curve inspection; guaranteeing availability/PR under O&M contracts.
- distinct_from: `theme:pv_project_development_epc` — operate-and-maintain vs develop-and-build; distinct from `theme:dcim_energy_management_software` (data_center_power) — plant-side renewable ops vs facility DC software.
- exclusions: construction itself; asset ownership without service contracts (development row scope).
- china_relevance: high — 光伏运维 is a large domestic services segment (CPIA/行业统计).
- confidence: high
- sources: SolarPower Europe, "O&M Best Practice Guidelines"; IEA PVPS, Task 13 performance/reliability reports; NREL, "U.S. Solar Photovoltaic System and Energy Storage Cost Benchmark" (O&M cost lines).

### theme:pv_project_development_epc
- id: `theme:pv_project_development_epc` · name_en: "PV project development & EPC" · name_zh: "电站开发与 EPC" · value_chain_position: downstream · parent_sub_theme: `theme:pv_downstream_deployment`
- defining_activities: developing sites (land, interconnection, permitting); engineering and procuring utility-scale/distributed plants; constructing and commissioning PV power plants; selling plants/PPAs into operating portfolios.
- distinct_from: `theme:pv_operations_maintenance` — build vs operate; distinct from `theme:solar_trackers_bos` (existing) — project execution vs BOS hardware supply.
- exclusions: module/BOS/inverter manufacturing; O&M services (separate row).
- china_relevance: high — 电站开发/EPC is the core Chinese downstream segment (国家能源局 installation statistics).
- confidence: high
- sources: IEA PVPS, "Trends in Photovoltaic Applications" (annual); SolarPower Europe, "Global Market Outlook"; 国家能源局, 光伏发电建设运行统计（年度）.

### theme:pv_upstream_supply (sub_theme)
- id: `theme:pv_upstream_supply` · name_en: "PV Upstream Supply" · name_zh: "光伏上游供给" · value_chain_position: upstream
- note: Groups the material steps between feedstock and cells — ingot/wafer, crucibles, glass/encapsulants, metalization pastes — inside the existing manufacturing chain framing.
- nominated_from: research:research/theme_graph/micro_expansion_20261021/C1_MICRO_RESEARCH.md
- parent: theme:solar

### theme:pv_technology_frontiers (sub_theme)
- id: `theme:pv_technology_frontiers` · name_en: "PV Technology Frontiers" · name_zh: "光伏技术前沿" · value_chain_position: midstream
- note: Groups device-system transitions outside incumbent c-Si production — perovskite/tandem and thin-film — distinct from the existing cell/module manufacturing row.
- nominated_from: research:research/theme_graph/micro_expansion_20261021/C1_MICRO_RESEARCH.md
- parent: theme:solar

### theme:pv_downstream_deployment (sub_theme)
- id: `theme:pv_downstream_deployment` · name_en: "PV Downstream Deployment" · name_zh: "光伏下游部署" · value_chain_position: downstream
- note: Groups the project tier — BIPV, agrivoltaics, floating PV, O&M, development/EPC, recycling — downstream of manufacturing.
- nominated_from: research:research/theme_graph/micro_expansion_20261021/C1_MICRO_RESEARCH.md
- parent: theme:solar

---

## Respected kills and deliberate non-rows

Carried from `research/theme_graph/hierarchy_content/C1_CATEGORIES_AND_COMPUTE_ENERGY.md` REJECTED table and the C2/C3 mechanisms, these candidates were deliberately NOT proposed:
- Generic "advanced packaging" supply-chain row (rejected as duplicate of `hbm_packaging` supply-chain angle) — instead, packaging appears only via component (`abf_package_substrate_supply`), equipment (`advanced_packaging_assembly_equipment`) and multi-die (`chiplet_multidie_compute`) mechanisms.
- `smr_modular_reactors` (rejected as subset of `reactor_technology`) — no SMR row re-proposed; advanced fuel forms (HALEU/TRISO) are a genuinely distinct upstream mechanism.
- Nuclear services/refurbishment stance bucket — no outage-services row proposed.
- `hyperscaler_neocloud_hosting` — no cloud/hosting row anywhere.
- Immersion cooling — deliberately not split out; it is a modality inside the existing `liquid_cooling_thermal` row (avoids subset-vs-parent).
- Stance/AVOID class names ("monopolists", "specialists", "unhedged", "legacy") — none used anywhere.
- Semiconductor process materials (photoresist, specialty gas, target, slurry) — flagged as a theme-tier prose candidate under semicap_equipment, never a row under an equipment theme.
- Grid cybersecurity — belongs to the cybersecurity theme, no row here.

## Sources standard

Every micro-theme above cites ≥2 named public, non-vendor-family references: industry-association roadmaps (SEMI, IEEE IRDS, ITRPV, CPIA, IEC/IEEE/ISO/JEDEC standards bodies), regulator/agency documents (DOE, FERC, NERC, EPA, NIST, 国家能源局, 工信部, 住建部, 国家原子能机构), official industry-association statistics (中国电力企业联合会, 中国核能行业协会, 中国钢铁工业协会, 中国有色金属工业协会硅业分会, 中国半导体行业协会, 中国电动汽车充电基础设施促进联盟, ODCC), intergovernmental reports (IEA, IRENA, OECD-NEA, IAEA, World Bank), trade press (World Nuclear News, PV Magazine, Semiconductor Engineering, EE Times, 北极星电力网, 《半导体行业观察》), academic/industry conferences (IEEE ITC, SWTest, SPIE Advanced Lithography, SEMI-THERM, APEC) and market-research series (TrendForce, Yole Group, 赛迪顾问/CCID). No issuer names appear anywhere in row content. No vendor theme families are used.
