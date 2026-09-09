---
key: SUPABASE-MIGRATION-NAMESPACE-TERMINAL-LEDGER-2026-09-06
question: >
  The one shared Supabase project (fsldfzlxyavsuwqbceod) has two hand-applied migration
  ledgers with colliding numbers (Terminal supabase/migrations 0001-0010 vs Macro
  scripts/deploy 0004-0008, different content) and two open Terminal PRs (#502, #507) both
  adding a file named 0011_*.sql. Which ledger owns the namespace, how are numbers allocated,
  and who keeps 0011?
answer: >
  charting-app supabase/migrations/ is the ONLY forward migration ledger for the shared
  project. Macro's scripts/deploy/000N series is frozen as a historical record (never
  extended; a Macro-side DDL need becomes a charting-app PR in the Terminal ledger). A number
  is allocated when a PR opens as max(number on master, numbers claimed by open PRs) + 1 and is
  recorded in a Reservations table in supabase/migrations/README.md in the same PR; a
  collision resolves in favour of the earlier-opened PR and the later PR renumbers before
  merge. Reservations now: 0011 analytics_eid (#507 keeps it), 0012 thesis_objects (#502
  renumbers), 0013 alert_runs_outbox (F08 slice 1), 0014 tenancy_foundation (F12). The initial
  seed is a one-time ruling exception to the earlier-opened rule: 0011 stays with #507 because
  it is a one-file Ready PR whose DDL is already applied live (2026-09-05), while #502 (opened
  2026-09-03, i.e. earlier) is a 24-file Draft that must rebase regardless; no future exception
  to earlier-opened-wins without a DEC amendment. Every file
  is idempotent, carries a "-- down:" block and a "-- readback:" catalog query; application
  stays an out-of-band operator/Meta-CEO act whose pre/post catalog readback is posted on the
  PR before the README application table is updated.

  Application mechanism (Meta-CEO B, 2026-09-06/07): migrations are applied by the
  owning Meta-CEO after the carrying PR merges, in ledger-number order (0014 after
  terminal#514, 0015 after #526, 0016 after #527; a later number is never applied
  before an earlier one is on master AND applied), through the Supabase Management
  API POST /v1/projects/{ref}/database/query (the CLI db push path is not used: no
  history table, see DSC:TERMINAL-HAS-NO-MIGRATION-LEDGER), with a pre/post catalog
  readback (to_regclass, pg_class.relrowsecurity, pg_indexes, pg_policy, pg_proc)
  captured as a receipt JSON and posted as a PR comment before the README
  application table row is edited. The request must carry a browser/curl User-Agent:
  the python-urllib default UA is rejected by the Cloudflare edge with HTTP 403
  "error code: 1010" (already recorded for scripts/geo_enrich.py and
  scripts/ad_ingest_run.py in DSC:SUPABASE-MANAGEMENT-PAT-EXPIRES-AT-30-DAYS).
  Measured carrier (review r2, 2026-09-08): the parenthetical above is the original
  allocation. terminal#514's files include both 0014_tenancy_foundation.sql and
  0015_team_roles_invitations.sql; terminal#526 is already MERGED (2026-09-07) as
  B-F12-3 app code over the 0014 foundation, not the 0015 SQL carrier. A successor
  applies 0014 then 0015 after #514 merges (ledger-number order; one receipt each,
  comments on #514), then 0016 after #527. Do not wait on #526 to apply 0015.
rationale: >
  There is no migration runner and no supabase_migrations schema (DSC:TERMINAL-HAS-NO-MIGRATION-LEDGER),
  so a file name is the only ledger the estate has; a second "0011" makes "what has been
  applied" unanswerable from git. Terminal owns the Supabase-facing runtime (auth, RLS,
  portfolio book, alerts evaluator), so its ledger is the natural single owner; renaming the
  already-applied Macro files would rewrite the record of what was applied under which name
  for no runtime benefit. Earlier-opened-wins is mechanical and needs no adjudication for
  future collisions; the seed itself is the one adjudicated exception (#502 opened first, on
  2026-09-03), taken because #507's single file is already applied live under the name
  0011_analytics_eid.sql and renaming an applied file rewrites the record of what was applied,
  while #502's 0011 is unapplied and its rename touches only its own files.
alternatives:
  - option: "Disjoint prefixes (Macro 2xxx as F12 proposed to Sol)."
    why_not: "Two forward ledgers for one database keep the applied-set unanswerable from either repo; the prefix only hides the collision."
  - option: "Adopt the Supabase CLI and a real history table."
    why_not: "db push would try to re-apply 0001..0010 into a history that does not exist; survivable only because every file is idempotent, and it is a separate platform change the Chairman has not asked for."
  - option: "Let #502 keep 0011 and renumber #507."
    why_not: "#507's file is already applied live as 0011_analytics_eid.sql, so renaming it rewrites the applied record, whereas #502's 0011 is unapplied and Draft. Correction 2026-09-06 (Meta-CEO B): #502 opened 2026-09-03, BEFORE #507 (2026-09-05) — the seed is an explicit exception to earlier-opened-wins, not an application of it."
evidence:
  - "git -C charting-app ls-tree --name-only origin/master supabase/migrations/ -> 0001..0010 + README.md (2026-09-06)"
  - "git ls-tree -r --name-only origin/main scripts/deploy/ templates/ | grep .sql -> 0004..0008 + templates/uwp_supabase.sql (macro main bed6c7e1)"
  - "GraphQL census of 16 open mastermind-terminal PRs: only #502 (0011_thesis_objects.sql) and #507 (0011_analytics_eid.sql) add migration files"
  - "supabase/migrations/README.md on origin/master: no remote migration history; 0009 applied before 0008"
  - "Charter research/MARKET_ONTOLOGY_META_CEO_CHARTER_2026_09_06.md §5 and §10.4 assign the settlement to Meta-CEO B"
  - "research/market_intelligence_productization/receipts/supabase_receipt_0012_thesis_objects_2026-09-06.json (0012 thesis_objects applied 2026-09-06; project_ref redacted to {ref})"
  - "research/market_intelligence_productization/receipts/supabase_receipt_0013_alert_runs_outbox_2026-09-06.json (0013 alert_runs_outbox applied 2026-09-07)"
  - "terminal#513 issuecomment-5563321750 is the 0013 receipt (html_url .../pull/513#issuecomment-5563321750; body is 'Supabase DDL readback receipt for 0013_alert_runs_outbox.sql'; gh api .../issues/513/comments --jq length = 1). Not on #514."
affects:
  - "WS:MARKET-OS"
  - "charting-app supabase/migrations/**"
  - "macro scripts/deploy/*.sql (frozen)"
  - "F08, F11, F12 lanes"
confidence: high
reversibility: costly
decided_by: "session 7cd4fae1-1ed9-41c2-adb4-1e5c6b0fbc5b (Meta-CEO B, Claude3, under the Chairman override of 2026-09-05)"
decided_at: 2026-09-06
---

Recorded by Meta-CEO B in Wave 0. The Terminal README change lands via packet B-PLAT-1;
#502's renumber lands in its release fix stage; 0013/0014 are minted by packets B-F08-2 and
B-F12-1. See DEC:CHAIRMAN-OVERRIDE-CLAUDE-META-CEO-REGIME-2026-09-06 for authority.
