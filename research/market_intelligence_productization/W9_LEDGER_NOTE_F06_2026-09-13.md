# W9 ledger note — the F06 slice of LEDGER_MOVES (#1–#3)

**Date:** 2026-09-13
**Packet:** `W9B_REC_F06` (Meta-CEO B ruling, 2026-09-13 16:02Z, W9 planner)
**Status:** `RECORDS_ONLY / MOVES PROPOSED, NOT APPLIED`
**Lane:** `claude/mo-b-rec-f06-note-20260913`
**Coordinating workstream:** `WS:MARKET-OS` (F06 lane)
**Ledger rows named:** `MO-PAID-020`, `MO-PAID-021`, `MO-DELTA-002`
**Ledger read at:** `research/market_intelligence_productization/MARKET_ONTOLOGY_F00C_GRANULAR_CLOSURE_LEDGER_2026-09-02.csv`,
lines 53–55, on `origin/main` at `321da62b3b0163b6ab5a287fb9847a13ed7f3ed2`
(blob `8bbb8d78c34c40ef1b22bdf5477de87f411319f5`, file sha256
`078d1f6dc29b49aba2eb61c7ff9208b871e5c3df1928288ca75ba81329f33dd5`)
**Who owns the CSV:** pull request `#7014` (the records lane). This note writes no row.
**Capability delta of this document:** `NONE`

## 0. What this note is, and what it is not

This is the F06 slice of `LEDGER_MOVES`: three proposed ledger moves, written so a
records lane can paste them without re-deriving anything. Each move names one row of the
granular closure ledger, quotes the text that is now stale, cites the merged pull request
that made it stale, claims ancestry for that merge against the commit this note was read
at, and proposes exactly two column values — `capability_state_c2` and
`next_bounded_child`.

It is not an edit. **The moves are proposed, not applied.** Nothing in this packet writes
to the ledger CSV, to any workstream record, or to any product surface. `#7014` owns the
CSV; the row attributions this note intends are restated in the pull request body under
"Records" so the owner can take them or leave them in one place. No authority ceiling, no
source-rights entry, no family assignment and no owner path changes here, and no move in
this note asks for one.

## 1. Provenance of these three moves

The planner's `orch/w8/LEDGER_MOVES.md` is not present in this repository: `orch/` is not
a tracked top-level directory on `origin/main`, and no file named `LEDGER_MOVES` exists in
any tree of this checkout. That is recorded here rather than papered over, because it
changes what "copy the line" can mean. The three moves below were therefore re-derived
from primary evidence in this repository and from the merged pull requests it names:

1. the three ledger rows as they read on `origin/main` at the commit named above;
2. the acceptance sentence already written in each row, applied literally — the sentence
   is the test, not a paraphrase of it and not a pull request's title;
3. the merged code, fixtures, tests and evidence receipts that exist on `origin/main`
   today, each cited by path and line so a reader can check it without this note;
4. the open pull requests that carry the residual work each row still owes, cited as
   in-flight and never as evidence of anything merged.

Every merge citation below carries an ancestor claim, and every ancestor claim was checked
with `git merge-base --is-ancestor <merge commit> origin/main` against
`321da62b3b0163b6ab5a287fb9847a13ed7f3ed2`, which exits 0 for all four commits cited
(`67ad703b`, `961a9c3d`, `3bbca537`, `9c6e1999`). Section 9 lists the commands.

## 2. What the state words mean here

The vocabulary is the ledger's own and nothing else: `NOT_BUILT`, `PARTIAL`,
`BUILT_NOT_PROVEN`, `SPEC_ONLY`, `PROVEN_LIVE`.

`BUILT_NOT_PROVEN` means the capability is merged to this repository's default branch and,
where it needed a rendered artifact, the render path and its tests are merged with it. It
says nothing about anyone having used it. It is the strongest word any move in this note
proposes, and it is deliberately weaker than the word the ledger reserves for a production
readback.

