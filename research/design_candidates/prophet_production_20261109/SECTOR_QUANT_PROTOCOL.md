# Prophet × Sector Intelligence — quantitative architecture and research contract

**Status:** C3 reasoning and primary-source research for the authorized design/masterplan extension, 9 November 2026 America/Vancouver. This is a proposed research and product specification. No internal protected outcomes, strategy backtests, trials, rankings, portfolio allocations or trades were run or authorized. All original Q01–Q24 work packets and their current admission boundaries remain intact. The Mastermind Quant Validation skill and validation cases were read; existing source/evaluation owners remain authoritative.

## 1. Decision to carry into the masterplan

Make **benchmark participation, sector allocation and within-sector security selection three separately observable jobs**. Sector Intelligence must influence where Prophet looks, what a candidate means, what challenges it, how it is monitored and how its outcome is attributed. A stock page with a sector badge does not fulfill this requirement.

The Chairman's beta-first mandate is a product and evaluation priority: Prophet must account for missed broad-market opportunity and establish credible market participation before presenting stock-selection success as an adequate result. It is not an empirical assertion that a leader-sector strategy already matches the market. Sector rotation is an active allocation decision. Cash exposure, concentration, late entries, wrong rotations and trading frictions can make it underperform a passive investable market benchmark even while some chosen stocks win.

Use a declared benchmark, currency, universe and risk objective for each market. Then measure the complete path from eligible opportunity to visible research, lawful entry, maintained exposure and outcome. Market beta is an estimated exposure; a sector label is not that exposure. A few high-performing published plans do not establish portfolio beta capture, market participation or alpha.

**Recommended product thesis:** “Understand the market, follow strengthening participation, identify independent leadership within it, and measure what each layer contributed.” Alpha outside currently leading sectors remains a deliberate discovery lane, particularly for nascent rotations; current sector leadership must not become a universal exclusion rule.

## 2. What the external evidence supports — and what remains a hypothesis

| Evidence | Narrow supported conclusion | Design implication and limit |
|---|---|---|
| Moskowitz & Grinblatt, *Do Industries Explain Momentum?*, Journal of Finance 1999 [QS1] | Their study finds an important industry component in stock momentum and reduced individual-stock momentum profitability after accounting for industry momentum. | Sector and member selection require separate baselines. This is historical research evidence, not acceptance of Prophet, every horizon, a long-only implementation or current US/HK/China performance. |
| Hong, Torous & Valkanov, *Do industries lead stock markets?*, JFE 2007, with their 2014 replication note [QS2, QS3] | The original study reports industry-return information about subsequent market returns; the authors' extension retains some predictability while highlighting time variation. | Industry information may inform a market-state model. Do not freeze a permanent causal leader list or claim exact pivot timing from this literature. The original non-US countries do not establish Hong Kong or mainland-China validation. |
| Moskowitz, Ooi & Pedersen, *Time series momentum*, JFE 2012 [QS4] | Their research concerns own-return trend persistence in 58 futures/forward instruments across asset classes, distinct from cross-sectional winner selection. | Market trend and relative sector leadership are separate features. A market can rise while a sector weakens relatively, or a defensive sector can lead in a falling market. Futures results do not automatically qualify single-stock implementations. |
| Daniel & Moskowitz, *Momentum crashes*, JFE 2016 [QS5] | Their momentum strategies experienced pronounced losses in some panic/rebound environments after market declines and high volatility. | Include reversal, crowding/concentration and rebound failure cases. “Alpha within beta leadership” cannot be called universally safest, nor may expected positive average performance replace downside evidence. |
| Ma, Liao & Jiang, *Factor momentum in the Chinese stock market*, Journal of Empirical Finance 2024 [QS6] | The paper reports a Chinese-market factor-momentum construction and relationships with stock/industry momentum that differ from a simple universal stock-momentum story. | Use it as motivation for market-specific controls, not a number to copy or an acceptance result. Publisher abstract was retrievable; full article was not retrieved in this review. |
| GICS methodology and Hang Seng Index Operation Guide [QS7, QS8] | Classification systems have their own hierarchy, business rules, review processes and changing constituent classifications. | Preserve taxonomy identity, version, effective dates and mapping confidence. US Healthcare, Hong Kong healthcare classifications and mainland industry groups are not interchangeable historical baskets. |
| HKEX Northbound order rules and official calendars [QS9, QS10] | Actual trading channels have instrument/board-specific price limits, turnaround restrictions, pre-trade checks and calendars. | Market-specific simulation rules must be keyed to date, instrument and channel. Do not run a frictionless US-style same-day entry/exit assumption across China or collapse calendar unavailability into a missing price. |

