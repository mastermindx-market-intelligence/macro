# C2 micro-theme expansion research — cybersecurity, defense_aerospace, robotics_automation, space_satellite, fintech_payments

Status: DRAFT taxonomy PROPOSALS for GMI COMPLETION seat ratification — display-only navigation vocabulary, no tickers, no issuers, no weights.
Lane: gmi-micro-c2-20261021-r4 · Base: ca7edbcf50df21bd321bffa3433e5f105d3335da · asserted_on: 2026-10-21
Companion rows: `research/theme_graph/micro_expansion_20261021/C2_PROPOSED_ROWS.yaml` (16 sub_themes, 70 micro_themes, 151 parents — merges clean under `validate_theme_hierarchy`).
Commission: GMI COMPLETION (Fable Meta-CEO, Chairman 2026-10-21) — "microthemes should immensely and aggressively go beyond the original masterplan".
Scope note — fintech: the V1 C2 record rejected fintech micros under L9 (Finance R11 was not federated then). This lane is the commissioned federation follow-through. The L9-scope rejections are superseded by the commission; the CD4 stance-class rejections (e.g. `interchange_dependent_monolines`) remain respected — every row below is a neutral value-chain segment, never a winner/loser archetype, and the old `fraud_and_identity_verification_specialists` overlap is avoided by scoping financial-crime work to regulatory AML/transaction monitoring, distinct from cybersecurity's `identity_access_management` / `identity_fraud_anti_abuse`.

## theme:cybersecurity

Existing micros `endpoint_security`, `network_security`, `identity_access_management`, `cloud_security` stay untouched. The 16 new rows below cover the rest of the issuer value chain: the operations/response workstream, the preventive control platforms across new surfaces, and the trust/governance substrate beneath both.

### theme:extended_detection_response
- **name_en:** Extended detection and response platforms
- **name_zh:** 扩展检测与响应（XDR/SIEM）
- **value_chain_position:** midstream
- **parent_sub_theme:** theme:secops_detection_response
- **defining_activities:** correlate telemetry across endpoint, identity, network and cloud domains; build detection content and analytics pipelines; orchestrate automated response playbooks; retain and hunt through security event history.
- **distinct_from:** `theme:endpoint_security` — endpoint_security protects the device itself; this row is the cross-domain analytics and response orchestration plane that consumes signals from it.
- **exclusions:** the protective agents themselves; outsourced operations (→ `theme:managed_security_services`).
- **china_relevance:** high — 等级保护2.0 and 关键信息基础设施安全保护条例 mandate monitoring and audit capability that maps to this segment.
- **confidence:** high
- **sources:** MITRE ATT&CK knowledge base — MITRE Corporation; NIST Cybersecurity Framework 2.0 (Detect/Respond functions) — NIST; SANS SOC Survey — SANS Institute.

### theme:managed_security_services
- **name_en:** Managed security services
- **name_zh:** 托管安全服务
- **value_chain_position:** downstream
- **parent_sub_theme:** theme:secops_detection_response
- **defining_activities:** operate customer SOCs and monitoring as a service; triage and escalate detections; co-manage customer security tooling; deliver retainer-based response readiness.
- **distinct_from:** `theme:extended_detection_response` — that row is the platform product; this row is the outsourced operating service delivered on top of platforms.
- **exclusions:** pure staffing/body-shop; platform vendors' own SaaS delivery.
- **china_relevance:** high — 网络安全服务市场 grows under compliance-driven outsourcing by banks, energy and government sectors.
- **confidence:** high
- **sources:** ENISA Threat Landscape — European Union Agency for Cybersecurity (ENISA); NIST Cybersecurity Framework 2.0 — NIST; ISC2 Cybersecurity Workforce Study — ISC2.

### theme:threat_intelligence_vulnerability_research
- **name_en:** Threat intelligence & vulnerability research
- **name_zh:** 威胁情报与漏洞研究
- **value_chain_position:** upstream
- **parent_sub_theme:** theme:secops_detection_response
- **defining_activities:** collect and analyse adversary infrastructure and tradecraft; discover and coordinate disclosure of vulnerabilities; publish indicators, MITRE-style mappings and exposure feeds; operate bug-bounty intake.
- **distinct_from:** `theme:extended_detection_response` — this is the raw-input research tier that feeds detections, not the detection product; distinct from `theme:endpoint_security` (a control, not research).
- **exclusions:** offense-grade exploit brokering; general OSINT analytics for marketing.
- **china_relevance:** high — CNVD/CNNVD coordinated-disclosure ecosystem and 攻防演练 culture sustain a domestic threat-research segment.
- **confidence:** high
- **sources:** CVE Program and ATT&CK — MITRE Corporation; FIRST CSIRT Services Framework — Forum of Incident Response and Security Teams (FIRST); Data Breach Investigations Report — Verizon.

### theme:digital_forensics_incident_response
- **name_en:** Digital forensics & incident response
- **name_zh:** 数字取证与应急响应
- **value_chain_position:** downstream
- **parent_sub_theme:** theme:secops_detection_response
- **defining_activities:** acquire and analyse forensic evidence after compromise; reconstruct intrusion timelines and root causes; support regulatory notification and recovery; negotiate/assist extortion incident handling.
- **distinct_from:** `theme:managed_security_services` — continuous monitoring versus episodic post-compromise engagements; distinct from `theme:cyber_range_training` (preparation, not response).
- **exclusions:** law-enforcement investigations for non-cyber crime; routine backup restore services.
- **china_relevance:** medium — 网络安全审查 and incident-reporting rules (《网络安全法》) create demand, though much DFIR work sits inside SOEs.
- **confidence:** high
- **sources:** NIST SP 800-86, Guide to Integrating Forensic Techniques into Incident Response — NIST; ISO/IEC 27037 (incident evidence identification/collection) — ISO/IEC; Computer Security Incident Handling Guide — SANS Institute.

### theme:cyber_range_training
- **name_en:** Cyber ranges & workforce training
- **name_zh:** 网络靶场与安全实训
- **value_chain_position:** enabler
- **parent_sub_theme:** theme:secops_detection_response
- **defining_activities:** build live-fire virtual ranges replicating enterprise/ICS networks; run adversary-emulation exercises and red-team curricula; certify workforce skills; benchmark defensive tooling.
- **distinct_from:** `theme:digital_forensics_incident_response` — capability building before incidents, not response during them; distinct from all control rows (no preventive/detective control of its own).
- **exclusions:** general IT certification market; academic degree programs.
- **china_relevance:** high — 国家级网络靶场 programs and 攻防演练 (HW-style exercises) make this a policy-supported domestic segment.
- **confidence:** high
- **sources:** NICE Framework (NIST SP 800-181) — NIST; ATT&CK Evaluations — MITRE Corporation; ENISA cybersecurity education and training recommendations — ENISA.

### theme:zero_trust_architecture
- **name_en:** Zero-trust architecture & microsegmentation
- **name_zh:** 零信任架构
- **value_chain_position:** midstream
- **parent_sub_theme:** theme:security_control_platforms
- **defining_activities:** enforce per-request authentication and authorization; implement ZTNA application access; microsegment east-west data-center traffic; deploy policy engines and continuous trust evaluation.
- **distinct_from:** `theme:network_security` — network_security hardens the perimeter; zero trust removes the perimeter assumption entirely; distinct from `theme:identity_access_management` (workforce identity products vs architecture enforcement).
- **exclusions:** consumer VPN; SD-WAN performance features without security enforcement.
- **china_relevance:** high — 零信任 is an explicitly promoted direction in 信通院 architectures and government cloud pilots.
- **confidence:** high
- **sources:** NIST SP 800-207, Zero Trust Architecture — NIST; Zero Trust Maturity Model — Cybersecurity and Infrastructure Security Agency (CISA); NIST Cybersecurity Framework 2.0 — NIST.

### theme:application_security_testing
- **name_en:** Application security testing
- **name_zh:** 应用安全测试
- **value_chain_position:** midstream
- **parent_sub_theme:** theme:security_control_platforms
- **defining_activities:** scan first-party source code (SAST); exercise running applications and APIs (DAST); analyse open-source component risk (SCA); gate CI/CD pipelines on findings.
- **distinct_from:** `theme:cloud_security` — cloud_security protects runtime workloads; this row tests code pre-production; distinct from `theme:supply_chain_security_sca` (component risk analysis vs artifact integrity attestation).
- **exclusions:** manual pen-test consultancies as a service line; WAF runtime rules.
- **china_relevance:** medium — 代码审计 and SDL tooling demand grows with 信创 application estates and 开源治理 policies.
- **confidence:** high
- **sources:** OWASP Application Security Verification Standard (ASVS) — OWASP Foundation; NIST SP 800-218, Secure Software Development Framework — NIST; ISO/IEC 27034 (application security) — ISO/IEC.

### theme:supply_chain_security_sca
- **name_en:** Software supply chain security
- **name_zh:** 软件供应链安全
- **value_chain_position:** midstream
- **parent_sub_theme:** theme:security_control_platforms
- **defining_activities:** generate and consume SBOMs; sign and attest build artifacts (SLSA-style provenance); monitor dependency and registry risk; enforce release-integrity policy across vendors.
- **distinct_from:** `theme:application_security_testing` — appsec analyses owned code quality; this row guarantees the provenance and integrity of what gets assembled and distributed, including third-party artifacts.
- **exclusions:** open-source project maintenance funding; hardware component sourcing security.
- **china_relevance:** high — 开源软件供应链 national initiatives and 信创 make dependency provenance a policy concern.
- **confidence:** high
- **sources:** The Minimum Elements for an SBOM — NTIA; SLSA (Supply-chain Levels for Software Artifacts) — OpenSSF; Executive Order 14028, Improving the Nation's Cybersecurity — The White House.

