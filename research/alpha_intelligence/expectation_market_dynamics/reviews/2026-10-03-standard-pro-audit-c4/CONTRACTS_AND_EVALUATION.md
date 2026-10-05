# K3E 2.0 — implementation contracts and evaluation requirements

**Status:** proposed engineering/scientific acceptance contract, 2026-10-03. This document does not replace existing schemas or frozen EVAL-0. Adopt extensions through the named current owners. See [MASTERPLAN.md](MASTERPLAN.md) for delivery packages and [EVIDENCE.md](EVIDENCE.md) for source IDs.

## 1. Common derived-object envelope

Reuse the existing identity, evidence, time, rights and lifecycle types. The following is a required semantic checklist, not permission to mint another universal schema.

| Field group | Required meaning and acceptance rule |
|---|---|
| Identity | Owner-native issuer/security references and resolver version; raw provider symbol retained only as source identity. No ticker heuristics. Event ID only when an event owner supplied it. A diagnostic lacking canonical identity must not satisfy a security-level contract. |
| Object/generation | Object kind, schema version, deterministic projection version, immutable generation and content digest. Do not combine legs from different generations without explicitly declaring the cross-generation composition and its cutoff. |
| Query | Decision cutoff; purpose; requested metric/fiscal period/horizon; requested market session; explicit scenario reference if any. Server authorization, not a user-supplied string, determines permitted use. |
| Clocks | Source-effective, source-published, provider-observed, system-observed, corrected/superseded clocks where actually known. Unknowns remain null with reason. Economic time does not substitute for availability. |
| Metric | Metric ID, observation role, period identity, horizon semantics, unit, currency, accounting basis and share convention. A range bound, growth rate, analyst count and central expectation are different roles. |
| Lineage | Exact source references, native record IDs, payload/blob hashes, collector/model versions, supersession links and qualification-receipt references. Hash consistency is not independent attestation. |
| Scope/coverage | Declared eligible population, available/fresh/stale/missing/excluded counts, independent unit definition and row-to-unit mapping. Nonexclusive reason flags must not be summed into population counts. |
| Inference | Observed source value, deterministic aggregation, conditional inverse set, prior-dependent posterior, priced-Q quantity, descriptive state, or evaluated forecast. No implicit conversion between them. |
| Uncertainty | Source uncertainty, sampling/model uncertainty and identification state separately. Contributor dispersion is not automatically forecast error variance. |
| Use/authority | References to owner-approved purpose and display/retention/model-use decisions. Context/shadow/promoted are separate from source validity. Client input cannot grant publication or financial authority. |
| Explanation | Component facts, assumptions, strongest rival explanation, unresolved limitation and next observable; all numeric claims trace to the object, not generated prose. |

Suggested output reasons include `NO_ELIGIBLE_CAPTURE`, `UNKNOWN_PUBLIC_AVAILABILITY`, `IDENTITY_UNRESOLVED`, `PERIOD_UNMAPPED`, `BASIS_UNKNOWN`, `UNIT_UNKNOWN`, `CURRENCY_UNKNOWN`, `RIGHTS_UNRESOLVED_FOR_PURPOSE`, `STALE_SOURCE`, `PARTIAL_PROVIDER_RESPONSE`, `HORIZON_MISMATCH`, `WEAKLY_IDENTIFIED`, `MULTIPLE_SOLUTIONS`, `NO_FEASIBLE_SOLUTION`, `MODEL_SENSITIVE` and `UNSUPPORTED_SPECIES`. Reconcile naming with current owners instead of creating synonyms beside accepted types.

Separate source loss from semantic refusal. A provider timeout is not zero; absence of options is not neutral options sentiment; a legitimate zero covering count is not a valid consensus value; a fiscal rollover is not a revision.

## 2. Point-in-time query and revision contract

### 2.1 Selection algorithm

