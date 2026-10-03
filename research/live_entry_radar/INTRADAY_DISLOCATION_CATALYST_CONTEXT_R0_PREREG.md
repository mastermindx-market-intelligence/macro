# Intraday Dislocation Catalyst Context R0 - Preregistration

**Status:** synthetic-only, research-only, BUILT_NOT_PROVEN candidate contract  
**Owner:** WS:LIVE-ENTRY-RADAR / entry_radar research plane  
**Consumer:** Terminal Tactical Intelligence / Dislocation + Reclaim product work  
**Authority:** display/research only; no rank, size, gate, signal origination, escalation, order, or portfolio authority  
**Frozen before:** any historical catalyst-outcome sweep or production wiring  
**Wire contract:** `research/live_entry_radar/contracts/catalyst_context.schema.json`

## 0. Commission

The Dislocation + Reclaim product needs an adverse-selection safety context around an already-existing tactical entry episode. This R0 answers one narrow question:

> At the Radar decision clock, what source-owner catalyst evidence and source-coverage state were actually knowable?

R0 does **not** decide whether a price move is a dislocation, whether exhaustion/reclaim has occurred, whether the security should be owned, or whether a trade should be taken.

## 1. Existing owners are binding

This work extends the existing Radar research owner. It does not create a second detector, tactical lifecycle, event store, replay ledger, or issuer-event truth plane.

Binding adjacent owners:

- Live Entry Radar owns tactical episode identity/lifecycle and its scientific TrialLedger.
- TTI R1-B owns the pending causal fresh-low -> exhaustion/reclaim construction on its existing held carrier; this R0 does not alter or import its unmerged implementation.
- Setup Species / Evaluation OS own experimental registration/evaluation.
- Company/Earnings Intelligence and other event programs own issuer-event truth and native clocks.
- DRL / price_pressure owns the existing residual-shock descriptor.
- Terminal remains a product consumer.

The R0 output carries the existing owner-issued Radar `episode_id` directly as
`radar_episode_id`, with `radar_episode_schema = "mastermind.live_entry_episode.v1"`.
Current Radar v1 episode IDs are the owner's 16-lowercase-hex `sha16` address over
`(ticker, detector_id, variant, first_armed_at)`; R0 refuses wrapper strings or aliases rather
than minting a second reference convention.

Radar's `mastermind.live_entry_episode.v1.evidence_refs` field remains owned by the incumbent
Radar entry-event ledger and is populated from the episode's existing `event_ids`. Catalyst
context does **not** append issuer-event/catalyst references into that field and does not mutate
the live episode record. The join is an external research projection keyed by the exact existing
`radar_episode_id`; owner-native catalyst refs remain inside the separate R0 context.

## 2. Killed constructions that remain killed

This R0 must not reopen the following Mastermind laws:

- `DNR:KILL-PSS-F3-RESIDUAL`: residual reset failed as standalone entry timing. Residual magnitude is context only.
- `DNR:KILL-LIQUIDITY-SHOCK-REVERSAL-CLASSIFIER`: prior no-news shock-reversal classifier did not earn promotion. R0 does not convert "no blocking event observed" into a bounce prediction.
- `DNR:KILL-WASHOUT-TURN`: depth x turn is not revived as an entry authority.
- `DNR:KILL-PARALLEL-SHOCK-CLASSIFIER`: R0 does not mint a second shock-day taxonomy.

No price, residual-return, VWAP, RVOL, oscillator, or LLM field is accepted by this catalyst contract.

## 3. R0 objects

### 3.0 Radar episode binding

The attachment carries:

- `radar_episode_schema = "mastermind.live_entry_episode.v1"`
- `radar_episode_id = <owner-issued 16-hex Live Entry Radar episode_id>`

These fields reference the incumbent Radar lifecycle. They do not alias it into Prophet B1,
create a new episode family, or recompute identity from ticker/date.

### 3.1 Source coverage read

R0 reuses Radar's existing source availability vocabulary:

- `ok`
- `stale`
- `unavailable`

A source read carries:

- `source_id`
- `status`
- `source_asof`
- `observed_at`
- optional human diagnostic detail

Required temporal law:

`source_asof <= observed_at <= decision_at`

for the read to count as healthy coverage at that decision.

### 3.2 Event evidence reference

R0 does not copy source bodies. It carries only compact source-owner references:

- `owner`
- `native_id`
- `ticker`
- `event_kind`
- `source_available_at`
- `known_at`
- `owner_disposition`
- `evidence_ref`

Temporal law:

`source_available_at <= known_at`

An event with `known_at > decision_at` is preserved as late evidence but may not rewrite the earlier decision context.

### 3.3 Owner disposition

R0 has no materiality model. It accepts only a disposition explicitly supplied under a governed source-owner mapping:

- `blocking`
- `soft`
- `nonblocking`
- `unknown`

If no accepted source-owner mapping exists, disposition is `unknown`. An LLM summary, headline sentiment, price drop, residual z-score, or event keyword may not invent this field.

### 3.4 Closed serialized wire

The cross-repository consumer boundary is the owner schema:

`research/live_entry_radar/contracts/catalyst_context.schema.json`

It is a closed Draft 2020-12 JSON Schema over the exact `CatalystContext.to_dict()` output.
The schema fixes:

- the R0 schema id and incumbent Radar episode schema;
- the owner-issued 16-lowercase-hex Radar episode id;
- the house UTC-second `...Z` clock form;
- the five context states and state-consistency invariants;
- non-empty declared required-source set;
- the existing Radar `ok | stale | unavailable` source-read vocabulary;
- closed source-read keys;
- unique evidence-reference arrays;
- the incumbent all-false Radar authority block;
- `research_only=true`;
- no undeclared root fields.

