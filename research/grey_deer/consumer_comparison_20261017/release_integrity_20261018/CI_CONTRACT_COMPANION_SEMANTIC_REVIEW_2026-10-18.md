# #1610 companion contract semantic review

**18 October 2026 UTC · Independent source review · REQUEST_CHANGES for one replacement-coverage gap · Native test acceptance pending**

Reviewer: research/release reviewer, actual GPT-6 Astra Pro. This review concerns the four proposed test files and their frozen deployment-helper boundary. It does not decide custody, authorize test execution, change the helper, or qualify a release.

## Decision

The proposed consolidation is justified in direction. The three old functions contain obsolete implementation requirements, including a directory-list rollback implementation, regeneration of Datadog metadata rather than restoration of its preimage, a later service stop, and deletion of a cohort marker without established transition ownership. Preserving those exact predicates would preserve the wrong behavior. Their failed CI evidence must nevertheless remain recorded.

The ten new cases are substantive fixture designs, with positive observations before target restart and observations before rollback restart where applicable. They are not passing evidence yet. **Do not accept the coupled deletion as complete until F1 below is repaired:** the fake forward CLI ignores the actual canonical-root and release-SHA inputs. The removal drops a previous root-binding predicate without equivalent checking at the replacement boundary. The frozen helper currently supplies the correct inputs by source inspection; this is a test-coverage gap, not evidence that the frozen helper misroutes them.

The smallest repair is in the existing fake CLI: require its actual `MASTERMIND_FORWARD_EVALUATION_RELEASE_STATE_ROOT` to identify the fixture's canonical live-data root, and require the actual `--deployment-sha` supplied to `init` and `finalize` to match the expected target. This can strengthen all existing and proposed shell cases without another test matrix, app import, or production-helper change. Preserve all existing test bodies. Native validation, including the previously failed companion owners, remains pending after the candidate is frozen and custody is resolved.

## Exact bytes reviewed

All identities below were independently recomputed from local bytes. The proposal's four-file identities match.

| Proposed file under `release_review/ci_contract_candidate/tests/` | Bytes | SHA256 |
|---|---:|---|
| `test_datadog_vps_install.py` | 5,991 | `a5a118e2c852902dd908913929a0f598f1c00bf970475a0c780e81b484244e95` |
| `test_forward_evaluation.py` | 31,215 | `637c6dbe5b304bd69a66f68ae4d8e58538bd1279914132c40d2cf924f7d4cf8d` |
| `test_portfolio_archival.py` | 16,993 | `0d82dc934e3d16b954c859cfec2c9cfff17013cf9d785678eb5a8ee26a4ad384` |
| `test_deploy_provenance.py` | 46,634 | `90b872cb6de4d7b8b2c53cc91f747c0c24b6e1fc881526081c5369d9805aa59c` |

Supporting immutable local copies:

| File | Bytes | SHA256 |
|---|---:|---|
| `release_review/CI_CONTRACT_COMPANION_PROPOSAL_2026-10-18.md` | 22,900 | `355a8d4f90d1b62246cddf4f2ec85698fd1bd50e5e2777ceb98a787bf9ab7e60` |
| `release_review/candidate/tests/test_deploy_provenance.py` | 40,060 | `1e463a9116fb6c9bc6e6fe10ea23bf619d8674fd7e0ad6ce2392410e302a897c` |
| `release_review/candidate/scripts/deploy_code_to_vps.sh` | 20,370 | `1ebfd44db982d73f7f9d507109fa3983ba65cc948e8afe9fe697589d712728a8` |
| `release_review/source/scripts/refresh_datadog_release_tag.sh` | 881 | `985a3ee9757daa65604d7b53752fc7d10dc3aed2cfd4888208c4f47d0bdd8ad9` |
| `release_review/ci_contract_source/tests/test_datadog_vps_install.py` | 6,368 | `83ddabf469c078b7f5132d5dc6b75ab6c330dd385265452971f922120e7230c5` |
| `release_review/ci_contract_source/tests/test_forward_evaluation.py` | 33,519 | `41a49e87ae003b87716e85fe7bc716081ee41a2fbf732dc8f534b5f96423cbb3` |
| `release_review/ci_contract_source/tests/test_portfolio_archival.py` | 17,984 | `89147abe92872ff4abd2ead5671a08b0301ac40499f892bfcd73c79ca3b7ad79` |

