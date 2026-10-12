---
workstream: WS:PROPHET-US-V4-RECOVERY
session: 01a11e89-b35d-7a81-9404-5fce2c6170cb / claude/ssd-prophet-object-change-25b9ad5f52aee56e
model: codex
ended_because: ci_handoff
mission: Finish unblocked four-market Daily Desk gaps while preserving P1a and Daily Brief holds.
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
prs: []
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
unverified:
- claim: Independent review, exact-head CI and source release.
  what_would_verify: Consume original prophet-object-change-review-01a11e89 result, adjudicate exact supplied bytes;
    publish original branch and complete normal exact-head gates and expected-head merge.
- claim: User-facing Daily Brief integration.
  what_would_verify: Resolve original P1a/Daily Brief holds, bind actual native owner validation and caller access,
    then route and browser proof. This module alone is not product acceptance.
unresolved:
- 'P1a PR8444 head a8d84782b3d2f1e6a875012067584c0b4234d7c0: original main-integration operation was refused before
  execution; comment6029541334 remains binding. No retry on this branch or another carrier.'
- 'Daily Brief PR8249 head873ebc4c940d77cf55921b905b3491ab48d6ccbc: original source repair was refused before execution;
  comment5924461491 remains binding. Retain malformed-input red evidence, dirty test extension and all three divergent
  source variants.'
- Daily Brief Task2 comment6027873064 requires actual owner-issued security_id, episode_id, candidate_generation_id
  and market_session plus selection receipt. No ticker/score/order substitute. Assembly/recovery/coverage stay independent
  reads.
- HK and China adoption require actual accepted P1a release. HK preserves PR8136 succession; China preserves PR8184/8270
  and needs seven-lane population/count inputs from existing producer. Canada must show native Plan unavailable
  until its owner exists.
next_actions:
- Complete the independent comparison source component. Route integration stays behind Daily Brief; no fourth assembler.
- Human unblock decision for P1a is the exact original current-main integration refusal, followed by recomputed
  real evidence and ordinary gates; not a waiver of those gates.
- Recommended Daily Brief reconciliation uses the original PR8249 carrier, preserves its pending regression tests
  and ports the distinct quote-clock behavior from R4.8 only after canonical source choice and the original source-edit
  refusal are resolved. Do not create another assembler.
do_not_redo:
- All source/CI/review/render/runtime/live evidence for PR8762/8798/8801/8806/8827/8832/8845/8857 is closed. Retain
  their attached merged worktrees; no reset or reuse.
- No P1a or Daily Brief held effect, foreign Paper effect, denied org403 or /api/health, optional low-memory VPS
  benchmark, D5/private Lab/scientific held work is reopened.
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
