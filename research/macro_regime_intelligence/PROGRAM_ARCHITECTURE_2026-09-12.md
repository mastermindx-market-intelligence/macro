---
schema: mastermind.macro_regime_intelligence.architecture.v1
operation_key: macro-regime-intelligence-architecture-20260912-sol-001
workstream: WS:RATES-INFLATION-COMMAND
program: rates-inflation-command
related_programs: [market-regime-risk]
owner: ceo-sol
status: CEO_DESIGN_BASELINE_PENDING_INDEPENDENT_REVIEW
capability_state: SPEC_ONLY
product_effect: NONE
runtime_effect: NONE
worker_effect: NONE
procedure_repo: mastermindx-market-intelligence/Mastermind
procedure_commit: 57a2672af5b9dcea282e4bae01d1a0b9d10bb1cd
skillpack_version: 1.0.1
bootstrap_major: 1
macro_evidence_commit: 1850547c80e92191e6b195acce446c912de7f5e3
authored_on: 2026-09-12
---

# Macro Regime Intelligence: one research experience, several accountable models

## 0. Mandate, disposition, and non-claim

Chairman Chris asked for an integrated historical and forward-looking understanding of real rates, breakevens, nominal yields across maturities, the dollar, changes and acceleration, technicals, employment, equity stability, Fed and administration policy, economic/inflation/oil regimes, historical implications and the intensity of future environments. The live follow-up to this Sol session was: "Take this on end to end to plan and complete autonomously."

This is the resulting CEO design baseline and delivery contract. It is not another autonomous program, model registry, queue, forecast ledger, graph database, or dashboard family. Organizational continuation stays in WS:RATES-INFLATION-COMMAND; existing market-regime-risk, Market OS, transmission, Evaluation OS, and portfolio owners retain their responsibilities. No parent is minted in the program registry.

**Current state: SPEC_ONLY.** This record does not claim implementation, independent review, CI, worker placement, production adoption, forecasting skill, or trade authority. The first implementation described below is contingent on current source custody, eligible execution capacity, and independent architecture review. The Chairman's live instruction supplies intent; this retrieved document does not self-assign a later worker.

The flagship question is:

> Are real yields approaching a durable peak, or only pausing? What would distinguish orderly disinflation, deteriorating growth, renewed inflation, a long-end premium shock, and a temporary technical reversal? What changes for bonds, gold, silver, equities, the dollar, and the user's portfolio under each path?

The final product must answer that question without making the user assemble ten dashboards. A connected graph without that answer is not completion.

## 1. Product and intelligence thesis

### User job

A portfolio manager or researcher needs to orient, identify what changed, understand the mechanism, compare plausible futures, examine comparable history and counterexamples, inspect conditional exposures, and save an evidence-backed watch or thesis. The product should reduce the cost of maintaining a coherent macro view while making uncertainty and disagreement visible.

### Machine job

Provide one versioned, source-clock-aware research projection of existing owners, with separate current-state estimates, market-implied pricing, conditional scenarios, horizon-specific statistical forecasts, historical outcomes, and permitted asset-exposure context. Existing Brain/Analyst and portfolio consumers must be able to explain the same evidence the user sees. They must not infer absent clocks, convert a hypothesis into probability, or treat several transformations of one observation as independent votes.

### Moat

The differentiated asset is not a bigger indicator directory. It is the accumulating, correction-safe record of state -> proposed mechanism -> conditional path -> independently selected historical evidence -> issued forecast -> realized outcome -> useful user decision. Negative results, rejected analogies, changed relationships, and well-dated research hypotheses remain part of that memory. Original implementation and properly licensed inputs are mandatory; competitor products supply workflow references, not code, text, or data to copy.

### 10/10 end-state

One existing Macro entry leads to: **Now / What changed / Possible paths / Historical comparisons / Exposures / What we are watching**. Every headline can be traced to the same machine contract. Future probabilities have explicit targets and horizons, documented calibration, and honest abstention. Historical examples include losing cases. Scenario strength is decomposed rather than collapsed into a mysterious score. Saved research and alerts use current owners. Instrumentation measures whether people complete this journey and whether the forecasts improve on simple alternatives.

The ambition is comprehensive. The release unit remains one independently useful vertical capability.

## 2. Reconciled estate and no-rebuild boundaries

Unless otherwise stated, file evidence in this section refers to Macro commit `1850547c80e92191e6b195acce446c912de7f5e3`. A repository implementation is not automatically PROVEN_LIVE.

