# Regime inputs — equity-internal series (COO ruling 36 §2)

A **series build, not a regime call**. It produces the equity-internal inputs a
regime model may later read: equal-weight versus cap-weight, universe breadth,
dispersion, leadership concentration, and relative price indices. Per ruling 36 the
regime definition itself (categories, transitions, any outcome relation) is Prophet's
work, not this file's. Nothing here assigns a regime category, cutoff, score, signal
or rank-based call, and nothing relates any series to outcomes, hit rates or backtests
on any period. Standing sidecar sentence: **series only: no outcome relation, no regime assignment, no trading call of any kind, on any period**.

Everything is group-level or universe-level. No member ticker, member row or member
price appears in any committed file. The Tiingo archive is not used at all.

## Basis, start and conventions

- **Basis**: `reconstructed_current_membership` — today's members applied to the past; not point-in-time; survivors only
- **Universe**: today's S&P 500, 503 names in 11 GICS sectors (`data/breadth/constituents.parquet`); today's classifications, same family `sector` basis as `scripts/build_tree_breadth_and_index.py`.
- **Start**: 2000-01-01. Rule (same sentence as the tree build): first January 1 from which every later calendar year has name-week above-200 flag disagreement against the Tiingo archive of 0.5% or less (S&P 500 members priced in both, weeks where both hold 200 sessions) Note: 200-session averages use the full download, so the first weeks after the start read flags from late in the prior year
- **Floors**: index 2 priced members; every share and statistic 2 counted members. `n` sits beside every value; a session with no valid value carries no row.
- **Equal-weight levels**: engine.baskets._ew_level: each session the index return is the plain mean of the daily total returns of the members priced that session (daily rebalance to equal weight), chained from 1.0 on the group's first valid session Total return (auto_adjust closes).
- **Member prices**: single-vintage yfinance auto_adjust download held off git. Vintage `2026-11-12T07:33:42.601690+00:00`; data end 2026-11-11. Top-up: 4 names, vintage `2026-11-12T09:39:20Z`, one call per ticker; each name's full history is from a single download.
- **ETF legs**: `data/yahoo/<T>.parquet` on origin/main, column `close`. First dates: SPY 1993-01-29, RSP 2003-05-01, SPHB 2011-05-05, IGV 2001-07-17, SOXX 2001-07-13.
- **Ratios**: every ratio is rebased to 100 at the first session both legs are valid. **Dispersion units**: percent (a 0.01 return reads 1.0); ddof=1.

## Series

38 daily series, long format `date, series, group, value, n, kind` with `kind ∈ house | etf | computed`. Gaps are abbreviated here; the sidecar carries the full sentences.

| series | one-line definition | first date | source | known gaps |
|---|---|---|---|---|
| `ew_index` | equal-weight total-return index level of the group, chained from 1.0 (daily rebalance) | 2000-01-03 | house member closes via engine.baskets._ew_level | survivors only |
| `ew_vs_spy` | EW universe index divided by SPY close, rebased to 100 at the first common session | 2000-01-03 | house EW index; SPY close on main | dividend method differs |
| `rsp_vs_spy` | RSP close divided by SPY close, rebased to 100 at the first common session | 2003-05-01 | RSP and SPY close on main | RSP starts 2003-05-01; dividend method differs |
| `pct_above_50` | percent of counted universe members strictly above their own 50-session simple moving average | 2000-01-03 | house member closes via engine.group_breadth_history.member_flags | counted set varies |
| `n_above_50` | count of universe members strictly above their own 50-session SMA (n = counted members) | 2000-01-03 | house member closes via engine.group_breadth_history.member_flags | counted set varies |
| `diff_pct_above_50_21d` | plain difference (points) of the percent-above-50 share, session t minus t-21 | 2000-01-03 | house member closes via engine.group_breadth_history.level_change | counted set varies |
| `diff_pct_above_50_63d` | plain difference (points) of the percent-above-50 share, session t minus t-63 | 2000-01-03 | house member closes via engine.group_breadth_history.level_change | counted set varies |
| `pct_above_200` | percent of counted universe members strictly above their own 200-session simple moving average | 2000-01-03 | house member closes via engine.group_breadth_history.member_flags | counted set varies |
| `n_above_200` | count of universe members strictly above their own 200-session SMA (n = counted members) | 2000-01-03 | house member closes via engine.group_breadth_history.member_flags | counted set varies |
| `diff_pct_above_200_21d` | plain difference (points) of the percent-above-200 share, session t minus t-21 | 2000-01-03 | house member closes via engine.group_breadth_history.level_change | counted set varies |
| `diff_pct_above_200_63d` | plain difference (points) of the percent-above-200 share, session t minus t-63 | 2000-01-03 | house member closes via engine.group_breadth_history.level_change | counted set varies |
| `new_highs_252` | count of universe members whose close strictly exceeds the prior 252-session maximum (full window) | 2000-01-03 | house member closes; house high52w_new convention | full 252 window |
| `new_lows_252` | count of universe members whose close is strictly below the prior 252-session minimum (full window) | 2000-01-03 | house member closes; house low52w_new convention | full 252 window |
| `nh_nl_252` | new 252-session highs minus new lows (counts) | 2000-01-03 | house member closes; house high52w_new/low52w_new convention | full 252 window |
| `n_counted_nh` | universe members with a close and a full prior 252-session window on the session | 2000-01-03 | house member closes | full 252 window |
| `dispersion_21d` | cross-sectional standard deviation (ddof=1, percent) of member simple 21-session returns, universe and per sector | 2000-01-03 | house member closes | endpoint closes needed |
| `dispersion_63d` | cross-sectional standard deviation (ddof=1, percent) of member simple 63-session returns, universe and per sector | 2000-01-03 | house member closes | endpoint closes needed |
| `sector_dispersion_21d` | standard deviation (ddof=1, percent) across the 11 sector EW index simple 21-session returns (n = sectors with a valid return) | 2000-02-02 | house sector EW levels | survivors only |
| `sector_dispersion_63d` | standard deviation (ddof=1, percent) across the 11 sector EW index simple 63-session returns (n = sectors with a valid return) | 2000-04-03 | house sector EW levels | survivors only |
| `pct_beat_ew_63d` | percent of counted members whose simple 63-session return strictly exceeds the EW universe index's over the same window | 2000-04-03 | house member closes and EW universe index | survivors only |
| `n_beat_ew_63d` | count of members beating the EW universe index over 63 sessions (n = counted members) | 2000-04-03 | house member closes and EW universe index | survivors only |
| `pct_beat_ew_126d` | percent of counted members whose simple 126-session return strictly exceeds the EW universe index's over the same window | 2000-07-03 | house member closes and EW universe index | survivors only |
| `n_beat_ew_126d` | count of members beating the EW universe index over 126 sessions (n = counted members) | 2000-07-03 | house member closes and EW universe index | survivors only |
| `rel_ai_software_vs_ew_universe` | ai_software basket EW index divided by the EW universe index, rebased to 100 at the first common session | 2000-01-03 | house EW levels | survivors only |
| `rel_ai_software_vs_ai_semiconductors` | ai_software basket EW index divided by the ai_semiconductors basket EW index, rebased to 100 at the first common session | 2000-01-03 | house EW levels | survivors only |
| `rel_ai_software_vs_soxx` | ai_software basket EW index divided by SOXX close, rebased to 100 at the first common session | 2001-07-13 | house EW levels and ETF close on main | survivors only; dividend method differs; SOXX starts 2001-07-13 |
| `rel_non_ai_software_vs_ew_universe` | non_ai_software basket EW index divided by the EW universe index, rebased to 100 at the first common session | 2000-01-03 | house EW levels | survivors only |
| `rel_non_ai_software_vs_ai_semiconductors` | non_ai_software basket EW index divided by the ai_semiconductors basket EW index, rebased to 100 at the first common session | 2000-01-03 | house EW levels | survivors only |
| `rel_non_ai_software_vs_soxx` | non_ai_software basket EW index divided by SOXX close, rebased to 100 at the first common session | 2001-07-13 | house EW levels and ETF close on main | survivors only; dividend method differs; SOXX starts 2001-07-13 |
| `rel_igv_vs_ew_universe` | IGV close divided by the EW universe index, rebased to 100 at the first common session | 2001-07-17 | house EW levels and ETF close on main | dividend method differs; IGV starts 2001-07-17 |
| `rel_igv_vs_ai_semiconductors` | IGV close divided by the ai_semiconductors basket EW index, rebased to 100 at the first common session | 2001-07-17 | house EW levels and ETF close on main | dividend method differs; IGV starts 2001-07-17 |
| `rel_igv_vs_soxx` | IGV close divided by SOXX close, rebased to 100 at the first common session | 2001-07-17 | ETF close on main | dividend method differs; IGV starts 2001-07-17; SOXX starts 2001-07-13 |
| `rel_high_beta_computed_vs_ew_universe` | computed high-beta EW index divided by the EW universe index, rebased to 100 at the first common session | 2000-01-03 | house EW levels | computed, not curated |
| `rel_high_beta_computed_vs_ai_semiconductors` | computed high-beta EW index divided by the ai_semiconductors basket EW index, rebased to 100 at the first common session | 2000-01-03 | house EW levels | computed, not curated |
| `rel_high_beta_computed_vs_soxx` | computed high-beta EW index divided by SOXX close, rebased to 100 at the first common session | 2001-07-13 | house EW levels and ETF close on main | computed, not curated; dividend method differs; SOXX starts 2001-07-13 |
| `rel_sphb_vs_ew_universe` | SPHB close divided by the EW universe index, rebased to 100 at the first common session | 2011-05-05 | house EW levels and ETF close on main | dividend method differs; SPHB starts 2011-05-05 |
| `rel_sphb_vs_ai_semiconductors` | SPHB close divided by the ai_semiconductors basket EW index, rebased to 100 at the first common session | 2011-05-05 | house EW levels and ETF close on main | dividend method differs; SPHB starts 2011-05-05 |
| `rel_sphb_vs_soxx` | SPHB close divided by SOXX close, rebased to 100 at the first common session | 2011-05-05 | ETF close on main | dividend method differs; SPHB starts 2011-05-05; SOXX starts 2001-07-13 |

**Computed high-beta group.** top fifth of universe members by trailing 252-session beta to SPY daily returns (cov/var on 252 paired daily returns, full window required), ranked at each month's last session, held the next month; ties broken by ticker; equal-weight daily rebalance within the held month, same _ew_level chaining from 1.0 First selection 1994-01-31; 395 monthly selections; cohort size 52–100 (last held cohort 100).

**Self-check.** Recomputed sector and basket EW levels match the committed `house_ew_index_daily_current.parquet` on 94,584 shared rows; max absolute level difference 5.00e-07 (the house file rounds to 6 decimals), on the same download vintage.

**House history.** no universe group exists in any house history file; every universe breadth series here is new data/breadth/breadth.parquet (the live nightly collector surface) does carry universe pct_above_50/200 and nh/nl, but on collector-cache prices, not the house download; it is not history and is not mixed into this house-basis file
**Historical index weights.** no: constituents files hold today's members only (name, sector), desk_weights/shadow.json is desk allocation, rate_futures constituents are futures contracts, cpi_relative_importance is CPI weights Decision: count-based leadership only; the weight-based top-10 measure is skipped
**Rates, credit, dollar.** No build here — census only, below.

## Rates, credit and dollar on main (census, no build)

Ref `origin/main`. parquet series under data/fred, fred_vintage, ofr_fsi, treasury, treasury_auctions, corp_bonds, canada_macro, china_macro, china_credit, china_yield, china_pboc, intl_macro, plus fed_net_liquidity, macro_snapshots/ledger, cot_dollar and the yahoo dollar indices; latest-value JSON surfaces listed separately
Excluded as not rates/credit/dollar source series: news/official/news caches, fred_surprise_cache, experiments, quarantine (rejected vintages), cycle ontology/pattern samples, seasonality, oracle, price_pressure, quality, research artifacts, release_forecast: not rates/credit/dollar source series

