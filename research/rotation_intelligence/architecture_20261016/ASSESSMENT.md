# Mastermind rotation intelligence: census, research assessment, and target architecture

**Assessment date:** October 16, 2026  
**Scope:** Sector, industry, subsector and thematic rotation; regime and capital-cycle conditioning; sector beta, stock-level alpha, and the cash alternative.  
**Disposition:** Research/design assessment completed. The broader predictive allocation capability remains unqualified; this report does not authorize trades, new scoring authority, or production release.

## Executive assessment

**Mastermind has a substantial measurement architecture, but the evidence does not yet qualify it to make the precise, continuously adaptive allocation decisions in the Chairman's north star.** This is not a greenfield research problem, and another collection of oscillators or a new rotation dashboard is not the highest-leverage response.

Three corrections to the starting assumptions matter immediately. First, **US sector and subsector T2 confluence already exists**, alongside synthetic equal-weight member charts. Second, **US sector ETF creation/redemption estimates exist**; an older internal audit describing that layer as absent has been superseded. Third, the latest Leadership Rotation programme receipt explicitly distinguishes a delivered measured product from an **unqualified predictive capability**. It reports the measured product complete, while retaining scientific and original-programme obligations. [I1–I4]

The architecture needs a qualified path from observation to decision:

> What changed → why it may matter → what is likely over a specified horizon → whether the opportunity is better than the alternatives after costs → how much risk the mandate permits → which instruments best express it.

A movement in relative strength is an observation. An ETF creation is a primary-market fund event. A rising analyst estimate is a fundamental revision. None is automatically a forecast, a causal investor-to-investor capital transfer, or a portfolio instruction.

The right research target is not an unsupported promise of a single correct sector at every moment. It is a system that **improves the probability and economic value of selecting the right exposures, detects changes with an explicitly measured delay/false-alarm trade-off, and abstains when evidence is insufficient**. Precision must be evaluated at an actionable horizon and net of turnover, not judged by an attractive retrospective turning-point chart.

## 1. Census scope and evidence standard

The census examined the Macro repository's engine, collectors, configuration, research, scripts, templates and tests; current Mastermind core rotation/perception evidence; and the latest cross-repository programme delivery records. The filename inventory contained 242 rotation-related matches. **That is a search result count, not a count of independent features, validated models, or live capabilities.** Two bounded read-only Fabric workers extracted implementation and research facts. Their returns were reviewed rather than accepted wholesale; historical-to-current overstatements and inaccurate numerical summaries were excluded.

### Immutable source anchors

| Surface | Observed reference | Interpretation |
|---|---|---|
| Mastermind protected procedure and core source | `50107c31531d3b4ab5a18b5acf5e77954a0549e3` | Governing Skillpack and core-source census pin |
| Macro `main` | `460e301502674cfe9a4002faae1034a5a6d666a3` | Implementation/research census pin |
| Terminal `master` | `b9282f74e4af8d3e7d44709fd6381a6825fd9d7b` | Observed repository head; not itself a production attestation |
| Leadership Rotation programme receipt | Mastermind #1194, comment `6180067004`, October 14, 2026 | Current owner-reported separation of delivered measurement and unqualified prediction |

Seven Macro subtree inventories were non-truncated: collectors 325 files, configuration 171, engine 1,976, research 7,623, scripts 1,541, templates 473 and tests 4,626. The assessment then narrowed to the relevant producers, contracts, consumers, and scientific records rather than treating every matching file as evidence.

**What this assessment does not claim:** a new market-data backtest, a fresh full test-suite run, authenticated production/browser verification, universal current feed entitlement, or inspection of every deployed instance. A supplementary bulk source-read request was refused before dispatch and was not retried through a different carrier. Conclusions below rely on successful source reads and independently retrieved programme records, not on a claim that the refused snapshot succeeded.

## 2. What already exists—and what each component actually proves

