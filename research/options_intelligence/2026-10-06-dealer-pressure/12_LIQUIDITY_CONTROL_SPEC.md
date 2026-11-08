# Liquidity and options materiality specification

**Status: SPEC_ONLY.** The research question is whether modeled hedge demand is economically large relative to the liquidity it could use. A large GEX number does not answer this question.

## 1. Three complementary denominators

For one hedge venue/instrument `v`, decision `t` and horizon `h`, define:

\[
R^{part}_{v,t,h}=\frac{|E_t[Q^{exec}_{v,t,h}]|}
{E_t[V_{v,t,h}]},\quad
R^{cap}_{v,t,h,\epsilon}=\frac{|Q^{exec}_{v,t,h}|}
{L_{v,t,h}(\epsilon)},\quad
J_{v,t,h}=\frac{|\widehat{Impact}_{v,t,h}|}{\widehat{\sigma}_{v,t,h}}.
\]

Quantities in each ratio must use the same units: shares/shares, contracts/contracts, or consistently converted dollar notionals. `V` is expected total traded volume; `L(ε)` is expected executable directional capacity within a declared price-impact tolerance; `J` uses estimated return impact divided by horizon return standard deviation (equivalently price impact divided by `P_t×σ_return`). None is a universal percentage probability of tape control.

Use a training-only time-of-day volume curve for `V`, updated with already-observed activity. It is a **participation proxy**, not immediately available liquidity. Historical ADV is a coarse baseline for event comparisons, not a final-five-minute depth denominator. Displayed top-of-book size is a snapshot, not total executable capacity. Realized spread and estimated impact inform capacity; they cannot simply be added to share depth because their units differ.

`L` combines displayed depth by distance, empirical depletion/replenishment, expected marketable flow, hidden liquidity response and allowed participation under the chosen scenario. Fit it on past observations with a reproducible execution/impact definition. Until continuous quote events/depth are admitted, report only `Rpart`; `Rcap` is unavailable. Never fabricate order-flow imbalance from a series sampled only when options trade.

## 2. Liquidity features and clocks

| Primitive | Proposed measurement | Restriction |
|---|---|---|
| Best bid/ask and size | Eligible event snapshots | Venue/aggregation and event coverage explicit |
| OFI | Sum signed bid/ask price-size event changes | Continuous eligible quote changes, not trade-sign volume |
| Depth | Size by side inside a price band | Cancellations and replenishment matter |
| Depletion | Loss of side depth over a defined event window | Separate trades from cancels where feed supports it |
| Replenishment | Reappearing executable size after depletion, lag-trained distribution | Future refill cannot be an earlier feature |
| Spread | Quoted spread; later effective/realized spreads as matured labels | Midpoint and trade clock align |
| Impact | Price response to signed flow conditional on state | Reverse causality; no automatic dealer attribution |
| Trade intensity | Eligible trades/contracts per second | Corrections and duplicated reports excluded |
| Basis | Synchronized futures/ETF/index residual | Different session and stale reference can dominate |

The Cont–Kukanov–Stoikov study motivates OFI and depth-conditioned impact and finds a less robust relation with volume alone [R10]. The queueing work of Cont–de Larrard motivates depletion-state variables [R11]. These are research supports, not imported fitted coefficients for current ES.

## 3. Joint uncertainty, not ratio of convenient point estimates

Sample or stress inventory, surface, execution policy and liquidity together. A downside shock may increase modeled selling while reducing depth; treating the numerator and denominator as independent understates tails. Report the distribution of `|Q|/L`, the probability mass near an unresolved/zero denominator, and capped display values with uncapped machine fields or explicit overflow reasons.

Distinguish `|E[Q]|` from `E[|Q|]`: opposite scenarios can cancel their mean while both require large trades. Report signed net pressure, expected absolute horizon-net demand and sign disagreement. Gross rehedging turnover is the separate path quantity `E[Σ_k|ΔX_k|]`. Never net SPX and Nasdaq books through a broad-market beta during a sector shock without residual-risk bounds.

If hedge demand can use ES **or** SPY, do not assign the entire amount to each and sum impacts. Choose a feasible allocation vector with liquidity costs and hedging residuals. Also do not assume summed venue depth is simultaneously accessible; cross-market substitution and arbitrage latency belong in the scenario.

## 4. Mechanism and identification

Gamma Fragility supports an interaction between a proxy of dealer gamma and underlying illiquidity; it is especially relevant to liquidity gating [R01]. It does not prove that a modern SPX day with a high mechanical ratio is controlled by options. Macro news can drive the price, IV, options activity and underlying liquidity at once.

Test lagged prediction first, with event/time/volatility controls. Test interaction terms separately from raw gamma. If pursuing causal claims later, state the instrument, excluded channels, placebo periods and treatment estimand; explanatory regressions and SHAP attributions are not causal evidence. Preserve options effects that are tiny relative to flow as informational context rather than elevating them into actionable nodes.

## 5. Proposed user states

Before calibration: **materiality unavailable**, **low modeled participation**, **potentially material under stated assumptions**, or **scenario-sensitive**. After a preregistered useful threshold is validated, a more compact 'options regime important today' label may be considered by the existing owner. Thresholds must come from training-only relationships to decision loss and calibration; do not invent a universal 10%, 20% or 0–100 control score.

A source-quality failure withdraws the assessment; it never produces 'options unimportant.' Separate missing liquidity from observed abundant liquidity. Show horizon and denominator in the same card as the result.

## 6. Acceptance and kill

Compare equal-complexity models using raw exposure, full-reprice demand, demand/expected volume and demand/capacity. Require a matched population and independent session confidence intervals. If the ratios do not add reliable out-of-sample improvement over the better simpler feature, retain that simpler feature and stop the expensive capacity estimator. If only thin single names show the effect, do not extrapolate it to ES/SPX. First-slice capacity work is conditional on the existing ES tape/depth owners and their source rights; a specification or open PR is not live liquidity evidence.

<!-- Report-local source links. Scope and access limits are in SOURCE_REGISTER.md. -->

[R01]: https://abarbon.com/papers/gamma-fragility
[R10]: https://arxiv.org/abs/1011.6402
[R11]: https://arxiv.org/abs/1104.4596
