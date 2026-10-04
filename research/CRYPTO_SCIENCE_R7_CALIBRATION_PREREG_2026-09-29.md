# Crypto science R7 — frozen calibration and protection-utility comparison

Date 2026-09-29. Existing WS:CRYPTO-INTELLIGENCE, operation crypto-vector-r2-20260926-sol-001, Macro draft PR8050. Research only. Baseline b445029abd6c84a66cadc572929e0beb702be4b7 (R6 already completed). Protected Mastermind f91847688f8126511c854ab253cd5c3cb67baa4e; INDEX94d1af402598894372858793a5b1931019c5fa77; compatible1.0.1/bootstrap1; COLD_START/RECONCILE_STATE/ACTIVE_EXECUTION/WEB_CEO_DELEGATION/CLOSEOUT read at same pin.

## Recovery and accepted intent

The Chairman reports network restoration and directs continuation of the ongoing Crypto scientific mission. Same M2 Studio Direct workspace/carrier is clean at the exact GitHub R6 head; the recorded R6 result is complete and published, not pending. No R7 file or active scientific process exists at recovery. Existing old loopback UI fixture servers are not scientific workers and are not disturbed. CI36514642263 and fences36514642065 succeeded for R6. The draft PR is currently mergeable=false; no merge/rebase/custody displacement occurs here. The previous chat failure does not imply R6 was lost or should be repeated.

Current principal duty: PRINCIPAL_JUDGMENT for calibration evidence, loss-function choice and honest action interpretation. Routine research implementation stays with the same scoped carrier because it is tightly coupled to those judgments; no independent reviewer/worker or new state owner is claimed. The external-review gate remains before any promotion. Current assignment permits this reversible research cycle without another administrative approval. No user risk tolerance or live model policy is inferred from the loss function below.

## Questions, scope and non-goals

R6 reported excessive mean probabilities, modest chronological proper-score gains over a potentially stale expanding prior, and no primary mean-wealth benefit from a coarse cash rule. R7 asks:
1. Does price information still improve probability quality over a recent-rate comparator on the SAME eligible episodes?
2. Can training-only intercept recalibration correct probability level without pretending to create new within-quarter ranking information?
3. Under one explicit marked-drawdown penalty and expected opportunity-cost cap, does protective action improve that declared utility relative to incumbent and a frequency-matched diagnostic?

No new features, base-learner refit, parent/label/window change, new event population, provider call, flow splice, threshold search, model promotion or live allocation. R6 remains unchanged. Signed-flow is still excluded pending units/mix/time/publication qualification. Recovery is NOT forced into a fit: its R6 population did not meet the frozen minimum and this study is downside-only. All historical periods have already been examined. Chronological replay here is not untouched research holdout or live-issued forecasts.

## Inputs and quarterly time fences

Reuse R6 predictions.csv (p0/p1/p2), labelled_records.csv, results.json and existing R5/R4 account/source evidence. No recalculation of base coefficients. The existing hourly BTC and immutable corrected-incumbent replay are used only to reconstruct the additional delayed-cash drawdown/turnover measurements not retained in R5 CSV. Check returns against R5 to avoid drifting the account convention. All inherited input/gate and prior evidence/source hashes must match before/after.

Each quarter from2018-01-01 through2026-07-01 fits using only earlier R6 OUT-OF-FITTING-SAMPLE predictions with finite p1,p2, binary mature y, issue<quarter, and entire account/target end+24h strictly before quarter. Do not use fitted predictions on a base learner's own training sample to train the calibrator. The R6 records are retrospective, not evidence of contemporaneous publication. Calibration needs >=80 such rows, >=15 of each class, and weighted effective N>=40. Below gate: unavailable for ALL new comparator/calibration methods; do not reduce the minimum. Old raw predictions are retained but paired scoring of new-vs-old uses identical eligible rows.

Weights w=2**(-age_in_days/365), age measured from issue to fit-quarter, no normalization of input observations before age calculation. These constants are fixed before R7 outcomes. Same cohort/weights for the recent-rate baseline and calibration. No half-life/window grid. Scoring is UNWEIGHTED over future eligible observations.

## Frozen forecasts

- R6_RATE, RAW_PRICE, RAW_VOLUME: original p0,p1,p2, unchanged.
- OOT_RATE: (positive_count+1)/(n+2) on the same calibration cohort.
- RECENT_RATE: (sum(w*y)+1)/(sum(w)+2), a recency-weighted smoothed rate with no episode features.
- CAL_PRICE, CAL_VOLUME: sigmoid(logit(clipped original p)+b). Slope fixed1. Clip original p to[1e-6,1-1e-6]. Fit ONLY b by minimizing weighted mean binary log loss plus 0.01*b*b/2. Solve the strictly monotone derivative root on[-50,50] using existing SciPy brentq, tolerance1e-12. Failure is unavailable, not fallback. This monotone shift preserves within-quarter ranking; cross-quarter AUC may change.

