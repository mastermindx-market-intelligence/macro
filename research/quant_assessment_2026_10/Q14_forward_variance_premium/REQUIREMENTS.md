# Q14: the six acceptance requirements and where each is proven

This file maps each of the brief's discriminating requirements to two kinds of proof:
- a hermetic test in `tests/test_vol_horizon_variance_premium.py`, which uses synthetic data only and imports only stdlib, numpy, scipy, pandas and the module
- an empirical artifact in this directory

Command used to run the tests (exit 0, 18 passed):

```
PYTHONPATH=<Q14 root> PYTHONDONTWRITEBYTECODE=1 python3.12 -m pytest tests/test_vol_horizon_variance_premium.py --rootdir <Q14 root> --noconftest -p no:cacheprovider -q
```

## 1. Both legs share horizon, annualization, calendar/session and variance units

**Mechanism:**
- `HorizonBasis` fixes four things:
  - the horizon, as a positive and bounded integer number of calendar days
  - the day-count basis (`calendar365` by default)
  - the unit, where only `horizon_variance` is admitted
  - the session close
- `vol_index_to_horizon_variance` maps index points to `(level/100)^2 * h/365`.
- `daily_variance_to_horizon_variance` scales a daily variance by the expected number of trading days in the horizon, `252 * h/365`.
- `HorizonBasis.basis_days` gives the horizon in the day count's own units: calendar days under `calendar365`, expected trading days `252 * h/365` under `trading252`. `year_fraction`, `atm_proxy_leg` and `annualized_vol_view` all use it, so both day counts give the same horizon variance and annualized view (audit M4).
- `ImpliedLeg` and `PhysicalLeg` each carry a basis and an as-of date.
- `build_premium` and `ex_post_premium` refuse a mismatch in horizon, day-count, units or as-of.
- A session-close mismatch is refused unless `acknowledge_session_offset=True`. The offset is then written into the record's notes: VIX 16:15 ET vs NYSE 16:00 ET.
- Volatility points are never accepted as variance.

**Tests:**
- `test_req1_vol_index_converts_to_calendar_horizon_variance_not_vol_points`
- `test_req1_daily_variance_scales_by_expected_trading_days_in_horizon`
- `test_req1_trading252_basis_is_expected_trading_days_and_consistent_with_calendar365`
- `test_req1_premium_refuses_mismatched_horizon_daycount_session_or_asof`
- `test_req1_basis_rejects_non_variance_units_and_unbounded_horizon`

**Empirical:** the unit-mismatch receipt in `result_baseline.json`.
- The incumbent vol-point spread and the horizon-variance premium have correlation 0.847.
- Their signs never disagree, which is algebraic.
- Their magnitudes diverge with the volatility level.

## 2. Forward-realized labels never leak into the contemporaneous estimate

**Mechanism:**
- `build_premium` refuses two kinds of `PhysicalLeg`:
  - any leg whose `kind` is not `forecast`
  - any forecast whose `information_time` is after its `asof`
- A forward label (`kind = "forward_label"`) can enter only `ex_post_premium`.
- `forward_realized_variance` sums squared returns on days in (t, t+h].
- `trailing_realized_variance` sums squared returns on days in (t−h, t] only.
- An incomplete window, or a missing return inside one, yields NaN for that leg, never a partial sum.
- In the study:
  - OLS coefficients are fit on training rows only.
  - A 31-calendar-day embargo separates train from holdout.

**Tests:**
- `test_req2_forward_label_cannot_enter_ex_ante_premium`
- `test_req2_forward_label_uses_only_returns_after_asof_and_trailing_only_before`
- `test_req2_missing_return_inside_window_voids_both_legs`
- `test_req5_coefficients_are_fit_on_training_rows_only` (shared with requirement 5)

**Empirical:** the split block of `result_compare.json`. The embargo dropped 18 rows, and the attrition counts are reported.

## 3. Absent overnight or tail-strike coverage is explicit

**Mechanism:**
- Both legs must carry a coverage receipt, or construction fails:
  - `ImpliedLeg` requires the keys `tail_strikes` and `overnight`.
  - `PhysicalLeg` requires the keys `overnight` and `sampling`.
- `realized_coverage(sampling)` admits only two samplings:
  - `close_to_close`, which includes overnight moves
  - `open_to_close`, which excludes them
- `realized_coverage` always states `intraday_path = not_observed_daily_sampling`.
- `strip_variance` reports:
  - the strike bounds `k_low_over_forward` and `k_high_over_forward`
  - whether each wing stopped at zero bids
  - its `discretization`
  - `jump_correction = "none"`
