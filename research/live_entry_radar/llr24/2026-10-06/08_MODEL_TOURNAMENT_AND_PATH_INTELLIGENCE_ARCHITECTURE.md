# 08 — Model tournament and path intelligence

**Central architecture:** a small collection of calibrated, explicitly scoped forecast heads conditioned on the same causal state, attached to existing Radar episodes only through an accepted owner contract. No composite “buy score” and no model-owned candidate lifecycle.

## 1. Forecast heads

| Head | Target | Baseline | Operational output |
|---|---|---|---|
| Location | Near finalized economic low / forward-available low within a fixed tolerance | Session × elapsed-time × liquidity base rate, then price-distance model | Probability, precise price basis and horizon; observed-distance descriptor remains separate |
| Survival | No material breach of fixed observed reference through H | Empirical survival curve by supported cohort | Monotone survival at 5/15/30/60/120 minutes and supported segment/day ends |
| First-event risk | New low versus confirmed reclaim versus expiry | Competing discrete-time hazards | Event incidence and “no first event yet”; never substitute for all-path survival |
| Path | Executable or price-only MAE/MFE, time to low/reclaim/target | Empirical conditional quantiles and simple quantile regression | Calibrated quantiles/ranges, probability of adverse barrier before favorable barrier |
| Entry economics | Buy now versus fixed wait, reclaim wait or no-entry at a common terminal | Fixed policies on same candidate set | Net cost/risk differences, fill coverage and missed opportunity; consumer-specific authority remains separate |
| Position health / exit | Bid-side giveback, failed continuation and invalidation path | Fixed causal exit/invalidation policies | Position-relative risk and context; separate labels and validation |

Heads may share features, but each has its own target, horizon, cohort, evidence mode, calibration, missingness and disposition. An unavailable microstructure head cannot be rendered as a neutral value; a qualified price head can remain available with its limitation shown.

## 2. Ordered tournament

**B0 — irreducible simple baselines.** Compare unconditional time-of-day/session rates; “no new low for N completed bars”; normalized distance from the observed low; elapsed time since that low; fixed wait; and no-entry. Add the incumbent Radar/TOI species states as separate existing-context comparators, not as evidence of model skill. These baselines make confirmation delay and ordinary price location visible.

**B1 — regularized interpretable models.** Logistic models for fixed-horizon binary targets and multinomial/discrete hazard models for time/event targets. Use a compact price path, volatility and time model before any indicator family. Coefficients are associations conditional on the chosen covariates, not causal market explanations. Penalization and all transformations are fit inside training folds.

**B2 — shallow nonlinear challengers.** Shallow gradient boosting, then one categorical-capable implementation if needed for session/security metadata. Depth, trees, learning rate, leaves and feature count have a small frozen search budget. Nonlinearity is admitted only on incremental out-of-sample scoring and practical benefit, not a better development chart.

**C1 — survival and multistate challengers.** Compare discrete cause-specific hazards, a suitable cumulative-incidence model and a multistate formulation only where the distinction changes a product question. Do not assume proportional hazards without checking. Repeated landmarks from the same episode remain dependent and are grouped in evaluation.

**C2 — sequence models.** A compact temporal convolution/recurrent model can compete after sufficient continuous qualified history exists. Compare to lag-feature boosting using the same information, observations, labels, latency, missingness and trial budget. An event sequence and a minute sequence are different sampling models; record event-count and wall-clock horizons.

**C3 — transformer / multimodal depth model.** Deferred until C2 leaves a reproducible material residual. DeepLOB and queue-forecasting results motivate a research direction, not transfer of next-tick performance to 30-minute low survival. A larger architecture does not justify collecting full-market L3. [M10; L07]

**Complexity gate:** retain the simplest model within the preregistered practical-equivalence band of the best eligible model. Report inference latency, memory, missing-feature coverage, training variability and source cost alongside statistical scores. A marginal log-loss gain that loses coverage, adds seconds of latency or fails economic gates does not justify escalation.

## 3. Probability coherence

