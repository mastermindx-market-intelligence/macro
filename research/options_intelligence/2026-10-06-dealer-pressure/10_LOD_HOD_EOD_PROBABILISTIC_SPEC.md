# Probabilistic intraday extremes and close-region specification

**Status: SPEC_ONLY.** Model outputs are null until the proposed out-of-sample validation is completed. Numerical examples elsewhere are synthetic mechanics, not estimated probabilities.

## 1. Define the traded object and session first

For the proposed S&P pilot, observe an admitted ES contract over the cash regular session and project zones into SPX only through a timestamped basis map. This is a **new research cohort**; accepted P5 v1 remains SPY/QQQ/IWM with its registered next-ten-minute variance contract. ES cash-session extrema are not automatically actual SPX index extrema; separately score the latter when an eligible index series and basis-error assessment exist. SPX itself is a calculated index, not an executable order book. Store whether the target is index value, eligible trade price or midpoint. Exclude invalid ticks and record correction vintages; do not make a clean final data series masquerade as live observations.

Define `t_open`, decision `t`, `C_cont` (continuous-session boundary), official auction close where applicable, and product fixing separately. A 16:00 ES observation is not necessarily the CME official settlement. The SPX official close, ETF primary auction price and final continuous midpoint are different labels. Early closes follow the security's actual calendar and rule version.

## 2. Exact outcomes

Freeze each node's zone `Z_j(t)=[a_j,b_j]` at formation. A later moving zone cannot improve the earlier forecast after the fact. Let `P_u` be the specified eligible price process.

\[
T_j=\inf\{u>t:P_u\in Z_j(t)\},\quad
L^{rem}_t=\min_{u\in[t,C]}P_u,\quad
H^{rem}_t=\max_{u\in[t,C]}P_u.
\]

`P(touch by C)=P(T_j≤C)` is separate from a conditional hold. When already inside a zone, report an in-zone state and model subsequent exit/retest; do not count it as a newly predicted touch.

Discrete prices can jump completely through a zone without an in-zone observation. Preserve a separate **gap-through** event when consecutive eligible observations cross both boundaries. The primary interaction label counts that as a crossing/failure at the first observed far-side price, with an explicit gap flag; the strict in-zone-touch statistic excludes it but reports its count. A missing data interval cannot prove a jump and is unobservable. Freeze this convention before scoring so sharp failures cannot disappear from the hold denominator.

Define the primary interaction time `T*_j=min(T_j,T_gap,j)`, where `T_gap,j` is the first qualified gap-through time. The primary hold/break model conditions on an observable interaction (`T*_j≤C`), so a gap-through contributes an immediate break. A separately labeled strict-touch analysis conditions on `T_j≤C` and excludes gap-throughs while reporting them. Do not mix those denominators.

For downward entry into a prospective absorption zone, define an upper rebound barrier `b_j+ε_t` and lower failure barrier `a_j−ε_t`, with `ε_t` frozen from tick/spread/lag-trained volatility. After the first primary interaction, compare the first qualifying rebound with the first qualifying breach over a predeclared resolution horizon, proposed fifteen trading minutes or the remaining eligible session, whichever is shorter.

| Label | Exact meaning |
|---|---|
| Touch | First qualified entry before horizon/session end |
| Hold | Rebound barrier reached before failure barrier within the resolution window |
| Break | Failure barrier reached before rebound barrier within the resolution window |
| Unresolved | Neither barrier reached before horizon/session end |
| Unobservable | Required path is missing or corrupt; distinct from unresolved |

Use mirrored definitions for upside resistance. If confirmation requires two consecutive one-minute closes, that rule is part of the label version; never mix it with an any-tick breach. Touches inside the final fifteen minutes have a shorter potential resolution horizon and need horizon-conditioned modeling. A next-day move cannot retrospectively turn an unresolved intraday touch into a hold.

Joint outcome coherence requires `P(hold|interaction)+P(break|interaction)+P(unresolved|interaction)=1` for the primary observable horizon. The separately reported strict-touch analysis obeys the corresponding identity conditional on strict touch. These are different from the probability of closing above a line. For sequential barriers, ordering is part of the event, not an independent binary label.

## 3. Remaining extremes versus whole-day extremes

At time `t`, the current day low `L_sofar` and high `H_sofar` are already known. Final day extremes satisfy

\[
L^{day}=\min(L^{sofar},L^{rem}),\qquad
H^{day}=\max(H^{sofar},H^{rem}).
\]

The distributions have mass at the already observed extreme when no new low/high occurs. Report `P(new LOD)`, `P(new HOD)` and remaining-range quantiles separately. A region containing the morning low may become the day's final LOD without another touch; a future-touch model alone cannot represent this event.

