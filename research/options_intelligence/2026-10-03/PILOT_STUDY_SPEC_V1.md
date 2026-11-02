# Six-pilot empirical study specification v1

**Status: PRINCIPAL_PROPOSAL — 2026-10-03.** All numeric design choices below are proposals for principal adjudication, not validated optima or assertions of available data/power. This is a draft, executable research contract once its named gates are filled; it is not an accepted preregistration, a fitted model, implementation acceptance or production authority.

**Operation:** `options-intelligence-deep-research-20261003-astra-001`. **Procedure context reported by principal:** Mastermind `20adcaf65c2dd1bb734ab06e215feb1a0eb65659`, INDEX 1.0.1, C2 bounded specification. The JSON companion is the structured form of this same contract.

## Frozen proposals and real remaining gates

One primary feature, target and augmentation algorithm is proposed per pilot. Coefficients are learned only on admitted training data; no alternative feature, link, regularization or horizon is selected after seeing validation/test performance. β=0 recovers the fixed B1-RI forecast. The now-specified research adapter still needs causal incumbent snapshot history, actual field/clock qualification, empirical dates, power-planned lengths, and owner acceptance; these remain real dependencies—not invented facts.

| Pilot | Primary feature | Target | Algorithm / loss |
|---|---|---|---|
| P1 | OIF01, M2 activity | Next 30-minute exact log high/low range | Linear incumbent offset; nonnegative range projection; squared loss |
| P2 | OIF04, M2 signed dollar delta | Next 30-minute market/sector residual log return | Linear incumbent offset; squared loss |
| P3 | OIF19, IV − sqrt(physical variance forecast) | Matched 20-session ACT/365F variance | Positive multiplicative incumbent offset; QLIKE |
| P4 | OIF22, borrow-adjusted matched IV spread | Five-session residual return after a one-session skip | Linear incumbent offset; squared loss |
| P5 | OIF13, one fixed inventory/shock scalar | Next ten-minute ACT/365F variance | Positive multiplicative incumbent offset; QLIKE |
| P6 | OIF35, raw relative spread | Actual full-fill cost within 60 seconds, conditional on fills | Nonnegative scalar incumbent offset; absolute loss |

**P6 principal disposition recorded 2026-10-03:** independently observed 60-second full-fill cost MAE is the sole empirical primary, conditional on actual complete fills. Catalogue quote coverage and simulated hedged markouts are diagnostics; explicit catalogue/protocol reconciliation is required before sealing. If actual fills are unavailable, P6 does not become a simulation-trained cost model.

Preserve #8286 and its registered nulls. Its 2017–2025 outcomes are development evidence, never an untouched confirmatory holdout. No completed study is rerun here.

## 1. Population and decision clocks

**Primary stock rule.** For P1–P4, take US common stocks in the latest causally consumer-admitted incumbent buy-pool revision available at formation, then apply the fixed source/reference/liquidity/contract gates below. Never use the current 69-row board as a historical universe.

**Qualification.** Known US common-stock identity (exclude ETFs, ADRs and incompatible deliverables); decision price >= USD 5; trailing 20 completed-session mean underlying dollar volume >= USD 50 million; trailing 20 completed-session mean total option contracts >= 1000; required current source/quote/contract and history gates. These numeric cutoffs are PRINCIPAL_PROPOSAL. Calculate only from data available at formation. No outcome selection or replacement after exclusions.

**Boundedness.** Process the complete admitted buy-pool census, with a proposed safety ceiling of 200 input rows per revision. A larger revision returns PANEL_BOUND_EXCEEDED pending a newly accepted bound; do not silently truncate by rank or ticker. No new capture resource is authorized by this specification.

**Identity and age.** Require publication/run/pair ID, exact board digest, row ID, as-of/effective dates, publication and consumer receipt timestamps, schema/score version, source-age metadata and full selection lineage. The last underlying price-through date must be no more than one completed NYSE session behind the expected price session. Missing/unknown board revision, unknown receipt, ambiguous effective age or all-missing incumbent covariates => unavailable, never confirmed absence.

**Population waterfall.** Persist every source row and its ordered inclusion/exclusion reasons; emit full-population and eligible-population digests each formation. B0 and B1/B2 use the same selected cohort. Options-free B0 inputs do not make that cohort options-free; inference is conditional on the incumbent selection and qualification rule.

**Sector benchmark rule.** PIT sector-to-ETF mapping fixed as Communication Services XLC, Consumer Discretionary XLY, Consumer Staples XLP, Energy XLE, Financials XLF, Health Care XLV, Industrials XLI, Materials XLB, Real Estate XLRE, Technology XLK, Utilities XLU. The source sector classification and its availability revision are required; unknown sector blocks the P2/P4 residual target rather than being assigned retrospectively.

**Scenario etfs.** SPY, QQQ, IWM

**Execution population.** P6 uses exact existing authorized single-leg standard-contract order/plan records, with their independent cohort/selection lineage. It is not forced into the current buy pool and creates no order. P5 retains its separate fixed ETF scenario population.

**Broader feasibility lane.** A separately labelled options-free feasibility lane may use SPY/QQQ/IWM/AAPL/MSFT/AMZN/GOOGL/META/NVDA. It is not a substitute for incumbent-cohort incrementality, a second primary, or a historical selection rule.

**Timezone.** America/New_York; store UTC plus IANA-zone/calendar version; ACT/365F uses actual UTC elapsed seconds.

**Calendar.** Pinned NYSE equity calendar and per-contract last-tradable/fixing calendars; full-session formation dates only. Future horizon paths retain actual holidays, half days and DST.

**Intraday slots local.** 10:00, 10:30, 11:00, 11:30, 12:00, 12:30, 13:00, 13:30, 14:00, 14:30, 15:00

**Rule.** For nominal slot s, t is the first actual eligible consumer admission at or after s and no later than s+10 seconds. Require exact feature artifact, B1 forecast and reference revisions available/received by t. Otherwise the slot is unavailable; do not move it to a more favorable later time. Persist actual t and the source cutoff c; source cutoff c<=t and t-c<=10 seconds. Windows end at c, outcomes begin at t. Actual receiver-clock precision/offset must qualify this ordering.

**Quotes.** Feature option quotes: original event age<=5 seconds at the feature valuation clock, <=2 seconds in the final 15 tradable minutes; underlying age<=2 seconds, <=1 second in that terminal period. No quote re-timestamping. P6 needs age<=1 second at the actual order decision. Outcome marks have their separate <=1-second rule below.

**Flow.** OIF01 uses the completed (c-15min,c] window; OIF04 uses (c-5min,c]. Require no recorded feed gap, complete reference units and a qualified event/condition/correction watermark. Later corrections do not change what the decision saw.

**Reconstruction.** Captured-PIT and reconstructed training history stay distinct. Reconstructed history may support model development when declared, but cannot establish historical operational performance. Final confirmatory decisions and B1/B2 artifacts require captured-PIT evidence.

## 2. Price sampling, units and label maturity

