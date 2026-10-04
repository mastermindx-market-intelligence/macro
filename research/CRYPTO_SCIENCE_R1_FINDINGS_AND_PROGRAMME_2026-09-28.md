# Crypto science R1 — actual model audit, findings and research programme

**Date:** 2026-09-28. **Parent:** WS:CRYPTO-INTELLIGENCE / Macro PR #8050. **Operation:** crypto-vector-r2-20260926-sol-001. **Status:** research begun; no new trading edge or production strategy accepted.

## 1. Executive decision

The scientific core is now an active part of the Crypto/Vector commission, not a later decorative enhancement. The product must distinguish an approaching selloff, a selloff already in progress, a washout that is still dangerous, an executable recovery, a durable trend and an exhausted cycle. These are different prediction and decision problems. Their signal speed, acceptable false-alarm rate and financial consequences differ.

The first completed work is a source and temporal-integrity audit, not a parameter search. It found two reproducible problems: the bottom-pressure history is not prefix-invariant on three dates in the declared year; and the existing impulse evaluator converts outcome-unavailable tail rows into negative labels. These findings justify repairing the research baseline before trusting an apparently better high/low detector. They do not establish that a live trade was wrong, that all historical performance is inflated, or that the current market should be sold.

The product objective is precise, falsifiable decision support: earliest defensible warning time, explicit invalidation, documented expected loss and upside forgone, calibrated uncertainty when supportable, and abstention when evidence is inadequate. Exact hindsight highs/lows are not attainable fills. A model can be useful without guessing every extreme, and an attractive extreme-calling chart can be useless if it repaints or assumes impossible execution.

**Authority remains unchanged:** BitcoinDecisionState is the final model-allocation owner; the Crypto class budget consumes that decision. This research has not changed engine code, configuration, source data, live alerts or trades. Model promotion requires a separate evidence-backed review and existing policy acceptance.

## 2. Evidence identity and completed work

Protected Mastermind source: `5c6b010a6157895d4f697548c75263cdff641ea6`; Skillpack 1.0.1/bootstrap 1. Baseline Macro branch: `0c252f0befaa0891a9666949835cab8e9d27f3ba`. Observed main: `03e8961d22b48cc65666f6318ee8c8bd610f3caa`. The principal BTC signal/input/override/radar sources and config were byte-identical across those two refs at inspection. This is repository parity, not deployed attestation.

The experiment specification was committed **before** new calculations at `47d4eacf6abd98055a085a779e9df75fee567d18`: `research/CRYPTO_SCIENCE_R1_AUDIT_PREREG_2026-09-28.md`. Derived evidence and executable audit are under `research/crypto_science/`. Eleven input files and seven principal source files were hashed before and after the audit; all remained unchanged. Complete cutoff results, not just selected examples, are retained.

### 2.1 Preregistered prefix test

Test: recompute each feature using only observations through date t; compare its value at t with the value assigned to t when later observations are included. A difference is unacceptable for a feature presented as a non-repainting historical decision input. A pass proves only this timing property, not historical publication availability or predictive power.

Window: every one of the final **366 daily dates**, 2025-09-26 through 2026-09-26. Tolerance: 1e-12. No dates were selected by profitability or proximity to a famous bottom.

| Tested path | Dates differing | Maximum absolute difference |
| --- | ---: | ---: |
| Incumbent bottom_pressure | 3 / 366 | 0.0930233 on its 0–1 scale |
| Research-only completed-date 72h counterfactual | 0 / 366 | 0 |
| Price-only momentum control | 0 / 366 | 0 |
| Price-only risk control | 0 / 366 | 0 |

The three incumbent differences are:

| Date | Full-history value | Prefix-only value | Full minus prefix |
| --- | ---: | ---: | ---: |
| 2026-05-20 | 0.2093023 | 0.1162791 | +0.0930233 |
| 2026-05-21 | 0.2790698 | 0.1860465 | +0.0930233 |
| 2026-07-01 | 0.3488372 | 0.4418605 | −0.0930233 |

