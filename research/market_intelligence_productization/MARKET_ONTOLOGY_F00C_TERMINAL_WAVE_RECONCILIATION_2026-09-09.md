# F00C ledger reconciled against the merged half-B Terminal wave

Packet B-REC-B5-1, recorded 2026-09-09 by the Meta-CEO B seat. Records only: no product
code, no new capability, no promotion of any authority ceiling.

## Why this record exists

Half B shipped ten pull requests to the Terminal repository between 2026-09-06 and
2026-09-09 — #513, #514, #515, #517, #520, #522, #524, #526, #527 and #529 — and not one
row of the granular closure ledger moved. The Charter's DONE test is computed off that
ledger, so for three days the program was counting itself as further behind than it was,
by roughly a tenth of the paid backlog. This packet re-reads each merged difference
against the ledger's own acceptance sentence and writes down what it found, row by row.

The rule applied to every row was the same and was applied literally: the acceptance
sentence already written in the ledger is the test, not a paraphrase of it and not the
pull request's title. Ten sentences were met. Two were not, and those two rows stay open
with the missing piece named.

## What the state words mean here

`BUILT_NOT_PROVEN` means the capability is merged to the Terminal default branch and, where
it needed a database change, the migration was applied to production with a receipt in this
repository. It does not mean anyone has used it. No row in this packet moves to
`PROVEN_LIVE`, because that word is reserved for a capability with a production readback
behind it, and the strongest evidence the seat holds is that the migrations applied — a
readback of the database catalog, not of two people doing the thing the row describes. When
two people have exercised one of these surfaces in production and that is recorded, the row
can move again; nothing in this packet anticipates that.

## The ten rows that moved

- `MO-PAID-051` — a team-scoped membership row is created and read by a live route. Shipped
  in #514, merged as `cff58ee8`, over migration 0014, which was applied to production on
  2026-09-08.
- `MO-PAID-081` — an invited address completes a join against a team. The invitation route
  creates an invitation for one address, and accepting it as that address joins the team;
  a different address is refused in plain words. The code came from the stacked #526 and
  reached the default branch inside #514's merge. Migration 0015 applied 2026-09-08.
- `MO-PAID-082` — two roles produce two outcomes on one route. An owner or an administrator
  may add a member or change a workspace setting; a plain member is refused on the same
  routes. The pure decision function that #529 added is cited alongside it.
- `MO-PAID-083` — a workspace setting persists distinctly from a personal one. Migration
  0015 stores the two as separate rows under separate read rules. There is no settings
  screen for it yet, which is exactly why the row reads as merged rather than proven.
- `MO-PAID-086` — a signed-in person downloads a snapshot of their own data as JSON or CSV.
  Shipped in #527, merged as `68bbe8ea`.
- `MO-PAID-087` — a deletion request returns a durable receipt with a reference code and the
  steps that follow. Also #527, over migration 0016, applied to production on 2026-09-09.
  The Supabase-side lifecycle behind it is still an out-of-repo fact and is recorded as
  unverified in the row's notes rather than being quietly dropped.
- `MO-PAID-028` — an event object resolves to the positions it touches on a routed page.
  Shipped in #522, merged as `68b0d00a`.
- `MO-DELTA-042` — the event object schema resolves to affected positions. Same merge. The
  object carries direction, mechanism and timeframe from the source or prints that the
  source did not state them.
- `MO-PAID-036` — a person's actual holdings produce a concentration, factor and liquidity
  readout. Shipped in #524, merged as `efcd98aa`. The factor half is met by industry weight
  and company-size weight.
- `MO-PAID-053` — Coverage, Ideas, Notes, Theses, Catalysts, Risks and Reviews render as
  views over the same objects. Shipped in #520, merged as `8255f482`, with no second engine
  and no second store.

## The two rows that did not move, and why

- `MO-PAID-046` asks that a person create and revise a Thesis through the interface, that
  revisions be new rows carrying `amended_from`, and that no edit be possible in place. Two
  of those three are true: migration 0012 gives an immutable version table, and #520 puts
  create and revise behind the workspace form, so every revision is a new row and nothing is
  edited in place. But the supersession link the shipped store carries is called
  `previous_version`; the token `amended_from` appears nowhere in the Terminal tree. That is
  a vocabulary mismatch, not a missing capability, and the honest way to close it is one
  bounded child that either carries the named reference or amends the sentence. Until then
  the row reads `PARTIAL`.
- `MO-DELTA-014` asks for per-user Sharpe, Sortino, beta and concentration. Only
  concentration shipped. Sharpe and Sortino exist in the Terminal tree only in seasonal and
  assistant tooling, and neither they nor beta are computed over a person's own holdings.
  One quarter of a sentence is not the sentence, so the row reads `PARTIAL` and keeps a
  child of its own. Note the knock-on: this row's child had been absorbed into
  `MO-PAID-036`'s, and `MO-PAID-036` has now closed, so the absorption is spent and the
  remaining work needs its own child rather than a parent that no longer exists.

## What this record deliberately does not do

- It does not touch `real_consumer` on any row. Several of the twelve still read `NONE`
  where a consumer now plainly exists. That column was outside this packet's named scope,
  and widening the scope of a ledger edit mid-packet is how a shared write surface becomes
  unreviewable. It is named here so the next reconciliation can pick it up.
- It does not touch `MO-PAID-084`, `MO-PAID-085` or `MO-PAID-088`. No pull request in this
  wave ships them.
- It does not claim any production proof. See the state-word section above.
- It writes no disposition into any row outside the twelve, and it changes no authority
  ceiling, no source-rights entry and no family assignment.

## Where the evidence lives

`F00C_TERMINAL_WAVE_RECONCILIATION_MANIFEST_2026-09-09.json`, beside this file, carries the
machine-readable version: each of the twelve rows with the pull request it names, that pull
request's merge commit, the producer paths that were confirmed present on the Terminal
default branch at commit `db69d072`, and the residual for each row that stayed open. The
suite `tests/test_f00c_terminal_reconciliation.py` asserts the manifest and the ledger agree
and that neither invents a state word. The suite reads the manifest, never the other
repository, so it cannot pass or fail on the state of a checkout this repository does not
own.
