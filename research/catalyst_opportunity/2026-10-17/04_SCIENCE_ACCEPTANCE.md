# Scientific design, falsification and acceptance

Status: proposed evaluation contract. No market backtest, prospective trading result or production test is reported as completed by this chapter. The acceptance cases below are specifications for Fable's implementation and research work; they are not a list of tests already run.

## 1. Five independent evaluation tracks

| Track | Question | Suitable evidence |
|---|---|---|
| Observation | Did the system actually cover the declared sources and instruments in time? | Source receipts, universe reconciliation, clock/coverage audits, ordinary-run health. |
| Interpretation | Were claims, identities, numbers, novelty and mechanisms correctly extracted? | Independent source-backed labels, blind adjudication, precision/recall and error taxonomy. |
| Event forecasting | Did the stated future event occur, with calibrated probabilities? | Frozen target/risk set, actual issue time, independent outcome, calibration and proper scores. |
| Market/timing utility | Did the case identify useful, executable opportunity beyond simpler scanners? | Point-in-time observations, matched baselines, realistic latency/fills/costs, untouched evaluation. |
| User utility | Did the user discover important unmonitored cases without intolerable alert burden? | Delivered alerts, task completion, measured relevance, misses, analyst effort and privacy-safe feedback. |

A pass in one track is not a pass in another. Operational completeness, extraction accuracy, forecast calibration and trading performance must not be averaged into one green badge.

## 2. Registered hypotheses

H1: all-market price/participation discovery identifies relevant emerging themes earlier than the existing confirmed-theme channel at a tolerable false-alert burden.

H2: structured event novelty and explicit source lineage add useful information beyond raw headline counts.

H3: attributable economic exposure improves security selection compared with indiscriminate theme membership.

H4: event plus market context adds incremental utility over a price/volume-only scanner using the same universe and decision times.

H5: causal timing observations improve entry feasibility or risk-adjusted follow-through compared with immediate entry after a discovery alert.

H6: deeper model reasoning improves sufficiently important cases after accounting for latency, cost and error risk, compared with constrained extraction plus deterministic rules.

H7: geopolitical forecasts improve calibration or decision utility against prevalence/persistence baselines for their exact targets; this is distinct from predicting defense or oil returns.

H8: personalized delivery that retains an unmonitored-sector allocation reduces meaningful misses without increasing user burden beyond the declared policy.

Each hypothesis receives an experiment card: target, eligible population, information cutoff, source/identity/model versions, baseline, estimator, primary metric, minimum relevant improvement, power/information plan, costs, exclusions, maturity, permitted claim, rejection rule and review boundary. These cards live in the incumbent experiment/evaluation owner, not a new registry.

## 3. Baseline ladder and ablations

Use the same contemporaneous universe, source access, information cutoffs and outcome windows wherever a comparison claims incremental value.

- B0: simple synchronized relative strength plus time-of-day volume.
- B1: existing Theme Scoring/confirmed alerts, preserving their actual timing.
- B2: coverage-adjusted news count/burst only.
- B3: structured event/novelty extraction without deep economic reasoning.
- B4: event plus market discovery, with explicit issuer exposure but no frontier model.
- B5: complete proposed method, including deeper interpretation and the qualified timing policy.

Compare components individually before claiming a fusion benefit. Match processing/delivery delays or report the latency difference explicitly. B5 cannot receive later news while B0 is frozen earlier and still claim a fair comparison.

Ablations remove one information family at a time. Removing seven price-derived indicators does not constitute seven independent causal experiments. Track shared upstream lineage and common event exposure.

## 4. October 2026 motivating case

### 4.1 Evidence status

The previous conversation named October 14-16 defense gains and escalating regional risks. This package does not accept that entire narrative as verified causal evidence. Exact news availability, original Mastermind receipts, intraday bars/quotes and executable entry windows have not been reconstructed. Public end-of-day or secondary price summaries cannot prove an achievable pre-rally entry.

