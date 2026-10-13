# SNI M0 — market and response-data qualification (Alibaba, Tencent) — 2026-10-11

**Unit:** M0 of the SNI end-to-end masterplan (`research/single_name_intelligence/e2e_20261011/MASTERPLAN.md` §6, carried on PR #8773 head `7906ef1c`, not on main). M0 is the market, session, corporate-action, FX and adjustment census, plus the admitted input contract that a reproducible response window would need. The masterplan assigns M0 to O3; this record was commissioned to O2 together with E0.
**Companion:** `SNI_E0_ISSUER_EVIDENCE_QUALIFICATION_2026-10-11.md`. Identity facts, the rights table and the C2/S0 blocker paragraph live there; this record does not repeat them.
**Machine-readable output:** the M0 families in `config/single_name_intelligence/coverage_profiles/{alibaba,tencent}.yml`.
**Status of this record:** qualification facts about existing owners. Nothing here is a signal, score, rank, gate or forecast. All six authority flags are false in both profiles. No identity id was minted. No source was procured and no licence was accepted.

## 0. Bottom line

No response window for either issuer can be computed reproducibly from what is on main today.

- **Daily windows on 9988, 700 and BABA** can be computed, but only as research display. They become reproducible only after an adjustment vintage is pinned, and every input's rights are UNVERIFIED.
- **No intraday window exists for any counter.** For HK this is BLOCKED-procurement; for BABA no owner carries it.
- **The RMB counters 89988 and 80700 have no prices in any owner.**
- **No ADS↔H basis can be reproduced**, because no owner carries the ADS-to-share ratio.

M0's own blockers to C2 are therefore the adjustment-vintage pin, the RMB-counter securities and prices, and FX/price rights. S0 additionally needs intraday and HK options for the response-window and options families. Procurement is out of scope for this unit.

## 1. Method

- **Repository and data references:** origin/main `6f4e215d26b1`. Data was read read-only from the macro checkout at `eb55c8573d94`. Each cited path is tracked on origin/main (`git cat-file -e`, listed in the O2 return).
- **Census history:** the census ran directly; the fabric receipts are in the E0 record §1.
- **Census correction:** a second targeted pass found USD/HKD, CNH futures, HK benchmarks, placements, the Connect change roster and HK valuation stores, which the first pass had missed. An earlier draft claim that no owner carries USD/HKD is withdrawn.
- **Absence claims:** each is bounded to the owner stores the cell names.

## 2. Family tables

Format: `status · rights · state`.


**Alibaba Group Holding Ltd** (`canonical_issuer_id: ISS:US-XNYS-BABA`)

| family | `hkd_9988` | `rmb_89988` | `adr_baba` |
|---|---|---|---|
| market_data_daily | partial · UNVERIFIED · LIVE | UNRESOLVED · UNVERIFIED · NONE | partial · UNVERIFIED · LIVE |
| market_data_intraday | BLOCKED · BLOCKED-procurement · NONE | BLOCKED · BLOCKED-procurement · NONE | UNRESOLVED · UNVERIFIED · NONE |
| corporate_actions_adjustment | partial · UNVERIFIED · LIVE | UNRESOLVED · UNVERIFIED · NONE | partial · UNVERIFIED · LIVE |
| sessions_calendar | ready · verified-internal · LIVE | ready · verified-internal · LIVE | ready · verified-internal · LIVE |
| southbound_holdings | partial · UNVERIFIED · LIVE | UNRESOLVED · UNVERIFIED · NONE | n/a (typed absence) |
| short_positions | ready · verified-internal · LIVE | partial · verified-internal · LIVE | UNRESOLVED · UNVERIFIED · NONE |
| adr_h_basis | partial · UNVERIFIED · LIVE | UNRESOLVED · UNVERIFIED · NONE | partial · UNVERIFIED · LIVE |
| fx | partial · UNVERIFIED · LIVE | partial · UNVERIFIED · LIVE | partial · UNVERIFIED · LIVE |
| options | BLOCKED · BLOCKED-procurement · NONE | BLOCKED · BLOCKED-procurement · NONE | partial · UNVERIFIED · STALE |

**Tencent Holdings Ltd** (`canonical_issuer_id: UNRESOLVED`)

| family | `hkd_0700` | `rmb_80700` |
|---|---|---|
| market_data_daily | partial · UNVERIFIED · LIVE | UNRESOLVED · UNVERIFIED · NONE |
| market_data_intraday | BLOCKED · BLOCKED-procurement · NONE | BLOCKED · BLOCKED-procurement · NONE |
| corporate_actions_adjustment | partial · UNVERIFIED · LIVE | UNRESOLVED · UNVERIFIED · NONE |
| sessions_calendar | ready · verified-internal · LIVE | ready · verified-internal · LIVE |
| southbound_holdings | partial · UNVERIFIED · LIVE | UNRESOLVED · UNVERIFIED · NONE |
| short_positions | ready · verified-internal · LIVE | partial · verified-internal · LIVE |
| adr_h_basis | UNRESOLVED · UNVERIFIED · LIVE | UNRESOLVED · UNVERIFIED · NONE |
| fx | partial · UNVERIFIED · LIVE | partial · UNVERIFIED · LIVE |
| options | BLOCKED · BLOCKED-procurement · NONE | BLOCKED · BLOCKED-procurement · NONE |

## 3. Per-family findings

### market_data_daily
- **HKD counters (`collectors/hk_stock_prices.py`, yfinance).**
  - `data/hk_stocks/9988.HK.parquet`: 1,681 OHLCV rows, 2019-11-26 to 2026-10-09.
  - `data/hk_stocks/0700.HK.parquet`: 5,485 rows, 2004-06-16 to 2026-10-09.
  - `data/hk_search/closes_deep.parquet` holds 1,690 and 5,511 non-null closes.
  - **Basis:** total-return adjusted only (`auto_adjust=True`). No raw or dividend-unadjusted series is carried.
  - **Vintages:** `overwrite_overlap = True` (`collectors/hk_stock_prices.py`, via `lib/store.py`) re-adjusts the refresh window on every run, and `closes_deep` splices dividend-adjustment vintages (`DSC:HK-DEEP-PANEL-SPLICES-ADJUSTMENT-VINTAGES`).
- **BABA (`collectors/yahoo.py`).**
  - `data/yahoo/BABA.parquet`: 3,032 rows, 2014-09-19 to 2026-10-09.
  - Under the W1.3 contract, `close` is split- and dividend-adjusted (total return) and `close_price` is split-adjusted but dividend-unadjusted.
  - The ratio is 0.9411 at the first row and 1.0 at the last, so a cumulative dividend factor is derivable.
  - The `massive_stock_day` manifest carries no BABA file on main.
- **RMB counters:** no price series in any owner store, so these cells are UNRESOLVED. Never substitute the HKD counter.

### market_data_intraday
- HK, all counters: no owner (BLOCKED-procurement).
  - The 08-28 matrix lists the HKEX Historical Full Book (securities), the trade file and tick-by-tick as paid candidates.
  - `data/intraday_flow/ledger.parquet` is US-only.
- BABA: 0 rows in the intraday-flow ledger (UNRESOLVED).

### corporate_actions_adjustment
- No explicit HK corporate-action ledger exists.
  - Adjustment factors are implicit in yfinance and are not stored.
  - Dividends are not carried as rows, and the hk_filings categories have no dividend class.
- Share-count changes reach the repo only as HKEXnews headline metadata. For 9988 this is the HK$80bn new-share placing (general_mandate, 2026-08-23 to 08-26).
- `collectors/hk_placements.py` (`data/hk_placements/events.parquet`, 810 rows, 2026-03-05 to 2026-10-09; placing 616, rights_issue 194) holds no 9988 or 0700 row. It keys on the HKEXnews `placing` category, so it misses general-mandate placings.
- BABA: a cumulative dividend factor is derivable as `close/close_price`. `engine/capital_structure` has 0 BABA rows. No owner carries the ADS ratio or its changes.

### sessions_calendar (the only ready M0 family)
- `lib/hk_calendar.py` carries HKEX full-day closures and announced half days. Its daily-bar data expectation is 17:30 HKT for a regular session; half days finish CAS by 12:10, with a 13:30 HKT expectation.
- `lib/nyse_calendar.py` carries NYSE sessions.
- Both are rule arithmetic in house code (verified-internal).
- Neither carries intraday segments, trading halts or single-name suspensions.

### southbound_holdings
- **Owners:** `collectors/hk_southbound_holdings.py` and `engine/hk_southbound_stocks.py`, an Eastmoney mirror (UNVERIFIED).
- **Coverage:**
  - 9988: 290 rows, 2024-09-19 to 2026-10-09.
  - 700: 477 rows, 2024-07-10 to 2026-10-09.
  - The store gap audit counts 523 dates with 9 gaps.
- **Connect change roster** (`scripts/collect_hk_connect_roster.py`, `data/hk_connect_roster/roster.parquet`, 796 change rows):
  - It records the 9988 add, announced 2024-09-09 and effective 2024-09-10.
  - It has no 700, 89988 or 80700 row. A missing change row is not an eligibility verdict.
- **RMB counters:** 0 holdings rows (UNRESOLVED). BABA is a typed absence (`applicable: false`).
- **First-party CCASS** is BLOCKED-licence (08-28 matrix).

### short_positions
- **Owner:** `collectors/hk_shorts.py` (SFC aggregated reportable short positions, weekly), the admitted Data OS HK evidence (verified-internal).
- **Coverage:**
  - 9988: 357 rows, 2019-11-29 to 2026-10-02.
  - 700: 735 rows, 2012-08-31 to 2026-10-02.
  - 89988 and 80700: 172 rows each, from 2023-06-23.
- The RMB-counter rows have no `security_id` to join on, and `value_hkd` is HKD even for the RMB counter.
- BABA: 0 rows in the FINRA short-interest and short-volume stores (UNRESOLVED).

### fx
- **USD/HKD.** Owner `collectors/hk_prices.py` (yfinance `HKD=X`, HKD per USD).
  - `data/hk/HKD_X.parquet`: 6,418 rows, 2001-07-16 to 2026-10-10.
  - Read by `engine/hk_inputs.py` as `usdhkd`.
- **USD/CNY.** FRED DEXCHUS (`collectors/fred.py`), 1981-01-02 to 2026-10-02, NY noon.
  - yfinance `CNY=X` (`collectors/china_prices.py`) runs 2001-06-25 to 2026-10-10.
- **Offshore CNH.**
  - A `USDCNH` snapshot sits in `data/forex/latest.json`.
  - `CNH=F` (`collectors/china_prices.py`, `data/china/CNH_F.parquet`, 3,368 rows, 2013-02-11 to 2026-10-09) is a CME futures contract, not spot CNH.
  - No spot-CNH history and no CNH/HKD cross exist.
- **Status:** every FX leg is partial with UNVERIFIED rights, and no admitted Data OS FX owner exists.
- A fixed peg constant must never stand in for the observed USD/HKD series. Onshore CNY must never be substituted silently for CNH.

### adr_h_basis
- **Alibaba.** `engine/hk_adr_bridge.py` pairs BABA→9988.HK (pair kind `direct`) for display.
  - No basis series exists.
  - The basis is not reproducible because no owner carries the ADS-to-share ratio. USD/HKD is carried, with rights UNVERIFIED.
- **Tencent.** The bridge pairs 0700.HK→KWEB (pair kind `proxy`).
  - **KWEB is an ETF and is never a Tencent quote.**
  - `data/yahoo/TCEHY.parquet` (4,216 rows) exists but is not an admitted security, so the cell is UNRESOLVED.

### options
- **BABA.** `engine/options_skew.py` and `collectors/thetadata.py` hold 44 skew snapshots, 2026-06-22 to 2026-08-21. They are STALE (the last snapshot is about seven weeks before as_of), and the ThetaData EOD store has `n_roots` 0.
- **HK stock options**, every counter: no owner (BLOCKED-procurement). HKEX Historical Full Book (SOM) is the 08-28 preferred candidate.

### Benchmarks for residual windows (context for M0; not a profile family)

| benchmark | owner | store | span | basis note |
|---|---|---|---|---|
| Hang Seng Index | `collectors/hk_prices.py` (yfinance `^HSI`) | `data/hk/_HSI.parquet` | 9,816 rows, 1986-12-31..2026-10-09 | price index |
| Hang Seng TECH | `collectors/hk_indices.py` (akshare) | `data/hk/HSTECH.parquet` | 1,511 OHLCV rows, 2020-08-17..2026-10-09 | price index |
| Tracker Fund 2800.HK | `collectors/hk_prices.py` | `data/hk/2800.HK.parquet` | 4,625 rows, 2008-01-02..2026-10-09 | yfinance `auto_adjust=True` |
| CSOP HS TECH ETF 3033.HK | `collectors/hk_prices.py` | `data/hk/3033.HK.parquet` | 1,503 rows, 2020-08-27..2026-10-09 | yfinance `auto_adjust=True` |
| S&P 500 ETF (BABA side) | `collectors/yahoo.py` | `data/yahoo/SPY.parquet` | 8,482 rows, 1993-01-29..2026-10-09 | `close` TR, `close_price` dividend-unadjusted |

All benchmark rights are UNVERIFIED.

**Basis mismatch.** A residual between a total-return stock (`hk_stocks`) and a price index (HSI, HSTECH) drifts by the dividend on every ex-date. A residual window must pair like bases: the TR stock against a TR ETF from the same adjustment vintage, or price against price.

## 4. Response-window feasibility today

| window | 9988 HKD | 89988 RMB | BABA ADS | 700 HKD | 80700 RMB |
|---|---|---|---|---|---|
| daily close-to-close (research display) | possible; vintage unpinned; rights UNVERIFIED | no prices | possible; two bases present; rights UNVERIFIED | possible; vintage unpinned; rights UNVERIFIED | no prices |
| daily residual vs benchmark | possible with a like-basis benchmark (2800/3033) | no | possible vs SPY (same `close` basis) | possible with a like-basis benchmark (2800/3033) | no |
| intraday (minutes/hours around an announcement) | BLOCKED-procurement | BLOCKED-procurement | no owner | BLOCKED-procurement | BLOCKED-procurement |
| overnight US→HK ordering | ordering is a calendar fact; no basis series | no | same | proxy only (KWEB); TCEHY unadmitted | no |
| ADS↔H basis | not reproducible (no ADS ratio) | no | not reproducible | no same-issuer ADR admitted | no |
| flow context (Southbound, SFC shorts) | weekly shorts ready; Southbound partial | shorts rows, no security_id | n/a / no rows | weekly shorts ready; Southbound partial | shorts rows, no security_id |

"Possible" means computable from current owner bytes. It does not mean admitted, reproducible or graded.

## 5. Temporal law applied to market inputs (masterplan §5.3)

1. **Prices carry no `first_public` field.**
   - A daily bar's event time is the session date. Its observation time is the collector run.
   - For HK, the bar is expected no earlier than 17:30 HKT on a regular day and 13:30 HKT on a half day (`lib/hk_calendar.py`).
2. **Announcement-to-session mapping.**
   - HKEXnews stamps in the store include post-close times (16:31, 17:30, 18:06 HKT) and pre-open times (06:04 HKT).
   - An announcement after the session's close maps to the next HK session. One before the open maps to that day's session.
   - Midday-break announcements need intraday data and are out of reach today.
3. **Cross-market ordering.** The NYSE close for date D precedes the HK open for the next HK session. That ordering is a calendar fact, not a lead-lag claim.
4. **SFC short positions.** The `date` field is the reporting-position date. Publication comes later and is not carried as a field, so consumers must apply the publication lag explicitly before treating a row as known.
5. **Southbound holdings.** `date` is the holding date (T). The daily snapshot run is the observation time. A backfilled row is a reconstruction, not a point-in-time observation.
6. **Adjustment vintage.** An adjusted close is known only as of the run that wrote it. A frozen window must name the vintage (run date or content hash), or it can drift between runs.
7. **FX.** DEXCHUS is NY noon. The yfinance `HKD=X` and `CNH=F` bar conventions are undeclared. An FX-converted window must name which leg and clock it used.
8. **No hindsight.** Current facts (for example today's Connect eligibility or today's ADS ratio) must never be used as historical point-in-time inputs.

## 6. What a reproducible admitted M0 input contract would require

Each item names an existing owner. None proposes a new SNI market-data store.

1. **Adjustment-vintage pin.** Owners: `collectors/hk_stock_prices.py` and `lib/store.py`. Carry the raw (or dividend-unadjusted) close plus factors, or freeze adjusted series by content hash and run date. BABA already carries two bases through `collectors/yahoo.py`.
2. **RMB-counter securities and prices.**
   - The Data OS CN/HK admission plus a counter seam must mint `security_id`s (the E0 record, gap 2).
   - A price owner (an `hk_stock_prices` child) must then carry 89988 and 80700.
3. **ADS ratio.** It needs a carried, dated field. The Data OS security master and `engine/hk_adr_bridge.py` are the candidate owners.
4. **FX admission.**
   - A Data OS-admitted USD/HKD leg with a rights record.
   - A spot-CNH leg distinct from onshore CNY and from `CNH=F`.
5. **Per-row clocks.** `owner_observation` and, where meaningful, `first_public` on prices, shorts and holdings, so that §5 can be applied mechanically.
6. **Rights adjudication** for yfinance, akshare, Eastmoney, FRED and ThetaData by the source-rights authority. This record accepts nothing.
7. **Benchmark declaration** per window: like-basis pairing and the same vintage.
8. **Procurement**, out of scope here: HK intraday and HK stock options, for S0's response-window and options families only.

## 7. Gaps (each names its closing owner)

1. **Adjustment vintage unpinned.** Owners: `collectors/hk_stock_prices.py` and `lib/store.py`.
2. **RMB-counter prices absent.** Owner: an `hk_stock_prices` child, after the Data OS counter `security_id` exists.
3. **ADS ratio uncarried.** Owners: the Data OS security master and `engine/hk_adr_bridge.py`.
4. **FX and price rights UNVERIFIED.** Owner: the source-rights authority.
5. **Spot CNH absent** (futures proxy only). Owner: `collectors/china_prices.py` or the forex desk (`scripts/build_forex.py`).
6. **BABA options stale since 2026-08-21.** Owners: `engine/options_skew.py` and `collectors/thetadata.py`.
7. **HK intraday and HK options.** BLOCKED-procurement (HKEX products); out of scope.
8. **Placement category filter misses general-mandate placings.** Owner: `collectors/hk_placements.py`.
9. **No halt or suspension calendar.** Owner: `lib/hk_calendar.py`.
