# Academic literature review and adjudication

**Evidence cut: 2026-10-06.** This is a mechanism and research-design review, not a meta-analysis with pooled causal estimates. The source register distinguishes current drafts, older versions, full-PDF inspection, author summaries and abstract-only access. A source listed here was not necessarily read cover to cover; the consequential method/claim and access limit are recorded.

## 1. What the literature can support

The defensible research programme is conditional: option intermediation can change underlying demand; effects depend on signed positions, hedge behavior, liquidity, product, clock and economic state. That does not imply that a public OI map measures the relevant positions, that hedges execute immediately, or that a strike is an extreme-price predictor.

The strongest empirical studies often use participant or opening/closing data absent from ordinary public trades. Their findings motivate a value-of-information experiment, not an assertion that a public quote-location proxy replicates their measurement.

Four evidence classes remain separate:

| Class | Appropriate interpretation | Inappropriate promotion |
|---|---|---|
| Identified empirical design | Estimated effect for a stated treatment under identification assumptions | Universal coefficient for every product/regime |
| Predictive association | Feature precedes an outcome conditional on the tested controls | Dealer execution causality or tradable alpha |
| Theoretical/mechanical model | A coherent channel under stated assumptions | Calibrated probabilities or actual inventory |
| Practitioner/vendor study | Candidate mechanism, measurement or negative comparator | Independent proof without reproducible sample, labels and scoring |

## 2. Dealer gamma and 0DTE: the central evidence

### R01 — Barbon and Buraschi, Gamma Fragility

**Version/access:** 2021 author/SSRN revision; author summary and abstract inspected. **Design:** dealer-gamma proxy interacted with stock illiquidity. **Result:** reported momentum/reversal patterns depend on the interaction. **Limit:** proxy inventory, historical stock setting and observational identification do not provide actual SPX hedge trades. **Implication:** test demand × liquidity and matched simpler controls; do not translate a gamma sign directly into support/resistance. [R01]

### R02 — Adams, Dim, Eraker, Fontaine, Ornthanalai and Vilkov, Do S&P 500 Options Increase Market Volatility? Evidence from 0DTEs

**Version/access:** July 15, 2026, targeted full-PDF methods/appendix inspection. This draft **subsumes two earlier papers**. **Design:** calendar variation in expiring contracts, plus a separate intraday predictive study using participant-derived positions. **Result:** average volatility attenuation is associated especially with positions accumulated before expiry day. **Limit:** calendar exclusion restrictions remain assumptions; the intraday futures-flow part is explicitly noncausal and cannot identify dealers' executions. **Implication:** split inherited positions from same-day trading, test expiry presence separately from volume share, and do not count predecessor drafts as independent replications. [R02]

### R03 — Amaya, Garcia-Ares, Pearson and Vasquez, 0DTE Index Options and Market Volatility: How Large is Their Impact?

**Version/access:** January 25, 2025; targeted full PDF. **Design:** participant-coded Cboe SPX/SPXW trade history, aggregate market-maker positions and model counterfactuals. **Result:** positive versus negative gamma has the expected conditional damping/amplification association; estimated magnitudes come from the fitted counterfactual. **Limit:** starting inventory/history, actual hedge execution and model specification remain consequential; a simulated maximum is not a universal causal bound. **Implication:** a scoped participant benchmark is achievable in principle and should precede an elaborate public-inference system. [R03]

### R04 — Fu, Li, Musto and Pearson, Hope at a Reasonable Price: Customer Use of Limit Orders in the 0DTE Market

**Version/access:** March 16, 2025 PDF hosted by SEC; methods inspected. **Design:** detailed SPXW participant/order-interest records and trade/quote alignment. **Result:** customer liquidity provision is material to understanding this market. **Limit:** the richer research dataset cannot be inferred from ordinary OPRA quote location. **Implication:** a passive buyer can be a customer; aggressor side must remain separate from dealer capacity, opening/closing and permanent inventory. Careful quote ordering is a measurement requirement, not cosmetic cleanup. [R04]

### R05 — Brogaard, Han and Won, 0DTEs and market volatility