### Assertions that should not become UI facts

1. **“Institutions and money flow are moving into this sector.”** A rising price, turnover increase, relative-strength score or popular news cluster is not direct observation of institutional allocation. Label these as their actual measures. A flow claim needs a qualified flow source with scope, period, availability lag and revisions; ownership snapshots are different again. Liquidity provision by market makers is not evidence of directional conviction.
2. **“Companies save their best news for their sector's spotlight.”** This is a testable mechanism hypothesis supplied by the user, not an established result of the reviewed evidence. It may be consistent with incentives, but scheduled reporting, common fundamentals, media attention and industry news clustering are competing explanations. Keep the mechanism out of causal product copy until a dedicated study supports a bounded claim.
3. **“This is the safest strategy.”** Safety requires a stated loss/drawdown/exposure objective, comparator and evidence. The design should expose strengthening breadth and independent stock evidence together with concentration, fragility and failed-rotation risk. It should not turn leadership into a safety label.
4. **“There is X% left in this market cycle.”** Past run-up and historical phase averages do not identify remaining upside. Future return, downside and time-to-transition require separately qualified conditional forecasts. A forecast interval is not an amount the market owes.

## 3. Shared quantitative objects and no-double-counting rules

These are contract requirements to bind into the existing owners, not instructions to create a second feature store, model registry or grading service.

### 3.1 Three scales, distinct questions

| Scale | Core question | Examples of useful qualified inputs | Output distinction |
|---|---|---|---|
| Market | Is the declared market rising, falling, broadening, narrowing or changing risk state? | Benchmark total return, breadth, dispersion, volatility, liquidity and qualified macro context | Observed facts / filtered state / forecasts are different fields. |
| Sector, industry and economic theme | Where is relative leadership forming, strengthening, persisting or failing? | Excess return versus the selected market, breadth, concentration, issuer-excluded participation, dated economic links and qualified flow/event evidence | Relative leadership does not imply positive absolute return. Taxonomy sector and overlapping theme are different object types. |
| Security and issuer | Does this name add evidence beyond the common move? | Within-group excess/residual behavior, earnings/economic change, idiosyncratic catalyst, own liquidity/entry conditions and counterevidence | A good sector is a prior/context, not issuer proof or an entry authorization. |

Every joined object needs market, listing/security/issuer identity, taxonomy and membership versions, benchmark, currency/return basis, horizon, source clocks, decision cutoff, coverage and quality states. Market close in one timezone cannot be joined to a later close in another timezone as though both were available at the same decision.

### 3.2 Return explanations must use one coherent method

Two legitimate displays have different meanings:

- **Descriptive relative return:** show stock, sector basket and market benchmark over the same declared window and basis; arithmetic differences are “stock versus sector” and “sector versus market.” These are useful comparisons, not identified causal contributions or proved alpha.
- **Factor decomposition:** estimate market exposure and an incremental sector factor using only data available before the decision. A possible model is security excess return = market beta × market excess return + sector-residual beta × market-orthogonal sector return + unexplained residual. Fit and shrink coefficients under a frozen protocol, retain uncertainty and sample coverage, and expose the model/method vintage. Do not simply add raw market and raw sector returns because the sector already contains market exposure.

Where actual portfolio/model-portfolio weights exist, use the existing attribution owner's consistent accounting method for market exposure, sector allocation, within-sector selection, interaction, cash, FX and costs. State the benchmark and multiperiod linking convention. Do not mix regression residuals with accounting contributions in one additive chart. Unknown positions or missing weights mean attribution is unavailable, not zero.

### 3.3 Exclude self-confirmation at the issuer level

