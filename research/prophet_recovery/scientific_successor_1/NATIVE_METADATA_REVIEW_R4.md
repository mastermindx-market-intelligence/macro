# H1 R4 — native metadata donor: bounded scientific source review

Operation: `prophet-frontier-hypotheses-20260926-sol-001`. Recovery: `prophet-frontier-successor-1-20260928`. Scientific-design successor reporting to parent Sol. Current Chairman instruction: continue. Cumulative return: macro#6805/5861635963.

**Overall disposition: HOLD for native integration and H1 execution. Bounded metadata-only source-design assessment: PASS.** No new blocking defect was found in that declared design on the inspected donor. This is an author-distinct static source/evidence review, not independent native re-execution, broad security certification, source release, or execution-bound protocol acceptance.

## 1. The material change

R3 established that unrestricted `load_grades(columns=..., months=...)` could decode numerical outcomes before redacting the returned frame. The parent has since supplied an implemented opt-in remedy, not merely another specification: native return #8091/5868451549 and science pointer #6805/5868458844.

The proposed `metadata_only=True` path addresses R3's unrestricted fallback and silent-refusal problems at source-design level. Retain the implementation and proceed to legitimate native adoption and consumer proof. Do not repeat the original R3 witnesses as though no remedy exists. Conversely, do not call all of R3 closed: training-key isolation, actual consumer wiring, source authorization and evaluation-stage separation are separate obligations.

R1 plus AR1–AR4 remains accepted by #6805/5865586990 and the Agent OS overlay at f478898c21962d7a4d17359051d8b1055561ab14. The three sleeves, eleven controls, C2-minus-C1/K5/H10, fixed ridge fits, original one-fifth weights, strict missing-selected rules and 50/25/25 pilot criteria are unchanged. R2's original-population, raw-liquidity and ordinary-industry requirements remain. No parallel risk-policy intervention is imported.

## 2. Exact review target and evidence

All donor paths below are under `research/prophet_recovery/grade_metadata_native_candidate_20260928/` in mastermindx-market-intelligence/macro at **0ac7db9ad531a2f5ea5e5c4a376ae2a28ce86a91**. The target is this immutable donor, not a claim about current main or a later source branch.

| Object | Exact identity |
|---|---|
| grade_metadata_native.patch | Git blob 3b017e8d6bb0ec6f4961702b9897844bd0a9c7d4 |
| Donor-declared patch SHA256 / size | b85bda281b8a307069db0f294a05d93053e853c38286bd661a87c92f55c306d8 / 33,973 bytes |
| Native application base | c72d5d7e5defc9582e032f72fa23a8fc90737aac |
| engine/us_prophet_grades.py | 0653dd6fecbdb484557c101a634f2188dacf10a5 -> proposed 5d4dbd2ea628efdfff70b4929a257308721721ed |
| tests/test_us_prophet_grades.py | f8db9523b69dbab0c7b7de66f37de1d3632f5ae4 -> proposed fb5e1f528d30c124df75d59f6f9edeb3879b37e3 |
| README.md | b99915d91dbd87708675759118ff5c77df33da9b |
| ACCEPTANCE_RECEIPT.json | be3c98222828d882f26547012c8c751466f4728b |
| MUTATION_REPORT.json | 609f1c55ba6725b7738047fffbd02cf0b58ea5bc |
| QUALIFIED_JUNIT.xml | d4dc0500c3431ea9fe1e22b5dcf6155a71f3ad6a |

Native GitHub reads supplied the patch, README and receipts. Patch hunks and relevant test bodies were inspected, including the read trace. The native Git blob identities are directly returned evidence. The donor's SHA256 and proposed-file identities are its bound receipts; this reviewer did not claim to recompute the original donor hash or reconstruct its full native module locally.

## 3. Source-design findings

### A. Projection cannot silently broaden in the strict branch

`load_grades` validates the boolean mode and dispatches `metadata_only=True` before entering the legacy body. `_load_grade_metadata` requires an explicit nonempty, unique list of allowed metadata columns and all four native key columns. Outcome columns are rejected even when all required keys are present.

The strict path obtains the schema, intersects requested permitted columns with available columns, reads only that intersection, and supplies nulls for absent permitted additions afterward. There is no strict-branch call to unrestricted `pd.read_parquet`. An ordinary read exception becomes `GradeMetadataReadError("PART_UNREADABLE", part)` rather than a full-column retry. The broad legacy fallback remains intentionally confined to the default path.

