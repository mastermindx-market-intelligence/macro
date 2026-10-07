# theme-graph hierarchy content C2 — Security, Industrial & Health micro-themes

Status: DRAFT taxonomy content for seat ratification — display-only navigation vocabulary, no tickers, no weights.
Decision: DEC:GMI-THEME-HIERARCHY-ON-CROSSWALK (spec PR #8585)
origin/main read at: 5a4ec17c8de9c5bf24993f745383bab2dcffed18
asserted_on: WC4_MERGE_DATE (placeholder, seat-stamped)
Lane: gmi_hier_c2

## Micro-themes

### theme:cybersecurity — Cybersecurity

| slug | name_en | name_zh | parents | nominated_from | evidence | rationale |
|---|---|---|---|---|---|---|
| cloud_native_security_platforms | Cloud-native security platforms | 云原生安全平台 | cybersecurity | research:config/theme_thesis_registry.yml | config/theme_thesis_registry.yml:435 "cloud_native_security_platform_consolidators" | Unified fabrics replacing many point products across the enterprise stack. |
| identity_access_management | Identity and access management | 身份与访问管理 | cybersecurity | research:config/theme_thesis_registry.yml | config/theme_thesis_registry.yml:439 "identity_and_access_management_specialists" | Credential and identity attack surface distinct from endpoint malware detection. |
| behavioral_ai_native_detection | Behavioral and AI-native detection | 行为与AI原生检测 | cybersecurity | research:config/theme_thesis_registry.yml | config/theme_thesis_registry.yml:421 "behavioral/AI-native detection" | Detection paradigm shift when signature updates lag AI-generated variants. |
| endpoint_network_cloud_security | Endpoint, network and cloud security | 端点、网络与云安全 | cybersecurity | basket:baskets:cybersecurity | data/baskets/membership.json:3532 "Endpoint, network, identity and cloud security software." | Basket thesis names the combined perimeter-to-cloud protection scope. |

### theme:defense_aerospace — Defense & Aerospace

| slug | name_en | name_zh | parents | nominated_from | evidence | rationale |
|---|---|---|---|---|---|---|
| missiles_munitions_effects | Missiles, munitions and effects | 导弹、弹药与毁伤效应 | defense_aerospace | research:research/defense_intelligence/D0R_DEFENSE_EQUITY_DRIVER_TAXONOMY.md | research/defense_intelligence/D0R_DEFENSE_EQUITY_DRIVER_TAXONOMY.md:61 "### 2. Missiles, munitions, and effects" | Expendable replenishment and production economics separate from platform primes. |
| missile_propulsion_supply | Missile and munition propulsion supply | 导弹与弹药推进系统供给 | defense_aerospace | research:config/theme_pathways.yml | config/theme_pathways.yml:529 "Missile & munition propulsion supply" | Propulsion bottlenecks constrain guided-munition output rates. |
| defense_sensors_electronics_c2 | Defense sensors, electronics and C2 | 国防传感器、电子与指控 | defense_aerospace | research:config/theme_pathways.yml | config/theme_pathways.yml:545 "Defense sensors, electronics & C2" | Radar, C2 and mission electronics layer under platform modernization. |
| electronic_warfare_systems | Electronic warfare systems | 电子战系统 | defense_aerospace | research:config/theme_pathways.yml | config/theme_pathways.yml:550 "electronic warfare systems" | EW named as enabling sub-system alongside sensors on modern platforms. |
| autonomous_systems_counter_uas | Autonomy, drones and counter-UAS | 自主系统、无人机与反无人机 | defense_aerospace | research:research/defense_intelligence/D0R_DEFENSE_EQUITY_DRIVER_TAXONOMY.md | research/defense_intelligence/D0R_DEFENSE_EQUITY_DRIVER_TAXONOMY.md:187 "### 8. Autonomy, drones, counter-UAS" | Unmanned and autonomous capability segment distinct from legacy platform primes. |
| military_space_communications | Military space and satellite communications | 军用太空与卫星通信 | defense_aerospace; space_satellite | research:config/theme_thesis_registry.yml | config/theme_thesis_registry.yml:911 "military_satellite_and_space_communications_providers"; config/theme_thesis_registry.yml:1417 "resilient space-based communications (anti-jamming, disaggregated" | Resilient battlefield satcom shared across defense programs and commercial space build-out (M4). |

### theme:robotics_automation — Robotics & Automation

| slug | name_en | name_zh | parents | nominated_from | evidence | rationale |
|---|---|---|---|---|---|---|
| ai_vision_motion_control | AI vision and motion control | AI视觉与运动控制 | robotics_automation | research:config/theme_thesis_registry.yml | config/theme_thesis_registry.yml:501 "ai_vision_and_motion_control_platform_providers" | Perception and motion software stack separate from robot hardware arms. |
| collaborative_robot_arms | Collaborative robot arms | 协作机械臂 | robotics_automation | research:config/theme_thesis_registry.yml | config/theme_thesis_registry.yml:505 "collaborative_robot_arm_manufacturers" | Cobot form factor for high-mix manufacturing distinct from fixed automation. |
| surgical_robotics_systems | Surgical robotics systems | 手术机器人系统 | robotics_automation; medical_devices | research:config/theme_thesis_registry.yml | config/theme_thesis_registry.yml:509 "surgical_robotics_with_installed_base_lock_in"; config/theme_thesis_registry.yml:1070 "AI-guided procedural tools (robotic surgery, AI imaging) creating" | Hospital surgical robotics spans factory automation thesis and med-device platform cycle (M1). |
| industrial_robots_cobots | Industrial robots and cobots | 工业机器人与协作机器人 | robotics_automation | research:config/theme_pathways.yml | config/theme_pathways.yml:609 "Industrial robots & cobots" | Factory automation hardware segment named in the curated pathway graph. |
| precision_actuators_servo_motors | Precision actuators and servo motors | 精密执行器与伺服电机 | robotics_automation | research:config/theme_pathways.yml | config/theme_pathways.yml:601 "Precision actuators & servo motors" | Component bottleneck layer distinct from finished robot systems. |
| software_defined_motion_control | Software-defined motion control | 软件定义运动控制 | robotics_automation | research:config/theme_thesis_registry.yml | config/theme_thesis_registry.yml:488 "judgment (bin-picking, quality inspection). Software-defined motion control" | Recurring control software layer atop automation hardware sales. |

### theme:glp1_obesity — GLP-1 / Obesity

| slug | name_en | name_zh | parents | nominated_from | evidence | rationale |
|---|---|---|---|---|---|---|
| glp1_incretin_therapies | GLP-1 incretin therapies | GLP-1肠促胰岛素疗法 | glp1_obesity | basket:baskets:obesity_glp1 | data/baskets/membership.json:3880 "Incretin/GLP-1 metabolic drugs — incumbents, oral next-gen pure-plays, supply chain and the names the drugs hurt." | Core incretin drug class named in the house obesity basket theme line. |
| oral_glp1_formulations | Oral GLP-1 formulations | 口服GLP-1制剂 | glp1_obesity | research:config/theme_thesis_registry.yml | config/theme_thesis_registry.yml:975 "Oral formulations eliminate" | Oral delivery modality distinct from injectable incretin platforms (M3). |
| glp1_api_drug_delivery | GLP-1 API and drug delivery manufacturing | GLP-1原料药与给药制造 | glp1_obesity | research:config/theme_thesis_registry.yml | config/theme_thesis_registry.yml:992 "glp1_api_and_drug_delivery_manufacturers" | Upstream API and delivery capacity separate from branded drug demand. |
| cardiorenal_metabolic_indications | Cardiorenal and metabolic indications | 心肾与代谢适应症 | glp1_obesity | research:config/theme_thesis_registry.yml | config/theme_thesis_registry.yml:996 "metabolic_and_cardiorenal_drug_platforms" | Adjacent indication expansion beyond weight loss alone. |
| fill_finish_delivery_devices | Fill-finish and drug-delivery devices | 灌装封装与给药装置 | glp1_obesity | research:config/theme_pathways.yml | config/theme_pathways.yml:672 "Fill-finish & drug-delivery device manufacturing" | Manufacturing bottleneck segment for scaling GLP-1 supply. |

### theme:space_satellite — Space & Satellites

Dual-parent micro `military_space_communications` is defined under `theme:defense_aerospace` (M4); not duplicated here.

| slug | name_en | name_zh | parents | nominated_from | evidence | rationale |
|---|---|---|---|---|---|---|
| leo_constellation_deployment | LEO constellation deployment | 低轨星座部署 | space_satellite | research:config/theme_thesis_registry.yml | config/theme_thesis_registry.yml:1414 "enabling proliferated satellite constellations" | Proliferated LEO build-out economics distinct from ground segment hardware. |
| satellite_broadband_services | Satellite broadband services | 卫星宽带服务 | space_satellite | research:config/theme_thesis_registry.yml | config/theme_thesis_registry.yml:1415 "Satellite broadband at $100-150/month penetrates rural," | Consumer and enterprise connectivity revenue pool from LEO services. |
| satellite_ground_terminals | Satellite ground terminals and equipment | 卫星地面终端与设备 | space_satellite | research:config/theme_pathways.yml | config/theme_pathways.yml:828 "Ground equipment & terminal manufacturers"; config/theme_thesis_registry.yml:1436 "satellite_ground_segment_and_terminal_manufacturers" | Ground segment hardware demand tied to constellation subscriber growth. |
| direct_to_device_connectivity | Direct-to-device satellite connectivity | 卫星直连终端通信 | space_satellite | research:config/theme_thesis_registry.yml | config/theme_thesis_registry.yml:1418 "Direct-to-device" | Handset-integrated satcom standard expanding addressable market beyond dedicated terminals. |

### theme:fintech_payments — Fintech & Payments

No micro-themes admitted in V1: Finance R11 is not federated (spec §5, L9).

## CROSS-LANE

- AI vision chips for robots — candidate tied to `ai_semiconductors` / `ai_infra` pathway refs — config/theme_pathways.yml:617 (robotics downstream winner basket_refs).
- Managed-care cost tailwind from obesity reduction — `managed_care` basket — config/theme_pathways.yml:688 (glp1 downstream winner; owning lane: diagnostics_lifesci / healthcare C3).
- Reshoring industrial capex driver for automation — `reshoring` basket — config/theme_pathways.yml:593 (pathway driver; owning theme: grid_electrification / industrials C1).
- Shipbuilding and nuclear naval platforms — research/defense_intelligence/D0R_DEFENSE_EQUITY_DRIVER_TAXONOMY.md:103 (defense product segment; deferred to defense lane depth beyond C2 scope).
- AI-guided imaging and monitoring platforms — medical_devices thesis — config/theme_thesis_registry.yml:1070 (medical_devices C3; surgical robotics dual-parent row is C2-owned per M1).

## REJECTED

| candidate | theme | reason |
|---|---|---|
| legacy_signature_based_security_vendors | cybersecurity | Stance loser class (CD4/M5); not a neutral segment slug. |
| cloud_native_security_platform_consolidators (as slug) | cybersecurity | Class name embeds winner stance; neutral slug admitted separately. |
| legacy_on_premise_siem | cybersecurity | Pathway impaired_incumbent / AVOID-shaped node (CD4). |
| us_defense_primes_with_high_international_fms_backlog | defense_aerospace | Winner stance class; contractor archetype not product segment (M2). |
| single_market_defense_contractors | defense_aerospace | Loser stance class (CD4). |
| defense_prime_contractors | defense_aerospace | Pathway direct_beneficiary label names contractors, not capability segment. |
| dual_use_ai_autonomy_linkage | defense_aerospace | Pathway second_order_risk node; not a standalone product micro. |
| labour_intensive_manufacturing_without_automation | robotics_automation | Loser stance class (CD4). |
| labour_intensive_assembly_operations | robotics_automation | Pathway impaired_incumbent / AVOID-shaped (CD4). |
| surgical_robotics_with_installed_base_lock_in (as slug) | robotics_automation | Class name carries installed-base winner framing; neutral slug used instead. |
| bariatric_surgery_displacement | glp1_obesity | Loser / displaced-procedure class (M3). |
| snack_and_discretionary_food | glp1_obesity | Loser stance; consumer sector not therapy chain segment. |
| glp1_drug_developers_manufacturers (generic) | glp1_obesity | Duplicate of incretin therapies + API rows without added segment grain. |
| legacy_geo_satellite_operators | space_satellite | Pathway impaired_incumbent / AVOID-shaped (CD4). |
| proliferated_leo_constellation_operators_with_defense_contracts | space_satellite | Winner class name; neutral LEO deployment row used instead. |
| terrestrial_rural_broadband_substitutes | space_satellite | Loser stance class (CD4). |
| payment_rail_infrastructure_providers | fintech_payments | L9 — no fintech micros; would duplicate non-federated R11 slices. |
| stablecoin_real_time_payment_rails | fintech_payments | L9 — Finance R11 not federated in V1. |
| fraud_and_identity_verification_specialists | fintech_payments | L9; also overlaps cybersecurity identity segment without fintech federation. |
| interchange_dependent_monolines | fintech_payments | Loser stance under fintech thesis (CD4). |

## GAPS

- No house vertical registry slice keys were found for these themes on origin/main; all rows use `research:` or `basket:baskets:` nominators only.
- Defense shipbuilding/naval hull segment (taxonomy §4) has house evidence but was not minted here to keep defense micro count within evidence-distinct siblings; C3 or a defense depth lane may admit it later.