For a purpose-qualified query, resolve identity and fiscal mapping with a lawful as-of owner view; select the relevant source grain; exclude rows unavailable at the cutoff; follow supersession only through versions available then; preserve any newer failed attempt as a distinct availability fact; return selected observations and complete denominator/reason accounting.

The two native capture clocks must be no later than the requested capture cutoff. Public-information replay additionally requires qualifying source-availability evidence. A historical vendor vintage delivered today may support a separately qualified reconstructed historical study; it does not become a prospectively captured Mastermind record. Preserve those evidence eras explicitly.

For two-cutoff changes, require the same subject, metric, explicit fiscal period, observation role, unit, currency and basis. Report the interval `(t_previous_capture, t_current_capture]`. The occurrence of a true analyst revision within that interval is not directly known from endpoints alone. Missing publication time does not become the collection timestamp.

`correction_state=supersedes` identifies source lineage, not necessarily economic cause. Distinguish an observed changed snapshot from a known provider correction, a fiscal rollover and an independently verified analyst revision. When the cause is unknown, do not choose the narrative that best fits price.

### 2.2 Changes, velocity and acceleration

For compatible values x0 and x1 separated by an actual elapsed interval Δt, the capture-interval slope is `(x1−x0)/Δt`. Declare whether Δt uses calendar duration or market sessions. Do not mix these scales or label this slope the exact speed of analyst updating.

With three eligible comparable observations, compute two interval slopes; an acceleration diagnostic may compare them across the elapsed difference between interval midpoints. Preserve the intervals and effective sample count. It is noisy descriptive arithmetic, not an automatically validated momentum signal. Repeated unchanged snapshots are not independent forecast events.

Percent changes require a defensible denominator. Do not divide through near-zero or negative EPS. Use owner-approved absolute/unit-scaled differences, regime stratification or abstention. Do not create analyst freshness from snapshot age or turn overlapping provider revision windows into independent counts.

### 2.3 Source/consumer acceptance cases

| ID | Discriminating case | Expected result |
|---|---|---|
| C01 | Identical snapshot recaptured | New capture may exist; no fabricated changed estimate or supersession |
| C02 | Changed same-period eligible value | Correct prior reference; old row unchanged; cause remains appropriately typed |
| C03 | Null/partial/failure after good | New failure/missingness visible; no zero or fresh-flat replacement |
| C04 | Fiscal period rolls under same relative horizon | Distinct period lineage; no same-period revision |
| C05 | Same numeric value, changed unit/currency/basis | Not silently comparable; native source lineage semantics preserved |
| C06 | Future capture or later correction inserted | Earlier cutoff result unchanged; later result appropriately differs |
| C07 | Source published earlier but captured later | No backward insertion into prospective Mastermind history |
| C08 | Provider symbol or dual-class ambiguity | Canonical as-of resolver or typed refusal; no guessed identity |
| C09 | Missing period anchor | No FY/Q inference from ticker, current calendar or raw +1q alone |
| C10 | Legitimate zero count, zero-covered numeric consensus | Count retained as count; unsupported consensus excluded |
| C11 | Missing high/low/median/contributor detail | Correct independent role-specific nulls; no invented SD/distribution |
| C12 | Rights or authentication denied | Only permitted omission metadata; no private numeric payload/cache leak |
| C13 | Mixed current/old generation in UI | Rejected or explicitly reconciled server-side; never silent blending |
| C14 | Empty eligible cohort | Denominator zero shown; no 100% coverage or normal-state inference |
| C15 | Duplicate/out-of-order rows and attempts | Deterministic dedup/lineage rules; no inflated episode N |
| C16 | Natural source version changes after #8064 | Relevant acceptance requalified; previous version receipt preserved |

Reuse the incumbent tests and natural evidence. Synthetic tests qualify code paths, not historical natural occurrence. Do not induce collection failures or mutate providers to obtain an attractive source receipt.

## 3. Priced Assumption Envelope contract

### 3.1 Object being estimated