`P(zone becomes LOD/HOD)` means the final eligible whole-day extreme lies inside the frozen zone, under an explicit tick/tie rule. Do not use eventual low/high to select the zone or feature universe. For a normalized error, divide distance from the realized extreme to the predicted region by a scale already fixed at `t`, not that day's later realized range.

## 4. Close regions and probability coherence

Use disjoint ordered price bins derived from frozen node boundaries and a neutral background grid, with lower/upper overflow bins. Output `P(P_close∈bin_j)` summing to one, plus a close-price CDF and quantiles. Overlapping UI zones may each display marginal probabilities, but their values cannot be summed as a partition.

Close must lie between final low/high. Prefer a joint path simulator or a constrained distribution that respects this relation. If separate models are retained for interpretability, report and repair incoherent probability sets through a preregistered reconciliation rule evaluated out of sample; do not silently clip predictions only on bad days.

Use the physical forecasting distribution learned from past observations. Option-implied risk-neutral tails and variance are features, not literal real-world probabilities. The price of downside insurance can rise without a proportional change in realized crash probability.

## 5. Model comparison

| Model | Appropriate use | Main risk | Initial decision |
|---|---|---|---|
| Empirical time-of-day conditional distribution | Strong simple remaining-range/close baseline | Sparse regime cells | Mandatory |
| Brownian/local-vol first-passage baseline | Transparent distance/time/vol dependence | Jumps, drift and state dependence | Mandatory diagnostic, not final truth |
| Discrete-time competing hazards | Touch ordering; hold/break/unresolved events | Repeated forecasts and sparse events | Preferred initial probability model |
| Logistic/GAM and shallow boosted trees | Nonlinear interactions with interpretable feature ablations | Tuning leakage/overfit | Compete under identical data splits |
| Quantile regression / distributional trees | Remaining high/low/close distributions | Crossing quantiles and incoherence | Initial distribution challenger |
| State-space/path simulation | Joint path coherence and state changes | Misspecified dynamics, expensive calibration | Later if simpler model misses material structure |
| Neural temporal model | Rich long-memory input if genuinely supported | Sample size, instability and explanation burden | Deferred; must beat simple models after cost |

A first-passage formulation is conceptually better matched to 'touch, then hold/break' than point regression. It is **not proven empirically superior**. Use point/quantile regression for continuous remaining extrema and close where it matches the outcome. The commission does not justify one neural system for all targets.

## 6. Discrete competing hazards

For an at-risk interval `k`, let `p_j,k` be the probability of first touching outcome `j` conditional on no earlier competing event. A multinomial model including no event keeps `Σ_j p_j,k≤1`. Then

\[
S_k=\prod_{r<k}\left(1-\sum_jp_{j,r}\right),\qquad
F_j(K)=\sum_{k≤K}S_kp_{j,k}.
\]

Choose competition for events that cannot happen first simultaneously. Multiple zones can be touched sequentially, so 'ever touches every zone' is not one mutually exclusive classification. Use a transition model after first touch, or separately specified marginal hazards with coherence checks. Bars that cross two barriers without event ordering are interval-censored/ambiguous; do not assume a profitable order.

Censor at the declared market boundary. Missing data are not independent censoring by assumption: outage-induced missingness may concentrate in stress. Report coverage and sensitivity, with no spurious increase in hold success from dropping violent missing periods.

## 7. Inputs and refresh

Baseline: price path up to `t`, time of day, prior high/low, VWAP distance, realized range, scheduled-event information and lag-trained seasonality. Candidate blocks: existing static exposures; signed public flow; inventory posterior; full nonlinear hedge stress; surface dynamics; matched liquidity/materiality; cross-product residuals; current auction phase; off-exchange response memory.

One-minute decision snapshots are a proposed research cadence. Event-triggered refreshes can later respond to a material input or state change, using existing event/history owners. Each forecast carries model freeze, data vintages, node version, target/session definition and latency. An updated forecast is a new decision record, not a correction of the earlier prediction unless the underlying source itself was corrected.

## 8. Calibration and output

Calibrate only on preceding matured labels. Report Brier/log scores for event probabilities, reliability by product/time/regime, interval coverage plus width, CRPS for distributions and normalized extreme-distance error. Proper scoring rules reward calibrated sharp distributions, not impressive hit rates from wide bands [R16]. Adaptive conformal intervals may be explored; long-run coverage is not per-state or stress-day conditional coverage [R17].

UI output: current price, remaining-session interval, separately identified zones with touch/hold/break definitions, probability range only when qualified, clock/coverage, mechanism and invalidation. The user should see 'unavailable' when a model is not admitted. A fresh numerical quote does not make an unvalidated forecast live.

<!-- Report-local source links. Scope and access limits are in SOURCE_REGISTER.md. -->

[R16]: https://sites.stat.washington.edu/people/raftery/Research/PDF/Gneiting2007jasa.pdf
[R17]: https://arxiv.org/abs/2106.00170
