# W9 ledger note — the F08 slice of LEDGER_MOVES (#7–#10), proposed and not applied

Packet W9B_REC_F08, drafted 2026-09-13 under the Meta-CEO B ruling of 2026-09-13 16:02Z (W9
planner). A research note only: no product code, no ledger edit, no move applied, and no comment
on any other lane's pull request. Each block below is written so the records stack can paste it
into `orch/w8/LEDGER_MOVES.md` as moves #7–#10, and so the lane that owns the ledger CSV — #7014
— can apply or reject each one on its own terms.

Everything here was read at macro `origin/main` = `321da62b3b0163b6ab5a287fb9847a13ed7f3ed2` and
Terminal `master` = `3db34e7a8e8eca4bef1ca12eba90daab6cc0c10c`, both on 2026-09-13. The ledger
quoted is
`research/market_intelligence_productization/MARKET_ONTOLOGY_F00C_GRANULAR_CLOSURE_LEDGER_2026-09-02.csv`.

## Why this note exists

Four F08 rows still describe the estate as it read before the F08 wave merged. One names a
producer that now exists and calls it `NONE`. One carries a next bounded child that shipped three
days before this note. Two name a missing contract whose delivery half merged while the row still
reads as though nothing had. The Charter's DONE test is computed off that ledger, so each of those
cells under-counts the program by at least one merged pull request — and one of the four, applied
carelessly, reddens two suites on `main`. So this note states, per row: the cells that are stale
as they read today, the merge that motivates the move, the ancestor claim that makes that merge
citable, the state word proposed, the child proposed, and the pins the applying PR must carry in
the same commit.

## What this note deliberately does not do

- It does not edit the ledger CSV and it does not apply any move. #7014 owns the CSV: a records
  lane applies, this note proposes.
- It does not disturb the ledger's shape — no new row, no new column, no changed family, authority
  ceiling, source-rights entry or acceptance sentence. Where an acceptance sentence is now the
  wrong test, the note says so in words and leaves the amendment to the lane that owns the file.
- It does not widen the state vocabulary. The five words used here are NOT_BUILT, SPEC_ONLY,
  PARTIAL, BUILT_NOT_PROVEN and PROVEN_LIVE. PROVEN_LIVE is proposed on no row, because the
  strongest evidence this seat holds is merged code plus an applied DDL with a seat receipt — never
  two people exercising the surface in production with a record of it.
- It writes no Supabase project reference, no personal access token and no key. Where a DDL
  application matters, the citation is the merged ledger-flip pull request and the seat receipt
  that pull request names; the ref is never written.
- It cites no unmerged pull request as evidence for a move. macro #6907 and macro #7131 were both
  OPEN at this read, and both are named below as open — which is precisely why two of these four
  moves stop at PARTIAL rather than going further.
- It promotes no authority ceiling. Every row keeps the ceiling it has today:
  `human_research_only; non-execution — no silent rebalance/size` on MO-DELTA-003, `context_only`
  on MO-DELTA-042, `notification_only` on MO-PAID-027 and on MO-PAID-085.

## What the state words mean here

The definitions are the ones the F00C reconciliation record already carries, restated so this note
can be read on its own.

- `NOT_BUILT` — no producer exists in either repository for what the row describes.
- `SPEC_ONLY` — a spec exists; no producer does.
- `PARTIAL` — an open word. Part of the row's own acceptance sentence is met and part is not, and
  the row says which part is missing.
- `BUILT_NOT_PROVEN` — the capability is merged to the relevant default branch and, where it needed
  a database change, that change was applied to production with a receipt. It does not mean anyone
  has used it.
- `PROVEN_LIVE` — reserved for a capability with a production readback behind it: two people
  exercising the surface, recorded. Nothing in this note proposes it, and nothing in this note
  anticipates it.

A move that only corrects stale text is still a move, and two of the four below are of that kind:
the state word stays where it is and the cells that describe reality change. That is named
explicitly on each row so nobody reads "unchanged state" as "nothing to apply".

## How every merge citation below was verified

- macro merges: `git merge-base --is-ancestor <merge sha> origin/main`, run inside this worktree at
  `321da62b3b0163b6ab5a287fb9847a13ed7f3ed2` — true for every macro sha quoted below.
- Terminal merges:
  `gh api repos/mastermindx-market-intelligence/mastermind-terminal/compare/<merge sha>...master`
  — `ahead` (master descends from the merge) or `identical` (master IS the merge), for every
  Terminal sha quoted below. No Terminal checkout was opened to produce this note; the compare
  call is the whole of the evidence, and a reader can repeat it.
- The ledger cells quoted below were read from the CSV at macro `origin/main`, byte for byte, and
  the in-repo line citations (`app/mailer.py:1004`, `engine/portfolio_digest.py:5` and the rest)
  were read at the same commit.

