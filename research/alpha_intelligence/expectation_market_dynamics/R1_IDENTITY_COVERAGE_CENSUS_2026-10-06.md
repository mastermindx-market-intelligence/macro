# R1 identity / basis / rights coverage census (SRC-A1 cutoff)

Measurement-only census at the frozen SRC-A1 universe cutoff `2026-10-03T06:31:51Z`. No design, collector, store, or rights recommendations.

| Field | Value |
|---|---|
| `source_revision` | `679a325d7d08019f1f0afa10e2e18277da1a38f2` (`origin/main` at measurement) |
| Machine receipt | `R1_IDENTITY_COVERAGE_CENSUS_2026-10-06.json` |
| HOLD | **HOLD-FOR-SOL** — informs R1 source-owner completion; does not complete R1 |

## Universe gate (receipt blobs)

| Check | Result |
|---|---|
| Constituent blobs | `ee4036e86b46…` (breadth), `aeac187ded45…` (midcap), `a44c8f5e6c36…` (smallcap) per `SRC_A1_OPERATING_RECEIPT_2026-10-03.json` |
| Symbol extraction | Parquet **index** `symbol` (not the `name` company-title column) |
| Distinct symbols | **1503** |
| `sorted_names_canonical_json_sha256` | **441a942e97950e2fae5c6a015f38535058b0647a540f8ee1ac2342d02bd6ddc5** — **MATCH** |

**Command**

```bash
PYTHONPATH=. python3 - <<'PY'
import hashlib, json, subprocess
from pathlib import Path
import pandas as pd
BLOBS=['ee4036e86b462b7edcc8595026d86d3171ea4e52','aeac187ded459ea94e149c5fc8dabc4e610d3ad0','a44c8f5e6c36368b402dcc5ecd08479487bc41b6']
names=set()
for b in BLOBS:
    raw=subprocess.check_output(['git','cat-file','-p',b])
    p=Path(f'/tmp/u_{b[:8]}.parquet'); p.write_bytes(raw)
    names.update(pd.read_parquet(p).index.astype(str))
sorted_names=sorted(names)
sha=hashlib.sha256(json.dumps(sorted_names,separators=(',',':')).encode()).hexdigest()
print(len(sorted_names), sha)
PY
```

**Summary line:** `1503 441a942e97950e2fae5c6a015f38535058b0647a540f8ee1ac2342d02bd6ddc5`

---

## Q1 — Identity sources (canonical in-repo)

Search bounds: `git ls-tree -r --name-only origin/main data | grep -iE 'alias|ident|security|issuer|master|cik|figi|isin|ticker'` → **2923** paths; plus `engine/` (**42** identity-related paths), `collectors/` (**3**), `lib/`, `scripts/`, `research/alpha_intelligence/`, `agentos/` (manual review). Non-canonical / out-of-scope for this table: `data/debt_maturity/cache/CIK*.json` (per-issuer debt caches), `data/stock_identity/**` (WS:STOCK-IDENTITY research atlas; not the Data OS issuer spine per `WS-PROPHET-US-V4-RECOVERY`).

Owner column: longest `agentos/workstreams/*.md` `owns_paths:` prefix match, else **UNOWNED**. `config/dataset_registry.yml` lists `owner: macro-dashboard` for `reference.*` datasets (not a workstream key).