### theme:data_security_posture
- **name_en:** Data security & posture management
- **name_zh:** 数据安全态势管理
- **value_chain_position:** midstream
- **parent_sub_theme:** theme:security_control_platforms
- **defining_activities:** discover and classify sensitive data across stores; remediate data-exposure posture (DSPM); enforce loss-prevention policy; manage encryption keys and secrets.
- **distinct_from:** `theme:identity_access_management` — IAM governs who may act; this row governs the data objects themselves; distinct from `theme:cloud_security` (workload protection vs data protection).
- **exclusions:** privacy-consent management as a marketing function; backup infrastructure.
- **china_relevance:** high — 《数据安全法》 data-classification duties and 数据出境 rules create a direct compliance product market.
- **confidence:** high
- **sources:** NIST SP 800-53 rev.5 (SC and PT control families) — NIST; ISO/IEC 27701 privacy information management — ISO/IEC; 《中华人民共和国数据安全法》 — 全国人民代表大会常务委员会.

### theme:operational_technology_security
- **name_en:** OT / industrial-control security
- **name_zh:** 工业控制安全
- **value_chain_position:** midstream
- **parent_sub_theme:** theme:security_control_platforms
- **defining_activities:** monitor and protect PLC/SCADA/process networks; inventory OT assets and protocols; engineer safe segmentation between IT and plant; validate OT incident procedures.
- **distinct_from:** `theme:network_security` — enterprise traffic protection; OT security targets industrial protocols with availability/safety-first semantics and proprietary fieldbus worlds.
- **exclusions:** functional-safety engineering itself; physical security of substations.
- **china_relevance:** high — 关键信息基础设施安全保护条例 explicitly covers energy/manufacturing control systems; 工控安全 is a named domestic market.
- **confidence:** high
- **sources:** IEC 62443 (industrial automation and control systems security) — ISA/IEC; NIST SP 800-82, Guide to Operational Technology Security — NIST; MITRE ATT&CK for ICS — MITRE Corporation.

### theme:email_collaboration_security
- **name_en:** Email & collaboration security
- **name_zh:** 邮件与协作安全
- **value_chain_position:** midstream
- **parent_sub_theme:** theme:security_control_platforms
- **defining_activities:** filter phishing and business-email-compromise at the mail layer; authenticate senders (SPF/DKIM/DMARC-class); protect collaboration/file-sharing surfaces; simulate phishing to train users.
- **distinct_from:** `theme:network_security` — content-borne social-attack channel rather than traffic/path protection; distinct from `theme:identity_fraud_anti_abuse` (post-authentication abuse vs message-borne intrusion).
- **exclusions:** archive/compliance journaling; consumer webmail.
- **china_relevance:** medium — enterprise mail security is a mature domestic category (反垃圾邮件/APT 邮件防护), tied to government and SOE procurement.
- **confidence:** high
- **sources:** Phishing Activity Trends Report — Anti-Phishing Working Group (APWG); M3AAWG best common practices — Messaging, Malware and Mobile Anti-Abuse Working Group; Phish Scale — NIST.

### theme:identity_fraud_anti_abuse
- **name_en:** Consumer fraud & anti-abuse
- **name_zh:** 反欺诈与业务反滥用
- **value_chain_position:** midstream
- **parent_sub_theme:** theme:security_control_platforms
- **defining_activities:** detect account takeover and credential stuffing; score and block bot/automation abuse; device-fingerprint and risk-score sessions; protect promotion/promo-abuse surfaces.
- **distinct_from:** `theme:identity_access_management` — IAM is workforce/enterprise access governance; this row is consumer-facing fraud and abuse economics; distinct from `theme:transaction_monitoring_aml` (proposed; regulatory money-flow screening).
- **exclusions:** consumer credit scoring; payment-network fraud rules (→ fintech AML row).
- **china_relevance:** high — 反电信网络诈骗法 obliges platforms to deploy real-time fraud interception, a statutory demand driver.
- **confidence:** high
- **sources:** NIST SP 800-63 Digital Identity Guidelines — NIST; FIDO2/WebAuthn specifications — FIDO Alliance; OWASP Automated Threats to Web Applications — OWASP Foundation.

### theme:hardware_root_of_trust
- **name_en:** Hardware root of trust & secure elements
- **name_zh:** 硬件信任根
- **value_chain_position:** upstream
- **parent_sub_theme:** theme:security_foundation_governance
- **defining_activities:** design/embed TPMs, secure enclaves and secure elements; manufacture and operate HSMs; implement measured boot and firmware attestation; certify cryptographic modules.
- **distinct_from:** `theme:endpoint_security` — software agents on devices versus the silicon anchor beneath them; distinct from `theme:defense_electronics_microelectronics` (proposed; defense-grade chips are a military supply chain, not a commercial trust product).
- **exclusions:** general SoC design; biometric sensors as hardware.
- **china_relevance:** high — 商用密码 and 可信计算 (TCM/可信计算3.0) create a parallel domestic trust-hardware stack.
- **confidence:** high
- **sources:** FIPS 140-3, Security Requirements for Cryptographic Modules — NIST; TPM 2.0 Library specification — Trusted Computing Group; GlobalPlatform device security specifications — GlobalPlatform.

### theme:post_quantum_cryptography_migration
- **name_en:** Post-quantum cryptography migration
- **name_zh:** 抗量子密码迁移
- **value_chain_position:** upstream
- **parent_sub_theme:** theme:security_foundation_governance
- **defining_activities:** inventory cryptographic assets (CBOM-style); replace vulnerable public-key algorithms with NIST-standardized PQC; build crypto-agility into products; plan staged migration across long-lived systems.
- **distinct_from:** `theme:hardware_root_of_trust` — that row supplies fixed-function trust silicon; this row is the algorithm-replacement and migration program across all crypto use, software and hardware alike.
- **exclusions:** quantum-computing hardware itself; quantum key distribution networks as a transport business.
- **china_relevance:** high — 国家密码管理局 drives 国密 algorithm families and PQC research; migration of banking/government crypto is a decade-scale program.
- **confidence:** medium
- **sources:** FIPS 203/204/205 Post-Quantum Cryptography Standards — NIST; Quantum-Safe Cryptography working group specifications — ETSI; Migration guidance to post-quantum cryptography — BSI (German Federal Office for Information Security).

### theme:security_governance_compliance
- **name_en:** Security governance, risk & compliance
- **name_zh:** 安全治理与合规
- **value_chain_position:** enabler
- **parent_sub_theme:** theme:security_foundation_governance
- **defining_activities:** operate GRC platforms and control libraries; quantify cyber risk financially; automate audit evidence; run board-level cyber disclosure and third-party risk programs.
- **distinct_from:** every technical control row — this governs and evidences security rather than preventing or detecting anything; distinct from `theme:cyber_insurance_risk_transfer` (internal governance vs external risk transfer).
- **exclusions:** legal counsel services; general enterprise GRC without security scope.
- **china_relevance:** high — 网络安全等级保护测评 and 数据安全 assessment obligations institutionalize a compliance tooling/services market.
- **confidence:** high
- **sources:** NIST Cybersecurity Framework 2.0 (Govern function) — NIST; Cybersecurity risk management and disclosure rules (Reg S-K Item 106) — US Securities and Exchange Commission; Directive (EU) 2022/2555 (NIS2) — European Union.

### theme:cyber_insurance_risk_transfer
- **name_en:** Cyber insurance & risk transfer
- **name_zh:** 网络保险
- **value_chain_position:** downstream
- **parent_sub_theme:** theme:security_foundation_governance
- **defining_activities:** underwrite cyber policies; model accumulation and systemic loss; require security-control baselines from insureds; pay and manage breach-related claims.
- **distinct_from:** `theme:security_governance_compliance` — internal risk management versus financial risk transfer to markets; distinct from all control rows (no security control is sold).
- **exclusions:** health/PII insurance lines; warranty extensions.
- **china_relevance:** medium — 网络安全保险 is a policy-encouraged pilot segment (工信部/金融监管 pilot guidance), still nascent.
- **confidence:** medium
- **sources:** Cyber Insurance Data Security Report — National Association of Insurance Commissioners (NAIC); cyber risk and insurance research papers — The Geneva Association; EIOPA staff papers on cyber insurance — EIOPA.

**Sub-theme grouping.** Three new sub_themes organize the expansion: `theme:secops_detection_response` (intel inputs, XDR analytics, managed ops, DFIR, ranges — the operate-and-respond workstream), `theme:security_control_platforms` (zero trust, appsec, supply chain, data, OT, mail, anti-abuse — the enforce-a-control product plane across surfaces the four legacy micros do not cover), and `theme:security_foundation_governance` (hardware trust roots, PQC migration, GRC, cyber insurance — the substrate and management/finance tier). The four existing micros remain direct children of `theme:cybersecurity`, untouched.

**Theme-tier candidates (prose only).** Two candidates for the seat, not proposed as rows: (1) a `theme:privacy_enhancing_technologies`-class theme (differential privacy, clean rooms, PETs) could sit under `theme:technology_software` as digital-privacy regulation (GDPR-class law) matures into an industry; (2) security-physical-convergence (building access, video security analytics) might eventually deserve its own theme bridging `industrials_defense` and software.

## theme:defense_aerospace

Existing micros (`missiles_munitions_effects`, `missile_propulsion_supply`, `defense_sensors_electronics_c2`, `autonomous_systems_counter_uas`, `naval_shipbuilding`, `aerospace_components_aftermarket`, `military_space_communications`, sub_theme `missile_munition_chain`) stay untouched. The 14 new rows add the major platform families, the upstream industrial base, readiness enablers, and the civil-aerospace half of the theme.

