# Mastermind Options Intelligence: academic evidence and replication gates

**Retrieval date: 2026-10-03.** Bounded public-research contribution for the parent’s single GitHub carrier. This report uses 18 academic or regulator research entries. It evaluates evidence and specifies tests; it does not establish Mastermind alpha or authorize production promotion.

## Executive finding

Options research supports several distinct information channels, with different data requirements and horizons. The most famous opening-flow result uses exchange classifications absent from ordinary public trade records [L02]. Surface signals are easier to observe but can reflect stock-borrow costs [L17]. Variance and tail premia describe compensation for risk, which must be separated from forecast probabilities [L08–L09]. Modern 0DTE findings depend on whether the estimand is new trading, accumulated inventory, or the presence of expiring contracts [L13–L15].

The useful next step is an incremental, preregistered evidence program tied to observable fields and existing baselines. None of these papers establishes that a generic combined options score improves Mastermind decisions.

**Access quality:** ten entries have the relevant full published/working manuscript available; two have the current abstract plus an earlier full draft; six rely on primary abstracts, author summaries, or indexed publisher passages. “Full” means the text was retrieved and relevant methods/results inspected, not that every proof/table has been independently reproduced. Unverified sample dates, coefficients and controls are explicitly left open. The JSON companion contains source URLs, retrieval date, tool references, version notes and structured ledger fields.

## Decisions the evidence supports

| Decision | Evidence basis | Consequence for implementation research |
|---|---|---|
| Classify a feature as exact, proxy, or unavailable before testing | L02–L05, L11, L16 | Exchange opening demand and public aggressor estimates need different names and claims. |
| Maintain direction, volatility, tail insurance and inventory as separate hypotheses | L03, L08–L09, L12–L15 | A result at one horizon/endpoint cannot silently validate another. |
| Make borrow and catalyst conditioning first-class comparisons | L06–L07, L12, L17–L18 | Test whether option features add information beyond these observable confounders. |
| Treat 0DTE amplification versus dampening as an unresolved, testable distinction | L13–L15 | Separate new flow from starting inventory, and preserve regime dependence. |
| Make quote timing and trade classification explicit gates | L10–L11, L16 | Unknown or complex observations remain unknown; abstention and coverage are reported. |

These are research design judgments drawn from the ledger, not claims that a particular feature will succeed.

## Evidence ledger

Each entry distinguishes what the source establishes from the proposed Mastermind implication. Reported returns are historical study results, generally portfolio statistics rather than forecasts for an individual security. Numerical magnitudes are included only where checked in the accessible primary source.

### L01. Easley, O’Hara, and Srinivas (1998)

**Option Volume and Stock Prices: Evidence on Where Informed Traders Trade** — Journal of Finance 53(2), 431–465.

**Access:** Primary publisher abstract; full text not retrieved.
- **Question:** Can informed traders choose options and reveal information through trading activity?
- **Sample / period:** Historical intraday equity/options observations; exact dates and selection criteria were not verified from accessible primary text.
- **Exact signal / treatment:** Directional option-volume categories distinguish bullish combinations (call buys/put sales) from bearish combinations (put buys/call sales).
- **Horizon:** Intraday lead–lag relations; exact lag grid not verified.
- **Verified result:** The publisher abstract reports information in option activity about subsequent stock prices. No numerical effect is admitted here.
- **Controls / identification:** Theoretical endogenous trading-location model; complete empirical controls require full-text review.
- **Data observability:** Trade-side information is necessary; total call/put volume is a different observable.
- **Limits:** Foundational evidence, with incomplete methodological access in this pass; not evidence that every options feature leads equities.
- **Mastermind implication:** Use as a directional-flow hypothesis and historical motivation, not a production calibration or priority claim.

