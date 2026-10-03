# PTSE — machine contracts and frozen-evaluation specification

Version: review proposal 1, 2026-10-03. Parent: Macro #7925. Incorporation target: existing architecture PR #8325. Companion documents: [audit](AUDIT_AND_RECENSUS.md), [masterplan](IMPLEMENTATION_MASTERPLAN.md), [evidence ledger](EVIDENCE_LEDGER.md).

## 0. Status and precedence

This document specifies the contract the implementation should realize. It is **not an already accepted runtime schema, completed preregistration, data qualification or promotion ruling**. Names and numerical defaults below are explicit proposals. Astra and the incumbent scientific/consumer owners should ratify or amend them before the relevant protected outcomes are inspected. Record amendments and their rationale under the existing research/Agent OS owners, not a new registry service.

The original C1-M1 experiment retains its separately frozen specification [G01–G04]. Its constants must not be silently replaced with this proposal. Current Chairman decisions and the scope-specific October 2 Options research amendment govern research permissions [G07–G09]. No schema or successful experiment manufactures score/rank/gate/sizing/alert/trading authority.

## 1. The machine job

PTSE is initially a **derived action-context adapter** over existing market observations and Prophet candidate/strategy/episode evidence. It answers what is observed, what changed, which source limitations matter, and which registered conditional outcomes have actually been estimated. It does not own a new market regime, candidate universe, execution eligibility, portfolio allocation, event calendar, source store or outcome ledger.

The same canonical observation and assessment identifiers must reach every supported consumer. A page must not recompute a different state from the same inputs. Use the existing Macro publication/transport family once W0 identifies the exact accepted seam. The proposed new namespace is `prophet.timing_context/v1-research`; validate namespace ownership before implementation. Do not reuse the already implemented flow field `market_tide` [G14] or MAS-260's intraday Outlook forecast identity [L03].

### 1.1 Identity and time envelope

| Field | Required semantics |
|---|---|
| `schema_version` | Version of the validated wire contract; unsupported versions fail to unavailable context |
| `observation_id` | Canonical deterministic identity over the observation's economic identity, immutable source references and calculation version |
| `assessment_id` | Separate identity for a model/target/action/horizon assessment; no model change may reuse an old assessment ID |
| `market`, `instrument_id` | Existing canonical market/instrument identity, never a bare ticker used as a globally unique key |
| `market_session` | Session from the accepted exchange calendar owner, not retrieval date, filesystem time or a quote's midnight timestamp |
| `decision_at` | Offset-aware UTC instant representing the information cutoff; local exchange timezone is separate metadata |
| `issued_at` | Actual issuance time. A late issuance retains its lateness; it is not backdated into the decision window |
| `source_available_at` | Attributable availability evidence at field/source level; do not synthesize exact times from date-only vintages |
| `valid_until` | Freshness bound fixed by the source/consumer contract and action horizon; not a universal guessed TTL |
| `forecast_horizon_sessions` | Exact positive integer for a registered daily target; interval labels such as “3–10” are presentation only |
| `forecast_end_session` | Exact endpoint resolved from the canonical calendar |
| `strategy_id`, `strategy_version` | Existing strategy identity and frozen version, where the assessment is strategy-specific |
| `holding_horizon_ref` | Strategy's independent holding-law reference; not automatically the forecast horizon |
| `model_version`, `target_version`, `feature_version` | Explicit versions; null with a reason when no estimate is fitted |
| `source_manifest_ref`, `calculation_receipt_ref` | Immutable bounded receipts, not a URL to mutable latest data |
| `supersedes_ref`, `correction_reason` | Existing correction lineage; never permission to erase the original observation or its issued decision |

Canonicalization must be deterministic and reject NaN, Infinity, duplicate identities and ambiguous units. Operational logs may record retrieval attempts separately; those attempts do not remint an unchanged economic observation. Any historical reconstruction has its own evidence grade and reconstruction time, not a fabricated prospective issuance time.

### 1.2 Observation records

Each dimension contains **owner facts**, not an undocumented new blended score:

`feature_id`, `owner_ref`, `source_artifact_id`, `economic_time`, `value`, `unit`, `status`, `known_at_evidence`, `calculation_version`, `source_scope`, `quality`, `coverage`, `limitations`.

Allowed field statuses must distinguish at least `OBSERVED`, `PARTIAL`, `STALE`, `UNAVAILABLE`, `CONFLICTED` and `NOT_APPLICABLE`. Numeric zero is a value, not a missingness marker. Unknown does not become neutral. A partial observation must retain its numerator, denominator, missing mass and eligible population rather than display a full-market percentage.

Trend, participation, volatility, liquidity, catalyst, options, cross-asset and leadership are **candidate information families**, not proven orthogonal factors. Preserve correlated/redundant lineage. An upstream Risk Radar or regime fact must carry its own identity and authority classification; it is not recalculated inside PTSE. Any display label is clearly descriptive and may coexist with conflicting observations.

### 1.3 Optional estimates

An unfitted engine does not emit numeric state probabilities, calibrated confidence or action permission. Use an explicit `estimate_status=NOT_FITTED` and absent estimate object.

A fitted estimate requires the model/target/horizon/population identity, fit-data cutoff, fit/calibration specification, eligible inputs, uncertainty method, source grade and evaluation receipt. Distinguish:

- an expected downside magnitude;
- a binary event probability;
- a return or path quantile;
- a probability distribution over mutually exclusive states;
- a one-step hazard;
- a cumulative transition probability over H sessions.

These are not interchangeable. A state distribution must sum to one within the declared numerical tolerance. Hazards for different nonexclusive outcomes need not sum to one; competing first-transition probabilities do, together with persistence. The schema must say which case applies. Do not add arbitrary probabilities to a narrative state label.

HMM/changepoint outputs must disclose whether they are online filtered estimates. Full-sample smoothed states may be diagnostic pictures only, not historical decision features. A learned state name or mapping fitted after seeing test returns invalidates the affected predictive test.

### 1.4 Candidate/action assessments

Join with the existing candidate plane using `candidate_episode_id`, `strategy_id/version`, `decision_at`, `action`, `target_version` and `horizon`. Resolve canonical IDs through existing owners; do not use approximate ticker/date joins that cross corporate identities or strategy episodes.

Each action assessment contains:

- `applicability`: applicable, not applicable, or unknown, with the incumbent eligibility receipt;
- `evidence_status`: observed-context-only, research-estimate, calibrated-shadow, or abstained;
- separate estimated benefit, downside/path risk and uncertainty where qualified;
- drivers and contradictions linked to owner facts, not causal claims inferred from a feature attribution;
- forecast and policy evidence references, kept separate;
- reassessment triggers and invalidation references;
- explicit authority scope, initially none.

Do not name an unpromoted field `entry_permission=true`. A downstream consumer should have to opt into a separately accepted decision contract before it can alter an incumbent action. Missing optional timing context leaves current Prophet behavior unchanged.

### 1.5 Authority enforcement

Initial values are false for rank, candidate admission, entry gating, plan mutation, alert escalation, sizing, portfolio change, execution and trade. Enforcement must exist at the consumer, not only as JSON flags. A source that unexpectedly returns true is rejected by the context-only consumer; it does not self-upgrade.

Before any later bounded authority, the existing decision owner must bind a promotion receipt to the exact action, population, strategy version, model version, horizon, input requirements and revocation policy. No wildcard “all Prophet” grant. No Portfolio ownership transfer. No LLM-originated numeric signal or escalation [G07].

## 2. Source admission and feature contracts

### 2.1 Evidence grades

Use existing source-owner classifications where present, mapping them explicitly rather than inventing another canonical registry. The research report must at least distinguish:

| Grade | Meaning | Permitted use in this program |
|---|---|---|
| `SYNTHETIC` | Controlled generated fixtures | Software, discrimination and mutation tests only |
| `RETROSPECTIVE_PIT_UNPROVEN` | Real historical values but historical availability, adjustment or membership not fully demonstrated | Labeled descriptive/exploratory research where current scope allows it; no PIT claim, prospective count or automatic model promotion |
| `PIT_QUALIFIED_REPLAY` | Actual source receipts support availability and all feature-specific historical requirements | Registered historical predictive comparisons, subject to untouched-outcome and research permission gates |
| `PROSPECTIVE_FIRST_SEEN` | Observation sealed from real attributable first-seen evidence in its natural decision window | Prospective accrual and, after separate evidence gates, prospective forecasting |

Conformance, source eligibility and economic usefulness are separate axes. A schema-valid object is not automatically any of the latter grades. Retrospective and prospective records may be compared but never pooled under a false common grade. Date-only availability should be represented as an interval/precision claim; if its latest possible availability exceeds the decision, the feature is ineligible for that decision.

### 2.2 Required source manifest

For every family, record source owner, exact existing store/adapter, raw/derived rights, frequency, actual min/max sessions, expected and present observations, missingness by era/market/root, first-availability semantics, revision behavior, source/calculation hashes, population/membership rules and allowed target horizons. Record extraction time and whether the counts are newly measured or inherited from an older inventory.

The manifest must distinguish price session scope from volume/activity scope; split-adjusted structural prices from total-return outcomes; current membership from historical membership; reported OI date from its position date and publication clock; observed trade/NBBO data from estimates; and unsigned gross positioning from sign-assumed dealer scenarios. No raw entitled quote corpus, credentials or confidential account material is committed to GitHub.

### 2.3 Family-specific contracts and starting owners

| Family | Existing evidence/owner to reuse | Admission-specific requirement | Current audit status |
|---|---|---|---|
| Price/trend | Data OS price/time contracts; stores located through the existing source owners and G21 inventory; C1 measurement primitives [G03–G04] | Exact regular-session structural and TR basis, corporate-action vintage, availability, valid calendar, no same-close execution inference | Current full eligible panel not measured by this audit |
| Participation/dispersion | Existing breadth, PIT membership and deep/delisted price owners [G21] | PIT member denominator, delisted price/outcome coverage, sector/cap-tier membership and missing mass through time | Paths exist in dated inventory; current coverage/PIT not assumed |
| Volatility | Existing realized/implied-volatility owners and accepted price returns | Same horizon/annualization/units; expected variance separated from risk premium; no future RV as a feature | Exact current history/availability to qualify |
| Catalyst/event sequence | MAS-204/release/calendar owners [L01]; C1 event evidence [G04] | Schedule known-at, genuine negative coverage, revisions/cancellations, event subtypes and surprise known only after release | C1 historical owner return unresolved in current records |
| Liquidity | Existing market microstructure, funding/credit or qualified proxy owners | Clearly distinguish NBBO/depth from OHLCV proxies; no hidden inventory claims or resurrection of the exact killed reversal construction | Field-level current source map owed in W0/W3 |
| Options/expiry | Options Hub/Theta/live-flow/Options research owners; existing stamp columns [G09,G13,G20,G22] | OI clock, root class, contract scope, settlement, source quality, full-book versus windowed coverage, side assumptions; appropriate derivative units | Real newer retrospective study exists; PIT/production restrictions remain |
| Cross-asset | Existing rates/credit/FX/commodity/financial-condition owners | Cross-market close/availability alignment, revision discipline, currency/unit basis and incremental rather than duplicated regime content | Family-specific readiness not yet measured |
| Leadership/themes | Existing Prophet/GMI/Theme and breadth owners [G17] | Versioned theme membership and leadership cohort; no historical current-membership recomputation claimed as PIT | Existing ownership, current eligible history to verify |

A family that is unavailable has a visible status and does not block unrelated baselines. Build two reporting populations: the broad eligible B0 population and each matched B0/challenger population. Report the difference between them. Complete-case filtering across every possible family is not the default research population.

## 3. Outcomes and action estimands

### 3.1 Preserve the original C1 target

For origin t, with qualified total-return closes T, split-adjusted closes S and the frozen v20 computation, C1 uses:

`Y5(t) = max(0, -min(log(T[t+k]/T[t]) for k=1..5)) / (v20(t) * sqrt(5))`.