### theme:fixed_wing_combat_aircraft
- **name_en:** Fixed-wing combat aircraft
- **name_zh:** 固定翼作战飞机
- **value_chain_position:** downstream
- **parent_sub_theme:** theme:combat_platforms_systems
- **defining_activities:** develop and produce fighters, bombers and trainers under multi-decade programs; sustain upgrade blocks and mid-life updates; manage sovereign assembly and offset industrial participation.
- **distinct_from:** `theme:aerospace_components_aftermarket` — parts/service layer versus the platform program itself; distinct from `theme:missiles_munitions_effects` (expendable output vs airframe programs).
- **exclusions:** airlift/tanker fleets as cargo platforms; unmanned combat aircraft (→ `theme:autonomous_systems_counter_uas`).
- **china_relevance:** high — 建军百年奋斗目标 (2027 centennial goals) drives sustained fighter procurement and engine indigenization.
- **confidence:** high
- **sources:** The Military Balance — International Institute for Strategic Studies (IISS); Defense acquisitions assessments of tactical aircraft — US Government Accountability Office (GAO); Defence Data portal — European Defence Agency (EDA).

### theme:rotorcraft_vertical_lift
- **name_en:** Rotorcraft & vertical-lift platforms
- **name_zh:** 直升机与旋翼机平台
- **value_chain_position:** downstream
- **parent_sub_theme:** theme:combat_platforms_systems
- **defining_activities:** design and build military/utility helicopters and tiltrotor fleets; sustain aging helicopter fleets and avionics upgrades; develop civil-certified vertical-lift airframes.
- **distinct_from:** `theme:fixed_wing_combat_aircraft` — separate platform family with a distinct certification basis and industrial base; distinct from `theme:aerospace_propulsion_engines` (the engine tier beneath it).
- **exclusions:** fixed-wing GA (→ `theme:business_general_aviation`); uncrewed rotorcraft (→ `theme:autonomous_systems_counter_uas`).
- **china_relevance:** high — domestic helicopter industrialization programs and low-altitude-economy policy expand both military and civil demand.
- **confidence:** high
- **sources:** The Military Balance — IISS; Vertipedia technical resource — Vertical Flight Society; FAA Aerospace Forecast — US Federal Aviation Administration.

### theme:land_systems_armored_vehicles
- **name_en:** Land systems & armored vehicles
- **name_zh:** 装甲车辆与陆战装备
- **value_chain_position:** downstream
- **parent_sub_theme:** theme:combat_platforms_systems
- **defining_activities:** produce tanks, fighting vehicles and self-propelled artillery; run service-life extension and digitization upgrades; supply armored-vehicle fleets to allied armies.
- **distinct_from:** `theme:missiles_munitions_effects` — platform manufacture vs ammunition replenishment; distinct from `theme:naval_shipbuilding` and air-platform rows (ground domain).
- **exclusions:** individual soldier equipment; soft-skin logistics trucks.
- **china_relevance:** high — mechanization/digitization targets and 军贸 (arms-export) programs sustain a large domestic base.
- **confidence:** high
- **sources:** The Military Balance — IISS; ground combat vehicle program assessments — US Government Accountability Office (GAO); National Defense Industrial Association division publications — NDIA.

### theme:air_defense_systems
- **name_en:** Air & missile defense systems
- **name_zh:** 防空反导系统
- **value_chain_position:** midstream
- **parent_sub_theme:** theme:combat_platforms_systems
- **defining_activities:** integrate sensor-to-shooter air-defense layers; produce ground-based radars, launchers and interceptors as one defended system; field counter-rocket/artillery/mortar (C-RAM) classes.
- **distinct_from:** `theme:missiles_munitions_effects` — the interceptor round is munition economics; this row is the integrated system-of-systems including its C2; distinct from `theme:defense_sensors_electronics_c2` (generic sensor/EW layer vs the integrated defensive shield).
- **exclusions:** man-portable air defense as a munition line; space-based missile tracking (→ space theme).
- **china_relevance:** high — layered national air-defense modernization and export missile systems are prominent domestic segments.
- **confidence:** high
- **sources:** Missile Threat project — Center for Strategic and International Studies (CSIS); Integrated Air and Missile Defence policy documents — NATO; The Military Balance — IISS.

### theme:undersea_systems_sonar
- **name_en:** Undersea warfare & sonar systems
- **name_zh:** 水下战系统
- **value_chain_position:** midstream
- **parent_sub_theme:** theme:combat_platforms_systems
- **defining_activities:** build hull/mine/dropped sonar arrays and acoustic processing; produce torpedoes and undersea vehicles; deploy fixed seabed surveillance chains.
- **distinct_from:** `theme:naval_shipbuilding` — hull construction and nuclear-yard throughput vs the acoustic/weapon system payload tier; distinct from `theme:defense_sensors_electronics_c2` (air/land sensor electronics vs the undersea acoustic domain).
- **exclusions:** seabed telecom cables (civil); oceanographic survey equipment.
- **china_relevance:** high — anti-submarine-warfare buildup and blue-water navy ambitions drive sonar/undersea procurement.
- **confidence:** medium
- **sources:** The Military Balance — IISS; submarine industrial base assessments — US Government Accountability Office (GAO); NATO Cooperative Maritime Research and Experimentation (CMRE) programme documentation — NATO STO.

### theme:aerospace_propulsion_engines
- **name_en:** Aircraft engines & propulsion
- **name_zh:** 航空发动机
- **value_chain_position:** midstream
- **parent_sub_theme:** theme:defense_industrial_base
- **defining_activities:** design, certify and manufacture military and commercial gas-turbine engines; sell decades of spare parts and overhaul; develop next-gen propulsion (adaptive-cycle, sustainable-fuel).
- **distinct_from:** `theme:missile_propulsion_supply` — expendable solid-rocket motor output vs long-life turbine engines with aftermarket; distinct from `theme:aerospace_components_aftermarket` (engines are the propulsion tier, not generic parts).
- **exclusions:** rocket propulsion (→ `theme:launch_vehicle_propulsion`); APUs as cabin systems.
- **china_relevance:** high — 两机专项 (aero-engine & gas-turbine national program) makes engine indigenization a flagship national effort.
- **confidence:** high
- **sources:** The Military Balance — IISS; military engine sustainment reports — US Government Accountability Office (GAO); AIAA technical committee publications — American Institute of Aeronautics and Astronautics (AIAA).

### theme:explosive_energetics_materials
- **name_en:** Energetics & propellant materials
- **name_zh:** 含能材料
- **value_chain_position:** upstream
- **parent_sub_theme:** theme:defense_industrial_base
- **defining_activities:** synthesize propellants, explosives and pyrotechnics; operate energetics pilot and production plants; qualify new energetic formulations for motors and warheads.
- **distinct_from:** `theme:missile_propulsion_supply` — motor assembly versus the chemical input tier beneath all motors and munition fills; distinct from `theme:nitrogen_fertilizer_production` (civil ammonia chemistry).
- **exclusions:** commercial blasting explosives for mining; pyrotechnics for entertainment.
- **china_relevance:** high — domestic energetics capacity scales with munition stockpile programs; a recognized bottleneck chemistry.
- **confidence:** medium
- **sources:** UN International Ammunition Technical Guidelines (IATG) — United Nations; conventional munitions industrial base assessments — US Government Accountability Office (GAO); energetics industrial-base working group reports — National Defense Industrial Association (NDIA).

### theme:defense_electronics_microelectronics
- **name_en:** Defense microelectronics & trusted chips
- **name_zh:** 国防微电子
- **value_chain_position:** upstream
- **parent_sub_theme:** theme:defense_industrial_base
- **defining_activities:** supply trusted/radiation-hardened foundry services; package defense-grade chiplets and power electronics; qualify microelectronics for weapons platforms.
- **distinct_from:** `theme:defense_sensors_electronics_c2` — sensor system integration versus the trusted component supply beneath it; distinct from `theme:semicap_equipment` theme rows (commercial fab tools, not the defense supply chain).
- **exclusions:** commercial smartphone/consumer chip supply; generic EDA software.
- **china_relevance:** high — domestic defense chips indigenization under export-control pressure; 国家集成电路 policy context.
- **confidence:** medium
- **sources:** Microelectronics Commons and Trusted Foundry program documentation — US Department of Defense; defense industrial base assessments — US Government Accountability Office (GAO); semiconductor and defense technology studies — Center for Strategic and International Studies (CSIS).

### theme:aerospace_structures_composites
- **name_en:** Airframe structures & composites
- **name_zh:** 航空结构与复合材料
- **value_chain_position:** upstream
- **parent_sub_theme:** theme:defense_industrial_base
- **defining_activities:** fabricate fuselage, wing and empennage subassemblies; produce advanced composite aerostructures and honeycomb; supply structures for both defense and civil platforms.
- **distinct_from:** `theme:aerospace_components_aftermarket` — new-build structures vs parts distribution/used material; distinct from `theme:aerospace_propulsion_engines` (structural airframe vs propulsion).
- **exclusions:** aircraft interior cabin products; raw carbon fiber without aero qualification.
- **china_relevance:** high — domestic aerostructure ramp for homegrown airliner and fighter programs builds composite capacity.
- **confidence:** high
- **sources:** Composite Materials Handbook (CMH-17) — SAE International with US FAA; National Center for Advanced Materials Performance (NCAMP) program — FAA; Aerospace Standards program — Aerospace Industries Association (AIA).

### theme:military_training_simulation
- **name_en:** Military training & simulation
- **name_zh:** 军事训练与仿真
- **value_chain_position:** downstream
- **parent_sub_theme:** theme:mission_support_enablers
- **defining_activities:** build full-mission and part-task simulators; operate live-virtual-constructive training ranges; deliver mission-rehearsal and distributed synthetic training services.
- **distinct_from:** `theme:defense_test_evaluation_infrastructure` — training users vs qualifying systems; distinct from platform rows (a service over platforms, not a platform).
- **exclusions:** commercial flight-school simulators for airlines; entertainment simulators.
- **china_relevance:** high — 实战化训练 requirements and synthetic-range investments are explicit procurement lines.
- **confidence:** high
- **sources:** National Training and Simulation Association (NTSA) industry resources and I/ITSEC proceedings — NTSA; NATO Modelling and Simulation Group publications — NATO Science and Technology Organization; training-range program reviews — US Government Accountability Office (GAO).

