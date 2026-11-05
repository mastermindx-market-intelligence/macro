---
workstream: "WS:CI-MERGE-CONTROL-PLANE"
session: "6e051448-2cc6-4432-93e6-166e660715a2 / claude/ssd-mastermindx-ci-workflow-ca9501-103ca38d7470b454"
model: fable
ended_because: ci_handoff
mission: >
  Fable CEO receiver for the MastermindX CI, independent-review and workflow
  acceleration program (Mastermind #917, handoff comment 6618966432). Reach
  minute-level PR CI across Mastermind, Macro and Terminal without dropping
  merge-path coverage; assess self-hosting on ubuntu1-4. Active checkpoint.
state_before: >
  Macro main 460760a9dd; Mastermind master b5e8a9682f with a twelve-entry merge
  queue; Terminal PR CI p50 54 min. Mastermind full CI 20m33s with shards
  624-1079 s; Macro PR ci p50 26 min p95 55 min. Macro PR CI hosted on
  ubuntu-latest; four Mac Studio self-hosted runners serve render and daily
  lanes only. Phase 1 review-policy ruling posted as #917 comment 6622731611.
changed:
  - path: agentos/handoffs/WS-CI-MERGE-CONTROL-PLANE-2026-11-04-ACCELERATION.md
    what: This checkpoint; the adjudicated cross-repo CI acceleration plan and runner findings.
verified:
  - claim: All three repositories are public, so hosted ubuntu-latest is the 4 vCPU free tier.
    command: gh api graphql repository visibility for Mastermind, macro, mastermind-terminal
    result: PUBLIC private=false for all three.
  - claim: ubuntu0 has no GitHub Actions runner installed.
    command: ssh mmx-ubuntu0 systemctl list-units plus runner directory and Runner.Listener process search
    result: 32 cores 29G RAM load 5.5; no runner service, directory or listener process; Fabric lanes only.
  - claim: The Macro sweeper is not cron-starved; its binding limiter is the in-flight proof cap after a check-definition commit.
    command: gh run view 41773787061 --log filtered on 10652, cap and stale
    result: 41 of the last 100 sweeps succeeded; sweep reports global cap 8 with 0 CI workload slots and 15 armed PRs refresh-deferred because main commit 3a03a77296b8 changed check definitions.
  - claim: Mastermind merge-group shard imbalance and queue wait are measured, not assumed.
    command: gh run view 41772104126 --log filtered on CI_MODULE plus local timestamp analysis
    result: 1791 modules; reported seconds per shard 868/1048/632/529/1184/976; shards started 3.5 to 10.3 min after run creation; fan-in 2.7 min after the last shard.
  - claim: The rebalanced six-shard placement keeps the exact partition and passes the planner policy tests.
    command: python3.12 scripts/ci_pytest.py --plan-only --jobs 6 and pytest tests/test_ci_pytest_policy.py tests/test_ci_parallel_fanin.py in the Mastermind worktree
    result: discovered=1797 running=1797 shards 332/269/276/298/296/326; 189 passed; predicted reported load 863/863/932/857/862/857 s.
next_actions:
  - Mastermind #2044 (shard re-pin) needs one fresh non-author review, then the merge queue; accept only when a merge-group run shows shard steps within about 15 percent of each other.
  - Mastermind M3 per-shard setup trim after #2016 merges (same ci.yml region); M1 in-shard xdist canary on one shard; M5 queue-required Mastermind OS frontend test is a Chairman or admin ruleset decision.
  - Terminal T4 split terminal-unit and cache Playwright there; T1 e2e against next build plus next start with an e2e-only flag and a negative test; T3 PR-time shard reduction only with merge-time full coverage.
  - Macro X1 scope the check-definition staleness rule by plan digest plus definition content hash, and X2 adaptive MAX_IN_FLIGHT_PR_PROOFS, both after #10652 then #10682 land (same file, live writers).
  - Self-hosting on ubuntu1-4 is CONDITIONAL-GO for Terminal e2e shards only (ephemeral one-job runners, restricted runner group, same-repo PRs, Fabric isolation, hosted fallback, canary first); NO-GO for merge, control or secret-bearing jobs; org runner registration needs an admin token.
do_not_redo:
  - Phase 1 review-policy ruling (#917 comment 6622731611): ROUTINE tier not FAST widening; seven CRITICAL pins; CRITICAL dispatch by tier.
  - Mastermind #2044 shard re-pin; #1989 #2000 #1570 merged; #2003 superseded by #1977; Macro review-once guard is already #10682.
  - The CI speed survey and self-hosting verdict (#917 checkpoint 3); do not re-survey without a changed measurement.
danger_areas:
  - scripts/merge_on_green.py has live writers (#10652 then #10682); any X1 or X2 edit lands after them.
  - A main commit touching ci.yml or fences.yml stales every armed Macro green at once; batch such commits.
  - Self-hosted runners on public repos expose the host to PR-authored YAML unless the runner group is restricted to main-defined workflows.
unverified:
  - The in-shard pytest-xdist speedup (M1) and the next-build e2e speedup (T1) are estimates until one canary run each.
  - The 500 concurrent-job Enterprise cap versus the 180/180 figure recorded in scripts/merge_on_green.py is unreconciled.
  - ubuntu1, ubuntu2 and ubuntu4 core counts and runner state were not observed.
unresolved:
  - Org runner API and runner-group listing return 403 for the current token; registration on ubuntu hosts is a human admin step named once.
  - Larger hosted runners are billed on public repos, so they are a Chairman spend decision; not taken.
evidence:
  - "Mastermind #917 comments 6622623037 (ACK), 6622731611 (Phase 1 ruling), 6622889443 (checkpoint 2), 6623031525 (checkpoint 3)"
  - "Mastermind #2044 with ci/shard_timings/41772104126.json"
  - "Macro sweep run 41773787061; Mastermind merge-group run 41772104126"
---

# WS:CI-MERGE-CONTROL-PLANE — 2026-11-04 acceleration checkpoint

Rung reached: Phase 1 ruling DELIVERED; Phase 4 first packet DELIVERED as Mastermind #2044 (review pending, not queued, not merged). Nothing in this checkpoint is production proof.

Full adjudication, arithmetic and sources live in Mastermind #917 checkpoint 3. This record exists so the Macro workstream owner can recover the plan without the Mastermind thread: the Macro-side actions are X1, X2 and X3 above, all sequenced behind #10652 then #10682 on `scripts/merge_on_green.py`.
