# Mastermind Options Intelligence: competitor evidence and design implications

Research cutoff and retrieval date: **2026-10-03**  
Status: **Public-source research complete for this bounded competitor lane; integration decisions provisional pending Mastermind's repository/runtime census.**

## What this comparison establishes

Mastermind should benchmark three different capabilities: making options observations trustworthy, helping a trader interpret them, and proving that a decision improves because of them. The strongest comparators solve different parts of that chain. Treating all of them as “options-flow scanners” obscures the most valuable engineering lessons.

This review covers the nine named competitors plus two relevant 2026 institutional integrations. It uses official product documentation, vendor methodology, vendor research, public schemas, and official announcements. Product capabilities below are **documented capabilities**, not independently operated or validated paid features. Marketing statements and illustrative backtests are not evidence of forecasting efficacy. “Not established” means the inspected public material did not prove the capability; it does not mean the vendor lacks it.

No private Mastermind source, production system, paid dataset, or signed-in competitor interface was inspected in this lane. Consequently, statements about what Mastermind should add are proposals to reconcile against the ongoing census, not claims that current Terminal lacks the feature.

## 1. Feature matrix: which decision does each product support?

**F** = classified flow; **V** = volatility surfaces/value; **D** = dealer/hedging abstraction; **H** = historical research; **X** = strategy/execution workflow. These are areas of documented emphasis, not ratings.

| Product | Decision supported | Documented emphasis | Data and transformation creating value | History / 0DTE boundary |
|---|---|---|---|---|
| **SpotGamma** | Where could options positioning alter intraday behavior, and which stocks have notable directional/volatility setups? | F, V, D | HIRO aggregates trade delta notional as estimated hedging pressure. TRACE applies a proprietary inventory model with participant lenses and gamma, delta-pressure, and charm-pressure views. Synthetic OI uses additional unspecified feeds and proprietary categorization. [C01–C03] | TRACE documents one-minute refresh and five-day forward projections. HIRO offers five days of chart history. Compass describes a one-year historical study; these are distinct from an open research engine. [C02, C04, C05] |
| **Cboe LiveVol** | What traded; how do present option prices, skew, earnings, and structures compare with relevant history? | F, V, H, X | Synchronized workbench: trade tape, time and sales, flow analytics, historical snapshots, earnings analysis, skew, scanners, spread alerts, position builder and monitor. Reviewed pages establish product components, not the exact signing or reconstruction algorithm. [C06, C07] | Time and sales/snapshots reach 2011; platform comparison separately lists last-30-day intraday charts. A chain containing same-day expiries is not by itself proof of a specialized 0DTE hedging model. [C07, C35] |
| **OptionMetrics / IvyDB / TradeFlow** | How should researchers obtain consistent historical surfaces and study the composition of options demand? | F, V, H | IvyDB handles pricing, sensitivities, standardized maturities, dividends and security-history continuity. TradeFlow adds intraday volume classification using trade codes, venue, quote location and VWAP-related processing. [C09, C10] | TradeFlow: five-minute, 30-minute and EOD data since January 2016. The Signed Volume predecessor explicitly covers 0DTE demand. This is a research dataset, not automatically a real-time trading signal feed. [C10, C36] |
| **Unusual Whales** | Which unusual activity merits attention; how does it connect with contract, market, volatility, and broader company context? | F, V, D, H | Trade-level filtering and multileg drilldown plus net premium, Greek exposure, volatility and APIs. Enterprise documentation distinguishes OPRA-derived datasets from C1-only SPX Market Exposure. [C13, C15, C16] | Documented histories differ: options trades from 2022, multileg from 2025, Greek exposure from 2023, SPX exposure from 2025. A subscription lookback can be shorter than dataset history. [C15, C16] |
| **Trade Alert** | What complex or unusual order needs immediate explanation or distribution to a desk? | F, V, H | Patented/proprietary order-flow processing, directional and complex-order alerts, expert context, historical recaps, APIs. [C08] | **Legacy/transition benchmark:** Cboe's official page says Trade Alert will cease operations and directs users to LiveVol. The inspected page did not give a cessation date; do not infer one or assume a safe new dependency. [C08] |
| **ORATS** | Is volatility expensive; which strategy and management rules work under explicit historical execution assumptions? | V, H, X | Surface smoothing; ATM level, slope and curvature; earnings-adjusted volatility; forecast-versus-implied comparisons; scanners and backtest workflows. Public documentation explains significant parts of the construction while forecasts and implementation remain partly proprietary. [C17] | Intraday backtester documents one-minute data from October 2020, approximately 140 symbols, 16 structures, timed entry/exit, stops, commissions, spread-based slippage and CSV signals. Native 0DTE support is explicitly documented. [C18] |
| **Market Chameleon** | Where is activity unusual, is an event move rich or cheap, and which names deserve investigation? | F, V, H | Market-wide volume report normalizes against 90-day activity and separates single-leg, multileg and stock-contingent trades. Event and strategy tools support contextual comparisons. [C19] | A dedicated 0DTE straddle tracker compares premium with historical values at the same point in the day. Public demo values are explicitly randomized and delayed; they cannot support market or accuracy claims. [C20] |
| **FlowAlgo** | Which urgent or large transactions should attract a discretionary trader's attention? | F, H | Consolidates cross-exchange sweep prints; filters using size, speed, fill pattern and relative activity; presents block alerts and historical filters. Significance algorithm is undisclosed. [C21] | Historical activity browsing is documented. Specialized volatility-surface research, dealer inventory, and systematic 0DTE testing were not established in the inspected pages. Its legacy guide acknowledges unknown motivation and intended holding time. [C21, C22] |
| **SqueezeMetrics** | Does the present price/volatility/options context resemble historically favorable or adverse states? | D, V, H | Current documented model combines price trend, volatility trend, gamma ratio and FINRA-derived dark ratio, with historical-neighbor analysis. Its current gamma ratio and older GEX white paper are different constructions. [C23, C24] | Current documentation uses five-day and 21-day forward contexts, CSV/API research and analog selection. Dedicated intraday 0DTE inventory was not established. Current plans page marks signup Closed. [C23, C25] |
| **SpiderRock + BMLL** | How does option execution relate to fair volatility, quote quality, subsequent markouts, and the underlying's microstructure? | F, V, D, H, X | Print-time quote/surface enrichment, inferred trade side, pricing-error and quality fields; BMLL adds detailed underlying history in a common research environment. Partnership announced April 23, 2026. [C26–C28] | Data schema includes at-trade features and separate +1/+10-minute outcomes. Short-horizon work is supported, but those outcome columns must not become contemporaneous predictors. Dealer-gamma study is an illustration, not independent causal proof. [C27, C29] |
| **SpiderRock + CPZAI** | Can a firm take one consistent analytics source through strategy research, validation, and governed deployment? | V, H, X | July 7, 2026 announcement describes live/historical options analytics within an AI research, backtesting, risk and governance environment. Specific inference algorithms, operational performance and 0DTE execution realism were not established. [C30] | Relevant as a workflow benchmark. Its announcement proves neither superior prediction nor an operating capability inside Mastermind. [C30] |

