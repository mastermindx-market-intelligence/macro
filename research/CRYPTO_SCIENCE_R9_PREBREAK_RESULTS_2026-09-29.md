# Crypto science R9 — advance warnings on an outcome-independent clock

Date2026-09-29. Existing WS:CRYPTO-INTELLIGENCE, operation crypto-vector-r2-20260926-sol-001, draft Macro8050. R8baseline27b97a4ff4807656e66df3707664300953d72221. Protocol3821bcdade52648ea1c18667b538a032c4c1808c committed before new outcomes; tested study candidate6d23d1b5f9fbd1034c44523fd03c74ec66b8f9e0 committed before execution. Research/test/continuity only; no production model, collector, source gate, UI, live forecast, alert, trade or allocation changed.

## 1. Why the sampled population changes

R4–R8 answered what to do after an observable72hour breakdown. They did not contain ordinary observation times that never became breakdowns, and therefore could not quantify a genuinely anticipatory warning's false alarms across calm markets. R9 changes that sampling question rather than searching more thresholds on the same event-conditioned episodes.

The study enumerates every00/06/12/18UTC clock time in the existing hourly source range. A watch is pre-break only if every prior24completed hourly D0state is known and none is true. Recent breakdowns are retained as excluded-from-watch observations; missing history is unknown, never evidence of safety. Price/known-target features require their original721hour continuity. No clock time is selected because a future event happens or removed because nothing happens.

The two frozen forecasts are a regularized continuous-price model and a recency-weighted historical event-rate comparator on the identical training population. Quarterly fits use completed outcomes plus a strict24h embargo, training-only scaling and fixed model settings. Minimum1000observations,30positive and300negative outcomes cannot be relaxed after results. The price model reuses the eight R8contemporaneous price/known-target measurements, not actual signed flow, order-book absorption or a new causal source. No calibration or threshold sweep is performed in R9.

The target is a future24h path from the assumed action-opening price: a5%decline before a3%rise. One-hour action delay is primary and sixhours sensitivity. Opening gaps determine ordering when observable; a both-barrier candle with unknown order is ambiguous, not a scored negative. A complete neither-hit path is negative; missing/incomplete windows are unknown. The terminalOPEN is needed, not the terminal candle's later high/low/close. These stored-price reference actions do not prove executable crash-time fills or actual publication latency.

## 2. Four distinct questions are kept separate

**Clock-level prediction:** Brier/logloss, ranking and average precision on identical mature eligible clocks. Adjacent24h targets overlap, so tens of thousands of rows are not independent market crises. Calendar-block uncertainty is retained. Average precision uses tied score groups and noninterpolated recall increments, not an optimistic trapezoidal approximation [1].

**Issued-warning burden:** fixed forecast>=10%, followed by no repeat until the warning's original action+24h expiry. Future observations cannot shorten, extend or erase the warning. Its own target can hit, fail or remain unknown. False-window warnings are completed negatives, not necessarily losing trades. Exposure-adjusted month counts use only observed eligible scored clocks (6hours each); calendar coverage is separately visible, so outages are not silently credited as calm periods.

**Episode-level advance warning:** the unchanged588R4D0catalogue supplies a distinct evaluation target. A damaging breakdown must have a mature lower-first outcome. A warning earns credit only if it is issued within24h BEFORE that breakdown, its assumed action occurs strictly BEFORE the break, and the damage confirmation falls before the warning expires. One warning can match at most one event and each event is credited once. Both all-catalogue recall and coverage-conditional recall are reported; unsupported events do not disappear from the all-event denominator. Lead time is measured to the observable break, not backward from a hindsight high.

**Economic protection:** at each issued warning, compare the corrected incumbent with a24h cash switch followed by restoration. Costs0/10/25bp are applied to the same warnings, unlike earlier experiments where costs changed fitted action selections. Report return difference, missed rebounds, avoided losses, turnover, already-cash cases and marked drawdown. The inherited5%-excess-drawdown preference is an experimental utility, not user risk consent, a guaranteed stop or account-specific advice. Reset per-warning accounts are not a continuous annualized portfolio.

