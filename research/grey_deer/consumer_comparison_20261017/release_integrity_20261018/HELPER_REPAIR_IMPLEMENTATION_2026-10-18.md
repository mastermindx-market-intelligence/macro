# Deployment-helper repair — candidate and confined validation

**18 October 2026 UTC · Bounded source candidate · Native acceptance and production qualification pending**

## Result and exact handoff

The admitted helper/test slice is implemented and frozen. The six demonstrated failures in the supplied helper are corrected in the confined fixture. Independent review then supplied three additional failing controls: two established-cohort authority mutations and one silent failed receipt-directory scan. They now pass. The final standard-library driver executed **44 standalone test cases: 44 passed, 0 failed**. This is not a pytest result or a production delivery result.

Only these two first-party candidate paths change:

| Path | Bytes | SHA256 |
|---|---:|---|
| [candidate/scripts/deploy_code_to_vps.sh](candidate/scripts/deploy_code_to_vps.sh.txt) | 20,370 | `1ebfd44db982d73f7f9d507109fa3983ba65cc948e8afe9fe697589d712728a8` |
| [candidate/tests/test_deploy_provenance.py](candidate/tests/test_deploy_provenance.py.txt) | 39,649 | `a4ed6d45ed39eec1aa92ac9d4aeb82219dcefc60e9632e7f27dd8b00f6bfb42a` |

The original source copies remain unchanged: helper 14,934 bytes, SHA256 `c158fc903121b8c4ad680049ded16000913393039944c6eec3a23d44ca376204`; tests 19,097 bytes, SHA256 `1bc5bf5e1980cb97fb8051d062e90e60536432b03782ff008cb31066f950bd3c`. The archive wrapper, tag helper, forward module, accepted release reports, models and studies have not been edited. There is no additional first-party test support file. The small validation driver and receipts below are review artifacts.

Parent admitted this slice after binding current native base `d65414e89ad3b930d84d614196a91d3cce8ba589`, comparing the fourteen governing/reviewed paths with the protected source, and completing the open-PR census. Its only helper/test hit, #124, has no unlanded delta in these targets. Forward-module ownership remains with #1586; this repair does not acquire that module. The parent's native workspace and release custody remain authoritative.

## What changes and why

The helper now stops the configured service and verifies its nonrunning state before snapshot or live-tree mutation. It explicitly issues `systemctl stop` even when an earlier observation is already nonrunning, because the observed unit has `Restart=always`. It requires stop success followed by `ActiveState=inactive|failed` and `MainPID=0`. These checks cover the configured unit; they do not establish that every external writer is absent.

A snapshot in the existing protected `.deploy_prev` area captures the entire eligible receiver tree using the same, unchanged `EXC` array as forward transfer and restoration. It covers receiver-only files that `--delete` can remove. Readiness is recorded only after snapshot copy, checksum verification and exact provenance/optional tag preimages succeed. Earlier complete backups survive a failed new snapshot. No new controller, queue or lifecycle store is introduced.

Forward copy, snapshot and restore use checksum comparison. This avoids rsync's ordinary size-and-mtime quick-check collision, which the fixture reproduces with unequal bytes sharing size and timestamp. Recovery explicitly stops the target before restore. It restores the eligible tree with deletion and the same exclusion protection, then verifies it before restarting. A missing/incomplete snapshot after possible mutation, failed restore, or unverified restore leaves the service stopped. A snapshot failure before live-tree mutation can restart the unchanged prior source without treating the incomplete snapshot as a preimage.

The code provenance marker is replaced atomically. Optional Datadog state has its exact prior bytes or prior absence captured and restored, and the existing tag helper receives the selected service identity. Restoration uses the original health contract, including scheduled runtime, and the previous valid code SHA when available. Failed restored restart or health is explicitly incomplete. Successful recovery wording is limited to **code rollback verified; runtime data retained**.

An established active cohort is preserved byte-for-byte across upgrade and no-op. Its historical deployment SHA may differ from the new code SHA. The helper skips its already-no-op initialization/finalization, checks marker identity before target start and after final verification, and refuses to silently initialize a marker that disappears. New or pending cohorts keep the existing successful init/finalize path. The helper never deletes or rewinds `start.json`, accounts, fills or other runtime data. Changed/unknown marker state requires reconciliation.