**Version/access:** current author research page updated in 2026; latest full paper was unavailable in this review. **Design disclosed:** staggered expiration introductions instrumenting 0DTE activity. **Result disclosed:** higher activity raises volatility in that specification. **Limit:** author-summary access cannot support a full methods audit; instrument exclusion and the treatment differ from R02. **Implication:** retain a live conflicting result. Expiry presence, same-day activity share and inherited dealer gamma are different estimands; opposite coefficients need not be logically inconsistent. [R05]

### R08 — Ni, Pearson, Poteshman and White, Does Option Trading Have a Pervasive Impact on Underlying Stock Prices?

**Version/access:** Review of Financial Studies 2021, published online in 2020; institutional abstract inspected. **Design:** option market-maker hedge rebalancing and stock-price dynamics. **Result:** evidence consistent with noninformational hedging effects on volatility and large moves. **Limit:** the historical single-stock setting is not a current SPX calibration. **Implication:** supports studying the transmission channel while preserving inventory, liquidity and product distinctions. [R08]

## 3. Signed option flow, inventory and volatility demand

### R06 — Pan and Poteshman, The Information in Option Volume for Future Stock Prices

**Version/access:** 2006 journal paper, author PDF. **Design:** buyer-initiated opening activity identified using special exchange data. **Result:** informative option-volume measures predict subsequent stock returns in the sample. **Limit:** public ask/bid classification lacks the opening and participant information used in the study. **Implication:** maintain a separate labeled-data benchmark and do not cite the paper as validation of ask-side equals customer-opening. [R06]

### R07 — Savickas and Wilson, On Inferring the Direction of Option Trades

**Version/access:** 2003 study; publisher web posting has a later date; abstract inspected. **Design:** compares trade-sign algorithms with identified trade direction. **Result:** classification is imperfect and depends on the method and trade type, particularly complex trades. **Limit:** historical accuracy is not today's OPRA accuracy; classifiable subsamples differ. **Implication:** use chronological calibration, abstention, package handling and risk-weighted error, not a borrowed universal success rate. [R07]

### R12 — Gârleanu, Pedersen and Poteshman, Demand-Based Option Pricing

**Version/access:** 2009 journal version, with older working-paper lineage; primary abstract. **Design:** theoretical and empirical demand effects when option risk cannot be perfectly hedged. **Result:** demand can affect option prices and implied-volatility structure. **Limit:** does not identify actual underlying hedge orders or a short-horizon directional target. **Implication:** volatility demand and inventory externalization are separate channels; imperfect hedging belongs in the execution-policy uncertainty. [R12]

### R13 — Bollen and Whaley, Does Net Buying Pressure Affect the Shape of Implied Volatility Functions?

**Version/access:** 2004, author-hosted PDF. **Design:** demand pressure and implied-volatility behavior across option classes. **Result:** supports treating demand and IV shape jointly. **Limit:** demand/IV feedback is endogenous; coefficients from that setting are not an intraday dealer execution law. **Implication:** independently model surface response and test raw flow versus hedge-demand transformations. [R13]

### R20 — Ni, Pan and Poteshman, Volatility Information Trading in the Option Market

**Version/access:** Journal of Finance, June 2008, author PDF. **Design:** non-market-maker volatility demand using historical exchange categories. **Result:** demand contains information about future realized volatility and affects option prices. **Limit:** this is volatility information, not automatically directional stock information, and relies on richer categories than public trade sign. **Implication:** keep the existing non-market-maker volatility-demand ontology separate from dealer inventory and signed underlying pressure. [R20]

## 4. Pinning, vanna, charm and the volatility surface

### R09 — Ni, Pearson and Poteshman, Stock Price Clustering on Option Expiration Dates

**Version/access:** 2005 journal study; primary indexed abstract. **Design:** stock-price clustering around expiration strikes. **Result:** documents expiration-related clustering. **Limit:** historic equities, endogenous strike selection and multiple mechanisms do not establish a universal max-pain target. **Implication:** test frozen strike/zone distances against matched non-expiry and shifted-strike placebos, preserving the already observed day's extreme. [R09]

### R14 — Hull and White, Optimal Delta Hedging for Options

