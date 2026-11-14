# R4: when regime conditioning helps, and when it manufactures precision

Date: 2026-10-17. Independent synthetic mathematical research under the existing PR #9507. This document is published before the diagnostic's Monte Carlo run. It is not native LR-W6/V3, a new empirical family registration, a market-data read or a deployed model.

## Current frontier and scope

The archive-qualification lane remains incomplete. A combined current-source/metadata-inspection call in this continuation was explicitly blocked before dispatch. No intended source read or local write is claimed to have occurred. The reason is not established; the same operation will not be retried, split or moved to a different tool/worker. The prior final-review provider403 remains separate and unretried.

This work is a genuinely independent algebraic question, using invented quantities only: when does conditioning on a regime improve estimation and selection, and when do small samples, shared noise or a changed relationship defeat it? It does not access the refused source files, archives, raw vendor data, runtime datasets, seals or look ledgers. A new bounded Fabric algebra consultation has its own stable task ID under the original research root, and is explicitly forbidden from inspecting those sources or replaying the old review.

## 1. Declared model, not a claim about actual sector returns

There are G=11 hypothetical groups. The known structural center is a_g, linearly spaced from -0.3 to +0.3. All quantities are dimensionless standardized opportunity units. They are not percentages, basis points, annual returns, account weights or real-regime parameter estimates.

A previous/current stable-regime deviation is delta ~ N(0, tau^2 I). An n-observation sample mean of historical opportunity is

    y_bar = a + delta + epsilon_bar
    Cov(epsilon_bar) = V = (sigma^2/n)[(1-rho)I + rho*11*u*u']
    u = ones(11)/sqrt(11), sigma=1.

The sample mean is generated directly from its exact Gaussian sufficient-statistic distribution. Independent replications are invented worlds, NOT independent days from a real return panel. Hyperparameters and, except in the deliberately misspecified case, the structural center are known to the comparator. Their estimation uncertainty is excluded and must be stated whenever the results are interpreted.

## 2. Fixed worlds and complete grid

Run all combinations of n in {4,12,48}, tau in {0,0.1,0.4}, rho in {0,0.6}, and these three worlds: 54 cells in total. Use 12,000 independent replications per cell, fixed seed 20261017, NumPy PCG64 generator. All cells are reported, not just favorable ones.

- **Stable:** current truth is a+delta; model center is a.
- **Relationship reversal:** current truth is a-delta, while the historical estimate remains generated from a+delta. This is a synthetic specification-break test, not a forecast of a real reversal.
- **Wrong structural center:** current truth is a+delta, but the model assumes center -a. Historical data remain generated from the actual a+delta. This tests shrinkage toward an incorrect economic prior.

No model is tuned after outcomes. The experiment does not choose an optimal shrinkage coefficient or a real sector allocation. The fixed grid is a falsifier set rather than an exhaustive stress universe.

## 3. Four estimators

For model center a_model and x=y_bar-a_model:

1. **Unconditioned center:** theta_hat=a_model.
2. **Hard regime cell:** theta_hat=y_bar, with no pooling.
3. **Scalar marginal shrinkage:** theta_hat=a_model+k*x, k=tau^2/(tau^2+sigma^2/n).
4. **Joint covariance-aware posterior mean:** theta_hat=a_model+K*x, K=tau^2(tau^2 I+V)^(-1).

The last two use oracle hyperparameters. They are conditional mathematical comparators, not qualified fitted investment models. No account optimizer, source adapter, feature registry or standing evaluator is created.

V has one common eigenvalue v_c=(sigma^2/n)[1+(G-1)rho] and G-1 contrast eigenvalues v_d=(sigma^2/n)(1-rho). K therefore has common/contrast shrinkage k_c=tau^2/(tau^2+v_c), k_d=tau^2/(tau^2+v_d). Implement the mean/contrast decomposition and independently compare it with a dense matrix inverse in tests.

For a constant common center and equal positive scalar k, all cross-sectional rankings are identical before/after shrinkage. For a constant center, the joint mean/contrast transform also preserves rankings when k_d>0. Thus smaller mean-squared error is not necessarily better selection. At tau=0 the shrinkage is zero and all estimated deviations tie; do not claim strict rank invariance in that degenerate case.

## 4. Analytical risk and falsifiers

Let b=a_model-a, and s=+1 in the stable/wrong-center worlds or -1 in the reversal world. Estimation error is

    (I-K)b + (K-sI)delta + K epsilon_bar.

Per-group mean squared error is

    ||(I-K)b||^2/G + tau^2*tr((K-sI)^2)/G + tr(K V K)/G.

Each estimator is a special case of this expression. Stable full pooling has risk tau^2; an unpooled hard cell has risk sigma^2/n. Therefore the ideal-center break-even is tau^2 > sigma^2/n. In the reversal world the hard-cell risk is 4*tau^2+sigma^2/n. Center bias is a separate failure, not something shrinkage automatically solves.

Each simulated MSE is compared with its closed-form value using its empirical Monte Carlo standard error; a six-standard-error discrepancy plus a numerical floor causes failure. This validates the declared simulation arithmetic, not the adequacy of its financial assumptions or the calibration of a fitted native test.

## 5. Decision metrics are not P&L

For every replication select the top three predicted groups, with stable index-order tie-breaking. Record latent mean-squared estimation error, average true latent opportunity of the chosen set, top-three opportunity regret versus an oracle that knows current truth, and optimism (reported chosen mean minus the true chosen mean).

Also compare a **dimensionless abstention decision**: act on that equal-weight top-three set only if its forecast mean exceeds a fixed hurdle 0.05; otherwise choose utility zero. If it acts, utility is the true latent selected mean minus 0.05. The oracle makes the equivalent decision knowing truth. This is a one-step utility toy. It is NOT a BIL investment, wealth path, transaction-cost estimate, confidence rule, risk mandate, position size or expected strategy return. Existing policy-accounting work is not replaced or rerun.

Report paired utility changes and their Monte Carlo uncertainty. Do not equate a reduction in MSE with economic superiority; a prior may improve average estimation and still obscure a rare true leader or react poorly to a structural change.

## 6. Three uncertainties must stay distinct

Parameter/conditional-mean uncertainty, future outcome variability, and probability of being top-ranked are different objects. A deterministic Gaussian example will compare P(theta>0) with P(Y_future>0) after adding independent future noise. It does not produce a real probability for a sector.

Selection-aware prediction methods in the existing literature appendix remain candidates only. Fresh primary-source review will check their selection, exchangeability, temporal dependence and delayed-feedback conditions; neither a paper title nor a marginal coverage result proves accuracy for a selected financial winner.

## 7. Acceptance and allowed output

Write reference tests before implementing the diagnostic: covariance decomposition, dense posterior equality, exact stable/reversal/bias risks, rank invariance and tau=0 edge, latent-versus-predictive uncertainty, malformed inputs, and no outcome/source/authority grant. Keep the full fixed-grid results and all unfavorable cases.

Permitted output: an independently checkable mathematical research result and concrete constraints for later model selection and uncertainty display. Not permitted: live ranking/sizing, a second empirical evaluator, source qualification by proxy, reopening native held results, reviving prohibited rotation×cycle/RS-dispersion gates, or calling an oracle simulation investment evidence.

The next model-research decision is whether the engine's proposed sophistication changes the actual choice, survives sparse support and misspecified mechanisms, and represents uncertainty correctly. The archive/consumer path remains separately governed and blocked only for the actual refused operation.