## 2. Trade classification, dealer identity, and confidence

### SpotGamma: hedging interpretation is a model output

HIRO's public definition supports an options-to-hedging abstraction; it does not reveal a transaction's complete counterparties or all offsets. TRACE explicitly calls its inventory construction proprietary. Synthetic OI documentation makes strong precision claims but does not expose the full feeds or classifier required to audit them. Retain that distinction when using these products as benchmarks. [C01–C03]

Compass publishes conditional results involving IV and risk-reversal ranks. One year's vendor backtest is a useful hypothesis generator; it is insufficient to establish stable incremental value across market regimes. Do not import thresholds as Prophet decision rules. [C04]

**Mastermind opportunity (inference):** display the estimated pressure, the assumption set and its sensitivity, and the market behavior that would invalidate the interpretation. A gamma map should explain why a zone matters and when confidence deteriorates.

### LiveVol and Trade Alert: interpret the whole structure

The workbench and complex-order emphasis demonstrate the value of seeing execution, volatility and structure together. The public overview does not establish that every detected spread is a uniquely reconstructed parent order, that side labels are exchange-certified, or that direction means opening intent. Cboe's separate Open-Close and TBT products must not be silently treated as part of every LiveVol or Trade Alert entitlement. [C06–C08, C31, C32]

**Mastermind opportunity (inference):** selecting an alert should expose contributing prints, candidate structures, residual unmatched legs and the explanation used by the downstream candidate decision.

