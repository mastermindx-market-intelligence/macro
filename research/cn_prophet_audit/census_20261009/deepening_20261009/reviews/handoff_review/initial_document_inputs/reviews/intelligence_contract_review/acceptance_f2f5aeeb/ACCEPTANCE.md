# Independent acceptance: final repaired intelligence contract

**Accept the bounded research contract at script SHA256 `f2f5aeeb27b87809123148a642b9d6b848290a82033b7118614288432c8af014`. All 79 acceptance cases pass, all 13 original failing variants are closed, and all 56 principal controls reproduce byte-for-byte. No remaining blocker was found within the identified contract surface.**

This acceptance supports implementation of the tested correctness boundaries through the existing source, qualification and generation owners. It does not authorize an intelligence ranking policy, new feature store or production activation. The laboratory does not establish investment improvement, execution quality or historical source-time completeness.

The full evidence is [ACCEPTANCE_RESULTS.json](ACCEPTANCE_RESULTS.json), produced by [accept_repaired_contract.py](accept_repaired_contract.py) under [ACCEPTANCE_DESIGN.md](ACCEPTANCE_DESIGN.md). The exact inputs and prior-review hashes are in [INPUT_FREEZE.json](INPUT_FREEZE.json). The principal result reproduced by the acceptance script has SHA256 `97f51b947a3be417e132b08ebaa98b3f0546c1a629a459cc98fb32e6b0d6fb97`.

## What is settled

| Contract boundary | Verified behavior |
| --- | --- |
| Exact duplicate identity | Numeric `1` and `1.0` coalesce deterministically. Boolean `True` versus numeric `1`, and `False` versus `0`, fail consistently as conflicting versions in either input order. |
| Large numeric identity | `2**53` and `2**53+1` remain distinct values. A same-version collision is refused in either order, while separate issuer observations retain strict percentile order. Finite source values remain valid; unrepresentable intelligence falls back atomically, and an unrepresentable latest source value suppresses the observation. |
| Cutoff noninterference | Provably future publication or first-seen availability excludes unrelated malformed identities, revisions, payloads and feature metadata before they can alter past selected inputs or normalization. A changed rejected-row diagnostic is not treated as a changed decision. |
| Known revisions and retractions | A known higher revision with missing, invalid or naive applicability suppresses its observation rather than restore an older active value. Valid future applicability retains the prior effective value. All six input permutations of the three-version correction/retraction fixture give the same suppression. |
| Canonical issuer and session identity | Malformed issuer aliases cannot enter the normalization population. Missing, malformed and impossible calendar dates are refused through the contract error model. A mismatched source session suppresses the chosen observation. Valid supported issuer syntax and caller-supplied valid dates remain usable. |
| Owner-declared cadence | A session-family row cannot declare itself periodic. Explicitly declared periodic families remain usable without an arbitrary age limit. Undeclared or conflicting family contracts are refused. Malformed periodic-family collection types now raise `ContractError("periodic_family_contract_invalid")`. |
| Qualified pre-cap coverage | Every qualified competitor contributes to intelligence coverage before either cap. Missing intelligence on a qualified name outside the current shortlist still forces the complete incumbent order. Measured zero remains valid. |
| Normalization identity | Normalization requires one family, unit and feature-contract identity and one qualified aggregate per canonical issuer. Mixed, missing or malformed metadata is refused. Lists and objects now raise the defined contract exception before set construction. Multiple source observations require the existing qualified aggregation rule. |
| Selected-input fingerprint | Changing only `unit` or only `feature_contract_id` changes the digest even when numeric values and percentiles stay identical. Equivalent numeric duplicate representations do not change the digest by input order. |
| Record object boundary | The newly added guard refuses `None`, an integer, a string and a list with `ContractError("source_record_not_object")` before reading row fields. |

The current 125-name qualified pre-cap population was checked directly. Its incumbent score-rank order is coherent with score descending and ticker ascending. Measured all-zero intelligence reproduces that incumbent order and the actual published 24-name selection. The current intelligence shortlist retains four incumbent names. Those controls demonstrate exact current-data reproduction and selection influence; they do not demonstrate alpha.

## Repair history remains reviewable

The initial independent review preserved 13 failing synthetic variants across six gap families. Its source snapshot, results and manifest remain unchanged. The first repaired hash closed all 13 but passed only 71 of 78 expanded acceptance cases: malformed cadence configuration and unhashable unit/feature-contract metadata leaked `TypeError` before the defined refusal path. That first repaired source, its seven failures and its manifest also remain unchanged under [acceptance_83944fe1](../acceptance_83944fe1/ACCEPTANCE.md).

The final candidate validates those scalar/collection types before set construction. All seven previous failures now produce the expected `ContractError`. The final review reuses all 78 expectations without relaxation and adds one direct case for the new record-object guard. It stops at 79 passing cases, with no additional feature hunting or general fuzzing campaign.

## Upstream premises required for implementation

The ordering helper establishes numeric completeness over a supplied qualified population. **It does not establish compatible generation, source-time or calibration identities.** The existing generation owner must bind the qualification population, incumbent scores and ranks, intelligence inputs, normalization reference population and calibration receipt before invoking the helper. Synthetic incompatible generation labels remain ignored by the numeric helper; this is an explicit ownership boundary.

Coherent incumbent score/rank inputs are also a caller premise. Contradictory synthetic scores and ranks can give different all-zero intelligence and fallback orders. The current population was independently verified to be coherent; the result is not generalized to arbitrary caller inputs.

The source/calendar owner must supply expected source-specific sessions and declared cadence. Valid date syntax alone does not prove an exchange trading session. The source selector assumes authoritative observation identities and numeric revision ordering from an existing owner. It cannot recover complete history from missing publication or first-seen fields or manufacture revision order from arrival order or hashes. Multiple observations per issuer must pass through the existing qualified aggregation rule before cross-sectional normalization.

The selected-input digest is a useful fingerprint example. It is not a substitute for complete upstream lineage or generation compatibility. These required bindings should be concrete integration acceptance checks in the implementation handoff; they are not certified by the 79 laboratory cases.

## Current-data negative finding and custody

The actual 475 analyst duplicate payload groups remain identical under independent canonical payload comparison. The existing hash-bound reader receipt reports zero conflicting groups and zero consensus, raw-rating or percentile changes under physical row reversal. This acceptance recomputes local payload equality and uses the existing reader receipt; it does not claim a new remote reader replay. The synthetic repairs do not establish present-data corruption.

The suite verifies all ten initial-review files and all eleven first-repaired-acceptance files before and after execution. It reads the final candidate from its separate exact snapshot and replays the principal suite in an owned temporary directory. No principal source, original study result, matched-control file, production file or PR is modified. No vendor call or remote replay is made. Study source remains `3d90aad6d83152dfeeaf8345bc995826ac9d3139`.

Reproduce with `python accept_repaired_contract.py` from this directory or invoke it by full path. The script deterministically writes only this acceptance result and verifies the preserved review history. [MANIFEST.json](MANIFEST.json) records the final package hashes; [VALIDATION.json](VALIDATION.json) records terminal artifact and custody verification.
