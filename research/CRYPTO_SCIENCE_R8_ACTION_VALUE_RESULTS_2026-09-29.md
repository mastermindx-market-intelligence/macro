# Crypto science R8 — earlier decisions help selection modestly; timing alone is not the missing edge

Date2026-09-29. Existing WS:CRYPTO-INTELLIGENCE, operation crypto-vector-r2-20260926-sol-001, draft Macro PR8050. R7 baseline4409729ed99f62e0f2127798ffc234953fb8f0e9. Preregistered before new outcomes:89b6876ba0937691270b7b042427ea6fc4c2e042. Tested implementation committed before computation:ede102e5eb9d83b4d13ef0f22b12148d72d433d5. Research/tests/continuity only; no production model, config, collector, gate, UI, alert, trade or live forecast changed.

## Executive finding

R8 tests a different question rather than another probability calibration: how much risk is still avoidable at the actual decision time, and can a model predict the economic value of a protective action directly? It compares the earliest completed-breakdown observation with a six-hour later observation on the SAME parent events and common endpoint.

Most large marked losses in this event set are not already inevitable by six hours. Hypothetically moving every account to cash at that later point prevents36of43subsequent>5%marked-drawdown cases. But indiscriminate exits lose money on average because rebounds and costs matter. Acting sooner expands a hindsight opportunity envelope, while blanket early exits sacrifice more return than later exits. Neither speed nor a larger theoretical opportunity is itself a predictive edge.

A small direct return/drawdown-value model selects early exits better than its late version on average, but the paired interval includes no improvement. The early model has slightly positive full-cohort protection utility and negative mean return, then negative return AND utility in the reused2024+ period. Forecast error generally fails to improve over simple historical-mean forecasts. No policy or predictive-confidence promotion is justified.

## 1. Recovery, scope and frozen experiment

Current protected Mastermindf91847688f8126511c854ab253cd5c3cb67baa4e/Skillpack1.0.1/bootstrap1. Incumbent M2 Studio Direct workspace was clean at the R7 remote head; no R8 or active science process. R7 exact CI36530173125 and fences36530172600 succeeded. Draft PR mergeable=false at recovery remains a separate integration/release matter; no merge/rebase or writer displacement.

We retain all588original R4 D0breakdown parents, source hashes and corrected incumbent targets. A D0observation becomes available only after the hourly candle closes below its preceding72-hour low. Landmark0 is that completed candle's availability; landmark6 follows six additional completed hours. One-hour action delay is primary, six hours is sensitivity. Both policies share the original24h account endpoint and restore the same incumbent target. No later market survival, model score or price outcome reselects the early parent population.

This is an EARLIER decision point on the same sample, not an independent new market population and not a pre-shock warning. The typical earliest signal already follows a decline. The unchanged snapshot ends inSeptember2026; no result is a current market recommendation.

Costs0/10/25bp one way, hourly-open reference actions, inventory drift, target-change trading and missing-price abstention preserve previous research semantics. Hourly marks do not capture every intrahour low, slippage, order-book impact or unavailable venue execution. No provider data was joined or repaired. Actual signed derivatives flow remains excluded for unqualified measurement/publication semantics, and no under-supported recovery model is forced into a fit.

### From event probability to action value

Instead of predicting a binary5%-before3%event then assigning average class payoffs, the new model directly estimates two continuous targets:
- dr: cash-policy return minus incumbent return over the common account;
- dx: reduction in drawdown beyond a5%marked-loss allowance.

A fixed two-output ridge model uses eight quantities observable by the decision issue: volatility-scaled1h/6h/24h/720hreturns, distance from preceding72hlow, progression of recent lows, log volatility and the incumbent TARGET already available then. It never sees the future action price, the future drifted exposure or a future model target. These correlated price transformations are not eight independent causal sources.

Each quarter fits on its own prior observations whose complete account end plus24h embargo is strictly before the fit. Minimum80examples and15positive/15negative return differences; zero-gain cases remain in training. Training-only means/scales, clipping+/-5standard deviations, fixed mean-loss ridge0.05, unpenalized intercept. No hyperparameter selection, new volume filter or outlier deletion. A historical-mean model is the matched simple comparator. Current outcomes affect scoring only, not action issuance.

