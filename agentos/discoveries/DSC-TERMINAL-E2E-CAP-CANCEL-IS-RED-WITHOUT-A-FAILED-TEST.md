---
key: TERMINAL-E2E-CAP-CANCEL-IS-RED-WITHOUT-A-FAILED-TEST
claim: >
  In charting-app, a Terminal e2e shard job that hits `timeout-minutes: 60` in
  `.github/workflows/ci.yml` concludes `cancelled` with zero failed tests, the aggregate
  required check "Terminal typecheck + tests" then fails, the session observer and
  `scripts/merge_on_green.py` both classify the head as red, and the controller's
  `sweep()` marks the PR `merge-blocked` and never refreshes it, so the PR stays blocked
  until something other than the controller pushes a new head.
falsifier: >
  For a run cancelled at the cap (precedents 38197231252 and 38199198159), run
  `gh api repos/<owner>/mastermind-terminal/actions/runs/<id>/jobs --jq '.jobs[] | "\(.name)|\(.conclusion)"'`
  and `gh run view <id> --repo <owner>/mastermind-terminal --log --job <tablet job id> | grep -c '✘'`.
  The claim is false if the tablet job's conclusion is not `cancelled`, or if the grep
  counts one or more failing test lines, or if a cold rerun of the same head
  (`cd terminal && CI=1 npx playwright test --project=tablet --workers=1 --retries=0`)
  yields a failure that survives `--last-failed`. It is also false if
  `scripts/merge_on_green.py` `sweep()` (lines 400-412) refreshes a PR whose
  `check_verdict` is red instead of marking it blocked and continuing.
so_what: >
  Treat a cap cancel as a capacity event, not a defect: do not rerun the same run (same
  matrix, same cap), do not raise the cap, do not touch the specs. Land the shard split
  (DEC:TERMINAL-E2E-SHARD-AT-CAP-SPLITS-NEVER-RAISES, Terminal #963) and then refresh each
  blocked head by hand with `gh api -X PUT repos/<owner>/mastermind-terminal/pulls/<n>/update-branch
  -f expected_head_sha=<head>` (or merge origin/master into the branch and push), because
  the controller refreshes only green BEHIND heads. If the suite's determinism is in
  doubt, prove it with a cold Linux full-matrix rerun of the exact head rather than with
  CI retries.
kind: landmine
verified_at: 2026-10-12
verified_by: >
  Runs 38197231252 (Terminal #959 at 06299948f) and 38199198159 (#960 at 7733e1b58) read
  2026-10-12: tablet job `cancelled` at the cap, no failing test line; #960 carried
  `merge-blocked` + `merge-on-green` with the controller skipping it on every sweep.
  Cold Linux full-matrix reruns of 7733e1b58 (ubuntu2) and the E07 head 03054a695
  (ubuntu0), workers 4, retries 0: every red case passed its `--last-failed` serial rerun,
  no deterministic failure. scripts/merge_on_green.py lines 407-409 read in the
  charting-app checkout: red -> mark_blocked("... the latest required CI is red") -> continue.
scope:
  - "charting-app"
  - ".github/workflows/ci.yml"
  - "scripts/merge_on_green.py"
  - "terminal/e2e/**"
  - "WS:TERMINAL-ENHANCEMENTS20"
confidence: verified
---

## Grounds

Playwright reports failures per test; a job killed by the runner's timeout reports none,
so the usual signal (a `✘` line, a `--last-failed` rerun) is absent. The required context
is the aggregate job, which fails when any shard does not succeed, so a cancel is
indistinguishable from a red to branch protection and to anything that reads the check
conclusion. The controller deliberately refuses to refresh red heads (a refresh would
mask a genuine failure), which is correct for real reds and a trap for cap cancels.

Observed 2026-10-12 during terminal-enhancements20: train 3 (#960) and the chart-pane
repair (#959) both went red at the tablet cap within an hour, every armed PR showed the
same `red:Terminal,shard:e2e tablet` row in the observer, and the only green run that
hour was #963's split matrix, whose halves finished in 13-32 minutes.

## What a session does with this

- Read the job conclusions before diagnosing a "red" e2e head; `cancelled` with no
  failing test lines means the cap, not the code.
- After the split is on master, the manual refresh is the unblocking act; the controller
  then removes `merge-blocked` on its own once the fresh run is green.
- Related: DEC:TERMINAL-E20-LANDING-TRAINS-ONE-CI-ONE-SQUASH (why every armed PR shares
  one CI critical path) and the Terminal memory `ci-e2e-flake-roulette` (rotating e2e
  reds that are real but non-deterministic are a different failure class: rerun, never
  bypass).
