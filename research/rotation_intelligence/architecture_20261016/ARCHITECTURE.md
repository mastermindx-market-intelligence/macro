# Architecture: conditional opportunity, risk and execution

Date: 2026-10-16. Status: pre-implementation design candidate for PR #9507. This document proposes interfaces and experiments; it does not register a model, authorize investment use, or change existing source permissions. Read [README](README.md) and [RESEARCH_DESIGN](RESEARCH_DESIGN.md) together.

## 1. The capability, expressed as decisions

The user should be able to ask: which exposures offer the strongest forward opportunity at my horizon; is that opportunity a broad sector, an industry, or an overlapping theme; what changed; what would invalidate it; is equity risk worthwhile relative to bills; and which stocks add something beyond group beta?

The answer has four distinct layers:

1. **Measurement:** what can be observed about prices, participation, economic evidence and fund activity as known at this time?
2. **Forecast:** what outcome distribution is supported for a specified population and horizon, conditional on those admissible observations?
3. **Policy:** what feasible action improves the mandate's objective after uncertainty, costs, liquidity and aggregate risk are considered?
4. **Expression:** should that action use a sector ETF, industry instrument, or a stock basket with independently qualified residual contribution?

Each layer can fail independently. A measured sector leader can have an unavailable forecast. A positive forecast can justify no trade after costs. A good sector selection can be best expressed by an ETF rather than the supposedly strongest stock.

**North-star output is economically useful, calibrated adaptation—not a forced winner on every screen refresh.** Ties, an unranked set, unsupported conditions and no-action/bills must be first-class outcomes.

## 2. Extend the incumbent architecture

Current source anchor for this design: Macro `4ae7f2ac4c58e6e93945a6f09313bcaadba5709e`. Exact source anchors from the initial assessment remain in [ASSESSMENT](ASSESSMENT.md). The current programme workstream is `agentos/workstreams/WS-LEADERSHIP-ROTATION-INTELLIGENCE.md`.

| Responsibility | Incumbent boundary to reuse | Proposed work | Explicitly not created |
|---|---|---|---|
| Source facts, snapshots, rights and availability | Existing Data OS and collectors, including sponsor/price/macro/filing owners | Qualify source contracts and versioned read adapters | New market-data warehouse, parallel collectors or rights authority |
| Security, group and exposure identity | Existing Theme Graph / GMI / MarketOntology owners | Dated partition membership and overlapping economic exposures | A second theme graph or permanent alternative symbol map |
| Regime context | `quad_vector`, `regime_vector`, `regime_prior` and their existing producers | Qualified causal contexts, source-specific freshness and exposure interactions | A competing quad model, macro truth or calendar |
| Leadership measurements and observed transitions | Rotation Command, Sector Central, `leadership_rotation_context` | Reuse measured objects and existing observation/event references | New rotation-event ledger, replacement detector or parallel schedule |
| Prediction and scientific qualification | Existing LR-W6, Research Factory/evaluation owners, `ResearchEstimate` | Candidate estimands, simulation qualification, admitted predictor adapters | A second evaluator, model registry or automatic research promotion service |
| Portfolio policy | Existing portfolio/risk owners and mandate controls | Cost-aware group/cash policy and look-through constraints after qualification | LLM-generated sizing or a parallel account/portfolio state |
| Stock expression | Existing Prophet/company/theme exposure and evaluation surfaces | Residual stock-selection tests against the group basket | Another independent stock ranker masquerading as a sector feature |
| Human and chat consumers | Existing Sector Intelligence/Rotation Command/Terminal and grounded chat contracts | Horizon-specific evidence, uncertainty, changes and invalidators | A separate dashboard with its own truth or recommendations |
| Dispatch and durability | Existing runtime/Fabric/GitHub/Agent OS owners | Bounded source/research jobs with immutable inputs and retained results | New job queue, watcher, lifecycle, retry or memory plane |

