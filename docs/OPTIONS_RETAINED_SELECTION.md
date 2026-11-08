# Retained Options selection input for Lab

`engine.options_retained_selection` composes existing pure readers. Lab owns
the adapter/UI integration. This contract does not add a reader service, endpoint,
store, catalog, acquisition, publisher, collector or installation.

## Caller and input custody

The assigning reader supplies an existing `IdentityArtifactRead(body, sha256,
read_at)` over **already captured original bytes**, plus an explicit aware
`decision_at` cutoff. The incumbent capture validator binds the digest, the
16 MiB bound and `read_at <= decision_at`. These are structural checks, not
authentication: the caller must retain the original capture/permission evidence.
Do not mint a capture from a mutable head, reconstructed JSON, fixture, new clock
or a new runtime request to satisfy this interface.

There is no implicit current time. A read observation is not first availability,
event time, publication time, trading session or correction order. Returned
dataclasses describe a detached in-process view; the original `capture.body`
remains the byte authority. They are not mutable shared-cache entries. Reuse the
incumbent selection/cache path when integrating; do not introduce another cache.

## Matrix: explicit known snapshot

```python
from engine.options_retained_selection import select_retained_matrix

selection = select_retained_matrix(
    snapshot_reference,       # existing SnapshotReference, never a mutable head
    captured_matrix,          # existing IdentityArtifactRead
    decision_at=decision_cutoff,
    expiry="2026-10-30",      # exact Gregorian expiry
    side="all",              # all | call | put
)
```

`selection.reference` preserves the incumbent root, session, SHA256, byte length,
`version_ref` and exact immutable history key. The incumbent verifier fails on
wrong bytes/root/session/length/digest, ambiguous coordinates or malformed
observation counts. It never falls back to the current Matrix.

`rows` contains exact `(expiry, strike, side)` coordinates and the source cell
index. Strike tokens and numeric metrics use the incumbent lossless Decimal
decoder. Do not serialize Decimal through float. Each row exists only when that
side supplies nonnull OI or volume, **including zero**. Missing metric keys,
explicit nulls and numeric zero remain distinct. An absent expiry/side returns
`no_supplied_observations`; it does not synthesize cells. Rows carry only supplied
own-side OI/volume/delta-OI/unusual values. Aggregate GEX/VEX/levels are preserved
in `document`, never divided into invented side values.

`document` retains every supplied source field, including `_build_meta`, build
`asof`, source session, EOD/Greeks/OI publication dates, coverage, gaps, correction
or availability claims. They retain their original scope; a supplied arbitrary
field does not become certified history metadata. `capture.body` preserves exact
JSON spelling/order/bytes. This contract exposes:

- `selection_mode = known_snapshot_only`;
- `first_available_at`, `history_order`, `correction_order`, `universe_coverage`
  are unknown (`None`);
- `gap_interpretation = missing_is_unknown`.

No authoritative ordered history index or first-availability evidence has been
qualified. Build/read clocks and digest lexical order must not drive playback.
The Matrix session and OI publication date are separate from both clocks.

## Events: exact captured dated decision ledger

```python
from engine.options_retained_selection import select_retained_events

selection = select_retained_events(
    captured_stage, session="2026-10-19", root="SPY",
    decision_at=decision_cutoff,
    event_ids=("known-event-id",),  # optional; absent means all supplied root rows
)
```

The only accepted source is the incumbent paired `live_flow.event_stage/v1`
JSONL for `live_flow/events/{session}.jsonl`. `parse_stage_bytes` validates the
whole captured stage before selecting a root/known IDs: torn lines, duplicate or
unpaired decisions, incompatible sessions and causal clock order fail closed.
Unknown/duplicate selected IDs refuse. The mutable capped feed is no substitute.

Each returned record keeps the incumbent event payload and byte-prefix receipt:
source key/schema, availability-line prefix record count and original-prefix
SHA256. Appending later events changes the full capture digest but preserves an
existing event's prefix identity. Ledger order is receipt order, not an asserted
market-time ordering or complete-session coverage.

The event `ts`, `observed_at`, `decision_at`, OI dates/values and other source
fields remain separate. The incumbent parsed `available_at` is a normalized
microsecond representation. `source_available_at` and
`source_availability_receipt` additionally preserve the original availability
spelling, nanoseconds and exact line bytes. The shared conservative clock parser
checks the original availability against captured read time. `read_observed_at`
is never relabeled event receipt or durable availability.

`population = individual_aggregate_events` and
`package_support = no_sourced_membership`. No qualified raw package/leg/member,
quantity, deliverable or correction lineage exists in this input. Swept/repeated
badges, proximity, coalescing, caller labels and the producer's fixed-100 premium
arithmetic do not provide it. Such supplied fields stay raw payload, not admitted
package support. No raw-print reconstruction or multiplier inference occurs.
Universe coverage and correction order remain unknown.

## Acceptance and effect boundary

`tests/test_options_retained_selection.py` exercises selected bytes, provenance,
zero/null/missing/precision, clocks, absent populations, root/ID isolation,
append-stable prefixes and false package claims under a socket fence. Existing
retention and FS-5 receipt suites remain affected dependencies. No identity/IW2
persistence, Lab UI, authentication, handler, archive publisher or runtime source
is edited. Synthetic contract checks do not qualify a live source, complete Lab
Stage E, A/B/C, commercial enrollment or a scientific trial.
