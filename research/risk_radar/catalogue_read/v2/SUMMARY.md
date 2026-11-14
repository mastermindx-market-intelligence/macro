# Catalogue read v2 — the five Risk Radar -v2 sets (r1g conventions)

Bounded research worker. Paper-only: nothing sizes, ranks or executes. No set-level verdict is issued (see §4).

## 1. Adapter pin and consistency

- adapter sha256 at start: `504257977843e0894a97ed53415475eab76d8fc91fa9fc9cb0bbdcb9d24929c1`
- adapter sha256 at end: `504257977843e0894a97ed53415475eab76d8fc91fa9fc9cb0bbdcb9d24929c1`
- matches the pin `504257977843e0894a97ed53415475eab76d8fc91fa9fc9cb0bbdcb9d24929c1` at both ends: **True**
- consistency vs `data/risk_radar/walkforward_alert_series.csv` on 2022-01-03..2023-12-29: **0 of 501 sessions differ** (missing in ours 0; shipped loud share 0.3852, ours 0.3852)

Alerts are built causally on the full history from 2019-06-03 by the Macro engine (`engine.risk_radar_eval.inputs.incumbent_signals()`, which carries the prereg-addendum-3 point-in-time FRED replay), then shifted one session on the full series before windowing, exactly as r1g. Scoring uses the desk's vendored kit (`catalogue/adapter.py` + `pivot/radar_eval`).

## 2. Primary tables (r1g results.csv columns)

### R-off (top)

> **Placebo not matched on alert exposure** (placement defect, see PR comment 6835380019). Placed mass on this table's window not yet measured; the desk's mass table supplies it in the follow-up. The per-asset pass columns in this table (`assets_pass`, `assets_no_calls`, `clusters_pass_all_assets`, `clusters_pass_any_asset`) are not verified until the repair.

| family | set | direction | role | primary_post | n_draws | seed | turns_scored | turns_flagged | turn_share | turn_lo90 | turn_hi90 | clusters_scored | clusters_flagged | cluster_share | cluster_lo90 | cluster_hi90 | median_delay_sessions | false_col | false_per_asset_year | alert_on_share | sessions_in_episode | spans | open_spans | false_calls | false_in_rebound | assets | assets_pass | assets_no_calls | clusters_pass_all_assets | clusters_pass_any_asset | catch_target_75 | catch_gap_pp | false_target_2 | censored |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| R-off | confluence_k4 | top | set | 5 | 2000 | 20261112 | 191 | 83 | 0.4346 | 0.374 | 0.497 | 45 | 23 | 0.5111 | 0.38 | 0.641 | -15 | false_risk_off_per_asset_year | 2.007 | 0.138 | 0.409 | 988 | 18 | 172 | 172 | 21 | 12 | 0 | 4 | 24 | not met | -31.5 | not met | 0 |
| R-off | incumbent | top | set | 5 | 2000 | 20261112 | 191 | 61 | 0.3194 | 0.264 | 0.379 | 45 | 15 | 0.3333 | 0.218 | 0.466 | -9 | false_risk_off_per_asset_year | 1.004 | 0.224 | 0.409 | 988 | 18 | 86 | 86 | 21 | 11 | 0 | 1 | 22 | not met | -43.1 | met | 0 |
| R-off | confluence_k4 | top | control (unshifted; cannot pass) | 5 | 2000 | 20261112 | 191 | 78 | 0.4084 | 0.349 | 0.47 | 45 | 22 | 0.4889 | 0.359 | 0.62 | -16 | false_risk_off_per_asset_year | 1.972 | 0.138 | 0.409 | 988 | 18 | 169 | 169 | 21 | 13 | 0 | 4 | 25 | not met | -34.2 | met | 0 |
| R-off | incumbent | top | control (unshifted; cannot pass) | 5 | 2000 | 20261112 | 191 | 56 | 0.2932 | 0.239 | 0.352 | 45 | 16 | 0.3556 | 0.237 | 0.489 | -9 | false_risk_off_per_asset_year | 1.073 | 0.224 | 0.409 | 988 | 18 | 92 | 92 | 21 | 9 | 0 | 1 | 22 | not met | -45.7 | met | 0 |
| R-off | mech_dd_ge_5pct | top | reference (R1g) | 5 | 2000 | 20261112 | 191 | 36 | 0.1885 | 0.143 | 0.241 | 45 | 16 | 0.3556 | 0.237 | 0.489 | -1 | false_risk_off_per_asset_year | 1.19 | 0.779 | 0.409 | 988 | 18 | 102 | 102 | 21 | 6 | 11 | 1 | 17 | not met | -56.1 | met | 0 |
| R-off | mech_near_high_1pct | top | reference (R1g) | 5 | 2000 | 20261112 | 191 | 33 | 0.1728 | 0.129 | 0.224 | 45 | 13 | 0.2889 | 0.18 | 0.42 | -12 | false_risk_off_per_asset_year | 2.94 | 0.09 | 0.409 | 988 | 18 | 252 | 252 | 21 | 5 | 9 | 0 | 21 | not met | -57.7 | not met | 0 |
| R-off | trend_200 | top | reference (R1g) | 5 | 2000 | 20261112 | 191 | 41 | 0.2147 | 0.167 | 0.269 | 45 | 20 | 0.4444 | 0.317 | 0.577 | -1 | false_risk_off_per_asset_year | 1.248 | 0.399 | 0.409 | 988 | 18 | 107 | 107 | 21 | 7 | 5 | 6 | 24 | not met | -53.5 | met | 0 |

