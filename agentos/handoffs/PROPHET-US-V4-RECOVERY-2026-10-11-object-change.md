---
workstream: WS:PROPHET-US-V4-RECOVERY
session: 01a11e89-b35d-7a81-9404-5fce2c6170cb / claude/ssd-prophet-object-change-25b9ad5f52aee56e
model: codex
ended_because: ci_handoff
mission: Finish remaining four-market Daily Desk gaps on their original carriers under the two explicit human reopen approvals.
state_before: B03 and Return to candidate are accepted live and closed. Shared four-market UI and Daily Brief route
  remain held on their original carriers.
changed:
- path: engine/prophet_object_change.py
  what: Pure presentation comparison of one explicitly supplied native object at a time, with closed shape checks,
    exact owner/object/candidate binding, separate original clocks and detached before/after records. No source
    or review acceptance is inferred.
- path: tests/test_prophet_object_change.py
  what: Exercise quote/assessment/Plan changes, malformed/failed reads, four-market isolation, separate clocks,
    missing review lineage and immutable results.
- path: .github/ci/legacy-jobs.yml
  what: Add the independent object comparison module and test selectors plus one proof step to the existing prophet-lab
    code gate.
prs: [8874]
verified:
- claim: The new comparison has an executing PR-time code owner.
  command: scripts.run_ci_pack.load_legacy_jobs(.github/ci/legacy-jobs.yml, gate=code) and select_jobs independently
    for module and test paths.
  result: 207 code jobs validate; prophet-lab selected for both paths. This is local plan ownership only, not terminal
    CI.
- claim: Returned artifact bytes were retrieved through the original admitted Fabric carrier.
  command: fabric_task.py result and artifacts prophet-object-change-build-01a11e89 with exact root, parent, ubuntu1
    and stdout digest.
  result: Terminal rc0. Retained stdout3410B SHA0c39738e9bfbd9ecf8ce90a31c79a9e455bad51eb06a6931a7e871cf4f239584.
    Export COMPLETE, producer_contract_verified true; artifact39914B SHA940deb32e5288c1e1aa9ed1e234fab29fa4731dcc07d40e4f779b829124e0e39.
    No historical-worker-byte attestation or usage/cost claim. Parent integration repairs remain separate.
- claim: Parent regression cases detect the returned draft defects before repair.
  command: python3 -m pytest tests/test_prophet_object_change.py -q with original returned module and expanded tests;
    object-change-parent-red-20261012.txt.
  result: 8 failed,86 passed. Two oversized numeric inputs raised OverflowError; six blank identity/receipt/review
    fields produced false unchanged results.
- claim: Final focused behavior passes after the bounded parent repair.
  command: python3 -m pytest tests/test_prophet_object_change.py -q; object-change-parent-green-20261012.txt.
  result: 94 passed,0 skipped,0 deselected. One unrelated old pytest temporary Chromium cleanup PermissionError
    warning. Input data and held owners untouched.
- claim: The bounded existing-manifest changes preserve code-gate behavior.
  command: python3 -m pytest tests/test_ci_pack.py -q -k "manifest_job_local_delta_is_bounded_to_changed_job or
    manifest_multiple_job_local_deltas_are_all_forced or manifest_job_delta_rejects_topology_gate_and_top_level_changes
    or no_hash_token_inside_folded_run_scalar_in_legacy_jobs_manifest or prophet_chronology_suites_run_in_the_code_gate"
  result: 5 passed,163 intentionally deselected. Canonical manifest validate-only succeeds.
- claim: Independent review accepts the exact comparison module and test bytes.
  command: fabric_task.py result and accept prophet-object-change-review-01a11e89 --by reviewer;
    object-change-review-adjudication-20261012.json; PR8874 comment6115543664.
  result: APPROVE; independently recomputed source/test hashes, 94 passing tests and 3664 probe calls. Canonical
    VALIDATED_OUTCOME on original root and parent. This two-file scope is not repository wiring or production proof.
- claim: First exact-head hosted CI is not clear; the local diagnostic identifies the missing dependency.
  command: load_semantic_evidence for CI38187164735/head2bdef9328e5dc0ee88106fb5ff5a17288dd04c5d;
    python3 -m pytest tests/test_ci_pack.py::test_curated_exclusive_scopes_cover_their_own_import_closure -q.
  result: Canonical hosted evidence has 88 logical jobs, 295 passing proof steps, 15 blocking and no inherited
    failures. Object-comparison proof passed. Local unchanged closure test fails because dataos-prospective-reference
    omits lib/nyse_calendar.py, imported by scripts/build_ext_quotes.py. Hosted classification remains unknown
    because head and exact-base failure signatures differ; no inherited waiver.
