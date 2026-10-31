---
key: TERMINAL-MIGRATION-PR-LANDS-SOLO-WITH-LEDGER-FOLLOWUP
question: >
  A Terminal pull request that adds supabase/migrations/NNNN_*.sql must record its prefix
  in RESERVATIONS.json with pr set to its own number and pr_state "open", and the Ingest
  CI check then refuses that file on every other PR's merge ref while the row is open
  (DSC:TERMINAL-OPEN-LEDGER-ROW-ON-MASTER-REDS-EVERY-OTHER-PR). The same checker refuses
  a row marked "merged" before the PR actually merged. In a program that lands accepted
  heads through landing trains (DEC:TERMINAL-E20-LANDING-TRAINS-ONE-CI-ONE-SQUASH), how
  does a migration PR such as E05 #927 (0033_watchlist_annotations) land and get applied?
answer: >
  A migration pull request lands SOLO and is followed by a ledger PR, in this order.
  (1) Merge origin/master into it, keeping master's rows byte-exact and adding only its
  own row, then run `GITHUB_EVENT_NAME=pull_request PR_NUMBER=<its number> python3 -m pytest
  tests/test_supabase_migration_namespace.py` plus the normal gates. (2) Apply the DDL
  through the reviewed applier, `python3 scripts/supabase_apply.py <file> --dry-run` and
  then `--apply --receipt <json>`, reading SUPABASE_ACCESS_TOKEN and SUPABASE_PROJECT_REF
  from the primary checkout's .env into the subshell (never printed, never committed);
  post the receipt as a PR comment, then record applied_in_production, applied_date and
  the README application row in the PR. An HTTP 401 means the PAT must be rotated by a
  human and ends the attempt; no retry on another carrier. (3) Arm merge-on-green plus
  auto-merge only when no landing train is mid-CI. (4) IMMEDIATELY after its squash, open a
  minimal follow-up PR that flips the row to pr_state "merged" with merged_sha, updates
  the SQL "-- Ledger row:" header and the README row, and arm it the same way (precedent
  terminal #946 -> #947). (5) Every landing train pushes its head only after that
  follow-up is on master, so no train merge ref ever carries an open row.

  Scoped MedTech application (2026-10-20): the matching partial amendment in
  DEC:SUPABASE-MIGRATION-NAMESPACE-TERMINAL-LEDGER-2026-09-06 applies this
  sequence only to Terminal #1084 and its exact bound 0037 SQL. It is effective
  only after independent review and canonical Macro main acceptance. Solo
  describes separate landing outside a train; it does not require a SQL-only
  PR or moving reviewed application code to another carrier. Preserve existing
  holds and the separation between application, merge, deployment and paid-user
  proof.
rationale: >
  The ledger checker makes the row's pr field a proof of ownership: a present open-row file
  is legitimate only on the PR the row names, so a train carrying the migration can never
  be green, and pre-flipping the row to merged is refused because the PR has not merged.
  The only consistent sequence is therefore solo landing plus an immediate follow-up, and
  the cheapest way to keep every other lane green is to hold train pushes until the
  follow-up lands rather than to rerun or "repair" reds that are structural. Applying
  through scripts/supabase_apply.py with a posted receipt keeps the house rule that an
  applied migration is evidenced on the PR before the README table claims it
  (DEC:SUPABASE-MIGRATION-NAMESPACE-TERMINAL-LEDGER-2026-09-06), and the estate has no
  migration history table to fall back on (DSC:TERMINAL-HAS-NO-MIGRATION-LEDGER).
alternatives:
  - option: "Carry the migration inside a landing train and flip the row in the same train."
    why_not: "The train's merge ref carries a present file whose row names another PR (#927), which the checker refuses as OPEN_PR_STATE_STALE; marking it merged inside the train is refused too because #927 has not merged."
  - option: "Relax the checker so an open row is tolerated on other PRs."
    why_not: "The open-while-present rule is what makes ownership and application status answerable from git in an estate with no migration history table; weakening it reopens the duplicate-prefix problem the ledger was built for."
  - option: "Apply the DDL after the squash instead of before."
    why_not: "The README application row and the receipt would then land in the follow-up PR, splitting the evidence from the code that depends on it; applying before the squash keeps the carrying PR self-evidencing, and the migration is additive and re-runnable."
evidence:
  - >
    Terminal #946 (migration 0032, row open) squashed as 2957bd64e; the immediate follow-up
    #947 (squash 200786b34) flipped the row to merged + merged_sha and cleared the Ingest reds on
    every other open PR. MarketOntology CEO A asked this program on Terminal issue 916 not
    to open a competing 0032 reconcile PR; #947 was adopted as the incumbent repair.
  - >
    Falsifier run 2026-10-11 in a clean worktree at master d0973ef6e (recorded in
    DSC:TERMINAL-OPEN-LEDGER-ROW-ON-MASTER-REDS-EVERY-OTHER-PR): PR_NUMBER=999 exits 1
    OPEN_PR_STATE_STALE when row 0032 is open, PR_NUMBER=946 exits 0.
  - >
    scripts/supabase_apply.py (charting-app) with --dry-run / --apply --receipt is the
    reviewed applier; scripts/README_supabase_apply.md documents the receipt-then-README
    order. E05 #927 holds prefix 0033 (0033_watchlist_annotations.sql), unapplied at the
    time of this decision.
affects:
  - "WS:TERMINAL-ENHANCEMENTS20"
  - "terminal-user-services"
  - "supabase/migrations/**"
confidence: high
reversibility: easy
decided_by: coo-fable
decided_at: 2026-10-11
---

## Checklist for the E05 landing (and any later migration PR)

1. Preconditions: ACCEPT review at the exact head; no landing train mid-CI; worktree clean.
2. Merge origin/master into the PR; confirm `git diff origin/master -- supabase/migrations/RESERVATIONS.json`
   shows only the new row; run the namespace pytest in PR mode with the PR's own number.
3. Dry run, then apply with a receipt; post the receipt on the PR; record application in the
   PR (row `applied_in_production`, `applied_date`; README table); re-run the pins; push.
4. Arm; after the squash, open the follow-up ledger PR at once and arm it.
5. Only then push or refresh any landing train head.

Taken by the program CEO session (Fable, Chairman-assigned 2026-10-11, Terminal issue 916).

## Scoped MedTech R14 sequence, 2026-10-20

The accepted MedTech amendment in
DEC:SUPABASE-MIGRATION-NAMESPACE-TERMINAL-LEDGER-2026-09-06 binds Terminal
#1084 and `0037_medtech_watches.sql` from
`9d080bdca3bcce8ec10c1fce4e1ca30386d6d3c3`, application-file SHA-256
`c2e4831534fe2af7f835b19210020544b56b01866109a06b965ea656d87b8406`.
Until independent review and normal acceptance of the amendment into Macro
main, this section is a proposal, not an effective ordering exception.

The bound SQL may be carried by descendants of the qualification baseline under
the exact identity and release-head conditions in the matching namespace amendment.
An updated carrier does not inherit acceptance when its changes invalidate that
amendment's dependency, ownership, ordering or application assumptions.

Keep #1084 as the existing carrier. The #927 precedent contains application
code as well as SQL: "solo" means separate from a landing train. Run the
namespace proof with `GITHUB_EVENT_NAME=pull_request PR_NUMBER=1084`.

After exact source acceptance, concluded required checks, current-base and
reservation reconciliation, reviewed-applier dry run, compatible current catalog
preflight, a clean reconciled carrier and existing application admission:

1. Apply only the bound 0037 file with the existing reviewed per-file applier.
   Retain the exact pre/post catalog receipt and verify all twelve typed catalog
   objects plus the RLS/privilege rows, as specified in the namespace amendment.
   A failed or ambiguous response
   stops this effect for same-carrier reconciliation.
2. Publish and read back that receipt before updating #1084's truthful
   application flags and README application row. Keep `pr_state: open`.
   Retain the originally applied source hash even when ledger comments change.
3. Complete affected checks, then solo squash when no landing train is mid-CI.
   Preserve all unrelated ledger rows and carrier holds.
4. Immediately land the minimal follow-up recording the actual squash SHA and
   `pr_state: merged`, with the matching SQL ledger header and README metadata.
   Never predeclare a merge.
5. Dependent train heads proceed only after that follow-up is accepted.
   Deploy the accepted Terminal revision through the existing release owner
   and prove the authenticated consumer workflow.

A compatible deployed Macro MedTech API is required before exposing the
Terminal workflow. Schema application, source acceptance, ledger completion,
deployment and live save/reload/exact-revision review are separate results.
An authentication refusal retains the existing credential-rotation boundary;
this amendment grants no alternate credential route or replay. Disable the
MedTech application routes if a production rollback is needed, preserving user
data. The SQL's destructive down block remains for disposable qualification
databases only.

The current Chairman-assigned MedTech recovery session authored this bounded
disposition under protected Mastermind
`a7553e0a18339c910eef9687c730b06605dd710e`. It changes no general migration
rule and performs no DDL. Dependency and preserved-carrier evidence reside in
the matching namespace amendment, with the existing SQL qualification in
[Terminal #1084](https://github.com/mastermindx-market-intelligence/mastermind-terminal/pull/1084).
