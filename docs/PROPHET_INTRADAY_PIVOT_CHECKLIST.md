# Prophet US intraday pivot checklist

This addition puts 3-hour structure, 30-minute pivot conditions, larger-timeframe
context, observation history and source clocks beside the existing US Stocks
turn-setup roster. It is an observation surface. Its authority is always
`may_rank=false, may_gate=false, may_size=false, may_trade=false`.

## Draft delivery status — unfinished

The collector extension, publication integration and actual dashboard surface are
implemented. Their conformance tests use synthetic inputs and stubbed network
boundaries. The pure causal evaluator is assigned to the existing paid Fabric run
`prophet-us-pivot-engine-20261104-c3`; its return has not been reconciled at this
checkpoint. The optional integration therefore fails to an explicit unavailable
envelope if that evaluator is absent or fails.

No production timer, collector invocation, service, R2 object, source qualification,
entry-availability owner or deployment has been changed. A new source file or a
passing test does not establish live coverage or entry efficacy.

Draft [PR #10715](https://github.com/mastermindx-market-intelligence/macro/pull/10715)
contains this partial implementation. The separate health projection return also
remains unverified; it is not included or active.

The governing outcome and current frontier are in
[the source plan](../research/prophet_v4/INTRADAY_PIVOT_CHECKLIST_2026-11-03.md).
Do not enable a fabricated input envelope to make the surface look complete.

## User workflow

1. Keep the existing D / 3D / W / 2W and monthly view as the parent context.
2. Inspect the separate 3H and 30m chips. Unknown evidence remains unknown.
3. Open the timing detail. It mirrors the owner's existing larger-timeframe display,
   then shows trigger, distance, invalidation, extension limit and individual rules.
4. Compare the bar close, quote time, assessment time and condition-first-known time.
   A delayed observation does not become real time because the page refreshed.
5. Inspect recent observations for transitions and corrections. These are observations,
   not submitted orders, fills, position entries or recommendations.

The modal uses the browser's native focus handling and Escape behavior, preserves
focus across refreshes, closes when the access tier changes, and leaves the roster's
first-12 fold behavior intact. The mobile disclosure scrolls. English/Chinese and
light/dark treatments use the existing page's language and theme system.

Nightly context is explicitly dated. It does not silently become a fresh parent
availability verdict.

## Existing owners and seams

| Concern | Owner / integration |
|---|---|
| Larger-timeframe display | `engine/mtf_upturn.py` and the existing roster renderer |
| Entry geometry and eligibility | `engine/entry_signal.py`, `engine/prophet_entry_availability.py` and their native source owners |
| Source acquisition | Existing `scripts/build_polygon_intraday.py` |
| Evaluation and publication | Existing `scripts/prophet_live_evaluator.py` and `engine/prophet_live/` |
| Public payload | Nested `pivot_checklist` in the existing `live/prophet_live.json` artifact |
| Observation persistence | Sibling `pivot_events` in the existing per-pass `prophet_live.events/v1` spool |
| Recent visible history | Bounded, derived `recent_events` projection inside that same artifact |
| Frontend refresh | Existing Prophet Live client; no new request loop or network client |
| Input projection | Private owner-produced envelope selected by `prophet_live.pivot_input_path` |

The default input projection path is
`/var/lib/macro-live/state/prophet_pivot_inputs.json`. Its schema is
`prophet.pivot_inputs/v1`. This reader is not its producer, an identity owner or an
admission authority. An empty configured path explicitly disables reading.

The existing quote view's `basis` field describes the vendor quote rung, such as
trade/minute/regular. It is not an adjustment basis. The checklist receives quotes
only from the qualified input envelope, with an explicit `basis_id` and native
timestamp; it never copies a rung into an adjustment identifier.

## Input contract to be supplied by the existing owners

An input projection must bind:

- The schema, generation time, expiry, source receipt, declared delay, observed versus
  synthetic input kind, and source qualification verdict.
- An exchange-session receipt with session date, actual open/close, and when those
  calendar facts became available. An early close is not a normal 16:00 session.
- Each stock's setup, canonical security identity, identity epoch and price basis.
- A parent validity verdict with receipt, source time, known time and validity window.
- Frozen pivot identity, trigger, invalidation and upper entry boundary with their own
  basis, receipt, known time and validity window.
- Closed 3H and 30m aggregates from the existing qualified aggregation owner, including
  interval boundaries, completeness/coverage, OHLCV, basis, source receipt, revision
  and actual known time.
- Quotes with price, native timestamp and an explicitly matching basis.

`source_admitted=true` is an owner attestation, not an operator feature flag.
Synthetic fixture values must never be installed into the live projection.

The integration rejects oversized input (over 4 MiB), malformed JSON, nonfinite
numbers and wrong schemas. Optional evaluation errors produce
`pivot_evaluation_failed`, no current positive rows and no new pivot event. They do
not disable the incumbent quote pass. The completed optional envelope is checked
for schema, false authority, size, event identity and JSON serializability before it
can join the public artifact.

## Causal acceptance rules

- Current prices can test or invalidate a pivot. A quote cannot establish a closed
  30-minute condition.
- A normal regular session has two full 3H intervals from its open. Its final short
  remainder cannot be presented as a full 3H candle. Do not pad absent trading bars.
- A prior session's last full 3H bar can be an explicitly receipted comparison
  baseline for the current first full 3H bar. This does not establish survival
  through the intervening remainder, overnight gap or missing observations.
- Filter facts by their known time before interpreting their payload. Later
  corrections must not leak into earlier prefix replays.
- Keep the price/bar event time separate from the time the combined condition could
  first be known. Never backdate entry availability.
- Keep individual observations visible when qualified bar evidence exists but a
  parent or level owner is unavailable. Overall availability remains unavailable.
- A single OHLC candle spanning both trigger and invalidation cannot establish their
  order. Such ambiguity is explicit.
- Frozen pivot changes require explicit supersession. A changed quote alone does
  not create another event or another pivot.
- Missing/stale evidence cannot clear a prior invalidation or restore a positive
  current state. A correction must name the evidence it changes and remain auditable.
- Historical condition evidence, current monitoring eligibility and trade admission
  are separate. No observation state overrides a failed native parent gate.

These rules are not a claim that the strategy has an accepted statistical edge.
Any promotion must use the existing entry-timing validation programme and its
accepted cohort, identity, availability and outcome contracts.

## Source capture extension

The incumbent aggregate collector accepts optional `multiplier`, `timespan` and
`retain_observations` arguments. Its default invocation keeps its configured
hourly cadence, v1 price receipt and no-retention behavior.

A different cadence requires an explicit compatible output directory. Retention
also requires an explicit compatible directory, including at the hourly cadence.
This invocation cannot convert an existing v1 store to v2 or downgrade a v2 store.
Cadence and receipt-contract conflicts are refused before any vendor call or write.

With retention enabled, each nonempty aggregate result is preserved under
`<out_dir>/observations/<ticker>/<sha256>.json`. The capture contains exact aggregate
records, query bounds, basis, declared 15-minute delay and the actual post-response
observation clock. It is not a raw HTTP-response archive or proof of every minute's
trading coverage.

Captures are content-addressed and published without replacing an existing name.
A differing file at that name is a refusal. Later revisions retain earlier captures.
The v2 price receipt binds the capture digest and availability time to the exact
fsynced parquet digest. Regressing clocks are refused; they are never clamped or
inferred from the candle end. Empty or failed responses do not refresh a prior
receipt.

No new scheduler or production cadence is installed. A future approved 30m
invocation belongs inside the existing source owner and orchestrator, after capacity,
entitlement and data qualification are verified. Hourly data must not be upsampled
into invented 30m coverage.

## Observation history and publication failures

The required causal-engine contract uses stable semantic event IDs and preserves
source clocks, pivot identities and correction links. Its implementation and
acceptance remain outstanding. The implemented wrapper deduplicates received IDs
and projects the latest 64 events; the UI displays up to six per stock and labels
corrections and earlier pivots. This projection does not prove that the missing
producer has generated causal, correction-safe observations.

The nightly incumbent reconciler reads only the spool's `events` array.
`pivot_events` are deliberately outside that array: timing observations must not
enter the incumbent trade-return grader as if they were its forming/cross events.

The incumbent artifact, served-copy and spool publication behavior remains distinct.
A spool write failure is reported with the pivot-observation count and preserves
the existing required-publication failure status. Seeing a current observation on
the page is not proof that its spool write succeeded.

## Outstanding activation requirements

1. Obtain and qualify current intraday coverage through the existing source and
   aggregation owners, including identity, basis, correction history and exchange
   session receipts.
2. Supply native parent and level evidence. At the checked source baseline,
   `prophet_b4_same_read.py` deliberately supplies empty native geometry/metric
   inputs and returns unavailable; its capture-only stream cannot be repurposed
   as a live input source.
3. Finish the exact existing causal-evaluator return and its adversarial verification.
   Do not duplicate that uncertain execution.
4. Reconcile the original health-projection return and prove freshness through the
   existing health owner before claiming continuous monitoring.
5. Complete source review/CI and the authorized release path. The assigned session
   does not self-approve or self-merge.
6. Verify the deployed commit, actual monitor cadence, receipt freshness, correction
   behavior and entitled browser path. The attempted read-only runtime inspection
   was refused by SSH public-key authentication; no runtime facts were obtained.

## Verification and rollback

Run the focused suites for source capture, pivot integration/surface, existing live
evaluation, VPS publication and nightly reconciliation. The browser runner is:

```sh
python -m scripts.capture_prophet_pivot_checklist --out <proof-directory>
```

It renders the actual stocks template, intercepts all network traffic locally, and
uses a simulated Pro session. Its receipt says `SYNTHETIC_CONFORMANCE`,
`market_data_proof=false` and `production_delivery_proof=false`.

To disable the optional read, set `prophet_live.pivot_input_path` to an empty string
through the incumbent configuration owner. Do not delete historical observations
or change the existing quote monitor, publication keys, access policy or timer.
