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

  Scoped amendment (2026-10-18):
  DEC:PORTFOLIO-CURRENCY-FORWARD-DISPOSITION-2026-10-18 preserves applied #946/0032,
  supersedes pending #866/0032 only as the currency application candidate for
  Terminal #1044, and preserves #778's 0035 claim by carrying the candidate at
  0036. Only that exact currency proposal may proceed independently of the
  unrelated pending lower-numbered migrations, subject to independent exact-head
  source acceptance and all existing runtime/application gates. For that carrier
  the later solo-migration procedure supplies the apply-before-squash and immediate
  ledger-follow-up sequence. The general allocation, history and application rules
  remain unchanged for all other files.

  Scoped amendment (2026-10-20, MedTech R14):
  Terminal #1084 may apply 0037_medtech_watches.sql at readback qualification baseline
  9d080bdca3bcce8ec10c1fce4e1ca30386d6d3c3, application-file SHA-256
  c2e4831534fe2af7f835b19210020544b56b01866109a06b965ea656d87b8406,
  without first merging or applying unrelated lower-numbered carriers. This
  exception covers only numeric ordering and the apply/merge sequence for this
  exact MedTech candidate. It takes effect only after independent review and
  normal acceptance of this amendment into canonical Macro main. The existing
  solo-migration procedure supplies application before the owning PR's solo
  squash and the immediate merged-ledger follow-up.

  Preserve every other reservation, applied SQL byte, carrier and release hold;
  no lower migration is adopted, replayed, renamed, released or marked merged.
  Require exact-head source acceptance, concluded required checks, current-base
  and namespace reconciliation, reviewed-applier dry run, compatible production
  catalog, a reconciled carrier and the existing application admission. A
  semantic change to the bound SQL requires fresh qualification and independent
  disposition. Credential, transport, resource, effect and production-proof
  gates remain unchanged; this is not a general out-of-order policy.
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
  - "0014_tenancy_foundation applied 2026-09-08T22:24:14Z after terminal#514 merged as cff58ee8; the SQL was fetched from Terminal master at that sha (sha256 prefix 88781e40). Receipt research/market_intelligence_productization/receipts/supabase_receipt_0014_tenancy_foundation_2026-09-08.json; terminal#514 comment ids 5592694274 (readback) and 5592731536 (receipts summary)."
  - "0015_team_roles_invitations applied 2026-09-08T22:24:42Z, strictly after 0014 and in ledger-number order. The SQL was authored on the stacked pull request terminal#526 (B-F12-3, squash 83424c63 onto #514's branch) and reached master inside cff58ee8, which is the source ref the receipt records (sha256 prefix bff0f8bf). Receipt research/market_intelligence_productization/receipts/supabase_receipt_0015_team_roles_invitations_2026-09-08.json; terminal#514 comment id 5592697055."
  - "0016_account_lifecycle_requests applied 2026-09-09T01:11:07Z after terminal#527 merged as 68bbe8ea (sha256 prefix 3375618a). Receipt research/market_intelligence_productization/receipts/supabase_receipt_0016_account_lifecycle_requests_2026-09-09.json; the receipt comment on terminal#527 is recorded in the seat kit as RECEIPT-0016-COMMENT."
  - "The predecessor seat 7cd4fae1 applied 0014 and 0015 a second time inside the 22:2xZ seat-transfer overlap. Both files are written IF NOT EXISTS / CREATE OR REPLACE, so the duplicate application was idempotent; the receipts of record are the successor's, and terminal#514 issuecomment-5592751149 records the supersession. See DSC:SEAT-TRANSFER-OVERLAP-DUPLICATES-IRREVERSIBLE-ACTS."
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


## Partial amendment, 2026-10-18

DEC:PORTFOLIO-CURRENCY-FORWARD-DISPOSITION-2026-10-18 records the bounded Portfolio
currency disposition and its evidence. It amends only the named carrier's pending
0032 precedence and lower-number application sequence; it does not retire this
record or grant a general ordering, ownership or runtime exception.

## Partial amendment, 2026-10-20 — MedTech R14

The current Chairman assignment recovers and continues the existing MedTech
project, including its backend and personal watch workflow. The assigned
principal resolves this bounded release dependency under Mastermind
`AGENTS.md` and `docs/sol_skills/ACTIVE_EXECUTION.md` at
`a7553e0a18339c910eef9687c730b06605dd710e`. This amendment follows the
reviewed source-disposition pattern already used by Macro #9593; it becomes
effective through independent review and canonical main acceptance, not by this
working-tree proposal.

### Bound SQL and evolving application carrier

This disposition covers only `supabase/migrations/0037_medtech_watches.sql`,
SHA-256 `c2e4831534fe2af7f835b19210020544b56b01866109a06b965ea656d87b8406`, carried
by Terminal PR #1084. Its corrected readback qualification baseline is
`9d080bdca3bcce8ec10c1fce4e1ca30386d6d3c3`. The carrier may advance through
descendants of that baseline, including current-master reconciliation and
reviewed application changes, provided the application SQL remains byte-identical
to the bound hash. Before application, verify that exact identity and accept the
actual release head, with concluded required checks, current namespace and
production-catalog reconciliation, and all existing application prerequisites.

