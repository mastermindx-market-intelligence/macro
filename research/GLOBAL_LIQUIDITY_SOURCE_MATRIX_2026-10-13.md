# Global Liquidity Source Matrix — 2026-10-13

**Programme:** WS:GLOBAL-LIQUIDITY-TRANSMISSION — task T03 (lane B1, research/draft leaf)
**Extends:** the 2026-08-22 census (S08), `research/GLOBAL_LIQUIDITY_DATA_CENSUS_2026-08-22.md`
**Machine-readable companion:** `config/global_liquidity_sources_v2.yml` (namespace `global_liquidity_sources_v2`)
**Measured at:** repo sha `f2a21e8d7f28` (2026-10-13), seat probe `git show <sha>:<path>` read into pandas

## 1 Purpose and claim level

This is a per-use source qualification matrix for every global-liquidity source
family the repository actually holds. It answers, separately for each of four
uses — `display`, `reconstructed_research`, `vintage_qualified_research`,
`prospective_eligibility` — whether a source is eligible, conditional (with the
condition), or excluded (with the reason).

- **Claim level: `source_qualification_display_tier`. `validated: false`.** This
  document qualifies sources; it does not validate a factor, signal or trade.
- **Measured truth:** every coverage range and row count below was measured by
  the seat at sha `f2a21e8d7f28` and copied exactly. Nothing is extrapolated.
  Where a fact is unknown the matrix says `unknown` and why.
- **Cites, never copies:** no data values, histories or series observations are
  reproduced here — only coverage metadata (dates, row counts, column names) and
  clock/licence qualifications.
- The v1 producer manifest (S11) is untouched; v2 is a new namespace
  (`supersedes: none`).

## 2 Law

The following laws bind every consumer of this matrix and are stated verbatim in
the machine-readable companion as well.

- **C04:** economic period, publication (release), first-system-known (evidence
  available), vintage, correction and decision clocks are distinct and never
  substituted.
- **C05:** `central_bank_assets`, `reserves`, `broad_money`, `private_credit`,
  `funding_price` and `market_liquidity` are DIFFERENT concepts; never summed,
  averaged or substituted across concepts.
- **C06:** `credit_impulse_global` stays NULL with status
  `insufficient_comparable_pit_coverage` and the exact reason: no in-repo BIS
  GLI / external-credit store (S27); China TSF is a flow aggregate in CNY with
  conservative availability; US C&I is a bank-loan stock with first-print-only
  vintages; their definitions, units, sectors and clocks are not comparable, so
  no global scalar is computable. Also `broad_money_global` null: only US M2
  (M2SL) is level-available; China M2 is yoy-only; EZ/JP/KR/GB M2 are absent.
- **FORBIDDEN POOL:** `china_tsf`, `us_ci_loans`, `bis_gli_external_credit` may
  never be pooled/summed/averaged into one credit measure.
- **Derived identity law:** `fed_net_liquidity` (formula owner:
  `engine.canon.load_net_liquidity_components`, stated once there and not
  restated here) omits other non-reserve liabilities and capital, so it is
  never reserves.

## 3 Matrix

Verdict vocabulary per use: **eligible** | **cond** (conditional — condition
stated) | **excl** (excluded — reason stated). Coverage dates/rows are measured
metadata, not data values.

