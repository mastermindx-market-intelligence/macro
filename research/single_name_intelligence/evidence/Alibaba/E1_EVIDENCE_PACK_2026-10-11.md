# E1 — Alibaba owner-native evidence pack (2026-10-11)

Task: E1 (SNI reference product, company Alibaba). Profile key:
`43251ca845b2:config/single_name_intelligence/coverage_profiles/alibaba.yml` (E0 branch
`origin/claude/sni-e0-m0-qualification-20261011`, read verbatim, not edited).
Repo read: origin/main `b79cd12239e5` (worktree `claude/sni-e1-alibaba-evidence-20261011`,
created from fresh origin/main 2026-10-11 ~17:40Z). As-of: 2026-10-11.
Authority: all authority flags false (rank/gate/size/signal/escalation/trade) — this pack is
qualification evidence only. No value below is a signal, score, rank, gate, size, forecast or
trade field.

Method law: every number below was produced in this run by an owner read or owner function
against committed owner data (blob shas cited); nothing is hand-typed, estimated, converted or
rounded. Owner calls are READ-ONLY; no file under `data/`, `engine/`, `lib/`, `scripts/`,
`config/` was modified. The E0 profile's binding facts are honored: no identity id is minted
(89988 stays unresolved), the HKD-counter/CNY-reporting currency defect is carried, never
relabelled, and no HK counter is attached to `ISS:US-XNYS-BABA`.

## Descriptor standard (the nine)

A row is OWNER_NATIVE only if all nine descriptors are recorded by the owner itself — in the
returned rows, the artifact's committed metadata/receipt, or the committed owner code contract
the call exercises (cited). Two descriptors are structurally type-level for non-monetary,
non-accounting metrics: `unit/currency` and `accounting_basis` are recorded "n/a (type)" only
when the owner's committed schema shows no such field exists (verified against the column list);
they are MISSING (→ PARTIAL) wherever a monetary value's currency is merely implied. A
descriptor this pack infers (publication lag, currency, schedule) is never owner-native.
Descriptors: (1) issuer subject, (2) reporting period, (3) known-at evidence, (4) unit/currency,
(5) dimensions, (6) accounting basis, (7) source span, (8) definition version,
(9) correction/refusal state. Metric ID is the row key, not a descriptor.

## Owner calls used (re-runnable from the worktree root with /usr/bin/python3)

- **C1** `pd.read_parquet('data/reference/security_master.parquet')` → row
  `security_id=='SEC:HK-XHKG-09988'`; and the negative query
  `d[d.listing_key.astype(str).str.contains('89988')]` → 0 rows.
- **C2** C1 plus `pd.read_parquet('data/reference/issuer_master.parquet')` → row
  `issuer_id=='ISS:US-XNYS-BABA'`; `pd.read_parquet('data/reference/vendor_aliases.parquet')`
  → 5 Alibaba alias rows; `json.load(open('data/reference/_receipt.json'))`.
- **C3** `from engine.theme_graph import identity_resolution as ir;
  ir.read_identity_resolution(latest=False)` → history rows per node: `co:us:BABA` = 61,
  `co:hk:9988.HK` = 61 (re-run 2026-10-11; the default `latest=True` call returns ONE row per
  node — 2,807 rows store-wide — and is never cited for a history count);
  `ir.resolve_graph_node_identity('co:hk:9988.HK')`; `ir.resolve_graph_node_identity('co:us:BABA')`.
- **C4** `from engine import hk_filing_bus as fb; fil = fb._load_filings()` (3,906 rows);
  `fb.classify_row(row.category, row.title)`; `fb.build_tape(fil, fb._load_placements(), window_days=3650)`.
- **C5** `fu = pd.read_parquet('data/hk_fundamentals/fundamentals.parquet');
  json.loads(fu[fu.ticker=='9988.HK'].iloc[-1]['payload'])`.
- **C6** `pd.read_parquet('data/earnings/earnings.parquet').loc['BABA']`.
- **C7** `pd.read_parquet('data/hk_stocks/9988.HK.parquet')`;
  `pd.read_parquet('data/yahoo/BABA.parquet')`; `ls data/massive_stock_day | grep -ci baba` → 0
  (re-run 2026-10-11); `git rev-parse HEAD:data/massive_stock_day/_manifest.json` →
  17e8338575a12e1ab80f988093a00cf08d8faf4a (re-run 2026-10-11).
- **C8** `sb = pd.read_parquet('data/hk_southbound/holdings.parquet')` (MultiIndex date×ticker);
  `sb[sb.index.get_level_values(1)=='9988.HK']` (290 rows); level `89988.HK` → 0 rows.
- **C9** `sp = pd.read_parquet('data/hk_shorts/positions.parquet')`; filter `stock_code==9988`
  (357 rows) and `stock_code==89988` (172 rows).
- **C10** `pd.read_parquet('data/hk_placements/events.parquet')` filter `9988|89988` → 0 of 811
  (re-run 2026-10-11: columns news_id/stock_code/ticker/category/announced_at/date/title/subcats;
  `date` 2026-03-05..2026-10-11, `announced_at` 2026-03-05 06:05:00..2026-10-11 18:25:00).
- **C11** `pd.read_parquet('data/intraday_flow/ledger.parquet')`; ticker 'BABA' → 0 of 7,424.
- **C12** `pd.read_parquet('data/finra/short_interest_history.parquet')` and
  `data/finra_short_volume/panel.parquet`; ticker 'BABA' → 0 and 0.
- **C13** `data/capital_structure/discovery.parquet` (24,262 rows) and
  `data/capital_structure/event_versions.parquet` (14,007 rows), filter `1577552|BABA` → 0 and 0;
  `data/fundamental_forensics/public_summary.json` (schema
  `fundamental_forensics.public_summary/v1`, generated 2026-10-06T11:07:22+00:00, 1,492
  companies, 1,058 findings, no Alibaba key); `ls data/fundamental_forensics/companyfacts` → absent.
- **C14** `json.load(open('data/research_vault/catalog.json'))` (schema
  `research_vault.catalog.v1` per `engine/research_vault/catalog.py` SCHEMA; generated field in
  file): 2,820 items; case-insensitive 'alibaba' name-pattern census → 24 items (pattern-census
  bound, not a subject-resolved link).
- **C15** `json.loads` per line of `data/qledger/claims.jsonl` (118,022 claims):
  `scope.key=='BABA'` → **159** (families us_importance_v0 78, us_importance_v0_pit 78, altdata 1,
  altdata_event 1, altdata_mid 1); scope containing '9988'/'89988' → 0 and 0. A raw substring scan
  for `"BABA"` hits 163 lines — the 4 extra lines are OTHER entities' claims that merely mention
  BABA (claim ids 969905d24586619b scope BRO altdata_event; 4d48b1a649685a97 TTD altdata_event;
  27c2a75f33a764fe LYB altdata_mid; 1a3f48a5e52b4f35 KVUE altdata_mid). The `scope.key` count
  (159) is the evidence_rows value used everywhere. Claim text/falsifier prose NOT copied
  (metadata only).
- **C16** `pd.read_parquet('data/hk/HKD_X.parquet')` (6,419 rows);
  `json.load(open('data/forex/latest.json'))['pairs']['USDCNH']` (asof 2026-10-09);
  `pd.read_parquet('data/china/CNH_F.parquet')` (3,368 rows);
  `pd.read_parquet('data/fred/DEXCHUS.parquet')` (11,421 rows).
- **C17** `pd.read_parquet('data/options_skew/snapshots.parquet')` filter `underlying=='BABA'`
  → 44; `json.load(open('data/options_skew/validation_gate.json'))`.
- **C18** `lib.hk_calendar.is_session(date(2026,10,9))` → True; `is_session(date(2026,10,1))`
  → False; `sessions_between(date(2026,9,1), date(2026,10,9))` → 27; `lib.nyse_calendar`:
  `is_session(date(2026,10,9))` → True; `is_session(date(2026,10,10))` → False;
  `len(sessions_between(date(2026,9,1), date(2026,10,9)))` → 28.