**650 parquet series.** List (path | series | first date):

### data/fred (207 series)

| path | series | first date |
|---|---|---|
| `data/fred/ADPMNUSNERSA.parquet` | ADPMNUSNERSA | 2010-01-01 |
| `data/fred/AMTMUO.parquet` | AMTMUO | 1992-01-01 |
| `data/fred/AMTMVS.parquet` | AMTMVS | 1992-01-01 |
| `data/fred/ANFCI.parquet` | ANFCI | 1971-01-08 |
| `data/fred/APU000072610.parquet` | APU000072610 | 1978-11-01 |
| `data/fred/AWHAETP.parquet` | AWHAETP | 2006-03-01 |
| `data/fred/AWHMAN.parquet` | AWHMAN | 1939-01-01 |
| `data/fred/BAMLC0A0CM.parquet` | BAMLC0A0CM | 2023-04-24 |
| `data/fred/BAMLC0A0CMEY.parquet` | BAMLC0A0CMEY | 2023-07-17 |
| `data/fred/BAMLC0A1CAAA.parquet` | BAMLC0A1CAAA | 2023-07-17 |
| `data/fred/BAMLC0A2CAA.parquet` | BAMLC0A2CAA | 2023-07-17 |
| `data/fred/BAMLC0A3CA.parquet` | BAMLC0A3CA | 2023-07-17 |
| `data/fred/BAMLC0A4CBBB.parquet` | BAMLC0A4CBBB | 2023-07-17 |
| `data/fred/BAMLCC0A0CMTRIV.parquet` | BAMLCC0A0CMTRIV | 2023-07-17 |
| `data/fred/BAMLEMCBPIOAS.parquet` | BAMLEMCBPIOAS | 2023-06-13 |
| `data/fred/BAMLEMEBCRPIEOAS.parquet` | BAMLEMEBCRPIEOAS | 2023-07-11 |
| `data/fred/BAMLEMFSFCRPIOAS.parquet` | BAMLEMFSFCRPIOAS | 2023-07-11 |
| `data/fred/BAMLEMHBHYCRPIOAS.parquet` | BAMLEMHBHYCRPIOAS | 2023-07-11 |
| `data/fred/BAMLEMNSNFCRPIOAS.parquet` | BAMLEMNSNFCRPIOAS | 2023-07-11 |
| `data/fred/BAMLEMRACRPIASIAOAS.parquet` | BAMLEMRACRPIASIAOAS | 2023-07-11 |
| `data/fred/BAMLEMRECRPIEMEAOAS.parquet` | BAMLEMRECRPIEMEAOAS | 2023-07-11 |
| `data/fred/BAMLEMRLCRPILAOAS.parquet` | BAMLEMRLCRPILAOAS | 2023-07-11 |
| `data/fred/BAMLH0A0HYM2.parquet` | BAMLH0A0HYM2 | 1996-12-31 |
| `data/fred/BAMLH0A0HYM2EY.parquet` | BAMLH0A0HYM2EY | 2023-07-17 |
| `data/fred/BAMLH0A1HYBB.parquet` | BAMLH0A1HYBB | 2023-07-17 |
| `data/fred/BAMLH0A2HYB.parquet` | BAMLH0A2HYB | 2023-07-17 |
| `data/fred/BAMLH0A3HYC.parquet` | BAMLH0A3HYC | 2023-06-13 |
| `data/fred/BAMLHE00EHYIOAS.parquet` | BAMLHE00EHYIOAS | 2023-07-11 |
| `data/fred/BAMLHYH0A0HYM2TRIV.parquet` | BAMLHYH0A0HYM2TRIV | 2023-06-19 |
| `data/fred/BOPGSTB.parquet` | BOPGSTB | 1992-01-01 |
| `data/fred/BOPTEXP.parquet` | BOPTEXP | 1992-01-01 |
| `data/fred/BOPTIMP.parquet` | BOPTIMP | 1992-01-01 |
| `data/fred/BUSLOANS.parquet` | BUSLOANS | 1947-01-01 |
| `data/fred/CAPG3344S.parquet` | CAPG3344S | 1972-01-01 |
| `data/fred/CAPUTLG211S.parquet` | CAPUTLG211S | 1972-01-01 |
| `data/fred/CAPUTLG2211A2S.parquet` | CAPUTLG2211A2S | 1967-01-01 |
| `data/fred/CAPUTLG2211S.parquet` | CAPUTLG2211S | 1967-01-01 |
| `data/fred/CAPUTLG331S.parquet` | CAPUTLG331S | 1967-01-01 |
| `data/fred/CAPUTLG3344S.parquet` | CAPUTLG3344S | 1972-01-01 |
| `data/fred/CAPUTLG334S.parquet` | CAPUTLG334S | 1972-01-01 |
| `data/fred/CCSA.parquet` | CCSA | 1967-01-07 |
| `data/fred/CES0500000003.parquet` | CES0500000003 | 2006-03-01 |
| `data/fred/CMRMTSPL.parquet` | CMRMTSPL | 1967-01-01 |
| `data/fred/CORESTICKM157SFRBATL.parquet` | CORESTICKM157SFRBATL | 1967-02-01 |
| `data/fred/CPIAUCSL.parquet` | CPIAUCSL | 1947-01-01 |
| `data/fred/CPILFESL.parquet` | CPILFESL | 1957-01-01 |
| `data/fred/CSUSHPISA.parquet` | CSUSHPISA | 1987-01-01 |
| `data/fred/CUSR0000SACL1E.parquet` | CUSR0000SACL1E | 1957-01-01 |
| `data/fred/CUSR0000SAF11.parquet` | CUSR0000SAF11 | 1952-01-01 |
| `data/fred/CUSR0000SAH1.parquet` | CUSR0000SAH1 | 1953-01-01 |
| `data/fred/CUSR0000SAS.parquet` | CUSR0000SAS | 1956-01-01 |
| `data/fred/CUSR0000SASLE.parquet` | CUSR0000SASLE | 1967-01-01 |
| `data/fred/CUUR0000SAG1.parquet` | CUUR0000SAG1 | 1947-01-01 |
| `data/fred/DAAA.parquet` | DAAA | 1983-01-03 |
| `data/fred/DBAA.parquet` | DBAA | 1986-01-02 |
| `data/fred/DCOILWTICO.parquet` | DCOILWTICO | 1986-01-02 |
| `data/fred/DEXBZUS.parquet` | DEXBZUS | 1995-01-02 |
| `data/fred/DEXCAUS.parquet` | DEXCAUS | 1971-01-04 |
| `data/fred/DEXCHUS.parquet` | DEXCHUS | 1981-01-02 |
| `data/fred/DEXJPUS.parquet` | DEXJPUS | 1971-01-04 |
| `data/fred/DEXMXUS.parquet` | DEXMXUS | 1993-11-08 |
| `data/fred/DEXSZUS.parquet` | DEXSZUS | 1971-01-04 |
| `data/fred/DEXUSAL.parquet` | DEXUSAL | 1971-01-04 |
| `data/fred/DEXUSEU.parquet` | DEXUSEU | 1999-01-04 |
| `data/fred/DEXUSUK.parquet` | DEXUSUK | 1971-01-04 |
| `data/fred/DFEDTARL.parquet` | DFEDTARL | 2008-12-16 |
| `data/fred/DFEDTARU.parquet` | DFEDTARU | 2008-12-16 |
| `data/fred/DFF.parquet` | DFF | 1954-07-01 |
| `data/fred/DFII10.parquet` | DFII10 | 2003-01-02 |
| `data/fred/DFII5.parquet` | DFII5 | 2003-01-02 |
| `data/fred/DGORDER.parquet` | DGORDER | 1992-02-01 |
| `data/fred/DGS1.parquet` | DGS1 | 1962-01-02 |
| `data/fred/DGS10.parquet` | DGS10 | 1962-01-02 |
| `data/fred/DGS2.parquet` | DGS2 | 1976-06-01 |
| `data/fred/DGS20.parquet` | DGS20 | 1962-01-02 |
| `data/fred/DGS3.parquet` | DGS3 | 1962-01-02 |
| `data/fred/DGS30.parquet` | DGS30 | 1977-02-15 |
| `data/fred/DGS3MO.parquet` | DGS3MO | 1981-09-01 |
| `data/fred/DGS5.parquet` | DGS5 | 1962-01-02 |
| `data/fred/DGS6MO.parquet` | DGS6MO | 1981-09-01 |
| `data/fred/DGS7.parquet` | DGS7 | 1969-07-01 |
| `data/fred/DHHNGSP.parquet` | DHHNGSP | 1997-01-07 |
| `data/fred/DRCCLACBS.parquet` | DRCCLACBS | 1991-01-01 |
| `data/fred/DRSFRMACBS.parquet` | DRSFRMACBS | 1991-01-01 |
| `data/fred/DSPIC96.parquet` | DSPIC96 | 1959-01-01 |
| `data/fred/DTB3.parquet` | DTB3 | 1954-01-04 |
| `data/fred/DTCISA156MSFRBPHI.parquet` | DTCISA156MSFRBPHI | 1968-05-01 |
| `data/fred/DTMUAMFRBDAL.parquet` | DTMUAMFRBDAL | 2004-06-01 |
| `data/fred/DTWEXAFEGS.parquet` | DTWEXAFEGS | 2006-01-02 |
| `data/fred/DTWEXBGS.parquet` | DTWEXBGS | 2006-01-02 |
| `data/fred/DTWEXEMEGS.parquet` | DTWEXEMEGS | 2006-01-02 |
| `data/fred/ECBASSETSW.parquet` | ECBASSETSW | 1999-01-01 |
| `data/fred/ECBDFR.parquet` | ECBDFR | 1999-01-01 |
| `data/fred/ECBMRRFR.parquet` | ECBMRRFR | 1999-01-01 |
| `data/fred/ECIALLCIV.parquet` | ECIALLCIV | 2001-01-01 |
| `data/fred/ECIWAG.parquet` | ECIWAG | 2001-01-01 |
| `data/fred/EFFR.parquet` | EFFR | 2000-07-03 |
| `data/fred/EXPINF10YR.parquet` | EXPINF10YR | 1982-01-01 |
| `data/fred/EXPINF1YR.parquet` | EXPINF1YR | 1982-01-01 |
| `data/fred/EXPINF5YR.parquet` | EXPINF5YR | 1982-01-01 |
| `data/fred/FEDTARMD.parquet` | FEDTARMD | 2026-01-01 |
| `data/fred/FLEXCPIM157SFRBATL.parquet` | FLEXCPIM157SFRBATL | 1967-02-01 |
| `data/fred/GASREGW.parquet` | GASREGW | 1990-08-20 |
| `data/fred/GDPNOW.parquet` | GDPNOW | 2011-07-01 |
| `data/fred/HOUST.parquet` | HOUST | 1959-01-01 |
| `data/fred/IC4WSA.parquet` | IC4WSA | 1967-01-28 |
| `data/fred/ICSA.parquet` | ICSA | 1967-01-07 |
| `data/fred/IHLIDXNEWUS.parquet` | IHLIDXNEWUS | 2020-02-01 |
| `data/fred/IHLIDXUS.parquet` | IHLIDXUS | 2020-02-01 |
| `data/fred/INDPRO.parquet` | INDPRO | 1919-01-01 |
| `data/fred/IORB.parquet` | IORB | 2021-07-29 |
| `data/fred/IPG2211A2N.parquet` | IPG2211A2N | 1939-01-01 |
| `data/fred/IPG2211S.parquet` | IPG2211S | 1972-01-01 |
| `data/fred/IPG3344S.parquet` | IPG3344S | 1972-01-01 |
| `data/fred/IPUTIL.parquet` | IPUTIL | 1939-01-01 |
| `data/fred/IQ.parquet` | IQ | 1983-09-01 |
| `data/fred/IR.parquet` | IR | 1982-09-01 |
| `data/fred/IR3TIB01AUM156N.parquet` | IR3TIB01AUM156N | 1968-01-01 |
| `data/fred/IR3TIB01CAM156N.parquet` | IR3TIB01CAM156N | 1956-01-01 |
| `data/fred/IR3TIB01CHM156N.parquet` | IR3TIB01CHM156N | 1999-07-01 |
| `data/fred/IR3TIB01GBM156N.parquet` | IR3TIB01GBM156N | 1957-01-01 |
| `data/fred/IRLTLT01AUM156N.parquet` | IRLTLT01AUM156N | 1969-07-01 |
| `data/fred/IRLTLT01CAM156N.parquet` | IRLTLT01CAM156N | 1955-01-01 |
| `data/fred/IRLTLT01CHM156N.parquet` | IRLTLT01CHM156N | 1955-01-01 |
| `data/fred/IRLTLT01EZM156N.parquet` | IRLTLT01EZM156N | 1970-01-01 |
| `data/fred/IRLTLT01GBM156N.parquet` | IRLTLT01GBM156N | 1960-01-01 |
| `data/fred/IRLTLT01JPM156N.parquet` | IRLTLT01JPM156N | 1989-01-01 |
| `data/fred/IRSTCI01JPM156N.parquet` | IRSTCI01JPM156N | 1985-07-01 |
| `data/fred/ISRATIO.parquet` | ISRATIO | 1992-01-01 |
| `data/fred/IUDSOIA.parquet` | IUDSOIA | 1997-01-02 |
| `data/fred/JPNASSETS.parquet` | JPNASSETS | 1998-04-01 |
| `data/fred/JTSJOL.parquet` | JTSJOL | 2000-12-01 |
| `data/fred/JTSQUR.parquet` | JTSQUR | 2000-12-01 |
| `data/fred/M2SL.parquet` | M2SL | 1959-01-01 |
| `data/fred/MCUMFN.parquet` | MCUMFN | 1972-01-01 |
| `data/fred/MEDCPIM158SFRBCLE.parquet` | MEDCPIM158SFRBCLE | 1983-01-01 |
| `data/fred/MICH.parquet` | MICH | 1978-01-01 |
| `data/fred/MNFCTRIRSA.parquet` | MNFCTRIRSA | 1992-01-01 |
| `data/fred/MORTGAGE30US.parquet` | MORTGAGE30US | 1971-04-02 |
| `data/fred/MPRIME.parquet` | MPRIME | 1949-01-01 |
| `data/fred/NEWORDER.parquet` | NEWORDER | 1992-02-01 |
| `data/fred/NFCI.parquet` | NFCI | 1971-01-08 |
| `data/fred/NFCICREDIT.parquet` | NFCICREDIT | 1971-01-08 |
| `data/fred/NFCILEVERAGE.parquet` | NFCILEVERAGE | 1971-01-08 |
| `data/fred/NFCIRISK.parquet` | NFCIRISK | 1971-01-08 |
| `data/fred/NONREVSL.parquet` | NONREVSL | 1943-01-01 |
| `data/fred/OBFR.parquet` | OBFR | 2016-03-01 |
| `data/fred/OVXCLS.parquet` | OVXCLS | 2007-05-10 |
| `data/fred/PAYEMS.parquet` | PAYEMS | 1939-01-01 |
| `data/fred/PCEPI.parquet` | PCEPI | 1959-01-01 |
| `data/fred/PCEPILFE.parquet` | PCEPILFE | 1959-01-01 |
| `data/fred/PCU221122221122.parquet` | PCU221122221122 | 2003-12-01 |
| `data/fred/PCU331110331110.parquet` | PCU331110331110 | 1965-01-01 |
| `data/fred/PCU334413334413.parquet` | PCU334413334413 | 1967-01-01 |
| `data/fred/PERMIT.parquet` | PERMIT | 1960-01-01 |
| `data/fred/PFGIUAMFRBDAL.parquet` | PFGIUAMFRBDAL | 2004-06-01 |
| `data/fred/PPIFES.parquet` | PPIFES | 2010-04-01 |
| `data/fred/PPIFIS.parquet` | PPIFIS | 2009-11-01 |
| `data/fred/PSAVERT.parquet` | PSAVERT | 1959-01-01 |
| `data/fred/RBAUBIS.parquet` | RBAUBIS | 1994-01-01 |
| `data/fred/RBBRBIS.parquet` | RBBRBIS | 1994-01-01 |
| `data/fred/RBCABIS.parquet` | RBCABIS | 1994-01-01 |
| `data/fred/RBCHBIS.parquet` | RBCHBIS | 1994-01-01 |
| `data/fred/RBCNBIS.parquet` | RBCNBIS | 1994-01-01 |
| `data/fred/RBGBBIS.parquet` | RBGBBIS | 1994-01-01 |
| `data/fred/RBJPBIS.parquet` | RBJPBIS | 1994-01-01 |
| `data/fred/RBMXBIS.parquet` | RBMXBIS | 1994-01-01 |
| `data/fred/RBUSBIS.parquet` | RBUSBIS | 1994-01-01 |
| `data/fred/RBXMBIS.parquet` | RBXMBIS | 1994-01-01 |
| `data/fred/RECPROUSM156N.parquet` | RECPROUSM156N | 1967-06-01 |
| `data/fred/REVOLSL.parquet` | REVOLSL | 1968-01-01 |
| `data/fred/RIFSPPNA2P2D90NB.parquet` | RIFSPPNA2P2D90NB | 1998-01-02 |
| `data/fred/RIFSPPNAAD90NB.parquet` | RIFSPPNAAD90NB | 1997-01-02 |
| `data/fred/RRPONTSYD.parquet` | RRPONTSYD | 2003-02-07 |
| `data/fred/RSAFS.parquet` | RSAFS | 1992-01-01 |
| `data/fred/SAHMREALTIME.parquet` | SAHMREALTIME | 1959-12-01 |
| `data/fred/SOFR.parquet` | SOFR | 2018-04-03 |
| `data/fred/SOFR99.parquet` | SOFR99 | 2018-04-03 |
| `data/fred/STICKCPIM157SFRBATL.parquet` | STICKCPIM157SFRBATL | 1967-02-01 |
| `data/fred/STLFSI4.parquet` | STLFSI4 | 1993-12-31 |
| `data/fred/SWPT.parquet` | SWPT | 2002-12-18 |
| `data/fred/T10Y2Y.parquet` | T10Y2Y | 1976-06-01 |
| `data/fred/T10Y3M.parquet` | T10Y3M | 1982-01-04 |
| `data/fred/T10YIE.parquet` | T10YIE | 2003-01-02 |
| `data/fred/T5YIE.parquet` | T5YIE | 2003-01-02 |
| `data/fred/T5YIFR.parquet` | T5YIFR | 2003-01-02 |
| `data/fred/TCU.parquet` | TCU | 1967-01-01 |
| `data/fred/THREEFYTP10.parquet` | THREEFYTP10 | 1990-01-02 |
| `data/fred/TOTALSL.parquet` | TOTALSL | 1943-01-01 |
| `data/fred/TRMMEANCPIM158SFRBCLE.parquet` | TRMMEANCPIM158SFRBCLE | 1983-01-01 |
| `data/fred/UEMPMEAN.parquet` | UEMPMEAN | 1948-01-01 |
| `data/fred/UMCSENT.parquet` | UMCSENT | 1952-11-01 |
| `data/fred/UNRATE.parquet` | UNRATE | 1948-01-01 |
| `data/fred/USGOVT.parquet` | USGOVT | 1939-01-01 |
| `data/fred/USPRIV.parquet` | USPRIV | 1939-01-01 |
| `data/fred/USREC.parquet` | USREC | 1854-12-01 |
| `data/fred/USRECD.parquet` | USRECD | 1854-12-01 |
| `data/fred/VIXCLS.parquet` | VIXCLS | 1990-01-02 |
| `data/fred/VXEEMCLS.parquet` | VXEEMCLS | 2011-03-16 |
| `data/fred/W875RX1.parquet` | W875RX1 | 1959-01-01 |
| `data/fred/WALCL.parquet` | WALCL | 2002-12-18 |
| `data/fred/WEI.parquet` | WEI | 2008-01-05 |
| `data/fred/WLCFLL.parquet` | WLCFLL | 2002-12-18 |
| `data/fred/WPU01.parquet` | WPU01 | 1913-01-01 |
| `data/fred/WPU012.parquet` | WPU012 | 1926-01-01 |
| `data/fred/WPU0543.parquet` | WPU0543 | 1958-01-01 |
| `data/fred/WRESBAL.parquet` | WRESBAL | 2002-12-18 |

