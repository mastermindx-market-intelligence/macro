# CorpActions split-history evidence — 2026-10-07

This source-only dependency extends the existing CorpActions owner and uses the
existing Market Memory source kernel. It does not activate a collector, private
store, scheduler or service. The dataset remains `PROPOSED`. Entry Radar source
basis remains unavailable; Phase 1 remains `NOT_ADMITTED`, H1/H2/H3 remain
`NOT_TESTED`, and the kernel authority flags remain false.

## Entry points and ownership

- `engine.close_pass.massive_close.retain_split_history(ticker,
  earliest_bar_et_date, basis_date, *, store_root)` is an explicit opt-in wrapper.
- `engine.close_pass.massive_split_evidence.acquire_split_history(...)` performs
  bounded acquisition and returns a sealed sanitized attempt.
- `intake_split_acquisition(attempt, *, store_root)` persists that exact attempt,
  allowing safe replay after an uncertain write.
- `SplitEvidenceReader(store_root, generation_id=...)` reads receipts/artifacts
  from a pinned kernel generation; `read(receipt_id)` returns the artifact, owner
  receipt and a separately sealed actual read receipt.

The default `corp_action_tickers` split/dividend guard, `SPLITS_PATH`, configured
`api.polygon.io` base, close-pass callers and their never-raise behavior are
unchanged. The new evidence operation raises typed intake/store errors when it
cannot honestly retain evidence. No default caller invokes it. Synthetic tests
replace the private `_open_split_request` transport seam and credential lookup;
production APIs accept no caller-supplied clock or acquisition ID.

The dedicated `massive_rest:stocks:split_history` SourceFamily uses version 1
schemas and the private leaf `sources-massive-split-history-v1`. The caller must
supply a safe private location accepted by the existing kernel. There is no
production default destination. This adapter uses the exported kernel lock,
immutable create-once object/capture/receipt/generation writes and atomic HEAD
replacement. It does not copy the persistence engine or alter the SPY family.

## Request and response contract

Only the new path uses `https://api.massive.com/stocks/v1/splits`. The initial query
contains an explicit case-sensitive `ticker`, `execution_date.gte` equal to the
earliest bar ET date, `sort=execution_date.asc`, and `limit=1000`. A valid named
`basis_date` at or after the lower date bound is retained as request context; it
is not an upper query bound, applicability proof or price-adjustment vintage.
Rows after that date remain observed rows. No stock-dividend exclusion is made.

Pagination must retain the exact HTTPS host and path, with one bounded safe
cursor. Cursor-only pagination is allowed. If ticker, lower bound, sort or limit
are repeated, they must match exactly. Duplicate query keys, unknown parameters,
changed scope, fragments, credentials in URL authority, alternate ports, repeated
cursors and redirects refuse. A pagination `apiKey` parameter is discarded; only
the owner's original authorization header is used. Cursor values and request
URLs are never retained; page evidence stores the cursor SHA-256. There is no
transparent retry or redirect that could hide another HTTP attempt.

Response JSON requires UTF-8, no duplicate keys at any depth, no nonfinite
constants, exact `status="OK"`, and an actual `results` list. An explicit response
ticker, when present, must be an exact string and match. Numeric JSON tokens
with the same spelling are not ticker strings. Each retained row requires a bounded native
`id`, exact requested ticker, valid execution date within the query range, finite
positive numeric `split_from` and `split_to`, and a known `adjustment_type`:
`forward_split`, `reverse_split` or `stock_dividend`. Native IDs are never
synthesized, case-folded or deduplicated. Duplicate IDs, including equal duplicate
rows, refuse completeness. Dates must be nondecreasing across pages.

Ratios and optional `historical_adjustment_factor` preserve the exact original
JSON numeric token as a decimal string, including precision/exponent spelling.
Strings, booleans, nulls, missing necessary fields and nonpositive numeric values
refuse. If an optional historical factor is supplied, it must also be a finite
positive number; absence stays absent. Unknown metadata is dropped. No headers,
credentials, arbitrary error text or unreviewed body strings enter the store.

## Attempt and page wire

The artifact schema is `market_memory.source.massive_split_history.v1`:

| Field | Meaning |
| --- | --- |
| `acquisition_id` | Random UUID hex for this attempt, independent of content |
| `request` | Fixed endpoint, ticker, lower date bound, sort, limit and named basis date |
| `started_utc_ns`, `completed_utc_ns` | Actual acquisition wall clocks, integer nanoseconds |
| `status` | `complete`, `partial` (retained rows plus failure), or `failed` |
| `failure_kind` | Fixed diagnostic or null for a complete acquisition |
| `pages` | Every HTTP attempt, in zero-based order, including a failed later page |
| `rows` | Reviewed native fields plus zero-based `page_index` / `row_index` |
| `acquisition_sha256` | Canonical sanitized attempt seal; not provider authentication |
| `basis_eligible`, `authority` | False basis eligibility and unchanged kernel authority |

