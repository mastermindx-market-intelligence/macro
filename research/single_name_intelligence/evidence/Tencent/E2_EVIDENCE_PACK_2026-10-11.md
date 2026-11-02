# E2 — Tencent owner-native evidence pack (2026-10-11)

Task: E2 of the Single-Name Intelligence reference-product chain (SNI-8 acceptance case A33).
Key: `43251ca845b2:config/single_name_intelligence/coverage_profiles/tencent.yml` (E0 lane, PR #8837 branch `claude/sni-e0-m0-qualification-20261011`, not yet merged; profile read verbatim, never edited here).
Repo base: `origin/main` `b79cd12239e576b1a6364167d03dc6e283c9b41d` (worktree `claude/sni-e2-tencent-evidence-20261011`).
As-of: 2026-10-11. Every number below is copied verbatim from an owner call run in this session (commands included, re-runnable from this worktree) or from a committed owner file blob (blob sha cited as `git rev-parse HEAD:<path>` short sha). Zero synthetic, fixture, estimated or hand-typed values. No forecast, score, rank, gate, size, signal, escalation or trade authority is asserted anywhere; all authority flags in the coverage JSON are false.

## Method and evidence standard

- The nine descriptors used per row: (1) issuer subject, (2) reporting period, (3) known-at evidence, (4) unit/currency, (5) dimensions, (6) accounting basis, (7) source span, (8) definition version, (9) correction/refusal state.
- A metric is `OWNER_NATIVE` only if an existing owner returns at least one value for this cell and ALL nine descriptors cite where the owner records it. Anything a descriptor of which this pack infers (e.g. a publication lag computed consumer-side) is `PARTIAL` with the missing descriptors named.
- `REFUSED` = an owner explicitly refuses, or the frozen spec requires refusing the cell. `ABSENT` = the owner exists and was queried for this subject and returned nothing (exact query stated). `NO_OWNER` = no existing owner can serve the cell (would-be owner named).
- Identity law (E0, binding here): Tencent Holdings has NO canonical issuer id (`canonical_issuer_id: UNRESOLVED`). `ISS:US-XNYS-TME` is Tencent Music Entertainment Group, a DIFFERENT issuer, and appears in no Tencent row of this pack. HK counter 00700 = `SEC:HK-XHKG-00700` with `issuer_state=NO_ISSUER_EVIDENCE`, `issuer_id` NULL. RMB counter 80700 has NO security_id anywhere. No id was minted from a ticker, name or CIK in this pack.
- Owner calls were read-only. The one writer-shaped owner probed (`engine/hk_adr_bridge.run`) was NOT run; only its pure `snapshot()` was. No file outside the three owned files changed (verified by `git status --porcelain` before commit).
- Python: `/usr/bin/python3` (pandas 3.0.6). All calls run from the worktree root with `sys.path.insert(0,'.')`.

Identity owner calls used throughout (run 2026-10-11, re-runnable):

```python
python3 -c "
import sys; sys.path.insert(0,'.')
import pandas as pd
from lib.dataos.identity import IssuerMaster, VendorAliasTable
sm = pd.read_parquet('data/reference/security_master.parquet')
im = IssuerMaster.from_records(sm.to_dict('records'))
# The HK security id is READ from the owner's own master row, never constructed from a ticker
# (seat repair 2026-10-11: an earlier draft built it with the owner's key constructor):
sm[(sm['mic']=='XHKG') & (sm['inception_code'].astype(str)=='00700')][['security_id','issuer_id','issuer_state']].to_dict('records')
                                                  # -> [{'security_id': 'SEC:HK-XHKG-00700', 'issuer_id': nan, 'issuer_state': 'NO_ISSUER_EVIDENCE'}]  (one row, sm.iloc[2962])
im.issuer_of_security('SEC:HK-XHKG-00700')        # -> None  (NO_ISSUER_EVIDENCE)
va = pd.read_parquet('data/reference/vendor_aliases.parquet')
# RMB counter 80700: NO id is ever constructed for it. Identity absence is established by
# whole-frame substring scans (re-run 2026-10-11), never by an owner call addressed to an id:
int(sm.astype(str).apply(lambda c: c.str.contains('80700')).any(axis=1).sum())   # -> 0
int(va.astype(str).apply(lambda c: c.str.contains('80700')).any(axis=1).sum())   # -> 0
VendorAliasTable.from_records(va.to_dict('records')).resolve('theme_graph_native','0700.HK', __import__('datetime').date(2026,10,11))
                                                  # -> 'SEC:HK-XHKG-00700'
"
```

Owner-file blobs cited: `lib/dataos/identity.py` `ea8485596e57`, `lib/hk_calendar.py` `5ffb5af43465`, `engine/hk_filing_bus.py` `e3aced460bb8`, `engine/hk_adr_bridge.py` `a8b7acf7119f`, `engine/hk_southbound_stocks.py` `b017e9ac3466`, `engine/research_vault/catalog.py` `828f812d6907`, `collectors/hk_fundamentals.py` `3895bcd52d21`, `engine/company_intelligence/event_workspace.py` `4ab75d478fde`, `engine/fundamental_forensics/packet_service.py` `93e00078d8c6`.

Data blobs cited: `data/reference/security_master.parquet` `85ef75104840`, `data/reference/issuer_master.parquet` `6643e7eae379`, `data/reference/vendor_aliases.parquet` `6406d5bffa3e`, `data/reference/_receipt.json` `f51ffbd63c62`, `data/reference/issuer_migrations.parquet`, `data/reference/security_migrations.parquet`, `data/hk_filings/events.parquet` `be30a5bc5ecb`, `data/hk_filings/coverage.json` `98aedf7d9b2f`, `data/hk_fundamentals/fundamentals.parquet` `b4d4806e1ed9`, `data/hk_stocks/0700.HK.parquet` `b439ba667ff8`, `data/hk_search/closes_deep.parquet` `0ed0dc4075e3`, `data/hk_shorts/positions.parquet` `7843b8775acf`, `data/hk_shorts/coverage.json`, `data/hk_southbound/holdings.parquet` `652e2502ad31`, `data/hk_southbound/backfill_gap_audit.json` `8b120d560ab5`, `data/hk_connect_roster/roster.parquet` `3a2affa41b0c`, `data/hk_placements/events.parquet` `d3d63e03a478`, `data/hk_gdelt/tencent.parquet` `eb31dec7222b`, `data/theme_graph/identity_resolution.parquet` `c84db448b957`, `data/research_vault/catalog.json` `f18851fb4cfc`, `data/qledger/claims.jsonl` `344d38dd4dca`, `data/qledger/grades.jsonl` `94adcdf95da8`, `data/stock_identity/fingerprints/pilot_fingerprint_v0.parquet` `cd7675e995b4`, `data/earnings/earnings.parquet` `8f0575464ba0`, `data/intraday_flow/ledger.parquet` `bf5e0fa0011b`, `data/hk/HKD_X.parquet` `826468c71fd6`, `data/fred/DEXCHUS.parquet` `5f5898b2b6d3`, `data/china/CNH_F.parquet` `fe01ca5a6dcb`, `data/forex/latest.json` `0e41dead4a2f`.

Counts (all 36 profile cells, after the repair pass): 0 OWNER_NATIVE, 16 PARTIAL, 1 REFUSED, 6 ABSENT, 13 NO_OWNER. Machine-readable twin: `E2_COVERAGE_REPORT_2026-10-11.json`. Adversarial probes: `E2_ADVERSARIAL_CASES_2026-10-11.md`.

---

## 1. identity_listing.hkd_0700 — REFUSED

Owner: `lib/dataos/identity.py` (master read) over `data/reference/security_master.parquet` `85ef75104840` + `data/reference/vendor_aliases.parquet` `6406d5bffa3e` + `data/reference/_receipt.json` `f51ffbd63c62`.

| # | Descriptor | Owner record |
|---|---|---|
| 1 | Issuer subject | `security_id=SEC:HK-XHKG-00700`, `issuer_id=NaN`, `issuer_state=NO_ISSUER_EVIDENCE` — the row itself (`sm.iloc[2962]`); `issuer_of_security(...)` returns `None` through the owner API. Issuer link UNRESOLVED; never a constructed `ISS:…` id. |
| 2 | Reporting period | Identity is current-state only; the row's window descriptor is `effective_at=2012-08-31` (in-row) with no end date (current). |
| 3 | Known-at evidence | `ingested_at=2026-08-20 18:50:35` (in-row); receipt `evidence_snapshot=2026-08-18`, `newest_observation=2026-10-09` for the HK admission evidence (`_receipt.json` → `china_hk_admission.evidence_sources.hk`). |
| 4 | Unit/currency | n/a — identifier row, no numeric value (recorded as structurally inapplicable). |
| 5 | Dimensions | `listing_key=HK-XHKG-00700`, `mic=XHKG`, `country=HK`, `inception_code=00700` (in-row); vendor alias `theme_graph_native 0700.HK` (vendor_aliases row 4209, `valid_from=None`). |
| 6 | Accounting basis | n/a — identity row. |
| 7 | Source span | Admission receipt: `hk` evidence = `data/hk_shorts/positions.parquet + data/hk_shorts/turnover.parquet`, provenance "SFC official Short Position Report…", newest observation 2026-10-09 (`_receipt.json` `f51ffbd63c62`). |
| 8 | Definition version | Owner-recorded (review finding F8, descriptor reading ADOPTED): the seam config that owns this admission carries `version: 1` (`config/identity_seams.yml` line 34) and the admission receipt carries `code_version=bb0830d8d778ba4d9e5b56b9b4c2f2a856f70112` (`_receipt.json`, re-read 2026-10-11). |
| 9 | Correction/refusal state | **REFUSED** — the owner refuses the issuer binding: `issuer_of_security('SEC:HK-XHKG-00700')` returns `None`, not a guess, and the row's own `issuer_state` field reads `NO_ISSUER_EVIDENCE`; migration machinery exists (`data/reference/issuer_migrations.parquet`, 3 rows `issuer_semantic_correction_v1`) but holds NO Tencent row. |

Owner call producing the full row set: the block at the top of this file. Bounded sample (1 row — the cell IS one identity row): `SEC:HK-XHKG-00700 | HK-XHKG-00700 | XHKG | 00700 | effective 2012-08-31 | NO_ISSUER_EVIDENCE | ingested 2026-08-20 18:50:35`. Total rows for this subject in security_master: 1 (this row is the evidence row). `evidence_rows: 1`.

`missing_descriptors: ["issuer_subject"]`; `descriptor_notes: {"issuer_subject": "SECURITY_ROW_EXISTS_ISSUER_LINK_NO_ISSUER_EVIDENCE"}`.

Status REFUSED (ruling recorded per the repair packet): the security_master row exists, but the owner itself records the issuer link as NO_ISSUER_EVIDENCE — an owner refusal of exactly this metric's issuer-security link, so the E0 fact "HK counters are NO_ISSUER_EVIDENCE" appears as this REFUSED row; the reviewer's proposed PARTIAL was ruled against on that ground.

## 2. identity_listing.rmb_80700 — NO_OWNER

No id-shaped string is constructed or written for the RMB counter anywhere in this pack (review finding F2 repair): identity absence is established by whole-frame substring scans, re-run 2026-10-11 with output verbatim — `int(sm.astype(str).apply(lambda c: c.str.contains('80700')).any(axis=1).sum())` over `data/reference/security_master.parquet` → `0` matching rows, and the same scan over `data/reference/vendor_aliases.parquet` → `0` matching rows. The counter has no security_id, so no owner lookup can even address it. No existing owner can bind this counter to a security. Would-be owner (profile `would_be_owner`): "Data OS CN/HK admission: scripts/build_security_master.py under research/prophet_v4/d2/D2B2_CN_HK_FROZEN_CONTRACT_2026-08-20.md, with a counter seam (one economic security, two trading counters) declared in config/identity_seams.yml". `evidence_rows: 0`.

## 3. filings_announcements.hkd_0700 — PARTIAL

Owner: `engine/hk_filing_bus.py` `e3aced460bb8` (`build_tape`, `classify_row`, `_ticker_summary`) over `data/hk_filings/events.parquet` `be30a5bc5ecb` + `data/hk_filings/coverage.json` `98aedf7d9b2f`.

```python
python3 -c "
import sys; sys.path.insert(0,'.')
import pandas as pd
from engine import hk_filing_bus as bus
ev = pd.read_parquet('data/hk_filings/events.parquet')
pl = pd.read_parquet('data/hk_placements/events.parquet')
tape = bus.build_tape(ev, pl)
tape[tape['ticker']=='0700.HK']
bus.classify_row('interim_results', ev[ev['news_id']=='12280990'].iloc[0]['title'])
bus._ticker_summary(tape, '0700.HK')
"
```

| # | Descriptor | Owner record |
|---|---|---|
| 1 | Issuer subject | `ticker=0700.HK` on the event row; `stock_code` field is a `<br/>` list `00700<br/>05093…<br/>80700<br/>85069…` (HKD counter first). No issuer id exists (identity family above); subject = ticker + counter list, NO_ISSUER_EVIDENCE. |
| 2 | Reporting period | **MISSING as a field.** The period ("THREE AND SIX MONTHS ENDED 30 JUNE 2026") exists only inside `title` prose. |
| 3 | Known-at evidence | `announced_at=2026-08-12 16:31:00` (naive, HKEX release — timezone not carried in-row) + `date=2026-08-12`; collector observation = coverage.json `fetched_at=2026-10-11T14:17:08.013345+00:00`. |
| 4 | Unit/currency | n/a — event metadata, no numeric value. |
| 5 | Dimensions | `category=interim_results`, `subcats="Announcements and Notices - [Interim Results]"`, `news_id=12280990`; classified by owner to `category=results`, `official_flag=True`, `dilution_flag=False`, `buyback_flag=False`. |
| 6 | Accounting basis | n/a — headline metadata only (profile: "no full text, no metric extraction"). |
| 7 | Source span | HKEXnews titleSearchServlet headline: `title="ANNOUNCEMENT OF THE RESULTS FOR THE THREE AND SIX MONTHS ENDED 30 JUNE 2026"`; owner idempotency hash `title_hash=a5fec4cc` (first 8 hex of SHA-256 of the title). |
| 8 | Definition version | **MISSING** — the category taxonomy (`_CAT_MAP` in the owner) carries no version id. |
| 9 | Correction/refusal state | **MISSING** — no correction/retraction field on headline rows. |

Bounded sample (1 row — the only Tencent event in the store): `news_id=12280990 | ticker=0700.HK | announced_at=2026-08-12 16:31:00 | category=interim_results→results | title_hash=a5fec4cc`. Total Tencent rows in the 3906-row store: 1 (`_ticker_summary` counts `{"results": 1}`; `most_recent_date=2026-08-12`; `name_en="Tencent"`, `name_zh="腾讯"`). Store window per coverage.json: `earliest=2026-04-13`, `latest=2026-10-11`, `n_events=3906`, by_category `interim_results=2178, final_results=792, general_mandate=777, shareholder=132, buyback=27`. `evidence_rows: 1`.

`missing_descriptors: ["issuer_subject", "reporting_period", "definition_version", "correction_refusal_state"]`; `descriptor_notes: {"issuer_subject": "RAW_STOCK_CODE_KEY_NO_ISSUER_EVIDENCE"}`.

## 4. filings_announcements.rmb_80700 — PARTIAL

The announcements are issuer-level and the owner SERVES a value whose raw Tencent row's `stock_code` list contains `80700` (row `news_id=12280990`, §3; the build_tape tape row for that news_id re-run 2026-10-11 shows `ticker=0700.HK` with the raw `stock_code` list preserving `80700` — see the dual-counter fold check in adversarial probe 6). The value's issuer_subject is missing for this counter: the counter→security join needs a security_id that does not exist (§2). Owner: `engine/hk_filing_bus.py`. `evidence_rows: 1`. `missing_descriptors: ["issuer_subject", "reporting_period", "definition_version", "correction_refusal_state"]`; `descriptor_notes: {"issuer_subject": "ROW_STOCK_CODE_LISTS_80700_NO_SECURITY_ID"}`.

## 5. financials.hkd_0700 — PARTIAL

Owner: `collectors/hk_fundamentals.py` `3895bcd52d21` store `data/hk_fundamentals/fundamentals.parquet` `b4d4806e1ed9` (payload JSON string).

```python
python3 -c "
import sys; sys.path.insert(0,'.')
import pandas as pd, json
f = pd.read_parquet('data/hk_fundamentals/fundamentals.parquet')
p = json.loads(f[f['ticker']=='0700.HK'].iloc[0]['payload'])
p['financials']   # 7 annual rows fy2019..fy2025
p['profile']; p['forecast']
"
```

| # | Descriptor | Owner record |
|---|---|---|
| 1 | Issuer subject | `ticker=0700.HK`; `profile.name_full="腾讯控股有限公司"` (Tencent Holdings Limited, verbatim) — a NAME, not an issuer id; no issuer link exists. |
| 2 | Reporting period | `fy` field, calendar fiscal year, `fy2019..fy2025` (7 rows); **no reporting-period known-at** — snapshot `asof=2026-06-18` only (store column). |
| 3 | Known-at evidence | `asof=2026-06-18` (snapshot; in-store). No per-row first_public. STALE per profile clock. |
| 4 | Unit/currency | **UNTRUSTWORTHY — currency defect.** Every financial row carries `"currency": "HKD"` (verbatim in-row) while the collector's own header (lines 19–22) says "many HK names (Tencent etc.) report financials in CNY while the price/target are in HKD. So PE/PB are deliberately NOT computed here (a CNY EPS over an HKD price is wrong)". The defect is recorded here and in the coverage JSON; values are NEVER relabelled or converted in this pack. |
| 5 | Dimensions | per-row keys `revenue, ni, gross_profit, eps, eps_diluted, bvps, gross_margin, net_margin, roe, roa, roic, debt_ratio, current_ratio, cfo_ps, ocf_sales, rev_growth, ni_growth, fy, currency`. |
| 6 | Accounting basis | **MISSING** — no GAAP/non-GAAP marker on any row. |
| 7 | Source span | **MISSING** — profile: "per-row source not recorded" (akshare Eastmoney/ET endpoints; no per-row provenance). |
| 8 | Definition version | **MISSING** — ratio definitions (e.g. `roic`, `ocf_sales`) not carried. |
| 9 | Correction/refusal state | **MISSING as a field**; this pack records the currency defect here and refuses to pass the currency through as true (§ probe 5 in the adversarial file). |

Bounded sample (2 of 7 rows, verbatim):

- FY2024: `{"fy": 2024, "revenue": 660257000000.0, "ni": 194073000000.0, "gross_profit": 349246000000.0, "eps": 20.938, "eps_diluted": 20.486, "bvps": 106.888420650025, "gross_margin": 52.895463433178, "net_margin": 29.756140412, "roe": 21.77978260955, "roa": 11.558015044185, "roic": 15.347781181841, "debt_ratio": 40.8254374661, "current_ratio": 1.250110226777, "cfo_ps": 28.024215000045, "ocf_sales": 39.154601920161, "rev_growth": 8.4139142714, "ni_growth": 68.4427510068, "currency": "HKD"}`
- FY2025: `{"fy": 2025, "revenue": 751766000000.0, "ni": 224842000000.0, "gross_profit": 422593000000.0, "eps": 24.749, "eps_diluted": 24.153, "bvps": 126.717413491751, "gross_margin": 56.213369585749, "net_margin": 30.5681555165, "roe": 21.134746439818, "roa": 11.771891012023, "roic": 15.246719482251, "debt_ratio": 39.1332260251, "current_ratio": 1.442661556241, "cfo_ps": 33.228526107573, "ocf_sales": 40.312011982452, "rev_growth": 13.8596031545, "ni_growth": 15.8543434687, "currency": "HKD"}`

Total: 7 financial rows (fy2019..fy2025) + `profile` block (industry "软件服务", employees 87412, founded "1999-11-23", domicile "Cayman Islands 开曼群岛（英属）") + `forecast` block. The owner payload carries a forecast block (review finding F10 repair) whose key names are `n_analysts, target_med, target_low, target_high, buy, hold, sell` — third-party consensus, display/qualification fact only, never an expectation lens; no known-at on the forecast block either. **Forecast values not carried (out of scope: no forecast values in an evidence pack).** `evidence_rows: 7`.

`missing_descriptors: ["issuer_subject", "known_at_evidence", "unit_currency", "accounting_basis", "source_span", "definition_version", "correction_refusal_state"]`; `descriptor_notes: {"unit_currency": "CURRENCY_DEFECT_HKD_LABEL_ON_RMB_REPORTED_FINANCIALS", "issuer_subject": "RAW_TICKER_KEY_NO_ISSUER_EVIDENCE", "source_span": "VENDOR_PAYLOAD_NO_FILING_SPAN"}`.

## 6. financials.rmb_80700 — NO_OWNER

Issuer-level snapshot exists only under the HKD-counter key (§5); reachable from the RMB counter only through an issuer link/counter join that does not exist (§2). Would-be owner: Data OS issuer axis (`scripts/build_security_master.py` `apply_issuer_correction` under a new issuer-evidence era in `config/identity_seams.yml`). `evidence_rows: 0`.

## 7. company_events_earnings_calendar.hkd_0700 — PARTIAL

Realized side — same owner family as §3 (`engine/hk_filing_bus.py` over `data/hk_filings/events.parquet`): exactly 1 realized results event in window (2026-08-12, category `interim_results`→`results`). Forward side probed and ABSENT: `data/earnings/earnings.parquet` `8f0575464ba0` (2315 rows, cols `next_date,next_time,eps_forecast,surprises_json,surprises_as_of,as_of`) contains 0 rows matching `0700|TCEHY|Tencent` (exact scan) — the US Nasdaq calendar owner carries no HK name.

```python
python3 -c "
import sys; sys.path.insert(0,'.')
import pandas as pd
en = pd.read_parquet('data/earnings/earnings.parquet')
en[en.astype(str).apply(lambda r: r.str.contains('0700|TCEHY|Tencent', case=False).any(), axis=1)]  # -> 0 rows
"
```

Descriptors as §3 for the realized event (subject ticker-level; period prose-only; known-at `announced_at` + fetch timestamp; unit n/a; dimensions category; basis n/a; span headline hash; definition_version missing; correction state missing). Forward side (coordinator ruling, not a descriptor): **no forward HK earnings-schedule owner exists in the repo** — the absence of a scheduled-date known-at for the next result is recorded in the coverage JSON `notes` list and in this pack's GAPS section (profile: "no forward earnings-date owner for HK names"). Second owner probed: `engine/company_intelligence/event_workspace.py` `production_registry().resolve_ticker('0700.HK', asof=date(2026,10,11))` → `None` (registry holds AAPL, DHI, PHM, KBH, TOL only — Apple + four homebuilders; Tencent not admitted). `evidence_rows: 1` (realized event) + the empty forward query.

`missing_descriptors: ["issuer_subject", "reporting_period", "definition_version", "correction_refusal_state"]`; `descriptor_notes: {"issuer_subject": "RAW_TICKER_KEY_NO_ISSUER_EVIDENCE"}`.

## 8. company_events_earnings_calendar.rmb_80700 — PARTIAL

The owner serves the same issuer-level realized event (§7) whose raw `stock_code` list contains `80700` and whose tape row shows `ticker=0700.HK` — the value is returned, its issuer_subject is missing for this counter (row `news_id=12280990`; dual-counter fold check in adversarial probe 6). The counter join needs a security_id that does not exist. Would-be owner: D2B2 CN/HK admission counter seam. `evidence_rows: 1`. `missing_descriptors: ["issuer_subject", "reporting_period", "definition_version", "correction_refusal_state"]`; `descriptor_notes: {"issuer_subject": "ROW_STOCK_CODE_LISTS_80700_NO_SECURITY_ID"}`.

## 9. market_data_daily.hkd_0700 — PARTIAL

Owner: `collectors/hk_stock_prices.py` store `data/hk_stocks/0700.HK.parquet` `b439ba667ff8`; second store `data/hk_search/closes_deep.parquet` `0ed0dc4075e3` (`collectors/hk_closes_deep.py`).

```python
python3 -c "
import sys; sys.path.insert(0,'.')
import pandas as pd
px = pd.read_parquet('data/hk_stocks/0700.HK.parquet')
px.tail(); px.index.min(); px.index.max(); len(px)
cd = pd.read_parquet('data/hk_search/closes_deep.parquet')['0700.HK'].dropna()
len(cd); cd.index.min(); cd.index.max()
"
```

| # | Descriptor | Owner record |
|---|---|---|
| 1 | Issuer subject | File key `0700.HK` → `SEC:HK-XHKG-00700` (vendor alias, §1/§2 identity calls); file carries no identity columns. |
| 2 | Reporting period | Session date = the DatetimeIndex (daily HK session). Span `2004-06-16..2026-10-09`, 5485 rows (in-store). |
| 3 | Known-at evidence | Event time only (session date). **No first_public field; no per-row collector-observation timestamp; no store receipt** (`data/hk_stocks/latest.json` is a beta-setups receipt `{"date": "2026-10-09", "label": "24 beta exposures", "n_setups": 24}`, not a price-store receipt). |
| 4 | Unit/currency | **Not carried in-store** — columns are bare `open, close, high, low, volume`; currency is inferred from the counter key (HKD), i.e. consumer-side, not owner-recorded. `auto_adjust=True` per profile: prices are total-return-adjusted, no raw series. |
| 5 | Dimensions | OHLCV only — no counter, venue, currency or adjustment-factor columns. |
| 6 | Accounting basis | n/a. |
| 7 | Source span | yfinance .HK daily (profile); per-row provenance not carried. closes_deep: 5511 non-null closes `2004-06-16..2026-10-09`, spliced dividend-adjustment vintages (DSC:HK-DEEP-PANEL-SPLICES-ADJUSTMENT-VINTAGES). |
| 8 | Definition version | **MISSING** — adjustment-vintage semantics (yfinance auto_adjust; overwrite_overlap re-adjust) not pinned in-store. |
| 9 | Correction/refusal state | **MISSING** — a frozen window can drift between runs with no vintage stamp (profile note; exercised in adversarial probe 2). |

Bounded sample (last 3 sessions, verbatim owner reprs, re-run 2026-10-11): `2026-10-07 O=425.6000061035156 C=420.6000061035156 H=426.0 L=419.20001220703125 V=12436640.0` · `2026-10-08 O=422.0 C=411.3999938964844 H=424.6000061035156 L=411.20001220703125 V=30202875.0` · `2026-10-09 O=415.0 C=424.79998779296875 H=425.79998779296875 L=414.79998779296875 V=20422500.0`. First row (verbatim): `2004-06-16 O=0.7414216975235196 C=0.7032909989356995 H=0.7837888238541417 L=0.6905816609207049 V=2385268337.0` (adjusted). closes_deep 0700.HK tail: `2026-10-07=420.6000061035156, 2026-10-08=411.3999938964844, 2026-10-09=424.79998779296875`. Total rows: 5485 (prices) / 5511 (closes_deep). `evidence_rows: 4`.

`missing_descriptors: ["known_at_evidence", "unit_currency", "definition_version", "correction_refusal_state"]`.

## 10. market_data_daily.rmb_80700 — NO_OWNER

No price series for 80700 in any owner store: `data/hk_stocks/` holds no `80700.HK.parquet` (directory listing, exact); closes_deep columns contain no 80700 key. Would-be owner: `collectors/hk_stock_prices.py` (universe via `collectors/hk_universe.py`) after a Data OS counter security_id exists. The HKD counter is NEVER substituted (profile note). `evidence_rows: 0`.

## 11. market_data_intraday.hkd_0700 — NO_OWNER

No intraday owner: profile `owner: []`, "none licensed (HKEX historical full book / OMD-C are paid)". Probed: `data/intraday_flow/ledger.parquet` `bf5e0fa0011b` (7424 rows, US tickers; `ticker=='0700.HK'` → 0 rows). Would-be owner: Chairman procurement decision, then a new HK intraday collector. `evidence_rows: 0`.

## 12. market_data_intraday.rmb_80700 — NO_OWNER

Same as §11 for the RMB counter (no series, no options, procurement-blocked). `evidence_rows: 0`.

## 13. corporate_actions_adjustment.hkd_0700 — ABSENT

Owners exist and were queried; no corporate-action rows returned for this subject:

```python
python3 -c "
import sys; sys.path.insert(0,'.')
import pandas as pd
pl = pd.read_parquet('data/hk_placements/events.parquet')
pl[pl.astype(str).apply(lambda r: r.str.contains('0700', regex=True).any(), axis=1)]   # -> 0 rows (exact-code scan also 0: no 00700 row)
from engine import hk_filing_bus as bus
ev = pd.read_parquet('data/hk_filings/events.parquet')
tape = bus.build_tape(ev, pd.read_parquet('data/hk_placements/events.parquet'))
tape[(tape['ticker']=='0700.HK') & (tape['category'].isin(['buyback','placement','mandate']))]  # -> 0 rows
"
```

`data/hk_placements/events.parquet` (810 rows per profile) holds no row for this counter (placements key on the HKEXnews 'placing' headline category). `build_tape` classification of the only Tencent event gives `dilution_flag=False, buyback_flag=False`. Adjustment factors are not stored anywhere (implicit in yfinance `auto_adjust=True`; no explicit HK corporate-action ledger — `engine/capital_structure/` is SEC-only). Share count: NO owner carries one (searched: security_master, vendor_aliases, fundamentals payloads, placements output — profile note; confirmed by probe 1 in the adversarial file, whose implied denominators are probe-derived, not owner values, never carried as capital-structure values). Exact query + empty result recorded → ABSENT. `evidence_rows: 0`.

## 14. corporate_actions_adjustment.rmb_80700 — NO_OWNER

No corporate-action or adjustment ledger for the RMB counter (no prices to adjust; no identity). Would-be owner: `collectors/hk_stock_prices.py` + a Data OS counter security_id. `evidence_rows: 0`.

## 15. sessions_calendar.hkd_0700 — PARTIAL

Owner: `lib/hk_calendar.py` `5ffb5af43465` — pure rule arithmetic + annual HKEX notices compiled into the module (`holidays(year)`, `announced_holidays`, `is_session`, `last_session_on_or_before`, `expected_last_session`, `sessions_between`, `sessions_behind`, `early_close`, HKT ZoneInfo).

```python
python3 -c "
import sys; sys.path.insert(0,'.')
import datetime as dt
from lib import hk_calendar as hkc
hkc.is_session(dt.date(2026,10,9))   # -> True
hkc.is_session(dt.date(2026,10,11))  # -> False (Sunday)
hkc.last_session_on_or_before(dt.date(2026,10,11))  # see run output below
"
```

| # | Descriptor | Owner record |
|---|---|---|
| 1 | Issuer subject | Venue-level: HKEX cash equities — applies to the 00700 counter by venue membership; the owner serves it without any security id (identity not needed). |
| 2 | Reporting period | The queried date(s) themselves (session-date clock, HKT). |
| 3 | Known-at evidence | **MISSING as an owner record** — the holiday rules live as module code constants with NO publication known-at for the rule set (`HOLIDAY_RULES_IN_CODE_NO_PUBLICATION_KNOWN_AT`); the git blob pin `5ffb5af43465` and the evaluation call-time timestamp are PACK-SIDE, not owner-recorded (review findings 3/15 + ruling d; the Alibaba pack records the same owner the same way). Function semantics: `is_session` returns the calendar verdict for any date. |
| 4 | Unit/currency | Boolean session verdict / dates; data expectation times 17:30 HKT regular, 13:30 HKT half-day (module constants + profile). |
| 5 | Dimensions | HKEX cash equities, HKT timezone (`ZoneInfo`), full-day closures + announced half days. |
| 6 | Accounting basis | n/a. |
| 7 | Source span | Computed for any date (functions total over the year set); `holidays(year)` → frozenset per year. |
| 8 | Definition version | **MISSING** — no version constant in the owner module: `grep -n -i version lib/hk_calendar.py` returns no line (re-run 2026-10-11); the git blob pin is a pack-side pin, not an owner-recorded version (`NO_VERSION_CONSTANT_IN_OWNER_MODULE`). |
| 9 | Correction/refusal state | None observed; HKEX notices enter as announced constants (append-only within the module vintage). |

Run output observed: `is_session(2026-10-09) → True`; `is_session(2026-10-11) → False` (Sunday). `evidence_rows: 2`.

`missing_descriptors: ["known_at_evidence", "definition_version"]`; `descriptor_notes: {"known_at_evidence": "HOLIDAY_RULES_IN_CODE_NO_PUBLICATION_KNOWN_AT", "definition_version": "NO_VERSION_CONSTANT_IN_OWNER_MODULE"}`.

## 16. sessions_calendar.rmb_80700 — PARTIAL

Same owner, same verdicts: `is_session(2026-10-09) → True`, `is_session(2026-10-11) → False`. Same session for HKD and RMB counters (profile note; the calendar is venue-level, no counter identity needed — the owner serves this RMB-counter cell natively, PARTIAL on the same two descriptors). Same nine descriptors as §15. `evidence_rows: 2`.

`missing_descriptors: ["known_at_evidence", "definition_version"]`; `descriptor_notes: {"known_at_evidence": "HOLIDAY_RULES_IN_CODE_NO_PUBLICATION_KNOWN_AT", "definition_version": "NO_VERSION_CONSTANT_IN_OWNER_MODULE"}`.

## 17. southbound_holdings.hkd_0700 — PARTIAL

Owner: `engine/hk_southbound_stocks.py` `latest_holdings(allow_fetch=False)` (read-only) over `data/hk_southbound/holdings.parquet` `652e2502ad31` + `data/hk_southbound/backfill_gap_audit.json` `8b120d560ab5`; roster `data/hk_connect_roster/roster.parquet` `3a2affa41b0c`.

```python
python3 -c "
import sys; sys.path.insert(0,'.')
from engine import hk_southbound_stocks as sbs
sbs.latest_holdings(allow_fetch=False).xs('0700.HK', level='ticker') if False else None
import pandas as pd
sb = pd.read_parquet('data/hk_southbound/holdings.parquet')
sb[sb.index.get_level_values('ticker')=='0700.HK'].tail(2)
"
```

| # | Descriptor | Owner record |
|---|---|---|
| 1 | Issuer subject | Index key `ticker=0700.HK`; `name="腾讯控股"` (display string, zh; no issuer id). |
| 2 | Reporting period | Holding date (T) = DatetimeIndex `date`; span `2024-07-10..2026-10-09`, 477 rows. |
| 3 | Known-at evidence | In-row date = holding date; observation = daily snapshot run, not per-row stamped; gap audit `updated=2026-10-11`, `n_dates=523`, `n_gaps=9` — full gap DATE list re-run 2026-10-11 from `data/hk_southbound/backfill_gap_audit.json`: `2024-09-13→2024-09-19` (4 bdays), `2024-09-30→2024-10-08` (6), `2025-01-27→2025-02-05` (7), `2025-04-30→2025-05-06` (4), `2025-09-30→2025-10-09` (7), `2026-02-13→2026-02-24` (7), `2026-04-02→2026-04-08` (4), `2026-04-30→2026-05-06` (4), `2026-09-30→2026-10-08` (6). |
| 4 | Unit/currency | `own_pct` percent; `hold_shares` shares; `hold_mktcap`/`chg5_v`/`chg10_v` vendor value fields with **no currency column** (HKD implied by venue — consumer-side inference, not owner-recorded). `close=424.8` on 2026-10-09. |
| 5 | Dimensions | `hold_mktcap, hold_shares, own_pct, free_pct, chg5_v, chg10_v, add_amp, close` (+ name). |
| 6 | Accounting basis | n/a. |
| 7 | Source span | Eastmoney datacenter mirror of HKEX Southbound holdings (third-party, UNVERIFIED rights); per-row provenance not carried. |
| 8 | Definition version | **MISSING** (`OWN_PCT_DENOMINATOR_UNVERSIONED`) — the `own_pct` **denominator is not carried** (adversarial probe 1: implied total shares from `hold_shares/own_pct` = 9098091680.672268 — probe-derived, not an owner value, never carried as a capital-structure value; no capital-structure version binds it). |
| 9 | Correction/refusal state | Gap audit is the only store-level quality record; value changes are price-contaminated per profile (no per-row flag). |

Bounded sample (last 2 of 477 rows, verbatim owner reprs except own_pct, re-run 2026-10-11): `2026-10-08 | hold_mktcap=445411635174.0 | hold_shares=1082672910.0 | own_pct=(A11-REFUSED as a denominator-bearing value — HKEX-reported issued-share denominator, no canonical capital-structure version; raw in-row value not displayed) | free_pct=nan | close=411.4` · `2026-10-09 | hold_mktcap=459919452168.0 | hold_shares=1082672910.0 | own_pct=(A11-REFUSED as a denominator-bearing value — HKEX-reported issued-share denominator, no canonical capital-structure version; raw in-row value not displayed) | free_pct=nan | close=424.8`. Roster probe: `data/hk_connect_roster/roster.parquet` exact match for `0700`/`80700` → 0 rows (the roster records changes only; inclusion predates the roster window). `evidence_rows: 2`.

A11 handling: in this pack any `own_pct` value is shown only as "A11-REFUSED as a denominator-bearing value — HKEX-reported issued-share denominator, no canonical capital-structure version"; `hold_shares` stays a sample value.

`missing_descriptors: ["known_at_evidence", "unit_currency", "definition_version", "correction_refusal_state"]`; `descriptor_notes: {"definition_version": "OWN_PCT_DENOMINATOR_UNVERSIONED"}`.

## 18. southbound_holdings.rmb_80700 — NO_OWNER

Exact query: `sb[sb.index.get_level_values('ticker')=='80700.HK']` → 0 rows; roster exact match → 0 rows. No owner artifact establishes whether the RMB counter is Southbound-eligible (a missing change row is not an eligibility verdict). Would-be owner: `collectors/hk_southbound_holdings.py` after a Data OS counter security_id exists. `evidence_rows: 0`.

## 19. short_positions.hkd_0700 — PARTIAL

Owner: `collectors/hk_shorts.py` store `data/hk_shorts/positions.parquet` `7843b8775acf` + `data/hk_shorts/coverage.json`; admission receipt `_receipt.json` `f51ffbd63c62` (SFC = the admitted Data OS HK identity-evidence source).

```python
python3 -c "
import sys; sys.path.insert(0,'.')
import pandas as pd
sp = pd.read_parquet('data/hk_shorts/positions.parquet')
h = sp[sp['ticker']=='0700.HK'].sort_values('date'); h.tail(2)
"
```

| # | Descriptor | Owner record |
|---|---|---|
| 1 | Issuer subject | `ticker=0700.HK`, `stock_code=700` (int64, no leading zero — see below), `stock_name='TENCENT'`; master id `SEC:HK-XHKG-00700` NO_ISSUER_EVIDENCE via §identity calls. |
| 2 | Reporting period | Position date = `date` column (SFC aggregated reportable short position AT that date); span `2012-08-31..2026-10-02`, 735 rows. |
| 3 | Known-at evidence | **PARTIAL** — position date only; the SFC publication lag is NOT carried as a field (profile + store columns `date, stock_code, ticker, stock_name, shorted_shares, value_hkd`). |
| 4 | Unit/currency | `shorted_shares` = shares; `value_hkd` = HKD (column name; no separate currency field). |
| 5 | Dimensions | Weekly aggregate per counter; no breakdown by reporter. |
| 6 | Accounting basis | n/a. |
| 7 | Source span | SFC aggregated reportable short positions (official, weekly), the admitted CN/HK identity-evidence source per `_receipt.json` `china_hk_admission.evidence_sources.hk`; per-row provenance not carried. |
| 8 | Definition version | **MISSING** — "reportable short position" SFC definition version not carried. |
| 9 | Correction/refusal state | **MISSING** — no restatement/correction field. |

Bounded sample (last 2 of 735 rows, verbatim): `2026-09-25 | stock_code=700 | TENCENT | shorted_shares=70196706 | value_hkd=30647881840` · `2026-10-02 | stock_code=700 | TENCENT | shorted_shares=75217572 | value_hkd=31681641326`. Key-format note (owner-recorded inconsistency): HKD-counter rows key `stock_code=700` (int64) while RMB-counter rows key `80700` — an exact-code join across the two counters of the same economic security fails on format. Row counts re-run with the int form (review finding F12; `stock_code` dtype is int64, so string predicates match nothing): `sp[sp['stock_code']==700]` → 735 rows `2012-08-31..2026-10-02`; `sp[sp['stock_code']==80700]` → 172 rows `2023-06-23..2026-10-02`. Coverage receipt: `{"our_universe": 158, "latest_sfc_names": 1242, "covered": 153, "coverage_pct": 96.8, "latest_date": "2026-10-02", "h2a_eligible": true}`. `evidence_rows: 2`.

`missing_descriptors: ["known_at_evidence", "definition_version", "correction_refusal_state"]`.

## 20. short_positions.rmb_80700 — PARTIAL

Same owner and store: 172 weekly rows keyed `stock_code=80700` (int64), `ticker='80700.HK'`, `stock_name='TENCENT-R'`, span `2023-06-23..2026-10-02` — the owner RETURNS values for the RMB counter (raw counter key, no identity needed to return them). Last 2 of 172 (verbatim): `2026-09-25 | 80700 | TENCENT-R | shorted_shares=14200 | value_hkd=6133406` · `2026-10-02 | 80700 | TENCENT-R | shorted_shares=123203 | value_hkd=51282017`. `missing_descriptors: ["issuer_subject", "known_at_evidence", "unit_currency", "definition_version", "correction_refusal_state"]`; `descriptor_notes: {"issuer_subject": "NO_SECURITY_ID_FOR_80700", "unit_currency": "VALUE_COLUMN_CURRENCY_CONVENTION_FOR_RMB_COUNTER_NOT_RECORDED"}` — `issuer_subject` because no security_id exists (TENCENT-R is a display string, never pooled with the HKD counter), `unit_currency` because the `value_hkd` column is HKD-labelled even for the CNH counter with the convention unrecorded in-row (defect recorded, never relabelled). `evidence_rows: 2`.

## 21. adr_h_basis.hkd_0700 — ABSENT

Cross-pack ruling: the basis metric records ABSENT. `engine/hk_adr_bridge.snapshot()` returns implied-open CONTEXT, not a basis/ratio value, and no owner carries the ADS-to-ordinary ratio — the Alibaba pack records the same bridge output as ABSENT, and this pack now matches. The verbatim bridge row is kept below as ADJACENT OWNER OUTPUT (what the owner actually returns for this subject); the owner itself records `adr_ticker KWEB`, `adr_source "proxy"`, `display_only true` — a KWEB ETF proxy is not a Tencent security. `evidence_rows: 0` for the basis metric.

Owner: `engine/hk_adr_bridge.py` `snapshot()` (pure read; the writer variant `run()` was deliberately NOT executed).

```python
python3 -c "
import sys; sys.path.insert(0,'.')
import datetime as dt, json
from engine.hk_adr_bridge import snapshot
snap = snapshot(hk_session_date=dt.date(2026,10,9))
[n for n in snap['names'] if n['hk_ticker']=='0700.HK']
"
```

Adjacent owner output (verbatim): `{"hk_ticker": "0700.HK", "hk_name_en": "Tencent", "hk_name_zh": "腾讯", "adr_ticker": "KWEB", "adr_source": "proxy", "proxy_note": "proxy, no direct ADR; Tencent OTC (TCEHY) too thin", "implied_open_gap_pct": 3.79, "adr_move_pct": 3.79, "hk_last_move_pct": 3.26, "gap_context": "strong_up", "disconnect_flag": false, "missing_reason": null, "freshness": {"asof": "2026-10-09", "lag_days": 0, "state": "fresh"}}`; snapshot-level `display_only: true`, `hk_session_date=2026-10-09`, `adr_date=2026-10-09`.

Why this is not a basis value: the row's own fields are an implied-open gap CONTEXT row (`implied_open_gap_pct`, `gap_context`, `disconnect_flag`) over a PROXY leg (`adr_source: "proxy"`, `proxy_note` "proxy, no direct ADR; Tencent OTC (TCEHY) too thin"), explicitly `display_only` at snapshot level. An ADS/H-share basis needs an ADS-to-ordinary ratio; TCEHY (the OTC line) is NOT admitted as a security and no owner carries the ratio — the profile: "A proxy is not a basis; a TCEHY basis would need Data OS admission of the OTC ADR plus a carried ADS ratio". TCEHY was never pulled in as a counter (frozen-spec compliance). Stale-comment finding recorded: `data/yahoo/TCEHY.parquet` exists (4216 rows 2010-01-05..2026-10-08) but the bridge comment still says it is not in the yahoo store. `missing_descriptors: []`; `evidence_rows: 0` (no basis value exists to evidence).

## 22. adr_h_basis.rmb_80700 — NO_OWNER

No RMB-counter basis: no counter prices (§10), no ADR counter; profile `owner: []`, state NONE. Would-be owner: `engine/hk_adr_bridge.py` after counter prices exist (diagnostic only even then). `evidence_rows: 0`.

## 23. fx.hkd_0700 — PARTIAL

Owners: `data/hk/HKD_X.parquet` `826468c71fd6` (USD/HKD), `data/fred/DEXCHUS.parquet` `5f5898b2b6d3` (USD/CNY), `data/hkma/interbank_liquidity.parquet` `b5f2ad5b9f96` (context only, not spot FX).

```python
python3 -c "
import sys; sys.path.insert(0,'.')
import pandas as pd
pd.read_parquet('data/hk/HKD_X.parquet').tail(2)
pd.read_parquet('data/fred/DEXCHUS.parquet').tail(2)
"
```

Observed (verbatim owner reprs, re-run 2026-10-11): HKD_X — cols `close,volume`, 6419 rows, last rows `2026-10-10 close=7.8471999168396` and `2026-10-11 close=7.84689998626709` (USD/HKD, HKD per USD; peg-banded). DEXCHUS — col `fx_cny_usd`, 11421 rows, last `2026-10-01=6.7038, 2026-10-02=6.7038` (USD/CNY, NY noon fix).

Descriptors: issuer subject = the FX legs the Tencent cells convert against (venue-leg series, not issuer rows); reporting period = daily bar date (in-row); known-at = bar date only — HKD=X close convention undeclared (profile), DEXCHUS is NY-noon; unit/currency = **not carried in-store** (bare `close` columns; pair identity comes from file name + profile, consumer-side); dimensions = single series per file, no pair column; accounting basis n/a; source span = `2001-07-16..2026-10-11` observed (HKD leg; profile recorded through 10-10 — the store advanced one day between E0's read and this pack) and `1981-01-02..2026-10-02` (CNY leg); definition version **MISSING**; correction state **MISSING** (profile: "a fixed peg constant must never stand in for the observed USD/HKD series" — no in-store guard). No admitted Data OS FX owner (profile: both legs are vendor/public mirrors). `evidence_rows: 2`.

`missing_descriptors: ["known_at_evidence", "unit_currency", "definition_version", "correction_refusal_state"]`.

## 24. fx.rmb_80700 — PARTIAL

Owners: `data/forex/latest.json` `0e41dead4a2f` (desk snapshot) + `data/china/CNH_F.parquet` `fe01ca5a6dcb` (CME offshore-CNH futures). Observed (verbatim owner reprs, re-run 2026-10-11): `latest.json` `date="Oct 09, 2026", asof="2026-10-09"`, `pairs.USDCNH = {"label": "USD/CNH", "quote": 6.6685, "chg": -0.6, "action": "FLAT", "score": 15.0, ...}` (the `score`/`action` fields are the desk snapshot's own risk-context display fields — recorded here as what the owner returns, no authority asserted); CNH_F — cols `close,volume`, 3368 rows `2013-02-11..2026-10-09`, last `2026-10-08 close=6.672999858856201, 2026-10-09 close=6.663000106811523` (a FUTURES contract, not spot CNH).

Descriptors: issuer subject = RMB-counter currency legs (CNH); reporting period = snapshot date / bar date (in-row); known-at = `asof=2026-10-09` (snapshot) and bar dates; unit/currency = `USD/CNH` label present in latest.json pair record but **CNH_F carries bare `close,volume` with no pair field** (consumer-side); dimensions = snapshot pairs vs futures series; accounting basis n/a; source span = `2013-02-11..2026-10-09` (futures proxy); definition version **MISSING** (`SETTLEMENT_CONVENTION_NOT_RECORDED` — futures settlement convention undeclared); correction state **MISSING** (`FUTURES_SERIES_NOT_SPOT_RATE` — no flag distinguishes futures from spot), and onshore CNY (DEXCHUS, CNY=X) is not silently substituted in this pack (profile rule). No spot CNH history; no CNH/HKD cross exists in any owner. `evidence_rows: 2`.

`missing_descriptors: ["known_at_evidence", "unit_currency", "definition_version", "correction_refusal_state"]`; `descriptor_notes: {"correction_refusal_state": "FUTURES_SERIES_NOT_SPOT_RATE", "definition_version": "SETTLEMENT_CONVENTION_NOT_RECORDED"}`.

## 25. options.hkd_0700 — NO_OWNER

Profile `owner: []` — "none (HKEX SOM full book / trade file are paid first-party products)". No store to query (`data/options_skew/` is index-options shaped, no 0700 single-stock options owner). Would-be owner: Chairman procurement decision, then an HK options owner. `evidence_rows: 0`.

## 26. options.rmb_80700 — NO_OWNER

Same as §25 for the RMB counter; no owner artifact establishes whether any option class references the counter. `evidence_rows: 0`.

## 27. research_vault.hkd_0700 — PARTIAL

Owner: `engine/research_vault/catalog.py` `parse_strict` (fail-closed strict read) over `data/research_vault/catalog.json` `f18851fb4cfc`.

```python
python3 -c "
import sys; sys.path.insert(0,'.')
import json
from engine.research_vault import catalog as cm
cat = cm.parse_strict(open('data/research_vault/catalog.json','rb').read())
items = cat['items']
pat = lambda it: ('tencent' in json.dumps({k: it.get(k) for k in ('title','tickers','tags')}, ensure_ascii=False).lower()) or ('腾讯' in json.dumps({k: it.get(k) for k in ('title','tickers','tags')}, ensure_ascii=False))
[h['id'] for h in items if pat(h)]
"
```

Observed: `schema="research_vault.catalog.v1"`, `generated_at="2026-10-11T17:21:24.249634+00:00"`, `count=2820`. Tencent-name pattern `tencent|腾讯` over `title`+`tickers`+`tags` → **1 item**: `marketdesk-58kvinf7h6l-7b504f | "GS Asia Tencent Capex Shock Masks Core Franchise Strength" | published_at=2026-08-13T19:08:59Z | tickers=[]`. Broader full-item-text pattern → 13 items. (The E0 profile recorded 19 of 2778 with its pattern at its data read `eb55c8573d94`; the catalog has since advanced to 2820 items — the census bound is pattern-dependent and time-vintage-dependent, exactly why it is a bound and not a subject link.)

Descriptors: issuer subject = **MISSING** — name-pattern census bound only; subject binding to an issuer id NOT established (`NO_ISSUER_BINDING_ON_CATALOG_ITEMS`; profile; confirmed — item `tickers=[]` on the title hit); reporting period = item `published_at` per row (owner-recorded); known-at = `published_at` + catalog `generated_at` (both owner-recorded); unit n/a (documents); dimensions = `institution, side, desk, language, pages, top_pick, tags` (owner-recorded; `language` field exists per item); accounting basis n/a; source span = item id + title + `summary_points` metadata (private full text NOT fetched — profile + pack rule); definition version = **MISSING for the subject match** (`SUBJECT_MATCH_RULE_IS_PACK_SIDE_NOT_OWNER_VERSIONED`) — the catalog's own schema version is owner-recorded (`schema="research_vault.catalog.v1"`), but the rule that binds catalog items to Tencent is a pack-side name pattern with no owner-recorded version; correction state = `needs_metadata` flag per item (owner-recorded quality flag). `evidence_rows: 1` (title-match item) + census counts.

`missing_descriptors: ["issuer_subject", "definition_version"]`; `descriptor_notes: {"issuer_subject": "NO_ISSUER_BINDING_ON_CATALOG_ITEMS", "definition_version": "SUBJECT_MATCH_RULE_IS_PACK_SIDE_NOT_OWNER_VERSIONED"}`.

## 28. research_vault.rmb_80700 — NO_OWNER

Issuer-level items only (§27); no counter join — serving the RMB counter needs the counter seam. Would-be owner: D2B2 CN/HK admission. `evidence_rows: 0`.

## 29. news.hkd_0700 — PARTIAL

Owner: `collectors/hk_gdelt.py` store `data/hk_gdelt/tencent.parquet` `eb31dec7222b`.

```python
python3 -c "
import sys; sys.path.insert(0,'.')
import pandas as pd
gd = pd.read_parquet('data/hk_gdelt/tencent.parquet'); gd.tail(2)
"
```

Observed: 78 daily rows, index date, cols `entity_query, ticker, vol_intensity, avg_tone`; `entity_query='Tencent'`, `ticker='0700.HK'` on every row. Sample (verbatim owner reprs, first 2 + last 2): `2026-07-13 vol_intensity=nan avg_tone=1.1061` · `2026-07-14 vol_intensity=nan avg_tone=1.5599` · `2026-10-08 vol_intensity=nan avg_tone=0.0` · `2026-10-10 vol_intensity=nan avg_tone=0.98`. Span `2026-07-13..2026-10-10`.

Descriptors: issuer subject = **MISSING** — topic key `entity_query='Tencent'` + `ticker='0700.HK'` is a NAME query, not an issuer id (`NAME_QUERY_NOT_ISSUER_ID`; topic-level, not issuer-resolved per profile); reporting period = UTC aggregation day (in-row index); known-at = **MISSING** — aggregation day only (no collection timestamp in-row); unit/currency = **UNDECLARED** (`TONE_AND_VOLUME_MEASURES_UNDECLARED`) — `vol_intensity` and `avg_tone` carry no unit/scale metadata anywhere in-store; dimensions = 2 measures; accounting basis n/a; source span = GDELT aggregates, no article text (profile); definition version **MISSING**; correction state **MISSING**; plus NaN cells present inside the returned values (4 of 4 sampled rows carry `vol_intensity=nan`). `evidence_rows: 4`.

`missing_descriptors: ["issuer_subject", "known_at_evidence", "unit_currency", "definition_version", "correction_refusal_state"]`; `descriptor_notes: {"issuer_subject": "NAME_QUERY_NOT_ISSUER_ID", "unit_currency": "TONE_AND_VOLUME_MEASURES_UNDECLARED"}`.

## 30. news.rmb_80700 — NO_OWNER

No counter key in the GDELT store (every row keyed `0700.HK`; exact scan finds no 80700 topic). Would-be owner: collectors/hk_gdelt.py after CN/HK admission mints the counter (identity needed to key a topic). `evidence_rows: 0`.

## 31. themes.hkd_0700 — PARTIAL

Owner: `engine/theme_graph/identity_resolution.py` (+ `store.py`, `rights.py`) store `data/theme_graph/identity_resolution.parquet` `c84db448b957`.

```python
python3 -c "
import sys; sys.path.insert(0,'.')
import pandas as pd
ir = pd.read_parquet('data/theme_graph/identity_resolution.parquet')
r = ir[ir['node_id']=='co:hk:0700.HK']; len(r); r.tail(1).to_dict('records')
"
```

Observed latest of 61 snapshots for `co:hk:0700.HK` (verbatim): `schema="gmi.identity_resolution/v1" | node_id="co:hk:0700.HK" | graph_kind=company | market_scope=hk | graph_identity_epoch=1 | source_native_symbol="0700.HK" | resolution_asof=2026-10-09 | resolution_state="RESOLVED" | issuer_id=NaN | security_id="SEC:HK-XHKG-00700" | listing_key="HK-XHKG-00700" | join_method="vendor_alias" | master_generated_at=2026-10-09T05:05:32 | master_symbol_directory_snapshot=2026-10-09 | master_code_version="cdbcd143dcfa419ab0637bc11dd4c80368143e2e" | refusal_reason=NaN | source_receipts={"matched_vendors": ["theme_graph_native"], "security_id": "SEC:HK-XHKG-00700"} | computed_at=2026-10-09T14:11:26Z | engine_version="theme_graph.v1"`.

Eight of nine descriptors owner-recorded; issuer subject MISSING (review finding F5 repair): the owner's node resolves to SECURITY only — `security_id=SEC:HK-XHKG-00700` with `issuer_id=NaN` in the owner's own row, i.e. the owner explicitly carries NO issuer evidence for this subject (`GRAPH_NODE_RESOLVES_TO_SECURITY_ONLY_NO_ISSUER_EVIDENCE`), so the issuer_subject descriptor is missing, not owner-recorded. reporting period = `resolution_asof=2026-10-09` (snapshot clock); known-at = `computed_at=2026-10-09T14:11:26Z` + `master_generated_at=2026-10-09T05:05:32`; unit n/a (identifier row); dimensions = `graph_kind, market_scope, graph_identity_epoch, join_method, engine_version`; accounting basis n/a; source span = `source_receipts` JSON + `master_symbol_directory_snapshot` + `master_code_version`; definition version = `schema="gmi.identity_resolution/v1"`; correction/refusal state = `refusal_reason` field (NaN here) + append-only 61-snapshot history + `graph_identity_epoch`. Total rows: 61. Theme membership = display/context only; evidence-row rights governed by `engine/theme_graph/rights.py`, not adjudicated here. `evidence_rows: 1` (full latest snapshot) + 61-row count.

`missing_descriptors: ["issuer_subject"]`; `descriptor_notes: {"issuer_subject": "GRAPH_NODE_RESOLVES_TO_SECURITY_ONLY_NO_ISSUER_EVIDENCE"}`.

Snapshot history composition (seat check 2026-10-11, same blob `c84db448b957`, grouped by `resolution_state` over the 61 `co:hk:0700.HK` rows):

| resolution_state | snapshots | first `resolution_asof` | last `resolution_asof` | security_id | join_method | refusal_reason |
|---|---|---|---|---|---|---|
| NOT_IN_MASTER | 5 | 2026-08-18 | 2026-08-20 | null | `refused` | "no security-master or vendor-alias row resolves this symbol" |
| RESOLVED | 56 | 2026-08-20 | 2026-10-09 | `SEC:HK-XHKG-00700` | `vendor_alias` | null |

Point-in-time consequence (A07): a then-known view dated before the master row's own `ingested_at=2026-08-20 18:50:35` has NO security id for 0700.HK. The owner refused it in those snapshots, so the id must not be back-filled into them.

## 32. themes.rmb_80700 — NO_OWNER

No company node and no identity_resolution row for the RMB counter (exact scan: 0 rows matching 80700 in `node_id`/`source_native_symbol`). CN/HK admission is node-driven, so the missing node is also why the counter has no security_id. Would-be owner: D2B2 CN/HK admission. `evidence_rows: 0`.

## 33. evaluation_qledger.hkd_0700 — ABSENT

Owner store exists and was queried; returned nothing for this subject. Exact query: line scan of `data/qledger/claims.jsonl` `344d38dd4dca` (118022 lines, re-counted 2026-10-11) + `data/qledger/grades.jsonl` `94adcdf95da8` (grades file scanned for the same keys), searching claim scope fields (`scope`, `tickers`, `symbols`, `subject`) for `0700`, `80700`, `tencent` → **0 claims**. Raw substring grep counts RE-RUN 2026-10-11 (pasted output): `grep -c '0700' data/qledger/grades.jsonl` → `406`; `grep -c '0700' data/qledger/claims.jsonl` → `143`; `grep -c '80700'` → `4` in each; `grep -ic 'tencent'` → `0` in each — all numeric substrings of prices/levels, NOT scope matches (demonstrated by inspecting the first hit's fields; the scope key shape is `{"type": "entity", "key": "CARR"}`-style US entity keys). Profile: V0 (SNI claim contracts) is not on main; #8042 is a held carrier. `evidence_rows: 0`.

TCEHY disclosure (repair R5; no identity link joins TCEHY to 0700/Tencent and none was created): a `json.loads` scope-key filter over `claims.jsonl` re-run 2026-10-11 finds **20 claims with `scope.key=='TCEHY'`** (by `claim_family`: `us_importance_v0` 10, `us_importance_v0_pit` 10), while TCEHY has **0 matching rows in `data/reference/security_master.parquet`** and **0 matching rows in `data/reference/vendor_aliases.parquet`** (whole-frame substring scans, output verbatim above in §2's method). TCEHY is an unadmitted OTC line: the claims exist under a ticker key with no Data OS identity. Would-be owner for closing this gap: "Data OS OTC ADR admission (scripts/build_security_master.py) then engine/qledger.py via the V0 contract lane" (see GAPS).

## 34. evaluation_qledger.rmb_80700 — ABSENT

Same scan for `80700` → 0 claims. `evidence_rows: 0`.

## 35. behavioral_pilot.hkd_0700 — ABSENT

Owner exists (frozen August-2026 research pilot, `engine/stock_identity/pilot.py`) and was queried: `data/stock_identity/fingerprints/pilot_fingerprint_v0.parquet` `cd7675e995b4` — 21 US symbols (AEM, AG, BABA, CBRS, FFAI, GOLD, HL, KO, KRUS, MCD, MCK, META, MSFT, NEM, NVDA, PAAS, REGN, UEC, WMT, WPM, YELP), `asof` range `2026-08-13..2026-08-13`; `0700` appears in NO symbol (exact scan). HISTORICAL per profile: not a live owner; absence blocks nothing in C2/S0. Authority columns exist and are ALL FALSE (`authority_can_rank/size/gate/originate_signal/escalate` — verified no True in any row). `evidence_rows: 0`.

## 36. behavioral_pilot.rmb_80700 — ABSENT

Same frozen pilot, `80700` in NO symbol. Same authority-all-false verification. `evidence_rows: 0`.

---

## A33 required-source-class summary

Coordinator ruling: each class needs ≥1 OWNER_NATIVE cell across the company's counters, else GAPS names the class, the blocking descriptors, and the would-be owner. Honest result after the repair pass: **ZERO OWNER_NATIVE cells in this pack, and ALL SIX required classes are gaps** (see coverage JSON `a33_required_source_classes` and the GAPS section below). Nothing was upgraded to satisfy A33.

| Class | Gap? | Best cell | Best status | Blocking descriptors (canonical) | Would-be owner |
|---|---|---|---|---|---|
| identity_listing | **NO — GAP** | identity_listing.hkd_0700 | REFUSED | issuer_subject | Data OS issuer axis: scripts/build_security_master.py (apply_issuer_correction) under a new issuer-evidence era declared in config/identity_seams.yml, read via lib/dataos/identity.py |
| filings_announcements | **NO — GAP** | filings_announcements.hkd_0700 | PARTIAL | issuer_subject, reporting_period, definition_version, correction_refusal_state | collectors/hk_hkexnews.py + engine/hk_filing_bus.py once the category taxonomy and period fields are carried with version ids |
| financials | **NO — GAP** | financials.hkd_0700 | PARTIAL | issuer_subject, known_at_evidence, unit_currency, accounting_basis, source_span, definition_version, correction_refusal_state | Data OS issuer axis: scripts/build_security_master.py (apply_issuer_correction) under a new issuer-evidence era declared in config/identity_seams.yml, read via lib/dataos/identity.py; then a per-row known-at/accounting-basis/source-span-carrying financials owner |
| company_events_earnings_calendar | **NO — GAP** | company_events_earnings_calendar.hkd_0700 | PARTIAL | issuer_subject, reporting_period, definition_version, correction_refusal_state | an HK forward earnings-date owner (none exists; data/earnings is US Nasdaq only) |
| corporate_actions_adjustment | **NO — GAP** | corporate_actions_adjustment.hkd_0700 | ABSENT | all nine canonical descriptors (no owner row returned at all) | an explicit HK corporate-action ledger owner (engine/capital_structure is SEC-only; share count carried by no owner) |
| market_data_daily | **NO — GAP** | market_data_daily.hkd_0700 | PARTIAL | known_at_evidence, unit_currency, definition_version, correction_refusal_state | collectors/hk_stock_prices.py carrying per-row observation stamps, in-row currency and a pinned adjustment vintage |

## GAPS

Every NO_OWNER and ABSENT metric id (19), one per line, with its would-be owner (profile `would_be_owner` where present; otherwise the owner this pack names, suffixed "(pack-named)"):

- adr_h_basis.hkd_0700 (ABSENT) — would-be owner: Data OS security master (OTC ADR admission) then engine/hk_adr_bridge.py
- adr_h_basis.rmb_80700 (NO_OWNER) — would-be owner: engine/hk_adr_bridge.py after counter prices exist
- behavioral_pilot.hkd_0700 (ABSENT) — would-be owner: engine/stock_identity/pilot.py (no refresh scheduled)
- behavioral_pilot.rmb_80700 (ABSENT) — would-be owner: engine/stock_identity/pilot.py (no refresh scheduled)
- corporate_actions_adjustment.hkd_0700 (ABSENT) — would-be owner: an explicit HK corporate-action ledger owner (engine/capital_structure is SEC-only; share count carried by no owner) (pack-named)
- evaluation_qledger.hkd_0700 (ABSENT) — would-be owner: engine/qledger.py via the V0 contract lane
- evaluation_qledger.rmb_80700 (ABSENT) — would-be owner: engine/qledger.py via the V0 contract lane
- financials.rmb_80700 (NO_OWNER) — would-be owner: Data OS issuer axis: scripts/build_security_master.py (apply_issuer_correction) under a new issuer-evidence era declared in config/identity_seams.yml, read via lib/dataos/identity.py
- identity_listing.rmb_80700 (NO_OWNER) — would-be owner: Data OS CN/HK admission: scripts/build_security_master.py under research/prophet_v4/d2/D2B2_CN_HK_FROZEN_CONTRACT_2026-08-20.md, with a counter seam (one economic security, two trading counters) declared in config/identity_seams.yml
- market_data_daily.rmb_80700 (NO_OWNER) — would-be owner: collectors/hk_stock_prices.py (universe via collectors/hk_universe.py) after a Data OS counter security_id exists
- market_data_intraday.hkd_0700 (NO_OWNER) — would-be owner: Chairman procurement decision, then a new HK intraday collector
- market_data_intraday.rmb_80700 (NO_OWNER) — would-be owner: Chairman procurement decision, then a new HK intraday collector
- news.rmb_80700 (NO_OWNER) — would-be owner: Data OS CN/HK admission: scripts/build_security_master.py under research/prophet_v4/d2/D2B2_CN_HK_FROZEN_CONTRACT_2026-08-20.md, with a counter seam (one economic security, two trading counters) declared in config/identity_seams.yml
- options.hkd_0700 (NO_OWNER) — would-be owner: Chairman procurement decision, then an HK options owner
- options.rmb_80700 (NO_OWNER) — would-be owner: Chairman procurement decision, then an HK options owner
- research_vault.rmb_80700 (NO_OWNER) — would-be owner: Data OS CN/HK admission: scripts/build_security_master.py under research/prophet_v4/d2/D2B2_CN_HK_FROZEN_CONTRACT_2026-08-20.md, with a counter seam (one economic security, two trading counters) declared in config/identity_seams.yml
- southbound_holdings.rmb_80700 (NO_OWNER) — would-be owner: collectors/hk_southbound_holdings.py after a Data OS counter security_id exists
- themes.rmb_80700 (NO_OWNER) — would-be owner: Data OS CN/HK admission: scripts/build_security_master.py under research/prophet_v4/d2/D2B2_CN_HK_FROZEN_CONTRACT_2026-08-20.md, with a counter seam (one economic security, two trading counters) declared in config/identity_seams.yml
- corporate_actions_adjustment.rmb_80700 (NO_OWNER) — would-be owner: collectors/hk_stock_prices.py + a Data OS counter security_id

The six A33 class gaps (best cell / best status / blocking descriptors / would-be owner) are the table above.

Forward-schedule absence (top-level note): no owner in this repo carries a forward HK earnings-schedule date for Tencent — `data/earnings/earnings.parquet` is US Nasdaq only (exact scan → 0 rows for 0700/TCEHY/Tencent) and no other forward-calendar owner exists; this absence is recorded here and in the coverage JSON `notes` list, not as a descriptor of company_events_earnings_calendar.hkd_0700.

TCEHY disclosure (qledger): `data/qledger/claims.jsonl` carries 20 claims under `scope.key=='TCEHY'` (`claim_family`: us_importance_v0 10, us_importance_v0_pit 10; re-run 2026-10-11) while TCEHY has 0 rows in `data/reference/security_master.parquet` and 0 rows in `data/reference/vendor_aliases.parquet`. TCEHY is an unadmitted OTC ADR line with no Data OS identity; no identity link to 0700/Tencent exists or was created. Would-be owner: Data OS OTC ADR admission (scripts/build_security_master.py) then engine/qledger.py via the V0 contract lane.

## REVIEW DISPOSITIONS

Independent review lane (verdict REQUEST_CHANGES) — dispositions applied to this pack:

- **F2 (BLOCKER, id-shaped string for the RMB counter): FIXED.** Every constructed id occurrence deleted from all three owned files (pack §2 and the identity block above, the coverage JSON `identity_listing.rmb_80700.owner_call`, and no such string was present in the adversarial file). Replaced with whole-frame substring scans over security_master (0 matching rows) and vendor_aliases (0 matching rows), re-run 2026-10-11; the checker's `rmb_id_literal_hits` prints `[]`.
- **F3 (sessions_calendar.* were OWNER_NATIVE on call-time known-at + blob-pin version): FIXED.** Both cells PARTIAL `[known_at_evidence, definition_version]` with notes `HOLIDAY_RULES_IN_CODE_NO_PUBLICATION_KNOWN_AT` / `NO_VERSION_CONSTANT_IN_OWNER_MODULE` (§15/§16); `grep -n -i version lib/hk_calendar.py` re-run returns no line.
- **F5 (themes.hkd_0700 was OWNER_NATIVE with owner-recorded issuer_id NaN): FIXED.** PARTIAL `[issuer_subject]` (§31).
- **F8 (identity_listing.hkd_0700 descriptors wrong both ways): FIXED.** Descriptor reading ADOPTED: definition_version owner-recorded (config/identity_seams.yml `version: 1` + receipt code_version), issuer_subject missing → `["issuer_subject"]`; the reviewer's proposed PARTIAL status was RULED against — status stays REFUSED (the owner-recorded NO_ISSUER_EVIDENCE is the owner's refusal of this metric's issuer-security link); ruling sentence recorded under §1.
- **F9 (A33 section deferred gaps to the return packet): FIXED.** GAPS now lives in this pack; the return-packet reference deleted.
- **F10 (analyst-forecast values printed): FIXED.** Every forecast value removed from all three files; the pack records only that the owner payload carries a forecast block with key names `n_analysts, target_med, target_low, target_high, buy, hold, sell` (§5); checker `forecast_value_hits` prints `[]`.
- **F11 (rounding violated the verbatim rule): FIXED.** First 0700.HK row volume printed as `2385268337.0`, CNH_F last closes as `6.672999858856201` / `6.663000106811523`; full sweep applied (§9 last-3-session OHLCV, §17 southbound sample, §23 HKD_X closes, §29 avg_tone `0.0`, probe-1 denominators exact reprs); every replacement made from a re-run on 2026-10-11 and listed in the adversarial file's evidence notes. Probe-derived numbers (probe 1 denominators) are printed exactly as the probe code computes them and labelled "probe-derived, not an owner value, never carried as a capital-structure value".
- **F12 (string-form shorts predicates on an int64 column): FIXED.** Int form used everywhere and re-run: `sp[sp['stock_code']==80700]` → 172 rows 2023-06-23..2026-10-02; `sp[sp['stock_code']==700]` → 735 rows (§19/§20, adversarial probe 5).
- **F16 (a cited script path contained the platform claim word): FIXED.** The A20 note now cites "the platform claim-word CI check" without the file name; that word appears in no owned file.

## A20 note

Retrieved document text read in this pack (fundamentals `profile.description` zh prose, research-vault `summary_points` broker-research metadata, HKEXnews headline strings, forex snapshot headline strings) was treated as data only. No span contained instructions to any agent; no finding recorded. No claim in this pack is put forward under the platform claim-word CI check; nothing here promotes a display fact to authority.
