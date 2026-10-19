---
workstream: "WS:CI-MERGE-CONTROL-PLANE"
session: "01a153e8-3c85-7bb2-af63-7f477b570512 / claude/ci-pack-throughput-20261019"
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
    what: Skip the generic path traversal for named suites already analyzed in this command.
  - path: tests/test_ci_pack.py
    what: Pin one traversal, retained separate-script ownership, and opaque-target refusal.
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
unverified:
  - Hosted candidate and post-merge natural-traffic latency improvement.
unresolved:
  - Complete scope/plan parity, affected tests, independent review and hosted proof are pending.
next_actions:
  - >
    Consume retained real-manifest parity and affected-test processes, adjudicate
    same-ID Fabric review, publish the scoped source PR and obtain hosted proof.
  - Compare natural first attempts at equivalent coverage before expanding shards or materialization.
do_not_redo:
  - Preserve the accepted September scope-test reuse in PR 8126.
  - Reuse the retained 40-run baseline and same-ID Fabric operations.
danger_areas:
  - Scope changes can silently drop coverage; require complete result and plan equality.
  - Do not run the destructive pack executor in this developer checkout.
  - Local green and one hosted run do not prove the fleet p95 target.
---

The current workspace is `/Volumes/Mastermind/agent-workspaces/codex/ffcf/macro-main`.
Raw evidence is `/Volumes/Mastermind/ci-pack-throughput-20261019/`; the committed
research directory contains normalized source-linked evidence and its index.

Existing #8094 remains a separate curated-only population optimization. No
`curated_exclusive_closure_findings`, workflows, manifest, proof schema, runner
settings, or gate semantics were edited. Open product PRs have disjoint additions
to `tests/test_ci_pack.py`; preserve them. The repository-wide census found no
open change to `ci_scope_dependencies.py` or `test_ci_trigger_closure.py`.

Original-root Fabric census `ci-pack-20261019-01a153e8-census` returned terminal
rc=0, but its metrics were **not accepted**: it extrapolated and included
inconsistent arithmetic. The parent recomputed metrics from retained API JSON.
The bounded independent semantic review uses
`ci-pack-20261019-01a153e8-review` on its original adapter/carrier. Do not duplicate
that operation. No peer messaging or watcher was created.

The partial Python 3.14 profiler was intentionally interrupted and is not a
passing suite; Python 3.12.13 supplies the acceptance test/benchmark environment.
Local macOS performance is not Linux/x86 hosted acceptance. Keep missing
full-checkout proofs, hosted CI, merge, and natural-traffic improvement distinct.
