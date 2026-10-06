# Competitive mechanism deconstruction: intraday dealer pressure, extrema and the close

**Research cut: 6 October 2026. Research only.** This supplement answers all fifteen competitive questions in Chris’s commission. It covers every named provider, separates legacy SqueezeMetrics research from its current monitor, and adds FirmTape, quantedOptions, ZeroGEX and FlashAlpha because their public material materially changes the comparison.

The governing Mastermind procedure was pinned by the principal to `a6d40ff648671b03bd4d829d84dd066b58ea8c3f`; the current Macro and Terminal baselines supplied to this lane were `c9631f8b2469587dec643bec94b16e77c09ef511` and `ad36a332cd4b53af1d917a94f6fb3a10e27dad84`. The October 3 options master plan, current state, contracts, signal catalogue, near-expiry specification and competitor report were consumed before extending the research. This is a supplement to that ontology and those owners.

## 1. What the competitive evidence establishes

The leading products offer useful ways to inspect **trade-derived pressure, a modeled standing book, and hypothetical future hedge changes**. These are different quantities. No inspected public documentation establishes complete consolidated dealer inventory, actual future hedge executions, executable cross-product liquidity, and calibrated LOD/HOD/closing-auction outcomes in one validated system.

Three distinctions are especially consequential.

- **Refresh speed does not identify inventory freshness.** quantedOptions explicitly distinguishes tagged SPX/VIX positioning from an OI-based ticker product whose intraday changes come from repricing. ZeroGEX similarly separates the standing OI book from classified trading. A minute-by-minute exposure series may change without a single newly confirmed position. [C58] [C60]
- **Futures display support usually means coordinate conversion.** MenthorQ, quantedOptions, FirmTape and ZeroGEX describe index or ETF levels mapped onto futures charts. This is useful, but it does not establish a jointly netted SPX/SPY/XSP/ES options book. HIRO is a notable documented exception at the aggregation-interface level: it explicitly offers an S&P product basket. Its hedge-equivalent weights remain undisclosed. [C02] [C29] [C54] [C57] [C60]
- **A probability must name its outcome.** QuantData forecasts persistence of a market state; MenthorQ’s level “hold” concerns the side of the close; SpotGamma publishes unconditional nonbreach/closing-side frequencies; ZeroGEX studies breaks conditional on approaching a wall. These measures cannot be ranked as interchangeable prediction accuracy. [C09] [C28] [C46] [C61]

The most useful incremental discoveries are QuantData’s explicit state forecasts, MenthorQ’s historical level definitions, the tagged-data distinction at OptionsDepth and quantedOptions, and ZeroGEX’s newly documented full-repricing/zero-flow interface. FirmTape and ZeroGEX also publish negative or weak research results, which make them useful adversarial comparators. None of these discoveries overturns Mastermind’s previous rejection of a simple signed-charm narrative. [C27] [C40] [C46] [C53] [C58] [C61] [C63]

### Evidence notation and access boundary

**D — documented:** a first-party source describes a mechanism or feature. This establishes the public description, not independently tested runtime behavior.

**V — vendor empirical or causal claim:** an author reports performance, causation or superior accuracy. Such claims are attributed and qualified.

**I — research inference:** a deduction made here from the stated mechanism.

**U — undisclosed in the inspected public materials:** an unresolved field, not an assertion that the vendor has no internal method.

Sources were accessed without accounts, subscriptions, trials, purchases or contact. Published APIs were read as documentation only. MomoEdge was available through indexed official content; direct opening was blocked. ZeroGEX’s newest Forced Flow article was available as indexed official full text, although direct opens failed. These access limits reduce certainty about current operational state. The source register provides stable URLs, dates, retrieval status and limitations.

## 2. SpotGamma HIRO

| Commission field | Finding |
|---|---|
| **1. User decision** | D: whether current options activity supports a move, opposes it, or suggests a reversal near a relevant level. [C01] |
| **2. Display** | D: price with accumulated estimated hedging pressure, call/put views, alerts, trade inspection and contextual technical/SpotGamma levels. [C01] [C02] |
| **3. Structural versus flow** | D: HIRO is trade-updated pressure; imported levels provide standing-structure context. I: agreement between them is a conjunction of different measurements. [C02] |
| **4. Inventory basis** | D: option transactions are translated into estimated delta-notional hedge demand. Proprietary filtering removes trades considered already hedged. U: classifier, initial book and reconciliation. [C01] [C03] |
| **5. Components** | D: flow, call/put splits and expiry selection are visible. U: a publicly specified joint gamma/vanna/charm/IV/liquidity forecast. [C02] |
| **6. Update frequency** | D: advertised real time. U: measured end-to-end latency, correction lag and per-source completeness. [C01] |
| **7. Cross-products** | D: individual tickers plus baskets for the S&P complex, component equities and large technology names. [C02] |
| **8. SPX/SPY/XSP/ES** | D: the S&P basket explicitly includes all four. U: contract normalization, product hedging ratios and overlap treatment. [C02] |
| **9. 0DTE** | D: nearest-expiry filtering. I: nearest expiry must not automatically be relabeled same-day expiry. [C02] |
| **10. Level definitions** | D: structural levels are an additional context layer. HIRO itself is principally a pressure series; no unique LOD/HOD definition was found. [C01] [C02] |
| **11. Static or dynamic** | D: dynamic flow and alerts; I: a reversal in the cumulative/rate series is different from a spatial hedge-flow root. |
| **12. Confidence** | U: calibrated trade-side, participant-side or outcome probabilities. An alert or large reading is not a confidence interval. |
| **13. Historical validation** | U: an inspected, reproducible HIRO-specific conditional-extrema or closing-pressure study. SpotGamma level statistics are a separate object; see §4. |
| **14. Fact versus inference** | D: the product estimates hedge effects from options activity. I: this is evidence of options-associated pressure under assumptions, not observed dealer stock trades. |
| **15. Irreducible proprietary part** | U: trade inclusion rules, participant inference, treatment of prior hedges, package handling and cross-product weighting. [C03] |

**Mastermind lesson:** preserve the joint reading of live flow and structure, with independently inspectable quantities. Extend OIF04/OIF06/OIF30 and their ambiguity envelopes; a similar interface does not justify importing a vendor’s implied participant certainty.

## 3. SpotGamma TRACE

| Commission field | Finding |
|---|---|
| **1. User decision** | D: identify where modeled dealer positioning may dampen or amplify price movement, including possible late-session pressure. [C04] |
| **2. Display** | D: gamma, delta-pressure and charm-pressure heatmaps; strike positioning, OI/net OI and participant lenses. [C04] |
| **3. Structural versus flow** | D: a proprietary options-inventory model refreshed intraday, with future surfaces. U: attribution of each revision to transactions, repricing or corrections. [C04] |
| **4. Inventory basis** | D: the product names a proprietary SPX inventory model and market-maker/customer/pro-customer/firm/broker-dealer views. U: precise feeds, starting positions and reconstruction. [C04] |
| **5. Components** | D: gamma, delta pressure and charm remain separate lenses. U: a disclosed unified vanna/IV-path/executable-liquidity model. [C05] [C06] [C07] |
| **6. Update frequency** | D: one-minute session updates and projections extending five days. U: source-event-to-consumer lag and revision handling. [C04] |
| **7. Cross-products** | D: inspected TRACE documentation describes SPX options. U: combined cash-index, ETF and futures-option inventory. [C04] |
| **8. SPX/SPY/XSP/ES** | U: no TRACE-specific consolidated S&P book was established. HIRO’s basket must not be attributed to TRACE. |
| **9. 0DTE** | D: time-dependent gamma/charm and expiry effects are central to the surface interpretation. [C05] [C07] |
| **10. Level definitions** | D: gamma sign/intensity regions and delta-pressure buy/sell contours; charm interfaces are described as possible pin areas. [C05] [C06] [C07] |
| **11. Static or dynamic** | D: price-time state transitions, not solely fixed strike lines. Delta-pressure topology distinguishes buying below/selling above from the opposite configuration. [C06] |
| **12. Confidence** | D: Stability Gauge estimates next-ten-minute large-move risk; it operates 09:30–15:30 ET and becomes unavailable afterward. U: calibrated probabilities and large-move definition. [C08] |
| **13. Historical validation** | U: a public TRACE-specific sample, frozen-model test and baseline-adjusted result for roots, extrema or closing regions. |
| **14. Fact versus inference** | D: the displayed topology and separate lenses are documented. V: stabilization, attraction and late-close usefulness. I: contour location alone cannot establish realized attraction. |
| **15. Irreducible proprietary part** | U: inventory assignment, projection conventions, surface smoothing, stability model and thresholds. |