| Capability | Existing implementation/evidence | Assessment |
|---|---|---|
| US sector/subsector confluence | `subsector_confluence`, `signal_gate`, `sector_signals`, `basket_index` | Implemented descriptive timing/context; constituent-history and out-of-domain limitations prevent automatic investment qualification. |
| China sector/concept cycles | `china_sector_cycles`, `china_sector_rotation`, `subsector_rotation_china`; shared confluence adapters | Implemented counterparts, but different universes, benchmarks and source conventions. US–China statistical equivalence is not established. |
| Relative leadership and rotation | `subsector_rotation`, `rotation_events`, `rotation_velocity`, `leadership_rotation_context`; core `rotation_tensor` | Measurement architecture exists. Pairwise leadership is not proof of causally transferred dollars or incremental forecasting skill. |
| Intraday/session-aware observations | Recent Macro rotation work and Leadership Rotation measured-product delivery | Do not describe the entire product as end-of-day only. The confluence path is daily; newer session-aware measurement is separate. This audit did not reproduce normal production latency. |
| ETF creation/redemption estimates | `etf_flows` delegates to `collectors.sponsors`; sector and broad-market stores | Built; explicitly display-data, not permitted to rank, gate or size. |
| Macro quads and continuous state | `regime`, `regime_one`, `quad_vector`, `regime_prior`, `regime_vector` | Reuse these owners. Distinguish causal filtered state from a smoothed display history. |
| Real-rate pressure | `regime_vector` uses DFII10 change over 63 sessions, risk context and hysteresis | Already present; richer conditioning is a validation/integration question, not a missing first real-rate indicator. |
| Breadth/concentration | `advanced_breadth`, `breadth_split`, `live_breadth`, ownership/theme crowding | Numerous observations exist. Many are deliberately display-only; signal promotion must be earned. |
| Fundamental/thematic foresight | `demand_chain`, `theme_activity`, `theme_revisions`, `foresight_cascade`, `foresight_score`, `foresight_earliness` | Valuable mechanism and evidence hierarchy; not equivalent to an expected-return model. |
| Forward evaluation | `foresight_grader`, `foresight_shadow`, cycle/rotation research and preregistration machinery | Reuse rather than create a second evaluation system. A grader's existence does not prove positive results. |
| Portfolio/risk context | `portfolio` and `foresight_sizing` | Cross-asset risk references and thematic posture/overlap controls exist. They are not proof of a qualified sector–theme–cash allocator. |

Sources: exact-source census and [I1–I12, I16–I20].

### US T2 and weighted charts: the direct answer

`engine/subsector_confluence.py` composes existing machinery across the US sector/subindustry universe. It explicitly describes the T1–T4 entry cascade, including **T2: 2-day MACD cross and 3-day StochRSI cross**, and combines a stock's own signal with its subsector's context. The engine also has basket, China-concept, Nasdaq and Russell confluence entry points. This is not China-only functionality. [I1]

The same file makes an essential disclosure: the US synthetic history uses **today's membership with `pit=False`**, is survivorship-tinted, and is a descriptive consolidated tape rather than an out-of-sample constituent-history backtest. Its multi-day aggregation convention can differ from a TradingView session anchor. SPDR-calibrated state base rates are deliberately not presented as validated probabilities for synthetic subindustries. These are material restrictions, not cosmetic caveats. [I1]

There should be two clearly separated uses of the chart service. A **current-composition analytical chart** answers how today's group behaves. A **point-in-time investment index** answers what a rule could have owned historically, with dated constituents, weights, corporate actions, rebalances and implementable costs. Both are useful; only the latter supports an honest historical portfolio test.

### A synthetic-candle problem worth testing

The basket builder correctly chains member returns rather than averaging unrelated dollar share prices. It also constructs weighted daily member highs and lows. [I10] Those extrema need not have occurred simultaneously.

For a deterministic counterexample, suppose two equal-weight stocks each open and close at 100. At one instant A=110 and B=90; later A=90 and B=110. The basket is 100 at those observations, but averaging the two individual daily highs produces 110 and averaging the lows produces 90. These are not demonstrated highs and lows of the investable basket.

This does **not** invalidate a close-based confluence signal. It does mean ATR, range, and money-flow calculations using those synthetic extremes need separate qualification. The preferred production solution is synchronized intraday portfolio marks, aggregated into real basket candles. Otherwise the display and downstream research must label the range construction as synthetic. Similarly, aggregate dollar turnover is traded activity, not net institutional inflow.

## 3. What the research supports—and what remains unproven

### Technical timing has some evidence, but the reported edge is modest

The sector-confluence research reports that a daily/3-day fresh-up combination, above the 200-day average and below its RSI cap, earned **0.87 percentage points of 63-day excess return versus SPY**, with a **53% hit rate** over **1,864 pooled signals**. The report describes a risk/rotation-timing map, not an alpha machine or a return forecast. It reports more consistent avoidance evidence than entry evidence. [I5]

These are reported historical results, not newly reproduced findings in this assessment. The raw signal count is not the number of independent opportunities: overlapping 63-day windows and correlated sectors can substantially reduce effective sample size. An investment qualification also needs next-executable fills, costs, alternative baselines, and a true point-in-time universe. Reusing an indicator definition is good engineering; it does not automatically transfer an ETF result to a small thematic basket.

### A delivered measured product is not a qualified predictive model

The October 14 Leadership Rotation receipt explicitly says the measured product is complete and reports merged Macro/Terminal repairs and deployment. It separately says **predictive capability is not qualified**; P1/P2/P3 real-data look counts are zero under the required scientific path, and P1 is withheld pending re-registration of the statistics. The original programme remains incomplete. Natural consumption, conditional issuance, operator/visual proof and the next preregistration remain distinct obligations. [I3]

