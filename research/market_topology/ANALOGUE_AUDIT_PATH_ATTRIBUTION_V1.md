# Analogue audit and path attribution v1

Research-only continuation of market-topology-research-20260923-astra-001 and PR #7812. This addendum is defined AFTER seeing the first analogue summary. It is therefore a disclosed diagnostic/exploratory follow-up, NOT an untouched confirmatory test or a new successful model. It does not tune or refit the failed/unsupported primary comparison.

## Inputs and custody

Use the original archived French ZIP (SHA256 13be85084196424aa85f29136af47f147a443275f90eb0955dbcdc6d6d25f448), committed industry_analogue_v1.py (script SHA256 7113dbb88a27532444174517c63fb9890535aaf1c202f843b469041b984af9e9), and its saved panel/predictions/summary. Summary SHA256 f0aaec4538bec2bc8a14cb1b2a7c30898a84679de7db8e090a13bf7ab0222285; panel SHA256 4bcde563d722e962dc04b8beb30108b047ff598051b2924b37bddcc8df285015; predictions SHA256 a88aec19a8cfbc554e682885a37e7a92f23c09fa2b6d4a36cb03760f61cc0fcc. No source-file modifications or rerun of fitted/retrieved predictions.

## A. Independent numerical and chronology audit

Parse saved JSONs strictly; recompute all target RMSE/MAE from the per-query predictions and compare with the saved summary. Check every selected neighbour's date, K=20, minimum 126-session spacing, and s+20 < t-252. Check whether any feature has zero historical variance at any query; v1's sd=1 fallback would not implement the protocol's zero-contribution rule when a query differs from a constant training column. If this occurs, mark the affected experiment invalid pending explicit correction, not silently passed.

Compare each analogue's primary squared error with the unconditional expanding-history mean using 5,000 circular 12-month-block bootstrap resamples, seed 2026092303. Positive gain means the analogue improves over unconditional. These extra pairings are diagnostic nominal intervals, not familywise tests.

Report neighbour RMS standardized distances (sqrt of stored distance), nearest and furthest distributions, and empirical 10th-90th percentile neighbour outcome ranges: mean width and realised primary outcome coverage. These are UNCALIBRATED retrospective support diagnostics, not advertised prediction intervals. Do not choose an abstention threshold or shrinkage weight after inspecting which dates lose.

## B. Sequence decomposition, not a new alpha label

For the feature-selected illustrative dates 1992-01-31 and 2013-11-29, report the 49-industry distribution of sign patterns over the oldest, middle and newest nonoverlapping 21-session blocks. +++ means positive in each block, NOT uninterrupted daily gains and NOT a proven future leader. -++ is a recovery-shaped trajectory; ++- is a recent setback. Preserve all patterns and near-exact-zero states. Report the per-block equal-industry proxy returns and median industry returns. Cases were selected to maximize persistence difference under declared matching tolerances, not randomly sampled.

## C. Fresh progress versus rolling-window expiration

At the same 311 monthly query dates, let M63(t) be an industry's trailing 63-session cumulative log return. The exact identity is:

M63(t)-M63(t-21) = [sum of newest 21 returns] - [sum of 21 returns that just left the window].

Compute the identity both absolutely and benchmark-relative, with the same daily-rebalanced equal-industry proxy. Count improvements (>1e-12) whose NEW 21-session return is nonpositive (<=1e-12). Report counts and pooled fractions, plus distribution of monthly fractions. A rising trailing momentum value can therefore occur without fresh positive performance/outperformance. This is an attribution fact, NOT proof of mispricing or negative alpha.

Under independent identically distributed symmetric continuous zero-drift newest/expired returns, the conditional proportion equals 25% analytically: P(new<=0 and new>expired)=1/8, divided by P(new>expired)=1/2. This is a reference null, not an empirically fitted benchmark. Do not claim an empirical fraction is unusual without an appropriate dependence-aware test.

## Interpretation boundaries

A low +++ population may reflect recently broadening recovery rather than sideways churn. Preserve trajectory order and recency. Neither this follow-up nor the prior negative analogue result settles stock-level forecasts. Data admission, current September market verification, terminal outcomes and the held stock trial remain unresolved. No Fable commission, production model, probability, trade, worker or wake is created.
