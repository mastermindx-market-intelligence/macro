# GLT T09 — preregistered rolling-origin component forecast study (measurement-only)

Programme `WS:GLOBAL-LIQUIDITY-TRANSMISSION`, task T09 (domain O3), 2026-10-13 packet, run 2026-10-19 (run 1 `as_of` 2026-10-19T11:16:11Z, run 2 11:16:55Z).
Config `config/global_liquidity_forecast_v1.yml` · module `engine/global_liquidity_forecast.py` ·
runner `scripts/research_global_liquidity_forecast.py` · tests `tests/test_global_liquidity_forecast.py` ·
result card `research/GLT_T09_FORECAST_RESULT_2026-10-13.json` (sha256 `0367130e6244a2726bb8070b78fe826cd5dcd86105484b423c42b2dde0373666`).

## §0 What this is and is not

This is ONE finite, preregistered measurement of whether simple residual models add forecast
accuracy over the protocol §6 baseline ladder for three Federal Reserve balance-sheet components:
reserve balances (`WRESBAL`, the primary target), the Treasury General Account and overnight reverse
repo, each as a change in $bn over 4, 8 and 13 weeks. It is `authority: measurement_only`,
`validated: false`, `vintage_cohort: 1`.

It is not a signal, ranking, score, position size, trade or alert, and nothing here is wired to
production: no `compose_outlook` call, no builder/nightly/render edit, no `data/` or `site/` write,
and no registration in the nightly `data/trial_ledger.jsonl` (the run used a scratch ledger).
A cell with disposition `issued` only makes the CONTRACTS §4 `statistical_forecast` estimate TYPE
available for T22 to decide on; every other cell carries `estimate_type: unavailable` with its
disposition as the abstention reason. A withheld answer is a complete answer.

The T14 card's 5/20/60-session horizons are asset-response horizons and do not apply here; the
component horizons are T08's declared 4/8/13 weeks.

Vintage: every series is the latest-vintage canonical-store history (cohort 1). No ALFRED or
first-release capture exists, so a later-revised value can stand in for the first-published one at
an origin; this revision risk is stated, not modelled, and a cohort-1 series never becomes cohort 3
by writing a timestamp.

## §1 Family declaration and trial-ledger receipt

Targets `reserves_wresbal_bn`, `tga_bn`, `rrp_bn` × horizons 4/8/13 weeks × five candidates
(`residual_ar_p1`, `residual_ar_p2`, `ridge_residual_a0.1`, `ridge_residual_a1.0`,
`ridge_residual_a10.0`, all fitted on the `announced_only` residual) = **45 trials**, declared in
the config before any fit. Baselines (all mandatory, ladder order, ties to the earlier):
`persistence`, `announced_only(empty)`, `seasonal_calendar`, `training_only_ar` (AR(p ≤ 4) chosen by
training-only AIC at each origin).

`register_family` logs the declared budget FIRST and then one trial per cell, with calendar-only
information cutoffs (the last evaluation origin of each target × horizon), BEFORE `run_study`.
Receipt: a scratch ledger outside the repository (never `data/trial_ledger.jsonl`): run 1 printed `ledger: new_trials=45 literal_n=45 declared_budget=45`; the ledger holds 46 lines (budget + 45 trials), sha256 `06a25420b4dad2f4a8b502242462d0fd77d9e86ff836e4e5926df32b8c7f73dd`; the card carries `trial_ledger.literal_n == family.n_trials_total == len(cells) == 45`. A second run on the same ledger added zero trials
(run 2 printed `ledger: new_trials=0 literal_n=45 declared_budget=45`; its card is identical except `run.as_of`). No target, horizon or model was dropped after results.

| # | target | horizon (weeks) | candidate | disposition |
|---|---|---|---|---|
| 0 | `reserves_wresbal_bn` | 4 | `residual_ar_p1` | `withheld_no_gain` |
| 1 | `reserves_wresbal_bn` | 4 | `residual_ar_p2` | `withheld_no_gain` |
| 2 | `reserves_wresbal_bn` | 4 | `ridge_residual_a0.1` | `withheld_no_gain` |
| 3 | `reserves_wresbal_bn` | 4 | `ridge_residual_a1.0` | `withheld_no_gain` |
| 4 | `reserves_wresbal_bn` | 4 | `ridge_residual_a10.0` | `withheld_no_gain` |
| 5 | `reserves_wresbal_bn` | 8 | `residual_ar_p1` | `withheld_no_gain` |
| 6 | `reserves_wresbal_bn` | 8 | `residual_ar_p2` | `withheld_no_gain` |
| 7 | `reserves_wresbal_bn` | 8 | `ridge_residual_a0.1` | `withheld_no_gain` |
| 8 | `reserves_wresbal_bn` | 8 | `ridge_residual_a1.0` | `withheld_no_gain` |
| 9 | `reserves_wresbal_bn` | 8 | `ridge_residual_a10.0` | `withheld_no_gain` |
| 10 | `reserves_wresbal_bn` | 13 | `residual_ar_p1` | `withheld_no_gain` |
| 11 | `reserves_wresbal_bn` | 13 | `residual_ar_p2` | `withheld_no_gain` |
| 12 | `reserves_wresbal_bn` | 13 | `ridge_residual_a0.1` | `withheld_no_gain` |
| 13 | `reserves_wresbal_bn` | 13 | `ridge_residual_a1.0` | `withheld_no_gain` |
| 14 | `reserves_wresbal_bn` | 13 | `ridge_residual_a10.0` | `withheld_no_gain` |
| 15 | `tga_bn` | 4 | `residual_ar_p1` | `withheld_no_gain` |
| 16 | `tga_bn` | 4 | `residual_ar_p2` | `withheld_no_gain` |
| 17 | `tga_bn` | 4 | `ridge_residual_a0.1` | `withheld_no_gain` |
| 18 | `tga_bn` | 4 | `ridge_residual_a1.0` | `withheld_no_gain` |
| 19 | `tga_bn` | 4 | `ridge_residual_a10.0` | `withheld_no_gain` |
| 20 | `tga_bn` | 8 | `residual_ar_p1` | `withheld_no_gain` |
| 21 | `tga_bn` | 8 | `residual_ar_p2` | `withheld_no_gain` |
| 22 | `tga_bn` | 8 | `ridge_residual_a0.1` | `withheld_no_gain` |
| 23 | `tga_bn` | 8 | `ridge_residual_a1.0` | `withheld_no_gain` |
| 24 | `tga_bn` | 8 | `ridge_residual_a10.0` | `withheld_no_gain` |
| 25 | `tga_bn` | 13 | `residual_ar_p1` | `withheld_no_gain` |
| 26 | `tga_bn` | 13 | `residual_ar_p2` | `withheld_no_gain` |
| 27 | `tga_bn` | 13 | `ridge_residual_a0.1` | `withheld_no_gain` |
| 28 | `tga_bn` | 13 | `ridge_residual_a1.0` | `withheld_no_gain` |
| 29 | `tga_bn` | 13 | `ridge_residual_a10.0` | `withheld_no_gain` |
| 30 | `rrp_bn` | 4 | `residual_ar_p1` | `withheld_no_gain` |
| 31 | `rrp_bn` | 4 | `residual_ar_p2` | `withheld_no_gain` |
| 32 | `rrp_bn` | 4 | `ridge_residual_a0.1` | `withheld_no_gain` |
| 33 | `rrp_bn` | 4 | `ridge_residual_a1.0` | `withheld_no_gain` |
| 34 | `rrp_bn` | 4 | `ridge_residual_a10.0` | `withheld_no_gain` |
| 35 | `rrp_bn` | 8 | `residual_ar_p1` | `withheld_no_gain` |
| 36 | `rrp_bn` | 8 | `residual_ar_p2` | `withheld_no_gain` |
| 37 | `rrp_bn` | 8 | `ridge_residual_a0.1` | `withheld_no_gain` |
| 38 | `rrp_bn` | 8 | `ridge_residual_a1.0` | `withheld_no_gain` |
| 39 | `rrp_bn` | 8 | `ridge_residual_a10.0` | `withheld_no_gain` |
| 40 | `rrp_bn` | 13 | `residual_ar_p1` | `withheld_no_gain` |
| 41 | `rrp_bn` | 13 | `residual_ar_p2` | `withheld_no_gain` |
| 42 | `rrp_bn` | 13 | `ridge_residual_a0.1` | `withheld_no_gain` |
| 43 | `rrp_bn` | 13 | `ridge_residual_a1.0` | `withheld_no_gain` |
| 44 | `rrp_bn` | 13 | `ridge_residual_a10.0` | `withheld_no_gain` |