| Capability | Existing owner / evidence | Disposition for this program |
|---|---|---|
| Nominal curve, real/breakeven slopes, curve shape and speed | `engine/yield_curve.py`; `research/YIELD_CURVE_ENGINE.md` | Extend or consume; never create a parallel curve engine. Broad nominal coverage does not imply equally broad TIPS coverage. |
| Multi-horizon yield changes and acceleration | `engine/yield_momentum.py` | Reuse the 2/5/10/20/30-year owner and its 5/22/63-session reads. Preserve the canonical `us20y` source, including its explicit no-substitution rule. |
| Rates/inflation/dollar transmission | `engine/rate_inflation_transmission.py`; `research/RATE_INFLATION_TRANSMISSION.md` | Existing measured associations and illustrative scenarios are inputs, not certified return forecasts. Retain negative verdicts. |
| Forward Path board | `engine/rates_inflation_command.py::build_board`; `scripts/build_rates_command.py`; `data/rates_command/latest.json` | This is the composition and publication home. Add an isolated research projection, not a competing store. |
| Dollar context | `engine/forex_dollar.py`; `data/forex/latest.json` | Reuse trend, valuation, positioning and policy-path context. Do not substitute a USD policy leg for a measured international rate differential. |
| Canonical regime decomposition | `engine/regime_one.py`; `engine/quad_vector.py` | Keep tape, economic evidence, filtered membership and risk authority distinct. New forward estimators belong to this owner, not the display composer. |
| Historical HMM display | `engine/regime_hmm.py` | Smoothed history is descriptive. Filtering with a later full-sample fit does not create a historical live forecast. |
| Driver attribution | `engine/market_drivers.py` | Sole existing shock/driver interpreter. Do not add another shock classifier or feed its constituent target-asset returns back as independent prediction evidence. |
| Transmission chains and episodes | `knowledge/transmission/SCHEMA.md`; `engine/transmission_chains.py` | Reuse chain identities, revision, lag, conditions, nulls, falsifiers and episode ownership. A richer display never silently promotes a chain into alpha. |
| Macro & Monetary workspaces | `engine/market_os/macro_workspaces/`; `templates/macro_monetary.html.j2` | Product integration, not transfer of domain truth. Retain active Market Ontology source ownership and current route migrations. |
| Existing public transmission surface | `templates/transmission.html.j2` | First visible research comparison belongs here through the existing build path. Do not invent another macro page. |
| Historical analogues / studies | Existing F10 Historical Analog Lab, Evaluation OS and Trial/Outcome owners; `agentos/handoffs/MARKET-ONTOLOGY-F10-QUANT-ANALOGS-FABLE-COO-2026-08-26.md` | Extend episode selection and outcome methods; do not duplicate a study registry or historical memory service. |
| AI briefing evidence | PR #7024; `engine/master_brain.py` existing regime reader | Reuse its deterministic dated evidence contract; do not add a second regime narrator or overwrite its incumbent source. |

### 2.1 Exact in-flight work that must be preserved

- **PR #7015**, operation `regime-hmm-w0-temporal-honesty-20260909-sol-001`, published head `0bd578085ee2e51e27de6b8610794a88cbbc28f8`: existing recorded-HMM history admission and temporal-honesty work. Direct PR read found Draft, unmerged and non-mergeable. Its tests and prior review receipts are not reproduced by this document. Do not duplicate its ledger reader or invent missing historical issuance metadata.
- **PR #7024**, operation `regime-hmm-w1-briefing-context-20260909-sol-001`, published head `66f9e5d0be33e2f6c1a6d4e749536d2f3e956cc5`: existing briefing consumer. Comment `5647959939`, dated September 12, 18:49:36Z, reports applied but unpublished incumbent changes, an unavailable Studio route, and an unresolved read-only preflight result. This is not an abandoned clean remote branch available for replacement. Source publication must reconcile that same incumbent.
- **PR #6860** owns the shared Lens interaction prerequisite identified by #7024. No parallel tooltip fix.
- **PR #7032** is reported merged in #7024's latest owner receipt. Do not continue presenting it as an unmerged prerequisite; a fresh integrated candidate still owes its own checks.
- **PR #6593** is the identified RIC workstream-status reconciliation carrier. This architecture does not independently rewrite `agentos/workstreams/WS-RATES-INFLATION-COMMAND.md`.
- **PR #6788 / issue #6787** owns adjacent policy-pre-turn monthly-transition architecture. Conditions and planning clocks may be consumed after acceptance; this program does not restart that child or become an administration-timing predictor.
- **PR #7031 / #7030** concerns an adjacent PCE release-research lane with its own source/safety boundaries. Its blocked executable material is not imported, reconstructed, or republished here.
- **PR #7040** already owns Risk Radar score-velocity/current-versus-prior work. No replacement risk score or ledger.
- Macro Command and bond-route migrations retain their active source owners. In particular, do not recreate a retired rates page because an older architecture names it.

These are evidence locators and boundaries, not a claim of current worker liveness. Source owners must be reconciled again immediately before an overlapping operation.

### 2.2 Why the current composition cannot simply be renamed a forecast

`build_board` reads several separately dated artifacts, uses the newest of only selected input dates as its wrapper `asof`, and can fall back to the current date when those dates are absent. The new projection may not inherit that wrapper as proof that every contributing fact is current. It must carry each input's own clock and provenance.

The same source's `compact_state` currently assigns `usd_dir` from the policy-row object rather than a dollar-direction field. This architecture does not repair unrelated legacy behavior by stealth; the new consumer must use the dollar owner's actual contract and explicitly test the join.

The existing code and prior research distinguish descriptive associations, contemporaneous shock betas and return-predictive content. Their negative results are a reason to test conditional methods carefully, not a reason to abandon useful analysis or to promote the same failed construction under a new label.

## 3. Economic objects and measurement contract

### 3.1 Four objects that must never be conflated