The case was selected after observing the rally and is therefore **development-only**. It must never be the final holdout or the sole basis for thresholds. Alternative catalysts such as analyst actions, procurement/company announcements, earnings expectations, general sector rotation and broader market shocks remain live hypotheses.

### 4.2 Three honest replay classes

**Observed-system replay:** uses the actual historical records Mastermind retained, including receipts, missing sources, configurations and output generations. It can answer what the system knew and did.

**Source-availability simulation:** uses independently evidenced public/source availability plus an explicitly modeled acquisition and processing delay. It can test what a specified future system might have observed, but is not proof that Mastermind observed it historically.

**Retrospective explanation:** uses later or revised information to understand the episode. It is useful research, not a point-in-time forecast or an executable backtest.

Never merge these classes into one timeline. Unknown arrival time remains unknown. A source's event date or search-engine date is not substituted for first observation.

### 4.3 Reconstruction protocol

Freeze the eligible universe and theme memberships before inspecting outcomes. Acquire licensed market history and original versions where available. Build the timestamped source timeline, identifying first release, revisions and later reports. Include all eligible competing themes and negative candidates, not just defense and oil. Run B0-B5 only where their required historical inputs are admissible. Emit unavailable results when a method cannot be reconstructed.

Inspect October 11-16 as one episode with within-episode timelines, not a collection of independent ticker wins. Determine when an alert would have been computed, delivered, seen and executable. Measure whether any qualifying opportunity remained after those delays. A correct decision may be watch, no entry, or too extended.

## 5. Data integrity before statistical sophistication

### 5.1 Point-in-time eligibility

A historical feature may use only source versions, relationships, membership, market observations, parameters and model state available at the cutoff. Test future-input noninterference: change arbitrary later evidence while holding all eligible earlier evidence fixed; the earlier assessment, ordering, reasons and eligibility must remain unchanged.

Preserve corporate actions, delistings, halts, cash outcomes, cross-listing roles and vendor corrections. Later cleaned data can be used for an independent outcome where the outcome policy allows it, not retroactively to improve the input signal.

The inspected qbus and Radar clocks provide useful guards but do not prove every composed path is temporally valid. A date parser accepting a date is not evidence of a precise release time. [I06, I07, I12]

### 5.2 LLM contamination

A modern model may know later events through its weights, even when retrieved documents are filtered by timestamp. Modern search rankings or revised pages can also reveal future information. Prompting the model not to look ahead or masking a company name does not prove contamination has been eliminated. [X12]

Use temporally compatible frozen models and archival retrieval where available; otherwise label historical semantic studies as retrospective and require prospective evaluation before promoting a predictive claim. Freeze prompt, model identifier, retrieval policy, source revisions and outputs. A model change is a new experimental version, not a cosmetic maintenance update for scientific claims.

### 5.3 Labels and adjudication

Label from source evidence, not from another model's confident agreement. Use independent adjudication for consequential disputed fields and sample agreed negatives as well as agreed positives. The retained news-impact benchmark has an unaudited agreed-absence stratum and incomplete case adjudication; reuse its accepted work without treating agreement as gold. [I11]

Record ambiguity and contract gaps explicitly. A per-share dividend cannot be forced into an incompatible aggregate-dollar field. An event with unavailable source text may be ineligible for a body-based extractor evaluation even if its headline is visible.

## 6. Metrics that match the user problem

### 6.1 Observation and extraction

Measure declared-universe coverage, source uptime, source-to-receipt delay, receipt-to-view delay, stale served generations, correction latency, unsupported identity rate, and dropped/refused items by reason. For extraction, measure field-level precision/recall, actor-role accuracy, unit/amount/date errors, source-span entailment, novelty classification and source-lineage mistakes.

Metrics include uncertainty and denominator. Ten good examples do not establish broad coverage. A recent successful job over old bytes does not establish fresh data.

