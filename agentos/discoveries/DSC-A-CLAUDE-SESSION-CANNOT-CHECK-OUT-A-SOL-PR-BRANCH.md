---
key: A-CLAUDE-SESSION-CANNOT-CHECK-OUT-A-SOL-PR-BRANCH
claim: >
  A Claude session handed a pull request whose head branch is `sol/*` (a ChatGPT-web
  carrier branch) cannot work on that branch directly: `.claude/hooks/ship_loop_guard.py`
  `_delivery_root_admission` admits delivery work only from a LINKED worktree whose
  current branch starts with `claude/`, and refuses any other branch with the reason
  `branch <name> is not claude/*`. The lawful shape is a `claude/*` lane based at the
  sol head that pushes every commit by explicit refspec
  (`git push origin HEAD:refs/heads/sol/<branch>`), so the PR's own head advances while
  the session stays admitted. The Stop guard then sees a `claude/*` branch with no PR of
  its own and keeps blocking with its ordinary internal codes until the sol PR is merged
  and verified against `origin/main`; that block is the expected cost of the pattern,
  not a defect to route around.
falsifier: >
  `_delivery_root_admission` in `.claude/hooks/ship_loop_guard.py` admitting a `sol/*`
  branch, or a `git push origin HEAD:refs/heads/sol/<branch>` from a `claude/*` lane
  being rejected by the remote for a reason other than a non-fast-forward.
so_what: >
  When a handoff names a `sol/*` PR, mint the `claude/*` lane at the PR's exact head,
  never check the sol branch out, push by refspec only, and keep "arm last" discipline
  on the sol PR (a push after arming can land behind the sweeper's merge). Do not
  rename the PR branch, open a replacement `claude/*` PR, or edit the admission hook to
  obtain a cleaner Stop message; the PR identity and its review history are the
  Chairman's carrier.
kind: constraint
verified_at: 2026-10-11
verified_by: >
  RS LEADER Meta-CEO session 5ec0472d (claude/ssd-rs-leader-wp1-1d927f831ec5f94e):
  `.claude/hooks/ship_loop_guard.py` lines 522-549 (`_delivery_root_admission`, reason
  string `is not claude/*`); PR #8750 (`sol/rs-leader-daily-weekly-high-watch-20261010-c1`)
  advanced a71eea31afb6 -> a7189a98f1c1 -> 7164b018ecd0 -> 72653445acf6 -> fadabdd26ceb
  entirely by `git push origin HEAD:refs/heads/sol/rs-leader-daily-weekly-high-watch-20261010-c1`
  from the claude/* lane, each push scheduling the PR's own exact-head `ci` run
  (38128428074, 38134796681).
scope: [macro, fleet-hooks]
confidence: verified
---

## Detail

The admission check is deliberately two-sided (linked worktree AND `claude/*`), so a
session cannot satisfy it by checking out the sol branch in its own worktree. The
refspec push keeps one writer on the PR branch and leaves the review carrier intact.
Because the lane's local branch never gets a PR, every Stop fires the guard's
`unmerged`/`unpushed`-family block for the lane itself; answer it with a one-line hold
note while the sol PR's watcher runs, and let the ladder admit the exit once the sol
PR is merged and verified.
