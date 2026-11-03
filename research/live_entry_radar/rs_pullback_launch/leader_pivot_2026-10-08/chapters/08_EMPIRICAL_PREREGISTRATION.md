# 08 | Empirical preregistration and ablation matrix

## Status and scope

**PROPOSED, OUTCOME-UNSEEN TARGET PROTOCOL — NOT A CANONICALLY REGISTERED EXECUTABLE TRIAL.** The scientific definitions below are specified now. Actual cohort/source manifests, eligible date cutoffs, inspected-history exclusions, source rights and independent reveal custody cannot be fabricated while the one-minute/PIT plane is unadmitted. They are the exact remaining registration fields, not permission to change definitions after outcomes. [I04–I05, I08, I15]

No historical target was trained, scored or inspected in this session. Existing published internal negatives are prior evidence, not a fresh holdout. The first market experiment, once admitted and registered, contains only the B0/P1 contrast. All richer families remain gated.

## 1. Population and episode origin

Use stable security IDs and point-in-time daily-leader eligibility supplied by the existing owner. Freeze eligibility at episode opening using the latest daily record actually available then; preserve its timestamp, formula and source. Do not repeatedly delete a legitimate pullback because current RS rank falls. No today's-survivors universe and no current-theme backfill. [I12, I20]

Proposed intraday species `leader_pullback_30m_reference_v1` is distinct from the incumbent daily 5%-scale pullback. At each completed 15m observation, calculate depth from the highest high of the preceding 120 RTH minutes, using only completed source intervals. Open one episode on the first transition into depth **0.5–2.0 A0**, while the owner-qualified daily leader is eligible. These are frozen experimental priors, not current production rules. The daily owner's constants are unchanged.

`A0` is a true-range Wilder ATR14 computed from fully completed 30m OHLC bars ending strictly before the origin. Preserve the prior RTH close in true range so overnight gaps are represented, and include an opening-gap primitive in B0. Freeze A0 for the entire episode. Reject zero/unsupported units. Do not substitute the Macro entry gauge's close-return proxy. [I13]

Only one active episode per security is allowed. It expires at 120 RTH minutes after origin or at the known session close, whichever is earlier. A fresh episode requires a completed return above the original depth boundary before a later new transition; no repeated rows around the same low are treated as independent episodes. An owner-compatible definition/amendment must be ratified before any event-writing implementation. The study reuses the incumbent episode factory.

Full-horizon primary origins must permit the reference entry and all 120 future RTH minutes before the published session close. This exclusion is knowable at origin. Later entries remain in a separate session-remainder analysis; they do not acquire a shorter primary ruler merely to look safer.

## 2. Exact completed-30m reference predicate

Let `L_ref` be the minimum low of the preceding four completed 30m bars. A primary rejection-bar candidate is issued only after the current full 30m bar is closed and all required source receipts are available, when:

```text
current_low < L_ref
current_close > L_ref
current_high > current_low
(current_close − current_low) / (current_high − current_low) ≥ 0.5
```

The emitted object freezes the bar's high, low, end time, known time, A0, support and source references. It is a **completed rejection candidate**, not a proven local minimum. A lower low later is allowed and must produce failure/invalidation evidence rather than deleting the original event. The toy audit checks availability and prefix invariance, not production conformance. [M01]

One separately counted structural challenger is a three-bar local-low pattern; its event time is the right-hand bar's availability, never the middle bar's earlier timestamp. Do not search an unrestricted candlestick catalogue.

Primary confirmation uses a **later** completed one-minute close above the frozen pivot high plus one valid tick. Invalidation is a later observed breach of the frozen pivot low minus one tick. If both occur in an unresolved source interval, report ordering uncertainty. The candidate expires after 60 RTH minutes or the episode's expiry, whichever comes first. `PIVOT_CONFIRMED` is observed reclaim, not proof of a successful launch. `LAUNCH` is an outcome field, never an input feature or retroactively rewritten detector state.

## 3. Decision time and reference price

For every input distinguish bar/event time, source public-availability time when demonstrable, Mastermind first receipt, revision time and decision issue time. A historical “could have known” source contract is not a record that Mastermind actually saw the fact then. Do not grant either meaning from a retrieval performed today.