### data/fred_vintage (9 series)

| path | series | first date |
|---|---|---|
| `data/fred_vintage/payems_all_vintages.parquet` | payems_all_vintages | None |
| `data/fred_vintage/release_targets/CPIAUCSL_all_vintages.parquet` | CPIAUCSL_all_vintages | None |
| `data/fred_vintage/release_targets/CPILFESL_all_vintages.parquet` | CPILFESL_all_vintages | None |
| `data/fred_vintage/release_targets/PAYEMS_all_vintages.parquet` | PAYEMS_all_vintages | None |
| `data/fred_vintage/release_targets/PCEPILFE_all_vintages.parquet` | PCEPILFE_all_vintages | None |
| `data/fred_vintage/release_targets/PCEPI_all_vintages.parquet` | PCEPI_all_vintages | None |
| `data/fred_vintage/release_targets/PPIFES_all_vintages.parquet` | PPIFES_all_vintages | None |
| `data/fred_vintage/release_targets/PPIFIS_all_vintages.parquet` | PPIFIS_all_vintages | None |
| `data/fred_vintage/vintages.parquet` | vintages | None |

### data/treasury (3 series)

| path | series | first date |
|---|---|---|
| `data/treasury/net_issuance.parquet` | net_issuance | 2005-10-03 |
| `data/treasury/tga.parquet` | tga | 2005-10-03 |
| `data/treasury/withheld_taxes.parquet` | withheld_taxes | 2023-02-14 |

### data/treasury_auctions (2 series)

| path | series | first date |
|---|---|---|
| `data/treasury_auctions/auctions.parquet` | auctions | None |
| `data/treasury_auctions/treasury_auction_runs.parquet` | treasury_auction_runs | 2026-06-15 |

### data/ofr_fsi (9 series)

| path | series | first date |
|---|---|---|
| `data/ofr_fsi/fsi.parquet` | fsi | 2000-01-03 |
| `data/ofr_fsi/fsi_credit.parquet` | fsi_credit | 2000-01-03 |
| `data/ofr_fsi/fsi_em.parquet` | fsi_em | 2000-01-03 |
| `data/ofr_fsi/fsi_equity.parquet` | fsi_equity | 2000-01-03 |
| `data/ofr_fsi/fsi_funding.parquet` | fsi_funding | 2000-01-03 |
| `data/ofr_fsi/fsi_oae.parquet` | fsi_oae | 2000-01-03 |
| `data/ofr_fsi/fsi_safe_assets.parquet` | fsi_safe_assets | 2000-01-03 |
| `data/ofr_fsi/fsi_us.parquet` | fsi_us | 2000-01-03 |
| `data/ofr_fsi/fsi_volatility.parquet` | fsi_volatility | 2000-01-03 |

### data/corp_bonds (343 series)

