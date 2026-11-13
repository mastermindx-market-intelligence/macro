> Supporting principal review recorded during the audit. Read PRINCIPAL_REVIEW_RESOLUTION.md and the corrected masterplan/task register for the adopted final proposal. This is not production or scientific acceptance.

# Terminal Options / Options Prophet — independent quantitative architecture review

Date: 2026-10-21. Role: principal adversarial design review for the Fable masterplan. This is a proposed target and acceptance framework, not a claim that any new signal is validated or deployed. No implementation, worker dispatch, source changes, or trading actions were performed.

## 1. Strategic conclusion

The product should earn the right to answer: **“What changed, what could it imply, which instrument best expresses that view, what could make it lose, and what should I monitor next?”** Its advantage should come from connecting evidence to decisions and tracking whether those decisions helped. More panels, more Greeks, a 3D surface, and a high composite score do not establish that advantage.

The existing architecture is already considerably more ambitious than a dashboard. Preserve its separation of Macro Plans, options-originated research, sparse model portfolios, and managed exact contracts. Implement its missing links end to end before inventing parallel stores, candidate ledgers, scoring owners, or a fifth Options owner. A new Fable program can consolidate outcome ownership while the incumbent source and lifecycle owners remain authoritative.

### Existing source anchors inspected

- Macro pinned main `d18dbe338fda75691d2f548efcd3a54242ea5978`, `research/OPTIONS_INTELLIGENCE_CONSOLIDATED_MASTERPLAN_2026-08-28.md`. The document is architecture/program control, explicitly not a live status database. Its October 9 addition describes the TP1 cash-pressure integration and its source limitations.
- Same pin, `research/options_estate/OPTIONS_PROPHET_SHADOW_ARCHITECTURE.md`.
- Terminal pinned master `d9ec4d2b86e9e9e0129d7fcd4c646f25f7670c49`, `docs/audits/2026-08-08-options-prophet-system-audit.md`.

These sources establish accepted design boundaries. Their August numerical snapshots must not be represented as fresh October census results.

## 2. Six evidence families with separate meanings

| Family | Question it should answer | What must not be inferred automatically |
|---|---|---|
| Information flow | Is qualified options activity unusual, persistent, and potentially informative at this horizon? | Large premium, call buying, volume/OI, or an ask-side print does not establish opening bullish institutional intent. |
| Positioning | Under stated inventory assumptions, where might hedging sensitivity amplify or dampen a move? | Open interest does not identify dealer inventory; estimated gamma is not a known net dealer position or a directional forecast. |
| Volatility price | Is the option's priced volatility/tail/event premium attractive relative to a qualified forecast or explicit scenario? | High IV is not automatically expensive; low premium is not automatically cheap; risk-neutral probabilities are not physical probabilities. |
| Price and pressure response | How is the underlying responding to qualified observed trading pressure and price structure? | A quote-location proxy is not an execution-time aggressor measurement; nonresponse is not proof of institutional absorption. |
| Catalysts | What scheduled or newly observed event could change the distribution within the trade horizon? | A news article cannot be assigned an earlier knowledge time, and an LLM narrative cannot create causal impact or a probability. |
| Execution and lifecycle | Can this exact contract or structure be entered, monitored, and exited under realistic conditions? | A fresh midpoint is not a fill; expiry payoff bounds are not proof that assignment, financing, or leg execution is harmless. |

Each family needs its own data availability, method/version, coverage, uncertainty, and permitted use. The user should see a compact conclusion with expandable evidence. Do not expose a wall of internal governance jargon in the primary experience.

### Confluence must add evidence

Represent lineage and overlap among observations. Flow, pressure, price response, technical momentum, and volatility changes may derive from the same price move or feed. Copying one observation into several panels cannot create several independent confirmations. Align the horizon and event cutoff before combining evidence: a delayed aggregate, a prior-night OI value, and a current quote describe different times.

For any proposed composite or rank contribution, compare a frozen base against base-plus-feature using the same eligible universe, timestamps, cost model, and outcome definitions. Use ablations and source-lineage controls. An attractive score without incremental utility is rejected. Existing DNR restrictions remain the current boundary until a narrowly scoped amendment is accepted; a new UI name does not bypass them.

## 3. Scientific and data architecture worth building

### Canonical data and contract identity

