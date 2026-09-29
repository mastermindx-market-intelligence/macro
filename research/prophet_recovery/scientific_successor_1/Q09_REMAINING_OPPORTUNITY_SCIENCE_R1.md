# Q09 — Remaining opportunity, first-event probability and payoff timing

**Scientific proposal and executed mathematical evidence • 29 September 2026**

Operation: `prophet-frontier-hypotheses-20260926-sol-001`; recovery: `prophet-frontier-successor-1-20260928`. Scientific-design successor reporting to parent Sol. Existing child return: Macro #6805/5861635963. Parent: #6817.

**Disposition: RECOMMEND the finite-horizon joint-event representation for the existing Q09/B10–B11 design; retain all statistical and product-promotion gates. NOT a registered experiment, trained model, native implementation, validated probability or trading policy.**

## 1. Decision and scope

The useful next science is not another review of the metadata reader. Q09 already asks whether separate payoff, adverse-tail and time-to-event forecasts improve decisions beyond stage labels. The Chairman now expressly authorizes independent science angles while the parent handles integration. This work resolves a specific ambiguity: **what exactly should a probability and a time estimate mean for an unresolved opportunity, and what can be learned when the order of target and invalidation is not observable?**

Recommendation: represent target-first, price-invalidation-first, other defined terminal-event-first, and no qualifying event by a finite horizon as one coherent distribution. Keep fixed-horizon return forecasts and executable-policy outcomes separate. Use transparent competing-event and landmark baselines before increasing model capacity. For ambiguous labels, calculate identification bounds on a paired proper-score comparison rather than inventing event order or deleting difficult cases.

This advances the existing Q09 question and its Q11 calibration interface. It does not start the empirical Q11 study, duplicate the parallel technical/options/risk seats, define new targets/stops, or add another model registry, event lifecycle, evaluator or data source. The mathematics below is a proposal to the existing owners; the prototype in the companion is a mathematical exhibit only.

### Existing sources and ownership

At Macro records commit `59d3e391691de90f45e18b9c9941551265fd2be9`, the source baseline is:

- `research/prophet_recovery/RESEARCH_ALLOCATION_2026_09_26.md`, blob `30dde5d67b2c09d45cc65010b7eda7790af00806`: Frontier A includes Q09 and expressly permits bounded hazard/competing-risk proposals.
- `research/prophet_v4/r6_fable_meta_ceo_handoff/effective/RESEARCH_DOCKET.md`: Q09 is remaining payoff/timing; Q11 is calibration/abstention; existing decisions remain with their current owners, not the old Fable wording.
- `research/prophet_v4/r6_fable_meta_ceo_handoff/effective/BUILD_PROGRAM.md`, blob `a5dcc6b2cee2b5e65a0dbde844eed074a313f1db`: B10 is Conditional Fusion/Evaluation research; B11 is the versioned qualified-head/shadow consumer.

R1/AR1–AR4 and parent acceptance #6805/5865586990 remain unchanged. In particular H1 remains C2-minus-C1/K5/H10 with its original weights, fits, inputs and 50/25/25 policy. **The bounded-score treatment below does not relax H1's strict selected-return completeness rule.** R2–R4 retain their exact source/adoption findings. The last scientific artifact before this unit is R4 `d41b008cdb2cc8a715bded1c5aa17886c60a7eb8`; no adoption or worker-liveness status was refreshed merely to fill this turn.

## 2. Four questions that must not share one “confidence” number

| Quantity | Defined question | What it does not establish |
|---|---|---|
| Endpoint return distribution | What is the original claim's return or benchmark-relative mark at a fixed future horizon under an explicit convention? | Which barrier occurred first, obtainable entry, execution price or maximum loss. |
| First-event distribution | Which predeclared event occurs first, and within how many supported sessions, from this information cut? | A profitable trade, total holding duration, or what occurs after the first event. |
| Entry-policy outcome | Does the exact native policy permit and obtain a fill, at what time/cost, and with what subsequent outcome? | It cannot be inferred from target probability for immediate hypothetical exposure. |
| Thesis/management state | What does the native owner currently say about the original case, conditions and management? | A model probability cannot create or overwrite that state. |