### theme:military_logistics_sustainment
- **name_en:** Military logistics & sustainment
- **name_zh:** 军事后勤与装备保障
- **value_chain_position:** downstream
- **parent_sub_theme:** theme:mission_support_enablers
- **defining_activities:** run depot-level maintenance and overhaul; operate supply-chain, inventory and readiness engineering for fielded fleets; deliver contested-logistics planning tools.
- **distinct_from:** `theme:aerospace_components_aftermarket` — fleet-availability service economics vs parts catalog distribution; distinct from `theme:naval_shipbuilding` (building hulls vs sustaining them).
- **exclusions:** commercial 3PL freight; military construction (facilities).
- **china_relevance:** high — 联合保障 and equipment-availability modernization sustain a large domestic segment.
- **confidence:** medium
- **sources:** weapon system sustainment assessments — US Government Accountability Office (GAO); Defense Logistics Agency strategy documentation — US Department of Defense; NATO logistics handbooks — NATO.

### theme:defense_test_evaluation_infrastructure
- **name_en:** Test, evaluation & range infrastructure
- **name_zh:** 试验鉴定与靶场设施
- **value_chain_position:** enabler
- **parent_sub_theme:** theme:mission_support_enablers
- **defining_activities:** operate proving grounds and open-air ranges; instrument flight test and telemetry collection; deliver independent T&E qualification services before fielding.
- **distinct_from:** `theme:military_training_simulation` — qualifying new systems vs rehearsing with fielded ones; distinct from platform rows.
- **exclusions:** commercial certification testing (FAA/EASA); academic wind tunnels.
- **china_relevance:** medium — 试验鉴定 reform is a stated PLA modernization priority, though largely state-internal.
- **confidence:** medium
- **sources:** Test Resource Management Center program documentation — US Department of Defense; ITEA publications — International Test and Evaluation Association; NATO STO applied-vehicle technology reports — NATO Science and Technology Organization.

### theme:air_traffic_management_systems
- **name_en:** Air traffic management systems
- **name_zh:** 空中交通管理系统
- **value_chain_position:** midstream
- **parent_sub_theme:** theme:civil_aerospace_economy
- **defining_activities:** build ATC automation, surveillance and navaid systems; develop UAV traffic management (UTM) for low-altitude airspace; modernize flight-data and flow-management infrastructure.
- **distinct_from:** `theme:defense_sensors_electronics_c2` — civil airspace infrastructure vs military C2; distinct from `theme:fixed_wing_combat_aircraft` (airspace systems vs aircraft).
- **exclusions:** airline operations software; onboard avionics boxes.
- **china_relevance:** high — 低空经济 policy and CAAC airspace reform create a fast-growing domestic UTM/ATM market.
- **confidence:** high
- **sources:** Global Air Navigation Plan — International Civil Aviation Organization (ICAO); NextGen modernization documentation — US Federal Aviation Administration; European ATM Master Plan — SESAR Joint Undertaking.

### theme:business_general_aviation
- **name_en:** Business & general aviation aircraft
- **name_zh:** 公务机与通用航空
- **value_chain_position:** downstream
- **parent_sub_theme:** theme:civil_aerospace_economy
- **defining_activities:** design and produce business jets, turboprops and piston aircraft; support fleets with parts, maintenance and completions; serve fractional ownership and charter operators.
- **distinct_from:** `theme:rotorcraft_vertical_lift` — fixed-wing civil airframes vs vertical lift; distinct from defense platform rows (civil demand cycle).
- **exclusions:** commercial airliners (mainline OEM programs); rotorcraft.
- **china_relevance:** medium — GA expansion under 低空经济 and new FBO infrastructure, though business-jet demand is cyclical.
- **confidence:** high
- **sources:** General Aviation Statistical Databook & Industry Outlook — General Aviation Manufacturers Association (GAMA); Business aviation references — National Business Aviation Association (NBAA); FAA Aerospace Forecast — US Federal Aviation Administration.

**Sub-theme grouping.** Four new sub_themes organize the expansion: `theme:combat_platforms_systems` (the five major platform families: fixed-wing, rotorcraft, land, air-defense, undersea), `theme:defense_industrial_base` (engines, energetics, trusted microelectronics, structures — the upstream input tier), `theme:mission_support_enablers` (training, sustainment, test ranges — readiness services), and `theme:civil_aerospace_economy` (ATM and business/GA — the non-defense half of the theme). The existing `missile_munition_chain` sub_theme and its two micros remain unchanged.

**Theme-tier candidates (prose only).** Three candidates for the seat: (1) a `theme:maritime_industrial` theme could gather shipbuilding, undersea and port/logistics infrastructure that currently spans `industrials_defense` rows; (2) civil commercial aerospace (airframers, interiors, MRO) may deserve its own theme distinct from defense as commercial aero cycles diverge; (3) homeland security & border resilience (detection, screening, critical-infrastructure protection) is a candidate bridge theme toward the security cluster.

## theme:robotics_automation

Existing micros (`machine_vision`, `industrial_motion_controls`, `collaborative_robot_arms`, `industrial_robot_arms`, `precision_actuators_servo_motors`, `surgical_robotics_systems`, sub_theme `robot_arm_systems`) stay untouched. The 13 new rows add mobile/service form factors, the software-and-intelligence layer, the integration/delivery economy, and vertical deployments the arm-centric rows never covered.

### theme:autonomous_mobile_robots
- **name_en:** Autonomous mobile robots (AMR/AGV)
- **name_zh:** 自主移动机器人
- **value_chain_position:** midstream
- **parent_sub_theme:** theme:autonomous_service_robots
- **defining_activities:** build self-navigating mobile platforms for material transport and inspection; deploy fleet-charging and mission software; certify mobile platforms for human-shared floors.
- **distinct_from:** `theme:industrial_robot_arms` / `theme:collaborative_robot_arms` — mobility without arms vs arm form factors under `theme:robot_arm_systems`; distinct from `theme:warehouse_automation_systems` (unit machines vs integrated facilities).
- **exclusions:** self-driving passenger vehicles; telepresence robots.
- **china_relevance:** high — domestic AMR makers lead global volume in 3PL/e-commerce intralogistics deployments.
- **confidence:** high
- **sources:** World Robotics report (service robots chapters) — International Federation of Robotics (IFR); ANSI/RIA R15.08 mobile robot safety standard — A3/ANSI; MHI Annual Industry Report — MHI.

### theme:humanoid_robots
- **name_en:** Humanoid robots
- **name_zh:** 人形机器人
- **value_chain_position:** midstream
- **parent_sub_theme:** theme:autonomous_service_robots
- **defining_activities:** develop bipedal general-purpose platforms for human environments; integrate dexterous hands and whole-body control; target manufacturing/logistics pilots before consumer markets.
- **distinct_from:** `theme:autonomous_mobile_robots` (wheeled/towed mobile platforms) and arm rows — a new form factor with its own actuator, tendon and balance stack; distinct from `theme:embodied_ai_robot_learning` (the brains vs the body).
- **exclusions:** prosthetics/exoskeleton wearables (→ `theme:rehabilitation_medical_robots`); entertainment animatronics.
- **china_relevance:** high — 工信部《人形机器人创新发展指导意见》 sets a national roadmap; local supply chains form around it.
- **confidence:** high
- **sources:** 《人形机器人创新发展指导意见》 — 工业和信息化部 (MIIT); World Robotics — IFR; IEEE Robotics and Automation Society technical committees — IEEE RAS.

### theme:agricultural_field_robotics
- **name_en:** Agricultural & field robotics
- **name_zh:** 农业机器人
- **value_chain_position:** midstream
- **parent_sub_theme:** theme:autonomous_service_robots
- **defining_activities:** build weeding, seeding and harvesting robots; field milking and barn-cleaning machines; develop soil/crop scouting autonomy for rough terrain.
- **distinct_from:** `theme:precision_agriculture_platforms` (existing, data platforms under ag_fertilizer) — field machinery that acts on crops vs agronomic software; distinct from arm rows (outdoor unstructured mobility).
- **exclusions:** conventional self-propelled harvesters without autonomy; ag chemical inputs.
- **china_relevance:** high — 农机装备 is a made-in-China-2025 priority class; 老龄化 farm labor pushes automation demand.
- **confidence:** high
- **sources:** World Robotics (agricultural robot chapters) — IFR; ISO 11783 (ISOBUS) series — ISO; Future Farming trade-press value-chain coverage — Future Farming.

### theme:rehabilitation_medical_robots
- **name_en:** Rehabilitation & hospital service robots
- **name_zh:** 康复与医疗服务机器人
- **value_chain_position:** midstream
- **parent_sub_theme:** theme:autonomous_service_robots
- **defining_activities:** build exoskeletons and gait-rehab trainers; deliver hospital logistics and disinfection robots; develop assistive care robotics for aging care.
- **distinct_from:** `theme:surgical_robotics_systems` — operating-room interventional platforms vs therapy/care/service robotics; distinct from `theme:humanoid_robots` (wearable/wheeled care machines vs general-purpose bipeds).
- **exclusions:** prosthetic limbs; telehealth software.
- **china_relevance:** high — 康复辅助器具产业 policy and aging-population care demand expand a named domestic category.
- **confidence:** high
- **sources:** World Robotics (medical robot chapters) — IFR; ISO 13482 (personal care robot safety) — ISO; 《关于加快发展康复辅助器具产业的意见》 — 国务院 (State Council).

### theme:laboratory_automation_robots
- **name_en:** Laboratory automation robotics
- **name_zh:** 实验室自动化
- **value_chain_position:** midstream
- **parent_sub_theme:** theme:autonomous_service_robots
- **defining_activities:** build liquid-handling and plate-handling workstations; automate sample prep and assay workflows; integrate lab robots with LIMS/execution software.
- **distinct_from:** `theme:life_science_lab_instruments` (existing, under diagnostics_lifesci) — robotic workflow systems vs single-function analytical instruments; distinct from arm rows (bench-scale motion with consumable economics).
- **exclusions:** sequencers and analytical instruments themselves; software-only scheduling.
- **china_relevance:** medium — biotech/pharma lab automation demand grows with domestic biologics capacity; most core tooling still imported.
- **confidence:** medium
- **sources:** SLAS laboratory automation standards and conference program — Society for Laboratory Automation and Screening (SLAS); ANSI/SLAS microplate and footprint standards — ANSI/SLAS; World Robotics — IFR.

