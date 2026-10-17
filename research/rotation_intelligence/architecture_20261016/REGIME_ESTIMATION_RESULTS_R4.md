# R4 results: conditional intelligence must improve the decision, not just the fit

Date: 2026-10-17. Research-only result in the existing PR #9507. No real market data, returns, native held outcomes, data-source qualification, production model or account allocation is claimed.

## 1. What changed in this continuation

The original archive/consumer task did not execute: a combined source/metadata-inspection call was explicitly blocked before dispatch. Its reason is unestablished. It was not split, replayed through another tool, or delegated. No archive payload or requested source file was read by that refused call. The prior final-package reviewer403 remains a different preserved failure. These are action-local constraints, not evidence that the entire mission or all tools are unavailable.

A genuinely independent, bounded research lane was completed instead: test the benefit and failure of regime-specific estimation under known synthetic assumptions, then assess how uncertainty should be exposed to a selected-sector consumer. The original metadata discovery and thirteen-series Data OS reuse proposal remain intact and unqualified for investment use.

[REGIME_ESTIMATION_DESIGN_R4.md](REGIME_ESTIMATION_DESIGN_R4.md) was published at `9a0540f8d6e2ff865f33f0d75d9e8c3e63b8120b` before this diagnostic was run. The grid and methods were not chosen after results. The methods do not consume the seven-pair native study or the nulled member-stock persistence panel.

## 2. Executed scope and reproducibility

The script [regime_conditioning_r4.py](regime_conditioning_r4.py) evaluates all **54 declared cells**, each with **12,000 invented worlds**, comparing four estimators. This is 648,000 synthetic replications, not 648,000 independent historical market observations. The model generates the exact distribution of a Gaussian sample mean; it does not replay returns or fit a time-series regime detector.

The structural center and covariance hyperparameters are known to the oracle comparators except where the center is deliberately misspecified. Estimation of those quantities, non-Gaussian tails, true regime uncertainty, transaction execution and actual market costs remain outside this diagnostic. The utility hurdle is 0.05 in arbitrary standardized units, not a bill yield or basis-point charge.

The complete grid is published in [regime_conditioning_grid_r4.csv](regime_conditioning_grid_r4.csv). Every stable, reversal, no-effect, weak-effect, strong-effect and wrong-center cell is retained. CSV fields are reported to six decimal places; `_delta_utility_vs_center_se` is the **Monte Carlo standard error of the paired utility difference versus the unconditioned-center comparator**, not a market-estimation confidence interval.

### Verification actually performed

- **20 reference tests passed**, including a dense-matrix posterior comparison, analytical stable/reversal/bias risks, rank invariance, ties, target uncertainty and invalid inputs.
- A complete-shaped zero-output placeholder first produced **25 assertion failures across those tests/subtests**, with no unrelated test errors. The earlier bare interface stub had missing-output errors and is not used as the discriminating red result.
- **216 simulated MSE values** agreed with the declared closed-form risks within the predeclared Monte Carlo tolerance. That is four estimators × 54 cells, not a fitted empirical significance claim.
- **1,000 additional flat-center fixtures** preserved the top-three rankings under both positive scalar and equicorrelated joint shrinkage, as the algebra requires.
- **Six deliberate mutations** were caught by their intended assertions: double-counting the prior variance, ignoring a regime reversal, omitting future noise, acting at hurdle equality, omitting center bias, and discarding correlation. Each produced one intended assertion failure and no unrelated test error. These are author checks, not independent final review.

Exact published source at `b5d66b9d663e60d3d958ae12a43865cf43df8b22` was retrieved and executed on M2 Python 3.14.7 / NumPy 2.5.2. All 20 tests passed and the complete published six-decimal CSV was reproduced **byte for byte**. Source/import inspection confirmed the declared numerical and standard-library modules, with no product imports or market-data reader.

Source SHA-256: `ebd5b6a2e2b7f014a6b855b466603976417bfcaee8dbf4d2e13c534471f20519` (7,376 bytes).

Test SHA-256: `bac45e42c18d903e66a0dcbf6f7fcdcc4ead8508183224ba3c18dac5b1304a54` (5,402 bytes).

Published grid SHA-256: `3bf274c893a5e523d1a9ca0027702f6f847876fc472711ca863b5eafe26199f8` (9,357 bytes).