### OptionMetrics: research quality includes explicit proxy definitions

The legacy Signed Volume research note identifies spread-relative Lee–Ready-style inference. The current TradeFlow overview adds richer inputs without publishing its complete assignment algorithm. [C10, C11]

OptionMetrics' September 28, 2026 methodology article is especially useful: public OPRA data lacks account/broker identity; its reproducible retail proxies use execution codes and trade-size buckets, while broader broker-identity estimates require non-public data. The article explicitly discusses a precision-versus-coverage tradeoff. Its displayed narrow and broad constructions are **retail-like proxies**, not participant identities. [C12]

**Mastermind opportunity (inference):** make “inferred retail-like,” “exchange-reported capacity,” and “unknown” different typed fields. Never equate an institutional-size print with an informed trader.

### Unusual Whales: its documentation already acknowledges major ambiguity

The public flow FAQ says buying can close a short position, selling can close a long position, and a print may belong to a multileg structure. Its bullish/bearish mappings assume opening activity. The accessible legacy flow guide additionally says midpoint executions were labeled BUY; current runtime behavior was not tested, so this is a documentation risk to investigate rather than a confirmed present defect. [C13, C14]

**Mastermind opportunity (inference):** report ambiguous volume explicitly. Directional percentages should reveal whether they exclude unknown trades or silently assign a direction. The denominator and classification coverage matter as much as the result.

### ORATS: model-fit confidence differs from forecast confidence

The documented surface factors and earnings decomposition help distinguish changing event risk from ordinary volatility. Its data fields include model-related confidence and errors; these are not automatically probabilities of a profitable trade. [C17]

The intraday backtester discloses execution assumptions and enables inspecting individual trades. That is valuable methodological transparency; minute marks still cannot prove exact within-minute fill order, executable size, or what happens first when multiple thresholds are crossed. The latter are research limitations inferred from the stated resolution. [C18]

### Market Chameleon and FlowAlgo: attention is not admission

Market Chameleon's guide qualifies relative volume with liquidity, catalyst and timeframe context. Its simple call/put composition is not equivalent to signed, opening directional demand. [C19] FlowAlgo acknowledges that motive and holding horizon are unknown, even though its marketing uses strong “smart money” language. [C21, C22]

**Mastermind opportunity (inference):** separate discovery from recommendation. An unusual print can create a research observation without creating an eligible candidate or changing a plan.

### SqueezeMetrics: explain assumptions before interpreting the sign

The historical GEX paper explicitly assumes market makers facilitate trades, hold calls long and puts short, and hedge at delta. These are assumptions about inventory and response, not observations of aggregate dealer books. [C24]

The current published gamma ratio uses constant-volatility BSM delta changes and OI to compare call/put convexity. It intentionally suppresses skew effects. Its historical-neighbor workflow is reproducible in broad concept, but interactive selection of “best” historical subsets creates a multiple-testing problem unless evaluated on later data. [C23]

### SpiderRock: the clearest auditable record benchmark found

The public schema separates None/Mid/Bid/Ask inference, exchange and gateway timestamps, quote age, cancellations, trade IV and fitted surface IV, pricing framework, exercise type, and future markouts. A field named probability is not a demonstrated calibrated probability merely because it appears in the schema; its construction and vintage still require verification. [C27]

The joint BMLL paper estimates inventory from execution IV relative to fair IV and illustrates a TSLA breakout strategy. That is a research hypothesis. The presented strategy does not, by itself, isolate incremental options information from its price/VWAP baseline. [C29]

## 3. Reproducibility from ThetaData: four different claims

ThetaData publicly documents option trade/quote records with execution and quote timestamps, conditions, exchange, sizes and NBBO. Quote matching can use a strictly earlier timestamp. Its OI documentation describes a morning publication representing the previous trading day. Actual Mastermind plan entitlements, retention and field integrity remain a separate audit. [C33, C34]

