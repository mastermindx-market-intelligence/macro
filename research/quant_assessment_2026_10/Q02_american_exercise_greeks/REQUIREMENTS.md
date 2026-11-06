# Q02 — requirement map

This file maps each requirement frozen in PREREG section 8 to the focused tests in
`tests/test_options_american_exercise.py` and to the evaluation artifacts.

**Test totals.** 81 tests are collected, and all 81 pass with exit 0 (the latest logged `pytest`
block in `RUNS.log`, under amendment A2). Amendment A2 added 8 tests for independent-audit
finding M1: 6 in req4 and 2 in req6. The focused command is:

```
PYTHONPATH=<Q02 root> PYTHONDONTWRITEBYTECODE=1 python3.12 -m pytest \
  tests/test_options_american_exercise.py --rootdir <Q02 root> --noconftest -p no:cacheprovider -q
```

**Hermeticity.** The tests are hermetic:

- They are synthetic, in relative units, with integer minute clocks.
- They do no file reads beyond importing the module, scan no repository tree and read no wall
  clock.
- They import only stdlib, numpy, scipy, pandas and the module.

## req1: European limit agrees with the shared formula (T1a–T1g)

26 tests.

| check | test | cases |
|---|---|---|
| T1a–T1d: FD price, delta, gamma, vanna and charm vs analytic at 4N | `test_req1_t1a_t1d_european_fd_matches_shared_formula_at_finest_grid` | 12 (call/put × K ∈ {80, 100, 120} × T ∈ {0.5, 0.1}) |
| T1e: module analytic Greeks vs `engine/greeks.py` formula, abs ≤ 1e-12 | `test_req1_t1e_module_analytic_greeks_equal_greeks_py_formula` | 10 |
| T1f: 4N error < N error (ATM price, delta, gamma) | `test_req1_t1f_refinement_reduces_european_atm_error` | 2 |
| T1g: one-cash-dividend European FD vs Gauss–Hermite quadrature | `test_req1_t1g_one_cash_dividend_european_fd_matches_quadrature` | 2 |

Artifacts:

- `results/e1_numerical.json`: T1a–T1g all pass;
- `results/baseline.json`: the code baseline is reproduced over 28 cases, with max abs diff 0.0
  against `engine/greeks.py` `bs_greeks`.

## req2: American constraints and independent lattice agreement (T2a–T2f)

15 tests.

| check | test | cases |
|---|---|---|
| T2a: American put ≥ intrinsic at every node | `test_req2_t2a_american_put_at_or_above_intrinsic_at_every_node` | 3 |
| T2b: American ≥ European on the same grid | `test_req2_t2b_american_at_or_above_european_on_same_grid` | 4 |
| T2c: put ≤ K, call ≤ S | `test_req2_t2c_american_put_below_strike_and_call_below_spot` | 3 |
| T2d: American call (q = 0, no dividend) equals European | `test_req2_t2d_american_call_without_dividends_equals_european` | 1 |
| T2e: American put FD vs CRR (2,000 steps) | `test_req2_t2e_american_put_fd_matches_independent_crr_lattice` | 3 |
| T2f: deep-ITM dividend call FD vs CRR-VN, premium ≥ 0.5 | `test_req2_t2f_deep_itm_dividend_call_matches_crr_vn_and_shows_premium` | 1 |

Artifact: `results/e1_numerical.json`. T2a–T2f all pass, and the T2f early-exercise premium is
3.83.

## req3: point-in-time dividends and expiry clock

6 tests.

| behaviour | test |
|---|---|
| a post-cutoff record leaves the price bit-identical to the no-dividend price | `test_req3_post_cutoff_record_leaves_price_bit_identical_to_no_dividend_price` |
| a pre-cutoff revision changes it; a later revision does not | `test_req3_pre_cutoff_revision_changes_the_price_and_later_revision_does_not` |
| out-of-window and cancelled records change nothing | `test_req3_out_of_window_and_cancelled_records_change_nothing` |
| a look-ahead cutoff raises | `test_req3_look_ahead_cutoff_raises` |
| AM_OPEN vs PM_CLOSE changes T and the price | `test_req3_am_open_versus_pm_close_changes_time_and_price` |
| an unknown settlement clock is UNAVAILABLE | `test_req3_unknown_settlement_clock_is_unavailable` |

Real-data artifacts:

- `results/attrition.json`: the stage-6 settlement clock and the stage-7 PIT dividend schedule
  have 0 rows of support;
- `results/absence_scan.json`: 0 dividend-schedule candidates anywhere under the data root.

## req4: refinement classification (CONVERGED / INTERVAL / UNAVAILABLE)

12 tests.