Full local JSON SHA-256: `6b8e55262e3cd42588155c5fdd05f5b658db37bacd8c038a198ce447fc6aba8e` (268,315 bytes). Full M2 JSON SHA-256: `b6be1d2bb465e9410a325654949ce8d671738636a6e7be1de092abcdfb3995a3`. Full raw JSON byte equality is **not** claimed; environment metadata differ. The declared published CSV equality is the verified cross-environment result. The script regenerates the complete precision output and additional diagnostics.

## 3. Result A: detailed regime cells can be much worse with weak support

For n=4, tau=0.1 and rho=0.6 in the stable world:

| Estimator | Mean-squared error | Top-three opportunity regret | Toy utility |
|---|---:|---:|---:|
| Unconditioned structural center | 0.010004 | 0.019086 | 0.190998 |
| Unpooled hard regime cell | 0.250028 | 0.110832 | 0.084190 |
| Scalar oracle shrinkage | 0.009636 | 0.019067 | 0.191017 |
| Joint oracle shrinkage | 0.009186 | 0.018672 | 0.191412 |

In this specified weak-effect/small-sample world, hard conditioning adds a great deal of noise. Shrinkage limits that damage, but scalar shrinkage's utility increment over the center is only about 0.000019, with Monte Carlo standard error about 0.000011. An attractive MSE reduction is not an economically meaningful sector-selection claim.

The exact ideal-center comparison is simple: full pooling has per-group risk tau^2; the hard-cell estimate has risk sigma^2/n. Hard conditioning improves that risk only when tau^2 exceeds sigma^2/n. This is an algebraic condition under the declared model, **not a universal minimum historical sample size**. Real regime samples can be dependent, selected, revisable or structurally nonstationary.

**Design consequence:** avoid a large table of sector × quad × real-rate × breadth cells that behaves as if a handful of observations precisely determines a preference. Pool information, retain support, and test whether the extra conditioning changes useful choices.

## 4. Result B: better estimation can leave rankings unchanged—or make decisions worse

With the same constant center for every group, a positive common multiplier is monotonic, so scalar shrinkage cannot change the ordering. Under this diagnostic's equicorrelation structure, joint shrinkage is

    Kx = k_contrast*x + (k_common-k_contrast)*mean(x)*ones.

The second term shifts every group equally and the first has a positive common multiplier. Therefore joint shrinkage also preserves ordering in that flat-center setting. Merely saying the model uses a covariance matrix does not prove a better top-three list. The statement excludes the tau=0 degenerate tie case.

There is a stronger adverse decision example in the wrong-center world, n=4, tau=0.1, rho=0.6:

| Estimator | Mean-squared error | Top-three regret | Toy utility |
|---|---:|---:|---:|
| Hard cell | 0.249615 | 0.110258 | 0.083079 |
| Joint oracle shrinkage toward the wrong center | 0.128011 | 0.492067 | -0.283781 |

The shrinkage estimate has smaller average squared error but makes much worse selections and actions under the chosen utility. Its incorrect prior centers preserve the wrong economic ordering. This is not evidence that shrinkage is generally bad; it is a precise falsifier of “lower forecast error guarantees better allocation.”

**Design consequence:** benchmark estimation, group selection and costed policy independently. Require actual selected-set improvement and preserve misspecified-prior cases. Do not choose a model solely by average error or a smooth dashboard score.

## 5. Result C: a sophisticated model can become confidently wrong after a relationship reversal

Compare the n=12, tau=0.4, rho=0.6 cells:

| World | Unconditioned utility | Hard-cell utility | Joint-oracle utility |
|---|---:|---:|---:|
| Stable relationship | 0.192583 | 0.408056 | 0.418449 |
| Historical relationship reverses | 0.191211 | -0.320096 | -0.296222 |

The current-regime deviation changes sign in the adverse world while the historical sample still describes the old direction. The model's covariance algebra remains correct for that historical sample, but its extrapolation is wrong. More data about the old relationship cannot by itself restore the new one. The hard-cell analytical MSE becomes 4*tau^2+sigma^2/n rather than sigma^2/n.

These are separate invented worlds, not evidence that Mastermind can detect or predict such a switch. The experiment deliberately supplies no successful change detector, and no parameters were retuned to erase the loss.