Each page carries request-start and response-completion integer UTC nanoseconds,
HTTP status if obtained, `observed_body_sha256`, `body_bytes_observed`,
`body_complete`, `rows_received` (null before a valid results list),
`rows_retained`, cursor hash, index and typed outcome. The body hash covers only
the bytes actually read. For an oversized or interrupted body it describes the
observed prefix, explicitly `body_complete=false`; it is not a digest of the
complete response. An EOF with declared Content-Length bytes still outstanding
refuses completeness even if the observed prefix is valid JSON. HTTP parser
`IncompleteRead`/`HTTPException` failures retain the bounded decoded prefix
actually exposed to the adapter, with `body_complete=false` and the fixed
`http_framing` diagnostic. Bytes consumed internally but not exposed by the HTTP
parser are not included in the observed-byte claim. Raw bodies are not retained.

Fixed failure kinds distinguish transport, HTTP framing, HTTP status, redirect, response
capacity, malformed JSON, response status, absent results, response identity,
malformed rows, duplicate IDs, row capacity, pagination, repeated cursor and page
capacity. Valid preceding rows and all attempted page receipts remain in the
failed/partial artifact. They are not complete coverage or basis evidence.
Complete-empty requires strict OK plus an actual empty list and terminal valid
pagination. An explicit null/empty `next_url` is refused rather than guessed to
mean completion; terminal success is absence of `next_url`.

## Persistence, revisions and clocks

The capture ID binds source family and acquisition identity. An exact replay of
that identity/payload is idempotent; changed content under the same identity is a
conflict. Fresh acquisitions always append, even identical observations. A/B/A,
reclassification, corrections and complete omissions remain separate immutable
receipts and generations. No old observations are expanded into a new vintage.
Kernel `vintage_id` identifies the request scope; it is explicitly not proof of
a price vintage. `revision_id` binds that scope and the complete artifact hash.

The owner receipt labels its clocks `owner_intake_started_utc_ns` and
`owner_receipt_assembled_utc_ns`. Both are before HEAD publication and neither
claims durable publication completion or downstream knowledge. The reader seals
actual read-start and read-completion clocks, pinned generation, owner receipt
hash and exact artifact byte hash/count. That read receipt is returned to its
caller, not persisted in another ledger. A later read cannot backdate itself.
All clocks remain integer nanoseconds; no lossy datetime conversion or fabricated
offsets occur. Clock regression/future acquisition refuses.

Readers verify source/capture/revision binding, object bytes, receipt copies and
kernel ancestry. Returned objects are isolated copies. Old generation replay
retains its artifact/owner receipt even after later acquisitions; each new read
has a new actual read receipt. The kernel hashes establish local consistency,
not signatures or external source authenticity.

Concurrent writers serialize only intake/publication with the existing per-store
flock; network activity happens before the lock. All prospective capacity checks
precede immutable attempt writes and HEAD advancement. A failed HEAD replace
leaves previous published evidence readable; unpublished immutable receipts can
be reconciled and reused for exact retry. A failure reported after an OS-level
replace must be reconciled through the existing kernel, not presumed rolled back.
No `.bak`, pruning, overwrite, auxiliary failure ledger or repair service exists.

## Bounds and refusal

- HTTP response: at most 1 MiB plus one byte to detect overflow.
- Acquisition: at most 8 pages, requested limit 1000, at most 4096 retained rows.
- Numeric token: 128 characters; native ID: 128 reviewed characters; ticker: 32.
- Kernel canonical object: 1 MiB; receipt: 64 KiB; generation: 4 MiB and 4096 receipts.

A response/row/page limit produces a typed incomplete acquisition where the
bounded evidence fits the object. Object/receipt/generation capacity refusal
leaves prior published bytes unchanged and does not claim the new attempt was
retained. The caller may keep the returned acquired attempt for later exact
intake replay; no truncation or silent history pruning is performed. Missing
credentials/invalid arguments refuse before an HTTP attempt, so they do not
manufacture a page observation.

## Verification and remaining dependency

`tests/test_close_pass_split_evidence.py` uses synthetic injected bytes and real
kernel filesystem primitives in temporary private roots. It covers direct valid
transport, strict empty, partial/later failure, malformed input, precision,
identity and pagination constraints, standard urllib redirect rejection, real HTTPResponse complete-length/chunked
controls and truncated-framing failures, numeric-token ticker refusal,
correction/reclassification/omission/A-B-A, exact replay/conflict, nanosecond read
custody, old pinned replay, capacity invariance, failed atomic HEAD replacement,
orphan reconciliation, concurrent writers and credential exclusion. Existing
close-pass, source-kernel/SPY and registry suites guard compatibility.

Hosted CI must add this focused suite beside the existing close-pass tests in
`.github/ci/legacy-jobs.yml`; routing is root-owned and outside this five-file
claim. No live provider, credential, runtime store or production operation forms
part of these proofs.

The next dependency remains retained raw-minute price/volume observations plus
an explicit reconstruction contract through their real owner. This slice does
not multiply factors, invert adjusted prices, establish split direction for a
price calculation, normalize volume or claim that a returned cumulative factor
is several independent factors. Current adjusted=true minute records still lack
an admitted adjustment vintage. Source retention alone does not admit the RS
Pullback Launch signal.

Primary contract references (reviewed before implementation):

- https://massive.com/docs/rest/stocks/corporate-actions/splits
- https://massive.com/knowledge-base/article/does-massive-support-normal-and-reverse-splits
- https://massive.com/knowledge-base/article/is-massives-stock-data-adjusted-for-splits-or-dividends
- https://massive.com/knowledge-base/article/why-does-volume-return-as-a-decimal-value-from-the-aggregates-endpoint