The mechanism is the three-day StochRSI input in `btc_signals.bottom_pressure`: `c.resample("3D").last()` followed by forward filling. A default left-labeled bucket may put a later close at its beginning. A six-day synthetic illustration assigns the Jan-3 close of 20 to the Jan-1 label. This is a data-time bug, not a discovery about markets. Pandas documentation explicitly warns that resampling labels can pull later information backward [P1].

Holding stored momentum, risk, valuation and the earlier history fixed, the prefix-only bottom-pressure values changed one day's raw allocation in each of four variants by up to **5.3156 percentage points**. This is an isolation/sensitivity diagnostic. It did not recompute the whole signal stack or override history, calculate PnL, establish a live execution error, or quantify net economic harm. The sign can go either way: do not call every look-ahead defect profit inflation without measuring it.

**Technical amendment:** the initial counterfactual used explicit `origin` with `3D`; pandas 3.0.5 warned that this origin is ignored for a non-Tick frequency. The initial script, output and CSV are retained. A documented, post-result technical amendment substituted `72h`, with unchanged origin/right-closure/right-label convention and all test dates. The single rerun reproduced the same result, without that warning. Python 3.14.7, pandas 3.0.5 and NumPy versions are recorded. Neither counterfactual is a deployed fix or a profit-optimized choice of bar anchor.

### 2.2 Exploratory impulse-label boundary audit

This second check arose while tracing a contradictory historical report, after the preregistered audit. It is explicitly **exploratory**, not retroactively preregistered.

`VECTOR_IMPULSE_PREDICTION.md` retains an incorrect old snippet, `close.shift(-1).rolling(3).min()`, annotated as the next three closes. In fact, at t it includes the prior/signal bars and reaches only one step forward. The current `btc_impulse_radar_backtest._labels` already uses a forward indexer, so that old-window bug is **not** being attributed to the present implementation.

However, the current function returns ordinary boolean comparisons of future extrema. In an eight-row monotonic toy series, only five three-day outcomes have matured, but the last three undefined outcomes become `False`, and `label.notna()` accepts all eight rows. Both up/down tails are affected. Consequently, downstream masks can count immature observations as completed negative events. The reproducible JSON is `r1_label_boundary_exploratory.json`. No falsifier gate was written or strategy demoted by this audit.

The repair requirement is to preserve a separate maturity/availability mask or nullable target through all evaluation functions. Recompute affected metrics after repair; do not assume a small number of tail rows can never affect a thin holdout or a near-threshold decision.

### 2.3 What remains unproven after these tests

The 366-day prefix check is not an all-history or all-feature audit. The controls exclude non-price inputs. Provider revisions, release delays, partial candles, missing bars, source splices, point-in-time asset universes and older model configurations remain separate questions. The new results do not establish predictive accuracy, causal market drivers, forecast calibration, post-cost alpha or production readiness.

## 3. What the incumbent model actually does

The current engine is not empty or simplistic. It has a substantial daily signal library, an impulse radar, leverage context and real order-flow collection. The immediate need is to separate their roles and test how much independent information each adds.

**Momentum** combines EMA trend/cross, MACD histogram, SMA200, 20-day return, RSI zones, SOPR momentum and short-term-holder cost basis. Current config weights eight votes equally, smooths over three days and uses confirmation/hysteresis. Several price votes are transformations of the same price history: eight votes are not eight independent sources of confidence.

**Risk** combines downside volatility percentile, 90-day drawdown, SOPR stress, the interday/intraday volatility relationship, deteriorating momentum, ETF outflows and absolute funding extremes. Current high-risk entry is at 25; exit is below 15. Those are policy thresholds on a composite, not 25% or 15% crash probabilities. Some legs describe damage or stress already occurring; their predictive increment needs separation from current-price momentum.

**Raw sizing** begins with a momentum/risk grid. The optimal variant targets full exposure above momentum 0.5 and below risk 25, half above momentum 0 and below risk 50, otherwise zero, before overlays. Valuation can add a floor or cap; conviction changes size; a path-dependent brake tightens after strategy drawdown; bottom pressure can add exposure after that brake. The ordering matters: a contrarian bottom overlay can add risk in the same stressed environment in which the brake reduces it. That is not automatically wrong, but it needs an ablation of both loss protection and recovery capture.

