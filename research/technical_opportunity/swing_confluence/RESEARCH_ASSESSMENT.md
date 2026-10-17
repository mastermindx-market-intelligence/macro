# Research assessment: entry confluence, oscillations and rates

**Date:** 2026-10-07 America/New_York. **Status:** research design and literature assessment, not an empirical Mastermind strategy result. No equity return study, chart-outcome inspection or market-data acquisition was performed in this slice. Numbers in the recipe are outcome-blind planning assumptions.

## Recommendation

Build a reusable **conditional entry experiment** inside the existing Strategy Lab, not an indicator optimizer detached from the investor's decision. Treat the daily stock state as context, a slower intraday view as setup, and a faster view as a trigger. Preserve a no-entry outcome. Run leader-pullback continuation and range reversal as different hypotheses; do not force a common oscillator or universal timeframe.

The first comparison should be 30m/120m and 30m/180m against simpler single-clock controls and session-aware alternatives. This is a sensible starting design because it directly tests the commission, not evidence that either pair wins. A narrow stable region of settings that survives unseen issuers and periods is preferable to a spectacular isolated winner. A fixed multiscale combination that performs as well as adaptive selection defeats the case for a per-stock selector.

The current deliverable compiles saved configurations and makes missing dependencies visible. It does not yet connect those configurations to a qualified intraday evaluator or production UI.

## 1. What to call a good entry

There are two consumer objectives, and they must not share a single misleading leaderboard.

**Standalone short swing:** Does timing improve net expectancy for the same eligible setups, after spread, slippage, turnover, gap risk and opportunity cost? Compare 1/2/3/5/10-session caps, not an assumed holding period. Measure entry-to-invalidation excursion, forward progress, false starts and time to progress as well as return. The 1-3-session and 5-10-session cases may represent different mechanisms; a pooled average cannot determine which to trade.

**Acquiring a position already desired:** Does waiting for the trigger improve the acquisition price or early drawdown versus a declared immediate or scheduled entry policy? Count unfilled and late entries, including a rally that never offers a pullback. Reporting only successfully filled dips is a selection bias. Keep the desired exposure and comparison deadline fixed; stock selection and timing are separate decisions. This acquisition objective is a later separately registered endpoint, not silently added to the included swing matrix.

An exact bottom is visible only after later prices occur. The research target is an actionable tradeoff between earlier price and more confirmation. A hindsight low may label an event for evaluation, but its timestamp cannot be backdated into a tradable signal. TradingView's official documentation demonstrates how unconfirmed higher-timeframe values repaint, and how improperly requested higher-timeframe values can leak future data [S1]. This makes actual information availability more important than a convincing chart.

## 2. Two setup families

### Leader pullback continuation

Use the existing point-in-time RS/leadership and setup-species owners to identify eligible leaders before the entry. Candidate context is a still-intact longer-term trend, relative strength against market/sector, and a pullback rather than an already-broken trend. Avoid choosing today's successful leaders as the historical test universe.

A candidate setup is slowing downside movement toward a causally defined support region, followed by a lower-timeframe reclaim or a new higher low that was genuinely confirmed by then. Test structure alone first. Add one momentum family, then participation, as separately accounted contrasts. Examples such as RSI reset, MACD-histogram turn or stochastic recovery are candidate alternatives, not three independent confirmations. Exact formulas, lookbacks, support anchors and confirmation thresholds must be taken from or registered through existing owners before the return study.

The important counterfactual is not buy-and-hold alone. It is the same eligible pullback entered without the proposed timing rule, plus lower-timeframe-only and fixed-multiscale controls. A filter that avoids losing setups but misses every large rebound must disclose that tradeoff.

### Range reversal

Use a trailing-only range-state definition. Test lower-boundary proximity and rejection against simple range proximity without timing. A possible target is the middle or opposite side of a range, but range-target exits are not included in the present two-exit matrix; adding them consumes a separately registered extension.

An economically cyclical company and an oscillating share price are different concepts. A bank can trend for months; a technology leader can trade sideways. Classification needs price-state and business/exposure fields separately. Treat trend breaks, earnings gaps, volatility expansion and an unstable range as contradiction or abstention candidates, not exceptions silently removed after losses.

## 3. Why changing the timeframe can appear to help

