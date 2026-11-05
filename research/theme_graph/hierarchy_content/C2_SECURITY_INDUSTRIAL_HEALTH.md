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
| endpoint_security | Endpoint security | 终端安全 | cybersecurity | basket:baskets:cybersecurity | data/baskets/membership.json:3532 "Endpoint, network, identity"; config/theme_thesis_registry.yml:421 "forcing enterprises to adopt behavioral/AI-native detection" | Device-level protection, where behavioral and AI-native detection is replacing signature tools. |
| network_security | Network security | 网络边界安全 | cybersecurity | basket:baskets:cybersecurity | data/baskets/membership.json:3532 "Endpoint, network, identity" | Perimeter and traffic-level protection distinct from device and identity controls. |
| identity_access_management | Identity and access management | 身份与访问管理 | cybersecurity | basket:baskets:cybersecurity | data/baskets/membership.json:3532 "identity and cloud security software"; config/theme_thesis_registry.yml:439 "identity_and_access_management_specialists" | Credential and identity attack surface distinct from endpoint malware detection. |
| cloud_security | Cloud security | 云安全 | cybersecurity | basket:baskets:cybersecurity | data/baskets/membership.json:3532 "identity and cloud security software"; config/theme_thesis_registry.yml:433 "cloud migration exposing new attack surfaces" | Protection for cloud workloads and the attack surface that cloud migration opens. |

### theme:defense_aerospace — Defense & Aerospace

| slug | name_en | name_zh | parents | nominated_from | evidence | rationale |
|---|---|---|---|---|---|---|
| missiles_munitions_effects | Missiles, munitions and effects | 导弹、弹药与毁伤效应 | defense_aerospace | research:research/defense_intelligence/D0R_DEFENSE_EQUITY_DRIVER_TAXONOMY.md | research/defense_intelligence/D0R_DEFENSE_EQUITY_DRIVER_TAXONOMY.md:61 "### 2. Missiles, munitions, and effects" | Expendable replenishment and production economics separate from platform primes. |
| missile_propulsion_supply | Missile and munition propulsion supply | 导弹与弹药推进系统供给 | defense_aerospace | research:config/theme_pathways.yml | config/theme_pathways.yml:529 "Missile & munition propulsion supply" | Propulsion bottlenecks constrain guided-munition output rates. |
| defense_sensors_electronics_c2 | Defense sensors, electronics and C2 | 国防传感器、电子与指控 | defense_aerospace | research:config/theme_pathways.yml | config/theme_pathways.yml:545 "Defense sensors, electronics & C2"; config/theme_pathways.yml:550 "electronic warfare systems"; research/defense_intelligence/D0R_DEFENSE_EQUITY_DRIVER_TAXONOMY.md:82 "### 3. Sensors, EW, C4ISR, mission electronics" | Radar, electronic warfare, C2 and mission electronics layer under platform modernization. |
| autonomous_systems_counter_uas | Autonomy, drones and counter-UAS | 自主系统、无人机与反无人机 | defense_aerospace | research:research/defense_intelligence/D0R_DEFENSE_EQUITY_DRIVER_TAXONOMY.md | research/defense_intelligence/D0R_DEFENSE_EQUITY_DRIVER_TAXONOMY.md:187 "### 8. Autonomy, drones, counter-UAS" | Unmanned and autonomous capability segment distinct from legacy platform primes. |
| naval_shipbuilding | Naval and nuclear shipbuilding | 海军与核动力舰船建造 | defense_aerospace | research:research/defense_intelligence/D0R_DEFENSE_EQUITY_DRIVER_TAXONOMY.md | research/defense_intelligence/D0R_DEFENSE_EQUITY_DRIVER_TAXONOMY.md:103 "### 4. Shipbuilding and nuclear naval" | Hull delivery and nuclear-yard throughput economics distinct from munitions and electronics. |
| aerospace_components_aftermarket | Aerospace components and aftermarket | 航空航天零部件与售后市场 | defense_aerospace | research:research/defense_intelligence/D0R_DEFENSE_EQUITY_DRIVER_TAXONOMY.md | research/defense_intelligence/D0R_DEFENSE_EQUITY_DRIVER_TAXONOMY.md:145 "### 6. Aerospace components, propulsion, materials, aftermarket" | Parts, materials and aftermarket-service layer across aircraft programs, distinct from munitions propulsion. |
| military_space_communications | Military space and satellite communications | 军用太空与卫星通信 | defense_aerospace; space_satellite | basket:baskets:space_economy | data/baskets/membership.json:4651 "defense-space"; config/theme_thesis_registry.yml:911 "military_satellite_and_space_communications_providers"; config/theme_thesis_registry.yml:1417 "resilient space-based communications (anti-jamming, disaggregated" | Resilient military satcom shared between defense programs and the commercial space build-out. |

