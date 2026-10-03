---
key: TERMINAL-MASTER-REQUIRES-RESOLVED-THREADS-SO-AN-ADVISORY-CODEQL-THREAD-BLOCKS-A-GREEN-HEAD
claim: >
  mastermind-terminal master protection carries required_conversation_resolution=true in
  addition to the three required checks; a pull request that is green, armed and mergeable
  still cannot merge (gh reports "base branch policy prohibits the merge"; native auto-merge
  never fires; the merge-on-green sweeper waits forever on mergeable_state=unstable) while ANY
  review thread is unresolved — including the CodeQL bot's advisory "Workflow does not contain
  permissions" thread, which is neither a required check nor a red. terminal#514 sat BLOCKED at
  green head 46ff13ec on 2026-09-08 until the single thread on
  .github/workflows/f12-team-postgres-canary.yml:47 was replied to and resolved (GraphQL
  addPullRequestReviewThreadReply then resolveReviewThread at 22:14Z); auto-merge fired the same
  minute and the pull request merged as cff58ee8. terminal#525 hit the same wall on 2026-09-07
  with two permission threads.
falsifier: >
  `gh api repos/mastermindx-market-intelligence/mastermind-terminal/branches/master/protection
  --jq .required_conversation_resolution.enabled` returns false, or an armed green pull request
  auto-merges while a review thread on it is still open.
so_what: >
  a Terminal ship loop must read the unresolved-thread count alongside the checks, the way it
  already reads `gh pr view N --json statusCheckRollup`; an unresolved thread is a merge gate to
  act on — reply and resolve while owning the follow-up, or fix it in the pull request — never
  something to wait out. Workflow files added to Terminal now carry an explicit least-privilege
  `permissions:` block from their first commit so the bot never opens the thread at all: that is
  packet B-PLAT-11, terminal#537, merged as 1d5956ec on 2026-09-09, which set the block on
  .github/workflows/f12-team-postgres-canary.yml.
kind: landmine
verified_at: 2026-09-08
verified_by: >
  Meta-CEO B successor seat, harness session d640f3ef, 2026-09-08 22:14Z on terminal#514
  (blocked at green head 46ff13ec, merged cff58ee8 the minute the thread on
  .github/workflows/f12-team-postgres-canary.yml:47 resolved); terminal#525 2026-09-07 20:04Z
  with two permission threads; terminal#537 merged 1d5956ec.
scope:
  - terminal
  - "mastermind-terminal branch protection (master)"
  - ".github/workflows/f12-team-postgres-canary.yml"
  - WS:MARKET-OS
confidence: verified
related:
  - "DSC:TERMINAL-HAS-NO-MIGRATION-LEDGER"
  - "WS:MARKET-OS"
---

A green, armed Terminal pull request does not merge while any review thread on it is
unresolved, and the CodeQL bot opens one on every workflow file that has no explicit
permissions block. The thread is advisory — it is not a required check and it is not a
red — but master protection treats every open thread as a merge gate, so the pull
request simply sits. Read the unresolved-thread count as part of the ship loop, reply and
resolve with the follow-up owed, and give any new workflow file its least-privilege
permissions block in the first commit.