Reuse the existing intraday and EOD owners. Carry exact contract identity, deliverable, multiplier, exercise style, settlement type/time, trading calendar, corporate-action revision and listing validity. Preserve event time, original receipt/availability time, vendor publication time, quote time, calculation time, and served time separately. Filter by the decision cutoff before joins. A later T+1 observation may be used as training truth only in a later training cycle, never as a contemporaneous historical feature.

Maintain corrections and cancellations without rewriting historical decisions. Distinguish missing, stale, delayed, unavailable, partial, and observed zero. A pipeline build timestamp cannot make an old market observation current. Preserve source entitlements and derived-display rights at the actual product boundary.

### Flow and inventory inference

Use probabilistic signing with a genuine abstain state and propagate uncertainty into aggregate measures. Link complex-order legs where identifiers support it; otherwise avoid interpreting each leg as independent directional conviction. Normalize abnormal activity by instrument, time of day, expiry, moneyness, event context, and relevant historical distributions. Evaluate opening/closing inference separately from buy/sell classification.

Dealer inventory is a latent quantity unless a licensed observation establishes it within its actual venue and participant scope. Present inventory scenarios or uncertainty bands rather than one unqualified “dealer position.” Calculate gamma/vanna/charm responses under explicitly stated inventory, spot, volatility, and time assumptions. Test whether sign or interpretation changes under plausible alternative inventory assumptions. Any inventory-conditioned hedging demand remains distinct from a forecast of actual dealer transactions, because hedging instruments, timing, and objectives may be unknown.

### Volatility and pricing

Build reproducible surfaces from synchronized eligible quotes, model inputs, rates/dividends, contract style, and quality filters. Qualify interpolation and extrapolation, show observed support, and reject obvious violations of the appropriate option-pricing restrictions. Numerical error tolerances must be scaled to instrument price, tick size, and task, not an arbitrary universal epsilon.

Expose delta, gamma, vega, theta, vanna, charm and other advanced sensitivities only with explicit units and conventions. Validate them with independent numerical methods and finite differences. Reprice full structures under nonlinear stress; a local Greek approximation is insufficient near expiry, a strike discontinuity, or a large jump.

Separate three outputs: current market-implied terminal distribution; stated scenario P&L; empirically calibrated physical/path forecast. The first does not identify the third. A competing-risks or survival model for target-before-stop and time-to-event is an ambitious research challenger, not a prerequisite for honest scenario analysis and not an automatic transformation of the IV surface.

### Catalyst and event models

Start with verified event calendars and issuer/exchange primary information where possible. Preserve first-seen and revised timestamps. Separate scheduled event exposure from predicted event outcome. Useful advanced work includes event variance extraction, implied versus historically realized event moves, post-event volatility collapse, gap scenarios, and horizon-matched catalyst relevance. Train and evaluate event models on event groups, preserving repeated-company and shared-market dependence.

### Explainability

The explanatory layer may translate retained evidence into plain language and surface contradictions. It must not originate missing measurements, model probabilities, contract prices, scores, or lifecycle facts. A useful explanation names both supporting and disconfirming evidence and states what observation would change the conclusion.

## 4. Options Prophet must select structures, not just symbols

A symbol can be a good directional idea while its options are a poor purchase. The candidate engine must compare plausible expressions of the same thesis: shares, no position, long option, debit spread, defined-payoff credit spread, hedge, or another permitted structure. This comparison must use the same horizon and market observations.

Candidate families should remain separately measurable: directional convexity; bearish expression or protection; volatility/event exposure; finite-payoff carry; relative-value surface opportunities; portfolio hedges. Do not let a high-win-rate premium-selling family dominate an undifferentiated leaderboard or compare returns on incompatible capital denominators.

### Exact candidate object

Every issued candidate should retain:

- Originating hypothesis, intended user job, horizon, strategy family, and model/policy versions.
- Exact legs, quantities, opening/closing action, contract identity, deliverable, expiry, exercise/settlement conventions.
- Original observations and their actual availability cutoff; relevant contradictory and missing evidence.
- Executable quote context, spread/depth/age, reference entry policy, fees, adverse fill assumptions, and capacity qualification.
- Premium/capital-at-risk in currency; expiry payoff bounds and break-even; path, assignment, event, liquidity, and financing risks as applicable.
- Price/IV/time scenarios; what must happen to benefit; invalidation/expiry policy and monitoring triggers.
- Why this structure was preferred to a simpler alternative, or why the system abstained.
- Separate descriptive evidence quality, forecast calibration, estimated economic advantage, and implementability. One “confidence” number cannot represent all four.

