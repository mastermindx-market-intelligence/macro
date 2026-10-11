# Cross-product dealer-book integration: contract economics and normalization

**Research date:** 2026-10-06. **Evidence class:** official exchange/clearing specifications plus original mathematical design. No account entitlement, live inventory, execution practice of a particular dealer, or empirical hedge ratio was observed. All examples below are hypothetical arithmetic.

## 1. Decision

A common hedge-equivalent view is defensible only after contract-specific valuation and fixing rules have been preserved. Start with native exposures and produce an explicitly conditional common-factor projection. Keep SPX/SPXW, XSP, SPY, ES-option and ES-future books separately inspectable. Apply the same rule to NDX/NDXP, XND, QQQ and NQ. A single dollar total cannot identify which dealers own the positions, whether the same intermediaries can net them, or which underlying they will actually transact.

The current Macro scenario surface supports one root, one scalar multiplier, supplied positive time-to-expiry, fixed OI and sticky-strike IV. It is useful reference machinery, but not a qualified multi-product book. The proposed cross-product layer belongs above the existing reference-data, Greek and source owners; it must not create a second options or futures data plane.

## 2. Contract specification matrix

These are standard, unadjusted contracts. Actual series/reference data takes precedence, including FLEX terms, corporate actions, holiday changes and newly listed products. “Cash” below describes option settlement; a futures option that delivers a cash-settled future is still deliverable at the option layer.

| Instrument | Native underlying and multiplier | Exercise and fixing/settlement distinction | Required treatment |
|---|---|---|---|
| SPX standard AM | Full S&P 500 index; $100 per index point | European, cash; standard AM fixing uses a special opening quotation derived from component opening prices. Ordinary trading ceases on the preceding business day. [X01] [X02] | Preserve AM root/series identity. Do not model as an actively tradable Friday 0DTE contract or substitute a universal 09:30 instant for the completed SOQ. |
| SPXW PM | Full S&P 500 index; $100 per point | European, cash; closing component prices determine exercise value. Expiring contracts ordinarily stop at 16:00 ET, 13:00 on specified half days. [X01] [X03] | Last trade, close fixing, publication/revision and cash payment are separate clocks. |
| XSP | One-tenth SPX index; $100 per XSP point | European, PM cash settlement; expiring Weeklys/EOM normally cease at 15:00 Chicago. [X04] [X05] | Delta in XSP points must be scaled by 0.1 before comparing dollars per SPX point. |
| SPY options | SPY ETF shares; normally 100 shares per contract | American, delivery of ETF shares; exercise/assignment can alter the equity inventory. Standard share delivery is T+1. [X03] [X06] | Dividend/borrow and early-exercise risk matter. Spot SPY/SPX ratio is a measured basis, not an identity. |
| ES futures | Exact CME futures month; $50 per futures index point | Futures exposure is to its actual contract/basis. [X07] | Retain exact expiry and roll mapping, with no back-adjusted continuous contract as tradable identity. |
| ES weekly/EOM options | One specified ES futures contract; $50 per option-premium point | European variants deliver the future; exercise uses ESF based on the final 30-second fixing window, ordinarily ending 16:00 ET. American quarterly variants and European quarterly-PM variants also exist. [X08] [X09] [X10] | Exercise style cannot be assigned solely from “ES.” Preserve option root and exact underlying future. Delivery must remain in the terminal-state book. |
| NDX / NDXP | Full Nasdaq-100 index; $100 per point | European and cash. The family includes AM and PM; NDXP is PM, with XQC closing settlement and expiring trading ordinarily ending 16:00 ET. [X11] [X12] | Keep NDX versus NDXP series and settlement identifiers, even when a vendor places both in one chain. |
| XND | One-hundredth NDX; $100 per XND point | European PM cash; XNDC derives from constituent official closing values, with expiring trading ordinarily ending 16:00 ET. [X13] | XND is 1/100 NDX, not 1/10. Preserve final settlement revisions separately from the 16:00 forecast. |
| QQQ options | QQQ ETF shares; normally 100 shares per contract | American, delivery of ETF shares. [X06] [X11] | No timeless exact NDX/QQQ conversion; use contemporaneous prices, training-only hedge ratios and residual basis scenarios. |
| NQ futures | Exact CME futures month; $20 per point | Distinct futures contract/basis. [X07] | S&P/ES and Nasdaq/NQ are separate common-factor complexes unless a separately justified cross-index hedge is modeled. |
| NQ weekly/EOM options | One specified NQ future; $20 per premium point | European weekly/EOM variants deliver the future; NQF fixing uses the final 30-second window ordinarily ending 16:00 ET. American quarterly/serial variants also exist. [X14] [X15] | Preserve exercise style, root, exact underlying month, option cutoff, fixing and resulting futures position. |

The official Nasdaq factsheets explicitly allow revisions to closing index values after 16:00. An eventual final settlement label and the value known to a user at 16:00 are therefore different data versions. That does not authorize a fixed delay assumption for every feed. [X12] [X13]