1. **Current state:** what observed data suggest now, including uncertain regime membership.
2. **Market-implied pricing:** the path priced into traded instruments, with its measure, risk-premium and instrument caveats.
3. **Conditional scenario:** an explicit assumed path and its implications. Scenario plausibility is not a numerically calibrated probability.
4. **Statistical forecast:** a distribution over a named future observable/target at a declared horizon, issued from a known information set and evaluated against realized outcomes.

A fifth object, **historical description**, includes smoothed regime history and retrospective analogues. It may inform research, but must not masquerade as an issued historical forecast.

### 3.2 Maturity, duration and forecast horizon

These are separate fields. A 10-year yield observed today can have a 1-month forecast; a long-bond ETF has changing portfolio duration rather than the maturity of a single Treasury. Labels, plots and scenarios must not exchange these concepts.

Treasury CMT yields are par, bond-equivalent rates, not a zero-coupon curve. Do not calculate economically precise forward rates by treating par yields as zero rates. Use a documented existing zero/discount-curve method, or show an explicitly approximate spread. Keep compounding convention, day count, nominal versus inflation-linked instrument and curve source in the receipt. See sources S1-S2.

### 3.3 Coverage destination

**Nominal curve:** front-end through long-end, with the full governed maturity grid available from existing collectors. **Real curve:** all supported TIPS tenors, with 5/10-year coverage distinguished from additional observed or modeled maturities. **Breakevens:** compatible same-date nominal/TIPS objects and independently sourced inflation-compensation measures; no arbitrary interpolation presented as observation. **Policy path:** futures/OIS or governed equivalent, dates and instrument conventions retained. **Term premium:** existing Kim-Wright plus another model only after collection/rights/validation review; show model disagreement, not an assumed true point.

**Dollar:** keep DXY, broad trade-weighted nominal USD and BIS real effective exchange rate conceptually separate. Relative US/foreign policy and real-rate paths require actual matched foreign inputs. Funding stress, safe-haven demand, trade competitiveness and US growth advantage are distinguishable mechanisms, not interchangeable explanations for a rising index. BIS research motivates the financial channel, not a universal numerical coefficient (S8).

US is the first complete research slice. International extensions reuse country and FX owners and disclose local data limitations. No US value is silently reused under another country's name.

### 3.4 Levels, changes and velocity

For rates, use basis-point changes; a percentage change around zero is not an appropriate yield-velocity measure. Distinguish raw level, trailing percentile, change over declared market sessions, slope of the recent path, equal-window acceleration, persistence, and cross-maturity breadth. Calendar days, business days and observed rows are not aliases. A missing observation must not silently shorten a 22-session window into 22 irregular observations.

Keep observed long real yields separate from an estimated short real policy stance relative to an uncertain neutral rate. A positive TIPS yield alone is not proof of policy restrictiveness. Inflation expectation horizon must match the real-policy-rate construction; do not subtract a 10-year breakeven from an overnight policy rate and label it an observed real policy rate.

### 3.5 Identities and dependence

Nominal yields, TIPS yields and their breakeven difference do not represent three independent confirming signals. The real-yield/inflation-compensation decomposition is an accounting relation with measurement conventions, while inflation compensation includes risk and relative-liquidity effects (S3). Duplicate transformations must share an evidence-family identifier. Attribution models and predictive models must disclose shared inputs. Asset behavior used to classify a shock cannot also be counted as independent evidence that the asset will subsequently respond.

## 4. One architecture, existing owners

```text
Existing licensed collectors / releases / market stores
    -> existing PIT and correction-safe domain owners
    -> curve, dollar, labor, inflation, credit, liquidity, oil and policy evidence
       |                         |
       |                         -> Regime One owned forecast / transition models
       -> TXI mechanisms         -> existing Evaluation OS / forecast ledgers
       -> F10 historical studies and distinct episode outcomes
    -> Rates & Inflation Command: additive regime_outlook research projection
    -> existing transmission surface / Macro Command deep link
    -> existing Brain evidence consumer / existing research and portfolio workflows
```

### 4.1 Source and output ownership

The **new user-facing projection** is proposed as `rates_command.v1.regime_outlook`, with a versioned nested schema. It is derived and rebuildable, not a new authoritative market state. The existing builder/publication path remains the only writer of its artifact. Its absence must be backward compatible for all existing consumers.

Probabilities and forecast trajectories belong to the existing Regime One owner through a separately reviewed additive contract. Do not rename `forward.p_quad` to make it a future forecast, and do not reuse the already ambiguous `next_quad_probs` name. Regime One's existing risk/gross mapping and every scoring consumer remain unchanged.

TXI retains mechanism/episode identities. Evaluation OS retains study/trial/outcome and promotion records. Existing forward ledgers retain issuance identity and nightly advancement. Research/portfolio objects retain saved-user-state ownership. Executive OS retains all work lifecycle, placement and continuation.

No new `macro-regime-service`, scheduler, database, RAG corpus, standalone forecast log, source registry or generic orchestration service is authorized by this design.

### 4.2 Minimum research projection

Each projection carries:

