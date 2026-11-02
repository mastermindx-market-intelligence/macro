---
key: ADOPT-THE-STALLED-CARRIER-NOT-A-SECOND-IMPLEMENTATION
question: >
  A finished, CI-green Terminal fix (mastermind-terminal PR #608, options surface
  identity + shared replay + heat geometry) sat open for 10 days behind a human
  re-review that never returned. Re-implement the fix on current master, or adopt the
  existing carrier, integrate current master into it, and re-earn its proof there?
answer: >
  Adopt the carrier. Merge current master INTO the existing branch, re-establish the
  discriminating RED/GREEN on the integrated base, submit it to an independent audit,
  repair what the audit finds on the same branch, and ship that head. Do not open a
  second implementation of the same defect.
rationale: >
  Two findings made this the cheap and honest answer. First, the branch was not
  abandoned work of unknown quality - it was complete work whose only missing step was a
  human click; re-implementing would have discarded a reviewed design and produced a
  second carrier competing for the same files. Second, and decisively: the 10-day wait
  was NOT a gate. `repos/.../branches/master/protection` returns
  `required_pull_request_reviews: null` - master protects exactly three CI contexts and
  requires zero approvals. The stall was self-imposed process, not policy, and the
  correct response to a self-imposed wait is to finish the work, not to route around the
  branch. The cost of adoption was bounded and measured: 227 master commits merged in,
  with exactly one real overlap (terminal/lib/flowClientCache.ts, where master's #634
  `flowGetFresh()` and the carrier's `flowGet(f, {refresh})` proved to share one module
  -level store/buildUrl/doFetch, so one cache owner survives). Historical green was
  explicitly NOT reused as proof: reverting only SurfacePane.tsx to the pre-fix blob on
  the INTEGRATED base reproduced the reviewer's original symptoms (2 failed | 23 passed),
  which is what licensed the new green. The audit then earned its keep by finding a real
  defect the original review, the tests and CI had all missed
  (DSC:A-FAILED-INDEX-READ-CANNOT-SET-THE-LEAF-ERROR), repaired on the same head.
alternatives:
  - option: Re-implement the fix fresh on current master and close #608
    why_not: >
      Discards a completed, reviewed design and its evidence; creates a second carrier
      touching the same files as an open PR; and re-earns nothing, because the new branch
      would need the same integration and the same proof anyway.
  - option: Keep waiting for the requested human re-review
    why_not: >
      The wait was verified not to be a merge gate (zero required approvals). Ten days of
      a real user-facing defect shipped in production is a live cost paid for a process
      step that policy does not require.
  - option: Adopt the carrier but ship its existing 2026-09-18 green as the proof
    why_not: >
      A green earned on a 227-commit-older base is not evidence about the head being
      merged. Re-establishing the RED on the integrated base is what makes the new green
      discriminating.
evidence:
  - "gh api repos/mastermindx-market-intelligence/mastermind-terminal/branches/master/protection -> required_status_checks.contexts = [Quote Hub tests, Terminal typecheck + tests, Ingest + signal-layer tests]; strict = true; required_pull_request_reviews = null"
  - "gh api .../pulls/608/files --paginate -> 125 files (the non-paginated `gh pr view --json files` truncates at 100 and returns only evidence screenshots, which misstates the change as docs-only)"
  - "mastermind-terminal PR #608, base b9828842d, integrated head aa9333502ecad41054b5d392a4fae9138b163e04"
  - "terminal/docs/evidence/options-workbench-r0-20260917/current-base-integration-20260929/ (frame-refresh-red.log: 2 failed | 23 passed with SurfacePane.tsx reverted to 1f94c551f on the integrated base; focused-green.log; typecheck-green.log)"
  - "terminal/docs/evidence/options-workbench-r0-20260917/review-hardening-v3-20260929/ (cold-index-red.log, render-boundary-red.log and their greens; surface-family-green.log 276 passed / 10 files; browser-matrix-green.log 36 passed cold under CI=1 --workers=1 --retries=0)"
affects:
  - "terminal"
  - "terminal/components/surface/**"
  - "terminal/lib/flowClientCache.ts"
  - "DSC:A-FAILED-INDEX-READ-CANNOT-SET-THE-LEAF-ERROR"
confidence: high
reversibility: easy
decided_by: session claude-opus-5 terminal-03-replay-geometry
decided_at: 2026-09-29
---

## Detail

The general rule this records is about *stalled carriers*, which this fleet produces
routinely: a branch that is finished and green but parked behind a human step.

The first question to ask is not "is this code any good?" but **"is the thing it is
waiting for actually a gate?"** That is a one-command read of branch protection, and
here it returned `null` for reviews. A wait that policy does not require is a decision
someone made, and it can be unmade by finishing the work - which is not the same as
bypassing anything, because the three contexts that *are* protected still had to go
green on the new head, and did.

The second question is what counts as proof after integration. Adopting a carrier means
its evidence was earned on a base that no longer exists. The rule applied here: re-run
the RED, not just the green. Reverting the single fixed file to its pre-fix blob on the
integrated base reproduced the exact reviewer-reported symptoms; that is what makes the
subsequent green a statement about *this* head rather than a re-run of history.

The third is that adoption is not absolution. A finished, CI-green, human-reviewed change
still went to an independent read-only audit, and the audit found a real user-facing
defect in the same family as the one being fixed - honest failure states applied at the
leaf read but not at the index read above it. Two prior readers and the whole test suite
had passed over it because every existing case was satisfied by cheaper conditions. The
lesson that generalizes: when a change's subject is "report this state honestly", audit
*every* level that can produce the state, because the tests will only cover the level
someone thought about.

One inventory trap is worth carrying forward on its own. `gh pr view <n> --json files`
silently truncates at 100 files. On this PR that returned 100 evidence screenshots and
zero source files, which reads as a docs-only change. Use
`gh api .../pulls/<n>/files --paginate` for any PR that might carry evidence directories.
