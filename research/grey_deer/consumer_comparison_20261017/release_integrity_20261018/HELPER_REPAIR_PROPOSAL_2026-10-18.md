# Mastermind #1567 — smallest coherent deployment-helper repair

**18 October 2026 UTC · Independent design proposal · No implementation or execution acceptance**

> Historical stage note: this proposal records the design-only stage before the parent admitted the bounded helper/test implementation. Its statements about unexecuted tests and proposal-only writes apply to that stage. The subsequent local candidate, executed failure controls, exact source hashes and remaining limits are recorded in [HELPER_REPAIR_IMPLEMENTATION_2026-10-18.md](HELPER_REPAIR_IMPLEMENTATION_2026-10-18.md). The accepted programme/release reports and original source copies remain unchanged.

## Decision

Repair the existing `scripts/deploy_code_to_vps.sh` transaction before treating it as a qualified carrier for the accepted future-source-date fix. Keep the current archive wrapper and the forward-evaluation owner. The first useful source change should address service ordering, complete restoration of the tree the helper can change, explicit snapshot failure, honest rollback health, and retention of marker state whose ownership is unknown.

**This proposal does not authorize or qualify a production deployment.** No deployment helper, first-party Python module, scheduler, provider, sampler or recovery command was executed or imported. The only writes for this assignment are this proposal. The supplied source files and accepted reports remain unchanged. Tests below are proposed and have not run.

The current runtime has an established active cohort. It therefore supports a narrower upgrade qualification than a first initialization or recovery of a pending cohort. Do not use that fact to hide the latter defects; do not require a healthy historical cohort to acquire the new code's SHA. Source and cohort identities have different meanings.

## Evidence and custody

| Source | Identity read for this proposal | What it establishes |
|---|---|---|
| [Deployment helper](source/scripts/deploy_code_to_vps.sh.txt) | 14,934 bytes; SHA256 `c158fc903121b8c4ad680049ded16000913393039944c6eec3a23d44ca376204` | Exact ordering, synchronization filters, named snapshot scope, health handling and marker cleanup described below. |
| [Archive wrapper](source/scripts/deploy_from_git.sh.txt) | 1,493 bytes; SHA256 `b983a9e88f6eddeac00929797d1e05c80e09e3c206bcabf4e26342fdb7dbb42f` | Fetch configured remote/base, reject a different requested SHA, archive that commit and invoke its helper. The helper has no inspection-only exit mode. |
| [Release scope review](MASTERmind_1567_RELEASE_SCOPE_REVIEW_2026-10-17.md) | 24,283 bytes; SHA256 `364b24db9b7de5f44fd96cf88eee3d62726edffef6782d000ef68d7ddae9923f` | Accepted #1567 source evidence and the static 298-path rollback gap. This is not an observed transfer count or current-archive approval. |
| [Forward activation review](FORWARD_ACTIVATION_REVIEW_2026-10-18.md) | 14,845 bytes; SHA256 `27a6adb95000dd18a01b1a267c38c9700f05a6e49a8ef67f6130d55a32afb53b` | Concrete initialization-ownership, pending-to-active rollback and baseline/output limitations. |
| [Forward module](source/portfolio/forward_evaluation.py.txt) | 75,128 bytes; SHA256 `19e053bbab9372bfd7c8dd075bfc9a6d3c7ce3450641982086400184a6e07a22` | `init` preserves a valid active marker; `finalize` does likewise; status does not certify a fresh evaluation. Relevant function bodies were read, never imported. |
| [Book locks](source/control_plane/locks.py.txt) | 5,687 bytes; SHA256 `d188aa91c682481c403c5fc0cd383f3956007d5d86b36d701d5920a1e1b5fd54` | Existing advisory `flock` owner and `data/locks/<name>.lock` convention. This file does not itself hold a release-wide lock for the deploy helper. |
| [Runtime qualification](../LIVE_RELEASE_QUALIFICATION_2026-10-18.json) | Parent's dated read-only runtime and namespace receipt | Old runtime `732cf7be…` at 02:42:26Z; active August 11 cohort; marker bytes identical through the canonical path and service mount namespace at 03:06:55Z. |