### R-on (bottom)

> **Placebo not matched on alert exposure** (placement defect, see PR comment 6835380019). Placed mass on this table's window not yet measured; the desk's mass table supplies it in the follow-up. The per-asset pass columns in this table (`assets_pass`, `assets_no_calls`, `clusters_pass_all_assets`, `clusters_pass_any_asset`) are not verified until the repair.

| family | set | direction | role | primary_post | n_draws | seed | turns_scored | turns_flagged | turn_share | turn_lo90 | turn_hi90 | clusters_scored | clusters_flagged | cluster_share | cluster_lo90 | cluster_hi90 | median_delay_sessions | false_col | false_per_asset_year | alert_on_share | sessions_in_episode | spans | open_spans | false_calls | false_in_rebound | assets | assets_pass | assets_no_calls | clusters_pass_all_assets | clusters_pass_any_asset | catch_target_75 | catch_gap_pp | false_target_2 | censored |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| R-on | confluence_k4 | bottom | set | 10 | 2000 | 20261112 | 197 | 69 | 0.3503 | 0.294 | 0.41 | 48 | 21 | 0.4375 | 0.315 | 0.566 | -8 | premature_all_clear_per_asset_year | 3.384 | 0.138 | 0.409 | 988 | 18 | 290 |  | 21 | 1 | 0 | 4 | 10 | not met | -40 | not met | 0 |
| R-on | exit_v1 | bottom | set | 10 | 2000 | 20261112 | 197 | 58 | 0.2944 | 0.241 | 0.352 | 48 | 13 | 0.2708 | 0.168 | 0.396 | 4 | premature_all_clear_per_asset_year | 0.315 | 0.283 | 0.409 | 988 | 18 | 27 |  | 21 | 12 | 0 | 17 | 39 | not met | -45.6 | met | 0 |
| R-on | incumbent | bottom | set | 10 | 2000 | 20261112 | 197 | 67 | 0.3401 | 0.284 | 0.4 | 48 | 12 | 0.25 | 0.151 | 0.373 | 4 | premature_all_clear_per_asset_year | 1.575 | 0.224 | 0.409 | 988 | 18 | 135 |  | 21 | 3 | 0 | 14 | 23 | not met | -41 | met | 0 |
| R-on | confluence_k4 | bottom | control (unshifted; cannot pass) | 10 | 2000 | 20261112 | 197 | 81 | 0.4112 | 0.352 | 0.472 | 48 | 21 | 0.4375 | 0.315 | 0.566 | 0 | premature_all_clear_per_asset_year | 3.349 | 0.138 | 0.409 | 988 | 18 | 287 |  | 21 | 1 | 0 | 4 | 10 | not met | -33.9 | not met | 0 |
| R-on | exit_v1 | bottom | control (unshifted; cannot pass) | 10 | 2000 | 20261112 | 197 | 59 | 0.2995 | 0.246 | 0.358 | 48 | 13 | 0.2708 | 0.168 | 0.396 | 7 | premature_all_clear_per_asset_year | 0.3617 | 0.283 | 0.409 | 988 | 18 | 31 |  | 21 | 12 | 0 | 17 | 39 | not met | -45.1 | met | 0 |
| R-on | incumbent | bottom | control (unshifted; cannot pass) | 10 | 2000 | 20261112 | 197 | 68 | 0.3452 | 0.289 | 0.405 | 48 | 13 | 0.2708 | 0.168 | 0.396 | 3 | premature_all_clear_per_asset_year | 1.54 | 0.224 | 0.409 | 988 | 18 | 132 |  | 21 | 3 | 0 | 14 | 23 | not met | -40.5 | met | 0 |
| R-on | mech_dd_ge_5pct | bottom | reference (R1g) | 10 | 2000 | 20261112 | 197 | 44 | 0.2234 | 0.175 | 0.278 | 48 | 16 | 0.3333 | 0.222 | 0.461 | 3 | premature_all_clear_per_asset_year | 2.31 | 0.148 | 0.409 | 988 | 18 | 198 |  | 21 | 0 | 6 | 0 | 0 | not met | -52.7 | not met | 0 |
| R-on | mech_near_high_1pct | bottom | reference (R1g) | 10 | 2000 | 20261112 | 197 | 69 | 0.3503 | 0.294 | 0.41 | 48 | 24 | 0.5 | 0.374 | 0.626 | 2 | premature_all_clear_per_asset_year | 2.8 | 0.054 | 0.409 | 988 | 18 | 240 |  | 21 | 0 | 5 | 0 | 0 | not met | -40 | not met | 0 |
| R-on | trend_200 | bottom | reference (R1g) | 10 | 2000 | 20261112 | 197 | 36 | 0.1827 | 0.139 | 0.234 | 48 | 21 | 0.4375 | 0.315 | 0.566 | 4 | premature_all_clear_per_asset_year | 1.4 | 0.399 | 0.409 | 988 | 18 | 120 |  | 21 | 3 | 5 | 13 | 17 | not met | -56.7 | met | 0 |

