# Q07 requirements → evidence map

Tests live in `tests/test_vol_fitted_har.py`. They are hermetic: synthetic data on an integer index, with no repository data, no network and no calendar dates. The module under test is `engine/vol_fitted_har.py` (RESEARCH_ONLY, not wired).

| # | Requirement | How the module meets it | Tests | Empirical artifact |
|---|---|---|---|---|
| 1 | The fit and forecast at a cutoff use only information available at that cutoff. | `har_forecast_path` refits at each grid cutoff `c`. The forecast for session `s` uses `X[s]`, which is built from trailing returns. Every control is a trailing or recursive statistic. | `test_req1_fit_and_forecast_use_only_information_at_cutoff`: perturbing all returns after `s` leaves forecasts ≤ `s` bit-identical. `test_req1_controls_are_causal` covers C0, C1 and C2. | `results/primary_results.json` → `support` |
| 2 | Overlapping forward windows are excluded from training. Unmatured targets cannot move the fit. The back-transform uses training residuals only. | `training_mask` requires `t + h ≤ c` (an embargo of h sessions). Duan smearing is computed on residuals from those rows only. C3 scaling and the interval quantiles use the same mask. | `test_req2_forward_windows_excluded_from_training`, `test_req2_unmatured_targets_cannot_move_the_fit`, `test_req2_back_transform_uses_training_residuals_only`, `test_req2_c3_scale_uses_matured_training_targets_only`, `test_req2_interval_quantiles_use_matured_training_targets_only` | PREREG §4 and §5; `RUNS.log` run 2 |
| 3 | The daily close-to-close proxy and the HF integrated-variance label never mix silently. | `LabeledTarget` carries `DAILY_CC_MSR`. `forward_target` refuses any other label. `require_label` refuses unlabelled or foreign targets. `assert_single_label` refuses mixes. | `test_req3_daily_and_hf_labels_never_mix_silently` | `primary_results.json` → `label` |
| 4 | QLIKE handling of zero or near-zero variance is declared and finite, and floor sensitivity is reported. | `qlike` floors both `y` and `f` at a declared positive floor and refuses floor ≤ 0. `FLOOR_SENSITIVITY = (1e-10, 1e-8, 1e-6)`. evaluate.py recomputes the whole pipeline (fit plus loss) at each floor. | `test_req4_qlike_zero_variance_handling_is_declared_and_finite`, `test_req4_floor_sensitivity_reports_every_declared_floor` | `primary_results.json` → `by_floor` (KEEP at all three floors; 0 targets below any floor) |
| 5 | Dependence-aware uncertainty, with KEEP only if the challenger beats EVERY simple control by the bar. | There is a paired circular block bootstrap over per-session cross-sectional mean losses, plus a Newey–West t. Honest N is counted in blocks. `decide` requires rel ≥ bar and a diff-CI lower bound > 0 against each control, and no floor flip. It returns INSUFFICIENT_DATA below 30 blocks or 5 assets. | `test_req5_block_bootstrap_detects_real_gain_and_not_noise`, `test_req5_keep_requires_beating_every_simple_control_by_the_bar` | `primary_results.json` → `by_floor["1e-08"].comparisons` (37 blocks, 13 assets) |
| 6 | Research success changes no cone probability, model promotion, portfolio budget or live forecast default. | `production_effects(verdict)` returns four False keys for every verdict and refuses unknown verdicts. `RESEARCH_ONLY = True`. Nothing imports the module, and there is no register/activate/schedule/promote/wire/main/run surface. | `test_req6_research_success_changes_no_production_effect`, `test_no_silent_activation_module_contract` | `primary_results.json` → `production_effects` (all False) |

Additional pins:
- `test_incumbent_reimplementation_matches_reference_formula` checks the module's C0 against the `har_vol` formula.
- `results/baseline_reproduction.json` gives max abs diff 0 against `engine/vol_forecast.har_vol` on all 13 ETFs.
- `test_bounded_inputs_are_enforced` covers the MAX_ROWS bound and refuses non-positive closes.

Focused command (exit 0, 16 passed; the two C3/interval tests were added by the finishing stage, see `POST_FREEZE_DISCLOSURES.md` §4):

```
PYTHONPATH=<Q07> PYTHONDONTWRITEBYTECODE=1 /opt/homebrew/bin/python3.12 -m pytest <Q07>/tests/test_vol_fitted_har.py --rootdir <Q07> --noconftest -p no:cacheprovider -q
```