This is the strongest current evidence against answering “yes, our architecture is already enough.” Conversely, it is evidence against claiming nothing has been built or all work is merely a plan.

### Preserve negative results instead of explaining them away

The core Rotation Tensor retains a failed historical promotion result. The associated metric-repair PR preserves that failure and says the corrected historical AUC is unknown, because the exact historical executable/data/score-vector bundle has not been recovered for requalification. A metric bug fix does not itself establish a predictive edge. [I4, I6]

Current ownership-crowding source also records that its earlier price-based crowded/extended construction did not show forward-return underperformance; its current lens remains hazard/de-escalation context. Foresight sizing source acknowledges weak detection evidence and implements display-only posture bands rather than point allocations. These are reasons to retain uncertainty and conduct discriminating tests, not reasons to wire all available data into a more persuasive composite. [I7, I8]

Older programme audits and retained studies contain additional null, underpowered and historical measurement findings. They are valuable hypotheses and repair history. They must not be presented as proof that every historical defect persists on today's source. Likewise, failed prediction of a market drawdown does not falsify a different question such as relative sector ranking; each target requires its own test.

## 4. What institutional practice contributes

Public research describes methods, not a complete view of proprietary hedge-fund books. There is no single institutional sector-rotation recipe.

**Business-cycle allocation:** Fidelity's framework uses recurring sector tendencies as context. Its mid-cycle discussion also illustrates the weakness of a deterministic sector calendar: leadership is mixed. The transferable idea is a conditional opportunity prior, not a rule that the same sector must win whenever a label appears. [E1]

**Macro sensitivity and valuation:** State Street studies sector/industry relationships with rates, inflation expectations, currency and oil. It emphasizes overlapping coefficient uncertainty, limited observations in some curve regimes, and explicitly cautions against using the relationships alone as rotation signals. Some relationships are contemporaneous sensitivities, not forecasts. [E2]

**Systematic industry and stock selection:** Moskowitz and Grinblatt's industry-momentum work supports testing industry selection separately from stock selection. Residual-momentum research demonstrates a way to distinguish stock-specific persistence from broad factor exposure. Neither establishes intraday pivot accuracy. [E3, E4]

**Capital-cycle investing:** Marathon London's framework focuses on returns on capital, competition, capacity investment and management capital allocation. Attractive demand is insufficient when expanding supply destroys future profitability; conversely, capacity withdrawal can improve an industry's future economics before the reported earnings recover. [E5]

**Portfolio construction:** Institutional risk work separates signal selection from portfolio exposure, concentration, overlap and execution. A good sector thesis can still be an unattractive trade if it duplicates existing risks, is crowded, or requires costly turnover. Momentum also needs rebound stress tests rather than an assumption that yesterday's winners always remain tomorrow's leaders. [E6, E7]

The practical synthesis is therefore: economic mechanism and expectations; observable confirmation; relative opportunity; portfolio risk; and explicit exit/invalidation. Mastermind should borrow this decision discipline, not copy any firm's proprietary signals or presume that adding an institutional label qualifies a model.

## 5. How to track sector funds rotation honestly

### Separate four evidence categories

**Observed fund events.** ETF creations/redemptions and reported fund subscriptions/redemptions are genuine observations at the fund level. ETF secondary-market turnover is a different activity; a large volume of ETF trading need not create new shares, and primary-market creation can be in kind. [E8]

**Reported allocator holdings.** Filings can reveal persistent positions or active-weight changes, but they arrive late and incompletely describe an investor's full book. Form 13F is generally due within 45 days of quarter-end. N-PORT is another delayed holdings source; ingestion must follow actual availability and applicable disclosure rules rather than assuming a uniform real-time feed. [E9, E10]

**Trading and positioning proxies.** Relative strength, dollar turnover, signed volume, options premiums, gamma estimates and price-derived cross-border “flow” are observations or estimates of different mechanisms. They are not interchangeable with cash subscriptions or an identified institution's equity purchases.

**Inferred migration.** A statement that sector B is gaining leadership while A weakens is supportable from prices. A statement that the same dollars left A and entered B requires linked investor-level evidence. Aggregate sector market values are not a conserved flow ledger.

### The existing ETF layer should be extended, not replaced

The current sector module already delegates to the canonical sponsor collector. The natural extension is a quality-controlled, source-clocked look-through table, with direct and inferred observations kept separate. [I2]

A simplified ETF creation-equivalent calculation is:

`fund_flow[t] ≈ NAV[t] × (shares_outstanding[t] − split_adjusted_shares_outstanding[t−1])`

For broader funds, an attributable sector estimate is:

`sector_flow_estimate[s,t] = Σ fund_flow[f,t] × latest_known_sector_weight[f,s,t]`

The second equation estimates where fund-level activity maps under the latest known portfolio weights; it does not prove same-day underlying stock purchases. EPFR's published sector methodology similarly combines fund flows with sector allocation information of a different frequency. This mixed clock must be visible. [E11]

Proposed quality controls include issuer observation date, first available date, rounding/precision when shares are derived from AUM/NAV, splits and fund reorganizations, stale holdings, broad-fund versus sector-fund decomposition, fund-of-funds duplication, and genuine large creations versus corporate-action jumps. Normalize by appropriate lagged assets or liquidity, not merely raw dollars. Separate passive market-wide subscriptions from discretionary sector overweights.

The scientific question is **incremental information**: after recent returns, volatility, earnings revisions and the known market flow are controlled for, do these observations improve future sector ranking or downside estimation? A useful coverage gain is not automatically an alpha gain.

## 6. Regimes, rates, breadth and industry cycles

### Use the existing regime owner, but expose a richer state vector

Mastermind already has a common regime prior and a rate-pressure component. The shared prior explicitly preserves source dates and restricts certain components to display-only while their point-in-time history accrues. The proposed work should consume those owners and their qualification states, not create a second macro classifier. [I9, I11]

For allocation research, keep the following concepts distinct: growth level, direction, acceleration and surprise; inflation level, breadth, direction and surprise; real and nominal yield levels and changes; curve shape and the cause of its change; credit conditions; liquidity; and the market's prior expectations. A quad label must never silently substitute one of these definitions for another.

Real yields are especially important as a conditioning variable, but TIPS yields and breakevens contain premium/liquidity effects as well as expectations. The model should not call breakeven inflation a pure forecast, nor count the same yield move several times under differently named features. [E12]

Macro data must be reconstructed as known at each decision time. ALFRED and FRED real-time periods distinguish historical vintages from today's revised history. A model trained on a revised series and scored against an old release date can appear earlier than any investor could have been. [E13]

### A regime playbook should generate candidates, not automatic allocations

The following are **proposed scenario hypotheses**, not a calibrated mapping or a current recommendation. They are motivated by the institutional frameworks above, but require Mastermind-specific tests.

| Environment | Candidate opportunity set to investigate | What must distinguish a real opportunity from a trap |
|---|---|---|
| Improving growth, easing inflation pressure, benign financing, broad participation | Multiple cyclical and quality-growth industries | Earnings breadth and financing conditions must support more than a few index heavyweights. |
| Similar macro backdrop but narrow participation and concentrated earnings | Specific industries or themes rather than whole sectors | Look-through overlap, ex-leader breadth, liquidity and valuation must justify selectivity. Narrow breadth alone does not justify more risk. |
| Reflation with improving orders and manageable real-rate pressure | Selected industrial, resource and financial exposures | Distinguish demand-led reflation from margin-destroying input inflation and adverse funding costs. |
| Growth weakens while inflation or real-rate pressure rises | Pricing-power exceptions, selected resource exposures, or a larger cash alternative | A sector can benefit from one macro axis and be hurt by another; absolute downside matters. |
| Growth slows, inflation eases, yields fall, credit remains contained | Quality defensives and selected duration-sensitive exposures | Falling rates can reflect either beneficial relief or worsening earnings/credit risk. |
| Credit deterioration and broad liquidation | Treasury bills as a serious competitor to all equity sectors | A defensive sector's relative win may still be an unacceptable absolute loss. |
| Recovery transition with improving credit and broadening participation | Emerging cyclical/industry leaders | Test rebound behavior; the prior winner list and a slow macro label can lag the transition. |

### Breadth should govern both interpretation and granularity

A broad sector chart should be accompanied by an equal-weight view, an ex-largest-members view, constituent contribution, participation above relevant trends, the distribution of member relative strength, new highs/lows, and earnings-revision breadth. These views answer different questions. They should not be merged into one “breadth score” before redundancy and predictive contribution are tested.

The key architectural split is **risk budget versus opportunity concentration**. A narrow market can contain a strong subsector opportunity while the correct total equity risk is lower. Conversely, expanding participation can justify a broader opportunity set without proving that every laggard deserves capital. Measure effective independent bets across overlapping themes; five labels can still describe one underlying position cluster.

### A sector's fundamental cycle is not its price oscillator

Within the existing thematic/demand architecture, evaluate industry-specific leading quantities: new orders relative to inventories, backlog conversion and cancellations, capacity utilization, pricing and discounts, capital expenditure relative to future demand, competing capacity additions, financing availability, and returns on invested capital.