| id | series | concept | clocks (econ / release / first-known) | vintage & correction | licence | coverage (start..end, rows) | in-repo path | display | reconstructed | vintage-qualified | prospective | exclusion |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| fed_total_assets | FRED WALCL (H.4.1 total assets) | central_bank_assets | Wednesday level / H.4.1 Thu ~16:30 ET (Wed+1BD) / unknown per-row → release+1BD | none in repo (latest-only mirror; revisions rare); corrections unobserved | public US government | 2002-12-18..2026-10-07, 1243 | `data/fred/WALCL.parquet` (`fed_balance_sheet`) | eligible | cond: release_lag_aligned (Wed+1BD), non-revised assumption stated | excl: no archive | cond: forward-only once a receipt-stamped producer exists | — |
| fed_reserve_balances | FRED WRESBAL | reserves | week AVERAGE ending Wednesday / H.4.1 Thu ~16:30 ET / unknown per-row → release+1BD | none in repo; corrections unobserved | public US government | 2002-12-18..2026-10-07, 1243 | `data/fred/WRESBAL.parquet` (`reserve_balances`) | eligible | cond: Wed+1BD, non-revised stated; LAW — week average, never one identity with WALCL's Wednesday level | excl: no archive | cond: receipt-stamped producer | — |
| fed_rrp | FRED RRPONTSYD + `data/nyfed/rrp` | reserves (non-reserve-liability identity component) | operation day D / NY Fed same day ~13:15 ET / unknown per-row (same-day) | none in repo | public US government (NY Fed) | 2003-02-07..2026-10-08, 3343; nyfed store 2013-04-02..2026-10-08, 3267 | `data/fred/RRPONTSYD.parquet` (`on_rrp`) | eligible | eligible: same-day | excl: no archive | cond: receipt-stamped producer | — |
| fed_tga | Treasury DTS TGA | reserves (non-reserve-liability identity component) | day D / D+1BD ~16:00 ET (S29) / unknown per-row → release | none in repo | public US government (Treasury) | 2005-10-03..2026-10-07, 5143 | `data/treasury/tga.parquet` (`tga_mn`) | eligible | eligible: D+1BD lag | excl: no archive | cond: receipt-stamped producer | — |
| fed_net_liquidity | derived WALCL−RRP−TGA (formula owner `engine.canon.load_net_liquidity_components`; not restated) | central_bank_assets (derived proxy: never reserves, never a total-asset level) | inherits components / max of component releases / max of component first-known | derived, recomputed; no independent vintage | derived | 2002-12-18..2026-10-08, 5445 (cols `walcl_bn`,`rrp_bn`,`tga_bn`,`netliq_bn`) | `data/macro/fed_net_liquidity.parquet` (`netliq_bn`) | cond: must be labelled "incomplete proxy" — omits other non-reserve liabilities and capital (S28) | cond: inherited clocks + proxy disclosure | excl: derived | cond: once every component carries receipts | — |
| fed_other_nonreserve_liabilities_and_capital | absent | reserves identity component | — | — | — | — | absent | excl: absent | excl | excl | excl | absent → R = A − N is not computable in-repo (S28) |
| ecb_total_assets | FRED ECBASSETSW (ECB weekly statement) | central_bank_assets | Friday reference / following Tuesday (~+2BD) / unknown per-row → release | none in repo; revision path unknown (medium) | public with attribution (ECB) | 1999-01-01..2026-09-25, 1448 | `data/fred/ECBASSETSW.parquet` (`ecb_assets`) | eligible | cond: +2BD, revision unknown; USD translation needs EURUSD, whose in-repo Yahoo store is licensed-no-redistribution | excl: no archive | cond: receipt-stamped producer | — |
| boj_total_assets | FRED JPNASSETS (BoJ accounts) | central_bank_assets | MONTH-END (store labels month-START; DSC:BOJ-ASSETS-REQUIRE-MONTH-END-ANCHOR) / ~+2BD after month end / unknown per-row → release | none in repo; revision path unknown (medium) | public with attribution (BoJ) | 1998-04-01..2026-09-01, 342 | `data/fred/JPNASSETS.parquet` (`boj_assets`) | cond: month-end anchor | cond: month-end anchor + ~2BD, revision unknown | excl: no archive | cond: receipt-stamped producer | — |
| pboc_balance_sheet | absent | central_bank_assets | — | — | — | — | absent | excl: absent | excl | excl | excl | absent; `data/china_pboc/fx_reserves.parquet` (225 rows, 2008-01-01..2026-09-01, cols `fx_reserves`,`gold_reserves`) and `data/china_omo/operations.parquet` (112 operation bulletins, no date index) are CONTEXT ONLY, never PBoC total assets |
| china_tsf | PBoC TSF (owner `collectors/china_credit.py`) | private_credit | month M / mid M+1, irregular / explicit conservative availability = day 16 of M+1 | none; later revisions not captured | public (PBoC) — terms per owner | 2015-01-01..2026-08-01, 140 (cols `tsf_total`,`rmb_loans`,…) | `data/china_credit/tsf.parquet` (`tsf_total`) | eligible | cond: explicit_conservative_availability (day 16 of M+1) | excl: no archive | cond: receipt-stamped producer | — · FORBIDDEN POOL member |
| us_ci_loans | FRED BUSLOANS (H.8) | private_credit | month / H.8 Friday ~16:15 ET, monthly revised / first print archived | FIRST-PRINT archive: 357 periods 1996-12..2026-08; later revisions not archived | public US government | 1947-01-01..2026-08-01, 956 | `data/fred/BUSLOANS.parquet` (`ci_loans`) | eligible | cond: revised after first print, release alignment stated | eligible: first print only | cond: receipt-stamped producer | — · FORBIDDEN POOL member |
| bis_gli_external_credit | absent | private_credit (cross-border/external) | quarterly with long lag (S27) | — | BIS terms | — | absent | excl: absent | excl | excl | excl | absent: no in-repo BIS GLI / external-credit store (S27) · FORBIDDEN POOL member · in-repo BIS `us_gap` (274 rows, 1957-12-31..2026-03-31) / DSR are STRUCTURAL credit-to-GDP measures, excluded from transmission use (not GLI) |
| us_m2 | FRED M2SL (H.6) | broad_money | month / H.6 ~4th Tuesday M+1, revised / first print archived | FIRST-PRINT archive: 357 periods 1996-12..2026-08; later revisions not archived | public US government | 1959-01-01..2026-08-01, 812 | `data/fred/M2SL.parquet` (`us_m2`) | eligible | cond: revised monthly, release alignment stated | eligible: first print only | cond: receipt-stamped producer | — |
| china_m2 | `data/china_macro/money_supply` (EastMoney aggregation) | broad_money | month / unknown — not stored / unknown — no release timestamp (S08) | none; revision risk unbounded | unknown — terms per owner | 2008-01-01..2026-08-01, 224 (cols `m2_yoy`,`m1_yoy`,`m0_yoy`) | `data/china_macro/money_supply.parquet` (`m2_yoy`) | cond: yoy-only context, never shown as a level | excl: yoy-only, not a level | excl: no archive | excl: no first-known clock to qualify | all research excluded: yoy-only, not a level, not PIT-safe |
| ez_jp_kr_gb_m2 | absent | broad_money | — | — | — | — | absent | excl: absent | excl | excl | excl | absent; legacy discontinued FRED feeds explicitly removed in v1, do not revive (S08) |
| us_funding_rates | FRED SOFR, EFFR, DFF, IORB | funding_price | SOFR/EFFR day D; DFF daily incl. weekends; IORB administered effective date / SOFR ~08:00, EFFR ~09:00 ET D+1BD (NY Fed) / unknown per-row → release | none; SOFR and IORB not in the vintage archive | public US government (NY Fed / Board) | SOFR 2018-04-03..2026-10-07, 2127; EFFR 2000-07-03..2026-10-07, 6595; DFF 1954-07-01..2026-10-07, 26397; IORB 2021-07-29..2026-10-09, 1899 | `data/fred/SOFR.parquet`, `EFFR.parquet`, `DFF.parquet`, `IORB.parquet` | eligible | eligible: D+1BD | excl: no archive | cond: receipt-stamped producer | — · spreads (SOFR−IORB, EFFR−IORB) only on common dates, from 2021-07-29 (IORB start) |
| market_liquidity_proxies | FRED DTWEXBGS (H.10), DFII10, BAMLH0A0HYM2 | market_liquidity | DTWEXBGS weekly H.10 (Monday); DFII10 daily; HY OAS daily / ~+1BD / unknown per-row → release | none; HY OAS pre-window history only in the append-only repo store (upstream rolling window) | DTWEXBGS/DFII10 public US government; BAMLH0A0HYM2 = ICE BofA, licensed_no_redistribution (custody gap: derived-display licence not verified in repo) | DTWEXBGS 2006-01-02..2026-10-02, 5203; DFII10 2003-01-02..2026-10-07, 5946; HY OAS 1996-12-31..2026-10-07, 7774 | `data/fred/DTWEXBGS.parquet`, `DFII10.parquet`, `BAMLH0A0HYM2.parquet` | cond: HY OAS licence gap | cond: +1BD, HY custody gap | excl: no archive | cond: receipt-stamped producer + licence gap closed | — |
| nfci_anfci | FRED NFCI, ANFCI | market_liquidity (composite) | week / weekly; ENTIRE history re-estimated each release / unknown per-row | none; whole-history revision | public US government | 1971-01-08..2026-10-02, 2909 (pair, as measured) | `data/fred/NFCI.parquet`, `ANFCI.parquet` | eligible | excl: whole-history revision, not PIT | excl: not in vintage archive | excl: not curable by receipts alone | all research excluded: whole-history revision, not point-in-time (S08; `collectors/fred.py` defers the family from the vintage matrix for the same reason) |
| hkma_shibor_context | `data/hkma/interbank_liquidity` + `data/china_funding/shibor` | funding_price (jurisdiction) | daily / daily fixing-publication / unknown per-row | none; typically non-revised fixings | HKMA / shibor.org terms | hkma 2002-01-02..2026-10-09, 6345 (cols `agg_balance`,`hibor_on`,…); shibor 2015-05-08..2026-10-12, 2381 | `data/hkma/interbank_liquidity.parquet`, `data/china_funding/shibor.parquet` | eligible: jurisdiction context | excl: jurisdiction context only | excl: no archive | excl: out of scope for the global measure | research excluded from the global measure: jurisdiction context only (S08) |
| cross_currency_basis | absent | funding_price | — | — | — | — | absent | excl: absent | excl | excl | excl | absent: no in-repo cross-currency basis store; CNH futures/spot basis, HIBOR−SOFR and HKMA aggregate balance are local diagnostics, never renamed into a covered global basis basket (S08) |

