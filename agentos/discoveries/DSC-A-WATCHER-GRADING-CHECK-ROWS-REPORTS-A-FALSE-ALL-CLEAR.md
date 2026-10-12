---
key: A-WATCHER-GRADING-CHECK-ROWS-REPORTS-A-FALSE-ALL-CLEAR
claim: >
  A CI watcher that decides "all checks concluded" from the rows of `gh pr
  checks` is measuring its own field of view, not the state of the head. A pull
  request's check list is a VIEW over the runs currently bound to its head, so
  it SHRINKS when the head moves: on a re-push the superseded head's rows leave
  the pull request with it, while the new head's `ci` run is queued and
  publishing none - and every "nothing is pending" predicate written over that
  list is satisfied by an empty or partial one. Measured on PR #8105,
  2026-09-27: a watcher logged `PENDING=13` naming six `ci-pack-*` at 23:08:15Z
  and `PENDING=0 | ALL CONCLUDED` at 23:13:17Z, then exited 0. Nothing had
  passed in the interval. The branch had been re-pushed; the 13 rows belonged to
  the abandoned head, the live head's `ci` run was `pending` in the queue, and
  the only red left standing was the by-design, sweeper-excluded
  `ci-authority/codex/merge-queue-pilot` - so the log read exactly like a clean
  green on a fully settled pull request. The window is not a momentary race:
  the superseded head's `ci` run held the branch concurrency group
  `in_progress`, so the live head's run stayed `pending` and the false all-clear
  would have stood for as long as that lock did.
falsifier: >
  At the moment any watcher reports concluded, ask the runs instead of the rows:
  `gh pr view <n> --json headRefOid` then `gh run list --branch <branch> --limit
  20 --json workflowName,status,conclusion,headSha`, keeping only rows whose
  `headSha` equals that head. If any such run is not `completed`, or if no run
  exists for that head at all, the verdict was not a verdict. Independently,
  check the rows for the binding gate BY NAME - `ci-gate` absent from `gh pr
  checks` means the pack set has not been published yet (`ci-plan` needs ~4
  min), so the list cannot be complete no matter how few rows are pending. A
  watcher whose exit condition cannot distinguish "every expected check passed"
  from "no checks are listed" is falsified by construction and needs no
  experiment.
so_what: >
  Fleet law tells every seat to hand an external wait to a durable watcher and
  explicitly forbids paying for it with per-Stop polling, so the watcher's
  notification IS the seat's evidence that a head is proven. A watcher that can
  report a false all-clear therefore converts the anti-polling rule into a
  merge-on-nothing: the next act after `ALL CONCLUDED` is a hand merge, an
  `--admin`, or a report of SHIPPED, each taken against a head whose packs never
  ran. That is the same defect as the merges that beat their own checks, reached
  by an instrument the seat trusted rather than by impatience. The cure costs
  two extra `gh` reads per poll: grade the RUNS at the current head first, read
  check rows only once those runs are completed, and refuse to emit any verdict
  while the binding gate name is missing from the rows. The second, separable
  fact is worth keeping: a superseded run can sit `in_progress` holding the
  branch concurrency group so the live head's run never starts - diagnose a
  long-`pending` run by listing the branch's runs per head, and cancel the
  abandoned one, which is releasing a lock rather than outrunning CI.
  A third fact outranks both, because it survives a fully correct watcher:
  a verdict is bound to the head it graded and expires when that head moves.
  Re-read `headRefOid` in the same breath as the merge and refuse to act on a
  verdict that names a different sha - the mover is often the merge sweeper
  itself, whose update-branch refresh is exactly what a seat waiting for that
  sweeper is least likely to suspect.
kind: landmine
verified_at: 2026-09-27
verified_by: >
  Claude Opus 5 seat c6467452 (GMI Industrials first vertical, operation
  gmi-industrials-fable-ceo-e2e-20260924-chairman-001), on its own PR #8105.
  The false verdict is in the watcher's own log, four lines, timestamps
  23:03:14Z-23:13:17Z. Disproved with `gh run list --branch
  claude/ind-requirement-traceability --json databaseId,workflowName,status,conclusion,headSha`,
  which showed `ci` `pending` at head `54821ee935c0` while `ci` at the
  superseded `e693458e6da2` was still `in_progress`, and with `gh pr checks
  8105` returning ten rows carrying no `ci-gate` and no `ci-pack-*` at all.
scope: [macro, agentos, all-programs]
confidence: verified
---

## Detail

