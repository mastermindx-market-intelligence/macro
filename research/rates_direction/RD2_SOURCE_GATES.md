# RD2 source gates and next bounded capability

Parent: WS:RATES-INFLATION-COMMAND. Operation: rates-direction-20260924-sol-001.
RD1 produced a negative result. Do not tune its frozen candidate, claim its history
is still untouched, or publish its probabilities as accepted forecasts.

## Freshly checked dependencies

Macro #7521 is OPEN / Draft / HOLD-FOR-SOL at
8da98209ad4a34450745780666c48b6999f2bfb2. Its source contract is
research/RATES_POLICY_CONSUMER_INTEGRATION_2026-09-20.md and its producer is
engine/fed_path.py. It preserves ZQ/EFFR versus SR3/SOFR basis and continuous
pricing through validated_pricing_view. It explicitly does NOT qualify historical
availability. Its rolling m12 delta can contain contract/weight/calendar effects;
required contract/period/weight evidence remains an upstream collector dependency.

Macro #7593 is OPEN / Draft / HOLD-FOR-SOL at
3cfc4f4fd48c04ac7f573298e87406f1c5947ace. Its contract is the September 21 DFII10
prospective PIT handoff. It binds source bytes and a conservative capture clock
through existing Transmission and W5. It qualifies a prospective measurement,
not a retrospectively known vintage. Natural production proof is still owed.

Its five-completed-session endpoints use NYSE sessions for an equity-entry
consumer. That is not a bug in its intended scope. Do NOT rename those endpoints
five Treasury sessions. Preserve that consumer and add any rates-specific horizon
through the existing receipt/calendar owners, with explicit basis identity.

These findings are about the inspected candidate revisions, not proof that every
other current source is absent or that live production has the same state.

## Smallest next producer + real-consumer slice

Reconcile the incumbent policy collector's exact current contract, then preserve
instrument identifier, rate family, reference period, settlement/quote convention,
raw implied rate, curve weight, source timestamp, capture timestamp and correction
identity in its existing snapshot. Let the existing fed_path/RIC consumer expose
fixed-period matched-contract repricing separately from rolling-horizon movement.
No second snapshot database, forward-path service, calendar, score or evaluator.

For the same instruments observed at both cuts, the exact symmetric decomposition
is: change in weighted path = sum(average weight * rate change) +
sum(average rate * weight change). The first term is matched-instrument repricing;
the second is reweighting/roll. Missing rates for an entering/exiting instrument
make a complete attribution unavailable; zero-filling would fabricate certainty.
Never blend ZQ/EFFR and SR3/SOFR without an independently qualified basis treatment.

The machine and UI must retain raw movement, matched repricing, roll contribution,
coverage/residual, clocks and reasons for abstention. None is a causal monetary
shock or a forecast probability merely because the arithmetic reconciles.

## Exact collector inspection at the RD1 source revision

`collectors/rate_futures.py` at 8796829eea9fe8792a73155f64d5c1dbe83ae3b6
retains contract identity inside `fetch()` while calculating `implied_path()`,
but returns only the interpolated `*_path` frames. The producer therefore has
an existing, narrow place to preserve source constituents instead of inventing a
second collector. The current path columns do not themselves retain constituent
symbols, weights or reference periods.

`full_history=True` requests five years for the strip generated from today's
live contract months. This method alone cannot reconstruct every expired
historical contract or establish an as-observed historical curve. Do not label
that download a historical PIT policy-path archive. This finding does not claim
that other existing archives are absent; inspect their owner before proposing
backfill or prospective-only coverage.

The helper uses whole-month offsets and cadence-centre assumptions. Before
changing reference-period metadata, verify the official ZQ/SR3 settlement and
reference-period conventions, especially quarterly contract naming; code and
synthetic parity alone do not establish economic correctness.

## Acceptance for the next source slice

Preserve old display numbers where their contract remains valid; version any
necessary semantic correction. Tests must distinguish unchanged-contract prices
with calendar roll, genuine repricing with unchanged weights, simultaneous roll
and repricing, incompatible rate families, missing/expired contracts, stale or
asynchronous observations, duplicate/corrected quotes, and source clock loss.
The same admitted raw quotes must reproduce both the path and its attribution.
Existing RIC must actually consume the result with explicit unknown behavior.
No event probabilities, Fed-intent prediction, equity risk gating or live forecast
promotion is authorized by this arithmetic capability.

Review the source/semantics change separately from RD1's frozen experiment.
Do not mutate held #7521 or #7593, assume their acceptance, or recreate their
receipt owners. The next independent statistical experiment needs a newly
registered construction and a truthful previously-seen/prospective split.