### theme:robotics_automation — Robotics & Automation

| slug | name_en | name_zh | parents | nominated_from | evidence | rationale |
|---|---|---|---|---|---|---|
| machine_vision | Machine vision | 机器视觉 | robotics_automation | basket:baskets:robotics_automation | data/baskets/membership.json:3752 "machine vision"; config/theme_thesis_registry.yml:486 "AI-native vision systems" | Perception layer that lets robots handle unstructured tasks, separate from motion hardware. |
| industrial_motion_controls | Industrial controls and motion control | 工业控制与运动控制 | robotics_automation | basket:baskets:robotics_automation | data/baskets/membership.json:3752 "industrial controls"; config/theme_thesis_registry.yml:488 "Software-defined motion control" | Control and motion software layer that earns recurring revenue atop automation hardware. |
| collaborative_robot_arms | Collaborative robot arms | 协作机械臂 | robotics_automation | research:config/theme_thesis_registry.yml | config/theme_thesis_registry.yml:505 "collaborative_robot_arm_manufacturers" | Cobot form factor for high-mix manufacturing distinct from fixed automation. |
| industrial_robot_arms | Industrial robot arms | 工业机械臂 | robotics_automation | research:config/theme_pathways.yml | config/theme_pathways.yml:609 "Industrial robots"; config/theme_thesis_registry.yml:508 "cannot justify traditional hard automation" | Fixed high-volume hard-automation robots, distinct from collaborative arms for high-mix work. |
| precision_actuators_servo_motors | Precision actuators and servo motors | 精密执行器与伺服电机 | robotics_automation | research:config/theme_pathways.yml | config/theme_pathways.yml:601 "Precision actuators & servo motors" | Component bottleneck layer distinct from finished robot systems. |
| surgical_robotics_systems | Surgical robotics systems | 手术机器人系统 | robotics_automation; medical_devices | basket:baskets:robotics_automation | data/baskets/membership.json:3752 "surgical robotics"; config/theme_thesis_registry.yml:509 "surgical_robotics_with_installed_base_lock_in"; config/theme_thesis_registry.yml:1070 "AI-guided procedural tools (robotic surgery, AI imaging) creating" | Hospital surgical robotics spans the automation thesis and the medical-device platform cycle. |

### theme:glp1_obesity — GLP-1 / Obesity

