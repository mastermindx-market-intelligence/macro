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
kind: landmine
verified_at: 2026-09-25
verified_by: >
  Historical author-recorded verification dated 2026-09-25; supporting receipt: https://github.com/mastermindx-market-intelligence/Mastermind/pull/600#issuecomment-5827970534.
  The receipt records clean detached HEAD 87117418, reflog commits 85adcfd1 and 51bb88aa, and the checkout back to the parent for baseline measurement. No current host or process state is asserted.
scope:
  - "Mastermind historical IAC-P1 B3 donor evidence (2026-09-25)"
  - "detached lane worktrees"
  - "historical source custody"
confidence: verified
---

## Historical provenance — 2026-09-25

The measurements, confidence and verification date above describe the original September 25 observation. The November 6 record repair validates document structure and preserves source references; it does not rerun the historical experiment or establish current runtime behavior. The supporting [original receipt](https://github.com/mastermindx-market-intelligence/Mastermind/pull/600#issuecomment-5827970534) records the historical evidence.

The [later canonical lineage ruling](https://github.com/mastermindx-market-intelligence/Mastermind/pull/600#issuecomment-5841164702) designated claude/iac1-p1-packet-carriage-20260925 as **DONOR_TEST_EVIDENCE / DO_NOT_PUBLISH_AS_P1**, with [Mastermind #986](https://github.com/mastermindx-market-intelligence/Mastermind/pull/986) the canonical P1 carrier. Its held C-D child remained STOP / DO_NOT_PUBLISH. These knowledge records grant no transplantation, installation, live-packet or replay authority; all original refused or uncertain effects retain their original target and reconciliation boundary.