The primary protection preference stays `du = dr + dx`, with5%drawdown allowance and20bp permitted model-estimated return sacrifice. Penalties0/2remain sensitivities. These are experimental loss preferences, NOT approved user risk tolerance, stop-loss levels or hard capital guarantees. Ridge outputs are expected marginal values, not probabilities. Scikit-learn's official ridge objective and NumPy's solver documentation support the numerical contract, not empirical profitability [1–2].

## 2. How much damage has already happened?

There are586complete primary-delay account paths among588parents. Before the earliest issue, the median known24hBitcoin return is **−3.12%**. That prior decline is not a loss the present signal predicted or avoided.

From the common account origin onward:

| Full586parent diagnostic,1h delay/10bp costs | Act at earliest issue | Act six hours later |
| --- | ---: | ---: |
| Accounts already>5%down BEFORE action |0|7|
| Incumbent accounts>5%down over full window |43|43|
| Accounts still>5%down if switched to cash |0|7|
| Mean current incumbent drifted exposure before action |43.56%|43.42%|
| Accounts exactly in cash at action |120|110|
| Mean cash-minus-incumbent net return |−0.1481pp|−0.0756pp|
| Mean cash-minus-incumbent protection utility |+0.0157pp|+0.0770pp|

Pre-action0at the earliest point is by construction of the event account. It does not erase the price decline before that account began. At the later point, the recorded mean pre-action account drawdown is0.595%, with mean net account change+0.073%: many paths rebound even though some have deep early losses. Max drawdown and endpoint return measure different aspects and must not be added or substituted.

The six-hour cash policy prevents36of43large marked-drawdown cases while retaining the seven already experienced. Thus the prior modelling failures cannot be explained solely by saying all losses happened before the later landmark. The research challenge is selecting those damaging continuations WITHOUT exiting the many rebounds. Prior exact cash exposure is also relevant: a raw BTC selloff does not imply identical losses for an incumbent that holds partial exposure or cash.

On already-used2024+,165complete parent paths contain only THREE incumbent>5%drawdown cases; none is already beyond5%before the six-hour action. Blanket cash removes all three but loses return and declared utility on average at both landmarks. Do not extrapolate those three prevented outcomes into a high-confidence crash-prevention statistic.

### Earlier choice has a larger hindsight opportunity, not a guaranteed better policy

The restricted hindsight envelope picks the better of cash or incumbent for EACH episode at a FIXED landmark, using its future outcome. It is impossible to trade as shown and is not the global best strategy or an optimized exit timestamp.

Its mean utility gain is0.6833pp at the earliest point versus0.5947pp six hours later. The paired early-minus-late envelope difference is0.0886pp, descriptive block95range[0.0395,0.1458]pp. That says an all-knowing selector would find somewhat more value earlier in this declared choice set. It does not establish an observable signal capable of capturing it.

In contrast, unconditionally exiting earlier rather than later REDUCES mean utility by0.0613pp, range[−0.1619,+0.0285]pp. Faster is useful only when the selection is sufficiently accurate; it can otherwise increase missed rebounds.

## 3. Direct economic-value forecasts: earlier is modestly better, not dependable

The study generated420quarter fits,396eligible and24insufficient. It records6,072candidate prediction scenarios and30,204policy scenarios, repeating588parents across landmarks, costs and delays—not tens of thousands of independent shocks.

For primary1h/10bp, the early model issues420forecasts,418with complete account outcomes;67lack price-feature history and19lack enough training. The six-hour model issues419,418with complete accounts;68lack feature history and19lack training. Support begins2018-07-10. Both primary scored sets happen to intersect at the same418parents, allowing a clean paired timing comparison. Early issuance did not depend on later feature availability; the intersection was formed only for evaluation.