**Underlying mark.** S(u) is the midpoint of the last eligible two-sided underlying NBBO with 0<bid<ask, positive sizes, event time<=u, and event age<=1 second. At formation, it must also be available to the consumer by t. Outcome marks can arrive later but retain event time and the fixed label-revision cutoff. No next quote or interpolation across a missing mark.

**High low.** P1 uses the maximum/minimum eligible regular-session underlying price events in (t,H], including the start mark S(t). Eligibility is the frozen producer high/low-condition map. A bar can be used only when wholly contained in the requested interval; boundary fragments require the actual eligible events or an exact interval aggregate. A clock-minute bar that extends outside the actual consumer window is forbidden. If exact interval extrema cannot be supplied, the P1 label is unavailable, not silently replaced by a sampled-midpoint range.

**Return adjustment.** Use split- and cash-distribution-aware total-return log increments. Compose share-count changes and ex-entitlement cash credits through a versioned corporate-action ledger; no restated adjusted-price series lacking its revision provenance. For a simple interval with k end shares and cash D per starting share, r=log((k*S_end+D)/S_start). Ambiguous deliverables/actions produce a missing label. Intraday windows with no action reduce to log(S_end/S_start).

**Intraday variance.** For H=t+600 seconds, take marks at t,t+60,...,t+600; sum the ten squared total-return log increments. Annualized RVar=sum(r^2)/T, T=600/(365*86400). Keep the unannualized sum and T. Zero realized variance is valid.

**Twenty session variance.** H is the same local wall-clock timestamp as actual t, 20 NYSE sessions later. Use t and then five-minute marks through the first session close, including the final shorter interval. For each following session use the first eligible regular-session NBBO mark at/after open within 60 seconds, then five-minute steps through close or H, including a shorter final interval. Include each previous-close-to-next-open return once. The initial and terminal partial sessions are retained. An opening mark later than 60 seconds, missing interior/close mark, or unsupported corporate action makes the label incomplete. RVar_H=sum(r^2)/T_H; T_H=(UTC(H)-UTC(t))/(365*86400). This is a specified sampling estimator, not continuous-path quadratic variation truth.

**Label revision.** Use a single immutable label-data cutoff: 20:00 ET on the first NYSE session strictly after the date of H (or the P6 deadline). Label_mature_at is that cutoff only if all required outcome bytes/reference versions are available then. Otherwise status=missing_at_cutoff. Later reconstruction is a new labelled revision; it never silently replaces the primary label or enters an earlier fit.

**Missingness.** No missing label becomes zero and no incomplete path is rescaled. B1/B2 use the same complete-label rows, while all scheduled/eligible/forecasted/labelled counts remain visible. P1–P5 require at least 99% label completion among forecast-eligible test decisions for the declared full eligible-population conclusion; otherwise report conditional complete-case evidence and fail that coverage gate. This 99% is a principal-proposed quality threshold, not an assertion that missingness below it is random. Report missingness by root/date/event/feature quantile and distinguish halts, delistings, source gaps and invalid marks.

**Proxy robustness.** QLIKE does not repair biased price observations. Its forecast-ranking robustness with noisy variance proxies relies on conditions including conditional unbiasedness relative to the relevant information sets (Patton 2011). Stale, asynchronous, sparse, selected or illiquid marks can violate those conditions. Report sampling/age/coverage diagnostics and a predeclared 10-minute-versus-5-minute P3 sampling sensitivity without selecting the better result. The primary result is forecast loss on the specified proxy, not trading utility or a guarantee about latent variance.

## 3. Baseline identity and nested comparisons

**B0.** The explicitly options-free, simple benchmark specified for each pilot. It is diagnostic and deliberately cannot replace a stronger incumbent comparison. Its upstream transformations, labels and cohort selection still require an options-lineage audit.

**B1.** B1-RI, the explicitly target-trained incumbent-INFORMATION research adapter specified in Appendix A. It is not the production ranker and is not claimed to be an existing native target forecast. It adds only the fixed receipt-derived C vector to the same B0 target algorithm using matured training data. Require adapter and causal board/input artifact identities at every decision.

**B1 target gate.** The finite Appendix A algorithm is the PRINCIPAL_PROPOSAL alternative to a native target forecast. Gate on actual causal snapshot/receipt history, accepted information fields and adapter training evidence, not on the existence of a production variance forecast. A raw rank/C1 score never directly becomes yhat or variance. If causal incumbent snapshots/covariates are absent, B1-RI is unavailable; a B0-only diagnostic cannot be called incumbent-information incrementality.

**B1 history.** Generate augmentation-training B1-RI offsets by the prespecified expanding monthly cross-fit using only earlier matured training records and causal board revisions. Final adapter/nuisance/scaler fits freeze at the training cutoff. No in-sample adapter predictions trained on the same target rows. This is an offline research incarnation; it neither freezes nor replaces the production ranker.

**B2.** B2-RI is B1-RI plus the one declared OIF coefficient. beta=0 exactly recovers B1-RI. Primary estimand: incremental loss improvement over this fixed target-trained summary of incumbent information. It does not establish improvement over every incumbent raw feature, the live production ranking policy or an existing native target forecast.

**Quality controls.** Required catalogue quality/package/borrow/carry controls are eligibility rules and prespecified stratified diagnostics in this v1. Audit whether B1 already contains them. If it does not, do not claim that a one-coefficient gain isolates the primary feature from those controls. A separately accepted common-nuisance adapter is required before making that stronger conditional-information claim; it is not silently added to B1. The RI naming is mandatory where a study lacks those stronger common-nuisance controls; a positive result cannot be relabelled as fully confounder-adjusted private information.

**Cohort.** Even B0 is evaluated conditionally if the underlying candidate/order cohort was options-selected. No zero-GEX ablation proves that every upstream champion path is options-free.

**B0 receipts.** Every B0 value must use bytes available to the consumer by actual decision t, including exact-window high/low extrema, price marks, corporate-action versions and fitted HAR artifacts. A trailing B0 window may end at t rather than the flow cutoff c only when its required bytes were actually received by t. A producer event timestamp alone is insufficient; later corrected bars cannot backfill a past B0 forecast. Retain B0 artifact publication, maximum input availability and consumer receipt ordering.

## 4. Exact training algorithms and numerical domains

**Rz.** For each root, primary feature scope and five-minute nominal clock bin (fixed formation clock for daily/weekly pilots), median and MAD use the last 60 eligible training sessions before the fit cutoff, minimum 40 finite observations and positive MAD. z=(x-median)/(1.4826*MAD). Freeze in validation/test. No winsorization, clipping, epsilon denominator or pooling fallback. P4 uses qualified daily 15:30 observations for its scaler, though forecasts are weekly. Physical units and raw x are retained.