The review correction also records a failed final authority comparison, lock check, finalize or status command independently of marker identity. An unchanged August cohort marker cannot now hide changed account/fill bytes under a recovery-complete result. Runtime bytes remain retained and authority/state reconciliation is explicit.

The existing settlement gate matches all top-level `*.json` entries, including a directory or dangling symlink with that suffix. It separately checks the enumerator's exit status, so a silent failed scan cannot return `clean`. A shell EXIT/INT/TERM path attempts the same bounded recovery once; a local SIGTERM control exercises the partial-copy branch.

## Evidence: actual failures and final controls

### Supplied helper, before repair

[HELPER_RED_BASELINE_2026-10-18.json](HELPER_RED_BASELINE_2026-10-18.json) records six executed failures against the exact supplied helper. The failed assertions were inspected; they are not missing-tool or harness errors.

| Original counterexample | Observed failure |
|---|---|
| Source replacement with an active old service | Live copy occurs before stopping the fake service. |
| Receiver-only/unlisted paths | Deleted `docs/obsolete.md` does not return; named-root backup cannot represent the full eligible tree. |
| Early snapshot-copy error | A later successful loop iteration masks failure and deployment reaches success. |
| Restored health remains unhealthy | Recovery still logs completion. |
| Foreign marker appears during refused init | Earlier absence is treated as cleanup ownership and the marker is deleted. |
| Excluded nested `.env` changes after snapshot | Whole-directory rollback rewinds the newer protected value. |

The exact original red test source is preserved in `red_baseline/`; its SHA256 is `8a5a275be5243201428c80636b531b778e43dd4503e1037d8e927306dd63a8aa`. It matches the original receipt. It was reconstructed from the retained authoring bytes and hash-checked, not silently replaced with the later test definitions.

### Independent-review counterexamples

The preceding candidate, helper SHA256 `c64b940d75a70db26eeed6af1305c2c0e7c924201026a45b69aaa8de2ebe483d`, is preserved with the exact review test source in `review_red_baseline/`.

| Receipt | Executed result before the final correction |
|---|---|
| [HELPER_ACTIVE_COHORT_REVIEW_RED_2026-10-18.json](HELPER_ACTIVE_COHORT_REVIEW_RED_2026-10-18.json) | 0/2 passed. Established active marker plus account mutation, then fills mutation: the authority gate refuses, old code returns, changed bytes remain, but recovery incorrectly says complete. |
| [HELPER_RECEIPT_SCAN_REVIEW_RED_2026-10-18.json](HELPER_RECEIPT_SCAN_REVIEW_RED_2026-10-18.json) | 0/1 passed. A silent nonzero `find` admits deployment success. |
| [HELPER_EXCLUDED_CACHE_REVIEW_CONTROL_2026-10-18.json](HELPER_EXCLUDED_CACHE_REVIEW_CONTROL_2026-10-18.json) | 1/1 passed as a conservative refusal. See the availability limitation below. |

### Final source

[HELPER_CANDIDATE_REVIEWED_VERIFICATION_2026-10-18.json](HELPER_CANDIDATE_REVIEWED_VERIFICATION_2026-10-18.json) binds the final helper/test hashes above and records 44/44 standalone cases. This supersedes the earlier 38-case and 40-case candidate receipts without erasing them. `bash -n` passed. The five existing application-import test functions are AST-identical to the originals, and the helper's `EXC` argument array is byte-identical.

Executed controls include initial and rollback stop failures; failed/incomplete snapshots; receiver-only deletion and new-source removal; protected nested data; same-size/same-mtime restoration; partial restore without restart; old health failure; code marker and optional tag restoration; established cohort upgrade/no-op/disappearance; refused/lost initialization or activation effects; account/fill mutation and missing authority; scheduled-runtime refusal; SIGTERM recovery; and newly introduced shared runtime packages.

## Reproducing the reported local execution

[helper_fixture_driver_20261018.py](helper_fixture_driver_20261018.py.txt) is 3,434 bytes, SHA256 `380ea13a8dcda1ef7a25eb888a5223e43ae1ab8bc36276509917303e9864be44`. It uses Python's standard library to load the exact standalone test functions, supplies only the small pytest decorator/assertion interface they require, and records each executed parametrized case. It excludes the five application-import tests. Pytest is absent in this cloud runtime; no installation was attempted. Native owning pytest remains a separate gate.

