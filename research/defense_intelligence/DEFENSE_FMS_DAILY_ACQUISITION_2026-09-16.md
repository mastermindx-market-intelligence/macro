# Defense Intelligence: unattended FMS acquisition continuation

Operation: `defense-fms-unattended-freshness-20260916-sol-001`.
Parent: `WS:DEFENSE-PROCUREMENT-V3`. Sol retains delivery and acceptance.
Source base: `aad0aaf33810c881a2da398380930eb50a9cdeda`.
Protected procedure: Mastermind `0fe8074ff953b2ced9025ed40f0f66019c759967`, Skillpack 1.0.1/bootstrap 1; INDEX, COLD_START, ACTIVE_EXECUTION, WEB_CEO_DELEGATION, RECONCILE_STATE and CLOSEOUT atomically loaded.

## Mission and authority

Maintain the accepted foreign-military-sales notification input without requiring a manual dispatch every day. This supports the investor's defense demand and export-policy context; a notification remains a proposed sale, not revenue, a funded order, or a trade signal.

The current Chairman continuation supplies intent. D6-B1 spec section 10 explicitly leaves cadence to Sol. This change selects one daily check at **10:43 UTC**, retaining manual branch dispatch. It does not replace any source, extend the population window, relax entitlement, or change the congressional-notification stage.

Direct work rationale: CRITICAL_PATH_SHORTCUT. This small existing-workflow change and its contract tests are cheaper than dispatch/review overhead. No Fable capacity, worker Job, source-custody transfer, new watcher, retry engine or provider account is used.

## Implementation boundary

The existing `fms-acquire.yml` workflow remains the only acquisition carrier. Scheduled runs select the repository default branch; manual runs retain the explicit ref. One quoted environment variable binds checkout and push. A branch-format check precedes acquisition. Shell-special characters in a valid ref are treated literally, not evaluated.

The runner labels, 30-minute timeout, four-file write allowlist, R2 store/readback path, shared `government-revenue-live` concurrency group and `cancel-in-progress: false` are unchanged. The separate Government Revenue publisher remains the sole site writer. This PR does not touch its candidate-collection repair (#7186).

An always-run Actions summary records the acquisition-step outcome, commit-step outcome, and whether projection files changed. It does **not** infer a new notification from a success or a changed generated timestamp. The existing collector may rebuild projection metadata while retaining identical observation/receipt histories; a clock-only output change is not fresh source evidence. Workflow history is the check receipt; no second health store is introduced.

## Tests and exact limits of proof

Before implementation: 11 new failures and one preservation control passed. After implementation: all 12 cadence tests passed. Full existing `tests/test_fms_notifications.py`: **83 passed**, including its later-clock repeated-input receipt/observation test. Commands used `python3 -m pytest ... -q --tb=short --basetemp=.pytest-local/<run>` in the isolated approved external-SSD worktree.

The new tests execute the actual workflow shell against disposable local bare Git repositories. They prove literal branch targeting, four-file publication, no commit on an unchanged working tree, refusal of unrelated files, invalid-ref refusal before acquisition, and honest success/failure summaries. They perform no remote push, live source fetch, real R2 write or production authentication. Passing these tests is not a natural scheduled-run receipt.

## Source custody, failures and acceptance

A path-scoped census checked 245 open PR heads for the workflow and test file; four missing local heads were resolved with their exact GitHub changed-file lists. No overlapping writer appeared in that census. The new workspace was created by the installed external-SSD storage helper, based on fresh main; neither the occupied primary nor #7186's source was modified.

At the preflight read, the latest FMS run remained `32961001544` from August 26. The latest ten runs of each shared-group workflow (`fms-acquire.yml`, `government-revenue-live.yml`, `dod-budget-acquire.yml`) contained no unfinished run. That is a dated preflight, not permanent permission to dispatch.

A separately reconciled one-shot refresh may use the **already released** acquisition workflow on main; it does not require executing this unmerged cadence candidate. Before that effect, recheck the shared group and the intended main revision; submit once and identify the exact returned run. A timeout or absent immediate run is effect-unknown, not permission to submit again. Record the actual run, source version, acquisition/readback/commit outcomes and source-health limits in the same PR receipt. No such refresh is claimed by this document at authoring time.

Stop the source lane on an unexpected path change, unavailable store, coverage refusal, unreconciled prior effect, or failed push. Never force-push, replace the previous evidence, invoke another collector, or count an unsuccessful source check as an empty valid population. Preserve the existing staged-DSCA/State scope and FR reconciliation law.

Release acceptance is: exact-head applicable CI and source review; normal merge; one actual scheduled default-branch run using the existing runner/store; no duplicate observations under repeated bytes; truthful check/commit outcomes; then the existing single publisher and entitled consumer read the corresponding graph. A successful manual refresh proves that invocation only, not an installed daily schedule or a healthy UI.

The command/notification stage, evidence known-at, publication date, graph generation time and workflow check time remain different facts. No forecast, expectation gap, entry, trade ranking, sizing, gate, or portfolio authority is enabled by this source-maintenance capability.

## Continuation

Keep #7186 on its existing branch/head until its release gates and production proof clear. Keep the financial qualification and four-company journey with the existing Earnings/Company Intelligence and D5 owners. D5 v1 requires human admission of program/role records; do not relabel model research as a human review or automatically promote a proposed map. Optional source expansion must not replace the investor workflow.

The next FMS action is to reconcile the actual latest source run, complete ordinary release of this same cadence carrier, and prove its first scheduled invocation. The next investment-intelligence action is the munitions program/company attribution and typed financial bridge, with primary-source scope and current expectations kept explicit. The Defense program remains open.