**Version/access:** 2017 journal record and primary indexed abstract; full current paper unavailable. **Design:** a hedge adjustment reflecting the relationship between underlying and implied-volatility changes. **Result:** minimum-variance hedge choice can differ from textbook pricing delta. **Limit:** not a dealer-book estimator or a market-impact model. **Implication:** name pricing-delta versus empirical/minimum-variance conventions and avoid counting the same spot/vol covariance adjustment twice. [R14]

### R15 — Gatheral and Jacquier, Arbitrage-Free SVI Volatility Surfaces

**Version/access:** 2013 preprint revision / 2014 publication; arXiv abstract and version metadata. **Design:** conditions and parameterizations for static-arbitrage consistency. **Result:** supplies a useful surface-integrity framework. **Limit:** an arbitrage-free surface fit does not forecast its motion. **Implication:** separate numerical admissibility from sticky-strike, sticky-delta and learned surface dynamics. [R15]

### Existing Mastermind adjudication: preserve negative results

The current OPEX/vanna/charm adjudication records surviving conditional concentration/volatility effects, stronger controlled vanna-relief, a refuted simple signed-charm hypothesis, changed charm-intensity interpretation, and pin/placebo/root-class qualifications. This commission does not rerun or promote those results. They are adverse priors against a new directional charm story and inputs to exact ablation design. [I15]

No strong independent evidence retrieved here justifies a universal sign rule for intraday charm-driven returns. Vanna and charm are legitimate derivatives under a specified model; prediction requires inventory, surface motion, execution and liquidity. The appropriate next test is full repricing with those factors individually and jointly, preserving their interaction and the prior failed hypotheses.

## 5. Underlying liquidity, queues and hedge behavior

### R10 — Cont, Kukanov and Stoikov, The Price Impact of Order Book Events

**Version/access:** 2011 preprint revision / 2014 publication; primary arXiv record. **Design:** high-frequency order-book events and short-horizon price changes. **Result:** OFI and depth explain price response more robustly than trade volume alone in the studied data. **Limit:** contemporaneous impact is not a dealer-specific causal effect or an imported ES coefficient. **Implication:** require continuous eligible quote-event evidence and estimate liquidity response within the target market. [R10]

### R11 — Cont and de Larrard, Price Dynamics in a Markovian Limit Order Market

**Version/access:** 2011 preprint / 2013 publication; primary arXiv record. **Design:** queue-depletion model with analytical price dynamics. **Result:** explains how state-dependent queues shape price transitions. **Limit:** model assumptions do not account for every modern venue or hidden-liquidity behavior. **Implication:** depletion/refill and first-passage state are useful candidates, but must beat simpler price/volume models. [R11]

### R19 — Avellaneda and Stoikov, High-Frequency Trading in a Limit Order Book

**Version/access:** 2008 paper, author-hosted sources. **Design:** inventory-sensitive quoting under uncertainty. **Result:** dealers can manage inventory through quotes as well as transactions. **Limit:** theory does not estimate current SPX dealers' hedge lag. **Implication:** distinguish target hedge from actual externalization; quote adjustment, netting and risk warehousing can weaken a mechanical target-to-flow mapping. [R19]

## 6. Probability forecasts and evaluation

### R16 — Gneiting and Raftery, Strictly Proper Scoring Rules, Prediction, and Estimation

**Version/access:** 2007, author PDF. **Design:** theory of probabilistic prediction and proper scoring. **Result:** scores can reward honest distribution forecasts rather than arbitrary hit-rate optimization. **Limit:** a proper score does not cure leakage, wrong labels or dependent observations. **Implication:** use Brier/log loss, quantile loss and CRPS with fixed outcomes, matched populations, calibration and interval-width checks. [R16]

### R17 — Gibbs and Candès, Adaptive Conformal Inference Under Distribution Shift

**Version/access:** 2021 preprint revision. **Design:** adaptive coverage under changing distributions. **Result:** motivates coverage monitoring and adaptation. **Limit:** aggregate or long-run coverage is not a guarantee for each time-of-day, stress state or conditional dealer regime. **Implication:** use conformal methods as a tested calibration layer with state-level diagnostics, not a blanket “90% confidence” claim. [R17]

