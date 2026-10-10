# Healthcare pivot research — deeper methodology and candidate assessment

**Date:** October 9, 2026. **Status:** PARTIAL; no validated stock/timeframe winner and no current buy instruction.

## Executive result

The new work ran independent numerical and timing diagnostics, not the previously denied historical-data analysis. It materially changes the confidence we should place in any apparent healthcare "best timeframe": the research and application helpers are not numerically identical; history depth can move crosses; an inspected exit harness mixes candle grids; and a confirmation helper needs an unfinished-bucket boundary check. An important existing safeguard was also recovered: the application already has a confirmation-date owner, so a new parallel timing system is neither needed nor justified.

The main task remains incomplete: no new empirical JNJ/LLY/ABBV/MRK/UNH strategy rankings, returns, volatility profiles or hit rates were produced. All named strategy rows below are explicit hypotheses. The prior captured market dataset was not accessed, modified or rerun.

## What was actually tested

The initial laboratory ran 19 checks, with 12 passes and 7 unsatisfied assumptions/contracts. The failed checks are NOT seven proven production defects: centered pivots are legitimately retrospective when their availability is delayed, and the application already includes a safeguard for that delay. Tests execute inspected numerical helper bodies or clearly identified isolated branches, not a full deployed application or TradingView/Pine browser.

A second fixed test used 64 synthetic paths, each 512 bars long, seeds 0–63, and reported every seed. There was no profitability search or stock data. It found 30/64 paths with at least one bullish-crossover difference between implementations, 54 bar-level disagreements across 809 union-of-crossover bars and 27,840 common valid bars. No disagreement occurred after bar 300 in these fixtures. A shifted event can contribute two disagreeing bars; these are not trade counts or P&L impacts.

The maximum RSI discrepancy across these synthetic paths was 15.3186 points; the median per-path maximum was 5.2935. These include initialization. They must not be advertised as the error on any real healthcare stock.

### Recent signal sensitivity to the amount of supplied history

Comparisons below use the last 10 bars of each synthetic path against the full 512-bar calculation. Entries are paths with any recent bullish-cross discrepancy, out of 64.

| Supplied history | Application helper | Research helper |
|---|---:|---:|
| 90 bars | 5/64 | 5/64 |
| 120 bars | 2/64 | 1/64 |
| 200 bars | 0/64 | 0/64 |
| 400 bars | 0/64 | 0/64 |

Zero observed date disagreements does not mean numerical identity, full Pine parity, or a universal safe warm-up. A lower timeframe can look more stable simply because the same calendar history contains more initialization bars.

## Findings and their exact scope

### 1. Indicator identity is not yet a settled comparison contract

The research helper uses SMA-seeded Wilder RMA and recursive EMA. Application `engine.technicals.rsi` and `engine.signal_quality._ema` use pandas adjusted EWM conventions. The synthetic tests show these can change cross dates, especially with short histories. Neither implementation should silently be substituted for the other while claiming a faithful port.

The native indicator is RSI14 -> EMA14 minus EMA60 -> EMA5 signal, combined with StochRSI14/14/3/3. Price MACD12/26/9 is a separately labeled comparator. Native RSI-MACD is in oscillator units; dividing it by a dollar-price ATR is not the same construction as price-MACD/ATR. A past-only rank can express its unusualness without mixing units.

On a strictly increasing 120-price fixture, application RSI was undefined on all 106 post-seed observations while the research RSI returned 100. The research RMA also failed to recover after an internal missing observation. The latter is conditional on gaps actually reaching the helper; callers that sanitize them may avoid it. Both numerical implementations passed a future-tail perturbation check on the earlier indicator prefix.

### 2. Marker date, setup knowledge, settled quality and fill time are different

The older filtered research simulator records an i+1 fill after consulting a filter that may require i+2. A synthetic two-world counterexample reproduced the problem: the observations through the supposed fill were identical, but a later observation changed TAKE to BLOCK.

However, the current inspected application already implements `CONFIRM_BARS=2`, `confirmation_date` and tests forbidding marker-date grading. That owner must be reused. The two-bar delay also covers the right-side confirmation of centered swing highs, not just the counter-trend reclaim branch.

For a three-session candle, the marker label can precede its own close by two sessions. Two additional three-session buckets then add around six sessions before settled quality is available. A 1–3-session tactical entry therefore cannot use that eventual confirmation as though it existed at the initial intraday low.

### 3. A required bucket must be complete, not merely present

The isolated terminal-branch test returned February 18 for an illustrative confirmation bucket whose first session was February 18 and whose planned last session was February 20. Appending the remaining sessions changed the returned anchor to February 20. This is a conditional function-level counterexample, not a tested live failure. It applies if an incomplete required final bucket reaches the helper.

