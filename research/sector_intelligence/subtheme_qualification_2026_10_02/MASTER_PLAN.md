# Mastermind granular leadership: integrated architecture and delivery plan

Date: October 2, 2026 (America/Los_Angeles)

Operation: `subtheme-takeover-replay-qualification-20261002-sol-001`.
Existing product parent: Macro #7749 / `WS:PROPHET-US-V4-RECOVERY`; existing repricing carrier: #7976. This document is a proposed integration and research plan, not a replacement workstream, approved model, source-custody transfer or production release.

Protected procedure pin: `Mastermind@bf1fa1db3147105e9ac3d4f7f4d20ef8efd59cba`, compatible Sol Skillpack 1.0.1 / bootstrap 1. Macro census pin: `e4910184b25c27eda95f81a09d3ce4a6f5d8535d`. Current implementation branch: `sol/subtheme-replay-qualification-20261002`.

## 1. Decision

Build a connected evidence-to-expectations-to-price-recognition workflow through existing owners. Do not build a new universal momentum/sentiment score, graph authority, candidate queue, claims ledger or publisher.

The useful end state is not simply a heatmap with smaller boxes. A user must be able to identify an economically coherent source of improving returns, see whether that improvement is already recognized in price, distinguish genuine cohort support from a single-stock move, find a qualified expression and entry, and understand the evidence that would change the position-management view. The machine must preserve identities, information availability, population definitions and decision authority across that entire path.

The immediate critical path is measurement reliability, not adding more alternative data. The existing rotation scorecard reports no proven forward edge, and its implementation has horizon, coverage and comparison defects. Connecting that score directly to Prophet would transmit uncertain measurements into a decision system. An offline qualification adapter has therefore been built first. It does not change the live ranker. [R01-R04]

The completed Deep Research report was not present in the accessible conversation/Library searches. The earlier launch receipt is not a completed research result. This plan uses the actual repository, prior supplied blueprint and primary research; it does not claim to consume an unseen report.

## 2. What the new investigation established

### 2.1 The existing evidence is weaker than the feature inventory implies

The committed scorecard is as of October 1, generated October 2 at 11:48 UTC. It contains 12,634 rows over 47 distinct observation dates. Every promotion flag is false; its own verdict is `measuring`. [R01]

| Legacy horizon label | Incumbent rank IC | Reported HAC t | Turn-engine rank IC | Incumbent / challenger graded rows |
|---|---:|---:|---:|---:|
| 5 | -0.0367 | -0.590 | -0.0488 | 12,051 / 6,700 |
| 10 | -0.0231 | -0.304 | -0.0541 | 10,979 / 5,628 |
| 21 | -0.0050 | -0.057 | -0.0362 | 9,907 / 4,556 |
| 63 | -0.0103 | -0.083 | unavailable | 5,351 / 0 |

These are existing producer-reported statistics, not newly recomputed returns. The labels are deliberately called legacy horizon labels: source code uses calendar-day arithmetic despite describing trading-day horizons. Negative estimates with these uncertainties do not establish a profitable inverse strategy. Different row populations make the displayed old/new difference an invalid paired strategy comparison. Forty-seven dates are not 12,634 independent experiments, and overlapping dates are not necessarily independent episodes. [R01-R02]

The existing emerging cohort reports average excess of -0.74%, -0.49% and -0.88% under the first three legacy labels, with respective positive-excess hit rates 42.3%, 45.3% and 43.8%. These are further reasons to withhold promotion, not grounds for a current trading recommendation. The source and selected-field transcription are included with this package. [R01]

### 2.2 Three source failures reproduced, plus one comparison-design failure

1. **Horizon mismatch.** September 25 plus five calendar days is September 30; the fifth following session in the explicit test calendar is October 2. Session-stamping the starting observation does not repair the future endpoint calculation.
2. **Population drift through missing outcomes.** The legacy basket routine averages available member returns once three are priceable. In an adversarial four-member fixture, three returns of +2% and one return of -20% give -3.5%; making the losing member unavailable changes the legacy reported mean to +2%. This proves a possible bias mechanism, not its prevalence in the live artifact.
3. **Iteration-dependent comparison headline.** The last eligible horizon overwrites the global `leader`. Reordering identical horizon results changes the headline winner. A per-horizon comparison should not become a global decision through dictionary iteration.
4. **Unpaired old/new comparison.** Source inspection and the actual artifact show the incumbent evaluated over all matured rows, while the challenger uses only rows carrying its newer score. Both must be re-evaluated on the same eligible observations before comparing them. [R02]

The reproductions are isolated semantic extracts of retrieved source expressions, not a full application import. Four regression tests preserve these discriminators. The original engine remains unchanged on this branch.

The prior research also identified unavailable z-score inputs becoming zero and then `leading` in the rotation engine. That prior finding remains a separate accepted investigation item; this turn has not measured current production incidence or repaired that engine. [R14]

### 2.3 An attractive shortcut has already failed a historical study

The August 3 Trend Intelligence masterplan reports a no-veto leader-reset study: 938 overlapping fires, median 21-session excess -1.50%, and per-name median -2.12%. The study is exploratory, in-sample and dependent; it is not new out-of-sample evidence. It nevertheless contradicts the shortcut of deleting anti-chase rules until recent winners become eligible. [R05]

