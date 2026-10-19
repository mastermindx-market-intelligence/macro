---
workstream: "WS:CI-MERGE-CONTROL-PLANE"
session: "01a153e8-3c85-7bb2-af63-7f477b570512 / claude/ci-pack-throughput-results-20261019"
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
  - path: contracts/market_memory/e0_reviewer_plan.v1.schema.json
    what: Add the missing canonical schema identifier to repair the reproduced population registry failure.
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
  - claim: The schema identifier repair fixes the complete owning test battery without weakening its rules.
    command: Three failing population tests; both population/reviewer-plan modules; exact research-price-panel pytest command from manifest
    result: Before3 failed; after181 affected tests passed and full owning battery1345 tests plus429 subtests passed. Removing the added identifier reproduces the original parsed schema exactly.
unverified:
  - Comparable post-merge natural-traffic latency improvement.
unresolved:
  - Comparable post-merge natural-traffic improvement remains unproven; hosted correctness and merge are verified.
next_actions:
  - Collect natural first attempts after the second merge, with exact treatment and execution proof identities.
  - Compare actual install, checkout, queue, command and total wall cost before further expansion.
do_not_redo:
  - Preserve the accepted September scope-test reuse in PR 8126.
  - Reuse the retained 40-run baseline and same-ID Fabric operations.
danger_areas:
  - Scope changes can silently drop coverage; require complete result and plan equality.
  - Do not run the destructive pack executor in this developer checkout.
  - Local green and one hosted run do not prove the fleet p95 target.
---

Workspace: `/Volumes/Mastermind/agent-workspaces/codex/ffcf/macro-main`.
Branch: `claude/ci-pack-throughput-results-20261019`, fresh main after PR9763.
Original root: `01a153e8-3c85-7bb2-af63-7f477b570512`.
Evidence: `/Volumes/Mastermind/ci-pack-throughput-20261019/`.
Report: `research/ci_pack_throughput_20261019/README.md`.

PR9722 merged7736fd72895fc24e55bf2d4bbc7b1f4e94203414; accepted scope parity,
CPU, tests and same-ID review remain settled. PR9763 merged18:49:48Z as
38d2dac36faabfff04f8efe5ee28e5c8dfa1c5ae, head996a22e7e5acebc5fd883068f04fa803d7a1aab7.
Full CI39298424658 passed all257 jobs/twelve packs/gate plus active authority
and fences. Plan3f62b28f67c5a17df6094debca5aa845ebf562c605cf5ce454798aeac5dfa4cb;
tested treea111b2f49b0d46b06d8a2d4f22dec9bf4d6acd6c. Planner/schema blobs and
new regression landed; other independent test edits remain. No observer remains:
50933,57835,70423,44369 are all settled/consumed; never recreate.

Two weights1630/1070 only; twelve packs/commands/proof/isolation unchanged.
Defense heal9758 incorporated. One-field reviewer-plan schema ID repair
reproduced3 failures before, passed181 affected and1345 owning tests/429subtests
after, then hosted proof passed. Prior39282678531/39290075936 include base
replay and are not successful throughput samples. Optional Fabric weight review
was denied before execution canonical_source_unreadable; no verdict or bypass.

Full accepted logs: trial-full.log, weight-success-full.log (do not redownload).
New metadata weight-success-run.json; per-step weight-success-stage-costs.json;
command/install groups weight-success-command-comparison.json; exact manifest
weight-success-legacy-jobs.yml; assignment replay weight-success-replay.json.
Weighted result48.82min/371.70 summed wall min versus78.08/337.38 first trial.
Gate wait3sec versus825sec. Two added jobs/seven changed definitions, so no
causal gain, cost neutrality or30% fleet p95 established. Exact-run fixed-cost
replay: old heuristic2694.53 -> calibrated2266.33sec max; excludes overhead.
Retain calibration; no speculative expansion.

Natural dedup-only16:50 cohort37 completions, two selected-set matches, zero
execution-proof matches; reuse caches. Weighted cohort starts after18:49:48Z;
18:53 snapshot weighted-natural-runs-1853.json has one pending/no completions.
Require tested blobf5e4e9c3202c35c9b29c6d038e1d077661fe6375 and base ancestry
from38d2dac36faabfff04f8efe5ee28e5c8dfa1c5ae. compare_natural.py accepts
--merge/--blob/--output; earlier defaults retained. Ancestry cache must match
treatment merge, not merely base SHA. Keep cancellations/reruns/pending visible.

Next: finish publishing this batched result through normal source, then collect
naturally concluded weighted first attempts at the existing hourly boundary;
compare exact selected and execution-proof identities before another source slice.
Do not dispatch artificial CI, rerun accepted tests, duplicate observers, message
peers, add a control plane, expand shards or deploy unrelated services. Preserve
writers/root/unknown effects. Respect300sec same-run read cooldown, no bypass.