## The four moves

### LEDGER_MOVES #7 — MO-DELTA-003 (F08-PORTFOLIO-ALERTS, CONTEXT_ONLY)

Row: `MO-DELTA-003`. Reads on macro `origin/main` today as `capability_state_c2 = NOT_BUILT`,
`granular_disposition = CONTEXT_ONLY`, `authority_ceiling = human_research_only; non-execution — no
silent rebalance/size`, `acceptance_test = a logged-in user builds role/weight targets computing
triggers against real holdings`.

Stale text as it reads on macro `origin/main` (quoted):

- `real_producer`: `NONE (templates/calculators/portfolio_rebalancing.html.j2 is standalone public
  SEO)` — stale. A constructor over canonical holdings now has a real producer on Terminal master,
  and the public SEO calculator at `templates/calculators/portfolio_rebalancing.html.j2` (present
  on `origin/main`) is a separate, unrelated surface that this row was never about.
- `real_consumer`: `public SEO page only` — stale for the same reason: the consumer is the
  signed-in Terminal portfolio page, not the anonymous calculator.
- `state_delta`: `UNCHANGED (SEO calculator exists but is not a constructor over canonical
  holdings)` — stale. Its parenthetical was true when written and is false now.
- `missing_contract_or_proof`: `role/weight/rebalance-trigger construction over canonical holdings`
  — partly stale. The weight half shipped; the role half did not; no rebalance trigger exists
  anywhere and none may, under the ceiling this row already carries.
- `next_bounded_child`: `DEFER — F08 lane constructor law (forward scope); non-execution constraint
  stands` — spent. The constructor law it defers to was ruled on 2026-09-06 in
  `agentos/decisions/DEC-F08-PORTFOLIO-CONSTRUCTOR-IS-RESEARCH-ONLY-2026-09-06.md`: research-only,
  non-execution, no order routing, no broker hook, and target storage itself deferred to a later
  slice needing its own ruling. A DEFER that points at a decision already taken is not a child.

