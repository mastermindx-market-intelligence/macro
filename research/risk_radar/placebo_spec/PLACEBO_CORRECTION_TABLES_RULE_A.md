# Placebo tables regenerated under Rule A (correction line, not a new read)

Rule: PLACEBO_PLACEMENT_SPEC_v1 Rule A, cap 10·n_draws (Amendment 1, co-signed). Old = the published
pre-repair figure; each was reproduced from the defective module before the Rule A run
(`rescore_rule_a.py`). Same inputs, seeds, windows and draws; only the placement changed. The chance
account is unchanged. Fold decisions, "retains default" and "inconclusive" never used the placebo.

Pivot-table HY rows: the published JSON predates the HY release-rule lag fix (bb856951), so the old
figure is not reproducible on today's input; the Rule A figure below is on the corrected input and
replaces the published HY rows.

## WALKFORWARD_SCORECARD_OOS_v1 §3

| series | near | defined | acceptance | placed mass in band (alert) | top p90 old → new | top mean old → new | bottom p90 old → new | false risk-off/yr mean old → new |
|---|---|---|---:|---|---|---|---|---|
| walkforward_loud | high | yes | 1.000 | 0.570 (0.000) | 0.833 → 0.833 | 0.664 → 0.646 | 0.500 → 0.500 | 2.016 → 2.057 |
| walkforward_loud | low | yes | 1.000 | 0.598 (0.213) | 0.833 → 0.833 | 0.591 → 0.581 | 0.667 → 0.667 | 1.709 → 1.736 |

## SCORECARD_INSAMPLE §6 (INSAMPLE_READS_LAG1_v2)

| series | near | defined | acceptance | placed mass in band (alert) | top p90 old → new | top mean old → new | bottom p90 old → new | false risk-off/yr mean old → new |
|---|---|---|---:|---|---|---|---|---|
| radar_loud | high | yes | 1.000 | 0.590 (0.000) | 0.778 → 0.778 | 0.544 → 0.531 | 0.500 → 0.500 | 1.883 → 1.882 |
| radar_loud | low | yes | 1.000 | 0.651 (0.225) | 0.667 → 0.667 | 0.506 → 0.502 | 0.625 → 0.625 | 1.625 → 1.653 |
| radar_riskoff | high | yes | 1.000 | 0.624 (0.000) | 0.778 → 0.778 | 0.618 → 0.635 | 0.500 → 0.500 | 2.332 → 2.294 |
| radar_riskoff | low | yes | 1.000 | 0.682 (0.252) | 0.778 → 0.778 | 0.605 → 0.592 | 0.625 → 0.637 | 2.009 → 2.023 |
| base_hy_oas_chg21_top_decile | high | yes | 1.000 | 0.724 (0.053) | 0.889 → 0.889 | 0.719 → 0.722 | 0.500 → 0.625 | 2.935 → 2.943 |
| base_hy_oas_chg21_top_decile | low | yes | 1.000 | 0.763 (0.347) | 0.889 → 0.889 | 0.705 → 0.706 | 0.750 → 0.750 | 2.549 → 2.579 |
| base_mech_near_high_1pct | high | yes | 0.123 | 0.640 (1.000) | 1.000 → 1.000 | 0.996 → 0.998 | 0.750 → 0.750 | 7.219 → 7.506 |
| base_mech_near_high_1pct | low | yes | 0.920 | 0.694 (0.804) | 1.000 → 1.000 | 0.990 → 0.992 | 0.875 → 0.875 | 6.432 → 6.554 |

## PIVOT_SCORECARD_INSAMPLE Placebo (PIVOT_PLACEBO_INSAMPLE_v2)

| series | near | defined | acceptance | placed mass in band (alert) | top p90 old → new | top mean old → new | bottom p90 old → new | false risk-off/yr mean old → new |
|---|---|---|---:|---|---|---|---|---|
| radar_loud | None | yes | 1.000 | 1.000 (1.000) | 0.556 → 0.556 | 0.387 → 0.394 | 0.625 → 0.625 | 1.170 → 1.161 |
| radar_loud | high | yes | 1.000 | 0.584 (0.000) | 0.778 → 0.778 | 0.606 → 0.611 | 0.500 → 0.500 | 2.221 → 2.208 |
| radar_loud | low | yes | 1.000 | 0.654 (0.226) | 0.778 → 0.778 | 0.593 → 0.582 | 0.625 → 0.625 | 1.911 → 1.953 |
| hy_oas_top_decile (HY: replaces published row) | None | yes | 1.000 | 1.000 (1.000) | 0.778 → 0.667 | 0.531 → 0.503 | 0.750 → 0.750 | 1.638 → 1.539 |
| hy_oas_top_decile (HY: replaces published row) | high | yes | 1.000 | 0.724 (0.053) | 0.889 → 0.889 | 0.739 → 0.722 | 0.500 → 0.625 | 3.237 → 2.943 |
| hy_oas_top_decile (HY: replaces published row) | low | yes | 1.000 | 0.763 (0.347) | 0.889 → 0.889 | 0.735 → 0.706 | 0.750 → 0.750 | 2.778 → 2.579 |
| vix_ge_20 | None | yes | 0.263 | 1.000 (1.000) | 0.889 → 0.889 | 0.749 → 0.725 | 0.875 → 0.750 | 2.973 → 2.970 |
| vix_ge_20 | high | yes | 0.431 | 0.412 (0.137) | 1.000 → 1.000 | 0.888 → 0.876 | 0.637 → 0.625 | 5.674 → 5.734 |
| vix_ge_20 | low | yes | 0.691 | 0.457 (0.353) | 1.000 → 1.000 | 0.880 → 0.872 | 0.875 → 0.750 | 5.008 → 5.044 |
| spy_below_200 | None | yes | 1.000 | 1.000 (1.000) | 0.456 → 0.556 | 0.294 → 0.306 | 0.500 → 0.500 | 0.847 → 0.843 |
| spy_below_200 | high | yes | 1.000 | 0.572 (0.000) | 0.667 → 0.667 | 0.497 → 0.490 | 0.375 → 0.500 | 1.597 → 1.590 |
| spy_below_200 | low | yes | 1.000 | 0.627 (0.183) | 0.667 → 0.667 | 0.471 → 0.472 | 0.500 → 0.500 | 1.375 → 1.375 |

