---
workstream: "WS:CI-MERGE-CONTROL-PLANE"
session: "claude/ci-scope-test-reuse-20260927-c3"
model: sol
ended_because: ci_handoff
mission: >
  Continue the Chairman's CI efficiency and autonomous-recovery commission by
  eliminating repeated immutable-tree scope derivation inside the existing
  packing-contract tests without changing production planning or required coverage.
state_before: >
  Thirteen test functions each called infer_job_scopes(load_legacy_jobs(MANIFEST)).
  A two-test baseline at Macro 7bd3ddbb466e4db0e06306728e4710883f477c4b
  computed the identical 237-job result twice, in 174.217s and 33.304s.
changed:
  - path: tests/test_ci_pack.py
    what: >
      Introduce a test-only, module-lifetime lazy scope reader and function-level
      deep copies. Thirteen immutable real-tree consumers reuse it. Actual inference
      occurs after the existing function-level planner-environment isolation. Four
      new tests cover laziness/single computation, deep isolation, fresh readers
      after changed source, and propagated errors. Synthetic/mutating planner tests
      and every production file remain unchanged.
verified:
  - claim: "The baseline performance regression fails for duplicate computation, not a product assertion."
    command: "python3.12 -m pytest -p ci_scope_probe tests/test_ci_pack.py::test_selection_fails_safe_toward_running_everything tests/test_ci_pack.py::test_real_manifest_has_non_vacuous_derived_scopes -q --durations=5"
    result: >
      Baseline: 2 existing tests passed and the added one-computation probe failed,
      213.87s total. Both scope payloads have SHA256
      5af5819c0e8f7618cf67f9a716beb530f50dbab43ba966b3238cb18ea2b2f420.
      Existing shared pytest-temporary-directory cleanup produced 19 warnings;
      no unrelated temporary directory was deleted.
  - claim: "The candidate performs one derivation and preserves the complete measured scope result."
    command: "Same two-test pytest command with the identical measuring plugin and a dedicated basetemp."
    result: >
      3 passed in 111.71s; one actual inference call took 108.563s. The full result
      hash exactly equals the baseline hash. Second-consumer setup took 0.04s.
      The first-call duration varies on a shared host, so the wall-time difference
      is not claimed as an isolated fleet-wide percentage improvement.
  - claim: "The new reader does not share mutable jobs or cache invalid-source failures."
    command: "python3.12 -m pytest tests/test_ci_pack.py -k manifest_scope_reader -q"
    result: "4 passed, 136 deselected in 1.97s."
  - claim: "No existing test assertion or synthetic planner behavior was changed."
    command: "AST comparison of all old/new functions after reversing only the 13 setup-expression and fixture-parameter substitutions; git diff --check"
    result: >
      All 152 existing functions compare identically after that normalization;
      all 129 existing test functions remain, zero removed, four added.
      Diff whitespace check passes. Candidate tests/test_ci_pack.py SHA256 is
      67850466c025ea305826d2b5ac7a17eb600b41e572b6d1e8316cc5037b489589.
  - claim: "The complete six-file hosted packing-contract command passes locally under minimal dependencies and PR-style environment variables."
    command: "minimal-venv/bin/python -m pytest tests/test_ci_pack.py tests/test_run_ci_pack_fetch_fallback.py tests/test_merge_on_green.py tests/test_merge_on_green_semantic.py tests/test_check_conflict_markers.py tests/test_release_hold_text.py -q --durations=15"
    result: >
      563 passed, 2 skipped in 344.54s, process exit 0. Python 3.12.13, pytest
      9.1.1 and PyYAML 6.0.3; GIT_ALLOW_PROTOCOL=file; ambient pull_request,
      pr_head and changed-file variables were supplied. Both skips are existing
      P0B receipt tests requiring the omitted mockups checkout:
      test_p0b_receipt_closure_job_owns_every_receipt_pinned_path and
      test_p0b_receipt_closure_job_would_block_6872_diff_shape. A separate -rs
      run confirmed that reason. They remain required for full-checkout CI.
  - claim: "The candidate integrates the three intervening CI repairs without changing its bounded PR delta."
    command: "git merge --no-commit --no-ff origin/main at 7878cc44564e677057c220fea7f01811ddc32c6c; git diff --cached origin/main; targeted commit/path census"
    result: >
      The merge was conflict-free. PR #8116 cancellation, #8122 shell-comment
      tokenization, and #8131 self-mod payload transport are present. The candidate
      delta against that main remains exactly tests/test_ci_pack.py plus this handoff:
      276 insertions and 26 deletions. Current manifest inference is 237 jobs,
      186 derived scopes, 50 declared exclusive, and 236 scoped jobs.
  - claim: "Every current-main test function is preserved across the integration except the declared fixture substitutions."
    command: "AST comparison of origin/main tests/test_ci_pack.py with the integrated tree, normalizing only the 13 real_manifest_scopes fixture substitutions"
    result: >
      Current main had 157 functions; the integrated tree has 165. Eight additions
      are the test-only reader, fixtures/helpers, and four regressions. Zero current
      functions were removed and zero normalized current functions mismatched.
  - claim: "The complete integrated packing-contract surface passes on the current material base."
    command: "minimal-venv/bin/python -m pytest tests/test_ci_pack.py tests/test_run_ci_pack_fetch_fallback.py tests/test_merge_on_green.py tests/test_merge_on_green_semantic.py tests/test_check_conflict_markers.py tests/test_release_hold_text.py -q --durations=20 --basetemp=/tmp/ci8126-integrated-pytest; focused cancellation tests; check_runner_policy.py; agentos.py validate"
    result: >
      Packing contracts: 568 passed, 2 skipped in 476.89s. The two skips are the
      same sparse-checkout mockups tests and remain owed to hosted full-checkout CI.
      Both cancellation tests passed; runner-policy check exited 0. Agent OS
      validation reported 1,340 records, 0 errors and 119 pre-existing warnings.
      Candidate-only diff whitespace check passed. During the run main advanced
      from 7878cc4 to 453c767 only through a White House alert update; the compared
      CI material paths did not move.
