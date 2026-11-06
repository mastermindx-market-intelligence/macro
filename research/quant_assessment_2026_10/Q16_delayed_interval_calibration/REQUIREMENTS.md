# Q16 requirements → code, tests, evidence

Module: `engine/interval_delayed_calibration.py`
Tests: `tests/test_interval_delayed_calibration.py`
Test run: 20 passed, exit code 0. The test command is the one in PR_BODY.md.

## req1 — No update consumes a label before its maturity or availability

- **Code**
  - `label_available` and `matured_mask` encode the rule j + h + avail_lag ≤ i.
  - `run_delayed_calibration` lets origin i use only origins j ≤ i − delay and records `consumed_max`.
  - `maturity_violations` counts any breach.
  - `fixed_split_quantile` and `tune_gamma` use only labels that matured by the training cutoff.
  - `run_leaky_aci_diagnostic` is the invalid contrast. It is flagged with `uses_immature_labels=True`.
- **Tests**
  - `test_req1_runner_never_consumes_immature_label`: covers 3 methods × 2 availability lags.
  - `test_req1_future_label_cannot_change_earlier_quantiles`: perturbs future labels and checks that the prefix is bit-identical.
  - `test_req1_training_tuning_and_fixed_quantile_ignore_labels_maturing_after_cutoff`.
  - `test_req1_maturity_clock_boundaries_and_leaky_diagnostic_is_flagged`.
- **Evidence**
  - Independent evidence: the future-label perturbation test (bit-identical prefix) and the LEAKY contrast.
  - `empirical.json` `maturity_violations`: 0 for fixed, rolling, aci and aci_lag1 on every asset; 5505 for leaky. This count is partly self-confirming (it checks the `consumed_max` each runner reports for itself), so it is supporting evidence only.
  - `controls.json` `maturity_violations_aci_total`: 0.
  - Provenance: the reproduction run (RUNS.log record 4, under `PREREG_AMENDMENT.md`) hash-checked the shipped module and reproduced all three result files byte for byte.

## req2 — Repeated forecasts of the same outcome are not independent evidence

- **Code**
  - `honest_block_count`: non-overlapping horizon blocks over distinct origins.
  - `collapse_repeated_forecasts`: one value per outcome.
  - `circular_block_bootstrap`: block length 2h = 44.
  - `newey_west_se`: lag 2h.
- **Tests**
  - `test_req2_overlapping_daily_forecasts_collapse_to_honest_blocks`.
  - `test_req2_repeated_forecasts_of_same_outcome_count_once`.
  - `test_req2_block_bootstrap_widens_for_overlapping_outcomes`.
- **Evidence**: honest N = 134 blocks, not 14,685 rows. The bootstrap uses 67 blocks of 44. All five assets share one date axis, so they add no independent blocks.

## req3 — Coverage, width and interval score are all reported; wide intervals cannot win on coverage

- **Code**: `interval_metrics` returns covered, width and Winkler interval score. `summarize_metrics` reports all three.
- **Primary metric**: interval score, not coverage (PREREG §8).
- **Tests**
  - `test_req3_interval_score_formula_and_all_three_metrics_reported`.
  - `test_req3_arbitrarily_wide_interval_loses_on_interval_score`: a ±50 interval reaches coverage 1.0 but scores more than 10× worse.
- **Evidence**: VERDICT table. ACI has the highest coverage (0.803) but loses on interval score to FIXED (0.790).

## req4 — Abrupt-shift and stationary controls separate adaptation from noise chasing

- **Code**
  - `simulate_overlapping_scores`: overlapping h-sums of t(5) innovations, with an optional variance shift.
  - `control_experiment`: compares fixed, rolling, aci and aci_leaky.
  - `discrimination_verdict`: three criteria — stationary no-noise-chasing, shift-up recovery, shift-down sharpening.
- **Tests**
  - `test_req4_live_controls_adapt_to_shift_and_stay_quiet_when_stationary`.
  - `test_req4_discrimination_rule_rejects_noise_chasing_and_non_adaptation`.
- **Evidence** (`controls.json`, 200 reps per scenario): stationary ratio 1.0198; shift-up gap 0.0064 for ACI vs 0.318 for FIXED; down-shift sharpens; `controls_discriminate=true`.

## req5 — Per-regime support is disclosed without universal conditional-coverage claims

- **Code**: `regime_support` returns n_rows, honest_blocks, coverage and support_ok (at least 20 blocks) per regime. It always returns `conditional_coverage_claim=False`.
- **Test**: `test_req5_regime_support_discloses_blocks_and_never_claims_conditional_coverage`.
- **Evidence** (`empirical.json` `regime_support`):

  | regime | blocks | ACI coverage | FIXED coverage |
  |---|---|---|---|
  | low | 124 | 0.705 | 0.696 |
  | mid | 128 | 0.813 | 0.790 |
  | high | 126 | 0.897 | 0.889 |

  Coverage is not conditionally uniform, and none is claimed.

## req6 — CN-HAR-2 and other registrations, trials and live forecasts are unchanged

- **Code**: pure functions only. There is no I/O at import, no registry, and `RESEARCH_ONLY = True`. `PROTECTED_REGISTRATIONS` names what is out of scope. Nothing imports the module.
- **Tests**
  - `test_req6_inputs_and_registrations_unchanged_and_nothing_written`: inputs are not mutated, a stand-in registry is unchanged, and the tmp cwd stays empty.
  - `test_no_silent_activation`.
- **Evidence**
  - The diff is new files only, listed in MANIFEST.json, with no edit to any existing file.
  - The trial ledger, calibration hub and CN-HAR-2 prereg were not written.
  - The incumbent `vol_forecast.py` is byte-identical to `_base`.
