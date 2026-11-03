# FIF Excel workflow (X1)

Deterministic `.xlsx` snapshot of a financial query response, plus Option A
Power Query refresh against the existing POST JSON query API.  This is not an
Office add-in, not `WEBSERVICE()`, and not an OData feed.

## Option A — Power Query (Excel Desktop 2016+ / Microsoft 365)

Uses Excel's built-in Power Query engine.  No add-in install, deployment, or
certification gate.

1. Open Excel Desktop (2016+ or Microsoft 365).  Excel for the web is **not**
   a claimed environment: custom `Web.Contents` refresh is admin-limited there.
2. Data → Get Data → From Other Sources → Blank Query → Advanced Editor.
3. Paste `contracts/excel/fif_financial_query.pq`.
4. Replace every `<<...>>` placeholder:
   - `<<FIF_QUERY_URL>>` — full URL of `POST /api/forensics/v1/financial/query`
     (JSON).  Do not point this at the `.xlsx` sibling; Power Query consumes JSON.
   - `<<FIF_BEARER_TOKEN>>` — current Supabase JWT.  Tokens expire; re-enter on
     401.  There is no longer-lived PAT on this surface.
   - `<<FIF_REQUEST_JSON>>` — the canonical query body (`schema`, `entity_id`,
     `policy.selection`, `policy.source_snapshot_at`, `policy.recorded_at`,
     `metric_ids`, `periods`).  Both cutoffs are mandatory.
5. Close the editor and load.  Values land as canonical decimal **text** from
   the JSON receipt (exactness preserved; do not coerce with Excel `VALUE()`
   unless you accept binary-float rounding).
6. Data → Refresh All re-POSTs the same body with the current Authorization
   header.  A signed-out or entitlement-lost refresh must fail visibly.

The generated workbook from `to_xlsx_bytes` is a **static snapshot**.  It does
not embed a Power Query connection (the OOXML package is the seven-entry
deterministic set).  Refresh is the separate `.pq` template against the live
JSON route.

The HTTP sibling `POST /api/forensics/v1/financial/query.xlsx` returns the
same snapshot as an attachment (`<query_hash>.xlsx`) under the same
entitlement gate and POST-only policy as the JSON route.

## A39 policy cases

| Case | What to pin | Expected workbook / refresh behaviour |
|---|---|---|
| Signed-out / entitlement-lost | Drop `Authorization`, or use a free-tier session | Power Query refresh **fails** (401/403).  Previously loaded numbers must not silently remain as if current.  Treat the query error as the workbook error state; do not keep a cached table as authoritative. |
| Source correction | Same `source_snapshot_at` + `recorded_at`; a later filing has landed | Re-query.  Compare the new receipt to `POST /api/forensics/v1/financial/revisions` at the same cutoffs.  Cell values change only when the cutoff-visible revision lineage changes; provenance accession/filed/accepted/recorded clocks must move with the selected source. |
| Pinned versus current | Pinned: freeze `policy` cutoffs (and optional snapshot id). Current: advance cutoffs / `latest` pointer | Two queries.  Pinned bytes and `query_hash` stay identical.  Current may differ.  Do not mix the two in one table without labelling the policy row on Meta. |
| Source links | Per-cell `accession`, CIK/`entity_id`, `filed_at`, `accepted_at`, `recorded_at`, mapping/formula digests | Workbook Response columns must equal the API receipt / CSV projection for those fields.  A mismatch is a failed roundtrip, not a display issue. |

## Determinism contract

`engine/fundamental_forensics/excel_export.py` (`to_xlsx_bytes`) is a pure
function of the response mapping.

- Standard library only (`zipfile`, `xml.sax.saxutils`, `csv`, `decimal`).
  No openpyxl, pandas, or lxml.
- ZIP: `ZIP_DEFLATED`, `compresslevel=6`.
- Every `ZipInfo.date_time == (1980, 1, 1, 0, 0, 0)`.
- Fixed entry order: `[Content_Types].xml`, `_rels/.rels`, `xl/workbook.xml`,
  `xl/_rels/workbook.xml.rels`, `xl/styles.xml`, `xl/worksheets/sheet1.xml`,
  `xl/worksheets/sheet2.xml`.
- No shared-strings table.  No styles beyond the mandatory empty stylesheet.
- Sheet `Response`: header + the same rows/columns as `MetricMatrix.to_csv_bytes`.
- Sheet `Meta`: key/value rows from fields the response already carries
  (schema, query id / `query_hash`, as-of cutoffs, governance `content_id`,
  coverage, `sha256` when present).  Never invented facts.  `exact_text_cells`
  is recorded only when a Decimal cannot round-trip through float.
- Text cells: `t="inlineStr"` with `<is><t xml:space="preserve">…</t></is>`,
  after `_csv_safe` (leading `=`, `+`, `-`, `@`, tab, CR get a leading `'`)
  and XML escaping (`&`, `<`, `>`, `"`, `'`).  Exception: a finite value
  that does not round-trip through IEEE-754 is written as its exact decimal
  text with no `_csv_safe` (no leading `'`, negative included), and its A1
  reference is listed in the Meta sheet `exact_text_cells`.
