# Explicit sponsor holdings capture

The existing `SectorHoldingsAdapter` now returns workbook-bound inputs for the
Sector assembler without invoking the legacy configuration loader, parquet
reader, store/history writer or current-date fallback.

## Calling contract

```python
result = SectorHoldingsAdapter.capture_from_inputs(
    sponsors=captured_config["sponsors"],
    evaluated_at=evaluation_instant,  # aware datetime
    clock=observation_clock,          # sampled after each acquisition
)
arguments = result.assembly_arguments()
# {"holdings": detached per-fund frames/None,
#  "holdings_evidence": detached per-fund observation facts}
```

Sponsor choices are detached once before acquisition. They must contain one to
eleven unique uppercase fund identifiers. The full Sector assembler separately
requires an explicit observation for each of its eleven configured funds.

Each attempt uses the existing HTTP/retry owner and exact SSGA URL. Its existing
three retries, 60-second request timeout and retry backoff remain intact. The
shared HTTP helper now loads its default User-Agent configuration only when the
caller has not supplied User-Agent; an already supplied header no longer causes
an unused ambient configuration read. There is no second HTTP/retry owner.

The result exposes fresh copies through `snapshots`, `evidence` and
`assembly_arguments()`. `workbooks` returns a detached mapping of immutable
captured byte strings. Failed funds have no snapshot. `available` is false when
all funds fail; it does not mean all eleven funds succeeded.

## Identity, dates and missingness

Successful evidence includes the exact workbook SHA-256 and byte length, origin
URL, actual document date, supplied evaluation instant and observed capture time.
The workbook remains available as bytes. Publication time is explicitly unknown.

The strict parser requires a complete calendar date in the actual As-of label.
It accepts full ISO, US numeric and complete English month-name date forms; it
does not infer a missing year, month or day. Missing, invalid, ambiguous or
future document dates fail. The date limit uses the incumbent US market-local
calendar-date owner, not a completed-price-session stamp. Older documents retain
their individual older dates. No maximum across funds is presented as a shared
document date.

Per-fund outcomes distinguish present, absent HTTP404, unreadable acquisition and
malformed captured input. Failed acquisition does not silently reuse an ambient
prior snapshot. Malformed bounded workbook bytes retain their observed identity;
oversized or non-byte input is refused before parsing and is not retained as a
qualified workbook.

The shared transform preserves the original header discovery, ticker/name
handling, real tickerNA, numeric weight coercion, top20 ordering/ties, rounding
and ranks for valid inputs. Strict capture additionally rejects ambiguous
headers/columns, duplicate identities, invalid/non-finite/out-of-range weights
and an empty effective snapshot. Zero weights remain present values. Legacy
`fetch`, `_fetch_fund`, store/history writes and `latest_top10` retain their APIs;
the legacy missing-date fallback remains confined to that legacy path.

## Resource and isolation contract

Before strict Excel parsing, the owner checks the8MiB encoded bound,256-member
ZIP bound,32MiB expanded bound, duplicate/unsafe archive entries, DTD/entity
declarations and worksheet geometry. Limits are10000rows,64columns and200000
observed cells. The real pandas/OpenXML parser then performs the shared
transformation. No archive is extracted to the filesystem.

The explicit path requires aware evaluation/capture instants and a monotonic
observation clock. It does not call `date.today()`, the legacy constructor,
ambient config/store readers or history writers.

## Qualification and remaining runtime work

The test-only legacy transform is pinned to Macro
4eddd4ad83f761d4178e1faa73173dccd71ed419. Controlled workbook bytes pass through
the actual Excel parser and exact top20 transform. Five incomplete-date cases
failed before the strict-date correction. Focused cases exercise parity,
identity/clocks, detachment, partial/all-failed outcomes, bounds, actual shared
HTTP retry behavior and default-header compatibility.

The existing integration test now captures workbook bytes for all eleven funds
through this owner, then runs the actual local-input reader, assembler, all five
document builders, incumbent private publisher and mounted API for preview and
entitled audiences. Upstream responses and identity lookups are controlled;
this is not a live provider or authenticated production receipt.

The original Fabric attempt returned a thermal admission refusal before worker
execution; its retained request/control effects and retry restriction remain.
The assigned principal completed this source leaf directly in the original
workspace. [Original-run reconciliation](https://github.com/mastermindx-market-intelligence/macro/pull/10780#issuecomment-6706865038).

This value API does not install an active refresh, publish a generation or supply
an overall snapshot deadline. Runtime integration must qualify the existing
shared service budget and native Yahoo/breadth/member generations before adding
live all-fund acquisition. The per-request HTTP timeout is not an overall
eleven-fund wall-time guarantee. No provider request was made during this source
implementation or its tests.
