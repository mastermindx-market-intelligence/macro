# theme-graph hierarchy content C3 — materials, health & solar micro-themes

Status: DRAFT taxonomy content for seat ratification — display-only navigation vocabulary, no tickers, no weights.
Decision: DEC:GMI-THEME-HIERARCHY-ON-CROSSWALK (spec PR #8585)
origin/main read at: a0fc9f894fa15ec7674abe0cae719634454aea06
asserted_on: WC4_MERGE_DATE (placeholder, seat-stamped)
Lane: gmi_hier_c3

## Micro-themes

### theme:rare_earth_critical_min — Rare Earth & Critical Minerals

| slug | name_en | name_zh | parents | nominated_from | evidence | rationale |
| rare_earth_refining_ex_china | Rare-earth processing outside China | 中国以外稀土冶炼加工 | rare_earth_critical_min | research:config/theme_thesis_registry.yml | config/theme_pathways.yml:882 "Rare earth processing & refining (ex-China)"; config/theme_thesis_registry.yml:1197 "Rare earth elements (Nd, Pr, Dy) are essential" | Western refining capacity named as the diversification bottleneck versus mining alone. |
| ndfeb_permanent_magnets | NdFeB permanent magnets | 钕铁硼永磁材料 | rare_earth_critical_min | research:config/theme_thesis_registry.yml | config/trade_flow_codes.yml:64 "Neodymium and dysprosium compounds are essential"; config/theme_thesis_registry.yml:1221 "Rare earth magnets are the downstream bottleneck" | Downstream magnet segment distinct from upstream ore and refining in house trade and thesis text. |
| critical_mineral_mining_development | Critical-mineral mining and development | 关键矿产开采与开发 | rare_earth_critical_min | basket:baskets:critical_minerals | data/baskets/membership.json:4638 "Rare earths, lithium, antimony and other policy-sensitive critical-mineral names."; config/theme_pathways.yml:890 "Critical mineral miners & processors" | Basket thesis names the producer/developer segment policy treats as the direct beneficiary layer. |
| gallium_germanium_supply_chain | Gallium and germanium supply chain | 镓与锗供应链 | rare_earth_critical_min | research:config/theme_thesis_registry.yml | config/theme_thesis_registry.yml:1188 "export controls on gallium, germanium, and rare earth magnets"; config/theme_thesis_registry.yml:1212 "export controls on gallium, germanium, rare earth magnets" | Export-control metals named alongside magnets as a distinct policy-sensitive supply segment. |

### theme:copper_steel_electrify — Copper, Steel & Electrification

| slug | name_en | name_zh | parents | nominated_from | evidence | rationale |
| copper_mine_supply_constraint | Copper mine supply and grade | 铜矿供给与品位约束 | copper_steel_electrify | research:config/theme_thesis_registry.yml | config/theme_pathways.yml:938 "Copper mine grade decline & permitting"; config/theme_thesis_registry.yml:1269 "grade depletion at major copper mines is" | Mine-grade and permitting lag named as the supply bottleneck separate from fabrication. |
| refined_copper_products | Refined copper products | 精炼铜产品 | copper_steel_electrify | research:config/theme_thesis_registry.yml | config/trade_flow_codes.yml:253 "Refined copper cathodes"; config/trade_flow_codes.yml:258 "primary feedstock for EV wiring, grid cable" | Trade codes distinguish cathode feedstock for electrification wiring from mine output. |
| structural_steel_electrification | Structural steel for electrification build-out | 电气化建设用结构钢 | copper_steel_electrify | research:config/theme_thesis_registry.yml | config/trade_flow_codes.yml:275 "Hot-rolled steel plate (other)"; config/trade_flow_codes.yml:280 "Steel plate used in grid infrastructure," | Steel plate demand tied to grid and EV infrastructure, not copper mining. |
| copper_wire_and_cable | Copper wire and cable | 铜线电缆 | copper_steel_electrify | basket:baskets:reshoring | config/theme_thesis_registry.yml:1290 "Grid and EV demand pull"; config/theme_pathways.yml:930 "Reshoring & electrification-driven metals demand" | Fabrication segment for grid and EV pull distinct from producers and mine supply. |

### theme:ag_fertilizer — Agriculture & Fertilizer

| slug | name_en | name_zh | parents | nominated_from | evidence | rationale |
| nitrogen_fertilizer_production | Nitrogen fertilizer production | 氮肥生产 | ag_fertilizer | research:config/theme_thesis_registry.yml | config/theme_thesis_registry.yml:1342 "Nitrogen fertilizer is manufactured from natural gas"; config/theme_pathways.yml:993 "Natural gas input cost for nitrogen fertilizer" | Haber-Bosch nitrogen segment named separately from potash/phosphate in pathways. |
| potash_phosphate_nutrients | Potash and phosphate nutrients | 钾肥与磷肥 | ag_fertilizer | research:config/theme_thesis_registry.yml | config/theme_pathways.yml:1000 "Fertilizer producers (nitrogen / potash / phosphate)"; config/theme_thesis_registry.yml:1344 "European nitrogen capacity — removing 15-20% of global nitrogen supply" | Pathways label splits nitrogen from other nutrient fertilizers. |
| precision_agriculture_platforms | Precision agriculture platforms | 精准农业平台 | ag_fertilizer | research:config/theme_thesis_registry.yml | config/theme_thesis_registry.yml:1333 "climate-driven yield volatility is forcing precision agriculture"; config/theme_pathways.yml:1007 "Precision agriculture technology" | Agronomic data platforms named as downstream of input-cost pressure, not fertilizer molecules. |

### theme:medical_devices — Medical Devices

| slug | name_en | name_zh | parents | nominated_from | evidence | rationale |
| ai_medical_imaging_modalities | AI medical imaging modalities | AI医学影像设备 | medical_devices | research:config/theme_thesis_registry.yml | config/theme_thesis_registry.yml:1055 "AI-enabled medical devices (robotic surgical systems, AI-powered imaging"; config/theme_thesis_registry.yml:1056 "modalities, remote patient monitoring) generate data" | Imaging modalities named as an AI-device segment apart from monitoring and implants. |
| remote_patient_monitoring | Remote patient monitoring | 远程患者监测 | medical_devices | research:config/theme_thesis_registry.yml | config/theme_thesis_registry.yml:1056 "modalities, remote patient monitoring) generate data"; config/theme_thesis_registry.yml:1079 "Chronic disease management requires always-on monitoring" | Continuous monitoring segment named in mechanism and winner-class vocabulary. |
| surgical_implants_instruments | Surgical implants and instruments | 外科植入物与器械 | medical_devices | basket:baskets:managed_care | config/theme_pathways.yml:1068 "Surgical device & implant manufacturers"; config/theme_thesis_registry.yml:1060 "contracts on an installed base create recurring revenue" | Implant and instrument manufacturers named without adopting the robotics platform lane. |

### theme:diagnostics_lifesci — Diagnostics & Life-Science Tools

| slug | name_en | name_zh | parents | nominated_from | evidence | rationale |
| liquid_biopsy_assays | Liquid biopsy assays | 液体活检检测 | diagnostics_lifesci | research:config/theme_thesis_registry.yml | config/theme_thesis_registry.yml:1124 "Liquid biopsy detects"; config/theme_thesis_registry.yml:1114 "earlier disease detection (liquid biopsy, proteomics)" | Blood-based early detection named as its own clinical category in thesis text. |
| ngs_sequencing_consumables | NGS sequencing consumables | 新一代测序耗材 | diagnostics_lifesci | research:config/theme_thesis_registry.yml | config/theme_thesis_registry.yml:1123 "Next-generation sequencing (NGS) costs have fallen"; config/theme_thesis_registry.yml:1144 "Installed base of sequencers drives recurring consumable revenue" | Sequencer installed base and consumable revenue model distinct from instruments alone. |
| proteomics_discovery_platforms | Proteomics discovery platforms | 蛋白质组学发现平台 | diagnostics_lifesci | research:config/theme_thesis_registry.yml | config/theme_thesis_registry.yml:1126 "Proteomics platforms (proximity ligation, mass spec)"; config/theme_thesis_registry.yml:1139 "platforms creating reimbursable liquid biopsy market" | Proteomics named as a multi-omics pillar beside sequencing and liquid biopsy. |
| life_science_lab_instruments | Life-science laboratory instruments | 生命科学实验室仪器 | diagnostics_lifesci | research:config/theme_thesis_registry.yml | config/trade_flow_codes.yml:307 "Instruments and apparatus for measuring/checking (lab instruments)"; config/trade_flow_codes.yml:312 "Life-science instruments (mass specs, flow cytometers, sequencers, etc.)" | Capital-equipment import category names the instruments segment for R&D spend. |
| diagnostic_reagents_kits | Diagnostic reagents and kits | 诊断试剂与试剂盒 | diagnostics_lifesci | research:config/theme_thesis_registry.yml | config/trade_flow_codes.yml:317 "Diagnostic reagents and kits"; config/trade_flow_codes.yml:322 "Reagent and assay kit imports track lab diagnostic volume across clinical" | Reagent kit trade line separates recurring assay volume from capital instruments. |

### theme:solar — Solar

| slug | name_en | name_zh | parents | nominated_from | evidence | rationale |
| pv_cell_module_manufacturing | Photovoltaic cell and module manufacturing | 光伏电池与组件制造 | solar | research:config/theme_thesis_registry.yml | config/theme_thesis_registry.yml:802 "subsidize domestic solar cell and module"; config/trade_flow_codes.yml:91 "Photovoltaic cells (solar cells, unassembled)" | Domestic cell and module manufacturing named separately from upstream silicon and downstream BOS. |
| polysilicon_solar_feedstock | Polysilicon solar feedstock | 光伏级多晶硅原料 | solar | research:config/theme_thesis_registry.yml | config/trade_flow_codes.yml:120 "Polysilicon is the upstream raw material"; config/trade_flow_codes.yml:120 "raw material for both solar wafers and" | Upstream polysilicon segment named before cells and modules in trade rationale. |
| solar_balance_of_system | Solar balance-of-system equipment | 光伏系统配套设备 | solar | research:config/theme_thesis_registry.yml | config/theme_thesis_registry.yml:823 "tracker_and_balance_of_system_domestically_sourced"; config/theme_thesis_registry.yml:825 "Trackers and inverters meeting domestic content criteria capture the" | Trackers and inverters grouped as BOS distinct from module fabs. |
| pv_inverters_grid_transformers | PV inverters and grid transformers | 光伏逆变器与电网变压器 | solar | research:config/theme_thesis_registry.yml | config/theme_pathways.yml:1170 "Solar inverters & grid-interconnection transformers"; config/theme_pathways.yml:1174 "Inverter supply and grid-interconnection transformer availability" | Project-execution bottleneck named for inverters and interconnection transformers. |

## CROSS-LANE — segments you saw that belong to another lane's theme (one line each: candidate, owning theme, evidence path:line). Do not mint them.

- ai_robotic_surgical_platforms — robotics_automation (optional second parent medical_devices per M1) — config/theme_thesis_registry.yml:1066
- gold_silver_pgm_uranium_miners — nuclear_power / out-of-V1 gold — data/baskets/membership.json basket keys gold_miners, uranium_miners (C2/M2)
- lithium_battery_chemistry_basket — not one of six C3 themes as primary home — critical_minerals basket thesis mentions lithium alongside REE
- grid_electrification_transmission — grid_electrification — config/theme_pathways.yml solar__bottleneck shares transformer theme with grid lane C1
- glp1_obesity_drug_supply — glp1_obesity — config/clinical_modalities.yml:65 glp1_named_agents
- contract_research_organizations — diagnostics_lifesci pathway second-order node only; not admitted as micro without stronger neutral segment line — config/theme_pathways.yml:1132

## REJECTED — | candidate | theme | reason |

| candidate | theme | reason |
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
| sequencing_consumable_platform_providers | diagnostics_lifesci | Class slug restates winner class; admitted as ngs_sequencing_consumables neutral segment |
| liquid_biopsy_assay_developers_with_reimbursement_coverage | diagnostics_lifesci | Reimbursement-coverage winner class; neutral assay row admitted instead |
| radiopharmaceutical_radioligand_modality | diagnostics_lifesci | Clinical modality row cites company pipelines; insufficient neutral house segment line without vendor-adjacent rationale text |
| domestic_solar_module_equipment_manufacturers_pathway | solar | Duplicate of pv_cell_module_manufacturing with policy-premium rationale only |
| quantum_computing_crypto_gold_themes | — | Out of V1 top-level themes (L12) |

## GAPS — anything you could not resolve, each with what would close it.

- Vertical `nominated_from` registry id for `mining_copper_economics` / `mining_rare_earth_economics` slices was not stamped on rows because the house vertical registry string (`vertical:<registry>:<slice>`) is not quoted in origin/main config bytes reviewed; slice keys exist only in `research/mining/m1_integration_program/domain/MINING_DOMAIN_DEFINITIONS_M1_2026-09-24.md`. A seat-published registry name would allow vertical nominators for mine-economics slices without duplicating thesis rows.
- `config/theme_pathways.yml` and `config/clinical_modalities.yml` are cited in evidence cells but are not admissible `research:` nominators per CD2; rows use thesis registry or basket nominators instead.
