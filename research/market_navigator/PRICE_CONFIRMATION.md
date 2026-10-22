# W3: Completed-bar price confirmation

Status: **BUILT_NOT_PROVEN** in a live source/client path. Research-only,
non-predictive descriptive subengine; explicitly no trading authority.

## Purpose

A single spot quote crossing 773, 775, 780, or another price level does NOT
establish a completed-bar breakout, sustained hold, reversal, head-and-shoulders
confirmation, or available options entry. This module adds a strict, deterministic
description of *current completed-bar closing evidence* for previously defined
price levels. It makes the false confirmation case observable without assuming
one price quote or a pattern-drawing chart is a trading signal.

The source owner, not this module, determines exchange calendar, instrument
identity, bar completeness, revisions, source-use rights, storage and true
availability. The module reads no market vendor, chart, screenshot or file.

## Typed contract

- `ClosedBar`: owner subject, horizon, exact generation, immutable bar receipt
  and revision, calendar session, owner sequence ordinal, OHLC, UTC measurement
  period, first actual availability, revision validity and completion.
- `LevelRule`: original owner-aligned subject, horizon, single event
  (`cross_above`, `cross_below`, `hold_above`, `hold_below`), exact level,
  unit, count of 2-16 completed bars, original rule reference, definition
  availability and exclusive deadline.
- `inspect`: exact `as_of`, ordered tuple of at most 64 typed bars, explicit
  latest expected owner sequence and application-bound owner verifier.

The verifier is a normal dependency supplied by the incumbent application
source owner. It must inspect original receipt bytes/generation membership,
calendar ordinals and rights; it is never accepted from HTTP, a model, an
analyst, user input or another mutable summary. Test lambdas deliberately do
not establish real source proof.

An upward cross requires the bar immediately before the last N bars to close
at/below the level, followed by N consecutive *strictly above* closes. A
downward cross is symmetric. A hold requires N consecutive strictly
above/below closes without inferring an earlier crossing. Equality does not
establish confirmation. No wick, volume, Greek, dark-pool or intraday path
claim is derived from these closing relationships.

The module requires exact source generation identity, gap-free owner
sequence ordinals, no overlapping measurements, latest expected bar and
fully completed/available/nonexpired revisions. Intraday confirmation does
not cross an overnight or new-session boundary. Daily/swing bars may cross
weekends when the incumbent calendar supplies consecutive session ordinals.
Future-unavailable, stale, incomplete, mismatched, mixed-generation or
missing data return explicit unresolved states; nothing converts absence
into zero or backs into a last-known snapshot. The original level-rule
availability must not be later than the decision cutoff.

Outputs bind subject, source generation and definition through SHA-256
descriptors, not raw owner references. They carry no source paths, text
corpora, probabilities, trade actions or ranking. A confirmed event is
a **condition observation**, not a prediction.

## Composition bridge

`qualified_observation` can provide a binary, dimensionless Observation to
existing `engine.market_navigator.compose` only when a bound owner verifier
returns exactly True and an independent derived Receipt agrees with the last
completed bar, generation, latest source availability and no-extended
revision expiry. 1.0 = defined completed-bar event established; 0.0 = event
not established. The `ratio` unit is a binary event measure, never a
calibrated probability. Ineligible inputs return no observation, not 0.

The caller supplies its original Scenario, `Condition("confirmed_reclaim",
"gte", 1, "ratio")`, actual rule availability, deadline and invalidation.
The compositor remains the authority for missingness and statuses; all
seven initial authority flags remain false. Nothing manufactures a
new scenario, original forecast or dealer narrative from the bar record.

## Verification

`python -m pytest tests/test_market_navigator_price_confirmation.py -q`:
64 focused cases pass using only synthetic bars/fixtures. They include a
completed genuine *mathematical* cross followed by an actual existing
compositor evaluation, no-source verification, future receipt, mixed
generation, subject, horizon, cross-session, partial bar, missing latest
bar, strict equality, unit mismatch, deadline and derived-receipt
fail-closed behavior.

Remaining production integration requires: a real incumbent bar reader with
source-use permission, exact owner calendar and full capture lineage,
reviewed verification callback, server-side source authorization, a coherent
source generation, signed-in query proof and a separate release review.
This source is NOT yet live, backtested, Paper-applied, or predictive.