For candidate assessment, peer/sector confirmation excludes the candidate issuer's relevant securities, not merely one ticker. Retain the raw sector measure for market monitoring and the issuer-excluded measure for independent confirmation. Both should carry their membership/weight method and excluded weight. For concentrated industries, the difference is itself useful information. A singleton or near-singleton basket cannot supply reliable independent confirmation.

Overlapping economic themes require explicit exposure weights or separately labeled memberships. They are not mutually exclusive sector buckets. Deduplicate economic exposure across issuer classes and nested themes; show overlap instead of counting the same rally as multiple confirming signals.

### 3.4 Symbiotic, with no circular evidence

Sector Intelligence supplies dated context to Prophet. Prophet can return dated, source-qualified issuer observations, breadth of research coverage, earnings revisions, independent emergence and invalidations. A stock's Prophet ranking or popularity must not become upstream sector evidence and then re-enter the same stock as “independent confirmation.”

Keep raw observations, derived features and selected/published decisions separately identified. A downstream aggregate must declare its input population, lag/cutoff and lineage. Distinguish complete member breadth from breadth among only Prophet-selected names. Use out-of-fold/cross-fitted construction when a learned aggregate and downstream model would otherwise reuse labels or fitted residuals.

## 4. Market state, remaining opportunity and pivot contracts

The same market can have positive trailing trend, weakening breadth, expensive valuation and negative forward uncertainty. A single green/red regime label hides this disagreement. Use a compact primary state with inspectable components and an explicit counter-case.

| Product element | What may be displayed before predictive qualification | What needs a qualified model/protocol |
|---|---|---|
| Market direction | Dated realized returns, observed trend rule, breadth and dispersion; exact method/version | Probability or expected return for a future horizon |
| Sector leadership | Relative performance, issuer-excluded breadth, concentration, persistence under a declared descriptive rule | Probability leadership will persist or outperform after costs |
| Rotation/pivot watch | New observed transition under a known rule; competing signs and historical context | Calibrated transition probability, time window or actionable pivot forecast |
| Remaining opportunity | Price already traveled, valuation/economic scenarios with explicit assumptions, source coverage | Conditional future return quantiles, adverse-tail risk and time-to-event distributions |
| Opportunity confidence | Evidence coverage, freshness and agreement/disagreement | Probability calibration or expected economic utility |

Research labels should define an event from the decision time forward. Examples are a predeclared adverse threshold, a sustained change in relative leadership or a benchmark-relative target, each with horizon, censoring, competing outcomes and invalidation. Choose actual thresholds and horizons through the existing protocol before inspecting protected outcomes. Do not train on a future-smoothed cycle state and present it as an online state estimate. A turning point visible only after later bars has an earlier event date and a later confirmation/availability date; preserve both.

For “how much remains,” prefer a vector of qualified outputs: future net/benchmark-relative return distribution, adverse-tail probability, probability of target before invalidation, and expected/quantile time conditional on a defined event. They share a coherent event definition but are individually accepted or unavailable. A missing head must not be synthesized by an LLM or estimated from a decorative progress bar.

## 5. Research design: prove the separate contributions

### 5.1 Immutable experiment header

Before outcome access, freeze hypothesis, intended product use, target market and investor channel, universe, benchmark, currency, return convention, decision cadence, horizon/label, source and code/config versions, selection history, costs, capacity constraints, primary metric and meaningful success criterion. Record the historical availability status of every required feature. Use the existing Evaluation protocol and retention owners. This design amendment does not register a trial or permit protected outcomes.

Historical studies require point-in-time constituent and industry membership, corporate actions, delistings, halted names, failed issuers, source publication/revision clocks and model vintage. Current-only taxonomies or classifications can support a current research UI; they cannot retrospectively identify what the system knew. When a necessary historical input is unavailable, narrow the historical claim or use an independently admitted prospective shadow study.

### 5.2 Minimum economic baseline family