### theme:robot_software_middleware
- **name_en:** Robot operating systems & middleware
- **name_zh:** 机器人操作系统与中间件
- **value_chain_position:** enabler
- **parent_sub_theme:** theme:robot_software_intelligence
- **defining_activities:** maintain open robot middleware frameworks (ROS-class); build fleet orchestration and task-allocation software; abstract heterogeneous robot hardware behind common APIs.
- **distinct_from:** `theme:industrial_motion_controls` — machine-level servo control vs robot-level/fleet-level software abstraction; distinct from `theme:embodied_ai_robot_learning` (infrastructure vs learned policies).
- **exclusions:** factory MES/ERP; simulation engines (→ `theme:robot_simulation_digital_twin`).
- **china_relevance:** high — domestic middleware stacks (open-source ecosystems) are a stated gap-and-goal in robot industry plans.
- **confidence:** high
- **sources:** ROS documentation — Open Robotics; ROS-Industrial consortium program — ROS-Industrial (Americas/Europe/Asia-Pacific); Data Distribution Service (DDS) specification — Object Management Group (OMG).

### theme:embodied_ai_robot_learning
- **name_en:** Embodied AI & robot learning
- **name_zh:** 具身智能
- **value_chain_position:** enabler
- **parent_sub_theme:** theme:robot_software_intelligence
- **defining_activities:** train manipulation/navigation policies from demonstration data; adapt vision-language-action foundation models to robot tasks; deploy learned skills on production robots.
- **distinct_from:** `theme:machine_vision` — perception sensing vs task-learning policies that act on perception; distinct from `theme:robot_software_middleware` (framework plumbing vs learned behavior).
- **exclusions:** generic LLM chat products; warehouse optimization analytics without robot control.
- **china_relevance:** high — 具身智能 is a named frontier in national AI/robot planning documents and university-industrial programs.
- **confidence:** high
- **sources:** Open X-Embodiment / RT-X robotics datasets and papers — cross-institution academic collaboration (arXiv, 2023); ICRA/IROS proceedings — IEEE Robotics and Automation Society; 《机器人产业发展报告》 — 中国电子学会 (Chinese Institute of Electronics).

### theme:robot_simulation_digital_twin
- **name_en:** Robot simulation & digital twins
- **name_zh:** 机器人仿真与数字孪生
- **value_chain_position:** enabler
- **parent_sub_theme:** theme:robot_software_intelligence
- **defining_activities:** build physics-accurate robot and cell simulation; train/verify policies in synthetic worlds (sim-to-real); commission production lines against digital-twin replicas.
- **distinct_from:** `theme:embodied_ai_robot_learning` — the verification/tooling environment vs the learned policies themselves; distinct from `theme:industrial_iot_condition_monitoring` (pre-deployment synthetic state vs live plant telemetry).
- **exclusions:** CAD authoring tools; MES systems.
- **china_relevance:** medium — digital-twin toolchains are encouraged by MIIT programs, though core simulation engines remain foreign-led.
- **confidence:** high
- **sources:** ISO 23247 (digital twin framework for manufacturing) — ISO; Manufacturing digital-twin and CPS foundational publications — NIST; Gazebo simulation ecosystem — Open Robotics.

### theme:robot_end_effectors_tooling
- **name_en:** Robot end effectors & tooling
- **name_zh:** 机器人末端执行器
- **value_chain_position:** upstream
- **parent_sub_theme:** theme:robot_arm_systems
- **defining_activities:** build electric/pneumatic grippers and dexterous hands; produce force-torque and tactile sensing; supply quick-change tooling and compliant fixtures.
- **distinct_from:** `theme:precision_actuators_servo_motors` — joint motion components vs the task-facing tooling mounted at the wrist; distinct from `theme:machine_vision` (2D/3D sensing vs contact tooling).
- **exclusions:** welding torches as consumables; conveyor tooling.
- **china_relevance:** high — dexterous end-effector supply is a recognized bottleneck for humanoid and 3C-assembly automation.
- **confidence:** medium
- **sources:** World Robotics — IFR; ISO 9409 (mechanical interface) series — ISO; ICRA proceedings on manipulation and grasping — IEEE Robotics and Automation Society.

### theme:warehouse_automation_systems
- **name_en:** Warehouse & fulfillment automation systems
- **name_zh:** 仓储物流自动化
- **value_chain_position:** downstream
- **parent_sub_theme:** theme:automation_integration_systems
- **defining_activities:** design and install goods-to-person and AS/RS systems; deliver sortation and conveyor integration; run long-term service/modernization contracts on installed systems.
- **distinct_from:** `theme:autonomous_mobile_robots` — integrated facility-scale systems vs unit mobile robots; distinct from `theme:robotics_system_integration` (warehouse vertical vs general automation integration).
- **exclusions:** parcel carrier networks; WMS software without hardware integration.
- **china_relevance:** high — domestic integrators deploy at global-leading volume for e-commerce and express networks.
- **confidence:** high
- **sources:** MHI Annual Industry Report — MHI; World Robotics — IFR; warehouse automation market research — Interact Analysis (trade-press analyst).

### theme:semiconductor_factory_automation
- **name_en:** Semiconductor factory automation
- **name_zh:** 半导体工厂自动化
- **value_chain_position:** downstream
- **parent_sub_theme:** theme:automation_integration_systems
- **defining_activities:** build automated material handling systems (AMHS) for fabs; supply cleanroom wafer-handling robots and load ports; integrate fab scheduling/dispatch software with tools.
- **distinct_from:** `theme:wafer_fab_subsystems` (existing, under semicap_equipment) — fab logistics automation vs the process-tool subsystem layer; distinct from `theme:warehouse_automation_systems` (cleanroom vertical vs general warehousing).
- **exclusions:** litho/etch process tools themselves; front-opening unified pod (FOUP) plastics.
- **china_relevance:** high — domestic fab buildout across the industry ramp pulls AMHS localization; segment demand is capacity-driven, not vendor-specific.
- **confidence:** high
- **sources:** SEMI E84/E87 and related automation interface standards — SEMI; World Robotics (electronics industry chapters) — IFR; 《中国机器人产业发展报告》 — 中国电子学会.

### theme:robotics_system_integration
- **name_en:** Robotics & automation system integration
- **name_zh:** 机器人系统集成
- **value_chain_position:** downstream
- **parent_sub_theme:** theme:automation_integration_systems
- **defining_activities:** engineer turnkey robot cells for end users; program and commission integrated automation lines; provide retrofit and maintenance services on installed automation.
- **distinct_from:** `theme:warehouse_automation_systems` and `theme:semiconductor_factory_automation` — the general integrator economy across industries vs those vertical specialists; distinct from robot/component makers upstream.
- **exclusions:** pure engineering consultancies; robot rental platforms.
- **china_relevance:** high — integrators are the largest fragment of the domestic automation value chain and the stated localization frontier.
- **confidence:** high
- **sources:** World Robotics (integrator statistics) — IFR; Automate market reports — Association for Advancing Automation (A3); Robotik + Automation sector statistics — VDMA (German Mechanical Engineering Industry Association).

### theme:industrial_iot_condition_monitoring
- **name_en:** Industrial IoT & condition monitoring
- **name_zh:** 工业互联网与状态监测
- **value_chain_position:** enabler
- **parent_sub_theme:** theme:automation_integration_systems
- **defining_activities:** deploy plant-wide vibration/temperature sensing networks; stream machine health telemetry to cloud analytics; run predictive-maintenance and OEE platforms.
- **distinct_from:** `theme:industrial_motion_controls` — plant data plane vs machine control loops; distinct from `theme:robot_simulation_digital_twin` (live production telemetry vs pre-deployment synthetic models).
- **exclusions:** building-management systems; consumer wearables.
- **china_relevance:** high — 工业互联网 is a national strategy with MIIT action plans and identified 5G+industrial-internet parks.
- **confidence:** high
- **sources:** OPC UA specification — OPC Foundation; RAMI 4.0 reference architecture — Plattform Industrie 4.0 (German Federal Ministry for Economic Affairs and Climate Action); 《工业互联网创新发展行动计划》 — 工业和信息化部 (MIIT).

**Sub-theme grouping.** Three new sub_themes organize the expansion: `theme:autonomous_service_robots` (AMR, humanoid, agricultural, rehab/care, lab — the mobile and service form factors), `theme:robot_software_intelligence` (middleware, embodied AI, simulation — the intelligence/tooling layer), and `theme:automation_integration_systems` (warehouse systems, fab automation, general integration, IIoT — the facility-scale delivery economy). `theme:robot_end_effectors_tooling` extends the existing `theme:robot_arm_systems` sub_theme, whose two arm micros remain unchanged.

**Theme-tier candidates (prose only).** Two candidates for the seat: (1) `theme:humanoid_embodied_ai` may deserve theme-tier status as the humanoid/embodied stack (body + brain + data flywheel) separates from classical industrial automation; (2) a logistics-automation theme (warehouse + postal/parcel + airport baggage handling) could anchor under `industrials_defense` as e-commerce capex persists.

## theme:space_satellite

Existing micros (`military_space_communications`, `launch_services`, `satellite_broadband_services`, `direct_to_device_connectivity`, `earth_observation`, `satellite_ground_terminals`, sub_theme `satellite_connectivity_services`) stay untouched. The 13 new rows add the space-segment industry, launch/ground capital infrastructure, data-and-assurance services, and two programmatic rows (space security, deep space) that sit directly under the theme.