Preserve the distinction between economic leadership and the eligibility of a particular entry construction. Test a materially different mechanism, not a renamed version of the rejected rule. Reopening a rejected family requires the existing decision owner and new discriminating evidence.

### 2.4 Better selection will not repair an intake loss by itself

The September conversion investigation identifies a latest-date Door observation view and mismatches between discovery observations and actionable episode requirements. Its selected historical generation had 35 flags: 8 exact receipts, 3 suppressions and 24 absent from that generation. Those figures are not a current overall loss rate; subsequent consumption and the chosen generation matter. They show why full funnel tracing is required. [R06]

Keep the sequence visible: observed opportunity -> received candidate -> valid episode -> scored population -> eligibility -> publication -> actual user visibility. Each missing stage requires a different repair. The research target is both decision quality and delivery integrity.

## 3. Census and disposition of existing work

This is a mission-focused census of the relevant intelligence, evaluation and consumer paths, not a claim to audit every unrelated Mastermind system. A source file, design, PR, merged implementation and production-proven feature remain distinct.

| Existing owner or asset | Evidence inspected | Disposition for this mission |
|---|---|---|
| GMI Theme Graph and company exposure | GMI masterplan, rights registry, established source-law boundaries | Reuse identities and evidence relationships. No fourth graph or fuzzy automatic canonical mapping. |
| Sector/theme/subtheme federation | September 20 architecture, prior research references | Preserve page-specific projections over shared owner facts; qualify actual integration separately. |
| Rotation and turn engines | Current builder, track-record implementation and artifact | Keep descriptive visibility; repair evaluation and missingness before predictive promotion. |
| Closed-session leadership, #7455 | Fresh API metadata: open, draft, unmerged; head `ebc7604b624adb8452041d8240f7cda41733f167` | Consume only after its own review, integration and ordinary-refresh proof; do not copy the engine. |
| Repricing/durability, #7976 | Fresh API metadata: open, draft, unmerged; head `0a6e4d7f518d3ab086da2b1aecfe0d5fa6dac6ff` | Existing breadth, revisions, earnings and leader-handoff implementation carrier. Integrate, do not fork. |
| Prophet R6 B09 | Existing peer/history qualification work card | Candidate-excluded peer evidence and membership/weight history remain its responsibility. |
| Prophet R6 B10 | Current work card | Existing Conditional Fusion/Evaluation comparison owner; no live champion change from this study. |
| Prophet strategy catalogue | September 30 catalogue | Retain distinct strategy families. Entry-episode identity is not a universal holding period. |
| Earnings read-through | August 16 mechanism/graph architecture | Adopt signed economic transmission and market-incorporation concepts; separate design from built status. |
| Research Vault | Existing searchable text, source/hash/metadata design | Extend source-grounded claim changes and source independence; do not create another corpus. |
| Attention/contagion and TIL | Existing GMI owner map and dispositions | Research additional predictive value through those owners; no new sentiment signal authority. |
| Calendar | Current `lib/nyse_calendar.py` | Reuse daily session arithmetic; its documented lack of early-close clocks must not become intraday clock truth. |
| Publication and consumer builders | `build_subsector_rotation.py`, daily workflow | Reuse collection/publication; do not do heavy graph/research computation in page rendering. |
| New offline qualification asset | This branch | Built and locally tested; source candidate only, not an accepted production grader or validated strategy. |

Sources: [R02-R13]. PR-body checkpoints can be older than the current API head; historical test counts in those bodies are not exact-head tests executed in this investigation.

## 4. North Star translated into observable acceptance

The full programme is complete only when the following user and machine journey works on the ordinary live path:

- Start at the market or an individual company, identify a relevant subtheme without requiring its entire parent sector to lead, and distinguish breadth from concentration.
- Drill into the actual economic mechanism and beneficiaries; see primary versus adjacent exposure, uncertainty, source timing and counterevidence.
- Compare current strength, emergence, thesis health, market recognition and entry quality without conflating them.
- Reach the complete relevant Prophet candidate cohort, including an understandable reason when a leader is not eligible or not scored.
- Examine an entry using qualified stock-specific timing and risk inputs, without buying a weak peer simply because the leader is extended.
- Observe how evidence, group leadership and stock-specific conditions change after entry; a stale entry trigger must not automatically mean a failed economic thesis.
- Inspect the same facts and dates in Sector Intelligence, GMI, Prophet and Terminal after a normal refresh, including stale, missing and correction cases.
- Any predictive claim has demonstrated incremental performance on its declared population/horizon, with independent scientific review and existing promotion approval.

This defines completion without promising perfect prediction. The actual optimization target is fewer costly selection and timing errors under realistic information and execution constraints.

## 5. Core architecture

### 5.1 A navigable hierarchy above an overlapping economic graph

The hierarchy is a user navigation aid: sector -> operating group -> theme -> subtheme -> company. Economic relationships are not a strict tree. Companies can participate in several products and end markets; a narrow subtheme can strengthen under a mixed sector; a customer transition can benefit one supplier and displace another.

