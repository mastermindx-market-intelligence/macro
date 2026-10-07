# Micro-theme membership census — GMI hierarchy V1.1 input (2026-10-07)

Program: GMI Theme Graph (WS:GMI-THEME-GRAPH)  
Commissioned by: orchestrator K under the GMI Meta-CEO seat  
Tree audited: origin/main 70d2bef9662618d9209aad40b534e2fb8ef10864  
Status: READ-ONLY census — no code, no data write, display-tier design input only  

VERDICT_LINE: CENSUS_DONE q=6/6

## Q1. Readers of data/baskets/membership.json

Production readers iterate the full `baskets` object unless a filter is noted. Adding a new US basket (including a hypothetical `{tier:"micro", parent_basket:"<id>"}` row with its own `members`) would enlarge any consumer that builds per-basket OHLCV, turn state, pulse, or theme-graph MEMBER_OF edges for that basket id. It would **not** by itself attach tickers to a `micro_theme` node until a crosswalk EXPRESSES edge and hierarchy PARENT_OF exist (`research/theme_graph/THEME_HIERARCHY_SPEC_V1_2026-10-07.md:29-30`).

| reader path:line | all-baskets or subset | output artifact / site rows affected by one new micro-tier basket |
|---|---|---|
| `engine/theme_graph/materialize.py:617-621` | **All baskets** in each suite document (`for basket in baskets.values()` via `build_family`) | New `MEMBER_OF` edges in `data/theme_graph/edges.parquet` for basket id if suite is `baskets` and crosswalk maps theme (`config/theme_crosswalk.yml` EXPRESSES); nodes unchanged until crosswalk admits basket |
| `scripts/build_baskets.py:538-544` | **All** `data.get("baskets", [])` for OHLCV/member sweep | `data/baskets/ohlcv/<T>.parquet`, `site/basketdata/*.json` legs that include the new basket id |
| `engine/group_pulse.py:347-351` | **Subset**: drops `cn_`/`hk_`/`ca_` prefixes (`NON_US_PREFIXES`, `engine/group_pulse.py:350-351`) | `site/marketdata/group_pulse.json` (and related pulse consumers) gain a basket row if id is US-prefixed |
| `engine/us_basket_turn.py:656-659` | **Subset**: same `cn_`/`hk_`/`ca_` filter (`engine/us_basket_turn.py:282-283`, `656-659`) | `site/basketdata/us_basket_turn.json`, ledger under `data/basket_turn/` |
| `engine/top_maturation.py:1238-1240` | **Subset**: drops non-US **and** `us_sector_*` (`engine/top_maturation.py:284`, `1238-1240`) | Maturation/top-age surfaces keyed by theme basket id |
| `engine/us_sector_rotation.py:735-739` | Loads full doc; **thematic** path skips `b-us_sector_*` duplicate ETF legs (`engine/us_sector_rotation.py:798`) | `data/us_sector_rotation/latest.json` only if basket wired into rotation map |
| `engine/neuralweb/thematic_state.py:500-507` | Reads full `membership.json` for ticker overlap with narratives | Thematic state overlays (display-tier), not micro paths |
| `engine/neuralweb/sector_map.py:128-142` | **Subset**: only baskets present in `panel_m` node set (`engine/neuralweb/sector_map.py:131-134`) | Sponsorship `subsector_node` mapping in neuralweb bottom sensors |
| `engine/flow_cohorts.py:88-91` | **Named cohort keys** mapped to specific basket ids in module constants | `site/marketdata/flow_cohorts.json` only if new id added to cohort map |
| `engine/options_universe.py:31-34` | **All active members** across all baskets | Options screener universe expansion |
| `scripts/fetch_basket_ohlcv.py:96` | **All members** aggregated from full membership | Price fetch queue for new tickers |
| `scripts/build_portfolio_ctx.py:264-274` | **All baskets**, PIT-filtered per member `added`/`removed` | Portfolio context basket membership legs |
| `tests/test_company_theme_exposure.py:176` | Pins **49** basket count on live file | CI regression if basket count changes without test update |
| `tests/test_thematic_state.py:88-106` | Crosswalk `primary_basket_id` ⊆ membership keys | CI fails if crosswalk references missing basket |
| `tests/test_us_basket_membership_pit.py:5-6` | Documents **49** US baskets + PIT store | Fixture contract for `engine/basket_membership_pit.py` |

Absence: **no** `app/` import of `data/baskets/membership.json` on HEAD (`git grep -l 'baskets/membership.json' HEAD -- app/` → empty).

## Q2. Existing basket filters and skips