The corresponding test forbids pandas fallback and traces requested and returned Arrow column names. Author mutation M02 deliberately restores unrestricted decoding and is recorded as caught by that targeted test. **Assessment: R3's metadata fallback objection is addressed by the donor's source design; deployed caller behavior remains unproved.**

### B. Refusal and valid emptiness are now distinguishable

The candidate compares the selected native part set with an explicit expected catalogue before decoding. It refuses missing, unexpected, corrupt, mismatched-size/hash/row-count parts and changed part names instead of returning surviving rows as a complete result. A missing store is `STORE_UNAVAILABLE`; an explicitly empty catalogue with an existing empty store can return a zero-row result with a scoped receipt.

This is all-or-nothing completeness for the supplied grading-run catalogue only. It does not recover missing original candidate counts or prove that the requested catalogue was the correct one. The returned receipt explicitly identifies its limited scope and leaves rights and label-usable-time verification false. Tests and author mutations M05/M06 discriminate failure from healthy emptiness. **Assessment: the strict helper no longer uses warning-plus-empty as its ordinary refusal result. The actual consumer must preserve that distinction.**

### C. Identity is tied to one encoded snapshot

`_grade_metadata_snapshot` copies the bounded encoded object, verifies declared size and SHA256, and returns that same temporary snapshot for schema, row-count and projected data reads. Schema inspection is not performed on one live path generation while decoding another. The source-replacement test and mutation M07 specifically challenge that relationship.

The final catalogue reread detects changed part names, not a guarantee that the live source paths still contain those bytes after the read. Returning the verified declared snapshot after a later path replacement is intentional and tested. Do not represent the receipt as proof of current live-path freshness.

**Important limit:** all encoded object bytes are copied/hashed. A Parquet footer can contain statistics. This is not a promise that no outcome-bearing encoded bytes or footer metadata enter the custodian process. The donor discloses this; the source grant must permit the actual read/copy. A broader authorized custodian and a restricted fitting process are different scopes. No worker may self-approve the catalogue or replace a missing grant with its own hashes.

### D. Nested fields and index enrichment receive explicit treatment

Before projected decoding, requested fields must have permitted scalar types; nested fields and duplicate schema names are refused. The Arrow read disables pandas-index enrichment and conversion ignores that metadata. The delivered tests use a nested outcome and an outcome-valued pandas index, rather than merely checking the final metadata column list. Author mutations M08/M09 are reported caught by those specific tests.

The native optional field is correctly named `bench_inserted_session_count`; its nullable floating representation is accepted only for finite, nonnegative integral non-null values. This is metadata validation, not benchmark or research eligibility. No inference is made from null identifiers or count fields merely because the reader returned them.

### E. Legacy behavior is deliberately not converted into a research gate

The production hunk is additive: new strict helpers and an opt-in dispatch precede the previous body. There is no change in this patch to numerical grading, nightly advancement, historical rows or the remaining existing functions. The donor reports AST identity for the original body and eighteen functions, plus separate legacy comparisons. This review inspected the diff rather than independently repeating that AST reconstruction.

Do not force legacy callers into strict mode as a side effect of adoption. Do not infer that legacy access has become research-safe because a new optional mode exists. A real B10/B06 consumer must demonstrably choose the strict mode for metadata and correctly handle its receipt/refusal.

## 4. What the test evidence actually says

The committed JUnit declares **73 tests, zero failures, zero errors and zero skips**, timestamp 2026-09-28T03:44:33.967252-07:00. Its cases comprise 63 metadata cases and 10 auxiliary legacy-compatibility cases. The added metadata tests are in the delivered patch; the ten auxiliary cases belong to the donor's separate local comparison harness. Do not expect the native `-k metadata` command alone to reproduce all 73 or call those 73 the complete repository suite.

The accompanying receipt reports Python3.14.7, pandas3.0.5, PyArrow25.0.1 and pytest9.1.1, real synthetic Parquet I/O and full-module loading with four non-reader dependency groups guarded. Those are the producer's recorded environment and execution, not this reviewer's environment or a full unstubbed deployment proof.

The mutation report records nine caught variants with exit1 and no setup errors. Each maps to a relevant assertion: outcome allowlist, unrestricted decode, digest, row count, corrupt-part omission, missing-part omission, different-path decoding, nested fields and index enrichment. The source tests were inspected for those distinctions. The report is author mutation evidence, not independent re-execution; the mutant source bodies are not among the five committed donor files.

One minor reproducibility correction is warranted: README names `QUALIFIED_TEST_OUTPUT.txt` as an actual result, but that file is not in the immutable five-file donor directory. Use the available JUnit and explicit receipt for this review. If the full 73-case local replay is needed, the owner should attach its retained auxiliary harness/output through the existing evidence path. This packaging discrepancy does not by itself refute the committed JUnit or block the source-design recommendation.