Retain three distinct relation types already present in the earnings architecture: disclosed economic relationships; narrative/fundamental similarity; and residual market co-movement. They may inform a source-bound read-through view but must not be merged into an undifferentiated causal edge. [R07-R08]

Four objects remain separate: a source's membership claim, measured economic exposure, trading exposure, and a basket construction weight. Revenue percentages require supporting evidence; price correlation, mention counts and LLM judgment do not manufacture them. [R07]

### 5.2 Use the finest defensible resolution, not the finest possible resolution

A two-company component bottleneck can be economically real but statistically fragile. It may deserve a semantic page and watch condition without a calibrated group forecast. Conversely, a 40-company label may be too heterogeneous to guide selection.

For each proposed split, ask whether it adds economic coherence, distinct historical responses, reliable measurement, and an actionable distinction after uncertainty and turnover. Compare its incremental out-of-sample value with the coarser parent. Taxonomy creation itself is a research choice and belongs inside the multiple-testing budget.

Do not add unrelated members to satisfy a breadth floor, or create a price basket for every new concept. Semantic-only, measurable and forecast-qualified are different states. GMI already recognizes separate local, measurable, canonical and microtheme planes. [R07]

### 5.3 Orthogonal dimensions, not a new lifecycle

Compose existing owner dimensions:

| Dimension | Question | Examples of valid disagreement |
|---|---|---|
| Economic thesis | Is the underlying mechanism improving? | Demand improves while margins are uncertain. |
| Expectations | Is evidence better or worse than what was expected? | Strong growth merely meets high expectations. |
| Price recognition | Has the market already recognized the improvement? | Good evidence but extended price. |
| Cohort support | Is the move shared and persistent? | Strong index return driven by one issuer. |
| Stock expression | Is this company a credible beneficiary? | Relevant product but immaterial exposure. |
| Entry/risk | Is this specific execution acceptable? | Strong thesis with no clean entry. |
| Evidence quality | How reliable and fresh is the read? | Price current, estimates stale, supplier link unconfirmed. |

These are views over existing owners, not seven new state machines. GMI remains descriptive; it does not acquire ranking or candidate-origination rights through this design. Prophet's accepted research and decision owners remain separate. [R07,R10]

### 5.4 The consumer contract

Bind every view to stable issuer/security/group identity, taxonomy and membership vintage, source version, observation and known time, correction state, measurement coverage, relevant market session, and permitted consumer uses. Use the existing contract field names and authority checks in implementation rather than treating this conceptual grammar as a new wire protocol.

A source-backed fact, an extracted claim, a curated relationship, a research hypothesis, and a calibrated forecast must remain distinguishable. Confidence in extraction is not probability of a profitable trade.

The same material observation must not produce independent confirmations by appearing in a press release, a broker note, a social repost and an AI summary. Preserve the original event/source cluster through the existing evidence pipeline.

## 6. The anticipation mechanism

### 6.1 Economics before keywords

The research chain is: customer or technology change -> specific exposure -> incremental revenue/cost/capital effects -> difference from expectations -> recognition by independent sources -> stock and peer response.

A demand increase is not necessarily a profit increase. Test supply constraints, yields, utilization, price erosion, competition, customer bargaining power, qualification lags, substitutes, capacity spending and working capital. Signed transmission matters: one firm's positive event may represent another firm's loss of share.

A useful read-through records what would have to happen, over what horizon, and what observable fact would change the interpretation. It does not automatically transfer a positive stock reaction to every neighbor.

Economic-link research provides historical support for testing delayed customer-supplier information incorporation. It does not prove a persistent exploitable delay in today's optical stocks. [P02]

### 6.2 The expectations and recognition gap

Measure changes in fundamentals separately from levels. A fast-growing business can disappoint if expectations were still higher; a previously weak business can reprice if deterioration slows more than expected. Actual results, prior guidance, current guidance and analyst consensus are separate series and clocks. Missing consensus stays unknown.

Novy-Marx's historical earnings-momentum study motivates prioritizing earnings surprises and revisions over a large menu of price indicators. That finding is a research prior, not a universal declaration that price has no information in every market or horizon. [P03]

### 6.3 Continuous leadership versus event jumps

Two groups can have the same trailing return but very different paths: steady peer-supported progress, a single earnings gap, or repeated reversals. Evaluate jump concentration, positive-return persistence, pullback recovery, downside-relative behavior and breadth transitions as distinct features rather than treating acceleration as sufficient.

The continuous-information research found different continuation outcomes for gradual versus discrete information in its historical setting. Its monthly-horizon evidence does not validate an intraday entry rule. A genuine earnings repricing can still deserve a separate event family; the lesson is to distinguish mechanisms, not ban jumps. [P04]

### 6.4 Residual information without deleting the desired exposure

Maintain separate measurements of market-relative, parent-relative and peer-relative performance. Residual momentum research motivates controls for common factor exposures. But subtracting the very subtheme return we want to capture can erase the economically relevant group effect. [P05]

For group selection, test group performance relative to the market and appropriate parent. For selecting a beneficiary within that group, test issuer-excluded peer support and stock-specific excess. Include matched volatility/liquidity/exposure baselines so a high-beta basket does not masquerade as superior intelligence.

### 6.5 Capital rotation is not automatically zero-sum