**Constructed counterexample.** The ordered price paths `100 → 94 → 111 → 108` and `100 → 111 → 94 → 108` both end +8%. With a fixed lower condition at 95 and upper condition at 110, one is lower-first and the other upper-first. Endpoint marks cannot label the first-event question. These invented conditions are not recommended trading levels.

Likewise, target-first probabilities alone do not determine expected return. In an illustrative event mixture with target-first 20%, lower-first 60% and no event 20%, assume conditional endpoint means of +10% and −5% for the first two groups. Let the no-event group's conditional mean be either −4% or +8%. The same event probabilities then imply −1.8% or +0.6% overall. These are assumed arithmetic worlds, not modeled financial returns. A first-event head is information, not a complete payoff model.

## 3. Define the event before choosing the model

For an existing native case and geometry version, let the information landmark be `l`. Define the next eligible observation interval using the owner calendar and actual usability cut; the forecast cannot claim an event that happened before its issuance. Let `T` be the first future qualifying event time in those intervals and `J` its cause:

- `U`: the specified original target condition first;
- `D`: the specified original price-invalidation condition first;
- `X`: a separately predeclared, source-supported structural termination that makes this particular first-event question no longer meaningful;
- `S_h`: none of U/D/X through horizon h, with the required observation support complete.

These are **absorbing categories for the first-event measurement only**, not new plan/position/issuer lifecycle states. A partial target touch need not close a native plan; an existing position may still need management after this forecast's measurement resolves. Existing owners retain those actions.

`X` must have a precise meaning before observation: for example an owner-verified cancellation of the original equity claim under the applicable specification. A trading halt, missing file, supplier outage, slow disclosure, generic plan edit, or “not on today's shortlist” is not automatically X. Different causes require different evidence. Neither a delisting label nor a new ticker by itself proves original-claim cancellation. Multi-cause ties require an accepted composite-cause definition or remain order-ambiguous; a worker cannot select the favorable priority.

A case already beyond a qualifying condition at l is prevalent/resolved for this question, not a newly predicted future success. A replacement geometry/version cannot erase the original forecast. Preserve original and current versions separately; do not continually move targets and reset the clock to excuse failure.

### Observation is a separate axis

“Neither event occurred” is a substantive observed outcome. “We do not know which occurred” is an evidence limitation. Store the distinction in the existing label/source record, with allowed event/time sets where needed. A model's probability mass is not a receptacle for source missingness.

An OHLC bar `open 100, high 111, low 94, close 105` is consistent with an upper-first path and a lower-first path. Unless an earlier qualifying open or finer, qualified sequence establishes order, the cause is a set `{U,D}`, not U, D, or no event. A later observed target cannot resolve an unobserved earlier interval in which the lower condition may have occurred. Do not deploy this toy path construction as a production bar labeler.

## 4. One joint finite-horizon distribution

At the fixed landmark information set I_l, define a discrete conditional hazard for each cause:

`a_k(b | I_l) = P(T=b, J=k | T>=b, I_l)`, k in {U,D,X}.

Require `a_k(b)>=0` and `sum_k a_k(b)<=1`. The remaining per-interval probability is no qualifying event in that interval. Set:

```
S(0) = 1
p_k(b) = S(b-1) * a_k(b)
S(b) = S(b-1) * (1 - sum_k a_k(b))
F_k(h) = sum_{b=1..h} p_k(b)
```

Then, for every h, `sum_k F_k(h)+S(h)=1`; each F_k is nondecreasing and S is nonincreasing. Proof is telescoping: the total event mass at b is `S(b-1)-S(b)`. The joint event-time mass across the finite horizon plus S(H) also sums to one. This does not assume that an event must eventually occur after H.

Two consequences are immediately implementable as future conformance requirements. First, **do not normalize away S(H)**: that would change an unconditional target-first probability into a probability conditional on some resolution. Second, separately normalizing each horizon's output does not enforce time coherence. A target probability of 60% by interval one and 50% by interval two is impossible for the same original event and information cut, even if both horizon vectors sum to one.

