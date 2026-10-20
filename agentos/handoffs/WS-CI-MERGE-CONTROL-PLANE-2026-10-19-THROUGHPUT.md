---
workstream: "WS:CI-MERGE-CONTROL-PLANE"
session: "01a153e8-3c85-7bb2-af63-7f477b570512 / claude/ci-pack-throughput-natural-20261019"
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
Branch: `claude/ci-pack-throughput-natural-20261019`, fresh main after report PR9780.
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

Natural weighted20:48 snapshot:32 runs,19 verified first-attempt completions
(14success/5failure),9pending,4cancelled. All19 qualify tested planner blob
f5e4e9c3202c35c9b29c6d038e1d077661fe6375 and base ancestry from
38d2dac36faabfff04f8efe5ee28e5c8dfa1c5ae. Scoped success N13 p50/p95
2106/3941sec, summed wall215.68/399.37min. Scoped failure N4 first-red
1669.5/2105sec. No exact original baseline selected-set/execution-proof matches.
Nine completions select neither calibrated job; five scoped exposed successes
have2452/3941sec and277.48/399.37 summed wall. All statistics descriptive.
Early6-success p95 2426sec became3941 as slower work completed; no causal gain,
cost neutrality or30% target established. No speculative shard/weight expansion.

Retained weighted-natural-runs/comparison/summary/stage-summary-2048.json plus
weighted-exposure-2048.json. Prior19:52 and dedup-only16:50 cohorts preserved.
Exploratory adjacent control16:50..18:49:48:35runs,22plans screened. Exact pair
39300382055(control,verified old blob/base) and39306252071(weighted) selects
91jobs but neither calibrated job. Control failed; weighted passed. It cannot
estimate calibration speedup. Do not replace baseline or relax full proof match.
Supplementary evidence late-control-matches/exact-match-2048.json retained.

Successful tail39311574352(PR9639):159jobs after476-file change/27selected job
changes. Critical pack6 wall3610sec, checkout377, wrapper3205; commands1525.04.
Two depth8->32 waits691.30/725.67sec target the same exact merge SHA before
signal-gate-pair-coherence/ruling-graph. Full log recovered by one same-carrier
read after cooldown; weighted-tail-39311574352.log now retained, do not download
again. Natural global success39309256542 full log retained:258jobs,2517sec/
373.43wall min; FIF1989.85sec, control1269.95, earnings779.43,nw-lobe681.92.
Critical checkout479sec. Details weighted-natural-tail-costs-2048.json.

Third bounded source slice is now prepared: _prepare_provided_actions checks
existing _tested_tree_ancestry_ready(root,trusted_git_env,exactSHA) BEFORE the
first depth2 fetch. Every invocation rechecks live local ancestry; no success
cache, cross-repository reuse, weakened predicate, command/proof or shard change.
Incomplete ancestry retains all bounded/legacy recovery rungs. New notice makes
real hosted reuse observable. Source changed only this precheck/notice.
Real shallow-Git regression shows original second consumer makes3 extra fetches;
after fix complete history persists and a separate shallow repo still fetches.
Nine fetch/recovery tests pass5.70sec.199 authority tests pass; one unconditional
fetch mock corrected to missing-then-ready and passes2.15sec.42 inherited cleanup
warnings retained.329-job all-gate manifest validates. Logs ancestry-before,
ancestry-after, ancestry-authority, ancestry-authority-repair, ancestry-manifest.
First acquisition may remain necessary; neither23.6min aggregate nor12.1min
second interval is an accepted saving. Hosted trial must establish real behavior.

Open-PR title scan and existing workspace inventory found no competing ancestry
repair. Preserve PR8094's separate curation scope and PR9773's active FIF repair.
Implementations9722/9763 and report9780 remain merged/verified; all old observers
are settled/consumed. Do not create a new observer per current heartbeat limit.

Next: finish this batched comparison plus bounded ancestry trial through normal
GitHub source, active authority/full hosted proof and normal merge. Use existing
hourly heartbeat as fallback attention and one bounded same-carrier read at a
useful boundary after cooldown; do not hot-poll or manufacture CI. Keep this one
checkpoint current; preserve original root, active writers and unknown effects.
No peer messages, new control plane, speculative shards or unrelated deployment.