**Sources:** [Publisher/AFA abstract](https://afajof.org/issue/volume-53-issue-2/); [Publisher record](https://onlinelibrary.wiley.com/doi/abs/10.1111/0022-1082.194060). **Evidence anchors:** Published abstract; empirical-table audit remains open.

### L02. Pan and Poteshman (2006)

**The Information in Option Volume for Future Stock Prices** — Review of Financial Studies 19(3), 871–908.

**Access:** Full published paper retrieved; targeted methods and results reviewed.
- **Question:** Does informed opening demand forecast stock returns?
- **Sample / period:** CBOE non-market-maker volume, January 1990–December 2001; actual buy/sell, opening/closing, and investor-type categories.
- **Exact signal / treatment:** Buyer-opening puts divided by buyer-opening puts plus calls; daily cross-sectional quintiles.
- **Horizon:** Next trading day and next week, with subsequent decay examined.
- **Verified result:** Low-ratio stocks outperform high-ratio stocks by over 40 basis points next day and over 1% next week on a risk-adjusted basis.
- **Controls / identification:** Market, size, value, momentum; information-asymmetry, leverage and liquidity comparisons.
- **Data observability:** The central signal uses nonpublic exchange classifications. Public quote-inferred trade direction does not recover opening status or investor identity.
- **Limits:** Publicly reconstructed flow predicts briefly then reverses; its incremental predictability disappears when the private component is included. Historical gross spreads are not current executable returns.
- **Mastermind implication:** Label OPRA reconstructions as proxies. Require labeled-data validation before claiming replication of the headline result.

**Sources:** [Author full paper](https://www.mit.edu/~junpan/volume.pdf). **Evidence anchors:** Abstract; data section; public-versus-private volume analysis.

### L03. Ni, Pan, and Poteshman (2008)

**Volatility Information Trading in the Option Market** — Journal of Finance 63(3), 1059–1091.

**Access:** Full published paper retrieved; targeted methods and results reviewed.
- **Question:** Does option demand reveal future volatility?
- **Sample / period:** CBOE non-market-maker activity, January 2, 1990–December 31, 2001.
- **Exact signal / treatment:** Sum of signed call and put contracts weighted by vega/option price, approximating the derivative of log option price with respect to volatility; baseline maturities exceed one week.
- **Horizon:** Individual future trading days at lags 1–5.
- **Verified result:** Volatility demand positively predicts subsequent high–low-based realized-volatility measures after controls. No portable numerical forecast coefficient is asserted.
- **Controls / identification:** Implied volatility, lagged realized volatility, absolute delta imbalance, option/stock activity, and earnings specifications.
- **Data observability:** Actual non-market-maker buys and sells; Black–Scholes weighting uses volatility from the preceding 60 trading days.
- **Limits:** This is volatility demand, not a bullish/bearish score. Plain vega flow is a different feature; inferred aggressor side is not investor identity.
- **Mastermind implication:** Preregister range/volatility endpoints separately and preserve the exact elasticity weighting as a named benchmark.

**Sources:** [Author full paper](https://web.mit.edu/people/junpan/npp.pdf). **Evidence anchors:** Equation (1), pp. 1064–65; forecasting regressions.

### L04. Johnson and So (2012)

**The option to stock volume ratio and future returns** — Journal of Financial Economics 106(2), 262–286.

**Access:** Full published paper downloaded from author-hosted PDF; targeted sections reviewed.
- **Question:** Can unsigned relative option activity predict returns?
- **Sample / period:** 1996–2010; 611,173 firm-weeks combining OptionMetrics, CRSP and Compustat.
- **Exact signal / treatment:** Weekly option contracts across strikes, expiring within the 30-trading-day window beginning five days after trade, divided by equity volume in 100-share lots.
- **Horizon:** Skip one trading day, then measure the following five trading days.
- **Verified result:** Low-minus-high O/S decile four-factor alpha is approximately 0.34% per week in the historical sample.
- **Controls / identification:** Factor returns, stock characteristics, prior returns, separate activity measures and short-sale-cost comparisons.
- **Data observability:** Volume and contract definitions are observable; historical universe, adjustments and maturity filters must match.
- **Limits:** High O/S predicts lower returns in this specification. It excludes same-day expirations and does not justify treating all option activity as bullish.
- **Mastermind implication:** A feasible public-data baseline, with original versus modern maturity buckets kept separate and borrowing conditions controlled.

**Sources:** [Author full paper](https://eso.scripts.mit.edu/docs/The-option-to-stock-volume.pdf); [Publisher record](https://www.sciencedirect.com/science/article/pii/S0304405X12000797). **Evidence anchors:** Section 3 and equation (7), pp. 267–68; Table 2.

### L05. Ge, Lin, and Pearson (2016)

**Why does the option to stock volume ratio predict stock returns?** — Journal of Financial Economics 120, 601–622.

**Access:** Primary institutional abstract and indexed publisher excerpts; full text not retrieved.
- **Question:** Which transactions explain O/S predictability?
- **Sample / period:** ISE Open/Close Trade Profile observations; exact sample dates were not verified from accessible primary text.
- **Exact signal / treatment:** Decomposition of relative volume into signed opening/closing transaction categories.
- **Horizon:** Weekly stock-return predictability; precise skip/formation convention requires full-text verification.
- **Verified result:** Opening call purchases are especially informative; closing call sales also contribute. Results do not support synthetic shorts being uniformly more informative than synthetic longs. No numerical magnitude admitted.
- **Controls / identification:** Accessible results compare trade categories and expiration weeks; complete regression specification remains unverified.
- **Data observability:** Exchange buy/sell and open/close classifications, not public aggregate volume alone.
- **Limits:** The decomposition challenges a single short-sale-friction explanation. Missing full text prevents a replication-grade specification.
- **Mastermind implication:** Preserve transaction type and strategy ambiguity; do not substitute subsequent open-interest changes for observed opening intent.

**Sources:** [Author institution record](https://hub.hku.hk/handle/10722/227461); [Publisher record](https://www.sciencedirect.com/science/article/pii/S0304405X16000167). **Evidence anchors:** Institutional abstract and publisher indexed passages; table audit open.

### L06. Cremers and Weinbaum (2010)

**Deviations from Put-Call Parity and Stock Return Predictability** — Journal of Financial and Quantitative Analysis 45(2), 335–367.

**Access:** Published abstract plus full March 2007 working-paper version; final tables not retrieved.
- **Question:** Do relative call/put prices forecast returns?
- **Sample / period:** Earlier draft: January 1996–December 2005. Do not assume every final-paper filter matches this version.
- **Exact signal / treatment:** Open-interest-weighted call-minus-put implied volatility for matched strike/expiration pairs.
- **Horizon:** Weekly subsequent stock returns.
- **Verified result:** Published abstract reports approximately 50 basis points per week between expensive-call and expensive-put portfolios and declining predictability over time.
- **Controls / identification:** Option versus equity liquidity; borrowing/rebate considerations. Final detailed specifications require final-text audit.
- **Data observability:** Paired option quotes, time-aligned stock price, valuation inputs and lag-appropriate open interest.
- **Limits:** Parity deviations can embed borrow costs and valuation conventions. Later evidence L17 materially qualifies the informational interpretation.
- **Mastermind implication:** Build a borrow-aware relative-price feature and a temporal-decay test; do not translate the old spread directly into forecast probability.

**Sources:** [Published record](https://doi.org/10.1017/S002210901000013X); [Earlier full manuscript, third-party mirror](https://chesler.us/resources/academia/Deviations%20from%20Put-Call%20Parity%20and%20Stock%20Returns.pdf). **Evidence anchors:** Published abstract; earlier working-paper data and signal definition.

### L07. Xing, Zhang, and Zhao (2010)

**What Does the Individual Option Volatility Smirk Tell Us About Future Equity Returns?** — Journal of Financial and Quantitative Analysis 45(3), 641–662.

**Access:** Full author-hosted accepted manuscript retrieved; targeted sections reviewed.
- **Question:** Does downside option pricing identify weak future stocks?
- **Sample / period:** January 1996–December 2005, OptionMetrics with equity, fundamentals and earnings data.
- **Exact signal / treatment:** IV of an OTM put with K/S in 0.80–0.95 minus an ATM call with K/S in 0.95–1.05; choose contracts closest to 0.95 and 1.00, respectively; 10–60 calendar days to expiration.
- **Horizon:** Weekly formation with a one-day skip; persistence beyond the next week is examined.
- **Verified result:** Low-skew stocks outperform high-skew stocks by approximately 10.9% annually after risk adjustment in the manuscript.
- **Controls / identification:** Size, value, momentum, volatility, turnover, historical skewness, option activity and related option signals.
- **Data observability:** Quoted surface and positive open interest; matched clocks and contract filters matter.
- **Limits:** The variable combines information, downside-insurance demand and pricing frictions; it is not a calibrated physical crash probability.
- **Mastermind implication:** Test incremental candidate deterioration after borrow, volatility and catalyst adjustment; maintain risk-premium versus information hypotheses.

**Sources:** [Author accepted manuscript](https://www.ruf.rice.edu/~yxing/option-skew-FINAL.pdf). **Evidence anchors:** Abstract; variable construction; cross-sectional controls.

### L08. Bollerslev, Tauchen, and Zhou (2009)

**Expected Stock Returns and Variance Risk Premia** — Review of Financial Studies 22(11), 4463–4492.

**Access:** Full published paper retrieved; targeted methods and results reviewed.
- **Question:** Does the aggregate price of variance risk predict equity returns?
- **Sample / period:** Monthly S&P 500 observations, January 1990–December 2007.
- **Exact signal / treatment:** Squared 30-day VIX minus preceding-month realized variance constructed from five-minute returns; both terms are observable at formation time. A forecast-based physical-variance alternative is also studied.
- **Horizon:** Monthly through multi-year, with strongest principal evidence around one quarter.
- **Verified result:** Quarterly regression adjusted R-squared is approximately 6.82%; higher variance premium predicts higher subsequent aggregate returns.
- **Controls / identification:** Valuation and macro-finance predictors; heteroskedasticity/overlap-robust inference.
- **Data observability:** Implied variance and already-realized variance on compatible scales; future realized variance is an outcome, not an available feature.
- **Limits:** Aggregate quarterly evidence does not establish next-day single-name direction. Variance and volatility spreads are distinct.
- **Mastermind implication:** Use as a market-risk-state benchmark with an explicit horizon and unit contract, separate from short-term deterioration alerts.

**Sources:** [Author full paper](https://public.econ.duke.edu/~boller/Published_Papers/rfs_09.pdf). **Evidence anchors:** Equation (22), data section 2.2, return-predictability tables.

### L09. Bollerslev and Todorov (2011)

**Tails, Fears, and Risk Premia** — Journal of Finance 66(6), 2165–2211.

**Access:** Full published paper retrieved; targeted methods and results reviewed.
- **Question:** How much compensation reflects extreme-tail risk and changing fear?
- **Sample / period:** High-frequency S&P futures, 1990–2008; index options, 1996–2008. Baseline estimation through June 2007 is applied to the later crisis interval.
- **Exact signal / treatment:** Physical jump-tail estimates from high-frequency returns compared with risk-neutral tails from short-maturity deep-OTM option prices.
- **Horizon:** Risk-premium decomposition and state variation, rather than a single next-day forecast target.
- **Verified result:** Tail compensation is economically material and fear varies beyond ordinary volatility. No tradable-alpha estimate is claimed here.
- **Controls / identification:** Separate physical and risk-neutral measures, jump/continuous components and crisis comparisons.
- **Data observability:** Requires broad option tails plus high-frequency history; tail estimation extrapolates from more frequent movements.
- **Limits:** Sparse extremes and extrapolation assumptions matter. Risk-neutral tail prices include compensation and cannot be equated with physical event frequencies.
- **Mastermind implication:** Expose downside-insurance state first; calibrate actual adverse-move probabilities separately on unseen outcomes.

**Sources:** [Author full paper](https://public.econ.duke.edu/~boller/Published_Papers/jf_11.pdf). **Evidence anchors:** Tail estimation framework; empirical data and crisis analysis.

### L10. Muravyev, Pearson, and Broussard (2013)

**Is there price discovery in equity options?** — Journal of Financial Economics 107(2), 259–283.

**Access:** Primary abstracts and indexed publisher methods passages; full text not retrieved.
- **Question:** Do option quotes add price information beyond current equities?
- **Sample / period:** Tick-level quotes for 36 liquid U.S. stocks and three ETFs, April 17, 2003–October 18, 2006 (882 trading days), verified in indexed publisher text.
- **Exact signal / treatment:** Disagreement between stock prices and option-implied stock prices from matched call/put quotes.
- **Horizon:** Immediate microstructure adjustment after disagreement.
- **Verified result:** The abstract finds no economically meaningful incremental option-price information; options adjust to the equity market. No numerical effect admitted.
- **Controls / identification:** Disagreement events are compared with similar control events; a larger, weaker-disagreement sample checks event-selection sensitivity. Complete filters still need full text.
- **Data observability:** Synchronized stock and options quotes with parity inputs.
- **Limits:** This null concerns a particular quote-level price-discovery question, not all future-return information in classified option flow.
- **Mastermind implication:** Require quote-age, asynchronous-update and contemporaneous-stock baselines before calling option prices leading indicators.

**Sources:** [Publisher abstract and methods excerpt](https://www.sciencedirect.com/science/article/abs/pii/S0304405X12001882); [Author institution record](https://experts.illinois.edu/en/publications/is-there-price-discovery-in-equity-options/). **Evidence anchors:** Publisher and institution abstracts; full-method audit open.

### L11. Savickas and Wilson (2003)

**On Inferring the Direction of Option Trades** — Journal of Financial and Quantitative Analysis 38(4), 881–902.

**Access:** Detailed primary publisher abstract; full text not retrieved.
- **Question:** How reliable are common option trade-signing rules?
- **Sample / period:** Historical options with known true direction; exact dates not verified from accessible primary text.
- **Exact signal / treatment:** Quote, Lee–Ready, Ellis–Michaely–O’Hara and tick-rule classifications.
- **Horizon:** Trade classification, not a return forecast.
- **Verified result:** Reported correct classifications are 83%, 80%, 77% and 59%, respectively, for each method’s classifiable subset; these are not identical-coverage comparisons.
- **Controls / identification:** Trade/quote location, size, moneyness, maturity, activity and complex index trades are examined.
- **Data observability:** True direction is needed for validation. Complex packages can make individual-leg execution prices misleading.
- **Limits:** Historical accuracy does not establish current vendor-feed accuracy. Excluding difficult observations changes coverage as well as accuracy.
- **Mastermind implication:** Return sign probability, abstention and coverage; validate modern feed-specific calibration and retain a separate complex/ambiguous category.

**Sources:** [Publisher abstract](https://www.cambridge.org/core/journals/journal-of-financial-and-quantitative-analysis/article/abs/on-inferring-the-direction-of-option-trades/FDA4541B57F78B2C8DCE129AFC25AAF0). **Evidence anchors:** Published abstract numerical results and qualification by classified subset.

### L12. Londono and Samadi (2023, revised record 2024)

**The Price of Macroeconomic Uncertainty: Evidence from Daily Options** — Federal Reserve International Finance Discussion Papers 1376.

**Access:** Full regulator working paper retrieved; targeted methods and results reviewed.
- **Question:** How do options price scheduled macroeconomic uncertainty?
- **Sample / period:** Daily S&P 500 option expirations, January 2017–May 2023; CPI, FOMC, payroll and GDP releases.
- **Exact signal / treatment:** Insurance/variance and related premium measures for expirations spanning announcements versus nearby expirations without them; principal contracts have 7–21 calendar days remaining.
- **Horizon:** Event insurance, evaluated before known releases; not necessarily same-day 0DTE trading.
- **Verified result:** Options spanning important announcements command greater insurance premia; the effect varies with uncertainty and risk-aversion state. No numerical estimate admitted.
- **Controls / identification:** Adjacent expiry comparisons and alternative maturity, strike and event specifications.
- **Data observability:** Surface snapshots plus the event calendar as known at formation time.
- **Limits:** Priced uncertainty does not reveal the sign of the announcement surprise. Working-paper author findings are not Federal Reserve policy.
- **Mastermind implication:** Make catalyst conditioning and event-specific variance normalization prerequisites for directional interpretations of elevated IV.

**Sources:** [Federal Reserve publication page](https://www.federalreserve.gov/econres/ifdp/the-price-of-macroeconomic-uncertainty-evidence-from-daily-options.htm); [Full paper](https://www.federalreserve.gov/econres/ifdp/files/ifdp1376.pdf). **Evidence anchors:** Sample construction and treatment/control design; paper-page version metadata.

### L13. Brogaard, Han, and Won (2026 current author listing)

**Does 0DTE Options Trading Increase Volatility?** — Working paper; presented at 2026 Conference on Financial Market Regulation.

**Access:** Current author summary and primary conference agenda; full current manuscript not retrieved.
- **Question:** Does greater 0DTE trading raise underlying volatility?
- **Sample / period:** Author chart covers January 2011–August 2023; the exact current estimation sample remains unverified.
- **Exact signal / treatment:** 0DTE trading activity instrumented by staggered introduction of index weekly options.
- **Horizon:** Underlying volatility; exact current outcome aggregation requires the full manuscript.
- **Verified result:** Current author summary reports that a one-standard-deviation trading increase raises volatility by 9.10% of its mean, remaining positive after gamma-hedging controls.
- **Controls / identification:** Instrumental-variable design and market-maker gamma controls are stated; complete specifications not verified.
- **Data observability:** Trading volume is observable; causal interpretation requires instrument/exclusion-assumption review.
- **Limits:** Older circulating versions report different magnitudes. This entry uses only the current author summary and does not treat it as full-method verification.
- **Mastermind implication:** Preserve an amplification hypothesis alongside L14–L15; compare estimands and regimes before resolving the apparent conflict.

**Sources:** [Author current summary](https://peterywon.github.io/); [SEC conference agenda](https://www.sec.gov/newsroom/meetings-events/13th-annual-conference-financial-market-regulation/13th-annual-conference-financial-market-regulation-day-one-agenda). **Evidence anchors:** Author page updated August 2026; SEC May 7, 2026 agenda confirms presentation, not findings.

### L14. Adams, Dim, Eraker, Fontaine, Ornthanalai, and Vilkov (2026-07-15)

**Do S&P 500 Options Increase Market Volatility? Evidence from 0DTEs** — Merged working paper.

**Access:** Full July 15, 2026 author-hosted manuscript retrieved; targeted methods and results reviewed.
- **Question:** How do expiring options and dealer positions affect intraday volatility?
- **Sample / period:** January 2018–December 2024; baseline calendar identification ends May 19, 2022; classified Cboe activity and futures observations.
- **Exact signal / treatment:** Presence of expiring contracts; market-maker gamma/hedging needs reconstructed from signed opening/closing histories, split into existing inventory and new trades.
- **Horizon:** Ten-minute realized volatility and subsequent intraday intervals.
- **Verified result:** Expiring-contract presence lowers ten-minute annualized realized volatility by 61 basis points on average. Earlier-established inventory drives the hedging shift, rather than new same-day positions.
- **Controls / identification:** Calendar variation and introduction comparisons; time effects; separate predictive intraday analysis is explicitly noncausal.
- **Data observability:** Exchange participant categories and position history, not a generic open-interest-times-gamma calculation.
- **Limits:** An average dampening effect does not rule out amplification in particular states. The manuscript supersedes two prior papers, which must not count as independent confirmations.
- **Mastermind implication:** Keep starting inventory separate from fresh flow; test state-dependent intraday mechanisms without projecting them onto five-day stock direction.

**Sources:** [Current full manuscript](https://www.jean-sebastienfontaine.com/papers/0dte-options-volatility.pdf); [Author version/lineage listing](https://www.vilkov.net/research.html). **Evidence anchors:** Title-page lineage; introduction; calendar design and inventory construction.

### L15. Amaya, Garcia-Ares, Pearson, and Vasquez (2025-01-25)

**0DTE Index Options and Market Volatility: How Large is Their Impact?** — Working paper.

**Access:** Full Cboe-hosted academic manuscript retrieved; targeted methods and results reviewed.
- **Question:** How large can measured dealer-gamma effects be?
- **Sample / period:** July 2020–June 2023; proprietary Cboe SPX/SPXW transactions and intraday underlying data.
- **Exact signal / treatment:** Market-maker inventory and gamma reconstructed using actual trade capacities; modeled hedging contribution to realized volatility.
- **Horizon:** Intraday, including 30-minute and full-day volatility.
- **Verified result:** Typical positive gamma dampens volatility; negative-gamma episodes amplify it. The estimated largest daily increase is 3.3 annualized volatility percentage points in this sample.
- **Controls / identification:** Inventory-based regressions and a model counterfactual removing the gamma contribution.
- **Data observability:** Detailed participant-side transaction data and accumulated positions are central.
- **Limits:** The maximum is a model-dependent historical counterfactual, not a universal upper bound or experimentally identified causal estimate. Cboe data support and research funding are disclosed.
- **Mastermind implication:** Use inventory uncertainty and state sensitivity, with explicit units; do not convert this estimate into a blanket safety claim about 0DTE.

**Sources:** [Full academic paper](https://cdn.cboe.com/resources/education/research_publications/gammasqueezes.pdf). **Evidence anchors:** Abstract; sample and inventory construction; volatility-impact counterfactual.

### L16. Fu, Li, Musto, and Pearson (2025-03-16)

**Hope at a Reasonable Price: Customer Use of Limit Orders in the 0DTE Market** — SEC DERA Working Paper.

**Access:** Full regulator working paper retrieved; targeted methods and results reviewed.
- **Question:** Can public data identify customer passive liquidity and execution costs?
- **Sample / period:** SPXW, July 1, 2020–September 28, 2023; OPRA with proprietary Cboe transaction validation.
- **Exact signal / treatment:** Customer limit-order presence from quote-condition codes, after correcting trade/quote sequencing problems.
- **Horizon:** Trade-level execution and intraday customer liquidity provision.
- **Verified result:** Customers frequently supply the best quotes; for actively traded slightly OTM contracts, their presence exceeds half the time in recent observations. No profitability claim about all retail traders follows.
- **Controls / identification:** Detailed trade/quote matching, sequencing reconstruction and participant-data comparisons.
- **Data observability:** Raw quote codes B/O/C identify customer interest at bid/offer/both when preserved; economic ordering can differ from naive timestamp sorting.
- **Limits:** Trade matching coverage is not side-classification accuracy. Reconstructing economic sequences must respect historical availability. DERA findings are authors’ views, not SEC policy.
- **Mastermind implication:** Audit vendor quote conditions and sequence semantics before signing flow; passive counterparty must not automatically be labeled dealer.

**Sources:** [SEC full paper](https://www.sec.gov/files/dera-hope-reasonable-prc-2503.pdf). **Evidence anchors:** Abstract; sequencing problem and quote-condition methodology.

### L17. Muravyev, Pearson, and Pollet (2025)

**Why does options market information predict stock returns?** — Journal of Financial Economics 172, 104153.

**Access:** Current published abstract plus full March 15, 2022 precursor; final tables not retrieved.
- **Question:** Do familiar option-IV predictors embed borrowing costs?
- **Sample / period:** 2022 precursor: July 2006–August 2015, Markit lending fees with OptionMetrics/CRSP. Final sample details require current full text.
- **Exact signal / treatment:** Call–put IV spread and skew, related analytically and empirically to stock-borrow fees.
- **Horizon:** Subsequent stock returns; monthly specifications inspected in the precursor, not asserted as the only final horizon.
- **Verified result:** The October 2025 published abstract reports at least a two-thirds reduction in IV-spread/skew predictability after excluding high-fee stocks.
- **Controls / identification:** Borrow-fee adjustment and low-fee comparisons; earlier regressions also examine familiar return characteristics.
- **Data observability:** Contemporaneous borrow fees or clearly marked missingness; rates/dividends and pricing inputs must align.
- **Limits:** The result substantially qualifies L06–L07; it neither proves zero remaining information nor measures Mastermind’s candidate-risk utility.
- **Mastermind implication:** Require borrow-conditioned incremental tests. A warning signal can retain decision value even when a short portfolio is uneconomic, but that value must be measured separately.

**Sources:** [Current institutional published abstract](https://experts.illinois.edu/en/publications/why-does-options-market-information-predict-stock-returns-3/); [Earlier full manuscript](https://www.aeaweb.org/conference/2023/program/paper/RsBt64RZ); [Published record](https://www.sciencedirect.com/science/article/pii/S0304405X25001618). **Evidence anchors:** Published abstract; 2022 precursor data and methodology; versions deliberately separated.

### L18. Weinbaum, Fodor, Muravyev, and Cremers (2023)

**Option Trading Activity, News Releases, and Stock Return Predictability** — Management Science 69(8), 4810–4827.

**Access:** Primary institutional published abstract; full text not retrieved.
- **Question:** Does news scheduling change which option transactions are informative?
- **Sample / period:** Corporate-news and classified option-activity sample; exact dates and full filters not verified from accessible primary text.
- **Exact signal / treatment:** Purchases versus sales of options, conditioned on scheduled/unscheduled announcements and timing relative to release.
- **Horizon:** News days and periods before releases; exact windows require full text.
- **Verified result:** Purchases are informative on news days and before unscheduled news, while pre-scheduled-release information appears in sales. No numerical effect admitted.
- **Controls / identification:** News scheduling and trading/margin-cost analyses are stated; complete specifications remain unverified.
- **Data observability:** Transaction categories and a point-in-time event/news calendar; future surprise labels are outcomes only.
- **Limits:** Missing full text prevents replication-grade implementation. The result rejects a uniform interpretation of elevated option purchases before known events.
- **Mastermind implication:** Preregister event interactions and keep purchases/sales separate; avoid treating earnings-related option activity as automatic directional confirmation.

**Sources:** [Author institution published abstract](https://experts.illinois.edu/en/publications/option-trading-activity-news-releases-and-stock-return-predictabi/). **Evidence anchors:** Published abstract; full-method audit open.

## Observability contract before Fable implementation

| Feature family | Minimum observable inputs | Unacceptable substitution | Appropriate status until validated |
|---|---|---|---|
| Opening buyer demand | Actual side, opening/closing state, participant scope, contract identifiers, timestamp and publication availability | Ask-side trades plus next-day open-interest changes presented as known opening purchases | Public-flow proxy; original academic replication blocked |
| Signed flow | Trades, valid surrounding quotes, conditions, sequence semantics, corrections, package/auction indicators where available | Every ask print is a customer purchase against a dealer; midpoint direction forced | Probabilistic classification with calibration and abstention |
| O/S | Equity and option volume in consistent units; original maturity and calendar conventions | Full-chain all-DTE volume called a Johnson–So replication | Distinct modern variant versus original benchmark |
| Call–put IV / skew | Synchronized paired quotes, rates, distributions/dividends, exercise convention, borrow costs, lagged OI, surface filters | Apparent parity deviation interpreted as private information without cost controls | Pricing-relative feature with confounder/missingness flags |
| Variance premium | Implied variance and lagged or forecast physical variance on matching units/horizons | Future realized variance as a feature; volatility difference labeled variance premium | Time-available market-state feature |
| Tail insurance | Adequate OTM surface coverage and explicit risk-neutral estimation | Risk-neutral tail mass labeled actual crash probability | Priced tail-risk state pending physical calibration |
| Dealer pressure | Participant-classified accumulated positions, or explicit inventory scenarios and uncertainty | Public OI times gamma presented as known dealer net gamma | Scenario estimate, with starting inventory separate from new flow |
| Event effects | Point-in-time event schedule and release timestamps | Later-known surprise or rescheduled calendar used as formation-time knowledge | Event-conditioned feature with timestamp provenance |

The table is a proposed engineering contract. It does not assert that the currently contracted vendor exposes these fields. Missing observables should produce an explicit unavailable/proxy state, not a guessed value.

## Reconcile 0DTE evidence without counting papers as votes

The current July 2026 Adams et al. manuscript expressly subsumes the earlier Dim–Eraker–Vilkov and Adams–Fontaine–Ornthanalai working papers [L14]. Store the old versions as provenance, not independent replications. The Brogaard–Han–Won current author summary remains an amplification result [L13]; its current full manuscript still needs review. Amaya et al. uses measured inventory and a modeled counterfactual [L15]. These are materially different identification designs.

For a preregistered comparison, ask four separate questions: does expiration availability change average volatility; does extra same-day trading change it; does starting dealer inventory predict it; and does the sign/magnitude change with liquidity or market conditions? Record the outcome frequency, aggregation, exposure definition, instrument, sample regime and inventory coverage for each. This separation permits a coherent result in which average dampening coexists with episodes of amplification.

## Incremental research packets for the existing program

The parent reports that the October 2 historical Theta retrospective was already completed and merged in #8286, with 60 evaluable cells and three within-family BH rejections, while point-in-time availability, out-of-sample validity and economics remain unproven. This worker has not independently audited that repository evidence. The proposals below are an overlay on that existing result, not instructions to recreate completed work.

### 1. Evidence-to-feature reconciliation

For every existing cell, attach the literature family, original signal definition, observed vendor fields, time-availability rule, tested horizon and replication status. Preserve the original result and classify differences explicitly: matched academic construction, modern proxy, different endpoint, or not evaluable. Only a concrete unresolved risk should trigger additional analysis.

### 2. Incremental baseline comparison

Freeze the candidate universe and compare the existing price/volume/realized-volatility/regime/catalyst/Prophet baseline with the same model plus a prespecified options family. Include an options-only comparison for interpretability. Use the same universe and availability rules for paired comparisons; report separate coverage effects rather than letting feature availability silently change the population.

Make one primary outcome/horizon explicit per family. Directional-return evidence, adverse excursion, realized range and calibration are different outcomes. A candidate-deterioration warning can be useful without supporting a profitable short portfolio, but the decision utility and false-positive cost must be specified before evaluation.

### 3. Confounder challenges

For IV relative prices, compare raw versus borrow-adjusted or low-borrow-fee subsets, with missing-borrow data identified. Add event-conditioned and event-excluded comparisons. For O/S, separate the historical maturity convention from 0DTE and other modern buckets. For signed flow, measure sensitivity to quote alignment, sign confidence, package ambiguity and exclusion rules. For dealer pressure, compare explicit inventory assumptions and starting-position versus new-flow components.

### 4. Temporal validation and uncertainty

Use a frozen untouched later period or a specified rolling out-of-time design. Purge training observations whose outcome windows overlap evaluation periods, and preserve revision/publication timestamps. Estimate uncertainty with dependence across dates and symbols considered. Register the full family of tested variants and corrections; a within-family BH rejection does not establish global discovery control, an independently replicated result, or positive net economics.

Record calibration, coverage, turnover/latency sensitivity and decision utility alongside statistical significance. Avoid changing thresholds after observing the validation sample. A research result should carry its horizon and data limitations into any future interface.

### 5. Promotion gates and bounded follow-ups

Hand Fable concrete research contracts only after feature lineage, time availability, baseline incrementality and evaluation rules are reviewable. A production gate must remain separate from the literature review. No unvalidated composite weighting follows from this report.

The highest-value remaining literature retrievals are the current full Brogaard–Han–Won manuscript and final full text/replication package for Muravyev–Pearson–Pollet (2025). The latter’s author-linked package was located, but was not downloaded or executed. Full texts for Ge et al., the event-flow paper, and the older signing/price-discovery studies would close explicitly marked method gaps; lack of access is not evidence of a null or positive result.

## Research-integrity notes

- Retrieval date is October 3, 2026; publication year, manuscript date and retrieval date are separate fields.
- No press coverage, vendor marketing claim or conference acceptance is used as proof of a quantitative result. A conference agenda verifies presentation only.
- Full working-paper access does not imply peer review. Regulator working papers express research findings, not adopted policy.
- This is a selective evidence map, not a systematic meta-analysis or a completed replication study. Differences across markets, eras, data access and endpoints prevent pooling the quoted returns as one expected-alpha estimate.
- Temporary reports are intended for incorporation into the parent’s authorized GitHub research carrier. This worker performed no GitHub write, production action, trading or external communication.
