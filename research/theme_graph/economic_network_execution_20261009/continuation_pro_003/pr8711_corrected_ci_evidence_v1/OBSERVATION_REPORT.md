# PR8711 corrected-candidate independent CI evidence review

**The corrected candidate’s observed CI run concluded successfully, and its complete all-pass semantic evidence reconciles independently against the actual tested source.** This is a bounded CI evidence conclusion. It does not authorize merge or replace the principal’s canonical release procedure, current freshness/holds checks, accepted-source review or native C01 witness.

Frozen observation completed: **2026-10-09T13:22:08.722425+00:00**. Reviewer: `/root/ci_release_evidence`. The full machine-readable record is `CI_EVIDENCE_VERIFICATION.json`, with **2,295 assertions passed**. The verifier treats source as bytes, YAML data and AST; it does not import or execute repository application code.

## Exact identity and tested source

| Binding | Observed value |
|---|---|
| Candidate head | `42174563149254d2399e23e101baafd8b06f9b1e` |
| Candidate’s sole parent | `9df735bbeaa8d0f4d4967296270bfb2246a5212f` |
| Run / attempt | `37932039980` / `1` |
| Event | `pull_request` |
| Actual tested synthetic commit | `04b70807e6b0a7d48091997eb405f9cc53ade9ad` |
| Ordered first parent / actual tested base | `40ebaebdbcd57eedaa627623f1cfd1860ff3ee3a` |
| Ordered second parent | `42174563149254d2399e23e101baafd8b06f9b1e` |
| Actual Git tree object | `0c5bd664aec83fe9a9d456b2f35e1e870fc0b3e8` |
| Plan logical SHA-256 | `e637d0f4907e040b1a4069d7c14748fba81137387e83ea6ec255bf0d53c5ce88` |
| Changed-path canonical SHA-256 | `5f2a89d5b23b7b307df3fbfd53bff817d26a7cedac3cf0937006ccc925b34ce4` |
| Merged manifest Git blob | `a5cfd271fe02ad22458cab56cc29e878de8a8fc9` |
| Hosted run status / conclusion | `completed` / `success` |

The PR API’s `base.sha` field lagged at `c4cd21d597521603fb75fe7a4602424e088c6bfa`. It is not the tested base. The immutable synthetic commit’s ordered parents, the actual retained plan, and the actual hosted checkout logs establish `40ebaebdbcd57eedaa627623f1cfd1860ff3ee3a` as the tested base. The workflow’s `tested_tree_sha` field names a commit; the distinct Git tree object is recorded separately above.