**Overrides and final authority** are separate from raw sizing. Current config explicitly retires the midterm calendar blackout and disables its gate. Historical calendar narratives must not regain authority through stale documents. We will compare raw and final contemporaneous paths, not fit a new model around an obsolete veto.

**Impulse radar** is already the home for shorter-lived pressure: DVOL-range jumps, profit-taking SOPR spikes, capitulation SOPR lows and context-only crowding/flow legs. Its up/down gauges are not probabilities. The current U1 definition requires a low SOPR z-score after price has already fallen at least 5% in five days: it is a post-washout bounce hypothesis, not a pre-crash or general pre-rally oracle. Existing alert eligibility is not authority to set portfolio size.

**Redundant confirmation:** the input layer derives NUPL as `1 - 1/MVRV`. These two must not be counted as independent confirmation in a new learner. Group features by information origin; test a block's incremental value after existing price and valuation information, not simply how many indicators agree.

## 4. Prior research that constrains this programme

These are **prior report findings**, not newly reproduced market statistics:

- `BTC_REENTRY_TRIGGER_EVAL.md` reports that all six candidates failed the preregistered combination of 180-day success, 90-day adverse-excursion limit and independent-fire minimum. Bottom-pressure >=0.45 had 41 fires but 18 separated episodes, and a reported 64% 180-day hit rate below its 70% bar. Long-run recovery after an oversold reading did not imply immediate timing precision. The report acknowledges visual parameter selection and overlapping windows.
- The impulse study withdraws an earlier Coinbase-premium predictive claim. It classifies the feature as contextual, records low recall and specific blind spots for surviving DVOL/SOPR legs, and rejects/promotes candidates under different evidence conditions. The old prose and current evaluator are not interchangeable.
- The hourly candle-proxy study records no qualifying act-tier survivor and a divergence candidate with high false-alarm cost. True aggressor flow is a different measurement, not a name to give candle-signed volume.
- The accuracy-upgrade report records macro-score association but a failed allocation gate. We must test a materially changed mechanism, data regime or decision interaction rather than repackage the rejected rule.

The current allocation bottom overlay starts its ramp at bottom-pressure 0.30, whereas the recovered re-entry report tested fresh crosses at 0.45 and 0.60 under a different job. Its published hit rates cannot be used as evidence for today's sizing rule without reproducing the actual rule, timing and costs. Likewise, a high lift is not high absolute accuracy: a hypothetical 2.5x increase over a 10% event base rate is still only 25% event probability, before selection bias and calibration.

Existing 2024+ holdouts have already been inspected repeatedly. They remain useful retrospective stress periods, but are not an untouched final test for a new strategy.

## 5. Data readiness determines achievable timing

The inspected local snapshot is dated through 2026-09-26, not a live market reading. It contains 4,393 daily signal rows and 197 columns; Coinbase hourly has 94,063 rows. This is enough to undertake substantial baseline research, but not enough to declare every factor historical and point-in-time.

| Input in this stored snapshot | Observed coverage | Research consequence |
| --- | --- | --- |
| True OKX hourly taker volume | 2,957 rows, 2026-05-26 onward | Real flow, but short history and few independent crises; not ten years of order-flow validation |
| BTC hourly OHLCV | 2016 onward; largest timestamp gap 16h | Deep price history, not aggressor-side history; do not call 24 observed rows a continuous 24h window across a gap |
| OKX hourly timestamps | Largest gap 10h | Test elapsed-time window completeness, not only row count |
| Deribit options structure | 89 source snapshots from 2026-06-13 | Historical gamma/skew regimes before collection cannot be invented from present observations |
| Funding | Raw store since 2023; derived funding_rate only 83 non-null rows in the inspected signal frame | Resolve source-column/definition/coverage differences before claiming multi-year factor evidence |
| ETF flows | From 2024-01-11 | Do not impute pre-ETF evidence or use after-close publications before their availability |
| Macro/on-chain data | Deep observation histories, availability clocks not established by these frames | Vintage/release-time audit remains necessary |

Glassnode documents immutable point-in-time variants precisely because entity labeling, late data and corrections can change history; it also distinguishes computation time from API publication. FRED distinguishes current revised observations from historical information vintages [P6–P7]. A daily timestamp alone proves neither was knowable at that time.