This reviewer ran no new native or real-Parquet tests. The current sandbox reports Python3.13.5/pandas2.2.3 with PyArrow absent. One read-only download of the new donor patch failed DNS and produced no patch file; native GitHub source reads succeeded. No dependency-install retry, alternate-host workaround, prior-fixture rerun or numerical experiment was performed. This limitation prevents an independent-runtime PASS, not a bounded source review.

## 5. Narrowed execution disposition

| Boundary | R4 disposition | Evidence still owed |
|---|---|---|
| Strict metadata projection source design | PASS within the inspected donor's stated trust scope | Native source adoption and actual-runtime conformance |
| Donor implementation qualification | Producer local evidence consumed; no new source-design blocker found | Owner's full applicable native/CI checks and required source/security review |
| Real metadata-only H1 intake | HOLD | Authorized immutable catalogue; real caller using strict mode; propagated receipt/refusal; rights, identity, original-population and clock proof |
| Training-label isolation | HOLD, not implemented by metadata mode | Exact permitted native grade tuples and accepted label-known/support cut before values reach the fitting process |
| Calibration/test isolation | HOLD, separate stage obligation | Verified coefficients/scalers and frozen predictions/selections before evaluation outcomes reach the evaluation stage |
| Full H1 numerical experiment | NOT_ADMITTED | Native input release/normal capture, R2 primitives, literal partitions/prior-access inventory, code/environment/trial/budget, independent execution-bound review and existing native smoke |

Requiring the four key COLUMNS is not restricting values to allowed four-field KEY TUPLES. The donor accepts no allowed-training-key argument and its strict allowlist excludes `excess_spy`. This is correct for a metadata reader, but it cannot also supply the training outcomes. R3's exact-key and stage-isolation requirements therefore remain with the native B06/B10 execution owner. Do not solve them by reading all outcomes and filtering afterward inside the fitting process. Do not add a new evaluator or research security plane to this review.

No missing input is treated as zero coverage, H1 failure or negative predictive evidence. No accepted economic threshold is reopened. Source capture and ordinary product reliability remain independent of these numerical-execution gates.

## 6. Exact next owner result

Parent/native empirical owner: consume the donor and this bounded review, reconcile the legitimate current source-adoption edge without repeating the refused custody census, and return one exact integrated revision plus applicable native verification and a source-bound metadata-only consumer trace. Keep the change on the rightful existing carrier; do not blindly append it to held #8091 or create a competing writer.

The first real intake must bind the authorized catalogue, actual strict call, decoded/output column trace, explicit failures versus emptiness, and the metadata receipt to the same source generation. Carry R2's original candidate inventory, twenty paired raw close-volume sessions, ordinary-industry bindings and issuer-safe peers separately. Label-known time cannot be invented from `graded_asof`.

The scientific successor then binds the actual redacted calendar/support/prior-access package to accepted R1 and reviews the native training/evaluation separation. An admitted empirical result is still required for a build/shadow/reject disposition. If adoption is genuinely blocked, return the exact owner/gate and preserved source/effect state; no abandoned-chat ACK or new scientific-threshold meeting is required.

This is a nonterminal scientific review result, not a worker dispatch, lease transfer, PR approval, merge or global hold. No watcher was created. Required independent execution-bound protocol review remains open. Original empirical workspace/effects remain UNKNOWN/PRESERVED.

## 7. Durable identities and procedure

Protected Mastermind pin: bf709270f29f5445288e8f453fe82f6c4dd389b4. INDEX blob94d1af402598894372858793a5b1931019c5fa77; Skillpack1.0.1/bootstrap1 compatible. Same-commit ACTIVE_EXECUTION, WEB_CEO_DELEGATION, REVIEW_RETURN, RECONCILE_STATE and CLOSEOUT loaded. Direct review reason: PRINCIPAL_JUDGMENT.

Own permitted publication surface: existing disjoint branch `review/prophet-frontier-successor1-20260928`, reconciled at e608eed686f0d2d72c1c5aa88b343f5cea487b63 before this record. Only this new review document is proposed for addition. R1/R2/R3, parent#7980, incumbent application/empirical/economic/Paper paths and all financial policies remain untouched. No original data, protected outcome, fitted model, external child, source release, deployment or autonomous computation occurred.

MISSION_COMPLETE:false. The completed unit is exact donor review and a scope-specific disposition, not a shipped fix or a proven predictor.