For a forward valuation owner M, financial state F at the allowed cutoff, observed price P, allowed assumptions C and numerical/economic tolerance ε, define:

`Theta(P,F,M,C,epsilon) = {theta in C : abs(V_M(theta;F) - P) <= epsilon}`.

P and V must use the same object and units: enterprise value, equity value or per-share value. Declare every conversion. Separate solver residual tolerance from an economically chosen price/noise band. Freeze tolerances before result-driven tuning.

Output locks and free variables, bounds, units, forward-model version, input receipt, feasible witnesses, root/contour coverage, solver convergence, constraint-boundary hits and identification diagnostics. A finite grid approximates an envelope; it is not a proof that unvisited regions contain no solutions. Empty search output requires a distinction between certified infeasibility and unresolved numerical search.

### 3.2 Identification

A single scalar price supplies at most one local independent equation. For p free parameters, print the 1×p Jacobian rank and nullspace dimension, not only a condition number. Under local smoothness, multiple free parameters generically leave unobserved directions. Locks and priors can narrow the answer, but that narrowing must be labeled as assumed rather than discovered from price.

A required adversary is `V(g,m)=g+m`: J=[1,1] has one nonzero singular value, while the direction [1,−1] leaves price unchanged. Any implementation that labels this jointly identified because the nonzero singular-value ratio equals one fails acceptance.

A posterior is permitted only with an explicit likelihood/noise model and prior. It is a distribution of assumptions conditional on that modeling choice, not a recovered representative market belief. Add prior/constraint sensitivity and comparison to the unconditioned reference.

### 3.3 Comparison with fundamental references

The initial product compares contours with declared scenarios/ranges. No default overlap percentage. Analyst low/high bounds, a confidence interval and a distribution of operating outcomes are different objects.

When a genuinely independent, owner-qualified joint reference F_ref exists, a separately registered compatibility statistic can be:

`compatibility_mass = integral 1(abs(V_M(theta;F)-P)<=epsilon) dF_ref(theta)`.

Name its measure, support, dependence assumptions, tolerance and model. Print sensitivity to all of them. It is a reference-model compatibility mass, not a probability of under/overvaluation. It changes with ε; an exact equality surface can have zero mass under a continuous distribution. Do not compare percentages computed with different tolerances or parameterizations as though they shared a scale.

Driver stretch is initially set-valued: projected requirement interval, reference interval, nearest feasible witness and scale definition. Per-driver interval overlap does not establish joint overlap. Zero-scale or unstable standardization yields a typed refusal. No arithmetic mean of driver stretches becomes a K3E score.

### 3.4 Forward-model accounting

Use the incumbent approved family, not an ad hoc inverse model whose accounting differs from the displayed forward model. For a future FCFF family, compute operating cash flow after consistent tax/reinvestment assumptions and discount with the appropriate WACC; bridge enterprise to equity under an explicit owner policy. FCFE uses the corresponding equity cash-flow/discount convention. An earnings multiple already values equity; do not append a debt bridge from a different family.

Freeze explicit-period growth, margin, reinvestment/capital intensity, tax and terminal assumptions. Stable growth, reinvestment and return on capital must be mutually coherent. Terminal growth must satisfy the selected family's convergence constraints; a small denominator is a model-sensitivity warning, not a precise forecast. [E03]

Current reported outstanding shares are not diluted shares. Currency/FX, share class, options dilution, leases, pensions and noncontrolling interests require actual owner inputs or refusal; do not cure absent inputs with plausible defaults. Unsupported issuer species receive a species-specific model later rather than being forced into a nonfinancial corporate DCF.

### 3.5 PAE acceptance suite