**Linear offset.** P1/P2/P4: beta=sum_train w*z*(y-b1)/sum_train w*z^2; through-origin weighted least squares, no intercept and no tuned penalty. Weights give each training date total weight one and each available root/slot within that date equal weight. Require finite values and strictly positive denominator. P1 predicts max(0,b1+beta*z); this declared nonnegative projection is part of the range algorithm, not an undisclosed numerical rescue. P2/P4 predict b1+beta*z. beta=0 recovers qualified B1 (P1 B1 must already be nonnegative). Primary loss is squared error in raw label units. For P1 this is specifically unconstrained WLS followed by a nonnegative prediction projection; it is not asserted to minimize the projected squared-loss objective.

**Positive variance offset.** P3/P5: v2=v1*exp(beta*z), with beta in the fixed PRINCIPAL_PROPOSAL domain [-1,1]. Fit one beta by minimizing mean weighted [log(v1)+beta*z+y/v1*exp(-beta*z)] on matured training records. No intercept. beta=0 exactly gives v1. The domain is a declared regularization choice, not a fitted risk bound. A boundary optimum is retained with constrained_optimum=true, not clipped after fitting.

**Variance solver.** The objective is convex for y>=0,v1>0. Let D(beta)=sum w*z*(1-(y/v1)*exp(-beta*z)); Q(beta)=sum w*z^2*(y/v1)*exp(-beta*z). If every y*z^2 is zero and sum(w*z)=0, the objective is analytically flat: FIT_UNIDENTIFIED. Otherwise, if D(-1)>=0 choose -1; else if D(1)<=0 choose 1; else bisect the monotone derivative root to beta bracket width<=1e-10, at most 100 iterations. All objective/derivative/intermediate values must be finite; retain a boundary optimum with its flag. Do not infer nonuniqueness solely from a rounded tiny Hessian; numerical inability to certify the bracket yields SOLVER_UNRESOLVED.

**Numerical refusal.** Canonical float64 calculations require finite y,z,b1/v1 and finite exponent/product/loss. Variance inputs/forecasts must be strictly positive; y may be zero. Underflow to zero, overflow, nonfinite products/losses, failed rank/denominator checks or solver nonconvergence produce typed refusal. No epsilon variance floor, clipping z, fallback to IV/B0, or replacement by B1 is permitted on failed B2 rows. Count all such refusals and require zero numerical refusals on otherwise eligible test rows for model qualification.

**Qlike.** L(v,y)=log(v)+y/v for v>0,y>=0, in matched variance units. Compute and report paired L(v1,y)-L(v2,y); no log(y) term, no loss applied to OIF19/OIF20, and no arbitrary additive target constant. Unit changes add the same constant to each loss and cancel in the paired difference.

**Physical har.** For each stock, construct completed-session unannualized integrated variance z_d including its preceding overnight return once, using the same five-minute/session-boundary estimator. X=(1,log z_last1,log mean(z_last5),log mean(z_last22),N_events). N_events counts distinct known scheduled FOMC decisions, CPI releases, payroll releases and root earnings within (t,H]; interval-valued event timing must lie wholly inside/outside or the count is unavailable. Fit OLS log(RVar_H)=X*b+e on the last 500 eligible training daily formation dates, minimum 252, all target labels matured before fit. Require full column rank and strictly positive log inputs/targets; a genuine zero training target is an explicit incompatible log-fit domain, not silently dropped or epsilon-replaced. smear=mean_train(exp(e)); vhat_P=exp(X*b)*smear. Coefficients and smear are training-only and frozen. No second smearing factor is applied to the directly QLIKE-trained B2.

**Generated feature training.** Avoid fitting the physical HAR or borrow projection on the same row whose residual becomes a B2 regressor. For augmentation-training rows, generate the feature with an expanding as-of fit using only earlier eligible data/labels; use the same maximum-500/minimum-252 rule, and freeze/refit only at the prespecified first-session-of-month development cutoffs. For validation/test, use the final training-cutoff nuisance models, frozen. B2 requires enough already cross-fitted rows; the first 252 nuisance-fit dates are warm-up, not augmentation observations. Existing qualified historical model receipts may supply those rows. This can be a binding history-availability gate.

**Training weights.** For every fit, give each eligible training date equal total weight, each eligible root within that date equal weight, and each eligible slot/order within that root/date equal weight; normalize all row weights to sum one. Preserve these weights in the fit receipt. These hierarchical weights replace any shorthand reference to equal root/slot rows and are also the evaluation loss weights. For a per-root nuisance fit this reduces to equal eligible dates.

## 5. Residual-return benchmark

**Definition.** For P2/P4, y=r_stock-beta_M*r_SPY-beta_S*r_sector over the exact same endpoint interval; r values are total-return log increments. The intercept from the beta fit is not subtracted. This is a fixed benchmark residual, not risk-adjusted alpha or a tradable hedged portfolio.

**Beta fit.** Per root, OLS daily total-return stock returns on an intercept, SPY and its PIT-mapped sector benchmark over the last 252 completed training sessions, minimum 126, full rank. Use only labels/reference data available before the fit cutoff; freeze betas for validation/test. A missing matched benchmark mark makes the label missing. Historical B1 target receipts must use this same residual-target version or be explicitly adapted before acceptance.

**Historical target causality.** Historical P2/P4 rows keep the market/sector beta vector fixed by the most recent first-session-of-month fit cutoff strictly before formation, estimated from earlier mature daily returns. Do not regenerate earlier residual labels with final-cutoff betas. Store each row beta artifact, fit cutoff and source classification revision; at the final training cutoff fit one frozen evaluation beta version for validation/test. Target identity is the declared as-of residualization algorithm plus each row beta version, not an assertion of a common estimated vector across all historical dates.

## Appendix A. Fixed incumbent-information research target adapter

**Status.** PRINCIPAL_PROPOSAL, adopted as the concrete primary B1 definition subject to causal data and owner acceptance; no fitted coefficients or implementation are supplied.

**Scope change.** This closes the native-target-forecast dependency by narrowing the claim. B1-RI is a target-trained summary-information research baseline, not the live incumbent ranker. A result beats this fixed adapter only. No dissent from using this tractable research estimand, but substituting its result for native-policy outperformance would materially overstate the evidence.

**Board example not training data.** Observed extract: board snapshot 3d9969c15bba0f57b64da7592c0731cc8a0f2eac, publication 75e82a871b0d2e67eae7d27c273f60c8817ec321, pair f9f4108104c84918bacc5ff06805be40, as_of 2026-10-01, emitted 2026-10-03T08:15:30Z, 69 rows. GEX was below the presence floor in that specific receipt. It cannot be used in October 1 decisions without earlier actual receipts, cannot establish every champion is options-free, and is not a historical-universe or training-data substitute. Executed binary attestation is unknown in the extract.

**C exact order.** score_center, stage_live, stage_setting_up, stage_ran, stage_basing, stage_unknown, score_missing, publication_age_days