The beginner presentation should show one understandable decision with a finite-loss default and an optional deeper analysis view. “Buy” and “sell” must identify buy-to-open/sell-to-open/buy-to-close/sell-to-close when relevant. Advanced users can select permitted complexity, but the product should never hide a short leg or imply that a credit received is maximum profit already earned.

### Portfolio and monitoring

Select the sparse portfolio jointly. Account for concentration in underlying, sector, common catalyst, delta, vega, expiry, liquidity, and correlated tail exposures. Use a frozen objective and robust constraints; an optimizer cannot compensate for unvalidated expected returns. Cash/abstention is a valid result. Preserve the earlier target of sparse issuance as a product hypothesis, never a quota that forces weak picks.

Differentiate issued model decisions, users' saved research, actual user positions, and any broker-reported fills. Do not merge them into one P&L series. Monitoring should explain changed thesis, worsening liquidity, event proximity, volatility changes, expiry/assignment exposure, and portfolio concentration. Whether a candidate lifecycle authorizes a management recommendation is a separate current-owner decision.

## 5. Evaluation and promotion ladder

| Gate | Required evidence | Falsifier |
|---|---|---|
| Measurement | Exact source identity/clocks; accepted semantic units; independent reference comparisons; natural-session coverage; missing/correction behavior | A known late, stale, adjusted, cancelled, or complex observation is represented as fresh/simple/independent truth. |
| Research candidate | Frozen hypothesis, universe, eligibility, horizon, trial history, point-in-time feature snapshots and suppressions | The candidate can only be reproduced using a revised source or surviving winners. |
| Forecast usefulness | Time-respecting out-of-sample evaluation; training-only normalization; horizon-aware purging; dependence-aware uncertainty; proper calibration and task-specific baselines | The gain disappears under held-out regimes, source-quality controls, simple baselines, or removal of one correlated feature. |
| Economic usefulness | Exact contract/structure selection; next-observable entry; spread/fees/latency; adverse fill and liquidity stress; appropriate capital denominator; tail and concentration results | Gross edge becomes negative under plausible execution, or direction is right while the selected option consistently loses. |
| Prospective shadow | Immutable decisions and suppressions; naturally arriving inputs; outcomes recorded without retrospective changes; registered look schedule | Missing outcomes, overwritten rules, hindsight exclusions, pseudo-replicated fires, or repeatedly inspected test data masquerade as independent validation. |
| Bounded product use | Explicit accepted family/use/horizon; user task evidence; specific source SLOs; degradation/rollback; telemetry and monitoring | A lower-tier signal gains ranking, alerts, or sizing authority through rendering or wiring alone. |
| Continued acceptance | Ongoing calibration, cost/capacity, drift, and user-value monitoring; retained version history and review triggers | A formerly useful model remains recommended after material performance or data deterioration. |

Do not adopt a universal “30 samples,” hit-rate, Sharpe, or AUC gate. Predeclare the smallest economically meaningful improvement, dependence structure, expected costs, confidence criterion, and statistical power for each family. A large row count can represent very few independent market sessions. The historical source audit already found repeated horizon rows being miscounted as independent fires; preserve that lesson in tests built from the actual production schema.

Use the existing evaluation/qledger and episode/campaign/outcome owners. Keep at least three distinct comparisons: existing Macro candidate without options; the same Macro candidate plus a frozen qualified options contribution; independently options-originated candidates. All three should disclose selection and evaluation differences. No result can be claimed incremental merely because it performed better in a different universe or period.

### Essential baselines and stress tests

- Source-order/activity-only; simple momentum or volatility rules; liquidity-matched random/control candidates; current accepted Macro baseline; no-trade where appropriate.
- Shares versus the recommended option expression, and simple liquid structures versus an optimized structure.
- Spread widening, missed fills, conservative fills, delayed entry, stale quotes, invalid surface points, price gaps, IV collapse, corporate actions, assignment and settlement cases.
- Regime, event, liquidity, DTE, underlying class, right, and strategy-family slices. Disclose data-poor slices; do not hide them in pooled results.
- Cluster/block uncertainty aligned to sessions, episodes, issuers and common shocks; overlapping horizons and repeat candidates cannot be independent trials.
- A permanent experiment history, independent held-out evaluation, and genuinely untouched prospective decisions. Retuned test results return to research.

## 6. Differentiated capabilities with credible user value