The release scripts were supplied as identical at installed baseline `732cf7be88e7159b4995a8885fbd381cd1484e3e` and accepted #1567 merge `b08223680180dcffdca7de10b03831dee3e1c287`. Parent has acquired a successor at `d65414e89ad3b930d84d614196a91d3cce8ba589`; this proposal does not assume those old helper bytes are the successor's current bytes until parent binds them.

Parent's complete open-PR census identifies active #1586, head `9b445ac50cffa3c78b8cde190572569d3625c25d`, as an owner of `portfolio/forward_evaluation.py` and its tests. Accordingly, the recommended implementation scope is **the existing deployment helper and its owning deployment tests**, after parent resolves the remaining helper/test custody question. This assignment does not acquire or propose independent writes to that module. The tag helper is read as a dependency; an environment-binding correction there, if needed, belongs to its existing owner rather than a parallel release path.

## Why the fixes belong together

The current helper performs source `rsync`, writes `.deployed_git_sha`, and invokes the optional tag helper before stopping the service. During rollback it can remove `start.json` and restore source before stopping the target service. Moving only the initial stop leaves the rollback interval exposed. Checking only the health return leaves an incomplete restored tree. Expanding only the current list of backup directories leaves the transport and backup policies free to diverge again.

The snapshot's `cp -a` loops also do not make each copy failure fatal. A failure in an earlier iteration can be hidden by a later successful iteration. The script then has no reliable complete preimage for a partial transfer. Finally, rollback logs its health probe but does not include a `503` in its return status. The outer deployment already exits unsuccessfully; the defect is the false implication of verified restoration, not an outer exit-zero claim. These facts are established by the helper and the accepted scope review.

The smallest coherent repair therefore changes one transaction, with the following priorities.

| Priority | Helper change | Useful boundary established | Remaining limitation |
|---|---|---|---|
| P0 | Stop and verify the relevant service/writers before live-tree replacement; stop and verify the target before restoration. | No ordinary source replacement while the protected process is running. | Requires effective stop semantics and actual writer coverage; a successful `systemctl stop` command alone is not universal quiescence. |
| P0 | Use the same explicit exclusion policy for a complete eligible-tree snapshot and restoring that tree, including deletion symmetry. | Every path the transport can add, replace or delete has a corresponding preimage or known prior absence. | Paths outside this tree that the helper changes need explicit preimages; data is not rolled back. |
| P0 | Publish snapshot readiness only after every copy and verification succeeds; preserve the last complete backup until the replacement is complete. | A partial snapshot cannot authorize live-tree mutation. | Host loss and interrupted writes still require reconciliation; no power-loss atomicity is claimed. |
| P0 | Include restore, restart and required health outcomes in the rollback result; centralize failure cleanup. | A failed or unverified restoration cannot be logged as complete. | Network loss can leave outcome unknown; uncertainty must remain visible. |
| P0 | Remove deletion inferred from an earlier absence observation. Preserve unowned or uncertain marker state and report reconciliation required. | The helper does not erase another initializer's authority marker. | This does not make first initialization/pending activation fully reversible. |
| P1 | Qualify the current established-active-cohort upgrade, requiring its marker to remain byte-identical. | The actual upgrade preserves the established evaluation cohort. | Does not qualify a missing, pending, invalid or concurrently changing marker. |
| P1 | Prove release exclusivity through the existing release owner, or repair serialization in the same helper under that owner. | Two deployers cannot interleave stop, snapshot, replacement and rollback. | Current per-book locks and isolated source workspaces do not themselves establish this property. |

## Proposed transaction order

This is a design sequence, not a shell program or a second controller.

1. **Bind the operation before effects.** Retain the wrapper's exact-current configured branch/archive contract. Bind the actual canonical remote/base, expected SHA, code root, live-data root, service and source identity. Validate roots and symlinks so an overridden path cannot redirect a snapshot or deletion outside the declared scope. Establish the actual release-owner exclusivity. Keep no-op admission strict: unchanged source, exact-commit health and the established active cohort; do not equate a zero dry-run line count with general runtime acceptance.