The user's scarce-capital interpretation is a hypothesis to test, not a permanent market fact. Distinguish a fixed budget moving between technologies from aggregate spending broadening, and a common macro repricing from specific economic improvement. Regime dimensions should include dispersion, concentration, liquidity/volatility and fundamental revision breadth through existing owners, not a new universal risk-on/risk-off label.

Momentum crash research is a warning about regime dependence and particular portfolio constructions, not proof that every long-only leader portfolio has the same risk. Compare actual downside and recovery behavior under the intended implementation. [P06]

## 7. Research Vault, attention and institutional evidence

### 7.1 Convert the Vault into source-grounded change intelligence

Reuse its existing text, hashes, metadata and access controls. Add analyses through the incumbent evidence owners that distinguish new coverage, changed estimates, revised assumptions, stronger operating specificity, resolved objections and fresh counterevidence. This is not another document corpus. [R09]

Normalize report activity within a stable publisher/desk panel. Track coverage changes in the ingestion system itself. New feeds, duplicate uploads and delayed batches must not appear as new market interest. Compare current versus prior versions, retain original spans, and use the first-known time at each decision.

Exclude platform-generated reports and their derivatives from independent corroboration of the platform's own hypothesis. Otherwise an idea can create a report, the report can create more keyword counts, and the system can incorrectly interpret its own output as confirmation.

### 7.2 Social and search are conditional inputs

Test attention novelty, independent-author breadth, diffusion among distinct source clusters and product-specific discussion after controlling for prior returns, volatility and known events. Activity preceding recognition differs from a crowd reacting to an already extended move. A monotonic 'more bullish mentions is better' rule is not justified by this plan.

X, Stocktwits and Google Trends are optional research legs, not critical dependencies for the first useful release. Current entitlements, rights, latency and source retention must be verified before ingestion or model use. An API refresh time must not be presented as the underlying event's time.

### 7.3 Separate holdings, transactions and inferred pressure

Holdings disclosures, ETF creations/redemptions, quote-signed trades, options activity, social attention and price/volume participation measure different things. Preserve the reporting lag and coverage of each. Neither a large trade nor an options premium print identifies a buyer as an institution or proves opening intent.

Do not manufacture a real-time institutional-inflow score from proxies. A qualified proxy can support a bounded inference labeled as such; direct participant claims require direct supporting data.

### 7.4 Rights are a first-release design input

At the inspected registry, house-curated content is admitted, while Finviz/THS rights remain unresolved for new GMI public emissions. Existing named owner surfaces have a narrow grandfathered treatment; that does not authorize a new product derivative. First release should prefer qualified house-owned semantics while unresolved uses remain internal. Possession of third-party research is not itself model-use or redistribution permission. [R11]

## 8. Prophet, entry and portfolio integration

### 8.1 Preserve and trace the opportunity population

A candidate should have an auditable stage transition and reason when it is excluded, deferred, not scored, not published or not visible. A presentation cap is not evidence of weakness. Candidate visibility and live trade eligibility remain separate.

The historical conversion findings imply that lossless intake and qualified episode identity are as important as improved selection. Do not invent a reset anchor to make an emerging observation fit an incompatible entry schema. The incumbent episode owner must admit the actual mechanism or display it honestly as not yet actionable. [R06]

### 8.2 Separate entry species and holding thesis

Preserve the September 30 strategy catalogue. Early leadership is one sleeve, alongside cyclical and earnings/expectations work; policy/event, dislocation, liquidity, range and defensive research remain distinct candidate families. This programme does not flatten them into one hold period. In particular, a two-to-fifteen-session entry identity is not a two-to-fifteen-session mandatory investment duration. [R12]

Research onset recognition, confirmed continuation, orderly resets and event repricing using distinct frozen definitions and controls. Do not silently revive the rejected generic no-veto leader reset. Being strongest is not an entry permission; being temporarily weaker is not proof of a catch-up opportunity.

### 8.3 Candidate-excluded peer confirmation

When evaluating a stock, exclude all listings of the candidate issuer from the peer read. A one-member group has no independent peer support. Overlapping themes sharing the same issuers are not multiple confirmations. Report the eligible and observed denominator, not just a percentage. These are the existing B09 responsibilities. [R10]

### 8.4 Position management

Distinguish changing group leadership, failure of the economic thesis, deterioration in stock-specific structure, valuation/expectations risk, and execution risk. A leader handoff inside an intact subtheme is not identical to rotating out of the theme. A timeout on an entry trigger is not automatic thesis invalidation.

Portfolio/Risk remains the sizing and exposure owner. Consolidate issuer, customer, end-market and factor concentration. Effective weight count `1/sum(w^2)` measures concentration of weights, not economic independence. Several optically different holdings may be the same customer-capex bet.

### 8.5 Terminal, multitimeframe and dislocation consumers

Slow economic/group context defines where to look; faster stock-specific structure helps assess when and how an entry might be executable. A dislocation in a durable leader requires different interpretation from a decline caused by deteriorating demand or collapsing peer support.

Do not require every timeframe to turn positive at once by default: that may create systematic delay. Compare qualified combinations under the appropriate entry-family evaluator. Terminal consumes accepted observations; it does not create an alternative ranking calculation in the browser.

