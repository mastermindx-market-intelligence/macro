# Crypto science R6 — chronological probability and separate action utility

Date label: 2026-09-28 (the research programme's existing session date). Parent WS:CRYPTO-INTELLIGENCE / Macro draft PR8050; same operation crypto-vector-r2-20260926-sol-001. Baseline `3d656d97f8935bccac81299b786e54e3d9868de4`. Protected Mastermind `bf709270f29f5445288e8f453fe82f6c4dd389b4`, INDEX blob94d1af402598894372858793a5b1931019c5fa77, compatible1.0.1/bootstrap1; ACTIVE_EXECUTION, WEB_CEO_DELEGATION, CLOSEOUT loaded atomically. Chairman Continue supplies intent; principal judgment owns prediction/utility design. Existing M2 Studio Direct carrier and isolated sparse workspace preserved. No new runtime/collector/paid source/forecast owner or reviewer. Source work is research-only and existing tests/continuity; no production model/gate/UI changes or merge.

## Question and design choice

R4/R5 fixed technical checklists did not earn promotion. R6 asks whether a SMALL continuous price/regime model improves chronological probability forecasts over a past event-rate baseline, and whether adding the SAME unsigned participation measurement contributes after price information. Forecast scores and action economics are separate tests. No model outputs will be labeled calibrated or actionable until the corresponding evidence qualifies.

Alternatives considered: more binary confirmations (already nearly redundant in downside), a flexible tree/large interaction model (too many researcher degrees of freedom for these episodes), pooling spot and derivatives aggression (measurement mismatch). Selected: two fixed strongly regularized logistic models plus an expanding historical-rate baseline. No hyperparameter/lag/feature search, new package install or threshold optimization. SciPy/NumPy are available locally; sklearn is not, so the small specified likelihood is solved with existing scipy.optimize, not an invented learned-model framework.

## Signed-flow qualification, before any outcome modelling

Actual collector uses OKX `/api/v5/rubik/stat/taker-volume`, ccy=BTC, instType=CONTRACTS, period=1H. The official documentation read this turn confirms sell-then-buy array order and SPOT/CONTRACTS scope. It labels ts only as Timestamp; its aggregate response section does not establish absolute unit, contract-mixture weighting, bucket start/end, completion/publication latency or revision history. The separate instrument-specific endpoint supports explicit unit and instId; those semantics CANNOT be imputed to the existing aggregate file. Official document bytes SHA2568a08f29d3da3ad1ecec9a6a36704b09dc61834e6fb9116efb51a7bbf4ae8a02c; URL https://www.okx.com/docs-v5/en/ . A web render hit a content-size limit, so the same public documentation was read once via a bounded host HTTP GET; no market/account API was called.

Metadata-only inspection: 2,957 hourly rows from2026-05-26 to2026-09-26 13:00, 9 absent hourly timestamps, empty dataframe attrs, finite nonnegative volumes and no zero-total observed rows. Input SHA25690ad3d707191c43ca5478c84e4f245d536cb1c2962d72046b15ca6d71b9eb923. Count only complete windows and overlap with R5 parents; no return association or CVD-profit result is computed from this unqualified clock. It remains excluded from R6 predictors. A dimensionless buy-minus-sell share cancels a common unit but does NOT repair mixture, timestamp or publication ambiguity. Genuine signed derivatives flow is not observed spot absorption.

## Fixed population and targets

Reuse the EXACT R5/R4 source identities, 588D0 downside parents and59washout parents, dates, onset separation, execution delays1h(primary)/6h(sensitivity), cost0/10(primary)/25bp. No new event selection by outcomes.

Downside forecast is issued at the R5 landmark, after six completed hourly follow-up bars: anchor+7h. Outcome entry is issue+lag. Target y=1 only when the existing lower5% barrier occurs before upper3% over the remaining18h; y=0 for upper-first or neither; ambiguous/censored remains unavailable. Same original24h account endpoint. This is conditional continuation, not a pre-shock or market-wide crash probability.

Recovery readiness uses the first R5 hourly reclaim only. Upper5%-before-lower3% over168h, with original336h common-policy endpoint. No-entry parents are not negative forecasts. The 55 existing candidate times are already known to be fewer than the minimum80 fit observations below; therefore this dataset cannot provide an eligible R6 recovery learner. Report this eligibility restriction rather than fit a tiny attractive model. The next recovery model needs a different justified population or new independent data, not a post-result lowered minimum.

## Frozen continuous feature definitions

Inputs are Coinbase BTC-USD hourly OHLCV with whole-hour naive UTC bucket STARTS. All data through the last completed bar only. Require721 contiguous valid OHLC bars ending there, plus the specified prior/reference windows. No gap-fill and no price splice. Nonfinite/nonpositive OHLC, impossible extrema and invalid chronology -> unknown; finite zero volume is observed, but nonpositive reference median -> volume ratio unknown.

Let a=parent hour, s=a+6h for downside, last completed bar at issue-1h. For recovery s is R5 first reclaim hour. Sigma is sample stdev of72 hourly log-close returns over73 bars ending a-1h (downside), or s-3h (recovery). Sigma must be positive. Six PRICE features:
1. log(last close/reference close)/(sigma*sqrt(6)), reference close at a for downside, s-6h for recovery.
2. log(last close/reference structure high-or-low)/(sigma*sqrt(6)); structure is original pre-a72h minimum low for downside, prior-s six-hour maximum high for recovery.
3. log(last3 low/previous3 low)/(sigma*sqrt(3)), using the final six completed bars.
4. log(last close/close24h earlier)/(sigma*sqrt(24)).
5. log(last close/close720h earlier)/(sigma*sqrt(720)), a continuous slow-trend condition rather than a hindsight regime label.
6. log(sigma), a volatility-state measurement.
PRICE_VOLUME adds one field: log1p(R5 volume ratio), including a valid zero. This is total unsigned spot participation, not signed buying. No interaction term, learned regime label, future smoothing or indicator proliferation.

M0=Laplace-smoothed expanding prevalence (positives+1)/(n+2). M1=PRICE logistic. M2=PRICE_VOLUME logistic. All three fit/evaluate on the SAME complete price+volume cohort for paired claims; excluded volume observations remain reported, not scored zero. No market data is scanned before this protocol's commit beyond already reported R4/R5 and metadata.

## Chronological fitting and forecast scoring

Refit at each calendar-quarter start from2018-01-01 through2026-07-01; predict subsequent issue times before next quarter. Training uses only previous observations whose COMPLETE outcome/common-policy end PLUS24h downside embargo (14d recovery) is strictly before fit time. End-of-quarter overlap remains in the issued quarter's evaluation only after outcome maturity; no quarter-outcome information enters fitting. Require n>=80, at least15positive and15negative labels. Insufficient history -> no model/forecast/action, NOT zero probability or cash. Retain every excluded/pending parent with reason.

Fit means/stdevs on the training set only, population ddof0; zero-variance scale becomes1. Standardize training/test with those training parameters and clip z to[-5,5]. Objective is mean binary log loss +0.05/2 times squared slope norm; intercept unpenalized. Fixed L-BFGS-B, zero initial coefficients except prevalence logit intercept, maxiter2000, gtol1e-9, ftol1e-12. No hyperparameter CV/selection and no post-hoc probability calibration fitted on held-out results. Optimizer failure or nonfinite solution -> explicit model unavailable, do not use another unregistered solver/model. Coefficients/scalers/fit counts/last training end saved with each fit. No class balancing that distorts empirical priors.

Primary forecast comparisons: paired Brier M1-M0 and M2-M1, with log loss and AUC alongside. Brier is a proper overall probability score, not pure calibration (official sklearn calibration documentation reviewed: https://scikit-learn.org/stable/modules/calibration.html). Report reliability bins fixed BEFORE results at[0,.1,.2,.3,.5,.75,1], each count/mean predicted/observed fraction, and mean probability versus observed prevalence. No declaring calibration from AUC or a lower Brier alone. Report all chronologically issued predictions, out-of-training 2018–2019/2020–2023/reused2024+ and whole eligible history; none is a fresh research-naive holdout. Block95 intervals use existing90-day calendar-block resampling seed20260928/1000draws. Leave-one-year-out means are sensitivity, not independent replication.

## Separate action-utility diagnostic

The binary event target is not a return or a cash instruction. For each quarter/lag/cost, use only the same eligible TRAINING rows with known account comparisons to estimate cash-minus-incumbent mean gain in y=0 andy=1. Shrink each class mean toward the same training overall mean using10pseudo-observations (fixed). Forecast expected marginal gain = p*mu1+(1-p)*mu0. Choose cash only if expected gain>0, otherwise keep incumbent. Require at least15complete payoff cases of each class; no new threshold search or test-outcome choice. This coarse mapping is itself an explicit economic hypothesis, not assumed correct.

Use R5's all-parent delayed cash and incumbent return accounts at the common24h endpoint. Until the six-hour action landmark all policies follow incumbent; no earlier losses are credited. Terminal target restoration/holdings drift/0,10,25bp assumptions remain inherited. Compare M0/M1/M2 policies against incumbent, R5 PRICE and R5PRICE_VOLUME on identical forecast-evaluable parents. Report cash fraction, actual mean marginal gain, expected gain reliability, positive/negative cash-event contribution, and uncertainty. No leverage, shorting or personal portfolio advice. A model can improve forecast scoring yet worsen this account policy; report both rather than treat a forecast metric as promotion.

## Implementation, tests and evidence

Scoped new helper research/crypto_science/r6_probability_study.py; extend existing tests/test_btc_impulse_falsifier.py, already in existing CI. Derived results under research/crypto_science/r6/; current Agent OS workstream/decision only. Do not change prior R1–R5 results, productionengine/config, collector, gate, shared UI, running worker or current branch ownership.

1. RED tests for feature-prefix invariance and unknown volume; training-only scaler; chronology/maturity/embargo; fixed ridge probability; insufficient class history; test-label/future-row non-influence; payoff calibration train-only; finite proper scores. Implement minimal helpers, GREEN existing research tests and commit before market execution.
2. Build metadata/source qualification receipt and all event features; reuse R5labels/accounts and R4incumbent only with all inherited hash checks. Execute frozen quarter learner once; preserve optimizer/status errors without outcome-driven tuning.
3. Independently express likelihood gradient/normalization, verify all saved training dates and predictions/scalers, recheck forecast scores and class-payoff/action account arithmetic from CSV. This is same-session numerical verification, not independent-person/model review.
4. Run existing combined Crypto/Vector/science suite and source claim/compiler/diff checks. Preserve exact process handles/logs, version/source/input hashes and all negative results. Commit/push on same carrier after local/remote-head fences; read back current results and cumulative frontier.

Review focus: a current feature requiring an unfinished bar; fitting scalers on test rows; future outcome leaking into train membership or class payoffs; missing flow reclassified asneutral; in-sample threshold selection; mismatched paired cohorts; low event base-rate masquerading as accuracy; same-event cost/lag repeats masquerading as independent sample; new schema drift invalidating prior evidence. No launch of collector/forward daemon is implied.

Promotion: NOT_ELIGIBLE from this retrospective study alone. Better score must survive paired uncertainty, chronological subperiods, coherent calibration and independently reviewed real-timestamp/execution/forward evidence. Parent mission incomplete. At R6 start no learner outputs or new outcome associations have been examined. Prior R5facts remain public-to-this-researcher, so this protocol is not an untouched final holdout.
