---
workstream: "WS:CI-MERGE-CONTROL-PLANE"
session: "01a153e8-3c85-7bb2-af63-7f477b570512 / codex/ci-throughput-parser-results-20261020"
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

# Current checkpoint — October20,2026

Original root01a153e8-3c85-7bb2-af63-7f477b570512; owned results branch
codex/ci-throughput-parser-results-20261020. PR9813 is merged9c7df3786fc3856fbb692da301584b4b443ab66d
at04:57:13Z, accepted96jobs/299proof units/0infra/all active checks;7blobs verified.
Final39364786931 cost34.55min to gate/222.45summed job-wall/2sec gatewait;
FIF2681pass1skip1552.58sec,4commands1573.07sec. All runners/downloads settled.
Do not reread consumed logs/tests. Full source/proof/cost details in report and
parser-trial.json; raw /Volumes/Mastermind/ci-pack-throughput-20261019/.

Both previously unread failure-job records obtained at admitted boundary.
Fixed05:54 parser snapshot COMPLETE:16runs,5qualified first-attempt completions
(3success2failure),11pending,0cancelled,0reruns. Exact parser79df25f36a17c79a726e28d11f0018dda92d5bbd
and plannerf92be10fc37455fd427829f0f964c5ef581b3a80 plus merge ancestry verified.
Success N3 p50/p951860/2218sec,wall228.50/252.18min; failure N2 first failed-step
completion950.5/1002sec (includes replay),wall117.63/201.85min. No global sample.
Zero original-baseline full-proof matches. Secondary94job pair: failed39374315686
vs success39341912215; pack6 ArtifactService timeout, FIFpassed but gatefailed.
Secondary3job pair: failed39372741047 vs weighted success39317389150, unexposed
FIF/collector-registry and different planner. Candidate discovery falsifier fails;
base has different git-date failure, authoritative5passed/1unknown. PR9831 already
advanced7774b567->c99882ec; PR9216 remains626071dd. Preserve repair carriers.

Portfolio-lead continuation authorizes batching these informative findings through
normal source delivery. Report/parser-trial/method/parser-natural-comparison/workstream
and this checkpoint are the batch. Next: normal source checks, PR, active hosted gates,
normal merge and landing; no new observer. Existing heartbeat supplies attention.
Then bounded natural comparison under existing method before further optimization.
Earlier00:55 ancestry cohort remains fixed45runs31eligible7pending7cancelled.
No causal fleet30percent gain or cost-neutrality claim; retain12packs/two weights.
No syntheticCI, new scheduler/controlplane, speculative shards or unrelated deploy.

Earlier releases9722/9763/9791 and reports9780/9801 accepted and reusable. All local
parser/equivalence/profile tests accepted; no replay. Optional weight review denied
preexecution canonical_source_unreadable, no verdict/bypass. Initial dedup Fabric
review accepted only for its original scope. Profiling tree remains detached and
unchanged ff3996daeb00dd92c50f93865d685c4cd5044f5d; do not remint/adopt.
Preserve original roots, active writers, grants and unknown effects. No routine peer
pings or relay.300sec same-run cooldown, no alternate reader/reset/sleep-retry.
Notify material results; two unchanged wakes diagnose/back off60min. Pause only
completion or a sole human/unknown-effect gate.
