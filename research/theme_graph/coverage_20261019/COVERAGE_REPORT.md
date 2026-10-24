# GMI theme-graph step-7 coverage proof

report_version: `0cd3e3374c17e213606f0e30fa7ad125bea95d6f3d6a93d5bea7e2a0fddb26bb`  
manifest_version: `2373df79e9418057828ab6cbf7f6fd4055e96b5d9fc66e3de72fa10854a782d5`  
source_commit: `0221d6e171751c15b24d9f0bea27056aeab2716c`

## Inputs

| role | path | git_blob_sha1 |
| --- | --- | --- |
| hierarchy | config/theme_crosswalk.yml | 48348268f5113350b7c12073708b8fa70ead1b9b |
| research_record | research/theme_graph/micro_member_research_addendum_20261016/research_addendum.json | e7803a1893cf9cdb73959b7643e618a300864478 |
| research_record | research/theme_graph/microtheme_membership_candidates_2026-10-08.json | eaeefaa420403c4afe77aed31b42dddc92f73cb4 |
| security_master | data/reference/security_master.parquet | 452fe313fa8d1904539128edbc8fb2fdd7d861d1 |
| security_master_receipt | data/reference/_receipt.json | ea0104419a926d263cdcf8bdf11e434ca2790cd8 |
| store_edges | data/theme_graph/edges.parquet | 0cec4f063690419d1e24332c8d493c26b1096f4b |
| store_identity_resolution | data/theme_graph/identity_resolution.parquet | c088b40deda56eb85d4d20112c1190f33fc504a3 |
| store_meta | data/theme_graph/_meta.json | 28c1d1d3481f62780e9744b584f5b88eea522fd5 |
| store_node_lifecycle | data/theme_graph/node_lifecycle.parquet | b246f37d43ddbfed09446a0e5602da782783aea4 |
| store_nodes | data/theme_graph/nodes.parquet | ab9a578135b71637bd4e5c114de4117c1300bab9 |
| store_probation_proposals | data/theme_graph/probation/proposals.jsonl | 58d8d8722d7834f30df55dd8b1e571ee20f7b773 |
| symbol_directory | data/symbol_directory/snapshots/2026-10-15.parquet | ebbbe7595f844aa034b2d446b81d13d057c5f5b4 |
| symbol_directory_manifest | data/symbol_directory/manifest.json | 0306f3bd7b0474cdef3f5c19dae1683c5e175d43 |

## Core denominators (US and CN are separate; never summed)

| market | securities | issuers resolved | issuers resolved (eligible) | eligible securities | unresolved-issuer securities |
| --- | --- | --- | --- | --- | --- |
| us | 1939 | 1927 | 1925 | 1935 | 6 |
| cn | 1019 | 0 | 0 | 1019 | 1019 |

## Gates