| path | series | first date |
|---|---|---|
| `data/corp_bonds/corp_bond_holdings_runs.parquet` | corp_bond_holdings_runs | 2026-07-15 |
| `data/corp_bonds/filing_pricing_sources.parquet` | filing_pricing_sources | None |
| `data/corp_bonds/finra_corp_bonds_runs.parquet` | finra_corp_bonds_runs | 2026-07-15 |
| `data/corp_bonds/finra_corporateMarketBreadth.parquet` | finra_corporateMarketBreadth | None |
| `data/corp_bonds/finra_corporateMarketSentiment.parquet` | finra_corporateMarketSentiment | None |
| `data/corp_bonds/finra_corporatesAndAgenciesCappedVolume.parquet` | finra_corporatesAndAgenciesCappedVolume | None |
| `data/corp_bonds/holdings/JNK/2026-07-10.parquet` | 2026-07-10 | None |
| `data/corp_bonds/holdings/JNK/2026-07-14.parquet` | 2026-07-14 | None |
| `data/corp_bonds/holdings/JNK/2026-07-16.parquet` | 2026-07-16 | None |
| `data/corp_bonds/holdings/JNK/2026-07-17.parquet` | 2026-07-17 | None |
| `data/corp_bonds/holdings/JNK/2026-07-20.parquet` | 2026-07-20 | None |
| `data/corp_bonds/holdings/JNK/2026-07-21.parquet` | 2026-07-21 | None |
| `data/corp_bonds/holdings/JNK/2026-07-22.parquet` | 2026-07-22 | None |
| `data/corp_bonds/holdings/JNK/2026-07-23.parquet` | 2026-07-23 | None |
| `data/corp_bonds/holdings/JNK/2026-07-24.parquet` | 2026-07-24 | None |
| `data/corp_bonds/holdings/JNK/2026-07-27.parquet` | 2026-07-27 | None |
| `data/corp_bonds/holdings/JNK/2026-07-28.parquet` | 2026-07-28 | None |
| `data/corp_bonds/holdings/JNK/2026-07-29.parquet` | 2026-07-29 | None |
| `data/corp_bonds/holdings/JNK/2026-07-30.parquet` | 2026-07-30 | None |
| `data/corp_bonds/holdings/JNK/2026-08-04.parquet` | 2026-08-04 | None |
| `data/corp_bonds/holdings/JNK/2026-08-05.parquet` | 2026-08-05 | None |
| `data/corp_bonds/holdings/JNK/2026-08-06.parquet` | 2026-08-06 | None |
| `data/corp_bonds/holdings/JNK/2026-08-07.parquet` | 2026-08-07 | None |
| `data/corp_bonds/holdings/JNK/2026-08-11.parquet` | 2026-08-11 | None |
| `data/corp_bonds/holdings/JNK/2026-08-12.parquet` | 2026-08-12 | None |
| `data/corp_bonds/holdings/JNK/2026-08-14.parquet` | 2026-08-14 | None |
| `data/corp_bonds/holdings/JNK/2026-08-17.parquet` | 2026-08-17 | None |
| `data/corp_bonds/holdings/JNK/2026-08-18.parquet` | 2026-08-18 | None |
| `data/corp_bonds/holdings/JNK/2026-08-19.parquet` | 2026-08-19 | None |
| `data/corp_bonds/holdings/JNK/2026-08-20.parquet` | 2026-08-20 | None |
| `data/corp_bonds/holdings/JNK/2026-08-21.parquet` | 2026-08-21 | None |
| `data/corp_bonds/holdings/JNK/2026-08-24.parquet` | 2026-08-24 | None |
| `data/corp_bonds/holdings/JNK/2026-08-25.parquet` | 2026-08-25 | None |
| `data/corp_bonds/holdings/JNK/2026-08-26.parquet` | 2026-08-26 | None |
| `data/corp_bonds/holdings/JNK/2026-08-27.parquet` | 2026-08-27 | None |
| `data/corp_bonds/holdings/JNK/2026-08-28.parquet` | 2026-08-28 | None |
| `data/corp_bonds/holdings/JNK/2026-09-01.parquet` | 2026-09-01 | None |
| `data/corp_bonds/holdings/JNK/2026-09-02.parquet` | 2026-09-02 | None |
| `data/corp_bonds/holdings/JNK/2026-09-03.parquet` | 2026-09-03 | None |
| `data/corp_bonds/holdings/JNK/2026-09-04.parquet` | 2026-09-04 | None |
| `data/corp_bonds/holdings/JNK/2026-09-08.parquet` | 2026-09-08 | None |
| `data/corp_bonds/holdings/JNK/2026-09-09.parquet` | 2026-09-09 | None |
| `data/corp_bonds/holdings/JNK/2026-09-10.parquet` | 2026-09-10 | None |
| `data/corp_bonds/holdings/JNK/2026-09-11.parquet` | 2026-09-11 | None |
| `data/corp_bonds/holdings/JNK/2026-09-14.parquet` | 2026-09-14 | None |
| `data/corp_bonds/holdings/JNK/2026-09-15.parquet` | 2026-09-15 | None |
| `data/corp_bonds/holdings/JNK/2026-09-16.parquet` | 2026-09-16 | None |
| `data/corp_bonds/holdings/JNK/2026-09-17.parquet` | 2026-09-17 | None |
| `data/corp_bonds/holdings/JNK/2026-09-18.parquet` | 2026-09-18 | None |
| `data/corp_bonds/holdings/JNK/2026-09-21.parquet` | 2026-09-21 | None |
| `data/corp_bonds/holdings/JNK/2026-09-22.parquet` | 2026-09-22 | None |
| `data/corp_bonds/holdings/JNK/2026-09-24.parquet` | 2026-09-24 | None |
| `data/corp_bonds/holdings/JNK/2026-09-29.parquet` | 2026-09-29 | None |
| `data/corp_bonds/holdings/JNK/2026-09-30.parquet` | 2026-09-30 | None |
| `data/corp_bonds/holdings/JNK/2026-10-01.parquet` | 2026-10-01 | None |
| `data/corp_bonds/holdings/JNK/2026-10-02.parquet` | 2026-10-02 | None |
| `data/corp_bonds/holdings/JNK/2026-10-05.parquet` | 2026-10-05 | None |
| `data/corp_bonds/holdings/JNK/2026-10-06.parquet` | 2026-10-06 | None |
| `data/corp_bonds/holdings/JNK/2026-10-07.parquet` | 2026-10-07 | None |
| `data/corp_bonds/holdings/JNK/2026-10-13.parquet` | 2026-10-13 | None |
| `data/corp_bonds/holdings/JNK/2026-10-19.parquet` | 2026-10-19 | None |
| `data/corp_bonds/holdings/JNK/2026-10-20.parquet` | 2026-10-20 | None |
| `data/corp_bonds/holdings/JNK/2026-10-21.parquet` | 2026-10-21 | None |
| `data/corp_bonds/holdings/JNK/2026-10-22.parquet` | 2026-10-22 | None |
| `data/corp_bonds/holdings/JNK/2026-10-29.parquet` | 2026-10-29 | None |
| `data/corp_bonds/holdings/JNK/2026-10-30.parquet` | 2026-10-30 | None |
| `data/corp_bonds/holdings/JNK/2026-11-02.parquet` | 2026-11-02 | None |
| `data/corp_bonds/holdings/JNK/2026-11-03.parquet` | 2026-11-03 | None |
| `data/corp_bonds/holdings/JNK/2026-11-04.parquet` | 2026-11-04 | None |
| `data/corp_bonds/holdings/JNK/2026-11-05.parquet` | 2026-11-05 | None |
| `data/corp_bonds/holdings/JNK/2026-11-09.parquet` | 2026-11-09 | None |
| `data/corp_bonds/holdings/JNK/2026-11-10.parquet` | 2026-11-10 | None |
| `data/corp_bonds/holdings/SPHY/2026-07-10.parquet` | 2026-07-10 | None |
| `data/corp_bonds/holdings/SPHY/2026-07-14.parquet` | 2026-07-14 | None |
| `data/corp_bonds/holdings/SPHY/2026-07-16.parquet` | 2026-07-16 | None |
| `data/corp_bonds/holdings/SPHY/2026-07-17.parquet` | 2026-07-17 | None |
| `data/corp_bonds/holdings/SPHY/2026-07-20.parquet` | 2026-07-20 | None |
| `data/corp_bonds/holdings/SPHY/2026-07-21.parquet` | 2026-07-21 | None |
| `data/corp_bonds/holdings/SPHY/2026-07-22.parquet` | 2026-07-22 | None |
| `data/corp_bonds/holdings/SPHY/2026-07-23.parquet` | 2026-07-23 | None |
| `data/corp_bonds/holdings/SPHY/2026-07-24.parquet` | 2026-07-24 | None |
| `data/corp_bonds/holdings/SPHY/2026-07-27.parquet` | 2026-07-27 | None |
| `data/corp_bonds/holdings/SPHY/2026-07-28.parquet` | 2026-07-28 | None |
| `data/corp_bonds/holdings/SPHY/2026-07-29.parquet` | 2026-07-29 | None |
| `data/corp_bonds/holdings/SPHY/2026-07-30.parquet` | 2026-07-30 | None |
| `data/corp_bonds/holdings/SPHY/2026-08-04.parquet` | 2026-08-04 | None |
| `data/corp_bonds/holdings/SPHY/2026-08-05.parquet` | 2026-08-05 | None |
| `data/corp_bonds/holdings/SPHY/2026-08-06.parquet` | 2026-08-06 | None |
| `data/corp_bonds/holdings/SPHY/2026-08-07.parquet` | 2026-08-07 | None |
| `data/corp_bonds/holdings/SPHY/2026-08-11.parquet` | 2026-08-11 | None |
| `data/corp_bonds/holdings/SPHY/2026-08-12.parquet` | 2026-08-12 | None |
| `data/corp_bonds/holdings/SPHY/2026-08-14.parquet` | 2026-08-14 | None |
| `data/corp_bonds/holdings/SPHY/2026-08-17.parquet` | 2026-08-17 | None |
| `data/corp_bonds/holdings/SPHY/2026-08-18.parquet` | 2026-08-18 | None |
| `data/corp_bonds/holdings/SPHY/2026-08-19.parquet` | 2026-08-19 | None |
| `data/corp_bonds/holdings/SPHY/2026-08-20.parquet` | 2026-08-20 | None |
| `data/corp_bonds/holdings/SPHY/2026-08-21.parquet` | 2026-08-21 | None |
| `data/corp_bonds/holdings/SPHY/2026-08-24.parquet` | 2026-08-24 | None |
| `data/corp_bonds/holdings/SPHY/2026-08-25.parquet` | 2026-08-25 | None |
| `data/corp_bonds/holdings/SPHY/2026-08-26.parquet` | 2026-08-26 | None |
| `data/corp_bonds/holdings/SPHY/2026-08-27.parquet` | 2026-08-27 | None |
| `data/corp_bonds/holdings/SPHY/2026-08-28.parquet` | 2026-08-28 | None |
| `data/corp_bonds/holdings/SPHY/2026-09-01.parquet` | 2026-09-01 | None |
| `data/corp_bonds/holdings/SPHY/2026-09-02.parquet` | 2026-09-02 | None |
| `data/corp_bonds/holdings/SPHY/2026-09-03.parquet` | 2026-09-03 | None |
| `data/corp_bonds/holdings/SPHY/2026-09-04.parquet` | 2026-09-04 | None |
| `data/corp_bonds/holdings/SPHY/2026-09-08.parquet` | 2026-09-08 | None |
| `data/corp_bonds/holdings/SPHY/2026-09-09.parquet` | 2026-09-09 | None |
| `data/corp_bonds/holdings/SPHY/2026-09-10.parquet` | 2026-09-10 | None |
| `data/corp_bonds/holdings/SPHY/2026-09-11.parquet` | 2026-09-11 | None |
| `data/corp_bonds/holdings/SPHY/2026-09-14.parquet` | 2026-09-14 | None |
| `data/corp_bonds/holdings/SPHY/2026-09-15.parquet` | 2026-09-15 | None |
| `data/corp_bonds/holdings/SPHY/2026-09-16.parquet` | 2026-09-16 | None |
| `data/corp_bonds/holdings/SPHY/2026-09-17.parquet` | 2026-09-17 | None |
| `data/corp_bonds/holdings/SPHY/2026-09-18.parquet` | 2026-09-18 | None |
| `data/corp_bonds/holdings/SPHY/2026-09-21.parquet` | 2026-09-21 | None |
| `data/corp_bonds/holdings/SPHY/2026-09-22.parquet` | 2026-09-22 | None |
| `data/corp_bonds/holdings/SPHY/2026-09-24.parquet` | 2026-09-24 | None |
| `data/corp_bonds/holdings/SPHY/2026-09-29.parquet` | 2026-09-29 | None |
| `data/corp_bonds/holdings/SPHY/2026-09-30.parquet` | 2026-09-30 | None |
| `data/corp_bonds/holdings/SPHY/2026-10-01.parquet` | 2026-10-01 | None |
| `data/corp_bonds/holdings/SPHY/2026-10-02.parquet` | 2026-10-02 | None |
| `data/corp_bonds/holdings/SPHY/2026-10-05.parquet` | 2026-10-05 | None |
| `data/corp_bonds/holdings/SPHY/2026-10-06.parquet` | 2026-10-06 | None |
| `data/corp_bonds/holdings/SPHY/2026-10-07.parquet` | 2026-10-07 | None |
| `data/corp_bonds/holdings/SPHY/2026-10-13.parquet` | 2026-10-13 | None |
| `data/corp_bonds/holdings/SPHY/2026-10-19.parquet` | 2026-10-19 | None |
| `data/corp_bonds/holdings/SPHY/2026-10-20.parquet` | 2026-10-20 | None |
| `data/corp_bonds/holdings/SPHY/2026-10-21.parquet` | 2026-10-21 | None |
| `data/corp_bonds/holdings/SPHY/2026-10-22.parquet` | 2026-10-22 | None |
| `data/corp_bonds/holdings/SPHY/2026-10-29.parquet` | 2026-10-29 | None |
| `data/corp_bonds/holdings/SPHY/2026-10-30.parquet` | 2026-10-30 | None |
| `data/corp_bonds/holdings/SPHY/2026-11-02.parquet` | 2026-11-02 | None |
| `data/corp_bonds/holdings/SPHY/2026-11-03.parquet` | 2026-11-03 | None |
| `data/corp_bonds/holdings/SPHY/2026-11-04.parquet` | 2026-11-04 | None |
| `data/corp_bonds/holdings/SPHY/2026-11-05.parquet` | 2026-11-05 | None |
| `data/corp_bonds/holdings/SPHY/2026-11-09.parquet` | 2026-11-09 | None |
| `data/corp_bonds/holdings/SPHY/2026-11-10.parquet` | 2026-11-10 | None |
| `data/corp_bonds/holdings/SPIB/2026-07-10.parquet` | 2026-07-10 | None |
| `data/corp_bonds/holdings/SPIB/2026-07-14.parquet` | 2026-07-14 | None |
| `data/corp_bonds/holdings/SPIB/2026-07-16.parquet` | 2026-07-16 | None |
| `data/corp_bonds/holdings/SPIB/2026-07-17.parquet` | 2026-07-17 | None |
| `data/corp_bonds/holdings/SPIB/2026-07-20.parquet` | 2026-07-20 | None |
| `data/corp_bonds/holdings/SPIB/2026-07-21.parquet` | 2026-07-21 | None |
| `data/corp_bonds/holdings/SPIB/2026-07-22.parquet` | 2026-07-22 | None |
| `data/corp_bonds/holdings/SPIB/2026-07-23.parquet` | 2026-07-23 | None |
| `data/corp_bonds/holdings/SPIB/2026-07-24.parquet` | 2026-07-24 | None |
| `data/corp_bonds/holdings/SPIB/2026-07-27.parquet` | 2026-07-27 | None |
| `data/corp_bonds/holdings/SPIB/2026-07-28.parquet` | 2026-07-28 | None |
| `data/corp_bonds/holdings/SPIB/2026-07-29.parquet` | 2026-07-29 | None |
| `data/corp_bonds/holdings/SPIB/2026-07-30.parquet` | 2026-07-30 | None |
| `data/corp_bonds/holdings/SPIB/2026-08-04.parquet` | 2026-08-04 | None |
| `data/corp_bonds/holdings/SPIB/2026-08-05.parquet` | 2026-08-05 | None |
| `data/corp_bonds/holdings/SPIB/2026-08-06.parquet` | 2026-08-06 | None |
| `data/corp_bonds/holdings/SPIB/2026-08-07.parquet` | 2026-08-07 | None |
| `data/corp_bonds/holdings/SPIB/2026-08-11.parquet` | 2026-08-11 | None |
| `data/corp_bonds/holdings/SPIB/2026-08-12.parquet` | 2026-08-12 | None |
| `data/corp_bonds/holdings/SPIB/2026-08-14.parquet` | 2026-08-14 | None |
| `data/corp_bonds/holdings/SPIB/2026-08-17.parquet` | 2026-08-17 | None |
| `data/corp_bonds/holdings/SPIB/2026-08-18.parquet` | 2026-08-18 | None |
| `data/corp_bonds/holdings/SPIB/2026-08-19.parquet` | 2026-08-19 | None |
| `data/corp_bonds/holdings/SPIB/2026-08-20.parquet` | 2026-08-20 | None |
| `data/corp_bonds/holdings/SPIB/2026-08-21.parquet` | 2026-08-21 | None |
| `data/corp_bonds/holdings/SPIB/2026-08-24.parquet` | 2026-08-24 | None |
| `data/corp_bonds/holdings/SPIB/2026-08-25.parquet` | 2026-08-25 | None |
| `data/corp_bonds/holdings/SPIB/2026-08-26.parquet` | 2026-08-26 | None |
| `data/corp_bonds/holdings/SPIB/2026-08-27.parquet` | 2026-08-27 | None |
| `data/corp_bonds/holdings/SPIB/2026-08-28.parquet` | 2026-08-28 | None |
| `data/corp_bonds/holdings/SPIB/2026-09-01.parquet` | 2026-09-01 | None |
| `data/corp_bonds/holdings/SPIB/2026-09-02.parquet` | 2026-09-02 | None |
| `data/corp_bonds/holdings/SPIB/2026-09-03.parquet` | 2026-09-03 | None |
| `data/corp_bonds/holdings/SPIB/2026-09-04.parquet` | 2026-09-04 | None |
| `data/corp_bonds/holdings/SPIB/2026-09-08.parquet` | 2026-09-08 | None |
| `data/corp_bonds/holdings/SPIB/2026-09-09.parquet` | 2026-09-09 | None |
| `data/corp_bonds/holdings/SPIB/2026-09-10.parquet` | 2026-09-10 | None |
| `data/corp_bonds/holdings/SPIB/2026-09-11.parquet` | 2026-09-11 | None |
| `data/corp_bonds/holdings/SPIB/2026-09-14.parquet` | 2026-09-14 | None |
| `data/corp_bonds/holdings/SPIB/2026-09-15.parquet` | 2026-09-15 | None |
| `data/corp_bonds/holdings/SPIB/2026-09-16.parquet` | 2026-09-16 | None |
| `data/corp_bonds/holdings/SPIB/2026-09-17.parquet` | 2026-09-17 | None |
| `data/corp_bonds/holdings/SPIB/2026-09-18.parquet` | 2026-09-18 | None |
| `data/corp_bonds/holdings/SPIB/2026-09-21.parquet` | 2026-09-21 | None |
| `data/corp_bonds/holdings/SPIB/2026-09-22.parquet` | 2026-09-22 | None |
| `data/corp_bonds/holdings/SPIB/2026-09-24.parquet` | 2026-09-24 | None |
| `data/corp_bonds/holdings/SPIB/2026-09-29.parquet` | 2026-09-29 | None |
| `data/corp_bonds/holdings/SPIB/2026-09-30.parquet` | 2026-09-30 | None |
| `data/corp_bonds/holdings/SPIB/2026-10-01.parquet` | 2026-10-01 | None |
| `data/corp_bonds/holdings/SPIB/2026-10-02.parquet` | 2026-10-02 | None |
| `data/corp_bonds/holdings/SPIB/2026-10-05.parquet` | 2026-10-05 | None |
| `data/corp_bonds/holdings/SPIB/2026-10-06.parquet` | 2026-10-06 | None |
| `data/corp_bonds/holdings/SPIB/2026-10-07.parquet` | 2026-10-07 | None |
| `data/corp_bonds/holdings/SPIB/2026-10-13.parquet` | 2026-10-13 | None |
| `data/corp_bonds/holdings/SPIB/2026-10-19.parquet` | 2026-10-19 | None |
| `data/corp_bonds/holdings/SPIB/2026-10-20.parquet` | 2026-10-20 | None |
| `data/corp_bonds/holdings/SPIB/2026-10-21.parquet` | 2026-10-21 | None |
| `data/corp_bonds/holdings/SPIB/2026-10-22.parquet` | 2026-10-22 | None |
| `data/corp_bonds/holdings/SPIB/2026-10-29.parquet` | 2026-10-29 | None |
| `data/corp_bonds/holdings/SPIB/2026-10-30.parquet` | 2026-10-30 | None |
| `data/corp_bonds/holdings/SPIB/2026-11-02.parquet` | 2026-11-02 | None |
| `data/corp_bonds/holdings/SPIB/2026-11-03.parquet` | 2026-11-03 | None |
| `data/corp_bonds/holdings/SPIB/2026-11-04.parquet` | 2026-11-04 | None |
| `data/corp_bonds/holdings/SPIB/2026-11-05.parquet` | 2026-11-05 | None |
| `data/corp_bonds/holdings/SPIB/2026-11-09.parquet` | 2026-11-09 | None |
| `data/corp_bonds/holdings/SPIB/2026-11-10.parquet` | 2026-11-10 | None |
| `data/corp_bonds/holdings/SPLB/2026-07-10.parquet` | 2026-07-10 | None |
| `data/corp_bonds/holdings/SPLB/2026-07-14.parquet` | 2026-07-14 | None |
| `data/corp_bonds/holdings/SPLB/2026-07-16.parquet` | 2026-07-16 | None |
| `data/corp_bonds/holdings/SPLB/2026-07-17.parquet` | 2026-07-17 | None |
| `data/corp_bonds/holdings/SPLB/2026-07-20.parquet` | 2026-07-20 | None |
| `data/corp_bonds/holdings/SPLB/2026-07-21.parquet` | 2026-07-21 | None |
| `data/corp_bonds/holdings/SPLB/2026-07-22.parquet` | 2026-07-22 | None |
| `data/corp_bonds/holdings/SPLB/2026-07-23.parquet` | 2026-07-23 | None |
| `data/corp_bonds/holdings/SPLB/2026-07-24.parquet` | 2026-07-24 | None |
| `data/corp_bonds/holdings/SPLB/2026-07-27.parquet` | 2026-07-27 | None |
| `data/corp_bonds/holdings/SPLB/2026-07-28.parquet` | 2026-07-28 | None |
| `data/corp_bonds/holdings/SPLB/2026-07-29.parquet` | 2026-07-29 | None |
| `data/corp_bonds/holdings/SPLB/2026-07-30.parquet` | 2026-07-30 | None |
| `data/corp_bonds/holdings/SPLB/2026-08-04.parquet` | 2026-08-04 | None |
| `data/corp_bonds/holdings/SPLB/2026-08-05.parquet` | 2026-08-05 | None |
| `data/corp_bonds/holdings/SPLB/2026-08-06.parquet` | 2026-08-06 | None |
| `data/corp_bonds/holdings/SPLB/2026-08-07.parquet` | 2026-08-07 | None |
| `data/corp_bonds/holdings/SPLB/2026-08-11.parquet` | 2026-08-11 | None |
| `data/corp_bonds/holdings/SPLB/2026-08-12.parquet` | 2026-08-12 | None |
| `data/corp_bonds/holdings/SPLB/2026-08-14.parquet` | 2026-08-14 | None |
| `data/corp_bonds/holdings/SPLB/2026-08-17.parquet` | 2026-08-17 | None |
| `data/corp_bonds/holdings/SPLB/2026-08-18.parquet` | 2026-08-18 | None |
| `data/corp_bonds/holdings/SPLB/2026-08-19.parquet` | 2026-08-19 | None |
| `data/corp_bonds/holdings/SPLB/2026-08-20.parquet` | 2026-08-20 | None |
| `data/corp_bonds/holdings/SPLB/2026-08-21.parquet` | 2026-08-21 | None |
| `data/corp_bonds/holdings/SPLB/2026-08-24.parquet` | 2026-08-24 | None |
| `data/corp_bonds/holdings/SPLB/2026-08-25.parquet` | 2026-08-25 | None |
| `data/corp_bonds/holdings/SPLB/2026-08-26.parquet` | 2026-08-26 | None |
| `data/corp_bonds/holdings/SPLB/2026-08-27.parquet` | 2026-08-27 | None |
| `data/corp_bonds/holdings/SPLB/2026-08-28.parquet` | 2026-08-28 | None |
| `data/corp_bonds/holdings/SPLB/2026-09-01.parquet` | 2026-09-01 | None |
| `data/corp_bonds/holdings/SPLB/2026-09-02.parquet` | 2026-09-02 | None |
| `data/corp_bonds/holdings/SPLB/2026-09-03.parquet` | 2026-09-03 | None |
| `data/corp_bonds/holdings/SPLB/2026-09-04.parquet` | 2026-09-04 | None |
| `data/corp_bonds/holdings/SPLB/2026-09-08.parquet` | 2026-09-08 | None |
| `data/corp_bonds/holdings/SPLB/2026-09-09.parquet` | 2026-09-09 | None |
| `data/corp_bonds/holdings/SPLB/2026-09-10.parquet` | 2026-09-10 | None |
| `data/corp_bonds/holdings/SPLB/2026-09-11.parquet` | 2026-09-11 | None |
| `data/corp_bonds/holdings/SPLB/2026-09-14.parquet` | 2026-09-14 | None |
| `data/corp_bonds/holdings/SPLB/2026-09-15.parquet` | 2026-09-15 | None |
| `data/corp_bonds/holdings/SPLB/2026-09-16.parquet` | 2026-09-16 | None |
| `data/corp_bonds/holdings/SPLB/2026-09-17.parquet` | 2026-09-17 | None |
| `data/corp_bonds/holdings/SPLB/2026-09-18.parquet` | 2026-09-18 | None |
| `data/corp_bonds/holdings/SPLB/2026-09-21.parquet` | 2026-09-21 | None |
| `data/corp_bonds/holdings/SPLB/2026-09-22.parquet` | 2026-09-22 | None |
| `data/corp_bonds/holdings/SPLB/2026-09-24.parquet` | 2026-09-24 | None |
| `data/corp_bonds/holdings/SPLB/2026-09-29.parquet` | 2026-09-29 | None |
| `data/corp_bonds/holdings/SPLB/2026-09-30.parquet` | 2026-09-30 | None |
| `data/corp_bonds/holdings/SPLB/2026-10-01.parquet` | 2026-10-01 | None |
| `data/corp_bonds/holdings/SPLB/2026-10-02.parquet` | 2026-10-02 | None |
| `data/corp_bonds/holdings/SPLB/2026-10-05.parquet` | 2026-10-05 | None |
| `data/corp_bonds/holdings/SPLB/2026-10-06.parquet` | 2026-10-06 | None |
| `data/corp_bonds/holdings/SPLB/2026-10-07.parquet` | 2026-10-07 | None |
| `data/corp_bonds/holdings/SPLB/2026-10-13.parquet` | 2026-10-13 | None |
| `data/corp_bonds/holdings/SPLB/2026-10-19.parquet` | 2026-10-19 | None |
| `data/corp_bonds/holdings/SPLB/2026-10-20.parquet` | 2026-10-20 | None |
| `data/corp_bonds/holdings/SPLB/2026-10-21.parquet` | 2026-10-21 | None |
| `data/corp_bonds/holdings/SPLB/2026-10-22.parquet` | 2026-10-22 | None |
| `data/corp_bonds/holdings/SPLB/2026-10-29.parquet` | 2026-10-29 | None |
| `data/corp_bonds/holdings/SPLB/2026-10-30.parquet` | 2026-10-30 | None |
| `data/corp_bonds/holdings/SPLB/2026-11-02.parquet` | 2026-11-02 | None |
| `data/corp_bonds/holdings/SPLB/2026-11-04.parquet` | 2026-11-04 | None |
| `data/corp_bonds/holdings/SPLB/2026-11-05.parquet` | 2026-11-05 | None |
| `data/corp_bonds/holdings/SPLB/2026-11-09.parquet` | 2026-11-09 | None |
| `data/corp_bonds/holdings/SPLB/2026-11-10.parquet` | 2026-11-10 | None |
| `data/corp_bonds/holdings/SPSB/2026-07-10.parquet` | 2026-07-10 | None |
| `data/corp_bonds/holdings/SPSB/2026-07-14.parquet` | 2026-07-14 | None |
| `data/corp_bonds/holdings/SPSB/2026-07-16.parquet` | 2026-07-16 | None |
| `data/corp_bonds/holdings/SPSB/2026-07-17.parquet` | 2026-07-17 | None |
| `data/corp_bonds/holdings/SPSB/2026-07-20.parquet` | 2026-07-20 | None |
| `data/corp_bonds/holdings/SPSB/2026-07-21.parquet` | 2026-07-21 | None |
| `data/corp_bonds/holdings/SPSB/2026-07-22.parquet` | 2026-07-22 | None |
| `data/corp_bonds/holdings/SPSB/2026-07-23.parquet` | 2026-07-23 | None |
| `data/corp_bonds/holdings/SPSB/2026-07-24.parquet` | 2026-07-24 | None |
| `data/corp_bonds/holdings/SPSB/2026-07-27.parquet` | 2026-07-27 | None |
| `data/corp_bonds/holdings/SPSB/2026-07-28.parquet` | 2026-07-28 | None |
| `data/corp_bonds/holdings/SPSB/2026-07-29.parquet` | 2026-07-29 | None |
| `data/corp_bonds/holdings/SPSB/2026-07-30.parquet` | 2026-07-30 | None |
| `data/corp_bonds/holdings/SPSB/2026-08-04.parquet` | 2026-08-04 | None |
| `data/corp_bonds/holdings/SPSB/2026-08-05.parquet` | 2026-08-05 | None |
| `data/corp_bonds/holdings/SPSB/2026-08-06.parquet` | 2026-08-06 | None |
| `data/corp_bonds/holdings/SPSB/2026-08-07.parquet` | 2026-08-07 | None |
| `data/corp_bonds/holdings/SPSB/2026-08-11.parquet` | 2026-08-11 | None |
| `data/corp_bonds/holdings/SPSB/2026-08-12.parquet` | 2026-08-12 | None |
| `data/corp_bonds/holdings/SPSB/2026-08-14.parquet` | 2026-08-14 | None |
| `data/corp_bonds/holdings/SPSB/2026-08-17.parquet` | 2026-08-17 | None |
| `data/corp_bonds/holdings/SPSB/2026-08-18.parquet` | 2026-08-18 | None |
| `data/corp_bonds/holdings/SPSB/2026-08-19.parquet` | 2026-08-19 | None |
| `data/corp_bonds/holdings/SPSB/2026-08-20.parquet` | 2026-08-20 | None |
| `data/corp_bonds/holdings/SPSB/2026-08-21.parquet` | 2026-08-21 | None |
| `data/corp_bonds/holdings/SPSB/2026-08-24.parquet` | 2026-08-24 | None |
| `data/corp_bonds/holdings/SPSB/2026-08-25.parquet` | 2026-08-25 | None |
| `data/corp_bonds/holdings/SPSB/2026-08-26.parquet` | 2026-08-26 | None |
| `data/corp_bonds/holdings/SPSB/2026-08-27.parquet` | 2026-08-27 | None |
| `data/corp_bonds/holdings/SPSB/2026-08-28.parquet` | 2026-08-28 | None |
| `data/corp_bonds/holdings/SPSB/2026-09-01.parquet` | 2026-09-01 | None |
| `data/corp_bonds/holdings/SPSB/2026-09-02.parquet` | 2026-09-02 | None |
| `data/corp_bonds/holdings/SPSB/2026-09-03.parquet` | 2026-09-03 | None |
| `data/corp_bonds/holdings/SPSB/2026-09-04.parquet` | 2026-09-04 | None |
| `data/corp_bonds/holdings/SPSB/2026-09-08.parquet` | 2026-09-08 | None |
| `data/corp_bonds/holdings/SPSB/2026-09-09.parquet` | 2026-09-09 | None |
| `data/corp_bonds/holdings/SPSB/2026-09-10.parquet` | 2026-09-10 | None |
| `data/corp_bonds/holdings/SPSB/2026-09-11.parquet` | 2026-09-11 | None |
| `data/corp_bonds/holdings/SPSB/2026-09-14.parquet` | 2026-09-14 | None |
| `data/corp_bonds/holdings/SPSB/2026-09-15.parquet` | 2026-09-15 | None |
| `data/corp_bonds/holdings/SPSB/2026-09-16.parquet` | 2026-09-16 | None |
| `data/corp_bonds/holdings/SPSB/2026-09-17.parquet` | 2026-09-17 | None |
| `data/corp_bonds/holdings/SPSB/2026-09-18.parquet` | 2026-09-18 | None |
| `data/corp_bonds/holdings/SPSB/2026-09-21.parquet` | 2026-09-21 | None |
| `data/corp_bonds/holdings/SPSB/2026-09-22.parquet` | 2026-09-22 | None |
| `data/corp_bonds/holdings/SPSB/2026-09-24.parquet` | 2026-09-24 | None |
| `data/corp_bonds/holdings/SPSB/2026-09-29.parquet` | 2026-09-29 | None |
| `data/corp_bonds/holdings/SPSB/2026-09-30.parquet` | 2026-09-30 | None |
| `data/corp_bonds/holdings/SPSB/2026-10-01.parquet` | 2026-10-01 | None |
| `data/corp_bonds/holdings/SPSB/2026-10-02.parquet` | 2026-10-02 | None |
| `data/corp_bonds/holdings/SPSB/2026-10-05.parquet` | 2026-10-05 | None |
| `data/corp_bonds/holdings/SPSB/2026-10-06.parquet` | 2026-10-06 | None |
| `data/corp_bonds/holdings/SPSB/2026-10-07.parquet` | 2026-10-07 | None |
| `data/corp_bonds/holdings/SPSB/2026-10-13.parquet` | 2026-10-13 | None |
| `data/corp_bonds/holdings/SPSB/2026-10-19.parquet` | 2026-10-19 | None |
| `data/corp_bonds/holdings/SPSB/2026-10-20.parquet` | 2026-10-20 | None |
| `data/corp_bonds/holdings/SPSB/2026-10-21.parquet` | 2026-10-21 | None |
| `data/corp_bonds/holdings/SPSB/2026-10-22.parquet` | 2026-10-22 | None |
| `data/corp_bonds/holdings/SPSB/2026-10-29.parquet` | 2026-10-29 | None |
| `data/corp_bonds/holdings/SPSB/2026-10-30.parquet` | 2026-10-30 | None |
| `data/corp_bonds/holdings/SPSB/2026-11-02.parquet` | 2026-11-02 | None |
| `data/corp_bonds/holdings/SPSB/2026-11-03.parquet` | 2026-11-03 | None |
| `data/corp_bonds/holdings/SPSB/2026-11-04.parquet` | 2026-11-04 | None |
| `data/corp_bonds/holdings/SPSB/2026-11-05.parquet` | 2026-11-05 | None |
| `data/corp_bonds/holdings/SPSB/2026-11-09.parquet` | 2026-11-09 | None |
| `data/corp_bonds/holdings/SPSB/2026-11-10.parquet` | 2026-11-10 | None |
| `data/corp_bonds/series/bond_panel_latest.parquet` | bond_panel_latest | None |
| `data/corp_bonds/series/issuer_daily.parquet` | issuer_daily | None |
| `data/corp_bonds/series/market_daily.parquet` | market_daily | None |
| `data/corp_bonds/series/maturity_wall.parquet` | maturity_wall | None |
| `data/corp_bonds/series/sector_daily.parquet` | sector_daily | None |
| `data/corp_bonds/series/theme_daily.parquet` | theme_daily | None |
| `data/corp_bonds/validation_sample/HYG_2026-07-13.parquet` | HYG_2026-07-13 | None |
| `data/corp_bonds/validation_sample/LQD_2026-07-13.parquet` | LQD_2026-07-13 | None |