**Mastermind lesson:** TRACE is an interface benchmark for conditional pressure surfaces. Carry the scenario horizon, IV assumption, inventory model and sign convention beside the surface. The absence of the stability gauge in the final half-hour is itself relevant: the displayed short-horizon confidence product does not cover the commission’s entire closing window. [C08]

## 4. SpotGamma’s structural adjuncts: Synthetic OI and level statistics

Equity Hub’s Synthetic OI documentation describes transaction categorization intended to improve position estimates and defines High/Low Volatility Points through negative/positive gamma concentration. Its support page specifies a **daily update before the open**, while its landing page advertises **near-real-time** position tracking. These statements cannot establish a single intraday publication contract without clarification. Record a product/version/cadence distinction rather than resolving the discrepancy by assumption. [C10] [C11]

The landing page also advertises strike/expiry positioning, broad equity coverage, historical comparison and an impact score. These are useful discovery and context jobs, but neither an impact score nor richer transaction data establishes exact beneficial-owner inventory. [C11]

The public SPX statistics page covers **10 May 2019–28 May 2024**. It reports call-wall nonbreach/close-below rates of **83%/88%**, and put-wall nonbreach/close-above rates of **89%/93%**. Its one-day implied range is unbroken on **35%** of sessions and contains the close on **76%**. These are useful descriptive baselines, not interchangeable probabilities of holding after touch. Distance, ordinary implied range and prior-day extrema need matched comparison. A wall far from price can earn a high nonbreach rate without offering a tradable conditional edge. [C09]

## 5. SqueezeMetrics IOB/DDOI and legacy GEX research

| Commission field | Finding |
|---|---|
| **1. User decision** | D: assess potential hedge-related liquidity and future volatility under alternative market states. [C12] |
| **2. Display** | D: implied order-book surfaces and GEX/VEX/GEX+/GIV spreadsheet measures. [C12] [C13] |
| **3. Structural versus flow** | D: a standing directional book reconstructed from transactions and later OI; not simply today’s running signed volume. [C13] |
| **4. Inventory basis** | D: DDOI classifies transactions and reconciles inferred direction with subsequent OI. U: complete classifier, latent open/close assignments and initialization. [C13] |
| **5. Components** | D: the legacy guide combines gamma and vanna after an assumed spot/IV mapping. The 2020 paper dismisses charm as small in that setting. [C12] [C13] |
| **6. Update frequency** | D: the spreadsheet guide describes approximately 05:30 next-morning publication. It does not establish real-time reconciled DDOI. [C13] |
| **7. Cross-products** | D: SPX is the IOB application. U: common inventory netting across distinct S&P products. [C12] |
| **8. SPX/SPY/XSP/ES** | I: ES-equivalent illustrations express scale, not evidence that an ES option book was merged. |
| **9. 0DTE** | U: a modern same-session reconstruction/error analysis. I: a 2020 charm judgment cannot be transferred to the present expiry mix. |
| **10. Level definitions** | D: scenario-dependent hedge response, with volatility estimates inferred from historical exposure relationships. [C13] |
| **11. Static or dynamic** | D: hypothetical spot/volatility states change the book’s hedge. I: these are model surfaces, not firm orders. |
| **12. Confidence** | D: the IOB distinguishes regions supported by historical observations. U: calibrated inventory uncertainty or conditional-touch probabilities. [C12] |
| **13. Historical validation** | D/V: historical SPX exposure/return plots reaching back to 2004. U: independently reproduced incremental/OOS inventory or extrema results. [C12] |
| **14. Fact versus inference** | D: published construction concept. V: claims of actual positions and compelled liquidity. I: reconciliation narrows possibilities but cannot generally identify every trade’s intent. |
| **15. Irreducible proprietary part** | U: DDOI state reconstruction, uncertain-print treatment and operational data lineage. |

**Important version separation.** The 2016 paper, revised December 2017, explicitly assumes delta-hedging counterparties, dealer-long calls and dealer-short puts, and delta-based hedging despite real desks’ bands. That historical convention is not the same method as the later DDOI claim, and neither is the current gamma-ratio monitor. [C15]

**Arithmetic audit.** The IOB’s example moves a hedge from 27 units at 3,000 to 37 at 2,950, and labels the $28,150 value difference additional buying. The subtraction is correct; the quantity is different. Ten additional units at the endpoint cost $29,500. The $1,350 gap reprices the original holding. Its example also changes time while presenting the spot experiment. Mastermind should retain its existing endpoint hedge-unit-change convention and isolated-factor diagnostics. [C12]

## 6. SqueezeMetrics current gamma/dark-ratio monitor

| Commission field | Finding |
|---|---|
| **1. User decision** | D: find historically similar price/volatility/options/off-exchange states for multi-day context. [C14] |
| **2. Display** | D: four axes, historical scatterplots, analog forecasts and CSV/API output. [C14] |
| **3. Structural versus flow** | D: daily price, volatility, OI-derived convexity and short-volume summaries. [C14] |
| **4. Inventory basis** | D: gamma ratio uses fixed-volatility BSM sensitivity and OI to compare call/put convexity; it does not reconstruct signed dealers. [C14] |
| **5. Components** | D: the axes remain visible, then enter analog selection; implied volatility is also available. [C14] |
| **6. Update frequency** | D: daily observations. U: an intraday inventory publication contract. [C14] |
| **7. Cross-products** | D: ticker comparisons; DIX separately combines dollar-weighted S&P constituent indicators. [C16] |
| **8. SPX/SPY/XSP/ES** | U: no consolidated S&P derivative inventory method established. |
| **9. 0DTE** | U: dedicated live same-day inventory treatment. |
| **10. Level definitions** | I: this is principally a state/analog product; no unique intraday pressure-root rule established. |
| **11. Static or dynamic** | I: rolling daily states, distinct from price-time hedge surfaces. |
| **12. Confidence** | D: normalized indicators and historical analog outcomes. U: inventory posterior or calibrated extrema probabilities. [C14] |
| **13. Historical validation** | D: five- or twenty-one-day analog outcomes and user-selected historical neighborhoods. U: frozen selection/OOS performance. [C14] |
| **14. Fact versus inference** | D: source transformations. V: dark short volume suggests passive buying. That interpretation does not establish investor identity. [C14] [C17] |
| **15. Irreducible proprietary part** | U: operational data lineage and full forecast-selection implementation; disclosed computations alone do not settle prediction quality. |

DIX is a **separate off-exchange transaction statistic**, not an auction imbalance or direct institutional-accumulation measure. FINRA explains that short-marked trades can facilitate customer long sales and that offsetting transactions may not appear in the public daily file. FINRA’s files also omit exchange activity unless separately combined. Consequently, a high dark ratio does not identify either a persistent short position or a unique underlying buyer’s motive. [C16] [C17]