| Primary unit-penalty model policy,418paired accounts | Early mean-only | Early ridge | Six-hour mean-only | Six-hour ridge |
| --- | ---: | ---: | ---: | ---: |
| Cash selections |418|204|418|223|
| Economically different accounts |352|184|351|206|
| Net return difference vs incumbent |−0.1373pp|−0.0197pp|−0.0932pp|−0.0832pp|
| Protection utility difference |−0.0457pp|+0.0249pp|−0.0075pp|−0.0452pp|
| >5%marked-drawdown cases, incumbent19 |0|10|3|9|

The historical-mean baseline chooses cash throughout these primary issued quarters because its TRAINING mean protection estimate is positive within the expected-sacrifice floor. It was not told the test losses. Its poor recent realization is evidence of base-regime/mean instability, not a strong benchmark whose defeat automatically proves an edge.

The early ridge policy's mean protection utility is+0.0249pp with interval **[−0.1008,+0.1666]pp**. Its mean return is still−0.0197pp. Moving the ridge decision from six hours to earliest observation yields+0.0701pp mean utility on the paired418accounts, interval **[−0.0353,+0.1986]pp**. Both intervals span zero. We retain that promising direction without promoting it as reliable immediate de-risking.

The frequency-matched selection diagnostic is+0.0416pp for early ridge, interval[−0.0414,+0.1435]pp, and−0.0199pp for the later model. This expected uniform-selection comparison holds quarterly decision FREQUENCY, not exact notional exposure, portfolio risk or duration. It is retrospective and not an executable alternative policy.

### Recent period remains a material failure

On the same145complete2024+model accounts, early ridge selects cash77times, late ridge86times. Early net return is **−0.1213pp** and protection utility **−0.1087pp** versus incumbent. Later values are−0.1367pp and−0.1221pp. The mean timing improvement is small, with wide uncertainty. Neither policy earns live authority just because earlier is less bad than later.

Forecast quality is another constraint: on the primary full scored cohort, ridge MSE is worse than the historical-mean forecast for BOTH dr and dx at both landmarks. Early drMSE0.00030883 versusmean0.00029764; early dxMSE0.00005719 versusmean0.00004748. These are squared return-fraction units, not accuracy percentages. Directly predicting the right economic quantity does not itself make the prediction good.

In the recent early cohort, predicted average excess-drawdown reduction is0.1455pp while the realized average is0.0215pp. The model continues to overestimate protectable tail damage. This helps explain why more defensively oriented policy need not improve the declared economic objective. It does not justify adjusting the penalty or training window after inspecting this result.

## 4. Cost and delay sensitivity: retain the whole experiment

For the same unit drawdown penalty, full supported ridge-policy utility differences versus incumbent (percentage points of event equity):

| Observation landmark | Execution delay |0bp cost|10bp cost|25bp cost|
| --- | ---: | ---: | ---: | ---: |
| Earliest |1h|+0.0409|+0.0249|−0.0225|
| Six-hour observation |1h|−0.0073|−0.0452|−0.0225|
| Earliest |6h|+0.0669|−0.0139|+0.0384|
| Six-hour observation |6h|+0.0616|+0.0004|+0.0033|

The table does not nominate the best delay/cost cell. Costs change the training target and therefore the fitted model's selections, and delay can change coverage. The6h subsets are not the identical set of all1hforecasts. Favorable secondary cells cannot substitute for the primary test or erase recent-period failure. Penalties0and2, all missingness, per-year counts and leave-one-year-out means remain in the machine-readable outputs.

Model selection thresholds are still the frozen positive-expected-utility and20bp estimated-sacrifice rules. No probability confidence percentage, fitted action boundary or supposedly optimal timing was chosen from the results. The same-frequency and restricted-hindsight diagnostics remain explicitly non-executable comparisons.

## 5. What the science now establishes—and what the next experiment must change

R8 resolves a substantive uncertainty: there is remaining protection opportunity after the later landmark, so the earlier negative studies were not merely measuring a market after all damage was finished. Earlier action creates somewhat greater theoretical opportunity but also greater exposure to false exits. A direct action-value target gives a more relevant representation of the user decision than a binary barrier label, yet the current linear features/model do not reliably estimate either return benefit or tail severity.

