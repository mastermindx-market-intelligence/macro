---
key: TERMINAL-CODEQL-PR-CHECK-FIRST-COMPLETES-AS-AN-INTERIM-NEUTRAL
claim: >
  The CodeQL result check-run (app github-advanced-security) on a mastermind-terminal pull
  request can first complete as neutral, "1 configuration not found" for
  /language:javascript-typescript, because the actions and python analyses upload before the
  JavaScript one, and GitHub later rewrites that same check-run in place to the real verdict
  without moving its completed_at: on terminal#878 head 7851d3a8 the only CodeQL check-run,
  113757658612, read neutral at first completion and now reads success, "No new alerts in code
  changed by this pull request", with completed_at 09:29:05Z, before the javascript-typescript
  analysis was created at 09:30:08Z.
falsifier: >
  `gh api "repos/mastermindx-market-intelligence/mastermind-terminal/commits/7851d3a8a4dcf7dc22ec215f0d1e67bed78ca151/check-runs?check_name=CodeQL"
  --jq .total_count` returning more than 1 (the neutral and the success were different
  check-runs), or a Terminal pull request whose CodeQL check-run, read while its
  Analyze (javascript-typescript) job is still running, already shows success or failure.
so_what: >
  A ship loop treats a CodeQL neutral "configuration not found" as undecided, never as a pass or
  a failure. It reads the verdict only after the Analyze (javascript-typescript) job has completed
  and `code-scanning/analyses?ref=refs/pull/<n>/head` lists the /language:javascript-typescript
  analysis at the head SHA. Default setup files pull-request analyses under refs/pull/<n>/head,
  so an alerts query on refs/pull/<n>/merge returns [] with no analysis behind it and proves
  nothing. A watcher that exits on the first completion, or keys on completed_at, reads the
  interim value, and auto-merge is armed only after the final verdict is read.
kind: landmine
verified_at: 2026-10-09
verified_by: >
  Claude Code session ba6fcbcb, 2026-10-09, read-only, on terminal#878: a watcher read
  check-run 113757658612 as neutral "1 configuration not found" (completed_at 09:29:05Z) right
  after it first completed; `gh api
  "repos/mastermindx-market-intelligence/mastermind-terminal/commits/7851d3a8a4dcf7dc22ec215f0d1e67bed78ca151/check-runs?check_name=CodeQL"`
  now returns total_count 1, conclusion success, the same completed_at; `gh api
  "repos/mastermindx-market-intelligence/mastermind-terminal/code-scanning/analyses?ref=refs/pull/878/head"`
  lists /language:javascript-typescript at 7851d3a8 created 09:30:08Z with results_count 0, and
  the same three analyses again at the updated head 4d1d2526.
scope:
  - terminal
  - "mastermind-terminal code scanning (CodeQL default setup)"
  - WS:MARKET-OS
confidence: verified
related:
  - "DSC:TERMINAL-CODEQL-ALERT-THREAD-IS-THE-ONLY-MERGE-GATE-AND-THE-BOT-RESOLVES-IT-ON-FIX"
  - "WS:MARKET-OS"
---

A pull request's `CodeQL` check-run is the summary of per-language analyses that upload
separately. When the actions and python analyses land first, the check-run completes as
`neutral`, "1 configuration not found". That means GitHub cannot compare against master's
javascript-typescript configuration yet. It is not a verdict. About a minute later the
JavaScript analysis uploads, and GitHub rewrites the same check-run to the real result,
keeping the original `completed_at`.

So "completed" is not "decided". Wait for the `Analyze (javascript-typescript)` job, confirm
that the analysis exists under `refs/pull/<n>/head`, and only then read the conclusion. Arm
auto-merge after that read, since nothing else in Terminal's required checks waits for it.