**Mastermind lesson:** keep off-exchange evidence in its existing audited lane. Test whether the statistic adds context without relabeling it as institutional demand or closing pressure.

## 7. GammaEdge

| Commission field | Finding |
|---|---|
| **1. User decision** | D: distinguish trend/chop, select meaningful zones, and require structure, sentiment and trend agreement. [C18] [C23] |
| **2. Display** | D: Greeks/OI by strike and expiry; NetStat summaries; VolM call/put centroids; SpecPA distribution bands and SpecPS slope behavior. [C19] [C20] [C21] [C22] |
| **3. Structural versus flow** | D: premarket structure uses overnight OI; live 0DTE volume tools form a separate stream. [C18] |
| **4. Inventory basis** | D: OI/Greek structure and traded-volume distributions. U: verified participant inventory. VolM documentation acknowledges that volume does not directly reveal opening versus closing. [C19] |
| **5. Components** | D: delta/gamma/charm/vanna surfaces are distinct; NetStat summarizes dominant strikes, sides and moneyness. Trend confirmation remains additional. [C21] [C23] |
| **6. Update frequency** | D: real-time spot repricing for the web app; VolM uses five-minute periods. U: measured latency. [C19] [C22] |
| **7. Cross-products** | D: stocks/ETFs and SPX analysis, with futures trading workflow. U: aggregate cross-book dealer exposure. [C18] [C22] |
| **8. SPX/SPY/XSP/ES** | U: a documented jointly netted book. Applying SPX structure while trading ES does not establish one. |
| **9. 0DTE** | D: explicit SPX same-day volume analysis and selectable expiry cohorts. [C19] [C22] |
| **10. Level definitions** | D: PTrans/NTrans transition areas, gamma concentrations, COI/POI references; volume centroids and percentile-like bands are additional locations. [C20] [C23] |
| **11. Static or dynamic** | D: OI-derived levels plus dynamically shifting volume distributions and extrapolated centroid trends. [C19] |
| **12. Confidence** | D/V: qualitative pattern agreement, concentration and slope interpretation; U: calibrated confidence bands or extrema probabilities. [C20] |
| **13. Historical validation** | D: worked sessions and practitioner comparison of sampling intervals. U: disclosed sample-wide conditional extrema or centroid-forecast skill. [C18] [C19] |
| **14. Fact versus inference** | D: volume-distribution calculations and charts. V/I: interpreting movement as new speculative positioning, monetization or future price targeting. |
| **15. Irreducible proprietary part** | U: exact transition rules, full centroid preprocessing, filtering and confidence/pattern selection. |

**Specific risk:** a call centroid can rise because spot rises and trading migrates toward newly near-the-money strikes. A line extended toward the close forecasts the continuation of that fitted volume pattern; it is not automatically a closing-price forecast. Test against spot-following and unsigned-volume baselines before assigning causal pressure. SpecPA’s association between band concentration and conviction similarly requires validation independent of selected examples. [C19] [C20]

## 8. MenthorQ

| Commission field | Finding |
|---|---|
| **1. User decision** | D: plan around options levels, volatility regimes and expected ranges, then assess changing intraday context. [C25] [C27] |
| **2. Display** | D: strike/expiry GEX/DEX/OI/volume, intraday changes, gamma levels, expected range, liquidity/regime summaries and backtest panels. [C25] [C26] [C28] |
| **3. Structural versus flow** | D: daily OI plus intraday repricing/volume/exposure comparisons. U: decomposition of each exposure change into new positions versus Greek changes. [C24] [C26] |
| **4. Inventory basis** | D: proprietary options models. The tagged-data explanation schedules Cboe/other-exchange integration for end-2026; it does not demonstrate current production use. [C27] |
| **5. Components** | D: gamma, delta, volatility and wider regime/flow models remain visible; Blindspots explicitly blend options flow, momentum and cross-asset correlation. U: executable liquidity denominator. [C26] [C30] |
| **6. Update frequency** | D: five-minute stock/ETF/index updates from 09:35–16:00 ET; new daily OI around 08:00. Futures have an extended five-minute schedule. Chart integrations can expose fewer scheduled snapshots. [C24] [C25] |
| **7. Cross-products** | D: broad equity, index, ETF, native futures, crypto and FX-related coverage. FX levels can derive from corresponding futures options. [C24] [C30] |
| **8. SPX/SPY/XSP/ES** | D: conversion of SPX/SPY levels to ES is documented. U: full jointly netted inventory. [C29] |
| **9. 0DTE** | D: same-day/near-expiry filters; some views use the next available expiry when no same-day contract exists. [C25] |
| **10. Level definitions** | D: call resistance, put support, high-volatility transition, one-day range and proprietary Blindspots. Exact level-selection formulas remain U. [C27] [C30] |
| **11. Static or dynamic** | D: daily levels with intraday revisions, comparison to EOD, and changing exposure. I: label migration is not necessarily inventory migration. [C25] |
| **12. Confidence** | D: regime-matched historical level statistics. U: full out-of-sample probability calibration or uncertainty in the underlying inventory. [C28] |
| **13. Historical validation** | D: up to three years of similar-regime sessions, with closing-side hold, comeback, failed close and beyond-level excursions. U: exact matching, model versions and leakage controls. [C28] |
| **14. Fact versus inference** | D: the tagged-data guide explicitly distinguishes participant origin, intent, flow, positions and incomplete market coverage. That caution should constrain other positioning claims. [C27] |
| **15. Irreducible proprietary part** | U: level algorithms, regime similarity, Blindspots weights and current reconstruction details. |

The historical panel’s definition matters: a level can count as held even after an intraday breach if the close returns to the appropriate side. This is a legitimate outcome when labeled, but does not answer whether a stop beyond the level would survive or whether the level held after its first touch. Do not inherit those probabilities for Mastermind’s containment zones. [C28]

The conversion documentation also highlights time alignment and futures basis. A coordinate transform must use matching timestamps and contract specifications. Treat converted lines as sourced annotations; they are not additional independently observed exposure. [C29]

## 9. Tier1Alpha

| Commission field | Finding |
|---|---|
| **1. User decision** | D: daily market-risk and tactical context spanning dealer gamma, volatility and systematic investors. [C31] [C32] |
| **2. Display** | D: daily research/charts; public positioning includes gamma, volatility/range and breadth-related context. An official March 2026 Hedgeye PDF attributes a chart section to Tier1Alpha. [C31] [C34] |
| **3. Structural versus flow** | I: daily structural synthesis is established; a continuous signed-inventory tape is not. |
| **4. Inventory basis** | U: exact sign convention, exchange-origin data, opening/closing classifier and initial book in inspected public material. |
| **5. Components** | D: options risk is considered alongside volatility-control, leveraged-ETF and broader market forces. U: exact combination model. [C32] |
| **6. Update frequency** | D: daily newsletter and weekly discussion were announced; current homepage routes distribution through Hedgeye. U: intraday recalculation contract. [C31] [C32] |
| **7. Cross-products** | D: broad market/systematic context. U: a common product-level hedge aggregation schema. |
| **8. SPX/SPY/XSP/ES** | U: no complete combined inventory method established. |
| **9. 0DTE** | D: explicit discussion of short-dated gamma and alternative option hedges. [C33] |
| **10. Level definitions** | U: complete public formulas for proprietary gamma/volatility/range levels. |
| **11. Static or dynamic** | I: periodic risk-state and level updates; no validated continuous pressure-root specification found. |
| **12. Confidence** | D: research interpretation; U: calibrated LOD/HOD or closing-region probabilities. |
| **13. Historical validation** | U: a reproducible, directly relevant study of inventory accuracy or intraday extrema. Public chart attribution alone is not validation. |
| **14. Fact versus inference** | D: the product covers multiple flow channels. V: its 0DTE article claims over 85% is hedged through farther-OTM options, without disclosed measurement supporting that percentage. [C33] |
| **15. Irreducible proprietary part** | U: position estimation, proprietary range/volatility transforms, forecasts and confidence calculations. |