| mechanism | evidence |
|---|---|
| Non-US basket id prefixes `cn_`, `hk_`, `ca_` excluded from US desk pipelines | `engine/us_basket_turn.py:282-283` defines `_NON_US_PREFIXES`; `656-659` filters |
| Same prefix filter in group pulse loader | `engine/group_pulse.py:350-351` |
| GICS equal-weight sector baskets `us_sector_*` excluded from “theme” maturation universe | `engine/top_maturation.py:284` `_NON_THEME_BASKET_PREFIXES = ("us_sector_",)`; `1238-1240` |
| Turn watch prefers non-`us_sector_` themed baskets | `engine/us_turn_watch.py:1151` `themed = [b for b in pool if not b.startswith("us_sector_")] or pool` |
| Sector rotation skips duplicate `b-us_sector_*` basket legs when ETF path covers sector | `engine/us_sector_rotation.py:798` |
| `sector_map` subsector arm ignores baskets not in `panel_m` | `engine/neuralweb/sector_map.py:131-134` |
| HIERARCHY_BLOCK excludes category `US Sectors (EW)` from semantic navigation | `research/theme_graph/hierarchy_content/HIERARCHY_BLOCK_V1.yaml:10` |

No consumer on HEAD reads a `tier:"micro"` field — **NOT FOUND** (searched: `git grep -n 'tier.*micro' HEAD -- engine/ scripts/ config/`).

## Q3. Basket PIT, admission and back-fill

**Document-level PIT fields** (`git show HEAD:data/baskets/membership.json` → keys `seed_date`, `history_note`, `added_semantics`, per-basket `created`, per-member `added`/`removed`/`curated_added`):

- `seed_date` = `2023-05-09`; `history_note` states baskets curated after seed_date are **back-projected** with current roster (`data/baskets/membership.json:seed_date`, `history_note` via `git show`).
- `added_semantics` documents admission semantics (same git show).

**US PIT store:** `engine/basket_membership_pit.py:48-56` — US suite `baskets` advanced only on nightly lane; append-only `membership_history.parquet`; `members_asof` falls back to current `membership.json` with `pit=False` before first snapshot (`engine/basket_membership_pit.py:73-77`).

**Thematic / rotation back-fill:** Consumers using raw `membership.json` without `members_asof` inherit **current** roster — explicit in `scripts/prophet_postmortem.py:57` (“membership.json is a single current file with no per-date history”). `contracts/theme_graph/README.md:60-66` labels `seed_constant` / reconstruction era edges as non-observational for promotion.

**DEC/DSC/DNR rows (basket PIT / admission):**

- `tests/test_us_basket_membership_pit.py:5-11` — problem statement: mutable 49-basket doc + look-ahead risk.
- `engine/basket_membership_pit.py:4-12` — CN charter reference; US mirror rationale.
- NOT FOUND in `agentos/decisions/` for US basket admission date policy beyond above (searched: `git grep -n 'basket.*PIT\|membership.json.*history' HEAD -- agentos/`).

A basket **added today** would: (1) appear in nightly `membership.json` with `created` / member `added` ≥ today; (2) get first `membership_history` snapshot on next successful `build_baskets --snapshot` when content hash changes (`engine/basket_membership_pit.py:28-33`); (3) still be **back-projected** in basket level charts per `history_note` unless consumers switch to PIT reader — **no automatic micro-theme `valid_from`** without crosswalk `asserted_on` (`research/theme_graph/THEME_HIERARCHY_SPEC_V1_2026-10-07.md:65-66`).

## Q4. House-owned sub-theme ticker groupings (federation candidates)

Gate #2: `data/themes_heatmap/perf_snapshot.json` is **Finviz-derived** (`engine/subsector_rotation.py:3-9`, `"source": "finviz-themes"` at `engine/subsector_rotation.py:363`) — **internal-only vendor input** for structure; compare coverage only, never micro membership source.