Primary references: [PR8711](https://github.com/mastermindx-market-intelligence/macro/pull/8711), [exact run](https://github.com/mastermindx-market-intelligence/macro/actions/runs/37932039980), [tested commit](https://github.com/mastermindx-market-intelligence/macro/commit/04b70807e6b0a7d48091997eb405f9cc53ade9ad), [candidate](https://github.com/mastermindx-market-intelligence/macro/commit/42174563149254d2399e23e101baafd8b06f9b1e), and [actual merged manifest](https://github.com/mastermindx-market-intelligence/macro/blob/04b70807e6b0a7d48091997eb405f9cc53ade9ad/.github/ci/legacy-jobs.yml). Original artifact IDs, GET endpoints and response receipts are enumerated in `ARTIFACT_INVENTORY.json` and the full verifier record.

## Completeness and exact denominators

| Evidence dimension | Observed | Complete expectation / denominator |
|---|---:|---:|
| Original artifact ZIPs and exact JSON members | 15 | 15 |
| Raw pack fragments | 12 | 12 |
| Selected logical jobs represented in fragments | 98 | 98 |
| Proof steps represented in fragments | 316 | 316 |
| Selected code jobs | 98 | 182 code jobs |
| Explicitly excluded code jobs | 84 | 182 code jobs |
| Other manifest gate jobs | 72 | 254 total manifest jobs |
| Changed repository paths in plan | 125 | 125 |
| Accepted engine/lib byte pins | 53 | 53 |

Observed step outcomes: `{"passed": 316}`. Missing packs: `[]`. Missing artifact names: `[]`. The full manifest’s 254 jobs are not a test-pass denominator. The selected and explicitly excluded code inventories exhaust the 182 code jobs. Q07 is present in the manifest and explicitly excluded; this review does not claim it ran.

The verifier recomputes all **98 selected job execution digests** and **316 planned step specification digests** from the exact actual merged manifest. It checks complete observed-plus-missing accounting, fragment identities, pack assignment, proof order, source hashes and every result. It does not rerun the scope-selection planner. A successful hosted job name alone is never treated as semantic proof.

| Pack | Hosted job ID | Hosted status / conclusion | Logical jobs in fragment | Proof steps | Actual fragment outcomes |
|---:|---:|---|---:|---:|---|
| 0 | 113826124598 | completed / success | 1 | 16 | `{"passed": 16}` |
| 1 | 113826124847 | completed / success | 1 | 1 | `{"passed": 1}` |
| 2 | 113826124804 | completed / success | 5 | 7 | `{"passed": 7}` |
| 3 | 113826124768 | completed / success | 10 | 44 | `{"passed": 44}` |
| 4 | 113826124749 | completed / success | 11 | 41 | `{"passed": 41}` |
| 5 | 113826124773 | completed / success | 10 | 40 | `{"passed": 40}` |
| 6 | 113826124689 | completed / success | 10 | 27 | `{"passed": 27}` |
| 7 | 113826124943 | completed / success | 10 | 29 | `{"passed": 29}` |
| 8 | 113826124849 | completed / success | 10 | 31 | `{"passed": 31}` |
| 9 | 113826124633 | completed / success | 10 | 17 | `{"passed": 17}` |
| 10 | 113826124722 | completed / success | 10 | 37 | `{"passed": 37}` |
| 11 | 113826124819 | completed / success | 10 | 26 | `{"passed": 26}` |

The retained aggregate is `clear`, has 98 jobs and 316 proof steps, and reports `{"passed": 316}`. Its logical evidence SHA-256 is `33eefd16f3c4b548f18e3a442c66415c684089bce99f3ec464bc05a91464dc73`. Independent exact aggregate reconciliation: **True**.

## Actual owner command and required gates

Logical owner: `company-relationship-candidates`, pack **11**. Proof ID: `File, pinned-source and immutable observation replay contracts`.

```sh
python -m pytest tests/test_company_relationship_candidates.py tests/test_company_pinned_relationship_candidates.py tests/test_company_relationship_review_set.py tests/test_company_relationship_observations.py -q
```

The new owner group reports **275 passed in 9.25s** at line 1209 of job `113826124819`. The actual new fragment, logical job, proof ID, execution digest and step digest are bound to the same source command. No old-run test result is an input to this conclusion.

The owner step specification SHA-256 is `3f346c8660ce1278b5d782982c639324dfa4412faa4856e91d19d822a0481d70`; its job execution SHA-256 is `5ff9e1dd799a76ff34ad59e95d95cafbc10cea6c6f4cb58da6922bb28801ff6f`.

The corrected candidate’s actual contract-delta job `113824875115` is `success`. Its full raw log reports **0 introduced, 0 inherited**, using the actual tested base. This is a new exact-head gate result. The former 2/0 finding on the old candidate remains preserved as a failed result.

The actual final `ci-gate` log, when present, is checked against the retained aggregate’s exact status, logical evidence digest, classification counts and infrastructure count. Actual semantic-clear and successful-contract notices are required before this verifier reports complete successful CI evidence. Hosted gate step outcomes and exact log line references are retained in the `ci_gate` field of the full and focused records.

| Full raw hosted log | Job ID | Bytes | SHA-256 |
|---|---:|---:|---|
| contract_delta | 113824875115 | 30,334 | `a22f7871b0b85b32caad86d096502e1650b04340cb4d2ab4f3834d49130dad04` |
| owner | 113826124819 | 116,767 | `876a79483f7b8c586d1177aa0568ec880618252ad65c338796775f92da57bc71` |
| ci_gate | 113836753055 | 126,617 | `1d698c379bc37c9621ffa13482f4a050659a5a9298a927555f770af5307a7a9e` |

Raw log bodies are preserved unchanged. The receipts also retain bounded exact raw or ANSI-stripped excerpts and line numbers. This corrected packet does not inherit the old packet’s excerpt-only retention limit.

## Actual source composition and material correction

The full actual merged CI manifest differs from the prior merged source only in the existing `unrun-builders-stores` job: the backup owner command adds the PostgreSQL binaries to its PATH, verifies `psql`, `initdb` and `pg_ctl`, rejects root execution, and runs `tests/test_backup_user_tables.py` plus `tests/test_backup_iw2_snapshot.py`. The workflow adds the corresponding test and fixture triggers. The owner’s 71 scope paths and four-suite command remain unchanged. `UPSTREAM_MERGED_MANIFEST_DELTA.diff` and `UPSTREAM_WORKFLOW_DELTA.diff` preserve the exact comparisons.

The broad GitHub upstream compare reached its 300-file cap; it is not represented as a complete repository overlap census. The separate source verifier closes the relevant 53-file byte question directly: **three complete Git tree responses and 52 unique blob responses** establish all **53 accepted engine/lib paths**, totaling **1,483,905 bytes**, at the actual tested Git tree. Each raw tree/blob API response and exact source byte sequence is losslessly retained in `tested_source_pin_read_001.json`. The reference manifest was accepted at checkpoint `6b58f15adae3b1d402d9993c52609d00083f1453`. Its later preservation in a review at 9df does not change that underlying reference revision.

This source result is byte compatibility for the 53 named paths. It is not an independent new functional review of those modules or certification of the other 18 owner scope paths. The principal retains responsibility for accepted-source verification and the native proof.

The correction commit is exactly one commit ahead of 9df, with an 18-path bounded comparison. The two frozen archived test-shaped files were renamed to `.py.txt`, preserving their exact bytes, not converted into extra runnable suites or hidden through a policy exclusion. The committed path map binds their original logical filenames, checkpoint 6b58, last original-path checkpoint 9df, current archive paths, lengths, hashes and the canonical runtime suite separately. Original and renamed v1/v2 source bodies were independently read at their immutable refs and compared byte-for-byte. The actual discovery law identifies runnable test basenames ending in `.py`; the archival representations no longer meet that discovery condition. The actual new 0/0 contract result verifies the material correction in hosted CI.

V1 archive: **43,659 bytes**, SHA-256 `80acae7aadcecec3214fe86d77c99da841d2544629d35380ec11b5d9cc94d67e`. V2 archive: **49,406 bytes**, SHA-256 `a73700e639c8e97a4ff84951b48358abe63b1f5048560d03b0e40f2310ac44da`. The committed map’s exact SHA-256 is `e79558bf8466b6f0b10faa281cb5164e9d4d39cf8e8be331193758acb006f75f`.

The prior failed/pending archive remains unchanged. Its 57 original manifest members were checked, and its Git blob matches the archive carried by the correction commit. `OLD_PACKET_PRESERVATION.json` records this check; the old archive and its already-frozen reports were not rewritten or inserted as new-run proof.

| Exact source file preserved as data | Bytes | SHA-256 |
|---|---:|---|
| `sources/merged_legacy_jobs.yml` | 1,248,919 | `6659e06968a347a6ccba8a35d07bdc7bb601e32acd84d410ad66ad238eed08cd` |
| `sources/scripts/ci_semantic_proof.py` | 73,298 | `9df4b9a9a8d68f7e9aa34a8eebe99e8d17e27f2ef0560eadcc050f3130359158` |
| `sources/scripts/run_ci_pack.py` | 223,426 | `65564916a55eb806d3d9fb0cd4e12726f05fec953f6e47ccd9240f5a141049df` |
| `sources/scripts/check_contract_delta.py` | 62,554 | `894f4e66dd323d5b17be2fe570bfd2fcb8456f92404d464a65b5b16f5c6a278f` |
| `sources/.github/workflows/ci.yml` | 318,629 | `ef9cd98724e4c545e4cb55420d0a6e5c9fc36b9d4efde449416b560cd8d255a9` |
| `sources/scripts/audit_unrun_tests.py` | 50,447 | `e50ba44cb678761d55f1c5bb9828390bd7c21c1672760d6f52781ca194dd7d47` |

## Artifact byte inventory

Every listed ZIP was downloaded through its actual GitHub artifact GET endpoint, matched to API length/digest, checked for a unique safe regular JSON member, and retained with that exact member. API and transferred artifact inventories must match exactly at the selected observation. Full member lengths and SHA-256 hashes, CRCs, source bindings, fragment job IDs and step inventories are in the machine-readable inventory; the table below lists every original ZIP.

| Artifact ID | Artifact name | ZIP bytes | ZIP SHA-256 |
|---:|---|---:|---|
| 11616114760 | `ci-changed-files` | 1,927 | `b955e5564e0ede563a15d28fa02d57d5eb848b8ce0e77d58d85363029eef3843` |
| 11616304926 | `ci-semantic-pack-37932039980-7` | 3,180 | `3543974c23e053aafa375c45a719052e6e5a133261a740c59efc2f9f873d8bfc` |
| 11616582831 | `ci-semantic-plan-37932039980-1` | 30,406 | `48dead6cfdd7c09763a0d79a22776c197713723ba116f70a79c20ad17cdb8a08` |
| 11616603602 | `ci-semantic-pack-37932039980-3` | 4,360 | `66afb61528741ba0c6f77838a43b3f4f9452dc2ad1f82b637f58c63d4aebbb63` |
| 11616603913 | `ci-semantic-pack-37932039980-8` | 3,338 | `78f067fb81c6263666557905ba147a3d371b4d4e855edc8c92b4f07f2586c723` |
| 11616674839 | `ci-semantic-pack-37932039980-4` | 4,356 | `d7a9bc45c99310b56b88730d7fe5f9922558e02ef7d6ce1d7d4bda370b278453` |
| 11617103120 | `ci-semantic-pack-37932039980-1` | 643 | `8386a4dad5eac248103aa954695c308774d9b3295ad362cb5c22d520776b7f1b` |
| 11617168204 | `ci-semantic-pack-37932039980-2` | 1,374 | `f64a688ef104d80379fa8358c1943513f24c7236eec7e46aa09a3cc568975db2` |
| 11617453832 | `ci-semantic-pack-37932039980-6` | 3,171 | `7e7595ef698d288727d2d802a5d739b784cdf8eea63c48549805c1717d807101` |
| 11617545100 | `ci-semantic-pack-37932039980-10` | 3,873 | `28a752c692b0ffca13f900635da8ac62f1487313f7e4737fa07d3a740b434885` |
| 11617700503 | `ci-semantic-pack-37932039980-11` | 3,044 | `b3f2cc9a0865d2bac688942d9b237ee92de90358c8437da4cde898706056ce01` |
| 11617730393 | `ci-semantic-pack-37932039980-9` | 2,380 | `a37f5df2b47893ade2bb952e8d3ab8bc4ba18269f39ca50348ae5242f2bdfcfd` |
| 11617745215 | `ci-semantic-pack-37932039980-5` | 4,223 | `ca245886f31b7bdbdb36dd6c5b56dfe0a9a9f3e5e3efc85dcc5d30a28a3a3166` |
| 11617957043 | `ci-semantic-evidence-37932039980` | 27,778 | `51c4f3ec635c16798dc2c043ea3101a06ad65b4c75c29f1ecf521314ed466cdf` |
| 11618476440 | `ci-semantic-pack-37932039980-0` | 1,591 | `593506ab6e07e4cc7aad394e7cf1fdcb1273d9c7e90829a62ddeafb220f710bd` |

## Exact-head check census and process accounting

These are actual observations, not a release-policy ruling. In particular, any merge-queue authority check failure is retained without silently turning it into a successful check or waiving it. The principal decides which current protected procedure applies.

| Exact-head check | Check ID | Status | Conclusion |
|---|---:|---|---|
| `ci-gate` | 113836753055 | completed | success |
| `trusted-ci` | 113826126041 | completed | skipped |
| `ci-pack-7` | 113826124943 | completed | success |
| `ci-pack-8` | 113826124849 | completed | success |
| `ci-pack-1` | 113826124847 | completed | success |
| `ci-pack-11` | 113826124819 | completed | success |
| `ci-pack-2` | 113826124804 | completed | success |
| `ci-pack-5` | 113826124773 | completed | success |
| `ci-pack-3` | 113826124768 | completed | success |
| `ci-pack-4` | 113826124749 | completed | success |
| `ci-pack-10` | 113826124722 | completed | success |
| `ci-pack-6` | 113826124689 | completed | success |
| `ci-pack-9` | 113826124633 | completed | success |
| `ci-pack-0` | 113826124598 | completed | success |
| `ci-authority/main` | 113825297584 | completed | success |
| `ci-authority/codex/merge-queue-pilot` | 113825293880 | completed | failure |
| `ci-authority` | 113825238882 | completed | success |
| `grader-manifest` | 113825181830 | completed | success |
| `capability-broker` | 113825178662 | completed | success |
| `self-mod-fence` | 113825171888 | completed | success |
| `github.event_name == 'pull_request' && github.event.pull_request.head.repo.full_name != github.repository && 'grader-manifest' || 'fork-grader-manifest-unused'` | 113824876181 | completed | skipped |
| `github.event_name == 'pull_request' && github.event.pull_request.head.repo.full_name != github.repository && 'self-mod-fence' || 'fork-self-mod-fence-unused'` | 113824876143 | completed | skipped |
| `github.event_name == 'pull_request' && github.event.pull_request.head.repo.full_name != github.repository && 'capability-broker' || 'fork-capability-broker-unused'` | 113824876121 | completed | skipped |
| `contract-delta` | 113824875115 | completed | success |
| `ci-plan` | 113824875035 | completed | success |
| `fence-pack` | 113824874301 | completed | success |
| `ci-authority` | 113824858395 | completed | success |

Every managed read process in this corrected-candidate audit completed with exit code 0 and was reconciled. Native commands use GitHub GET operations and in-memory processing; there are no native writes, Git mutations, application imports/tests, workflow dispatches, reruns, cancellations or release changes. `native_read_scripts.json` preserves the exact read scripts, purposes, process footer evidence and associated receipts.

| Native PID | Purpose | Exit code | Runtime seconds |
|---:|---|---:|---:|
| 10557 | New candidate PR, commit, run and exact-head check discovery | 0 | 3.19 |
| 13436 | Run, tested commit, correction compare and full merged CI source reads | 0 | 10.43 |
| 19404 | Actual upstream compare, committed archive map and old/new archival source reads | 0 | 10.86 |
| 24738 | Actual plan and changed-path artifact ZIP reads | 0 | 3.49 |
| 31546 | New packs 1 and 2, metadata and whole corrected contract-delta log | 0 | 9.38 |
| 43720 | New packs 3, 4, 8 and 10 with metadata snapshot | 0 | 11.12 |
| 50553 | Actual tested Git trees and all 53 accepted engine/lib source byte pins | 0 | 8.61 |
| 66090 | New packs 5, 6, 7, 9 and 11, metadata and whole new owner log | 0 | 14.08 |
| 88115 | Concluded run metadata, pack 0, final semantic aggregate and whole final gate log | 0 | 9.58 |

## Reproduction and proof limits

The durable archive contains these observations, the exact artifact ZIPs and members, full raw new logs, exact CI source data, all retained source-pin API/blob bytes, both independent verifiers, historical verifier versions and bounded read/materialization scripts. `PACKAGING_NOTES.md` records representation and transport adjustments. Extraction and verifier replay are accounted for separately in the archive verification receipt; fresh replay outputs never alter the frozen originals.

With Python 3 and PyYAML, run from the extracted evidence directory using fresh output names:

```sh
PYTHONDONTWRITEBYTECODE=1 python -B verify_tested_code_pins.py --output FRESH_SOURCE_PIN_VERIFICATION.json
PYTHONDONTWRITEBYTECODE=1 python -B verify_corrected_artifacts.py --snapshot artifact_read_005_and_snapshot_006.json --output FRESH_CI_EVIDENCE_VERIFICATION.json
```

The 53-pin verifier uses Python’s standard library. The CI verifier reads preserved YAML with PyYAML 6.0.3; repository source is treated only as data and AST. Replays perform no network, Git, native device operation, application import or application test.

No current main freshness, live hold, licensing right, evidence custody, source truth, historical availability, Graph1 admission, production acceptance or predictive promotion is certified here. Independent source composition review belongs to its named owner; this observer does not claim to have authored or functionally reviewed those modules. The principal owns canonical release adjudication, expected-head merge, accepted-source verification and the actual native C01 witness.