The needed invariant is: `eligible_at >= scheduled end of every required source bucket`, as well as all event/news availability times. Counting nonmissing rows is insufficient; the calendar defines the bucket, while missing observations affect data quality.

### 4. The inspected exit harness mixes its close grid and high/low grid

Its close series comes from session grouping, while highs/lows still use `resample("3B")` followed by a reindex. On a synthetic six-group calendar, five reindexed highs were missing and the remaining finite high belonged to a different group. That is a present source-composition problem.

It does not prove the originally archived exit study used this same inconsistent revision. Do not use this audit to declare previously rejected trailing-stop or regime-router ideas validated. The old negative evidence remains evidence; a faithful reconstruction would need the original source/data/version bundle.

A second exit-policy detail also deserves explicit definition: a "high since entry" initialized from the entire entry candle includes prices printed before a close-of-candle fill. That can be a deliberate reference policy, but it is not literally a post-entry high.

### 5. Weekly gating is a separate parity question

The research implementation and application use different weekly mapping conventions. One uses the last weekly close before the setup candle's close; the other shifts weekly state and aligns it to an open-date label. A controlled Monday-to-Wednesday example disagreed. Which is correct requires the exact intended Pine `request.security` configuration, not an assumption that a shift always removes repainting.

## Why the best timeframe is partly a memory-length question

With a 390-minute regular session, literal grids have final short candles. EMA60 has half-life ln(0.5)/ln(59/61) = 20.79 bars. Counting each retained short candle as one bar produces:

| Grid | Candles/session | EMA60 half-life, approximate sessions |
|---|---:|---:|
| 1h | 7 | 2.97 |
| 2h | 4 | 5.20 |
| 3h | 3 | 6.93 |
| 4h | 2 | 10.40 |

This is the linear EMA component, not the full nonlinear RSI-MACD's total response. It is an analytical clock calculation, not a market-performance result.

Therefore compare both literal chart settings and approximately matched physical memory. Use equal-session partitions such as 130-minute and 195-minute candles as clock-artifact controls, not more opportunities to mine an impressive winner. Do not drop short candles silently, mix regular and overnight sessions, or manufacture 30-minute history from hourly OHLC.

## Candidate strategy definitions

These are frozen starting hypotheses for future evaluation. Their numeric thresholds are not optimized results. No trade authorization or production algorithm change is implied.

### Trend pullback

Use a contemporaneously constructive daily context, a pullback to a predeclared setup-timeframe reference, and a structural execution trigger. The price-only draft requires two confirmed one-bar-right-side swing lows, a higher second low, and a subsequent completed close above the intervening neckline. The neckline is fixed once the second pivot becomes knowable. Enter only after that information exists.

Add rising native RSI-MACD histogram as an ablation, not an assumed improvement. Test StochRSI separately. Do not force every trend entry to wait for RSI<30 or retroactively restrict the sample to setups that later received a multi-day TAKE label.

### Sweep and reclaim

Define support from the preceding 20 completed setup bars, excluding the candidate bar. A low below that reference followed by a close above it creates the setup. The draft trigger is a subsequent completed execution close above the sweep candle's high, with no intervening break of its low. A next-bar hold is a distinct delayed policy; it cannot be backdated to the sweep.

### Event-base repair

Define the event and timestamp before selecting a chart anchor. A test definition can include a known material announcement or a gap of at least two pre-event ATRs. Fix a first completed regular-session range and an event-anchored VWAP. Compare immediate acceptance versus a subsequent retest. Do not exclude failed events after seeing that they never recovered.

A trade-level VWAP and a typical-price-times-volume bar proxy are not interchangeable; the proxy must be disclosed. The last trade, a bid/ask midpoint, a regular-session candle and an overnight executable quote also have different meanings.

## The five priority stocks

The rows below are conditional hypotheses, not measured permanent personalities or statements about today's charts.

### JNJ

**First comparison:** 4h vs 2h setup; 60m execution.

**Primary family:** Shallow trend pullback. **Separate alternative:** Failed range breakdown and reclaim.

**Question:** Does price acceptance add more than forcing a deep oversold oscillator reading?

**Special constraint:** A persistent uptrend would make repeated oscillator-top exits expensive; test that cost, do not assume the trend exists.

**Falsifier:** Reject the shallow-pullback hypothesis if it does not improve adverse excursion and opportunity capture versus the price-only entry.

**Top/exit assessment:** Keep the incumbent exit during entry comparisons; quantify premature exit followed by re-entry cost.