| Capability class | Feasibility using ordinary public trade/quote/OI inputs | What remains unproven or additional |
|---|---|---|
| Tape, filters, contract drilldown, observed premium/size | Straightforward in concept when the subscribed feed covers the universe and records are retained. | Coverage, latency, corrections, stable contract identity, raw-data rights, and performance at market scale. |
| Quote-relative buy/sell inference; signed premium and Greek notional | Reproducible as an original, documented estimator. | Signing accuracy; quote sequencing; midpoint, locked/crossed and stale markets; whether stock or other option legs change meaning. |
| Sweeps / clusters | Reproducible as heuristic grouping of compatible same-contract prints and conditions. | Exact parent identity; source timestamp resolution; unrelated simultaneous orders; proprietary vendor matching rules. |
| Complex-order reconstruction | Partial: exchange trade codes can identify complex executions and compatible candidate legs. | Unique all-market parent linkage requires identifiers not proved present in standard ThetaData records. A complex flag alone is not a recovered package. |
| Surface, skew, term structure, event premium, expected move | Original calculations possible with appropriate quotes, pricing conventions and reference data. | Stable fitting, no-arbitrage quality, dividends, rates, borrow, settlement, calendar, missing strikes and model error. Vendor-identical surfaces are not reproducible without the vendor model. |
| OI/Greek exposure and pressure scenarios | Deterministic exposure calculations under explicitly stated position/sign assumptions are possible. | Actual dealer inventory, opening/closing, netting, hedging choice and outside-market offsets are not recovered by a formula. |
| Intraday “synthetic OI” | Possible as a labeled estimate or scenario; never identical to confirmed clearing OI. | The latent inventory problem and proprietary additional feeds remain. Same-day expiring activity can open and close before any next-day OI confirmation. |
| Historical analogs and signal testing | Possible from retained point-in-time inputs and later outcomes. | A backtest must reproduce information availability and data versions, not just today's cleaned historical files. |
| Retail/institutional classification | Narrow execution-code/size proxies can be reproduced. [C12] | Actual account or broker identity requires another data source. Small algorithmic slices and larger retail orders confound size. |
| Dealer-state participant lenses / exchange opening labels | Not established from ordinary OPRA-derived ThetaData. | Licensed exchange-origin data, limits on exchange coverage and publication lag; even these do not reveal all hedges or intent. [C31, C32] |

**Decision:** reproduce economic ideas and transparent observables with original implementations. Do not promise to clone proprietary model outputs. All replication estimates are conditional on the root audit confirming required raw fields and entitlements.

## 4. A concrete validation route: exchange-origin labels

Cboe's Enhanced US Options Trade-by-Trade Execution Detail is a particularly valuable discovery. The official product page documents **C1-only coverage, T+1 delivery, history from October 7, 2019, side/open-close/capacity fields and simple/complex execution IDs**. Other Cboe venues are described as planned, not presently covered. [C32]

**Proposed use:** acquire a bounded, properly licensed evaluation sample if justified, then compare Mastermind's OPRA-derived classification with the exchange-reported outcomes on the overlapping venue. Measure aggressor inference separately from buy/sell leg direction and opening status; require schema inspection before choosing a ground-truth target. Stratify by single versus complex, auctions, quote distance, size, DTE and time of day. Do not extrapolate measured C1 accuracy to every venue.

This would directly test whether a package heuristic recovers linked legs and whether “opening-like” evidence identifies opening activity. It also supplies a control demonstrating how much predictive performance depends on privileged variables that Mastermind cannot observe live. T+1 truth belongs in research/evaluation; it cannot be inserted into same-day historical decisions.

Cboe's Open-Close summary offers a coarser alternative. Its documentation flags historical OI/volume convention changes and an announced November 8, 2026 intraday update. The latter is future-dated relative to this report and must not be assumed operational. Raw-data and derived-redistribution rights require explicit entitlement review before product use. [C31]

No account, trial, purchase, or vendor contact was initiated.

## 5. What Mastermind can do better through Prophet's lifecycle

These are proposed consumer outcomes, subject to reconciliation with existing owners and implementation. No additional lifecycle store, event store or replay plane is proposed here.

