# Research round R1 — reaction, hazard and useful protection are different questions

Status: source-grounded research design and implementation findings. No new financial backtest, forecasting edge, cash allocation or production improvement is claimed. This is the first round of the continuing mission in `MISSION.md`, not the end of research.

## 1. The first question was mis-specified

The motivating incident is not only whether a forecast predicted a future >=5% SPY drawdown. It is whether current weakness in the user's relevant exposures was recognised and delivered at all. A long-horizon macro blend, an index-level implied-volatility measure, a cohort-damage detector and a forward drawdown probability have different targets. Average them together and an internally correct score can still answer the wrong question.

The current source already contains an appropriate decomposition in `engine/risk_envelope.py`: measured state, transition hazard and capital policy. Reuse it. The first research result is therefore a measurement/interface diagnosis, not a new trading model. Exact tests reproduced three vocabulary failures: native leadership `CRACKING`, native Radar `elevated`, and native Radar `risk-off` were not mapped by `scripts/build_risk_envelope.py`. The local correction carries those observations at the existing FRAGILE competence ceiling and leaves numerical/forecast/policy authority unchanged. A source warning that is dropped before the UI cannot be rescued by optimizing its forecast.

## 2. Primary evidence and what it does—and does not—justify

### Volatility is neither direction nor universal market scope

Cboe describes VIX as a non-directional, annualized expectation of S&P500 volatility over a constant30-day horizon. Its VIX1D discussion explicitly distinguishes short-horizon volatility from the30-day measure. Therefore a calm VIX reading is not, by definition, a confirmation that a semiconductor cohort is healthy or that a multi-session negative price drift is absent. This is a scope/horizon inference, not a claim that VIX has no predictive information.

Primary source: Cboe, *What the VIX and VIX1D Indices Attempt to Measure and How They Differ* (2023-04-24), https://www.cboe.com/insights/posts/what-the-vix-and-vix-1-d-indices-attempt-to-measure-and-how-they-differ/ . Read on2026-10-15. No current VIX quote from a cached page is used as live evidence.

Cboe's dispersion description separates constituent-specific variability from index variability. This supports testing breadth/dispersion and cohort damage separately rather than treating a quiet index as a universal veto. It does not establish a trading edge for a new dispersion threshold.

Primary source: Cboe, *The Dispersion Index*, https://www.cboe.com/us/indices/dispersion/ . Read on2026-10-15; methodology explanation only, not cached displayed values.

### Risk control must be judged out of sample and after implementation costs

Moreira and Muir report substantial benefits from volatility-managed portfolios. Cederburg et al., using103 equity strategies, find that such portfolios do not systematically outperform unmanaged counterparts and that feasible out-of-sample versions can perform poorly because of parameter instability. DeMiguel et al. subsequently report a conditional multifactor construction that survives their out-of-sample and cost tests. The disagreement is constructive: a particular failed construction does not close the research space, and an attractive in-sample result does not authorize deployment.

Primary sources: Moreira and Muir, *Volatility Managed Portfolios*, NBER22208, https://www.nber.org/papers/w22208 ; Cederburg et al., *On the performance of volatility-managed portfolios*, Journal of Financial Economics138(1), https://www.sciencedirect.com/science/article/pii/S0304405X2030132X ; DeMiguel et al., *A Multifactor Perspective on Volatility-Managed Portfolios*, https://onlinelibrary.wiley.com/doi/full/10.1111/jofi.13395 . Read on2026-10-15. These are literature results, not Mastermind replication results.

### Recovery deserves a separate test, not a symmetrical reset

Daniel and Moskowitz document momentum crashes associated with panic states and market rebounds. For this mission the design implication is to include sharp recovery episodes and the opportunity cost of remaining defensive; it is not to label all rebounds safe or apply their strategy without replication. A system optimized only for warning onset can remain trapped in an alarm through a recovery.

Primary source: Daniel and Moskowitz, *Momentum Crashes*, NBER20439, https://www.nber.org/papers/w20439 . Read on2026-10-15.

### Good early warning requires timing, stability and interpretability

The BIS's banking-crisis work emphasizes timing, signal stability, interpretability and false-alarm tradeoffs in addition to forecasting power. It uses a multi-year banking-crisis horizon. Borrow the evaluation principles, not its thresholds or banking-crisis target, for an equity swing-trading product. A warning can be statistically useful yet operationally too late, too unstable or poorly explained.

Primary source: Aldasoro, Borio and Drehmann, *Early warning indicators of banking crises: expanding the family*, BIS Quarterly Review(March2018), https://www.bis.org/publications/qr-201803/early-warning-indicators-banking-crises-expanding-family . Read on2026-10-15.

## 3. Hypotheses worth testing next

