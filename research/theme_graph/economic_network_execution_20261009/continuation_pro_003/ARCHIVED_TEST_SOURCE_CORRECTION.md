# Archive representation correction for PR #8711

**Preserve the exact two historical test sources as text archives. Keep the current canonical test suite unchanged.** The actual `contract-delta` gate for candidate `9df735bbeaa8d0f4d4967296270bfb2246a5212f` reported two introduced unrun-suite findings, both inside the frozen v1/v2 observation implementation evidence. That failed result remains part of this execution record.

The unchanged discovery rule in `scripts/audit_unrun_tests.py` recognizes Python files named `test_*.py` or `*_test.py`. These two source copies were retained as authored evidence, while the live v2 suite is `tests/test_company_relationship_observations.py`. Representing the historical copies as `.py.txt` makes that intended role explicit. Their contents are not edited, normalized, executed again or removed from the evidence archive. No discovery rule, CI inventory, source baseline, waiver or runtime code is changed by this correction.

## Exact archive resolution

[ARCHIVED_TEST_SOURCE_MAP.json](ARCHIVED_TEST_SOURCE_MAP.json) binds the full original repository paths and original checkpoint `6b58f15adae3b1d402d9993c52609d00083f1453`, the last original-path checkpoint `9df735bbeaa8d0f4d4967296270bfb2246a5212f`, and the current archival paths, lengths and SHA-256 values. V1 and v2 remain separate evidence versions:

| Version | Text archive | Bytes | SHA-256 |
|---|---|---:|---|
| V1 | [test_company_relationship_observations.py.txt](observation_implementation/v1/test_company_relationship_observations.py.txt) | 43,659 | `80acae7aadcecec3214fe86d77c99da841d2544629d35380ec11b5d9cc94d67e` |
| V2 | [test_company_relationship_observations.py.txt](observation_implementation/v2/test_company_relationship_observations.py.txt) | 49,406 | `a73700e639c8e97a4ff84951b48358abe63b1f5048560d03b0e40f2310ac44da` |

The author manifests and earlier checkpoint manifests stay byte-exact. Their logical source names describe the original checkpoint; current-tree verification resolves just these two names through the explicit map. Every other member keeps its existing path. A verifier must not apply a broad filename-rewrite rule or treat v1 as the current v2 application.

## Observed failure and remaining proof

Run `37925499382`, attempt1, actually tested synthetic merge `c852221c2bc4d8275c11c686094ccbf472f82ad9` with base `c4cd21d597521603fb75fe7a4602424e088c6bfa`. Its differential gate reported exactly two introduced and zero inherited unrun-suite findings. The complete failed-gate log is 30,995 bytes, SHA-256 `85fe520d6cb4f29cafe4f990a792bb7c28218742ac72a54e17710f0858666334`. The principal separately retains the [complete log](native_validation/pr8711-original-contract-delta-001.log): decoded connector content was encoded as UTF-8 and matched both the independently recorded raw-log length and hash. The independent CI packet itself retains bounded excerpts and the raw-log hash, not the full body. [The read receipt](native_validation/pr8711-original-contract-log-read-002.json) records this representation and the earlier CLI attempt, which stopped before writing a file.

The current owner suite separately passed all 275 tests in 8.73 seconds in that run. That observed pass is useful application evidence, but it does not turn the failed differential gate into a successful run or release. The source-composition review also independently proved the accepted Q07 insertion and the Company Intelligence enrollment compose exactly; no application repair was indicated.

Independent reading of the actual discovery code confirms that the two archival suffixes fall outside its existing test-filename rule. The principal's [native relocation receipt](native_validation/archive-representation-relocation-001.json) records the applied byte-preserving moves and all 53 unchanged code pins. A normal exact-head hosted gate remains required for the corrected commit. Neither static reasoning nor the earlier 275 native tests substitutes for that new concluded gate. There is no reason to repeat the unchanged native application tests merely to verify these two text representations.

All observation results remain `NOT_ADMITTED`, with no Graph1, production or predictive promotion. This correction concerns source custody and test inventory only.

## Retained independent evidence

The [original CI archive index](pr8711_original_ci_evidence_v1/ARCHIVE_README.md) freezes the failed/pending original-candidate observation at 12:14:53 UTC: 13 available artifacts against 15 expected, 97 of 98 selected jobs and 300 of 316 planned proof steps observed. Missing pack 0 and the final aggregate remain missing in this frozen record. The prior run is not relabelled by any later result.

The [source-integration review](pr8711_integration_review_v1/REVIEW.md) and its exact nine-file archive preserve the separate composition assessment. Both archive manifests are verified against every retained member during native transfer; archived verifier code is not executed again merely to transfer it.