## §2 Windows (copied verbatim from the T14 card)

Card `research/liquidity_transmission/glt_preregistration_card.v1.json` in Mastermind at master
`2d7021dd8ea5da27eaf11fc8b7249d53aac9f041`, `card_hash`
`da060bf47e8eafc7e94d0cadbb4135c9207a069aad9eef3539ea9d62911d6aee`.

| window | value |
|---|---|
| train | 2008-01-04 .. 2017-12-29 |
| dev | 2018-01-02 .. 2021-12-31 |
| reserved (never touched, not even as a label) | 2022-01-03 .. 2026-06-30 |
| purge | 60 sessions → 12 weeks by the declared rule `ceil(purge_sessions/5)` |

Every evaluation origin is a Friday strictly before `reserved_start` and every outcome matures on or
before `dev_end` (`rolling_origins` raises `ReservedWindowTouched` otherwise). Card: latest last
origin 2021-12-03 (h = 4; every maturity is on or before `dev_end` 2021-12-31, strictly before `reserved_start` 2022-01-03). T09 spends no reveal look; `reveal.custodian` and `look_budget` govern
T20/T22.

## §3 Publication clocks and the information-set rule

| target | clock rule | meaning |
|---|---|---|
| `reserves_wresbal_bn` | `h41_thursday_1630` | H.4.1 Thursday 16:30 ET for the Wednesday week, rolled to the next federal business day |
| `tga_bn` | `dts_next_business_day_1600` | Daily Treasury Statement, following federal business day 16:00 ET (S29: economic date ≠ publication) |
| `rrp_bn` | `same_day_1315` | same day 13:15 ET |

An observation enters the information set at origin o only if `published_at_utc ≤ cutoff_utc(o)`
(Friday 00:00 America/New_York). A source frame without a publication clock is refused
(`MissingPublicationClock`), never assumed. Every transform — differences, the seasonal
week-of-year means, AR order by AIC, ridge standardisation and coefficients — is fitted only on
training rows (Fridays from `train_start` whose outcome matured at least the 12-week purge before
the origin); `fit_baseline`/`fit_candidate` raise `LeakedValidationResidual` if any training
maturity is at or after the origin. Intervals are empirical conformal quantiles of
INNER rolling residuals (refits at earlier Fridays) whose maturity is at least 12 weeks before the
origin (`calibration_scope: training-only inner rolling residuals`); a residual dated at or after
the origin raises `LeakedValidationResidual`. A point forecast without a calibrated interval can
never be `issued`. The runner truncates every source to `dev_end` before the canonical loader and
then keeps only rows published by `dev_end`.

## §4 Baseline ladder results per target × horizon

**`reserves_wresbal_bn`** — MAE / RMSE of the horizon change ($bn) on the identical scored origins of each horizon

| model | h=4 MAE | h=4 RMSE | h=8 MAE | h=8 RMSE | h=13 MAE | h=13 RMSE |
|---|---|---|---|---|---|---|
| `persistence` | 110.345 | 191.012 | 189.188 | 323.678 | 271.571 | 430.759 |
| `announced_only(empty)` | 110.345 | 191.012 | 189.188 | 323.678 | 271.571 | 430.759 |
| `seasonal_calendar` | 109.183 | 186.678 | 188.390 | 316.046 | 270.654 | 415.284 |
| `training_only_ar` | 112.978 | 190.321 | 191.170 | 320.045 | 272.722 | 419.572 |
| `residual_ar_p1` | 112.309 | 190.700 | 191.127 | 320.042 | 272.877 | 419.355 |
| `residual_ar_p2` | 112.153 | 190.548 | 191.377 | 320.613 | 272.753 | 419.311 |
| `ridge_residual_a0.1` | 108.029 | 185.829 | 188.939 | 318.451 | 269.646 | 416.804 |
| `ridge_residual_a1.0` | 108.030 | 185.831 | 188.933 | 318.451 | 269.660 | 416.818 |
| `ridge_residual_a10.0` | 108.036 | 185.854 | 188.868 | 318.454 | 269.792 | 416.950 |

