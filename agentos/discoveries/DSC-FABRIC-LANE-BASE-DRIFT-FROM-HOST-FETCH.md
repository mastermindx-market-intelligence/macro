---
key: FABRIC-LANE-BASE-DRIFT-FROM-HOST-FETCH
claim: >
  Fabric lanes on ubuntu3 share one remote-tracking origin/master in ~/lanes/repos/mastermind-terminal, so a
  `git fetch origin master` run on the host while a lane is working makes that lane's `git diff
  origin/master HEAD` show master's newer files as deletions and its `git reset --soft origin/master` capture
  them as reverts.
falsifier: >
  Run `ssh mmx-ubuntu3 'git -C ~/lanes/wt/r2-pr4-session-review-1021 log --oneline -3'` and
  `git diff --name-only 81d0b2a88...805d7dae1` in a Terminal checkout; the claim is refuted if the lane
  branch shows no "Restore beta ops/tests files reverted by the base drift" commits, or if the lane's first
  pushed head f7382380c did not delete the six ops/ and tests/ files that #1107 added to master after the
  lane's worktree was cut at 187bf9582.
so_what: >
  Pin the base in every lane packet (`BASE=<full sha>`; guards and diffs use `$BASE`, never
  origin/master) and forbid fetch/pull/merge inside the lane; cut worktrees from a fetched sha
  (`git fetch origin <ref>` then `git worktree add --detach $W FETCH_HEAD`). At consumption verify
  `git diff --name-only <base>...<branch>` lists only the owned files before opening a PR.
kind: landmine
verified_at: 2026-10-22
verified_by: >
  `git log --oneline 187bf9582..805d7dae1` on Terminal branch claude/r2-session-review-1021 shows commits
  2602c0a91 and 805d7dae1 ("Restore beta ops/tests files ... reverted by the base drift") and
  `git diff --name-only 81d0b2a88...805d7dae1` lists only the six owned terminal/ files; lane
  r2-pr4-session-review-1021-v1 RESULT incident section (fabric host ~/lanes/ext/RESULT_PR4.md).
scope:
  - fabric
  - terminal
  - "terminal:terminal/components/exposure-map"
confidence: verified
---

## Exact observed boundary

The PR-4 worktree was cut with `git worktree add --detach … origin/master` at 187bf9582. The parent session
then fetched origin/master on the same host to cut the PR-6 and PR-7 lanes, advancing the ref to 81d0b2a88
(#1107, ops/ and tests/ only). The lane's final squash step `git reset --soft origin/master` saw the six new
files as deletions and pushed them; two repair commits restored them. The slice's own six files were never
affected, and the three-dot diff against master is clean.

## Not claimed

Nothing here says the lane was wrong to squash against its contract's named base; the contract named a
moving ref. Later packets (R2-PR5 onward) name the sha.