The recurrence models the *observed first-event distribution*, not the joint distribution of all latent target and invalidation times that would have occurred after a competing event. Such counterfactual times are not identified by first-event observations alone. No independence of latent failure times, causal acceleration, or structural economic mechanism is inferred.

### Numerical illustration, not estimated parameters

For three intervals with target hazard 0.1 and lower-condition hazard 0.2 in each, the exact horizon probabilities are:

| Upper-first | Lower-first | Other terminal-first | No event |
|---:|---:|---:|---:|
| 21.9% | 43.8% | 0% | 34.3% |

The zero X in this fictional construction is stipulated, not an instruction to set unmeasured native structural risk to zero.

### Why competing events cannot be discarded

In a fictional cohort of 100 origins, 60 lower-condition events occur in interval one; 20 targets occur in interval two; 20 cases remain event-free. Actual target incidence is 20/100 = 20%. Treating the 60 lower events as ordinary censoring and applying the target-only complement of Kaplan–Meier gives 20/40 = 50%. The discrepancy is purely algebraic. Competing-risks research distinguishes cause-specific rates from cumulative event risk [M1]. It does not validate any Prophet financial forecast.

## 5. Time estimates that do not conceal the chance of failure

The unconditional target quantile at probability q is the smallest h for which `F_U(h)>=q`. If F_U(H)<q, that quantile is **not reached within the supported horizon**. Do not fill it with H, extrapolate indefinitely, or average target times only among winners and call the result “expected time to target.”

A different, legitimate quantity is the conditional timing distribution *among cases reaching the target first by H*:

`P(T<=h | J=U,T<=H,I_l) = F_U(h)/F_U(H)` for h<=H and F_U(H)>0.

It must be accompanied by F_U(H) and the conditioning language. In the 100-origin example, all successful targets occur in interval two but the target probability is only 20%. “Target in two sessions” would disguise the other 80%. There is no unconditional median target time within that horizon.

For time to *any* first resolution, the finite restricted mean `E[min(T,H)] = sum_{b=0..H-1} S(b)` includes every origin. The three-interval illustrative law gives 2.19 intervals. It is not an expected time to target and is not a holding-period recommendation.

## 6. “From now” does not reset the original case

A current-landmark forecast conditions on an event-free case at the actual new landmark and on evidence usable then. It has its own issuance time and model/source version while retaining the original event definition. Origin and landmark forecasts answer different questions and need separate evaluation populations. Landmark methodology explicitly restricts predictions to subjects still at risk and handles repeated use of the same subject [M2,M3].

Under **unchanged original information plus learning only that no event occurred through s**, the original law implies:

`P(s<T<=s+u,J=k | T>s,I_0) = [F_k(s+u)-F_k(s)] / S(s)`.

For the illustrative constant-hazard law, after one event-free interval the next-two probabilities are upper-first 17%, lower-first 34%, and no event 49%. Using the old three-interval 21.9% as a fresh next-two probability is wrong. If S(s)=0 the conditioning event has no support; do not resurrect the case in the risk set.

When new evidence X_l is added, a newly estimated landmark law need not equal that algebraic reconditioning of the old forecast. It must be validated as a new conditional forecast. Its probability can rise or fall relative to the older forecast; **monotonicity is required across horizons within one fixed forecast, not across successive information updates**.

The same case's origin and later landmarks are not independent samples. Keep original case/source grouping, overlap support and decision dates in evaluation. A long-lived opportunity does not become ten independent discoveries because it was refreshed ten times. Start with one predeclared origin forecast; qualify one fixed landmark separately before a dense daily-updating model. No native scheduler or refresh policy is created here.

## 7. Candidate method and fair comparators

The initial modeling recommendation is a transparent discrete-time multinomial hazard, not a neural network or graph model. For each interval b and cause k:

`eta_kb = alpha_kb + beta_k' z(X_l)`;

`a_k(b) = exp(eta_kb) / [1 + sum_j exp(eta_jb)]`.