**Mastermind lesson:** hedge substitution deserves an explicit scenario; do not apply a universal “only 15% reaches futures” discount. Options can offset option risk without a contemporaneous stock trade, but the fraction, state dependence and net effect need independent evidence. [C33]

## 10. Tradytics

| Commission field | Finding |
|---|---|
| **1. User decision** | D: screen activity, interpret options sentiment and inspect dealer/technical context. [C35] [C38] |
| **2. Display** | D: trade tape, call/put flow, Greek positioning, historical DEX, and configurable filters. Public tape fields include bid/ask, IV, size, OI and expiry. [C35] [C37] [C39] |
| **3. Structural versus flow** | D: dealer-positioning tools coexist with minute-based cumulative trading summaries. I: neither should be treated as the other. [C38] |
| **4. Inventory basis** | U: complete dealer reconstruction. D: the flow UI explicitly has an infer-buy/sell setting and opening-order filters; filter names are not ground truth. [C39] |
| **5. Components** | D: gamma, vanna, charm and delta-related products are separately explained, with additional flow and technical tools. [C35] |
| **6. Update frequency** | D: flow summaries by minute; sourcing page describes real-time options, possible analytical delay, and 15-minute-delayed dark-pool data. The public tape is delayed further. [C36] [C38] [C39] |
| **7. Cross-products** | D: multi-ticker equity/options analysis. U: netted index/ETF/futures dealer inventory. [C39] |
| **8. SPX/SPY/XSP/ES** | U: combined S&P book not established. |
| **9. 0DTE** | D: days-to-expiration filters include zero. U: exact same-session payoff/settlement treatment. [C39] |
| **10. Level definitions** | U: reproducible proprietary dealer-level formulas; D: DEX evaluates historical options-delta/price relationships. [C37] |
| **11. Static or dynamic** | D: live cumulative flow and historical strategy/context views. U: full price-vol-time pressure-root model. [C37] [C38] |
| **12. Confidence** | U: calibrated participant or extrema probabilities. Filtered activity is a selection, not a reliability estimate. |
| **13. Historical validation** | D: user-accessible historical/backtesting workflow for DEX. U: relevant frozen protocol, sample and independent result. [C37] |
| **14. Fact versus inference** | D: displayed trade evidence and inference controls. I: “opening,” “smart” or “whale” labels cannot independently prove intent. |
| **15. Irreducible proprietary part** | U: inference, detector/scorer, dealer reconstruction and historical selection logic. |

**Naming warning:** Tradytics’ **Daily Options Deltas (DEX)** is a historical predictive framework. Elsewhere “DEX” frequently means a physical dollar-delta exposure. Mastermind needs canonical quantities and unit metadata rather than a shared acronym. [C37]

## 11. OptionsDepth

| Commission field | Finding |
|---|---|
| **1. User decision** | D: inspect participant positioning and potential hedge sensitivity across price and time. [C40] [C41] |
| **2. Display** | D: gamma/charm/vanna heatmaps and 3D surfaces, participant exposures, strike/expiry breakdown, net and change views. [C41] [C42] |
| **3. Structural versus flow** | D: intraday participant-book analytics; “flow” mode means exposure difference between chosen times. I: that difference may include repricing. [C42] |
| **4. Inventory basis** | D/V: the FAQ claims Cboe participant-tagged data rather than bid/ask heuristics. U: complete initial inventory, coverage and reconciliation sufficient to substantiate “actual positions.” [C40] [C44] |
| **5. Components** | D: separate delta, gamma, charm and vanna. U: a disclosed total pressure/liquidity or auction-nowcast model. [C42] |
| **6. Update frequency** | D: one-minute snapshots. U: measured feed and consumer latency. [C40] |
| **7. Cross-products** | D: SPX and VIX are documented. U: common hedging aggregation between them. [C40] |
| **8. SPX/SPY/XSP/ES** | U: complete S&P product integration not established. ES is discussed as a possible SPX hedge, which is a different fact. [C43] |
| **9. 0DTE** | D: explicit expiry filters and projected near-expiry convexity; later expiries contribute to the book. [C42] [C43] |
| **10. Level definitions** | D: gamma peaks/troughs and time-varying exposure regions. U: calibrated probabilities attached to those locations. [C43] |
| **11. Static or dynamic** | D: aggregate portfolio sensitivities across hypothetical spot/time, not solely raw strike histograms. [C43] [C44] |
| **12. Confidence** | D: accuracy claims; U: disclosed posterior, uncertainty band or probability calibration. |
| **13. Historical validation** | D: chart/API history and a separate historical data shop. U: peer-reproducible predictive study. Data availability is not validation. [C40] [C45] |
| **14. Fact versus inference** | D: richer origin-data claim. I: participant categories can improve attribution without observing external hedges or proving the full inventory state. |
| **15. Irreducible proprietary part** | U: seed inventory, book maintenance, corrections, projection inputs and derivation from tagged transactions. |

The FAQ advertises an API exposure horizon up to 90 DTE, while the Data Shop describes positional coverage up to 60 DTE. These can describe different products; treat them as separate coverage contracts. Do not silently extrapolate one entitlement or historical dataset to another. [C40] [C45]

**Mastermind lesson:** this is a serious benchmark for evaluating a participant-data upgrade. Verify the exact source product, exchange scope, starting inventory and known-at revisions before promoting an inferred book to a stronger evidence label.

## 12. QuantData

| Commission field | Finding |
|---|---|
| **1. User decision** | D: determine current Pin/Grind/Volatile/Transition state, likely persistence and range; inspect options-flow changes around levels. [C46] |
| **2. Display** | D: Exposure Forecast, strike-time Interval Map, exposure ladders, Net Drift and replay. [C46] [C47] [C49] |
| **3. Structural versus flow** | D: exposure snapshots and differences coexist with trade-derived premium sentiment. U: exposure inventory reconstruction. [C47] [C49] |
| **4. Inventory basis** | D: positioning is explicitly described as estimated. Net Drift signs trades by their execution within the spread. U: whether the exposure model uses that same classifier or additional position data. [C46] [C49] |
| **5. Components** | D: delta/gamma/vanna/charm filters, flow, price and optional dark-zone context; Forecast compresses information into market states. U: combination weights and executable liquidity. [C47] [C50] |
| **6. Update frequency** | D: older exposure guidance specifies roughly five seconds; Interval Map supports minute aggregation. U: measured Forecast publication latency. [C47] [C48] |
| **7. Cross-products** | D: broad ticker coverage; Net Drift can aggregate market/sector/industry sentiment. U: shared dealer inventory across products. [C46] [C49] |
| **8. SPX/SPY/XSP/ES** | D: Forecast can project levels onto futures axes. U: combined inventory across the S&P complex. [C46] |
| **9. 0DTE** | D: expiry filters include same-day contracts; exact-time settlement/Greek qualification remains U. [C48] |
| **10. Level definitions** | D: call/put exposure walls and gamma flip; walls need not lie on their expected side of spot. [C46] |
| **11. Static or dynamic** | D: time-varying exposure maps, state changes and forecast bands. I: a bubble’s change is not proof of new dealer contracts. [C47] |
| **12. Confidence** | D: state-persistence probabilities at 30/60/90/120-minute horizons, late-session close horizon, and hold-strength labels. Net Drift separately visualizes unclassified midpoint trades. [C46] [C49] |
| **13. Historical validation** | V: roughly 90% Pin versus 75% Volatile one-hour tight-range persistence; Volatile moves about twice as large. U: band definition, dates, sample, splits and calibration. [C46] |
| **14. Fact versus inference** | D: Forecast explicitly does not predict direction. I: state confidence cannot be reused as a directional, touch, extreme or close probability. [C46] |
| **15. Irreducible proprietary part** | U: state classifier, probability model, training data and dealer-position assumptions. |