- Finite `int` / `Decimal` that round-trip through IEEE-754: numeric `<v>`
  with `format(Decimal(v), "f")` (never a Python float repr).  CSV value
  column uses that column's exact decimal text.
- Dates / datetimes: ISO-8601 text (UTC `Z` form when timezone-aware).
- `None`: omitted cell.
- Two calls with the same mapping produce identical bytes.

## Limits

- Transport: JSON POST, `Content-Type: application/json`, body ≤ 64 KiB,
  response ≤ 8 MiB, ≤ 50 metrics, ≤ 8 periods, ≤ 400 cells.
- Auth: `Authorization: Bearer` (or the Supabase session cookie on the JSON
  route).  Entitlement is `require_site_full_user` on every call, including
  refresh.  GET/PUT/PATCH/DELETE/HEAD on the financial paths return private 405.
- Formula injection: textual fields are `_csv_safe`.  The canonical numeric
  value column stays numeric so a negative Decimal is not prefixed with `'`.
- Excel-for-web, Office Scripts, and Office.js add-ins are out of scope.
- Power Query POST-with-auth behaviour varies by Excel build; test each
  claimed desktop environment before asserting it.
- JWT lifetime forces token re-entry; a missing or expired token is a failed
  refresh, not a stale-number success.

## A39-L localhost refresh proof

`scripts/fif_excel_refresh_harness.py` runs the four A39 policy cases against
the real routes on a loopback server with a controllable sign-in state, and
checks the saved workbook against the API receipt by machine.  Golden corpus
only: it refuses to start when `FIF_FINANCIAL_DATASET_MODE` holds anything but
`golden` or when any environment variable whose *name* starts with `R2_` is
present (names only, values never read), and it binds `127.0.0.1` exclusively.

1. **Serve** (repo root, uvicorn on `PATH` — the deployment ASGI runner):

   ```
   python3 scripts/fif_excel_refresh_harness.py serve --out <dir> [--port 8765]
   ```

   Before the socket opens, the harness calls the routes in-process and writes
   into `<dir>`: `tokens.json` (mode 0600, the canonical record of the two
   random bearer tokens), `pinned.pq`, `current.pq`, `signed_out.pq`,
   `free_tier.pq` (the committed template with only the `<<...>>`
   placeholders filled — the request JSON is M-escaped with doubled quotes;
   mode 0600 because each embeds its case token), and `receipts.json` (per
   case: status, `query_hash`, the receipt nodes, the request body, plus
   revisions evidence and the pinned/current cell differences).  The stdout
   summary and stderr GAP lines never contain a token.
   `python3 scripts/fif_excel_refresh_harness.py cases` prints the
   case table (case, token kind, cutoffs, expected status) without tokens.

2. **Paste per case** (Excel Desktop, Advanced Editor as in Option A):

   | Case | Paste | Expected |
   |---|---|---|
   | authorized, pinned policy | `pinned.pq` | table loads; earlier filing only |
   | authorized, current policy | `current.pq` | table loads; newly visible cell + moved source links |
   | signed out | `signed_out.pq` (empty bearer) | refresh fails 401 |
   | free tier | `free_tier.pq` | refresh fails 403 |

   The full token for `pinned`/`current` is in `<dir>/tokens.json` under
   `"full"`; `signed_out.pq` and `free_tier.pq` are already self-contained.
   Do not edit the pasted M beyond the placeholders the harness filled.

3. **Save the workbook**: after Close & Load and (for the two failure cases)
   the failed Data → Refresh All, save as `.xlsx` (e.g. `pinned.xlsx`).  For
   the failure cases, do not keep a previously loaded table as if current —
   clear it and leave the query error state.

4. **Verify**:

   ```
   python3 scripts/fif_excel_refresh_harness.py verify-workbook \
     --case pinned --workbook pinned.xlsx --out <dir>
   ```

   Prints a JSON verdict (`case`, `rows_compared`, `mismatches`, `verdict`) and
   exits 0 on `match`, 1 on `mismatch` (including a failure-case workbook that
   still presents receipt-looking rows), 2 on input errors.  The checker reads
   the workbook with the standard library only, finds the loaded table through
   `xl/tables/*.xml` refs or the first sheet carrying the receipt's column
   headers, and compares cell for cell — values as canonical decimal text,
   source-link fields (`accession`, `entity_id`, `filed_at`, `accepted_at`,
   `recorded_at`, mapping/formula digests) exactly.  A Power Query load of the
   shipped template carries the node columns; there the nested
   `period`/`provenance` records are bound by `cell_id`, the canonical hash
   over the whole node payload.

   Known corpus limitation (recorded per run in `receipts.json` `gaps`): the
   golden pair's pinned→current differences are the later filing's FILED facts
   (a newly visible cell, and an unchanged value whose selected source moved),
   never `revision_of` events, so the revisions route answers 200 with an
   empty `revisions` list and cannot carry the differing cell.  The harness
   refuses to fabricate one and reports the gap instead.