These are architectural responsibilities, not claims that every adjacent integration is already built or production-qualified. The initial target is additive research through existing boundaries.

### Preserve the measured-object contract

`engine/leadership_rotation_context.py` explicitly separates `GroupMeasurement`, `TransitionObservation` and `ResearchEstimate`. Its research identity has eleven fields: target, horizon_sessions, origin, exit_rule, model, protocol, cohort_id, training_cutoff, supported_population, uncertainty_definition and evidence_tier. The probability defaults to an unmeasured marker; valid numeric probabilities require complete identity. Source: lines 824–846 and 1014–1061 at the design pin.

A structurally valid ResearchEstimate is **not** proof of model admission. The independent source-use and scientific owner still determines whether it can be produced and consumed. GroupMeasurement's display restrictions remain unchanged. A future distribution-valued extension belongs in a versioned additive contract under that owner, not by inserting a forecast into an observed metric or toggling its rank permission.

## 3. Four economic clocks, three decision horizons

Keep macro conditions, industry supply/capital cycles, corporate earnings/revisions and market-price structure as separate evidence clocks. A synchronized dashboard refresh does not make quarterly filings intraday observations.

| Horizon | Main question | Candidate inputs | What must not happen |
|---|---|---|---|
| Strategic, roughly one to several quarters | Is the opportunity set improving, and is the economic thesis durable? | Capacity, competition, pricing, orders, financing, earnings expectations, macro vintages | Historical revised information cannot impersonate early knowledge |
| Tactical, candidate 5/20/60 sessions | Which groups may outperform, persist or deteriorate over an actionable holding period? | Relative return, breadth change, revisions, admitted fund activity and continuous regime context | Three correlated technical indicators must not count as three independent confirmations |
| Execution, session and intraday | Is the observation current and is this a reasonable way to enter or reduce the qualified exposure? | Aligned bars, spreads/liquidity, overnight versus regular-session moves, event risk | An intraday price move cannot refresh a stale fundamental thesis or manufacture a new 20-day forecast |

The exact horizons are candidate protocol parameters, not interchangeable product labels. The existing hourly/minute measurement work must retain its own source-clock and production proof.

**Existing DNR remains binding:** no new rotation×cycle-confluence gate, LLM detector, connect-flow gating or parallel schedule. This package investigates economically distinct information and existing measurement interfaces; it does not rebrand a prohibited construction. Any later proposal materially touching such a boundary requires explicit adjudication of that exact construction and evidence, not a broad inference from this document.

## 4. Representation of the opportunity set

### Partitions and overlapping themes are different objects

A sector/industry classification is normally treated as a partition within a specified taxonomy/version. Economic themes are overlapping exposures: one security can express several themes with different evidence quality. Both use incumbent identity owners, and both require dated, known-at membership.

Maintain an exposure matrix A mapping feasible instruments to underlying securities or economic risks. A policy weight vector w produces look-through exposures A·w. Splitting the same holdings into several theme labels must not increase the apparent number of independent bets. Coverage shortfalls must remain explicit; do not silently renormalize an incomplete exposure map into a fully known portfolio.

A group's **opportunity quality** and the portfolio's **total risk budget** are separate decisions. Narrow participation may justify a narrower candidate list and a smaller equity budget simultaneously. The rule must not be “low breadth means concentrate more.”

### Two index products

A current-composition analytical index asks how today's members have behaved; it may be useful for descriptive timing. A point-in-time investment index asks what an implementable membership/weight rule could have owned at each date. They must have different evidence modes and cannot share an implied backtest qualification.

The first investment baseline uses available broad-sector ETFs at their real inception, with a separate synthetic/industry transfer protocol. A sector and its overlapping themes must not be counted as independent observations in hypothesis tests or as additive diversification in a portfolio.

## 5. Forecast architecture: start simple, become complex only for a reason

### Forecast the joint opportunity, not isolated scores

