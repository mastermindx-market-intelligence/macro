# Fixed follow-up analyses

Written before examining held-out outcome tables. These analyses diagnose the
frozen finalists and fixed timeframe hypotheses; they do not select a new winner.

1. Recompute the frozen finalists for every 2-session phase (2), 3-session phase
   (3), and 2-week phase (2): 12 combinations, including the original phase.
   Report the range and each cell, without choosing a favorable anchor.
2. Recompute the original phase with dividend-adjusted OHLC, using the daily
   adjclose/close factor consistently for open, high, low, and close. This is a
   sensitivity to chart basis, not an executable total-return strategy.
3. On the original unfiltered high-timeframe trigger dates, compare each lower
   timeframe condition to its complement. Report unconditional qualification and
   survival, then standardize survival among already-qualified candidates to a
   common distribution of age (0-5,6-10,11-21), distance (0-1,1-2 ATR), and depth
   (4-6,6+ ATR). Retain only strata with at least5 events in each condition; report
   retained counts/coverage. These associations are descriptive, not causal, and
   remain confounded by asset, regime and other omitted information.
4. For fixed high hypotheses (Stoch curl; same/cross 1W/2W MACD deep-improving or
   crossover; and Stoch-only), wait from0 to10 daily sessions for 1D,2D,3D lower
   confirmation. Compare both-rising and matching recent MACD-cross conditions.
   Freeze the original candidate low/high, its date, and its ATR. Stop if it is
   breached by more than0.25 ATR before confirmation. Require the lower signal on
   a completed bar. Preserve the original candidate when calculating delay,
   distance, age, and next63-session survival from confirmation. Report all base
   setups, cancellations, confirmations, and successes per original setup as
   well as success per confirmation. No candidate substitution after a failure.
   Only base setups with the full10+63 follow-up window inside the test period
   enter this comparison, including immediate confirmation and no-wait baseline.
   Intermediate tolerated breaches remain visible. Waiting after failure cannot
   count as a success. No returns-based optimization or extra threshold search.
5. Numerical examples and event charts are illustrative; the pooled and subgroup
   results, including failures and missed pivots, determine the conclusions.

All added literal configurations are logged to the existing canonical TrialLedger
class in the study-local ledger before these analyses are evaluated. Pointwise
intervals do not correct the full exploratory family of comparisons.