| ID | Test | Pass condition |
|---|---|---|
| P01 | Hand-computable forward case | Same value as the approved owner calculator |
| P02 | Conditional one-dimensional inversion | Residual within declared tolerance; all locks printed |
| P03 | Multiple roots/nonmonotone surface | All discovered roots retained; no unsupported uniqueness claim |
| P04 | One price, multiple free parameters | Rank/nullspace and weak-identification warning survive |
| P05 | Boundary/no root | No silent bound widening; infeasible vs unresolved search distinguished |
| P06 | Denominator/terminal instability | Invalid family refused; sensitivity and terminal dependence visible |
| P07 | Enterprise/equity/per-share swap | Mismatch rejected; debt/cash not double counted |
| P08 | Actual loader fields and share convention | No invented field aliases or diluted-share substitution |
| P09 | Reparameterization/prior/tolerance change | Probability/geometry labels remain correct and sensitivity printed |
| P10 | Marginal overlap but no joint witness | Does not claim joint compatibility |
| P11 | Deterministic repeat/replay | Same inputs/settings generate identical canonical output |
| P12 | Future fact, later correction, price shock | Earlier output unchanged; new scenario/generation explicitly created |

## 4. Options and cross-channel contracts

Use the options owner's exact exercise/model/quote conventions. Where a European-equivalent density is claimed, the owner documents its transformation or qualifying instruments, discount factor, maturity and numerical extraction. Include quote synchronization, bid/ask conditions, strike support, tail treatment, no-arbitrage checks, nonnegativity/normalization and solver diagnostics. Q is not P; calibration from Q to P is a separately evaluated target/model, not a label change. [E01–E02; E10]

Event-variance estimation works with maturity-consistent total variance, not raw IV subtraction. Background variance and event membership are model assumptions. Excess implied event variance alone is not a variance risk premium. Quotes do not directly reveal buyer-initiated opening positions, actual dealer inventory or a distribution of issuer revenue. [E04; E11]

Cross-channel comparisons require a declared mapping of subject, variable, horizon, unit, measure and conditioning set. An event-day stock-return Q distribution and a three-year revenue CAGR surface are displayed alongside each other, not subtracted. A PAE contour and a priced tail can jointly inform a scenario narrative, but that narrative is not a calibrated joint distribution without an explicit model.

Residual response must retain its owner baseline, fit window, corporate-action and session conventions. A contemporaneous price-derived feature cannot validate itself with the same price move. Distinguish an explanation of today's price from a preregistered prediction of a strictly later outcome.

## 5. Preserve the exact EVAL-0 contract

Source: `EVALUATION_PREREG.md` and `eval0_preregistration.v1.json` at the main audit pin. The machine record is authoritative. [I07]

| Item | Frozen v1 rule |
|---|---|
| Registration | K3E-EVAL-0-V1; canonical SHA-256 `986ec117e8517b77e8dece565fd9d9dc169e758beb9d1619acc443e061ef87fd` |
| Development | 2012-01-03 to 2018-12-31 |
| Validation | 2019-01-02 to 2022-12-30 |
| Locked retrospective holdout | 2023-01-03 to 2026-08-21; one final evaluation |
| Prospective activation | First NYSE session open strictly after accepted main contains the exact digest; consume actual activation receipt |
| Purge/embargo | 63 sessions, tied to maximum registered horizon |
| Inference unit | Distinct issuer episode, not rows/days/repeated fires; 20 quiet sessions separate revision episodes |
| Minimum N | 100 issuer episodes overall; 25 per claimed subgroup |
| Coverage | At least 60% eligible observations and 60% named motivating cases answered with honest abstention |
| Baselines | Nine registered boring baselines; compare to strongest eligible one |
| Challenger budget | 64 total; failed jobs, discarded sets, ablations and manual feature/threshold changes count |
| Multiple testing | Benjamini–Yekutieli, q=0.10, across full registered dependent comparison family |
| Research-advance effect size | At least 5% relative primary-loss improvement in validation AND locked holdout |
| Uncertainty | Issuer-episode clustered 95% interval excluding zero; date-block sensitivity; no material calibration/abstention regression |
| Authority | ADVANCE_RESEARCH_ONLY is not product, Prophet, ranking, sizing, gating or trade authority |
| Amendment | New version, digest, explicit diff/reason/supersession and new forward boundary; old observed outcomes stay old |

