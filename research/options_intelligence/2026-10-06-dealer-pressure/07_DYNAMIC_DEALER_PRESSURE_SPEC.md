# Dynamic dealer-pressure specification

**Status: SPEC_ONLY; original proposed extension.** Extend the current GEX, spot/time surface and options-flow owners. Current source already contains a spot-repriced gamma profile and a fixed-OI spot/time surface. The accepted October 3 contracts also contain complete/partial endpoint-rehedging reference kernels and mechanics assertions. This specification extends those contracts to inventory-conditioned whole-book demand and explicit uncertainty; it does not discover endpoint mechanics from scratch or create another GEX engine. [I03] [I11] [I23]

## 1. Four objects that must remain distinct

1. Option risk at a state: delta/gamma/vanna/charm of a covered book.
2. Target hedge position at a state: the underlying or futures position that neutralizes a stated risk convention.
3. Incremental hedge trade between two states: a change in target holdings.
4. Executed hedge flow and resulting impact: behavior and liquidity, not a Greek identity.

The same dollar exposure can arise from a price move, an IV change, a newly traded position or a multiplier change. Differencing dollar delta mixes new hedge units with revaluation of existing units unless decomposed.

## 2. Reference repricing

For one price coordinate `S`, currency, covered inventory `h_i` and appropriate contract multiplier `m_i`,

\[
B(S,\boldsymbol\sigma,t;h)=-\sum_i h_i m_i\Delta_i(S,\sigma_i,t),\qquad
Q^{target}_{0\to1}=B_1-B_0,\qquad H_{0\to1}=S_1Q^{target}_{0\to1}.
\]

Positive `Q` and `H` mean an underlying-equivalent purchase. For SPX this is a risk coordinate, **not executable SPX shares**; convert to an ES/SPY hedge vector using `08_CROSS_PRODUCT_EXPOSURE_SPEC.md`. `H` is USD reference notional at the target price. Only for a cash-equity purchase is the transaction cash change `−H`, excluding fees, carry and financing. SPX synthetic units have no cash transaction; futures reference notional is neither cash paid, margin nor variation P&L.

Do not use `S1×B1−S0×B0` as traded notional. The difference includes `(S1−S0)×B0`, revaluation of the original hedge. The witness file makes this error observable.

For a European vanilla with constant carry, the baseline pricing delta uses

\[
d_1=\frac{\log(S/K)+(r-q+\sigma^2/2)\tau}{\sigma\sqrt\tau},
\quad \Delta_c=e^{-q\tau}\Phi(d_1),\quad
\Delta_p=e^{-q\tau}[\Phi(d_1)-1].
\]

This formula is a reference convention, not a universal near-expiry pricing truth. Use forward-consistent European pricing for index contracts, a suitable American model for ETF early exercise and discrete dividends, and the correct futures-option convention. Never feed a physically delivered adjusted contract into a standard multiplier by default.

`τ` ends at the economic payoff fixing, not the settlement cash-payment date. Keep last-tradable time, fixing rule, exercise cutoff and settlement payment distinct. At a known European fixing, delta approaches its payoff derivative except at the strike, where a numerical convention must not pretend to resolve pin risk. A contract awaiting an uncertain fixing is a separate state, not a positive epsilon time-to-expiry. Post-fixing residual hedge unwind requires an explicit inventory/exercise model; deleting option gamma is not proof of an immediate stock trade.

## 3. Exact separation of inventory and repricing

For unchanged canonical contract identity and multiplier, with `δh=h1−h0` and `δΔ=Δ1−Δ0`,

\[
Q^{target}=-\sum_i m_i\left[h_{i0}\delta\Delta_i+
\delta h_i\Delta_{i0}+\delta h_i\delta\Delta_i\right].
\]

The first term reprices the starting book, the second is new signed position risk, and the last is their interaction. An exact symmetric allocation is

\[
Q^{target}=-\sum_i m_i\left[
\tfrac{h_{i0}+h_{i1}}2(\Delta_{i1}-\Delta_{i0})+
(h_{i1}-h_{i0})\tfrac{\Delta_{i0}+\Delta_{i1}}2\right].
\]

