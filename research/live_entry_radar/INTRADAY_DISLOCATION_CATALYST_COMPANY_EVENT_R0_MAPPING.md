# Catalyst Context R0 Mapping Freeze - Company Intelligence Earnings Workspace

**Owner path:** `engine/company_intelligence/events.py` + `engine/company_intelligence/event_workspace.py`  
**Consumer:** `engine.entry_radar.catalyst_context`  
**Authority:** research-only context; all Radar authority remains false  
**Frozen before:** adapter implementation or any market-outcome study

## 1. Purpose

Attach one already-published Company Intelligence earnings-results workspace to an existing
Live Entry Radar tactical episode without inventing a second event identity, lifecycle, or
materiality model.

This mapping proves only **presence of a source-owner earnings event version** at a caller
observation clock. It does not establish universe-wide Company Intelligence coverage and it
never proves the absence of other catalysts.

## 2. Accepted owner object

The adapter accepts only a payload that passes `validate_event_workspace` and whose canonical
`event_id` parses through `parse_canonical_event_id` as:

`event_type == "earnings_results"`

The caller also supplies:

- the tactical security ticker being evaluated;
- `owner_observed_at`, the clock when the caller actually observed this owner workspace.

The ticker must be present in `issuer.listings[].ticker`. A workspace for another listing/
issuer is a contract error, not a fuzzy match.

## 3. Accepted lifecycle states

R0 admits only the lifecycle states that the **current production
`build_event_workspace` publisher can actually persist**:

- `complete`
- `corrected`

The canonical `company_event.v1` lifecycle is broader, but that does not license this adapter
to speculate about future workspace publication semantics. The current builder creates an event,
walks `started -> complete` in memory, and only additionally walks to `corrected` when the
bound source revision changed (or carries an already-corrected state forward). It then serializes
that final state into `event_workspace.lifecycle.state`.

Accordingly, the adapter refuses all other event-lifecycle states, including:

- `discovered`
- `scheduled`
- `rescheduled`
- `started`
- `completed_partial`
- `derived_ready`
- `distributed`
- `cancelled`
- `superseded`

Refusal is not nonblocking evidence. If a future owner publisher begins minting another lifecycle
state, that source contract must be recensused and this mapping re-frozen before R0 can consume it.

## 4. Clock law

The workspace supplies:

- `lifecycle.source_available_at` - the source-owner availability clock;
- `lifecycle.observed_at` - Company Intelligence observation clock;
- `generated_at` - the exact workspace-generation build clock.

The caller supplies:

- `owner_observed_at` - when the current consumer actually observed this published object.

The adapter requires:

`source_available_at <= lifecycle.observed_at <= generated_at <= owner_observed_at`

This is deliberately stricter than reusing SEC/public availability as a consumer clock.
A workspace artifact cannot be backdated to the original issuer event merely because the
source existed earlier.

Output clocks are:

- `source_available_at = lifecycle.source_available_at`
- `known_at = owner_observed_at`

Historical static workspace bytes with no lawful consumer observation receipt therefore
cannot manufacture a historical as-observed intraday decision.

## 5. Frozen disposition mapping

For this safety-context experiment only, an admitted currently-published
`earnings_results` workspace maps to:

`owner_disposition = "blocking"`

This is conservative and direction-free. It means only:

> a source-owner earnings-results event version was already known at the tactical decision
> clock, so the episode cannot be described as an ordinary catalyst-clear mean-reversion case.

It does not classify the earnings as good/bad, predict continuation/reversal, or create
entry/trading authority.

## 6. Exact version identity

Company Intelligence intentionally keeps the logical `event_id` stable across corrections.
The workspace publisher separately mints an immutable `generation_id`.

R0 therefore references the exact owner version as:

`native_id = {event_id}@{generation_id}`

and:

`evidence_ref = company-intelligence-workspace:{event_id}@{generation_id}`

This composes two existing owner identities; it does not mint a new company-event identity.

## 7. No-coverage rule

The adapter returns only `CatalystEvidence`. It never returns `CatalystSourceRead`.

A healthy Company Intelligence source-coverage read requires a separate receipt that proves
the requested owner source set was completely read by the Radar decision clock. Presence of
one workspace, a ready manifest, or an empty lookup is not by itself universe-wide
catalyst-clear evidence.

## 8. Refusals

The adapter refuses:

- invalid `event_workspace.v1`;
- non-`earnings_results` event identity;
- requested ticker absent from the issuer listings;
- missing source/owner/generation clocks;
- any clock inversion;
- pre-release, cancelled, or superseded lifecycle state.

Refusal is never serialized as `nonblocking`.

## 9. Validation

Synthetic tests must prove:

- exact owner event/generation identity is preserved;
- post-release result workspaces map to blocking presence evidence;
- scheduled/discovered events are refused;
- wrong ticker is refused;
- non-results events are refused;
- source/owner/generation clock inversions are refused;
- attaching the resulting evidence to incomplete coverage still keeps the known blocking
  event visible;
- no source coverage receipt, score, rank, recommendation, or trade authority is minted.

## 10. Prospective current-reader composition

The existing owner reader `engine.neuralweb.company_intelligence_reader.read_current_event_workspace`
is the only read seam admitted by R0 for current-marker forward shadowing. R0 does not add a
network client, ticker index, cache, publication path, or event store.

The reader envelope is interpreted asymmetrically:

- `available == true`: the owner already loaded the current marker/generation, selected the
  ticker alias, fetched the immutable workspace object, hash-verified it, and returned a
  `receipt`. R0 may adapt that workspace as **presence evidence** after applying the frozen
  event/ticker/lifecycle/clock rules above.
- `available == false`: whether the owner says `Event workspace does not cover this ticker`
  or reports a fetch/integrity failure, R0 emits no negative event fact. The catalyst result
  remains `coverage_unknown`.

The caller must supply `read_observed_at`, the actual prospective consumer observation clock.
The found workspace is not knowable to R0 before that clock. If `read_observed_at` is later
than the Radar decision clock, the event is retained only as late evidence and cannot rewrite
the earlier decision.

A successful read must preserve the owner envelope's `context_only` authority and carry the
owner `workspace_sha256` receipt. The pure composition helper
`assess_company_intelligence_current_read_for_live_episode` performs no I/O and does not mint
a `CatalystSourceRead` coverage-clear receipt. Even a verified found event therefore does not
claim universe-wide catalyst coverage.

**Historical prohibition:** this current-marker reader may not be used to reconstruct a
historical decision-time absence or to backfill `known_at` from `generated_at`, SEC
availability, file mtime, or today's marker. Historical outcome work remains blocked on
lawful owner vintages / observation receipts or prospective forward accrual.

## Relevance window (2026-10-03)

A results release drives the context from the moment it is known until the close of the first regular US session that opens at or after the release became available. A release after the close or before the open is relevant through that next session's close. A release during a session is relevant through the following session's close. After that the reference is kept as expired evidence and no longer drives the context state. The window is computed from the Radar reference-session calendar and the release's source-availability clock only.

## Repair 2 — 2026-10-03

- Company-event earnings evidence carries the same five-session `aftermath_until` extension after `relevant_until`.
- Coverage reads must satisfy the module 900-second staleness ceiling as well as owner `fresh_until`.
- Late workspace evidence is recorded for audit and never rewrites decision-time state or coverage.
- Amendments and distinct workspace generations remain separate evidence rows.
