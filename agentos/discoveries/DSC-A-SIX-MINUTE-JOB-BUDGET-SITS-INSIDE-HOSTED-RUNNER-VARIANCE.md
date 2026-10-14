---
key: A-SIX-MINUTE-JOB-BUDGET-SITS-INSIDE-HOSTED-RUNNER-VARIANCE
claim: >
  The legacy job `unrun-grading-board` (`.github/ci/legacy-jobs.yml`,
  `timeout-minutes: 6`, ubuntu-latest) runs a 246-test pytest step whose wall
  time on GitHub's hosted pool varies more than 3x between VMs in the same
  hour (~100 s on a healthy VM, 323 s / 331 s on a slow one), so a 6-minute
  budget is inside the pool's ordinary variance and the job can red a PR
  whose content changed nothing on that path. The red looks identical to a
  genuine regression in the pack summary.
falsifier: >
  Compare the step timings: ci run 38607052594 attempt 1 (PR #9368, head
  3b59d3aa) `unrun-grading-board` first step 323 s then 331 s, both killed by
  the 6-min budget (`CI_PACK_FAILED_JOBS=["unrun-grading-board"]`), against
  sibling run 38610150807 (99.69 s) and main baseline 38594781419 (~100 s)
  for the identical step; attempt 2 of the same head ran green with no code
  change. A local A/B of the step on the PR head vs the PR reverted measured
  84.81 s vs 84.65 s. Prophet sibling 38610150807 lost `unrun-factor-research`
  (8-min budget) to the same slow-VM hour.
so_what: >
  Before attributing a pack red that is a job TIMEOUT to the PR, compare that
  step's wall time with the newest main baseline and a concurrent sibling;
  a 3x slowdown with no module-level diff is the runner, and the lawful
  remedy is a re-run of the failed jobs, never an `--admin` merge over the red
  and never a content change to the PR. Durable fix = raise the budget to at
  least 3x the healthy wall time in a separate whole-pack heal PR; a 6-minute
  budget on a ~100 s step is one slow VM away from a false red.
kind: landmine
verified_at: 2026-10-14
verified_by: >
  ci run 38607052594 job ci-pack-8 log (saved as the seat's
  pr9368_pack8.log: `##[error]unrun-grading-board: timed out after 6
  minutes` at 17:45:20Z and 18:16:54Z); run 38610150807 and run 38594781419
  job timings; `gh run view 38607052594 --json jobs` after the re-run; local
  pytest A/B timings by ORCH-FIX.
scope:
  - macro
  - .github/ci/legacy-jobs.yml
  - scripts/run_ci_pack.py
confidence: verified
---

A legacy job's `timeout-minutes` is a per-job wall-clock fuse. On the hosted
`ubuntu-latest` pool the same pytest step ran ~100 s on three independent
VMs and 323–331 s on the VM that served PR #9368's first attempt, in the same
hour in which a Prophet sibling lost a different 8-minute job the same way.
The PR's diff touched nothing imported at module level by those tests, and the
re-run of the failed jobs on the identical head went green.

Related: `DSC:PACK-RUNNER-SKIPS-STEPS-AFTER-FIRST-RED` (why the summary shows
only the timeout and nothing after it); `DSC:MACRO-CI-LINUX-POOL-IS-THREE-RUNNERS-AND-STARVES-AT-FLEET-SCALE`
(the self-hosted pool has the opposite failure mode — queueing, not slow VMs).