| grouping | path:line | owner | lists tickers? (count) | #groups | rights / provenance | name overlap with 69 micro ids |
|---|---|---|---:|---:|---|---|
| Curated US theme baskets | `data/baskets/membership.json` (`baskets.*.members`) | Mastermind curation / nightly lane | yes (~49 baskets; member count varies) | 49 | `mastermind_curated` (`tests/test_theme_graph_materialize.py:427-428`) | PROXY only via `primary_basket_id` — no id equals micro slug (Q5: 0 IDENTITY) |
| Theme crosswalk primary baskets | `config/theme_crosswalk.yml` themes[].primary_basket_id | GMI / crosswalk PRs | indirect (via basket members) | 18 themes | `mastermind_curated` | Maps **theme** tier only on HEAD (`config/theme_crosswalk.yml:520-523` `micro_themes: []`) |
| Semiconductors vertical slices (#7870) | NOT ON HEAD — nominated_from refs `vertical:theme_research_registry:*` in `research/theme_graph/hierarchy_content/HIERARCHY_BLOCK_V1.yaml:69-76` | #7870 owner (not merged) | slice_keys carry cohorts in that PR; **absent here** | 2 nominated slices on main block | house vertical registry (future) | `hbm_packaging`, `sic_gan_specialty`, `gpu_merchant_accelerators`, `ai_interconnect_silicon`, `custom_asic_silicon`, … semicap micros |
| Mining M1 domain slices | `research/mining/m1_integration_program/domain/MINING_DOMAIN_DEFINITIONS_M1_2026-09-24.md` | Mining program | yes (domain cohorts) | 2 slice_keys in doc | house research registry | `copper_mining`, `refined_copper`, `rare_earth_*`, `critical_mineral_mining_development`, `gallium_germanium_supply_chain` |
| Nuclear program slices | `research/energy/nuclear_program/` (tests parametrize slice_keys) | Energy vertical | yes in tests | multiple SLICES in program | house research | `reactor_technology`, `nuclear_components`, `fuel_cycle` |
| Defense equity driver taxonomy | `research/defense_intelligence/D0R_DEFENSE_EQUITY_DRIVER_TAXONOMY.md` | Defense research | archetype groups (not full ticker store on HEAD audit) | taxonomy rows | house research | defense micro ids (`missiles_*`, `naval_shipbuilding`, …) |
| Nasdaq/Russell amalgamations | `data/baskets_nasdaq/membership.json`, `data/baskets_russell/membership.json` via `engine/cycle_pattern/registry.py:126-135` | subsector rotation lane | yes | 8 + 11 groups | house constructed | partial — industrial/tech names, not 1:1 micro slugs |
| `theme_pathways.yml` | `config/theme_pathways.yml` (themes list) | theme pathways config | **no tickers** — narrative pathways | themes only | house config | thematic labels only, not micro slugs |
| `theme_thesis_registry.yml` | `config/theme_thesis_registry.yml` | GMI thesis registry | no ticker lists | thesis rows | house | textual overlap only |
| GICS sector panels via breadth | `engine/neuralweb/sector_map.py:85-103` | breadth parquets | yes (~1500 names) | 11 sectors | house/GICS | sector grain, not micro |

## Q5. Micro-to-basket identity table

On HEAD, `config/theme_crosswalk.yml` has `hierarchy.micro_themes: []` (`config/theme_crosswalk.yml:520-523`) — all 69 micros exist only in `research/theme_graph/hierarchy_content/HIERARCHY_BLOCK_V1.yaml` pending W-C4. **0 IDENTITY**, **49 PROXY** (parent `primary_basket_id`), **20 NONE** (parent themes without `primary_basket_id`: `medical_devices`, `copper_steel_electrify`, `ag_fertilizer`, `diagnostics_lifesci`, `solar`).

| micro_id | parent theme | IDENTITY / PROXY / NONE | basket id(s) | quoted basket name/theme/tags evidence | note |
|---|---|---|---|---|---|
| `hbm_packaging` | `memory_storage` | PROXY | `memory_storage` | name="Memory, HBM & Storage"; theme="DRAM/HBM, NAND and enterprise storage — the AI-memory cycle."; tags=[memory, hbm, dram, nand, storage, ai-infrastructure] | Parent theme `memory_storage` primary_basket_id=memory_storage |
| `sic_gan_specialty` | `ai_semiconductors` | PROXY | `ai_semiconductors` | name="AI Semiconductors"; theme="GPUs, AI accelerators, AI networking silicon and custom-ASIC names."; tags=[gpu, accelerators, custom-asic, ai-networking, datacenter, compute] | not shipped by W-C4 on origin/main (hierarchy block only; #7870 registry absent) |
| `gpu_merchant_accelerators` | `ai_semiconductors` | PROXY | `ai_semiconductors` | name="AI Semiconductors"; theme="GPUs, AI accelerators, AI networking silicon and custom-ASIC names."; tags=[gpu, accelerators, custom-asic, ai-networking, datacenter, compute] | Parent theme `ai_semiconductors` primary_basket_id=ai_semiconductors |
| `ai_interconnect_silicon` | `ai_semiconductors` | PROXY | `ai_semiconductors` | name="AI Semiconductors"; theme="GPUs, AI accelerators, AI networking silicon and custom-ASIC names."; tags=[gpu, accelerators, custom-asic, ai-networking, datacenter, compute] | Parent theme `ai_semiconductors` primary_basket_id=ai_semiconductors |
| `custom_asic_silicon` | `ai_semiconductors` | PROXY | `ai_semiconductors` | name="AI Semiconductors"; theme="GPUs, AI accelerators, AI networking silicon and custom-ASIC names."; tags=[gpu, accelerators, custom-asic, ai-networking, datacenter, compute] | Parent theme `ai_semiconductors` primary_basket_id=ai_semiconductors |
| `conventional_dram` | `memory_storage` | PROXY | `memory_storage` | name="Memory, HBM & Storage"; theme="DRAM/HBM, NAND and enterprise storage — the AI-memory cycle."; tags=[memory, hbm, dram, nand, storage, ai-infrastructure] | Parent theme `memory_storage` primary_basket_id=memory_storage |
| `nand_enterprise_storage` | `memory_storage` | PROXY | `memory_storage` | name="Memory, HBM & Storage"; theme="DRAM/HBM, NAND and enterprise storage — the AI-memory cycle."; tags=[memory, hbm, dram, nand, storage, ai-infrastructure] | Parent theme `memory_storage` primary_basket_id=memory_storage |
| `lithography_tools` | `semicap_equipment` | PROXY | `semicap_equipment` | name="Semiconductor Equipment (WFE)"; theme="Wafer-fab equipment, metrology and subsystem suppliers — the AI-capex pick-and-shovel layer."; tags=[wfe, semicap, ai-capex, metrology, subsystems] | Parent theme `semicap_equipment` primary_basket_id=semicap_equipment |
| `etch_deposition_equipment` | `semicap_equipment` | PROXY | `semicap_equipment` | name="Semiconductor Equipment (WFE)"; theme="Wafer-fab equipment, metrology and subsystem suppliers — the AI-capex pick-and-shovel layer."; tags=[wfe, semicap, ai-capex, metrology, subsystems] | Parent theme `semicap_equipment` primary_basket_id=semicap_equipment |
| `process_metrology_inspection` | `semicap_equipment` | PROXY | `semicap_equipment` | name="Semiconductor Equipment (WFE)"; theme="Wafer-fab equipment, metrology and subsystem suppliers — the AI-capex pick-and-shovel layer."; tags=[wfe, semicap, ai-capex, metrology, subsystems] | Parent theme `semicap_equipment` primary_basket_id=semicap_equipment |
| `wafer_fab_subsystems` | `semicap_equipment` | PROXY | `semicap_equipment` | name="Semiconductor Equipment (WFE)"; theme="Wafer-fab equipment, metrology and subsystem suppliers — the AI-capex pick-and-shovel layer."; tags=[wfe, semicap, ai-capex, metrology, subsystems] | Parent theme `semicap_equipment` primary_basket_id=semicap_equipment |
| `liquid_cooling_thermal` | `data_center_power` | PROXY | `data_center_power` | name="Data-Center Power & Cooling"; theme="Electrical, thermal and power infrastructure feeding AI datacenters."; tags=[data center, power, cooling, electrification, ai infrastructure, grid] | Parent theme `data_center_power` primary_basket_id=data_center_power |
| `hv_transformers_switchgear` | `grid_electrification` | PROXY | `power_grid` | name="Power & Grid Buildout"; theme="Generation, grid & electrification"; tags=[power, grid, electrification, utilities] | Parent theme `grid_electrification` primary_basket_id=power_grid |
| `ups_power_conversion` | `data_center_power` | PROXY | `data_center_power` | name="Data-Center Power & Cooling"; theme="Electrical, thermal and power infrastructure feeding AI datacenters."; tags=[data center, power, cooling, electrification, ai infrastructure, grid] | Parent theme `data_center_power` primary_basket_id=data_center_power |
| `reactor_technology` | `nuclear_power` | PROXY | `nuclear_power` | name="Nuclear & SMR Power"; theme="Nuclear utilities, SMR developers and the nuclear fuel/services chain — AI baseload power."; tags=[nuclear, smr, baseload, ai-power, utilities, fuel-cycle] | Parent theme `nuclear_power` primary_basket_id=nuclear_power |
| `nuclear_components` | `nuclear_power` | PROXY | `nuclear_power` | name="Nuclear & SMR Power"; theme="Nuclear utilities, SMR developers and the nuclear fuel/services chain — AI baseload power."; tags=[nuclear, smr, baseload, ai-power, utilities, fuel-cycle] | Parent theme `nuclear_power` primary_basket_id=nuclear_power |
| `fuel_cycle` | `nuclear_power` | PROXY | `nuclear_power` | name="Nuclear & SMR Power"; theme="Nuclear utilities, SMR developers and the nuclear fuel/services chain — AI baseload power."; tags=[nuclear, smr, baseload, ai-power, utilities, fuel-cycle] | Parent theme `nuclear_power` primary_basket_id=nuclear_power |
| `grid_distribution_automation` | `grid_electrification` | PROXY | `power_grid` | name="Power & Grid Buildout"; theme="Generation, grid & electrification"; tags=[power, grid, electrification, utilities] | Parent theme `grid_electrification` primary_basket_id=power_grid |
| `transmission_hvdc_cabling` | `grid_electrification` | PROXY | `power_grid` | name="Power & Grid Buildout"; theme="Generation, grid & electrification"; tags=[power, grid, electrification, utilities] | Parent theme `grid_electrification` primary_basket_id=power_grid |
| `endpoint_security` | `cybersecurity` | PROXY | `cybersecurity` | name="Cybersecurity"; theme="Endpoint, network, identity and cloud security software."; tags=[cybersecurity, software, cloud, identity, endpoint] | Parent theme `cybersecurity` primary_basket_id=cybersecurity |
| `network_security` | `cybersecurity` | PROXY | `cybersecurity` | name="Cybersecurity"; theme="Endpoint, network, identity and cloud security software."; tags=[cybersecurity, software, cloud, identity, endpoint] | Parent theme `cybersecurity` primary_basket_id=cybersecurity |
| `identity_access_management` | `cybersecurity` | PROXY | `cybersecurity` | name="Cybersecurity"; theme="Endpoint, network, identity and cloud security software."; tags=[cybersecurity, software, cloud, identity, endpoint] | Parent theme `cybersecurity` primary_basket_id=cybersecurity |
| `cloud_security` | `cybersecurity` | PROXY | `cybersecurity` | name="Cybersecurity"; theme="Endpoint, network, identity and cloud security software."; tags=[cybersecurity, software, cloud, identity, endpoint] | Parent theme `cybersecurity` primary_basket_id=cybersecurity |
| `missiles_munitions_effects` | `defense_aerospace` | PROXY | `defense` | name="Defense & Aerospace"; theme="Primes & defense-tech"; tags=[defense, aerospace] | Parent theme `defense_aerospace` primary_basket_id=defense |
| `missile_propulsion_supply` | `defense_aerospace` | PROXY | `defense` | name="Defense & Aerospace"; theme="Primes & defense-tech"; tags=[defense, aerospace] | Parent theme `defense_aerospace` primary_basket_id=defense |
| `defense_sensors_electronics_c2` | `defense_aerospace` | PROXY | `defense` | name="Defense & Aerospace"; theme="Primes & defense-tech"; tags=[defense, aerospace] | Parent theme `defense_aerospace` primary_basket_id=defense |
| `autonomous_systems_counter_uas` | `defense_aerospace` | PROXY | `defense` | name="Defense & Aerospace"; theme="Primes & defense-tech"; tags=[defense, aerospace] | Parent theme `defense_aerospace` primary_basket_id=defense |
| `naval_shipbuilding` | `defense_aerospace` | PROXY | `defense` | name="Defense & Aerospace"; theme="Primes & defense-tech"; tags=[defense, aerospace] | Parent theme `defense_aerospace` primary_basket_id=defense |
| `aerospace_components_aftermarket` | `defense_aerospace` | PROXY | `defense` | name="Defense & Aerospace"; theme="Primes & defense-tech"; tags=[defense, aerospace] | Parent theme `defense_aerospace` primary_basket_id=defense |
| `military_space_communications` | `space_satellite` | PROXY | `space_economy` | name="Space Economy"; theme="Launch, satcom, direct-to-device, Earth observation, defense-space and components — the commercial space build-out."; tags=[space, launch, satellite, defense-space, new-space] | Parent theme `space_satellite` primary_basket_id=space_economy |
| `machine_vision` | `robotics_automation` | PROXY | `robotics_automation` | name="Robotics & Automation"; theme="Factory automation, machine vision, surgical robotics and industrial controls."; tags=[automation, robotics, machine-vision, industrial, capex] | Parent theme `robotics_automation` primary_basket_id=robotics_automation |
| `industrial_motion_controls` | `robotics_automation` | PROXY | `robotics_automation` | name="Robotics & Automation"; theme="Factory automation, machine vision, surgical robotics and industrial controls."; tags=[automation, robotics, machine-vision, industrial, capex] | Parent theme `robotics_automation` primary_basket_id=robotics_automation |
| `collaborative_robot_arms` | `robotics_automation` | PROXY | `robotics_automation` | name="Robotics & Automation"; theme="Factory automation, machine vision, surgical robotics and industrial controls."; tags=[automation, robotics, machine-vision, industrial, capex] | Parent theme `robotics_automation` primary_basket_id=robotics_automation |
| `industrial_robot_arms` | `robotics_automation` | PROXY | `robotics_automation` | name="Robotics & Automation"; theme="Factory automation, machine vision, surgical robotics and industrial controls."; tags=[automation, robotics, machine-vision, industrial, capex] | Parent theme `robotics_automation` primary_basket_id=robotics_automation |
| `precision_actuators_servo_motors` | `robotics_automation` | PROXY | `robotics_automation` | name="Robotics & Automation"; theme="Factory automation, machine vision, surgical robotics and industrial controls."; tags=[automation, robotics, machine-vision, industrial, capex] | Parent theme `robotics_automation` primary_basket_id=robotics_automation |
| `surgical_robotics_systems` | `medical_devices` | NONE | `—` | name="—"; theme="—"; tags=[—] | Parent theme `medical_devices` has no primary_basket_id on HEAD (config/theme_crosswalk.yml) |
| `glp1_incretin_therapies` | `glp1_obesity` | PROXY | `obesity_glp1` | name="GLP-1 & Obesity"; theme="Incretin/GLP-1 metabolic drugs — incumbents, oral next-gen pure-plays, supply chain and the names the drugs hurt."; tags=[glp1, obesity, pharma, metabolic, biotech] | Parent theme `glp1_obesity` primary_basket_id=obesity_glp1 |
| `oral_glp1_formulations` | `glp1_obesity` | PROXY | `obesity_glp1` | name="GLP-1 & Obesity"; theme="Incretin/GLP-1 metabolic drugs — incumbents, oral next-gen pure-plays, supply chain and the names the drugs hurt."; tags=[glp1, obesity, pharma, metabolic, biotech] | Parent theme `glp1_obesity` primary_basket_id=obesity_glp1 |
| `glp1_api_manufacturing` | `glp1_obesity` | PROXY | `obesity_glp1` | name="GLP-1 & Obesity"; theme="Incretin/GLP-1 metabolic drugs — incumbents, oral next-gen pure-plays, supply chain and the names the drugs hurt."; tags=[glp1, obesity, pharma, metabolic, biotech] | Parent theme `glp1_obesity` primary_basket_id=obesity_glp1 |
| `cardiorenal_metabolic_indications` | `glp1_obesity` | PROXY | `obesity_glp1` | name="GLP-1 & Obesity"; theme="Incretin/GLP-1 metabolic drugs — incumbents, oral next-gen pure-plays, supply chain and the names the drugs hurt."; tags=[glp1, obesity, pharma, metabolic, biotech] | Parent theme `glp1_obesity` primary_basket_id=obesity_glp1 |
| `fill_finish_delivery_devices` | `glp1_obesity` | PROXY | `obesity_glp1` | name="GLP-1 & Obesity"; theme="Incretin/GLP-1 metabolic drugs — incumbents, oral next-gen pure-plays, supply chain and the names the drugs hurt."; tags=[glp1, obesity, pharma, metabolic, biotech] | Parent theme `glp1_obesity` primary_basket_id=obesity_glp1 |
| `launch_services` | `space_satellite` | PROXY | `space_economy` | name="Space Economy"; theme="Launch, satcom, direct-to-device, Earth observation, defense-space and components — the commercial space build-out."; tags=[space, launch, satellite, defense-space, new-space] | Parent theme `space_satellite` primary_basket_id=space_economy |
| `satellite_broadband_services` | `space_satellite` | PROXY | `space_economy` | name="Space Economy"; theme="Launch, satcom, direct-to-device, Earth observation, defense-space and components — the commercial space build-out."; tags=[space, launch, satellite, defense-space, new-space] | Parent theme `space_satellite` primary_basket_id=space_economy |
| `direct_to_device_connectivity` | `space_satellite` | PROXY | `space_economy` | name="Space Economy"; theme="Launch, satcom, direct-to-device, Earth observation, defense-space and components — the commercial space build-out."; tags=[space, launch, satellite, defense-space, new-space] | Parent theme `space_satellite` primary_basket_id=space_economy |
| `earth_observation` | `space_satellite` | PROXY | `space_economy` | name="Space Economy"; theme="Launch, satcom, direct-to-device, Earth observation, defense-space and components — the commercial space build-out."; tags=[space, launch, satellite, defense-space, new-space] | Parent theme `space_satellite` primary_basket_id=space_economy |
| `satellite_ground_terminals` | `space_satellite` | PROXY | `space_economy` | name="Space Economy"; theme="Launch, satcom, direct-to-device, Earth observation, defense-space and components — the commercial space build-out."; tags=[space, launch, satellite, defense-space, new-space] | Parent theme `space_satellite` primary_basket_id=space_economy |
| `rare_earth_separation_refining` | `rare_earth_critical_min` | PROXY | `critical_minerals` | name="Critical Minerals & Rare Earths"; theme="US/allied critical-mineral and rare-earth supply chain ex-China — producers and government-backed developers."; tags=[rare-earths, critical-minerals, lithium, antimony, supply-chain] | Parent theme `rare_earth_critical_min` primary_basket_id=critical_minerals |
| `ndfeb_permanent_magnets` | `rare_earth_critical_min` | PROXY | `critical_minerals` | name="Critical Minerals & Rare Earths"; theme="US/allied critical-mineral and rare-earth supply chain ex-China — producers and government-backed developers."; tags=[rare-earths, critical-minerals, lithium, antimony, supply-chain] | Parent theme `rare_earth_critical_min` primary_basket_id=critical_minerals |
| `critical_mineral_mining_development` | `rare_earth_critical_min` | PROXY | `critical_minerals` | name="Critical Minerals & Rare Earths"; theme="US/allied critical-mineral and rare-earth supply chain ex-China — producers and government-backed developers."; tags=[rare-earths, critical-minerals, lithium, antimony, supply-chain] | Parent theme `rare_earth_critical_min` primary_basket_id=critical_minerals |
| `gallium_germanium_supply_chain` | `rare_earth_critical_min` | PROXY | `critical_minerals` | name="Critical Minerals & Rare Earths"; theme="US/allied critical-mineral and rare-earth supply chain ex-China — producers and government-backed developers."; tags=[rare-earths, critical-minerals, lithium, antimony, supply-chain] | Parent theme `rare_earth_critical_min` primary_basket_id=critical_minerals |
| `copper_mining` | `copper_steel_electrify` | NONE | `—` | name="—"; theme="—"; tags=[—] | Parent theme `copper_steel_electrify` has no primary_basket_id on HEAD (config/theme_crosswalk.yml) |
| `refined_copper` | `copper_steel_electrify` | NONE | `—` | name="—"; theme="—"; tags=[—] | Parent theme `copper_steel_electrify` has no primary_basket_id on HEAD (config/theme_crosswalk.yml) |
| `structural_steel_electrification` | `copper_steel_electrify` | NONE | `—` | name="—"; theme="—"; tags=[—] | Parent theme `copper_steel_electrify` has no primary_basket_id on HEAD (config/theme_crosswalk.yml) |
| `copper_wire_cable` | `copper_steel_electrify` | NONE | `—` | name="—"; theme="—"; tags=[—] | Parent theme `copper_steel_electrify` has no primary_basket_id on HEAD (config/theme_crosswalk.yml) |
| `nitrogen_fertilizer_production` | `ag_fertilizer` | NONE | `—` | name="—"; theme="—"; tags=[—] | Parent theme `ag_fertilizer` has no primary_basket_id on HEAD (config/theme_crosswalk.yml) |
| `potash_phosphate_nutrients` | `ag_fertilizer` | NONE | `—` | name="—"; theme="—"; tags=[—] | Parent theme `ag_fertilizer` has no primary_basket_id on HEAD (config/theme_crosswalk.yml) |
| `precision_agriculture_platforms` | `ag_fertilizer` | NONE | `—` | name="—"; theme="—"; tags=[—] | Parent theme `ag_fertilizer` has no primary_basket_id on HEAD (config/theme_crosswalk.yml) |
| `medical_imaging` | `medical_devices` | NONE | `—` | name="—"; theme="—"; tags=[—] | Parent theme `medical_devices` has no primary_basket_id on HEAD (config/theme_crosswalk.yml) |
| `remote_patient_monitoring` | `medical_devices` | NONE | `—` | name="—"; theme="—"; tags=[—] | Parent theme `medical_devices` has no primary_basket_id on HEAD (config/theme_crosswalk.yml) |
| `surgical_implants_instruments` | `medical_devices` | NONE | `—` | name="—"; theme="—"; tags=[—] | Parent theme `medical_devices` has no primary_basket_id on HEAD (config/theme_crosswalk.yml) |
| `liquid_biopsy_assays` | `diagnostics_lifesci` | NONE | `—` | name="—"; theme="—"; tags=[—] | Parent theme `diagnostics_lifesci` has no primary_basket_id on HEAD (config/theme_crosswalk.yml) |
| `genomic_sequencing` | `diagnostics_lifesci` | NONE | `—` | name="—"; theme="—"; tags=[—] | Parent theme `diagnostics_lifesci` has no primary_basket_id on HEAD (config/theme_crosswalk.yml) |
| `proteomics_discovery_platforms` | `diagnostics_lifesci` | NONE | `—` | name="—"; theme="—"; tags=[—] | Parent theme `diagnostics_lifesci` has no primary_basket_id on HEAD (config/theme_crosswalk.yml) |
| `life_science_lab_instruments` | `diagnostics_lifesci` | NONE | `—` | name="—"; theme="—"; tags=[—] | Parent theme `diagnostics_lifesci` has no primary_basket_id on HEAD (config/theme_crosswalk.yml) |
| `diagnostic_reagents_kits` | `diagnostics_lifesci` | NONE | `—` | name="—"; theme="—"; tags=[—] | Parent theme `diagnostics_lifesci` has no primary_basket_id on HEAD (config/theme_crosswalk.yml) |
| `pv_cell_module_manufacturing` | `solar` | NONE | `—` | name="—"; theme="—"; tags=[—] | Parent theme `solar` has no primary_basket_id on HEAD (config/theme_crosswalk.yml) |
| `polysilicon_solar_feedstock` | `solar` | NONE | `—` | name="—"; theme="—"; tags=[—] | Parent theme `solar` has no primary_basket_id on HEAD (config/theme_crosswalk.yml) |
| `solar_inverters` | `solar` | NONE | `—` | name="—"; theme="—"; tags=[—] | Parent theme `solar` has no primary_basket_id on HEAD (config/theme_crosswalk.yml) |
| `solar_trackers_bos` | `solar` | NONE | `—` | name="—"; theme="—"; tags=[—] | Parent theme `solar` has no primary_basket_id on HEAD (config/theme_crosswalk.yml) |
## Q6. Binding rows and clauses

**Gate #2 (verbatim):** "Do not use an internal-only vendor input to launder restricted structure into a house-owned output." (`research/theme_graph/THEME_HIERARCHY_SPEC_V1_2026-10-07.md:15-16`)

**Gate #8:** No new store, producer, selection store, ThemeState owner, rights resolver, publication control plane, lobe or vocabulary family (`research/theme_graph/THEME_HIERARCHY_SPEC_V1_2026-10-07.md:9-11`).

**DNR:HOLD-TICKER-EXPOSURE-TAGS (full row):** `| HOLD-TICKER-EXPOSURE-TAGS | Per-ticker multi-label business-model exposure tags (tech) | DEFERRED — group-level taxonomy only; revive needs revenue-geography ingestion + own adjudication | TI-R2, TECH_INTERNALS_CODEX_ADJUDICATION_BY_FABLE.md |` (`research/DO_NOT_REBUILD.md:166`)

**Read-time composition (no stored ticker→micro edges):** `research/theme_graph/THEME_HIERARCHY_SPEC_V1_2026-10-07.md:95-100` — paths composed at read time via basket membership; `engine/theme_graph/structural_navigation.py` `hierarchy_paths` (named at `research/theme_graph/THEME_HIERARCHY_SPEC_V1_2026-10-07.md:98-99`).

**(a) Adding baskets to membership.json:** Lawful curated admission path exists (`scripts/promote_candidate.py:5-8` inserts into region membership); PIT via `engine/basket_membership_pit.py`; theme-graph emits `MEMBER_OF` from membership not from vendor (`engine/theme_graph/materialize.py:617-621`). Hierarchy spec: new-tier micro ids must not be referenced by basket/EXPRESSES until consumer wave (`research/theme_graph/THEME_HIERARCHY_SPEC_V1_2026-10-07.md:69-70`).

**(b) Storing micro member lists in theme_crosswalk.yml:** **Forbidden as membership store** — crosswalk holds hierarchy vocabulary and EXPRESSES for **theme-tier** baskets only; micro_themes rows carry `nominated_from`, not members (`research/theme_graph/THEME_HIERARCHY_SPEC_V1_2026-10-07.md:53-59`, `29-30`).

**(c) New edge type ticker→micro:** **Refused in V1** — only `PARENT_OF` for hierarchy; ticker linkage remains `MEMBER_OF` basket → read-time path (`research/theme_graph/THEME_HIERARCHY_SPEC_V1_2026-10-07.md:32-38`, `contracts/theme_graph/README.md:39-42`).

**PIT:** `asserted_on` ≥ epoch; not emitted before as-of (`research/theme_graph/THEME_HIERARCHY_SPEC_V1_2026-10-07.md:65-66`). No backdating admission.

## Candidate options (input to orchestrator K, not a ruling)

### Option A — Federate vertical `slice_keys` at read time (house registries)
- **Constraint:** Slug equals micro id (`research/theme_graph/THEME_HIERARCHY_SPEC_V1_2026-10-07.md:84-88`); no vendor finviz/ths.
- **Files:** `engine/theme_graph/structural_navigation.py`, vertical registry modules (e.g. future `engine/market_ontology/theme_research_registry`), tests in W-C5/W-C6.
- **First wave:** Semiconductors slices already named in `HIERARCHY_BLOCK_V1.yaml` (`hbm_packaging`, `sic_gan_specialty`) once #7870 lands; expose cohort read API, no new parquet store.
- **Lawful:** Group-level membership at slice grain; tickers resolved at read time; Gate #8 satisfied if registry remains incumbent vertical store.

### Option B — Child baskets under parent theme basket (`parent_basket` field)
- **Constraint:** DNR:HOLD-TICKER-EXPOSURE-TAGS — members stay basket group, not per-ticker tags; PIT via `added`/`membership_history`.
- **Files:** `data/baskets/membership.json`, `config/theme_crosswalk.yml` EXPRESSES for new basket ids, `engine/theme_graph/materialize.py`, consumer tier-guard W-C2b.
- **First wave:** One pilot micro (e.g. `hbm_packaging`) as new basket id equal to micro slug with subset of `memory_storage` members; `asserted_on` = admission date.
- **Lawful:** Gate #2 (house-curated); no new store beyond existing membership + theme_graph emitter.

### Option C — Pure read-time partition of parent basket members via house rules table
- **Constraint:** No persisted member list for micro — rule map in crosswalk or research YAML keyed by micro id, applied in `hierarchy_paths`.
- **Files:** `config/theme_crosswalk.yml` or `research/theme_graph/` rule file; `structural_navigation.py` reader only.
- **First wave:** Display-only labeling of existing `memory_storage` members into HBM vs DRAM buckets using curated ticker sets in YAML (group-level rows, not per-ticker tag file).
- **Lawful:** Read-time composition §6; must not become shadow per-ticker tag store (DNR).

**Dropped (unlawful):**
- Finviz/THS subsector snapshot → micro members (**Gate #2**, `engine/subsector_rotation.py:3-9`).
- New `ticker→micro_theme` edge type in theme_graph (**spec §2**, Q6c).
- Per-ticker exposure tag table (**DNR:HOLD-TICKER-EXPOSURE-TAGS**).
- New selection store / ThemeState owner for micro picks (**Gate #8**).
- Back-dated `asserted_on` or seed_constant micro membership (**PIT**, `contracts/theme_graph/README.md:60-66`).

## Gaps and search bounds

- W-C4 population of `config/theme_crosswalk.yml` `hierarchy.micro_themes` not on audited HEAD (empty list at `config/theme_crosswalk.yml:523`); census used `HIERARCHY_BLOCK_V1.yaml` as authoritative id list.
- #7870 `theme_research_registry` module not on HEAD — could not cite live slice ticker counts; only `nominated_from` strings in hierarchy block.
- `app/` has no direct membership readers on HEAD.
- Full engine/scripts reader enumeration truncated in Q1 table to production paths + count-pinning tests; complete path list: `git grep -l 'baskets/membership.json' HEAD -- engine/ scripts/ tests/` (80+ test fixtures).
- No test suite executed (docs-only census per commission).

