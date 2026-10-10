# Repaired intelligence contract: all original failures closed; two bounded validation gaps remain

**Disposition for script `83944fe1d2090012203701cbd6f79acfa77555b3d7457cae351080eaddc38fb2`: all six original gap families are repaired, with 13 of 13 failing variants now passing. The expanded acceptance suite passes 71 of 78 cases. Two malformed-input validation paths still require small amendments before claiming a fully controlled invalid-input contract.**

The principal's 56 checks reproduce byte-for-byte against its repaired `results.json`, hash `8b68899dd005ab869fba204d5eb1949bf2739de30e3bb75f8ed5d5188f1e1ebf`. The original review and its failing source snapshot remain unchanged. This is correctness research on synthetic inputs, with no production changes, vendor calls, new return study or ranking activation.

The complete executable evidence is in [ACCEPTANCE_RESULTS.json](ACCEPTANCE_RESULTS.json), produced by [accept_repaired_contract.py](accept_repaired_contract.py). [ACCEPTANCE_DESIGN.md](ACCEPTANCE_DESIGN.md) fixes the acceptance questions before execution; [INPUT_FREEZE.json](INPUT_FREEZE.json) binds the repaired inputs and the ten original review files that remain unchanged.

## Repaired behavior

| Original gap | Independent acceptance result |
| --- | --- |
| Boolean versus numeric duplicate identity | `True` versus `1`, and `False` versus `0`, consistently raise `ContractError("conflicting_source_version")` in both input orders. No order can turn the Boolean into measured evidence. |
| Equivalent numeric representation | `1` and `1.0` coalesce to the same canonical integer and the same selected-input digest in either order. Zero, negative integers and `2**53` have the same property. `2**53` and `2**53+1` remain distinct: claiming one version causes a conflict; using separate issuers preserves their strict percentile order. |
| Future malformed identity or revision | Valid future publication or first-seen availability excludes the row before unrelated malformed identity, revision, payload or metadata can affect the earlier selected digest or normalization. This includes the original three variants and additional malformed fields. |
| Invalid applicability on known higher retraction | Missing, invalid and naive `effective_from` values suppress the known higher version rather than return its old active observation. Reversing input order does not change that behavior. Valid future applicability still retains the prior effective value. All six permutations of a three-version correction/retraction sequence suppress consistently. |
| Invalid session equality | Missing, malformed and impossible expected dates now raise a defined `ContractError`. Invalid observed dates and mismatched valid dates suppress the chosen observation. Leap-day syntax remains accepted when explicitly supplied by the caller. |
| Noncanonical issuer identity | Trailing/leading spaces, lowercase or absent suffixes, invalid exchanges and wrong digit counts cannot enter the selected normalization population. Canonical `.SS`, `.SZ` and `.BJ` positive controls still work. |
| Unrepresentable JSON integer | `10**400` intelligence triggers the complete V3 fallback. As the known latest source value, it explicitly suppresses the observation with `not_finite_json_number`. No uncaught overflow remains in these cases. |

The table separates equivalent numeric representation from Boolean collisions for clarity; these comprise one of the six originally reported gap families.

The two original integration-boundary cases are also repaired. A row cannot reclassify a session family as periodic. Only a caller-declared periodic family is admitted, and an older valid periodic observation is not rejected by an arbitrary age cutoff. Normalization refuses mixed families, units or feature-contract identities, and it continues to require one qualified aggregate per canonical issuer.

Both newly added fingerprint fields are effective. Changing only `unit` or only `feature_contract_id` changes `selected_input_digest`, even with identical numeric values and percentiles. This verifies a selected-input fingerprint, not a complete generation identity.

The exact current population remains 125 qualified pre-cap names. Its incumbent `score_rank` order agrees with score descending and ticker ascending. Measured all-zero intelligence therefore reproduces the actual V3 order and published 24-name selection. A qualified missing-intelligence row outside the current shortlist still forces atomic fallback, confirming that coverage is checked before either cap. Current intelligence and incumbent shortlist overlap remains four names.

## Remaining bounded gaps

The seven failing probes fall into two families. They reject by crashing the helper before its defined exception path, rather than silently accepting a value. No stale-value resurrection or false numerical coverage is demonstrated by these remaining failures.

| Path | Counterexamples | Actual result | Minimal amendment |
| --- | --- | --- | --- |
| Caller-owned periodic-family validation | `periodic_families=None`, `1`, or `[["filing"]]` | Uncaught `TypeError` from constructing `frozenset`: noniterable or unhashable value. | Validate/materialize the iterable before constructing a set. Reject a string container, noniterable values and noncanonical/nonstring members with `ContractError("periodic_family_contract_invalid")`. Catch materialization type errors within that boundary. |
| Normalization metadata validation | Homogeneous `unit=[]`, `unit={}`, `feature_contract_id=[]`, or `feature_contract_id={}` | Uncaught `TypeError` because the set of contract tuples is constructed before validating each member. | Collect or iterate the metadata tuples; first require every member to be a nonempty trimmed string, then construct the distinct-contract set and require exactly one tuple. Use `ContractError("normalization_requires_homogeneous_feature_contract")` for invalid fields. |

These are bounded error-handling issues. They matter if the existing caller catches `ContractError` to record a refusal or preserve an incumbent result: a leaked `TypeError` can instead abort that caller. They are not evidence that current stored data contain malformed metadata. The repaired hash can be accepted for the 13 closed counterexamples; complete acceptance of the declared hostile-input surface remains pending these two amendments or an explicit upstream schema-validation guarantee.

## Integration premises retained

Numeric completeness does not establish compatible generations, source times or calibration. Adding incompatible synthetic generation labels still leaves the numeric helper in intelligence mode; the helper makes no claim to validate those labels. The existing generation owner must bind qualification, coherent incumbent score/rank, intelligence inputs, the normalization population and calibration receipt before calling this ordering function.

Likewise, contradictory caller-supplied scores and ranks can produce different all-zero intelligence and fallback orders. The current 125-row population was checked and is coherent. The synthetic contradiction is retained as an integration premise, not counted as a new failure of a claim that the amended design no longer makes.

Calendar-date syntax is not a trading-calendar proof. The source/calendar owner must supply the expected source-specific session and cadence. Missing publication or first-seen provenance still cannot certify complete system-observed history; authoritative revisions cannot be invented from arrival or hash order. This laboratory does not solve those ownership questions by validating numbers.

The actual analyst duplicate finding remains negative. Independently canonicalizing all 475 duplicate payload groups finds one unique payload in every group. The existing hash-bound reader receipt reports zero conflicting groups and zero changes to consensus, raw ratings or percentiles under physical row reversal. This acceptance recomputes payload equality locally; it does not claim a new remote reader replay.

## Reproduction and preservation

Run `python accept_repaired_contract.py` from this directory or invoke it by full path. It uses only the immutable local `reviewed_source/` snapshot, replays the principal suite in an owned temporary directory and verifies every initial review hash before and after execution. Its result deterministically retains both passing and failing cases. A later repair must receive a separate snapshot and acceptance receipt; these results should not be overwritten to appear passing.
