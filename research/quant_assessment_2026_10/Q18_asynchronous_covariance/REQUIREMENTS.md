# Q18 requirements → test map

Suite: `tests/test_async_session_covariance.py` (26 tests, hermetic: stdlib, numpy, pandas and
the module only; no repository file is opened). Module: `engine/async_session_covariance.py`
(research only; nothing imports it).

The table is keyed to the brief's six discriminating acceptance requirements (B1–B6). The
author's original contract tests (`test_req*`) are kept and listed where they also pin a
brief requirement.

| # | Brief requirement | How the module/study meets it | Pinning tests |
|---|---|---|---|
| B1 | Different exchange-close intervals are not silently labelled simultaneous observations. | `classify_pair_clock` returns SIMULTANEOUS only when every close offset is 0; otherwise NONSYNCHRONOUS / DST_VARYING; UNIDENTIFIED for an undeclared clock. `return_intervals` gives each return an explicit UTC interval; `overlap_pairs` shows an Asia return dated t overlaps US returns dated t−1 and t. Study artifact: `results/support_report.json` (SSE/HKEX vs NYSE = DST_VARYING, NYSE vs NYSE = SIMULTANEOUS). | `test_brief1_different_close_clocks_are_never_labelled_simultaneous`, `test_brief1_same_date_label_is_not_the_same_return_interval`, `test_req1_interval_map_is_explicit_utc_and_contiguous`, `test_req1_undeclared_clock_is_unknown_not_guessed`, `test_req2_simultaneous_closes_hy_equals_naive` |
| B2 | DST, half-days, holidays and nonoverlapping sessions are explicit. | `return_intervals` flags `holiday_gap`, `early_close`, `dst_shift`; `qualify_pair` counts them in `support` and returns NO_OVERLAP (not 0) when sessions never overlap; holiday gaps are absorbed by HY, never zero-filled. | `test_brief2_nonoverlapping_sessions_are_an_explicit_state_not_a_zero`, `test_brief2_dst_holiday_and_half_day_are_counted_in_support`, `test_req1_holiday_gap_and_early_close_flags`, `test_req2_holiday_gaps_are_absorbed_by_hy` |
| B3 | Daily data never yields invented intraday covariance precision. | `lag_aligned` accepts only a non-boolean integer session count (`TypeError` for 0.5, 1.0, bools, arrays, lists, strings); daily input yields exactly one interval per consecutive close pair, ending at the declared close time; no output key carries intraday/lead/causal/best/optimal/argmax/selected_lag/tuned; honest N is counted in time blocks, not daily rows. | `test_brief3_lag_is_an_integer_session_count_only`, `test_brief3_daily_input_yields_daily_resolution_only`, `test_brief3_honest_n_is_time_blocks_not_daily_rows`, `test_req5_block_bootstrap_is_seeded_and_reports_honest_blocks` |
| B4 | Synthetic correlated asynchronous paths test estimator bias and support limits. | `simulate_async_pair` (declared clocks, known rho); HY bias is below naive bias at rho 0.3 and 0.6; fewer than `min_pairs` overlaps gives INSUFFICIENT with no correlation. | `test_brief4_synthetic_bias_shrinks_for_hy_and_support_limit_is_enforced`, `test_req2_naive_same_label_attenuates_and_hy_recovers` |
| B5 | Chosen lags/windows are frozen before holdout comparison and not called causal direction. | One declared lag (default 1, integer only); no public callable or name contains lag-search/causal/lead/direction terms; module docstring states no lead/lag is a causal direction; the study's lags, windows and estimators were frozen in `PREREG.md` (sha in `FREEZE.log`) before the holdout run, and `evaluate.py` refuses to run on a hash mismatch. | `test_brief5_lag_is_frozen_by_declaration_and_never_called_causal`, `test_req3_only_declared_estimators_no_lag_search`, `test_brief3_lag_is_an_integer_session_count_only` |
| B6 | Input owner, missingness and context-only authority remain intact. | Inputs are never mutated; invalid prices are counted and bridged, never zero-filled; MEASURED / NO_OVERLAP / UNKNOWN / INVALID / EXCLUDED / PENDING / INSUFFICIENT stay distinct; `RESEARCH_ONLY = True`; the docstring declares context-only records; PSD is reported, never repaired (repair belongs to Q08). | `test_brief6_missingness_kept_inputs_untouched_context_only`, `test_req4_states_are_distinct_and_missing_is_never_zero`, `test_req4_invalid_price_is_bridged_not_zero_filled_and_zero_is_measured`, `test_req4_excluded_and_pending_states`, `test_req6_psd_is_reported_not_repaired_and_inputs_untouched`, `test_req6_out_of_bounds_corr_flagged_not_clipped`, `test_req6_inputs_are_bounded`, `test_no_silent_activation_module_contract` |

Also in the suite (inference helpers): `test_req5_newey_west_matches_iid_at_lag0_and_grows_with_autocorrelation`.

## Declared gaps

* **B6 input owner** is enforced at study level, not by a unit test: inputs are read-only
  macro-main `data/` files at vintage `cdab6268`, checked against the PREREG §4 sha256 table
  on every `evaluate.py` run and recorded in every RUNS.log record. The module itself takes
  arrays and has no notion of a file owner.
* **B5 freeze ordering** (PREREG before holdout) is a process property evidenced by
  `FREEZE.log`, the evaluate freeze guard and `RUNS.log`, not by a unit test. RUNS.log line 1
  (the baseline reproduction) predates the freeze; it is training-only and disclosed
  (PREREG §7, `PREREG_AMENDMENT.md` A2, RUNS.log note).
* **B3 at sub-daily resolution**: no intraday data is used anywhere; a future intraday
  extension would need its own study identity.

Study-level evidence for the estimator choice (not part of the unit suite): `PREREG.md` (frozen,
see `FREEZE.log`), `PREREG_AMENDMENT.md`, `evaluate.py` (freeze guard, appends to `RUNS.log`),
`report_support.py`, `results/primary_results.json`, `results/per_block.csv`,
`results/support_report.json`, `VERDICT.md`.

Served model: Claude Opus 5.5 (`claude-opus-5-5`).