Best baseline (min MAE, ties to ladder order): h=4: `seasonal_calendar`; h=8: `seasonal_calendar`; h=13: `seasonal_calendar`.

**`tga_bn`** — MAE / RMSE of the horizon change ($bn) on the identical scored origins of each horizon

| model | h=4 MAE | h=4 RMSE | h=8 MAE | h=8 RMSE | h=13 MAE | h=13 RMSE |
|---|---|---|---|---|---|---|
| `persistence` | 100.038 | 146.374 | 161.453 | 248.949 | 223.164 | 355.395 |
| `announced_only(empty)` | 100.038 | 146.374 | 161.453 | 248.949 | 223.164 | 355.395 |
| `seasonal_calendar` | 89.127 | 138.581 | 157.382 | 245.588 | 231.975 | 362.750 |
| `training_only_ar` | 104.532 | 156.460 | 170.762 | 269.533 | 230.084 | 364.576 |
| `residual_ar_p1` | 101.839 | 149.875 | 163.477 | 256.718 | 228.427 | 361.448 |
| `residual_ar_p2` | 101.126 | 150.046 | 163.484 | 257.078 | 228.892 | 361.947 |
| `ridge_residual_a0.1` | 91.562 | 144.813 | 157.891 | 251.968 | 227.369 | 364.146 |
| `ridge_residual_a1.0` | 91.570 | 144.803 | 157.902 | 251.986 | 227.387 | 364.161 |
| `ridge_residual_a10.0` | 91.643 | 144.706 | 158.005 | 252.151 | 227.546 | 364.289 |

Best baseline (min MAE, ties to ladder order): h=4: `seasonal_calendar`; h=8: `seasonal_calendar`; h=13: `persistence`.

**`rrp_bn`** — MAE / RMSE of the horizon change ($bn) on the identical scored origins of each horizon

| model | h=4 MAE | h=4 RMSE | h=8 MAE | h=8 RMSE | h=13 MAE | h=13 RMSE |
|---|---|---|---|---|---|---|
| `persistence` | 40.531 | 96.939 | 70.538 | 162.334 | 106.355 | 246.700 |
| `announced_only(empty)` | 40.531 | 96.939 | 70.538 | 162.334 | 106.355 | 246.700 |
| `seasonal_calendar` | 56.442 | 99.648 | 84.004 | 163.400 | 117.937 | 248.125 |
| `training_only_ar` | 50.582 | 118.525 | 83.798 | 195.386 | 112.130 | 258.251 |
| `residual_ar_p1` | 42.571 | 100.441 | 73.470 | 170.285 | 108.221 | 249.275 |
| `residual_ar_p2` | 45.148 | 105.744 | 76.347 | 178.188 | 109.767 | 252.310 |
| `ridge_residual_a0.1` | 59.440 | 118.475 | 90.898 | 193.791 | 117.070 | 258.550 |
| `ridge_residual_a1.0` | 59.338 | 118.328 | 90.772 | 193.602 | 117.003 | 258.483 |
| `ridge_residual_a10.0` | 58.391 | 116.960 | 89.588 | 191.832 | 116.414 | 257.858 |

Best baseline (min MAE, ties to ladder order): h=4: `persistence`; h=8: `persistence`; h=13: `persistence`.

## §5 Candidate gains with confidence intervals

Relative gain = 1 − MAE(candidate) / MAE(best baseline), on identical scored origins; 90 % paired
moving-block bootstrap (13-week blocks, 2 000 resamples, seed 20261013), best baseline fixed.