This prevents counted-twice flow. If a transaction is already in `h1`, do not add its full delta flow again to the resulting hedge change. Package legs enter once under their economic contract identity.

For a deliverable/multiplier change, first rebase both endpoints into a common economic contract coordinate or use risk per contract `r_i=m_iΔ_i`. The exact identity becomes `Q=−Σ[h0 δr+δh r0+δh δr]`. Non-cash deliverable components require a risk vector. A corporate-action reclassification must not appear as a new hedge trade solely because contract counts or multipliers changed.

For spot, surface, time and inventory attribution, compare all factor orders using an exact Shapley decomposition, or expose a fixed order plus interaction residual. Four factors need at most sixteen unique corner repricings to support all permutations; reuse values. Greek approximations are a separate diagnostic:

\[
Q^{lin}\approx-\sum_i h_i m_i(\Gamma_i\delta S+
Vanna_i\delta\sigma_i+Charm_i\delta t).
\]

Here charm is the derivative with respect to **advancing calendar time**, `−∂Δ/∂τ`, with expiry fixed. IV is a decimal: a 1.2-point increase is `0.012`, not `1.2`. Report approximation residual in hedge units and dollars; percentage error is null when the reference response is near zero. No scalar charm sign becomes a directional predictor. The prior signed-charm rejection remains binding research evidence.

## 4. State surface and future surface paths

Represent the object as `H_t(S*, surface*, t*, inventory_scenario, hedge_policy)` conditional on a frozen anchor, not a universal three-dimensional force. A scalar IV axis is only a parallel-shift scenario; the full surface is `σ(K,expiry)` or a low-dimensional set of level/skew/curvature/term factors.

| Surface model | What is held fixed? | Use | Main limit |
|---|---|---|---|
| Fixed IV | Each contract's IV | Unit/sign diagnostic | Not a predicted market reaction |
| Sticky strike | Vol attached to strike/expiry | Structural baseline | Misses leverage/skew response |
| Sticky delta | Vol attached to defined forward-delta coordinate | Alternative risk convention | Requires consistent iterative strike/delta mapping |
| Learned response | Lag-trained level/skew/term shocks conditional on spot, regime and time | Forecast candidate | Endogeneity and regime shift; no future fitting |
| Stress envelope | Joint spot, vol and liquidity shocks with explicit dependence | Robustness / tail scenarios | No probability unless calibrated |

An arbitrage-consistent fitted surface improves numerical integrity; it does not forecast surface motion. SVI/SSVI offers a relevant static-arbitrage framework [R15]. Treat total variance `σ²τ` and annualized IV separately near expiry; vanishing time value does not imply annualized IV itself must converge to zero.

**Pricing delta and minimum-variance hedge delta are different conventions.** Spot/IV covariance can change an optimal hedge. Hull–White provides a relevant alternative [R14]. If a surface-consistent total derivative or empirical hedge delta already includes this covariance, do not add the same vega/covariance adjustment a second time. First slice uses a clearly named pricing-delta convention and keeps alternative hedge policies as ablations.

## 5. Proposed numerical domain

Start with the existing scenario engine's domain and quote-selection constraints. Proposed research evaluations: spot shocks 0, ±0.25%, ±0.5%, ±1%; parallel IV 0, ±1, ±3 points; horizons 1, 5, 15, 30 minutes and contract-specific close. Add the commission's exact −0.35% / +1.2 points / +20 minutes scenario. Refine around near-spot strikes, expiry boundaries and response crossings until an error tolerance is met; do not sample a huge fixed grid merely to look detailed.

Near-expiry tests must include 3,601/3,600/3,599/1,800/900/300/60/1 seconds; fixed-IV and price-refitted-IV comparisons are different tests. Required numerical cases: zero holdings, long/short call and put, vertical/calendar spreads, nearly offsetting portfolios, changing multipliers, multiple gamma crossings, tangencies without sign changes, missing IV/Greeks, no crossing, and expiry/fixing boundaries.

