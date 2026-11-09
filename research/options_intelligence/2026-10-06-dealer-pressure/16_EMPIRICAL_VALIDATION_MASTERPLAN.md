# Empirical validation masterplan

**Research design, not an executed market backtest.** This commission ran synthetic accounting/numerical witnesses only. It did not establish forecast uplift, trading returns, calibrated probabilities, current data entitlement or production performance. Reuse incumbent registered evaluation, research-output and candidate/outcome owners.

## 1. Primary decision

Determine whether inventory-conditioned nonlinear hedge pressure adds enough out-of-sample value beyond existing price, flow, GEX, Daytrade and Entry Radar systems to justify its incremental data and engineering cost. Separate 'can inventory be estimated?' from 'does better inventory improve decisions?' The second can fail even if the first succeeds.

## 2. Registration before touching outcomes

Freeze universe, covered roots/expiries, source/rights versions, decision cadence, label definitions, liquidity coordinate, train/test schedule, priors, missingness policy, primary metrics, feature blocks, variants, model-search budget, minimum useful effect, negative controls and stop rules. Record historical source availability class and chronology before selecting attractive event days.

A first data audit may inspect schema, counts and clock/gap distributions, but must not choose the final sample based on favorable returns. Development failures can revise the protocol with a new version; the previously inspected test segment becomes development data. Keep one genuinely untouched later segment.

## 3. Data grades and PIT join

| Grade | Evidence | Allowed conclusion |
|---|---|---|
| ACTUAL_AS_SEEN / captured PIT | Original receipt/publication vintages and model/consumer clocks | As-seen decision replay, subject to coverage |
| HISTORICAL_RECEIVABILITY / reconstructed PIT | Economic events plus defensible release schedule/latency assumptions | Historical sensitivity study; not original live proof |
| FINAL_VINTAGE / final corrected history | Final file with unavailable original vintages | Measurement/mechanism research only; cannot claim live deployability |
| Synthetic | Constructed prices/inventories/events | Accounting/numerical correctness, no alpha |

At decision `t`, every input's `available_at≤t`. Model computation and publication must also have finished by the simulated consumer time; use `max(input_available_at)+actual_or_assumed_compute_delay` as a minimum, not a fabricated actual clock. Effective session and event time do not substitute for received time. Preserve corrections: as-known-live and eventually-corrected truth are separate replays. Later OI, finalized auction records and revised index constituent files are never backfilled into earlier features.

Train transformations, surface-response coefficients, imputation, feature selection, scale normalizers and calibration only on earlier admitted observations. All training/calibration labels must mature before model freeze, including subsequent-day auction reversal labels and later OI smoothing targets. A simple train/test date cut without label maturity is insufficient.

## 4. Proposed first sample and horizons

Start with the S&P complex: SPX/SPXW exposures, ES cash-session target/hedge reference, SPY as a separate cross-product challenger. This is a **new, additive research registration**. Accepted P5 v1 remains SPY/QQQ/IWM and its next-ten-minute variance/B2-RI versus B1-RI contract. Do not edit that acceptance through this proposal. The initial new target is ES cash-session price behavior; actual SPX-index extrema require their own source and basis-aware evaluation. 0DTE and 1–7 calendar-day cohorts remain separate from 8+ day background risk. Store trading-session distance and exact fixing time too. A supplied complete series-history baseline is preferred for the shortest cohort. Start at a manageable set of qualified sessions selected by calendar/coverage, not outcome. [I01] [I03] [I05]

Target at least 250 independent sessions for initial formal comparison and continue if precision is insufficient; 60–120 sessions can diagnose feasibility but cannot establish broad regime robustness. The count is a planning assumption, not a statistical guarantee. For an event probability near 0.5, 385 independent observations give only about ±5 percentage-point simple binomial precision; clustered same-day node touches reduce effective sample size. Power analysis must use pilot session-level loss variance and the predeclared minimum useful gain.

**One proposed primary endpoint:** the equally weighted mean pinball loss at quantiles 0.10/0.50/0.90 for next-fifteen-trading-minute downside and upside ES excursions, normalized by a scale frozen at the decision time. Downside is `(P_t−min P_u)/scale_t` and upside is `(max P_u−P_t)/scale_t`, for `u∈[t,t+15m]`. Restrict primary decisions to those with fifteen eligible minutes remaining. The primary contrast adds the preregistered inventory/full-reprice block to the best simpler research adapter selected using development data only.