| # | target | h | candidate | best baseline | relative MAE gain | 90% CI low | 90% CI high | n scored |
|---|---|---|---|---|---|---|---|---|
| 0 | `reserves_wresbal_bn` | 4 | `residual_ar_p1` | `seasonal_calendar` | -0.0286 | -0.0703 | 0.0066 | 205 |
| 1 | `reserves_wresbal_bn` | 4 | `residual_ar_p2` | `seasonal_calendar` | -0.0272 | -0.0647 | 0.0095 | 205 |
| 2 | `reserves_wresbal_bn` | 4 | `ridge_residual_a0.1` | `seasonal_calendar` | 0.0106 | -0.0272 | 0.0433 | 205 |
| 3 | `reserves_wresbal_bn` | 4 | `ridge_residual_a1.0` | `seasonal_calendar` | 0.0106 | -0.0297 | 0.0419 | 205 |
| 4 | `reserves_wresbal_bn` | 4 | `ridge_residual_a10.0` | `seasonal_calendar` | 0.0105 | -0.0283 | 0.0427 | 205 |
| 5 | `reserves_wresbal_bn` | 8 | `residual_ar_p1` | `seasonal_calendar` | -0.0145 | -0.0518 | 0.0241 | 201 |
| 6 | `reserves_wresbal_bn` | 8 | `residual_ar_p2` | `seasonal_calendar` | -0.0159 | -0.0519 | 0.0206 | 201 |
| 7 | `reserves_wresbal_bn` | 8 | `ridge_residual_a0.1` | `seasonal_calendar` | -0.0029 | -0.0206 | 0.0236 | 201 |
| 8 | `reserves_wresbal_bn` | 8 | `ridge_residual_a1.0` | `seasonal_calendar` | -0.0029 | -0.0219 | 0.0221 | 201 |
| 9 | `reserves_wresbal_bn` | 8 | `ridge_residual_a10.0` | `seasonal_calendar` | -0.0025 | -0.0215 | 0.0232 | 201 |
| 10 | `reserves_wresbal_bn` | 13 | `residual_ar_p1` | `seasonal_calendar` | -0.0082 | -0.0597 | 0.0315 | 196 |
| 11 | `reserves_wresbal_bn` | 13 | `residual_ar_p2` | `seasonal_calendar` | -0.0078 | -0.0605 | 0.0307 | 196 |
| 12 | `reserves_wresbal_bn` | 13 | `ridge_residual_a0.1` | `seasonal_calendar` | 0.0037 | -0.0214 | 0.0196 | 196 |
| 13 | `reserves_wresbal_bn` | 13 | `ridge_residual_a1.0` | `seasonal_calendar` | 0.0037 | -0.0218 | 0.0207 | 196 |
| 14 | `reserves_wresbal_bn` | 13 | `ridge_residual_a10.0` | `seasonal_calendar` | 0.0032 | -0.0237 | 0.0193 | 196 |
| 15 | `tga_bn` | 4 | `residual_ar_p1` | `seasonal_calendar` | -0.1426 | -0.2805 | -0.0727 | 192 |
| 16 | `tga_bn` | 4 | `residual_ar_p2` | `seasonal_calendar` | -0.1346 | -0.2629 | -0.0543 | 192 |
| 17 | `tga_bn` | 4 | `ridge_residual_a0.1` | `seasonal_calendar` | -0.0273 | -0.1270 | 0.0580 | 192 |
| 18 | `tga_bn` | 4 | `ridge_residual_a1.0` | `seasonal_calendar` | -0.0274 | -0.1285 | 0.0572 | 192 |
| 19 | `tga_bn` | 4 | `ridge_residual_a10.0` | `seasonal_calendar` | -0.0282 | -0.1312 | 0.0533 | 192 |
| 20 | `tga_bn` | 8 | `residual_ar_p1` | `seasonal_calendar` | -0.0387 | -0.1236 | 0.0154 | 188 |
| 21 | `tga_bn` | 8 | `residual_ar_p2` | `seasonal_calendar` | -0.0388 | -0.1359 | 0.0304 | 188 |
| 22 | `tga_bn` | 8 | `ridge_residual_a0.1` | `seasonal_calendar` | -0.0032 | -0.0919 | 0.0752 | 188 |
| 23 | `tga_bn` | 8 | `ridge_residual_a1.0` | `seasonal_calendar` | -0.0033 | -0.0916 | 0.0725 | 188 |
| 24 | `tga_bn` | 8 | `ridge_residual_a10.0` | `seasonal_calendar` | -0.0040 | -0.0895 | 0.0737 | 188 |
| 25 | `tga_bn` | 13 | `residual_ar_p1` | `persistence` | -0.0236 | -0.0470 | -0.0047 | 183 |
| 26 | `tga_bn` | 13 | `residual_ar_p2` | `persistence` | -0.0257 | -0.0569 | -0.0030 | 183 |
| 27 | `tga_bn` | 13 | `ridge_residual_a0.1` | `persistence` | -0.0188 | -0.0750 | 0.0337 | 183 |
| 28 | `tga_bn` | 13 | `ridge_residual_a1.0` | `persistence` | -0.0189 | -0.0740 | 0.0305 | 183 |
| 29 | `tga_bn` | 13 | `ridge_residual_a10.0` | `persistence` | -0.0196 | -0.0739 | 0.0262 | 183 |
| 30 | `rrp_bn` | 4 | `residual_ar_p1` | `persistence` | -0.0503 | -0.0873 | 0.0133 | 205 |
| 31 | `rrp_bn` | 4 | `residual_ar_p2` | `persistence` | -0.1139 | -0.1950 | 0.0043 | 205 |
| 32 | `rrp_bn` | 4 | `ridge_residual_a0.1` | `persistence` | -0.4665 | -1.2111 | -0.3362 | 205 |
| 33 | `rrp_bn` | 4 | `ridge_residual_a1.0` | `persistence` | -0.4640 | -1.1474 | -0.3399 | 205 |
| 34 | `rrp_bn` | 4 | `ridge_residual_a10.0` | `persistence` | -0.4407 | -1.1601 | -0.3227 | 205 |
| 35 | `rrp_bn` | 8 | `residual_ar_p1` | `persistence` | -0.0416 | -0.0740 | 0.0158 | 201 |
| 36 | `rrp_bn` | 8 | `residual_ar_p2` | `persistence` | -0.0824 | -0.1397 | 0.0011 | 201 |
| 37 | `rrp_bn` | 8 | `ridge_residual_a0.1` | `persistence` | -0.2886 | -0.6918 | -0.2174 | 201 |
| 38 | `rrp_bn` | 8 | `ridge_residual_a1.0` | `persistence` | -0.2868 | -0.7076 | -0.2213 | 201 |
| 39 | `rrp_bn` | 8 | `ridge_residual_a10.0` | `persistence` | -0.2701 | -0.7198 | -0.2032 | 201 |
| 40 | `rrp_bn` | 13 | `residual_ar_p1` | `persistence` | -0.0175 | -0.0276 | -0.0046 | 196 |
| 41 | `rrp_bn` | 13 | `residual_ar_p2` | `persistence` | -0.0321 | -0.0443 | -0.0068 | 196 |
| 42 | `rrp_bn` | 13 | `ridge_residual_a0.1` | `persistence` | -0.1007 | -0.4302 | -0.0591 | 196 |
| 43 | `rrp_bn` | 13 | `ridge_residual_a1.0` | `persistence` | -0.1001 | -0.4110 | -0.0595 | 196 |
| 44 | `rrp_bn` | 13 | `ridge_residual_a10.0` | `persistence` | -0.0946 | -0.4765 | -0.0565 | 196 |

## §6 Interval coverage and width (80 / 90)

Observed coverage is in percentage points against the nominal level; width is the mean full width
(2q) in $bn. `missing` counts scored origins without a calibrated interval (fewer than 52 inner
residuals).

