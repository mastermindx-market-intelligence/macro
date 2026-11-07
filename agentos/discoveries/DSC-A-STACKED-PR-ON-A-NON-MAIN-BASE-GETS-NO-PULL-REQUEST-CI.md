---
key: A-STACKED-PR-ON-A-NON-MAIN-BASE-GETS-NO-PULL-REQUEST-CI
claim: >
  A macro PR whose base branch is not main carries a structural `ci-authority` FAILURE
  (`{"schema":"ci.authority.v1", ..., "reason":"unsupported_base_ref"}`) and schedules NO
  `pull_request` ci.yml or fences.yml runs at all, so its head is never proven by CI until the
  PR is retargeted to main. The red is a property of the base ref, not of the diff.
falsifier: >
  A stacked macro PR (base = another feature branch) whose newest ci-authority check concludes
  SUCCESS, or for which `gh run list --commit <head> --json workflowName` lists a ci.yml or
  fences.yml run triggered by `pull_request`.
so_what: >
  Never try to "heal" the ci-authority red on a stacked PR and never arm it; the only fix is
  landing the base and retargeting. Do not retarget early either: the stacked diff would then
  carry every path of its base PR. Judge a stacked lane result from a local test run on its
  head (the seat did: 192 passed / 56 skipped on #8486) and record it as PARKED by inheritance.
kind: constraint
verified_at: 2026-10-05
verified_by: >
  PR #8486 (base claude/gmi-w3c-seams-… of #8417): ci-authority check output JSON
  reason=unsupported_base_ref; `gh run list --commit 2e2bcd75ca62 --json workflowName` -> [].
scope:
  - macro
  - .github/workflows/ci.yml
  - .github/workflows/fences.yml
confidence: verified
cited_by:
  - WS:GMI-THEME-GRAPH
---

Observed on 2026-10-05 while judging the Wave D2 lane result on PR #8486, which was opened by a
fabric lane against #8417's branch because its module imports the D1 seams. The PR showed exactly
one check, `ci-authority`, concluding FAILURE with the `unsupported_base_ref` reason, and the
head commit had zero workflow runs. The same head's tests pass locally. The repository's merge
sweeper and the ship-loop guard both read check state, so a stacked PR looks "red" to every
instrument while being structurally unprovable rather than broken.