Treat these as separate clocks: **industry supply cycle, company earnings cycle, macro cycle, and market-pricing cycle**. An industry's profits can still be rising while its stocks peak because the marginal outlook is deteriorating relative to expectations. A weak reported quarter can coincide with a price turn when capacity exits and order declines stop worsening. These are research mechanisms, not permission to manufacture forward estimates from narrative alone.

## 7. Selecting the next sector or theme, and detecting pivots

### Separate continuation and transition

A leader-continuation model asks whether established relative strength is likely to persist. A transition model asks whether a challenger is improving before it dominates the usual rankings. Combining them indiscriminately can either chase late strength or perpetually buy weak laggards.

The proposed system should maintain an observable challenger set, with the source and reason for entry recorded. A candidate may first appear through improving relative-return slope, stabilizing internal breadth, an earnings/industry catalyst, or more persistent observed fund demand. It need not wait for every slow regime and technical gate to turn green. But early observation does not grant full conviction: contrary macro evidence and poor data coverage must remain visible.

### Pivot zones, not hindsight turning-point labels

An actionable transition can be represented in stages: formation, confirmation, persistence and invalidation. The early stage needs a measurable false-alarm rate; confirmation has a measurable delay; persistence requires a testable holding policy; invalidation must specify what would change the decision.

Online change-point methods are candidates for detecting altered behavior, not evidence of a market edge by themselves. Benchmark them against simpler causal thresholds and existing event logic. Never use a hindsight peak/trough timestamp as though it were a signal available on that date. [E14]

Keep slow fundamental/regime evidence separate from intermediate leadership and fast execution timing. Session-aware measurement must distinguish overnight, regular-session and aligned intraday comparisons. A five-minute analytical interval is not a five-minute-fresh signal if the source arrives later. Publication time, observation time and first availability must remain separate all the way to the UI.

### An explicit horizon-specific decision object

Extend the existing measured contract rather than create a separate intelligence plane. A proposed forecast/decision record should carry:

- Group identity and point-in-time membership/weight version; instrument expression and benchmark.
- Decision horizon; observation and availability clocks; source coverage and freshness.
- Expected return relative to both the equity benchmark and Treasury bills, with uncertainty and calibration state.
- Probability of outperforming or entering the top group, downside/tail estimate, and rank uncertainty.
- Evidence for and against the thesis, invalidation conditions, crowding/overlap, liquidity and expected execution cost.
- Qualification state and allowed use: descriptive, research-only, or independently qualified for a specific decision.

A 0–100 rubric is not a probability. “The next best sector” can legitimately be a small set whose expected outcomes are statistically indistinguishable; the system should not invent a precise order just because a UI requires one.

## 8. Sector beta, stock alpha, and cash

### Three decisions—not one score

**Total risk:** Is equity exposure attractive relative to the feasible defensive alternatives under the mandate?

**Group selection:** Which sectors, subsectors or themes offer the best expected opportunity at the stated horizon and risk budget?

**Instrument/stock selection:** Does a stock basket add value beyond simply owning the chosen sector or industry exposure?

The user's sector-first workflow is a sensible research structure, but its stock layer must demonstrate residual contribution. Attribution should separate market exposure, sector/theme exposure, style factors and remaining stock-specific return. A high-beta stock in a rising sector is not automatically an alpha discovery. Fundamental revisions, earnings quality, cash generation, valuation relative to expectations, customer-chain capture and stock-versus-industry strength are candidate stock-level inputs. [E3, E4]

### Cash is an investable competitor, not an afterthought

Use an actual historical Treasury-bill total-return series in the evaluation, including the appropriate yield and implementation assumptions. Do not compare an equity strategy to zero-return cash by default. Do not substitute long-duration Treasuries for bills: that introduces a separate rate-risk decision.

The allocation policy should permit reduced risk or cash when estimated net opportunity is weak, confidence is low, or tail/liquidity constraints bind. It should not force a switch from a bad growth sector into a less-bad defensive sector simply to remain fully invested.

Risk weights must come from a qualified portfolio policy with uncertainty, covariance, concentration, liquidity and turnover controls—not free-form model-generated trade sizing. No-trade bands and hysteresis should be tested for economic value, not added until the resulting curve looks smooth. This report proposes no actual account weights or trades.

## 9. Research programme that could qualify the capability

### Start with the existing scientific blocker

The current Leadership Rotation disposition makes the next research dependency unusually clear: **repair and re-register the estimands/statistics and establish usable power through the existing LR-W6/V3 path before treating real-data outcomes as confirmatory evidence.** No new evaluation database, event owner, programme identity or score authority is required. [I3]

In parallel, the point-in-time sector-ranking baseline and cost/cash accounting can be specified and prepared within the existing evaluation owners. Receiver-only models must be explicit comparators: a sender-to-receiver story earns a role only when it improves on identifying the improving receiver alone.

### A small set of discriminating hypotheses