**Vintage archive note (measured).** `data/fred_vintage/vintages.parquet` holds
rows=16518 with ONE row per (series, period) = FIRST PRINT ONLY (0 duplicate
periods). Liquidity-relevant series present: BUSLOANS (357 periods,
1996-12..2026-08) and M2SL (357 periods, 1996-12..2026-08). WALCL, WRESBAL,
ECBASSETSW, JPNASSETS, SOFR and IORB are NOT in the vintage archive. The
archive therefore supports first-print research only, never revision-path
research (S30 documents FRED's realtime-period semantics this store does not
reproduce).

## 4 Corrections to the 2026-08-22 census

a) **BIS us_gap coverage end:** now runs to 2026Q1 (2026-03-31); the census
   said 2025Q4.
b) **FRED vintage archive capability:** it is FIRST-PRINT-ONLY (one row per
   series-period); it supports first-print research for BUSLOANS and M2SL, not
   revision-path research, and covers no balance-sheet series.
c) **WRESBAL vs WALCL:** WRESBAL is a week average while WALCL is a Wednesday
   level; they are not one identity.
d) **v1 FX conflation:** v1 converts ECB/BoJ assets to USD at the
   reference-date FX before differencing, so a USD change mixes quantity and FX
   translation; T04's exact decomposition
   `dV = q_prev*dL + L_prev*dq + dL*dq` is the correction (cite C07).
