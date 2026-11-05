# Mastermind #1567 — forward-evaluation activation and rollback

**18 October 2026 UTC · Bounded source review · No runtime execution**

**Disposition: preserve the accepted #1567 source repair; full release and runtime acceptance remain open.** The forward-evaluation module has useful cohort and publication protections, but the deployment transaction does not completely own or restore marker state. A prior pending marker can remain active after a failed release, and an initialization failure can remove a marker that this deployment did not create. These are source-supported failure paths, not claims that either occurred on the VPS.

This addendum follows `MASTERmind_1567_RELEASE_SCOPE_REVIEW_2026-10-17.md`. It does not repeat that review's 298-path rollback coverage finding or change the recorded `autonomous_production_deploy: prohibited` boundary. No first-party code was imported or executed; no CLI, live data, Studio, Git, network, browser, deployment or recovery operation was used. Only the supplied local source and prior review were read. The parent's source retrieval establishes the two-pin identity below; local byte counts and SHA256 were independently checked.

## Source identity and citation key

| Key | Exact source | Identity |
|---|---|---|
| **F** | `portfolio/forward_evaluation.py` | Same supplied Git blob `ef9944ebed235803ea32e7532c0a03884675cc69` at observed baseline `732cf7be88e7159b4995a8885fbd381cd1484e3e` and accepted merge `b08223680180dcffdca7de10b03831dee3e1c287`; 75,128 bytes; SHA256 `19e053bbab9372bfd7c8dd075bfc9a6d3c7ce3450641982086400184a6e07a22`. |
| **D** | `scripts/deploy_code_to_vps.sh` | Same source at those pins according to the preceding review; supplied local file 14,934 bytes; SHA256 `c158fc903121b8c4ad680049ded16000913393039944c6eec3a23d44ca376204`. |

References such as **F:519–557** below mean numbered lines in those exact files, not current branch contents. Source identity does not establish the current installed module, effective service environment or all imported dependencies.

## What the deployed commands actually do

| Command / boundary | Behavior established by source | Acceptance limit |
|---|---|---|
| `init --deployment-sha … --asof …` | For an absent marker, read seven local artifact families per active book; retain five families of legacy row identities/hashes plus input statuses; create `portfolio_forward_evaluation/start.json` once as `pending_health`. A valid active marker is preserved across later deployment SHAs. A pre-existing pending marker with a different SHA is refused; an invalid existing marker is refused rather than reset. **F:231–270, 407–438, 519–557.** | No source-health gate rejects missing, invalid or partial baseline input statuses. No lock is acquired inside the module. The wrapper's stopped-service assumption supplies baseline quiescence. |
| `finalize --deployment-sha …` | A matching pending marker becomes `active` and gets `health_verified_sha`; a valid active marker remains unchanged. The write is reread and compared. **F:560–577.** | This command does not probe health or take a lock itself. `health_verified_sha` records the caller's assertion after its separate health gate. It is not an independently measured attestation from this module. |
| Global `status` | Read marker and existing per-book snapshots/run-status artifacts; return top-level `started` when the marker is valid and active. The CLI returns 2 for `not_started`/`unknown_book`, otherwise 0. It never calls `evaluate` for this command. **F:1597–1701, 1704–1735.** | An active marker passes global status even when all books are `awaiting_first_post_mark_snapshot` or have `stale_after_error`. No current-release SHA argument, snapshot freshness threshold, book equality check or completed evaluation is required. This is a cohort-start gate, not delivery or performance acceptance. |
| Release data root | Only CLI `init`, `finalize` and `status` use `MASTERMIND_FORWARD_EVALUATION_RELEASE_STATE_ROOT`; the override must be absolute. Scheduler/API calls and CLI `run` retain the ordinary registry-root `data` namespace. **F:58–85, 1719–1723.** | The helper consistently passes its live-data path (**D:81–86, 285–289, 328–331**), but equivalence with the service's actual mount namespace still requires the effective unit/drop-ins. |