For every candidate input, require entity/venue, units, observation interval, candle open/close convention, actual or conservatively bounded availability time, ingestion time, revision identity, missingness and rights. Aggregated dollar OI can change when price changes without an equivalent change in contracts. Spot/perpetual flow, venues, funding conventions and time windows must not be silently mixed. A guessed dealer position from options OI is a scenario assumption, not observed inventory.

## 6. Mechanism map: what can move crypto, and what would falsify our reading?

We separate three evidence classes: documented market mechanism; reproducible predictive association; and an untested strategy hypothesis. Causality, prediction and profitable action are different claims. A causal shock may be unpredictable; a predictor can be useful without identifying the ultimate cause; a statistically useful predictor can still be too late or expensive to trade.

### Macro risk-taking and balance-sheet conditions

Earlier Liu/Tsyvinski research found crypto-specific momentum and attention predictability and limited exposure to conventional macro factors in its sample. Later IMF authors found stronger equity co-movement alongside institutional participation and a risk-taking channel from US monetary tightening [P2–P3]. These need not be contradictory timeless laws: samples and market structure differ. Our hypothesis is that macro inputs should condition the relevance of other signals, not impose one permanently bullish/bearish liquidity formula.

Tests should use changes in policy expectations or identified surprises, real-yield/dollar/credit conditions, and changing BTC-equity downside exposure. A chart where a chosen money-supply series leads BTC after searching many lags is not causal identification. For monetary-shock work, use narrow event windows, timestamped surprise measures, placebo event times and pre-trend checks. For ordinary forecasting, require incremental out-of-sample value after price/volatility and seasonality controls. A failure to survive a lag/period change or loss of value after basic price controls is a rejection, not a reason to keep retuning the liquidity shift.

### Spot pressure, liquidity and absorption

Research by Makarov/Schoar documents segmented exchanges and a relationship between common signed volume and BTC returns [P4]. That is motivation to measure real trade direction and cross-venue liquidity, not permission to convert a contemporaneous explanatory fit into a forecast hit rate.

Candidate mechanism: price impact depends on directional aggressive trading relative to available liquidity and how quickly that liquidity replenishes. Research should distinguish a sell wave that keeps moving price down from equally large selling absorbed near an observed level. Net selling alone may be a continuation signal, an exhaustion signal or a response to news. Test price-impact-per-unit-flow, replenishment, spread/depth changes and cross-venue agreement, with executable timestamps and actual trade aggressor fields. Reject a divergence claim if its improvement disappears with one-bar delay or when true trade signs replace a candle proxy.

### Leverage, carry and forced selling

BIS Crypto Carry links large futures bases to leveraged upside demand and scarce arbitrage capital, and finds elevated carry associated with subsequent crash risk [P5]. Separately, transaction-level research on Compound/Aave demonstrates collateral sales and liquidation feedback spreading across markets [P8]. The latter identifies a mechanism in particular DeFi settings; it is not proof that every BTC downturn follows the same chain.

The testable hypothesis is an interaction: vulnerable leverage plus deteriorating absorption plus a price/volatility shock raises continuation hazard. High carry alone need not be a top. OI alone cannot tell us net directional ownership; each futures contract has two sides. Falling dollar OI can reflect both a change in contracts and a lower underlying price. Qualify contract units, margin conventions, venue sets and observation clocks before estimating leverage unwinds.

A flush may reduce future forced-selling pressure, but a liquidation spike does not prove the bottom: collateral selling may continue and new sellers may replace liquidated longs. Our recovery model must test what happens after the flush, including failed rebounds, rather than assume liquidation equals buy signal.

### Holder cost basis, realized behavior and supply

The existing model already has MVRV/NUPL, SOPR, holder cost bases, Reserve Risk, miner economics and ETF/stablecoin inputs. Proposed research treats them as distinct, slow or medium-horizon conditions rather than a pile of equal votes. Cheapness and realized-loss stress can identify vulnerability or opportunity without identifying the last low.