| Baseline | Construction/purpose | Key control |
|---|---|---|
| Passive investable market | The declared market benchmark, investable proxy and relevant costs/tracking differences | Same accessible market, currency, calendar and capital convention; disclose index versus executable vehicle. |
| Simple participation rule | A transparent existing-owner trend/exposure rule or constant exposure comparator | No higher leverage or unannounced risk budget as the source of apparent improvement. |
| Sector allocation only | Sector-context allocation with neutral/passive member selection | Isolate sector allocation while holding market exposure, risk budget and turnover assumptions comparable. |
| Member selection only | Prophet security selection under fixed benchmark sector allocations, or prespecified sector-neutral construction | Isolate member selection from accidental sector bets; retain the global discovery population. |
| Joint sector + member selection | Context-conditioned security selection/allocation | Test incremental value over both components and a simple additive alternative. |
| Incumbent Prophet policy | Exact retained incumbent source/policy convention | Preserve its original evidence era; do not retrofit improved context into its historical decisions. |
| Independent-emergence lane | Security observations outside current leading groups | Measure early new-leader recall and missed transitions without hindsight selection. |

Where the question includes market timing as well as sector allocation and stock selection, a prespecified factorial design can toggle each of the three mechanisms. That yields identifiable ablations rather than one opaque “new score beats old score.” Do not turn every optional toggle into a post-hoc search over the test set. A risk/exposure-matched comparison is required in addition to raw P&L; differences in invested time, market beta or concentration must remain visible.

### 5.3 Hypotheses to register as amendments to current Q packets

1. **Market participation:** context improves capture of the declared market opportunity under the same capital/risk objective, after costs and unavailable/no-entry states.
2. **Sector allocation:** context adds out-of-sample value beyond a simple trend/sector benchmark and market exposure alone.
3. **Member selection:** chosen names add value within their dated sector/industry after issuer-excluded context and common factor exposure.
4. **Interaction:** joint context and name evidence improve the declared task beyond additive separate models; partial pooling beats tiny unregularized context cells when evidence is thin.
5. **Transition awareness:** pivot/weakening information improves detection or management under a frozen delay/false-alarm tradeoff, rather than relabeling past turning points.
6. **Company news timing:** optional dedicated event study tests whether favorable issuer announcements cluster after observable sector attention/leadership, controlling for reporting calendars, fiscal seasonality, issuer effects, common shocks, news coverage and release/availability times. Correlation cannot establish deliberate scheduling or causality.
7. **Cross-market transfer:** a pooled or transferred model is compared with market-native baselines and calibration. A positive US result does not supply HK or mainland-China acceptance.

### 5.4 Evaluation design and implementation realism

Use rolling or expanding time-respecting train/validation/test windows. Fit normalization, imputation, membership-derived transforms, residualization, feature selection and calibration in their permitted windows only. Purge overlapping training labels crossing test information intervals; choose any embargo from the feature/label dependence, not a universal decorative percentage. Do not inspect the final test repeatedly while choosing the model.

Dates and sectors create strong shared dependence across individual names. Use date/sector/issuer-aware uncertainty estimation and disclose effective sample sizes. Repeated landmarks on one episode are not independent observations. Include name-disjoint and sector/regime sensitivity where relevant to the claimed transfer, without treating one split as sufficient for every claim. Record the number of tried candidates and corrections for selection/multiple comparisons.

Retain never-confirmers, no-entry/no-fill, failed rotations, overnight gaps, halts, delistings, excluded/unavailable source cases and tail periods. Report unavailable coverage separately from economic failure. Counterfactual comparisons use the same eligible cohort and decision opportunities, not only the names each model ultimately trades.

The fill model must use prices and order opportunities available after the signal and source-to-user latency. Include spreads, commissions, applicable taxes/fees, slippage, turnover, liquidity/participation limits, cash yield, dividends, corporate actions and currency conversion. Shorting/derivatives, if separately authorized, add borrow, financing and contract-specific restrictions. No assumption of a fill at a locked limit or an unavailable auction price.

China/HK/US require date-specific exchange/session and investor-channel rules. HKEX's current Northbound guidance differentiates Main Board, STAR and ETF price-limit arrangements and disallows turnaround trading in the reviewed route. The correct software contract is a versioned trading-constraints owner, not a hard-coded universal 10% rule. Stock Connect calendars and eligibility must match the investor's access route. A-share and H-share lines are distinct securities; currency, holiday, source latency and price limits can create different opportunity and risk even for the same issuer. [QS9, QS10]

