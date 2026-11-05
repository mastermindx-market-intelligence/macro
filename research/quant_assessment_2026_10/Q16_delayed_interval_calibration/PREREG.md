# Q16 — Delayed-feedback and regime-shift calibration of existing forecast intervals

Pre-registration. Written before any test-window outcome or synthetic-control outcome
was read. The only empirical read before this freeze is the training-window baseline
reproduction (`baseline_repro.py`, RUNS.log record 1). After the freeze this file is
never edited; any change goes into `PREREG_AMENDMENT.md`.

Author: Claude Opus 5.5 (model ID `claude-opus-5-5`), Q16 AUTHOR seat.
Status: research reference only. Nothing is wired, registered, scheduled, promoted or gated.

## 1. Question

Can an adaptive conformal layer (ACI, Gibbs & Candès 2021) on top of an existing scale
forecast improve 80% interval quality when labels arrive late (22 trading days later)
and the forecasts overlap? Or does delayed feedback make adaptation unreliable, so that
honest fixed split calibration should be kept?

## 2. Non-duplication (incumbent refresh and collision grep)

I ran the collision grep before writing any code. A search for
`conformal|ACI|gibbs|adaptive conformal` over `_base/engine` and `_base/scripts`
returned rc=1 (no conformal or ACI code). The new names `engine/interval_delayed_calibration.py`
and `tests/test_interval_delayed_calibration.py` are absent from `_base`.

Incumbents, and the narrow relation this study stays inside:

| Incumbent | What it is | Relation |
|---|---|---|
| ANTICIPATION_ENGINE.md §5.4 | Planned CQR (conformalized quantile regression), not built | No CQR program and no quantile regression here. Q16 tests only delayed-label and shift handling of a residual calibration layer. |
| cycle_masterplan PREREGISTRATION §18, CN-HAR-2 conformal layer | Frozen registration: pre-2024 fit, confirmatory after 2026-07-07, admin clock 2027-07-01 | Not read as data, not refit, not re-scored, not re-registered. Q16 touches none of its files, trials or forecasts (requirement 6). |
| HAR-1 cycle_pattern analog cone (`har_scorecard.json`, promoted_null) | Analog cone with cn_sector coverage 0.445 < 0.60 | Different estimand (analog cone). Unchanged. |
| MRI-R30 release interval recalibration V1 | Vol-scaled residual quantiles in `engine/release_forecast`; `PREREG_INTERVAL_RECAL_V1.md`; `tests/test_release_interval_recal.py` | Release-surprise intervals with honest N ≈ 36. Not consumed and not altered. |
| `engine/prophet_live/interval.py` | Armed-pack price interval contract | Unrelated contract. Untouched. |
| `trial_ledger.py`, `calibration_hub.py`, OA-3/qledger | Trial, grade and calibration owners | Nothing is written to them. No new trial ID is minted there. |
| `engine/vol_forecast.py` (HAR realized-vol cone) | Incumbent base scale predictor | Consumed unchanged as the scale `σ_h`. Same sha256 in Q16 and `_base`. |

Q07 (fitted HAR volatility, a sibling brief) is not read and not depended on. It is a
possible future base predictor; this is listed as a limitation.

Standing kills and holds are respected: DNR:KILL-OUTCOME-AUDITION (one frozen design,
single holdout); DNR:KILL-LLM-ORIGINATION (no LLM produces a number); DNR:KILL-FUSED-COMPOSITE
and DNR:KILL-REGIME-SCORECARD and DNR:KILL-COMPOSITE-REGIME-RELIABILITY-MONITOR (no
composite, scorecard or monitor is built; regime cells are support disclosure only).

## 3. Estimand, unit and clocks

- **Estimand.** The central 80% (α = 0.2) interval for the 22-trading-day log return
  `y_t = log C_{t+22} − log C_t`. The interval is `[−q_t, q_t]·σ_{h,t}`, where
  `σ_{h,t} = vol_forecast.har_vol(close)_t · sqrt(22)`. The centre is zero.
- **Score.** Normalized absolute residual `|s_t| = |y_t / σ_{h,t}|`.
- **Unit.** One (asset, origin-day) forecast. Evidence is counted in non-overlapping
  22-day blocks, never in rows.
- **Input clock.** The forecast is emitted at close t from closes up to and including t.
- **Output (label) clock.** The label matures at close t+22, with `avail_lag = 0`. An
  update at origin i may consume only origins j with `j + 22 ≤ i` (requirement 1).
  Every runner returns `consumed_max` and the evaluation counts maturity violations; the
  required count is 0.
- **Cohort.** SPY, QQQ, IWM, TLT and GLD, restricted to their common trading-date axis
  (2004-11-18 to 2026-10-08, 5506 dates; the baseline run fixes these values).

## 4. Source vintages (read-only, licensed local data, vintage cdab6268)

