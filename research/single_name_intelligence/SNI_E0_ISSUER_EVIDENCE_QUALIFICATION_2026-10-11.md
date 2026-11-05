# SNI E0 — issuer evidence qualification (Alibaba, Tencent) — 2026-10-11

**Unit:** E0 of the SNI end-to-end masterplan (`research/single_name_intelligence/e2e_20261011/MASTERPLAN.md` §6, carried on PR #8773 head `7906ef1c`, not on main). E0 is field-by-field source, rights, coverage, temporal and owner qualification for the reference names, with no procurement.
**Companion:** `SNI_M0_MARKET_DATA_QUALIFICATION_2026-10-11.md` (market, session, corporate-action, FX and adjustment families).
**Machine-readable output:** `config/single_name_intelligence/coverage_profiles/{alibaba,tencent}.yml`, schema `contracts/single_name_intelligence/coverage_profile.v1.schema.json`, pinned by `tests/test_single_name_coverage_profiles.py`.
**Status of this record:** qualification facts about existing owners. Nothing here is a signal, score, rank, gate or forecast. All six authority flags (rank, gate, size, signal, escalation, trade) are false in both profiles. No identity id was minted.

## 0. What blocks C2 and S0 today

C2 (reference-twin read model) needs C1 + E0 + M0, and S0 (frozen research registrations) needs E0 + M0 + V0. Neither can start on what is on main today, for five reasons:

1. **C1 is not admitted.** The relationship contract sits on #8711, which is open and not on main. This blocks C2 by itself.
2. **V0 is not on main.** The qledger/evaluation contract carrier #8042 is held. This blocks S0 by itself.
3. **E0 identity is incomplete.** Data OS links only the BABA ADS to an issuer (`ISS:US-XNYS-BABA`, SEC-registrant axis). `SEC:HK-XHKG-09988` and `SEC:HK-XHKG-00700` exist with `NO_ISSUER_EVIDENCE`. The RMB counters 89988 and 80700 have no `security_id` at all. Tencent Holdings has no issuer id; `ISS:US-XNYS-TME` is Tencent Music, a different issuer.
4. **No admitted financial-metric owner exists for either issuer.** No owner carries the masterplan's required descriptors: metric id, reporting period, known-at, unit/currency, accounting basis, source span, definition version and correction state. BABA has zero FIF or capital-structure rows. The HK akshare snapshot (asof 2026-06-18) is stale and its rights are UNVERIFIED.
5. **M0 has no reproducible admitted input contract.** The price basis is total-return adjusted and is re-adjusted on every refresh, with dividend-adjustment vintages spliced in `closes_deep`. RMB-counter prices, the ADS-to-share ratio and HK intraday are absent. USD/HKD exists only as a yfinance mirror (`data/hk/HKD_X.parquet`), and offshore CNH only as a futures proxy (`CNH=F`). BABA options are stale since 2026-08-21, and HK options are blocked on procurement. Every market-data source's rights are UNVERIFIED.

The cheapest unblock order is: C1 admission (#8711) → a Data OS issuer/counter seam (the owner named in §2) → an E1/E2 owner-scoped metric child → an M0 adjustment-vintage pin. Procurement (HK intraday, HK options) blocks only S0 response-window and options families; it does not block C2.

## 1. Method and receipts

- **Repository reference:** origin/main `6f4e215d26b1` (fetched 2026-10-11T09:00Z).
- **Data reads:** read-only from the macro checkout at `eb55c8573d94`. Every cited evidence path is tracked on origin/main; the existence check is listed in the O2 return.
- **Census method:** the census ran directly under the execution-continuation law. Fabric launch receipts:
  - local `sub.sh`: rc=78 `LOCAL_SEAT_REMOTE_REQUIRED`;
  - `remote_sub.sh auto glm-codex` dry run: rc=3 `NO_HOST`.

  The seat later diagnosed the second receipt as a pool-name mismatch (the mode `glm-codex` is admitted only on ubuntu0) and confirmed the census was not to be redone.
- **Census correction:** a second targeted pass found stores the first pass missed: USD/HKD (`data/hk/HKD_X.parquet`), offshore-CNH futures (`data/china/CNH_F.parquet`), HK benchmarks, `data/hk_placements/`, `data/hk_connect_roster/` and `data/hk_valuation/`. The profiles and both records carry the corrected facts. An earlier draft claim that no owner carries USD/HKD is withdrawn.
- **Exact matching:** probes used exact ticker/code `isin` matching, not substring regexes. Absence claims are bounded to the stores named in each cell.
- **Status meanings:**
  - `ready`: an owner exists, coverage is present, the clock is known, and rights are verified-internal.
  - `partial`: an owner exists but carries a named defect (rights UNVERIFIED, stale, missing fields).
  - `UNRESOLVED`: no owner join exists. The cell names its `would_be_owner`.
  - `BLOCKED`: the gap needs procurement or a licence. The cell names its `would_be_owner`.
- **Typed absences:** not-applicable cells (BABA Southbound) are `applicable: false` and are counted separately.
- **Rights classes:**
  - `verified-internal`: an in-repo owner receipt or decision admits the source. Examples: Data OS identity (SEC + SFC/HKEX), SFC short positions, house-generated qledger, house code calendars.
  - `UNVERIFIED`: no such receipt exists. This covers yfinance, akshare/Eastmoney, HKEXnews scrape, GDELT, FRED, Nasdaq, ThetaData and FINRA.
  - `BLOCKED-procurement`: a paid HKEX product that has not been bought.
  - `BLOCKED-licence`: data that can be reached but whose use needs a formal licence, such as first-party CCASS.

## 2. Identity (the gating family)

| counter | security_id (owner: `lib/dataos/identity.py`) | issuer link | evidence | would-be owner of the gap |
|---|---|---|---|---|
| BABA (NYSE ADS) | `SEC:US-XNYS-BABA` | `ISS:US-XNYS-BABA` RESOLVED (era `issuer_semantic_correction_v1`, evidence `sec_company_tickers`, snapshot 2026-08-18; CIK 0001577552 is evidence only) | `data/reference/{security_master,issuer_master,vendor_aliases}.parquet` | — |
| 9988 (HKD) | `SEC:HK-XHKG-09988` (effective 2019-11-29) | UNRESOLVED (`NO_ISSUER_EVIDENCE`) | same + `data/reference/_receipt.json` (china_hk_admission: SFC short positions + HKEX turnover) | `scripts/build_security_master.py` `apply_issuer_correction` under a new issuer-evidence era in `config/identity_seams.yml` |
| 89988 (RMB) | absent | absent | appears only in SFC short positions and HKEXnews stock-code lists | `scripts/build_security_master.py` CN/HK admission (`research/prophet_v4/d2/D2B2_CN_HK_FROZEN_CONTRACT_2026-08-20.md`) plus a counter seam in `config/identity_seams.yml` |
| 700 (HKD) | `SEC:HK-XHKG-00700` (effective 2012-08-31) | UNRESOLVED (`NO_ISSUER_EVIDENCE`) | same | as for 9988 |
| 80700 (RMB) | absent | absent | as for 89988 | as for 89988 |

**Why the HK links are missing.** The issuer axis groups securities only by an identical SEC CIK, so an HK-only listing can never acquire an issuer. CN/HK admission is driven by theme-graph company nodes: `co:hk:9988.HK`, `co:hk:0700.HK` and `co:us:BABA` exist, but no node exists for either RMB counter, so neither counter was ever admitted.

**Theme-graph resolution.** Theme-graph identity resolution (`data/theme_graph/identity_resolution.parquet`, 61 snapshots, latest 2026-10-09) resolves 9988.HK and 0700.HK to their securities with a NULL issuer, and BABA to `ISS:US-XNYS-BABA` via `master_inception_exact`.

**What this record does not do.** It does not link any HK counter to an issuer from its ticker, name or CIK. That link is the Data OS owner's act (masterplan §5.2: owner-supplied canonical ids only).

**Current identity only.** Data OS carries current identity only. Historical issuer lineage would need the accepted historical bridge, not today's grouping applied backward (§5.2).

## 3. Per-family findings (E0 families)

The tables below are generated from the profiles. Each cell reads `status · rights · temporal state`. Coverage counts, spans, clocks and notes live in the YAML.

**Alibaba Group Holding Ltd** (`canonical_issuer_id: ISS:US-XNYS-BABA`)

| family | `hkd_9988` | `rmb_89988` | `adr_baba` |
|---|---|---|---|
| identity_listing | partial · verified-internal · LIVE | UNRESOLVED · verified-internal · NONE | ready · verified-internal · LIVE |
| filings_announcements | partial · UNVERIFIED · LIVE | UNRESOLVED · UNVERIFIED · LIVE | UNRESOLVED · UNVERIFIED · NONE |
| financials | partial · UNVERIFIED · STALE | UNRESOLVED · UNVERIFIED · STALE | UNRESOLVED · UNVERIFIED · NONE |
| company_events_earnings_calendar | partial · UNVERIFIED · LIVE | UNRESOLVED · UNVERIFIED · LIVE | partial · UNVERIFIED · STALE |
| research_vault | partial · UNVERIFIED · LIVE | UNRESOLVED · UNVERIFIED · LIVE | partial · UNVERIFIED · LIVE |
| news | partial · UNVERIFIED · LIVE | UNRESOLVED · UNVERIFIED · NONE | partial · UNVERIFIED · LIVE |
| themes | partial · UNVERIFIED · LIVE | UNRESOLVED · UNVERIFIED · NONE | partial · UNVERIFIED · LIVE |
| evaluation_qledger | UNRESOLVED · verified-internal · NONE | UNRESOLVED · verified-internal · NONE | partial · verified-internal · LIVE |
| behavioral_pilot | UNRESOLVED · verified-internal · HISTORICAL | UNRESOLVED · verified-internal · HISTORICAL | partial · verified-internal · HISTORICAL |

**Tencent Holdings Ltd** (`canonical_issuer_id: UNRESOLVED`)

| family | `hkd_0700` | `rmb_80700` |
|---|---|---|
| identity_listing | partial · verified-internal · LIVE | UNRESOLVED · verified-internal · NONE |
| filings_announcements | partial · UNVERIFIED · LIVE | UNRESOLVED · UNVERIFIED · LIVE |
| financials | partial · UNVERIFIED · STALE | UNRESOLVED · UNVERIFIED · STALE |
| company_events_earnings_calendar | partial · UNVERIFIED · LIVE | UNRESOLVED · UNVERIFIED · LIVE |
| research_vault | partial · UNVERIFIED · LIVE | UNRESOLVED · UNVERIFIED · LIVE |
| news | partial · UNVERIFIED · LIVE | UNRESOLVED · UNVERIFIED · NONE |
| themes | partial · UNVERIFIED · LIVE | UNRESOLVED · UNVERIFIED · NONE |
| evaluation_qledger | UNRESOLVED · verified-internal · NONE | UNRESOLVED · verified-internal · NONE |
| behavioral_pilot | UNRESOLVED · verified-internal · HISTORICAL | UNRESOLVED · verified-internal · HISTORICAL |

- **filings_announcements.** Owners are `collectors/hk_hkexnews.py` and `engine/hk_filing_bus.py`. They scrape HKEXnews headline metadata only: 3,905 rows from 2026-04-13 to 2026-10-09.
  - 9988 has 4 events: final_results 1 and general_mandate 3. The three general_mandate events are the HK$80bn new-share placing, 2026-08-23 to 08-26. The stock-code field reads `09988<br/>89988`.
  - 700 has 1 event: interim_results on 2026-08-12. Its stock-code list includes 80700.
  - The store has no dividend category.
  - There is no full text, no metric extraction and no history before 2026-04-13.
  - BABA's SEC route (`engine/fundamental_forensics/broad_sec_store.py`, `engine/capital_structure/source_identity.py`) admits 20-F/6-K forms in code but carries **zero** occurrences for CIK 1577552 (`data/capital_structure/{discovery,event_versions}.parquet`, `data/fundamental_forensics/public_summary.json`).
  - `DEC:FINANCE-SEC-EVIDENCE-RIGHTS-HELD-UNTIL-FAMILY-ADMITTED` holds SEC-evidence display rights until the family is admitted.
- **financials.** The owner is `collectors/hk_fundamentals.py` (akshare, `data/hk_fundamentals/fundamentals.parquet`).
  - Coverage: annual indicators (9988.HK fy2020 to fy2026, where the fiscal year ends in March and the fy label convention is undeclared; 0700.HK fy2019 to fy2025), plus a profile and a third-party forecast block. The snapshot asof is 2026-06-18, and per-row source is not recorded.
  - **The currency descriptor is present but untrustworthy.** Every financial row for both names carries a vendor `currency` field reading `HKD`, while the collector's own header notes that names such as Tencent report in CNY. A consumer reading that field would mislabel the reporting currency.
  - None of the other masterplan metric descriptors are present beyond the economic period: known-at, accounting basis, source span, definition version and correction state.
  - BABA has no metric rows in any owner (`engine/fundamental_forensics/sec_companyfacts.py`). The companyfacts directory holds only a publish lock.
  - The forecast block is consensus display material and is never an expectation lens.
  - `collectors/hk_valuation.py` (`data/hk_valuation/by_name.parquet`) carries vendor PE/PB ratios for 00700 and 09988: 96 rows, 2026-06-18 to 2026-10-09. These are vendor-computed ratios, not reported metrics, and their rights are UNVERIFIED.
- **company_events_earnings_calendar.**
  - HK names: only realized results announcements exist inside the hkexnews window.
  - `engine/hk_event_calendar.py` is a macro/policy calendar, and `engine/hk_catalyst_calendar.py` covers index reviews and Stock Connect eligibility reviews. Neither is an issuer calendar.
  - BABA: `collectors/equity_earnings.py` (Nasdaq public JSON) shows next_date 2026-08-20 at as_of 2026-09-30, a date already in the past. It is STALE. 700 is not in the US calendar.
- **research_vault.** Owners are `engine/research_vault/catalog.py` and `subjects.py`. Of 2,778 items, 41 match an Alibaba name pattern and 19 match a Tencent name pattern. That is a census bound, not a subject-resolved link.
- **news.** The owner is `collectors/hk_gdelt.py`.
  - Coverage: `data/hk_gdelt/alibaba.parquet` has 77 daily rows (2026-07-12 to 2026-10-06, keyed 9988.HK) and `tencent.parquet` has 78 rows (2026-07-13 to 2026-10-10, keyed 0700.HK).
  - These are volume and tone aggregates only, with no article text.
  - Within the searched stores (hk_gdelt, research_vault), no BABA-keyed news owner exists.
- **themes.** Owners are `engine/theme_graph/{identity_resolution,store,rights}.py`. Theme membership is context only. Evidence rows carry licensing fields under `engine/theme_graph/rights.py`; this record does not adjudicate them.
- **evaluation_qledger.** Owners are `engine/qledger.py` and `engine/qledger_store.py`.
  - BABA appears in scope of 159 claims out of 117,961: `us_importance_v0` 78, `us_importance_v0_pit` 78, `altdata` 1, `altdata_event` 1, `altdata_mid` 1. They span 2026-06-22 to 2026-09-27.
  - No HK counter appears in any claim scope.
  - This is an existence census. No hit-rate or return grading is described here as probabilistic forecast support.
  - SNI claim contracts are V0's (#8042 held).
- **behavioral_pilot — HISTORICAL.** The August 2026 stock-identity pilot (`engine/stock_identity/{pilot,fingerprint,plane}.py`) froze at 2026-08-13.
  - It covers 21 US symbols, with BABA epoch_0 none/provisional, OHLCV `auto_adjust=True` and all authority false. No Tencent or HK symbol is included.
  - It is prior art, not a live owner, and blocks nothing.

## 4. Rights table

| source | used by | rights class | basis |
|---|---|---|---|
| SEC company_tickers (Data OS issuer axis) | identity_listing (BABA) | verified-internal | `data/reference/_receipt.json`; Data OS builder |
| SFC short-position reports + HKEX turnover (Data OS CN/HK admission) | identity_listing (HK HKD counters), short_positions | verified-internal | `_receipt.json` china_hk_admission |
| house-generated qledger | evaluation_qledger | verified-internal | in-repo generator |
| house code calendars | sessions_calendar | verified-internal | `lib/hk_calendar.py`, `lib/nyse_calendar.py` |
| HKEXnews titleSearch scrape | filings, company events, placement events (`collectors/hk_placements.py`) | UNVERIFIED | no in-repo terms adjudication; the 08-28 matrix lists the paid IIS feed NOT_BUILT |
| SEC EDGAR via FIF / capital structure | filings, financials (BABA) | UNVERIFIED | `DEC:FINANCE-SEC-EVIDENCE-RIGHTS-HELD-UNTIL-FAMILY-ADMITTED` |
| akshare (Eastmoney/ET) | financials (HK) | UNVERIFIED | no receipt |
| Eastmoney datacenter mirror | southbound_holdings | UNVERIFIED | third-party mirror |
| HK Connect change roster (SSE/SZSE notices) | southbound_holdings (eligibility changes) | UNVERIFIED | `scripts/collect_hk_connect_roster.py`; no rights record |
| Nasdaq public calendar JSON | company events (BABA) | UNVERIFIED | no receipt |
| yfinance | market_data_daily, corporate actions, ADR bridge inputs, fx (`HKD=X`, `CNY=X`, `CNH=F`) | UNVERIFIED | no receipt |
| GDELT | news | UNVERIFIED | no receipt |
| research vault items | research_vault | UNVERIFIED | mixed item provenance |
| theme-graph evidence rows | themes | UNVERIFIED (row-level licensing fields exist) | `engine/theme_graph/rights.py`, not adjudicated here |
| FRED DEXCHUS (Fed H.10) | fx | UNVERIFIED | public-domain Fed series; no in-repo record |
| ThetaData | options (BABA) | UNVERIFIED | subscription vendor; no SNI-scope record |
| FINRA short interest / volume | short_positions (BABA, no rows) | UNVERIFIED | no receipt |
| HKEX Historical Full Book (securities, SOM), trade file, tick-by-tick | intraday, HK options | BLOCKED-procurement | paid; prices in the 08-28 HK qualification (HK$5,000 / 1,500 / 750 / 500 per month) |
| first-party CCASS | southbound comparison | BLOCKED-licence | 08-28 matrix `source_unlicensed` |

## 5. Deltas against the 2026-08-28 prior art (commit `e3b1d5c7`; cited, not copied)

1. **Counter grouping.** `SNI1_OWNER_SOURCE_MATRIX_2026-08-28.md` lines 39 and 41 asked that 9988/89988 be grouped under one security, and 700/80700 likewise. **Still open.** Data OS has no counter grouping, and the RMB counters are not in the master.
2. **Issuer axis is new.** `ISS:US-XNYS-BABA` exists under era `issuer_semantic_correction_v1` (snapshot 2026-08-18). It postdates the matrix but covers only the SEC-registrant axis.
3. **Theme-graph identity resolution is new.** It has 61 snapshots since 2026-08-18.
4. **TCEHY (line 137, "no qualified owner, NOT_BUILT").** `data/yahoo/TCEHY.parquet` now exists (4,216 rows), but it is not admitted as a Data OS security. The bridge comment in `engine/hk_adr_bridge.py` still says TCEHY is "not in yahoo store". That comment is stale.
5. **BABA options (line 145, "mixed owner state").** Now STALE: the last skew snapshot is from 2026-08-21.
6. **HK stock options (lines 147–150).** Unchanged: NOT_BUILT, `source_unlicensed` (here BLOCKED-procurement).
7. **Southbound (line 160).** Unchanged: PARTIAL, Eastmoney mirror. First-party CCASS (line 163) is still unlicensed.
8. **HKEXnews collector window is new.** `collectors/hk_hkexnews.py` has carried issuer events since 2026-04-13.
9. **SFC short positions now carry the RMB counters.** There are 172 weekly rows each for 89988 and 80700 from 2023-06-23. This is the first owner-observed RMB-counter data, but it has no `security_id` to join on.
10. **qledger BABA claims are new** (`us_importance_v0` family, from 2026-06-22).
11. **The 08-28 BABA→9988 bridge** (HK qualification line 51, "PROVEN_LIVE display") is still display-only. The ADS-to-share ratio is still uncarried. USD/HKD is carried, but only as a yfinance mirror with UNVERIFIED rights.
12. **The August pilot is now HISTORICAL** (frozen 2026-08-13).
13. **Placement owner exists but misses the issuer event.** `collectors/hk_placements.py` (810 rows, 2026-03-05 to 2026-10-09) keys on the HKEXnews `placing` headline category. It holds no 9988 row, because HKEXnews filed Alibaba's HK$80bn placing under `general_mandate`.
14. **Connect eligibility change roster is new.** `data/hk_connect_roster/roster.parquet` records the 9988 Southbound add (announced 2024-09-09, effective 2024-09-10, source sse). It holds no 0700, 89988 or 80700 row. It is a change roster, so a missing row is not an eligibility verdict.

## 6. Counts (from the profiles)

| issuer | cells | ready | partial | UNRESOLVED | BLOCKED | n/a (typed absence) |
|---|---|---|---|---|---|---|
| Alibaba (3 counters × 18 families) | 54 | 5 | 25 | 19 | 4 | 1 |
| Tencent (2 counters × 18 families) | 36 | 3 | 13 | 16 | 4 | 0 |

Split by unit:
- **Alibaba:** E0 is 1 ready / 13 partial / 13 UNRESOLVED. M0 is 4 ready / 12 partial / 6 UNRESOLVED / 4 BLOCKED / 1 n/a.
- **Tencent:** E0 is 0 ready / 7 partial / 11 UNRESOLVED. M0 is 3 ready / 6 partial / 5 UNRESOLVED / 4 BLOCKED.

The only `ready` E0 cell for either issuer is BABA identity.

## 7. Gaps (each names its closing owner)

1. **HK issuer links for 9988/700.** Owner: Data OS issuer axis (`scripts/build_security_master.py`, a new era in `config/identity_seams.yml`). It needs non-SEC issuer evidence, for example the HKEX issuer page.
2. **RMB counter securities 89988/80700.** Owner: Data OS CN/HK admission plus a counter seam.
3. **Tencent Holdings issuer id.** Same owner as gap 1.
4. **Metric descriptors (masterplan §7 E0–E2).** No owner carries them, and the one present (`currency`) mislabels RMB-reported figures as HKD. E1/E2 need an owner-scoped child of FIF (20-F filer admission for BABA) and of `collectors/hk_fundamentals.py` (known-at, currency, basis). This is not a new SNI financial database.
5. **Forward HK results dates.** No owner exists. A child of `collectors/hk_hkexnews.py` or of the issuer calendar would close it.
6. **Stale BABA next earnings date.** Owner: `collectors/equity_earnings.py`.
7. **Subject-resolved research-vault and news links.** Owners: `engine/research_vault/subjects.py` and `collectors/hk_gdelt.py`.
8. **Rights adjudication** for every UNVERIFIED source in §4. The owner is the source-rights authority; this record procures and accepts nothing.
9. **Stale TCEHY comment** in `engine/hk_adr_bridge.py` (mechanical; out of scope here).
10. **Placement category filter** in `collectors/hk_placements.py` misses general-mandate placings such as 9988's (mechanical; owner `collectors/hk_placements.py`; out of scope here).
