---
key: A-RERUN-REPLAYS-THE-STALE-MERGE-COMMIT-REFRESH-THE-BRANCH-INSTEAD
claim: >
  `gh run rerun <id> --failed` on a pull-request `ci.yml` run can never turn an INHERITED red
  green after main is healed, because `.github/workflows/ci.yml` checks out
  `ref: ${{ github.sha }}` ("A PR run proves GitHub's synthetic merge commit, not a later
  API-resolved branch tip"), and that SHA is frozen at run creation: the rerun replays the
  same merge commit of the PR head with the OLD main, without the heal. The act that
  proves the heal is a branch refresh (`PUT /repos/{owner}/{repo}/pulls/{n}/update-branch`
  with `expected_head_sha`), which moves the head to a new merge commit whose second parent
  is the healed main tip and schedules a NEW `pull_request` run against it.
falsifier: >
  On any PR whose red was proven inherited, run `gh run rerun <run> --failed` and watch it
  conclude green while the PR head is unchanged; or read `.github/workflows/ci.yml` and find
  the pull-request jobs checking out `refs/pull/<n>/merge` (re-resolved) or the branch tip
  instead of `${{ github.sha }}`. Either disproves the claim.
so_what: >
  When a PR's red is inherited from main and a heal has merged, do NOT re-run the failed run
  and do NOT push an empty commit: refresh the branch (`gh api -X PUT
  repos/<owner>/<repo>/pulls/<n>/update-branch -f expected_head_sha=<old head>`), then
  read the new head quota-free with `git fetch origin
  "+refs/pull/<n>/head:refs/remotes/origin/pr-<n>-head"` + `git cat-file -p` (parent 1 =
  old head, parent 2 = healed main; DSC:GITHUB-UPDATE-BRANCH-MERGE-PUTS-THE-OLD-HEAD-FIRST),
  re-arm ONE watcher on that head, and merge with `--match-head-commit <new head>` on
  concluded green. The sweeper's base-inherited-red path performs the same refresh; a
  manual rerun only spends a 30-minute pack run on a proof that cannot change.
kind: constraint
verified_at: 2026-10-05
verified_by: >
  Macro PR #8475 (F6): head ee88b142484f red on ci-pack-0 (run 37293056579) from #8069's Q06
  JSON missing in six curated exclusive scopes; heal PR #8484 merged as 20eb503a09ae at
  11:26Z; `ci.yml` lines ~4552-4557 and ~4908-4911 pin `ref: ${{ github.sha }}`; update-branch
  at 11:30Z moved the head to 23631a156ecb (parents ee88b142 + 20eb503a); the new run
  concluded green 12:02Z and the PR squash-merged as e2be81444d4c at 12:03:48Z.
scope: [macro, ".github/workflows/ci.yml", "ship loop"]
confidence: verified
---

# A rerun replays the stale merge commit; refresh the branch instead

The pull-request proof in this repository is bound to GitHub's synthetic merge commit at
the moment the run is created. A `--failed` rerun is a replay of that exact commit, so it
re-proves the PR head against the main it was born on. Once main has been healed the only
act that produces a proof of "this head on the healed main" is a branch refresh, which mints
a new merge commit and a new run. The seat's own first plan on #8475 (comment 5993047617)
named a rerun; it was retracted by name in comment 5993534089 once `ci.yml` was read.