| # | target | h | candidate | cov 80 (pp) | width 80 ($bn) | missing 80 | cov 90 (pp) | width 90 ($bn) | missing 90 |
|---|---|---|---|---|---|---|---|---|---|
| 0 | `reserves_wresbal_bn` | 4 | `residual_ar_p1` | 71.71 | 236.48 | 0 | 83.41 | 317.15 | 0 |
| 1 | `reserves_wresbal_bn` | 4 | `residual_ar_p2` | 70.24 | 232.53 | 0 | 84.88 | 320.95 | 0 |
| 2 | `reserves_wresbal_bn` | 4 | `ridge_residual_a0.1` | 74.15 | 237.26 | 0 | 85.37 | 317.48 | 0 |
| 3 | `reserves_wresbal_bn` | 4 | `ridge_residual_a1.0` | 74.15 | 237.16 | 0 | 85.37 | 317.44 | 0 |
| 4 | `reserves_wresbal_bn` | 4 | `ridge_residual_a10.0` | 74.15 | 235.87 | 0 | 85.37 | 317.09 | 0 |
| 5 | `reserves_wresbal_bn` | 8 | `residual_ar_p1` | 67.66 | 317.54 | 0 | 80.10 | 450.86 | 0 |
| 6 | `reserves_wresbal_bn` | 8 | `residual_ar_p2` | 68.16 | 324.11 | 0 | 80.60 | 459.93 | 0 |
| 7 | `reserves_wresbal_bn` | 8 | `ridge_residual_a0.1` | 72.64 | 364.33 | 0 | 83.08 | 492.79 | 0 |
| 8 | `reserves_wresbal_bn` | 8 | `ridge_residual_a1.0` | 72.64 | 363.95 | 0 | 83.08 | 492.63 | 0 |
| 9 | `reserves_wresbal_bn` | 8 | `ridge_residual_a10.0` | 72.14 | 360.46 | 0 | 83.08 | 490.43 | 0 |
| 10 | `reserves_wresbal_bn` | 13 | `residual_ar_p1` | 62.24 | 434.45 | 0 | 79.59 | 559.92 | 0 |
| 11 | `reserves_wresbal_bn` | 13 | `residual_ar_p2` | 64.29 | 438.01 | 0 | 80.10 | 560.10 | 0 |
| 12 | `reserves_wresbal_bn` | 13 | `ridge_residual_a0.1` | 72.45 | 514.90 | 0 | 81.63 | 673.82 | 0 |
| 13 | `reserves_wresbal_bn` | 13 | `ridge_residual_a1.0` | 72.45 | 514.56 | 0 | 81.63 | 671.92 | 0 |
| 14 | `reserves_wresbal_bn` | 13 | `ridge_residual_a10.0` | 72.45 | 510.94 | 0 | 81.12 | 657.13 | 0 |
| 15 | `tga_bn` | 4 | `residual_ar_p1` | 62.50 | 162.45 | 0 | 70.31 | 227.96 | 0 |
| 16 | `tga_bn` | 4 | `residual_ar_p2` | 58.85 | 159.69 | 0 | 69.79 | 224.78 | 0 |
| 17 | `tga_bn` | 4 | `ridge_residual_a0.1` | 61.98 | 134.12 | 0 | 70.31 | 195.44 | 0 |
| 18 | `tga_bn` | 4 | `ridge_residual_a1.0` | 61.98 | 134.17 | 0 | 70.31 | 195.41 | 0 |
| 19 | `tga_bn` | 4 | `ridge_residual_a10.0` | 61.46 | 134.44 | 0 | 70.31 | 196.09 | 0 |
| 20 | `tga_bn` | 8 | `residual_ar_p1` | 51.60 | 196.09 | 0 | 61.17 | 258.27 | 0 |
| 21 | `tga_bn` | 8 | `residual_ar_p2` | 52.13 | 190.88 | 0 | 62.77 | 254.62 | 0 |
| 22 | `tga_bn` | 8 | `ridge_residual_a0.1` | 47.34 | 165.35 | 0 | 63.30 | 234.30 | 0 |
| 23 | `tga_bn` | 8 | `ridge_residual_a1.0` | 47.34 | 165.39 | 0 | 63.30 | 234.21 | 0 |
| 24 | `tga_bn` | 8 | `ridge_residual_a10.0` | 47.34 | 165.96 | 0 | 63.30 | 233.11 | 0 |
| 25 | `tga_bn` | 13 | `residual_ar_p1` | 45.90 | 182.19 | 0 | 59.02 | 264.76 | 0 |
| 26 | `tga_bn` | 13 | `residual_ar_p2` | 45.36 | 180.91 | 0 | 59.56 | 269.97 | 0 |
| 27 | `tga_bn` | 13 | `ridge_residual_a0.1` | 40.44 | 162.05 | 0 | 56.83 | 266.26 | 0 |
| 28 | `tga_bn` | 13 | `ridge_residual_a1.0` | 40.44 | 161.97 | 0 | 56.83 | 266.29 | 0 |
| 29 | `tga_bn` | 13 | `ridge_residual_a10.0` | 39.89 | 162.55 | 0 | 57.38 | 266.08 | 0 |
| 30 | `rrp_bn` | 4 | `residual_ar_p1` | 82.44 | 179.24 | 0 | 86.83 | 267.09 | 0 |
| 31 | `rrp_bn` | 4 | `residual_ar_p2` | 83.41 | 178.94 | 0 | 86.34 | 255.96 | 0 |
| 32 | `rrp_bn` | 4 | `ridge_residual_a0.1` | 83.90 | 159.67 | 0 | 84.88 | 235.82 | 0 |
| 33 | `rrp_bn` | 4 | `ridge_residual_a1.0` | 83.90 | 159.75 | 0 | 84.88 | 235.08 | 0 |
| 34 | `rrp_bn` | 4 | `ridge_residual_a10.0` | 83.41 | 159.99 | 0 | 85.37 | 232.77 | 0 |
| 35 | `rrp_bn` | 8 | `residual_ar_p1` | 80.60 | 165.68 | 0 | 81.59 | 248.23 | 0 |
| 36 | `rrp_bn` | 8 | `residual_ar_p2` | 80.10 | 158.52 | 0 | 82.09 | 218.97 | 0 |
| 37 | `rrp_bn` | 8 | `ridge_residual_a0.1` | 79.60 | 122.65 | 0 | 82.09 | 175.33 | 0 |
| 38 | `rrp_bn` | 8 | `ridge_residual_a1.0` | 79.60 | 122.93 | 0 | 82.09 | 175.32 | 0 |
| 39 | `rrp_bn` | 8 | `ridge_residual_a10.0` | 80.60 | 126.24 | 0 | 82.09 | 179.34 | 0 |
| 40 | `rrp_bn` | 13 | `residual_ar_p1` | 78.57 | 143.72 | 0 | 79.08 | 197.35 | 0 |
| 41 | `rrp_bn` | 13 | `residual_ar_p2` | 78.57 | 150.84 | 0 | 79.08 | 202.17 | 0 |
| 42 | `rrp_bn` | 13 | `ridge_residual_a0.1` | 79.08 | 146.16 | 0 | 79.08 | 198.11 | 0 |
| 43 | `rrp_bn` | 13 | `ridge_residual_a1.0` | 79.08 | 146.11 | 0 | 79.08 | 197.73 | 0 |
| 44 | `rrp_bn` | 13 | `ridge_residual_a10.0` | 79.08 | 145.82 | 0 | 79.08 | 195.64 | 0 |