### 6.2 Event forecasts

Use Brier score and log score with documented numerical clipping, calibration by horizon/risk group, precision-recall where appropriate, and comparison against the actual event prevalence/persistence baseline. Do not infer skill from high accuracy on a rare event. Report base rates, positive events, effective independent episodes and confidence intervals. [X13]

A calibrated event probability can still be economically unhelpful. Evaluate any decision utility under a declared loss/payoff model separately, rather than assuming a better Brier score means profitable trading.

### 6.3 Discovery and timing

Measure precision at the user's attention budget, recall of predefined material opportunities across the full covered universe, lead time before a predefined extension/confirmation point, false alerts per user-day, repeated-alert burden, and the proportion that remains technically reviewable after delivery.

Define a material opportunity using a frozen rule before evaluation: horizon, market-relative or raw return, liquidity, risk path and threshold. Do not define success as whichever stock later went up most. Report both detected and missed eligible episodes. Track whether the explanation was correct even when the price moved favorably.

For an executable policy, report net returns, drawdown, turnover, adverse/favorable excursion, spread/slippage sensitivity, nonfills, gaps and capital overlap. Return minus SPY is market-relative, not automatically alpha. A volatility-adjusted or factor-residual claim needs the corresponding qualified estimator.

### 6.4 User utility

Test whether a user can discover an unmonitored sector, understand the mechanism and uncertainty, open the right chart, save/follow the case and interpret a correction. Measure time, errors, relevance and burden. Do not infer user benefit from click-through alone or train solely on the user's existing favorites.

Production behavioral research and customer data collection require their normal consent/privacy treatment. The design can first use structured internal tasks and a consented evaluation cohort.

## 7. Statistical design

Use chronological development, validation and final untouched evaluation blocks. Purge overlapping label windows and apply embargo where needed by the horizon and dependence structure. Separate crisis/actor-pair episodes and calendar shocks across folds where the claimed generalization requires it.

Resample or model dependence at the actual unit: incident, issuer, theme and common calendar shock. Five defense names moving on one headline do not supply five independent conflict forecasts. Repeated intraday alerts do not become hundreds of independent events.

For paired method comparisons, use the same eligible rows, outcome maturity, weights and benchmark basis. Preserve all-event descriptive summaries separately from the paired estimand. Never compare high-return events retained on one side against only the subset of controls that survived missingness. Do not impute unavailable baseline returns as zero. [I01, I14]

Track all tried variants and horizons through the existing experiment owner. Multiplicity corrections and deflated performance measures can help evaluate selection, but cannot repair look-ahead, survivorship, invalid labels or unrealistic execution. Choose one primary estimand and a small declared set of secondary diagnostics before evaluation. [X22]

Predefine a minimum useful improvement in user burden/lead time or net decision utility, not merely statistical significance. Estimate the needed effective information from development variability and event prevalence. Do not promise that an arbitrary number of calendar weeks can validate rare geopolitical events.

## 8. Finite promotion and rejection

The first implementation registers an evaluation review boundary after a declared operating window, such as 90 eligible market sessions, **as an administrative review target rather than a guarantee of enough statistical information**. A target-specific power/information calculation may require a different boundary. Source integrity failures trigger earlier review.

At review:

**PROMOTE_ADVISORY:** the exact method beats its prespecified baseline by the required practical margin, with uncertainty supporting the claim; extraction/data integrity and realistic execution pass; costs and burden fit the declared product; the existing decision owner accepts the bounded use.

**KEEP_SHADOW:** useful information remains insufficient or a resolvable data limitation persists. Record exactly what observations are missing, how they will accrue under an admitted runtime, and the next finite decision boundary. Do not call the trading capability complete.

**REJECT:** the effect fails, harms user utility, depends on unavailable rights/data, or cannot be made trustworthy at acceptable cost. Remove the unsupported claim or feature; preserve useful factual/context functions. Rejection of one model does not require discarding the entire discovery product.