The denominator's 1 is the no-event reference category. This makes per-interval probabilities coherent by construction; the recurrence supplies coherent cumulative probabilities. Compute with a stable softmax, not unprotected exponentials. A time-bin baseline and regularized slopes provide a checkable starting point. Within a forecast, all X_l features are fixed to the landmark information cut; later observed features cannot enter earlier predictions.

Compare against (a) the supported marginal first-event distribution on the same training population and calendar; and (b) a strong transparent model with native geometry distance, case age, own-price/volatility/liquidity and ordinary-industry context. Any economic feature increment must use identical source coverage, observation times and model capacity. Shorter targets or wider invalidations mechanically alter target frequency; comparisons must hold the native geometry policy fixed or explicitly condition on it. Do not make a model look better by changing what counts as success.

For an exactly observed event `(t,k)`, the sequence likelihood is `S(t-1)*a_k(t)`. For complete no-event observation through H it is S(H). For genuine administrative censoring at c it is S(c), not S(H). Observation through c can contribute a prefix likelihood only under the applicable censoring assumptions. Gaps that could conceal earlier events do not supply an event-free prefix across the gap. A likelihood of a coarsened event set requires an explicitly justified observation/coarsening model; it is not a free missing-at-random assumption.

Use whole-origin likelihoods with weights fixed by the declared user task. A date-equal research estimand gives each origin date total weight one and divides that mass across its originally eligible cases; do not silently renormalize risk sets independently at every event time. Separate calibration and final tests chronologically, preserve original-case overlap/dependence, and forbid tuning on the final outcomes. Sparse causes and geometry strata require supported smoothing/partial pooling or an unavailable head, not invented certainty.

**This is an implementable mathematical candidate, not a completed empirical registration.** The exact source cohort, feature vector, penalty normalization/value, time-bin/horizon grid, calibration method, partitions, inference method, comparison budget and decision tolerances must be frozen in the existing future Q09 registration before fitting. No choice is borrowed automatically from H1; no Q09 fit, model search or trial was launched here. The decision now is which representation and failure semantics to build toward, not that this candidate predicts markets well.

## 8. Proper evaluation and what current research does not license

At a fixed supported horizon, let `p=(F_U,F_D,F_X,S)`. A fully observed case has a one-hot class y. Use the negatively oriented multiclass Brier score:

`L(p,y) = sum_k (p_k - 1[y=k])^2`.

For true class probabilities q, direct expansion gives:

`E_q[L(p,Y)] - E_q[L(q,Y)] = sum_k (p_k-q_k)^2`.

Thus honest probabilities minimize expected loss. Positive fixed weights over horizons preserve propriety for those horizon distributions; the full event-time logarithmic score distinguishes exact timing when labels support it. These are mathematical forecast-accuracy statements, not statements about profit. Proper-score principles are established in [M4]. Do not optimize an uncalibrated ranking score and relabel it a probability.

Censoring-adjusted scoring research supplies useful methods, but their assumptions matter: the 2025 competing-risks scoring work explicitly assumes event-time/censoring independence conditional on covariates [M5]. A vendor dropping distressed names, disappearing securities, ambiguous intrabar order or a missing price feed is not automatically an instance of that assumption. The relevant nuisance model and positivity must be justified; very large weights do not create absent outcome information.

The 2026 competing-risks calibration paper distinguishes event/time calibration and provides useful diagnostics. Its stated setup includes continuous event distributions, independent observations and non-informative censoring; its tail-based CR-D approach also relies on eventual resolution and a horizon sufficiently long to approximate limiting event mass. The paper identifies this last requirement as a practical limitation [M6]. **Do not transplant that tail-based test as a certification rule for short, discrete, overlapping trading episodes with material no-event mass.** Its finite-horizon marginal alternative is not the same tail requirement, but marginal agreement still is not case-specific or top-selection calibration. The paper's financial applicability is untested here.

### Selected-cohort counterexample