**No move in this note proposes `PROVEN_LIVE`.** That word needs a readback of the served
production artifact, and the only such receipt this repository holds for the F06 lane is
the B1A one for a single issuer (`agentos/handoffs/MARKET-OS-2026-08-26-b1a-proven-live.md`,
served `/stocks/AAPL.html` byte-identical to disk at sha256
`8154964e0ed4b886eb3d59e075d094496f052aa8d785e239d57639e5d2a8338f`). The served stockdata
tree is gitignored, so this repository holds no equivalent receipt for the second issuer,
and a merged test is not a production readback. When a nightly readback of the second
issuer's served page and object is recorded, that row can move again; nothing here
anticipates it.

`NOT_BUILT` is proposed for one row below, and it is proposed as a *correction of the row's
reasons*, not as a claim that nothing happened. A row can be honestly `NOT_BUILT` while the
dependencies it named as missing have since merged; what changes is the text, not the word.

## 3. LEDGER_MOVE #1 — `MO-PAID-020`

- row_id: `MO-PAID-020` (family `F06-SECURITY-RESEARCH`, disposition
  `UPGRADE_EXISTING_OWNER`, ledger line 54)
- quoted stale text (verbatim from the row as read at the commit named above):
  - `capability_state_c2`: `PARTIAL`
  - `state_delta`: "REFRESHED + OWNER-CORRECTION: #6529 merged, but WS:STOCK-IDENTITY is a
    different program (behavioral fingerprint/expert routing); the actual blocker
    NO_GENERAL_NAMESPACE_RENDERER + CIK_LEG_UNOWNED_ACCESS lives INSIDE WS:MARKET-OS B1A
    records and is unclaimed there"
  - `real_producer`: "scripts/build_stock_library.py -> engine/security_state.py::compile_security_state
    (deterministic, zero-IO, AAPL-instance-scoped)"
  - `real_consumer`: "/stockdata/AAPL.json + /stocks/AAPL.html (B1A PROVEN_LIVE for AAPL
    only; 2 of 3014 stockdata files carry the key)"
  - `missing_contract_or_proof`: "general issuer journey blocked on the
    ListingAlias->ListingKey renderer + issuer_cik reader exposure (both WS:MARKET-OS-owned
    repairs)"
  - `acceptance_test`: "a second issuer gets a real security_state.v1 object + rendered
    page byte-verified like AAPL"
  - `next_bounded_child`: "RULED: a single bounded renderer/CIK-access repair may be
    admitted only after a fresh collision census; it remains CAPACITY_SELECTABLE /
    WAITING_CAPACITY (not this session's to self-assign); any owner-path mutation returns
    OWNER_BOUNDARY_REQUIRED"
- why the text is stale: the row still describes a single-issuer world. Two of its own
  claims are now false on `origin/main`. The producer is no longer AAPL-instance-scoped:
  `engine/security_state.py:81` reads `SECURITY_STATE_TICKERS = (PINNED_TICKER, "MSFT")`,
  `engine/security_state.py:152` defines `MSFT_SUBJECT`, and
  `scripts/build_stock_library.py:4578` carries the comment "Market OS B1A:
  security_state.v1 (frozen AAPL + MSFT allowlist)". The named blocker is no longer wholly
  unclaimed: the `issuer_cik` reader exposure shipped as an owner-backed read through
  `lib/dataos/identity.py`, and the compiled object's own disclosure for that leg is now
  `CIK_LEG_OWNER_BACKED_CURRENT_ONLY` rather than an unowned access
  (`tests/fixtures/security_state/golden_msft_expected_output.json`,
  `identity_proof.disclosures`).
- merge citation: `#6920` — "[MO-BB2b] B-F06-1: Second issuer end to end: owner-routed
  ListingAlias->ListingKey resolution + issuer_cik reader", merged 2026-09-11T18:11:14Z as
  `67ad703bd24d637ed42c5511947c82f1c1cb0c3a`. Producer and proof paths on `origin/main`
  from that merge: `engine/security_state.py`, `lib/dataos/identity.py`,
  `scripts/build_stock_library.py`, `scripts/build_ticker_pages.py`,
  `scripts/security_state_producer.py`, `templates/ticker.html.j2`,
  `tests/fixtures/security_state/golden_msft_input.json`,
  `tests/fixtures/security_state/golden_msft_expected_output.json`,
  `tests/test_security_state_contract.py`, `tests/test_security_state_view_model.py`,
  `mockups/evidence/security_state/` (eight crops, `EVIDENCE.yml`,
  `manifest.json` generated 2026-09-10T23:36:32Z).
- ancestor claim: `67ad703bd24d637ed42c5511947c82f1c1cb0c3a` is an ancestor of `origin/main`
  at `321da62b3b0163b6ab5a287fb9847a13ed7f3ed2` (`git merge-base --is-ancestor` exits 0).
- acceptance sentence, applied literally: **met.** A second issuer (MSFT) gets a real
  `security_state.v1` object — `identity_proof.state` `PROVEN` via `owner_backed_chain.v1`
  with nine legs, nine equalities and zero refusals, `security_id` `SEC:US-XNAS-MSFT`,
  `issuer_id` `ISS:US-XNAS-MSFT`, `listing_key` `US-XNAS-MSFT` — and it is byte-verified
  exactly the way AAPL is: `tests/test_security_state_contract.py:1761`
  (`test_golden_expected_output_is_byte_exact`) is parametrized over the AAPL and MSFT
  golden pairs and asserts whole-object equality plus an equal `content_sha256`. The
  rendered page half is covered by
  `tests/test_security_state_view_model.py:808`
  (`test_view_model_renders_the_msft_state_with_plain_words`), which renders
  `templates/ticker.html.j2` from the golden MSFT object and asserts the section is present
  with no raw enum code in the markup, and by
  `tests/test_security_state_view_model.py:1852`
  (`test_identity_checks_panel_has_no_machine_text_on_golden_msft_and_m1`).
- proposed capability_state_c2: `BUILT_NOT_PROVEN`
- why not `PROVEN_LIVE`: see section 2. No served-artifact readback for the second issuer
  exists in this repository, and the B1A receipt names AAPL alone.
- why not `PARTIAL`: the row's own acceptance sentence is met on the default branch. What
  remains is a *different* sentence — universe expansion beyond the frozen allowlist — and
  that belongs in `missing_contract_or_proof` and `next_bounded_child`, not in a state word
  that would keep a shipped capability reading as half-done.
- residual, named and not hidden: the allowlist is frozen at two issuers. The expansion
  gate `NO_GENERAL_NAMESPACE_RENDERER` survives as a repair, and the fresh collision census
  the row's own ruling demanded is in flight as `#7122` (open, head
  `536bc2c4fd0cf663dac25fae98bdab086c6090d1`), which reports
  `no_identity_row=1` and `resolvable_outside_allowlist=242` over a `data/stocks` universe
  and admits exactly one bounded repair. Nothing from `#7122` is counted as merged here.
