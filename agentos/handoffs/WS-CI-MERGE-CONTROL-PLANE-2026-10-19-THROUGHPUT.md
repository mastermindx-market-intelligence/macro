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

Workspace: `/Volumes/Mastermind/agent-workspaces/codex/ffcf/macro-main`.
Branch: `claude/ci-pack-throughput-evidence-20261019`; original root
`01a153e8-3c85-7bb2-af63-7f477b570512`.
Raw evidence: `/Volumes/Mastermind/ci-pack-throughput-20261019/`.
Report: `research/ci_pack_throughput_20261019/README.md`.

PR9722 merged as7736fd72895fc24e55bf2d4bbc7b1f4e94203414 with full hosted proof.
Reuse accepted scope/CPU/tests/review evidence. Its observer44369 is consumed.
No causal fleet gain/30% target is established. The first full trial took78.1min,
including825sec final-gate queueing. Do not re-download its retained logs.

Current carrier: https://github.com/mastermindx-market-intelligence/macro/pull/9763
Two balancing estimates1630/1070, twelve packs and all proof/isolation controls
unchanged. One optional Fabric weight review was denied before execution
(canonical_source_unreadable); no verdict/bypass. PR8094 remains separate.

Trial39282678531 failed Defense's eight-minute deadline on candidate and base.
Existing landed heal PR9758 was incorporated; observer70423 consumed rc1.
Recovery39290075936 (head67377ec633cf3e797ebe61a0453ccd2b44b18b35) passed Defense
but failed three population tests in research-price-panel on candidate AND base.
Observer57835 is now consumed rc1; do not recreate it. Full log retained as
weight-recovery-full.log, exact plan in weight-recovery-plan/ci-plan.json.
Tested tree2b12ec85550ac49c3e17f15627335cb22737d8dd; baseaee0f40a6b40e8b9287d3ffee9cf988d2a641434;
257 selected jobs; plan4bf52141b3d0106616678078ca620b7c498eab66bc10dadd3ec054161474f591.
Both failed runs include extra base replay and are not successful latency samples.

Cause: PR9765 added e0_reviewer_plan.v1.schema.json without the $id required by
the existing population schema registry. Main b2bf0b63a1eae8fc894dd2290ec62bd2f7d00a68
still lacks it.500 open PRs checked; no competing repair on this schema, and the
original schema worktree has no dirty edit on the path. Add only canonical $id;
all other parsed schema contents identical. Three failures reproduced before;
181 affected tests pass after; full exact research-price-panel pytest command
passes1345 tests and429 subtests in116.29s (45 inherited warnings). All52 schema
identifiers complete/unique. Logs: schema-id-before.log, schema-id-after.log,
schema-owner-battery.log. No validation constraint, timeout or selector changed.

Natural16:50 cohort:57 runs,37 verified first attempts,9 pending,9 cancelled,
2 reruns; two selected-set matches but zero execution-proof matches. Scoped
success p50/p95 1920/3511 seconds remains descriptive. Reuse cached captures.
Heavy successful groups in failed recovery: FIF1969.43sec total, earnings577.05;
FIF checkout800.22sec. No additional weight/shard decision follows from this.

Next: push the schema repair and batched evidence to this same PR, then retain
ONE verified observer for the new head/run. Required hosted checks and normal
merge remain owed. At completed-run boundary collect full logs before other
same-run reads; respect300sec cooldown with no alternate reader/reset.
Preserve this checkpoint, active writers and unknown effects. No artificial CI,
peer messages, new coordinator/control plane, extra shards or unrelated deploy.