- `schema_version`, explicit `analysis_cutoff`, `built_at`, and per-input source/version references;
- `current_state`: named existing owner reads, including tape/economy disagreement;
- `evidence`: units, observation/reference date, release/available time when known, source clock status, freshness, correction identity and coverage;
- `conditional_paths`: stable scenario identifiers, assumed conditions, supporting/contradicting/unknown evidence, mechanism references and next observable discriminators;
- `forecast_distributions`: only from an admitted forecasting owner; otherwise a typed absence explaining what is missing;
- `historical_comparisons`: selected episode identities, selection-method version, true sample count and outcome distributions, or an honest absence;
- `conditional_exposures`: descriptive or tested response objects, with horizon and evidence tier;
- `authority`: display/research only in the initial release; no rank, size, gate, escalation or trade permission.

This is a contract specification, not a fabricated emitted artifact. Final exact field names must align with the existing schema owner and current consumer census before implementation.

## 5. Time, missing data, corrections and rights

### 5.1 Clocks

Preserve, rather than manufacture: observation/reference period; official release time; first availability to Mastermind; ingestion time; analysis cutoff; model training cutoff and version; forecast issue time; outcome observation time; and later correction time.

An ALFRED vintage date supports a date-level historical information set, not an exact intraday timestamp. A reconstructed feature history may be useful without being an observed publication history. A model that filters observations causally but estimates its parameters from later data is not a point-in-time historical forecast. Older rows lacking provenance remain explicitly unverified. See S4 and the retained #7015 contract.

### 5.2 No false calm or false freshness

Missing, not covered, stale, malformed, future-dated, conflicted, provisional, insufficient history and rights-blocked are distinct. No unknown value becomes zero, flat, unchanged or a negative condition. A current build timestamp cannot refresh an old source. A cross-series spread uses an admissible common date and documents the lag; it never pairs independently latest values without disclosure.

Partial coverage should still give a useful partial comparison. It must not issue a fully observed joint forecast. Missingness patterns are recorded and tested, rather than silently renormalizing a composite over surviving inputs. A source outage cannot generate a regime transition.

### 5.3 Corrections

Rebuild descriptive current projections from corrected owner data. Preserve original issued forecasts and their information-set fingerprints. Link later corrections to them, and display original-versus-corrected evidence separately. Do not retroactively rewrite what the system knew or move the issue time to improve a score. Training labels and revision policy are preregistered per target.

### 5.4 Rights

Use current first-party/licensed collection paths. FRED availability does not by itself establish commercial redistribution rights for every underlying series. Source entitlements, historical rights, derivative rights and public-versus-operator visibility are checked by existing owners before adding a feed. DXY/futures/foreign OIS and commercial research receive particular attention. No new provider subscription or paid compute is authorized by this record. Public Brain receives shipped product evidence, not internal source code, operational notes or private research documents.

## 6. Regime representation and model ladder

### 6.1 Preserve dimensions

Represent economic activity level and momentum; inflation level, momentum, breadth and anchoring; real/nominal/term-premium curve conditions; dollar/funding conditions; credit/liquidity; oil shock composition; actual policy decisions and conditional communications; and market technical confirmation.

Do not cross every label into hundreds of sparsely observed joint states. Use a compact economic state representation with continuous conditioners and hierarchical shrinkage. Existing house quadrants are house definitions, not NBER recession declarations. The label "stagflation" on a market-proxy quadrant is not sufficient evidence of a macroeconomic contraction.

### 6.2 The target contract comes before fitting

For every estimator freeze: target owner, exact target definition and version, horizon, issue cadence, information set, available sample, outcome-vintage policy, missingness rule, loss function, baselines and promotion bar.

The first regime target should be the **future published slow-economic regime under the existing owner's fixed definition**, separately labeled from the future market-proxy regime. If historical records do not support that target, an explicit counterfactual replay under frozen owner code may be researched, but it must be labeled reconstructed and cannot be spliced into an issued-forecast track record.

Additional continuous targets can cover future changes in selected real/nominal yields, inflation and dollar indices. They are separate forecasts with their own units, horizons and evaluation. They do not automatically justify an asset-return prediction.

Forecast horizons are initially 1/3/6/12 calendar months, anchored to a declared target-date rule. Market-session horizons used for asset outcomes are named separately. The 12-month model is not a repetition of a one-month point forecast under an unstated assumption.

### 6.3 Baselines first

Compare the existing admitted owner, persistence/no-change, unconditional historical frequencies and an empirical Markov baseline fitted only on the training window. Do not benchmark a persistent four-state problem only against a uniform 25% probability.

First challenger: regularized transition models conditioned on a small preregistered set of real-rate/curve/dollar/labor/inflation/credit variables, with shrinkage and explicit missing-data treatment. State-dependent transition probabilities are a method, not evidence of skill.

Only after incremental benefit is demonstrated, consider duration-dependent/semi-Markov behavior, dynamic-factor/state-space forecasts for mixed-frequency releases, or coherent joint curve trajectories. Dynamic factors are useful methodological references for asynchronous releases and dimensionality reduction (S5); they are not a reason to replace working domain owners. The recent TVTP paper in S10 is a research candidate with identification cautions, not a production certification.

### 6.4 Coherent paths

A multi-horizon fan should come from a coherent model or explicitly disclose separately estimated marginals. Probabilities of a state at a future date, probability of ever entering a state before that date, transition hazard, and expected dwell time are different outputs. Do not derive dwell time from a constant-transition formula and present it as duration-sensitive.