2. **Prepare failure handling before stopping anything.** The existing helper should have one guarded recovery function before its first service mutation. Track in-process facts such as whether stop was attempted, whether a complete snapshot is known, whether tree mutation began and whether the result is committed. These are local control-flow facts, not a new lifecycle store. A lost modifying reply is an unknown result to reconcile on the original operation, not proof that nothing happened. A trap must not recursively trigger itself.

3. **Stop, verify, then perform the pre-mutation gates.** Stop the service under the established release reservation and verify its relevant process/cgroup is stopped. Resolve the actual `KillMode`, `ExecStop`, timeout and detached-writer behavior before claiming quiescence. Check settlement residue and required authority bytes while old code is still the installed code. If a gate refuses, restart the unchanged prior runtime only when its state and the lack of code mutation are known. Do not initiate settlement recovery from this helper review.

4. **Capture a complete code preimage.** Snapshot the receiver's complete rsync-eligible tree, applying the exact same exclusions as the forward transport. The existing protected `.deploy_prev` area can hold the snapshot and small metadata; there is no need for a new release repository, service or queue. A fresh attempt must not destroy the prior complete snapshot before its own snapshot has succeeded. A single explicit failing snapshot operation is preferable to loops whose intermediate failures disappear. Verify the selected tree's path/type/content/mode identity, and publish a readiness indicator only after successful completion. Do not proceed on a merely existing directory or a zero final loop status.

5. **Cover the helper's explicit out-of-band writes separately.** `.deployed_git_sha` is excluded by rsync and needs its exact prior bytes/type or explicit absence retained. The optional `81-datadog-version.conf` also needs an exact preimage if this attempt can change it; deriving a replacement from `PREVIOUS_SHA` is not proof of restoring the prior file. Bind the tag helper's `MASTERMIND_SERVICE` to the chosen service because it is a different environment variable from the deployment helper's service override. Preserve the optional-absent case. No live portfolio data, journal, evaluation snapshot or policy artifact is an assumed rollback target.

6. **Replace source while the service remains stopped.** Mark the start of possible mutation before invoking rsync, because a nonzero/transport-lost result can still mean a partially changed tree. Preserve the current exclusion policy and full archive contract. Write the release marker atomically and invoke the optional tag helper only within this stopped interval. A failed tree copy, provenance write or tag refresh enters the same bounded recovery path.

7. **Apply the existing cohort contract according to the observed state.** For today's valid active cohort, preserve its exact preimage and require the same bytes when verifying the release. It is legitimate for its August 11 deployment SHA to differ from the new code SHA. Existing `init`/`finalize` calls preserve this marker by design; if these are retained, verify that no transition occurred. If an optimization skips the no-op `init`/`finalize` calls on this already-active path, its tests must preserve the same accepted behavior and must not silently divert a changed/missing marker into initialization.

8. **Start the target and verify the actual release.** Preserve exact-commit, reasoning-policy and scheduled-runtime health requirements. A forward `status` success is a cohort check, not a fresh evaluation, calibration or Risk Radar delivery check. Target startup can create durable effects before health succeeds; the active changed dependency set must establish whether previous code can safely read those effects. A code snapshot does not undo them.

9. **Commit success only at the declared boundary.** Keep the healthy-source result separate from cohort state and consumer proof. No additional `start.json` mutation, snapshot generation, model call or portfolio action should be introduced to make an otherwise failing deployment look accepted. Record the bounded result in the existing deployment log/receipt path, with no new operational ledger.

10. **For failures, stop the target before restoring code.** If the target cannot be proven stopped, do not overwrite its live tree and claim a safe rollback. Once stopped and a complete snapshot is known, restore the eligible tree with the same filters and `--delete` semantics; this removes failed-release additions and recreates deleted predecessor paths. Restore the explicit metadata preimages. Only then restart the prior service and verify the declared previous-SHA/policy/scheduler health contract. Any restore, restart, health or marker-state uncertainty makes restoration unverified and the deployment unsuccessful. Retain evidence and use the existing owner for reconciliation.

