# PR8711 refreshed-candidate independent CI evidence review

**The new exact-source CI run concluded successfully, and its complete semantic evidence reconciles independently against the actual tested source.** The frozen disposition is `CONCLUDED_RUN_PASS__COMPLETE_ALL_PASS_SEMANTIC_RECONCILIATION_VALID`. This is a CI evidence conclusion; the principal retains canonical release adjudication, current freshness/holds, expected-head merge, accepted-source verification and the native C01 witness.

Observation completed: **2026-10-09T14:16:52.263323+00:00**. Reviewer: `/root/ci_release_evidence`. The complete machine-readable record is `CI_EVIDENCE_VERIFICATION.json`, with **2,302 assertions passed**. Source was read as bytes, YAML data and AST; no repository application was imported or tested by this observer.

## Exact candidate, tested merge and plan

| Binding | Actual observed value |
|---|---|
| Candidate | `693ee939c8a28920ef9de7bc32a9f47a7ba76b82` |
| Candidate’s sole parent | `1a1f4a2db62afd5d943a86a391e104f9dad560a1` |
| Normal integration’s ordered parents | `42174563149254d2399e23e101baafd8b06f9b1e`, then `3bb1ee47939d9caa1db10a4e764365d3a2ee5b77` |
| Run / attempt / event | `37938576895` / `1` / `pull_request` |
| Actual tested synthetic commit | `7d5fd7428fa91567db755117657f856e1347c5f9` |
| Tested commit’s ordered first parent | `3bb1ee47939d9caa1db10a4e764365d3a2ee5b77` |
| Tested commit’s ordered second parent | `693ee939c8a28920ef9de7bc32a9f47a7ba76b82` |
| Distinct Git tree object | `67c6a12f7b91e45b63614819a732753fa4a7599a` |
| Plan logical SHA-256 | `5545065ee276bfda077d80ab6ce243eff0142223066378eb3ed2d36ccd05d0e0` |
| Changed-path canonical SHA-256 | `8300e2c6dc44f2afd29c6a011a5f1d6daa272bd79959a0904fe47e8e416a2cdd` |
| Actual merged manifest Git blob | `07a8f2eb51f852e4da38142b00d862473889adcc` |
| Hosted run status / conclusion | `completed` / `success` |

The actual retained plan and immutable tested commit agree on base `3bb1ee4` and candidate `693ee939`. Actual hosted checkout logs bind their executed commit to the same synthetic merge. The workflow field named `tested_tree_sha` contains a commit SHA; this review records the distinct Git tree object separately.