| Hypothesis | Minimum comparator | What would justify further investment |
|---|---|---|
| Fund-flow information adds useful forward information | Price/momentum, volatility, earnings revisions and broad-market flows | Incremental out-of-sample ranking or downside improvement after costs, not merely same-day correlation. |
| Regime conditioning improves group selection | The identical unconditioned ranker | Better net utility or calibration across held-out regimes without an explosion in unstable cells. |
| Breadth changes reveal early transitions | Group returns, volatility and concentration alone | Earlier useful observations with a tolerable false-alarm/cost trade-off. |
| Industry/capital-cycle evidence adds information | Price plus macro baseline | Improvement beyond what prices and earnings revisions already reveal. |
| Finer-grain selection beats broad-sector exposure | Sector ETF and equal-weight alternatives | Incremental value after liquidity, constituent overlap and implementation costs. |
| A pivot model improves economic decisions | Existing threshold/event logic and receiver-only baseline | Captured opportunity and reduced regret, not just an earlier retrospective timestamp. |
| Stock selection adds alpha within chosen groups | The corresponding sector/industry basket | Residual contribution after beta/style and costs, robust across periods. |

### Data and experimental requirements

Use dated constituents and weights; delistings and corporate actions; true ETF inception and sector-taxonomy changes; earnings-estimate vintages; actual filing/release availability; separate price and total-return conventions; local calendars and time zones; and independently observable source coverage. Revised macro history and current-membership backfills cannot stand in for point-in-time data.

Evaluate rolling or expanding walk-forward models with truly held-out periods. Purge/embargo overlapping labels where required, cluster errors by shared market episode and date, and use a resampling scheme that preserves dependence. Eleven sectors observed on the same day are not eleven independent macro experiments. Rare regime cells need partial pooling or abstention, not precise estimates from a handful of transitions.

The baseline set should include broad-market buy-and-hold, equal-weight sectors, simple relative momentum, an absolute-trend/cash alternative, macro-only, price-only, and the combined model. Reproduce results at the next actually executable price and stress transaction costs and turnover. Include prospective source-clocked shadow observations before granting production decision authority.

Multiplicity must be controlled across the declared hypothesis family, not hidden by choosing the most attractive horizon, sector, threshold or backtest start date. The factor-discovery literature shows why conventional isolated significance tests become misleading after extensive searching. [E15]

Judge success by more than hit rate: top-group excess return and rank correlation; calibration of probabilities and intervals; net return, downside and turnover; transition delay and false alarms; opportunity regret versus a simple baseline and bills; and residual stock contribution. Keep observations, forecasts and actions in distinct logs under existing owners, so evaluation can identify whether an error came from data, prediction, selection or execution.

## 10. Priorities and acceptance gates

### Priority 1 — Finish measurement and evidence truth

Reconcile the existing measured-product delivery with normal-source observation, consumer and signed-in visual proof. Bind point-in-time membership, price/return basis, source clocks and metric revisions. Display what is observed, inferred, stale or unqualified. Preserve source ownership and current release protections.

**Acceptance:** an exact, reproducible observation can be traced from source availability through the actual consumer without acquiring an unjustified probability, freshness claim or trading authority.

### Priority 2 — Qualify the scientific target and baseline

Advance the existing LR-W6/V3 statistical work; separate measurement, prediction and policy estimands. Establish receiver-only/simple-ranker and Treasury-bill baselines. Predeclare candidate horizons and what constitutes economically useful improvement.

**Acceptance:** the test is correctly sized and meaningfully powered for its declared target, and the baseline can be reproduced on an investable, point-in-time universe.

### Priority 3 — Add independent information, not more correlated indicators

Improve existing flow look-through and allocator-position evidence; earnings-revision breadth; industry/capital-cycle observations; and exposure-overlap measurement. Each addition must resolve a named missing decision input and pass an incremental-information test.

**Acceptance:** data quality and availability are established, and the new input improves a held-out decision or uncertainty estimate beyond the existing baseline.

### Priority 4 — Qualify the sector/theme/cash policy, then the stock-alpha layer

Select exposures at the appropriate granularity with total-risk, overlap and liquidity constraints. Evaluate the stock layer against the chosen group basket. Keep uncertainty-aware abstention and no-trade behavior as valid outputs.

**Acceptance:** net-of-cost out-of-sample and prospective performance satisfy a predeclared mandate; failures and weak-support regimes remain visible rather than being retuned away.

### Priority 5 — Make the existing product answer the allocation question

Extend Sector Intelligence / Rotation Command / Terminal with a decision view: current leaders, emerging challengers, weakening groups, cash comparison, horizon, evidence clocks, uncertainty, confirmation and invalidation conditions, and instrument choices. Reuse existing contracts and intelligence owners; do not build a parallel dashboard with independent truth.

