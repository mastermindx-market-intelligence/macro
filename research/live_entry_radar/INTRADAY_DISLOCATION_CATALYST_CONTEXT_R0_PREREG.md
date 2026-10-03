# Intraday Dislocation Catalyst Context R0 - Preregistration

**Status:** synthetic-only, research-only, BUILT_NOT_PROVEN candidate contract  
**Owner:** WS:LIVE-ENTRY-RADAR / entry_radar research plane  
**Consumer:** Terminal Tactical Intelligence / Dislocation + Reclaim product work  
**Authority:** display/research only; no rank, size, gate, signal origination, escalation, order, or portfolio authority  
**Frozen before:** any historical catalyst-outcome sweep or production wiring

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
- every authority flag remains false;
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

After the pure contract is green, the next bounded step is a source-owner adapter census: for each candidate source plane, document exact native identity, clock semantics, coverage state, accepted owner-disposition mapping (if any), and whether the source can support prospective forward shadowing.

Only after that source matrix is accepted may an adapter attach real owner evidence to existing Radar tactical episodes. Any empirical claim then runs through Setup Species / Evaluation OS on the incumbent TrialLedger, not a new Terminal ledger.