- proposed next_bounded_child: "land the in-flight collision census and its one admitted
  bounded repair (#7122), then carry the owner-routed ListingAlias->ListingKey renderer past
  the frozen two-issuer allowlist so a third issuer compiles and renders byte-verified with
  no allowlist entry; universe expansion stays BLOCKED under
  NO_GENERAL_NAMESPACE_RENDERER until it does. Still CAPACITY_SELECTABLE /
  WAITING_CAPACITY; any owner-path mutation returns OWNER_BOUNDARY_REQUIRED."

## 4. LEDGER_MOVE #2 — `MO-PAID-021`

- row_id: `MO-PAID-021` (family `F06-SECURITY-RESEARCH`, disposition
  `UPGRADE_EXISTING_OWNER`, ledger line 55)
- quoted stale text (verbatim):
  - `capability_state_c2`: `PARTIAL`
  - `state_delta`: "UNCHANGED"
  - `real_producer`: "NONE for B1B-B6 (todo, depends on B1A + renderer repair)"
  - `real_consumer`: "NONE yet"
  - `missing_contract_or_proof`: "entire B1B-B6 chart-first cockpit wave"
  - `acceptance_test`: "B1B ships a cockpit over frozen security_state.v1 for a second
    issuer"
  - `next_bounded_child`: "DEFER — dependency MO-PAID-020's renderer repair, then a
    separate Sol commission for B1B-B6"
  - `authority_ceiling`: "display_only; gated behind identity-renderer repair"
- why the text is stale: `real_producer` reads `NONE`, and a producer now exists on
  `origin/main`. The B1B cockpit is rendered by `templates/ticker.html.j2` — panel 1
  "Overview" at `templates/ticker.html.j2:1109` and panel 8 "Owner & model receipts" at
  `templates/ticker.html.j2:1197` — and baked by `scripts/build_ticker_pages.py`. The row's
  defer reason is spent too: the `MO-PAID-020` renderer repair it waited on merged in
  `#6920` (move #1 above), and the freeze it needed was already merged in `#6966`.
- merge citation: `#7007` — "[MO-BB2b] B-F06-3: Second-issuer cockpit per the F06 scope
  freeze — eight panels over the shipped security-state view model", merged
  2026-09-12T10:50:21Z as `961a9c3d270a4642104ec32c39c7faf1656b8f2b`. Paths on
  `origin/main` from that merge: `scripts/build_ticker_pages.py`,
  `templates/ticker.html.j2`, `tests/test_security_state_view_model.py`, and
  `mockups/evidence/f06_second_issuer_cockpit/` (eight crops, `EVIDENCE.yml`,
  `manifest.json` generated 2026-09-11T00:31:27Z, `capturedAtHead`
  `36ea10b2f1d4dd526a87bd11988ce33ba4a971db`, axes dark and light × `en` and `zh` ×
  desktop 1440 and mobile 390). Scope citation behind it: `#6966` — "[MO-BB4] B-F06-2: F06
  scope freeze", merged 2026-09-10T03:54:29Z as
  `9c6e1999bb9a9a6e904a98ea617cade16594b404`, which landed
  `research/market_intelligence_productization/MARKET_ONTOLOGY_F06_SCREENER_AND_COCKPIT_SCOPE_2026-09-06.md`
  and its eight-panel display-only map.
- ancestor claim: `961a9c3d270a4642104ec32c39c7faf1656b8f2b` and
  `9c6e1999bb9a9a6e904a98ea617cade16594b404` are both ancestors of `origin/main` at
  `321da62b3b0163b6ab5a287fb9847a13ed7f3ed2` (`git merge-base --is-ancestor` exits 0 for
  each).
- acceptance sentence, applied literally: **met.** B1B ships a cockpit over the frozen
  `security_state.v1` object for a second issuer. The pinned heading list is
  `_B1B_HEADINGS_EN` at `tests/test_security_state_view_model.py:2368` — Overview, Where it
  stands, What changed, Opportunity context, What could go wrong, What to watch next,
  Evidence, Owner & model receipts — and
  `tests/test_security_state_view_model.py:2536`
  (`test_ticker_page_renders_all_eight_b1b_panel_headings_for_msft`) renders the golden MSFT
  object and asserts the page's visible headings equal that list exactly. The ceiling holds
  in the same suite: `tests/test_security_state_view_model.py:2629`
  (`test_no_new_panel_reads_a_rank_score_size_or_gate_field`), and the shipped object's own
  `authority` block reads `class` `context_only`, `display_only` true, and `can_rank`,
  `can_gate`, `can_size`, `can_originate_signal`, `can_execute` all false.
- proposed capability_state_c2: `BUILT_NOT_PROVEN`
- why not `PROVEN_LIVE`: the crops are a component-harness capture at a named code head,
  not a readback of a served production page for the second issuer. Section 2 applies.
- residual, named and not hidden: B1B is one slice of the `B1B-B6` child in
  `agentos/workstreams/WS-MARKET-OS.md` (id `B1B-B6`, "Terminal/Desk projection and
  chart-first security cockpit over frozen security_state.v1"). B2 onward are untouched,
  and the C, D, E and F children that depend on `B1B-B6` are no closer than they were
  except by this one slice.
- proposed next_bounded_child: "the remainder of the B1B-B6 child — B2 onward, the
  Terminal/Desk projection and the chart-first cockpit over the same frozen
  security_state.v1 object. It needs its own commission, it inherits the display_only
  ceiling, and it may not add a rank, a score, a size or a gate."

## 5. LEDGER_MOVE #3 — `MO-DELTA-002`

- row_id: `MO-DELTA-002` (family `F06-SECURITY-RESEARCH`, disposition `NEW_BOUNDED_BUILD`,
  ledger line 53)
- quoted stale text (verbatim):
  - `capability_state_c2`: `NOT_BUILT`
  - `state_delta`: "UNCHANGED (only quad/options/confluence screeners exist — not research
    screeners)"
  - `real_producer`: "NONE"
  - `real_consumer`: "NONE"
  - `missing_contract_or_proof`: "filter-universe research-screener workflow
    (theme/catalyst/exposure/valuation posture)"
  - `acceptance_test`: "a research-priority-only screener ships (never a trade ranker per
    ceiling)"
  - `next_bounded_child`: "DEFER — dependency F07 valuation inputs + GMI theme owners"
  - `source_rights`: "depends on F07 valuation-posture inputs (unbuilt) + GMI theme owners"
  - `authority_ceiling`: "research_priority_only; may not become trade ranker without
    promotion"
- why the text is stale — and why the state word is not: the parenthetical "(unbuilt)"
  attached to the F07 valuation-posture inputs is false on `origin/main`.
  `engine/valuation_scenario.py` is present, together with `engine/valuation.py` and
  `engine/valuation_assumptions.py`. The `source_rights` and `next_bounded_child` text both
  inherit that false claim, so both need correcting. The state word does not: nothing of the
  research screener itself is merged. `origin/main` carries no `engine/research_screener.py`,
  no `scripts/build_research_screener.py`, no `templates/research_screener.html.j2`, no
  `site/research_screener.html` and no `tests/test_research_screener.py` — a listing of the
  default branch returns zero paths matching `research_screener`. The screener-shaped things
  that do exist are the ones the row already names as not-research-screeners:
  `engine/quad_screener.py`, `engine/seasonality/screener.py`,
  `scripts/build_confluence_screener.py`, `scripts/build_options_screener.py`,
  `scripts/fetch_finviz_screener.py`, `templates/confluence_screener.html.j2`,
  `templates/options_screener.html.j2`. So the first half of `state_delta` stays true and
  the row's own acceptance sentence stays unmet.
- merge citation: `#6905` — "[MO-BB1] B-F07-1: Valuation under different assumptions (V1):
  one issuer, reported SEC fundamentals, plain language", merged 2026-09-12T17:07:09Z as
  `3bbca5375cbe7fccd13a4f02f3d2e6d3dba3eee2`. This one is cited for the DEPENDENCY only,
  never for the row's own capability: it is where the valuation-posture input this row was
  waiting on came from. Scope citation: `#6966`, merged 2026-09-10T03:54:29Z as
  `9c6e1999bb9a9a6e904a98ea617cade16594b404`, whose freeze document defines the four filter
  families and the binding no-ranker ceiling, and names `KILL-CAUSAL-DAG-ALPHA` and
  `KILL-LLM-CONFIDENCE` as binding (`tests/test_market_ontology_f06_scope.py:66`).
- ancestor claim: `3bbca5375cbe7fccd13a4f02f3d2e6d3dba3eee2` and
  `9c6e1999bb9a9a6e904a98ea617cade16594b404` are both ancestors of `origin/main` at
  `321da62b3b0163b6ab5a287fb9847a13ed7f3ed2` (`git merge-base --is-ancestor` exits 0 for
  each).
- acceptance sentence, applied literally: **not met.** No research-priority-only screener is
  on the default branch, so no state word above `NOT_BUILT` is available. The build is in
  flight as `#7102` (open, draft, head
  `3846fe6675c24be6708681ce2629511b56d92ee7`), whose own body records four plain-word
  lenses with the Theme lens shipped disabled behind a visible bilingual hint ("Theme lens
  isn't available yet" / "主题视角尚未提供。"). In-flight work is cited as in-flight; it is
  counted as nothing.
- proposed capability_state_c2: `NOT_BUILT`
- why not `PARTIAL`: `PARTIAL` would say part of the row's own capability shipped. What
  shipped is an *input* owned by another row's family (F07 valuation posture) and a *scope
  freeze*, which is a record, not a capability. Counting a dependency as partial progress on
  the dependent row is how a ledger starts reporting work it does not have.
- residual, named and not hidden: the GMI theme owner is still unbuilt, and it is the only
  one of the row's two named dependencies that remains. The theme lens shipping disabled is
  the honest shape of that gap on a page, and it does not close the row.
- proposed next_bounded_child: "land the in-flight research screener v1 (#7102) — four
  plain-word lenses over owner-attributed signal, Theme visibly disabled until a GMI theme
  owner exists, default order alphabetical, never a rank, a score, a size or a gate. After
  it merges, the only remaining dependency this row names is the GMI theme owner, and that
  becomes the next child."

## 6. Paste-ready block for the records lane

The three moves in one place, in the order the ledger rows appear. Column values only; the
prose above is the argument for them.

```text
LEDGER_MOVES #1
  row_id: MO-PAID-020
  merge_citation: #6920 merged 2026-09-11T18:11:14Z as 67ad703bd24d637ed42c5511947c82f1c1cb0c3a
  ancestor_claim: 67ad703bd24d637ed42c5511947c82f1c1cb0c3a is an ancestor of origin/main at 321da62b3b0163b6ab5a287fb9847a13ed7f3ed2
  proposed_capability_state_c2: BUILT_NOT_PROVEN
  proposed_next_bounded_child: land the in-flight collision census and its one admitted bounded repair (#7122), then carry the owner-routed ListingAlias->ListingKey renderer past the frozen two-issuer allowlist so a third issuer compiles and renders byte-verified with no allowlist entry; universe expansion stays BLOCKED under NO_GENERAL_NAMESPACE_RENDERER until it does. Still CAPACITY_SELECTABLE / WAITING_CAPACITY; any owner-path mutation returns OWNER_BOUNDARY_REQUIRED.

LEDGER_MOVES #2
  row_id: MO-PAID-021
  merge_citation: #7007 merged 2026-09-12T10:50:21Z as 961a9c3d270a4642104ec32c39c7faf1656b8f2b (scope freeze #6966 merged 2026-09-10T03:54:29Z as 9c6e1999bb9a9a6e904a98ea617cade16594b404)
  ancestor_claim: 961a9c3d270a4642104ec32c39c7faf1656b8f2b and 9c6e1999bb9a9a6e904a98ea617cade16594b404 are ancestors of origin/main at 321da62b3b0163b6ab5a287fb9847a13ed7f3ed2
  proposed_capability_state_c2: BUILT_NOT_PROVEN
  proposed_next_bounded_child: the remainder of the B1B-B6 child — B2 onward, the Terminal/Desk projection and the chart-first cockpit over the same frozen security_state.v1 object. It needs its own commission, it inherits the display_only ceiling, and it may not add a rank, a score, a size or a gate.

LEDGER_MOVES #3
  row_id: MO-DELTA-002
  merge_citation: dependency only — #6905 merged 2026-09-12T17:07:09Z as 3bbca5375cbe7fccd13a4f02f3d2e6d3dba3eee2 (scope freeze #6966 as 9c6e1999bb9a9a6e904a98ea617cade16594b404); the row's own capability is unmerged, in flight as #7102 head 3846fe6675c24be6708681ce2629511b56d92ee7
  ancestor_claim: 3bbca5375cbe7fccd13a4f02f3d2e6d3dba3eee2 and 9c6e1999bb9a9a6e904a98ea617cade16594b404 are ancestors of origin/main at 321da62b3b0163b6ab5a287fb9847a13ed7f3ed2
  proposed_capability_state_c2: NOT_BUILT
  proposed_next_bounded_child: land the in-flight research screener v1 (#7102) — four plain-word lenses over owner-attributed signal, Theme visibly disabled until a GMI theme owner exists, default order alphabetical, never a rank, a score, a size or a gate. After it merges, the only remaining dependency this row names is the GMI theme owner, and that becomes the next child.
```

## 7. Stale records this note names and does not edit

Naming them is the point; editing them belongs to the lane that owns each file.

- `agentos/workstreams/WS-MARKET-OS.md` still carries child `B1B-B6` as `status: todo` with
  the next action "Separate commission after Sol accepts B1A; B1B requires the frozen
  security_state.v1 surface plus the identity-renderer repair before any second issuer".
  B1B has shipped and both of its preconditions merged, so that record is stale in the same
  way the ledger rows are.
- The same workstream record still says "universe expansion beyond ("AAPL",) is still
  BLOCKED under NO_GENERAL_NAMESPACE_RENDERER" and "only 2 of 3014 stockdata files carry the
  key (AAPL.json plus the AAPL row of index.json)". The allowlist now names two issuers, so
  the count in that sentence is a pre-`#6920` fact. The gate itself is still open; only the
  numbers around it moved.
- `MO-PAID-020`'s `real_consumer` and `MO-PAID-021`'s `real_consumer` are stale for the same
  reason (`/stockdata/AAPL.json` alone; `NONE yet`). Neither is proposed here. The records
  lane that owns the CSV should decide whether a consumer column may cite a rendered surface
  with no production readback behind it, and this note does not pre-empt that decision.
- `agentos/decisions/DEC-MARKET-OS-B1A-IDENTITY-GATE-OWNER-BACKED-CHAIN.md` names
  `CIK_LEG_UNOWNED_ACCESS` as a repair item. The compiled object now discloses
  `CIK_LEG_OWNER_BACKED_CURRENT_ONLY` for that leg instead. A decision record is superseded,
  never edited, so this belongs to a `DEC-*` successor if the seat wants one.

## 8. What this note deliberately does not do

- It writes no ledger row. The CSV is untouched by this packet and `#7014` owns it.
- It applies no move. Everything above is a proposal with an argument attached.
- It proposes no `PROVEN_LIVE` and no authority widening. No ceiling, source right, family
  or owner path changes, and no move asks for a promotion.
- It counts nothing from an open pull request as shipped. `#7122` and `#7102` are cited as
  in-flight residuals only.
- It does not touch `templates/_navlinks.html.j2`, any template, any stylesheet, any page,
  any pixel, anything under `data/` or `site/`, and any other repository's tree.
- It records no secret, no project reference, no personal access token and no key of any
  kind, and the suite that pins this note asserts that stays true.

## 9. How to re-verify every claim above

All commands are read-only and run from a checkout of this repository.

```bash
# the ledger text quoted in sections 3-5, at the commit this note was read at
git show 321da62b3b0163b6ab5a287fb9847a13ed7f3ed2:research/market_intelligence_productization/MARKET_ONTOLOGY_F00C_GRANULAR_CLOSURE_LEDGER_2026-09-02.csv | sed -n '53,55p'

# the four ancestor claims
for c in 67ad703bd24d637ed42c5511947c82f1c1cb0c3a \
         961a9c3d270a4642104ec32c39c7faf1656b8f2b \
         3bbca5375cbe7fccd13a4f02f3d2e6d3dba3eee2 \
         9c6e1999bb9a9a6e904a98ea617cade16594b404; do
  git merge-base --is-ancestor "$c" 321da62b3b0163b6ab5a287fb9847a13ed7f3ed2 && echo "ancestor: $c"
done

# the two-issuer allowlist and its byte-exact golden proof
git show origin/main:engine/security_state.py | sed -n '81p;152p'
git show origin/main:tests/test_security_state_contract.py | sed -n '1755,1768p'

# the eight B1B panel headings pinned for the second issuer
git show origin/main:tests/test_security_state_view_model.py | sed -n '2368,2378p;2536,2544p'

# the absence that keeps move #3 at NOT_BUILT
git ls-tree -r --name-only origin/main | grep -c research_screener   # prints 0
git ls-tree -r --name-only origin/main | grep -E 'screener' | grep -vE '^(data|site|mockups|ux-evidence|research)/'

# the pin test for this note
python3 -m pytest tests/test_w9_ledger_note_f06.py -q
```
