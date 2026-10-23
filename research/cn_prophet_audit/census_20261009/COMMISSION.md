# MASTERMIND-X — CHINA PROPHET DEEP CENSUS & CANDIDATE QUALITY INVESTIGATION

**Role:** China Prophet Research & Intelligence Architecture Lead  
**Mode:** GPT-6 Pro / Extra High — Deep Investigation  
**Priority:** P0 — Product Intelligence Quality  
**Mission:** Determine why China Prophet is producing disappointing stock candidates, establish the actual root causes, and design a measurable, evidence-backed upgrade program.

## 0. Executive Mandate

Conduct a comprehensive forensic investigation of Mastermind-X's **China Prophet** stock candidate discovery, qualification, ranking, scoring, prediction, selection, and publishing mechanisms.

The central question is:

**Why is China Prophet so bad at identifying attractive Chinese stocks, and exactly what must change to make it substantially better?**

Do not assume the answer is simply that we need a larger AI model, more market data, or better weights.

Determine whether the problem originates from:

- An inherently weak alpha-discovery methodology.
- Incorrect or incomplete candidate universes.
- Weak features and missing Chinese-market intelligence.
- Flawed screening, exclusion, ranking, or scoring mechanisms.
- Bad entry timing, exit assumptions, or holding-period alignment.
- Insufficient regime and sector awareness.
- Overreliance on conventional momentum, valuation, or technical indicators.
- Stale, incomplete, incorrectly aligned, or low-quality market data.
- Predictive model failure, incorrect calibration, or unreliable labeling.
- Look-ahead leakage, survivorship bias, or misleading backtests.
- Failure to model China's distinctive trading mechanics.
- Misalignment between intelligence producers and the Prophet product.
- Problems with data delivery, publication freshness, and user-visible candidate presentation.

These are hypotheses, not established defects. Test them independently.

**Your job is to discover what is actually broken, how much each weakness contributes, and what improvements can be demonstrated rather than merely proposed.**

---

## 1. Source Discovery, Governance, and Execution

Primary repositories:

- `mastermindx-market-intelligence/Mastermind`
- The current canonical Macro implementation repository; verify its identity rather than assuming a historical repository or branch remains authoritative.

First:

1. Read the current protected `docs/sol_skills/INDEX.md` from Mastermind, pin the exact commit SHA, and load the applicable procedures from that commit, including `ACTIVE_EXECUTION` and `SESSION_RELIABILITY` where required.
2. Identify the current protected Mastermind and Macro source revisions.
3. Discover the real China Prophet implementation and its owners. Do not assume directory names or architecture.
4. Identify related work in China Information Edge, Prophet, market calendars, financial datasets, candidate engines, scoring, dashboards, backtests, and research dockets.
5. Reconcile existing PRs, open investigations, and completed research before recommending duplicate work.

Use GitHub, authorized repository inspection, available data-access tools, and existing analytics.

Do not modify live selection algorithms, production data, public predictions, or deployment configuration during this research mission.

Non-invasive diagnostics and reproducible local experiments are authorized subject to existing runtime, permissions, data-rights, and custody gates.

Persist research evidence to the existing canonical repository workflow. If a new code-bearing research artifact requires a PR, use an isolated Draft/HOLD carrier rather than colliding with existing implementation owners.

Do not launch a new ownership, queue, orchestration, or memory system.

## 2. Phase I — Complete China Prophet Mechanism Census

Reverse-engineer the entire candidate-selection pipeline.

Map the actual path:

**Stock universe → data ingestion → feature generation → screening → candidate eligibility → scoring → ranking → prediction → qualification → release timing → publication → outcome tracking → feedback and retraining**

For every stage, identify:

- Exact source files, functions, services, and upstream dependencies.
- Inputs, data sources, feature definitions, and update frequencies.
- Filtering conditions, hard exclusions, thresholds, and defaults.
- Ranking formulae, model architectures, and weighting logic.
- Model training, validation, calibration, and versioning, if present.
- What is persisted, cached, recalculated, or published.
- Data timestamps, timezone conventions, and freshness rules.
- Failure handling, missing-feature behavior, and silent fallbacks.
- Existing tests, telemetry, monitoring, and evaluation coverage.

Inspect whether the production pathway actually invokes the sophisticated intelligence already developed elsewhere in Mastermind, or whether Prophet is effectively using a simpler, disconnected selection algorithm.

Particularly investigate:

**A. Candidate generation**

Which stocks can enter the universe? Which cannot? Are promising small- and mid-cap opportunities excluded before ranking?