**Design consequence:** qualify the economic mechanism, its age and its out-of-support behavior separately from sampling uncertainty. A rule that merely shrinks historical estimates is not proof of early adaptation. The existing model/evaluation owner needs structural-change and invalidation tests; this does not create a new shock classifier or prohibited rotation×cycle gate.

## 6. Result D: a near-certain mean is not a near-certain investment outcome

In the executed Gaussian example, P(conditional mean > 0) is about **99.9968%**, while P(next realized outcome > 0) is about **57.9162%** after adding the specified independent future noise. These are mathematical example values, not probabilities for any actual sector.

A UI or chat response that transfers the first number into “chance this trade wins” would be making a different claim. Probability of being top-three is different again because it depends on other groups' outcomes. [UNCERTAINTY_METHOD_REVIEW_R4.md](UNCERTAINTY_METHOD_REVIEW_R4.md) turns this into target-specific consumer requirements and reviews selective-calibration/delayed-feedback methods.

## 7. Fabric consultation and rigorous rejection of incorrect claims

One new independent algebra consultation ran through the normal paid Fabric route: `rotation-r4-20261017-c1-conditioning-math`, original root/parent `rotation-intelligence-census-20261016-sol-c1`. It had no repository, archive, network, source-effect or delegation permission. This was not a repeat of the failed R1 package review or the blocked R4 source inspection.

It returned terminal rc=0; retained response SHA-256 `020244a8f3c2061307a63ffb5a461153091f4de6be5da7510169a4d2b9e727ae`. The principal checked the result and **did not grant blanket acceptance**:

- Its posterior expression double-counted tau^2 after defining V_x to include it; its later eigenvalue expression was inconsistent with that formula. The implemented covariance and dense-inverse test use the correct noise covariance V.
- It incorrectly claimed equicorrelated joint shrinkage could reorder the flat-center top-three. The algebra and 1,000-fixture test disprove that claim.
- It introduced an independent future latent state but retained an incompatible old-posterior predictive mean/variance formula. The corrected stable-state example adds future innovation to posterior state variance; an independent state requires its own conditional distribution.
- The variance of a pairwise difference is symmetric in the two indices even with unequal variances; noisy extremes and selection bias should not be explained with a mathematically asymmetric difference-variance claim.
- Correct pooling break-even, common-versus-contrast shrinkage, reversal risk and the difference between selection and sizing were independently retained, with their assumptions.

The tests are not evidence of an independent final design review. No new worker remains running, no watcher was created, and no provider restriction was bypassed. The earlier source and review gates remain separate.

## 8. Concrete model and consumer requirements adopted for this supplement

1. Compare an unconditioned/pooled baseline with conditional challengers using matched information and explicit support. Known hyperparameters in a diagnostic cannot stand in for estimated real-world parameters.
2. Require distinct tests for prediction error, selected-group quality, calibrated uncertainty and actual policy value. A model must earn each claimed capability.
3. Include wrong economic priors and relationship reversals, not just higher Gaussian noise. Do not imply that confidence shrinkage detects a new regime.
4. Carry the precise probability target, horizon, cohort, source cutoff and uncertainty meaning into the existing forecast/consumer contract. No generic probability-of-success label from a mean-confidence number.
5. Treat new selective/conformal methods as version-bound research candidates with actual data assumptions and delayed-label geometry, not automatic guarantees or replacement error-budget systems.

These are evidence/acceptance requirements for the already proposed architecture. No source ranking permission, model promotion, new regime service or existing DNR reopening is implied.

## 9. Remaining frontier

The archive/consumer qualification is still the critical real-data dependency. This turn did not validate payload hashes, numerical session completeness, revisions, source-use mapping or the BIL gap. The explicitly blocked combined source-inspection action remains frozen; a permitted recovery requires actual changed authorization/capability evidence, not another identical request or a different worker.

The independent regime/uncertainty diagnostic is complete and published. Final package review and required CI acceptance remain separate; the prior provider403 has not been reclassified as approval. The mission's empirical and product outcomes remain incomplete. The compatible protected procedure pin and the same GitHub branch/PR are preserved.

Supporting M2 evidence: `/Volumes/Mastermind/research/rotation-intelligence-census-20261016-sol-c1/r4-conditioning/` contains exact published source, reference-test log, full output and verification JSON. The algebra return is retained in the parent evidence root. GitHub owns the published findings and complete compact grid; these local receipts are supporting evidence, not a new data or control plane.
