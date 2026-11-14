# Research synthesis: mechanisms, conditional models and decision quality

Review date: 2026-10-16. This supplements the 35-source register in [ASSESSMENT](ASSESSMENT.md); it is not a claim to have replicated the cited studies. Primary papers, author/institution pages and official methodology documents were used. Each entry states what was actually inspected and what does **not** transfer automatically to Mastermind.

The synthesis is intentionally decision-oriented: what information to represent, which competing explanation to test, which model may help, and what would falsify the proposed benefit. A cited paper is not source-use permission or a model-promotion receipt.

## A. Group leadership and economic mechanism

### L1 — Industry momentum is a separate component from stock momentum

Moskowitz and Grinblatt, *Do Industries Explain Momentum?* (1999). Reviewed the author/AQR research summary and journal metadata. [Primary source](https://www.aqr.com/insights/research/journal-article/do-industries-explain-momentum).

The study attributes an important part of intermediate-horizon stock momentum to industry effects. Its principal horizon is not minute-by-minute rotation. **Design consequence:** evaluate group selection first and measure residual stock contribution separately. **Discriminator:** a stock strategy that loses its excess after conditioning on industry/style has captured exposure rather than established stock alpha. Nothing here qualifies Mastermind's T2 trigger or proves present-day sector timing.

### L2 — Capital cycles concern supply and competition, not only demand

Marathon London, *The Home of Capital Cycle Investing*. Reviewed the firm's own public process description and the preceding assessment's institutional synthesis. [Primary source](https://www.marathon.co.uk/the-home-of-capital-cycle-investing/).

The investment lens emphasizes profitability, capital allocation and competitive supply responses. **Design consequence:** extend existing demand-chain/Foresight evidence with industry-specific capacity, inventory, pricing and financing hypotheses. **Discriminator:** incremental prediction beyond price and revisions; a persuasive capex narrative that adds no forward information is not a qualified signal. This is evidence of a firm's stated method, not a transparent replication of its investment results.

### L3 — A rate increase can contain different economic information

Jarociński and Karadi, *Deconstructing Monetary Policy Surprises—The Role of Information Shocks* (AEJ: Macroeconomics, 2020). Reviewed the publisher abstract; complimentary PDF retrieval was unsuccessful. [Primary source](https://www.aeaweb.org/articles?id=10.1257/mac.20180090).

The paper separates policy and information shocks using joint high-frequency asset responses around policy announcements under a structural design. **Design consequence:** preserve event context and distinguish financing pressure from improving economic information. **Discriminator:** rate-sensitive sector effects should not be assumed invariant to the nature of the shock. Do not label every daily rates/stocks co-movement causally using this result; event timing and identification assumptions matter.

### L4 — Real-yield and breakeven proxies are not pure expectations

D'Amico, Kim and Wei, *Tips from TIPS* (Federal Reserve FEDS 2014-24). Reviewed the official abstract. [Primary source](https://www.federalreserve.gov/pubs/feds/2014/201424/201424abs.html).

Their term-structure analysis shows why liquidity premiums can distort common real-rate and inflation-expectation proxies. **Design consequence:** keep nominal yield, real-yield proxy, breakeven, liquidity and source limitations distinct; do not count the same yield change repeatedly. **Discriminator:** a proposed sector relationship should survive sensible alternative rate specifications and stress/liquidity controls. Historical premium estimates are not imported as current values.

## B. Conditional return models and risk exposure

### L5 — Nonlinear interactions are promising; the sample must support them

Gu, Kelly and Xiu, *Empirical Asset Pricing via Machine Learning* (RFS, 2020; NBER version 2018/2019). Reviewed the primary NBER abstract/search record; direct HTML retrieval returned 403. [Primary source](https://www.nber.org/papers/w25398).

The authors identify predictive gains from nonlinear interactions in a broad stock-level setting, with recurring momentum, liquidity and volatility information. **Design consequence:** admit bounded nonlinear challengers after a regularized baseline. **Discriminator:** same folds, inputs, tuning accounting and costs; a challenger must add held-out value. Large-stock-panel evidence cannot justify an unconstrained model on eleven sectors or a promise of intraday pivots.

### L6 — Characteristics can describe time-varying risk, not just alpha

Kelly, Pruitt and Su, *Characteristics Are Covariances* (JFE, 2019; NBER 24540). Reviewed the primary NBER abstract. [Primary source](https://www.nber.org/papers/w24540).

IPCA uses characteristics to instrument time-varying loadings on latent factors. **Design consequence:** treat dynamic exposure estimation as a candidate explanation before calling a characteristic residual alpha. **Discriminator:** compare with simpler prior-only factor controls and distinguish concurrent covariance fit from forward prediction. A latent-factor layer is a later challenger, not a prerequisite service or automatic sector model.

### L7 — An optimizer can amplify estimation error

DeMiguel, Garlappi and Uppal, *Optimal Versus Naive Diversification: How Inefficient is the 1/N Portfolio Strategy?* Reviewed the publisher abstract and bibliographic record. [Primary source](https://academic.oup.com/rfs/article-lookup/doi/10.1093/rfs/hhm075).

The paper's tested estimators did not consistently beat equal weighting across its datasets once estimation effects were considered. **Design consequence:** retain equal-weight and simple allocation benchmarks, shrink unstable estimates and bound concentration. **Discriminator:** out-of-sample net policy value, not in-sample frontier improvement. This is not a universal theorem that optimization can never work, nor a transferable numerical minimum sample size for this project.

### L8 — Covariance shrinkage addresses one source of instability

Ledoit and Wolf, *Honey, I Shrunk the Sample Covariance Matrix*. Reviewed the BSE primary research abstract; the repository's catalogue date is not treated as the original publication date. [Primary source](https://bse.eu/research/working-papers/honey-i-shrunk-sample-covariance-matrix).

Shrinkage reduces extreme covariance-estimation errors that can disturb allocation. **Design consequence:** test stable risk estimation through the existing portfolio owner. **Discriminator:** genuine held-out risk and turnover improvement. Better covariance does not repair biased return forecasts, source leakage or invalid tail assumptions; it cannot independently authorize sizing.

## C. Trading time, transitions and uncertainty

### L9 — Signal decay and trading cost belong in the policy

Gârleanu and Pedersen, *Dynamic Trading with Predictable Returns and Transaction Costs* (Journal of Finance, 2013). Reviewed the primary NBER abstract/version record. [Primary source](https://www.nber.org/papers/w15205).

The model distinguishes predictors by decay and derives partial adjustment toward a changing target under trading costs; its reported empirical illustration uses commodity futures. **Design consequence:** test partial adjustment/no-trade regions against fixed-cadence rebalancing. **Discriminator:** matched net wealth paths and cost sensitivity. A slowly developing economic thesis and a short-lived price impulse should not automatically receive identical turnover treatment. The result is not a ready-made sector sizing rule.

### L10 — Online change detection is not retrospective peak picking

Adams and MacKay, *Bayesian Online Changepoint Detection* (2007). Reviewed the authors' arXiv abstract. [Primary source](https://arxiv.org/abs/0710.3742).

The method tracks a distribution over elapsed time since a change under a specified generative model. **Design consequence:** it is a candidate for a clearly defined residual transition problem after simple causal thresholds. **Discriminator:** full-origin false alarms, delay, missingness and economic policy value. Its assumptions and chosen hazard/observation model must be tested; a change probability is not a probability that a sector trade succeeds.

### L11 — Adaptive interval validity and investment value differ

Gibbs and Candès, *Conformal Inference for Online Prediction with Arbitrary Distribution Shifts* (JMLR, 2024). Reviewed the primary paper abstract. [Primary source](https://jmlr.org/papers/v25/22-1218.html).

The procedure adapts interval calibration to changing distributions and evaluates applications including volatility. **Design consequence:** consider adaptive uncertainty only after reconciling the actual feedback delay and forecast horizon. **Discriminator:** predeclared coverage, interval usefulness and economic value; an interval that widens whenever uncertain may be statistically honest yet unusable for allocation. Do not claim conditional validity for every selected sector or regime from a marginal/long-run result.

### L12 — Selection changes the calibration problem

Bao, Huo, Ren and Zou, *CAP: A General Algorithm for Online Selective Conformal Prediction with FCR Control* (JMLR, 2025). Reviewed the abstract and relevant full-paper sections 2–5, including Proposition 1, Assumption 1 and the selection/adaptation discussion; inspected the PDF. [Primary paper](https://www.jmlr.org/papers/volume26/24-0452/24-0452.pdf).

The finite-sample result uses independence/exchangeability and selection symmetry conditions; distribution-shift extensions target different adaptive guarantees. **Design consequence:** calibrate the selection process, not just all-sector predictions. **Discriminator:** actual selected-sector coverage with serial dependence, overlapping outcomes and delayed labels. Rare selections can produce uninformative intervals. The paper motivates a candidate, not a transferred guarantee for this financial application.

### L13 — Recent uncertainty-aware sorting is a challenger, not established protection

Liu, Luo, Wang and Zhang, *Uncertainty-Adjusted Sorting for Asset Pricing with Machine Learning* (January 2026 arXiv preprint). Reviewed the full-text introduction and methodology sections, not a replicated empirical study. [Primary preprint](https://arxiv.org/abs/2601.00593).

The proposed sorting differs from conservative lower-bound selection: its long side uses optimistic upper bounds. The paper describes primarily volatility-related gains and does not make interval-coverage qualification its objective. **Design consequence:** test decision use of uncertainty as a separate policy comparison. **Discriminator:** genuine net benefit after exposure controls and matched asset/time assignment. Residual width must not automatically be equated with parameter uncertainty. Publication status and model assumptions limit transfer; this is not a recommendation to implement its rule.

## D. Research integrity is an intelligence capability

### L14 — Multiplicity must include the search that produced the model

Harvey, Liu and Zhu, *… and the Cross-Section of Expected Returns* (RFS, 2016; NBER 20592). Reviewed the primary NBER abstract/version record. [Primary source](https://www.nber.org/papers/w20592).

A large search over factors changes the interpretation of conventional significance. **Design consequence:** preserve candidate count, horizons, tuning and original failures under one declared study family. **Discriminator:** conclusions that survive the correct error-control procedure and untouched/prospective evidence. A single larger t-statistic threshold is not a substitute for the actual dependence, selection and preregistration design.

### L15 — A historical number and a historically knowable number are different

Federal Reserve Bank of St. Louis, FRED real-time-period documentation. Reviewed the official documentation. [Primary source](https://fred.stlouisfed.org/docs/api/fred/realtime_period.html).

The default view can represent today's knowledge of history; real-time periods support historical vintages. **Design consequence:** join by actual knowledge cutoff and retain revision identity. **Discriminator:** deliberately substitute a later vintage; the as-known reader must reject it or disclose a different evidence mode. An old observation date alone proves no point-in-time feature.

### L16 — Research-data methods change

Kenneth French Data Library, official methodology notices. Reviewed metadata only; no return file was downloaded and no native held research phase was run. [Primary source](https://mba.tuck.dartmouth.edu/pages/faculty/Ken.French/data_library.html).

The FIZ-to-CIZ transition changes return construction, including dividend timing, and historical series can be revised. **Design consequence:** pin dataset version and method as well as file path. **Discriminator:** reproducing an old model with refreshed data must either match the original data contract or be reported as a new experiment. No claim is made about the historical investability of every research portfolio.

## E. What is genuinely advanced in the proposed design

The proposed advance is not a larger collection of indicators. It is a structured combination of economic mechanisms, conditional models and decision-aware uncertainty with preserved evidence boundaries.

**First, describe exposure to changes rather than only label regimes.** A company's funding profile, pricing power, input costs and customer demand can mediate how a macro shock affects its economics. Test these interactions rather than assume every industry within a sector responds identically.

**Second, use a multi-clock mechanism map.** A source can be leading for earnings while lagging market expectations. Record whether an observation concerns demand, supply, financing, reported profitability or pricing, and test its incremental value at the intended horizon.

**Third, quantify the uncertainty in choosing among groups.** A model's best point forecast may be the noisiest. Joint outcomes, exposure overlap and selection-aware validation help distinguish genuine confidence from an arbitrary ordering.

**Fourth, test the decision rule itself.** The same forecast can produce different outcomes under immediate, staged, delayed or no-action policies. Costs, signal decay, cash return and common terminal dates determine whether the forecast is useful.

These are research hypotheses and architectural choices. None is claimed to deliver precision or alpha before the native qualification path succeeds. The concrete mechanism questions and future work packets are in [READINESS_AND_DELEGATION](READINESS_AND_DELEGATION.md).

## Review boundary and remaining research obligations

Abstract-level review identifies methods and transfer limits; it does not replace full methodological replication. Before implementing a selected advanced challenger, the bounded research worker must read its actual method/assumptions, bind the exact version, specify how Mastermind data violate or meet those assumptions, and pass a discriminating synthetic comparison against simpler alternatives. No paper's released code or proprietary implementation is copied in this package.

A full source-level read of the native V2.1 preregistration confirmed that existing α, Holm family, size, power, verdict and look rules remain binding. This supplement deliberately does not alter them. The next native registration must explicitly state how any new target relates to the preserved hypotheses and prior failures.