## §7 Outage denominators

The four origin classes (outage, outcome unavailable, model unavailable, scored) partition
`n_origins_total`; an outage reduces the scored set transparently and never shrinks the denominator.

| target | h | first origin | last origin | n_origins_total | n_outage | outage share | n_outcome_unavailable | n_model_unavailable | n_origins_scored | source status |
|---|---|---|---|---|---|---|---|---|---|---|
| `reserves_wresbal_bn` | 4 | 2018-01-05 | 2021-12-03 | 205 | 0 | — | 0 | 0 | 205 | `loaded` |
| `reserves_wresbal_bn` | 8 | 2018-01-05 | 2021-11-05 | 201 | 0 | — | 0 | 0 | 201 | `loaded` |
| `reserves_wresbal_bn` | 13 | 2018-01-05 | 2021-10-01 | 196 | 0 | — | 0 | 0 | 196 | `loaded` |
| `tga_bn` | 4 | 2018-01-05 | 2021-12-03 | 205 | 9 | 0.0439 | 4 | 0 | 192 | `loaded` |
| `tga_bn` | 8 | 2018-01-05 | 2021-11-05 | 201 | 5 | 0.0249 | 8 | 0 | 188 | `loaded` |
| `tga_bn` | 13 | 2018-01-05 | 2021-10-01 | 196 | 0 | — | 13 | 0 | 183 | `loaded` |
| `rrp_bn` | 4 | 2018-01-05 | 2021-12-03 | 205 | 0 | — | 0 | 0 | 205 | `loaded` |
| `rrp_bn` | 8 | 2018-01-05 | 2021-11-05 | 201 | 0 | — | 0 | 0 | 201 | `loaded` |
| `rrp_bn` | 13 | 2018-01-05 | 2021-10-01 | 196 | 0 | — | 0 | 0 | 196 | `loaded` |

## §8 Dispositions (all 45 cells) and what the answer licenses

Precedence (first true wins): `unavailable` → `withheld_insufficient_sample` (n < 52) →
`withheld_no_gain` (gain < 0.05, or CI missing, or CI low ≤ 0) → `withheld_miscalibrated`
(coverage outside ±5 points of nominal, or an interval missing) → `issued`.

| disposition | cells |
|---|---|
| `issued` | 0 |
| `withheld_no_gain` | 45 |
| `withheld_insufficient_sample` | 0 |
| `withheld_miscalibrated` | 0 |
| `unavailable` | 0 |