An alarm can satisfy its own price-path target without matching the strict D0incident definition. That is not an inconsistency: these measure different questions. Conversely, an advance match does not prove the exact peak was identified or an attainable profitable exit occurred.

## 3. Implementation and evidence discipline

The prior optional R8diagnostic-print refusal remains fenced; it was not repeated to recover extra R8statistics. This is a new predeclared research action on the same permitted carrier. The initial R9unit tests failed because its module did not exist. A subsequent implementation attempt imported scikit-learn, which is absent in this environment; no package was installed. The documented average-precision formula is instead expressed with installed NumPy, with an additional initially-failing tie/zero-positive test. All initial outcomes are retained. A publication precheck caught trailing whitespace in the dependency-failure log before the study started; only diagnostic line-ending whitespace was normalized, not results or source semantics.

The study implementation was committed before any empirical calculation. The planned verifier uses an independently expressed array-based feature/label computation, explicit cash-and-coin inventory accounting, logit optimum gradients and separate warning/event-matching/statistic calculations. That is SAME-session numerical verification, not independent researcher approval. Complete scientific findings and verification receipts follow below; the parent mission is not assumed complete merely because this report exists.

## 4. Calendar support and proper forecast scores

The fixed study contains31,372clock/lag rows (15,686unique clock times repeated under1h/6hdelay),70quarter fits,25,526issued-period candidate rows and1,176catalogue event/lag rows (588unique D0onsets). Neither scenario count is an independent market sample size. All70fits meet the fixed minimum; this does not make source-observation gaps disappear.

For primary1h forecasts from2018onward, the12,763clock rows divide into8,879forecast-qualified,2,507recent-break,1,130price-history-unknown and247past-context-unknown cases. Among qualified forecasts,8,838have mature unambiguous targets;41are not scored. There are828positive overlapping clock targets (9.37%). They must not be confused with the smaller number of distinct damaging D0events.

| Same8,838primary eligible mature clocks | Recent event-rate | Price logit |
| --- | ---: | ---: |
| Mean forecast |11.14%|10.96%|
| Actual target frequency |9.37%|9.37%|
| Brier, lower better |0.084180|0.080970|
| Log loss, lower better |0.305335|0.291311|
| ROC AUC |0.6096|0.7105|
| Noninterpolated average precision |0.1214|0.2097|

The paired Brier difference is **−0.003210**, with descriptive90calendar-day-block95interval **[−0.005411,−0.001303]**. Thus the price features add retrospective discrimination/proper-score value over this simple same-cohort rate baseline across the full declared period. AUC0.71 is NOT71%accuracy, and average precision0.21 is NOTthe realized precision of the fixed10%warning threshold. The repeated, already-used historical data and unverified source-publication assumptions still prevent a fresh predictive-skill acceptance claim.

The interval also favors the price model separately in2018–2019 and2020–2023. Reused2024+does NOTshow the same proper-score advantage:

| Same3,006recent mature clocks /145positive targets | Recent event-rate | Price logit |
| --- | ---: | ---: |
| Actual target frequency |4.82%|4.82%|
| Mean forecast |6.83%|8.80%|
| Brier |0.046053|0.046514|
| Log loss |0.194354|0.197262|
| ROC AUC |0.5996|0.6732|
| Average precision |0.0624|0.0983|

The recent paired Brier difference is **+0.000461** (worse), interval[−0.001204,+0.002030]. Ranking remains better than the rate comparator, but risk level is overstated and probability losses do not improve. A better ordering of observations and a well-calibrated probability are different claims. We do not re-select a threshold or calibration offset on these outcomes.

## 5. The fixed warning threshold produces too much non-event activity

At the unchanged>=10%threshold and prospective cooldown, primary price forecasts produce4,557above-threshold clock observations but only1,114issued warnings. Repeated high scores do not restart/extend the warning; no future outcome is consulted in de-duplication.