This is a nonnegative **closing-path downside magnitude**. It is not intraday MAE, crash probability, realized execution loss or an option return. C1's original events, N/P/PE/PEI race, monthly cutoffs, three-complete-year coverage rule and inference settings remain unchanged [G03]. Its numerical hurdle is not a promotion rule.

### 3.2 Proposed first new study: PTSE-B0-H5-v1

Purpose: establish an event-independent price-only benchmark and its coverage before testing the value of additional families. Instrument: SPY first; market: US regular sessions. Target: the same Y5 measurement as C1 where price evidence supports it. Inputs: the frozen C1 P vector (`log(v20)`, `trend63`, `momentum5`, and the deterministic positive-trend/negative-momentum indicator), with train-only transformations. Reference: past-data-only mean forecast. This is a transparent continuity baseline, not proof that these are the optimal features.

The **new** runner admits price-qualified dates without requiring event facts. The original C1 runner is not modified to manufacture this behavior. On the price-and-event-qualified overlap, publish a compatibility comparison proving measurement parity; outside it, identify the cohort difference explicitly. A model can be evaluated here without its output acquiring operational authority.

The proposed first candidate integration is observation-only `NEW_ENTRY` context for one currently accepted Prophet strategy sleeve, using that owner's actual candidate and Availability identities. Market Y5 accuracy does not count as successful candidate-policy validation. The six action schemas remain supported even when only one has sufficient evidence initially.

### 3.3 Action outcome matrix

| Action | Eligibility known at decision | Comparison and primary consequences | Required failure/selection controls |
|---|---|---|---|
| `NEW_ENTRY` | Candidate exists in the unmodified incumbent cohort; relevant strategy/session/source/geometry eligibility exists | Enter at the next lawful executable opportunity versus the frozen wait/current policy; net return/path, invalidation, time to liftoff and delay regret | Keep excluded, rejected, stale and unfilled candidates in the census; no post-result selection of winners |
| `CONTINUATION` | Position/simulated position is open under a specified prior policy, with current information only | Hold versus the frozen reduce/exit alternative; remaining upside, drawdown and trend survival | No defining a “working winner” using its future path; position origin and current risk budget retained |
| `PULLBACK_BUY` | Existing strategy's pullback geometry and pre-decision candidate state qualify | Buy versus wait/no-buy; recovery probability/time, adverse excursion and breakdown | Distinguish a realized recovery from one inferred retrospectively; competing breakdown and censoring explicit |
| `ADD` | Existing eligible holding, available risk budget and incumbent add geometry | Incremental units versus no-add at the same timestamp; incremental P&L, downside and concentration consequence | Do not evaluate as a fresh unrelated trade or ignore exposure already held |
| `DERISK` | Existing exposure and a frozen alternative reduction policy | Full paired policy path through exit and subsequent re-entry; net P&L, tail loss, cash carry, foregone upside and turnover | Never stop evaluation at the avoided drawdown; no future-optimal re-entry price |
| `REENTRY` | Attributable prior reduction/exit episode and current incumbent re-entry eligibility | Re-enter under the registered rule versus the current/fixed alternative; recovery capture, whipsaw and delay/price penalty | Cohort comes from the same prior de-risk policy, not arbitrary historical troughs |

A feature can have information value without policy value. State/action associations are observational; matched shadow simulations do not by themselves identify causal live uplift. Any randomized intervention or causal decision experiment requires separate incumbent-owner authorization, appropriate controls and its own scope.

### 3.4 Execution and policy accounting

Signals based on the completed close cannot fill at that same close. Use the first eligible, attributable executable source under the strategy's accepted law, normally a later session/quote for the initial daily study. Record spread, slippage, fees, cash carry, fillability, delayed/missed fills and corporate actions. Underlying stock returns are not executable option P&L; options need their own bid/ask lifecycle and contract economics [G09].

The baseline and challenger must have the same starting capital, position/risk limits and valuation clock. Evaluate complete portfolios or clearly labeled equal-risk single-action experiments; do not sum unlimited overlapping hypothetical positions and call it a portfolio. Report opportunity cost as a decomposition, not a second subtraction when it is already included in net P&L.