CME’s older general weekly FAQ contains historical listing-cycle language. Use it for the documented distinction between American and European families, and prefer the specific current product pages/security definitions for actual listed expiries. A recent crawl does not make every paragraph an operative present-day contract schedule. [X09] [X14] [X15]

## 3. A mathematically consistent common numeraire

Let I be the chosen common index factor, U_p the native underlying of product p, m_p its monetary/deliverable multiplier, h_i signed option inventory in contracts, and Delta_i the derivative of the option’s quoted premium with respect to U_p. Define the local conversion

    a_p = dU_p / dI

and native dollar sensitivity per index point

    A_i = h_i * m_p * Delta_i * a_p.

For index products, a_SPX = 1, a_XSP = 0.1, a_NDX = 1, and a_XND = 0.01 within the corresponding complex. ETF and futures a_p are model inputs tied to current prices, financing, dividends, basis and the declared horizon.

One contract of hedge future f has sensitivity M_f * a_f dollars per index point. The full target futures hedge is therefore

    n_f(state) = - sum_i A_i(state) / (M_f * a_f(state)).

Do not multiply futures option deltas by another 100. An option quoted on ES with multiplier 50 and delta 0.5 has a target hedge of minus 0.5 ES contracts before other holdings/netting; its multiplier already matches the underlying future. Similarly a standard NQ option at delta 0.5 maps to minus 0.5 NQ.

An equivalent formulation uses beta-scaled dollar delta:

    D_i = h_i * m_p * Delta_i * U_p * beta_p,
    beta_p = d log(U_p) / d log(I),
    n_f = - sum_i D_i / (M_f * F_f * beta_f).

Here beta is a local exposure conversion, not a claim that historical statistical beta is stable during an auction or a stress event. The two formulations agree when a_p = U_p * beta_p / I.

For a future state x*, report the incremental target hedge

    delta_n_f = n_f(x*) - n_f(x0)

and, if a dollar figure helps users,

    endpoint_trade_notional = delta_n_f * M_f * F_f(x*).

This is signed notional valued at the endpoint. It is not futures cash paid, financing need, execution P&L, or the total cash traded along a rebalance path. An actual path of hedge transactions additionally requires a rebalance policy, execution instruments, latency/cost model and inventory transitions.

### Hypothetical unit check

Assume delta 0.5, matched index sensitivity, and negligible futures basis solely for the arithmetic:

- One SPX contract: 100 × 0.5 = $50 per SPX point, equivalent to one ES.
- Ten XSP contracts: 10 × 100 × 0.5 × 0.1 = $50 per SPX point, also one ES.
- One SPY option at an assumed SPY/SPX derivative of 0.1: 100 × 0.5 × 0.1 = $5 per SPX point, or 0.1 ES.
- One NDX contract: 100 × 0.5 = $50 per NDX point, or 2.5 NQ.
- One hundred XND contracts: 100 × 100 × 0.5 × 0.01 = $50 per NDX point, or 2.5 NQ.
- A QQQ option needs an explicit a_QQQ. Replacing it with an unexplained fixed 1/40 or 1/50 is not an admissible conversion.

These examples normalize sensitivity; they do not prove a dealer will execute the theoretical hedge or have access to the same netting pool.

## 4. Full-state repricing and basis

The scenario generator should produce native U_p*, forward/futures F_p*, volatility surfaces, rates/dividends and remaining economic times from a common scenario. Reprice each contract in its suitable model before aggregation. Compute the comparison once with frozen basis, then add clearly identified basis/dividend/financing shocks and empirical residual scenarios.

For European cash-index options, forward/carry and discounting must be coherent. For American ETF options, discrete dividends, borrow and early exercise require a suitable model and accepted reference data. For options on futures, the underlying is F, with the model’s discounted/premium convention preserved. A universal Black–Scholes spot model plus one scalar q is a diagnostic approximation, not a product-complete valuation engine.

A historical statistical hedge ratio can be estimated on training-only, synchronized observations at the intended horizon. Preserve the estimation window, weighting, missingness and uncertainty. Estimate stressed and close-window residuals rather than assuming full-session beta applies during a rebalance auction. Do not update an intraday forecast’s hedge ratio from the closing price it is trying to predict.

For a stock/ETF liquidity denominator and a futures denominator, put both in the same economic units and horizon before comparison. Futures displayed contracts × multiplier × price and ETF displayed shares × price are not automatically additive executable capacity. Cross-venue substitution, simultaneous demand, quote replenishment, spread costs and stress correlation can make their sum overstate usable liquidity. Begin with alternative instrument-allocation scenarios, not an unexplained sum of all available depth.

## 5. Settlement, expiry and inventory continuity

The pressure model must explicitly represent these transitions:

1. **Cash-settled option:** payoff fixing removes option delta after the economic fixing is resolved; any pre-existing underlying hedge can remain until a declared unwinding policy executes. A model may compare “unwind immediately” with delayed/partial unwind. Neither is an observed instruction.
2. **Physically delivered ETF option:** assignment converts option exposure to a stock position. Dropping expired options and setting their hedge requirement to zero without adding delivered shares can fabricate an unwind.
3. **Option delivering a future:** resulting ES/NQ exposure belongs in the post-expiry inventory. It is distinct from the option’s final value and from the future’s daily settlement.
4. **AM settlement:** last tradable time precedes economic fixing. Model overnight/gap exposure separately and retain uncertainty while constituent opens are incomplete.
5. **Halted component, corporate action or correction:** preserve an unresolved/finalized reference state. A later corrected closing index value cannot rewrite the feature used before the correction became available.
6. **Holiday/half day:** derive event times from exact series and session calendars. Fixed 16:00 or “third Friday” shortcuts are insufficient.

These are accounting requirements implied by the product specifications, not predictions of when aggregate dealers hedge. [X02] [X06] [X08] [X12] [X13] [X14]

## 6. Netting and double-counting rules

There are three different forms of duplication:

- **Record duplication:** the same option trade redistributed by multiple sources. Resolve at source identity/correction lineage; never add both.
- **Economic overlap:** distinct options in SPX, SPY and ES have overlapping factor risk. They are legitimate separate contracts and must not be deduplicated merely because the factor exposure is similar.
- **Unobserved common ownership/netting:** whether the same dealer owns offsetting legs across products. Preserve separate product priors and at least two netting scenarios; ordinary OPRA/OI does not identify this mapping.

Report gross positive and negative sensitivity by product, the conditional net, and unclassified/excluded exposure. An apparently small common net can conceal large opposite exposures in separate intermediaries or illiquid venues. An apparently large gross value can exaggerate aggregate external hedging when dealers net internally.

Inventory posteriors across products are generally dependent. A jointly constructed ensemble should carry common dealer/customer-flow assumptions and market-wide shocks. Do not obtain falsely narrow bands by independently sampling each root and assuming cancellation. If only scenario weights exist, call the output a scenario envelope, not a calibrated credible interval.

## 7. Exact eligibility and falsification requirements

Before admitting a cross-product total, require:

- Exact option and deliverable identity, product family, exercise style, fixing identifier/rule, underlying future month and valid-time reference version.
- Native multiplier, quoted units, currency, price basis and delta convention.
- Causally consistent option/underlying/forward/volatility observations and a complete eligibility denominator.
- Native per-product quantities that reconcile to the published common-factor conversion.
- Named inventory, basis, exercise and execution-allocation scenarios.
- Expiry-transition accounting that reconciles the option, delivered asset, existing hedge and cash payoff.
- Separate exclusion/null reasons for absent ES/NQ options, adjusted ETF series, unknown calendars, stale basis or missing reference data.
- Same-source duplicate controls and product-level gross/net disclosures.

Numerical acceptance tests should include SPX↔10 XSP and NDX↔100 XND scale equivalence for economically matched synthetic contracts; futures-option delta conversion; carry shocks; sticky-strike/sticky-delta changes; American ex-dividend boundaries; AM/PM and half-day fixtures; exact future roll; post-expiry delivered inventory; and unknown multiplier/underlying refusing aggregation.

Statistical acceptance is separate: test whether the common projection improves future pressure/range predictions over native products and price/liquidity baselines. A successful unit conversion earns no predictive claim. If cross-product uncertainty is larger than the signal or the incremental source cost exceeds useful forecast improvement, retain native displays and defer aggregation.

## Official source register

<!-- Report-local source links. Scope and access limits are in SOURCE_REGISTER.md. -->

[X01]: https://www.cboe.com/tradable-products/sp-500/spx-options/spx-specifications
[X02]: https://cdn.cboe.com/resources/spx/Settlement_of_Standard_AM_Settled_SP_500_Index_Options.pdf
[X03]: https://www.cboe.com/tradable_products/sp_500/spx_weekly_options/specifications/
[X04]: https://www.cboe.com/tradable-products/sp-500/xsp-options/specifications
[X05]: https://www.cboe.com/tradable_products/sp_500/mini_spx_options/specifications
[X06]: https://www.theocc.com/clearance-and-settlement/clearing/equity-options-product-specifications
[X07]: https://www.cmegroup.com/education/courses/introduction-to-equity-index-products/discover-equity-index-notional-value-and-price
[X08]: https://www.cmegroup.com/articles/faqs/e-mini-s-p-500-tuesday-and-thursday-options-frequently-asked-questions.html
[X09]: https://www.cmegroup.com/trading/equity-index/weekly-eom-options-faq.html
[X10]: https://www.cmegroup.com/education/articles-and-reports/e-mini-sp-500-quarterly-pm-options-european-style-faq.html
[X11]: https://www.nasdaq.com/products/north-american-markets/nasdaq-100-options-xnd-ndx
[X12]: https://www.nasdaq.com/NDXP-factsheet
[X13]: https://www.nasdaq.com/XNDindexoptions
[X14]: https://www.cmegroup.com/articles/faqs/e-mini-nasdaq-100-tuesday-and-thursday-options-frequently-asked-questions.html
[X15]: https://www.cmegroup.com/trading/equity-index/files/emini-nasdaq-100-futures-options.pdf
