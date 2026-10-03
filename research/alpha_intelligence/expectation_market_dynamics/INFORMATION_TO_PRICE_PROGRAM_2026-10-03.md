# Information→Price: initiation, architecture delta, and first implementation

Status: **RESEARCH_ONLY; MISSION_COMPLETE: false**

Assignment/evidence carrier: [Macro #8309](https://github.com/mastermindx-market-intelligence/macro/issues/8309)

Operation: `information-to-price-20261003-sol-001`

Source basis: Macro `ff420e6841a2468e4b718340cff240abbef114f1`; protected Mastermind `bdf2a972e68a70270c24d4b5d61a4d60edc4f288`.

## 1. Decision

Initiate the Chairman's package by extending the existing **Expectation Market Dynamics (K3E-0)** work under **WS:ALPHA-INTELLIGENCE-INTEGRATION**. The central information→expectations→market-response architecture already exists as a frozen research design. A second Market Preference engine, Theme Transmission engine, Investment State, belief store or residual engine would obscure ownership and duplicate substantial work.

The first implementation is a reproducible, outcome-blind audit of the existing SRC-A1 expectation observations and attempt receipts. It answers a consequential prerequisite: **can today's retained source data support a comparable, correctly timed expectation→event→price study, and which missing facts prevent it?** It does not turn data-quality judgments into investment judgments.

This is a substantive narrowing based on source evidence, not rejection of the overall question. The handoff's proposed reaction-residual model cannot be validly estimated until the expectation, event, identity, measurement-basis and market-response owners can supply compatible inputs. The audit is designed to make that gap measurable and reproducible, rather than hide it behind a model.

Existing program documents remain controlling for their own contracts. This supplement does not amend EVAL-0, its activation, registered targets, eras, trial budget, horizon definitions, promotion gates or outcome restrictions. The equations below define research questions; they are not production formulas.

## 2. What already exists

| Proposed capability | Existing owner and implementation | Current conclusion from this census |
|---|---|---|
| Expectation trajectories and changing consensus | K3E-0; `collectors/equity_revisions.py`; the two SRC-A1 native parquet artifacts | Raw observations are accruing in committed data. Downstream expectation/market/coupling semantics are not established by the row count. |
| Expectation versus price disagreement and phase transitions | K3E `EXPECTATION_MODEL_SPEC.md`, `MARKET_MODEL_SPEC.md`, `COUPLING_AND_PHASE_SPEC.md` | Already designed: market leading, Street catch-up, expectations continuing while price stalls, market extending while expectations stale, opposing sign and unestimable states. Do not rebuild. |
| Cross-domain expectation baselines and incorporation | MAS-119 and MAS-118, respectively | A local EPS/revenue adapter must not create a universal expectation schema or universal gap score. |
| Per-security Investment State | Market OS `engine/security_state.py` and `contracts/market_os/security_state.v1.schema.json` | Existing pure state/change/evidence composition. Initial AAPL/MSFT scope and all-false financial authority remain. #7963 owns the Prophet-outlook join. |
| Evidence and belief provenance | Research Vault, Research Intelligence, K1 Evidence Foundation | Document custody, source hashes, claim edges, model synthesis, belief deltas and consensus relations already exist. More source copies are not independent evidence. |
| Earnings identity, facts and corrections | Company Intelligence / Earnings / FIF | Canonical issuer-period-event identity and generation/receipt discipline exist. G0 already records the missing reaction/session and consensus joins. |
| Theme propagation | GMI semantic graph, K3-D relationship hypotheses, MarketOntology F04 composition | Membership, causal relationships, market co-movement and transmission hypotheses are distinct. No new GMI transmission engine. |
| Candidate selection | Prophet's existing sleeves, conditional-fusion/evaluation owners | #7762 covers north-star quantitative architecture; #8303 covers regime/indicator research; #7604/#8240 cover emerging-subtheme/early-leadership work. |
| Tactical episodes and dislocation context | Live Entry Radar and native dislocation/reclaim owners | #8305 owns catalyst context; #6625 owns the separate live episode-source repair. No duplicate event identity, replay or classifier. |
| Investment criticism and action | Mastermind `brain/committee.py`, Technician, Sentinel, PM-Conviction, Gate Officer, NEXUS | These roles already exist. Actual deployed flags were not attested in this census. The gated PM judgment book is a scoped exception to an oversimplified “all model judgment is subtract-only” description. |
| Learning and experiments | Existing Evaluation OS/QLedger and K3E EVAL-0 | Reuse registrations, episode identity, trial accounting and promotion. A new notebook is not a new grader or permission to inspect held outcomes. |

Source status is deliberately not upgraded to PROVEN_LIVE. The Executive read at 2026-10-03T06:09:20Z reported installed Mastermind `b3627c580dd37ac1c167f59ac4b7555a4330edef`, Macro `88804ed7079700c598bb8e04aa64307d1335402d`, and read-only mode. Those installed revisions differ from the source pins above. Repository implementation, installed code, scheduled source collection, public rendering and acceptance remain separate proofs.

## 3. The measured source gap

The exact committed observations artifact contains **473,200 rows**, **473,200 unique observation IDs**, and **1,506 ticker symbols**. Declared system-observation clocks run from **2026-08-25T03:40:06.778559Z** through **2026-10-02T12:20:08.635917Z**. The attempts artifact contains **8,583 rows**.

| Field or state | Measured population |
|---|---:|
| Issuer reference missing | 473,200 |
| Security reference missing | 473,200 |
| Units, currency and accounting basis missing | 473,200 each |
| Rights class UNKNOWN | 473,200 |
| Source-effective/source-published clocks missing | 473,200 each |
| Provider/system observation clocks populated | 473,200 each |
| Native period-end populated | 448,588 |
| Native period-end missing | 24,612 |
| Unchanged correction label | 276,724 |
| Original label | 75,630 |
| Missing label | 71,039 |
| Supersedes label | 49,807 |
| Finite measurement rows | 400,509 |
| Genuine NULL measurement rows | 72,691 |
| Structurally eligible declared-capture rows after audit | 400,482 |
| Central average/median rows with declared capture support | 66,860 |
| Retained empty-consensus measurement defects | 27 |
| Observation / attempt collection sessions | 44 / 46 |

The observation bytes have SHA-256 `3db55f485c01bd307f1419ff04f392ae5f1994d2e7d8071b977abe9bbb562b93`. The reviewed diagnostic was executed at the frozen cutoff `2026-10-03T06:31:51Z`. The full report is `INFORMATION_TO_PRICE_AUDIT_2026-10-03.json`, SHA-256 `9191e344d4d10b211a66ccb22f5b5a0a07aa2180aaa2b0ddb08503239a704e36`. Its separate partitions and nonexclusive reasons must not be added together. Arrow nullable decoding preserves true NULL separately from IEEE NaN.

The 27 defects are all retained August 26 C2 observations for BRK-B, COKE and CRVL, where non-count fields were present despite empty analyst coverage. They reproduce the already documented pre-repair error; no later cohort violates that criterion. The nine literal zero coverage counts remain valid coverage facts. The audit also marks 2,016 rows with unavailable coverage companions; these are already within the missing-measurement population. No duplicate-ID, receipt-linkage, supersession-consistency or knowledge-clock violation was detected in this snapshot. This scoped result is not proof of complete history.

Several absences are intentional under SRC-A1. The collector was not authorized to invent issuer identity, fiscal-year/quarter labels, unit, currency, accounting basis, contributor identities or rights. A provider-native period-end can be useful without a guessed fiscal quarter. Therefore these counts identify **downstream dependencies**, not automatically collector defects.

Missing source-publication clocks do not mean all prospective capture evidence is worthless. A retained, independently verified pre-event capture can establish what the system possessed at that time. It cannot prove an earlier public-information history. The audit separates declared capture-time structure from historical availability attestation. It never calls a current Git snapshot “PIT certified.”

Likewise, UNKNOWN rights is not proof of prohibited use, and it is not permission. The accepted source-use owner must resolve the permitted use. The first audit uses already-held data internally and publishes only aggregate diagnostics and immutable byte references.

Raw rows are not independent issuer episodes. Each collection can contain multiple metrics, relative horizons and observation types. Counts, high/low estimates, growth and year-ago values must not be mistaken for additional current consensus means. The audit reports these denominators separately.

## 4. Which hypotheses survive

**Supported as research questions:** some information is incorporated with delay; information diffusion can differ across firms; returns and analyst revisions can contain complementary information; economic links can constrain useful propagation tests; model criticism and research allocation can be evaluated for incremental value.

**Not established:** that a reaction residual identifies sponsorship or underownership; that market “preference” is a unique latent psychological variable; that an LLM can recover a stock's current causal driver from a persuasive narrative; that a lagging beneficiary will catch up; or that a unified architecture beats the existing system.

**Rejected as implementation choices now:** a universal conviction/vibe/gap score; a new global Investment State or evidence store; a new residual engine; rewriting current company models before measuring incremental value; using current snapshots as historical consensus; and running many thresholds until a memorable winner appears.

The appropriate north star is **incremental decision utility conditional on existing information and feasible actions**. “Information per unit of compute” is useful operationally, but too narrow mathematically: accurate information has little action value when it does not change a feasible decision. Conversely, a modest improvement near an action boundary can matter substantially.

There is no fixed smallest set of beliefs for every security and horizon. A sufficient state depends on the permitted decisions, uncertainty, objectives and observation process. Start with a small owner-backed read sufficient for one decision; add a field only when an ablation shows why it matters or a safety/identity contract requires it.

## 5. Precise research objects

### Four different states

Business facts, measured consensus, observed market response and feasible trade decisions remain different objects. Business improvement is not necessarily a positive surprise; a price increase can reflect discount rates rather than better operating facts; a useful forecast can still lack an executable trade after latency, costs and portfolio constraints. Existing Security State may compose owner-backed reads of these objects while preserving their timestamps, uncertainty, missingness and authority. It must not collapse them into one narrative confidence score.

### Expectation and surprise

For a defined issuer, metric, fiscal period and accounting basis, let C-minus be the last admissible pre-event expectation and A the first comparable actual. A surprise is A minus C-minus **only after** currency, units, fiscal period, consolidation and accounting basis match.

Normalization is metric-specific. EPS divided by a pre-event share price is one possible research scale. Dividing a revision by near-zero or negative EPS is not a safe generic transform. Revenue, margin and unit-volume surprises need their own owner definitions. A headline “beat” across incomparable measures is unavailable, not a weak positive.

The collector's snapshot average is not the market's full distribution. High–low is not standard deviation; aggregate analyst count is not contributor identity; a source capture date is not an analyst revision's issued date.

### Expected response and reaction residual

Let R-event be the native market-response owner's event-window quantity. If lawful owner output separates broad-market, sector and issuer components, preserve the exact version, benchmark, universe, corporate-action basis, window and clocks. K3E imports these; it does not recalculate a residual.

A proposed news-response model is:

    m(event) = E[R-event | comparable surprise, pre-event context, information available at forecast time]
    u(event) = R-event - m(event)

The second quantity exists only after R-event is observable. It cannot predict its own event window. A later-return target starts strictly after the admissible decision cutoff and executable entry convention.

The residual includes model error, omitted information, measurement error and shocks. It is not “mispricing” by definition. Moreover, when m is linear in features X, u = R-event minus b'X is an algebraic recombination of X and R-event. Adding u to a linear benchmark already containing both cannot add independent information. Any advantage must survive a comparator with the same underlying information and comparable nonlinear/regularization capacity.

Prediction and mechanism are separate conclusions. A forecast can improve without establishing whether attention, constraints or information diffusion caused the pattern.

### Dynamic driver importance

The proposed driver sensitivity beta(i,j,h,t) is best interpreted initially as a **conditional predictive association** or a derivative of a specified forecast model with respect to a measured surprise. It is not automatically a causal elasticity.

Individual companies have few comparable events. Start with pooled, low-capacity, horizon-specific models and shrinkage; require uncertainty and out-of-time stability before name-specific parameters. Do not select a company's driver, event window or regime after seeing which best explains its return. A driver extraction model must be evaluated separately for extraction accuracy and predictive utility.

### Market preference

Define the measurable target as the conditional payoff to a fixed characteristic or factor portfolio over a fixed horizon. Trailing factor payoff and volatility are demanding simple baselines. Macro regime is contextual information; factor payoffs can change within a macro regime.

Naming recent winners “the market preference” does not identify the next payoff. Risk-premium shifts, cash-flow expectations, exposures and liquidity can produce the same observed rotation. A preference model earns inclusion only through incremental forecasting or decision value, not a satisfying retrospective label.

### Theme transmission

A useful graph has relationships known before the decision, their disclosure/validity clocks, economic direction and exposure semantics. Mere shared theme membership does not prove transfer.

Test whether an upstream event adds information about a downstream outcome after own-name momentum, sector returns, upstream returns and ordinary co-movement. Use existing K3-D/F04/GMI objects and randomized-link negative controls. Separate “unobserved response,” “observed nonparticipation” and “predicted catch-up.” Repeated refusal can falsify a catch-up hypothesis; it cannot reveal investors' motives.

### Research value and criticism

For proposed research Z, existing information I and feasible action set A:

    EVSI(Z | I) = E_Z[max_a E[U(a,Y) | I,Z]] - max_a E[U(a,Y) | I]

Deduct acquisition, compute and latency cost. This defines the question; it does not provide a calibrated numerical score for free. A practical first step logs the decision before research, the exact question, whether the answer changed that decision, and the eventual resolution. Research Vault retains evidence; Executive/Capacity retains task placement.

Critic objections should carry an observable claim, novelty, active-driver relevance, falsifier and horizon. Generic risk, novel uncertainty, material contradiction and hard factual falsification should remain distinguishable. These are annotations to existing roles, not extra veto authority.

Evaluate the base decision, each critic's incremental effect, the final combination, and a simple filter accepting the same fraction. Preserve vetoed proposals. Matched acceptance rates prevent a critic from “winning” merely by refusing most cases. Shadow counterfactual returns do not prove executable fills, borrow or market-impact counterfactuals.

### Change-focused research, evidence decay and model dependence

The useful research unit is a decision-relevant change: which previously cited claim changed, what new source supports the change, which expectation or action could change, and what observable would resolve the uncertainty. Existing Vault/Research Intelligence custody and Executive task placement own the records and work. A repeated summary of the same documents is not a new independent observation.

Evidence age and economic relevance are different. An old audited fact can remain true while its ability to distinguish future outcomes decays; a fresh article can contain stale information. Estimate decay by evidence family, target and horizon only within an admitted training/evaluation design. Until supported, preserve source date, age, novelty and the next scheduled observable instead of fabricating a universal evidence half-life or learned urgency score.

Model outputs remain derived claims. Trace conclusions to original sources and correction families; preserve disagreement and missing support. Counting multiple LLM restatements as corroboration creates a self-reinforcing story without new evidence. Historical tests using contemporary LLM weights also risk future knowledge even when supplied documents are dated correctly. Frozen model/prompt versions and prospective shadow observation are necessary when that contamination cannot be bounded.

Human judgment and model criticism should each earn a defined role through matched-case, matched-information evaluation. Measure forecast accuracy, confidence calibration, changed decisions, false vetoes, coverage, timing and cost as well as eventual utility. A favorable realized P&L alone cannot separate a good forecast, a favorable market move and execution luck.

Technical patterns, attention load and price/expectation disagreement can be measured as predictive context. They do not by themselves identify hidden positioning, forced liquidation or a true dislocation. Existing source-specific incorporation work must determine whether new facts change the business case, consensus, discount-rate context or executable trade; the killed shock-reversal constructions remain closed.

## 6. Empirical evidence that changes the design

- **Chan, Jegadeesh and Lakonishok (1996), Momentum Strategies:** historical returns and earnings surprises carried complementary drift information. This supports keeping earnings, revisions and price controls separate. It does not validate a new residual. [Publisher](https://onlinelibrary.wiley.com/doi/10.1111/j.1540-6261.1996.tb05222.x).
- **Blitz, Huij and Martens (2011), Residual Momentum:** factor-residual momentum reduced conventional momentum's changing factor exposures in their historical study. It concerns historical return residuals, not news-response gaps or ownership identification. [Accepted manuscript](https://repub.eur.nl/pub/22252/ResidualMomentum-2011.pdf).
- **Hirshleifer, Lim and Teoh (2009), Driven to Distraction:** competing announcements were associated with weaker immediate reactions and greater delayed response. Attention load is testable, but announcement timing and common shocks remain alternative explanations. [Author copy](https://bpb-us-e2.wpmucdn.com/sites.uci.edu/dist/c/362/files/2020/07/Driven-to-Distraction-Extraneous-Events-and-Underreaction-to-Earnings-News.pdf).
- **Cohen and Frazzini, Economic Links and Predictable Returns:** disclosed customer/supplier relationships support a concrete lead–lag hypothesis and controls beyond own-stock momentum. Use point-in-time relationships, not today's inferred graph. The accessed copy is a June 2006 draft of later published work. [Author seminar draft](https://w4.stern.nyu.edu/finance/docs/pdfs/Seminars/063f-cohen.pdf).
- **Cochrane (2011), Discount Rates:** time-varying discount rates motivate separating cash-flow news from expected-return/risk-premium changes. Price is evidence, but a rise need not certify a better business outlook. [Author copy](https://www.johnhcochrane.com/s/discount_rates_jf.pdf).
- **Ehsani and Linnainmaa, Factor Momentum and the Momentum Factor:** factor persistence creates a low-cost rotation comparator. The accessed 2019 conference draft is not proof of current tradability or exact final-publication estimates. [Conference draft](https://www.aeaweb.org/conference/2020/preliminary/paper/RHhbnykd).
- **Tetlock (2011), All the News That's Fit to Reprint:** stale repeated news can accompany subsequent reversal. A weak or odd news reaction does not always imply underreaction; deduplication and novelty controls are necessary. [Author research record](https://business.columbia.edu/faculty/research/all-news-thats-fit-reprint-do-investors-react-stale-information).
- **Gueta et al. (2025), Can LLMs Learn Macroeconomic Narratives from Social Media?:** narrative extraction did not consistently improve the examined forecasting tasks; some gains were marginal and a random-text control exposed a content-attribution problem. This is a task-specific negative result, not a universal impossibility claim. [Primary paper](https://aclanthology.org/2025.findings-naacl.4.pdf).
- **Brooks, Frankel and Kamenica (2024), Comparisons of Signals:** the value of a source depends on the other information already available. Evaluate complementarity and redundancy, not standalone apparent quality. [Author paper](https://benjaminbrooks.net/downloads/bfk_comparisons.pdf).
- **Harvey, Liu and Zhu (2016), … and the Cross-Section of Expected Returns:** extensive factor selection changes the evidentiary bar. Count trials and retain adverse findings; significance corrections cannot repair lookahead. [Author copy](https://people.duke.edu/~charvey/Research/Published_Papers/P118_and_the_cross.PDF).

These papers justify discriminating tests. None proves Mastermind's current or proposed implementation produces alpha.

## 7. Existing evaluation contract, preserved

K3E EVAL-0 already registers T1 revision direction, T2 arrival, T3 cluster onset, T4 same-period consensus change, T5 dispersion direction, T6 owner-native residual response, T7 lead–lag and T8 phase transitions.

The existing ruler fixes development 2012–2018, validation 2019–2022, locked holdout 2023-01-03 through 2026-08-21, and prospective activation thereafter. It requires 63-session purge/embargo, 100 distinct issuer episodes overall, 25 per claimed subgroup, a 64-trial family, BY-FDR at q=0.10, and the existing 60% coverage and motivating-case conditions. Exact definitions remain in the immutable JSON registration, not this summary.

The current raw source starts in August 2026. It cannot fill the registered historical eras. If a rights-cleared vintage cannot cover them, the answer is reduced coverage or UNESTIMABLE_AS_PROGRAM, not silently moving dates. No held target outcomes were inspected in this initiation.

Before advanced response/coupling work:
1. Qualify SRC-A1 through its existing owner, including retained lineage and natural collection evidence.
2. Obtain lawful identity, measurement-basis and fiscal-anchor joins; preserve unresolved facts.
3. Follow existing EXP-1 and MKT-1 contracts and acceptance. Import residuals from their owner.
4. Use the strongest eligible registered baseline and its exact target/window.
5. Keep episode clustering, overlap, costs, latency, selection and censoring explicit.
6. Require prospective corroboration and a separate promotion decision before any financial authority.

Price/revisions baselines, same-information nonlinear controls, text-shuffle controls and graph-link controls discussed here are **design recommendations for the proper existing registration owner**. They do not silently add trials, targets or alter EVAL-0.

## 8. Implementation sequence and acceptance

| Phase | Deliverable | Evidence required | Integration boundary |
|---|---|---|---|
| R0 — current source qualification | Stateless native observation/attempt audit; versioned source/owner map | Synthetic integrity/clock/lineage tests; real pinned-input output; independent review; exact source/input hashes | Research files only; no returns, collectors, production state or new schema authority |
| R1 — source owner completion | Missing native identity/basis/use decisions and actual lineage acceptance | Owner-issued receipts; natural unchanged/changed/failure/rollover cohorts; no hindsight backfill | SRC-A1, identity, provider-use and common baseline owners |
| R2 — deterministic expectation surface | Existing EXP-1 read model | Comparable same-period values, explicit missingness, source/observer cutoffs, strongest simple baselines | Existing K3E specification |
| R3 — response and event composition | Existing MKT-1 plus Earnings/FIF/native response reads | Canonical event and security identity; correct sessions; source corrections; owner residual receipts | No new residual/event engine; no Wire-promotion input widening |
| R4 — coupling experiment | Existing CPL-1/EVAL-0 admitted tests | Frozen target, trial accounting, chronological evaluation, strong comparators, episode N | Research-only until native gates pass |
| R5 — prospective consumer | Existing scheduled owner accrues shadow output; existing read model exposes accepted context | Actual natural-time production and consumer proof, degradation, correction and replay checks | Security State/F04/Prophet context as separately accepted |
| R6 — decision and learning | Construction-specific promotion; critic/human attribution | After-cost incremental utility, coverage, calibration, portfolio interaction, independent acceptance | Existing deterministic portfolio/evaluation authority |

R0 completion does not complete the mission. VEND-0 procurement is not a prerequisite for a lawful free-estate EXP-1; accepted degraded outputs can preserve what the existing source does and does not support. R1 is not an instruction to fabricate missing metadata or buy a new feed. Source-use decisions, common schema changes, provider activation and live installation remain with their actual owners.

## 9. Deliberate exclusions and falsifiers

The following remain outside this increment: autonomous live capital; production deployment; trade sizing; new queues, stores, event identities, replay, publication or decision authorities; generic “vibe” scoring; subjective stock-specific driver promotion; inferred hidden positioning; vendor procurement; and held-outcome tuning.

Preserve all relevant construction-scoped exclusions, including DNR:KILL-PSS-F3-RESIDUAL, KILL-LIQUIDITY-SHOCK-REVERSAL-CLASSIFIER, KILL-OUTCOME-AUDITION, KILL-CAUSAL-DAG-ALPHA, KILL-LLM-ORIGINATION and KILL-OWNERSHIP-BREAKAWAY. Shadow execution does not exempt a killed construction.

The broad thesis fails as an implementation program if compatible lawful data cannot support its claims, a simpler eligible model wins, gains vanish under matched information/capacity or feasible latency/costs, or explanatory quality is the only improvement. Keep useful source/context infrastructure where appropriate, but remove the unsupported predictive construction.

## 10. Recoverable next action

The first source audit is implemented, independently reviewed, and executed on the pinned artifacts; all 23 tests pass. Review repaired analyst-coverage dependencies, future-effective clock handling and retained-lineage contradictions before publication. The execution receipt and natural source witnesses are recorded in `VERIFICATION_AND_NEXT_GATE_2026-10-03.md`.

The next useful owner action is SRC-A1 acceptance, with explicit post-repair cohorts and natural producer receipts. Current source-body witnesses now exercise unchanged observations, supersession, partial-after-good preservation, anchored rollover and repeated horizon shape. A fully traced scheduled KBH rollover replaces the initially selected dispatched MKC example, and shares the scheduled September 25 session with the JBGS partial-preservation witness. Successful source execution and publication can coexist with unrelated engine-tail failure; do not invent a blanket job-health gate. Complete the native cohort/contract acceptance record using these component receipts. These bounded witnesses do not independently promote the collector or establish predictive value. Publish the reviewed candidate under #8309, preserve the native accepted state until changed by its proper owner, and open EXP-1 only after that acceptance and a fresh collision census.

The source workspace remains bound to this operation. No Executive Job, external daemon, automated wake, production installation or all-account rollout is claimed. Native research/build/review helpers are bounded contributions consumed in this active session; their results do not transfer source custody or promote this research.