### LLY

**First comparison:** 2h vs 4h setup; 30m vs 60m execution.

**Primary family:** Trend reset with a confirmed higher low. **Separate alternative:** Breakout retest.

**Question:** Does a shallow momentum reset enter strong continuation episodes better than waiting for deep daily oversold?

**Special constraint:** Do not pool routine pullbacks with materially negative announcement gaps.

**Falsifier:** Reject the faster trigger if apparent price improvement is outweighed by stop-outs, execution cost or missed delayed confirmations.

**Top/exit assessment:** Distinguish extension from failure; test profit protection without assuming every RSI extreme is a top.

### ABBV

**First comparison:** 2h vs 4h; 3h diagnostic challenger setup; 30m vs 60m execution.

**Primary family:** Preidentified support acceptance. **Separate alternative:** Range sweep and reclaim.

**Question:** Does the additional hold/retest reduce false entries enough to compensate for paying a later price?

**Special constraint:** Separate ex-dividend price mechanics, ordinary consolidation and event-related repricing.

**Falsifier:** Reject an extra oscillator filter if the same structural entries perform equivalently without it under matched opportunities.

**Top/exit assessment:** Test failed breakout plus support loss; keep risk warnings separate from mechanical sells.

### MRK

**First comparison:** Daily context; 4h vs 2h setup; 60m execution.

**Primary family:** Base repair in weak structure. **Separate alternative:** Ordinary trend pullback in constructive structure.

**Question:** Can a tradeable local repair be identified without claiming the larger downtrend has ended?

**Special constraint:** A local bounce and a durable reversal are different labels; no automatic claim that MRK is currently weak.

**Falsifier:** Reject repair entries that mostly fail below overhead resistance or only appear good after conditioning on a later recovery.

**Top/exit assessment:** Treat overhead supply as an exit-reference candidate, not an automatic permanent price target.

### UNH

**First comparison:** Daily context; 4h vs 2h after stabilization setup; 60m execution.

**Primary family:** Post-event base acceptance. **Separate alternative:** Non-event structural pullback.

**Question:** Can acceptance above an event-defined reference distinguish durable repair from a reflex bounce?

**Special constraint:** Use a pre-event risk ruler as well as live ATR; a shock must not make the same dollar risk look artificially smaller.

**Falsifier:** Reject the event-repair variant if its edge disappears when all qualifying shocks, including never-recovered cases, are included.

**Top/exit assessment:** Keep gap exposure distinct from stop distance; do not infer a guaranteed stop fill.

## Remaining stock-by-stock research matrix

| Stock | Setup → execution candidates | Main test and falsifier |
|---|---|---|
| AMGN | 2h vs 4h → 60m | Does the pullback rule generalize beyond a small number of event episodes? Reject an advantage driven by one episode or one extreme gap. |
| GILD | 2h vs 4h → 60m | Does momentum add information after location and acceptance are already required? Reject redundant momentum votes with no incremental out-of-sample effect. |
| PFE | Daily/4h vs 2h → 60m | Does local structural recovery justify an entry before long-term averages recover? Reject bounce entries that cannot overcome nearer overhead resistance. |
| BMY | Daily/4h vs 2h → 60m | Does reclaim acceptance improve entry quality beyond an oversold crossover? Reject results dominated by exposure reduction or a single repricing. |
| ABT | 4h vs 2h → 60m | Does a slower trigger reduce adverse excursion without losing too much move capture? Reject extra confirmation if it merely chases the same move at a worse location. |
| MDT | 4h vs 2h → 60m | Which entry family matches observed structure in the training period? Reject family selection that reverses in held-out periods. |
| TMO | Weekly/daily context; 4h vs 2h → 60m | Does longer-context repair distinguish sustained recovery from short bounces? Reject gains that vanish after shared-cycle episodes are grouped together. |
| DHR | Weekly/daily context; 4h vs 2h → 60m | Does the TMO-derived hypothesis survive on this held-out name? Reject a supposed cross-stock validation that is only one common sector episode. |
| ISRG | 2h vs 4h → 30m vs 60m | Does a faster trigger capture a higher low without multiplying shake-outs? Reject the faster entry if benefits disappear after spread/slippage and failed setups. |
| SYK | 2h vs 4h → 30m vs 60m | Does the same growth-pullback construction transfer from the diagnostic names? Reject an isolated best parameter with poor neighboring settings. |
| BSX | 2h vs 4h → 30m vs 60m | Does price acceptance outperform a stand-alone StochRSI cross? Reject increased churn without a lower adverse-excursion distribution. |
| VRTX | Daily/4h; 2h challenger → 60m | Does the technical setup retain value outside binary-event windows? Reject a rule whose success requires retrospectively excluding bad events. |
| REGN | Daily/4h; 2h challenger → 60m | Does an event-reference reclaim improve outcomes across multiple unrelated events? Reject performance dominated by one catalyst or one reversal. |
| ELV | Daily/4h → 60m | Does the UNH event-repair hypothesis transfer to another payer-related name? Reject an effect that disappears under leave-one-event-out checks. |
| CI | Daily/4h → 60m | Does the shared rule survive a different business mix? Reject a peer filter that merely restates the stock through a heavily self-weighted benchmark. |
| CVS | Daily/4h → 60m | Does repair acceptance help across distinct company-specific and group-wide episodes? Reject a strategy that only works after the successful recoveries are selected. |
| HCA | Daily/4h → 60m | Does the rule work without importing insurer economics into hospital behavior? Reject validation based only on pooled healthcare returns. |
| ZTS | 4h vs 2h → 60m | Does the general family transfer outside the main drug/device/payer clusters? Reject isolated ticker tuning unsupported by the shared family. |