**Acceptance:** a user can distinguish “this group is strengthening” from “this forecast has earned decision authority,” see why a candidate changed, and understand when no allocation edge is supported.

## Final judgment

The architecture is **strong enough to extend, but not yet sufficient to claim the requested allocation precision**. Its strongest assets are existing measured contracts, multiple levels of market granularity, thematic economic mechanisms, and an unusually explicit record of negative and unqualified findings. Its central weakness is the gap between abundant observations and a demonstrated, cost-aware allocation policy.

The most valuable next step is not a new director, a new rotation score, or another oscillator. It is to complete the existing scientific qualification path and establish an honest point-in-time sector/industry ranking baseline with a cash alternative—then prove which independent information improves it. That creates a defensible path from getting the sector right to finding the alpha leaders, without confusing narrative plausibility, technical confirmation or shipped code with investment skill.

---

## Source register

Internal references below are pinned unless they are explicitly current owner records. Source prose describes its own claims; this report separately states the level of verification reached. URLs are included for reproducibility, not as permission to change the referenced work.

### Internal sources

[I1] Macro, `engine/subsector_confluence.py`, especially lines 1–41 and the named family entry points. https://github.com/mastermindx-market-intelligence/macro/blob/460e301502674cfe9a4002faae1034a5a6d666a3/engine/subsector_confluence.py

[I2] Macro, `engine/etf_flows.py`, lines 1–80. https://github.com/mastermindx-market-intelligence/macro/blob/460e301502674cfe9a4002faae1034a5a6d666a3/engine/etf_flows.py

[I3] Leadership Rotation T26 owner receipt, October 14, 2026, comment 6180067004 on Mastermind #1194. https://github.com/mastermindx-market-intelligence/Mastermind/pull/1194#issuecomment-6180067004

[I4] Mastermind #1194, current metric-repair scope and preserved historical-evidence limitation; read October 16, 2026. https://github.com/mastermindx-market-intelligence/Mastermind/pull/1194

[I5] Macro, `research/SECTOR_CONFLUENCE.md`, especially lines 1–80. https://github.com/mastermindx-market-intelligence/macro/blob/460e301502674cfe9a4002faae1034a5a6d666a3/research/SECTOR_CONFLUENCE.md

[I6] Mastermind, retained Rotation Tensor validation. https://github.com/mastermindx-market-intelligence/Mastermind/blob/50107c31531d3b4ab5a18b5acf5e77954a0549e3/research/eyes/validation_runs/rotation_tensor_2026-07-02.md

[I7] Macro, `engine/ownership_crowding.py`, lines 1–45. https://github.com/mastermindx-market-intelligence/macro/blob/460e301502674cfe9a4002faae1034a5a6d666a3/engine/ownership_crowding.py

[I8] Macro, `engine/foresight_sizing.py`, lines 1–54. https://github.com/mastermindx-market-intelligence/macro/blob/460e301502674cfe9a4002faae1034a5a6d666a3/engine/foresight_sizing.py

[I9] Macro, `engine/regime_prior.py`, lines 1–70. https://github.com/mastermindx-market-intelligence/macro/blob/460e301502674cfe9a4002faae1034a5a6d666a3/engine/regime_prior.py

[I10] Macro, `engine/basket_index.py`, especially `consolidated_candle`, lines 317–441. https://github.com/mastermindx-market-intelligence/macro/blob/460e301502674cfe9a4002faae1034a5a6d666a3/engine/basket_index.py

[I11] Macro, `engine/regime_vector.py`, rate-pressure functions, lines 148–223. https://github.com/mastermindx-market-intelligence/macro/blob/460e301502674cfe9a4002faae1034a5a6d666a3/engine/regime_vector.py

[I12] Macro, `engine/quad_vector.py`, published contract and causal probability owner. https://github.com/mastermindx-market-intelligence/macro/blob/460e301502674cfe9a4002faae1034a5a6d666a3/engine/quad_vector.py

[I13] Macro, historical institutional-sector problem audit. Its earlier US flow-gap claim is superseded by I2. https://github.com/mastermindx-market-intelligence/macro/blob/460e301502674cfe9a4002faae1034a5a6d666a3/research/INSTITUTIONAL_SECTOR_INTELLIGENCE_PROBLEM_AUDIT_FOR_FABLE.md

[I14] Macro, October 13 intraday/session research; explicitly points to a later continuation, so its initial delivery status is not treated as current. https://github.com/mastermindx-market-intelligence/macro/blob/460e301502674cfe9a4002faae1034a5a6d666a3/research/rotation_intelligence/intraday_sessions_20261013/RESEARCH_AND_IMPLEMENTATION.md