1. **Thesis-to-structure comparison:** show when a correct stock view still implies a bad option purchase, and identify a simpler expression or no-trade alternative.
2. **Evidence change tracking:** explain what changed since the last observation, with source freshness, uncertainty and contradictions, rather than repeating a static bullish/bearish label.
3. **Event and volatility decomposition:** separate expected directional move, implied event premium, post-event IV collapse and path dependence.
4. **Conditional positioning explorer:** show inventory-assumption sensitivity and price/vol/time shocks with linked 2D slices; any 3D view must support a discriminating task beyond visual spectacle.
5. **Portfolio-aware candidates and hedges:** show how an otherwise attractive candidate changes the user's declared risk profile, without silently inventing their holdings or risk tolerance.
6. **Knowable-at-the-time replay:** reproduce the original decision and compare later evidence; original facts and later revisions remain visibly distinct.
7. **Outcome attribution:** separate signal selection, structure selection, timing, execution and management contributions. This makes improvement possible and prevents a stock winner from hiding an option loser.
8. **Useful abstention:** explain why no candidate clears the current bar and what evidence or market change would reopen consideration. Abstention should teach, not look like a broken screen.

## 7. Sequencing decisions for Fable

The first meaningful product vertical should connect one qualified family in a liquid universe from natural input through candidate evidence, exact finite-loss structure, realistic quote qualification, plain-language thesis, immutable decision and later outcome. It should also demonstrate no-candidate, conflicting-evidence, stale-source, and failed-execution cases. This proves the architecture and user value more effectively than parallel delivery of many disconnected panels.

Build data/measurement quality and UX discovery in parallel. Begin descriptive scenario and structure tools before waiting for alpha validation; preserve their descriptive status. Bring advanced statistical/ML models in as challengers after simple baselines and qualified data. Run independent statistical acceptance separately from visual/product acceptance. Reserve Fable judgment for cross-owner policy, source spend, DNR amendments, irreversible product claims, and final outcome acceptance; reserve hard model/estimator implementation for qualified Opus where bounded labor cannot safely resolve it.

Do not make “full parity” a reason to copy competitors' opaque scores or unsupported claims. Parity should mean users can complete every relevant competitor job with verified data and equal-or-better task performance. Superiority must be measured on usefulness and reliability, not promised in advance.

## 8. Current primary-source checks for the parent audit

The parent must open these sources before using their web reference IDs in its final response. Summaries below are deliberately short and scoped.

- Cboe Open-Close: https://datashop.cboe.com/cboe-options-open-close-volume-summary — inspected 2026-10-21. Selected Cboe venues; participant/action/open-close volume summaries; current page advertises EOD and 1-minute or 10-minute snapshots. Raw internal use only; external derived display requires additional approval/fees. Ref `turn3view0`.
- Cboe Enhanced TBT: https://datashop.cboe.com/enhanced-us-options-trade-by-trade-execution-detail — C1-only currently, T+1; side/open-close/capacity, NBBO/local BBO and simple/complex execution IDs. It is training/reconstruction evidence, not a same-day live feed. Ref `turn3view1`.
- TBT technical spec: https://cdn.cboe.com/resources/membership/US-Options-Trade-By-Trade-Execution-Detail-Specification.pdf — v1.0 dated 20260112; distinguishes processed/booked time, trading date, floor-action timestamp and late trades. Ref `turn3view2`.
- FINRA OTC Transparency: https://www.finra.org/filing-reporting/otc-transparency — aggregate ATS and non-ATS reporting is delayed. Do not market it as live identified dark-pool buying. Ref `turn0search1` (opened in the source batch).
- Federal Reserve, *What is Certain about Uncertainty?*: https://www.federalreserve.gov/econres/ifdp/files/ifdp1294.pdf — risk-neutral derivative-implied probabilities differ from physical probabilities and contain risk-premium information. Ref `turn3view3`.
- OCC, *Characteristics and Risks of Standardized Options*: https://www.theocc.com/getcontentasset/a151a9ae-d784-4a15-bdeb-23a029f50b70/dfc3d011-8f63-43f6-9ed8-4b444333a1d0/riskstoc.pdf — inspected for exercise, assignment and settlement risks. Use to ground contract-specific risk modeling, not to add a generic warning wall.
- Cboe, *0DTEs Decoded: Positioning, Trends, and Market Impact*, May 2, 2025: https://www.cboe.com/insights/posts/0-dt-es-decoded-positioning-trends-and-market-impact/ — its historical analysis illustrates why large gross activity need not imply large net dealer hedging. This is not proof of today's positioning. Ref `turn4view0`.