Construct 100 cases all carrying the forecast `(60% U,20% D,0% X,20% S)`. A pre-existing, decision-known ranking group selects 20 cases whose outcomes are `(4 U,12 D,0 X,4 S)`. The other 80 have `(56 U,8 D,0 X,16 S)`. The pooled frequencies exactly equal the published probabilities, yet the selected target frequency is 20%, not 60%.

This demonstrates failure of pooled or score-wise calibration under selection using additional information. It is **not** a claim that fully conditional true probabilities lose calibration under a selection rule measurable with respect to that same conditioning information. Q11 must validate the actual delivered population, ranking/tie/coverage policy and model generation. Report coverage, cause-specific reliability, proper scores and uncertainty separately for full and selected cohorts. Small samples and a non-significant calibration test cannot establish equivalence to a useful accuracy tolerance.

## 9. New derivation: paired-score bounds for unresolved event order

This is the main additional result of the present unit. It turns an unavailable event order into a precise limit on what an evaluation could conclude, without substituting a favorable label. It is a direct application of finite-set minimization, not a claim of a newly invented statistical estimator.

For case i at one fixed horizon, let A_i be the nonempty set of classes still possible given the qualified source. An exact label is a singleton; a double-hit bar may give `{U,D}`; unknown follow-up may permit more causes and S. Let w_i be fixed, nonnegative, outcome-independent weights summing to one over the **original** comparison population. Unknown source-population size prevents construction of these full-population bounds; surviving rows cannot invent it.

For candidate forecast p_i and comparator q_i, the paired loss difference under one actual class y is:

`d_i(y) = ||p_i||^2 - ||q_i||^2 - 2*(p_i,y - q_i,y)`.

Every compatible completed label set satisfies:

```
D_lower = sum_i w_i * min_{y in A_i} d_i(y)
D_upper = sum_i w_i * max_{y in A_i} d_i(y)
D_lower <= weighted paired Brier difference <= D_upper
```

The bounds are exact when all casewise completions are independently feasible. With additional cross-case or temporal constraints, they remain conservative outer bounds until that constraint set is handled. They are **identification bounds**, not confidence intervals, not sampling-error bars, and not evidence of out-of-sample skill. Do not multiply probabilities of alternative labels unless a missingness model has actually been justified.

Use the **same unknown actual class** to compare the two models. Minimizing the candidate loss and maximizing the comparator loss under different true labels for the same case produces needlessly loose bounds. First-event incidence itself has simple lower/upper bounds: weighted mass with exact cause k versus weighted mass for which k remains possible. The maxima for different causes are not generally jointly attainable.

### Exact illustration

Take 100 fictional original cases: 20 upper-first, 50 lower-first, 20 complete no-event, and 10 unresolved between upper and lower. Upper incidence lies in [20%,30%]; lower incidence in [50%,60%]. No-event remains 20%, and the same unresolved 10% cannot be allocated twice.

Compare constant candidate `p=(.30,.50,0,.20)` with comparator `q=(.20,.60,0,.20)`. The exact full-population paired Brier difference lies in **[−0.02,+0.02]**. All 1,024 assignments of the ten unresolved binary labels were enumerated and attained those endpoints. A complete-case calculation gives +0.0066667 and might tempt a rejection of the candidate; the missing event order can reverse that conclusion. These numbers are Brier-score units, **not basis points, return percentages, or a 2% probability error**.

Separate worst-case losses give [−0.06,+0.06], unnecessarily wide because they allow contradictory truths for the two predictions on the same case. The shared-truth pairing removes that artificial uncertainty.

### Label information has a measurable comparison value

The width contribution from case i is:

`2*w_i * [max_{y in A_i}(p_i,y-q_i,y) - min_{y in A_i}(p_i,y-q_i,y)]`.

In the example, each unresolved row contributes 0.004 Brier units of identification width; ten give 0.04. This identifies where better event-order evidence could change the model comparison. It is not a command to selectively backfill favorable cases: any refinement must follow the predeclared source/ascertainment policy, apply to both models, retain the original denominator and record unresolved cases. Fixed broader sampling and source rights remain controlling. If the two models give identical relevant probabilities, resolving that row does not change their paired-score uncertainty, though it can still matter for absolute calibration or other claims.