The first B0/P1 study schedules predictions at every completed full-30m decision landmark inside each active episode, including landmarks with NO_PIVOT. It must not score only successful or eventually confirmed pivots. The original calendar-defined opportunity denominator includes scheduled-but-missing predictions. Report both equal-episode-weighted and raw-landmark results, with the former primary; compute scheduled landmark weights from the origin calendar, not subsequent price outcomes. All models in a paired comparison share these eligible decision timestamps and admissible information sets. The price-only reference `E` is the open of the first regular one-minute interval whose start is strictly later than issue time. It is a defined future entry convention, not a feature known at the preceding issue. Missing E is unresolved, not a favorable fill. Economic variants require actual executable quote/latency evidence; OHLC does not establish fill price or size.

Every landmark used for the primary launch forecast must independently leave all 120 RTH minutes after its reference entry before the known session close. Origin eligibility alone does not prove this for later landmarks. A later landmark without that room belongs only to the separately declared session-remainder analysis; its exclusion is applied identically to B0 and P1 and reported. Forecast horizons are measured from each decision-reference entry; policy economics still ends at the common original episode terminal time. They answer different questions and cannot borrow one another’s denominators.

Store every expected prediction, issued prediction, late/missing prediction and abstention through the existing ledger. No late backfill counts as a prospective issue. Revisions remain append-only and cannot change the originally issued feature vector.

## 4. Six distinct targets

**Downside.** Positive adverse excursion at horizon H is `MAE_H/A0 = max(0, (E − minimum_future_price_H)/A0)`. Estimate its distribution or registered quantiles and `P(MAE_H ≤ 0.25 A0)`. Report the probability of adverse excursion above 1 A0. Quote-executable downside is a separate target from trade-price lows.

**Launch.** Primary first-passage event is the upper barrier `E + 1.0 A0` before the lower barrier `E − 0.5 A0`, within 120 RTH minutes. A lower-first event is a competing event, not right-censoring. Observed neither-hit by H is a non-launch for that fixed-horizon probability. Secondary horizons are 30, 60 and 90 RTH minutes and session remainder; they are not alternative primary winners.

**False start.** Let `E_c` be the confirmation-reference entry under the same next-interval convention. Test whether the frozen invalidation `pivot_low − one_tick` is breached before `E_c + 1.0 A0`, within the smaller of 60 RTH minutes after confirmation and the remaining original episode window. A zero remaining window is NON_EVALUABLE. No reclaim, confirmed-but-no-barrier, and unresolved path order are separate states; no-reclaim rows are not successful confirmations. This conditional false-start target is distinct from the fixed-120-minute launch forecast.

**Confirmation cost.** Report `(E_confirmed − E_armed)/A0` and `(E_confirmed − E_formed)/A0` only where both reference entries exist, with elapsed time and source support. Also report the full-population frequencies of never-formed, never-confirmed and missed-before-confirmation moves. A conditional average on successful pairs is not the population economic answer.

**Remaining opportunity.** Estimate the conditional distribution of future favorable excursion from the current state, alongside the chance of reaching the frozen target and the distance already consumed since origin. Realized MFE is an evaluation outcome, not an oracle value displayed at entry. Do not rebrand a distance-to-ATR-extension heuristic as a validated remaining-upside estimate.

**Economic timing.** Compare early/armed, formed, confirmed, incumbent-compatible and abstain policies on the same eligible episodes. The primary economic horizon ends at the same episode terminal time for all policies. A late entrant does not get extra future time. All shares/budgets and reference-risk normalization are fixed from the common origin; a tighter late stop cannot buy more exposure and manufacture a larger R.

For example, define a fixed notional budget B and origin quantity `q0=B/P0`; common risk unit is `R0=q0×0.5A0`. Evaluate `(realized net P&L)/R0`. This is an experimental common ruler, not a live sizing recommendation. Non-entry is zero realized return and remains in the opportunity denominator. Missed moves, stop gaps, duration, capital use, turnover and tail loss are printed separately.

## 5. Strong B0 and fair attribution

B0 contains current and lagged subject returns; market, sector and qualified peer returns at matched lags; leader quality; pullback depth/age/slope; volatility; liquidity/ADV; bar-of-day; registered support/location geometry; catalyst coverage/state; primitive higher-timeframe information; and faithful incumbent Entry Engine/gauge context. It includes missingness and observation age. No convenient omission of benchmark history may create “RS alpha.” [I03, I07]

