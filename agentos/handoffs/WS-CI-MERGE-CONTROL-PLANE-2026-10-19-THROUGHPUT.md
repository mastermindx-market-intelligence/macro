---
workstream: "WS:CI-MERGE-CONTROL-PLANE"
session: "01a153e8-3c85-7bb2-af63-7f477b570512 / claude/ci-pack-throughput-evidence-20261019"
model: codex
ended_because: ci_handoff
mission: >
  Deliver the Chairman's October 19 CI pack throughput commission: lower
  push-to-gate and actionable-red latency without coverage, identity, isolation,
  cancellation, or cost regression. This is an active checkpoint, not completion.
state_before: >
  Macro main 168c96bf9ca68427749bc70664902c343d968d9c; hosted route, twelve packs,
  historical scope-test reuse already merged in #8126. Current protected procedure
  Mastermind 5469f12de01158b0e495d616d2be6f56c03cf8a8, skillpack 1.0.1/bootstrap 1.
changed:
  - path: scripts/run_ci_pack.py
    what: Landed duplicate-traversal repair; next trial calibrates only FIF/earnings weights.
  - path: tests/test_ci_pack.py
    what: Add calibrated assignment, complete coverage and unchanged execution-proof regression.
  - path: research/ci_pack_throughput_20261019/README.md
    what: Measured baseline, ranked architectures, shard simulations, limits and rollback.
verified:
  - claim: The recent baseline includes exact run and plan identities.
    command: gh api repos/mastermindx-market-intelligence/macro/actions/workflows/ci.yml/runs and exact-attempt jobs/plan artifacts
    result: >
      40 concluded runs; primary cohort 22 first-attempt noncancelled runs,
      17 cancellations separate, one reused-job rerun excluded. Successful
      first-attempt run-to-gate p50/p95 3196/4074 seconds. First failed-step
      completion for seven failures p50/p95 2632/4178 seconds. These are proxies,
      not exact push/error timestamps or billed minutes.
  - claim: Existing authority negative controls pass before modification.
    command: python3.12 -m pytest tests/test_ci_plan_workflow.py tests/test_ci_semantic_proof.py tests/test_ci_pack_semantic.py tests/test_ci_pack_fragments.py tests/test_trusted_ci_production_route.py -q
    result: 200 passed in 143.38 seconds.
  - claim: The performance regression discriminates the duplicate traversal.
    command: python3.12 -m pytest tests/test_ci_pack.py -q -k 'named_suite_closure_is_traversed_once or opaque_pytest_target_still_refuses'
    result: Original source 1 failed/1 passed; candidate 2 passed.
  - claim: Complete inferred scopes and ten replayed plans are unchanged.
    command: Retained compare_scope.py against original infer_job_scopes and candidate on the same manifest/tree
    result: 255 jobs; closure calls 1352 to 697; identical scope result SHA256 b6509bbd711065dcff26d0ed20658bf58e4adafee0bd4c6745cf7897af195ea8; all ten plans equal.
  - claim: The alternating local benchmark reduces scope-inference CPU work.
    command: Retained compare_cpu.py under Python 3.12.13; three old and three new warmed samples
    result: Median process CPU seconds 17.886 to 8.652 (51.6 percent lower); local diagnostic only, not hosted p95 proof.
  - claim: The bounded independent review is accepted through its original carrier.
    command: fabric_task.py result and accept ci-pack-20261019-01a153e8-review --by reviewer
    result: PASS; real closure-root and filter assumptions checked; ACCEPTED / VALIDATED_OUTCOME. Manifest validate-only also passed for 255 jobs.
unverified:
  - Comparable post-merge natural-traffic latency improvement.
unresolved:
  - Comparable post-merge natural-traffic improvement remains unproven; hosted correctness and merge are verified.
next_actions:
  - Deliver the two-weight trial through required hosted checks and normal merge.
  - Compare actual install, checkout, queue, command and total wall cost before further expansion.