| Dimension | Threshold (verbatim) | Measured | Verdict |
| --- | --- | --- | --- |
| Denominator honesty | 100% of the frozen universe has explicit coverage/status for each promised dimension; issuer/security/activity counts and exclusions are published separately. No arbitrary all-graph denominator. | {"core_markets": {"cn": {"eligibility_counts_sum": 1019, "eligible_securities": 1019, "exclusions_listed": 0, "identity_status_counts_sum": 1019, "issuer_and_security_counts_separate": true, "issuers_resolved_distinct_eligible": 0, "securities_total": 1019}, "us": {"eligibility_counts_sum": 1939, "eligible_securities": 1935, "exclusions_listed": 4, "identity_status_counts_sum": 1935, "issuer_and_security_counts_separate": true, "issuers_resolved_distinct_eligible": 1925, "securities_total": 1939}}, "issuer_security_counts_separate_keys": true} | PASS |
| Principal activity coverage | At least 95% of eligible core U.S./China issuers have a current source-backed principal activity and qualified identity; every remainder has a specific reason and source/owner next step. Assess each market separately. | {"denominator_lower_bound": 1926, "denominator_upper_bound": 1931, "market": "us", "numerator_issuers": 0, "ratio_lower_bound_denominator": "0.0000", "ratio_upper_bound_denominator": "0.0000"} | FAIL |
| Principal activity coverage | At least 95% of eligible core U.S./China issuers have a current source-backed principal activity and qualified identity; every remainder has a specific reason and source/owner next step. Assess each market separately. | {"denominator_lower_bound": 1, "denominator_upper_bound": 1019, "market": "cn", "numerator_issuers": 0, "ratio_lower_bound_denominator": "0.0000", "ratio_upper_bound_denominator": "0.0000"} | FAIL |
| Taxonomy coverage | All 68 currently adopted micros have versioned scope and an owner-reviewed coverage disposition. No forced constituent minimum or parent inheritance to inflate a sparse theme. | {"declared_micro_count": 68, "discrepancy": null, "micros_without_scope_version": 0, "observed_micro_count": 68, "owner_reviewed": false} | FAIL |
| Correctness | Zero hard identity merges, fabricated named anonymous customers, unauthorized source promotion, future leakage, failed-fetch removals, or magnitude/species conflations in release controls. | null | NOT_IN_THIS_LANE |
| Automatic admission | No automatic positive admission until a per-relation/per-source evaluation supports a one-sided 95% lower confidence bound of at least 95% precision. 59 independent all-correct cases reach approximately 0.9505; correlated disclosures require an adjusted design, not this shortcut. | null | NOT_IN_THIS_LANE |
| Freshness | At least 95% of accessible material filing/corporate-action changes are observed and routed within 48 hours; visible stale/unavailable status is mandatory when source cadence or rights prevent refresh. Validity and retrieval freshness remain separate. | null | NOT_IN_THIS_LANE |
| Corrections | Material confirmed errors are withheld or corrected by the next ordinary publication; the original view remains reproducible and correction latency is measured. | null | NOT_IN_THIS_LANE |
| Product usefulness | At least 90% success on predefined investor explanation tasks, measured separately for EN/ZH and supported desktop/mobile views; exact ID/status/date parity on every release journey. | null | NOT_IN_THIS_LANE |
| Predictive claims | No prediction/allocation promotion from descriptive acceptance. The existing evaluator must separately judge PIT baselines, leakage, costs, robustness, calibration and the specific intended use. | null | NOT_IN_THIS_LANE |

## Remainders (every one has a named owner; no OTHER)

| market | reason | count | owner | next step |
| --- | --- | --- | --- | --- |
| ca | NOT_IN_MASTER | 167 | Data OS security master | decide master admission for the listing |
| cn | CN_LISTED_COUNTS_NOT_AVAILABLE | 1019 | Data OS | install a market-wide listed-count owner for mainland China |
| cn | IDENTITY_NOT_QUALIFIED | 1019 | engine.company_intelligence.issuer_disclosure_owner + named GMI curator | native fact -> build_activity_membership_evidence -> make_activity_membership_proposal -> named curator ratification |
| cn | NO_ISSUER_EVIDENCE | 1019 | Data OS security master (scripts/build_security_master.py) | china_hk issuer admission via CNInfo evidence |
| intl | UNSUPPORTED_MARKET | 233 | Data OS universe owner | no installed universe owner for this market |
| us | DEFERRED_IDENTITY_EXCEPTION | 1 | Data OS identity-exception owner | resolve the recorded identity exception |
| us | EXCLUDED_ENTITY_TYPE_CONFLICT | 1 | Data OS security master | kept outside the company denominator; own count preserved |
| us | EXCLUDED_ETF_KIND | 2 | Data OS security master | kept outside the company denominator; own count preserved |
| us | EXCLUDED_SUPERSEDED_DUPLICATE_MINT | 1 | Data OS security master | kept outside the company denominator; own count preserved |
| us | IDENTITY_NOT_QUALIFIED | 726 | engine.company_intelligence.issuer_disclosure_owner + named GMI curator | native fact -> build_activity_membership_evidence -> make_activity_membership_proposal -> named curator ratification |
| us | ISSUER_EVIDENCE_CONFLICT | 2 | Data OS security master | adjudicate the conflicting issuer evidence |
| us | NOT_IN_GRAPH | 721 | GMI graph population / engine.theme_graph.identity_resolution owner | decide node admission from the master; never inferred |
| us | NO_ACTIVITY_EVIDENCE | 4 | engine.company_intelligence.issuer_disclosure_owner + named GMI curator | native fact -> build_activity_membership_evidence -> make_activity_membership_proposal -> named curator ratification |
| us | NO_ISSUER_EVIDENCE | 3 | Data OS security master (scripts/build_security_master.py) | attach issuer evidence (SEC CIK) for the security |
| us | VENDOR_MEMBERSHIP_ONLY | 1201 | engine.company_intelligence.issuer_disclosure_owner + named GMI curator | native fact -> build_activity_membership_evidence -> make_activity_membership_proposal -> named curator ratification |