| Input | sha256 |
|---|---|
| macro-main `data/yahoo/SPY.parquet` | 6c785d556c22e20f85f89f55597b10469f0fc4c40a577b8efb04bc11964a3152 |
| macro-main `data/yahoo/QQQ.parquet` | 5e851c16c54a1bfe190cdc454cf88b17b2a23601d6e15897f74be2ad19bebf0c |
| macro-main `data/yahoo/IWM.parquet` | fbb51d631c7bae1d9c76152e24b291ea2847c76a424a8db8385c267109f962ea |
| macro-main `data/yahoo/TLT.parquet` | 609a3eddb55dcbe33c66c98ddf0a635d0a49a685edee6d2651e17c18dc472a93 |
| macro-main `data/yahoo/GLD.parquet` | 07170179f8c72d63b5c5144481bde2c81df2c8dbf7fde2dfe2a4499771a1527b |
| `engine/vol_forecast.py` (incumbent, unchanged) | bcd6ec2cc8c116b469173ab475dc495be7e024b4ea452b9d1cf6de58301e06c0 |
| `engine/interval_delayed_calibration.py` at freeze | a8eba0a0017fa4f3e3616622c56c09aa0727db0dc5e82763e31eb0d953df67cb |

The price column is the adjusted `close`. `evaluate.py` re-hashes every data input and
`engine/vol_forecast.py`, and refuses to run on a mismatch. After the run, the only
permitted edit to the harness module is the `Q16_VERDICT` string and the verdict
sentence of its docstring.

## 5. Baseline (reproduced before the freeze, training window only)

Nobody has published coverage numbers for the incumbent vol cone, so the baseline is
re-derived. RUNS.log record 1 (exit 0, input sha256s as above; output
`baseline_train.json` sha256 ef388b2589497c4237315070304f90f4149d0ba19695b7456bcaa721e35f6dfb)
reads the cone as a Gaussian ±1.2816·σ_h band. Its coverage on matured training origins
is 0.66–0.76 against a nominal 0.80, so the naive cone under-covers. This motivates
calibration, but it says nothing yet about adaptive versus fixed calibration.

## 6. Competitors

| ID | Method | Role |
|---|---|---|
| M0 | Naive Gaussian cone, q = 1.2816 | Descriptive only (incumbent reading) |
| FIXED | Split conformal. One quantile of matured training scores (`fixed_split_quantile`, level 0.8), frozen | **Primary baseline** (honest fixed calibration) |
| ROLLING | Conformal quantile of the last W = 504 matured scores, `min_calib = 252` | Secondary competitor |
| ACI | Delayed-feedback ACI on the same matured rolling buffer. `alpha_t` is updated by `gamma·(α − err_{i−22})` only when the label matures, and clipped to [0.005, 0.995] | **Candidate** |
| LEAKY | ACI consuming the previous origin's immature label (delay 1) | Diagnostic only, invalid by construction |

**Tuning (inside training only).** ACI's `gamma` is chosen per asset from the grid
{0.001, 0.005, 0.01, 0.02, 0.05} by `tune_gamma`, which:

- masks every label not matured by train_end,
- truncates the series at train_end,
- minimizes the mean normalized interval score over origins [504, train_end − 22],
- breaks ties toward the smaller gamma.

The FIXED quantile uses only matured training labels. W, min_calib and the clip are
fixed in advance; they are not tuned. All methods run online from the start of the
data. ROLLING and ACI therefore warm up inside training.

## 7. Chronological split and outcome windows

- **train_end** = the position of 2014-12-31 on the common axis (position 2546).
- **Training labels:** origins with i + 22 ≤ 2546.
- **Test origins:** i > 2546 with a finite label (matured by the data end), a finite
  σ_h and a finite issued q for every compared method. This is the common support:
  about 2937 origins per asset and about 133 honest blocks.
- **Single holdout.** It is evaluated once. There is no repeated holdout search and no
  re-split.

## 8. Metrics (requirement 3)

All three metrics are reported for every method, overall and per asset:

- **Coverage:** mean of `|s| ≤ q`.
- **Width:** mean normalized width `2q`.
- **Interval score:** normalized Winkler `nIS = 2q + (2/α)·max(|s| − q, 0)`.

Raw-unit width and IS (multiplied by σ_h) are reported descriptively. Coverage alone
never decides anything: a wide interval pays for its width through nIS.

## 9. Hypotheses, primary statistic and practical bar

- **Primary statistic.** For each test date t on the common support of all five assets,
  `d_t = mean_a nIS_ACI(a,t) − mean_a nIS_FIXED(a,t)`. The relative effect is
  `R = mean_t d_t / mean_t mean_a nIS_FIXED(a,t)`.
- **H1 (adaptive helps):** R ≤ −0.02 (at least a 2% interval-score improvement) with
  the bootstrap 95% CI upper bound for R below 0.
- **H0:** otherwise.

**Trial family.** There is one confirmatory comparison: ACI vs FIXED on pooled nIS.
The gamma grid is a training-only tuning step, not a test-time trial. The synthetic
controls are a gate. Everything else is descriptive and makes no claim.

