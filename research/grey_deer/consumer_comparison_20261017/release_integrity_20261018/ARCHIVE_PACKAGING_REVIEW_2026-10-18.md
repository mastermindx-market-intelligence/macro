# Independent archive-packaging review — 18 October 2026

Reviewer: `/root/forward_activation_review`. Review observation: **2026-10-18T09:36:41.679332Z**. Intended repository location: `research/grey_deer/consumer_comparison_20261017/release_integrity_20261018/ARCHIVE_PACKAGING_REVIEW_2026-10-18.md`.

**Disposition: the reviewed packaging candidate is an appropriate, lossless publication repair. No material inconsistency or owner-test evasion was found in this bounded review.** This accepts the archive representation and its stated evidence limits. It does not establish required-CI success, landing, Mastermind source acceptance, production deployment or programme acceptance.

## Scope and exact inputs

I read the four supplied packaging artifacts, compared the new index with its retained cloud predecessor, and independently recomputed byte counts, SHA256 values and Git blob identities for all 25 named cloud originals under `release_review/`. Only standard-library byte, JSON and text operations were used. I did not execute or import archived source, run tests, use native tools or network access, or change an existing source/evidence file. The sole new file is this review.

| Input | Bytes | SHA256 |
|---|---:|---|
| [Archive path map](ARCHIVE_PATH_MAP_2026-10-18.json) | 9,765 | `5e20da1b8683e87d0e8981b257633345a9e1319f5c620b498a52400476595412` |
| [Failure and packaging record](CI_FAILURE_AND_ARCHIVE_PACKAGING_2026-10-18.md) | 3,943 | `4d151f6c468a822d644ceed5298b4b13a16267d01cf662da5ba1e6de60b9d3f1` |
| [New packet index](README.md) | 10,838 | `50ebfefd6c7feb917b68b85c9b62f14a46adb12018f20e5cc58e46bba119cdee` |
| [Root-native import-check receipt](rr-evidence-archive-import-native-receipt-20261018.json) | 2,294 | `638b3afcd97ad597ffaaf40479c6848039f19296332983714b09028dc8e126aa` |
| Retained predecessor `release_review/README.md` | 9,598 | `6f304efd10a3265d7f95d087fc431a0c14af6feca5f8ef63790e6dc199ef5980` |

The first three current artifact hashes exactly match the native receipt's `source_sha256` bindings. The map and receipt consistently bind failed evidence head `f11fa0c66273ca1976f37e2f529fe9ff689ee439`, Macro PR #9595 and a subsequent worktree candidate. The original CI failure and PR-disarm observations are supplied by root through the failure record; this review did not independently retrieve hosted CI or PR state.

## All 25 archive preimages verified

**25/25 byte counts, 25/25 SHA256 values and 25/25 Git blob hashes match the map.** The verified total is **936,396 bytes**: 17 Python files and 8 shell files. Both original and destination paths are unique. Every destination is exactly its original relative path plus `.txt`; there are no absolute paths or parent-traversal components. Every entry declares `content_changed: false`, consistent with the retained preimage bytes.

The following is the complete verification coverage. Full per-file hashes remain bound by the exact map identity above.

| Original logical archive paths | Verified files | Result |
|---|---:|---|
| `candidate/scripts/deploy_code_to_vps.sh`; `candidate/tests/test_deploy_provenance.py` | 2 | All identities match |
| `helper_fixture_driver_20261018.py` | 1 | All identities match |
| `native_run2_candidate/scripts/deploy_code_to_vps.sh`; `native_run2_candidate/tests/test_deploy_provenance.py` | 2 | All identities match |
| `pre_native_candidate/scripts/deploy_code_to_vps.sh`; `pre_native_candidate/tests/test_deploy_provenance.py` | 2 | All identities match |
| `red_baseline/scripts/deploy_code_to_vps.sh`; `red_baseline/tests/test_deploy_provenance.py` | 2 | All identities match |
| `review_red_baseline/scripts/deploy_code_to_vps.sh`; `review_red_baseline/tests/test_deploy_provenance.py` | 2 | All identities match |
| `source/app/main.py`; `source/app/scheduler.py`; `source/app/web.py` | 3 | All identities match |
| `source/bot/__init__.py`; `source/bot/settle.py` | 2 | All identities match |
| `source/control_plane/locks.py` | 1 | All identities match |
| `source/portfolio/__init__.py`; `source/portfolio/forward_evaluation.py`; `source/portfolio/paper_account.py`; `source/portfolio/registry.py` | 4 | All identities match |
| `source/scripts/deploy_code_to_vps.sh`; `source/scripts/deploy_from_git.sh`; `source/scripts/refresh_datadog_release_tag.sh` | 3 | All identities match |
| `source/tests/test_deploy_provenance.py` | 1 | All identities match |