**C values.** score_center=(published prophet.score-50)/50 for a finite score in [0,100]; an explicitly null score uses 0 with score_missing=1, while invalid/nonfinite/out-of-range scores refuse the row. Four stage indicators use the exact strings live/setting_up/ran/basing; blocked is the all-zero known reference. An explicitly null stage sets stage_unknown=1. An unrecognized non-null stage is SCHEMA_VERSION_UNQUALIFIED. publication_age_days=(t-publication_time)/86400 >=0, from the exact admitted revision. No rank reconstruction, score rescaling by current cross-section, family/GEX recomputation or future board metadata.

**Covariate gate.** Require a known, selected board row and at least one genuine observed score or recognized stage; all-missing score/stage refuses the row. Explicit null field plus observed other field is distinguished from absent/unknown board. Keep field-level missingness and source-quality flags. Document any covariate constant in training; it conveys no cross-sectional/time variation merely because a coefficient exists.

**B0 contract.** Use exactly each pilot B0 target algorithm below, unchanged in the adapter. B1-RI adds C to that target model through the following fixed offset fit. The B0 lineage/selection audit remains mandatory; calling its inputs options-free is conditional on that audit.

**Identity target adapter.** P1/P2/P4/P6: fit gamma=(C^T W C + .01 I)^(-1) C^T W (y-b0), with no extra intercept, fixed ridge .01 and the common date-balanced training weights normalized to sum one. C and gamma orders are pinned above. Solve the positive-definite system by Cholesky with a finite residual check relative norm <=1e-10; failure is unavailable, not pseudoinverse/fallback. B1=b0+C*gamma; only P1 uses the declared max(0,.) range projection. The P6 adapter estimates a cost mean and is evaluated by MAE; it is not asserted to be an optimal conditional-median model.

**Variance target adapter.** P3/P5: B1=v0*exp(C*gamma), v0>0. Fit gamma in [-1,1]^8 by minimizing mean weighted [log(v0)+C*gamma+y/v0*exp(-C*gamma)] + (.01/2)*sum gamma_j^2. No intercept and no additional smear. The fixed positive ridge makes the objective strictly convex. beta=0 in the later OIF augmentation still exactly recovers this fitted B1.

**Variance adapter solver.** Start gamma=0. Cyclic coordinate descent in pinned C order; each coordinate minimizes the convex objective on [-1,1] with derivative sum w*C_j*(1-y/v_current)+.01*gamma_j. Use the same bracket/bisection convention as the scalar solver, accounting for all other fixed coordinates. Stop only when max coordinate change <=1e-8 and projected-gradient infinity norm <=1e-7; maximum 10,000 sweeps. At a lower boundary the KKT condition is derivative>=0; at an upper boundary it is derivative<=0; interior derivative is zero. Finite-domain/refusal rules apply to every iteration and prediction. Nonconvergence refuses the fit. Boundary coordinates are reported.

**Training causality.** Use the same mature-label splits and date weights as the pilot. For each monthly cross-fit cutoff, fit B0 nuisance components and the RI adapter only from earlier eligible rows with matured labels; produce forecasts for the following development block without refitting. These held-out B1-RI forecasts feed scalar OIF augmentation training. At the final training cutoff fit the frozen evaluation adapter on admitted development rows; validation/test outcomes never change it. Insufficient historical board receipts/history => gate held, not recreated availability. Inside each RI fit, every fitted B0 offset must itself be an earlier as-of or time-ordered held-out forecast: for P3, an HAR forecast whose target never entered that HAR fit. The RI adapter may not use in-sample HAR fitted values even though its own training labels are mature. Persist row-wise B0 fit/publication/availability receipts. Next, held-out B1-RI forecasts feed B2 fitting. This two-level historical forecast construction applies at the final RI fit as well; no final HAR predictions retroactively replace its training offsets. P1/P5 persistence and P2/P4/P6 constant B0 need no fitted-offset cross-fit but still require causal input/target versions.

**Forecast receipt.** Persist target_id, B0 algorithm/parameter hash, C schema/hash and raw receipt refs, gamma/fit cutoff/label cutoff, OIF beta/scaler refs, source/board population digest, artifact publication and consumer receipt, predicted units/horizon, and unavailable reasons. The emitted forecast belongs to an unimplemented research adapter, not to the production champion.

**Scaler causality.** Each historical nuisance/B0/B1 forecast artifact must have been computable before its forecast row. The final B2 feature scaler is estimated solely from admitted augmentation-training feature values before the final fit cutoff and is then applied as a training transformation to those rows; it is not falsely labelled as the scaler historically published at each row. Validation/test use that one frozen final scaler. Preserve both raw historical OIF values and this final model-input transform.

## 6. Pilot-specific contracts

### P1 — OIF01

**Universe.** Dynamic, causally admitted and prequalified incumbent US-common-stock buy pool under the common population rule; M2 only, standard single-underlying deliverables.

**Formation.** Each common intraday slot on full sessions; actual t after eligible delivery.

**Feature.** Raw A=sum(q*m)/Vstock over completed 15 minutes, same root/window and known share units; RZ(A) supplies z. Vstock<=0 or a feed gap is unavailable. Unsigned complex legs remain activity, with package/quality controls retained.

**Label.** H=t+1800 seconds; y=log(max eligible underlying price/min eligible underlying price) over the exact interval, including S(t). y>=0, dimensionless, no annualization.

**B0.** Trailing exact 30-minute log high/low range ending at t, using only available underlying observations; unchanged-range forecast, including valid zero.

**B1.** B1-RI from Appendix A using this exact target and B0 definition; the matching range/return/cost target units.

**B2.** linear_offset, projected to nonnegative range as declared.

**Primary loss.** (y-yhat)^2 in squared log-return range units.

**Controls and gates:**

- OIF06 envelope/mass, OIF35 median relative spread and OIF37 measured coverage/age retained on the identical cohort; Greek-unobservable envelope is unknown, not zero.
- Require known multiplier/deliverable for every counted contract and at least 90% qualified received-premium quote coverage; retain all received denominator mass. No market-wide completeness claim without a source-universe receipt.
- Actual precise-interval high/low labels are required. Any necessary stronger conditional-quality claim requires the common-nuisance gate in the baseline contract.

**Not claimed.** Bullish direction, opening demand, human discovery utility or a Johnson–So replication. Fixed-capacity review utility is a separate queued study.

### P2 — OIF04

**Universe.** Dynamic, causally admitted and prequalified incumbent US-common-stock buy pool under the common population rule; M2 only, standard single-underlying deliverables.

**Formation.** Each common intraday slot; completed five-minute flow window.

**Feature.** D=sum classified a*q*m*Delta*S; signed long-option delta includes negative puts. Use RZ(D). Signing requires strictly preceding valid quotes and the pinned conservative condition/package rule. Unknown and ambiguous exposure stays in OIF06, with unpriceable Greek mass separately unknown.

**Label.** H=t+1800 seconds; y is the exact market-and-sector residual total-return log increment from the common residual_return contract.

**B0.** Zero conditional residual-return forecast (a simple martingale diagnostic, not a strong operational benchmark).

**B1.** B1-RI from Appendix A using this exact target and B0 definition; the matching range/return/cost target units.