The creation helper writes and file-fsyncs a temporary file before publishing it with an exclusive hard link; it does not overwrite an existing destination. The replacement helper uses a temporary file and `os.replace`, then its callers reread the marker. These protect complete-file visibility in ordinary operation. They do not provide a multi-process transaction or, without directory fsync and replacement-file fsync, establish power-loss durability of the whole transition. **F:441–481.**

The normal evaluation path refuses future dates, archived/unsupported books and missing/pending cohort authority before writing a snapshot. It publishes dated snapshots, latest pointers, correction receipts/prior revisions and run status only within the forward-evaluation output tree. Its returned authority is observational, and Prophet comparisons remain explicitly non-causal. These are useful boundaries within this module; the imported registry/package initialization remains an actual unreviewed dependency. **F:37, 1421–1448, 1473–1591.**

## Actionable transaction defects

### 1. Deletion ownership is inferred before successful initialization

The helper records marker existence before backup and source replacement (**D:132–139**). If that earlier observation was `missing`, it sets `FORWARD_START_CREATED=1` before calling `init` (**D:281–289**). An unsuccessful init/SSH command immediately enters rollback (**D:285–292**). Rollback deletes `start.json` solely from that flag, without checking its deployment SHA or identity (**D:156–161**).

A concrete source path is: the existence probe sees absence; another initializer creates a valid pending marker for a different SHA; this init reads it and refuses (**F:530–535**); the failed command bypasses the later ownership correction and rollback removes the other marker. The flag is corrected when successful init output says `initialized:false` (**D:294–298**), but that does not protect the failure path. Conversely, an earlier `present` observation cannot identify a subsequently recreated marker as owned by this attempt.

**Required bounded repair/qualification:** removal must be conditional on positive ownership and unchanged marker identity at removal time. Initial absence alone cannot establish ownership. Preserve the existing successful concurrent-initializer protection and test refused-init/transport-failure paths; do not introduce a blind marker reset or delete another attempt's state. This review does not implement that repair or acquire its writer scope.

### 2. A pre-existing pending marker can remain active after rollback

For a valid pending marker belonging to the same SHA, `init` preserves the original marker (**F:530–535**). Because the marker was already present, the helper's creation flag remains zero. After exact-commit health and the US hash comparison, `finalize` changes it to active (**F:560–577; D:309–331**). If the following status command or SSH transport fails, the helper invokes rollback (**D:332–335**), but it neither restores the prior pending bytes nor removes this marker: its only marker undo is the creation-flag branch. The marker is in the live-data tree, outside the code backup (**D:90–103, 156–192**).

This is a state-transition gap even without concurrent writers. The deployment can fail and restore source while leaving newly active cohort authority from that attempt. An already active historical cohort is a different case: preserving it across later deployments is the intended behavior and must remain intact.

**Required bounded repair/qualification:** define the release commit point and retain the exact pre-transition marker identity. A failed attempt must account for a pending-to-active transition it performed, with an identity check that protects later legitimate changes. Verify failure after successful `finalize`, not only failure before initialization. Do not reset established active cohorts.

### 3. Marker rollback does not establish forward-output rollback or cohort consistency

When a newly created marker is removed, existing forward snapshots, revisions, correction receipts and run-status artifacts remain outside the code restore scope. Initialization checks the marker, not those output directories (**F:519–557; D:90–103, 156–192**). `load_snapshot` validates JSON object/schema only; `_book_status` does not compare the saved snapshot's `cohort` with the current marker before presenting it (**F:1597–1663**).

The module also permits an in-flight `evaluate` call that already read an active marker to persist after marker removal: it passes the cached marker into `build_snapshot` and does not recheck authority before `_persist_snapshot` (**F:1013–1018, 1581–1590**). The helper does not stop the service before removing the marker/restoring code during rollback (**D:152–190**). Whether a real scheduler can enter that interval depends on its caller locks and service topology, which were not supplied.

**Consequent limit:** code restoration plus marker deletion is not proof that a failed release left no forward artifacts, or that a later new marker's status cannot expose an older cohort's snapshot. Qualify the actual scheduler/lock path and define how retained outputs are attributed across failed attempts. Preserve correction lineage; do not erase ledgers as an assumed undo operation.

## Baseline completeness and invariant coverage