**B. Candidate qualification**

What makes a stock eligible? Are eligibility thresholds arbitrary, stale, contradictory, or biased?

**C. Candidate ranking**

What is the actual mathematical and computational mechanism that determines which stocks appear at the top?

**D. Prophet signals**

Are predictive signals genuinely forecasting useful future outcomes, or simply restating recent stock behavior?

**E. Final publication**

Are users seeing the highest-ranked eligible candidates, cached alternatives, manually selected stocks, or candidates modified by downstream constraints?

**F. Feedback**

Does Prophet evaluate previous recommendations and learn from success and failure? Is there an actual closed-loop performance evaluation system?

Deliver a traceable architecture map with verified source references.

## 3. Phase II — Historical Candidate Performance Autopsy

Establish whether China Prophet truly underperforms, by how much, and under which circumstances.

Reconstruct historical candidate outputs from actual stored or reproducibly generated point-in-time data.

Do not evaluate today's picks using information they could not have possessed when originally issued.

Use the fullest reliable history available, identifying coverage gaps explicitly.

Measure, where supported:

| Dimension | Required analysis |
|---|---|
| Hit rate | Positive and benchmark-relative outcomes |
| Forward returns | 1, 3, 5, 10, 20, and 60 trading-day horizons |
| Ranking quality | Rank IC, precision@K, top-decile lift |
| Risk | Maximum adverse excursion, drawdown, volatility |
| Timing | Performance following first actionable entry |
| Opportunity cost | Prophet versus eligible alternatives |
| Sector exposure | Concentration, sector bias, relative performance |
| Market regime | Bull, bear, sideways, crisis, recovery |
| Stability | Rank churn, turnover, signal decay |
| Execution | Slippage, fees, liquidity, limit restrictions |

Separate theoretical signal returns from realistically executable returns.

Compare Prophet against:

- Appropriate CSI market and size benchmarks.
- Simple momentum and reversal baselines.
- Sector-neutral and liquidity-matched random selections.
- Reasonable fundamental, quality, and valuation baselines.
- The current pipeline with individual filters/features removed.
- Existing Mastermind intelligence signals when they can be assessed fairly.

Use confidence intervals and sample sizes. Distinguish statistically meaningful improvements from noise.

Produce individual candidate autopsies of representative successful and unsuccessful picks:

- Original candidate and timestamp.
- Exact score and available features at issuance.
- Reason for selection.
- Actual actionable entry opportunity.
- Subsequent price path and relevant events.
- Specific reasons the original thesis succeeded or failed.

**Determine whether the main deficiency is candidate discovery, ranking, timing, prediction, execution realism, or product reporting.**

## 4. Phase III — China-Specific Market Intelligence Investigation

China is not a straightforward extension of the U.S. equity market.

Investigate whether China Prophet correctly handles the structural characteristics of the markets it actually covers.

Include:

### Chinese market mechanics

