---
workstream: "WS:CI-MERGE-CONTROL-PLANE"
session: "01a153e8-3c85-7bb2-af63-7f477b570512 / codex/ci-throughput-parser-20261020"
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

# Current checkpoint — October 20, 2026

Original root01a153e8-3c85-7bb2-af63-7f477b570512. Working branch
codex/ci-throughput-parser-20261020 starts at pinned main
d52827f26b062f67d594350a65becf406710d4d1. Own report edits carried intact.
Source and result history: research/ci_pack_throughput_20261019/README.md.
Raw evidence: /Volumes/Mastermind/ci-pack-throughput-20261019/.

Settled source releases9722/9763/9791 and reports9780/9801 are accepted;
all observers and log downloads are settled, no CI observer remains.
Latest implementation9791 merged c3c67487f42e1c54986b2e95dca327946fdc5ed0;
report9801 merged368c4c3a660215a0bf4809c9b8ff5e65098f413a, six blobs verified.
Do not repeat accepted logs/tests. Optional weight review was denied before
execution (canonical_source_unreadable); no verdict or bypass. Initial dedup
review accepted on original ID; it does not cover subsequent changes.

Natural00:55 cohort is FIXED:45runs,31qualified first attempts(29success/2failure),
7pending/7cancelled. Scoped successN27 p50/p951966/2863sec, summedwall186.47/278.23min.
Zero full execution-proof matches to original or weighted baseline. Critical ancestry
reuse proven in39336610321/39333873303 retained logs; counterfactual cost unknown.
Six slowest scoped successes are FIF-alone critical; twelve packs remain appropriate.
Candidate-specific failures39342972042(PR9479) and39342630438(PR9797) have passing
isolated bases; preserve their existing carriers. No duplicate heals or cohort expansion.

FIF localization: exact hosted tree ff3996daeb00dd92c50f93865d685c4cd5044f5d,
2121 collected node IDs. Ordinals1441..1512 map70publisher+2freshness tests;
count equality alone is not hosted order/timing proof. Exact original run36308
settled:72pass/42inherited cleanup warnings/403.73sec. Slowest unchanged-refusal
publisher test42.37sec. Focused cProfile2162 settled:1pass/94.36sec including
profiling overhead;52parses/60.24cumulative sec;67.5million ASCII generator calls;
36618 direct-text calls scan complete event lists. Retained fif-slowest.pstats and
fif-slowest-profile-summary.json, no reprofile needed.

Fourth bounded trial changes only collectors/sec_filing_parser.py:
bytes.isascii replaces equivalent Python byte loop; direct text uses the existing
source-order bisect index but retains owner identity and includes excluded text.
Plain list fallback, parser limits, refusals, result/proof formats, commands,
shards and CI selection are unchanged. Active FIF9761/9794/9799 checked; their
paths do not overlap parser/tests. No producer or registry edits.

Local checks:214parser tests pass, including new mixed-content/sibling scan
regression; that regression fails against original function. Publisher parity3178
settled:52calls/two distinct large filing documents, full outputs identical.
Unprofiled slowest test29.41sec after vs42.37before, descriptive local evidence.
Run84051 settled:72pass/42inherited warnings/335.45sec vs403.73before.
Alternating2document medianCPU0.8960->0.6836sec(23.7percent), outputs identical.
Logs/parser-benchmark.json and fif-targeted-after-result.json retained.
All local runners settled. Next: batch fixed-cohort evidence with this source trial,
normal PR/required hosted checks/merge, verify landing. No causal fleet30% or
cost-neutrality claim. No artificial CI or workflow dispatch.

Profiling checkout remains detached and unchanged at exact hosted tree:
/Volumes/Mastermind 2/agent-workspaces/claude/14851c4656838a3b/ci-fif-profile-20261020-d2a18633b13632ae
Do not remint/adopt it. Its helper receipt retains its original branch identity.
Main checkout's earlier moving-ref switch race was diagnosed and repaired only
on eight exact parent-tree reversals; own report edits preserved. Use pinned SHAs
for switches, never reset/clean/stash or touch another writer.

Preserve root, active writers and unknown effects. No peer messages, control plane,
speculative shards or unrelated deploy. Full logs FIRST before same-run metadata;
300sec read cooldown, no alternate reader/reset. Existing hourly heartbeat only;
notify material results, diagnose after two unchanged wakes, back off60min.
Pause only on completion or a sole identified human/unknown-effect gate.