The parent/proposal binds the failed hosted CI run `39109519443` to #1610 head `797c760f3e18eb6993579f56986103de9d9fdcb4`. This review did not query GitHub or re-observe that run, its current status, or the native checkout.

## Preservation and scope verified

AST comparison and exact function-source comparison found **37 original deployment test function definitions, representing 49 literal parameter cases**. All 37 bodies are byte-for-byte unchanged; their ASTs, including decorators and parameter values, are unchanged. Thus “49 old test function bodies” is imprecise: the preserved quantity is 49 cases across 37 functions. The candidate has 40 functions and 59 literal cases. This is static enumeration, not pytest collection or an execution result.

The only changed existing deployment-owner helper is `_fake_transport`, with the opt-in restart observer. `_write_executable`, `_run_deploy`, `_transport_events`, and `_established_marker` are unchanged. Three new test functions expand to 4 + 4 + 2 cases. Both embedded transport strings parse as Python; neither was executed.

Each companion copy removes exactly its named legacy function. Every remaining top-level function retains identical source and AST; there are no test classes. The forward copy also removes its now-unused module-level `subprocess` import. No unrelated function changes were found.

## F1 — canonical CLI handoff is not checked by its fake boundary

**Material replacement gap; repair before semantic acceptance of the coupled patch.** In the candidate deployment owner, `_fake_transport` assigns `data = root / "live-data"` and `marker = data / "portfolio_forward_evaluation/start.json"`. Its fake `python3` branch accepts the module and command but takes `expected` from `FAKE_EXPECTED`. It does not read `MASTERMIND_FORWARD_EVALUATION_RELEASE_STATE_ROOT` or interpret the actual `--deployment-sha` argument. `init` and `finalize` therefore stamp the expected fixture SHA and write the expected fixture path regardless of those actual inputs.

The deleted forward function checked the helper's canonical default and at least four explicit CLI root bindings. The remaining `test_activation_gate_order_and_canonical_lock_are_explicit` checks the canonical lock and authority comparisons, but not those CLI bindings. `test_deploy_writes_expected_marker_before_restart` checks where the fake wrote; its path is hard-coded by the fake. The retained forward unit test `test_release_cli_override_targets_canonical_live_data_only` sets the correct environment itself and exercises the real CLI separately; it does not verify the deploy helper supplies that environment.

Consequently, removing the helper's four CLI root assignments would not, by itself, be detected by the replacement fixture assertions. Supplying the old SHA to `init`/`finalize` likewise would not change the fake's output. These are reasoned counterexamples from source, not executed mutations. The proposal's statement that the existing owner establishes canonical routing is stronger than its actual boundary coverage.

Validate the received root before handling fake CLI operations and the received target SHA for `init`/`finalize`. Missing, conflicting, or malformed required inputs should fail that boundary. Do not infer a passing real-CLI integration result from this repair: it qualifies the shell handoff to a checked fake, while the retained real-CLI unit owner qualifies the receiver separately.

## Assessment of the ten proposed cases