- Shanghai, Shenzhen, STAR, ChiNext, and Beijing exchange differences where in scope.
- Price-limit rules and limit-up/limit-down execution feasibility.
- Suspensions, ST/*ST designations, and delisting risks.
- Liquidity, turnover, and trading accessibility.
- T+1 restrictions and other relevant execution constraints.
- IPO seasoning and board-specific eligibility.
- Exchange calendars, multi-day holidays, and stale trading periods.
- A/H relationships and Stock Connect calendars when relevant.

### Chinese information advantage

Determine whether Prophet can properly exploit:

- Official Chinese-language company disclosures.
- Earnings releases, revisions, and earnings surprises.
- Regulatory and exchange announcements.
- Industrial policies and sector catalysts.
- Credit, liquidity, and macroeconomic regime changes.
- Industry supply-chain relationships.
- Company-level operating indicators.
- Institutional positioning and publicly available fund-flow proxies.
- Chinese-market sentiment and attention signals.
- Valuation, capital allocation, ownership, and governance signals.

Verify data availability, licensing, lag, and actual historical predictive value. Do not assume any alternative dataset provides alpha.

### Market regime adaptation

Investigate whether a single static strategy is being applied regardless of conditions.

Test whether different opportunity-selection approaches are warranted for:

- Broad-market recoveries.
- Liquidity-driven rallies.
- Policy-driven sector rotations.
- Earnings-driven repricing.
- Growth versus value leadership.
- Speculative momentum and subsequent reversal.
- Prolonged drawdowns and unfavorable liquidity conditions.

Evaluate the possibility that Prophet should issue **fewer or no candidates** when evidence is weak.

Do not recommend increased prediction frequency simply to maintain a full feed.

## 5. Phase IV — Root-Cause Analysis and Controlled Experiments

Construct a ranked failure register based on evidence.

For each material hypothesis, provide:

1. The suspected failure.
2. Exact implementation or dataset involved.
3. Evidence supporting or rejecting it.
4. Number or percentage of candidates affected.
5. Estimated impact on selection quality.
6. A reproducible experiment to isolate the effect.
7. A proposed remedy.
8. Confidence level and unresolved uncertainty.

Run bounded offline experiments where feasible.

Candidate experiments may include:

- Removing or modifying weak filters.
- Sector-relative instead of absolute ranking.
- Market-regime-conditioned signals.
- Explicit catalyst and earnings qualification.
- Improving data freshness and event alignment.
- Different entry-window definitions.
- Separating short-horizon and medium-horizon signals.
- Integrating verified Chinese-language intelligence.
- Confidence-calibrated abstention.
- Eliminating redundant or negatively useful features.
- Replacing stale or simplistic weighting mechanisms.

Use chronological walk-forward evaluations, untouched holdouts, leakage protections, transaction-cost assumptions, and defensible statistical comparisons.

Do not optimize solely against one backtest period. Record negative experiments.

Where historical data is insufficient, specify the smallest data, instrumentation, or prospective shadow evaluation required to resolve the question.

## 6. Phase V — Research Frontier and Competitive Evaluation

Investigate strong, relevant approaches from contemporary quantitative research and the Chinese equity market.

Evaluate the evidence for:

- Cross-sectional multi-factor ranking.
- Learning-to-rank and nonlinear factor interactions.
- Regime-aware models and mixture-of-experts approaches.
- Event-driven alpha and catalyst detection.
- Earnings revisions and announcement-driven repricing.
- Sector and supply-chain propagation.
- Short-horizon reversal and momentum conditional on regime.
- News and disclosures processed through multilingual models.
- Point-in-time graph-based company relationships.
- Predictive uncertainty and selective abstention.
- Alternative-data signals that are actually accessible and rights-compliant.

Compare methods on predictive value, operational feasibility, cost, robustness, leakage risk, maintenance burden, and incremental advantage over the current system.

Research existing China Prophet, China Information Edge, and TOI-related work before proposing overlapping infrastructure.

Do not blindly import U.S. trading assumptions or promote impressive research-paper backtests into production promises.

The goal is to identify which capabilities plausibly improve **our actual product with our actual data and engineering constraints**.

## 7. Phase VI — Design the China Prophet Upgrade

Produce a target architecture grounded in the investigation.

Consider whether the product should separate:

**Discovery engine:** Finds eligible Chinese-equity opportunities.

**Intelligence engine:** Evaluates fundamentals, events, catalysts, relationships, market structure, and risks.

**Ranking engine:** Estimates benchmark-relative opportunity quality at defined horizons.

**Timing engine:** Determines whether an attractive company is currently actionable.

**Qualification engine:** Rejects unsupported, stale, untradeable, poorly calibrated, or low-confidence candidates.

**Explanation engine:** Presents understandable, sourced reasons for selection, invalidation conditions, and uncertainty.

**Evaluation engine:** Tracks every issued candidate through realized outcomes and future model diagnostics.

These are conceptual responsibilities, not permission to create duplicate services. Map them onto existing Mastermind owners whenever possible.

Preserve clear distinctions between:

- Attractive company versus attractive stock price.
- Long-term thesis versus near-term trade.
- Predicted return versus confidence.
- Signal score versus suitability or execution accessibility.
- Strong historical result versus validated future predictive ability.

Design an approach that enables Prophet to show fewer but more credible candidates, with an understandable reason each one deserves attention.

No live trading, portfolio allocation, or model-originated position sizing is authorized.

## 8. Phase VII — Prioritized Improvement Program

Rank opportunities by:

- Expected evidence-backed performance impact.
- Confidence that the change addresses an actual failure.
- Implementation complexity.
- Data and licensing requirements.
- Operational cost and latency.
- Risk of regression.
- Reuse of existing Mastermind infrastructure.
- Time needed to validate results.

Organize the resulting roadmap into:

**P0 — Correctness and integrity**

Eliminate broken selection logic, data alignment defects, stale picks, look-ahead, misleading evaluations, or execution-impossible candidates.

**P1 — Candidate quality**

Improve universe construction, ranking, signal usefulness, timing, and qualification.

**P2 — China information edge**

Add only high-value, verified Chinese-market intelligence currently missing from the pipeline.

**P3 — Adaptive intelligence**

Evaluate regime-conditioned methods, stronger predictors, model calibration, and more sophisticated candidate selection.

**P4 — Product trust and learning**

Improve explanations, release timing, confidence communication, historical outcome reporting, and continuous monitoring.

Every recommendation must name the affected existing component, required evidence, acceptance test, and measurable success criterion.

Avoid arbitrary claims such as achieving an 80% win rate or guaranteed excess returns.

## 9. Required Deliverables

Produce the following, supported by actual source references, datasets, experiments, and reproducible commands where applicable.

### Deliverable A — Executive Diagnosis

An accessible report explaining:

- Why China Prophet currently produces disappointing picks.
- Which failures are proven versus suspected.
- The three to five highest-impact corrections.
- Whether the current foundation should be repaired, substantially redesigned, or selectively replaced.
- What we can improve immediately versus what requires research.

### Deliverable B — Full Mechanism Census

A source-linked map of every production candidate-selection stage, including duplicated, disconnected, or obsolete implementations.

### Deliverable C — Historical Performance Evaluation

Real performance tables, baselines, sample sizes, cohort breakdowns, and candidate success/failure case studies.

If reliable point-in-time replay is not possible, explain exactly why and define the data needed to make it possible.

### Deliverable D — Root-Cause Register

A ranked, evidence-based list of failures and candidate remedies.

### Deliverable E — Proposed China Prophet V2 Architecture

A specific evolution of the existing system, showing what to reuse, repair, retire, and introduce.

### Deliverable F — Experiment and Acceptance Plan

For every major proposed improvement:

- Hypothesis.
- Required implementation.
- Dataset and evaluation method.
- Benchmark and baseline.
- Success/failure threshold.
- Leakage and overfitting controls.
- Shadow-mode validation.
- Rollback or rejection conditions.

### Deliverable G — Implementation Handoff

An engineering-ready execution plan with:

- Prioritized work packages.
- Concrete code owners and likely source paths.
- Existing PRs or dependencies.
- Proposed bounded implementation sequence.
- Tests and production observability.
- Data-rights and source-quality constraints.
- Release and acceptance gates.

Persist the findings as a durable research docket through the repository's canonical process.

## 10. Investigation Quality Standard

This mission must go significantly beyond reading the Prophet README and proposing common stock-selection techniques.

Inspect actual production code.

Trace actual candidate records.

Compare actual predictions against actual subsequent results.

Verify what was knowable at prediction time.

Test whether existing signals contain meaningful predictive information.

Look for structural flaws that explain repeated underperformance.

Where evidence does not support a conclusion, explicitly state that.

Do not hide uncertainty behind sophisticated terminology.

Most importantly, **do not mistake improvements in presentation, model complexity, or backtest appearance for improvements in candidate quality**.

## 11. Execution Protocol

Begin with source qualification and the actual producer-to-publication pipeline.

Advance through the census, performance reconstruction, causal diagnosis, controlled experiments, research synthesis, and proposed architecture without stopping at an intermediate planning document.

Use existing authorized delegation facilities when the investigation can be separated safely, such as source census, historical performance, China-specific data research, and architecture assessment. Do not assume any worker has started without a verified receipt.

Persist material findings and reproducible evidence at milestones. Reconcile existing carriers and effects before any modifications.

If one dataset or dependency is blocked, advance independent investigations. Do not fabricate results or substitute unverified synthetic performance for real evidence.

Do not deploy, change live production rankings, publish recommendations, or activate trading.

## 12. Definition of Done

The investigation is complete only when we can answer these questions with verifiable evidence:

1. **How does China Prophet actually pick its stocks today?**
2. **How poorly does it perform, measured fairly against suitable alternatives?**
3. **Which specific parts of its selection mechanism are causing the disappointing outcomes?**
4. **What unique properties of Chinese equities are currently mishandled or ignored?**
5. **Which available Mastermind capabilities could materially improve its output?**
6. **Which proposed upgrades demonstrate improvement in robust offline tests, and which remain hypotheses?**
7. **What exact implementation sequence gives us the highest-confidence path toward substantially better candidate quality?**
8. **How will we measure continuously whether China Prophet is genuinely improving rather than merely producing more convincing-looking predictions?**

**Final objective:** Transform China Prophet from an insufficiently validated candidate generator into a disciplined, China-native, evidence-driven opportunity discovery system with measurable selection quality, realistic timing, transparent uncertainty, and a trustworthy feedback loop.

Start the technical investigation immediately. Do not stop after producing a generic strategy proposal.