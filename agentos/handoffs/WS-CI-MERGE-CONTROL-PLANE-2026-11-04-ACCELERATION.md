---
workstream: "WS:CI-MERGE-CONTROL-PLANE"
session: "6e051448-2cc6-4432-93e6-166e660715a2 / claude/ssd-mastermindx-ci-workflow-ca9501-103ca38d7470b454"
model: fable
ended_because: ci_handoff
checkpoint: "6 (2026-11-05, after the Chairman reconciliation request)"
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
    what: This checkpoint; the adjudicated cross-repo CI acceleration plan and runner findings, amended at checkpoint 6 with the reconciliation and the three open lanes.
  - path: "Terminal PR 1297 (scripts/ci_pr_scope.py, .github/workflows/ci.yml, tests/test_ci_pr_scope.py)"
    what: Terminal fast mode. A trusted-base classifier executed from the PR base commit decides mode docs or full from Git objects only, with a positive allowlist (Markdown under docs and terminal/docs minus the trees and files that code or tests read, plus raster evidence images); docs mode skips hub, unit, e2e, ingest and PostgreSQL work while the frozen required contexts still report; everything unqualified is full.
  - path: "Macro PR 10745 (scripts/run_ci_pack.py, tests/test_run_ci_pack_base_replay_env.py, .github/ci/legacy-jobs.yml)"
    what: The exact-base replay child environment keeps CI (and PYTHONUTF8) so pytest prints the same failure message on both sides and semantic failure atoms match; the allowlist is a named constant with a whole-word secret-name test, wired into ci-control-plane-contracts.
  - path: "Mastermind PR 2065 (scripts/ci_pytest.py, scripts/ci_parallel_shard.py, scripts/ci_pytest_timing.py, scripts/ci_xdist_guard.py, .github/workflows/ci.yml, pyproject.toml)"
    what: Every six-shard job runs pytest-xdist with four workers (loadfile, no worker restart) with a controller-only completion guard that fails a shard when a worker is lost or fewer tests finish than were collected, a pinned PYTHONHASHSEED for identical worker collection, and a controller-aware CI_MODULE timing reporter.
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
verified_checkpoint_6:
  - claim: Terminal had no PR fast mode; Mastermind has pr_scope and pr_fast tiers (2016, 2057 merged); Macro has the semantic plan and no-work pack skip but no PR tier.
    command: read of the three ci.yml files on their default branches and of Mastermind 917 comments through 6648077765
    result: Terminal 1297 built; Mastermind tiers unchanged; Macro PR-tier work not started (semantic plan already skips no-work packs).
  - claim: The Terminal classifier survived an independent adversarial review after repair.
    command: Opus reviewer subagent, read-only, replaying synthetic merge commits against head 43aec0c34 then 549711233
    result: first cut REJECT (GITHUB_OUTPUT newline injection, docs class held files read by code and tests, classifier trusted on non-default bases); repaired head ACCEPT-WITH-NITS; 61 scope tests and 66 CI-parsing and sweeper tests pass.
  - claim: The Macro 10735 pack-11 base-red mismatch was an environment defect, not a candidate failure.
    command: pytest short-summary behaviour under CI versus not, compared with scripts/ci_semantic_proof.py atom construction (reviewer cited _pytest/terminal.py and compat.py)
    result: replay without CI prints no failure message, so reason-hash atoms never match; fix at Macro 10745 head c8699c68f, reviewer ACCEPT-WITH-NITS after a wiring and test repair.
  - claim: pytest-xdist 3.8.0 exits 0 with no tests ran when a worker dies during import or collection.
    command: reviewer probes c and f (worker exit at import, SIGKILL after collection) under -n 4 --dist loadfile --max-worker-restart 0
    result: rc 0 before the guard; rc 1 with CI_XDIST_GUARD lines at Mastermind 2065 head 2cb89e7f9; healthy runs with deselection, skips, xfail and xpass print no guard line.