## 9. Decisive IOB research integration delta

This additional review inspected the four exact Terminal issue 599 research returns below and three linked source artifacts at the reported #9492 merge (`a2a1f2e40624cf079c1e756f9f7b0a4306539d2c`): the identity-offset kernel, frozen pilot specification, and study/refusal adapter. The empirical results below are reported by the original research owner; this review did not rerun their private datasets or experiments. The source-level design and refusal boundaries were directly inspected.

### Preserve and consume the original research programme

The original root is `institutional-options-iob-20261012-c1`. R15 reports a fourteen-round evidence synthesis, a ranked twelve-family Options Strategy Research Atlas, an existing-owner experiment/consumer contract, and retained R2–R14 archives. A hash-verified archive establishes integrity and continuity, not a new empirical rerun. The package is a research return for the existing parent programme, not implementation custody. The plan should make the original Fable continuation and original research root part of the consolidation map; apparent session inactivity is insufficient reason to replace them.

The original scientific thesis is already **conditional hedge-demand intelligence**, with observed or explicitly assumed holdings, hedge policy, costs, fixing/model conventions, risk units and surface assumptions. It does not equate an estimated target with executable liquidity. Risk transition, crash bounds, return prediction, dynamic hedge effectiveness and exact-option trading economics remain different questions. The masterplan should preserve that separation while bringing the useful outputs into a single product workflow.

### Six concrete advanced pilots already specified

The inspected `pilot-study-spec.v1.json` is explicitly a principal proposal with nine null binding fields, unbound split dates, and G0–G6 admission requirements. These are researched contracts, not executed production features.

| Pilot | Already specified question | Meaning and boundary |
|---|---|---|
| P1 / OIF01 | Does 15-minute option activity relative to underlying volume add information about the next 30-minute price range? | Activity/range, not bullishness or opening demand. |
| P2 / OIF04 | Does qualified signed delta-weighted option flow improve a 30-minute market/sector-residual return forecast? | Strictly preceding valid quotes and package controls; unknown exposure retained. Not a calibrated directional probability or dealer inventory. |
| P3 / OIF19 | Does forward-ATM implied volatility minus a causal physical HAR risk forecast add information about a matched twenty-session variance outcome? | Exact expiry/strike support and total-variance interpolation; no extrapolation. The vol spread is not a variance and is not the separate OIF20 variance-risk-premium feature. |
| P4 / OIF22 | Does an OI-weighted matched call/put IV spread, with prescribed borrow/carry/dividend/spread controls, improve a later residual-return forecast? | As-of or cross-fitted nuisance projection and an explicit one-session skip; not proof of private information or fee-free shorting. |
| P5 / OIF13 | Does a frozen hypothetical same-day book's nonlinear hedge response to a −1% spot, +1 volatility-point, ten-minute shock add information about ten-minute realized variance? | The primary call-positive/put-negative OI allocation is an inventory scenario, not observed dealer holdings. It is not five-day direction, actual hedges, or causal amplification. |
| P6 / OIF35 | Does quoted relative spread improve a model of actual full-fill implementation shortfall? | Requires independent actual fills and fees; partial/nonfills are explicit separate outcomes. Simulated midpoint marks cannot supply the target. |

Reconcile and extend these pilots through their original owners. Do not create a second HAR implementation, eight-covariate builder, experiment adapter, evaluator, or outcome ledger under the new masterplan.

### Numerical machinery: useful source work, no empirical promotion

R15 independently reviewed the identity-link B1-RI kernel that subsequently merged in #9492. Direct source inspection confirms that it implements the frozen eight-column offset calculation for P1/P2/P4/P6 and checks numerical domains and supplied clock order. It deliberately does not authenticate historical receipt provenance, population eligibility, date-balanced weights, or B0 cross-fit lineage.

R16 supplies the complementary P3/P5 positive-link solver: `v1 = v0 * exp(C gamma)`, bounded eight-dimensional coefficients, weighted QLIKE plus fixed ridge, deterministic coordinate descent, explicit convergence criteria and typed refusal. Its numerical comparisons and later R17 native unit tests establish arithmetic feasibility within their scope. They are not forecast accuracy, population qualification, throughput acceptance, or permission to activate the empirical adapter. Integration must reconcile the original candidate and source custody instead of rewriting it.

