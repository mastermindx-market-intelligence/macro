# Genuine member OHLCV private generation

Status: source-qualified, not activated. Base `bb107bccc52152d46b5ee91865632a22bced6e20`.
Governing [Macro #10779](https://github.com/mastermindx-market-intelligence/macro/issues/10779);
carrier [#10780](https://github.com/mastermindx-market-intelligence/macro/pull/10780);
protected Mastermind law `49c2e1d93e5e080b1671c98087a845e5beb09dd5`.

## Existing owners and new boundary

The incumbent genuine five-field acquisition returns `BasketOHLCVAcquisition`.
The new bounded contract in `lib/member_ohlcv_generation_contract.py` encodes that
captured result and its actual prior into the existing generation publisher:

| Member | Meaning |
|---|---|
| `members/open.parquet` | Genuine adjusted opens |
| `members/high.parquet` | Genuine adjusted highs |
| `members/low.parquet` | Genuine adjusted lows |
| `members/close.parquet` | Genuine adjusted closes |
| `members/volume.parquet` | Corresponding provider volume |
| `acquisition.json` | Exact breadth dependency, policy/prior identities, acquisition classifications and per-field evidence |

Domain `sector-member-ohlcv`, receipt `sector_member_ohlcv.v1`. The generic
publisher's existing manifest/content identity and compare-and-select operation
remain the publication authority. No provider call, new store, scheduler, selector,
public endpoint, history writer or deployment is added.

The shared primitive panel codec now accepts the genuine open field. The breadth
domain itself retains its exact four-field population and fixed nineteen members.
A new breadth snapshot verification entry rechecks the incumbent content identity
and derives values from those captured bytes; a previously mutated derived frame or
membership dictionary is not authority.

## Admission and retention

The acquisition requested population must match the captured breadth membership.
Type, size, uniqueness and exact population are checked before constructing panel
axes. Existing provider-alias uniqueness, US cash identities, actual five-field
geometry, nonnegative volume, observed dates and interior gaps are preserved.

The new encoder preserves prior columns removed from the requested population as
`archive_only`. They are not requested, acquired or current. Failed replacements
retain exact prior observations in all five fields. Accepted full replacements must
contain every prior observed date, without a new blanket depth floor for an IPO.

All five selected field tips must agree for an accepted replacement. Only a tip
equal to the completed-session target is a current acquisition. An accepted older
history remains `historical_only`. Retained values carry `not_requalified`, even
if a retained bar happens to reach the target.

Partial and unavailable acquisitions remain truthful publishable input evidence.
`require_current=True` establishes target-session/dependency validity; it does
not assert all symbols have current candles. The full Sector adapter must preserve
these classifications and apply its incumbent consumer requirements.

Exact prior bytes are rechecked during final publication admission, including
retained generation provenance where available. The selected reader checks current
bytes, receipt and dependency semantics without recursively revalidating every
historical prior generation. The acquisition's discarded response summaries remain
producer evidence; the reader cannot reconstruct a rejected provider response from
the selected bars.

A bootstrap capture must explicitly supply all five canonical prior panels or
observed absence of all five. It is not a legacy-store reader. Binding original
legacy file captures and genuine policy source bytes remains the capture adapter's
obligation; this source package does not manufacture bootstrap provenance.

## Clocks, dependency and bounds

The exact captured breadth dependency includes original publication, source revision,
content identity and member hashes, and retains its pinned Yahoo dependency.
Breadth publication, prior capture and policy capture precede acquisition evaluation;
evaluation precedes preparation, which precedes actual publication. New admission
rechecks the current completed-session target, including when an existing immutable
generation is reused. Recovery may explicitly read historical captures without
restamping their original publication.

The reader requires the already captured breadth/Yahoo pair. It reads one selected
OHLCV snapshot and never replaces either dependency by rereading a current pointer.
`read_sector_member_ohlcv_capture` extends the existing Sector capture owner with
that exact binding.

The fixed set is limited to 64 MiB per member and 384 MiB total encoded bytes.
The existing shared codec enforces 50,000 rows, 5,000 columns, 5 million cells,
8 MiB footer, primitive schema, 32 row groups and 64 MiB per decoded panel.
Prospective allocation across all five panels is checked before decoding, with
a 256 MiB limit. Common axes and joint geometry are then validated.

## Proof and remaining work

The final affected run passed **130 tests**, including the new 36-test contract
suite, the breadth contract and incumbent genuine acquisition tests. The earlier
31-test run also passed; counts overlap. An advisory source review identified an
encoder population check that needed to precede panel allocation. That correction
and four rejection regressions are included in the final run.

Tests cover actual private publication/readback, the existing price-pair binding,
missing fields, impossible candles, unavailable input, exclusions, short histories,
historical-only results, unchanged failed replacements, archive preservation,
prior hash/content mismatch, mutable derived breadth values, corrupt captured bytes,
declared allocation before decoding, stale reuse, retained original publication,
and the original publisher's selection fence.

[Exact commands, hashes and receipts](SECTOR_MEMBER_OHLCV_GENERATION_SOURCE_REVIEW_2026-11-06.json).

No new provider traffic, production activation or authenticated beta proof occurred.
The complete auxiliary/holdings capture and composition adapter, updater barrier,
application/native consumer, protected CI/release, sole-writer transfer and family
rollout remain open. The protected holdings result and recorded CI/Terminal/browser
capability fences remain unchanged.