| Path | Owner | Git blob @ `origin/main` | Rows | History support | Primary identity fields |
|---|---|---:|---:|---|---|
| `data/reference/security_master.parquet` | UNOWNED | `362a32522f92a7cb180763d4bb5c97de865c4061` | 2382 | yes (`effective_at`, `ingested_at`, `security_state`, `superseded_by`) | `security_id`, `issuer_id`, `issuer_cik`, `listing_key`, `country`, `mic`, `inception_code` |
| `data/reference/issuer_master.parquet` | UNOWNED | `525395c72994819a160aea1cdedc46365f1d465a` | 1213 | snapshot (`era`, `status`) | `issuer_id`, `cik`, `legal_name`, `n_securities` |
| `data/reference/vendor_aliases.parquet` | UNOWNED | `1197a56fd6107905e8d926629f19ac80b7a76278` | 6037 | yes (`valid_from`, `valid_to`, `ingested_at`) | `vendor`, `vendor_symbol`, `security_id` |
| `data/reference/issuer_migrations.parquet` | UNOWNED | see JSON | 3 | yes (`migrated_at`) | `security_id`, `old_issuer_id`, `new_issuer_id` |
| `data/reference/security_migrations.parquet` | UNOWNED | see JSON | 1 | yes (`migrated_at`) | `security_id`, `superseded_by` |
| `data/symbol_directory/cik_map/2026-09-28.parquet` | UNOWNED | see JSON | 10440 | dated snapshot family under `data/symbol_directory/cik_map/` | `ticker`, `cik`, `title` |
| `data/openfigi/cusip_ticker.parquet` | UNOWNED | see JSON | 2771 | ingest stamp `_mapped_at` | `cusip`, `ticker`, `name`, `exch`, `sec_type` |
| `data/breadth/ticker_sectors.parquet` | UNOWNED | see JSON | 1515 | no | `ticker`, `sector` (sector label only) |
| `data/theme_graph/identity_resolution.parquet` | WS:GMI-THEME-GRAPH | see JSON | 151465 | yes (`resolution_asof`, `computed_at`, epochs) | `issuer_id`, `security_id`, `listing_key`, `source_native_symbol` |
| `data/ffiec_y9c/bhc_ticker_map.csv` | UNOWNED | see JSON | 23 | no | `ticker`, BHC metadata (bank holding companies) |
| `lib/dataos/identity.py` | UNOWNED | see JSON | n/a | API (`VendorAliasTable`, `IssuerMaster`, listing/SEC/ISS mint rules) | identity types + alias table |
| `scripts/build_security_master.py` | UNOWNED | see JSON | n/a | producer | builds `data/reference/*` |
| `scripts/security_state_producer.py` | UNOWNED | see JSON | n/a | reads reference owners | composes `security_state.v1` inputs |
| `engine/security_state.py` | UNOWNED | see JSON | n/a | compiler | `security_state` projection |
| `collectors/symbol_directory.py` | UNOWNED | see JSON | n/a | producer | `data/symbol_directory/` |

Full blob list and field arrays: `R1_IDENTITY_COVERAGE_CENSUS_2026-10-06.json` → `sources[]`.

**Row-count command (example)**

```bash
git show origin/main:data/reference/security_master.parquet > /tmp/security_master.parquet
python3 -c "import pandas as pd; print(len(pd.read_parquet('/tmp/security_master.parquet')))"
```

**Summary line:** `2382`

---

## Q2 — Prospective coverage at SRC cutoff (1503 symbols)

Cutoff date for PIT alias resolution: **2026-10-03** (UTC calendar date of `2026-10-03T06:31:51Z`). Store ticker resolution uses `lib.dataos.identity.VendorAliasTable.resolve("store", ticker, date)`; issuer link uses `IssuerMaster.issuer_of_security`. **Currency / fiscal-year-end / accounting-basis columns are absent** from `reference.security_master` and `reference.issuer_master` at `origin/main`, so those counts are **0** unless noted.

| Source | Issuer id resolved | Alias / change dated ≤ cutoff | Currency | FYE | Basis | Undated alias rows (separate) |
|---|---:|---:|---:|---:|---:|---:|
| `data/reference/security_master.parquet` (+ store alias chain) | 779 / 1503 | 2 | 0 | 0 | 0 | 777 |
| `data/reference/vendor_aliases.parquet` (all vendors) | 779 | 2 | 0 | 0 | 0 | 777 |
| `data/reference/*_migrations.parquet` (≤ cutoff `migrated_at`) | 779 | 3 tickers with ≥1 migration row | 0 | 0 | 0 | — |
| `data/symbol_directory/cik_map/2026-09-28.parquet` (latest snapshot ≤ cutoff) | 1499 ticker rows present (CIK, not `issuer_id`) | 0 | 0 | 0 | 0 | 0 |
| `data/openfigi/cusip_ticker.parquet` | 898 tickers present | 0 | 0 | 0 | 0 | 0 |
| `data/theme_graph/identity_resolution.parquet` | 776 distinct `source_native_symbol` with non-null `issuer_id` | 0 | 0 | 0 | 0 | 0 |
| `data/revisions/expectation_observations.parquet` | 0 (`issuer_ref` always null) | 0 | 0 (`currency` null) | 0 (`fiscal_year` null) | 0 (`basis` null) | 0 |

**Command (reference spine)**

```bash
PYTHONPATH=. python3 /tmp/build_r1_census.py | jq '.coverage["data/reference/vendor_aliases.parquet"]'
```