Target families are T1 next same-period revision direction; T2 revision arrival; T3 cluster onset; T4 consensus change; T5 dispersion direction; T6 residual response; T7 lead/lag; T8 phase transition. Dependency restrictions remain binding. Snapshot and contributor clusters do not pool. Unsupported source granularity cannot be repaired by changing the target after looking at outcomes.

For a newly registered family, stronger thresholds may be proposed before access, but q=0.05 alone is not a complete design. Freeze a primary estimand, strongest baseline, effect-size threshold, power calculation, dependence-valid uncertainty, family/search budget, minimum coverage and prospective corroboration. BY addresses a multiple-testing issue, not biased data or invalid p-values. [E05]

## 6. Hypothesis and experiment matrix

All rows below are candidates or dispositions, not measured alpha. Existing v1 targets keep their exact rules; new targets require A3 registration. Minimum numeric floors below refer to existing v1 only; a new experiment needs its own prospective power/coverage decision, not a borrowed arbitrary N.

| Candidate | Estimand / required data / horizon | Baseline and primary evaluation | Falsifier and current disposition |
|---|---|---|---|
| Context-adjusted revision impulse | Same-period provider-consensus change conditional on sector/history; qualified snapshots, 21/63 sessions | Raw 30/90-day revision and strongest v1 baseline; T1 log loss or T4 MAE/pinball | Date/issuer-block shuffle, later-vintage leak, size/coverage control; eligible only after economic qualification |
| Breadth–magnitude decomposition | Contribution beyond consensus change; exact provider breadth semantics or contributor vintages | Mean revision + coverage; T1/T4 and calibration | Count-versus-reviser substitution, overlapping-window double count; aggregate provider version separately named |
| Dispersion change | Same-measure contributor SD change, 21/63 sessions | Dispersion level + coverage; T5 probabilistic loss | Range substituted for SD, composition/staleness confound; DATA_BLOCKED when SD/detail unavailable |
| Revision velocity/acceleration | Capture-interval slope and slope change from comparable irregular observations | Level/change + elapsed interval; T1/T4 | Randomized capture intervals, short denominator, future corrections; descriptive first, no claim of analyst speed |
| Contributor diffusion/half-life | Time from first contributor revision to subsequent updating | Fixed-window/no-change hazard; interval-aware survival score | Anonymous aggregate snapshots cannot identify arrival sequence; DEFER until contributor rights/vintages |
| Price→Street lag | Whether pre-cutoff owner residual history improves future captured revision prediction | Revisions-only and price-only; T1/T2/T7 | Common event shocks, price-window overlap, censoring; forecast ordering only, not causal incorporation |
| Street→price lag | Whether eligible revisions improve strictly later residual response | Momentum, sector and raw revisions; T6 | Same-session outcome leakage, post-event consensus, baseline refit after event; shadow only |
| PAE requirement stretch | Set-valued requirement/reference mismatch, initially state reproducibility; later 21/63-session or longer target explicitly registered | Simple multiple and locked one-axis inverse; model stability first, then target-specific loss | WACC/terminal/ROIC prior sensitivity, circular price input; no alpha test until A6/A7 and independent reference |
| Fundamental–PAE compatibility | Named joint-reference mass within stated price band | Scenario membership or point-gap comparator; proper target-specific predictive loss only if preregistered | Tolerance/measure dependence, using price-conditioned posterior as reference; geometry first, percentage disabled by default |
| Implied event variance | Option total-variance event component at actual event maturity | Raw IV/implied move and owner historical-volatility baseline; realized-variance/tail loss | Non-event placebos, multiple events, stale quotes, Q/P confusion; owner-qualified liquid cohort only |
| Skew–dispersion tension | Incremental future tail information of explicitly mapped channels | Skew-only and dispersion-only; proper tail/Brier/log score | Missing SD, maturity mismatch, liquidity selection; DEFER absent compatible variables/history |
| Guidance–consensus difference | Same-period/basis guidance relative to pre-event explicit forecast | Consensus-only; later forecast/actual loss | After-release consensus, GAAP/adjusted mismatch; specialist event owner and MAS-119 boundary retained |
| Positioning-amplified asymmetry | Incremental interaction with lag-correct crowding/liquidity for future tail risk | Gap alone and positioning alone | Publication-lag-preserving shuffles, concentration/liquidity controls, insufficient subgroup N; context until validated |
| Phase transitions | Probability of next objectively defined descriptive state, 21/63 sessions | No-change/simple Markov AND components-only | Outcome-designed labels, state instability, redundant information; optional after A9; no assumed phase classifier |
| Opening option flow | Reproduction of buyer-initiated opening-flow construct, short horizon | Aggregate PCR plus ordinary price/liquidity controls | Quote-side proxy is not opening position identity; DATA_BLOCKED until the actual information set exists |