| # | target | h | candidate | disposition | estimate type | reason |
|---|---|---|---|---|---|---|
| 0 | `reserves_wresbal_bn` | 4 | `residual_ar_p1` | `withheld_no_gain` | `unavailable` | best baseline seasonal_calendar: relative_gain=-0.028634 (min_relative_gain=0.05), gain_ci=(-0.07035, 0.00656) at level 0.9 |
| 1 | `reserves_wresbal_bn` | 4 | `residual_ar_p2` | `withheld_no_gain` | `unavailable` | best baseline seasonal_calendar: relative_gain=-0.027205 (min_relative_gain=0.05), gain_ci=(-0.064701, 0.00955) at level 0.9 |
| 2 | `reserves_wresbal_bn` | 4 | `ridge_residual_a0.1` | `withheld_no_gain` | `unavailable` | best baseline seasonal_calendar: relative_gain=0.010567 (min_relative_gain=0.05), gain_ci=(-0.027195, 0.043262) at level 0.9 |
| 3 | `reserves_wresbal_bn` | 4 | `ridge_residual_a1.0` | `withheld_no_gain` | `unavailable` | best baseline seasonal_calendar: relative_gain=0.010561 (min_relative_gain=0.05), gain_ci=(-0.02975, 0.041933) at level 0.9 |
| 4 | `reserves_wresbal_bn` | 4 | `ridge_residual_a10.0` | `withheld_no_gain` | `unavailable` | best baseline seasonal_calendar: relative_gain=0.0105 (min_relative_gain=0.05), gain_ci=(-0.028302, 0.042744) at level 0.9 |
| 5 | `reserves_wresbal_bn` | 8 | `residual_ar_p1` | `withheld_no_gain` | `unavailable` | best baseline seasonal_calendar: relative_gain=-0.014529 (min_relative_gain=0.05), gain_ci=(-0.051834, 0.024071) at level 0.9 |
| 6 | `reserves_wresbal_bn` | 8 | `residual_ar_p2` | `withheld_no_gain` | `unavailable` | best baseline seasonal_calendar: relative_gain=-0.015855 (min_relative_gain=0.05), gain_ci=(-0.051869, 0.020627) at level 0.9 |
| 7 | `reserves_wresbal_bn` | 8 | `ridge_residual_a0.1` | `withheld_no_gain` | `unavailable` | best baseline seasonal_calendar: relative_gain=-0.002917 (min_relative_gain=0.05), gain_ci=(-0.020623, 0.02359) at level 0.9 |
| 8 | `reserves_wresbal_bn` | 8 | `ridge_residual_a1.0` | `withheld_no_gain` | `unavailable` | best baseline seasonal_calendar: relative_gain=-0.002882 (min_relative_gain=0.05), gain_ci=(-0.021859, 0.022097) at level 0.9 |
| 9 | `reserves_wresbal_bn` | 8 | `ridge_residual_a10.0` | `withheld_no_gain` | `unavailable` | best baseline seasonal_calendar: relative_gain=-0.002536 (min_relative_gain=0.05), gain_ci=(-0.021516, 0.023213) at level 0.9 |
| 10 | `reserves_wresbal_bn` | 13 | `residual_ar_p1` | `withheld_no_gain` | `unavailable` | best baseline seasonal_calendar: relative_gain=-0.008214 (min_relative_gain=0.05), gain_ci=(-0.05965, 0.031516) at level 0.9 |
| 11 | `reserves_wresbal_bn` | 13 | `residual_ar_p2` | `withheld_no_gain` | `unavailable` | best baseline seasonal_calendar: relative_gain=-0.007755 (min_relative_gain=0.05), gain_ci=(-0.060539, 0.030736) at level 0.9 |
| 12 | `reserves_wresbal_bn` | 13 | `ridge_residual_a0.1` | `withheld_no_gain` | `unavailable` | best baseline seasonal_calendar: relative_gain=0.003727 (min_relative_gain=0.05), gain_ci=(-0.021365, 0.019638) at level 0.9 |
| 13 | `reserves_wresbal_bn` | 13 | `ridge_residual_a1.0` | `withheld_no_gain` | `unavailable` | best baseline seasonal_calendar: relative_gain=0.003673 (min_relative_gain=0.05), gain_ci=(-0.0218, 0.020737) at level 0.9 |
| 14 | `reserves_wresbal_bn` | 13 | `ridge_residual_a10.0` | `withheld_no_gain` | `unavailable` | best baseline seasonal_calendar: relative_gain=0.003185 (min_relative_gain=0.05), gain_ci=(-0.023719, 0.019275) at level 0.9 |
| 15 | `tga_bn` | 4 | `residual_ar_p1` | `withheld_no_gain` | `unavailable` | best baseline seasonal_calendar: relative_gain=-0.142628 (min_relative_gain=0.05), gain_ci=(-0.280504, -0.072705) at level 0.9 |
| 16 | `tga_bn` | 4 | `residual_ar_p2` | `withheld_no_gain` | `unavailable` | best baseline seasonal_calendar: relative_gain=-0.134628 (min_relative_gain=0.05), gain_ci=(-0.262921, -0.054308) at level 0.9 |
| 17 | `tga_bn` | 4 | `ridge_residual_a0.1` | `withheld_no_gain` | `unavailable` | best baseline seasonal_calendar: relative_gain=-0.027327 (min_relative_gain=0.05), gain_ci=(-0.126981, 0.057976) at level 0.9 |
| 18 | `tga_bn` | 4 | `ridge_residual_a1.0` | `withheld_no_gain` | `unavailable` | best baseline seasonal_calendar: relative_gain=-0.027411 (min_relative_gain=0.05), gain_ci=(-0.128513, 0.057192) at level 0.9 |
| 19 | `tga_bn` | 4 | `ridge_residual_a10.0` | `withheld_no_gain` | `unavailable` | best baseline seasonal_calendar: relative_gain=-0.028229 (min_relative_gain=0.05), gain_ci=(-0.131201, 0.053258) at level 0.9 |
| 20 | `tga_bn` | 8 | `residual_ar_p1` | `withheld_no_gain` | `unavailable` | best baseline seasonal_calendar: relative_gain=-0.038726 (min_relative_gain=0.05), gain_ci=(-0.123619, 0.015395) at level 0.9 |
| 21 | `tga_bn` | 8 | `residual_ar_p2` | `withheld_no_gain` | `unavailable` | best baseline seasonal_calendar: relative_gain=-0.038772 (min_relative_gain=0.05), gain_ci=(-0.135912, 0.030391) at level 0.9 |
| 22 | `tga_bn` | 8 | `ridge_residual_a0.1` | `withheld_no_gain` | `unavailable` | best baseline seasonal_calendar: relative_gain=-0.003232 (min_relative_gain=0.05), gain_ci=(-0.091911, 0.075244) at level 0.9 |
| 23 | `tga_bn` | 8 | `ridge_residual_a1.0` | `withheld_no_gain` | `unavailable` | best baseline seasonal_calendar: relative_gain=-0.003303 (min_relative_gain=0.05), gain_ci=(-0.091564, 0.072523) at level 0.9 |
| 24 | `tga_bn` | 8 | `ridge_residual_a10.0` | `withheld_no_gain` | `unavailable` | best baseline seasonal_calendar: relative_gain=-0.003957 (min_relative_gain=0.05), gain_ci=(-0.089482, 0.073656) at level 0.9 |
| 25 | `tga_bn` | 13 | `residual_ar_p1` | `withheld_no_gain` | `unavailable` | best baseline persistence: relative_gain=-0.023585 (min_relative_gain=0.05), gain_ci=(-0.047003, -0.004659) at level 0.9 |
| 26 | `tga_bn` | 13 | `residual_ar_p2` | `withheld_no_gain` | `unavailable` | best baseline persistence: relative_gain=-0.025667 (min_relative_gain=0.05), gain_ci=(-0.056903, -0.002991) at level 0.9 |
| 27 | `tga_bn` | 13 | `ridge_residual_a0.1` | `withheld_no_gain` | `unavailable` | best baseline persistence: relative_gain=-0.018844 (min_relative_gain=0.05), gain_ci=(-0.075019, 0.033744) at level 0.9 |
| 28 | `tga_bn` | 13 | `ridge_residual_a1.0` | `withheld_no_gain` | `unavailable` | best baseline persistence: relative_gain=-0.018926 (min_relative_gain=0.05), gain_ci=(-0.073991, 0.03045) at level 0.9 |
| 29 | `tga_bn` | 13 | `ridge_residual_a10.0` | `withheld_no_gain` | `unavailable` | best baseline persistence: relative_gain=-0.019635 (min_relative_gain=0.05), gain_ci=(-0.073932, 0.026229) at level 0.9 |
| 30 | `rrp_bn` | 4 | `residual_ar_p1` | `withheld_no_gain` | `unavailable` | best baseline persistence: relative_gain=-0.050335 (min_relative_gain=0.05), gain_ci=(-0.087327, 0.013262) at level 0.9 |
| 31 | `rrp_bn` | 4 | `residual_ar_p2` | `withheld_no_gain` | `unavailable` | best baseline persistence: relative_gain=-0.113903 (min_relative_gain=0.05), gain_ci=(-0.195046, 0.004282) at level 0.9 |
| 32 | `rrp_bn` | 4 | `ridge_residual_a0.1` | `withheld_no_gain` | `unavailable` | best baseline persistence: relative_gain=-0.46652 (min_relative_gain=0.05), gain_ci=(-1.21109, -0.336198) at level 0.9 |
| 33 | `rrp_bn` | 4 | `ridge_residual_a1.0` | `withheld_no_gain` | `unavailable` | best baseline persistence: relative_gain=-0.464013 (min_relative_gain=0.05), gain_ci=(-1.14737, -0.339948) at level 0.9 |
| 34 | `rrp_bn` | 4 | `ridge_residual_a10.0` | `withheld_no_gain` | `unavailable` | best baseline persistence: relative_gain=-0.440655 (min_relative_gain=0.05), gain_ci=(-1.1601, -0.322727) at level 0.9 |
| 35 | `rrp_bn` | 8 | `residual_ar_p1` | `withheld_no_gain` | `unavailable` | best baseline persistence: relative_gain=-0.041554 (min_relative_gain=0.05), gain_ci=(-0.074025, 0.015799) at level 0.9 |
| 36 | `rrp_bn` | 8 | `residual_ar_p2` | `withheld_no_gain` | `unavailable` | best baseline persistence: relative_gain=-0.082351 (min_relative_gain=0.05), gain_ci=(-0.139671, 0.001066) at level 0.9 |
| 37 | `rrp_bn` | 8 | `ridge_residual_a0.1` | `withheld_no_gain` | `unavailable` | best baseline persistence: relative_gain=-0.288635 (min_relative_gain=0.05), gain_ci=(-0.691761, -0.217391) at level 0.9 |
| 38 | `rrp_bn` | 8 | `ridge_residual_a1.0` | `withheld_no_gain` | `unavailable` | best baseline persistence: relative_gain=-0.286842 (min_relative_gain=0.05), gain_ci=(-0.707645, -0.221256) at level 0.9 |
| 39 | `rrp_bn` | 8 | `ridge_residual_a10.0` | `withheld_no_gain` | `unavailable` | best baseline persistence: relative_gain=-0.270058 (min_relative_gain=0.05), gain_ci=(-0.719805, -0.203201) at level 0.9 |
| 40 | `rrp_bn` | 13 | `residual_ar_p1` | `withheld_no_gain` | `unavailable` | best baseline persistence: relative_gain=-0.017545 (min_relative_gain=0.05), gain_ci=(-0.027631, -0.004568) at level 0.9 |
| 41 | `rrp_bn` | 13 | `residual_ar_p2` | `withheld_no_gain` | `unavailable` | best baseline persistence: relative_gain=-0.032083 (min_relative_gain=0.05), gain_ci=(-0.044279, -0.006796) at level 0.9 |
| 42 | `rrp_bn` | 13 | `ridge_residual_a0.1` | `withheld_no_gain` | `unavailable` | best baseline persistence: relative_gain=-0.100748 (min_relative_gain=0.05), gain_ci=(-0.430244, -0.059071) at level 0.9 |
| 43 | `rrp_bn` | 13 | `ridge_residual_a1.0` | `withheld_no_gain` | `unavailable` | best baseline persistence: relative_gain=-0.100117 (min_relative_gain=0.05), gain_ci=(-0.410958, -0.059472) at level 0.9 |
| 44 | `rrp_bn` | 13 | `ridge_residual_a10.0` | `withheld_no_gain` | `unavailable` | best baseline persistence: relative_gain=-0.094582 (min_relative_gain=0.05), gain_ci=(-0.476542, -0.056517) at level 0.9 |

