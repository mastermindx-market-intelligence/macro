---
key: ALWAYS-ON-A-JOB-OPTS-OUT-OF-RUN-CANCELLATION
claim: >
  A job-level `if: always()` in a GitHub Actions workflow opts that job out of RUN
  CANCELLATION, not merely out of the needs-failed/needs-skipped default. In ci.yml the
  `ci-pack` matrix led with `always()`, so `concurrency.cancel-in-progress: true` -
  which the workflow sets for every `pull_request` event and whose own comment calls
  cancelling superseded packs "pure savings" - never once cancelled a pack. Measured
  over 9 superseded pull_request runs on 2026-09-20: 108 of 108 pack jobs concluded
  `success` or `failure` and ZERO concluded `cancelled`, every superseded run showing
  the identical natural-completion signature {success: 10, failure: 2}. Packs ran up to
  29 minutes past the commit that obsoleted them, burning a mean 57 runner-minutes per
  superseded run (p50 31, max 161). 29.7% of all concluded ci runs (33/111) are
  superseded, so ~31 hosted runner-hours were being discarded per 7h window. The control
  is inside the same runs: `contract-delta` carries no `always()`, received the same
  cancel signal, and died within 16 seconds.
falsifier: >
  Observe a superseded `pull_request` run of ci.yml whose ci-pack jobs conclude
  `cancelled` while the job condition still leads with `always()`; or show a superseded
  run where pack `completed_at` never exceeds the superseding run's `created_at`. Either
  refutes the mechanism. Reverting `!cancelled()` back to `always()` and observing packs
  still cancel would likewise refute it.
so_what: >
  Never reach for `always()` to mean "run even if a need was skipped or failed" - that is
  `!cancelled()`, which is the same predicate MINUS cancellation immunity. Reserve
  `always()` for jobs that must publish a verdict even on a cancelled run; `ci-gate` is
  the legitimate case and keeps it. The waste this causes is INVISIBLE: every affected
  run is green, no check reds, and the cost appears only as hosted spend and as pool
  contention that surfaces the moment capacity stops being free. Auditing a workflow for
  cancellation behaviour means reading job `if:` conditions, NOT just the `concurrency`
  block - the concurrency block was correct the whole time. Downstream was already
  written for the fixed behaviour: scripts/merge_on_green.py treats `cancelled` as
  INCOMPLETE ("a superseded/cancelled runner is not evidence against the pull request"),
  a branch that was unreachable while `always()` stood.
scope: [macro]
confidence: verified
kind: landmine
verified_at: 2026-09-20
verified_by: >
  .github/workflows/ci.yml ci-pack `if:` (led with `always()`) vs `concurrency.
  cancel-in-progress: ${{ github.event_name != 'workflow_dispatch' }}`;
  gh api /repos/mastermindx-market-intelligence/macro/actions/runs/<id>/jobs over runs
  35494134933, 35494194161, 35495080110, 35495083079, 35495702604, 35495880067,
  35496306877, 35496459148, 35491651576 (108 pack jobs, 0 cancelled);
  run 35496306877 shows contract-delta cancelled 07:17:18Z against packs finishing
  07:24-07:45Z after supersession at 07:17:02Z;
  scripts/merge_on_green.py:308-310 INCOMPLETE_CONCLUSIONS;
  repair + discriminating test in PR #7513.
---

The trap is that the `concurrency` block reads correct and IS correct. ci.yml's
cancel-in-progress was deliberately made event-conditional on 2026-08-09 to end a
main-proof livelock, and its comment states the PR-side intent explicitly. Nothing in
that block is wrong. The cancellation was consumed one layer down, by a single token at
the head of the consuming job's condition, and no test or check could see it: a
superseded run's packs completing successfully is indistinguishable from a healthy run.

Cost is measured in `jobs` API timings, never the run list. The run-level record of a
superseded run reports `conclusion: cancelled`, which reads like the savings were taken.
Only the per-job `started_at`/`completed_at` show twelve packs running to term.

Note the asymmetry that makes this diagnosable at all: a run carries exactly one cancel
signal, so any job in the same run that DOES cancel proves the signal arrived. Look for
that control before concluding a platform-level cancellation failure.
