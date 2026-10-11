# Defensive nested washouts V5 — native-clock and cycle-management audit

**October 10, 2026. MISSION_COMPLETE: false. Local mathematical/source/mechanics phase complete; corrected real-stock performance remains untested.**

## 1. Assignment, continuity and access boundary

The user requested a heavy research continuation of long W/2W StochRSI washouts followed by shorter RSI-MACD bullish confirmation. The V4 correction remains: ordinary price-MACD and standalone RSI(2) studies did not test this strategy, and their stock rankings cannot be transferred to it.

Protected Mastermind source reverified unchanged: `326c8469a21d7f50fc9ecb1848196bf1c6e66685`, skillpack1.0.1/bootstrap1. Research predecessor: `bcd05af9779634c9b8071c02181e9be4b008ec58`; verified intermediate V5 checkpoint: `93435d6f523f110c53c06fa1bfc0566c36838797`. Indicator source reference: macro `9bcdbb4d887f1e2a082e1743cb84af6261fb25b4`, native RSI14 -> EMA14 minus EMA60 -> EMA5.

Inherited denied lanes remain the V3 result-table read and V4 compound remote workspace/earlier-price acquisition. No retry, equivalent export, replacement acquisition, recomputation or alternative-carrier attempt occurred. The uploaded local packages provide source and derived reports, not the native market histories required for the corrected experiment. Current work used those already-delivered sources, primary public documentation, algebra and manufactured data only.

No new MCD/WMT/WM/COST/PG return, win rate, correlation, best timeframe, calibrated probability or allocation is claimed. No broker order, live size, production source change, merge, deployment, alert, worker or scheduled continuation. Direct method design and adjudication are intertwined (PRINCIPAL_JUDGMENT).

## 2. Main new result: the clocks define different hypotheses

The offline engine now distinguishes completed-native W/2W state from daily-close developing W/2W state. Each provisional observation starts from the last committed native state and substitutes one current native close; it does not append every daily update as a new weekly candle. Future finalized W/2W values are never placed at the start of the interval.

A constructed ten-observation two-week example produces an early bullish condition that disappears by the final native close; it adds only one committed native bar. This demonstrates a mechanical possibility, not its frequency or profitability in stocks. Completed-bar testing can miss developing-bar decisions, while backfilling the final value creates look-ahead. Neither is a faithful replacement for the other.

Native crossover and crossover of the daily snapshot series are separately retained as `native_bull_first_observation` and `snapshot_bull_event`. During a forming native candle those are different definitions. Main lower-timeframe entries and all exit clocks continue to use completed native bars. Daily reconstruction is not intraday tick reconstruction. User-chart phase, session, adjustment and decision-time parity remain unverified.

## 3. Exact conditional RSI-MACD crossover-price boundary

Let F0/L0 be the previous native EMA14/EMA60 of RSI14 and S0 the previous EMA5 signal. With af=2/15 and al=2/61, current MACD is:

`M = (1-af)F0 - (1-al)L0 + (af-al)R`.

The signal update gives `M-S = (2/3)(M-S0)`. Thus required current RSI for histogram equality is:

`R* = [S0 - (1-af)F0 + (1-al)L0] / (af-al)`.

A fresh native bullish crossover separately requires the previous histogram nonpositive. Let U/D be previous Wilder average gain/loss, A=13U, B=13D and q=R*/100. For a finite interior root, the required close change is `qB/(1-q)-A` when q>=A/(A+B), otherwise `A+B-A/q`. Add it to the previous native close. Flat, saturated and nonpositive-price cases are classified rather than assigned a fictitious usable threshold.

The implementation checked 99 positive finite manufactured roots against direct recalculation, with maximum absolute histogram residual about `1.03e-14`, and verified both sides of each boundary. This is an algebraic threshold conditional on known state, NOT a forecast, target, fill, trade advantage or high-precision prediction.

A manufactured example with prior close100 has a boundary near98.9762. A next close99.50 produces a bullish cross even though price falls0.5% and RSI declines. Histogram changes from about-0.09639 to+0.09769. This proves that improving filtered momentum need not mean a green candle or rising raw RSI on that bar. It does not establish that such entries are valid or invalid.

Proposed diagnostic: `(observed close - conditional boundary) / known daily ATR`. It records margin beyond the mathematical crossover, not confidence. No threshold or empirical benefit is selected.

## 4. Additional indicator-interpretation findings

StochRSI can move because its reference range changes. In a manufactured example, RSI remains47 while the prior fourteen-bar range changes from40–70 to40–50 as an old high rolls out. Raw StochRSI changes from23.33 to70. Smoothing also responds. This is not automatically a false signal; distinguish reference-range change from improving raw momentum before testing incremental value.

An EMA60 has geometric half-life about20.79 native observations, or41.58 weeks on2W bars. That describes filter weights, not a predicted cycle. The first computable signal at native bar78 is not the same as negligible initialization sensitivity. The retained conservative200-native-bar 2W warmup requires roughly400 weeks/7.7years and remains a research convention, not an inherent technical requirement.

A V4 phase-origin issue was reproduced: a shifted2D grid could seed its initial native history with a one-session fragment. V5 excludes such incomplete origin groups. This is a construction correction; no real-market return impact is asserted.

## 5. Complete offline exit/retry mechanics

A fixed feature stream can now be replayed with one fractional-share unit account, next-open entries/exits, known initial stops, opening-gap and entry-day stop handling, close-observed trail updates, explicit holding limits and open/pending sample-end states. No automatic year-end liquidation, dividend cash ledger, cash yield, taxes or cross-stock capital competition is present. It is a research normalization, not recommended sizing.

