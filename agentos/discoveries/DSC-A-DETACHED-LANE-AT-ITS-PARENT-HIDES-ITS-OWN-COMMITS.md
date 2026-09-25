---
key: A-DETACHED-LANE-AT-ITS-PARENT-HIDES-ITS-OWN-COMMITS
claim: >
  A bounded lane working on a DETACHED HEAD that checks itself back to its parent - the normal way
  to measure a PARENT baseline when the brief demands one - leaves its own commits reachable only
  from the reflog. `git log` on the worktree then shows the parent with a clean tree and no sign of
  the work, which reads exactly like a lane that produced nothing. Observed 2026-09-25 on Mastermind
  IAC-P1 B3, lane `rs_20260925T060029Z_15006`: worktree HEAD `87117418` clean, zero commits in
  `git log`, while the reflog showed `commit 85adcfd1` at 23:16, `commit 51bb88aa` at 23:18, then
  `checkout: moving from 51bb88aa to 87117418` at 23:25, and `git cat-file -t` confirmed both
  objects present. The lane process was alive throughout, running the baseline leg.
falsifier: >
  On a detached lane worktree that reports no commits, run `git reflog --date=iso` and
  `git cat-file -t <sha>` for any commit the reflog names. If the objects resolve, HEAD was never
  the work product. To confirm the commits are genuinely unreferenced rather than on a branch, check
  `git for-each-ref` - no ref will point at them.
so_what: >
  Two consequences. An orchestrator polling worktree HEAD to decide whether a lane delivered will
  report a false negative and may redispatch work that already exists; read the reflog instead.
  And commits in that state are one `gc` from gone, with no branch or tag holding them - so
  verified lane output should be published (or at minimum fetched into a referenced local head)
  rather than left sitting in a parked worktree while the orchestrator waits for the lane's own
  gate figures, which are testimony about evidence rather than evidence.
