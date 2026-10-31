# Result dictionary

All main percentages describe pivot detection and survival, not profitable trades.

## Rule identity

- `side`: bottom or top.
- `stoch_tf`, `macd_tf`: independent indicator timeframes.
- `stoch_mode`: curl, recent K/D cross, or a named simple baseline.
- `macd_mode`: deep, deep_rising, deep_falling, cross, deep_then_cross,
  deep_or_cross, or none.
- `deep_rising` and `deep_falling` are DIRECTIONAL. For a bottom, rising is a
  negative histogram improving upward. For a top, rising is a positive histogram
  improving downward toward a bearish reversal. Consequently top deep_falling
  means a high positive histogram still growing.
- `filter`: none, `lf_TIMEFRAME_CONDITION`, or `aux_CONDITION`.
- `rule_id`: exact stable configuration string; do not select a new rule using
  the held-out rows and describe it as an independently validated winner.
- `pool`: primary = 48 exchange-traded instruments; crypto = BTC and ETH only.

## Main event counts and rates

- `n`: all alerts of the stated rule in the specified pool and split, with a
  complete 63-session outcome window.
- `qualified_n`: alerts with candidate age <=21 sessions, close-to-pivot distance
  <=2 ATR at the pivot, and approach depth >=4 ATR.
- `timely_durable_n`: qualified alerts whose original pivot survives 63 sessions
  with at most a 0.25-ATR breach.
- `timely_durable_rate`: timely_durable_n / n. The report calls this all-alert
  success or near-pivot success. Failure can mean excessive distance or age,
  insufficient approach depth, or a future pivot breach.
- `qualified_survival63`: timely_durable_n / qualified_n. Keep qualified_n visible.
- `survival63`: pivot survival among ALL alerts, including old or distant lows.
  This can be high for late crossovers without demonstrating early detection.
- `strict_survival63`: all-alert survival with zero tolerated breach.
- `median_age`: candidate age at alert, in daily sessions.
- `median_distance_atr`: distance from alert close to frozen candidate price,
  divided by ATR known at that pivot.
- `median_depth_atr`: approach from the opposite extreme in the 63 sessions
  preceding the candidate, measured in its frozen ATR.
- `reference_pivots`: independent local 63-left/63-right extreme catalogue with
  at least a 4-ATR approach and rejection; enough detection and outcome followup.
- `detected_pivots`: unique catalogue pivots detected at age <=21 and <=2 ATR.
- `recall`: detected_pivots / reference_pivots; called pivot coverage in report.
- `balance_score`: harmonic mean of timely_durable_rate and recall. Descriptive
  tradeoff, not formal single-target F1.
- `median_breach63_atr`, `p90_breach63_atr`: adverse future breach of frozen pivot.
- `median_mfe63_atr`: favorable excursion from alert close, a secondary measure.
- `median_directional_return63`: signed close-to-close return, secondary. No
  execution, commissions, financing, or position sizing is simulated.

## Uncertainty and filters

- `ci_low/high`: pointwise 95% six-month whole-cross-section block bootstrap of
  timely_durable_rate; 2,000 draws. Not multiplicity-adjusted.
- `asset_ci_low/high`, `year_ci_low/high`: alternate cluster sensitivities.
- `delta_vs_high_base`: filtered all-alert rate minus the same unfiltered high
  base rate; intervals jointly resample the same half-year blocks.
- `broad_evidence_floor`: n>=60, assets>=12, groups>=3, quarters>=20. This does not
  guarantee power, independence, or adequate qualified cases.
- `conditional_survival_n_at_least40`: separate minimum qualified denominator.
  A larger n cannot compensate for a tiny qualified_n.
- A zero-success bootstrap can produce [0,0] by construction. Do not interpret
  this as proof that the underlying event probability is exactly zero.

## Waiting policy

- All setups use a common complete 10+63-session follow-up cohort.
- Original candidate date, price, ATR and depth are frozen; confirmation does
  not replace the pivot. Invalidation precedes confirmation on the same bar.
- `confirmed_n`, `invalidated_n`, `unconfirmed_n` partition eligible setups.
- `administratively_excluded`: endpoint setups without the full common window.
- `timely_durable_precision`: successes / confirmations.
- `timely_durable_yield`: successes / all eligible original setups.
- `base_timely_durable_rate`: immediate policy on exactly that common cohort.
- `conditional_survival`: hold rate among qualified confirmations only.
- `fixed_end_primary_precision`: secondary endpoint at original setup +63;
  main outcomes extend to confirmation +63.
- `missed_original_successes`: original successes not preserved by the policy,
  including qualification loss and extended-window failure, not just missed alerts.
- Waiting recall uses its conservative p+94 reference-followup convention.

## Standardized alignment

- `not_aligned` includes mixed or neutral available states; it is not synonymous
  with `explicitly_opposed`.
- Compare qualified candidates within age 0-5/6-10/11-21, distance <=1/1-2 ATR,
  and depth 4-6/>6 ATR strata, requiring at least5 cases per arm in each cell.
- Reference weights use all qualified available high-base events in common
  support, including neutral events for the explicit-opposition comparison.
- `retained_n/share`: retained aligned/comparison union.
- `target_retained_n/share`: fraction of the qualified base target represented.
- `standardized_delta`: aligned minus comparison survival, in proportion units.
- `bootstrap_blocks`: distinct half-year blocks in common-support comparisons.
- `valid_bootstrap_fraction`: proportion of draws with both arms in every fixed
  supported cell. Bounds are unavailable below 80% valid draws or fewer than
  two blocks. Very small arms and zero-success arms still require caution.

## Files

- `full_grid_development_validation.csv`: 4,868 rows = 2,434 rules x2 splits.
  These are selection/development results, not the complete grid on final test.
  It includes the principal detection metrics rounded to six significant digits;
  the original unrounded development/validation table remains in the research
  workspace and was used for selection. Final result tables retain full precision.
- `final_results.csv`: 34 frozen rules x primary/crypto pools =68 rows.
- `by_asset.csv`, `by_asset_group.csv`, `by_regime.csv`, `by_year.csv`: subgroup diagnostics.
  Regime recall is deliberately unavailable because pivot-date and signal-date
  regimes are different conditioning events.
- `anchor_basis_sensitivity.csv`: 34 rules x2 pools x13 variants =884 rows.
- `standardized_alignment.csv`: 720 fixed condition/comparator rows.
- `timeframe_conflicts.csv`: unstandardized conditions on the fixed high trigger
  dates, with each condition and its complement kept separate.
- `waiting_summary.csv`: 120 fixed policies.
- `selected_diagnostics.csv`: validation metrics, qualified uncertainty, strict
  outcomes, qualification breakdown and final signal dates.
- `outcome_sensitivity.csv`: named distance, age, horizon, depth and exclusion
  analyses. Not a new search for the preferred outcome definition.
- `illustrative_prices.csv`, `illustrative_events.csv`: explicitly selected
  example windows only, not the entire OHLCV dataset or alert stream.
- `coverage.csv`, `pivot_counts.csv`: usable indicator history and label counts.
- JSON locks/registrations/summaries: study provenance and frozen rule identities.
- `data_audit/`: original data manifest, canonical content hashes, source
  cross-check and calendar checks. Provider data are current-vintage history.
