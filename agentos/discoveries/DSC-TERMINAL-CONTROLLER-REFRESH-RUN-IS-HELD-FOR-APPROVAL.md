---
key: TERMINAL-CONTROLLER-REFRESH-RUN-IS-HELD-FOR-APPROVAL
claim: >
  In charting-app, when `scripts/merge_on_green.py` refreshes a green-but-behind PR through
  `api.update_branch`, GitHub authors the refresh merge commit as `github-actions[bot]`, and
  the `pull_request` CI run that commit triggers completes immediately with conclusion
  `action_required` (held for approval) instead of running. The controller's follow-up
  `workflow_dispatch` run on the same head goes green, but branch protection keeps the PR's
  `mergeable_state` at `blocked`, so the PR shows every required check green in the
  dispatch run and still never merges; the held run needs an explicit
  `POST /repos/<owner>/mastermind-terminal/actions/runs/<id>/approve` (or a head pushed by
  a user token) before the protection clears.
falsifier: >
  Arm a green PR that is behind master and let the controller refresh it, then run
  `gh run list --repo <owner>/mastermind-terminal --branch <branch> --json databaseId,event,status,conclusion,headSha`
  and `gh api repos/<owner>/mastermind-terminal/pulls/<n> --jq .mergeable_state`. The claim
  is false if the refreshed head's `pull_request` run is not `completed/action_required`,
  or if `mergeable_state` becomes `clean` and the PR squashes after only the dispatch run
  succeeds, with no approve call and no user-token push. It is also false if
  `git log -1 --format=%an <refreshed head>` is not `github-actions[bot]`.
so_what: >
  A "green but BLOCKED" PR after a controller refresh is this landmine, not a flake and not
  a reason for an admin bypass (the Terminal master has `enforce_admins: false`, so a direct
  REST merge would silently skip protection and is forbidden). Approve the held run
  (`gh api -X POST repos/<owner>/mastermind-terminal/actions/runs/<id>/approve`), or
  refresh the head yourself by merging origin/master in a worktree and pushing with your
  own token, which produces a normal `pull_request` run that needs no approval. The durable
  fix belongs in `scripts/merge_on_green.py`: after `update_branch`, approve the held run
  or dispatch against it and wait for that run, with a controller test; until that lands,
  every controller refresh needs the manual approve. Landed 2026-10-19 (#989, train 5,
  e8a25a202); the manual approve applies only to refreshes made before it.
kind: landmine
verified_at: 2026-10-12
verified_by: >
  Terminal #963 (CI shard split) during terminal-enhancements20: controller refreshes to
  12a78fa3c and then b1ee4676c, both authored `github-actions[bot]`; their `pull_request`
  runs 38202767869 and 38207806770 read `completed/action_required` with no jobs executed,
  while the controller's dispatch runs (38207802855 on b1ee4676c) went green and
  `gh api .../pulls/963` kept `mergeable_state: blocked` with `auto_merge` armed for over
  an hour. `gh api -X POST .../actions/runs/38207806770/approve` at 05:29:25Z moved that run
  to `queued`. The PR was then disarmed because landing train 3 (#960) folded its head, so
  the squash after approval was not observed; confidence stays probable until a PR merges
  through the approve path alone.
scope:
  - "charting-app"
  - "scripts/merge_on_green.py"
  - ".github/workflows/merge-on-green.yml"
  - ".github/workflows/ci.yml"
  - "WS:TERMINAL-ENHANCEMENTS20"
confidence: probable
---

## Grounds

Branch protection on `master` is strict (`required_status_checks.strict: true`) and names
the aggregate contexts "Terminal typecheck + tests", "Quote Hub tests" and "Ingest +
signal-layer tests". Protection evaluates the check runs attached to the head commit; a
`pull_request` run held in `action_required` registers the required contexts as pending
on that commit, and a later `workflow_dispatch` run on the same commit does not replace
them. The hold itself is GitHub's approval gate for workflow runs whose triggering actor
is the Actions bot rather than a repository user, which is exactly what a REST
`update-branch` refresh produces. The controller was written assuming its dispatch run is
the run that matters (`scripts/merge_on_green.py`: `api.update_branch` then
`api.dispatch_ci`), so it waits for `mergeable_state: clean` that never arrives.

## What a session does with this

- Read `gh run list --branch <b> --json event,conclusion` before diagnosing a PR that is
  green in the observer yet `blocked`; an `action_required` `pull_request` run on the
  current head is the signature.
- Approve the held run or push a user-token refresh; never merge by REST as an admin and
  never mark an unmerged PR as merged.
- Related: DSC:TERMINAL-E2E-CAP-CANCEL-IS-RED-WITHOUT-A-FAILED-TEST (the other way a
  controller-managed PR stalls without a failing test) and
  DEC:TERMINAL-E20-LANDING-TRAINS-ONE-CI-ONE-SQUASH (why one stalled armed PR holds every
  other armed PR behind strict protection).