### theme:spacecraft_manufacturing_satellites
- **name_en:** Spacecraft & satellite manufacturing
- **name_zh:** 卫星整星制造
- **value_chain_position:** midstream
- **parent_sub_theme:** theme:space_segment_industry
- **defining_activities:** integrate satellite buses and payloads; qualify spacecraft through environmental test; deliver complete satellites to constellation, government and science customers.
- **distinct_from:** `theme:launch_services` — orbit access vs the orbit-bound hardware; distinct from `theme:satellite_ground_terminals` (space segment vs user equipment).
- **exclusions:** launch vehicles; one-off components (→ `theme:space_components_subsystems`).
- **china_relevance:** high — national constellation buildout plans and 商业航天 policy expand integrated satellite manufacturing capacity.
- **confidence:** high
- **sources:** State of the Satellite Industry Report — Satellite Industry Association (SIA); satellites-built-and-launched outlook research — Euroconsult/Novaspace; 《中国的航天》白皮书 — 国务院新闻办公室 (SCIO).

### theme:space_components_subsystems
- **name_en:** Space components & subsystems
- **name_zh:** 航天器部组件与单机
- **value_chain_position:** upstream
- **parent_sub_theme:** theme:space_segment_industry
- **defining_activities:** produce reaction wheels, star trackers and propulsion units; manufacture solar arrays and power electronics; supply space-qualified (rad-tolerant) electronics and harnesses.
- **distinct_from:** `theme:spacecraft_manufacturing_satellites` — unit suppliers vs final spacecraft integration; distinct from `theme:defense_electronics_microelectronics` (proposed; defense-grade terrestrial chips vs flight-qualified space units).
- **exclusions:** launch-vehicle engines; ground antenna RF front-ends.
- **china_relevance:** high — 单机部组件自主化 is a named localization goal in domestic aerospace supply-chain policy.
- **confidence:** high
- **sources:** EEE-INST-002 instructions for EEE parts — NASA; ECSS engineering standards — European Cooperation for Space Standardization (ESA-led); State-of-the-Art Small Spacecraft Technology report — NASA.

### theme:in_orbit_services_servicing
- **name_en:** On-orbit servicing & life extension
- **name_zh:** 在轨服务
- **value_chain_position:** midstream
- **parent_sub_theme:** theme:space_segment_industry
- **defining_activities:** perform rendezvous-and-proximity operations on client spacecraft; refuel, repair and reposition satellites; execute end-of-life deorbit and debris-removal missions.
- **distinct_from:** `theme:in_space_manufacturing` — servicing existing assets vs producing new materials; distinct from `theme:space_situational_awareness_traffic` (acting in orbit vs tracking/cataloguing).
- **exclusions:** launch services; satellite insurance claims handling.
- **china_relevance:** medium — domestic on-orbit servicing demonstrations (refueling/debris experiments) remain state-led, with commercial entry emerging.
- **confidence:** medium
- **sources:** On-orbit Servicing, Assembly, and Manufacturing (OSAM) mission documentation — NASA; Mitigation of Orbital Debris rules incl. five-year deorbit requirement — US Federal Communications Commission (FCC); Space Debris Mitigation Guidelines — Inter-Agency Space Debris Coordination Committee (IADC).

### theme:in_space_manufacturing
- **name_en:** In-space manufacturing & research platforms
- **name_zh:** 在轨制造
- **value_chain_position:** midstream
- **parent_sub_theme:** theme:space_segment_industry
- **defining_activities:** operate microgravity production platforms; manufacture specialty materials/fibers and host life-science payloads; return products or data to terrestrial customers.
- **distinct_from:** `theme:in_orbit_services_servicing` — production for terrestrial markets vs maintenance of orbiting assets; distinct from `theme:laboratory_automation_robots` (proposed; terrestrial lab robotics).
- **exclusions:** crewed station operations themselves; remote-sensing payload hosting (→ `theme:earth_observation`).
- **china_relevance:** medium — space-station science payload programs and commercial microgravity research demand are nascent but policy-supported.
- **confidence:** low
- **sources:** In Space Production Applications (InSPA) announcements — NASA; ISS National Lab research solicitations — Center for the Advancement of Science in Space (CASIS); The Space Economy in Figures — OECD.

### theme:launch_vehicle_propulsion
- **name_en:** Launch vehicle propulsion
- **name_zh:** 运载火箭动力系统
- **value_chain_position:** upstream
- **parent_sub_theme:** theme:launch_ground_infrastructure
- **defining_activities:** develop liquid rocket engines and solid motor stages; test and qualify propulsion systems; supply reusable-engine fleets to launch-vehicle programs.
- **distinct_from:** `theme:launch_services` — propulsion hardware sold to vehicle developers vs the flight service sold to satellite owners; distinct from `theme:aerospace_propulsion_engines` (proposed; gas-turbine aviation vs rocket propulsion).
- **exclusions:** spacecraft thrusters (→ `theme:space_components_subsystems`); missile motors (→ `theme:missile_propulsion_supply`).
- **china_relevance:** high — reusable-engine development and 商业火箭 ecosystem are prominent domestic commercial-space milestones.
- **confidence:** high
- **sources:** Space Technology Taxonomy, TA01 Launch Propulsion — NASA; Annual Compendium of Commercial Space Transportation — FAA Office of Commercial Space Transportation (AST); commercial transportation safety reports — FAA/AST.

### theme:spaceport_launch_infrastructure
- **name_en:** Spaceports & launch infrastructure
- **name_zh:** 商业航天发射场
- **value_chain_position:** upstream
- **parent_sub_theme:** theme:launch_ground_infrastructure
- **defining_activities:** build and license launch pads and support facilities; provide range-safety and mission-integration services; manage reentry/recovery sites.
- **distinct_from:** `theme:launch_vehicle_propulsion` — fixed infrastructure vs propulsion hardware; distinct from `theme:ground_segment_as_a_service` (launch-site infra vs satellite ground-station networks).
- **exclusions:** military missile test ranges; horizontal-runway airports without launch licensing.
- **china_relevance:** high — coastal commercial launch sites (海南商业航天发射场-class provincial programs) are new national infrastructure, though facilities are state-owned.
- **confidence:** high
- **sources:** Launch and reentry site licensing documentation — FAA Office of Commercial Space Transportation (AST); commercial aerospace promotion policy documents — 国家发展改革委 (NDRC) and provincial governments; The Space Economy in Figures — OECD.

### theme:ground_segment_as_a_service
- **name_en:** Ground stations & ground segment services
- **name_zh:** 地面段站网服务
- **value_chain_position:** midstream
- **parent_sub_theme:** theme:launch_ground_infrastructure
- **defining_activities:** operate distributed ground-station/teleport networks; provide TT&C, scheduling and downlink-as-a-service; route and preprocess satellite data for operators.
- **distinct_from:** `theme:satellite_ground_terminals` — operator-side infrastructure services vs mass-market user hardware; distinct from `theme:satellite_broadband_services` (selling connectivity vs selling ground access).
- **exclusions:** consumer set-top/terminal retail; broadcast uplinks for TV networks.
- **china_relevance:** medium — ground-station networks scale with domestic constellation deployment; much capacity is state-built.
- **confidence:** medium
- **sources:** CCSDS recommendations — Consultative Committee for Space Data Systems (CCSDS); ground segment and operations documentation — European Space Operations Centre (ESA/ESOC); industry reports — Global Satellite Operators Association (GSOA).

### theme:space_situational_awareness_traffic
- **name_en:** Space situational awareness & traffic management
- **name_zh:** 太空态势感知
- **value_chain_position:** downstream
- **parent_sub_theme:** theme:space_data_services
- **defining_activities:** track and catalogue orbiting objects; screen conjunctions and issue collision-avoidance warnings; deliver space-weather and debris-environment services.
- **distinct_from:** `theme:earth_observation` — imaging the Earth vs tracking objects around it; distinct from `theme:space_security_counterspace` (proposed; civil safety assurance vs defense space-control systems).
- **exclusions:** astrophysics surveys; radio-frequency spectrum monitoring for regulators.
- **china_relevance:** high — national space-object monitoring system buildout is an explicit priority as domestic constellation traffic grows.
- **confidence:** high
- **sources:** Space Debris Mitigation Guidelines — Inter-Agency Space Debris Coordination Committee (IADC); Long-Term Sustainability of Outer Space Activities guidelines — UN Committee on the Peaceful Uses of Outer Space (COPUOS); Space-Track catalogue services — 18th Space Defense Squadron, US Space Force.

### theme:geospatial_intelligence_analytics
- **name_en:** Geospatial intelligence & EO analytics
- **name_zh:** 地理空间智能
- **value_chain_position:** downstream
- **parent_sub_theme:** theme:space_data_services
- **defining_activities:** turn imagery into change-detection and monitoring products; build analytics platforms over multi-source EO data; deliver mapping/INSAR and 3D-baseline deliverables.
- **distinct_from:** `theme:earth_observation` — raw imaging/sensing from orbit vs the value-added analytics tier sold to end users; distinct from `theme:space_situational_awareness_traffic` (Earth-surface products vs orbit-object safety).
- **exclusions:** raw tasking/imaging itself; consumer map apps.
- **china_relevance:** high — 卫星应用 industry plans and provincial remote-sensing industry parks grow the domestic analytics layer.
- **confidence:** high
- **sources:** OGC standards — Open Geospatial Consortium; GEOINT community publications — US Geospatial Intelligence Foundation (USGIF); Copernicus programme documentation — European Commission / ESA.

### theme:positioning_navigation_timing
- **name_en:** Satellite navigation & timing (PNT)
- **name_zh:** 卫星导航与授时
- **value_chain_position:** midstream
- **parent_sub_theme:** theme:space_data_services
- **defining_activities:** produce GNSS chipsets, modules and antennas; operate augmentation and correction services; develop resilient alternative-PNT (terrestrial/LEO) systems.
- **distinct_from:** `theme:satellite_broadband_services` — a positioning/timing signal service vs communications capacity; distinct from `theme:satellite_iot_messaging` (proposed; location fix vs machine messaging).
- **exclusions:** inertial navigation as standalone avionics; cellular network timing without PNT context.
- **china_relevance:** high — 北斗规模化应用 policy makes the PNT industry chain a named national strategic emerging industry.
- **confidence:** high
- **sources:** GNSS Market Report — EU Agency for the Space Programme (EUSPA); National PNT Advisory Board reports — US Department of Transportation; RTCM standards — Radio Technical Commission for Maritime Services.

