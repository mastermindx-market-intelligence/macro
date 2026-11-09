# PR8711 refreshed candidate v2: independent CI evidence

**The exact new-source CI run concluded successfully. All planned semantic evidence independently reconciles against the actual tested source.** The frozen disposition is `CONCLUDED_RUN_PASS__COMPLETE_ALL_PASS_SEMANTIC_RECONCILIATION_VALID`. This is a bounded CI evidence conclusion. The principal retains canonical release adjudication, current freshness and holds, expected-head merge, accepted-source comparison and the actual native C01 witness.

Observation completed: **2026-10-09T15:35:07.916014+00:00**. Reviewer: `/root/ci_release_evidence`. The complete machine-readable record is `CI_EVIDENCE_VERIFICATION.json`, with **2,320 assertions passed**. This observer read repository source as bytes, YAML and AST. It did not import or test a repository application.

## Exact candidate, actual tested merge and plan

| Binding | Actual observed value |
|---|---|
| Candidate head | `cbcc5ee143400af162a252e4faac0f06c7157e37` |
| Candidate sole parent | `3521765204903320db76ddd84d6a43539ded8e62` |
| Normal integration first parent | `693ee939c8a28920ef9de7bc32a9f47a7ba76b82` |
| Normal integration second parent | `87b01101ef13aa20ded205f3a2b267b68d094def` |
| Run / attempt / event | `37949036732` / `1` / `pull_request` |
| Actual tested synthetic commit | `ecd49338799e419055737a20f3fb462c4b97bdd8` |
| Tested commit ordered first parent | `6ced30b9d69f7e5644d74f1f4648def0ac357c42` |
| Tested commit ordered second parent | `cbcc5ee143400af162a252e4faac0f06c7157e37` |
| Distinct actual Git tree object | `cbf9097804ffa9e094ec700bfc8a044e8ed7ee8d` |
| Plan logical SHA-256 | `40fcf0771c17114af3dd85f03a81bd2c81b55d463fcf4feeda816b073bfff5f9` |
| Changed-path canonical SHA-256 | `26766bdbca14f10ef37706adecacb586f65e183ffdd62fe1b54eb435c4fac747` |
| Actual tested manifest Git blob | `2265e5ccc3d408d6679bdfba5ac22ab959aaaccf` |
| Hosted run status / conclusion | `completed` / `success` |

The retained actual plan, immutable tested commit and hosted checkout logs independently bind this run to **base `6ced30` and candidate `cbcc5ee`**. The earlier integrated upstream is `87b01101`; the initial PR metadata base field also reported `87b01101`. Those values are retained separately and are not substituted for the actual tested first parent. The workflow field named `tested_tree_sha` holds a commit SHA; this review records the distinct Git tree object separately.

