---
key: A-JOB-TIMEOUT-RUNS-THE-ALWAYS-TAIL-INSIDE-A-BOUNDED-GRACE
claim: >
  A GitHub Actions job-level `timeout-minutes` does NOT make the `if: always()` /
  `if: cancelled()` tail unreachable. At the cap GitHub cancels the job and then keeps
  scheduling the remaining steps for a bounded grace of about five minutes; the tail is
  lost only when that grace is EXHAUSTED, and then every unreached step carries a null
  `started_at` rather than a `cancelled`/`skipped` conclusion. Both outcomes are measured
  on the same `collect` job at the same 240m cap. SURVIVED — job 105033526139 (run
  35168062576, 2026-09-17): cap fired 04:48:55Z, `push market data` completed 04:50:53Z,
  `salvage push` succeeded 04:50:57Z, the W2 finish recorded its row 04:51:42Z, job ended
  04:51:54Z = cap+2:59. EXHAUSTED — job 107895940199 (run 36078806272, 2026-09-25): cap
  fired 04:43:08Z, `commit market data` still ran 04:43:31→04:45:40Z INSIDE the grace, the
  push then started at cap+2:32 with ~2:28 left, and the job was killed at cap+5:00 with
  steps 32-38 all null. The practical consequence is that a post-cap belt is real but has
  a hard ceiling, so it may never be sized as a budget: the `market-commit-push` band was
  9.6m (09-23) and 10.7m (09-24), roughly twice the grace, which is the actual reason the
  09-25 checkpoint could not be rescued. The null `started_at` is also the field that
  distinguishes the two cases — an ordinary cancellation leaves timestamps behind.
falsifier: >
  Query the two jobs and compare against the cap:
  `gh api repos/mastermindx-market-intelligence/macro/actions/jobs/105033526139 --jq
  '.steps[]|select(.number>=31)|"\(.number) \(.conclusion) \(.started_at)"'`
  The claim is falsified if step 32 (`salvage push`) does NOT show `success` with a
  `started_at` later than 04:48:55Z, or if job 107895940199's steps 32+ show any non-null
  `started_at`. It is also falsified if a future run shows a tail step starting more than
  ~5 minutes past its cap, which would mean the grace is not bounded near five minutes.
  Whether ~5:00 is a GitHub constant or runner-configurable is NOT established here —
  only that it is bounded and that both sides of the bound have been observed.
so_what: >
  The false form of this belief ("a job timeout skips the always() tail entirely") is
  actively harmful in two opposite directions and both have shipped. Believing the tail
  ALWAYS runs makes a cap look covered by a salvage step that will not be scheduled —
  that is the 2026-09-25 lost checkpoint, where a committed night of collections never
  reached the remote and no W2 row exists for the night at all. Believing it NEVER runs
  declares dead a lever that measurably works, namely shrinking the post-cap tail so it
  fits the grace; PR #8008 asserted exactly that in four places in `daily.yml` and was
  caught only by an independent review that pulled the 09-17 job. When reasoning about a
  capped job, read `steps[].started_at` from the jobs API, never the run log: after a
  cancel the surviving cleanup steps tick seconds apart and mimic an almost-finished tail.
kind: runtime
verified_at: 2026-09-29
verified_by: "gh api repos/mastermindx-market-intelligence/macro/actions/jobs/105033526139 --jq '.steps[]|select(.number>=28)'"
scope:
  - macro
  - .github/workflows/daily.yml
  - scripts/ci/nightly_timings_finish.sh
  - tests/test_daily_collect_commit_path.py
confidence: verified
---