Joint rate scenarios must respect curve conventions and economic identities. They may include common factors plus maturity-specific residuals. Independent sliders for nominal, real and breakeven yields cannot simultaneously violate their defining relation. Market-implied scenarios and real-world statistical forecast probabilities stay labeled separately.

### 6.5 Environment strength

Publish separate measures of **magnitude, momentum, breadth, persistence and confidence**. State confidence and asset-response confidence are also distinct. Do not compress them into one cross-domain health/conviction score. A severe low-probability tail is not the same object as a mild high-confidence environment.

## 7. Policy, oil and technical evidence

### Policy

Separate the Fed's observed actions, official communications, conditional reaction framework, market pricing and the statistical forecast. Equity weakness enters through observed financial conditions and economic channels, not an assumed equity-price guarantee. The Fed's stated mandate is employment and price stability (S9).

For administration policy, reuse the existing event owners to distinguish proposed, announced, enacted, implemented, challenged, stayed and reversed actions. Quantify observable fiscal/trade/energy exposures where data support it. Treat intentions and timing narratives as sourced, contestable research hypotheses. No LLM-generated probability of a political intervention, geopolitical escalation or rescue.

### Oil

Distinguish demand-led, supply-led, precautionary/geopolitical and unexplained moves; allow mixed and unknown. Use existing price, curve, inventory, production, physical and policy evidence. A rise in spot oil alone does not identify the cause. The discontinued New York Fed oil model is a methodology reference, not a live feed (S6). Do not multiply a supply/demand label into asset weights without a separately admitted response model.

### Technicals

Reuse the existing yield-momentum/canon/market owners for multi-timeframe trend, turns and confirmation. A technical reversal can precede slow data, so disagreement is an explicit competing read. Technicals condition timing hypotheses; they do not erase unfavorable fundamentals or turn a descriptive market label into a forecast. Separate yield direction from bond-price direction, and keep security duration/convexity with the asset response.

## 8. Mechanism and historical research memory

### 8.1 Extend TXI, not another graph

Each relevant relationship should retain mechanism, sign, lag, regime conditions, data source, alternative explanations, supporting and contrary studies, known examples, failed examples, and empirical confidence where actually estimated. A graph edge must declare whether it is an accounting identity, a theoretical channel, an observational association, an identified causal estimate, or a proposed hypothesis.

Shared origins are de-duplicated. A persuasive chain is not a causal identification strategy. LLMs may synthesize properly licensed research and propose/refute hypotheses for review; they do not manufacture coefficients, numeric confidence, causal identification or authority. Existing CHF/TXI proposal, review, episode and promotion machinery is reused.

Window failure must be described at its tested altitude: "the 22-session turn did not occur" does not mean "a durable peak is impossible." Preserve both the instrument verdict and the live market behavior, consistent with current house law.

### 8.2 Historical comparisons

Select analogues using only pre-outcome features at the comparison date. Match starting levels, path shape, velocity, labor/credit conditions, policy configuration and relevant valuation/positioning where available. Fit normalizers and feature selection inside each training split. Explicitly separate similarity search from estimated causality.

De-duplicate clustered dates into distinct episodes and preserve an out-of-sample outcome window. Exclude unavailable/delisted instruments only with disclosure; include survivorship limits in all cohort conclusions. Show nearest failures and divergent outcomes, not only memorable successes. Display effective episode count, selection distance, coverage, era and outcome quantiles. No sufficiently comparable sample is an admissible answer.

Historical cases motivating the Chairman's question, including the contrasting bond/metals paths around 2018-2019 and 2022, belong in the acceptance set. They are not automatically independent test cases after being used to design the rule. Add preregistered counterexamples and blind holdouts. Do not force pre-TIPS history into an observed real-yield dataset with an unlabeled proxy.

### 8.3 Asset responses

Estimate responses separately by asset, horizon and mechanism. Report total-return conventions, cash benchmark, carry, drawdown, distribution and uncertainty. Bonds, gold, silver, broad equities, defensive sectors, small caps, semiconductors and the dollar must not share one untested response coefficient.

A correct economic forecast is not enough: prices may already reflect it, and valuation, starting yields, positioning, supply and idiosyncratic fundamentals matter. Conditional exposure context is useful before trade authority. Single-name and sector projections must reuse security/portfolio identities and identify uncertain betas. No price forecast, trade rank or position size is inferred from a narrative-only edge.

## 9. Evaluation and learning contract

### 9.1 Point-in-time evaluation

Use anchored/rolling walk-forward evaluation with all feature transforms, labels, hyperparameters and calibration fitted inside the training window. Purge overlapping forward labels and apply a horizon-aware embargo. Distinguish selection data, untouched test data and forward-accrual results. Block-bootstrap at episode/appropriate time-block level; 1,000 adjacent daily rows do not become 1,000 independent crises.

Report Brier and log scores for categorical distributions; reliability and resolution; transition detection timing and false alarms; duration error where forecast; and proper interval/density scores for continuous paths. Evaluate against all preregistered baselines, including persistence. Report per-era/per-regime degradation, sample counts, calibration drift and abstention coverage. Multiple-comparison control and negative findings survive model selection.

Predicting another model's changing label can become self-referential. The evaluation report must state whether the target is an operational house label or an external economic observable, and must not promote success on the former as proof of the latter.