From the review workspace, reproduce the expected six original failures (exit 1):

```bash
python3 release_review/helper_fixture_driver_20261018.py \
  release_review/red_baseline/tests/test_deploy_provenance.py \
  integrity /tmp/rr-original-red.json
```

Reproduce the final forty-four passing cases (exit 0):

```bash
python3 release_review/helper_fixture_driver_20261018.py \
  release_review/candidate/tests/test_deploy_provenance.py \
  all /tmp/rr-candidate-verification.json
```

For the additional review failures, use the same driver with `release_review/review_red_baseline/tests/test_deploy_provenance.py`, the selector `active_cohort_authority_mutation` or `silent_receipt_scan_failure`, and a new output receipt path. These are expected exit-1 controls; they are not part of the final candidate's failure count.

The fixture supplies fake SSH, systemctl, curl, forward CLI, flock, sleeps and failure controls. Only one fake host and fixture paths are admitted. Real local rsync **3.2.7, protocol 31** supplies the actual filter, checksum and deletion behavior within temporary trees. The fake booted SHA is distinct from the on-disk marker. No application or forward module is imported; no service, production data or network operation occurs. The shim's fake flock tests invocation/order, not real lock concurrency. The harness is an orchestration and filesystem-semantics proof with explicit boundaries, not a production simulator.

## Remaining limits and deliberately unexecuted cases

**A protected descendant can prevent exact restoration of an introduced directory.** The target fixture creates `new_package/module.py`; startup then creates excluded `new_package/__pycache__/x.pyc`. On failed health, restore removes the included module and retains the excluded cache. Rsync cannot remove the now-nonempty introduced container, and its verification output is nonempty. The helper reports restoration incomplete and leaves the service stopped. This is verified safe refusal with an availability cost, not a passing exact-restore claim. It requires qualified recovery by the real owner; no directory-normalizing special case or cache deletion was added.

The original design's H01–H16 matrix was broader than the implementation proof. The following variants have **not** been executed and are not counted as passed:

- Real SSH interruption or reply loss at arbitrary remote command boundaries, global concurrent deployments, host/power loss or SIGKILL. Simulated lost init/finalize responses do not close these larger windows.
- Every first-init/pending-state variant against the real forward module, durable snapshot/model/settlement effects, or all-book activation serialization. The module's owner and initialization semantics are unchanged.
- The complete path-type matrix: directory-to-file/symlink replacement with excluded descendants, external symlink traversal, all plain included symlink and mode/ownership permutations. The tested snapshot-root symlink refusal and new-cache container case cover only their declared paths.
- All no-op variants with stale health or existing pending state, dry-run transport failure, a stop reply lost after an effective stop, a restored-service restart failure distinct from target restart failure, and every wrong-health-SHA/timeout variant.
- A full per-book/per-artifact settlement matrix, every excluded family after startup, and every generic shell/SIGINT/SIGTERM failure timing. WAL/receipt, nested `.env`, new cache, and SIGTERM-after-copy controls are narrower.
- Native owning pytest, production rsync/systemd versions and behavior, startup compatibility of the full accepted archive, live upgrade, restored runtime authority invariants, and backend-to-user acceptance.

The parent's live evidence shows an active historical cohort since 11 August and a configured service with `KillMode=mixed`, `SendSIGKILL=yes`, one-minute stop timeout and `Restart=always`. It does not prove absence of detached writers or exclusive deployment ownership. No such proof is claimed here. A successful code-health result does not attest that excluded regional books, queues, journals or forward snapshots have no target-start effects.

## Parent's next acceptance step

Transfer only the exact final helper and existing test owner into the admitted native successor, run the owning pytest suite there, and bind independent semantic review to these hashes. Continue through the existing exact-bundle and runtime release qualification after those source gates. The historical active-cohort upgrade is the relevant live path; newly initialized or pending cohorts remain separately bounded. This candidate neither installs accepted #1567 nor establishes delivered Risk Radar intelligence, and the broader programme work remains with the parent.