A strategy/Portfolio owner must supply the policy objective and materiality threshold from its existing mandate. Until that contract is explicit, forecast research and context product work continue, but policy promotion is `UTILITY_CONTRACT_UNRESOLVED`. Do not invent the Chairman's risk aversion or silently choose weights that make a model look good.

## 4. Transition and representation tests

A proposed transition target needs an observable definition independent of the challenger: onset condition, prior-state condition, persistence confirmation, horizon, end/recovery rule, eligibility and censoring. Use an existing accepted fragility/price-event definition where appropriate; otherwise preregister the target inside the appropriate existing research owner before outcomes. A fitted latent state's own future smoothed labels are not an independent success criterion.

For each transition warning report:

`onset_at`, `first_warning_at`, `lead_sessions`, `warning_duration`, `false_warning_episode`, `missed_event`, `recovery_at`, `censoring_reason`, `incumbent_warning_at`.

Lead is signed: warnings after onset have negative lead and cannot be marketed as early prediction. Consecutive daily alarms are one episode under a frozen rule, not many independent successes. Rare crises, strongly correlated indices and hundreds of same-day stock candidates do not create hundreds of independent transitions.

Compare the simplest adequate representations: existing owner dimensions with no new state; a regularized direct outcome model; a hazard model for an explicit event; and at most one initially registered latent/changepoint challenger. A hybrid is not presumed superior. Named states remain optional communication until stability, filtering, calibration and incremental action value are demonstrated. A descriptive label must not imply a model-estimated probability when none exists.

## 5. Experiment registration, leakage controls and finite trial budget

### 5.1 Registration packet, before protected outcome access

Each study must specify exact data/feature/source hashes, evidence grade, population, decision clock, target and horizon, benchmark, train/development/calibration-fit/calibration-evaluation/final-test boundaries, purge/embargo, missingness, trial family, transformations, allowable model configurations, inference, materiality and falsifiers. It must also state which history researchers have already inspected.

Dates cannot honestly be declared untouched by this review: historical exposure has to be reconciled with existing research owners. W0/W3 must fill actual calendar boundaries and access history before a confirmatory run. When no genuinely untouched historical period remains, historical evaluation is exploratory and confirmation is prospective. Do not use “we froze it today” to cleanse yesterday's inspected outcomes.

### 5.2 Proposed finite first arena

The proposed first incremental family has **at most six confirmatory contrasts at H5**: five B0-plus-family comparisons for participation, catalyst, liquidity, options and cross-asset, and one mechanism-specified interaction. Leadership/concentration is initially part of participation unless a distinct construction is registered instead. A slot is not entitlement: permission, eligible data and a complete study specification remain required. Unavailable slots remain visibly unevaluated, not replaced after looking at results.

B0 versus its past-only mean is a separately identified benchmark-quality assessment. The original C1 experiment retains its own frozen comparisons and family; it is not merged with the new multiplicity family. A broader model exploration may use a capped development-only search, proposed at no more than 12 configurations per registered model comparison, with all attempts recorded. Additional final contrasts or horizons create a visible new family/version and fresh confirmation requirement.

These caps are research-budget proposals, not empirically optimal constants or exemptions from existing admission law. Ratify them before outcomes. Do not spend all slots on superficial variants of the same feature. A marginally null feature may enter the single registered interaction when its mechanism justifies it; preserve the marginal null, charge the interaction trial and compare with both component ablations.

### 5.3 Temporal validation

Use chronological expanding or rolling folds. Fit scalers, imputation rules, feature selection, state mappings and calibration only inside the appropriate prior-data partition. Root/date groups sharing market exposure stay together across split boundaries. Purge every training origin whose actual inclusive outcome window intersects a validation/test interval; apply a separately defined trading-session embargo. An embargo is not a substitute for checking true label endpoints and availability.