unverified:
  - claim: "Hosted exact-head CI acceptance, including the two full-checkout P0B receipt tests."
    what_would_verify: >
      Consume the source PR's required current-head/current-base GitHub checks and actual
      ci-control-plane-contracts execution. No unrelated suite is waived.
  - claim: "Production latency improvement and independent acceptance."
    what_would_verify: >
      A non-author semantic review, normal release gates, and a subsequent real
      hosted execution of the accepted source with timing and complete coverage.
  - claim: "Autonomous CI repair can safely recover an orphaned worker."
    what_would_verify: >
      Prove exact operation ownership, source custody, result/parent consumption,
      and a bounded repair/recovery path. The restored Executive read endpoint
      alone is not this proof. No modifying CI watcher was armed by this source patch.
unresolved:
  - "PR #8094 remains a separate frozen production optimization; PR #8061's registration mismatch remains with its incumbent carrier."
  - "Two supplemental Studio compound reads were safety-refused before dispatch. Their intended reads were not retried; neither was a source mutation."
  - "The integrated source still owes a new immutable head, hosted full-checkout CI, and independent rereview before release."
next_actions:
  - "Commit and push the conflict-free integration on the existing PR #8126 branch; do not create a replacement carrier."
  - "Bind hosted CI and independent review to the new exact head and current PR base; repair only concrete returned findings."
  - "On concluded-green exact-head evidence, complete normal expected-head release and post-merge readback; retain BUILT_NOT_PROVEN until a subsequent real hosted observation supports PROVEN_LIVE."
do_not_redo:
  - "Do not rebuild #8116's cancellation fix, #8122's tokenizer repair, or expand #8094."
  - "Do not infer runner shortage from a red PR or restore the rejected old self-mod-fence weight 1100."
  - "Do not reuse the test snapshot for production or synthetic/mutable planner inputs."
  - "Do not repeat either safety-refused read through another tool or carrier."
  - "Do not reset, clean, or delete a sibling checkout or its pytest temporary files."
danger_areas:
  - "Module-scoped eager inference before function-level environment isolation recreates the historical PR environment leak."
  - "Shallow result copies permit nested LegacyJob.definition mutations to poison another test."
  - "Later source or dependency movement legitimately changes the scope digest; requalify the integrated tree rather than pinning a stale count."
---

# CI scope-test reuse — source and proof frontier

MISSION_COMPLETE: false
CAPABILITY: BUILT_NOT_PROVEN
OPERATION: ci-scope-test-reuse-20260927-c3
PARENT_OPERATION: ci-fleet-efficiency-audit-20260927

Protected procedure: Mastermind
`5c6b010a6157895d4f697548c75263cdff641ea6`, Skillpack 1.0.1,
INDEX blob `94d1af402598894372858793a5b1931019c5fa77`.
Original source base: Macro `7bd3ddbb466e4db0e06306728e4710883f477c4b`.
Current integration parents: candidate `ecb8753f71f14bf7cb06fe571010eae64111452d`
and material main `7878cc44564e677057c220fea7f01811ddc32c6c`.

The workspace is the locked linked worktree under the canonical Macro root:
`/Users/chriswong/Documents/Cluade/macro-main/.claude/worktrees/ci-scope-test-reuse-20260927-c3`.
Only this operation owns that branch. A checkpoint does not transfer its custody.

The disposable baseline/candidate instrumentation and original local receipts are
in `/tmp/mmx-ci-continuation-20260927-c3` on the Studio host. Their decisive
outputs and limitations are embedded above; this temporary path is not a second
canonical evidence store. The actual source PR and its checks are the release
carrier. Full packing-contract log SHA256: 653d690428ebd3937427213a00d428dcbe902ec237e1ba33f623484cadf94e4b. No runner, cache service, workflow, manifest, cancellation policy,
retry policy, merge policy, provider account, or production deployment is changed.

The Executive reader responded successfully at 2026-09-28T02:44:22Z in readonly
mode, grounded in Mastermind `aebb2ed19e68bda072e38221638925d674b656dc` and
Macro `88804ed7079700c598bb8e04aa64307d1335402d`. Its exposed registry contained
one failed job and no running attempts; that scoped registry is not a census of
all GitHub builders or evidence that existing source leases have expired.
