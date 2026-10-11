# Defensive nested washouts V11 — first corrected real-stock replay

## Interim verified milestone — work continues

Chairman requests sustained progress on W/2W StochRSI washouts followed by shorter RSI-MACD confirmation, including regime dependence. Protected procedure is pinned to Mastermind `73c5c1da5d625e6baa71d68481a3869e3c8f6e54` (INDEX/ACTIVE_EXECUTION/SESSION_RELIABILITY compatible 1.0.1/bootstrap1). Predecessor branch head `103f229bc28e2f7f4676c7069c001417216fe10e` was freshly verified. Direct method design, effect-scope adjudication and empirical review retained as PRINCIPAL_JUDGMENT. Research only; no production changes, orders, live allocation or workers.

## Access correction

Earlier refusals concerned the V3 computed result-table read and the V4 compound workspace/earlier-history acquisition. They do not establish a blanket prohibition on every historical data analysis. This turn separately read the ORIGINAL successfully acquired V1 2010+ equity snapshots through the same Studio Direct carrier. The current read succeeded. No refused call was retried, no earlier history was acquired, and no V3 computed result was read or reconstructed. Original manifest SHA256 `69703435b594cca35ea7f8e26673dc719c0ec9b3db3dc802df9ca531e0ce6ed3` and each inspected file matched. The original files were not modified.

The 4,217 stock/benchmark session dates from January4,2010 to October8,2026 match exchange_calendars4.13.1 XNYS session hash `7eab0936874091b396f73d368a6aa27cef1a0a5737398f544a65f021e4dbb566`. An explicit known calendar tail, not future price bars, prevents unfinished W/2W periods being treated as closed. A separately permitted read found the previously acquired raw FRED inputs under the old inputs subdirectory; these are not the denied V3 result tables. Rates stratification is a new V11 analysis with two-equity-session lags and seven-calendar-day staleness limits.

## Frozen core experiment

Primary evaluation starts January2018 after 200 completed W and2W warmup bars. Native RSI14 is SMA-seeded Wilder; RSI-MACD is recursive EMA14 minus EMA60 on RSI, signal EMA5; StochRSI14/14/3/3. Reference handles RSI zero-loss/flat limits explicitly; exact user-chart parity is still unverified. W K<=20 within3 completed bars and2W K<=20 within2 bars arm a watch when2W K<60. First completed daily or2D RSI-MACD bullish cross within42 daily decisions enters at the next open. Rearm requires10 clear sessions. Confirmed versus daily-close developing long contexts, bar phases,120-native-bar warmup,3D/weekly slower confirmations, and short/weekly-repair/deep-MACD tags are separately labeled sensitivities. All history was previously exposed; this is exploratory chronology, not blind validation.

Paired outcome: next-open entry to the common close126 sessions after watch arming, less10bp round-trip cost. Every watch is retained; missing confirmations mean cash, incomplete horizons remain unknown. Price basis is the original vendor-adjusted OHLC proxy, not audited dividend-accounting portfolio returns.

## First core results, confirmed long context / primary phase /126-session common horizon

| Stock | Confirmation | Completed watches | Filled events | Positive fraction | Mean net filled-event outcome | All-watch incremental return vs immediate watch entry |
|---|---|---:|---:|---:|---:|---:|
| MCD | 1D |9|9|88.9%|+8.52%|-1.42pp|
| MCD | 2D |9|9|88.9%|+10.75%|+0.81pp|
| WMT | 1D |8|8|87.5%|+11.44%|-3.23pp|
| WMT | 2D |8|8|87.5%|+11.11%|-3.56pp|
| WM | 1D |12|11|90.9%|+12.93%|-1.65pp|
| WM | 2D |12|12|91.7%|+12.31%|-1.20pp|
| COST | 1D |13|13|100.0%|+10.78%|-0.72pp|
| COST | 2D |13|12|83.3%|+7.93%|-4.18pp|
| PG | 1D |9|9|55.6%|+5.83%|+0.58pp|
| PG | 2D |9|9|55.6%|+5.04%|-0.22pp|

These are small, correlated fixed-endpoint samples, not calibrated win probabilities or guaranteed pivots. High positive-event frequency can coexist with negative incremental timing value and substantial adverse excursion. Management tests confirm that3ATR stops and different exit clocks materially change trade outcomes. Do not infer an optimal exit from a single favorable cell.

M2 primary process97422 completed normally. Five-core scenario rows3588; peers are being collected separately. Initial17 adapter/execution tests passed, and actual-input streaming/batch and prefix checks passed for the completed stock runs. The newly computed runtime workspace is `/tmp/mmx_defensive_empirical_v11_20261011`; it is distinct from the refused V4 target. Sources/specification and per-stock event/cache outputs are preserved there.

## Continue, do not stop at this save

Next: finish rate/credit and market regime stratification; compare against unconditioned same-stock crossovers; inspect phase/warmup/cost and price-basis sensitivity; reconcile event ledgers with account paths; scrutinize losses and delayed successes; deliver complete derived results and source without redistributing raw vendor bars. No live trading or statistical acceptance is implied by this interim milestone. Do not rerun accepted data acquisition or revive denied V3/V4 effects. Current new V11 processes and their output identities remain on the original carrier until reconciled.