Training labels must have matured by the fit cutoff. Test labels can mature later, without rewriting the original prediction. Missing/censored labels remain in coverage accounting. A normalizer or adjustment vintage from the future cannot enter a past feature. A release surprise cannot enter a pre-release observation; an event's later actual time cannot replace the schedule that was known then.

Show matched-population and full-coverage results. Compare all model arms on identical origins within a contrast. Time-block/episode inference must preserve shared dependence and missing calendar positions. Correlated SPY/QQQ/IWM results are sensitivity checks, not independent replications. Label information from overlapping candidate paths must not cross folds through an upstream context stamp.

### 5.4 Proposed statistical defaults, not existing house-law replacements

For the new H5 continuous benchmark, MSE is primary; MAE and tail/path strata are secondary. A proposed research-pass requires a relative primary-loss improvement of at least **2%** on the protected matched test and a positive multiplicity-adjusted lower confidence bound for the paired loss improvement. The 2% threshold is an explicit starting materiality proposal, not a discovered edge or a policy-value guarantee; the owner must ratify it before outcome access or replace it with a documented ex-ante threshold.

Use family-wise error control for confirmatory claims, proposed Holm at 0.05 across the registered contrasts. Exploratory BH results may be reported separately with the family and dependence limitations; do not relabel them confirmatory. Produce paired dependence-aware confidence intervals. A proposed reproducibility default is 10,000 deterministic-seed calendar-block draws, seed 20261003, primary 63-session blocks and 21/126-session sensitivity, subject to pre-result validation against the new label/event structure. These are method proposals inspired by C1 continuity, not proof that every transition process has that dependence length.

Compute attainable power or precision using prior/development data and independent session/episode support. A proposed target is 80% power for the registered material improvement after multiplicity adjustment. Report the assumptions and uncertainty of that calculation; a tiny number of market crises cannot satisfy it by increasing bootstrap draws or counting more stocks. Insufficient support leads to `INCONCLUSIVE`/`POWER_LIMITED`, not silent threshold relaxation.

Report era/root effects and uncertainty, including sign changes and missingness. “Survives all eras” must not mean each underpowered stratum independently clears an arbitrary p-value. Define beforehand the relevant stability/noninferiority bounds and pooling model. An unexplained reversal or unacceptable modern-era loss blocks transfer to that population. A result specific to one admitted era remains explicitly scoped rather than promoted universally.

### 5.5 Probability and calibration gates

Only a registered binary/multinomial/survival target supports probability metrics. Use proper scoring rules such as Brier/log loss for the appropriate object; do not score C1's continuous Y5 as a probability. Keep calibration fit, calibration evaluation and final policy evaluation disjoint.

Calibration acceptance must predefine tolerance and precision by use case. As a review starting point for a well-supported, nonrare binary event, consider calibration-in-the-large within 5 percentage points, calibration slope in 0.8–1.2, and a confidence interval narrow enough to distinguish those tolerances. These are **not universal tail-event tolerances** and not sufficient alone: proper-loss improvement, subgroup behavior, applicability, abstention and stability also matter. Rare-event or transition cells need target-specific precision calculations; unresolved support leaves them unqualified.

Do not publish a 70% probability because a descriptive state occurred in seven of ten correlated examples. Report uncertainty and prospective maturity at the estimate's actual action/horizon/population. A nominal confidence level is not achieved calibration merely because the software printed it.

### 5.6 Policy-positive and authority gates

The policy comparison must clear the incumbent owner's frozen economic materiality and risk constraints on eligible, mature prospective evidence. Report paired net-value difference with dependence-aware uncertainty, drawdown/tail-loss difference, upside forfeited, turnover, exposure time and re-entry penalties. Include observed-cost baseline and a preregistered adverse cost/fill scenario, proposed at twice variable execution costs where economically meaningful. Do not substitute a successful index target for missing candidate-policy proof.

Backtest or retrospective research-pass alone cannot promote. Independent scientific and implementation review, actual source/consumer proof, applicable current authority law and a bounded explicit ruling are all required. Promotion applies only to its registered population/action/horizon. If no model clears the gates, retain observed context and the null findings; do not tune until permission can be manufactured.

