# FIF X0 — query CSV/Parquet routes and thin Python client

Sibling POST routes of `/api/forensics/v1/financial/query` (`app/forensics.py:842`)
and `/query.xlsx` (`app/forensics.py:889`). Same admission, same
`require_site_full_user`, same canonical receipt. No second encoder, no job
system.

## Routes and headers

| Method | Path | Handler |
|---|---|---|
| POST | `/api/forensics/v1/financial/query.csv` | `app/forensics.py:988` |
| POST | `/api/forensics/v1/financial/query.parquet` | `app/forensics.py:1010` |
| GET/PUT/PATCH/DELETE/HEAD | each path above | private 405 after auth (`app/forensics.py:975`, `:997`) |

Shared body: `_financial_query_export` at `app/forensics.py:933`.
`_admit_json_post_body` runs outside the try (`:948`); provider construction
and `execute_financial_query` sit inside the 503 boundary (`:949-958`).

Success headers (plus `_PRIVATE_HEADERS` no-store/private):

- `Content-Disposition: attachment; filename="{response_query_id}.{fmt}"`
- `X-FIF-Response-SHA256` = sha256 of the CSV/Parquet payload
- `X-FIF-Receipt-SHA256` = sha256 of the JSON envelope (`result.sha256`)

## No second pipeline

`export_query_envelope` (`engine/fundamental_forensics/query_exports.py:35`)
rebuilds `MetricMatrix.from_dict(envelope["receipt"])` and requires
`matrix.to_dict() == envelope["receipt"]` (`query_exports.py:24-32`).

| Format | Function | Source |
|---|---|---|
| JSON | `execute_financial_query` body | `query_service.py:500-609` |
| CSV | `MetricMatrix.export("csv")` | `query.py:3703-3711` (`_csv_safe` at `query.py:587-590`) |
| Parquet | `_encode_cells_parquet(matrix)[0]` | `query_snapshots.py:563-589` |
| XLSX | `to_xlsx_bytes` | `excel_export.py:121` (X1, unchanged) |

Parquet media type is `application/vnd.apache.parquet`
(`query_exports.py:16`), the snapshot cells projection, never a second receipt.

## A54 stateless replay

No export job owner exists. Resume = re-issue the identical canonical request
bytes; the payload and headers are a deterministic function of that body.
Cancel = client abort; the server holds no export state. Entitlement is
re-checked on every call (`Depends(require_site_full_user)`). A long-running
export would need a plan amendment.

## Client

`engine/fundamental_forensics/api_client.py` is stdlib-only. Inject a transport
in tests; the default `urllib.request` path is unused by CI.

```python
from engine.fundamental_forensics.api_client import FinancialQueryClient

def transport(method, url, headers, body, timeout):
    # FastAPI TestClient adapter: no sockets.
    response = client.request(method, urlparse(url).path, content=body, headers=dict(headers))
    return response.status_code, dict(response.headers), bytes(response.content)

c = FinancialQueryClient("http://testserver", transport=transport)
envelope = c.query(request)          # Decimal cell_values(), never float
csv_out = c.export(request, "csv")   # sha256 == X-FIF-Response-SHA256
```

`encode_query_request` uses canonical JSON (`sort_keys=True`, compact
separators, `ensure_ascii=False`) and refuses floats/NaN/Infinity, oversize
bodies, and `metric_ids`/`periods` past `MAX_METRIC_IDS`/`MAX_PERIODS`
imported from `query_service`. Bearer tokens never appear in `repr()` or
exceptions.

## GAPS

- No real-Excel refresh receipt (X1 workbook is static OOXML; Power Query
  against these routes is unmeasured in a supported Excel environment).
- No async export owner; A54 is stateless replay only.
- The analyst UI still does not call the financial query or export routes.
- Golden FIP1 receipt text fields do not begin with `=+/@`/tab/CR; A40
  formula-guard coverage uses a kernel matrix built with those prefixes
  through the same `_csv_safe` encoder the HTTP CSV bytes equal.