Separate four changes: bar grain, session/anchor, indicator memory and source/adjustment basis. Fourteen 30-minute observations and fourteen 180-minute observations do not contain the same history. A successful change may be slower smoothing rather than a genuine cycle at the new grain. Use both fixed-bar-count and fixed-physical-memory controls from the existing Temporal Grain implementation.

For the explicitly declared 390-minute session example, 120-minute bars create three full buckets and a 30-minute terminal bucket; 180-minute bars create two full buckets and a 30-minute terminal bucket. 130-minute and 195-minute partitions divide that example evenly. This is arithmetic, not evidence that either alternative predicts better, and not an exchange-calendar implementation. Actual early closes, DST, missing rows, vendor anchors and reporting delay still require the existing clock owner's proof.

Only completed and available higher-timeframe observations may inform the faster trigger. A 30-minute trigger cannot use the eventual closing value of a three-hour bar that has not finished. No forward fill may cross an unavailable observation or silently substitute a later correction. The source panel must also distinguish current split-adjusted history from the history available at the old decision time.

## 4. Rates and events: a promising conditional hypothesis, not a clockwork law

There is primary empirical support for researching event-conditioned price behavior, but none of the following establishes the requested single-name swing strategy.

**Auctions:** Fleming, Liu and Nguyen's New York Fed Staff Report 1188, issued March 2026 and revised July 2026, uses 33 years of intraday Treasury data. It reports higher yields ahead of auctions and reversal afterward, with stronger pressure under tighter dealer risk-bearing constraints and net order flow important to transmission [S2]. This concerns Treasury securities, not stock pullback lows. The equity extension is a new hypothesis: does an observed relief in rates improve an already-armed equity entry, conditional on that stock's prior rate exposure?

**Macro news:** Andersen, Bollerslev, Diebold and Vega find state-dependent responses to macroeconomic surprises in high-frequency stock, bond and currency futures [S3]. The same class of news need not imply the same equity direction across economic states. The design should therefore distinguish a discount-rate relief scenario from weakening expected cash flows rather than encode falling yields as universally bullish.

**FOMC:** A New York Fed update of pre-FOMC drift found that the 2011-2018 pattern differed from the 1994-2011 evidence and was concentrated in press-conference meetings in the later sample [S4]. This is historical evidence of instability, not a current calendar trading rule. The San Francisco Fed provides raw and orthogonalized monetary-policy surprise series derived from announcement-window futures changes [S5]. These are post-announcement explanatory observations; they cannot be used to select a pre-announcement entry. Historical download availability and real-time predictor availability are different questions.

**Different stocks:** A 2025 Federal Reserve study finds heterogeneous bank-equity responses to monetary-policy shocks across balance-sheet characteristics [S6]. This motivates exposure-aware analysis but does not establish a generic financial-sector or single-name rule. Estimate exposure using training-only data, allow shrinkage toward group estimates, and report instability; do not assign a permanent rate beta from a full-sample regression.

Auction announcements, competitive results and security issuance are distinct events. TreasuryDirect describes separate announcement, auction and issue steps, and warns that typical scheduling patterns may change [S7]. Use actual historical announcements and timestamps through the existing event owner. A calendar label alone is not a demand surprise. An auction tail requires a comparable when-issued yield immediately before the result; absent that input, the test must remain calendar-only.

### Proposed rate/event contrast

Keep the technical rule frozen and compare: technical only; technical plus pre-known calendar context; technical plus prior rate state; and, separately, a post-release strategy using surprises that were already observable. The latter is not the same strategy as anticipating a release. Include earnings, overlapping macro releases and market/sector controls. Separate FOMC statement, projections, press conference, minutes and major speeches where the source supports their exact historical timing. Daily yields cannot resolve the minute-by-minute order of an intraday rate reversal and stock entry.

The scientific question is **incremental usefulness**: does rates/event context improve the same technical opportunity policy out of sample, and in which exposure groups? Predictive success would not by itself prove that rates caused the equity pivot.

## 5. Can the apparent waves be generalized?

Start with the possibility that the pattern is transient or not real. Estimate any oscillation descriptors on trailing data through Stock Identity/Temporal Grain, not by fitting a sine wave to the entire chart. Distinguish a stock-specific oscillation from a shared market/sector move, a repeated time-of-day liquidity pattern, and a reaction to scheduled information.