| Stage | Useful options decision output | Relevant benchmark | Required acceptance evidence |
|---|---|---|---|
| Discovery | Surface a sustained, interpretable demand change with contract/structure evidence, not just a large print. | TradeFlow, Unusual Whales, FlowAlgo | Discovery lift versus price/volume-only shortlist; unique package counting; unknown/complex coverage. |
| Before admission | State whether options support, contradict, or cannot assess the candidate at the candidate's actual horizon. | IvyDB research discipline, ORATS context | Baseline Prophet versus baseline + options on untouched later data; abstention and coverage reporting. |
| Plan formation | Identify event risk, expected range, liquidity constraints and conditional pressure zones that affect entry timing or invalidation monitoring. | LiveVol, Market Chameleon, SpotGamma | Calibrated range/event errors; no unsupported precision; counterfactual plan comparison. |
| After admission | Detect persistent deterioration or an options-state transition relevant to the thesis, with an explicit reason and horizon. | SpotGamma dynamic views plus broader Mastermind context | Warning precision, false-alert burden, lead time, adverse-excursion reduction, and retained candidate-state proof. |
| Intraday / 0DTE | Provide short-lived pressure and range context tied to exact expiry and observed liquidity. | TRACE, ORATS intraday, SpiderRock | Separate intraday labels; correct settlement/time conventions; recorded live observations; no automatic promotion into a five-day conviction score. |
| Outcome and calibration | Explain which options evidence helped, failed or was unusable, and decide which features remain eligible. | IvyDB, ORATS, SpiderRock/BMLL | Point-in-time reproducibility, cost sensitivity, regime/symbol stability, feature ablation and drift monitoring. |

A useful user-facing explanation could be: “Your three-day candidate still has price and sector support. Today's options evidence is mixed: short-dated protection demand increased, but most of the largest prints belong to uncertain complex structures. Confidence is insufficient to alter eligibility; monitor the existing invalidation level and tomorrow's event.” This is an illustrative product behavior, not a market call or an established Mastermind capability.

A stronger state transition could occur only after validated evidence: “The candidate's event-risk model changed enough to trigger plan review.” The options layer should produce structured evidence and a recommendation to the existing candidate owner; that owner remains responsible for the authorized state transition.

## 6. Recommended research/build priorities after census

1. **Make the observations auditable.** Preserve raw-to-derived lineage, classification version, data vintage, quote timing, correction state, quality and unknown flags. SpiderRock's schema is a benchmark for what to expose, not an instruction to duplicate its data model wholesale.
2. **Separate the inference layers.** Keep print side, opening likelihood, package interpretation, participant proxy, inventory assumption and expected market impact distinct. A later layer must not turn uncertain inputs into a falsely precise conclusion.
3. **Build the volatility/event comparison spine.** Harmonized surface slices, same-time-of-day comparisons and event-aware measures offer testable context without needing to identify a trader's intent. First verify and extend existing implementations.
4. **Run a small incremental-value program.** Start with a few horizon-specific families: quality-filtered signed demand, surface/event repricing and explicitly conditional pressure scenarios. Compare against existing price, volume, regime, sector and catalyst features. Do not initially merge them into a universal bullish/bearish score.
5. **Prove pre-admission and post-admission consumption.** A Terminal chart is not the outcome. Retain the exact evidence available at each decision, the candidate owner's disposition, and later outcomes through existing evaluation ownership.
6. **Add advanced dealer or retail modeling only when justified.** Additional exchange data should be selected to reduce a demonstrated uncertainty or unlock a named decision. Do not fund a broad data purchase merely to match a competitor's feature count.

## 7. Specific follow-up questions for the root program

- Does Mastermind retain the exact trade/quote pairing used to sign each print, including an unknown state and the published time of OI?
- Is a “sweep” still confined to same-contract execution clustering, with multi-leg packages handled by the correct existing layer?
- Can a candidate decision be replayed through the existing evidence/evaluation path without next-day corrections or later OI leaking backward?
- Are reported gamma/charm/vanna values tagged with units, model, scenario assumptions and actual settlement time?
- Which options features currently alter admission or post-admission behavior, and which are presentation only?
- Is there an existing legal entitlement for Cboe open/close or another exchange-origin validation sample?
- Can the existing Terminal interface move from summary to evidence with every alert, without requiring users to infer the whole trade themselves?
- Does the evaluation stack distinguish data-quality confidence, inference confidence and empirically calibrated outcome probability?

## Source register

All sources retrieved October 3, 2026. Source IDs map to web references and evidence types in the companion JSON file.