### 9.2 Separate advancement gates

- **Research/context release:** accurate inputs, time semantics, useful analysis, no unauthorized forecasts or capital effect, real consumer and UI proof. No standalone-alpha gate is required merely to display context.
- **Forecast release:** named target/horizon, reproducible PIT evaluation, calibrated uncertainty, comparative skill or explicit experimental status, immutable forward issuance, model/feature/version provenance.
- **Asset-response claim:** separate response evaluation, horizon and costs/carry conventions, uncertainty and selection disclosure.
- **Capital authority:** a future explicit owner promotion under current house law; not granted by this architecture or by a successful display/forecast release.

Do not hide failed performance behind the word experimental indefinitely. Publish the measured result, keep the baseline champion when appropriate, and demote or retire the failed construction without destroying its research record.

### 9.3 Instrumentation

Use existing analytics, not a new tracking plane. Measure orientation-to-scenario completion, evidence expansion, analogue/counterexample inspection, saved thesis/watch completion, return visits and correction visibility. Analyze whether the user can answer the motivating question, not simply whether a graph was clicked. Learning includes user utility and model performance; neither substitutes for the other.

## 10. Experience architecture

### Main journey

1. **Now:** a plain-language statement with dated coverage and major disagreements. No large unsupported confidence number.
2. **What changed:** source changes versus revisions versus market repricing; explain the material mechanism without ranking by feed failure.
3. **Possible paths:** a small fixed set of competing conditional cards; observed supporting/contradicting/unknown evidence; what would change the assessment; a separate forecast panel only when admitted.
4. **History:** comparable episodes, path distributions and counterexamples with honest sample size.
5. **Exposures:** conditional asset/portfolio implications and uncertainty, not an unearned allocation instruction.
6. **Watch:** save the research object or create an existing-owner alert with the same evidence references.

The first surface is `transmission.html`, not a new route. Macro Command should deep-link/project it through its existing navigation owner after integration. The first machine consumer is the existing Rates & Inflation artifact reader; later Brain propagation must extend the already discovered reader, not create an extra Neural Web route just for visibility.

### Visual/interaction floor

Use the actual product design system and canonical components. Dark is an instrument-like command center; light is a research workspace with its own material hierarchy. Shared semantics, spacing and navigation, not merely inverted colors. English and Chinese convey the same probability/uncertainty distinctions. Primary conclusions and key caveats must not depend on hover. Mobile touch, keyboard, reduced motion, unavailable data and source corrections are real states, not screenshot-only fixtures.

Do not modify shared Lens/theme behavior in this vertical. Consume its accepted fixes and test the full page. No runtime-injected stylesheet, second navigation family, or graph-first wall of nodes.

## 11. First independently useful vertical: rates-peak path comparison

### Mission

On the existing transmission surface, compare the conditions for a durable easing of real-rate pressure with the main alternatives, using actual existing owner evidence and explicit missingness. The user should leave knowing what is currently supported, what is contradicted, and which observation would discriminate the paths.

### Initial path cards

| Stable research path | Assumption under examination | Essential discriminators |
|---|---|---|
| `orderly_disinflation` | Inflation pressure eases without broad deterioration in labor/credit. | Inflation composition and expectations, hiring/income/claims, credit conditions, real-rate velocity. |
| `growth_deterioration` | Lower yield pressure comes with weakening activity and financing conditions. | Labor breadth, real activity, credit spreads/funding, earnings context and dollar behavior. |
| `renewed_inflation_pressure` | Price pressure broadens or persists, rather than only a transitory oil print. | Inflation breadth, wages/services, breakevens with liquidity caveats, policy repricing and oil mechanism. |
| `long_end_premium_shock` | Long-end yields rise for reasons not captured by the near-term policy path alone. | Curve decomposition, term-premium model evidence, issuance/demand context, cross-model disagreement. |
| `technical_pause` | A price/yield reversal is visible, but durable fundamental confirmation is incomplete. | Multi-horizon yield turns, market breadth, positioning and subsequent macro confirmation. |

These cards are not mutually exclusive macro states, exhaustive outcomes, a ranking, or a probability simplex. Do not normalize their condition counts to 100%. A later quantitative forecast uses its own explicit target partition; its probabilities are not assigned to these overlapping narratives by convenience.

### Exact implementation boundary to freeze at pickup

- Extend the existing RIC composer with an additive `regime_outlook` block and a pure, deterministic helper if decomposition warrants one. The helper belongs to the same owner and is not registered as a new state engine.
- Reuse currently governed transmission, forex, regime, market-state and workspace snapshot inputs. Fresh-read the exact workspace manifest and source fields; do not guess paths or rely on the new build timestamp.
- Expose nominal/real/breakeven changes, dollar direction, labor/credit/inflation evidence and term-premium uncertainty with their individual source clocks. Missing labor or oil causality remains an unknown discriminator, never a fabricated reassuring condition.
- Every condition names its input and calculation or owner verdict. Reuse reviewed thresholds; a new threshold requires its own disclosed rationale and research status. Do not invent hard-coded percentages to make a card decisive.
- Render a compact comparison in the existing template/build path, using the same projection the machine consumer receives. No third artifact writer, new endpoint or model invocation.
- Add targeted producer-to-render tests and only the owning CI scope needed to execute them. No CI framework rewrite.
- Preserve existing fields, scores, filters, allocation, ledger advancement and user-state contracts byte-semantically outside the bounded addition.

