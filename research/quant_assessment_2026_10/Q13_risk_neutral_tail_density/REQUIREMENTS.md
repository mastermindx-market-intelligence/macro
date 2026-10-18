# Q13 — Acceptance requirements map

Each requirement is quoted verbatim from the brief and mapped to:

- the module mechanism in `engine/options_rn_tail_density.py`;
- the hermetic tests in `tests/test_options_rn_tail_density.py`;
- the proxy artifact in `results/`.

Each requirement then gets a status. All proxy evidence is **PROXY — not
admitted surface**. No admitted surface exists (PREREG §0, M1–M4), so the
phrase "on admitted surfaces" cannot be exercised on data. It is exercised on
synthetic arbitrage-free and noisy surfaces in the tests.

**Test suite result:** 27 passed, exit 0. That is 24 test functions, one of
them parametrized ×4. The exact command is in `_handoff/PR_BODY.md`.

## 1. "Nonnegative density and probability accounting pass on admitted surfaces."

**Module**

- `static_arbitrage_report` counts butterfly, monotonicity, slope-floor and
  price-bound violations.
- `repair_call_prices` applies PAVA on slopes clipped to `[-D, 0]`, plus a
  level shift.
- `density_from_call_grid` and `density_from_smile` report three groups of
  fields:
  - `total_mass`, `left_mass`, `right_mass`;
  - `negative_mass_after_repair`, `raw_negative_mass`;
  - a monotone CDF.

**Tests**

- `test_req1_butterfly_witness_is_detected_and_repaired_to_nonnegative_density`
- `test_req1_noisy_quotes_repair_removes_all_negative_mass_and_keeps_accounting`
- `test_req1_smile_density_is_nonnegative_sums_to_one_and_has_monotone_cdf`
- `test_req1_arbitrage_free_black76_grid_is_left_unchanged_by_repair`

**Proxy artifact:** `results/diagnostics.json` → `14_2_full_chain_report_TEST[*]`.

- The `density` fields on all 13 TEST dates show:
  - `total_mass` 1.0;
  - `negative_mass_after_repair` ≤ 7.6e-14;
  - repair change at most 6.6e-6 of the band half-width.
- The `quoted_surface_arbitrage` field shows the vendor-iv quoted surface
  itself is arbitrage-free on 0/13 dates, with a median of 39 butterfly
  violations. The audit detects this; it is not hidden.

**Status:**

- **Met in the module contract and tests.**
- On the proxy, the accounting passes for the smile density.
- On an admitted surface it is **not exercisable** (M4).

## 2. "Reintegrated option prices match source-compatible intervals at declared tolerance."

**Module**

- `reintegrate_call_prices` refuses strikes outside the grid.
- `reintegration_check(density, K, lo, hi, tol_rel=1e-6)` returns `n`,
  `n_outside`, `max_excess`, `max_excess_over_half_width`, `within` and
  `tolerance`.
- Source-compatible intervals come from `call_equivalent_bands`: declared
  iv half-width bands, with puts mapped through parity on the same basis.

**Tests**

- `test_req2_reintegrated_prices_fall_inside_declared_quote_bands_at_quoted_strikes`
- `test_req2_reintegration_flags_prices_outside_bands_and_refuses_outside_grid`

**Proxy artifact:** `results/diagnostics.json` → `14_2_full_chain_report_TEST[*].reintegration`.

- Within the band on **0/13** dates.
- A median of 92 of 190 quoted strikes fall outside.
- The maximum excess is a median of 3.30 half-widths (range 2.55–4.55).
- Tolerance is `1e-6·F`, about 7.4e-4.

**Status:**

- **Met in the module contract and tests** (detected and reported).
- **NOT met on the proxy:** a smoothed single smile does not reintegrate
  inside the declared band on the vendor-iv surface.
- `classify_identification` does not use reintegration, because the frozen
  PREREG §13 classifier list omits it. The proxy reached
  `PRICE_BOUNDS_ONLY` through the relative-width rule instead.
- Recorded as a limitation and gap in `VERDICT.md` §7 item 8.

## 3. "Forward/moment constraints use the same discount and forward basis."

**Module**

- One `ForwardBasis` (`from_forward`, `make_forward_basis`) carries `F`, `D`
  and `T`.
- Pricing (`black76_price`), parity (`put_to_call`), the bands, the
  Breeden–Litzenberger derivative and the forward check all take that same
  object.
- `forward_ok` requires the raw and the repaired prices to pass, at
  `1e-3·F` (amendment A1.6).

**Tests**

- `test_req3_forward_check_passes_when_prices_and_density_share_one_basis`
- `test_req3_forward_check_fails_on_discount_or_forward_mismatch` (×4: `D` and
  `F` at ±1%)
- `test_req3_put_call_parity_and_put_bands_use_the_same_basis`

**Proxy artifacts**

- `results/diagnostics.json` → `14_2_full_chain_report_TEST[*].density.forward_ok`:
  13/13, raw and repaired.
- `results/per_date.csv` columns `C_forward_ok` and `C_forward_ok_raw`: all
  `True` on 28/28 dates.