Primary references: [PR8711](https://github.com/mastermindx-market-intelligence/macro/pull/8711), [exact run](https://github.com/mastermindx-market-intelligence/macro/actions/runs/37949036732), [candidate](https://github.com/mastermindx-market-intelligence/macro/commit/cbcc5ee143400af162a252e4faac0f06c7157e37), [tested merge](https://github.com/mastermindx-market-intelligence/macro/commit/ecd49338799e419055737a20f3fb462c4b97bdd8), [actual tested manifest](https://github.com/mastermindx-market-intelligence/macro/blob/ecd49338799e419055737a20f3fb462c4b97bdd8/.github/ci/legacy-jobs.yml), [actual tested base](https://github.com/mastermindx-market-intelligence/macro/commit/6ced30b9d69f7e5644d74f1f4648def0ac357c42), and [integration upstream](https://github.com/mastermindx-market-intelligence/macro/commit/87b01101ef13aa20ded205f3a2b267b68d094def). Retained capture receipts enumerate actual GET endpoints, Git object identities, lengths and hashes.

## Complete accounting and independent semantic reconciliation

| Evidence dimension | Observed | Exact denominator |
|---|---:|---:|
| Original artifact ZIPs | 15 | 15 |
| Exact original JSON members | 15 | 15 |
| Raw pack fragments | 12 | 12 |
| Selected logical jobs represented | 98 | 98 |
| Proof steps represented | 316 | 316 |
| Selected code jobs | 98 | 182 code jobs |
| Explicitly excluded code jobs | 84 | 182 code jobs |
| Other manifest gate jobs | 72 | 254 total manifest jobs |
| Changed paths in this plan | 158 | 158 |
| Accepted engine/lib byte pins | 53 | 53 |
| Enrolled owner-file byte identities bound to actual tested tree | 71 | 71 |

All **316 observed proof steps passed**. No planned pack, job, step, final aggregate or required actual owner/contract/final-gate log is missing. The 254 manifest jobs are not a test-pass denominator. The full 98-job selected and 84-job excluded inventories exhaust the 182 code jobs. Q07 is present and explicitly excluded; this packet does not claim that it ran.

The verifier recomputes all **98 execution-context digests** and **316 planned step specification digests** from actual tested source. It checks complete plan and changed-path digests, run/head/base/source bindings, selected/excluded and pack partitions, unique fragment jobs and ordered proof steps, outcomes and final aggregate. It does not rerun the scope-selection planner or infer semantic success from hosted job names.

| Pack | Hosted job ID | Hosted conclusion | Logical jobs | Proof steps |
|---:|---:|---|---:|---:|
| 0 | 113884343844 | success | 1 | 16 |
| 1 | 113884343525 | success | 1 | 1 |
| 2 | 113884343603 | success | 5 | 7 |
| 3 | 113884343579 | success | 10 | 44 |
| 4 | 113884343584 | success | 10 | 38 |
| 5 | 113884343545 | success | 10 | 40 |
| 6 | 113884343629 | success | 11 | 34 |
| 7 | 113884343692 | success | 10 | 25 |
| 8 | 113884343699 | success | 10 | 18 |
| 9 | 113884343585 | success | 10 | 31 |
| 10 | 113884343625 | success | 10 | 37 |
| 11 | 113884343581 | success | 10 | 25 |

The final aggregate is **`clear`**, with **98 jobs**, **316 proof steps**, classification counts **`{"passed": 316}`**, and zero infrastructure findings. Its logical evidence SHA-256 is **`3d1bea93bf510a2f60989ed8d13a70699fb6c67d46f107a21c9970a150fc7cc8`**. The verifier independently reconstructs the complete all-pass aggregate and compares the whole document. Actual final-gate JSON stdout, summary values and clear notices match the retained aggregate. This all-pass reconstruction makes no claim to validate a hypothetical non-all-pass aggregate.

## Actual current owner and differential contract results

The actual new plan places `company-relationship-candidates` in **pack 6**, hosted job **113884343629**. The logical proof is `File, pinned-source and immutable observation replay contracts`.

```sh
python -m pytest tests/test_company_relationship_candidates.py tests/test_company_pinned_relationship_candidates.py tests/test_company_relationship_review_set.py tests/test_company_relationship_observations.py -q
```

The actual current owner log reports **275 passed in 10.84s**, at line **1260**. Its entire result group, whole raw log, source command, execution context and step specification bind to the current fragment and actual tested commit. Execution-context SHA-256: `5ff9e1dd799a76ff34ad59e95d95cafbc10cea6c6f4cb58da6922bb28801ff6f`. Step specification SHA-256: `3f346c8660ce1278b5d782982c639324dfa4412faa4856e91d19d822a0481d70`.

The current contract-delta job **113882722976** concluded **success**. Its actual full log reports **0 introduced and 0 inherited** findings against base `6ced30b9d69f`, at line **382**. The actual `--base` command, checkout and counts are verified from this run. No error line is observed in that complete contract log. The actual final CI gate enforced the current semantic and contract results.

| Whole raw log | Hosted job ID | Bytes | SHA-256 |
|---|---:|---:|---|
| contract_delta | 113882722976 | 30,533 | `8065b6022c5e5e134792c6d8b9c2dcc7641d8f9082150b2723a9db4839ecbc1d` |
| owner | 113884343629 | 138,540 | `48dfa7431695516aeedc30935266dfc5a8882d7e1f7bebf4ea43dfd3c1763dbc` |
| ci_gate | 113894386902 | 126,616 | `881035df939b9decf83cdf9f34fcb0f2201712b505e64c564b1489b6b114b5e5` |

The complete new log bodies are retained unchanged. Earlier runs' owner timings, fragments and gate results do not provide current-head execution evidence.

## What the normal source refresh changed

The independently verified normal integration commit `35217652` has ordered parents `693ee939` then `87b01101`. The candidate adds **22 evidence-only paths** under the principal continuation directory relative to that integration. Actual local raw Git tree comparison and current immutable GitHub commit comparison both retain the complete 22-path inventory.

Before publication completed, this observer read **137 immutable local Git objects**, totaling **8,685,410 raw bytes**, and verified **230 resolved source bindings**. All **71 enrolled owner files** were byte-identical at the previous candidate, normal integration and new candidate. All **53 accepted application pins**, the canonical observation suite, the owner definition and the **253 other accepted job definitions and top-level fields** were preserved against the integrated upstream. The local proof passed **970 assertions**. Its original status, `LOCAL_COMMITTED_SOURCE_RECONCILIATION_PASS__REMOTE_AND_CI_NOT_OBSERVED`, remains frozen and accurate for that observation time. Later publication and actual CI identity are established by separate captures.

The verified accepted-upstream range contains **13 commits after `3bb1ee4`**. The CI-definition commit is `ff652de571523466dea4d4d7f9644022198c3465`, with sole parent `aee2725637d9fa66dd75ea24c4b2693b8bcf3a85`. Its sole parsed CI manifest effect is one scope insertion into each of six existing jobs:

| Existing logical job | Added scope path |
|---|---|
| `biocatalyst-history` | `engine/risk_envelope.py` |
| `conviction-profile` | `engine/risk_envelope.py` |
| `flow-surface` | `engine/risk_envelope.py` |
| `ticker-news-qbus` | `engine/risk_envelope.py` |
| `unrun-government-revenue-candidate-projection` | `engine/risk_envelope.py` |
| `unrun-government-revenue-grader` | `engine/risk_envelope.py` |

All prior scope paths preserve their order. There are **no command, job-ID or non-path-field changes** in that CI-definition comparison. Three complete comparisons independently establish the same six changes: the definition commit's parent to that commit, prior main `3bb1ee4` to integrated upstream `87b01101`, and prior candidate `693ee939` to current candidate `cbcc5ee`. The actual tested `ecd493` manifest is byte-identical to the current candidate's manifest. This bounded comparison is not a functional review of unrelated accepted upstream changes.

The complete current and previous manifests each have **254 jobs**. All selected/excluded inventories, **98 job execution-context digests**, **316 proof specifications**, and **all pack assignments** are identical across these actual plans. The current owner pack 6 was independently read from the new plan. No historical placement was assumed. The actual semantic reconciler, pack runner, differential contract checker, workflow and discovery law files are all byte-identical to their previously verified pins.

## Actual tested source and owner-file binding

A separate fresh GET capture retained **three complete Git trees and 52 unique Git blobs** from the actual tested tree. All **53 accepted engine/lib files**, totaling **1,483,905 bytes**, match their accepted reference pins. Raw tree/blob API response bytes and actual source byte sequences are retained losslessly. The accepted reference manifest remains checkpoint `6b58f15adae3b1d402d9993c52609d00083f1453`.

A second independent preserved-data proof binds **all 71 enrolled owner-file byte identities**, totaling **2,152,680 bytes**, to the actual tested Git tree. It reconstructs the actual GitHub root tree in Git's binary representation and verifies its object hash, then verifies the seven shared owner-subtree identities and traverses **85 already-retained local Git objects** to each enrolled file. This extends the actual tested-tree binding to the other 18 owner inputs without claiming 18 additional fresh GitHub blob downloads. The canonical observation test SHA-256 remains `a73700e639c8e97a4ff84951b48358abe63b1f5048560d03b0e40f2310ac44da`.

These proofs establish named byte identities and actual tested-tree reachability. They do not create a new functional code review, source authorship guarantee, rights decision or native accepted-source witness. The two mechanisms and full inventories are recorded separately.

| Exact actual CI source preserved as data | Bytes | SHA-256 |
|---|---:|---|
| `sources/merged_legacy_jobs.yml` | 1,249,336 | `5cc24c46e7c4ed8b0b9525366a7069e86f546b32849c72cb8518320842d860cd` |
| `sources/scripts/ci_semantic_proof.py` | 73,298 | `9df4b9a9a8d68f7e9aa34a8eebe99e8d17e27f2ef0560eadcc050f3130359158` |
| `sources/scripts/run_ci_pack.py` | 223,426 | `65564916a55eb806d3d9fb0cd4e12726f05fec953f6e47ccd9240f5a141049df` |
| `sources/scripts/check_contract_delta.py` | 62,554 | `894f4e66dd323d5b17be2fe570bfd2fcb8456f92404d464a65b5b16f5c6a278f` |
| `sources/.github/workflows/ci.yml` | 318,629 | `ef9cd98724e4c545e4cb55420d0a6e5c9fc36b9d4efde449416b560cd8d255a9` |
| `sources/scripts/audit_unrun_tests.py` | 50,447 | `e50ba44cb678761d55f1c5bb9828390bd7c21c1672760d6f52781ca194dd7d47` |

## Historical proof, publication and canonical release boundary

The previous `693ee939` candidate retains its own complete successful run `37938576895`, tested at `7d5fd742` on base `3bb1ee4`. Its **98-file frozen packet** remains unchanged. This generation checked the current committed Git-blob identity and exact unchanged scratch bytes of the five transferred archive/report objects. The old archive was not replayed, rewritten or nested inside this archive.

The actual committed principal `CI_REFRESH_ADJUDICATION_004.md` and checkpoint manifest were read in full and retained. They attribute gate002's refusal to a stale protected Mastermind source pin, the atomic source reconciliation to `8d838c8d` with INDEX1.0.1 and ten unchanged companion blobs, and gate003's refusal to new `ff652` CI-definition freshness. Those refusals did not invalidate the earlier complete historical CI proof. The principal records no merge or waiver and then a normal accepted-main integration. These are principal provenance, not this observer's independent ruling on live policy.

This lane's early preparation also preserves the principal's report of the initial normal push failing: PID50875 exit1, missing promisor object with no-lazy-fetch protection retained, and remote still at `693ee939`. The principal subsequently reported ordinary supported publication using command-scoped `push.negotiate=true`, PID30522 exit0, with exact `cbcc5ee` readback. This observer did not operate or independently audit that recovery command; it independently observed the published exact candidate and its natural new run. Native process records below include only this observer's reads.

The current exact-head check census is retained in full:

| Check name | Check ID | Status | Conclusion |
|---|---:|---|---|
| `ci-gate` | 113894386902 | completed | success |
| `trusted-ci` | 113884346079 | completed | skipped |
| `ci-pack-0` | 113884343844 | completed | success |
| `ci-pack-8` | 113884343699 | completed | success |
| `ci-pack-7` | 113884343692 | completed | success |
| `ci-pack-6` | 113884343629 | completed | success |
| `ci-pack-10` | 113884343625 | completed | success |
| `ci-pack-2` | 113884343603 | completed | success |
| `ci-pack-9` | 113884343585 | completed | success |
| `ci-pack-4` | 113884343584 | completed | success |
| `ci-pack-11` | 113884343581 | completed | success |
| `ci-pack-3` | 113884343579 | completed | success |
| `ci-pack-5` | 113884343545 | completed | success |
| `ci-pack-1` | 113884343525 | completed | success |
| `ci-authority/main` | 113883206552 | completed | success |
| `ci-authority/codex/merge-queue-pilot` | 113883201985 | completed | failure |
| `ci-authority` | 113883120713 | completed | success |
| `grader-manifest` | 113883119670 | completed | success |
| `capability-broker` | 113883116744 | completed | success |
| `self-mod-fence` | 113883113323 | completed | success |
| `contract-delta` | 113882722976 | completed | success |
| `ci-plan` | 113882722632 | completed | success |
| `github.event_name == 'pull_request' && github.event.pull_request.head.repo.full_name != github.repository && 'self-mod-fence' \|\| 'fork-self-mod-fence-unused'` | 113882720556 | completed | skipped |
| `github.event_name == 'pull_request' && github.event.pull_request.head.repo.full_name != github.repository && 'capability-broker' \|\| 'fork-capability-broker-unused'` | 113882720220 | completed | skipped |
| `github.event_name == 'pull_request' && github.event.pull_request.head.repo.full_name != github.repository && 'grader-manifest' \|\| 'fork-grader-manifest-unused'` | 113882719693 | completed | skipped |
| `fence-pack` | 113882718223 | completed | success |
| `ci-authority` | 113882707434 | completed | success |

The observed `ci-authority/codex/merge-queue-pilot` failure remains explicit. The observer grants no exclusion or waiver and makes no current required-check policy ruling. Root owns canonical protected-procedure checks, live main freshness and holds. This packet cannot authorize merge on its own.

## Complete retained artifacts, receipts and process reconciliation

| Artifact ID | Exact artifact name | Original ZIP bytes | Original ZIP SHA-256 |
|---:|---|---:|---|
| 11625039562 | `ci-semantic-pack-37949036732-6` | 3,607 | `7d782fe597feab45aac37fc27c7141b4255329effc05327ead837cc5ea9315d2` |
| 11625148341 | `ci-semantic-pack-37949036732-2` | 1,304 | `473d7218924674b68e9ea1724e223b4009f233255a5a9edd88ae13d8857750dc` |
| 11625203083 | `ci-semantic-pack-37949036732-3` | 4,359 | `8fab23b8beca05fb35353a4ed995d49335b01919f496ddff7210addb2b417210` |
| 11625318298 | `ci-semantic-pack-37949036732-10` | 3,811 | `a25b4935466e481bb1dd66ebaada13d94f5d694b3cd4998ead04635cddf6542e` |
| 11625419905 | `ci-semantic-pack-37949036732-0` | 1,593 | `87e5a5fd2f9b13200b87bf05a24676ae6f49194acd1a4a3543f95e4679266077` |
| 11625495919 | `ci-semantic-plan-37949036732-1` | 30,405 | `4f4856c0a32c68b5dee829d17635c426ab0215f48b08a0628e3dd4a57fa29beb` |
| 11625537417 | `ci-semantic-pack-37949036732-4` | 4,138 | `90ee0e04c47c316b342fba5ab16984887ba099934368fa565cb166192d6b46d4` |
| 11625610959 | `ci-changed-files` | 2,249 | `ec2ef76768c2e27099f4bf33dca21eea0481695b996bff9ec33caea42429e61f` |
| 11625693141 | `ci-semantic-pack-37949036732-11` | 2,973 | `e6fb2c18021b859f8f980926e24756d37ae3ab9d07a0b22110af02ba620ca587` |
| 11625788778 | `ci-semantic-pack-37949036732-8` | 2,449 | `4a63f39ea8a84324440411710fd886cfc4d3a7a95dbe87c1600654ba236db567` |
| 11625793301 | `ci-semantic-pack-37949036732-5` | 4,222 | `3a5f8389326ade0502e93cf556cc14ba9380e7a35b03d68e1fdd378b7c421f88` |
| 11626026740 | `ci-semantic-pack-37949036732-7` | 2,952 | `0ffddcea87582cc79257336a08212aa0131120e63e72b01913c571e4bd2443b0` |
| 11626032126 | `ci-semantic-pack-37949036732-9` | 3,371 | `a68b48f6e1458c9de1b38ed8e1d45be47ca069dc08094e0f5960b1fcef33717d` |
| 11626091205 | `ci-semantic-pack-37949036732-1` | 645 | `7df2cdc1f65202fea1c27c93658470eff2097b88d467824cb572e60f77f8ec77` |
| 11626596029 | `ci-semantic-evidence-37949036732` | 27,794 | `624bcbaf0551672266da789e23a3a60832092c47e2530d006d2d73271760978f` |

Every ZIP retains its original byte sequence and its one exact JSON member under `artifacts/<actual-id>/`. ZIP length, SHA-256, API inventory digest, unique member name, CRC, metadata, path/type safety and decoded semantic content are checked. The full artifact and selected/excluded inventories are in `ARTIFACT_INVENTORY.json` and the complete verification JSON.

| Frozen evidence entry point | Bytes | SHA-256 |
|---|---:|---|
| `CI_EVIDENCE_VERIFICATION.json` | 1,001,692 | `28a6cc9176575fc7a49a9b9090406e8636250dc1923b752ed9c3c519cb69f476` |
| `SOURCE_REFRESH_ASSESSMENT.json` | 232,750 | `775f833cce6f1043739d30c8353dca59cf84fa3c9f64cd0bd1ff21c7ebe66562` |
| `SOURCE_PIN_VERIFICATION.json` | 17,457 | `4fa42b3739aa87f8757935b74053d96b19846c0fa7eda24fa4a4c660054deef1` |
| `TESTED_OWNER71_BINDING_VERIFICATION.json` | 33,773 | `b45b31da56f1ff8ca107b3b5f75c71fbc66cf4e2550f9d105070cd5dcd56e640` |
| `LOCAL_CANDIDATE_VERIFICATION.json` | 959,882 | `33b42ab2cbba3d3600455a85b5cacf4a09623b0fb832eb745d73983bbd744ad5` |
| `PRIOR_V1_PACKET_PRESERVATION.json` | 3,283 | `dc86918041413e0a42f3cf6fcb576833eba7fce3d5cdfefe41f0b3c7d9d09543` |
| `principal_context/CI_REFRESH_ADJUDICATION_004.md` | 8,132 | `3208be87ff0bbcb738c2e8847067ea868bea93451c88fe28e262e53391101bcb` |
| `principal_context/CI_REFRESH_CHECKPOINT_MANIFEST_004.json` | 38,345 | `c0529dc603316a7f97e4d468269ca3e04df2ba257ae4db3d85437f987fccb896` |

| Observer-managed native PID | Purpose | Exit | Runtime seconds |
|---:|---|---:|---:|
| 21862 | Immutable local Git object/source/ancestry read; no network | 0 | 6.46 |
| 34605 | Published exact candidate, natural CI run and reported merge discovery | 0 | 4.5 |
| 41069 | Actual plan/changed ZIPs, six CI sources, tested/base commits and 22-path candidate comparison | 0 | 15.84 |
| 43737 | Fresh actual tested three Git trees and 52 unique source blobs for 53 pins | 0 | 8.22 |
| 52407 | Run/job/check/artifact snapshot and two immutable principal004 context sources | 0 | 6.42 |
| 79713 | Eight actual pack ZIPs and complete current contract log | 0 | 18.92 |
| 5392 | Three more actual pack ZIPs and complete current relationship-owner log | 0 | 11.64 |
| 16515 | Concluded exact-run census, final pack0 and aggregate ZIPs, complete current final-gate log | 0 | 9.64 |

All **8 observer-managed native processes completed and were reconciled**. Exact executed scripts and completion receipts are retained in `native_read_scripts.json`. The initial source read used immutable native Git-object reads with lazy fetching and optional locks disabled; all subsequent native acquisition was GitHub GET. This observer performed no native write, Git mutation, CI dispatch/rerun/cancellation, application import/test, policy change or merge.

## Reproducibility and limits

`VERIFIER_DERIVATION.json` and `CI_VERIFIER_REVISION.diff` record the new exact identity, source and provenance bindings. Existing pure ZIP, plan, source digest, raw fragment, full-log and all-pass aggregate verification algorithms were retained. The new verifier additionally binds the current local source reconciliation, distinct integrated upstream and actual tested base, six scope changes, 71-owner Git-object proof, prior 98-file packet transfer objects, and actual current owner-log role.

The completed deterministic archive has a separate regular-file-only manifest, verification receipt and README. It preserves every actual ZIP/member, source capture, raw Git object capture, full selected/excluded inventory, whole log, read script, partial observation and verification report. Five unchanged current-generation preserved-data verifiers are replayed from the extracted layout with fresh filenames:

```sh
PYTHONDONTWRITEBYTECODE=1 python -B verify_local_candidate_objects.py --output FRESH_LOCAL_CANDIDATE_VERIFICATION.json
PYTHONDONTWRITEBYTECODE=1 python -B verify_tested_code_pins.py --output FRESH_SOURCE_PIN_VERIFICATION.json
PYTHONDONTWRITEBYTECODE=1 python -B verify_tested_owner_tree_bindings.py --output FRESH_TESTED_OWNER71_BINDING_VERIFICATION.json
PYTHONDONTWRITEBYTECODE=1 python -B assess_source_refresh.py --output FRESH_SOURCE_REFRESH_ASSESSMENT.json
PYTHONDONTWRITEBYTECODE=1 python -B verify_refreshed_artifacts.py --snapshot artifact_read_005_and_snapshot_005.json --output FRESH_CI_EVIDENCE_VERIFICATION.json
```

These commands read preserved evidence without Git, network, native operations or repository application imports/tests. Final replay uses the final selected snapshot and all retained transfers; historical partial reports retain their own observed denominators and are not relabelled complete.

This packet supplies no live release freshness or hold certification, merge authorization, waiver, source-rights permission, custody/authorship guarantee, historical availability, factual admission, Graph1 admission, production acceptance or predictive promotion. Functional code review, the actual accepted-source native C01 proof and broader research completion retain their existing owners.