## 3. Components — descriptive only

These are not sets and cannot pass. Shifted, 500 draws.

### k-curve (confluence k of 12)

| family | k | alert_on_share | cluster_catch | turn_catch | false_per_asset_year |
|---|---|---|---|---|---|
| R-off | 1 | 0.751 | 0.6222 | 0.6021 | 8.133 |
| R-off | 2 | 0.468 | 0.8667 | 0.8639 | 6.989 |
| R-off | 3 | 0.265 | 0.7556 | 0.7696 | 3.944 |
| R-off | 4 | 0.138 | 0.5111 | 0.4346 | 2.007 |
| R-off | 5 | 0.079 | 0.4 | 0.3089 | 1.389 |
| R-off | 6 | 0.039 | 0.2222 | 0.1885 | 0.7934 |
| R-off | 7 | 0.018 | 0.0444 | 0.0209 | 0.0933 |
| R-off | 8 | 0.009 | 0.0222 | 0.0052 | 0.0817 |
| R-off | 9 | 0.002 | 0.0222 | 0.0052 | 0.035 |
| R-off | 10 | 0 | 0 | 0 | 0 |
| R-off | 11 | 0 | 0 | 0 | 0 |
| R-off | 12 | 0 | 0 | 0 | 0 |
| R-on | 1 | 0.751 | 0.2083 | 0.1624 | 5.601 |
| R-on | 2 | 0.468 | 0.4583 | 0.4315 | 5.928 |
| R-on | 3 | 0.265 | 0.3125 | 0.264 | 4.842 |
| R-on | 4 | 0.138 | 0.4375 | 0.3503 | 3.384 |
| R-on | 5 | 0.079 | 0.3958 | 0.3706 | 2.334 |
| R-on | 6 | 0.039 | 0.3333 | 0.3756 | 1.353 |
| R-on | 7 | 0.018 | 0.0833 | 0.1117 | 0.1517 |
| R-on | 8 | 0.009 | 0.0625 | 0.0914 | 0.21 |
| R-on | 9 | 0.002 | 0.0625 | 0.0914 | 0.0233 |
| R-on | 10 | 0 | 0 | 0 | 0 |
| R-on | 11 | 0 | 0 | 0 | 0 |
| R-on | 12 | 0 | 0 | 0 | 0 |

### Single legs (each of the 12 alone)

