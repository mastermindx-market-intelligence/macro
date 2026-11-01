# WP02 policy v2 — corrective delta

**State: author correction complete; independent corrective review and principal adoption pending.** This version implements the principal's accepted R1/R2 correction scope. It preserves the frozen v1 recommendation and the independent review's original `REQUEST_CHANGES_TWO_P2_INPUT_CONTRACT_GAPS` verdict. It does not turn that initial review into a pass.

## 1. Exact input bindings

| Input | SHA-256 |
| --- | --- |
| Frozen v1 policy | `03881ee568f6f08f06ef88a2fad0e33ff2fe14b3ab1db526c35221d642cfe9fd` |
| Frozen v1 memo | `763f8724b1ec9e88a60b94dd65b3d61befe6af79ff28f64f472f0a87ecf9a582` |
| Independent initial review | `e35cc6b4bffa57cb7203f126620b069e7b2944dd45e29f71c4e9bf827dc390b6` |
| Independent findings | `ce6e7c2364fdd5db96cf47120e5dc14d79e036ffabc9d8f955bf94e2491af446` |
| Independent method checks | `c7bbdaf7b8acfd3008ff2f1fd4c630d75bfdc80fe4e15bd6c92f20a7b1892bf5` |
| Independent source observations | `d16eea19bd56f8cd59a7ad15d54148cda6990ced2f690cca30d6194e1a917af0` |
| Independent review manifest | `e3319b04840b48866dba1c1414293c8f67068cc3d877570a7ffe22ef263042ec` |

The complete review, findings, checks, source observations and supporting manifest/bindings were read. The original review's three input snapshots equal the frozen v1 policy, memo and source register. `PRESERVATION_BASELINE.json` verifies the exact inventories of the 21-file frame audit, five-file v1 recommendation and ten-file initial review. The correction writes only this separate v2 directory.

## 2. R1: historical membership completeness

**Finding:** valid D intervals for all surviving rows in a later directory do not prove that the directory includes every issuer present at D. A post-D delisting can alter the denominator and the surviving issuers' relative bands.

**Corrected JSON clauses:** `/historical_frame/perimeter_closure`, `/historical_frame/target_membership_coordinate`, `/historical_frame/input_bindings`, `/historical_frame/permitted_methods/HISTORICAL_D_SNAPSHOT`, `/historical_frame/permitted_methods/ANCHORED_MEMBERSHIP_RECONSTRUCTION`, `/historical_frame/reconciliation`, and `/historical_frame/readiness`.

The contract now requires historical closure of venue, segment and instrument partitions, including subsequently closed or transferred partitions. Each contributing partition must supply one of two evidenced routes:

1. An authoritative, complete roster at D, with all source files, pages or export partitions, documented membership convention, exact retained and parsed bindings, and a source total or demonstrably exhaustive export/pagination closure.
2. A complete anchor roster plus complete membership events between the anchor and D. Forward application verifies each before-state; reverse application verifies each after-state. Post-D removals are restored and post-D admissions removed. Transfers, conversions, identifier replacements and primary-status transitions are not silently omitted. All required anchors, events and correction relations remain subject to K.

Reconciliation compares exact membership and event states, not counts alone. Counts must be nonnegative integers; an unknown or unpublished count stays explicit rather than becoming zero. Unresolved potentially eligible omissions, unidentified partitions, missing event kinds or intervals, ambiguous effective ordering, unproved rights, and inadequate completeness evidence remain holds. Unknown activity within a relevant partition holds every activity pool it could affect.

**Linked changes:** `/instrument_and_venue/venue_register_requirement`, `/relative_size/denominator`, `/relative_size/completeness`, `/relative_size/administrative_population_label`, `/cutoff_policy/historical_roster`, and the preflight sequence. **Memo:** §§3.1, 5 and 7. Failure is `FRAME_HISTORY_UNPROVEN` before affected quantiles; proof of history still does not supply missing issuer identity, primary activity or capitalization.

## 3. R2: component assertion conflicts and supersession

**Finding:** publication recency cannot reconcile independent, incompatible assertions about the same class, measurement date and basis. A latest-publication rule could select either side of a size boundary without proving a correction.

**Corrected JSON clauses:** `/capitalization/assertion_resolution/identities`, `/component_keys`, `/admissibility_and_order`, `/supersession`, `/resolution_receipt`, and `/dependency_and_unit_closure`, all under `/capitalization/assertion_resolution`.

Publisher/document/assertion identity is now separate from the economic fact key. Publisher and publication/observation identity cannot partition same-fact disagreement away. Assertions preserve actual measurement or applicability coordinates, exact source and derivation bindings, units, basis, issuer/class/event identity, source lineage, revision relations, publication bounds and permitted use.

Point-measurement selection uses the greatest eligible measurement date under the prescribed component rule. Later publication does not replace a newer measurement with an older one. Persistent rights and ratio states require evidence of the state or transition applicable at D; a later asserted start date cannot settle overlapping incompatible states.

Equivalent exact normalized assertions retain all provenance. Distinct active comparable values produce `CAP_COMPONENT_CONFLICT`. Identity, applicability or basis ambiguity produces `CAP_COMPONENT_BASIS_UNPROVEN`. Only source-proved correction or authoritative revision relations remove superseded assertions. Reconciliation of units, basis or aliases is recorded as that relation type and is not automatically a correction edge. Relations must have exact fact scope, actual referenced evidence, valid K bounds and an acyclic graph. An unreconciled independent competitor remains active even if another publisher corrected its own assertion.