## 9. Real-time and product architecture

### 9.1 Two market clocks plus the information clocks

Maintain tentative intraday observations separately from completed-session records. Preserve source publication, source observation, first-known, ingestion, correction, computation, decision and served-generation timing where applicable. Late data cannot be inserted into an earlier decision merely because its economic date is earlier.

The daily calendar owner documents that early-close clocks are not modeled. Reuse its session arithmetic for daily work, and extend/qualify the same accepted calendar source for intraday market opens, shortened sessions, halts, timezone changes and auction handling. Do not infer exact session clocks from a union of price-file rows. [R13]

### 9.2 Incremental computation, one shared read path

Use existing collectors and evidence owners. A new event updates affected issuers/relationships/groups; finalized bars update shared features. Materialized/cached read views feed the existing builders and APIs. Heavy parsing, graph calculation and historical replay stay off the render path.

A proposed one-to-five-minute active-group refresh is a performance target only where feeds and rights support it, not a current service guarantee. Slow reporting inputs retain their slow timestamps. Measure latency and cost per useful changed observation, not per newly created job.

### 9.3 Four consumer questions

Sector Intelligence: where leadership is established, emerging, narrowing or weakening.

GMI dossier: what mechanism explains it, what evidence changed, and what could change the view.

Prophet candidate/detail: which security expresses the opportunity, whether the candidate is eligible, and why it is not when excluded.

Terminal/dislocation: what the actual stock structure and executable conditions say now, alongside the slower context.

Use existing navigation, permissions and design system. Test desktop/mobile, light/dark and EN/ZH on actual owned surfaces rather than adding another dashboard.

### 9.4 Failure handling

Missing is not neutral, false or zero. Stale observations may remain visible with dates but cannot lead a fresh synthesis. Partial cohorts retain the expected denominator. Same-date corrections supersede rather than count as persistence. Rights or clock failures block the affected dimension, not unrelated lawful facts.

A failed publication must not silently serve a fresh wrapper around old data. Ordinary-refresh proof is required after initial deployment. No failure creates an automatic alternative publisher, bypass collector or hidden fallback score.

## 10. Empirical programme

### 10.1 Four distinct evidence tiers

**A: Long-history economic-group research.** Use qualified broad-industry data to sanity-check momentum, path quality, regimes and simple baselines across long periods. The official French industry series are useful research inputs but are not fine subtheme histories, and revised historical files are not the original publication vintages. Findings do not transfer automatically to today's subthemes. [P07]

**B: Mastermind retained historical cohort.** Reconstruct the exact source observations, membership/weights, known-time bounds, price basis and execution calendar for the retained 2026 histories. This diagnoses the deployed design and source coverage. It may have limited independent market episodes; report that limitation.

**C: Prospective shadow evaluation.** Freeze definitions and record decisions before outcomes in existing ledgers. This is the strongest evidence for new microtheme semantics and new document features when old point-in-time records do not exist. A nominal thirty-episode inherited gate is not alone sufficient for statistical power or robustness. [R07]

**D: Intraday implementation.** Only after daily context qualification, test next executable entry timing with appropriate quotes/spreads, auctions, halts, price limits, liquidity, costs and capacity. Close-to-close group predictability is not an executable entry strategy.

### 10.2 Freeze targets separately

Current leadership detection is descriptive and should agree with independently recomputed current measurements. Emergence asks whether a nonleader becomes a leader; persistence asks whether a current leader remains useful; entry timing asks whether a particular executable action has acceptable returns and adverse excursion.

Candidate primary emergence label for preregistration: entry into the top parent-relative quintile over a declared following-session window, with a separately defined persistence target. This is a proposed label, not an optimized threshold or accepted probability. Evaluate absolute outcome as well: relative leadership during a severe decline may still lose money.

Use 5, 10 and 20 completed-session research horizons for the new comparison, and retain the incumbent 21-session convention as a separately named sensitivity. Do not relabel old calendar-based outcomes as new session outcomes.

The new offline adapter chooses next-session open through the Hth following session close. That is explicit research target semantics, not a claim to reproduce the old close-to-close grader without change.

### 10.3 Baseline ladder and feature-family ablations

| Comparison | Increment being tested | What would falsify its usefulness |
|---|---|---|
| Stock-only momentum vs same stocks plus sector context | Broad allocation context | No paired out-of-sample improvement after risk/cost matching. |
| Sector context vs incumbent subtheme context | Value of narrower grouping | Gains vanish when the same candidate population and execution are used. |
| Incumbent vs corrected measurement/peer breadth | Reliability and cohort confirmation | Benefit is only missing-data selection or the candidate's own return. |
| Qualified price features plus path quality | Persistence versus raw acceleration | Effect disappears after prior returns/volatility and event controls. |
| Above plus earnings/revisions/read-through | Anticipatory economics | Known-time filtering removes the apparent lead or costs absorb it. |
| Above plus Vault claim changes | Independent research diffusion | Dedupe/stable-source-panel controls eliminate improvement. |
| Social/search individually | Incremental attention information | Pure reaction to previous price/news, unstable across regimes, or not worth cost. |

