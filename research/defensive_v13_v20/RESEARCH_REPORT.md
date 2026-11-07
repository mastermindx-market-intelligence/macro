# Defensive Nested-Washout Research V13–V20
**Completed October 13, 2026 · equity snapshot cutoff October 8, 2026 · research only**

## Executive finding

The Chairman’s hypothesis is fundamentally a **long-horizon recovery-context signal**, not a standalone daily oscillator alpha model. The corrected V11 core-five historical sample was favorable at fixed horizons, but the next eight research phases uncover essential qualifications: the same exact six-month dates frequently favored non-signaled defensive peers; short RSI-MACD crossover timing was little better than counterfactual delays; tight stops removed eventual recoveries; keeping capital invested between watches can improve the return profile but depends on the benchmark, realized fill clock and historical period. Most importantly, **the stock’s relative recovery after week four appears more interesting than its precision on entry day**, but remains retrospectively selected.

**Do not install, size or automate trades from this evidence.** Not a production trading signal, chart-parity proof, prediction-interval calibration or a true holdout. Neither 1D nor 2D has a selection-adjusted confirmed trading edge. All proposed stock and SPY exposures are hypothetical account normalization only.

## Evidence and input custody

- The original V11 evidence was published in [macro PR #9034](https://github.com/mastermindx-market-intelligence/macro/pull/9034) and merged. Its immutable reproduction ZIP has SHA-256 `97966f72ea15cb34e0f5453252eef683411c894b7ca4432de4ce7c540d1ffaf0`.
- V12 has its own existing [PR #9064](https://github.com/mastermindx-market-intelligence/macro/pull/9064), separate author, head and review/CI. Do **not** modify, duplicate, merge or impersonate its custody from this continuation.
- M2 recovery workspace: `/Volumes/Mastermind/research/defensive_nested_v12_20261013`. Previously missing `/tmp` directories were not blindly replayed. Retained V11 archive and a separately dated, originally admitted 2010+ vendor-data re-fetch were reconciled against fixed V11 entries; the latest snapshot raw bytes differ but the maximum V11 event-result discrepancy was ~7.7e-7. This is **not a new independent vendor** and not a vintage-controlled fundamental study.
- V12 frozen first-entry schedule: 396 original 1D/2D watches across 18 original named equities; 340 completed filled events in the full panel. Core five have **50 daily plus 50 two-day completed first-watch entries**, drawn from **114 original core watch records** (12 incomplete, two skipped). Both frames frequently select overlapping same-stock cycles; they are not 100 independent events.
- No denied V3 result read, V4 earlier-history acquisition, or prior refused cache-modification operation was repeated. V13–V20 use original V11/V12 derived files and already-admitted same-window data. No new data acquisition, broker access, live sizing or production edits.

## Precise setup and units

Long watch: completed weekly StochRSI K <=20 during the last three weekly candles and completed two-week K <=20 during the last two 2W candles, 2W K<60; first completed 1D or 2D RSI-MACD (RSI14, EMA14-EMA60, signal EMA5) bullish crossover and following-open entry. 200 completed higher-frame warmup bars, 42-session watch and clear interval as V11. The main V12 exit event study holds each selected entry until the **common arm+126-session endpoint**, which is earlier than 126 full sessions of ownership when confirmation was delayed. This must not be confused with V11’s 126-full-entry-session context-at-cross study.

The V13/V14 portfolio study follows the frozen same-stock position schedule through October 8, 2026. Five fixed equal initial-capital sleeves, no cross-sleeve rebalancing, leverage, cash interest, taxes, dividend-cash ledger or realistic spreads. Prices are final-vintage adjusted OHLC proxies. Transaction fee assumption: 5 basis points on each side, with separate 30-basis-point roundtrip sensitivity; corporate-action/custody and exact chart settings remain unverified. Cash account endings and prices do not create executable broker receipts.

## V12 carried-forward: stop distance changes exposure and drawdown

Core five, **50 complete daily first-watch entries** and equal named entry dates:

| Exit | Positive endpoint outcomes | Mean net event return | Mean adverse excursion |
|---|---:|---:|---:|
| No initial stop, hold to common end | 86% | +10.06% | -7.17% |
| Fixed entry-stop 3ATR | 50% | +5.66% | -4.12% |
| Fixed entry-stop 6ATR | 72% | +7.68% | -5.50% |
| 6ATR plus fixed structure low and negative lower histogram | 64% | +6.73% | -4.83% |

A wider 6ATR stop retains more winners at **the same capital notional**, but targets a smaller capital exposure at **the same intended initial stop-risk budget**. The paired matched-risk 6ATR-minus-3ATR result was ~-0.284 percentage points per opportunity; its exploratory block interval included zero. A one-event improvement can dominate a nominally positive rule difference. Hard-stop gap losses can exceed their intended budget. No universal stop is qualified.

## V13: full account paths expose idle capital

Core five equal-initial-capital sleeves, January 2018–October 8, 2026:

| Policy | CAGR | Maximum close-to-close portfolio drawdown | Average stock exposure |
|---|---:|---:|---:|
| Buy and hold same five stocks, fixed initial sleeves | **14.25%** | -20.51% | 100% |
| Enter on W+2W watch, hold to fixed study endpoint, cash between | 8.14% | -19.34% | 42.16% |
| Same entry, 3ATR hard stop | 5.22% | -10.78% | 32.83% |
| Same entry, 6ATR hard stop | 6.99% | -15.17% | 38.93% |
| Same entry, structure+negative-hist stop | 6.14% | -14.89% | 36.87% |

**Important correction:** initial V13 portfolio output erroneously anchored buy/hold to the first available 2010 price. Red/green tests established the bug; all reported benchmark calculations were corrected to the January 2018 account start. Earlier uncorrected 2010-anchored results are invalid. Unused cash earns zero by design. These are account capital trajectories, not average single-trade returns.

## V14: alternative reserve is SPY, not idle cash

A fixed posthoc overlay holds SPY in the sleeve while no chosen stock position is open. Switching SPY to the chosen stock is at the next known eligible open. A stock-to-SPY transition **only acquires SPY at the close of the stock exit day**, not retroactively that morning.

**This timing was a material V14 audit fix.** An earlier version improperly credited the SPY opening-to-close movement on days when a stock exit could occur intraday. A failing regression exposed it, then the corrected replay and robustness audit were rerun. Do not reuse the pre-fix **16.80% overlay CAGR / +2.21pp advantage**.

Corrected core-five 1D overlays:

| Overlay | CAGR | Max drawdown |
|---|---:|---:|
| SPY buy-and-hold, same window | 14.59% | -33.72% |
| Buy/hold core five | 14.25% | -20.51% |
| SPY when flat, stock when signaled, fixed endpoint | **16.60%** | **-21.41%** |
| SPY reserve, 3ATR stop | 16.09% | -29.56% |
| SPY reserve, 6ATR stop | 15.60% | -27.85% |

The core overlay CAGR edge over SPY is **+2.01pp**; at a 30bps roundtrip fee instead of 10bps it falls to **+1.57pp**. A four-consecutive-calendar-quarter block-resampling interval for **annualized log-relative advantage** is **-1.78pp to +5.53pp**, including zero. It is not multiple-testing adjusted and is not a direct CAGR confidence interval. Removing any one of the core five leaves a positive historical *point estimate* against SPY. Against peers, this transfer is weak: thirteen-peer endpoint overlay CAGR **14.68%** versus SPY **14.59%**, and the all-18 overlay **15.23%**.

Period instability is substantial: core-overlay relative wealth versus SPY improved **+21.20% during 2018–2022**, then declined **-3.92% over the 2023–2026 remainder**. It is not a validated always-on SPY-beating strategy. The overlay and SPY benchmark own equity-market beta almost all the time; it does not demonstrate stock timing independent of factor exposure.

## V15: the same-date four-stock control

For every complete core first daily signal, compare its stock's net result to an **equal-weight position in the other four named core stocks**, entered on *exactly the same next-open day* and sold at the *same endpoint*, using the same fee convention:

- 50 daily events: signaled stock mean **+10.06%**; contemporaneous other-four average **+9.19%**.
- Mean incremental same-date stock selection **+0.87 percentage points**; selected stock beat the other-four mean only **25/50** times.
- Exploratory four-quarter clustered confidence interval **-0.98pp to +2.93pp** includes zero. Stock-specific means vary from MCD/PG underperforming their comparators to WMT/WM/COST positive, all sample-dependent.

**Implication:** many six-month successes are shared sector/market recoveries, not proof the method uniquely chooses the best defensive stock.

## V16: first fresh crossover versus matched alternate waiting

Frozen original watches and common endpoints were maintained. Reshuffle observed signal-to-arm lags among events within the same arm year. This is a diagnostic counterfactual and does not pretend a trader knew alternative future signals:

| Frame | Actual mean return | Mean year-matched shuffle | Actual-minus-shuffle |
|---|---:|---:|---:|
| 1D | +10.06% | +9.73% | **+0.33pp** |
| 2D | +9.47% | +10.25% | **-0.77pp** |

Within 5000 permuted sets, ~22.9% exceeded the daily actual mean; ~97.4% exceeded the 2D mean. This is not a valid market efficiency p-value: exact signal-dependent delay, correlated cycles and posthoc inspection still matter.

A separate trailing-252-session, ex-ante SPY-beta adjustment for the selected-stock terminal return minus its other-four counterparts yielded a daily mean **+0.71pp in log-return units**, with an exploratory block interval **-0.96 to +2.60pp**.

## V17: relative leader/laggard state at entry

Classify the selected stock using its prior **63 completed trading sessions through t-1** versus an equal mean of the four peers; no outcome-fitted threshold beyond relative sign:

- Daily: 41/50 entries had been **laggards**. Their subsequent beta-adjusted selected-versus-other-four mean was **+0.87pp log**; nine prior leaders had approximately zero.
- Two-day: 38/50 were laggards; their beta-adjusted relative mean ~+0.66pp versus leaders ~-1.75pp.
- Neither result qualifies a leading/lagging gate: the cells are sparse, comparisons are after seeing the data, and the pooled Spearman diagnostics were not compelling. A universal relative-strength veto would discard most of the actual washout population.

## V18: path after the exact entry

The same 50 first daily entries were evaluated after 5,10,20,42,63 trading sessions, always with next-open entry and equal-date four-stock/SPY comparators. Key daily observations:

| Trading sessions from entry | Positive fraction | Mean net result | Selected-minus-four mean |
|---|---:|---:|---:|
| 5 | 60% | +0.79% | +0.40pp |
| 10 | 62% | +1.18% | +0.50pp |
| 20 | 68% | +2.57% | +0.56pp |
| 42 | 72% | +5.07% | +1.44pp |
| 63 | **84%** | **+6.89%** | **+2.31pp** |

**14/50** daily entries had **intraday drawdown worse than -5% during the first 20 sessions**, of which **12** nonetheless had positive terminal net result at session 63. This explains the tension between a seemingly accurate longer-cycle opportunity detector and tight stop losses. It does not justify blindly accepting a -5% dip or averting all stops.

## V19: new relative gain between session 20 and session 63

On identical entry cohorts, the daily selected-minus-four mean rises **from +0.56pp to +2.31pp**, a +1.74pp difference; the two-day difference is +1.87pp. The 4-quarter-block interval for the *change in relative simple-return advantage* was **+0.05 to +3.60pp** on daily and **+0.31 to +3.86pp** on two-day.

This is not the same as automatically entering another trade at day20, and the two non-independent entry frames must not be counted as separate holdouts. The intervals are not familywise adjusted.

## V20: market-beta-adjusted *incremental* week-four-to-week-thirteen recovery

A further independent algebraic contrast used ex-ante **252 completed daily returns through t-1** to calculate each core stock’s SPY beta. The return window is **close after the 20th owned session to close after the 63rd**, with no new trade or fee charged inside the return decomposition. For each selected stock, subtract beta times SPY's contemporaneous log return; then subtract the equally weighted residual of its other four core peers.

| Initial RSI-MACD confirmation | Selected-minus-four beta-adjusted log return | Four-quarter block interval | Observations |
|---|---:|---:|---:|
| Daily | **+1.53pp** | **-0.05 to +3.18pp** | 50 |
| Two-day | **+1.96pp** | **+0.31 to +4.09pp** | 50 |

Daily advantage was positive in **60%** of episodes; two-day in **56%**. Leave-one-year and leave-one-stock-out point estimates remained positive. The daily interval includes zero; the two-day interval does not, **but it is not selection-adjusted** and these 50/50 sets overlap substantially. Findings suggest the intermediate recovery trajectory is the highest-priority unexplained effect, more than precise entry-day timing.

## Cross-cutting red-team caveats

1. **Selection and no fresh holdout:** original stock universe and latest history were chosen and repeatedly inspected; five-core and thirteen peers were not randomly held out or survivorship-free. No new results can be called prospective.
2. **Correlation and clustering:** many observations share exact risk episodes and dates. Four-quarter block resampling is exploratory and no correction for all prior hypotheses was applied. Small samples make even positive lower bounds fragile.
3. **Actual strategy versus diagnostic:** V16 random-delay resampling is not an executable alternative signal; V19/V20 sequential close-to-close return is not a new position; V13/14 fixed-sleeve accounting differs from average single trade.
4. **Beta estimator:** trailing historical beta is a proxy. Beta can change after entry; one market factor is not all sector/issuer exposure. Counterfactual buy/hold controls do not replace real causal earnings and rates data.
5. **Data:** the latest successfully acquired same-window equity snapshot is a different raw-byte vintage from V11 but was compared against the original entry outcomes. We need independent vendor, dividend cash accounting, original corporate-action/vintage handling, point-in-time fundamentals, chart-export indicator parity, SPY tracking, gap/slippage, market access and true account capital limits before trading.
6. **Publication:** V11 is in main via PR #9034. V12 is a separate source/research PR #9064 with independent writer/CI; this continuation must not modify it. This V13–V20 report/derived-data archive is a separate research candidate.
7. **Causal and prediction claims:** no validated per-stock profit probability, portfolio allocation, regime sign, hedge beta, option structure or live order emerges from these results.

## Research conclusion / continuation frontier

Treat **W/2W RSI-context exhaustion** as an opportunity-sponsorship feature. Test how often a true company/sector repair produces 4-to-13-week relative recovery, and whether any ex-ante fundamental revisions or rate/credit observations distinguish that path *without suppressing missed winners*. First require chart parity and source-known point-in-time event data. Do not choose 1D vs 2D on these retrospective aggregate outcomes.

**STATUS: research analyzers and historical outcomes built and independently mechanically tested; alpha/live adoption remains unproven.** The next meaningful product consumer is a *paper-only* conditional-recovery dashboard or prospectively frozen signal ledger, not automatic order/sizing deployment.

### Related sources
- [V11 published original study](https://github.com/mastermindx-market-intelligence/macro/pull/9034)
- [V12 independent follow-up PR](https://github.com/mastermindx-market-intelligence/macro/pull/9064)
- [Mastermind technical indicator system source](https://github.com/mastermindx-market-intelligence/macro/blob/main/engine/canon.py)