### data/china_credit (1 series)

| path | series | first date |
|---|---|---|
| `data/china_credit/tsf.parquet` | tsf | 2015-01-01 |

### data/china_yield (1 series)

| path | series | first date |
|---|---|---|
| `data/china_yield/rates.parquet` | rates | 2023-01-03 |

### data/cot (1 series)

| path | series | first date |
|---|---|---|
| `data/cot/cot_dollar.parquet` | cot_dollar | 1995-01-03 |

### data/yahoo (3 series)

| path | series | first date |
|---|---|---|
| `data/yahoo/DXYN.parquet` | DXYN | 1986-11-25 |
| `data/yahoo/DXYZ.parquet` | DXYZ | 2024-03-26 |
| `data/yahoo/JCDXY.parquet` | JCDXY | 2014-06-24 |

### data/canada_macro (16 series)

| path | series | first date |
|---|---|---|
| `data/canada_macro/cad_reer.parquet` | cad_reer | 1994-01-01 |
| `data/canada_macro/corra.parquet` | corra | 2002-06-10 |
| `data/canada_macro/cpi_index.parquet` | cpi_index | 2006-05-01 |
| `data/canada_macro/cpi_yoy.parquet` | cpi_yoy | 1995-01-01 |
| `data/canada_macro/gdp_monthly.parquet` | gdp_monthly | 2006-04-01 |
| `data/canada_macro/goc_10y.parquet` | goc_10y | 2002-06-11 |
| `data/canada_macro/goc_2y.parquet` | goc_2y | 2002-06-10 |
| `data/canada_macro/goc_5y.parquet` | goc_5y | 2002-06-10 |
| `data/canada_macro/goc_long.parquet` | goc_long | 2002-06-10 |
| `data/canada_macro/goc_rrb.parquet` | goc_rrb | 2002-06-10 |
| `data/canada_macro/house_prices.parquet` | house_prices | 1970-01-01 |
| `data/canada_macro/policy_rate.parquet` | policy_rate | 2009-04-21 |
| `data/canada_macro/unemployment.parquet` | unemployment | 2006-06-01 |
| `data/canada_macro/us_10y.parquet` | us_10y | 1962-01-02 |
| `data/canada_macro/us_2y.parquet` | us_2y | 1976-06-01 |
| `data/canada_macro/usdcad_boc.parquet` | usdcad_boc | 2017-01-03 |

