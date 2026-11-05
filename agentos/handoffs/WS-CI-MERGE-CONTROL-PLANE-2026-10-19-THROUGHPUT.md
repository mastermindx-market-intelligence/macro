---
workstream: "WS:CI-MERGE-CONTROL-PLANE"
session: "01a153e8-3c85-7bb2-af63-7f477b570512 / codex/ci-throughput-matched-cohort-20261020"
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

# Current checkpoint — October20,2026,10:03Z

Original root01a153e8-3c85-7bb2-af63-7f477b570512; owned branch
codex/ci-throughput-matched-cohort-20261020 from fresh main. PR9850 merged
6793c010048996193d3d98876b486910c7982e3c at09:08:07Z. CI39389030973:
75 selected jobs, exact subject0d0e5ee02f5972ecd220e5e8e77d499f86c4d075,
all12packs/gate/contract-delta/fences/active authority passed. All6authored blobs
verified after successful fresh fetch; concurrent shared-ref fetch race resolved
by one successful refetch, no reset. Evidence parser-results-landing.json.
PR9813 remains accepted9c7df3786fc3856fbb692da301584b4b443ab66d:
96jobs/299proofs/7blobs;34.55min/222.45wall. Earlier releases9722/9763/9791
and reports9780/9801 reusable. No live observers/runners/downloads.

Fixed07:54 parser comparison COMPLETE:57runs,36qualified first attempts
(29success7failure),18pending3cancelled0reruns. All31missing job records acquired;
no missing metadata. Exact parser79df25f36a17c79a726e28d11f0018dda92d5bbd,
plannerf92be10fc37455fd427829f0f964c5ef581b3a80 plus parser-merge ancestry.
Scoped successN24 p50/p951895/2553sec,wall177.675/253.95min. Global successN5
2723/3156sec,wall352.6/360.1min. Scoped failureN7 firstfailed-step completion
578/1853sec (includes replay),wall200.067/337.633min. Zero original-baseline
full-proof matches. Preserve fixed05:54 and ancestry00:55 cohorts separately.

Secondary matched successes39384839986/39378857695/39374295130 share identical
103job execution proofs and pack assignment with ONE old-parser control39346152272.
Control2007sec/232.533wallmin; treated2066/2581/2553sec and220.833/228.15/228.067wallmin.
All treated slower to gate, fewer summed wall minutes; not3independent pairs.
Control criticalpack7; treated criticalFIF-alonepack0. FIF wrapper1347sec control
versus1616/2172/2113sec treated; checkout199sec versus201/197/197. No causal gain,
cost neutrality or30percent target proven. Keep12packs/two weights.

All four matched full logs now consumed; no download handles remain. Control
FIF2680pass1skip1311.39sec, fourcommands1329.857sec. Treated primary
2681pass1skip1573.45/2126.72/2065.02sec; fourcommands1594.096/2151.041/2089.544sec.
All treated runner2.337.0/image20261012.334.1/Python3.12.13. Labels do not control
physical performance or transitive inputs. Primary FIF command dominates.
Decision: retain12packs/two weights/accepted parser source; next engineering slice
needs discriminating residual profile and current active-carrier check. No additional
optimization/revert justified by one reused control. Current action: batch complete
fixed comparison/report/method/workstream through normal source delivery. No new
cohort expansion, accepted-test/log replay or per-wake placeholder PR. Preserve
repair carriers9216/9831 and all active FIF owners.

Portfolio capacity dependency: canonical scripts/merge_on_green.py census and
lease register observed10:01:26Z:13active PR proofs+1unindexed reservation=14,
cap8, zero slots. Leaseowner7480; admission-boundary-1000.json retained.
NO opening evidence; NO peer send, reservation or rerun. At next already-useful
release/cohort integration boundary obtain eligible existing observation; send
actual opening evidence ONCE via supported peer message to Evaluation OS root
01a1333d-b0c0-7f33-9259-dd718391d9e4. That original owner alone holds UNUSED
one-rerun authority38801258721/workflow335022837/PR6651 at
b4ff0d721ab8f40cd7aa50d469167537f43ca3cd and must fresh-check/execute same carrier.
Do not poll solely for this dependency, preempt, raise cap or reset guards.

Raw evidence /Volumes/Mastermind/ci-pack-throughput-20261019/. All accepted
logs/tests/reviews remain reusable; no replay. Optional Fabric weight review
was denied preexecution canonical_source_unreadable, no verdict/bypass.
Profiling tree stays detached unchangedff3996da. Preserve root/grants/writers,
Desktop approvals/refusals and unknown effects. No speculative shards, new
scheduler/controlplane or unrelated deploy. Existing hourly heartbeat only;
notify material results. Two unchanged wakes diagnose once/back off60minutes.