| Primary1h price-warning stream | Full issued period | Reused2024+ |
| --- | ---: | ---: |
| Warnings issued |1,114|228|
| Mature/unambiguous own-window outcomes |1,109|228|
| Own−5%-before+3%target reached |156|20|
| Completed own-window non-events |953|208|
| Unknown own outcomes |5|0|
| Observed own-window precision |14.07%|8.77%|
| False-window warnings per equivalent observed-watch month |13.13|8.42|

These rates use72.59equivalent full-watch months in the complete period and24.69in the recent period, compared with105and33calendar months represented. They count only eligible scored watch clocks,6h each, rather than silently treating missing or ongoing-break hours as observed safe opportunity. For notification interpretation, calendar monthly counts and eligibility are retained in monthly_burden.csv; this is not a claim that users actually received messages or that the system ran continuously.

The rate-only method issues1,220warnings/1,212scored,152own-target hits and1,060non-events over the full period:12.54%precision and14.60false-window warnings per equivalent observed-watch month. The price model modestly reduces alarm burden and improves this observed hit fraction, but still produces many non-events. In the recent period, the rate-only forecast stays below10%and emits no warnings; its precision is UNDEFINED, not100%and not a forced zero-precision trading rule.

A completed non-event is not necessarily a losing trade, and an own-window target hit does not prove a feasible profitable exit. This is why the economic comparison is not inferred from the hit-rate table. Nor should a10%estimated event probability be marketed as a high-confidence immediate-sell command.

## 6. Advance-to-break recall exposes both modelling and coverage limits

There are78mature damaging primary-lag D0events in the evaluated2018+catalogue. Only37had even one usable pre-break model clock satisfying the strict positive-action-lead and warning-expiry conditions. Both the price model and the rate-only comparator match20events—not proof that the matched sets or causal information are identical, and not a new20-out-of20success claim.

For the price model, catalogue recall is **20/78=25.64%**; supported-event recall is **20/37=54.05%**. Report BOTH. Among those matched events, median observation lead is9h and median action-reference lead8h; observation lead ranges2–20h. This is advance notice relative to the defined first72hbreak, not proof a market peak was predicted before any decline.

In reused2024+, there are15damaging catalogue events, of which5have qualified watch coverage. Price forecasts match only **one**: **1/15overall recall**, **1/5supported recall**. That one warning's observation lead is3h and action-reference lead2h. A median from ONE match is an example, not a reliable lead-time distribution. The rate-only stream has no recent warnings and matches none.

Why is coverage so limited? A separately labeled POST-RUN DESCRIPTIVE audit decomposes the already-frozen support predicate; it does not change selection, outcomes, targets or results:

| Why a damaging event cannot be covered by this experiment | Full primary catalogue | Recent primary catalogue |
| --- | ---: | ---: |
| No issued clock meets BOTH strict pre-break action and damage-before-expiry timing |18|5|
| No past-qualified pre-break context at those times |12|4|
| Price or incumbent-target feature history unavailable |11|1|
| Supported under all original gates |37|5|
| Total |78|15|

The first row combines the chosen6hclock, assumed execution lag and24hexpiry; it is NOTproof every such event happened too fast. The second includes recent/unknown prior-break context, not a failed forecast on otherwise eligible observations. The third is real measurement support, not low model confidence. These limitations belong in the unconditional denominator rather than being removed to report54%recall alone.

Own-window precision and catalogue recall are intentionally different objects.156own-window hits need not equal20strictly anticipatory D0matches. A large fall can meet the warning's price-path target outside the catalogue's exact onset/ordering definition; repeated/ongoing market damage and expired lead windows are not relabeled as advance predictions.

With6hassumed execution delay, the price stream has1,111warnings/1,104scored,144own-window hits,12strict matches among83damaging events (33supported). In the recent6hcase there are220warnings/219scored,17own hits and ZEROstrict matches among19damaging events (4supported). Delay changes the event reference prices, populations and eligible lead window; do not claim these are identical primary events under merely a shifted alert timestamp.

