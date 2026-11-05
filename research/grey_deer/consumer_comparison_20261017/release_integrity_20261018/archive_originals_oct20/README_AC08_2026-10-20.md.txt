# Deployment-helper release integrity evidence — 18 October 2026

This packet records the bounded helper repair supporting delivery of the accepted Mastermind #1567 future-source-date fix. The source change is [PR #1610](https://github.com/mastermindx-market-intelligence/Mastermind/pull/1610), reported head `797c760f3e18eb6993579f56986103de9d9fdcb4`. **The final native owning suite passed 49/49, including the five application cases. Source landing, production deployment and Risk Radar delivery are not established by this packet.**

**Subsequent required CI failed.** Run [39109519443](native/rr-helper-ci-39109519443-result.json) failed three wider static deployment-contract tests; the native 49-case pass remains narrower evidence. At **08:28:04.970897Z**, [#1610 was confirmed draft](native/rr-helper-ci-failure-draft-disposition-20261018.json), unqueued and without auto-merge. The [single observer completed](native/rr-helper-ci-39109519443-watch-receipt.json), exit 1; no active watcher, rerun or waiver is claimed. Exact companion-test guarantees and current source-writer custody require qualification before a source successor.

Only `scripts/deploy_code_to_vps.sh` and its existing owner `tests/test_deploy_provenance.py` change. The archive wrapper, forward module, models, samplers, policy owners and accepted programme evidence retain their existing ownership. Earlier reports and manifests preserve the stage they reviewed; their pending-native language predates the final native result below.

## Evidence packaging correction — 18 October, after 09:16Z CI failure

Macro evidence PR #9595 at `f11fa0c66273ca1976f37e2f529fe9ff689ee439` failed run **39113159863**. Six retained Mastermind test copies were classified as unregistered Macro pytest suites; retained foreign application/test source produced 27 unresolved first-party-import findings. These are publication defects in this evidence packet. The [path-and-hash map](ARCHIVE_PATH_MAP_2026-10-18.json) now names all 25 Python and shell evidence copies with a `.txt` suffix while preserving every raw byte and Git blob. This adds no Macro source, test registration, CI waiver or change to the owning Mastermind files.

The original transfer manifests and source-review paths remain historical logical names; resolve the 25 renamed paths through that map. The prior four-space Markdown normalization remains independently recorded below. The [failure and repair record](CI_FAILURE_AND_ARCHIVE_PACKAGING_2026-10-18.md) also retains the three reference-integrity findings that hosted CI reproduced on both its base and candidate. PR #9595 was disarmed and returned to draft at **09:21:38.439890Z**. A new exact-head CI result and landing receipt are still required.

The [independent packaging review](ARCHIVE_PACKAGING_REVIEW_2026-10-18.md) accepts the earlier lossless archive representation with its stated limits. The unchanged owning Macro import-check module passed [15/15 native cases](rr-evidence-archive-import-native-receipt-20261018.json). A broader 170-link publication check then found nine archive-rename links and five inherited transfer-path links unresolved in three historical reports. The [bounded link repair](PUBLICATION_LINK_REPAIR_2026-10-18.json) changes only those 14 destinations and retains all three complete [original texts](PUBLICATION_LINK_REPAIR_ORIGINALS_2026-10-18.json). It does not alter historical findings or turn the native import result into whole-CI acceptance.

## Start here

| Evidence | Purpose |
|---|---|
| [Accepted #1567 release-scope review](MASTERmind_1567_RELEASE_SCOPE_REVIEW_2026-10-17.md) and [forward-activation review](FORWARD_ACTIVATION_REVIEW_2026-10-18.md) | Source acceptance, actual release boundaries and the historical active-cohort context. |
| [Forward dependencies](FORWARD_DEPENDENCY_REVIEW_2026-10-18.md), [settlement finalization callers](SETTLEMENT_FINALIZATION_CALLER_REVIEW_2026-10-18.md) and [settlement dependency notes](SETTLEMENT_DEPENDENCY_STATIC_NOTES_2026-10-18.md) | Existing callers, custody and durable-effect boundaries; no new writer authority. |
| [Repair proposal](HELPER_REPAIR_PROPOSAL_2026-10-18.md) and [implementation handoff](HELPER_REPAIR_IMPLEMENTATION_2026-10-18.md) | Original defects, coherent two-file repair, failure controls and explicitly unexecuted variants. |
| [Independent semantic review](HELPER_CANDIDATE_SEMANTIC_REVIEW_2026-10-18.md) | Accepted helper control flow; review counterexamples; code-recovery and runtime-data limits. |
| [Peer-lookup correction](HELPER_NATIVE_RSYNC_PEER_FIX_2026-10-18.md), [diagnostic-assertion correction](HELPER_NATIVE_DIAGNOSTIC_ASSERTION_FIX_2026-10-18.md) and [independent portability review](HELPER_TEST_HARNESS_PORTABILITY_REVIEW_2026-10-18.md) | Two native test-only corrections, retained failed runs and final source identity. |

## Final source identity

| File | Bytes | SHA256 |
|---|---:|---|
| [Candidate helper](candidate/scripts/deploy_code_to_vps.sh.txt) | 20,370 | `1ebfd44db982d73f7f9d507109fa3983ba65cc948e8afe9fe697589d712728a8` |
| [Candidate tests](candidate/tests/test_deploy_provenance.py.txt) | 40,060 | `1e463a9116fb6c9bc6e6fe10ea23bf619d8674fd7e0ad6ce2392410e302a897c` |

The helper hash is unchanged across both native portability corrections. The peer fix changes only the confined fixture's local rsync peer lookup. The last correction removes one GNU-specific diagnostic assertion; the exact filesystem, service, restart-history and helper-owned failure assertions remain. “All test ASTs unchanged” applies to the earlier peer-fix stage, with this one-assertion exception in the final successor.

## Evidence progression — do not combine different source versions

| Stage | Retained result and attribution |
|---|---|
| [Original red baseline](HELPER_RED_BASELINE_2026-10-18.json) | **Six failed controls** against supplied helper `c158fc90…`: copying with the service active; incomplete receiver-tree rollback; masked snapshot failure; misleading restored-health completion; deletion of an unowned marker; and rewind of excluded nested data. Exact executable fixture source is retained in `red_baseline/`. |
| [Active-cohort review reds](HELPER_ACTIVE_COHORT_REVIEW_RED_2026-10-18.json) and [silent-scan review red](HELPER_RECEIPT_SCAN_REVIEW_RED_2026-10-18.json) | **Three further failures** against helper `c64b940d…`: account mutation and fills mutation with an unchanged active marker could be called complete; silent failed receipt enumeration could admit deployment. `review_red_baseline/` preserves that pair. |
| [Pre-native full standalone run](HELPER_CANDIDATE_REVIEWED_VERIFICATION_2026-10-18.json) | **44/44 passed**, using the [standard-library fixture driver](helper_fixture_driver_20261018.py.txt), local rsync 3.2.7 and controlled transport; no app imports and no pytest execution. Exact helper hash is the final helper above; exact test hash is `a4ed6d45ed39eec1aa92ac9d4aeb82219dcefc60e9632e7f27dd8b00f6bfb42a`. This result does not apply to either later test hash. `pre_native_candidate/` preserves its pair and manifest. |
| [Native run 1](native/rr-helper-native-pytest-receipt-20261018.json), 07:41:55–07:42:25 UTC | **Failed, exit 1**, at the pre-native test hash: Apple's local rsync peer re-entered the shim; a separate local Macro vendor dependency was absent. The failures remain evidence, not passed helper behavior. |
| [Native run 2](native/rr-helper-native-pytest-receipt-20261018-run2.json), 07:47:42–07:49:27 UTC | **48 passed / 1 failed; zero errors or skips**, at test `d9dd66255444a70ba2160d30a2b62e540bcbc6620736030152cbef50c7ab7f59`. Only the GNU-specific diagnostic assertion failed; substantive excluded-cache outcomes were observed. `native_run2_candidate/` preserves the pair and manifest. |
| [Final native run 3](native/rr-helper-native-pytest-receipt-20261018-run3.json), 07:52:15.082963–07:54:37.180544 UTC | **49 passed; zero failures, errors or skips**, at the exact final pair above, with Apple openrsync and Python 3.14.7. This is the owning pytest run and includes all five application cases. |

Native results above are supplied by the native owner. Their retained log identities are: run 1, 91,721 bytes, SHA256 `fcf4e967a0890eba39bddf6114b987de3d28a0a112425049deb5b7ce4dd96396`; run 2, 7,482 bytes, SHA256 `c0986b80026beec6fae1e14c58ce6d3c92700317dbb33ef193fde9b3dc65bb09`; final run 3, 5,364 bytes, SHA256 `600984428ed7a81e2051270bd8e3bfbcf4ed9d6c9b02e1f85a5ac5b5d0125299`. Earlier intermediate receipts and manifests remain historical artifacts.

The packet includes [run 2 JUnit](native/rr-helper-native-pytest-20261018-run2.xml), [run 3 JUnit](native/rr-helper-native-pytest-20261018-run3.xml), the [Macro dependency binding](native/rr-helper-native-macro-dependency-20261018.json), [source PR receipt](native/rr-helper-source-pr-20261018.json) and [08:03 source PR/CI observation](native/rr-helper-source-pr-state-20261018.json). Raw logs remain native; their hashes are recorded in the receipts. These are dated observations, distinct from final source or production acceptance. The initial index recorded source CI in progress; its later failed result is retained separately above. Queue and landing still require their own exact receipts.

## What the passing source result means

The helper verifies the configured service is stopped before source mutation or restore; snapshots and restores the full eligible receiver tree with identical exclusion rules and checksum verification; refuses incomplete snapshots/restores; preserves cohort and runtime bytes; and distinguishes verified code recovery from unresolved authority state. This supports the existing active historical cohort, which began on 11 August; it does not reset that cohort or create a second lifecycle owner.

**The excluded-cache availability case remains deliberately fail-closed.** The [retained control](HELPER_EXCLUDED_CACHE_REVIEW_CONTROL_2026-10-18.json) introduces a package whose startup creates an excluded cache. Restore removes included new source and retains protected cache bytes, but the nonempty introduced parent prevents exact restoration. The helper reports incomplete recovery and leaves the service stopped. A passing test of this refusal is not successful availability recovery.

**There is no full runtime recovery claim.** Code rollback does not undo target-start effects in accounts, fills, regional books, queues, journals, settlements or forward snapshots. A configured-unit stop does not prove every external writer is absent; the cooperating US book lock does not serialize every writer or competing deployer. Complete first-init/pending atomicity, arbitrary transport or host loss, every path-type permutation and end-to-end consumer acceptance remain outside this slice. The source PR, CI, queue, landing and production decisions continue through their existing owners.

## Publication normalization

The staged-file check found two trailing-space Markdown hard breaks in the settlement dependency notes. The [normalization receipt](PUBLICATION_NORMALIZATION_2026-10-18.json) records removal of exactly four space bytes from that published note. Its complete original UTF-8 text and accepted SHA256 are retained in the [original-text record](source/SETTLEMENT_DEPENDENCY_STATIC_NOTES_ORIGINAL_2026-10-18.json). At that earlier publication stage, 55 original files remained byte-identical and the final original was exactly recoverable from that record. After the separately recorded hyperlink corrections, 52 of the original 56 files remain byte-identical (including the raw source copies under their mapped archive names); three link-corrected document originals are exactly recoverable from the [link-repair original-text record](PUBLICATION_LINK_REPAIR_ORIGINALS_2026-10-18.json), and the settlement-note original remains recoverable from its own record. No substantive review text, candidate helper or test changed.