**B2.** linear_offset without clipping or probability conversion.

**Primary loss.** (y-yhat)^2, squared decimal log-return units.

**Controls and gates:**

- At least 90% of received eligible premium must have qualified quote/model inputs; at least 70% of known absolute delta mass must have a nonambiguous sign. These are fixed proposed coverage gates, not signing-accuracy evidence.
- Retain exact classifier, package watermark, quote timing, OIF06 bounds, OIF35 spread and OIF37 coverage. An envelope crossing zero prohibits a robust-direction label but does not delete an otherwise eligible forecasting row.
- No current calibrated buy/opening/customer/dealer probability is assumed.

**Not claimed.** A calibrated direction probability, actual opening purchases, dealer positions or a tradable residual hedge portfolio.

### P3 — OIF19

**Universe.** Dynamic, causally admitted and prequalified incumbent US-common-stock buy pool under the common population rule; standard qualified contracts and per-root history gates.

**Formation.** Nominal 09:35 ET; actual t satisfies the common ten-second delivery gate; H is the same local time 20 NYSE sessions later.

**Feature.** x=sigma_ATM(T_H)-sqrt(vhat_P,H), in decimal annualized volatility; sigma is forward-ATM IV from linear interpolation of total variance over qualified strikes and expiries bracketing actual T_H. No extrapolation. vhat_P is the training-only physical_HAR estimate. Use RZ(x); negative x is valid.

**Label.** Matched ACT/365F RVar_H from the common twenty-session sampling path; keep raw integrated variance and actual T_H. y=0 is valid in evaluation.

**B0.** The separately specified positive physical_HAR variance forecast, with its training-only Duan smear.

**B1.** B1-RI from Appendix A using this exact target and B0 definition; strictly positive variance in the matched units/horizon.

**B2.** positive_variance_offset: v2=v1*exp(beta*z19). beta is fitted once by the stated convex QLIKE solver; no additional smearing or intercept.

**Primary loss.** QLIKE log(v)+y/v; paired differences only for inference.

**Controls and gates:**

- Matching rates/dividends/exercise/underlying clocks, positive IV, eligible bracketing expiries, source age and OIF35/OIF37 coverage must qualify. Missing surface or physical forecast => unavailable x, never zero.
- If an external same-interval variance uses (252/n)*sum(r^2), multiply by (n/252)/T_H before comparison. Missing n, interval or convention blocks use.
- Cross-fitted nuisance features are mandatory during augmentation training; all H20 labels mature before nuisance fits, beta fit and final model sealing.
- QLIKE zero labels remain valid. Positive-link numerical failures are explicit refusal, not clipping or fallback.

**Not claimed.** OIF19 as variance, expected realized volatility E[sqrt(RVar)], a risk-neutral physical probability, or the quarterly aggregate VRP result. OIF20=IV^2-vhat=OIF19*(IV+sqrt(vhat)) remains a separate queued feature; no substitution, joint fit or best-of selection.

### P4 — OIF22

**Universe.** Dynamic, causally admitted and prequalified incumbent US-common-stock buy pool under the common population rule; standard qualified contracts and per-root history gates.

**Formation.** Friday 15:30 ET only when that regular session exists and actual t passes delivery. No Thursday substitute on Friday holidays/half days. Entry a is the same local clock as t on the next NYSE session; H is that same clock five NYSE sessions after a. If a or H is after a scheduled half-day close, formation is calendar-ineligible rather than shifted.

**Feature.** Pick the expiry nearest 30 calendar days within [21,45], tie to earlier expiry. Match call/put strike; require |log(K/F)|<=.05 and at least three eligible pairs. Raw IV spread uses weights (OI_C+OI_P)/sum pair OI, with OI revision available at formation. x=Raw-X_fee*beta_fee. Fit per-root OLS borrow projection on last 500 daily 15:30 training formations, minimum 252, using (1,b,b^2,Tbar,I_div,Spr_pair,log(F/S)); Spr_pair is OI-weighted mean of half the sum of call/put relative spreads. Generate training x as-of/cross-fitted; freeze evaluation projection. Use RZ(x) from daily formations. Precisely, w_j=(OI_Cj+OI_Pj)/sum_k(OI_Ck+OI_Pk); Raw=sum_j w_j*(IV_Cj-IV_Pj), in decimal annual-volatility units. b is the contemporaneously quoted annual borrow fee as a decimal; b^2 is its literal square. Tbar=sum_j w_j*T_j, where T_j is ACT/365F years to the contract model fixing endpoint. I_div=1 iff at least one dividend ex-entitlement date/time known at formation falls in (t, fixing_endpoint], otherwise 0 only with a qualified complete schedule; unknown schedule is unavailable. Spr_pair=sum_j w_j*.5*(RelSpread_Cj+RelSpread_Pj); log(F/S) is dimensionless with the exact qualified forward F and spot S used for pair IVs. The nuisance design order is exactly (1,b,b^2,Tbar,I_div,Spr_pair,log(F/S)); coefficients retain the implied units. No sign flip is selected after outcomes.

**Label.** After the explicit one-session skip, y is market-and-sector residual log total return from S(a) to S(H), with all benchmark marks synchronized. Formation-to-entry return is not part of y.

**B0.** Zero residual-return forecast.

**B1.** B1-RI from Appendix A using this exact target and B0 definition; the matching range/return/cost target units.

**B2.** linear_offset, no post-outcome sign or threshold choice.

**Primary loss.** Squared residual-log-return error.

**Controls and gates:**

- Borrow fee in decimal annual units must be available and no older than one trading session; missing/stale fee makes adjusted x unavailable, never zero fee.
- Freeze low-fee diagnostic as b<=0.01/year (1% annualized), a proposed label not an economic theorem. Report observed-high-fee and missing-fee populations. OIF23 raw spread uses the identical pairs/rows for its diagnostic.
- Known dividends, exercise/carry inputs, pair clocks and full-rank nuisance fit are required. Missing OI denominator/pairs or rank failure => unavailable.
- Minimum 52 eligible weekly training dates plus daily nuisance history; absent history is a gate, not a reason to reuse the inspected #8286 result as a holdout.

**Not claimed.** Exact replication of published IV-spread tables, a fee-free short portfolio, or proof the residual is private information.

### P5 — OIF13

**Universe.** SPY, QQQ and IWM; same-day still-tradable contracts only. One hedge underlying/currency per observation.

**Formation.** Common intraday slots; no final-ten-minute extension or expiry crossing. A numerical qualification pass is required before empirical forecasting.

**Feature.** At each session 09:35, freeze the selected same-day contract book with |log(K/F_09:35)|<=.05 and positive prior-reported OI, using known reference identities. h_call=+OI_call and h_put=-OI_put is the sole PRIMARY inventory scenario. It is not claimed to be dealer inventory. Keep the book fixed through that session, and require every nonzero selected position to have a qualified current model/quote. At feature time, compute H=-(.99*S)*sum h*m*(Delta(.99*S,sigma+.01,T-600/Y)-Delta(S,sigma,T)), sticky strike, Y=365*86400. Require all T>600/Y. Raw H is USD endpoint hedge notional. RZ(H) is an explicitly versioned model-input transform, not a change to OIF13 raw units. Other shocks and sign allocations are diagnostics, not additional primary forecasts.