### What the answer licenses

**All 45 cells are `withheld_no_gain`; none is issued.** On the 2018-2021 dev window no preregistered
residual candidate beats its target x horizon's best baseline by the declared margin (relative MAE gain
>= 0.05) with a 90 % CI whose low end is above 0. Not one of the 45 gain CIs has a positive low end.
The study therefore licenses NO `statistical_forecast` estimate type for any component: every cell carries
`estimate_type: unavailable`, T22 has nothing to wire for reserves, TGA or RRP at 4/8/13 weeks, and the
T08 outlook stays accounting/scenario-only. A withheld answer is a complete answer.

The null is informative:

- Reserves (all horizons) and TGA (4 and 8 weeks): `seasonal_calendar` is the best baseline. The ridge
  residual models beat persistence (TGA h4 MAE 91.6 vs 100.0 $bn) but not the calendar (89.1). The
  closest cell in the family is reserves h4 `ridge_residual_a0.1`: gain +0.0106, CI (-0.027, 0.043).
  Only 6 of 45 point gains are positive at all.
- TGA 13 weeks and RRP (all horizons): `persistence` is best and every candidate is worse; the RRP ridge
  cells lose 0.09-0.47 with the whole CI below 0.
- `announced_only` is rendered `announced_only(empty)`: no curated announcement schedule exists at
  cohort 1, so its forecast is a zero change, its MAE equals persistence's, and the tie goes to
  persistence (ladder order).
- Calibration would have withheld almost every cell as well: only 3 of 45 cells (all RRP) have observed
  coverage within +/-5 points of nominal at both 80 and 90 %; the training-only (2008-2017) inner
  residuals under-cover the 2018-2021 dev window (e.g. TGA h13 80 % coverage 40-46 points, reserves h13
  62-72). The fixed precedence reports `withheld_no_gain` first.
- `forecast_identity` is the unavailable record (`no_h41_table5_anchor_in_inputs`); no anchor was
  fabricated, so the C16 identity is tested on fixtures only.

## §9 What would change the answer

- **A curated announcement schedule** (Treasury refunding TGA targets, QT caps) would make
  `announced_only` a real baseline and give the residual models a non-trivial residual; that is a new
  collector and out of T09 scope.
- **An H.4.1 Table 5 anchor in the inputs** would let the C16 forecast identity reconcile on real data
  instead of returning the unavailable record.
- **First-release vintages** (ALFRED or captured releases, cohort 3) would remove the stated revision risk.
- **The TGA canonical-store gap**: `data/treasury/tga.parquet` has no rows after 2021-09-30 inside the
  dev window, so 13 TGA origins per horizon are outage or
  outcome-unavailable (counted in the denominators, never dropped). Filled history would add them.
- **A different candidate family** (for example calendar features inside the residual model, or a
  regime-aware interval) only as a NEW preregistered family with its own ledger budget. This family and
  its margins are frozen and are never re-tuned on this result.
- The reserved window 2022-01-03 .. 2026-06-30 was not touched; only T20/T22 under the card's reveal
  custodian may spend a look.