**Documentation contradiction:** the Interval Map article gives opposing descriptions of short-gamma hedging on an upward move. Its later description and QuantData’s dedicated GEX explanation correctly identify buying into a rise for a delta-hedged short-gamma book. Mastermind should validate signs from explicit inventory and Greek definitions, never color or prose alone. [C47] [C48]

The API is a useful schema comparator: exposure requests distinguish Greek, representation units, expiry/strike and snapshot time. Historical timestamps are necessary but do not alone prove that data at those timestamps preserves the version actually available then. [C50]

## 13. MomoEdge

| Commission field | Finding |
|---|---|
| **1. User decision** | D: move from market/regime selection to structural context and ranked options activity. [C51] |
| **2. Display** | D: Pulse, PRISM, Flow and heatmap; Oracle is described as a context synthesis layer. [C51] [C52] |
| **3. Structural versus flow** | D: PRISM covers strike/expiry structure; Flow scores transactions. U: exact linkage and inventory updates. [C51] |
| **4. Inventory basis** | U: dealer-sign assumptions, participant feed, seed book and reconciliation. |
| **5. Components** | D: structure, flow, macro and technical information are combined at the synthesis layer. U: individual weights and Greek attribution. [C52] |
| **6. Update frequency** | D: live/frequent wording; U: per-surface measurable cadence. [C51] |
| **7. Cross-products** | D: US equity/index/ETF-oriented workflow. U: cross-product hedge normalization. [C51] |
| **8. SPX/SPY/XSP/ES** | U: no combined book established. |
| **9. 0DTE** | D: expiry-dependent scoring horizons are described. U: exact same-day inventory and fixing mechanics. [C51] |
| **10. Level definitions** | D: gamma/OI/volume, key levels and pin-versus-acceleration framing; U: precise rules. [C51] |
| **11. Static or dynamic** | U: dynamic-state equations and validated level migration. |
| **12. Confidence** | D/V: trade scores and demonstration precision. U: probability calibration. [C51] |
| **13. Historical validation** | V: outcome tracking and a demo precision of 0.71 for high-score trades. U: denominator, test split and independently verified result. [C51] |
| **14. Fact versus inference** | D: indexed first-party descriptions only; no authenticated or live product inspection. |
| **15. Irreducible proprietary part** | U: PRISM rules, score training, horizon routing and Oracle synthesis. |

The indexed homepage mixes different training counts and V8 demonstrations with a forthcoming-beta statement. Dataset scope and product maturity remain unresolved. [C51]

## 14. FirmTape — additional comparator

| Commission field | Finding |
|---|---|
| **1. User decision** | D: distinguish exposure conventions, observe current structure and investigate whether a hypothesized effect survives controls. [C54] |
| **2. Display** | D: strike ladders, separate signed/OI-convention/volume books, Greek diagnostics, history and futures-axis levels. [C54] |
| **3. Structural versus flow** | D: quote-signed SPX 0DTE activity is distinct from OI-based broader-expiry structure and unsigned volume. [C54] |
| **4. Inventory basis** | D: a trade-sign-derived book is called measured; I: quote signing still does not observe participant identity. U: verified initial inventory and external netting. [C54] |
| **5. Components** | D: delta, gamma, vega, vanna and charm readouts remain inspectable. U: complete options-plus-auction causal model. [C54] |
| **6. Update frequency** | D: SPX stream about one second; other option chains about five minutes. Status logs expose dropped packets, restarts and rebuilds. [C54] [C56] |
| **7. Cross-products** | D: over one hundred additional chain books; book methodology differs from the signed SPX product. [C54] [C56] |
| **8. SPX/SPY/XSP/ES** | D: futures are mapped index levels, not a merged native futures-option book. [C54] |
| **9. 0DTE** | D: explicit signed same-day book and separate wider-expiry conventions. U: participant-ground-truth accuracy. [C54] |
| **10. Level definitions** | D: gamma concentrations and zero crossings with distance/relevance controls. [C54] |
| **11. Static or dynamic** | D: changing ladders/levels, replay and basis adjustment. I: revised replay is not automatically as-seen-live evidence. [C54] [C56] |
| **12. Confidence** | D: published methodological caveats and weak/null findings. U: calibrated LOD/HOD or close probabilities. |
| **13. Historical validation** | D/V: 1,088 SPX sessions, April 2022–August 2026; minute regressions with controls and a final 40-session holdout. Effects are tiny and held-out evidence weak. [C53] |
| **14. Fact versus inference** | D: study defines flow from negative changes in dollar DEX. I: these changes can mix inventory, spot, IV and time effects, so they do not identify observed hedging latency. [C53] |
| **15. Irreducible proprietary part** | U: upstream tape entitlements, classifier/reconstruction implementation and full live-revision behavior. |

The study reports effects under approximately 0.05 basis points per standard-deviation impulse at its strongest short horizons and explicitly declines to call this a trading edge. The direction/timing association is worth independently testing. It does not prove that dealers executed the inferred trades, and randomizing signs does not eliminate all endogeneity in the original exposure measure. [C53]

**Operational and rights limits:** status “100%” measures represented minutes, not every print. Dropped-packet and replay logs matter independently. A rebuilt historical state can differ from what a live consumer saw. The licensing page offers derived-data redistribution but excludes a competing dealer-positioning terminal from every listed tier; raw vendor tape is never included. Therefore a standard subscription is not evidence that this is an admissible Mastermind data supplier. No acquisition or license action was taken. [C55] [C56]

## 15. quantedOptions — additional comparator

| Commission field | Finding |
|---|---|
| **1. User decision** | D: read regime, strike concentrations, projected sensitivity and flow beside an execution-platform chart. [C57] |
| **2. Display** | D: ladders, gamma/charm/vanna surfaces, premium flow, cumulative delta/gamma, historical replay and earlier-snapshot overlays. [C57] [C58] |
| **3. Structural versus flow** | D: separate market-maker SPX/VIX product and OI/volume-based ticker product. [C58] |
| **4. Inventory basis** | D/V: quantedGamma claims licensed Cboe minute participant data; quantedTicker explicitly uses OI/volume and conventional call-positive/put-negative gamma. [C58] |
| **5. Components** | D: Greeks retain separate scales; premium flow and book delta are different panels. U: calibrated total hedge demand versus executable liquidity. [C57] |
| **6. Update frequency** | D: minute SPX/VIX recomputation. Ticker OI updates overnight; intraday changes reprice spot/time/IV. [C58] |
| **7. Cross-products** | D: wide ticker coverage and several platform/futures overlays, with different underlying models. [C57] |
| **8. SPX/SPY/XSP/ES** | D: SPX-to-ES chart conversion. U: a combined SPX/SPY/XSP/ES position estimate. [C57] |
| **9. 0DTE** | D: zero-day/all-expiry selections and an all-minus-zero-day view for later positioning. [C58] |
| **10. Level definitions** | D: per-strike concentration, hypothetical-spot gamma profile and its zero crossings, plus straddle-related range. [C57] [C58] |
| **11. Static or dynamic** | D: minute ladders, surfaces, replay and prior-snapshot comparison. |
| **12. Confidence** | D: source/model/freshness distinctions; U: calibrated probability of a level holding or becoming an extreme. [C57] |
| **13. Historical validation** | D: replay and case-study material; U: independently reproducible conditional-outcome calibration. [C58] |
| **14. Fact versus inference** | D: public method separation. I: tagged transactions strengthen attribution but do not by themselves prove the complete starting book. |
| **15. Irreducible proprietary part** | U: initial participant holdings, correction/reconciliation logic, historical known-at versions and full licensed redistribution scope. |