The law applies to outstanding shares, the fixed price counter and official session, ADR/conversion ratios, ordinary-class rights, corporate actions, quote units and the prescribed ECB FX series. Material dependencies are resolved through the same graph. A stale pre-split close paired with post-split shares requires the proved inverse price factor; unresolved class or factor dependencies hold the full issuer cap. The latest required conflicted measurement cannot fall back to an older clean one, and partial-class sums, averaging, source preference or quota fit cannot resolve the conflict.

**Linked changes:** `/capitalization/share_count/source`, `/capitalization/prices/source`, `/capitalization/prices/historical_adjustment`, `/capitalization/share_class_and_ADR/assertion_rule`, `/capitalization/fx/assertion_rule`, `/capitalization/cap_unknown_handling`, and `/cutoff_policy/revisions`. **Memo:** §6.1. Required unresolved components leave capitalization null and hold the affected pool.

## 4. Related clarifications within the accepted correction scope

| Concern | Exact v2 clause | Result |
| --- | --- | --- |
| INT self-use and residual target | `/deterministic_selection/INT_feasibility/residual_pseudocode` | Remove the current candidate before tentative flow, subtract its country and cell incidence once, reject negative quotas, and require flow equal to the remaining quota sum. Zero is a valid empty completion. |
| Deterministic feasible solution | `/deterministic_selection/INT_feasibility/deterministic_solution` | Produce the lexicographically smallest sorted selected-priority list under the unchanged seed and encoding. Do not confuse this with a bit-vector order. |
| Source scope required for ranks | `/frame_sourcing_dependency` | All 42 complete historical jurisdiction/activity pools are required, including unselected issuers. This is a frame dependency larger than 120 lookups; actual pool and population cardinalities remain null. |
| Company activity versus segment role | `/coverage_axes` | Company primary activity determines the issuer quota. Source-reported segment roles are a separate evidence axis. A future supplement needs its own owner, protocol, inclusion rule, denominator, overlap and rights; it cannot silently fill the 120 slots or the difficult-case minimum. |
| Historical inference | `/cutoff_policy/D_conditioned_inference_limit` | D membership conditions the earlier annual-document sample. This design is not a historical issuer population or probability sample. |
| Structural versus authenticated evidence | `/authority_boundary` | A parseable receipt, matching self-declared hashes or a correct kernel establishes at most `STRUCTURAL_ONLY`. Source authority, historical coverage, rights and derivation reconciliation remain separate verified states. |

**Memo locations:** INT in §9; frame sourcing and trust in §9.1; company/segment distinction in §8.1; D-conditioned inference in §5.

The first selector still needs a consequential principal choice: which existing trusted owner-review/admission receipt interface supplies authenticated source, coverage and entitlement decisions, and how the selector verifies that provenance. This recommendation creates no new signature scheme or authority registry. `trust_interface_selected_here` is null. Until a trusted interface is bound and verified, the selector may exercise structural or synthetic behavior but cannot claim real-source history readiness or select the real 120-issuer cohort. Missing verification yields `SOURCE_AUTHORITY_UNVERIFIED` and/or `SOURCE_RIGHTS_UNVERIFIED`; unknown rights are not falsely reported as a proved lack of a license.

## 5. Unchanged policy law and parameters

The correction does not change the five strata of 24, six activity groups of four in each stratum, 2 L / 1 M / 1 S cell quotas, INT 8 UK / 8 Japan / 8 EU constraints, one issuer per dual listing, 120 total, or the difficult-case and document-scope requirements. It does not change the recommended relative 50/25/25 count-band rule, equal-value boundary treatment, the 42 pool definitions, or the companion absolute USD boundaries. No Canada-specific relaxation is introduced.

The seed remains the literal `GMI-WP02-20261009-v1` even though this document version is v2; changing a policy version does not silently reseed its candidate order. D remains 2026-09-30 and K remains 2026-10-09T00:00:00Z. Share-count age, price age and common FX date bounds are unchanged. The capitalization construct remains a disclosed-share reference estimate; actual unobserved share changes are not claimed known. The activity and instrument decisions A01/A02/A03 remain recommendations pending principal adoption. No actual issuer has been selected or assigned a new identifier.

`ARTIFACT_VALIDATION.json` records the exact changed JSON pointers and equality checks for these invariants.

## 6. Correction checks and their limits

The standard-library-only `SYNTHETIC_METHOD_CHECKS.py` was run with Python `-B` against embedded artificial identities, dates, counts, values and relations. Its 12 controls passed. They cover the survivor-roster counterexample, reversible membership transitions and mismatched event rejection; same-fact conflict, measurement ordering, exact unit equivalence, scoped abstract supersession and cyclic relations; the price/share split bridge; residual selection against exhaustive feasible subsets across 720 permutations of six toy candidates; an isolated residual self-use/zero-target control; and duplicate toy identity rejection.

The code assumes source-authenticated correction edges as explicit premises of its artificial examples. It does not authenticate publisher corrections, historical venue coverage, bytes from financial sources or source rights. It is not the production selector or a source-receipt validator. No actual source frame, 120-issuer selection, application import, native replay, source acquisition or provider action was performed. The result is `PASS_SYNTHETIC_CONTROLS_ONLY`, not independent corrective-review PASS, source readiness, production admission or predictive evidence.

The primary source register is copied byte-for-byte from v1. This correction introduces no new external-source capture or raw-source hash. The initial review's six primary-source observations are attributed to that reviewer; reading their records is not presented as a new independent retrieval.

## 7. Handoff state

The package is frozen for independent corrective review. The previous review, v1 policy and measured frame deficiency remain intact. The principal owns A01/A02/A03 adoption, the trusted input interface, lawful frame sourcing, any later selector implementation and any real cohort freeze. Both R1 and R2 are author-implemented and pending independent judgment; all real selection, source-entitlement, predictive and production holds remain in force.