## Taxonomy


| id | scope_version | disposition | admitted | proposed | research | vendor routes |
| --- | --- | --- | --- | --- | --- | --- |
| theme:aerospace_components_aftermarket | 2c804fe8fb37 | RESEARCH_UNADMITTED | 0 | 0 | 2 | 0 |
| theme:ai_interconnect_silicon | b3947368615b | RESEARCH_UNADMITTED | 0 | 0 | 4 | 0 |
| theme:autonomous_systems_counter_uas | 1f23493ee9f2 | RESEARCH_UNADMITTED | 0 | 0 | 2 | 0 |
| theme:cardiorenal_metabolic_indications | 0f6cd9aaeaa9 | RESEARCH_UNADMITTED | 0 | 0 | 2 | 0 |
| theme:cloud_security | 51af3fb0738a | RESEARCH_UNADMITTED | 0 | 0 | 3 | 0 |
| theme:collaborative_robot_arms | 2e5712bc7ad2 | RESEARCH_UNADMITTED | 0 | 0 | 2 | 0 |
| theme:conventional_dram | 9754e97b0898 | RESEARCH_UNADMITTED | 0 | 0 | 4 | 0 |
| theme:copper_mining | 8659b1d358b4 | RESEARCH_UNADMITTED | 0 | 0 | 2 | 0 |
| theme:copper_wire_cable | 64779253d42b | RESEARCH_UNADMITTED | 0 | 0 | 3 | 0 |
| theme:critical_mineral_mining_development | aaf42d65c272 | RESEARCH_UNADMITTED | 0 | 0 | 2 | 0 |
| theme:custom_asic_silicon | 977a5d5ded39 | RESEARCH_UNADMITTED | 0 | 0 | 3 | 0 |
| theme:defense_sensors_electronics_c2 | ddd27d1c6a8f | RESEARCH_UNADMITTED | 0 | 0 | 1 | 0 |
| theme:diagnostic_reagents_kits | e185f8841654 | RESEARCH_UNADMITTED | 0 | 0 | 1 | 0 |
| theme:direct_to_device_connectivity | b58b336f6865 | RESEARCH_UNADMITTED | 0 | 0 | 2 | 0 |
| theme:earth_observation | a1e8f9fbaf36 | RESEARCH_UNADMITTED | 0 | 0 | 3 | 0 |
| theme:endpoint_security | 9b5c3dbc19a1 | RESEARCH_UNADMITTED | 0 | 0 | 2 | 0 |
| theme:etch_deposition_equipment | 9a5ae1906ff3 | RESEARCH_UNADMITTED | 0 | 0 | 4 | 0 |
| theme:fill_finish_delivery_devices | 9b0fde7f3ad7 | RESEARCH_UNADMITTED | 0 | 0 | 2 | 0 |
| theme:fuel_cycle | 3c2716940a6d | RESEARCH_UNADMITTED | 0 | 0 | 2 | 0 |
| theme:gallium_germanium_supply_chain | 47044b144716 | RESEARCH_UNADMITTED | 0 | 0 | 3 | 0 |
| theme:genomic_sequencing | 5943f8f400c8 | RESEARCH_UNADMITTED | 0 | 0 | 3 | 0 |
| theme:glp1_api_manufacturing | 72481bff0221 | RESEARCH_UNADMITTED | 0 | 0 | 6 | 0 |
| theme:glp1_incretin_therapies | b7c98979b4f0 | RESEARCH_UNADMITTED | 0 | 0 | 3 | 0 |
| theme:gpu_merchant_accelerators | 650bfac87452 | RESEARCH_UNADMITTED | 0 | 0 | 2 | 0 |
| theme:grid_distribution_automation | d2e6f365799a | RESEARCH_UNADMITTED | 0 | 0 | 2 | 0 |
| theme:hbm_packaging | 7b6bd278681b | RESEARCH_UNADMITTED | 0 | 0 | 9 | 0 |
| theme:hv_transformers_switchgear | 310607ab5a3a | RESEARCH_UNADMITTED | 0 | 0 | 3 | 0 |
| theme:identity_access_management | 89f4de9b394e | RESEARCH_UNADMITTED | 0 | 0 | 3 | 0 |
| theme:industrial_motion_controls | 5b63e0b640f6 | RESEARCH_UNADMITTED | 0 | 0 | 3 | 0 |
| theme:industrial_robot_arms | a6dd9e074466 | RESEARCH_UNADMITTED | 0 | 0 | 2 | 0 |
| theme:launch_services | be0ab871d197 | RESEARCH_UNADMITTED | 0 | 0 | 2 | 0 |
| theme:life_science_lab_instruments | 55127a55a976 | RESEARCH_UNADMITTED | 0 | 0 | 2 | 0 |
| theme:liquid_biopsy_assays | 4b457f0f1781 | RESEARCH_UNADMITTED | 0 | 0 | 2 | 0 |
| theme:liquid_cooling_thermal | ade92a568068 | RESEARCH_UNADMITTED | 0 | 0 | 2 | 0 |
| theme:lithography_tools | 48fb6b9c5b7e | RESEARCH_UNADMITTED | 0 | 0 | 4 | 0 |
| theme:machine_vision | a39db127a120 | RESEARCH_UNADMITTED | 0 | 0 | 3 | 0 |
| theme:medical_imaging | e19ac4ebfec8 | RESEARCH_UNADMITTED | 0 | 0 | 1 | 0 |
| theme:military_space_communications | cbd6d0a3506c | RESEARCH_UNADMITTED | 0 | 0 | 1 | 0 |
| theme:missile_propulsion_supply | 732cf16c34b1 | RESEARCH_UNADMITTED | 0 | 0 | 1 | 0 |
| theme:missiles_munitions_effects | 3991a030892e | RESEARCH_UNADMITTED | 0 | 0 | 2 | 0 |
| theme:nand_enterprise_storage | 7238482db4f6 | RESEARCH_UNADMITTED | 0 | 0 | 7 | 0 |
| theme:naval_shipbuilding | b27279cbdcef | RESEARCH_UNADMITTED | 0 | 0 | 2 | 0 |
| theme:ndfeb_permanent_magnets | 1254e86d15a6 | RESEARCH_UNADMITTED | 0 | 0 | 3 | 0 |
| theme:network_security | 2cb03bd93993 | RESEARCH_UNADMITTED | 0 | 0 | 2 | 0 |
| theme:nitrogen_fertilizer_production | 8ce6bbd94e12 | RESEARCH_UNADMITTED | 0 | 0 | 1 | 0 |
| theme:nuclear_components | 6051a89f0cc0 | RESEARCH_UNADMITTED | 0 | 0 | 2 | 0 |
| theme:oral_glp1_formulations | 7e0a430543ee | RESEARCH_UNADMITTED | 0 | 0 | 2 | 0 |
| theme:polysilicon_solar_feedstock | 292747bc9257 | RESEARCH_UNADMITTED | 0 | 0 | 2 | 0 |
| theme:potash_phosphate_nutrients | 034d731d8d93 | RESEARCH_UNADMITTED | 0 | 0 | 2 | 0 |
| theme:precision_actuators_servo_motors | 00d8c20e901c | RESEARCH_UNADMITTED | 0 | 0 | 4 | 0 |
| theme:precision_agriculture_platforms | 7bd38760292f | RESEARCH_UNADMITTED | 0 | 0 | 1 | 0 |
| theme:process_metrology_inspection | ace060b0986b | RESEARCH_UNADMITTED | 0 | 0 | 4 | 0 |
| theme:proteomics_discovery_platforms | b635005f36c7 | RESEARCH_UNADMITTED | 0 | 0 | 4 | 0 |
| theme:pv_cell_module_manufacturing | 5a8d4ef8e095 | RESEARCH_UNADMITTED | 0 | 0 | 2 | 0 |
| theme:rare_earth_separation_refining | b37d097a7582 | RESEARCH_UNADMITTED | 0 | 0 | 3 | 0 |
| theme:reactor_technology | 2e61d094f569 | RESEARCH_UNADMITTED | 0 | 0 | 2 | 0 |
| theme:refined_copper | c83797dce791 | RESEARCH_UNADMITTED | 0 | 0 | 2 | 0 |
| theme:remote_patient_monitoring | a71f00e9894c | RESEARCH_UNADMITTED | 0 | 0 | 2 | 0 |
| theme:satellite_broadband_services | 1ce60a7fa8c3 | RESEARCH_UNADMITTED | 0 | 0 | 2 | 0 |
| theme:satellite_ground_terminals | 752a46ccb5fe | RESEARCH_UNADMITTED | 0 | 0 | 3 | 0 |
| theme:solar_inverters | 24f4b5239a1f | RESEARCH_UNADMITTED | 0 | 0 | 4 | 0 |
| theme:solar_trackers_bos | cc23aa3f4988 | RESEARCH_UNADMITTED | 0 | 0 | 2 | 0 |
| theme:structural_steel_electrification | 91c29fc6ad61 | RESEARCH_UNADMITTED | 0 | 0 | 1 | 0 |
| theme:surgical_implants_instruments | 82144aa26fe3 | RESEARCH_UNADMITTED | 0 | 0 | 2 | 0 |
| theme:surgical_robotics_systems | c7d0b16c839a | RESEARCH_UNADMITTED | 0 | 0 | 3 | 0 |
| theme:transmission_hvdc_cabling | 83b1598db60e | RESEARCH_UNADMITTED | 0 | 0 | 2 | 0 |
| theme:ups_power_conversion | ea2d95295e3a | RESEARCH_UNADMITTED | 0 | 0 | 2 | 0 |
| theme:wafer_fab_subsystems | d90fccdf57dc | RESEARCH_UNADMITTED | 0 | 0 | 4 | 0 |

