# W9 ledger note — the F13 slice of LEDGER_MOVES (#32–#35), proposed and not applied

Packet W9B_REC_F13, drafted 2026-09-13 under the Meta-CEO B ruling of 2026-09-13 16:02Z (W9
planner). A research note only: no product code, no ledger edit, no move applied, and no comment
on any other lane's pull request. Each block below is written so the records stack can paste it
into `orch/w8/LEDGER_MOVES.md` as moves #32–#35, and so the lane that owns the ledger CSV — #7014
— can apply or reject each one on its own terms.

Everything here was read at macro `origin/main` = `a0515d73b9fe2b6109aff84448760a5ccaf773e6` on
2026-09-13 (the head the session was started at, two commits behind the live `origin/main` tip
`e0e3fda2fa2a`; both commits are data-only nightly timings and do not affect the F13 rows this
note reads). The ledger quoted is
`research/market_intelligence_productization/MARKET_ONTOLOGY_F00C_GRANULAR_CLOSURE_LEDGER_2026-09-02.csv`.

## Why this note exists

Four F13 rows still describe the estate as it read before the F13 wave merged. One names the
public-glossary surface that now ships and calls it `NOT_BUILT`. Two name support-mail and
in-product help that now exist as merged code on `main` but still read PARTIAL with no acceptance
journey recorded. One names the personal-accuracy scoring capability that was spec-frozen three
weeks before this note and still reads PARTIAL because the runtime that would close its acceptance
sentence is open. The Charter's DONE test is computed off that ledger, so each of those cells
under-counts the program by at least one merged pull request — and one of the four, applied
carelessly, reddens suites on `main`. So this note states, per row: the cells that are stale as
they read today, the merge that motivates the move, the ancestor claim that makes that merge
citable, the state word proposed, the child proposed, and the pins the applying PR must carry in
the same commit.

## What this note deliberately does not do

- It does not edit the ledger CSV and it does not apply any move. #7014 owns the CSV: a records
  lane applies, this note proposes.
- It does not disturb the ledger's shape — no new row, no new column, no changed family,
  authority ceiling, source-rights entry or acceptance sentence. Where an acceptance sentence is
  now the wrong test, the note says so in words and leaves the amendment to the lane that owns
  the file.
- It does not widen the state vocabulary. The five words used here are NOT_BUILT, SPEC_ONLY,
  PARTIAL, BUILT_NOT_PROVEN and PROVEN_LIVE. PROVEN_LIVE is proposed on no row, because the
  strongest evidence this seat holds is merged code plus an applied DDL with a seat receipt — never
  two people exercising the surface in production with a record of it.
- It writes no Supabase project reference, no personal access token and no key. Where a DDL
  application matters, the citation is the merged ledger-flip pull request and the seat receipt
  that pull request names; the ref is never written.
- It cites no unmerged pull request as evidence for a move. macro #6861 (capability health &
  freshness projection V1) and macro #7133 (the dated product changelog follow-up) were OPEN at
  this read, and both are named below as open — which is precisely why two of these four moves
  stop at PARTIAL rather than going further.
- It promotes no authority ceiling. Every row keeps the ceiling it has today: `learning_only` on
  MO-DELTA-007, `reference_only` on MO-DELTA-011, `operations_only` on MO-PAID-058,
  `operations_and_explanation_only` on MO-PAID-088.

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

A move that only corrects stale text is still a move, and one of the four below is of that kind:
the state word stays where it is and the cells that describe reality change. That is named
explicitly on each row so nobody reads "unchanged state" as "nothing to apply".

## How every merge citation below was verified

- macro merges: `git merge-base --is-ancestor <merge sha> origin/main`, run inside this worktree at
  `a0515d73b9fe2b6109aff84448760a5ccaf773e6` — true for every macro sha quoted below.
- The ledger cells quoted below were read from the CSV at macro `origin/main` (`321da62b3b01` is
  the ancestor that carries the cell text; `a0515d73b9fe` is its descendant and the cell content
  is unchanged between those shas), byte for byte, and the in-repo line citations
  (`lib/help_directory.py`, `lib/glossary.py`, `engine/explanation_memory.py`, `app/support.py`,
  `data/product/changelog.yml`) were read at the same commit.