- **C19** `from engine import hk_adr_bridge as ab; ab.snapshot(hk_session_date=date(2026,10,9))`
  (read-only compute; `display_only: true`, note "context, not a signal").
- **C20** `pd.read_parquet('data/hk_gdelt/alibaba.parquet')` (77 rows, index `date` UTC).
- **C21** `pd.read_parquet('data/stock_identity/fingerprints/pilot_fingerprint_v0.parquet')`
  (21 US symbols); `json.load(open('data/stock_identity/ohlcv/manifest.json'))`;
  `pd.read_parquet('data/stock_identity/ohlcv/BABA.parquet')` (2,992 rows);
  `data/stock_identity/episodes/pilot/BABA.json`.

Blob shas cited below are `git rev-parse HEAD:<path>` at `b79cd12239e5` (short form).

Status totals (machine-readable twin: `E1_COVERAGE_REPORT_2026-10-11.json`):
**2 OWNER_NATIVE · 25 PARTIAL · 2 REFUSED · 12 ABSENT · 13 NO_OWNER (54 cells).**

---

## identity_listing — SECURITY/ISSUER IDENTITY & LISTING

Owner: `lib/dataos/identity.py` (ea8485596e57) reading `data/reference/security_master.parquet`
(85ef75104840), `issuer_master.parquet` (6643e7eae379), `vendor_aliases.parquet` (6406d5bffa3e),
receipt `_receipt.json` (f51ffbd63c62), registry `config/identity_seams.yml` (83a518a73b22).
Master columns (seams-declared): security_id, issuer_id, issuer_state, issuer_cik,
issuer_evidence_snapshot, listing_key, country, mic, inception_code, effective_at, ingested_at,
security_state, superseded_by.

| metric_id | status | issuer subject | period | known-at | unit/curr | dimensions | acct basis | source span | def version | correction/refusal |
|---|---|---|---|---|---|---|---|---|---|---|
| identity_listing.hkd_9988 | **REFUSED** (`OWNER_REFUSED_NO_ISSUER_EVIDENCE`; missing: issuer_subject) | MISSING — security row `SEC:HK-XHKG-09988` exists, but the owner itself records the issuer link `issuer_state=NO_ISSUER_EVIDENCE`, `issuer_id` NULL (SECURITY_ROW_EXISTS_ISSUER_LINK_NO_ISSUER_EVIDENCE) | `effective_at 2019-11-29` (row) | `ingested_at 2026-08-20T18:50:35` (row) + receipt `generated_at 2026-10-11T16:03:17` | n/a (type) — identity record; master schema has no currency column | country HK, mic XHKG, listing_key `HK-XHKG-09988`, inception_code 09988 | n/a (type) — reference record | security_master.parquet blob 85ef75104840, 1 row | seams `version: 1` + CN/HK admission contract `research/prophet_v4/d2/D2B2_CN_HK_FROZEN_CONTRACT_2026-08-20.md` + receipt `code_version bb0830d8…` | issuer axis REFUSAL recorded by owner: `issuer_state=NO_ISSUER_EVIDENCE` (link to ISS:US-XNYS-BABA would be a mint; forbidden) |
| identity_listing.rmb_89988 | **NO_OWNER** | — (no row exists; counter must stay unresolved) | — | — | — | — | — | security_master.parquet blob 85ef75104840, query C1 → 0 rows | — | would-be owner: Data OS CN/HK admission — `scripts/build_security_master.py` under a counter seam in `config/identity_seams.yml` (per profile would_be_owner). NO id constructed here |
| identity_listing.adr_baba | **OWNER_NATIVE** | `SEC:US-XNYS-BABA` → issuer `ISS:US-XNYS-BABA` RESOLVED, `issuer_cik 0001577552`, legal_name "Alibaba Group Holding Ltd" | `effective_at 2026-08-21` (security row); issuer era snapshot 2026-08-18 | `ingested_at 2026-08-21T10:17:27` (row) + receipt `generated_at 2026-10-11T16:03:17` | n/a (type) — identity record | country US, mic XNYS; vendor aliases membership/store/yahoo/yahoo_fetch × BABA; issuer `n_securities 1`, `status active` | n/a (type) | security_master 85ef75104840 + issuer_master 6643e7eae379 + vendor_aliases 6406d5bffa3e | issuer era `issuer_semantic_correction_v1` (issuer_master `era` field; seams yml:71,316) + seams `version: 1` | correction ledger queried: `issuer_migrations.parquet` (ddef55b56231, 3 rows) and `security_migrations.parquet` (b2aae9179179, 1 row) → 0 Alibaba rows (no pending correction); the issuer id itself exists via the recorded semantic-correction era, `evidence_source sec_company_tickers` |

Coordinator ruling (review F6 disposition): identity_listing.hkd_9988 stays **REFUSED** — the
commission requires the E0 fact "HK counters are NO_ISSUER_EVIDENCE" to appear as a REFUSED /
NO_OWNER row, and the owner-recorded `NO_ISSUER_EVIDENCE` is the owner's refusal of exactly this
metric's issuer–security link; the reviewer's descriptor reading (only `issuer_subject` missing)
is adopted.

Sample rows (exact, from C1/C2): SEC:HK-XHKG-09988 / issuer NULL / NO_ISSUER_EVIDENCE /
HK / XHKG / 09988 / effective 2019-11-29 / ingested 2026-08-20 18:50:35. SEC:US-XNYS-BABA /
ISS:US-XNYS-BABA / RESOLVED / 0001577552 / snapshot 2026-08-18 / US / XNYS / BABA / effective
2026-08-21 / ingested 2026-08-21 10:17:27. security_master query `89988` → 0 rows.

## filings_announcements — HK/SEC FILINGS & ANNOUNCEMENTS

| metric_id | status | issuer subject | period | known-at | unit/curr | dimensions | acct basis | source span | def version | correction/refusal |
|---|---|---|---|---|---|---|---|---|---|---|
| filings_announcements.hkd_9988 | **PARTIAL** (missing: issuer_subject, reporting_period, definition_version, correction_refusal_state) | MISSING — rows keyed by raw `ticker 9988.HK` / `stock_code "09988<br/>89988"` (as recorded); the owner records issuer evidence NO_ISSUER_EVIDENCE for 09988 and no security_id exists for 89988 (RAW_STOCK_CODE_KEY_NO_ISSUER_EVIDENCE) | MISSING — owner carries announcement `date` (e.g. 2026-08-24) only; no reporting-period field | `announced_at` = HKEX release timestamp (e.g. 2026-08-24 06:04:00) — first-public, owner field | n/a (type) — headline metadata | news_id, category, subcats, title; classified category + dilution_flag/buyback_flag from `classify_row` | n/a (type) | data/hk_filings/events.parquet blob be30a5bc5ecb (3,906 rows, 2026-04-13..2026-10-11) + coverage.json 98aedf7d9b2f (`fetched_at 2026-10-11T14:17:08Z`) | MISSING — category taxonomy in committed owner code `engine/hk_filing_bus.py` (e3aced460bb8) `classify_row` carries no version constant | MISSING — the store has no correction/retraction field; the store-window note (starts 2026-04-13, no earlier history) is coverage text, NOT a correction state; headlines only, no full text; rights UNVERIFIED (per profile). All four rows carry `dilution_flag=True` where applicable (placing rows) |
| filings_announcements.rmb_89988 | **PARTIAL** (missing: issuer_subject, reporting_period, definition_version, correction_refusal_state) | MISSING — subject appears only as the counter string inside `stock_code "09988<br/>89988"` (both counters in one announcement); no security_id exists for 89988 (ROW_STOCK_CODE_LISTS_89988_NO_SECURITY_ID); the `ticker` column folds to `9988.HK` only — see adversarial probe P6 | MISSING — same 4 rows: 2026-05-13, 2026-08-23, 2026-08-24, 2026-08-26; no reporting-period field | `announced_at` (same field) | n/a (type) | news_id/category/subcats as above | n/a (type) | same blob be30a5bc5ecb, the 4 rows whose stock_code names 89988 | MISSING — same versionless classifier code | MISSING — same: no correction/retraction field. The raw counter code is carried as the owner itself records it, NOT a minted id; join to the identity axis remains impossible (would-be owner: CN/HK admission, per profile) |
| filings_announcements.adr_baba | **ABSENT** | — | — | — | — | — | — | discovery.parquet 688e781e91b0 + event_versions.parquet 52446066643d + public_summary.json 36bd01cec2eb, query C13 → 0 | — | exact queries recorded (C13): CIK 1577552 / ticker BABA → 0 rows in both stores; FIF public_summary/v1 (1,492 companies) has no Alibaba key; `data/fundamental_forensics/companyfacts/` absent. Would-be owner: `engine/fundamental_forensics/broad_sec_store.py` (c38ee45ad68a) universe with 20-F filer admission. DEC:FINANCE-SEC-EVIDENCE-RIGHTS-HELD-UNTIL-FAMILY-ADMITTED noted |