Remaining-session extrema, 5/30/60-minute excursions, touch/hold/break, close regions and entry outcomes are registered secondary families. Ten-minute exchange labels delayed after interval end can support fifteen/thirty-minute experiments; they do not establish final-minute nowcasting. Auction experiments have their own venue-specific sample and clock.

## 4A. Required extrema and close verdicts in the first study

The fifteen-minute endpoint remains the single primary. The commission also requires independent, frozen answers about remaining-session extremes and closing behavior. Both families therefore receive mandatory result tables in the same first study; they are not satisfied merely by passing a close non-inferiority gate.

| Family | Fixed target and origins | Proper score | Required comparison and verdict |
|---|---|---|---|
| F1: primary short horizon | Next fifteen-minute normalized ES upside/downside excursions on the admitted minute grid | Mean pinball, quantiles 0.10/0.50/0.90, both sides; equal session weight | Same information arms and strongest development-selected simpler adapter; positive, negative or inconclusive |
| F2: remaining-session extremes | Remaining upside/downside ES excursion from origins at cash-session close minus 60, 30 and 15 minutes; no future range in scale | Mean pinball, quantiles 0.10/0.50/0.90; equal side/origin and session weight | Identical arms and a target-matched price/volatility/seasonality baseline; separate useful-value verdict |
| F3: close | Signed normalized return from those same three origins to the admitted ES cash-close mark | Mean pinball, quantiles 0.10/0.25/0.50/0.75/0.90; equal origin and session weight | Identical arms and target-matched close baseline; separate useful-value verdict |

All three use the same ex-ante scale and original-availability admission law. Report10 governs session definitions and missing paths. A qualified SPX index-close/extreme target is scored separately; ES results do not certify SPX or a share auction. No auction-feed acquisition is required to score the ES close mark. A full close CDF and disjoint-bin probabilities, once implemented, additionally receive CRPS and Brier/log scores.

Freeze each family's useful-effect threshold before outcomes. A 2% relative loss improvement is a proposed starting hurdle for each, subject to owner cost/power review, not a measured effect. Predeclare the familywise inference policy (for example Holm-adjusted directional tests and compatible simultaneous bounds across F1/F2/F3) before claiming multiple confirmatory successes. Do not relabel a successful secondary as a passing primary.

**Futility is endpoint-specific.** A precise F1 null stops the corresponding fifteen-minute claim; it does not settle F2 or F3. Stop the broader scoped inventory effort only when all required families exclude their useful gain with adequate coverage and precision, or record a separate cost decision that explicitly leaves an unanswered family unresolved. An imprecise null is inconclusive. Close non-inferiority measures harm, not positive incremental closing value.

## 5. Ten mandatory baselines

| ID | Comparator | Fairness requirement |
|---|---|---|
| B01 | Price/technical-only intraday model | Same timestamps, model capacity and label eligibility |
| B02 | Historical intraday seasonality | Prior dates only; product/event calendar matched |
| B03 | VWAP/deviation/ATR/prior high-low zones | Match number, width and distance of zones |
| B04 | Static prior-OI walls | Same OI vintage and contract universe |
| B05 | Static GEX | Explicit inventory sign convention, same Greek inputs |
| B06 | Current Mastermind GEX/levels | Frozen actual code/config revision, not an invented replica |
| B07 | Current Daytrade Suite | Actual incumbent output and availability where retained |
| B08 | Current Live Entry Radar | Exact candidate/episode/trigger revision; options already present disclosed |
| B09 | Simple public options-flow model | Identical eligible trade/quote population |
| B10 | Advanced inventory/full-reprice model | Same baseline covariates, frozen complexity and latency |

If a historical incumbent output cannot be reconstructed at a truthful vintage, mark that comparator unevaluable; do not manufacture a passing comparison. A retrained common prediction head on frozen feature blocks is useful for scientific attribution, while native incumbent-policy replay measures product utility. Report both; they answer different questions. In the accepted prior programme, B1-RI is a fixed target-trained adapter of a small causal incumbent-information summary, and B2-RI augments it; neither is the full native production policy. Its options-free-input B0 also uses an options-conditioned cohort subject to lineage audit. Preserve those names and qualify this new B01–B10 comparison table as a separate research register. [I01] [I03]

### Existing Exposure Outlook comparison