## Stock personality should be measured, not narrated

Before assigning an archetype, describe its rolling trend efficiency, distribution of pullback depth, gap contribution, event-conditioned recovery, relative strength and exit/re-entry cost. Report uncertainty and change over time. Company identity is a prior, not proof of a permanent trading process.

For cross-stock normalization, use price volatility for price quantities, oscillator ranks for oscillator quantities and spread/volume measures appropriate to time of day. A daily ATR estimated after a large gap is a different ruler from the one available before the announcement. In the arithmetic fixture, a prior ATR of 2 becomes 3.2857 after a true range of 20 under ATR14. The same price distance of 6 then looks like 1.826 ATR rather than 3 ATR; the dollar exposure did not shrink.

The peer benchmark should not merely echo the stock. For a simple fixed-weight one-period benchmark, excluding the subject has return approximately `(benchmark_return - prior_weight * subject_return)/(1-prior_weight)`. This is an arithmetic approximation, not a replacement for a properly maintained point-in-time peer basket. Using current ETF weights historically would introduce another error.

## Independent evidence, not indicator vote counting

RSI, StochRSI and RSI-MACD are related transformations. Three agreeing oscillators are not three independent probabilities. Use location, momentum, price acceptance, participation and event context as separate candidate evidence families. Even those families can be correlated; their incremental value must be tested.

The ablation order is price/location/acceptance only; add native histogram; test StochRSI separately; add peer-relative context; then add time-of-day-adjusted participation. Do not build a huge Cartesian grid of thresholds before the price-only baseline is understood. A complex rule loses to the simpler baseline if its apparent benefit disappears after matched opportunity/exposure or realistic costs.

## How to evaluate bottoms and tops without future selection

A retrospective pivot can be an outcome label, but cannot decide which trades were eligible in the past. Freeze the swing magnitude, horizon and tolerance before evaluating candidates. Report distance from a later pivot in ATR units, entry delay, adverse excursion, shake-out frequency and the share of qualified opportunities missed. Include all raw eligible setups, including those that never develop into a later confirmed signal.

A paired lead study on moves that eventually received a baseline signal answers a conditional question: how early was the candidate on those eventual baseline moves? It does not answer how the live candidate performs across all its extra false starts. Retain the descriptive lead analysis, but do not mistake its conditioning for an executable selection policy.

For exits, keep entries fixed. Keep the incumbent mechanical exit during entry experiments. Test warnings, actual sells and short entries separately. Maximum favorable excursion is not realized profit. A post-entry high must not include an earlier high from the same candle unless the policy intentionally says so. Intrabar target/stop order must be resolved by finer data or conservative handling; the same OHLC can encode opposite outcomes.

## Validation and promotion rules

The initial literal clock study has 18 shared cells: three entry families, three setup clocks and two execution clocks. Fix indicator lengths. Select within training, not from the final test. Record all tried rules and rejected variants. More complicated per-ticker fitting must earn its place over pooled/archetype rules.

Use chronological and leave-stock/leave-event-out evaluations. Diagnostic names such as JNJ and LLY are not pristine holdouts simply because a new script is used. A previously inspected historical period is retrospective evidence, not a truly untouched test. A final forward observation period remains necessary; no autonomous forward monitor has been started by this report.

Purge training episodes whose outcome windows overlap validation/test. Set the embargo from the actual outcome/holding horizon. Preserve entire date/event blocks and correlated stock observations when estimating uncertainty. Fifty correlated signals in one sector episode are not fifty independent confirmations. Use matched opportunities, exposure and exits to distinguish better entry location from merely trading less.

