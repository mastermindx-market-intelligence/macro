---
key: EDITING-A-PR-BODY-IS-A-CI-TRIGGER-THAT-CAN-CANCEL-ITS-OWN-PROOF
claim: >
  `ci-authority` runs on `pull_request_target: [opened, synchronize, reopened, edited]` with
  `cancel-in-progress` enabled for that event and a concurrency group keyed on the PR NUMBER, so
  two PR-BODY edits inside one run's lifetime make the second cancel the first — leaving a
  permanently `cancelled` `ci-authority` row in `statusCheckRollup` that the merge sweeper and
  `ship_loop_guard.py` both read as a genuine red, on a head whose code never changed and whose
  other `ci-authority` runs all succeeded.
falsifier: >
  Read `.github/workflows/ci-authority.yml` `on:` and `concurrency:` — if `edited` is absent from
  the `pull_request_target` types, or `cancel-in-progress` is not true for that event, this is
  false. Measured on PR #8177, 2026-09-29: three `pull_request_target` runs on the identical head
  `f16910decbe6` at 06:19:51 (push/synchronize, success), 06:20:08 (body edit, CANCELLED) and
  06:20:17 (second body edit, success) — `gh run list --branch
  claude/fleet-storage-records-20260929 --workflow ci-authority.yml --json
  databaseId,event,status,conclusion,createdAt`.
so_what: >
  BATCH PR-body edits into one `gh pr edit` call. If a second edit is genuinely needed — correcting
  your own published claim is the common case, and is the right thing to do — expect the cancelled
  row and clear it with `gh run rerun <cancelled run id>`, which concludes it `success` without
  touching the head or restarting the packs. Do NOT whitelist `CANCELLED` in a watcher or a guard
  to make the symptom go away: the same conclusion class is how a genuinely killed proof presents,
  and forgiving it is how a real red goes invisible. Note the shape as well as the fact — arming a
  PR is safe here (the workflow does NOT trigger on `labeled`), so "arm LAST" is unaffected; it is
  EDITING that is the trigger, which is the one PR act sessions treat as free.
kind: landmine
verified_at: 2026-09-29
verified_by: >
  .github/workflows/ci-authority.yml `on.pull_request_target.types` and the `concurrency` block
  (`cancel-in-progress: ${{ github.event_name == 'pull_request_target' }}`); run ids 36530511790 /
  36530535548 / 36530548704 on PR #8177; `gh run rerun 36530535548` concluded it `success` and the
  Stop guard's `ci_failed_unmerged: ci-authority (cancelled)` block cleared with no new commit.
scope:
  - macro
  - .github/workflows/ci-authority.yml
confidence: verified
---

## Why this is worth recording separately

`DSC:PR-EVENT-DELIVERY-IS-NOT-CANDIDATE-IDENTITY` already records the general shape — a shared
concurrency group letting one event's run cancel another's pending proof, and the principle that
`cancel-in-progress` cannot protect a pending proof from same-group replacement. That record's
trigger is lifecycle event DELIVERY ORDER (a delayed `closed` event arriving after a `reopened`
one), which a session cannot cause and cannot avoid.

This one's trigger is an ordinary authoring act: **a session editing its own pull request body
twice.** That is something sessions do constantly and believe to be free, and here it is the
difference between an armed PR that merges and an armed PR that sits red until a human looks.

## How it presents, which is the expensive part

Nothing errors. `gh pr edit` returns rc=0 and prints the PR URL. The rollup then carries three
`ci-authority` rows — two `success`, one `cancelled` — and the one that matters is the one that
did the least. Every other check is green. The PR is armed. And the sweeper will never touch it,
because it merges only on concluded-CLEAN and a `cancelled` conclusion is not clean.

The detection that worked was **two independent instruments agreeing**: a watcher that classifies
any non-`SUCCESS/NEUTRAL/SKIPPED` conclusion as failed (fail-closed by construction) reported
`red=ci-authority`, and `ship_loop_guard.py` independently blocked with
`ci_failed_unmerged: ci-authority (cancelled)`. A single instrument would have been easy to
dismiss as over-strictness — which is exactly what I nearly did.