| Cases | Meaningful distinctions in the actual proposed code | Limits |
|---|---|---|
| Datadog: onboarded absent/present × target health success/failure, four cases | The test copies the real refresher script into fixture source, ships it through the helper, and observes the selected `fixture.service` version file at restart. Prior bytes include a comment, so rollback cannot pass by regenerating only the old SHA. It checks reload-before-restart order, optional onboarding, and an unrelated onboarded default service sentinel. Omitting the tag update, using the old SHA, or targeting the default service would be distinguished by the positive cases and sentinel. | No real systemd or Datadog service runs. Atomic reader concurrency, permissions/ownership, and every refresher failure mode are not established. The existing custom failure-refresher cases retain coverage of a prior version file's absence or exact bytes after refresh failure. |
| Policy files: prior roots absent/present × target health success/failure, four cases | Both `.claude` and `.codex` contain distinct new reviewer and introduced files. The observer checks target bytes at the target restart, preventing “never transferred” from passing a final-state-only rollback check. Failed-health cases check prior bytes/absence at old restart and final state; newly created policy roots must disappear. | This does not run reasoning agents or validate the policies' content. These cases do not enumerate all receiver-only files, excluded descendants, symlinks, modes, or ownership. Existing generic snapshot/restore and excluded-descendant controls remain intact; the proposal does not need to duplicate them merely for policy directory names. |
| Healthy unchanged code: missing/pending cohort, two cases | The fixture overwrites its old app content with source, sets both on-disk and independently modeled booted SHA to target, and starts active with healthy policy fields. Its only extra remote file is the excluded deployment marker. Thus these are meaningful no-op preconditions by inspection, not merely ordinary changed-code deployments. They require one restart and init/finalize leading to an active marker. The existing active-cohort repeat checks the complementary valid no-op. | Actual forward CLI effects are modeled. Root/SHA handoff assertions are self-fulfilling until F1 is fixed. Existence of init/finalize events alone is not proof of real cohort correctness; the broader preserved owner covers modeled order and failure behavior. |

The removed rollback-scheduler predicate demanded `probe_health "$PREVIOUS_SHA" 0`. Retiring it is justified because the frozen helper now also requires scheduled-runtime health during recovery. Existing target-scheduler and restored-health failure controls remain, but no claim is made that every possible restored-health field mutation has been independently exercised.

## Observer and real refresher execution boundary

The added observer is off by default because inherited `FAKE_*` variables are stripped and each new test opts in with fixed fixture-relative paths. It resolves each requested path before applying the existing root-containment check, so the observer does not follow an observed path outside the resolved fixture root. It reads bytes or records absence and appends to a fixture-root JSONL file before the fake service updates its booted state. It does not run the observed policies or make a network call. I found no new observer path-escape or production-side mutation in these ten controlled setups.

The Datadog cases explicitly set `SYSTEMD_ROOT` to the fixture systemd directory and `SYSTEMCTL_BIN` to the fake systemctl shim. The fake SSH wrapper maps the helper's `/etc/systemd/system` paths to that same directory. The helper supplies `MASTERMIND_SERVICE='$SVC'` and the target argument to the deployed refresher; the reviewed refresher uses those inputs, writes through `mktemp`/`mv`, and calls the shim. This is a substantive real shell-refresher boundary, not `SYSTEMCTL_BIN=true` standing in for the whole update. It still remains an unexecuted source design in this review.

The fake transport is a controlled test harness, not a general sandbox for arbitrary helper code. Its Bash, real local rsync, and selected local file utilities perform actual fixture operations when executed. Existing app-importing owner tests and companion module tests are separate execution effects. Reviewing this addition does not admit any of those runs or certify isolation on the native host.

## Evidence and next acceptance step

Only local file reads, hashes, textual diffs, and standard-library AST parsing/enumeration were performed. No first-party import, helper execution, test collection/run, provider/installer execution, native mutation, Git operation, or live delivery probe occurred. No source or candidate file was edited by this reviewer.

Repair F1 in the existing fixture, freeze the resulting four-file identity, and review that narrow delta. Resolve actual custody in the parent's separate task. Native test acceptance then requires the admitted candidate's affected existing owners and deployment cases to be executed with their real results retained, including failures or skips. The earlier 49-case pass belongs to its frozen source; the three hosted failures stay failed evidence until a new qualified run supersedes them. Neither this review, static parsing, nor a future fixture pass establishes live deployment or programme acceptance.
