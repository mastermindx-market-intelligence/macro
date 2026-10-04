# Crypto science R9 — fixed-clock advance warnings, quiet periods and alarm burden

Existing WS:CRYPTO-INTELLIGENCE / operation crypto-vector-r2-20260926-sol-001 / draft Macro8050. Current Chairman Continue commissions the already-specified pre-break scientific unit. Baseline27b97a4ff4807656e66df3707664300953d72221. Protected Mastermind39d0bfd55bf19c2c27322ec691189e63df201c15; INDEX94d1af402598894372858793a5b1931019c5fa77; compatible1.0.1/bootstrap1; same-pin COLD_START/ACTIVE_EXECUTION/WEB_CEO_DELEGATION/CLOSEOUT read. Same clean M2 Studio Direct sparse workspace and branch; no pending R9 or scientific process at recovery. R8fences36541041201passed,CI36541041357still running. No merge/deploy or rerun of R8. Optional diagnostic previously refused in R8 is not retried.

## Goal and principal choice

R4–R8 sampled only already-observed72h breakdowns. They cannot quantify warnings in quiet markets or before the first break. This experiment changes the OBSERVABLE sampling population, not the old rules to make their results look better. Can a fixed-clock price model warn of an adverse next-day path BEFORE an existing breakdown, with acceptable alarm burden and economic protection? Direct work is PRINCIPAL_JUDGMENT for prospective sampling, matching, target semantics and interpretation. No external worker/reviewer or independent acceptance is implied. Routine reversible in-scope research does not require another administrative approval; live-policy promotion still requires independent review and fresh issuance evidence.

No production engine/config/collector/source/gate/UI edit, new data/model subscription, signed-flow splice, calibration/ridge tuning, new trade/alert/forecast runtime owner or automatic wake. R1–R8 are immutable references. Data snapshot ends September2026 and every historical era is already used research, not an untouched test.

## 1. Population is chosen without knowledge of future events

Enumerate EVERY UTC six-hour issue time (00/06/12/18) from the first through the final source time. Use only the completed hour starting issue−1h and earlier. Keep rows with absent history, unknown target or incomplete future outcome with explicit status; never drop a clock time because nothing subsequently happens.

A pre-break watch is eligible only when all of the preceding24 COMPLETED hourly D0 states are known and none is true. D0 is the existing R4 close-below-prior72h-low definition, including its original data/sigma completeness guard. This excludes ongoing/recent observed breakdowns using PAST information only. Unknown past D0 is unknown, not no-break. There is no future-survival filter. Report calendar row counts, known/pre-break/recent-break/unknown counts and monthly coverage separately.

Reuse the eight R8 contemporaneous features at this completed hour: volatility-scaled1h/6h/24h/720h returns, distance from previous72h low, recent-low progression, log volatility and the already-available incumbent daily target. Do not use action-price drift, future allocation or resting-order-book claims. The reused price source includes unsigned volume, but R9 does not add it as a predictor. Training/issuance requires the original721complete hourly price observations and known target; older normal clocks remain visible as insufficient-history rows.

## 2. Forecast target and horizon

Action reference=issue+lag hours, lag1primary/6sensitivity. Target: price hits−5% BEFORE+3% during next24h from that reference opening price. Use original R4 opening-gap-first, otherwise unordered same-OHLC-both-barriers=ambiguous; neither is completed negative, ambiguous/censored is UNKNOWN. Require complete24hour path plus terminal OPEN only; do not use the terminal hour's later high/low/close. Label publication maturity is end=action+24h; even early barrier touches retain this conservative full-horizon maturity. Source collection/publication timing is still an unproven real-world assumption; execution prices are idealized stored opens, not achieved fills.

The primary target is a future PRICE PATH from the watch's own action reference, not proof a72hbreak will precede it. Event-recall matching below is an additional evaluation object and must not replace this label or manufacture its base rate.

## 3. Frozen forecasting methods and chronological fits

Only two forecasts: RECENT_RATE and PRICE_LOGIT. Quarter fits from2018Q1onward. Train on all earlier pre-break rows with original features finite, mature binary target, issue<quarter and end+24h embargo STRICTLY<quarter. Minimum1000examples,30positive,300negative; no lowering if sparse. All observations unweighted for logit. Standardization means/scales from training only; clip+/-5; reuse exact R6 logistic objective with fixed mean-logloss L2penalty.05, unpenalized intercept and unchanged optimizer. No upsampling, class balancing, nonlinear expansion, alternate hyperparameters or feature selection.

RECENT_RATE uses the SAME training cohort with fixed365day half-life weights and one positive/one negative pseudo-observation: (sum(w*y)+1)/(sum(w)+2). It is a proper-score comparator, not supposed independent alpha. Price fit failure makes both methods unavailable for paired scoring. Retain all fit counts/indices/statuses and optimizer results. No new posterior recalibration in R9.

Score both forecasts on identical eligible mature clock rows with Brier/logloss/AUC/average precision/mean probability/event fraction. Average precision uses exact ties, not trapezoid interpolation. Show fixed bins[0,.025,.05,.1,.2,.4,1]. Adjacent24h forecast windows overlap; clock rows are NOT independent trials. Periodsall2018+,2018–2019,2020–2023,reused2024+. Same90calendar-day-block1000resampling/seed20260928 used previously; report paired Brier difference and interval, not binomial confidence over overlapping rows.

## 4. Warning issuance before observing any future outcomes