Merge citation: terminal #552, `[MO-BB5] B-F08-B5-1: Portfolio construction targets — your own
weight targets and drift bands over canonical holdings, readout only (DDL 0023, shipped unapplied)`,
MERGED 2026-09-10T15:19:54Z as `9022e0138dc11f700a4a7ac5297b09077522ff8e`. Producers:
`terminal/lib/portfolioTargets.ts`, `terminal/app/api/portfolio/targets/route.ts`,
`terminal/components/PortfolioView.tsx`, DDL `supabase/migrations/0023_portfolio_targets.sql`. The
DDL that #552 shipped unapplied was applied to production on 2026-09-13T06:57:13Z and recorded by
terminal #580, `[MO-B] Ledger flip: 0022/0023 applied in production 2026-09-13 (seat receipts)`,
MERGED 2026-09-13T11:20:34Z as `3db34e7a8e8eca4bef1ca12eba90daab6cc0c10c`; the apply receipt is
held by the seat in the handoff kit (`ddl/receipt_0023.json`) and the project ref is never written.
#552's own Records line keeps the ceiling where this row keeps it: "Ledger row MO-DELTA-003.
Authority ceiling unchanged: user-typed weights + drift readout only."

Ancestor claim: `9022e0138dc11f700a4a7ac5297b09077522ff8e` is an ancestor of Terminal `master`
(compare status `ahead`), and `3db34e7a8e8eca4bef1ca12eba90daab6cc0c10c` IS Terminal `master` at
this read (compare status `identical`). Neither sha was taken from a checkout this repository owns.

Proposed capability_state_c2: PARTIAL

Why PARTIAL and not further: the row's own acceptance sentence names two objects — role/weight
targets, and triggers computed against real holdings. The weight half shipped: a signed-in person
types a target weight and a drift band per holding, and the readout computes the gap in points and
a `within_band` / `outside_band` verdict over the canonical book, folded to one holding per ticker
so two open lots of the same name read as one position. The role half does not exist: the token
`role` appears nowhere in `terminal/lib/portfolioTargets.ts`. A drift band is a research verdict
about a gap, not a rebalance trigger, and the ceiling forbids it becoming one. Half a sentence is
not the sentence — the same rule the F00C reconciliation applied to `MO-DELTA-014` — so the row
moves off NOT_BUILT and stops at PARTIAL. PROVEN_LIVE is not available to it either way: nobody has
exercised the surface in production.

Proposed next_bounded_child: ONE child: settle the role half of the acceptance sentence — either
ship role targets under the same `human_research_only` ceiling, or amend the sentence to the
weight targets that actually shipped in terminal#552 (merged 9022e013) and record that amendment
as a decision; and owe the routed-page acceptance journey in production (a signed-in person saves
a target and reads the drift verdict against their own book) before this row reads above PARTIAL.

Proposed co-text for the same edit, offered so the CSV move is one act and not four (each is a
proposal, none is applied here):

- `state_delta`: `EVIDENCE-REFINED: terminal#552 (merged 9022e013) ships user-typed weight targets
  and drift bands over canonical holdings, readout only, under the DEC-F08-PORTFOLIO-CONSTRUCTOR-
  IS-RESEARCH-ONLY ceiling; DDL 0023 applied in production 2026-09-13 per terminal#580 (seat
  receipts). No role target shipped and no rebalance trigger may exist. State moves off NOT_BUILT;
  nobody has exercised the surface.`
- `real_producer`: `terminal/lib/portfolioTargets.ts + terminal/app/api/portfolio/targets/route.ts
  + terminal/components/PortfolioView.tsx on Terminal master (terminal#552, merged 9022e013; DDL
  0023 applied per terminal#580). templates/calculators/portfolio_rebalancing.html.j2 remains a
  standalone public SEO surface and is not this row's producer.`
- `real_consumer`: `the signed-in Terminal portfolio page (targets card in PortfolioView.tsx)`
- `missing_contract_or_proof`: `role targets (or an amended acceptance sentence) + a production
  acceptance journey over real holdings; rebalance triggers stay out of scope by ceiling`
- Keep unchanged: `granular_disposition`, `acceptance_test`, `source_rights`, `authority_ceiling`,
  `correction_behavior`.

### LEDGER_MOVES #8 — MO-DELTA-042 (F08-PORTFOLIO-ALERTS, PROJECTION_ONLY)

Row: `MO-DELTA-042`. Reads on macro `origin/main` today as `capability_state_c2 =
BUILT_NOT_PROVEN`, `granular_disposition = PROJECTION_ONLY`, `authority_ceiling = context_only`,
`acceptance_test = the event object schema resolves to affected positions`.

Stale text as it reads on macro `origin/main` (quoted):

- `next_bounded_child`: `ONE child: add the F08 §9 invalidation element to the shipped event-object
  schema, so an event states the condition that would void it alongside direction, mechanism and
  timeframe — carried on this row because MO-PAID-028's own sentence is now met and its child is
  empty.` — spent. That element shipped.
- `missing_contract_or_proof`: `machine-readable event schema (direction/mechanism/timeframe/
  invalidation) + mapping` — stale: the schema now carries all four elements, so nothing in this
  cell is missing any more.
- `adjudication_notes`: `pair-adjudication with MO-PAID-028. Residual: the shipped object carries
  direction, mechanism and timeframe but no invalidation field, and only the earnings calendar keys
  by ticker, so the two other published calendars stay unjoinable and are disclosed as such on the
  surface.` — the first half of the residual is stale; the second half (the unjoinable calendars)
  still stands and is still disclosed on the surface.
- `state_delta` and `real_producer` name only terminal#522 and are incomplete rather than wrong.

Merge citation: terminal #576, `[MO-BW6] B-F08-8: What would void this read — the invalidation
condition on every event impact (MO-DELTA-042 residual)`, MERGED 2026-09-13T06:23:11Z as
`45a0e78e01377502399761626899458f9d08ffd9`. Producers: `terminal/lib/eventImpact.ts`,
`terminal/components/EventImpactPanel.tsx`. It adds `EventInvalidation` to `EventTouch`, required at
compile time and pinned by a runtime guard, table-driven over every mapped event kind, with a typed
null where no defensible ticker-keyed metric exists (`macro_release` and `index_review`, the two
calendars the module already discloses as unjoinable). #576's own Records line reads: "MO-DELTA-042
residual closed — the `invalidation` element is now on every event impact. The row stays
BUILT_NOT_PROVEN (routed-page acceptance journey owed)." The row's earlier citation stands beside
it: terminal #522, MERGED 2026-09-07T15:40:03Z as
`68b0d00a8ffe4145786c0e2aa9775e44a279ad80`.

Ancestor claim: `45a0e78e01377502399761626899458f9d08ffd9` and
`68b0d00a8ffe4145786c0e2aa9775e44a279ad80` are both ancestors of Terminal `master`
`3db34e7a8e8eca4bef1ca12eba90daab6cc0c10c` (compare status `ahead` for each).

Proposed capability_state_c2: BUILT_NOT_PROVEN

The state word does not move — this is a text move, and the note says so plainly so nobody reads it
as a no-op. The row already reads BUILT_NOT_PROVEN and BUILT_NOT_PROVEN is still exactly right:
merged to the Terminal default branch, no DDL of its own to apply, and nobody recorded using it.
What moves is the child, the missing-contract cell and the residual clause. PROVEN_LIVE stays out of
reach until the routed-page acceptance journey on the live page with the production calendar is
recorded, which #576 names as still owed.

Proposed next_bounded_child: ONE child: the routed-page acceptance journey for the event object on
the live portfolio page with the production calendar — the invalidation element itself shipped in
terminal#576 (merged 45a0e78e) on every mapped event kind, with a typed null where no ticker-keyed
metric exists, and the residual that remains is that only the earnings calendar keys by ticker, so
the two other published calendars stay unjoinable and are disclosed as such on the surface.

That wording keeps the token `invalidation` in this row's child deliberately, and the reason is a
pin on `main`: `tests/test_f00c_terminal_reconciliation.py::test_the_event_object_invalidation_
residual_has_exactly_one_owner` requires exactly one of `MO-PAID-028` / `MO-DELTA-042` to name the
element in `next_bounded_child`, and requires that the one is `MO-DELTA-042`. A child that drops the
word — even correctly, because the element shipped — reddens that suite unless the pin is amended
in the same commit. Keeping the word, in a sentence that says it shipped, satisfies the pin and
states the truth.

Proposed co-text for the same edit:

- `state_delta`: `The machine-readable event object shipped in terminal#522 (merged 68b0d00a) and
  carries its fourth element since terminal#576 (merged 45a0e78e): direction, mechanism, timeframe
  and invalidation are carried from the source or printed as not stated, with a typed null where no
  ticker-keyed metric exists, and the object resolves to the affected open positions. No production
  acceptance journey recorded; nobody has used it.`
- `real_producer`: `terminal/lib/eventImpact.ts + terminal/components/EventImpactPanel.tsx on
  Terminal master (terminal#522, merged 68b0d00a; invalidation added by terminal#576, merged
  45a0e78e)`
- `missing_contract_or_proof`: `a production acceptance journey on the routed page (the schema
  itself — direction/mechanism/timeframe/invalidation + mapping — is merged)`
- `adjudication_notes`: `pair-adjudication with MO-PAID-028. Residual: the invalidation element
  shipped in terminal#576; what remains is that only the earnings calendar keys by ticker, so the
  two other published calendars stay unjoinable and are disclosed as such on the surface, and no
  routed-page acceptance journey has been recorded.`
- Keep unchanged: `granular_disposition`, `acceptance_test`, `source_rights`, `authority_ceiling`,
  `correction_behavior`, `real_consumer` (still `NONE` — this note found no consumer evidence and
  proposes no invention of one).

### LEDGER_MOVES #9 — MO-PAID-027 (F08-PORTFOLIO-ALERTS, UPGRADE_EXISTING_OWNER)

Row: `MO-PAID-027`. Reads on macro `origin/main` today as `capability_state_c2 = PARTIAL`,
`granular_disposition = UPGRADE_EXISTING_OWNER`, `authority_ceiling = notification_only`,
`acceptance_test = a held position generates a material-change alert reaching a delivery channel`.

Stale text as it reads on macro `origin/main` (quoted):

- `state_delta`: `UNCHANGED` — stale. Three pull requests in this lane merged since the cell was
  written, one of them in this repository.
- `missing_contract_or_proof`: `delivery path + held-position->material-change->alert journey` —
  half stale. The delivery path merged; the held-position journey did not.
- `real_producer`: `engine/alerts.py (rule engine -> data/alerts/alerts_log.parquet) +
  engine/alert_triage.py (command-center display)` — incomplete: it omits the merged delivery leg
  this repository now owns.
- `next_bounded_child`: `F08 lane program (marketontology-f08-portfolio-alerts-20260826-fable-001)
  owns the delivery-path build` — spent as written. The delivery-path build merged; what the lane
  owes now is the enable and the producer that fires on a held position.

Merge citation: macro #6906, `[MO-BB1] B-F08-1b: Alert delivery leg: mailer alert message type +
off-render outbox drain with run receipts`, MERGED 2026-09-10T04:09:10Z as
`85587051495c7bdd4949d8efa1efd298d9a47214` — `app/mailer.py` gains the alert message type
(`ALERT_TEMPLATE = "alert_fire"` at `app/mailer.py:1004`, `ALERT_CLS = "transactional"` at `:1005`,
`compose_alert()` at `:1052`), plus `engine/alert_delivery_drain.py`, `scripts/drain_alert_outbox.py`
and the off-render units `app/deploy/macro-alert-drain.service` / `.timer`. Beside it, in the
Terminal: #513, `[MO-BB1T] B-F08-2: Alert run receipts + fire-to-delivery outbox in the Terminal
evaluator (migration 0013)`, MERGED 2026-09-06T20:58:41Z as
`be898be59a761768a0a61c424aea7f83c2b95087` (`ingest/alerts_engine.py`,
`supabase/migrations/0013_alert_runs_outbox.sql`), and #517, `[MO-BB2] B-F08-3: In-product alerts
surface in the Terminal shell: list, drillback, calm/degraded states, delivery outcome`, MERGED
2026-09-07T07:21:21Z as `ee88afaf0bc1aa68efb5a26f3e63286cbde9ab5a`
(`terminal/app/(shell)/alerts/page.tsx`, `terminal/components/AlertsView.tsx` and the
`terminal/components/alerts/` set).

Ancestor claim: `85587051495c7bdd4949d8efa1efd298d9a47214` is an ancestor of macro `origin/main`
`321da62b3b0163b6ab5a287fb9847a13ed7f3ed2` (`git merge-base --is-ancestor` → true);
`be898be59a761768a0a61c424aea7f83c2b95087` and `ee88afaf0bc1aa68efb5a26f3e63286cbde9ab5a` are
ancestors of Terminal `master` `3db34e7a8e8eca4bef1ca12eba90daab6cc0c10c` (compare status `ahead`
for each). Migration 0013 is recorded applied; Terminal master states 0013–0023 applied as of
terminal #580.

Proposed capability_state_c2: PARTIAL

The state word does not move, and the note is explicit about why. The acceptance sentence is "a
held position generates a material-change alert reaching a delivery channel", and three things still
stand between the row and that sentence:

1. No merged producer evaluates a held position for a material change and files a fire. macro
   `engine/portfolio_changes.py` is a display spine that, in its own words at
   `engine/portfolio_changes.py:20`, "READS ctx and returns strings; it writes nothing, anywhere";
   `engine/portfolio_digest.py` composes a marketing-class digest and states at
   `engine/portfolio_digest.py:5` "**THE SEND PATH IS NOT WIRED, DELIBERATELY.**"; and the Terminal
   evaluator `ingest/alerts_engine.py` evaluates user-defined condition rows over a symbol manifest,
   not the A1A book. The F08 freeze §8 is the design that is still owed: "held-position
   material-change monitoring is evaluated implicitly over the A1A book — it creates NO per-position
   `alerts` rows".
2. The delivery lane that did merge ships DORMANT. `scripts/drain_alert_outbox.py:43` requires
   `ALERT_DRAIN_ENABLE=1`, and `app/deploy/README.md:361-365` records that enabling live sends
   requires a separate opus privacy/risk review (F08 freeze §10 V4) and that "this packet is not
   that review". That review has not been performed.
3. `app/mailer.py` runs mail-off. `is_configured()` at `app/mailer.py:126` requires host + user +
   pass + from; `docs/ops/email-support-setup.md:3` records that the code "works today in **mail-off
   mode**"; a send attempt therefore types `skipped_no_smtp` (`app/mailer.py:350`), and with the
   drain dormant nothing even reaches that branch.

So the delivery path is merged and the journey is not. PARTIAL is the honest word; the cells are
what move.

Proposed next_bounded_child: ONE child, the V4 enable slice the F08 freeze §10 names, in this order:
(1) one merged producer that evaluates a held position over the A1A book for a material change and
files the fire into the §6 outbox, creating no per-position alerts rows; (2) the opus privacy/risk
review that `app/deploy/README.md:361-365` requires before live sends; (3) the mailer's SMTP
credentials and `ALERT_DRAIN_ENABLE=1` in the deployed environment; and then one real fire observed
reaching `app/mailer.py` or typing its failure, recorded. Until all of it lands the acceptance
sentence is unmet and the row stays open.

Proposed co-text for the same edit:

- `state_delta`: `EVIDENCE-REFINED: the delivery leg merged — macro#6906 (85587051495c) adds the
  alert_fire mailer message type, the off-render outbox drain and its systemd units; terminal#513
  (be898be5) the fire-to-delivery outbox and run receipts; terminal#517 (ee88afaf) the in-product
  alerts surface. The drain ships dormant behind ALERT_DRAIN_ENABLE=1, the mailer runs mail-off, and
  no producer fires on a held position, so the acceptance sentence is still unmet. State unchanged.`
- `real_producer`: `engine/alerts.py (rule engine -> data/alerts/alerts_log.parquet) +
  engine/alert_triage.py (command-center display) + app/mailer.py alert_fire message type and
  engine/alert_delivery_drain.py / scripts/drain_alert_outbox.py (macro#6906, merged 85587051495c,
  dormant) + ingest/alerts_engine.py receipts and outbox on Terminal master (terminal#513, merged
  be898be5)`
- `real_consumer`: `Alert Command Center (macro tier live) + the signed-in Terminal alerts page
  (terminal#517, merged ee88afaf). No per-user email has been delivered: the drain is dormant and
  the mailer is mail-off.`
- `missing_contract_or_proof`: `held-position material-change producer over the A1A book + the V4
  opus privacy/risk review + SMTP credentials and ALERT_DRAIN_ENABLE=1 in the deployed environment`
- Keep unchanged: `granular_disposition`, `acceptance_test`, `source_rights`, `authority_ceiling`,
  `correction_behavior`.

### LEDGER_MOVES #10 — MO-PAID-085 (F08-PORTFOLIO-ALERTS, UPGRADE_EXISTING_OWNER)

Row: `MO-PAID-085`. Reads on macro `origin/main` today as `capability_state_c2 = NOT_BUILT`,
`granular_disposition = UPGRADE_EXISTING_OWNER`, `authority_ceiling = notification_only`,
`acceptance_test = a set preference causes an actual send on the next matching alert`.

Stale text as it reads on macro `origin/main` (quoted):

- `real_producer`: `app/account_prefs.py (no alert prefs) + engine/portfolio_digest.py ('SEND PATH
  IS NOT WIRED, DELIBERATELY')` — half stale, and the half that is stale matters. The digest clause
  is still literally true at this commit (`engine/portfolio_digest.py:5`), and macro's
  `app/account_prefs.py` still holds no alert keys. But the cell reads as though no alert-preference
  surface exists anywhere, and one does: a merged Terminal settings panel with an Alert delivery
  section, plus a merged alert-class mailer message type in this repository.
- `missing_contract_or_proof`: `alert/notification preference UI/API + mailer wiring` — partly
  stale. The preference UI merged and the alert-class mailer wiring merged; the macro preference API
  keys did not, and no send occurs.
- `real_consumer`: `NONE` — stale: the merged Terminal settings panel is a consumer of the
  preference contract, rendering a calm not-available state until the macro API lands.
- `state_delta`: `UNCHANGED` — stale, for the same reason.
- `next_bounded_child`: `F08 delivery-path child includes prefs + app/mailer.py wiring (not
  rights-blocked)` — stale in shape: it folds this row into a delivery-path child that has since
  merged in part, and it does not name the two things that actually block the acceptance sentence.

Merge citation: terminal #545, `[MO-BB1] B-F08-6: Alert delivery preferences in the Terminal
settings panel, read and saved through a BFF route over macro's account-prefs API (plain-language
EN/ZH, calm not-available state until #6907 deploys)`, MERGED 2026-09-09T18:18:08Z as
`1736907777486fc3ea7111da0cd676d418c3d8c8` — `terminal/app/api/account/alert-prefs/route.ts`,
`terminal/components/settings/SectionAlertDelivery.tsx`, `terminal/components/settings/SettingsPanel
.tsx`. terminal #551, `[MO-BB1] B-F08-7b: Terminal account-preference writes are fenced to the keys
the Terminal owns (never alert delivery keys) — the Terminal half of the single-writer repair`,
MERGED 2026-09-10T17:33:02Z as `ee320e390f9c09231a54e06c0e941f43875c198f`
(`terminal/lib/accountPrefs.ts`, `terminal/lib/prefDelivery.ts`). macro #7013, `[MO-BB1] B-F08-7a:
Account preferences writer no longer clobbers the Terminal's keys — fresh read before write,
key-scoped merge, tz default from fresh state (macro side)`, MERGED 2026-09-10T13:55:19Z as
`0c1801c4efa587d9edb8383ebe252215173311ff` (`app/account_prefs.py`, `lib/user_prefs.py`) — the
single-writer repair's macro half, which is what makes one prefs sink safe for two writers. macro
#6906, MERGED 2026-09-10T04:09:10Z as `85587051495c7bdd4949d8efa1efd298d9a47214` — the alert-class
mailer message type (`app/mailer.py:1004`).

Ancestor claim: `0c1801c4efa587d9edb8383ebe252215173311ff` and
`85587051495c7bdd4949d8efa1efd298d9a47214` are ancestors of macro `origin/main`
`321da62b3b0163b6ab5a287fb9847a13ed7f3ed2` (`git merge-base --is-ancestor` → true for each);
`1736907777486fc3ea7111da0cd676d418c3d8c8` and `ee320e390f9c09231a54e06c0e941f43875c198f` are
ancestors of Terminal `master` `3db34e7a8e8eca4bef1ca12eba90daab6cc0c10c` (compare status `ahead`
for each).

Named as OPEN, and therefore cited as no move's evidence: macro #6907, `[MO-BB1] B-F08-1a: Alert
delivery preferences: email opt-in, category, timezone, quiet hours (API + signed-in account
surface)`, which is the macro account-prefs API leg the merged Terminal panel waits for —
terminal #545's own GAPS line reads "The live round-trip against a deployed #6907 is still owed";
and macro #7131, the digest send-path honesty packet, which touches `engine/portfolio_digest.py`.
Both were OPEN at this read.

Proposed capability_state_c2: PARTIAL

Why PARTIAL and not further: the acceptance sentence is "a set preference causes an actual send on
the next matching alert". Nobody can set an alert preference against macro's API yet, because
`app/account_prefs.py` on `origin/main` carries no alert keys and #6907 is open, so the merged
Terminal panel renders its calm not-available state. And no send happens at all: the mailer is
mail-off (`docs/ops/email-support-setup.md:3`), the transactional drain is dormant
(`app/deploy/README.md:361-365`, behind a privacy/risk review that has not been performed), and the
digest's own marketing-class send path is unwired on `origin/main`
(`engine/portfolio_digest.py:5`). The row does move off NOT_BUILT — a merged preference surface in
the Terminal, a merged write fence on both sides, and a merged alert-class mailer message type are
real producers — and it stops at PARTIAL because the sentence's verb is "causes an actual send".

Proposed next_bounded_child: ONE child: land and deploy macro#6907's alert-preference keys in
`app/account_prefs.py` / `lib/user_prefs.py` so the merged Terminal panel (terminal#545, merged
17369077) reads and saves against a real API instead of its calm not-available state, and then prove
the acceptance sentence end to end — one set preference causes one actual send on the next matching
alert, or types its failure — which needs the mailer's SMTP credentials and, for the transactional
class, `ALERT_DRAIN_ENABLE=1` after the opus privacy/risk review that
`app/deploy/README.md:361-365` requires. The digest's marketing-class leg needs its own
opt-in / suppression / one-click-unsubscribe wiring and is a separate child, not this one.

Proposed co-text for the same edit:

- `state_delta`: `EVIDENCE-REFINED: the alert-preference surface merged in the Terminal (terminal#545
  17369077, BFF route over macro's account-prefs API, calm not-available state until macro#6907
  deploys) with both writers fenced (terminal#551 ee320e39; macro#7013 0c1801c4) and the alert-class
  mailer message type merged in macro (macro#6906 85587051495c). macro's sink still holds no alert
  keys (#6907 OPEN), the mailer is mail-off, the drain is dormant and the digest send path is
  unwired, so no preference causes a send. State moves off NOT_BUILT.`
- `real_producer`: `terminal/app/api/account/alert-prefs/route.ts +
  terminal/components/settings/SectionAlertDelivery.tsx on Terminal master (terminal#545, merged
  17369077; writes fenced by terminal#551, merged ee320e39) over macro app/account_prefs.py, which
  still holds no alert keys (macro#6907 OPEN; single-writer repair merged as macro#7013, 0c1801c4) +
  app/mailer.py alert_fire message type (macro#6906, 85587051495c) + engine/portfolio_digest.py
  ('SEND PATH IS NOT WIRED, DELIBERATELY', still literally true at line 5)`
- `real_consumer`: `the signed-in Terminal settings panel (Alert delivery section), rendering a calm
  not-available state until macro#6907 deploys; no email consumer yet`
- `missing_contract_or_proof`: `macro alert-prefs API keys (macro#6907 OPEN) + one real send: SMTP
  credentials, and for the transactional class ALERT_DRAIN_ENABLE=1 behind the V4 privacy/risk
  review; the digest's marketing-class leg still needs opt-in, suppression and one-click
  unsubscribe`
- `source_rights`: keep `email via existing app/mailer.py (unwired, not rights-blocked)` — the
  rights position did not change; only the wiring did, and it changed only for the alert class.
- Keep unchanged: `granular_disposition`, `acceptance_test`, `authority_ceiling`,
  `correction_behavior`.

PIN WARNING for the applying lane: `tests/test_b_rec3_wave_boundary_records.py` pins this row's raw
CSV line byte-identical to base `ecaf8f8e` — `_UNTOUCHED_F12_ROWS_AT_BASE['MO-PAID-085']`, asserted
by `test_the_untouched_f12_rows_are_byte_identical_to_base`, whose docstring says 084/085/088 "are
not owned by this wave". Its sibling `test_the_untouched_f12_rows_keep_an_open_state_word` allows
NOT_BUILT, SPEC_ONLY or PARTIAL, so the PARTIAL proposed here keeps that pin green. A PR that
applies move #10 must therefore amend the byte-identical pin (and that docstring's claim) in the
same commit, and must leave `MO-PAID-084` and `MO-PAID-088` byte-identical — this note proposes
nothing for either.

## Pins an applying PR must carry in the same commit

| move | pin on `main` today | what the applying PR must do |
| --- | --- | --- |
| #7 MO-DELTA-003 | none found. No suite on `origin/main` names this row. | Apply the cell edits; nothing else is owed. |
| #8 MO-DELTA-042 | `tests/test_f00c_terminal_reconciliation.py`: `test_manifest_mirrors_the_ledger_next_bounded_child` (manifest must equal the ledger's child), `test_the_event_object_invalidation_residual_has_exactly_one_owner` (exactly one of MO-PAID-028 / MO-DELTA-042 names the element, and it must be MO-DELTA-042), `test_ledger_row_is_unique_and_matches_the_manifest_state` (ledger state must equal the manifest state). | Update `research/market_intelligence_productization/F00C_TERMINAL_WAVE_RECONCILIATION_MANIFEST_2026-09-09.json` for this row's `next_bounded_child` in the same commit, and keep the token `invalidation` in the new child (the wording proposed above does) so the owner pin stays green without amendment. |
| #9 MO-PAID-027 | none found. No suite on `origin/main` names this row. | Apply the cell edits; nothing else is owed. |
| #10 MO-PAID-085 | `tests/test_b_rec3_wave_boundary_records.py`: `test_the_untouched_f12_rows_are_byte_identical_to_base` (raw CSV line pinned to base `ecaf8f8e`) and `test_the_untouched_f12_rows_keep_an_open_state_word` (NOT_BUILT / SPEC_ONLY / PARTIAL only). | Amend the byte-identical pin and its docstring in the same commit; PARTIAL keeps the open-state pin green; leave MO-PAID-084 and MO-PAID-088 untouched. |

Two ledger-wide pins also bind any applying PR, and neither is disturbed by these four moves:
`tests/test_f00c_terminal_reconciliation.py::test_ledger_shape_is_unchanged` (131 lines including
the header, 15 columns, unchanged order) and
`tests/test_market_ontology_half_b_rights_docket.py` (130 data rows). No move here adds or removes
a row. The Half-A K-chain docket's parity pin
(`tests/test_market_ontology_half_a_k_chain_docket.py`, which requires its own "Ledger evidence"
line to agree with the CSV on `granular_disposition`, `capability_state_c2` and `real_consumer`)
names MO-DELTA-006, MO-PAID-016, MO-PAID-018, MO-PAID-024, MO-PAID-033, MO-PAID-042, MO-PAID-043
and MO-PAID-044 — none of the four rows in this note — so it is unaffected. Note that move #9 does
propose a new `real_consumer` for MO-PAID-027; had that row been in the docket, the docket would
have owed the same edit.

## What would falsify these proposals

- #7: a role-target surface merged on Terminal master, or a recorded production acceptance journey,
  moves the row above PARTIAL. A readback contradicting terminal #580 — DDL 0023 not in fact applied
  — drops it back to NOT_BUILT, because the storage the targets surface writes to would not exist.
- #8: a readback of `terminal/lib/eventImpact.ts` at master showing no invalidation element on a
  mapped kind would falsify the citation and leave the child exactly as it reads today. A recorded
  routed-page acceptance journey changes the child and is the only thing that would move the state
  word; this note proposes no such move.
- #9: one merged producer that fires on a held position, plus one observed send or typed failure,
  moves the row to BUILT_NOT_PROVEN. A production readback of two people receiving one alert is
  what would move it further, and this note never proposes that word.
- #10: macro #6907 merged and deployed plus one observed send moves the row to BUILT_NOT_PROVEN. If
  #6907 closes unmerged, the Terminal panel keeps its not-available state and PARTIAL is already
  generous; the note's proposal would then need re-reading, not defending.

## Where the evidence lives

`tests/test_w9_ledger_note_f08.py`, one suite and one test, pins this file: that it exists; that it
names all four rows; that the bare word BUILT_NOT_PROVEN begins with appears nowhere in it, in
any case, BUILT_NOT_PROVEN being the only allowed form with that prefix; that it carries no
Supabase project reference, personal access token or key; and that every row's block carries the
five labelled lines
ruling R1 requires — a quoted stale text, a merge citation, an ancestor claim, a proposed state
inside the five-word vocabulary and never PROVEN_LIVE, and a proposed next bounded child. The suite
reads this note and nothing else: not the ledger CSV, not the Terminal repository, not a network
call. It therefore cannot pass or fail on the state of a checkout this repository does not own, and
a green run is evidence about this file only.

The ledger cells quoted above are from macro `origin/main` at
`321da62b3b0163b6ab5a287fb9847a13ed7f3ed2`. The merges are cited by pull request, state, merge
timestamp and full merge sha, and every ancestor claim was checked on 2026-09-13 by the two commands
named in "How every merge citation below was verified". Nothing in this note is a claim about any
check being green, in this repository or the other one.

Records: moves proposed, not applied; #7014 owns the CSV.
