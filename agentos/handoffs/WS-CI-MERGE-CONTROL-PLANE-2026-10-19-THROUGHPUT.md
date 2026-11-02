---
workstream: "WS:CI-MERGE-CONTROL-PLANE"
session: "01a153e8-3c85-7bb2-af63-7f477b570512 / codex/ci-parser-qname-20261020"
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
    what: Landed traversal/weight trials; third trial preserves already-complete exact ancestry.
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
  - Consume parser trial local verification, then deliver its normal hosted PR and verify source landing.
  - Compare actual install, checkout, queue, command and total wall cost before further expansion.
do_not_redo:
  - Preserve the accepted September scope-test reuse in PR 8126.
  - Reuse the retained 40-run baseline and same-ID Fabric operations.
danger_areas:
  - Scope changes can silently drop coverage; require complete result and plan equality.
  - Do not run the destructive pack executor in this developer checkout.
  - Local green and one hosted run do not prove the fleet p95 target.
---

# Current checkpoint — October20,2026,11:12Z

Original root01a153e8-3c85-7bb2-af63-7f477b570512. Owned branch
codex/ci-parser-qname-20261020. Report9857 merged4290a79a222da944dbee0b438474029d67d0c4b2
at11:04:34Z;75selected jobs, all active gates/fences/authority passed,5blobs verified
on fresh main. No accepted-log/test replay or cohort expansion. Fixed0754comparison
and all earlier implementation/report releases remain accepted; no causal fleet
speedup/cost neutrality/30percent target is proven. Keep12packs/two weights.

New discriminating residual profile on exact parser79df25 and two accepted inputs:
687371 qname splits,0.419cumsec of2.109instrumentedsec. Complete outputs match.
Candidate stores split name parts per node and invalidates on qname change; no global
cache, output/limit/refusal/proof/route change. Regression fails before1200splits vs6;
215parser tests pass7.96sec after. Five alternating local samples CPU0.749179→0.655287
(12.53percent),wall0.805988→0.726055; complete output hashes equal. Tracemalloc peaks
+3.25/+5.49percent, not RSS/hosted cost. Offline TEMP-store publisher lineage
round-trip passes1test10.85sec, including direct-mint equality. All local runners settled.
No source edit to active FIF producer/registry carriers. Bounded500open-PR file census
and targeted parser title/body search found no parser carrier; census reached limit,
so it is not an exhaustive proof of absence. Exact current parser blob was verified.
Next: finish affected integration check, normal scoped PR/hosted proof/merge/landing.
Evidence qname-trial.json and raw /Volumes/Mastermind/ci-pack-throughput-20261019/.

Portfolio dependency at11:03:56Z release boundary: canonical admission16active proofs
+1unindexed reservation=17/cap8, no opening; lease7480. No peer send or rerun.
At next useful integration boundary use eligible existing canonical observation;
return actual opening ONCE via supported peer message to Evaluation OS root
01a1333d-b0c0-7f33-9259-dd718391d9e4. Original owner alone fresh-checks/executes unused
authority for38801258721/workflow335022837/PR6651 atb4ff0d721ab8f40cd7aa50d469167537f43ca3cd.
No dependency-only polling/reservation/preemption/capchange/guardreset.

Preserve root/grants/writers/unknown effects and real approval/refusal boundaries.
Earlier optional Fabric weight review denied preexecution canonical_source_unreadable;
no verdict/bypass. Profiling tree ff3996da remains unchanged, not adopted/reminted.
No synthetic CI, speculative shards, new scheduler/controlplane or unrelated deploy.
One existing hourly heartbeat; no CI observer.300sec same-run cooldown/no bypass.
Notify material results; two unchanged wakes diagnose/back off60minutes.
