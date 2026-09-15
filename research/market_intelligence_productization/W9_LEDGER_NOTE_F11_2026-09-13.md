# W9 ledger note — F11 slice (LEDGER_MOVES #11, #20, #21, #22, #23)

Packet W9B_REC_F11, drafted 2026-09-13 by the Meta-CEO B seat under the W9 planner
ruling of 2026-09-13 16:02Z. Records only: no product code, no CSV edit, no
authority promotion. Every move proposed below is a RECOMMENDED next state for
the F11 lane; it is pasted, never applied, and the F00C CSV at
`research/market_intelligence_productization/MARKET_ONTOLOGY_F00C_GRANULAR_CLOSURE_LEDGER_2026-09-02.csv`
remains the source of truth until #7014 (B-REC-B5-X) lands and a records lane
under the operator picks it up. PR #7014 owns the CSV; this PR owns the prose
and a pin test.

## Why this note exists

The F11 lane (research workspace, human-research tier) has been frozen on five
ledger rows for the duration of Wave 4 and Wave 5. The Wave 4 reconciliation
packet (B-REC-B5-1, merged at macro#7003 22aa5ec8 on 2026-09-12 at 55ba45bf)
moved MO-PAID-053 to `BUILT_NOT_PROVEN` and named MO-PAID-046's vocabulary gap
as the residual child. It did not touch the four F11 rows that this note
proposes to advance. The W9 planner asks for the next slice of
`orch/w8/LEDGER_MOVES.md` as a research note the records stack can paste when
#7014 lands; this file is that slice, scoped to the five F11 rows the records
stack will read first.

## The vocabulary the rows already carry

The column already accepts a fixed set of five state values, frozen by
MARKET_ONTOLOGY_F00C_GRANULAR_CLOSURE_LEDGER_2026-09-02.csv column header:
`NOT_BUILT`, `PARTIAL`, `BUILT_NOT_PROVEN`, `SPEC_ONLY`, `PROVEN_LIVE`. Every
move proposed below stays inside that set. `PROVEN_LIVE` is never set in this
note: no row carries a production readback, and the strongest evidence in hand
for any row is either a Terminal merge sha or a frozen contract, neither of
which is a production readback of two people doing the thing the row
describes. `BUILT_NOT_PROVEN` is permitted where Terminal has the merge, the
migration is applied, and the production readback has not happened.

## The five rows

### LEDGER_MOVE #11 — MO-PAID-031 (grounded research answers)

> Quoted stale text (state_delta, F00C CSV line 102): "UNCHANGED
> (app/research.py = Research Vault PDF library, a false-positive nearest
> organ)".

Merge citation + ancestor claim. The merge that did not move this row is none;
the ancestor claim that holds the row open is
`research/market_intelligence_productization/MARKET_ONTOLOGY_F11_POST_VERTICAL_CONTRACT_2026-09-06.md`
§MO-PAID-031, which freezes the closed-list corpora (shipped product artifacts
+ Tier-2 receipts + the user's own objects under owner-only RLS), the
forbidden-corpus list (DNR:KILL-PUBLIC-INTERNALS, DNR:KILL-LLM-CONFIDENCE, A7),
and the ceiling `non_authoritative_assistant` for the assistant. The contract
is frozen and recorded on main; the row remains `SPEC_ONLY` because no
research-mode route has been built, and the contract explicitly defers behind
the Thesis-object vertical (MO-PAID-046/047/053).

Proposed `capability_state_c2`: `PARTIAL`. The contract is now on main with
acceptance language, so the row is past pure spec; the implementation half is
still owed. The move is past `SPEC_ONLY` because nothing about the contract is
open to interpretation anymore — what is owed is wiring, not more spec.

Proposed `next_bounded_child`: ONE bounded build under the F11 lane that wires
a research-mode route to the closed-list corpora, sits behind
CXI-R23 / `engine/neuralweb/brain_gateway.py:406-424` (`BRAIN_INTERNALS_ALLOWLIST`)
without widening or mirroring that gate, prints the ceiling sentence in plain
words, and returns the plain-word null when no allowed corpus covers the
question. Acceptance: a research query returns a non-authoritative grounded
answer distinct from `app/research.py` and from general chat; it cites only
corpora 1–3, carries the ceiling sentence, and prints the plain-word null.

### LEDGER_MOVE #20 — MO-PAID-032 (recurring briefs)

> Quoted stale text (state_delta, F00C CSV line 103): "UNCHANGED".

Merge citation + ancestor claim. No merge moved this row. The ancestor claim
is the same F11 contract document at §MO-PAID-032, which freezes the cadence
owner (`.github/workflows/daily.yml` cron pair at `:36-37` plus
`scripts.build_session_digest` at `:3236` and `scripts.build_briefing` at
`:3946`; the weekly cadence owner is `.github/workflows/weekly.yml:4`), the
subscription row contract (`{subscription_id, user_id, target, cadence, delivery,
state, created_at}` with `cadence ∈ {daily_after_us_close, weekly_saturday}` and
`delivery = in_product_inbox` for v1), and the typed-degraded-state contract.
The contract documents the open dependency on MO-PAID-085 for email/push
delivery and names its ceiling `workflow_only`. The row is still `SPEC_ONLY`
because no subscription surface has been built and the cadence owner has no
subscriber route today.

Proposed `capability_state_c2`: `PARTIAL`. Same shape as #11: the contract is
frozen and on main, so the row is past pure spec, but no subscription surface
exists, so it is not `BUILT_NOT_PROVEN`. The contract's explicit scoping — the
in-product cadence and disclosure contract only, with email/push as an OPEN
DEPENDENCY on MO-PAID-085 — is what the move reads against.

Proposed `next_bounded_child`: ONE bounded build that adds the
in-product-inbox subscription surface over the existing
`.github/workflows/daily.yml` and `.github/workflows/weekly.yml` cadence
owners, idempotent on `(subscription_id, slot_asof)`, emitting at most one
brief per user per cadence slot. A slot that cannot produce writes the typed
degraded state with the plain-word line and never back-fills with a
synthesized brief. The build inherits the dependency on MO-PAID-085 and does
not wire a send path. Acceptance: a scheduled recurring brief arrives on
cadence without manual re-trigger, produced by the existing nightly/weekly
owner with no second scheduler; a slot that cannot produce shows the typed
degraded state and its plain-word line instead of a brief.

### LEDGER_MOVE #21 — MO-PAID-047 (condition monitoring)

> Quoted stale text (state_delta, F00C CSV line 105): "UNCHANGED
> (falsifier_tripwires latch law verified: FIRED sticky; un-fire only by
> version bump; current_leg re-evaluated live — Ruling A17)".

Merge citation + ancestor claim. The ancestor is `engine/falsifier_tripwires.py`
in production (the tripwire state machine over cycle-ontology conditions, with
the latch/version-bump/current_leg semantics verified at `persist()` ~L504-546)
and its consumers `engine/moat_falsifiers.py`, the theme thesis lane, and the
research factory. The latch law has been verified; what is owed is the
USER-FACING projection that binds a Thesis Condition to a monitor subscription
plus notification via the F08 delivery path. House law #3821 — user-facing text
never says "falsifier" or its untranslated Chinese equivalent — is the
front-facing constraint the projection must honor.

Proposed `capability_state_c2`: `PARTIAL` (unchanged in this packet). The row
already carries `PARTIAL` because the underlying machinery is verified and the
projection over user Thesis Conditions is owed; nothing in the F11 contract or
in this planner batch moves it past `PARTIAL` until the user-monitor binding
ships and a notification has been received from a user Thesis Condition FIRED
transition via the F08 path. A move to `BUILT_NOT_PROVEN` would require the
binding to have shipped without a production readback, and that shipping has
not happened.

Proposed `next_bounded_child`: ONE bounded build that binds user Thesis
Conditions (Thesis head + Condition row + subscriber + cadence) to the
existing `engine/falsifier_tripwires.py` state machine, reusing the
latch/version-bump/current_leg semantics verbatim and naming no second engine.
The notification half rides the F08 delivery path (the existing
`engine/portfolio_digest.py` typed-degraded contract); the front-facing
language never carries "falsifier" or its untranslated Chinese term per
house law #3821. Acceptance: a subscribed Thesis Condition FIRED transition
triggers a notification via the F08 delivery path; a version bump un-fires
only via the existing tripwire state machine, never via a second engine.

### LEDGER_MOVE #22 — MO-PAID-053 (Research Management System views)

> Quoted stale text (state_delta, F00C CSV line 106): "The research
> management views shipped in terminal#520 (B-F11-2, merged 8255f482):
> Coverage, Ideas, Notes, Theses, Catalysts, Risks and Reviews all render as
> filtered views over the same Thesis objects, with no separate engine and no
> second store."

Merge citation + ancestor claim. The merge is terminal#520 (B-F11-2), squashed
as `8255f482`, over `terminal/lib/rmsViews.ts`,
`terminal/components/workspaces/ThesisWorkspace.tsx`, and
`terminal/app/api/theses/route.ts` on Terminal master. The B-REC-B5-1
reconciliation packet (`research/market_intelligence_productization/MARKET_ONTOLOGY_F00C_TERMINAL_WAVE_RECONCILIATION_2026-09-09.md`,
the row at MO-PAID-053) read the row's acceptance sentence literally — "Coverage,
Ideas, Notes, Theses, Catalysts, Risks and Reviews render as views over the
same objects" — and found the sentence met. The CSV moved the row to
`BUILT_NOT_PROVEN` on 2026-09-12 in the macro#7003 merge, not before. The
residual gap the reconciliation named — views over not-yet-built Thesis
identities — closes once the MO-PAID-046 amendment language lands on Terminal
master (the `previous_version` ↔ `amended_from` vocabulary alignment).

Proposed `capability_state_c2`: `BUILT_NOT_PROVEN` (unchanged in this
packet). The row already carries `BUILT_NOT_PROVEN` after the Wave 4
reconciliation. The proposed move does not advance the row to `PROVEN_LIVE`,
because no production readback exists; a `PROVEN_LIVE` move would require
two distinct users exercising the surfaces in production with receipted
session traces, and that evidence has not been recorded.

Proposed `next_bounded_child`: NONE in this packet. The bounded child the
B-REC-B5-1 reconciliation named — the `previous_version` ↔ `amended_from`
vocabulary alignment on the Terminal master — is owned by MO-PAID-046's own
row and not duplicated here. This note records that the F11 slice does not
add a second child for MO-PAID-053, and the field stays empty.

### LEDGER_MOVE #23 — MO-PAID-054 (chat-to-Thesis binding)

> Quoted stale text (state_delta, F00C CSV line 107): "UNCHANGED (audit-1
> correction PROVEN_LIVE→PARTIAL confirmed already applied in CSV)".

Merge citation + ancestor claim. The assistant organ itself was audited and
moved from `PROVEN_LIVE` to `PARTIAL` in the audit-1 round, with the receipted
200s on `GET /api/brain/me` and `POST /api/brain/chat` standing as evidence of
the LIVE half and the workspace-object binding absent as evidence of the
PARTIAL half. The ancestor contract is the same F11 document at
§MO-PAID-054, which freezes the propose-only write-back (`thesis_amendment_proposal`
rows, mandatory `amended_from`, K1 `EvidenceRef` pointers only, never a copy),
the never-in-place rule (no UPDATE/DELETE on a Thesis head row, no in-place
edit), the never-a-score rule (no model-originated numeric), and the identity
gate (Stock Identity + Data OS + Supabase auth under the caller's session,
never a service-role write). The ceiling is `non_authoritative_assistant` (A7).
The row is `PARTIAL` because the binding to durable user Thesis/Note objects
is still owed.

Proposed `capability_state_c2`: `PARTIAL` (unchanged in this packet). The row
stays `PARTIAL` because the durable-object binding is unimplementable until
MO-PAID-046/047/053 land, and the F11 contract explicitly defers on that
dependency. A move to `BUILT_NOT_PROVEN` would require the binding to have
shipped, which it has not.

Proposed `next_bounded_child`: ONE bounded build under the F11 lane that
binds chat context to the durable Thesis/Note objects once MO-PAID-046/047/053
land, inheriting those rows' contracts. The build writes at most a
`proposed` amendment row from a chat turn, mandates `amended_from`, refuses
in-place updates, and refuses any model-originated numeric field. Reads and
proposals resolve through Stock Identity + Data OS + Supabase auth under the
caller's session; no service-role write on behalf of a chat turn. Acceptance:
a chat turn cites a durable user Thesis by `amended_from` and writes at most a
`proposed` amendment row; no in-place edit and no model-originated score is
reachable from any chat path; a proposal without `amended_from` is refused with
a plain-word reason.

## Summary table

| Move | Row | Current state | Proposed state | Child in this packet |
|---|---|---|---|---|
| #11 | MO-PAID-031 | `SPEC_ONLY` | `PARTIAL` | one bounded build, F11 lane |
| #20 | MO-PAID-032 | `SPEC_ONLY` | `PARTIAL` | one bounded build, F11 lane |
| #21 | MO-PAID-047 | `PARTIAL` | `PARTIAL` (unchanged) | one bounded build, F11 lane |
| #22 | MO-PAID-053 | `BUILT_NOT_PROVEN` | `BUILT_NOT_PROVEN` (unchanged) | none (vocabulary alignment owned by MO-PAID-046) |
| #23 | MO-PAID-054 | `PARTIAL` | `PARTIAL` (unchanged) | one bounded build, F11 lane |

## What this note does not do

- It does not edit the F00C CSV. The CSV remains the source of truth and is
  owned by PR #7014 (B-REC-B5-X). When #7014 lands and a records lane picks
  this note up, the proposed `capability_state_c2` values may be applied as
  written; until then the proposed column here is a recommendation only.
- It does not promote any row to `PROVEN_LIVE`. The strongest evidence in
  hand for any row is either a Terminal merge sha (BUILT_NOT_PROVEN eligible)
  or a frozen contract (PARTIAL eligible) or neither (SPEC_ONLY / NOT_BUILT),
  and no row carries a production readback of two people exercising the
  surface in production.
- It does not add a second child to MO-PAID-053; the residual
  `previous_version` ↔ `amended_from` vocabulary alignment is named by the
  MO-PAID-046 row, not duplicated here.
- It does not touch MO-PAID-085 (email/push delivery); the F11 contract
  documents the open dependency and this note records it again.
- It does not comment on macro#6819. The records agent never comments on
  #6819; only the seat posts the Wave 5 comment, and that comment is one
  sentence naming this record.

## Records chain

- Wave 5 record: `agentos/handoffs/MARKET-ONTOLOGY-META-CEO-B-2026-09-13.md`,
  ending seat d640f3ef at 03:53Z 2026-09-13, succeeded by
  harness session 7cd4fae1 (Fable 5.1).
- Wave 4 record: `agentos/handoffs/MARKET-ONTOLOGY-META-CEO-B-2026-09-11T12.md`.
- F11 contract ancestor:
  `research/market_intelligence_productization/MARKET_ONTOLOGY_F11_POST_VERTICAL_CONTRACT_2026-09-06.md`.
- F11 HUMAN-RESEARCH-RMS handoff:
  `agentos/handoffs/MARKET-ONTOLOGY-F11-HUMAN-RESEARCH-RMS-FABLE-COO-2026-08-26.md`.
- DEC-F11: `agentos/decisions/DEC-F11-ASSISTANT-GROUNDS-ON-PRODUCT-ARTIFACTS.md`.
- Pin test: `tests/test_w9_ledger_note_f11.py` (this packet).