**Label.** Horizon endpoint t+600 seconds; annualized realized variance from ten one-minute log-return increments under the common intraday variance rule.

**B0.** Trailing ten-minute realized variance on the identical ACT/365F convention. It must be strictly positive for the B0 QLIKE diagnostic and for the multiplicative B1-RI adapter. A genuine zero is never epsilon-raised: it blocks that row of the positive B0/B1-RI/B2 comparison, while the scenario output and realized outcome remain in the census. It is not a missing realized-variance label.

**B1.** B1-RI from Appendix A using this exact target and B0 definition; strictly positive variance in the matched units/horizon.

**B2.** positive_variance_offset with the same one-coefficient convex solver and fixed domain.

**Primary loss.** QLIKE of positive v1/v2 against nonnegative realized variance.

**Controls and gates:**

- Accepted independent pricing/Greek/time/hedge witnesses, including correct portfolio-versus-hedge sign and endpoint-spot notional, are prerequisites; this spec does not certify them.
- Book identity, OI availability and full coverage of the SELECTED book are required. This is not full-market or actual dealer-book coverage. No hidden removal of hard-to-price positions.
- The predetermined half-day/expiry rules and book/quote freshness must pass; unqualified expiry crossing is unavailable.
- Report fixed alternative inventory/shock outputs only as sensitivity diagnostics; do not select the best scenario by validation/test performance.
- If the incumbent board has no causally known row for a fixed ETF, B1-RI empirical incrementality is unavailable for that ETF. Retain numerical/scenario work; do not encode missing board identity as a zero C1 signal or replace the empirical cohort.

**Not claimed.** Actual dealer inventory/trades, causal price amplification, market-wide GEX, or a validation of five-day candidate direction.

### P6 — OIF35

**Universe.** Authorized existing single-leg standard-contract order/plan records with known US stock/ETF identity and exact selection lineage; no new orders, routing or quantity changes. Separate from the buy-pool population.

**Formation.** Actual consumer order decision t with frozen side a in {-1,+1}, requested q>0, exact contract, fees and decision NBBO M0; require t+60 seconds before last tradable time, q<=displayed ask_size for a buy (a=+1) or q<=displayed bid_size for a sell (a=-1), and quote age<=1 second. Link order, child fills, plan, feature and source revisions by exact IDs.

**Feature.** x=RelSpread=(ask-bid)/M0. Keep raw dimensionless x and quote/depth metadata. For this cost model, no RZ is used; x is the published raw OIF35 scalar.

**Label.** Primary empirical target is observed quote-to-fill implementation shortfall for an order fully filled by t+60 seconds: y_bps=10000*(a*(VWAP_actual_fills-M0)/M0 + actual_fees/(q*m*M0)). Fill events/fees come from independent actual execution records. Negative price-improvement costs are valid. Partial/unfilled/cancelled orders have explicit categorical outcomes, no invented full-order slippage. Report the primary cost result as conditional on full fills and report that selection/coverage; it is not unconditional execution policy value.

**B0.** Zero slippage/fee forecast, a deliberately simple options-free-input diagnostic; no claim that it is an adequate economic cost model.

**B1.** B1-RI from Appendix A using this exact target and B0 definition; the matching range/return/cost target units.

**B2.** One nonnegative through-origin offset coefficient: yhat2=yhat1+beta*x; fit beta>=0 by weighted median of (y-yhat1)/x with weights w*x over x>0 training rows, then take max(0,that median). This is the exact one-dimensional L1 optimum on the declared domain, no intercept/tuning. beta=0 recovers B1. If the weighted-median minimizer is an interval, choose its smallest nonnegative minimizer; record nonuniqueness.

**Primary loss.** Absolute error in option-premium basis points against actual full-fill cost. Proposed useful margin: 5 basis points MAE improvement.

**Controls and gates:**

- Actual order/fill/fee access and authorization are mandatory for this empirical target. If absent, P6 stays at observation/numerical-simulation stage and its confirmatory p=1.
- Use exact contract, q/side from the existing plan; retain OIF34/36/37/38/40, quote age, displayed size and clock margin. Actual fills are never synthesized from the NBBO.
- Account for every order and missing execution receipt; distinguish known no-fill from missing records. Full-fill conditioning cannot support changed fill-rate, routing or policy utility claims.
- Principal disposition recorded 2026-10-03: actual 60-second full-fill cost MAE is the sole empirical primary, conditional on actual complete fills; catalogue quote coverage and simulated hedged markout become diagnostics. The principal will reconcile catalogue/protocol versions explicitly before sealing. No actual-data or expression authority is implied.
- The separate order population still needs a causal incumbent row for the exact root and accepted revision to construct C. An ETF or order outside a qualified incumbent snapshot is not assigned an invented zero score or stage. Such rows remain observation/coverage records, while B1-RI/B2 forecasting is unavailable.

**Simulated markout diagnostic.** For fixed hypothetical q/side and contemporaneous admissible quote, define P_entry=ask for buy or bid for sell; at t+60 use option midpoint M60 and underlying S60. Markout=a*q*m*((M60-P_entry)-Delta0*(S60-S0))-declared_fees, in USD, with a frozen initial delta hedge and explicitly assumed hedge financing/cost convention. This is simulated mark-to-market, not an actual fill/exit, and is never a training label for execution calibration. Missing clocks/Greeks/quotes make it unavailable. No result is produced here.

**Not claimed.** Fills from midpoint/NBBO, actual delta-hedged P&L, cost calibration from self-generated simulation, or any permission to compute/publish candidate option P&L under false candidate authority flags.

## 7. Splits, purging and frozen model lifetime

**Dates.**

```json
{
  "training_start": null,
  "training_fit_cutoff": null,
  "validation_start": null,
  "validation_end": null,
  "test_model_sealed_at": null,
  "test_start": null,
  "test_end": null
}
```

**Date status.** BLOCKED_UNTIL_DATA_AND_PRINCIPAL_BINDING. No historical or future empirical dates are asserted available here.

**Training.** Last 500 eligible training formation sessions, minimum 252 distinct eligible dates per required root, before the fit cutoff and after nuisance warm-up. P4 coefficient fitting uses weekly formations from that training span, minimum 52 weekly dates. P6 needs at least 252 eligible order dates and 500 full-fill observations. These are fit-domain proposals, not power guarantees.