Changes elsewhere in the carrier require source review and qualification
appropriate to their effects. Any change that invalidates this disposition's
dependency, ownership, ordering or application assumptions reopens the affected
disposition. Any change to SQL bytes before application requires an updated hash
binding; semantic SQL changes require fresh qualification and independent
disposition. After application, retain the actual applied hash even if later
ledger/header metadata changes. This exception becomes effective only after
independent review and normal acceptance into canonical Macro main.

### Readback repair and executable preservation

The previous full-file hash
`b5d642dc7da65eceddedd24062d621c7efc481cd62a05e891eaaf6a12ff4a628`
returned table names and object counts, but omitted ten typed expected entries
from the incumbent applier's named-object readback. The repaired file retains
the existing privilege/RLS query and adds actual catalog names, kinds, schemas,
owning tables and function signatures. This changes executed verification
behavior, so the binding above points to the new file and its actual commit.

The executable DO span is byte-identical: 7,106 bytes, SHA-256
`a6845559c01e3e22f141992d1be9f80b6892dbdf582539fb35d456d821273985`.
The generic applier is unchanged. On an isolated local cluster, its first apply
and replay both produce complete receipts; the old count-only readback fails
with ten missing typed entries. A trigger-only removal also proves that the
applier's bare-name check alone cannot establish typed closure when a same-named
function survives, including when attached only to an unrelated relation.
Before declaring production application verified, inspect all twelve typed
catalog objects and the retained RLS/privilege rows, in addition to the applier's
status. Local psql transport does not prove production HTTP transport or
production application. The prior dependency/ownership disposition is preserved;
the readback and revised exact binding require independent review.

### Why this candidate can be separated

0037 creates only `medtech_watches`, `medtech_reviewed_changes` and their
own indexes, constraints, account policies and guard functions. Its external
schema prerequisites are existing compatible `auth.users`, `auth.uid()`,
database roles and UUID/PostgreSQL facilities. It references no saved-view,
Investigation, drawing or Portfolio object.

In particular, #778/0035 changes `workspace_settings` and its saved-view guard.
It is not a schema prerequisite of 0037. The reviewed 0037 PostgreSQL fixture
qualifies account isolation, immutable baselines, review receipts, privilege
boundaries and a concurrent quota without those unrelated migrations. A fresh
production catalog preflight remains necessary; isolated qualification is not
production application proof.

### Preserved owners and evidence

- Terminal #1084 is the sole 0037 carrier. Its current full SQL file is
  [bound at 9d080bd](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/9d080bdca3bcce8ec10c1fce4e1ca30386d6d3c3/supabase/migrations/0037_medtech_watches.sql).
  The [readback qualification](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/9d080bdca3bcce8ec10c1fce4e1ca30386d6d3c3/docs/evidence/medtech-r14-applier-readback-qualification-20261020.json)
  supplies 38 disposable PostgreSQL checks through the incumbent per-file
  applier, including actual typed catalog closure and discriminating controls.
  The prior [identifier qualification](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/54caaf9a6fd586144c733ca7b68189ffbb0d5d94/docs/evidence/medtech-r14-identifier-parity-20261020.json)
  remains historical executable-DDL evidence; it does not bind the repaired
  full-file hash or establish the former readback's completeness.
- #804 retains 0029/0030 and its release hold; 0030 is not adopted or applied.
- #858 retains 0031 and its [October 19 application evidence](https://github.com/mastermindx-market-intelligence/mastermind-terminal/pull/858#issuecomment-6260582227).
  Applied-but-unmerged is distinct from unapplied. Do not replay it.
- #778 retains the unapplied 0035 claim and hold at
  `88f2919a5c2222bcf05f452f2549b9af180dcae6`.
- #1044 retains 0036 and its [recovered original application receipt and
  independent catalog reconciliation](https://github.com/mastermindx-market-intelligence/mastermind-terminal/pull/1044#issuecomment-6283607982).
  Do not replay it. Earlier MedTech prose calling 0036 unapplied is stale.
- Current Terminal master already records 0026 as merged/applied; the older
  Portfolio amendment's historical description does not govern current state.
- All other reservations, holds, historical records and applied bytes remain
  with their existing owners.

### Scope, alternatives and reconsideration

Waiting for unrelated held application/UI work would not protect a schema
dependency. Splitting #1084 into a new SQL-only carrier would add ownership and
ledger work; the solo procedure means separate landing, not a SQL-only PR.
A general ordering waiver, a second migration ledger, renumbering any applied
file and weakening the namespace checker are rejected.

Follow the matching MedTech section in
DEC:TERMINAL-MIGRATION-PR-LANDS-SOLO-WITH-LEDGER-FOLLOWUP. Preserve the actual
application-file hash in its receipt even when later comments/ledger metadata
change. A new SQL dependency, conflicting catalog object, unresolved effect,
changed executable semantics or failed required check reopens the affected
qualification. No production DDL was performed in authoring this amendment.