### Required proof

A real current input bundle travels through the existing builder to the served transmission page and the declared machine reader. Demonstrate one supported condition, one contrary condition and one genuine unknown from the actual data. Also exercise old-policy/new-market timestamps, missing labor, incompatible curve dates, malformed numeric values including booleans and non-finite values, future timestamps, source revisions, and valid zero/negative yields.

The deterministic computation must not perform network access, model fitting or persistence. Never invoke a nominally read-only production helper without checking its side effects; #7024's evidence already identifies why `master_brain.run(persist=False)` is not sufficient proof of no ledger mutation.

Browser acceptance: actual desktop/mobile EN/ZH x dark/light, touch and keyboard, no hidden required caveats, no horizontal overflow, no console/request failures, correct source navigation and no duplicate rendered interpretation. Confirm the output after the normal deployment, not only a fixture/server preview. Record exact source/release identities and compare all scoring/allocation outputs before/after.

### Independence and dependencies

The descriptive path comparison does not wait for a new predictive model, a complete global data expansion, or #7015's historical forecast proof. It does wait for lawful source custody, admitted input semantics, architecture review, real integration and consumer/browser proof. It may not edit the incumbent #7024 worktree, `master_brain.py`, shared Lens source, or Risk Radar source. Forecast-grade history later consumes #7015 after acceptance; briefing propagation later consumes #7024 after acceptance.

## 12. Delivery sequence and capability ledger

These are scope slices inside existing owners, not a second execution queue. Placement/lifecycle remain Executive OS facts. The sequence does not assign an unbound worker.

| Slice | New capability | State at authoring | Acceptance boundary |
|---|---|---|---|
| A0 | Recover intent, source owners, research and this architecture | SPEC_ONLY | Independent architecture verdict; correct durable records; no claim of product delivery. |
| R1 | Compare rates-peak paths from dated evidence on the existing surface | NOT_BUILT | Producer + machine consumer + live user journey and negative-state proof from real inputs. |
| R2 | Horizon-specific economic-regime forecast benchmark and first challenger | NOT_BUILT | Exact targets, PIT walk-forward report, preserved baseline and negative results, current issue with no invented historical issuance. |
| R3 | Historical analogue/outcome comparisons and counterexamples integrated with R1 | PARTIAL substrate; new joined journey NOT_BUILT | Honest distinct-episode selection, no lookahead, real historical distributions in the same product. |
| R4 | Broader real-curve/relative-dollar and coherent joint path capability | PARTIAL substrate; expansion NOT_BUILT | Source/rights admission, correct curve math, cross-model uncertainty, measured incremental forecasting benefit where claimed. |
| R5 | Conditional asset/portfolio exposure and existing-owner saved watches | PARTIAL substrate; joined workflow NOT_BUILT | Actual portfolio journey, separate asset-response evidence, no unintended rank/size/gate effect. |
| R6 | Forward calibration, drift response and user-utility learning | PARTIAL substrate; program proof NOT_BUILT | Existing ledgers/analytics expose issued outcomes, comparative skill, corrections, abstention and user completion. |

R2 and R3 can be investigated in bounded disjoint work after R1 semantics freeze, but do not fan out several speculative models or create duplicated datasets. First exploit existing data and validators. When a slice finishes, immediately advance the next unblocked dependency within the same product intent. Do not convert an idle period into an unrelated cleanup campaign.

### Capacity and review

Default bounded implementation/research avenue: Terra. Harder, architecture-sensitive but bounded statistical implementation: CTO Sol. Independent specialist review may use Opus/Grok where available and appropriate. Fable is reserved for a genuinely unresolved cross-owner principal question, not every file edit. No numbered account is assigned by this record. No Chairman account allocation is required. Unplaced work is WAITING_CAPACITY / needs_placement; no worker-specific watcher or START is claimed.

## 13. Release and final acceptance

For every vertical: exact scope -> current source/ownership reconciliation -> reviewed design -> implementation -> adversarial intent/code review -> required concluded checks -> ordinary merge -> existing publication/deployment -> real user and machine proof -> durable closeout.

An integration check does not require an ancestry-only rebase when immutable accepted semantics remain compatible; use the current release/review-reuse law. Genuine conflicting code needs reconciliation by its owner, not a bypass. Never label pending CI green or use a preview failure as permission to bypass the existing release path.

The overall program is complete only when:

- **Truth:** source clocks, revisions, rights, curve identities and coverage are reliable.
- **Intelligence:** structured evidence, mechanisms, competing paths, tested forecasts and historical comparisons are useful and consistent.
- **Product:** a real user can complete the flagship question, inspect implications and save a watch/thesis on the existing surfaces.
- **Learning:** issued forecasts and user utility are measured; failures and changes are discoverable.

No guarantee of market direction is part of acceptance. Meaningfully calibrated uncertainty and an honest baseline can be the correct outcome. A sophisticated but unhelpful model is rejected; a useful contextual tool remains valuable without capital authority.

## 14. Current execution boundary and exact continuation