Test incremental contribution by information block: valuation level; realized spending/losses; cohort behavior; structural supply changes. Do not count deterministic identities as independent evidence. Exchange-address labels and provider revisions need point-in-time treatment. Issuance into a treasury wallet, stablecoin circulation growth or a large ETF flow does not by itself identify when market purchases occur; test the actual lag and reverse causality instead of asserting automatic capital transmission.

### Technical structure and momentum

Technical analysis will be encoded as reproducible measurements, not abandoned or treated as mystical pattern recognition. Candidate families include trend slope/alignment, volatility-scaled distance from moving averages, momentum acceleration/deceleration, trailing range breaks and failed reclaims, realized-volatility expansion, rejection/acceptance at a known level, and price-relative-to-traded-volume anchors established before the forecast.

Every pivot definition must record when it became knowable. A swing low requiring two later closes can be a confirmed level only after those closes; it cannot appear as a real-time signal on the low's date. Anchored VWAP must use a pre-existing event/level rule, not the best-looking future swing. A divergence is a feature, not a verdict. Compare it with simpler return/volatility features before granting it model weight.

Cross-sectional market/size/momentum results motivate a separate asset-selection experiment [P9]. They do not establish that the aggregate BTC market is safe. BTC exposure timing and altcoin relative leadership therefore need separate evaluation and decision authority.

### Event, counterparty and venue shocks

Unexpected insolvency, an exploit or a policy surprise may not be forecastable from yesterday's RSI. The research must grade pre-shock warning, immediate detection and post-shock continuation separately. Operational defense may depend on observable loss of liquidity, abnormal venue spreads or a broken source, not a claim that the event was predicted.

This category needs timestamped events and contemporaneous source-status records. Do not label a report available before its first publication or score an edited later headline as the original alert. Protect users against unavailable execution and data failures without interpreting an unavailable market feed as a bearish price forecast.

## 7. Four prediction heads; one existing allocation authority

This is a proposed research decomposition, not four independent trading bots or new score planes. Existing signal/calibration/radar owners should expose the qualified results; BitcoinDecisionState continues to resolve accepted policy.

| Research head | Specific question | Candidate evidence | Critical false positive |
| --- | --- | --- | --- |
| Fast downside/cascade | Is a damaging decline likely to begin or continue within the next hours/day? | Price impact, real flow, depth, qualified carry/OI, volatility shock | Selling every crowded but healthy uptrend |
| Washout/recovery | Has selling pressure stopped producing new downside, with an executable recovery now emerging? | Loss realization, unwind, absorption, reclaimed level, failed-low behavior | Buying the first oversold reading in an unfinished bear leg |
| Trend participation | Is this breakout/reclaim likely to persist over days/weeks? | Completed-bar trend, momentum, breadth, spot follow-through, regime | Repeated false breakouts and costly whipsaw |
| Cycle distribution | Is medium/long-horizon reward becoming poor relative to left-tail risk? | Valuation/holder behavior, slowing demand, carry, failed advances, macro context | Exiting a durable bull market far too early |

The immediate-risk problem does not have to wait for the slow model's normal confirmation delay. A separately qualified fast protective condition can be evaluated at completed intraday observations and trigger a proposed exposure reduction under existing policy. It must earn that authority against its false-alarm and execution costs; there is no new emergency veto in this R1 work.

Likewise, recovery need not wait until every slow macro measure turns positive. A staged recovery hypothesis may prove useful while the long-run regime remains defensive. But the system must say which proposition improved: tactical recovery, trend recovery, or cycle thesis. These are not interchangeable risk-on claims.

A useful displayed sequence is:

**Downside:** latent fragility → failed advance/distribution watch → observed structural break or fast stress → continuation risk → recovery conditions.

**Upside:** selloff → washout watch → absorption/stabilization → observable reclaim → trend follow-through.

This sequence is a research hypothesis. Stages can be skipped, reversed or unavailable. “Watch” does not size positions. Sequentially updating probabilities should not wait for a theatrical label to complete, nor should two signals from the same input count as independent confirmations.

## 8. The next experiments must answer economic questions

### Primary next questions

First repair and review the timing/maturity defects through the existing engine/test owner, then reproduce the baseline on corrected, availability-qualified data. The research audit did not authorize a silent live fix. Re-run old candidate claims on their original definitions before adding new features.