- No Terminal checkout was opened to produce this note. The F13 rows this packet reads all live on
  the macro side of the split: the glossary is a public-page render, the help page is a public
  page, the support tickets are an `app/support.py` route, and the personal-accuracy ledger is a
  spec freeze pending a runtime that has not opened here. Terminal-side citations, where any are
  needed, are named by their macro-side records documents and merge shas, never by a checkout.

## The four moves

### LEDGER_MOVES #32 — MO-DELTA-007 (F13-OPS-LEARNING, PROJECTION_ONLY)

Row: `MO-DELTA-007`. Reads on macro `origin/main` today as `capability_state_c2 = PARTIAL`,
`granular_disposition = PROJECTION_ONLY`, `authority_ceiling = learning_only`,
`acceptance_test = a user-submitted claim receives a Brier/hit-rate score on a personal ledger
page`, and the row carries the standing ban: `do_not_redo: no universal analyst score conflating
quality/retention/alpha/P&L`.

Stale text as it reads on macro `origin/main` (quoted):

- `state_delta`: `UNCHANGED` — half stale. The spec half of this row is no longer unchanged:
  the personal-accuracy spec was merged 2026-09-06 (#6964) and freezes the data contract, the
  per-episode Brier pair rule, the hit-rate denominator, the six verdict strings, the ceiling's
  seven forbidden uses, and the glance-tier copy block in both languages. What is unchanged is
  the runtime half: no `UserClaim` store exists, no submission surface exists, and the spec
  itself opens with "DATA NULL (2026-09-06): no user-claim store exists in this repository;
  nothing can be scored today and nothing may be fabricated."
- `real_producer`: `engine/explanation_memory.py (grade_thesis/grade_ledger/_compute_brier ->
  site/qledger/explanation_memory.json) + engine/trial_ledger.py (hash-keyed append)` — incomplete.
  The spec freezes `engine/trial_ledger.py:150` as the append-only precedent for `UserClaim`,
  but `engine/trial_ledger.py` is the trial-ledger producer for signal/desk theses only today; a
  `UserClaim` ledger is its sibling, not its instance, and no module on `origin/main` writes one.
- `real_consumer`: `templates/measurement.html.j2 Calibration Lab` — stale. The Calibration Lab
  surface that exists on `origin/main` today renders the trial-ledger scoring for the **existing
  signal/desk thesis** producer and does not read a user-authored `UserClaim` stream. The spec's
  glance-tier copy block is for a different surface — a personal ledger page — that this row's
  acceptance sentence names but no merged code produces.
- `missing_contract_or_proof`: `binding USER-authored claims into scoring (signal/desk theses only
  today) + team rollup` — stale in shape. The contract half is now spec-frozen (#6964, the merged
  F13 personal-accuracy ledger spec); what is missing is the runtime half: a submission route, an
  append-only `UserClaim` ledger, the resolver that converts a matured claim into an
  episode-keyed pair, the Brier-call site, and the personal-page consumer. The team-rollup leg
  is named in the spec as `DEFERRED, NOT KILLED` and stays outside this move.
- `next_bounded_child`: `DEFER — dependency the Thesis-object vertical (user claim authoring
  surface) before Eval OS can score it` — half stale, half still true. The dependency still
  stands: an Eval OS still scores what the Thesis-object vertical produces. What changed is that
  the dependency is now frozen as a contract: the spec names the producer it expects, the
  contract it must keep, the ceiling it must respect, and the seven forbidden uses. A child
  that still says "DEFER — dependency" without naming the frozen contract under-counts the
  program by one merged spec.

Merge citation: macro #6964, `[MO-BB4] B-F13-4: F13 personal accuracy ledger: how a user's own
claims get scored, and what the number may never be used for`, MERGED 2026-09-06T19:55:18Z as
`9d179135a1826787a1b351ab08296d008b286b50`. Producers:
`research/market_intelligence_productization/MARKET_ONTOLOGY_F13_PERSONAL_ACCURACY_LEDGER_SPEC_2026-09-06.md`
(the spec itself). The spec opens with §0 Header and the DATA NULL line, freezes the `UserClaim`
JSONL schema in §1, the Brier/hit-rate rule in §2, the episode rule in §3, the ceiling in §4,
the null ladder in §5, the glance-tier copy block in §6, and the theme treatment in §7. No
runtime landed.

Named as OPEN, and therefore cited as no move's evidence: macro #6861, `feat(f13): capability
health & freshness projection V1 (engine+registry+builder, display-tier)`, which is the F13
display-tier projection lane — distinct from this row's user-claim ledger, and open at this read.

Ancestor claim: `9d179135a1826787a1b351ab08296d008b286b50` is an ancestor of macro `origin/main`
(`git merge-base --is-ancestor` → true).

Proposed capability_state_c2: SPEC_ONLY

Why SPEC_ONLY and not PARTIAL: the row reads PARTIAL today because the spec half and the
runtime half are conflated under one cell. The spec is now frozen (one spec, on `origin/main`,
with the seven-forbidden-uses ceiling, the episode rule and the glance-tier copy block) and the
runtime is absent (DATA NULL line still applies — no `UserClaim` store exists, nothing may be
fabricated). SPEC_ONLY is the honest description of a row whose contract is on `main` and whose
producer is not. PARTIAL is reserved for the moment a runtime exists and only an acceptance
journey is missing. PROVEN_LIVE is not available to it either way: nobody has submitted a claim,
and the spec itself forbids a model-originated score.

Proposed next_bounded_child: ONE child: ship the runtime half that the spec expects — a
`UserClaim` submission route, an append-only ledger file at a path the spec's `engine/trial_ledger.py:150`
precedent licenses, the resolver that converts a matured claim into an episode-keyed pair, the
`brier_reliability` call keyed on probability-carrying episode pairs, and a personal-ledger
consumer that renders the §6 glance-tier copy block in EN and ZH and nothing else above the
fold — and prove the acceptance sentence end to end (one user-submitted claim receives a
Brier/hit-rate score on a personal ledger page) before this row reads above SPEC_ONLY. The
team-accuracy rollup named in this row's `missing_contract_or_proof` cell stays `DEFERRED, NOT
KILLED` per the spec's §4 ruling; the seven forbidden uses in the spec's §4 ceiling travel with
whatever ships, and a child that proposes a cross-user ranking will be refused at the door.

Proposed co-text for the same edit, offered so the CSV move is one act and not four (each is a
proposal, none is applied here):

- `state_delta`: `EVIDENCE-REFINED: spec frozen in #6964 (merged 9d179135) — UserClaim JSONL
  contract, per-episode Brier pair rule, hit-rate denominator, the six verdict strings, the
  learning_only ceiling with seven forbidden uses, and the glance-tier EN/ZH copy block. Runtime
  half is still NULL: no UserClaim store, no submission surface, no resolver, no personal-ledger
  consumer. State moves from PARTIAL to SPEC_ONLY.`
- `real_producer`: `engine/explanation_memory.py (signal/desk thesis scoring only) +
  engine/trial_ledger.py (trial-ledger hash-keyed append, the spec's append-only precedent at
  :150) — the existing module, NOT the user-claim ledger. A user-claim producer does not exist
  on origin/main today.`
- `real_consumer`: `the existing Calibration Lab surface (templates/measurement.html.j2) renders
  signal/desk thesis scoring only; the personal-ledger page the spec's §6 copy block is for does
  not exist on origin/main today`
- `missing_contract_or_proof`: `the runtime half the spec expects: a UserClaim submission
  route, an append-only ledger file, an episode resolver, a brier_reliability call keyed on
  probability-carrying episode pairs, and a personal-ledger consumer that renders §6. The
  team-accuracy rollup stays DEFERRED per the spec's §4 ceiling.`
- Keep unchanged: `granular_disposition`, `acceptance_test`, `source_rights`, `authority_ceiling`,
  `correction_behavior`, the standing `do_not_redo` ban against a universal analyst score.

### LEDGER_MOVES #33 — MO-DELTA-011 (F13-OPS-LEARNING, PROJECTION_ONLY)

Row: `MO-DELTA-011`. Reads on macro `origin/main` today as `capability_state_c2 = PARTIAL`,
`granular_disposition = PROJECTION_ONLY`, `authority_ceiling = reference_only`,
`acceptance_test = a public page lists >=50 defined terms from the existing vocabulary`.

Stale text as it reads on macro `origin/main` (quoted):

- `state_delta`: `UNCHANGED (internal vocabulary substrate exists; the user-facing surface itself
  is NOT_BUILT — F00B's PARTIAL preserved)` — stale. The user-facing surface is now merged to
  `main`. The state_delta half the row still prints ("internal vocabulary substrate exists") is
  true; the half it still prints ("the user-facing surface itself is NOT_BUILT") is false.
- `real_producer`: `docs/site_semantics/ (6 files, Context Index source)` — half stale. The
  internal substrate half is correct: `docs/site_semantics/` is the source the new public page
  draws from. The half that is missing is the producer of the public page itself: the public-page
  builder and the term-bucket view-model that reads the substrate and renders it.
- `real_consumer`: `scripts/context_index_query.py (internal only)` — stale. The consumer named
  here is the internal-only Context Index tool. The public-page consumer is a different surface:
  a public-glossary page rendered by `scripts/build_public_pages.py` (with `scripts/build_site.py`
  for the nightly full-site render), fed by `lib/glossary.py`, sourced from `docs/site_semantics/`
  and `templates/glossary.html.j2`. Both render paths call the same view-model so the two can
  never hand the template different contexts.
- `next_bounded_child`: `bounded /glossary child over docs/site_semantics (F01/F13 cheap-projection
  batch)` — spent. That child shipped.
- `missing_contract_or_proof`: `user-facing glossary page` — stale. The page exists; what remains
  is an acceptance journey on it.
- `adjudication_notes` (where present on this row): see the Records block in #7014 for the
  F00B-preserved half.

Merge citation: macro #6909, `[MO-BB1] B-F13-1: Public glossary over the existing vocabulary, in
plain language`, MERGED 2026-09-06T06:26:01Z as `2891964bd04e2ced25002274784d4f37a490a62e`.
Producers: `lib/glossary.py` (term-bucket view-model, sourced from `docs/site_semantics/`),
`templates/glossary.html.j2` (the public-page template), `site/glossary.html` (the rendered
output checked into the paired plain-copy lane), `scripts/build_public_pages.py` (public-pages
builder; consumes `lib/glossary.py`), `scripts/build_site.py` (nightly full-site render; consumes
the same view-model), `templates/_public_nav.html.j2` (navlink entry on the public nav), plus the
suite trio `tests/test_glossary.py` (133 lines), `tests/test_glossary_contract.py` (114 lines),
and `tests/test_glossary_letter_rail_js.py` (166 lines). The render gate is
`tests/test_public_chrome.py` (parity-guarded against the hand-authored landing).

#6909's own evidence matrix carried the full dark/light × EN/ZH × 1440/390 receipt at
`mockups/evidence/glossary/`. It is closed-merged, not staged as evidence for any open follow-up;
no production acceptance journey is named by it.

Ancestor claim: `2891964bd04e2ced25002274784d4f37a490a62e` is an ancestor of macro `origin/main`
(`git merge-base --is-ancestor` → true).

Proposed capability_state_c2: BUILT_NOT_PROVEN

Why BUILT_NOT_PROVEN and not further: the public-glossary page is merged to `origin/main`, with
both render paths agreeing on a single view-model, with a navlink entry on the public nav, with
the parity guard (`test_public_chrome.py`), with the term-bucket contract pinned, with the
letter-rail JS pinned, and with the evidence matrix's eight captures for dark/light × EN/ZH ×
1440/390. That is the full BUILT_NOT_PROVEN bar: merged, no DDL of its own to apply (the page
draws from a static docs vocabulary, not from a database), and no production acceptance journey
recorded. PROVEN_LIVE is not available to it either way: nobody has visited the public page in
production with a record of it.

Proposed next_bounded_child: ONE child: a production acceptance journey for the public-glossary
page — one signed-in-or-anonymous reader lands on `/glossary` from the public nav, browses the
letter rail, opens at least one term entry, and reads its plain-language definition in EN and ZH
— recorded in a receipt the records lane can paste, not invented here. The /glossary child this
row's old `next_bounded_child` named already shipped in #6909 (merged 2891964bd) and is named
closed. A child that re-proposes the build is a DEFER pointing at a decision already taken and
is not a child.

Proposed co-text for the same edit:

- `state_delta`: `The public-glossary surface shipped in #6909 (merged 2891964bd):
  lib/glossary.py + templates/glossary.html.j2 + site/glossary.html, with both render paths
  reading the same view-model, a navlink on the public nav, the parity guard at
  tests/test_public_chrome.py, the term-bucket contract test, the letter-rail JS test, and the
  dark/light × EN/ZH × 1440/390 evidence matrix at mockups/evidence/glossary/. State moves off
  PARTIAL; no production acceptance journey recorded.`
- `real_producer`: `lib/glossary.py (term-bucket view-model sourced from docs/site_semantics/)
  + scripts/build_public_pages.py + scripts/build_site.py (both call the same view-model) on
  macro origin/main (merged 2891964bd). docs/site_semantics/ stays the internal substrate the
  view-model reads from.`
- `real_consumer`: `templates/glossary.html.j2 + site/glossary.html (the rendered public page)
  and the public nav (templates/_public_nav.html.j2)`
- `missing_contract_or_proof`: `a production acceptance journey over the live /glossary page
  (the page itself — view-model + dual-render contract + navlink entry + parity guard — is merged)`
- Keep unchanged: `granular_disposition`, `acceptance_test`, `source_rights`, `authority_ceiling`,
  `correction_behavior`, the F00B-preserved half in `adjudication_notes` (if present on this row).

### LEDGER_MOVES #34 — MO-PAID-058 (F13-OPS-LEARNING, UPGRADE_EXISTING_OWNER)

Row: `MO-PAID-058`. Reads on macro `origin/main` today as `capability_state_c2 = PARTIAL`,
`granular_disposition = UPGRADE_EXISTING_OWNER`, `authority_ceiling = operations_only`,
`acceptance_test = a PRO ticket provably routes to a different queue/alert`.

Stale text as it reads on macro `origin/main` (quoted):

- `state_delta`: `UNCHANGED` — stale. Two pull requests in this lane merged since the cell was
  last edited: #6919 (B-F13-2, product specs for MO-PAID-057 and MO-PAID-058, records-only)
  closed the "DEFER — needs a dedicated-channel product decision" half of the next_bounded_child
  by minting the spec; #6959 (B-F13-3, help + dated changelog + tier-routed support) closed the
  runtime half by routing `app/support.py` through `lib.help_directory.route_for_tier` for the
  three plan states (free / paid / unreadable-entitlement). The cell reads as if neither had
  landed.
- `real_producer`: `app/support.py (ticket_ref, rate limiter; _tier_for read but not routed)` —
  stale. The clause "read but not routed" was true when written and is false now: #6959 added
  `route_for_tier` resolution and the `tier_known` boolean, and `app/support.py` now routes every
  ticket through it. `lib/help_directory.py` is the consumer of that resolution.
- `real_consumer`: `operator mailbox via app/mailer.py` — half stale. The consumer that existed
  when this row was last edited is still the consumer today (`app/mailer.py` carries the operator
  mailbox; the `meta.queue` field is the queue label that lands in the receipt without exposing
  the internal `queue` string to JSON). The half that is stale is that the consumer is now
  reached only through the routed leg — a free ticket never reaches the priority queue and a paid
  ticket never reaches the community queue.
- `next_bounded_child`: `DEFER — needs a dedicated-channel product decision` — spent. The
  product decision landed in #6919 (merged 8ec42a8e), which records the choice and the four
  receipt notes; the runtime that implements the decision landed in #6959 (merged 8cf7c412),
  which closes the row's acceptance sentence at the routing half.
- `missing_contract_or_proof`: `tier-differentiated routing/queue/SLA` — partly stale. The
  routing half shipped; the SLA half (response-time promise per tier) is a follow-up named in the
  F13 product spec and is not on `origin/main` today. The accept sentence is split: routing is
  shipped; SLA is owed.
- `adjudication_notes` (where present on this row): the honeypot branch sits above
  `_resolve_user(authorization)` in #6959's final head, so a honeypot hit performs zero outbound
  I/O and the receipt copy is NEUTRAL (EN `Thanks — your message was received.` / ZH `感谢，我们已收到您的留言。`).

Merge citation: macro #6919, `[MO-BB2] B-F13-2: Product specs for MO-PAID-057 (refresh/release
truth) and MO-PAID-058 (help channel decision) — records only`, MERGED 2026-09-06T09:17:50Z as
`8ec42a8e21311cce81cdc2d880326404438485b8`. No product code in this PR — it mints the spec. macro
#6959, `[MO-BB3b] B-F13-3: Help that answers questions plus a dated product changelog, and support
tickets that route by plan`, MERGED 2026-09-08T19:55:59Z as
`8cf7c41240183246a1e9091c5f1f92d4ae815de4`. Producers: `app/support.py` (route-by-tier
resolution, honeypot-neutral receipt), `lib/help_directory.py` (`route_for_tier`, the
view-model `help_page_view_model` shared with `scripts.build_site.build_help_page` and
`scripts.build_public_pages.build`), `templates/help.html.j2` (the help page), `data/product/changelog.yml`
(7 dated entries, newest first, each citing its PR), the suites `tests/test_help_directory.py` and
`tests/test_support_tier_routing.py` (the latter covers free/paid/unreadable-entitlement and the
honeypot neutral contract). The dark/light × EN/ZH × 1440/390 evidence matrix lives at
`mockups/evidence/help_changelog/`.

Ancestor claim: `8ec42a8e21311cce81cdc2d880326404438485b8` and
`8cf7c41240183246a1e9091c5f1f92d4ae815de4` are both ancestors of macro `origin/main`
(`git merge-base --is-ancestor` → true for each).

Proposed capability_state_c2: PARTIAL

Why PARTIAL and not further: the acceptance sentence is "a PRO ticket provably routes to a
different queue/alert". The "different queue" half ships: `app/support.py` resolves `(tier,
tier_known)` and routes every ticket through `lib.help_directory.route_for_tier` — free to the
community queue, paid to the priority queue, unreadable-entitlement to the free queue and the
receipt says so — and the suite `tests/test_support_tier_routing.py` proves each case. The
"alert" half does not: no merged producer fires an alert on tier-routed ticket creation, and
the SLA leg of the F13 spec's promise (response-time per tier) is a follow-up named in the spec
and not on `origin/main` today. Half a sentence is not the sentence — the same rule the F08
slice applied to MO-DELTA-003 — so the row moves off PARTIAL with the spec + runtime halves
named and stops at PARTIAL with the alert/SLA halves named. PROVEN_LIVE is not available to it
either way: nobody has filed a paid ticket against the priority queue with a record of it.

Proposed next_bounded_child: ONE child: ship the SLA half of the F13 spec's tier-routed support
promise — a per-tier response-time bound that the help page surfaces, the priority queue
verifies, and the route receipt prints — and prove the acceptance sentence end to end (one PRO
ticket filed against `app/support.py` lands at the priority queue, with the SLA surface in the
receipt) before this row reads above PARTIAL. The spec already names the four receipt notes and
the four receipt fields; the SLA half is the missing quarter, and it travels with the same
honeypot-neutral contract that #6959 set.

Proposed co-text for the same edit:

- `state_delta`: `EVIDENCE-REFINED: B-F13-2 spec landed in #6919 (merged 8ec42a8e); B-F13-3
  runtime landed in #6959 (merged 8cf7c412). app/support.py now resolves (tier, tier_known) and
  routes every ticket through lib.help_directory.route_for_tier; free→community queue,
  paid→priority queue, unreadable-entitlement→free with the receipt saying so. Honeypot hit is
  neutral above _resolve_user. The SLA half (per-tier response-time) and the alert-on-routed-
  ticket half are owed. State stays PARTIAL.`
- `real_producer`: `app/support.py (route-by-tier resolution, honeypot-neutral receipt) +
  lib/help_directory.py (route_for_tier + help_page_view_model shared by both render paths) +
  tests/test_support_tier_routing.py on macro origin/main (merged 8cf7c412, behind #6919
  merged 8ec42a8e)`
- `real_consumer`: `the operator mailbox (app/mailer.py) via the routed leg — free never
  reaches the priority queue, paid never reaches the community queue; the receipt carries
  routing.plan/promise_en/promise_zh/note_en/note_zh without exposing the internal queue string`
- `missing_contract_or_proof`: `per-tier response-time bound (the SLA half of the F13 spec) +
  a production acceptance journey proving a PRO ticket lands at the priority queue with the SLA
  surface in the receipt; the routing half is shipped`
- Keep unchanged: `granular_disposition`, `acceptance_test`, `source_rights`, `authority_ceiling`,
  `correction_behavior`.

### LEDGER_MOVES #35 — MO-PAID-088 (F13-OPS-LEARNING, UPGRADE_EXISTING_OWNER)

Row: `MO-PAID-088`. Reads on macro `origin/main` today as `capability_state_c2 = PARTIAL`,
`granular_disposition = UPGRADE_EXISTING_OWNER`, `authority_ceiling =
operations_and_explanation_only`, `acceptance_test = an authenticated user reaches /help FAQs
and a dated product changelog`.

Stale text as it reads on macro `origin/main` (quoted):

- `state_delta`: `EVIDENCE-REFINED: /learn SEO hub (templates/seo_learn_index.html.j2 via
  build_free_content.py:1201) and an economic-release calendar widget exist but are NOT
  in-product help/FAQ/changelog; state unchanged` — half stale. The negative half is still true:
  the /learn SEO hub is a marketing surface (a static `seo_learn_index.html.j2` produced by
  `scripts/build_free_content.py`), and the economic-release calendar widget is the existing
  calendar component, neither of which is the in-product help/FAQ/changelog the row asks for.
  The half that is stale is the "state unchanged" half: B-F13-3 landed on 2026-09-08 and the
  in-product help/FAQ/changelog surfaces it shipped are the surfaces this row's acceptance
  sentence names.
- `real_producer`: `templates/methodology.html.j2 + app/support.py (tickets) + seo_learn_index
  (marketing surface)` — half stale. `templates/methodology.html.j2` still exists and is still
  a methodology surface; `app/support.py` still handles tickets; `seo_learn_index` is still a
  marketing surface and is still not this row's producer. The half that is missing is the new
  producer: `templates/help.html.j2` (the help page that renders `lib/help_directory.help_page_view_model`)
  + `lib/help_directory.py` (`HELP_ANSWERS`, 14 question-shaped bilingual entries; `help_page_view_model`
  shared with both render paths) + `data/product/changelog.yml` (7 dated entries, newest first,
  each citing its merged PR) + `scripts/build_public_pages.py` (public-pages path) +
  `scripts/build_site.py` (nightly full-site path).
- `real_consumer`: `public SEO pages + support mailbox` — half stale. The public SEO pages the
  row named are still consumers of `seo_learn_index`, not of the help surface. The new consumer
  is the help page itself (`templates/help.html.j2` rendering on `/help`) and the support
  mailbox, which the help page renders alongside the answers + changelog + support plans.
- `next_bounded_child`: `bounded /help + changelog child (F01/F13 cheap-projection batch; 1-2
  templates)` — spent. That child shipped.
- `missing_contract_or_proof`: `/help FAQ template + genuine product changelog surface` — half
  stale. The `/help` FAQ template shipped in #6959 (merged 8cf7c412); the changelog surface
  shipped alongside it (the dated rail with 7 PR-citing entries). What remains is an acceptance
  journey: one authenticated reader reaches `/help`, reads the FAQ, and reads the dated rail.

Merge citation: macro #6959, `[MO-BB3b] B-F13-3: Help that answers questions plus a dated
product changelog, and support tickets that route by plan`, MERGED 2026-09-08T19:55:59Z as
`8cf7c41240183246a1e9091c5f1f92d4ae815de4`. Producers: `templates/help.html.j2`,
`lib/help_directory.py` (`HELP_ANSWERS`, `route_for_tier`, `help_page_view_model`),
`data/product/changelog.yml`, `scripts/build_public_pages.py`, `scripts/build_site.py`,
`tests/test_help_directory.py`, `tests/test_support_tier_routing.py`. The dark/light × EN/ZH ×
1440/390 evidence matrix lives at `mockups/evidence/help_changelog/` (8/8 captures).

Named as OPEN, and therefore cited as no move's evidence: macro #7133, `[MO-B F13-4] Changelog:
plain-word entries for every user-facing change since 2026-09-06 (MO-PAID-088 follow-up)`,
DRAFT at this read, which is the changelog-refresh follow-up that the row's stale cell implicitly
names; it does not change the in-product help/FAQ surface and it does not move this row's state
word further. Its draft state is the reason this move stops at PARTIAL — a follow-up that adds
changelog entries can land without a re-evaluation of the row.

Ancestor claim: `8cf7c41240183246a1e9091c5f1f92d4ae815de4` is an ancestor of macro `origin/main`
(`git merge-base --is-ancestor` → true).

Proposed capability_state_c2: PARTIAL

Why PARTIAL and not further: the row's acceptance sentence is "an authenticated user reaches
/help FAQs and a dated product changelog". The help/FAQ half ships: the help page renders the
view-model composed of entries + categories + directory_state + answers + answers_state +
changelog + support plans, both render paths call the same view-model, and the suites pin the
contract. The dated-product-changelog half also ships in code: `data/product/changelog.yml` is
the source, the help page renders the rail, the schema is `mastermind.product_changelog.v1`, and
the entries are dated newest first with each entry citing its PR. What is missing is the
acceptance journey: nobody has reached `/help` as an authenticated user and read the FAQ and
the dated rail with a record of it. Half a sentence is not the sentence — so the row moves off
PARTIAL with the in-product help/FAQ/changelog halves named and stops at PARTIAL with the
acceptance-journey half named. PROVEN_LIVE is not available to it either way.

Proposed next_bounded_child: ONE child: a routed-page acceptance journey for `/help` — one
authenticated reader lands at the help page from the public nav (or a deep link), opens at
least one FAQ entry, reads its plain-language answer in EN and ZH, and reads the dated
changelog rail with its newest-first entries — recorded in a receipt the records lane can paste,
not invented here. The help/FAQ + changelog child this row's old `next_bounded_child` named
already shipped in #6959 (merged 8cf7c412) and is named closed. A child that re-proposes the
build is a DEFER pointing at a decision already taken and is not a child.

Proposed co-text for the same edit:

- `state_delta`: `EVIDENCE-REFINED: B-F13-3 landed in #6959 (merged 8cf7c412). templates/help.html.j2
  renders lib/help_directory.help_page_view_model (entries + categories + directory_state +
  answers + answers_state + changelog + support plans). HELP_ANSWERS has 14 question-shaped
  bilingual entries; data/product/changelog.yml is dated newest-first with 7 PR-citing entries.
  Both render paths (scripts/build_public_pages.py and scripts/build_site.py) call the same
  view-model. State moves off PARTIAL with the help/FAQ/changelog halves shipped; the routed-page
  acceptance journey is owed.`
- `real_producer`: `lib/help_directory.py (HELP_ANSWERS + help_page_view_model + route_for_tier)
  + templates/help.html.j2 + data/product/changelog.yml on macro origin/main (merged 8cf7c412).
  The seo_learn_index marketing surface is still not this row's producer.`
- `real_consumer`: `the /help page (templates/help.html.j2) renders answers + changelog +
  support plans for an authenticated reader; the support mailbox (app/mailer.py) is reached
  through the routed leg`
- `missing_contract_or_proof`: `a routed-page acceptance journey over the live /help page (the
  in-product help/FAQ/changelog surface itself — view-model + dual-render contract + dated rail
  + 14 bilingual answers — is merged)`
- Keep unchanged: `granular_disposition`, `acceptance_test`, `source_rights`, `authority_ceiling`,
  `correction_behavior`.

## Records

This packet proposes, the records lane applies. Moves proposed, not applied; #7014 owns the CSV.

Intended row attributions, written here because this PR writes nothing to the ledger:

- LEDGER_MOVE #32 — `MO-DELTA-007`: proposed `capability_state_c2` `SPEC_ONLY`, proposed
  `next_bounded_child` rewritten to name the runtime half the spec expects.
- LEDGER_MOVE #33 — `MO-DELTA-011`: proposed `capability_state_c2` `BUILT_NOT_PROVEN`, proposed
  `next_bounded_child` rewritten to the routed-page acceptance journey (the build child is
  named spent).
- LEDGER_MOVE #34 — `MO-PAID-058`: proposed `capability_state_c2` stays `PARTIAL` (text move),
  proposed `next_bounded_child` rewritten to the SLA half of the F13 spec's tier-routed support
  promise (the routing half is named shipped).
- LEDGER_MOVE #35 — `MO-PAID-088`: proposed `capability_state_c2` stays `PARTIAL` (text move),
  proposed `next_bounded_child` rewritten to the routed-page acceptance journey on `/help` (the
  in-product help/FAQ/changelog child is named spent).

PROVEN_LIVE is never set on any row. The strongest evidence this seat holds is merged code plus
an applied DDL with a seat receipt — never two people exercising the surface in production
with a record of it.

🤖 Generated with [Claude Code](https://claude.com/claude-code)