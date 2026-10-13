---
key: TERMINAL-OPEN-LEDGER-ROW-ON-MASTER-REDS-EVERY-OTHER-PR
claim: >
  In charting-app, the moment master carries a supabase/migrations/NNNN_*.sql whose
  RESERVATIONS.json row still says pr_state "open", the required "Ingest + signal-layer
  tests" check fails OPEN_PR_STATE_STALE on EVERY other open pull request: actions/checkout
  checks out the PR merge ref (master plus the PR), so the file is present on that ref, and
  scripts/check_supabase_migration_namespace.py in PULL_REQUEST mode accepts a present
  open-row file only when the row's pr equals the running PR_NUMBER. A `gh run rerun` keeps
  the stale merge ref, so only a new push (or the merge-on-green controller's refresh of a
  BEHIND head) can turn the job green again, and only after the row is flipped on master.
falsifier: >
  In any charting-app checkout at master, edit supabase/migrations/RESERVATIONS.json so
  prefixes["0032"].pr_state is "open" (drop merged_sha), then run
  `GITHUB_EVENT_NAME=pull_request PR_NUMBER=999 python3 scripts/check_supabase_migration_namespace.py`.
  The claim is false if that exits 0. It is also false if the row's own PR number,
  `GITHUB_EVENT_NAME=pull_request PR_NUMBER=946 python3 scripts/check_supabase_migration_namespace.py`,
  exits non-zero, or if a plain `gh run rerun` of a red Ingest job on another PR turns green
  while master's row is still open. Restore the file with `git checkout --` afterwards.
so_what: >
  A pull request that adds a migration lands ALONE, never inside a landing train, and its
  RESERVATIONS.json row must name that PR (pr == the carrying PR number). Immediately after
  it squashes, open a tiny follow-up PR that sets pr_state "merged" plus merged_sha
  (precedent terminal #946 -> #947; the checker itself refuses a row marked merged before
  the PR merged, so the flip cannot be pre-staged). Until that follow-up is on master every
  other PR's Ingest job is red for a structural reason, not a code reason: do not rerun,
  do not bypass, do not "fix" the other PRs; land the follow-up, then push (or let the
  controller refresh) the other heads. Landing trains therefore push their heads only
  after the follow-up has landed. The full procedure is
  DEC:TERMINAL-MIGRATION-PR-LANDS-SOLO-WITH-LEDGER-FOLLOWUP.
kind: landmine
verified_at: 2026-10-11
verified_by: >
  Falsifier run 2026-10-11 ~21:25Z in a clean SSD worktree at master d0973ef6e: row 0032
  flipped to open -> PR_NUMBER=999 exit 1 with "[OPEN_PR_STATE_STALE] 0032: prefix 0032's
  file is present on the branch of pull request #999, but RESERVATIONS.json records it as
  pr_state 'open' on pull request 946"; PR_NUMBER=946 exit 0 "0 findings"; file restored
  -> PR_NUMBER=999 exit 0. Live precedent the same day: terminal #946 (migration 0032,
  row open) squashed as 2957bd64e and the Ingest job of every other open E20 PR went red
  until the follow-up #947 (squash 200786b34, row flipped to merged + merged_sha) landed. The rule
  is pinned by tests/test_supabase_migration_namespace.py and documented in the checker's
  own docstring (scripts/check_supabase_migration_namespace.py lines 30-56).
scope:
  - "charting-app"
  - "supabase/migrations/RESERVATIONS.json"
  - "scripts/check_supabase_migration_namespace.py"
  - ".github/workflows/ci.yml"
  - "terminal-user-services"
confidence: verified
---

## Grounds

The checker runs in three scopes. On a push to master (STRICT) it refuses any present
`.sql` whose row is still `open`, which is why the row must be flipped by a follow-up PR
rather than left open. In a pull request (PULL_REQUEST mode, `PR_NUMBER` wired from
`github.event.pull_request.number` in `.github/workflows/ci.yml`) a present open-row file
is legitimate only for the PR the row names; any other PR carrying it is "stale". Because
`actions/checkout` builds the merge ref from current master, a row that is open ON MASTER
is carried by every PR, so every PR except the row's own goes red at once.

Observed 2026-10-11 during the terminal-enhancements20 program
(WS:TERMINAL-ENHANCEMENTS20): after #946 squashed, the E20 lane PRs showed
`red:shard:...`/Ingest reds on their next CI even though their diffs did not touch
`supabase/`; the reds cleared only on heads pushed after #947 landed. Reruns of the
existing runs stayed red because the rerun reuses the original merge ref.

## What a session does with this

- Before arming any PR, check `git show origin/master:supabase/migrations/RESERVATIONS.json`
  for a row with `"pr_state": "open"` whose `.sql` is present on master. If one exists, the
  only useful action is to land that row's follow-up PR.
- A migration PR's row must say `pr: <that PR>`; the E20 program's E05 (#927, prefix 0033)
  is the next instance and lands solo per
  DEC:TERMINAL-MIGRATION-PR-LANDS-SOLO-WITH-LEDGER-FOLLOWUP.
- Related: DSC:TERMINAL-HAS-NO-MIGRATION-LEDGER (why application is a separate,
  receipted operator act and never `supabase db push`).
