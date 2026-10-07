# theme-graph hierarchy content C3 — materials, health & solar micro-themes

Status: DRAFT taxonomy content for seat ratification — display-only navigation vocabulary, no tickers, no weights.
Decision: DEC:GMI-THEME-HIERARCHY-ON-CROSSWALK (spec PR #8585)
origin/main read at: 96261883beec41fb1a11881ad9b32b3a31cd5f52
asserted_on: WC4_MERGE_DATE (placeholder, seat-stamped)
Lane: gmi_hier_c3

## Micro-themes

### theme:rare_earth_critical_min — Rare Earth & Critical Minerals

| slug | name_en | name_zh | parents | nominated_from | evidence | rationale |
|---|---|---|---|---|---|---|
| rare_earth_separation_refining | Rare-earth separation & refining | 稀土分离与冶炼 | rare_earth_critical_min | research:config/theme_pathways.yml | config/theme_pathways.yml:882 "Rare earth processing & refining"; config/theme_thesis_registry.yml:1197 "Rare earth elements (Nd, Pr, Dy) are essential" | Midstream separation and smelting between mined ore and finished magnet alloys, distinct from mining and from NdFeB fabrication. |
| ndfeb_permanent_magnets | NdFeB permanent magnets | 钕铁硼永磁材料 | rare_earth_critical_min | research:config/theme_thesis_registry.yml | config/trade_flow_codes.yml:64 "Neodymium and dysprosium compounds are essential"; config/theme_thesis_registry.yml:1221 "Rare earth magnets are the downstream bottleneck" | Downstream magnet segment distinct from upstream ore and refining in house trade and thesis text. |
| critical_mineral_mining_development | Critical-mineral mining and development | 关键矿产开采与开发 | rare_earth_critical_min | basket:baskets:critical_minerals | data/baskets/membership.json:4638 "Rare earths, lithium, antimony and other policy-sensitive critical-mineral names."; config/theme_pathways.yml:890 "Critical mineral miners & processors" | Basket thesis names the producer/developer segment policy treats as the direct beneficiary layer. |
| gallium_germanium_supply_chain | Gallium and germanium supply chain | 镓与锗供应链 | rare_earth_critical_min | research:config/theme_thesis_registry.yml | config/theme_thesis_registry.yml:1188 "export controls on gallium, germanium, and rare earth magnets"; config/theme_thesis_registry.yml:1212 "export controls on gallium, germanium, rare earth magnets" | Export-control metals named alongside magnets as a distinct policy-sensitive supply segment. |

### theme:copper_steel_electrify — Copper, Steel & Electrification

| slug | name_en | name_zh | parents | nominated_from | evidence | rationale |
|---|---|---|---|---|---|---|
| copper_mining | Copper mining | 铜矿开采 | copper_steel_electrify | research:config/theme_pathways.yml | config/theme_pathways.yml:946 "Copper producers & recyclers"; config/theme_thesis_registry.yml:1269 "grade depletion at major copper mines is" | Mine and concentrate supply stage, distinct from cathode refining and from wire or cable fabrication. |
| refined_copper | Refined copper (cathode) | 精炼铜（阴极铜） | copper_steel_electrify | research:config/trade_flow_codes.yml | config/trade_flow_codes.yml:253 "Refined copper cathodes"; config/trade_flow_codes.yml:258 "primary feedstock for EV wiring, grid cable" | Smelting and refining to cathode feedstock, distinct from mining and from wire or cable fabrication. |
| structural_steel_electrification | Structural steel for electrification build-out | 电气化建设用结构钢 | copper_steel_electrify | research:config/trade_flow_codes.yml | config/trade_flow_codes.yml:275 "Hot-rolled steel plate (other)"; config/trade_flow_codes.yml:280 "Steel plate used in grid infrastructure," | Steel plate demand tied to grid and EV infrastructure, not copper mining. |
| copper_wire_cable | Copper wire and cable | 铜线电缆 | copper_steel_electrify | research:config/theme_thesis_registry.yml | config/theme_thesis_registry.yml:1288 "copper_wire_and_cable_manufacturers_with_domestic_positioning"; config/theme_thesis_registry.yml:1267 "high-purity copper cables and busbars" | Building and industrial copper wire, cable and busbar fabrication; high-voltage transmission cable systems belong under grid_electrification:transmission_hvdc_cabling (lane C1). |

### theme:ag_fertilizer — Agriculture & Fertilizer

| slug | name_en | name_zh | parents | nominated_from | evidence | rationale |
|---|---|---|---|---|---|---|
| nitrogen_fertilizer_production | Nitrogen fertilizer production | 氮肥生产 | ag_fertilizer | research:config/theme_thesis_registry.yml | config/theme_thesis_registry.yml:1342 "Nitrogen fertilizer is manufactured from natural gas"; config/theme_pathways.yml:993 "Natural gas input cost for nitrogen fertilizer" | Haber-Bosch nitrogen segment named separately from potash/phosphate in pathways. |
| potash_phosphate_nutrients | Potash and phosphate nutrients | 钾肥与磷肥 | ag_fertilizer | research:config/theme_pathways.yml | config/theme_pathways.yml:1000 "Fertilizer producers (nitrogen / potash / phosphate)" | Pathways names potash and phosphate nutrient producers apart from nitrogen-only fertilizer. |
| precision_agriculture_platforms | Precision agriculture platforms | 精准农业平台 | ag_fertilizer | research:config/theme_thesis_registry.yml | config/theme_thesis_registry.yml:1333 "climate-driven yield volatility is forcing precision agriculture"; config/theme_pathways.yml:1007 "Precision agriculture technology" | Agronomic data platforms named as downstream of input-cost pressure, not fertilizer molecules. |

### theme:medical_devices — Medical Devices

| slug | name_en | name_zh | parents | nominated_from | evidence | rationale |
|---|---|---|---|---|---|---|
| medical_imaging | Medical imaging systems | 医学影像系统 | medical_devices | research:config/theme_thesis_registry.yml | config/theme_thesis_registry.yml:1055 "AI-enabled medical devices (robotic surgical systems, AI-powered imaging"; config/theme_thesis_registry.yml:1056 "modalities, remote patient monitoring) generate data" | Imaging modality capital equipment; AI-assisted reads are a current technology driver, not the segment definition. |
| remote_patient_monitoring | Remote patient monitoring | 远程患者监测 | medical_devices | research:config/theme_thesis_registry.yml | config/theme_thesis_registry.yml:1056 "modalities, remote patient monitoring) generate data"; config/theme_thesis_registry.yml:1079 "Chronic disease management requires always-on monitoring" | Continuous monitoring segment named in mechanism and winner-class vocabulary. |
| surgical_implants_instruments | Surgical implants and instruments | 外科植入物与器械 | medical_devices | research:config/theme_pathways.yml | config/theme_pathways.yml:1068 "Surgical device & implant manufacturers" | Implant and instrument manufacturers named without adopting the robotics platform lane. |

### theme:diagnostics_lifesci — Diagnostics & Life-Science Tools

| slug | name_en | name_zh | parents | nominated_from | evidence | rationale |
|---|---|---|---|---|---|---|
| liquid_biopsy_assays | Liquid biopsy assays | 液体活检检测 | diagnostics_lifesci | research:config/theme_thesis_registry.yml | config/theme_thesis_registry.yml:1124 "Liquid biopsy detects"; config/theme_thesis_registry.yml:1114 "earlier disease detection (liquid biopsy, proteomics)" | Blood-based early detection named as its own clinical category in thesis text. |
| genomic_sequencing | Genomic sequencing (NGS) | 基因测序（NGS） | diagnostics_lifesci | research:config/theme_thesis_registry.yml | config/theme_thesis_registry.yml:1123 "Next-generation sequencing (NGS) costs have fallen"; config/theme_thesis_registry.yml:1144 "Installed base of sequencers drives recurring consumable revenue" | Sequencing instruments and their consumable revenue model; distinct from general lab instruments. |
| proteomics_discovery_platforms | Proteomics discovery platforms | 蛋白质组学发现平台 | diagnostics_lifesci | research:config/theme_thesis_registry.yml | config/theme_thesis_registry.yml:1126 "Proteomics platforms (proximity ligation, mass spec)"; config/theme_thesis_registry.yml:1139 "platforms creating reimbursable liquid biopsy market" | Proteomics named as a multi-omics pillar beside sequencing and liquid biopsy. |
| life_science_lab_instruments | Life-science laboratory instruments | 生命科学实验室仪器 | diagnostics_lifesci | research:config/trade_flow_codes.yml | config/trade_flow_codes.yml:307 "Instruments and apparatus for measuring/checking (lab instruments)"; config/trade_flow_codes.yml:312 "Life-science instruments (mass specs, flow cytometers, sequencers, etc.)" | General R&D lab capital equipment; dedicated sequencers belong under genomic_sequencing. |
| diagnostic_reagents_kits | Diagnostic reagents and kits | 诊断试剂与试剂盒 | diagnostics_lifesci | research:config/trade_flow_codes.yml | config/trade_flow_codes.yml:317 "Diagnostic reagents and kits"; config/trade_flow_codes.yml:322 "Reagent and assay kit imports track lab diagnostic volume across clinical" | Reagent kit trade line separates recurring assay volume from capital instruments. |

### theme:solar — Solar

| slug | name_en | name_zh | parents | nominated_from | evidence | rationale |
|---|---|---|---|---|---|---|
| pv_cell_module_manufacturing | Photovoltaic cell and module manufacturing | 光伏电池与组件制造 | solar | research:config/theme_thesis_registry.yml | config/theme_thesis_registry.yml:802 "subsidize domestic solar cell and module"; config/trade_flow_codes.yml:91 "Photovoltaic cells (solar cells, unassembled)" | Domestic cell and module manufacturing named separately from upstream silicon and downstream BOS. |
| polysilicon_solar_feedstock | Polysilicon solar feedstock | 光伏级多晶硅原料 | solar | research:config/trade_flow_codes.yml | config/trade_flow_codes.yml:120 "Polysilicon is the upstream raw material"; config/trade_flow_codes.yml:120 "raw material for both solar wafers and" | Upstream polysilicon segment named before cells and modules in trade rationale. |
| solar_inverters | Solar inverters | 光伏逆变器 | solar | research:config/theme_pathways.yml | config/theme_pathways.yml:1170 "Solar inverters & grid-interconnection transformers" | DC-to-AC power conversion for PV arrays, distinct from trackers or balance-of-system hardware and from grid interconnection transformers (lane C1). |
| solar_trackers_bos | Solar trackers & balance-of-system | 光伏跟踪支架与系统配套 | solar | research:config/theme_thesis_registry.yml | config/theme_thesis_registry.yml:823 "tracker_and_balance_of_system_domestically_sourced"; config/theme_thesis_registry.yml:825 "Trackers and inverters meeting domestic content criteria capture the" | Mechanical trackers and non-inverter BOS hardware; inverters are solar_inverters. |

## CROSS-LANE — segments you saw that belong to another lane's theme (one line each: candidate, owning theme, evidence path:line). Do not mint them.

- ai_robotic_surgical_platforms — robotics_automation (optional second parent medical_devices per M1) — config/theme_thesis_registry.yml:1066
- gold_silver_pgm_miners — out of V1 (no gold top-level theme) — data/baskets/membership.json:4137 "Liquid US-listed gold producers with direct operating leverage"
- uranium_fuel_cycle — nuclear_power:fuel_cycle — data/baskets/membership.json:4435 "Uranium miners, developers and fuel-cycle/enrichment"
- grid_hv_transformers_switchgear — grid_electrification:hv_transformers_switchgear (lane C1) — config/theme_pathways.yml:1170 "Solar inverters & grid-interconnection transformers"
- glp1_obesity_drug_supply — glp1_obesity — config/clinical_modalities.yml:65

## REJECTED — | candidate | theme | reason |

| candidate | theme | reason |
|---|---|---|
| chinese_solar_module_exporters_into_us_market | solar | Stance/geography export class (CD4, M3); house names as impaired incumbent only |
| ira_45x_eligible_us_solar_cell_and_module_manufacturers | solar | Policy-eligibility winner class, not neutral segment slug (M3, M5) |
| ex_china_rare_earth_miners_and_processors | rare_earth_critical_min | Winner-class geography stance; neutral mining covered by critical_mineral_mining_development |
| ev_and_wind_manufacturers_without_secured_non_chinese_supply | rare_earth_critical_min | Loser/AVOID stance class, not a micro segment |
| steel_producers_exposed_to_chinese_overcapacity_dumping | copper_steel_electrify | Loser stance on steel pricing, not neutral steel product segment |
| import_dependent_copper_consuming_manufacturers | copper_steel_electrify | Impaired-incumbent stance node in pathways |
| high_cost_european_chemical_producers_with_gas_exposure | ag_fertilizer | Loser stance class in thesis registry |
| food_processors_thin_margin_ag_inputs | ag_fertilizer | Impaired-incumbent pathway node, not fertilizer segment |
| ai_robotic_surgical_platform_providers | medical_devices | Lane C2 surgical robotics (M1); do not mint or synonym |
| obesity_related_bariatric_devices | medical_devices | GLP-1 displacement impaired node; stance on procedure mix |
| sequencing_consumable_platform_providers | diagnostics_lifesci | Class slug restates winner class; admitted as genomic_sequencing neutral segment |
| liquid_biopsy_assay_developers_with_reimbursement_coverage | diagnostics_lifesci | Reimbursement-coverage winner class; neutral assay row admitted instead |
| radiopharmaceutical_radioligand_modality | diagnostics_lifesci | Clinical modality row cites company pipelines; insufficient neutral house segment line without vendor-adjacent rationale text |
| domestic_solar_module_equipment_manufacturers_pathway | solar | Duplicate of pv_cell_module_manufacturing with policy-premium rationale only |
| lithium_battery_materials | rare_earth_critical_min | lithium mining is inside critical_mineral_mining_development (membership.json:4638 names lithium); battery chemistry has no V1 theme |
| contract_research_organizations | diagnostics_lifesci | pathways second-order node only; no neutral segment line |
| quantum_computing_crypto_gold_themes | — | outside the 18 V1 themes (mission scope) |

## GAPS — anything you could not resolve, each with what would close it.

- Vertical `nominated_from` registry id for `mining_copper_economics` / `mining_rare_earth_economics` slices was not stamped on rows because the house vertical registry string (`vertical:<registry>:<slice>`) is not quoted in origin/main config bytes reviewed; slice keys exist only in `research/mining/m1_integration_program/domain/MINING_DOMAIN_DEFINITIONS_M1_2026-09-24.md`. A seat-published registry name would allow vertical nominators for mine-economics slices without duplicating thesis rows.
- `config/clinical_modalities.yml` is cited as evidence only; it is not an admissible nominator.