### data/china_macro (13 series)

| path | series | first date |
|---|---|---|
| `data/china_macro/cpi.parquet` | cpi | 2008-01-01 |
| `data/china_macro/customs.parquet` | customs | 2008-01-01 |
| `data/china_macro/fai.parquet` | fai | 2008-03-01 |
| `data/china_macro/gdp.parquet` | gdp | 2006-03-01 |
| `data/china_macro/indpro.parquet` | indpro | 2008-02-01 |
| `data/china_macro/lpr_rate.parquet` | lpr_rate | 2017-12-14 |
| `data/china_macro/money_supply.parquet` | money_supply | 2008-01-01 |
| `data/china_macro/pmi.parquet` | pmi | 2008-01-01 |
| `data/china_macro/ppi.parquet` | ppi | 2006-01-01 |
| `data/china_macro/rates.parquet` | rates | 2026-05-26 |
| `data/china_macro/retail.parquet` | retail | 2008-01-01 |
| `data/china_macro/rmb_loan.parquet` | rmb_loan | 2008-01-01 |
| `data/china_macro/rrr.parquet` | rrr | 2007-01-05 |

### data/china_pboc (3 series)

| path | series | first date |
|---|---|---|
| `data/china_pboc/cny_fix.parquet` | cny_fix | 1994-01-01 |
| `data/china_pboc/fx_reserves.parquet` | fx_reserves | 2008-01-01 |
| `data/china_pboc/repo_rates.parquet` | repo_rates | 2023-06-19 |

