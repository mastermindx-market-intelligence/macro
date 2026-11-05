# Independent review: native rsync test-harness portability

**18 October 2026 UTC — bounded static addendum — accepted for the owning native rerun.**

No defect was found in the two supplied test-only portability changes. They give the already validated local rsync subprocess a fixture peer executable and remove one vendor-specific diagnostic assertion while retaining the substantive outcome checks. The deployment helper is byte-identical to the previously reviewed candidate. This disposition admits the narrow test-source successor; it does not establish a passing native run or production release qualification.

## Exact reviewed identity

All paths below are within `/workspace/scratch/da452a3ea08d/release_review/`.

| Artifact | Bytes | SHA256 |
|---|---:|---|
| `candidate/scripts/deploy_code_to_vps.sh` — unchanged | 20,370 | `1ebfd44db982d73f7f9d507109fa3983ba65cc948e8afe9fe697589d712728a8` |
| `candidate/tests/test_deploy_provenance.py` — final reviewed tests | 40,060 | `1e463a9116fb6c9bc6e6fe10ea23bf619d8674fd7e0ad6ce2392410e302a897c` |
| `native_run2_candidate/tests/test_deploy_provenance.py` — peer-fix stage | 40,161 | `d9dd66255444a70ba2160d30a2b62e540bcbc6620736030152cbef50c7ab7f59` |
| `pre_native_candidate/tests/test_deploy_provenance.py` — preceding tests | 39,649 | `a4ed6d45ed39eec1aa92ac9d4aeb82219dcefc60e9632e7f27dd8b00f6bfb42a` |
| `HELPER_NATIVE_RSYNC_PEER_FIX_2026-10-18.diff` | 1,986 | `6f18ebba77f2487be2dba7e11fa4deae12c4eecb17615ed821933816d5bc94df` |
| `HELPER_NATIVE_DIAGNOSTIC_ASSERTION_FIX_2026-10-18.diff` | 659 | `926c52c006e7fb8a02ebb2248edfb18d5e9c302a67e29e5b2eb5e403e9168fbb` |

The existing [helper semantic review](sandbox:/workspace/scratch/da452a3ea08d/release_review/HELPER_CANDIDATE_SEMANTIC_REVIEW_2026-10-18.md), 16,664 bytes, SHA256 `da500f46c8e839e09cefa447fe60f9255c22866693f5c742aa6e3672fefaa18a`, remains unchanged. It binds the helper to the preceding test hash. Its substantive protections, limitations and pending release gates remain in force.

## Narrow source findings

The first three-hunk delta changes only `_fake_transport` in [test_deploy_provenance.py](sandbox:/workspace/scratch/da452a3ea08d/release_review/candidate/tests/test_deploy_provenance.py). Independent standard-library AST comparison confirmed that all other top-level nodes, including every test function and its assertions, were unchanged at the intermediate `d9dd6625…` stage. The final successor changes one assertion as described below. The source was parsed as data; no first-party module or test body was executed by this reviewer.

At lines 98–105, the fixture retains its existing installed-rsync lookup and creates `rsync-peer-bin` under the fixture directory. That directory contains one `rsync` symlink to the resolved admitted binary. Lines 157–166 still remove the remote-shell option, accept only the fixture host prefix, translate it to a local destination and apply the existing fixture source/destination checks before invocation.

At lines 174–178, the additional peer-directory check precedes a copied subprocess environment. The new directory is prepended only for the real local rsync invocation. This is not a mutation of the helper's environment. The helper continues to receive the fake command directory first on `PATH` at line 290; line 299 supplies only the peer-directory fixture variable. The original shim path remains behind the peer directory for the child. Since the added directory supplies only rsync, the existing SSH, service, HTTP, Python and lock shims remain available in their prior order. The fake SSH's exact-host/argument admission and production-path rejection remain unchanged at lines 145–154.

These mechanics address the parent's observed local-peer recursion without changing helper control flow, broadening the admitted remote host, or weakening the existing path checks. This conclusion concerns the controlled fixture and the supplied delta; it is not a new general security claim about arbitrary adversarial fixture paths or executables.

The second delta removes only the literal `cannot delete non-empty directory: new_package` log assertion from `test_integrity_new_package_with_excluded_cache_fails_restore_closed`, beginning at line 601. Lines 608–618 retain the nonzero result, included-module removal, exact protected-cache bytes, restored old application bytes, helper-owned failed-verification classification, inactive service, restart history containing only the new release attempt, and absence of false completion. Independent AST comparison verified every other top-level node unchanged from `d9dd6625…`, and this one test identical after removal of that exact assertion. The retained assertions express the intended conservative recovery behavior without requiring a particular rsync vendor's prose. The earlier all-test-ASTs-unchanged finding must not be applied to the final successor.

## Evidence and remaining gate

The parent reported the first native run at 07:41:55–07:42:25 UTC with exit 1: Apple's rsync re-entered the fake shim with server arguments, and the guard refused them before source mutation. The builder's [portability note](sandbox:/workspace/scratch/da452a3ea08d/release_review/HELPER_NATIVE_RSYNC_PEER_FIX_2026-10-18.md) records the parent-bound 91,721-byte log, SHA256 `fcf4e967a0890eba39bddf6114b987de3d28a0a112425049deb5b7ce4dd96396`. That failure is retained, not relabeled as a passing helper test. This reviewer did not read or rerun the native log/process.

The two peer-fix-stage focused receipts were read and hash-verified: `HELPER_RSYNC_PEER_FORWARD_CONTROL_2026-10-18.json` (552 bytes; SHA256 `8d169856fc7cac92b95f02c26630dff4d9c8799261722a8a8b4d4df5c193e240`) and `HELPER_RSYNC_PEER_RESTORE_CONTROL_2026-10-18.json` (557 bytes; SHA256 `405cbc3ebc2b948686d22267750b72ecfdb564d675c085429db76fa08183a4c0`). Each records one passing standalone fixture control at `d9dd6625…`. They cover stop-before-copy/success and failed-copy rollback preserving excluded descendants. They use the builder's standard-library driver and local rsync, with no application imports or production calls recorded. They are not executions of the final successor.

The parent subsequently reported native run 2 at 07:47:42–07:49:27 UTC: 49 cases, 48 passed, one failed, zero skipped/errors, exit 1. Its supplied 7,482-byte log identity is SHA256 `c0986b80026beec6fae1e14c58ce6d3c92700317dbb33ef193fde9b3dc65bb09`. The sole failure was the vendor-specific assertion removed above. The parent reports that inspection established source removal, preserved excluded cache, old application bytes and the helper's incomplete/stopped outcome. These are attributed native observations; this reviewer did not independently execute the run or inspect its log. Run 2 remains a failed run at `d9dd6625…`, not a final green result.

The preceding 44/44 receipt remains bound to `a4ed6d45…` under `pre_native_candidate/`; its 8,506-byte hash remains `dbfe8dc9ec6b5f70d060883b7e34e0ca285e09c6ae7f35dcb1372546d046a003`. It is not a full-run result for either portability successor.

**Next actual dependency:** the native owner reruns the owning pytest suite at the exact final pair, retaining both preceding native failures and recording the result against `1e463a91…`. No further helper edit or source audit is requested by this addendum. The prior semantic review's broader release gates are unaffected. Production deployment remains prohibited absent separate current authorization.