## Wider-market ledger (not a denominator)

| market | graph company nodes | by resolution state | master securities | status |
| --- | --- | --- | --- | --- |
| ca | 167 | {"NOT_IN_MASTER": 167} | 0 | WIDER_MARKET_LEDGER_NOT_IN_CORE_DENOMINATOR |
| hk | 147 | {"RESOLVED": 147} | 147 | WIDER_MARKET_LEDGER_NOT_IN_CORE_DENOMINATOR |
| intl | 233 | {"UNSUPPORTED_MARKET": 233} | 0 | WIDER_MARKET_LEDGER_NOT_IN_CORE_DENOMINATOR |

## Graph-side ledger

| market | state/lifecycle_status | count |
| --- | --- | --- |
| ca | NOT_IN_MASTER/canonical | 167 |
| cn | NOT_IN_MASTER/canonical | 2 |
| cn | RESOLVED/canonical | 1019 |
| hk | RESOLVED/canonical | 147 |
| intl | UNSUPPORTED_MARKET/canonical | 233 |
| us | DEFERRED_IDENTITY_EXCEPTION/canonical | 1 |
| us | DEFERRED_IDENTITY_EXCEPTION/retired | 1 |
| us | ENTITY_TYPE_CONFLICT/retired | 1 |
| us | NOT_IN_MASTER/canonical | 24 |
| us | RESOLVED/canonical | 1213 |
| us | RESOLVED/merged | 1 |

FAIL stays FAIL: this report never rounds a failing gate into a pass.
