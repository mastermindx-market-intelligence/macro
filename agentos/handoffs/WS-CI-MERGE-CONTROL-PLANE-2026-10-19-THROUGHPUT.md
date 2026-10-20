---
workstream: "WS:CI-MERGE-CONTROL-PLANE"
session: "01a153e8-3c85-7bb2-af63-7f477b570512 / codex/ci-throughput-ancestry-results-20261019"
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
  - Collect naturally concluded third-treatment first attempts after 21:52:31Z; PR9791 is merged and verified.
  - Compare actual install, checkout, queue, command and total wall cost before further expansion.
do_not_redo:
  - Preserve the accepted September scope-test reuse in PR 8126.
  - Reuse the retained 40-run baseline and same-ID Fabric operations.
danger_areas:
  - Scope changes can silently drop coverage; require complete result and plan equality.
  - Do not run the destructive pack executor in this developer checkout.
  - Local green and one hosted run do not prove the fleet p95 target.
---


Current checkpoint — 2026-10-19T23:59Z. Original root
`01a153e8-3c85-7bb2-af63-7f477b570512`; workspace
`/Volumes/Mastermind/agent-workspaces/codex/ffcf/macro-main`; fresh-main branch
`codex/ci-throughput-ancestry-results-20261019`. Existing dirty checkpoint was
preserved through branch transition. Report/result/method/workstream updates are
prepared locally for batching with the next informative natural comparison.
Evidence root: `/Volumes/Mastermind/ci-pack-throughput-20261019/`.

PR9791 merged `c3c67487f42e1c54986b2e95dca327946fdc5ed0` at21:52:31Z.
Head a0153871732eeb4c3f24e733216d30ab89465f91; CI39324251115 success,
258 logical jobs/554 passed proof units/zero infrastructure findings. All active
checks passed; inactive pilot context remains intentionally red for main.
All8 candidate source/test/report blobs match merge: ancestry-landing-verification.json.
Plan2f6d0a326f72d5e4746dac5225d6c4ba528b47370d1bb0d64bb65e215a0f1564;
tested tree ff3996daeb00dd92c50f93865d685c4cd5044f5d.

Full log ancestry-trial-full.log consumed; no observer exists. The one log
acquisition terminal81373 is settled. Do not redownload accepted logs/tests.
Stage metadata ancestry-trial-run.json and ancestry-stage-costs.json retained;
inner costs ancestry-inner-costs.json. One initial metadata request hit cooldown;
after completing fresh-main integration, one eligible same-carrier read succeeded.
No alternate reader/reset/rerun. All earlier observer handles remain consumed.

Hosted reuse: one retaining-local-history notice before ruling-graph in pack10;
five incomplete-history consumers still deepen2->8. Correctness/mechanism proven,
counterfactual seconds saved unproven. Trial2527sec/362.57 summed wall minutes,
3sec gate wait; pack checkout2945sec; commands15075.19sec; installs177/1679.59sec.
FIF critical2396sec wall/229checkout/2120.20commands. Reuse pack10 noncritical.
Prior258-job global selects same set but3 execution definitions differ. No causal
fleet p95 gain, cost neutrality or30% target proved. Retain twelve packs/two weights.

Next: collect naturally concluded ci.yml PR first attempts created after
2026-10-19T21:52:31Z. Verify tested planner blob
f92be10fc37455fd427829f0f964c5ef581b3a80 and base ancestry from
c3c67487f42e1c54986b2e95dca327946fdc5ed0. Reuse compare_natural.py with
--merge/--blob/--output/--base-prefix ancestry-base- and post-* captures.
Plan artifacts ci-semantic-plan-RUNID-1. Snapshot ancestry-natural-runs-2356.json:
29runs/12verified successes/13pending/4cancelled/0reruns. Missing timestamps for
39332378137 recovered through same carrier; all12 plans/blob/base/jobs retained.
Existing compare_natural.py produced ancestry-natural-comparison/summary-2356.json.
Scoped successN11 p50/p951981/2863sec, wall196.25/278.23min; globalN1
3130sec/329.15wall. No completed failures. One original selected-set match
39341997524->39235580372 has changed dataos-identity-seams/research-factory-authority
execution definitions. Zero full proof matches to original or19 weighted controls.
No causal gain/cost-neutrality/30% claim; pending cohort may alter tail.

Natural full log39330880213 now retained (ancestry-natural-39330880213.log), no
redownload. Five deepening notices and one real reuse in noncritical pack8;
criticalpack11 has no consumer. Eight of12 plans co-locate consumers; two have
co-located consumers on critical packs:39336610321(pack5),39333873303(pack9).
Next useful investigation: full logs for those two, FIRST before same-run metadata;
metadata already captured23:56, respect300sec cooldown. Separate observed reuse
from potential exposure and actual command/install/checkout costs. No new source
slice until evidence warrants it. Batch report, ancestry-success-result.json and
ancestry-natural-comparison.json through normal source; prepared edits preserve
previous checkpoint. No repeated tests/log reads or report PR per wake.

Do not create an observer;
existing hourly automation is the return path. Exact selected/execution proofs,
outcome strata, exposure and pending/cancellation limitations remain binding.
Batch material natural results with prepared report updates through normal source;
no PR per wake and no source expansion until measured evidence justifies it.

Earlier settled: PR9722 dedup merge7736fd72895fc24e55bf2d4bbc7b1f4e94203414;
PR9763 calibration/schema merge38d2dac36faabfff04f8efe5ee28e5c8dfa1c5ae;
report9780 merge576e21dc2e46bea739465c84a33ffbdf2135cd78. Accepted tests/review
and raw costs stay retained. Optional weight review was denied preexecution
canonical_source_unreadable; no verdict/retry/bypass. Later schema repairs via9775
are settled. Preserve other writers, including unrelated PR8094 and FIF repair.

Prior weighted20:48 cohort:32runs/19verified/9pending/4cancelled. Scoped-success
N13 p50/p952106/3941sec, wall215.68/399.37min. Nine completions unexposed to
calibrated jobs; no original-baseline proof match. Exploratory adjacent exact pair
is unexposed and outcome-mismatched. Full details are already landed in the report
and weighted-natural-comparison.json; do not relax matching or blend treatments.

No artificial CI, peer messages, new control plane, speculative shards or unrelated
deployment. Preserve original root, writers and unresolved effects. Respect300sec
same-run cooldown. Notify material results only; after two unchanged wakes diagnose
once/back off60min. Pause only on completion or sole human/unknown-effect gate.