### 5.5 Metrics aligned to the mandate

| Job | Required measurement family | Interpretive safeguard |
|---|---|---|
| Market participation | Net benchmark-relative return, tracking error, estimated beta with uncertainty, invested/cash exposure, upside/downside capture and missed-participation attribution | No guaranteed match; capture ratios unstable near a zero benchmark denominator need explicit handling. Measure full periods, not selected winning market days alone. |
| Sector allocation | Allocation contribution, sector-relative net return, concentration, rotation turnover, false pivots and leadership persistence by horizon | Compare with passive/equal-weight/simple trend alternatives on matched support. |
| Name selection | Within-sector selection contribution, market/sector-adjusted residual performance, matched risk/size/liquidity controls, distribution of wins/losses | “Residual” is not automatically skill or causal alpha. Avoid selecting winners first and explaining them later. |
| Forecast/pivot | Proper scoring rules, reliability, return-interval coverage/width, transition timing error, false-alarm/delay curve and abstention coverage | Evaluate selected top-K and thin cells separately; do not promise exact turning dates. |
| User usefulness | Time to find supported sector-aligned candidates, comprehension of absolute/relative strength, retained investigation and meaningful alert follow-through | Engagement alone is not an alpha label. Test whether users understand disagreement and uncertainty. |
| Operational reliability | Missing/stale taxonomy/source rates, late revisions, source-to-visible latency, cross-surface agreement and correction propagation | A broken source is distinct from a genuine economic weakening. |

**Acceptance is predeclared and job-specific.** There is no defensible universal Sharpe, win-rate, beta, alpha or probability threshold to invent in the design turn. Before evaluation, the existing research owner must freeze a meaningful minimum effect, uncertainty requirement, costs/stress scenarios and maximum allowed risk/concentration/turnover for the intended use. Economic qualification should require improvement or a declared noninferiority result versus the relevant baseline under that frozen objective, with coverage and failure regimes reported. Noninferiority margins must be chosen before outcomes. A broad-market participation objective is not silently replaced with lower drawdown after the return objective fails.

Release levels remain separate: source-correct descriptive research; accepted historical research model; prospective shadow evidence; approved product prediction/ranking/alert; any separately authorized portfolio/execution use. Failure at one level need not suppress useful descriptive context, but it does block dependent predictive claims.

## 6. Amend existing Q work; preserve the original programme

The source registry at the final Turn 4 commit already contains natural homes. Add bounded subprotocols and cross-references; do not renumber or silently overwrite original questions, endpoints, statuses or protected-outcome permissions.

| Original Q packet | Sector/market amendment |
|---|---|
| Q01 decision-time integrity | PIT taxonomy/membership/benchmark/flow availability and cross-session joins. |
| Q02 missed-opportunity attribution | Separate missed market participation, sector allocation, discovery, entry and management losses. |
| Q03 independent origination | Retain early sector turn/independent emergence observations and full discovery recall. |
| Q04 entry timing; Q15 execution realism; Q18 incumbent B4 | Context availability at the original cut; preserve incumbent policy/evidence era; market-native costs/fills and calendar constraints. |
| Q05 group leadership/member selection | Primary owner for sector-only/member-only/joint and issuer-excluded controls. |
| Q06 earnings; Q14 specialist evidence | Qualified event/flow features and optional news-timing study with causal limitations. |
| Q07 cycle domain; Q08 funding/original equity | Distinguish market/sector financial turn from economic recovery and original-shareholder survival. |
| Q09 remaining opportunity; Q11 calibration | Separate conditional return/tail/transition heads, censoring, selected-cohort calibration and abstention. |
| Q10 ranking; Q12 context routing | Fair context-conditioned ordering, partial pooling and out-of-support behavior; preserve research versus current-entry purposes. |
| Q13 propagation | Dated economic relation versus sector/theme association, overlap and circularity controls. |
| Q16/Q17 management | Deteriorating market/sector context as a separately qualified policy input; original thesis and strategy rules remain authoritative. |
| Q19 attention/alerts; Q24 comprehension | Meaningful sector/issuer transitions, explicit opt-in, actual delivery and comprehension of context/forecast distinctions. |
| Q20 representations | Compare more complex joint representations with transparent market/sector/member baselines. |
| Q21 portfolio | Primary home for benchmark participation, exposures, concentration, correlated names, allocation/selection/cash/FX/cost attribution. |
| Q22 operation | Distinguish source breakage from real regime drift and forecast degradation. |
| Q23 later sleeves/instruments | Market-native adaptation; no automatic international, short, options or leverage transfer. |