### theme:satellite_iot_messaging
- **name_en:** Satellite IoT & narrowband messaging
- **name_zh:** 卫星物联网
- **value_chain_position:** downstream
- **parent_sub_theme:** theme:space_data_services
- **defining_activities:** operate narrowband store-and-forward constellations; integrate NTN messaging into standard chipsets; serve asset-tracking, maritime and utility telemetry markets.
- **distinct_from:** `theme:direct_to_device_connectivity` — machine telemetry at kilobit scale vs consumer voice/data to handsets; distinct from `theme:satellite_broadband_services` (narrowband IoT vs high-throughput access).
- **exclusions:** terrestrial LPWAN networks; AIS mandated transponders.
- **china_relevance:** high — 天地一体化 information-network plans fold satellite IoT into national new-infrastructure programs (信通院 white-paper territory).
- **confidence:** high
- **sources:** 3GPP Non-Terrestrial Networks (NTN) specifications, Rel-17/18 — 3GPP; satellite IoT and NTN market research — Euroconsult/Novaspace; 天地一体化信息网络 white papers — 中国信息通信研究院 (CAICT).

### theme:space_security_counterspace
- **name_en:** Space security & counterspace systems
- **name_zh:** 空间安全与攻防系统
- **value_chain_position:** midstream
- **parent_sub_theme:** none
- **defining_activities:** harden and proliferate defense satellite architectures; field jamming-detection and EMP/kinetic-threat resilience; provide defense space-domain-awareness inputs to warfighter networks.
- **distinct_from:** `theme:military_space_communications` — protected communications services vs the defensive/enabling space-control systems around them; distinct from `theme:space_situational_awareness_traffic` (civil safety cataloguing vs defense threat response).
- **exclusions:** offensive weapons programs (not equity-segment vocabulary); civil traffic management.
- **china_relevance:** high — 太空攻防 is an active PLA modernization domain and domestic policy discourse mirrors global counterspace investment.
- **confidence:** medium
- **sources:** Space Threat Assessment (annual) — Center for Strategic and International Studies (CSIS); Global Counterspace Capabilities report (annual) — Secure World Foundation; space security and PAROS research papers — UNIDIR.

### theme:deep_space_missions
- **name_en:** Deep space & planetary exploration
- **name_zh:** 深空探测
- **value_chain_position:** midstream
- **parent_sub_theme:** none
- **defining_activities:** build planetary probes, landers and sample-return spacecraft; develop deep-space relay and communications infrastructure; execute lunar-economy logistics and ISRU demonstration missions.
- **distinct_from:** `theme:spacecraft_manufacturing_satellites` — Earth-orbiting spacecraft OEM vs exploration-class mission systems; distinct from `theme:launch_vehicle_propulsion` (missions vs propulsion hardware).
- **exclusions:** orbital tourism; military space-control (→ `theme:space_security_counterspace`).
- **china_relevance:** high — 探月工程/行星探测 (lunar and planetary programs) are flagship national efforts with a maturing supplier base.
- **confidence:** medium
- **sources:** Planetary Science and Astrobiology Decadal Survey — National Academies of Sciences, Engineering, and Medicine; Cosmic Vision programme documentation — ESA; lunar and deep-space exploration program plans — 国家航天局 (CNSA).

**Sub-theme grouping.** Three new sub_themes organize the expansion: `theme:space_segment_industry` (satellite assembly, components, servicing, in-space production — what flies), `theme:launch_ground_infrastructure` (propulsion, spaceports, ground-station networks — the capital base under everything), and `theme:space_data_services` (SSA/traffic, geospatial analytics, PNT, satellite IoT — data and assurance sold from orbit). The existing `theme:satellite_connectivity_services` sub_theme and its micros remain unchanged; `theme:space_security_counterspace` and `theme:deep_space_missions` sit directly under the theme as programmatic rows without a sub_theme.

**Theme-tier candidates (prose only).** Two candidates for the seat: (1) a defense-space theme (space control, proliferated defense architectures, tactically responsive launch) could eventually split from `defense_aerospace`/`space_satellite` with dual parents as military-space procurement separates from civil space; (2) a space-science-exploration theme could gather deep-space missions, space astronomy and human spaceflight under one programmatic umbrella if issuer exposure materializes.

## theme:fintech_payments

No V1 micros exist under this theme (Finance R11 was not federated), so all 14 rows below are new. The V1 REJECTED-table rejections were federation-scope (L9) decisions, superseded by this lane's commission; the two substance-based rejections remain respected — no stance/monoline classes are proposed, and identity/fraud work is scoped to regulatory AML transaction monitoring to avoid the cybersecurity overlap flagged in V1.

### theme:digital_payment_processing
- **name_en:** Digital payment processing & gateways
- **name_zh:** 数字支付处理
- **value_chain_position:** downstream
- **parent_sub_theme:** theme:merchant_acceptance_processing
- **defining_activities:** authorize, capture and settle transactions for merchants; provide gateways, tokenization and checkout orchestration; underwrite merchant acquiring risk.
- **distinct_from:** `theme:payment_network_schemes` — merchant-side acceptance vs the inter-bank switching/clearing rail; distinct from `theme:pos_hardware_smart_terminals` (software processing vs acceptance hardware).
- **exclusions:** consumer wallets' social features; lending products attached at checkout (→ `theme:digital_lending_credit_tech`).
- **china_relevance:** high — 非银行支付机构监督管理条例 re-frames licensed processing economics for the world's largest mobile-payment market.
- **confidence:** high
- **sources:** Developments in retail payments reports — Bank for International Settlements, CPMI; PCI DSS standards — PCI Security Standards Council; The Federal Reserve Payments Study — Federal Reserve System.

### theme:pos_hardware_smart_terminals
- **name_en:** Payment terminals & acceptance hardware
- **name_zh:** 支付终端与受理设备
- **value_chain_position:** upstream
- **parent_sub_theme:** theme:merchant_acceptance_processing
- **defining_activities:** manufacture certified POS/smart terminals; ship secure readers and PIN pads; implement softPOS acceptance on commodity phones.
- **distinct_from:** `theme:digital_payment_processing` — certified hardware form factors vs processing software services; distinct from `theme:cash_cycle_atm_networks` (acceptance devices vs cash dispensing/recycling).
- **exclusions:** consumer wearables' payment chips; barcode-scanner peripherals.
- **china_relevance:** high — domestic terminal makers lead global smart-terminal shipments and smart POS iteration (刷脸/掌纹-class biometric acceptance).
- **confidence:** high
- **sources:** EMV specifications — EMVCo; PIN Transaction Security (PTS) requirements — PCI Security Standards Council; retail payment messaging standards (ISO 8583 family) — ISO TC 68.

### theme:b2b_payments_automation
- **name_en:** B2B payments & AP/AR automation
- **name_zh:** 企业支付自动化
- **value_chain_position:** downstream
- **parent_sub_theme:** theme:merchant_acceptance_processing
- **defining_activities:** automate invoicing and payables/receivables workflows; issue virtual cards and managed corporate spend; integrate payments into ERP/procurement systems.
- **distinct_from:** `theme:digital_payment_processing` — enterprise invoice/payables rails vs consumer checkout acceptance; distinct from `theme:instant_account_payment_rails` (a consumer of those rails, not the rail).
- **exclusions:** trade-finance letters of credit; procurement marketplace software.
- **china_relevance:** medium — B2B payment digitalization grows with supply-chain-finance platforms, though corporate settlement remains bank-centric.
- **confidence:** high
- **sources:** Strategic payments surveys — Association for Financial Professionals (AFP); ACH rules and network statistics — Nacha; retail/C2B payments reports — BIS CPMI.

### theme:payment_network_schemes
- **name_en:** Payment networks & clearing schemes
- **name_zh:** 支付网络与清算
- **value_chain_position:** midstream
- **parent_sub_theme:** theme:money_movement_rails
- **defining_activities:** operate card-scheme authorization and clearing; set scheme rules and interchange frameworks; run fraud/standards programs across issuers and acquirers.
- **distinct_from:** `theme:digital_payment_processing` — the network between issuers/acquirers vs services to merchants; distinct from `theme:instant_account_payment_rails` (card four-party scheme vs account-based credit transfer).
- **exclusions:** individual issuing banks; ATM/branch infrastructure.
- **china_relevance:** high — 银联-class domestic scheme economics and clearing-license regime (清算机构牌照) define a bounded domestic market.
- **confidence:** high
- **sources:** The Federal Reserve Payments Study — Federal Reserve System; interchange-cap regulation studies — US Federal Reserve (Durbin Amendment research); payments statistics and reports — European Central Bank.

### theme:instant_account_payment_rails
- **name_en:** Instant account-to-account payment rails
- **name_zh:** 实时账户支付
- **value_chain_position:** midstream
- **parent_sub_theme:** theme:money_movement_rails
- **defining_activities:** operate real-time credit-transfer schemes; migrate banks to ISO 20022 messaging; build request-to-pay and overlay services on instant rails.
- **distinct_from:** `theme:payment_network_schemes` — account-based transfer vs card schemes; distinct from `theme:stablecoin_tokenized_money` (ledger-based tokens vs bank-account rails).
- **exclusions:** legacy batch ACH modernization alone; intra-bank transfers.
- **china_relevance:** high — 网联 clearing plus bank real-time infrastructure underpins the largest instant-payment usage globally (人民银行 payment-system family).
- **confidence:** high
- **sources:** FedNow Service documentation — Federal Reserve System; SEPA Instant Credit Transfer scheme rulebooks — European Payments Council; fast payments reports — BIS CPMI.