e) **Coverage end dates** refreshed to measured_at_sha `f2a21e8d7f28`
   (2026-10-13) throughout section 3.
f) **ICE BofA HY OAS licence** is a custody gap: no in-repo record verifies
   redistribution or derived-display terms for `BAMLH0A0HYM2` (ICE BofA data
   served via FRED; `collectors/fred.py` documents only its rolling-window
   history caveat).
g) **Legacy international M2 stores:** the census listed
   `data/fred/{EZ,JP,KR,GB}_m2.parquet` as discontinued feeds; none is tracked
   at origin/main `f30746d115ff` (`git ls-tree origin/main data/fred/`), so the
   `ez_jp_kr_gb_m2` row is `absent`, not merely stale.

## 5 Gaps

Absent stores (no in-repo data; prospective work would need new collectors,
which are out of scope for T03):

- full H.4.1 liabilities, including other non-reserve liabilities and capital
  (so reserves R = A − N are not computable in-repo, S28);
- PBoC balance sheet (total assets) — fx_reserves and OMO bulletins are
  context only;
- BIS global liquidity indicators / external credit (S27);
- cross-currency basis;
- EZ/JP/KR/GB M2 (legacy discontinued feeds must not be revived);
- native ECB/BoJ stores — only the FRED mirrors above exist in-repo.

Licence / custody gaps:

- ICE BofA HY OAS (`BAMLH0A0HYM2`) is licensed_no_redistribution and the
  licence for derived display is not verified in repo (correction f);
- the in-repo Yahoo EURUSD store is licensed_no_redistribution, so any USD
  translation of ECB assets inherits that custody restriction;
- PBoC TSF, HKMA and shibor.org terms are carried per owner
  (`terms_unverified`).

Clock gaps: no collector keeps a per-row first-known receipt; first-known
clocks are reconstructions from release schedules except where an explicit
availability stamp (TSF) or first-print archive row (BUSLOANS, M2SL) exists.

## 6 Sources cited

- S08 — `research/GLOBAL_LIQUIDITY_DATA_CENSUS_2026-08-22.md` (repo)
- S11 — `config/global_liquidity_transmission_v1.yml` (repo)
- S27 — https://www.bis.org/statistics
- S28 — https://www.federalreserve.gov/monetarypolicy/bst_frliabilities.htm
- S29 — https://home.treasury.gov/data/receipts-outlays
- S30 — https://fred.stlouisfed.org/docs/api/fred/realtime_period.html
- FRED series pages: https://fred.stlouisfed.org/series/WALCL ,
  /series/WRESBAL , /series/RRPONTSYD , /series/ECBASSETSW ,
  /series/JPNASSETS , /series/BUSLOANS , /series/M2SL , /series/SOFR ,
  /series/EFFR , /series/DFF , /series/IORB , /series/DTWEXBGS ,
  /series/DFII10 , /series/BAMLH0A0HYM2 , /series/NFCI , /series/ANFCI

No other URLs are cited. Repo citations in text (`engine/canon.py`,
`collectors/china_credit.py`, `collectors/fred.py`, `data/*` paths) are
in-repo pointers, not external sources.
