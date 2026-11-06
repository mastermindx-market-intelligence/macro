# Industry analogue trial v1 - pre-result protocol

Operation: market-topology-research-20260923-astra-001. Research only; not a Fable commission. This protocol is committed before the new analogue outcomes are computed. It does not modify or replace the negative industry ridge pilot or the held stock ORDER_TRANSITION_TRIAL_V1.

## Question and scope

Does matching richer industry-population structure improve forecasts of the fraction of industries making positive returns over the NEXT 20 sessions, compared with a strong conventional market/breadth analogue? This is a market-state conditional-distribution experiment, NOT another individual-industry return-ranking model. Industry breadth is not stock breadth. No September 2026 current-market conclusion or executable PnL is claimed.

Use the already archived official Kenneth French 49 Industry Portfolios daily source ZIP on the original research host. Required SHA256: 13be85084196424aa85f29136af47f147a443275f90eb0955dbcdc6d6d25f448. Parse only its first value-weighted block; -99.99/-999 become missing, never zero; percentage returns become fractions. Current-vintage CRSP-derived history, not contemporaneously archived releases. Industry composition follows the provider's methodology; individual-security survivorship/identity/terminal qualification is not inferred from this aggregate source.

## Sample and clocks

Features require all 49 industries across 252 complete prior daily returns. Formation anchors are last observed sessions of full calendar months. Candidate history starts January 1980. Test anchors are January 2000 through November 2025, with all 20 future sessions ending by December 31, 2025. Report exact usable counts and exclusions; do not substitute a shorter feature window to recover excluded anchors. No 2026 outcome is used for model selection.

For query t, a candidate s is allowed only when s+20 < t-252 (strict nonoverlap between candidate outcome and the query's longest lookback). Candidate outcomes must already be known. Features and distances use only candidate history and query information through t. Standardize each feature using the mean and sample standard deviation of eligible candidate features; constant columns contribute zero. No tuning, learned feature weights, future scaling or test-outcome selection.

## Three fixed comparisons

1. Unconditional expanding-history prediction: mean of all eligible candidate outcomes.
2. Conventional analogue, using 10 features: daily-rebalanced equal-industry proxy cumulative log returns over 21/63/126 sessions; proxy realized daily volatility over 63 sessions; proxy current drawdown from its 126-session high; fractions of industries with positive 21/63/126-session returns; fractions above their 50/200-session wealth moving average. The proxy is NOT SPY or a cap-weighted total market.
3. Augmented analogue: conventional features plus the 8 fields below. Distance = one-half mean squared standardized difference over conventional fields plus one-half mean squared standardized difference over added fields. Conventional distance is its own mean squared standardized difference. Equal weighting of the two groups is fixed before results.

Added fields:
- persistent_positive63: fraction positive in each of the three nonoverlapping 21-session blocks ending t;
- persistent_negative63: fraction negative in all three blocks;
- low_net_progress63: fraction with absolute 63-session cumulative log return below 0.25 times sigma63 times sqrt(63), requiring positive finite sigma63;
- leader_turnover21: 1-Jaccard(top10 industries by 63-session return at t, top10 at t-21); ties resolved by stable input-column order;
- return_dispersion63: cross-sectional sample standard deviation of 63-session log returns;
- correlation63: average off-diagonal pairwise correlation of 63 daily industry log returns;
- positive_gain_concentration63: HHI of positive parts of 63-session log returns, normalized to sum 1; use 0 plus an explicit no-positive-gains flag in diagnostic metadata when no positive gain exists (this is NOT index contribution concentration);
- breadth_change21: current positive-63-session fraction minus its value 21 sessions earlier.

For each analogue model sort eligible candidates by distance, ties chronological. Greedily select K=20 candidates with any two selected anchor positions at least 126 daily sessions apart. This reduces overlapping episodes; it does not establish statistical independence. No relaxed separation to fill K. If fewer than 20 can be selected, omit query from all-model comparison and report it. Selected candidates get equal weights. Record exact neighbour dates, distances and outcomes. The unconditional model uses all eligible history rather than claiming its rows are independent episodes.

## Outcomes and inference

Primary: future20_positive_share = fraction of all 49 industries whose cumulative return on t+1..t+20 is positive. Compare paired squared errors (conventional minus augmented); positive difference favours augmentation. Report each model's RMSE and MAE in percentage points.

Secondary diagnostics only: next-20-session cross-sectional return dispersion; future realized volatility of the equal-industry proxy; average future percentile rank of today's top10 industries; average future percentile rank of today's bottom10. These targets use FUTURE-ONLY returns, not surviving overlapping trailing labels. Forecast each with neighbour means. Report all targets, not only favourable ones. These secondary tests cannot rescue a failed primary as confirmatory evidence.

Inference: 5,000 circular block bootstrap replicates over chronologically ordered query errors; 12 monthly anchors/block; seed 2026092303. Report nominal 95% paired-MSE-gain intervals, 2000-2009/2010-2019/2020-2025 subperiods, and leave-one-test-year-out primary gains. No familywise significance or investable alpha claim from nominal intervals. A dataset-vintage revision, sample error or coding correction must be disclosed; do not tune K, horizons, features, blocks or eras to improve results.

## Descriptive cases and support

An explanatory historical case pair may be selected without future outcomes: among eligible anchors separated by >=126 sessions, require positive63 breadth within 2/49, proxy 63-session log return within 0.03, and proxy daily volatility within 0.002; maximize the difference in persistent_positive63. Label it a selected illustration, not unbiased predictive evidence. Report the matching tolerances and all conventional differences.

Forecasts in this first experiment deliberately force K matches when technically available. That is an experimental limitation, not production permission. Expose nearest/furthest distance, neighbour-year concentration and largest standardized feature mismatches. A deployable analogue requires a separately calibrated no-match/support rule; never turn K nearest neighbours into a claim that K genuinely comparable historical regimes exist.

## Reproducibility and holds

Retain source digest, complete executed script, environment versions, feature/target definitions, per-query predictions, neighbour identities, summary and input hash readback in the existing research artifact home. Publish only original research code, protocol and aggregate results; do not publish the vendor source archive. The raw stock trial remains held. The previously blocked R2 operation is not retried or routed around. No production data mutation, worker, watcher, autonomous wake or trading effect is authorized by this document.