do_not_redo:
  - Preserve the accepted September scope-test reuse in PR 8126.
  - Reuse the retained 40-run baseline and same-ID Fabric operations.
danger_areas:
  - Scope changes can silently drop coverage; require complete result and plan equality.
  - Do not run the destructive pack executor in this developer checkout.
  - Local green and one hosted run do not prove the fleet p95 target.
---

Current frontier: first trial **PR 9722 merged** as
`7736fd72895fc24e55bf2d4bbc7b1f4e94203414` at 13:13:09Z. All 255 logical jobs,
twelve packs, gate, authority and fences passed. Source/test landing verified.
Original observer 44369 is settled and consumed; never recreate it. Release result:
https://github.com/mastermindx-market-intelligence/macro/pull/9722#issuecomment-6268117245

Workspace `/Volumes/Mastermind/agent-workspaces/codex/ffcf/macro-main`, branch
`claude/ci-pack-throughput-evidence-20261019`, refreshed to main
`c375959f69cf757a5edbf517ecd3b1d848836a55` while preserving report edits.
Raw evidence `/Volumes/Mastermind/ci-pack-throughput-20261019/`; source report
`research/ci_pack_throughput_20261019/README.md`. Original root remains
`01a153e8-3c85-7bb2-af63-7f477b570512`. Separate PR 8094 is not adopted.

First hosted run 39247388552 took 78.1 min and 337.38 summed job wall minutes,
including 825 sec final-gate queueing for a 12-sec gate. Control-plane inner group
740.414 sec versus historical median847.738 is descriptive only; local CPU median
fell51.6%. Neither proves fleet p95 improvement. Accepted first-trial scope/plan
parity,327 affected tests and200 authority tests are retained; do not repeat them
without a relevant change.

Natural snapshot15:51Z:43 runs,16 pending,5 cancelled,1 rerun excluded;
21 verified first-attempt completions(18 success/3 failure), all scoped.
Exact planner blob and base ancestry verified; zero baseline selected-set or
execution-proof matches. Success p50/p95 2106/3565 sec vs3265.5/4074 historic;
completion-conditioned and different work, no causal or30% target claim.
`postmerge-runs-1551.json`, `post-*` captures and `natural-comparison-latest.json`
retain raw facts. One502 jobs capture was recovered through the same API after
cooldown; original error retained. `compare_natural.py` accepts a snapshot path.

Second trial: only two balancing estimates, FIF1630 and earnings1070; unchanged
algorithm, twelve packs, selectors, commands, proofs and hosted isolation.
`trial-full.log` is now complete:255 measured jobs,14219.792 command seconds.
`calibrated-weight-simulation.json` reproduces exact original pack assignments and
models max command work2085.4->1532.3sec(-26.5%). Conservative1400/900 gives same
result; FIF alone only-3.2%.42 scope replays:13 improve,0worse,median0; unknown jobs
excluded explicitly. Installation/reuse,checkout,queue,artifacts are outside model.
Earnings has one observation; real hosted cost remains required.

Candidate checks:7 targeted packing/coverage/hash/curation tests passed in135.76s;
200 authority/negative controls passed in58.43s,42 existing pytest-cleanup warnings.
No ceiling or gate weakened. Optional same-ID Fabric weight review
`ci-pack-20261019-01a153e8-weight-review` returnedrc78 before reviewer execution:
`admission_denied reason=canonical_source_unreadable`; no verdict/no acceptance,
no alternate provider. Initial dedup review remains accepted for its original scope.

Next: publish this bounded trial plus batched evidence through normal GitHub source,
consume one verified CI observer, resolve genuine failures, then normal merge.
No artificial CI, peer messages, new coordinator/control plane, extra shards or
unrelated deploy. After hosted correctness, compare real per-stage costs and natural
matched traffic; do not infer throughput acceptance from a green run or model.