For incumbent context, actual retained as-issued outputs and their inputs are preferred. An owner-approved deterministic replay of a frozen Entry Engine version from genuinely PIT inputs may serve as a **research-policy emulation**, not evidence that the historical software actually issued that decision. Label actual-history and emulated-policy comparisons separately. Missing old inputs cannot be supplied from present-day artifacts.

When a derived family depends on a trailing exposure estimate or a longer history, the fair representation comparator receives the same primitive dependency closure. A flexible baseline must be tested alongside the simple regularized model. Novel group source value and representation value are separate ablations, as specified in chapter 06.

## 6. Additive tournament

| Family | Cumulative addition | Primary question / special condition |
|---|---|---|
| B0 | Strong primitive baseline | Is any incremental complexity needed? |
| P1 | Completed 30m structure | Does explicit causal structure improve beyond its primitives? |
| P2 | Market/sector residual repair | New species accepted against the PSS-F3 kill; raw-history comparator |
| P3 | Qualified industry/static group | Adds beyond sector and subject history, with PIT scope |
| P4 | Dynamic GMI theme/subtheme | Recent/prospective matched-cohort source increment |
| P5 | Ex-self theme residual resilience | Separates new group data from derived representation |
| P6 | 15m anticipation | Net common-budget gain rather than cheaper-looking entries alone |
| P7 | One fixed higher context, reference 120m | Matched memory, observation age and missed coverage |
| P8 | Fixed multiscale context | Equal-weight, median and same-covariate references |
| P9 | Structure-derived temporal band | Only an accepted Temporal Grain recipe; no ticker outcome selection |

Run add-one-to-B0 and remove-one-from-the-supported-full-model analyses. Removing a representation differs from removing its source and all descendants. Keep rejected and held branches in the attempted-family accounting; an unadmitted P4 or P9 is NOT_TESTED, not zero effect. [I07–I08]

**The first market wave is four launch-model specifications:** B0 and B0+P1, each in a regularized linear and a shallow-tree form. No theme, adaptive band or arbitrary oscillator grid enters that first outcome read. The three-bar pivot alternative is a later separately counted comparison, not an unlogged repair of P1.

For planning transparency, two model forms applied to B0, P1 and eight later add-one/cumulative families produce at most 36 initial feature/model specifications; nine remove-one contrasts add up to 18, giving 54 before clock variants, structural alternatives or specialist families. This ceiling is arithmetic, not a trial registration or a claim of 54 independent experiments. Separate targets, horizon reads, policy variants, costs, seeds, refits and any later configurations must be enumerated in the incumbent ledger. The first four models do not authorize the other fifty. [M01]

## 7. Model fitting, chronology and power

Initial launch models are ridge logistic regression minimizing mean log loss plus `0.01 × sum(beta²)/2`, with an unpenalized intercept and train-standardized inputs, and a shallow boosted-tree comparator with maximum depth two, 100 trees and learning rate 0.05. Use a fixed minimum leaf support of 50 where the chosen implementation supports that contract. All preprocessing is train-only. These are proposed capacity limits; the implementation/version and exact equivalent parameters must be frozen before execution, with no outcome-based library substitution.

Use chronological training, a disjoint calibration block, validation and a sealed final holdout. A qualified historical panel should provide at least eight quarterly out-of-sample folds for the cross-era claim; a shorter panel may support a narrower development result but not that generalization claim. Development dates and already-inspected price histories are not relabeled untouched. Applicable DNR fresh-formation restrictions remain in force. [I08, I19]

Purge overlapping label/episode windows across boundaries, with an embargo covering the maximum 120-minute outcome span plus the registered finalization lag. Past-only feature lookback overlap is not itself future leakage. Keep all names together in calendar blocks. Use a 20-session block bootstrap as the primary uncertainty estimator, with 5- and 60-session sensitivities and explicit era summaries. Never ticker-only bootstrap or random-row split the primary experiment. [I08, I19]

Estimate required sample size before outcome access using source-only counts, a blinded or training-only nuisance estimate and dependence-aware simulations. Require 80% power for the registered practical margin at the adjusted testing level. Event count is not independent N; retain the number of sessions, quarterly folds, common-shock clusters and distinct names. When the admitted history cannot power the contrast, the result is underpowered, not a relaxed pass.

## 8. Pre-outcome gates