**Summary line:** `{"issuer_id":779,"alias_dated":2,"currency":0,"fye":0,"basis":0,"undated":777}`

---

## Q3 — Provider family (expectation collector)

| Item | Verbatim owner statement (path:line) |
|---|---|
| Provider id | `collectors/equity_revisions.py:86` — `_EXPECTATION_PROVIDER = "yfinance"` |
| Collector docstring (Yahoo / yfinance) | `collectors/equity_revisions.py:6-9` — “yfinance gives only the CURRENT snapshot… This drips a capped batch… (never hammers Yahoo)” |
| Physical owner | `research/alpha_intelligence/expectation_market_dynamics/OWNER_AND_REUSE_MATRIX.md:42-47` — “`collectors/equity_revisions.py` owns prospective EPS/revenue observation collection” |
| Terms / family read | `research/licenses/PROPHET_US_SOURCE_RIGHTS_REGISTER_2026-09-23.md:135` — “Yahoo terms were fetched at `https://legal.yahoo.com/us/en/yahoo/terms/otos/index.html` on 2026-09-23T19:32:46Z.” |

**Bounds if provider unnamed:** `rg -n 'yfinance|Yahoo Finance' collectors/equity_revisions.py research/alpha_intelligence/expectation_market_dynamics agentos/decisions/DEC-SRC-A1-PROSPECTIVE-EXPECTATION-SOURCE-CONTRACT.md` → matches above (not NONE FOUND).

---

## Q4 — Rights class for `expectation_attempts.parquet` rows

| Item | Verbatim statement |
|---|---|
| Writer assignment | `collectors/equity_revisions.py:363` — `"rights_class": "UNKNOWN",` (observation rows; attempts table has no `rights_class` column) |
| Contract field | `research/alpha_intelligence/expectation_market_dynamics/DATA_CLOCK_RIGHTS_MATRIX.md:92` — lists `rights_class` on observations, no enum value |
| Rights register (research) | `research/licenses/PROPHET_US_SOURCE_RIGHTS_REGISTER_2026-09-23.md:142` — “`collectors/equity_revisions.py:358-364` records `rights_class: UNKNOWN`. Posture: **not a source**.” |

No `agentos/decisions/*` or `config/*` row assigns a non-`UNKNOWN` rights class to `data/revisions/expectation_attempts.parquet` (searched `rg -n 'rights_class' research/alpha_intelligence/expectation_market_dynamics agentos/deciders collectors/equity_revisions.py config`).

---

## Q5 — Publication clocks (expectation + identity sources)

### `expectation_attempts.parquet` (pyarrow schema @ `origin/main`)

Columns: `attempt_id`, `collection_session_id`, `provider`, `ticker_compat`, `attempted_at`, `completed_at`, `status`, `http_status`, `latency_ms`, `response_payload_hash`, `safe_error_class`, `safe_error_detail`, `observation_count`.

**Source-effective / publication timestamps distinct from capture:** **NONE** — only session/attempt clocks (`attempted_at`, `completed_at`).

```bash
git show origin/main:data/revisions/expectation_attempts.parquet > /tmp/expectation_attempts.parquet
python3 -c "import pyarrow.parquet as pq; print([f.name for f in pq.read_schema('/tmp/expectation_attempts.parquet')])"
```

### `expectation_observations.parquet`

Declared clocks include `source_effective_at`, `source_published_at`, `provider_observed_at`, `system_observed_at` (`collectors/equity_revisions.py:354-357` sets source clocks **null**; collector comment: “yfinance's estimate accessors do not expose source-issued clocks.”).

| Field | Non-null rows (full file) |
|---|---:|
| `source_effective_at` | 0 |
| `source_published_at` | 0 |
| `provider_observed_at` | 495320 |
| `system_observed_at` | 495320 |

### Q1 identity sources

| Source | Source-effective / publication-like fields |
|---|---|
| `vendor_aliases` | `valid_from` / `valid_to` (alias validity), not publication |
| `security_master` | `effective_at`, `ingested_at` |
| `cik_map` snapshots | snapshot date in path; columns `ticker`, `cik`, `title` only |
| `theme_graph/identity_resolution` | `resolution_asof`, `computed_at`, `master_generated_at` |

---

## Tests / validators

```bash
python3 -c "import json; json.load(open('research/alpha_intelligence/expectation_market_dynamics/R1_IDENTITY_COVERAGE_CENSUS_2026-10-06.json'))"
```

**Summary line:** (no output, exit 0)