| slug | name_en | name_zh | parents | nominated_from | evidence | rationale |
|---|---|---|---|---|---|---|
| glp1_incretin_therapies | GLP-1 incretin therapies | GLP-1肠促胰岛素疗法 | glp1_obesity | basket:baskets:obesity_glp1 | data/baskets/membership.json:3880 "Incretin/GLP-1 metabolic drugs — incumbents, oral next-gen pure-plays, supply chain and the names the drugs hurt." | Core incretin drug class named in the house obesity basket theme line. |
| oral_glp1_formulations | Oral GLP-1 formulations | 口服GLP-1制剂 | glp1_obesity | basket:baskets:obesity_glp1 | data/baskets/membership.json:3880 "oral next-gen"; config/theme_thesis_registry.yml:975 "Oral formulations eliminate" | Oral delivery modality distinct from injectable incretin platforms. |
| glp1_api_manufacturing | GLP-1 API manufacturing | GLP-1原料药生产 | glp1_obesity | research:config/theme_thesis_registry.yml | config/theme_thesis_registry.yml:994 "GLP-1 API manufacturing requires specialized fermentation capacity" | Drug-substance capacity with multi-year lead times, upstream of fill-finish and devices. |
| cardiorenal_metabolic_indications | Cardiorenal and metabolic indications | 心肾与代谢适应症 | glp1_obesity | research:config/theme_thesis_registry.yml | config/theme_thesis_registry.yml:996 "metabolic_and_cardiorenal_drug_platforms" | Adjacent indication expansion beyond weight loss alone. |
| fill_finish_delivery_devices | Fill-finish and drug-delivery devices | 灌装封装与给药装置 | glp1_obesity | research:config/theme_pathways.yml | config/theme_pathways.yml:672 "Fill-finish & drug-delivery device manufacturing" | Manufacturing bottleneck segment for scaling GLP-1 supply. |

### theme:space_satellite — Space & Satellites

Dual-parent micro `military_space_communications` is defined under `theme:defense_aerospace`; not duplicated here.

| slug | name_en | name_zh | parents | nominated_from | evidence | rationale |
|---|---|---|---|---|---|---|
| launch_services | Launch services | 发射服务 | space_satellite | basket:baskets:space_economy | data/baskets/membership.json:4651 "Launch, satcom, direct-to-device"; config/theme_thesis_registry.yml:1413 "Reusable launch vehicles" | Orbit-access layer whose reusable-vehicle cost curve sets constellation economics. |
| satellite_broadband_services | Satellite broadband services | 卫星宽带服务 | space_satellite | basket:baskets:space_economy | data/baskets/membership.json:4651 "Launch, satcom, direct-to-device"; config/theme_thesis_registry.yml:1415 "Satellite broadband at" | Subscriber connectivity revenue from satcom where fibre is uneconomic. |
| direct_to_device_connectivity | Direct-to-device satellite connectivity | 手机直连卫星通信 | space_satellite | basket:baskets:space_economy | data/baskets/membership.json:4651 "Launch, satcom, direct-to-device"; config/theme_thesis_registry.yml:1418 "Direct-to-device" | Handset-integrated satellite links that extend the market beyond dedicated terminals. |
| earth_observation | Earth observation | 对地观测 | space_satellite | basket:baskets:space_economy | data/baskets/membership.json:4651 "Earth observation" | Imaging and sensing data from orbit, distinct from communications services. |
| satellite_ground_terminals | Satellite ground terminals and equipment | 卫星地面终端与设备 | space_satellite | research:config/theme_pathways.yml | config/theme_pathways.yml:828 "Ground equipment & terminal manufacturers"; config/theme_thesis_registry.yml:1436 "satellite_ground_segment_and_terminal_manufacturers" | Ground segment hardware demand tied to constellation subscriber growth. |

### theme:fintech_payments — Fintech & Payments

No micro-themes admitted in V1: Finance R11 is not federated (spec §5, L9).

## CROSS-LANE

- AI vision chips for robots — candidate tied to `ai_semiconductors` / `ai_infra` pathway refs — config/theme_pathways.yml:617 (robotics downstream winner basket_refs).
- Managed-care cost tailwind from obesity reduction — `managed_care` basket — config/theme_pathways.yml:688 (glp1 downstream winner; owning lane: diagnostics_lifesci / healthcare C3).
- Reshoring industrial capex driver for automation — `reshoring` basket — config/theme_pathways.yml:593 (pathway driver; owning theme: grid_electrification / industrials C1).
- AI-guided imaging and monitoring platforms — medical_devices thesis — config/theme_thesis_registry.yml:1070 (medical_devices C3; surgical robotics dual-parent row is C2-owned).