Exit clocks are separate: lower bearish crossover; weekly bearish crossover; or a fresh completed2W K>=80 after entry followed by weekly bearish crossover. All have explicit maximum holding and protective-risk assumptions; no optimal stop/exit is claimed.

A local prototype defect was caught with failing tests and repaired: a stale pre-entry2W K>=80 could arm the cycle exit. Fresh-native metadata is now mandatory for that exit. The manufactured regression previously exited December31 rather than the declared fresh-reading policy's January6. No production strategy was changed.

One versus at most two attempts are modeled within the SAME fixed active watch. A retry requires a fresh lower bullish signal, an intervening lower bearish reset by default, cooldown and remaining watch validity. Failed first attempts stay in both ledger and account. This is not pyramiding, averaging down, an unlimited retry, or a new independent market cycle.

## 6. Same-opportunity evaluation and chart-parity contract

Master watches are fixed before optional short-StochRSI or deep-MACD entry filters. Two estimands remain explicit: gate the same first crossover versus wait for the first eligible crossover. The former retains rejected opportunities and missed winners; the latter changes delay and reentry paths. Paired63/126/252-session files keep incomplete horizons distinct from losses. Event windows can overlap; the account model cannot hold overlapping positions.

A new evaluation segment starts in cash and admits only watches armed on/after its start; earlier prices are used for warmup, not silently adopted trades. Empty-opportunity segments produce schema-valid outputs rather than errors. This empty-case defect was reproduced and repaired before delivery.

The export comparator requires native start/close-session agreement and sufficient finite RSI/MACD/signal/K/D rows at a declared tolerance. All-NaN arrays and a handful of rows do not prove parity. Tests used an independently copied synthetic export, not an actual TradingView export. It does not choose phases using returns.

## 7. Verification and delivery

**61 local unit/integration/CLI tests passed** in the final run. Observed mechanics include native/batch identity, immutable previews, explicit cross semantics, prefix invariance, future perturbations, phase/calendar boundaries, numeric inversion, costs/stops, pending state, retry accounting, fixed opportunity sets and parity checks. Two end-to-end CLI walkthroughs use manufactured sinusoidal prices and a manufactured weekday calendar. These are not stock backtests. Actual stocks tested in this continuation:0.

Six Python source files are syntax-checked. No networking modules are imported in delivered research source. Original V4 batch reference is preserved byte-for-byte. Synthetic numerical outputs are labeled and never presented as stock evidence.

Local delivery:
- report `/mnt/data/defensive_nested_v5/RESEARCH_FINDINGS.md`, approximately2,955 words;
- code/tests, eight research-status cards, mathematical examples, two final manufactured walkthroughs, explicit synthetic input metadata, README and integrity records;
- package `/mnt/data/Defensive_Nested_Washout_V5_Clock_Research_2026-10-10.zip`,60 files,1,517,933 bytes;59 manifest-member hashes and ZIP integrity verified.

Hashes:
- package: `5e782b5637364c1816f02e3846c5a94ebc6cab23a39e3bc10e1c540a18da3e06`
- report: `4beb383631979fa452ee954c24fbdaaa219e9fb07aa62b2c4e06348ef66c51fe`
- clock engine: `0ccf75074e3bbcb5b994df817ad0e3b36c7612b9ef0af363f32de81b4afa0747`
- policy engine: `93ca27e3a7669eb7a532b8dac7aef5d127b6db7b0326ad9b1ddd5915d38ae507`
- study assembly: `7e4a84c14a53f75c23d80dbd1cbfd719f7f4dcc39b69769547cd1e2762627662`
- CLI: `b32791cd1c0c7137338029aa3405f2dd5b19dd8cf992c950430c33847e9f99f4`

## 8. Exact remaining frontier

The next critical empirical action is fixed actual-stock episode replay using legitimately available native price inputs and verified chart semantics. Compare completed/developing long context, daily/two-day native confirmation, fast/weekly/cycle exits, and bounded attempts; do not expand into another unrelated indicator-family search. Account for shared market cycles, overlap, all attempted variants and prior exposure to recent history before making inferential claims.

That lane remains blocked by the inherited access boundaries; no legitimate clearance or new raw input was established in this turn. Do not retry or replace denied actions on continuation. Source-known issuer/rates/credit context remains a hypothesis, not a validated filter. No new ticker ranking, hit rate, expected return or weight may be published from these synthetic results.

Stop reason: the ready independent mathematical/mechanical work is delivered and verified; actual-market confirmation and chart parity remain outstanding. MISSION_COMPLETE remains false. No pending modification, active child, user-auth ceremony, automated wake or durable background execution is fabricated. Preserve accepted V5 results unless their code/definitions change.

## Primary references

TradingView execution model/rollback: https://www.tradingview.com/pine-script-docs/language/execution-model/
TradingView other timeframes and lookahead: https://www.tradingview.com/pine-script-docs/concepts/other-timeframes-and-data/
TradingView repainting: https://www.tradingview.com/pine-script-docs/concepts/repainting/
TradingView Stochastic RSI: https://www.tradingview.com/support/solutions/43000502333-stochastic-rsi-stoch-rsi/
TradingView strategies: https://www.tradingview.com/pine-script-docs/concepts/strategies/
Sullivan, Timmermann and White1999: https://doi.org/10.1111/0022-1082.00163

References support definitions/methodology, not profitable outcomes. New algebra/counterexamples are derived in the attached report and verified by the included synthetic tests.