Co-primary forecast contrasts, primary1h execution assumption: CAL_PRICE minus RECENT_RATE Brier, and CAL_PRICE minus RAW_PRICE Brier. Negative is better. Secondary: CAL_VOLUME minus CAL_PRICE and RAW_PRICE minus RECENT_RATE. Report all methods Brier/logloss/AUC/mean probability/event frequency, fixed bins[0,.1,.2,.3,.5,.75,1], sample/exclusion counts. Binned decomposition includes reliability, resolution, uncertainty AND the residual between actual continuous Brier and binned-mean Brier; never assert an exact three-term identity for unbinned scores without that residual.

Periods: all eligible2018+,2018–2019,2020–2023,already-used2024+. Retain1h primary/6h sensitivity without choosing the favorable lag. Paired uncertainty: same R4 calendar90-day block resampling,1000draws,seed20260928; descriptive not multiplicity-adjusted proof. Preserve leave-one-year-out results; no redefining periods after results.

## Separately frozen protective objective

Accounts are the SAME original24h downside parents and delayed six-hour landmark action used in R5/R6. Incumbent is followed until that action. Candidate either continues it or stays cash after the action until the original endpoint and restores the target. One-way costs0/10/25bp,1h primary/6h sensitivity, original idealized recorded hourly-open prices and no repaired/missing bars. These are reference executions, not achievable fills. Preserve missing account paths rather than zero-fill.

Reconstruct both incumbent and delayed-cash returns R, negative maximum marked drawdown D, and turnover T with the existing account recurrence, checking R against R5. Set L=max(-D,0). Research loss allowance B=.05 (5% marked drawdown from original parent-account origin). Primary utility U=R-max(L-B,0). Sensitivities lambda=0 and2 in U=R-lambda*max(L-B,0), all retained. This is a declared experimental loss preference, not a guarantee that losses stay <=5% or a risk budget approved for users. Both paths share pre-action losses; none is credited to foresight. Costs already enter R and drawdown: do not charge turnover twice.

For each quarter/cost/lambda, use the same eligible earlier OOT records, weights and mature account outcomes to estimate class-conditional DELTA U (cash minus incumbent) and DELTA R. Within each class, shrink weighted gain sum toward weighted overall mean by10pseudo-observations; require15raw account observations per class. At a candidate time, probability p yields expected gains p*mu1+(1-p)*mu0. Select cash only when expected DELTA U>0 AND expected DELTA R>=-0.002 (20bp allowed expected event-equity sacrifice). Both are frozen assumptions, not empirically guaranteed bounds. No action needs current y; issue action before looking at its eventual label/realized account. Missing future labels may prevent scoring but cannot retrospectively change the action.

Report average marginal return, marginal utility, change in excess drawdown, turnover, actual cash selections, how many selected accounts changed economically, costed avoided-loss and missed-rebound sums, and instances where actual loss exceeds the allowance. Utility is per-parent, not annualized portfolio utility. Distinguish raw/calibrated forecasts and RECENT_RATE; action mapping is not a theorem that event probability should set size.

Selection diagnostic: within each test quarter/lag/cost/lambda/method, q=number of cash selections/number of usable candidate accounts. Compare model marginal R/U with q times the per-parent cash-minus-incumbent R/U, averaging over the same parents. This is expected uniform-random assignment at the same observed quarterly action frequency, not an executable hindsight policy, not equal risk, and not exact notional-exposure matching. Label it FREQUENCY_MATCHED_DIAGNOSTIC. It asks whether selection adds value beyond how often the policy avoids exposure. Do not reinterpret zero drawdown among cash accounts as bottom/exit accuracy.

## Implementation, tests and independent arithmetic

One research module research/crypto_science/r7_calibration_study.py; derived outputs in existing research/crypto_science/r7/. Add tests to existing tests/test_btc_impulse_falsifier.py, already enrolled in CI. No new runner/dependency, engine/config/collector/gate/template changes. Existing Agent OS decision/workstream records hold cumulative frontier.

Ordered work: (1) commit this protocol before any R7 fit/payoff results; (2) RED tests for time fences, min counts/ESS, intercept gradient and monotonicity, known vs missing probabilities, residual decomposition, risk/cost units and future-label-independent decisions; (3) implement and GREEN, commit candidate before study; (4) execute fixed study once; (5) independent numerical expression verifies training membership/weights, offset root and forecasts, all new account/drawdown arithmetic, mappings, action decisions, score/reliability/decomposition/utility/frequency-match summaries and block intervals; (6) broad existing Crypto/Vector/science tests, claim checker, compile and diff checks; (7) interpret all results and record no-promotion or exact qualification without changing experiment.

Independent arithmetic means different numerical expression in this same session, NOT an independent researcher. Review focus: embargo equality edges; empty/one-class/low-effective samples; no current outcome input to actions; cash already held by incumbent; prior-drawdown carry; hidden mismatched comparator cohorts; granularity and units of probability/Brier/percentage points; missing periods retained; likelihood-score improvement versus actual tail-risk utility. No live confidence label or strategy promotion from this one retrospective comparison.

Public methodology: scikit-learn official calibration guide https://scikit-learn.org/stable/modules/calibration.html (proper score combines calibration/discrimination; independent calibration records); SciPy brentq https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.brentq.html (bracketed scalar solver). Documentation supports method semantics, not efficacy of this experiment. No market/account endpoint or paid provider activated.
