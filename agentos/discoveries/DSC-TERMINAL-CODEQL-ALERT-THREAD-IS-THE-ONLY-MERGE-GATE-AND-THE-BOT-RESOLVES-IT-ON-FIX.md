---
key: TERMINAL-CODEQL-ALERT-THREAD-IS-THE-ONLY-MERGE-GATE-AND-THE-BOT-RESOLVES-IT-ON-FIX
claim: >
  On mastermind-terminal, a new CodeQL alert in a pull request's changed code is held back from
  master only by the github-advanced-security review thread it opens on the flagged line (master
  requires conversation resolution but no CodeQL check), and the bot resolves that thread itself
  once a later push fixes the alert: on terminal#876 the js/request-forgery alert #24 opened a
  thread on terminal/lib/flowSource.ts:392 at 2026-10-09T08:37:29Z, the fix push marked the alert
  fixed at 08:52:33Z, the thread's resolvedBy is github-advanced-security[bot], and the pull
  request merged as 5503f970 at 09:38:08Z.
falsifier: >
  `gh api graphql -f query='query { repository(owner:"mastermindx-market-intelligence",
  name:"mastermind-terminal") { pullRequest(number:876) { reviewThreads(first:5) { nodes {
  resolvedBy { login } } } } } }'` returning a login other than github-advanced-security[bot], or
  `gh api repos/mastermindx-market-intelligence/mastermind-terminal/branches/master/protection
  --jq .required_status_checks.contexts` listing a CodeQL context, or a green armed Terminal pull
  request merging while a github-advanced-security thread on it is still open.
so_what: >
  Clear a github-advanced-security alert thread by fixing the code and letting the bot resolve
  it, never by replying and resolving it by hand: that removes the alert's only merge gate
  without fixing anything, so the reply-and-resolve routine in
  DSC:TERMINAL-MASTER-REQUIRES-RESOLVED-THREADS-SO-AN-ADVISORY-CODEQL-THREAD-BLOCKS-A-GREEN-HEAD
  does not apply to security alerts. Because any writer can resolve a thread, a ship loop still
  reads the CodeQL check-run verdict on the head itself before the merge lands.
kind: landmine
verified_at: 2026-10-09
verified_by: >
  Claude Code session ba6fcbcb, 2026-10-09 ~09:50Z, read-only: GraphQL reviewThreads on
  terminal#876 (one thread, author and resolvedBy github-advanced-security[bot], path
  terminal/lib/flowSource.ts:392, created 08:37:29Z); `gh api
  "repos/mastermindx-market-intelligence/mastermind-terminal/code-scanning/alerts?ref=refs/pull/876/head"`
  (alert #24 js/request-forgery, created 08:37:26Z, fixed 08:52:33Z); `gh api
  repos/mastermindx-market-intelligence/mastermind-terminal/branches/master/protection`
  (required_conversation_resolution true; contexts Quote Hub tests, Terminal typecheck + tests,
  Ingest + signal-layer tests).
scope:
  - terminal
  - "mastermind-terminal branch protection (master)"
  - "mastermind-terminal code scanning (CodeQL default setup)"
  - WS:MARKET-OS
confidence: verified
related:
  - "DSC:TERMINAL-MASTER-REQUIRES-RESOLVED-THREADS-SO-AN-ADVISORY-CODEQL-THREAD-BLOCKS-A-GREEN-HEAD"
  - "DSC:TERMINAL-CODEQL-PR-CHECK-FIRST-COMPLETES-AS-AN-INTERIM-NEUTRAL"
  - "WS:MARKET-OS"
---

CodeQL is not a required check on Terminal `master`, so the `CodeQL` check-run itself gates
nothing. A new alert still cannot merge quietly. The bot posts it as a review thread on the
flagged line, and master's conversation-resolution rule holds every unresolved thread. That
thread is the alert's only gate, and it clears the right way on its own: when a later push
fixes the alert, the bot resolves its thread and the merge proceeds.

The general advice for unresolved threads on Terminal is to reply and resolve while owning
the follow-up. That fits the advisory workflow-permissions threads it was written for. For a
security alert it removes the only gate and changes nothing in the code. Fix the code, and
read the CodeQL verdict yourself. A thread is a soft gate that any writer can click away.