Terminal and any later consumer must validate this owner wire rather than reconstructing the
shape from prose or widening it locally. Adding a new field or authority bit is an owner-contract
change, not a consumer convenience edit.

## 4. Fail-closed context states

The output state is descriptive context, not a gate:

1. `blocking_event_observed` - at least one on-time owner-classified blocking event exists.
2. `event_classification_unknown` - an on-time event exists but its owner disposition is unknown.
3. `coverage_unknown` - one or more explicitly required source owners are missing, stale, unavailable, or only observed after the decision clock.
4. `soft_event_observed` - coverage is complete and at least one soft event is known, with no blocking/unknown event.
5. `no_blocking_event_observed` - all required source reads are healthy at the decision clock and no blocking/unknown/soft event is known.

Precedence is exactly the order above except that a known blocking event remains visible even when another source's coverage is incomplete. "No blocking event observed" means only within the explicitly declared covered sources. It is never serialized or narrated as "no news."

Every output carries the existing all-false Radar authority block and `research_only=true`.

## 5. Coverage law

The caller must declare `required_sources`. An empty required-source set is a contract error.

A source omitted from `source_reads` is missing, not negative.

A stale or unavailable source is not an empty source.

A read observed after `decision_at` does not backfill historical coverage.

The R0 contract does not claim that the currently available issuer-event estate is universe-complete. Current source censuses show uneven event and materiality coverage; historical point-in-time issuer-event replay remains incomplete. Therefore initial integration remains synthetic/forward-shadow only.

## 6. Identity and correction law

Evidence dedup identity is `(owner, native_id)`.

Exact duplicate payloads are idempotent.

The same identity with conflicting bytes/classification is a contract error and must fail closed upstream; keep-last is forbidden.

Evidence ticker must equal the tactical episode ticker.

Output ordering is deterministic.

No output key may introduce score/rank/weight/conviction/buy/sell/trade semantics.

## 7. R0 acceptance tests

The first implementation must prove:

- healthy empty coverage yields only `no_blocking_event_observed`;
- missing/stale/unavailable required source yields `coverage_unknown`;
- a source observed after the decision clock cannot establish coverage;
- source-asof after observed-at is rejected;
- on-time blocking evidence yields `blocking_event_observed`;
- owner disposition `unknown` fails closed;
- soft evidence remains context only and cannot gain authority;
- late blocking evidence is preserved as late evidence but does not rewrite the prior context;
- source-available-at after known-at is rejected;
- wrong-ticker evidence is rejected;
- exact duplicate evidence is idempotent;
- conflicting duplicate evidence is rejected;
- the owner-issued Radar `episode_id` is passed through exactly as `radar_episode_id`;
- wrapper/surrogate Radar episode references are refused;
- the incumbent live episode record and its `evidence_refs` are not mutated by catalyst attachment;
- output is deterministic;
- the runtime serialized output validates against the owner JSON Schema;
- unknown root/source-read fields are rejected by the wire schema;
- surrogate Radar episode ids, loose clock encodings, empty required-source sets, and
  contradictory context-state payloads are rejected by the wire schema;
- every authority flag remains false in both runtime and wire schema;
- `required_sources` cannot be empty.

## 8. What R0 does not prove

Passing these tests proves only contract behavior on synthetic inputs. It does **not** prove:

- material-event coverage completeness;
- a reliable historical no-news label;
- improved entry timing;
- lower MAE;
- profitability;
- live latency;
- real-time source entitlement;
- production readiness.

No historical outcome sweep is authorized by this preregistration alone.

## 9. Next evidence gate

The source-owner census, two earnings-presence adapters, direct owner Radar-episode binding,
prospective Company Intelligence current-reader composition, and one real current owner-read
proof now exist. The current blocking evidence is upstream Radar live-source availability:
canonical `data/entry_radar/ledger_state.json` remains `WAITING_FOR_LIVE_SOURCE`, and the
private-spool remediation is the separate held owner carrier Macro PR #6625.

Therefore the next end-to-end gate is a **real owner-issued Live Entry Radar episode** arriving
through the accepted incumbent private transport. R0 must not fabricate an episode, enable
`ENTRY_RADAR_LIVE_ENABLE`, or substitute a Prophet/ticker-date episode while that gate is closed.

Independent work may continue on the closed wire contract and Terminal consumer semantics.
Any empirical timing/MAE/return claim still runs through Setup Species / Evaluation OS on the
incumbent TrialLedger after lawful forward episodes exist; R0 creates no second evaluation ledger.


## Pre-outcome integrity correction (2026-10-03)

This is implementation hardening before any outcome read, not a new selector or
trial. Required source sets, source-owned freshness, disposition precedence and
all-false authority are unchanged. The context remains unmerged research code.

- Intraday clocks require explicit timezone and second precision; date-only or
  naive values are refused rather than assigned midnight/UTC. Microseconds are
  retained in comparison, duplicate detection and wire serialization.
- A current Radar snapshot may not be projected before its arm, candidate or last
  observation clock. Missing snapshot clocks refuse the composition.
- Company workspace evidence must match its owner-canonical payload hash and its
  issuer/event identity. A 64-character hash shape is not payload verification.
- Direct context construction must satisfy the same state/coverage invariants as
  the assessor. Required sources are an explicit sequence, not a string.
- CI collects these regressions in the incumbent Radar test step. No independent
  workflow, scientific registry, source collector, production activation or trade
  permission is introduced. This adds no historical coverage or absence proof.

The unmerged schema is stored in the incumbent Radar research namespace; the
existing ownership fence stays unchanged. Its schema identifier is not a live URL
or publication claim. No published consumer or frozen detector schema changes.