**Validation.** Use the next max(63,20*L) full NYSE formation sessions, where L is the primary bootstrap block length: 400 sessions for P3/P4 and 100 for P1/P2/P5/P6. Models/scalers are frozen. This conservative minimum-20-block duration was principal-adjudicated 2026-10-03 as a numeric design constraint, not a power guarantee or claim of feasible data. Validation is for pipeline audit, support/domain checks and pretest variance/power planning, not feature, coefficient-bound, loss or hyperparameter selection. No post-validation refit in v1. A changed algorithm creates a newly sealed version and a new untouched test.

**Purge.** Every observation used for any fitting, nuisance estimation, tuning, selection or calibration must have label_mature_at <= that stage cutoff. Remove training labels overlapping validation. Also wait for all validation labels used for planning to mature before sealing the final test; specifically exclude the H20 validation tail from influencing an earlier test model. Use exact [label_start,label_end] intervals, not a guessed fixed gap. The same boundary logic applies at every historical cross-fit cutoff.

**Test.** First full session after all capability/source/authority/principal/model/validation-label gates are accepted, then the precommitted number of NYSE formation sessions N. Primary v1 has one final test and no interim efficacy looks or automatic refits. Operational source failures are recorded without viewing comparative losses; pausing cannot select good-return days.

**Length.** Before any test outcomes, set N from the power rule with a principal-proposed lower bound 126 and upper bound 504 NYSE sessions. These are planning limits, not promised duration or sufficiency. If required N exceeds 504, label the confirmatory pilot infeasible/underpowered under v1; do not pretend the upper bound is adequate. Each pilot may bind its own N before its test starts; the six-test multiplicity family remains fixed.

## 8. Loss, dependence, multiplicity and power

**Loss aggregation.** On identical forecast/label-eligible rows, give each eligible date equal total weight, each eligible root within date equal weight, then each eligible slot/order within root/date equal weight. Use this same hierarchy for fitting and evaluation. P4 uses eligible formation Fridays, while non-formation sessions remain structural missing positions in its bootstrap calendar. Never count prints, legs or repeated alerts as independent observations.

**Block lengths sessions.**

```json
{
  "P1": 5,
  "P2": 5,
  "P3": 20,
  "P4": 20,
  "P5": 5,
  "P6": 5
}
```

**Bootstrap.** For each pilot construct its ordered NYSE session grid with daily statistic g_d: for P1/P2/P4, g_d=mean_date(.98*L1-L2); for P3/P5, g_d=mean_date(L1-L2)-.01; for P6, g_d=mean_date(L1-L2)-5. Dates without eligible paired outcomes are missing positions, never zeros; P4 non-Friday dates are structural missing positions. Let Tobs be the mean over observed g_d. Resample 9,999 circular moving-calendar-block series: independently choose starts uniform on [0,n-1], copy L successive grid positions modulo n, concatenate ceil(n/L) blocks, and truncate to n. Preserve complete cross-root/slot records within each sampled date and aggregate with the declared weights. For null draws replace every observed g_d by g_d-Tobs before resampling; p=(1+count(null_mean>=Tobs))/(9999+1), including ties. An empty resample is INVALID_EMPTY_BOOTSTRAP and invalidates inference; do not silently redraw. Any nonfinite statistic likewise invalidates inference. Repeat exactly once at 2L as a registered sensitivity, never choose the more favorable result.

**Test.** Test one-sided H0 E[g_d]<=0 with the exact centered-bootstrap p-value above. Report ordinary uncentered paired loss benefit and margin separately. Apply Holm step-down to the six p-values sorted ascending, ties by pilot ID: reject sequentially only while p_(k)<=.05/(7-k), k=1,...,6, stop at the first failure. Unrun, blocked or invalid pilots keep p=1; the family never shrinks. Existing #8286 BH results remain a different family. No interim efficacy looks or alpha recycling.

**Margins.**

```json
{
  "P1": "2% reduction in mean squared range error",
  "P2": "2% reduction in mean squared residual-return error",
  "P3": "0.01 mean paired QLIKE loss improvement",
  "P4": "2% reduction in mean squared residual-return error",
  "P5": "0.01 mean paired QLIKE loss improvement",
  "P6": "5 basis points of initial option premium reduction in mean absolute execution-cost error"
}
```

**Margin status.** PRINCIPAL_PROPOSAL statistical screening margins, not established economic utility or validated optimal thresholds. The principal must accept/revise them before validation/test outcome-driven decisions. Decision utility/policy promotion requires separate stakeholder costs and authority.

**Relative margin statistic.** For P1/P2/P4, the null-boundary daily statistic is mean(0.98*L1-L2); also report ordinary mean(L1-L2) and relative reduction 1-mean(L2)/mean(L1), unavailable if mean(L1)=0. For P3/P5/P6, subtract the fixed margin only for the hypothesis test; never alter the fitted target or reported raw loss.

**Power.** Power is planned only after all validation labels mature, and no power number is asserted here. Define validation daily boundary g as above and its mean-centered residual grid e. The declared alternative shifts the null-boundary mean by delta: delta=.02*mean_validation(L1) for P1/P2/P4, .01 for P3/P5, and 5 premium-bps for P6, corresponding to twice the useful margin in the original loss units. Require finite delta>0. Split the validation calendar into nonoverlapping length-L blocks from its first session, discard only the final shorter block, and require at least 20 blocks containing observed g. Require positive finite sample variance of these block means. Also compute nonoverlapping 2L blocks, require at least 10 usable blocks and positive finite variance; estimate long-run SD at each length as sqrt(length)*sample_SD(block means). If their ratio SD_2L/SD_L falls outside [.5,2], return POWER_UNRESOLVED. These are conservative minimum stability screens, not proof of stationarity, valid asymptotics or future support. Missing blocks cannot be replenished after inspecting validation outcomes.

**Randomness.** Deterministic random indices use counter-mode SHA256, not an implementation-dependent PRNG: UTF-8 seed = operation + "|" + pilot_id + "|" + phase + "|L=" + decimal_block_length + "|N=" + decimal_grid_length. Allowed phases are test-null, test-interval, power-null, power-alt. For counter c=0,1,... hash seed + "|" + decimal(c); take the first 8 digest bytes as an unsigned big-endian integer u. To draw an index in n grid positions, reject u >= floor(2^64/n)*n and consume the next counter, otherwise return u mod n. Consume one accepted draw per block in replication-major order. No outcome-dependent seed change.

**Intervals.** Report a two-sided 95% percentile interval for the ordinary, unadjusted paired loss improvement using separate test-interval block draws. Sort the 9,999 uncentered bootstrap statistics; empirical quantile q_p is the item at one-based index ceil(9999*p), for p=.025,.975 (no interpolation). For relative-MSE pilots also recompute 1-mean(L2)/mean(L1) in each draw, reporting unavailable if any denominator is zero. These are descriptive marginal intervals, not simultaneous familywise confidence intervals; Holm governs the six primary one-sided decisions.