## 7. Acting on every warning still gives up too many rebounds

At1hprimary delay and10bpone-way costs,1,109price warnings have complete paired account paths.237begin with the incumbent already in cash;910produce an economically nonzero difference. The hypothetical cash policy removes49>5%marked-drawdown cases in this selected sample, but mean net return versus following the incumbent is **−0.1419percentage points per warning**, with block95range **[−0.2702,−0.0194]pp**.

The mean reduction in excess drawdown is+0.1123pp, insufficient to offset the missed return under the inherited unit-penalty protection objective: mean utility **−0.0296pp**, interval[−0.1422,+0.0909]. Removing observed tail losses by holding cash is not itself forecasting skill or superior economic policy.

In the recent228accounts,61startcash,175are economically different. Cash removes11incumbent>5%marked-loss cases but costs **−0.2222ppmean return**, interval[−0.3990,−0.0447], and **−0.1505ppmean utility**, interval[−0.3458,+0.0428]. There is no evidence here for elevating this warning into an accepted emergency allocation veto.

Costs do not alter which warnings are issued in R9. The same fixed warning stream is marked under all fee assumptions:

| Price-warning cash policy / primary1hdelay | Full mean return / utility, pp | Recent mean return / utility, pp |
| --- | ---: | ---: |
|0bp|−0.0560 / +0.0562|−0.1353 / −0.0636|
|10bp|−0.1419 / −0.0296|−0.2222 / −0.1505|
|25bp|−0.2706 / −0.1582|−0.3524 / −0.2806|

All6hdelay results also retain negative mean return; at10bp the full mean return/utility are−0.1562/−0.0579pp and recent−0.2532/−0.1857pp. No favorable cost/delay cell is substituted for the primary assumption. Per-warning accounts use reset initial equity and do not describe annualized compounded performance.

The rate-only warning policy has full mean return−0.1376pp and utility−0.0442pp on its1,213complete accounts. Its warning times differ from the price model, so comparing those two mean utilities is NOTa paired claim of incremental selection skill. The proper-score comparator above is paired on identical clocks; the policy table is not.

## 8. Scientific ruling and the next material dependency

**No live warning or protective-allocation promotion.** The pre-break population contains genuine retrospective price-ranking information relative to a simple rate estimate. That is stronger evidence of advance-to-event discrimination than a model tested only after a breakdown. But its fixed operating point has many own-window non-events, recent probability overstatement, limited strict pre-break event coverage and negative net-return protection. The recent era does not reproduce the full-period proper-score gain. Selectively reporting AUC0.71,54%supported recall or all49selected drawdowns removed would materially mislead users.

The conclusion is not that advance warning is impossible or that useful data cannot improve the system. The new capability is a denominator-honest assessment that can reject an attractive warning before it becomes a noisy dashboard or a costly emergency exit. A forecast with some ranking power may still be useful as research context after review, while lacking authority to size a portfolio or send urgent alerts.

This batch also separates model weakness from observation-design limits. Many catalogue incidents have no qualified clock satisfying the required lead/expiry constraints. A6hschedule cannot be represented as continuous protection, and an observation after a first break belongs to conditional management rather than anticipatory warning. These are different jobs; we should not rescue a pre-break model by silently switching its successful cases to post-break detection.

The next dependency is a source-qualified, independently reviewable information increment, not another unregistered choice of threshold on this same clock sample. Existing review boundaries are captured in research/crypto_science/r9/REVIEW_BOUNDARIES.md without claiming a reviewer has accepted them. Resolve the actual instrument, units, aggregation/settlement interval, observation versus publication time and venue coverage of the existing derivatives-flow/funding inputs using their current collectors and primary provider contracts. Keep their genuinely short supported history separate from the long price history; do not splice it, rename unsigned spot volume as absorption or infer dealer inventory.