`SIGINT`, `SIGTERM` and unexpected nonzero shell exits should enter the appropriate recovery branch once, according to whether mutation could have occurred. `SIGKILL`, host loss and network partitions cannot be made transactional by a shell trap. Do not describe these as covered; preserve the original operation and its backup when outcome is unknown.

## Snapshot details that must not be simplified away

The source of truth for selection should remain the existing `EXC` rule set. Both remote snapshot and restoration must receive that same rule set with safe, literal argument handling. The forward transport changes the entire allowed root, not only the repository's changed-file list. A receiver-only `docs/obsolete.md` can be deleted even when no Git deletion appears in the candidate inventory. A newly added `research/new.md` needs removal when restoring a previous tree that never contained it.

Keep excluded material protected throughout both directions. A nested `app/.env`, `app/example.lock` or `data` component must not be overwritten from a whole-directory snapshot after it has changed independently. The current whole-directory `cp -a` restore can include excluded descendants, despite excluding them from the deployment transport. The new selection symmetry must preserve that live material rather than quietly broadening restoration to it.

A directory-to-file or directory-to-symlink change can interact with protected descendants. Do not assume that an ordinary exclusion makes every such type change safe. Require a refusal before live mutation where the intended replacement cannot preserve protected descendants, or supply a demonstrated rsync behavior for the bound version. Verify symlink preservation without following links outside the declared roots. The proposal does not add permission to rewrite unrelated destination files or weaken the existing exclusions.

Do not close the gap by adding only the six currently uncovered roots to `DIRS`, by dropping `--delete`, by restoring only Git-diff paths, or by bypassing the clean-archive wrapper for a two-file production copy. Those choices leave respectively future scope drift, stale executable material, receiver-only deletions, or a different release contract unresolved.

## Marker behavior without taking the forward owner's source

The old helper sets `FORWARD_START_CREATED=1` from a pre-initialization absence probe and can delete the marker on a failed init. Merely delaying the assignment until a successful `initialized:true` response fixes one refusal path but does not prove ownership after a lost response, or protect a marker later replaced by another operation. Matching only the deployment SHA is also insufficient: another operation can use the same SHA.

**Recommended helper-only repair: no unconditional removal or restoration of `start.json`.** Retain the observed preimage/hash and the command/result observations. On an uncertain or changed authority state, preserve it and mark state reconciliation required. This is a repair to unsafe cleanup, not a new authority owner. It preserves successful initialization capability, while making the limitation of a failed initialization explicit.

| Initial state / result | Proposed helper treatment | Qualification status |
|---|---|---|
| Valid active historical marker; normal upgrade succeeds | Preserve exact bytes. Do not demand equality between cohort SHA and new release SHA. | Candidate for this bounded upgrade qualification. |
| Valid active marker; code/health failure; marker unchanged | Restore code only after target stop; preserve cohort and all live data. Verify previous runtime health. | Code rollback can be tested; durable target-start effects remain a separate compatibility question. |
| Marker was absent; init fails or its SSH reply is lost | Preserve whatever marker now exists. Do not turn earlier absence into deletion authority. Code/source restoration and marker uncertainty must be reported separately. | Initialization outcome unresolved until canonical reconciliation. |
| Another initializer's marker is observed; `initialized:false` or refusal | Preserve it whether this attempt received a clean response or not. | No marker cleanup authority. |
| Same-SHA marker was pending; finalization might have occurred before status/transport failure | Preserve current marker and evidence. Do not restore pending bytes or remove an active marker without the actual owner's transition contract. | No complete-state rollback claim. |
| Active marker changed/disappeared during a nominal upgrade | Refuse ordinary success; retain evidence and current state. Do not silently reinitialize or overwrite it. | Outside today's established-cohort qualification. |
| Invalid marker or incomplete required initialization baseline | Retain and refuse the corresponding initialization path. Do not repair baseline contents as part of deployment. | Existing forward owner must define and validate recovery/admission. |

The parent's observed historical baseline has `available` account, decisions, fills, latest, NAV and positions for all three books, and `missing` post-sell artifacts. These statuses do not show that the already-active cohort must be reset. Nor do they prove every baseline source is complete today. The report deliberately preserves the distinction between an optional absent family and an incomplete required baseline.

