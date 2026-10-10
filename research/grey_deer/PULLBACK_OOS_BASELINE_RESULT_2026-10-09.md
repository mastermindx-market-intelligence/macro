# Pullback downside baseline — first frozen-fit OOS diagnostic

**Operation:** `risk-radar-pullback-20261009` · **Status: RESEARCH_REJECTED_FOR_PUBLICATION** (not a model release or production scoring source).

## Immutable prereg and test provenance

The exploratory evaluation design was published **before this comparison** at Macro commit
`d8676764b84652c0547be4f9179454ed46123988`, source
`research/grey_deer/PULLBACK_OOS_BASELINE_PREREG_2026-10-09.md`
(Git blob `d16f06d10d8d8ae60568c1fe197918ac3d9c1906`).
A prior full-history descriptive census had already been viewed; therefore
this is **not an untouched confirmatory holdout**, irrespective of the
pre-analysis commit. The current-vintage local source `data/yahoo/SPY.parquet`
was read without writes, SHA256
`6c785d556c22e20f85f89f55597b10469f0fc4c40a577b8efb04bc11964a3152`.
The price basis was `close_price`; the phase source was existing held
observer blob `54e7f0443d5b58d08a2a7327326e62766cc1ca0d`, invoked
at each historical origin with **only prices available through that date**.

The deterministic labeler and frozen empirical predictor live under
`research/grey_deer/`; no live Risk Radar engine, publisher, capital policy,
history ledger or view-model imports them.

## Frozen evaluation result

21-session stride after a 63-close warmup; 21-NYSE-session future-minimum
labels with strict maturity/null guards. Fixed pre-2018 fit; origins from
2018 forward are held out of all fitting. N=291 train origins; N=104
test origins; N=96 paired forecast origins (8 abstained for
undercovered phase cohorts). Counts of paired phases: monitoring 39,
underway 20, stabilizing 25, recovering 12. Peak dates are **weak
episode proxies**, not certified independent crisis IDs.

| Evaluation metric (96 paired test origins) | Unconditional baseline | Phase-conditioned baseline |
|---|---:|---:|
| Q25–Q75 predictive interval coverage; desired ≈50% | 42.71% | **39.58%** |
| Mean Q25–Q75 interval width (fraction of today's price) | 0.03619 | 0.03304 |
| Mean pinball loss, Q25 | 0.0070476 | **0.0071759** |
| Mean pinball loss, Q75 | 0.0119307 | **0.0121167** |
| Mean pinball loss, Q90 | 0.0078048 | 0.0076758 |
| Q90 exceedance (nominal ≈10%) | 9.38% | **12.50%** |

Higher coverage is better at a comparable interval width; lower pinball
loss is better. The phase-only candidate's tighter interval
undercovered; its Q25 and Q75 pinball loss worsened, and Q90
exceedances became more frequent even though Q90 pinball improved
slightly. These observations **do not establish incremental
predictive skill or support publication**.

Era robustness on the same paired origin set:

| Era | Paired N | Unconditional Q25–Q75 coverage | Phase-conditioned coverage |
|---|---:|---:|---:|
| 2018–2019 | 22 | 45.45% | 36.36% |
| 2020–2021 | 22 | 50.00% | 45.45% |
| 2022 onward | 52 | 38.46% | 38.46% |

The 2020–2021 stress era had a slightly better phase-conditioned Q90
pinball score, but only 22 paired origins and no independent
episode-clustered uncertainty assessment. Newer-era coverage is weak
for both baselines. Do **not** treat these descriptive differences as
a statistically significant regime-conditioned forecasting edge.

## Product ruling and next discriminating research

**Do not wire raw historical phase-conditioned probabilities or the
Paper illustrative total-depth numbers into live US/China Risk Radar.**
Keep the measured-only view and explicit `Estimate unavailable`.
The model must be developed around measured current depth, decline
velocity, realized volatility and source-qualified breadth/credit/rates
under actual historical availability clocks—not around the phase label
alone. Test a country-specific volatility-matched baseline first,
then a bounded conditional quantile candidate with rolling-origin,
episode-blocked validation and stress-era calibration. True PIT
price vintages and data licensing must be resolved before release;
a re-derivable current vendor vintage is not proof of first-known
signals.

No claim of live future-depth skill, precision of bottom timing,
investment sizing, or recovery/entry permission is made here.
The missing #8188 observer integration, US/China served-page
verification, full Paper matrix and independent review remain open.