## REJECTED

| candidate | theme | reason |
|---|---|---|
| legacy_signature_based_security_vendors | cybersecurity | Stance loser class (CD4/M5); not a neutral segment slug. |
| cloud_native_security_platform_consolidators (as slug) | cybersecurity | Class name embeds winner stance; neutral slug admitted separately. |
| endpoint_network_cloud_security | cybersecurity | Restates the whole theme scope, overlapping every sibling. |
| cloud_native_security_platforms | cybersecurity | Platform-consolidation framing; superseded by the basket-named neutral cloud_security. |
| behavioral_ai_native_detection | cybersecurity | Detection paradigm spanning endpoint and network rows; its cite now sits on endpoint_security. |
| legacy_on_premise_siem | cybersecurity | Pathway impaired_incumbent / AVOID-shaped node (CD4). |
| us_defense_primes_with_high_international_fms_backlog | defense_aerospace | Winner stance class; contractor archetype not product segment (CD4). |
| single_market_defense_contractors | defense_aerospace | Loser stance class (CD4). |
| defense_prime_contractors | defense_aerospace | Pathway direct_beneficiary label names contractors, not capability segment. |
| electronic_warfare_systems | defense_aerospace | Sub-system inside defense_sensors_electronics_c2 per pathways:550 and D0R section 3; its cite now sits on that row. |
| dual_use_ai_autonomy_linkage | defense_aerospace | Pathway second_order_risk node; not a standalone product micro. |
| ai_vision_motion_control | robotics_automation | Bundled two basket-named segments; split into machine_vision and industrial_motion_controls. |
| software_defined_motion_control | robotics_automation | Merged into industrial_motion_controls — same layer. |
| industrial_robots_cobots | robotics_automation | Overlapped collaborative_robot_arms; renamed industrial_robot_arms for the non-cobot form factor. |
| labour_intensive_manufacturing_without_automation | robotics_automation | Loser stance class (CD4). |
| labour_intensive_assembly_operations | robotics_automation | Pathway impaired_incumbent / AVOID-shaped (CD4). |
| surgical_robotics_with_installed_base_lock_in (as slug) | robotics_automation | Class name carries installed-base winner framing; neutral slug used instead. |
| glp1_api_drug_delivery | glp1_obesity | Its drug-delivery half overlapped fill_finish_delivery_devices; narrowed to API manufacturing. |
| bariatric_surgery_displacement | glp1_obesity | Loser / displaced-procedure class; not a therapy-chain segment. |
| snack_and_discretionary_food | glp1_obesity | Loser stance; consumer sector not therapy chain segment. |
| glp1_drug_developers_manufacturers (generic) | glp1_obesity | Duplicate of incretin therapies + API rows without added segment grain. |
| leo_constellation_deployment | space_satellite | Build-out driver spanning launch and satcom services, not a distinct segment. |
| legacy_geo_satellite_operators | space_satellite | Pathway impaired_incumbent / AVOID-shaped (CD4). |
| proliferated_leo_constellation_operators_with_defense_contracts | space_satellite | Winner class name; constellation build-out not a distinct micro. |
| terrestrial_rural_broadband_substitutes | space_satellite | Loser stance class (CD4). |
| payment_rail_infrastructure_providers | fintech_payments | L9 — no fintech micros; would duplicate non-federated R11 slices. |
| stablecoin_real_time_payment_rails | fintech_payments | L9 — Finance R11 not federated in V1. |
| fraud_and_identity_verification_specialists | fintech_payments | L9; also overlaps cybersecurity identity segment without fintech federation. |
| interchange_dependent_monolines | fintech_payments | Loser stance under fintech thesis (CD4). |

## GAPS

- No house vertical registry slice keys were found for these themes on origin/main; all rows use `research:` or `basket:baskets:` nominators only.