### R18 — OCC/OIC open-interest mechanics

**Version/access:** current primary education/FAQ pages. **Design:** clearing-accounting definitions, not a predictive study. **Result:** OI depends on both sides' opening/closing and subsequent exercise/adjustment processes. **Limit:** the net count does not identify participant ownership or unique trade assignments. **Implication:** use later OI as a reconciliation constraint; signed dealer changes depend on buyer/seller capacity, whether the dealer opens or closes. [R18]

## 7. Closing, index/ETF arbitrage and off-exchange research

Venue rules and feed specifications govern measurable fields and clocks; an empirical auction result cannot override those contracts. The six adjacent primary studies below complete the review of close effects, index/ETF transmission and off-exchange market quality.


These six entries support mechanisms and benchmark design. They do not supply a validated Mastermind model or establish current tradable alpha.

| Primary study | What the accessible evidence supports | Sample/access boundary | Research implication |
|---|---|---|---|
| Bogousslavsky & Muravyev, 2023, “Who trades at the close?” [A49] | Indexing and ETF activity help explain auction growth; price impact and short-lived closing deviations deserve distinct measurement. | Publisher abstract/highlights accessed; full article blocked. Author companion data describes 2010–2018 NYSE/Nasdaq common stocks, price >$5 and capitalization >$100m at month start [A50]. | Use auction-volume and price-deviation benchmarks; do not infer that every imbalance reverses. |
| Jegadeesh & Wu, 2022, “Closing auctions: Nasdaq versus NYSE” [A51] | Exchange comparison of closing-auction impact/resiliency and associations with ETF/index flows. | Indexed publisher abstract accessed; full text blocked and exact estimation sample not verified. | Exchange-specific estimates and adequate price-impact baselines are necessary. |
| Brown, Davies & Ringgenberg, 2021, “ETF Arbitrage, Non-Fundamental Demand, and Return Predictability” [A52] | ETF arbitrage can transmit demand to underlying securities and be associated with subsequent reversal. | Journal author digest accessed; full sample/implementation not verified. Evidence is not a minute-level final-close rule. | Separate primary-market flow scenarios, arbitrage mechanism and measured executable response. |
| FCA Occasional Paper 68, 2025, “ETF (Mis)pricing” [A53] | Primary/secondary transaction data permit richer AP inventory and pricing analysis. | Official summary: 128 ETFs, 2018–2022; confidential regulatory observations are not a publicly obtainable feed. | Treat AP inventory as latent unless a comparable legal observation source exists. |
| Chang, Hong & Liskovich, NBER 2013 / RFS 2015, “Regression Discontinuity and the Price Effects of Stock Market Indexing” [A54] | Membership-boundary designs can isolate index-demand price effects. | NBER abstract/digest and indexed paper accessed; Russell setting 1996–2012, with pre/post-banding distinctions. | Event design can identify local effects; it does not identify all rebalance flow or transfer automatically to 2026 intraday trading. |
| Zhu, 2014, “Do Dark Pools Harm Price Discovery?” [A55] | A theory of informed/uninformed venue selection, execution risk, lit liquidity and price discovery. | Full 43-page theoretical paper accessed; equilibrium results are conditional, not a signed empirical data product. | Dark activity can change market quality without revealing bullish/bearish dealer positioning. |

The author-provided closing-auction dataset has aggregate late-day and auction variables, not a full live NOII history. It can be a low-cost external sanity benchmark subject to access/reuse terms; its linked dataset was not downloaded [A50]. Modern 2019/2024/2026 rule regimes require fresh validation.



Across these adjacent topics, the implementation implication is precise: separate public schedules and inventory scenarios from actual auction messages; distinguish in-kind ETF creation from underlying cash buying; model price response and later reversal rather than assigning motive; and measure off-exchange prints at their legally supplied execution/report clocks. Full treatment and exact sources are in reports 11, 13 and 14.

## 8. Contradiction resolution and falsifiable priorities