**Mastermind lesson:** put the **method and source class at product level**, not just in a global disclaimer. A tagged index book and an unsigned-OI equity model should never share a label that implies identical inventory evidence.

## 16. ZeroGEX — additional comparator with direct closing-pressure overlap

| Commission field | Finding |
|---|---|
| **1. User decision** | D: inspect structure, trade-derived hedging pressure, scenario hedge changes and late-day directional context. [C62] [C63] [C64] |
| **2. Display** | D: walls/flip, expiry heatmaps, separate flow views, EOD score, full-reprice curve, charm-to-close path, vanna ladder and historical/projected pressure field. [C63] [C65] |
| **3. Structural versus flow** | D: standing OI is separate from classified session trades; intraday structural changes are repricing. [C59] [C60] [C64] |
| **4. Inventory basis** | D: conventional assumed dealer-long calls/short puts. Hedging Flow separately assumes a dealer on the passive side of classified prints. Neither is presented in the detailed methodology as observed inventory. [C59] [C64] |
| **5. Components** | D: full scenario repricing is primary for Forced Flow, with Greek attribution; the EOD score is a separate heuristic combination of charm, pin/momentum context, time and calendar. [C62] [C63] |
| **6. Update frequency** | D: approximately one-minute levels/scores, five-minute flow, faster quotes. These are distinct clocks. [C60] |
| **7. Cross-products** | D: SPX/SPY/QQQ/NDX analytics; ES/NQ price axes. Single-name expansion is a roadmap item in the coverage document. [C60] |
| **8. SPX/SPY/XSP/ES** | D: futures charts reuse index books with carry adjustment; no native futures-option aggregation. Dollar exposures remain unprojected in that display. [C60] |
| **9. 0DTE** | D: true same-date flow filter can return no eligible book; near-expiry structure is explicit. Multi-day model weighting deliberately attenuates the shortest maturities. [C59] [C64] |
| **10. Level definitions** | D: gamma concentration walls, repriced gamma roots, and zero-flow prices where modeled endpoint hedge change cancels. [C59] [C63] [C65] |
| **11. Static or dynamic** | D: zero-flow roots move with the scenario and remaining time; negative/positive local flow slopes distinguish attraction-like and repulsion-like topology. [C63] |
| **12. Confidence** | D: score thresholds are hand selected; a separate charm track record compares against a naive baseline with an interval. U: a calibrated probability of root attraction. [C62] [C63] |
| **13. Historical validation** | D/V: a ten-week, 737-touch wall study; no published multi-session zero-flow closing-location study. The new charm evaluation is a narrower estimand. [C61] [C63] |
| **14. Fact versus inference** | D: unusually explicit model assumptions. I: full repricing improves conditional arithmetic without identifying inventory or ensuring realized price response. |
| **15. Irreducible proprietary part** | U: operational data vendors, classification/revision details and validated signal selection. Public descriptions do not provide independently certified performance. |

The **EOD score is not a probability**: its components, saturation points and calendar/time adjustments are described as house choices. It can amplify a reading because of the calendar without new evidence. Its fixed afternoon window leaves the score inactive on half-days, according to the coverage page. Mastermind should retain the useful decomposition while using actual exchange-session horizons and separately estimated reliability. [C62] [C60]

The wall study uses proximity within five basis points, a buffered break sustained for ten minutes, and an hour horizon; it treats unresolved end-of-day observations as censored. It reports approximately 31% hour-ahead break probability for S&P products and about 47–50% for Nasdaq products. Nineteen proposed covariates did not yield a robust discriminator in that small window. This is a falsification challenge, not a universal proof that size, gamma regime or flow never matter. Its claimed invariance across products also exceeds what a short sample can establish. [C61]

**Mastermind lesson:** the generic full-reprice/transition-root mechanism already exists publicly. Differentiation must come from better inventory uncertainty, correct known-at evidence, liquidity and closing-flow separation, and genuinely out-of-sample outcome calibration. A new visualization alone would not settle the commission.

## 16A. FlashAlpha — additional API and data-quality comparator

| Commission field | Finding |
|---|---|
| **1. User decision** | D: inspect inferred same-day hedge pressure, changing concentration and pin context through an API or dashboard. [C66] [C69] |
| **2. Display** | D: per-bar/cumulative hedge-flow estimates, call/put splits, exposure Greeks, evolving magnet and pin-score components. [C66] [C69] |
| **3. Structural versus flow** | D: settled exposure and a distinct flow-adjusted effective-OI suite. [C68] |
| **4. Inventory basis** | D: quote-side volume feeds an OI estimator calibrated against later settled-OI residuals. U: independent opening/closing or dealer labels. [C68] |
| **5. Components** | D: core methodology applies call/put dealer polarity to GEX alone; other Greek aggregates use their natural signs. I: these are not automatically derivatives of one consistently signed portfolio. [C67] |
| **6. Update frequency** | D: minute Greek snapshots; plan-dependent caching. Hedge-flow bars offer 30-second through 15-minute aggregation. These are not identical to feed latency. [C66] [C67] |
| **7. Cross-products** | D/V: native CME futures-option chains, Black-76 and actual contract multipliers, alongside equity/index analytics. [C71] |
| **8. SPX/SPY/XSP/ES** | D: compatible output across SPY/SPX/ES is claimed. U: a jointly netted inventory posterior or complete S&P aggregation. [C71] |
| **9. 0DTE** | D: explicit same-day hedge-flow scope; empty bars outside an eligible session or before samples exist. Newer quality documentation describes settlement-aware exclusion. [C66] [C70] |
| **10. Level definitions** | D: gamma concentration/flip and a magnet selected by largest absolute net gamma, with a component-based pin score. [C69] |
| **11. Static or dynamic** | D: magnet and score change as effective OI and market inputs change. I: maximum absolute gamma alone does not establish attraction topology. [C69] |
| **12. Confidence** | D: pin-strength score and separate input-quality telemetry. U: calibrated probability of pinning, touching or holding. [C69] [C70] |
| **13. Historical validation** | D/V: OI residual fitting, internal Greek/aggregate checks and root stress tests. U: independently reproduced predictive validation. [C67] [C68] [C70] |
| **14. Fact versus inference** | D: current-engine historical recomputation is explicitly described. I: this differs from replaying the exact analytical output published by an older model. [C72] |
| **15. Irreducible proprietary part** | U: fitting internals, full classifier/position state, feed rights and reconciliation of differing documentation vintages. |

The OI fitting exercise does not make quote-side buying synonymous with opening, or selling with closing. Each can open or close a position. A scalar that reduces aggregate residual bias is not a calibrated per-trade opening probability; midpoint omission also needs an explicit uncertainty envelope. [C68]

The July core document admits unversioned historical overwrites. August historical and September quality documents instead assert immutable/traceable inputs. This may reflect upgrades, but a buyer needs the effective dates, covered datasets and original versus revised extracts reconciled. Even with immutable inputs, current-engine reconstruction is a different research object from original-live model output. [C67] [C70] [C72]

The core document also states that standard access does not license redistribution, embedding or white-label use. API availability therefore does not itself settle suitability as a Mastermind input. No API was executed and no commercial action was taken. [C67]

### GammaTape: a bounded negative example

GammaTape’s September article describes OI-derived Greek charts but treats annualized IV as necessarily disappearing at same-day expiry. Time can shrink remaining variance to zero while annualized IV stays positive; substituting an IV-to-zero shock for time runoff confounds vanna and charm. This is a methodological counterexample, not a reason to copy its aggregate calculation. [C73]