Report numerical error, missing-book bounds, inventory disagreement, surface-model disagreement and forecast distribution separately. Near cancellation, compute signed and gross exposures and a cancellation ratio. A small net plus large gross is a sensitivity warning, not certainty of quiet trading.

## 6. Endpoint versus path

For a fixed fully covered book under immediate exact target tracking, cumulative signed target changes telescope to `B_T−B_0`. Summing them along a path adds no new net endpoint information. However,

\[
Turnover=\sum_k|B_{k+1}-B_k|,\quad
Cash=-\sum_k P^{exec}_k(B_{k+1}-B_k)
\]

depend on the path. The Cash expression is for cash-equity executions; for futures track commissions, margin and variation P&L separately, without treating price times contracts as cash paid. Liquidity consumption, temporary impact, execution costs and hedge delays also depend on the path. A short-gamma book can buy on rallies and sell on reversals, generating large gross turnover with almost zero net endpoint flow.

Maintain `target_change`, `gross_rehedge_turnover`, `expected_execution_next_horizon` and `impact_distribution` as distinct outputs. Do not rename turnover as net pressure.

Publish exact signed components `Q_0DTE`, `Q_1to7D` and `Q_8plusD` using the contract's declared calendar-day and fixing-state cohort at the anchor. Track cohort migration separately when an interval crosses a session/expiry boundary. Their sum plus explicit uncovered/residual components reconciles to covered total demand. Expected execution velocity is `v_exec(t,h)=E_t[X_(t+h)−X_t]/h` in shares/second or futures-contracts/second; its USD-reference rate uses a declared price and multiplier. It is unavailable as an expectation unless a probabilistic execution policy is justified; a selected policy yields scenario velocity only.

## 7. From target demand to expected execution

Introduce an explicitly hypothetical actual hedge state `X_t`, target `B_t`, and execution policy. A minimal scenario is delayed partial adjustment `dX_t=κ_t(B_t−X_t)dt`, with unknown initial hedge gap and instrument allocation. Alternative immediate/full and no-externalization scenarios bound useful sensitivity; 0–100% is a chosen scenario range, not a universal bound on real dealers.

Fit execution-response parameters only against suitable independent measurements. Regressing aggregate ES flow on modeled dealer demand is an association with many other traders, not ground-truth dealer execution. Inventory-management theory permits quote adjustment and risk warehousing [R19]; it does not calibrate the actual SPX response lag. Use named assumptions until data support estimation.

## 8. Publication fields

Anchor state and time; price coordinate; exact contract/reference/input revisions; inventory model; covered expiries; quote/Greek quality; surface model; hedge convention; target spot/time; buy/sell units; USD conversion price; cohort and attribution components; interaction residual; numerical tolerance; scenario bounds; optional calibrated predictive intervals; update cause; next expiry/fixing transition; stale/gap/null reasons; correction lineage; semantic authority flags.

Refresh on qualified input changes or the incumbent clock. Proposed minute-level pilot does not claim high-frequency execution readiness. The same canonical output drives Exposure, Flow context and any future calibrated node view.

<!-- Report-local source links. Scope and access limits are in SOURCE_REGISTER.md. -->

[I03]: https://github.com/mastermindx-market-intelligence/macro/blob/c9631f8b2469587dec643bec94b16e77c09ef511/research/options_intelligence/2026-10-03/CONTRACTS.md
[I11]: https://github.com/mastermindx-market-intelligence/macro/blob/c9631f8b2469587dec643bec94b16e77c09ef511/engine/gex_engine.py
[I23]: https://github.com/mastermindx-market-intelligence/macro/blob/c9631f8b2469587dec643bec94b16e77c09ef511/engine/options_scenario_surface.py
[R14]: https://doi.org/10.1016/j.jbankfin.2017.05.006
[R15]: https://arxiv.org/abs/1204.0646
[R19]: https://math.nyu.edu/inmemoriam/avellaneda/HighFrequencyTrading.pdf