For mechanism diagnosis, compare against matched-time controls and suitable nulls that preserve volatility clustering, overnight structure and cross-sectional co-movement. Any surrogate or detrending choice itself belongs in the registered research family. Test whether a proposed phase survives time shifts and new securities without re-selecting its favorite clock. If a phase exists only after centered smoothing, or disappears after controlling common exposures, reject the original timing interpretation.

A small number of macro events remains a small sample even when hundreds of stocks trade on each event. Use event/date-aware inference and calendar-time blocks, not independent-trade standard errors. Purge overlapping forward labels at fold boundaries. Select parameters inside training/validation, then reveal an untouched time-and-issuer confirmation set once.

Bailey and Lopez de Prado's Deflated Sharpe Ratio work explicitly addresses performance inflation from selection across many tests and non-normal returns [S8]. Reuse the existing TrialLedger/Evaluation OS, preserving failed variants and chart-guided changes. The planner's 8,640 conservative comparisons are not 8,640 independent trials and not a completed ledger; the owner must reconcile actual looks and dependence. Do not choose an ad hoc effective-trial count that makes the winner pass.

## 6. Chart inspection protocol

After source and outcome-access qualification, sample chart episodes before judging their appearance. Use the existing Terminal renderer with matched clocks and data vintage. For each case, hide future bars at the decision point, record eligibility, setup, trigger, available-at time and invalidation, then reveal the outcome. Include winners, false starts, missed rebounds, range breaks and unavailable-data cases. Separate exploration charts from confirmation charts; every exploration-led rule change spends a new look. Screenshots are supporting diagnostics, never a substitute for the event-level evaluation denominator.

## 7. Completion and rejection criteria

A useful result may be a broadly stable clock band, two family-specific policies, superiority of a simple fixed-clock baseline, or no supported entry advantage. No rule should be promoted merely because it has the best in-sample Sharpe or looks closest to past lows.

The full requested capability is complete only when a saved recipe runs through admitted data and canonical indicators/evaluation, produces reproducible comparisons and truthful failure states, opens the exact same episodes in the existing chart UI, and survives independent review plus the relevant untouched/prospective proof. This slice does not meet that full completion standard.

## Primary references

[S1] TradingView, Pine Script documentation, Repainting; accessed 2026-10-07. https://www.tradingview.com/pine-script-docs/concepts/repainting/

[S2] Fleming, Michael J., Weiling Liu and Giang Nguyen (2026), Intraday Price Pressure and Order Flow Around U.S. Treasury Auctions. Federal Reserve Bank of New York Staff Reports 1188, revised July. https://www.newyorkfed.org/research/staff_reports/sr1188.html

[S3] Andersen, Torben G., Tim Bollerslev, Francis X. Diebold and Clara Vega (2005; published 2007), Real-Time Price Discovery in Stock, Bond and Foreign Exchange Markets. NBER Working Paper 11312; Journal of International Economics 73, 251-277. https://www.nber.org/papers/w11312

[S4] Lucca, David O. and Emanuel Moench (2018), The Pre-FOMC Announcement Drift: More Recent Evidence. New York Fed Liberty Street Economics, November 26. https://libertystreeteconomics.newyorkfed.org/2018/11/the-pre-fomc-announcement-drift-more-recent-evidence/

[S5] Federal Reserve Bank of San Francisco, Monetary Policy Surprises data and methods, updated series based on Bauer and Swanson (2023); accessed 2026-10-07. https://www.frbsf.org/research-and-insights/data-and-indicators/monetary-policy-surprises/

[S6] Ehresmann, Paige, Juan M. Morelli and Jessie Jiaxu Wang (2025), What Do Bank Stock Returns Say About Monetary Policy Transmission? FEDS Notes, August 4. https://www.federalreserve.gov/econres/notes/feds-notes/what-do-bank-stock-returns-say-about-monetary-policy-transmission-20250804.html

[S7] TreasuryDirect, How Auctions Work; When Auctions Happen; accessed 2026-10-07. https://www.treasurydirect.gov/auctions/how-auctions-work/ ; https://www.treasurydirect.gov/auctions/when-auctions-happen/

[S8] Bailey, David H. and Marcos Lopez de Prado (2014), The Deflated Sharpe Ratio: Correcting for Selection Bias, Backtest Overfitting, and Non-Normality. Journal of Portfolio Management 40(5), 94-107. https://doi.org/10.3905/jpm.2014.40.5.094