A future full first-init/pending repair needs positive transition ownership, exact preimages/postimages, a commit point, and serialization with all relevant writers. Those changes belong with the current forward owner. A helper shell `read/hash/delete` sequence is not an atomic compare-and-delete. This proposal must not be used to smuggle that lifecycle repair into an unowned module or to erase forward outputs as a presumed undo.

## Meaningful failure-injection test design

### Harness contract

Extend the existing deployment-provenance test owner after parent reads and binds its actual source. Run the exact candidate helper only after source/workspace and test admission are resolved. Do not import or run `portfolio.forward_evaluation` or the real tag/service commands in this harness.

Use a private temporary fixture with separate source archive, destination code tree, canonical-data tree, systemd-drop-in tree, retained backup and append-only test event trace. Set every supported path/host/service/health/key override explicitly to fixture values; the key is a dummy file. Provide an explicit command search path with fake `ssh`, `rsync`, `systemctl`, `curl`, the expected forward CLI command and bounded test sleeps. The fake SSH endpoint accepts only the one declared fixture host and fixture-root operations, and fails every unknown command. It must never call the real SSH client, systemd, network, provider, credential owner or production path.

The fake rsync should not merely return configured success. Where available, use it as an assertion/recording adapter around an installed local rsync restricted to the private fixture so that filters, type handling and deletion behavior are real. Otherwise separate orchestration tests from unverified transport semantics; a hand-written fake is insufficient evidence for exact rsync exclusion/deletion behavior. Record the rsync version for the semantic tests. This proposal did not inspect tool availability or run a transport.

The fake service maintains a running/stopped flag and a booted-commit identity distinct from on-disk provenance. A simulated old process retains its original identity after a file copy until stopped/restarted. Independent fixture events can introduce a foreign marker, change protected files, append a fake durable output, or fail after a partial copy. Forward CLI results are explicit fixtures from the reviewed contract, not evidence that the real module behaves identically at an unbound successor.

Assert final file content/type/mode and protected-sentinel identity from an independently captured preimage, not only command strings or invocation counts. Assert the service's booted revision and outcome classification. For every recovery failure, test that logs cannot be read as verified restoration. An outer nonzero exit alone does not detect the present rollback-health defect.

### Required cases for the helper repair