The proposed target is a horizon-specific distribution of net opportunity. For group g, origin t and executable entry e(t), define a terminal date u(t,h). A research return label can be a log-wealth difference:

`Y[g,t,h] = log(V_g(u)/V_g(e)) - log(V_b(u)/V_b(e))`.

The benchmark b is explicitly identified; an equity benchmark and a bill benchmark answer different questions. This label is not a trade policy: variable exits, waiting, rebalancing and costs need their own actual cash-flow paths.

A useful forecast needs expected opportunity, downside, uncertainty, and the probability of beating specified alternatives. Its supported population, horizon, model version and source cutoff are inseparable from the values. Do not independently forecast top-three probabilities that cannot be reconciled with a joint cross-section; use a qualified joint distribution or another tested coherent ranking method.

A low-variance estimate with high data coverage can still be economically wrong. Separate measurement confidence, parameter/model uncertainty, outcome variability, and out-of-support conditions.

### Model ladder

**M0: transparent baselines.** Broad index, equal-weight eligible sectors, a frozen relative-momentum rule and an absolute-trend/bill rule. They establish whether complexity earns value at all.

**M1: small regularized conditional model.** Pool information across sectors and shrink sector-specific slopes toward shared coefficients. Candidate continuous interactions combine an exposure with a macro change, rather than splitting a small sample into quad × real-rate × breadth × sector cells. Sector-specific evidence is allowed only where support exists. No coefficient is interpreted causally without a separate identification design.

**M2: constrained nonlinear challengers.** Shallow boosted trees or other bounded nonlinear functions can test predeclared interactions. They must use the same information, origins, costs, held-out periods and tuning budget as their comparator. Their ability to fit a large stock panel does not establish usefulness in an eleven-sector time series.

**M3: latent exposure and transition challengers.** Time-varying factor structure, causal change-point methods and probabilistic state mixtures may address a specific residual failure of M1/M2. They are not the default infrastructure and do not replace the existing regime owner. A method that explains concurrent prices is not automatically a forward-return predictor.

Model count and tuning attempts are part of the research family. A failed challenger remains a retained result; it is not renamed until a favorable test appears. Literature foundations and transfer limits are in [LITERATURE](LITERATURE.md).

### Continuation and transition

Continuation and early formation are separate prediction tasks. Reuse existing observation/transition references rather than building another stage machine. Candidate eligibility must be defined from information available at origin and must retain later failures, including groups that never confirm.

For transition research, measure the economic value of acting on a candidate, the probability and cost of a false start, and the delay to a frozen confirmation rule. A fixed five-day difference between two detectors does not prove five days of useful advance warning. An early signal may genuinely predict a 20-day move without predicting the next day; monotonic performance across horizons is not a validity requirement.

## 6. A decision policy with bills, uncertainty and no trade

After independent qualification, the incumbent portfolio owner may compare feasible weights by an objective such as expected return minus risk, turnover and uncertainty penalties. The illustrative form is:

`maximize_w E[R_portfolio(w)] - lambda·risk(w) - cost(w,w_prev) - eta·model_uncertainty(w)`

subject to the existing mandate, non-negative/short permissions, exposure, liquidity, concentration, turnover and cash constraints. This is an architectural objective, **not an approved sizing formula or numerical mandate**. Tail risk and liquidity constraints cannot be replaced by a covariance penalty alone.

For the initial policy study, use long-only unlevered instruments and bills; no short borrow assumptions or account-specific sizing are needed. Keep short/hedged extensions in separately admitted research. Use shrinkage or other qualified risk estimation, but recognize that improving covariance does not cure an unreliable expected-return model.

Transaction-cost-aware partial adjustment and no-trade regions are candidate policies. Different signals can decay at different speeds; it may be rational to move gradually toward a durable thesis and not chase a short-lived price impulse. Test this against simple fixed-cadence rebalancing. Do not choose hysteresis to cosmetically smooth the backtest.