No model promotes itself, and no marketing claim exceeds the accepted target/horizon/coverage. Fable can execute the registered evaluation and ordinary repairs; material changes to targets, claims or risk authority return to their actual decision owner.

## 9. Adversarial acceptance catalog

The identifiers below are stable planning references. Their status is NOT_RUN until implementation evidence is attached. Scope-specific subsets apply to staged releases; the entire declared release must satisfy its relevant tests.

| ID | Case | Required result |
|---|---|---|
| A01 | Event time precedes public availability | No pre-availability inference or simulated entry. |
| A02 | Date-only publication | No invented intraday precision. |
| A03 | Backfilled source | Actual new receipt retained; historical first-seen not rewritten. |
| A04 | Future raw evidence changed | Earlier output, reasons and ordering unchanged. |
| A05 | Future identity/membership changed | Earlier security routing unchanged. |
| A06 | Later model/prompt changed | Frozen earlier assessment remains reproducible. |
| A07 | Late market correction | Original input preserved; current revision explicit. |
| A08 | Corporate action or delisting | No false jump; cash/security outcome handled. |
| A09 | Exact duplicate source item | One native item, no duplicate alert. |
| A10 | Syndicated reports across outlets | Shared origin disclosed; no artificial corroboration. |
| A11 | Two similar but distinct incidents | Not silently collapsed into one. |
| A12 | Incident later split/merged | Alias lineage appended; prior view preserved. |
| A13 | Recycled old headline becomes viral | Attention novelty separated from new physical event. |
| A14 | Retraction or reclassified attack | Prior alert linked to correction and affected users informed. |
| A15 | Official adversarial assertion | Attribution and uncertainty retained. |
| A16 | Source outage during quiet period | No inference that risk has fallen because reports vanished. |
| A17 | Wrong actor, unit or time | Structured extraction refused or corrected before use. |
| A18 | Agreed negative model labels | Sampled independently; agreement not accepted as truth. |
| A19 | Unencodable financial field | Typed contract gap, not forced value. |
| A20 | Prompt injection in source text | No tool, credential, budget or instruction effect. |
| A21 | Unsupported transport | No spoofing of an admitted provider route. |
| A22 | Expired model-processing right | No unauthorized enrichment despite visible headline. |
| A23 | Current display right revoked | Caches and historical views obey current access policy. |
| A24 | Tenant/sign-out changes mid-request | No cross-user result or stale protected response. |
| A25 | Theme outside user's watchlist | Still eligible for declared all-market discovery. |
| A26 | One dominant constituent | Broad-participation label withheld when breadth absent. |
| A27 | Missing 30% of members | Coverage explicit; D0 admission fails as specified. |
| A28 | Same-day repeated builds | Existing two-session confirmation not accelerated. |
| A29 | Early intraday discovery | Separate provisional alert; confirmed channel unchanged. |
| A30 | No news explanation for strong tape | Unexplained market-first case remains possible. |
| A31 | Analyst upgrade versus geopolitical story | Competing causes shown; no automatic war attribution. |
| A32 | Correlated price indicators | No false count of independent confirmations. |
| A33 | Theme membership expands to securities | Required membership-expansion family/prefix preserved. |
| A34 | Issuer/security mapping ambiguous | No economic claim, holdings join or trade nomination as resolved. |
| A35 | Radar extra score/authority fields | Rejected by frozen contract. |
| A36 | Nomination before source/as-of or without spool | Not consumable. |
| A37 | TTL expired or source stale | Existing availability/retention policy preserved. |
| A38 | Pivot uses future bars | Confirmation time, not pivot time, governs alert. |
| A39 | Same-bar closing signal and fill | Fill cannot precede the decision/delivery. |
| A40 | Limit touched but not executable | Nonfill/partial-fill assumptions disclosed and tested. |
| A41 | Premarket spread or market halt | Timing refused/degraded; no normal-session execution assumption. |
| A42 | Post-alert gap and overextension | Thesis may remain while entry urgency is withheld. |
| A43 | Weekend gap through stop | Loss not falsely capped at the stop price. |
| A44 | Oil rises on demand rather than supply | Mechanism alternatives preserved. |
| A45 | Defense sale ceiling/award amendment | No revenue conversion or double counting. |
| A46 | Bio endpoint success with financing need | Clinical and shareholder consequences separated. |
| A47 | MedTech regulatory milestone without reimbursement | Commercial conclusion remains conditional. |
| A48 | Semiconductor capex announcement without company order | No invented supplier revenue. |
| A49 | Mining project value with debt/dilution | No direct gross-NPV-to-equity substitution. |
| A50 | Nuclear/grid permit without financing/interconnection | Operating consequence not assumed. |
| A51 | Deal breaks or consideration changes | Outcome and issuer roles remain correct. |
| A52 | Missing paired control | Cannot improve paired inference; exclusion denominator shown. |
| A53 | Multiple tickers from one incident | Dependence-aware sample size and uncertainty. |
| A54 | Modern LLM knows historical outcome | Retrospective study not promoted as clean predictive evidence. |
| A55 | Best horizon selected after seeing results | Registered primary analysis unchanged; variant disclosed. |
| A56 | No method beats simple baseline | Honest REJECT/KEEP_SHADOW, no forced winner. |
| A57 | Restart after uncertain write/delivery | Same identity reconciled; no duplicate effect. |
| A58 | Partial publication/mixed source generations | No false fresh complete view. |
| A59 | Burst and model budget exhausted | Factual/cheap path remains honest; defer reasons visible. |
| A60 | UI long text/mobile/keyboard/EN-ZH | Readable correct interaction with no hidden essential state. |
| A61 | Alert correction/dedup/quiet hours | Material updates delivered according to explicit preferences. |
| A62 | Ordinary scheduled producer | Real retained generation reaches entitled API/browser. |
| A63 | Rollback or model downgrade | Correct prior/limited mode restored without history erasure. |
| A64 | End-to-end frozen issue to mature outcome | One attributable chain, not unrelated artifacts. |