| family | leg | alert_on_share | cluster_catch | turn_catch | false_per_asset_year |
|---|---|---|---|---|---|
| R-off | credit_oas_roc | 0.117 | 0.3111 | 0.267 | 1.517 |
| R-off | credit_hyg_tlt | 0.108 | 0.3333 | 0.2775 | 2.404 |
| R-off | rates_move | 0.25 | 0.4222 | 0.3351 | 1.715 |
| R-off | rates_realrate | 0.139 | 0.8222 | 0.8115 | 4.714 |
| R-off | bubble_ext | 0.188 | 0.2667 | 0.3089 | 2.462 |
| R-off | bubble_leadership | 0.148 | 0.3778 | 0.3979 | 3.197 |
| R-off | growth_defensives | 0.094 | 0.4222 | 0.3822 | 2.322 |
| R-off | growth_cyc_def | 0.124 | 0.3556 | 0.3246 | 1.89 |
| R-off | vol_term | 0.105 | 0.4889 | 0.4607 | 1.902 |
| R-off | global_breadth | 0.329 | 0.2222 | 0.1728 | 0.9451 |
| R-off | jpy_carry | 0.145 | 0.6667 | 0.7225 | 3.361 |
| R-off | corr_floor_break | 0.021 | 0.1111 | 0.0942 | 0.6418 |
| R-on | credit_oas_roc | 0.117 | 0.3333 | 0.2944 | 2.625 |
| R-on | credit_hyg_tlt | 0.108 | 0.3333 | 0.2284 | 1.995 |
| R-on | rates_move | 0.25 | 0.2083 | 0.1827 | 2.87 |
| R-on | rates_realrate | 0.139 | 0.875 | 0.8376 | 4.516 |
| R-on | bubble_ext | 0.188 | 0.1667 | 0.203 | 1.575 |
| R-on | bubble_leadership | 0.148 | 0.25 | 0.198 | 2.065 |
| R-on | growth_defensives | 0.094 | 0.5208 | 0.5787 | 3.127 |
| R-on | growth_cyc_def | 0.124 | 0.375 | 0.3503 | 1.68 |
| R-on | vol_term | 0.105 | 0.4792 | 0.4721 | 2.754 |
| R-on | global_breadth | 0.329 | 0.125 | 0.132 | 1.085 |
| R-on | jpy_carry | 0.145 | 0.5 | 0.4873 | 2.415 |
| R-on | corr_floor_break | 0.021 | 0.1042 | 0.1117 | 0.7701 |

## 4. Sets read and alert ON share

Five sets read (R-off incumbent, R-off confluence_k4, R-on incumbent, R-on confluence_k4, R-on exit_v1), each with an unshifted control that cannot pass.

> **Placebo not matched on alert exposure** (placement defect, see PR comment 6835380019). Placed mass on this table's window not yet measured; the desk's mass table supplies it in the follow-up. The per-asset pass columns in this table (`assets_pass`, `assets_no_calls`, `clusters_pass_all_assets`, `clusters_pass_any_asset`) are not verified until the repair.

| family | set | alert_on_share | cluster_catch | false_per_asset_year | assets_pass | clusters_pass_all_assets |
|---|---|---|---|---|---|---|
| R-off | incumbent | 0.224 | 0.3333 | 1.004 | 11 | 1 |
| R-off | confluence_k4 | 0.138 | 0.5111 | 2.007 | 12 | 4 |
| R-on | incumbent | 0.224 | 0.25 | 1.575 | 3 | 14 |
| R-on | confluence_k4 | 0.138 | 0.4375 | 3.384 | 1 | 4 |
| R-on | exit_v1 | 0.283 | 0.2708 | 0.315 | 12 | 17 |

No set-level verdict: the budget-matched reference (bm_ref) does not exist yet (Principal ruling 2026-11-12 10:25Z).

Per-asset pass and pass-all columns above are description only.

## 5. Deviations and notes

- The k=3 follow-up row (`rr-roff-confluence-k3-followup`) was **not** scored on any block, per the brief; no alert-vs-turn relation was computed for it.
- The desk kit's `pivots.py` is a strict prefix of the worktree copy (identical scoring bytes; the worktree appends an unused `beyond_reference`), so scoring is byte-equivalent. The desk kit lacks `availability.py`/`walkforward.py` and its `inputs.py` has no point-in-time replay, so alerts come from the Macro engine.
- Runtime: 286s wall for 58 jobs.