Do not stack every signal and test only the final combination. Preserve negative and redundant results. Conditional Fusion's existing research owner decides any model form; this document does not authorize a fused production score. [R10]

### 10.4 Statistical and timing controls

Chronological splits; train-only hyperparameters and taxonomy choices; purged training outcomes that overlap the validation start or become known only after it; untouched date blocks; clustered or block uncertainty for common dates, overlapping returns and economic exposures; paired labels and comparison populations; predeclared feature families and minimum economically meaningful improvement.

An unchanged set of successful tickers is not an unbiased universe. Preserve delisted, acquired and failed members where the owner data support them; never assign zero to missing delisting outcomes. Date-only observations require conservative, source-supported availability bounds and sensitivity tests, not invented intraday timestamps.

Count actual disjoint label intervals separately from independent market episodes. A large cross-section cannot create years of temporal evidence. Do not use significance from a handpicked best horizon without multiple-testing treatment. Model probabilities require calibration checks and Brier/log-loss comparisons against explicit baselines.

The current adapter's strict complete-population target is a qualification default, not a claim that discarding incomplete groups solves missing-not-at-random bias. The owner evaluation must also disclose how many groups were excluded, compare their characteristics and use justified bounds/sensitivity analyses. It must not report complete-case results as the entire opportunity population.

### 10.5 Decision metrics

Primary: earlier detection at matched precision or false-alert budget, together with net forward excess and adverse excursion under comparable risk and turnover.

Secondary: recall of later leaders; top-k persistence; per-date rank IC; absolute return; drawdown and recovery; entry feasibility; turnover and spread/slippage sensitivity; issuer/customer concentration; source coverage; probability calibration; and performance by predeclared regime, region and coverage tier.

Run negative controls: shifted/late timestamps, randomized within-parent labels, candidate-inclusive versus candidate-excluded peer support, duplicate-source inflation, stale inputs, placebo events, missing weak members, and source-panel expansion. Controls must be tied to the failure being tested; a placebo success is a reason to distrust the result.

### 10.6 What actually ran in this investigation

81 local tests passed, including a synthetic end-to-end command-line replay. Four tests reproduce legacy source failure mechanisms. Twelve additional author adversarial cases initially failed and were repaired in the new adapter before the final pass, including late-known training outcomes and nonfinite derived returns. This is author verification, not independent scientific review.

The existing recorded performance artifact was inspected and audited, not recomputed from raw historical market data. No new trading-performance, cost, capacity, calibration or market-holdout result is claimed. Public download attempts in this execution environment failed; inspected workflow artifacts contained CI evidence or no artifacts, not the qualified panel. This is a local access/qualification limit, not a claim that the company lacks price data.

The exact next empirical dependency is a source-owner-qualified export or mounted dataset containing retained snapshots, frozen membership/weights, feature availability, adjusted OHLC, calendar clocks and source receipts. The adapter refuses unsupported claims rather than manufacturing a backtest.

## 11. Delivery sequence and bounded work units

These are work units to attach to existing owners, not a new job queue or assertion that workers have started. Existing source writers, reviews and runtime custody must be reconciled before each effect.

### U0 - Repair and qualify the measurement contract

Owner: incumbent subsector track-record/Evaluation, coordinated with current rotation writer.

Inputs: exact current grader source; retained snapshots; calendar and price-owner interfaces; this adapter and regression cases.

Change: explicit session horizons, execution/knowledge clocks, frozen-denominator coverage, paired old/new cohorts and deterministic per-horizon comparison. Preserve old artifacts as historical versions; do not rewrite prior decisions.

Acceptance: exact endpoint cases including holiday/early-close behavior; missing member and benchmark refusals; matched cohort digests; no horizon-order effect; old/new calculation discrepancy report on the same real inputs; integration into existing CI; independent review. No live rank changes.

Rollback: restore the prior descriptive publication path while retaining new evidence and clearly withholding forward claims. Never silently substitute calendar outcomes for session outcomes.

### U1 - Qualify the economic pilot

Owner: GMI/F04 and company exposure.

Inputs: dated first-party product/customer/segment evidence; existing source-local and canonical concepts; current rights register.

Change: curate optics/connectivity, literal lithography, etch/deposition, packaging, memory and compute distinctions where warranted. Record exposure basis, uncertainty and incremental economics; permit multiple memberships and honest null canonical mappings.

Acceptance: source-span-backed relationships, effective and known times, primary versus adjacent beneficiary distinction, issuer overlap, sparse-group handling and rights-safe projections. No invented exposure percentages or automatic financial weights.

Rollback: return uncertain concepts to semantic-only status without deleting their evidence history.

### U2 - Finish the descriptive leadership vertical

Owner: #7455 and #7976 incumbent integration owners; shared UI owners remain separate.

Inputs: qualified identity/member/price receipts; accepted closed-session and repricing contracts.

Change: integrate strength, acceleration, persistence, breadth, concentration, revisions/earnings evidence and leader handoffs as named dimensions. Keep thesis health distinct from entry quality.

Acceptance: one real subtheme -> members -> company journey, source and generation agreement, candidate-excluded peer evidence, narrow-versus-broad cases, null/stale/correction cases, deployed bytes and subsequent ordinary-refresh proof. Review and release gates are not replaced by this plan.