Report net expectancy in units of the declared initial risk together with tail losses, drawdown, opportunity recall and capital occupancy. Do not choose a winner solely from win rate or total return. An illustrative 18 wins in 24 independent trades gives a Wilson 95% interval of approximately 55.1%–88.0%, despite the apparent 75% hit rate; dependence can make the evidence weaker still. Eight wins in eight observations do not demonstrate certainty: the corresponding lower Wilson bound is about 67.6%.

Costs require actual execution assumptions: entry spread, adverse opening gaps, delayed fills, nonfills, exits, financing/borrow when relevant and simultaneous-position constraints. A stop price is a trigger, not a guarantee of the fill price. No trade sizing or orders are generated here.

## What would qualify as a stock-specific winner

A candidate must improve the intended entry-risk/efficiency outcomes against the simple baseline on held-out opportunities, retain acceptable net expectancy and opportunity capture, survive nearby parameter and period checks, and not depend on a single announcement or common market episode. Its indicator and timestamp identity must match the prospective consumer. An inconclusive stock is labeled INSUFFICIENT EVIDENCE rather than assigned a fabricated best clock.

## Deliverables and scope boundary

`audit_lab.py`, `stress_math.py` and `boundary_checks.py` are reproducible independent synthetic diagnostics. Their JSON/CSV outputs contain the exact results and scope limitations. `strategy_spec_v2.json` and `stock_candidate_matrix.csv` are untested candidate specifications. No production source was modified. The prior host analysis was neither repaired nor rerun, and no worker, watcher or trading operation was created.

Remaining work is actual canonical/Pine and full-consumer boundary validation plus permitted causal market-data evaluation. The original host denial still constrains its affected actions. This report is not a claim that market-strategy discovery is complete.

## Source references

These references support the inspected constructions and methodology; they do not supply unmeasured healthcare strategy results.
- [Native research confluence](https://github.com/mastermindx-market-intelligence/macro/blob/b29ba7102d35bebf6f322c1d6fadf8309726bf4e/research/signal_engine/confluence.py)
- [Application numerical helpers](https://github.com/mastermindx-market-intelligence/macro/blob/b29ba7102d35bebf6f322c1d6fadf8309726bf4e/engine/technicals.py)
- [Application signal quality and confirmation owner](https://github.com/mastermindx-market-intelligence/macro/blob/b29ba7102d35bebf6f322c1d6fadf8309726bf4e/engine/signal_quality.py)
- [Existing no-leak guard tests](https://github.com/mastermindx-market-intelligence/macro/blob/b29ba7102d35bebf6f322c1d6fadf8309726bf4e/tests/test_signal_quality_no_leak.py)
- [Historical filtered simulator](https://github.com/mastermindx-market-intelligence/macro/blob/b29ba7102d35bebf6f322c1d6fadf8309726bf4e/research/signal_engine/test_buyfilter.py)
- [Historical filter](https://github.com/mastermindx-market-intelligence/macro/blob/b29ba7102d35bebf6f322c1d6fadf8309726bf4e/research/signal_engine/diagnose_v2.py)
- [Exit harness](https://github.com/mastermindx-market-intelligence/macro/blob/b29ba7102d35bebf6f322c1d6fadf8309726bf4e/research/signal_engine/diagnose_v5_exits.py)
- [Signal engine charter](https://github.com/mastermindx-market-intelligence/macro/blob/b29ba7102d35bebf6f322c1d6fadf8309726bf4e/research/signal_engine/CHARTER.md)
- [Confluence tuning and limitations](https://github.com/mastermindx-market-intelligence/macro/blob/b29ba7102d35bebf6f322c1d6fadf8309726bf4e/research/signal_engine/CONFLUENCE_TUNING.md)
- [pandas EWM definitions](https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.ewm.html)
- [TradingView higher-timeframe requests and repainting](https://www.tradingview.com/pine-script-docs/concepts/other-timeframes-and-data/)
- [NYSE trading hours](https://www.nyse.com/trade/hours-calendars)
- [NIST Wilson confidence intervals](https://itl.nist.gov/div898/handbook/prc/section2/prc241.htm)
- [Bailey et al., Probability of Backtest Overfitting](https://papers.ssrn.com/sol3/Papers.cfm?abstract_id=2326253)
- [SEC investor bulletin on stop orders](https://www.investor.gov/introduction-investing/general-resources/news-alerts/alerts-bulletins/investor-bulletins-15)
- [Canonical research issue](https://github.com/mastermindx-market-intelligence/macro/issues/8718)