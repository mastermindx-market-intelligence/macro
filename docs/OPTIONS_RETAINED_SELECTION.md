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
The dataclasses alone are **not** a Python-to-Terminal wire contract. Terminal
consumes only the versioned lossless JSON form below, through Lab's sole adapter.

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
spelling, nanoseconds and exact line bytes. The incumbent exact nanosecond clock
parser compares the ORIGINAL availability and captured-read instants. Shared
microsecond ceilings cannot authorize evidence that actually arrived later.
The incumbent normalized read/cutoff fields remain unchanged. `read_observed_at`
is never relabeled event receipt or durable availability.

`population = individual_aggregate_events` and
`package_support = no_sourced_membership`. No qualified raw package/leg/member,
quantity, deliverable or correction lineage exists in this input. Swept/repeated
badges, proximity, coalescing, caller labels and the producer's fixed-100 premium
arithmetic do not provide it. Such supplied fields stay raw payload, not admitted
package support. No raw-print reconstruction or multiplier inference occurs.
Universe coverage and correction order remain unknown.

## Lossless Terminal wire v1

`encode_retained_matrix(...)` and `encode_retained_events(...)` accept the same
explicit arguments as their corresponding selectors and return UTF-8 JSON
**bytes**. `decode_retained_selection_wire(bytes)` returns a validated JSON-safe
object. These functions are pure projections, not new source readers. They do
not accept a mutated dataclass as authority; they reconstruct from captured bytes.

All objects below have **only** the listed fields. A `?` means the original key
may be absent, distinct from an explicit null. An array is ordered as supplied
by the selector/ledger, never a qualified historical time ordering.

```typescript
// Data numbers are decimal strings. Only bounded structural sizes/indexes are
// JSON integers. Do not convert DecimalToken to Number/parseFloat to establish
// contract identity, counts, clock equality or provenance.
type DecimalToken = string;
type ExactJSON = null | boolean | string
  | { decimal: DecimalToken }
  | { array: ExactJSON[] }
  | { object: Record<string, ExactJSON> };

type Capture = {
  encoding: "base64";
  body_base64: string;       // canonical padded RFC4648 of ORIGINAL bytes
  sha256: string;            // 64 lowercase hex characters
  byte_length: number;      // integer 1..16,777,216; booleans/floats refused
  read_at: string;          // original supplied aware ISO clock, up to 9 decimals
};
type Common = {
  schema: "options.retained_selection.wire/v1";
  capture: Capture;
  decision_at: string;       // original supplied cutoff spelling/precision
  cutoff_utc: string;        // incumbent normalized conservative cutoff
  read_observed_at: string;  // incumbent normalized read; NOT first availability
};
type MatrixWire = Common & {
  kind: "matrix";
  selector: { expiry: string; side: "all" | "call" | "put" };
  snapshot: {
    root: string; session: string | null; sha256: string; byte_length: number;
    version_ref: string; key: string;
  };
  rows: {
    expiry: string; strike: DecimalToken; side: "call" | "put";
    cell_index: number;       // nonnegative source cell-array index
    metrics: {
      open_interest?: ExactJSON; volume?: ExactJSON;
      delta_oi?: ExactJSON; unusual?: ExactJSON;
    };
  }[];
  document: ExactJSON;       // lossless original full Matrix document
  state: {
    selection_mode: "known_snapshot_only";
    row_status: "supplied_observations" | "no_supplied_observations";
    first_available_at: null; history_order: null; correction_order: null;
    universe_coverage: null; gap_interpretation: "missing_is_unknown";
  };
};
type EventWire = Common & {
  kind: "events";
  selector: { session: string; root: string; event_ids: string[] | null };
  source_stage_key: string;
  records: {
    event: ExactJSON;         // exact ORIGINAL decision payload, not float projection
    decision_at: string;      // incumbent normalized decision clock
    available_at: string;    // incumbent normalized durable-availability clock
    source_available_at: string;  // original availability spelling/nanoseconds
    source_availability_receipt_base64: string; // exact original receipt line
    source_stage_key: string; source_stage_schema: "live_flow.event_stage/v1";
    source_stage_prefix_records: number; // positive availability-line ordinal
    source_stage_prefix_sha256: string;
  }[];
  state: {
    population: "individual_aggregate_events";
    package_support: "no_sourced_membership";
    universe_coverage: null; correction_order: null;
  };
};
type SelectionWire = MatrixWire | EventWire;
```

`ExactJSON` has an unambiguous tag for numbers **and** containers. For example:

```json
{"open_interest":{"decimal":"9007199254740993"},"volume":null,"delta_oi":{"decimal":"-2.5"}}
```

The source string `"12"` remains a string; source number `12.0` becomes
`{"decimal":"12"}`; a source object `{"decimal":"12"}` becomes
`{"object":{"decimal":"12"}}`. No array/object/string can masquerade as a
number. Number tokens use the incumbent exact canonical Decimal formatter:
plain notation, no exponent, leading plus, redundant leading/trailing zero or
negative zero. Zero is `"0"`. Strike tokens additionally obey the incumbent
positive coordinate bounds. No numeric source field passes through binary float.
For events, the original paired-stage reader validates the stage first; the same
decision-line bytes are then decoded with the incumbent exact-number decoder.
`event` contains the original decision payload; durable availability remains in
the separately named receipt fields, not merged into an invented source event.

Bounds are part of v1: captured body at most 16 MiB; encoded wire at most 64 MiB;
at most 2,000,000 wire JSON values and 64 wire nesting edges; at most 24 original
source-tree nesting edges. Numeric plain expansion is bounded **before** any
formatting allocation to 128 characters (zero canonicalizes directly). Large
exponents and oversized/deep payloads refuse, never truncate or round. Structural
lengths/indexes/record counts are bounded integers safely below `2^53`, not data
metrics. No other JSON numbers are permitted outside these declared fields.

Decoding is validation, not trust in the parsed metadata:

1. Require bounded UTF-8 bytes, strict JSON with no duplicate keys/nonfinite
   constants, exact version/kind and tree bounds.
2. Decode canonical base64, enforce captured byte length, then run the incumbent
   digest/read-clock/reference/session/coordinate or paired-stage validation.
   Event availability must not exceed the original captured-read instant at
   nanosecond precision, even when both share the same rounded microsecond.
3. Rebuild the complete expected v1 projection from those captured bytes and the
   explicit selector/cutoff. Compare canonical JSON bytes for **all** fields,
   rejecting missing nulls, extra fields, decimal spelling changes, float values,
   booleans in integer slots, altered metadata, references, receipts and unknowns.
4. Return JSON-safe tagged values. Successful roundtrip proves structural
   consistency with the captured input, not authenticated access or permission.

Lab's TypeScript adapter must enforce this same closed schema/limits, canonical
base64 and digest/length binding before use. It must retain decimal tokens and
raw capture authority; parsing the original Matrix JSON into ordinary JavaScript
numbers is not an exact-value decoder. A compatible trusted encoder's output is
still not a runtime acquisition grant. Lab owns any narrowly necessary display
conversion and mounted selection behavior; this producer does not change it.

## Acceptance and effect boundary

`tests/test_options_retained_selection.py` exercises selected bytes, provenance,
zero/null/missing/precision, clocks, absent populations, root/ID isolation,
append-stable prefixes and false package claims under a socket fence. Existing
retention and FS-5 receipt suites remain affected dependencies. No identity/IW2
persistence, Lab UI, authentication, handler, archive publisher or runtime source
is edited. Synthetic contract checks do not qualify a live source, complete Lab
Stage E, A/B/C, commercial enrollment or a scientific trial.