Sample rows (exact, from C4 — the 4 events for this issuer in the store):
`12157537 / 09988<br/>89988 / final_results / 2026-05-13 17:30:00 / "ANNOUNCEMENT OF THE MARCH QUARTER 2026 RESULTS AND FISCAL YEAR 2026 ANNUAL RESULTS"`;
`12295308 / general_mandate / 2026-08-23 18:06:00 / proposed placing of new shares`;
`12295380 / general_mandate / 2026-08-24 06:04:00 / "PRICING OF HK$80 BILLION PLACING OF NEW SHARES UNDER GENERAL MANDATE"`;
`12300619 / general_mandate / 2026-08-26 19:23:00 / completion of placing`.
Store census: 3,906 events; by_category interim_results 2,178 / final_results 792 /
general_mandate 777 / shareholder 132 / buyback 27.

## financials — ANNUAL FINANCIAL LINES

| metric_id | status | issuer subject | period | known-at | unit/curr | dimensions | acct basis | source span | def version | correction/refusal |
|---|---|---|---|---|---|---|---|---|---|---|
| financials.hkd_9988 | **PARTIAL** (missing: issuer_subject, known_at_evidence, unit_currency, accounting_basis, source_span, definition_version, correction_refusal_state) | MISSING — payload keyed by raw ticker `9988.HK`; owner-recorded issuer link NO_ISSUER_EVIDENCE (RAW_TICKER_KEY_NO_ISSUER_EVIDENCE); payload `profile.name_full` 阿里巴巴集团控股有限公司 stays as recorded | `fy` 2020..2026 (fiscal-year label; fy-end convention undeclared by owner — profile: "fiscal year ends March; fy label convention undeclared") | **MISSING** — no first-public/publication field; only collector snapshot column `asof = 2026-06-18` (observation, not publication) | **MISSING** — `currency "HKD"` recorded per line but **defective**: collector header `collectors/hk_fundamentals.py:19-21` (3895bcd52d21) states many HK names report in CNY while price/target are HKD; descriptor missing with note CURRENCY_DEFECT_HKD_LABEL_ON_RMB_REPORTED_FINANCIALS; defect carried, never relabelled (probe P5) | line keys revenue, ni, gross_profit, eps, eps_diluted, bvps + ratio fields; profile block (industry, employees 126,661); separate forecast block (n_analysts/target levels/buy-hold-sell) — **forecast values NOT carried here (out of scope)** | **MISSING** — no GAAP/IFRS/non-GAAP marker anywhere in payload | **MISSING** — vendor payload carries no filing span (VENDOR_PAYLOAD_NO_FILING_SPAN); artifact citation: data/hk_fundamentals/fundamentals.parquet blob b4d4806e1ed9, 1 payload row (7 financial lines) | **MISSING** — no schema/version field in payload | **MISSING** — correction state records the currency defect: vendor label `HKD` on reported financials the collector itself notes are reported in CNY; values stay verbatim, never relabelled or converted; ratios deliberately not computed by collector for PE/PB for this reason; third-party consensus forecast block present = display/qualification fact only |
| financials.rmb_89988 | **NO_OWNER** | — | — | — | — | — | — | same blob b4d4806e1ed9; snapshot exists only under ticker `9988.HK` | — | issuer-level family reachable from this counter only through an issuer link that does not exist; would-be owner: Data OS issuer axis (`scripts/build_security_master.py` apply_issuer_correction under a new issuer-evidence era), per profile |
| financials.adr_baba | **ABSENT** | — | — | — | — | — | — | query C13 → 0 metric rows in every FIF / capital_structure artifact | — | would-be owner: `engine/fundamental_forensics/sec_companyfacts.py` with 20-F filer admission. A11 note: any share-count/valuation denominator for Alibaba is REFUSED by this pack — no canonical capital-structure version exists (probe P1) |

Sample values (exact, from C5, fy2026 line — currency label as recorded): revenue
1023670000000.0; ni 103592000000.0; gross_profit 407534000000.0; eps 5.7; eps_diluted 5.5;
bvps 55.683165380648; currency "HKD" (defect). 7 lines total, fy 2020→2026. The 0700.HK row was
queried as a control and is ALSO labeled "HKD" — the defect is store-wide, not Alibaba-specific.

## company_events_earnings_calendar — EVENTS & EARNINGS CALENDAR

