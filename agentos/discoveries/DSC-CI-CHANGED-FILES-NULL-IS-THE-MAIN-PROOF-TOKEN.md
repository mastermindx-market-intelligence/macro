---
key: CI-CHANGED-FILES-NULL-IS-THE-MAIN-PROOF-TOKEN
claim: >
  The planner's changed-file handle (`CI_CHANGED_FILES_FILE`) legitimately holds
  the literal token `null` (full suite, no changed-file list) on EVERY main-role
  ci.yml plan and in the base replay, so a pack step that refuses `null`
  unconditionally reds every main proof. A main plan must carry no changed_from
  (scripts/run_ci_pack.py:2162). The base replay writes "null\n" for its child
  with GITHUB_EVENT_NAME=base_replay (run_ci_pack.py:4472, :4533). A pr_head plan
  with no list raises ManifestError (run_ci_pack.py:2154), so on a pull_request
  `null` only ever means the planner failed. Measured: #7237 (10fc49afe17f) made
  scripts/check_p0b_receipt_closure.py refuse `null`, and the next main dispatch,
  run 36357668603 at dcc6eb378ff7, went red on ci-pack-11 / p0b-receipt-closure
  with "REFUSED: planner changed-file handle is null / unavailable".
falsifier: >
  A workflow_dispatch ci.yml run on main whose ci-plan writes a real path list
  into CI_CHANGED_FILES_FILE; or run_ci_pack.py no longer writing "null\n" for the
  base replay; or a pull_request plan that publishes `null` without a
  ManifestError. Quick check: python3 -m pytest tests/test_ci_pack.py -q -k
  null_on_exactly_the_events_that_publish_it (it asserts the producer side and
  the p0b allow-list against run_ci_pack.SUPPORTED_PLAN_ROLE_EVENTS).
so_what: >
  A new consumer of CI_CHANGED_FILES_FILE must read `null` as "no list" and decide
  by event. Accept it on the main-role events (workflow_dispatch, workflow_run,
  schedule) plus base_replay, and refuse it on pull_request. Take the event as an
  explicit argv flag, `--event "${GITHUB_EVENT_NAME:-}"`, never from os.environ
  inside the checker. Its own unit suite runs inside the main proof's pack with
  GITHUB_EVENT_NAME=workflow_dispatch, so an env read silently relaxes those
  tests. The stakes are high because ci.yml has no push trigger: main is proven
  only by dispatch. A consumer that refuses `null` leaves main unproven, which
  freezes every authority-changed merge (they clear only on a main-descendant
  ci.yml SUCCESS) and starves the sweeper's base-inherited-red refresh. When a
  main proof reds with a null-handle refusal, look at the consumer, not the
  planner. The consumers that already handle `null`:
  check_conflict_markers.planner_changed_paths (treats it as an empty list);
  check_self_mod_fence (returns ok, []); check_p0b_receipt_closure (the --event
  allow-list from #8114).
kind: landmine
verified_at: 2026-09-27
verified_by: >
  Run 36357668603 ci-pack-11 log (the only failing step). Code:
  scripts/run_ci_pack.py:2154, :2162, :4472, :4533. Consumer census:
  git grep -n CI_CHANGED_FILES_FILE -- .github/ scripts/. Heal PR #8114 (merged
  de81c74c81ab), CI run 36361971686 success: it adds
  tests/test_check_p0b_receipt_closure.py::test_cli_accepts_null_handle_on_a_main_role_event,
  ::test_cli_still_refuses_null_handle_off_the_main_role_events,
  ::test_cli_never_reads_the_event_from_the_environment, and
  tests/test_ci_pack.py::test_p0b_closure_accepts_null_on_exactly_the_events_that_publish_it.
scope: [macro, "scripts/run_ci_pack.py", ".github/ci/legacy-jobs.yml", "scripts/check_p0b_receipt_closure.py"]
confidence: verified
---

# `null` in the changed-file handle is the main proof's token, not an error

The planner hands every pack its changed-file list through one file,
`CI_CHANGED_FILES_FILE`. On a pull request that file holds the PR's paths. Three
producers write the literal token `null` instead:

1. **Main-role plans** (`workflow_dispatch`, `workflow_run`, `schedule`). A main
   plan proves one identical tree/head/base SHA and must carry no `changed_from`,
   so it has no list. It runs the full suite.
2. **The base replay.** `run_ci_pack.py` replays the base tree with
   `GITHUB_EVENT_NAME=base_replay` and writes `"null\n"` for that child.
3. **The ManifestError widening path.** It publishes an empty `plan_sha`, so
   `ci-gate` blocks by construction anyway.

A `pr_head` plan with no list raises `ManifestError`, so on a pull request `null`
really does mean the planner broke. #7237 was right to refuse it there. It was
wrong to refuse it everywhere. Main is proven only by dispatch, and every dispatch
publishes `null`, so a blanket refusal reds every main proof. Every
authority-changed merge then stays frozen until someone finds the consumer.

The #8114 shape: the step passes `--event "${GITHUB_EVENT_NAME:-}"`, and the
checker holds an allow-list (`NO_DIFF_SUBJECT_EVENTS`) that a test pins against
`run_ci_pack.SUPPORTED_PLAN_ROLE_EVENTS` main roles plus `base_replay`.
`pull_request`, an empty event and unknown events keep the refusal.