### data/intl_macro (37 series)

| path | series | first date |
|---|---|---|
| `data/intl_macro/AU_cpi_yoy.parquet` | AU_cpi_yoy | 1948-07-01 |
| `data/intl_macro/AU_gdp.parquet` | AU_gdp | 1959-07-01 |
| `data/intl_macro/AU_short_3m.parquet` | AU_short_3m | 1968-01-01 |
| `data/intl_macro/AU_unemployment.parquet` | AU_unemployment | 1978-02-01 |
| `data/intl_macro/AU_yield_10y.parquet` | AU_yield_10y | 1969-07-01 |
| `data/intl_macro/EZ_cpi_yoy.parquet` | EZ_cpi_yoy | 1996-12-01 |
| `data/intl_macro/EZ_gdp.parquet` | EZ_gdp | 1995-01-01 |
| `data/intl_macro/EZ_m2.parquet` | EZ_m2 | 1980-01-01 |
| `data/intl_macro/EZ_short_3m.parquet` | EZ_short_3m | 1994-01-01 |
| `data/intl_macro/EZ_unemployment.parquet` | EZ_unemployment | 1990-07-01 |
| `data/intl_macro/EZ_yield_10y.parquet` | EZ_yield_10y | 1970-01-01 |
| `data/intl_macro/GB_cpi_yoy.parquet` | GB_cpi_yoy | 1956-01-01 |
| `data/intl_macro/GB_gdp.parquet` | GB_gdp | 1955-01-01 |
| `data/intl_macro/GB_m2.parquet` | GB_m2 | 1986-12-01 |
| `data/intl_macro/GB_short_3m.parquet` | GB_short_3m | 1957-01-01 |
| `data/intl_macro/GB_unemployment.parquet` | GB_unemployment | 1983-01-01 |
| `data/intl_macro/GB_yield_10y.parquet` | GB_yield_10y | 1960-01-01 |
| `data/intl_macro/IN_cpi_yoy.parquet` | IN_cpi_yoy | 1957-01-01 |
| `data/intl_macro/IN_yield_10y.parquet` | IN_yield_10y | 2011-12-01 |
| `data/intl_macro/JP_cpi_yoy.parquet` | JP_cpi_yoy | 1956-01-01 |
| `data/intl_macro/JP_gdp.parquet` | JP_gdp | 1994-01-01 |
| `data/intl_macro/JP_m2.parquet` | JP_m2 | 1955-01-01 |
| `data/intl_macro/JP_short_3m.parquet` | JP_short_3m | 2002-04-01 |
| `data/intl_macro/JP_unemployment.parquet` | JP_unemployment | 1955-01-01 |
| `data/intl_macro/JP_yield_10y.parquet` | JP_yield_10y | 1989-01-01 |
| `data/intl_macro/KR_cpi_yoy.parquet` | KR_cpi_yoy | 1960-01-01 |
| `data/intl_macro/KR_gdp.parquet` | KR_gdp | 1960-01-01 |
| `data/intl_macro/KR_m2.parquet` | KR_m2 | 1970-01-01 |
| `data/intl_macro/KR_short_3m.parquet` | KR_short_3m | 1991-01-01 |
| `data/intl_macro/KR_unemployment.parquet` | KR_unemployment | 1990-01-01 |
| `data/intl_macro/KR_yield_10y.parquet` | KR_yield_10y | 2000-10-01 |
| `data/intl_macro/de_10y.parquet` | de_10y | 1956-05-01 |
| `data/intl_macro/es_10y.parquet` | es_10y | 1980-01-01 |
| `data/intl_macro/ez_cb_assets.parquet` | ez_cb_assets | 1999-01-01 |
| `data/intl_macro/ez_depo_rate.parquet` | ez_depo_rate | 1999-01-01 |
| `data/intl_macro/fr_10y.parquet` | fr_10y | 1960-01-01 |
| `data/intl_macro/it_10y.parquet` | it_10y | 1991-03-01 |

### data/macro (1 series)

| path | series | first date |
|---|---|---|
| `data/macro/fed_net_liquidity.parquet` | fed_net_liquidity | 2002-12-18 |

### data/macro_snapshots (1 series)

| path | series | first date |
|---|---|---|
| `data/macro_snapshots/ledger.parquet` | ledger | None |

### Latest-value JSON surfaces (not history)

- `data/rates_command/latest.json` (as of None)
- `data/macro_context/latest.json` (as of None)
- `data/international_macro/EZ_latest.json` (as of None)
- `data/international_macro/GB_latest.json` (as of None)
- `data/international_macro/IN_latest.json` (as of None)
- `data/international_macro/JP_latest.json` (as of None)
- `data/international_macro/KR_latest.json` (as of None)

Display surfaces owned by other systems; listed for completeness, not inputs to this build.

## Files, rebuild, tests

- `data/breadth/history/regime_inputs_daily_current.parquet` — 494,532 rows, 4,186,568 bytes (zstd).
- `data/breadth/history/regime_inputs_current.meta.json` — per-series definition, first date, source, basis, kind, gaps; basis and no-outcome sentences; price vintage; registry hashes; the house self-check; a compact rates/credit/dollar census summary.
- `scripts/build_regime_inputs.py` — the builder (off the render path, never nightly); `--basis dated` and `--basis fixchg-current` add the two bases below.
- `data/breadth/history/regime_inputs_dated_sp500_daily.parquet` + `regime_inputs_dated_sp500.meta.json` — the dated-membership basis from 1996 (see "Dated membership (from 1996)" below).
- `data/breadth/history/regime_inputs_fixchg_current.parquet` + `regime_inputs_fixchg_current.meta.json` — the like-for-like fixed-set universe change on the current basis, in a separate file so the two frozen current outputs stay byte-identical.
- Tests in `tests/test_build_tree_breadth_and_index.py` (already CI-registered): 10 synthetic tests (one per statistic plus a full synthetic build) and 3 committed-file tests for the current basis; plus 8 dated/fixed-set synthetic tests and 4 committed-file tests (dated columns/kinds/floors, dated sidecar, the current-basis fixed-set file, and a frozen-byte guard on the two current outputs).

Rebuild (member closes stay off git; ETFs read from main):

```
python3 scripts/build_regime_inputs.py \
  --closes <scratch>/closes_with_topup.parquet \
  --download-meta <scratch>/download_meta_with_topup.json \
  --out data/breadth/history \
  --house-index data/breadth/history/house_ew_index_daily_current.parquet \
  --census-json <rates/credit/dollar census.json>
```

Dated basis (Tiingo archive member closes and dated membership stay off git; SPY read from main):

```
python3 scripts/build_regime_inputs.py --basis dated \
  --closes <scratch>/tiingo_member_closes.parquet \
  --pit-dir <scratch>/breadth \
  --out data/breadth/history \
  --start 1996-01-02            # add --minimum for the COO 13:58Z minimum set
```

Current-basis fixed-set change (same members and prices as the frozen current file):

```
python3 scripts/build_regime_inputs.py --basis fixchg-current \
  --closes <scratch>/closes_with_topup.parquet \
  --download-meta <scratch>/download_meta_with_topup.json \
  --out data/breadth/history
```

## Dated membership (from 1996)

A second basis alongside the current one: `reconstructed_dated_membership` — the S&P 500
dated membership windows (`sp1500_pit_membership`, src=sp500), so a member counts only on
sessions inside its own window. Start 1996-01-02. Where the current basis applies today's
members to the whole past (survivors only), this basis holds the names that were actually
in the index on each date, removing that survivor bias. Sector labels are as of now, not
era-correct.

- **Prices**: the licensed Tiingo EOD archive (normalized eod-bars, captures 2026-10-11..16),
  member-level and held off git. Adjusted closes are the archive's split- and dividend-adjusted
  values as of the capture, not the prices printed at the time. Group-level shares and counts
  only; no member price, row or ticker is committed.
- **Cleaning**: identical to the house dated sector history
  (`scripts/build_group_breadth_history.py`) — partial-session rows dropped by a centred 21-row
  median rule, a duplicate-series scan, and the same missing-rows accounting. 11 partial
  rows dropped; 0 duplicate ticker pairs found.