Include the active MAS-260 price/volatility baseline and its established observed-outcome owner in the incumbent census. Its recorded GEX promotion refusal is prior adverse evidence, not a new result of this commission. Exact negative-test metrics and local/unpushed calibration sources require incumbent reconciliation before reuse. If original outputs are unavailable, identify the target-matched research adapter separately and do not claim it is the original policy. [M01] [IPR7328]

## 6. Information-ladder experiment

Within B10 compare: explicit OI scenarios; deterministic aggressor proxy; scenario ensemble; calibrated public filter; participant-informed delayed inventory; and a final corrected participant benchmark labeled as a **scoped higher-information benchmark**, not tradable performance or a universal full-book upper bound. Keep identical quote/surface/liquidity inputs across these comparisons.

First ask whether the stronger participant benchmark improves forecasting. If adequate coverage/power excludes the preregistered useful gain, investment in a public filter imitating that scoped benchmark for that endpoint is not justified. Apply the broader-stop rule in `4A across the required extrema and close families. If the interval still admits a useful gain, the result is inconclusive. If a useful gain exists, ask how much survives actual publication latency and incomplete history. Then test whether the public filter closes enough of that gap at lower data cost. A failure for C1/SPX cannot settle all dealers, other products or unobserved OTC portfolios.

## 7. Walk-forward schedule

Proposed template: 120-session training window, next 20-session calibration window, next 20-session test window, rolled forward twenty sessions. Longer histories permit expanding-window and annual regime checks. Do not silently use this template if source history is too short. Fix it before scoring; alternate windows are sensitivity variants within the registered model-search budget.

Purge all training/calibration examples whose outcome intervals overlap the next segment; embargo at least through the latest necessary label maturity, not an arbitrary number of minutes. Fit hyperparameters through nested earlier-only folds. Keep a final 60-session chronological holdout for the model selected through development if history permits; otherwise state evidence is preliminary and reserve prospective testing.

Date-block bootstrap or suitable dependent-data inference compares per-session loss differences. Resample entire sessions and, for monthly/rebalance dependence, broader blocks as sensitivity. Hundreds of minute observations from one day are not hundreds of independent market regimes. For cross-product models, splitting SPX into train and SPY into test on the same day is not independent validation.

## 8. Required ablations

1. Assumed versus inferred versus participant-informed inventory.
2. Single-product versus cross-product hedge equivalents, with residual-risk coverage.
3. Gamma only versus gamma+vanna+charm and exact full repricing.
4. Static inventory versus intraday updates; starting positions versus new trading.
5. Raw exposure versus incremental hedge demand.
6. Hedge demand versus demand/volume and demand/capacity.
7. Options-only versus options+underlying microstructure.
8. Generic late-day features versus venue-specific auction information.
9. Options/liquidity baseline versus incremental off-exchange memory.
10. Immediate/full hedge versus delayed/partial execution assumptions.
11. Fixed-IV/sticky-strike/sticky-delta/learned surface response.
12. As-known data versus final corrections as a separately labeled diagnostic.

Apply hierarchical testing: one primary outcome and model comparison, then a small number of registered families, then exploratory variants. Control multiplicity within declared families and disclose the entire search budget. Do not pick the only winning horizon or call a merged paper independent replication.

## 9. Metrics and exact units

| Target | Metrics | Important trap |
|---|---|---|
| Touch / hold / break | Brier, log loss, calibration intercept/slope, reliability plots, support count | Primary denominator includes qualified interactions, including immediate gap-through breaks; strict-touch subset and unresolved reported |
| LOD/HOD region | Probability score; coverage and interval width; distance to region normalized by ex-ante scale | More/wider zones mechanically improve hit rate |
| Remaining extrema | Pinball loss by quantile, coverage, width, tail failures | Today's future high/low never enters feature normalization |
| Close region / CDF | Multiclass log/Brier, CRPS, calibration by venue/phase | Official auction versus last print distinct |
| Entry timing | MFE/MAE, delay, missed winners, adverse excursion and false-entry count | Exact incumbent candidates frozen; no retrospective setup selection |
| Auction aftereffects | Close-to-next-open and close-to-next-session returns residualized on market/event state | Next-day information only a matured label |
| Measurement | Inventory/hedge-unit error, exposure-weighted sign error, coverage | Classification accuracy is not predictive value |
| Operations | Consumer latency distribution, eligible coverage, correction rate, CPU/storage/data cost | Fresh file timestamp is not current market data |

For CRPS use the forecast CDF against the realized scalar price; for joint low/high/close dependence use a declared multivariate proper score or path-based coverage diagnostics. Do not report a precise probability without reliability evidence and enough independent outcomes. No source-quality number can substitute for forecast calibration.

## 10. Confounders, placebos and falsification

Control or stratify using information known at formation: macro releases, scheduled Fed events, earnings for constituent/single-name extensions, volatility regime, month/quarter end, index changes, ordinary versus expiry sessions, tick/spread regime, primary listing and auction-rule era, futures rolls and dividend/exercise state.

Placebos: shifted strikes with matched widths/distances; randomized inventory signs preserving gross exposure; lagged/stale versions; flow-time permutations within comparable historical strata; gamma-only and unsigned-activity proxies; unaffected symbols/event dates. A negative control that accidentally contains future prices is invalid. Compare both observed-time and event-time artifacts when sequence uncertainty matters.

Do not infer causal percentages of late-day selling from correlated model components. Feature attribution explains a fitted forecast, not the share of institutional, dealer or discretionary orders. Causal studies require a separate identified design and cannot be manufactured through a richer feature set.

## 11. Provisional go/no-go policy

Before outcomes, the owner chooses the minimum useful loss reduction from expected user benefit and total cost. As an initial design target, evaluate whether a 2% relative improvement in the primary pinball score is economically meaningful; this is **a proposed hurdle**, not an established effect. Report confidence intervals and absolute changes. A provisional promotion rule requires a point gain above the useful hurdle and a one-sided session-block 95% confidence bound above zero, with multiplicity handled as registered. A stronger lower-bound-above-hurdle rule may be chosen before outcomes if costs require it.

Predeclare stress/close non-inferiority margins separately; a suggested planning value is at most 2% relative proper-loss degradation, subject to adequate subgroup precision. If the upper confidence bound on degradation exceeds the chosen margin, safety of that subgroup is unproved. Small strata are inconclusive rather than silently passed. Coverage and latency requirements are source- and use-specific and must be set before scoring.

Failure modes have specific consequences:

- Higher-information benchmark confidence interval rules out a useful gain at adequate coverage/power: stop the corresponding endpoint claim; broader reconstruction stops only under the F1/F2/F3 rule in `4A. Keep useful descriptive mechanics. A nonsignificant but imprecise result is inconclusive.
- Benefit disappears after true latency: do not buy faster feeds until a timed value-of-information test justifies them.
- Apparent uplift only in final corrected history: research-only result; capture PIT before promotion.
- Benefit explained by raw flow or liquidity: ship the simpler qualified block through the incumbent owner.
- Sign/threshold unstable across credible priors: scenario presentation only.
- Good average result but unbounded tail/cost/false-veto harm: no policy promotion.

