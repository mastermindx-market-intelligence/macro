---
key: GITHUB-UPDATE-BRANCH-MERGE-PUTS-THE-OLD-HEAD-FIRST
claim: >
  GitHub's "Update branch" (PUT /repos/{owner}/{repo}/pulls/{n}/update-branch, the
  same act the sweeper's base-inherited-red refresh and the web button perform) moves
  the pull request's head to a merge commit titled "Merge branch 'main' into <branch>"
  whose FIRST parent is the PR's previous head and whose SECOND parent is the base tip
  - the same parent order a local `git merge main` on the branch produces. A re-arm
  check that recognises the update by "parent 2 == old head" therefore never matches,
  reports the move as a foreign push, and leaves the PR un-watched.
falsifier: >
  `git fetch origin main && git log -1 --format=%P <new head>` on any update-branch
  head showing the old head in the SECOND position; or a GitHub-generated update
  merge whose first parent is the base tip.
so_what: >
  A watcher that exits HEAD_MOVED after an update-branch is reporting the EXPECTED
  state, not an intrusion: classify the move by `parent1 == old head && parent2 is
  the base tip` and re-arm on the new head immediately (the PR's checks re-run on the
  merge commit and the sweeper merges only on that head). Do not open a conflict
  investigation or a second PR, and do not keep the old watcher: its head is gone.
kind: runtime
verified_at: 2026-10-04
verified_by: >
  Macro PR #8392 after the sweeper's update-branch: new head
  ae96a7f264df2d0a0fb0e3b3ef8739e04b060cc5 ("Merge branch 'main' into
  claude/idr-edgar-8k-accession-backfill-20261004"), `git log -1 --format=%P` =
  3ec016886c2f (old PR head) a918da3a32c8 (origin/main tip at the time). The seat's
  re-arm check in the Intraday Dislocation + Reclaim session tested parent 2 first,
  printed NOT_AN_UPDATE_BRANCH_MERGE, and had to be re-armed by hand. Terminal PR #797
  (2026-10-04) repeated the shape: `gh pr merge` refused "head branch is not up to
  date", PUT update-branch moved the head 7a7b160ef513 -> f09ac75d483b.
scope: [macro, terminal]
confidence: verified
---

## Detail

Both repositories now refuse a merge whose head is behind the base (Terminal through
its ruleset, Macro through the sweeper's refresh), so update-branch merges are the
normal shape of a head move on an armed PR. The only honest response to one is to
re-arm on the new head after confirming its parents; a watcher keyed on the old head
cannot see the checks that now decide the merge.