The watcher was a correct, quota-lawful instrument in every other respect: one watcher per
endpoint, a 300s interval well above the guard's 90s floor, one log line per poll, exit on
settle. It was wrong only in what it compared.

```
23:03:14Z poll 1: PENDING=3  FAIL=ci-authority/codex/merge-queue-pilot | still: fence-pack,contract-delta,ci-plan
23:08:15Z poll 2: PENDING=13 FAIL=ci-authority/codex/merge-queue-pilot | still: ci-pack-0,ci-pack-2,ci-pack-1,ci-pack-10,ci-pack-11,ci-pack-9
23:13:17Z poll 3: PENDING=0  FAIL=ci-authority/codex/merge-queue-pilot | ALL CONCLUDED
23:13:17Z WATCHER EXIT: checks concluded
```

Thirteen packs do not conclude in five minutes on this repository, and none of them did. The
transition between poll 2 and poll 3 was a re-push, which rebinds the pull request to a new head
and takes the old head's check rows with it.

Three properties combine, and each is individually reasonable:

* **The check list is head-scoped.** It is not a ledger of what this pull request has ever run;
  it is the set of check runs attached to the current head. So it is legitimately empty for a
  head whose runs have not started.
* **`ci-plan` publishes the pack set.** Even once a run starts, the `ci-pack-*` rows do not
  exist until the planner lands (~4 min) - already recorded as
  `DSC:CI-PLAN-PUBLISHES-THE-PACK-SET-SO-ZERO-PACKS-IS-NOT-PROOF`. This record is the
  same absence arriving through a watcher's exit condition instead of a human's rollup read.
* **The one surviving red is the one a reader is trained to discount.**
  `ci-authority/codex/merge-queue-pilot` is red by design on every main-targeting pull request
  and the sweeper excludes it by name, so a log whose only failure is that name reads as clean.

The asymmetry that makes this dangerous: a watcher that wrongly reports STILL PENDING costs one
more poll, while a watcher that wrongly reports CONCLUDED costs the proof. Exit conditions must
therefore be written as positive requirements over expected names - "every run at this head is
completed AND `ci-gate` is present AND no non-excluded row failed" - never as the absence of
pending rows. The corrected watcher for this pull request does exactly that, and refuses to
speak while `ci-gate` is missing.

### A correct watcher's verdict still expires when the head moves

The corrected watcher above was re-armed on this same pull request and behaved exactly as
specified: it pinned the head, graded the runs at that head, waited for every one to reach
`completed`, required `ci-gate` by name, and excluded only the by-design pilot red.

```
23:46:19Z poll 7: head=54821ee935c0 runs=3 RUNS_PENDING ci(in_progress)
23:51:22Z poll 8: head=54821ee935c0 ALL_SETTLED rows=26 runs=fences=success,ci=success,ci-authority=success verdict=GREEN
23:51:22Z WATCHER EXIT: checks settled
```

That verdict was true. It was also already stale: the live head was `c94a361d1941`, a
`Merge branch 'main' into claude/ind-requirement-traceability` pushed at 23:51:29Z - two
seconds after the watcher spoke - and at that head `fences` and `ci-authority` were green
while `ci` (run 36360090612) had restarted and was `in_progress`. Merging on the watcher's
exit would have merged a head whose `ci` had run for eight seconds.

The mover is the part worth remembering. It was not a sibling seat and not the author: it was
the **merge sweeper's own `update-branch` base refresh**, the mechanism fleet law describes as
the thing that drains an armed backlog once main is healed. A seat waiting for the sweeper to
merge its pull request is therefore waiting on the one actor most able to invalidate its
proof, and least likely to be suspected of it. Any armed pull request can have its head moved
under a correct verdict at any moment.

So the exit condition and the consumption of the verdict are two separate cures. The first is
in this record above. The second: **re-read `headRefOid` in the same breath as the merge**,
compare it to the sha the verdict names, and refuse the merge on any mismatch - then regrade
the runs at the new head. The cost of the check is one `gh pr view --json headRefOid`; the
cost of skipping it is a merge over a run that had barely started.

Related: `DSC:CI-PLAN-PUBLISHES-THE-PACK-SET-SO-ZERO-PACKS-IS-NOT-PROOF` (the same
absence, read once from a rollup rather than continuously by an instrument);
`DSC:A-PLANS-TRACEABILITY-TABLE-IS-NOT-COVERAGE` (the absence of a failing row is not the
presence of a passing one, at requirement scale).