- **C01:** [SpotGamma HIRO](https://support.spotgamma.com/hc/en-us/articles/4420646443539-What-is-the-SpotGamma-HIRO-Indicator).
- **C02:** [SpotGamma TRACE](https://support.spotgamma.com/hc/en-us/articles/33607907909011-What-is-SpotGamma-TRACE).
- **C03:** [SpotGamma Synthetic OI](https://support.spotgamma.com/hc/en-us/articles/39946919887891-What-is-the-Equity-Hub-Synthetic-OI-Open-Interest-Model).
- **C04:** [Compass statistics](https://support.spotgamma.com/hc/en-us/articles/39936685498899-Compass-Guided-View-Statistics).
- **C05:** [HIRO history](https://support.spotgamma.com/hc/en-us/articles/12285325741715-How-can-I-see-5-day-history-in-HIRO).
- **C06:** [LiveVol Pro](https://www.livevol.com/options-trading-analysis-software/).
- **C07:** [LiveVol guide](https://www.livevol.com/user-guide/?m=analytics-components/time-and-sales).
- **C08:** [Trade Alert and cessation notice](https://www.cboe.com/solutions/real-time-market-alerts).
- **C09:** [OptionMetrics / IvyDB](https://optionmetrics.com/).
- **C10:** [TradeFlow](https://optionmetrics.com/ivydb-tradeflow/).
- **C11:** [Signed-volume methodology](https://optionmetrics.com/wp-content/uploads/2020/01/Assessing-Option-Demand-from-Signed-Volume-Order-Flow.pdf).
- **C12:** [2026 retail identification](https://optionmetrics.com/blog/how-much-of-0-dte-is-really-retail-evidence-from-spx-and-spy-options/).
- **C13:** [Unusual Whales flow guide](https://docs.unusualwhales.com/features/2-options-flow/).
- **C14:** [Unusual Whales flow FAQ](https://docs.unusualwhales.com/faq/items/4-flow/).
- **C15:** [Unusual Whales enterprise coverage](https://unusualwhales.com/enterprise).
- **C16:** [Unusual Whales API](https://unusualwhales.com/public-api).
- **C17:** [ORATS methodology](https://orats.com/docs/core-research).
- **C18:** [ORATS intraday backtester](https://orats.com/intraday-backtester).
- **C19:** [Market Chameleon volume report](https://marketchameleon.com/Instructional-Stock-and-Options-Trading-Videos/565/Option-Volume-Graphs-by-Expiration-Market-Chameleon-Tutorial).
- **C20:** [Market Chameleon 0DTE tracker](https://marketchameleon.com/Reports/ExpiringOptionsReport).
- **C21:** [FlowAlgo](https://www.flowalgo.com/).
- **C22:** [FlowAlgo fundamentals](https://help.flowalgo.com/en/articles/1257275-flowalgo-fundamentals).
- **C23:** [SqueezeMetrics current methodology](https://squeezemetrics.com/monitor/docs).
- **C24:** [SqueezeMetrics historical GEX paper](https://squeezemetrics.com/download/white_paper.pdf).
- **C25:** [SqueezeMetrics plans](https://squeezemetrics.com/monitor/plans).
- **C26:** [SpiderRock historical data](https://spiderrock.net/data/historical-data-analytics/options-greeks/).
- **C27:** [SpiderRock current print schema](https://docs.spiderrockconnect.com/docs/HistoricalData/Data%20Dictionaries/OptionPrintSetHist/).
- **C28:** [BMLL partnership announcement](https://www.bmlltech.com/news/press-releases-and-news/bmll-partners-with-spiderrock-to-expand-cross-asset-market-analytics).
- **C29:** [BMLL–SpiderRock research](https://www.bmlltech.com/files/documents/BMLL-Spiderrock-White-Paper.pdf).
- **C30:** [SpiderRock–CPZAI](https://spiderrock.net/spiderrock-partners-with-cpzai-to-deliver-an-ai-native-systematic-options-trading-workflow/).
- **C31:** [Cboe Open-Close](https://datashop.cboe.com/cboe-options-open-close-volume-summary).
- **C32:** [Cboe enhanced trade-by-trade data](https://datashop.cboe.com/enhanced-us-options-trade-by-trade-execution-detail).
- **C33:** [ThetaData trade/quote records](https://thetadata.net/docs/operations/option_history_trade_quote.html).
- **C34:** [ThetaData OI publication](https://www.thetadata.net/docs/operations_excel/option_snapshot_open_interest.html).
- **C35:** [LiveVol comparison](https://www.livevol.com/analytics-platforms/).
- **C36:** [Signed Volume product page](https://optionmetrics.com/signed-volume/).