This bounded-score result is useful while planning label granularity. It does not make an unbounded missing financial return identifiable and cannot bypass the existing H1 completeness gate. Even a strictly negative identification interval on one realized cohort still requires appropriately dependent out-of-sample inference before a model-improvement claim.

## 10. Consumer contract and build disposition

Extend only the existing B10 model/evaluation and B11 prediction/read-model artifacts after their owners approve the scientific proposal. These are required semantic slots, not a new canonical schema:

| Existing responsibility | Required meaning and refusal behavior |
|---|---|
| B1 / case and source owners | Exact original source/case identity, geometry version, correction lineage, issuance/usable clocks and event-free status. No invented episode or guessed plan relation. |
| B4 / strategy / market-permission owners | Original conditions and entry/management authority. Forecast output cannot invent conditions, authorize entry or cancel a native refusal. |
| B06 / Evaluation / source owners | First-event cause/time or qualified allowed set; complete no-event versus censoring versus source-unknown; gap/tie/corporate-action and terminal-claim evidence. Existing grade outputs remain unchanged. |
| B10 / Conditional Fusion | One finite-horizon joint event-time distribution and residual mass, horizon/calendar/support, fitted model/feature/calibrator identity, honest unavailable reason per head. No universal country/sleeve score. |
| Q11 / Evaluation | Proper-score and actual selected-cohort qualification, support/coverage and dependence, missing-label bounds as appropriate, separate statistical uncertainty. |
| B11 / existing product read model | Preserve original and current forecast versions; show supported probability, horizon and conditioning plainly; missing means unavailable, never zero. No live numeric display before qualification. |

Initial human-facing wording should express the quantity, not “confidence”: for example, **“Target before invalidation within H supported sessions”** alongside other outcomes and no-event mass. A conditional timing statement must say **“Among target-first outcomes within H…”** and retain the target probability. A research-only/unqualified head shows its unavailable state, not fictional numbers from this document. No Paper edit or production copy change was made here.

For entry-policy analysis, use the law of total probability over actual allowed fill times/states. `P(fill) * P(target | immediate exposure)` is not generally the joint outcome. Two fictional joint distributions can both have fill probability 50% and upper-first probability 20%, yet have fill-and-upper joint probability 20% or 0%. Multiplying the equal marginals gives 10% in both worlds and is correct in neither. This is a minimal non-identification example even before addressing changed event geometry or time at an actual fill. The native policy and execution owner must supply the correct conditioning and costs.

### Concrete recommendation to parent

Adopt the **semantic/mathematical direction** for future Q09 work: finite-horizon joint events, explicit residual mass, origin/landmark separation, source-unknown label sets, paired-score identification bounds and actual selected-cohort calibration. Do not order another large predictor or more indicators before the event and label support are specified. Preserve existing scalar endpoint output as an endpoint output; neither remove useful research nor falsely upgrade it into a target probability.

The next native build step, when separately commissioned, is an owner-contained label/forecast conformance vertical against fictional fixtures and actual source interfaces, followed by a source-feasibility manifest and the future Q09 preregistration. It is not a new research database. A coherent forecaster that does not beat matched simple baselines on qualified, untouched outcomes is rejected or kept diagnostic. A probability head that fails selected-cohort calibration stays hidden as a probability even when its ranking is useful. No automatic champion, sizing, trade, alert or holding authority follows.

H1 integration remains independent; Q09 must not consume its sealed test outcomes or introduce a fourth H1 arm. H2/Earnings, Cycle, the parallel risk/technical/sector/options studies and source writers retain their grants. The central mission still includes interpretation of the first admitted empirical/build disposition; this scientific proposal alone does not complete it.

## 11. Evidence actually executed

Final command: `python q09_mathematical_checks.py`.

**22 named checks passed, 0 failed.** One check exhaustively evaluated exact mass/time identities for 1,000 stipulated rational three-interval hazard sequences. Another enumerated all 1,024 completions of the ten ambiguous labels. These are finite mathematical constructions, not 2,024 market observations, independent experiments or a model-performance estimate. The earlier 20-check draft is superseded, not added to the final total.