| Apparent contradiction | Resolution to test | Consequence for Mastermind |
|---|---|---|
| 0DTE dampens versus increases volatility | Expiring inherited inventory, activity share and calendar treatment differ | Register each variable and estimand separately; no blanket “0DTE stabilizes” label |
| Large option volume versus small dealer gamma | Gross turnover can net across participants and structures | Estimate net position change and gross activity separately |
| Countercyclical hedge response versus “magnet” | Damping can exist without an anchored inward drift field | Require two-sided attraction evidence, not only positive gamma |
| Accurate trade signing versus bad dealer inference | Aggressor and capacity are different latent variables | Calibrate separately and preserve unidentifiability |
| Strong intraday Greek changes versus weak price forecast | Inventory may be wrong or externally hedged weakly; liquidity/news can dominate | Benchmark better information and liquidity before complexity |
| Favorable close hit rate versus no predictive value | Wider/more zones, later redrawing and late information can inflate hits | Freeze zones, width, universe and known-at; use proper scores |
| Descriptive vendor study versus empirical alpha | Disclosure may omit sample, labels, costs or held-out calibration | Use it as a comparator, not a transferable performance claim |

The scientific priority is an information-ladder test with a scoped participant benchmark, exact endpoint repricing and honest latency. The next priority is whether liquidity normalization adds value beyond the same flow and price inputs. Closing-auction and off-exchange work should progress as separately measurable adjacent families, not as explanations added after observing the close.

<!-- Report-local source links. Scope and access limits are in SOURCE_REGISTER.md. -->

[A49]: https://www.sciencedirect.com/science/article/pii/S1386418123000502
[A50]: https://bogousslavsky.github.io/data/
[A51]: https://www.sciencedirect.com/science/article/pii/S0304405X21005092
[A52]: https://revfin.org/etf-arbitrage-non-fundamental-demand-and-return-predictability/
[A53]: https://www.fca.org.uk/publications/occasional-papers-fca-research/occasional-paper-68-etf-mispricing
[A54]: https://www.nber.org/papers/w19290
[A55]: https://www.mit.edu/~zhuh/Zhu_darkpool_RFS.pdf
[I15]: https://github.com/mastermindx-market-intelligence/macro/blob/c9631f8b2469587dec643bec94b16e77c09ef511/research/OPTIONS_OPEX_VANNA_CHARM_ADJUDICATION.md
[R01]: https://abarbon.com/papers/gamma-fragility
[R02]: https://www.jean-sebastienfontaine.com/papers/0dte-options-volatility.pdf
[R03]: https://cdn.cboe.com/resources/education/research_publications/gammasqueezes.pdf
[R04]: https://www.sec.gov/files/dera-hope-reasonable-prc-2503.pdf
[R05]: https://peterywon.github.io/
[R06]: https://www.mit.edu/~junpan/volume.pdf
[R07]: https://www.cambridge.org/core/journals/journal-of-financial-and-quantitative-analysis/article/abs/on-inferring-the-direction-of-option-trades/FDA4541B57F78B2C8DCE129AFC25AAF0
[R08]: https://experts.illinois.edu/en/publications/does-option-trading-have-a-pervasive-impact-on-underlying-stock-p/
[R09]: https://www.sciencedirect.com/science/article/pii/S0304405X05000577
[R10]: https://arxiv.org/abs/1011.6402
[R11]: https://arxiv.org/abs/1104.4596
[R12]: https://academic.oup.com/rfs/article-abstract/22/10/4259/1590158
[R13]: https://www.whaley.info/_files/ugd/1362e1_81f94ba850fb4ec4aea173770b355408.pdf
[R14]: https://doi.org/10.1016/j.jbankfin.2017.05.006
[R15]: https://arxiv.org/abs/1204.0646
[R16]: https://sites.stat.washington.edu/people/raftery/Research/PDF/Gneiting2007jasa.pdf
[R17]: https://arxiv.org/abs/2106.00170
[R18]: https://www.optionseducation.org/referencelibrary/faq/general-information
[R19]: https://math.nyu.edu/inmemoriam/avellaneda/HighFrequencyTrading.pdf
[R20]: https://web.mit.edu/people/junpan/npp.pdf
