# GMI micro-theme expansion group C2 — Security, Industrial, Space & Payments chains

Status: DRAFT taxonomy content PROPOSED for seat ratification — display-only navigation vocabulary; no tickers, no constituents, no weights, no predictive claims.
Lane: gmi-micro-c2-20261021 · Commissioned by: GMI COMPLETION seat (Fable Meta-CEO, Chairman commission 2026-10-21).
Base commit: ca7edbcf50df21bd321bffa3433e5f105d3335da (origin/main read at that sha).
Companion rows file: `research/theme_graph/micro_expansion_20261021/C2_PROPOSED_ROWS.yaml`.
Union lane: gmi-micro-u2-20261021-r1 — UNION of variant A (lane/gmi-micro-c2-20261021-r4, PR #9985) and variant B (lane/gmi-micro-c2-20261021-r9, PR #9983); spine = B byte-for-byte, A-only micros grafted, duplicates reconciled — see `## Union ledger` at the end of this file.

## Scope and method

- Five themes: `theme:cybersecurity`, `theme:defense_aerospace`, `theme:robotics_automation`, `theme:space_satellite`, `theme:fintech_payments`.
- Every proposed micro describes **what an equity issuer DOES** along the theme's value chain (upstream / midstream / downstream / enabler). Existing micros under these themes are untouched — no renames, no re-ids; rows below ADD and state mechanism distinctness from the nearest existing row in the `note`/`distinct_from` fields.
- Sources: each micro cites ≥2 public, non-vendor references **by name** — industry-association taxonomies, standards bodies, regulator classifications, supervisory white papers, trade-press value-chain maps, academic/industry reports. Chinese names use the natural A-share/HK disclosure and Chinese trade-press terms. No vendor theme families (finviz, ths/tonghuashun) as sources or nominators.
- No constituents: no issuer names, tickers, or "examples of companies" anywhere; organizations cited are references (standards bodies, regulators, associations), not membership evidence.
- V1 note: the C2 hierarchy-content record (2026-10-13) rejected four fintech surfaces solely under the V1 L9 gate ("Finance R11 not federated"). The current commission federates fintech explicitly; rows below re-open that space with distinct slugs and tighter mechanisms (no interchange/monoline stance rows, no hybrid slug). The seat ratifies or rejects; nothing here is admitted by this document.

---

## theme:cybersecurity — Cybersecurity

Existing micros (unchanged): `theme:endpoint_security`, `theme:network_security`, `theme:identity_access_management`, `theme:cloud_security` — all defined by the protected SURFACE. The new rows cut the industry by value-chain mechanism instead: what an issuer builds or runs to produce security outcomes (engineering inputs, control platforms, and the operations/assurance market), not which surface it guards.

**Sub-theme grouping.** Three new sub-themes group the new rows: `theme:security_engineering_enablement` (enabler inputs: intelligence, vulnerability research, secure development, supply-chain attestation, cryptography, people), `theme:security_control_platforms` (midstream product platforms organized by control mechanism rather than surface: zero-trust access, data governance, OT/IoT, AI security), and `theme:security_operations_assurance` (downstream: the operations, integration/certification, insurance and sovereign-mission market). The four existing surface rows stay attached directly to `theme:cybersecurity`.

**Theme-tier candidates (prose only).** (1) `theme:ai_model_security_governance` could eventually justify a standalone AI-assurance theme under technology_software if model-risk markets institutionalize. (2) A national/sovereign-cyber demand pool sits between cybersecurity and defense_aerospace; if it grows, a cross-category "cyber defense" theme candidate exists — flagged for the seat, not proposed as a row.

### theme:threat_intelligence_cti — Threat intelligence feeds & platforms
- **name_en:** Threat intelligence feeds & platforms · **name_zh:** 威胁情报服务
- **value_chain_position:** enabler
- **parent_sub_theme:** theme:security_engineering_enablement
- **defining_activities:** curate adversary TTP/indicator feeds; operate intelligence platforms with SIEM/SOC integrations; produce finished sector intelligence; track actor infrastructure and campaign reuse
- **distinct_from:** theme:endpoint_security, theme:soc_mdr_services — those consume detection at surfaces; this row produces the curated adversary-knowledge layer itself
- **exclusions:** law-enforcement takedowns; classified national collection beyond commercial CTI
- **china_relevance:** high — 威胁情报 is a named segment in CAICT industry white papers and TC260 standardization work
- **confidence:** high
- **sources:** MITRE ATT&CK knowledge base (MITRE Corporation); OASIS STIX/TAXII Cyber Threat Intelligence specifications; 中国信息通信研究院《网络安全产业白皮书》; Data Breach Investigations Report — Verizon; FIRST CSIRT Services Framework — Forum of Incident Response and Security Teams (FIRST)

### theme:vulnerability_exposure_management — Vulnerability research & exposure management
- **name_en:** Vulnerability research & exposure management · **name_zh:** 漏洞研究与暴露面管理
- **value_chain_position:** enabler
- **parent_sub_theme:** theme:security_engineering_enablement
- **defining_activities:** run coordinated vulnerability disclosure; operate CVE-numbering and scoring pipelines; enumerate internet-facing attack surface; prioritize remediation against exploited-vulnerability intelligence; operate bug-bounty intake alongside coordinated disclosure
- **distinct_from:** theme:endpoint_security — endpoint detects exploits at runtime; this row supplies the pre-exploit weakness pipeline (CVE/CVSS/KEV-class feeds, external attack-surface discovery)
- **exclusions:** offensive exploitation for hire; brokered access markets
- **china_relevance:** high — 漏洞管理 is formalized in 网络安全等级保护 requirements and CNVD-class national platforms
- **confidence:** high
- **sources:** CVE Program and FIRST CVSS v4.0; CISA Known Exploited Vulnerabilities Catalog; ISO/IEC 30111 vulnerability handling processes

### theme:application_security_devsecops — Application security & DevSecOps
- **name_en:** Application security & DevSecOps · **name_zh:** 应用安全与开发安全
- **value_chain_position:** upstream
- **parent_sub_theme:** theme:security_engineering_enablement
- **defining_activities:** embed static/dynamic/dependency analysis in CI pipelines; govern API security testing; gate releases on secure-development policy; harden application architecture against OWASP-class flaws
- **distinct_from:** theme:endpoint_security, theme:cloud_security — both protect running systems; this row secures software before it ships, inside the development toolchain
- **exclusions:** runtime workload protection (cloud_security); developer-productivity tooling without security function; WAF runtime rules; manual pen-test consultancies as a service line
- **china_relevance:** high — 开发安全/软件安全开发 is promoted via 工信部 software-quality and 等保 pipeline requirements
- **confidence:** high
- **sources:** OWASP Application Security Verification Standard and OWASP Top 10; NIST SP 800-218 Secure Software Development Framework; ISO/IEC 27034 application security

### theme:supply_chain_firmware_security — Software supply chain & firmware security
- **name_en:** Software supply chain & firmware security · **name_zh:** 软件供应链与固件安全
- **value_chain_position:** upstream
- **parent_sub_theme:** theme:security_engineering_enablement
- **defining_activities:** generate and verify SBOMs; attest build provenance and signing chains; audit firmware and boot chains; enforce hardware root-of-trust and code-signing infrastructure; monitor dependency and registry risk; enforce release-integrity policy across vendors
- **distinct_from:** theme:application_security_devsecops — that row tests source code; this row certifies where software and firmware came from (provenance, SBOM, attestation); theme:hardware_root_of_trust — that row is the silicon trust anchor (TPM/secure element/HSM); this row certifies the software and firmware chain attested through it
- **exclusions:** generic IT asset management; endpoint runtime agents (endpoint_security); open-source project maintenance funding; hardware component sourcing security
- **china_relevance:** high — 供应链安全 and 可信固件 are standing themes in 等保 and 信创 security requirements
- **confidence:** medium
- **sources:** NIST SP 800-161 Rev.1 C-SCRM practices and NTIA SBOM minimum elements; OpenSSF SLSA build-provenance framework v1.0; Executive Order 14028, Improving the Nation's Cybersecurity — The White House

### theme:crypto_pki_key_management — Cryptography, PKI & key management
- **name_en:** Cryptography, PKI & key management · **name_zh:** 密码技术与密钥管理
- **value_chain_position:** enabler
- **parent_sub_theme:** theme:security_engineering_enablement
- **defining_activities:** operate certificate authorities and key-management services; build HSM-backed signing estates; plan post-quantum migration inventories; certify commercial-cryptography compliance
- **distinct_from:** theme:data_security_privacy_governance — that row enforces data-handling policy; this row issues and protects the cryptographic trust material beneath every control; theme:post_quantum_cryptography_migration — that row runs the algorithm-replacement migration program (CBOM, staged migration, crypto-agility); this row operates the standing PKI/key-material estate beneath it
- **exclusions:** application-level encryption features; blockchain custody rails outside PKI
- **china_relevance:** high — 商用密码 regime (密码法, GM/T standards, 国密算法迁移) is a distinct compliance market
- **confidence:** high
- **sources:** NIST FIPS 203/204/205 post-quantum cryptography standards; 国家密码管理局《商用密码管理条例》及 GM/T 系列标准; CA/Browser Forum TLS Baseline Requirements

### theme:cyber_workforce_training — Cyber workforce, ranges & training
- **name_en:** Cyber workforce, ranges & training · **name_zh:** 网络安全人才与实训
- **value_chain_position:** enabler
- **parent_sub_theme:** theme:security_engineering_enablement
- **defining_activities:** deliver role-based workforce curricula; operate cyber ranges and emulation environments; certify practitioner competence; run red-team/blue-team exercise programs; benchmark defensive tooling against adversary emulation
- **distinct_from:** theme:soc_mdr_services — that row sells monitoring outcomes; this row sells human capability and practice environments, not live detection
- **exclusions:** academic degree granting; general IT certification
- **china_relevance:** high — 网络空间安全 is a national first-level discipline; 攻防演练 (HW-class exercises) drives a dedicated training market
- **confidence:** medium
- **sources:** NIST SP 800-181 Rev.1 NICE Workforce Framework; ENISA cybersecurity education/skills reports; 中国网络空间安全协会 workforce programs; ATT&CK Evaluations — MITRE Corporation

### theme:zero_trust_sase_access — Zero-trust access & SASE
- **name_en:** Zero-trust access & SASE · **name_zh:** 零信任接入与SASE
- **value_chain_position:** midstream
- **parent_sub_theme:** theme:security_control_platforms
- **defining_activities:** broker per-session, per-application access decisions; converge SD-WAN with cloud-delivered edge enforcement; retire implicit network-location trust; continuously evaluate device/user posture; microsegment east-west data-center traffic
- **distinct_from:** theme:identity_access_management (directory-wide identity lifecycle) and theme:network_security (perimeter/traffic appliances) — this row is the identity-centric session-access control plane between them
- **exclusions:** legacy VPN appliance hardware; directory and SSO administration (identity row); consumer VPN; SD-WAN performance features without security enforcement
- **china_relevance:** high — 零信任 is a formalized CAICT standards series and 信通院/行业 pilot architecture
- **confidence:** high
- **sources:** NIST SP 800-207 Zero Trust Architecture; 中国信息通信研究院零信任系列标准与白皮书; Zero Trust Maturity Model — Cybersecurity and Infrastructure Security Agency (CISA)

### theme:data_security_privacy_governance — Data security & privacy governance
- **name_en:** Data security & privacy governance · **name_zh:** 数据安全与隐私合规
- **value_chain_position:** midstream
- **parent_sub_theme:** theme:security_control_platforms
- **defining_activities:** classify and inventory data; enforce DLP and encryption policy on data objects; operationalize privacy rights (consent, deletion, cross-border transfer); evidence compliance to supervisors; remediate data-exposure posture findings (DSPM); manage secrets vaulting
- **distinct_from:** theme:cloud_security (protects workloads), theme:identity_access_management (controls who acts) — this row governs the data object itself across wherever it lives
- **exclusions:** database administration; records-management software without security enforcement; backup infrastructure
- **china_relevance:** high — 数据安全法/个人信息保护法 + 数据分类分级 and 数据出境规则 created a dedicated compliance market
- **confidence:** high
- **sources:** 中华人民共和国《数据安全法》《个人信息保护法》及 GB/T 35273 个人信息安全规范; ISO/IEC 27701 privacy information management; NIST SP 800-53 Rev.5 (SC/PT control families) — NIST

### theme:ot_iot_industrial_security — OT, IoT & industrial security
- **name_en:** OT, IoT & industrial security · **name_zh:** 工控与物联网安全
- **value_chain_position:** midstream
- **parent_sub_theme:** theme:security_control_platforms
- **defining_activities:** passively inventory and monitor OT/IoT protocols; zone and conduit industrial networks; protect PLC/SCADA integrity where availability and safety outrank confidentiality; secure connected-device fleets; validate OT incident procedures
- **distinct_from:** theme:network_security — that row guards enterprise IT traffic; this row handles fieldbus/industrial protocols and safety-instrumented systems under IEC 62443 zone models
- **exclusions:** enterprise endpoint agents; building-automation comfort systems without safety impact; functional-safety engineering itself; physical security of substations
- **china_relevance:** high — 工业互联网安全 is a MIIT standard system with 等保2.0 industrial extensions
- **confidence:** high
- **sources:** IEC 62443 industrial automation and control systems security series; NIST SP 800-82 Rev.3 Guide to OT Security; 工信部《工业互联网安全标准体系》; MITRE ATT&CK for ICS — MITRE Corporation

### theme:ai_model_security_governance — AI security & model governance
- **name_en:** AI security & model governance · **name_zh:** 人工智能安全与模型治理
- **value_chain_position:** midstream
- **parent_sub_theme:** theme:security_control_platforms
- **defining_activities:** red-team models for adversarial/prompt-injection abuse; monitor model behavior and data pipelines; evidence AI risk to supervisors and boards; enforce generative-AI content and usage policy
- **distinct_from:** every surface row (endpoint/network/identity/cloud) — the protected asset here is the model and its training data, not a device, network or workload
- **exclusions:** generic AI development platforms; data-privacy compliance (data_security row)
- **china_relevance:** high — 《生成式人工智能服务管理暂行办法》与 TC260《人工智能安全治理框架》 created filing/assessment obligations
- **confidence:** medium
- **sources:** NIST AI Risk Management Framework 1.0; MITRE ATLAS adversarial threat lexicon for AI systems; TC260《人工智能安全治理框架》(2024)

### theme:soc_mdr_services — Security operations, SIEM & MDR
- **name_en:** Security operations, SIEM & MDR · **name_zh:** 安全运营与托管检测
- **value_chain_position:** downstream
- **parent_sub_theme:** theme:security_operations_assurance
- **defining_activities:** aggregate cross-surface telemetry into SIEM/XDR data platforms; run 24/7 triage, hunt and incident response; deliver managed detection/response outcomes; tune detections against adversary behavior; co-manage customer security tooling under retainer-based response readiness
- **distinct_from:** theme:endpoint_security, theme:network_security, theme:cloud_security — those sell per-surface products; this row sells the human-led operating service that runs across all of them; theme:extended_detection_response — that row is the cross-domain detection/analytics platform product; this row is the human-led operated service delivered on top of platforms; theme:digital_forensics_incident_response — that row is episodic post-compromise forensics and response engagements; this row is continuous monitoring operations
- **exclusions:** one-time implementation projects (integration row); workforce training (training row); pure staffing/body-shop arrangements
- **china_relevance:** high — 安全服务 (安全运营/托管) is the fastest-named segment in CAICT industry white papers; 等保 mandates monitoring capability
- **confidence:** high
- **sources:** NIST Cybersecurity Framework 2.0 (Detect/Respond functions); NIST SP 800-61 computer security incident handling guide; ENISA Threat Landscape reports; ISC2 Cybersecurity Workforce Study — ISC2

### theme:security_integration_compliance — Security integration & compliance assessment
- **name_en:** Security integration & compliance assessment · **name_zh:** 安全集成与合规测评
- **value_chain_position:** downstream
- **parent_sub_theme:** theme:security_operations_assurance
- **defining_activities:** design and implement control stacks at customer sites; integrate multi-vendor security architectures; conduct 等保测评-class conformity assessments; prepare audit evidence for certification bodies
- **distinct_from:** theme:soc_mdr_services — that row monitors continuously; this row delivers one-time/periodic implementation and certification assurance; theme:security_governance_compliance — that row operates GRC platforms and risk governance; this row delivers on-site integration labor and conformity assessment
- **exclusions:** product resale without integration labor; ongoing monitoring
- **china_relevance:** high — 等级保护测评 (GB/T 28448) is a licensed assessment market unique to China compliance
- **confidence:** high
- **sources:** GB/T 22239 网络安全等级保护基本要求与 GB/T 28448 测评要求; ISO/IEC 27001 certification scheme (IAF-accredited conformity assessment)

### theme:cyber_insurance_risk_quantification — Cyber insurance & risk quantification
- **name_en:** Cyber insurance & risk quantification · **name_zh:** 网络保险与风险量化
- **value_chain_position:** downstream
- **parent_sub_theme:** theme:security_operations_assurance
- **defining_activities:** underwrite cyber policies on quantified loss models; model probable-maximum-loss from attack trees; operate breach-response and recovery coverage services; price control improvements into premiums; require security-control baselines from insureds; pay and manage breach-related claims
- **distinct_from:** theme:soc_mdr_services — that row reduces loss; this row finances residual risk — an insurance-market mechanism absent from the existing four surface rows
- **exclusions:** property/casualty lines without cyber exposure; reinsurers without cyber books; health/PII insurance lines; warranty extensions
- **china_relevance:** medium — 工信部与金融监管总局 2023《关于促进网络安全保险规范健康发展的意见》 formalized the segment
- **confidence:** medium
- **sources:** NAIC Cyber Insurance Reports (US market data); 工信部、国家金融监督管理总局《关于促进网络安全保险规范健康发展的意见》(2023); cyber risk and insurance research papers — The Geneva Association; EIOPA staff papers on cyber insurance

### theme:national_cyber_defense — National cyber defense missions
- **name_en:** National cyber defense missions · **name_zh:** 国家级网络防御
- **value_chain_position:** downstream
- **parent_sub_theme:** theme:security_operations_assurance
- **defining_activities:** build sovereign SOC/CERT infrastructure; deliver cleared defensive services to states; operate national situational-awareness and early-warning systems; support treaty and norms implementation
- **distinct_from:** theme:soc_mdr_services — that row serves enterprises commercially; this row serves states under classified, policy-driven mission programs
- **exclusions:** offensive cyber operations; election administration itself
- **china_relevance:** high — 《国家网络空间安全战略》 and 关键信息基础设施保护条例 define the sovereign demand pool
- **confidence:** medium
- **sources:** NATO Cooperative Cyber Defence Centre of Excellence, Tallinn Manual 2.0; 中国《国家网络空间安全战略》(2016)


**Union grafts (variant A rows re-parented onto this spine — see `## Union ledger`):**

### theme:extended_detection_response
- **name_en:** Extended detection and response platforms
- **name_zh:** 扩展检测与响应（XDR/SIEM）
- **value_chain_position:** midstream
- **parent_sub_theme:** theme:security_control_platforms
- **defining_activities:** correlate telemetry across endpoint, identity, network and cloud domains; build detection content and analytics pipelines; orchestrate automated response playbooks; retain and hunt through security event history.
- **distinct_from:** `theme:endpoint_security` — endpoint_security protects the device itself; this row is the cross-domain analytics and response orchestration plane that consumes signals from it; distinct from theme:soc_mdr_services (the human-led operated service layer vs this platform product)
- **exclusions:** the protective agents themselves; outsourced operations (→ `theme:soc_mdr_services`).
- **china_relevance:** high — 等级保护2.0 and 关键信息基础设施安全保护条例 mandate monitoring and audit capability that maps to this segment.
- **confidence:** high
- **sources:** MITRE ATT&CK knowledge base — MITRE Corporation; NIST Cybersecurity Framework 2.0 (Detect/Respond functions) — NIST; SANS SOC Survey — SANS Institute.

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
- **distinct_from:** `theme:identity_access_management` — IAM is workforce/enterprise access governance; this row is consumer-facing fraud and abuse economics; distinct from `theme:payments_fraud_aml_decisioning` (proposed; regulatory money-flow screening).
- **exclusions:** consumer credit scoring; payment-network fraud rules (→ fintech AML row).
- **china_relevance:** high — 反电信网络诈骗法 obliges platforms to deploy real-time fraud interception, a statutory demand driver.
- **confidence:** high
- **sources:** NIST SP 800-63 Digital Identity Guidelines — NIST; FIDO2/WebAuthn specifications — FIDO Alliance; OWASP Automated Threats to Web Applications — OWASP Foundation.

### theme:digital_forensics_incident_response
- **name_en:** Digital forensics & incident response
- **name_zh:** 数字取证与应急响应
- **value_chain_position:** downstream
- **parent_sub_theme:** theme:security_operations_assurance
- **defining_activities:** acquire and analyse forensic evidence after compromise; reconstruct intrusion timelines and root causes; support regulatory notification and recovery; negotiate/assist extortion incident handling.
- **distinct_from:** `theme:soc_mdr_services` — continuous monitoring versus episodic post-compromise engagements; distinct from `theme:cyber_workforce_training` (preparation, not response).
- **exclusions:** law-enforcement investigations for non-cyber crime; routine backup restore services.
- **china_relevance:** medium — 网络安全审查 and incident-reporting rules (《网络安全法》) create demand, though much DFIR work sits inside SOEs.
- **confidence:** high
- **sources:** NIST SP 800-86, Guide to Integrating Forensic Techniques into Incident Response — NIST; ISO/IEC 27037 (incident evidence identification/collection) — ISO/IEC; Computer Security Incident Handling Guide — SANS Institute.

### theme:security_governance_compliance
- **name_en:** Security governance, risk & compliance
- **name_zh:** 安全治理与合规
- **value_chain_position:** enabler
- **parent_sub_theme:** theme:security_operations_assurance
- **defining_activities:** operate GRC platforms and control libraries; quantify cyber risk financially; automate audit evidence; run board-level cyber disclosure and third-party risk programs.
- **distinct_from:** every technical control row — this governs and evidences security rather than preventing or detecting anything; distinct from `theme:cyber_insurance_risk_quantification` (internal governance vs external risk transfer); distinct from theme:security_integration_compliance (GRC platforms and risk governance vs on-site integration labor and conformity assessment)
- **exclusions:** legal counsel services; general enterprise GRC without security scope.
- **china_relevance:** high — 网络安全等级保护测评 and 数据安全 assessment obligations institutionalize a compliance tooling/services market.
- **confidence:** high
- **sources:** NIST Cybersecurity Framework 2.0 (Govern function) — NIST; Cybersecurity risk management and disclosure rules (Reg S-K Item 106) — US Securities and Exchange Commission; Directive (EU) 2022/2555 (NIS2) — European Union.

### theme:hardware_root_of_trust
- **name_en:** Hardware root of trust & secure elements
- **name_zh:** 硬件信任根
- **value_chain_position:** upstream
- **parent_sub_theme:** theme:security_engineering_enablement
- **defining_activities:** design/embed TPMs, secure enclaves and secure elements; manufacture and operate HSMs; implement measured boot and firmware attestation; certify cryptographic modules.
- **distinct_from:** `theme:endpoint_security` — software agents on devices versus the silicon anchor beneath them; distinct from `theme:defense_microelectronics` (proposed; defense-grade chips are a military supply chain, not a commercial trust product); distinct from theme:supply_chain_firmware_security (the provenance/attestation chain rooted in this silicon)
- **exclusions:** general SoC design; biometric sensors as hardware.
- **china_relevance:** high — 商用密码 and 可信计算 (TCM/可信计算3.0) create a parallel domestic trust-hardware stack.
- **confidence:** high
- **sources:** FIPS 140-3, Security Requirements for Cryptographic Modules — NIST; TPM 2.0 Library specification — Trusted Computing Group; GlobalPlatform device security specifications — GlobalPlatform.

### theme:post_quantum_cryptography_migration
- **name_en:** Post-quantum cryptography migration
- **name_zh:** 抗量子密码迁移
- **value_chain_position:** upstream
- **parent_sub_theme:** theme:security_engineering_enablement
- **defining_activities:** inventory cryptographic assets (CBOM-style); replace vulnerable public-key algorithms with NIST-standardized PQC; build crypto-agility into products; plan staged migration across long-lived systems.
- **distinct_from:** `theme:hardware_root_of_trust` — that row supplies fixed-function trust silicon; this row is the algorithm-replacement and migration program across all crypto use, software and hardware alike; distinct from theme:crypto_pki_key_management (that row operates standing PKI/key material; this row is the algorithm-replacement migration program)
- **exclusions:** quantum-computing hardware itself; quantum key distribution networks as a transport business.
- **china_relevance:** high — 国家密码管理局 drives 国密 algorithm families and PQC research; migration of banking/government crypto is a decade-scale program.
- **confidence:** medium
- **sources:** FIPS 203/204/205 Post-Quantum Cryptography Standards — NIST; Quantum-Safe Cryptography working group specifications — ETSI; Migration guidance to post-quantum cryptography — BSI (German Federal Office for Information Security).

---

## theme:defense_aerospace — Defense & Aerospace

Existing micros (unchanged): `theme:missiles_munitions_effects`, `theme:missile_propulsion_supply`, `theme:defense_sensors_electronics_c2`, `theme:autonomous_systems_counter_uas`, `theme:naval_shipbuilding`, `theme:aerospace_components_aftermarket`, `theme:military_space_communications`, plus sub_theme `theme:missile_munition_chain`. The V1 record already rejected contractor-stance rows and the standalone EW slug; the rows below stay neutral segment vocabulary and fill the missing domains: air/ground platforms, engines, advanced strike vehicles, the munitions chemical/component tiers, and the technology/readiness base.

**Sub-theme grouping.** `theme:defense_platform_programs` groups whole-platform primes by domain (air, land, engines, integrated air defense). `theme:strike_munitions_chain` extends the existing missile chain upstream into hypersonic vehicles, energetics chemistry and guidance components. `theme:defense_technology_readiness` groups the enabling industrial base (trusted microelectronics, photonics, training/simulation, digital modernization) and downstream readiness services (sustainment/MRO, CBRN protection). **Union addendum:** `theme:civil_aerospace_economy` is carried over from variant A (civil air-traffic management and business/general aviation — the non-defense half of aerospace) and groups `theme:air_traffic_management_systems` and `theme:business_general_aviation`.

**Theme-tier candidates (prose only).** (1) A "space defense / counterspace" theme candidate spans defense_aerospace and space_satellite — left out of scope here as a sensitive adjacency. (2) If the seat wants deeper strike-chain granularity, `theme:strike_munitions_chain` could mature into a standalone theme beside `theme:missile_munition_chain`.

### theme:military_aircraft_platforms — Military aircraft platforms
- **name_en:** Military aircraft platforms · **name_zh:** 军用飞机平台
- **value_chain_position:** midstream
- **parent_sub_theme:** theme:defense_platform_programs
- **defining_activities:** design and integrate complete combat/trainer/transport aircraft; manage multi-decade platform programs and upgrades; deliver aircraft-with-mission-systems packages; sustain fleet airworthiness; manage sovereign assembly and offset industrial participation
- **distinct_from:** theme:aerospace_components_aftermarket — that row supplies parts and aftermarket across programs (incl. commercial); this row owns the prime platform program itself; theme:rotorcraft_vertical_lift — that row is the rotary/vertical-lift platform family with its own certification basis and industrial base; this row is the fixed-wing/trainer/transport program base
- **exclusions:** rotorcraft are folded in by domain; commercial airframes; munitions and engines (separate rows); unmanned combat aircraft (counter-UAS row)
- **china_relevance:** high — 军用飞机 (战机/军机) programs are the largest 国防装备 line in A-share 军工 disclosures
- **confidence:** high
- **sources:** IISS, The Military Balance (air forces chapters); GAO Weapons Systems Annual Assessments; Defence Data portal — European Defence Agency (EDA)

### theme:ground_combat_systems — Ground combat systems & artillery
- **name_en:** Ground combat systems & artillery · **name_zh:** 陆战装备与火炮
- **value_chain_position:** midstream
- **parent_sub_theme:** theme:defense_platform_programs
- **defining_activities:** produce tanks, infantry fighting vehicles and artillery systems; integrate fire-control and protection subsystems; deliver ammunition-handling and sustainment interfaces; upgrade legacy fleets; supply armored-vehicle fleets to allied armies
- **distinct_from:** theme:naval_shipbuilding (hull-domain industrial base) and theme:military_aircraft_platforms (air domain) — this row is the land-domain platform base
- **exclusions:** small arms beyond vehicle-mounted systems; munitions fills (energetics row); individual soldier equipment; soft-skin logistics trucks
- **china_relevance:** high — 陆战装备 (装甲车辆/火炮) is a distinct 军工 segment in Chinese disclosure vocabulary
- **confidence:** high
- **sources:** IISS, The Military Balance (land forces chapters); SIPRI Arms Transfers and Military Expenditure databases; ground combat vehicle program assessments — US Government Accountability Office (GAO); National Defense Industrial Association division publications — NDIA

### theme:military_aero_engines — Military aero engines
- **name_en:** Military aero engines · **name_zh:** 军用航空发动机
- **value_chain_position:** upstream
- **parent_sub_theme:** theme:defense_platform_programs
- **defining_activities:** develop and produce military turbofan/turboprop engines; manage engine life-cycle parts and overhaul programs; qualify hot-section materials; support engine-fleet readiness
- **distinct_from:** theme:missile_propulsion_supply — that row covers rocket/motor propulsion for expendable munitions; this row covers manned-aircraft turbine propulsion; theme:aerospace_propulsion_engines — that row is the wider military-and-commercial aero-engine industrial base with lifetime aftermarket economics; this row is the military program tier
- **exclusions:** commercial aero engines without military variants; missile motors
- **china_relevance:** high — 航空发动机 (两机专项) is a named national program and A-share 军工 supply-chain segment
- **confidence:** high
- **sources:** GAO military aviation engine program assessments; IISS, The Military Balance

### theme:air_missile_defense_systems — Integrated air & missile defense
- **name_en:** Integrated air & missile defense · **name_zh:** 防空反导系统
- **value_chain_position:** midstream
- **parent_sub_theme:** theme:defense_platform_programs
- **defining_activities:** integrate radars, fire control and interceptors into layered defense systems; deliver engagement and command software; test system-of-systems intercepts; couple sensor and effector networks; field sensor-to-shooter layers including counter-rocket/artillery/mortar (C-RAM) classes
- **distinct_from:** theme:missiles_munitions_effects — that row covers the munition's output economics; this row covers the integrated defensive system (sensors + fire control + interceptors as one system)
- **exclusions:** handheld MANPADS as munitions; space-based interceptor research; space-based missile tracking (→ space theme)
- **china_relevance:** high — 防空反导 (红旗/陆基中段类) is standard 军工 trade-press vocabulary
- **confidence:** high
- **sources:** CSIS Missile Threat project (system profiles); IISS, The Military Balance (air-defence inventories); Integrated Air and Missile Defence policy documents — NATO

### theme:hypersonic_strike_vehicles — Hypersonic strike vehicles & thermal protection
- **name_en:** Hypersonic strike vehicles & thermal protection · **name_zh:** 高超声速飞行器与热防护
- **value_chain_position:** midstream
- **parent_sub_theme:** theme:strike_munitions_chain
- **defining_activities:** develop glide and air-breathing Mach-5+ vehicles; qualify thermal-protection materials; build flight-test and range instrumentation chains; integrate with boost and release platforms
- **distinct_from:** theme:missiles_munitions_effects (conventional munitions economics) — a distinct vehicle class with its own materials, propulsion coupling and test chain
- **exclusions:** ballistic missiles of legacy classes; space-launch vehicles
- **china_relevance:** high — 高超声速 is a core 国防科技 frontier term in Chinese trade press and journals
- **confidence:** medium
- **sources:** GAO hypersonic weapons assessments; RAND Corporation hypersonic-report series

### theme:energetics_explosives_supply — Energetics & explosives supply
- **name_en:** Energetics & explosives supply · **name_zh:** 含能材料与炸药供应链
- **value_chain_position:** upstream
- **parent_sub_theme:** theme:strike_munitions_chain
- **defining_activities:** produce propellant grains and rocket-motor ingredients; manufacture explosive fills and pyrotechnics; scale energetics production capacity; qualify insensitive-munition chemistries
- **distinct_from:** theme:missile_propulsion_supply — that row names the propulsion-assembly bottleneck; this row is the chemical feedstock tier feeding ALL munitions (fills, propellants, pyros)
- **exclusions:** commercial mining explosives; fuel logistics
- **china_relevance:** high — 含能材料 is a distinct 军工新材料 segment in Chinese disclosure and academic vocabulary
- **confidence:** medium
- **sources:** National Academies report on Advanced Energetic Materials; NDIA armaments/energetics industrial-base working-group papers; UN International Ammunition Technical Guidelines (IATG) — United Nations; conventional munitions industrial-base assessments — US Government Accountability Office (GAO)

### theme:seekers_guidance_components — Seekers & guidance components
- **name_en:** Seekers & guidance components · **name_zh:** 导引头与制导部件
- **value_chain_position:** upstream
- **parent_sub_theme:** theme:strike_munitions_chain
- **defining_activities:** produce imaging/RF seekers and guidance sections; manufacture fuzes and guidance electronics; precision-align inertial measurement units; qualify components across munition families
- **distinct_from:** theme:missiles_munitions_effects — that row covers whole-munition replenishment; this row is the precision-guidance component layer inside the munition
- **exclusions:** complete missile assembly; aircraft mission computers (sensors row)
- **china_relevance:** high — 导引头与精确制导 is standard 导弹产业链 vocabulary in Chinese trade press
- **confidence:** medium
- **sources:** GAO guided-munitions industrial-base assessments; CSIS Missile Threat project

### theme:defense_microelectronics — Defense-grade microelectronics
- **name_en:** Defense-grade microelectronics · **name_zh:** 军用微电子元器件
- **value_chain_position:** upstream
- **parent_sub_theme:** theme:defense_technology_readiness
- **defining_activities:** produce radiation-hardened and militarized semiconductors; run accredited/trusted fabrication and assembly; assure microelectronics supply integrity; qualify components for extreme environments; package defense-grade chiplets and power electronics
- **distinct_from:** theme:defense_sensors_electronics_c2 — that row integrates mission electronics into systems; this row supplies the trusted upstream silicon and components beneath them
- **exclusions:** merchant AI accelerators (ai_semiconductors theme); COTS boards without military qualification; generic EDA software
- **china_relevance:** high — 军工电子/元器件自主可控 is a standing A-share 军工 supply-chain segment
- **confidence:** high
- **sources:** DMEA Trusted Accreditation (formerly Trusted Foundry) program documents; GAO/DoD microelectronics assurance reports; semiconductor and defense technology studies — Center for Strategic and International Studies (CSIS)

### theme:defense_photonics_eo_ir — Defense photonics & EO/IR systems
- **name_en:** Defense photonics & EO/IR systems · **name_zh:** 国防光电与红外系统
- **value_chain_position:** upstream
- **parent_sub_theme:** theme:defense_technology_readiness
- **defining_activities:** produce cooled/uncooled infrared focal planes; build precision optics, gimbals and laser systems; manufacture night-vision and image-intensifier tubes; integrate EO payloads for platforms
- **distinct_from:** theme:defense_sensors_electronics_c2 — that row covers radar, EW and C2 electronics; this row is the photonics/imaging component chain beneath sensor systems
- **exclusions:** radar hardware; directed-energy weapon integration (kept at prose level here)
- **china_relevance:** high — 国防光电 (红外焦平面/激光) is a distinct 军工 segment in Chinese disclosures
- **confidence:** medium
- **sources:** SPIE defense and security proceedings (optical/photonics sensing); IISS, The Military Balance (sensor inventories)

### theme:defense_training_simulation — Defense training & simulation
- **name_en:** Defense training & simulation · **name_zh:** 军事模拟训练与靶场
- **value_chain_position:** enabler
- **parent_sub_theme:** theme:defense_technology_readiness
- **defining_activities:** build flight/tactical simulators and part-task trainers; operate live-virtual-constructive ranges; deliver mission-rehearsal content and after-action tooling; interoperate via simulation standards
- **distinct_from:** every hardware row — this row supplies readiness capability and training content, not combat equipment; theme:defense_test_evaluation_infrastructure — that row qualifies new systems before fielding; this row rehearses with fielded ones
- **exclusions:** academic instruction; entertainment simulation; commercial flight-school simulators for airlines
- **china_relevance:** medium — 实战化训练/模拟蓝军 appears in PLA-modernization trade coverage; civilian exposure is thinner
- **confidence:** medium
- **sources:** NATO Modelling and Simulation Group standards (STANAG-class interoperability); NTSA/NDIA training & simulation (I/ITSEC) industry programs; training-range program reviews — US Government Accountability Office (GAO)

### theme:defense_digital_it_services — Defense digital & IT modernization
- **name_en:** Defense digital & IT modernization · **name_zh:** 国防信息化与数字服务
- **value_chain_position:** enabler
- **parent_sub_theme:** theme:defense_technology_readiness
- **defining_activities:** modernize defense ministries' enterprise networks and clouds; stand up software factories and DevSec pipelines; migrate classified workloads; deliver command-staff digital workflows
- **distinct_from:** theme:defense_sensors_electronics_c2 — that row is mission electronics for weapon systems; this row is institutional digital transformation of the defense enterprise
- **exclusions:** weapons-embedded software (platform rows); national CERT operations (cyber national row)
- **china_relevance:** high — 国防信息化/军队信息化 is an explicit modernization line in Chinese defense white papers
- **confidence:** medium
- **sources:** US DoD Software Modernization Strategy (2022); 中国《新时代的中国国防》白皮书 (信息化建设章节)

### theme:defense_sustainment_mro — Defense sustainment & MRO
- **name_en:** Defense sustainment & MRO · **name_zh:** 装备维修与保障服务
- **value_chain_position:** downstream
- **parent_sub_theme:** theme:defense_technology_readiness
- **defining_activities:** run depot-level maintenance and overhauls; deliver reliability upgrades mid-life; manage readiness-focused spares and engineering support; modernize legacy fleets in service; operate supply-chain, inventory and readiness engineering for fielded fleets; deliver contested-logistics planning tools
- **distinct_from:** theme:aerospace_components_aftermarket — that row is the parts/commercial-MRO layer; this row is the military program sustainment service layer around readiness
- **exclusions:** commercial airline MRO; new-build platform delivery; commercial 3PL freight; military construction (facilities)
- **china_relevance:** medium — 装备维修保障 appears in 军工 service segments; most exposure remains state-yard based
- **confidence:** medium
- **sources:** GAO weapon-system sustainment and depot-maintenance reports; Aviation Week MRO trade-press coverage (military fleets); Defense Logistics Agency strategy documentation — US Department of Defense; NATO logistics handbooks — NATO

### theme:cbrn_defense_equipment — CBRN defense equipment
- **name_en:** CBRN defense equipment · **name_zh:** 核生化防护装备
- **value_chain_position:** midstream
- **parent_sub_theme:** theme:defense_technology_readiness
- **defining_activities:** produce detection and identification systems for chemical/biological/radiological agents; manufacture personal protective equipment; build decontamination systems; certify against treaty-relevant standards
- **distinct_from:** every existing row — a protection-equipment segment adjacent to munitions policy but absent from platform, munitions and sensor rows
- **exclusions:** civil-health pandemic PPE without CBRN qualification; demolition/explosive ordnance disposal
- **china_relevance:** medium — 核生化防护 (三防) appears in 军工 and 应急管理 vocabulary; listed exposure is limited
- **confidence:** medium
- **sources:** OPCW industry verification and declaration regime materials; NATO Joint CBRN Defence Centre of Excellence publications


**Union grafts (variant A rows re-parented onto this spine — see `## Union ledger`):**

### theme:rotorcraft_vertical_lift
- **name_en:** Rotorcraft & vertical-lift platforms
- **name_zh:** 直升机与旋翼机平台
- **value_chain_position:** downstream
- **parent_sub_theme:** theme:defense_platform_programs
- **defining_activities:** design and build military/utility helicopters and tiltrotor fleets; sustain aging helicopter fleets and avionics upgrades; develop civil-certified vertical-lift airframes.
- **distinct_from:** `theme:military_aircraft_platforms` — separate platform family with a distinct certification basis and industrial base; distinct from `theme:aerospace_propulsion_engines` (the engine tier beneath it).
- **exclusions:** fixed-wing GA (→ `theme:business_general_aviation`); uncrewed rotorcraft (→ `theme:autonomous_systems_counter_uas`).
- **china_relevance:** high — domestic helicopter industrialization programs and low-altitude-economy policy expand both military and civil demand.
- **confidence:** high
- **sources:** The Military Balance — IISS; Vertipedia technical resource — Vertical Flight Society; FAA Aerospace Forecast — US Federal Aviation Administration.

### theme:undersea_systems_sonar
- **name_en:** Undersea warfare & sonar systems
- **name_zh:** 水下战系统
- **value_chain_position:** midstream
- **parent_sub_theme:** theme:defense_platform_programs
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
- **parent_sub_theme:** theme:defense_technology_readiness
- **defining_activities:** design, certify and manufacture military and commercial gas-turbine engines; sell decades of spare parts and overhaul; develop next-gen propulsion (adaptive-cycle, sustainable-fuel).
- **distinct_from:** `theme:missile_propulsion_supply` — expendable solid-rocket motor output vs long-life turbine engines with aftermarket; distinct from `theme:aerospace_components_aftermarket` (engines are the propulsion tier, not generic parts); distinct from theme:military_aero_engines (the military program tier vs this military-and-commercial industrial base)
- **exclusions:** rocket propulsion (→ `theme:launch_vehicle_propulsion`); APUs as cabin systems.
- **china_relevance:** high — 两机专项 (aero-engine & gas-turbine national program) makes engine indigenization a flagship national effort.
- **confidence:** high
- **sources:** The Military Balance — IISS; military engine sustainment reports — US Government Accountability Office (GAO); AIAA technical committee publications — American Institute of Aeronautics and Astronautics (AIAA).

### theme:aerospace_structures_composites
- **name_en:** Airframe structures & composites
- **name_zh:** 航空结构与复合材料
- **value_chain_position:** upstream
- **parent_sub_theme:** theme:defense_technology_readiness
- **defining_activities:** fabricate fuselage, wing and empennage subassemblies; produce advanced composite aerostructures and honeycomb; supply structures for both defense and civil platforms.
- **distinct_from:** `theme:aerospace_components_aftermarket` — new-build structures vs parts distribution/used material; distinct from `theme:aerospace_propulsion_engines` (structural airframe vs propulsion).
- **exclusions:** aircraft interior cabin products; raw carbon fiber without aero qualification.
- **china_relevance:** high — domestic aerostructure ramp for homegrown airliner and fighter programs builds composite capacity.
- **confidence:** high
- **sources:** Composite Materials Handbook (CMH-17) — SAE International with US FAA; National Center for Advanced Materials Performance (NCAMP) program — FAA; Aerospace Standards program — Aerospace Industries Association (AIA).

### theme:defense_test_evaluation_infrastructure
- **name_en:** Test, evaluation & range infrastructure
- **name_zh:** 试验鉴定与靶场设施
- **value_chain_position:** enabler
- **parent_sub_theme:** theme:defense_technology_readiness
- **defining_activities:** operate proving grounds and open-air ranges; instrument flight test and telemetry collection; deliver independent T&E qualification services before fielding.
- **distinct_from:** `theme:defense_training_simulation` — qualifying new systems vs rehearsing with fielded ones; distinct from platform rows.
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
- **distinct_from:** `theme:defense_sensors_electronics_c2` — civil airspace infrastructure vs military C2; distinct from `theme:military_aircraft_platforms` (airspace systems vs aircraft).
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

---

## theme:robotics_automation — Robotics & Automation

Existing micros (unchanged): `theme:machine_vision`, `theme:industrial_motion_controls`, `theme:collaborative_robot_arms`, `theme:industrial_robot_arms`, `theme:precision_actuators_servo_motors`, `theme:surgical_robotics_systems`, plus sub_theme `theme:robot_arm_systems`. The existing rows center on factory arms and their control/perception layers. The new rows push along the chain into components (transmission, tooling, contact sensing), emerging form factors (humanoids, service, rehab, civil UAS), application systems (intralogistics, warehouse, agriculture, construction, integration), and the software/operations layer (simulation, MES, RaaS).

**Sub-theme grouping.** `theme:robot_core_components` (upstream transmission/tooling/sensing bottlenecks), `theme:emerging_robot_form_factors` (new machine classes beyond the fixed arm), `theme:automation_application_systems` (engineered systems and vertical deployments), `theme:automation_software_operations` (the digital and service layer that monetizes automation).

**Theme-tier candidates (prose only).** (1) Humanoid/embodied AI machines may merit a standalone theme (industrials_defense or technology_software parent) as commercialization scales. (2) A "low-altitude economy" theme candidate is plausible for China-scoped taxonomies if civil-UAS infrastructure becomes a listed spend pool distinct from robotics.

### theme:precision_reducers_gearboxes — Precision reducers & gearboxes
- **name_en:** Precision reducers & gearboxes · **name_zh:** 精密减速器
- **value_chain_position:** upstream
- **parent_sub_theme:** theme:robot_core_components
- **defining_activities:** manufacture harmonic and RV cycloidal precision reducers; grind gear tooth profiles to arc-minute accuracy; scale transmission capacity for multi-joint programs; qualify backlash and life ratings
- **distinct_from:** theme:precision_actuators_servo_motors — that row is the torque-generating actuator; this row is the speed-reducing transmission between servo and joint
- **exclusions:** general industrial gearboxes without precision ratings; actuator motor windings
- **china_relevance:** high — 减速器 (谐波/RV) is the canonical 机器人核心零部件 localization segment in A-share disclosures
- **confidence:** high
- **sources:** IFR World Robotics (industrial robot structure/technology sections); 中国机器人产业联盟 (CRIA) component statistics; 日本机器人工业会 (JARL) component data

### theme:end_effectors_grippers — End effectors & grippers
- **name_en:** End effectors & grippers · **name_zh:** 末端执行器与灵巧手
- **value_chain_position:** upstream
- **parent_sub_theme:** theme:robot_core_components
- **defining_activities:** manufacture electric/pneumatic grippers and quick-change tooling; build dexterous multi-finger hands; engineer application tools (welding torches, sprayers); integrate tooling with arm controllers; supply compliant fixtures and application tooling
- **distinct_from:** theme:robot_arm_systems — that row is the finished arm; this row is the distal tooling layer that converts arm motion into manipulation
- **exclusions:** complete arms; machine-vision cameras (vision row)
- **china_relevance:** high — 末端执行器/灵巧手 is the focus of 人形机器人 dexterity roadmaps (工信部指导意见)
- **confidence:** medium
- **sources:** IFR World Robotics; A3 (Association for Advancing Automation) robot-component resources; ISO 9409 (mechanical interface) series — ISO; ICRA proceedings on manipulation and grasping — IEEE Robotics and Automation Society

### theme:force_tactile_safety_sensing — Force, tactile & safety sensing
- **name_en:** Force, tactile & safety sensing · **name_zh:** 力觉触觉与安全传感
- **value_chain_position:** upstream
- **parent_sub_theme:** theme:robot_core_components
- **defining_activities:** produce six-axis force/torque sensors and tactile arrays; build safety scanners, light curtains and compliant-control sensing; enable force-limited collaborative operation; calibrate contact-rich skills
- **distinct_from:** theme:machine_vision — that row is camera-based perception; this row is contact and safety sensing that lets machines touch safely
- **exclusions:** lidar for outdoor autonomy; consumer wearables
- **china_relevance:** high — 六维力传感器 is the standard localization bottleneck term in Chinese robotics trade press
- **confidence:** medium
- **sources:** ISO 10218-1/-2 and ISO/TS 15066 (robot and collaborative safety requirements); A3 robot-safety standards resources

### theme:humanoid_embodied_robots — Humanoid & embodied AI robots
- **name_en:** Humanoid & embodied AI robots · **name_zh:** 人形机器人与具身智能
- **value_chain_position:** midstream
- **parent_sub_theme:** theme:emerging_robot_form_factors
- **defining_activities:** develop biped/humanoid whole-body machines; integrate foundation models with embodied control; run dexterous-manipulation and locomotion training; pilot general-purpose tasks outside fixed cells; target manufacturing and logistics pilots before consumer deployment
- **distinct_from:** theme:industrial_robot_arms / theme:collaborative_robot_arms — fixed-base single-task arms; this row is the general-purpose mobile form factor with embodied AI; theme:embodied_ai_robot_learning — that row is the cross-form-factor learned-behavior layer (the brains); this row is the humanoid/general-purpose body (the form factor)
- **exclusions:** prosthetics (rehab row); warehouse AMRs (intralogistics row); entertainment animatronics
- **china_relevance:** high — 人形机器人/具身智能 is codified in MIIT《人形机器人创新发展指导意见》(2023) and provincial industrial plans
- **confidence:** medium
- **sources:** 工信部《人形机器人创新发展指导意见》(2023); IFR World Robotics (humanoid discussions); 中国电子学会《中国机器人产业发展报告》; IEEE Robotics and Automation Society technical communities — IEEE RAS

### theme:professional_service_robots — Professional service robots
- **name_en:** Professional service robots · **name_zh:** 商用服务机器人
- **value_chain_position:** midstream
- **parent_sub_theme:** theme:emerging_robot_form_factors
- **defining_activities:** deploy cleaning, delivery, hospitality and inspection robots; operate public-space navigation fleets; integrate building systems and mission software; service and upgrade installed fleets
- **distinct_from:** theme:amr_agv_intralogistics (factory/warehouse interiors) and arm rows (factory cells) — this row serves buildings, streets and public spaces outside industry
- **exclusions:** surgical robotics (medical_devices dual row); consumer household robots without professional service
- **china_relevance:** high — 商用服务机器人 (配送/清洁/酒店) is a mature Chinese category with volume deployments
- **confidence:** high
- **sources:** IFR Service Robot statistics (professional-service categories); 中国电子学会《中国机器人产业发展报告》

### theme:rehab_exoskeleton_robotics — Rehabilitation robots & exoskeletons
- **name_en:** Rehabilitation robots & exoskeletons · **name_zh:** 康复机器人与外骨骼
- **value_chain_position:** midstream
- **parent_sub_theme:** theme:emerging_robot_form_factors
- **defining_activities:** build gait-training and upper-limb therapy robots; manufacture wearable exoskeletons for mobility and industrial support; deliver therapy-program content; integrate with clinical assessment scales; develop assistive care robotics for aging care
- **distinct_from:** theme:surgical_robotics_systems — that row operates inside patients during procedures; this row assists bodies in recovery and daily mobility
- **exclusions:** prosthetic limbs; hospital logistics robots; telehealth software
- **china_relevance:** high — 康复机器人/外骨骼 appears in MIIT-class equipment guidance and 老龄化 policy demand
- **confidence:** medium
- **sources:** ISO 13482 (personal care robot safety); 工信部等康复辅助器具产业与养老装备 guidance documents; 《关于加快发展康复辅助器具产业的意见》 — 国务院 (State Council)

### theme:civil_uas_low_altitude_economy — Civil UAS & low-altitude economy
- **name_en:** Civil UAS & low-altitude economy · **name_zh:** 民用无人机与低空经济
- **value_chain_position:** midstream
- **parent_sub_theme:** theme:emerging_robot_form_factors
- **defining_activities:** manufacture civilian unmanned aircraft and eVTOL-class platforms; operate logistics, survey, inspection and agricultural-spraying flights; build UTM/traffic-management services; certify airworthiness for low-altitude operations
- **distinct_from:** theme:autonomous_systems_counter_uas (defense_aerospace) — that row is military unmanned/counter-UAS; this row is the civil low-altitude economy
- **exclusions:** military drones; missile-class munitions; passenger airliners
- **china_relevance:** high — 低空经济 is a national growth-engine designation (2024 政府工作报告) under《无人驾驶航空器飞行管理暂行条例》
- **confidence:** high
- **sources:** 国务院/中央军委《无人驾驶航空器飞行管理暂行条例》(2023); FAA 14 CFR Part 107 small-UAS rule (classification vocabulary); 2024年《政府工作报告》低空经济表述

### theme:amr_agv_intralogistics — AMR/AGV intralogistics robots
- **name_en:** AMR/AGV intralogistics robots · **name_zh:** 移动机器人与厂内物流
- **value_chain_position:** midstream
- **parent_sub_theme:** theme:automation_application_systems
- **defining_activities:** build autonomous mobile robots and AGVs; deploy fleet managers and traffic orchestration; integrate with WMS/MES material calls; retrofit brownfield plants without fixed infrastructure; certify mobile platforms for human-shared floors
- **distinct_from:** theme:robot_arm_systems — arms manipulate in place; this row navigates and transports material, with a distinct fleet-software stack
- **exclusions:** outdoor field machines (agriculture row); human-carrying platforms
- **china_relevance:** high — 移动机器人 (AGV/AMR) is a leading Chinese robotics export/segment in GGII and CRIA statistics
- **confidence:** high
- **sources:** IFR World Robotics service-robot statistics; MHI (Material Handling Industry) Annual Industry Report; 高工机器人产业研究所 (GGII) mobile-robot data; ANSI/RIA R15.08 mobile-robot safety standard — A3/ANSI

### theme:warehouse_fulfillment_automation — Warehouse fulfillment automation systems
- **name_en:** Warehouse fulfillment automation systems · **name_zh:** 智能仓储物流自动化
- **value_chain_position:** downstream
- **parent_sub_theme:** theme:automation_application_systems
- **defining_activities:** engineer goods-to-person and AS/RS racking systems; install conveyance and sortation; deploy warehouse execution software; commission whole-facility fulfillment flows; run long-term service and modernization contracts on installed systems
- **distinct_from:** theme:amr_agv_intralogistics — that row supplies mobile-robot units; this row delivers the entire engineered fulfillment system including fixed automation and execution software
- **exclusions:** courier last-mile networks; pure WMS SaaS without physical systems
- **china_relevance:** high — 智能仓储/物流自动化 is named in 中国物流与采购联合会 smart-logistics programs
- **confidence:** high
- **sources:** MHI Annual Industry Report; 中国物流与采购联合会《中国智慧物流发展报告》; warehouse automation market research — Interact Analysis (trade-press analyst)

### theme:agricultural_field_robotics — Agricultural field robotics
- **name_en:** Agricultural field robotics · **name_zh:** 农业机器人与无人农场
- **value_chain_position:** downstream
- **parent_sub_theme:** theme:automation_application_systems
- **defining_activities:** build autonomous tractors and implements; deploy weeding/seeding/harvesting robots; operate GNSS-guided machinery fleets; integrate agronomic data with machine task maps
- **distinct_from:** theme:precision_agriculture_platforms (ag_fertilizer theme) — that row is the agronomic-data platform layer; this row is the field machine executing work
- **exclusions:** drone spraying (civil-UAS row); greenhouse fixed automation
- **china_relevance:** high — 农机装备/无人农场 sits under 农业机械化 national programs (农业农村部)
- **confidence:** medium
- **sources:** FAO, The State of Food and Agriculture 2022: Leveraging automation in agriculture; IFR World Robotics (agriculture robot categories); ISO 11783 (ISOBUS) series — ISO; Future Farming trade-press value-chain coverage

### theme:construction_robotics — Construction robotics & intelligent building
- **name_en:** Construction robotics & intelligent building · **name_zh:** 建筑机器人与智能建造
- **value_chain_position:** downstream
- **parent_sub_theme:** theme:automation_application_systems
- **defining_activities:** deploy layout, rebar, tiling and finishing robots on sites; operate 3D-printed construction systems; automate demolition and hazardous works; couple machines with intelligent-construction BIM workflows
- **distinct_from:** theme:industrial_robot_arms — that row serves factory floors; this row serves building construction sites under intelligent-construction programs
- **exclusions:** mining automation; architectural software without machines
- **china_relevance:** high — 智能建造/建筑机器人 is codified in 住建部 intelligent-construction pilot policy
- **confidence:** medium
- **sources:** 住建部等《关于推动智能建造与建筑工业化协同发展的指导意见》(2020); IFR World Robotics (construction categories)

### theme:robot_system_integration — Automation system integration
- **name_en:** Automation system integration · **name_zh:** 自动化系统集成
- **value_chain_position:** downstream
- **parent_sub_theme:** theme:automation_application_systems
- **defining_activities:** design turnkey cells and automated lines; integrate robots, conveyance and controls; commission and validate cycle times; maintain and retool lines across model changes
- **distinct_from:** every hardware row — those supply units; this row designs, integrates and commissions the complete automated system around them
- **exclusions:** pure software integrators; general electrical contractors without automation scope; robot rental platforms
- **china_relevance:** high — 系统集成 (集成商) is the standard Chinese robotics-chain tier in GGII/CRIA industry maps
- **confidence:** high
- **sources:** IFR integrator-member industry structure; A3 integrator membership programs; Robotik + Automation sector statistics — VDMA (German Mechanical Engineering Industry Association)

### theme:robot_simulation_digital_twin — Robot simulation & digital twin
- **name_en:** Robot simulation & digital twin · **name_zh:** 机器人仿真与数字孪生
- **value_chain_position:** enabler
- **parent_sub_theme:** theme:automation_software_operations
- **defining_activities:** build offline robot programming tools; run virtual commissioning before line builds; maintain manufacturing digital twins; validate cycle-time and safety envelopes digitally
- **distinct_from:** theme:mes_manufacturing_software — that row executes production; this row simulates and validates it digitally before and during operation
- **exclusions:** game-engine tooling without industrial use; CAD design suites
- **china_relevance:** high — 数字孪生 is a CAICT white-paper series and 工信部 industrial-internet capability line
- **confidence:** medium
- **sources:** ISO 23247 digital-twin framework for manufacturing; 中国信息通信研究院《数字孪生白皮书》; Manufacturing digital-twin and CPS foundational publications — NIST; Gazebo simulation ecosystem — Open Robotics

### theme:mes_manufacturing_software — MES & manufacturing software
- **name_en:** MES & manufacturing software · **name_zh:** 制造执行系统与工业软件
- **value_chain_position:** enabler
- **parent_sub_theme:** theme:automation_software_operations
- **defining_activities:** deploy manufacturing execution and MOM systems; orchestrate orders, quality and traceability; integrate SCADA/historian data upward to ERP; manage recipes, genealogy and compliance records
- **distinct_from:** theme:industrial_motion_controls — that row controls machines in real time; this row orchestrates the factory above the machines
- **exclusions:** CAD/PLM authoring; finance ERP modules
- **china_relevance:** high — 工业软件 (MES/MOM) is an explicit localization priority in MIIT software-industry plans
- **confidence:** high
- **sources:** ISA-95 / IEC 62264 enterprise-control system integration standard; 工信部《"十四五"软件和信息技术服务业发展规划》

### theme:raas_fleet_operations — Robotics-as-a-service & fleet operations
- **name_en:** Robotics-as-a-service & fleet operations · **name_zh:** 机器人即服务与远程运维
- **value_chain_position:** downstream
- **parent_sub_theme:** theme:automation_software_operations
- **defining_activities:** sell robot outcomes on subscription contracts; operate remote teleoperation and fleet-monitoring centers; bundle maintenance, spares and uptime SLAs; redeploy fleets across customers
- **distinct_from:** every hardware row — those sell units; this row sells operated availability, a business-model mechanism rather than a machine
- **exclusions:** leasing without operations; pure maintenance contracting
- **china_relevance:** medium — "机器人+"应用行动 encourages service-model innovation; RaaS accounting is nascent in Chinese disclosures
- **confidence:** medium
- **sources:** 工信部等17部门《"机器人+"应用行动实施方案》(2023); IFR World Robotics (service-model discussions)


**Union grafts (variant A rows re-parented onto this spine — see `## Union ledger`):**

### theme:laboratory_automation_robots
- **name_en:** Laboratory automation robotics
- **name_zh:** 实验室自动化
- **value_chain_position:** midstream
- **parent_sub_theme:** theme:automation_application_systems
- **defining_activities:** build liquid-handling and plate-handling workstations; automate sample prep and assay workflows; integrate lab robots with LIMS/execution software.
- **distinct_from:** `theme:life_science_lab_instruments` (existing, under diagnostics_lifesci) — robotic workflow systems vs single-function analytical instruments; distinct from arm rows (bench-scale motion with consumable economics).
- **exclusions:** sequencers and analytical instruments themselves; software-only scheduling.
- **china_relevance:** medium — biotech/pharma lab automation demand grows with domestic biologics capacity; most core tooling still imported.
- **confidence:** medium
- **sources:** SLAS laboratory automation standards and conference program — Society for Laboratory Automation and Screening (SLAS); ANSI/SLAS microplate and footprint standards — ANSI/SLAS; World Robotics — IFR.

### theme:semiconductor_factory_automation
- **name_en:** Semiconductor factory automation
- **name_zh:** 半导体工厂自动化
- **value_chain_position:** downstream
- **parent_sub_theme:** theme:automation_application_systems
- **defining_activities:** build automated material handling systems (AMHS) for fabs; supply cleanroom wafer-handling robots and load ports; integrate fab scheduling/dispatch software with tools.
- **distinct_from:** `theme:wafer_fab_subsystems` (existing, under semicap_equipment) — fab logistics automation vs the process-tool subsystem layer; distinct from `theme:warehouse_fulfillment_automation` (cleanroom vertical vs general warehousing).
- **exclusions:** litho/etch process tools themselves; front-opening unified pod (FOUP) plastics.
- **china_relevance:** high — domestic fab buildout across the industry ramp pulls AMHS localization; segment demand is capacity-driven, not vendor-specific.
- **confidence:** high
- **sources:** SEMI E84/E87 and related automation interface standards — SEMI; World Robotics (electronics industry chapters) — IFR; 《中国机器人产业发展报告》 — 中国电子学会.

### theme:robot_software_middleware
- **name_en:** Robot operating systems & middleware
- **name_zh:** 机器人操作系统与中间件
- **value_chain_position:** enabler
- **parent_sub_theme:** theme:automation_software_operations
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
- **parent_sub_theme:** theme:automation_software_operations
- **defining_activities:** train manipulation/navigation policies from demonstration data; adapt vision-language-action foundation models to robot tasks; deploy learned skills on production robots.
- **distinct_from:** `theme:machine_vision` — perception sensing vs task-learning policies that act on perception; distinct from `theme:robot_software_middleware` (framework plumbing vs learned behavior); distinct from theme:humanoid_embodied_robots (the general-purpose body form factor vs the learned-behavior layer)
- **exclusions:** generic LLM chat products; warehouse optimization analytics without robot control.
- **china_relevance:** high — 具身智能 is a named frontier in national AI/robot planning documents and university-industrial programs.
- **confidence:** high
- **sources:** Open X-Embodiment / RT-X robotics datasets and papers — cross-institution academic collaboration (arXiv, 2023); ICRA/IROS proceedings — IEEE Robotics and Automation Society; 《机器人产业发展报告》 — 中国电子学会 (Chinese Institute of Electronics).

### theme:industrial_iot_condition_monitoring
- **name_en:** Industrial IoT & condition monitoring
- **name_zh:** 工业互联网与状态监测
- **value_chain_position:** enabler
- **parent_sub_theme:** theme:automation_software_operations
- **defining_activities:** deploy plant-wide vibration/temperature sensing networks; stream machine health telemetry to cloud analytics; run predictive-maintenance and OEE platforms.
- **distinct_from:** `theme:industrial_motion_controls` — plant data plane vs machine control loops; distinct from `theme:robot_simulation_digital_twin` (live production telemetry vs pre-deployment synthetic models).
- **exclusions:** building-management systems; consumer wearables.
- **china_relevance:** high — 工业互联网 is a national strategy with MIIT action plans and identified 5G+industrial-internet parks.
- **confidence:** high
- **sources:** OPC UA specification — OPC Foundation; RAMI 4.0 reference architecture — Plattform Industrie 4.0 (German Federal Ministry for Economic Affairs and Climate Action); 《工业互联网创新发展行动计划》 — 工业和信息化部 (MIIT).

---

## theme:space_satellite — Space & Satellites

Existing micros (unchanged): `theme:launch_services`, `theme:satellite_broadband_services`, `theme:direct_to_device_connectivity`, `theme:earth_observation`, `theme:satellite_ground_terminals`, `theme:military_space_communications`, plus sub_theme `theme:satellite_connectivity_services`. Existing rows skew to services and access; the new rows add the industrial base (satellites, components, propulsion), in-space operations (SSA, servicing, ground networks, insurance), the data value chain (PNT, analytics, IoT), and exploration (human spaceflight, lunar/deep space).

**Sub-theme grouping.** `theme:space_industrial_base` (upstream manufacturing), `theme:space_operations_services` (in-space and ground operations plus risk transfer), `theme:space_data_value_chain` (downstream data products), `theme:space_exploration_programs` (beyond-Earth-orbit missions).

**Theme-tier candidates (prose only).** (1) `theme:space_satellite` currently sits under industrials_defense; a dedicated "space economy" macro_category candidate (splitting commercial space from defense) is flagged for the seat. (2) The space data chain could alternatively group under technology_software if the seat prefers data-centric adjacency.

### theme:satellite_manufacturing_constellations — Satellite manufacturing & constellation production
- **name_en:** Satellite manufacturing & constellation production · **name_zh:** 卫星整星研制与批产
- **value_chain_position:** midstream
- **parent_sub_theme:** theme:space_industrial_base
- **defining_activities:** design and integrate complete satellite buses and payloads; run high-rate constellation assembly lines; perform environmental qualification testing; deliver AIT (assembly, integration, test) services; deliver complete satellites to government and science customers
- **distinct_from:** theme:launch_services — that row provides orbit access; this row builds the spacecraft. Distinct from V1-rejected `leo_constellation_deployment` (a build-out driver, not a segment): the mechanism here is manufacturing
- **exclusions:** launch vehicles; ground user terminals
- **china_relevance:** high — 卫星研制/星座批产 is standard 商业航天 vocabulary (上海"垣信-class" G60 星链 plan coverage)
- **confidence:** high
- **sources:** Satellite Industry Association, State of the Satellite Industry Report; OECD, The Space Economy in Figures; satellites-built-and-launched outlook research — Euroconsult/Novaspace; 《中国的航天》白皮书 — 国务院新闻办公室 (SCIO)

### theme:satellite_components_payloads — Satellite components & payloads
- **name_en:** Satellite components & payloads · **name_zh:** 卫星部组件与载荷
- **value_chain_position:** upstream
- **parent_sub_theme:** theme:space_industrial_base
- **defining_activities:** produce transponders and communication payloads; manufacture solar arrays, batteries and deployables; build reaction wheels, gimbals and star trackers; supply TT&C electronics and space-qualified parts; supply space-qualified (rad-tolerant) electronics and harnesses
- **distinct_from:** theme:satellite_manufacturing_constellations — that row integrates the whole satellite; this row is the component/payload tier beneath it
- **exclusions:** launch-vehicle engines (propulsion row); user-terminal chips; ground antenna RF front-ends
- **china_relevance:** high — 卫星部组件/有效载荷 is the standard 商业航天产业链 upstream tier in Chinese trade maps
- **confidence:** high
- **sources:** ECSS (European Cooperation for Space Standardization) engineering standards; OECD, The Space Economy in Figures; EEE-INST-002 instructions for EEE parts — NASA; State-of-the-Art Small Spacecraft Technology report — NASA

### theme:spacecraft_propulsion_systems — Spacecraft propulsion & electric thrusters
- **name_en:** Spacecraft propulsion & electric thrusters · **name_zh:** 空间推进与电推进
- **value_chain_position:** upstream
- **parent_sub_theme:** theme:space_industrial_base
- **defining_activities:** manufacture Hall-effect and ion electric thrusters; build chemical thrusters for orbit-raising and station-keeping; qualify propulsion chains for constellation maintenance; integrate propellant management
- **distinct_from:** theme:launch_services — launch vehicles reach orbit; this row moves and maintains the spacecraft once there; theme:launch_vehicle_propulsion — that row builds launch-vehicle propulsion hardware sold to vehicle programs; this row moves and maintains spacecraft in orbit
- **exclusions:** launch-vehicle first stages; missile propulsion (defense theme)
- **china_relevance:** high — 电推进 is a standing 航天科技 frontier term in Chinese aerospace trade press
- **confidence:** medium
- **sources:** ESA electric-propulsion programme documentation; AIAA Electric Propulsion Technical Committee resources

### theme:space_situational_awareness_debris — Space situational awareness & debris tracking
- **name_en:** Space situational awareness & debris tracking · **name_zh:** 空间态势感知与碎片监测
- **value_chain_position:** midstream
- **parent_sub_theme:** theme:space_operations_services
- **defining_activities:** track orbital objects and maintain catalogs; screen conjunctions and issue collision warnings; monitor debris-generating events; provide space-traffic data services; deliver space-weather and debris-environment services
- **distinct_from:** theme:earth_observation — that row images Earth; this row observes the orbital environment itself for flight safety
- **exclusions:** kinetic debris removal (servicing row); radio-frequency spectrum filing
- **china_relevance:** medium — 空间碎片监测 is a national CNSA capability line; listed exposure is thin
- **confidence:** medium
- **sources:** ESA Space Debris Office Annual Space Environment Report; IADC Space Debris Mitigation Guidelines; UNOOSA Long-Term Sustainability guidelines; Space-Track catalogue services — 18th Space Defense Squadron, US Space Force

### theme:in_orbit_servicing_removal — In-orbit servicing & life extension
- **name_en:** In-orbit servicing & life extension · **name_zh:** 在轨服务与延寿
- **value_chain_position:** midstream
- **parent_sub_theme:** theme:space_operations_services
- **defining_activities:** rendezvous and dock with client spacecraft; refuel, repair and upgrade satellites in orbit; deorbit end-of-life assets; execute debris-removal missions under license; reposition satellites on station
- **distinct_from:** theme:space_situational_awareness_debris — that row watches the environment; this row physically operates on spacecraft in orbit
- **exclusions:** crewed servicing (exploration row); launch and deployment
- **china_relevance:** medium — 在轨服务/在轨维修 appears in 商业航天 planning; missions remain early
- **confidence:** medium
- **sources:** NASA On-orbit Servicing, Assembly, and Manufacturing (OSAM) program documents; ESA ClearSpace-1 debris-removal mission materials; Mitigation of Orbital Debris rules including the five-year deorbit requirement — US Federal Communications Commission (FCC); Space Debris Mitigation Guidelines — Inter-Agency Space Debris Coordination Committee (IADC)

### theme:dedicated_small_launch_vehicles — Dedicated small launch vehicles
- **name_en:** Dedicated small launch vehicles · **name_zh:** 小型商业运载火箭
- **value_chain_position:** midstream
- **parent_sub_theme:** theme:space_operations_services
- **defining_activities:** build and operate small-lift launch vehicles; offer dedicated single-customer orbits on responsive schedules; run mobile/coastal launch operations; serve rideshare-complement and rapid-replacement demand
- **distinct_from:** theme:launch_services — that row is the whole orbit-access layer (reusable-heavy economics); this row is the dedicated small-vehicle responsiveness segment with a distinct vehicle class and price point
- **exclusions:** heavy-lift reusable vehicles; suborbital tourism
- **china_relevance:** high — 商业小运载 (朱雀/快舟-class vocabulary) is a flagship 商业航天 segment in Chinese trade press
- **confidence:** medium
- **sources:** FAA Office of Commercial Space Transportation annual launch reports; 2024年《政府工作报告》与中央经济工作会议 商业航天战略性新兴产业表述

### theme:ground_station_networks_ttoc — Ground station networks & TT&C-as-a-service
- **name_en:** Ground station networks & TT&C-as-a-service · **name_zh:** 地面站网与测运控服务
- **value_chain_position:** midstream
- **parent_sub_theme:** theme:space_operations_services
- **defining_activities:** operate global antenna gateway networks; deliver TT&C and orbit-control services per satellite; schedule pass contacts and downlink capacity; manage ITU-class frequency coordination support; route and preprocess satellite data for operators
- **distinct_from:** theme:satellite_ground_terminals — that row sells end-user terminals; this row runs the operator ground segment the constellation talks to
- **exclusions:** consumer dishes; broadcaster uplinks; broadcast uplinks for TV networks
- **china_relevance:** high — 测运控/地面站网 is the standard Chinese constellation infrastructure term
- **confidence:** medium
- **sources:** ITU Radio Regulations (space services frameworks); ESA Estrack ground-station network documentation; CCSDS recommendations — Consultative Committee for Space Data Systems (CCSDS); ground segment and operations documentation — European Space Operations Centre (ESA/ESOC); industry reports — Global Satellite Operators Association (GSOA)

### theme:space_insurance_underwriting — Space insurance & launch risk
- **name_en:** Space insurance & launch risk · **name_zh:** 航天保险
- **value_chain_position:** downstream
- **parent_sub_theme:** theme:space_operations_services
- **defining_activities:** underwrite launch and in-orbit phase policies; model failure probabilities by vehicle and orbit; handle third-party liability requirements; price constellation self-insurance alternatives
- **distinct_from:** every existing space row — none prices risk; this row is the risk-transfer financing mechanism of the chain (cf. cyber insurance in cybersecurity)
- **exclusions:** aviation insurance without space exposure; government indemnification programs themselves
- **china_relevance:** medium — 航天保险 is an established Chinese market line tied to 发射责任险 requirements
- **confidence:** medium
- **sources:** OECD, The Space Economy in Figures (insurance chapters); International Union of Aerospace Insurers (IUAI) materials

### theme:gnss_pnt_services — GNSS navigation & PNT services
- **name_en:** GNSS navigation & PNT services · **name_zh:** 卫星导航与位置服务
- **value_chain_position:** downstream
- **parent_sub_theme:** theme:space_data_value_chain
- **defining_activities:** operate navigation satellite services and augmentations; deliver precise-point-positioning corrections; provide resilient timing distribution; build positioning chip-modules into vertical applications; produce GNSS chipsets, modules and antennas; develop resilient alternative-PNT (terrestrial/LEO) systems
- **distinct_from:** communication rows (broadband/D2D/IoT move bits) and theme:earth_observation (images) — this row's product is location and time reference itself
- **exclusions:** EO imaging; cellular positioning without satellite augmentation; inertial navigation as standalone avionics
- **china_relevance:** high — 北斗卫星导航与位置服务 is a named national industry (中国卫星导航系统管理办公室 white papers)
- **confidence:** high
- **sources:** 国务院新闻办公室《新时代的中国北斗》白皮书 (2022); ICAO Annex 10 GNSS provisions; GNSS Market Report — EU Agency for the Space Programme (EUSPA); National PNT Advisory Board reports — US Department of Transportation; RTCM standards — Radio Technical Commission for Maritime Services

### theme:geospatial_analytics_platforms — Geospatial analytics & EO downstream
- **name_en:** Geospatial analytics & EO downstream · **name_zh:** 地理空间数据分析应用
- **value_chain_position:** downstream
- **parent_sub_theme:** theme:space_data_value_chain
- **defining_activities:** turn EO imagery and sensor data into analytics products; operate geospatial platforms and APIs; fuse satellite data with other sources for sector insight; deliver change-monitoring subscriptions; deliver mapping, InSAR and 3D-baseline products
- **distinct_from:** theme:earth_observation — that row owns imaging/sensing from orbit; this row is the downstream data-application tier that consumes it
- **exclusions:** owning imaging satellites; mapping-agency statutory functions; consumer map apps
- **china_relevance:** high — 遥感应用/地理信息产业 is tracked annually by 中国地理信息产业协会
- **confidence:** high
- **sources:** GEO (Group on Earth Observations) GEOSS framework; 中国地理信息产业协会《中国地理信息产业发展报告》; OGC standards — Open Geospatial Consortium; GEOINT community publications — US Geospatial Intelligence Foundation (USGIF); Copernicus programme documentation — European Commission / ESA

### theme:satellite_iot_ntn — Satellite IoT & NTN messaging
- **name_en:** Satellite IoT & NTN messaging · **name_zh:** 天基物联网
- **value_chain_position:** downstream
- **parent_sub_theme:** theme:space_data_value_chain
- **defining_activities:** operate narrowband satellite messaging networks; integrate 3GPP NTN standards into device modules; serve asset-tracking and metering traffic; enable roaming between terrestrial and satellite coverage; serve maritime and utility telemetry markets
- **distinct_from:** theme:satellite_broadband_services and theme:direct_to_device_connectivity — those target broadband and handsets; this row serves low-power machine traffic
- **exclusions:** consumer voice/broadband; terrestrial LPWAN without satellite leg; AIS mandated transponders
- **china_relevance:** high — 天基物联网 (行云/吉星-class vocabulary) is an active Chinese constellation category
- **confidence:** medium
- **sources:** 3GPP Release 17/18 Non-Terrestrial Networks (NTN) specifications; GSMA satellite-terrestrial convergence publications; satellite IoT and NTN market research — Euroconsult/Novaspace; 天地一体化信息网络 white papers — 中国信息通信研究院 (CAICT)

### theme:human_spaceflight_stations — Human spaceflight & space stations
- **name_en:** Human spaceflight & space stations · **name_zh:** 载人航天与空间站
- **value_chain_position:** midstream
- **parent_sub_theme:** theme:space_exploration_programs
- **defining_activities:** develop crewed spacecraft and escape systems; build and operate pressurized orbital stations; deliver astronaut training and mission operations; contract commercial research payloads on stations
- **distinct_from:** every existing row — all are robotic/uncrewed commercial services; this row carries humans and pressurized infrastructure
- **exclusions:** suborbital tourism-only flights; lunar surface missions (deep-space row)
- **china_relevance:** high — 载人航天/中国空间站 is a national engineering program with broad supplier chains
- **confidence:** medium
- **sources:** NASA Commercial LEO Destinations (CLD) program documents; 中国载人航天工程办公室 station-program announcements

### theme:lunar_deep_space_missions — Lunar & deep-space missions
- **name_en:** Lunar & deep-space missions · **name_zh:** 月球与深空探测
- **value_chain_position:** midstream
- **parent_sub_theme:** theme:space_exploration_programs
- **defining_activities:** build lunar landers, rovers and relay spacecraft; deliver commercial payload-delivery services to the Moon; operate deep-space science missions; develop cislunar navigation and communication infrastructure; execute sample-return and ISRU demonstration missions
- **distinct_from:** theme:human_spaceflight_stations — that row is Earth-orbit crewed infrastructure; this row is exploration beyond Earth orbit
- **exclusions:** LEO constellations; interplanetary science without mission hardware; orbital tourism; military space-control missions (→ theme:space_security_counterspace)
- **china_relevance:** high — 探月工程/深空探测 (嫦娥/天问 series) anchors a national supplier chain
- **confidence:** medium
- **sources:** NASA Commercial Lunar Payload Services (CLPS) program; ISECG Global Exploration Roadmap; Planetary Science and Astrobiology Decadal Survey — National Academies of Sciences, Engineering, and Medicine; Cosmic Vision programme documentation — ESA; lunar and deep-space exploration program plans — 国家航天局 (CNSA)


**Union grafts (variant A rows re-parented onto this spine — see `## Union ledger`):**

### theme:launch_vehicle_propulsion
- **name_en:** Launch vehicle propulsion
- **name_zh:** 运载火箭动力系统
- **value_chain_position:** upstream
- **parent_sub_theme:** theme:space_industrial_base
- **defining_activities:** develop liquid rocket engines and solid motor stages; test and qualify propulsion systems; supply reusable-engine fleets to launch-vehicle programs.
- **distinct_from:** `theme:launch_services` — propulsion hardware sold to vehicle developers vs the flight service sold to satellite owners; distinct from `theme:aerospace_propulsion_engines` (proposed; gas-turbine aviation vs rocket propulsion); distinct from theme:spacecraft_propulsion_systems (in-space thrusters vs launch-vehicle propulsion)
- **exclusions:** spacecraft thrusters (→ `theme:satellite_components_payloads`); missile motors (→ `theme:missile_propulsion_supply`).
- **china_relevance:** high — reusable-engine development and 商业火箭 ecosystem are prominent domestic commercial-space milestones.
- **confidence:** high
- **sources:** Space Technology Taxonomy, TA01 Launch Propulsion — NASA; Annual Compendium of Commercial Space Transportation — FAA Office of Commercial Space Transportation (AST); commercial transportation safety reports — FAA/AST.

### theme:in_space_manufacturing
- **name_en:** In-space manufacturing & research platforms
- **name_zh:** 在轨制造
- **value_chain_position:** midstream
- **parent_sub_theme:** theme:space_operations_services
- **defining_activities:** operate microgravity production platforms; manufacture specialty materials/fibers and host life-science payloads; return products or data to terrestrial customers.
- **distinct_from:** `theme:in_orbit_servicing_removal` — production for terrestrial markets vs maintenance of orbiting assets; distinct from `theme:laboratory_automation_robots` (proposed; terrestrial lab robotics).
- **exclusions:** crewed station operations themselves; remote-sensing payload hosting (→ `theme:earth_observation`).
- **china_relevance:** medium — space-station science payload programs and commercial microgravity research demand are nascent but policy-supported.
- **confidence:** low
- **sources:** In Space Production Applications (InSPA) announcements — NASA; ISS National Lab research solicitations — Center for the Advancement of Science in Space (CASIS); The Space Economy in Figures — OECD.

### theme:spaceport_launch_infrastructure
- **name_en:** Spaceports & launch infrastructure
- **name_zh:** 商业航天发射场
- **value_chain_position:** upstream
- **parent_sub_theme:** theme:space_operations_services
- **defining_activities:** build and license launch pads and support facilities; provide range-safety and mission-integration services; manage reentry/recovery sites.
- **distinct_from:** `theme:launch_vehicle_propulsion` — fixed infrastructure vs propulsion hardware; distinct from `theme:ground_station_networks_ttoc` (launch-site infra vs satellite ground-station networks).
- **exclusions:** military missile test ranges; horizontal-runway airports without launch licensing.
- **china_relevance:** high — coastal commercial launch sites (海南商业航天发射场-class provincial programs) are new national infrastructure, though facilities are state-owned.
- **confidence:** high
- **sources:** Launch and reentry site licensing documentation — FAA Office of Commercial Space Transportation (AST); commercial aerospace promotion policy documents — 国家发展改革委 (NDRC) and provincial governments; The Space Economy in Figures — OECD.

### theme:space_security_counterspace
- **name_en:** Space security & counterspace systems
- **name_zh:** 空间安全与攻防系统
- **value_chain_position:** midstream
- **parent_sub_theme:** none
- **defining_activities:** harden and proliferate defense satellite architectures; field jamming-detection and EMP/kinetic-threat resilience; provide defense space-domain-awareness inputs to warfighter networks.
- **distinct_from:** `theme:military_space_communications` — protected communications services vs the defensive/enabling space-control systems around them; distinct from `theme:space_situational_awareness_debris` (civil safety cataloguing vs defense threat response).
- **exclusions:** offensive weapons programs (not equity-segment vocabulary); civil traffic management.
- **china_relevance:** high — 太空攻防 is an active PLA modernization domain and domestic policy discourse mirrors global counterspace investment.
- **confidence:** medium
- **sources:** Space Threat Assessment (annual) — Center for Strategic and International Studies (CSIS); Global Counterspace Capabilities report (annual) — Secure World Foundation; space security and PAROS research papers — UNIDIR.

---

## theme:fintech_payments — Fintech & Payments

No micros were admitted in V1 (Finance R11 was not federated); this theme currently has zero children in the hierarchy. The rows below build the full payments value chain for the first time: merchant acceptance, clearing rails, digital money, embedded finance, and risk/compliance. V1's four L9-rejected surfaces are re-opened with distinct slugs and tighter mechanisms under the current commission (see Scope note).

**Sub-theme grouping.** `theme:merchant_acceptance_chain` (what merchants touch), `theme:payment_clearing_rails` (networks and clearing/settlement infrastructure), `theme:digital_money_platforms` (wallets, tokenized cash, digital banking), `theme:embedded_finance_services` (finance embedded into non-financial journeys), `theme:payments_risk_compliance` (the decisioning and assurance layer).

**Theme-tier candidates (prose only).** (1) Stablecoin/tokenized-cash infrastructure may eventually belong under the crypto_digital_assets category as a cross-category theme candidate. (2) Post-trade market infrastructure could justify a "capital markets infrastructure" theme separate from payments if the seat wants the securities chain distinct.

### theme:payment_acceptance_gateways — Merchant acquiring & payment gateways
- **name_en:** Merchant acquiring & payment gateways · **name_zh:** 收单与支付网关
- **value_chain_position:** downstream
- **parent_sub_theme:** theme:merchant_acceptance_chain
- **defining_activities:** onboard and underwrite merchants; route authorization requests to networks/acquirers; aggregate settlement and payouts; provide checkout APIs and recurring-billing tooling; provide tokenization services
- **distinct_from:** theme:card_network_schemes — schemes set the four-party rules this row clears through; acceptance side vs network side
- **exclusions:** issuing cards to consumers; terminal hardware manufacturing (separate row); lending products attached at checkout (→ theme:digital_lending_credit_tech)
- **china_relevance:** high — 收单机构/支付网关 is the standard Chinese licensed-payments vocabulary (人民银行 payment-license segments)
- **confidence:** high
- **sources:** BIS CPMI payment, clearing and settlement framework (PFMI context); 中国支付清算协会《中国支付清算行业运行报告》; PCI DSS standards — PCI Security Standards Council; The Federal Reserve Payments Study — Federal Reserve System

### theme:pos_smart_terminal_hardware — POS terminals & smart payment hardware
- **name_en:** POS terminals & smart payment hardware · **name_zh:** POS终端与智能硬件
- **value_chain_position:** downstream
- **parent_sub_theme:** theme:merchant_acceptance_chain
- **defining_activities:** manufacture certified payment terminals; build secure modules and readers (contact/contactless); integrate QR/NFC/mPOS form factors; maintain terminal certification against scheme and PCI standards; implement softPOS acceptance on commodity phones
- **distinct_from:** theme:payment_acceptance_gateways — that row is the software routing above; this row is the certified device layer executing secure acceptance
- **exclusions:** ATMs without payment-acceptance scope; consumer phones themselves; consumer wearables' payment chips; barcode-scanner peripherals
- **china_relevance:** high — 智能POS/受理终端 is a distinct Chinese hardware segment under 银联-class certification regimes
- **confidence:** high
- **sources:** PCI Security Standards Council PIN Transaction Security (PTS) requirements; EMVCo contact/contactless Level 1 & 2 specifications; retail payment messaging standards (ISO 8583 family) — ISO TC 68

### theme:b2b_corporate_payments — B2B corporate payments & treasury
- **name_en:** B2B corporate payments & treasury · **name_zh:** 企业支付与财资管理
- **value_chain_position:** downstream
- **parent_sub_theme:** theme:merchant_acceptance_chain
- **defining_activities:** automate accounts-payable/receivable workflows; issue and process virtual cards; run supplier payouts and cross-border collections; integrate treasury and ERP payment rails; integrate payments into ERP and procurement systems
- **distinct_from:** consumer acceptance rows — this row targets corporate payment workflows and working capital rather than shopper checkout
- **exclusions:** consumer wallets; lending products without payment rails; procurement marketplace software
- **china_relevance:** medium — 对公支付/财资管理 is a growing segment tracked in 人民银行 支付体系运行 reports
- **confidence:** medium
- **sources:** AFP (Association for Financial Professionals) Electronic Payments Survey; 中国人民银行《支付体系运行总体情况》; ACH rules and network statistics — Nacha

### theme:card_network_schemes — Card networks & scheme rules
- **name_en:** Card networks & scheme rules · **name_zh:** 银行卡网络与卡组织
- **value_chain_position:** midstream
- **parent_sub_theme:** theme:payment_clearing_rails
- **defining_activities:** operate scheme rules and brand standards; run authorization switching among issuers and acquirers; set interchange-class economics within regulation; certify participants and terminals; run fraud and standards programs across issuers and acquirers
- **distinct_from:** theme:payment_acceptance_gateways and theme:pos_smart_terminal_hardware — both operate downstream under scheme licenses; this row is the rule-setting and switching network itself
- **exclusions:** issuing banks; merchant acquirers
- **china_relevance:** high — 银联-class 卡组织/转接清算 is a licensed clearing segment (银行卡清算机构) in China
- **confidence:** high
- **sources:** BIS CPMI "Digitalisation of payments" report; EMVCo specifications (scheme-owned standards body); The Federal Reserve Payments Study — Federal Reserve System; interchange-cap regulation studies — US Federal Reserve (Durbin Amendment research); payments statistics and reports — European Central Bank

### theme:instant_payment_rails — Instant payment rails
- **name_en:** Instant payment rails · **name_zh:** 实时支付清算网络
- **value_chain_position:** midstream
- **parent_sub_theme:** theme:payment_clearing_rails
- **defining_activities:** operate account-to-account real-time clearing and settlement; run central-switch message standards; provide fraud-screening hooks and request-to-pay; interconnect banks and non-bank PSPs; migrate banks to ISO 20022 messaging
- **distinct_from:** theme:card_network_schemes — that row clears card-based four-party volume; this row is account-based instant clearing (IBPS/FedNow-class infrastructure)
- **exclusions:** card networks; wallet apps riding the rails
- **china_relevance:** high — 网联平台与人民银行网上支付跨行清算系统 (IBPS) are the Chinese instant-rail anchors
- **confidence:** high
- **sources:** BIS CPMI fast-payments reports; 中国人民银行 网上支付跨行清算系统/网联平台 documentation; FedNow Service documentation — Federal Reserve System; SEPA Instant Credit Transfer scheme rulebooks — European Payments Council

### theme:cross_border_remittance_networks — Cross-border payments & remittance
- **name_en:** Cross-border payments & remittance · **name_zh:** 跨境支付与汇款
- **value_chain_position:** midstream
- **parent_sub_theme:** theme:payment_clearing_rails
- **defining_activities:** operate multi-currency correspondent and clearing networks; execute FX conversion and hedging at transfer; run compliance screening across corridors; provide collection/disbursement platforms for marketplaces
- **distinct_from:** theme:instant_payment_rails — that row is domestic clearing; this row spans jurisdictions, currencies and correspondent chains
- **exclusions:** trade finance credit; correspondent banking without payment operations; tourist FX retail
- **china_relevance:** high — 跨境支付 (CIPS-class infrastructure and 跨境电商收款) is a national infrastructure segment
- **confidence:** high
- **sources:** FSB G20 Cross-border Payments Roadmap; BIS Innovation Hub Nexus multilateral-link documentation; Remittance Prices Worldwide — World Bank; Payment Aspects of Financial Inclusion — BIS CPMI and World Bank Group

### theme:post_trade_settlement_infra — Post-trade settlement & market infrastructure
- **name_en:** Post-trade settlement & market infrastructure · **name_zh:** 交易后结算与金融基础设施
- **value_chain_position:** midstream
- **parent_sub_theme:** theme:payment_clearing_rails
- **defining_activities:** operate CSDs, clearing houses and settlement engines; net obligations and manage default-waterfall risk; run collateral management; deliver depository and asset-servicing functions
- **distinct_from:** payment rows — those clear currency; this row clears securities and derivatives obligations under PFMI-class principles
- **exclusions:** exchanges' matching engines; custody banks without infrastructure roles
- **china_relevance:** high — 交易后结算/金融市场基础设施 is formal CNCC/人民银行 FMI vocabulary
- **confidence:** medium
- **sources:** BIS CPMI-IOSCO Principles for Financial Market Infrastructures (PFMI); EU Central Securities Depositories Regulation (CSDR)

### theme:stablecoin_digital_cash — Stablecoin & tokenized cash infrastructure
- **name_en:** Stablecoin & tokenized cash infrastructure · **name_zh:** 稳定币与代币化现金
- **value_chain_position:** midstream
- **parent_sub_theme:** theme:digital_money_platforms
- **defining_activities:** issue stablecoins against reserve portfolios; operate redemption and attestation regimes; run ledger issuance/custody infrastructure; integrate tokenized cash into settlement flows; tokenize deposits and money-market instruments
- **distinct_from:** theme:instant_payment_rails — that row settles on account-based rails; this row settles with tokenized bearer-style digital cash under FSB/HKMA-class regimes (distinct from V1's rejected hybrid slug, which mixed the two)
- **exclusions:** volatile crypto assets; sovereign CBDC (separate row); crypto exchanges' trading venues
- **china_relevance:** medium — 稳定币 is emerging via 香港金管局《稳定币条例》; mainland activity remains restricted
- **confidence:** medium
- **sources:** FSB High-level Recommendations for Global Stablecoin Arrangements; 香港金融管理局《稳定币条例》(2025); crypto-asset and DeFi reports — Bank for International Settlements (BIS)

### theme:cbdc_sovereign_currency — CBDC platforms
- **name_en:** CBDC platforms · **name_zh:** 央行数字货币平台
- **value_chain_position:** midstream
- **parent_sub_theme:** theme:digital_money_platforms
- **defining_activities:** build central-bank digital currency cores (wholesale/retail); operate two-tier distribution with banks; deliver smart-contract conditional payments; run digital-currency wallets under sovereign liability
- **distinct_from:** theme:stablecoin_digital_cash — that row is private tokenized cash; this row is central-bank liability infrastructure (e-CNY-class)
- **exclusions:** reserve-backed private coins; core banking modernization without CBDC
- **china_relevance:** high — 数字人民币 (e-CNY) 研发 is a formal PBOC program with pilot-city infrastructure
- **confidence:** medium
- **sources:** BIS surveys "The rise of central bank digital currencies"; 中国人民银行数字人民币研发工作组白皮书; Central bank digital currencies: foundational principles and core features — BIS and seven central banks; digital euro progress reports — European Central Bank

### theme:digital_wallets_superapps — Digital wallets & super-app payments
- **name_en:** Digital wallets & super-app payments · **name_zh:** 数字钱包与超级应用
- **value_chain_position:** downstream
- **parent_sub_theme:** theme:digital_money_platforms
- **defining_activities:** operate consumer wallets with stored value; run QR/NFC payment acceptance networks; attach lifestyle services into super-app journeys; manage wallet risk limits under supervision
- **distinct_from:** theme:payment_acceptance_gateways — that row serves merchants; this row owns the consumer payment instrument and experience
- **exclusions:** bank deposits; loyalty points without payment function
- **china_relevance:** high — 移动支付/数字钱包 is the global-scale Chinese category (移动支付普及率 led by Chinese wallets)
- **confidence:** high
- **sources:** BIS CPMI "Digitalisation of payments"; 中国支付清算协会 mobile-payment industry reports

### theme:digital_banking_platforms — Digital banking platforms
- **name_en:** Digital banking platforms · **name_zh:** 数字银行平台
- **value_chain_position:** downstream
- **parent_sub_theme:** theme:digital_money_platforms
- **defining_activities:** run branchless banking with digital onboarding; operate core-banking stacks for deposits and lending; deliver in-app credit and savings journeys; manage capital and liquidity under banking licenses
- **distinct_from:** theme:digital_wallets_superapps — wallets move payments; this row carries the full banking relationship (deposits and credit books)
- **exclusions:** wallets without licenses; core-banking software vendors without banking operations
- **china_relevance:** high — 直销银行/互联网银行 is an established licensed category (民营银行/微贷-类 vocabulary)
- **confidence:** medium
- **sources:** HKMA virtual-bank regime guidelines; FSB "Fintech and market structure in financial services" report

### theme:embedded_finance_baas — Embedded finance & banking-as-a-service
- **name_en:** Embedded finance & banking-as-a-service · **name_zh:** 嵌入式金融与银行即服务
- **value_chain_position:** downstream
- **parent_sub_theme:** theme:embedded_finance_services
- **defining_activities:** expose payments/cards/lending rails via APIs; issue partner-branded accounts and cards under licenses; operate KYC and ledgering middleware; distribute finance inside non-financial platforms
- **distinct_from:** theme:digital_banking_platforms — that row serves end customers directly; this row supplies the programmable plumbing to partners
- **exclusions:** open-banking data aggregation without execution; white-label apps with full bank books
- **china_relevance:** medium — 开放银行/开放API is guided by 金标委 and HKMA-class frameworks; BaaS licensing in mainland remains constrained
- **confidence:** medium
- **sources:** UK CMA Open Banking (CMA9) standard; 香港金融管理局 Open API Framework for the Hong Kong Banking Sector; BIS FSI Insights on the digitalisation of payments and finance; fintech regulatory sandbox guidance — UK Financial Conduct Authority (FCA); fintech banking guidance — US Office of the Comptroller of the Currency (OCC)

### theme:pos_credit_bnpl — Point-of-sale credit & BNPL
- **name_en:** Point-of-sale credit & BNPL · **name_zh:** 先买后付与场景信贷
- **value_chain_position:** downstream
- **parent_sub_theme:** theme:embedded_finance_services
- **defining_activities:** underwrite time-split repayment at checkout; operate BNPL approval decisioning in milliseconds; fund receivables via warehouse lines or securitization; manage merchant discount economics
- **distinct_from:** theme:digital_wallets_superapps — wallets pay with existing funds; this row underwrites credit embedded in the payment moment
- **exclusions:** general-purpose credit cards; pawn/microfinance without POS rails
- **china_relevance:** high — 先买后付/消费分期 is an active licensed consumer-finance segment (消费金融公司) under 金监总局 rules
- **confidence:** medium
- **sources:** UK FCA buy-now-pay-later market reviews (Woolard Review and follow-ons); 国家金融监督管理总局《消费金融公司管理办法》(2024)

### theme:payments_fraud_aml_decisioning — Payments fraud & AML decisioning
- **name_en:** Payments fraud & AML decisioning · **name_zh:** 支付风控与反欺诈
- **value_chain_position:** enabler
- **parent_sub_theme:** theme:payments_risk_compliance
- **defining_activities:** score transaction fraud in real time; screen payments against sanctions and AML typologies; operate device intelligence and behavioral signals; file suspicious-activity workflows with supervisors
- **distinct_from:** theme:identity_access_management (cybersecurity) — that row governs access to systems; this row decides the risk of individual payment transactions (V1's rejected fraud row conflated the two under the L9 gate); theme:identity_fraud_anti_abuse — that row is consumer-platform abuse (bots, account takeover, promo abuse); this row decides risk on individual payment transactions
- **exclusions:** workforce IAM; chargeback processing without decisioning
- **china_relevance:** high — 反电诈/支付风控 obligations under 人民银行 and 反电信网络诈骗法 drive a dedicated market
- **confidence:** high
- **sources:** FATF Recommendations and AML/CFT guidance; 中国人民银行《金融机构反洗钱和反恐怖监督管理办法》(2021); BSA/AML Examination Manual — FFIEC; customer due diligence rules — FinCEN (US Treasury)

### theme:kyc_regtech_compliance — KYC, identity verification & regtech
- **name_en:** KYC, identity verification & regtech · **name_zh:** 身份核验与合规科技
- **value_chain_position:** enabler
- **parent_sub_theme:** theme:payments_risk_compliance
- **defining_activities:** verify customer identity at onboarding (document/biometric); screen prospects against PEP/watchlists; automate regulatory reporting and transaction monitoring calibration; manage eKYC evidence lifecycles
- **distinct_from:** theme:payments_fraud_aml_decisioning — that row scores live transactions; this row gates relationships at onboarding and reporting cycles (V1's rejected identity-verification row was an L9 casualty; the mechanism here is customer due diligence, not workforce access)
- **exclusions:** workforce IAM; marketing consent management
- **china_relevance:** high — 实名制/KYC obligations (反洗钱法, 账户实名制) make eKYC infrastructure a regulated necessity
- **confidence:** medium
- **sources:** FATF Guidance on Digital Identity; Basel Committee principles for the sound management of risks related to fintech


**Union grafts (variant A rows re-parented onto this spine — see `## Union ledger`):**

### theme:open_banking_data_sharing
- **name_en:** Open banking & financial data access
- **name_zh:** 开放银行
- **value_chain_position:** enabler
- **parent_sub_theme:** theme:embedded_finance_services
- **defining_activities:** expose bank account data via mandated APIs; aggregate accounts and initiate payments under consent; certify third-party providers under open-finance regimes.
- **distinct_from:** `theme:embedded_finance_baas` — mandated data-access rights vs discretionary product embedding; distinct from payment rail rows (data layer, not money movement).
- **exclusions:** credit bureaus' regulated data; marketing-data brokers.
- **china_relevance:** medium — personal-information protection law and 金融数据 security rules shape a consent-based data-sharing layer, still bank-led pilots.
- **confidence:** high
- **sources:** PSD2 revised payment services directive — European Union; Open Banking Standards — UK Open Banking Implementation Entity (OBIE); Section 1033 personal financial data rights rule — US Consumer Financial Protection Bureau (CFPB).

### theme:digital_lending_credit_tech
- **name_en:** Digital lending & credit technology
- **name_zh:** 数字信贷
- **value_chain_position:** downstream
- **parent_sub_theme:** theme:embedded_finance_services
- **defining_activities:** underwrite consumer/SME credit with alternative data; originate, service and collect loans digitally; embed credit decisioning APIs into partners.
- **distinct_from:** `theme:embedded_finance_baas` — the credit product/risk vs the embedding stack; distinct from `theme:payments_fraud_aml_decisioning` (credit underwriting vs financial-crime screening).
- **exclusions:** mortgage servicing platforms; credit-rating agencies.
- **china_relevance:** high — internet-loan rules (商业银行互联网贷款管理) institutionalize a large supervised digital-credit market.
- **confidence:** high
- **sources:** Global Findex Database — World Bank; Fintech credit markets around the world — BIS working papers; 商业银行互联网贷款管理暂行办法 — 中国银保监会 (CBIRC).

### theme:retail_investment_platforms
- **name_en:** Digital wealth & retail investment platforms
- **name_zh:** 数字财富管理
- **value_chain_position:** downstream
- **parent_sub_theme:** theme:digital_money_platforms
- **defining_activities:** operate retail brokerage and savings-investment apps; provide robo-advisory and model portfolios; custody and clear retail asset flows.
- **distinct_from:** payment and lending rows — savings/investment products vs payments or credit; distinct from `theme:crypto_digital_assets` macro category (regulated securities wealth vs digital-asset venues).
- **exclusions:** institutional prime brokerage; pension administration.
- **china_relevance:** high — fund-distribution platforms under 公募基金销售 rules serve the world's largest retail fund flows.
- **confidence:** medium
- **sources:** FINRA Industry Snapshot — FINRA; Investment platforms market study — UK Financial Conduct Authority (FCA).

### theme:cash_cycle_atm_networks
- **name_en:** Cash cycle & ATM networks
- **name_zh:** 现金循环与自助设备
- **value_chain_position:** midstream
- **parent_sub_theme:** theme:payment_clearing_rails
- **defining_activities:** manufacture and service ATMs/CRS recycling machines; operate cash-in-transit and vault logistics; manage recirculation and cash-forecasting for banks.
- **distinct_from:** `theme:pos_smart_terminal_hardware` — cash dispensing/recycling infrastructure vs acceptance terminals; distinct from all digital-rail rows (physical cash persists alongside them).
- **exclusions:** bank branch staffing; retail safes.
- **china_relevance:** medium — ATM/CRS demand declines with mobile payment yet remains policy-maintained for cash access (人民币现金收付 rights rules).
- **confidence:** high
- **sources:** Study on the payment attitudes of consumers (SPACE) — European Central Bank; Diary of Consumer Payment Choice — Federal Reserve Banks (Atlanta/San Francisco); ATM industry statistics — ATMIA.

---

## Proposal counts and field dictionary

| theme | new sub_themes | new micro_themes | micros by chain position |
|---|---|---|---|
| theme:cybersecurity | 3 | 21 | upstream 4 · midstream 7 · downstream 5 · enabler 5 |
| theme:defense_aerospace | 4 | 20 | upstream 6 · midstream 8 · downstream 3 · enabler 3 |
| theme:robotics_automation | 4 | 20 | upstream 3 · midstream 6 · downstream 6 · enabler 5 |
| theme:space_satellite | 4 | 17 | upstream 4 · midstream 9 · downstream 4 · enabler 0 |
| theme:fintech_payments | 5 | 19 | upstream 0 · midstream 7 · downstream 9 · enabler 3 |
| **total** | **20** | **97** | parent rows: 213 (20 theme→sub, 97 theme→micro, 96 sub→micro) |

\* RaaS (`theme:raas_fleet_operations`) is filed downstream (service delivery); simulation/MES are enablers counted under robotics midstream/enabler in the YAML `value_chain_position` field where noted.

Field conventions used above: `defining_activities` are verb phrases describing what an issuer DOES to belong; `distinct_from` names the nearest existing/proposed micro ids with the one-line mechanism boundary; `exclusions` fence the row; `china_relevance` uses high/medium/low with natural industry vocabulary and no issuers; `confidence` is the lane's evidence-calibrated rating (never a validation claim); `sources` lists ≥2 named public non-vendor references. Display-tier only: no weights, shares, scores, ranks, or exposure of any kind; rows PROPOSE, the seat ratifies.

## Union ledger (gmi-micro-u2-20261021-r1)

Union rules applied in order: spine = variant B; exact-id overlaps keep B's row and section (A-only sources appended); near-duplicate pairs resolved MERGE (kept id = the more precise mechanism statement, ties to B) or KEEP-BOTH (genuinely different mechanisms — `distinct_from` of both names the other); every remaining A-only micro grafted verbatim with `parent_sub_theme` re-parented and any merged-away id reference remapped.

#### Exact overlaps (3)
- EXACT theme:agricultural_field_robotics — kept B row/section; A-only sources (ISO 11783 ISOBUS, Future Farming) appended.
- EXACT theme:embedded_finance_baas — kept B row/section; A-only sources (BIS FSI Insights, FCA sandboxes, OCC guidance) appended.
- EXACT theme:robot_simulation_digital_twin — kept B row/section; A-only sources (NIST digital-twin/CPS, Open Robotics Gazebo) appended.

#### Seat-listed near pairs — MERGE (17, all kept on B's id; B's mechanism statement was at least as precise in every pair, so the tie-break never bound against B)
- MERGE kept=theme:air_missile_defense_systems dropped=theme:air_defense_systems — same integrated air/missile-defense system-of-systems; A's C-RAM classes, space-tracking exclusion and NATO IAMD source folded in.
- MERGE kept=theme:application_security_devsecops dropped=theme:application_security_testing — same pre-production appsec/CI mechanism; A's pen-test/WAF exclusions folded in.
- MERGE kept=theme:amr_agv_intralogistics dropped=theme:autonomous_mobile_robots — same intralogistics mobile-robot mechanism incl. fleet software; A's human-shared-floor safety certification (ANSI/RIA R15.08) folded in.
- MERGE kept=theme:cross_border_remittance_networks dropped=theme:cross_border_remittance_infra — same multi-corridor settlement/FX/compliance mechanism; A's tourist-FX exclusion, World Bank and BIS/World Bank sources folded in.
- MERGE kept=theme:cyber_insurance_risk_quantification dropped=theme:cyber_insurance_risk_transfer — same underwrite-on-quantified-loss mechanism; A's control-baseline requirements, claims handling, Geneva Association and EIOPA sources folded in.
- MERGE kept=theme:cyber_workforce_training dropped=theme:cyber_range_training — same human-capability/ranges mechanism (each named the other's core); A's tooling-benchmark activity and ATT&CK Evaluations source folded in.
- MERGE kept=theme:lunar_deep_space_missions dropped=theme:deep_space_missions — same beyond-Earth-orbit exploration mechanism; A's sample-return/ISRU activities, Decadal Survey/ESA/CNSA sources folded in.
- MERGE kept=theme:geospatial_analytics_platforms dropped=theme:geospatial_intelligence_analytics — same downstream EO-analytics mechanism; A's InSAR/3D deliverables, OGC/USGIF/Copernicus sources folded in.
- MERGE kept=theme:humanoid_embodied_robots dropped=theme:humanoid_robots — same humanoid form-factor-with-embodied-AI mechanism; A's pilot-first activity, animatronics exclusion, IEEE RAS source folded in.
- MERGE kept=theme:in_orbit_servicing_removal dropped=theme:in_orbit_services_servicing — same rendezvous/refuel/deorbit/debris-removal mechanism; A's reposition activity, FCC five-year rule and IADC sources folded in.
- MERGE kept=theme:instant_payment_rails dropped=theme:instant_account_payment_rails — same account-based instant-clearing mechanism; A's ISO 20022 migration activity, FedNow/EPC sources folded in.
- MERGE kept=theme:defense_training_simulation dropped=theme:military_training_simulation — same simulator/LVC-range/mission-rehearsal mechanism; A's airline flight-school exclusion, GAO source and the training-vs-T&E boundary folded in.
- MERGE kept=theme:pos_smart_terminal_hardware dropped=theme:pos_hardware_smart_terminals — same certified acceptance-hardware mechanism; A's softPOS activity, wearables/barcode exclusions, ISO 8583 source folded in.
- MERGE kept=theme:robot_system_integration dropped=theme:robotics_system_integration — same turnkey integration/commissioning mechanism; A's rental-platform exclusion and VDMA source folded in.
- MERGE kept=theme:satellite_iot_ntn dropped=theme:satellite_iot_messaging — same narrowband satellite-IoT/NTN mechanism; A's maritime/utility markets, AIS exclusion, Euroconsult and CAICT sources folded in.
- MERGE kept=theme:supply_chain_firmware_security dropped=theme:supply_chain_security_sca — same SBOM/provenance/integrity mechanism (B adds the firmware tier); A's dependency-registry monitoring, EO 14028 source folded in.
- MERGE kept=theme:warehouse_fulfillment_automation dropped=theme:warehouse_automation_systems — same goods-to-person/AS/RS/sortation+WES mechanism; A's service/modernization contracts and Interact Analysis source folded in.

#### Scan-found near pairs the token heuristic missed — MERGE (23, kept on B's id)
- MERGE kept=theme:military_aircraft_platforms dropped=theme:fixed_wing_combat_aircraft — A's fixed-wing combat row is a slice of B's combat/trainer/transport program mechanism; A's offset/sovereign-assembly activity, UCA exclusion, EDA source folded in.
- MERGE kept=theme:ground_combat_systems dropped=theme:land_systems_armored_vehicles — same tanks/IFV/artillery land-platform mechanism; A's allied-fleet supply, soldier-equipment/truck exclusions, GAO/NDIA sources folded in.
- MERGE kept=theme:energetics_explosives_supply dropped=theme:explosive_energetics_materials — same energetics-chemistry supply mechanism; A's IATG/GAO sources folded in.
- MERGE kept=theme:defense_microelectronics dropped=theme:defense_electronics_microelectronics — same trusted/rad-hard defense silicon mechanism; A's chiplet/power-electronics packaging, EDA exclusion, CSIS source folded in.
- MERGE kept=theme:defense_sustainment_mro dropped=theme:military_logistics_sustainment — shared depot-MRO core; A's supply-chain/readiness-engineering and contested-logistics activities, DLA/NATO sources folded in (mechanism kept single: readiness sustainment).
- MERGE kept=theme:rehab_exoskeleton_robotics dropped=theme:rehabilitation_medical_robots — same rehab/therapy-robot mechanism; A's assistive-care activity, telehealth exclusion, State Council source folded in. A's hospital-logistics slice is already covered by theme:professional_service_robots (B's rehab row excludes it).
- MERGE kept=theme:end_effectors_grippers dropped=theme:robot_end_effectors_tooling — same wrist tooling mechanism; A's compliant-fixture activity, ISO 9409/ICRA sources folded in. A's force/torque sensing line is NOT folded — B's theme:force_tactile_safety_sensing owns that mechanism.
- MERGE kept=theme:satellite_manufacturing_constellations dropped=theme:spacecraft_manufacturing_satellites — same satellite AIT/manufacturing mechanism; A's government/science-customer breadth, Euroconsult and SCIO white-paper sources folded in.
- MERGE kept=theme:satellite_components_payloads dropped=theme:space_components_subsystems — same component/subsystem tier; A's rad-tolerant electronics/harness activity, RF front-end exclusion, NASA EEE/Small Spacecraft sources folded in.
- MERGE kept=theme:ground_station_networks_ttoc dropped=theme:ground_segment_as_a_service — same operator ground-segment/TT&C mechanism; A's data routing/preprocessing, broadcast-uplink exclusion, CCSDS/ESOC/GSOA sources folded in.
- MERGE kept=theme:space_situational_awareness_debris dropped=theme:space_situational_awareness_traffic — same track/catalogue/conjunction-screening mechanism; A's space-weather service and Space-Track source folded in.
- MERGE kept=theme:gnss_pnt_services dropped=theme:positioning_navigation_timing — same PNT signal/augmentation mechanism (B already builds chip-modules); A's chipset/antenna production and alt-PNT development, EUSPA/USDOT/RTCM sources folded in.
- MERGE kept=theme:payment_acceptance_gateways dropped=theme:digital_payment_processing — same merchant acquiring/gateway mechanism; A's tokenization activity, checkout-lending exclusion, PCI DSS/Fed study sources folded in.
- MERGE kept=theme:b2b_corporate_payments dropped=theme:b2b_payments_automation — B's AP/AR automation core is A's whole row; A's ERP/procurement integration, Nacha source folded in.
- MERGE kept=theme:card_network_schemes dropped=theme:payment_network_schemes — A's row is card-scheme operation/rules/interchange, B's exact mechanism; A's fraud/standards programs, Fed/ECB/Durbin sources folded in.
- MERGE kept=theme:stablecoin_digital_cash dropped=theme:stablecoin_tokenized_money — same reserve-backed issuance/redemption/attestation mechanism; A's deposit-tokenization activity, venue exclusion, BIS source folded in.
- MERGE kept=theme:cbdc_sovereign_currency dropped=theme:cbdc_infrastructure — same sovereign CBDC core/two-tier mechanism; A's BIS-seven-banks principles and digital-euro sources folded in.
- MERGE kept=theme:payments_fraud_aml_decisioning dropped=theme:transaction_monitoring_aml — B's sanctions/AML screening + SAR filing is A's row core (calibration adjacent to theme:kyc_regtech_compliance); A's FFIEC/FinCEN sources folded in.
- MERGE kept=theme:soc_mdr_services dropped=theme:managed_security_services — same outsourced-security-operations mechanism; A's co-managed tooling/retainer readiness, body-shop exclusion, ISC2 source folded in.
- MERGE kept=theme:threat_intelligence_cti + theme:vulnerability_exposure_management dropped=theme:threat_intelligence_vulnerability_research — A's single row conflated two mechanisms B splits precisely; A's bug-bounty intake folded into the vulnerability row, Verizon DBIR and FIRST CSIRT sources into the CTI row.
- MERGE kept=theme:zero_trust_sase_access dropped=theme:zero_trust_architecture — A's row includes ZTNA/per-request access, B's exact core; A's east-west microsegmentation activity, consumer-VPN exclusion, CISA ZTM source folded in.
- MERGE kept=theme:data_security_privacy_governance dropped=theme:data_security_posture — B's classify/inventory/DLP core subsumes A's DSPM row; A's posture-remediation and secrets-vaulting activities, backup exclusion, NIST 800-53 source folded in.
- MERGE kept=theme:ot_iot_industrial_security dropped=theme:operational_technology_security — same OT/ICS protection mechanism; A's OT-incident-procedure validation, safety/substation exclusions, ATT&CK for ICS source folded in.

#### Scan-found near pairs — KEEP-BOTH (10; `distinct_from` of both names the other)
- KEEP-BOTH theme:extended_detection_response ~ theme:soc_mdr_services — platform product vs human-led operated service (the same product/service boundary B draws against the surface rows).
- KEEP-BOTH theme:digital_forensics_incident_response ~ theme:soc_mdr_services — episodic post-compromise forensics engagements vs continuous monitoring operations.
- KEEP-BOTH theme:identity_fraud_anti_abuse ~ theme:payments_fraud_aml_decisioning — consumer-platform anti-abuse (bots/ATO/promo) vs payment-transaction risk decisioning; different signals, domains and buyers.
- KEEP-BOTH theme:hardware_root_of_trust ~ theme:supply_chain_firmware_security — the silicon trust anchor (TPM/secure element/HSM) vs the software/firmware provenance chain attested through it.
- KEEP-BOTH theme:post_quantum_cryptography_migration ~ theme:crypto_pki_key_management — the algorithm-replacement migration program (CBOM, staged migration, crypto-agility) vs the standing PKI/key-material estate.
- KEEP-BOTH theme:security_governance_compliance ~ theme:security_integration_compliance — GRC platforms/risk governance vs on-site integration labor and conformity assessment.
- KEEP-BOTH theme:embodied_ai_robot_learning ~ theme:humanoid_embodied_robots — the cross-form-factor learning/policy layer (brains) vs the humanoid body (form factor).
- KEEP-BOTH theme:launch_vehicle_propulsion ~ theme:spacecraft_propulsion_systems — launch-vehicle propulsion hardware (B's row explicitly excludes launch first stages) vs in-space propulsion/thrusters.
- KEEP-BOTH theme:rotorcraft_vertical_lift ~ theme:military_aircraft_platforms — separate platform family with its own certification basis and industrial base, incl. civil-certified vertical lift B's military-program row does not cover.
- KEEP-BOTH theme:aerospace_propulsion_engines ~ theme:military_aero_engines — the military-and-commercial aero-engine industrial base with lifetime aftermarket economics (B's row explicitly excludes commercial engines) vs the military program tier.

#### Grafted A-only micros (27) with new parent_sub_theme
- theme:extended_detection_response → theme:security_control_platforms
- theme:email_collaboration_security → theme:security_control_platforms
- theme:identity_fraud_anti_abuse → theme:security_control_platforms
- theme:digital_forensics_incident_response → theme:security_operations_assurance
- theme:security_governance_compliance → theme:security_operations_assurance
- theme:hardware_root_of_trust → theme:security_engineering_enablement
- theme:post_quantum_cryptography_migration → theme:security_engineering_enablement
- theme:rotorcraft_vertical_lift → theme:defense_platform_programs
- theme:undersea_systems_sonar → theme:defense_platform_programs
- theme:aerospace_propulsion_engines → theme:defense_technology_readiness
- theme:aerospace_structures_composites → theme:defense_technology_readiness
- theme:defense_test_evaluation_infrastructure → theme:defense_technology_readiness
- theme:military_logistics_sustainment → theme:defense_technology_readiness
- theme:air_traffic_management_systems → theme:civil_aerospace_economy
- theme:business_general_aviation → theme:civil_aerospace_economy
- theme:laboratory_automation_robots → theme:automation_application_systems
- theme:semiconductor_factory_automation → theme:automation_application_systems
- theme:robot_software_middleware → theme:automation_software_operations
- theme:embodied_ai_robot_learning → theme:automation_software_operations
- theme:industrial_iot_condition_monitoring → theme:automation_software_operations
- theme:launch_vehicle_propulsion → theme:space_industrial_base
- theme:in_space_manufacturing → theme:space_operations_services
- theme:spaceport_launch_infrastructure → theme:space_operations_services
- theme:space_security_counterspace → (no sub_theme — carried as a direct theme child, per variant A's programmatic-row placement)
- theme:open_banking_data_sharing → theme:embedded_finance_services
- theme:digital_lending_credit_tech → theme:embedded_finance_services
- theme:retail_investment_platforms → theme:digital_money_platforms
- theme:cash_cycle_atm_networks → theme:payment_clearing_rails

#### Sub_themes carried over from A (1)
- theme:civil_aerospace_economy (under theme:defense_aerospace) — no B sub_theme fits civil ATM/business-GA; children: theme:air_traffic_management_systems, theme:business_general_aviation.

#### Final union counts per theme
- theme:cybersecurity: sub_themes 3, micro_themes 21 (upstream 4 · midstream 7 · downstream 5 · enabler 5)
- theme:defense_aerospace: sub_themes 4, micro_themes 20 (upstream 6 · midstream 8 · downstream 3 · enabler 3)
- theme:robotics_automation: sub_themes 4, micro_themes 20 (upstream 3 · midstream 6 · downstream 6 · enabler 5)
- theme:space_satellite: sub_themes 4, micro_themes 17 (upstream 4 · midstream 9 · downstream 4 · enabler 0)
- theme:fintech_payments: sub_themes 5, micro_themes 19 (upstream 0 · midstream 7 · downstream 9 · enabler 3)
- TOTAL: sub_themes 20, micro_themes 97, parents 213 (20 theme→sub, 97 theme→micro, 96 sub→micro).