[I15] Macro, `engine/leadership_rotation_context.py`, existing stateless measured-product contract. https://github.com/mastermindx-market-intelligence/macro/blob/460e301502674cfe9a4002faae1034a5a6d666a3/engine/leadership_rotation_context.py

[I16] Macro, `engine/demand_chain.py`. https://github.com/mastermindx-market-intelligence/macro/blob/460e301502674cfe9a4002faae1034a5a6d666a3/engine/demand_chain.py

[I17] Macro, `engine/theme_revisions.py`. https://github.com/mastermindx-market-intelligence/macro/blob/460e301502674cfe9a4002faae1034a5a6d666a3/engine/theme_revisions.py

[I18] Macro, `engine/foresight_grader.py`. https://github.com/mastermindx-market-intelligence/macro/blob/460e301502674cfe9a4002faae1034a5a6d666a3/engine/foresight_grader.py

[I19] Macro, `engine/foresight_shadow.py`. https://github.com/mastermindx-market-intelligence/macro/blob/460e301502674cfe9a4002faae1034a5a6d666a3/engine/foresight_shadow.py

[I20] Macro, `engine/portfolio.py`, risk-budget reference rather than trade-list authority. https://github.com/mastermindx-market-intelligence/macro/blob/460e301502674cfe9a4002faae1034a5a6d666a3/engine/portfolio.py

### Primary institutional, regulatory and academic references

[E1] Fidelity, sector investing and the business-cycle framework. https://www.fidelity.com/viewpoints/investing-ideas/sector-investing

[E2] State Street Investment Management, “How macroeconomic variables impact sector performance”; analysis largely through 2022, not a current allocation forecast. https://www.ssga.com/us/en/institutional/insights/how-macroeconomic-variables-impact-sector-performance

[E3] Moskowitz and Grinblatt, “Do Industries Explain Momentum?” (1999), AQR research page. https://www.aqr.com/insights/research/journal-article/do-industries-explain-momentum

[E4] Robeco, residual momentum research overview (2013). https://www.robeco.com/en-latam/insights/2013/10/robecos-residual-momentum-less-risky-and-more-sustainable

[E5] Marathon London, “The Home of Capital Cycle Investing.” https://www.marathon.co.uk/the-home-of-capital-cycle-investing/

[E6] Man Group, “Applying Dynamic Risk Management.” https://www.man.com/insights/applying-dynamic-risk-management

[E7] Daniel and Moskowitz, “Momentum Crashes,” AQR research page. https://www.aqr.com/insights/research/journal-article/momentum-crashes

[E8] Investment Company Institute, ETF primary/secondary-market explanation. The historical trading-share statistic is not used as a current estimate. https://www.ici.org/viewpoints/view_14_etf_paper_01

[E9] US SEC, Form 13F frequently asked questions. https://www.sec.gov/rules-regulations/staff-guidance/frequently-asked-questions-about-form-13f

[E10] US SEC, Form N-PORT data sets. Actual filing/public availability controls ingestion; this report does not treat a proposed disclosure change as enacted. https://www.sec.gov/data-research/sec-markets-data/form-n-port-data-sets

[E11] EPFR, “Unlocking value in Japanese sectors,” methodology example combining fund flows and allocation weights. Vendor research is evidence of the method, not independent proof of strategy profitability. https://epfr.com/insights/quants-corner/unlocking-value-japanese-sectors/

[E12] Federal Reserve, “Tips from TIPS: The Informational Content of Treasury Inflation-Protected Security Prices” (2014). https://www.federalreserve.gov/pubs/feds/2014/201424/201424abs.html

[E13] Federal Reserve Bank of St. Louis, real-time periods / historical data vintages. https://fred.stlouisfed.org/docs/api/fred/realtime_period.html

[E14] Adams and MacKay, “Bayesian Online Changepoint Detection” (2007). Method candidate, not an established sector-trading result. https://arxiv.org/abs/0710.3742

[E15] Harvey, Liu and Zhu, “… and the Cross-Section of Expected Returns,” NBER Working Paper 20592. https://www.nber.org/papers/w20592

### Execution and recovery note

Research operation: `rotation-intelligence-census-20261016-sol-c1`. Source inventories and retained extracts are at `/Volumes/Mastermind/research/rotation-intelligence-census-20261016-sol-c1` on M2 Studio. Both read-only census workers are terminal; neither full return is granted blanket acceptance. Independently checked subsets and parent corrections are incorporated here. No active worker, watcher, trading action, source-code change, merge, deployment, credential change or effect-unknown modification is claimed.

This assessment does not take custody of #1194's metric repair, existing LR-W6/V3 work, Factor Atlas, or any adjacent source/publication carrier. The next research action belongs within those existing scopes and qualifications, not a replacement programme. The bounded assessment is complete; the broader predictive allocation programme is not.