## 7. Exact Paper and implementation implications

1. **Today:** put a concise market-and-sector strip above candidate discovery: selected market/benchmark, absolute market direction, breadth, leading/strengthening/weakening groups and an explicit observation time. Show support and counter-case. Make “Explore Healthcare candidates” carry the exact group context into Prophet.
2. **Sector workbench:** rank groups under a declared purpose/horizon, retain coverage/concentration, distinguish observed rotation from forecast pivot, and show candidate research density separately from whole-sector breadth. A user can inspect member leaders, emergent challengers and contrary evidence.
3. **Security setup:** show market → sector/industry → security context with one coherent time basis. Provide both own-stock strength and issuer-excluded peer confirmation. A strong sector plus weak company or weak sector plus independently strong company remains explainable, not forced into one score.
4. **Screener/Compare:** filters expose sector state, market state, strength type, context freshness and independent member evidence. Preserve global/unmapped/unknown and independent-emergence routes. Compare supports market/sector-relative and raw views over matched windows.
5. **Plans/Follow:** retain context at the original decision alongside current context and source-qualified changes. A sector turn may invite reassessment under an accepted policy; it must not silently rewrite original reasons, invalidate every strategy or generate an alert on each rank shuffle.
6. **Record/portfolio:** provide a model-record view and, when actual qualified allocation data exists, a separate benchmark-participation and allocation/selection attribution view. Do not imply the current model-plan ledger alone proves portfolio returns or beta capture.
7. **Build notes:** every widget states its owner/ref, population, method, horizon, timestamp/availability, states, counterpart deep link and acceptance falsifier. Planned model output stays a labeled design fixture until the owning protocol accepts it. The Paper notes should contain this implementation mapping; product-facing copy should remain concise.

### High-value discriminating cases

- Sector is a relative leader while the whole market and sector both fall: UI distinguishes relative from absolute strength.
- Candidate dominates its sector weight: raw group strength differs from issuer-excluded confirmation; no self-certifying boost.
- Strongest current sector is a fading incumbent while a weak-ranked sector is starting to broaden: early-emergence lane preserves recall.
- Cross-market sector names match but memberships/taxonomies do not: no silent interchangeable peer set or benchmark.
- Source correction changes past classification or breadth: retain original context and disclose current correction; do not revise a historical signal silently.
- A US close arrives after China/HK decision time: future information excluded from that decision, even on the same calendar date.
- A stock gaps to an inaccessible limit after the signal: opportunity can exist, but fill/participation metrics retain no-fill and delay.
- Apparent joint alpha disappears when market exposure is matched: report exposure-driven performance, not selection skill.
- Market rebounds violently and old leaders lag: test the momentum/reversal failure case rather than inheriting a “safe leadership” label.
- Sector data is unavailable: useful issuer research remains accessible with explicit missing context; current-entry or forecasts dependent on it abstain.

## 8. Sources and read limits

All references below are primary research authors/publishers, index methodology owners or the exchange. Evidence was reviewed on 9 November 2026 PT (10 November UTC). No paper's historical return figure is adopted as a product promise, no full-source quote is reproduced, and no protected project outcomes were read.