For discrete intervals j and stochastic first-event types k (new low, confirmed reclaim), define hazards λ(k,j) conditional on no earlier first event. Ensure nonnegative hazards and total hazard no greater than one. Then S(j) = product over intervals through j of `(1 − sum_k λ(k,j))`, and F_k(J) = sum through J of `S(j−1) λ(k,j)`. Cause incidences plus no-event probability sum to one. Administrative expiry assigns the remaining S(J) to endpoint bookkeeping; it is not a freely learned stochastic hazard. Source loss is censoring, not expiry.

These equations describe first events only. A reclaim can be followed by a new low. The all-path survival head therefore needs its own label/hazard or a multistate continuation after reclaim. Its probabilities must not be derived from an absorbing reclaim competing-risk model. A model test must include this counterexample explicitly.

Quantile outputs must be ordered and have units/reference prices. Calibration must be checked separately for each horizon and supported session. Do not subtract independently fitted MAE and MFE quantiles and call the result a joint path distribution. If a consumer needs joint barrier probabilities, train/evaluate that joint target or use a validated coherent path simulation.

## 4. Global model versus session specialists

Start with a global model carrying continuous clock features, session identity, liquidity, spread, gap, volatility and supported catalyst/context flags. Let coefficients/interactions learn simple differences with regularization. Overnight support is expected to be sparse relative to RTH; hierarchical shrinkage prevents small overnight buckets from producing extreme probabilities.

A specialist is justified only when a preregistered interaction is stable across folds, the session has enough independent event and non-event support, and it improves calibration and economics after its increased complexity is charged. A mixture-of-experts router must use causal features and return unavailable for unsupported conditions; it must not choose retrospectively whichever expert performed best on a ticker. The existing outcome-audition kill directly rules out that shortcut. [P11]

Propose separate eligibility for RTH, premarket, after-hours and overnight before separate weights. A global model trained mostly on RTH is not a qualified overnight model merely because it accepts a session flag. Future exchange-hour changes create a new clock/liquidity era and require prospective transfer checks.

## 5. Calibration and uncertainty

Use held-out chronological calibration after model/feature selection. Compare logistic recalibration and, only with sufficient support, a monotone nonparametric mapping. Calibration data cannot double as the final model-selection holdout. Report Brier/log score against the cohort base rate, calibration intercept/slope, reliability bins, sample/event counts and cluster-aware uncertainty.

An interval on estimated probability measures parameter/calibration uncertainty; a predicted MAE interval measures outcome variability. They are different. A model can be uncertain about a wide outcome distribution; neither quantity should be relabelled simply “confidence.” Conformal intervals may be a challenger, but ordinary exchangeability coverage is not automatic under financial dependence, regime change or selected cohorts. [M05; M04]

Glance-tier probability display requires: a precise target/horizon; supported source/clock; sufficient local evidence; and a successful external calibration gate. Otherwise show “not yet estimated,” “insufficient comparable history,” or a validated ordinal band if that band has its own held-out evidence. Do not present a model's raw output as a probability merely because its activation is a sigmoid.

## 6. Forecast artifact and serving boundary

Model artifacts should be content-addressed under the incumbent experiment/evidence owner, with training-data manifest, feature graph/version, label/clock version, splits, trial IDs, cost conventions, calibration map, support envelope and promotion decision. Register the family through Setup Species and the existing trial ledger; use existing claim/outcome ledgers. This file creates no new registry.

Research inference is initially offline. Later prospective inference consumes the same feature implementation and produces immutable snapshots before outcomes. A producer may compute expensive features outside the critical Radar pass and attach a completed, fresh, version-matched result through an approved projection contract. It must never delay or bypass canonical episode processing to hide a latency failure.

Rollback means stop publishing the optional admitted annotation and retain prior predictions/evidence; Radar continues under its existing contract. Model replacement is a new version with a prospective boundary, not silent recalibration of history. Automatic retraining/promotion is outside this commission.

## 7. Immediate tournament specification

The proposed first target is chapter06's fully specified `PRICE_L30M_30M_v1`, accompanied by reference-low distance and chapter09's fixed B0 base rate. It becomes admissible only after source/protocol acceptance. It is operationally simpler to label than a whole-day buyer-executable low, but its predictability is **unknown**. Start with B0 and B1. Execute the economic comparison only on quote-qualified observations under its separate label. RTH with a complete 30-minute lookback and outcome is the first proof domain; opening/closing transitions, overnight and other horizons remain distinct later tasks. This avoids turning a convenient available label into a stronger execution claim.