Bill returns are actual horizon-matched investment returns, not an annual yield copied into a return field or a zero-cash default. Long-duration government bonds are a separate exposure with duration risk, not a synonym for cash.

## 7. Stock alpha after group beta

Evaluate the group selection and the stock expression separately. The stock-level target is incremental contribution beyond the chosen industry/theme basket and appropriate market/style exposures, not a high-beta amplification of a sector rally.

Candidate evidence includes revision breadth and acceleration, margins/cash generation, economic exposure purity, valuation relative to expectations, order/backlog realization and stock strength relative to the group. Fit nuisance factor exposures using only admitted prior data; never residualize test returns with full-sample betas and call that point-in-time alpha.

Two distinct tests are required: did selecting the group improve the baseline; and, holding the group decisions fixed, did the stock basket improve the group instrument after costs? Report the interaction as well: selecting stocks using future successful groups is a hindsight-conditioned evaluation.

## 8. Product answer and degraded behaviour

The existing journey should show four adjacent but non-substitutable panels: current measured leadership; emerging observations with confirmation/invalidation; qualified horizon-specific opportunity, when available; and permitted portfolio/instrument interpretation. The screen and grounded chat must identify which panel supports each sentence.

A proposed opportunity record displays the supported horizon, probability/return units, uncertainty interval, benchmark, evidence time, contributing mechanisms, strongest counterargument, invalidators, cost sensitivity and qualification status. It may display a candidate set without an exact order when rank uncertainty is material.

On a source interruption, retain last-good display with its original timestamp only when existing policy permits it. Do not carry forward a model's investment permission or silently switch to a different benchmark/model. Missing exposures, unsupported regimes or unavailable bill comparison may make the decision unavailable while descriptive leadership remains visible.

Model-drift and calibration observations belong in the existing evaluation and monitoring owners. Withholding a forecast after a declared falsifier is different from automatically retraining/promoting a replacement. Retraining, publication and allowed use remain separate existing decisions.

## 9. Infrastructure strategy and implementation boundaries

No new always-on service is justified by this design. Use incumbent snapshot references, pure bounded transforms, existing research jobs, existing model/evaluation registration and current publishers. Cache expensive derived features only under the existing owner with a key containing source, membership, method and as-known versions. A cache hit is not source freshness.

Before increasing compute, show which consumer question remains unresolved and why a bounded experiment cannot answer it economically. The research dependency graph in [READINESS_AND_DELEGATION](READINESS_AND_DELEGATION.md) is a plan, not a scheduler. Fabric chooses admitted workers/hosts; the graph does not grant capacity or multiply descendant budgets.

### Design rulings and reopening evidence

| Decision | Rejected alternative | Evidence that could reopen it |
|---|---|---|
| Reuse existing measured/evaluation/identity owners | A new unified rotation service owning all truth | A demonstrated missing capability that cannot be added without violating the existing contract; explicit architecture adjudication |
| Receiver-only baseline first | Assume paired capital migration is inherently superior | Incremental held-out value of donor information under matched receiver inputs and selection |
| Pooled/simple models before deep models | Fit a large unconstrained model to thin sector/regime cells | Reproducible support, stable out-of-sample increment and resource economics |
| Separate total risk from granularity | Automatically concentrate when breadth narrows | A qualified policy study, not an anecdote about concentrated winners |
| Bills and no trade are feasible actions | Always own the least-bad equity sector | A mandate that explicitly excludes cash; still report the counterfactual |
| Preserve uncertainty after selection | Apply marginal calibration to the chosen winner without checking | Selection-aware validation under actual dependency and delayed-label conditions |
| No product implementation in this package | Begin wiring unqualified scores because interfaces are available | Completion of the declared research/data/readiness gates and the next authorized implementation phase |

These rulings freeze the scope of this supplement. They do not supersede the programme's canonical V3, held research phases, live source custody or release protections.
