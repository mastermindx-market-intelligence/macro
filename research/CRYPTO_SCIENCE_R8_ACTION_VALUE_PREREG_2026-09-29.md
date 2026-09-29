# Crypto science R8 — when protection is actionable, and direct action-value modelling

Date2026-09-29. Existing WS:CRYPTO-INTELLIGENCE, operation crypto-vector-r2-20260926-sol-001, Macro draft PR8050. Baseline4409729ed99f62e0f2127798ffc234953fb8f0e9. Current protected Mastermind f91847688f8126511c854ab253cd5c3cb67baa4e; INDEX94d1af402598894372858793a5b1931019c5fa77; compatible1.0.1/bootstrap1. Required cold-start/execution/delegation/closeout companions loaded from same pin. Current Chairman Continue supplies assignment. Direct duty PRINCIPAL_JUDGMENT: action timing, estimands and loss semantics are consequential scientific choices. No independent review claimed, no new runtime/provider/collector or live allocation authority.

Recovery: local/remote head match, clean incumbent M2 Studio Direct worktree, no R8 or active scientific process. R7 exact CI36530173125/fences36530172600 succeeded. The draft PR is currently mergeable=false; source research does not merge/rebase/displace a writer. Existing review/production gates remain. Signed flow remains excluded for prior source-contract reasons; recovery fit population remains too small. Prior R1-R7 studies are not repeated or overwritten.

## 1. Frozen question and why it differs from R7

R7 calibrated a binary continuation target, then converted probabilities into protection decisions through class-average payoffs. R8 asks directly how much return and drawdown damage can still be avoided at the earliest observable breakdown versus six hours later, and whether continuous measurements can predict THAT marginal economic value. No more calibration-window tuning or barrier-probability threshold search.

Two linked deliverables: A, decision-opportunity anatomy with explicit hindsight bounds and missed rebound costs; B, chronological prediction of cash-minus-incumbent return and excess-drawdown reduction at each fixed decision time. Both are research, not deployment. A positive diagnostic upper bound is not an achievable strategy. A negative fitted result does not prove no one could forecast the market.

## 2. Parent population and action timing

Use exactly the588existing R4/R5 D0 parent events. D0 is a completed hourly close below the previous72hour low, with valid complete inputs and the incumbent24hour onset separation. Do not reselect parents based on later deterioration, fitted forecast or realized severity. Freshly reproduce parent dates only as an identity check against frozen artifacts.

Define landmark k in{0,6} completed hours after the breakdown candle. Anchor a is the original candle START. Feature availability/decision issue=a+(1+k)hours. Action reference=issue+lag, lag1h primary/6h sensitivity. Common account origin=a+(1+lag)hours and terminal=a+(25+lag)hours, irrespective of k. At k0 the policy may act at origin; at k6 it follows incumbent for the first6hours. Both restore the incumbent target at the SAME terminal timestamp. This controls the opportunity window and avoids giving the delayed policy extra future days.

This independently specifies an earlier decision POINT on the same observable parent cohort, not a newly independent sample or a pre-shock forecast. Selecting the initial breakdown inherently conditions on damage already underway. Later price/feature completeness must not gate issuance of an earlier model. Pair only at evaluation when both paths are observable; disclose the resulting intersection rather than silently aligning coverage.

## 3. Input/data/market assumptions

Use unchanged R7 inherited input and gate hashes, corrected R4 incumbent_replay_targets.csv, existing Coinbase hourly OHLC, R5 parent/account records. No provider market/API/account call, source splice, history repair, model/config/gate/template change. Publish derived diagnostics only, no raw-parquet/price-store or fonts. Original research artifacts remain byte-identical. All history has been inspected before; chronological OUT-OF-TRAINING tests are not untouched research holdouts or live-issued forecasts.

Maintain R4 complete hourly window checks, invalid/missing price/target abstention, lagged daily target timing, drift-to-target trade convention and0/10/25basis-point one-way costs. Costs are proportional to target turnover under existing accounting, not a complete market-impact model. Hourly opens are idealized reference executions; hourly marks miss intrahour drawdowns and do not certify order execution during a crash.

## 4. Opportunity anatomy, fixed before outcomes

For every parent/lag/cost/k, compare (i) incumbent throughout and (ii) incumbent until action, then cash until common terminal with target restored. Record return R, maximum marked drawdown D<=0, turnover, actual incumbent drifted exposure immediately BEFORE the action, and incumbent mark/return/drawdown already experienced from the common origin to that moment. Do not count the candidate's action fee as a pre-action loss. Include last24h BTC return known at issue separately from event-account loss; do not sum those different bases.

At each fixed action, measure unlevered price worst/favorable excursion from action open through terminal. Record whether a5% account drawdown was already experienced BEFORE action and how much excess drawdown can actually be reduced, using the existing R7 allowanceB=.05. No ratios that silently add overlapping prefix and suffix drawdowns into total drawdown. A highwater from before action persists in the full account.

Define dr=R_cash-R_inc; dx=max(-D_inc-.05,0)-max(-D_cash-.05,0). Define du(lambda)=dr+lambda*dx with lambda1primary and0/2sensitivities. Report mean/median, positive/negative/zero counts, cash benefit and missed-rebound sums, tail exceedance counts, exposed versus already-cash cases, event-period and leave-year-out diagnostics. Paired k0-minus-k6 dr and du measure a FIXED cash switch at each landmark, not the causal value of new information.

Hindsight diagnostic: max(dr,0) and max(du,0) are per-event payoff of a clairvoyant cash-or-incumbent choice at THAT fixed time; they are unattainable upper envelopes, not forecast or PnL claims. Compare envelopes k0 versus k6 on identical complete parents. Do not optimize timing over arbitrary hours, entry/exit levels or choose a future local extreme.

