# Portfolio brief snapshot witness — exact wire schema

The producer half of the Portfolio brief snapshot contract. This file records
the EXACT wire fields of the opted-in response, so the Terminal-side consumer
can be written against something fixed rather than something inferred.

## The opt-in

```
GET /api/portfolio/brief
X-Mastermind-Portfolio-Context: snapshot-v1
```

The header selects a RESPONSE CONTRACT. It grants no authority: the owner is
the authenticated session, the entitlement gate is the existing Pro gate, and
both run before any private read. A request WITHOUT the header is an ordinary
request and keeps the exact legacy loader, cache and response. An
unsupported header value is refused with
`400 {"detail": {"error": "unsupported_portfolio_context"}}` rather than
answered with an ordinary response a caller would read as a witness.

## The response

The opt-in response is the ordinary `portfolio_brief.v2` payload PLUS one
additive top-level key. The brief itself is unchanged.

```jsonc
{
  "schema": "portfolio_brief.v2",
  "...": "the unchanged brief",
  "portfolio_context": { /* the witness, below */ }
}
```

## `portfolio_context` — schema `portfolio_snapshot_witness.v1`

| field | type | meaning |
|---|---|---|
| `schema` | string | always `portfolio_snapshot_witness.v1` |
| `owner_id` | string | the AUTHENTICATED owner (session id, else session email). Never a request-supplied value. |
| `population` | string | `positions` or `watchlist_union`. The two are distinct books; a union never qualifies as a positions book. |
| `rows` | array of object | the COMPLETE captured raw `portfolio_positions` rows, VERBATIM — open and closed. The ten captured fields are `id`, `ticker`, `shares`, `entry_price`, `entry_currency`, `entry_currency_basis`, `entry_date`, `notes`, `status`, `created_at`. Values are never coerced, never rounded and never re-serialised into another shape. |
| `selected_position_ids` | array of string | the ids of the OPEN, positionable rows — Terminal's canonical open membership (`closed` only for a trimmed+lowercased `closed`; anything else reads open). Empty for `watchlist_union`. |
| `composer_input_source` | string | `positions` or `watchlist_union` — which population the composer was actually called with. A consumer MUST NOT read a `watchlist_union` witness as a positions book. |
| `composer_inputs` | array of object | the EXACT rows the unchanged composer was called with: `ticker`, `shares`, `entry_price`, VERBATIM from the captured rows. Present so a consumer can check ACTUAL INPUT COMPATIBILITY (not merely selected-ID equality) against its own `rowToPosition` projection. |
| `completeness` | object | the proof that the capture was complete — see below. |

### `completeness`

```jsonc
{
  "source": "portfolio_positions",
  "exact_count": 3,          // the total the SAME response stated
  "range_first": 0,          // the start of the returned range
  "range_last": 2,           // the end of the returned range
  "returned_count": 3,       // the rows actually returned
  "open_count": 2,           // the rows the canonical open rule selects
  "selected_count": 2,       // the open rows that also qualify as positions
  "max_rows": 1000,          // the hard cap on one read
  "positions_reads": 1,      // exactly one positions read was made
  "complete": true,
  "watchlist": null          // or the watchlist union's own completeness
}
```

Every number comes from the SAME response. `exact_count` and the range are
PostgREST's `Content-Range` for that one request; there is no second read and
no pagination stitched together. `watchlist` is `null` for a positions book and
otherwise carries the union's own `lists`/`symbols` completeness plus its
`reads` count.

## When there is no witness

An opted-in request that cannot be witnessed fails CLOSED. It never returns an
unwitnessed brief, and it never returns an empty book for an unknown one.

```
503 {"detail": {"error": "portfolio_snapshot_unavailable", "reason": "<reason>"}}
```

| reason | meaning |
|---|---|
| `transport_failure` | the private store did not answer |
| `store_not_configured` | the service-role transport is not configured |
| `missing_count` | the response stated no total — completeness cannot be proved |
| `count_mismatch` | more rows exist than came back: the read was truncated |
| `over_limit` | the book exceeds the 1000-row cap |
| `invalid_range` | the returned range does not describe the rows that came back |
| `nonzero_start_range` | the range does not start at zero |
| `duplicate_ids` | two captured rows share an id |
| `not_json_safe` | a captured value is not representable as strict JSON |
| `unsupported_numeric_magnitude` | a numeric column overflows the Python composer |
| `non_finite_numeric` | a numeric column reads as Infinity/NaN |
| `ticker_mismatch` | the two readers read the ticker differently |
| `shares_mismatch` | the two readers read `shares` differently |
| `entry_price_mismatch` | the two readers read `entry_price` differently |
| `row_dropped_by_terminal` | the composer counts a name the Terminal cannot see |
| `watchlist_*` | the union's own read failed or could not be proved complete |

## A captured example

A real response from the implemented producer (synthetic rows, synthetic
owner):

```json
{
  "schema": "portfolio_snapshot_witness.v1",
  "owner_id": "u-example",
  "population": "positions",
  "rows": [
    {
      "id": "11111111-1111-4111-8111-111111111111",
      "ticker": "NVDA",
      "shares": 10,
      "entry_price": 100.0,
      "entry_currency": null,
      "entry_currency_basis": null,
      "entry_date": "2026-01-15",
      "notes": null,
      "status": "open",
      "created_at": "2026-01-15T09:30:00+00:00"
    },
    {
      "id": "22222222-2222-4222-8222-222222222222",
      "ticker": "AMD",
      "shares": 5,
      "entry_price": 50.0,
      "entry_currency": "USD",
      "entry_currency_basis": {"ticker": "AMD", "price": 50.0},
      "entry_date": "2026-01-15",
      "notes": "core position",
      "status": "open",
      "created_at": "2026-01-15T09:30:00+00:00"
    },
    {
      "id": "33333333-3333-4333-8333-333333333333",
      "ticker": "XOM",
      "shares": 20,
      "entry_price": 70.0,
      "entry_currency": null,
      "entry_currency_basis": null,
      "entry_date": "2026-01-15",
      "notes": null,
      "status": "closed",
      "created_at": "2026-01-15T09:30:00+00:00"
    }
  ],
  "selected_position_ids": [
    "11111111-1111-4111-8111-111111111111",
    "22222222-2222-4222-8222-222222222222"
  ],
  "composer_input_source": "positions",
  "composer_inputs": [
    {"ticker": "NVDA", "shares": 10, "entry_price": 100.0},
    {"ticker": "AMD", "shares": 5, "entry_price": 50.0}
  ],
  "completeness": {
    "exact_count": 3,
    "range_first": 0,
    "range_last": 2,
    "returned_count": 3,
    "max_rows": 1000,
    "complete": true,
    "open_count": 2,
    "selected_count": 2,
    "positions_reads": 1,
    "source": "portfolio_positions",
    "watchlist": null
  }
}
```

Note the closed `XOM` row: it is in `rows` (the capture is the whole book) and
absent from `selected_position_ids` and from `composer_inputs` (it is not open).
Note also that the currency receipt survives verbatim: `entry_currency` and
`entry_currency_basis` are carried exactly as captured. The producer does NOT
interpret them — the Terminal owns the currency projection and derives the same
currency from the same bytes.

## What the witness never is

- It is never a canonical hash. There is no Python book key here.
- It is never logged and never placed in a URL. It holds the owner's private
  rows.
- It is never attached to a previously cached brief. Bound mode neither reads
  nor writes the legacy cache.
- It is never assembled from separately timed pagination.
- It never claims a position the Terminal cannot see: a row the two readers
  disagree about is refused, not normalised.