The script uses Python's standard library and exact fractions. It accesses no market/source store, native repository module, fitting procedure, network service or bootstrap. It creates only the adjacent JSON receipt. No PyArrow installation or previously refused resource was retried. The companion preserves the complete executed script, actual Python version, output and content hashes. This is author verification, not an independent scientific review.

## 12. Primary research consulted and limits of transfer

Source-derived contributions are distinguished here from the proposed Prophet design and direct arithmetic above. No published medical/benchmark performance is claimed to transfer to stocks.

- **[M1] Andersen, Geskus, de Witte and Putter (2012), “Competing risks in epidemiology: possibilities and pitfalls,” International Journal of Epidemiology, DOI 10.1093/ije/dyr213; PMID 22253319.** Supports the distinction between cause-specific hazard and cumulative incidence and the problem with censoring competitors for actual first-event risk. Used for conceptual interpretation, not financial effect sizes.
- **[M2] Nicolaie et al. (2013), “Dynamic prediction by landmarking in competing risks,” Statistics in Medicine, DOI 10.1002/sim.5665; PMID 23086627.** Supports restricting the landmark risk set and using covariates available at the landmark. Does not authorize rolling financial forecasts or prove their validity.
- **[M3] “Landmark proportional subdistribution hazards models for dynamic prediction of cumulative incidence functions” (2020), JRSS Series C 69(5):1145 onward, Oxford article 7058671.** Sections 2.4–2.5 describe repeated landmark records, their correlation and censoring assumptions. Only those methodological issues are used; no model-selection procedure or clinical performance is adopted.
- **[M4] Gneiting and Raftery (2007), “Strictly Proper Scoring Rules, Prediction, and Estimation,” JASA 102:359–378, DOI 10.1198/016214506000001437; University of Washington technical-report abstract also checked.** Supports proper forecast scoring. The specific Brier expansion and partial-label contrast bounds above are directly derived here.
- **[M5] Alberge et al., “Survival Models: Proper Scoring Rule and Stochastic Optimization with Competing Risks,” AISTATS 2025, PMLR 258:3619–3627; arXiv 2410.16765v1, especially Section 3.** Supports censoring-adjusted proper scores under stated assumptions. SurvivalBoost was not installed, fitted, benchmarked or selected as Prophet's winner.
- **[M6] Alberge, Haugomat, Varoquaux and Abécassis, “On the calibration of survival models with competing risks,” AISTATS 2026, PMLR 300:1837–1845; arXiv 2602.00194v1, assumptions 2–6 and Section 6 limitations.** Supports evaluating event and time calibration together. Its asymptotic, independence, continuity and tail requirements are not automatic certification for this proposal. No paper-specific calibration test was executed or installed.

All were accessed through primary publisher, PubMed or author/arXiv sources on 29 September 2026. An HTML v2 retrieval for M5 and some publisher full-text routes failed; the identified v1 HTML and accessible primary records were used instead. No missing full-text claim was invented. The full research evidence for the internal docket is the exact repository sources named in Section 1.

## Continuation and authority

Protected procedure: Mastermind `f91847688f8126511c854ab253cd5c3cb67baa4e`; INDEX `94d1af402598894372858793a5b1931019c5fa77`; compatible Skillpack 1.0.1/bootstrap 1. Same-pin active execution, Web CEO, reconciliation and closeout consumed. Current live Chairman direction expands independent science effort, not financial or source custody authority.

Publication is confined to the existing science review branch and existing cumulative child/parent return. No parent/empirical/economic/production/Paper source was modified. Own effects are explicit and reconciled; external child handles none. No background execution is claimed.

**MISSION_COMPLETE:false.** This bounded Q09 unit supplies a new scientific representation, discriminating examples and paired-label uncertainty derivation. The next independent science phase can investigate Q12's information increment versus context memorization/partial pooling without touching protected outcomes; actual H1 source/adoption returns still receive their owed interpretation when delivered. Neither a new research angle nor a checkpoint clears the existing empirical gates.