`_read_inputs` converts unavailable/unreadable objects to missing/invalid statuses, and partially parsed JSONL retains valid rows. `_baseline_for` records these statuses and whatever row identities were readable; `initialize_start` and `load_start` do not reject those statuses. Validation checks that required row-ID/hash fields are lists, not that the baseline was complete or that counts and hashes reconcile. **F:139–174, 231–270, 407–438, 484–557.**

On later evaluation, the exclusion test uses baseline `row_ids` and an inclusive date window. It uses current input statuses without carrying the original baseline's missing/partial status into cohort admissibility. Thus a recovered row from an unreadable baseline artifact can be counted as forward if its date is within the cohort window, particularly the start date; a row strictly before the start date remains excluded by the date condition. **F:606–618, 1030–1049.** This is a specific completeness gap, not a claim that every absent optional artifact must block a fresh book.

The release owner should declare which baseline sources may legitimately be absent and refuse or explicitly quarantine incomplete required baselines. Recording an error status alongside an empty exclusion set is insufficient to assert that all pre-existing rows were excluded.

| Artifact / invariant | What the current source enforces | What remains unproved |
|---|---|---|
| US account and fills | Both files must exist/read; byte hashes are captured after the service stop and compared after health while holding `book:autonomous.lock`. Missing files, changed bytes or lock acquisition failure refuse activation. **D:260–279, 313–334.** | The bytes need not be valid JSON/complete JSONL to pass this shell check. The comparison spans this attempt, not the earlier baseline of a reused pending marker. All actual writers honoring the same lock is unverified. |
| China/HK account and fills | Marker initialization reads their artifact statuses and available baseline rows. The settlement-presence gate includes all three books. **F:43, 231–270, 545; D:238–250.** | No corresponding before/after account/fill hashes or China/HK locks appear in this release transaction. The shared marker activates all three books. |
| Decisions, NAV, positions and post-sell artifacts | Available legacy identities/hashes are retained in the marker. **F:407–438.** | Reads are sequential and have no module lock; there is no final byte comparison for these artifacts. The service stop's coverage of every relevant writer remains unverified. |
| Marker and forward outputs | Pending authority blocks ordinary snapshot writes; existing active cohorts are preserved; same-asof changes keep prior revision/correction records. **F:1491–1521, 1581–1590.** | There is no release-wide coherent snapshot/restore of this tree, and global status does not certify a completed or fresh evaluation. |
| Policy, prompts, other journals, risk-consumer output | None is changed by the reviewed init/finalize/status function bodies. | The full release may affect them elsewhere. The module and two US byte checks cannot establish their parity, investment-policy validation or end-user delivery. |

These are portfolio forward-evaluation mechanics. Their activation is not evidence that Risk Radar's separate prospective warning log has genuinely issued, and does not admit a Grey Deer forecast, allocation or trade.

## Only the next actual dependencies

1. **`portfolio/__init__.py` and `portfolio/registry.py` at both pins**, then the effective service unit/drop-ins. Python's package/module entry and the explicit registry import are on every invoked CLI path. Resolve import effects, book metadata/root paths and the actual canonical-data bind mount; do not infer these from comments.
2. **The resolved service entry point, health handler and actual forward-evaluation callers/lock implementation.** Find the callers of `evaluate`/`run`/`record_failure` and the implementation owning `book:autonomous.lock`. This determines quiescence during init, whether US/China/HK writers or evaluators can run before activation/rollback completes, and what the health fields attest. No entry-point filename is guessed here.
3. **The canonical settlement reader/recovery source located by `paper_transaction.json` and `settlement_receipts`, plus `scripts/refresh_datadog_release_tag.sh`.** These were already directly warranted by the helper. Read their exact pinned effects; execute neither recovery nor tag refresh as part of qualification.

The parent can now carry the concrete marker-ownership, failed-activation and baseline-completeness findings to the existing release qualification. A future production decision must bind the exact then-current bundle and effective runtime, not silently reuse `b0822368…` evidence for a later archive. The previously accepted narrow source repair remains accepted; this addendum grants no deployment permission and makes no current-VPS or complete-release claim.