A warning begins when the current pre-break/feature/training-qualified forecast is>=0.10. Threshold fixed before outcomes; no quantile/threshold grid. Separate streams for two methods and two lags. Once issued, no new warning until its fixed action+24h endpoint (no extension on repeated high scores); a new warning may begin exactly at/after expiry on the next eligible clock. Unknown subsequent features do not reset cooldown or retroactively cancel an issued warning. Do not require target maturity, economic input availability or a later break when issuing.

Report raw high-score clock counts, de-duplicated warnings, complete/ambiguous/censored outcomes, lower-first fractions, missed positives at the clock level (as diagnostic only), and alarm/false-window-alarm counts per actual month. False-window-alarm means a warning with completed upper-first/neither outcome, not necessarily an unprofitable trade. Unknown is not false. Exposure-adjusted month denominator is eligible scored-watch-clock count*6h/(24*30.4375); this is equivalent observed watch time, not all calendar hours. Also show calendar months and coverage; do not use outages to claim quiet/safe periods.

## 5. Strict advance warning of damaging breakdown EPISODES

Reuse ALL588R4D0parent onset identities from unchanged R8accounts, independent of the new clock forecasts. No new crisis-picking. For each lag, call the same−5/+3over24h outcome from break-availability+lag. Damaging events are mature lower-first cases; ambiguous/censored stay separately counted. The low-hit hour is a time interval: conservative confirmation at its end (opening gaps are still labeled by that bar interval for this diagnostic).

A warning may match a damaging event ONLY if issued within24h BEFORE break availability, action reference is strictly before break availability, and the event's downside-confirmation timestamp is<=the warning's own expiry. Thus a late recognition of an ongoing break is never branded advance warning, and a much later crash is not credited to an expired warning. One warning matches at most the earliest such event; one event is credited at most once, with earliest eligible warning in chronological order. Cooldown already prevents warning-window overlap within a stream.

Report all mature damaging events in evaluated periods, how many had at least one model-qualified PAST pre-break watch time capable of meeting these same temporal conditions, matched count/recall against ALL events and conditional recall against supported events. Report median/range issue-to-break lead and action-to-break lead, not time measured backward from a hindsight peak. No claim that all market declines are represented by the D0catalog. Counts are distinct episodes, not adjacent hourly positives. Nonmatched warnings may still satisfy their own price-path target; report that distinction instead of calling them contradictory.

Event matching and resulting leads are outcome-based evaluation only. They never enter training features, warning issue/cooldown or action selection. All candidate events and exclusion reasons remain in events.csv/event_matches.csv.

## 6. Economic consequence of acting on warnings

For each issued warning with complete24h price and incumbent-target path, compare following the corrected incumbent against switching to cash at the warning action reference, holding cash24h and restoring the incumbent's terminal target. Start from the same incumbent exposure at action. Original R4 self-financing target-change/dynamic-weight recurrence;0/10/25bp one-way costs; same hourly-open marked drawdown convention. Warnings do not change with cost; costs here are accounting sensitivity, not a new trained policy per cost. Missing paths retained. No new live emergency veto or sizing.

Report per-warning cash-minus-incumbent return, loss-avoidance vs missed-rebound sums, turnover, observed exposure including alreadycash cases, marked drawdown/exceedance counts, and declared research utility delta=return_delta+reduction in max(drawdown−5%,0). Five-percent is the old research objective, not user risk consent/guarantee. These event accounts are nonoverlapping within each method stream but reset equity; averages are NOT annualized continuous portfolio results.

Threshold probability quality, alert burden, incident recall and economic gain are separate. A model can predict events yet cause costly false exits; simply warning less can lower apparent drawdown. Do not force RECENT_RATE to emit warnings if below the fixed threshold, or treat its zero warnings as perfect precision. No out-of-scope economic oracle, parameter sweep or post-hoc positive subgroup selection.

## 7. Implementation, verification, persistence

Architecture: one research-only study module research/crypto_science/r9_prebreak_study.py using existing R4/R6/R8 helpers; existing shared scientific test file tests/test_btc_impulse_falsifier.py is appended, not rewritten or duplicated; derived outputs under research/crypto_science/r9/. No new CI runner/dependency. Vectorize feature calculations only if independently checked against the exact R8per-observation helper; no semantic shortcuts across missing hours.

Ordered steps: commit this protocol before outcomes; RED tests for fixed-clock full enumeration, past-only pre-break filter, feature-prefix invariance, label maturity/ambiguous bars, minimum/strict quarterly fences, future-label-independent cooldown, one-to-one matching and strict positive lead, common account costs and undefined zero-warning precision; implement/GREEN; commit candidate and same AgentOS in-turn checkpoint BEFORE study; execute once; independently re-express feature/label/training/score/issuance/matching/account arithmetic; complete existing Crypto/Vector/science suite, source-claim/compile/diff checks; write all results and limitations, immutable evidence manifest, cumulative DEC/WS checkpoint and remote readback.

Hash-check55inherited input identities/18gates plus all R1–R8evidence and inherited source/config bytes before/after. Preserve old test file as exact prefix. No raw-price/parquet/credential/font publication. Independent arithmetic in this session is NOT independent scientific review. Signed-flow semantics, actual release-time/rights parity, external review and forward-issued evidence remain mandatory before promotion. The frozen research completes an advance-warning comparison, not the overall Crypto/Vector mission.

Method reference: official scikit-learn precision-recall and average_precision_score documentation (retrieved2026-09-29), https://scikit-learn.org/stable/auto_examples/model_selection/plot_precision_recall.html and https://sklearn.org/stable/modules/generated/sklearn.metrics.average_precision_score.html . Defines rare-event precision/recall and noninterpolated average precision; not an empirical efficacy claim. Use existing installed code/numerics without package installation.