## 17. Evidence and falsifier register

These entries are compact research decisions, not accusations that a vendor’s private system lacks capabilities. “Not established” means the inspected public evidence is insufficient.

| ID | Claim or tempting interpretation | Evidence and limitation/contradiction | Concrete falsifier or acceptance test |
|---|---|---|---|
| **CR01** | A frequently refreshed exposure map contains newly observed dealer inventory. | Repricing-only ticker models are explicitly documented. [C58] [C60] | Freeze positions; reprice spot/IV/time. If this reproduces most changes, label them sensitivity updates. Require transaction attribution for the remainder. |
| **CR02** | Synthetic OI has one unambiguous intraday cadence. | SpotGamma support and landing descriptions differ. [C10] [C11] | Product/version-specific publication receipts and measured component refresh intervals. |
| **CR03** | Participant-tagged flow establishes the full dealer book. | Richer attribution is claimed, but initial holdings and extra-book hedges remain unresolved. [C40] [C58] | Reconcile a known seed, all eligible events, corrections, expirations and transfers against independent positions, with coverage by venue/product. |
| **CR04** | Matching a next-day OI change identifies each print’s opening/closing status. | DDOI uses later OI, but many latent assignments can fit one net change. [C13] | Enumerate observationally equivalent assignments; evaluate real-time posterior calibration on independent labels. Do not backfill future OI into live features. |
| **CR05** | A change in hedge dollar value equals dollars of additional hedge purchases. | The IOB numerical example mixes existing-position repricing with changed units. [C12] | Compare endpoint units required with prior units, then value only the difference at the chosen execution/scenario price. |
| **CR06** | The sign of short-gamma hedge demand can be read from vendor colors or prose. | QuantData’s Interval Map explanations conflict. [C47] [C48] | Explicit long/short call/put unit tests across spot directions; identical sign conventions in data, chart and narrative. |
| **CR07** | A high wall hold percentage establishes tradable containment. | Published nonbreach, closing-side and conditional-touch outcomes differ. [C09] [C28] [C61] | Score touch, subsequent break, first-passage order, close side and session extreme separately against distance/IV/technical baselines. |
| **CR08** | A state-persistence probability predicts direction. | QuantData explicitly separates the two. [C46] | Calibrate each declared outcome separately; reject any UI conversion from regime probability to buy/sell probability. |
| **CR09** | Volume centroids reveal opening speculation and tomorrow’s/closing targets. | Volume patterns and inferred positioning are different objects. [C19] [C20] | Control contemporaneous spot and moneyness migration; require lead-lag skill and incremental out-of-sample value. |
| **CR10** | A vendor’s historical trade score demonstrates population precision. | MomoEdge’s indexed performance/maturity accounting is unresolved. [C51] | Frozen model, all eligible candidates, matured labels, exact score threshold, denominator, horizon and complete misses. |
| **CR11** | Dark short volume proves institutional buying. | FINRA documents a customer-selling pathway to short-marked public prints. [C17] | Test the hypothesis without owner labels; reject deterministic buyer-motive attribution. |
| **CR12** | ES support means a combined S&P options book. | Several products explicitly transform the display coordinate only. [C29] [C54] [C57] [C60] | Trace every contributing contract and multiplier; compare chart mapping with actual common-risk aggregation. |
| **CR13** | Dollar-DEX regressions measure actual dealer hedge speed. | FirmTape’s regressor includes exposure changes, with tiny/weak held-out results. [C53] | Decompose trades and repricing, control stock-led information, and validate against independently observed execution where available. |
| **CR14** | Complete historical minutes prove complete live tape. | FirmTape separately logs drops and rebuilds. [C56] | Compare event counts/sequences, received-at values and revision vintages. Keep original-live and rebuilt histories separate. |
| **CR15** | A zero-flow root must attract price. | ZeroGEX distinguishes root topology and does not claim a multi-session target result. [C63] | Frozen point-in-time roots; slope class; placebo roots; distance/volatility controls; out-of-sample touch/attraction/extreme/close outcomes. |
| **CR16** | Calendar amplification or charm sign adds predictive evidence. | ZeroGEX’s weights and timing are heuristic. [C62] | Compare exact runoff with incumbent controls, calendar-only and price-momentum baselines; respect Mastermind’s prior signed-charm refutation. |
| **CR17** | An API or redistribution tier authorizes the intended integration. | FirmTape explicitly excludes a competing positioning terminal. [C55] | Review the actual contracted use, derived-data rights and consumer scope before acquisition; do not infer rights from a schema. |

## 18. What to bring into Mastermind

### Preserve these product jobs

1. **Pressure beside price, with structural context.** Show recent classified flow, cumulative flow and standing-book sensitivity as separately named quantities. Expose disagreement rather than averaging it away. HIRO and QuantData provide useful interface precedents. [C01] [C49]
2. **A scenario surface with interpretable transitions.** A selected horizon/IV scenario should reveal where required hedge demand changes direction and whether local topology is absorption-like or acceleration-like. TRACE, OptionsDepth and ZeroGEX demonstrate the job. A root remains a model output. [C06] [C43] [C63]
3. **A direct distinction between input uncertainty and forecast uncertainty.** Midpoint ambiguity bands, source/model labels, and state/outcome probabilities solve different questions. Keep each visible. [C49] [C57]
4. **Historical outcomes with explicit definitions.** A level inspection should disclose touch, breach, excursion, close-side and extreme outcomes separately. Historical examples and aggregate percentages must retain their cohort and as-of version. [C28] [C61]
5. **Abstention that means something.** No eligible expiry, unresolved root, stale source, insufficient comparable history and outside-session horizon require distinct states. They should not silently become zero or neutral. [C59] [C60] [C64]

### Extend the existing ontology, without another omnibus score

The October 3 contracts already provide the appropriate starting objects:

| Existing family | Extension informed by this census | Required boundary |
|---|---|---|
| **OIF04 / OIF06 / OIF30** | Flow rate, cumulative classified dollar delta and ambiguity envelope next to price. | Aggressor inference stays separate from participant and opening/closing inference. |
| **OIF11 / OIF12** | Keep gross OI cash-gamma scale distinct from signed inventory scenarios. | Unsigned exposure size does not identify dealer direction. |
| **OIF13 / OIF14 / OIF15** | Full spot/IV/time hedge scenarios with vanna/charm attribution and residual nonlinear interaction. | Same inventory scenario, units and endpoint convention across comparisons. |
| **OIF16 / OIF17 and existing gamma profile** | Concentration nodes, distances and root classes tied to dynamic scenarios. | A concentration, gamma zero and flow zero are separate level types. |
| **OIF18** | Subsequent OI changes constrain retrospective reconstruction and future model learning. | Following-session OI cannot identify each print's intent or become an earlier live input. |
| **OIF29 / OIF31 / OIF33** | Expiry composition, turnover and near-spot concentration. | Activity and exposure concentration do not establish a fresh dealer position. |
| **OIF32 / OIF34** | Exact near-expiry runoff and final-hour IV/Greek diagnostics. | Economic expiry/fixing and remaining-session clocks; no assumed universal charm direction. |
| **Existing quote/flow/Radar/evaluation owners** | Source quality, known-at replay, outcome and incremental-baseline evaluation. | Preserve the incumbent data plane and prior nulls. |

This mapping is architectural advice, not an activation decision or new pilot authorization. The principal should reconcile exact family names and current owners with the pinned catalogue when preparing the implementation package.

### What still differentiates the commission

The competitor census does **not** supply the missing scientific bridge from options-associated exposure to realized price pressure. Mastermind still needs to determine:

- which inventory states remain plausible under the available evidence;
- how much their scenario hedge demands disagree;
- whether those demands are material relative to eligible, contemporaneous executable liquidity;
- which alternative cash, futures, ETF, benchmark and auction channels explain the same movement;
- whether those features improve specific out-of-sample outcomes beyond the incumbent information;
- how the forecast transitions to an official-auction nowcast without retroactively contaminating the earlier prediction.

Those are the commission’s unresolved research tasks. They should remain visible even if the eventual interface can reproduce every attractive chart surveyed here.

## 19. Research limits and reproducibility

This lane audited public descriptions and first-party research, not paid production systems or raw vendor data. Vendor studies were inspected, not rerun. Source absence is scoped to the inspected documents. Current undated pages can change without version history; the source register records retrieval on 6 October 2026 and identifies publication dates when available.

The IOB PDF was retrieved openly and locally parsed because the web reader rejected its file size. The report audits a short numerical example; it does not reproduce the paper or its code. No proprietary formula, source code, image library, paid dataset or production collector was copied into the deliverable.

The authoritative source metadata is in **evidence/sources_competitors.json**. Bracket references in this report resolve to stable public URLs. Source titles, reported dates, access limitations and tool reference identifiers are preserved there for principal verification.

<!-- Report-local source links. Scope and access limits are in SOURCE_REGISTER.md. -->

[C01]: https://support.spotgamma.com/hc/en-us/articles/4420646443539-What-is-the-SpotGamma-HIRO-Indicator
[C02]: https://spotgamma.com/hiro-lp/
[C03]: https://support.spotgamma.com/hc/en-us/articles/12284071347091-What-does-the-All-Trades-filter-indicate
[C04]: https://support.spotgamma.com/hc/en-us/articles/33607907909011-What-is-SpotGamma-TRACE
[C05]: https://support.spotgamma.com/hc/en-us/articles/33608037264787-What-is-the-Gamma-Heatmap
[C06]: https://support.spotgamma.com/hc/en-us/articles/33608084842643-What-is-the-Delta-Pressure-Heatmap
[C07]: https://support.spotgamma.com/hc/en-us/articles/33608198289043-What-is-the-Charm-Pressure-Heatmap
[C08]: https://support.spotgamma.com/hc/en-us/articles/50497959584787-What-is-the-TRACE-Stability-Gauge
[C09]: https://support.spotgamma.com/hc/en-us/articles/31209900542867-SpotGamma-SPX-Key-Levels-Statistics
[C10]: https://support.spotgamma.com/hc/en-us/articles/39946919887891-What-is-the-Equity-Hub-Synthetic-OI-Open-Interest-Model
[C11]: https://spotgamma.com/equity-hub-synthetic-oi-lp/
[C12]: https://squeezemetrics.com/download/The_Implied_Order_Book.pdf
[C13]: https://squeezemetrics.com/monitor/static/guide.pdf
[C14]: https://squeezemetrics.com/monitor/docs
[C15]: https://squeezemetrics.com/download/white_paper.pdf
[C16]: https://squeezemetrics.com/monitor/dix
[C17]: https://www.finra.org/rules-guidance/notices/information-notice-051019
[C18]: https://www.gammaedge.com/trade-futures
[C19]: https://www.gammaedge.com/blog/price-follows-speculation-spx-0dte-volume-patterns
[C20]: https://www.gammaedge.com/blog/price-follows-speculation-specpa-specps-part-2
[C21]: https://www.gammaedge.com/blog/master-market-structure-analysis-how-to-use-netstat-to-anticipate-price-moves-through-delta-gamma-charm-and-vanna
[C22]: https://www.gammaedge.com/web-app-sign-up
[C23]: https://www.gammaedge.com/blog/options-market-analysis-how-options-drive-stock-prices-in-modern-markets
[C24]: https://menthorq.com/guide/menthorq-asset-coverage/
[C25]: https://menthorq.com/guide/intraday-gamma-models/
[C26]: https://menthorq.com/guide/options-menu/
[C27]: https://menthorq.com/guide/cboe-market-maker-tagged-data-explained/
[C28]: https://menthorq.com/guide/levels-backtesting-add-historical-probability-to-every-key-trading-level/
[C29]: https://menthorq.com/guide/levels-conversion/
[C30]: https://menthorq.com/guide/gamma-levels-on-forex/
[C31]: https://tier1alpha.com/
[C32]: https://app.hedgeye.com/insights/136818-hedgeye-announces-partnership-with-options-research-provider-tier-1-al?type=macro,market-insights
[C33]: https://tier1alpha.com/market-impact-of-0dte-flows-navigating-gamma-exposure-and-delta-hedging-in-short-duration-markets/
[C34]: https://app.hedgeye.com/mu/he_tms_km_rr_3-6-2026?encoded_data=fC82%21uJh3J20JTd9mUtaFpVsGjn9C8z0%3D%2C
[C35]: https://tradytics.com/support/how-to-understand-dealer-positioning-gamma-vanna-charm
[C36]: https://tradytics.com/support/where-do-you-get-data-from
[C37]: https://tradytics.com/support/what-is-dex
[C38]: https://tradytics.com/support/what-is-algo-and-net-flow
[C39]: https://tradytics.com/live-options-flow
[C40]: https://optionsdepth.com/faq
[C41]: https://optionsdepth.com/feature-market-makers-exposure
[C42]: https://optionsdepth.com/feature-positional-insights
[C43]: https://www.optionsdepth.com/resouce/market-makers-gamma-exposure-projection
[C44]: https://www.optionsdepth.com/resouce/market-makers-charm-exposure-projection
[C45]: https://optionsdepth.com/data-shop
[C46]: https://help.quantdata.us/en/articles/16936089-mastering-the-exposure-forecast-pin-grind-and-volatile-market-states
[C47]: https://help.quantdata.us/en/articles/11133167-mastering-the-interval-map-visualizing-greeks-exposure-in-real-time
[C48]: https://help.quantdata.us/en/articles/7852449-what-is-gamma-exposure-gex
[C49]: https://help.quantdata.us/en/articles/9900974-mastering-the-net-drift-tool-leveraging-order-flow-sentiment-for-smarter-options-trading
[C50]: https://quantdata.us/api/docs/endpoints/exposure-by-strike
[C51]: https://momoedge.ai/
[C52]: https://momoedge.ai/about
[C53]: https://www.firmtape.com/research/how-fast-do-dealers-hedge
[C54]: https://www.firmtape.com/guide
[C55]: https://www.firmtape.com/licensing
[C56]: https://www.firmtape.com/status
[C57]: https://www.quantedoptions.com/orderflow-plugin
[C58]: https://www.quantedoptions.com/learn/how-it-works
[C59]: https://zerogex.io/methodology
[C60]: https://zerogex.io/help/platform/data-coverage
[C61]: https://zerogex.io/education/how-often-do-gamma-walls-break
[C62]: https://zerogex.io/education/eod-pressure-explained
[C63]: https://zerogex.io/education/forced-flow-and-zero-flow-explained
[C64]: https://zerogex.io/help/platform/hedging-flow
[C65]: https://zerogex.io/help/platform/dealer-positioning
[C66]: https://flashalpha.com/articles/detect-gamma-squeeze-real-time-dealer-hedge-flow-api
[C67]: https://flashalpha.com/methodology
[C68]: https://flashalpha.com/articles/effective-open-interest-methodology-live-gex-from-flow
[C69]: https://flashalpha.com/articles/live-0dte-pin-risk-api-intraday-flow-adjusted-magnet
[C70]: https://flashalpha.com/methodology/data-quality
[C71]: https://flashalpha.com/methodology/futures
[C72]: https://flashalpha.com/methodology/historical-data
[C73]: https://gammatape.com/blog/dex-vanna-charm-on-the-0dte-chart