The cloud originals retain their original filenames. I independently verified those preimages against the supplied map; I did not independently read the renamed native destination files or assert a completed native Git rename/landing. The failure record attributes preimage and renamed-content verification to the root packaging operation.

## Exact index delta

The new README differs from the predecessor only by one inserted section, **“Evidence packaging correction — 18 October, after 09:16Z CI failure,”** and these three existing hyperlink targets:

| Previous target | New target |
|---|---|
| `candidate/scripts/deploy_code_to_vps.sh` | `candidate/scripts/deploy_code_to_vps.sh.txt` |
| `candidate/tests/test_deploy_provenance.py` | `candidate/tests/test_deploy_provenance.py.txt` |
| `helper_fixture_driver_20261018.py` | `helper_fixture_driver_20261018.py.txt` |

Removing that inserted section and reversing those three substitutions reproduces the predecessor text exactly. The section itself adds two explanatory links, to the map and failure record; those are new links, not additional substitutions of existing archive links. Existing result text, tables, source hashes, failed controls, excluded-cache refusal, runtime limits and the four-space normalization account remain unchanged.

The notice correctly identifies the six foreign `test_deploy_provenance.py` copies named in the map; preserves the reported 27 import/name findings and three separately base-reproduced reference-integrity findings; records the failed head and dated draft/disarm state; and retains the need for a new required-CI result and landing receipt. It does not convert the base-reproduction observation into a waiver.

## Documentary representation and owner-test boundary

The map explicitly identifies these files as another repository's source and tests, or earlier evidence stages. Its coverage includes original failures, review counterexamples, pre-native tests, the intermediate native test version, and the reviewed helper/test pair. Changing their archive suffix avoids presenting these documentary copies as active Macro source or six new Macro test suites. Retaining every byte, the source identity, stage attribution and original logical path is the correct preservation boundary for this packet.

In particular, the archive still binds the helper to `1ebfd44db982d73f7f9d507109fa3983ba65cc948e8afe9fe697589d712728a8` and its 49-case-stage tests to `1e463a9116fb6c9bc6e6fe10ea23bf619d8674fd7e0ad6ce2392410e302a897c`. It preserves the older 44-case test identity `a4ed6d45ed39eec1aa92ac9d4aeb82219dcefc60e9632e7f27dd8b00f6bfb42a` separately. Packaging does not transfer results between versions or qualify any later owner-worktree successor.

This is not an assertion that a text suffix makes code intrinsically safe to execute. The archive contract expressly requires a separately qualified owning workspace before restoring or executing a named source copy. There is no proposed change here to an owning Mastermind test assertion, active implementation, CI gate, waiver or source-owner rule. The independent source repair and its wider failed static contracts remain distinct work.

## Supplied native result and remaining acceptance

The native execution belongs to **root**, not this reviewer. Its receipt reports the unchanged Macro `tests/test_first_party_import_names.py` suite completed **15/15**, with zero failures, errors or skips and exit 0, between **09:28:04.477105Z and 09:29:10.750767Z**. The command is scoped to that existing test module. Its bound identities are:

| Native input/evidence | Bound SHA256 |
|---|---|
| `tests/test_first_party_import_names.py` | `799f2eb683ded3248a7e01f1db7d9308e22aae755dfb539c8d37969175f7105f` |
| `tests/conftest.py` | `ad0b342a4303b5dc098d203530e8e8a83d4b5c3cbc38730309448cac14570425` |
| 1,961-byte native log | `639dcdcd9b4fdfc0249796d57540ab6dc221422a38e1ada02c78f58d2e0885cb` |
| Native JUnit | `11bb505a5984cf7cdfcec14fdbd3cb87fad05d284950b467de11644764aa0eb5` |

The receipt reports matching post-run source hashes, an empty post-run data-site Git status, enabled data/module guards, disabled provider/LLM fuses, and no model execution or production deployment. I verified the receipt's local identity and packaging-artifact bindings, not the native test/conftest bytes or raw log/JUnit independently. Those remain attributed root observations.

This result supports resolution of the affected import-check failure in the candidate. It does not demonstrate that the six-suite discovery/registration finding, all required CI packs or reference-integrity gate now pass. The admitted next checks are the existing affected suite-discovery/contract gate and normal required CI on the actual successor, followed by exact-file landing evidence through the current owner. No blind rerun, gate waiver, deployment or release acceptance follows from this review.

## Historical transfer and normalization remain separate

The **original 56-file transfer receipt remains a dated transfer record**. The separate removal of exactly four Markdown trailing-space bytes remains recorded by its own normalization receipt, with the original note recoverable from the retained UTF-8 JSON. The present 25-path archive map is a later representation change. None of these three evidence stages is silently substituted for another, and this review does not re-attest the original transfer or normalization operation. The unchanged account in the new README preserves that distinction.