### theme:stablecoin_tokenized_money
- **name_en:** Stablecoins & tokenized money
- **name_zh:** 稳定币与代币化货币
- **value_chain_position:** midstream
- **parent_sub_theme:** theme:money_movement_rails
- **defining_activities:** issue reserve-backed stablecoins under supervisory frameworks; tokenize deposits and money-market instruments; run redemption and reserve-attestation operations.
- **distinct_from:** `theme:instant_account_payment_rails` — distributed-ledger token rail vs bank-account credit transfer; distinct from `theme:cbdc_infrastructure` (private issuance vs sovereign).
- **exclusions:** unbacked crypto assets; crypto exchanges' trading venues.
- **china_relevance:** medium — mainland restricts crypto issuance; 香港金管局 stablecoin regime makes the HK franchise a live China-adjacent market.
- **confidence:** medium
- **sources:** High-level Recommendations for Global Stablecoin Arrangements — Financial Stability Board (FSB); crypto-asset and DeFi reports — Bank for International Settlements (BIS); 稳定币条例 — 香港金融管理局 (HKMA).

### theme:cbdc_infrastructure
- **name_en:** Central bank digital currency infrastructure
- **name_zh:** 央行数字货币
- **value_chain_position:** midstream
- **parent_sub_theme:** theme:money_movement_rails
- **defining_activities:** build CBDC core ledgers and wallet systems; implement two-tier distribution through intermediaries; support programmable-payment pilots.
- **distinct_from:** `theme:stablecoin_tokenized_money` — sovereign money vs private tokenized cash; distinct from `theme:instant_account_payment_rails` (a new money form vs faster movement of bank deposits).
- **exclusions:** wholesale settlement experiments without retail instruments; crypto-mining infrastructure.
- **china_relevance:** high — 数字人民币 (e-CNY) is the most advanced major-economy retail CBDC program, with published PBoC white-paper framework.
- **confidence:** high
- **sources:** Central bank digital currencies: foundational principles and core features — BIS and seven central banks; digital euro progress reports — European Central Bank; 《中国数字人民币的研发进展》白皮书 — 中国人民银行 (PBoC).

### theme:cross_border_remittance_infra
- **name_en:** Cross-border payments & remittances
- **name_zh:** 跨境支付与汇款
- **value_chain_position:** midstream
- **parent_sub_theme:** theme:money_movement_rails
- **defining_activities:** move value across currency corridors; provide FX and correspondent-bank alternatives; serve migrant remittance and SME trade payment flows.
- **distinct_from:** every domestic rail row — the multi-corridor settlement/FX layer; distinct from `theme:stablecoin_tokenized_money` when tokens are the corridor (row covers the corridor economics regardless of rail).
- **exclusions:** trade-document digitization (trade finance); tourist FX retail.
- **china_relevance:** high — CIPS-class RMB internationalization and 跨境电商 collections make cross-border rails a strategic domestic buildout.
- **confidence:** high
- **sources:** G20 Roadmap for Enhancing Cross-border Payments — FSB / BIS CPMI; Remittance Prices Worldwide — World Bank; Payment Aspects of Financial Inclusion — BIS CPMI and World Bank Group.

### theme:open_banking_data_sharing
- **name_en:** Open banking & financial data access
- **name_zh:** 开放银行
- **value_chain_position:** enabler
- **parent_sub_theme:** theme:open_finance_platforms
- **defining_activities:** expose bank account data via mandated APIs; aggregate accounts and initiate payments under consent; certify third-party providers under open-finance regimes.
- **distinct_from:** `theme:embedded_finance_baas` — mandated data-access rights vs discretionary product embedding; distinct from payment rail rows (data layer, not money movement).
- **exclusions:** credit bureaus' regulated data; marketing-data brokers.
- **china_relevance:** medium — personal-information protection law and 金融数据 security rules shape a consent-based data-sharing layer, still bank-led pilots.
- **confidence:** high
- **sources:** PSD2 revised payment services directive — European Union; Open Banking Standards — UK Open Banking Implementation Entity (OBIE); Section 1033 personal financial data rights rule — US Consumer Financial Protection Bureau (CFPB).

### theme:embedded_finance_baas
- **name_en:** Embedded finance & banking-as-a-service
- **name_zh:** 嵌入式金融与银行即服务
- **value_chain_position:** downstream
- **parent_sub_theme:** theme:open_finance_platforms
- **defining_activities:** provide API stacks hosting regulated products (accounts, cards, credit) for non-financial brands; manage program compliance and BIN sponsorship; distribute financial products at partner point-of-need.
- **distinct_from:** `theme:open_banking_data_sharing` — product distribution vs data access; distinct from `theme:digital_lending_credit_tech` (the embedding platform vs the credit decision itself).
- **exclusions:** white-label hardware; loyalty points programs without regulated products.
- **china_relevance:** medium — 场景金融 partnerships thrive but under stricter joint-liability supervision after platform-loan rules.
- **confidence:** medium
- **sources:** FSI Insights on the digitalisation of payments and finance — BIS; fintech and innovation regulatory sandboxes — UK Financial Conduct Authority (FCA); fintech banking guidance — US Office of the Comptroller of the Currency (OCC).

### theme:digital_lending_credit_tech
- **name_en:** Digital lending & credit technology
- **name_zh:** 数字信贷
- **value_chain_position:** downstream
- **parent_sub_theme:** none
- **defining_activities:** underwrite consumer/SME credit with alternative data; originate, service and collect loans digitally; embed credit decisioning APIs into partners.
- **distinct_from:** `theme:embedded_finance_baas` — the credit product/risk vs the embedding stack; distinct from `theme:transaction_monitoring_aml` (credit underwriting vs financial-crime screening).
- **exclusions:** mortgage servicing platforms; credit-rating agencies.
- **china_relevance:** high — internet-loan rules (商业银行互联网贷款管理) institutionalize a large supervised digital-credit market.
- **confidence:** high
- **sources:** Global Findex Database — World Bank; Fintech credit markets around the world — BIS working papers; 商业银行互联网贷款管理暂行办法 — 中国银保监会 (CBIRC).

### theme:retail_investment_platforms
- **name_en:** Digital wealth & retail investment platforms
- **name_zh:** 数字财富管理
- **value_chain_position:** downstream
- **parent_sub_theme:** theme:open_finance_platforms
- **defining_activities:** operate retail brokerage and savings-investment apps; provide robo-advisory and model portfolios; custody and clear retail asset flows.
- **distinct_from:** payment and lending rows — savings/investment products vs payments or credit; distinct from `theme:crypto_digital_assets` macro category (regulated securities wealth vs digital-asset venues).
- **exclusions:** institutional prime brokerage; pension administration.
- **china_relevance:** high — fund-distribution platforms under 公募基金销售 rules serve the world's largest retail fund flows.
- **confidence:** medium
- **sources:** FINRA Industry Snapshot — FINRA; Investment platforms market study — UK Financial Conduct Authority (FCA).

### theme:transaction_monitoring_aml
- **name_en:** Transaction monitoring & AML compliance
- **name_zh:** 反洗钱与交易监控
- **value_chain_position:** enabler
- **parent_sub_theme:** none
- **defining_activities:** screen transactions for AML/sanctions risk; run KYC/CDD programs and periodic reviews; file suspicious-activity and regulatory reports.
- **distinct_from:** `theme:identity_access_management` / `theme:identity_fraud_anti_abuse` (proposed, cybersecurity) — regulatory financial-crime compliance vs enterprise access control and consumer abuse; distinct from all rails rows (a compliance overlay, not a rail).
- **exclusions:** tax advisory; internal fraud HR investigations.
- **china_relevance:** high — 反洗钱法 amendments (2024 revision, effective 2025) expand obligation scope; 反诈 monitoring obligations bind every payment institution.
- **confidence:** high
- **sources:** FATF Recommendations — Financial Action Task Force (FATF); BSA/AML Examination Manual — FFIEC; customer due diligence rules — FinCEN (US Treasury).

### theme:cash_cycle_atm_networks
- **name_en:** Cash cycle & ATM networks
- **name_zh:** 现金循环与自助设备
- **value_chain_position:** midstream
- **parent_sub_theme:** none
- **defining_activities:** manufacture and service ATMs/CRS recycling machines; operate cash-in-transit and vault logistics; manage recirculation and cash-forecasting for banks.
- **distinct_from:** `theme:pos_hardware_smart_terminals` — cash dispensing/recycling infrastructure vs acceptance terminals; distinct from all digital-rail rows (physical cash persists alongside them).
- **exclusions:** bank branch staffing; retail safes.
- **china_relevance:** medium — ATM/CRS demand declines with mobile payment yet remains policy-maintained for cash access (人民币现金收付 rights rules).
- **confidence:** high
- **sources:** Study on the payment attitudes of consumers (SPACE) — European Central Bank; Diary of Consumer Payment Choice — Federal Reserve Banks (Atlanta/San Francisco); ATM industry statistics — ATMIA.

**Sub-theme grouping.** Three new sub_themes organize the expansion: `theme:merchant_acceptance_processing` (processing, terminals, B2B payables — the accept-money side), `theme:money_movement_rails` (card schemes, instant rails, stablecoins, CBDC, cross-border — the move-money layer), and `theme:open_finance_platforms` (open banking, embedded finance, digital wealth — the access-and-distribution layer). `theme:digital_lending_credit_tech`, `theme:transaction_monitoring_aml` and `theme:cash_cycle_atm_networks` sit directly under the theme — credit, compliance and cash are theme-wide rather than one rail's concern.

**Theme-tier candidates (prose only).** Three candidates for the seat: (1) a `theme:digital_assets_tokenization` theme under the currently empty `theme:crypto_digital_assets` macro category (tokenized securities, custody, on-chain markets) — distinct from the stablecoin rail row proposed here; (2) an `theme:insurance_technology` theme under `theme:financial_services` (underwriting, claims, distribution) — insurance has no theme today; (3) a `theme:financial_market_infrastructure` theme (exchange/clearing/dematerialization technology) if the seat wants capital-markets plumbing separate from retail payments.