Rollback: withhold affected dimensions, not substitute a new score or erase unrelated fresh facts.

### U3 - Add the economic evidence changes

Owner: Earnings Intelligence/Group Earnings, Research Vault, existing TIL/attention and evidence owners.

Inputs: admitted source documents, original hashes/spans, revisions and consensus vintages where available, existing relation graph.

Change: source-grounded economic claims, signed read-through, changed expectations and independent-source diffusion. Cluster report versions/reposts and exclude self-generated confirmations.

Acceptance: changes reproduced from actual document versions; future corrections cannot alter old decision views; claims survive without model-invented IDs; actual versus guidance versus consensus remains distinct; missing evidence stays missing; latency and rights disclosed.

Rollback: return to source-linked research display; no downstream forecast feature until requalified.

### U4 - Close the Prophet consumer/funnel gaps

Owner: Prophet R6 principal, B09/B10 and incumbent intake/episode/board owners.

Inputs: existing candidate and suppression receipts; group evidence; accepted entry-species definitions; current parent frontier.

Change: preserve relevant opportunities through intake and expose why-not decisions; distinguish discovery observation from actionable episode and entry from holding thesis. No fabricated anchors, group bonuses or global veto removal.

Acceptance: trace selected real cases across all funnel stages, including eligible-but-not-selected and data-unavailable cases; full cohort remains inspectable; independent peer support is genuine; stable source identities prevent duplicate origination.

Rollback: revert consumer changes under existing owner policy while retaining diagnostic receipts; do not alter the live graded population ad hoc.

### U5 - Run the registered comparisons

Owner: existing Conditional Fusion/Evaluation B10 with B06 labels and B09 inputs.

Inputs: U0-qualified panel, frozen hypotheses/targets, source rights and data provenance, realistic costs.

Change: execute the baseline ladder and source-family ablations on matched populations, followed by prospective shadow evaluation. Produce positive, null and rejected conclusions.

Acceptance: reproducible input/model hashes, untouched test intervals, paired uncertainty, predeclared economic effect threshold, independent scientific review, adverse-excursion/cost/coverage analysis. A result does not itself authorize a champion, sizing or population change.

Rollback: retain the incumbent decision policy and explicitly publish a null research result when the proposed enhancement fails.

### U6 - Production integration and operating proof

Owner: existing publishers and product builders; Portfolio/Risk owns any later action-bearing use.

Inputs: independently accepted source contracts and results; current rights/admission gates; actual browser/runtime environment.

Change: serve coherent cached views to GMI, Sector Intelligence, Prophet and Terminal; keep slow context and fast execution separate.

Acceptance: private/entitled access where required, desktop/mobile and dark/light EN/ZH journeys, generation freshness, ordinary refresh, partial and failure states, measured latency/compute budgets, no silent bypass of held data. Release progressively under existing rollback mechanisms.

US qualification does not certify CN/HK/global behavior. Regional rollout must separately address sessions, currencies, listings, corporate actions, limits and source availability through existing regional owners.

## 12. Reconciliation of prior plans and rejected shortcuts

This plan supplements, rather than replaces, the September federation architecture, GMI source law, Earnings read-through architecture and Prophet R6 programme. It adds a specific measurement-repair dependency and a clearer incremental research sequence.

Preserve: existing identities/rights/graph owners, named rather than universally fused dimensions, separate candidate and decision authority, existing entry/portfolio owners, current source/worker custody and release gates.

Change in proposed priority: qualify actual historical measurements and the full consumer funnel before investing in broad new social/search intake or fine-grained predictive displays.

Reject for this programme: a fourth semantic graph; a generic all-input score; a new ranker hidden in GMI sorting; today's membership backcast as point-in-time history; treating keyword growth as institutional flow; adding irrelevant stocks to make small groups broad; making all sectors pass a top-down gate; deleting anti-chase controls to include a handful of recent winners; and treating a synthetic test or code merge as market/production acceptance.

The inherited no-veto study remains adverse historical evidence. The current scorecard remains provisional. Existing draft branches remain their owners' work; this research branch does not take them over or establish an approved successor principal.

## 13. Current capability and exact next action

Built: an offline, deterministic acceptance adapter and tests that can qualify source-owner packets for clock, population and paired-comparison correctness. It has no network collector, production import, scheduler, rank policy or trade authority.

Verified: local contract and adversarial tests; isolated legacy failure reproductions; source-attributed audit of the current committed scorecard; GitHub source persistence/readback for the new research branch.

Not established: a new real-market historical replay, incremental out-of-sample edge, full scientific review, live product integration, deployment, ordinary-refresh acceptance or all-country readiness.

Primary continuation: **the incumbent Evaluation/Prophet B09-B10 path qualifies and supplies the exact retained snapshot/member/price/calendar packet, then runs the corrected paired replay; its result determines whether the next improvement is in measurement, intake, features or entry construction.** U1 semantic qualification and U3 rights-safe evidence adapter design can proceed independently under their existing source owners.

No additional user ceremony is needed for routine already-authorized source work. Human-only rights, authentication, protected approvals and live deployment boundaries remain real gates. No worker or watcher is claimed as dispatched by this document.

## Source register

