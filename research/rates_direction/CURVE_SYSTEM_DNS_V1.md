# Curve-system DNS forecast v1 — pre-outcome contract

Parent: WS:RATES-INFLATION-COMMAND / rates-direction-20260924-sol-001 / PR 7909.

Procedure pin: Mastermind 819abc8c23609cdded2b33f6e1bfc7854bd5c847,
Skillpack mastermind.sol_skillpack.v1 1.0.1 / bootstrap major 1.

## Hypothesis

The rejected RD1 model forecast each tenor directly from recent yield changes, two
curve spreads and real-rate features. The rejected oscillator studies forecast from
technical phase, and the rejected shock study conditioned an already-observed rate
impulse on contemporaneous driver states.

This is a materially different hypothesis: the Treasury curve is a low-dimensional
dynamic system. A fixed Nelson-Siegel level/slope/curvature representation, with
factor dynamics estimated only from observations available before each forecast,
may forecast the 10-year yield level better than a no-change/random-walk benchmark
at short/medium horizons.

This is corrected-history chronological research only. It does not establish
historical publication timestamps, executable prices, prospective accuracy or trade
authority.

## Fixed source panel

Use only existing repository FRED constant-maturity Treasury files:

- DGS1.parquet  SHA256 6b5e423be804de3da0f7380301fedbb9ce4f89f2d57cb307306c2eaa50054549
- DGS2.parquet  SHA256 0cb9aa029d0d435b013b25421ba8c9365b61dcda07deaea386061396760c4eec
- DGS3.parquet  SHA256 cb889793f79d91902537b944a217716f4b3e838faa255226419e7079c86996d9
- DGS5.parquet  SHA256 e32bbcf503b1bfc96dd7e7a1cf0523895b7ab19d9e9eeccc8a9661650ec51ca3
- DGS7.parquet  SHA256 97f8d99591f210b5ec0bb14aec90b679e5d5d88e74bd9e3c7170bf2a6cef774b
- DGS10.parquet SHA256 7369b3a15097c9ff06e765ca76476f34263ad2ae3759827e878fdea44f6bfbf9

Use the exact intersection of finite date labels. At freeze preflight this is 12,574
rows from 1976-06-01 through 2026-09-22. Missing dates are never forward-filled.
Targets crossing a source-date gap greater than four calendar days are ineligible.

The source is the incumbent corrected Treasury history, not a new dataset owner.

## Fixed curve representation

Maturities are [12, 24, 36, 60, 84, 120] months.

Use the standard three-factor Nelson-Siegel loading matrix with fixed
lambda = 0.0609 per month:

level loading = 1
slope loading = (1 - exp(-lambda*tau)) / (lambda*tau)
curvature loading = slope_loading - exp(-lambda*tau)

Estimate each date's three beta factors by ordinary least squares across the six
observed yield nodes. Lambda is never fitted or searched. This research implementation
does not replace engine/yield_curve.py as the production curve owner.

## Fixed forecast models

All models forecast the 10-year yield LEVEL at h observed-date intervals, then report
forecast change in basis points relative to the origin 10-year yield.

1. no_change
   Future 10Y level equals current 10Y level.

2. direct_ar10y
   Horizon-specific direct OLS:
   10Y[t+h] = a + b * 10Y[t].

3. dns_diag
   Three separate horizon-specific direct OLS models:
   beta_k[t+h] = a_k + b_k * beta_k[t].
   Reconstruct future 10Y from the three forecast factors.

4. dns_var — DECLARED PRIMARY CANDIDATE
   Horizon-specific direct multivariate OLS:
   beta[t+h] = a + B * beta[t].
   Reconstruct future 10Y from the forecast factors.

No alternate lambda, extra lags, macro variables, oscillator states, regularization
grid, regime selector or model ensemble is authorized in v1.

## Horizons and fitting clock

H = {5, 20, 60} observed DGS10-date intervals, approximately one week, one month and
three months. These are not certified Treasury trading sessions.

At a refit origin:
- eligible historical pair j requires j+h < current origin;
- last 252 eligible historical pairs form the residual-calibration candidate block;
- fit pairs must have target end strictly before the first calibration origin;
- fit uses at most 2,520 pairs and requires at least 1,260;
- calibration requires at least 126 pairs;
- refit every 20 source observations.

The same fit/calibration clocks apply to every model. No target from or after the
current origin may enter fit or calibration.

Residual calibration:
- compute each model's signed 10Y-change residuals on the held-back calibration block;
- add those residuals to the current point forecast to form an empirical predictive
  distribution;
- p_up = P(change > +2bp), p_down = P(change < -2bp), p_flat otherwise, with one
  Laplace pseudo-count per class.

The +/-2bp band is fixed for all horizons. Continuous forecast error remains primary;
the class probabilities are a directional diagnostic.

## Evaluation

Primary evaluation period: forecast origins 2021-01-01 through 2025-12-31, with
target_end also no later than 2025-12-31.

Primary test:
- tenor: 10Y
- horizon: 20 observed-date intervals
- candidate: dns_var
- benchmark: no_change
- metric: mean squared error of 10Y yield change in bp
- relative MSE reduction = (MSE_no_change - MSE_dns_var) / MSE_no_change
- positive is improvement.

Mandatory secondary reporting:
- h=5 and h=60 for all four models;
- MAE;
- three-class Brier and log loss using the +/-2bp classes;
- count of forecast origins;
- greedily non-overlapping windows;
- date-span;
- Newey-West diagnostic on paired squared-error improvement using lag 2*h;
- 2010-2020 pre-primary history reported separately as context only, never used to
  rescue a failed 2021-2025 primary.

A model is NOT accepted merely for a positive point estimate. A prospective shadow
and independent review remain required before authority. If the primary relative MSE
is <= 0, v1 is a null for this construction and must not be retuned on the primary
period.

## Trial accounting

Register exactly 12 configurations in one new TrialLedger family:
ric_curve_system_dns_v1 = 4 models x 3 horizons.

Baselines count in the declared family so the research width is explicit. No reset
of the family after results.

## Authority ceiling

Research-only. No RIC stance, alert, equity risk state, rank, size, gate, trade,
production forecast, or portfolio behavior changes. A positive retrospective result
may at most justify a separately frozen prospective shadow through an existing
evaluation owner.