| behaviour | test |
|---|---|
| a smooth European case is CONVERGED for every quantity | `test_req4_smooth_european_case_is_converged_for_every_quantity` |
| a synthetic non-convergent sequence is INTERVAL with no point value | `test_req4_synthetic_nonconvergent_sequence_is_interval_without_point_value` |
| a non-finite sequence is UNAVAILABLE | `test_req4_non_finite_sequence_is_unavailable` |
| the ATM European price interval brackets the analytic value | `test_req4_european_atm_price_interval_brackets_the_analytic_value` |
| a near-boundary American put never reports CONVERGED gamma/vanna/charm | `test_req4_near_boundary_american_put_never_reports_converged_higher_derivatives` |
| a charm stencil straddling an ex-date is UNAVAILABLE | `test_req4_charm_stencil_straddling_an_ex_date_is_unavailable` |
| an in-bounds sigma whose frozen +/- 0.01 vanna bump leaves SIGMA_BOUNDS (0.015, 4.995; American and European) gives vanna UNAVAILABLE `vol_bump_out_of_bounds`, no exception, bump still 0.01 (A2, audit M1; 4 cases) | `test_req4_vol_bump_leaving_sigma_bounds_makes_vanna_unavailable_not_an_error` |
| a bump that touches SIGMA_BOUNDS exactly (0.02, 4.99) still reports vanna (A2; 2 cases) | `test_req4_vol_bump_touching_sigma_bounds_still_reports_vanna` |

Artifact: `results/e1_numerical.json` `classification_status`. It has 80 classifications: 74
CONVERGED and 6 INTERVAL, all of them prices near the strike kink.

## req5: units are explicit and discriminating

3 tests.

| behaviour | test |
|---|---|
| per-share to per-contract needs an explicit multiplier (10-share adjusted ≠ 100) | `test_req5_per_share_to_per_contract_needs_an_explicit_multiplier` |
| decimal to vol points is ×100; vega per 1.00 vol to per vol point is /100 | `test_req5_decimal_vol_points_and_vega_units_are_distinct` |
| annual to daily charm needs a declared 365 or 252 basis; unknown labels and undeclared bases raise | `test_req5_annual_to_daily_charm_needs_a_declared_basis` |

## req6: fail-closed applicability selector

16 tests.

| behaviour | test | cases |
|---|---|---|
| each missing term gives UNAVAILABLE with a named reason | `test_req6_each_missing_term_fails_closed_with_a_named_reason` | 11 |
| an estimated or incomplete dividend schedule fails closed; missing ≠ declared-empty | `test_req6_estimated_or_incomplete_dividend_schedule_fails_closed` | 1 |
| all failing reasons are reported together; no 100 is assumed; no dataclass or converter default | `test_req6_all_failing_reasons_are_reported_together_and_no_100_is_assumed` | 1 |
| model choice follows declared terms only | `test_req6_selector_model_choice_follows_declared_terms_only` | 1 |
| an edge-volatility contract (sigma 0.015, 4.995) prices without raising and vanna fails closed (A2, audit M1) | `test_req6_edge_volatility_contract_prices_without_raising_and_vanna_fails_closed` | 2 |

The 11 named reasons covered by the parametrized test are:

- `exercise_style_unknown` (None and BERMUDAN);
- `deliverable_unknown` (kind and shares);
- `adjusted_deliverable_unknown` (two adjusted roots);
- `non_share_deliverable_not_modelled`;
- `multiplier_unknown`;
- `settlement_clock_unknown`;
- `dividend_metadata_missing`;
- `rates_missing`.

Real-data artifact: `results/selector.json`. All 4,418,705 chain rows are UNAVAILABLE in both
arms, with named reasons, and 0 rows are decided otherwise.

## No silent activation

3 tests.

| behaviour | test |
|---|---|
| `RESEARCH_ONLY is True`; docstring starts "RESEARCH REFERENCE — NOT WIRED" and carries the verdict; no register/activate/wire/schedule/promote/publish/emit names; only stdlib, numpy and scipy imports | `test_no_silent_activation_research_only_and_registers_nothing` |
| calls leave module globals unchanged and import nothing beyond numpy and scipy | `test_no_silent_activation_calls_leave_globals_and_imports_unchanged` |
| a fresh import performs no file I/O and no registration | `test_no_silent_activation_fresh_import_has_no_side_effects` |

Nothing in the repository imports `engine.options_american_exercise`. Q02 adds new files only,
and `engine/greeks.py` is byte-identical (sha256 `d471f5ed…a8d9c`).

## Evaluation-protocol requirements (commission)

| requirement | where met |
|---|---|
| Incumbent refresh and collision check | PREREG section 12 |
| Inspected baseline reproduced, or its absence proven, and logged | `results/baseline.json`: code baseline reproduced; empirical B1 absent with no price column. Logged in `RUNS.log` runs 2 and 3 with command, exit code and input/output sha256s (run 3, under A2, reproduces every run-2 output byte for byte except `inventory.json`, which records the new module and test hashes) |
| PREREG frozen before outcomes | `FREEZE.log`. PREREG sha256 `9ae188f1…3676` is unchanged. Amendments A1 and A2 are each frozen in `AMENDMENT_FREEZE.log` before the run they authorize |
| evaluate.py refuses on a hash mismatch and logs every run | Stage-0 guards: exit 2 on a PREREG or amendment mismatch, exit 3 if already run. Every run appended to `RUNS.log`. A retained synthetic-root exercise of these guards is in `guard_check/transcript.json` (A2, audit M2) |
| Exactly one dependence-aware empirical comparison, or INSUFFICIENT_DATA naming the missing input | HG fails, so E2 was NOT_RUN. VERDICT section 1 names the missing inputs: exercise style, deliverable/multiplier, settlement clock, PIT dividend schedule and option price |
| Focused test passes with exit 0 | latest `RUNS.log` pytest block: `81 passed` |