- [QS1] Moskowitz, T. J. & Grinblatt, M. (1999), *Do Industries Explain Momentum?* Journal of Finance 54(4), 1249–1290. Publisher abstract and citation: https://onlinelibrary.wiley.com/doi/10.1111/0022-1082.00146 . Note: the issue is August 1999; the publisher's online publication timestamp is later.
- [QS2] Hong, H., Torous, W. & Valkanov, R. (2007), *Do industries lead stock markets?* Journal of Financial Economics 83(2), 367–396. Publisher abstract retrieved through search; direct full-page open returned 403: https://www.sciencedirect.com/science/article/pii/S0304405X06001383 . DOI https://doi.org/10.1016/j.jfineco.2005.09.010 . Do not claim a full-paper methods audit from this retrieval.
- [QS3] The same authors (7 October 2014), replication and extension note, author university-hosted PDF: https://rady.ucsd.edu/_files/faculty-research/valkanov/Note_10282014.pdf . The note also explicitly discusses data-download vintage changes, strengthening the requirement to retain source vintages.
- [QS4] Moskowitz, T. J., Ooi, Y. H. & Pedersen, L. H. (2012), *Time series momentum*. Author-affiliated research summary: https://www.aqr.com/insights/research/journal-article/time-series-momentum . DOI https://doi.org/10.1016/j.jfineco.2011.11.003 . Research concerns the stated futures/forward population, not a deployment result for this product.
- [QS5] Daniel, K. & Moskowitz, T. J. (2016), *Momentum crashes*. Author-faculty-hosted article PDF: https://spinup-000d1a-wp-offload-media.s3.amazonaws.com/faculty/wp-content/uploads/sites/3/2019/09/Mom_crashes_JFE_final.pdf . DOI https://doi.org/10.1016/j.jfineco.2015.12.002 . Used here for the existence and conditions of a failure mode, not to transplant its proposed dynamic strategy.
- [QS6] Ma, T., Liao, C. & Jiang, F. (2024), *Factor momentum in the Chinese stock market*. Journal of Empirical Finance 75, 101458. Publisher abstract retrieved through search; direct full-page open returned 403: https://www.sciencedirect.com/science/article/abs/pii/S0927539823001251 . DOI https://doi.org/10.1016/j.jempfin.2023.101458 . Limited to evidence of market-specific empirical questions; no full replication or audit performed.
- [QS7] S&P Dow Jones Indices/MSCI, *Global Industry Classification Standard Methodology*, October 2026: https://www.spglobal.com/spdji/en/documents/methodologies/methodology-gics.pdf . Relevant sections: methodology, hierarchy, classification review and structure changes.
- [QS8] Hang Seng Indexes, *Index Operation Guide*, November 2026 version 3.29, section 7 HSICS: https://www.hsi.com.hk/content/dam/wpb/hsil/index_operation/en_hk/index_operation_guide.pdf . Classification overview: https://origin-www.hsi.com.hk/eng/our-services/hsics . Use dated exact provider versions for implementation.
- [QS9] HKEX, *Quotation Requirements and Restrictions for Shanghai Connect Orders*, reviewed page states effective 6 July 2026: https://www.hkex.com.hk/Mutual-Market/Stock-Connect/Reference-Materials/Rules-and-Regulations/Quotation-Requirements-and-Restrictions-for-Shanghai-Connect-Orders?sc_lang=en . Analogous Shenzhen route: https://www.hkex.com.hk/Mutual-Market/Stock-Connect/Reference-Materials/Rules-and-Regulations/Quotation-Requirements-and-Restrictions-for-Shenzhen-Connect-Orders?sc_lang=en . Actual admissibility remains instrument/channel/date-specific.
- [QS10] HKEX, *Trading Hour, Trading and Settlement Calendar*: https://www.hkex.com.hk/mutual-market/stock-connect/reference-materials/trading-hour%2C-trading-and-settlement-calendar?sc_lang=en . The current page links the 2026 trading and Northbound settlement calendars; consume actual dated owner schedules rather than a universal weekday rule.

## 9. Verdict

**Architecture recommendation: adopt now.** Deep market/sector/security context, source coherence, navigation, preserved original context and explicit benchmark participation are justified product requirements.

**Predictive/economic verdict: promising hypotheses requiring qualification.** The reviewed literature motivates sector-aware research and supplies important failure cases. It does not prove Prophet's beta capture, alpha, pivot forecasts, remaining upside, deliberate company-news timing or cross-market portability. The implementation package should preserve these as concrete, measurable obligations under the existing Q programme, not as claimed capabilities or indefinite optional research.