- claim: The existing upstream owner already supplied the dependency repair.
  command: git show de0c202a016502ce521db66a70e5905b76e0c9c2 -- .github/ci/legacy-jobs.yml;
    git merge --no-ff --no-commit 6361f5e0e071dfc050c503e225afe8a4897f0e8d.
  result: PR8870 adds lib/nyse_calendar.py to the original job scope. Normal current-main composition is conflict-free;
    comparison module/test bytes remain exact reviewed bytes. No checker or allowlist change.
- claim: Composed closure and bounded manifest behavior pass after consuming the upstream repair.
  command: python3 -m pytest tests/test_ci_pack.py -q -k "curated_exclusive_scopes_cover_their_own_import_closure
    or manifest_job_local_delta_is_bounded_to_changed_job or manifest_multiple_job_local_deltas_are_all_forced
    or manifest_job_delta_rejects_topology_gate_and_top_level_changes or no_hash_token_inside_folded_run_scalar_in_legacy_jobs_manifest
    or prophet_chronology_suites_run_in_the_code_gate"; python3 scripts/agentos.py validate.
  result: 6 passed, 162 intentionally deselected in 148.30s; Agent OS has 0 errors and 110 existing warnings.
    Canonical manifest validates 209 code jobs. Parsed manifest equals pinned main except the two owned selectors
    and one proof step. Exactly five owned paths differ from pinned main. This is local composition proof, not new hosted CI.
unverified:
- claim: Repaired exact-head CI and source release.
  what_would_verify: Complete composed local proof, publish the original branch, consume new exact-head terminal
    semantic CI and normal gates, then fresh-main compatibility and expected-head squash.
- claim: User-facing Daily Brief integration.
  what_would_verify: Complete the approved original P1a/Daily Brief repairs, bind actual native owner validation and caller access,
    then route and browser proof. This module alone is not product acceptance.
unresolved:
- 'P1a PR8444: human explicitly reopened only original current-main integration, superseding refusal6029541334.
  Original merge exec22293 is active against pinned main1df533de2847fd71bbddaad401e722393c007919. Preserve the
  process and lock; do not duplicate/reset/abort without actual-state adjudication. Recomputed artifact, review,
  CI, merge and live proof remain owed.'
- 'Daily Brief PR8249: human explicitly chose this original implementation and reopened refused repair5924461491.
  Original Fabric prophet-daily-brief-repair-01a11e89/exec46885 remains active. Preserve original 40-line dirty
  regressions and exact input hashes; consume returned artifact once, integrate, prove and independently review.
  R4.8 contributes its distinct independent quote-clock behavior; third variant remains preserved.'
- Daily Brief Task2 comment6027873064 requires actual owner-issued security_id, episode_id, candidate_generation_id
  and market_session plus selection receipt. No ticker/score/order substitute. Assembly/recovery/coverage stay independent
  reads.
- HK and China adoption require actual accepted P1a release. HK preserves PR8136 succession; China preserves PR8184/8270
  and needs seven-lane population/count inputs from existing producer. Canada must show native Plan unavailable
  until its owner exists.
next_actions:
- Complete the independent comparison source component. Route integration stays behind Daily Brief; no fourth assembler.
- Continue both explicitly approved original operations; no new human decision is needed for those repairs.
- Today/standouts already owns selection and ordering in scripts/build_stock_library.py::main. Obtain native
  four-field object binding before that actual producer issues provenance for its unchanged selection. The Task2
  consumer cannot issue selection, and prophet_bridge.select_candidates is not a replacement selector.
do_not_redo:
- All source/CI/review/render/runtime/live evidence for PR8762/8798/8801/8806/8827/8832/8845/8857 is closed. Retain
  their attached merged worktrees; no reset or reuse.
- Only P1a refusal6029541334 and Daily Brief refusal5924461491 were superseded by explicit human approval.
  Foreign Paper effect, denied org403 or /api/health, optional low-memory VPS benchmark, D5/private Lab/scientific
  held work and all other denials remain closed.
- CI38187164735 status, plan, final semantic artifact, fences, authority, pilot and independent comparison review
  are consumed and closed. The local red log provides the dependency diagnosis; do not repeat the refused failed-job
  log request without a new diagnostic need. A new source head requires new exact-head CI.
- One existing observer prophet-r6-source-clock-delivery remains the continuity path; no new watcher or generic
  status pings.
danger_areas:
- A pure comparison cannot authenticate owner/review receipts. Future caller must use its native validators and
  access owner before normalization.
- Changed means supplied facts differ, not a trading recommendation, fresh entry verdict, newly accepted assessment
  or reconstructed history.
- Cross-candidate-generation comparisons stay unavailable without a separately accepted native relation. Source-generation
  receipt movement alone is not economic change.
---

The current implementation phase is independent preparation for the selected Daily Desk workflow.
It does not establish route integration or new production acceptance.