The protected Skillpack loaded successfully at the pinned commit and is compatible. The Executive connector's state request failed with an MCP tunnel 404, so no fresh runtime state, job admission or dispatch is asserted. Device discovery is not host readiness: the MacBook answered ping but its configuration read failed and the attempted read-only shell preflight was safety-blocked. No equivalent bypass was attempted. The Studio later advertised a new connection session, but its direct ping still timed out. No host files, processes or incumbent source were modified by this architecture operation.

**Primary next action:** independently review this design and the R1 input/consumer boundary, then place exactly one eligible bounded R1 implementation through the existing owner/capacity path after actual host/source access is qualified. The R1 packet must pin the current composer, workspace manifest, template/builder and owning tests; return unresolved input joins rather than invent them. No second general audit or replacement program charter is needed.

**Independent retained dependency:** the existing #7024 owner must recover the SAME Studio/source context, reconcile its prior local effects and pending read-only preflight, publish the already applied repair on the same branch, and complete current-head/Lens/production proof. This architecture does not ask a new worker to recreate that patch. #7015 remains its own temporal-history carrier.

This source record is the continuation anchor, not an Executive runtime admission. Current gate failure must not be hidden by calling a plan a shipped engine.

## 15. Primary research and workflow references

All external sources below were accessed through live web research on September 12, 2026. These are summarized methodology/workflow references; no vendor data, private implementation or proprietary text was copied.

- **S1 - US Treasury, Treasury Yield Curve Methodology (updated February 18, 2025).** Par-curve construction and indicative quote timing; prevents treating CMTs as observed zero-coupon rates. https://home.treasury.gov/policy-issues/financing-the-government/interest-rate-statistics/treasury-yield-curve-methodology
- **S2 - US Treasury, Interest Rates FAQ.** CMT bond-equivalent/par conventions, semiannual coupon basis and no daily Treasury zero-coupon publication. https://home.treasury.gov/policy-issues/financing-the-government/interest-rate-statistics/interest-rates-frequently-asked-questions
- **S3 - Federal Reserve, Tips from TIPS: Update and Discussions (May 21, 2019).** Inflation compensation includes expected inflation, inflation-risk premium and relative TIPS liquidity effects; inferred real rates and term premia are not direct observables. https://www.federalreserve.gov/econres/notes/feds-notes/tips-from-tips-update-and-discussions-20190521.html
- **S4 - Federal Reserve Bank of St. Louis, ALFRED and real-time periods.** Vintage availability and later revisions; date-level vintages do not supply an undocumented intraday arrival time. https://fred.stlouisfed.org/docs/api/fred/realtime_period.html ; https://alfred.stlouisfed.org/help/downloaddata
- **S5 - New York Fed Staff Nowcast / O'Keeffe and Petrova, Component-Based Dynamic Factor Nowcast Model, Staff Report1152 (April2025).** Mixed-frequency real-time processing, density output and component decomposition as methodological references; not an instruction to build a second nowcast. https://www.newyorkfed.org/research/policy/nowcast/ ; https://www.newyorkfed.org/research/staff_reports/sr1152
- **S6 - New York Fed Oil Price Dynamics Report.** Distinguishes demand, supply and residual contributions. Discontinued November2023: not a current production dependency. https://www.newyorkfed.org/research/policy/oil_price_dynamics_report
- **S7 - New York Fed Treasury Term Premia.** ACM supplies model-estimated components, not directly observed premium truth; preserve model provenance and uncertainty. https://www.newyorkfed.org/research/data_indicators/term-premia-tabs
- **S8 - BIS Working Paper695, The dollar exchange rate as a global risk factor.** Evidence on bank-credit/investment channels alongside the standard trade channel; neither a universal coefficient nor a current trading signal. https://www.bis.org/publications/working-paper-695-dollar-exchange-rate-global-risk-factor-evidence-investment
- **S9 - Federal Reserve, The Fed Explained: Monetary Policy.** Employment/price-stability goals and the financial-conditions transmission channel. https://www.federalreserve.gov/aboutthefed/fedexplained/monetary-policy.htm
- **S10 - Modee et al., Multi-regime Markov-switching models with time-varying transition probabilities, arXiv2605.14976 (May2026), abstract inspected.** Research candidate; the authors report identification/specification cautions. Full methodological replication remains unperformed. https://arxiv.org/abs/2605.14976
- **W1 - Macrobond official product description.** Workflow reference: governed time series, revision/PIT history and reusable research. Marketing claims are not independently verified performance. https://www.macrobond.com/
- **W2 - LSEG Datastream and Macroeconomics.** Workflow reference: economic-event monitoring, hypothesis testing, scenarios and reusable dynamic charts. No access, license or vendor capability parity is claimed. https://www.lseg.com/en/data-analytics/datastream-and-macroeconomics

## 16. Supersession scope

This baseline adds an explicit integrated future-path research capability to the existing RIC/Market OS product, and clarifies the route from context to forecasting to asset evidence. It does not supersede existing source-writer custody, accepted domain formulas, DNR prohibitions, forecast/ledger identity, release gates, or the Market Ontology Meta-CEO source split. Any later change to those boundaries requires a precise owner ruling and separate evidence, not a broad reading of the word autonomous.
