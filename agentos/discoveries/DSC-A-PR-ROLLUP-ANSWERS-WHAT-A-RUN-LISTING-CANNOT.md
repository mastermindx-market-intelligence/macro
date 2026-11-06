---
key: A-PR-ROLLUP-ANSWERS-WHAT-A-RUN-LISTING-CANNOT
claim: >
  A merge watcher built on `gh run list --branch <b>` reported a calm `NO_RUNS_YET` for 8
  consecutive polls on PR #8206 while the pull request itself carried ELEVEN concluded
  checks and a green ci-gate. Two independent causes: it asked a question about REFS for a
  fact that lives on the PULL REQUEST (statusCheckRollup cannot be confused about which
  ref it describes, and it includes check-only status contexts a run listing never
  returns), and `gh(...) or []` collapsed a FAILED call into an empty result, making an
  outage indistinguishable from "nothing has started".
falsifier: >
  Run `gh run list --branch <branch> --json headSha` for a green PR's branch and compare
  its sha set against `gh pr view <n> --json statusCheckRollup`; a PR whose checks include
  ci-authority/main or capability-broker (CheckRun rows posted outside a workflow run on
  that branch) will show rollup entries with no corresponding run row.
so_what: >
  Read merge/CI state from the endpoint that OWNS the fact: `gh pr view <n> --repo
  <owner>/<name> --json state,headRefOid,mergedAt,mergeCommit,mergeStateStatus,
  statusCheckRollup`. Never let a failed call and an empty result share a code path - an
  unreadable poll is a THIRD state (UNKNOWN, loud after N in a row), never folded into
  either verdict. And give every quiet instrument a budgeted escalation that prints the RAW
  thing it saw, not just its conclusion: the 8-poll escalation printing "shas seen: -" is
  the only reason this was found at all. A wrong instrument that is loud costs one look; a
  wrong instrument that is calm costs the window.
kind: landmine
verified_at: 2026-09-29
verified_by: >
  Measured on PR #8206 at 17:59:05Z (daemon reported NO_RUNS_YET after 8 polls;
  `gh pr view 8206 --json statusCheckRollup` returned 15 rows, 0 pending, ci-gate SUCCESS,
  and the only red was ci-authority/codex/merge-queue-pilot). Replaced by a rollup-reading
  observer; #8206 and #8208 both merged minutes later and were verified in origin/main's own
  bytes 9/9, with the same checker scoring 0/9 on pre-merge main.
scope:
  - scripts/merge_on_green.py
  - WS:GMI-INDUSTRIALS-FIRST-VERTICAL
confidence: verified
---

A related fact worth recording because it is what makes an `UNSTABLE` pull request safe to
merge without `--admin`: `scripts/merge_on_green.py:656` names
`ci-authority/codex/merge-queue-pilot` as `CI_AUTHORITY_INACTIVE_CONTEXT` and
`is_non_binding_check` drops it for PRs targeting main, because each PR run fails the unused
base so a retarget cannot reuse a success earned against another. So a PR whose ONLY red is
that context is mergeable by the sweeper and by hand, and reaching for `--admin` there would
be routing around a mechanism that already works. `ci-authority/main` stays fully binding.