## 10. Dependence-aware uncertainty and honest N (requirement 2)

- **Primary uncertainty.** A circular moving-block bootstrap on the date axis
  (`circular_block_bootstrap`) of the ratio `mean(d)/mean(FIXED)`. Both series are
  resampled with identical blocks. Block length 44 (= 2h) covers the 22-day label
  overlap; pooling across assets per date absorbs cross-asset correlation. B = 2000,
  seed 16.
- **Secondary.** A Newey–West (Bartlett) HAC standard error of mean d with 44 lags.
- **Honest N.** The number of non-overlapping 22-day blocks among test dates
  (`honest_block_count`). Rows, and the five assets, are not independent evidence.
  Repeated daily forecasts of overlapping outcomes are never counted as separate
  confirmations.

## 11. Synthetic controls (requirement 4) — gate

`control_experiment` runs 200 replications for each of three scenarios: stationary,
shift_up (shock scale ×2 at the test midpoint) and shift_down (×0.5).

- **Settings:** n = 6000, h = 22, α = 0.2, n_train = 3000, W = 504, the same gamma grid
  tuned inside training, and a stale predictor.
- **Seeds:** stationary 10000+r, shift_up 20000+r, shift_down 30000+r, for r = 0..199.

`discrimination_verdict` applies these criteria, with noise_tol 0.02 and cov_gain 0.05:

- **stationary_no_noise_chasing:** mean ACI test nIS ≤ 1.02 × FIXED.
- **shift_up_coverage_recovers:** the post-shift ACI coverage gap is at least 0.05
  smaller than FIXED's, and ACI's post-shift nIS is lower.
- **shift_down_sharpens:** ACI's post-shift mean width is lower and its nIS is lower.

`controls_discriminate` is true only if all three hold. Each replication's ACI maturity
violations must be 0.

## 12. Decision rule, falsifier and stop rule

**INSUFFICIENT_DATA** if the honest test blocks on the common support number fewer
than 60, or if any input hash mismatches.

**KEEP** (adaptive layer) only if ALL of:

1. R ≤ −0.02 and the bootstrap 95% CI upper bound for R < 0.
2. The pooled ACI test coverage gap `|cov − 0.8|` ≤ max(FIXED gap, 0.03).
3. The pooled ACI mean normalized width ≤ 1.25 × FIXED.
4. The pooled point mean of `nIS_ACI − nIS_ROLLING` ≤ 0 (the adaptive state must add
   something over plain rolling recalibration).
5. `controls_discriminate` is true and the total ACI maturity violations (empirical and
   control) equal 0.

**REJECT** otherwise: the adaptive layer is rejected and honest fixed calibration is
kept.

**Falsifier (brief).** "If delayed feedback makes adaptation unreliable or intervals
expand without useful sharpness, reject the adaptive layer and retain honest fixed
calibration." Criteria 1–5 encode it: unreliable adaptation fails 1, 2 or 5;
expansion without sharpness fails 1 or 3.

**Stop rule.** `evaluate.py` runs once. A rerun is allowed only after a crash (non-zero
exit before any result file is written), with identical configuration, and it is logged
in RUNS.log. No parameter, window, asset, horizon or split is changed after an outcome
is seen. A changed design is a new study (PREREG_AMENDMENT.md plus a new identity).

## 13. Descriptive outputs (no claims)

- Per-asset coverage, width and nIS for M0, FIXED, ROLLING, ACI and LEAKY.
- Per-regime support (requirement 5). Regimes are terciles of `vol_forecast.vol_regime`
  at t (low/mid/high/unknown). For each regime and method the output gives rows, honest
  blocks and coverage. Cells with fewer than 20 honest blocks are flagged
  `support_ok = false`. Every row carries `conditional_coverage_claim = false`; no
  universal conditional-coverage claim is made.
- `avail_lag = 1` sensitivity: ACI re-tuned and re-run with a one-day publication lag.
- The LEAKY minus ACI nIS gap, sizing how much a naive look-ahead implementation gains.
- Attrition: origins dropped for missing σ_h, missing label, or missing issued q
  (warm-up), per asset.
- The gamma tuning tables and the chosen gamma per asset.

## 14. Requirement 6 boundary

Nothing writes outside this directory. No existing file is edited. CN-HAR-2, HAR-1,
MRI-R30, trial_ledger, calibration_hub, qledger and every live forecast are untouched.
The module holds no handle to any of them, and the test suite pins that inputs are not
mutated and that nothing is written.

## 15. Limitations known in advance

- The adjusted-close vintage is not point-in-time (later dividend adjustments are
  applied retroactively). This matters little for 22-day log returns but is not zero.
- The zero-drift centre: only the scale is calibrated.
- The five assets are correlated. Pooling per date handles this in uncertainty, but the
  panel is narrow.
- Q07's fitted HAR is not used as the base predictor. Results are conditional on the
  incumbent `vol_forecast.har_vol` scale.
- One horizon (22) and one level (80%).
