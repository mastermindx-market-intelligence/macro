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

Only post-release states are admitted as blocking presence evidence:

- `started`
- `completed_partial`
- `complete`
- `corrected`
- `derived_ready`
- `distributed`

The following are **not** mapped to blocking evidence by this adapter:

- `discovered`
- `scheduled`
- `rescheduled`
- `cancelled`
- `superseded`

A non-admitted state is refused. The caller must preserve unknown/coverage-incomplete
semantics; it may not silently reinterpret the refusal as nonblocking.

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

For this safety-context experiment only, an admitted post-release
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
