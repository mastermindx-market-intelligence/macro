# Theme graph hierarchy content C1 — macro-categories, theme→category, compute/energy micro-themes

Status: DRAFT taxonomy content for seat ratification — display-only navigation vocabulary, no tickers, no weights.
Decision: DEC:GMI-THEME-HIERARCHY-ON-CROSSWALK (spec PR #8585)
origin/main read at: 6e8609a633f0623938dd2b41e0975096acef67fb
asserted_on: WC4_MERGE_DATE (placeholder, seat-stamped)
Lane: gmi_hier_c1

**K2 resolutions (one line each).** AI & Technology vs Artificial Intelligence: both are basket shelves for AI-adjacent monitoring (broad mega-cap/infra vs neoclouds/agents); merged under `technology_software` because neither shelf maps to a distinct foresight theme. Semiconductors vs Semiconductors & Hardware: chip-cycle baskets vs non-AI hardware proxy shelf; merged under `semiconductors_hardware` with chip themes on the Semiconductors shelf only. Industrials vs Industrials & Defense: factory automation vs defense/reshoring/space shelves; merged under `industrials_defense` as one capital-goods navigation family. Software: cybersecurity and non-AI software baskets share the Software shelf → `technology_software`. Consumer Cyclical vs Consumer Defensive: kept as **two** categories because membership.json maintains separate cyclical vs defensive staples shelves and no V1 foresight theme spans both.

## Macro-categories

| slug | name_en | name_zh | note | child themes | evidence | rationale |
| --- | --- | --- | --- | --- | --- | --- |
| technology_software | Technology & software | 科技与软件 | basket categories: AI & Technology &#124; Artificial Intelligence &#124; Software. | ai_semiconductors (secondary); cybersecurity; data_center_power (secondary) | data/baskets/membership.json:11 "AI & Technology"; data/baskets/membership.json:2704 "Artificial Intelligence"; data/baskets/membership.json:2835 "Software" | Houses AI-adjacent basket shelves and software baskets; foresight chip themes stay primarily under semiconductors_hardware. |
| semiconductors_hardware | Semiconductors & hardware | 半导体与硬件 | basket categories: Semiconductors &#124; Semiconductors & Hardware. | ai_semiconductors; memory_storage; semicap_equipment | data/baskets/membership.json:3109 "Semiconductors"; data/baskets/membership.json:2968 "Semiconductors & Hardware" | Direct basket categories for the three chip-cycle themes plus the non-AI hardware monitoring shelf. |
| energy_power | Energy & power | 能源与电力 | basket categories: Energy & Power. | data_center_power; nuclear_power; grid_electrification; solar | data/baskets/membership.json:666 "Energy & Power" | Generation, grid, nuclear, and data-center power baskets share one energy shelf. |
| materials_mining | Materials & mining | 材料与矿业 | basket categories: Materials & Mining. | rare_earth_critical_min; ag_fertilizer; copper_steel_electrify (secondary) | data/baskets/membership.json:4138 "Materials & Mining" | Commodity and mining baskets; ag_fertilizer has no dedicated basket and sits with materials-style commodity navigation. |
| industrials_defense | Industrials & defense | 工业与国防 | basket categories: Industrials &#124; Industrials & Defense. | defense_aerospace; robotics_automation; space_satellite; copper_steel_electrify | data/baskets/membership.json:3753 "Industrials"; data/baskets/membership.json:462 "Industrials & Defense" | Automation, defense, reshoring, and space economy baskets. |
| healthcare_lifesciences | Healthcare & life sciences | 医疗与生命科学 | basket categories: Healthcare. | glp1_obesity; medical_devices; diagnostics_lifesci | data/baskets/membership.json:1228 "Healthcare" | Healthcare-themed baskets and foresight healthcare themes. |
| financial_services | Financial services | 金融服务 | basket categories: Financials. | fintech_payments | data/baskets/membership.json:1043 "Financials" | Payments, banks, and insurance monitoring shelves. |
| consumer_cyclical | Consumer cyclical | 可选消费 | basket categories: Consumer Cyclical. | none | data/baskets/membership.json:1324 "Consumer Cyclical" | No V1 foresight theme sits under cyclical consumer baskets yet. |
| consumer_defensive | Consumer defensive | 必需消费 | basket categories: Consumer Defensive. | none | data/baskets/membership.json:1914 "Consumer Defensive" | No V1 foresight theme sits under defensive staples baskets yet. |
| crypto_digital_assets | Crypto & digital assets | 加密与数字资产 | basket categories: Crypto & Digital Assets. | none | data/baskets/membership.json:2478 "Crypto & Digital Assets" | No V1 foresight theme; crypto baskets remain unmapped to foresight-18. |

## Theme → category

| theme | category parent(s) | evidence | rationale |
| --- | --- | --- | --- |
| ai_semiconductors | semiconductors_hardware; technology_software | config/theme_crosswalk.yml:56 "- ai_semiconductors"; config/theme_crosswalk.yml:57 "- ai_infra"; data/baskets/membership.json:3109 "Semiconductors"; data/baskets/membership.json:11 "AI & Technology" | Primary identity is the Semiconductors basket; ai_infra proxy sits on the AI & Technology shelf. |
| memory_storage | semiconductors_hardware | config/theme_crosswalk.yml:75 "- memory_storage"; data/baskets/membership.json:3374 "Semiconductors" | Single primary basket on the Semiconductors shelf. |
| semicap_equipment | semiconductors_hardware | config/theme_crosswalk.yml:92 "- semicap_equipment"; data/baskets/membership.json:3228 "Semiconductors" | WFE basket maps directly to Semiconductors category. |
| data_center_power | energy_power; technology_software | config/theme_crosswalk.yml:108 "- data_center_power"; config/theme_crosswalk.yml:109 "- ai_neoclouds"; data/baskets/membership.json:3447 "Energy & Power"; data/baskets/membership.json:2704 "Artificial Intelligence" | Primary basket is Energy & Power; ai_neoclouds demand driver is on Artificial Intelligence shelf. |
| nuclear_power | energy_power | config/theme_crosswalk.yml:127 "- nuclear_power"; config/theme_crosswalk.yml:128 "- uranium_miners"; data/baskets/membership.json:1722 "Energy & Power" | Nuclear and uranium-proxy baskets share Energy & Power. |
| grid_electrification | energy_power | config/theme_crosswalk.yml:146 "- power_grid"; data/baskets/membership.json:665 "Generation, grid & electrification" | power_grid basket thesis names grid buildout. |
| cybersecurity | technology_software | config/theme_crosswalk.yml:163 "- cybersecurity"; data/baskets/membership.json:3533 "Software" | Cybersecurity basket category is Software. |
| defense_aerospace | industrials_defense | config/theme_crosswalk.yml:179 "- defense"; data/baskets/membership.json:462 "Industrials & Defense" | Defense basket sits on Industrials & Defense shelf. |
| robotics_automation | industrials_defense | config/theme_crosswalk.yml:195 "- robotics_automation"; data/baskets/membership.json:3753 "Industrials" | Robotics basket category is Industrials (not the defense shelf). |
| glp1_obesity | healthcare_lifesciences | config/theme_crosswalk.yml:214 "- obesity_glp1"; data/baskets/membership.json:3881 "Healthcare" | obesity_glp1 basket is Healthcare category. |
| fintech_payments | financial_services | config/theme_crosswalk.yml:231 "- payments_fintech"; data/baskets/membership.json:1502 "Financials" | payments_fintech basket is Financials category. |
| space_satellite | industrials_defense | config/theme_crosswalk.yml:247 "- space_economy"; data/baskets/membership.json:891 "Industrials & Defense" | space_economy basket is Industrials & Defense. |
| rare_earth_critical_min | materials_mining | config/theme_crosswalk.yml:264 "- critical_minerals"; data/baskets/membership.json:4138 "Materials & Mining" | critical_minerals basket is Materials & Mining. |
| copper_steel_electrify | industrials_defense; materials_mining | config/theme_crosswalk.yml:281 "- reshoring"; data/baskets/membership.json:4652 "Industrials & Defense"; config/theme_thesis_registry.yml:1267 "electrification requires high-purity copper cables and busbars. Offshore" | reshoring basket is defense/industrial shelf; thesis mechanism names copper in electrification. |
| ag_fertilizer | materials_mining | config/theme_crosswalk.yml:298 "basket_ids: []"; config/theme_thesis_registry.yml:1331 "Consensus sees agriculture and fertilizer as a purely" | No basket; thesis registry treats ag/fertilizer as a foresight commodity theme under materials navigation. |
| medical_devices | healthcare_lifesciences | config/theme_crosswalk.yml:317 "- managed_care"; data/baskets/membership.json:1228 "Healthcare" | Closest healthcare basket is managed_care. |
| diagnostics_lifesci | healthcare_lifesciences | config/theme_crosswalk.yml:333 "basket_ids: []"; config/theme_thesis_registry.yml:1112 "Consensus views diagnostics as a COVID-recovery normalization story with" | No basket; thesis registry defines diagnostics as its own foresight healthcare theme. |
| solar | energy_power | config/theme_crosswalk.yml:349 "basket_ids: []"; config/theme_thesis_registry.yml:792 "Consensus treats US solar as stranded by Chinese module" | No basket; thesis registry defines solar as an energy foresight theme. |

## Basket-category accounting

| basket category label (verbatim) | category slug or EXCLUDED | evidence (membership.json line) | reason |
| --- | --- | --- | --- |
| AI & Technology | technology_software | membership.json:11 | Absorbed by technology_software macro-category. |
| Artificial Intelligence | technology_software | membership.json:2704 | Same navigation family as AI & Technology and Software shelves. |
| Consumer Cyclical | consumer_cyclical | membership.json:1324 | Distinct cyclical consumer shelf; no V1 theme yet. |
| Consumer Defensive | consumer_defensive | membership.json:1914 | Distinct defensive staples shelf; no V1 theme yet. |
| Crypto & Digital Assets | crypto_digital_assets | membership.json:2478 | Crypto baskets unmapped to foresight-18. |
| Energy & Power | energy_power | membership.json:666 | Power, grid, nuclear, and data-center power baskets. |
| Financials | financial_services | membership.json:1043 | Banks, payments, insurance shelves. |
| Healthcare | healthcare_lifesciences | membership.json:1228 | Healthcare and life-science themes. |
| Industrials | industrials_defense | membership.json:3753 | Factory automation and industrial distribution. |
| Industrials & Defense | industrials_defense | membership.json:462 | Defense, reshoring, space economy shelves. |
| Materials & Mining | materials_mining | membership.json:4138 | Miners and critical minerals baskets. |
| Semiconductors | semiconductors_hardware | membership.json:3109 | Chip-cycle baskets for three semiconductor themes. |
| Semiconductors & Hardware | semiconductors_hardware | membership.json:2968 | Non-AI hardware monitoring shelf. |
| Software | technology_software | membership.json:2835 | Cybersecurity and non-AI software baskets. |
| US Sectors (EW) | EXCLUDED | membership.json:5290 | Equal-weight sector-index baskets are axis B (sector/industry), not semantic-theme navigation per spec K3. |

## Micro-themes

### theme:ai_semiconductors — AI Semiconductors

| slug | name_en | name_zh | parents | nominated_from | evidence | rationale |
| --- | --- | --- | --- | --- | --- | --- |
| hbm_packaging | HBM & advanced packaging | HBM 与先进封装 | ai_semiconductors; memory_storage | vertical:theme_research_registry:hbm_packaging | PR #7870@f12db8bf engine/market_ontology/theme_research_mounts.py:135-142 (frozen by orchestrator C); config/theme_thesis_registry.yml:81 "HBM4 production and shipments are an active" | Federated vertical slice; HBM stacking is distinct from generic accelerator silicon. |
| sic_gan_specialty | SiC / GaN specialty devices | SiC / GaN 特种器件 | ai_semiconductors | vertical:theme_research_registry:sic_gan_specialty | PR #7870@f12db8bf engine/market_ontology/theme_research_mounts.py:135-142 (frozen by orchestrator C); no origin/main corroboration | Federated vertical slice; no additional house line names SiC/GaN on origin/main. |
| gpu_merchant_accelerators | GPUs & merchant accelerators | GPU 与通用加速芯片 | ai_semiconductors | basket:baskets:ai_semiconductors | data/baskets/membership.json:3108 "GPUs, AI accelerators, AI networking silicon and custom-ASIC names." | Merchant GPU and off-the-shelf accelerator silicon, distinct from custom ASIC programs. |
| ai_interconnect_silicon | AI cluster interconnect silicon | AI 集群互联芯片 | ai_semiconductors | research:config/theme_thesis_registry.yml | config/theme_thesis_registry.yml:86 "Cluster scaling increases interconnect demand, but winner status remains" | Mechanism distinguishes interconnect from compute and packaging. |
| custom_asic_silicon | Custom ASIC accelerators | 定制 ASIC 加速芯片 | ai_semiconductors | basket:baskets:ai_semiconductors | data/baskets/membership.json:3114 "custom-asic" | Custom ASIC compute programs, distinct from merchant GPU and merchant accelerator silicon. |

### theme:memory_storage — Memory, HBM & Storage

| slug | name_en | name_zh | parents | nominated_from | evidence | rationale |
| --- | --- | --- | --- | --- | --- | --- |
| hbm_packaging | HBM & advanced packaging | HBM 与先进封装 | ai_semiconductors; memory_storage | vertical:theme_research_registry:hbm_packaging | config/theme_thesis_registry.yml:174 "HBM stacking and qualification make yield and allocation important, while broad" | Same federated row as under ai_semiconductors; memory thesis treats HBM as its own product path. |
| conventional_dram | Conventional DRAM (non-HBM) | 常规 DRAM（非 HBM） | memory_storage | research:config/theme_thesis_registry.yml | config/theme_thesis_registry.yml:165 "DDR5, LPDDR5X, enterprise SSD and other DRAM/NAND activity. The opportunity is" | Commodity DRAM product path separate from HBM-dominant AI memory framing. |
| nand_enterprise_storage | NAND & enterprise storage | NAND 与企业级存储 | memory_storage | basket:baskets:memory_storage | data/baskets/membership.json:3373 "DRAM/HBM, NAND and enterprise storage — the AI-memory cycle." | Basket thesis explicitly names NAND and enterprise storage. |

### theme:semicap_equipment — Semiconductor Equipment (WFE)

| slug | name_en | name_zh | parents | nominated_from | evidence | rationale |
| --- | --- | --- | --- | --- | --- | --- |
| lithography_tools | Lithography tools | 光刻设备 | semicap_equipment | research:config/theme_thesis_registry.yml | config/theme_thesis_registry.yml:258 "etch, deposition, lithography, and metrology tools. Equipment suppliers often" | Lithography exposure as a fab tool class, sibling to etch/deposition and metrology. |
| etch_deposition_equipment | Etch & deposition equipment | 刻蚀与沉积设备 | semicap_equipment | research:config/theme_thesis_registry.yml | config/theme_thesis_registry.yml:258 "etch, deposition, lithography, and metrology tools. Equipment suppliers often" | Etch/deposition named as core WFE process steps. |
| process_metrology_inspection | Process metrology & inspection | 工艺量测与检测 | semicap_equipment | basket:baskets:semicap_equipment | data/baskets/membership.json:3227 "Wafer-fab equipment, metrology and subsystem suppliers — the AI-capex pick-and-shovel layer." | Basket theme highlights metrology subsystem suppliers. |
| wafer_fab_subsystems | Wafer-fab subsystems & components | 晶圆厂设备子系统与零部件 | semicap_equipment | basket:baskets:semicap_equipment | data/baskets/membership.json:3227 "metrology and subsystem suppliers — the AI-capex pick-and-shovel layer." | Basket theme names subsystem suppliers as a layer distinct from process tools. |

### theme:data_center_power — Data Center Power & Cooling

| slug | name_en | name_zh | parents | nominated_from | evidence | rationale |
| --- | --- | --- | --- | --- | --- | --- |
| liquid_cooling_thermal | Liquid cooling & thermal management | 液冷与热管理 | data_center_power | research:config/theme_thesis_registry.yml | config/theme_thesis_registry.yml:359 "liquid cooling mandatory" | Thermal segment mandatory for high-density AI racks. |
| hv_transformers_switchgear | HV transformers & switchgear | 高压变压器与开关设备 | data_center_power; grid_electrification | research:config/theme_thesis_registry.yml | config/theme_thesis_registry.yml:327 "market underestimates that the power-delivery bottleneck (transformers," | Shared power-delivery bottleneck across campus and grid buildout (M3). |
| ups_power_conversion | UPS & power conversion | UPS 与电力转换 | data_center_power | research:config/theme_thesis_registry.yml | config/theme_thesis_registry.yml:363 "High-density power requires custom UPS and conversion architectures;" | Distinct from switchgear: on-site conversion and UPS integration. |

### theme:nuclear_power — Nuclear & SMR Power

| slug | name_en | name_zh | parents | nominated_from | evidence | rationale |
| --- | --- | --- | --- | --- | --- | --- |
| reactor_technology | Reactor technology | 反应堆技术 | nuclear_power | research:research/energy/nuclear_program/REG-PACKET-2026-09-25-nuclear_power.md | research/energy/nuclear_program/REG-PACKET-2026-09-25-nuclear_power.md:70 "Reactor technology" | REG-PACKET slice key for reactor designers. |
| nuclear_components | Nuclear components | 核电部件 | nuclear_power | research:research/energy/nuclear_program/REG-PACKET-2026-09-25-nuclear_power.md | research/energy/nuclear_program/REG-PACKET-2026-09-25-nuclear_power.md:71 "Nuclear components" | REG-PACKET slice for plant components supply chain. |
| fuel_cycle | Fuel cycle | 核燃料循环 | nuclear_power | research:research/energy/nuclear_program/REG-PACKET-2026-09-25-nuclear_power.md | research/energy/nuclear_program/REG-PACKET-2026-09-25-nuclear_power.md:72 "Fuel cycle" | REG-PACKET slice for mining through enrichment. |

### theme:grid_electrification — Grid & Electrification

| slug | name_en | name_zh | parents | nominated_from | evidence | rationale |
| --- | --- | --- | --- | --- | --- | --- |
| hv_transformers_switchgear | HV transformers & switchgear | 高压变压器与开关设备 | data_center_power; grid_electrification | research:config/theme_thesis_registry.yml | config/theme_thesis_registry.yml:718 "Grid load growth requires transmission upgrades, new substations, and" | Same slug as data_center_power row (M3); grid thesis emphasizes transmission and substations. |
| grid_distribution_automation | Grid distribution automation | 电网配电自动化 | grid_electrification | research:config/theme_thesis_registry.yml | config/theme_thesis_registry.yml:719 "distribution automation at unprecedented capital intensity. Transformer" | Distribution automation named separately from bulk transmission hardware. |
| transmission_hvdc_cabling | Transmission & HVDC cabling | 输电与 HVDC 电缆 | grid_electrification | research:config/theme_thesis_registry.yml | config/theme_thesis_registry.yml:746 "High-voltage direct-current (HVDC) cables and specialized underground" | HVDC and specialized cable segment with long lead times. |

## CROSS-LANE

- Endpoint/network/identity security software segments → cybersecurity (C2); evidence data/baskets/membership.json:3530 theme field names security software scope.
- Factory robotics vs autonomous systems slices → robotics_automation (C2); evidence data/baskets/membership.json:3752 "Factory automation, machine vision, surgical robotics and industrial controls."
- GLP-1 therapeutic supply chain → glp1_obesity (C2); evidence data/baskets/membership.json obesity_glp1 basket.
- Rare-earth processing vs critical minerals basket → rare_earth_critical_min (C3); evidence data/baskets/membership.json critical_minerals theme.
- Solar module supply chain → solar (C3); evidence config/theme_thesis_registry.yml:802 "IRA Section 45X tax credits subsidize domestic solar cell and"
- Defense primes vs space economy → defense_aerospace / space_satellite (C2); evidence separate baskets defense and space_economy.

## REJECTED

| candidate | theme | reason |
| --- | --- | --- |
| gpu_asic_monopolists | ai_semiconductors | Stance/winner class (CD4); use neutral gpu_merchant_accelerators instead. |
| advanced_packaging_and_hbm_suppliers | ai_semiconductors | Stance class; covered by federated hbm_packaging micro. |
| high_bandwidth_networking_and_silicon_photonics | ai_semiconductors | Class name embeds stance; ai_interconnect_silicon covers interconnect segment. |
| legacy_cpu_centric_datacenter_builders | ai_semiconductors | AVOID loser class, not a segment (CD4). |
| commodity_memory_undifferentiated | memory_storage | AVOID loser class (CD4). |
| hbm_capable_dram_producers | memory_storage | Stance class; conventional_dram is neutral product path. |
| advanced_packaging_foundries | memory_storage | Duplicate of hbm_packaging supply chain angle. |
| commodity_nand_and_standard_dram_producers | memory_storage | AVOID loser class (CD4). |
| etch_and_deposition_monopolists | semicap_equipment | Stance class; etch_deposition_equipment is neutral. |
| metrology_and_process_control_specialists | semicap_equipment | Stance class; process_metrology_inspection is neutral. |
| legacy_rearview_semi_equipment | semicap_equipment | AVOID loser class (CD4). |
| electrical_equipment_monopolists_in_grid_critical_components | data_center_power | Stance class; hv_transformers_switchgear is neutral. |
| liquid_cooling_and_thermal_management_specialists | data_center_power | Stance class name; admitted as liquid_cooling_thermal. |
| power_conversion_and_ups_system_integrators | data_center_power | Integrator stance framing; ups_power_conversion names product layer. |
| unhedged_power_utilities_in_constrained_grids | data_center_power | AVOID loser class (CD4). |
| smr_technology_developers_with_contracted_revenue | nuclear_power | Stance class; reactor_technology REG-PACKET slice covers reactor design. |
| smr_modular_reactors | nuclear_power | Subset of reactor_technology (REG-PACKET slice); no micro-under-micro adjacency (L6). |
| uranium_fuel_cycle_specialists | nuclear_power | Duplicate of fuel_cycle micro (M2). |
| nuclear_services_and_refurbishment_contractors | nuclear_power | Services/refurb stance bucket; no neutral house line separate from fuel_cycle and reactor_technology. |
| natural_gas_peakers_in_nuclear_ppa_regions | nuclear_power | AVOID loser class (CD4). |
| high_voltage_transformer_and_switchgear_manufacturers | grid_electrification | Stance class; shared hv_transformers_switchgear row. |
| grid_software_and_distribution_automation_vendors | grid_electrification | Vendor wording; admitted as grid_distribution_automation. |
| transmission_line_and_cable_specialists | grid_electrification | Stance class; transmission_hvdc_cabling is neutral. |
| rate_regulated_utilities_with_lagging_recovery_timelines | grid_electrification | AVOID loser class (CD4). |
| quantum_computing | — | Mission scope: new top-level themes such as quantum, crypto, ai_software and gold are out of V1. |
| ai_software | — | Mission scope: new top-level themes such as quantum, crypto, ai_software and gold are out of V1. |
| gold_miners | — | Unmapped basket, not a theme micro. |
| hyperscaler_neocloud_hosting | data_center_power | Owned by ai_neoclouds basket / C2 lane themes, not equipment micro. |
| uranium_miners_proxy | nuclear_power | Basket proxy, not a micro slug (would collide with basket id pattern). |

## GAPS

- SiC / GaN specialty devices lack origin/main corroboration beyond federated PR #7870 slice registration; seat may require a house research line before ratification.
- `copper_steel_electrify` dual category (industrials_defense + materials_mining) rests on reshoring basket and thesis copper mechanism — no dedicated copper/steel basket on origin/main.