Retain the originating RS gates as the initial product-level requirements, made explicit here. They are proposed acceptance policy, not literature-derived constants. Freeze them through the owning scientific review before reveal. [I03]

| Claim | Gate |
|---|---|
| Launch | At least 2% relative Brier improvement versus strong B0 on the same supported observations, with multiplicity-adjusted positive-effect evidence. |
| Downside | At least 0.10 A0 lower mean MAE at predeclared equal coverage, with positive-effect evidence; the upper confidence bound for deterioration in `P(MAE>1A0)` must not exceed 1 percentage point. |
| Economics | At least 0.10 common-budget R improvement per eligible episode versus incumbent-compatible policy; positive net mean and positive incremental mean under doubled admitted costs; no material adverse-tail deterioration. |
| Stability | Positive direction in at least 70% of eligible quarterly folds, with no hidden dominant-name/era dependence. |
| Prospective | At least 90 supported sessions after the exact champion is frozen, plus its precomputed event/power and calibration requirements. Elapsed days alone never pass. |

For equal coverage, compare the same number of candidates in each supported decision-time cohort, using a predeclared 20% evaluation coverage and identical budget. Select `floor(0.20 × n)` from the same n eligible candidates, ranking by the registered risk estimate; break exact ties by a frozen stable-security-ID hash. Cohorts with fewer than five eligible candidates contribute no risk-selection comparison but remain in the overall prediction/coverage accounting. This is a cross-sectional coverage-standardized research ruler, not a threshold fitted to the future test distribution. Any deployment-like threshold must be fixed on training/calibration, not chosen using the test distribution. Print the whole risk–coverage curve as secondary evidence; it is not a search for a prettier operating point.

Define economic tail noninferiority before reveal: the upper confidence bound on the candidate's additional worst-5%-episode expected loss must be at most 0.05 R. This is a recommended additional guard, not a historical result. Unknown gap/impact risk prevents an economic pass rather than being assumed away.

Use Holm family-wise control at 5% across the primary claims actually registered for a wave. Secondary horizons and subgroups cannot rescue a failed primary. A new family needs positive adjusted incremental evidence beyond the current champion and must preserve the relevant product-level gate. Adaptive selection has a higher complexity hurdle: at least 0.05 R additional net common-budget value versus the best fixed/memory-matched alternative, while preserving forecast and tail gates. No sufficient quote/cost basis means no economic adaptation promotion.

## 9. Cost, missingness and censoring law

Price-only forecast evaluation can proceed on an admitted price plane. Executable economics additionally needs defensible bid/ask, fees, impact, latency and fill assumptions for the supported size/liquidity scope. This does not make continuous L1 predictive features an MVP dependency; it makes execution evidence an economic dependency. Do not purchase L2/L3 merely to begin. [I09–I10]

Unknown intra-minute ordering when both barriers are hit is ORDER_UNRESOLVED. Preserve paired best/worst bounds using the **same unknown outcome** for both models; do not give each arm a different label. For Brier improvement, evaluate both feasible outcomes jointly. If the conclusion changes under valid bounds, the target is unresolved. A conservative lower-first convention may be a labeled policy sensitivity, not invented observed truth. [I08, M01]

Keep source gaps, halts, delistings and early-close censoring explicit. Never drop only bad-outcome missingness, backfill original first-seen times, assume stop-price fills through a gap, or treat no observed quote as zero transaction cost. Compare costs at the same exposure and eligible-episode denominator.

## 10. Promotion and prospective issue

Engineering acceptance, source admission, scientific validation, forecast calibration, economic usefulness, UI integration and trading authority are separate gates. Passing any one does not grant the others. After scientific selection, fit calibration only on its reserved chronology; print cohort, target, horizon and version. Use the LLR reliability-bin method as a starting protocol: fixed deciles, any adjacent-bin merging decided only in calibration, at least 400 resolved labels across 20 distinct days per proposed display bin, and simultaneous 95% calibration-error intervals contained within ±0.05. Counts are necessary proposed floors, not independent-event or calibration proofs; failed bins abstain. Do not equate “90 days” with calibrated probabilities. [I08–I10]

The first prospective step can be source/descriptor observation through the existing Radar/W5 path. Forecast validation begins only after its own frozen contract and owner-approved annotation seam exist. Missing forecasts remain in the expected-denominator report. No second prediction store, scheduler, alert lifecycle or background daemon is authorized by this packet.
