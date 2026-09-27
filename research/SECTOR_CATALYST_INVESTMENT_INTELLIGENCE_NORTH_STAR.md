# Sector Catalyst Investment Intelligence — shared north-star contract

**Decision:** `DEC:SECTOR-CATALYST-RECOMMENDATION-NORTH-STAR`.
**Scope:** BioCatalyst, Defense Procurement and future sector-specific catalyst/research
lobes. This is a shared product and build contract, not a new runtime, rank service,
source registry, budget authority or permission grant.
**Mandate provenance:** current Chairman instruction, captured on Macro #6712,
[comment5851663121](https://github.com/mastermindx-market-intelligence/macro/pull/6712#issuecomment-5851663121).
**Source basis:** Mastermind protected4c6b206d3fb7fbc6d077faf61ae361bedf259925;
Macro1990a8b8bb2c02ce8595648dcf2cad1f44e29e88. Source publication and model/live-product
acceptance are separate facts. No live recommendation is created by this document.

## 1. The outcome, without dilution

The product recommends the most attractive sector stocks for a defined investment
horizon, explains the expected payoff and major risk, and lets the user inspect the full
research behind the judgment. The first view serves that judgment within seconds.
Research depth is revealed progressively; it is not replaced by superficial language.

The product must answer: **Which stocks? Why these? Why now? How likely is the catalyst
outcome? What could the equity be worth? How much is already reflected in the price?
What could invalidate the thesis? Over what period should the thesis pay?**

The Chairman's objective is a high share of strong realized outcomes, not merely a
pleasant information service. The measurable target therefore includes return quality,
win rate, payoff asymmetry, severe-loss frequency, drawdown, costs and usable coverage.
No fixed success percentage is promised before validation. "Research only forever" is
not the intended end state; neither is uncalibrated automated advice.

## 2. The complete user journey

### Ranked stock picks

Default to actual accepted recommendations, ranked within a declared horizon and
eligible universe. Display the company/security, plain stance, thesis in one sentence,
next catalyst with native date/window, expected **net** return, meaningful success/failure
likelihoods, conditional upside/downside and the primary uncertainty. The reference price,
as-of time, horizon and ranking policy are unambiguous. Do not compare a three-month return
with a twelve-month return as though they were interchangeable.

The lead idea receives visual weight, but the ranked list remains usable. The hero is not
a second unfiltered truth source: changing universe, horizon or eligibility must recompute
or replace the entire consistent view through the existing owner. A low expected-value,
high-success-probability event belongs in an explicit excluded/watch/avoid view, not among
the best buys merely because it is likely to pass.

### A single pick

Open a prepared investment thesis, not an assignment to "go research the company." Show
the investment case, principal risk, catalyst timeline, expected value, probability/payoff
branches, price-implied expectations, scientific/competitive evidence, financial translation,
and conditions that strengthen or invalidate the recommendation. All material claims link
to source evidence and analytical versions. A supporting fact and its strongest
counter-evidence should be inspectable together.

Keep the whole company in view: other pipeline/program value, economic ownership,
licenses/royalties, funding, debt, dilution, catalysts on adjacent assets, competitors,
management incentives, operating execution and valuation all matter.

### Continuity and learning

A recommendation has a stable identity and versions; it is not silently rewritten after
news. Users can see what changed and why. The original probability, price, horizon,
evidence cutoff and falsifiers remain available. The existing user-state/watch/alert
systems keep saved research, enabled watches and delivered alerts distinct. The existing
portfolio/risk/execution owners—not a research narrative—govern sizing and trades.

## 3. One canonical architecture, specialized research

| Responsibility | Reuse / extension boundary |
|---|---|
| Company/security, asset and economic-right identity | Existing Company/Stock Identity and GMI relationships; no local ticker guess or second map |
| Filings, earnings, guidance, transcripts, corporate events | Company/Event and Earnings Intelligence; do not create duplicate SEC/IR collectors |
| Scientific/domain sources and source versions | Existing BioCatalyst or Government Revenue/Defense source owners, GMI/Research Vault, rights and temporal contracts |
| Financial facts, cash, debt, burn, share count, royalties and dilution | Financial Intelligence Fabric / Capital Structure; domain-specific valuation inputs consume these facts |
| Market expectations and incorporation evidence | Existing Alpha/expectations/market dynamics owner; no universal gap score manufactured in the page |
| Forecasts and model evaluation | Extend the accepted domain assessment/evaluation seams; name any missing port before implementation |
| Recommendation rank, stance, eligibility and entry | Existing shared recommendation/entry policy; integrate sector-specific calibrated assessments there |
| Watchlists, portfolio risk, alerts and trade execution | Existing owners; a displayed forecast never self-activates them |
| Cross-session decisions, plans and returns | Agent OS / repository evidence, not another state database |

Known navigation references include `WS:BIOCATALYST-CORE-PRODUCT`, the draft BioCatalyst
V3 program on Macro#6712, `WS:DEFENSE-PROCUREMENT-V3`, `WS:GMI-THEME-GRAPH`, and
`WS:ALPHA-INTELLIGENCE-INTEGRATION`. Names are navigation, not proof that every required
interface is already built. A source/port census must verify the concrete seam at the
implementation head. Missing functionality is an owned extension, not permission for a
parallel system.

## 4. Separate the questions a probability can answer

A single "success probability" is inadequate without a target. Define each forecast with
its event, population, cutoff, horizon, label rule, method version and uncertainty.

For biotech, separate:

* meeting a prespecified trial endpoint with a clinically meaningful effect;
* an acceptable efficacy/safety result in the intended population;
* phase progression, first-cycle FDA approval, eventual approval, and label breadth;
* manufacturing/inspection readiness and the timing of a decision;
* commercial uptake, reimbursement and financing outcomes;
* positive stock return, a specified high-return hurdle, and benchmark outperformance.

An FDA decision is a regulator's review of a sponsor's evidence; not every clinical
study is "an FDA trial." A promising phase II result does not establish phase III
success, approval, reimbursement, or investment profit. FDA describes approval in a
benefit-risk framework; surrogate endpoints and accelerated pathways have distinct
interpretive obligations.[1][2]

A multi-state event model should include positive, mixed/narrow, negative, delayed and
unresolved possibilities where applicable. Mutually exclusive exhaustive states sum to
one. Separately named marginal probabilities need not sum to one and must not be rendered
as though they do. Do not multiply correlated stage probabilities as independent events.
Timing uncertainty is a distribution/window, not an invented exact date.

## 5. The evidence engine: deterministic breadth and specialist judgment

The deterministic layer retrieves, identifies, versions, extracts and compiles available
facts. It preserves raw/source-native representations, units, endpoint definitions,
trial amendments, source timestamps, observation timestamps, corrections and provenance.
It must not label a registry's primary-completion estimate as an announced readout.

For BioCatalyst, the minimum dossier includes:

| Evidence family | Granular questions to retain |
|---|---|
| Trial lineage | Molecule/asset, indication, phase, mechanism, modality, biomarker strategy, prior studies, related programs |
| Protocol and analysis plan | Primary/secondary endpoints, estimand, analysis population, control, randomization, blinding, power, assumed effect, hierarchy and multiplicity |
| Results | Effect size and interval, absolute/relative effects, responder definitions, missingness, attrition, subgroup pre-specification, external replication |
| Safety | Exposure, duration, adverse events, discontinuation, dose relation, imbalance, severe events, historical class issues |
| Regulatory | Public correspondence/review, advisory material, precedent, label scope, accelerated/confirmatory requirements, CMC/inspection risk |
| Business and finance | Rights/royalties, launch costs, funding runway, debt, dilution, addressable patients, net pricing, adoption and competition |
| Company execution | Comparable past programs, indication/modality expertise, operational changes, track record with selection/confounding caveats |
| Market | Reference price, market/enterprise value, consensus/expectations, event response, options context, liquidity and borrow where relevant |

ClinicalTrials.gov's official API provides a structured registry access path; EDGAR APIs
provide submission and financial-XBRL access. They are sources to consume through existing
collectors, not reasons to create another ingestion stack.[3][4] Abstract/full-text rights,
transcript licenses and unpublished regulatory information must be respected. "Not public"
and "not retrieved" are not the same as "does not exist."

The LLM layer performs scientifically and economically useful work: compare studies,
inspect endpoint relevance, challenge subgroup narratives, reconcile inconsistent
statements, identify competing explanations, connect mechanism to observed effect,
assess analogue suitability, synthesize the bull/bear theses, and propose specific
falsifiers. It produces evidence-bound structured findings and reasoned hypotheses,
not unauditable sentiment or a free-floating confidence percentage.

A second reading is valuable when it attacks the first hypothesis; several identical
summaries are not independent evidence. LLM model/version, retrieval scope, evidence
spans and material unresolved questions are retained. Research questions can trigger
bounded follow-up under the existing research owner, but raw LLM enthusiasm cannot
originate or size a trade.

## 6. Priors, updating and calibration

Use historical success/failure cohorts stratified appropriately by phase, specialty,
indication, modality, mechanism novelty, endpoint, population, biomarker enrichment,
regulatory pathway and era. Include discontinued, failed and withdrawn programs and
right-censored cases. Sparse groups shrink toward suitable parent cohorts rather than
producing confident 100% estimates from three examples.

The BIO/Informa/QLS analysis distinguishes indications, modalities, regulatory and
predictive factors.[5] Wong, Siah and Lo also show that cohort and method choices affect
reported rates; their original publication has a corrigendum, which is itself a useful
example of why source corrections must be captured.[6][7] These sources support the
need for conditional priors, not a claim that a particular public rate is suitable for
our current universe without rebuilding its denominator and rights assessment.

Candidate method: a hierarchical prior plus structured statistical/model features and
an evidence-bound research signal, then calibration on held-out data. Compare this with
simpler baselines. LLM research is permitted to materially change a forecast **after its
incremental value is established**; it is not confined to decorative narrative. Conversely,
adding arbitrary percentage points for "good management" or "positive tone" is not Bayesian
updating. Repeated reports, related trials and correlated features need dependence handling.

Clinical-trial prediction research using LLMs exists, including protocol-based transition
prediction and interpretable LLM-agent-generated features.[8][9] Such papers motivate
experiments; their reported accuracy is not our performance, calibrated investment edge,
or permission to promote a model. Accuracy alone can be misleading under imbalance.

## 7. Translate outcomes into equity, not just scientific optimism

For each joint outcome and horizon, estimate conditional **diluted equity value** from
asset economics and the rest of the company. Preserve commercial/risk assumptions:
addressable population or funded program, net price, uptake/delivery, margins, competition,
patent/contract duration, economic rights, development/launch costs, future funding, net
cash/debt, share issuance and terminal value. Multiple catalysts and correlated assets
require joint treatment rather than summing independent headline upsides.

For price `P0`, horizon `H`, mutually exclusive outcomes `s`, probabilities `p_s`,
conditional equity prices `P_s,H`, cash distributions `D_s,H` and expected costs `c_H`:

`E[R_H | information_t] = sum_s p_s * ((P_s,H + D_s,H) / P0 - 1) - c_H`.

Also estimate the probability of positive net return, the probability of beating the
chosen benchmark/hurdle, loss quantiles/expected shortfall and model uncertainty. A high
probability of clinical success with a poor payoff must not rank above a better investment
merely because the scientific story is more certain. Show gross conditional outcome
returns separately from net expected return; never subtract costs inconsistently.

The simple four-state specimen in the R7 mockup is for reading-order and arithmetic
proof only. Production branches contain distributions and real uncertainty, not an assertion
that four point outcomes capture every tail. A stop price is not guaranteed execution
through a binary-event gap.

## 8. Estimate what the price anticipates, honestly

Use multiple independent evidence families when possible: valuation inversion, consensus
estimates and revisions, disclosed expectations, prior event reactions, options distributions,
positioning/borrow and competitor-relative pricing. Each retains its own assumptions and date.

A reverse-valuation success probability is **model-implied**, not directly observed investor
belief. Discounting, risk premiums, other pipeline value, financing assumptions and joint
outcomes make the inverse problem non-unique. Publish a sensitivity range and the dominant
assumption, not a false precise "% priced in." An option-implied move is neither approval
probability nor proof that expected upside is exhausted.

If the same model supplies both "our value" and "price-implied success," the gap is a
restatement of that model's thesis, not independent confirmation. Independent market
expectation evidence and falsifiers remain required. An impossible implied probability
is a model inconsistency, not a number to clamp silently into a plausible range.

## 9. Rank the investment, not the story

Integrate these assessments with the existing recommendation/entry owner. Rank within
comparable horizons using uncertainty-aware expected excess return and the accepted risk,
liquidity, cost, concentration and entry policy. Report coverage and abstention alongside
performance so a tiny cherry-picked sample cannot masquerade as universal accuracy.

Do not invent an opaque blended Catalyst Score. The ranking may be mathematically rich,
but its explanation must be plain: why this pick outranks the next, what return is
anticipated, what loss can occur, and which assumption could change the order. A number
on a page is not sizing authority. Portfolio allocation remains with the existing owner.

## 10. Defense Procurement is the second specialist profile

Keep the same investment output and user journey, but replace the causal evidence model.
The Defense profile must distinguish:

* budget authorization, appropriation, solicitation, ceiling, obligation and award as
different events—not interchangeable revenue;
* competitive set, incumbent position, technical performance, price/cost realism,
production readiness, teaming/subcontract rights and down-selection evidence;
* protest/recompete/cancellation/delay probabilities, procurement route and contract type;
* delivery milestones, funded backlog conversion, margins, working capital, capacity,
supplier constraints, capex and retained economics;
* materiality to the issuer and expected earnings/free-cash-flow impact;
* the stock's current expectations, valuation, conditional rerating and downside.

Historical cohorts require their own award/funding/outcome definitions and selection
bias audit. A biotech phase-transition prior is not a procurement win-rate prior. A
multibillion-dollar ceiling does not imply a multibillion-dollar award, nor does an award
imply immediate profits. Generalize the schema/experience and evaluation discipline;
retain domain-specific causal and financial models.

## 11. How to prove a real edge

Freeze target definitions, universe, benchmark, horizon, costs, evaluation dates and
acceptance thresholds before judging the model. Use temporally separated validation,
clustered molecule/company/program holdouts, leakage audits, corrected delisting/corporate
history and clearly handled unresolved outcomes. One asset's repeated trial readouts do
not supply independent sample size.

Measure three levels separately:

1. **Evidence correctness:** identity, extraction, source precision/recall, contradiction
coverage, data completeness, historical non-leakage, update latency and rights.
2. **Forecast quality:** calibration/reliability with uncertainty; Brier/log-loss; event
timing; discrimination by relevant subgroup; prior-only and structured-only comparisons;
stability across regimes and model versions.
3. **Investment utility:** net realized returns and benchmark excess; win rate and payoff
ratio; expected shortfall/drawdown; precision among top picks; coverage and turnover;
executable prices, gaps, spreads, liquidity/capacity and correlated event exposure.

A past-looking retrieval cutoff is necessary but does not remove future facts memorized
in model weights. Treat retrospective LLM backtests with appropriate caution and use
prospective frozen forecasts/shadow recommendations as a decisive test. Entity masking or
prompt instructions alone are not proof of leakage removal. Preserve both positive and
negative results and measure incremental value of LLM research against a no-LLM baseline.

The learning loop classifies misses as event-direction error, timing error, effect-size/
label error, commercial/financial translation error, pricing/expectations error, execution
friction, regime change or evidence defect. It should also study overlooked winners and
false exclusions. Revisions and recalibration follow existing evaluation and model-release
owners, not a page script that tunes itself on recent outcomes.

## 12. Build sequence that reaches the actual product

**S1 — One complete event cohort.** Select a bounded, rights-accessible, historically
reconstructable cohort. Establish source coverage, outcome labels, companies and economic
rights. Resolve unobservable targets explicitly. This is a foundation, not completion.

**S2 — Research and model comparison.** Build source dossiers, prior baselines, structured
features and LLM-enriched research. Validate extraction and leakage. Run matched temporal
experiments and document adverse cases. This is a candidate model, not a live signal.

**S3 — Outcome-to-equity and expectations.** Join the existing financial and market owners,
produce horizon-specific scenarios, dilution/cost assumptions, return distributions and
sensitivity. Test against simple historical/valuation baselines and issuer counterexamples.

**S4 — Full shadow recommendation vertical.** Through the existing recommendation owner,
produce ranked timestamped picks, prices, horizons, watch/avoid decisions and complete
customer-shaped dossiers. Record prospective outcomes using the existing evaluation owner.

**S5 — Scoped production admission.** Meet preregistered source/model/risk/commercial
acceptance, show the real-path user journey, then release only the validated scope. Retain
abstention and degraded-state behavior. Expand by demonstrated evidence, not by copying
unvalidated probabilities into more specialties.

**S6 — Cross-sector expansion.** Reuse shared interfaces and experience. Add Defense's
specialist evidence/priors/financial translation, independently validate it, and carry the
same full selection-to-learning contract forward.

## 13. Builder acceptance map

These are obligations, not reported test results.

| ID | Required proof |
|---|---|
| SC-01 | Ranked Buy/Wait/Watch/Avoid output reaches the primary page through the accepted owner |
| SC-02 | Rank binds security, reference price/time, universe, model/policy version and horizon |
| SC-03 | Each pick opens the actual thesis and strongest counter-thesis, not a research to-do list |
| SC-04 | Catalyst outcome, timing, FDA/clinical label, stock profit and outperformance remain distinct |
| SC-05 | Outcome states are exhaustive where claimed, with delay/missingness explicitly handled |
| SC-06 | Priors have valid phase/specialty/modality/era denominators and sparse-cohort treatment |
| SC-07 | Granular evidence includes protocols, endpoints, effect sizes, safety and amendments |
| SC-08 | Filings/transcripts and economic-rights evidence join the correct company at the cutoff |
| SC-09 | LLM claims bind to source spans; counter-evidence and unavailable evidence remain visible |
| SC-10 | No repeated document, related trial or correlated model output is counted as independent proof |
| SC-11 | Held-out calibration and simple/no-LLM baselines are reported with uncertainty |
| SC-12 | Conditional equity values include rights, burn, financing, dilution and the rest of the company |
| SC-13 | Expected-return arithmetic and gross/net treatments reconcile across page, dossier and export |
| SC-14 | Price-implied expectations include method/sensitivity and no false observed-consensus claim |
| SC-15 | Same-model valuation gap is not counted as independent confirmation |
| SC-16 | A high-success/negative-EV counterexample is excluded despite a compelling scientific story |
| SC-17 | Horizon switches use separately evaluated horizon estimates, not linear scaling |
| SC-18 | Missing data or failed calibration withdraw affected estimates without erasing valid facts |
| SC-19 | Source corrections preserve original forecast versions and actual known-at-time information |
| SC-20 | Prospective shadow records include losers, delistings, rejected ideas, coverage and costs |
| SC-21 | Performance separates forecast quality, selection utility, implementation defects and regime effects |
| SC-22 | Default page explains the recommendation, payoff, horizon and main risk within seconds |
| SC-23 | Dossier retains full technical depth under readable progressive disclosure |
| SC-24 | Dark/light, EN/ZH, keyboard/focus and 320/390/tablet/desktop real paths are verified |
| SC-25 | Unavailable/empty/partial/stale/auth states cannot manufacture a current recommendation |
| SC-26 | Saving, monitoring and trading retain their existing distinct authorities and receipts |
| SC-27 | Defense distinguishes funding/ceiling/obligation/award/revenue/margin/cash |
| SC-28 | A new sector reuses shared source/identity/state/rank/evaluation owners, not duplicated systems |
| SC-29 | A cold-start builder retrieves this DEC/contract through the existing owning program intake |
| SC-30 | Completion includes useful intelligence, a full ranked-pick journey and validated learning—not just ingestion |

## 14. Anti-regression instructions for future sessions

Do not "make the product safer" by permanently removing predictions or recommendations.
Make the methods and admission better. Do not "make it simpler" by stripping away the
analysis that creates value. Make its meaning easier to consume. Do not "make it impressive"
by inventing probabilities, prices, live alerts or precision that the owners cannot support.

The target is **a powerful specialist investment engine with a very simple face**. Show the
conclusion first, expose the strongest caveat, and retain the entire chain behind the click.

## 15. Research references and precise use

[1] FDA, Development & Approval Process: https://www.fda.gov/Drugs/DevelopmentApprovalProcess/
— benefit-risk and review context, not a prediction dataset.

[2] FDA, Surrogate Endpoint Resources: https://www.fda.gov/drugs/development-resources/surrogate-endpoint-resources-drug-and-biologic-development
— endpoint interpretation, not a generic conversion to success probability.

[3] NLM, ClinicalTrials.gov API Version2.0:
https://www.nlm.nih.gov/pubs/techbull/ma24/ma24_clinicaltrials_api.html
a— official structured registry access. Current schema/rights must be rechecked at implementation.

[4] SEC, EDGAR APIs:
https://www.sec.gov/search-filings/edgar-application-programming-interfaces
— submissions and XBRL access, with entity/timing/units and access rules preserved.

[5] BIO/Informa/QLS, Clinical Development Success Rates2011–2020:
https://www.bio.org/clinical-development-success-rates-and-contributing-factors-2011-2020
— conditional prior taxonomy; no copied proprietary corpus or unsupported current-rate claim.

[6] Wong, Siah, Lo, Estimation of Clinical Trial Success Rates:
https://pubmed.ncbi.nlm.nih.gov/29394327/ — method/cohort sensitivity.

[7] Corrigendum: https://academic.oup.com/biostatistics/article/20/2/366/5183543
— corrections must be included in the evidence lineage.

[8] CTP-LLM: https://arxiv.org/abs/2408.10995 — candidate research precedent, not accepted production performance.

[9] AutoCT: https://arxiv.org/abs/2506.04293 — LLM-agent/structured-feature research precedent,
not proof of equity alpha or our own calibration.