B1-RI is a target-trained **summary of incumbent information**, not the live production ranker. Beating B1-RI does not establish superiority over the actual production policy or every raw incumbent feature. The specification requires causal B0 forecasts inside each RI fit, historical cross-fitting, then held-out B1-RI offsets for B2. Mature labels alone do not make in-sample HAR offsets causal. The existing adapter explicitly refuses all empirical execution while its gates remain unsatisfied.

### Scientific failures and kills that must survive

| Original finding | Required programme consequence |
|---|---|
| R4 exploratory 13.31% result is qualified by R5/R6 and R7 source gaps | Never extract the attractive number into a product claim or use it as accepted alpha. |
| R13 favourable point estimates did not pass its family test; R14 worsened both later-period return benchmarks | Do not continue tuning that same simple directional model on the inspected history. Preserve its scoped negative result and seek genuinely new observations or a different research question. |
| R18's 312 weekly origins: variance QLIKE 0.4025873 → 0.4145204, 2.9641% worse | No accepted variance improvement; both fixed subperiods also had worse primary point scores. |
| R18 risk-increase Brier 0.1759672 → 0.1789086, 1.6716% worse; both primary Holm-adjusted p-values = 1 | No predictive promotion. This does not prove universal harm or zero information in all options data. |
| Additional seven-day lag: apparent variance improvement with interval crossing zero and adjusted p = .569; probability score worsened | Not a winner to select after inspection. It changes both baseline and additions, so it is not an isolated options-latency experiment. |
| Historical release/first-known and revision evidence was not authenticated; conservative lag assumptions were used; outcomes were previously inspected | Treat R18 as retrospective qualified research, not an untouched, fully receipt-authenticated prospective test. Do not retune the block on the same 312 weeks. |

R18's reusable acquisition contribution is the provider-documented CFTC PRE API path and the matched exact-code futures-only/combined histories, carried through existing source owners. It is not live dealer gamma. Preserve R18's correction to R17: under matched reporting categories/populations, a combined-minus-futures-only net difference can be a meaningful aggregate option-equivalent contribution. It still does not identify individual inventory, gamma, or executed hedges. Differing trader counts do not automatically make every aggregate difference meaningless, and count differences are not unique newly identified traders.

### Two next decision-changing paths

**Known-book hedge utility:** a qualified book with observed hedge actions, executable quotes and costs; compare the incumbent hedge policy with one frozen volatility-aware challenger. Report residual variance, downside, mean P&L, turnover, fills and nonfills separately. Risk reduction is not necessarily profit improvement. Add uncertainty-aware control only after the uncertainty estimate itself is qualified.

**Predictive incremental value:** genuine uninspected observations with authenticated release/correction chronology and the required incumbent, IV, volume, liquidity and roll controls. Freeze the endpoint and useful margin before observing the new outcomes. A new coefficient set on old inspected outcomes is not new evidence.

The plan must also retain the existing OA-3 exact-option evaluator rather than duplicate it. R15 describes its narrow v1 as one standard long contract, first firm ask after expression availability, actual entry plus 60-minute bid, same RTH, fixed $0.65 per-side research fee, no 0DTE/packages/shorts or midpoint/stock substitution. A dynamic known-book hedge study is a separate experiment; it must not masquerade as OA-3 or import another cohort's identity. Broader structure/lifecycle capabilities belong in explicit later versions with their own acceptance evidence.

### Exact evidence references

- R15: https://github.com/mastermindx-market-intelligence/mastermind-terminal/issues/599#issuecomment-6205483325
- R16: https://github.com/mastermindx-market-intelligence/mastermind-terminal/issues/599#issuecomment-6212979482
- R17: https://github.com/mastermindx-market-intelligence/mastermind-terminal/issues/599#issuecomment-6225063323
- R18: https://github.com/mastermindx-market-intelligence/mastermind-terminal/issues/599#issuecomment-6230275005
- Merged identity kernel: https://github.com/mastermindx-market-intelligence/macro/blob/a2a1f2e40624cf079c1e756f9f7b0a4306539d2c/scripts/options_pilot_identity_offset.py
- Frozen pilot contract: https://github.com/mastermindx-market-intelligence/macro/blob/a2a1f2e40624cf079c1e756f9f7b0a4306539d2c/research/options_intelligence/2026-10-03/pilot-study-spec.v1.json
- Empirical-refusal adapter: https://github.com/mastermindx-market-intelligence/macro/blob/a2a1f2e40624cf079c1e756f9f7b0a4306539d2c/scripts/options_pilot_study_adapter.py

