# Dispersion audit: market-relative is not market-exposure-neutral

Status: FEATURE-ONLY MEASUREMENT AUDIT. This is not a future-return test, not a recommendation to replace the incumbent regime axis, and not proof of fund flows.

## Exact mathematical issue

Subtracting the same market return from every industry leaves cross-sectional dispersion unchanged:

    SD_g(R_g - R_market) = SD_g(R_g).

Thus 'dispersion of market-relative returns' has not removed heterogeneity in market sensitivity. With R_g = beta_g * M + e_g, the exact equal-weight cross-sectional variance identity is:

    Var(R) = M^2 Var(beta) + Var(e) + 2 M Cov(beta, e).

The covariance term may be negative; component ratios must not be sold as a causal decomposition. Here e can absorb an intercept and omitted factors. Neither e nor its dispersion is known to be mispricing or money flow.

An illustrative, non-empirical example makes the problem clear: if three industries have fixed betas 0.5, 1.0 and 1.5, and a market shock is -4%, their model returns are -2%, -4% and -6%. There is dispersion and apparent defensive relative leadership without any assumed change in exposures or demand for the defensive industry. Subtracting -4% from each return does not eliminate the spread. Relative outperformance also does not make the -2% long position profitable.

## Fixed empirical diagnostic

The code design was committed before reading these diagnostic results at `112f4356d15c6e0cf4024db26f45e757f25fdd65` in `dispersion_audit.py`. SHA256: `c7a170cd045d7e0f45fe85a5c1a145889247fbeafc687d15a1a4ae5233152895`.

Inputs are the same hash-asserted French49 and market daily returns, numerically filtered through 2002-12-31. At each month end, fit each industry's intercept and beta on 252 daily log returns ending before the recent21-session evaluation window. Require at least20 complete industries. Compare cross-industry dispersion of recent21 log returns with dispersion after subtracting the frozen intercept-and-beta prediction. 'High' means above the series' own 80th percentile over the preceding120 calendar months, excluding the current month; all120 prior observations required.

This is a fixed measurement convention, not an optimized or calibrated regime definition. No forward trade outcome is evaluated.

## Results

788 eligible months, 1937-05 through 2002-12:

| | Adjusted not high | Adjusted high |
|---|---:|---:|
| Raw not high | 574 | 39 |
| Raw high | 38 | 137 |

There are 175 raw-high months and 176 adjusted-high months. Of raw-high months, **38/175 = 21.71%** are not adjusted-high. Conversely, **39/176 = 22.16%** of adjusted-high months are not raw-high. The two level series remain strongly related: Pearson correlation0.9009 and Spearman0.9099. The distinction is consequential for some high-state classifications, not evidence that the original measure is generally worthless or that the adjusted one forecasts better.

Mean absolute recent21 market log return by cell: neither high2.96%; adjusted-only high5.57%; raw-only high4.12%; both high4.74%. These diagnostics do not establish that every disagreement is caused only by beta; estimated intercepts, residual shocks, model error and moving thresholds also matter.

All monthly raw-versus-market-relative standard deviations matched numerically. The variance identity's largest absolute error was 1.04e-17. The lagged threshold passed a prefix-invariance check at1970-03. Process66827 exited0. Full local `DISPERSION_AUDIT_RESULTS.json` SHA256: `e616fdf8788e8ead2370405a114c9e590089c2f8722e1c3aca5935f674d85a4f`.

## Consequence for regime research

Keep raw dispersion as a measurable state, but do not rename it 'rotation opportunity' without a payoff test. Add exposure-adjusted dispersion as a challenger, not a new automatically favorable vote. At stock level, separate between-industry dispersion from within-industry dispersion; they need not imply the same opportunity. Freeze exposures, constituents, thresholds and any state-filter parameters before the decision. Validate on original timer events and compare at matched opportunity coverage.

These results use current-vintage industry data rather than a historical-vintage archive. Industry-level dispersion is not a direct test of stock dispersion, monetary regimes, flow migration, or durable bottoms. No post-2002 outcome, private stock panel, live trading or deployment was used.