**Power simulation.** For N in {126,147,168,...,504}, generate 1,999 independent null series of length N and 1,999 alternative series from the validation residual calendar grid using the same circular L-block rule, preserving missing positions and truncating to N. Null entries are e; alternative observed entries are e+delta. Use phases power-null and power-alt and the candidate N in the seed. Empty/nonfinite resamples give POWER_UNRESOLVED, with no redraw. Sort the null means; critical value is the item at one-based index ceil(1999*(1-.05/6)). Count alternative means strictly greater than that value. Compute the two-sided 95% Wilson lower endpoint for that success proportion with z=1.959963984540054. Choose the first N whose lower endpoint is at least .80; this is the frozen planning N. If none qualifies, POWER_INFEASIBLE_WITHIN_504. The Bonferroni .05/6 planning threshold is conservative relative to the eventual Holm family. Simulation conditions on validation dependence/missingness and an imposed constant shift; it does not establish actual future effect size, stationarity, economic usefulness or 80% realized power. Persist all null/alternative counts, seeds, critical values, interval endpoints and candidate N decisions.

## 9. Availability and authority gates

| Gate | Owner | Required evidence | Blocked claim/work |
|---|---|---|---|
| G0 | Principal and incumbent research owner | Accept or amend the PRINCIPAL_PROPOSAL design, P6 catalogue disposition, useful margins and exact input/output identities before any trial is sealed. | All confirmatory fitting/evaluation authority |
| G1 | WS:ADVANCED-DATA-OPTIONS and WS:INTRADAY-FLOW-P0-RECOVERY | Current entitlement/resource, natural-session data, condition/correction/reference, arbitrary-interval label sampling and source/consumer clocks qualify for the named universe. | Affected pilot/source rows; no provider login/collector dispatch authorized here |
| G2 | Incumbent Prophet/OA owner | Accept the exact Appendix A RI adapter and supply causal incumbent snapshot/history receipts for it. Audit B0 lineage, selection and exact board/run/revision identity. No native forecast is assumed. | Primary incumbent incremental claim |
| G3 | WS:OPTIONS-CONTEXT-AUDIT-PREREG-V2 | Bind actual train/validation/test dates, histories, primary family, overlap/maturity manifest, exact scaler/nuisance artifacts and power-planned N. | Accepted preregistration and confirmatory run |
| G4 | Incumbent analytical/numerical owner | Accept relevant model/Greek/deliverable/clock/scenario numerical fixtures under exact source heads; no false-floor or unsigned-position substitution. | P2 Greek-dependent rows, P3/P4 surfaces, P5, P6 Greek diagnostics as applicable |
| G5 | WS:OPTIONS-ALPHA-INTELLIGENCE-RECOVERY | Authorize read use of existing order/fill/fee records and the distinct exact-option policy contract. No inherited candidate authority escalation. | P6 empirical target; absence leaves numerical/observational work only |
| G6 | Principal/research reviewer | Pass pretest finite-domain/source/coverage checks and power feasibility without test-outcome inspection. | Confirmatory seal; unmet gates are explicit findings, not automatic retries or fallback models |

**Still unbound:** `principal_adjudication_receipt`, `incumbent_owners_acceptance_receipts`, `source_capability_receipt`, `B0_lineage_manifest`, `B1_RI_adapter_and_snapshot_receipts`, `dataset_manifest`, `split_date_manifest`, `power_planned_test_lengths`, `accepted_trial_id`. Null values are intentional gates, not defaults that an implementation may guess.

## 10. Bounded implementation handoff and report

Implement finite existing-owner adapters that validate the above inputs, construct immutable feature/label records, fit exactly the declared coefficients on admitted development rows, emit B0/B1/B2 forecasts/losses and a report/typed refusal. Do not add collectors, stores, autonomous jobs, model search, orders, notifications or production schema/authority changes. No fit or implementation was run while authoring this specification.

The study JSON is a research specification, not the strict candidate feed. Preserve all incumbent false candidate authority flags and distinct expression-policy field sets. ROOT/principal adjudication and existing owner acceptance remain required; this file grants neither.

The finite worker return must include exact input/version manifests; per-slot/order eligibility and reason counts; raw/scaled feature values; label starts/ends/maturity and revision IDs; B0/B1/B2 forecast identities; coefficient/scaler/nuisance receipts; numerical failures; common-row losses and population coverage; calendar-block uncertainty and multiplicity; pretest power assumptions versus realized sample support; and one of blocked, invalid construction, underpowered, failed incremental test or qualified-for-further-specified-policy-evaluation. No state automatically enables a candidate score, rank, gate, order or deployment.

Useful nonempirical fixtures include a negative OIF19 with a positive v2; β=0 identity; y=0 finite QLIKE; variance-unit conversion; late artifact receipt; a validation H20 label crossing test start; incomplete range boundary bars; an unavailable target-matched B1; a true no-fill versus missing fill record; and a book missing one nonzero position. These are acceptance requirements, not tests executed in this authoring task.

## Primary methods references

- **M-PATTON**: Andrew J. Patton (2011), [Volatility forecast comparison using imperfect volatility proxies](https://public.econ.duke.edu/~ap172/Patton_vol_proxies_JoE_2011.pdf). Primary author-hosted full paper retrieved; abstract and assumptions reviewed, not an empirical replication. QLIKE/proxy qualifications; no claim that the present sampled labels satisfy conditional unbiasedness.
- **M-CORSI**: Fulvio Corsi (2009), [A Simple Approximate Long-Memory Model of Realized Volatility](https://doi.org/10.1093/jjfinec/nbp001). Official metadata/abstract verified by principal; this worker full publisher fetch failed. Motivation for heterogeneous daily/weekly/monthly variance lags; this direct-H log-variance candidate is not claimed to reproduce the paper.
- **M-DUAN**: Naihua Duan (1983), [Smearing Estimate: A Nonparametric Retransformation Method](https://doi.org/10.1080/01621459.1983.10478017). Official metadata/abstract verified by principal; this worker full publisher fetch failed. Training-only retransformation motivation. A global residual smear is a specified candidate mean correction, not proof of conditional calibration under heteroskedasticity.

## Input versions

| Input | SHA256 |
|---|---|
| `RESEARCH_PROTOCOL.md` | `af5509c15a54b936a6995905723c44a7ae0cfeaba2e0072fbc001cdcc511cd05` |
| `CONTRACTS.md` | `e2a8ced5a769996a8b46a737db07d33ce6a9571b8838d763447d5c2e19514db5` |
| `options-signal-catalog.json` | `03f6e951dd838cc348472159d96a9eefe1c328879e720b09a2f4021aa57f7a82` |
| `options-near-expiry-spec.md` | `1bf7dd8412f035a7a3b2f02c91ba32eca1ea6d8ae1c02519e524e5bf83ecf2ec` |
| `options-catalog-review.md` | `32870831c237b6de33bd01835a22c9053e0cc18095b603e8081411cb3db59ecd` |
| `options-independent-review.md` | `e64678346797b68644fd349b856a8b237e7146522e6f47840dafcdb4791b0555` |
| `gex-published-board-extract.json` | `af00367aeb4ba9fa64569eacfcac98926e5dcf46f863e1e99348d5d81938972e` |