| metric_id | status | issuer subject | period | known-at | unit/curr | dimensions | acct basis | source span | def version | correction/refusal |
|---|---|---|---|---|---|---|---|---|---|---|
| company_events_earnings_calendar.hkd_9988 | **PARTIAL** (missing: issuer_subject, reporting_period, definition_version, correction_refusal_state) | MISSING — ticker `9988.HK`, stock_code `09988<br/>89988` raw codes; owner-recorded issuer link NO_ISSUER_EVIDENCE (RAW_STOCK_CODE_KEY_NO_ISSUER_EVIDENCE) | MISSING — owner carries the announcement date 2026-05-13 (FY2026 annual + March-quarter results, per the row's own title prose), no reporting-period field | `announced_at 2026-05-13 17:30:00` (HKEX release) | n/a (type) | news_id 12157537, category final_results (classifier: `results`), subcats "[Quarterly Results / Final Results / Dividend or Distribution]" | n/a (type) | events.parquet be30a5bc5ecb, 1 results-category row of 4 store events | MISSING — classifier code e3aced460bb8 carries no version constant | MISSING — no correction/retraction field. Realized events only — **no forward scheduled-date owner for HK names** (engine/hk_event_calendar.py / hk_catalyst_calendar.py are macro/index-level, per profile); response windows can only be anchored after the fact |
| company_events_earnings_calendar.rmb_89988 | **PARTIAL** (missing: issuer_subject, reporting_period, definition_version, correction_refusal_state) | MISSING — same single results announcement; owner records the counter in `stock_code "09988<br/>89988"`; no security_id exists for 89988 (ROW_STOCK_CODE_LISTS_89988_NO_SECURITY_ID) | MISSING — same announcement date, no reporting-period field | `announced_at 2026-05-13 17:30:00` | n/a (type) | same news_id/category | n/a (type) | same blob/row | MISSING — same versionless classifier | MISSING — same: no correction/retraction field; realized-only limit stands; ticker column folds to 9988.HK (probe P6); no counter id minted |
| company_events_earnings_calendar.adr_baba | **PARTIAL** (missing: definition_version) | index key `ticker == 'BABA'` | `next_date 2026-08-20` (+ `next_time "time-pre-market"`) | `as_of 2026-09-30T03:23:30Z` + `surprises_as_of 2026-08-13T02:58:10Z` (both owner fields) | n/a (type) — date field | next_date/next_time; eps_forecast and surprises fields exist in the row but their values are NOT carried here (forecast/consensus = out of scope) | n/a (type) | data/earnings/earnings.parquet blob 8f0575464ba0, 1 row (2,315 total) | **MISSING** — no schema/version field; collector contract `collectors/equity_earnings.py` (3cf263cdc561:16-19) documents ticker-indexed columns and that dates "are estimated and can move; community/Nasdaq-sourced, not official" | owner fields show the row is STALE: next_date 2026-08-20 already past at as_of 2026-09-30 (the next-report row was not rolled after the 2026-08-20 report) |

## market_data_daily — DAILY BARS

| metric_id | status | issuer subject | period | known-at | unit/curr | dimensions | acct basis | source span | def version | correction/refusal |
|---|---|---|---|---|---|---|---|---|---|---|
| market_data_daily.hkd_9988 | **PARTIAL** (missing: known_at_evidence, unit_currency, definition_version) | file-keyed subject `9988.HK` (collector writes one file per symbol; profile links it to `SEC:HK-XHKG-09988` via vendor alias `theme_graph_native 9988.HK`) | DatetimeIndex `Date`, session dates 2019-11-26..2026-10-09 (1,681 rows) | **MISSING** — no collection/publication timestamp column; owner clock = HK session date (profile) | **MISSING** — prices carry no currency column or constant; HKD is implied by the counter only | open/high/low/close/volume | price basis recorded in collector contract: `auto_adjust=True` total-return adjusted only, `overwrite_overlap=True` re-adjusts the refresh window (`collectors/hk_stock_prices.py:25`, 64d4708cf626); no raw series | data/hk_stocks/9988.HK.parquet blob 2792f4bc5685; closes_deep.parquet 0ed0dc4075e3 (wide store, `9988.HK` column) | **MISSING** | adjustment-vintage drift documented by owner-adjacent DSC:HK-DEEP-PANEL-SPLICES-ADJUSTMENT-VINTAGES (profile): a frozen return window can drift between collector runs; vintage must be pinned by consumers |
| market_data_daily.rmb_89988 | **NO_OWNER** | — | — | — | — | — | — | `ls data/hk_stocks` → no 89988 file; closes_deep has no 89988 column | — | would-be owner `collectors/hk_stock_prices.py` (universe via collectors/hk_universe.py) after a Data OS counter security_id exists; never substitute the HKD counter |
| market_data_daily.adr_baba | **PARTIAL** (missing: known_at_evidence, unit_currency, definition_version) | file-keyed subject `BABA` (collector per-symbol file) | DatetimeIndex `Date`, 2014-09-19..2026-10-09 (3,032 rows) | **MISSING** — no collection/publication timestamp column | **MISSING** — USD implied, not declared; price semantics ARE declared: dual basis per collector W1.3 (`collectors/yahoo.py:6-15`, c4a16844e604): `close` = split+dividend adjusted (total return), `close_price` = split-adjusted dividend-unadjusted | close, close_price, volume | dual price basis recorded in owner code (above); "both stored bases are re-adjusted by Yahoo at every fetch" (collector line 15) | data/yahoo/BABA.parquet blob 2c627eecb86b; massive_stock_day manifest 17e8338575a1 spans the US universe but `ls data/massive_stock_day | grep -ci baba` → 0 (no BABA file) | **MISSING** | data/stock_identity/ohlcv/BABA.parquet is the HISTORICAL August pilot copy, not an owner (profile family_notes) |

Sample rows (exact): 9988.HK 2026-10-09 open 104.5 / close 107.0 / high 107.30000305175781 /
low 104.30000305175781 / volume 72349748.0; 2026-10-08 close 104.30000305175781 / volume
66440072.0. BABA 2026-10-09 close_price 111.37000274658203 / close 111.37000274658203 / volume
12326200.0; 2026-10-08 close_price 105.69999694824219 / close 105.69999694824219 / volume
11580400.0; first row 2014-09-19 close_price 93.88999938964844 / close 88.35541534423828 /
volume 271879400.0.

## market_data_intraday — INTRADAY

| metric_id | status | note |
|---|---|---|
| market_data_intraday.hkd_9988 | **NO_OWNER** | no HK intraday owner (HKEX historical full book / OMD-C are paid); `data/intraday_flow/ledger.parquet` is US-only; rights BLOCKED-procurement per profile. Would-be owner: Chairman procurement decision, then a new HK intraday collector |
| market_data_intraday.rmb_89988 | **NO_OWNER** | same, plus no counter identity |
| market_data_intraday.adr_baba | **ABSENT** | owner `engine/intraday_flow.py` exists; C11 query → 0 BABA rows of 7,424 (sessions 2026-07-11..2026-10-09). Would-be owner: engine/intraday_flow.py universe |

## corporate_actions_adjustment — CORPORATE ACTIONS & ADJUSTMENT

| metric_id | status | evidence + refusal state |
|---|---|---|
| corporate_actions_adjustment.hkd_9988 | **ABSENT** | owners queried, no explicit action rows: `data/hk_placements/events.parquet` (d3d63e03a478, 811 rows; re-run 2026-10-11: `date`
2026-03-05..2026-10-11, `announced_at` 2026-03-05 06:05:00..2026-10-11 18:25:00) → 0 rows for this counter — the collector keys on the 'placing' headline category and missed the 9988 HK$80bn placing that HKEXnews filed under general_mandate (profile + verified here); no dividend/split rows in any HK store; adjustment factors not stored (implicit in `auto_adjust=True`). Would-be: an explicit HK corporate-action ledger |
| corporate_actions_adjustment.rmb_89988 | **NO_OWNER** | no corporate-action or adjustment ledger for the RMB counter (no prices to adjust); would-be `collectors/hk_stock_prices.py` + counter security_id |
| corporate_actions_adjustment.adr_baba | **PARTIAL** (missing: known_at_evidence, definition_version) | cumulative dividend factor derivable from two owner-recorded columns as `close/close_price` (derivation documented in collector W1.3); sample from C7: first row 88.35541534423828/93.88999938964844 = 0.941064…, last row 111.37000274658203/111.37000274658203 = 1.0; NO explicit corporate-action rows; `data/capital_structure` has 0 BABA rows (C13); ADS-ratio changes carried by no owner (profile). Factor rows are a derivation from owner columns, never an owner row — hence PARTIAL |

## sessions_calendar — SESSION/TRADING CALENDAR

| metric_id | status | evidence |
|---|---|---|
| sessions_calendar.hkd_9988 | **PARTIAL** (missing: known_at_evidence, definition_version) | `lib/hk_calendar.py` (5ffb5af43465) rule arithmetic + annual HKEX notices: is_session(2026-10-09)=True, is_session(2026-10-01)=False (holiday), sessions_between(2026-09-01, 2026-10-09)=27, holidays(2026) n=14. Period = queried date (call argument); clock "session date in HKT; 17:30 HKT regular expectation, 13:30 half-day" (owner docstring/profile). known_at_evidence MISSING (HOLIDAY_RULES_IN_CODE_NO_PUBLICATION_KNOWN_AT) — no per-rule first-known date is recorded. definition_version MISSING (NO_VERSION_CONSTANT_IN_OWNER_MODULE) — `grep -in version lib/nyse_calendar.py lib/hk_calendar.py` returns no line (re-run 2026-10-11): the calendars are versionless rule code; a git blob sha is not an owner-declared version |
| sessions_calendar.rmb_89988 | **PARTIAL** (missing: known_at_evidence, definition_version) | same session calendar serves both HK counters (profile note); same three probe results; same known_at_evidence and definition_version gaps with the same notes |
| sessions_calendar.adr_baba | **PARTIAL** (missing: known_at_evidence, definition_version) | `lib/nyse_calendar.py` (0ece6439ffe4): is_session(2026-10-09)=True, is_session(2026-10-10)=False, sessions_between(2026-09-01, 2026-10-9)=28, holidays(2026) n=10; clock America/New_York; BABA close precedes next HK open (temporal-law fact, profile). known_at_evidence and definition_version MISSING with the same notes as the HK calendar rows (no publication known-at; no version constant in the owner module) |

## southbound_holdings — SOUTHBOUND HOLDINGS

| metric_id | status | evidence |
|---|---|---|
| southbound_holdings.hkd_9988 | **PARTIAL** (missing: known_at_evidence, unit_currency, definition_version, correction_refusal_state) | 290 rows, index (date, ticker) 2024-09-19..2026-10-09; subject recorded as ticker `9988.HK` + name 阿里巴巴-W; period = holding date T (index); values exact from C8: 2024-09-19 hold_shares 199783605.0, hold_mktcap 17121454948.5, close 85.7; 2026-10-09 hold_shares 1986384146.0, hold_mktcap 212543103622.0, close 107.0; 2026-10-08 close 104.3. **own_pct on any date: A11-REFUSED as a denominator-bearing value — HKEX-reported issued-share denominator, no canonical capital-structure version** (definition_version MISSING, OWN_PCT_DENOMINATOR_UNVERSIONED; the latest-row own_pct is therefore not shown as a number; hold_shares stays a sample value). unit: hold_shares are column-declared; hold_mktcap/close carry no currency declaration → unit/currency missing. known_at_evidence MISSING (holding date is a position date; no publication field). correction/refusal MISSING as an owner descriptor — values are price-contaminated (profile note), source is a third-party Eastmoney mirror, rights UNVERIFIED; first-party CCASS BLOCKED-licence per 08-28 matrix |
| southbound_holdings.rmb_89988 | **NO_OWNER** | C8: index level `89988.HK` → 0 rows; the store keys (date, ticker) and cannot key the RMB counter at all; no artifact establishes RMB-counter Southbound eligibility (hk_connect_roster 3a2affa41b0c has 0 rows for 89988 — a missing change row is not an eligibility verdict). Would-be owner: collectors/hk_southbound_holdings.py after a counter security_id exists |
| southbound_holdings.adr_baba | **REFUSED** (`NOT_APPLICABLE_PER_PROFILE`) | profile cell `applicable: false` — a US ADS is not a Southbound security; typed absence, no value |

## short_positions — SHORT POSITIONS

| metric_id | status | evidence |
|---|---|---|
| short_positions.hkd_9988 | **PARTIAL** (missing: known_at_evidence, definition_version, correction_refusal_state) | 357 weekly rows 2019-11-29..2026-10-02; subject recorded: stock_code 9988, ticker 9988.HK, stock_name "BABA-W"; period = position date; units column-declared (shorted_shares shares; value_hkd HKD); source SFC aggregated reportable short positions (official, verified-internal rights). known_at_evidence MISSING: SFC publication lag is NOT carried as a field (profile + schema re-run 2026-10-11: columns date/stock_code/ticker/stock_name/shorted_shares/value_hkd only). definition_version MISSING — no schema/version field in the store. correction/refusal MISSING — no correction/retraction field. Samples (C9, exact): 2026-10-02 shorted_shares 186521267, value_hkd 19472820275; 2026-09-25 shorted_shares 206803687, value_hkd 22417519671 |
| short_positions.rmb_89988 | **PARTIAL** (missing: issuer_subject, known_at_evidence, unit_currency, definition_version, correction_refusal_state) | 172 weekly rows 2023-06-23..2026-10-02 keyed NATIVELY by the counter: stock_code 89988, ticker 89988.HK, stock_name "BABA-WR" (owner distinguishes the counters by name here). issuer_subject MISSING — rows are keyed by the raw code and the counter has no security id (NO_SECURITY_ID_FOR_89988; none minted). Samples: 2026-10-02 shorted_shares 111000, value_hkd 11428560. unit_currency MISSING — the value column's exact name is `value_hkd` (re-run 2026-10-11): the column name carries HKD, but the owner records no convention for what currency the RMB counter's value column reports beyond that name (VALUE_COLUMN_CURRENCY_CONVENTION_FOR_RMB_COUNTER_NOT_RECORDED); carried as recorded. known_at_evidence MISSING (publication lag not a field); definition_version MISSING — no schema/version field; correction/refusal MISSING — no correction/retraction field |
| short_positions.adr_baba | **ABSENT** | owners exist and were queried: FINRA short_interest_history (5,990-de4fa81f blob 5990de4fa81f, 9,129 rows) and finra_short_volume panel (cdc95d8bca55, 137,047 rows) → 0 BABA rows each; universe excludes BABA (profile). Would-be owner: collectors/finra.py universe |

## adr_h_basis — ADR/H BASIS (diagnostic only)

| metric_id | status | evidence |
|---|---|---|
| adr_h_basis.hkd_9988 | **ABSENT** | owner `engine/hk_adr_bridge.py` (a8b7acf7119f) was run (C19): `snapshot(hk_session_date=2026-10-09)` returns implied-open CONTEXT only — for 9988.HK: `adr_move_pct 5.36`, `hk_last_move_pct 2.59`, `implied_open_gap_pct 5.36`, `gap_context "strong_up"`, `disconnect_flag false`, freshness asof 2026-10-09 state fresh, `display_only true`, note "context, not a signal". The BASIS series itself is absent from owner output: no field carries an ADR/H ratio and no owner carries the ADS-to-ordinary ratio (profile). USD/HKD leg exists (fx family). The metric value (basis) → ABSENT with the adjacent owner output recorded |
| adr_h_basis.rmb_89988 | **NO_OWNER** | no RMB-counter prices and no spot-CNH owner (CNH=F is a futures proxy); would-be owner engine/hk_adr_bridge.py after counter prices exist |
| adr_h_basis.adr_baba | **ABSENT** | same bridge run; no basis value on the ADR side either; `display_only: true` is owner-recorded |

## fx — FX LEGS

| metric_id | status | evidence |
|---|---|---|
| fx.hkd_9988 | **PARTIAL** (missing: known_at_evidence, unit_currency, definition_version, correction_refusal_state) | `data/hk/HKD_X.parquet` (826468c71fd6): 6,419 rows 2001-07-16..2026-10-11, columns close/volume, DatetimeIndex Date; last close 7.84689998626709 (HKD per USD, collector semantics `HKD=X`); read by engine/hk_inputs.py as usdhkd. unit_currency MISSING — the pair (USD/HKD) is implied by the file name, not recorded in the row (columns close/volume, re-run 2026-10-11). Close-fixing convention undeclared (profile → carried); correction_refusal_state MISSING (no owner-recorded state); no publication timestamp |
| fx.rmb_89988 | **PARTIAL** (missing: known_at_evidence, unit_currency, definition_version, correction_refusal_state) | two owner sources, both carried as-is: (1) desk snapshot `data/forex/latest.json` (0e41dead4a2f): USDCNH quote 6.6685, chg -0.6, asof 2026-10-09, owner-recorded trust flags `reliable: false`, `shock_state: exogenous_bid`, `cnh_basis_bps -53.0`, schema_note "MSX-1 additive-only enrichment"; (2) `data/china/CNH_F.parquet` (fe01ca5a6dcb): 3,368 rows 2013-02-11..2026-10-09, columns close/volume, last close 6.663000106811523 — a FUTURES proxy, not spot (caveat carried from owner/profile text; correction_refusal_state itself MISSING as an owner descriptor); unit_currency MISSING — the pair is implied by the JSON key (`pairs.USDCNH`) / file name, not recorded in rows (PAIR_IMPLIED_BY_FILE_NAME_NOT_RECORDED_IN_ROW); onshore CNY (`data/fred/DEXCHUS.parquet` 5f5898b2b6d3, fx_cny_usd 6.7038 @ 2026-10-02) must NOT be substituted silently |
| fx.adr_baba | **PARTIAL** (missing: known_at_evidence, unit_currency, definition_version, correction_refusal_state) | counter is USD-native; the USD/HKD diagnostic leg is the same HKD_X store (above; unit_currency MISSING with the same pair-implied-by-file-name note); FX matters only for basis work and that leg's rights are UNVERIFIED (profile); correction_refusal_state MISSING (no owner-recorded state) |

## options — OPTIONS

| metric_id | status | evidence |
|---|---|---|
| options.hkd_9988 | **NO_OWNER** | no stock-options owner for 9988.HK (HKEX SOM full book / trade file are paid first-party products); rights BLOCKED-procurement; would-be: Chairman procurement decision, then an HK options owner |
| options.rmb_89988 | **NO_OWNER** | same; no artifact establishes whether any option class references the RMB counter |
| options.adr_baba | **PARTIAL** (missing: known_at_evidence) | 44 BABA skew snapshots 2026-06-22..2026-08-21 in `data/options_skew/snapshots.parquet` (75fb9a223cd6); columns date/underlying/asof/spot/tenor_days/otm_put_iv/atm_call_iv/skew/n_strikes/source; sample exact (C17): 2026-08-21 spot 119.34, otm_put_iv 0.3872, atm_call_iv 0.4114, skew -0.0242, n_strikes 108, source thetadata. asof = date (snapshot-as-of only, no publication time) → known-at missing. Correction state: `validation_gate.json` (2c8d22130093, schema options_skew.gate.v1) records `scored: false`, `status insufficient_history (have 44/120 dates)`, `weight 0.0` — display-only context by the owner's own gate; snapshots stopped 2026-08-21 (~7 weeks before as-of) |

## research_vault — RESEARCH VAULT CATALOG

| metric_id | status | evidence |
|---|---|---|
| research_vault.hkd_9988 | **PARTIAL** (missing: issuer_subject, definition_version) | catalog `data/research_vault/catalog.json` (f18851fb4cfc), 2,820 items, owner schema constant `research_vault.catalog.v1` (`engine/research_vault/catalog.py` SCHEMA, 828f812d6907); case-insensitive 'alibaba' name-pattern census (C14) → 24 items (E0's own census bound with a different pattern was 41/2,778 — the store has since grown; both are census bounds, not subject links). published_at is owner-recorded per item (e.g. "Alibaba Group (BABA) Alibaba Cloud APSARA Key Takeaways", 2026-09-22T13:39:08Z). issuer_subject MISSING: items match by name text; binding to an issuer id is not established by any owner. Item summaries are third-party prose → treated as untrusted data (A20), only ids/dates/titles cited |
| research_vault.rmb_89988 | **NO_OWNER** | issuer-level items only; no counter join key exists |
| research_vault.adr_baba | **PARTIAL** (missing: issuer_subject, definition_version) | same catalog scan (C14); same 24-item name-pattern bound; same missing subject binding |

## news — NEWS/ATTENTION AGGREGATES

| metric_id | status | evidence |
|---|---|---|
| news.hkd_9988 | **PARTIAL** (missing: issuer_subject, known_at_evidence, unit_currency, definition_version, correction_refusal_state) | `data/hk_gdelt/alibaba.parquet` (2bc738a16655): 77 daily rows 2026-07-12..2026-10-06, index `date` (UTC aggregation day — the only time field, so known_at_evidence beyond the aggregation day is missing); issuer_subject MISSING — subject is entity_query "Alibaba" + ticker 9988.HK, a name query not an issuer id (NAME_QUERY_NOT_ISSUER_ID); unit_currency MISSING — TONE_AND_VOLUME_MEASURES_UNDECLARED (vol_intensity/avg_tone carry no unit definition); definition_version MISSING — no schema/version in the store; correction/refusal MISSING — no correction field. Sample exact (C20): 2026-07-12 vol_intensity 0.0225, avg_tone NaN; 2026-10-06 vol_intensity 0.0253, avg_tone NaN (NaN carried as recorded, never zero-filled — A10). GDELT volume/tone aggregates only, no article text |
| news.rmb_89988 | **NO_OWNER** | topic keyed 9988.HK only; no counter key |
| news.adr_baba | **ABSENT** | no BABA-keyed news owner in the searched bounds: the GDELT store's rows are keyed 9988.HK; BABA is reachable only through the issuer, whose HK link is UNRESOLVED (profile); exact query C20 → 0 BABA-keyed rows |

## themes — THEME GRAPH IDENTITY/MEMBERSHIP

| metric_id | status | evidence |
|---|---|---|
| themes.hkd_9988 | **PARTIAL** (missing: issuer_subject) | `resolve_graph_node_identity('co:hk:9988.HK')` (C3) returns a fully-descriptorized row: schema `gmi.identity_resolution/v1`, node co:hk:9988.HK, market_scope hk, source_native_symbol 9988.HK, resolution_asof 2026-10-09, RESOLVED → security_id `SEC:HK-XHKG-09988`, issuer_id NULL, join_method vendor_alias, master_generated_at 2026-10-09T05:05:32, master_code_version cdbcd143dcfa…, computed_at 2026-10-09T14:11:26Z, engine_version theme_graph.v1, refusal_reason empty, source_receipts `{"matched_vendors": ["theme_graph_native"]}`. History: 61 rows for this node via `read_identity_resolution(latest=False)` (re-run 2026-10-11). issuer_subject MISSING — GRAPH_NODE_RESOLVES_TO_SECURITY_ONLY_NO_ISSUER_EVIDENCE: the graph node resolves to the SECURITY id only, `issuer_id` NULL with no issuer evidence (the remaining eight descriptors are owner-recorded) |
| themes.rmb_89988 | **NO_OWNER** | no company node for the RMB counter in `data/theme_graph/nodes.parquet`; CN/HK Data OS admission is node-driven, so a missing node is also why the counter has no security_id (profile). Would-be owner: CN/HK admission path |
| themes.adr_baba | **OWNER_NATIVE** | `resolve_graph_node_identity('co:us:BABA')`: RESOLVED → security_id `SEC:US-XNYS-BABA`, issuer_id `ISS:US-XNYS-BABA`, join_method `master_inception_exact`, same asof/computed_at/engine_version fields; history 61 rows for co:us:BABA via `read_identity_resolution(latest=False)` (re-run 2026-10-11). Theme membership is display/context only; evidence-row rights governed by `engine/theme_graph/rights.py`, not adjudicated here |

## evaluation_qledger — CLAIM/GRADE LEDGER (census only)

| metric_id | status | evidence |
|---|---|---|
| evaluation_qledger.hkd_9988 | **ABSENT** | C15 re-run: 0 of 118,022 claims carry '9988' in scope; exact scan recorded (json.loads per line). Would-be owner: engine/qledger.py via the V0 SNI claim contract (not on main; #8042 held carrier) |
| evaluation_qledger.rmb_89988 | **ABSENT** | same scan for '89988' → 0 claims |
| evaluation_qledger.adr_baba | **PARTIAL** (missing: issuer_subject) | **159** claims with `scope.key == 'BABA'` (families: us_importance_v0 78, us_importance_v0_pit 78, altdata 1, altdata_event 1, altdata_mid 1; re-run 2026-10-11). A raw substring scan for "BABA" hits 163 lines — the 4 extra are OTHER entities' claims that merely mention BABA (claim ids 969905d24586619b scope BRO altdata_event; 4d48b1a649685a97 TTD altdata_event; 27c2a75f33a764fe LYB altdata_mid; 1a3f48a5e52b4f35 KVUE altdata_mid); the scope.key count **159** is the evidence_rows value. issuer_subject MISSING — the scope key is the RAW TICKER STRING 'BABA', not an issuer id (SCOPE_KEY_IS_RAW_TICKER_NOT_ISSUER_ID). Metadata owner-recorded per claim: desk, asof, scope{type entity, key BABA}, direction, horizon_d, bench, check_by, timestamp_quality (DISCLOSURE_DATE / CRAWL_BOUNDED), is_placebo, claim_family (a versioned definition name, e.g. us_importance_v0), claim_id, timestamp, status; grades file carries graded_at/embargo_applied. Claim/falsifier prose and entry levels deliberately NOT copied (private text + out-of-scope fields; A20). Census only — no hit-rate or return grading is presented as forecast support (profile family_notes) |

## behavioral_pilot — AUGUST 2026 STOCK-IDENTITY PILOT (HISTORICAL)

| metric_id | status | evidence |
|---|---|---|
| behavioral_pilot.hkd_9988 | **ABSENT** | pilot store `pilot_fingerprint_v0.parquet` (cd7675e995b4) holds exactly 21 US symbols (AEM, AG, BABA, CBRS, FFAI, GOLD, HL, KO, KRUS, MCD, MCK, META, MSFT, NEM, NVDA, PAAS, REGN, UEC, WMT, WPM, YELP); 9988 not present. HISTORICAL: pilot frozen 2026-08-13; absence blocks nothing (profile) |
| behavioral_pilot.rmb_89988 | **ABSENT** | same store; 89988 not present |
| behavioral_pilot.adr_baba | **PARTIAL** (missing: unit_currency; source = the FROZEN 2026-08 research pilot — read as HISTORICAL only, never current data) | fingerprint row symbol BABA: asof 2026-08-13, epoch_key epoch_0, epoch_detector "none/provisional", price_plane_id stock_identity_ohlcv_v1, n_sessions 2992, fingerprint_spec_hash 0e3457b1…; manifest (b74ae237e99b, schema stock_identity.ohlcv_manifest.v1) records fetched_at 2026-08-14T10:52:09Z, adjustment_mode "auto_adjust=True (dividend/split adjusted total-return)", fetcher collectors._stock_ohlc.fetch_ohlc, authority all-false (can_rank/gate/originate_signal/size/escalate all false — owner-recorded); pilot OHLCV 2,992 rows 2014-09-19..2026-08-13; episode file carries per-episode resolution_known_date fields. Unit: the plane declares adjustment mode but no currency → unit/currency missing. Correction state: HISTORICAL prior art, never current behaviour (profile family_notes + manifest authority block) |

---

## A33 required-source classes (coordinator ruling) — satisfaction map

Exactly **ONE** of the six required source classes is satisfied: identity_listing, via
identity_listing.adr_baba only. Machine-readable twin: `a33_required_source_classes` in
`E1_COVERAGE_REPORT_2026-10-11.json`.

| class | satisfied? | best cell | best status | blocking missing descriptors | would-be owner |
|---|---|---|---|---|---|
| identity_listing | **YES** | identity_listing.adr_baba | OWNER_NATIVE | — | n/a — satisfied: adr_baba owner-records security SEC:US-XNYS-BABA bound to issuer ISS:US-XNYS-BABA |
| filings_announcements | **NO — GAP** | filings_announcements.hkd_9988 | PARTIAL | issuer_subject, reporting_period, definition_version, correction_refusal_state | collectors/hk_hkexnews.py + engine/hk_filing_bus.py once the category taxonomy carries a version id, a correction/retraction field exists, and the subject binds through the Data OS identity axis |
| financials | **NO — GAP** | financials.hkd_9988 | PARTIAL | issuer_subject, known_at_evidence, unit_currency, accounting_basis, source_span, definition_version, correction_refusal_state | Data OS issuer axis: scripts/build_security_master.py (apply_issuer_correction) under a new issuer-evidence era declared in config/identity_seams.yml, read via lib/dataos/identity.py (binds issuer_subject only; no owner exists for the remaining descriptor gaps) |
| company_events_earnings_calendar | **NO — GAP** | company_events_earnings_calendar.adr_baba | PARTIAL | definition_version | collectors/hk_hkexnews.py + engine/hk_filing_bus.py once the category taxonomy carries a version id, a correction/retraction field exists, and the subject binds through the Data OS identity axis |
| corporate_actions_adjustment | **NO — GAP** | corporate_actions_adjustment.adr_baba | PARTIAL | known_at_evidence, definition_version | collectors/yahoo.py-class adjustment metadata carrying known-at stamps and a definition version, plus an explicit HK corporate-action ledger (profile names no would_be_owner for this class; pack-named) |
| market_data_daily | **NO — GAP** | market_data_daily.adr_baba | PARTIAL | known_at_evidence, unit_currency, definition_version | collectors/hk_stock_prices.py / collectors/yahoo.py / collectors/massive_stock_day.py recording a known-at column, a declared currency and a definition version (profile names no would_be_owner for these descriptors; pack-named) |

No cell was upgraded to OWNER_NATIVE to satisfy A33; the hkd_9988 identity cell is REFUSED (the
owner's own NO_ISSUER_EVIDENCE), and the five GAPs above are the honest answer to the class
requirement.

## Binding E0 facts — how each was honored

1. `ISS:US-XNYS-BABA` is the only resolved issuer id and is attached ONLY to the ADR line; the
   HK counters carry issuer NULL / NO_ISSUER_EVIDENCE exactly as the owners record.
2. 89988 has no security_id: every 89988 cell that needs identity is NO_OWNER; where an owner
   natively records the raw counter code (hk_shorts stock_code 89988; hk_filings stock_code
   "09988<br/>89988") the subject descriptor cites that raw string — no id is constructed.
3. The hk_fundamentals HKD-on-CNY currency defect is carried in the correction/refusal state of
   financials.hkd_9988 and probe P5 — PARTIAL, never relabelled or converted.
4. BABA has 0 rows in every FIF / fundamental_forensics / capital-structure artifact (C13), so
   every A11 share-count/valuation denominator for Alibaba is REFUSED (probe P1); no
   denominator was computed in this pack.
5. southbound_holdings.adr_baba is recorded REFUSED / NOT_APPLICABLE_PER_PROFILE, no value.

## GAPS

Every NO_OWNER and ABSENT cell (25 ids), one per line, with its would-be owner (the E0 profile
cell's `would_be_owner` where present; otherwise the owner this pack names, suffixed
"(pack-named)"):

NO_OWNER (13):

- adr_h_basis.rmb_89988 — engine/hk_adr_bridge.py after counter prices exist
- corporate_actions_adjustment.rmb_89988 — collectors/hk_stock_prices.py + a Data OS counter security_id
- financials.rmb_89988 — Data OS issuer axis: scripts/build_security_master.py (apply_issuer_correction) under a new issuer-evidence era declared in config/identity_seams.yml, read via lib/dataos/identity.py
- identity_listing.rmb_89988 — Data OS CN/HK admission: scripts/build_security_master.py under research/prophet_v4/d2/D2B2_CN_HK_FROZEN_CONTRACT_2026-08-20.md, with a counter seam (one economic security, two trading counters) declared in config/identity_seams.yml
- market_data_daily.rmb_89988 — collectors/hk_stock_prices.py (universe via collectors/hk_universe.py) after a Data OS counter security_id exists
- market_data_intraday.hkd_9988 — Chairman procurement decision, then a new HK intraday collector
- market_data_intraday.rmb_89988 — Chairman procurement decision, then a new HK intraday collector
- news.rmb_89988 — Data OS CN/HK admission: scripts/build_security_master.py under research/prophet_v4/d2/D2B2_CN_HK_FROZEN_CONTRACT_2026-08-20.md, with a counter seam (one economic security, two trading counters) declared in config/identity_seams.yml
- options.hkd_9988 — Chairman procurement decision, then an HK options owner
- options.rmb_89988 — Chairman procurement decision, then an HK options owner
- research_vault.rmb_89988 — Data OS CN/HK admission: scripts/build_security_master.py under research/prophet_v4/d2/D2B2_CN_HK_FROZEN_CONTRACT_2026-08-20.md, with a counter seam (one economic security, two trading counters) declared in config/identity_seams.yml
- southbound_holdings.rmb_89988 — collectors/hk_southbound_holdings.py after a Data OS counter security_id exists
- themes.rmb_89988 — Data OS CN/HK admission: scripts/build_security_master.py under research/prophet_v4/d2/D2B2_CN_HK_FROZEN_CONTRACT_2026-08-20.md, with a counter seam (one economic security, two trading counters) declared in config/identity_seams.yml

ABSENT (12):

- adr_h_basis.adr_baba — engine/hk_adr_bridge.py (pack-named; profile names no would_be_owner for this cell)
- adr_h_basis.hkd_9988 — engine/hk_adr_bridge.py (pack-named; profile names no would_be_owner for this cell)
- behavioral_pilot.hkd_9988 — engine/stock_identity/pilot.py (no refresh scheduled)
- behavioral_pilot.rmb_89988 — engine/stock_identity/pilot.py (no refresh scheduled)
- corporate_actions_adjustment.hkd_9988 — an explicit HK corporate-action ledger (pack-named; profile names no would_be_owner for this cell)
- evaluation_qledger.hkd_9988 — engine/qledger.py via the V0 contract lane
- evaluation_qledger.rmb_89988 — engine/qledger.py via the V0 contract lane
- filings_announcements.adr_baba — engine/fundamental_forensics/broad_sec_store.py universe (20-F filer admission)
- financials.adr_baba — engine/fundamental_forensics/sec_companyfacts.py (20-F filer admission)
- market_data_intraday.adr_baba — engine/intraday_flow.py universe
- news.adr_baba — collectors/hk_gdelt.py (pack-named; profile names no would_be_owner for this cell)
- short_positions.adr_baba — collectors/finra.py universe

A33 class gaps (5):

- filings_announcements — best cell filings_announcements.hkd_9988, PARTIAL; blocking
  issuer_subject, reporting_period, definition_version, correction_refusal_state; would-be owner
  collectors/hk_hkexnews.py + engine/hk_filing_bus.py once the category taxonomy carries a
  version id, a correction/retraction field exists, and the subject binds through the Data OS
  identity axis.
- financials — best cell financials.hkd_9988, PARTIAL; blocking issuer_subject,
  known_at_evidence, unit_currency, accounting_basis, source_span, definition_version,
  correction_refusal_state; would-be owner the Data OS issuer axis (binds issuer_subject only;
  no owner exists for the remaining descriptor gaps).
- company_events_earnings_calendar — best cell company_events_earnings_calendar.adr_baba,
  PARTIAL; blocking definition_version; would-be owner as filings_announcements (HK filing-bus
  version id + correction/retraction field + identity-axis subject binding).
- corporate_actions_adjustment — best cell corporate_actions_adjustment.adr_baba, PARTIAL;
  blocking known_at_evidence, definition_version; would-be owner an explicit HK corporate-action
  ledger plus collectors/yahoo.py-class adjustment metadata with known-at stamps and a
  definition version (pack-named).
- market_data_daily — best cell market_data_daily.adr_baba, PARTIAL; blocking known_at_evidence,
  unit_currency, definition_version; would-be owner collectors/hk_stock_prices.py /
  collectors/yahoo.py / collectors/massive_stock_day.py recording a known-at column, a declared
  currency and a definition version (pack-named).

Standing DEC note: BABA has 0 rows in every FIF / fundamental_forensics / capital-structure
artifact (C13) and 0 FINRA rows (C12); the would-be owners above are gated by
DEC:FINANCE-SEC-EVIDENCE-RIGHTS-HELD-UNTIL-FAMILY-ADMITTED where applicable.

## COORDINATOR CONTRADICTIONS

None. Every owner re-run performed for this repair agreed with the frozen target table (R3/R4):
qledger scope.key=='BABA' re-run → 159 (coordinator's recount), families exactly as ruled;
identity-resolution history via `latest=False` → 61 rows for co:us:BABA and 61 for co:hk:9988.HK
(the previously cited "122 rows from `read_identity_resolution()`" was a call misattribution,
fixed under R6); hk_placements re-run → 811 rows (count unchanged; the cited span was stale and
is corrected to the re-run span ..2026-10-11 under F14); hk_shorts re-run → 357 rows (9988) and
172 rows (89988), value column `value_hkd`. No target row was contradicted by an owner output.

## REVIEW DISPOSITIONS

Disposition of the independent review lane's findings on this pack (verdict REQUEST_CHANGES;
each REPAIR below is binding and was applied in this edit):

- **F1 (BLOCKER — filings/events hkd_9988 + rmb_89988 marked OWNER_NATIVE; A33 map said YES for
  both classes): REPAIRED.** All four rows are now PARTIAL with missing
  [issuer_subject, reporting_period, definition_version, correction_refusal_state]; the A33 map
  shows both classes as GAP with would-be owner "collectors/hk_hkexnews.py +
  engine/hk_filing_bus.py once the category taxonomy carries a version id, a
  correction/retraction field exists, and the subject binds through the Data OS identity axis".
  The store has no correction field and `engine/hk_filing_bus.py` has no version constant; the
  store-window coverage text is NOT presented as a correction state.
- **F4 (themes.hkd_9988 OWNER_NATIVE with owner-recorded issuer_id NULL): REPAIRED** per the
  frozen table — now PARTIAL [issuer_subject] with note
  GRAPH_NODE_RESOLVES_TO_SECURITY_ONLY_NO_ISSUER_EVIDENCE.
- **F6 (identity_listing.hkd_9988): RULED by the coordinator — status stays REFUSED** (the
  commission requires the E0 fact "HK counters are NO_ISSUER_EVIDENCE" to appear as a
  REFUSED/NO_OWNER row, and the owner-recorded NO_ISSUER_EVIDENCE is the owner's refusal of
  exactly this metric's issuer–security link); **the reviewer's descriptor reading (only
  issuer_subject missing) is ADOPTED.** The ruling sentence sits under the identity_listing
  table.
- **F7 (evaluation_qledger.adr_baba OWNER_NATIVE on raw scope key): REPAIRED** — now PARTIAL
  [issuer_subject] with note SCOPE_KEY_IS_RAW_TICKER_NOT_ISSUER_ID; count corrected to the
  scope.key re-run (see R5 disposition below).
- **F13 ("ir.read_identity_resolution() (122 Alibaba rows = 61+61)" misattributed a store-level
  count to a latest-only call): REPAIRED** per R6 — the history count is now cited to
  `read_identity_resolution(latest=False)` (61 rows per node, re-run 2026-10-11), and the
  default `latest=True` call is marked one-row-per-node.
- **F14 (hk_placements span cited 2026-03-05..2026-10-09 was stale): REPAIRED** — re-run
  `fb._load_placements()` (columns news_id/stock_code/ticker/category/announced_at/date/
  title/subcats): 811 rows, `date` 2026-03-05..2026-10-11, `announced_at`
  2026-03-05 06:05:00..2026-10-11 18:25:00; the re-run span is cited verbatim in C10, the
  corporate_actions row, and the JSON owner_call.
- **F15 (sessions_calendar cells omitted definition_version): REPAIRED** — all three cells now
  carry definition_version MISSING (NO_VERSION_CONSTANT_IN_OWNER_MODULE; `grep -in version` over
  `lib/nyse_calendar.py` + `lib/hk_calendar.py` returns no line — a git blob is not an
  owner-declared version) plus the known-at note HOLIDAY_RULES_IN_CODE_NO_PUBLICATION_KNOWN_AT.
- **Review C15 "163 BABA — MATCH" was a substring count: RESOLVED per R5** — the scope.key count
  is 159 (families us_importance_v0 78, us_importance_v0_pit 78, altdata 1, altdata_event 1,
  altdata_mid 1); the 163 substring lines include 4 non-BABA claims (969905d24586619b BRO,
  4d48b1a649685a97 TTD, 27c2a75f33a764fe LYB, 1a3f48a5e52b4f35 KVUE). evidence_rows = 159
  everywhere.
- **Review-side gaps the reviewer did not check: DONE** — `ls data/massive_stock_day | grep -ci
  baba` → 0 and `git rev-parse HEAD:data/massive_stock_day/_manifest.json` →
  17e8338575a12e1ab80f988093a00cf08d8faf4a, both pasted next to the C7 citation.
- Cross-pack findings F2 (constructed id literal for an RMB counter) and F10 (forecast values)
  do not apply to this pack: the substring-scan form is kept for 89988 (no id-shaped string is
  written for it — confirmed by the report's id-literal scan) and forecast values stay
  uncarried.