- Truncation is disclosed as a downward bias on the strip and is never silently corrected.

**Tests:**
- `test_req3_overnight_coverage_is_explicit_for_each_sampling`
- `test_req3_tail_strike_truncation_is_flagged_and_biases_strip_down`

**Empirical:**
- Labels are close-to-close, so overnight moves are included. This is recorded in every receipt.
- The forecast leg has its own receipt (`demeaned: true`, `returns: simple_pct`, estimator line), separate from the label's (`demeaned: false`, log returns). This fixes audit M3; see `PREREG_AMENDMENT.md`.
- The VIX strip's truncation and discretization are disclosed in `PREREG.md` §9 and in the Limitations section of `VERDICT.md`.

## 4. Proxy and model-free-style strip estimates are never mixed in one history silently

**Mechanism:**
- `ImpliedLeg.measure_kind` must be `strip` or `atm_proxy`; anything else raises.
- `assemble_history` refuses a history that mixes kinds, horizons or bases, unless `segment_by_kind=True`. In that case it returns an explicit `{kind: records}` segmentation.
- `strip_variance` labels its result `measure_kind = "strip"`, and `atm_proxy_leg` labels its result `atm_proxy`.

**Tests:**
- `test_req4_strip_recovers_flat_vol_and_is_labelled_strip_not_proxy`
- `test_req4_history_refuses_mixed_strip_and_proxy_unless_segmented`

**Empirical:**
- The entire study history is one kind, `strip` (the vendor VIX).
- No ATM-proxy row entered.
- `assemble_history` was called without segmentation and accepted the history.

## 5. Incremental evidence is judged against simple IV/RV controls with dependence-aware uncertainty

**Mechanism:** `incremental_comparison` compares controls C = [1, IV2, RV_trail] with A = C + premium_hat. It reports:
- MSE (primary) and QLIKE (secondary)
- a moving-block bootstrap of the per-row loss difference (block 63, B 2000, seed 14)
- a Newey-West HAC t-statistic (42 lags)
- stability across chronological thirds

`evaluate.py` adds honest N as non-overlapping label windows and 63-day blocks.

**Tests:**
- `test_req5_informative_extra_leg_is_kept_and_noise_leg_is_rejected`
- `test_req5_coefficients_are_fit_on_training_rows_only`
- `test_req5_block_bootstrap_and_hac_widen_under_serial_dependence`
- `test_req5_qlike_is_zero_at_the_truth_and_positive_elsewhere`

**Empirical:** `result_compare_T1_original.json` holds the single frozen comparison (T1 record), repeated byte-identically. The post-audit re-run `result_compare.json` matches it on every number. The result is **REJECT**:
- the relative MSE reduction is 2.02%, below the 5% bar
- the bootstrap lower bound is −7.28e-08, which is not above zero
- the HAC t-statistic is 1.10
- QLIKE is slightly worse

## 6. No expected-profit, risk probability, trade selection or short-volatility authority is inferred

**Mechanism:**
- The module computes measurements only. Every record and comparison output carries `authority = "none"`.
- `assert_no_authority` refuses any output that contains:
  - any authority value other than `"none"`
  - a forbidden key such as `expected_profit`, `probability`, `trade_signal`, `rank`, `size`, `short_vol` or `recommendation`
- The module sets `RESEARCH_ONLY = True` and has no import-time side effects and no registration.
- Nothing in the repository imports it.

**Tests:**
- `test_req6_records_carry_no_profit_probability_trade_or_short_vol_authority`
- `test_no_silent_activation_module_contract`

**Empirical:** `VERDICT.md` labels the positive mean ex-post premium as a spread between a risk-neutral price and a physical outcome. It is not an expected profit, not a probability and not a reason to sell volatility.

## Run and freeze receipts

- `PREREG.md` was frozen before any outcome was read, and its sha256 is recorded in `FREEZE.log`.
- `evaluate.py` re-hashes `PREREG.md` on every run and refuses with exit 2 on a mismatch. RUNS.log entry 5 exercises this on a scratch copy, which does not ship.
- Every run appends a line to RUNS.log with:
  - the command
  - the exit code
  - the input sha256s
  - the output sha256s
- RUNS.log entries:
  - entry 1 is the baseline reproduction
  - entries 2 and 3 are the comparison, run twice with an identical hash
  - entries 4 to 6 are a manual note, the refusal check and the docstring-edit record
  - entries 7 and 8 are the audit M1/M2 disclosures, written after `PREREG_AMENDMENT.md` and before any re-run
  - entry 9 is the single post-audit comparison re-run, exit 0
  - entry 10 is the field-by-field reproduction check: only the pre-declared differences appear