- **Missing rows**: 453 dated membership rows have no stored close inside their own
  window and are absent. Early-year coverage is lean.
- **Floors**: index 2 priced members; every share and statistic 2 counted members; `n` beside
  every value. Unsupported spans are left missing, never approximated.
- **Fixed-set start window**: the fixed set is the dated members at t with a defined average
  at both t and t-k; it is not membership at both ends. Rows whose start session precedes the
  first dated-membership session (1996-01-02) are not produced: an end date t keeps its
  `fix_chg` / `n_fixed` row for horizon k only when at least k sessions of dated membership
  lie before it, so the fixed-set lines start with the diff series (1996-01-31 for k=21,
  1996-04-01 for k=63). A row (end date t, horizon k) is a *true both-ends count* when every
  name counted in `n_fixed` is a dated S&P 500 member at both session t and session t-k.
  After the blanking, 5,224 of the 15,446 produced k=21 rows (33.82%; 200-day line 34.16%,
  50-day line 33.48%) and 468 of the 15,362 produced k=63 rows (3.05% on both lines) meet
  that definition. Each denominator is all produced `fix_chg_pct_above` rows of that horizon
  after the blanking, the 200-day and 50-day lines together (the `n_fixed` rows mirror them
  1:1, so counting those instead gives the same shares). Before the blanking the same measure
  gave 5,224 of 15,488 k=21 rows (33.73%) and 468 of 15,488 k=63 rows (3.02%): a start-window
  row can never be a true both-ends count, because no name is a dated member before
  1996-01-02.
- **Not included**: curated basket relative indices (ai_software, non_ai_software, IGV, SOXX and SPHB legs) are not included: no dated membership exists for curated baskets. The computed high-beta group IS included; it is derived from the dated universe.
- **No outcomes**: series only: no outcome relation, no regime assignment, no trading call of
  any kind, on any period.

31 daily series, long format `date, series, group, value, n, kind`, data end 2026-10-09;
`regime_inputs_dated_sp500_daily.parquet` holds 496,497 rows (3,984,688 bytes, zstd). This is the **full** set.
The like-for-like fixed-set change is also built on the current basis in a separate small file
(`regime_inputs_fixchg_current.parquet`) so the frozen current outputs stay byte-identical.

| series | definition | first date | gaps |
|---|---|---|---|
| `diff_pct_above_200_21d` | plain difference (points) of the percent-above-200 share, session t minus t-21 | 1996-01-31 | the counted set can differ between the two endpoints of a change; members without a stored close inside their own window are absent; early-year coverage is lean |
| `diff_pct_above_200_63d` | plain difference (points) of the percent-above-200 share, session t minus t-63 | 1996-04-01 | the counted set can differ between the two endpoints of a change; members without a stored close inside their own window are absent; early-year coverage is lean |
| `diff_pct_above_50_21d` | plain difference (points) of the percent-above-50 share, session t minus t-21 | 1996-01-31 | the counted set can differ between the two endpoints of a change; members without a stored close inside their own window are absent; early-year coverage is lean |
| `diff_pct_above_50_63d` | plain difference (points) of the percent-above-50 share, session t minus t-63 | 1996-04-01 | the counted set can differ between the two endpoints of a change; members without a stored close inside their own window are absent; early-year coverage is lean |
| `dispersion_21d` | cross-sectional standard deviation (ddof=1, percent) of member simple 21-session returns, universe and per sector; dated members must be in-window at both ends | 1996-01-31 | members without both endpoint closes, or outside their membership window at either end, are not counted; members without a stored close inside their own window are absent; early-year coverage is lean |
| `dispersion_63d` | cross-sectional standard deviation (ddof=1, percent) of member simple 63-session returns, universe and per sector; dated members must be in-window at both ends | 1996-04-01 | members without both endpoint closes, or outside their membership window at either end, are not counted; members without a stored close inside their own window are absent; early-year coverage is lean |
| `ew_index` | equal-weight total-return index level of the group, chained from 1.0 (daily rebalance) | 1996-01-02 | members without a stored close inside their own window are absent; early-year coverage is lean |
| `ew_vs_spy` | EW universe index divided by SPY close, rebased to 100 at the first common session | 1996-01-02 | different dividend methods between legs shift the long-run ratio level, not the timing of its turns |
| `fix_chg_pct_above_200_21` | like-for-like change (points) of the percent-above-200 share over 21 sessions: universe members at t with a defined 200-session average at BOTH t and t-k; their share above at t minus the share of the same names at t-k; the fixed set is the dated members at t with a defined average at both t and t-k; it is not membership at both ends. Rows whose start session precedes the first dated-membership session (1996-01-02) are not produced. | 1996-01-31 | the fixed set is the members at t with a defined average at both ends; a name leaving the universe before t drops out; members without a stored close inside their own window are absent; early-year coverage is lean |
| `fix_chg_pct_above_200_63` | like-for-like change (points) of the percent-above-200 share over 63 sessions: universe members at t with a defined 200-session average at BOTH t and t-k; their share above at t minus the share of the same names at t-k; the fixed set is the dated members at t with a defined average at both t and t-k; it is not membership at both ends. Rows whose start session precedes the first dated-membership session (1996-01-02) are not produced. | 1996-04-01 | the fixed set is the members at t with a defined average at both ends; a name leaving the universe before t drops out; members without a stored close inside their own window are absent; early-year coverage is lean |
| `fix_chg_pct_above_50_21` | like-for-like change (points) of the percent-above-50 share over 21 sessions: universe members at t with a defined 50-session average at BOTH t and t-k; their share above at t minus the share of the same names at t-k; the fixed set is the dated members at t with a defined average at both t and t-k; it is not membership at both ends. Rows whose start session precedes the first dated-membership session (1996-01-02) are not produced. | 1996-01-31 | the fixed set is the members at t with a defined average at both ends; a name leaving the universe before t drops out; members without a stored close inside their own window are absent; early-year coverage is lean |
| `fix_chg_pct_above_50_63` | like-for-like change (points) of the percent-above-50 share over 63 sessions: universe members at t with a defined 50-session average at BOTH t and t-k; their share above at t minus the share of the same names at t-k; the fixed set is the dated members at t with a defined average at both t and t-k; it is not membership at both ends. Rows whose start session precedes the first dated-membership session (1996-01-02) are not produced. | 1996-04-01 | the fixed set is the members at t with a defined average at both ends; a name leaving the universe before t drops out; members without a stored close inside their own window are absent; early-year coverage is lean |
| `n_above_200` | count of universe members strictly above their own 200-session SMA (n = counted members) | 1996-01-02 | the counted set can differ between the two endpoints of a change; members without a stored close inside their own window are absent; early-year coverage is lean |
| `n_above_50` | count of universe members strictly above their own 50-session SMA (n = counted members) | 1996-01-02 | the counted set can differ between the two endpoints of a change; members without a stored close inside their own window are absent; early-year coverage is lean |
| `n_beat_ew_126d` | count of members beating the EW universe index over 126 sessions (n = counted members) | 1996-07-01 | membership is required on the session; the return window may span a member's entry date; members without a stored close inside their own window are absent; early-year coverage is lean |
| `n_beat_ew_63d` | count of members beating the EW universe index over 63 sessions (n = counted members) | 1996-04-01 | membership is required on the session; the return window may span a member's entry date; members without a stored close inside their own window are absent; early-year coverage is lean |
| `n_counted_nh` | universe members with a close and a full prior 252-session window on the session; the member must be in-window on the session | 1996-01-02 | a close and a full prior 252-session window are both required; members without a stored close inside their own window are absent; early-year coverage is lean |
| `n_fixed_200_21` | members counted at both ends of the 21-session fixed-set change of the percent-above-200 share (defined 200-session average at t and t-k); the fixed set is the dated members at t with a defined average at both t and t-k; it is not membership at both ends. Rows whose start session precedes the first dated-membership session (1996-01-02) are not produced. | 1996-01-31 | the fixed set is the members at t with a defined average at both ends; a name leaving the universe before t drops out; members without a stored close inside their own window are absent; early-year coverage is lean |
| `n_fixed_200_63` | members counted at both ends of the 63-session fixed-set change of the percent-above-200 share (defined 200-session average at t and t-k); the fixed set is the dated members at t with a defined average at both t and t-k; it is not membership at both ends. Rows whose start session precedes the first dated-membership session (1996-01-02) are not produced. | 1996-04-01 | the fixed set is the members at t with a defined average at both ends; a name leaving the universe before t drops out; members without a stored close inside their own window are absent; early-year coverage is lean |
| `n_fixed_50_21` | members counted at both ends of the 21-session fixed-set change of the percent-above-50 share (defined 50-session average at t and t-k); the fixed set is the dated members at t with a defined average at both t and t-k; it is not membership at both ends. Rows whose start session precedes the first dated-membership session (1996-01-02) are not produced. | 1996-01-31 | the fixed set is the members at t with a defined average at both ends; a name leaving the universe before t drops out; members without a stored close inside their own window are absent; early-year coverage is lean |
| `n_fixed_50_63` | members counted at both ends of the 63-session fixed-set change of the percent-above-50 share (defined 50-session average at t and t-k); the fixed set is the dated members at t with a defined average at both t and t-k; it is not membership at both ends. Rows whose start session precedes the first dated-membership session (1996-01-02) are not produced. | 1996-04-01 | the fixed set is the members at t with a defined average at both ends; a name leaving the universe before t drops out; members without a stored close inside their own window are absent; early-year coverage is lean |
| `new_highs_252` | count of universe members whose close strictly exceeds the prior 252-session maximum (full window); the member must be in-window on the session | 1996-01-02 | a close and a full prior 252-session window are both required; members without a stored close inside their own window are absent; early-year coverage is lean |
| `new_lows_252` | count of universe members whose close is strictly below the prior 252-session minimum (full window); the member must be in-window on the session | 1996-01-02 | a close and a full prior 252-session window are both required; members without a stored close inside their own window are absent; early-year coverage is lean |
| `nh_nl_252` | new 252-session highs minus new lows (counts); the member must be in-window on the session | 1996-01-02 | a close and a full prior 252-session window are both required; members without a stored close inside their own window are absent; early-year coverage is lean |
| `pct_above_200` | percent of counted universe members strictly above their own 200-session simple moving average | 1996-01-02 | the counted set can differ between the two endpoints of a change; members without a stored close inside their own window are absent; early-year coverage is lean |
| `pct_above_50` | percent of counted universe members strictly above their own 50-session simple moving average | 1996-01-02 | the counted set can differ between the two endpoints of a change; members without a stored close inside their own window are absent; early-year coverage is lean |
| `pct_beat_ew_126d` | percent of counted members whose simple 126-session return strictly exceeds the EW universe index's over the same window | 1996-07-01 | membership is required on the session; the return window may span a member's entry date; members without a stored close inside their own window are absent; early-year coverage is lean |
| `pct_beat_ew_63d` | percent of counted members whose simple 63-session return strictly exceeds the EW universe index's over the same window | 1996-04-01 | membership is required on the session; the return window may span a member's entry date; members without a stored close inside their own window are absent; early-year coverage is lean |
| `rel_high_beta_computed_vs_ew_universe` | computed high-beta EW index divided by the EW universe index, rebased to 100 at the first common session | 1996-02-01 | computed, not curated; selection restricted to dated members with a full 252-session window at the selection session; the cohort is held fixed within the month |
| `sector_dispersion_21d` | standard deviation (ddof=1, percent) across the 11 sector EW index simple 21-session returns (n = sectors with a valid return) | 1996-01-31 | a sector with fewer than 2 priced members in-window has no EW level that session; n = sectors with a valid return; members without a stored close inside their own window are absent; early-year coverage is lean |
| `sector_dispersion_63d` | standard deviation (ddof=1, percent) across the 11 sector EW index simple 63-session returns (n = sectors with a valid return) | 1996-04-01 | a sector with fewer than 2 priced members in-window has no EW level that session; n = sectors with a valid return; members without a stored close inside their own window are absent; early-year coverage is lean |
