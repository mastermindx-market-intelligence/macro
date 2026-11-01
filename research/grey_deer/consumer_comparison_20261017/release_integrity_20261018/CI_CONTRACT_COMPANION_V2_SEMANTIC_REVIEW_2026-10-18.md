# #1610 companion v2 — independent F1 successor review

**18 October 2026 UTC · F1 closed by source review · Semantic design accepted for the coupled successor · Native acceptance pending**

The narrow successor closes my canonical-root/release-SHA handoff finding. No remaining issue in this delta blocks semantic acceptance of the proposed four-file companion design. This disposition does not admit native writes, test execution, custody, or release. The coupled removals still require their replacement evidence to be qualified on the admitted native candidate.

## Exact identity and preserved history

Independently hashed review inputs:

| File under `release_review/` | Bytes | SHA256 |
|---|---:|---|
| `ci_contract_candidate_v2/tests/test_deploy_provenance.py` | 47,847 | `0da8a0d094b3b6f20bdedbdc427481a6425d709736621e7c5554a125cf78cc48` |
| `CI_CONTRACT_COMPANION_V2_REVISION_2026-10-18.md` | 8,128 | `a82aaee29c3d910cf9f369891d12521bbef31bcd82f729d93860a3569b1da11a` |
| Unchanged `ci_contract_candidate/tests/test_datadog_vps_install.py` | 5,991 | `a5a118e2c852902dd908913929a0f598f1c00bf970475a0c780e81b484244e95` |
| Unchanged `ci_contract_candidate/tests/test_forward_evaluation.py` | 31,215 | `637c6dbe5b304bd69a66f68ae4d8e58538bd1279914132c40d2cf924f7d4cf8d` |
| Unchanged `ci_contract_candidate/tests/test_portfolio_archival.py` | 16,993 | `0d82dc934e3d16b954c859cfec2c9cfff17013cf9d785678eb5a8ee26a4ad384` |

The preceding REQUEST_CHANGES review remains unchanged: `CI_CONTRACT_COMPANION_SEMANTIC_REVIEW_2026-10-18.md`, 12,923 bytes, SHA256 `318ec1f753d0540af6541e96deb35425f6a117f6c1d39d6f33677ac92f53c3b1`. The preceding deployment-owner proposal also remains unchanged at 46,634 bytes, SHA256 `90b872cb6de4d7b8b2c53cc91f747c0c24b6e1fc881526081c5369d9805aa59c`. This is a successor disposition for different bytes, not a rewrite of that finding.

## Why F1 is closed

**Actual root input:** the fake `python3` branch now reads the received `MASTERMIND_FORWARD_EVALUATION_RELEASE_STATE_ROOT`. Missing/blank and relative values fail. Strict resolution rejects nonexistent paths, and the resolved path must equal the fixture's existing canonical live-data root. The marker path is then derived from that validated received root. A path identifying another existing directory is refused. A symlink alias resolving to the same admitted directory is accepted, which is consistent with checking destination identity in this controlled fixture.

**Actual SHA input:** for `init` and `finalize`, the branch collects separate-value and equals-value `--deployment-sha` forms. It requires the resulting list to contain exactly one value equal to the expected target. Missing, empty, duplicate, conflicting, wrong, or terminally truncated forms fail. A separate option followed by another SHA option also fails rather than treating the second option as an acceptable SHA. Newly initialized `deployment_sha` and finalized `health_verified_sha` use the validated received value.

**Validation precedes modeled operation effects:** both checks occur before `gate(command)`, marker-directory creation, marker reads/writes, and the deliberate foreign-init failure injection. Strict path resolution itself is a filesystem read. `status` receives the same root check without an invented SHA requirement. The previous counterexamples—omitting/misrouting the CLI root or passing the old SHA—can no longer be silently replaced with fixture defaults at this boundary.

These are source-level conclusions. No malformed-input probe or fixture was executed. The SHA scanner is intentionally not a complete emulation of the real CLI argument parser: unrelated/unknown flags and date parsing are outside this repair. The retained real-CLI unit owner and the checked fake handoff still prove different parts of the contract when executed. Filesystem-race protection and arbitrary hostile-helper containment are not claims of this controlled test harness.

## Preservation verified

Exact test-function source and AST comparisons, including decorators and parameter values, found:

- All **37 original deployment test functions / 49 literal parameter cases** unchanged against the frozen owner.
- All **40 proposed deployment test functions / 59 literal cases** unchanged against the first companion proposal.
- Every top-level AST node outside `_fake_transport` unchanged from the first proposal.
- Both embedded transport strings parse successfully through the standard-library AST parser.

The source diff is confined to the received-root/SHA validation and use of those validated values within the existing fake CLI. There are no new test cases, suppressed assertions, or changed test bodies. The three other companion hashes remain their original proposed identities.

## Acceptance boundary

The first review's favorable Datadog, policy-transfer, observer, and no-op design findings remain applicable; its F1 coverage objection is closed for this successor. All recorded limitations remain. The preserved 49-case native pass is not transferred to v2, and the three failed hosted checks retain their failed attribution until properly superseded by new evidence.

Root may proceed with its separate custody qualification and then the admitted native validation workflow. **There is no new passing test receipt in this review.** Local source/document reads, hashes, textual diffs, and AST parsing/comparison were the only review actions. No helper/shim execution, test collection/run, first-party import, native/Git/provider operation, production action, or source edit occurred. Only this new review was written.