- §14.3, the ATM call/put iv gap: median 0.0136 on TEST. It shows that the
  available basis (SOFR, `q = 0`, American) is internally consistent but not
  a qualified basis (M2/M3).

**Status:**

- **Met** for internal basis consistency.
- The basis itself is a declared proxy (M2), not the Q12 basis.

## 4. "Tail truncation and extrapolation mass are reported."

**Module**

- `extrapolation_mass(density, k_lo, k_hi)` returns `mass_below_quoted`,
  `mass_above_quoted`, `extrapolated_mass`, `grid_truncation_mass`,
  `left_truncation_mass` and `right_truncation_mass`.
- The smile reports `extrapolated(k)` and `k_star_extrapolated`, and the
  wings are Lee-capped.

**Tests**

- `test_req4_narrow_grid_reports_positive_truncation_and_extrapolation_mass`
- `test_req4_wide_grid_truncation_mass_is_negligible`
- `test_req4_report_exposes_extrapolation_fields_and_flags_extrapolated_strike`
- `test_req4_smile_wings_are_explicit_and_lee_capped`

**Proxy artifacts**

- `results/diagnostics.json` §14.2 `density` fields:
  - extrapolated mass median 0.00213 (range 0.00086–0.00318);
  - left grid truncation median 0.00053;
  - right grid truncation about 0.
- `results/per_date.csv` column `C_k_star_extrapolated`: `True` on all 28
  dates, because `K* = 0.90F` lies outside the truncated estimator window.

**Status: Met.**

## 5. "Quote perturbations change uncertainty instead of generating false exact crash odds."

**Module**

- `perturbation_interval` takes uniform-in-band draws with a fixed seed and
  returns an interval with `measure == "Q"`.
- `tail_probability_bounds` gives the identified chord interval `[L, U]`.
- `classify_identification` applies the frozen thresholds.
- `rn_tail_report` withholds `point_estimate` and `perturbation_interval`
  under `PRICE_BOUNDS_ONLY`.

**Tests**

- `test_req5_perturbation_interval_widens_with_quote_uncertainty`
- `test_req5_identified_bounds_widen_with_band_and_contain_the_true_q_probability`
- `test_req5_weak_wing_support_restricts_output_to_price_bounds_only`
- `test_req5_full_density_only_when_identified_and_point_sits_inside_bounds`
- `test_req5_classifier_rules_are_the_frozen_thresholds`
- `test_req5_perturbation_is_deterministic_for_a_fixed_seed`

**Proxy artifacts**

- `results/compare_summary.json`: the `falsifier` fires (median relative
  width 1.588 > 0.5), and `output_restriction` is `PRICE_BOUNDS_ONLY`.
- §14.1 band scaling: the median width grows from 0.0368 (0.5×) to 0.0595
  (1×) to 0.0849 (2×).
- §14.2: `identification` is `PRICE_BOUNDS_ONLY` on 13/13 dates, and
  `point_estimate` is null.
- The direct diagnostic perturbation interval (median width 0.00117) is a
  median of 46× narrower than `[L, U]`. This is exactly the false precision
  that the withholding rule prevents.

**Status: Met.** Uncertainty widens with the band. On the proxy,
`rn_tail_report` emits no point estimate and no perturbation interval. The
per-date `q_C`, `q_B1` and `q_B0` columns in `results/per_date.csv` are
harness comparison inputs for the H1 distance metric. They are PROXY and
diagnostic only, never a reported tail estimate.

## 6. "Risk-neutral and physical probabilities remain explicitly different throughout output and consumers."

**Module**

- `MEASURE_LABEL`, with `measure == "Q"` on the density, bounds, the
  perturbation interval and the report.
- No physical, real-world, crash or forecast key exists.
- `to_physical` always raises `MeasureError`.
- `admitted = False`, `label = "PROXY — not admitted surface"` and
  `verdict = "INSUFFICIENT_DATA"`.
- There are no consumers: nothing imports the module.

**Tests**

- `test_req6_report_is_labeled_risk_neutral_and_carries_no_physical_keys`
- `test_req6_conversion_to_physical_probability_is_refused`
- `test_req6_report_is_unadmitted_proxy_with_insufficient_data_verdict`
- Also `test_no_silent_activation_module_contract` (nothing registers,
  schedules or activates).

**Proxy artifacts**

- `results/compare_summary.json` has `measure: "Q"` and a `measure_label`
  stating "not a physical probability, not crash odds, not a forecast".
- Each `perturbation_interval` in `results/diagnostics.json` carries
  `measure: "Q"`.
- `VERDICT.md` header and §8.

**Status: Met.**

## Additional contract tests

- `test_contract_bounded_inputs_are_rejected_not_truncated` covers
  `MAX_QUOTES`, `MAX_DRAWS`, non-finite inputs, an invalid basis,
  non-monotone grids and degenerate smiles.
- `test_no_silent_activation_module_contract` checks four things:
  - re-import opens no files;
  - it leaves the environment unchanged;
  - it leaves the root logging handlers unchanged;
  - it pulls in no new modules beyond numpy and scipy.

  It also checks that no public name implies registration, scheduling or
  wiring.
