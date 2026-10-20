# Q15 — Six discriminating acceptance requirements: evidence map

**Test suite:** `tests/test_vol_noise_robust_realized.py`. It is hermetic: synthetic data only, no repo files, no network, no clock.

**Command:**

```
PYTHONPATH=<Q15> PYTHONDONTWRITEBYTECODE=1 /opt/homebrew/bin/python3.12 -m pytest <Q15>/tests/test_vol_noise_robust_realized.py --rootdir <Q15> --noconftest -p no:cacheprovider -q
```

**Result:** `6 passed`, exit 0.

**Discrimination.** A mutation check ran on scratch copies of the module; the deliverable was never edited. One unmutated control copy passes 6/6. Each of six single-line mutants is killed by the test of the requirement it attacks:

| Mutant | Killed by |
|---|---|
| Parzen weight coefficient 6 → 5 | req1 |
| Kernel drops the factor 2 on autocovariances | req2 and req4 |
| Gap returns enter intraday variance (max_gap ×1e9) | req3 |
| As-of filter leaks future knowledge (cutoff +1e9) | req5 |
| `ACTIVATION["gate"] = True` | req6 |
| Noise flag threshold disabled (0.10 → 1.10) | req2 |

Every mutant's run exits 1. The harness is scratch only and is not shipped.

| # | Requirement | Test | How it discriminates | Supporting artifact |
|---|---|---|---|---|
| 1 | Noise-free synthetic controls recover the specified integrated-variance target | `test_req1_noise_free_synthetic_controls_recover_integrated_variance_target` | The simulator's per-step variance sums exactly to the target IV. RV and the H=0 kernel are exact on a deterministic path. Parzen weights are pinned at 0, ½, 1 and 1.5. With no noise, the Monte Carlo relative bias is under 2% (tick RV), 3% (kernel) and 6% (preaveraged, sparse), under both constant and stochastic vol. | `mc_bias_table.json` (500 reps, both vol modes, `all_pass: true`) |
| 2 | Added bid/ask bounce is not read uncritically as economic variance | `test_req2_bid_ask_bounce_is_not_read_uncritically_as_economic_variance` | With Roll-type bounce, raw RV excess equals the theoretical 2nω² to within ±10%, while the noise-aware estimate stays within 8% of the true IV. `noise_dominated` fires on every noisy path and on no clean path. The jump split is `noise_qualified`. Raw RV is still reported, labelled `raw_rv_includes_noise`. | `mc_bias_table.json`. On admitted data, `noise_by_year` in `result_confirmatory.json` reports noise share and lag-1 autocorrelation instead of silently absorbing them. |
| 3 | Sampling gaps, irregular times, halts and overnight returns have declared treatment | `test_req3_gaps_irregular_times_halts_and_overnight_have_declared_treatment` | `GAP_POLICY` declares no interpolation. A two-break tape gives exact intraday, overnight and total variance, and gap returns never enter the intraday estimator. Previous-tick sampling drops pre-first-tick grid points (no back-fill) and counts stale returns. NaNs and non-monotone times raise errors instead of being filled. Labels report overnight variance separately. | `evaluate.py`: weeks with an internal gap over 6 h are attrition (`attrition.train.by_reason.gap = 1`), never interpolated. |
| 4 | Estimator bias and variance are measured against simple controls across fixed noise regimes | `test_req4_bias_variance_measured_against_simple_controls_across_fixed_noise_regimes` | Bias, sd and RMSE are computed for 4 estimators × all fixed `NOISE_REGIMES`, with the RMSE identity checked. Tick-RV bias tracks theory. The kernel beats tick RV and sparse RV on RMSE under medium and high noise. Tick RV is at least as good as the kernel with no noise, an honest efficiency cost. | `mc_bias_table.json` |
| 5 | A historical corrected tape cannot alter earlier forecast inputs | `test_req5_historical_corrected_tape_cannot_alter_earlier_forecast_inputs` | A later correction to an in-window print leaves the label recomputed as of the old cutoff byte-identical, with the same `version_id`. Recomputing at the later cutoff gives a new `version_id` and a new value. The as-of tape keeps the latest revision known at the cutoff. A label cannot be built before its window closes. | Shown synthetically, by the unit test only. The empirical path never calls `asof_tape` or `build_versioned_label`: the admitted parquet carries no knowledge times or revision history, and `label_version` in `result_confirmatory.json` is a hash of the whole input set (inputs, prereg and spec). On the admitted tape a correction would appear only as an input-hash mismatch, which `evaluate.py` refuses (exit 4). |
| 6 | No new raw-data capture, variance forecast, gate or replacement accepted outcome label is silently activated | `test_req6_no_raw_capture_forecast_gate_or_accepted_label_is_silently_activated` | Checks `RESEARCH_ONLY is True`; the docstring starts "RESEARCH REFERENCE — NOT WIRED"; every `ACTIVATION` flag is False; module imports are limited to hashlib, json, math and numpy. No public symbol is named register, schedule, publish, gate, forecast, fetch, write, etc. Labels carry `research_only=True`, `accepted_label=False` and `is_forecast=False`. Re-import opens no file. | No repo file imports the module and nothing registers it. `result_confirmatory.json` carries `research_only: true` and `accepted_label: false`. |

## Scientific-contract items (beyond the six)

| Item | Where |
|---|---|
| Incumbent check / non-duplication | `PREREG.md` §2 "Non-duplication" |
| Baseline reproduced | `baseline_reproduction.json`; RUNS.log line 1, exit 0. The incumbent `vol_forecast` columns are reproduced, and the hourly 23:00 close matches the daily close on 3932/3932 days. |
| Freeze before outcomes | `FREEZE.log` at 10:13:59 UTC, before the first admitted-data run (10:16:59 bracket) |
| One dependence-aware comparison | `evaluate.py confirmatory`: chronological split, training-only ξ², moving-block bootstrap, honest N, attrition, INSUFFICIENT_DATA guard. It refuses a re-run without a PREREG_AMENDMENT reason (exit 5). |
| Hash guard | `evaluate.py` exits 3 on a PREREG/FREEZE mismatch and 4 on an input hash mismatch. A tamper dry run on a scratch copy returned 3. Every run appends to RUNS.log. |