All R references are owning-repository evidence read through GitHub. Unless otherwise indicated, paths are in `mastermindx-market-intelligence/macro` at census commit `e4910184b25c27eda95f81a09d3ce4a6f5d8535d`. Prior-plan observations are labeled and do not certify current production behavior.

- **R01:** `data/subsector_rotation/track_record.json`, blob `6713f5ad29061e752b8c21e9a180bc3c31a84574`; as of 2026-10-01, generated 2026-10-02T11:48:00.166631+00:00.
- **R02:** `engine/subsector_track_record.py`, blob `a6f9c2c5ae8511eefa8e7b721820f040d6cf59ce`; inspected horizon/maturity, available-member averaging, compute comparison and headline routines.
- **R03:** `scripts/build_subsector_rotation.py`, blob `cb4ce2ae1b3a546ee32a7ad1a5fe046bd7546f1c`; existing producer/publication and source paths.
- **R04:** GitHub PR #7455 and #7976 metadata, current API heads recorded in section 3; historical PR-body claims not re-executed here.
- **R05:** `research/PROPHET_US_TREND_INTELLIGENCE_MASTERPLAN_BY_FABLE.md`, section 2.5; historical 2026-08-03 exploratory study, not current live performance.
- **R06:** `research/prophet/cpu_leadership/CONVERSION_FINDINGS_2026-09-21.md`, blob `8a9750f80b982e488a47bd3b3b3db97f7ec5f7fd`; selected-generation intake analysis.
- **R07:** `research/GLOBAL_MARKET_INTELLIGENCE_MASTERPLAN_BY_FABLE.md`, source-law gates and ownership; dated historical census sections not treated as current liveness.
- **R08:** `research/EARNINGS_NEURAL_GRAPH_READTHROUGH_AND_CATALYST_ARCHITECTURE_2026-08-16.md`, blob `98a6a3f9859ff8e51d4aa2391f1d983423fbc38a`; architecture candidate, not proof of implementation.
- **R09:** `research/RESEARCH_VAULT_MASTERPLAN.md`, previously inspected in the parent research, metadata/text/hash/rights design; full production behavior not freshly verified here.
- **R10:** `research/prophet_v4/r6_fable_meta_ceo_handoff/work_cards/B09.md` (prior inspection) and `B10.md` (fresh read, blob `d6748c6d602d116e157d13c7b4574e6b1e1b79bd`); existing input and comparison owners.
- **R11:** `config/theme_sources.yml`, blob `e59ce0a9f98e34e45165545f21a84596c23a6de4`; actual current registry snapshot.
- **R12:** `research/prophet_v4/PROPHET_STRATEGY_CATALOG_V1_2026-09-30.md`, blob `fb5cf28e35f8c0ca9c2a57eaa0f881f8cd05d6e4`.
- **R13:** `lib/nyse_calendar.py`, blob `0ece6439ffe4b081ee7a268fe99b69e1de1216a3`; daily session methods and explicit early-close scope limitation.
- **R14:** Prior research addendum on #7976, comment `5956628573`; prior missingness reproduction and architecture recovery, not a fresh live-incident measure.
- **R15:** `docs/superpowers/specs/2026-09-20-sector-theme-subtheme-intelligence-system-design.md`, previously read in the parent research; preserved federation ownership.

Primary public research is used as evidence for hypotheses, not as direct validation of a 2026 subtheme or intraday strategy:

- **P01:** Moskowitz and Grinblatt (1999), *Do Industries Explain Momentum?* Author-hosted summary: https://www.aqr.com/Insights/Research/Journal-Article/Do-Industries-Explain-Momentum . Intermediate-horizon industry evidence; no automatic short-horizon transfer.
- **P02:** Cohen and Frazzini (2008), *Economic Links and Predictable Returns*. https://www.aqr.com/Insights/Research/Journal-Article/Economic-Links-and-Predictable-Returns . Public customer-supplier relationships and delayed information incorporation in the studied historical setting.
- **P03:** Novy-Marx (2015), *Fundamentally, Momentum Is Fundamental Momentum*, NBER working paper 20984. https://www.nber.org/papers/w20984 . Earnings/price momentum comparisons; not a current subtheme backtest.
- **P04:** Da, Gurun and Warachka (2014), *Frog in the Pan: Continuous Information and Momentum*, Review of Financial Studies 27(7), 2171-2218. https://academic.oup.com/rfs/article-abstract/27/7/2171/1578455 . Path/information continuity motivation; no intraday execution claim.
- **P05:** Blitz, Huij and Martens (2011), *Residual Momentum*, Journal of Empirical Finance 18(3), 506-521. https://repub.eur.nl/pub/22252 . Common-factor exposure controls and historical risk-adjusted comparisons.
- **P06:** Daniel and Moskowitz (2016), *Momentum Crashes*, Journal of Financial Economics; DOI 10.1016/j.jfineco.2015.12.002. https://www.sciencedirect.com/science/article/pii/S0304405X16301490 . Portfolio-construction and regime caveats apply.
- **P07:** Kenneth French Data Library, 49 Industry Portfolios and methodology. https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/Data_Library/det_49_ind_port.html . Broad-industry research input; source revisions and differing data regimes require explicit handling.