next_actions:
  - Terminal 1297 is armed with GitHub auto-merge after update-branch; once merged, open or observe one docs-only PR and record its wall time (target about 3 min versus p50 54 min) as the fast-mode PRODUCTION_PROOF.
  - Macro 10745 is armed merge-on-green with review requested from mastermindx-2; it is a global invalidator (full 384-job plan). After it lands, update-branch Macro 10735 so its pack-11 replay re-runs with CI set, then let the sweeper clear the stale merge-blocked.
  - Mastermind 2065 is armed for the merge queue with review requested from mastermindx-2; its own CI run is the measurement: compare each pytest_shards job and ci/shard_timings against the serial baseline (p50 about 20 min, floor 789 s for tests/test_capacity_host_artifacts.py on shard 2). Accept only if every shard is green and no module fails only under xdist.
  - Terminal 1277 (self-hosted e2e canary workflow) is armed; on merge re-mint a JIT runner on ubuntu0, dispatch selfhosted-e2e-canary.yml with shard desktop-1 at workers 1 then 4, compare with the hosted baseline (13m32s queue plus 51m55s run), then deregister the runner.
  - Mastermind #2044 (shard re-pin) needs one fresh non-author review, then the merge queue; accept only when a merge-group run shows shard steps within about 15 percent of each other.
  - Mastermind M3 per-shard setup trim after #2016 merges (same ci.yml region); M1 in-shard xdist canary on one shard; M5 queue-required Mastermind OS frontend test is a Chairman or admin ruleset decision.
  - Terminal T4 split terminal-unit and cache Playwright there; T1 e2e against next build plus next start with an e2e-only flag and a negative test; T3 PR-time shard reduction only with merge-time full coverage.
  - Macro X1 scope the check-definition staleness rule by plan digest plus definition content hash, and X2 adaptive MAX_IN_FLIGHT_PR_PROOFS, both after #10652 then #10682 land (same file, live writers).
  - Self-hosting on ubuntu1-4 is CONDITIONAL-GO for Terminal e2e shards only (ephemeral one-job runners, restricted runner group, same-repo PRs, Fabric isolation, hosted fallback, canary first); NO-GO for merge, control or secret-bearing jobs; org runner registration needs an admin token.
do_not_redo:
  - Terminal 1297 classifier design and its review repairs; Macro 10745 replay-env root cause; Mastermind 2065 xdist guard and hash-seed pin; Macro 10738 fif-kernel xdist (head 0059d4432, binding checks green, sweeper-owned).
  - Phase 1 review-policy ruling (#917 comment 6622731611): ROUTINE tier not FAST widening; seven CRITICAL pins; CRITICAL dispatch by tier.
  - Mastermind #2044 shard re-pin; #1989 #2000 #1570 merged; #2003 superseded by #1977; Macro review-once guard is already #10682.
  - The CI speed survey and self-hosting verdict (#917 checkpoint 3); do not re-survey without a changed measurement.
danger_areas:
  - scripts/merge_on_green.py has live writers (#10652 then #10682); any X1 or X2 edit lands after them.
  - A main commit touching ci.yml or fences.yml stales every armed Macro green at once; batch such commits.
  - Self-hosted runners on public repos expose the host to PR-authored YAML unless the runner group is restricted to main-defined workflows.
unverified:
  - Shard wall time under four xdist workers and the docs-only Terminal PR time are estimates until the two CI runs above conclude.
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
  - "Checkpoint 6 lanes: Terminal 1297 and 1277, Macro 10745 and 10738, Mastermind 2065; Macro 10735 run 41925067587 pack 11 (replay-env defect)"
---

# WS:CI-MERGE-CONTROL-PLANE — 2026-11-04 acceleration checkpoint

Rung reached: Phase 1 ruling DELIVERED; Phase 4 first packet DELIVERED as Mastermind #2044 (review pending, not queued, not merged). Nothing in this checkpoint is production proof.

Full adjudication, arithmetic and sources live in Mastermind #917 checkpoint 3. This record exists so the Macro workstream owner can recover the plan without the Mastermind thread: the Macro-side actions are X1, X2 and X3 above, all sequenced behind #10652 then #10682 on `scripts/merge_on_green.py`.