After that, prioritize one fast-downside and one recovery experiment rather than scanning every horizon at once. Proposed label anchors for the next preregistration are the existing 24-hour downside family and a seven-day post-washout recovery family. Exact barrier levels, cooldowns, episode definitions and score thresholds must be frozen before outcomes are inspected; none is optimized or presented as an actionable rule in R1.

For fast risk, compare a forecast made before the damaging move with a continuation warning after damage has begun. Report both; do not hide the second inside a claim of early detection. For recovery, compare an achievable entry following the signal with adverse excursion and subsequent upside; a future maximum is not an exit fill.

### Objective and evaluation

The policy question is whether an action improves expected utility after costs compared with the incumbent policy, not whether the forecast looks impressive. Reducing exposure trades drawdown protection against missed upside and re-entry cost. Adding exposure trades recovery participation against false-bottom loss. The optimum threshold depends on those asymmetric costs and the calibrated distribution, not a round marketing score.

Keep outcome families internally consistent. For competing first-passage events, estimate downside-first, upside-first and no-barrier outcomes; those probabilities must sum to one. Marginal probabilities of both barriers being touched over a long window are a different object and may overlap. End-of-horizon return, intraperiod worst loss and “touched a local high” are different labels and cannot substitute for one another.

Report event precision, recall and false alerts per month; alert duration; warning-time distribution; missed-tail loss; downside avoided; upside forgone; recovery participation; turnover; and net-cost performance. For probabilities, include Brier/log loss and calibration by regime and horizon, with uncertainty bands. A high overall accuracy on many quiet hours is meaningless without the event base rate.

Use a no-trade/hodl comparator, a simple trend/cash comparator, the incumbent raw and accepted final allocation, and a risk-matched volatility-target comparator. Decompose model-alpha from exposure reduction: lower drawdown from simply holding less BTC is not evidence of better timing. Cash yield, financing/funding, fees, spread, slippage and realistic outage/gap execution belong in the comparison. Report conservative cost/latency stress, not only one convenient fee assumption.

### Robustness against research overfitting

Use expanding or rolling chronological fits with nested training-only selection. Purge overlapping future labels and embargo by the relevant horizon, not an arbitrary fixed number of bars for every experiment. Cluster outcomes into independent episodes; a week-long crash does not provide hundreds of independent successful hourly alerts. Bootstrap by time blocks/events and show sensitivity to episode definitions.

Run leave-one-crisis/cycle analyses as robustness checks, plus chronological out-of-sample tests. Removing one crisis after seeing a failure cannot become a new definition of the market. A model that loses its value when any one episode is removed should be reported as fragile. Record every attempted feature block, threshold and failed variant in the existing research/evaluation owner.

Candidate complexity should start with transparent threshold/logistic/discrete-time-hazard baselines. Nonlinear challengers, including gradient-boosted interactions, must improve calibrated net utility on held-out periods and survive data-delay stress. An HMM or change-point model may describe changing distributions, but a smoothed state using future observations cannot be used as a live feature. An LLM can synthesize sourced explanations and research alternatives; it is not a substitute for the numerical forecast or position-sizing authority.

The final untouched period must genuinely be untouched. Because earlier research repeatedly used 2024+ data, merely splitting at 2024 again does not produce independent final evidence. A locked forward ledger of forecasts issued before outcomes is essential; use the existing impulse/review/forecast owners and keep feature availability/model versions immutable. R1 starts no autonomous collector or alert daemon.

## 9. A decision-ready dashboard, not more indicator clutter

The science should improve the first screen without turning it into a cockpit of unexplained gauges. The proposed read is: current accepted exposure state; tactical downside/recovery assessment; horizon and timing; the two or three decisive independent observations; strongest counterevidence; what would change the assessment; and data coverage.

For a future qualified warning, the user should be able to answer: Is this a forecast or an observed breakdown? What is its horizon? Is the issue market-wide or venue-specific? Is the model reducing risk, merely watching, or unable to decide? Which actual observation would invalidate the warning? The UI must not show a numerical confidence percentage until that probability has been calibrated for that target and horizon.

A recovery panel should separately show washed out, stabilized, reclaimed and confirmed; it must not rewrite the original low after more history arrives. Research watch, confirmed model action and alert delivery remain distinct. This is how precision and understandable design reinforce each other.