## 5. Fixed observable features and regressors

For each k and lag, use only hourly bars through s=a+k, available at s+1h. Require721contiguous valid closes/OHLC from s-720h through s; no filling or alternate feed. Compute sigma=sample std of72log returns over73hourly closes ending s-1h; require finite>0. Feature vector:
1.log(close_s/close_s-1)/sigma;
2.log(close_s/close_s-6)/(sigma*sqrt6);
3.log(close_s/close_s-24)/(sigma*sqrt24);
4.log(close_s/close_s-720)/(sigma*sqrt720);
5.log(close_s/min(low_s-72..s-1))/(sigma*sqrt6);
6.log(min(low_last3)/min(low_previous3))/(sigma*sqrt3);
7.log(sigma);
8.the existing incumbent TARGET available at issue according to the same lagged daily-availability convention.

No feature uses price at delayed action or a future target, forward outcome or future six-hour completeness. Features are transformations of price plus known incumbent state, not independent causal witnesses. Actual drifted action exposure is DIAGNOSTIC/OUTCOME, not a predictor. No volume or signed-flow variable is added: this batch tests aligning the target and action time, not another unqualified data source.

Quarterly expanding training begins2018-01-01 through2026-07-01. Train each k/lag/cost only on its own prior rows with finite features/dr/dx and full account end+24h STRICTLY before quarter; issue also<quarter. Minimum80examples plus15positive and15negative dr observations (threshold +/-1e-12), retaining zero-gain cases. Insufficient support => unavailable, do not reduce floors. Training cohorts may differ by landmark or cost; record all memberships and use paired evaluation to compare candidates.

M0=two training means of dr,dx, no feature conditioning. M1=fixed multi-output ridge regression of dr,dx on the eight features. Standardize features with TRAINING means and population std; constant std->1; clip to+/-5standard deviations at train/test. Solve mean squared loss + .05 times squared slope norm; unpenalized intercept. No y winsorization, label selection, weighting/half-life or hyperparameter grid. Closed-form regularized normal equations using existing NumPy; independent augmented-least-squares verification. If the numeric solve is invalid/singular, withhold rather than change penalty.

Models estimate marginal RETURN and excess-drawdown reduction, NOT probabilities. No percentages of crash confidence. Prediction quality: MSE and MAE for each target versus same-training M0, signed bias, model predictions/observed means. OOS selection: predict_du=pred_dr+lambda*pred_dx. Select cash iff predict_du>0 AND pred_dr>=-.002, preserving R7's expected20bp sacrifice floor. The allowance and floor remain research preferences, not accepted user risk limits. Missing eventual account does not stop recording a decision from available features; only scoring is unavailable.

## 6. Evaluation and nonselection constraints

Primary comparisons1h lag/10bp cost/lambda1: M1-minus-M0 actual marginal utility at each landmark; M1k0-minus-M1k6 on the SAME predicted/complete parents; M1 versus incumbent net return, drawdown/turnover and missed-rebound loss. Report original per-landmark coverage and paired intersection. Also report unconditioned cash and hindsight envelopes separately. Do not rank/test-select the best cost, lag, lambda or period.

Periods: full2016+,2016-2019,2020-2023,already-used2024+. Model OOS starts2018and exact support may begin later. Include no-feature/no-fit/no-account and no-action cases. Actual utility scoring is per-parent not annualized/non-overlapping portfolio wealth. Forecast MSE requires finite future targets but issuance does not. All cost/lag/lambda sensitivities, year counts and leave-one-year-out means retained.

Use existing R4 90-calendar-day block bootstrap,1000draws,seed20260928,2.5/97.5percentiles for paired economic means. This is descriptive and not multiplicity-adjusted significance. Same-frequency diagnostic within quarter/method/k/lag/cost/lambda compares selection with expected uniform-random selection at identical frequency; it is retrospective and neither executable nor exactly risk/notional matched. No claim of preserved policy alpha merely because it beats a benchmark with more exposure.

## 7. Implementation and verification plan

Scoped files: new research/crypto_science/r8_action_value_study.py; outputs within existing research/crypto_science/r8/; appended tests in existing tests/test_btc_impulse_falsifier.py; existing Agent OS cumulative decision/workstream updates. No production change/parallel control plane/new CI job/dependency.

Ordered tasks: commit this preregistration before calculations; RED tests for prefix-stable features/unknown handling, pre-action mark boundaries and unchanged incumbent input, ridge training-only scaling/normal-equation residuals, future-target immunity, minimum support, direct dr/dx decision semantics; implement then GREEN and commit source before study. Execute once with hash fences, no blind overwrite. Independently express cash/coin inventory accounting including highwater and pre-action state, features/time eligibility, augmented least-squares fit, all predictions/decisions and summary/uncertainty arithmetic. Run full existing Crypto/Vector/science pack and source-claim/syntax/diff checks. Preserve any failed/interrupted result before a permitted technical repair; never overwrite evidence to manufacture a clean run.

Independent arithmetic is by this session, not independent scientific/code review. External review and actual forward/source-time/live proof remain before promotion. R8 is completed only when decision-ready evidence answers whether the studied timing/value targets improve upon the failed R6/R7 path, with uncertainty, false exits and data limitations explicit.

Method references inspected: official scikit-learn Ridge objective https://scikit-learn.org/1.8/modules/generated/sklearn.linear_model.Ridge.html and NumPy solve https://numpy.org/doc/stable/reference/generated/numpy.linalg.solve . Our explicit mean-loss penalty corresponds to total-loss alpha=.05*n; no package default is silently substituted. Docs support numerical semantics, not empirical efficacy.