Once one such distinct input is qualified, freeze a coverage-matched study of its incremental warning information and economics against R9's exact calendar baseline, with explicit no-data states and unchanged objective. If a faster observation cadence is studied, it needs its own frozen clock and event matching, not a retroactive redefinition of R9. Continue to distinguish hazard ranking, calibrated probabilities, notification burden and policy utility. Independent review and new forward-issued evidence through existing owners precede any promotion.

A separate review of the warning population, first-passage definitions and opportunity-cost assumptions may identify a scientific flaw; that must be corrected transparently with prior outputs preserved. It is not permission to search until a profitable curve appears. The broader scientific and product mission remains active and incomplete.

## 9. Completed verification, effects and reproducibility

The fixed market study ran ONCE, process44541, exit0. The earlier attempted compound publication command stopped at a trailing-whitespace check BEFORE any study process started; it is not an outcome rerun. The dependency import failure was also pre-study. No outcome/threshold/feature/label amendment or result-driven parameter change occurred. The post-run coverage review is explicitly descriptive and leaves the original outputs untouched.

Nine R9coretests pass after the recorded RED failures. The unchanged existing scientific test prefix plus additions passes66tests,42warnings. The final combined Crypto/Vector/science invocation passes **293tests,48warnings**. Python compile, source-scope claim checker and diff checks pass. Existing deprecation/temporary browser cleanup warnings remain; no warning-free claim is made. No CI job, installed dependency or production source file was changed.

Independent numerical expression, in the SAME session rather than a separate reviewer, completed as process99287 exit0. It verifies:
-31,372calendar/lag records and26,508finite feature observations via direct arrays and strict past-only availability, independently of the generating vectorized formulas;
-all own-window label categories/maturity and the1,176catalogue event/lag records;
-all70quarter training memberships, minimum/embargo gates, scales, fixed logistic optimum gradients and recent-rate calculations;
-all25,526prediction rows and4,665prospectively issued warnings, including cooldown that ignores future labels;
-all65strict advance event matches across method/lag scenarios and each coverage denominator;
-27,840cash-and-coin inventory paths underlying the complete costed comparisons, independently of the generating target-weight recurrence;
-all probability/AUC/noninterpolated AP/reliability scores, paired calendar-block intervals, warning/false-warning/lead statistics, monthly coverage/burden and economic summaries.

These counts repeat observations across delays/methods/costs; neither65matches nor27,840paths means that many independent market incidents. The original data snapshot,55input identities,18gate files,114prior evidence artifacts and inherited source/config/research hashes remained unchanged. The preceding scientific test file remains an exact byte prefix; appended R9tests are separately hashed. No raw price/parquet, credential or font artifact is published.

Canonical output directory: research/crypto_science/r9/. The exact code/protocol/source/data identities live in results.json and MANIFEST.json. CSVs retain clock status, every prediction, warnings, all catalogue events, event matches, costed warning accounts and monthly burden. coverage_review.py/json preserve the separately labeled explanation of unsupported cases. REVIEW_BOUNDARIES.md is a requested review scope, not a claimed review receipt. Full report source is this file.

**Disposition:** complete this bounded pre-break warning experiment with NO policy or high-confidence forecast promotion. Research now measures quiet-period alarm burden and strictly positive advance-to-break lead instead of only post-break management. It demonstrates full-history discrimination, but recent overstatement, high non-event burden, coverage gaps and negative protection economics remain material. Independent review, exact live publication/rights/execution qualification, new forward-issued evidence and the broader Crypto/Vector release are still open. No model/effort switch, unattended worker, watcher, new runtime/forecast owner or live user action is implied.

[1] Official scikit-learn precision-recall and average-precision definitions reviewed2026-09-29: https://scikit-learn.org/stable/auto_examples/model_selection/plot_precision_recall.html and https://sklearn.org/stable/modules/generated/sklearn.metrics.average_precision_score.html . Methodological definitions only, not empirical evidence of efficacy. The local environment has no scikit-learn package; the exact noninterpolated calculation is implemented and independently checked with existing NumPy/Pandas, without installing a new dependency.
