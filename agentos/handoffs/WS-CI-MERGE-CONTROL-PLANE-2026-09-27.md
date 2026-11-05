---
workstream: "WS:CI-MERGE-CONTROL-PLANE"
session: >
  worktree dazzling-yonath-b270fb; branches claude/contract-delta-control-plane-classes
  (#8102), claude/p0b-null-handle-main-events (#8114), and
  claude/agentos-ci-null-handle-records (these records)
model: opus
ended_because: complete
mission: >
  Add three whole-tree shapes as differential classes to ci.yml's contract-delta
  job (scripts/check_contract_delta.py). A PR must red on its own head when it
  breaches a packing-probe ceiling (templates/index.html 134 jobs / 5,800 s,
  scripts/build_free_content.py 132 / 5,600, engine/prophet/plan_book.py
  127 / 5,600), introduces a skip-only suite (scripts/check_skip_only_suites.py),
  or opens a trigger gap (scripts/check_ci_trigger_closure.py). Constraints: the
  verdict is a function of the PR tree only; an inherited finding never reds;
  no ceiling is raised. Then prove the merged head with a main-descendant ci.yml
  SUCCESS.
state_before: >
  All three shapes were whole-tree checks with no base comparison. A PR that
  breached one surfaced as a red on whatever ran next, blamed on the wrong head.
  contract-delta diffed only curated closure and suite findings. Main was proven
  green at 386c98edda2c (ci.yml run 36351116221).
changed:
  - path: scripts/check_contract_delta.py
    what: >
      Three new differential classes: probe ceilings, skip-only suites and
      trigger gaps. Each is computed on the head tree and on its first-parent
      base. An introduced finding prints ::error and reds; an inherited one prints
      ::notice. Merged in #8102 as dcc6eb378ff7.
  - path: scripts/run_ci_pack.py, scripts/check_skip_only_suites.py, scripts/check_ci_trigger_closure.py
    what: >
      Each finding computation is now a callable that both the standalone gate
      and contract-delta use, so the two copies cannot drift. The callables are
      run_ci_pack.packing_probe_measurements / packing_probe_breaches,
      check_skip_only_suites.skip_only_findings and
      check_ci_trigger_closure.trigger_gap_findings (#8102).
  - path: .github/workflows/ci.yml, .github/ci/legacy-jobs.yml
    what: >
      Comments only, naming the five differential classes contract-delta now
      runs. No wiring changed (#8102).
  - path: tests/test_contract_delta.py, tests/test_check_skip_only_suites.py, tests/test_ci_pack.py
    what: >
      Tests for each class, including an inherited-does-not-red case per class
      (#8102).
  - path: scripts/check_p0b_receipt_closure.py
    what: >
      New --event flag. NO_DIFF_SUBJECT_EVENTS accepts the planner's `null`
      handle only on workflow_dispatch, workflow_run, schedule and base_replay.
      pull_request, an empty event and unknown events still refuse with rc 2.
      Merged in #8114 as de81c74c81ab.
  - path: .github/ci/legacy-jobs.yml
    what: >
      The p0b step passes --event "${GITHUB_EVENT_NAME:-}". Its comment is
      apostrophe-free on purpose (#8114).
  - path: tests/test_check_p0b_receipt_closure.py, tests/test_ci_pack.py, tests/test_check_ui_visual_evidence.py
    what: >
      Pin the event allow-list against run_ci_pack.SUPPORTED_PLAN_ROLE_EVENTS,
      the pull_request refusal, the rule never to read the event from the
      environment, and the manifest flag (#8114).
  - path: agentos/discoveries/DSC-CI-CHANGED-FILES-NULL-IS-THE-MAIN-PROOF-TOKEN.md
    what: New discovery recording that `null` is legitimate on every main proof.
  - path: agentos/discoveries/DSC-CI-RUN-BLOCK-COMMENT-QUOTE-BLINDS-CLOSURE-INFERENCE.md
    what: New discovery on the apostrophe landmine in run-block comments.
verified:
  - claim: contract-delta reds a PR on its own head for an introduced probe breach and an introduced skip-only suite
    command: gh run view 36353898581 (ci.yml on scratch head e117abf72193 of the #8102 branch)
    result: >
      contract-delta failed on the probe breach 135 > 134 and on the skip-only
      gate. Commit af1f7b76a0a3 reverted the scratch byte for byte.
  - claim: the final #8102 head is clean with zero introduced findings
    command: gh api repos/mastermindx-market-intelligence/macro/actions/jobs/108722294398/logs (contract-delta, run 36354874511, head 9152c435277d)
    result: SUCCESS; 0 introduced, 0 inherited (base 9f09d0b53ed3); gate wall 565.0 s
  - claim: contract-delta's added runtime is about +215 s
    command: >
      #8102 PR body section "Runtime (measured)" gives the before value from 5
      PR runs on 2026-09-27. Job 108722294398 above gives the after value.
    result: >
      The gate step went from 334–350 s (one outlier at 198 s) to 559–565 s.
      Per-side census in seconds (head/base): closure+suites 332.8/301.5,
      probes 152.0/130.4, skip_only 23.7/24.6, trigger_gaps 41.4/41.1.
  - claim: trigger closure is clean on the merged tree
    command: python3 scripts/check_ci_trigger_closure.py
    result: exit 0
  - claim: the first main proof after #8102 went red because of #7237, not #8102
    command: gh run view 36357668603 --log-failed (workflow_dispatch on dcc6eb378ff7)
    result: >
      The only failing step was ci-pack-11 / p0b-receipt-closure: "REFUSED:
      planner changed-file handle is null / unavailable". #7237 (10fc49afe17f)
      had made that gate refuse `null` on every event.
  - claim: both PRs merged on concluded-green checks
    command: gh pr view 8114 --json mergedAt,mergeCommit; gh run view 36361971686 --json conclusion,updatedAt
    result: >
      #8102 merged as dcc6eb378ff7 at 2026-09-27T23:07:42Z. #8114 merged as
      de81c74c81ab at 2026-09-28T00:48:58Z, after its run 36361971686 concluded
      success at 00:48:39Z.
  - claim: the discoveries validate
    command: python3 scripts/agentos.py validate
    result: 0 error(s)
unverified:
  - claim: >
      The merged authority of #8102 and #8114 is proven by a main-descendant
      ci.yml SUCCESS. The proof is run 36363735025, a workflow_dispatch on main
      at de81c74c81ab, dispatched at 2026-09-28T00:51:14Z over a clear field.
      It was still in flight when this record was pushed. Its conclusion is
      posted on #8102 and #8114.
    what_would_verify: >
      gh run view 36363735025 --json conclusion,headSha should show success. If
      it is red, attribute each failing job by name against main's own newest
      ci.yml runs before calling it this work's.
unresolved:
  - >
    ci-pack's job-level `if:` starts with `always()`, so cancel-in-progress
    never stops a started pack; a superseded run held #8102's re-push pending
    for about 11 minutes until it was force-cancelled. The `!cancelled()` fix is
    a separate proposed task, not merged.
  - >
    pytest_invocation_ambiguities still tokenizes shell comments. The frozen fix
    is to strip full-line comments before shlex; it is a separate proposed task,
    not merged. See DSC:CI-RUN-BLOCK-COMMENT-QUOTE-BLINDS-CLOSURE-INFERENCE.
  - >
    Known limit of the new classes, accepted in the Opus review: a renamed
    suite or job is keyed as a new finding, so a pure rename of an
    already-failing item reds as introduced.
next_actions:
  - >
    A PR that adds a job to the templates/index.html packing probe will red its
    own contract-delta, because the probe sits at exactly 134 of 134. Move work
    out of that probe; do not raise the ceiling.
  - >
    When a main ci.yml proof reds with a null-handle refusal, find the consumer
    of CI_CHANGED_FILES_FILE that refuses `null`. Apply the #8114 shape: an
    explicit --event flag plus an allow-list mirrored from
    run_ci_pack.SUPPORTED_PLAN_ROLE_EVENTS.
do_not_redo:
  - Do not raise any packing-probe ceiling to green a PR. The ceilings are the contract.
  - >
    Do not make check_p0b_receipt_closure.py read GITHUB_EVENT_NAME from the
    environment; test_cli_never_reads_the_event_from_the_environment pins this.
  - >
    Do not re-investigate the red on main proof 36357668603. It was #7237's
    null refusal, healed by #8114.
  - >
    Do not switch pytest_invocation_ambiguities to shlex comments=True. It
    truncates ${VAR#pattern}.
danger_areas:
  - >
    scripts/** and .github/ci/** are CI authority. A merged head clears only
    through a main-descendant ci.yml SUCCESS. Preflight for an in-flight main
    run first, and never dispatch over one.
  - >
    contract-delta's gate step now takes about 560 s on a 2-core hosted runner.
    Each whole-tree class runs twice, once on head and once on base, so another
    class adds its cost twice.
  - >
    An apostrophe in a legacy-jobs run-block comment silently removes that
    job's inferred closure (DSC:CI-RUN-BLOCK-COMMENT-QUOTE-BLINDS-CLOSURE-INFERENCE).
prs: [8102, 8114]
discoveries:
  - "DSC:CI-CHANGED-FILES-NULL-IS-THE-MAIN-PROOF-TOKEN"
  - "DSC:CI-RUN-BLOCK-COMMENT-QUOTE-BLINDS-CLOSURE-INFERENCE"
---

Two merged PRs and one records PR. #8102 made the three whole-tree CI shapes
differential, so a PR is judged only on what it introduces. #8114 healed the
unrelated #7237 regression that had turned every main proof red. Both
discoveries record what future sessions would otherwise rediscover the
expensive way.