H1—reaction loss: source-native deterioration exists earlier than the foreground warning because of vocabulary, freshness, aggregation and delivery gates. Test original recorded artifacts against the original rendered/served state at the same knowledge time. This is partly proven at the source-interface level; production occurrence and duration are not yet measured.

H2—scope mismatch: cohort damage and weakening equal-weight/small-cap participation provide a useful contemporaneous explanation while capitalization-weighted indexes and longer trends still hold. Compare with an equally timely price-only benchmark. Do not claim capital inflows from relative-price strength; flows need their own data.

H3—orderly deterioration: downward drift and persistent breadth damage matter even when realized/implied volatility is not extreme. Evaluate price-path and downside measures independently of total-volatility thresholds. No new threshold is selected from the October screenshot.

H4—regime-specific interpretation: defensive relative strength may reflect different mechanisms under growth concern, rates/inflation pressure or a sector-specific earnings unwind. Test whether the extra mechanism labels improve conditional outcomes beyond the simple reaction baseline, rather than assuming an elaborate narrative adds value.

H5—recovery asymmetry: warning clearance based on renewed participation, leadership stabilization and price repair can differ from the reverse of warning onset. Compare false-clear frequency with excessive time spent defensive after genuine recovery.

These remain hypotheses. Explanatory usefulness does not itself authorize rank, gate or size changes. Existing frozen Grey Deer studies and their trial budgets remain intact.

## 4. Benchmark definition before a new empirical run

Three separate scorecards are required.

**A—Detection/delivery correctness.** Target is an already-issued native observation and its first legitimate availability time, not a future return. Reconstruct producer -> adapter -> envelope -> warning payload -> consumer. Report native states recognised, source coverage, data-to-composition latency, composition-to-publication latency, publication-to-paint latency, warnings lost on dismissal/news, stale-as-current errors, out-of-order regression, and current-state explanation preservation. Unknowns are counted explicitly. Synthetic contract tests and historical source captures are different evidence modes.

**B—Forecast discrimination and calibration.** Specify market/cohort, horizon and outcome before reading the holdout. Keep index-level>=5% outcomes separate from a stock's own drawdown and from present trend failure. Use chronological train/validation/test splits, independent episodes and intervals that account for overlap. Compare to unconditional rates, the current owner forecast and a simple price/volatility benchmark. Report base rates, interval coverage, calibration error, false alarms, misses and warning lead time. Do not multiply the sample size by counting every day of one episode as an independent success.

**C—Decision usefulness.** Evaluate an explicit implementable response under existing risk-policy authority against the same holdings, timestamped information and execution assumptions. Include slippage, turnover, cash carry, hedge costs when relevant, opportunity cost in rallies and delayed re-entry. Report downside protection and recovery participation, not only Sharpe or avoided-loss anecdotes. No automatic liquidation, selected security recommendation or numerical sizing is produced by this research design.

Required episode controls: ordinary pullback, orderly multi-session decline, narrow hardware/semiconductor damage, index-held/weak-breadth divergence, broad sell-off, credit/liquidity stress, rates shock, sector earnings shock, fast rebound and false recovery. October14 is a motivating diagnostic episode and must not be reported as a fresh out-of-sample test after influencing the design.

## 5. Data and evidence admission

For each record retain source event time, first available time, publication time, market session, observation scope, taxonomy/membership version and source revision. An observation date is not a first-availability receipt. Historical price reconstruction may test a causal price rule, but it cannot prove what Mastermind actually knew or displayed on that date. Never backdate an engine output, use revised fundamentals as contemporaneous inputs, silently substitute a future cohort membership, or count a generated-at timestamp as freshness.

For the next empirical round, first inventory the existing retained source artifacts, forward logs and lawful price/cohort stores. Use original captures where present; label reconstruction and missing coverage. Reuse existing episode and trial infrastructure rather than create a second ledger. Freeze the exact new experiment, dataset version, baseline, outcome, exclusions and stopping rule before its results. Absence of a usable original capture narrows the claim; it does not justify fabricated evidence or stopping all independent work.

## 6. Implementation decisions unlocked now

Repair producer-vocabulary translation and source-to-consumer tests immediately; no predictive backtest is needed to stop dropping a native warning. Keep the native source label and its competence separate from the combined descriptive stage. Do not let one missing required source hide the fact that another fresh source has an actual warning, but also do not call the whole market confirmed from partial evidence. Finish the existing foreground warning path and explicitly label uncertain/stale coverage. Treat future forecast/position-sizing changes as separate researched promotions.

Next research round: timestamped data-coverage census and preregistration of the reaction/delivery benchmark, then a causal replay using available original captures and explicitly labelled reconstruction. This round has not run a new financial strategy backtest and has not established predictive or economic superiority.