Every executed row records mechanism, observation grain, exact feature cutoff, label availability, target horizon, eligible species/cohort, use rights, baseline, negative controls, search cost, coverage, effect size, uncertainty, trial result and independent review. Additional narrative ideas are exploratory; they do not silently enter promotion search.

## 7. Experimental protocol and stop rules

1. **Availability before outcomes:** establish owner-native as-of identity, source delivery/correction clocks, universe and corporate actions. A present-day survivor list is not a historical universe.
2. **Search budget before fitting:** freeze feature families and baseline eligibility. Preserve all failed trials. Equivalent reformulations do not reset the budget.
3. **Dependence before significance:** cluster by issuer/episode/event; use date-block sensitivity and appropriate purge/embargo. Cross-market or subgroup claims require independently sufficient evidence.
4. **Censoring before labels:** distinguish an unchanged observed snapshot, an unobserved interval, collection failure and an event that has not yet arrived. Survival censoring is not a negative label.
5. **Increment before aggregate performance:** ablate fundamentals, revisions, price, options and positioning; compare both constituent and incremental models. A rich combined model must beat the strongest eligible simple reference.
6. **Calibration and coverage before marketing:** report reliability and risk–coverage curves. Abstaining on difficult cases can improve apparent accuracy; print eligibility and refusal denominators.
7. **One final locked decision:** report null/adverse results and preserve the original holdout. Do not relabel a disappointing locked result exploratory and then reuse the same tape as a fresh holdout.
8. **Prospective before financial effect:** natural shadow evidence and consumer-specific approval precede Fusion/Prophet influence. No finite source audit proves return predictability.

Stop the specific construction when leakage is necessary, its real source grain is unavailable, bounds/priors determine the favorable answer, incremental results disappear under the registered controls, trial budget is exceeded, current-regime coverage fails, or rights do not allow the required use. A failed hypothesis remains a durable scientific result; it does not authorize adding a heuristic under a different name.

## 8. Delivery evidence and release tests

The complete core release needs source acceptance, economic/use qualification, deterministic replay, forward/inverse parity, options-owner qualification, UI/machine parity, authenticated live transport, source-cycle observation and rollback. The artifact set must identify which claims are independently executed, reported by an incumbent, proposed, or still unverified.

Do not substitute any of these pairs: hosted CI selection for actual named test execution; source merge for deployment; a synthetic fixture for a natural market observation; session hash for attestation; row count for effective N; point forecast for distribution; current public vendor description for contractual rights; phase explanation for a validated forecast.

The build's final status table must retain `PROVEN_LIVE`, `BUILT_NOT_PROVEN`, `PARTIAL`, `DARK_OR_DISCONNECTED`, `BROKEN`, `SPEC_ONLY` and `NOT_BUILT` at the capability level. Rejected-by-design concepts are explicitly outside implementation scope, not secretly implemented as downstream convenience fields.