## 6. Prospective learning and monitoring

Issue immutable observations before their outcomes exist. Append matured outcomes through the current Market Memory/Eval/candidate grading owners. Retain the incumbent control cohort and never edit old decisions to reflect later source corrections or a new model. Corrections receive their existing lineage and a separately attributable assessment.

Start observation accrual as soon as source/identity/consumer contracts are lawful, even while some historical feature lanes remain blocked. Do not wait for an HMM or every B0–B6 study. Model forecasts begin only when their own registration and issuance requirements are met. Prospective observation capture is not prospective forecast validation.

Operational review checks source freshness, coverage, latency, schema drift, missingness, correction anomalies and publication/consumer generation. Scientific reviews occur at fixed, predeclared maturity checkpoints; repeated peeking must not select promotion dates or thresholds. Alerting uses existing operator attention owners. This document creates no timer or background process; actual scheduling requires the normal authorized runtime path and an attributable receipt.

## 7. Discriminating acceptance tests

At minimum, make each of the following deliberate mutations fail in the relevant contract/test, and show that a legal control passes:

| Mutation | Required discrimination |
|---|---|
| A future source revision or adjusted vintage is substituted into a past feature | Historical decision is rejected or separately graded as ineligible; no restamping |
| Date-only availability is converted to midnight precision | False PIT admission fails |
| One expected trading session is omitted from a supplied calendar | Completeness check fails at the owner boundary; arithmetic alone cannot authenticate it |
| Missing event history is supplied as a zero event flag | Explicit known-negative requirement fails |
| Negative-event receipt becomes unresolvable through the bridge | Provenance round-trip test fails; investigate without assuming an existing defect |
| A post-close decision fills at that same close | Policy eligibility/fill test fails; C1 closing-path arithmetic remains valid as a different target |
| A current membership snapshot is relabeled historical PIT | Breadth source qualification fails or downgrades honestly |
| HMM smoothing/scaling sees a protected future observation | Historical feature/fit-cutoff test fails |
| A challenger is evaluated only on surviving winners or drops unfilled candidates | Frozen-cohort accounting fails |
| An immature/missing label is treated as no event or zero loss | Maturity/censoring test fails |
| A null options Greek is replaced with zero, or windowed GEX with full-book exposure | Source scope/coverage test fails |
| A signed inventory estimate is relabeled observed dealer position | Side-semantics validation fails |
| Invalid/NaN probability, wrong horizon or unsupported schema reaches UI | Consumer renders explicit unavailable context, never a confident state |
| Context on/off/stale/adversarial changes Prophet ranks, admissions, plans or exposure | Zero-authority compatibility test fails |
| Same economic observation is delivered twice | Idempotent same identity; no duplicate issuance/outcome |
| A true correction rewrites the old observation in place | Append/correction lineage test fails |
| An old instrument/strategy request resolves after a newer one | Consumer discards stale response; no cross-root/strategy substitution |
| Latest deployment mixes producer/model/schema generations | Real-path health rejects the inconsistent generation and falls back to incumbent behavior |

Software acceptance needs exact-head tests and relevant normal CI, not an inherited count. Publication acceptance needs producer → immutable artifact → actual API/consumer → outcome linkage, not a fixture screenshot. Natural-session proof cannot be replaced with a historical replay.

## 8. Required run result and decision record

Every study emits, through existing artifact owners: registered/evaluable/non-evaluable cell counts; source grade and coverage; frozen cohort hashes; fit/model/target versions; actual split and maturity boundaries; all attempted configurations; primary and secondary metrics; uncertainty and multiplicity results; era/root/action slices; costs; negative controls; corrections; independent review; and one of `RESEARCH_PASS`, `NO_INCREMENTAL_EVIDENCE`, `REFUTED_CONSTRUCTION`, `INCONCLUSIVE`, `NON_EVALUABLE` or the existing canonical equivalent.

A non-evaluable cell is an honest result of the census, not completed empirical validation. A research-pass is not a forecast or policy promotion. Preserve these distinctions in the machine artifact, product copy, GitHub closeout and Astra's final report.
