# Curve-system DNS v1 result: point forecast rejected; directional calibration remains a prospective-only hypothesis

## Predeclared primary finding

The fixed dynamic Nelson-Siegel curve construction does **not** beat a no-change
10-year yield forecast on its declared primary test.

Primary period: 2021-01-01 through 2025-12-31.
Primary horizon: 20 common DGS observations.
Primary candidate: DNS multivariate direct factor dynamics (dns_var).
Benchmark: no_change.
Primary metric: 10Y change mean squared error in basis-point squared.

| Model | MSE bp^2 | MAE bp | Relative MSE reduction vs no-change |
|---|---:|---:|---:|
| no_change | **740.153** | **21.463** | reference |
| direct_ar10y | 774.234 | 21.737 | -4.60% |
| dns_diag | 798.870 | 22.046 | -7.93% |
| dns_var — PRIMARY | **881.014** | 23.311 | **-19.03%** |

The primary point estimate fails. Its paired squared-error HAC diagnostic is
mean -140.86 bp^2, t=-1.772, p=0.0763 (lag 40); this is descriptive and in the
wrong direction. No point-forecast construction is promoted.

## Short- and medium-horizon point errors

The same conclusion holds at the other declared horizons.

| Horizon | no-change MSE | direct AR relative MSE | DNS diagonal | DNS VAR |
|---|---:|---:|---:|---:|
| 5 observations | 176.531 | -1.44% | -6.91% | -10.07% |
| 20 observations | 740.153 | -4.60% | -7.93% | -19.03% |
| 60 observations | 2329.999 | -23.74% | -18.07% | -73.87% |

Negative means worse than no-change. At h=5, DNS diagonal and DNS VAR are
significantly worse on the diagnostic paired test (p=0.0047 and p=0.0005
respectively). At h=60 the DNS VAR is also materially worse (diagnostic p=0.014).
The random-walk/no-change baseline remains difficult to beat for levels.

The fixed six-node Nelson-Siegel representation reconstructs the observed 10Y with a
full-sample cross-sectional RMSE of 3.672 bp. That reconstruction error is not a
forecasting result and cannot explain away the larger forecast deterioration.

## Predeclared directional diagnostic

The protocol also predeclared a three-class probability diagnostic:
DOWN (<-2bp), FLAT (within +/-2bp), UP (>+2bp), calibrated from held-back prior
residuals. This diagnostic does **not** supersede the failed continuous primary.

There is one reproducible pattern worth carrying only as a new prospective
hypothesis:

| Period | Horizon | no-change Brier | direct AR improvement | DNS diagonal improvement | DNS VAR improvement |
|---|---:|---:|---:|---:|---:|
| 2021-2025 | 20 | 0.584242 | +2.24% | +0.80% | -1.06% |
| 2010-2020 context | 20 | 0.590754 | +1.95% | +0.81% | -3.17% |
| 2021-2025 | 60 | 0.539457 | +6.36% | **+9.10%** | +2.32% |
| 2010-2020 context | 60 | 0.644980 | +6.09% | **+6.97%** | -2.60% |

Positive means lower/better Brier than the no-change residual-calibrated probability
baseline.

This pattern is secondary evidence only. The h=60 primary-period slice has just
20 greedily non-overlapping windows (45 in 2010-2020 context), and the model/horizon
choice is visible after retrospective results. It therefore cannot be re-labelled a
validated forecast. If pursued, the next test must freeze the selected directional
candidate and accrue genuinely post-selection prospective calls before outcomes.

At h=5 the directional result does not replicate: DNS diagonal and DNS VAR worsen
Brier in both declared periods. This argues against a generic "curve factors predict
rates" conclusion.

## Data and clocks

Input is the immutable intersection of repository DGS1/DGS2/DGS3/DGS5/DGS7/DGS10
files frozen before evaluation: 12,574 common rows, 1976-06-01 through 2026-09-22.

Targets are common-DGS observed-date intervals, not certified Treasury trading
sessions. Missing dates are not filled; targets crossing >4-calendar-day source gaps
are excluded.

Fit/calibration are chronological:
- fit target ends before calibration starts;
- calibration target ends before forecast origin;
- fit max 2,520 pairs / min 1,260;
- calibration max 252 / min 126;
- refit cadence 20 source observations.

The source is corrected historical FRED data. Historical publication-time
availability is not certified.

## Immutable evidence

Freeze commit:
08ddb2c550ec84a4de9c780121a938dc0d02a1cf

Freeze time:
2026-09-25T00:04:18.258662Z

TrialLedger family:
ric_curve_system_dns_v1

Registered configurations:
12 = four models x three horizons.

Evidence:
- registration SHA256: e2c5b7b7c19a41b73ff2c0bcc2f8df18ad7f566f2bfb37e4377a872281ef3ce8
- predictions SHA256: 29fd579355ff8d9b3424ecc5ef3e65822780ee7a5376b914483917ef65666594
- summary SHA256: 8614e219879331571fca6dd9e07df4d3777eaadbb4497c420542026b8bf2dcde
- saved prediction rows: 131,464

Same-author verification recomputed both declared period summaries exactly from the
saved rows, checked unique model/horizon/origin identities, finite normalized
probabilities, purged fit/calibration clocks, the pre-registration TrialLedger prefix
and the exact 12-row family suffix. This is not independent review.

## Ruling

Do not promote DNS level forecasts.

Do not retune lambda, lags, fit windows or factor dynamics on the 2021-2025 primary
to recover the failed point forecast.

The only live scientific lead from this study is narrower: **longer-horizon direction
probabilities may carry information even when point-level forecasts are poorly
calibrated.** That lead requires a separately frozen prospective-only evaluation
before any product or portfolio authority.

No RIC stance, alert, equity risk state, rank, size, gate or trade authority changes.