## 10. Delivery sequence and promotion boundary

**R1 completed:** incumbent source/authority audit; prior rejection recovery; preregistered 366-cutoff test with controls; raw-allocation sensitivity; data coverage and hashes; exploratory immature-label demonstration; primary-source mechanism review; and this decision-ready research programme. No claim of an improved profitable strategy.

**R2, next substantive batch:** fix and independently review the higher-timeframe and label-maturity seams within the existing owners; expand prefix/availability audits across the actual decision inputs; reproduce the incumbent baseline and prior impulse candidates without altering their outcome definitions. Report any alpha loss after removing bias. Historical-vintage limitations stay visible.

**R3:** the frozen fast-downside experiment, then paired post-washout recovery experiment. Evaluate interactions versus individual signals, false-alarm cost, lead time, net execution and regime dependence. Real flow is only eligible on actual supported history; old candle proxies remain labeled proxies.

**R4:** medium-horizon persistence and longer-horizon distribution/risk-reward experiments, with strict sample-size and cycle uncertainty. Integrate only features with demonstrated incremental value and stable availability.

**R5:** shadow forecasts under the existing issued-forward owner, drift/coverage monitoring and independent review. A material decision-policy change needs real-path performance evidence and accepted promotion, not green CI or an aesthetically convincing dashboard.

The next implementation/replay phase is intentionally separate from this research-only diagnostic. All production model/config files remain unchanged. No planned result is counted as completed, no new served-model/mode identity is inferred, and no automatic future work is promised.

## Primary public sources reviewed

These sources support mechanism/measurement claims, not a claimed replication or endorsement of Mastermind. Reviews in this R1 batch use the primary authors' abstracts/summaries and official documentation; full empirical reproduction is still work to do.

[P1] Pandas time-series/resampling documentation: https://pandas.pydata.org/pandas-docs/dev/user_guide/timeseries.html and API https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.resample.html . Distinguish aggregation closure, label and timestamp availability.

[P2] Liu and Tsyvinski, Risks and Returns of Cryptocurrency, NBER WP24877 (2018; published RFS 2021): https://www.nber.org/papers/w24877 . Historical momentum/attention evidence; not a timeless assertion of macro independence.

[P3] Che, Copestake, Furceri and Terracciano, The Crypto Cycle and US Monetary Policy, IMF WP2023/163: https://www.imf.org/en/publications/wp/issues/2023/08/04/the-crypto-cycle-and-us-monetary-policy-534834 . Authors' research on changing common risk and monetary transmission; not IMF policy or a timing model.

[P4] Makarov and Schoar, Trading and Arbitrage in Cryptocurrency Markets, JFE (2020), author-institution summary: https://mitsloan.mit.edu/cfi/trading-and-arbitrage-cryptocurrency-markets . Exchange fragmentation and contemporaneous signed-volume relationships; not advance forecast accuracy.

[P5] Schmeling, Schrimpf and Todorov, Crypto Carry, BIS WP1087 (2023): https://www.bis.org/publications/working-paper-1087-crypto-carry . Carry, leveraged demand/arbitrage constraints and crash association; not a sufficient instant-exit trigger.

[P6] Glassnode official Point-in-Time Metrics documentation: https://docs.glassnode.com/data/point-in-time-metrics . Dataset mutations, tracking start dates and computation/publication distinction; no provider subscription acquired here.

[P7] FRED/ALFRED official real-time-period documentation: https://fred.stlouisfed.org/docs/api/fred/realtime_period.html . Current revised data and historical information vintages differ.

[P8] Lehar and Parlour, Systemic Fragility in Decentralised Markets, BIS WP1062 (2022): https://www.bis.org/publications/working-paper-1062-systemic-fragility-decentralised-markets . Directly studied DeFi liquidation/price-impact feedback; scope is not every BTC venue.

[P9] Liu, Tsyvinski and Wu, Common Risk Factors in Cryptocurrency, NBER WP25882 (2019; published JF2022): https://www.nber.org/papers/w25882 . Cross-sectional market/size/momentum evidence is distinct from aggregate Bitcoin turning-point timing.
