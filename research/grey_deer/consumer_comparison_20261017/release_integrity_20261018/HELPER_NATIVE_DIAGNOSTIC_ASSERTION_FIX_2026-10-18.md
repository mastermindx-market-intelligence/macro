# Native rsync diagnostic assertion correction

**18 October 2026 UTC · One test assertion removed · Final native suite pending**

The parent-reported second native owning pytest run reached **48 passed, 1 failed, 0 skipped and 0 errors across 49 cases**, 07:47:42–07:49:27 UTC, exit 1. The only failing assertion required GNU rsync's exact text `cannot delete non-empty directory: new_package`. Apple's rsync reported that condition differently. The parent observed that the included module was removed, the protected cache retained, the old application bytes restored, and the helper itself reported incomplete recovery with the service left stopped.

The run2 log identity supplied by the parent is 7,482 bytes, SHA256 `c0986b80026beec6fae1e14c58ce6d3c92700317dbb33ef193fde9b3dc65bb09`. The subagent has not executed native pytest or inferred a passing final suite from that nearly complete run.

## Exact successor

| File | Bytes | SHA256 |
|---|---:|---|
| `candidate/scripts/deploy_code_to_vps.sh` — unchanged | 20,370 | `1ebfd44db982d73f7f9d507109fa3983ba65cc948e8afe9fe697589d712728a8` |
| `candidate/tests/test_deploy_provenance.py` — one assertion removed | 40,060 | `1e463a9116fb6c9bc6e6fe10ea23bf619d8674fd7e0ad6ce2392410e302a897c` |

The [exact diff](HELPER_NATIVE_DIAGNOSTIC_ASSERTION_FIX_2026-10-18.diff) removes only the vendor-diagnostic assertion from `test_integrity_new_package_with_excluded_cache_fails_restore_closed`. The test still asserts all of the following:

- Failed deployment exit status.
- Removal of the new included module.
- Exact preserved bytes of the protected cache.
- Exact restored old application bytes.
- The helper-owned `restoration failed verification; leaving service stopped` classification.
- An inactive service and a restart history containing only the attempted target SHA.
- Absence of a misleading `rollback complete` result.

AST comparison verified that this one assertion is the only removed statement. Every other statement in the test, every other test function and the entire transport fixture remain unchanged from test hash `d9dd6625…`. The production helper is byte-identical.

## Evidence continuity

The **all-test-ASTs-unchanged** statement applies to the preceding peer-lookup correction from `a4ed6d45…` to `d9dd6625…`. It does not describe this successor: one test intentionally changes by removing its vendor-specific message assertion. The other 48 native cases are unaffected.

The `d9dd6625…` helper/test pair and manifest are preserved under `native_run2_candidate/`. The earlier `a4ed6d45…` pair and 44/44 standalone receipt remain under `pre_native_candidate/`; original and review-red evidence are unchanged. No earlier passing receipt is reassigned to the new test hash.

No test suite was rerun in the cloud for this one-line assertion correction. The parent will run the final owning native suite against these exact files. Independent reviewer `forward_activation_review` has the one-line diff, new hash and run2 log identity. No new helper behavior, assertion on implementation internals, source owner or production action is introduced.