## 10. Release gates

G0: exact owners, source/rights/identity/clock feasibility, coverage denominator and initial case selection are recorded.

G1: implementation contracts and applicable adversarial tests pass at the exact candidate; required independent review and repository checks are satisfied.

G2: an ordinary real producer, publication, authorized API, browser and notification path work, including corrections and missing states. This permits a factual/scenario product within its declared coverage.

G3: the specific predictive/advisory claim meets the registered empirical rule and actual decision-owner permission. UI deployment cannot satisfy this gate.

G4: ordinary operating behavior, source health, cost, recovery, rollback and responsibility are demonstrated across the source cadence. A manual canary alone cannot satisfy it.

G5: all retained domain and workflow obligations are accounted for, user tasks pass, and claims accurately reflect qualified capabilities. A pending rare-event study remains an explicit obligation; it cannot be hidden behind a global completed label.

The gates attach to the relevant action and claim. A blocked paid source does not block an independent market-first factual release. A future production gate does not stop ordinary source implementation. A failed model experiment does not authorize weakening the evaluation rule or inventing more favorable labels.

## 11. What would defeat the thesis

The thesis weakens if the price-only baseline discovers the same opportunities with less delay and burden; if economic mappings add plausible stories but no selection value; if source rights or data costs overwhelm the benefit; if early alerts mostly precede false breakouts; if actionable price movement occurs before data are available; or if prospective model performance vanishes after honest temporal controls.

Those outcomes must be allowed. The program succeeds scientifically by resolving them honestly and operationally by delivering only the capabilities that earn their place. Its moat is not the number of engines or agents. It is a reliable, useful and increasingly well-tested investor workflow.