| ID | Setup and injected event | Required observation / counterexample retained |
|---|---|---|
| H01 | Valid active historical marker with a different SHA from the target; mixed code additions, replacements and receiver-only deletions. | Successful target boot and exact expected code tree; same cohort bytes; excluded data unchanged. A historical cohort SHA mismatch is not an error. |
| H02 | Exact source, correct target health and valid active marker; then variants with wrong health SHA or pending marker. | Only the fully qualified case is a no-op. Zero dry-run changes cannot independently yield success. No-op performs no stop, tree copy or marker write. |
| H03 | Dry-run fails; service stop fails; or stop reply is lost after a simulated stop. | No live-tree copy before verified stop. Lost reply is reconciled or reported unknown, never treated as verified absence of effect. |
| H04 | Snapshot fails on an early file and would later copy another file successfully. | No release sync/provenance/tag write; readiness false; previous complete backup retained. This reproduces the current loop-masking counterexample. |
| H05 | Existing WAL or top-level settlement receipt for each active book, one case at a time. | Refusal before source mutation; old code remains installed. No automatic settlement/recovery call. Receipt presence is not relabeled from content the helper never examined. |
| H06 | Forward rsync deletes old `docs/obsolete.md`, creates new `research/new.md`, changes `CLAUDE.md`, then fails partway. | After verified rollback, all eligible preimage bytes/types/modes return and failed additions are absent. This must expose the old named-root gap, including destination-only deletion. |
| H07 | Excluded nested `.env`/lock/data sentinel changes after the snapshot; then the release fails. | The newer excluded bytes survive restoration. A broad whole-directory restore that rewinds them must fail this test. |
| H08 | Failure writing `.deployed_git_sha`; tag refresh fails after replacing its file; both optional tag-present and tag-absent controls. | Exact prior provenance and tag preimages or prior absence restored; service remains stopped during restoration. Custom service binding must not touch another fixture service. |
| H09 | Target health times out, reports the wrong commit, false reasoning policy or false scheduled runtime. | No success. Target is stopped before restoring the full eligible tree; previous booted commit and declared health requirements are verified. A still-running old process must not satisfy target health. |
| H10 | Recovery stop fails, restore is partial, old restart fails, or old health remains `503`, separately. | Nonzero deployment and unverified recovery. No `rollback complete` claim. If target stop is unproved, no unsafe restore begins under a running target. |
| H11 | Unexpected nonzero shell exit, `SIGINT` or `SIGTERM` after stop, during source mutation and after target start. | One bounded recovery path, no recursive/double restoration, correct branch for whether code could have changed. No claim to cover SIGKILL/host loss. |
| H12 | Earlier marker absence followed by a foreign same-SHA marker, different-SHA pending marker, or invalid marker; init refuses/returns false/loses its reply. | No deletion or overwrite of any marker. Unknown effect survives as reconciliation required. Checking only SHA or earlier absence must fail this test. |
| H13 | Same-SHA pending marker finalizes successfully; the following status call or SSH reply fails. Also test newly initialized then activated state. | Active/current marker retained, no false full-state rollback claim, no automatic forward-output erasure. This remains a first-init/pending qualification counterexample. |
| H14 | Established active marker changes or disappears before release verification. | No ordinary success and no silent initialization. The current marker/absence is retained for the real owner. |
| H15 | Directory-to-symlink/file change with a protected descendant, a symlink outside the fixture roots, and a plain included symlink control. | Unsafe path/type transition refused before mutation; external sentinel unchanged; supported plain symlink restored with its prior target. |
| H16 | Two deploy attempts overlap around snapshot/copy, if an actual release serialization mechanism is included in scope. | Exactly one mutating attempt; the second refuses or waits within the existing owner contract. If no mechanism is implemented, retain this as unqualified rather than manufacture a passing mock lock. |

H01/H02 are useful success and no-op controls. H04/H06/H10/H12 directly distinguish the proposed repair from the supplied helper's defects. H13 and H16 must remain visible counterexamples if their broader semantics are not repaired in this source slice. Do not count a stubbed successful result as a passed real-module or concurrency claim.

The existing future-date regression tests remain accepted for their original scope; this helper change does not justify rerunning research studies or models. After these narrowly relevant tests and required native gates pass, stop optional testing and move to exact-source/release qualification.

## Acceptance gates and remaining unsafe territory

**Source repair acceptance** requires exact current helper/test custody; old/current/candidate source identity; tests demonstrating the full selected-tree preimage and protected-data invariants; target and rollback ordering; honest restore-health failure; and marker retention on unknown effects. An independent reviewer must be able to distinguish a code rollback from unresolved state without reading a narrative explanation outside the result. Neither passing tests nor merging that change installs #1567.

**Current active-cohort release qualification** additionally requires the actual final full archive and receiver transfer plan; active changed dependencies and installed environment compatibility; exclusive release ownership; real service/writer quiescence; retained restoration artifact and exact out-of-band preimages; proof that startup/durable effects are compatible with the predecessor; exact health and coherent portfolio invariants; and the existing reserved production decision. The two observed source files and historical archive cannot qualify a later full bundle automatically.

**Still unsafe to claim after the helper-only slice:** complete first-init/pending atomicity; all-book and all-caller exclusion during activation; rollback of model calls, settlements, journals or forward snapshots; arbitrary concurrent deploy safety without actual serialization; power-loss recovery; fresh forward-evaluation delivery merely from status; calibrated Grey Deer warning intelligence; installation or end-user acceptance of the future-date fix. The frontend/Copilot source writers and their product gaps remain separate programme work.

## Next action for the parent

Finish the current helper/test target-delta and instruction/custody check, read the existing deployment-provenance tests, and implement the coherent helper slice in the acquired native successor if that scope is clear. Keep the current forward module and accepted evidence immutable. Bind the resulting candidate to the tests above and independent review. Then qualify the actual active-cohort upgrade and complete bundle through the existing release owner; do not use unresolved first-init/pending cleanup or a mock harness as production permission.