This points to a population/information question, not permission for another grid of thresholds. AllR4-R8episodes were conditioned on an observable72hour breakdown. They cannot answer whether a system could warn BEFORE that first break, cannot estimate a false-alarm rate over all normal market hours, and cannot establish an exact cycle-top warning. A future model should not obtain an apparently early warning by retrospectively selecting only times that later break down.

The next protocol should therefore define an earlier watch population on a fixed calendar clock or an independently observable deterioration condition, keep non-events/quiet periods, and score actual lead time to a damaging episode alongside false alarms per month. It must retain episode clustering so many adjacent warning hours are not called independent successful forecasts. Keep calendar-context/pre-shock warning and conditional post-break management distinct. Include the incumbent's already-known exposure and the cost of forgone recoveries in the economic target rather than optimizing a decorative risk number.

That new question must be frozen before its outcomes or sample are inspected; none of those earlier-watch thresholds or model results was explored in R8. Independent review of the existing time/price/target/account seams remains a promotion gate, not optional prose. A genuinely qualified new input may help, but we will not relabel unsigned spot volume as absorption or assume missing signed-flow units/publication clocks are resolved. No new collector, account, forecast store or allocation plane is authorized by this research plan.

## 6. Verification and effect record

The fixed study ran once, process58078, exit0. It produced588parent identities,7,056account-scenario rows,420quarter fits,6,072prediction rows and30,204policy rows. There was no outcome rerun, changed threshold, model/label amendment or overwritten prior evidence. These scenario counts are not independent market sample sizes.

Eight initial source tests failed because the R8 module was absent; all eight subsequently passed. The complete existing research file passed57tests with42warnings. The final combined Crypto/Vector/science invocation passed **284tests,48warnings**; Python compilation, existing source-scope claim checker and git diff checks passed with exit0. Existing warning categories were not suppressed in the saved evidence or asserted fixed. No runner/dependency/new gate was created.

Independent numerical expression, by this SAME session and not an independent reviewer, checked:
-1,998valid feature observations, including strict completed-bar timing and known target availability;
-14,076cash/coin inventory paths, marked highwater/drawdown, pre-action state, turnover and economic outcomes;
-all420training memberships and396eligible ridge fits, with a separate augmented least-squares solve rather than the generating normal-equation solver;
-all6,072prediction rows and30,204policy rows, with actions chosen without eventual account results;
-all288utility summaries, opportunity anatomy, timing contrasts, forecast-error summaries, same-frequency controls and declared block intervals;
-144paired ridge-versus-mean method contrasts retained in paired_method_contrasts.json.

Verifier process61426 completed exit0. Every55input identity,18gate file and100prior evidence artifact remained unchanged, as did inherited source/config/research identities. The old scientific test file remains an exact byte prefix. No raw-parquet/price-store, credentials or fonts were published. Computation reused the current accepted research data snapshot; it did not establish real-time source-publication or execution parity.

After this complete verification, one OPTIONAL read-only command to print additional paired-method, leave-year-out and file-size summaries was refused before dispatch because the platform could not determine its safety status. It was not retried, rephrased or sent through another carrier. No result, source, account or runtime effect was uncertain from that refused print. The already verified required evidence remains preserved; no new unobserved diagnostic values are asserted here. This action-specific refusal is not described as a total source/write outage.

**Disposition:** complete this bounded timing/action-value experiment without promoting a policy. Earlier selective action is a direction worth distinguishing from waiting, but its positive full-period utility is uncertain and absent in recent data. The parent mission—reliable multi-horizon Crypto intelligence, understandable design and production-quality risk decisions—remains incomplete. Independent review, historical availability/rights, fresh issued-forward evidence and live acceptance remain required.

[1] Official scikit-learn Ridge documentation, objective and multioutput support: https://scikit-learn.org/1.8/modules/generated/sklearn.linear_model.Ridge.html . R8's explicit mean-loss penalty maps to total-loss alpha=.05*n; docs are methodological support, not empirical efficacy.
[2] Official NumPy solve documentation: https://numpy.org/doc/stable/reference/generated/numpy.linalg.solve . The generating ridge solve uses existing NumPy; verification independently uses augmented least squares. No package installation or market/account API request occurred.
