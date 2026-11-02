# 09 | Model architecture recommendation

## One evidence projection, separate estimands

A single 0–100 pivot score is the wrong abstraction. It cannot explain whether a stock has limited remaining downside, a likely near-term expansion, an expensive confirmation, little upside left, or insufficient source coverage. Use a typed state record with separately versioned measurements and, only after validation, separate probabilistic heads. [I01, I03]

The first model stack is intentionally small: deterministic source/causality validation; owner-supplied daily leader eligibility; a frozen completed-bar descriptor; strong primitive features; regularized statistical heads; and a thin accepted projection into Radar/Terminal. No end-to-end language model, per-ticker policy table or unconstrained sequence network is justified initially.

## Six heads, not six mandatory complex models

| Head | Initial estimator | Required output semantics |
|---|---|---|
| Downside | Regularized MAE/quantile regression and a fixed-threshold survival classifier | Unit, horizon, quantiles or typed UNESTIMATED; tail probability only with calibration |
| Launch | Ridge logistic reference; shallow-tree challenger; later discrete-time competing-risk model if earned | Upper-before-lower cumulative probability at registered horizons |
| False start | Reclaim-conditioned competing outcome/registered classifier | Failure definition, frozen invalidation and no-reclaim state |
| Confirmation cost | Empirical conditional distributions or regularized quantiles | Price cost, time cost, sample support and non-confirmation rate |
| Remaining opportunity | Conditional favorable-excursion quantiles and barrier probability | Not an oracle high or a naive ATR-extension truth |
| Economics | Paired policy evaluation, not an independent confidence score | Net common-budget utility, exposure, missed moves and tails |

Sharing inputs or an encoder does not make the heads statistically independent. The initial descriptive module emits these as UNESTIMATED or as direct observed measurements; it does not fill them with plausible numbers. Six output concepts do not require training six neural networks.

## Coherent probabilities

For a fixed origin, fixed barriers and supported observation path, cumulative probability of upper-first by 30/60/90/120 minutes should be nondecreasing. A later decision time, different reference entry or changed barrier defines a different conditional question and cannot be compared as if only the horizon changed.

A competing-risk model can encode launch, downside invalidation and no event, but a lower-first event must not be treated as harmless censoring. Genuine source loss can censor observation. They have different meanings and different likelihood contributions. Model coherence does not replace calibration evidence. [I08]

Use a separate reserved calibration block. For a public calibrated-probability claim, require reliability uncertainty that supports the chosen display precision and target scope. The LLR proposal of calibration-frozen bins, at least 400 resolved observations across 20 distinct days per proposed bin, and simultaneous ±5-percentage-point calibration-error bounds is an appropriate starting gate; it may yield no displayable bins. That is better than a falsely precise 83% probability. [I08]

## Conditional interactions worth testing

The most credible new relative claim is not “residual turns up.” It is an interaction between independently known leadership, a controlled common shock, relative resilience and a causal structural event. Test that interaction against all main effects and matched raw-history primitives. A significant residual feature without incremental interaction evidence does not establish the proposed mechanism.

Similarly, dynamic themes must add on a common recent/PIT cohort after industry context, not by replacing the universe. A higher timeframe must improve a forecast beyond a slower filter and its coverage selection. Fifteen-minute anticipation must pay for extra false starts. These are targeted additions, not a network asked to discover an unconstrained conjunction.

## Fixed multiscale North Star

The mature record should present a small fixed set of supported contexts and allow a regularized model to use the vector. Compare equal-weight and median summaries with the selector-free vector model. There is no requirement to label one timescale the stock's true clock.

A later Temporal Grain band can be joined as a versioned measurement if its owner has accepted it. Its fingerprint inputs must generalize across names; behavioral-neighbor pooling and bounded empirical-Bayes evidence must retain support and shrinkage. No ticker identity or outcomes-derived home rung enters as a hidden strategy key. [I15–I18]

## Stability, abstention and failure behavior

Abstain on unsupported identity/basis, incomplete bars, future-known memberships, insufficient ex-self support, unstable exposures, unavailable clock state or out-of-scope calibration. Retain the original reason rather than mapping all failures to a generic low-confidence score.

A missing optional theme feature can fall back to an accepted stable-group model only through an explicitly registered fallback with its own scope and evaluation. Silent zero-filling or post-hoc fallback to whichever model predicts a rally is prohibited.

Do not begin with automatic retraining, online strategy search, LLM explanations that originate trade claims, participant-intent inference, universal confidence fusion or new infrastructure. The minimum system should be removable without altering incumbent candidate selection, portfolio sizing or entry authority.
