# GMI taxonomy owner review of the 68 frozen micros (2026-11-02)

## Purpose and authority

This dossier is the evidence behind `research/theme_graph/micro_owner_dispositions.yml`: one recorded owner disposition for each FROZEN-tier micro (crosswalk `asserted_on` before 2026-10-21). `scripts/gmi_coverage_proof.py` reads that file. A row sets only that micro's `owner_reviewed` / `owner_disposition` in the coverage report. It never changes a computed coverage disposition, a count, a gate threshold or the frozen 68-micro denominator.

Authority: on 2026-11-02 Chairman Chris told seat 6f14c2da, verbatim, "Take over the taxonomy owner job as well". `DEC:GMI-TAXONOMY-OWNER-DELEGATED-TO-SEAT` records that delegation. It supersedes only the "a seat may not self-review" clause of `DEC:GMI-DESCRIPTIVE-PRODUCT-ACCEPTANCE-2026-10-19`. The compensating control is an independent, non-authoring review of this dossier and the contract before merge.

A non-KEEP disposition here is a recorded owner decision only. Nothing in this change edits `config/theme_crosswalk.yml` or executes a MERGE, RENAME, RETIRE or SPLIT. Execution is a separate follow-up lane (see [Follow-up rules](#follow-up-rules)).

## Method

- Timestamps: `decided_at` values are UTC (`2026-11-03T01:01:17+00:00`), the same moment as 2026-11-02 local time (PDT). The file date follows local time.
- Inputs: `config/theme_crosswalk.yml` at base commit `0e2ec04297a4ed4d1b18f16c57092e6ec8dc7165`, the read-only baseline coverage proof produced by `python3 scripts/gmi_coverage_proof.py --symbol-directory data/symbol_directory/snapshots/2026-10-31.parquet --out <scratch dir>`, and the activity probation lane `data/theme_graph/probation/activity_proposals.jsonl`.
- Facts are computed by `research/theme_graph/micro_owner_review_2026_11_02_overlap.py`, not by eye. Its output is the companion `research/theme_graph/micro_owner_review_2026-11-02.json` (sha256 `2102f3d93cf2a66a08699ca0976cabb7e3a8419ce1c507ce1a6104882ca4e692`). It contains 68 frozen micros out of 371 crosswalk micros; the frozen id-set sha256 is `5feff3276eda4a07791a872208dc4c2cdd5fa06e7e99553ada1e01fd8f7ed878`, which equals the baseline proof's.
- Each frozen micro is scored against every other crosswalk micro, frozen and expansion alike: token Jaccard on name+id (`name_jac`), token Jaccard on name+note (`def_jac`), character-trigram cosine on the EN name (`name_char3`), Jaccard on ZH-name bigrams (`zh_bigram`), shared parent, and shared member companies.
- Composite: `composite = .35 name_jac + .25 def_jac + .2 name_char3 + .2 zh_bigram + .1 shared_parent + .3 shared_members`. Flag rule: `composite >= 0.30 or name_jac >= 0.34 or zh_bigram >= 0.34 or shared members`. A flag is a prompt for judgment, not a finding.
- Membership: the only edge type into micros in `data/theme_graph/edges.parquet` is PARENT_OF, so member companies come from the probation lane alone. Only `theme:hbm_packaging` has a member. A shared-member overlap test is therefore uninformative for the other 67, and the review leans on scope text, names, parents and referrer excerpts.
- Referrers: crosswalk rows whose note names the micro. The excerpts show how the rest of the taxonomy already uses each scope.
- Gate-2 provenance: each micro's id and `nominated_from` are checked for the vendor/source label markers (finviz_themes, ths_concepts, china_ths, and the ltheme and china-THS basket label prefixes). No frozen micro carries one.

Rubric (seat-frozen):

| disposition | meaning |
|---|---|
| KEEP | distinct, coherent scope under a sensible parent with no frozen near-duplicate; EMPTY coverage alone is never grounds to retire |
| MERGE | near-duplicate of another micro; the note names the target id |
| RENAME | scope is sound but the EN/ZH name misleads; the note gives the proposed EN and ZH names |
| SPLIT | scope conflates two investable mechanisms; the note names the children |
| RETIRE | not a coherent investable micro, including vendor/source labels and gate-2 provenance |

Confidence: HIGH means the scope, the flags and the referrers all agree. MEDIUM means a judgment call with a stated reason. LOW (LOW-CONFIDENCE) means the call could reasonably go the other way, and the contract note starts with `LOW-CONFIDENCE`.

## Summary

| measure | value |
|---|---|
| frozen micros reviewed | 68 of 68 |
| KEEP | 64 |
| MERGE | 0 |
| RENAME | 4 |
| SPLIT | 0 |
| RETIRE | 0 |
| confidence HIGH / MEDIUM / LOW | 54 / 7 / 7 |
| baseline coverage disposition | EMPTY 67, NATIVE_POPULATED 1 |
| gate-2 provenance hits | 0 |

## Non-KEEP and LOW-CONFIDENCE proposals

| micro | disposition | confidence | proposal |
|---|---|---|---|
| [`theme:cardiorenal_metabolic_indications`](#micro-cardiorenal_metabolic_indications) | KEEP | LOW | LOW-CONFIDENCE KEEP: issuers likely coincide with glp1_incretin_therapies; revisit as MERGE or RENAME once populated. |
| [`theme:critical_mineral_mining_development`](#micro-critical_mineral_mining_development) | KEEP | LOW | LOW-CONFIDENCE KEEP: broad umbrella; per-commodity SPLIT considered and not proposed. |
| [`theme:fill_finish_delivery_devices`](#micro-fill_finish_delivery_devices) | KEEP | LOW | LOW-CONFIDENCE KEEP: possible SPLIT (fill-finish capacity vs pen/autoinjector devices) if member sets diverge. |
| [`theme:fuel_cycle`](#micro-fuel_cycle) | RENAME | MEDIUM | RENAME to EN 'Nuclear fuel front end (mining to enrichment)' / ZH '核燃料循环前端（铀矿开采至浓缩）'. Scope unchanged. |
| [`theme:glp1_incretin_therapies`](#micro-glp1_incretin_therapies) | RENAME | MEDIUM | RENAME to EN 'Injectable GLP-1 incretin therapies' / ZH '注射用 GLP-1 肠促胰岛素疗法'. Scope unchanged. |
| [`theme:hbm_packaging`](#micro-hbm_packaging) | RENAME | MEDIUM | RENAME to EN 'HBM memory stacking & packaging' / ZH 'HBM 存储堆叠与封装'. Scope unchanged. Execution is deferred to a qualified C01 cutover that preserves generation 040b and D2E acceptance, and must re-bind actprop:287edbf7e04b8aba873b7493 (co:us:MU) to the new scope_version in the same act. |
| [`theme:nand_enterprise_storage`](#micro-nand_enterprise_storage) | RENAME | LOW | LOW-CONFIDENCE RENAME to EN 'NAND flash & enterprise SSDs' / ZH 'NAND 闪存与企业级 SSD'. Scope unchanged. |
| [`theme:precision_agriculture_platforms`](#micro-precision_agriculture_platforms) | KEEP | LOW | LOW-CONFIDENCE KEEP: scope coherent; placement under ag_fertilizer is questionable (re-parenting is outside the disposition rubric). |
| [`theme:reactor_technology`](#micro-reactor_technology) | KEEP | LOW | LOW-CONFIDENCE KEEP: generic name; possible later RENAME to make the SMR/LWR designer scope explicit. |
| [`theme:structural_steel_electrification`](#micro-structural_steel_electrification) | KEEP | LOW | LOW-CONFIDENCE KEEP: name says structural steel, note says steel plate; investability thin; revisit as RENAME or RETIRE. |

## Follow-up rules

- Execution of every non-KEEP row is a separate lane with its own review. It edits `config/theme_crosswalk.yml`, and it never changes the frozen 68-micro denominator: a renamed micro keeps its id and stays frozen-tier, and no micro enters or leaves the frozen set because of this review.
- A RENAME changes the crosswalk entry, and with it the micro's `scope_version` (sha256 of the whole entry). Renaming `theme:hbm_packaging` must re-bind its admitted activity row (`actprop:287edbf7e04b8aba873b7493`, member `co:us:MU`) to the new `scope_version`. That rename is therefore executed only at a qualified C01 cutover that preserves generation 040b and D2E acceptance, and the cutover re-binds the row in the same act. Otherwise the only populated frozen micro loses its admission.
- After a RENAME executes, the owner updates that micro's contract row, normally to KEEP against the new names. Rows key on `micro_id`, not on `scope_version`, so the coverage gate stays closed throughout.
- LOW-CONFIDENCE KEEPs to revisit once members exist: `theme:cardiorenal_metabolic_indications` (possible MERGE into `theme:glp1_incretin_therapies`), `theme:critical_mineral_mining_development` (possible per-commodity SPLIT), `theme:fill_finish_delivery_devices` (possible SPLIT), `theme:reactor_technology` (possible RENAME), `theme:structural_steel_electrification` (possible RENAME or RETIRE).
- Parent placement is outside the disposition rubric: `theme:precision_agriculture_platforms` sits under `theme:ag_fertilizer`, which is questionable. It is recorded for a hierarchy follow-up.
- Containment questions on the expansion side, outside this frozen-tier review: `theme:wafer_fab_subsystems` and `theme:vacuum_subsystem_components`; `theme:launch_services` and `theme:dedicated_small_launch_vehicles`; `theme:pv_cell_module_manufacturing` with `theme:advanced_cell_manufacturing` and `theme:pv_manufacturing_equipment`; `theme:liquid_cooling_thermal` with `theme:cold_plate_liquid_cooling` and immersion cooling; `theme:grid_distribution_automation` and `theme:grid_protection_substation_automation`; `theme:surgical_implants_instruments` and `theme:surgical_energy_endoscopy`.

## Per-micro review

Sorted by id. Each heading's anchor is the `evidence` target of that micro's contract row.

### micro-aerospace_components_aftermarket

`theme:aerospace_components_aftermarket`: Aerospace components and aftermarket / 航空航天零部件与售后市场

- **Proposed disposition:** KEEP (confidence HIGH)
- **Rationale:** A coherent parts, materials and aftermarket-service layer across aircraft programs. No neighbour is flagged, and the expansion rows defense_sustainment_mro and military_aircraft_platforms already define their scopes against it.
- **Name quality:** Matches the scope; no naming defect found.
- **Parent paths:** `theme:industrials_defense>theme:defense_aerospace>theme:aerospace_components_aftermarket`
- **Asserted on / nominated from:** 2026-10-08 / `research:research/defense_intelligence/D0R_DEFENSE_EQUITY_DRIVER_TAXONOMY.md`
- **Crosswalk note:** "Parts, materials and aftermarket-service layer across aircraft programs, distinct from munitions propulsion."
- **scope_version:** `2c804fe8fb37875f92bbc07dccabe006405c49f31cc3f9b937f08a5c14cc2b2f`
- **Baseline coverage:** EMPTY; admitted 0, proposed 0, rejected 0; vendor routes 0, vendor member companies 0; research records none; route kinds none
- **Member companies (probation lane):** none
- **Siblings:** 26 micros share a parent; frozen siblings: `theme:autonomous_systems_counter_uas`, `theme:defense_sensors_electronics_c2`, `theme:military_space_communications`, `theme:missile_propulsion_supply`, `theme:missiles_munitions_effects`, `theme:naval_shipbuilding`
- **Gate-2 provenance markers:** none
- **Flagged by rule:** none

| nearest neighbour | tier | composite | name_jac | def_jac | name_char3 | zh_bigram | shared parent | shared members |
|---|---|---|---|---|---|---|---|---|
| `theme:seekers_guidance_components` | DISPLAY_EXPANSION | 0.293 | 0.2 | 0.13 | 0.385 | 0.067 | yes | 0 |
| `theme:aerospace_structures_composites` | DISPLAY_EXPANSION | 0.224 | 0.167 | 0.12 | 0.118 | 0.062 | yes | 0 |
| `theme:aerospace_propulsion_engines` | DISPLAY_EXPANSION | 0.216 | 0.167 | 0.143 | 0.032 | 0.077 | yes | 0 |
| `theme:nuclear_components` | FROZEN_ACCEPTANCE | 0.197 | 0.25 | 0.056 | 0.393 | 0.083 | no | 0 |
| `theme:vacuum_subsystem_components` | DISPLAY_EXPANSION | 0.182 | 0.2 | 0.136 | 0.321 | 0.067 | no | 0 |

Referenced by:

- `theme:defense_sustainment_mro` (DISPLAY_EXPANSION): "...e layer: depot maintenance, mid-life upgrades, readiness engineering; aerospace_components_aftermarket is the parts/commercial MRO tier beneath it."
- `theme:military_aircraft_platforms` (DISPLAY_EXPANSION): "...rm program (complete combat/transport aircraft with mission systems); aerospace_components_aftermarket supplies parts and aftermarket across programs."

### micro-ai_interconnect_silicon

`theme:ai_interconnect_silicon`: AI cluster interconnect silicon / AI 集群互联芯片

- **Proposed disposition:** KEEP (confidence HIGH)
- **Rationale:** Cluster network, switch and SerDes silicon is a different mechanism from compute and from packaging. The only flag (ai_power_delivery_silicon, 0.336) comes from shared 'AI ... silicon' tokens. Five expansion rows carve their scopes against it.
- **Name quality:** Matches the scope; no naming defect found.
- **Parent paths:** `theme:semiconductors_hardware>theme:ai_semiconductors>theme:ai_interconnect_silicon`; `theme:technology_software>theme:ai_semiconductors>theme:ai_interconnect_silicon`
- **Asserted on / nominated from:** 2026-10-08 / `research:config/theme_thesis_registry.yml`
- **Crosswalk note:** "Mechanism distinguishes interconnect from compute and packaging."
- **scope_version:** `b3947368615b0cc304dd7e548fb7d76d4c876886c35e1074de0472b800579d0c`
- **Baseline coverage:** EMPTY; admitted 0, proposed 0, rejected 0; vendor routes 0, vendor member companies 0; research records none; route kinds none
- **Member companies (probation lane):** none
- **Siblings:** 24 micros share a parent; frozen siblings: `theme:custom_asic_silicon`, `theme:gpu_merchant_accelerators`, `theme:hbm_packaging`
- **Gate-2 provenance markers:** none
- **Flagged by rule:** `theme:ai_power_delivery_silicon` (0.336)

| nearest neighbour | tier | composite | name_jac | def_jac | name_char3 | zh_bigram | shared parent | shared members |
|---|---|---|---|---|---|---|---|---|
| `theme:ai_power_delivery_silicon` | DISPLAY_EXPANSION | 0.336 | 0.333 | 0.091 | 0.372 | 0.111 | yes | 0 |
| `theme:pcie_fabric_silicon` | DISPLAY_EXPANSION | 0.288 | 0.143 | 0.25 | 0.265 | 0.111 | yes | 0 |
| `theme:silicon_photonics_devices` | DISPLAY_EXPANSION | 0.235 | 0.143 | 0.143 | 0.247 | 0.0 | yes | 0 |
| `theme:custom_asic_silicon` | FROZEN_ACCEPTANCE | 0.215 | 0.143 | 0.143 | 0.035 | 0.111 | yes | 0 |
| `theme:large_diameter_silicon_wafers` | DISPLAY_EXPANSION | 0.215 | 0.111 | 0.038 | 0.333 | 0.0 | yes | 0 |

Referenced by:

- `theme:co_packaged_optics_integration` (DISPLAY_EXPANSION): "...kage-level integration of optical engines beside ASICs; distinct from ai_interconnect_silicon (electrical switch silicon) and silicon_photonics_devices (photonic c..."
- `theme:network_offload_processors` (DISPLAY_EXPANSION): "...load processors; distinct from pcie_fabric_silicon (fixed fabric) and ai_interconnect_silicon (switch fabric)."
- `theme:optical_transceiver_modules` (DISPLAY_EXPANSION): "Pluggable photonic-electronic conversion modules; distinct from ai_interconnect_silicon (electrical switch/SerDes silicon)."
- `theme:pcie_fabric_silicon` (DISPLAY_EXPANSION): "Intra-host PCIe/CXL fabric silicon; distinct from ai_interconnect_silicon (cluster-scale network silicon)."
- `theme:silicon_photonics_devices` (DISPLAY_EXPANSION): "Photonic IC devices and photonic PDK/foundry shuttles; distinct from ai_interconnect_silicon (electrical) and co_packaged_optics_integration (package integration)..."

### micro-autonomous_systems_counter_uas

`theme:autonomous_systems_counter_uas`: Autonomy, drones and counter-UAS / 自主系统、无人机与反无人机

- **Proposed disposition:** KEEP (confidence HIGH)
- **Rationale:** The unmanned and counter-UAS defense segment, distinct from legacy platform primes. No neighbour is flagged, and civil_uas_low_altitude_economy holds the civil side apart.
- **Name quality:** Matches the scope; no naming defect found.
- **Parent paths:** `theme:industrials_defense>theme:defense_aerospace>theme:autonomous_systems_counter_uas`
- **Asserted on / nominated from:** 2026-10-08 / `research:research/defense_intelligence/D0R_DEFENSE_EQUITY_DRIVER_TAXONOMY.md`
- **Crosswalk note:** "Unmanned and autonomous capability segment distinct from legacy platform primes."
- **scope_version:** `1f23493ee9f25819fbe40b1d76e00c8a8d2e02ab211408a549f668c6e1a7658f`
- **Baseline coverage:** EMPTY; admitted 0, proposed 0, rejected 0; vendor routes 0, vendor member companies 0; research records none; route kinds none
- **Member companies (probation lane):** none
- **Siblings:** 26 micros share a parent; frozen siblings: `theme:aerospace_components_aftermarket`, `theme:defense_sensors_electronics_c2`, `theme:military_space_communications`, `theme:missile_propulsion_supply`, `theme:missiles_munitions_effects`, `theme:naval_shipbuilding`
- **Gate-2 provenance markers:** none
- **Flagged by rule:** none

| nearest neighbour | tier | composite | name_jac | def_jac | name_char3 | zh_bigram | shared parent | shared members |
|---|---|---|---|---|---|---|---|---|
| `theme:ground_combat_systems` | DISPLAY_EXPANSION | 0.188 | 0.111 | 0.067 | 0.161 | 0.0 | yes | 0 |
| `theme:civil_uas_low_altitude_economy` | DISPLAY_EXPANSION | 0.174 | 0.1 | 0.259 | 0.23 | 0.143 | no | 0 |
| `theme:air_missile_defense_systems` | DISPLAY_EXPANSION | 0.167 | 0.1 | 0.036 | 0.033 | 0.083 | yes | 0 |
| `theme:undersea_systems_sonar` | DISPLAY_EXPANSION | 0.166 | 0.111 | 0.037 | 0.0 | 0.091 | yes | 0 |
| `theme:defense_photonics_eo_ir` | DISPLAY_EXPANSION | 0.163 | 0.1 | 0.028 | 0.032 | 0.071 | yes | 0 |

Referenced by:

- `theme:civil_uas_low_altitude_economy` (DISPLAY_EXPANSION): "...ass platforms and UTM traffic services under low-altitude regulation; autonomous_systems_counter_uas (defense_aerospace) is the military/counter segment."

### micro-cardiorenal_metabolic_indications

`theme:cardiorenal_metabolic_indications`: Cardiorenal and metabolic indications / 心肾与代谢适应症

- **Proposed disposition:** KEEP (confidence LOW, LOW-CONFIDENCE)
- **Rationale:** An indication-expansion scope (cardiorenal and metabolic outcomes beyond weight loss). It is coherent as a demand driver, but its likely issuers are the same incretin sponsors, so it may not separate as an investable set. Revisit as a MERGE into glp1_incretin_therapies, or a RENAME, once it has members.
- **Name quality:** Matches the scope; no naming defect found.
- **Parent paths:** `theme:healthcare_lifesciences>theme:glp1_obesity>theme:cardiorenal_metabolic_indications`
- **Asserted on / nominated from:** 2026-10-08 / `research:config/theme_thesis_registry.yml`
- **Crosswalk note:** "Adjacent indication expansion beyond weight loss alone."
- **scope_version:** `0f6cd9aaeaa9ec5687b6b510a49b7eee49ad5c8cb3ecd4027b87aec553839b36`
- **Baseline coverage:** EMPTY; admitted 0, proposed 0, rejected 0; vendor routes 0, vendor member companies 0; research records none; route kinds none
- **Member companies (probation lane):** none
- **Siblings:** 16 micros share a parent; frozen siblings: `theme:fill_finish_delivery_devices`, `theme:glp1_api_manufacturing`, `theme:glp1_incretin_therapies`, `theme:oral_glp1_formulations`
- **Gate-2 provenance markers:** none
- **Flagged by rule:** none

| nearest neighbour | tier | composite | name_jac | def_jac | name_char3 | zh_bigram | shared parent | shared members |
|---|---|---|---|---|---|---|---|---|
| `theme:metabolic_bariatric_surgery` | DISPLAY_EXPANSION | 0.26 | 0.2 | 0.038 | 0.305 | 0.1 | yes | 0 |
| `theme:oral_glp1_formulations` | FROZEN_ACCEPTANCE | 0.141 | 0.0 | 0.0 | 0.206 | 0.0 | yes | 0 |
| `theme:amylin_cagri_analogues` | DISPLAY_EXPANSION | 0.129 | 0.0 | 0.043 | 0.09 | 0.0 | yes | 0 |
| `theme:digital_titration_adherence` | DISPLAY_EXPANSION | 0.127 | 0.0 | 0.0 | 0.137 | 0.0 | yes | 0 |
| `theme:medical_nutrition_meal_replacement` | DISPLAY_EXPANSION | 0.124 | 0.0 | 0.025 | 0.091 | 0.0 | yes | 0 |

Referenced by: none.

### micro-cloud_security

`theme:cloud_security`: Cloud security / 云安全

- **Proposed disposition:** KEEP (confidence HIGH)
- **Rationale:** Cloud-workload protection is bought as its own security category. The flags against endpoint (0.397), network (0.390), email and application security come from shared vocabulary under one parent, and every one of those rows defines itself by a different protected surface.
- **Name quality:** Matches the scope; no naming defect found.
- **Parent paths:** `theme:technology_software>theme:cybersecurity>theme:cloud_security`
- **Asserted on / nominated from:** 2026-10-08 / `basket:baskets:cybersecurity`
- **Crosswalk note:** "Protection for cloud workloads and the attack surface that cloud migration opens."
- **scope_version:** `51af3fb0738a1a9586d69b8c695eeb9c31c205799c64d69f18f408d1432e1151`
- **Baseline coverage:** EMPTY; admitted 0, proposed 0, rejected 0; vendor routes 0, vendor member companies 0; research records none; route kinds none
- **Member companies (probation lane):** none
- **Siblings:** 24 micros share a parent; frozen siblings: `theme:endpoint_security`, `theme:identity_access_management`, `theme:network_security`
- **Gate-2 provenance markers:** none
- **Flagged by rule:** `theme:endpoint_security` (0.397), `theme:network_security` (0.39), `theme:email_collaboration_security` (0.332), `theme:application_security_devsecops` (0.319)

| nearest neighbour | tier | composite | name_jac | def_jac | name_char3 | zh_bigram | shared parent | shared members |
|---|---|---|---|---|---|---|---|---|
| `theme:endpoint_security` | FROZEN_ACCEPTANCE | 0.397 | 0.333 | 0.105 | 0.519 | 0.25 | yes | 0 |
| `theme:network_security` | FROZEN_ACCEPTANCE | 0.39 | 0.333 | 0.133 | 0.535 | 0.167 | yes | 0 |
| `theme:email_collaboration_security` | DISPLAY_EXPANSION | 0.332 | 0.25 | 0.12 | 0.404 | 0.167 | yes | 0 |
| `theme:application_security_devsecops` | DISPLAY_EXPANSION | 0.319 | 0.25 | 0.071 | 0.425 | 0.143 | yes | 0 |
| `theme:data_security_privacy_governance` | DISPLAY_EXPANSION | 0.296 | 0.2 | 0.103 | 0.378 | 0.125 | yes | 0 |

Referenced by:

- `theme:application_security_devsecops` (DISPLAY_EXPANSION): "...code/API testing inside development pipelines; endpoint_security and cloud_security protect running systems, this row secures software before it ships."
- `theme:data_security_privacy_governance` (DISPLAY_EXPANSION): "...classification, DLP, privacy rights, cross-border transfer evidence; cloud_security protects workloads and IAM controls who acts - this row enforces data..."

### micro-collaborative_robot_arms

`theme:collaborative_robot_arms`: Collaborative robot arms / 协作机械臂

- **Proposed disposition:** KEEP (confidence MEDIUM)
- **Rationale:** This is the highest-scoring frozen pair (industrial_robot_arms, 0.547). The two notes define each other by exclusion: cobots for high-mix work, fixed arms for high-volume automation. The adoption drivers differ. Several arm makers sell both, so the member sets may converge; that is a reason to watch the pair, not to merge it now.
- **Name quality:** Matches the scope; no naming defect found.
- **Parent paths:** `theme:industrials_defense>theme:robotics_automation>theme:collaborative_robot_arms`; `theme:industrials_defense>theme:robotics_automation>theme:robot_arm_systems>theme:collaborative_robot_arms`
- **Asserted on / nominated from:** 2026-10-08 / `research:config/theme_thesis_registry.yml`
- **Crosswalk note:** "Cobot form factor for high-mix manufacturing distinct from fixed automation."
- **scope_version:** `2e5712bc7ad26d4e505837721d4c928b6043a612fcc66784e9cdbc8455fa8219`
- **Baseline coverage:** EMPTY; admitted 0, proposed 0, rejected 0; vendor routes 0, vendor member companies 0; research records none; route kinds intermediate
- **Member companies (probation lane):** none
- **Siblings:** 25 micros share a parent; frozen siblings: `theme:industrial_motion_controls`, `theme:industrial_robot_arms`, `theme:machine_vision`, `theme:precision_actuators_servo_motors`, `theme:surgical_robotics_systems`
- **Gate-2 provenance markers:** none
- **Flagged by rule:** `theme:industrial_robot_arms` (0.547)

| nearest neighbour | tier | composite | name_jac | def_jac | name_char3 | zh_bigram | shared parent | shared members |
|---|---|---|---|---|---|---|---|---|
| `theme:industrial_robot_arms` | FROZEN_ACCEPTANCE | 0.547 | 0.5 | 0.467 | 0.445 | 0.333 | yes | 0 |
| `theme:laboratory_automation_robots` | DISPLAY_EXPANSION | 0.262 | 0.167 | 0.115 | 0.373 | 0.0 | yes | 0 |
| `theme:humanoid_embodied_robots` | DISPLAY_EXPANSION | 0.243 | 0.167 | 0.214 | 0.157 | 0.0 | yes | 0 |
| `theme:robot_simulation_digital_twin` | DISPLAY_EXPANSION | 0.229 | 0.167 | 0.1 | 0.227 | 0.0 | yes | 0 |
| `theme:professional_service_robots` | DISPLAY_EXPANSION | 0.217 | 0.2 | 0.03 | 0.196 | 0.0 | yes | 0 |

Referenced by:

- `theme:humanoid_embodied_robots` (DISPLAY_EXPANSION): "...with whole-body control and foundation-model integration; industrial/collaborative_robot_arms are fixed-base single-task arms."

### micro-conventional_dram

`theme:conventional_dram`: Conventional DRAM (non-HBM) / 常规 DRAM（非 HBM）

- **Proposed disposition:** KEEP (confidence HIGH)
- **Rationale:** The commodity DDR/DIMM product path, explicitly separated from HBM. No neighbour is flagged. Five expansion rows (CXL expansion, LPDRAM, memory interface chips, memory wafer fab, niche memory) define themselves against it.
- **Name quality:** Matches the scope; no naming defect found.
- **Parent paths:** `theme:semiconductors_hardware>theme:memory_storage>theme:conventional_dram`
- **Asserted on / nominated from:** 2026-10-08 / `research:config/theme_thesis_registry.yml`
- **Crosswalk note:** "Commodity DRAM product path separate from HBM-dominant AI memory framing."
- **scope_version:** `9754e97b089846195b7f2fd84d7f3b6fb2279341f160c82151874ebd81f795e6`
- **Baseline coverage:** EMPTY; admitted 0, proposed 0, rejected 0; vendor routes 0, vendor member companies 0; research records none; route kinds none
- **Member companies (probation lane):** none
- **Siblings:** 20 micros share a parent; frozen siblings: `theme:hbm_packaging`, `theme:nand_enterprise_storage`
- **Gate-2 provenance markers:** none
- **Flagged by rule:** none

| nearest neighbour | tier | composite | name_jac | def_jac | name_char3 | zh_bigram | shared parent | shared members |
|---|---|---|---|---|---|---|---|---|
| `theme:memory_wafer_fab` | DISPLAY_EXPANSION | 0.219 | 0.1 | 0.133 | 0.253 | 0.0 | yes | 0 |
| `theme:niche_memory_products` | DISPLAY_EXPANSION | 0.214 | 0.111 | 0.185 | 0.146 | 0.0 | yes | 0 |
| `theme:hbm_packaging` | FROZEN_ACCEPTANCE | 0.197 | 0.167 | 0.05 | 0.128 | 0.0 | yes | 0 |
| `theme:persistent_memory_scm` | DISPLAY_EXPANSION | 0.152 | 0.0 | 0.179 | 0.036 | 0.0 | yes | 0 |
| `theme:memory_assembly_test` | DISPLAY_EXPANSION | 0.148 | 0.0 | 0.192 | 0.0 | 0.0 | yes | 0 |

Referenced by:

- `theme:cxl_memory_expansion_devices` (DISPLAY_EXPANSION): "Memory decoupled from host DIMM slots over CXL; distinct from conventional_dram (standard DIMMs) and pcie_fabric_silicon (generic fabric)."
- `theme:lpdram_low_power_memory` (DISPLAY_EXPANSION): "Low-power mobile/packaged DRAM class; distinct from conventional_dram (server/PC DDR DIMM path)."
- `theme:memory_interface_chips` (DISPLAY_EXPANSION): "...nion silicon around server DRAM per JEDEC module specs; distinct from conventional_dram (the DRAM itself) and SSD controllers (storage side)."
- `theme:memory_wafer_fab` (DISPLAY_EXPANSION): "Fab-process production layer (node migration, yield); conventional_dram/nand_enterprise_storage are product segments. Distinct from advanced_..."
- `theme:niche_memory_products` (DISPLAY_EXPANSION): "...g-node specialty lines with long lifecycle commitments; distinct from conventional_dram (commodity mainstream) and persistent_memory_scm (new media classes)."

### micro-copper_mining

`theme:copper_mining`: Copper mining / 铜矿开采

- **Proposed disposition:** KEEP (confidence HIGH)
- **Rationale:** The mine and concentrate stage. The only flag, refined_copper (0.383), is the next stage, and both notes say so. Miners earn the metal price; smelters earn treatment and refining charges. Those are different mechanisms.
- **Name quality:** Matches the scope; no naming defect found.
- **Parent paths:** `theme:industrials_defense>theme:copper_steel_electrify>theme:copper_mining`; `theme:industrials_defense>theme:copper_steel_electrify>theme:copper_supply_chain>theme:copper_mining`; `theme:materials_mining>theme:copper_steel_electrify>theme:copper_mining`; `theme:materials_mining>theme:copper_steel_electrify>theme:copper_supply_chain>theme:copper_mining`
- **Asserted on / nominated from:** 2026-10-08 / `research:config/theme_pathways.yml`
- **Crosswalk note:** "Mine and concentrate supply stage, distinct from cathode refining and from wire or cable fabrication."
- **scope_version:** `8659b1d358b42ba8d7cf04b5d254050edecbb7a6033f94ff46d4d5bcbc6c62d7`
- **Baseline coverage:** EMPTY; admitted 0, proposed 0, rejected 0; vendor routes 0, vendor member companies 0; research records none; route kinds intermediate
- **Member companies (probation lane):** none
- **Siblings:** 17 micros share a parent; frozen siblings: `theme:copper_wire_cable`, `theme:refined_copper`, `theme:structural_steel_electrification`
- **Gate-2 provenance markers:** none
- **Flagged by rule:** `theme:refined_copper` (0.383)

| nearest neighbour | tier | composite | name_jac | def_jac | name_char3 | zh_bigram | shared parent | shared members |
|---|---|---|---|---|---|---|---|---|
| `theme:refined_copper` | FROZEN_ACCEPTANCE | 0.383 | 0.25 | 0.5 | 0.355 | 0.0 | yes | 0 |
| `theme:copper_wire_cable` | FROZEN_ACCEPTANCE | 0.299 | 0.25 | 0.154 | 0.363 | 0.0 | yes | 0 |
| `theme:secondary_copper_smelting` | DISPLAY_EXPANSION | 0.284 | 0.2 | 0.136 | 0.399 | 0.0 | yes | 0 |
| `theme:copper_solvent_extraction_ew` | DISPLAY_EXPANSION | 0.276 | 0.143 | 0.208 | 0.372 | 0.0 | yes | 0 |
| `theme:copper_mill_products` | DISPLAY_EXPANSION | 0.252 | 0.143 | 0.154 | 0.319 | 0.0 | yes | 0 |

Referenced by: none.

### micro-copper_wire_cable

`theme:copper_wire_cable`: Copper wire and cable / 铜线电缆

- **Proposed disposition:** KEEP (confidence HIGH)
- **Rationale:** Building and industrial wire, cable and busbar fabrication. Its note routes high-voltage transmission cable to transmission_hvdc_cabling, so the boundary is explicit. No neighbour is flagged.
- **Name quality:** Matches the scope; no naming defect found.
- **Parent paths:** `theme:industrials_defense>theme:copper_steel_electrify>theme:copper_supply_chain>theme:copper_wire_cable`; `theme:industrials_defense>theme:copper_steel_electrify>theme:copper_wire_cable`; `theme:materials_mining>theme:copper_steel_electrify>theme:copper_supply_chain>theme:copper_wire_cable`; `theme:materials_mining>theme:copper_steel_electrify>theme:copper_wire_cable`
- **Asserted on / nominated from:** 2026-10-08 / `research:config/theme_thesis_registry.yml`
- **Crosswalk note:** "Building and industrial copper wire, cable and busbar fabrication; high-voltage transmission cable systems belong under grid_electrification:transmission_hvdc_cabling (lane C1)."
- **scope_version:** `64779253d42bb3f1fe33b47ef3fbf2f5f1b851930ff27c74303f3866d2385a35`
- **Baseline coverage:** EMPTY; admitted 0, proposed 0, rejected 0; vendor routes 0, vendor member companies 0; research records none; route kinds intermediate
- **Member companies (probation lane):** none
- **Siblings:** 17 micros share a parent; frozen siblings: `theme:copper_mining`, `theme:refined_copper`, `theme:structural_steel_electrification`
- **Gate-2 provenance markers:** none
- **Flagged by rule:** none

| nearest neighbour | tier | composite | name_jac | def_jac | name_char3 | zh_bigram | shared parent | shared members |
|---|---|---|---|---|---|---|---|---|
| `theme:copper_mining` | FROZEN_ACCEPTANCE | 0.299 | 0.25 | 0.154 | 0.363 | 0.0 | yes | 0 |
| `theme:refined_copper` | FROZEN_ACCEPTANCE | 0.284 | 0.2 | 0.16 | 0.372 | 0.0 | yes | 0 |
| `theme:magnet_winding_wire` | DISPLAY_EXPANSION | 0.24 | 0.2 | 0.091 | 0.238 | 0.0 | yes | 0 |
| `theme:copper_mill_products` | DISPLAY_EXPANSION | 0.223 | 0.125 | 0.118 | 0.251 | 0.0 | yes | 0 |
| `theme:copper_solvent_extraction_ew` | DISPLAY_EXPANSION | 0.219 | 0.125 | 0.028 | 0.342 | 0.0 | yes | 0 |

Referenced by: none.

### micro-critical_mineral_mining_development

`theme:critical_mineral_mining_development`: Critical-mineral mining and development / 关键矿产开采与开发

- **Proposed disposition:** KEEP (confidence LOW, LOW-CONFIDENCE)
- **Rationale:** The producer and developer layer for critical minerals. It is coherent but broad: there are three flags, the top one ree_exploration_resource_definition (0.370), all expansion rows. A per-commodity SPLIT was considered and not proposed, because the policy mechanism (state support for domestic producers) is shared. Revisit if member sets diverge by commodity.
- **Name quality:** Matches the scope; no naming defect found.
- **Parent paths:** `theme:materials_mining>theme:rare_earth_critical_min>theme:critical_mineral_mining_development`
- **Asserted on / nominated from:** 2026-10-08 / `basket:baskets:critical_minerals`
- **Crosswalk note:** "Basket thesis names the producer/developer segment policy treats as the direct beneficiary layer."
- **scope_version:** `aaf42d65c27249364c9b91de3c2cc560fa8503b276d7cadfe3e77a8356946a3e`
- **Baseline coverage:** EMPTY; admitted 0, proposed 0, rejected 0; vendor routes 0, vendor member companies 0; research records none; route kinds none
- **Member companies (probation lane):** none
- **Siblings:** 19 micros share a parent; frozen siblings: `theme:gallium_germanium_supply_chain`, `theme:ndfeb_permanent_magnets`, `theme:rare_earth_separation_refining`
- **Gate-2 provenance markers:** none
- **Flagged by rule:** `theme:ree_exploration_resource_definition` (0.37), `theme:critical_min_substitution` (0.353), `theme:critical_min_byproduct_recovery` (0.35)

| nearest neighbour | tier | composite | name_jac | def_jac | name_char3 | zh_bigram | shared parent | shared members |
|---|---|---|---|---|---|---|---|---|
| `theme:ree_exploration_resource_definition` | DISPLAY_EXPANSION | 0.37 | 0.2 | 0.233 | 0.478 | 0.231 | yes | 0 |
| `theme:critical_min_substitution` | DISPLAY_EXPANSION | 0.353 | 0.286 | 0.059 | 0.462 | 0.231 | yes | 0 |
| `theme:critical_min_byproduct_recovery` | DISPLAY_EXPANSION | 0.35 | 0.25 | 0.091 | 0.497 | 0.2 | yes | 0 |
| `theme:heavy_mineral_sands_monazite` | DISPLAY_EXPANSION | 0.225 | 0.125 | 0.059 | 0.267 | 0.067 | yes | 0 |
| `theme:natural_graphite_processing` | DISPLAY_EXPANSION | 0.219 | 0.125 | 0.067 | 0.292 | 0.0 | yes | 0 |

Referenced by:

- `theme:ree_exploration_resource_definition` (DISPLAY_EXPANSION): "...cal-mineral assets, upstream of the producer/developer layer named by critical_mineral_mining_development, with no operating-mine output."

### micro-custom_asic_silicon

`theme:custom_asic_silicon`: Custom ASIC accelerators / 定制 ASIC 加速芯片

- **Proposed disposition:** KEEP (confidence HIGH)
- **Rationale:** Custom ASIC programs and merchant GPUs (gpu_merchant_accelerators, 0.491) are an explicit mutual distinction with different economics: design services plus volume on one side, merchant pricing on the other.
- **Name quality:** Matches the scope; no naming defect found.
- **Parent paths:** `theme:semiconductors_hardware>theme:ai_semiconductors>theme:ai_compute_silicon>theme:custom_asic_silicon`; `theme:semiconductors_hardware>theme:ai_semiconductors>theme:custom_asic_silicon`; `theme:technology_software>theme:ai_semiconductors>theme:ai_compute_silicon>theme:custom_asic_silicon`; `theme:technology_software>theme:ai_semiconductors>theme:custom_asic_silicon`
- **Asserted on / nominated from:** 2026-10-08 / `basket:baskets:ai_semiconductors`
- **Crosswalk note:** "Custom ASIC compute programs, distinct from merchant GPU and merchant accelerator silicon."
- **scope_version:** `977a5d5ded3928a01d919e47ebed6484d970ee00e2e8040a8d4c1be0036aca87`
- **Baseline coverage:** EMPTY; admitted 0, proposed 0, rejected 0; vendor routes 0, vendor member companies 0; research records none; route kinds intermediate
- **Member companies (probation lane):** none
- **Siblings:** 24 micros share a parent; frozen siblings: `theme:ai_interconnect_silicon`, `theme:gpu_merchant_accelerators`, `theme:hbm_packaging`
- **Gate-2 provenance markers:** none
- **Flagged by rule:** `theme:gpu_merchant_accelerators` (0.491)

| nearest neighbour | tier | composite | name_jac | def_jac | name_char3 | zh_bigram | shared parent | shared members |
|---|---|---|---|---|---|---|---|---|
| `theme:gpu_merchant_accelerators` | FROZEN_ACCEPTANCE | 0.491 | 0.143 | 0.636 | 0.48 | 0.429 | yes | 0 |
| `theme:ai_interconnect_silicon` | FROZEN_ACCEPTANCE | 0.215 | 0.143 | 0.143 | 0.035 | 0.111 | yes | 0 |
| `theme:pcie_fabric_silicon` | DISPLAY_EXPANSION | 0.194 | 0.143 | 0.053 | 0.04 | 0.111 | yes | 0 |
| `theme:ai_power_delivery_silicon` | DISPLAY_EXPANSION | 0.183 | 0.143 | 0.043 | 0.0 | 0.111 | yes | 0 |
| `theme:edge_inference_processors` | DISPLAY_EXPANSION | 0.181 | 0.0 | 0.176 | 0.075 | 0.111 | yes | 0 |

Referenced by:

- `theme:eda_design_automation` (DISPLAY_EXPANSION): "Design tooling enabler; custom_asic_silicon/gpu_merchant_accelerators are chip products, this is the software the..."

### micro-defense_sensors_electronics_c2

`theme:defense_sensors_electronics_c2`: Defense sensors, electronics and C2 / 国防传感器、电子与指控

- **Proposed disposition:** KEEP (confidence HIGH)
- **Rationale:** The radar, EW and C2 mission-electronics integration layer. The flag defense_microelectronics (0.332, expansion) is the silicon beneath it, and its own note says so. Three expansion rows use this boundary.
- **Name quality:** Matches the scope; no naming defect found.
- **Parent paths:** `theme:industrials_defense>theme:defense_aerospace>theme:defense_sensors_electronics_c2`
- **Asserted on / nominated from:** 2026-10-08 / `research:config/theme_pathways.yml`
- **Crosswalk note:** "Radar, electronic warfare, C2 and mission electronics layer under platform modernization."
- **scope_version:** `ddd27d1c6a8fd26aa0084071c77bfea078a31c81a66835ebb991fd06dcc2a61c`
- **Baseline coverage:** EMPTY; admitted 0, proposed 0, rejected 0; vendor routes 0, vendor member companies 0; research records none; route kinds none
- **Member companies (probation lane):** none
- **Siblings:** 26 micros share a parent; frozen siblings: `theme:aerospace_components_aftermarket`, `theme:autonomous_systems_counter_uas`, `theme:military_space_communications`, `theme:missile_propulsion_supply`, `theme:missiles_munitions_effects`, `theme:naval_shipbuilding`
- **Gate-2 provenance markers:** none
- **Flagged by rule:** `theme:defense_microelectronics` (0.332)

| nearest neighbour | tier | composite | name_jac | def_jac | name_char3 | zh_bigram | shared parent | shared members |
|---|---|---|---|---|---|---|---|---|
| `theme:defense_microelectronics` | DISPLAY_EXPANSION | 0.332 | 0.167 | 0.2 | 0.548 | 0.071 | yes | 0 |
| `theme:defense_photonics_eo_ir` | DISPLAY_EXPANSION | 0.276 | 0.125 | 0.161 | 0.389 | 0.071 | yes | 0 |
| `theme:defense_digital_it_services` | DISPLAY_EXPANSION | 0.264 | 0.125 | 0.24 | 0.236 | 0.067 | yes | 0 |
| `theme:cbrn_defense_equipment` | DISPLAY_EXPANSION | 0.243 | 0.167 | 0.111 | 0.284 | 0.0 | yes | 0 |
| `theme:defense_sustainment_mro` | DISPLAY_EXPANSION | 0.237 | 0.167 | 0.065 | 0.313 | 0.0 | yes | 0 |

Referenced by:

- `theme:defense_digital_it_services` (DISPLAY_EXPANSION): "...ion of the defense enterprise (networks, clouds, software factories); defense_sensors_electronics_c2 is weapon-system mission electronics - different estate."
- `theme:defense_microelectronics` (DISPLAY_EXPANSION): "Trusted/rad-hard silicon supply beneath systems; defense_sensors_electronics_c2 integrates mission electronics - this row supplies the accredited ups..."
- `theme:defense_photonics_eo_ir` (DISPLAY_EXPANSION): "...chain: IR focal planes, precision optics, lasers, night-vision tubes; defense_sensors_electronics_c2 covers radar/EW/C2 electronics - adjacent tiers, different physics."

### micro-diagnostic_reagents_kits

`theme:diagnostic_reagents_kits`: Diagnostic reagents and kits / 诊断试剂与试剂盒

- **Proposed disposition:** KEEP (confidence HIGH)
- **Rationale:** Recurring assay consumables, separated from capital instruments. The flag companion_diagnostics (0.306, expansion) is a test-paired-with-drug category, not a duplicate.
- **Name quality:** Matches the scope; no naming defect found.
- **Parent paths:** `theme:healthcare_lifesciences>theme:diagnostics_lifesci>theme:diagnostic_reagents_kits`
- **Asserted on / nominated from:** 2026-10-08 / `research:config/trade_flow_codes.yml`
- **Crosswalk note:** "Reagent kit trade line separates recurring assay volume from capital instruments."
- **scope_version:** `e185f88416540eef539bd0c4210681ae9dd17ff77cd6a475e6daa48a51536e9b`
- **Baseline coverage:** EMPTY; admitted 0, proposed 0, rejected 0; vendor routes 0, vendor member companies 0; research records none; route kinds none
- **Member companies (probation lane):** none
- **Siblings:** 19 micros share a parent; frozen siblings: `theme:genomic_sequencing`, `theme:life_science_lab_instruments`, `theme:liquid_biopsy_assays`, `theme:proteomics_discovery_platforms`
- **Gate-2 provenance markers:** none
- **Flagged by rule:** `theme:companion_diagnostics` (0.306)

| nearest neighbour | tier | composite | name_jac | def_jac | name_char3 | zh_bigram | shared parent | shared members |
|---|---|---|---|---|---|---|---|---|
| `theme:companion_diagnostics` | DISPLAY_EXPANSION | 0.306 | 0.25 | 0.074 | 0.359 | 0.143 | yes | 0 |
| `theme:lifesci_raw_reagents` | DISPLAY_EXPANSION | 0.258 | 0.111 | 0.179 | 0.296 | 0.077 | yes | 0 |
| `theme:pcr_molecular_diagnostics` | DISPLAY_EXPANSION | 0.246 | 0.143 | 0.074 | 0.296 | 0.091 | yes | 0 |
| `theme:immunoassay_clinical_chemistry` | DISPLAY_EXPANSION | 0.157 | 0.0 | 0.154 | 0.0 | 0.091 | yes | 0 |
| `theme:life_science_lab_instruments` | FROZEN_ACCEPTANCE | 0.145 | 0.0 | 0.083 | 0.123 | 0.0 | yes | 0 |

Referenced by: none.

### micro-direct_to_device_connectivity

`theme:direct_to_device_connectivity`: Direct-to-device satellite connectivity / 手机直连卫星通信

- **Proposed disposition:** KEEP (confidence HIGH)
- **Rationale:** Satellite links built into handsets are a distinct extension of the market beyond dedicated terminals. No neighbour is flagged, and satellite_iot_ntn holds machine traffic apart.
- **Name quality:** Matches the scope; no naming defect found.
- **Parent paths:** `theme:industrials_defense>theme:space_satellite>theme:direct_to_device_connectivity`; `theme:industrials_defense>theme:space_satellite>theme:satellite_connectivity_services>theme:direct_to_device_connectivity`
- **Asserted on / nominated from:** 2026-10-08 / `basket:baskets:space_economy`
- **Crosswalk note:** "Handset-integrated satellite links that extend the market beyond dedicated terminals."
- **scope_version:** `b58b336f6865e72756eea27ff5efc3861b62575a0e310e1930b54d059fbfeb86`
- **Baseline coverage:** EMPTY; admitted 0, proposed 0, rejected 0; vendor routes 0, vendor member companies 0; research records none; route kinds intermediate
- **Member companies (probation lane):** none
- **Siblings:** 22 micros share a parent; frozen siblings: `theme:earth_observation`, `theme:launch_services`, `theme:military_space_communications`, `theme:satellite_broadband_services`, `theme:satellite_ground_terminals`
- **Gate-2 provenance markers:** none
- **Flagged by rule:** none

| nearest neighbour | tier | composite | name_jac | def_jac | name_char3 | zh_bigram | shared parent | shared members |
|---|---|---|---|---|---|---|---|---|
| `theme:military_space_communications` | FROZEN_ACCEPTANCE | 0.276 | 0.143 | 0.043 | 0.303 | 0.273 | yes | 0 |
| `theme:satellite_broadband_services` | FROZEN_ACCEPTANCE | 0.267 | 0.167 | 0.1 | 0.325 | 0.091 | yes | 0 |
| `theme:satellite_iot_ntn` | DISPLAY_EXPANSION | 0.249 | 0.143 | 0.179 | 0.271 | 0.0 | yes | 0 |
| `theme:satellite_components_payloads` | DISPLAY_EXPANSION | 0.247 | 0.167 | 0.034 | 0.319 | 0.083 | yes | 0 |
| `theme:satellite_ground_terminals` | FROZEN_ACCEPTANCE | 0.233 | 0.143 | 0.095 | 0.217 | 0.077 | yes | 0 |

Referenced by:

- `theme:satellite_iot_ntn` (DISPLAY_EXPANSION): "...affic over satellite under 3GPP NTN; satellite_broadband_services and direct_to_device_connectivity target broadband and handsets - different traffic class and devices."

### micro-earth_observation

`theme:earth_observation`: Earth observation / 对地观测

- **Proposed disposition:** KEEP (confidence HIGH)
- **Rationale:** Imaging and sensing data from orbit, distinct from communications. No neighbour is flagged. Geospatial analytics, PNT and space-situational-awareness rows define themselves against it.
- **Name quality:** Matches the scope; no naming defect found.
- **Parent paths:** `theme:industrials_defense>theme:space_satellite>theme:earth_observation`
- **Asserted on / nominated from:** 2026-10-08 / `basket:baskets:space_economy`
- **Crosswalk note:** "Imaging and sensing data from orbit, distinct from communications services."
- **scope_version:** `a1e8f9fbaf366ef686dd9af74f4ebf8bd0a990a72e6ff4a8289bf1e2fb4a9cb2`
- **Baseline coverage:** EMPTY; admitted 0, proposed 0, rejected 0; vendor routes 0, vendor member companies 0; research records none; route kinds none
- **Member companies (probation lane):** none
- **Siblings:** 22 micros share a parent; frozen siblings: `theme:direct_to_device_connectivity`, `theme:launch_services`, `theme:military_space_communications`, `theme:satellite_broadband_services`, `theme:satellite_ground_terminals`
- **Gate-2 provenance markers:** none
- **Flagged by rule:** none

| nearest neighbour | tier | composite | name_jac | def_jac | name_char3 | zh_bigram | shared parent | shared members |
|---|---|---|---|---|---|---|---|---|
| `theme:gnss_pnt_services` | DISPLAY_EXPANSION | 0.184 | 0.0 | 0.115 | 0.275 | 0.0 | yes | 0 |
| `theme:geospatial_analytics_platforms` | DISPLAY_EXPANSION | 0.183 | 0.0 | 0.3 | 0.042 | 0.0 | yes | 0 |
| `theme:rare_earth_separation_refining` | FROZEN_ACCEPTANCE | 0.162 | 0.2 | 0.048 | 0.399 | 0.0 | no | 0 |
| `theme:satellite_manufacturing_constellations` | DISPLAY_EXPANSION | 0.16 | 0.0 | 0.062 | 0.223 | 0.0 | yes | 0 |
| `theme:ground_station_networks_ttoc` | DISPLAY_EXPANSION | 0.153 | 0.0 | 0.032 | 0.227 | 0.0 | yes | 0 |

Referenced by:

- `theme:geospatial_analytics_platforms` (DISPLAY_EXPANSION): "...on tier consuming satellite data into insight products and platforms; earth_observation owns the imaging/sensing from orbit."
- `theme:gnss_pnt_services` (DISPLAY_EXPANSION): "...augmentation corrections, resilient timing; comms rows move bits and earth_observation images - this row positions."
- `theme:space_situational_awareness_debris` (DISPLAY_EXPANSION): "...ironment itself: catalogs, conjunction screening, collision warnings; earth_observation images Earth - different target, safety-of-flight purpose."

### micro-endpoint_security

`theme:endpoint_security`: Endpoint security / 终端安全

- **Proposed disposition:** KEEP (confidence HIGH)
- **Rationale:** Device-level protection is bought as its own category. The flags against network (0.398) and cloud (0.397) security come from shared vocabulary under one parent. Four expansion rows (AppSec, XDR, threat intelligence, exposure management) carve against it.
- **Name quality:** Matches the scope; no naming defect found.
- **Parent paths:** `theme:technology_software>theme:cybersecurity>theme:endpoint_security`
- **Asserted on / nominated from:** 2026-10-08 / `basket:baskets:cybersecurity`
- **Crosswalk note:** "Device-level protection, where behavioral and AI-native detection is replacing signature tools."
- **scope_version:** `9b5c3dbc19a1b1db3cc1d9f60f9a3d21261a48525ec07ec86838eceecb3218b3`
- **Baseline coverage:** EMPTY; admitted 0, proposed 0, rejected 0; vendor routes 0, vendor member companies 0; research records none; route kinds none
- **Member companies (probation lane):** none
- **Siblings:** 24 micros share a parent; frozen siblings: `theme:cloud_security`, `theme:identity_access_management`, `theme:network_security`
- **Gate-2 provenance markers:** none
- **Flagged by rule:** `theme:network_security` (0.398), `theme:cloud_security` (0.397), `theme:email_collaboration_security` (0.315), `theme:application_security_devsecops` (0.305)

| nearest neighbour | tier | composite | name_jac | def_jac | name_char3 | zh_bigram | shared parent | shared members |
|---|---|---|---|---|---|---|---|---|
| `theme:network_security` | FROZEN_ACCEPTANCE | 0.398 | 0.333 | 0.222 | 0.485 | 0.143 | yes | 0 |
| `theme:cloud_security` | FROZEN_ACCEPTANCE | 0.397 | 0.333 | 0.105 | 0.519 | 0.25 | yes | 0 |
| `theme:email_collaboration_security` | DISPLAY_EXPANSION | 0.315 | 0.25 | 0.1 | 0.367 | 0.143 | yes | 0 |
| `theme:application_security_devsecops` | DISPLAY_EXPANSION | 0.305 | 0.25 | 0.061 | 0.386 | 0.125 | yes | 0 |
| `theme:ai_model_security_governance` | DISPLAY_EXPANSION | 0.287 | 0.2 | 0.1 | 0.367 | 0.091 | yes | 0 |

Referenced by:

- `theme:application_security_devsecops` (DISPLAY_EXPANSION): "Shift-left code/API testing inside development pipelines; endpoint_security and cloud_security protect running systems, this row secures software..."
- `theme:extended_detection_response` (DISPLAY_EXPANSION): "...y analytics and response orchestration (XDR/SIEM/SOAR); distinct from endpoint_security, which protects the device itself rather than correlating signals acr..."
- `theme:threat_intelligence_cti` (DISPLAY_EXPANSION): "Produces curated adversary TTP/indicator knowledge; nearest rows endpoint_security and soc_mdr_services consume detection at surfaces - this row supplie..."
- `theme:vulnerability_exposure_management` (DISPLAY_EXPANSION): "...ness pipeline (CVE/CVSS/KEV-class scoring, attack-surface discovery); endpoint_security detects exploits at runtime, this row finds and prioritizes weaknesse..."

### micro-etch_deposition_equipment

`theme:etch_deposition_equipment`: Etch & deposition equipment / 刻蚀与沉积设备

- **Proposed disposition:** KEEP (confidence HIGH)
- **Rationale:** The core WFE process-tool class. Its flags, CMP (0.346) and ion implant (0.332), are expansion sibling tool classes, and each defines itself as distinct from this row.
- **Name quality:** Matches the scope; no naming defect found.
- **Parent paths:** `theme:semiconductors_hardware>theme:semicap_equipment>theme:etch_deposition_equipment`; `theme:semiconductors_hardware>theme:semicap_equipment>theme:wfe_process_tools>theme:etch_deposition_equipment`
- **Asserted on / nominated from:** 2026-10-08 / `research:config/theme_thesis_registry.yml`
- **Crosswalk note:** "Etch/deposition named as core WFE process steps."
- **scope_version:** `9a5ae1906ff3ec95e18042b5b9795a2b8f042be8cc97a5eb26d3c25b32d59762`
- **Baseline coverage:** EMPTY; admitted 0, proposed 0, rejected 0; vendor routes 0, vendor member companies 0; research records none; route kinds intermediate
- **Member companies (probation lane):** none
- **Siblings:** 18 micros share a parent; frozen siblings: `theme:lithography_tools`, `theme:process_metrology_inspection`, `theme:wafer_fab_subsystems`
- **Gate-2 provenance markers:** none
- **Flagged by rule:** `theme:cmp_planarization_equipment` (0.346), `theme:ion_implant_equipment` (0.332)

| nearest neighbour | tier | composite | name_jac | def_jac | name_char3 | zh_bigram | shared parent | shared members |
|---|---|---|---|---|---|---|---|---|
| `theme:cmp_planarization_equipment` | DISPLAY_EXPANSION | 0.346 | 0.2 | 0.188 | 0.5 | 0.143 | yes | 0 |
| `theme:ion_implant_equipment` | DISPLAY_EXPANSION | 0.332 | 0.2 | 0.158 | 0.5 | 0.111 | yes | 0 |
| `theme:epitaxy_thermal_equipment` | DISPLAY_EXPANSION | 0.287 | 0.167 | 0.182 | 0.313 | 0.1 | yes | 0 |
| `theme:wet_clean_equipment` | DISPLAY_EXPANSION | 0.272 | 0.125 | 0.2 | 0.3 | 0.091 | yes | 0 |
| `theme:coat_develop_track` | DISPLAY_EXPANSION | 0.269 | 0.167 | 0.05 | 0.378 | 0.111 | yes | 0 |

Referenced by:

- `theme:cmp_planarization_equipment` (DISPLAY_EXPANSION): "Mechanical-chemical polish platforms; distinct from etch_deposition_equipment and from cmp_polishing_consumables (consumables, not machine)."
- `theme:epitaxy_thermal_equipment` (DISPLAY_EXPANSION): "Epi reactors and oxidation/diffusion/RTP furnaces; distinct from etch_deposition_equipment (CVD/PVD/ALD tooling) and ion_implant_equipment (implantation)."
- `theme:ion_implant_equipment` (DISPLAY_EXPANSION): "Doping tool family; distinct from etch_deposition_equipment (remove/add material) and epitaxy_thermal_equipment (furnace growth/t..."
- `theme:wet_clean_equipment` (DISPLAY_EXPANSION): "Wet-chemistry process tools; distinct from etch_deposition_equipment (plasma dry processing) and fab_facility_systems (fab utilities)."

### micro-fill_finish_delivery_devices

`theme:fill_finish_delivery_devices`: Fill-finish and drug-delivery devices / 灌装封装与给药装置

- **Proposed disposition:** KEEP (confidence LOW, LOW-CONFIDENCE)
- **Rationale:** A coherent GLP-1 supply-bottleneck scope downstream of API. It pairs two mechanisms that may separate as investments: sterile fill-finish capacity (contract manufacturers) and pen or autoinjector devices. No SPLIT is proposed until the member sets show that divergence.
- **Name quality:** Matches the scope; no naming defect found.
- **Parent paths:** `theme:healthcare_lifesciences>theme:glp1_obesity>theme:fill_finish_delivery_devices`; `theme:healthcare_lifesciences>theme:glp1_obesity>theme:glp1_supply_chain>theme:fill_finish_delivery_devices`
- **Asserted on / nominated from:** 2026-10-08 / `research:config/theme_pathways.yml`
- **Crosswalk note:** "Manufacturing bottleneck segment for scaling GLP-1 supply."
- **scope_version:** `9b0fde7f3ad78e12a76c26d98b3cb56ed50a969a1b794f70e83bdc8bb97ef0d2`
- **Baseline coverage:** EMPTY; admitted 0, proposed 0, rejected 0; vendor routes 0, vendor member companies 0; research records none; route kinds intermediate
- **Member companies (probation lane):** none
- **Siblings:** 16 micros share a parent; frozen siblings: `theme:cardiorenal_metabolic_indications`, `theme:glp1_api_manufacturing`, `theme:glp1_incretin_therapies`, `theme:oral_glp1_formulations`
- **Gate-2 provenance markers:** none
- **Flagged by rule:** none

| nearest neighbour | tier | composite | name_jac | def_jac | name_char3 | zh_bigram | shared parent | shared members |
|---|---|---|---|---|---|---|---|---|
| `theme:infusion_chemo_delivery_devices` | DISPLAY_EXPANSION | 0.27 | 0.25 | 0.292 | 0.481 | 0.067 | no | 0 |
| `theme:oral_small_molecule_obesity` | DISPLAY_EXPANSION | 0.188 | 0.111 | 0.087 | 0.136 | 0.0 | yes | 0 |
| `theme:glp1_api_manufacturing` | FROZEN_ACCEPTANCE | 0.175 | 0.0 | 0.3 | 0.0 | 0.0 | yes | 0 |
| `theme:pharma_cold_chain_logistics` | DISPLAY_EXPANSION | 0.14 | 0.0 | 0.16 | 0.0 | 0.0 | yes | 0 |
| `theme:sharps_waste_services` | DISPLAY_EXPANSION | 0.131 | 0.0 | 0.037 | 0.11 | 0.0 | yes | 0 |

Referenced by: none.

### micro-fuel_cycle

`theme:fuel_cycle`: Fuel cycle / 核燃料循环

- **Proposed disposition:** RENAME (confidence MEDIUM)
- **Rationale:** The note scopes it to 'mining through enrichment', and three expansion rows (fuel_assembly_fabrication, haleu_advanced_fuel_supply, spent_fuel_management) carve fabrication, HALEU and the back end away from it. The name 'Fuel cycle / 核燃料循环' still claims the whole cycle. A SPLIT of mining from conversion and enrichment was considered (LOW-CONFIDENCE) and not proposed.
- **Proposed names:** EN "Nuclear fuel front end (mining to enrichment)" / ZH "核燃料循环前端（铀矿开采至浓缩）" (scope unchanged)
- **Name quality:** Misleading. The EN and ZH names claim the whole fuel cycle, but the scope and every referrer treat it as the front end only.
- **Parent paths:** `theme:energy_power>theme:nuclear_power>theme:fuel_cycle`
- **Asserted on / nominated from:** 2026-10-08 / `research:research/energy/nuclear_program/REG-PACKET-2026-09-25-nuclear_power.md`
- **Crosswalk note:** "REG-PACKET slice for mining through enrichment."
- **scope_version:** `3c2716940a6dd76be3857d887e1141cdbce5c2cd9dea43f541d7cb4167e9f37e`
- **Baseline coverage:** EMPTY; admitted 0, proposed 0, rejected 0; vendor routes 0, vendor member companies 0; research records none; route kinds none
- **Member companies (probation lane):** none
- **Siblings:** 17 micros share a parent; frozen siblings: `theme:nuclear_components`, `theme:reactor_technology`
- **Gate-2 provenance markers:** none
- **Flagged by rule:** `theme:fuel_assembly_fabrication` (0.349), `theme:haleu_advanced_fuel_supply` (0.307)

| nearest neighbour | tier | composite | name_jac | def_jac | name_char3 | zh_bigram | shared parent | shared members |
|---|---|---|---|---|---|---|---|---|
| `theme:fuel_assembly_fabrication` | DISPLAY_EXPANSION | 0.349 | 0.2 | 0.294 | 0.275 | 0.25 | yes | 0 |
| `theme:haleu_advanced_fuel_supply` | DISPLAY_EXPANSION | 0.307 | 0.2 | 0.278 | 0.248 | 0.091 | yes | 0 |
| `theme:triso_fuel_form_fabrication` | DISPLAY_EXPANSION | 0.274 | 0.143 | 0.15 | 0.308 | 0.125 | yes | 0 |
| `theme:spent_fuel_management` | DISPLAY_EXPANSION | 0.262 | 0.143 | 0.208 | 0.198 | 0.1 | yes | 0 |
| `theme:nuclear_components` | FROZEN_ACCEPTANCE | 0.173 | 0.0 | 0.231 | 0.075 | 0.0 | yes | 0 |

Referenced by:

- `theme:fuel_assembly_fabrication` (DISPLAY_EXPANSION): "...converting enriched product into qualified assemblies; distinct from fuel_cycle (scoped mining-through-enrichment)."
- `theme:haleu_advanced_fuel_supply` (DISPLAY_EXPANSION): "...gh-assay enrichment/supply layer for advanced reactors; distinct from fuel_cycle (legacy mining-through-enrichment LEU scope)."
- `theme:spent_fuel_management` (DISPLAY_EXPANSION): "BACK end of the cycle; the existing fuel_cycle row covers mining-through-enrichment (front end), so this adds an unc..."

### micro-gallium_germanium_supply_chain

`theme:gallium_germanium_supply_chain`: Gallium and germanium supply chain / 镓与锗供应链

- **Proposed disposition:** KEEP (confidence HIGH)
- **Rationale:** Export-controlled by-product metals form a distinct, policy-sensitive supply segment. No neighbour is flagged.
- **Name quality:** Matches the scope; no naming defect found.
- **Parent paths:** `theme:materials_mining>theme:rare_earth_critical_min>theme:gallium_germanium_supply_chain`
- **Asserted on / nominated from:** 2026-10-08 / `research:config/theme_thesis_registry.yml`
- **Crosswalk note:** "Export-control metals named alongside magnets as a distinct policy-sensitive supply segment."
- **scope_version:** `47044b14471602546e19cea1b3348ccd8d52d137d68cec8ee670ab09818a50d4`
- **Baseline coverage:** EMPTY; admitted 0, proposed 0, rejected 0; vendor routes 0, vendor member companies 0; research records none; route kinds none
- **Member companies (probation lane):** none
- **Siblings:** 19 micros share a parent; frozen siblings: `theme:critical_mineral_mining_development`, `theme:ndfeb_permanent_magnets`, `theme:rare_earth_separation_refining`
- **Gate-2 provenance markers:** none
- **Flagged by rule:** none

| nearest neighbour | tier | composite | name_jac | def_jac | name_char3 | zh_bigram | shared parent | shared members |
|---|---|---|---|---|---|---|---|---|
| `theme:fusion_supply_chain` | DISPLAY_EXPANSION | 0.247 | 0.333 | 0.115 | 0.382 | 0.125 | no | 0 |
| `theme:titanium_sponge_pigment` | DISPLAY_EXPANSION | 0.241 | 0.143 | 0.077 | 0.361 | 0.0 | yes | 0 |
| `theme:supply_chain_firmware_security` | DISPLAY_EXPANSION | 0.212 | 0.286 | 0.059 | 0.284 | 0.2 | no | 0 |
| `theme:energetics_explosives_supply` | DISPLAY_EXPANSION | 0.143 | 0.167 | 0.032 | 0.184 | 0.2 | no | 0 |
| `theme:ndfeb_permanent_magnets` | FROZEN_ACCEPTANCE | 0.143 | 0.0 | 0.091 | 0.101 | 0.0 | yes | 0 |

Referenced by: none.

### micro-genomic_sequencing

`theme:genomic_sequencing`: Genomic sequencing (NGS) / 基因测序（NGS）

- **Proposed disposition:** KEEP (confidence HIGH)
- **Rationale:** Sequencer instruments and their consumables. life_science_lab_instruments explicitly routes dedicated sequencers here. No neighbour is flagged.
- **Name quality:** Matches the scope; no naming defect found.
- **Parent paths:** `theme:healthcare_lifesciences>theme:diagnostics_lifesci>theme:genomic_sequencing`; `theme:healthcare_lifesciences>theme:diagnostics_lifesci>theme:multi_omics_platforms>theme:genomic_sequencing`
- **Asserted on / nominated from:** 2026-10-08 / `research:config/theme_thesis_registry.yml`
- **Crosswalk note:** "Sequencing instruments and their consumable revenue model; distinct from general lab instruments."
- **scope_version:** `5943f8f400c821d77e24e601fcd5bf29c5fe6cae53b29f1282ba722c5dab8d72`
- **Baseline coverage:** EMPTY; admitted 0, proposed 0, rejected 0; vendor routes 0, vendor member companies 0; research records none; route kinds intermediate
- **Member companies (probation lane):** none
- **Siblings:** 19 micros share a parent; frozen siblings: `theme:diagnostic_reagents_kits`, `theme:life_science_lab_instruments`, `theme:liquid_biopsy_assays`, `theme:proteomics_discovery_platforms`
- **Gate-2 provenance markers:** none
- **Flagged by rule:** none

| nearest neighbour | tier | composite | name_jac | def_jac | name_char3 | zh_bigram | shared parent | shared members |
|---|---|---|---|---|---|---|---|---|
| `theme:life_science_lab_instruments` | FROZEN_ACCEPTANCE | 0.177 | 0.0 | 0.278 | 0.036 | 0.0 | yes | 0 |
| `theme:oligo_gene_synthesis` | DISPLAY_EXPANSION | 0.148 | 0.0 | 0.042 | 0.078 | 0.111 | yes | 0 |
| `theme:proteomics_discovery_platforms` | FROZEN_ACCEPTANCE | 0.13 | 0.0 | 0.056 | 0.078 | 0.0 | yes | 0 |
| `theme:point_of_care_testing` | DISPLAY_EXPANSION | 0.129 | 0.0 | 0.04 | 0.093 | 0.0 | yes | 0 |
| `theme:diagnostic_reagents_kits` | FROZEN_ACCEPTANCE | 0.128 | 0.0 | 0.05 | 0.078 | 0.0 | yes | 0 |

Referenced by:

- `theme:life_science_lab_instruments` (FROZEN_ACCEPTANCE): "General R&D lab capital equipment; dedicated sequencers belong under genomic_sequencing."

### micro-glp1_api_manufacturing

`theme:glp1_api_manufacturing`: GLP-1 API manufacturing / GLP-1原料药生产

- **Proposed disposition:** KEEP (confidence HIGH)
- **Rationale:** Drug-substance capacity with multi-year lead times, upstream of fill-finish and devices. No neighbour is flagged.
- **Name quality:** Matches the scope; no naming defect found.
- **Parent paths:** `theme:healthcare_lifesciences>theme:glp1_obesity>theme:glp1_api_manufacturing`; `theme:healthcare_lifesciences>theme:glp1_obesity>theme:glp1_supply_chain>theme:glp1_api_manufacturing`
- **Asserted on / nominated from:** 2026-10-08 / `research:config/theme_thesis_registry.yml`
- **Crosswalk note:** "Drug-substance capacity with multi-year lead times, upstream of fill-finish and devices."
- **scope_version:** `72481bff0221f6943e3b77cd0ae696c41ea5010c5e43acea5bc3cc54c25ca869`
- **Baseline coverage:** EMPTY; admitted 0, proposed 0, rejected 0; vendor routes 0, vendor member companies 0; research records none; route kinds intermediate
- **Member companies (probation lane):** none
- **Siblings:** 16 micros share a parent; frozen siblings: `theme:cardiorenal_metabolic_indications`, `theme:fill_finish_delivery_devices`, `theme:glp1_incretin_therapies`, `theme:oral_glp1_formulations`
- **Gate-2 provenance markers:** none
- **Flagged by rule:** none

| nearest neighbour | tier | composite | name_jac | def_jac | name_char3 | zh_bigram | shared parent | shared members |
|---|---|---|---|---|---|---|---|---|
| `theme:glp1_incretin_therapies` | FROZEN_ACCEPTANCE | 0.299 | 0.333 | 0.125 | 0.255 | 0.0 | yes | 0 |
| `theme:oral_glp1_formulations` | FROZEN_ACCEPTANCE | 0.283 | 0.333 | 0.091 | 0.217 | 0.0 | yes | 0 |
| `theme:recombinant_peptide_fermentation` | DISPLAY_EXPANSION | 0.225 | 0.143 | 0.069 | 0.104 | 0.182 | yes | 0 |
| `theme:photomask_manufacturing` | DISPLAY_EXPANSION | 0.191 | 0.2 | 0.033 | 0.565 | 0.0 | no | 0 |
| `theme:pv_manufacturing_equipment` | DISPLAY_EXPANSION | 0.182 | 0.167 | 0.067 | 0.532 | 0.0 | no | 0 |

Referenced by: none.

### micro-glp1_incretin_therapies

`theme:glp1_incretin_therapies`: GLP-1 incretin therapies / GLP-1肠促胰岛素疗法

- **Proposed disposition:** RENAME (confidence MEDIUM)
- **Rationale:** The scope is the injectable incretin drug class: its sibling oral_glp1_formulations is 'distinct from injectable incretin platforms'. But the class-wide name also covers oral GLP-1s, which is the only flag (0.301). The expansion sibling `theme:multi_receptor_incretin_agonists` sets itself apart from "the single-receptor incretin therapy class", so the proposed name keeps the GLP-1-class meaning and must not read as "GLP-1 plus any incretin".
- **Proposed names:** EN "Injectable GLP-1 incretin therapies" / ZH "注射用 GLP-1 肠促胰岛素疗法" (scope unchanged)
- **Name quality:** Misleading. The class-wide name overlaps the oral sibling; the scope is injectable therapies.
- **Parent paths:** `theme:healthcare_lifesciences>theme:glp1_obesity>theme:glp1_incretin_therapies`; `theme:healthcare_lifesciences>theme:glp1_obesity>theme:glp1_therapy_products>theme:glp1_incretin_therapies`
- **Asserted on / nominated from:** 2026-10-08 / `basket:baskets:obesity_glp1`
- **Crosswalk note:** "Core incretin drug class named in the house obesity basket theme line."
- **scope_version:** `b7c98979b4f0705d169cb115b4342b9db2e612ebdaab614c55b85a8f225fdaf2`
- **Baseline coverage:** EMPTY; admitted 0, proposed 0, rejected 0; vendor routes 0, vendor member companies 0; research records none; route kinds intermediate
- **Member companies (probation lane):** none
- **Siblings:** 16 micros share a parent; frozen siblings: `theme:cardiorenal_metabolic_indications`, `theme:fill_finish_delivery_devices`, `theme:glp1_api_manufacturing`, `theme:oral_glp1_formulations`
- **Gate-2 provenance markers:** none
- **Flagged by rule:** `theme:oral_glp1_formulations` (0.301)

| nearest neighbour | tier | composite | name_jac | def_jac | name_char3 | zh_bigram | shared parent | shared members |
|---|---|---|---|---|---|---|---|---|
| `theme:oral_glp1_formulations` | FROZEN_ACCEPTANCE | 0.301 | 0.333 | 0.167 | 0.213 | 0.0 | yes | 0 |
| `theme:glp1_api_manufacturing` | FROZEN_ACCEPTANCE | 0.299 | 0.333 | 0.125 | 0.255 | 0.0 | yes | 0 |
| `theme:multi_receptor_incretin_agonists` | DISPLAY_EXPANSION | 0.241 | 0.125 | 0.167 | 0.276 | 0.0 | yes | 0 |
| `theme:oral_small_molecule_obesity` | DISPLAY_EXPANSION | 0.133 | 0.0 | 0.13 | 0.0 | 0.0 | yes | 0 |
| `theme:fill_finish_delivery_devices` | FROZEN_ACCEPTANCE | 0.13 | 0.0 | 0.095 | 0.032 | 0.0 | yes | 0 |

Referenced by: none.

### micro-gpu_merchant_accelerators

`theme:gpu_merchant_accelerators`: GPUs & merchant accelerators / GPU 与通用加速芯片

- **Proposed disposition:** KEEP (confidence HIGH)
- **Rationale:** Merchant GPU and accelerator silicon versus custom ASICs (0.491) is an explicit mutual distinction. Four expansion rows (server boards, EDA, edge inference, processing-in-memory) define themselves against it.
- **Name quality:** Matches the scope; no naming defect found.
- **Parent paths:** `theme:semiconductors_hardware>theme:ai_semiconductors>theme:ai_compute_silicon>theme:gpu_merchant_accelerators`; `theme:semiconductors_hardware>theme:ai_semiconductors>theme:gpu_merchant_accelerators`; `theme:technology_software>theme:ai_semiconductors>theme:ai_compute_silicon>theme:gpu_merchant_accelerators`; `theme:technology_software>theme:ai_semiconductors>theme:gpu_merchant_accelerators`
- **Asserted on / nominated from:** 2026-10-08 / `basket:baskets:ai_semiconductors`
- **Crosswalk note:** "Merchant GPU and off-the-shelf accelerator silicon, distinct from custom ASIC programs."
- **scope_version:** `650bfac874523220eefe5370981f8d39c16be81b868469014f3d072088beeefa`
- **Baseline coverage:** EMPTY; admitted 0, proposed 0, rejected 0; vendor routes 0, vendor member companies 0; research records none; route kinds intermediate
- **Member companies (probation lane):** none
- **Siblings:** 24 micros share a parent; frozen siblings: `theme:ai_interconnect_silicon`, `theme:custom_asic_silicon`, `theme:hbm_packaging`
- **Gate-2 provenance markers:** none
- **Flagged by rule:** `theme:custom_asic_silicon` (0.491)

| nearest neighbour | tier | composite | name_jac | def_jac | name_char3 | zh_bigram | shared parent | shared members |
|---|---|---|---|---|---|---|---|---|
| `theme:custom_asic_silicon` | FROZEN_ACCEPTANCE | 0.491 | 0.143 | 0.636 | 0.48 | 0.429 | yes | 0 |
| `theme:edge_inference_processors` | DISPLAY_EXPANSION | 0.19 | 0.0 | 0.158 | 0.143 | 0.111 | yes | 0 |
| `theme:eda_design_automation` | DISPLAY_EXPANSION | 0.163 | 0.0 | 0.25 | 0.0 | 0.0 | yes | 0 |
| `theme:ai_interconnect_silicon` | FROZEN_ACCEPTANCE | 0.144 | 0.0 | 0.059 | 0.033 | 0.111 | yes | 0 |
| `theme:ai_server_board_integration` | DISPLAY_EXPANSION | 0.141 | 0.0 | 0.136 | 0.034 | 0.0 | yes | 0 |

Referenced by:

- `theme:ai_server_board_integration` (DISPLAY_EXPANSION): "Accelerator carrier boards and server SKUs; distinct from gpu_merchant_accelerators (the chip) and from data_center_power power hardware."
- `theme:eda_design_automation` (DISPLAY_EXPANSION): "Design tooling enabler; custom_asic_silicon/gpu_merchant_accelerators are chip products, this is the software the design runs on. Adds the..."
- `theme:edge_inference_processors` (DISPLAY_EXPANSION): "Device-scale neural processors; distinct from gpu_merchant_accelerators (datacenter rack-scale accelerators)."
- `theme:processing_in_memory` (DISPLAY_EXPANSION): "...beside memory arrays; distinct from persistent_memory_scm (media) and gpu_merchant_accelerators (discrete accelerators)."

### micro-grid_distribution_automation

`theme:grid_distribution_automation`: Grid distribution automation / 电网配电自动化

- **Proposed disposition:** KEEP (confidence HIGH)
- **Rationale:** Feeder-level distribution automation. Its flags, grid_protection_substation_automation (0.405) and grid_dispatch_ems_software (0.306), are expansion rows that define themselves against it (substation; control centre). Their boundary with each other is recorded as expansion-tier follow-up.
- **Name quality:** Matches the scope; no naming defect found.
- **Parent paths:** `theme:energy_power>theme:grid_electrification>theme:grid_distribution_automation`
- **Asserted on / nominated from:** 2026-10-08 / `research:config/theme_thesis_registry.yml`
- **Crosswalk note:** "Distribution automation named separately from bulk transmission hardware."
- **scope_version:** `d2e6f365799a0de6a17db5ad7fc7c91fd46bcc0f22cc8beb6909df76b7d1f1d2`
- **Baseline coverage:** EMPTY; admitted 0, proposed 0, rejected 0; vendor routes 0, vendor member companies 0; research records none; route kinds none
- **Member companies (probation lane):** none
- **Siblings:** 21 micros share a parent; frozen siblings: `theme:hv_transformers_switchgear`, `theme:transmission_hvdc_cabling`
- **Gate-2 provenance markers:** none
- **Flagged by rule:** `theme:grid_protection_substation_automation` (0.405), `theme:grid_dispatch_ems_software` (0.306)

| nearest neighbour | tier | composite | name_jac | def_jac | name_char3 | zh_bigram | shared parent | shared members |
|---|---|---|---|---|---|---|---|---|
| `theme:grid_protection_substation_automation` | DISPLAY_EXPANSION | 0.405 | 0.333 | 0.15 | 0.603 | 0.154 | yes | 0 |
| `theme:grid_dispatch_ems_software` | DISPLAY_EXPANSION | 0.306 | 0.167 | 0.182 | 0.235 | 0.273 | yes | 0 |
| `theme:grid_storage_integration` | DISPLAY_EXPANSION | 0.25 | 0.167 | 0.04 | 0.35 | 0.056 | yes | 0 |
| `theme:robot_system_integration` | DISPLAY_EXPANSION | 0.231 | 0.167 | 0.077 | 0.564 | 0.2 | no | 0 |
| `theme:eda_design_automation` | DISPLAY_EXPANSION | 0.224 | 0.2 | 0.038 | 0.524 | 0.2 | no | 0 |

Referenced by:

- `theme:ami_smart_metering` (DISPLAY_EXPANSION): "Customer-end metering/data chain; distinct from grid_distribution_automation (feeder automation) and grid_asset_monitoring (network asset telemetr..."
- `theme:ev_charging_infrastructure` (DISPLAY_EXPANSION): "Road-electrification charging equipment/networks; distinct from grid_distribution_automation (feeders) and rail_traction_electrification (rail traction power)."
- `theme:grid_dispatch_ems_software` (DISPLAY_EXPANSION): "...rol-center EMS/SCADA and security-constrained dispatch; distinct from grid_distribution_automation (feeder hardware/software layer) — control-center system operation, n..."
- `theme:grid_protection_substation_automation` (DISPLAY_EXPANSION): "...850; distinct from hv_transformers_switchgear (primary apparatus) and grid_distribution_automation (feeder automation)."

### micro-hbm_packaging

`theme:hbm_packaging`: HBM & advanced packaging / HBM 与先进封装

- **Proposed disposition:** RENAME (confidence MEDIUM)
- **Rationale:** This is the only populated frozen micro (NATIVE_POPULATED, member co:us:MU). Its note scopes it to HBM stacking, and three expansion rows treat it as the HBM segment. But '& advanced packaging' collides with advanced_packaging_2_5d_3d (0.473, same parent). It is not a SPLIT, because logic advanced packaging already has its own row.
- **Proposed names:** EN "HBM memory stacking & packaging" / ZH "HBM 存储堆叠与封装" (scope unchanged)
- **Name quality:** Misleading. 'advanced packaging / 先进封装' collides with the logic packaging row; the scope is HBM stacking.
- **Parent paths:** `theme:semiconductors_hardware>theme:ai_semiconductors>theme:hbm_packaging`; `theme:semiconductors_hardware>theme:memory_storage>theme:hbm_packaging`; `theme:technology_software>theme:ai_semiconductors>theme:hbm_packaging`
- **Execution deferral:** this RENAME changes `scope_version`, so it is executed only at a qualified C01 cutover that preserves generation 040b and D2E acceptance; that cutover re-binds `actprop:287edbf7e04b8aba873b7493` (`co:us:MU`) in the same act.
- **Asserted on / nominated from:** 2026-10-08 / `research:config/theme_pathways.yml`
- **Crosswalk note:** "Federated vertical slice; HBM stacking is distinct from generic accelerator silicon."
- **scope_version:** `7b6bd278681b3ac55030fea6a3341e4bf9122b010c8fc947be17913cc128c1eb`
- **Baseline coverage:** NATIVE_POPULATED; admitted 1, proposed 1, rejected 0; vendor routes 0, vendor member companies 0; research records none; route kinds none
- **Member companies (probation lane):** `co:us:MU`
- **Siblings:** 44 micros share a parent; frozen siblings: `theme:ai_interconnect_silicon`, `theme:conventional_dram`, `theme:custom_asic_silicon`, `theme:gpu_merchant_accelerators`, `theme:nand_enterprise_storage`
- **Gate-2 provenance markers:** none
- **Flagged by rule:** `theme:advanced_packaging_2_5d_3d` (0.473), `theme:advanced_packaging_equipment` (0.372)

| nearest neighbour | tier | composite | name_jac | def_jac | name_char3 | zh_bigram | shared parent | shared members |
|---|---|---|---|---|---|---|---|---|
| `theme:advanced_packaging_2_5d_3d` | DISPLAY_EXPANSION | 0.473 | 0.286 | 0.174 | 0.649 | 0.5 | yes | 0 |
| `theme:advanced_packaging_equipment` | DISPLAY_EXPANSION | 0.372 | 0.4 | 0.08 | 0.631 | 0.429 | no | 0 |
| `theme:advanced_substrate_interposer` | DISPLAY_EXPANSION | 0.286 | 0.143 | 0.2 | 0.288 | 0.143 | yes | 0 |
| `theme:advanced_node_foundry` | DISPLAY_EXPANSION | 0.255 | 0.167 | 0.036 | 0.328 | 0.111 | yes | 0 |
| `theme:conventional_dram` | FROZEN_ACCEPTANCE | 0.197 | 0.167 | 0.05 | 0.128 | 0.0 | yes | 0 |

Referenced by:

- `theme:advanced_packaging_2_5d_3d` (DISPLAY_EXPANSION): "AI-LOGIC interposer/hybrid-bonding assembly; distinct from hbm_packaging, whose mechanism is HBM memory stacking and its packaging angle, not..."
- `theme:advanced_substrate_interposer` (DISPLAY_EXPANSION): "...interposers); distinct from advanced_packaging_2_5d_3d (assembly) and hbm_packaging (memory stacking segment)."
- `theme:memory_assembly_test` (DISPLAY_EXPANSION): "Back-end service layer across memory (incl. non-HBM); distinct from hbm_packaging (HBM segment framing) and ai_chip_osat (logic assembly)."

### micro-hv_transformers_switchgear

`theme:hv_transformers_switchgear`: HV transformers & switchgear / 高压变压器与开关设备

- **Proposed disposition:** KEEP (confidence HIGH)
- **Rationale:** The primary high-voltage apparatus bottleneck shared by data-centre and grid build-out. No neighbour is flagged. Seven expansion rows carve their scopes against it, the most-used boundary in the frozen set.
- **Name quality:** Matches the scope; no naming defect found.
- **Parent paths:** `theme:energy_power>theme:data_center_power>theme:hv_transformers_switchgear`; `theme:energy_power>theme:grid_electrification>theme:hv_transformers_switchgear`; `theme:technology_software>theme:data_center_power>theme:hv_transformers_switchgear`
- **Asserted on / nominated from:** 2026-10-08 / `research:config/theme_thesis_registry.yml`
- **Crosswalk note:** "Shared power-delivery bottleneck across campus and grid buildout (M3)."
- **scope_version:** `310607ab5a3a4305d6eefde801826befe2b4718eabf61bdfb38c2847e1c3bb58`
- **Baseline coverage:** EMPTY; admitted 0, proposed 0, rejected 0; vendor routes 0, vendor member companies 0; research records none; route kinds none
- **Member companies (probation lane):** none
- **Siblings:** 38 micros share a parent; frozen siblings: `theme:grid_distribution_automation`, `theme:liquid_cooling_thermal`, `theme:transmission_hvdc_cabling`, `theme:ups_power_conversion`
- **Gate-2 provenance markers:** none
- **Flagged by rule:** none

| nearest neighbour | tier | composite | name_jac | def_jac | name_char3 | zh_bigram | shared parent | shared members |
|---|---|---|---|---|---|---|---|---|
| `theme:uhv_transmission` | DISPLAY_EXPANSION | 0.199 | 0.0 | 0.111 | 0.232 | 0.125 | yes | 0 |
| `theme:transformer_core_laminations` | DISPLAY_EXPANSION | 0.17 | 0.167 | 0.077 | 0.318 | 0.143 | no | 0 |
| `theme:electrical_steel_core_materials` | DISPLAY_EXPANSION | 0.153 | 0.0 | 0.211 | 0.0 | 0.0 | yes | 0 |
| `theme:grid_protection_substation_automation` | DISPLAY_EXPANSION | 0.149 | 0.0 | 0.174 | 0.026 | 0.0 | yes | 0 |
| `theme:grid_interconnection_services` | DISPLAY_EXPANSION | 0.148 | 0.0 | 0.192 | 0.0 | 0.0 | yes | 0 |

Referenced by:

- `theme:ai_power_delivery_silicon` (DISPLAY_EXPANSION): "...wer silicon (multiphase, IVR); distinct from ups_power_conversion and hv_transformers_switchgear (facility power hardware)."
- `theme:busway_smart_pdu` (DISPLAY_EXPANSION): "In-building rack-level distribution hardware; distinct from hv_transformers_switchgear (utility-class equipment) and dc_hvdc_power_architecture (source arch..."
- `theme:electrical_steel_core_materials` (DISPLAY_EXPANSION): "Core material input to transformers; distinct from hv_transformers_switchgear (transformer/switchgear products) - upstream bottleneck layer."
- `theme:facts_reactive_compensation` (DISPLAY_EXPANSION): "...ion; distinct from flexible_hvdc_converter_valves (DC conversion) and hv_transformers_switchgear (primary equipment)."
- `theme:grid_interconnection_services` (DISPLAY_EXPANSION): "...ing: queues, dedicated substations, relay coordination; distinct from hv_transformers_switchgear (equipment manufacture) and transmission_substation_epc (public netwo..."
- `theme:grid_protection_substation_automation` (DISPLAY_EXPANSION): "Protection/control intelligence per IEC 61850; distinct from hv_transformers_switchgear (primary apparatus) and grid_distribution_automation (feeder automati..."
- `theme:uhv_transmission` (DISPLAY_EXPANSION): "Corridor systems engineering at 1000kV AC/±800kV DC; distinct from hv_transformers_switchgear (equipment class) and transmission_hvdc_cabling (cable links)."

### micro-identity_access_management

`theme:identity_access_management`: Identity and access management / 身份与访问管理

- **Proposed disposition:** KEEP (confidence HIGH)
- **Rationale:** Directory-wide identity lifecycle and access control is a distinct category. No neighbour is flagged. Three expansion rows (consumer anti-abuse, payments fraud, zero-trust access) define themselves against it.
- **Name quality:** Matches the scope; no naming defect found.
- **Parent paths:** `theme:technology_software>theme:cybersecurity>theme:identity_access_management`
- **Asserted on / nominated from:** 2026-10-08 / `basket:baskets:cybersecurity`
- **Crosswalk note:** "Credential and identity attack surface distinct from endpoint malware detection."
- **scope_version:** `89f4de9b394ece59ef91dfe903f612db6db9fcf28b1875c4e1b7a4c24047abd6`
- **Baseline coverage:** EMPTY; admitted 0, proposed 0, rejected 0; vendor routes 0, vendor member companies 0; research records none; route kinds none
- **Member companies (probation lane):** none
- **Siblings:** 24 micros share a parent; frozen siblings: `theme:cloud_security`, `theme:endpoint_security`, `theme:network_security`
- **Gate-2 provenance markers:** none
- **Flagged by rule:** none

| nearest neighbour | tier | composite | name_jac | def_jac | name_char3 | zh_bigram | shared parent | shared members |
|---|---|---|---|---|---|---|---|---|
| `theme:vulnerability_exposure_management` | DISPLAY_EXPANSION | 0.279 | 0.167 | 0.133 | 0.355 | 0.083 | yes | 0 |
| `theme:crypto_pki_key_management` | DISPLAY_EXPANSION | 0.245 | 0.143 | 0.029 | 0.349 | 0.091 | yes | 0 |
| `theme:zero_trust_sase_access` | DISPLAY_EXPANSION | 0.23 | 0.167 | 0.107 | 0.226 | 0.0 | yes | 0 |
| `theme:identity_fraud_anti_abuse` | DISPLAY_EXPANSION | 0.2 | 0.143 | 0.115 | 0.106 | 0.0 | yes | 0 |
| `theme:liquid_cooling_thermal` | FROZEN_ACCEPTANCE | 0.165 | 0.167 | 0.056 | 0.339 | 0.125 | no | 0 |

Referenced by:

- `theme:identity_fraud_anti_abuse` (DISPLAY_EXPANSION): "...r, bots and payment abuse against consumer-facing apps; distinct from identity_access_management, which governs workforce/enterprise access rights."
- `theme:payments_fraud_aml_decisioning` (DISPLAY_EXPANSION): "...al time: fraud scoring, AML/sanctions screening, device intelligence; identity_access_management (cybersecurity) governs system access, not payment risk. Re-opens V1'..."
- `theme:zero_trust_sase_access` (DISPLAY_EXPANSION): "Per-session identity-centric access control plane; identity_access_management governs directory-wide identity lifecycle and network_security guards..."

### micro-industrial_motion_controls

`theme:industrial_motion_controls`: Industrial controls and motion control / 工业控制与运动控制

- **Proposed disposition:** KEEP (confidence MEDIUM)
- **Rationale:** The controls and motion layer between automation hardware and factory software; the MES and robot-middleware rows define themselves against it. The note's 'software layer' undersells the PLC and drive hardware the name covers. That is a wording fix, not a rename.
- **Name quality:** Matches the scope. The crosswalk note's 'software layer' wording undersells the controls hardware; that is a note-wording fix, not a rename.
- **Parent paths:** `theme:industrials_defense>theme:robotics_automation>theme:industrial_motion_controls`
- **Asserted on / nominated from:** 2026-10-08 / `basket:baskets:robotics_automation`
- **Crosswalk note:** "Control and motion software layer that earns recurring revenue atop automation hardware."
- **scope_version:** `5b63e0b640f660bd089dfc4e359b20bea934f2f725d2c739a3b626b24a224726`
- **Baseline coverage:** EMPTY; admitted 0, proposed 0, rejected 0; vendor routes 0, vendor member companies 0; research records none; route kinds none
- **Member companies (probation lane):** none
- **Siblings:** 25 micros share a parent; frozen siblings: `theme:collaborative_robot_arms`, `theme:industrial_robot_arms`, `theme:machine_vision`, `theme:precision_actuators_servo_motors`, `theme:surgical_robotics_systems`
- **Gate-2 provenance markers:** none
- **Flagged by rule:** none

| nearest neighbour | tier | composite | name_jac | def_jac | name_char3 | zh_bigram | shared parent | shared members |
|---|---|---|---|---|---|---|---|---|
| `theme:industrial_iot_condition_monitoring` | DISPLAY_EXPANSION | 0.287 | 0.167 | 0.107 | 0.43 | 0.077 | yes | 0 |
| `theme:industrial_robot_arms` | FROZEN_ACCEPTANCE | 0.279 | 0.2 | 0.1 | 0.309 | 0.111 | yes | 0 |
| `theme:machine_vision` | FROZEN_ACCEPTANCE | 0.153 | 0.0 | 0.15 | 0.076 | 0.0 | yes | 0 |
| `theme:construction_robotics` | DISPLAY_EXPANSION | 0.152 | 0.0 | 0.034 | 0.218 | 0.0 | yes | 0 |
| `theme:mes_manufacturing_software` | DISPLAY_EXPANSION | 0.151 | 0.0 | 0.148 | 0.0 | 0.071 | yes | 0 |

Referenced by:

- `theme:mes_manufacturing_software` (DISPLAY_EXPANSION): "...factory above machines: MES/MOM, quality, traceability, ERP handoff; industrial_motion_controls controls machines in real time - different altitude of the software s..."
- `theme:robot_software_middleware` (DISPLAY_EXPANSION): "...fleet orchestration abstracting heterogeneous hardware; distinct from industrial_motion_controls, which closes servo loops on one machine."

### micro-industrial_robot_arms

`theme:industrial_robot_arms`: Industrial robot arms / 工业机械臂

- **Proposed disposition:** KEEP (confidence HIGH)
- **Rationale:** Fixed, high-volume hard-automation robots. The pair with collaborative_robot_arms (0.547) is an explicit mutual distinction, and construction_robotics holds the non-factory case apart.
- **Name quality:** Matches the scope; no naming defect found.
- **Parent paths:** `theme:industrials_defense>theme:robotics_automation>theme:industrial_robot_arms`; `theme:industrials_defense>theme:robotics_automation>theme:robot_arm_systems>theme:industrial_robot_arms`
- **Asserted on / nominated from:** 2026-10-08 / `research:config/theme_pathways.yml`
- **Crosswalk note:** "Fixed high-volume hard-automation robots, distinct from collaborative arms for high-mix work."
- **scope_version:** `a6dd9e074466c5a17bcbbdf23f3e80d87e6a988b33f53c02a94ea7f4b6cefe21`
- **Baseline coverage:** EMPTY; admitted 0, proposed 0, rejected 0; vendor routes 0, vendor member companies 0; research records none; route kinds intermediate
- **Member companies (probation lane):** none
- **Siblings:** 25 micros share a parent; frozen siblings: `theme:collaborative_robot_arms`, `theme:industrial_motion_controls`, `theme:machine_vision`, `theme:precision_actuators_servo_motors`, `theme:surgical_robotics_systems`
- **Gate-2 provenance markers:** none
- **Flagged by rule:** `theme:collaborative_robot_arms` (0.547)

| nearest neighbour | tier | composite | name_jac | def_jac | name_char3 | zh_bigram | shared parent | shared members |
|---|---|---|---|---|---|---|---|---|
| `theme:collaborative_robot_arms` | FROZEN_ACCEPTANCE | 0.547 | 0.5 | 0.467 | 0.445 | 0.333 | yes | 0 |
| `theme:industrial_motion_controls` | FROZEN_ACCEPTANCE | 0.279 | 0.2 | 0.1 | 0.309 | 0.111 | yes | 0 |
| `theme:industrial_iot_condition_monitoring` | DISPLAY_EXPANSION | 0.275 | 0.167 | 0.069 | 0.406 | 0.091 | yes | 0 |
| `theme:humanoid_embodied_robots` | DISPLAY_EXPANSION | 0.235 | 0.167 | 0.172 | 0.168 | 0.0 | yes | 0 |
| `theme:laboratory_automation_robots` | DISPLAY_EXPANSION | 0.23 | 0.167 | 0.16 | 0.159 | 0.0 | yes | 0 |

Referenced by:

- `theme:construction_robotics` (DISPLAY_EXPANSION): "..., printing, rebar, finishing under intelligent-construction programs; industrial_robot_arms serves factory floors - this row serves building construction."

### micro-launch_services

`theme:launch_services`: Launch services / 发射服务

- **Proposed disposition:** KEEP (confidence HIGH)
- **Rationale:** The orbit-access layer, with its own cost curve. Two flags, dedicated_small_launch_vehicles (0.312) and spaceport_launch_infrastructure, are expansion carve-outs. The third, satellite_broadband_services (0.305), comes from shared tokens. Whether small-launch is contained in this row is expansion-tier follow-up.
- **Name quality:** Matches the scope; no naming defect found.
- **Parent paths:** `theme:industrials_defense>theme:space_satellite>theme:launch_services`
- **Asserted on / nominated from:** 2026-10-08 / `basket:baskets:space_economy`
- **Crosswalk note:** "Orbit-access layer whose reusable-vehicle cost curve sets constellation economics."
- **scope_version:** `be0ab871d197482145e9613c570840501a5a81d2ec38a6da52782ccc88f5dec9`
- **Baseline coverage:** EMPTY; admitted 0, proposed 0, rejected 0; vendor routes 0, vendor member companies 0; research records none; route kinds none
- **Member companies (probation lane):** none
- **Siblings:** 22 micros share a parent; frozen siblings: `theme:direct_to_device_connectivity`, `theme:earth_observation`, `theme:military_space_communications`, `theme:satellite_broadband_services`, `theme:satellite_ground_terminals`
- **Gate-2 provenance markers:** none
- **Flagged by rule:** `theme:dedicated_small_launch_vehicles` (0.312), `theme:spaceport_launch_infrastructure` (0.307), `theme:satellite_broadband_services` (0.305)

| nearest neighbour | tier | composite | name_jac | def_jac | name_char3 | zh_bigram | shared parent | shared members |
|---|---|---|---|---|---|---|---|---|
| `theme:dedicated_small_launch_vehicles` | DISPLAY_EXPANSION | 0.312 | 0.2 | 0.308 | 0.325 | 0.0 | yes | 0 |
| `theme:spaceport_launch_infrastructure` | DISPLAY_EXPANSION | 0.307 | 0.25 | 0.16 | 0.274 | 0.125 | yes | 0 |
| `theme:satellite_broadband_services` | FROZEN_ACCEPTANCE | 0.305 | 0.25 | 0.045 | 0.39 | 0.143 | yes | 0 |
| `theme:launch_vehicle_propulsion` | DISPLAY_EXPANSION | 0.281 | 0.25 | 0.125 | 0.31 | 0.0 | yes | 0 |
| `theme:gnss_pnt_services` | DISPLAY_EXPANSION | 0.278 | 0.2 | 0.03 | 0.39 | 0.111 | yes | 0 |

Referenced by:

- `theme:dedicated_small_launch_vehicles` (DISPLAY_EXPANSION): "...gle-customer orbits on responsive schedules with small-lift vehicles; launch_services is the whole orbit-access layer at reusable-heavy economics - a disti..."
- `theme:launch_vehicle_propulsion` (DISPLAY_EXPANSION): "...stages sold to vehicle programs; propulsion hardware tier upstream of launch_services flights."
- `theme:satellite_manufacturing_constellations` (DISPLAY_EXPANSION): "...raft: bus/payload integration, high-rate constellation assembly, AIT; launch_services provides orbit access. Distinct from V1-rejected leo_constellation_de..."
- `theme:spacecraft_propulsion_systems` (DISPLAY_EXPANSION): "...h: Hall/ion thrusters, chemical orbit-raising, propellant management; launch_services' vehicles reach orbit, this row operates beyond it."

### micro-life_science_lab_instruments

`theme:life_science_lab_instruments`: Life-science laboratory instruments / 生命科学实验室仪器

- **Proposed disposition:** KEEP (confidence HIGH)
- **Rationale:** General R&D lab capital equipment. Its flags, lims_lab_informatics (0.351) and lifesci_raw_reagents (0.311), are software and consumables rows, not duplicates.
- **Name quality:** Matches the scope; no naming defect found.
- **Parent paths:** `theme:healthcare_lifesciences>theme:diagnostics_lifesci>theme:life_science_lab_instruments`
- **Asserted on / nominated from:** 2026-10-08 / `research:config/trade_flow_codes.yml`
- **Crosswalk note:** "General R&D lab capital equipment; dedicated sequencers belong under genomic_sequencing."
- **scope_version:** `55127a55a976a56f1d46cbcf2e67aebd319b7089134341a347d012627f27d414`
- **Baseline coverage:** EMPTY; admitted 0, proposed 0, rejected 0; vendor routes 0, vendor member companies 0; research records none; route kinds none
- **Member companies (probation lane):** none
- **Siblings:** 19 micros share a parent; frozen siblings: `theme:diagnostic_reagents_kits`, `theme:genomic_sequencing`, `theme:liquid_biopsy_assays`, `theme:proteomics_discovery_platforms`
- **Gate-2 provenance markers:** none
- **Flagged by rule:** `theme:lims_lab_informatics` (0.351), `theme:lifesci_raw_reagents` (0.311)

| nearest neighbour | tier | composite | name_jac | def_jac | name_char3 | zh_bigram | shared parent | shared members |
|---|---|---|---|---|---|---|---|---|
| `theme:lims_lab_informatics` | DISPLAY_EXPANSION | 0.351 | 0.286 | 0.12 | 0.423 | 0.182 | yes | 0 |
| `theme:lifesci_raw_reagents` | DISPLAY_EXPANSION | 0.311 | 0.2 | 0.094 | 0.374 | 0.214 | yes | 0 |
| `theme:lab_automation_sample_prep` | DISPLAY_EXPANSION | 0.282 | 0.222 | 0.107 | 0.263 | 0.125 | yes | 0 |
| `theme:laboratory_automation_robots` | DISPLAY_EXPANSION | 0.2 | 0.125 | 0.231 | 0.309 | 0.182 | no | 0 |
| `theme:icl_central_labs` | DISPLAY_EXPANSION | 0.192 | 0.0 | 0.067 | 0.161 | 0.214 | yes | 0 |

Referenced by: none.

### micro-liquid_biopsy_assays

`theme:liquid_biopsy_assays`: Liquid biopsy assays / 液体活检检测

- **Proposed disposition:** KEEP (confidence HIGH)
- **Rationale:** Blood-based early detection is its own clinical and reimbursement category. No neighbour is flagged.
- **Name quality:** Matches the scope; no naming defect found.
- **Parent paths:** `theme:healthcare_lifesciences>theme:diagnostics_lifesci>theme:liquid_biopsy_assays`; `theme:healthcare_lifesciences>theme:diagnostics_lifesci>theme:multi_omics_platforms>theme:liquid_biopsy_assays`
- **Asserted on / nominated from:** 2026-10-08 / `research:config/theme_thesis_registry.yml`
- **Crosswalk note:** "Blood-based early detection named as its own clinical category in thesis text."
- **scope_version:** `4b457f0f17814bfc17e4545cf239dd03f32a7d1e29c60962e9c6846eeea221d6`
- **Baseline coverage:** EMPTY; admitted 0, proposed 0, rejected 0; vendor routes 0, vendor member companies 0; research records none; route kinds intermediate
- **Member companies (probation lane):** none
- **Siblings:** 19 micros share a parent; frozen siblings: `theme:diagnostic_reagents_kits`, `theme:genomic_sequencing`, `theme:life_science_lab_instruments`, `theme:proteomics_discovery_platforms`
- **Gate-2 provenance markers:** none
- **Flagged by rule:** none

| nearest neighbour | tier | composite | name_jac | def_jac | name_char3 | zh_bigram | shared parent | shared members |
|---|---|---|---|---|---|---|---|---|
| `theme:immunoassay_clinical_chemistry` | DISPLAY_EXPANSION | 0.159 | 0.0 | 0.074 | 0.109 | 0.091 | yes | 0 |
| `theme:clinical_mass_spectrometry` | DISPLAY_EXPANSION | 0.14 | 0.0 | 0.037 | 0.044 | 0.111 | yes | 0 |
| `theme:trial_biomarker_services` | DISPLAY_EXPANSION | 0.138 | 0.0 | 0.045 | 0.135 | 0.0 | yes | 0 |
| `theme:pcr_molecular_diagnostics` | DISPLAY_EXPANSION | 0.135 | 0.0 | 0.037 | 0.036 | 0.091 | yes | 0 |
| `theme:point_of_care_testing` | DISPLAY_EXPANSION | 0.129 | 0.0 | 0.0 | 0.0 | 0.143 | yes | 0 |

Referenced by: none.

### micro-liquid_cooling_thermal

`theme:liquid_cooling_thermal`: Liquid cooling & thermal management / 液冷与热管理

- **Proposed disposition:** KEEP (confidence MEDIUM)
- **Rationale:** The broad liquid-cooling segment row; four expansion rows define themselves against it. The only flag, cold_plate_liquid_cooling (0.364), calls itself a sub-segment. Whether the broad row and its expansion children should coexist is expansion-tier follow-up, not a defect in the frozen row.
- **Name quality:** Matches the scope; no naming defect found.
- **Parent paths:** `theme:energy_power>theme:data_center_power>theme:liquid_cooling_thermal`; `theme:technology_software>theme:data_center_power>theme:liquid_cooling_thermal`
- **Asserted on / nominated from:** 2026-10-08 / `research:config/theme_thesis_registry.yml`
- **Crosswalk note:** "Thermal segment mandatory for high-density AI racks."
- **scope_version:** `ade92a568068c09c0e0089bb6bfd4f136cbb72551944bf06cd2ecb046865a7db`
- **Baseline coverage:** EMPTY; admitted 0, proposed 0, rejected 0; vendor routes 0, vendor member companies 0; research records none; route kinds none
- **Member companies (probation lane):** none
- **Siblings:** 17 micros share a parent; frozen siblings: `theme:hv_transformers_switchgear`, `theme:ups_power_conversion`
- **Gate-2 provenance markers:** none
- **Flagged by rule:** `theme:cold_plate_liquid_cooling` (0.364)

| nearest neighbour | tier | composite | name_jac | def_jac | name_char3 | zh_bigram | shared parent | shared members |
|---|---|---|---|---|---|---|---|---|
| `theme:cold_plate_liquid_cooling` | DISPLAY_EXPANSION | 0.364 | 0.286 | 0.182 | 0.448 | 0.143 | yes | 0 |
| `theme:immersion_cooling_systems` | DISPLAY_EXPANSION | 0.286 | 0.167 | 0.2 | 0.244 | 0.143 | yes | 0 |
| `theme:immersion_thermal_fluids` | DISPLAY_EXPANSION | 0.235 | 0.111 | 0.13 | 0.229 | 0.091 | yes | 0 |
| `theme:dcim_energy_management` | DISPLAY_EXPANSION | 0.222 | 0.125 | 0.037 | 0.282 | 0.062 | yes | 0 |
| `theme:thermal_rejection_heat_recovery` | DISPLAY_EXPANSION | 0.182 | 0.125 | 0.154 | 0.0 | 0.0 | yes | 0 |

Referenced by:

- `theme:cold_plate_liquid_cooling` (DISPLAY_EXPANSION): "Pumped cold-plate loops and CDUs; distinct from liquid_cooling_thermal (broad segment row) and immersion_cooling_systems (dielectric baths)."
- `theme:immersion_cooling_systems` (DISPLAY_EXPANSION): "...h board redesign; distinct from cold_plate_liquid_cooling (loops) and liquid_cooling_thermal (segment)."
- `theme:precision_air_conditioning` (DISPLAY_EXPANSION): "Air-side white-space cooling and containment; distinct from liquid_cooling_thermal (liquid segment) and thermal_rejection_heat_recovery (exterior plant)..."
- `theme:thermal_rejection_heat_recovery` (DISPLAY_EXPANSION): "...ort; distinct from precision_air_conditioning (white-space units) and liquid_cooling_thermal (IT-space segment)."

### micro-lithography_tools

`theme:lithography_tools`: Lithography tools / 光刻设备

- **Proposed disposition:** KEEP (confidence HIGH)
- **Rationale:** The exposure-tool class, sibling to etch/deposition and metrology. No neighbour is flagged. The coat/develop track, photomask and foundry rows define themselves against it.
- **Name quality:** Matches the scope; no naming defect found.
- **Parent paths:** `theme:semiconductors_hardware>theme:semicap_equipment>theme:lithography_tools`; `theme:semiconductors_hardware>theme:semicap_equipment>theme:wfe_process_tools>theme:lithography_tools`
- **Asserted on / nominated from:** 2026-10-08 / `research:config/theme_thesis_registry.yml`
- **Crosswalk note:** "Lithography exposure as a fab tool class, sibling to etch/deposition and metrology."
- **scope_version:** `48fb6b9c5b7ed4fa9dcfe8e7673a7e7c4fc48ea5fe0cc5e304c0fad9dc802e30`
- **Baseline coverage:** EMPTY; admitted 0, proposed 0, rejected 0; vendor routes 0, vendor member companies 0; research records none; route kinds intermediate
- **Member companies (probation lane):** none
- **Siblings:** 18 micros share a parent; frozen siblings: `theme:etch_deposition_equipment`, `theme:process_metrology_inspection`, `theme:wafer_fab_subsystems`
- **Gate-2 provenance markers:** none
- **Flagged by rule:** none

| nearest neighbour | tier | composite | name_jac | def_jac | name_char3 | zh_bigram | shared parent | shared members |
|---|---|---|---|---|---|---|---|---|
| `theme:wet_clean_equipment` | DISPLAY_EXPANSION | 0.168 | 0.0 | 0.182 | 0.0 | 0.111 | yes | 0 |
| `theme:cmp_planarization_equipment` | DISPLAY_EXPANSION | 0.166 | 0.0 | 0.105 | 0.0 | 0.2 | yes | 0 |
| `theme:coat_develop_track` | DISPLAY_EXPANSION | 0.166 | 0.0 | 0.15 | 0.0 | 0.143 | yes | 0 |
| `theme:etch_deposition_equipment` | FROZEN_ACCEPTANCE | 0.164 | 0.0 | 0.143 | 0.0 | 0.143 | yes | 0 |
| `theme:ion_implant_equipment` | DISPLAY_EXPANSION | 0.164 | 0.0 | 0.143 | 0.0 | 0.143 | yes | 0 |

Referenced by:

- `theme:advanced_node_foundry` (DISPLAY_EXPANSION): "...isting foundry row (existing rows are design products). Distinct from lithography_tools (buys tools) and memory_wafer_fab (logic flows, not memory arrays)."
- `theme:coat_develop_track` (DISPLAY_EXPANSION): "Resist track cluster paired to scanners; distinct from lithography_tools (the exposure scanner) and photoresist materials (the chemistry)."
- `theme:photomask_manufacturing` (DISPLAY_EXPANSION): "...le pattern master (e-beam write, pellicle, EUV blanks); distinct from lithography_tools (the exposure tool) and photoresist (consumable chemistry)."

### micro-machine_vision

`theme:machine_vision`: Machine vision / 机器视觉

- **Proposed disposition:** KEEP (confidence HIGH)
- **Rationale:** The perception layer, distinct from motion hardware and from robot-learning software. No neighbour is flagged.
- **Name quality:** Matches the scope; no naming defect found.
- **Parent paths:** `theme:industrials_defense>theme:robotics_automation>theme:machine_vision`
- **Asserted on / nominated from:** 2026-10-08 / `basket:baskets:robotics_automation`
- **Crosswalk note:** "Perception layer that lets robots handle unstructured tasks, separate from motion hardware."
- **scope_version:** `a39db127a120295df301fc808dcbf6fee3e8324b41a8d8f6828942c33a684b5c`
- **Baseline coverage:** EMPTY; admitted 0, proposed 0, rejected 0; vendor routes 0, vendor member companies 0; research records none; route kinds none
- **Member companies (probation lane):** none
- **Siblings:** 25 micros share a parent; frozen siblings: `theme:collaborative_robot_arms`, `theme:industrial_motion_controls`, `theme:industrial_robot_arms`, `theme:precision_actuators_servo_motors`, `theme:surgical_robotics_systems`
- **Gate-2 provenance markers:** none
- **Flagged by rule:** none

| nearest neighbour | tier | composite | name_jac | def_jac | name_char3 | zh_bigram | shared parent | shared members |
|---|---|---|---|---|---|---|---|---|
| `theme:precision_actuators_servo_motors` | FROZEN_ACCEPTANCE | 0.158 | 0.0 | 0.1 | 0.165 | 0.0 | yes | 0 |
| `theme:industrial_iot_condition_monitoring` | DISPLAY_EXPANSION | 0.154 | 0.0 | 0.143 | 0.09 | 0.0 | yes | 0 |
| `theme:robot_software_middleware` | DISPLAY_EXPANSION | 0.154 | 0.0 | 0.143 | 0.0 | 0.091 | yes | 0 |
| `theme:industrial_motion_controls` | FROZEN_ACCEPTANCE | 0.153 | 0.0 | 0.15 | 0.076 | 0.0 | yes | 0 |
| `theme:professional_service_robots` | DISPLAY_EXPANSION | 0.153 | 0.0 | 0.029 | 0.103 | 0.125 | yes | 0 |

Referenced by:

- `theme:embodied_ai_robot_learning` (DISPLAY_EXPANSION): "...on and foundation models; task-acquisition intelligence distinct from machine_vision perception sensing."
- `theme:force_tactile_safety_sensing` (DISPLAY_EXPANSION): "...nners, light curtains enabling force-limited collaborative operation; machine_vision is camera perception."

### micro-medical_imaging

`theme:medical_imaging`: Medical imaging systems / 医学影像系统

- **Proposed disposition:** KEEP (confidence HIGH)
- **Rationale:** Imaging-modality capital equipment. No neighbour is flagged and no row refers to it.
- **Name quality:** Matches the scope; no naming defect found.
- **Parent paths:** `theme:healthcare_lifesciences>theme:medical_devices>theme:ai_clinical_data_devices>theme:medical_imaging`; `theme:healthcare_lifesciences>theme:medical_devices>theme:medical_imaging`
- **Asserted on / nominated from:** 2026-10-08 / `research:config/theme_thesis_registry.yml`
- **Crosswalk note:** "Imaging modality capital equipment; AI-assisted reads are a current technology driver, not the segment definition."
- **scope_version:** `e19ac4ebfec8e27650b805066d39a5b322de39c40c0e2af8ed45e6096b2ba9f3`
- **Baseline coverage:** EMPTY; admitted 0, proposed 0, rejected 0; vendor routes 0, vendor member companies 0; research records none; route kinds intermediate
- **Member companies (probation lane):** none
- **Siblings:** 18 micros share a parent; frozen siblings: `theme:remote_patient_monitoring`, `theme:surgical_implants_instruments`, `theme:surgical_robotics_systems`
- **Gate-2 provenance markers:** none
- **Flagged by rule:** none

| nearest neighbour | tier | composite | name_jac | def_jac | name_char3 | zh_bigram | shared parent | shared members |
|---|---|---|---|---|---|---|---|---|
| `theme:surgical_robotics_systems` | FROZEN_ACCEPTANCE | 0.295 | 0.2 | 0.087 | 0.417 | 0.1 | yes | 0 |
| `theme:medical_biomaterials_polymers` | DISPLAY_EXPANSION | 0.217 | 0.167 | 0.037 | 0.247 | 0.0 | yes | 0 |
| `theme:immersion_cooling_systems` | DISPLAY_EXPANSION | 0.181 | 0.2 | 0.077 | 0.459 | 0.0 | no | 0 |
| `theme:immunoassay_clinical_chemistry` | DISPLAY_EXPANSION | 0.15 | 0.167 | 0.067 | 0.372 | 0.0 | no | 0 |
| `theme:ami_smart_metering` | DISPLAY_EXPANSION | 0.149 | 0.167 | 0.034 | 0.409 | 0.0 | no | 0 |

Referenced by: none.

### micro-military_space_communications

`theme:military_space_communications`: Military space and satellite communications / 军用太空与卫星通信

- **Proposed disposition:** KEEP (confidence HIGH)
- **Rationale:** Protected military satcom, distinct from commercial broadband and from counterspace. No neighbour is flagged.
- **Name quality:** Matches the scope; no naming defect found.
- **Parent paths:** `theme:industrials_defense>theme:defense_aerospace>theme:military_space_communications`; `theme:industrials_defense>theme:space_satellite>theme:military_space_communications`
- **Asserted on / nominated from:** 2026-10-08 / `basket:baskets:space_economy`
- **Crosswalk note:** "Resilient military satcom shared between defense programs and the commercial space build-out."
- **scope_version:** `cbd6d0a3506c2fd559751ba63de6876c73c24fd7a163da9d98d24d023cf6b79f`
- **Baseline coverage:** EMPTY; admitted 0, proposed 0, rejected 0; vendor routes 0, vendor member companies 0; research records none; route kinds none
- **Member companies (probation lane):** none
- **Siblings:** 48 micros share a parent; frozen siblings: `theme:aerospace_components_aftermarket`, `theme:autonomous_systems_counter_uas`, `theme:defense_sensors_electronics_c2`, `theme:direct_to_device_connectivity`, `theme:earth_observation`, `theme:launch_services`, `theme:missile_propulsion_supply`, `theme:missiles_munitions_effects`, `theme:naval_shipbuilding`, `theme:satellite_broadband_services`, `theme:satellite_ground_terminals`
- **Gate-2 provenance markers:** none
- **Flagged by rule:** none

| nearest neighbour | tier | composite | name_jac | def_jac | name_char3 | zh_bigram | shared parent | shared members |
|---|---|---|---|---|---|---|---|---|
| `theme:direct_to_device_connectivity` | FROZEN_ACCEPTANCE | 0.276 | 0.143 | 0.043 | 0.303 | 0.273 | yes | 0 |
| `theme:satellite_broadband_services` | FROZEN_ACCEPTANCE | 0.275 | 0.167 | 0.1 | 0.366 | 0.091 | yes | 0 |
| `theme:satellite_components_payloads` | DISPLAY_EXPANSION | 0.256 | 0.167 | 0.034 | 0.36 | 0.083 | yes | 0 |
| `theme:satellite_manufacturing_constellations` | DISPLAY_EXPANSION | 0.254 | 0.143 | 0.056 | 0.372 | 0.077 | yes | 0 |
| `theme:military_aero_engines` | DISPLAY_EXPANSION | 0.251 | 0.167 | 0.069 | 0.293 | 0.083 | yes | 0 |

Referenced by:

- `theme:space_security_counterspace` (DISPLAY_EXPANSION): "...etection, space domain awareness for defense; distinct from protected military_space_communications services."

### micro-missile_propulsion_supply

`theme:missile_propulsion_supply`: Missile and munition propulsion supply / 导弹与弹药推进系统供给

- **Proposed disposition:** KEEP (confidence HIGH)
- **Rationale:** The propulsion bottleneck in munitions supply. The flag missiles_munitions_effects (0.314) is the system layer above it. The aero-engine and energetics rows define themselves against it.
- **Name quality:** Matches the scope; no naming defect found.
- **Parent paths:** `theme:industrials_defense>theme:defense_aerospace>theme:missile_munition_chain>theme:missile_propulsion_supply`; `theme:industrials_defense>theme:defense_aerospace>theme:missile_propulsion_supply`
- **Asserted on / nominated from:** 2026-10-08 / `research:config/theme_pathways.yml`
- **Crosswalk note:** "Propulsion bottlenecks constrain guided-munition output rates."
- **scope_version:** `732cf16c34b142a3200a49af27bd2ac0a431f9ac42a6f479f481dd432bf13ada`
- **Baseline coverage:** EMPTY; admitted 0, proposed 0, rejected 0; vendor routes 0, vendor member companies 0; research records none; route kinds intermediate
- **Member companies (probation lane):** none
- **Siblings:** 26 micros share a parent; frozen siblings: `theme:aerospace_components_aftermarket`, `theme:autonomous_systems_counter_uas`, `theme:defense_sensors_electronics_c2`, `theme:military_space_communications`, `theme:missiles_munitions_effects`, `theme:naval_shipbuilding`
- **Gate-2 provenance markers:** none
- **Flagged by rule:** `theme:missiles_munitions_effects` (0.314)

| nearest neighbour | tier | composite | name_jac | def_jac | name_char3 | zh_bigram | shared parent | shared members |
|---|---|---|---|---|---|---|---|---|
| `theme:missiles_munitions_effects` | FROZEN_ACCEPTANCE | 0.314 | 0.167 | 0.056 | 0.479 | 0.231 | yes | 0 |
| `theme:aerospace_propulsion_engines` | DISPLAY_EXPANSION | 0.26 | 0.143 | 0.154 | 0.356 | 0.0 | yes | 0 |
| `theme:energetics_explosives_supply` | DISPLAY_EXPANSION | 0.233 | 0.167 | 0.16 | 0.175 | 0.0 | yes | 0 |
| `theme:air_missile_defense_systems` | DISPLAY_EXPANSION | 0.231 | 0.125 | 0.13 | 0.197 | 0.077 | yes | 0 |
| `theme:launch_vehicle_propulsion` | DISPLAY_EXPANSION | 0.163 | 0.167 | 0.045 | 0.401 | 0.067 | no | 0 |

Referenced by:

- `theme:aerospace_propulsion_engines` (DISPLAY_EXPANSION): "...ls gas-turbine aero engines with long-life aftermarket; distinct from missile_propulsion_supply, which is expendable solid-rocket motor output."
- `theme:energetics_explosives_supply` (DISPLAY_EXPANSION): "...rains, explosive fills, pyrotechnics, insensitive-munition chemistry; missile_propulsion_supply names propulsion assembly, not the chemistry tier."
- `theme:military_aero_engines` (DISPLAY_EXPANSION): "...ropulsion for manned military aircraft including life-cycle overhaul; missile_propulsion_supply covers expendable rocket/motor propulsion - different propulsion phys..."

### micro-missiles_munitions_effects

`theme:missiles_munitions_effects`: Missiles, munitions and effects / 导弹、弹药与毁伤效应

- **Proposed disposition:** KEEP (confidence HIGH)
- **Rationale:** Replenishment economics for expendable munitions. The flag missile_propulsion_supply (0.314) is the supplier layer beneath it. Three expansion rows (air and missile defence, hypersonics, seekers) carve against it.
- **Name quality:** Matches the scope; no naming defect found.
- **Parent paths:** `theme:industrials_defense>theme:defense_aerospace>theme:missile_munition_chain>theme:missiles_munitions_effects`; `theme:industrials_defense>theme:defense_aerospace>theme:missiles_munitions_effects`
- **Asserted on / nominated from:** 2026-10-08 / `research:research/defense_intelligence/D0R_DEFENSE_EQUITY_DRIVER_TAXONOMY.md`
- **Crosswalk note:** "Expendable replenishment and production economics separate from platform primes."
- **scope_version:** `3991a030892ecab11266fc5b74186ec13b1a9676377b10df8d36b1bbf92989fd`
- **Baseline coverage:** EMPTY; admitted 0, proposed 0, rejected 0; vendor routes 0, vendor member companies 0; research records none; route kinds intermediate
- **Member companies (probation lane):** none
- **Siblings:** 26 micros share a parent; frozen siblings: `theme:aerospace_components_aftermarket`, `theme:autonomous_systems_counter_uas`, `theme:defense_sensors_electronics_c2`, `theme:military_space_communications`, `theme:missile_propulsion_supply`, `theme:naval_shipbuilding`
- **Gate-2 provenance markers:** none
- **Flagged by rule:** `theme:missile_propulsion_supply` (0.314)

| nearest neighbour | tier | composite | name_jac | def_jac | name_char3 | zh_bigram | shared parent | shared members |
|---|---|---|---|---|---|---|---|---|
| `theme:missile_propulsion_supply` | FROZEN_ACCEPTANCE | 0.314 | 0.167 | 0.056 | 0.479 | 0.231 | yes | 0 |
| `theme:air_missile_defense_systems` | DISPLAY_EXPANSION | 0.183 | 0.0 | 0.174 | 0.2 | 0.0 | yes | 0 |
| `theme:hypersonic_strike_vehicles` | DISPLAY_EXPANSION | 0.167 | 0.0 | 0.16 | 0.136 | 0.0 | yes | 0 |
| `theme:autonomous_systems_counter_uas` | FROZEN_ACCEPTANCE | 0.158 | 0.0 | 0.1 | 0.164 | 0.0 | yes | 0 |
| `theme:military_space_communications` | FROZEN_ACCEPTANCE | 0.154 | 0.0 | 0.0 | 0.272 | 0.0 | yes | 0 |

Referenced by:

- `theme:air_missile_defense_systems` (DISPLAY_EXPANSION): "...d defensive system-of-systems (radars + fire control + interceptors); missiles_munitions_effects covers the munition's output economics, not the layered defense syste..."
- `theme:hypersonic_strike_vehicles` (DISPLAY_EXPANSION): "...uise vehicle class with thermal-protection materials and test chains; missiles_munitions_effects covers conventional munitions economics, not this vehicle class."
- `theme:seekers_guidance_components` (DISPLAY_EXPANSION): "...t layer inside munitions: seekers, fuzes, guidance electronics, IMUs; missiles_munitions_effects covers whole-munition replenishment."

### micro-nand_enterprise_storage

`theme:nand_enterprise_storage`: NAND & enterprise storage / NAND 与企业级存储

- **Proposed disposition:** RENAME (confidence LOW, LOW-CONFIDENCE)
- **Rationale:** Seven expansion rows treat it as the NAND media and drive segment; for example, nearline_hard_disk_drives calls it the 'flash-based framing'. But 'enterprise storage' collides with data_center_storage_systems (0.422) and invites storage-array vendors. LOW-CONFIDENCE, because the source thesis may have meant storage systems as well.
- **Proposed names:** EN "NAND flash & enterprise SSDs" / ZH "NAND 闪存与企业级 SSD" (scope unchanged)
- **Name quality:** Possibly misleading. 'enterprise storage / 企业级存储' reads as storage systems; the referrers treat the scope as flash media and drives.
- **Parent paths:** `theme:semiconductors_hardware>theme:memory_storage>theme:nand_enterprise_storage`
- **Asserted on / nominated from:** 2026-10-08 / `basket:baskets:memory_storage`
- **Crosswalk note:** "Basket thesis explicitly names NAND and enterprise storage."
- **scope_version:** `7238482db4f636da20b61043f383ad904ebca545a27b698f41f351eff9eba9b1`
- **Baseline coverage:** EMPTY; admitted 0, proposed 0, rejected 0; vendor routes 0, vendor member companies 0; research records none; route kinds none
- **Member companies (probation lane):** none
- **Siblings:** 20 micros share a parent; frozen siblings: `theme:conventional_dram`, `theme:hbm_packaging`
- **Gate-2 provenance markers:** none
- **Flagged by rule:** `theme:data_center_storage_systems` (0.422)

| nearest neighbour | tier | composite | name_jac | def_jac | name_char3 | zh_bigram | shared parent | shared members |
|---|---|---|---|---|---|---|---|---|
| `theme:data_center_storage_systems` | DISPLAY_EXPANSION | 0.422 | 0.286 | 0.125 | 0.643 | 0.308 | yes | 0 |
| `theme:enterprise_ssd_controllers` | DISPLAY_EXPANSION | 0.294 | 0.167 | 0.15 | 0.388 | 0.1 | yes | 0 |
| `theme:software_defined_storage_platforms` | DISPLAY_EXPANSION | 0.277 | 0.167 | 0.176 | 0.25 | 0.125 | yes | 0 |
| `theme:tape_archival_storage` | DISPLAY_EXPANSION | 0.273 | 0.2 | 0.056 | 0.319 | 0.125 | yes | 0 |
| `theme:embedded_storage_solutions` | DISPLAY_EXPANSION | 0.267 | 0.143 | 0.13 | 0.281 | 0.143 | yes | 0 |

Referenced by:

- `theme:data_center_storage_systems` (DISPLAY_EXPANSION): "Engineers all-flash arrays/scale-out systems; distinct from nand_enterprise_storage (drive/media segment) and memory_module_manufacturing (modules)."
- `theme:embedded_storage_solutions` (DISPLAY_EXPANSION): "...motive; distinct from memory_module_manufacturing (socketed/card) and nand_enterprise_storage (enterprise drives)."
- `theme:enterprise_ssd_controllers` (DISPLAY_EXPANSION): "Controller silicon + FTL firmware managing NAND; distinct from nand_enterprise_storage (media/segment) and memory_interface_chips (DRAM-side interface)."
- `theme:memory_module_manufacturing` (DISPLAY_EXPANSION): "...ricates RDIMM/SSD/card products for both DRAM and NAND; distinct from nand_enterprise_storage (segment) and data_center_storage_systems (complete systems)."
- `theme:memory_wafer_fab` (DISPLAY_EXPANSION): "...b-process production layer (node migration, yield); conventional_dram/nand_enterprise_storage are product segments. Distinct from advanced_node_foundry (logic flow..."
- `theme:nearline_hard_disk_drives` (DISPLAY_EXPANSION): "Magnetic recording capacity tier; distinct from nand_enterprise_storage (flash-based framing)."
- `theme:software_defined_storage_platforms` (DISPLAY_EXPANSION): "Storage control software over commodity hardware; distinct from nand_enterprise_storage (hardware) and enterprise_ssd_controllers (silicon)."

### micro-naval_shipbuilding

`theme:naval_shipbuilding`: Naval and nuclear shipbuilding / 海军与核动力舰船建造

- **Proposed disposition:** KEEP (confidence HIGH)
- **Rationale:** Throughput economics for hull delivery and nuclear yards. No neighbour is flagged. The ground-combat, undersea and floating-nuclear rows define themselves against it.
- **Name quality:** Matches the scope; no naming defect found.
- **Parent paths:** `theme:industrials_defense>theme:defense_aerospace>theme:naval_shipbuilding`
- **Asserted on / nominated from:** 2026-10-08 / `research:research/defense_intelligence/D0R_DEFENSE_EQUITY_DRIVER_TAXONOMY.md`
- **Crosswalk note:** "Hull delivery and nuclear-yard throughput economics distinct from munitions and electronics."
- **scope_version:** `b27279cbdcef94f20a4faf185582476dedf13ef1a34fd894ff4e111d08b1dd5c`
- **Baseline coverage:** EMPTY; admitted 0, proposed 0, rejected 0; vendor routes 0, vendor member companies 0; research records none; route kinds none
- **Member companies (probation lane):** none
- **Siblings:** 26 micros share a parent; frozen siblings: `theme:aerospace_components_aftermarket`, `theme:autonomous_systems_counter_uas`, `theme:defense_sensors_electronics_c2`, `theme:military_space_communications`, `theme:missile_propulsion_supply`, `theme:missiles_munitions_effects`
- **Gate-2 provenance markers:** none
- **Flagged by rule:** none

| nearest neighbour | tier | composite | name_jac | def_jac | name_char3 | zh_bigram | shared parent | shared members |
|---|---|---|---|---|---|---|---|---|
| `theme:nuclear_components` | FROZEN_ACCEPTANCE | 0.162 | 0.25 | 0.059 | 0.301 | 0.0 | no | 0 |
| `theme:floating_nuclear_platforms` | DISPLAY_EXPANSION | 0.16 | 0.143 | 0.12 | 0.257 | 0.143 | no | 0 |
| `theme:missiles_munitions_effects` | FROZEN_ACCEPTANCE | 0.148 | 0.0 | 0.111 | 0.1 | 0.0 | yes | 0 |
| `theme:undersea_systems_sonar` | DISPLAY_EXPANSION | 0.146 | 0.0 | 0.13 | 0.067 | 0.0 | yes | 0 |
| `theme:ground_combat_systems` | DISPLAY_EXPANSION | 0.134 | 0.0 | 0.111 | 0.033 | 0.0 | yes | 0 |

Referenced by:

- `theme:floating_nuclear_platforms` (DISPLAY_EXPANSION): "...r products; distinct from npp_construction_epc (site-fixed works) and naval_shipbuilding (naval vessels)."
- `theme:ground_combat_systems` (DISPLAY_EXPANSION): "...land-domain platform base: tanks, IFVs, artillery with fire control; naval_shipbuilding covers hulls and military_aircraft_platforms covers air - this is the..."
- `theme:undersea_systems_sonar` (DISPLAY_EXPANSION): "...lance and undersea vehicles; the acoustic ocean domain, distinct from naval_shipbuilding hull construction."

### micro-ndfeb_permanent_magnets

`theme:ndfeb_permanent_magnets`: NdFeB permanent magnets / 钕铁硼永磁材料

- **Proposed disposition:** KEEP (confidence HIGH)
- **Rationale:** The downstream magnet segment, distinct from ore and from separation/refining. No neighbour is flagged.
- **Name quality:** Matches the scope; no naming defect found.
- **Parent paths:** `theme:materials_mining>theme:rare_earth_critical_min>theme:ndfeb_permanent_magnets`; `theme:materials_mining>theme:rare_earth_critical_min>theme:rare_earth_processing_magnets>theme:ndfeb_permanent_magnets`
- **Asserted on / nominated from:** 2026-10-08 / `research:config/theme_thesis_registry.yml`
- **Crosswalk note:** "Downstream magnet segment distinct from upstream ore and refining in house trade and thesis text."
- **scope_version:** `1254e86d15a6ccfef8e3c7e3d5bf55e397a094efea7bf210a670aabc25e7d85b`
- **Baseline coverage:** EMPTY; admitted 0, proposed 0, rejected 0; vendor routes 0, vendor member companies 0; research records none; route kinds intermediate
- **Member companies (probation lane):** none
- **Siblings:** 19 micros share a parent; frozen siblings: `theme:critical_mineral_mining_development`, `theme:gallium_germanium_supply_chain`, `theme:rare_earth_separation_refining`
- **Gate-2 provenance markers:** none
- **Flagged by rule:** none

| nearest neighbour | tier | composite | name_jac | def_jac | name_char3 | zh_bigram | shared parent | shared members |
|---|---|---|---|---|---|---|---|---|
| `theme:smco_bonded_magnets` | DISPLAY_EXPANSION | 0.234 | 0.167 | 0.074 | 0.286 | 0.0 | yes | 0 |
| `theme:magnet_scrap_recycling` | DISPLAY_EXPANSION | 0.232 | 0.143 | 0.1 | 0.201 | 0.083 | yes | 0 |
| `theme:rare_earth_separation_refining` | FROZEN_ACCEPTANCE | 0.146 | 0.0 | 0.182 | 0.0 | 0.0 | yes | 0 |
| `theme:gallium_germanium_supply_chain` | FROZEN_ACCEPTANCE | 0.143 | 0.0 | 0.091 | 0.101 | 0.0 | yes | 0 |
| `theme:ree_phosphor_luminescent` | DISPLAY_EXPANSION | 0.142 | 0.0 | 0.0 | 0.126 | 0.083 | yes | 0 |

Referenced by: none.

### micro-network_security

`theme:network_security`: Network security / 网络边界安全

- **Proposed disposition:** KEEP (confidence HIGH)
- **Rationale:** Perimeter and traffic-level protection. The flags against endpoint (0.398), cloud (0.390) and email security come from shared vocabulary. The OT-security and zero-trust rows define themselves against it.
- **Name quality:** Matches the scope. The ZH 网络边界安全 ('network perimeter security') is narrower than the EN but agrees with the note.
- **Parent paths:** `theme:technology_software>theme:cybersecurity>theme:network_security`
- **Asserted on / nominated from:** 2026-10-08 / `basket:baskets:cybersecurity`
- **Crosswalk note:** "Perimeter and traffic-level protection distinct from device and identity controls."
- **scope_version:** `2cb03bd93993a2c5e565704c1f09942ac0644de479949fe8f6deb57b5f2c5234`
- **Baseline coverage:** EMPTY; admitted 0, proposed 0, rejected 0; vendor routes 0, vendor member companies 0; research records none; route kinds none
- **Member companies (probation lane):** none
- **Siblings:** 24 micros share a parent; frozen siblings: `theme:cloud_security`, `theme:endpoint_security`, `theme:identity_access_management`
- **Gate-2 provenance markers:** none
- **Flagged by rule:** `theme:endpoint_security` (0.398), `theme:cloud_security` (0.39), `theme:email_collaboration_security` (0.325)

| nearest neighbour | tier | composite | name_jac | def_jac | name_char3 | zh_bigram | shared parent | shared members |
|---|---|---|---|---|---|---|---|---|
| `theme:endpoint_security` | FROZEN_ACCEPTANCE | 0.398 | 0.333 | 0.222 | 0.485 | 0.143 | yes | 0 |
| `theme:cloud_security` | FROZEN_ACCEPTANCE | 0.39 | 0.333 | 0.133 | 0.535 | 0.167 | yes | 0 |
| `theme:email_collaboration_security` | DISPLAY_EXPANSION | 0.325 | 0.25 | 0.16 | 0.378 | 0.111 | yes | 0 |
| `theme:application_security_devsecops` | DISPLAY_EXPANSION | 0.295 | 0.25 | 0.033 | 0.398 | 0.1 | yes | 0 |
| `theme:ot_iot_industrial_security` | DISPLAY_EXPANSION | 0.29 | 0.2 | 0.107 | 0.365 | 0.1 | yes | 0 |

Referenced by:

- `theme:ot_iot_industrial_security` (DISPLAY_EXPANSION): "...ety-instrumented systems where availability outranks confidentiality; network_security targets enterprise IT traffic, not IEC 62443 zones and fieldbus."
- `theme:zero_trust_sase_access` (DISPLAY_EXPANSION): "...ntity_access_management governs directory-wide identity lifecycle and network_security guards perimeter traffic - this row brokers each application session."

### micro-nitrogen_fertilizer_production

`theme:nitrogen_fertilizer_production`: Nitrogen fertilizer production / 氮肥生产

- **Proposed disposition:** KEEP (confidence HIGH)
- **Rationale:** Haber-Bosch nitrogen has gas-cost-driven economics distinct from mined potash and phosphate. No neighbour is flagged.
- **Name quality:** Matches the scope; no naming defect found.
- **Parent paths:** `theme:materials_mining>theme:ag_fertilizer>theme:nitrogen_fertilizer_production`
- **Asserted on / nominated from:** 2026-10-08 / `research:config/theme_thesis_registry.yml`
- **Crosswalk note:** "Haber-Bosch nitrogen segment named separately from potash/phosphate in pathways."
- **scope_version:** `8ce6bbd94e12a5626c5fa12989e971500dad000ee17e029e84d27eca7f6fd898`
- **Baseline coverage:** EMPTY; admitted 0, proposed 0, rejected 0; vendor routes 0, vendor member companies 0; research records none; route kinds none
- **Member companies (probation lane):** none
- **Siblings:** 15 micros share a parent; frozen siblings: `theme:potash_phosphate_nutrients`, `theme:precision_agriculture_platforms`
- **Gate-2 provenance markers:** none
- **Flagged by rule:** none

| nearest neighbour | tier | composite | name_jac | def_jac | name_char3 | zh_bigram | shared parent | shared members |
|---|---|---|---|---|---|---|---|---|
| `theme:water_soluble_fertigation` | DISPLAY_EXPANSION | 0.261 | 0.167 | 0.038 | 0.463 | 0.0 | yes | 0 |
| `theme:green_ammonia_synthesis` | DISPLAY_EXPANSION | 0.24 | 0.143 | 0.125 | 0.292 | 0.0 | yes | 0 |
| `theme:controlled_release_fertilizers` | DISPLAY_EXPANSION | 0.229 | 0.167 | 0.043 | 0.299 | 0.0 | yes | 0 |
| `theme:potash_phosphate_nutrients` | FROZEN_ACCEPTANCE | 0.189 | 0.0 | 0.357 | 0.0 | 0.0 | yes | 0 |
| `theme:medical_isotope_production` | DISPLAY_EXPANSION | 0.177 | 0.2 | 0.042 | 0.358 | 0.125 | no | 0 |

Referenced by: none.

### micro-nuclear_components

`theme:nuclear_components`: Nuclear components / 核电部件

- **Proposed disposition:** KEEP (confidence HIGH)
- **Rationale:** The plant component supply chain. The note only records provenance, but five expansion rows (conventional island, fusion supply chain, EPC, safety I&C, forgings) define themselves against it, so the scope in use is clear.
- **Name quality:** Matches usage. The crosswalk note records provenance only; the scope is fixed by the five expansion rows that define themselves against it.
- **Parent paths:** `theme:energy_power>theme:nuclear_power>theme:nuclear_components`
- **Asserted on / nominated from:** 2026-10-08 / `research:research/energy/nuclear_program/REG-PACKET-2026-09-25-nuclear_power.md`
- **Crosswalk note:** "REG-PACKET slice for plant components supply chain."
- **scope_version:** `6051a89f0cc065935b6726f28a4dae7cd0b75e337d7909e05549af391f935f41`
- **Baseline coverage:** EMPTY; admitted 0, proposed 0, rejected 0; vendor routes 0, vendor member companies 0; research records none; route kinds none
- **Member companies (probation lane):** none
- **Siblings:** 17 micros share a parent; frozen siblings: `theme:fuel_cycle`, `theme:reactor_technology`
- **Gate-2 provenance markers:** none
- **Flagged by rule:** none

| nearest neighbour | tier | composite | name_jac | def_jac | name_char3 | zh_bigram | shared parent | shared members |
|---|---|---|---|---|---|---|---|---|
| `theme:npp_construction_epc` | DISPLAY_EXPANSION | 0.271 | 0.143 | 0.182 | 0.264 | 0.111 | yes | 0 |
| `theme:nuclear_digital_ic` | DISPLAY_EXPANSION | 0.26 | 0.2 | 0.095 | 0.33 | 0.0 | yes | 0 |
| `theme:nuclear_grade_forgings_materials` | DISPLAY_EXPANSION | 0.252 | 0.167 | 0.158 | 0.268 | 0.0 | yes | 0 |
| `theme:fuel_assembly_fabrication` | DISPLAY_EXPANSION | 0.239 | 0.2 | 0.048 | 0.287 | 0.0 | yes | 0 |
| `theme:floating_nuclear_platforms` | DISPLAY_EXPANSION | 0.22 | 0.167 | 0.04 | 0.258 | 0.0 | yes | 0 |

Referenced by:

- `theme:conventional_island_equipment` (DISPLAY_EXPANSION): "...l-to-electric train (turbines, generators, condensers); distinct from nuclear_components (nuclear-side component chain) and reactor_technology (reactor system..."
- `theme:fusion_supply_chain` (DISPLAY_EXPANSION): "...vessels, blankets); distinct from gen4_reactor_systems (fission) and nuclear_components (fission plant parts)."
- `theme:npp_construction_epc` (DISPLAY_EXPANSION): "Civil works, heavy-lift installation, code QA; distinct from nuclear_components (component supply) and transmission_substation_epc (grid-scope EPC)."
- `theme:nuclear_digital_ic` (DISPLAY_EXPANSION): "Safety-class I&C platforms and simulators; distinct from nuclear_components (mechanical components) and fab_automation_cim (manufacturing executi..."
- `theme:nuclear_grade_forgings_materials` (DISPLAY_EXPANSION): "...ualified materials/forgings INTO component fabrication; distinct from nuclear_components (fabricated components) and conventional_island_equipment (machinery)..."

### micro-oral_glp1_formulations

`theme:oral_glp1_formulations`: Oral GLP-1 formulations / 口服GLP-1制剂

- **Proposed disposition:** KEEP (confidence HIGH)
- **Rationale:** The oral modality, distinct from injectables, with its own manufacturing profile. The flag is the injectable class row, which is proposed for RENAME so that the two names stop overlapping.
- **Name quality:** Matches the scope; no naming defect found.
- **Parent paths:** `theme:healthcare_lifesciences>theme:glp1_obesity>theme:glp1_therapy_products>theme:oral_glp1_formulations`; `theme:healthcare_lifesciences>theme:glp1_obesity>theme:oral_glp1_formulations`
- **Asserted on / nominated from:** 2026-10-08 / `basket:baskets:obesity_glp1`
- **Crosswalk note:** "Oral delivery modality distinct from injectable incretin platforms."
- **scope_version:** `7e0a430543ee268b976fc3d220dee30b9b4d330514bf5046edfd87e93fc6a62c`
- **Baseline coverage:** EMPTY; admitted 0, proposed 0, rejected 0; vendor routes 0, vendor member companies 0; research records none; route kinds intermediate
- **Member companies (probation lane):** none
- **Siblings:** 16 micros share a parent; frozen siblings: `theme:cardiorenal_metabolic_indications`, `theme:fill_finish_delivery_devices`, `theme:glp1_api_manufacturing`, `theme:glp1_incretin_therapies`
- **Gate-2 provenance markers:** none
- **Flagged by rule:** `theme:glp1_incretin_therapies` (0.301)

| nearest neighbour | tier | composite | name_jac | def_jac | name_char3 | zh_bigram | shared parent | shared members |
|---|---|---|---|---|---|---|---|---|
| `theme:glp1_incretin_therapies` | FROZEN_ACCEPTANCE | 0.301 | 0.333 | 0.167 | 0.213 | 0.0 | yes | 0 |
| `theme:glp1_api_manufacturing` | FROZEN_ACCEPTANCE | 0.283 | 0.333 | 0.091 | 0.217 | 0.0 | yes | 0 |
| `theme:oral_small_molecule_obesity` | DISPLAY_EXPANSION | 0.246 | 0.125 | 0.211 | 0.145 | 0.1 | yes | 0 |
| `theme:cardiorenal_metabolic_indications` | FROZEN_ACCEPTANCE | 0.141 | 0.0 | 0.0 | 0.206 | 0.0 | yes | 0 |
| `theme:digital_titration_adherence` | DISPLAY_EXPANSION | 0.138 | 0.0 | 0.04 | 0.139 | 0.0 | yes | 0 |

Referenced by: none.

### micro-polysilicon_solar_feedstock

`theme:polysilicon_solar_feedstock`: Polysilicon solar feedstock / 光伏级多晶硅原料

- **Proposed disposition:** KEEP (confidence HIGH)
- **Rationale:** The upstream silicon feedstock segment. No neighbour is flagged. The wafer, ingot and module-materials rows define themselves against it.
- **Name quality:** Matches the scope; no naming defect found.
- **Parent paths:** `theme:energy_power>theme:solar>theme:polysilicon_solar_feedstock`; `theme:energy_power>theme:solar>theme:pv_manufacturing_chain>theme:polysilicon_solar_feedstock`
- **Asserted on / nominated from:** 2026-10-08 / `research:config/trade_flow_codes.yml`
- **Crosswalk note:** "Upstream polysilicon segment named before cells and modules in trade rationale."
- **scope_version:** `292747bc925711d3bdd6402727babe01203267fe846ade0b301c8cf8e31e521b`
- **Baseline coverage:** EMPTY; admitted 0, proposed 0, rejected 0; vendor routes 0, vendor member companies 0; research records none; route kinds intermediate
- **Member companies (probation lane):** none
- **Siblings:** 21 micros share a parent; frozen siblings: `theme:pv_cell_module_manufacturing`, `theme:solar_inverters`, `theme:solar_trackers_bos`
- **Gate-2 provenance markers:** none
- **Flagged by rule:** none

| nearest neighbour | tier | composite | name_jac | def_jac | name_char3 | zh_bigram | shared parent | shared members |
|---|---|---|---|---|---|---|---|---|
| `theme:solar_inverters` | FROZEN_ACCEPTANCE | 0.267 | 0.25 | 0.038 | 0.248 | 0.1 | yes | 0 |
| `theme:pv_silver_paste` | DISPLAY_EXPANSION | 0.216 | 0.125 | 0.077 | 0.195 | 0.071 | yes | 0 |
| `theme:solar_trackers_bos` | FROZEN_ACCEPTANCE | 0.211 | 0.143 | 0.056 | 0.17 | 0.067 | yes | 0 |
| `theme:silicon_ingot_wafer_slicing` | DISPLAY_EXPANSION | 0.17 | 0.0 | 0.19 | 0.036 | 0.077 | yes | 0 |
| `theme:pv_glass_encapsulants` | DISPLAY_EXPANSION | 0.161 | 0.0 | 0.182 | 0.0 | 0.077 | yes | 0 |

Referenced by:

- `theme:large_diameter_silicon_wafers` (DISPLAY_EXPANSION): "Electronic-grade 300mm wafer supply; distinct from polysilicon_solar_feedstock (solar feedstock) and memory_wafer_fab (operates fabs, sells no wafer..."
- `theme:pv_glass_encapsulants` (DISPLAY_EXPANSION): "Module materials (glass, EVA/POE, backsheets); distinct from polysilicon_solar_feedstock (silicon) and pv_cell_module_manufacturing (assembly)."
- `theme:silicon_ingot_wafer_slicing` (DISPLAY_EXPANSION): "Converts feedstock into wafers; distinct from polysilicon_solar_feedstock (produces the silicon) and pv_cell_module_manufacturing (cell/module..."

### micro-potash_phosphate_nutrients

`theme:potash_phosphate_nutrients`: Potash and phosphate nutrients / 钾肥与磷肥

- **Proposed disposition:** KEEP (confidence MEDIUM)
- **Rationale:** Mined-nutrient producers, held apart from nitrogen. A SPLIT into potash and phosphate was considered, but the main listed producers span both, so it would not separate issuers.
- **Name quality:** Matches the scope; no naming defect found.
- **Parent paths:** `theme:materials_mining>theme:ag_fertilizer>theme:potash_phosphate_nutrients`
- **Asserted on / nominated from:** 2026-10-08 / `research:config/theme_pathways.yml`
- **Crosswalk note:** "Pathways names potash and phosphate nutrient producers apart from nitrogen-only fertilizer."
- **scope_version:** `034d731d8d930e7c34c9cf6722c3a7dba2a30ac5a25b8688c7833065f5ec4d20`
- **Baseline coverage:** EMPTY; admitted 0, proposed 0, rejected 0; vendor routes 0, vendor member companies 0; research records none; route kinds none
- **Member companies (probation lane):** none
- **Siblings:** 15 micros share a parent; frozen siblings: `theme:nitrogen_fertilizer_production`, `theme:precision_agriculture_platforms`
- **Gate-2 provenance markers:** none
- **Flagged by rule:** none

| nearest neighbour | tier | composite | name_jac | def_jac | name_char3 | zh_bigram | shared parent | shared members |
|---|---|---|---|---|---|---|---|---|
| `theme:phosphate_rock_mining` | DISPLAY_EXPANSION | 0.238 | 0.167 | 0.095 | 0.278 | 0.0 | yes | 0 |
| `theme:organic_nutrient_recovery` | DISPLAY_EXPANSION | 0.228 | 0.167 | 0.043 | 0.295 | 0.0 | yes | 0 |
| `theme:potash_mining_solutions` | DISPLAY_EXPANSION | 0.217 | 0.167 | 0.095 | 0.175 | 0.0 | yes | 0 |
| `theme:nitrogen_fertilizer_production` | FROZEN_ACCEPTANCE | 0.189 | 0.0 | 0.357 | 0.0 | 0.0 | yes | 0 |
| `theme:micronutrients_soil_conditioners` | DISPLAY_EXPANSION | 0.167 | 0.0 | 0.08 | 0.234 | 0.0 | yes | 0 |

Referenced by: none.

### micro-precision_actuators_servo_motors

`theme:precision_actuators_servo_motors`: Precision actuators and servo motors / 精密执行器与伺服电机

- **Proposed disposition:** KEEP (confidence HIGH)
- **Rationale:** The component bottleneck layer beneath finished robots. No neighbour is flagged, and precision_reducers_gearboxes holds the transmission stage apart.
- **Name quality:** Matches the scope; no naming defect found.
- **Parent paths:** `theme:industrials_defense>theme:robotics_automation>theme:precision_actuators_servo_motors`
- **Asserted on / nominated from:** 2026-10-08 / `research:config/theme_pathways.yml`
- **Crosswalk note:** "Component bottleneck layer distinct from finished robot systems."
- **scope_version:** `00d8c20e901c941814895b8c33dd8c431dd9024b54e9f2e2adfc2e32160bc86d`
- **Baseline coverage:** EMPTY; admitted 0, proposed 0, rejected 0; vendor routes 0, vendor member companies 0; research records none; route kinds none
- **Member companies (probation lane):** none
- **Siblings:** 25 micros share a parent; frozen siblings: `theme:collaborative_robot_arms`, `theme:industrial_motion_controls`, `theme:industrial_robot_arms`, `theme:machine_vision`, `theme:surgical_robotics_systems`
- **Gate-2 provenance markers:** none
- **Flagged by rule:** none

| nearest neighbour | tier | composite | name_jac | def_jac | name_char3 | zh_bigram | shared parent | shared members |
|---|---|---|---|---|---|---|---|---|
| `theme:precision_reducers_gearboxes` | DISPLAY_EXPANSION | 0.287 | 0.167 | 0.185 | 0.321 | 0.091 | yes | 0 |
| `theme:end_effectors_grippers` | DISPLAY_EXPANSION | 0.216 | 0.0 | 0.115 | 0.283 | 0.154 | yes | 0 |
| `theme:machine_vision` | FROZEN_ACCEPTANCE | 0.158 | 0.0 | 0.1 | 0.165 | 0.0 | yes | 0 |
| `theme:industrial_motion_controls` | FROZEN_ACCEPTANCE | 0.148 | 0.0 | 0.05 | 0.175 | 0.0 | yes | 0 |
| `theme:professional_service_robots` | DISPLAY_EXPANSION | 0.143 | 0.0 | 0.031 | 0.178 | 0.0 | yes | 0 |

Referenced by:

- `theme:precision_reducers_gearboxes` (DISPLAY_EXPANSION): "Harmonic/RV speed-reduction transmission between servo and joint; precision_actuators_servo_motors generates the torque, this row reduces speed with arc-minute accuracy..."

### micro-precision_agriculture_platforms

`theme:precision_agriculture_platforms`: Precision agriculture platforms / 精准农业平台

- **Proposed disposition:** KEEP (confidence LOW, LOW-CONFIDENCE)
- **Rationale:** A coherent scope for agronomic data and platforms with no near neighbour; the top score, cbdc_sovereign_currency at 0.170, is a token artefact. But it sits under ag_fertilizer, and agricultural_field_robotics calls it the data layer. Parent placement is outside this rubric and is flagged for follow-up.
- **Name quality:** Matches the scope; no naming defect found.
- **Parent paths:** `theme:materials_mining>theme:ag_fertilizer>theme:precision_agriculture_platforms`
- **Asserted on / nominated from:** 2026-10-08 / `research:config/theme_thesis_registry.yml`
- **Crosswalk note:** "Agronomic data platforms named as downstream of input-cost pressure, not fertilizer molecules."
- **scope_version:** `7bd38760292f36cb78330841cb13e1c0a418d84a618cc070c7643feadd5a3cb8`
- **Baseline coverage:** EMPTY; admitted 0, proposed 0, rejected 0; vendor routes 0, vendor member companies 0; research records none; route kinds none
- **Member companies (probation lane):** none
- **Siblings:** 15 micros share a parent; frozen siblings: `theme:nitrogen_fertilizer_production`, `theme:potash_phosphate_nutrients`
- **Gate-2 provenance markers:** none
- **Flagged by rule:** none

| nearest neighbour | tier | composite | name_jac | def_jac | name_char3 | zh_bigram | shared parent | shared members |
|---|---|---|---|---|---|---|---|---|
| `theme:cbdc_sovereign_currency` | DISPLAY_EXPANSION | 0.17 | 0.167 | 0.029 | 0.432 | 0.091 | no | 0 |
| `theme:digital_banking_platforms` | DISPLAY_EXPANSION | 0.165 | 0.2 | 0.033 | 0.323 | 0.111 | no | 0 |
| `theme:proteomics_discovery_platforms` | FROZEN_ACCEPTANCE | 0.165 | 0.2 | 0.05 | 0.328 | 0.083 | no | 0 |
| `theme:military_aircraft_platforms` | DISPLAY_EXPANSION | 0.164 | 0.2 | 0.038 | 0.311 | 0.111 | no | 0 |
| `theme:rotorcraft_vertical_lift` | DISPLAY_EXPANSION | 0.14 | 0.167 | 0.037 | 0.269 | 0.091 | no | 0 |

Referenced by:

- `theme:agricultural_field_robotics` (DISPLAY_EXPANSION): "...chines: autonomous tractors, weeding/harvest robots on GNSS guidance; precision_agriculture_platforms (ag_fertilizer) is the data layer, this row executes the field work."

### micro-process_metrology_inspection

`theme:process_metrology_inspection`: Process metrology & inspection / 工艺量测与检测

- **Proposed disposition:** KEEP (confidence HIGH)
- **Rationale:** The metrology and inspection tool class. 'Subsystem suppliers' in the note is provenance wording. The ATE and system-level-test rows define themselves against it.
- **Name quality:** Matches the scope. 'Subsystem suppliers' in the note is provenance wording.
- **Parent paths:** `theme:semiconductors_hardware>theme:semicap_equipment>theme:process_metrology_inspection`; `theme:semiconductors_hardware>theme:semicap_equipment>theme:wfe_process_tools>theme:process_metrology_inspection`
- **Asserted on / nominated from:** 2026-10-08 / `basket:baskets:semicap_equipment`
- **Crosswalk note:** "Basket theme highlights metrology subsystem suppliers."
- **scope_version:** `ace060b0986bd9e279ffe9452d9880f037d87567a7c58f931592a821cb34fac2`
- **Baseline coverage:** EMPTY; admitted 0, proposed 0, rejected 0; vendor routes 0, vendor member companies 0; research records none; route kinds intermediate
- **Member companies (probation lane):** none
- **Siblings:** 18 micros share a parent; frozen siblings: `theme:etch_deposition_equipment`, `theme:lithography_tools`, `theme:wafer_fab_subsystems`
- **Gate-2 provenance markers:** none
- **Flagged by rule:** none

| nearest neighbour | tier | composite | name_jac | def_jac | name_char3 | zh_bigram | shared parent | shared members |
|---|---|---|---|---|---|---|---|---|
| `theme:epitaxy_thermal_equipment` | DISPLAY_EXPANSION | 0.214 | 0.167 | 0.038 | 0.23 | 0.0 | yes | 0 |
| `theme:wet_clean_equipment` | DISPLAY_EXPANSION | 0.198 | 0.125 | 0.042 | 0.22 | 0.0 | yes | 0 |
| `theme:wafer_fab_subsystems` | FROZEN_ACCEPTANCE | 0.189 | 0.0 | 0.357 | 0.0 | 0.0 | yes | 0 |
| `theme:equipment_field_services` | DISPLAY_EXPANSION | 0.147 | 0.0 | 0.038 | 0.186 | 0.0 | yes | 0 |
| `theme:etch_deposition_equipment` | FROZEN_ACCEPTANCE | 0.14 | 0.0 | 0.071 | 0.113 | 0.0 | yes | 0 |

Referenced by:

- `theme:semiconductor_ate` (DISPLAY_EXPANSION): "...systems; distinct from ai_chip_osat (performs test as a service) and process_metrology_inspection (optical/process metrology)."
- `theme:system_level_test_services` (DISPLAY_EXPANSION): "Post-assembly device test as a service; distinct from process_metrology_inspection (in-fab wafer control) and from test_ate_equipment (testers for sale)..."

### micro-proteomics_discovery_platforms

`theme:proteomics_discovery_platforms`: Proteomics discovery platforms / 蛋白质组学发现平台

- **Proposed disposition:** KEEP (confidence HIGH)
- **Rationale:** A multi-omics pillar beside sequencing and liquid biopsy. No neighbour is flagged.
- **Name quality:** Matches the scope; no naming defect found.
- **Parent paths:** `theme:healthcare_lifesciences>theme:diagnostics_lifesci>theme:multi_omics_platforms>theme:proteomics_discovery_platforms`; `theme:healthcare_lifesciences>theme:diagnostics_lifesci>theme:proteomics_discovery_platforms`
- **Asserted on / nominated from:** 2026-10-08 / `research:config/theme_thesis_registry.yml`
- **Crosswalk note:** "Proteomics named as a multi-omics pillar beside sequencing and liquid biopsy."
- **scope_version:** `b635005f36c767d5c1b701ba29c4083d2649f0b7e067fdcc3b150dade8d2cf2d`
- **Baseline coverage:** EMPTY; admitted 0, proposed 0, rejected 0; vendor routes 0, vendor member companies 0; research records none; route kinds intermediate
- **Member companies (probation lane):** none
- **Siblings:** 19 micros share a parent; frozen siblings: `theme:diagnostic_reagents_kits`, `theme:genomic_sequencing`, `theme:life_science_lab_instruments`, `theme:liquid_biopsy_assays`
- **Gate-2 provenance markers:** none
- **Flagged by rule:** none

| nearest neighbour | tier | composite | name_jac | def_jac | name_char3 | zh_bigram | shared parent | shared members |
|---|---|---|---|---|---|---|---|---|
| `theme:cbdc_sovereign_currency` | DISPLAY_EXPANSION | 0.168 | 0.167 | 0.029 | 0.439 | 0.071 | no | 0 |
| `theme:digital_banking_platforms` | DISPLAY_EXPANSION | 0.168 | 0.2 | 0.034 | 0.365 | 0.083 | no | 0 |
| `theme:military_aircraft_platforms` | DISPLAY_EXPANSION | 0.167 | 0.2 | 0.04 | 0.351 | 0.083 | no | 0 |
| `theme:precision_agriculture_platforms` | FROZEN_ACCEPTANCE | 0.165 | 0.2 | 0.05 | 0.328 | 0.083 | no | 0 |
| `theme:rotorcraft_vertical_lift` | DISPLAY_EXPANSION | 0.149 | 0.167 | 0.038 | 0.335 | 0.071 | no | 0 |

Referenced by: none.

### micro-pv_cell_module_manufacturing

`theme:pv_cell_module_manufacturing`: Photovoltaic cell and module manufacturing / 光伏电池与组件制造

- **Proposed disposition:** KEEP (confidence HIGH)
- **Rationale:** Combined cell and module volume manufacturing. advanced_cell_manufacturing (0.334) says this row 'stays the combined volume' layer, and pv_manufacturing_equipment (0.377) is the tool layer. Whether either is contained in this row is expansion-tier follow-up.
- **Name quality:** Matches the scope; no naming defect found.
- **Parent paths:** `theme:energy_power>theme:solar>theme:pv_cell_module_manufacturing`; `theme:energy_power>theme:solar>theme:pv_manufacturing_chain>theme:pv_cell_module_manufacturing`
- **Asserted on / nominated from:** 2026-10-08 / `research:config/theme_thesis_registry.yml`
- **Crosswalk note:** "Domestic cell and module manufacturing named separately from upstream silicon and downstream BOS."
- **scope_version:** `5a8d4ef8e0953265c781cf8d668460af2f3c5f50494a69e26cc91e20c7fea68c`
- **Baseline coverage:** EMPTY; admitted 0, proposed 0, rejected 0; vendor routes 0, vendor member companies 0; research records none; route kinds intermediate
- **Member companies (probation lane):** none
- **Siblings:** 21 micros share a parent; frozen siblings: `theme:polysilicon_solar_feedstock`, `theme:solar_inverters`, `theme:solar_trackers_bos`
- **Gate-2 provenance markers:** none
- **Flagged by rule:** `theme:pv_manufacturing_equipment` (0.377), `theme:advanced_cell_manufacturing` (0.334)

| nearest neighbour | tier | composite | name_jac | def_jac | name_char3 | zh_bigram | shared parent | shared members |
|---|---|---|---|---|---|---|---|---|
| `theme:pv_manufacturing_equipment` | DISPLAY_EXPANSION | 0.377 | 0.333 | 0.167 | 0.393 | 0.2 | yes | 0 |
| `theme:advanced_cell_manufacturing` | DISPLAY_EXPANSION | 0.334 | 0.222 | 0.138 | 0.41 | 0.2 | yes | 0 |
| `theme:pv_recycling_circularity` | DISPLAY_EXPANSION | 0.294 | 0.286 | 0.074 | 0.233 | 0.143 | yes | 0 |
| `theme:perovskite_tandem_pv` | DISPLAY_EXPANSION | 0.288 | 0.286 | 0.182 | 0.129 | 0.083 | yes | 0 |
| `theme:memory_module_manufacturing` | DISPLAY_EXPANSION | 0.246 | 0.286 | 0.074 | 0.546 | 0.091 | no | 0 |

Referenced by:

- `theme:advanced_cell_manufacturing` (DISPLAY_EXPANSION): "Cell-technology platform layer (efficiency transitions); pv_cell_module_manufacturing stays the combined volume-manufacturing row; distinct from perovskite..."
- `theme:pv_glass_encapsulants` (DISPLAY_EXPANSION): "...backsheets); distinct from polysilicon_solar_feedstock (silicon) and pv_cell_module_manufacturing (assembly)."
- `theme:pv_silver_paste` (DISPLAY_EXPANSION): "...ization consumables incl. silver-reduction transitions; distinct from pv_cell_module_manufacturing (cell production) and cmp_polishing_consumables (fab slurries)."
- `theme:silicon_ingot_wafer_slicing` (DISPLAY_EXPANSION): "...distinct from polysilicon_solar_feedstock (produces the silicon) and pv_cell_module_manufacturing (cell/module processing)."

### micro-rare_earth_separation_refining

`theme:rare_earth_separation_refining`: Rare-earth separation & refining / 稀土分离与冶炼

- **Proposed disposition:** KEEP (confidence HIGH)
- **Rationale:** Midstream separation and smelting. Its four expansion flags (magnet scrap recycling 0.372, metals and master alloys, ionic-clay leaching, catalysts) are adjacent stages, none a duplicate.
- **Name quality:** Matches the scope; no naming defect found.
- **Parent paths:** `theme:materials_mining>theme:rare_earth_critical_min>theme:rare_earth_processing_magnets>theme:rare_earth_separation_refining`; `theme:materials_mining>theme:rare_earth_critical_min>theme:rare_earth_separation_refining`
- **Asserted on / nominated from:** 2026-10-08 / `research:config/theme_pathways.yml`
- **Crosswalk note:** "Midstream separation and smelting between mined ore and finished magnet alloys, distinct from mining and from NdFeB fabrication."
- **scope_version:** `b37d097a758270eeb8b103f5e9e3c1f5b71f67a2c87364ec36913304702bc1d3`
- **Baseline coverage:** EMPTY; admitted 0, proposed 0, rejected 0; vendor routes 0, vendor member companies 0; research records none; route kinds intermediate
- **Member companies (probation lane):** none
- **Siblings:** 19 micros share a parent; frozen siblings: `theme:critical_mineral_mining_development`, `theme:gallium_germanium_supply_chain`, `theme:ndfeb_permanent_magnets`
- **Gate-2 provenance markers:** none
- **Flagged by rule:** `theme:magnet_scrap_recycling` (0.372), `theme:ree_metals_master_alloys` (0.318), `theme:ion_adsorption_ree_leaching` (0.315), `theme:ree_catalyst_materials` (0.306)

| nearest neighbour | tier | composite | name_jac | def_jac | name_char3 | zh_bigram | shared parent | shared members |
|---|---|---|---|---|---|---|---|---|
| `theme:magnet_scrap_recycling` | DISPLAY_EXPANSION | 0.372 | 0.286 | 0.25 | 0.457 | 0.091 | yes | 0 |
| `theme:ree_metals_master_alloys` | DISPLAY_EXPANSION | 0.318 | 0.25 | 0.185 | 0.328 | 0.091 | yes | 0 |
| `theme:ion_adsorption_ree_leaching` | DISPLAY_EXPANSION | 0.315 | 0.222 | 0.094 | 0.491 | 0.077 | yes | 0 |
| `theme:ree_catalyst_materials` | DISPLAY_EXPANSION | 0.306 | 0.286 | 0.062 | 0.339 | 0.111 | yes | 0 |
| `theme:ree_exploration_resource_definition` | DISPLAY_EXPANSION | 0.294 | 0.2 | 0.091 | 0.428 | 0.077 | yes | 0 |

Referenced by: none.

### micro-reactor_technology

`theme:reactor_technology`: Reactor technology / 反应堆技术

- **Proposed disposition:** KEEP (confidence LOW, LOW-CONFIDENCE)
- **Rationale:** The reactor designers. The note only records provenance and the name is generic, but gen4_reactor_systems keeps this row as 'the SMR/LWR designer slice', and two other rows define themselves against it. A later RENAME could make the LWR/SMR scope explicit.
- **Name quality:** Generic. Acceptable while gen4_reactor_systems carries the Gen-IV split; a later RENAME could make the SMR/LWR designer scope explicit.
- **Parent paths:** `theme:energy_power>theme:nuclear_power>theme:reactor_technology`
- **Asserted on / nominated from:** 2026-10-08 / `research:research/energy/nuclear_program/REG-PACKET-2026-09-25-nuclear_power.md`
- **Crosswalk note:** "REG-PACKET slice key for reactor designers."
- **scope_version:** `2e61d094f56904063c98bd8018a67a7286abbdc243af07f9900e5038c1a2529d`
- **Baseline coverage:** EMPTY; admitted 0, proposed 0, rejected 0; vendor routes 0, vendor member companies 0; research records none; route kinds none
- **Member companies (probation lane):** none
- **Siblings:** 17 micros share a parent; frozen siblings: `theme:fuel_cycle`, `theme:nuclear_components`
- **Gate-2 provenance markers:** none
- **Flagged by rule:** none

| nearest neighbour | tier | composite | name_jac | def_jac | name_char3 | zh_bigram | shared parent | shared members |
|---|---|---|---|---|---|---|---|---|
| `theme:reactor_decommissioning` | DISPLAY_EXPANSION | 0.261 | 0.25 | 0.043 | 0.312 | 0.0 | yes | 0 |
| `theme:gen4_reactor_systems` | DISPLAY_EXPANSION | 0.254 | 0.167 | 0.138 | 0.306 | 0.0 | yes | 0 |
| `theme:grid_forming_inverter_technology` | DISPLAY_EXPANSION | 0.174 | 0.2 | 0.048 | 0.458 | 0.0 | no | 0 |
| `theme:fuel_cycle` | FROZEN_ACCEPTANCE | 0.163 | 0.0 | 0.25 | 0.0 | 0.0 | yes | 0 |
| `theme:nuclear_components` | FROZEN_ACCEPTANCE | 0.163 | 0.0 | 0.25 | 0.0 | 0.0 | yes | 0 |

Referenced by:

- `theme:conventional_island_equipment` (DISPLAY_EXPANSION): "...; distinct from nuclear_components (nuclear-side component chain) and reactor_technology (reactor system design)."
- `theme:gen4_reactor_systems` (DISPLAY_EXPANSION): "...stinct supply chains (helium turbomachinery, sodium, salt chemistry); reactor_technology stays the SMR/LWR designer slice."
- `theme:npp_operations` (DISPLAY_EXPANSION): "Operates units, runs outages, sells wholesale power; distinct from reactor_technology (design) and npp_construction_epc (delivery)."

### micro-refined_copper

`theme:refined_copper`: Refined copper (cathode) / 精炼铜（阴极铜）

- **Proposed disposition:** KEEP (confidence HIGH)
- **Rationale:** Smelting and refining to cathode. Its flags, copper_mining (0.383) and copper_solvent_extraction_ew (0.372), are the upstream stage and an alternative process route, both recorded as distinct.
- **Name quality:** Matches the scope; no naming defect found.
- **Parent paths:** `theme:industrials_defense>theme:copper_steel_electrify>theme:copper_supply_chain>theme:refined_copper`; `theme:industrials_defense>theme:copper_steel_electrify>theme:refined_copper`; `theme:materials_mining>theme:copper_steel_electrify>theme:copper_supply_chain>theme:refined_copper`; `theme:materials_mining>theme:copper_steel_electrify>theme:refined_copper`
- **Asserted on / nominated from:** 2026-10-08 / `research:config/trade_flow_codes.yml`
- **Crosswalk note:** "Smelting and refining to cathode feedstock, distinct from mining and from wire or cable fabrication."
- **scope_version:** `c83797dce791c98d2ec8b1a8c4b9ac8b88b2b6f69934b7d35f08bac040be3907`
- **Baseline coverage:** EMPTY; admitted 0, proposed 0, rejected 0; vendor routes 0, vendor member companies 0; research records none; route kinds intermediate
- **Member companies (probation lane):** none
- **Siblings:** 17 micros share a parent; frozen siblings: `theme:copper_mining`, `theme:copper_wire_cable`, `theme:structural_steel_electrification`
- **Gate-2 provenance markers:** none
- **Flagged by rule:** `theme:copper_mining` (0.383), `theme:copper_solvent_extraction_ew` (0.372)

| nearest neighbour | tier | composite | name_jac | def_jac | name_char3 | zh_bigram | shared parent | shared members |
|---|---|---|---|---|---|---|---|---|
| `theme:copper_mining` | FROZEN_ACCEPTANCE | 0.383 | 0.25 | 0.5 | 0.355 | 0.0 | yes | 0 |
| `theme:copper_solvent_extraction_ew` | DISPLAY_EXPANSION | 0.372 | 0.286 | 0.12 | 0.62 | 0.091 | yes | 0 |
| `theme:copper_wire_cable` | FROZEN_ACCEPTANCE | 0.284 | 0.2 | 0.16 | 0.372 | 0.0 | yes | 0 |
| `theme:secondary_copper_smelting` | DISPLAY_EXPANSION | 0.254 | 0.167 | 0.2 | 0.23 | 0.0 | yes | 0 |
| `theme:copper_byproduct_refining` | DISPLAY_EXPANSION | 0.229 | 0.125 | 0.115 | 0.284 | 0.0 | yes | 0 |

Referenced by: none.

### micro-remote_patient_monitoring

`theme:remote_patient_monitoring`: Remote patient monitoring / 远程患者监测

- **Proposed disposition:** KEEP (confidence HIGH)
- **Rationale:** The continuous-monitoring device and service segment. No neighbour is flagged.
- **Name quality:** Matches the scope; no naming defect found.
- **Parent paths:** `theme:healthcare_lifesciences>theme:medical_devices>theme:ai_clinical_data_devices>theme:remote_patient_monitoring`; `theme:healthcare_lifesciences>theme:medical_devices>theme:remote_patient_monitoring`
- **Asserted on / nominated from:** 2026-10-08 / `research:config/theme_thesis_registry.yml`
- **Crosswalk note:** "Continuous monitoring segment named in mechanism and winner-class vocabulary."
- **scope_version:** `a71f00e9894c33e4fdecf7db13585fac797c4c3b0c2357eb271110559bb08174`
- **Baseline coverage:** EMPTY; admitted 0, proposed 0, rejected 0; vendor routes 0, vendor member companies 0; research records none; route kinds intermediate
- **Member companies (probation lane):** none
- **Siblings:** 18 micros share a parent; frozen siblings: `theme:medical_imaging`, `theme:surgical_implants_instruments`, `theme:surgical_robotics_systems`
- **Gate-2 provenance markers:** none
- **Flagged by rule:** none

| nearest neighbour | tier | composite | name_jac | def_jac | name_char3 | zh_bigram | shared parent | shared members |
|---|---|---|---|---|---|---|---|---|
| `theme:industrial_iot_condition_monitoring` | DISPLAY_EXPANSION | 0.152 | 0.167 | 0.036 | 0.338 | 0.083 | no | 0 |
| `theme:grid_asset_monitoring` | DISPLAY_EXPANSION | 0.151 | 0.143 | 0.042 | 0.383 | 0.067 | no | 0 |
| `theme:respiratory_anesthesia_equipment` | DISPLAY_EXPANSION | 0.139 | 0.0 | 0.042 | 0.141 | 0.0 | yes | 0 |
| `theme:dental_implant_equipment` | DISPLAY_EXPANSION | 0.134 | 0.0 | 0.043 | 0.115 | 0.0 | yes | 0 |
| `theme:medical_imaging` | FROZEN_ACCEPTANCE | 0.128 | 0.0 | 0.045 | 0.083 | 0.0 | yes | 0 |

Referenced by: none.

### micro-satellite_broadband_services

`theme:satellite_broadband_services`: Satellite broadband services / 卫星宽带服务

- **Proposed disposition:** KEEP (confidence HIGH)
- **Rationale:** Subscriber connectivity revenue. The only flag, launch_services (0.305), comes from shared tokens under the same parent. satellite_iot_ntn holds machine traffic apart.
- **Name quality:** Matches the scope; no naming defect found.
- **Parent paths:** `theme:industrials_defense>theme:space_satellite>theme:satellite_broadband_services`; `theme:industrials_defense>theme:space_satellite>theme:satellite_connectivity_services>theme:satellite_broadband_services`
- **Asserted on / nominated from:** 2026-10-08 / `basket:baskets:space_economy`
- **Crosswalk note:** "Subscriber connectivity revenue from satcom where fibre is uneconomic."
- **scope_version:** `1ce60a7fa8c38a4c7881c8ebb5c9398a43bd9439dad93dc6eb10e14ef70e137c`
- **Baseline coverage:** EMPTY; admitted 0, proposed 0, rejected 0; vendor routes 0, vendor member companies 0; research records none; route kinds intermediate
- **Member companies (probation lane):** none
- **Siblings:** 22 micros share a parent; frozen siblings: `theme:direct_to_device_connectivity`, `theme:earth_observation`, `theme:launch_services`, `theme:military_space_communications`, `theme:satellite_ground_terminals`
- **Gate-2 provenance markers:** none
- **Flagged by rule:** `theme:launch_services` (0.305)

| nearest neighbour | tier | composite | name_jac | def_jac | name_char3 | zh_bigram | shared parent | shared members |
|---|---|---|---|---|---|---|---|---|
| `theme:launch_services` | FROZEN_ACCEPTANCE | 0.305 | 0.25 | 0.045 | 0.39 | 0.143 | yes | 0 |
| `theme:military_space_communications` | FROZEN_ACCEPTANCE | 0.275 | 0.167 | 0.1 | 0.366 | 0.091 | yes | 0 |
| `theme:satellite_ground_terminals` | FROZEN_ACCEPTANCE | 0.273 | 0.167 | 0.105 | 0.35 | 0.091 | yes | 0 |
| `theme:satellite_components_payloads` | DISPLAY_EXPANSION | 0.269 | 0.2 | 0.037 | 0.351 | 0.1 | yes | 0 |
| `theme:direct_to_device_connectivity` | FROZEN_ACCEPTANCE | 0.267 | 0.167 | 0.1 | 0.325 | 0.091 | yes | 0 |

Referenced by:

- `theme:satellite_iot_ntn` (DISPLAY_EXPANSION): "Low-power machine traffic over satellite under 3GPP NTN; satellite_broadband_services and direct_to_device_connectivity target broadband and handsets - dif..."

### micro-satellite_ground_terminals

`theme:satellite_ground_terminals`: Satellite ground terminals and equipment / 卫星地面终端与设备

- **Proposed disposition:** KEEP (confidence HIGH)
- **Rationale:** End-user ground hardware. No neighbour is flagged, and ground_station_networks_ttoc holds the gateway/TT&C segment apart.
- **Name quality:** Matches the scope; no naming defect found.
- **Parent paths:** `theme:industrials_defense>theme:space_satellite>theme:satellite_ground_terminals`
- **Asserted on / nominated from:** 2026-10-08 / `research:config/theme_pathways.yml`
- **Crosswalk note:** "Ground segment hardware demand tied to constellation subscriber growth."
- **scope_version:** `752a46ccb5fe8162fd489ab9220a15550cda7e50617cd7358df2c665bd0597e3`
- **Baseline coverage:** EMPTY; admitted 0, proposed 0, rejected 0; vendor routes 0, vendor member companies 0; research records none; route kinds none
- **Member companies (probation lane):** none
- **Siblings:** 22 micros share a parent; frozen siblings: `theme:direct_to_device_connectivity`, `theme:earth_observation`, `theme:launch_services`, `theme:military_space_communications`, `theme:satellite_broadband_services`
- **Gate-2 provenance markers:** none
- **Flagged by rule:** none

| nearest neighbour | tier | composite | name_jac | def_jac | name_char3 | zh_bigram | shared parent | shared members |
|---|---|---|---|---|---|---|---|---|
| `theme:satellite_broadband_services` | FROZEN_ACCEPTANCE | 0.273 | 0.167 | 0.105 | 0.35 | 0.091 | yes | 0 |
| `theme:satellite_components_payloads` | DISPLAY_EXPANSION | 0.251 | 0.167 | 0.074 | 0.287 | 0.083 | yes | 0 |
| `theme:ground_station_networks_ttoc` | DISPLAY_EXPANSION | 0.243 | 0.111 | 0.207 | 0.193 | 0.071 | yes | 0 |
| `theme:military_space_communications` | FROZEN_ACCEPTANCE | 0.241 | 0.143 | 0.045 | 0.322 | 0.077 | yes | 0 |
| `theme:direct_to_device_connectivity` | FROZEN_ACCEPTANCE | 0.233 | 0.143 | 0.095 | 0.217 | 0.077 | yes | 0 |

Referenced by:

- `theme:ground_station_networks_ttoc` (DISPLAY_EXPANSION): "...ound segment: gateway antennas, TT&C, orbit control, pass scheduling; satellite_ground_terminals sells end-user equipment - this row runs the network the constellatio..."

### micro-solar_inverters

`theme:solar_inverters`: Solar inverters / 光伏逆变器

- **Proposed disposition:** KEEP (confidence HIGH)
- **Rationale:** PV DC-to-AC conversion. The flag solar_trackers_bos (0.314) excludes inverters by its own note. The grid-forming and MLPE rows define themselves against it.
- **Name quality:** Matches the scope; no naming defect found.
- **Parent paths:** `theme:energy_power>theme:solar>theme:solar_inverters`
- **Asserted on / nominated from:** 2026-10-08 / `research:config/theme_pathways.yml`
- **Crosswalk note:** "DC-to-AC power conversion for PV arrays, distinct from trackers or balance-of-system hardware and from grid interconnection transformers (lane C1)."
- **scope_version:** `24f4b5239a1f784da2ad73b5e9e47f60316b800ea35f378bf682693cfc203a05`
- **Baseline coverage:** EMPTY; admitted 0, proposed 0, rejected 0; vendor routes 0, vendor member companies 0; research records none; route kinds none
- **Member companies (probation lane):** none
- **Siblings:** 21 micros share a parent; frozen siblings: `theme:polysilicon_solar_feedstock`, `theme:pv_cell_module_manufacturing`, `theme:solar_trackers_bos`
- **Gate-2 provenance markers:** none
- **Flagged by rule:** `theme:solar_trackers_bos` (0.314)

| nearest neighbour | tier | composite | name_jac | def_jac | name_char3 | zh_bigram | shared parent | shared members |
|---|---|---|---|---|---|---|---|---|
| `theme:solar_trackers_bos` | FROZEN_ACCEPTANCE | 0.314 | 0.167 | 0.3 | 0.32 | 0.083 | yes | 0 |
| `theme:polysilicon_solar_feedstock` | FROZEN_ACCEPTANCE | 0.267 | 0.25 | 0.038 | 0.248 | 0.1 | yes | 0 |
| `theme:pv_silver_paste` | DISPLAY_EXPANSION | 0.236 | 0.143 | 0.061 | 0.262 | 0.091 | yes | 0 |
| `theme:grid_forming_inverter_technology` | DISPLAY_EXPANSION | 0.227 | 0.2 | 0.143 | 0.32 | 0.286 | no | 0 |
| `theme:mlpe_power_electronics` | DISPLAY_EXPANSION | 0.19 | 0.0 | 0.094 | 0.333 | 0.0 | yes | 0 |

Referenced by:

- `theme:grid_forming_inverter_technology` (DISPLAY_EXPANSION): "...d-forming capability class specified in new grid codes; distinct from solar_inverters (grid-following PV product) and from storage plants."
- `theme:mlpe_power_electronics` (DISPLAY_EXPANSION): "Per-panel device class with rooftop safety mechanism; distinct from solar_inverters (string/central architectures)."
- `theme:solar_trackers_bos` (FROZEN_ACCEPTANCE): "Mechanical trackers and non-inverter BOS hardware; inverters are solar_inverters."

### micro-solar_trackers_bos

`theme:solar_trackers_bos`: Solar trackers & balance-of-system / 光伏跟踪支架与系统配套

- **Proposed disposition:** KEEP (confidence HIGH)
- **Rationale:** Mechanical trackers and non-inverter BOS hardware. The pair with solar_inverters is an explicit mutual distinction.
- **Name quality:** Matches the scope; no naming defect found.
- **Parent paths:** `theme:energy_power>theme:solar>theme:solar_trackers_bos`
- **Asserted on / nominated from:** 2026-10-08 / `research:config/theme_thesis_registry.yml`
- **Crosswalk note:** "Mechanical trackers and non-inverter BOS hardware; inverters are solar_inverters."
- **scope_version:** `cc23aa3f49887452831cf17f27a43a3b746fca5ac43188f8d1e8b3d5b0bd996a`
- **Baseline coverage:** EMPTY; admitted 0, proposed 0, rejected 0; vendor routes 0, vendor member companies 0; research records none; route kinds none
- **Member companies (probation lane):** none
- **Siblings:** 21 micros share a parent; frozen siblings: `theme:polysilicon_solar_feedstock`, `theme:pv_cell_module_manufacturing`, `theme:solar_inverters`
- **Gate-2 provenance markers:** none
- **Flagged by rule:** `theme:solar_inverters` (0.314)

| nearest neighbour | tier | composite | name_jac | def_jac | name_char3 | zh_bigram | shared parent | shared members |
|---|---|---|---|---|---|---|---|---|
| `theme:solar_inverters` | FROZEN_ACCEPTANCE | 0.314 | 0.167 | 0.3 | 0.32 | 0.083 | yes | 0 |
| `theme:solar_storage_integration` | DISPLAY_EXPANSION | 0.249 | 0.222 | 0.083 | 0.184 | 0.071 | yes | 0 |
| `theme:polysilicon_solar_feedstock` | FROZEN_ACCEPTANCE | 0.211 | 0.143 | 0.056 | 0.17 | 0.067 | yes | 0 |
| `theme:pv_silver_paste` | DISPLAY_EXPANSION | 0.193 | 0.1 | 0.038 | 0.179 | 0.062 | yes | 0 |
| `theme:pv_project_development_epc` | DISPLAY_EXPANSION | 0.148 | 0.0 | 0.19 | 0.0 | 0.0 | yes | 0 |

Referenced by:

- `theme:pv_project_development_epc` (DISPLAY_EXPANSION): ".../commissioning; distinct from pv_operations_maintenance (operate) and solar_trackers_bos (BOS hardware supply)."

### micro-structural_steel_electrification

`theme:structural_steel_electrification`: Structural steel for electrification build-out / 电气化建设用结构钢

- **Proposed disposition:** KEEP (confidence LOW, LOW-CONFIDENCE)
- **Rationale:** A demand-driver scope: steel for grid and EV infrastructure. The name says structural steel while the note says steel plate, and listed steelmakers' exposure to this demand is diluted. There is no near-duplicate. Revisit as a RENAME, or a RETIRE, if no issuer set separates from general steel.
- **Name quality:** Imprecise. The name says structural steel, the note says steel plate.
- **Parent paths:** `theme:industrials_defense>theme:copper_steel_electrify>theme:structural_steel_electrification`; `theme:materials_mining>theme:copper_steel_electrify>theme:structural_steel_electrification`
- **Asserted on / nominated from:** 2026-10-08 / `research:config/trade_flow_codes.yml`
- **Crosswalk note:** "Steel plate demand tied to grid and EV infrastructure, not copper mining."
- **scope_version:** `91c29fc6ad610626b7d7921f8a8e9593b21a4ac2bbd9e15bcac3536de2e8878c`
- **Baseline coverage:** EMPTY; admitted 0, proposed 0, rejected 0; vendor routes 0, vendor member companies 0; research records none; route kinds none
- **Member companies (probation lane):** none
- **Siblings:** 17 micros share a parent; frozen siblings: `theme:copper_mining`, `theme:copper_wire_cable`, `theme:refined_copper`
- **Gate-2 provenance markers:** none
- **Flagged by rule:** none

| nearest neighbour | tier | composite | name_jac | def_jac | name_char3 | zh_bigram | shared parent | shared members |
|---|---|---|---|---|---|---|---|---|
| `theme:mining_fleet_electrification` | DISPLAY_EXPANSION | 0.244 | 0.125 | 0.062 | 0.425 | 0.0 | yes | 0 |
| `theme:electrical_steel_goes_noes` | DISPLAY_EXPANSION | 0.24 | 0.125 | 0.069 | 0.395 | 0.0 | yes | 0 |
| `theme:steel_service_centers` | DISPLAY_EXPANSION | 0.195 | 0.111 | 0.036 | 0.237 | 0.0 | yes | 0 |
| `theme:rail_traction_electrification` | DISPLAY_EXPANSION | 0.186 | 0.111 | 0.16 | 0.392 | 0.143 | no | 0 |
| `theme:building_electrification_heatpumps` | DISPLAY_EXPANSION | 0.174 | 0.111 | 0.037 | 0.464 | 0.167 | no | 0 |

Referenced by: none.

### micro-surgical_implants_instruments

`theme:surgical_implants_instruments`: Surgical implants and instruments / 外科植入物与器械

- **Proposed disposition:** KEEP (confidence HIGH)
- **Rationale:** Implant and instrument makers, distinct from surgical robotics. The flag surgical_energy_endoscopy (0.415, expansion) is a carve-out recorded as expansion-tier follow-up.
- **Name quality:** Matches the scope; no naming defect found.
- **Parent paths:** `theme:healthcare_lifesciences>theme:medical_devices>theme:surgical_implants_instruments`
- **Asserted on / nominated from:** 2026-10-08 / `research:config/theme_pathways.yml`
- **Crosswalk note:** "Implant and instrument manufacturers named without adopting the robotics platform lane."
- **scope_version:** `82144aa26fe38e57d4d01f7dd5caefa2c7dc77d5416034df6c458b9ad8d4661f`
- **Baseline coverage:** EMPTY; admitted 0, proposed 0, rejected 0; vendor routes 0, vendor member companies 0; research records none; route kinds none
- **Member companies (probation lane):** none
- **Siblings:** 18 micros share a parent; frozen siblings: `theme:medical_imaging`, `theme:remote_patient_monitoring`, `theme:surgical_robotics_systems`
- **Gate-2 provenance markers:** none
- **Flagged by rule:** `theme:surgical_energy_endoscopy` (0.415)

| nearest neighbour | tier | composite | name_jac | def_jac | name_char3 | zh_bigram | shared parent | shared members |
|---|---|---|---|---|---|---|---|---|
| `theme:surgical_energy_endoscopy` | DISPLAY_EXPANSION | 0.415 | 0.333 | 0.211 | 0.546 | 0.182 | yes | 0 |
| `theme:surgical_robotics_systems` | FROZEN_ACCEPTANCE | 0.27 | 0.2 | 0.188 | 0.263 | 0.0 | yes | 0 |
| `theme:neuromodulation_implants` | DISPLAY_EXPANSION | 0.267 | 0.2 | 0.087 | 0.295 | 0.083 | yes | 0 |
| `theme:dental_implant_equipment` | DISPLAY_EXPANSION | 0.262 | 0.2 | 0.045 | 0.403 | 0.0 | yes | 0 |
| `theme:wound_care_advanced_dressings` | DISPLAY_EXPANSION | 0.201 | 0.125 | 0.042 | 0.234 | 0.0 | yes | 0 |

Referenced by: none.

### micro-surgical_robotics_systems

`theme:surgical_robotics_systems`: Surgical robotics systems / 手术机器人系统

- **Proposed disposition:** KEEP (confidence HIGH)
- **Rationale:** Hospital surgical robot platforms. No neighbour is flagged, and rehab_exoskeleton_robotics holds the non-surgical case apart.
- **Name quality:** Matches the scope; no naming defect found.
- **Parent paths:** `theme:healthcare_lifesciences>theme:medical_devices>theme:surgical_robotics_systems`; `theme:industrials_defense>theme:robotics_automation>theme:surgical_robotics_systems`
- **Asserted on / nominated from:** 2026-10-08 / `basket:baskets:robotics_automation`
- **Crosswalk note:** "Hospital surgical robotics spans the automation thesis and the medical-device platform cycle."
- **scope_version:** `c7d0b16c839a6f54d3304e5e19590807daacc1fa1d9f86e0b882ac7a3435e86e`
- **Baseline coverage:** EMPTY; admitted 0, proposed 0, rejected 0; vendor routes 0, vendor member companies 0; research records none; route kinds none
- **Member companies (probation lane):** none
- **Siblings:** 43 micros share a parent; frozen siblings: `theme:collaborative_robot_arms`, `theme:industrial_motion_controls`, `theme:industrial_robot_arms`, `theme:machine_vision`, `theme:medical_imaging`, `theme:precision_actuators_servo_motors`, `theme:remote_patient_monitoring`, `theme:surgical_implants_instruments`
- **Gate-2 provenance markers:** none
- **Flagged by rule:** none

| nearest neighbour | tier | composite | name_jac | def_jac | name_char3 | zh_bigram | shared parent | shared members |
|---|---|---|---|---|---|---|---|---|
| `theme:medical_imaging` | FROZEN_ACCEPTANCE | 0.295 | 0.2 | 0.087 | 0.417 | 0.1 | yes | 0 |
| `theme:agricultural_field_robotics` | DISPLAY_EXPANSION | 0.289 | 0.2 | 0.065 | 0.346 | 0.167 | yes | 0 |
| `theme:robot_software_middleware` | DISPLAY_EXPANSION | 0.284 | 0.143 | 0.033 | 0.377 | 0.25 | yes | 0 |
| `theme:surgical_implants_instruments` | FROZEN_ACCEPTANCE | 0.27 | 0.2 | 0.188 | 0.263 | 0.0 | yes | 0 |
| `theme:construction_robotics` | DISPLAY_EXPANSION | 0.25 | 0.167 | 0.034 | 0.247 | 0.167 | yes | 0 |

Referenced by:

- `theme:rehab_exoskeleton_robotics` (DISPLAY_EXPANSION): "...sisting bodies outside surgery: gait training, mobility exoskeletons; surgical_robotics_systems operates inside patients during procedures."

### micro-transmission_hvdc_cabling

`theme:transmission_hvdc_cabling`: Transmission & HVDC cabling / 输电与 HVDC 电缆

- **Proposed disposition:** KEEP (confidence HIGH)
- **Rationale:** Insulated HV/HVDC cable systems with long lead times. No neighbour is flagged. Four rows (overhead conductors, copper wire and cable, converter stations, UHV transmission) define themselves against it.
- **Name quality:** Matches the scope; no naming defect found.
- **Parent paths:** `theme:energy_power>theme:grid_electrification>theme:transmission_hvdc_cabling`
- **Asserted on / nominated from:** 2026-10-08 / `research:config/theme_thesis_registry.yml`
- **Crosswalk note:** "HVDC and specialized cable segment with long lead times."
- **scope_version:** `83b1598db60ee2a418077ee85645a95b3060b7917042f20b2ec436cacea8b836`
- **Baseline coverage:** EMPTY; admitted 0, proposed 0, rejected 0; vendor routes 0, vendor member companies 0; research records none; route kinds none
- **Member companies (probation lane):** none
- **Siblings:** 21 micros share a parent; frozen siblings: `theme:grid_distribution_automation`, `theme:hv_transformers_switchgear`
- **Gate-2 provenance markers:** none
- **Flagged by rule:** none

| nearest neighbour | tier | composite | name_jac | def_jac | name_char3 | zh_bigram | shared parent | shared members |
|---|---|---|---|---|---|---|---|---|
| `theme:uhv_transmission` | DISPLAY_EXPANSION | 0.298 | 0.167 | 0.167 | 0.406 | 0.083 | yes | 0 |
| `theme:hvdc_converter_stations` | DISPLAY_EXPANSION | 0.261 | 0.167 | 0.235 | 0.219 | 0.0 | yes | 0 |
| `theme:transmission_substation_epc` | DISPLAY_EXPANSION | 0.251 | 0.143 | 0.043 | 0.453 | 0.0 | yes | 0 |
| `theme:advanced_overhead_conductors` | DISPLAY_EXPANSION | 0.15 | 0.0 | 0.2 | 0.0 | 0.0 | yes | 0 |
| `theme:grid_asset_monitoring` | DISPLAY_EXPANSION | 0.15 | 0.0 | 0.042 | 0.118 | 0.077 | yes | 0 |

Referenced by:

- `theme:advanced_overhead_conductors` (DISPLAY_EXPANSION): "Bare overhead conductor technology; distinct from transmission_hvdc_cabling (insulated underground/submarine cable) and from line-rating sensors."
- `theme:copper_wire_cable` (FROZEN_ACCEPTANCE): "...-voltage transmission cable systems belong under grid_electrification:transmission_hvdc_cabling (lane C1)."
- `theme:hvdc_converter_stations` (DISPLAY_EXPANSION): "Converter power electronics and stations; distinct from transmission_hvdc_cabling (cable systems) - the two halves of an HVDC link."
- `theme:uhv_transmission` (DISPLAY_EXPANSION): "...kV DC; distinct from hv_transformers_switchgear (equipment class) and transmission_hvdc_cabling (cable links)."

### micro-ups_power_conversion

`theme:ups_power_conversion`: UPS & power conversion / UPS 与电力转换

- **Proposed disposition:** KEEP (confidence HIGH)
- **Rationale:** Facility UPS and on-site conversion. No neighbour is flagged. Five expansion rows (power silicon, gensets, battery backup, DC architecture, server PSUs) define themselves against it.
- **Name quality:** Matches the scope; no naming defect found.
- **Parent paths:** `theme:energy_power>theme:data_center_power>theme:ups_power_conversion`; `theme:technology_software>theme:data_center_power>theme:ups_power_conversion`
- **Asserted on / nominated from:** 2026-10-08 / `research:config/theme_thesis_registry.yml`
- **Crosswalk note:** "Distinct from switchgear: on-site conversion and UPS integration."
- **scope_version:** `ea2d95295e3ad0899be59d37985f2a490a27812f73961e35615f243a8e603d8e`
- **Baseline coverage:** EMPTY; admitted 0, proposed 0, rejected 0; vendor routes 0, vendor member companies 0; research records none; route kinds none
- **Member companies (probation lane):** none
- **Siblings:** 17 micros share a parent; frozen siblings: `theme:hv_transformers_switchgear`, `theme:liquid_cooling_thermal`
- **Gate-2 provenance markers:** none
- **Flagged by rule:** none

| nearest neighbour | tier | composite | name_jac | def_jac | name_char3 | zh_bigram | shared parent | shared members |
|---|---|---|---|---|---|---|---|---|
| `theme:prefab_power_modules` | DISPLAY_EXPANSION | 0.249 | 0.167 | 0.091 | 0.215 | 0.125 | yes | 0 |
| `theme:server_power_supplies` | DISPLAY_EXPANSION | 0.247 | 0.143 | 0.143 | 0.307 | 0.0 | yes | 0 |
| `theme:behind_meter_generation` | DISPLAY_EXPANSION | 0.222 | 0.143 | 0.077 | 0.261 | 0.0 | yes | 0 |
| `theme:dc_hvdc_power_architecture` | DISPLAY_EXPANSION | 0.213 | 0.125 | 0.13 | 0.184 | 0.0 | yes | 0 |
| `theme:ai_power_delivery_silicon` | DISPLAY_EXPANSION | 0.186 | 0.167 | 0.222 | 0.358 | 0.0 | no | 0 |

Referenced by:

- `theme:ai_power_delivery_silicon` (DISPLAY_EXPANSION): "Package/board-level power silicon (multiphase, IVR); distinct from ups_power_conversion and hv_transformers_switchgear (facility power hardware)."
- `theme:backup_generator_sets` (DISPLAY_EXPANSION): "Emergency standby gensets and paralleling; distinct from ups_power_conversion (electronic ride-through) and behind_meter_generation (continuous sel..."
- `theme:dc_battery_backup` (DISPLAY_EXPANSION): "...orage element of the ride-through chain incl. rack BBU; distinct from ups_power_conversion (conversion electronics) and grid_storage_integration (grid assets)."
- `theme:dc_hvdc_power_architecture` (DISPLAY_EXPANSION): "...rchitecture and integrated transformer-rectifier units; distinct from ups_power_conversion (UPS product stage) and busway_smart_pdu (rack distribution)."
- `theme:server_power_supplies` (DISPLAY_EXPANSION): "Rack-level conversion products (PSU/power shelf); distinct from ups_power_conversion (facility UPS) and dc_hvdc_power_architecture (the bus feeding them)."

### micro-wafer_fab_subsystems

`theme:wafer_fab_subsystems`: Wafer-fab subsystems & components / 晶圆厂设备子系统与零部件

- **Proposed disposition:** KEEP (confidence HIGH)
- **Rationale:** The subsystem and component supplier layer beneath process tools. The flag vacuum_subsystem_components (0.473) calls itself a class within this layer, which is an expansion-tier containment follow-up.
- **Name quality:** Matches the scope; no naming defect found.
- **Parent paths:** `theme:semiconductors_hardware>theme:semicap_equipment>theme:wafer_fab_subsystems`
- **Asserted on / nominated from:** 2026-10-08 / `basket:baskets:semicap_equipment`
- **Crosswalk note:** "Basket theme names subsystem suppliers as a layer distinct from process tools."
- **scope_version:** `d90fccdf57dc03d63576c98c5a16738a56d2da54edd792351d8b4c18301fa3c1`
- **Baseline coverage:** EMPTY; admitted 0, proposed 0, rejected 0; vendor routes 0, vendor member companies 0; research records none; route kinds none
- **Member companies (probation lane):** none
- **Siblings:** 18 micros share a parent; frozen siblings: `theme:etch_deposition_equipment`, `theme:lithography_tools`, `theme:process_metrology_inspection`
- **Gate-2 provenance markers:** none
- **Flagged by rule:** `theme:vacuum_subsystem_components` (0.473)

| nearest neighbour | tier | composite | name_jac | def_jac | name_char3 | zh_bigram | shared parent | shared members |
|---|---|---|---|---|---|---|---|---|
| `theme:vacuum_subsystem_components` | DISPLAY_EXPANSION | 0.473 | 0.4 | 0.25 | 0.622 | 0.231 | yes | 0 |
| `theme:rf_power_matching_subsystems` | DISPLAY_EXPANSION | 0.284 | 0.143 | 0.136 | 0.373 | 0.125 | yes | 0 |
| `theme:fab_facility_systems` | DISPLAY_EXPANSION | 0.254 | 0.143 | 0.115 | 0.318 | 0.059 | yes | 0 |
| `theme:wet_clean_equipment` | DISPLAY_EXPANSION | 0.243 | 0.111 | 0.167 | 0.18 | 0.133 | yes | 0 |
| `theme:fab_automation_cim` | DISPLAY_EXPANSION | 0.207 | 0.143 | 0.038 | 0.104 | 0.133 | yes | 0 |

Referenced by:

- `theme:advanced_packaging_equipment` (DISPLAY_EXPANSION): "...ls); distinct from advanced_packaging_2_5d_3d (packaging service) and wafer_fab_subsystems (front-end subsystems)."
- `theme:equipment_field_services` (DISPLAY_EXPANSION): "Installed-base service/retrofit revenue; distinct from wafer_fab_subsystems (component supply) and refurbished_equipment_market (used-tool resale..."
- `theme:vacuum_subsystem_components` (DISPLAY_EXPANSION): "Vacuum generation/flow component class within the broad wafer_fab_subsystems layer; a recognized standalone parts segment."