Primary references: [PR8711](https://github.com/mastermindx-market-intelligence/macro/pull/8711), [exact run](https://github.com/mastermindx-market-intelligence/macro/actions/runs/37938576895), [candidate](https://github.com/mastermindx-market-intelligence/macro/commit/693ee939c8a28920ef9de7bc32a9f47a7ba76b82), [tested merge](https://github.com/mastermindx-market-intelligence/macro/commit/7d5fd7428fa91567db755117657f856e1347c5f9), [actual merged manifest](https://github.com/mastermindx-market-intelligence/macro/blob/7d5fd7428fa91567db755117657f856e1347c5f9/.github/ci/legacy-jobs.yml), and [accepted upstream commit](https://github.com/mastermindx-market-intelligence/macro/commit/3bb1ee47939d9caa1db10a4e764365d3a2ee5b77). Retained receipts enumerate the exact GET endpoints, Git object identifiers and byte hashes.

## Complete accounting

| Evidence dimension | Observed | Exact denominator |
|---|---:|---:|
| Original artifact ZIPs and exact JSON members | 15 | 15 |
| Raw pack fragments | 12 | 12 |
| Selected logical jobs represented | 98 | 98 |
| Proof steps represented | 316 | 316 |
| Selected code jobs | 98 | 182 code jobs |
| Explicitly excluded code jobs | 84 | 182 code jobs |
| Other manifest gate jobs | 72 | 254 total manifest jobs |
| Changed paths in this plan | 137 | 137 |
| Accepted engine/lib byte pins | 53 | 53 |

All **316 observed proof steps passed**. No planned pack, job, step or final artifact is missing. The 254 manifest jobs are not a test-pass denominator. The full 98-job selected inventory and 84-job excluded inventory exhaust the 182 code jobs. Q07 is present but explicitly excluded; this packet does not claim it ran.

The verifier recomputes all **98 execution-context digests** and **316 planned step specification digests** from the actual merged source. It checks exact plan, run, head, base and source bindings; complete selected/excluded and pack partitions; unique fragment jobs/steps; proof order; outcomes; and the final aggregate. It does not rerun the scope-selection planner or infer semantic success from job names.

| Pack | Hosted job ID | Hosted conclusion | Logical jobs | Proof steps |
|---:|---:|---|---:|---:|
| 0 | 113848538208 | success | 1 | 16 |
| 1 | 113848538235 | success | 1 | 1 |
| 2 | 113848538309 | success | 5 | 7 |
| 3 | 113848538142 | success | 10 | 44 |
| 4 | 113848538308 | success | 10 | 38 |
| 5 | 113848538282 | success | 10 | 40 |
| 6 | 113848538221 | success | 11 | 34 |
| 7 | 113848538411 | success | 10 | 25 |
| 8 | 113848538234 | success | 10 | 18 |
| 9 | 113848538209 | success | 10 | 31 |
| 10 | 113848538362 | success | 10 | 37 |
| 11 | 113848538526 | success | 10 | 25 |

The final aggregate is **`clear`**, with **98 jobs**, **316 proof steps**, classification counts **`{"passed": 316}`**, and zero infrastructure findings. Logical evidence SHA-256: **`e9deb074013733053d9552c8ab4f710f44e1cd940e2b30eb1be40fa0c838e913`**. The verifier independently reconstructs the complete all-pass aggregate and compares the whole document. The actual final gate’s full JSON stdout, summary values and clear notices match that retained aggregate.

## Actual new owner and contract results

The relationship owner belongs to **pack 6** in this generation. Its hosted job is **`113848538221`**. The exact logical owner and proof are `company-relationship-candidates` and `File, pinned-source and immutable observation replay contracts`.

```sh
python -m pytest tests/test_company_relationship_candidates.py tests/test_company_pinned_relationship_candidates.py tests/test_company_relationship_review_set.py tests/test_company_relationship_observations.py -q
```

The actual new owner log reports **275 passed in 10.76s**, at line **1257**. Its current raw fragment, exact source command, execution context and step specification are bound to that result. Execution-context SHA-256: `5ff9e1dd799a76ff34ad59e95d95cafbc10cea6c6f4cb58da6922bb28801ff6f`. Step specification SHA-256: `3f346c8660ce1278b5d782982c639324dfa4412faa4856e91d19d822a0481d70`.

The new contract-delta job **`113846810075`** concluded **`success`**. Its actual full log reports **0 introduced and 0 inherited** findings against base `3bb1ee47939d`. That count and the actual `--base` command are verified from the new log. The final `ci-gate` independently enforced the successful semantic and contract results.

| Whole raw log | Hosted job ID | Bytes | SHA-256 |
|---|---:|---:|---|
| contract_delta | 113846810075 | 30,460 | `237cd231e40586f14a83c856547b85492ffa05b5945a20ae1f93cf6ca1650355` |
| owner | 113848538221 | 138,354 | `ed55afa8c73474bed7db07aba596c2f434238b42729a1e0480b6bd59efe77018` |
| ci_gate | 113860832578 | 126,630 | `0b4ad6f2ca2de9974ac94c60e00aec06c7ed1539208becf9526eecf08bea36f8` |

Each whole log is retained unchanged, with exact length/hash and line references. New-run results are not supplied by the earlier candidate’s logs.

## What the source refresh changed

The independently read accepted upstream commit `3bb1ee4` has sole parent `40ebaeb` and exactly **three changed paths**: `.github/ci/legacy-jobs.yml`, `scripts/build_stock_library.py`, and `tests/test_build_stock_library_price_clock.py`. `UPSTREAM_COMMIT_CONFIRMATION.json` binds the complete immutable commit response. This inventory is not a functional review of that upstream change.

The complete actual CI manifests before and after this refresh have **254 jobs**, no added or removed job identifiers, and identical top-level parsed fields. Exactly one existing job definition changes: **`unrun-grading-board`**. Its existing continuity step adds `tests/test_build_stock_library_price_clock.py` to the pytest command. The exact raw diff is retained in `UPSTREAM_MERGED_MANIFEST_DELTA.diff`; both full manifests and both plans are retained for offline structural comparison. The semantic reconciler, pack runner, differential contract checker, workflow and test-discovery source files are all byte-identical across these two generations.

The selected and excluded inventories remain identical, and all **98 execution-context digests remain unchanged**. Exactly one source step specification changes: `board ledger row-persistence + same-as_of continuity guard`, now SHA-256 `cfdce80317b9e4e7e15e9cb3c94f015ff0a081b8789bc8cd985ffa92469eb181`.

The actual new plan nevertheless **changes 51 job-to-pack assignments**. The relationship owner moves from pack 11 to **pack 6**. Its entire job definition, all 71 scope paths, command and proof digests remain unchanged. The verifier uses the new actual placement. `SOURCE_REFRESH_ASSESSMENT.json` fully enumerates the placement changes and the single changed source specification. An initial preparation assertion that placement was unchanged stopped before creating a report; the exact preparation source and refusal are preserved in `PREPARATION_OBSERVATIONS.json`. This was an observer preparation correction, not a hosted CI failure, and no result was attributed to the wrong owner pack.

The separate source verifier makes fresh GET reads of **three complete Git trees and 52 unique blobs** at the actual tested tree. All **53 accepted engine/lib paths**, totaling **1,483,905 bytes**, match the accepted reference pins. Every raw tree/blob API response and exact source byte sequence is losslessly retained in `tested_source_pin_read_001.json`. The accepted reference manifest remains checkpoint `6b58f15adae3b1d402d9993c52609d00083f1453`; its historical preservation in later reviews does not change that reference revision.

This establishes byte compatibility for the 53 named paths. It does not create a new functional code review or independently certify the other 18 owner scope paths. The principal’s broader 71-input and research-path preservation judgment is retained as attributed provenance.

| Exact actual CI source preserved as data | Bytes | SHA-256 |
|---|---:|---|
| `sources/merged_legacy_jobs.yml` | 1,249,132 | `e76d0e54e8401c56016447e8542c750fae02e78c7f160943b1d6a986b8a979aa` |
| `sources/scripts/ci_semantic_proof.py` | 73,298 | `9df4b9a9a8d68f7e9aa34a8eebe99e8d17e27f2ef0560eadcc050f3130359158` |
| `sources/scripts/run_ci_pack.py` | 223,426 | `65564916a55eb806d3d9fb0cd4e12726f05fec953f6e47ccd9240f5a141049df` |
| `sources/scripts/check_contract_delta.py` | 62,554 | `894f4e66dd323d5b17be2fe570bfd2fcb8456f92404d464a65b5b16f5c6a278f` |
| `sources/.github/workflows/ci.yml` | 318,629 | `ef9cd98724e4c545e4cb55420d0a6e5c9fc36b9d4efde449416b560cd8d255a9` |
| `sources/scripts/audit_unrun_tests.py` | 50,447 | `e50ba44cb678761d55f1c5bb9828390bd7c21c1672760d6f52781ca194dd7d47` |

## Preserved successful history and principal release boundary

The previous corrected candidate `4217456` obtained its own complete successful proof in run `37932039980`, tested at `04b708` on base `40ebaeb`. A later principal freshness check refused release after accepted main `3bb1ee4` changed CI definitions. The successful historical proof remains successful; that later freshness ruling does not rewrite its result. The principal applied an ordinary main integration and published this new evidence-only candidate for its own naturally triggered CI.

This observer independently checked the new candidate’s sole integration parent and that integration’s ordered parents. The evidence-only commit is exactly one commit ahead of the integration and changes **13 paths**, all in the existing `continuation_pro_003` research directory. The previous frozen successful packet’s **90 original manifest members** remain byte-identical. Its archive, manifest, verification, README and readable report match the actual Git blobs carried by this candidate; `PRIOR_SUCCESS_PACKET_PRESERVATION.json` records those checks. The prior archive was not replayed, rewritten or used as new execution proof.

The exact committed `CI_REFRESH_ADJUDICATION_002.md` and `CI_REFRESH_CHECKPOINT_MANIFEST_002.json` were independently read at the candidate and retained under `principal_context/`. They identify the prior canonical freshness refusal, normal integration and owner-preserving intent. They are principal-authored provenance, not this observer’s independent present-tense release ruling. Root retains the final protected procedure, source/hold/review and baseline checks, expected-head merge and fresh-store postmerge C01 witness.

## Complete artifact byte inventory

Every artifact below was downloaded through its actual artifact GET endpoint. Original ZIP length and SHA-256 match the API inventory. Each ZIP contains exactly one safe regular JSON member; duplicate names, links, traversal and malformed member shapes are refused. All available artifacts equal the exact selected snapshot inventory. Full member hashes, CRCs, logical jobs, proof steps and source bindings are enumerated in `ARTIFACT_INVENTORY.json` and the full verifier record.

| Artifact ID | Artifact name | ZIP bytes | ZIP SHA-256 |
|---:|---|---:|---|
| 11620333849 | `ci-semantic-pack-37938576895-9` | 3,371 | `3e6e6e3bdf909744eb1e20794bd90317727f947f3419406045cc19fa6207d34e` |
| 11620413426 | `ci-semantic-pack-37938576895-10` | 3,810 | `d53e4fdd73b23f3c51ad918f2d052b0c9ab2ab47169a25dd897bbd1aa29c283b` |
| 11620418039 | `ci-semantic-pack-37938576895-4` | 4,140 | `8adbf7b460ac09d93908553e31874d5f275fb00dcc1b980b768edddfb985b5f3` |
| 11620508520 | `ci-semantic-pack-37938576895-7` | 2,955 | `e4b46d722e8fd0fe18c1cd950a65864a4f5b2a694e7a6133a1fb76b373cc109f` |
| 11620707841 | `ci-semantic-pack-37938576895-2` | 1,306 | `a3d8b54ec7e1aa3e5addc13a1e17b37f6d45c5e674964a7f3bcff9856d2632bf` |
| 11620718788 | `ci-semantic-pack-37938576895-6` | 3,606 | `3e707edd8a8e0b04a81b6b841b7f9cc54ea905a140f894aa792daaa883c0076d` |
| 11620758250 | `ci-semantic-pack-37938576895-8` | 2,447 | `86140f659ab11c467b5154f5c7c76f548e74064c4f9c1c9dc54397340dd12792` |
| 11621065219 | `ci-semantic-plan-37938576895-1` | 30,405 | `6fb05af6642d7dab3533beb41591b7adc9a4e41f665356e691ac566b2b46ecf3` |
| 11621160171 | `ci-changed-files` | 2,057 | `a65dad40c7aecb9b018f5ed7adbd74a49467cd2428f2eaffd26983ed661d85b5` |
| 11621257725 | `ci-semantic-pack-37938576895-11` | 2,972 | `101dd7f20e5ad0f895d6accc90d3f4f3238dd48764827af576a6e81fce5fa284` |
| 11621407074 | `ci-semantic-pack-37938576895-1` | 645 | `dd5d24d90a43218e64a8d93057f9bf39743fd065e3255a24c0b717a2666f60f6` |
| 11621492367 | `ci-semantic-pack-37938576895-3` | 4,359 | `2f077c58a3fb55107743ad2caf9bead3a2027278bdf281b98f44805e5b382d0a` |
| 11621792266 | `ci-semantic-pack-37938576895-0` | 1,595 | `4acc782d983303a0b459316a5b3aee68034f0bd7e1df1adb87c663e6bc181da5` |
| 11621921191 | `ci-semantic-pack-37938576895-5` | 4,222 | `82e1bcfc30caf3328110c432a742c22c01bb269cf38a3566f820428022d380eb` |
| 11622770817 | `ci-semantic-evidence-37938576895` | 27,788 | `34998f2b20c4e840175d7965009e756c2927d9aa5bfd25b62739699f86203ae7` |

## Exact-head checks and native process accounting

The complete census contains **27 exact-head checks**. Actual non-success states remain visible. The principal’s committed adjudication describes the inactive pilot context under the existing helper; this observer does not waive a check or adjudicate its current policy binding.

| Check | Check ID | Status | Conclusion |
|---|---:|---|---|
| `ci-gate` | 113860832578 | completed | success |
| `ci-authority/main` | 113849447119 | completed | success |
| `ci-authority/codex/merge-queue-pilot` | 113849444088 | completed | failure |
| `ci-authority` | 113849377966 | completed | success |
| `trusted-ci` | 113848539758 | completed | skipped |
| `ci-pack-11` | 113848538526 | completed | success |
| `ci-pack-7` | 113848538411 | completed | success |
| `ci-pack-10` | 113848538362 | completed | success |
| `ci-pack-2` | 113848538309 | completed | success |
| `ci-pack-4` | 113848538308 | completed | success |
| `ci-pack-5` | 113848538282 | completed | success |
| `ci-pack-1` | 113848538235 | completed | success |
| `ci-pack-8` | 113848538234 | completed | success |
| `ci-pack-6` | 113848538221 | completed | success |
| `ci-pack-9` | 113848538209 | completed | success |
| `ci-pack-0` | 113848538208 | completed | success |
| `ci-pack-3` | 113848538142 | completed | success |
| `grader-manifest` | 113847140993 | completed | success |
| `capability-broker` | 113847137408 | completed | success |
| `self-mod-fence` | 113847133529 | completed | success |
| `github.event_name == 'pull_request' && github.event.pull_request.head.repo.full_name != github.repository && 'capability-broker' \|\| 'fork-capability-broker-unused'` | 113846843948 | completed | skipped |
| `contract-delta` | 113846810075 | completed | success |
| `ci-plan` | 113846809854 | completed | success |
| `github.event_name == 'pull_request' && github.event.pull_request.head.repo.full_name != github.repository && 'self-mod-fence' \|\| 'fork-self-mod-fence-unused'` | 113846809679 | completed | skipped |
| `github.event_name == 'pull_request' && github.event.pull_request.head.repo.full_name != github.repository && 'grader-manifest' \|\| 'fork-grader-manifest-unused'` | 113846809391 | completed | skipped |
| `fence-pack` | 113846807728 | completed | success |
| `ci-authority` | 113846798223 | completed | success |

All **7** managed native GET processes completed and were reconciled. The exact scripts, purposes, completion footers and capture references are preserved in `native_read_scripts.json`.

| Native PID | Purpose | Exit code | Runtime seconds |
|---:|---|---:|---:|
| 34599 | Exact new candidate, integration ancestry and naturally triggered run discovery | 0 | 4.39 |
| 39224 | Actual tested merge, six CI-law sources, plan/changed artifacts and evidence-only commit comparison | 0 | 15.39 |
| 45345 | Fresh actual tested trees and source blobs proving 53 accepted byte pins | 0 | 8.12 |
| 57415 | New packs 1, 2 and 4, whole contract log and principal refresh context | 0 | 11.5 |
| 76190 | Eight additional packs, whole actual owner pack 6 log and accepted upstream commit | 0 | 19.58 |
| 90683 | Bounded metadata snapshot while pack 5 remained running; no new artifact or log body | 0 | 4.59 |
| 4438 | Concluded run metadata, pack 5, final semantic aggregate and whole final gate log | 0 | 9.68 |

## Offline reproduction and limits

`VERIFIER_DERIVATION.json`, `CI_VERIFIER_REVISION.diff` and `SOURCE_PIN_VERIFIER_REVISION.diff` preserve the exact verifier lineage. Core ZIP/member, plan/source/step, full-log, aggregate and Git-object validation algorithms are reused. Changes bind the new generation’s actual identities, 137 paths, pack-6 owner, structural refresh and provenance. The previous verifier bytes remain exact under `verifier_origin/`.

The archive includes all actual artifacts and whole new logs, source/object bytes, structural comparison inputs, captures, inventories, reports and bounded scripts. It has an external regular-file-only manifest with every relative name, length and SHA-256. Safe extraction and unchanged verifier replays are recorded separately in the archive verification receipt. With Python 3 and PyYAML, use fresh output names from the extracted evidence directory:

```sh
PYTHONDONTWRITEBYTECODE=1 python -B assess_source_refresh.py --output FRESH_SOURCE_REFRESH_ASSESSMENT.json
PYTHONDONTWRITEBYTECODE=1 python -B verify_tested_code_pins.py --output FRESH_SOURCE_PIN_VERIFICATION.json
PYTHONDONTWRITEBYTECODE=1 python -B verify_refreshed_artifacts.py --snapshot artifact_read_005_and_snapshot_005.json --output FRESH_CI_EVIDENCE_VERIFICATION.json
```

These read preserved evidence without Git, network, native operations, application imports or application tests. `PACKAGING_NOTES.md` distinguishes exact raw artifact/source/log retention from decoded API metadata, and documents source-capture transport framing and the preparation correction.

This packet supplies no current main freshness or live-hold certification, merge authorization, policy waiver, source-rights permission, custody/authorship guarantee, historical availability, factual admission, Graph1 admission, production acceptance or predictive promotion. Functional code review and the actual accepted-source native C01 proof retain their existing owners.