## 12. Prospective validation and acceptance artifacts

Later authorized implementation should shadow the existing service for a proposed minimum 60 eligible sessions, extended until registered power/coverage targets are met. Predictions must be recorded before outcomes. No trading/ranking/sizing/auto-exit changes are implied. Require input/model manifests, archived forecasts, label vintages, coverage/latency receipt, complete score/ablation tables, calibration plots, failed hypotheses and a reproducible existing-owner evaluation command.

Promotion from observation to calibrated prediction, and from prediction to any decision policy, are separate decisions. This commission finishes at an implementation-ready research handoff; none of those promotions occurred here.

<!-- Report-local source links. Scope and access limits are in SOURCE_REGISTER.md. -->

[I01]: https://github.com/mastermindx-market-intelligence/macro/blob/c9631f8b2469587dec643bec94b16e77c09ef511/research/options_intelligence/2026-10-03/MASTER_PLAN.md
[I03]: https://github.com/mastermindx-market-intelligence/macro/blob/c9631f8b2469587dec643bec94b16e77c09ef511/research/options_intelligence/2026-10-03/CONTRACTS.md
[I05]: https://github.com/mastermindx-market-intelligence/macro/blob/c9631f8b2469587dec643bec94b16e77c09ef511/research/options_intelligence/2026-10-03/options-near-expiry-spec.md
[IPR7328]: https://github.com/mastermindx-market-intelligence/macro/pull/7328
[M01]: https://linear.app/mastermindx/issue/MAS-260/options-exposure-outlook-research-calibrated-forecasts-and-terminal
